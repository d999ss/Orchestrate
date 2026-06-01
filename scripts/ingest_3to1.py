#!/usr/bin/env python3
"""Ingest browser-outpainted wide frames from the Desktop into the SB4 board at true 3:1.

For each frame N it looks on the Desktop for (first match wins):
  frame-NN.png / frame-N.png / Frame N.png / frame_NN.png   (.jpg/.jpeg/.webp ok too)
then normalizes to exact 3:1 and writes:
  storyboard-4/3to1-4k/frame-NN.png   4608x1536  (lightbox / wall master)
  storyboard-4/3to1/frame-NN.png      1536x512   (light card preview)

Usage:
  .venv/bin/python scripts/ingest_3to1.py 1          # one frame
  .venv/bin/python scripts/ingest_3to1.py 1 8 13     # several
  .venv/bin/python scripts/ingest_3to1.py            # every frame-*.png found on Desktop
"""
import os, sys, pathlib
from PIL import Image, ImageStat

ROOT = pathlib.Path(__file__).resolve().parent.parent
# Your live working folder: expand frames in place here, re-run, filled ones sync in.
DESK = pathlib.Path(os.path.expanduser("~/Desktop/Expanded Frames"))
DESK.mkdir(parents=True, exist_ok=True)
P4K = ROOT / "storyboard-4" / "3to1-4k"; P4K.mkdir(parents=True, exist_ok=True)
PPV = ROOT / "storyboard-4" / "3to1";    PPV.mkdir(parents=True, exist_ok=True)
WALL = (4608, 1536)        # exact 3:1 master
PREV = (1536, 512)         # exact 3:1 preview


def find(n):
    cands = [f"{n:02d}", f"{n}", f"frame-{n:02d}", f"frame-{n}", f"Frame {n}", f"frame_{n:02d}", f"Frame {n:02d}"]
    for stem in cands:
        for ext in (".png", ".jpg", ".jpeg", ".webp", ".PNG"):
            p = DESK / f"{stem}{ext}"
            if p.exists():
                return p
    return None


def fit_cover(im, size):
    """Scale to cover then center-crop to exact size (handles ~3:1 with tiny trim)."""
    tw, th = size
    w, h = im.size
    s = max(tw / w, th / h)
    im = im.resize((round(w * s), round(h * s)), Image.LANCZOS)
    w, h = im.size
    return im.crop(((w - tw) // 2, (h - th) // 2, (w - tw) // 2 + tw, (h - th) // 2 + th))


def is_padded(im):
    """True if the frame is a prep canvas (original centered, dead-black side bars)
    rather than a real outpaint. Filled frames carry faint particle noise to the edges."""
    g = im.convert("L"); w, h = g.size
    L = ImageStat.Stat(g.crop((0, 0, 90, h)))
    R = ImageStat.Stat(g.crop((w - 90, 0, w, h)))
    return (L.mean[0] < 2 and R.mean[0] < 2 and L.stddev[0] < 4 and R.stddev[0] < 4)


def ingest(n, force=False):
    src = find(n)
    if not src:
        print(f"--   frame-{n:02d}: nothing in drop folder")
        return False
    im = Image.open(src).convert("RGB")
    if is_padded(im) and not force:
        print(f"WAIT frame-{n:02d}: still a prep canvas (black sides) — needs expanding, skipped")
        return False
    fit_cover(im, WALL).save(P4K / f"frame-{n:02d}.png")
    fit_cover(im, PREV).save(PPV / f"frame-{n:02d}.png")
    print(f"OK   frame-{n:02d}: {src.name} ({im.size[0]}x{im.size[1]}) -> 4608x1536 + 1536x512")
    return True


def main():
    force = "--force" in sys.argv
    args = [int(a) for a in sys.argv[1:] if not a.startswith("--")]
    nums = args or list(range(1, 31))
    done = sum(ingest(n, force) for n in nums)
    print(f"\ningested {done}/{len(nums)} (rest still need expanding)")


if __name__ == "__main__":
    main()
