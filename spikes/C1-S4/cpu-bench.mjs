// C1-S4 / BUD-CPU-REQ CT micro-benchmark: CPU time (process.cpuUsage) of the same aws4fetch
// presign code and WebCrypto Ed25519 verify, in Node's V8 on this container's x86 CPU.
// NOT Cloudflare Workers CPU time. Throwaway research code.
import { AwsClient } from "aws4fetch";
import os from "node:os";
const client = new AwsClient({ accessKeyId: "AKIDEXAMPLE", secretAccessKey: "not-a-real-secret", service: "s3", region: "auto" });
const base = "https://0123456789abcdef0123456789abcdef.r2.cloudflarestorage.com/rq-ingest/staging/abc/def/s1";
async function presign200() {
  const urls = [];
  for (let i = 1; i <= 200; i++) {
    const u = new URL(base); u.searchParams.set("X-Amz-Expires", "900");
    u.searchParams.set("partNumber", String(i)); u.searchParams.set("uploadId", "x".repeat(120));
    urls.push((await client.sign(new Request(u, { method: "PUT" }), { aws: { signQuery: true } })).url);
  }
  return urls;
}
const cpuMs = (u) => (u.user + u.system) / 1000;
const out = { node: process.version, cpu: os.cpus()[0].model, runs: [] };
for (let i = 0; i < 5; i++) await presign200(); // warm-up (JIT)
for (let r = 0; r < 30; r++) {
  const c0 = process.cpuUsage(); const t0 = performance.now();
  await presign200();
  const c = process.cpuUsage(c0); out.runs.push({ cpu_ms: +cpuMs(c).toFixed(2), wall_ms: +(performance.now() - t0).toFixed(2) });
}
const s = (k) => { const x = out.runs.map((r) => r[k]).sort((a, b) => a - b); return { p50: x[Math.floor(x.length / 2)], max: x[x.length - 1] }; };
out.presign200 = { cpu_ms: s("cpu_ms"), wall_ms: s("wall_ms") };
const kp = await crypto.subtle.generateKey({ name: "Ed25519" }, true, ["sign", "verify"]);
const msg = crypto.getRandomValues(new Uint8Array(256));
const sig = await crypto.subtle.sign({ name: "Ed25519" }, kp.privateKey, msg);
for (let i = 0; i < 2000; i++) await crypto.subtle.verify({ name: "Ed25519" }, kp.publicKey, sig, msg);
const ed = [];
for (let r = 0; r < 5; r++) {
  const c0 = process.cpuUsage(); let ok = 0;
  for (let i = 0; i < 10000; i++) if (await crypto.subtle.verify({ name: "Ed25519" }, kp.publicKey, sig, msg)) ok++;
  ed.push(+(cpuMs(process.cpuUsage(c0)) / 10000).toFixed(5));
}
out.ed25519_verify_cpu_ms_each = ed;
delete out.runs;
console.log(JSON.stringify(out, null, 1));
