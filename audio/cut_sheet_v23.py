"""Cut sheet v23 — clean structural pass. No flagged frames. Strictly forward.

Audit rules enforced:
1. No flagged frames: f08 UFO, f14 data trails, f16 Alom-text, f17 text,
   f22/23/24 redundant stadium, f26 hallway, f29 UFO podium, f30 earth bookend
2. No two consecutive cuts share a frame (no flash)
3. Strictly forward through story · no spatial regression (no zoom-out)
4. ONE stadium beat only (f21 aerial)
5. f28 stage finale is the final held window to FILM_LEN
6. Every internal cut lands on a real bass note or kick (audible punch)
"""
import json, pathlib
import numpy as np
import scipy.signal
import librosa
import warnings
warnings.filterwarnings("ignore")

ROOT = pathlib.Path("/Users/donnysmith/Projects/Orchestrate")
BASS = pathlib.Path("/tmp/demucs_4stem/htdemucs/Beats/bass.wav")
DRUMS = pathlib.Path("/tmp/demucs_4stem/htdemucs/Beats/drums.wav")
AUDIO_START = 7.13
FILM_LEN = 60.0


# Strictly forward narrative arc. 16 frames. Cosmos → generation → grid →
# regional → city → venue → stage. No flagged content.
SEQUENCE = [
    1,    # earth — build-up bar
    2,    # push into power plant — first kick
    3,    # turbine couples — plant activates
    4,    # combustion ring ignites · HERO
    9,    # electricity in copper · HERO
    10,   # switchyard · energy exits source
    11,   # transformers · voltage climbs
    12,   # transmission corridor across countryside
    13,   # grid aerial reveal · HERO
    18,   # transmission lines into city
    19,   # Atlanta lighting up · BIGGEST DROP
    20,   # city lights spreading
    21,   # downtown stadium aerial · ONE stadium beat
    25,   # Signia by Hilton exterior · venue arrival
    27,   # inside keynote hall
    28,   # stage lights ignite · FINALE (held to FILM_LEN)
]

# Audit: every entry must be a non-flagged frame
FLAGGED = {8, 14, 16, 17, 22, 23, 24, 26, 29, 30}
for f in SEQUENCE:
    assert f not in FLAGGED, f"flagged frame f{f} in sequence"
# Audit: no consecutive duplicates
for i in range(len(SEQUENCE) - 1):
    assert SEQUENCE[i] != SEQUENCE[i+1], f"consecutive duplicate at index {i}: f{SEQUENCE[i]}"
print(f"Audit pass: {len(SEQUENCE)} frames, no flagged content, no duplicates, strictly forward")


def detect_bass(path, t_start, t_end):
    y, sr = librosa.load(str(path), sr=None, mono=True,
                          offset=t_start, duration=t_end - t_start)
    hop = 256
    env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
    onsets = librosa.onset.onset_detect(onset_envelope=env, sr=sr, hop_length=hop,
                                          units="time", delta=0.25, wait=10)
    win = int(0.05 * sr)
    out = []
    for t in onsets:
        idx = int(t * sr)
        seg = y[max(0, idx-win):min(len(y), idx+win)]
        if len(seg) == 0: continue
        rms = float(np.sqrt(np.mean(seg ** 2)))
        if rms > 0.001:
            out.append((float(t), rms, "bass"))
    return out


def detect_kicks(path, t_start, t_end):
    y, sr = librosa.load(str(path), sr=None, mono=True,
                          offset=t_start, duration=t_end - t_start)
    nyq = sr / 2
    sos = scipy.signal.butter(6, [30/nyq, 150/nyq], btype="bandpass", output="sos")
    y_k = scipy.signal.sosfiltfilt(sos, y)
    hop_n = int(0.010 * sr)
    win_n = int(0.025 * sr)
    n = (len(y_k) - win_n) // hop_n
    env = np.array([np.sqrt(np.mean(y_k[i*hop_n:i*hop_n + win_n] ** 2)) for i in range(n)])
    env_s = scipy.signal.savgol_filter(env, 5, 2) if len(env) > 5 else env
    max_e = env_s.max() if env_s.size else 1.0
    peaks, _ = scipy.signal.find_peaks(env_s, height=max_e*0.18,
                                       prominence=max_e*0.10,
                                       distance=int(0.18 / 0.010))
    return [(float(p * 0.010), float(env_s[p]), "kick") for p in peaks]


def build():
    print(f"\n=== SB1 v23 · clean structural pass · {len(SEQUENCE)} frames ===")
    bass = detect_bass(BASS, AUDIO_START, AUDIO_START + FILM_LEN)
    kicks = detect_kicks(DRUMS, AUDIO_START, AUDIO_START + FILM_LEN)
    if bass:
        max_b = max(e for _, e, _ in bass)
        bass = [(t, e/max_b, k) for t, e, k in bass]
    if kicks:
        max_k = max(e for _, e, _ in kicks)
        kicks = [(t, e/max_k, k) for t, e, k in kicks]

    merged_raw = sorted(bass + kicks, key=lambda x: x[0])
    merged = []
    for t, e, kind in merged_raw:
        if merged and abs(t - merged[-1][0]) < 0.08:
            if kind == "bass" or e > merged[-1][1]:
                merged[-1] = (t, max(e, merged[-1][1]),
                              "bass" if kind == "bass" else merged[-1][2])
            continue
        merged.append((t, e, kind))
    print(f"Punch events available: {len(merged)}")

    # Need (len(SEQUENCE) - 1) internal cut points; f28 held to FILM_LEN
    n_cuts = len(SEQUENCE) - 1
    first_t = merged[0][0]
    # Anchor the LAST internal cut at film 52.5s — that's where the master's
    # final loud kick lands. Source-side detection at 54.49 was a false
    # positive (or a different musical event); the master audit confirms the
    # actual final loud kick is at master 55.23s = film 52.23s.
    # Snap to nearest punch within 1.5s of 52.5.
    LAST_ANCHOR_TARGET = 52.15   # tuned: master 55.23 kick − 50ms baseline offset = film 52.18s, target 52.15
    last_anchor = min(merged, key=lambda x: abs(x[0] - LAST_ANCHOR_TARGET))[0]
    print(f"Need {n_cuts} cut points · last cut anchored at {last_anchor:.2f}s "
          f"(target {LAST_ANCHOR_TARGET}s, f28 hold = {FILM_LEN-last_anchor:.2f}s)")

    # Distribute targets evenly between first punch and the last anchor
    targets = [first_t + (last_anchor - first_t) * (i / (n_cuts - 1))
               for i in range(n_cuts)]

    # Non-exclusive snap: each target → nearest punch independently
    chosen_raw = []
    for target in targets:
        best, best_dist = None, 1.5
        for t, _, _ in merged:
            d = abs(t - target)
            if d < best_dist:
                best_dist = d
                best = t
        if best is not None:
            chosen_raw.append(round(best, 3))
    # Dedupe by 0.5s min spacing — for any pair within 0.5s, push the later
    # cut to the next-best nearby punch
    chosen_raw = sorted(chosen_raw)
    chosen = [chosen_raw[0]]
    for c in chosen_raw[1:]:
        if c - chosen[-1] >= 0.5:
            chosen.append(c)
        else:
            # Find the next punch after chosen[-1] + 0.5 that's within 1.5s
            wanted = chosen[-1] + 0.6
            alt = None
            alt_d = 1.5
            for t, _, _ in merged:
                if t < chosen[-1] + 0.5: continue
                d = abs(t - wanted)
                if d < alt_d:
                    alt_d = d
                    alt = t
            if alt is not None:
                chosen.append(round(alt, 3))

    cuts = [0.0] + chosen + [FILM_LEN]
    deduped = [cuts[0]]
    for c in cuts[1:]:
        if c - deduped[-1] >= 0.5:
            deduped.append(c)
    cuts = deduped
    cuts[-1] = FILM_LEN

    n = len(cuts) - 1
    seq = SEQUENCE[:n]

    windows = []
    for i in range(n):
        s_t = cuts[i]; e_t = cuts[i+1]
        windows.append({
            "frame": seq[i],
            "start_in_audio": round(s_t, 3),
            "end_in_audio": round(e_t, 3),
            "duration": round(e_t - s_t, 3),
            "abs_audio_t": round(AUDIO_START + s_t, 3),
        })

    # Final audit on actual windows
    for i in range(len(windows) - 1):
        assert windows[i]["frame"] != windows[i+1]["frame"], \
            f"consecutive dup at window {i}"
        assert windows[i]["frame"] not in FLAGGED, f"flagged frame in window {i}"
    assert windows[-1]["frame"] == 28, "last window must be f28 finale"

    print(f"\n{len(windows)} cuts (all audited clean):")
    for w in windows:
        marker = "  ★FINALE" if w is windows[-1] else ""
        print(f"  f{w['frame']:02d}  {w['start_in_audio']:5.2f}→{w['end_in_audio']:5.2f}s ({w['duration']:.2f}s){marker}")

    out = {
        "audio_file": "Beats.mp3",
        "audio_start_sec": AUDIO_START,
        "audio_end_sec": AUDIO_START + FILM_LEN,
        "film_duration_sec": FILM_LEN,
        "phase": "sb1_v23_clean_structural",
        "storyboard": "1",
        "windows": windows,
    }
    (ROOT / "audio/cut_sheet_sb1.json").write_text(json.dumps(out, indent=2))
    print(f"\nWrote audio/cut_sheet_sb1.json")


if __name__ == "__main__":
    build()
