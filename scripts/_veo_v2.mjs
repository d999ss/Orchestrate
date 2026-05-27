// v2 selective re-render — only the 7 beats that didn't land in v1.
// Beat 05 (a/b/c): Veo invented UI labels — strengthened "no text/no UI" negation.
// Beat 07 (a/b/c): "gold burst" prompt produced UFO/disc — switched to cyan-pure energy.
// Beat 09c: hero hold needs cleaner negative-space frame for title overlay in compose.
//
// Outputs to electron/_render_v2/ (separate from v1).

import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

const PROJECT = process.env.GCP_PROJECT;
const LOC = process.env.GCP_LOCATION || "us-central1";
const KEYJSON = process.env.GOOGLE_APPLICATION_CREDENTIALS;
const MODEL = process.env.VEO_MODEL || "veo-3.0-generate-001";
if (!PROJECT || !KEYJSON) { console.error("env: source orchestrate-veo.env first"); process.exit(2); }

const ROOT = path.resolve(import.meta.dirname, "..");
const SRC = path.join(ROOT, "electron");
const OUT = path.join(ROOT, "electron", "_render_v2");
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

const STYLE = " GE Vernova evergreen halftone dot-matrix aesthetic: fine luminous cyan-teal particle points on deep evergreen-near-black, cinematic, restrained, premium. 16:9 cinematic.";
// Strengthened NEG for v2 — explicitly bans UI text and gold-discs.
const NEG = "ANY text, ANY letters, ANY words, ANY numbers, ANY glyphs, ANY captions, ANY UI labels, ANY interface panels, ANY dashboards with text, ANY readable strings; gold discs, gold rings, satellite dishes, UFOs, parabolic reflectors, radar dishes, antennas; robots, robotic arm, faces, crowd, hospital, surgery, aircraft, control tower, financial chart, ticker; orange, amber, yellow dominance, magenta, rainbow; lens flare, generic stock motion graphics.";

const JOBS = [
  ["05a_paths_fan",  "Cyan and lime path lines fan radially from a single bright junction point — pure abstract decision space, just paths and particle field. NO UI panels, NO text labels, NO words." + STYLE],
  ["05b_gridos",     "Cascading cyan-lime data flows shimmer and animate across an evergreen halftone field — pure abstract intelligence visualization. NO interface text, NO panels, NO words, NO numbers, NO labels, NO buttons." + STYLE],
  ["05c_path_chosen","One single bright cyan path locks in across the evergreen field — all other paths dim and fade. Pure abstract choice moment, just light paths, NO text, NO UI." + STYLE],
  ["07a_gold_burst", "A bright cyan radial burst at the center of an evergreen halftone particle field — particles flying outward in all directions. Pure cyan energy, NO gold, NO discs, NO satellites, NO UFOs, NO objects." + STYLE],
  ["07b_lime_ripple","A bright lime green ripple pulse travels outward through the cyan dot-matrix grid — concentric expanding energy waves, abstract." + STYLE],
  ["07c_climax",     "A single climactic flash where lime green and cyan converge at one peak point in the evergreen halftone field — pure light convergence, no objects, no discs." + STYLE],
  ["09c_hero_hold",  "Sustained hero hold: an evergreen halftone particle field with a soft cyan particle bloom slightly left-of-center — clean dark negative space top-right, calm breath, suitable for a brand mark overlay. No text, no UI." + STYLE],
];

const base = `https://${LOC}-aiplatform.googleapis.com/v1/projects/${PROJECT}/locations/${LOC}/publishers/google/models/${MODEL}`;
let blocked = false;

async function veo(tok, name, prompt) {
  const startPng = path.join(SRC, `${name}.png`);
  const outMp4 = path.join(OUT, `${name}.mp4`);
  if (!fs.existsSync(startPng)) { console.log(name, "MISSING START PNG"); return; }
  if (fs.existsSync(outMp4) && fs.statSync(outMp4).size > 5e5) { console.log(name, "cached, skip"); return; }
  const img = fs.readFileSync(startPng).toString("base64");
  const r = await fetch(`${base}:predictLongRunning`, {
    method: "POST", headers: { Authorization: `Bearer ${tok}`, "Content-Type": "application/json" },
    body: JSON.stringify({ instances: [{ prompt, image: { bytesBase64Encoded: img, mimeType: "image/png" } }],
      parameters: { aspectRatio: "16:9", sampleCount: 1, negativePrompt: NEG, personGeneration: "allow_adult", resolution: "1080p", generateAudio: false } }) });
  const op = await r.json();
  if (op?.error?.code === 429 || op?.error?.status === "RESOURCE_EXHAUSTED" || op?.error?.code === 403) {
    blocked = true; console.log(name, `BLOCKED ${op.error.code}`); return; }
  if (!op?.name) throw new Error(`${name} start: ` + JSON.stringify(op).slice(0, 400));
  console.log(name, "started…");
  for (let i = 0; i < 120; i++) {
    await sleep(8000);
    const pr = await fetch(`${base}:fetchPredictOperation`, {
      method: "POST", headers: { Authorization: `Bearer ${tok}`, "Content-Type": "application/json" },
      body: JSON.stringify({ operationName: op.name }) });
    const p = await pr.json();
    if (p.error) throw new Error(`${name} op: ` + JSON.stringify(p.error).slice(0, 300));
    if (p.done) {
      const s = p.response?.videos?.[0] || p.response?.generatedSamples?.[0] || p.response?.predictions?.[0];
      const b = s?.bytesBase64Encoded || s?.video?.bytesBase64Encoded;
      if (!b) throw new Error(`${name}: no video bytes`);
      fs.writeFileSync(outMp4, Buffer.from(b, "base64"));
      console.log(name, `OK · ${(fs.statSync(outMp4).size/1024/1024).toFixed(2)} MB`);
      return;
    }
  }
  throw new Error(`${name}: timeout`);
}

(async () => {
  const tok = await token();
  console.log(`auth ok · project=${PROJECT} model=${MODEL}`);
  for (const [name, prompt] of JOBS) {
    if (blocked) break;
    try { await veo(tok, name, prompt); }
    catch (e) { console.error(name, "FAILED:", e.message); }
  }
  process.exit(blocked ? 7 : 0);
})();
