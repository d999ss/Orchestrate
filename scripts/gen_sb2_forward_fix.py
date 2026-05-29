#!/usr/bin/env python3
"""Patch: regen the 13 SB2 clips whose camera wasn't moving FORWARD.

Forward only — push-in, dolly-in, fly-through, tracking-forward, advancing
through frame depth. No orbits, no lateral dollies, no pull-backs, no booms.
The film is a journey; every cut must drive the viewer forward.
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

STYLE = (
    "Maintain the EXACT cyan-on-deep-black painterly concept-art aesthetic of the reference image. "
    "Stylized, atmospheric, painterly. NOT photoreal, NOT documentary, NOT real-world video. "
    "Energy is directed, precise, deliberate, contained. NOT chaotic, NOT photoreal lightning, "
    "NOT explosive. The energy stays channeled and purposeful. "
    "Cyan-white emissive glow on deep black void. Soft halation around bright sources. "
    "ABSOLUTELY NO TEXT, NO LOGOS, NO WORDS, NO LETTERS, NO BRAND MARKS anywhere in the frame. "
)

FORWARD_RULE = (
    "CRITICAL CAMERA RULE: The camera moves FORWARD through the scene the entire shot. "
    "Push-in, dolly-in, or fly-through only. The viewer advances deeper into the frame. "
    "ABSOLUTELY NO orbit, NO lateral pan, NO sideways dolly, NO pull-back, NO boom up, "
    "NO crane down, NO tilt-only. Forward camera motion only — always advancing. "
)

# Frame -> (source_frame_idx, forward-only scene prompt).
# source_frame_idx defaults to the same number; specify to use a different source.
PROMPTS = {
    1:  (1,  "A glowing cyan globe in deep darkness, connected lights appearing across continents as a network forms. Camera pushes forward toward the planet, the globe growing larger and filling the frame as we approach."),
    4:  (4,  "The stator's particle field aligns to the spinning rotor inside a turbine. Halftone field lines bloom outward in cyan. Camera dollies forward into the rotor housing, advancing into the spinning machinery."),
    6:  (6,  "A shared rotating shaft inside a generator, transferring mechanical energy to the next stage. Camera dollies forward along the shaft, advancing down its length into the depth of the machinery."),
    8:  (8,  "Magnetic field lines pulse into cyan particles between rotor magnets. N and S poles align. The frame births an electron. Camera pushes forward into the magnetic field, advancing through the pulsing flux."),
    13: (13, "A top-down grid mesh of transmission lines spreads across dark terrain. Camera flies forward over the mesh at high altitude, the network rushing toward the viewer in receding depth."),
    14: (14, "Branching cyan paths fan out across a wider grid mesh as routing decisions visualize. Camera flies forward into the branching paths, advancing along the lines as they fork outward."),
    15: (15, "Silhouettes of grid operators in a control room, ultrawide displays glowing cyan. Camera dollies forward through the silhouettes toward the displays at the back of the room."),
    16: (16, "A regional map across the southeastern United States. Atlanta resolves as a brighter node. Camera flies forward low over the map at high speed, advancing toward Atlanta as it brightens ahead."),
    19: (19, "A dark dormant city skyline at night, the first signs of cyan power on the horizon. Camera flies forward over the dark city toward the brightening horizon, advancing toward the dawn of light."),
    23: (23, "A stadium bowl ignites in sequence, an eight-petal pinwheel crown of cyan light blooming outward. Camera pushes forward over the stadium bowl, advancing toward the center of the ignition."),
    25: (25, "The Signia by Hilton hotel tower at night, glass facade glowing cyan, GWCC dome adjacent. Camera pushes forward toward the hotel entrance, advancing along the approach to the building."),
    29: (29, "A vast keynote hall, audience silhouetted in the foreground, the stage glowing cyan in the distance. Camera pushes forward through the rows of the audience toward the stage at the front."),
    30: (1,  "A glowing cyan globe fully lit with every continent connected by arcs of cyan light forming a complete network. The grid is alive. Camera pushes forward toward the planet, advancing into the globe as it fills the frame — the journey's climactic arrival at its destination."),
}


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


def submit_one(idx, src_idx, prompt, token):
    out_dir = ROOT / "films" / "sb2_clips"
    out_mp4 = out_dir / f"clip-{idx:02d}.mp4"
    img_path = ROOT / "storyboard-2" / f"frame-{src_idx:02d}.png"
    b64 = crop_16_9_b64(img_path)
    payload = {
        "instances": [{
            "prompt": STYLE + FORWARD_RULE + prompt,
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
    out_dir = ROOT / "films" / "sb2_clips"
    out_mp4 = out_dir / f"clip-{idx:02d}.mp4"
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
    todo = sorted(PROMPTS.keys())
    print(f"Regenerating {len(todo)} forward-only clips: {todo}")
    token = mint_token()
    ops = {}
    for idx in todo:
        src_idx, prompt = PROMPTS[idx]
        # delete existing so the regen actually overwrites
        out_mp4 = ROOT / "films" / "sb2_clips" / f"clip-{idx:02d}.mp4"
        if out_mp4.exists():
            out_mp4.unlink()
        backoff = 15
        for attempt in range(6):
            i, op, err = submit_one(idx, src_idx, prompt, token)
            if not err:
                ops[idx] = op
                print(f"  clip-{idx:02d} (src f{src_idx:02d}): submitted")
                break
            if "HTTP 429" in str(err) or "RESOURCE_EXHAUSTED" in str(err):
                print(f"  clip-{idx:02d}: 429, retry in {backoff}s")
                time.sleep(backoff)
                backoff = min(backoff * 2, 120)
                continue
            print(f"  clip-{idx:02d}: FAIL {err}", file=sys.stderr)
            break
        time.sleep(4)

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
                if status.startswith("saved"):
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
