#!/usr/bin/env python3
"""Push 04C / 05A / 05B / 05C toward 08B's grounded human-scale energy by
re-framing the existing processed frames to focus on a single incident/
crew/route — same UI source, tighter composition. 16:9 crops scaled to
1920×1080. Writes new PNGs in place (originals backed up to .bak.png)."""
from PIL import Image
from pathlib import Path
import shutil, sys
ROOT = Path(__file__).parent

# Each entry: (frame_id, crop_box (left, top, right, bottom)).
# Crops are 16:9 so they scale cleanly to 1920×1080. Boxes chosen by eye
# against the actual frames to keep the most "08B-like" detail visible.
RECROPS = {
    # Action Center column + first half of AI Scorecard — one set of
    # incidents being acted on. Drops the four aggregate right panels.
    "04c_full_mesh":   (0,    180, 1280, 900),
    # Tighter region of the dispatch map showing a few named crews +
    # their neighborhood. Drops the long crew-list margin on the left.
    "05a_paths_fan":   (240,  120, 1840, 1020),
    # Zoom into the incident detail card (Incident 926483, Mathew Hart,
    # Autumn Street, AI conf 90%). 08B-feel: one human, one place.
    "05b_gridos":      (640,  120, 1920, 840),
    # One crew row across the day timeline — Mathew Hart's actual shift.
    "05c_path_chosen": (0,    160, 1600, 1060),
}

def push(fid, box):
    src = ROOT / f"{fid}.png"
    bak = ROOT / f"{fid}.bak.png"
    if not bak.exists():
        shutil.copy(src, bak)
    im = Image.open(src).convert("RGB")
    cropped = im.crop(box)
    # Upscale to 1920×1080 (Lanczos for sharpness). Confirms 16:9 by ratio.
    w, h = cropped.size
    assert abs((w/h) - (16/9)) < 0.01, f"{fid} crop is not 16:9: {w}x{h}"
    out = cropped.resize((1920, 1080), Image.LANCZOS)
    out.save(src, format="PNG", optimize=True)
    print(f"  {fid:24} {box[2]-box[0]}x{box[3]-box[1]} -> 1920x1080")

def main():
    only = set(sys.argv[1:]) if len(sys.argv)>1 else None
    todo = [(k,v) for k,v in RECROPS.items() if not only or k in only]
    print(f"pushing {len(todo)} frames toward 08B…")
    for fid, box in todo:
        push(fid, box)
    print("done — originals backed up to *.bak.png; git diff to compare")

if __name__ == "__main__":
    main()
