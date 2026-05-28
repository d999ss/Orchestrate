#!/usr/bin/env bash
# Assemble 8 Veo clips into a 58.6s film cut on every 4th downbeat of Beats.mp3
# Audio segment: 29.067s → 87.680s of Beats.mp3 (the energetic core)
# Cut points (relative to film start): 0.00, 7.392, 14.773, 22.154, 29.535, 36.927, 44.084, 51.231, 58.613
set -euo pipefail

cd "$(dirname "$0")/.."
ROOT="$PWD"
CLIPS="$ROOT/films/sb1_clips"
AUDIO="$ROOT/audio/Beats.mp3"
OUT="$ROOT/films/sb1_film.mp4"
WORK=$(mktemp -d)

# Per-clip durations matching every-4th-downbeat windows in Beats.mp3 29-88s segment
DUR=(7.392 7.381 7.381 7.381 7.392 7.157 7.147 7.381)
AUDIO_START=29.067
AUDIO_LEN=58.613

for i in 1 2 3 4 5 6 7 8; do
  IN="$CLIPS/clip-$i.mp4"
  D="${DUR[$((i-1))]}"
  if [ ! -f "$IN" ]; then echo "MISSING $IN" >&2; exit 1; fi
  ffmpeg -y -hide_banner -loglevel error \
    -i "$IN" \
    -t "$D" \
    -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black,setsar=1,fps=30" \
    -an -c:v libx264 -pix_fmt yuv420p -crf 16 -preset slow \
    "$WORK/trim-$i.mp4"
done

{ for i in 1 2 3 4 5 6 7 8; do echo "file '$WORK/trim-$i.mp4'"; done; } > "$WORK/concat.txt"

ffmpeg -y -hide_banner -loglevel error \
  -f concat -safe 0 -i "$WORK/concat.txt" \
  -c:v copy "$WORK/visuals.mp4"

# Trim Beats.mp3 to the energetic 58.6s window
ffmpeg -y -hide_banner -loglevel error \
  -ss "$AUDIO_START" -t "$AUDIO_LEN" -i "$AUDIO" \
  -c:a aac -b:a 192k "$WORK/audio_trim.m4a"

# Mux
ffmpeg -y -hide_banner -loglevel error \
  -i "$WORK/visuals.mp4" \
  -i "$WORK/audio_trim.m4a" \
  -map 0:v:0 -map 1:a:0 \
  -c:v copy -c:a copy \
  -shortest -movflags +faststart \
  "$OUT"

echo
ffprobe -v error -show_entries format=duration:stream=codec_name,width,height -of default=nw=1 "$OUT"
echo "wrote $OUT ($(du -h "$OUT" | awk '{print $1}'))"
rm -rf "$WORK"
