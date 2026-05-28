"""Cut sheet v6 — DENSE. ~55 cuts in 60s, no clip > 3s, drop is rapid-fire.

Strategy:
- Total cuts: ~55 (avg ~1.1s)
- Intro (0 → 8.98s): 4 cuts (frame 1 holds 2.5s, then 3 more leading into beat-1)
- Verse (8.98 → 36.78s): ~22 cuts at ~1.2s avg
- Drop+Climax (36.78 → 60.0s): ~29 cuts, mostly 0.5-0.9s rapid-fire

All 30 unique frames used. Some frames appear 2x (story callbacks at impact moments).
Every cut still snaps to a real audio onset (HPSS-isolated kick + melodic + beat grid).
"""
import sys, json
import numpy as np
import librosa

ROOT = "/Users/donnysmith/Projects/Orchestrate"
audio = f"{ROOT}/audio/Beats.mp3"

y, sr = librosa.load(audio, sr=None, mono=True)
duration = float(librosa.get_duration(y=y, sr=sr))
hop = 256

y_h, y_p = librosa.effects.hpss(y, margin=4)
onset_env_p = librosa.onset.onset_strength(y=y_p, sr=sr, hop_length=hop)
onset_env_full = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
frame_times = librosa.frames_to_time(np.arange(len(onset_env_p)), sr=sr, hop_length=hop)

p_onsets = librosa.onset.onset_detect(
    onset_envelope=onset_env_p, sr=sr, hop_length=hop, units="time",
    delta=0.10, wait=3,
)
full_onsets = librosa.onset.onset_detect(
    onset_envelope=onset_env_full, sr=sr, hop_length=hop, units="time",
    delta=0.08, wait=2,
)
tempo, beats = librosa.beat.beat_track(y=y, sr=sr, units="time")

def s_at(t, env):
    idx = int(np.argmin(np.abs(frame_times - t)))
    lo, hi = max(0, idx-2), min(len(env), idx+3)
    return float(env[lo:hi].max())

# Snap candidates in 0-60s window
FILM_END = 60.0
candidates = sorted(set(
    [round(float(t), 4) for t in p_onsets if 0 <= t <= FILM_END] +
    [round(float(t), 4) for t in full_onsets if 0 <= t <= FILM_END] +
    [round(float(t), 4) for t in beats if 0 <= t <= FILM_END]
))

# Song landmarks
FIRST_BEAT = 8.98
SECTION_2 = 36.78        # drop entry

# Phase targets — total ~55 cuts, weighted toward the drop
PHASES = [
    # Cut throughout the silent intro too — don't wait for the downbeat
    (0.0, FIRST_BEAT, 6),            # 6 cuts in 9s intro ≈ 1.5s avg
    (FIRST_BEAT, SECTION_2, 22),     # verse: 22 cuts in ~28s ≈ 1.27s avg
    (SECTION_2, FILM_END, 32),       # drop: 32 cuts in ~23s ≈ 0.72s avg
]
TARGET = sum(n for _, _, n in PHASES)
print(f"Target cuts: {TARGET}")

MIN_DT_NORMAL = 0.35
MIN_DT_DROP = 0.30      # allow tighter during the drop

def pick_phase_cuts(phase_start, phase_end, n, used, min_dt):
    """n evenly-spaced cuts in [phase_start, phase_end].
    Each anchor snaps to nearest unique candidate. If none, use the anchor itself.
    Guarantees min_dt spacing between picks within this phase and against used.
    """
    if n == 0:
        return []
    span = phase_end - phase_start
    local_cands = [c for c in candidates if phase_start - 0.01 <= c <= phase_end + 0.01]
    # Evenly-spaced target times across the phase
    anchors = [phase_start + (i + 1) * span / n for i in range(n)]
    chosen = []
    picked_so_far = list(used)
    for a in anchors:
        # 1) Snap to nearest unused candidate within ±0.4s of anchor
        nearby = sorted([c for c in local_cands if abs(c - a) < 0.4 and c not in picked_so_far],
                        key=lambda c: abs(c - a))
        picked = None
        for c in nearby:
            if all(abs(c - x) >= min_dt for x in picked_so_far):
                picked = c
                break
        # 2) Fallback: use the anchor time itself (forces a cut even in silent regions)
        if picked is None:
            picked = a
            # Nudge if too close to prior picks
            while any(abs(picked - x) < min_dt for x in picked_so_far) and picked < phase_end - 0.05:
                picked += min_dt
        chosen.append(picked)
        picked_so_far.append(picked)
    return chosen


cuts = [0.0]
used = [0.0]
for phase_start, phase_end, n in PHASES:
    is_drop = phase_start >= SECTION_2 - 0.5
    min_dt = MIN_DT_DROP if is_drop else MIN_DT_NORMAL
    picks = pick_phase_cuts(phase_start, phase_end, n, used, min_dt)
    cuts.extend(picks)
    used.extend(picks)

# Ensure we hit exactly TARGET+1 cut points
while len(cuts) > TARGET + 1:
    interior = [(i, s_at(cuts[i], onset_env_p)) for i in range(1, len(cuts)-1)]
    weakest = min(interior, key=lambda x: x[1])[0]
    cuts.pop(weakest)
while len(cuts) < TARGET + 1:
    gaps = [(cuts[i+1] - cuts[i], i) for i in range(len(cuts)-1)]
    gaps.sort(reverse=True)
    i = gaps[0][1]
    mid = (cuts[i] + cuts[i+1]) / 2
    local = [c for c in candidates if cuts[i] + 0.3 < c < cuts[i+1] - 0.3 and c not in cuts]
    if local:
        local.sort(key=lambda c: abs(c - mid))
        cuts.insert(i+1, local[0])
    else:
        break

cuts.sort()
cuts[-1] = FILM_END

# Sanity: dedupe near-collisions (anything within 0.10s of prior)
deduped = [cuts[0]]
for c in cuts[1:]:
    if c - deduped[-1] >= 0.10:
        deduped.append(c)
cuts = deduped

# Map cuts to story frames. 30 unique frames, ~55 cuts → some frames appear ~2x.
# Story rhythm:
#   Phase A (intro) → frame 1 only
#   Phase B (verse) → frames 2-12 in order (one each, plus 11 extras filled by revisits)
#   Phase C (drop) → frames 13-30 in order (one each, plus 11 extras for impact)
# Strategy: walk frames 1..30 in story order; when we run out, revisit the most
# impactful frames again (1, 5, 9, 13, 17, 21, 25, 29 — the keyframes that benefit
# from a callback).

N_WINDOWS = len(cuts) - 1
unique_frames = list(range(1, 31))
revisit_pool = [1, 5, 9, 13, 17, 21, 25, 29, 4, 8, 17, 21, 29, 30]
revisits_needed = N_WINDOWS - 30
sequence = list(unique_frames)
ri = 0
# Inject revisits at impactful moments: distribute across the drop section
drop_start_window = next((i for i, c in enumerate(cuts[:-1]) if c >= SECTION_2), len(cuts) - 2)
inject_positions = sorted(np.linspace(drop_start_window + 2, N_WINDOWS - 2, revisits_needed).astype(int).tolist())
for p in inject_positions:
    if ri < len(revisit_pool):
        sequence.insert(p, revisit_pool[ri])
        ri += 1
# Trim/pad to exact N_WINDOWS
sequence = sequence[:N_WINDOWS]
while len(sequence) < N_WINDOWS:
    sequence.append(revisit_pool[ri % len(revisit_pool)])
    ri += 1

# Build windows
windows = []
for i in range(N_WINDOWS):
    s_t = cuts[i]
    e_t = cuts[i+1]
    windows.append({
        "frame": sequence[i],
        "start_in_audio": round(s_t, 3),
        "end_in_audio": round(e_t, 3),
        "duration": round(e_t - s_t, 3),
        "onset_strength": round(s_at(s_t, onset_env_p), 2),
    })

print(f"\n{len(windows)} cuts (audio 0 → {FILM_END}s):")
durations = []
for i, w in enumerate(windows):
    t = w["start_in_audio"]
    phase = "INTRO" if t < FIRST_BEAT else ("VERSE" if t < SECTION_2 else "DROP")
    bar = "▓" * min(int(w["onset_strength"] * 3), 22)
    print(f"  {i+1:2d}  f{w['frame']:02d}  {t:6.2f}→{w['end_in_audio']:6.2f}s ({w['duration']:.2f}s) [{phase[:5]}]  {bar}")
    durations.append(w["duration"])

print()
print(f"Total: {cuts[-1]-cuts[0]:.2f}s · cuts: {len(windows)} · mean {np.mean(durations):.2f}s · range {min(durations):.2f}-{max(durations):.2f}s")

out = {
    "audio_file": "Beats.mp3",
    "audio_start_sec": 0.0,
    "audio_end_sec": FILM_END,
    "film_duration_sec": FILM_END,
    "phase": "dense_v6",
    "windows": windows,
}
with open(f"{ROOT}/audio/cut_sheet.json", "w") as f:
    json.dump(out, f, indent=2)
print(f"\nWrote {ROOT}/audio/cut_sheet.json")
