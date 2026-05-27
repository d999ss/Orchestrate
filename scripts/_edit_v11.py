#!/usr/bin/env python3
"""
v11 — evergreen base.

v10's blacks were pure #000. The conference shimmer reference is evergreen
(#003c3a). Every clip needs to sit on that evergreen base so the film matches
the shimmer wall behind the keynote screen.

Method: composite each clip over a solid evergreen layer using screen blend.
Black pixels lift to evergreen, cyan dot-matrix stays cyan.
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
OUT = ROOT / "films" / "electron_v11.mp4"
TMP = Path("/tmp/electron_v11")
TMP.mkdir(exist_ok=True, parents=True)

# Evergreen base color from brand spec: #003c3a
EVERGREEN = "0x003c3a"

# Grade chain with shadow lift toward evergreen.
# colorbalance shifts shadows: less red, more green, slight blue lift toward teal.
# Then curves slightly lifts the black point so pure black becomes ~3% green.
GRADE = (
    "colorbalance=rs=-0.20:gs=0.18:bs=0.08:"
    "rm=-0.05:gm=0.05:bm=0.02,"
    "eq=contrast=1.06:brightness=-0.005:saturation=1.10,"
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


def composite_over_evergreen(in_path, out_path, dur, scale_first=False):
    """Composite the clip over an evergreen base, lifting blacks to teal."""
    scale = "scale=1920:1080:flags=lanczos," if scale_first else ""
    # Use lighten blend with evergreen base: max(clip, evergreen)
    # This keeps cyan dots bright but ensures background is at least evergreen.
    filter_complex = (
        f"color=c={EVERGREEN}:s=1920x1080:r=24:d={dur}[bg];"
        f"[0:v]{scale}{GRADE}[fg];"
        f"[bg][fg]blend=all_mode=lighten[out]"
    )
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(in_path),
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-t", f"{dur}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-r", "24", "-an",
        str(out_path),
    ])


def ken_burns_png(png_path, dur, dst, direction="in", strength=0.05):
    fps = 24
    nb_frames = int(dur * fps)
    if direction == "in":
        z_expr = f"min(zoom+{strength/dur/fps*1.5},1+{strength})"
    else:
        z_expr = f"if(eq(on,0),{1+strength},max(zoom-{strength/dur/fps*1.5},1.0))"
    # First render without grade (we'll composite + grade after)
    tmp_raw = dst.with_suffix(".raw.mp4")
    vf = (
        f"scale=1920:1080:flags=lanczos,setsar=1,"
        f"zoompan=z='{z_expr}':d={nb_frames}:s=1920x1080:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':fps={fps}"
    )
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-loop", "1", "-i", str(png_path),
        "-t", f"{dur}",
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-r", f"{fps}", "-an",
        str(tmp_raw),
    ])
    composite_over_evergreen(tmp_raw, dst, dur)
    tmp_raw.unlink()


def make_intro_part_1():
    dst = TMP / "intro_a.mp4"
    print("INTRO A · 0-3s slow zoom-in on 01a_origin (evergreen base)")
    ken_burns_png(ELECTRON / "01a_origin.png", 3.0, dst, direction="in", strength=0.06)
    return dst


def make_intro_part_2():
    a = ELECTRON / "01a_origin.png"
    b = DM / "dm_09_58_06.png"
    fps = 24
    total_dur = 5.0

    raw_a = TMP / "intro_b_a_raw.mp4"
    raw_b = TMP / "intro_b_b_raw.mp4"

    # Raw layers without grade
    for png, raw, z_strength, direction in [(a, raw_a, 0.30, "out"), (b, raw_b, 0.08, "in")]:
        nb_frames = int(total_dur * fps)
        if direction == "in":
            z_expr = f"min(zoom+{z_strength/total_dur/fps*1.5},1+{z_strength})"
        else:
            z_expr = f"if(eq(on,0),{1+z_strength},max(zoom-{z_strength/total_dur/fps*1.5},1.0))"
        vf_raw = (
            f"scale=1920:1080:flags=lanczos,setsar=1,"
            f"zoompan=z='{z_expr}':d={nb_frames}:s=1920x1080:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':fps={fps}"
        )
        run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-loop", "1", "-i", str(png),
            "-t", f"{total_dur}",
            "-vf", vf_raw,
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-pix_fmt", "yuv420p", "-r", f"{fps}", "-an",
            str(raw),
        ])

    # Xfade the two raw layers
    xfaded = TMP / "intro_b_xfaded.mp4"
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(raw_a), "-i", str(raw_b),
        "-filter_complex",
        f"[0:v][1:v]xfade=transition=fade:duration=3.5:offset=1.5[out]",
        "-map", "[out]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
        str(xfaded),
    ])
    # Now composite the xfaded over evergreen
    dst = TMP / "intro_b.mp4"
    composite_over_evergreen(xfaded, dst, total_dur)
    print("INTRO B · 3-8s sustained reveal · evergreen base composited")
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

    # Render trim + setpts to a raw file, then composite over evergreen
    raw = dst.with_suffix(".raw.mp4")
    setpts = f"setpts=PTS/{speed}"
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-ss", f"{in_s}", "-i", str(src_file), "-t", f"{source_dur}",
        "-vf", f"{setpts}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-r", "24", "-an",
        str(raw),
    ])
    composite_over_evergreen(raw, dst, dur)
    raw.unlink()
    return dst


def main():
    clips = PLAN["clips"]
    print(f"v11 · evergreen base · {len(clips)} clips")

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
