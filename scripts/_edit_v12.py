#!/usr/bin/env python3
"""
v12 — evergreen particles, black background.

User clarification: background stays black. The particles need to read as
evergreen (more green, less blue) not cyan-blue. Hue shift + colorchannel
remap brings the dot color into the brand spec.
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RDIR = ROOT / "electron" / "_render"
ELECTRON = ROOT / "electron"
DM = ROOT / "electron" / "_dotmatrix"
AUDIO = ROOT / "references" / "demand-audio.m4a"
PLAN = json.loads((ROOT / "scripts" / "clip_plan.json").read_text())
OUT = ROOT / "films" / "electron_v12.mp4"
TMP = Path("/tmp/electron_v12")
TMP.mkdir(exist_ok=True, parents=True)

# Evergreen grade: hue shift -12° (cyan → green-cyan), reduce blue channel,
# boost green slightly. Keeps blacks black.
GRADE = (
    "hue=h=-12,"
    "colorchannelmixer="
    "rr=0.97:rg=0.03:rb=0.00:"
    "gr=0.00:gg=1.05:gb=0.05:"
    "br=0.00:bg=0.10:bb=0.78,"
    "eq=contrast=1.06:brightness=-0.015:saturation=1.12,"
    "vignette=angle=PI/5:mode=backward"
)

DM_OVERRIDES = {
    14: "dm_09_58_06.png",
    23: "dm_09_58_06.png",
    30: "dm_09_54_08.png",
    32: "dm_09_54_57.png",
    33: "dm_09_54_57.png",
    34: "dm_09_55_28.png",
    35: "dm_09_55_28.png",
    36: "dm_09_55_28.png",
}

SPEED = 1.25


def run(cmd):
    subprocess.run(cmd, check=True)


def ken_burns_png(png_path, dur, dst, direction="in", strength=0.05):
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
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-loop", "1", "-i", str(png_path),
        "-t", f"{dur}",
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-r", f"{fps}", "-an",
        str(dst),
    ])


def make_intro_part_1():
    dst = TMP / "intro_a.mp4"
    print("INTRO A · slow zoom-in (evergreen particles)")
    ken_burns_png(ELECTRON / "01a_origin.png", 3.0, dst, direction="in", strength=0.06)
    return dst


def make_intro_part_2():
    a = ELECTRON / "01a_origin.png"
    b = DM / "dm_09_58_06.png"
    fps = 24
    total_dur = 5.0

    layer_a = TMP / "intro_b_a.mp4"
    ken_burns_png(a, total_dur, layer_a, direction="out", strength=0.30)
    layer_b = TMP / "intro_b_b.mp4"
    ken_burns_png(b, total_dur, layer_b, direction="in", strength=0.08)

    dst = TMP / "intro_b.mp4"
    print("INTRO B · sustained reveal · operator-dot-matrix")
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

    if idx in DM_OVERRIDES:
        png = DM / DM_OVERRIDES[idx]
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
    print(f"v12 · evergreen particles (black bg) · {len(clips)} clips")

    paths = [make_intro_part_1(), make_intro_part_2()]
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
