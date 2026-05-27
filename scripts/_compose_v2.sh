#!/usr/bin/env bash
# Compose v2 — uses v1 clips where they worked, drops in v2 re-renders for the
# 7 fixed beats, snaps cuts to librosa strong-beats, overlays ORCHESTRATE
# title-text on the hero hold (until SVG is provided).
#
# Output: films/electron_v2.mp4

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RDIR_V1="$ROOT/electron/_render_4k"
RDIR_V2="$ROOT/electron/_render_v2_4k"
AUDIO="$ROOT/references/demand-audio.m4a"
OUT="$ROOT/films/electron_v2.mp4"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# v2 beat-snapped timing — uses librosa strong_beats:
# strong_beats = [0.49, 24.26, 24.73, 28.42, 29.35, 32.11, 33.04, 36.27, 44.81]
# Cluster at 24-37s is the drop — visual action condenses there.
# Pacing: slow build (0-24s), drop (24-37s), ride-out (37-60s).
declare -a JOBS=(
  # name                source  t_in    t_out    notes
  "02a_wind             v1       5.000    9.000"   # 4s · solar/wind build
  "02b_solar            v1       9.000   13.000"   # 4s
  "02c_hydro            v1      13.000   17.000"   # 4s
  "03a_dense_field      v1      17.000   19.500"   # 2.5s · particle field forming
  "03b_grid_order       v1      19.500   22.000"   # 2.5s
  "03c_grid_perspective v1      22.000   24.260"   # 2.26s · land on first strong beat
  "04a_first_links      v1      24.260   24.730"   # 0.47s · MICRO-CUT on strong beat
  "04b_radiating_node   v1      24.730   26.500"   # 1.77s
  "04c_full_mesh        v1      26.500   28.420"   # 1.92s · strong beat
  "05a_paths_fan        v2      28.420   29.350"   # 0.93s · strong beat
  "05b_gridos           v2      29.350   32.110"   # 2.76s · strong beat
  "05c_path_chosen      v2      32.110   33.040"   # 0.93s · strong beat
  "06a_comet            v1      33.040   34.500"   # 1.46s
  "06b_currents         v1      34.500   35.500"   # 1s
  "06c_aurora           v1      35.500   36.270"   # 0.77s · strong beat
  "07a_gold_burst       v2      36.270   38.500"   # 2.23s
  "07b_lime_ripple      v2      38.500   41.000"   # 2.5s
  "07c_climax           v2      41.000   44.810"   # 3.81s · strong beat
  "08a_atlanta          v1      44.810   48.000"   # 3.19s · stadium reveal on strong beat
  "08b_distribution     v1      48.000   51.000"   # 3s
  "08c_aerial_sweep     v1      51.000   54.500"   # 3.5s
  "09a_venue_dawn       v1      54.500   56.500"   # 2s · approach
  "09b_keynote_stage    v1      56.500   58.000"   # 1.5s · into the room
  "09c_hero_hold        v2      58.000   60.000"   # 2s · ORCHESTRATE land
)

# Prepend chain_test for beats 01 (0-5s)
CT_TRIMMED="$TMP/00_chain_test.mp4"
echo "00. chain_test → trim to 5s, scale to 4K"
ffmpeg -hide_banner -y -ss 0 -i "$ROOT/electron/chain_test.mp4" -t 5 \
  -vf "scale=3840:2160:flags=lanczos" \
  -c:v libx264 -preset fast -crf 18 -pix_fmt yuv420p -an "$CT_TRIMMED" 2>&1 | tail -1

LIST="$TMP/list.txt"
echo "file '$CT_TRIMMED'" > "$LIST"

i=1
for line in "${JOBS[@]}"; do
  read -r name src t_in t_out <<<"$line"
  if [ "$src" = "v2" ]; then
    SRC_FILE="$RDIR_V2/$name.mp4"
  else
    SRC_FILE="$RDIR_V1/$name.mp4"
  fi
  if [ ! -f "$SRC_FILE" ]; then
    echo "warn: $SRC_FILE missing — falling back to v1 if not already"
    SRC_FILE="$RDIR_V1/$name.mp4"
    if [ ! -f "$SRC_FILE" ]; then echo "error: no source for $name"; exit 1; fi
  fi
  dur=$(awk "BEGIN{printf \"%.3f\", $t_out - $t_in}")
  DST="$TMP/$(printf '%02d' $i)_${name}.mp4"
  printf '%2d. %-22s  %s  %5.2fs\n' "$i" "$name" "$src" "$dur"
  # For 09c hero hold (the last clip), overlay ORCHESTRATE title text
  if [ "$name" = "09c_hero_hold" ]; then
    ffmpeg -hide_banner -y -ss 0 -i "$SRC_FILE" -t "$dur" \
      -vf "drawtext=text='ORCHESTRATE':fontfile=/System/Library/Fonts/Supplemental/Impact.ttf:fontsize=120:fontcolor=#A6FF00:x=(w-text_w)/2:y=(h-text_h)/2:alpha='if(lt(t,0.2),0,if(lt(t,0.6),(t-0.2)/0.4,1))',drawtext=text='2026':fontfile=/System/Library/Fonts/Supplemental/Impact.ttf:fontsize=48:fontcolor=#FFFFFF:x=(w-text_w)/2:y=(h-text_h)/2+90:alpha='if(lt(t,0.4),0,if(lt(t,0.8),(t-0.4)/0.4,1))'" \
      -c:v libx264 -preset fast -crf 18 -pix_fmt yuv420p -an "$DST" 2>&1 | tail -1
  else
    ffmpeg -hide_banner -y -ss 0 -i "$SRC_FILE" -t "$dur" -c:v libx264 -preset fast -crf 18 -pix_fmt yuv420p -an "$DST" 2>&1 | tail -1
  fi
  echo "file '$DST'" >> "$LIST"
  i=$((i + 1))
done

VCAT="$TMP/concat.mp4"
echo ""; echo "concat → $VCAT"
ffmpeg -hide_banner -y -f concat -safe 0 -i "$LIST" -c copy "$VCAT" 2>&1 | tail -2

echo ""; echo "mux audio → $OUT"
mkdir -p "$ROOT/films"
ffmpeg -hide_banner -y -i "$VCAT" -i "$AUDIO" \
  -map 0:v -map 1:a \
  -c:v copy -c:a aac -b:a 192k -shortest \
  -movflags +faststart \
  "$OUT" 2>&1 | tail -2

echo ""; echo "done · $OUT"
ffprobe -v error -show_entries format=duration,size -show_entries stream=codec_name,width,height,r_frame_rate -of default=noprint_wrappers=1 "$OUT"
