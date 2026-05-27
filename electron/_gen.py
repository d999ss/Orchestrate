#!/usr/bin/env python3
"""Generate 27 storyboard frames, composite each with the keynote PPT
shimmer texture for brand-thread cohesion.

Backends (auto-selected):
  - VERTEX (preferred): if GOOGLE_APPLICATION_CREDENTIALS + GCP_PROJECT are
    set, uses Imagen-4 on Vertex AI under your paid project. Same billing
    bucket as Veo. Not bound by AI Studio prepayment credits.
  - GEMINI (fallback): uses gemini-2.5-flash-image (Nano Banana) with the
    AI Studio key from ~/.claude/secrets.json — subject to prepayment cap.

After `scripts/_gcp_setup.sh` runs once, just:
  source ~/.claude/secrets/orchestrate-veo.env
  python3 electron/_gen.py <frame_id>
"""
import os, sys, json, base64, time, ssl, subprocess, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image, ImageEnhance, ImageChops
from pathlib import Path
import certifi
SSL_CTX = ssl.create_default_context(cafile=certifi.where())

ROOT=Path(__file__).parent
SHIMMER=Image.open(ROOT/"shimmer.png").convert("RGB")

# Backend selection
GAC = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
GCP_PROJECT = os.environ.get("GCP_PROJECT")
GCP_LOCATION = os.environ.get("GCP_LOCATION", "us-central1")
USE_VERTEX = bool(GAC and GCP_PROJECT and Path(GAC).exists())

if USE_VERTEX:
    print(f"[backend] VERTEX  project={GCP_PROJECT}  loc={GCP_LOCATION}", file=sys.stderr)
    _SA = json.loads(Path(GAC).read_text())
    SA_EMAIL = _SA["client_email"]
    _PEM_PATH = Path(GAC).with_suffix(".pem")
    if not _PEM_PATH.exists():
        _PEM_PATH.write_text(_SA["private_key"])
        _PEM_PATH.chmod(0o600)
else:
    KEY=json.loads(Path.home().joinpath(".claude/secrets.json").read_text())["google"]["gemini_api_key"]
    print("[backend] GEMINI (AI Studio Nano Banana) — set GOOGLE_APPLICATION_CREDENTIALS+GCP_PROJECT for Vertex", file=sys.stderr)

# Vertex access token cache (SA token good ~1h). Mints via openssl-signed JWT
# → OAuth2 token exchange. No gcloud calls, no global config mutation.
_TOK = {"v": None, "t": 0}
def _b64u(b): return base64.urlsafe_b64encode(b).rstrip(b"=").decode()
def _vertex_token():
    if _TOK["v"] and (time.time() - _TOK["t"]) < 3000:
        return _TOK["v"]
    now = int(time.time())
    claim = {"iss": SA_EMAIL, "scope": "https://www.googleapis.com/auth/cloud-platform",
             "aud": "https://oauth2.googleapis.com/token", "iat": now, "exp": now + 3600}
    header = _b64u(json.dumps({"alg":"RS256","typ":"JWT"}).encode())
    body = _b64u(json.dumps(claim).encode())
    signing_input = f"{header}.{body}".encode()
    sig = subprocess.run(["openssl","dgst","-sha256","-sign",str(_PEM_PATH),"-binary"],
                         input=signing_input, capture_output=True, check=True).stdout
    jwt = f"{header}.{body}.{_b64u(sig)}"
    req = urllib.request.Request("https://oauth2.googleapis.com/token",
        data=("grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer&assertion="+jwt).encode(),
        headers={"Content-Type":"application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=30, context=SSL_CTX) as r:
        tok = json.loads(r.read())["access_token"]
    _TOK["v"], _TOK["t"] = tok, time.time()
    return tok

STYLE=("GE Vernova Orchestrate 2026 keynote aesthetic. Deep evergreen base color "
       "#004745 to #003c3a filling the frame, with a fine halftone dot-matrix "
       "particle texture overlaid. Cinematic 16:9 framing. Cyan #00B2A9 and "
       "lime #C8FF00 brand accents only. Premium abstract data-visualization "
       "style, soft volumetric glow. No people, no text, no logos, no UI. "
       "Brand-pure, calm, technical.")

SHOTS = [
 ("01a_origin",           "Dead center: one single bright cyan point of light — an electron — floating in a deep evergreen halftone particle field. Subtle atmospheric haze. Otherwise empty."),
 ("01b_pulse_out",        "Center: one cyan electron point of light emitting a single perfect concentric ring of cyan-teal light rolling outward through an evergreen halftone particle field."),
 ("01c_first_trail",      "A single cyan electron moving across the frame leaving its first thin cyan comet trail behind it, evergreen halftone particle field background."),
 ("02a_wind",             "A regional wind turbine in silhouette against an evergreen halftone particle sky at dawn, cyan-teal energy beginning to pulse outward from the blade tips."),
 ("02b_solar",            "Aerial top-down view of a regional solar panel array rendered in evergreen halftone dot-matrix, cyan and lime data points tracking eastward sunlight across the panels."),
 ("02c_hydro",            "A regional hydro dam at dawn, water release rendered as flowing cyan-teal data streams over an evergreen halftone particle field."),
 ("03a_dense_field",      "A dense swirling field of cyan particles emerging from an evergreen halftone base, energy concentrating, no other elements."),
 ("03b_grid_order",       "Cyan particles snapping into a precise regular dot-matrix grid pattern, the evergreen field organizing itself into order."),
 ("03c_grid_perspective", "A dot-matrix grid of cyan points tilting into deep space perspective, evergreen depth fading back, abstract architecture."),
 ("04a_first_links",      "First bright cyan link lines drawing between scattered nodes in an evergreen halftone field — the network forming for the first time."),
 ("04b_radiating_node",   "A central glowing cyan node radiating bright lines outward in a starburst pattern across an evergreen halftone particle field."),
 ("04c_full_mesh",        "A complete intelligent mesh network — every node connected by cyan lines — spread across an evergreen halftone particle field."),
 ("05a_paths_fan",        "From a single bright junction point, thousands of fine cyan and lime path lines fanning out radially in every direction across an evergreen field."),
 ("05b_gridos",           "An abstract intelligence layer hovering above a cyan grid — cascading cyan-lime calculations and faint geometric data flows over an evergreen halftone base."),
 ("05c_path_chosen",      "One single cyan path locked bright across an evergreen field, a small lime green confidence-score glyph beside it, every other path dimmed."),
 ("06a_comet",            "A long sweeping cyan-teal comet trail arcing across an evergreen halftone particle field, the moment of acceleration."),
 ("06b_currents",         "Multiple cyan flow currents weaving and crossing each other across an evergreen halftone particle field, motion and direction."),
 ("06c_aurora",           "A graceful aurora-like curve of cyan and lime light bending across the entire frame over an evergreen halftone particle field."),
 ("07a_gold_burst",       "A bright gold radial burst centered in an evergreen halftone particle field, energy and particles flying outward."),
 ("07b_lime_ripple",      "A bright lime green ripple pulse traveling outward through a cyan dot-matrix grid over an evergreen halftone particle field."),
 ("07c_climax",           "A single climactic flash where gold, lime green, and cyan converge at one peak point in the evergreen halftone field."),
 ("08a_atlanta",          "Aerial view of Mercedes-Benz Stadium in Atlanta — the real building. Architecturally accurate: EIGHT TRIANGULAR ROOF PETALS forming a pinwheel-aperture pattern that opens from the center like a camera lens (NOT a closed dome, NOT a ringed circular roof, NOT generic). The roof petals meet at a central oculus. The exterior walls are crystal-faceted, undulating, curving outward. No Mercedes-Benz logo. The Atlanta downtown skyline rises behind it. Entire scene rendered in evergreen halftone dot-matrix — the petal edges traced in cyan-teal light, the city behind in deeper evergreen. No sports, no field, no players, no logos. Brand-pure architectural silhouette as Atlanta's signature landmark."),
 ("08b_distribution",     "Regional distribution power lines reaching from substations into halftone-rendered neighborhoods, cyan pulses traveling along the lines, evergreen palette."),
 ("08c_aerial_sweep",     "Sweeping high aerial view of a regional grid network pulsing in cyan-teal unison across an evergreen halftone landscape."),
 ("09a_venue_dawn",       "A conference venue exterior at dawn rendered in evergreen halftone, faint abstract silhouettes of attendees walking in — calm, anticipatory, brand-pure."),
 ("09b_keynote_stage",    "Interior of the Orchestrate 2026 keynote hall — the stage and big screens lit up with abstract cyan-lime brand visuals, the room evergreen and quiet, no audience visible."),
 ("09c_hero_hold",        "Final hero hold: an evergreen halftone particle field with a soft cyan particle burst at center and faint lime accents — clean negative space top-right for a brand mark."),
]

def _composite_and_save(name, raw_bytes):
    raw_path = ROOT/f"{name}.raw.png"
    raw_path.write_bytes(raw_bytes)
    base = Image.open(raw_path).convert("RGB")
    sh = SHIMMER.resize(base.size, Image.LANCZOS)
    # screen blend the shimmer at ~35% intensity for the brand thread
    blended = ImageChops.screen(base, ImageEnhance.Brightness(sh).enhance(0.35))
    out = ROOT/f"{name}.png"
    blended.save(out, format="PNG", optimize=True)
    raw_path.unlink()
    return out.stat().st_size

def _gen_vertex(name, shot):
    prompt = f"{STYLE}\n\nScene: {shot}"
    url = (f"https://{GCP_LOCATION}-aiplatform.googleapis.com/v1/projects/"
           f"{GCP_PROJECT}/locations/{GCP_LOCATION}/publishers/google/models/"
           f"imagen-4.0-generate-001:predict")
    body = json.dumps({"instances":[{"prompt": prompt}],
                       "parameters":{"sampleCount":1, "aspectRatio":"16:9"}}).encode()
    for attempt in range(3):
        try:
            tok = _vertex_token()
            req = urllib.request.Request(url, data=body, headers={
                "Authorization": f"Bearer {tok}", "Content-Type":"application/json"})
            with urllib.request.urlopen(req, timeout=180, context=SSL_CTX) as r:
                resp = json.loads(r.read())
            preds = resp.get("predictions", [])
            if preds and "bytesBase64Encoded" in preds[0]:
                size = _composite_and_save(name, base64.b64decode(preds[0]["bytesBase64Encoded"]))
                return (name, "OK", size)
            return (name, f"NO_IMAGE: {json.dumps(resp)[:200]}", 0)
        except urllib.error.HTTPError as e:
            err = e.read().decode("utf-8","replace")[:200]
            if attempt < 2: time.sleep(2*(attempt+1)); continue
            return (name, f"HTTP {e.code} {err}", 0)
        except Exception as e:
            if attempt < 2: time.sleep(2*(attempt+1)); continue
            return (name, f"ERR {e}", 0)

def _gen_gemini(name, shot):
    prompt = f"{STYLE}\n\nScene: {shot}"
    body = json.dumps({"contents":[{"parts":[{"text": prompt}]}]}).encode()
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent?key={KEY}",
        data=body, headers={"Content-Type":"application/json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=120, context=SSL_CTX) as r:
                resp = json.loads(r.read())
            parts = resp.get("candidates",[{}])[0].get("content",{}).get("parts",[])
            for p in parts:
                if "inlineData" in p:
                    size = _composite_and_save(name, base64.b64decode(p["inlineData"]["data"]))
                    return (name, "OK", size)
            return (name, f"NO_IMAGE: {json.dumps(resp)[:200]}", 0)
        except urllib.error.HTTPError as e:
            if attempt < 2: time.sleep(2*(attempt+1)); continue
            return (name, f"HTTP {e.code}", 0)
        except Exception as e:
            if attempt < 2: time.sleep(2*(attempt+1)); continue
            return (name, f"ERR {e}", 0)

def gen(name, shot):
    return _gen_vertex(name, shot) if USE_VERTEX else _gen_gemini(name, shot)

def main():
    only = set(sys.argv[1:]) if len(sys.argv)>1 else None
    todo = [(n,s) for n,s in SHOTS if not only or n in only]
    print(f"generating {len(todo)} frames…")
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(gen, n, s): n for n,s in todo}
        for f in as_completed(futs):
            n, status, size = f.result()
            print(f"  {n:24} {status:10} {size}")
    print("done")

if __name__ == "__main__":
    main()
