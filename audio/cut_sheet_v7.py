"""Cut sheet v7 — onset-locked. Audio starts at the first downbeat, NOT 0:00.
No silent intro. Every cut snaps to a real percussive/full onset.

Strategy:
- audio_start_sec = first beat (~8.98s into Beats.mp3)
- Film = 60s starting there
- 45 cuts, all picked from real onsets with measurable strength
- Phase A (relative 0-22s, verse): ~18 cuts at ~1.2s avg
- Phase B (relative 22-60s, drop+climax): ~27 cuts at ~0.7-1.4s avg
- All 30 unique frames + 15 revisits at impact moments
"""
import sys, json
import numpy as np
import librosa

ROOT = "/Users/donnysmith/Projects/Orchestrate"
audio = f"{ROOT}/audio/Beats.mp3"

y, sr = librosa.load(audio, sr=None, mono=True)
hop = 256
y_h, y_p = librosa.effects.hpss(y, margin=4)
env_p = librosa.onset.onset_strength(y=y_p, sr=sr, hop_length=hop)
env_f = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
ft = librosa.frames_to_time(np.arange(len(env_p)), sr=sr, hop_length=hop)

p_on = librosa.onset.onset_detect(onset_envelope=env_p, sr=sr, hop_length=hop,
                                   units="time", delta=0.10, wait=3)
f_on = librosa.onset.onset_detect(onset_envelope=env_f, sr=sr, hop_length=hop,
                                   units="time", delta=0.08, wait=2)
tempo, beats = librosa.beat.beat_track(y=y, sr=sr, units="time")

AUDIO_START = float(beats[0])    # 8.981s — skip the silent intro
FILM_LEN = 60.0
AUDIO_END = AUDIO_START + FILM_LEN

def s_at(t, env):
    idx = int(np.argmin(np.abs(ft - t)))
    lo, hi = max(0, idx-2), min(len(env), idx+3)
    return float(env[lo:hi].max())

# Merge percussive + full + beat candidates in window
cand = sorted(set(
    [round(float(t), 4) for t in p_on if AUDIO_START <= t <= AUDIO_END] +
    [round(float(t), 4) for t in f_on if AUDIO_START <= t <= AUDIO_END] +
    [round(float(t), 4) for t in beats if AUDIO_START <= t <= AUDIO_END]
))

# Score each candidate (max of percussive + full envelope strength)
scored = [(t, max(s_at(t, env_p), s_at(t, env_f))) for t in cand]
# Drop weakest (anything below threshold)
scored = [(t, s) for t, s in scored if s >= 1.5]
print(f"Strong candidates in window: {len(scored)}")

# Phase split in absolute audio time
DROP_ABS = AUDIO_START + 22.0    # drop entry ~31s of audio
PHASE_A_TARGET = 18              # verse: 22s, ~1.22s avg
PHASE_B_TARGET = 27              # drop+climax: 38s, ~1.4s → tightening to ~0.7s
TARGET = PHASE_A_TARGET + PHASE_B_TARGET   # 45 cuts → 46 cut points

MIN_DT_VERSE = 0.50
MIN_DT_DROP = 0.30

def pick_cuts(scored_in_phase, target, min_dt, prev_used):
    """Greedy: sort by strength desc, take strongest non-overlapping, then
    backfill from remaining with min_dt spacing against ALL picks."""
    used = list(prev_used)
    picks = []
    # Pass 1: strongest hits
    for t, s in sorted(scored_in_phase, key=lambda x: -x[1]):
        if all(abs(t - x) >= min_dt for x in used + picks):
            picks.append(t)
            if len(picks) >= target:
                break
    # Pass 2: if short, fill gaps with weaker onsets
    if len(picks) < target:
        for t, s in sorted(scored_in_phase, key=lambda x: -x[1]):
            if t in picks:
                continue
            if all(abs(t - x) >= min_dt for x in used + picks):
                picks.append(t)
                if len(picks) >= target:
                    break
    return sorted(picks)

phase_a_scored = [(t, s) for t, s in scored if AUDIO_START <= t < DROP_ABS]
phase_b_scored = [(t, s) for t, s in scored if DROP_ABS <= t <= AUDIO_END]

# Force first cut at AUDIO_START itself (the downbeat)
cuts_abs = [AUDIO_START]
# Opening earth hold: snap to the strongest hit between 1.8s and 2.6s after
# the downbeat, and EXCLUDE everything earlier so no verse cut can land
# inside the establishing-shot window.
OPENING_MIN = 1.8
OPENING_MAX = 2.6
opening_cands = [(t, s) for t, s in scored if AUDIO_START + OPENING_MIN <= t <= AUDIO_START + OPENING_MAX]
opening_pick = None
if opening_cands:
    opening_pick = max(opening_cands, key=lambda x: x[1])[0]
    cuts_abs.append(opening_pick)
    print(f"Opening hold: f01 runs 0 → {opening_pick - AUDIO_START:.2f}s (locked to strongest hit in [{OPENING_MIN},{OPENING_MAX}]s)")

# Filter phase_a candidates: drop anything inside the opening-hold window
opening_floor = opening_pick if opening_pick is not None else AUDIO_START
phase_a_scored = [(t, s) for t, s in scored if opening_floor <= t < DROP_ABS]
phase_b_scored = [(t, s) for t, s in scored if DROP_ABS <= t <= AUDIO_END]

picks_a = pick_cuts(phase_a_scored, PHASE_A_TARGET, MIN_DT_VERSE, cuts_abs)
cuts_abs.extend(picks_a)
picks_b = pick_cuts(phase_b_scored, PHASE_B_TARGET, MIN_DT_DROP, cuts_abs)
cuts_abs.extend(picks_b)
cuts_abs = sorted(set(cuts_abs))
# Make sure film ends at AUDIO_END
if cuts_abs[-1] < AUDIO_END - 0.1:
    cuts_abs.append(AUDIO_END)
else:
    cuts_abs[-1] = AUDIO_END

# Convert to relative time (0 = start of film)
cuts = [t - AUDIO_START for t in cuts_abs]
N_WINDOWS = len(cuts) - 1

# Cap any window over 3.0s by inserting the next strongest onset in the gap
def enforce_max_hold(cuts_rel, cuts_abs_local, max_hold=3.0):
    out_rel = list(cuts_rel)
    out_abs = list(cuts_abs_local)
    while True:
        worst_i = None
        worst_d = 0
        for i in range(len(out_rel) - 1):
            d = out_rel[i+1] - out_rel[i]
            if d > max_hold and d > worst_d:
                worst_d = d
                worst_i = i
        if worst_i is None:
            break
        # Find any strong candidate inside this gap
        lo, hi = out_abs[worst_i] + 0.3, out_abs[worst_i+1] - 0.3
        gap_cands = [(t, s) for t, s in scored if lo < t < hi and t not in out_abs]
        if not gap_cands:
            break
        t, s = max(gap_cands, key=lambda x: x[1])
        out_abs.insert(worst_i + 1, t)
        out_rel.insert(worst_i + 1, t - AUDIO_START)
    return out_rel, out_abs

cuts, cuts_abs = enforce_max_hold(cuts, cuts_abs, max_hold=2.7)
N_WINDOWS = len(cuts) - 1

# Story sequence — STORYBOARD-1 NARRATIVE ARC, NOT RANDOM REVISITS.
#
# Storyboard 1 tells one continuous story:
#   1-2    cosmos / earth (establishing)
#   3-9    power generation (turbine, combustion, generator, electromagnetic)
#   10-13  transmission / grid network
#   14-17  regional grid concentrating toward Atlanta
#   18-22  city lights activating / downtown
#   23-24  stadium climax
#   25-28  conference center → keynote interior
#   29-30  keynote stage reveal (final payoff)
#
# Structure:
#   Pass 1 (verse, ~30 windows): walk frames 1→30 in story order, ONE EACH
#   Pass 2 (drop): climactic montage walking the city→stage payoff (frames
#                  17-30) in order, with the keynote reveal (28/29/30)
#                  hammered repeatedly at the climax. Always lands on f30.

def build_climax_sequence(n):
    """Return n frame numbers for the drop climax, ending on f30.
    Walks frames 17-30 in story order with intentional repetition on the
    payoff (28, 29, 30)."""
    base = [
        # City activation pass (rapid story beats)
        17, 18, 19, 20, 21, 22,
        # Stadium climax
        23, 24,
        # Conference center → keynote interior
        25, 26, 27, 28,
        # Stage reveal first hit
        29, 30,
        # Encore: re-hit the climactic beats
        25, 26, 27, 28, 29, 30,
        # Encore 2: focus on the venue + stage
        27, 28, 29, 30,
        # Encore 3: drive the keynote home
        28, 29, 30,
        # Final pulse: hold the reveal
        29, 30, 30,
    ]
    # Trim or extend by repeating the final pulse
    if len(base) >= n:
        return base[:n - 1] + [30]   # always end on f30
    out = list(base)
    pulse = [28, 29, 30]
    pi = 0
    while len(out) < n:
        out.append(pulse[pi % 3])
        pi += 1
    return out[:n - 1] + [30]

n_verse = min(30, N_WINDOWS)             # first 30 cuts walk frames 1-30 in order
n_drop = max(0, N_WINDOWS - n_verse)
sequence = list(range(1, n_verse + 1))
if n_drop > 0:
    sequence.extend(build_climax_sequence(n_drop))

# If we have fewer than 30 windows total, still end on f30
sequence[-1] = 30
assert len(sequence) == N_WINDOWS

# Build windows
windows = []
for i in range(N_WINDOWS):
    s_t = cuts[i]
    e_t = cuts[i+1]
    abs_t = cuts_abs[i]
    windows.append({
        "frame": sequence[i],
        "start_in_audio": round(s_t, 3),
        "end_in_audio": round(e_t, 3),
        "duration": round(e_t - s_t, 3),
        "abs_audio_t": round(abs_t, 3),
        "onset_strength": round(max(s_at(abs_t, env_p), s_at(abs_t, env_f)), 2),
    })

print(f"\n{len(windows)} cuts (audio {AUDIO_START:.2f} → {AUDIO_END:.2f}s):")
durations = []
weak = 0
for i, w in enumerate(windows):
    phase = "VERSE" if w["abs_audio_t"] < DROP_ABS else "DROP"
    bar = "▓" * min(int(w["onset_strength"] * 2), 22)
    print(f"  {i+1:2d}  f{w['frame']:02d}  rel {w['start_in_audio']:6.2f}→{w['end_in_audio']:6.2f}s ({w['duration']:.2f}s) [{phase}]  hit={w['onset_strength']:.1f}  {bar}")
    durations.append(w["duration"])
    if w["onset_strength"] < 2.0:
        weak += 1

print()
print(f"Total: {cuts[-1]-cuts[0]:.2f}s · cuts: {len(windows)} · mean {np.mean(durations):.2f}s · range {min(durations):.2f}-{max(durations):.2f}s")
print(f"Weak cuts (< 2.0 onset strength): {weak}")

out = {
    "audio_file": "Beats.mp3",
    "audio_start_sec": round(AUDIO_START, 3),
    "audio_end_sec": round(AUDIO_END, 3),
    "film_duration_sec": FILM_LEN,
    "phase": "onset_locked_v7",
    "first_beat_abs": round(AUDIO_START, 3),
    "windows": windows,
}
with open(f"{ROOT}/audio/cut_sheet.json", "w") as f:
    json.dump(out, f, indent=2)
print(f"\nWrote {ROOT}/audio/cut_sheet.json")
