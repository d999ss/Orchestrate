#!/usr/bin/env python3
"""Patch: regen SB2 clip-30 as a bookend to f01 (globe orbit + pull back).

Why: previous clip-30 used frame-29.png (audience + screen) which duplicated
clip-29 visually. The journey arc is best closed by returning to the globe
where it started — same move SB3 makes naturally.
"""
import os, sys, json, time, base64, pathlib, ssl, urllib.request, urllib.error, io
import certifi
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

# Bookend finale: the globe from frame-01 is now FULLY lit, every continent
# connected by glowing arcs. Camera orbits slowly and pulls back to reveal
# the planet at full scale — the journey's destination is the planet itself.
PROMPT = (
    "A glowing cyan globe floats in deep darkness. Every continent is fully "
    "lit, connected by arcs of cyan light forming a complete network around "
    "the planet. The grid is alive. Camera slowly orbits the globe while "
    "pulling back to reveal its full scale — the journey's bookend, the "
    "planet running on the grid."
)


def crop_16_9_b64(p: pathlib.Path) -> str:
    img = Image.open(p).convert("RGB")
    w, h = img.size
    target_h = int(round(w * 9 / 16))
    if target_h < h:
        top = (h - target_h) // 2
        img = img.crop((0, top, w, top + target_h))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def http(url, token, body):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=120, context=SSL_CTX) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try: body = json.loads(body)
        except Exception: pass
        return e.code, body


def main():
    creds = service_account.Credentials.from_service_account_file(
        SA_KEY, scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(Request())
    token = creds.token

    src = ROOT / "storyboard-2" / "frame-01.png"
    out = ROOT / "films" / "sb2_clips" / "clip-30.mp4"
    b64 = crop_16_9_b64(src)

    payload = {
        "instances": [{
            "prompt": STYLE + PROMPT,
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
    if code != 200:
        print(f"submit failed: {code} {resp}", file=sys.stderr); sys.exit(1)
    opname = resp["name"]
    print(f"submitted clip-30 (frame-01 bookend): {opname}")

    while True:
        code, r = http(f"{ENDPOINT}:fetchPredictOperation", token, {"operationName": opname})
        if code != 200:
            print(f"poll failed: {code} {r}", file=sys.stderr); sys.exit(1)
        if r.get("done"):
            break
        time.sleep(15)
        print(f"  polling {time.strftime('%H:%M:%S')}")

    if r.get("error"):
        print(f"ERROR: {r['error']}", file=sys.stderr); sys.exit(1)
    videos = r.get("response", {}).get("videos", [])
    if not videos:
        print("no videos in response", file=sys.stderr); sys.exit(1)
    out.write_bytes(base64.b64decode(videos[0]["bytesBase64Encoded"]))
    print(f"saved {out} ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
