#!/usr/bin/env python3
"""SB2 v2 — Veo 3.0-fast regen with camera motion + 16:9 source pre-crop.

Why this exists:
- Existing sb2_clips/* were made with the locked-camera SB2/SB3 generator.
  User feedback: "the fucking camera never moves" and "weird crop".
- Source PNGs are 1536x1024 (3:2). Veo outputs 1920x1080 (16:9). Without
  pre-crop the model invents content top/bottom or letterboxes.

Fix:
- Pre-crop each source to 1536x864 (16:9 center crop, drops 80px top + 80px bottom)
  via Pillow into a temp dir, base64-encode that.
- Every prompt opens with the same art-direction lock SB1 v23 used and
  closes with a CAMERA MOTION verb specific to the frame.

Output: films/sb2_clips_v2/clip-NN.mp4 (idempotent)
"""
import os, sys, json, time, base64, pathlib, ssl, urllib.request, urllib.error, io
import certifi
from concurrent.futures import ThreadPoolExecutor, as_completed
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

# Art direction lock — matches SB1 v23 that the user approved.
STYLE = (
    "Maintain the EXACT cyan-on-deep-black painterly concept-art aesthetic of the reference image. "
    "Stylized, atmospheric, painterly. NOT photoreal, NOT documentary, NOT real-world video. "
    "Energy is directed, precise, deliberate, contained. NOT chaotic, NOT photoreal lightning, "
    "NOT explosive. The energy stays channeled and purposeful. "
    "Cyan-white emissive glow on deep black void. Soft halation around bright sources. "
    "ABSOLUTELY NO TEXT, NO LOGOS, NO WORDS, NO LETTERS, NO BRAND MARKS anywhere in the frame. "
)

# Prompts: scene description verbatim from storyboard-2/index.html, with a
# specific camera motion verb appended. No "locked-off camera" language.
PROMPTS = {
    1:  "A glowing globe rotates slowly. Connected lights appear across continents, first one node, then a network forming. Camera slowly orbits the planet.",
    2:  "The world resolves into a single energy facility, lit from inside. Camera pushes in steadily toward the facility.",
    3:  "Source-agnostic generation. Cyan glow gathers and pulses inside the turbine housing. No flame, no gas. Camera slowly dollies forward into the housing.",
    4:  "The stator's particle field aligns to the spinning rotor. Halftone field lines bloom outward. Camera orbits around the rotor.",
    5:  "A single bright cyan point separates from a particle field and travels toward the right edge of frame. Camera tracks with the point as it exits.",
    6:  "A shared shaft transfers rotational energy laterally. Mechanical handoff in cinematic slow motion. Camera dollies sideways with the shaft.",
    7:  "Layered concentric rings accelerate. The interior takes the speed and multiplies it. Camera pushes in toward the center.",
    8:  "Magnetic field lines pulse into existence as cyan particles. N and S align. The frame births the electron. Camera slowly orbits around the field.",
    9:  "A clean cyan waveform pulses across the frame. The signal is now real, measurable, alive. Camera dollies forward along the waveform.",
    10: "Energy exits the source, joining a larger high-voltage transmission system. Camera tracks outward with the energy.",
    11: "Step-up transformer coils. Voltage climbs visibly as cyan energy intensifies. Camera pushes in toward the coil.",
    12: "A long corridor of transmission towers marches into the horizon. Wide cinematic aspect. Camera dollies forward through the corridor.",
    13: "The transmission corridor is revealed as one strand in a much wider grid mesh. Camera booms upward to expose the network.",
    14: "Routing decisions visualized as branching cyan paths fanning out across the grid network. Camera pulls back slowly to reveal the branches.",
    15: "Operators silhouetted in a quiet control room. The room behind the grid. Camera drifts laterally across the silhouettes.",
    16: "A regional map resolves. Atlanta lights up as a brighter node. Camera pushes down toward Atlanta.",
    17: "Cyan vectors converge from across the territory toward a central point. Demand pulling supply forward. Camera follows the convergence inward.",
    18: "Transmission towers feed into a city skyline silhouette. The handoff begins. Camera tracks forward toward the skyline.",
    19: "A dark dormant city with first signs of power on the horizon. Camera drifts slowly across the skyline.",
    20: "The skyline fills with light. Streets thread with moving cyan illumination. Camera pushes in toward the brightening city.",
    21: "Aerial low pass through a lit downtown toward a glowing stadium. Camera flies forward at low altitude.",
    22: "A service line carrying cyan energy. The last leg of physical delivery. Camera tracks along the service line.",
    23: "A stadium bowl ignites in cinematic sequence. Halo of warm reflection blooms outward. Camera orbits around the bowl.",
    24: "Street-level view: a cyan arc of energy crosses an open plaza from the stadium toward a hotel base. Camera follows the arc.",
    25: "A modern luxury hotel tower at night, glass facade glowing cyan, convention dome adjacent. Camera drifts wide across the exterior.",
    26: "Interior atrium of a modern luxury hotel. Hallways, lobbies, and meeting rooms activating one by one. Camera pushes forward through the corridors.",
    27: "Doors of a keynote hall open. Cyan ambient light reaches the threshold. Stage still in shadow beyond. Camera pushes slowly toward the open doors.",
    28: "Low angle inside a keynote hall. First beam of cyan light strikes the lectern. Tight detail. Camera pushes in toward the lectern.",
    29: "Side angle across an audience. Faces softly lit by an off-frame cyan glow. Camera dollies laterally across the seated rows.",
    30: "A fully-activated keynote stage with curved LED screens glowing cyan. The whole environment alive. Camera pulls back to reveal the full stage.",
}


def crop_to_16_9_b64(png_path: pathlib.Path) -> str:
    """Center-crop a 1536x1024 source to 1536x864 (16:9) and return base64 PNG."""
    img = Image.open(png_path).convert("RGB")
    w, h = img.size
    target_h = int(round(w * 9 / 16))
    if target_h >= h:
        # Source is already wider than 16:9 -- letterbox would be needed.
        cropped = img
    else:
        top = (h - target_h) // 2
        cropped = img.crop((0, top, w, top + target_h))
    buf = io.BytesIO()
    cropped.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


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


def submit_one(idx, prompt, token):
    out_dir = ROOT / "films" / "sb2_clips_v2"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_mp4 = out_dir / f"clip-{idx:02d}.mp4"
    if out_mp4.exists():
        return idx, None, "exists"
    img_path = ROOT / "storyboard-2" / f"frame-{idx:02d}.png"
    if not img_path.exists():
        return idx, None, f"missing {img_path}"
    b64 = crop_to_16_9_b64(img_path)
    payload = {
        "instances": [{
            "prompt": STYLE + prompt,
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
    if code != 200 or "name" not in (resp if isinstance(resp, dict) else {}):
        return idx, None, f"HTTP {code}: {resp}"
    return idx, resp["name"], None


def poll_one(idx, opname, token):
    out_dir = ROOT / "films" / "sb2_clips_v2"
    out_mp4 = out_dir / f"clip-{idx:02d}.mp4"
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
    # Argparse-free: pass a comma list like "1,5,10" to limit
    only = None
    if len(sys.argv) > 1:
        only = set(int(x) for x in sys.argv[1].split(","))
    todo = [(i, PROMPTS[i]) for i in range(1, 31) if only is None or i in only]
    print(f"Generating {len(todo)} SB2 v2 clips")
    token = mint_token()
    ops = {}
    for idx, prompt in todo:
        out_mp4 = ROOT / "films" / "sb2_clips_v2" / f"clip-{idx:02d}.mp4"
        if out_mp4.exists():
            print(f"  clip-{idx:02d}: skip (exists)")
            continue
        backoff = 15
        for attempt in range(6):
            i, op, err = submit_one(idx, prompt, token)
            if err == "exists":
                break
            if not err:
                ops[idx] = op
                print(f"  clip-{idx:02d}: submitted")
                break
            if "HTTP 429" in str(err) or "RESOURCE_EXHAUSTED" in str(err):
                print(f"  clip-{idx:02d}: 429, retry in {backoff}s")
                time.sleep(backoff)
                backoff = min(backoff * 2, 120)
                continue
            print(f"  clip-{idx:02d}: FAIL {err}", file=sys.stderr)
            break
        time.sleep(4)

    if not ops:
        print("Nothing to poll.")
        return

    print(f"\n=== Polling {len(ops)} ops ===")
    done = set()
    last_token = time.time()
    while len(done) < len(ops):
        if time.time() - last_token > 2400:
            token = mint_token()
            last_token = time.time()
        pending = [(k, v) for k, v in ops.items() if k not in done]
        with ThreadPoolExecutor(max_workers=12) as ex:
            futs = {ex.submit(poll_one, idx, op, token): idx for idx, op in pending}
            for fut in as_completed(futs):
                idx, status = fut.result()
                if status.startswith("saved") or status == "exists":
                    done.add(idx)
                    print(f"  clip-{idx:02d}: {status}")
                elif "ERROR" in status or "HTTP" in status or "no videos" in status:
                    print(f"  clip-{idx:02d}: {status}", file=sys.stderr)
                    done.add(idx)
        if len(done) < len(ops):
            print(f"  {time.strftime('%H:%M:%S')} {len(done)}/{len(ops)} done")
            time.sleep(15)
    print(f"\n=== Done ({len(done)}/{len(ops)}) ===")


if __name__ == "__main__":
    main()
