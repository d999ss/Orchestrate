#!/usr/bin/env bash
# Hands-off finisher: keeps retrying the 15 remaining frames with the FPV chase prompt
# until Runway's daily cap clears, then assembles the full FPV cut and exports to Desktop.
# Quota is only spent on the 15 frames that still need FPV (the other 15 are already good).
cd /Users/donnysmith/Projects/Orchestrate || exit 1

LOG=/tmp/sb4_autofinish.log
CLIPS=films/sb4_clips_runway
REMAINING=(10 1 2 3 4 5 6 7 8 9 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30)
INTERVAL=2700          # 45 min between retry cycles while capped
MAX_CYCLES=64          # ~48h safety stop

note(){ echo "[$(date '+%m-%d %H:%M:%S')] $*" >> "$LOG"; }
notify(){ command -v sentinel-notify >/dev/null 2>&1 && sentinel-notify "$1" >/dev/null 2>&1 || true; }

: > "$LOG"
note "auto-finish started — ${#REMAINING[@]} clips need FPV: ${REMAINING[*]}"

cycle=0
while [ $cycle -lt $MAX_CYCLES ]; do
  cycle=$((cycle+1))
  todo=()
  for n in "${REMAINING[@]}"; do nn=$(printf "%02d" "$n"); [ -f "$CLIPS/.fpv-$nn" ] || todo+=("$n"); done
  if [ ${#todo[@]} -eq 0 ]; then note "all FPV clips complete"; break; fi
  note "cycle $cycle — attempting ${#todo[@]}: ${todo[*]}"
  for n in "${todo[@]}"; do
    nn=$(printf "%02d" "$n")
    out=$(.venv/bin/python scripts/gen_sb4_runway.py --force "$n" 2>&1)
    if echo "$out" | grep -q "^OK"; then
      touch "$CLIPS/.fpv-$nn"; note "  OK $nn"
    elif echo "$out" | grep -qi "daily task limit\|429"; then
      note "  daily cap still hit (at $nn) — pausing this cycle"; break
    else
      note "  fail $nn: $(echo "$out" | tail -1)"
    fi
  done
  done_ct=0; for n in "${REMAINING[@]}"; do nn=$(printf "%02d" "$n"); [ -f "$CLIPS/.fpv-$nn" ] && done_ct=$((done_ct+1)); done
  note "progress: $done_ct/${#REMAINING[@]} FPV done"
  [ $done_ct -eq ${#REMAINING[@]} ] && break
  sleep $INTERVAL
done

# assemble + export
note "assembling full FPV cut"
.venv/bin/python scripts/assemble_sb4.py "$PWD/films/sb4_fpv_full.mp4" >> "$LOG" 2>&1
DEST="$HOME/Desktop/Orchestrate SB4 videos $(date +%Y-%m-%d)"
mkdir -p "$DEST/clips"
cp films/sb4_fpv_full.mp4 "$DEST/00_FULL_FPV_cut_60s.mp4" 2>/dev/null
cp films/sb4_clips_runway/clip-*.mp4 "$DEST/clips/" 2>/dev/null
note "DONE — full FPV cut + 30 clips exported to: $DEST"
notify "Orchestrate SB4 done — full FPV cut on your Desktop"
touch "$CLIPS/.AUTOFINISH_DONE"
