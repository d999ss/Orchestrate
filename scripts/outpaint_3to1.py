#!/usr/bin/env python3
"""Outpaint SB4 frames from 3:2 (1536x1024) to true 3:1 (3072x1024) with gpt-image-1.

Flow (matches the manual ChatGPT method "fill out the rest of the frame"):
  - keep the original frame pixel-identical in the center (no crop, no drift)
  - generate a left and a right extension as separate gpt-image-1 edits,
    each anchored on the original's edge so the void/haze continues
  - composite [left_ext | original | right_ext] -> 3072x1024 (3:1), feathered joins

Usage:
  .venv/bin/python scripts/outpaint_3to1.py 8         # one frame (proof)
  .venv/bin/python scripts/outpaint_3to1.py           # all 30 missing
  .venv/bin/python scripts/outpaint_3to1.py --force 8
Output: storyboard-4/3to1-fill/frame-NN.png  (3072x1024)
"""
import os, sys, io, json, base64, pathlib
import requests
import numpy as np
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "storyboard-4"
OUT = SRC / "3to1-fill"
OUT.mkdir(parents=True, exist_ok=True)

KEY = json.loads(pathlib.Path(os.path.expanduser("~/.claude/secrets.json")).read_text())["openai"]["api_key"]
EDITS = "https://api.openai.com/v1/images/edits"
MODEL = "gpt-image-1"
EXT = 768          # px added on each side -> 1536 + 2*768 = 3072 (3:1 at h=1024)
FEATHER = 40       # px blend at each join
PROMPT = (
    "Fill out the rest of the frame. Continue the existing scene seamlessly into the empty area: "
    "the same dark near-black teal void, faint drifting cyan-teal particles, soft volumetric haze, "
    "matching grain, depth and lighting. Extend the environment naturally. "
    "No new focal subjects, no text, no logos, no letters, no numbers."
)


def edit(canvas_rgba, mask_rgba):
    """One gpt-image-1 edit call. canvas/mask are 1536x1024 RGBA PIL images."""
    def buf(im):
        b = io.BytesIO(); im.save(b, "PNG"); b.seek(0); return b
    files = {
        "image": ("canvas.png", buf(canvas_rgba), "image/png"),
        "mask": ("mask.png", buf(mask_rgba), "image/png"),
    }
    data = {"model": MODEL, "prompt": PROMPT, "size": "1536x1024", "n": "1", "quality": "medium"}
    r = requests.post(EDITS, headers={"Authorization": f"Bearer {KEY}"}, files=files, data=data, timeout=300)
    r.raise_for_status()
    b64 = r.json()["data"][0]["b64_json"]
    return Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB").resize((1536, 1024))


OVERLAP = 160      # px of cross-fade so the fill blends into the original with no seam


def side_extension(orig, side):
    """Generate one extension strip (EXT+OVERLAP wide) for 'left' or 'right' of orig."""
    W, H = 1536, 1024
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    mask = Image.new("RGBA", (W, H), (0, 0, 0, 0))   # alpha 0 = editable
    keep = Image.new("RGBA", (W, H), (0, 0, 0, 255)) # opaque = keep
    if side == "right":
        canvas.paste(orig.crop((W - EXT, 0, W, H)).convert("RGBA"), (0, 0))  # orig right edge as context
        mask.paste(keep.crop((0, 0, W - EXT, H)), (0, 0))                    # keep [0:768], fill [768:1536]
        out = edit(canvas, mask)
        return out.crop((W - EXT - OVERLAP, 0, W, H))   # width EXT+OVERLAP, overlap on the left
    else:
        canvas.paste(orig.crop((0, 0, EXT, H)).convert("RGBA"), (W - EXT, 0))  # orig left edge as context
        mask.paste(keep.crop((0, 0, W - EXT, H)), (W - EXT, 0))                # keep [768:1536], fill [0:768]
        out = edit(canvas, mask)
        return out.crop((0, 0, EXT + OVERLAP, H))       # width EXT+OVERLAP, overlap on the right


def fade_alpha(w, h, fade):
    a = np.full((h, w), 255, np.uint8)
    ramp = (np.arange(OVERLAP) / OVERLAP * 255).astype(np.uint8)
    if fade == "in":
        a[:, :OVERLAP] = ramp[None, :]
    else:
        a[:, w - OVERLAP:] = ramp[::-1][None, :]
    return Image.fromarray(a, "L")


def build(n, force=False):
    out_path = OUT / f"frame-{n:02d}.png"
    if out_path.exists() and out_path.stat().st_size > 5000 and not force:
        print(f"skip frame-{n:02d}"); return
    orig = Image.open(SRC / f"frame-{n:02d}.png").convert("RGB").resize((1536, 1024))
    right = side_extension(orig, "right")               # EXT+OVERLAP wide
    left = side_extension(orig, "left")
    canvas = Image.new("RGB", (1536 + 2 * EXT, 1024), (4, 9, 11))
    canvas.paste(orig, (EXT, 0))                                          # original at [768:2304]
    canvas.paste(left, (0, 0), fade_alpha(left.width, 1024, "out"))       # right edge fades into orig
    canvas.paste(right, (EXT + 1536 - OVERLAP, 0), fade_alpha(right.width, 1024, "in"))  # left edge fades in
    canvas.save(out_path)
    print(f"OK   frame-{n:02d} -> {out_path.name} ({canvas.size[0]}x{canvas.size[1]})")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    force = "--force" in sys.argv
    nums = [int(a) for a in args] if args else list(range(1, 31))
    for n in nums:
        try:
            build(n, force)
        except requests.HTTPError as e:
            print(f"FAIL frame-{n:02d}: HTTP {e.response.status_code}: {e.response.text[:200]}")
        except Exception as e:
            print(f"FAIL frame-{n:02d}: {e}")


if __name__ == "__main__":
    main()
