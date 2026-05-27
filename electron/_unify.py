#!/usr/bin/env python3
"""Deck-wide unify pass — bring frames that don't match the brand asset
into the same field-as-canvas language.

Two kinds of fix:
  RECOLOR  → for 07A/07B/07C which have gold/amber/lime color violations.
             Strip to luminance, retint to evergreen+cyan only, then
             composite onto the brand GIF field for unity.
  PHOTOFIELD → for 08A/08B/09A/09B which are photo-real or duotone
             photos that don't sit in the dot-matrix world. Composite
             onto the brand field at reduced opacity so the field
             breathes through, with feathered edges.

Frames that are already on-brand (08C, 09C, 05A/B/C) are left alone.
"""
import sys, subprocess
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter, ImageChops, ImageDraw, ImageOps

ROOT = Path(__file__).parent
GIF = Path.home() / "Desktop" / "Orchestrate 2026-selected" / "Orchestrate Keynote PPT GIF.gif"
TMP = Path("/tmp")
SHIMMER = Image.open(ROOT/"shimmer.png").convert("RGB")

def gif_field(width=1920, height=1080):
    """Same field source as _field_compose: 3-frame lighten-blend from
    the brand GIF, scale-to-fill, center-crop."""
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

def backup(path):
    bak = path.with_suffix(".bak.png")
    if not bak.exists():
        bak.write_bytes(path.read_bytes())
    return bak

def recolor_to_brand(src_path):
    """Strip color from a frame, retint to evergreen+cyan gradient.
    Maps shadows → deep evergreen #003a38, midtones → mid-evergreen,
    highlights → cyan #7ec5b9 (muted, not neon). Then composite onto
    the brand field at ~75% opacity for unity."""
    src = Image.open(src_path).convert("RGB")
    # Strip to luminance
    lum = ImageOps.grayscale(src)
    # Re-tint via a 3-color gradient lookup
    palette_img = Image.new("RGB", (1, 256))
    px = palette_img.load()
    for v in range(256):
        # Black → deep evergreen → mid-evergreen → cyan-white
        if v < 80:
            t = v / 80
            r = int(5 + (20-5)*t); g = int(35 + (75-35)*t); b = int(40 + (75-40)*t)
        elif v < 180:
            t = (v - 80) / 100
            r = int(20 + (90-20)*t); g = int(75 + (180-75)*t); b = int(75 + (175-75)*t)
        else:
            t = (v - 180) / 75
            r = int(90 + (200-90)*t); g = int(180 + (240-180)*t); b = int(175 + (235-175)*t)
        px[0, v] = (r, g, b)
    palette_img = palette_img.resize((1, 256), Image.NEAREST)
    # Apply LUT per-channel via point lookup
    def lookup(v): return palette_img.getpixel((0, v))
    out = Image.new("RGB", src.size)
    out_px = out.load()
    lum_px = lum.load()
    for y in range(src.size[1]):
        for x in range(src.size[0]):
            out_px[x, y] = lookup(lum_px[x, y])
    return out

def composite_onto_field(content, field, opacity=0.78, feather_px=40):
    """Drop content onto field with feathered edges + opacity. Used both
    for recolored 07s and for photo frames in 08/09."""
    content = content.resize(field.size, Image.LANCZOS) if content.size != field.size else content
    base_alpha = Image.new("L", content.size, int(255 * opacity))
    feather = Image.new("L", content.size, 0)
    margin = feather_px + 20
    ImageDraw.Draw(feather).rectangle(
        (margin, margin, content.size[0] - margin, content.size[1] - margin), fill=255)
    feather = feather.filter(ImageFilter.GaussianBlur(feather_px))
    mask = ImageChops.multiply(base_alpha, feather)
    out = field.copy()
    out.paste(content, (0, 0), mask)
    return out

def brand_shimmer(im, strength=0.18):
    """Light shimmer screen-blend so the frame ties to the brand thread."""
    sh = SHIMMER.resize(im.size, Image.LANCZOS)
    return ImageChops.screen(im, ImageEnhance.Brightness(sh).enhance(strength))

# Per-frame treatment plan
RECOLOR_TARGETS = ["07a_gold_burst", "07b_lime_ripple", "07c_climax"]
PHOTOFIELD_TARGETS = {
    # photo opacity (lower = more field showing through)
    "08a_atlanta":       0.82,
    "08b_distribution":  0.82,
    "09a_venue_dawn":    0.82,
    "09b_keynote_stage": 0.82,
}

def go():
    print("[1/2] pulling brand field…", flush=True)
    field = gif_field()

    for fid in RECOLOR_TARGETS:
        p = ROOT / f"{fid}.png"
        if not p.exists(): print(f"  skip {fid} (missing)"); continue
        backup(p)
        print(f"  RECOLOR  {fid}…", flush=True)
        recolored = recolor_to_brand(p)
        out = composite_onto_field(recolored, field, opacity=0.85, feather_px=20)
        out = brand_shimmer(out, 0.14)
        out.save(p, format="PNG", optimize=True)
        print(f"    {p.stat().st_size:,} bytes")

    for fid, opacity in PHOTOFIELD_TARGETS.items():
        p = ROOT / f"{fid}.png"
        if not p.exists(): print(f"  skip {fid} (missing)"); continue
        backup(p)
        print(f"  PHOTOFIELD  {fid}  opacity={opacity}…", flush=True)
        photo = Image.open(p).convert("RGB")
        # Pull photo toward evergreen
        photo = ImageEnhance.Color(photo).enhance(0.55)
        photo = ImageEnhance.Brightness(photo).enhance(0.92)
        out = composite_onto_field(photo, field, opacity=opacity, feather_px=60)
        out = brand_shimmer(out, 0.16)
        out.save(p, format="PNG", optimize=True)
        print(f"    {p.stat().st_size:,} bytes")

if __name__ == "__main__":
    go()
