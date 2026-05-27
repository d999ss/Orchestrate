#!/usr/bin/env python3
"""
v2 real edit pass — composes from the existing 4K Veo clips. No re-rendering.

Per-clip work:
  - Scrub IN-point past the slow Veo build (default: start at 2.0s of the 8s clip)
  - Apply a subtle color grade (lock evergreen, push cyan, suppress accidental warm tones)
  - Trim to the duration required by the beat-lock chart
Sequence work:
  - 300ms cross-dissolves between adjacent clips
  - ORCHESTRATE title build-in on the hero hold (drawtext, not Veo)
  - Mux the locked Demand audio
Output: films/electron_v2.mp4 (3840×2160 · 60s · H.264 · AAC)
"""

import json
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RDIR_V1 = ROOT / "electron" / "_render_4k"
AUDIO = ROOT / "references" / "demand-audio.m4a"
OUT = ROOT / "films" / "electron_v2.mp4"
TMP = Path("/tmp/electron_v2")
TMP.mkdir(exist_ok=True, parents=True)

# Color grade: lock evergreen, punch cyan, suppress accidental warm tones.
# eq filter params tuned for halftone dot-matrix content.
GRADE = (
    "eq=contrast=1.08:brightness=-0.02:saturation=1.15,"
    "colorchannelmixer="
    "rr=0.95:rg=0.05:rb=0.00:"
    "gr=0.00:gg=1.00:gb=0.05:"
    "br=0.00:bg=0.05:bb=1.05,"
    "curves=preset=increase_contrast"
)

# Per-clip manifest: (name, src_dir, in_point_in_8s_clip, duration_needed)
# in_point chosen to skip Veo's slow build (typically 0-2s) and land on payoff motion.
# Durations match beat-lock chart targets.
CLIPS = [
    # (name,                 src_dir,   in_s, dur_s, notes)
    ("chain_test",           "ELECTRON_DIR", 0.0,  5.0),   # Beats 01A-01C, downsampled from 720p
    ("02a_wind",             "V1",     2.0,  2.5),
    ("02b_solar",            "V1",     2.0,  2.5),
    ("02c_hydro",            "V1",     2.0,  2.5),
    ("03a_dense_field",      "V1",     2.5,  2.0),
    ("03b_grid_order",       "V1",     3.0,  2.0),
    ("03c_grid_perspective", "V1",     3.0,  2.0),
    ("04a_first_links",      "V1",     2.5,  2.0),
    ("04b_radiating_node",   "V1",     2.0,  2.0),
    ("04c_full_mesh",        "V1",     3.0,  2.0),
    ("05a_paths_fan",        "V1",     3.0,  3.0),
    ("05b_gridos",           "V1",     3.0,  3.0),
    ("05c_path_chosen",      "V1",     3.0,  2.0),
    ("06a_comet",            "V1",     2.0,  2.5),
    ("06b_currents",         "V1",     2.5,  2.0),
    ("06c_aurora",           "V1",     2.0,  2.5),
    ("07a_gold_burst",       "V1",     3.5,  2.5),
    ("07b_lime_ripple",      "V1",     2.5,  2.0),
    ("07c_climax",           "V1",     3.0,  2.5),
    ("08a_atlanta",          "V1",     2.0,  3.0),
    ("08b_distribution",     "V1",     2.5,  3.0),
    ("08c_aerial_sweep",     "V1",     2.0,  3.0),
    ("09a_venue_dawn",       "V1",     2.5,  2.0),
    ("09b_keynote_stage",    "V1",     2.0,  1.5),
    ("09c_hero_hold",        "V1",     2.5,  3.5),   # extended for title build-in
]

# Cross-dissolve duration (each transition eats this much from both clips).
XFADE = 0.4


def run(cmd, **kw):
    print(f"  $ {' '.join(shlex.quote(str(c)) for c in cmd[:5])}…", flush=True)
    return subprocess.run(cmd, check=True, **kw)


def make_clip(idx, name, src_dir, in_s, dur_s):
    """Trim + grade one clip; return path to intermediate mp4."""
    if src_dir == "V1":
        src = RDIR_V1 / f"{name}.mp4"
    elif src_dir == "ELECTRON_DIR":
        src = ROOT / "electron" / f"{name}.mp4"
    else:
        sys.exit(f"unknown src_dir: {src_dir}")
    if not src.exists():
        sys.exit(f"missing source: {src}")
    dst = TMP / f"i{idx:02d}_{name}.mp4"

    # Scale chain_test from 720p to 4K
    scale_chain = ""
    if name == "chain_test":
        scale_chain = "scale=3840:2160:flags=lanczos,"

    vf = scale_chain + GRADE

    if name == "09c_hero_hold":
        # Two-input filter: clip + ORCHESTRATE title PNG, overlay with timed alpha.
        title_png = RDIR_V1 / "orchestrate_title.png"
        if not title_png.exists():
            sys.exit(f"missing title PNG: {title_png} — run scripts/_make_title.py")
        # Alpha curve: invisible 0-0.5s, fade-in 0.5-1.3s, hold to end.
        filter_complex = (
            f"[0:v]{vf}[base];"
            f"[1:v]format=rgba,fade=in:st=0.5:d=0.8:alpha=1[title];"
            f"[base][title]overlay=0:0:format=auto[out]"
        )
        cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-ss", f"{in_s}", "-i", str(src),
            "-loop", "1", "-i", str(title_png),
            "-t", f"{dur_s}",
            "-filter_complex", filter_complex,
            "-map", "[out]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-an",
            str(dst),
        ]
    else:
        cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-ss", f"{in_s}",
            "-i", str(src),
            "-t", f"{dur_s}",
            "-vf", vf,
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-an",
            str(dst),
        ]
    run(cmd)
    return dst


def compose_xfade(intermediates):
    """Chain cross-fade all intermediates into one video, then mux audio."""
    n = len(intermediates)
    vcat = TMP / "vcat.mp4"

    # Build filter_complex with chained xfades
    inputs = []
    for i, p in enumerate(intermediates):
        inputs.extend(["-i", str(p)])

    # Each clip has its full duration. Offset for clip i+1's xfade is sum(dur[0..i]) - XFADE.
    durations = [c[3] for c in CLIPS]
    durations[0] = 5.0  # chain_test full length

    filter_parts = []
    last_label = "0:v"
    cumulative = 0.0
    for i in range(1, n):
        cumulative += durations[i - 1] - XFADE
        out_label = f"v{i}"
        filter_parts.append(
            f"[{last_label}][{i}:v]xfade=transition=fade:duration={XFADE}:offset={cumulative:.3f}[{out_label}]"
        )
        last_label = out_label

    filter_complex = ";".join(filter_parts) if filter_parts else None

    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        *inputs,
    ]
    if filter_complex:
        cmd += ["-filter_complex", filter_complex, "-map", f"[{last_label}]"]
    cmd += [
        "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
        str(vcat),
    ]
    print("\nxfade chain compositing…", flush=True)
    run(cmd)
    return vcat


def mux_audio(vcat):
    OUT.parent.mkdir(exist_ok=True, parents=True)
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(vcat),
        "-i", str(AUDIO),
        "-map", "0:v", "-map", "1:a",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart",
        str(OUT),
    ]
    print("\nmuxing audio…", flush=True)
    run(cmd)


def main():
    print(f"v2 edit · {len(CLIPS)} clips · {XFADE*1000:.0f}ms cross-dissolves\n")
    intermediates = []
    for i, (name, src_dir, in_s, dur_s) in enumerate(CLIPS):
        print(f"[{i+1:2d}/{len(CLIPS)}] {name:<22}  in={in_s}s  dur={dur_s}s")
        p = make_clip(i, name, src_dir, in_s, dur_s)
        intermediates.append(p)

    vcat = compose_xfade(intermediates)
    mux_audio(vcat)

    # Inspect output
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
