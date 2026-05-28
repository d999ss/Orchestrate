#!/usr/bin/env python3
"""Regenerate clip-01 at the 8s Veo max with continuous slow motion to fill the
8.98s intro hold without freezing.
"""
import os, sys, json, time, base64, pathlib, ssl, urllib.request, urllib.error
import certifi
from google.oauth2 import service_account
from google.auth.transport.requests import Request

SSL_CTX = ssl.create_default_context(cafile=certifi.where())

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "films" / "sb1_clips"
ARCHIVE = OUT / "v3_intro_short"
ARCHIVE.mkdir(exist_ok=True)

PROJECT = os.environ.get("GCP_PROJECT", "orchestrate-veo")
LOCATION = os.environ.get("GCP_LOCATION", "us-central1")
SA_KEY = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS",
                         os.path.expanduser("~/.claude/secrets/veo-runner-key.json"))
MODEL = "veo-3.0-fast-generate-001"
ENDPOINT = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT}/locations/{LOCATION}/publishers/google/models/{MODEL}"

PROMPT = (
    "ABSOLUTELY NO TEXT, NO LOGOS, NO WORDS, NO LABELS, NO PLACE NAMES. "
    "Static locked camera position, completely fixed lens, no pan, tilt, zoom, dolly, or shake. "
    "Cold cyan-white industrial cinematography, broadcast film quality, anamorphic widescreen, photoreal. "
    "A massive glowing cyan globe of Earth slowly and continuously rotates in deep space across the entire shot. "
    "City lights ignite one by one across continents in cascading waves throughout the duration — "
    "starting sparse, building to a dense network of pulsing nodes by the end. "
    "Drifting stardust particles continuously cross the frame. "
    "Continuous visible motion from first frame to last — never static, never frozen."
)


def mint_token():
    creds = service_account.Credentials.from_service_account_file(
        SA_KEY, scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
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


def main():
    out_mp4 = OUT / "clip-01.mp4"
    if out_mp4.exists():
        arch = ARCHIVE / "clip-01.mp4"
        if not arch.exists():
            out_mp4.rename(arch)
        else:
            out_mp4.unlink()
    img_path = ROOT / "storyboard-1" / "frame-01.png"
    b64 = base64.b64encode(img_path.read_bytes()).decode()

    token = mint_token()
    payload = {
        "instances": [{"prompt": PROMPT,
                       "image": {"bytesBase64Encoded": b64, "mimeType": "image/png"}}],
        "parameters": {
            "aspectRatio": "16:9",
            "durationSeconds": 8,
            "sampleCount": 1,
            "resolution": "1080p",
            "personGeneration": "allow_all",
            "generateAudio": False,
        },
    }
    code, resp = http(f"{ENDPOINT}:predictLongRunning", token, payload)
    if code != 200:
        print(f"submit fail {code}: {resp}", file=sys.stderr)
        sys.exit(1)
    opname = resp["name"]
    print(f"submitted {opname.split('/')[-1][:12]}")

    while True:
        code, resp = http(f"{ENDPOINT}:fetchPredictOperation", token,
                          {"operationName": opname})
        if not resp.get("done"):
            print(f"  {time.strftime('%H:%M:%S')} pending…")
            time.sleep(15)
            continue
        if resp.get("error"):
            print(f"ERROR: {resp['error']}", file=sys.stderr)
            sys.exit(1)
        videos = resp.get("response", {}).get("videos", [])
        if not videos or "bytesBase64Encoded" not in videos[0]:
            print(f"no video: {resp.get('response')}", file=sys.stderr)
            sys.exit(1)
        out_mp4.write_bytes(base64.b64decode(videos[0]["bytesBase64Encoded"]))
        print(f"saved {out_mp4}")
        break


if __name__ == "__main__":
    main()
