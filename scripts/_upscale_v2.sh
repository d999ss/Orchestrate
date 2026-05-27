#!/usr/bin/env bash
# Upscale the v2 re-renders to 4K via Topaz Proteus.
# Reads:  electron/_render_v2/*.mp4
# Writes: electron/_render_v2_4k/*.mp4

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/electron/_render_v2"
OUT="$ROOT/electron/_render_v2_4k"
TOPAZ_APP="/Applications/Topaz Video.app"
TOPAZ_FFMPEG="$TOPAZ_APP/Contents/MacOS/ffmpeg"
export TVAI_MODEL_DIR="$TOPAZ_APP/Contents/Resources/models"
export TVAI_MODEL_DATA_DIR="$TOPAZ_APP/Contents/Resources/models"

if [ ! -d "$SRC" ]; then echo "error: $SRC missing"; exit 1; fi
mkdir -p "$OUT"

shopt -s nullglob
clips=("$SRC"/*.mp4)
[ "${#clips[@]}" -eq 0 ] && { echo "error: no v2 clips"; exit 1; }

count=0
for src in "${clips[@]}"; do
  count=$((count + 1))
  name="$(basename "$src")"
  dst="$OUT/$name"
  if [ -f "$dst" ] && [ "$(stat -f%z "$dst" 2>/dev/null || stat -c%s "$dst")" -gt 5000000 ]; then
    echo "[$count] $name — cached, skip"; continue
  fi
  echo "[$count] $name — upscaling 1080p → 4K"
  "$TOPAZ_FFMPEG" -hide_banner -y \
    -i "$src" \
    -vf "tvai_up=model=prob-4:scale=2:vram=1:instances=1" \
    -c:v h264_videotoolbox -b:v 50M -pix_fmt yuv420p \
    -an \
    "$dst" 2>&1 | tail -1
done

echo "done · $count clips · $OUT"
