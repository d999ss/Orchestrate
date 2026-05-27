#!/usr/bin/env python3
"""
v10 — dot-matrix subject pass + intro motion.

Adds slow motion to the cold open (no more static), and slots the 4 new
dot-matrix subject PNGs into their beats. These are the brand-language
reference frames the client wants.

  Cold open (0-3s):     01a_origin · slow zoom-IN (subtle motion, not static)
  Reveal (3-8s):        sustained cross-fade with operator-dotmatrix
                        replacing the abstract dot-grid for instant impact
  Beat 08a:             Mercedes-Benz Stadium dot-matrix · slow zoom
  Beat 09a:             Signia by Hilton dot-matrix · slow zoom
  Beat 09b/09c:         Keynote hall dot-matrix (ORCHESTRATE 2026 in-image)
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RDIR = ROOT / "electron" / "_render"
OPER = ROOT / "electron" / "_render_operator"
ELECTRON = ROOT / "electron"
DM = ROOT / "electron" / "_dotmatrix"
AUDIO = ROOT / "references" / "demand-audio.m4a"
PLAN = json.loads((ROOT / "scripts" / "clip_plan.json").read_text())
OUT = ROOT / "films" / "electron_v10.mp4"
TMP = Path("/tmp/electron_v10")
TMP.mkdir(exist_ok=True, parents=True)

GRADE = (
    "eq=contrast=1.08:brightness=-0.02:saturation=1.10,"
    "colorchannelmixer="
    "rr=0.97:rg=0.03:rb=0.00:"
    "gr=0.00:gg=1.00:gb=0.02:"
    "br=0.00:bg=0.02:bb=1.02,"
    "vignette=angle=PI/5:mode=backward"
)

# Map clip index → dot-matrix PNG override
DM_OVERRIDES = {
    14: "dm_09_58_06.png",       # 05b_gridos beat — use operator-dot-matrix
    23: "dm_09_58_06.png",       # 05b_gridos again — same operator
    30: "dm_09_54_08.png",       # 08a_atlanta — Mercedes-Benz Stadium dot-matrix
    32: "dm_09_54_57.png",       # 09a_venue_dawn — Signia dot-matrix
    33: "dm_09_54_57.png",       # 09a breath — Signia held
    34: "dm_09_55_28.png",       # 09b_keynote_stage — keynote hall dot-matrix
    35: "dm_09_55_28.png",       # 09c_hero_hold begin — keynote hall continues
    36: "dm_09_55_28.png",       # 09c TITLE LAND — ORCHESTRATE 2026 already in image
}

SPEED = 1.25


def run(cmd):
    subprocess.run(cmd, check=True)


def ken_burns_png(png_path, dur, dst, direction="in", strength=0.05):
    """Slow zoom on a still PNG."""
    fps = 24
    nb_frames = int(dur * fps)
    if direction == "in":
        z_expr = f"min(zoom+{strength/dur/fps*1.5},1+{strength})"
    else:
        z_expr = f"if(eq(on,0),{1+strength},max(zoom-{strength/dur/fps*1.5},1.0))"
    vf = (
        f"scale=1920:1080:flags=lanczos,setsar=1,"
        f"zoompan=z='{z_expr}':d={nb_frames}:s=1920x1080:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':fps={fps},"
        f"{GRADE}"
    )
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-loop", "1", "-i", str(png_path),
        "-t", f"{dur}",
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-r", f"{fps}", "-an",
        str(dst),
    ]
    run(cmd)


def make_intro_part_1():
    """0.0-3.0s · slow zoom-IN on 01a_origin (not static — subtle motion)."""
    png = ELECTRON / "01a_origin.png"
    dst = TMP / "intro_a.mp4"
    print("INTRO A · 0-3s slow zoom-in on 01a_origin (motion restored)")
    ken_burns_png(png, 3.0, dst, direction="in", strength=0.06)
    return dst


def make_intro_part_2():
    """3.0-8.0s · sustained 5s reveal · 01a → operator dot-matrix cross-fade."""
    a = ELECTRON / "01a_origin.png"
    b = DM / "dm_09_58_06.png"   # operator dot-matrix as the reveal target — strong impact
    fps = 24
    total_dur = 5.0
    nb_frames = int(total_dur * fps)

    layer_a = TMP / "intro_b_a.mp4"
    ken_burns_png(a, total_dur, layer_a, direction="out", strength=0.30)

    layer_b = TMP / "intro_b_b.mp4"
    ken_burns_png(b, total_dur, layer_b, direction="in", strength=0.08)

    dst = TMP / "intro_b.mp4"
    print("INTRO B · 3-8s sustained reveal · 01a → operator-dot-matrix")
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(layer_a), "-i", str(layer_b),
        "-filter_complex",
        f"[0:v][1:v]xfade=transition=fade:duration=3.5:offset=1.5[out]",
        "-map", "[out]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
        str(dst),
    ])
    return dst


def make_body_clip(c):
    idx = c["i"]
    name = c["clip"]
    in_s = c["src_in"]
    dur = c["t_out"] - c["t_in"]
    dst = TMP / f"c{idx:02d}.mp4"

    # Dot-matrix PNG override
    if idx in DM_OVERRIDES:
        png = DM / DM_OVERRIDES[idx]
        if png.exists():
            print(f"  [{idx:2d}] DM-PNG → {DM_OVERRIDES[idx]} · {dur:.2f}s")
            direction = "in" if idx % 2 == 0 else "out"
            ken_burns_png(png, dur, dst, direction=direction, strength=0.06)
            return dst

    is_breath = "BREATH" in (c.get("anchor") or "").upper()
    speed = 1.0 if is_breath else SPEED
    source_dur = dur * speed

    src_file = RDIR / f"{name}.mp4"
    if not src_file.exists():
        sys.exit(f"missing {name}")

    setpts = f"setpts=PTS/{speed}"
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-ss", f"{in_s}", "-i", str(src_file), "-t", f"{source_dur}",
        "-vf", f"{setpts},{GRADE}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-r", "24", "-an",
        str(dst),
    ]
    run(cmd)
    return dst


def main():
    clips = PLAN["clips"]
    print(f"v10 · dot-matrix pass + motion intro · {len(clips)} clips")

    paths = []
    paths.append(make_intro_part_1())
    paths.append(make_intro_part_2())

    for c in clips:
        if c["t_out"] <= 8.0:
            continue
        paths.append(make_body_clip(c))

    print("\nconcat…")
    list_path = TMP / "concat.txt"
    list_path.write_text("\n".join(f"file '{p}'" for p in paths))
    vcat = TMP / "vcat.mp4"
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "concat", "-safe", "0", "-i", str(list_path),
        "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
        str(vcat),
    ])

    print("mux audio…")
    OUT.parent.mkdir(exist_ok=True, parents=True)
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(vcat), "-i", str(AUDIO),
        "-map", "0:v", "-map", "1:a",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart",
        str(OUT),
    ])
    print(f"\ndone · {OUT}")
    subprocess.run([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration,size",
        "-show_entries", "stream=codec_name,width,height",
        "-of", "default=noprint_wrappers=1",
        str(OUT),
    ])


if __name__ == "__main__":
    main()
