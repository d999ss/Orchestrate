"""Generate END keyframes for Runway image-to-video first/last interpolation.

Each end frame is a CROPPED region of the corresponding storyboard PNG,
forcing the camera to "push in" / "pan toward" that region during interpolation.

Camera move per frame chosen for narrative weight:
- push-in: end = center crop (camera pushes forward)
- pan-and-push: end = offset crop (camera pans + pushes)
- orbit-feel: end = slight x-shift crop (camera arcs)
"""
import pathlib
from PIL import Image

ROOT = pathlib.Path("/Users/donnysmith/Projects/Orchestrate")
SRC = ROOT / "storyboard-1"
DST = ROOT / "storyboard-1" / "endframes"
DST.mkdir(exist_ok=True)

# (frame, crop_scale, x_offset_pct, y_offset_pct) per frame
# crop_scale = how much of the original to keep (smaller = more push-in)
# x/y offset = pan direction (positive = pan right/down, negative = pan left/up)
MOVES = {
    1:  (0.75, 0.0, 0.0),    # earth: subtle orbit-feel push
    2:  (0.60, 0.0, 0.0),    # push to plant: hard push-in
    3:  (0.75, 0.0, 0.0),    # turbine coupling: medium push
    4:  (0.55, 0.0, 0.0),    # combustion: push into the ring
    9:  (0.60, 0.10, 0.0),   # electricity: push + pan right along conductor
    10: (0.70, 0.0, 0.0),    # switchyard: push in
    11: (0.75, 0.0, -0.10),  # transformers: tilt up
    12: (0.55, 0.0, 0.0),    # transmission corridor: hard push down corridor
    13: (0.80, 0.0, 0.0),    # grid aerial: subtle push (already wide)
    18: (0.55, 0.0, 0.0),    # transmission to city: hard push toward city
    19: (0.55, 0.0, 0.0),    # Atlanta lighting: hard push to skyline
    20: (0.80, 0.10, 0.0),   # city spreading: gentle pan + push
    21: (0.70, 0.0, 0.0),    # stadium aerial: orbital feel via push
    25: (0.55, 0.0, 0.0),    # Signia exterior: hard push to building
    27: (0.50, 0.0, 0.0),    # keynote hall: HARDEST push down aisle to stage
    28: (0.65, 0.0, 0.0),    # stage finale: push in to stage
}

for frame, (scale, x_off, y_off) in MOVES.items():
    src_path = SRC / f"frame-{frame:02d}.png"
    if not src_path.exists():
        print(f"  missing {src_path}")
        continue
    img = Image.open(src_path)
    W, H = img.size
    new_w, new_h = int(W * scale), int(H * scale)
    # Center crop with offset
    cx = W / 2 + (W * x_off)
    cy = H / 2 + (H * y_off)
    left = max(0, int(cx - new_w / 2))
    top = max(0, int(cy - new_h / 2))
    right = min(W, left + new_w)
    bottom = min(H, top + new_h)
    cropped = img.crop((left, top, right, bottom))
    # Resize back to original dimensions (so first/last frames match size)
    end = cropped.resize((W, H), Image.LANCZOS)
    out_path = DST / f"frame-{frame:02d}-end.png"
    end.save(out_path)
    print(f"  f{frame:02d}: crop {scale}, offset ({x_off}, {y_off}) → {out_path.name}")

print(f"\nWrote {len(MOVES)} end keyframes to {DST}")
