#!/usr/bin/env bash
# Compose the final 60-second 4K master from the upscaled Veo renders and the
# locked Demand audio track.
#
# Reads:
#   electron/chain_test.mp4              (24s preview · beats 01A→01C — TBD if we keep or re-render at 4K)
#   electron/_render_4k/*.mp4            (24 × 1080p→4K upscaled clips for beats 02-09)
#   references/demand-audio.m4a          (60s locked audio)
# Writes:
#   electron_60s_4k.mp4                  (final deliverable, 3840×2160, H.264, AAC, ~60s)
#
# Trim/cut points come from BEATS_TIMELINE.md (needs refresh against demand-audio).
# This script assumes equal-pacing for now (~2.2s per frame); refine timings later.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RDIR="$ROOT/electron/_render_4k"
AUDIO="$ROOT/references/demand-audio.m4a"
OUT="$ROOT/electron_60s_4k.mp4"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# Beat-frame in-points (window seconds). Equal-paced default until BEATS_TIMELINE
# is re-paced against demand-audio.m4a. Each frame trims its 8s Veo clip to the
# duration listed (the visible runtime).
declare -a JOBS=(
  # name                 in_window_s  out_window_s
  "02a_wind              5.000        7.333"
  "02b_solar             7.333        9.667"
  "02c_hydro             9.667       12.000"
  "03a_dense_field      12.000       14.000"
  "03b_grid_order       14.000       16.000"
  "03c_grid_perspective 16.000       18.000"
  "04a_first_links      18.000       20.000"
  "04b_radiating_node   20.000       22.000"
  "04c_full_mesh        22.000       24.000"
  "05a_paths_fan        24.000       27.000"
  "05b_gridos           27.000       30.000"
  "05c_path_chosen      30.000       32.000"
  "06a_comet            32.000       34.500"
  "06b_currents         34.500       36.500"
  "06c_aurora           36.500       39.000"
  "07a_gold_burst       39.000       41.500"
  "07b_lime_ripple      41.500       43.500"
  "07c_climax           43.500       46.000"
  "08a_atlanta          46.000       49.000"
  "08b_distribution     49.000       52.000"
  "08c_aerial_sweep     52.000       55.000"
  "09a_venue_dawn       55.000       57.000"
  "09b_keynote_stage    57.000       58.500"
  "09c_hero_hold        58.500       60.000"
)

# Trim each upscaled clip to its target duration, write to TMP/<idx>.mp4
i=1
trim_inputs=()
for line in "${JOBS[@]}"; do
  read -r name t_in t_out <<<"$line"
  src="$RDIR/$name.mp4"
  dur=$(awk "BEGIN{printf \"%.3f\", $t_out - $t_in}")
  if [ ! -f "$src" ]; then
    echo "error: $src missing — run _veo_electron.mjs + _upscale_4k.sh first"
    exit 1
  fi
  dst="$TMP/$(printf '%02d' $i)_${name}.mp4"
  printf '%2d. %-22s  %5.2fs trim from %s\n' "$i" "$name" "$dur" "$src"
  ffmpeg -hide_banner -y -ss 0 -i "$src" -t "$dur" -c:v libx264 -preset fast -crf 18 -pix_fmt yuv420p -an "$dst" 2>&1 | tail -1
  trim_inputs+=("$dst")
  i=$((i + 1))
done

# Concat list for ffmpeg concat demuxer
LIST="$TMP/list.txt"
: > "$LIST"
# Prepend chain_test for beats 01A→01C (first 5s of window 0-5s)
# Note: chain_test is 1280×720 24s — we re-scale to 4K to match the rest.
if [ -f "$ROOT/electron/chain_test.mp4" ]; then
  CT_TRIMMED="$TMP/00_chain_test.mp4"
  echo "00. chain_test (beats 01) → trim to 5s, scale to 4K"
  ffmpeg -hide_banner -y -ss 0 -i "$ROOT/electron/chain_test.mp4" -t 5 \
    -vf "scale=3840:2160:flags=lanczos" \
    -c:v libx264 -preset fast -crf 18 -pix_fmt yuv420p -an "$CT_TRIMMED" 2>&1 | tail -1
  echo "file '$CT_TRIMMED'" >> "$LIST"
else
  echo "warn: chain_test.mp4 missing — beats 01 will be absent"
fi
for f in "${trim_inputs[@]}"; do echo "file '$f'" >> "$LIST"; done

# Concatenate video, then mux locked audio
VCAT="$TMP/concat.mp4"
echo ""
echo "concat → $VCAT"
ffmpeg -hide_banner -y -f concat -safe 0 -i "$LIST" -c copy "$VCAT" 2>&1 | tail -2

echo ""
echo "mux audio → $OUT"
ffmpeg -hide_banner -y -i "$VCAT" -i "$AUDIO" \
  -map 0:v -map 1:a \
  -c:v copy -c:a aac -b:a 192k -shortest \
  -movflags +faststart \
  "$OUT" 2>&1 | tail -2

echo ""
echo "done · $OUT"
ffprobe -v error -show_entries format=duration,size -show_entries stream=codec_name,width,height,r_frame_rate -of default=noprint_wrappers=1 "$OUT"
