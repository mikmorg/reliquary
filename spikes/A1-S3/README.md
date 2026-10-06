# Spike A1-S3: dedup-ID test vectors in two (three) languages (THROWAWAY)

> **Throwaway spike code, not production code.** Workstream A1 (`docs/research/PLAN.md`).
> The constructions and the text form in `vectors.json` are **candidates** for ADR-0006, written
> down so that independent implementations can be checked against each other. They are **not**
> a decision. The analyst and the ADR choose; `docs/spec/identifiers.md` then adopts or
> regenerates the vectors for the chosen construction.

- **Run by / date:** A1 spike runner (Wave 1, batch W1-b), 2026-09-29
- **Exec tag:** CT
- **Data class:** `SYN → results`. Inputs are generated patterns and fixed test secrets.
- **Pass criterion (PLAN):** "Rust plus a second implementation (TS or Kotlin) agree on 50 vectors, including an empty file, > 4 GiB, and domain-separation negatives."

## Candidate constructions (K_e = the family secret of epoch e, 32 bytes)

| Letter | Key derivation | ID |
|---|---|---|
| a | `dk = HKDF-SHA256(ikm=K_e, salt=empty, info="reliquary/v1/dedup-key")`, the same info string as the content-encryption spike (format note §6) | `HMAC-SHA256(dk, content)`: ADR-0001 as written |
| b | `dk = HKDF-SHA256(ikm=K_e, salt=empty, info="reliquary/v1/dedup-key/sha256-digest")` | `HMAC-SHA256(dk, SHA-256(content))`: rotatable from the cache (A1-S2) |
| c | `dk = BLAKE3 derive_key("reliquary 2026-09-29 dedup-id keyed-blake3 content v1", K_e)` | `BLAKE3 keyed_hash(dk, content)` |
| d | `dk = BLAKE3 derive_key("reliquary 2026-09-29 dedup-id keyed-blake3 blake3-digest v1", K_e)` | `BLAKE3 keyed_hash(dk, BLAKE3(content))` |

The derive_key context strings follow the "[application] [date] [purpose]" format recommended by the BLAKE3 authors.

**Candidate text form:** `rq1-<a|b|c|d>-e<epoch>-<52 chars>`. The epoch is decimal with no leading zeros. The body is the RFC 4648 base32 alphabet in lower case (`a-z2-7`), unpadded; the 4 unused bits of the last character must be zero, so the last character is always `a` or `q`. Example: `rq1-b-e0-rcpp3px63udebhlao4lfljlyfllfabz6xuna2fhbsskmtrbatjea` (empty file). The string is 61 characters for epochs 0–9. It is a single case with no `.`, space or reserved characters, so it works on case-insensitive FAT/exFAT/NTFS volumes and inside R2 keys (1,024-byte limit). The RFC 4648 alphabet was taken from Go's `encoding/base32` source (a secondary source) because rfc-editor.org is blocked. It was cross-checked with Python's `base64.b32encode`.

## Vectors (`vectors.json`, 51 in total)

- **P01–P27, positive (27).** Each gives SHA-256, BLAKE3, `id_a`–`id_d` and the four text forms. Lengths: 0; 1; `"abc"`; 55/56/63/64/65 (SHA-256 padding and block edges); 1023/1024/1025/2048/2049 (BLAKE3 chunk edges); 4095/4096; 65536; 100000; 1 MiB; 4 MiB − 1/4 MiB/4 MiB + 1; **2^32 − 1, 2^32 and 2^32 + 1 bytes (> 4 GiB)**; plus three epoch-1 repeats (0, 1024, 4 MiB + 1). Content is `byte i = i mod 251`, as in the official BLAKE3 vectors, or ASCII `abc`.
- **N28–N37, domain-separation negatives (10).** Each gives an `expected` value that must be produced and a `forbidden` value that a common mistake would produce:
  - b ≠ a over a file whose bytes are SHA-256(X). With a shared key these two would collide.
  - d ≠ c over a file whose bytes are BLAKE3(X).
  - No HKDF or derive_key step, i.e. K_e used directly (a, b, c).
  - Digest MACed as hex text instead of 32 raw bytes (b, d).
  - Epoch 0 ≠ epoch 1.
  - ID ≠ unkeyed SHA-256.
  - A `v2` HKDF info string gives a different key.
- **E38–E51, encoding negatives (14).** A strict parser must reject each one with the given reason: upper case (whole string or one character), `=` padding, 51 or 53 body characters, non-canonical trailing bits, a character outside the alphabet (`1`), unknown version `rq2`, unknown construction, epoch `e00`, empty epoch, a hex body, a trailing newline, and a trailing dot (Windows strips trailing dots from file names).

## Results (measured)

| Check | Implementation | Result |
|---|---|---|
| Generate and self-verify all 51 vectors | Rust: `sha2` 0.11.0, `hmac` 0.13.0, `hkdf` 0.13.0, `blake3` 1.8.7, and a hand-written base32 codec and parser | 51/51 pass |
| Independently recompute all 51 vectors | JavaScript on Node v22.22.2: `node:crypto` (OpenSSL) for SHA-256, HMAC and HKDF; `@noble/hashes` 2.4.0 (pure JS) for BLAKE3; its own base32 codec and parser written from the rules above. Inputs fed in irregular piece sizes. | **51/51 pass**, including P22–P24 (> 4 GiB) and all negatives |
| Third check of constructions a and b, SHA-256 and base32 for all 27 positives | Python 3.11.15 standard library (`hashlib`, `hmac`, `base64`; HKDF written from RFC 5869's two steps) | 27/27 pass |
| BLAKE3 libraries against the official BLAKE3 `test_vectors.json` (35 cases; hash, keyed_hash and derive_key, 131-byte XOF output) | Rust `blake3` 1.8.7 and `@noble/hashes` 2.4.0 | 35/35 and 35/35 pass |
| SHA-256 of `""` and `"abc"` | all three | `e3b0c442…b855` and `ba7816bf…15ad`, the widely published values. The FIPS 180-4 document itself was blocked (nvlpubs.nist.gov), so the comparison is with the values three independent libraries compute. |

Time for the JS check: 1,516 s (25 min). The > 4 GiB vectors dominate it: pure-JS BLAKE3 on a contended VM took 390–500 s per 4 GiB input.

**Verdict: pass.** Rust and an independent second implementation (JavaScript/TypeScript runtime) agree on all 51 vectors, which include an empty file, three inputs of 4 GiB or more, and 10 domain-separation negatives. A third, partial implementation (Python) agrees on every value it can compute. This validates the vectors for the **candidate** constructions only. If ADR-0006 picks different labels or an encoding, regenerate the vectors with the same harness.

## Not covered

- HMAC-SHA256 against RFC 4231 and HKDF against RFC 5869's own test cases: both RFC texts are blocked (rfc-editor.org, ietf.org). The three independent libraries agree with each other, but that is not the same as matching the RFC appendices. Follow-up: fetch the RFC 4231/5869 vectors through another channel, or from a library's test files labelled as secondary.
- A Kotlin/JVM implementation. JCA offers SHA-256 and HmacSHA256 but no BLAKE3.
- Vectors for tree-hash or chunk-list IDs (reserved, not designed).

## Reproduce

```sh
cd spikes/A1-S3
curl -sSo /tmp/blake3_tv.json https://raw.githubusercontent.com/BLAKE3-team/BLAKE3/master/test_vectors/test_vectors.json
(cd rust && cargo build --release)
rust/target/release/a1-vectors blake3-official /tmp/blake3_tv.json
rust/target/release/a1-vectors gen > /tmp/vectors.json && cmp /tmp/vectors.json vectors.json   # deterministic
rust/target/release/a1-vectors verify vectors.json
(cd ts && npm ci && node verify.mjs ../vectors.json /tmp/blake3_tv.json)     # about 25 min on a busy 4-vCPU VM
python3 py_check.py vectors.json
```
