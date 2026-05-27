# The Electron · 60s Beat Lock

**Locked audio:** `references/beats.mp3` · 2m 22s source · cut window picked from energy analysis.

**Proposed cut:** **0:37.59 → 1:37.59** (60.0 sec)

## Why this window

Energy analysis of beats.mp3 (RMS over 200ms windows, silence-gates at -30dB / 0.4s threshold):

| Track time | Event | Why it matters for us |
|---|---|---|
| 0:00 – 0:01.6 | Pure silence | Track intro — not the right entry for a film opener |
| 0:08 / 0:22 / **0:37.59** | Silence-gate transitions | Natural musical drops at section boundaries |
| 0:37.59 – 0:38.51 | **Gate (0.9s)** | **Cut window starts here — gives beat 01 ORIGIN a literal breath** |
| 1:07.25 / 1:14.52 | Two gates inside the window | Beat-lock anchors for 05→06 and 06→07 transitions |
| 1:35.84 – 1:37.59 | Climax peak (–9.44 dB, hottest point in the track) | **Cut window ends on the climax — ORCHESTRATE title hit lands ON the loudest beat** |

The 60s window starts on a natural breath-gate and ends on the loudest point of the song. Every beat boundary aligns to a musical event, not arbitrary timing.

## Beat-Lock Chart

Format: `Window (film time) · Track (source time) · Frame in/out · Musical event`

| Beat | Window | Track | Frames | Musical anchor |
|---|---|---|---|---|
| **01 ORIGIN** · potential gathers | 0.00 – 5.00 | 37.59 – 42.59 | 01A (0.0–1.7) silent breath · 01B (1.7–3.3) pulse · 01C (3.3–5.0) trail | Gate at window 0.0–0.9 → 01A literally silent |
| **02 THE SOURCE** · wind / solar / hydro | 5.00 – 12.00 | 42.59 – 49.59 | 02A (5.0–7.3) · 02B (7.3–9.7) · 02C (9.7–12.0) | Track enters at moderate energy |
| **03 INTO THE GRID** · particle field | 12.00 – 18.00 | 49.59 – 55.59 | 03A (12–14) · 03B (14–16) · 03C (16–18) | Sustained build |
| **04 INTELLIGENT CONNECTIONS** · network forms | 18.00 – 24.00 | 55.59 – 61.59 | 04A (18–20) · 04B (20–22) · 04C (22–24) | Continued build |
| **05 THE DECISION** · real GridOS | 24.00 – 32.00 | 61.59 – 69.59 | 05A (24–27) · 05B (27–30) GridOS UI · 05C (30–32) path chosen | **Gate at window 29.66 → 05B "AI confidence 95%" lands on the gate** |
| **06 FLOW + MOTION** · cross-territory | 32.00 – 39.00 | 69.59 – 76.59 | 06A (32–34.5) · 06B (34.5–36.9) · 06C (36.9–39) | **Gate at window 36.93 → 06B→06C transition** |
| **07 REACHING THE REGION** · approach | 39.00 – 46.00 | 76.59 – 83.59 | 07A (39–41.5) · 07B (41.5–43.5) · 07C (43.5–46) | Building toward peak |
| **08 THE CITY IGNITES** · Mercedes-Benz Stadium | 46.00 – 55.00 | 83.59 – 92.59 | 08A (46–49) stadium reveal · 08B (49–52) distribution · 08C (52–55) aerial sweep | Energy climbing |
| **09 THE KEYNOTE** · denouement | 55.00 – 60.00 | 92.59 – 97.59 | 09A (55–57) venue · 09B (57–58.5) stage · 09C (58.5–60) ORCHESTRATE hero | **Climax peak at window 58–60 → title lands ON the loudest beat** |

## Production notes

- **Veo 3 clips are 8s each.** Each beat-frame is shorter than 8s, so the renders get trimmed in post. Order: render at 8s → cut to in/out → cross-dissolve adjacent frames within the same beat (≤0.3s) → hard cut on beat boundaries.
- **Beat 09C is sustained breath** — easiest to handle as a held frame with subtle motion, not a discrete 8s clip.
- **The three musical gates inside the window (0.0, 29.66, 36.93) are hard-cut anchors.** Edits must hit these.
- **Climax landing.** The ORCHESTRATE wordmark fade-in should be timed to peak at window 60.0s (track 97.59s), which is just past the loudest point of the song. Hold the mark for ≥1.5s past the cut.
- **No fade-out at end.** Hard cut to black after the title hold, or freeze on the final frame.

## Total budget at Veo 3 Fast

| Item | Count | Per | Subtotal |
|---|---|---|---|
| Veo 3 Fast i2v · 8s · 16:9 | 24 clips (beats 02–09) | ~$0.30 | **~$7.20** |
| Re-rolls (assume 50% retry rate) | 12 | ~$0.30 | ~$3.60 |
| **Total render budget** | | | **~$11–15** |

Beat 01 already done via chain_test (no spend).

## How to run

```bash
source ~/.claude/secrets/orchestrate-veo.env
node scripts/_veo_electron.mjs
```

Outputs to `electron/_render/<shot>.mp4`. Idempotent — re-run to fill gaps without re-spending.
