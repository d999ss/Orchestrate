#!/usr/bin/env python3
"""
v8 — intro fix + operator hero shot.

Changes from v7:
  - Intro (0-8s): replace spray-y Veo output with ken-burns on source PNGs.
    Slow scale moves on the still images give controlled, clean motion.
  - GridOS section (clips 14/23): slot in the operator_console 4K Veo
    render as the human-in-the-loop hero shot.
  - Control room wall: replace one of the abstract decision shots.
  - Keep the 36-clip Beat Map structure and music sync.
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Review delivery is 1080p — skip Topaz dependency, use 1080p sources directly.
RDIR_4K = ROOT / "electron" / "_render"
OPER_4K = ROOT / "electron" / "_render_operator"
ELECTRON = ROOT / "electron"
AUDIO = ROOT / "references" / "demand-audio.m4a"
PLAN = json.loads((ROOT / "scripts" / "clip_plan.json").read_text())
OUT = ROOT / "films" / "electron_v8.mp4"
TMP = Path("/tmp/electron_v8")
TMP.mkdir(exist_ok=True, parents=True)

GRADE = (
    "eq=contrast=1.08:brightness=-0.02:saturation=1.10,"
    "colorchannelmixer="
    "rr=0.97:rg=0.03:rb=0.00:"
    "gr=0.00:gg=1.00:gb=0.02:"
    "br=0.00:bg=0.02:bb=1.02,"
    "vignette=angle=PI/5:mode=backward"
)

# Use ken-burns (slow zoom) on PNGs for the abstract intro beats where Veo
# produced spray/cloud. These look like discrete dot-matrix when held still.
KENBURNS_BEATS = {
    1,   # 01a_origin cold open
    2,   # 01b_pulse_out
    3,   # 01c_first_trail
    4,   # 02a_wind
    5,   # 02b_solar
    6,   # 02c_hydro
    7,   # 03a_dense_field (breath)
    8,   # 03b_grid_order
    9,   # 03c_grid_perspective
}

# Slot operator/control-room clips into the GridOS decision section
OPERATOR_OVERRIDES = {
    14: "operator_console",        # clip 14 was 05b_gridos — swap to operator console
    23: "control_room_wall",       # clip 23 was 05b_gridos again — swap to control room
}

SPEED = 1.25  # for kept Veo footage


def run(cmd):
    subprocess.run(cmd, check=True)


def ken_burns(png_path, dur, dst, direction="in"):
    """Slow zoom on a still PNG · 1080p output for review."""
    z_expr = "min(zoom+0.0008,1.10)" if direction == "in" else "if(eq(on,0),1.10,max(zoom-0.0008,1.0))"
    fps = 24
    nb_frames = int(dur * fps)
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


def make_clip(c):
    idx = c["i"]
    name = c["clip"]
    in_s = c["src_in"]
    dur = c["t_out"] - c["t_in"]
    dst = TMP / f"c{idx:02d}.mp4"

    # Operator overrides — use the 4K operator clips
    if idx in OPERATOR_OVERRIDES:
        op_name = OPERATOR_OVERRIDES[idx]
        src = OPER_4K / f"{op_name}.mp4"
        if src.exists():
            print(f"  [{idx:2d}] OVERRIDE → {op_name}")
            cmd = [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-ss", "1.0", "-i", str(src), "-t", f"{dur}",
                "-vf", GRADE,
                "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                "-pix_fmt", "yuv420p", "-r", "24", "-an",
                str(dst),
            ]
            run(cmd)
            return dst

    # Ken-burns intro beats
    if idx in KENBURNS_BEATS:
        png = ELECTRON / f"{name}.png"
        if png.exists():
            direction = "out" if idx in (1, 7) else "in"  # zoom out on breath/origin, in elsewhere
            print(f"  [{idx:2d}] KEN-BURNS {direction} on {name}.png · {dur:.2f}s")
            ken_burns(png, dur, dst, direction)
            return dst

    # Default: Veo footage with speed-up (as v7)
    is_breath = "BREATH" in (c.get("anchor") or "").upper()
    speed = 1.0 if is_breath else SPEED
    source_dur = dur * speed

    src_file = RDIR_4K / f"{name}.mp4"
    if not src_file.exists():
        sys.exit(f"missing {name}")

    setpts = f"setpts=PTS/{speed}"
    if idx == 36:
        title_png = RDIR_4K / "orchestrate_title_top.png"
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
    print(f"v8 · intro fix (ken-burns) + operator hero · {len(clips)} clips")
    paths = []
    for c in clips:
        dur = c["t_out"] - c["t_in"]
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
