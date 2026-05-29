#!/usr/bin/env python3
"""SB3 v2 — Veo 3.0-fast regen with camera motion + 16:9 source pre-crop.

Same approach as gen_sb2_v2.py:
- Art direction lock matches SB1 v23 (cyan-on-deep-black painterly, energy
  under control, no text/logos)
- Each prompt closes with a frame-specific camera motion verb instead of
  "Locked-off camera"
- Source PNGs pre-cropped 1536x1024 -> 1536x864 (16:9) so Veo doesn't invent
  content top/bottom

Output: films/sb3_clips_v2/clip-NN.mp4 (idempotent)
"""
import os, sys, json, time, base64, pathlib, ssl, urllib.request, urllib.error, io
import certifi
from concurrent.futures import ThreadPoolExecutor, as_completed
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from PIL import Image

SSL_CTX = ssl.create_default_context(cafile=certifi.where())
ROOT = pathlib.Path(__file__).resolve().parent.parent

PROJECT = "orchestrate-veo"
LOCATION = "us-central1"
SA_KEY = os.path.expanduser("~/.claude/secrets/veo-runner-key.json")
MODEL = "veo-3.0-fast-generate-001"
ENDPOINT = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT}/locations/{LOCATION}/publishers/google/models/{MODEL}"

STYLE = (
    "Maintain the EXACT cyan-on-deep-black painterly concept-art aesthetic of the reference image. "
    "Stylized, atmospheric, painterly. NOT photoreal, NOT documentary, NOT real-world video. "
    "Energy is directed, precise, deliberate, contained. NOT chaotic, NOT photoreal lightning, "
    "NOT explosive. The energy stays channeled and purposeful. "
    "Cyan-white emissive glow on deep black void. Soft halation around bright sources. "
    "ABSOLUTELY NO TEXT, NO LOGOS, NO WORDS, NO LETTERS, NO BRAND MARKS anywhere in the frame. "
)

# SB3 — Branded Matrix. Same general arc as SB2 but slightly different framing.
# Per-frame camera motion derived from each storyboard description's verb.
PROMPTS = {
    1:  "A glowing globe floats in deep darkness. Connected lights appear across continents — the planet running on the grid. Camera slowly orbits the planet.",
    2:  "Camera moves toward the globe and transitions into a modern energy facility — where electricity starts. Camera pushes in steadily.",
    3:  "Natural gas ignites inside a turbine system. The first energy release — combustion at scale. Camera slowly dollies forward into the chamber.",
    4:  "Step 1 — Gas ignites. Heat releases as a column of rising cyan energy inside the chamber. Camera tilts upward following the column.",
    5:  "Step 2 — The energy spins into a vortex, gathering speed in a tight rotational motion. Camera orbits around the vortex.",
    6:  "Step 3 — Spin transfers into a magnetic field, cyan electromagnetic flux forming around the rotor. Camera pushes in toward the rotor.",
    7:  "Step 4 — Spinning magnetic fields induce current. Motion becomes voltage, visible cyan field lines pulsing. Camera orbits around the field.",
    8:  "Step 5 — Electricity sparks into being. The first arc of cyan current jumps between conductors. Camera holds with subtle drift, then pushes in.",
    9:  "Step 6 — Electrons stream forward as a current pulse. The journey of electricity begins along a conductor. Camera tracks with the current.",
    10: "Electricity moves into the power grid. High-voltage lines leaving the substation in a cinematic wide shot. Camera dollies sideways with the lines.",
    11: "Transformers increase the power for long distance travel. Voltage stepped up, coils glowing cyan. Camera pushes in toward the coils.",
    12: "Transmission lines carry electricity across a region. Towers and wires marching toward the city. Camera dollies forward through the corridor.",
    13: "The regional grid becomes visible. Dot matrix tilting into depth — the system as terrain. Camera tilts up to reveal the matrix.",
    14: "Grid systems direct where electricity needs to go. Cyan paths fan out across the territory. Camera pulls back to reveal the branches.",
    15: "Operators silhouetted in a control room, monitoring screens. Human-in-the-loop, eyes on the grid. Camera drifts laterally across the silhouettes.",
    16: "The southeastern power network becomes visible. The full regional system, lit cyan. Camera pulls back to expose the full network.",
    17: "More power begins flowing toward Atlanta. The current bends toward the destination. Camera follows the curve of the current.",
    18: "Transmission lines lead into the city. The lattice tightens around Atlanta. Camera tracks forward toward the city.",
    19: "Atlanta begins lighting up. The skyline catches the surge of incoming power. Camera drifts laterally across the brightening skyline.",
    20: "Buildings, roads, and infrastructure activate across the city. Every system coming online at once. Camera pushes in over the city.",
    21: "The city brightens. The skyline catches the surge before the landmark stadium ignites. Camera pushes forward toward the stadium.",
    22: "Cyan electricity flows into the stadium. The path's final surge — the climax of the journey. Camera tracks the current as it enters.",
    23: "The stadium lights turn on. An eight-petal pinwheel crown ignites in cyan over the host city. Camera orbits above the stadium.",
    24: "The surrounding downtown area lights up. The full mesh of the city visible at once. Camera pulls up to expose the lit grid.",
    25: "A modern luxury conference center powers on at night. Signia by Hilton — the front door of the journey's end. Camera drifts wide across the exterior.",
    26: "Interior corridors and halls activate inside the convention complex. Lights coming awake one by one. Camera pushes forward through the corridors.",
    27: "A keynote room begins turning on. A soft particle bloom — the space the journey lands in. Camera drifts forward into the space.",
    28: "Stage lights and presentation screens activate. The room fully lit, ready to begin. Camera pushes in toward the stage.",
    29: "A vast keynote hall, audience silhouetted in the foreground, a glowing cyan globe on the keynote screen in the distance. Camera pushes slowly forward through the audience toward the screen — the journey's final destination.",
    30: "The whole planet, fully lit and connected — the visual opposite of where we began. Camera slowly orbits the glowing planet, pulling slightly back to reveal its full scale.",
}


def crop_to_16_9_b64(png_path: pathlib.Path) -> str:
    img = Image.open(png_path).convert("RGB")
    w, h = img.size
    target_h = int(round(w * 9 / 16))
    if target_h < h:
        top = (h - target_h) // 2
        img = img.crop((0, top, w, top + target_h))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def mint_token():
    creds = service_account.Credentials.from_service_account_file(
        SA_KEY, scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(Request())
    return creds.token


def http(url, token, body):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120, context=SSL_CTX) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try: body = json.loads(body)
        except Exception: pass
        return e.code, body


def submit_one(idx, prompt, token):
    out_dir = ROOT / "films" / "sb3_clips_v2"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_mp4 = out_dir / f"clip-{idx:02d}.mp4"
    if out_mp4.exists():
        return idx, None, "exists"
    img_path = ROOT / "storyboard-3" / f"frame-{idx:02d}.png"
    if not img_path.exists():
        return idx, None, f"missing {img_path}"
    b64 = crop_to_16_9_b64(img_path)
    payload = {
        "instances": [{
            "prompt": STYLE + prompt,
            "image": {"bytesBase64Encoded": b64, "mimeType": "image/png"},
        }],
        "parameters": {
            "aspectRatio": "16:9",
            "durationSeconds": 4,
            "sampleCount": 1,
            "resolution": "1080p",
            "personGeneration": "allow_all",
            "generateAudio": False,
        },
    }
    code, resp = http(f"{ENDPOINT}:predictLongRunning", token, payload)
    if code != 200 or "name" not in (resp if isinstance(resp, dict) else {}):
        return idx, None, f"HTTP {code}: {resp}"
    return idx, resp["name"], None


def poll_one(idx, opname, token):
    out_dir = ROOT / "films" / "sb3_clips_v2"
    out_mp4 = out_dir / f"clip-{idx:02d}.mp4"
    if out_mp4.exists():
        return idx, "exists"
    code, r = http(f"{ENDPOINT}:fetchPredictOperation", token, {"operationName": opname})
    if code != 200:
        return idx, f"poll HTTP {code}"
    if not r.get("done"):
        return idx, "pending"
    if r.get("error"):
        return idx, f"ERROR: {r['error']}"
    preds = r.get("response", {}).get("videos", [])
    if not preds:
        return idx, "no videos"
    b64 = preds[0].get("bytesBase64Encoded")
    if b64:
        out_mp4.write_bytes(base64.b64decode(b64))
        return idx, f"saved clip-{idx:02d}.mp4"
    return idx, "unknown response"


def main():
    only = None
    if len(sys.argv) > 1:
        only = set(int(x) for x in sys.argv[1].split(","))
    todo = [(i, PROMPTS[i]) for i in range(1, 31) if only is None or i in only]
    print(f"Generating {len(todo)} SB3 v2 clips")
    token = mint_token()
    ops = {}
    for idx, prompt in todo:
        out_mp4 = ROOT / "films" / "sb3_clips_v2" / f"clip-{idx:02d}.mp4"
        if out_mp4.exists():
            print(f"  clip-{idx:02d}: skip (exists)")
            continue
        backoff = 15
        for attempt in range(6):
            i, op, err = submit_one(idx, prompt, token)
            if err == "exists":
                break
            if not err:
                ops[idx] = op
                print(f"  clip-{idx:02d}: submitted")
                break
            if "HTTP 429" in str(err) or "RESOURCE_EXHAUSTED" in str(err):
                print(f"  clip-{idx:02d}: 429, retry in {backoff}s")
                time.sleep(backoff)
                backoff = min(backoff * 2, 120)
                continue
            print(f"  clip-{idx:02d}: FAIL {err}", file=sys.stderr)
            break
        time.sleep(4)

    if not ops:
        print("Nothing to poll.")
        return

    print(f"\n=== Polling {len(ops)} ops ===")
    done = set()
    last_token = time.time()
    while len(done) < len(ops):
        if time.time() - last_token > 2400:
            token = mint_token()
            last_token = time.time()
        pending = [(k, v) for k, v in ops.items() if k not in done]
        with ThreadPoolExecutor(max_workers=12) as ex:
            futs = {ex.submit(poll_one, idx, op, token): idx for idx, op in pending}
            for fut in as_completed(futs):
                idx, status = fut.result()
                if status.startswith("saved") or status == "exists":
                    done.add(idx)
                    print(f"  clip-{idx:02d}: {status}")
                elif "ERROR" in status or "HTTP" in status or "no videos" in status:
                    print(f"  clip-{idx:02d}: {status}", file=sys.stderr)
                    done.add(idx)
        if len(done) < len(ops):
            print(f"  {time.strftime('%H:%M:%S')} {len(done)}/{len(ops)} done")
            time.sleep(15)
    print(f"\n=== Done ({len(done)}/{len(ops)}) ===")


if __name__ == "__main__":
    main()
