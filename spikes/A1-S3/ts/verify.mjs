// Reliquary A1-S3: independent JavaScript (Node 22) check of vectors.json (THROWAWAY spike code).
// SHA-256, HMAC-SHA256 and HKDF-SHA256 come from node:crypto (OpenSSL); BLAKE3 comes from
// @noble/hashes (pure JS, a separate code base from the Rust blake3 crate). Base32 and the
// strict text parser are written here from the rules in vectors.json, without the Rust code.
//
// Usage: node verify.mjs ../vectors.json [../ref/blake3_test_vectors.json]
import { createHash, createHmac, hkdfSync } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { blake3 } from '@noble/hashes/blake3.js';

const enc = new TextEncoder();
const hex = (u8) => Buffer.from(u8).toString('hex');
const ALPHA = 'abcdefghijklmnopqrstuvwxyz234567';

function b32(bytes) {
  let out = '', acc = 0, n = 0;
  for (const b of bytes) {
    acc = ((acc << 8) | b) & 0xffff; n += 8;
    while (n >= 5) { n -= 5; out += ALPHA[(acc >> n) & 31]; }
  }
  if (n > 0) out += ALPHA[(acc << (5 - n)) & 31];
  return out;
}

const RE = /^rq1-([abcd])-e(0|[1-9][0-9]{0,8})-([a-z2-7]*)$/;
function parse(s) {
  if (!s.startsWith('rq1-')) return { err: 'bad-version-prefix' };
  const parts = s.slice(4).split('-');
  const [c, e, ...restParts] = parts;
  const body = restParts.join('-');
  if (!['a', 'b', 'c', 'd'].includes(c)) return { err: 'unknown-construction' };
  if (e === undefined || !/^e(0|[1-9][0-9]{0,8})$/.test(e)) return { err: 'bad-epoch' };
  if (body.length !== 52) return { err: 'bad-length' };
  if (!/^[a-z2-7]{52}$/.test(body)) return { err: 'bad-character' };
  if ((ALPHA.indexOf(body[51]) & 0x0f) !== 0) return { err: 'non-canonical-trailing-bits' };
  if (!RE.test(s)) return { err: 'other' };
  // decode
  const out = []; let acc = 0, n = 0;
  for (const ch of body) {
    acc = ((acc << 5) | ALPHA.indexOf(ch)) & 0xfff; n += 5;
    if (n >= 8) { n -= 8; out.push((acc >> n) & 0xff); }
  }
  return { c, epoch: Number(e.slice(1)), id: Buffer.from(out.slice(0, 32)) };
}

function K(epoch) { return Buffer.from(Array.from({ length: 32 }, (_, i) => (i + 32 * epoch) & 0xff)); }

const INFO_A = 'reliquary/v1/dedup-key';
const INFO_B = 'reliquary/v1/dedup-key/sha256-digest';
const CTX_C = 'reliquary 2026-09-29 dedup-id keyed-blake3 content v1';
const CTX_D = 'reliquary 2026-09-29 dedup-id keyed-blake3 blake3-digest v1';

const hkdf32 = (ikm, info) => Buffer.from(hkdfSync('sha256', ikm, Buffer.alloc(0), Buffer.from(info), 32));
const deriveKey = (ctx, km) => blake3(km, { context: enc.encode(ctx) });

// Pattern block, a multiple of 251 bytes, so consecutive blocks continue the pattern.
const BLOCK = Buffer.alloc(251 * 8192);
for (let i = 0; i < BLOCK.length; i++) BLOCK[i] = i % 251;

// Feed in irregular piece sizes on purpose (exercises streaming and buffering in each library).
const PIECES = [1, 63, 64, 65, 1023, 1025, 4096, 65537, 1 << 20];
function feed(content, len, f) {
  if (content === 'ascii:abc') { f(Buffer.from('abc')); return; }
  if (content !== 'pattern-mod-251') throw new Error('unknown content ' + content);
  let off = 0, p = 0;
  while (off < len) {
    // stay aligned to the pattern: slice from BLOCK at (off mod 251)
    let want = len > 16 * 1048576 ? BLOCK.length - 251 : PIECES[p++ % PIECES.length];
    want = Math.min(want, len - off);
    const start = off % 251;
    f(BLOCK.subarray(start, start + want));
    off += want;
  }
}

function compute(content, len, epoch) {
  const k = K(epoch);
  const dka = hkdf32(k, INFO_A), dkb = hkdf32(k, INFO_B);
  const dkc = deriveKey(CTX_C, k), dkd = deriveKey(CTX_D, k);
  const sha = createHash('sha256'), ma = createHmac('sha256', dka);
  const b3 = blake3.create({}), kc = blake3.create({ key: dkc });
  feed(content, len, (buf) => { sha.update(buf); ma.update(buf); b3.update(buf); kc.update(buf); });
  const sha256 = sha.digest(), bl = Buffer.from(b3.digest());
  return {
    sha256, blake3: bl,
    a: ma.digest(),
    b: createHmac('sha256', dkb).update(sha256).digest(),
    c: Buffer.from(kc.digest()),
    d: Buffer.from(blake3(bl, { key: dkd })),
  };
}

function checkOfficial(path) {
  const doc = JSON.parse(readFileSync(path, 'utf8'));
  const key = enc.encode(doc.key);
  let pass = 0, fail = 0;
  for (const c of doc.cases) {
    const input = Uint8Array.from({ length: c.input_len }, (_, i) => i % 251);
    const ok = hex(blake3(input, { dkLen: 131 })) === c.hash
      && hex(blake3(input, { key, dkLen: 131 })) === c.keyed_hash
      && hex(blake3(input, { context: enc.encode(doc.context_string), dkLen: 131 })) === c.derive_key;
    ok ? pass++ : fail++;
  }
  console.log(JSON.stringify({ check: 'blake3-official-vectors', impl: 'noble-hashes 2.4.0', cases_pass: pass, cases_fail: fail }));
}

const [vecPath, officialPath] = process.argv.slice(2);
if (officialPath) checkOfficial(officialPath);
const doc = JSON.parse(readFileSync(vecPath, 'utf8'));
let pass = 0, fail = 0; const failures = [];
const memo = new Map();
const t0 = Date.now();
for (const v of doc.vectors) {
  let ok = false;
  if (v.kind === 'positive') {
    const t = Date.now();
    const r = compute(v.content, v.length, v.epoch);
    ok = hex(r.sha256) === v.sha256 && hex(r.blake3) === v.blake3;
    for (const c of ['a', 'b', 'c', 'd']) {
      const text = `rq1-${c}-e${v.epoch}-${b32(r[c])}`;
      const p = parse(text);
      ok = ok && hex(r[c]) === v['id_' + c] && text === v['text_' + c]
        && !p.err && p.c === c && p.epoch === v.epoch && p.id.equals(r[c]);
    }
    if (v.length > 1e9) console.error(`${v.id} len=${v.length} ${(Date.now() - t) / 1000}s ok=${ok}`);
    memo.set(`${v.content}/${v.length}/${v.epoch}`, r);
  } else if (v.kind === 'domain-separation-negative') {
    const r = memo.get(`${v.content}/${v.length}/${v.epoch}`) ?? compute(v.content, v.length, v.epoch);
    const got = hex(r[v.field.slice(3)]);
    ok = got === v.expected && got !== v.forbidden;
  } else if (v.kind === 'encoding-negative') {
    ok = parse(v.text).err === v.reject_reason;
  }
  ok ? pass++ : (fail++, failures.push(v.id));
}
console.log(JSON.stringify({ impl: `node ${process.version} (node:crypto/OpenSSL + @noble/hashes 2.4.0)`, pass, fail, failures, secs: (Date.now() - t0) / 1000 }));
process.exit(fail ? 1 : 0);
