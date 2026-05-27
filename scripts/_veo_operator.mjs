// Animate the GridOS "In Context" references — operator at console + control
// room wall. Subtle motion only (screen flicker, atmospheric particle drift,
// micro head movement). These slot into the Decision section of the film
// where GridOS UI shows.

import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

const PROJECT = process.env.GCP_PROJECT;
const LOC = process.env.GCP_LOCATION || "us-central1";
const KEYJSON = process.env.GOOGLE_APPLICATION_CREDENTIALS;
const MODEL = process.env.VEO_MODEL || "veo-3.0-generate-001";
if (!PROJECT || !KEYJSON) { console.error("source orchestrate-veo.env"); process.exit(2); }

const ROOT = path.resolve(import.meta.dirname, "..");
const REFS = path.join(ROOT, "references");
const OUT = path.join(ROOT, "electron", "_render_operator");
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

const NEG = "face distortion, melting, multiple heads, extra limbs, twisting, deformed hands, glitching face; cartoon, anime, illustration; gold dominance, magenta, rainbow; lens flare.";

const JOBS = [
  {
    src: "gridos-operator.jpeg",
    out: "operator_console.mp4",
    prompt: "Subtle cinematic motion: the operator sits still watching the GridOS screens, only a slight micro-shift in posture. Screens softly animate with cyan data shimmer and live charts updating. Atmospheric dust particles drift slowly through the room lighting. Slow camera dolly forward by a few centimeters. Calm focus. Photorealistic. 16:9 cinematic.",
  },
  {
    src: "gridos-control-room.jpeg",
    out: "control_room_wall.mp4",
    prompt: "Wide control room wall with curved multi-display. Screens animate subtly — charts update, network maps pulse with cyan data, oscillation timelines tick forward. Slow camera dolly forward toward the wall. Calm restraint. Photorealistic. 16:9 cinematic.",
  },
];

const base = `https://${LOC}-aiplatform.googleapis.com/v1/projects/${PROJECT}/locations/${LOC}/publishers/google/models/${MODEL}`;

async function veo(tok, job) {
  const srcPath = path.join(REFS, job.src);
  const outPath = path.join(OUT, job.out);
  if (fs.existsSync(outPath) && fs.statSync(outPath).size > 5e5) { console.log(job.out, "cached"); return true; }
  const img = fs.readFileSync(srcPath).toString("base64");
  const mime = job.src.endsWith(".png") ? "image/png" : "image/jpeg";
  const r = await fetch(`${base}:predictLongRunning`, {
    method: "POST", headers: { Authorization: `Bearer ${tok}`, "Content-Type": "application/json" },
    body: JSON.stringify({ instances: [{ prompt: job.prompt, image: { bytesBase64Encoded: img, mimeType: mime } }],
      parameters: { aspectRatio: "16:9", sampleCount: 1, negativePrompt: NEG, personGeneration: "allow_adult", resolution: "1080p", generateAudio: false } }) });
  const op = await r.json();
  if (op?.error) {
    console.error(job.out, "error:", JSON.stringify(op.error).slice(0, 300));
    if (op.error.code === 429 || op.error.code === 403) return false;
    throw new Error(op.error.message);
  }
  console.log(job.out, "started…");
  for (let i = 0; i < 120; i++) {
    await sleep(8000);
    const pr = await fetch(`${base}:fetchPredictOperation`, {
      method: "POST", headers: { Authorization: `Bearer ${tok}`, "Content-Type": "application/json" },
      body: JSON.stringify({ operationName: op.name }) });
    const p = await pr.json();
    if (p.error) throw new Error(JSON.stringify(p.error));
    if (p.done) {
      const s = p.response?.videos?.[0] || p.response?.generatedSamples?.[0] || p.response?.predictions?.[0];
      const b = s?.bytesBase64Encoded || s?.video?.bytesBase64Encoded;
      if (!b) {
        // Possibly RAI filter — try without negativePrompt
        console.error(job.out, "no bytes, response:", JSON.stringify(p.response).slice(0, 400));
        throw new Error("no video");
      }
      fs.writeFileSync(outPath, Buffer.from(b, "base64"));
      console.log(job.out, `OK · ${(fs.statSync(outPath).size/1024/1024).toFixed(1)} MB`);
      return true;
    }
  }
  throw new Error("timeout");
}

(async () => {
  const tok = await token();
  console.log(`auth · ${PROJECT}`);
  for (const job of JOBS) {
    try { await veo(tok, job); }
    catch (e) { console.error(job.out, "FAILED:", e.message); }
  }
})();
