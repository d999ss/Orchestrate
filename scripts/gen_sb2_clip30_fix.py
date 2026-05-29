#!/usr/bin/env python3
"""Patch: regen clip-30 from frame-29.png source.

Why: storyboard-2/frame-30.png has "ORCHESTRATE 2026 / GridOS Customer
Conference / GE VERNOVA" text + logo baked in. Veo image-to-video preserves
those marks, which violates the no-text rule. Frame-29.png is the audience
silhouette + glowing screen with the globe — no text — and works as a finale
when the camera pushes in toward the screen instead of laterally dollying
(clip-29's motion).
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

# Use frame-29 source. Camera pushes IN toward the glowing screen as the
# climax. Clip-29 dollies laterally; clip-30 zooms forward = crescendo.
PROMPT = (
    "A vast keynote hall, audience silhouetted in the foreground, a glowing cyan "
    "globe on the curved keynote screen in the distance. The globe pulses with "
    "directed energy. Camera pushes slowly forward through the audience toward "
    "the glowing screen — the final destination of the journey."
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

    src = ROOT / "storyboard-2" / "frame-29.png"  # NOT frame-30 — text-free
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
    print(f"submitted clip-30 (frame-29 source): {opname}")

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
