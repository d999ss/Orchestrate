#!/usr/bin/env python3
"""
v9 — INTRO REWORK.

The 8s intro is the most important thing in the film. It sets the contract
with the audience. v6/v7/v8 had 6+ cuts in 8s — too busy. v9 does TWO
elements in 8s:

  0.0 – 3.0s:  STATIC HOLD on 01a_origin.png (single electron, no motion).
               This is the breath. The silence. The audience leans in.

  3.0 – 8.0s:  ONE sustained slow zoom-out from the electron, revealing the
               surrounding particle field (cross-fading 01b → 03b_grid_order
               for richer texture). 5 seconds of continuous reveal motion.

  8.0 – 60.0s: Beats 10-36 unchanged from the v8 plan (operator hero stays,
               Veo footage where it works, title at the end).
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RDIR = ROOT / "electron" / "_render"
OPER = ROOT / "electron" / "_render_operator"
ELECTRON = ROOT / "electron"
AUDIO = ROOT / "references" / "demand-audio.m4a"
PLAN = json.loads((ROOT / "scripts" / "clip_plan.json").read_text())
OUT = ROOT / "films" / "electron_v9.mp4"
TMP = Path("/tmp/electron_v9")
TMP.mkdir(exist_ok=True, parents=True)

GRADE = (
    "eq=contrast=1.08:brightness=-0.02:saturation=1.10,"
    "colorchannelmixer="
    "rr=0.97:rg=0.03:rb=0.00:"
    "gr=0.00:gg=1.00:gb=0.02:"
    "br=0.00:bg=0.02:bb=1.02,"
    "vignette=angle=PI/5:mode=backward"
)

OPERATOR_OVERRIDES = {
    14: "operator_console",
    23: "control_room_wall",
}

SPEED = 1.25


def run(cmd):
    subprocess.run(cmd, check=True)


def make_intro_part_1():
    """0.0-3.0s · static hold on 01a_origin."""
    png = ELECTRON / "01a_origin.png"
    dst = TMP / "intro_a.mp4"
    print("INTRO A · 0-3s static hold on 01a_origin")
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-loop", "1", "-i", str(png),
        "-t", "3.0",
        "-vf", f"scale=1920:1080:flags=lanczos,setsar=1,{GRADE}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-r", "24", "-an",
        str(dst),
    ]
    run(cmd)
    return dst


def make_intro_part_2():
    """3.0-8.0s · sustained 5s reveal · zoom-out from 01a with cross to 03b."""
    a = ELECTRON / "01a_origin.png"
    b = ELECTRON / "03b_grid_order.png"
    fps = 24
    total_dur = 5.0
    nb_frames = int(total_dur * fps)

    # Layer 1: zoom-out on 01a_origin
    layer_a = TMP / "intro_b_a.mp4"
    z_out = "if(eq(on,0),1.30,max(zoom-0.0010,1.0))"
    vf_a = (
        f"scale=1920:1080:flags=lanczos,setsar=1,"
        f"zoompan=z='{z_out}':d={nb_frames}:s=1920x1080:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':fps={fps},"
        f"{GRADE}"
    )
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-loop", "1", "-i", str(a),
        "-t", f"{total_dur}",
        "-vf", vf_a,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-r", f"{fps}", "-an",
        str(layer_a),
    ])

    # Layer 2: subtle zoom-in on 03b_grid_order (the wider reveal target)
    layer_b = TMP / "intro_b_b.mp4"
    z_in = "min(zoom+0.0005,1.08)"
    vf_b = (
        f"scale=1920:1080:flags=lanczos,setsar=1,"
        f"zoompan=z='{z_in}':d={nb_frames}:s=1920x1080:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':fps={fps},"
        f"{GRADE}"
    )
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-loop", "1", "-i", str(b),
        "-t", f"{total_dur}",
        "-vf", vf_b,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-r", f"{fps}", "-an",
        str(layer_b),
    ])

    # Cross-fade A → B over the 5s: fade starts at 1.5s, lasts 3.5s
    dst = TMP / "intro_b.mp4"
    print("INTRO B · 3-8s sustained reveal · xfade 01a → 03b_grid_order over 3.5s")
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
    """Body clips (beats 10-36) — match v8 strategy."""
    idx = c["i"]
    name = c["clip"]
    in_s = c["src_in"]
    dur = c["t_out"] - c["t_in"]
    dst = TMP / f"c{idx:02d}.mp4"

    if idx in OPERATOR_OVERRIDES:
        op_name = OPERATOR_OVERRIDES[idx]
        src = OPER / f"{op_name}.mp4"
        if src.exists():
            print(f"  [{idx:2d}] OVERRIDE → {op_name}")
            cmd = [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-ss", "1.0", "-i", str(src), "-t", f"{dur}",
                "-vf", f"scale=1920:1080:flags=lanczos,{GRADE}",
                "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                "-pix_fmt", "yuv420p", "-r", "24", "-an",
                str(dst),
            ]
            run(cmd)
            return dst

    is_breath = "BREATH" in (c.get("anchor") or "").upper()
    speed = 1.0 if is_breath else SPEED
    source_dur = dur * speed

    src_file = RDIR / f"{name}.mp4"
    if not src_file.exists():
        sys.exit(f"missing {name}")

    setpts = f"setpts=PTS/{speed}"
    if idx == 36:
        title_png = ROOT / "electron" / "_render_4k" / "orchestrate_title_top.png"
        filter_complex = (
            f"[0:v]{setpts},{GRADE}[base];"
            f"[1:v]scale=1920:1080,format=rgba,fade=in:st=0.3:d=0.9:alpha=1[title];"
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
    print(f"v9 · INTRO REWORK + body · {len(clips)} clips")

    paths = []
    # Intro: replace beats 1-9 (clips 0.0-8.0s in the plan) with two sustained shots
    paths.append(make_intro_part_1())  # 0-3s
    paths.append(make_intro_part_2())  # 3-8s

    # Body: beats 10-36 (skip first 9 clips of the plan, since intro covers 0-8s)
    # The plan has clip 9 ending at exactly 8.00s, so we skip clips 1-9
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
