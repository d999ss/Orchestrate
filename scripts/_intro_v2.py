#!/usr/bin/env python3
"""
Intro v2 · 10 seconds · master-shimmer cold open → operator emerges.

  0.0 – 4.0s   The conference shimmer master asset (the brand wall itself).
               Slow camera push. Pure brand atmosphere · evergreen dot field.

  4.0 – 10.0s  Cross-fade · operator-at-console coalesces from the shimmer.
               Continuous slow push-in · settles on the wide operator + screens.

Output: films/electron_intro_v2.mp4
"""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REFS = ROOT / "references"
DM = ROOT / "electron" / "_dotmatrix"
OUT = ROOT / "films" / "electron_intro_v2.mp4"
TMP = Path("/tmp/electron_intro_v2")
TMP.mkdir(exist_ok=True, parents=True)

GRADE = (
    "hue=h=-14,"
    "colorchannelmixer="
    "rr=0.97:rg=0.03:rb=0.00:"
    "gr=0.00:gg=1.06:gb=0.05:"
    "br=0.00:bg=0.10:bb=0.75,"
    "eq=contrast=1.05:saturation=1.12,"
    "vignette=angle=PI/5:mode=backward"
)

FPS = 24


def run(cmd):
    subprocess.run(cmd, check=True)


def main():
    # PHASE A · 0-4s · conference shimmer MP4, slowed and cropped for depth
    # The shimmer mp4 is ~4.5s; play full and add slow zoom for cinematic feel
    a = TMP / "phase_a.mp4"
    print("PHASE A · 0-4s · conference shimmer (master asset)")
    nb = int(4.0 * FPS)
    vf_a = (
        f"scale=1920:1080:flags=lanczos,setsar=1,"
        f"zoompan=z='min(zoom+{0.10/nb:.6f},1.10)':d={nb}:s=1920x1080:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':fps={FPS},"
        f"{GRADE}"
    )
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-stream_loop", "-1", "-i", str(REFS / "conference-shimmer.mp4"),
        "-t", "4.0",
        "-vf", vf_a,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-r", f"{FPS}", "-an",
        str(a),
    ])

    # PHASE B · 4-10s · operator emerges and reveals
    # Single continuous slow zoom-out on the operator dot-matrix, starting
    # tight on the silhouette and pulling back to the full console.
    b = TMP / "phase_b.mp4"
    print("PHASE B · 4-10s · operator coalesces and reveals (6s sustained)")
    nb_b = int(6.0 * FPS)
    z_start, z_end = 1.55, 1.0
    z_step = (z_start - z_end) / nb_b
    z_expr = f"if(eq(on,0),{z_start},max(zoom-{z_step:.6f},{z_end}))"
    vf_b = (
        f"scale=3840:2160:flags=lanczos,setsar=1,"
        f"zoompan=z='{z_expr}':d={nb_b}:s=1920x1080:x='iw*0.5-(iw/zoom/2)':y='ih*0.55-(ih/zoom/2)':fps={FPS},"
        f"{GRADE}"
    )
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-loop", "1", "-i", str(DM / "dm_09_58_06.png"),
        "-t", "6.0",
        "-vf", vf_b,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-r", f"{FPS}", "-an",
        str(b),
    ])

    # Cross-fade A→B over 1.0s at A's tail
    print("xfade A→B (1.0s)…")
    vcat = TMP / "vcat.mp4"
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(a), "-i", str(b),
        "-filter_complex",
        "[0:v][1:v]xfade=transition=fade:duration=1.0:offset=3.0[out]",
        "-map", "[out]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
        str(vcat),
    ])

    # Mux 10s of audio
    print("mux audio…")
    OUT.parent.mkdir(exist_ok=True, parents=True)
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(vcat), "-i", str(ROOT / "references" / "demand-audio.m4a"),
        "-map", "0:v", "-map", "1:a",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart",
        "-t", "10.0",
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
