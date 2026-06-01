#!/usr/bin/env python3
"""Regen 8 hero SB1 clips with KINETIC motion · same art direction.

Constraints (must preserve):
- Stylized concept-art aesthetic from the original storyboard PNG
- Cyan-on-deep-black palette
- Painterly NOT documentary
- Particle/constellation overlay vibe

Add:
- Camera push-ins, dolly motion, rapid tracking
- Explosive/kinetic subject motion
- Lightning BOLTS (not painterly arcs) on the electricity clip

Image-to-video off the existing storyboard PNG so aesthetic stays locked.
"""
import os, sys, json, time, base64, pathlib, ssl, urllib.request, urllib.error
import certifi
from concurrent.futures import ThreadPoolExecutor, as_completed
from google.oauth2 import service_account
from google.auth.transport.requests import Request

SSL_CTX = ssl.create_default_context(cafile=certifi.where())
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "films" / "sb1_clips"
ARCHIVE = OUT / "v23_static_archive"
ARCHIVE.mkdir(exist_ok=True)

PROJECT = "orchestrate-veo"
LOCATION = "us-central1"
SA_KEY = os.path.expanduser("~/.claude/secrets/veo-runner-key.json")
MODEL = "veo-3.0-fast-generate-001"
ENDPOINT = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT}/locations/{LOCATION}/publishers/google/models/{MODEL}"

# Style lock — keeps the cyan/painterly look while ALLOWING camera motion
STYLE = (
    "Maintain the EXACT cyan-on-deep-black painterly concept-art aesthetic of "
    "the reference image. Stylized, atmospheric, particle-painted look. NOT "
    "documentary photorealism. Constellation network dots, cyan emissive glow. "
    "ABSOLUTELY NO TEXT, NO LOGOS, NO WORDS, NO LETTERS in any frame. "
)

# Motion-explicit per-frame prompts. Camera moves + kinetic subject action.
SUBJECTS = {
    2:  "Rapid cinematic camera push-in toward a hyperscale energy facility. "
        "The structure rushes closer as the camera accelerates. "
        "Lights ignite across the facility in a cascading wave as it grows in frame. "
        "Cyan particles streak past the camera. Kinetic forward motion.",

    4:  "Explosive blue-white combustion erupts in a perfect ring of fire inside a turbine chamber. "
        "Flames blast outward at high speed. Heat shockwave distortion. Cyan sparks burst radially. "
        "The fire is alive, aggressive, kinetic. Particles fly outward from the center.",

    9:  "BOLTS of high-voltage LIGHTNING arc and crackle through copper conductors. "
        "Branching electrical discharges jump between wires with violent intensity. "
        "Bright cyan-white plasma bolts forking like real lightning, not soft glow. "
        "Sparks shower outward at the junctions. Crackling kinetic energy.",

    13: "Fast aerial flyover across a vast cyan-lit power grid network at night. "
        "The camera tracks rapidly across glowing transmission corridors. "
        "Motion blur on distant grid nodes. Particles streak past at speed. "
        "Dynamic forward velocity across the terrain.",

    19: "Rapid cinematic zoom-in toward Atlanta as the city ignites. "
        "Skyline accelerates closer to the camera. Buildings light up in a cascading wave, "
        "block by block, racing toward the viewer. Cyan energy pulses flow into the city. "
        "Kinetic forward push.",

    21: "Aerial dolly-out over a downtown stadium at night. "
        "The stadium dome blazes with cyan light as the camera ascends. "
        "Surrounding city lights spread outward. Particles drift past the camera. "
        "Smooth elevating cinematic motion.",

    27: "Cinematic camera push-in down a vast keynote hall toward the distant stage. "
        "Ambient cyan house lights warm up as the camera glides forward. "
        "Seats blur past on either side. The stage at the focal point grows brighter. "
        "Forward dolly motion with depth-of-field.",

    28: "Stage lights ERUPT outward at peak intensity. "
        "Cyan-white beams blast forward toward the camera. "
        "Lens flares punching the lens. The curved LED screen behind explodes with light. "
        "Particles, smoke, and energy radiate outward. Climactic kinetic impact.",
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


def submit(idx, token):
    out_mp4 = OUT / f"clip-{idx:02d}.mp4"
    # Archive current
    arch = ARCHIVE / out_mp4.name
    if out_mp4.exists() and not arch.exists():
        out_mp4.rename(arch)
    elif out_mp4.exists():
        out_mp4.unlink()
    img_path = ROOT / "storyboard-1" / f"frame-{idx:02d}.png"
    b64 = base64.b64encode(img_path.read_bytes()).decode()
    payload = {
        "instances": [{
            "prompt": STYLE + SUBJECTS[idx],
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
    return http(f"{ENDPOINT}:predictLongRunning", token, payload)


def poll(idx, op, token):
    out_mp4 = OUT / f"clip-{idx:02d}.mp4"
    if out_mp4.exists():
        return idx, "exists"
    code, r = http(f"{ENDPOINT}:fetchPredictOperation", token, {"operationName": op})
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
    return idx, "unknown"


def main():
    todo = list(SUBJECTS.keys())
    print(f"Regenerating {len(todo)} hero clips with motion: {todo}")
    token = mint_token()
    ops = {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = [ex.submit(submit, i, token) for i in todo]
        for fut in as_completed(futs):
            try:
                code, resp = fut.result()
                if code == 200 and "name" in resp:
                    idx = None
                    for i in todo:
                        if str(i) in resp.get("name", ""):  # imperfect; track via submit result
                            pass
                    # Simpler: re-iterate
            except Exception as e:
                print(f"  submit fail: {e}", file=sys.stderr)
    # Use a different approach for tracking ops:
    ops.clear()
    print("Re-submitting one-by-one with op tracking...")
    for idx in todo:
        out_mp4 = OUT / f"clip-{idx:02d}.mp4"
        if out_mp4.exists():
            continue
        code, resp = submit(idx, token)
        if code == 200 and "name" in resp:
            ops[idx] = resp["name"]
            print(f"  clip-{idx:02d}: submitted")
            time.sleep(2)
        elif code == 429:
            print(f"  clip-{idx:02d}: 429, waiting 30s")
            time.sleep(30)
            code, resp = submit(idx, token)
            if code == 200 and "name" in resp:
                ops[idx] = resp["name"]
                print(f"  clip-{idx:02d}: submitted (retry)")
            else:
                print(f"  clip-{idx:02d}: FAIL {code}", file=sys.stderr)
        else:
            print(f"  clip-{idx:02d}: FAIL {code} {resp}", file=sys.stderr)

    print(f"\nPolling {len(ops)} ops...")
    done = set()
    while len(done) < len(ops):
        for idx, op in list(ops.items()):
            if idx in done: continue
            i, status = poll(idx, op, token)
            if status.startswith("saved") or status == "exists":
                done.add(idx)
                print(f"  clip-{idx:02d}: {status}")
            elif "ERROR" in status or "HTTP" in status or "no videos" in status:
                print(f"  clip-{idx:02d}: {status}", file=sys.stderr)
                done.add(idx)
        if len(done) < len(ops):
            time.sleep(10)
    print("\n=== Done ===")


if __name__ == "__main__":
    main()
