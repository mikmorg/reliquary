// THROWAWAY spike code (Reliquary A1-S3 follow-up). Independent JavaScript check of the DRAFT
// identifiers.md vectors, written from the spec text. node:crypto only (createHash, createHmac,
// hkdfSync), own base32 codec and parser. Usage: node verify_idv1.mjs vectors.json
import { createHash, createHmac, hkdfSync } from 'node:crypto';
import { readFileSync } from 'node:fs';

const v = JSON.parse(readFileSync(process.argv[2], 'utf8'));
const A = 'abcdefghijklmnopqrstuvwxyz234567';
const hex = (b) => Buffer.from(b).toString('hex');
const hkdf = (ikm, info) => Buffer.from(hkdfSync('sha256', ikm, Buffer.alloc(0), Buffer.from(info, 'ascii'), 32));
const info = (k, e) => `reliquary/v1/dedup-id-key/kind=${k.toString(16).padStart(2, '0')}/epoch=${e.toString(16).padStart(4, '0')}/scope=family`;
const H = (k, ...parts) => { const h = createHmac('sha256', k); for (const p of parts) h.update(p); return h.digest(); };
function b32(buf) { let out = '', acc = 0, bits = 0; for (const b of buf) { acc = ((acc << 8) | b) & 0xffff; bits += 8; while (bits >= 5) { bits -= 5; out += A[(acc >> bits) & 31]; } } if (bits) out += A[(acc << (5 - bits)) & 31]; return out; }
function b32dec(s) { let acc = 0, bits = 0; const out = []; for (const c of s) { const x = A.indexOf(c); if (x < 0) throw new Error('alphabet'); acc = ((acc << 5) | x) & 0xffff; bits += 5; if (bits >= 8) { bits -= 8; out.push((acc >> bits) & 0xff); } } if (acc & ((1 << bits) - 1)) throw new Error('trailing bits'); return Buffer.from(out); }
const text = (k, e, mac) => `rd1-${k.toString(16).padStart(2, '0')}-${e.toString(16).padStart(4, '0')}-${b32(mac)}`;
const binary = (k, e, mac) => Buffer.concat([Buffer.from([k, e >> 8, e & 0xff]), mac]);
function parseText(s) {
  if (s.length !== 64 || !s.startsWith('rd1-') || s[6] !== '-' || s[11] !== '-') throw new Error('syntax');
  const k = s.slice(4, 6), e = s.slice(7, 11), body = s.slice(12);
  if (!/^[0-9a-f]{2}$/.test(k) || !/^[0-9a-f]{4}$/.test(e)) throw new Error('hex');
  const kind = parseInt(k, 16); if (kind === 2) throw new Error('reserved'); if (![1, 3, 4].includes(kind)) throw new Error('unknown kind');
  const mac = b32dec(body); if (mac.length !== 32) throw new Error('len');
  return [kind, parseInt(e, 16), mac];
}
function parseBinary(b) { if (b.length !== 35) throw new Error('len'); if (b[0] === 2) throw new Error('reserved'); if (![1, 3, 4].includes(b[0])) throw new Error('kind'); return [b[0], (b[1] << 8) | b[2], b.subarray(3)]; }

const PERIOD = Buffer.alloc(251 * 16384); for (let i = 0; i < PERIOD.length; i++) PERIOD[i] = i % 251;
function feed(content, sinks) {
  if (content.startsWith('ascii:')) { for (const s of sinks) s.update(Buffer.from(content.slice(6), 'ascii')); return; }
  const n = Number(content.split(':')[1]); const sizes = [5, 2, 333, 1 << 16, PERIOD.length - 251]; let off = 0, i = 0;
  while (off < n) { const start = off % 251; const take = Math.min(sizes[i % sizes.length], n - off, PERIOD.length - start); const c = PERIOD.subarray(start, start + take); for (const s of sinks) s.update(c); off += take; i++; }
}
const S = Object.fromEntries(['S_0', 'S_1', 'S_root'].map((k) => [k, Buffer.from(v.secrets[k], 'hex')]));
const kroot = hkdf(S.S_root, 'reliquary/v1/content-mac-key/scope=family');
let fails = 0; if (hex(kroot) !== v.k_root.key) { fails++; console.log('FAIL kroot'); }
const cache = new Map();
for (const p of v.positive) {
  const kind = parseInt(p.kind, 16), e = p.epoch, sec = S[p.secret];
  const K = hkdf(sec, info(kind, e)), k3 = hkdf(sec, info(3, e));
  const key = `${p.content}|${e}|${p.secret}`;
  if (!cache.has(key)) { const sh = createHash('sha256'), h3 = createHmac('sha256', k3), hr = createHmac('sha256', kroot); h3.update(Buffer.from([3])); feed(p.content, [sh, h3, hr]); cache.set(key, [sh.digest(), h3.digest(), hr.digest()]); }
  const [d, mac3, inner] = cache.get(key);
  const mac = kind === 1 ? H(K, Buffer.from([1]), d) : kind === 3 ? mac3 : H(K, Buffer.from([4]), inner);
  const [pk, pe, pm] = parseText(p.id_text); const [bk, be, bm] = parseBinary(Buffer.from(p.id_binary, 'hex'));
  const ok = hex(d) === p.sha256 && hex(K) === p.key && hex(mac) === p.mac && text(kind, e, mac) === p.id_text && hex(binary(kind, e, mac)) === p.id_binary
    && pk === kind && pe === e && pm.equals(mac) && bk === kind && be === e && Buffer.from(bm).equals(mac) && (kind !== 4 || hex(inner) === p.inner);
  if (!ok) { fails++; console.log('FAIL', p.id); }
}
// domain-separation negatives recomputed
const c = (() => { const parts = []; feed('pattern-mod-251:1025', [{ update: (x) => parts.push(Buffer.from(x)) }]); return Buffer.concat(parts); })();
const d = createHash('sha256').update(c).digest(); const s0 = S.S_0; const B = (...x) => Buffer.from(x);
const [k1, k3, k4] = [1, 3, 4].map((k) => hkdf(s0, info(k, 0)));
const mac1 = H(k1, B(1), d), mac3 = H(k3, B(3), c), mac4 = H(k4, B(4), H(kroot, c));
const m = H(hkdf(s0, info(1, 0x0102)), B(1), d);
const mine = {
  N01: [mac1, H(k1, d)], N02: [mac1, H(s0, B(1), d)], N03: [mac1, H(hkdf(s0, 'reliquary/v1/dedup-id-key'), B(1), d)],
  N04: [mac1, H(hkdf(s0, 'reliquary/v1/dedup-key/sha256-digest'), d)], N05: [mac1, H(k1, B(1), Buffer.from(hex(d), 'ascii'))],
  N06: [H(hkdf(s0, info(1, 1)), B(1), d), mac1], N07: [mac1, H(hkdf(s0, 'reliquary/v1/dedup-id-key/kind=01/epoch=0000'), B(1), d)],
  N08: [mac1, d], N09: [mac3, H(k3, c)], N10: [mac3, H(k1, B(3), c)], N11: [mac4, H(k4, B(4), H(k4, c))], N12: [mac4, H(k4, B(4), d)],
  N13: [mac4, H(k4, B(4), H(S.S_root, c))], N14: [binary(1, 0x0102, m), Buffer.concat([B(1, 2, 1), m])],
};
for (const n of v.domain_separation_negative) { const [e, f] = mine[n.id]; if (hex(e) !== (n.expected_mac ?? n.expected_binary) || hex(f) !== n.forbidden || e.equals(f)) { fails++; console.log('FAIL', n.id); } }
for (const n of v.encoding_negative) { try { 'text' in n ? parseText(n.text) : parseBinary(Buffer.from(n.binary, 'hex')); fails++; console.log('FAIL accepted', n.id); } catch { /* rejected as required */ } }
console.log(`node ${process.version}: positives ${v.positive.length}, domain negatives ${v.domain_separation_negative.length}, encoding negatives ${v.encoding_negative.length}, failures ${fails}`);
process.exit(fails ? 1 : 0);
