#!/usr/bin/env python3
"""Field-as-world composite — extended to 05A/05B/05C with per-shot
UI source-crops and per-shot composite shapes so each frame reads as
a DIFFERENT moment of GridOS, not three angles on the same screen.

The brand keynote GIF is the canvas. Each shot composites a tightly
cropped UI region into that canvas at a shape tuned to its caption:

  05A  Paths across the region  → just the regional map (no crew column),
                                  ~roughly-square, calm wide composition
  05B  GridOS recommends         → just the incident-detail card + crew
                                  panel zoomed tight, intimate decision
  05C  Dispatch committed        → just the gantt strip (no crew column,
                                  no header), wide horizontal ticker
"""
import sys, subprocess
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter, ImageChops, ImageDraw

ROOT = Path(__file__).parent
GIF = Path.home() / "Desktop" / "Orchestrate 2026-selected" / "Orchestrate Keynote PPT GIF.gif"
TMP = Path("/tmp")
assert GIF.exists(), f"missing brand GIF at {GIF}"

# Per-shot config: source bak, region to crop FROM the bak (left, top,
# right, bottom in source coords), final composite size (w, h), and the
# (x, y) anchor on the 1920x1080 canvas.
SHOTS = {
    # 05A — just the regional MAP (no crew list, no header, no metrics)
    "05a": {
        "src":     "05a_paths_fan.bak.png",
        "out":     "05a_paths_fan.png",
        "ui_crop": (470, 280, 1920, 1080),   # map area only
        "ui_size": (1400, 775),               # roughly-square, dominant
        "anchor":  (260, 152),
    },
    # 05B — just the RIGHT CREW-DETAIL panel (portrait, intimate decision)
    "05b": {
        "src":     "05b_gridos.bak.png",
        "out":     "05b_gridos.png",
        "ui_crop": (1365, 280, 1930, 1045),  # right crew detail panel only
        "ui_size": (590, 800),                # portrait, single moment
        "anchor":  (665, 140),
    },
    # 05C — gantt rows only (skip metrics, tabs, header) — wide ticker
    "05c": {
        "src":     "05c_path_chosen.bak.png",
        "out":     "05c_path_chosen.png",
        "ui_crop": (470, 427, 1920, 1024),   # gantt cells, multiple rows
        "ui_size": (1740, 715),               # wide horizontal block
        "anchor":  (90, 182),
    },
}

def gif_field(width=1920, height=1080):
    """Lighten-blend three frames from the brand GIF, scale-to-fill,
    center-crop to (width, height)."""
    frames_dir = TMP / "_gif_frames"
    frames_dir.mkdir(exist_ok=True)
    for f in frames_dir.glob("*.png"): f.unlink()
    subprocess.run(["ffmpeg", "-y", "-i", str(GIF), "-vf",
                    "select='eq(n,8)+eq(n,20)+eq(n,32)',scale=3240:-1",
                    "-vsync", "vfr", str(frames_dir/"f_%02d.png")],
                   check=True, capture_output=True)
    frames = sorted(frames_dir.glob("f_*.png"))
    base = Image.open(frames[0]).convert("RGB")
    for f in frames[1:]:
        base = ImageChops.lighter(base, Image.open(f).convert("RGB"))
    w, h = base.size
    if h != height:
        base = base.resize((int(w*height/h), height), Image.LANCZOS)
        w, h = base.size
    x0 = (w - width) // 2
    return base.crop((x0, 0, x0 + width, height))

def composite_into_field(field, ui_src_path, ui_crop, ui_size, anchor):
    """Carve a soft darker well, drop the cropped UI into it with
    feathered edges so the UI emerges within the field, not on top."""
    src = Image.open(ROOT/ui_src_path).convert("RGB").crop(ui_crop)
    ui = src.resize(ui_size, Image.LANCZOS)
    ui = ImageEnhance.Brightness(ui).enhance(0.92)
    ui = ImageEnhance.Color(ui).enhance(0.62)

    x, y = anchor
    out = field.copy()

    # Soft darker well behind the UI region
    well = Image.new("L", field.size, 255)
    ImageDraw.Draw(well).rectangle(
        (x - 30, y - 30, x + ui.size[0] + 30, y + ui.size[1] + 30), fill=120)
    well = well.filter(ImageFilter.GaussianBlur(60))
    field_dim = Image.eval(out, lambda v: int(v * 0.62))
    out = Image.composite(out, field_dim, well)

    # Feathered alpha on the UI itself
    feather = Image.new("L", ui.size, 0)
    ImageDraw.Draw(feather).rectangle(
        (30, 30, ui.size[0]-30, ui.size[1]-30), fill=255)
    feather = feather.filter(ImageFilter.GaussianBlur(28))
    base_alpha = Image.new("L", ui.size, 235)  # ~92% opacity
    mask = ImageChops.multiply(base_alpha, feather)

    out.paste(ui, (x, y), mask)
    return out

def go(shot_id):
    spec = SHOTS[shot_id]
    print(f"[1/3] field from brand GIF…", flush=True)
    field = gif_field()
    print(f"[2/3] composite UI: crop={spec['ui_crop']} size={spec['ui_size']} anchor={spec['anchor']}", flush=True)
    composed = composite_into_field(field, spec["src"], spec["ui_crop"],
                                    spec["ui_size"], spec["anchor"])
    out = ROOT / spec["out"]
    composed.save(out, format="PNG", optimize=True)
    print(f"WROTE  {out}  ({out.stat().st_size:,} bytes)")

if __name__ == "__main__":
    targets = sys.argv[1:] or ["05a", "05b", "05c"]
    for t in targets:
        go(t)
