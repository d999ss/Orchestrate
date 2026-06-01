# Orchestrate 2026 — project layout

## Deployed (git-tracked, on the live site)
- `storyboard-1..4/` · `film-1..4/` — the pages (index.html). storyboard-4 also holds `3to1/` (board previews), `frame-01..30.png` (source stills), `GEV_RULES.md`, `beats.mp3`.
- `texture/` — the Texture Engine tool (index.html). Self-contained pixel-texture generator with live controls + PNG export. Linked in the board-nav under "Texture". Live: https://orchestrate-review-bttr.vercel.app/texture/
- `films/` — deliverable masters only: `sb1_master.mp4`, `sb2_master.mp4`, `sb3_master.mp4`, `sb4_film.mp4` + their `*_poster.jpg`. Plus `sb4_clips_runway/CLIP_OK.txt`.
- `audio/` — canonical tracks + cut sheets: `music5.mp3`, `beats.mp3`, `slate_countdown.mp3`, `music5_grid.json`, `cut_sheet_sb1..4.json`, `runway_briefs_sb4.json`.
- `scripts/` — the pipeline (gen_sb4_runway, assemble_sb4, ingest_manual, finish_sb4_auto, etc.).

## Local source (gitignored, not deployed) — `_source/`
- `_source/masters/` — the high-res film masters (GE ORCHESTRATE FIXED / 4K_FINAL).
- `_source/clips/` — per-storyboard motion clips + grades (sb1/2/3 clips, locked sets, grades).
- `_source/frames/` — frame staging folders (Frames to Expand, Expanded Frames, etc.).
- `storyboard-4/3to1-4k/` — 4608x1536 board frames for the lightbox (local only).
- `films/sb4_clips_runway/*.mp4` — the 30 SB4 source clips (CLIP_OK.txt is tracked).

## Archive (gitignored, safe to delete to reclaim space) — `_archive/`
- `_archive/films/` — superseded film experiments + SB4 WIP cuts (LEDwall variants, rough/beatsync/music5 previews, etc.).
- `_archive/audio/` — scratch cut-sheet scripts, .bak files, intermediate analysis JSON.
- `_archive/storyboard-4/` — dead frame sets (4k, 4k-topaz, 3to1-fill).

## Film 4 review link
https://orchestrate-review-bttr.vercel.app/film-4/  (public; deployment protection disabled)
