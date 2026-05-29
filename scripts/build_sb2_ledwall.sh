#!/usr/bin/env bash
# Build SB2 master at native LED-wall 4608x1536 (3:1) from existing v2 clips.
#
# Pipeline:
#   1. 3s slate at 4608x1536 with last 3s of countdown beep (last beep on cut)
#   2. Center-crop sb2_film.mp4 (1920x1080 16:9) to 1920x640 (3:1 content area)
#   3. Lanczos upscale to 4608x1536, polish pass (cyan grade, halation, grain, vignette)
#   4. Concat slate + body
#   5. Re-encode at CRF 22 to stay under GitHub 100MB
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"

SLATE_PNG="${SLATE_PNG:-/tmp/slate_3to1.png}"
BODY_IN="$ROOT/films/sb2_film.mp4"
COUNTDOWN_MP3="$ROOT/audio/slate_countdown.mp3"
OUT="$ROOT/films/sb2_master.mp4"

[ -f "$SLATE_PNG" ] || { echo "missing slate $SLATE_PNG" >&2; exit 1; }
[ -f "$BODY_IN" ] || { echo "missing $BODY_IN" >&2; exit 1; }

WORK=$(mktemp -d)
SLATE_DURATION=3
COUNTDOWN_START=8.80   # last 3 beeps; final beep lands on cut to film

# 1. Slate at 4608x1536 with countdown beeps. Forced 30fps to match body.
ffmpeg -y -hide_banner -loglevel error \
  -loop 1 -framerate 30 -t "$SLATE_DURATION" -i "$SLATE_PNG" \
  -ss "$COUNTDOWN_START" -t "$SLATE_DURATION" -i "$COUNTDOWN_MP3" \
  -vf "scale=4608:1536:force_original_aspect_ratio=decrease,pad=4608:1536:(ow-iw)/2:(oh-ih)/2:black,setsar=1,fps=30,format=yuv420p" \
  -c:v libx264 -pix_fmt yuv420p -crf 18 -preset slow \
  -c:a aac -b:a 192k -ar 48000 -ac 2 \
  -t "$SLATE_DURATION" \
  "$WORK/slate.mp4"

# 2. Body: center-crop 1920x1080 to 1920x640 (3:1), upscale to 4608x1536 lanczos.
#    Mild cyan grade + halation + grain + vignette (same polish chain as v23).
VFILT_BODY="\
crop=1920:640:0:(ih-640)/2,\
scale=4608:1536:flags=lanczos,\
format=yuv420p,\
eq=brightness=0.03:contrast=1.08:gamma=0.97:saturation=1.12,\
curves=master='0/0.03 0.25/0.22 0.5/0.5 0.75/0.78 1/0.97',\
curves=blue='0/0.02 0.5/0.50 1/1',\
split=2[base][bloom_src];\
[bloom_src]lutrgb=r='if(gt(val,210),val,0)':g='if(gt(val,210),val,0)':b='if(gt(val,210),val,0)',\
gblur=sigma=24,\
eq=saturation=1.5[bloom];\
[base][bloom]blend=all_mode=screen:all_opacity=0.28,\
noise=alls=6:allf=t+u,\
vignette=PI/5:eval=init\
"

ffmpeg -y -hide_banner -loglevel error \
  -i "$BODY_IN" \
  -filter_complex "[0:v]${VFILT_BODY}" \
  -c:v libx264 -pix_fmt yuv420p -crf 20 -preset slow \
  -c:a aac -b:a 192k -ar 48000 \
  -movflags +faststart \
  "$WORK/body.mp4"

# 3. Concat slate + body
cat > "$WORK/list.txt" <<EOF
file '$WORK/slate.mp4'
file '$WORK/body.mp4'
EOF
ffmpeg -y -hide_banner -loglevel error -f concat -safe 0 -i "$WORK/list.txt" \
  -c:v libx264 -pix_fmt yuv420p -crf 22 -preset slow \
  -c:a aac -b:a 192k -ar 48000 \
  -movflags +faststart \
  "$OUT"

# Poster
ffmpeg -y -hide_banner -loglevel error -ss 8 -i "$OUT" -frames:v 1 -update 1 \
  -vf "scale=1920:640" "$ROOT/films/sb2_poster.jpg"

echo ""
ffprobe -v error -show_entries format=duration:stream=codec_name,width,height -of default=nw=1 "$OUT"
SZ=$(ls -l "$OUT" | awk '{print $5}')
echo "wrote $OUT ($SZ bytes / $(du -h "$OUT" | awk '{print $1}'))"
rm -rf "$WORK"
