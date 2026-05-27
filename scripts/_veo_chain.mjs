// End-frame chained re-render — fixes "clips don't connect" by using each
// generated clip's last frame as the next clip's start frame. This is the
// technique that made chain_test.mp4 feel continuous across beats 01A→C.
//
// Sequential, can't parallelize. ~$18 + ~40 min.
// Output: electron/_render_chain/*.mp4 (1080p)

import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { spawn } from "node:child_process";

const PROJECT = process.env.GCP_PROJECT;
const LOC = process.env.GCP_LOCATION || "us-central1";
const KEYJSON = process.env.GOOGLE_APPLICATION_CREDENTIALS;
const MODEL = process.env.VEO_MODEL || "veo-3.0-generate-001";
if (!PROJECT || !KEYJSON) { console.error("source orchestrate-veo.env first"); process.exit(2); }

const ROOT = path.resolve(import.meta.dirname, "..");
const SRC = path.join(ROOT, "electron");
const OUT = path.join(ROOT, "electron", "_render_chain");
fs.mkdirSync(OUT, { recursive: true });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const b64url = (b) => Buffer.from(b).toString("base64url");

async function token() {
  const sa = JSON.parse(fs.readFileSync(KEYJSON, "utf8"));
  const now = Math.floor(Date.now() / 1000);
  const claim = { iss: sa.client_email, scope: "https://www.googleapis.com/auth/cloud-platform",
    aud: "https://oauth2.googleapis.com/token", iat: now, exp: now + 3600 };
  const head = b64url(JSON.stringify({ alg: "RS256", typ: "JWT" }));
  const body = b64url(JSON.stringify(claim));
  const sig = crypto.createSign("RSA-SHA256").update(`${head}.${body}`).sign(sa.private_key);
  const jwt = `${head}.${body}.${b64url(sig)}`;
  const r = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: `grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Ajwt-bearer&assertion=${jwt}` });
  const j = await r.json();
  if (!j.access_token) throw new Error("token: " + JSON.stringify(j).slice(0, 300));
  return j.access_token;
}

// Extract the last frame of an mp4 to a PNG (for chaining).
function extractLastFrame(mp4Path, pngPath) {
  return new Promise((resolve, reject) => {
    const p = spawn("ffmpeg", [
      "-hide_banner", "-loglevel", "error", "-y",
      "-sseof", "-0.3", "-i", mp4Path,
      "-update", "1", "-frames:v", "1",
      pngPath,
    ]);
    p.on("close", (code) => code === 0 ? resolve() : reject(new Error(`ffmpeg ${code}`)));
  });
}

const STYLE = " GE Vernova evergreen halftone dot-matrix aesthetic: cyan-teal particle points on deep evergreen-near-black, cinematic, restrained. Continuous flowing motion. 16:9.";
const NEG = "ANY text, ANY letters, ANY words, ANY numbers, ANY UI labels, ANY interface panels; gold discs, satellite dishes, UFOs; robots, faces, crowd; lens flare.";

// Each entry: [name, motion_prompt]. Source PNG comes from electron/{name}.png
// for the FIRST clip and from the previous clip's last frame for the rest.
const JOBS = [
  ["02a_wind",             "Camera tilts up as cyan energy pulses outward from the turbine blade tips, particles streaming into the field continuously."],
  ["02b_solar",            "The energy flows forward across the solar array, cyan and lime data points cascading eastward."],
  ["02c_hydro",            "The flow accelerates downward through the hydro release, cyan-teal water-data streams gathering momentum."],
  ["03a_dense_field",      "The cyan particle swarm intensifies and concentrates inward, energy compressing toward a single point."],
  ["03b_grid_order",       "Particles snap rapidly into a regular dot-matrix lattice, order emerging from chaos in one decisive moment."],
  ["03c_grid_perspective", "The dot-matrix grid tilts and recedes into deep three-dimensional space, evergreen depth opening up."],
  ["04a_first_links",      "Bright cyan link lines progressively draw themselves between nodes, the network animating into being."],
  ["04b_radiating_node",   "From the central node, cyan starburst lines radiate outward in continuous pulsing rhythm."],
  ["04c_full_mesh",        "The full mesh network pulses in unison, every link visible, every node lit."],
  ["05a_paths_fan",        "Cyan and lime path lines fan out radially, decision space expanding."],
  ["05b_gridos",           "Cascading cyan-lime data flows animate across the intelligence layer."],
  ["05c_path_chosen",      "All paths dim except one, a single bright cyan path locking in."],
  ["06a_comet",            "A cyan comet trail sweeps across the field with momentum."],
  ["06b_currents",         "Multiple cyan currents weave and cross smoothly, continuous flow."],
  ["06c_aurora",           "A cyan-and-lime aurora curves across the entire frame, slow majestic motion."],
  ["07a_gold_burst",       "A cyan radial burst expands outward, particles flying, energy building."],
  ["07b_lime_ripple",      "A lime ripple pulse travels outward through the cyan grid, anticipation rising."],
  ["07c_climax",           "Lime and cyan converge at one peak point, climactic flash."],
  ["08a_atlanta",          "Camera reveals the faceted Mercedes-Benz Stadium silhouette as city dot-matrix lights ignite around it."],
  ["08b_distribution",     "Cyan pulses travel along distribution lines into halftone neighborhoods."],
  ["08c_aerial_sweep",     "Sweeping high aerial across the regional grid, every node pulsing in cyan unison."],
  ["09a_venue_dawn",       "Calm slow dolly toward the conference venue exterior at dawn."],
  ["09b_keynote_stage",    "Camera pushes into the keynote hall, stage screens animating with brand visuals."],
  ["09c_hero_hold",        "Final hero hold, soft cyan particle bloom slightly left-of-center, sustained breath."],
];

const base = `https://${LOC}-aiplatform.googleapis.com/v1/projects/${PROJECT}/locations/${LOC}/publishers/google/models/${MODEL}`;

async function veo(tok, startPng, prompt, outMp4) {
  if (fs.existsSync(outMp4) && fs.statSync(outMp4).size > 5e5) {
    console.log(path.basename(outMp4), "cached, skip"); return true;
  }
  const img = fs.readFileSync(startPng).toString("base64");
  const r = await fetch(`${base}:predictLongRunning`, {
    method: "POST", headers: { Authorization: `Bearer ${tok}`, "Content-Type": "application/json" },
    body: JSON.stringify({ instances: [{ prompt: prompt + STYLE, image: { bytesBase64Encoded: img, mimeType: "image/png" } }],
      parameters: { aspectRatio: "16:9", sampleCount: 1, negativePrompt: NEG, personGeneration: "allow_adult", resolution: "1080p", generateAudio: false } }) });
  const op = await r.json();
  if (op?.error) {
    if (op.error.code === 429 || op.error.code === 403) { console.log("BLOCKED", op.error.status); return false; }
    throw new Error(JSON.stringify(op.error).slice(0, 400));
  }
  console.log(path.basename(outMp4), "started…");
  for (let i = 0; i < 120; i++) {
    await sleep(8000);
    const pr = await fetch(`${base}:fetchPredictOperation`, {
      method: "POST", headers: { Authorization: `Bearer ${tok}`, "Content-Type": "application/json" },
      body: JSON.stringify({ operationName: op.name }) });
    const p = await pr.json();
    if (p.error) throw new Error("op: " + JSON.stringify(p.error));
    if (p.done) {
      const s = p.response?.videos?.[0] || p.response?.generatedSamples?.[0] || p.response?.predictions?.[0];
      const b = s?.bytesBase64Encoded || s?.video?.bytesBase64Encoded;
      if (!b) throw new Error("no video");
      fs.writeFileSync(outMp4, Buffer.from(b, "base64"));
      console.log(path.basename(outMp4), `OK · ${(fs.statSync(outMp4).size/1024/1024).toFixed(1)} MB`);
      return true;
    }
  }
  throw new Error("timeout");
}

(async () => {
  const tok = await token();
  console.log(`auth · ${PROJECT} · ${MODEL}`);
  // First clip: start from the last frame of chain_test (beats 01 end).
  let prevMp4 = path.join(SRC, "chain_test.mp4");
  for (let i = 0; i < JOBS.length; i++) {
    const [name, prompt] = JOBS[i];
    const outMp4 = path.join(OUT, `${name}.mp4`);
    // Extract previous clip's last frame as this clip's start.
    const startPng = path.join(OUT, `_start_${name}.png`);
    await extractLastFrame(prevMp4, startPng);
    const ok = await veo(tok, startPng, prompt, outMp4);
    if (!ok) { console.log("aborting chain"); process.exit(7); }
    prevMp4 = outMp4;
  }
  console.log("\nchain complete · 24 clips");
})();
