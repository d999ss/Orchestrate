#!/usr/bin/env python3
"""Fix the 4 SB1 clips with text/visual artifacts: 16, 26, 29, 30.

Adds explicit anti-text directive + replaces 'tripod' language with 'static camera position'
to prevent Veo from rendering a physical tripod in the frame.
"""
import os, sys, json, time, base64, pathlib, ssl, urllib.request, urllib.error
import certifi
from concurrent.futures import ThreadPoolExecutor, as_completed
from google.oauth2 import service_account
from google.auth.transport.requests import Request

SSL_CTX = ssl.create_default_context(cafile=certifi.where())

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "films" / "sb1_clips"
ARCHIVE = OUT / "v3_text_artifacts"
ARCHIVE.mkdir(exist_ok=True)

PROJECT = os.environ.get("GCP_PROJECT", "orchestrate-veo")
LOCATION = os.environ.get("GCP_LOCATION", "us-central1")
SA_KEY = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS",
                         os.path.expanduser("~/.claude/secrets/veo-runner-key.json"))
MODEL = "veo-3.0-fast-generate-001"
ENDPOINT = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT}/locations/{LOCATION}/publishers/google/models/{MODEL}"

# CRITICAL anti-artifact directive (front-loaded)
ANTI_TEXT = (
    "ABSOLUTELY NO TEXT, NO LOGOS, NO WORDS, NO LETTERS, NO NUMBERS, NO SIGNAGE, "
    "NO CAPTIONS, NO WATERMARKS, NO BRAND MARKS, NO PLACE NAMES, NO MAP LABELS, "
    "NO CITY NAMES, NO COMPANY NAMES. No GE, no Vernova, no Atlanta. "
    "No physical camera or tripod visible in the frame. "
)
CAM = ("Static locked camera position, completely fixed lens, no pan, tilt, zoom, dolly, "
       "parallax, or shake. Cold cyan-white industrial cinematography, broadcast film quality, "
       "anamorphic widescreen, photoreal, hyperreal detail. ")

SUBJECTS = {
    16: ("Aerial wide of the southeastern United States at night, the regional power grid "
         "visualized as a glowing cyan wireframe network pulsing across multiple states. Lines "
         "of energy flow inward toward a central density. ABSOLUTELY NO TEXT, NO PLACE NAMES, "
         "NO STATE LABELS, NO MAP LABELS, NO CITY NAMES."),
    26: ("Wide interior of a vast modern conference center atrium at night. Cathedral-tall "
         "geometric ceiling structure illuminated in cool cyan-white. The space is empty, "
         "polished concrete floor reflecting overhead architectural lights. Long converging "
         "perspective. ABSOLUTELY NO SIGNAGE, NO WAYFINDING, NO TEXT ON WALLS, NO LOGOS."),
    29: ("Pull-back aerial reveal: foreground a darkened keynote auditorium stage glowing "
         "cyan-white with kinetic abstract light patterns on a curved immersive LED wall. "
         "Background, through a vast wraparound window, an illuminated futuristic city "
         "skyline at night. Crowds visible only as silhouettes. ABSOLUTELY NO LOGOS, "
         "NO 'GE', NO 'VERNOVA', NO BRAND TEXT, NO COMPANY NAMES, NO PLACE NAMES."),
    30: ("Wide interior shot of a fully-illuminated keynote auditorium. The curved immersive "
         "LED screens behind the stage glow with abstract cyan-white geometric light patterns "
         "and particle constellations — purely visual, no text. The space is calm and grand. "
         "ABSOLUTELY NO LOGOS, NO BRAND MARKS, NO TEXT, NO WORDS ON THE SCREENS. "
         "Critically: NO PHYSICAL CAMERA, NO TRIPOD, NO PHOTOGRAPHIC EQUIPMENT VISIBLE in the frame."),
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
    img_path = ROOT / "storyboard-1" / f"frame-{idx:02d}.png"
    if not img_path.exists():
        return idx, None, f"missing {img_path}"
    if out_mp4.exists():
        arch = ARCHIVE / out_mp4.name
        if not arch.exists():
            out_mp4.rename(arch)
        else:
            out_mp4.unlink()
    b64 = base64.b64encode(img_path.read_bytes()).decode()
    prompt = ANTI_TEXT + CAM + SUBJECTS[idx]
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
    todo = list(SUBJECTS.keys())
    print(f"=== Regenerating {len(todo)} SB1 clips with anti-text directive ===")
    print(f"Frames: {todo}  (originals archived to {ARCHIVE.name}/)")
    token = mint_token()
    ops = {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = [ex.submit(submit_one, i, token) for i in todo]
        for fut in as_completed(futs):
            idx, op, err = fut.result()
            if err:
                print(f"  clip {idx:02d}: SUBMIT FAIL {err}", file=sys.stderr)
            else:
                print(f"  clip {idx:02d}: submitted {op.split('/')[-1][:12]}")
                ops[idx] = op
    if not ops:
        return

    print(f"\n=== Polling {len(ops)} ops ===")
    done = set()
    last_token = time.time()
    while len(done) < len(ops):
        if time.time() - last_token > 2400:
            token = mint_token()
            last_token = time.time()
        with ThreadPoolExecutor(max_workers=4) as ex:
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


if __name__ == "__main__":
    main()
