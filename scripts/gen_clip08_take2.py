#!/usr/bin/env python3
"""Regen clip-08 again — first new version came back as kaleidoscope.

Explicit anti-symmetry prompt this time. Goal: looks like a real photograph
of a real generator, no mirror artifacts.
"""
import os, sys, json, time, base64, pathlib, ssl, urllib.request, urllib.error
import certifi
from google.oauth2 import service_account
from google.auth.transport.requests import Request

SSL_CTX = ssl.create_default_context(cafile=certifi.where())
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "films" / "sb1_clips"
ARCHIVE = OUT / "kaleidoscope_archive"
ARCHIVE.mkdir(exist_ok=True)

PROJECT = "orchestrate-veo"
LOCATION = "us-central1"
SA_KEY = os.path.expanduser("~/.claude/secrets/veo-runner-key.json")
MODEL = "veo-3.0-fast-generate-001"
ENDPOINT = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT}/locations/{LOCATION}/publishers/google/models/{MODEL}"

PROMPT = (
    "Documentary cinematography. Asymmetric composition, NO mirror symmetry, "
    "NO kaleidoscope, NO reflection, NO repeated patterns. "
    "Wide-angle cinematic view inside a hydroelectric or steam power plant generator hall. "
    "Massive cylindrical industrial generator unit photographed from a slight angle. "
    "Visible bright copper stator windings wrapped around the rotor. "
    "Industrial grey concrete floor, yellow safety railings, overhead lighting. "
    "Subtle cyan-white internal glow from the active generator. "
    "Slight steam venting. Catwalks visible. Photoreal, documentary, broadcast quality. "
    "Locked-off camera, static frame. "
    "ABSOLUTELY NO TEXT, NO LOGOS, NO WORDS, NO BRAND MARKS anywhere in frame."
)


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


def main():
    token = mint_token()
    out_mp4 = OUT / "clip-08.mp4"
    if out_mp4.exists():
        arch = ARCHIVE / out_mp4.name
        if arch.exists():
            out_mp4.unlink()
        else:
            out_mp4.rename(arch)
        print(f"Archived current clip-08.mp4 to {arch}")

    payload = {
        "instances": [{"prompt": PROMPT}],
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
    if code != 200:
        print(f"SUBMIT FAIL: {code} {resp}", file=sys.stderr)
        return 1
    op = resp["name"]
    print(f"Submitted: {op.split('/')[-1][:16]}")
    while True:
        code, r = http(f"{ENDPOINT}:fetchPredictOperation", token, {"operationName": op})
        if r.get("done"):
            break
        time.sleep(10)
        print(f"  {time.strftime('%H:%M:%S')} pending...")
    if r.get("error"):
        print(f"ERROR: {r['error']}", file=sys.stderr)
        return 1
    b64 = r["response"]["videos"][0]["bytesBase64Encoded"]
    out_mp4.write_bytes(base64.b64decode(b64))
    print(f"saved {out_mp4} ({out_mp4.stat().st_size//1024} KB)")


if __name__ == "__main__":
    sys.exit(main() or 0)
