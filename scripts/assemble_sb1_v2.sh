#!/usr/bin/env bash
# Assemble all 30 SB1 Veo clips into a 60s film cut to Beats.mp3 cut_sheet.json
set -euo pipefail

cd "$(dirname "$0")/.."
ROOT="$PWD"
CLIPS="$ROOT/films/sb1_clips"
AUDIO="$ROOT/audio/Beats.mp3"
CUT_SHEET="$ROOT/audio/cut_sheet.json"
OUT="$ROOT/films/sb1_film.mp4"
WORK=$(mktemp -d)

# Read cut sheet
AUDIO_START=$(jq -r '.audio_start_sec' "$CUT_SHEET")
AUDIO_LEN=$(jq -r '.film_duration_sec' "$CUT_SHEET")
N_CUTS=$(jq -r '.windows | length' "$CUT_SHEET")

echo "Cut sheet: $N_CUTS windows, audio $AUDIO_START → +$AUDIO_LEN s"

# Verify all unique frames referenced exist
for F in $(jq -r '.windows[].frame' "$CUT_SHEET" | sort -u); do
  PADF=$(printf "%02d" "$F")
  if [ ! -f "$CLIPS/clip-$PADF.mp4" ]; then
    echo "MISSING $CLIPS/clip-$PADF.mp4" >&2
    exit 1
  fi
done

# Trim each clip to its window duration. NO SLOW MOTION EVER.
# Native playback only. If a window happens to exceed native length, it gets
# capped to native (rare — cut sheet should never ask for this).
for i in $(seq 1 "$N_CUTS"); do
  IDX=$(printf "%03d" "$i")
  FRAME=$(jq -r ".windows[$((i-1))].frame" "$CUT_SHEET")
  PADF=$(printf "%02d" "$FRAME")
  IN="$CLIPS/clip-$PADF.mp4"
  D=$(jq -r ".windows[$((i-1))].duration" "$CUT_SHEET")
  ffmpeg -y -hide_banner -loglevel error \
    -i "$IN" \
    -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black,setsar=1,fps=30" \
    -t "$D" \
    -an -c:v libx264 -pix_fmt yuv420p -crf 16 -preset slow \
    "$WORK/trim-$IDX.mp4"
done

# Concat list
{ for i in $(seq 1 "$N_CUTS"); do printf "file '%s/trim-%03d.mp4'\n" "$WORK" "$i"; done; } > "$WORK/concat.txt"

ffmpeg -y -hide_banner -loglevel error \
  -f concat -safe 0 -i "$WORK/concat.txt" \
  -c:v copy "$WORK/visuals_raw.mp4"

# Fade-out last 1.5s of visuals so the film doesn't end abruptly
FADE_DUR=1.5
FADE_START=$(awk -v t="$AUDIO_LEN" -v f="$FADE_DUR" 'BEGIN{printf "%.3f", t-f}')
ffmpeg -y -hide_banner -loglevel error \
  -i "$WORK/visuals_raw.mp4" \
  -vf "fade=out:st=${FADE_START}:d=${FADE_DUR}" \
  -an -c:v libx264 -pix_fmt yuv420p -crf 16 -preset slow \
  "$WORK/visuals.mp4"

# Trim Beats.mp3 to the cut-sheet window, fade out audio in sync
ffmpeg -y -hide_banner -loglevel error \
  -ss "$AUDIO_START" -t "$AUDIO_LEN" -i "$AUDIO" \
  -af "afade=t=out:st=${FADE_START}:d=${FADE_DUR}" \
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
