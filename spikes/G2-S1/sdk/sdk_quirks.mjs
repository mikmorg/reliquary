// G2-S1: does an off-the-shelf AWS SDK (JS v3) work against a target with default settings?
// Usage: node sdk_quirks.mjs <name> <endpoint> <bucket> <region> <ak> <sk>
import { S3Client, PutObjectCommand, GetObjectCommand, CreateMultipartUploadCommand, UploadPartCommand, CompleteMultipartUploadCommand } from "@aws-sdk/client-s3";
import { getSignedUrl } from "@aws-sdk/s3-request-presigner";
import { createHash, randomBytes } from "node:crypto";
import { Readable } from "node:stream";
const [name, endpoint, Bucket, region, ak, sk] = process.argv.slice(2);
const sha = (b) => createHash("sha256").update(b).digest("hex");
const mk = (extra = {}) => new S3Client({ endpoint, region, forcePathStyle: true, credentials: { accessKeyId: ak, secretAccessKey: sk }, maxAttempts: 1, ...extra });
const withTimeout = (p, ms) => Promise.race([p, new Promise((_, rej) => setTimeout(() => rej(new Error(`timeout ${ms} ms`)), ms))]);
const run = Date.now().toString(36);
const out = { target: name, sdk: "@aws-sdk/client-s3 3.1142.0", results: [] };
async function check(id, title, fn) {
  const t0 = Date.now();
  try { const r = await withTimeout(fn(), 20000); out.results.push({ id, title, ok: true, ms: Date.now() - t0, ...r }); }
  catch (e) { out.results.push({ id, title, ok: false, ms: Date.now() - t0, error: `${e.name}: ${e.message}`.slice(0, 200), http: e.$metadata?.httpStatusCode ?? null }); }
  console.log(JSON.stringify(out.results.at(-1)));
}
async function getSha(c, Key) { const g = await c.send(new GetObjectCommand({ Bucket, Key })); const b = Buffer.from(await g.Body.transformToByteArray()); return sha(b); }
const small = randomBytes(4096), big = randomBytes(6 * 1024 * 1024);
await check("S1", "PutObject 4 KiB Buffer, SDK defaults", async () => { const c = mk(); const k = `sdk/${run}/s1`; await c.send(new PutObjectCommand({ Bucket, Key: k, Body: small })); return { roundtrip: (await getSha(c, k)) === sha(small) }; });
await check("S2", "PutObject 6 MiB Buffer, SDK defaults (includes the SDK expect-continue middleware)", async () => { const c = mk(); const k = `sdk/${run}/s2`; await c.send(new PutObjectCommand({ Bucket, Key: k, Body: big })); return { roundtrip: (await getSha(c, k)) === sha(big) }; });
await check("S3", "PutObject stream body with ContentLength, SDK default checksum setting (wire encoding not captured)", async () => { const c = mk(); const k = `sdk/${run}/s3`; await c.send(new PutObjectCommand({ Bucket, Key: k, Body: Readable.from([small]), ContentLength: small.length })); return { roundtrip: (await getSha(c, k)) === sha(small) }; });
await check("S4", "Same as S3 with requestChecksumCalculation WHEN_REQUIRED", async () => { const c = mk({ requestChecksumCalculation: "WHEN_REQUIRED" }); const k = `sdk/${run}/s4`; await c.send(new PutObjectCommand({ Bucket, Key: k, Body: Readable.from([small]), ContentLength: small.length })); return { roundtrip: (await getSha(c, k)) === sha(small) }; });
await check("S5", "Same as S2 with the expect-continue middleware removed", async () => { const c = mk(); c.middlewareStack.remove("addExpectContinueMiddleware"); const k = `sdk/${run}/s5`; await c.send(new PutObjectCommand({ Bucket, Key: k, Body: big })); return { roundtrip: (await getSha(c, k)) === sha(big) }; });
await check("S6", "getSignedUrl PutObject + UploadPart (path-prefixed endpoint), fetch() upload, SDK Complete", async () => {
  const c = mk({ requestChecksumCalculation: "WHEN_REQUIRED" }); c.middlewareStack.remove("addExpectContinueMiddleware");
  const k = `sdk/${run}/s6`;
  const u = await getSignedUrl(c, new PutObjectCommand({ Bucket, Key: k }), { expiresIn: 900 });
  const r = await fetch(u, { method: "PUT", body: small });
  const { UploadId } = await c.send(new CreateMultipartUploadCommand({ Bucket, Key: k + "m" }));
  const parts = [];
  for (const [n, b] of [[1, big], [2, small]]) {
    const pu = await getSignedUrl(c, new UploadPartCommand({ Bucket, Key: k + "m", UploadId, PartNumber: n }), { expiresIn: 900 });
    const pr = await fetch(pu, { method: "PUT", body: b }); parts.push({ PartNumber: n, ETag: pr.headers.get("etag") });
    if (!pr.ok) throw new Error(`part ${n} http ${pr.status}`);
  }
  await c.send(new CompleteMultipartUploadCommand({ Bucket, Key: k + "m", UploadId, MultipartUpload: { Parts: parts } }));
  return { put_status: r.status, url_path_prefix_kept: new URL(u).pathname, mpu_roundtrip: (await getSha(c, k + "m")) === sha(Buffer.concat([big, small])) };
});
await check("S7", "PutObject IfNoneMatch '*' via SDK on existing key", async () => { const c = mk({ requestChecksumCalculation: "WHEN_REQUIRED" }); const k = `sdk/${run}/s1`; try { await c.send(new PutObjectCommand({ Bucket, Key: k, Body: small, IfNoneMatch: "*" })); return { status: 200 }; } catch (e) { return { status: e.$metadata?.httpStatusCode, code: e.name }; } });
console.error(JSON.stringify(out));
