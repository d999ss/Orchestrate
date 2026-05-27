#!/usr/bin/env python3
"""
Deep music analysis for the Beat Map tab.

Extracts: tempo, beats, downbeats, onsets, onset strengths, RMS energy curve,
silences, spectral flux (transients), climax windows, breath windows.

Output: scripts/music_analysis.json
"""

import json
import sys
from pathlib import Path

import librosa
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
AUDIO = ROOT / "references" / "demand-audio.m4a"
OUT = ROOT / "scripts" / "music_analysis.json"

if not AUDIO.exists():
    sys.exit(f"missing {AUDIO}")

print(f"load · {AUDIO}", file=sys.stderr)
y, sr = librosa.load(str(AUDIO), sr=22050, mono=True)
duration = float(librosa.get_duration(y=y, sr=sr))
print(f"  · {duration:.2f}s · {sr} Hz", file=sys.stderr)

# Tempo + beats
print("beat track…", file=sys.stderr)
tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, units="frames")
beat_times = librosa.frames_to_time(beat_frames, sr=sr).tolist()
tempo_val = float(tempo[0]) if hasattr(tempo, "__len__") else float(tempo)

# Onset detection (transients)
print("onset detect…", file=sys.stderr)
onset_env = librosa.onset.onset_strength(y=y, sr=sr)
onset_frames = librosa.onset.onset_detect(
    onset_envelope=onset_env, sr=sr, units="frames",
    pre_max=15, post_max=15, pre_avg=15, post_avg=15, delta=0.25, wait=8,
)
onset_times = librosa.frames_to_time(onset_frames, sr=sr).tolist()
onset_strengths = [float(s) for s in onset_env[onset_frames]]

# RMS energy curve (200ms windows)
print("rms…", file=sys.stderr)
frame_len = int(sr * 0.2)
hop_len = int(sr * 0.05)  # 50ms hop for smoother curve
rms = librosa.feature.rms(y=y, frame_length=frame_len, hop_length=hop_len)[0]
rms_times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop_len).tolist()
rms_db = [float(20 * np.log10(max(r, 1e-6))) for r in rms]

# Spectral flux — where the spectrum is changing fast (good for transitions/swells)
print("spectral flux…", file=sys.stderr)
S = np.abs(librosa.stft(y, n_fft=2048, hop_length=hop_len))
flux = np.sqrt(np.sum(np.diff(S, axis=1, prepend=0) ** 2, axis=0))
flux_norm = (flux - flux.min()) / (flux.max() - flux.min() + 1e-9)
flux_times = librosa.frames_to_time(np.arange(len(flux_norm)), sr=sr, hop_length=hop_len).tolist()
flux_vals = [float(v) for v in flux_norm]

# Climax windows: top 10% RMS sustained for >0.5s
print("climaxes…", file=sys.stderr)
rms_arr = np.array(rms_db)
climax_threshold = float(np.percentile(rms_arr, 90))
climax_mask = rms_arr > climax_threshold
climax_windows = []
in_window = False
ws = 0.0
for i, m in enumerate(climax_mask):
    t = rms_times[i]
    if m and not in_window:
        in_window = True
        ws = t
    elif not m and in_window:
        in_window = False
        if t - ws >= 0.5:
            climax_windows.append([float(ws), float(t)])

# Breath windows: bottom 15% RMS sustained for >0.4s
breath_threshold = float(np.percentile(rms_arr, 15))
breath_mask = rms_arr < breath_threshold
breath_windows = []
in_window = False
ws = 0.0
for i, m in enumerate(breath_mask):
    t = rms_times[i]
    if m and not in_window:
        in_window = True
        ws = t
    elif not m and in_window:
        in_window = False
        if t - ws >= 0.4:
            breath_windows.append([float(ws), float(t)])

# Strong beats: beat times that coincide with high onset strength (top 30%)
print("strong beats…", file=sys.stderr)
if onset_strengths:
    strong_threshold = float(np.percentile(onset_strengths, 70))
    strong_onset_times = [t for t, s in zip(onset_times, onset_strengths) if s >= strong_threshold]
else:
    strong_onset_times = []

strong_beats = []
for bt in beat_times:
    if any(abs(bt - ot) < 0.18 for ot in strong_onset_times):
        strong_beats.append(float(bt))

# Major impacts: top 5% onset strengths
print("major impacts…", file=sys.stderr)
if onset_strengths:
    impact_threshold = float(np.percentile(onset_strengths, 95))
    major_impacts = [float(t) for t, s in zip(onset_times, onset_strengths) if s >= impact_threshold]
else:
    major_impacts = []

# Spectral-flux peaks (swells / momentum ramps): top 10%
flux_arr = np.array(flux_vals)
flux_threshold = float(np.percentile(flux_arr, 90))
flux_peaks_times = [t for t, v in zip(flux_times, flux_vals) if v >= flux_threshold]

out = {
    "audio_file": str(AUDIO.relative_to(ROOT)),
    "duration_sec": duration,
    "sample_rate": sr,
    "tempo_bpm": tempo_val,
    "beats": beat_times,
    "strong_beats": strong_beats,
    "onsets": onset_times,
    "onset_strengths": onset_strengths,
    "major_impacts": major_impacts,
    "climax_windows": climax_windows,
    "breath_windows": breath_windows,
    "spectral_flux_peaks": flux_peaks_times,
    "rms_db_curve": list(zip(rms_times, rms_db)),
    "flux_curve": list(zip(flux_times, flux_vals)),
}

OUT.write_text(json.dumps(out, indent=2))
print(f"\nwrote {OUT.relative_to(ROOT)}", file=sys.stderr)
print(f"  tempo:           {tempo_val:.1f} BPM", file=sys.stderr)
print(f"  beats:           {len(beat_times)}", file=sys.stderr)
print(f"  strong beats:    {len(strong_beats)}", file=sys.stderr)
print(f"  onsets:          {len(onset_times)}", file=sys.stderr)
print(f"  major impacts:   {len(major_impacts)}", file=sys.stderr)
print(f"  climax windows:  {len(climax_windows)}", file=sys.stderr)
print(f"  breath windows:  {len(breath_windows)}", file=sys.stderr)
print(f"  flux peaks:      {len(flux_peaks_times)}", file=sys.stderr)
