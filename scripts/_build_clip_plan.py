#!/usr/bin/env python3
"""
Build the 30+ clip editorial plan from the music analysis.

Output: scripts/clip_plan.json — every clip with:
  - index, t_in, t_out, duration
  - act (1/2/3)
  - source_png (which storyboard frame)
  - source_clip (which Veo render if reusing footage), source_in_s
  - entry_motion, exit_motion (continuity vectors)
  - palette_start, palette_end
  - shimmer_behavior
  - music_anchor (which beat/impact/breath this clip lives on)
  - notes (generation intent)
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ANALYSIS = json.loads((ROOT / "scripts" / "music_analysis.json").read_text())
OUT = ROOT / "scripts" / "clip_plan.json"

# Editorial spec — every clip locks to a music event.
# Major impacts cluster: 24.85, 25.43, 26.35, 27.26 → rapid hard cuts.
# Breath windows: 6.05-6.85, 23.89-26.14, 28.99-29.84, 43.88-44.73, 51.28-52.08.

CLIPS = [
    # idx, t_in, t_out, act, anchor, source_png, source_clip, src_in, entry, exit, palette_start, palette_end, shimmer, notes
    # ACT 1 · ORIGIN (0-8s) — sacred energy birth
    dict(i= 1, t_in= 0.00, t_out= 0.49, act=1, anchor="cold open (silence)",
         png="01a_origin", clip="01a_origin", src_in=0.0,
         entry="static · single point", exit="hold",
         pal_a="black 100%", pal_b="black + cyan core",
         shimmer="single fixed pixel, no drift",
         notes="absolute silence frame, electron not yet visible"),
    dict(i= 2, t_in= 0.49, t_out= 1.20, act=1, anchor="STRONG BEAT 0.49 · ignition",
         png="01b_pulse_out", clip="01b_pulse_out", src_in=0.0,
         entry="point → ring", exit="ring expanding outward",
         pal_a="black + cyan core", pal_b="cyan ring on black",
         shimmer="first pulse, radial",
         notes="the ignition · electron pulses outward in one perfect ring"),
    dict(i= 3, t_in= 1.20, t_out= 2.20, act=1, anchor="momentum onset (flux peak)",
         png="01c_first_trail", clip="01c_first_trail", src_in=0.0,
         entry="ring continues outward", exit="electron arcs forward leaving trail",
         pal_a="cyan ring", pal_b="cyan with first trail",
         shimmer="radial drift outward, trail behind",
         notes="continuity — same electron, now traveling"),
    dict(i= 4, t_in= 2.20, t_out= 3.50, act=1, anchor="energy builds",
         png="02a_wind", clip="02a_wind", src_in=2.0,
         entry="trail continues forward", exit="turbine pulse emerging",
         pal_a="cyan trail on evergreen", pal_b="cyan pulse from blade tips",
         shimmer="field expanding around turbine silhouette",
         notes="first energy source visible — wind turbine emerges in the field"),
    dict(i= 5, t_in= 3.50, t_out= 5.00, act=1, anchor="cascade",
         png="02b_solar", clip="02b_solar", src_in=2.0,
         entry="turbine pulse outward", exit="solar cascade right",
         pal_a="cyan pulse", pal_b="cyan + lime data cascade",
         shimmer="data points cascading eastward",
         notes="solar joins · lime accents introduced for first time"),
    dict(i= 6, t_in= 5.00, t_out= 6.05, act=1, anchor="approaching breath",
         png="02c_hydro", clip="02c_hydro", src_in=2.0,
         entry="data cascade settles", exit="release downward",
         pal_a="cyan + lime sparse", pal_b="cyan downstream",
         shimmer="downward release pattern",
         notes="hydro · vertical motion sets up the breath"),
    dict(i= 7, t_in= 6.05, t_out= 6.85, act=1, anchor="BREATH 6.05-6.85 · held",
         png="03a_dense_field", clip="03a_dense_field", src_in=4.0,
         entry="downstream pause", exit="held density",
         pal_a="evergreen + scattered cyan", pal_b="same, even calmer",
         shimmer="minimal drift, low density",
         notes="visual restraint · particles slow, music breathes"),
    dict(i= 8, t_in= 6.85, t_out= 8.00, act=1, anchor="re-entry",
         png="03b_grid_order", clip="03b_grid_order", src_in=2.5,
         entry="from breath, particles re-coalesce", exit="snapping to grid",
         pal_a="sparse cyan", pal_b="cyan dot-matrix forming",
         shimmer="halftone snap into formation",
         notes="ACT 1 ends here · particles organize"),

    # ACT 2 · INTELLIGENCE (8-24s) — the system wakes
    dict(i= 9, t_in= 8.00, t_out=10.00, act=2, anchor="grid order solid",
         png="03c_grid_perspective", clip="03c_grid_perspective", src_in=2.0,
         entry="grid formed", exit="tilting into depth",
         pal_a="cyan dot-matrix flat", pal_b="3D perspective receding",
         shimmer="grid tilts into Z-axis",
         notes="opening the world · spatial dimension reveals"),
    dict(i=10, t_in=10.00, t_out=12.00, act=2, anchor="first links",
         png="04a_first_links", clip="04a_first_links", src_in=2.5,
         entry="perspective grid", exit="cyan lines drawing between nodes",
         pal_a="evergreen + cyan dots", pal_b="cyan with bright links",
         shimmer="link lines extending between particle nodes",
         notes="the network begins drawing itself"),
    dict(i=11, t_in=12.00, t_out=14.00, act=2, anchor="radiating",
         png="04b_radiating_node", clip="04b_radiating_node", src_in=2.0,
         entry="link lines spread", exit="central node radiating outward",
         pal_a="cyan link mesh", pal_b="bright central pulse",
         shimmer="starburst pattern from one node",
         notes="intelligence concentrating · pulsing rhythm matches beat grid"),
    dict(i=12, t_in=14.00, t_out=16.00, act=2, anchor="full mesh",
         png="04c_full_mesh", clip="04c_full_mesh", src_in=3.0,
         entry="radial energy peaks", exit="complete connected mesh",
         pal_a="bright pulse", pal_b="full mesh lit",
         shimmer="every link visible, full network",
         notes="the system is fully aware"),
    dict(i=13, t_in=16.00, t_out=18.00, act=2, anchor="decision space opens",
         png="05a_paths_fan", clip="05a_paths_fan", src_in=3.0,
         entry="mesh complete", exit="paths fanning from junction",
         pal_a="full mesh", pal_b="cyan + lime path lines fanning",
         shimmer="radial fan, lime accents on key paths",
         notes="evaluating options · lime introduced as decision color"),
    dict(i=14, t_in=18.00, t_out=20.00, act=2, anchor="GridOS surfaces",
         png="05b_gridos", clip="05b_gridos", src_in=3.0,
         entry="paths probing", exit="data shimmer across layer",
         pal_a="path lines", pal_b="cascading cyan-lime intelligence",
         shimmer="data shimmer across an abstract UI layer",
         notes="GridOS · pure abstract intelligence visualization, NO text"),
    dict(i=15, t_in=20.00, t_out=22.00, act=2, anchor="path locks",
         png="05c_path_chosen", clip="05c_path_chosen", src_in=3.0,
         entry="paths dimming", exit="one bright path locked",
         pal_a="multi-path", pal_b="single bright cyan path",
         shimmer="one path bright, others fade",
         notes="the decision is made · committed"),
    dict(i=16, t_in=22.00, t_out=23.89, act=2, anchor="approach the drop",
         png="06a_comet", clip="06a_comet", src_in=2.0,
         entry="path locked", exit="sweeping forward into momentum",
         pal_a="single path", pal_b="cyan comet trail",
         shimmer="comet trail with high momentum",
         notes="ACT 2 ends · system has decided · accelerating"),

    # ACT 3 · ARRIVAL (24-60s) — the drop, ignition, keynote
    dict(i=17, t_in=23.89, t_out=24.26, act=3, anchor="BREATH 23.89-26.14 START",
         png="06b_currents", clip="06b_currents", src_in=2.5,
         entry="comet enters breath", exit="held swirl",
         pal_a="cyan motion", pal_b="dim cyan swirl",
         shimmer="motion slows · density drops",
         notes="visual restraint enters · before the impacts hit"),
    dict(i=18, t_in=24.26, t_out=24.85, act=3, anchor="STRONG BEAT 24.26",
         png="06c_aurora", clip="06c_aurora", src_in=2.0,
         entry="held swirl", exit="aurora curve forms",
         pal_a="dim cyan swirl", pal_b="lime + cyan aurora",
         shimmer="graceful curve across the frame",
         notes="lime introduces the climax color"),
    dict(i=19, t_in=24.85, t_out=25.43, act=3, anchor="IMPACT 1 · 24.85",
         png="07a_gold_burst", clip="07a_gold_burst", src_in=3.5,
         entry="aurora curve", exit="cyan radial burst",
         pal_a="aurora", pal_b="explosion of cyan particles",
         shimmer="radial burst outward",
         notes="HARD CUT on impact · cyan-only burst, no gold"),
    dict(i=20, t_in=25.43, t_out=26.35, act=3, anchor="IMPACT 2 · 25.43",
         png="07b_lime_ripple", clip="07b_lime_ripple", src_in=2.5,
         entry="cyan explosion", exit="lime ripple traveling outward",
         pal_a="cyan burst", pal_b="lime concentric waves",
         shimmer="lime ripple through cyan grid",
         notes="HARD CUT · lime energy escalates"),
    dict(i=21, t_in=26.35, t_out=27.26, act=3, anchor="IMPACT 3 · 26.35",
         png="07c_climax", clip="07c_climax", src_in=3.0,
         entry="lime ripple", exit="convergence at peak",
         pal_a="lime ripples", pal_b="lime + cyan convergence flash",
         shimmer="all energy collapsing to one point",
         notes="HARD CUT · the convergence point"),
    dict(i=22, t_in=27.26, t_out=28.42, act=3, anchor="IMPACT 4 · 27.26",
         png="04c_full_mesh", clip="04c_full_mesh", src_in=4.0,
         entry="convergence flash", exit="mesh re-stabilizing",
         pal_a="convergence", pal_b="stable cyan mesh",
         shimmer="post-impact stabilization",
         notes="HARD CUT · the system absorbed all that energy"),
    dict(i=23, t_in=28.42, t_out=29.35, act=3, anchor="STRONG BEAT 28.42",
         png="05b_gridos", clip="05b_gridos", src_in=4.0,
         entry="stable mesh", exit="decision confirmed",
         pal_a="stable mesh", pal_b="lime confidence pulse",
         shimmer="confidence settling",
         notes="GridOS · AI 95% · this is the spine moment"),
    dict(i=24, t_in=29.35, t_out=32.11, act=3, anchor="STRONG BEAT 29.35 · momentum",
         png="06a_comet", clip="06a_comet", src_in=3.5,
         entry="decision confirmed", exit="momentum across territory",
         pal_a="lime pulse", pal_b="cyan comet across landscape",
         shimmer="comet trail across regional grid",
         notes="dispatch committed · momentum builds"),
    dict(i=25, t_in=32.11, t_out=33.04, act=3, anchor="STRONG BEAT 32.11",
         png="06b_currents", clip="06b_currents", src_in=3.0,
         entry="comet momentum", exit="currents weaving",
         pal_a="cyan comet", pal_b="multiple flow currents",
         shimmer="multiple cyan currents crossing",
         notes="approach phase · multiple paths converging"),
    dict(i=26, t_in=33.04, t_out=36.27, act=3, anchor="approach the city",
         png="06c_aurora", clip="06c_aurora", src_in=3.0,
         entry="currents weaving", exit="aurora bending toward target",
         pal_a="cyan currents", pal_b="cyan-lime aurora",
         shimmer="aurora curving toward destination",
         notes="energy heading toward Atlanta"),
    dict(i=27, t_in=36.27, t_out=39.50, act=3, anchor="STRONG BEAT 36.27 · arrival prep",
         png="08c_aerial_sweep", clip="08c_aerial_sweep", src_in=2.0,
         entry="aurora bend", exit="aerial sweep across territory",
         pal_a="aurora", pal_b="aerial view of grid network",
         shimmer="every node pulsing in unison from altitude",
         notes="we are arriving · regional view of grid alive"),
    dict(i=28, t_in=39.50, t_out=43.88, act=3, anchor="building to silence",
         png="08b_distribution", clip="08b_distribution", src_in=2.5,
         entry="aerial sweep", exit="distribution lines lighting",
         pal_a="aerial", pal_b="lit distribution lines into neighborhoods",
         shimmer="cyan pulses traveling along lines",
         notes="energy spreading into the region · building tension to drop"),
    dict(i=29, t_in=43.88, t_out=44.73, act=3, anchor="BREATH 43.88-44.73 · THE DROP",
         png="08a_atlanta", clip="08a_atlanta", src_in=0.5,
         entry="distribution lit", exit="held darkness, stadium silhouette emerging",
         pal_a="lit lines", pal_b="dark + faint stadium silhouette",
         shimmer="minimal · the calm before",
         notes="THE SILENCE · only true silence in the track · hold here"),
    dict(i=30, t_in=44.73, t_out=46.50, act=3, anchor="STRONG BEAT 44.81 · IGNITION",
         png="08a_atlanta", clip="08a_atlanta", src_in=2.0,
         entry="silence ends", exit="stadium fully revealed in halftone",
         pal_a="dark silhouette", pal_b="Mercedes-Benz Stadium pinwheel in cyan halftone",
         shimmer="faceted petals trace in cyan light",
         notes="THE CITY IGNITES · this is the visual climax"),
    dict(i=31, t_in=46.50, t_out=49.50, act=3, anchor="stadium lit",
         png="08c_aerial_sweep", clip="08c_aerial_sweep", src_in=3.0,
         entry="stadium revealed", exit="aerial dolly over city",
         pal_a="stadium", pal_b="full city in halftone",
         shimmer="region-wide pulse in cyan",
         notes="Atlanta alive · the network we built is now visible at scale"),
    dict(i=32, t_in=49.50, t_out=51.28, act=3, anchor="venue approach",
         png="09a_venue_dawn", clip="09a_venue_dawn", src_in=2.5,
         entry="aerial above city", exit="dolly toward Signia at dawn",
         pal_a="city aerial", pal_b="Signia by Hilton glass tower",
         shimmer="atmospheric dawn shimmer on the building",
         notes="the audience knows this venue · they are here right now"),
    dict(i=33, t_in=51.28, t_out=52.08, act=3, anchor="BREATH 51.28-52.08",
         png="09a_venue_dawn", clip="09a_venue_dawn", src_in=4.0,
         entry="venue at dawn", exit="held breath before interior",
         pal_a="venue exterior", pal_b="same, held quiet",
         shimmer="atmospheric only",
         notes="pause · anticipation · the audience leans in"),
    dict(i=34, t_in=52.08, t_out=54.50, act=3, anchor="enter the room",
         png="09b_keynote_stage", clip="09b_keynote_stage", src_in=2.0,
         entry="venue exterior", exit="push into keynote hall",
         pal_a="exterior", pal_b="keynote hall, stage lit",
         shimmer="stage screens animating with cyan-lime",
         notes="we are now inside the room you are sitting in"),
    dict(i=35, t_in=54.50, t_out=58.00, act=3, anchor="hero hold begins",
         png="09c_hero_hold", clip="09c_hero_hold", src_in=2.5,
         entry="inside the hall", exit="sustained cyan particle bloom",
         pal_a="keynote hall", pal_b="evergreen with cyan bloom",
         shimmer="soft sustained particle bloom · cyan accents",
         notes="settling · breath for the title to land"),
    dict(i=36, t_in=58.00, t_out=60.00, act=3, anchor="TITLE LAND",
         png="09c_hero_hold", clip="09c_hero_hold", src_in=5.0,
         entry="cyan bloom holding", exit="ORCHESTRATE title fully lit",
         pal_a="cyan bloom", pal_b="ORCHESTRATE 2026 in lime + white",
         shimmer="particle bloom continues behind title",
         notes="the moment · ORCHESTRATE wordmark in lime, 2026 in white, particles behind"),
]

# Validate
total = sum(c["t_out"] - c["t_in"] for c in CLIPS)
assert abs(total - 60.0) < 0.01, f"total = {total}, expected 60.0"
assert len(CLIPS) >= 30, f"only {len(CLIPS)} clips, need ≥30"

# Sanity check timestamps are sequential
for i in range(1, len(CLIPS)):
    assert CLIPS[i]["t_in"] >= CLIPS[i-1]["t_out"] - 0.001, f"gap at clip {i}"

out = {
    "total_clips": len(CLIPS),
    "total_duration": total,
    "music_anchors_used": {
        "major_impacts": [24.85, 25.43, 26.35, 27.26],
        "strong_beats_used": [0.49, 24.26, 28.42, 29.35, 32.11, 33.04, 36.27, 44.81],
        "breath_windows_used": [[6.05, 6.85], [23.89, 24.26], [43.88, 44.73], [51.28, 52.08]],
    },
    "clips": CLIPS,
}

OUT.write_text(json.dumps(out, indent=2))
print(f"wrote {OUT.relative_to(ROOT)}")
print(f"  {len(CLIPS)} clips · {total:.2f}s total")
print(f"  act 1: clips 1-{sum(1 for c in CLIPS if c['act']==1)}")
print(f"  act 2: clips {sum(1 for c in CLIPS if c['act']==1)+1}-{sum(1 for c in CLIPS if c['act']<=2)}")
print(f"  act 3: clips {sum(1 for c in CLIPS if c['act']<=2)+1}-{len(CLIPS)}")
durs = [c["t_out"] - c["t_in"] for c in CLIPS]
print(f"  durations: min {min(durs):.2f}s · max {max(durs):.2f}s · avg {sum(durs)/len(durs):.2f}s")
