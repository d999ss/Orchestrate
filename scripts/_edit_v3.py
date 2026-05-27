#!/usr/bin/env python3
"""
v3 polish pass.

Fixes from v2:
  - Total runtime hit 52.9s instead of 60. Bump clip durations to compensate
    for the 9.6s eaten by cross-dissolves (24 transitions × 0.4s).
  - ORCHESTRATE title was centered over the bright cyan burst, blocking it.
    Reposition title to upper-third with the burst readable underneath.
  - Soften the color grade (v2 had too much green pull on some shots).
"""

import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RDIR_V1 = ROOT / "electron" / "_render_4k"
AUDIO = ROOT / "references" / "demand-audio.m4a"
OUT = ROOT / "films" / "electron_v3.mp4"
TMP = Path("/tmp/electron_v3")
TMP.mkdir(exist_ok=True, parents=True)

# Lighter grade than v2 — let the source clips breathe more.
GRADE = (
    "eq=contrast=1.05:brightness=-0.015:saturation=1.08,"
    "colorchannelmixer="
    "rr=0.97:rg=0.03:rb=0.00:"
    "gr=0.00:gg=1.00:gb=0.02:"
    "br=0.00:bg=0.02:bb=1.02"
)

# Durations re-paced to land at 60s with 0.4s xfades.
# Total clip time needs to be ~60 + (24 × 0.4) = 69.6s before xfade overlap.
CLIPS = [
    ("chain_test",           "ELECTRON_DIR", 0.0,  5.5),
    ("02a_wind",             "V1",     2.0,  2.8),
    ("02b_solar",            "V1",     2.0,  2.8),
    ("02c_hydro",            "V1",     2.0,  2.8),
    ("03a_dense_field",      "V1",     2.5,  2.3),
    ("03b_grid_order",       "V1",     3.0,  2.3),
    ("03c_grid_perspective", "V1",     3.0,  2.3),
    ("04a_first_links",      "V1",     2.5,  2.3),
    ("04b_radiating_node",   "V1",     2.0,  2.3),
    ("04c_full_mesh",        "V1",     3.0,  2.3),
    ("05a_paths_fan",        "V1",     3.0,  3.3),
    ("05b_gridos",           "V1",     3.0,  3.3),
    ("05c_path_chosen",      "V1",     3.0,  2.3),
    ("06a_comet",            "V1",     2.0,  2.8),
    ("06b_currents",         "V1",     2.5,  2.3),
    ("06c_aurora",           "V1",     2.0,  2.8),
    ("07a_gold_burst",       "V1",     3.5,  2.8),
    ("07b_lime_ripple",      "V1",     2.5,  2.3),
    ("07c_climax",           "V1",     3.0,  2.8),
    ("08a_atlanta",          "V1",     2.0,  3.3),
    ("08b_distribution",     "V1",     2.5,  3.3),
    ("08c_aerial_sweep",     "V1",     2.0,  3.3),
    ("09a_venue_dawn",       "V1",     2.5,  2.3),
    ("09b_keynote_stage",    "V1",     2.0,  1.8),
    ("09c_hero_hold",        "V1",     2.5,  4.0),   # held longer for title build
]

XFADE = 0.4


def run(cmd):
    print(f"  $ ffmpeg …", flush=True)
    subprocess.run(cmd, check=True)


def make_clip(idx, name, src_dir, in_s, dur_s):
    if src_dir == "V1":
        src = RDIR_V1 / f"{name}.mp4"
    elif src_dir == "ELECTRON_DIR":
        src = ROOT / "electron" / f"{name}.mp4"
    else:
        sys.exit(f"unknown src_dir: {src_dir}")
    if not src.exists():
        sys.exit(f"missing: {src}")
    dst = TMP / f"i{idx:02d}_{name}.mp4"

    scale_chain = "scale=3840:2160:flags=lanczos," if name == "chain_test" else ""
    vf = scale_chain + GRADE

    if name == "09c_hero_hold":
        title_png = RDIR_V1 / "orchestrate_title_top.png"
        if not title_png.exists():
            sys.exit(f"missing title PNG: {title_png}")
        filter_complex = (
            f"[0:v]{vf}[base];"
            f"[1:v]format=rgba,fade=in:st=0.8:d=1.0:alpha=1[title];"
            f"[base][title]overlay=0:0:format=auto[out]"
        )
        cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-ss", f"{in_s}", "-i", str(src),
            "-loop", "1", "-i", str(title_png),
            "-t", f"{dur_s}",
            "-filter_complex", filter_complex, "-map", "[out]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-pix_fmt", "yuv420p", "-an",
            str(dst),
        ]
    else:
        cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-ss", f"{in_s}", "-i", str(src),
            "-t", f"{dur_s}", "-vf", vf,
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-pix_fmt", "yuv420p", "-an",
            str(dst),
        ]
    run(cmd)
    return dst


def compose_xfade(intermediates):
    vcat = TMP / "vcat.mp4"
    inputs = []
    for p in intermediates:
        inputs.extend(["-i", str(p)])
    durations = [c[3] for c in CLIPS]
    filter_parts = []
    last_label = "0:v"
    cumulative = 0.0
    for i in range(1, len(intermediates)):
        cumulative += durations[i - 1] - XFADE
        out_label = f"v{i}"
        filter_parts.append(
            f"[{last_label}][{i}:v]xfade=transition=fade:duration={XFADE}:offset={cumulative:.3f}[{out_label}]"
        )
        last_label = out_label
    filter_complex = ";".join(filter_parts)
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", f"[{last_label}]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
        str(vcat),
    ]
    print("\nxfade chain …", flush=True)
    run(cmd)
    return vcat


def mux_audio(vcat):
    OUT.parent.mkdir(exist_ok=True, parents=True)
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(vcat), "-i", str(AUDIO),
        "-map", "0:v", "-map", "1:a",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart",
        str(OUT),
    ]
    print("\nmux audio …", flush=True)
    run(cmd)


def main():
    print(f"v3 polish · {len(CLIPS)} clips · {XFADE*1000:.0f}ms dissolves")
    total = sum(c[3] for c in CLIPS) - (len(CLIPS) - 1) * XFADE
    print(f"  projected runtime: {total:.2f}s\n")
    intermediates = []
    for i, (name, src_dir, in_s, dur_s) in enumerate(CLIPS):
        print(f"[{i+1:2d}/{len(CLIPS)}] {name:<22}  in={in_s}s  dur={dur_s}s")
        intermediates.append(make_clip(i, name, src_dir, in_s, dur_s))
    vcat = compose_xfade(intermediates)
    mux_audio(vcat)
    print("\ndone.")
    subprocess.run([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration,size",
        "-show_entries", "stream=codec_name,width,height,r_frame_rate",
        "-of", "default=noprint_wrappers=1",
        str(OUT),
    ])


if __name__ == "__main__":
    main()
