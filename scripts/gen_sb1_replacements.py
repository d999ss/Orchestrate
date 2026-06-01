#!/usr/bin/env python3
"""Regenerate the 6 SB1 frames that didn't read narratively.

Replacements (legible, literal, not abstract):
  f08  electromagnetic burst → actual generator interior (copper windings + sparks)
  f14  data trails           → aerial transmission grid at night (lit power lines)
  f17  cyan flow             → transmission lines leading into city skyline
  f23  stadium bloom         → actual modern stadium at night, lights blazing
  f29  keynote pull-back     → packed keynote auditorium with stage
  f30  (was earth)           → triumphant low-angle stage finale shot

Uses Vertex Veo 3.0-fast text-to-video (no start image — the existing
storyboard PNGs are the unreadable ones). Originals archived.
"""
import os, sys, json, time, base64, pathlib, ssl, urllib.request, urllib.error
import certifi
from concurrent.futures import ThreadPoolExecutor, as_completed
from google.oauth2 import service_account
from google.auth.transport.requests import Request

SSL_CTX = ssl.create_default_context(cafile=certifi.where())
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "films" / "sb1_clips"
ARCHIVE = OUT / "v9_abstract_originals"
ARCHIVE.mkdir(exist_ok=True)

PROJECT = os.environ.get("GCP_PROJECT", "orchestrate-veo")
LOCATION = os.environ.get("GCP_LOCATION", "us-central1")
SA_KEY = os.path.expanduser("~/.claude/secrets/veo-runner-key.json")
MODEL = "veo-3.0-fast-generate-001"
ENDPOINT = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT}/locations/{LOCATION}/publishers/google/models/{MODEL}"

STYLE = (
    "Locked-off static camera, no pan, no tilt, no zoom, no dolly. "
    "Cold cyan-white industrial cinematography, photoreal, hyperreal detail, "
    "broadcast film quality, anamorphic widescreen. "
    "ABSOLUTELY NO TEXT, NO LOGOS, NO WORDS, NO LETTERS, NO BRAND MARKS anywhere in frame. "
)

# Literal compositions — viewer must understand what they're looking at without context.
SUBJECTS = {
    8:  "Macro extreme close-up inside a massive electrical generator. Polished copper stator windings filling the frame. Visible electrical discharge sparks crackling between rotor poles. Cyan-white electricity actively pulsing through the copper coils. Mechanical industrial detail, oil-slick textures, glowing electromagnetic activity. The viewer must immediately recognize this as a power generator interior.",

    14: "Aerial top-down view of a regional electrical transmission grid at night. Glowing high-voltage power lines stretched between tall lattice transmission towers across dark countryside. Multiple parallel power lines crossing rolling terrain. Cyan-white energy actively pulsing along the conductors. Scale of a national grid. Wide cinematic establishing shot.",

    17: "Wide cinematic ground-level shot. Massive lattice transmission towers carrying high-voltage power lines leading from the foreground toward a brightly-illuminated modern city skyline in the far distance at night. Cyan-white electricity actively surges along the conductor lines toward the city. The city's lights glow on the horizon. Atmospheric haze. Photoreal infrastructure cinematography.",

    23: "Aerial wide cinematic shot of a modern football stadium at night, fully illuminated. Stadium dome visible, perimeter lights blazing, the playing field bright and active inside, surrounding stands filled with crowd silhouettes. Urban skyscrapers visible in the background. The entire stadium is unmistakably a real sports venue at peak activity. Hyperreal architectural detail.",

    29: "Wide cinematic interior shot of a packed corporate keynote auditorium. Thousands of attendees seated in tiered rows facing a massive curved illuminated stage at the front. Stage lights blazing with cyan-white intensity. A huge immersive curved LED screen at the front of the stage glowing with abstract cyan light patterns. Audience silhouettes filling the foreground. Conference setting unmistakable.",

    30: "Triumphant low-angle hero shot of a fully-activated keynote stage at peak performance. Massive stage lights at full intensity casting cyan-white beams upward and outward into the rafters. The immersive curved LED screens behind the stage glowing brilliantly with abstract cyan light. Smoke and atmospheric haze diffusing the light. Stage edge in foreground, lights blazing. Climactic finale moment.",
}


def mint_token():
    creds = service_account.Credentials.from_service_account_file(
        SA_KEY, scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(Request())
    return creds.token


def http(url, token, body=None):
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


def submit_one(idx, token):
    out_mp4 = OUT / f"clip-{idx:02d}.mp4"
    # Archive original
    if out_mp4.exists():
        arch = ARCHIVE / out_mp4.name
        if not arch.exists():
            out_mp4.rename(arch)
        else:
            out_mp4.unlink()
    payload = {
        "instances": [{"prompt": STYLE + SUBJECTS[idx]}],
        "parameters": {
            "aspectRatio": "16:9",
            "durationSeconds": 4,
            "sampleCount": 1,
            "resolution": "1080p",
            "personGeneration": "allow_all",
            "generateAudio": False,
        },
    }
    code, resp = http(f"{ENDPOINT}:predictLongRunning", token, body=payload)
    if code != 200 or "name" not in (resp if isinstance(resp, dict) else {}):
        return idx, None, f"HTTP {code}: {resp}"
    op = resp["name"]
    (OUT / f"clip-{idx:02d}.opname").write_text(op)
    return idx, op, None


def poll_one(idx, opname, token):
    out_mp4 = OUT / f"clip-{idx:02d}.mp4"
    if out_mp4.exists():
        return idx, "exists"
    code, resp = http(f"{ENDPOINT}:fetchPredictOperation", token, body={"operationName": opname})
    if code != 200:
        return idx, f"poll HTTP {code}"
    if not resp.get("done"):
        return idx, "pending"
    err = resp.get("error")
    if err:
        return idx, f"ERROR: {err}"
    preds = resp.get("response", {}).get("videos", [])
    if not preds:
        return idx, f"no videos"
    b64 = preds[0].get("bytesBase64Encoded")
    if b64:
        out_mp4.write_bytes(base64.b64decode(b64))
        return idx, f"saved clip-{idx:02d}.mp4"
    return idx, "unknown response"


def main():
    todo = list(SUBJECTS.keys())  # [8, 14, 17, 23, 29, 30]
    print(f"Regenerating clips: {todo}")
    print(f"Archive: {ARCHIVE}")
    token = mint_token()
    ops = {}
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = [ex.submit(submit_one, i, token) for i in todo]
        for fut in as_completed(futs):
            idx, op, err = fut.result()
            if err:
                print(f"  clip-{idx:02d} SUBMIT FAIL: {err}", file=sys.stderr)
            else:
                print(f"  clip-{idx:02d}: submitted")
                ops[idx] = op
    if not ops:
        return
    print(f"\nPolling {len(ops)} ops...")
    done = set()
    last_token = time.time()
    while len(done) < len(ops):
        if time.time() - last_token > 2400:
            token = mint_token()
            last_token = time.time()
        with ThreadPoolExecutor(max_workers=6) as ex:
            futs = {ex.submit(poll_one, i, op, token): i for i, op in ops.items() if i not in done}
            for fut in as_completed(futs):
                idx, status = fut.result()
                if status.startswith("saved") or status == "exists":
                    done.add(idx)
                    print(f"  clip-{idx:02d}: {status}")
                elif status.startswith("ERROR") or status.startswith("HTTP") or status.startswith("no videos"):
                    print(f"  clip-{idx:02d}: {status}", file=sys.stderr)
                    done.add(idx)
        if len(done) < len(ops):
            print(f"  {time.strftime('%H:%M:%S')} done {len(done)}/{len(ops)}")
            time.sleep(15)
    print("\n=== Done ===")


if __name__ == "__main__":
    main()
