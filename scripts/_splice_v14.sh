#!/usr/bin/env bash
# Splice the new 10s intro_v2 onto v12 body (from 10s onward) → electron_v14.mp4
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# Intro: full 10s of intro_v2
ffmpeg -hide_banner -loglevel error -y -i "$ROOT/films/electron_intro_v2.mp4" -t 10 \
  -c:v libx264 -preset fast -crf 18 -pix_fmt yuv420p -r 24 -an "$TMP/intro.mp4"

# Body: 10s-60s of v12 (50s)
ffmpeg -hide_banner -loglevel error -y -ss 10 -i "$ROOT/films/electron_v12.mp4" -t 50 \
  -c:v libx264 -preset fast -crf 18 -pix_fmt yuv420p -r 24 -an "$TMP/body.mp4"

# Concat + mux audio
printf "file '%s'\nfile '%s'\n" "$TMP/intro.mp4" "$TMP/body.mp4" > "$TMP/list.txt"
ffmpeg -hide_banner -loglevel error -y -f concat -safe 0 -i "$TMP/list.txt" \
  -c:v libx264 -preset fast -crf 18 -pix_fmt yuv420p "$TMP/vcat.mp4"

ffmpeg -hide_banner -loglevel error -y -i "$TMP/vcat.mp4" -i "$ROOT/references/demand-audio.m4a" \
  -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart \
  "$ROOT/films/electron_v14.mp4"

ls -lh "$ROOT/films/electron_v14.mp4"
ffprobe -v error -show_entries stream=codec_name,width,height -show_entries format=duration -of default=noprint_wrappers=1 "$ROOT/films/electron_v14.mp4"
