#!/usr/bin/env bash
# Grade SB1 to match the user's reference emerald (target ~#1FDC95)
# Heavy blue pull, green boost in mids/highlights, blacks kept deep.
set -euo pipefail

IN="$HOME/Projects/Orchestrate/films/sb1_film.mp4"
OUT_DIR="$HOME/Projects/Orchestrate/films/grades"
mkdir -p "$OUT_DIR"

# Grade D: tuned to reference. Target = #1FDC95 (R=31 G=220 B=149)
# Strategy:
#   1. colorchannelmixer: pull blue down to ~75%, redistribute some to green
#   2. hue rotate -22° (between teal and pure green)
#   3. colorbalance: green push in mids+highlights, blue pull everywhere
#   4. eq: saturation +18%, gamma slightly down to keep blacks deep
ffmpeg -y -hide_banner -loglevel error -i "$IN" \
  -vf "colorchannelmixer=rr=1.0:gg=1.08:gb=0.05:bg=0.15:bb=0.70,hue=h=-22,colorbalance=rs=-0.02:gs=0.05:bs=-0.15:rm=0.0:gm=0.15:bm=-0.20:rh=0.0:gh=0.12:bh=-0.18,eq=saturation=1.18:gamma=0.95" \
  -c:v libx264 -pix_fmt yuv420p -crf 16 -preset slow \
  -c:a copy "$OUT_DIR/D_emerald.mp4"

# Grade E: even more aggressive emerald (in case D is too subtle)
ffmpeg -y -hide_banner -loglevel error -i "$IN" \
  -vf "colorchannelmixer=rr=0.95:gg=1.15:gb=0.10:bg=0.20:bb=0.55,hue=h=-25,colorbalance=rs=-0.05:gs=0.10:bs=-0.25:rm=-0.02:gm=0.20:bm=-0.28:rh=-0.02:gh=0.18:bh=-0.25,eq=saturation=1.25:gamma=0.92" \
  -c:v libx264 -pix_fmt yuv420p -crf 16 -preset slow \
  -c:a copy "$OUT_DIR/E_emerald_heavy.mp4"

# Pull mid-frame stills + side-by-side D vs E vs reference-style hue (target hue is roughly 160°)
for v in D_emerald E_emerald_heavy; do
  ffmpeg -y -hide_banner -loglevel error -i "$OUT_DIR/$v.mp4" \
    -ss 12 -vframes 1 "$OUT_DIR/$v.png"
done

ffmpeg -y -hide_banner -loglevel error \
  -i "$OUT_DIR/A_original.png" \
  -i "$OUT_DIR/D_emerald.png" \
  -i "$OUT_DIR/E_emerald_heavy.png" \
  -filter_complex "[0:v]scale=640:-1[a];[1:v]scale=640:-1[d];[2:v]scale=640:-1[e];[a][d][e]hstack=inputs=3" \
  "$OUT_DIR/comparison_DE.png"

echo
ls -la "$OUT_DIR/D_emerald.mp4" "$OUT_DIR/E_emerald_heavy.mp4" "$OUT_DIR/comparison_DE.png"
