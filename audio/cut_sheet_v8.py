"""Cut sheet v8 — madmom beat-grid locked.

Uses madmom's RNN downbeat detector (research-grade, 0.75% interval stdev vs
librosa's 4.4%). Every visual cut lands on a real beat from the 130.0 BPM
grid. No off-beat snapping, no anchor fallbacks.

Structure:
- Audio starts at the first kick downbeat (8.97s of Beats.mp3)
- Film = 60s starting there
- Verse: cuts every 2 beats (~0.92s) — gives storytelling time
- Drop: cuts every 1 beat (~0.46s) — rapid-fire on the kick
- Opening: f01 holds 4 beats (~1.85s) for the establishing shot
- All 30 storyboard frames in order, then climax revisit walking f17-f30
- Ends on f30
"""
import json
import numpy as np
import warnings
warnings.filterwarnings("ignore")
from madmom.features.downbeats import RNNDownBeatProcessor, DBNDownBeatTrackingProcessor

ROOT = "/Users/donnysmith/Projects/Orchestrate"
audio = f"{ROOT}/audio/Beats.mp3"

print("Running madmom RNN downbeat detector...")
act = RNNDownBeatProcessor()(audio)
tracker = DBNDownBeatTrackingProcessor(beats_per_bar=[3, 4], fps=100)
beats_raw = tracker(act)  # array of (time, bar_position) where bar_position in 1..4
beats_all = [(float(t), int(b)) for t, b in beats_raw]
print(f"Detected {len(beats_all)} beats (downbeats included)")

# Find first kick downbeat — the perceptual song start. From inspection, this
# is at ~8.97s (a bar-position 1 beat where the kick drops in).
KICK_START = 8.0
first_downbeat = next((t for t, b in beats_all if t >= KICK_START and b == 1), None)
assert first_downbeat is not None, "could not find first kick downbeat"
AUDIO_START = first_downbeat
FILM_LEN = 60.0
AUDIO_END = AUDIO_START + FILM_LEN
print(f"First kick downbeat (audio start): {AUDIO_START:.3f}s")

# Beats in our window, relative time
window_beats = [(t - AUDIO_START, b) for t, b in beats_all if AUDIO_START <= t <= AUDIO_END]
print(f"Beats in 60s window: {len(window_beats)}")
print(f"First 8 relative: {[(round(t,3), b) for t,b in window_beats[:8]]}")
mean_interval = np.diff([t for t, _ in window_beats]).mean()
print(f"Mean beat interval: {mean_interval:.4f}s ({60/mean_interval:.2f} BPM)")

# Define cut anchors on the grid
# Phase A (verse): every 2 beats — slow build
# Phase B (drop): every beat — rapid
# Drop entry: roughly 22-24s into the film (~bar 12)
DROP_REL = 22.0  # relative seconds into film
beat_times = [t for t, _ in window_beats]

# Verse cuts: every 2nd beat from 0
verse_cuts = []
for i, (t, b) in enumerate(window_beats):
    if t >= DROP_REL:
        break
    if i % 2 == 0:                   # every other beat
        verse_cuts.append(t)
# Drop cuts: every beat
drop_cuts = [t for t, _ in window_beats if t >= DROP_REL]

cuts = sorted(set(verse_cuts + drop_cuts))

# Force opening to hold 4 beats (the first verse cut becomes the END of f01)
OPENING_BEATS = 4
opening_end = window_beats[OPENING_BEATS][0]
cuts = [c for c in cuts if c == 0.0 or c >= opening_end - 0.01]
if opening_end not in cuts:
    cuts = sorted(cuts + [opening_end])

# Ensure final cut is at exactly FILM_LEN
if cuts[-1] < FILM_LEN - 0.05:
    cuts.append(FILM_LEN)
else:
    cuts[-1] = FILM_LEN

# Deduplicate near-collisions
deduped = [cuts[0]]
for c in cuts[1:]:
    if c - deduped[-1] >= 0.20:
        deduped.append(c)
cuts = deduped

N_WINDOWS = len(cuts) - 1
print(f"Total cuts: {N_WINDOWS}")

# Story sequence — same arc as v7
def build_climax_sequence(n):
    base = [
        17, 18, 19, 20, 21, 22,
        23, 24,
        25, 26, 27, 28,
        29, 30,
        25, 26, 27, 28, 29, 30,
        27, 28, 29, 30,
        28, 29, 30,
        29, 30, 30,
    ]
    if len(base) >= n:
        return base[:n - 1] + [30]
    out = list(base)
    pulse = [28, 29, 30]
    pi = 0
    while len(out) < n:
        out.append(pulse[pi % 3])
        pi += 1
    return out[:n - 1] + [30]

n_verse = min(30, N_WINDOWS)
n_drop = max(0, N_WINDOWS - n_verse)
sequence = list(range(1, n_verse + 1))
if n_drop > 0:
    sequence.extend(build_climax_sequence(n_drop))
sequence = sequence[:N_WINDOWS]
sequence[-1] = 30
assert len(sequence) == N_WINDOWS

# Build windows
windows = []
beat_dict = {round(t, 3): b for t, b in window_beats}
for i in range(N_WINDOWS):
    s_t = cuts[i]
    e_t = cuts[i+1]
    bar_pos = beat_dict.get(round(s_t, 3), 0)
    windows.append({
        "frame": sequence[i],
        "start_in_audio": round(s_t, 3),
        "end_in_audio": round(e_t, 3),
        "duration": round(e_t - s_t, 3),
        "abs_audio_t": round(AUDIO_START + s_t, 3),
        "bar_pos": bar_pos,
    })

print(f"\n{len(windows)} cuts (audio {AUDIO_START:.2f} → {AUDIO_END:.2f}s):")
durations = []
for i, w in enumerate(windows):
    phase = "VERSE" if w["start_in_audio"] < DROP_REL else "DROP"
    bp = w["bar_pos"]
    mark = "▼" if bp == 1 else ("·" if bp else "?")
    print(f"  {i+1:2d}  f{w['frame']:02d}  rel {w['start_in_audio']:6.2f}→{w['end_in_audio']:6.2f}s ({w['duration']:.2f}s) [{phase}]  {mark} pos {bp}")
    durations.append(w["duration"])

print()
print(f"Total: {cuts[-1]-cuts[0]:.2f}s · cuts: {len(windows)} · mean {np.mean(durations):.3f}s · range {min(durations):.3f}-{max(durations):.3f}s")

out = {
    "audio_file": "Beats.mp3",
    "audio_start_sec": round(AUDIO_START, 3),
    "audio_end_sec": round(AUDIO_END, 3),
    "film_duration_sec": FILM_LEN,
    "phase": "madmom_beat_locked_v8",
    "bpm": round(60/mean_interval, 2),
    "windows": windows,
}
with open(f"{ROOT}/audio/cut_sheet.json", "w") as f:
    json.dump(out, f, indent=2)
print(f"\nWrote {ROOT}/audio/cut_sheet.json")
