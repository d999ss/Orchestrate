#!/usr/bin/env python3
"""Generate all 27 Electron board frames via OpenAI gpt-image-1 in the
point-cloud industrial cinema language (the mood-board look).

Per-shot prompts are caption-driven. Non-UI frames are pure point-cloud
sculptures. UI frames (04C, 05A, 05B, 05C, 08B) generate a point-cloud
scene with a clean dark monitor/tablet region, then PIL composites the
real GridOS screenshot into that region.

Idempotent: skips frames whose output already exists at >0.5MB. Backs
up originals to electron/<id>.bak.png before overwriting.

Cost: ~$0.19/frame × 27 = ~$5.13 on OpenAI API.
"""
import os, sys, json, base64, ssl, time, urllib.request
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image, ImageDraw, ImageFilter, ImageChops, ImageEnhance
import certifi
SSL_CTX = ssl.create_default_context(cafile=certifi.where())

REPO = Path.home() / ".." / "tmp" / "Orchestrate-storyboard"
# resolve to /tmp/Orchestrate-storyboard
REPO = Path("/tmp/Orchestrate-storyboard")
ELE = REPO / "electron"
KEY = json.loads(Path.home().joinpath(".claude/secrets.json").read_text())["openai"]["api_key"]

# --- DNA scaffolding -------------------------------------------------
BRAND = (
    " Rendered as a true volumetric point cloud — tiny dim pale mint-"
    "cyan particulate grains floating in 3D space, the interior visible "
    "through density. Scale variation: dust-fine stippling drifts in "
    "the empty space; medium structural points trace only the most "
    "prominent forms; rare faintly brighter pinpoints at intersections. "
    "Subject is 60-70% missing — only the strongest skeletal elements "
    "register; the rest dissolves gradually into a vast deep evergreen "
    "near-black void. NO crisp silhouette, NO perimeter, NO outline — "
    "every edge fades into darkness. Subject occupies less than 35% of "
    "the frame; the rest is empty atmospheric darkness with faint "
    "particle drift. Villeneuve / Deakins cinematic darkness — premium, "
    "restrained, almost camouflaged. Built like an incomplete LiDAR scan "
    "+ electron microscopy + astrophotography hybrid. Calm industrial "
    "intelligence. 16:9."
)
NEG_PRIMER = (
    " Absolutely NO text, NO letters, NO numbers, NO words, NO logos, "
    "NO brand marks, NO wordmarks, NO captions, NO signage, NO UI, NO "
    "dashboard, NO HUD, NO photo-real photograph, NO photographic, NO "
    "hologram, NO wireframe, NO Tron lines, NO vector illustration, NO "
    "AI-startup glow, NO crypto-conference visual, NO esports graphic, "
    "NO bright neon, NO saturated cyan, NO yellow, NO amber, NO orange, "
    "NO gold, NO lime, NO magenta, NO purple, NO white background, NO "
    "sky, NO daylight, NO clouds, NO sun, NO ground, NO floor, NO "
    "halftone print noise, NO motion blur, NO lens flare, NO depth of "
    "field, NO bokeh. Calm restrained darkness only."
)

# --- per-shot prompts (matches Electron captions + DNA) --------------
SHOTS = {
    # 01 ORIGIN — charge gathers / builds / released
    "01a_origin":          ("A single dim pale mint-cyan luminous point of potential floating in vast deep evergreen near-black emptiness — almost invisible, barely registering as light, with the faintest drift of fine dust particles around it. Cinematic restraint, premium darkness, the entire frame is mostly empty atmospheric void.", None),
    "01b_pulse_out":       ("A single dim pale mint-cyan particulate point at center emitting ONE soft concentric ring of energy expanding outward through a vast deep evergreen near-black void — the ring is made of fine particulate dust, partially dissolved, almost invisible. Mostly empty space, atmospheric.", None),
    "01c_first_trail":     ("A single faint mint-cyan particle leaving a soft particulate trail of dust as it moves across a vast deep evergreen near-black void — the trail is made of incomplete dust drifts, dissolving into darkness, partially formed. The frame is mostly empty atmospheric space.", None),
    # 02 THE SOURCE — wind / solar / hydro
    "02a_wind":            ("An archaeological fragment of a wind turbine — only the rotor hub and partial blade shapes register as particulate density — emerging dimly from a vast deep evergreen near-black void. 60% of the form is dissolved into darkness.", None),
    "02b_solar":           ("Aerial fragment of a solar panel array — only a partial grid of panels registers as dim particulate density, the rest dissolves into the deep evergreen void. Geometric repetition barely visible.", None),
    "02c_hydro":           ("Fragment of a hydroelectric dam — only the spillway and partial dam wall register as particulate density, water release suggested by drifting particle currents flowing downward. Vast empty atmospheric darkness around.", None),
    # 03 INTO THE GRID
    "03a_dense_field":     ("A dense localized cluster of mint-cyan particle dust suspended in vast deep evergreen darkness — the cluster has internal density variation but no defined shape, suggesting many electrons gathering. Almost invisible, restrained.", None),
    "03b_grid_order":      ("Mint-cyan particulate points beginning to align into a faint rectilinear dot-matrix pattern — only partially formed, half the pattern still chaotic drifting dust, half resolving into order. Deep evergreen darkness dominates the frame.", None),
    "03c_grid_perspective":("A vast mint-cyan dot-matrix grid tilting into deep three-dimensional perspective, dissolving into the deep evergreen void at the horizon — the grid is incomplete, only partial rows register, the rest is darkness.", None),
    # 04 INTELLIGENT CONNECTIONS
    "04a_first_links":     ("Sparse mint-cyan particulate nodes in deep evergreen darkness with faint particulate lines beginning to form between them — most links are incomplete, only the strongest register. Vast negative space.", None),
    "04b_radiating_node":  ("A single brighter mint-cyan particulate node at the center of vast deep evergreen darkness, with faint particulate lines radiating outward — only some lines are fully formed, others dissolve into dust before reaching the edge.", None),
    # 04C uses scene + UI composite
    "04c_full_mesh":       ("A vast intelligent network of mint-cyan particulate nodes connected by faint particulate lines, suspended in deep evergreen darkness — most of the mesh is incomplete, the eye fills in the structure. In the center of the frame, ONE clean dark rectangular blank panel (no text, no UI) ready to receive a screenshot composite, with a faint cyan glow at its bezel.",
                           {"ui": "04c_full_mesh.bak.png", "rect": (380, 200, 1160, 680)}),
    # 05 THE DECISION — UI composites
    "05a_paths_fan":       ("Aerial point-cloud fragment of a regional map — partial roads and feeder lines traced in mint-cyan particulate dust against deep evergreen darkness, the form 70% missing. On the left side of the frame, ONE clean dark rectangular blank panel (no text, no UI) ready to receive a screenshot composite, with a faint cyan glow at its bezel.",
                           {"ui": "05a_paths_fan.bak.png", "rect": (90, 140, 1350, 820), "src_crop": (470, 280, 1920, 1080)}),
    "05b_gridos":          ("Vast deep evergreen near-black void with faint mint-cyan particle drift across the frame. Center-right of the frame: ONE clean dark rectangular blank panel (no text, no UI) — a portrait monitor — ready to receive a screenshot composite, with a faint cyan glow at its bezel.",
                           {"ui": "05b_gridos.bak.png", "rect": (665, 140, 1255, 940), "src_crop": (1365, 280, 1930, 1045)}),
    "05c_path_chosen":     ("Vast deep evergreen near-black void with faint mint-cyan particle drift. Across the center horizontal third of the frame: ONE clean dark wide horizontal panel (no text, no UI) ready to receive a screenshot composite, with a faint cyan glow at its bezel.",
                           {"ui": "05c_path_chosen.bak.png", "rect": (90, 362, 1830, 717), "src_crop": (470, 427, 1920, 1024)}),
    # 06 FLOW + MOTION — regional route
    "06a_comet":           ("A long sweeping mint-cyan particulate trail arcing across vast deep evergreen darkness — the trail is incomplete, the head bright, the tail dissolving into dust. Mostly empty space around it.", None),
    "06b_currents":        ("Multiple sparse particulate streams crossing each other through deep evergreen darkness — currents made of dim mint-cyan dust, most of each stream missing, only their intersections register.", None),
    "06c_aurora":          ("A graceful incomplete curving arc of mint-cyan particulate dust bending across vast deep evergreen darkness — the arc dissolves at both ends, only the apex has full density.", None),
    # 07 REACHING THE REGION — surge, building, not peak
    "07a_gold_burst":      ("A sparse outward expansion of mint-cyan particulate dust from a single point at center — most of the radial pattern is incomplete, particles drifting outward into deep evergreen darkness. Restrained, atmospheric.", None),
    "07b_lime_ripple":     ("A faint mint-cyan particulate pulse traveling outward through a sparse dot-matrix grid suspended in deep evergreen darkness — the pulse is partial, the grid 70% missing.", None),
    "07c_climax":          ("Mint-cyan particulate currents sweeping forward through deep evergreen darkness, converging toward a distant point — the currents are sparse, partial, mostly empty space. Almost no peak yet, just approach.", None),
    # 08 THE CITY IGNITES — climax
    "08a_atlanta":         ("An archaeological fragment of a monumental faceted angular stadium-like structure — a low circular building with an eight-petal pinwheel-aperture roof (camera-shutter geometry meeting at a small central oculus) and a faceted diamond-crystal exterior wall — emerging dimly from a vast deep evergreen near-black void. The form is 70% missing. Aerial three-quarter cinematic angle.", None),
    # 08B — UI composite
    "08b_distribution":    ("Fragment of a regional power substation — partial transformer silhouettes and overhead distribution line shapes in mint-cyan particulate dust against vast deep evergreen darkness. In the lower-center of the frame: ONE clean dark rectangular blank tablet (no text, no UI) held suggested in space, ready to receive a screenshot composite, with a faint cyan glow.",
                           {"ui": "08b_distribution.bak.png", "rect": (340, 460, 1580, 1040)}),
    "08c_aerial_sweep":    ("A vast sweeping aerial fragment of a regional power grid network — only the strongest mint-cyan particulate lines register across the landscape, the rest dissolves into deep evergreen darkness. Atmospheric, restrained.", None),
    # 09 THE KEYNOTE — denouement
    "09a_venue_dawn":      ("An archaeological fragment of a tall faceted modern hotel building exterior at night — only the strongest vertical structural lines and partial window grid register as mint-cyan particulate dust against vast deep evergreen darkness, the rest dissolves.", None),
    "09b_keynote_stage":   ("An archaeological fragment of a long modern auditorium interior — only the strongest perspective lines of the stage and partial seating rows register as mint-cyan particulate dust against vast deep evergreen darkness. No people, no text, mostly empty atmospheric space.", None),
    "09c_hero_hold":       ("A vast deep evergreen near-black field with a soft circular cluster of mint-cyan particulate dust drifting at the center — the cluster is barely visible, atmospheric, the form 80% empty space. Clean negative space surrounding for a brand mark to be placed later.", None),
}

# --- OpenAI call -----------------------------------------------------
def gen_image(prompt, size="1536x1024", quality="high", n=1):
    body = json.dumps({"model":"gpt-image-1","prompt":prompt+BRAND+NEG_PRIMER,
                       "size":size,"n":n,"quality":quality}).encode()
    req = urllib.request.Request("https://api.openai.com/v1/images/generations",
        data=body, headers={"Authorization":f"Bearer {KEY}","Content-Type":"application/json"})
    for attempt in range(3):
        try:
            r = urllib.request.urlopen(req, timeout=600, context=SSL_CTX).read()
            data = json.loads(r)
            return [base64.b64decode(d["b64_json"]) for d in data["data"]]
        except urllib.error.HTTPError as e:
            err = e.read().decode("utf-8","replace")
            if attempt < 2: time.sleep(3*(attempt+1)); continue
            raise RuntimeError(f"HTTP {e.code}: {err[:300]}")

# --- UI composite (same recipe as _field_compose) --------------------
def composite_ui(scene_bytes, ui_path, rect, src_crop=None):
    scene = Image.open(__import__("io").BytesIO(scene_bytes)).convert("RGB")
    if scene.size != (1920, 1080):
        scene = scene.resize((1920, 1080), Image.LANCZOS)
    src = Image.open(ELE/ui_path).convert("RGB")
    if src_crop: src = src.crop(src_crop)
    x, y, x2, y2 = rect
    w, h = x2-x, y2-y
    ui = src.resize((w, h), Image.LANCZOS)
    ui = ImageEnhance.Brightness(ui).enhance(0.92)
    ui = ImageEnhance.Color(ui).enhance(0.65)
    # soft dark well behind UI
    well = Image.new("L", scene.size, 255)
    ImageDraw.Draw(well).rectangle((x-30, y-30, x2+30, y2+30), fill=120)
    well = well.filter(ImageFilter.GaussianBlur(60))
    field_dim = Image.eval(scene, lambda v: int(v*0.62))
    out = Image.composite(scene, field_dim, well)
    # feathered UI alpha
    feather = Image.new("L", ui.size, 0)
    ImageDraw.Draw(feather).rectangle((30, 30, w-30, h-30), fill=255)
    feather = feather.filter(ImageFilter.GaussianBlur(28))
    base_alpha = Image.new("L", ui.size, 235)
    mask = ImageChops.multiply(base_alpha, feather)
    out.paste(ui, (x, y), mask)
    return out

# --- runner ----------------------------------------------------------
def backup(p):
    bak = p.with_name(p.stem + ".bak.png")
    if not bak.exists() and p.exists(): bak.write_bytes(p.read_bytes())

def do_one(fid, scene_prompt, ui_spec):
    out_path = ELE / f"{fid}.png"
    if out_path.exists() and out_path.stat().st_size > 5e5 and "--force" not in sys.argv:
        # only skip if explicitly cached; for this clean redo, always overwrite unless --skip-existing
        if "--skip-existing" in sys.argv:
            return (fid, "cached")
    backup(out_path)
    imgs = gen_image(scene_prompt)
    if ui_spec:
        final = composite_ui(imgs[0], ui_spec["ui"], ui_spec["rect"], ui_spec.get("src_crop"))
        final.save(out_path, format="PNG", optimize=True)
    else:
        out_path.write_bytes(imgs[0])
    return (fid, f"OK {out_path.stat().st_size:,}B")

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    todo = [(fid, p, ui) for fid, (p, ui) in SHOTS.items() if not args or fid in args]
    print(f"generating {len(todo)} frames via gpt-image-1 (~${len(todo)*0.19:.2f})…")
    with ThreadPoolExecutor(max_workers=3) as ex:
        futs = {ex.submit(do_one, fid, p, ui): fid for fid, p, ui in todo}
        for f in as_completed(futs):
            try:
                fid, status = f.result()
                print(f"  {fid:24} {status}")
            except Exception as e:
                print(f"  {futs[f]:24} FAIL  {e}")
    print("done.")

if __name__ == "__main__":
    main()
