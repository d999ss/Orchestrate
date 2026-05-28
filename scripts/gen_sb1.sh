#!/usr/bin/env bash
# Generate 8 Veo 3.0-fast image-to-video clips for Storyboard 1.
# Each clip is 8s, 1080p, 16:9, no Veo audio (we mux demand-audio.m4a later).
# Submits all 8 in parallel, waits for completion, downloads MP4s.
set -u

cd "$(dirname "$0")/.."
ROOT="$PWD"
source ~/.claude/secrets/orchestrate-veo.env

OUT="$ROOT/films/sb1_clips"
mkdir -p "$OUT"

TOKEN=$(python3 -c "
from google.oauth2 import service_account
from google.auth.transport.requests import Request
import os
creds = service_account.Credentials.from_service_account_file(
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'],
    scopes=['https://www.googleapis.com/auth/cloud-platform'])
creds.refresh(Request())
print(creds.token)
")

MODEL="veo-3.0-fast-generate-001"
ENDPOINT="https://${GCP_LOCATION}-aiplatform.googleapis.com/v1/projects/${GCP_PROJECT}/locations/${GCP_LOCATION}/publishers/google/models/${MODEL}"

# Keyframe → prompt map (locked-camera, subject motion only)
declare -a KEYFRAMES=(01 05 09 13 17 21 25 29)
declare -a PROMPTS=(
"Locked-off camera, tripod-mounted, completely static frame. No pan, tilt, zoom, dolly, or shake. A glowing globe floats in deep darkness. City lights twinkle on one by one across the world map, faint cyan-white. Subtle drifting particles. Cold cinematic palette. Photoreal, broadcast film quality."
"Locked-off camera, completely static frame. Massive turbine rotor blades in a brightly-lit hot air stream. Blades accelerate from slow rotation to high speed, motion blur intensifying. Cold blue-white industrial light. Hyperreal mechanical detail, sparks of heat haze. Photoreal."
"Locked-off camera, completely static frame. Glowing cyan-white electricity travels through a network of polished conductors and busbars. Pulses of energy move smoothly across the frame. Macro detail, dark industrial background. Photoreal, cinematic."
"Locked-off camera, completely static aerial top-down. A regional electrical grid revealed as a glowing cyan network across dark terrain. Lines pulse outward in synchronized waves from substations. Subtle drift of overlaid data. Photoreal, cinematic."
"Locked-off camera, completely static wide. Distant Atlanta skyline at night. Lights surge brighter in cascading waves across the city as power flows in. Subtle cyan grid lines tracing the network. Dramatic dynamic range, photoreal."
"Locked-off camera, completely static aerial wide of an Atlanta-style stadium at night. Stadium bowl lights bloom on in a rolling sequence across the seating sections. Dust and atmospheric haze. Photoreal, cinematic."
"Locked-off camera, completely static. Modern conference center exterior at night. Interior lights cascade on floor by floor, top to bottom, in synchronized waves. Cold cyan-white glow through glass. Photoreal, hyperreal architectural detail."
"Locked-off camera, completely static. A wide reveal: dark keynote stage in foreground glowing cyan-white, illuminated Atlanta cityscape stretching behind through a vast window. Slow particle bloom around the GE Vernova brand mark center frame. Reverent, hero, photoreal."
)

submit() {
  local idx=$1 frame=$2 prompt=$3
  local img="$ROOT/storyboard-1/frame-${frame}.png"
  if [ ! -f "$img" ]; then echo "MISSING $img" >&2; return 1; fi
  local b64; b64=$(base64 -i "$img")
  local payload
  payload=$(python3 -c "
import json, sys
print(json.dumps({
  'instances':[{'prompt': sys.argv[1], 'image':{'bytesBase64Encoded': sys.argv[2], 'mimeType':'image/png'}}],
  'parameters':{'aspectRatio':'16:9','durationSeconds':8,'sampleCount':1,'resolution':'1080p','personGeneration':'allow_all','generateAudio':False}
}))" "$prompt" "$b64")
  local r
  r=$(curl -s "${ENDPOINT}:predictLongRunning" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "$payload")
  local opname; opname=$(echo "$r" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('name',''))")
  if [ -z "$opname" ]; then
    echo "SUBMIT FAIL clip $idx: $r" >&2
    return 1
  fi
  echo "$opname" > "$OUT/clip-${idx}.opname"
  echo "submit clip $idx (frame-${frame}) → ${opname##*/}"
}

echo "=== Submitting 8 Veo ops in parallel ==="
for i in "${!KEYFRAMES[@]}"; do
  submit "$((i+1))" "${KEYFRAMES[$i]}" "${PROMPTS[$i]}" &
done
wait
echo

echo "=== Polling until all done ==="
DONE_COUNT=0
while [ "$DONE_COUNT" -lt 8 ]; do
  DONE_COUNT=0
  for i in $(seq 1 8); do
    OPFILE="$OUT/clip-${i}.opname"
    OUTFILE="$OUT/clip-${i}.mp4"
    [ -f "$OUTFILE" ] && { DONE_COUNT=$((DONE_COUNT+1)); continue; }
    [ ! -f "$OPFILE" ] && continue
    OPNAME=$(cat "$OPFILE")
    R=$(curl -s "${ENDPOINT}:fetchPredictOperation" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d "{\"operationName\":\"$OPNAME\"}")
    DONE=$(echo "$R" | python3 -c "import sys,json; print(json.load(sys.stdin).get('done'))")
    if [ "$DONE" = "True" ]; then
      python3 -c "
import sys, json, base64
d = json.load(sys.stdin)
err = d.get('error')
if err:
    print('ERR clip $i:', err, file=sys.stderr); sys.exit(1)
resp = d.get('response', {})
preds = resp.get('videos') or []
if not preds:
    print('no preds for clip $i', file=sys.stderr); sys.exit(1)
p = preds[0]
b64 = p.get('bytesBase64Encoded')
if b64:
    open('$OUTFILE','wb').write(base64.b64decode(b64))
    print('saved $OUTFILE')
elif p.get('gcsUri'):
    print('gcsUri returned for $i:', p['gcsUri'])
" <<< "$R"
      DONE_COUNT=$((DONE_COUNT+1))
    fi
  done
  if [ "$DONE_COUNT" -lt 8 ]; then
    echo "$(date +%H:%M:%S) done $DONE_COUNT/8…"
    sleep 15
    # refresh token if approaching 50min
    TOKEN=$(python3 -c "
from google.oauth2 import service_account
from google.auth.transport.requests import Request
import os
creds = service_account.Credentials.from_service_account_file(
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'],
    scopes=['https://www.googleapis.com/auth/cloud-platform'])
creds.refresh(Request())
print(creds.token)
")
  fi
done

echo
echo "=== All 8 clips downloaded ==="
ls -la "$OUT"/*.mp4
