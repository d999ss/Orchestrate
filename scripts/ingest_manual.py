#!/usr/bin/env python3
"""Ingest a manually-generated clip (any resolution/aspect) as clip-NN.
Scale-to-FILLS the 3:1 band (1584x528) so a centered subject survives, then marks
the frame 'good' so the assembler uses it. Usage: ingest_manual.py <N> <path-to-clip>"""
import sys, subprocess, pathlib
ROOT=pathlib.Path("/Users/donnysmith/Projects/Orchestrate")
n=int(sys.argv[1]); src=sys.argv[2]
out=ROOT/f"films/sb4_clips_runway/clip-{n:02d}.mp4"
subprocess.run(["ffmpeg","-y","-loglevel","error","-i",src,
  "-vf","scale=1584:528:force_original_aspect_ratio=increase,crop=1584:528,fps=30,setsar=1",
  "-an","-c:v","libx264","-pix_fmt","yuv420p",str(out)],check=True)
ok=ROOT/"films/sb4_clips_runway/CLIP_OK.txt"
have=set(ok.read_text().split()) if ok.exists() else set()
have.add(str(n)); ok.write_text(" ".join(sorted(have,key=int)))
print(f"ingested clip-{n:02d} (3:1 band) and marked good; CLIP_OK now: {sorted(have,key=int)}")
