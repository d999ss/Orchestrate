#!/usr/bin/env python3
"""Render the ORCHESTRATE 2026 title as a transparent 4K PNG."""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "electron" / "_render_4k" / "orchestrate_title.png"

W, H = 3840, 2160
img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

font_path = "/System/Library/Fonts/Supplemental/Impact.ttf"
big = ImageFont.truetype(font_path, 360)
small = ImageFont.truetype(font_path, 140)

LIME = (166, 255, 0, 255)
WHITE = (255, 255, 255, 220)

txt1 = "ORCHESTRATE"
bbox1 = draw.textbbox((0, 0), txt1, font=big)
w1 = bbox1[2] - bbox1[0]
h1 = bbox1[3] - bbox1[1]
x1 = (W - w1) // 2
y1 = (H - h1) // 2 - 120
draw.text((x1, y1), txt1, font=big, fill=LIME)

txt2 = "2026"
bbox2 = draw.textbbox((0, 0), txt2, font=small)
w2 = bbox2[2] - bbox2[0]
x2 = (W - w2) // 2
y2 = y1 + h1 + 60
draw.text((x2, y2), txt2, font=small, fill=WHITE)

OUT.parent.mkdir(parents=True, exist_ok=True)
img.save(OUT)
print(f"wrote {OUT}")
