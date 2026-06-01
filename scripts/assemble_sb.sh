#!/usr/bin/env bash
# Parametric assembler — assembles a film for SB1/SB2/SB3
# Usage:  bash scripts/assemble_sb.sh <sb_num>
#         scripts/assemble_sb.sh 2
set -euo pipefail

SB="${1:?usage: assemble_sb.sh <sb_num>}"
cd "$(dirname "$0")/.."
ROOT="$PWD"
CLIPS="$ROOT/films/sb${SB}_clips"
AUDIO="$ROOT/audio/Beats.mp3"
CUT_SHEET="$ROOT/audio/cut_sheet_sb${SB}.json"
OUT="$ROOT/films/sb${SB}_film.mp4"
WORK=$(mktemp -d)

[ -f "$CUT_SHEET" ] || { echo "missing $CUT_SHEET — run audio/cut_sheet_sb.py $SB first"; exit 1; }
[ -d "$CLIPS" ] || { echo "missing $CLIPS"; exit 1; }

AUDIO_START=$(jq -r '.audio_start_sec' "$CUT_SHEET")
AUDIO_LEN=$(jq -r '.film_duration_sec' "$CUT_SHEET")
N_CUTS=$(jq -r '.windows | length' "$CUT_SHEET")
echo "SB${SB}: $N_CUTS windows, audio $AUDIO_START → +$AUDIO_LEN s"

for F in $(jq -r '.windows[].frame' "$CUT_SHEET" | sort -u); do
  PADF=$(printf "%02d" "$F")
  [ -f "$CLIPS/clip-$PADF.mp4" ] || { echo "MISSING $CLIPS/clip-$PADF.mp4" >&2; exit 1; }
done

# Trim each clip to its window duration. Native playback (no fake zoompan).
for i in $(seq 1 "$N_CUTS"); do
  IDX=$(printf "%03d" "$i")
  FRAME=$(jq -r ".windows[$((i-1))].frame" "$CUT_SHEET")
  PADF=$(printf "%02d" "$FRAME")
  IN="$CLIPS/clip-$PADF.mp4"
  D=$(jq -r ".windows[$((i-1))].duration" "$CUT_SHEET")
  ffmpeg -y -hide_banner -loglevel error \
    -i "$IN" \
    -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black,setsar=1,fps=30,tpad=stop_mode=clone:stop_duration=10" \
    -t "$D" \
    -an -c:v libx264 -pix_fmt yuv420p -crf 16 -preset slow \
    "$WORK/trim-$IDX.mp4"
done

{ for i in $(seq 1 "$N_CUTS"); do printf "file '%s/trim-%03d.mp4'\n" "$WORK" "$i"; done; } > "$WORK/concat.txt"
ffmpeg -y -hide_banner -loglevel error -f concat -safe 0 -i "$WORK/concat.txt" -c:v copy "$WORK/visuals_raw.mp4"

# Fade-out last 1.5s
FADE_DUR=1.5
FADE_START=$(awk -v t="$AUDIO_LEN" -v f="$FADE_DUR" 'BEGIN{printf "%.3f", t-f}')
ffmpeg -y -hide_banner -loglevel error \
  -i "$WORK/visuals_raw.mp4" \
  -vf "fade=out:st=${FADE_START}:d=${FADE_DUR}" \
  -an -c:v libx264 -pix_fmt yuv420p -crf 16 -preset slow \
  "$WORK/visuals.mp4"

# Sample-accurate audio trim: decode MP3 to WAV first, then seek/trim there.
# `-ss` BEFORE `-i` on MP3 snaps to packet boundary (~26ms drift). Fix: decode
# entire file to WAV (no packet snap), then `-ss` AFTER `-i` is sample-accurate.
ffmpeg -y -hide_banner -loglevel error \
  -i "$AUDIO" -ar 48000 -ac 2 -c:a pcm_s16le "$WORK/audio_full.wav"

ffmpeg -y -hide_banner -loglevel error \
  -i "$WORK/audio_full.wav" -ss "$AUDIO_START" -t "$AUDIO_LEN" \
  -af "afade=t=out:st=${FADE_START}:d=${FADE_DUR}" \
  -c:a aac -b:a 192k "$WORK/audio_trim.m4a"

ffmpeg -y -hide_banner -loglevel error \
  -i "$WORK/visuals.mp4" -i "$WORK/audio_trim.m4a" \
  -map 0:v:0 -map 1:a:0 -c:v copy -c:a copy -shortest -movflags +faststart \
  "$OUT"

echo
ffprobe -v error -show_entries format=duration:stream=codec_name,width,height -of default=nw=1 "$OUT"
echo "wrote $OUT ($(du -h "$OUT" | awk '{print $1}'))"

# Build master with 3-beep slate
MASTER="$ROOT/films/sb${SB}_master.mp4"
bash "$ROOT/scripts/assemble_master.sh" /tmp/slate.png "$OUT" "$MASTER"

# Poster
ffmpeg -y -hide_banner -loglevel error -ss 1.0 -i "$OUT" -vframes 1 -vf "scale=1920:1080" "$ROOT/films/sb${SB}_poster.jpg"
echo "wrote sb${SB}_master.mp4 and sb${SB}_poster.jpg"

rm -rf "$WORK"
