#!/usr/bin/env python3
"""Truly sequential Veo generation — submit ONE clip, poll until done, next.

Slow (~50s per clip avg) but immune to concurrent-job rate limits.
Idempotent — skips clips that already exist.

Usage:
  .venv/bin/python scripts/gen_one_by_one.py <sb_num>   # SB2 or SB3
  .venv/bin/python scripts/gen_one_by_one.py 23         # both SB2 and SB3
"""
import os, sys, json, time, base64, pathlib, ssl, urllib.request, urllib.error
import certifi
from google.oauth2 import service_account
from google.auth.transport.requests import Request

SSL_CTX = ssl.create_default_context(cafile=certifi.where())
ROOT = pathlib.Path(__file__).resolve().parent.parent

PROJECT = "orchestrate-veo"
LOCATION = "us-central1"
SA_KEY = os.path.expanduser("~/.claude/secrets/veo-runner-key.json")
MODEL = "veo-3.0-fast-generate-001"
ENDPOINT = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT}/locations/{LOCATION}/publishers/google/models/{MODEL}"

# Reuse style from gen_sb2_sb3.py
sys.path.insert(0, str(ROOT / "scripts"))
from gen_sb2_sb3 import STYLE, SB2, SB3


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


def submit(sb, idx, prompt, token):
    img_path = ROOT / f"storyboard-{sb}" / f"frame-{idx:02d}.png"
    b64 = base64.b64encode(img_path.read_bytes()).decode()
    payload = {
        "instances": [{"prompt": STYLE + prompt, "image": {"bytesBase64Encoded": b64, "mimeType": "image/png"}}],
        "parameters": {
            "aspectRatio": "16:9",
            "durationSeconds": 4,
            "sampleCount": 1,
            "resolution": "1080p",
            "personGeneration": "allow_all",
            "generateAudio": False,
        },
    }
    return http(f"{ENDPOINT}:predictLongRunning", token, payload)


def gen_one(sb, idx, prompt, token):
    out_mp4 = ROOT / "films" / f"sb{sb}_clips" / f"clip-{idx:02d}.mp4"
    if out_mp4.exists():
        return "exists"

    # Submit with retry on 429
    backoff = 30
    op = None
    for attempt in range(8):
        code, resp = submit(sb, idx, prompt, token)
        if code == 200 and "name" in resp:
            op = resp["name"]
            break
        is_429 = code == 429 or (isinstance(resp, dict) and "RESOURCE_EXHAUSTED" in json.dumps(resp))
        if is_429:
            sys.stdout.write(f" 429 (wait {backoff}s)")
            sys.stdout.flush()
            time.sleep(backoff)
            backoff = min(backoff + 30, 180)
            continue
        return f"SUBMIT FAIL {code}: {resp}"

    if not op:
        return "FAILED after 8 attempts"

    # Poll until done
    poll_count = 0
    while True:
        time.sleep(8)
        poll_count += 1
        code, r = http(f"{ENDPOINT}:fetchPredictOperation", token, {"operationName": op})
        if code != 200:
            return f"POLL FAIL {code}"
        if r.get("done"):
            break
        if poll_count > 60:
            return "POLL TIMEOUT (>8min)"

    if r.get("error"):
        return f"ERROR {r['error']}"
    preds = r.get("response", {}).get("videos", [])
    if not preds:
        return "NO VIDEOS"
    b64 = preds[0].get("bytesBase64Encoded")
    if not b64:
        return "NO BYTES"
    out_mp4.write_bytes(base64.b64decode(b64))
    return f"saved {out_mp4.stat().st_size//1024}KB"


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "23"
    todo = []
    if "2" in target:
        for i in range(1, 31):
            todo.append(("2", i, SB2[i]))
    if "3" in target:
        for i in range(1, 31):
            todo.append(("3", i, SB3[i]))

    # Filter out already-existing
    pending = [(sb, i, p) for sb, i, p in todo if not (ROOT / "films" / f"sb{sb}_clips" / f"clip-{i:02d}.mp4").exists()]
    print(f"Need {len(pending)} clips · skipping {len(todo)-len(pending)} existing")

    token = mint_token()
    last_token = time.time()
    for n, (sb, idx, prompt) in enumerate(pending, 1):
        if time.time() - last_token > 2400:
            token = mint_token()
            last_token = time.time()
        sys.stdout.write(f"[{n}/{len(pending)}] sb{sb}/clip-{idx:02d}…")
        sys.stdout.flush()
        result = gen_one(sb, idx, prompt, token)
        print(f" {result}")

    print("=== Done ===")


if __name__ == "__main__":
    main()
