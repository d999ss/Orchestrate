#!/usr/bin/env python3
"""Read cut points from /tmp/manual_cuts.json, write the cut sheet, rebuild."""
import json, subprocess, pathlib

ROOT = pathlib.Path("/Users/donnysmith/Projects/Orchestrate")
data = json.loads((pathlib.Path("/tmp/manual_cuts.json")).read_text())

AUDIO_START = 7.13
FILM_LEN = 60.0
cuts = [0.0] + sorted(data["cuts"]) + [FILM_LEN]
story = data["story"]
assert len(cuts) - 1 == len(story), f"need {len(story)} windows, got {len(cuts)-1}"

windows = []
for i, frame in enumerate(story):
    s_t = cuts[i]
    e_t = cuts[i+1]
    windows.append({
        "frame": frame,
        "start_in_audio": round(s_t, 3),
        "end_in_audio": round(e_t, 3),
        "duration": round(e_t - s_t, 3),
        "abs_audio_t": round(AUDIO_START + s_t, 3),
    })

cs = {
    "audio_file": "Beats.mp3",
    "audio_start_sec": AUDIO_START,
    "audio_end_sec": AUDIO_START + FILM_LEN,
    "film_duration_sec": FILM_LEN,
    "phase": "sb1_manual_editor",
    "storyboard": "1",
    "windows": windows,
}
(ROOT / "audio/cut_sheet_sb1.json").write_text(json.dumps(cs, indent=2))
print(f"Wrote audio/cut_sheet_sb1.json with {len(windows)} windows")
subprocess.run(["bash", str(ROOT / "scripts/assemble_sb.sh"), "1"], check=True)
subprocess.run(["open", str(ROOT / "films/sb1_master.mp4")])
