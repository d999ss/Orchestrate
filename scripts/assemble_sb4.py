#!/usr/bin/env python3
"""Assemble the SB4 beat-locked cut from Runway clips (+ stills for any not yet rendered).

Per frame: crop the 1584x528 (3:1) band out of the 1584x672 letterboxed clip, trim to the
cut-sheet duration, 30fps. If a clip is missing, hold the still for that duration so the
edit timing and audio sync stay intact. Concat in order, lay beats.mp3 windowed to the
0:48 start. Preview res = native band (1584x528); final gets Topaz-upscaled to 4608x1536.

Usage: .venv/bin/python scripts/assemble_sb4.py [out.mp4]
"""
import json, os, pathlib, subprocess, sys

ROOT = pathlib.Path("/Users/donnysmith/Projects/Orchestrate")
CUT = json.loads((ROOT / "audio" / "cut_sheet_sb4.json").read_text())
CLIPS = ROOT / "films" / "sb4_clips_runway"
STILLS = ROOT / "storyboard-4" / "3to1-4k"
BEATS = ROOT / "audio" / "music5.mp3"
AUDIO_START = CUT["audio_start_sec"]
WORK = pathlib.Path("/tmp/sb4_assemble"); WORK.mkdir(parents=True, exist_ok=True)
OUT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "films" / "sb4_rough.mp4"
W, H, FPS = 1584, 528, 30


def run(cmd): subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


segs = []
used_clip = used_still = 0
for w in CUT["windows"]:
    n = w["frame"]; d = round(w["duration"], 3)
    seg = WORK / f"seg-{n:02d}.mp4"
    clip = CLIPS / f"clip-{n:02d}.mp4"
    # Clips verified clean (fill frame, no box) are listed in CLIP_OK.txt; ingest_manual.py appends to it.
    _ok = CLIPS / "CLIP_OK.txt"
    CLIP_OK = {int(x) for x in _ok.read_text().split()} if _ok.exists() else {1, 2, 4, 6, 7, 8, 9, 12, 15, 17, 21}
    if n in CLIP_OK and clip.exists() and clip.stat().st_size > 10000:
        clen = float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
                "-of","default=noprint_wrappers=1:nokey=1",str(clip)],capture_output=True,text=True).stdout.strip() or 5.0)
        vf = f"crop={W}:{H}:0:72"
        if d > clen + 0.05:               # hold longer than the clip -> slow it to fill (no freeze)
            vf += f",setpts={d/clen:.4f}*PTS"
        vf += f",fps={FPS},setsar=1"
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(clip),
             "-t", str(d), "-vf", vf,
             "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(seg)])
        used_clip += 1
    else:
        # hold the still for d (placeholder for not-yet-rendered clips)
        run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-t", str(d),
             "-i", str(STILLS / f"frame-{n:02d}.png"),
             "-vf", f"scale={W}:{H},fps={FPS},setsar=1",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", str(seg)])
        used_still += 1
    segs.append(seg)

# concat (re-encode for safety across mixed sources)
lst = WORK / "list.txt"
lst.write_text("".join(f"file '{s}'\n" for s in segs))
silent = WORK / "silent.mp4"
# grade to match the other LED-wall films (cool, contrasty, slight vignette, fine grain)
GRADE = ("eq=brightness=0.02:contrast=1.08:gamma=0.97:saturation=1.14,"
         "curves=master='0/0.02 0.25/0.21 0.5/0.5 0.75/0.79 1/0.98',"
         "curves=blue='0/0.02 0.5/0.5 1/1',"
         "vignette=PI/5,noise=alls=5:allf=t")
run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
     "-vf", GRADE, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS), str(silent)])

total = round(sum(w["duration"] for w in CUT["windows"]), 3)
run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(silent),
     "-ss", str(AUDIO_START), "-t", str(total), "-i", str(BEATS),
     "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(OUT)])

print(f"wrote {OUT}  ({total}s, {used_clip} clips + {used_still} stills)")
