#!/usr/bin/env bash
# Final SB1 master assembly: slate (5s w/ countdown beep) + film (60s) = 65s
set -euo pipefail

ROOT="$HOME/Projects/Orchestrate"
SLATE_PNG="$1"
FILM="$2"
OUT="${3:-$ROOT/films/sb1_master.mp4}"
COUNTDOWN_MP3="$ROOT/audio/slate_countdown.mp3"
SLATE_DURATION=3
COUNTDOWN_START=8.80   # the countdown file has clear 1s-spaced beeps from 4.8s on.
                       # 8.80→11.80 captures exactly 3 beeps with the last one
                       # landing on the cut to the film.

WORK=$(mktemp -d)

# Build 3s slate video with exactly 3 countdown beeps. Final beep lands on
# the cut to the film (classic cinema countdown convention).
ffmpeg -y -hide_banner -loglevel error \
  -loop 1 -framerate 30 -t "$SLATE_DURATION" -i "$SLATE_PNG" \
  -ss "$COUNTDOWN_START" -t "$SLATE_DURATION" -i "$COUNTDOWN_MP3" \
  -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black,setsar=1,format=yuv420p" \
  -c:v libx264 -pix_fmt yuv420p -crf 16 -preset slow \
  -c:a aac -b:a 192k -ar 48000 -ac 2 \
  -t "$SLATE_DURATION" \
  -movflags +faststart \
  "$WORK/slate.mp4"

# 2. Normalize the film's audio sample rate / codec to match slate (re-encode briefly)
ffmpeg -y -hide_banner -loglevel error \
  -i "$FILM" \
  -c:v copy \
  -c:a aac -b:a 192k -ar 48000 \
  "$WORK/film_norm.mp4"

# 3. Concat via concat demuxer (requires matching streams)
cat > "$WORK/list.txt" <<EOF
file '$WORK/slate.mp4'
file '$WORK/film_norm.mp4'
EOF

ffmpeg -y -hide_banner -loglevel error \
  -f concat -safe 0 -i "$WORK/list.txt" \
  -c copy \
  -movflags +faststart \
  "$OUT"

echo
ffprobe -v error -show_entries format=duration:stream=codec_name,width,height -of default=nw=1 "$OUT"
echo "wrote $OUT ($(du -h "$OUT" | awk '{print $1}'))"
rm -rf "$WORK"
