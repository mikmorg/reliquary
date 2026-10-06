// THROWAWAY SPIKE helper: typage (npm age-encryption) CLI for A2-S3 interop.
import * as age from "age-encryption";
import { readFileSync, writeFileSync, readdirSync } from "node:fs";
import { createHash } from "node:crypto";
import { inflateSync } from "node:zlib";
const sha = (b) => createHash("sha256").update(b).digest("hex");
const ids = (p) => readFileSync(p, "utf8").split("\n").map((l) => l.trim()).filter((l) => l.startsWith("AGE-SECRET-KEY-"));
const [cmd, ...a] = process.argv.slice(2);
if (cmd === "keygen") {
  const id = await age.generateHybridIdentity();
  const r = await age.identityToRecipient(id);
  writeFileSync(a[0], `# public key: ${r}\n${id}\n`, { mode: 0o600 });
  console.log(r);
} else if (cmd === "encrypt") {
  const e = new age.Encrypter();
  for (const r of readFileSync(a[0], "utf8").split("\n").map((l) => l.trim()).filter((l) => l && !l.startsWith("#"))) e.addRecipient(r);
  writeFileSync(a[2], await e.encrypt(readFileSync(a[1])));
} else if (cmd === "decrypt") {
  const d = new age.Decrypter();
  for (const i of ids(a[0])) d.addIdentity(i);
  try {
    const out = await d.decrypt(readFileSync(a[1]));
    if (a[2]) writeFileSync(a[2], out);
    console.log(JSON.stringify({ ok: true, bytes: out.length, sha256: sha(out) }));
  } catch (e) {
    console.log(JSON.stringify({ ok: false, error: String(e && e.message || e) }));
    process.exit(1);
  }
} else if (cmd === "cctv") {
  let pass = 0, fail = 0, na = 0; const failed = [];
  for (const n of readdirSync(a[0]).sort()) {
    let raw = readFileSync(`${a[0]}/${n}`);
    const kv = []; let off = 0;
    for (;;) { const i = raw.indexOf(10, off); const line = raw.subarray(off, i).toString(); off = i + 1; if (line === "") break; const j = line.indexOf(": "); kv.push(j < 0 ? [line, ""] : [line.slice(0, j), line.slice(j + 2)]); }
    const get = (k) => (kv.find(([kk]) => kk === k) || [])[1];
    let file = raw.subarray(off);
    if (get("compressed") === "zlib") file = inflateSync(file);
    const idents = kv.filter(([k]) => k === "identity").map(([, v]) => v);
    const expect = get("expect");
    if (get("armored") !== undefined || idents.length === 0) { na++; continue; }
    const d = new age.Decrypter(); idents.forEach((i) => d.addIdentity(i));
    let got, err = null, out = null;
    try { out = await d.decrypt(new Uint8Array(file)); got = "success"; } catch (e) { got = "error"; err = String(e && e.message || e); }
    let ok = expect === "success" ? (got === "success" && sha(out) === get("payload")) : got === "error";
    if (ok) pass++; else { fail++; failed.push(n); }
    console.log(JSON.stringify({ vector: n, expect, got, result: ok ? "pass" : "FAIL", error: err }));
  }
  console.log(JSON.stringify({ summary: { pass, fail, na, failed } }));
}
