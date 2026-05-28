#!/usr/bin/env python3
"""Regenerate SB1 clips 1-10 with motion-explicit prompts.

Camera = tripod-locked (no pan/tilt/zoom)
Subject = kinetic and active (explicit verbs: spinning, surging, igniting, accelerating)
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
# Archive the static v2 clips before overwriting
ARCHIVE = OUT / "v2_static"
ARCHIVE.mkdir(exist_ok=True)

PROJECT = os.environ.get("GCP_PROJECT", "orchestrate-veo")
LOCATION = os.environ.get("GCP_LOCATION", "us-central1")
SA_KEY = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS",
                         os.path.expanduser("~/.claude/secrets/veo-runner-key.json"))
MODEL = "veo-3.0-fast-generate-001"
ENDPOINT = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT}/locations/{LOCATION}/publishers/google/models/{MODEL}"

# Camera grammar (consistent across all clips)
CAM = ("Camera mounted on a heavy tripod. No camera pan, tilt, zoom, dolly, parallax, "
       "or shake — the lens is absolutely fixed. Cold cyan-white industrial cinematography, "
       "broadcast film quality, anamorphic widescreen, photoreal, hyperreal detail. ")

# Per-frame SUBJECT motion — explicit kinetic verbs (the camera locked-down already enforced above)
SUBJECTS = {
    1:  "A massive glowing cyan globe rotates slowly in deep space. Hundreds of city lights pulse on across continents in cascading waves, each light igniting individually with a tiny flare. Particles of stardust drift across the frame. The globe rotation is visible and continuous.",
    2:  "Rapid cinematic zoom-in motion blur — the camera-perspective rushes from cosmic space toward a hyperscale energy facility on Earth. Lights inside the facility flicker on rapidly as the scale resolves. The entire structure surges with cyan-white power.",
    3:  "Massive turbine machinery actively rotating and engaging with a generator coupling. The rotor shaft visibly spins at high RPM, mechanical coupling tightening with visible torque. Steam vents, sparks, metallic vibration.",
    4:  "Inside a turbine combustion chamber, natural gas is actively igniting — flames erupting in a perfect blue-white ring of fire, propagating outward at speed. Heat haze distorting the frame. The fire is unmistakably burning, alive, kinetic.",
    5:  "Massive turbine rotor blades spinning at extreme high RPM, motion-blurred into a continuous disc of metallic blur. Hot air streaming through them with visible heat haze. Sparks of friction. Pure kinetic mechanical fury.",
    6:  "Industrial turbine rotor spinning faster and faster, escalating from fast to blurred-disk speed within the shot. Vibration shakes ambient particles in the air. Strobing reflections of cyan light on polished metal as it rotates.",
    7:  "Generator rotor parts spinning rapidly inside the housing — polished electromagnetic core blurring into pure rotational motion. Visible centrifugal force. Crackling electrical arcs at the periphery.",
    8:  "Macro view of generator magnets — electromagnetic field lines visibly forming and pulsing into existence as electricity is induced. Cyan energy filaments crackling between poles, building intensity. Active electromagnetic generation.",
    9:  "Glowing cyan-white electricity actively traveling through polished copper conductors and busbars at high speed. Visible energy pulses racing along the wires, like lightning channeled into metal. Sparks at junctions.",
    10: "High-voltage power surging from generator output into a switchyard at night. Visible cyan energy actively flowing along conductor lines toward distant transmission towers. Electrical hum, slight ground vibration shaking nearby particles.",
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
    # Archive existing clip before overwriting
    if out_mp4.exists():
        arch = ARCHIVE / out_mp4.name
        if not arch.exists():
            out_mp4.rename(arch)
        else:
            out_mp4.unlink()
    b64 = base64.b64encode(img_path.read_bytes()).decode()
    prompt = CAM + SUBJECTS[idx]
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
    todo = list(SUBJECTS.keys())  # 1-10
    print(f"=== Regenerating {len(todo)} SB1 clips with motion-explicit prompts ===")
    print(f"Frames: {todo}  (originals archived to {ARCHIVE.name}/)")
    token = mint_token()
    ops = {}
    with ThreadPoolExecutor(max_workers=10) as ex:
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


if __name__ == "__main__":
    main()
