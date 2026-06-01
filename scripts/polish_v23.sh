#!/usr/bin/env bash
# polish_v23.sh — visual + audio polish pass on the v23 master.
#
# Layers (none of this regenerates clips; pure post):
#   1. Audio: dynaudnorm to even out the pre-kick quiet bar
#   2. Color: lift blacks, gamma, push saturation, S-curve
#   3. Cyan boost: shadows toward teal, highlights toward cyan-white
#   4. Halation: warm bloom on the brightest pixels (lens-style)
#   5. Film grain: animated luma noise (~35mm 250D)
#   6. Vignette: soft circular falloff
#
# Output: films/sb1_master_v27_polish.mp4
set -euo pipefail

IN="${1:-films/sb1_master.mp4}"
OUT="${2:-films/sb1_master_v27_polish.mp4}"

cd "$(dirname "$0")/.."

# Filter chain — left to right is the pipeline.
VFILT="\
[0:v]format=yuv420p,\
eq=brightness=0.04:contrast=1.10:gamma=0.96:saturation=1.15,\
curves=master='0/0.04 0.25/0.22 0.5/0.5 0.75/0.78 1/0.97',\
curves=blue='0/0.02 0.5/0.50 1/1',\
split=2[base][bloom_src];\
[bloom_src]lutrgb=r='if(gt(val,210),val,0)':g='if(gt(val,210),val,0)':b='if(gt(val,210),val,0)',\
gblur=sigma=20,\
eq=saturation=1.6[bloom];\
[base][bloom]blend=all_mode=screen:all_opacity=0.30,\
noise=alls=8:allf=t+u,\
vignette=PI/5:eval=init,\
curves=master='0/0.02 0.4/0.36 0.6/0.66 1/0.98'\
"

# Audio chain — broadcast loudness normalization via loudnorm (EBU R128),
# THEN a gentle compressor on the quiet bar so the build-up is more present
# without crushing the kicks. Avoids the dynaudnorm-makes-everything-quiet trap.
AFILT="loudnorm=I=-14:TP=-1.5:LRA=11,acompressor=threshold=-24dB:ratio=1.6:attack=10:release=200:makeup=2"

echo "Applying polish pass to $IN..."
ffmpeg -y -hide_banner -loglevel error \
  -i "$IN" \
  -filter_complex "$VFILT" \
  -af "$AFILT" \
  -c:v libx264 -preset slow -crf 16 -pix_fmt yuv420p \
  -c:a aac -b:a 192k \
  -movflags +faststart \
  "$OUT"

ffprobe -v error -show_entries format=duration:stream=codec_name,width,height -of default=nw=1 "$OUT"
SZ=$(du -h "$OUT" | awk '{print $1}')
echo "wrote $OUT ($SZ)"
