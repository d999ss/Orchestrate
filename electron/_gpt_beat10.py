#!/usr/bin/env python3
"""Beat 10 'THE CONFERENCE' — three additional frames in the
point-cloud language, mirroring the Signal board's keynote
sequence but rendered in the new aesthetic."""
import json, base64, ssl, urllib.request
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import certifi
SSL_CTX = ssl.create_default_context(cafile=certifi.where())
KEY = json.loads(Path.home().joinpath(".claude/secrets.json").read_text())["openai"]["api_key"]
OUT = Path(__file__).parent

BRAND = (
    " Rendered as a true volumetric point cloud — tiny dim pale mint-"
    "cyan particulate grains floating in 3D space, the interior visible "
    "through density. Scale variation: dust-fine stippling drifts in "
    "the empty space; medium structural points trace only the most "
    "prominent forms; rare faintly brighter pinpoints at intersections. "
    "Vast deep evergreen near-black void around the subject. NO crisp "
    "silhouette, NO perimeter — every edge fades into darkness. "
    "Villeneuve / Deakins cinematic darkness — premium, restrained, "
    "almost camouflaged. Built like an incomplete LiDAR scan + electron "
    "microscopy + astrophotography. Calm industrial intelligence. "
    "Absolutely NO text, NO logos, NO brand marks, NO wordmarks, NO "
    "signage, NO UI, NO HUD, NO photo-real, NO hologram, NO wireframe, "
    "NO neon glow, NO yellow, NO amber, NO orange, NO gold, NO lime, "
    "NO white background, NO bright sky. 16:9."
)

SHOTS = [
    ("10a_conference_dawn",
     "Aerial three-quarter point-cloud rendering of a long modern "
     "conference venue exterior at pre-dawn — a wide low building with "
     "a sloped curtain-wall facade and a forecourt, a small dispersed "
     "crowd of attendees walking in from the right. Building, "
     "landscape, and attendees ALL rendered in the SAME volumetric "
     "particulate dust language — no figure stands out as photographic. "
     "Faint pre-dawn warmth on the right horizon is implied only by a "
     "very slight density warm-shift, not by color saturation. The "
     "building is 50% dissolved into the evergreen darkness — only the "
     "strongest structural lines and roofline register. Subject "
     "occupies the lower-center of the frame; vast empty atmospheric "
     "space above."),

    ("10b_stage_lit",
     "Cinematic interior of the Orchestrate 2026 keynote hall viewed "
     "from the rear of the room down the center aisle. The room has a "
     "very specific architecture: ONE single wide rectangular screen "
     "spanning nearly the full width of the stage at the front (no "
     "side panels), tall fabric curtain drapes on the LEFT and RIGHT "
     "side walls of the room, a modern dropped ceiling with two large "
     "angled cove panels and strip lighting, and THREE audience "
     "sections of chairs angled inward toward a single wide center "
     "aisle that leads to the stage. Audience silhouettes occupy the "
     "chairs facing forward, with a small lone presenter figure "
     "standing on stage in front of the screen. The stage screen "
     "itself shows a soft mint-cyan particle cluster (NO text, NO "
     "logos, NO wordmarks — only an abstract drifting particle field). "
     "EVERYTHING — chairs, audience, presenter, curtains, ceiling, "
     "stage, screen — is rendered in the SAME volumetric point-cloud "
     "dust language: mint-cyan particulate grains against deep "
     "evergreen near-black darkness. Audience as particle silhouettes "
     "from behind. The whole scene is 50% dissolved, atmospheric, "
     "premium restraint. Strong central-aisle perspective into the "
     "hall."),

    ("10c_hero_brand",
     "A vast deep evergreen near-black field. On the LEFT third of the "
     "frame: a soft, glowing cluster of mint-cyan particulate dust — "
     "restrained, atmospheric, mostly drift with no defined shape, "
     "almost an aurora of particles. The entire RIGHT two-thirds of "
     "the frame is empty negative space — pure deep evergreen void "
     "with the faintest atmospheric particle drift — prepared as a "
     "clean canvas for a brand mark to be overlaid in post. The "
     "left-side particle cluster is the only feature in the frame. "
     "Premium, restrained, very dark."),
]

def gen(name, prompt):
    body = json.dumps({"model":"gpt-image-1","prompt":prompt+BRAND,
                       "size":"1536x1024","n":1,"quality":"high"}).encode()
    r = urllib.request.urlopen(urllib.request.Request(
        "https://api.openai.com/v1/images/generations",
        data=body, headers={"Authorization":f"Bearer {KEY}",
                            "Content-Type":"application/json"}),
        timeout=600, context=SSL_CTX).read()
    data = json.loads(r)["data"][0]["b64_json"]
    out = OUT / f"{name}.png"
    out.write_bytes(base64.b64decode(data))
    return (name, out.stat().st_size)

with ThreadPoolExecutor(max_workers=3) as ex:
    futs = {ex.submit(gen, n, p): n for n, p in SHOTS}
    for f in as_completed(futs):
        n, size = f.result()
        print(f"  {n:24} OK {size:,}B")
print("done.")
