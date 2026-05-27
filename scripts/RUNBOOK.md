# The Electron · Production Runbook

Final film: `electron_60s_4k.mp4` · 3840×2160 · 60s · H.264 · AAC.

## Toolchain (all installed)

| | |
|---|---|
| Veo 3 (Vertex) | `~/.claude/secrets/orchestrate-veo.env` + `veo-runner-key.json` — confirmed live 2026-05-27 |
| Topaz Video AI | `/Applications/Topaz Video.app` — uses bundled ffmpeg for CLI upscale |
| Audio | `references/demand-audio.m4a` (60s, locked) |
| Source PNGs | `electron/*.png` — all 27 present |

## Pipeline (3 steps)

```bash
cd ~/Projects/Orchestrate

# 1. Generate 24 × 1080p clips for beats 02-09 (~$18 total · Veo 3 standard)
source ~/.claude/secrets/orchestrate-veo.env
node scripts/_veo_electron.mjs
# → electron/_render/*.mp4

# 2. Upscale to 4K via Topaz Proteus (prob-4 model · 2× scale · GPU)
bash scripts/_upscale_4k.sh
# → electron/_render_4k/*.mp4

# 3. Trim per beat-lock, concatenate, mux with locked Demand audio
bash scripts/_compose_60s.sh
# → electron_60s_4k.mp4
```

All three scripts are **idempotent** — re-run to fill gaps without re-spending.

## Beat structure

See `BEATS_TIMELINE.md` for the full chart. **Note:** that file was paced
against Beats.mp3 (now an alternative). The compose script uses equal-paced
timings (~2.2s/frame) as a starting baseline until BEATS_TIMELINE is re-paced
against demand-audio.m4a.

## Open items before final render

| Item | Status |
|---|---|
| Veo 3 access | ✅ live |
| Audio | ✅ locked (`demand-audio.m4a`) |
| 4K target | ✅ confirmed (Sparks · 3840×2160) |
| Topaz install | ✅ Video AI, Photo AI, Gigapixel all present |
| Beat-lock pacing against demand-audio | ⏳ baseline equal-paced; refine when needed |
| ORCHESTRATE wordmark vector | ⏳ for beat 09C hero hold |
| GridOS Atlanta-specific UI | ⏳ for beat 05B |
| Frame rate / codec / container spec rows | ⏳ from Sparks doc |

## Cost projection

| Stage | Spend | Time |
|---|---|---|
| Veo 3 generate 24 × 8s @ 1080p | ~$0.50 × 24 = $12 + ~50% retry buffer = **~$18** | 30-60 min (sequential API calls) |
| Topaz upscale 24 × 8s @ 4K (Proteus) | $0 (local GPU) | ~10-20 min depending on GPU |
| Final compose | $0 | <1 min |
| **Total** | **~$18** | **~1-2 hr** |

## Validation

Before firing the full $18 run, validate the pipeline end-to-end with a single
beat:

```bash
source ~/.claude/secrets/orchestrate-veo.env
# Modify scripts/_veo_electron.mjs JOBS to keep only one frame for testing
node scripts/_veo_electron.mjs
bash scripts/_upscale_4k.sh
```

Spot-check the resulting 4K clip looks right before committing to the full run.
