#!/usr/bin/env python3
"""Generate Veo 3.0-fast clips for SB2 and SB3 (60 total).

Same approach as SB1: image-to-video off the existing storyboard-N/frame-NN.png
references. Locked-off subject motion. Cyan-white industrial palette.

Idempotent — skips clips that already exist.
"""
import os, sys, json, time, base64, pathlib, ssl, urllib.request, urllib.error
import certifi
from concurrent.futures import ThreadPoolExecutor, as_completed
from google.oauth2 import service_account
from google.auth.transport.requests import Request

SSL_CTX = ssl.create_default_context(cafile=certifi.where())
ROOT = pathlib.Path(__file__).resolve().parent.parent

PROJECT = "orchestrate-veo"
LOCATION = "us-central1"
SA_KEY = os.path.expanduser("~/.claude/secrets/veo-runner-key.json")
MODEL = "veo-3.0-fast-generate-001"
ENDPOINT = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT}/locations/{LOCATION}/publishers/google/models/{MODEL}"

STYLE = (
    "Maintain the EXACT aesthetic, color palette, and visual style of the reference image. "
    "Do NOT introduce photoreal documentary realism. Keep the painterly, "
    "stylized, abstract atmospheric look of the reference image. "
    "Locked-off camera, completely static frame. No pan, no tilt, no zoom, no dolly, no shake. "
    "Subject motion only within the frame — subtle particle drift, glow pulsing, gentle energy flow. "
    "Cyan-white emissive glow on deep black void. Constellation particle overlays. "
    "ABSOLUTELY NO TEXT, NO LOGOS, NO WORDS, NO LETTERS, NO BRAND MARKS anywhere in the frame. "
)

# SB2 — Anatomy of a Watt
SB2 = {
    1: "A glowing globe rotates slowly, connected lights appear across continents — a network of nodes forming.",
    2: "Push-in motion: the camera moves toward a single energy facility, lights flickering on across its structure.",
    3: "Inside generation: cyan glow gathers and pulses inside the turbine housing, source-agnostic energy forming.",
    4: "A stator's particle field aligns to the spinning rotor; halftone field lines bloom outward.",
    5: "A single bright cyan point of light separates from a field and exits frame right, the journey beginning.",
    6: "A shared shaft transfers rotational energy laterally — mechanical handoff in slow motion.",
    7: "Layered rings of metal accelerate, the interior multiplying the speed and motion blurring.",
    8: "Magnetic field lines pulse into existence visualized as cyan particles, the moment electricity is born.",
    9: "A clean cyan waveform pulses across the frame, the first measurable electric signal alive.",
    10: "Energy exits the source, joining a larger system of high-voltage transmission infrastructure.",
    11: "Step-up coils inside a transformer, voltage climbing visibly as cyan energy intensifies.",
    12: "A long corridor of transmission towers marches into the horizon, wide aspect, cinematic.",
    13: "The camera pulls up: the transmission corridor revealed as one strand in a much wider grid mesh.",
    14: "Routing decisions visualized as branching cyan paths fanning out across the grid network.",
    15: "Operators silhouetted in a control room behind ultrawide displays of live grid data.",
    16: "A map reveals: the southeastern region resolves, Atlanta lighting up as a brighter node on the map.",
    17: "Cyan vectors converge toward a central point: demand pulling supply forward dynamically.",
    18: "Transmission towers feed into a city skyline silhouette — the energy handoff begins.",
    19: "A dark dormant city with first signs of power appearing on the horizon, lights beginning to ignite.",
    20: "The skyline fills with light, streets threading with moving cyan illumination across the city.",
    21: "Aerial low pass through a lit downtown toward a stadium, urban infrastructure activating.",
    22: "A service line carrying cyan energy to its final destination, the last leg of physical delivery.",
    23: "A stadium bowl ignites in sequence, a halo of warm reflection blooming outward.",
    24: "Street-level view: a cyan point of energy arcs from a stadium across an open plaza toward a hotel base.",
    25: "Wide cinematic shot of the Signia by Hilton hotel tower at night, glass facade glowing, GWCC dome adjacent.",
    26: "Interior atrium of a modern luxury hotel — hallways, lobbies, meeting rooms activating one by one.",
    27: "Doors of a keynote hall open; cyan ambient light reaches the threshold, the stage beyond still in shadow.",
    28: "Low angle inside the keynote hall: the first beam of light strikes the lectern, tight detail.",
    29: "Side angle across an audience, faces softly lit by an off-frame cyan glow, screen implied but not shown.",
    30: "Wide hero closing frame of a fully-activated keynote stage with immersive curved LED screens glowing cyan.",
}

# SB3 — Branded Matrix
SB3 = {
    1: "A glowing globe rotates in deep space, connected lights appear across the world — a planet running on the grid.",
    2: "The camera moves toward the globe and transitions into a modern energy facility, where electricity starts.",
    3: "Natural gas ignites inside a turbine system, the first kinetic energy release at industrial scale.",
    4: "A column of rising cyan energy as gas ignites, heat releasing upward inside the chamber.",
    5: "The energy spins into a vortex, gathering speed in a tight rotational motion blur.",
    6: "Spin transfers into a magnetic field, cyan electromagnetic flux beginning to form around the rotor.",
    7: "Spinning magnetic fields induce current, visible cyan electromagnetic lines forming and pulsing.",
    8: "Electricity sparks into being — the first arc of cyan current jumps between conductors.",
    9: "Electrons stream forward as a current pulse, the journey of electricity beginning along a conductor.",
    10: "Electricity moves into the power grid, high-voltage lines leaving a substation in a cinematic wide shot.",
    11: "Transformers increase power for long distance travel — voltage stepped up, coils glowing cyan.",
    12: "Transmission lines carry electricity across a region; towers and wires marching toward the city.",
    13: "The regional grid becomes visible — dot matrix tilting into depth, the system as terrain.",
    14: "Grid systems direct where electricity needs to go, cyan paths fanning out across the territory.",
    15: "Operators silhouetted inside a control room, monitoring screens, human-in-the-loop on the grid.",
    16: "The southeastern power network becomes visible — the full regional system lit in cyan.",
    17: "Cyan power flows toward Atlanta, the current bending toward the destination on the map.",
    18: "Transmission lines lead into the city, the lattice tightening around Atlanta.",
    19: "Atlanta begins lighting up, the skyline catching the surge of incoming power.",
    20: "Buildings, roads, and infrastructure activate across the city — every system coming online.",
    21: "The city brightens, the skyline catching the surge before a landmark stadium ignites.",
    22: "Cyan electricity flows into a stadium, the path's final surge — the journey's climax.",
    23: "Stadium lights turn on, an eight-petal pinwheel crown igniting in cyan over the host city.",
    24: "The surrounding downtown area lights up, the full mesh of the city visible at once.",
    25: "A modern luxury hotel and convention center exterior powers on at night, illuminated cyan.",
    26: "Interior corridors and halls activate inside the convention complex, lights coming awake one by one.",
    27: "A keynote room begins turning on, a soft particle bloom — the space the journey lands in.",
    28: "Stage lights and presentation screens activate, the keynote room fully lit, ready to begin.",
    29: "An audience sits inside the powered environment, faces softly illuminated by stage glow.",
    30: "The whole planet, fully lit and connected — the visual opposite of where we began.",
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


def submit_one(sb, idx, prompt, token):
    out_dir = ROOT / "films" / f"sb{sb}_clips"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_mp4 = out_dir / f"clip-{idx:02d}.mp4"
    if out_mp4.exists():
        return sb, idx, None, "exists"
    img_path = ROOT / f"storyboard-{sb}" / f"frame-{idx:02d}.png"
    if not img_path.exists():
        return sb, idx, None, f"missing {img_path}"
    b64 = base64.b64encode(img_path.read_bytes()).decode()
    payload = {
        "instances": [{"prompt": STYLE + prompt, "image": {"bytesBase64Encoded": b64, "mimeType": "image/png"}}],
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
        return sb, idx, None, f"HTTP {code}"
    return sb, idx, resp["name"], None


def poll_one(sb, idx, opname, token):
    out_dir = ROOT / "films" / f"sb{sb}_clips"
    out_mp4 = out_dir / f"clip-{idx:02d}.mp4"
    if out_mp4.exists():
        return sb, idx, "exists"
    code, r = http(f"{ENDPOINT}:fetchPredictOperation", token, {"operationName": opname})
    if code != 200:
        return sb, idx, f"poll HTTP {code}"
    if not r.get("done"):
        return sb, idx, "pending"
    if r.get("error"):
        return sb, idx, f"ERROR: {r['error']}"
    preds = r.get("response", {}).get("videos", [])
    if not preds:
        return sb, idx, "no videos"
    b64 = preds[0].get("bytesBase64Encoded")
    if b64:
        out_mp4.write_bytes(base64.b64decode(b64))
        return sb, idx, f"saved sb{sb}/clip-{idx:02d}.mp4"
    return sb, idx, "unknown response"


def main():
    todo = [("2", i, SB2[i]) for i in range(1, 31)] + [("3", i, SB3[i]) for i in range(1, 31)]
    print(f"Generating {len(todo)} Veo clips total ({len([t for t in todo if t[0]=='2'])} SB2, {len([t for t in todo if t[0]=='3'])} SB3)")
    token = mint_token()
    ops = {}
    # Slow sequential submission with retry on 429
    for sb, idx, prompt in todo:
        # Skip if already done
        out_mp4 = ROOT / "films" / f"sb{sb}_clips" / f"clip-{idx:02d}.mp4"
        if out_mp4.exists():
            continue
        key = f"{sb}-{idx:02d}"
        # Retry with backoff on rate limit
        backoff = 15
        for attempt in range(6):
            sbr, idxr, op, err = submit_one(sb, idx, prompt, token)
            if err == "exists":
                break
            if not err:
                ops[key] = (sb, idx, op)
                print(f"  sb{sb}/clip-{idx:02d}: submitted (attempt {attempt+1})")
                break
            if "HTTP 429" in err or "RESOURCE_EXHAUSTED" in str(err):
                print(f"  sb{sb}/clip-{idx:02d}: 429, retrying in {backoff}s")
                time.sleep(backoff)
                backoff = min(backoff * 2, 120)
                continue
            print(f"  sb{sb}/clip-{idx:02d}: FAIL {err}", file=sys.stderr)
            break
        time.sleep(4)  # always pause between submissions

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
        pending = [(k, v[0], v[1], v[2]) for k, v in ops.items() if k not in done]
        with ThreadPoolExecutor(max_workers=12) as ex:
            futs = {ex.submit(poll_one, sb, idx, op, token): k for k, sb, idx, op in pending}
            for fut in as_completed(futs):
                sb, idx, status = fut.result()
                key = f"{sb}-{idx:02d}"
                if status.startswith("saved") or status == "exists":
                    done.add(key)
                    print(f"  {key}: {status}")
                elif "ERROR" in status or "HTTP" in status or "no videos" in status:
                    print(f"  {key}: {status}", file=sys.stderr)
                    done.add(key)
        if len(done) < len(ops):
            print(f"  {time.strftime('%H:%M:%S')} {len(done)}/{len(ops)}")
            time.sleep(15)
    print(f"\n=== Done ===")


if __name__ == "__main__":
    main()
