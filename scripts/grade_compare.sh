#!/usr/bin/env bash
# Render 3 color-grade variants of sb1_film.mp4 for side-by-side comparison.
# Target: storyboard teal-emerald #4ed9c6.
set -euo pipefail

IN="$HOME/Projects/Orchestrate/films/sb1_film.mp4"
OUT_DIR="$HOME/Projects/Orchestrate/films/grades"
mkdir -p "$OUT_DIR"

# Grade A: current (no change)
cp "$IN" "$OUT_DIR/A_original.mp4"

# Grade B: medium teal-emerald. Hue shift -15°, slight green boost, blue pull-down.
# hue h takes degrees. colorbalance shifts shadows/mids/highlights.
ffmpeg -y -hide_banner -loglevel error -i "$IN" \
  -vf "hue=h=-15,colorbalance=rs=0.0:gs=0.05:bs=-0.05:rm=0.0:gm=0.08:bm=-0.08:rh=0.0:gh=0.05:bh=-0.05" \
  -c:v libx264 -pix_fmt yuv420p -crf 16 -preset slow \
  -c:a copy "$OUT_DIR/B_medium.mp4"

# Grade C: heavy emerald. Hue shift -28°, stronger green boost.
ffmpeg -y -hide_banner -loglevel error -i "$IN" \
  -vf "hue=h=-28,colorbalance=rs=0.0:gs=0.10:bs=-0.10:rm=0.0:gm=0.15:bm=-0.15:rh=0.0:gh=0.10:bh=-0.10,eq=saturation=1.05" \
  -c:v libx264 -pix_fmt yuv420p -crf 16 -preset slow \
  -c:a copy "$OUT_DIR/C_heavy.mp4"

# Build a 1-frame-each comparison strip from each version (mid-film thumb)
for v in A_original B_medium C_heavy; do
  ffmpeg -y -hide_banner -loglevel error -i "$OUT_DIR/$v.mp4" \
    -ss 12 -vframes 1 "$OUT_DIR/$v.png"
done

# Side-by-side comparison still (no text labels — drawtext not available)
ffmpeg -y -hide_banner -loglevel error \
  -i "$OUT_DIR/A_original.png" \
  -i "$OUT_DIR/B_medium.png" \
  -i "$OUT_DIR/C_heavy.png" \
  -filter_complex "[0:v]scale=640:-1[a];[1:v]scale=640:-1[b];[2:v]scale=640:-1[c];[a][b][c]hstack=inputs=3" \
  "$OUT_DIR/comparison.png"

echo
echo "Outputs:"
ls -la "$OUT_DIR"/*.mp4 "$OUT_DIR"/comparison.png
