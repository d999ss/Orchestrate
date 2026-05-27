#!/usr/bin/env python3
"""
Intro-focus build · 8 seconds · all energy on the operator reveal.

Three motion-controlled phases on dot-matrix sources:

  0.0 – 1.5s   Faint particle field emerging from black.
               01a_origin held with very slow zoom-in.

  1.5 – 4.0s   Operator silhouette begins coalescing.
               Tight close-up on operator-dot-matrix · slow zoom-out reveal.

  4.0 – 8.0s   Full operator at console revealed, screens visible.
               Sustained continued zoom-out · settle on the wide.

No static. No spray. Continuous push. Evergreen-tinted dots, black bg.

Output: films/electron_intro.mp4
"""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ELECTRON = ROOT / "electron"
DM = ROOT / "electron" / "_dotmatrix"
AUDIO = ROOT / "references" / "demand-audio.m4a"
OUT = ROOT / "films" / "electron_intro.mp4"
TMP = Path("/tmp/electron_intro")
TMP.mkdir(exist_ok=True, parents=True)

# Evergreen particle grade — hue toward green, less blue, black bg preserved.
GRADE = (
    "hue=h=-14,"
    "colorchannelmixer="
    "rr=0.97:rg=0.03:rb=0.00:"
    "gr=0.00:gg=1.06:gb=0.05:"
    "br=0.00:bg=0.10:bb=0.75,"
    "eq=contrast=1.08:brightness=-0.02:saturation=1.14,"
    "vignette=angle=PI/5:mode=backward"
)

FPS = 24


def run(cmd):
    subprocess.run(cmd, check=True)


def zoom_clip(png, dur, dst, z_start, z_end, x_focus="iw/2", y_focus="ih/2"):
    """Render a PNG with smooth linear zoom from z_start to z_end."""
    nb = int(dur * FPS)
    # zoompan uses per-frame z increment; compute as (end-start)/nb
    if z_end > z_start:
        z_expr = f"min(zoom+{(z_end-z_start)/nb:.6f},{z_end})"
    else:
        z_expr = f"if(eq(on,0),{z_start},max(zoom-{(z_start-z_end)/nb:.6f},{z_end}))"
    vf = (
        f"scale=3840:2160:flags=lanczos,setsar=1,"
        f"zoompan=z='{z_expr}':d={nb}:s=1920x1080:x='{x_focus}-(iw/zoom/2)':y='{y_focus}-(ih/zoom/2)':fps={FPS},"
        f"{GRADE}"
    )
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-loop", "1", "-i", str(png),
        "-t", f"{dur}",
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-r", f"{FPS}", "-an",
        str(dst),
    ])


def main():
    # PHASE A · 0.0-1.5s · faint emergence
    a = TMP / "phase_a.mp4"
    print("PHASE A · 0-1.5s · faint emergence (01a_origin, slow zoom-in)")
    zoom_clip(ELECTRON / "01a_origin.png", 1.5, a, z_start=1.0, z_end=1.20)

    # PHASE B · 1.5-4.0s · operator silhouette coalescing (tight, zoom-out from 1.6× → 1.15×)
    # Focus on upper-middle area where the operator's head sits
    b = TMP / "phase_b.mp4"
    print("PHASE B · 1.5-4s · operator silhouette coalesces (tight → medium)")
    # Operator image: silhouette is roughly center-low. Start tight on his head/torso area.
    zoom_clip(DM / "dm_09_58_06.png", 2.5, b,
              z_start=1.80, z_end=1.15,
              x_focus="iw*0.5", y_focus="ih*0.55")

    # PHASE C · 4.0-8.0s · full reveal, continued zoom-out (1.15× → 1.0×)
    c = TMP / "phase_c.mp4"
    print("PHASE C · 4-8s · sustained wide reveal of operator + screens")
    zoom_clip(DM / "dm_09_58_06.png", 4.0, c,
              z_start=1.15, z_end=1.00,
              x_focus="iw*0.5", y_focus="ih*0.5")

    # Cross-fade A→B over 0.6s at A's tail (1.5s) — i.e. xfade duration 0.6, offset 0.9
    # B→C is a continuous motion handoff — direct concat (or tiny xfade)
    print("\nxfade A→B (0.6s)…")
    ab = TMP / "ab.mp4"
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(a), "-i", str(b),
        "-filter_complex",
        "[0:v][1:v]xfade=transition=fade:duration=0.6:offset=0.9[out]",
        "-map", "[out]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
        str(ab),
    ])

    # B→C: continuous (same image, continuing zoom). Simple concat works.
    list_path = TMP / "concat.txt"
    list_path.write_text("\n".join(f"file '{p}'" for p in [ab, c]))
    vcat = TMP / "vcat.mp4"
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "concat", "-safe", "0", "-i", str(list_path),
        "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
        str(vcat),
    ])

    # Mux audio (first 8s)
    print("mux audio…")
    OUT.parent.mkdir(exist_ok=True, parents=True)
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(vcat), "-i", str(AUDIO),
        "-map", "0:v", "-map", "1:a",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart",
        "-t", "8.0",
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
