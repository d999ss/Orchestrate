"""Render the Bttr. Technical slate PNG for the SB1 film intro.

Classic aerospace/film-leader layout: deep black, emerald accent, monospace labels.
Logo: Bttr.'s actual SVG glyphs drawn directly with PIL (square ring + circle ring + arc).
"""
import sys
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080
BG = (4, 9, 11)
ACCENT = (78, 217, 198)
DIM = (122, 169, 164)
FG = (205, 235, 231)
LINE = (20, 48, 46)

HOME = Path.home()
def find_font(candidates, size):
    for path in candidates:
        try:
            return ImageFont.truetype(str(path), size)
        except Exception:
            continue
    return ImageFont.load_default()

# Real brand fonts from user's library
DISPLAY = [
    HOME / "Library/Fonts/Graphik-Bold.otf",
    HOME / "Library/Fonts/Graphik-Semibold.otf",
    HOME / "Library/Fonts/Graphik-Medium.otf",
]
SANS = [
    HOME / "Library/Fonts/Graphik-Medium.otf",
    HOME / "Library/Fonts/Graphik-Regular.otf",
]
SANS_LIGHT = [
    HOME / "Library/Fonts/Graphik-Regular.otf",
    HOME / "Library/Fonts/Graphik-Light.otf",
]
MONO = [
    HOME / "Library/Fonts/IBMPlexMono-Medium.ttf",
    HOME / "Library/Fonts/IBMPlexMono-Regular.ttf",
]
MONO_LIGHT = [
    HOME / "Library/Fonts/IBMPlexMono-Regular.ttf",
    HOME / "Library/Fonts/IBMPlexMono-Light.ttf",
]

# Render at 2x for sharpness, downsample
SUPERSAMPLE = 2
f_eyebrow = find_font(MONO,        18 * SUPERSAMPLE)
f_label   = find_font(MONO,        20 * SUPERSAMPLE)
f_value   = find_font(MONO_LIGHT,  20 * SUPERSAMPLE)
f_footer  = find_font(MONO_LIGHT,  16 * SUPERSAMPLE)
f_sub     = find_font(MONO,        22 * SUPERSAMPLE)

# Render at 2x then downsample for crisp text
img = Image.new("RGB", (W * SUPERSAMPLE, H * SUPERSAMPLE), BG)
d = ImageDraw.Draw(img)

S = SUPERSAMPLE
def sx(v): return int(v * S)


def draw_bttr_logo(draw_obj, ox, oy, scale):
    """Draw the Bttr. logo (square + circle + arc) at origin (ox,oy) with given scale.

    SVG viewBox is 0 0 51 40. We scale into the destination size.
    """
    s = scale * S
    # Square ring: outer 0,0 → 21.9,21.8; inner 3.64,3.62 → 18.26,18.18
    outer = (ox + 0*s, oy + 0*s, ox + 21.9*s, oy + 21.8*s)
    inner = (ox + 3.64*s, oy + 3.62*s, ox + 18.26*s, oy + 18.18*s)
    # Draw outer rect filled, then punch the inner with background
    draw_obj.rectangle(outer, fill=FG)
    draw_obj.rectangle(inner, fill=BG)
    # Circle ring: center (39.12,15.51), outer r=11.80, inner r=8.18
    cx, cy = ox + 39.12*s, oy + 15.51*s
    r_out, r_in = 11.80*s, 8.18*s
    draw_obj.ellipse((cx-r_out, cy-r_out, cx+r_out, cy+r_out), fill=FG)
    draw_obj.ellipse((cx-r_in, cy-r_in, cx+r_in, cy+r_in), fill=BG)
    # Bottom arc / smile: approximate path 3
    # Path 3 vertices (approximation):
    pts = [
        (9.19, 29.05),
        (9.63, 35.16),
        (14.77, 40.00),
        (21.03, 40.00),
        (25.82, 40.00),
        (29.95, 37.16),
        (31.83, 33.09),
        (28.66, 31.26),
        (27.44, 34.27),
        (24.48, 36.38),
        (21.03, 36.38),
        (16.77, 36.38),
        (13.27, 33.17),
        (12.84, 29.05),
    ]
    poly = [(ox + x*s, oy + y*s) for x, y in pts]
    draw_obj.polygon(poly, fill=FG)


# Outer thin rule frame
PAD = 64
d.rectangle([sx(PAD), sx(PAD), sx(W-PAD), sx(H-PAD)], outline=LINE, width=S)

# Top-left eyebrow
d.text((sx(PAD+24), sx(PAD+28)), "BTTR · TECHNICAL", fill=ACCENT, font=f_eyebrow)
# Top-right ID
d.text((sx(W-PAD-24-360), sx(PAD+28)), "ID  SB1.V5.E.250528.A", fill=DIM, font=f_eyebrow)

# Bttr. logo as real graphic — big anchor
logo_x = sx(PAD + 24)
logo_y = sx(280)
draw_bttr_logo(d, sx(PAD+24), sx(280), 6.0)  # scale 6 → ~314x245 in 2x space → 157x123 final

# Project subtitle below logo
sub_y = sx(450)
d.text((sx(PAD+24), sub_y), "ORCHESTRATE  2026   ·   STORYBOARD  01", fill=ACCENT, font=f_sub)

# Horizontal rule
rule_y = sx(530)
d.line([(sx(PAD+24), rule_y), (sx(W-PAD-24), rule_y)], fill=LINE, width=S)

# Metadata grid
rows = [
    ("PROJECT",     "ORCHESTRATE  2026"),
    ("CONCEPT",     "01  ·  EARTH TO KEYNOTE"),
    ("CUT",         "V5  ·  RAW"),
    ("STATUS",      "WIP  ·  FOR INTERNAL REVIEW"),
    ("DATE",        "2026.05.28"),
    ("RUNTIME",     "00:60"),
    ("FRAMES",      "30  ·  AI-GENERATED"),
    ("AUDIO",       "BEATS.MP3  ·  130.8  BPM"),
    ("COLOR",       "EMERALD  v5"),
    ("RESOLUTION",  "1920 × 1080  ·  H.264"),
]
row_y = sx(580)
row_h = sx(36)
label_x = sx(PAD+24)
value_x = sx(PAD+280)
for label, value in rows:
    d.text((label_x, row_y), label, fill=DIM, font=f_label)
    d.text((value_x, row_y), value, fill=FG, font=f_value)
    row_y += row_h

# Bottom rule + footer
foot_rule_y = row_y + sx(16)
d.line([(sx(PAD+24), foot_rule_y), (sx(W-PAD-24), foot_rule_y)], fill=LINE, width=S)
d.text((sx(PAD+24), foot_rule_y + sx(24)),
       "FOR INTERNAL REVIEW ONLY  ·  DO NOT DISTRIBUTE  ·  © 2026 BELIEVE IN BTTR LLC",
       fill=DIM, font=f_footer)
d.text((sx(W-PAD-24-130), foot_rule_y + sx(24)), "WIP  v5", fill=ACCENT, font=f_footer)

# Downsample for crisp text
final = img.resize((W, H), Image.LANCZOS)

out = Path(sys.argv[1] if len(sys.argv) > 1 else "slate.png")
final.save(out, optimize=True)
print(f"Wrote {out}")
