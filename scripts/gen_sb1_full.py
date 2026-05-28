#!/usr/bin/env python3
"""Generate Veo 3.0-fast clips for ALL 30 Storyboard-1 frames.

Unified style frame applied to every clip for cohesion:
  - Locked-off tripod camera, no pan/tilt/zoom/dolly/shake
  - Cold cyan-white industrial cinematography
  - Photoreal, broadcast film quality, anamorphic widescreen
  - Subject motion only (within-frame); same color grade across all 30

Frames 1, 5, 9, 13, 17, 21, 25, 29 already generated in films/sb1_clips/.
This script ONLY generates the missing 22 (idempotent: skips existing clip-NN.mp4).

Each clip: 4s (Veo min, for tight cuts), 1080p, 16:9, no Veo audio.
"""
import os, sys, json, time, base64, pathlib, ssl, urllib.request, urllib.error
import certifi
from concurrent.futures import ThreadPoolExecutor, as_completed
from google.oauth2 import service_account
from google.auth.transport.requests import Request

SSL_CTX = ssl.create_default_context(cafile=certifi.where())

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "films" / "sb1_clips"
OUT.mkdir(parents=True, exist_ok=True)

PROJECT = os.environ.get("GCP_PROJECT", "orchestrate-veo")
LOCATION = os.environ.get("GCP_LOCATION", "us-central1")
SA_KEY = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS",
                         os.path.expanduser("~/.claude/secrets/veo-runner-key.json"))
MODEL = "veo-3.0-fast-generate-001"
ENDPOINT = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT}/locations/{LOCATION}/publishers/google/models/{MODEL}"

# Unified style frame — same on every clip for cohesion
STYLE = (
    "Locked-off camera, tripod-mounted, completely static frame. "
    "No pan, tilt, zoom, dolly, parallax, or camera shake. "
    "Cold cyan-white industrial cinematography, broadcast film quality, "
    "anamorphic widescreen, photoreal, hyperreal detail, "
    "subtle drifting particles, deep shadow contrast. "
    "Subject motion only within the frame. "
)

# Per-frame subject motion (matches storyboard-1 narrative beats 1-30)
SUBJECTS = {
    1:  "A glowing cyan globe floats in deep darkness. City lights twinkle on one by one across continents.",
    2:  "The camera holds. Globe transitions into a modern hyperscale energy facility, lights flickering on across the structure.",
    3:  "A massive turbine couples to a generator; the shaft begins rotating, mechanical coupling tightening.",
    4:  "Inside a turbine combustion chamber: natural gas igniting in a perfect ring of blue-white flame.",
    5:  "Hot air streams through massive turbine rotor blades; blades accelerate, motion blur intensifies.",
    6:  "The turbine spins faster and faster, mechanical detail blurring into pure motion.",
    7:  "Inside the generator: rotor parts spinning rapidly, polished surfaces blurring.",
    8:  "Macro shot of generator magnets; electromagnetic field lines pulsing into existence as electricity forms.",
    9:  "Glowing cyan-white electricity travels through polished conductors and busbars in pulses of energy.",
    10: "Electricity flows from generator output into the high-voltage power grid switchyard at night.",
    11: "Macro of high-voltage transformers humming under load; insulators glowing slightly, cooling fins shimmering.",
    12: "Aerial dolly-free view: transmission lines stretching across dark countryside, carrying glowing cyan energy.",
    13: "Aerial top-down: the regional electrical grid revealed as a glowing cyan network across dark terrain.",
    14: "Grid control overlay: cyan data trails routing across the network, lines redirecting power dynamically.",
    15: "Modern grid control room at night, operators silhouetted against curved ultrawide displays of live data.",
    16: "Aerial wide: southeastern US at night, the power network glowing across multiple states in cyan filigree.",
    17: "Aerial: cyan energy pulses concentrating, flowing toward an Atlanta-style city skyline in the distance.",
    18: "Wide cinematic: transmission lines lead into a brightly-lit city at night, cyan glow surging along them.",
    19: "Distant Atlanta skyline at night begins lighting up in cascading waves, buildings turning on block by block.",
    20: "Wider city view: buildings, roads, and infrastructure activating across the city, light spreading outward.",
    21: "Aerial wide of a downtown stadium at night, becoming the brightest point in the city, lighting up.",
    22: "Wide tracking-free view: glowing cyan energy pulses flow visibly into the stadium structure.",
    23: "Inside the stadium bowl: the stadium lights bloom on in a rolling sequence across all seating sections.",
    24: "Wider view: the surrounding downtown area lights up, buildings glowing brighter in synchronized waves.",
    25: "Modern conference center exterior at night: interior lights cascade on floor by floor, top to bottom.",
    26: "Wide interior atrium of the conference center: ceiling lights, signage, and architectural details activating.",
    27: "Inside the keynote hall: ambient house lights coming up, scale of the room becoming visible.",
    28: "Keynote stage: stage lights ignite, towering immersive curved LED screens flickering to life with cyan visuals.",
    29: "Aerial pull-back reveal: keynote room foreground glowing cyan-white, illuminated Atlanta cityscape beyond.",
    30: "The fully-powered keynote room from inside, immersive LED screens glowing softly with the GE Vernova brand mark.",
}


def mint_token():
    creds = service_account.Credentials.from_service_account_file(
        SA_KEY, scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    creds.refresh(Request())
    return creds.token


def http(url, token, body=None, method="POST"):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120, context=SSL_CTX) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            body = json.loads(body)
        except Exception:
            pass
        return e.code, body


def submit_one(idx, token):
    out_mp4 = OUT / f"clip-{idx:02d}.mp4"
    if out_mp4.exists():
        return idx, None, "exists"
    img_path = ROOT / "storyboard-1" / f"frame-{idx:02d}.png"
    if not img_path.exists():
        return idx, None, f"missing {img_path}"
    b64 = base64.b64encode(img_path.read_bytes()).decode()
    prompt = STYLE + SUBJECTS.get(idx, "Locked-off subject motion within the frame.")
    payload = {
        "instances": [
            {"prompt": prompt, "image": {"bytesBase64Encoded": b64, "mimeType": "image/png"}}
        ],
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
    if code != 200 or not isinstance(resp, dict) or "name" not in resp:
        return idx, None, f"HTTP {code}: {resp}"
    op = resp["name"]
    (OUT / f"clip-{idx:02d}.opname").write_text(op)
    return idx, op, None


def poll_one(idx, opname, token):
    out_mp4 = OUT / f"clip-{idx:02d}.mp4"
    if out_mp4.exists():
        return idx, "exists"
    code, resp = http(f"{ENDPOINT}:fetchPredictOperation", token,
                       body={"operationName": opname})
    if code != 200:
        return idx, f"poll HTTP {code}: {resp}"
    if not resp.get("done"):
        return idx, "pending"
    err = resp.get("error")
    if err:
        return idx, f"ERROR: {err}"
    preds = resp.get("response", {}).get("videos", [])
    if not preds:
        return idx, f"no videos: {resp.get('response')}"
    p = preds[0]
    b64 = p.get("bytesBase64Encoded")
    if b64:
        out_mp4.write_bytes(base64.b64decode(b64))
        return idx, f"saved clip-{idx:02d}.mp4"
    return idx, f"unknown pred: {list(p.keys())}"


def main():
    # Normalize: rename old single-digit clip files to two-digit naming
    for i in (1, 2, 3, 4, 5, 6, 7, 8):
        old = OUT / f"clip-{i}.mp4"
        if old.exists():
            new = OUT / f"clip-{[1,5,9,13,17,21,25,29][i-1]:02d}.mp4"
            if not new.exists():
                old.rename(new)
                print(f"renamed {old.name} -> {new.name}")

    todo = [i for i in range(1, 31) if not (OUT / f"clip-{i:02d}.mp4").exists()]
    if not todo:
        print("All 30 clips already present.")
        return
    print(f"=== Submitting {len(todo)} Veo {MODEL} ops (4s each, 1080p) ===")
    print(f"Frames: {todo}")
    token = mint_token()
    ops = {}
    with ThreadPoolExecutor(max_workers=10) as ex:
        futs = [ex.submit(submit_one, i, token) for i in todo]
        for fut in as_completed(futs):
            idx, op, err = fut.result()
            if err == "exists":
                continue
            if err:
                print(f"  clip {idx:02d}: SUBMIT FAIL {err}", file=sys.stderr)
            else:
                print(f"  clip {idx:02d}: submitted {op.split('/')[-1][:12]}")
                ops[idx] = op
    if not ops:
        print("Nothing to submit.")
        return

    print(f"\n=== Polling {len(ops)} ops until done ===")
    done = set()
    last_token = time.time()
    while len(done) < len(ops):
        if time.time() - last_token > 2400:
            token = mint_token()
            last_token = time.time()
        with ThreadPoolExecutor(max_workers=10) as ex:
            futs = {ex.submit(poll_one, i, op, token): i for i, op in ops.items() if i not in done}
            for fut in as_completed(futs):
                idx, status = fut.result()
                if status.startswith("saved") or status == "exists":
                    done.add(idx)
                    print(f"  clip {idx:02d}: {status}")
                elif status.startswith("ERROR") or status.startswith("HTTP") or status.startswith("no videos"):
                    print(f"  clip {idx:02d}: {status}", file=sys.stderr)
                    done.add(idx)
        if len(done) < len(ops):
            print(f"  {time.strftime('%H:%M:%S')} done {len(done)}/{len(ops)} …")
            time.sleep(15)

    print("\n=== Done ===")
    for mp4 in sorted(OUT.glob("clip-*.mp4")):
        print(f"  {mp4.name}  {mp4.stat().st_size//1024} KB")


if __name__ == "__main__":
    main()
