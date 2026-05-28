#!/usr/bin/env python3
"""Generate 8 Veo 3.0-fast image-to-video clips for Storyboard 1.

Each clip: 8s, 1080p, 16:9, no Veo audio. Submits in parallel, polls, downloads.
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

CLIPS = [
    ("01", "Locked-off camera, tripod-mounted, completely static frame. No pan, tilt, zoom, dolly, or shake. A glowing globe floats in deep darkness. City lights twinkle on one by one across the world map, faint cyan-white. Subtle drifting particles. Cold cinematic palette. Photoreal, broadcast film quality."),
    ("05", "Locked-off camera, completely static frame. Massive turbine rotor blades in a brightly-lit hot air stream. Blades accelerate from slow rotation to high speed, motion blur intensifying. Cold blue-white industrial light. Hyperreal mechanical detail, sparks of heat haze. Photoreal."),
    ("09", "Locked-off camera, completely static frame. Glowing cyan-white electricity travels through a network of polished conductors and busbars. Pulses of energy move smoothly across the frame. Macro detail, dark industrial background. Photoreal, cinematic."),
    ("13", "Locked-off camera, completely static aerial top-down. A regional electrical grid revealed as a glowing cyan network across dark terrain. Lines pulse outward in synchronized waves from substations. Subtle drift of overlaid data. Photoreal, cinematic."),
    ("17", "Locked-off camera, completely static wide. Distant Atlanta skyline at night. Lights surge brighter in cascading waves across the city as power flows in. Subtle cyan grid lines tracing the network. Dramatic dynamic range, photoreal."),
    ("21", "Locked-off camera, completely static aerial wide of an Atlanta-style stadium at night. Stadium bowl lights bloom on in a rolling sequence across the seating sections. Dust and atmospheric haze. Photoreal, cinematic."),
    ("25", "Locked-off camera, completely static. Modern conference center exterior at night. Interior lights cascade on floor by floor, top to bottom, in synchronized waves. Cold cyan-white glow through glass. Photoreal, hyperreal architectural detail."),
    ("29", "Locked-off camera, completely static. A wide reveal: dark keynote stage in foreground glowing cyan-white, illuminated Atlanta cityscape stretching behind through a vast window. Slow particle bloom around the GE Vernova brand mark center frame. Reverent, hero, photoreal."),
]


def mint_token():
    creds = service_account.Credentials.from_service_account_file(
        SA_KEY, scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    creds.refresh(Request())
    return creds.token


def http(url, token, body=None, method="GET"):
    headers = {"Authorization": f"Bearer {token}"}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
        if method == "GET":
            method = "POST"
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


def submit_one(idx, frame_id, prompt, token):
    img_path = ROOT / "storyboard-1" / f"frame-{frame_id}.png"
    if not img_path.exists():
        return idx, None, f"missing {img_path}"
    b64 = base64.b64encode(img_path.read_bytes()).decode()
    payload = {
        "instances": [
            {
                "prompt": prompt,
                "image": {"bytesBase64Encoded": b64, "mimeType": "image/png"},
            }
        ],
        "parameters": {
            "aspectRatio": "16:9",
            "durationSeconds": 8,
            "sampleCount": 1,
            "resolution": "1080p",
            "personGeneration": "allow_all",
            "generateAudio": False,
        },
    }
    code, resp = http(f"{ENDPOINT}:predictLongRunning", token, body=payload, method="POST")
    if code != 200 or not isinstance(resp, dict) or "name" not in resp:
        return idx, None, f"HTTP {code}: {resp}"
    op = resp["name"]
    (OUT / f"clip-{idx}.opname").write_text(op)
    return idx, op, None


def poll_one(idx, opname, token):
    out_mp4 = OUT / f"clip-{idx}.mp4"
    if out_mp4.exists():
        return idx, "exists"
    code, resp = http(f"{ENDPOINT}:fetchPredictOperation", token,
                       body={"operationName": opname}, method="POST")
    if code != 200:
        return idx, f"poll HTTP {code}: {resp}"
    if not resp.get("done"):
        return idx, "pending"
    err = resp.get("error")
    if err:
        return idx, f"ERROR: {err}"
    preds = resp.get("response", {}).get("videos", [])
    if not preds:
        return idx, f"no videos in resp: {resp.get('response')}"
    p = preds[0]
    b64 = p.get("bytesBase64Encoded")
    if b64:
        out_mp4.write_bytes(base64.b64decode(b64))
        return idx, f"saved {out_mp4.name}"
    gcs = p.get("gcsUri")
    if gcs:
        return idx, f"gcsUri (not yet supported): {gcs}"
    return idx, f"unknown pred: {list(p.keys())}"


def main():
    print(f"=== Submitting 8 Veo {MODEL} ops in parallel ===")
    token = mint_token()
    ops = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = [ex.submit(submit_one, i + 1, f, p, token) for i, (f, p) in enumerate(CLIPS)]
        for fut in as_completed(futs):
            idx, op, err = fut.result()
            if err:
                print(f"  clip {idx}: SUBMIT FAIL {err}", file=sys.stderr)
            else:
                print(f"  clip {idx}: submitted {op.split('/')[-1][:12]}")
                ops[idx] = op
    if not ops:
        print("No ops submitted, aborting.", file=sys.stderr)
        sys.exit(1)

    print(f"\n=== Polling {len(ops)} ops until done ===")
    done = set()
    last_token = time.time()
    while len(done) < len(ops):
        if time.time() - last_token > 2400:  # 40min
            token = mint_token()
            last_token = time.time()
        with ThreadPoolExecutor(max_workers=8) as ex:
            futs = {ex.submit(poll_one, i, op, token): i for i, op in ops.items() if i not in done}
            for fut in as_completed(futs):
                idx, status = fut.result()
                if status.startswith("saved") or status == "exists":
                    done.add(idx)
                    print(f"  clip {idx}: {status}")
                elif status.startswith("ERROR") or status.startswith("HTTP") or status.startswith("no videos"):
                    print(f"  clip {idx}: {status}", file=sys.stderr)
                    done.add(idx)  # don't loop on permanent fail
        if len(done) < len(ops):
            ts = time.strftime("%H:%M:%S")
            print(f"  {ts} done {len(done)}/{len(ops)} …")
            time.sleep(15)

    print("\n=== Done ===")
    for mp4 in sorted(OUT.glob("clip-*.mp4")):
        print(f"  {mp4.name}  {mp4.stat().st_size//1024} KB")


if __name__ == "__main__":
    main()
