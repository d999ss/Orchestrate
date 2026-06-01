#!/usr/bin/env python3
"""Regenerate all 16 SB1 hero clips with Runway Gen-4.5 image-to-video.

Strategy:
- Use the approved storyboard PNG as promptImage (locks aesthetic)
- Add motion-explicit prompt: camera moves + subject kinetic action
- 5-second clips at 1280:720 (matches 16:9, can upscale later)
- Idempotent: skips clips already in films/sb1_clips_runway/

Cost: 16 × 12 credits = 192 credits at Gen-4.5 720p · ~$10
Time: ~16 × 1-2 min sequential (1 concurrent limit)
"""
import os, json, base64, pathlib, time
import sys
from runwayml import RunwayML, TaskFailedError

ROOT = pathlib.Path("/Users/donnysmith/Projects/Orchestrate")
OUT = ROOT / "films" / "sb1_clips_runway"
OUT.mkdir(parents=True, exist_ok=True)

# Load API key
SECRETS = json.loads(pathlib.Path("/Users/donnysmith/.claude/secrets.json").read_text())
os.environ["RUNWAYML_API_SECRET"] = SECRETS["runway"]["api_key"]

client = RunwayML()

# Style lock — every prompt opens with this.
STYLE = (
    "Maintain the exact cyan-on-deep-black painterly concept-art aesthetic of the reference image. "
    "Energy under control — directed, precise, deliberate. NOT chaotic, NOT photoreal lightning, "
    "NOT explosive. The energy stays channeled, contained, and purposeful. "
    "No text, no logos, no words. "
)

# Subject prompts taken VERBATIM from the original SB1 storyboard script
# (gen_sb1_full.py). Camera motion added minimally — only what fits the
# storyboard description's verb. Energy stays controlled.
SUBJECTS = {
    1:  "A glowing cyan globe floats in deep darkness. City lights twinkle on one by one across continents. "
        "Camera slowly orbits the planet.",
    2:  "Camera holds, then slowly pushes in. Globe transitions into a modern hyperscale energy facility; "
        "lights flicker on across the structure in a controlled cascade.",
    3:  "A massive turbine couples to a generator; the shaft begins rotating, mechanical coupling "
        "tightening smoothly. Camera holds with subtle drift.",
    4:  "Inside a turbine combustion chamber: natural gas igniting in a perfect ring of blue-white flame. "
        "The ring forms with deliberate intensity, contained within the chamber.",
    9:  "Glowing cyan-white electricity travels through polished conductors and busbars in pulses of energy. "
        "The pulses race precisely along the wires. Camera holds.",
    10: "Electricity flows from generator output into the high-voltage power grid switchyard at night. "
        "Camera dollies slowly forward as the energy moves outward.",
    11: "Macro of high-voltage transformers humming under load; insulators glowing slightly, "
        "cooling fins shimmering. Subtle camera drift.",
    12: "Aerial view: transmission lines stretching across dark countryside, carrying glowing cyan energy. "
        "Camera flies forward along the corridor.",
    13: "Aerial top-down: the regional electrical grid revealed as a glowing cyan network across dark terrain. "
        "Camera slowly pulls back to expose the full network.",
    18: "Wide cinematic: transmission lines lead into a brightly-lit city at night, cyan glow surging "
        "along them in directed pulses. Camera tracks forward.",
    19: "Distant Atlanta skyline at night begins lighting up in cascading waves, buildings turning on "
        "block by block. Camera pushes in toward the city.",
    20: "Wider city view: buildings, roads, and infrastructure activating across the city, light "
        "spreading outward in a controlled wave. Camera slowly drifts over the city.",
    21: "Aerial wide of a downtown stadium at night, becoming the brightest point in the city, "
        "lighting up. Camera circles the stadium.",
    25: "Modern conference center exterior at night: interior lights cascade on floor by floor, "
        "top to bottom. Camera holds and slowly pushes in.",
    27: "Inside the keynote hall: ambient house lights coming up, scale of the room becoming visible. "
        "Camera dollies forward down the aisle.",
    28: "Keynote stage: stage lights ignite, towering immersive curved LED screens flickering to life "
        "with cyan visuals. Controlled crescendo of light. Camera holds.",
}


def gen_one(idx):
    out_mp4 = OUT / f"clip-{idx:02d}.mp4"
    if out_mp4.exists():
        return f"clip-{idx:02d}: exists (skip)"

    img_path = ROOT / "storyboard-1" / f"frame-{idx:02d}.png"
    if not img_path.exists():
        return f"clip-{idx:02d}: missing storyboard image"

    b64 = base64.b64encode(img_path.read_bytes()).decode()
    data_uri = f"data:image/png;base64,{b64}"

    end_path = ROOT / "storyboard-1" / "endframes" / f"frame-{idx:02d}-end.png"
    if not end_path.exists():
        return f"clip-{idx:02d}: missing end keyframe"
    end_b64 = base64.b64encode(end_path.read_bytes()).decode()
    end_uri = f"data:image/png;base64,{end_b64}"

    prompt = STYLE + SUBJECTS[idx]
    sidecar = OUT / f"clip-{idx:02d}.task.json"
    print(f"  clip-{idx:02d}: submitting Gen-3a Turbo first+last...")
    try:
        task = client.image_to_video.create(
            model="gen3a_turbo",
            prompt_image=[
                {"position": "first", "uri": data_uri},
                {"position": "last", "uri": end_uri},
            ],
            prompt_text=prompt,
            ratio="1280:768",
            duration=5,
        ).wait_for_task_output(timeout=420)
        # SAVE task ID + URL before download attempt — recoverable on failure
        sidecar.write_text(json.dumps({
            "task_id": getattr(task, "id", None),
            "output": list(task.output) if task.output else [],
            "frame": idx,
        }, indent=2))
        if not task.output:
            return f"clip-{idx:02d}: ERROR no output"
        video_url = task.output[0]
        # Use httpx (proper SSL via certifi) — NOT urllib.request
        import httpx
        with httpx.stream("GET", video_url, follow_redirects=True, timeout=120) as r:
            r.raise_for_status()
            with open(out_mp4, "wb") as f:
                for chunk in r.iter_bytes():
                    f.write(chunk)
        size_kb = out_mp4.stat().st_size // 1024
        return f"clip-{idx:02d}: saved {size_kb} KB"
    except TaskFailedError as e:
        return f"clip-{idx:02d}: FAILED {e.task_details}"
    except Exception as e:
        return f"clip-{idx:02d}: ERROR {type(e).__name__}: {e}"


def main():
    # Use the f09 test we already validated; skip if exists
    todo = [i for i in SUBJECTS.keys() if not (OUT / f"clip-{i:02d}.mp4").exists()]
    # Also skip if we have a -firstlast version we can promote
    promotions = []
    for i in SUBJECTS.keys():
        fl = OUT / f"clip-{i:02d}-firstlast.mp4"
        canon = OUT / f"clip-{i:02d}.mp4"
        if fl.exists() and not canon.exists():
            canon.write_bytes(fl.read_bytes())
            promotions.append(i)
            if i in todo:
                todo.remove(i)
    if promotions:
        print(f"Promoted existing firstlast tests: {promotions}")

    print(f"Generating {len(todo)} clips with Gen-3a Turbo first+last (5s · 25 cr each)")
    print(f"Estimated cost: {len(todo) * 25} credits\n")

    org = client.organization.retrieve()
    needed = len(todo) * 25
    print(f"Balance: {org.credit_balance} · Need: {needed}")
    if org.credit_balance < needed:
        print(f"WARNING: short by {needed - org.credit_balance}")
    print()

    for idx in todo:
        result = gen_one(idx)
        print(f"  {result}")
        time.sleep(2)

    print("\n=== Done ===")
    final_balance = client.organization.retrieve().credit_balance
    spent = org.credit_balance - final_balance
    print(f"Spent: {spent} credits · Remaining: {final_balance}")


if __name__ == "__main__":
    main()
