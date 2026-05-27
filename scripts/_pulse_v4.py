#!/usr/bin/env python3
"""
v4 = v3 + beat-pulse white-flash overlay at librosa strong beats.
"""

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "films" / "electron_v3.mp4"
AUDIO = ROOT / "references" / "demand-audio.m4a"
BEATS = json.loads((ROOT / "scripts" / "beats.json").read_text())
OUT = ROOT / "films" / "electron_v4.mp4"

strong = BEATS["strong_beats"]
print(f"strong beats: {[f'{b:.2f}' for b in strong]}")

PULSE_DUR = 0.07  # 70ms flash

# Build enable expression: "between(t,a,b)+between(t,c,d)+..."
gates = "+".join(f"between(t,{b:.3f},{b+PULSE_DUR:.3f})" for b in strong)

# Use color source as white flash, overlay onto base with enable gate.
# Alpha 0.35 = subtle but visible punch on each strong beat.
filter_complex = (
    f"color=c=white:s=3840x2160:r=24:d=60[white];"
    f"[0:v][white]blend=all_mode=screen:all_opacity=0.35:enable='{gates}'[out]"
)

cmd = [
    "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
    "-i", str(SRC),
    "-i", str(AUDIO),
    "-filter_complex", filter_complex,
    "-map", "[out]", "-map", "1:a",
    "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
    "-c:a", "aac", "-b:a", "192k",
    "-movflags", "+faststart",
    "-shortest",
    str(OUT),
]
print(f"rendering {OUT.name} …")
subprocess.run(cmd, check=True)

subprocess.run([
    "ffprobe", "-v", "error",
    "-show_entries", "format=duration,size",
    "-show_entries", "stream=codec_name,width,height",
    "-of", "default=noprint_wrappers=1",
    str(OUT),
])
