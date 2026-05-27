#!/usr/bin/env python3
"""
v6 — render against the 36-clip Beat Map plan.

Each clip uses the source_clip + src_in specified in clip_plan.json.
Hard cuts ON major impacts and breath-to-action transitions.
Cross-dissolves elsewhere, varying by duration.
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RDIR_4K = ROOT / "electron" / "_render_4k"
ELECTRON = ROOT / "electron"
AUDIO = ROOT / "references" / "demand-audio.m4a"
PLAN = json.loads((ROOT / "scripts" / "clip_plan.json").read_text())
OUT = ROOT / "films" / "electron_v6.mp4"
TMP = Path("/tmp/electron_v6")
TMP.mkdir(exist_ok=True, parents=True)

GRADE = (
    "eq=contrast=1.05:brightness=-0.015:saturation=1.08,"
    "colorchannelmixer="
    "rr=0.97:rg=0.03:rb=0.00:"
    "gr=0.00:gg=1.00:gb=0.02:"
    "br=0.00:bg=0.02:bb=1.02"
)

# Hard cuts (no xfade) for music-impact moments — the 4 major impacts.
HARD_CUT_AFTER = {19, 20, 21, 22}  # after clips 19,20,21,22 (the impact sequence)
# Hard cut after the silence at 43.88-44.73s (clip 29 ends at 44.73, then ignition at 30)
HARD_CUT_AFTER.add(29)
# Hard cut before first impact: cut at clip 19 itself
HARD_CUT_BEFORE = {19, 30}

def run(cmd):
    subprocess.run(cmd, check=True)

def make_clip(c):
    """Trim source per spec, apply grade, optionally overlay title for last clip."""
    idx = c["i"]
    name = c["clip"]
    in_s = c["src_in"]
    dur = c["t_out"] - c["t_in"]
    is_first_silent = idx == 1  # 01 cold open: use the still PNG

    dst = TMP / f"c{idx:02d}.mp4"

    if is_first_silent:
        # Use 01a_origin.png as a static hold
        png = ELECTRON / "01a_origin.png"
        cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-loop", "1", "-i", str(png),
            "-t", f"{dur}",
            "-vf", f"scale=3840:2160:flags=lanczos,{GRADE}",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-pix_fmt", "yuv420p", "-r", "24", "-an",
            str(dst),
        ]
        run(cmd)
        return dst

    # Beats 01a/b/c live inside chain_test.mp4. Map name → offset in chain_test.
    CHAIN_OFFSETS = {"01a_origin": 0.0, "01b_pulse_out": 8.0, "01c_first_trail": 16.0}
    if name in CHAIN_OFFSETS:
        src_file = ELECTRON / "chain_test.mp4"
        chain_in = CHAIN_OFFSETS[name] + in_s
        cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-ss", f"{chain_in}", "-i", str(src_file), "-t", f"{dur}",
            "-vf", f"scale=3840:2160:flags=lanczos,{GRADE}",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-pix_fmt", "yuv420p", "-an",
            str(dst),
        ]
        run(cmd)
        return dst

    # Some clips use chain_test (only 1280×720) — scale to 4K
    src_file = RDIR_4K / f"{name}.mp4"
    if not src_file.exists():
        # Fallback: maybe it's in the unscaled folder, scale on the fly
        alt = ROOT / "electron" / f"{name}.mp4"
        if alt.exists():
            src_file = alt
            scale_chain = "scale=3840:2160:flags=lanczos,"
        else:
            sys.exit(f"missing source: {name}")
    else:
        scale_chain = ""

    vf = scale_chain + GRADE

    # Final clip (36 · TITLE LAND): overlay title PNG with fade-in
    if idx == 36:
        title_png = RDIR_4K / "orchestrate_title_top.png"
        filter_complex = (
            f"[0:v]{vf}[base];"
            f"[1:v]format=rgba,fade=in:st=0.3:d=0.9:alpha=1[title];"
            f"[base][title]overlay=0:0:format=auto[out]"
        )
        cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-ss", f"{in_s}", "-i", str(src_file),
            "-loop", "1", "-i", str(title_png),
            "-t", f"{dur}",
            "-filter_complex", filter_complex, "-map", "[out]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-pix_fmt", "yuv420p", "-an",
            str(dst),
        ]
    else:
        cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-ss", f"{in_s}", "-i", str(src_file),
            "-t", f"{dur}",
            "-vf", vf,
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-pix_fmt", "yuv420p", "-an",
            str(dst),
        ]
    run(cmd)
    return dst


def main():
    clips = PLAN["clips"]
    print(f"v6 · {len(clips)} clips · {sum(c['t_out']-c['t_in'] for c in clips):.2f}s")
    paths = []
    for i, c in enumerate(clips):
        dur = c["t_out"] - c["t_in"]
        print(f"[{c['i']:2d}/{len(clips)}] {c['clip']:<22}  in={c['src_in']}s  dur={dur:.2f}s  · {c['anchor'][:40]}")
        paths.append(make_clip(c))

    # Concat clips back-to-back — total duration = sum of clip durations = 60s exactly.
    # Hard cuts at every boundary; continuity comes from motion-vector handoff in the plan,
    # not from cross-dissolves.
    print("\nconcatenating clips back-to-back (hard cuts, exact 60s)…")
    list_path = TMP / "concat.txt"
    list_path.write_text("\n".join(f"file '{p}'" for p in paths))
    vcat = TMP / "vcat.mp4"
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "concat", "-safe", "0", "-i", str(list_path),
        "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
        str(vcat),
    ]
    run(cmd)

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
        "-show_entries", "stream=codec_name,width,height,r_frame_rate",
        "-of", "default=noprint_wrappers=1",
        str(OUT),
    ])


if __name__ == "__main__":
    main()
