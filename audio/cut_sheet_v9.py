"""Cut sheet v9 — story-linear, abstract-aware, no revisits.

Walks frames 1→30 in order ONCE. Variable hold per frame, matched to bar
boundaries. Abstract/hero frames get longer holds (2-4 bars); action/
transitional frames get shorter holds (half-bar to 1 bar). Lands on f30
with a held finale.

All cuts snap to madmom-detected beats from the 130 BPM grid.
"""
import json
import numpy as np
import warnings
warnings.filterwarnings("ignore")
from madmom.features.downbeats import RNNDownBeatProcessor, DBNDownBeatTrackingProcessor

ROOT = "/Users/donnysmith/Projects/Orchestrate"
audio = f"{ROOT}/audio/Beats.mp3"

print("Running madmom...")
act = RNNDownBeatProcessor()(audio)
tracker = DBNDownBeatTrackingProcessor(beats_per_bar=[3, 4], fps=100)
beats_raw = tracker(act)
beats_all = [(float(t), int(b)) for t, b in beats_raw]

KICK_START = 8.0
AUDIO_START = next(t for t, b in beats_all if t >= KICK_START and b == 1)
FILM_LEN = 60.0
AUDIO_END = AUDIO_START + FILM_LEN

window_beats = [(t - AUDIO_START, b) for t, b in beats_all if AUDIO_START <= t <= AUDIO_END + 0.5]
beat_times = [t for t, _ in window_beats]
mean_int = float(np.diff(beat_times).mean())
print(f"Start: {AUDIO_START:.3f}s · {len(window_beats)} beats in window · {60/mean_int:.2f} BPM")

# Beats per frame — story-arc-aware, abstract frames get longer holds.
# Each unit = 1 beat (0.46s at 130 BPM).
# Total should land ≈130 beats (one bar buffer either way is fine — we trim
# to the last beat before AUDIO_END).
BEATS_PER_FRAME = {
    # ──────── COSMOS / ESTABLISH ────────
    1:  8,    # earth — long abstract establish (3.7s)
    2:  3,    # zoom to facility
    # ──────── POWER GENERATION ────────
    3:  3,    # turbine coupling
    4:  8,    # combustion ring of fire — abstract (3.7s)
    5:  3,    # rotor blades spinning
    6:  3,    # rotor faster
    7:  3,    # generator interior
    8:  8,    # electromagnetic field lines — abstract (3.7s)
    9:  8,    # electricity in copper — abstract (3.7s)
    # ──────── TRANSMISSION / GRID ────────
    10: 3,    # switchyard
    11: 3,    # transformers
    12: 4,    # transmission lines
    13: 7,    # grid network aerial — abstract (3.2s)
    14: 7,    # data trails routing — abstract (3.2s)
    15: 3,    # control room
    # ──────── REGIONAL → CITY ────────
    16: 4,    # southeast US lit
    17: 3,    # cyan flow toward city
    18: 3,    # transmission into city
    19: 3,    # city lighting up
    20: 3,    # lights spreading
    21: 3,    # downtown stadium
    # ──────── STADIUM CLIMAX ────────
    22: 3,    # energy into stadium
    23: 3,    # bowl bloom
    24: 3,    # downtown synced
    # ──────── VENUE → KEYNOTE ────────
    25: 3,    # conference center exterior
    26: 3,    # atrium
    27: 3,    # keynote hall ambient
    28: 4,    # stage lights ignite
    29: 7,    # keynote pull-back — abstract (3.2s)
    30: 8,    # final stage reveal — held finale (3.7s)
}
total_beats = sum(BEATS_PER_FRAME.values())
print(f"Allocated {total_beats} beats across 30 frames (target ≈{len(window_beats)-1})")

# Snap each cumulative beat boundary to the actual madmom beat time
cuts_rel = [0.0]
acc = 0
for f in range(1, 31):
    acc += BEATS_PER_FRAME[f]
    if acc >= len(beat_times):
        cuts_rel.append(beat_times[-1])
    else:
        cuts_rel.append(beat_times[acc])

# Ensure film ends at exactly FILM_LEN
cuts_rel[-1] = FILM_LEN

# Build windows
windows = []
for i in range(30):
    s_t = cuts_rel[i]
    e_t = cuts_rel[i+1]
    windows.append({
        "frame": i + 1,
        "start_in_audio": round(s_t, 3),
        "end_in_audio": round(e_t, 3),
        "duration": round(e_t - s_t, 3),
        "abs_audio_t": round(AUDIO_START + s_t, 3),
        "beats_held": BEATS_PER_FRAME[i + 1],
    })

print(f"\n{len(windows)} cuts (audio {AUDIO_START:.2f} → {AUDIO_END:.2f}s):")
durations = []
for w in windows:
    bars = w["beats_held"] / 4
    tag = "abstract" if w["beats_held"] >= 5 else ("hold" if w["beats_held"] >= 4 else "action")
    print(f"  f{w['frame']:02d}  rel {w['start_in_audio']:5.2f}→{w['end_in_audio']:5.2f}s ({w['duration']:.2f}s · {w['beats_held']} beats / {bars:.1f} bars) {tag}")
    durations.append(w["duration"])

print()
print(f"Total: {cuts_rel[-1]-cuts_rel[0]:.2f}s · frames: 30 · mean {np.mean(durations):.2f}s · range {min(durations):.2f}-{max(durations):.2f}s")

out = {
    "audio_file": "Beats.mp3",
    "audio_start_sec": round(AUDIO_START, 3),
    "audio_end_sec": round(AUDIO_END, 3),
    "film_duration_sec": FILM_LEN,
    "phase": "story_linear_v9",
    "bpm": round(60/mean_int, 2),
    "windows": windows,
}
with open(f"{ROOT}/audio/cut_sheet.json", "w") as f:
    json.dump(out, f, indent=2)
print(f"\nWrote {ROOT}/audio/cut_sheet.json")
