// Generate dot-matrix industrial subjects via Vertex Imagen.
// Output: electron/_dotmatrix/dm_<name>.png

import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

const PROJECT = process.env.GCP_PROJECT;
const LOC = process.env.GCP_LOCATION || "us-central1";
const KEYJSON = process.env.GOOGLE_APPLICATION_CREDENTIALS;
const MODEL = "imagen-3.0-generate-002";
if (!PROJECT || !KEYJSON) { console.error("source orchestrate-veo.env first"); process.exit(2); }

const ROOT = path.resolve(import.meta.dirname, "..");
const OUT = path.join(ROOT, "electron", "_dotmatrix");
fs.mkdirSync(OUT, { recursive: true });

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

const STYLE = " Rendered in cyan-teal dot-matrix particle structure on deep black background. Every surface made of discrete luminous particle points. Halftone dot-matrix wireframe. Photorealistic dots. Industrial cinema. Evergreen and cyan-teal only, no other colors. Crisp geometric structure. 16:9 cinematic.";

const JOBS = [
  ["wind_turbine",   "A wind turbine with three angled blades, viewed from a low cinematic angle." + STYLE],
  ["solar_array",    "An array of solar panels stretching to the horizon, low aerial view." + STYLE],
  ["hydro_dam",      "A hydroelectric dam releasing water through spillways." + STYLE],
  ["transmission",   "Transmission towers carrying power lines across a landscape at night, lit network of cyan dots flowing along the lines." + STYLE],
  ["substation",    "An electrical substation with transformers and breakers, network nodes visible." + STYLE],
  ["network_mesh",   "An interconnected network of glowing nodes connected by lines, abstract mesh in 3D space." + STYLE],
  ["city_grid",      "A city skyline at night with grid of power lines extending in perspective, every building outlined in dots." + STYLE],
  ["aerial_sweep",   "A sweeping aerial view of a regional power grid network with substations and transmission lines glowing." + STYLE],
];

const base = `https://${LOC}-aiplatform.googleapis.com/v1/projects/${PROJECT}/locations/${LOC}/publishers/google/models/${MODEL}`;

async function gen(tok, name, prompt) {
  const outPng = path.join(OUT, `dm_${name}.png`);
  if (fs.existsSync(outPng) && fs.statSync(outPng).size > 50000) { console.log(name, "cached"); return; }
  const r = await fetch(`${base}:predict`, {
    method: "POST", headers: { Authorization: `Bearer ${tok}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      instances: [{ prompt }],
      parameters: { sampleCount: 1, aspectRatio: "16:9", safetyFilterLevel: "block_only_high", personGeneration: "allow_adult" }
    })
  });
  const j = await r.json();
  if (j.error) {
    console.error(name, "ERROR:", JSON.stringify(j.error).slice(0, 300));
    return;
  }
  const pred = j.predictions?.[0];
  const b64 = pred?.bytesBase64Encoded;
  if (!b64) {
    console.error(name, "no image:", JSON.stringify(j).slice(0, 300));
    return;
  }
  fs.writeFileSync(outPng, Buffer.from(b64, "base64"));
  console.log(name, `OK · ${(fs.statSync(outPng).size/1024).toFixed(0)} KB`);
}

(async () => {
  const tok = await token();
  console.log(`auth · ${PROJECT} · ${MODEL}`);
  for (const [name, prompt] of JOBS) {
    try { await gen(tok, name, prompt); }
    catch (e) { console.error(name, "FAILED:", e.message); }
  }
})();
