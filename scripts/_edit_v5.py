#!/usr/bin/env python3
"""
v5 — music-driven 5-section edit, not storyboard-driven 27-cut.

Sections (from RMS profile of demand-audio.m4a):
  1 COLD OPEN     0.0 – 2.0s   silence breath → single electron, static hold
  2 WORLD WAKES   2 – 22s      20s slow build → particle field building
  3 THE DECISION  22 – 44s     22s peak plateau → network / GridOS
  4 THE DROP      44 – 45s     0.9s silence in track → flash + hard cut
  5 RESOLUTION    45 – 60s     15s outro → stadium → keynote → title

Each section is built from 1-3 Veo clips with long cross-fades, no rapid cuts.
"""

import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RDIR_V1 = ROOT / "electron" / "_render_4k"
ELEC_PNG = ROOT / "electron"
AUDIO = ROOT / "references" / "demand-audio.m4a"
OUT = ROOT / "films" / "electron_v5.mp4"
TMP = Path("/tmp/electron_v5")
TMP.mkdir(exist_ok=True, parents=True)

# Lighter grade — let clips breathe.
GRADE = (
    "eq=contrast=1.05:brightness=-0.015:saturation=1.08,"
    "colorchannelmixer="
    "rr=0.97:rg=0.03:rb=0.00:"
    "gr=0.00:gg=1.00:gb=0.02:"
    "br=0.00:bg=0.02:bb=1.02"
)


def run(cmd):
    subprocess.run(cmd, check=True)


def make_section_1():
    """0-2s: static hold on 01a_origin.png at 4K."""
    print("[1] COLD OPEN 0-2s — static hold on 01a_origin.png")
    png = ELEC_PNG / "01a_origin.png"
    dst = TMP / "s1_cold_open.mp4"
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-loop", "1", "-i", str(png),
        "-t", "2.0",
        "-vf", f"scale=3840:2160:flags=lanczos,{GRADE}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-r", "24", "-an",
        str(dst),
    ]
    run(cmd)
    return dst


def chain_clips(name, srcs_with_durs, total_dur, xfade=1.5):
    """Cross-fade a sequence of Veo clips together to fill `total_dur`."""
    intermediates = []
    for i, (src_name, in_s, dur) in enumerate(srcs_with_durs):
        src = RDIR_V1 / f"{src_name}.mp4"
        if not src.exists():
            sys.exit(f"missing {src}")
        dst = TMP / f"{name}_part{i}.mp4"
        cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-ss", f"{in_s}", "-i", str(src), "-t", f"{dur}",
            "-vf", GRADE,
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-pix_fmt", "yuv420p", "-an",
            str(dst),
        ]
        run(cmd)
        intermediates.append((dst, dur))

    # Chain with xfade
    out = TMP / f"{name}.mp4"
    if len(intermediates) == 1:
        # Just rename
        intermediates[0][0].rename(out)
        return out

    inputs = []
    for p, _ in intermediates:
        inputs.extend(["-i", str(p)])

    filter_parts = []
    last_label = "0:v"
    cum = 0.0
    for i in range(1, len(intermediates)):
        cum += intermediates[i - 1][1] - xfade
        out_label = f"v{i}"
        filter_parts.append(
            f"[{last_label}][{i}:v]xfade=transition=fade:duration={xfade}:offset={cum:.3f}[{out_label}]"
        )
        last_label = out_label
    filter_complex = ";".join(filter_parts)

    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", f"[{last_label}]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
        str(out),
    ]
    run(cmd)
    return out


def make_section_2():
    """2-22s: WORLD WAKES — 20s of build. Three sub-clips with 1.5s cross-fades."""
    print("[2] WORLD WAKES 2-22s (20s) — 02a/02b/02c chained, long cross-fades")
    # Total = 20s with 2 xfades of 1.5s = need sum of durations = 20 + 2*1.5 = 23s
    return chain_clips("s2_world", [
        ("02a_wind",  2.0, 8.0),
        ("02b_solar", 2.0, 8.0),
        ("02c_hydro", 2.0, 7.0),
    ], total_dur=20.0)


def make_section_3():
    """22-44s: DECISION — 22s of peak plateau. Three clips with 1.5s xfades."""
    print("[3] THE DECISION 22-44s (22s) — 04a/04c/05b chained")
    return chain_clips("s3_decision", [
        ("04a_first_links",  2.0, 8.0),
        ("04c_full_mesh",    2.0, 8.0),
        ("05b_gridos",       2.0, 9.0),
    ], total_dur=22.0)


def make_section_4():
    """44-45s: THE DROP — 1s hard cut. White flash → black."""
    print("[4] THE DROP 44-45s — white flash + black")
    dst = TMP / "s4_drop.mp4"
    # 0.0-0.15s: white flash, 0.15-1.0s: black
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", "color=c=white:s=3840x2160:r=24:d=0.15",
        "-f", "lavfi", "-i", "color=c=black:s=3840x2160:r=24:d=0.85",
        "-filter_complex", "[0:v][1:v]concat=n=2:v=1[out]",
        "-map", "[out]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p",
        str(dst),
    ]
    run(cmd)
    return dst


def make_section_5():
    """45-60s: RESOLUTION — 15s. Stadium → keynote → title."""
    print("[5] RESOLUTION 45-60s (15s) — 08a_atlanta + 09c_hero_hold + title")
    # Two parts: stadium (8s) + hero hold with title (7s) with 1s xfade
    # Need 15s total with 1 xfade of 1s = sum of durations 16s
    stadium = TMP / "s5_stadium.mp4"
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-ss", "1.0", "-i", str(RDIR_V1 / "08a_atlanta.mp4"), "-t", "8.0",
        "-vf", GRADE,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-an", str(stadium),
    ]
    run(cmd)

    # Hero hold with title overlay (build-in animation)
    hero = TMP / "s5_hero.mp4"
    title_png = RDIR_V1 / "orchestrate_title_top.png"
    if not title_png.exists():
        sys.exit("missing title PNG — run scripts/_make_title_v3.py")
    src = RDIR_V1 / "09c_hero_hold.mp4"
    filter_complex = (
        f"[0:v]{GRADE}[base];"
        f"[1:v]format=rgba,fade=in:st=1.5:d=1.5:alpha=1[title];"
        f"[base][title]overlay=0:0:format=auto[out]"
    )
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-ss", "1.0", "-i", str(src),
        "-loop", "1", "-i", str(title_png),
        "-t", "8.0",
        "-filter_complex", filter_complex, "-map", "[out]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-an",
        str(hero),
    ]
    run(cmd)

    # Concat with 1s xfade
    out = TMP / "s5_resolution.mp4"
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(stadium), "-i", str(hero),
        "-filter_complex", "[0:v][1:v]xfade=transition=fade:duration=1.0:offset=7.0[out]",
        "-map", "[out]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
        str(out),
    ]
    run(cmd)
    return out


def main():
    sections = [
        make_section_1(),
        make_section_2(),
        make_section_3(),
        make_section_4(),
        make_section_5(),
    ]

    print("\nconcat sections …")
    list_path = TMP / "sections.txt"
    list_path.write_text("\n".join(f"file '{s}'" for s in sections))

    vcat = TMP / "vcat.mp4"
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "concat", "-safe", "0", "-i", str(list_path),
        "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
        str(vcat),
    ])

    print("mux audio …")
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
