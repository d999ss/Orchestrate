"""Cut sheet generator — parametric for any storyboard (SB1/SB2/SB3).

Usage:  .venv/bin/python audio/cut_sheet_sb.py <sb_num>

Produces audio/cut_sheet_sb<N>.json with the v13 structure:
- madmom RNN downbeat grid (130 BPM)
- audio starts at first kick downbeat
- variable holds: abstract/hero frames longer, action shorter
- end on the stage finale frame, with the cosmos bookend just before
"""
import json
import sys
import numpy as np
import warnings
warnings.filterwarnings("ignore")
from madmom.features.downbeats import RNNDownBeatProcessor, DBNDownBeatTrackingProcessor

ROOT = "/Users/donnysmith/Projects/Orchestrate"
audio = f"{ROOT}/audio/Beats.mp3"


# Per-storyboard frame allocation (frame number, beats held).
# Each list MUST sum to ~130 beats (one beat = 0.4615s @ 130 BPM, 60s film).
# Order matters — this is the playback sequence.

# SB1 — sum = 131 beats (matches the 131-beat 60s window)
SB1 = [
    (1,  8), (2,  4), (3,  4), (4,  8), (5,  3), (6,  3), (7,  3),
    (8,  6), (9,  7), (10, 4), (11, 4), (12, 4), (13, 6), (14, 5),
    (15, 3), (16, 4), (17, 3), (18, 3), (19, 3), (20, 3), (21, 3),
    (22, 3), (23, 4), (24, 3), (25, 3), (26, 3), (27, 6),
    (29, 5), (30, 5), (28, 8),     # cosmos bookend, then stage finale
]

# SB2 — Anatomy of a Watt. f30 is the keynote stage reveal = finale. sum = 131
SB2 = [
    (1,  8), (2,  3), (3,  3), (4,  6), (5,  4), (6,  4), (7,  4),
    (8,  7), (9,  6), (10, 3), (11, 3), (12, 5), (13, 6), (14, 5),
    (15, 3), (16, 5), (17, 4), (18, 3), (19, 3), (20, 3), (21, 3),
    (22, 3), (23, 4), (24, 3), (25, 4), (26, 4), (27, 4),
    (28, 4), (29, 5), (30, 8),     # f30 = fully-activated keynote stage = finale
]

# SB3 — Branded Matrix. f28 = stage finale, f30 (lit planet) before. sum = 131
SB3 = [
    (1,  8), (2,  3), (3,  3), (4,  4), (5,  4), (6,  4), (7,  4),
    (8,  6), (9,  6), (10, 4), (11, 4), (12, 4), (13, 6), (14, 5),
    (15, 3), (16, 5), (17, 3), (18, 3), (19, 3), (20, 3), (21, 3),
    (22, 3), (23, 4), (24, 3), (25, 4), (26, 4), (27, 5),
    (29, 5), (30, 5), (28, 8),     # cosmos bookend, then stage finale
]

SEQUENCES = {"1": SB1, "2": SB2, "3": SB3}


def build(sb_num: str):
    sequence = SEQUENCES[sb_num]
    print(f"=== SB{sb_num} cut sheet ===")

    act = RNNDownBeatProcessor()(audio)
    tracker = DBNDownBeatTrackingProcessor(beats_per_bar=[3, 4], fps=100)
    beats_raw = tracker(act)
    beats_all = [(float(t), int(b)) for t, b in beats_raw]

    KICK_START = 8.0
    AUDIO_START = next(t for t, b in beats_all if t >= KICK_START and b == 1)
    FILM_LEN = 60.0

    window_beats = [(t - AUDIO_START, b) for t, b in beats_all if AUDIO_START <= t <= AUDIO_START + FILM_LEN + 0.5]
    beat_times = [t for t, _ in window_beats]
    mean_int = float(np.diff(beat_times).mean())
    print(f"Start: {AUDIO_START:.3f}s · {len(window_beats)} beats · {60/mean_int:.2f} BPM")
    total = sum(b for _, b in sequence)
    print(f"{len(sequence)} frames · {total} beats allocated · window has {len(window_beats)-1}")

    cuts_rel = [0.0]
    acc = 0
    for _, beats in sequence:
        acc += beats
        if acc >= len(beat_times):
            cuts_rel.append(beat_times[-1])
        else:
            cuts_rel.append(beat_times[acc])
    cuts_rel[-1] = FILM_LEN

    windows = []
    for i, (frame, beats) in enumerate(sequence):
        s_t = cuts_rel[i]
        e_t = cuts_rel[i+1]
        windows.append({
            "frame": frame,
            "start_in_audio": round(s_t, 3),
            "end_in_audio": round(e_t, 3),
            "duration": round(e_t - s_t, 3),
            "abs_audio_t": round(AUDIO_START + s_t, 3),
            "beats_held": beats,
        })

    durations = []
    for w in windows:
        bars = w["beats_held"] / 4
        tag = "abstract" if w["beats_held"] >= 7 else ("hold" if w["beats_held"] >= 5 else "action")
        marker = "  ★" if w is windows[-1] else ""
        print(f"  f{w['frame']:02d}  {w['start_in_audio']:5.2f}→{w['end_in_audio']:5.2f}s ({w['duration']:.2f}s · {w['beats_held']}b/{bars:.1f}bars) {tag}{marker}")
        durations.append(w["duration"])

    print(f"Total: {cuts_rel[-1]-cuts_rel[0]:.2f}s · mean {np.mean(durations):.2f}s · range {min(durations):.2f}-{max(durations):.2f}s")

    out = {
        "audio_file": "Beats.mp3",
        "audio_start_sec": round(AUDIO_START, 3),
        "audio_end_sec": round(AUDIO_START + FILM_LEN, 3),
        "film_duration_sec": FILM_LEN,
        "phase": f"sb{sb_num}_v13",
        "bpm": round(60/mean_int, 2),
        "storyboard": sb_num,
        "windows": windows,
    }
    out_path = f"{ROOT}/audio/cut_sheet_sb{sb_num}.json"
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"Wrote {out_path}")
    return out_path


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "2"
    if target == "all":
        for n in ("1", "2", "3"):
            build(n)
            print()
    else:
        build(target)
