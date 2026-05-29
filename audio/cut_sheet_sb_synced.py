"""SB2 / SB3 motion-synced cut sheet.

Goal: 30 frames, every cut lands on a real kick (or strong bass note),
not on a math BPM-grid position. Same detection stack as SB1 v23.

Usage:
    python3 audio/cut_sheet_sb_synced.py 2
    python3 audio/cut_sheet_sb_synced.py 3
"""
import json, pathlib, sys
import numpy as np
import scipy.signal
import librosa
import warnings
warnings.filterwarnings("ignore")

ROOT = pathlib.Path("/Users/donnysmith/Projects/Orchestrate")
BASS = pathlib.Path("/tmp/demucs_4stem/htdemucs/Beats/bass.wav")
DRUMS = pathlib.Path("/tmp/demucs_4stem/htdemucs/Beats/drums.wav")

# Audio window inside Beats.mp3 used for the body. Same as the existing
# unsynced sheet -- this is the musical phrase the film maps onto.
AUDIO_START = 8.97
FILM_LEN = 60.0
SR = 22050

# Each cut is held for at least this many seconds before the next cut.
# Prevents one-frame flashes when kicks land very close.
MIN_HOLD = 0.6


def detect_kicks(stem_path: pathlib.Path, audio_start: float, audio_len: float):
    """Return kick onset times (seconds, relative to audio_start) inside the window."""
    y, sr = librosa.load(stem_path, sr=SR, offset=audio_start, duration=audio_len)
    # Onset envelope emphasising sub-bass / kick energy
    onset_env = librosa.onset.onset_strength(
        y=y, sr=sr, fmax=200, lag=2, max_size=3
    )
    # Pick peaks. Tuned to the 130-BPM kick pattern in Beats.mp3.
    onsets = librosa.onset.onset_detect(
        onset_envelope=onset_env, sr=sr, hop_length=512,
        wait=8, pre_avg=8, post_avg=8, pre_max=4, post_max=4, delta=0.4,
        units="time", backtrack=True,
    )
    return onsets.tolist()


def merge_anchors(kicks, bass_notes):
    """Union of kicks + bass notes, sorted and deduped at <80ms resolution."""
    all_anchors = sorted(kicks + bass_notes)
    merged = []
    for t in all_anchors:
        if not merged or t - merged[-1] > 0.08:
            merged.append(t)
    return merged


def pick_cuts(anchors, n_cuts: int, film_len: float, min_hold: float):
    """Choose n_cuts cut START times from anchors so they tile film_len evenly.

    First pick is ALWAYS 0 — f01 plays as the lead-in bar before the first
    kick. This mirrors SB1 v23, where the first frame holds while the music
    builds, and the first detected kick lands on the cut to f02. Without this
    the body ends short of film_len and the audio fade-out gets truncated.

    Remaining (n_cuts-1) picks: target start times at i * film_len/n_cuts for
    i=1..n_cuts-1, snap each to the closest forward anchor.
    """
    if not anchors:
        raise SystemExit("no kick anchors detected -- bad audio split?")
    # f01 lead-in always starts at 0
    picks = [0.0]
    prev = 0.0
    targets = [i * film_len / n_cuts for i in range(1, n_cuts)]
    for t in targets:
        candidates = [a for a in anchors if a >= prev + min_hold]
        if not candidates:
            break
        best = min(candidates, key=lambda a: abs(a - t))
        picks.append(best)
        prev = best
    return picks


def build_windows(picks, film_len: float, n_frames: int):
    """Convert pick times into window dicts compatible with assemble_sb.sh."""
    windows = []
    for i, t in enumerate(picks):
        end_t = picks[i + 1] if i + 1 < len(picks) else film_len
        windows.append({
            "frame": i + 1,
            "start_in_audio": round(t, 3),
            "end_in_audio": round(end_t, 3),
            "duration": round(end_t - t, 3),
            "abs_audio_t": round(AUDIO_START + t, 3),
        })
    return windows


def main():
    sb = sys.argv[1] if len(sys.argv) > 1 else "2"
    assert sb in ("2", "3"), "sb must be 2 or 3"
    n_frames = 30

    print(f"Detecting kicks/bass for SB{sb}...")
    kicks = detect_kicks(DRUMS, AUDIO_START, FILM_LEN)
    bass = detect_kicks(BASS, AUDIO_START, FILM_LEN)
    print(f"  drums onsets: {len(kicks)}")
    print(f"  bass  onsets: {len(bass)}")
    anchors = merge_anchors(kicks, bass)
    print(f"  merged anchors: {len(anchors)}")

    if len(anchors) < n_frames:
        print(f"WARNING: only {len(anchors)} anchors but need {n_frames} cuts. "
              f"Some cuts will share or get extended.")

    picks = pick_cuts(anchors, n_frames, FILM_LEN, MIN_HOLD)
    print(f"  picked {len(picks)} cut starts")

    windows = build_windows(picks, FILM_LEN, n_frames)

    sheet = {
        "audio_file": "Beats.mp3",
        "audio_start_sec": AUDIO_START,
        "audio_end_sec": AUDIO_START + FILM_LEN,
        "film_duration_sec": FILM_LEN,
        "phase": f"sb{sb}_synced_v1",
        "bpm": 129.98,
        "storyboard": sb,
        "windows": windows,
    }

    out = ROOT / "audio" / f"cut_sheet_sb{sb}.json"
    out.write_text(json.dumps(sheet, indent=2))
    print(f"\nwrote {out}")

    print("\n=== Cut anchors (abs audio time) ===")
    for w in windows:
        beats_since_start = (w["start_in_audio"] / (60 / 129.98))
        print(f"  f{w['frame']:02d}  {w['duration']:5.2f}s  @ {w['abs_audio_t']:6.2f}s  (~{beats_since_start:5.1f} beats in)")


if __name__ == "__main__":
    main()
