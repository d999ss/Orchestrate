#!/usr/bin/env python3
"""UI-in-context composite pipeline.

Step 1 — Vertex Imagen generates a scene with a clearly defined glowing
         rectangular monitor / tablet / wall-of-screens area, NO readable
         UI text inside it.
Step 2 — PIL composites the real GridOS screenshot onto that monitor
         region (with screen tint + slight glow bleed).
Step 3 — Brand pipeline: shimmer overlay + particle dust + evergreen
         grade so the composite reads as one piece, not a sticker.

Run from the repo root after:
  source ~/.claude/secrets/orchestrate-veo.env
"""
import os, sys, json, base64, time, ssl, subprocess, urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageChops, ImageEnhance
import certifi
SSL_CTX = ssl.create_default_context(cafile=certifi.where())

ROOT = Path(__file__).parent
SHIMMER = Image.open(ROOT/"shimmer.png").convert("RGB")

GAC = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
GCP_PROJECT = os.environ["GCP_PROJECT"]
GCP_LOCATION = os.environ.get("GCP_LOCATION", "us-central1")
_SA = json.loads(Path(GAC).read_text())
SA_EMAIL = _SA["client_email"]
_PEM = Path(GAC).with_suffix(".pem")
if not _PEM.exists():
    _PEM.write_text(_SA["private_key"]); _PEM.chmod(0o600)

def _b64u(b): return base64.urlsafe_b64encode(b).rstrip(b"=").decode()
_TOK = {"v": None, "t": 0}
def token():
    if _TOK["v"] and (time.time() - _TOK["t"]) < 3000: return _TOK["v"]
    now = int(time.time())
    claim = {"iss": SA_EMAIL, "scope": "https://www.googleapis.com/auth/cloud-platform",
             "aud": "https://oauth2.googleapis.com/token", "iat": now, "exp": now + 3600}
    h = _b64u(json.dumps({"alg":"RS256","typ":"JWT"}).encode())
    b = _b64u(json.dumps(claim).encode())
    sig = subprocess.run(["openssl","dgst","-sha256","-sign",str(_PEM),"-binary"],
                         input=f"{h}.{b}".encode(), capture_output=True, check=True).stdout
    jwt = f"{h}.{b}.{_b64u(sig)}"
    r = urllib.request.urlopen(urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=f"grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer&assertion={jwt}".encode(),
        headers={"Content-Type":"application/x-www-form-urlencoded"}), timeout=30, context=SSL_CTX)
    tok = json.loads(r.read())["access_token"]
    _TOK["v"], _TOK["t"] = tok, time.time(); return tok

def imagen(prompt):
    url = (f"https://{GCP_LOCATION}-aiplatform.googleapis.com/v1/projects/"
           f"{GCP_PROJECT}/locations/{GCP_LOCATION}/publishers/google/models/"
           f"imagen-4.0-fast-generate-001:predict")
    body = json.dumps({"instances":[{"prompt": prompt}],
                       "parameters":{"sampleCount":1, "aspectRatio":"16:9"}}).encode()
    req = urllib.request.Request(url, data=body, headers={
        "Authorization": f"Bearer {token()}", "Content-Type":"application/json"})
    with urllib.request.urlopen(req, timeout=180, context=SSL_CTX) as r:
        resp = json.loads(r.read())
    return base64.b64decode(resp["predictions"][0]["bytesBase64Encoded"])

# Per-frame scene prompts tuned to pay off the live caption. Each prompt
# is rendered in the deck's illustrative dot-matrix particle aesthetic
# (NOT photographic), with a clearly placed dark rectangular monitor /
# tablet / wall screen that has NO UI inside it. The PIL step then
# composites the real GridOS screenshot into that rectangle.
_BRAND = (
    "rendered in the GE Vernova Orchestrate dot-matrix particle aesthetic, "
    "illustrative not photographic, not stock-photo. Deep evergreen #004745 "
    "base, cyan #00B2A9 brand accents only, faint chartreuse #C8FF00 flecks, "
    "no other colors. All figures constructed from luminous cyan particle "
    "points against deep evergreen darkness. No faces, no recognizable "
    "people, no text anywhere, no logos, no UI elements inside any screen. "
    "Premium cinematic lighting with strong cyan rim-light from monitors. "
    "16:9."
)

SCENES = {
    # 04C "The intelligent network running" — wide control center, wall of screens
    "04c": {
        "prompt": (
            "Wide cinematic establishing shot of a darkened GE Vernova grid "
            "operations control center — a vast curved video wall of monitors "
            "filling the back of the frame, two or three operator silhouettes "
            "at curved desks in the foreground viewed from behind, suggesting "
            "an intelligent network running at scale. ONE single very large "
            "central monitor on the video wall, perfectly rectangular and "
            "front-facing, dominates the center of the frame as a clean dark "
            "blank rectangle with faint cyan glow — ready to receive a "
            "screenshot composite, NO text or UI inside it. Other surrounding "
            "monitors are smaller and out-of-focus glows. Strong volumetric "
            "cyan light through the room. " + _BRAND
        ),
        "monitor_rect": (380, 150, 1160, 720),
        "source_ui": "04c_full_mesh.bak.png",
        "out_path": "04c_full_mesh.png",
    },
    # 05A "The journey is geographic now" — single operator + regional map
    "05a": {
        "prompt": (
            "Cinematic shot of ONE operator silhouette at the LOWER-RIGHT "
            "corner of frame — only the back of their shoulder and a hint of "
            "the back of their head visible, made from luminous cyan particle "
            "points. They are facing one VERY LARGE widescreen monitor that "
            "DOMINATES the frame (filling roughly the upper-left three-quarters "
            "of the frame). The monitor is a clean dark blank rectangle with "
            "faint cyan glow, NO text or UI inside it, with a real visible "
            "monitor bezel and stand. NO secondary monitors anywhere. Behind "
            "the monitor on the right side, a faint distant city skyline at "
            "dusk rendered in dot-matrix particles is just visible through a "
            "deep window slot — quiet, atmospheric, not the focus. Cyan rim-"
            "light from the monitor catches drifting particles in the air. " + _BRAND
        ),
        "monitor_rect": (60, 130, 1280, 800),
        "source_ui": "05a_paths_fan.bak.png",
        "out_path": "05a_paths_fan.png",
    },
    # 05B "The decision moment, made real" — over-the-shoulder
    "05b": {
        "prompt": (
            "Cinematic over-the-shoulder composition. ONE operator silhouette "
            "at the FAR-RIGHT edge of the frame — only the back of one shoulder "
            "and a sliver of the back of their head visible (NOT central, NOT "
            "a full bust, NOT a statue) — made from luminous cyan particle "
            "points. They face one very large widescreen monitor that fills "
            "the LEFT two-thirds of the frame. The monitor is a clean dark "
            "blank rectangle with a real visible bezel, faint cyan glow inside, "
            "NO text or UI. Strong volumetric monitor glow bouncing into the "
            "dark evergreen room, catching drifting particles in the air. "
            "Faint out-of-focus secondary monitors deeper in the background. " + _BRAND
        ),
        "monitor_rect": (90, 140, 1110, 800),
        "source_ui": "05b_gridos.bak.png",
        "out_path": "05b_gridos.png",
    },
    # 05C "An actual GridOS timeline" — multi-operator floor, gantt across screens
    "05c": {
        "prompt": (
            "Wider cinematic establishing shot of a real-feeling grid "
            "operations control floor — three operator silhouettes (made from "
            "luminous cyan particle points, viewed from behind, at curved "
            "consoles in the foreground) looking up at a massive, "
            "architectural video wall covering the entire back wall of the "
            "room. The video wall feels REAL — built into the wall, with deep "
            "bezels, ambient back-lighting, NOT a graphic outline. Across "
            "the center of the wall, ONE very wide horizontal panel "
            "dominates, a clean dark blank rectangle with faint cyan glow, "
            "NO text or UI inside, ready for a screenshot composite — it will "
            "show the day's GridOS gantt. Volumetric cyan light bounces from "
            "the wall into the room, catching dot-matrix particles in the "
            "air. " + _BRAND
        ),
        "monitor_rect": (160, 230, 1600, 540),
        "source_ui": "05c_path_chosen.bak.png",
        "out_path": "05c_path_chosen.png",
    },
    # 08B "The grid down to the truck on the street" — field tech with tablet
    "08b": {
        "prompt": (
            "Cinematic medium shot of a field technician silhouette holding a "
            "rugged tablet horizontally in both hands at chest height, standing "
            "outdoors at a regional power substation at dusk — transformer "
            "silhouettes and overhead distribution lines visible in the "
            "background built from dot-matrix particles. The tablet screen "
            "fills a large area in the lower-center of the frame, perfectly "
            "rectangular and front-facing, clean dark blank rectangle with "
            "faint cyan glow, NO text or UI inside it, ready for a screenshot "
            "composite. Strong cyan rim-light from the tablet up onto the "
            "tech's hands and chest. Calm, grounded, human-scale, the journey "
            "down to one truck on the street. " + _BRAND
        ),
        "monitor_rect": (340, 460, 1240, 580),
        "source_ui": "08b_distribution.bak.png",
        "out_path": "08b_distribution.png",
    },
}

def composite_ui_onto_monitor(scene_img, ui_path, rect):
    """Paste the real UI screenshot onto the monitor area with a screen blend
    + slight glow bleed so it reads as light coming through, not a sticker."""
    x, y, w, h = rect
    ui = Image.open(ROOT/ui_path).convert("RGB")
    # Fit UI into rect preserving aspect (UI is 16:9 already so this is clean)
    ui = ui.resize((w, h), Image.LANCZOS)
    # Slight cyan-evergreen tint pass so the UI ties to the room light
    r, g, b = ui.split()
    g = ImageEnhance.Brightness(g).enhance(1.05)
    b = ImageEnhance.Brightness(b).enhance(1.10)
    ui = Image.merge("RGB", (r, g, b))
    # Softly bevel/shrink the UI a touch inside the monitor rect (margin)
    inset = 6
    inner = ui.resize((w - 2*inset, h - 2*inset), Image.LANCZOS)
    scene_img.paste(inner, (x + inset, y + inset))
    # Add a soft glow bleed from the monitor edges
    glow_mask = Image.new("L", scene_img.size, 0)
    ImageDraw.Draw(glow_mask).rectangle([x, y, x+w, y+h], fill=255)
    glow_mask = glow_mask.filter(ImageFilter.GaussianBlur(48))
    glow_layer = Image.new("RGB", scene_img.size, (10, 50, 60))
    scene_img = Image.composite(
        ImageChops.screen(scene_img, ImageEnhance.Brightness(glow_layer).enhance(0.35)),
        scene_img, glow_mask)
    return scene_img

def brand_pipeline(im):
    """Shimmer overlay (screen blend at low brightness) so the frame
    matches the rest of the deck's brand thread."""
    sh = SHIMMER.resize(im.size, Image.LANCZOS)
    return ImageChops.screen(im, ImageEnhance.Brightness(sh).enhance(0.22))

def go(frame_id):
    spec = SCENES[frame_id]
    print(f"[1/3] imagen scene for {frame_id}…", flush=True)
    scene_bytes = imagen(spec["prompt"])
    scene_raw = ROOT / f".{frame_id}_scene.raw.png"
    scene_raw.write_bytes(scene_bytes)
    scene = Image.open(scene_raw).convert("RGB")
    # Ensure 1920x1080 working canvas
    if scene.size != (1920, 1080):
        scene = scene.resize((1920, 1080), Image.LANCZOS)
    print(f"[2/3] compositing UI onto monitor rect {spec['monitor_rect']}…", flush=True)
    scene = composite_ui_onto_monitor(scene, spec["source_ui"], spec["monitor_rect"])
    print(f"[3/3] brand pipeline…", flush=True)
    final = brand_pipeline(scene)
    out = ROOT / spec["out_path"]
    final.save(out, format="PNG", optimize=True)
    scene_raw.unlink()
    print(f"WROTE  {out}  ({out.stat().st_size:,} bytes)")

if __name__ == "__main__":
    for fid in (sys.argv[1:] or ["05b"]):
        go(fid)
