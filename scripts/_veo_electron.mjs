// Generate beats 02-09 (24 clips) for The Electron via Vertex Veo 3 Fast i2v.
// Beat 01 already covered by electron/chain_test.mp4.
//
// Env required:
//   GCP_PROJECT=orchestrate-veo
//   GCP_LOCATION=us-central1                 (default)
//   GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa-key.json
//   VEO_MODEL=veo-3.0-fast-generate-001      (default)
//
// Run: source ~/.claude/secrets/orchestrate-veo.env && node scripts/_veo_electron.mjs
//
// Output: electron/_render/<shot>.mp4 (8s, 16:9). Idempotent (skips existing
// >0.5MB), 429-aware, exits 7 if blocked so a /loop can keep probing.

import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

const PROJECT = process.env.GCP_PROJECT;
const LOC = process.env.GCP_LOCATION || "us-central1";
const KEYJSON = process.env.GOOGLE_APPLICATION_CREDENTIALS;
// Standard Veo 3 outputs 1080p native; Fast outputs 720p. We want 1080p so the
// Topaz 2× upscale to 4K is clean. Override with VEO_MODEL if needed.
const MODEL = process.env.VEO_MODEL || "veo-3.0-generate-001";
if (!PROJECT || !KEYJSON) {
  console.error("env: need GCP_PROJECT + GOOGLE_APPLICATION_CREDENTIALS");
  console.error("hint: source ~/.claude/secrets/orchestrate-veo.env");
  process.exit(2);
}

const ROOT = path.resolve(import.meta.dirname, "..");
const SRC = path.join(ROOT, "electron");
const OUT = path.join(ROOT, "electron", "_render");
fs.mkdirSync(OUT, { recursive: true });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const b64url = (b) => Buffer.from(b).toString("base64url");

async function token() {
  const sa = JSON.parse(fs.readFileSync(KEYJSON, "utf8"));
  const now = Math.floor(Date.now() / 1000);
  const claim = {
    iss: sa.client_email,
    scope: "https://www.googleapis.com/auth/cloud-platform",
    aud: "https://oauth2.googleapis.com/token",
    iat: now, exp: now + 3600
  };
  const head = b64url(JSON.stringify({ alg: "RS256", typ: "JWT" }));
  const body = b64url(JSON.stringify(claim));
  const sig = crypto.createSign("RSA-SHA256").update(`${head}.${body}`).sign(sa.private_key);
  const jwt = `${head}.${body}.${b64url(sig)}`;
  const r = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: `grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Ajwt-bearer&assertion=${jwt}`
  });
  const j = await r.json();
  if (!j.access_token) throw new Error("token: " + JSON.stringify(j).slice(0, 300));
  return j.access_token;
}

const STYLE = " GE Vernova evergreen halftone dot-matrix aesthetic: fine luminous cyan-teal particle points on deep evergreen-near-black, cinematic, restrained, premium. Smooth accelerating motion. 16:9 cinematic.";
const NEG = "robots, robotic arm, surgery, operating room, airplane, aircraft, control tower, trading floor, financial chart, ticker, dashboard panels, generic screens, faces, crowd; ANY text, letters, words, numbers, glyphs, captions, logos; gold dominance, orange, amber, rainbow, magenta; lens flare, generic stock motion graphics.";

// 24 jobs · 8 beats × 3 frames. Beat 01 lives in electron/chain_test.mp4.
const JOBS = [
  ["02a_wind",             "Camera slowly tilts up as cyan-teal energy pulses outward from the turbine blade tips, particles streaming into the field." + STYLE],
  ["02b_solar",            "Cyan and lime data points cascade eastward across the panel array following the dawn light, accelerating." + STYLE],
  ["02c_hydro",            "Cyan-teal water-data streams release downward through the halftone field, gathering momentum, current accelerating into the grid." + STYLE],

  ["03a_dense_field",      "The cyan particle swarm intensifies and concentrates inward, energy compressing toward a single point." + STYLE],
  ["03b_grid_order",       "Particles snap rapidly into a regular dot-matrix lattice — order emerging from chaos in a single decisive moment." + STYLE],
  ["03c_grid_perspective", "The dot-matrix grid tilts and recedes into deep three-dimensional space, evergreen depth opening up." + STYLE],

  ["04a_first_links",      "Bright cyan link lines progressively draw themselves between nodes — the network animating into being, link by link." + STYLE],
  ["04b_radiating_node",   "From the central glowing node, cyan starburst lines radiate outward in a continuous pulsing rhythm." + STYLE],
  ["04c_full_mesh",        "The complete mesh network pulses in unison — every link visible, every node lit, intelligence at full clarity." + STYLE],

  ["05a_paths_fan",        "Cyan and lime path lines fan out radially from one junction, each path probing forward, decision space expanding." + STYLE],
  ["05b_gridos",           "Cascading cyan-lime calculations animate across the intelligence layer, data flows shimmering, decision resolving." + STYLE],
  ["05c_path_chosen",      "All paths dim except one — a single bright cyan path locks in, lime confidence glyph pulses beside it." + STYLE],

  ["06a_comet",            "A cyan-teal comet trail sweeps across the field with momentum, particles trailing in its wake." + STYLE],
  ["06b_currents",         "Multiple cyan currents weave and cross each other smoothly, directional flow continuous." + STYLE],
  ["06c_aurora",           "A graceful cyan-and-lime aurora curves and undulates across the entire frame, slow majestic motion." + STYLE],

  ["07a_gold_burst",       "A bright cyan-and-lime radial burst (cyan-dominant, not gold) expands outward, particles flying, energy building toward peak." + STYLE],
  ["07b_lime_ripple",      "A bright lime ripple pulse travels outward through the cyan dot-matrix grid, anticipation rising." + STYLE],
  ["07c_climax",           "Lime green and cyan converge at one peak point — climactic flash, charge concentrating." + STYLE],

  ["08a_atlanta",          "Camera reveals Mercedes-Benz Stadium's eight-petal pinwheel roof in faceted halftone — the city dot-matrix lights ignite around it, building to peak intensity." + STYLE],
  ["08b_distribution",     "Cyan pulses travel along distribution lines into halftone neighborhoods — light spreading out, the region waking." + STYLE],
  ["08c_aerial_sweep",     "Sweeping high aerial across the regional grid network, every node pulsing in cyan-teal unison at peak intensity." + STYLE],

  ["09a_venue_dawn",       "Calm slow dolly toward the conference venue exterior at dawn, abstract halftone silhouettes drifting in, anticipatory." + STYLE],
  ["09b_keynote_stage",    "Camera pushes into the keynote hall — stage screens animating with cyan-lime brand visuals, room quiet and held." + STYLE],
  ["09c_hero_hold",        "Final hero hold — soft cyan particle burst at center, faint lime accents, sustained breath. Negative space top-right for the ORCHESTRATE mark." + STYLE],
];

const base = `https://${LOC}-aiplatform.googleapis.com/v1/projects/${PROJECT}/locations/${LOC}/publishers/google/models/${MODEL}`;
let blocked = false;

async function veo(tok, name, prompt) {
  const startPng = path.join(SRC, `${name}.png`);
  const outMp4 = path.join(OUT, `${name}.mp4`);
  if (!fs.existsSync(startPng)) { console.log(name, "MISSING START PNG, skip"); return; }
  if (fs.existsSync(outMp4) && fs.statSync(outMp4).size > 5e5) { console.log(name, "cached, skip"); return; }
  const img = fs.readFileSync(startPng).toString("base64");
  const r = await fetch(`${base}:predictLongRunning`, {
    method: "POST",
    headers: { Authorization: `Bearer ${tok}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      instances: [{ prompt, image: { bytesBase64Encoded: img, mimeType: "image/png" } }],
      parameters: { aspectRatio: "16:9", sampleCount: 1, negativePrompt: NEG, personGeneration: "allow_adult", resolution: "1080p", generateAudio: false }
    })
  });
  const op = await r.json();
  if (op?.error?.code === 429 || op?.error?.status === "RESOURCE_EXHAUSTED" || op?.error?.code === 403) {
    blocked = true;
    console.log(name, `BLOCKED ${op.error.code} — ${op.error.status}`);
    return;
  }
  if (!op?.name) throw new Error(`${name} start: ` + JSON.stringify(op).slice(0, 400));
  console.log(name, "started…");
  for (let i = 0; i < 90; i++) {
    await sleep(10000);
    const pr = await fetch(`${base}:fetchPredictOperation`, {
      method: "POST",
      headers: { Authorization: `Bearer ${tok}`, "Content-Type": "application/json" },
      body: JSON.stringify({ operationName: op.name })
    });
    const p = await pr.json();
    if (p.error) throw new Error(`${name} op: ` + JSON.stringify(p.error).slice(0, 300));
    if (p.done) {
      const s = p.response?.videos?.[0] || p.response?.generatedSamples?.[0] || p.response?.predictions?.[0];
      const b = s?.bytesBase64Encoded || s?.video?.bytesBase64Encoded;
      if (!b) throw new Error(`${name}: no video bytes in response`);
      fs.writeFileSync(outMp4, Buffer.from(b, "base64"));
      console.log(name, `OK → ${path.relative(ROOT, outMp4)} (${(fs.statSync(outMp4).size/1024/1024).toFixed(2)} MB)`);
      return;
    }
  }
  throw new Error(`${name}: timeout waiting for video`);
}

(async () => {
  const tok = await token();
  console.log(`auth ok · project=${PROJECT} loc=${LOC} model=${MODEL}`);
  for (const [name, prompt] of JOBS) {
    if (blocked) { console.log("blocked, abandoning loop"); break; }
    try { await veo(tok, name, prompt); }
    catch (e) { console.error(name, "FAILED:", e.message); }
  }
  process.exit(blocked ? 7 : 0);
})();
