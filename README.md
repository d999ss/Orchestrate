# Orchestrate 2026 — From Kick to Grid

Storyboard and previz package for **GE Vernova × Bttr** "Orchestrate 2026" Direction 3 Hybrid spot.

**Tagline:** *Powering Performance, from the Game to the Grid.*

## Contents

| Path | What |
|------|------|
| `storyboard.html` | Self-contained interactive storyboard. 27 sub-shots across 9 beats, embedded Spotify candidates, fullscreen slideshow. Open in any browser. |
| `frames/` | Nine 16:9 reference frames extracted from the original storyboard PDF (1280×720 PNG). Used as `start_image` references for hero-shot generation. |
| `subshots/` | 18 newly generated sub-shot mp4s (Seedance 2.0 std, 1080p, 4s each). Pair with the v3 hero shots in `../ge-previz-v3/` for the full 27-shot edit. |
| `bttr-favicon.svg` / `bttr-favicon-dark.svg` | Bttr. wordmark assets pulled from makebttr.com. |

## Generation pipeline

1. **Storyboard extraction** — Original PDF cropped to nine 16:9 panels (one per beat).
2. **Reference upload** — Frames uploaded to Higgsfield as `start_image` inputs.
3. **Previz iterations**
   - v1: Veo 3.1 Lite (1344×768) — disposable
   - v2: Cinema Studio 3.0 (1344×768) — disposable
   - **v3: Seedance 2.0 std (1920×1080)** — current cut, archived locally at `../ge-previz-v3/GE_Previz_v3.mp4`
4. **Storyboard expansion** — 9 beats × 3 sub-shots = 27 shots. Hero sub-shots use storyboard frames as references; non-hero sub-shots generated fresh.

## Storyboard structure

| Beat | Title | Sub-shots |
|------|-------|-----------|
| 01 | The Stage | Aerial wide · architecture detail · field-level |
| 02 | The Energy Builds | Crowd · field rippling · grass macro |
| 03 | The Player | Solo walk · lit corridor · ECU eyes |
| 04 | The Strategy | OTS clipboard · faces leaning · hands stacking |
| 05 | The Kick | Low approach · macro contact · explosion |
| 06 | In Flight | Ball arcing · fracturing · polygonizing |
| 07 | Energy Becomes Data | Sphere · beams outward · nodes lighting |
| 08 | Systems Awaken | Stadium grid · cityscape · power-line pulse |
| 09 | From the Game to the Grid | Earth reveal · grid spreading · hero hold |

## Usage

```bash
open storyboard.html
```

Click **Play Slideshow** for fullscreen review. Paste any Spotify track URL into the loader to audition music candidates.

---

Bttr · April 2026
