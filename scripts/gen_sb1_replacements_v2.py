#!/usr/bin/env python3
"""Regen the 6 SB1 replacements — TAKE 2.

Take 1 went documentary-realistic. Wrong art direction.
This take matches the established stylized cyan-on-deep-black aesthetic of
f01, f04, f09, f13 (the frames that work). Single iconic subject in negative
space, abstract energy, network/particle overlays, painterly NOT photoreal.
"""
import os, sys, json, time, base64, pathlib, ssl, urllib.request, urllib.error
import certifi
from concurrent.futures import ThreadPoolExecutor, as_completed
from google.oauth2 import service_account
from google.auth.transport.requests import Request

SSL_CTX = ssl.create_default_context(cafile=certifi.where())
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "films" / "sb1_clips"
ARCHIVE = OUT / "take1_documentary"
ARCHIVE.mkdir(exist_ok=True)

PROJECT = "orchestrate-veo"
LOCATION = "us-central1"
SA_KEY = os.path.expanduser("~/.claude/secrets/veo-runner-key.json")
MODEL = "veo-3.0-fast-generate-001"
ENDPOINT = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT}/locations/{LOCATION}/publishers/google/models/{MODEL}"

# Style frame matches the existing legible/working frames (f01, f04, f09, f13).
# Stylized concept art. Cyan-white glow on deep black. Network/particle overlays.
# Single iconic subject in negative space. Painterly, NOT photoreal documentary.
STYLE = (
    "Stylized concept art aesthetic — NOT photoreal documentary. "
    "Deep black void background, single iconic subject isolated in negative space, "
    "subtle ambient particles and tiny constellation network dots scattered throughout. "
    "Cyan-white emissive glow from the subject itself. "
    "Painterly cinematic atmosphere, anamorphic widescreen, soft volumetric haze. "
    "Locked-off static camera, no pan, no tilt, no zoom, no kaleidoscope, no mirror symmetry, "
    "asymmetric composition. "
    "ABSOLUTELY NO TEXT, NO LOGOS, NO WORDS, NO LETTERS, NO BRAND MARKS anywhere in frame. "
)

SUBJECTS = {
    8:  "A single isolated industrial generator rotor element floating in deep void. "
        "Polished copper conductive bands visible, wrapping around a cylindrical core. "
        "Thin cyan-white filaments of electricity arc along the surface between the bands. "
        "Subtle particles drifting in foreground.",

    14: "Top-down isometric view of an abstract regional power grid on a deep black plane. "
        "Glowing cyan-white power lines connecting silhouetted lattice transmission towers, "
        "forming a sparse network across the dark surface. "
        "Continuous pulses of light travel along the lines. "
        "Faint constellation dots scattered across the plane.",

    17: "Wide composition: a single silhouetted lattice transmission tower in the foreground, "
        "cyan-white power line stretching from it across deep darkness toward a distant "
        "cluster of pinpoint city lights on the horizon. "
        "Energy pulses visibly traveling along the line toward the city cluster. "
        "Deep atmospheric haze, particles, no recognizable buildings.",

    23: "Top-down isometric view of a stylized stadium oval on a deep black plane. "
        "Glowing cyan-white rim outlining the stadium structure, central oval field "
        "blooming with bright cyan light, abstract crowd represented as scattered dots "
        "filling the seating area. Faint network lines radiate outward from the stadium "
        "across the dark plane.",

    29: "Stylized cross-section view of an empty auditorium interior. "
        "Curving rows of seat silhouettes recede into deep black void. "
        "A single bright cyan-white glow at the distant focal point representing the stage. "
        "Soft volumetric beams of cyan light reach out from the focal point. "
        "Particles drifting, painterly atmosphere.",

    30: "Hero shot: a single vertical pillar of cyan-white light rising from a stylized "
        "stage platform into a deep black void. "
        "Particles swirling around the pillar in zero gravity. "
        "The stage platform glows underneath. "
        "Triumphant, monumental, abstract finale composition.",
}


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


def submit_one(idx, token):
    out_mp4 = OUT / f"clip-{idx:02d}.mp4"
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
    code, resp = http(f"{ENDPOINT}:predictLongRunning", token, payload)
    if code != 200 or "name" not in (resp if isinstance(resp, dict) else {}):
        return idx, None, f"HTTP {code}: {resp}"
    return idx, resp["name"], None


def poll_one(idx, opname, token):
    out_mp4 = OUT / f"clip-{idx:02d}.mp4"
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
    todo = list(SUBJECTS.keys())
    print(f"Regenerating clips (take 2 — stylized): {todo}")
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
    print(f"\nPolling {len(ops)}...")
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
                elif "ERROR" in status or "HTTP" in status or "no videos" in status:
                    print(f"  clip-{idx:02d}: {status}", file=sys.stderr)
                    done.add(idx)
        if len(done) < len(ops):
            print(f"  {time.strftime('%H:%M:%S')} {len(done)}/{len(ops)}")
            time.sleep(15)
    print("=== Done ===")


if __name__ == "__main__":
    main()
