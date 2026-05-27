#!/usr/bin/env bash
# Upscale Veo 3 1080p renders to 4K UHD (3840×2160) using Topaz Video AI's
# Proteus model. Per Sparks delivery spec (Brittany Norton, 2026-05-27).
#
# Reads:  electron/_render/*.mp4   (1080p Veo outputs)
# Writes: electron/_render_4k/*.mp4 (3840×2160 H.264)
#
# Idempotent — skips any output >5 MB already on disk. Re-run safely.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/electron/_render"
OUT="$ROOT/electron/_render_4k"
TOPAZ_APP="/Applications/Topaz Video.app"
TOPAZ_FFMPEG="$TOPAZ_APP/Contents/MacOS/ffmpeg"
export TVAI_MODEL_DIR="$TOPAZ_APP/Contents/Resources/models"
export TVAI_MODEL_DATA_DIR="$TOPAZ_APP/Contents/Resources/models"

if [ ! -x "$TOPAZ_FFMPEG" ]; then
  echo "error: Topaz Video AI ffmpeg not found at $TOPAZ_FFMPEG"
  exit 1
fi
if [ ! -d "$SRC" ]; then
  echo "error: $SRC does not exist — run scripts/_veo_electron.mjs first"
  exit 1
fi

mkdir -p "$OUT"

# Proteus (prob-4) handles synthetic / dot-matrix / cinematic content best.
# scale=2 means 1920×1080 → 3840×2160 exactly (no aspect drift).
MODEL="prob-4"
SCALE="2"

shopt -s nullglob
clips=("$SRC"/*.mp4)
if [ "${#clips[@]}" -eq 0 ]; then
  echo "error: no clips found in $SRC"
  exit 1
fi

count=0
total="${#clips[@]}"
for src in "${clips[@]}"; do
  count=$((count + 1))
  name="$(basename "$src")"
  dst="$OUT/$name"

  if [ -f "$dst" ] && [ "$(stat -f%z "$dst" 2>/dev/null || stat -c%s "$dst")" -gt 5000000 ]; then
    echo "[$count/$total] $name — cached, skip"
    continue
  fi

  echo "[$count/$total] $name — upscaling 1080p → 4K (Proteus prob-4)…"
  # Topaz bundled ffmpeg only ships VideoToolbox encoders (no libx264).
  # h264_videotoolbox at 50 Mbps = solid 4K master quality on Apple Silicon.
  "$TOPAZ_FFMPEG" -hide_banner -y \
    -i "$src" \
    -vf "tvai_up=model=$MODEL:scale=$SCALE:vram=1:instances=1" \
    -c:v h264_videotoolbox -b:v 50M -pix_fmt yuv420p \
    -an \
    "$dst" 2>&1 | tail -3
done

echo ""
echo "done · $count clips · output: $OUT"
