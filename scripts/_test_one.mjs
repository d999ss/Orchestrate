// One-shot Veo 3 test render — single frame to validate the pipeline before
// committing to the full $18 run.
//
// Frame: 02a_wind (clean motion, predictable result, low risk)
// Cost: ~$0.50, ~30-90s.

import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

const PROJECT = process.env.GCP_PROJECT;
const LOC = process.env.GCP_LOCATION || "us-central1";
const KEYJSON = process.env.GOOGLE_APPLICATION_CREDENTIALS;
const MODEL = process.env.VEO_MODEL || "veo-3.0-generate-001";
if (!PROJECT || !KEYJSON) {
  console.error("env: source ~/.claude/secrets/orchestrate-veo.env first");
  process.exit(2);
}

const ROOT = path.resolve(import.meta.dirname, "..");
const SRC = path.join(ROOT, "electron", "02a_wind.png");
const OUT = path.join(ROOT, "electron", "_render", "02a_wind.mp4");
fs.mkdirSync(path.dirname(OUT), { recursive: true });

const STYLE = " GE Vernova evergreen halftone dot-matrix aesthetic: fine luminous cyan-teal particle points on deep evergreen-near-black, cinematic, restrained, premium. Smooth accelerating motion. 16:9 cinematic.";
const NEG = "robots, robotic arm, surgery, operating room, airplane, aircraft, control tower, trading floor, financial chart, ticker, dashboard panels, generic screens, faces, crowd; ANY text, letters, words, numbers, glyphs, captions, logos; gold dominance, orange, amber, rainbow, magenta; lens flare, generic stock motion graphics.";
const PROMPT = "Camera slowly tilts up as cyan-teal energy pulses outward from the turbine blade tips, particles streaming into the field." + STYLE;

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

(async () => {
  console.log(`auth · project=${PROJECT} loc=${LOC} model=${MODEL}`);
  const tok = await token();
  console.log("ok · sending Veo i2v request for 02a_wind…");
  const img = fs.readFileSync(SRC).toString("base64");
  const base = `https://${LOC}-aiplatform.googleapis.com/v1/projects/${PROJECT}/locations/${LOC}/publishers/google/models/${MODEL}`;
  const r = await fetch(`${base}:predictLongRunning`, {
    method: "POST", headers: { Authorization: `Bearer ${tok}`, "Content-Type": "application/json" },
    body: JSON.stringify({ instances: [{ prompt: PROMPT, image: { bytesBase64Encoded: img, mimeType: "image/png" } }],
      parameters: { aspectRatio: "16:9", sampleCount: 1, negativePrompt: NEG, personGeneration: "allow_adult", resolution: "1080p", generateAudio: false } }) });
  const op = await r.json();
  if (op?.error) {
    console.error("Veo error:", JSON.stringify(op.error, null, 2));
    process.exit(op.error.code === 429 || op.error.code === 403 ? 7 : 1);
  }
  if (!op?.name) { console.error("no op name:", JSON.stringify(op).slice(0, 400)); process.exit(1); }
  console.log("operation:", op.name);
  for (let i = 0; i < 120; i++) {
    await sleep(8000);
    const pr = await fetch(`${base}:fetchPredictOperation`, {
      method: "POST", headers: { Authorization: `Bearer ${tok}`, "Content-Type": "application/json" },
      body: JSON.stringify({ operationName: op.name }) });
    const p = await pr.json();
    process.stdout.write(p.done ? "DONE\n" : `.${(i+1)*8}s `);
    if (p.error) throw new Error("op err: " + JSON.stringify(p.error));
    if (p.done) {
      const s = p.response?.videos?.[0] || p.response?.generatedSamples?.[0] || p.response?.predictions?.[0];
      const b = s?.bytesBase64Encoded || s?.video?.bytesBase64Encoded;
      if (!b) { console.error("no video bytes:", JSON.stringify(p.response).slice(0, 500)); process.exit(1); }
      fs.writeFileSync(OUT, Buffer.from(b, "base64"));
      const mb = (fs.statSync(OUT).size / 1024 / 1024).toFixed(2);
      console.log(`saved · ${path.relative(ROOT, OUT)} · ${mb} MB`);
      process.exit(0);
    }
  }
  console.error("timeout"); process.exit(1);
})();
