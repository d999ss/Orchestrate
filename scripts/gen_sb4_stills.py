#!/usr/bin/env python3
"""Generate Storyboard 4 still frames with OpenAI gpt-image-1.

Art direction: dark-teal point-cloud / particle render, cyan-on-black, the
Orchestrate 2026 reference look. Subjects = the 30 electron-journey shots,
natural-gas origin, a single brighter cyan point as the electron.

Idempotent: skips frames that already exist (non-empty) unless --force.
Usage:
  .venv/bin/python scripts/gen_sb4_stills.py            # all missing
  .venv/bin/python scripts/gen_sb4_stills.py 1 2        # only frames 1,2
  .venv/bin/python scripts/gen_sb4_stills.py --force 2  # regen frame 2
"""
import os, sys, json, base64, pathlib, ssl, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import certifi
    SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:
    SSL_CTX = ssl.create_default_context()

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "storyboard-4"
OUT.mkdir(parents=True, exist_ok=True)

SECRETS = json.loads(pathlib.Path(os.path.expanduser("~/.claude/secrets.json")).read_text())
API_KEY = SECRETS["openai"]["api_key"]
ENDPOINT = "https://api.openai.com/v1/images/generations"
MODEL = "gpt-image-1"
SIZE = "1536x1024"
QUALITY = "high"

STYLE = (
    "Dark-teal point-cloud render. The subject is constructed entirely from thousands of "
    "tiny glowing cyan-teal particles and dots (color #4ED9C6, white-hot on the nearest edges), "
    "like a 3D LED scan or voxel point cloud floating in a deep near-black void. Monochrome "
    "cyan-on-black palette, very dark teal background (#04090b) with a soft radial vignette and "
    "faint volumetric haze, gentle bloom and shallow depth of field, fine constellation particle "
    "overlays drifting in the surrounding darkness. Cinematic, moody, high dynamic range, painterly "
    "and abstract, NOT photoreal documentary. Generous negative black space. Absolutely no text, "
    "no logos, no words, no letters, no numbers, no brand marks anywhere. "
)

SUBJECTS = {
    1:  "A natural gas power plant and turbine hall at night, stacks and pipework, with a faint warm core glow of combustion deep inside the structure.",
    2:  "Extreme close macro of a spinning generator turbine rotor; at its center a single brighter white-cyan point of light breaks free from the particle field, an electron being born.",
    3:  "A copper conductor as a stream of particles; a chaotic cloud of dots resolving into one directed, flowing line of brighter cyan light moving through the frame.",
    4:  "A tall high-voltage step-up transformer with coils and bushings, a brighter pulse of light climbing the windings.",
    5:  "An electrical switchyard of insulators and steel gantries, a single bright cyan thread of current racing out along the first conductor into the dark distance.",
    6:  "A lone silhouetted operator before a wide wall of glowing grid-data displays in a dim control room, a climbing load curve on screen.",
    7:  "Macro of a thick insulated power cable, a brighter cyan current pulsing just beneath its surface.",
    8:  "A single tall transmission pylon rising from the ground into a black sky, a faint cyan current thread climbing the conductor, backlit.",
    9:  "A long line of transmission towers striding across dark open terrain toward the horizon, faint cyan current on the wires, wide cinematic composition.",
    10: "Aerial view racing along a corridor of transmission towers, motion implied by streaking cyan particle trails.",
    11: "Giant transmission towers spanning a wide dark river, a faint reflection of dots on the black water below, hazy.",
    12: "Aerial of power lines running parallel to a faint highway toward a distant city glow on the horizon.",
    13: "A downtown Atlanta skyline emerging from darkness, the tall Signia by Hilton glass tower and the distinctive curved roof of Mercedes-Benz Stadium recognizable among towers of glowing dots, faint haze, wide cinematic.",
    14: "A line of urban distribution poles descending into a particle cityscape at night, current threading down.",
    15: "Macro of substation insulators, a crisp bright blue-cyan arc of light crackling across a small gap.",
    16: "Low view beneath city distribution lines, a brighter cyan current pulsing along the wires toward a glow ahead, night.",
    17: "The Signia by Hilton Atlanta at night, a tall modern glass hotel tower with a glowing facade and the Georgia World Congress Center convention hall adjacent, a warmer glowing entrance, a crowd of faint particle figures filtering in.",
    18: "Macro into an electrical breaker panel, the brighter cyan feed pressing down into the bus bars.",
    19: "A row of breakers, indicators lighting one by one, a single brighter cyan point standing out among them.",
    20: "Tight macro of a breaker contact, a small controlled bright cyan spark flashing at the gap.",
    21: "First-person view plunging into a glowing tunnel inside a power cable, walls of dots rushing past toward a bright point ahead.",
    22: "Accelerating first-person tunnel of streaking particles, a bright filament point of white-cyan light growing at the end, tight vignette.",
    23: "Wide of a lone speaker at a lectern on a dark stage, a glowing presentation screen behind, the audience house in shadow.",
    24: "Tight macro of a hand reaching for a presentation clicker, a brighter edge glow on the fingers.",
    25: "Macro into a stage LED fixture, a single bright cyan point striking the junction and a bloom of cyan light building from it.",
    26: "First-person burst of a single bright white-cyan point of light rocketing out through a lens into a dark hall, a cyan particle lens flare.",
    27: "A single bright cyan beam of light streaking across a dark auditorium over rows of faint silhouetted heads toward one figure.",
    28: "A young person's face turning up into a beam of cyan light in the dark, eyes catching the glow.",
    29: "Tight on a face flooded with blooming cyan-white light, the moment of impact, dark surround.",
    30: "Wide of a stage and conference hall igniting in bright cyan-white light, the room and audience revealed as a vast field of glowing particles, climactic.",
}


def http(body, retries=4):
    data = json.dumps(body).encode()
    last = None
    for attempt in range(retries):
        req = urllib.request.Request(
            ENDPOINT, data=data,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=300, context=SSL_CTX) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            body_txt = e.read().decode()
            last = f"HTTP {e.code}: {body_txt[:300]}"
            if e.code in (429, 500, 502, 503):
                time.sleep(8 * (attempt + 1))
                continue
            raise RuntimeError(last)
        except (urllib.error.URLError, TimeoutError) as e:
            last = str(e)
            time.sleep(6 * (attempt + 1))
    raise RuntimeError(last or "unknown error")


def gen(n):
    path = OUT / f"frame-{n:02d}.png"
    prompt = STYLE + "SHOT: " + SUBJECTS[n]
    resp = http({"model": MODEL, "prompt": prompt, "size": SIZE, "quality": QUALITY, "n": 1})
    b64 = resp["data"][0]["b64_json"]
    path.write_bytes(base64.b64decode(b64))
    return n, path.stat().st_size


def main():
    args = [a for a in sys.argv[1:] if a != "--force"]
    force = "--force" in sys.argv
    nums = [int(a) for a in args] if args else list(range(1, 31))
    todo = []
    for n in nums:
        p = OUT / f"frame-{n:02d}.png"
        if p.exists() and p.stat().st_size > 5000 and not force:
            print(f"skip  frame-{n:02d} (exists)")
        else:
            todo.append(n)
    if not todo:
        print("nothing to do")
        return
    print(f"generating {len(todo)} frame(s): {todo}")
    ok, fail = 0, 0
    with ThreadPoolExecutor(max_workers=3) as ex:
        futs = {ex.submit(gen, n): n for n in todo}
        for f in as_completed(futs):
            n = futs[f]
            try:
                n, size = f.result()
                ok += 1
                print(f"OK    frame-{n:02d}  ({size//1024} KB)")
            except Exception as e:
                fail += 1
                print(f"FAIL  frame-{n:02d}  {e}")
    print(f"done: {ok} ok, {fail} failed")


if __name__ == "__main__":
    main()
