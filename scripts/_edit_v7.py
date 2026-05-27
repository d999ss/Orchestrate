#!/usr/bin/env python3
"""
v7 — speed pass.

Each Veo i2v clip generates lazy ambient motion. By setpts=PTS/1.3 (1.3× speed),
we show ~30% more motion content in the same clip duration. The cut grid stays
locked to the Beat Map (so cuts still hit music events), but each clip feels
more kinetic.

Breath clips (4 of them) stay at 1.0× to preserve restraint.
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
OUT = ROOT / "films" / "electron_v7.mp4"
TMP = Path("/tmp/electron_v7")
TMP.mkdir(exist_ok=True, parents=True)

GRADE = (
    "eq=contrast=1.10:brightness=-0.02:saturation=1.10,"
    "colorchannelmixer="
    "rr=0.97:rg=0.03:rb=0.00:"
    "gr=0.00:gg=1.00:gb=0.02:"
    "br=0.00:bg=0.02:bb=1.02,"
    "vignette=angle=PI/5:mode=backward"
)

# Breath clips that should stay at native speed (anchor copy contains BREATH)
SPEED = 1.30

def run(cmd):
    subprocess.run(cmd, check=True)


def make_clip(c):
    idx = c["i"]
    name = c["clip"]
    in_s = c["src_in"]
    dur = c["t_out"] - c["t_in"]
    is_breath = "BREATH" in (c.get("anchor") or "").upper()
    speed = 1.0 if is_breath else SPEED
    source_dur = dur * speed   # how much source we need to fill `dur` of output

    dst = TMP / f"c{idx:02d}.mp4"

    if idx == 1:
        # Cold open: static hold on PNG
        png = ELECTRON / "01a_origin.png"
        cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-loop", "1", "-i", str(png), "-t", f"{dur}",
            "-vf", f"scale=3840:2160:flags=lanczos,{GRADE}",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-pix_fmt", "yuv420p", "-r", "24", "-an",
            str(dst),
        ]
        run(cmd)
        return dst

    CHAIN_OFFSETS = {"01a_origin": 0.0, "01b_pulse_out": 8.0, "01c_first_trail": 16.0}
    if name in CHAIN_OFFSETS:
        src_file = ELECTRON / "chain_test.mp4"
        chain_in = CHAIN_OFFSETS[name] + in_s
        # chain_test is 720p, scale + speed up
        setpts = f"setpts=PTS/{speed}"
        cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-ss", f"{chain_in}", "-i", str(src_file), "-t", f"{source_dur}",
            "-vf", f"scale=3840:2160:flags=lanczos,{setpts},{GRADE}",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-pix_fmt", "yuv420p", "-r", "24", "-an",
            str(dst),
        ]
        run(cmd)
        return dst

    src_file = RDIR_4K / f"{name}.mp4"
    if not src_file.exists():
        sys.exit(f"missing {name}")

    # Title overlay on final clip
    if idx == 36:
        title_png = RDIR_4K / "orchestrate_title_top.png"
        setpts = f"setpts=PTS/{speed}"
        filter_complex = (
            f"[0:v]{setpts},{GRADE}[base];"
            f"[1:v]format=rgba,fade=in:st=0.3:d=0.9:alpha=1[title];"
            f"[base][title]overlay=0:0:format=auto[out]"
        )
        cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-ss", f"{in_s}", "-i", str(src_file), "-t", f"{source_dur}",
            "-loop", "1", "-i", str(title_png),
            "-filter_complex", filter_complex, "-map", "[out]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-pix_fmt", "yuv420p", "-r", "24", "-an",
            str(dst),
        ]
    else:
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
    print(f"v7 · speed pass · {len(clips)} clips · breath@1.0x, rest@{SPEED}x")
    paths = []
    for c in clips:
        dur = c["t_out"] - c["t_in"]
        is_breath = "BREATH" in (c.get("anchor") or "").upper()
        sp = 1.0 if is_breath else SPEED
        print(f"[{c['i']:2d}] {c['clip']:<22}  {dur:.2f}s × {sp}x")
        paths.append(make_clip(c))

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
