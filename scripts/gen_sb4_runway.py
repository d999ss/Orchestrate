#!/usr/bin/env python3
"""Animate SB4 stills with Runway image-to-video, forward-through-space doctrine.

- promptImage = the 4608x1536 (3:1) still, letterboxed into Runway's widest ratio
  1584:672 (72px bars top/bottom) so no content is cropped. Crop the 3:1 band back
  out later, then Topaz Video upscale to 4608x1536.
- promptText = style lock + the per-frame forward-motion brief from runway_briefs_sb4.json
- 5s silent clips. Idempotent: skips clips already saved.

Usage:
  .venv/bin/python scripts/gen_sb4_runway.py 8        # one clip (test)
  .venv/bin/python scripts/gen_sb4_runway.py          # all 30 missing
  .venv/bin/python scripts/gen_sb4_runway.py --force 8
"""
import os, io, sys, json, base64, pathlib
from PIL import Image
from runwayml import RunwayML, TaskFailedError

ROOT = pathlib.Path("/Users/donnysmith/Projects/Orchestrate")
STILLS = ROOT / "storyboard-4" / "3to1-4k"
OUT = ROOT / "films" / "sb4_clips_runway"; OUT.mkdir(parents=True, exist_ok=True)
BRIEFS = json.loads((ROOT / "audio" / "runway_briefs_sb4.json").read_text())

SECRETS = json.loads(pathlib.Path(os.path.expanduser("~/.claude/secrets.json")).read_text())
os.environ["RUNWAYML_API_SECRET"] = SECRETS["runway"]["api_key"]
client = RunwayML()

MODEL = "gen4_turbo"
RATIO = "1584:672"           # Runway's widest; least letterbox to 3:1
FRAME = (1584, 672)          # feed Runway a FULL frame (no bars) at its widest ratio
# (deliverable 3:1 is recovered by center-cropping 1584x528 in the assembler, like build_sb3_ledwall)
# FPV chase: camera rides just behind the electron, flying forward through space.
# Lead with the camera physics — I2V follows FPV motion far more reliably than "push".
FPV = ("FPV first-person flight. The camera flies fast and continuously FORWARD through the scene, "
       "riding just behind a single bright cyan-teal electron point that streaks ahead and leads the way deeper into the frame. "
       "The whole environment rushes toward the camera and blurs past the edges with strong forward parallax and depth. "
       "Continuous forward dolly chasing the point. The camera NEVER stops, NEVER pans sideways, NEVER orbits, NEVER pulls back, NEVER tilts away. ")
TAIL = (" " + BRIEFS["global_constraints"])
MOTION = {f["frame"]: f["motion"] for f in BRIEFS["frames"]}


def fill_data_uri(still_path):
    # scale-to-FILL the Runway frame (cover, crop the 3:1 sides) — NO bars for Runway to inset.
    im = Image.open(still_path).convert("RGB")
    tw, th = FRAME; w, h = im.size; s = max(tw / w, th / h)
    im = im.resize((round(w * s), round(h * s)), Image.LANCZOS); w, h = im.size
    im = im.crop(((w - tw) // 2, (h - th) // 2, (w - tw) // 2 + tw, (h - th) // 2 + th))
    buf = io.BytesIO(); im.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def gen(n, force=False):
    out = OUT / f"clip-{n:02d}.mp4"
    if out.exists() and out.stat().st_size > 10000 and not force:
        print(f"skip clip-{n:02d}"); return
    still = STILLS / f"frame-{n:02d}.png"
    prompt = FPV + MOTION[n] + TAIL
    print(f"gen clip-{n:02d} ... ({MOTION[n][:60]}...)")
    task = client.image_to_video.create(
        model=MODEL,
        prompt_image=[{"position": "first", "uri": fill_data_uri(still)}],
        prompt_text=prompt,
        ratio=RATIO,
        duration=5,
    ).wait_for_task_output(timeout=600)
    if not task.output:
        print(f"clip-{n:02d}: NO OUTPUT"); return
    import httpx
    (OUT / f"clip-{n:02d}.json").write_text(json.dumps({"task_id": getattr(task, "id", None), "output": list(task.output)}, indent=2))
    r = httpx.get(task.output[0], timeout=120); r.raise_for_status()
    out.write_bytes(r.content)
    print(f"OK clip-{n:02d} -> {out.name} ({out.stat().st_size//1024} KB)")


def main():
    force = "--force" in sys.argv
    args = [int(a) for a in sys.argv[1:] if not a.startswith("--")]
    nums = args or list(range(1, 31))
    for n in nums:
        try:
            gen(n, force)
        except TaskFailedError as e:
            print(f"clip-{n:02d}: TASK FAILED {e}")
        except Exception as e:
            print(f"clip-{n:02d}: ERROR {type(e).__name__}: {str(e)[:200]}")


if __name__ == "__main__":
    main()
