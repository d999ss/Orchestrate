#!/usr/bin/env python3
"""
Detect beats, downbeats, and onsets in the locked audio track.

Output: scripts/beats.json with:
  - tempo (BPM)
  - beats (every detected beat, seconds)
  - onsets (transient/hit events, seconds — strongest energy changes)
  - strong_beats (beats that coincide with strong onsets; cut candidates)

The compose script can snap each storyboard beat boundary to the nearest
strong_beat for true musical sync.
"""

import json
import sys
from pathlib import Path

import librosa
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
AUDIO = ROOT / "references" / "demand-audio.m4a"
OUT = ROOT / "scripts" / "beats.json"

if not AUDIO.exists():
    print(f"error: {AUDIO} not found", file=sys.stderr)
    sys.exit(1)

print(f"loading · {AUDIO}", file=sys.stderr)
y, sr = librosa.load(str(AUDIO), sr=22050, mono=True)
duration = librosa.get_duration(y=y, sr=sr)
print(f"  · {duration:.2f}s · {sr} Hz", file=sys.stderr)

# Tempo + beats
print("beat-track …", file=sys.stderr)
tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, units="frames")
beat_times = librosa.frames_to_time(beat_frames, sr=sr)
tempo_val = float(tempo[0]) if hasattr(tempo, "__len__") else float(tempo)

# Onset strength (transients)
print("onset detect …", file=sys.stderr)
onset_env = librosa.onset.onset_strength(y=y, sr=sr)
onset_frames = librosa.onset.onset_detect(
    onset_envelope=onset_env, sr=sr, units="frames",
    pre_max=20, post_max=20, pre_avg=20, post_avg=20, delta=0.3, wait=10,
)
onset_times = librosa.frames_to_time(onset_frames, sr=sr)
onset_strengths_at_onsets = onset_env[onset_frames]

# Strong beats: beats that fall within 0.2s of a high-energy onset
print("strong-beat selection …", file=sys.stderr)
strong_threshold = float(np.percentile(onset_strengths_at_onsets, 70))
strong_onset_times = onset_times[onset_strengths_at_onsets >= strong_threshold]

strong_beats = []
for bt in beat_times:
    if any(abs(bt - ot) < 0.2 for ot in strong_onset_times):
        strong_beats.append(float(bt))

out = {
    "audio_file": str(AUDIO.relative_to(ROOT)),
    "duration_sec": float(duration),
    "sample_rate": int(sr),
    "tempo_bpm": tempo_val,
    "beats": [float(t) for t in beat_times],
    "onsets": [float(t) for t in onset_times],
    "onset_strengths": [float(s) for s in onset_strengths_at_onsets],
    "strong_beats": strong_beats,
    "strong_threshold_pct": 70,
}

OUT.write_text(json.dumps(out, indent=2))
print(f"\nwrote {OUT.relative_to(ROOT)}", file=sys.stderr)
print(f"  tempo:        {tempo_val:.1f} BPM", file=sys.stderr)
print(f"  beats:        {len(beat_times)}", file=sys.stderr)
print(f"  onsets:       {len(onset_times)}", file=sys.stderr)
print(f"  strong beats: {len(strong_beats)}  (cut candidates)", file=sys.stderr)
