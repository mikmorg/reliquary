# A1-S3 follow-up: vectors for the draft `docs/spec/identifiers.md` (THROWAWAY)

> **Throwaway spike code, not production code.** Workstream A1 (`docs/research/PLAN.md`).
> The first A1-S3 run (`../README.md`) produced vectors for four **candidate** constructions under
> labels and a text form (`rq1-…`) that the A1 recommendation did not adopt. All three skeptics
> flagged that gap (major issue: "A1-S3 vectors do not cover the recommended construction or
> encoding"). This follow-up regenerates the vectors with the **exact** byte layout of the draft
> spec, for all three whole-file kinds the owner can choose under DR-A1-1. The output is
> `docs/spec/identifiers-vectors.json`.

- **Run by / date:** A1 synthesis stage (Wave 1, batch W1-b), 2026-10-06
- **Exec tag:** CT
- **Data class:** `SYN → results`. Inputs are generated patterns and fixed test secrets.
- **Pass criterion (PLAN A1-S3):** Rust plus a second implementation agree on ≥ 50 vectors, including an empty file, > 4 GiB, and domain-separation negatives.

## What is vectored

All values are exactly as `docs/spec/identifiers.md` (Draft) defines them:

| Kind | Construction | Status in the draft spec |
|---|---|---|
| `01` | `mac = HMAC-SHA256(K, 0x01 ‖ SHA-256(content))` (digest form) | Proposed v1 whole-file kind (DR-A1-1 option B) |
| `03` | `mac = HMAC-SHA256(K, 0x03 ‖ content)` (content form, the settled wording plus HKDF epoch keys) | Alternative (DR-A1-1 option A) |
| `04` | `inner = HMAC-SHA256(K_root, content)`, `mac = HMAC-SHA256(K, 0x04 ‖ inner)` (nested form) | Alternative (DR-A1-1 option N) |

The derived keys are:
- `K = HKDF-SHA256(ikm = S_e, salt = empty, info = "reliquary/v1/dedup-id-key/kind=<kk>/epoch=<eeee>/scope=family", L = 32)`.
- `K_root = HKDF-SHA256(S_root, salt = empty, info = "reliquary/v1/content-mac-key/scope=family", L = 32)`.

The two forms are:
- Text form: `rd1-<kk>-<eeee>-<52 lowercase base32>`, 64 characters.
- Binary form: `kind ‖ u16be(epoch) ‖ mac`, 35 bytes.

The vectors are:
- **72 positive.** These cover 18 contents × 3 kinds. The contents are `"abc"` and byte patterns of length 0, 1, 55, 56, 63, 64, 65, 1023, 1024, 1025, 65535, 65536, 65537, 1 MiB, **2³² − 1, 2³² and 2³² + 1**. On top of that, lengths 0 and 1025 are repeated × 3 kinds at epochs 1, 0x0102 (to check byte order) and 0xffff.
- **14 domain-separation negatives.** Each has an `expected` value and a `forbidden` value that a known mistake would produce:
  - the kind byte left out;
  - the raw secret used as the key;
  - the bare label `reliquary/v1/dedup-id-key` (as Proposed ADR-0008 currently writes it);
  - the first A1-S3 candidate-b label;
  - the digest MACed as hex text;
  - the epoch missing from key derivation;
  - the scope left out;
  - the plain SHA-256 used as the ID;
  - for kind 03: no kind byte, and the wrong kind's key;
  - for kind 04: the epoch key used as the inner key, SHA-256 used as the inner value, and the raw S_root used as the inner key;
  - a little-endian epoch in the binary form.
- **25 encoding negatives** that a strict parser must reject:
  - 21 text cases: upper case (whole string, one character, epoch); `=` padding; 51 or 53 body characters; non-canonical trailing bits; `1` or `8` in the body; `rd2`; reserved kind `02`; unknown kind `ff`; 3- or 5-digit epoch; a bare 64-hex SHA-256; a hex body; a trailing newline; a trailing dot; a leading space; `_` as separator; `=` inside the body.
  - 4 binary cases: length 34, length 36, kind 0x00, kind 0x02.

## Results (measured, 2026-10-06, same shared x86 VM as the other A1 spikes)

| Check | Implementation | Result |
|---|---|---|
| Generate; regenerate and compare byte-for-byte; parse and round-trip every positive; reject every encoding negative; every negative's expected ≠ forbidden | Rust: `sha2` 0.11.0, `hmac` 0.13.0, `hkdf` 0.13.0, hand-written base32 and parser | 72/72, 25/25, 14/14, deterministic |
| Recompute everything from the spec text, using irregular feed sizes, with its own parser | Python 3.11.15 standard library (`hashlib` and `hmac`, which are OpenSSL-backed; `base64`; HKDF written from RFC 5869's extract-then-expand) | **72/72, 14/14, 25/25**, including the > 4 GiB cases |
| Same, independently written | Node v22.22.2 `node:crypto` (`createHash`, `createHmac`, `hkdfSync`), its own base32 codec and parser | **72/72, 14/14, 25/25** |
| Reference vectors for the primitives (the RFC 4231 and RFC 5869 texts are blocked) | Rust and Python against **C2SP Wycheproof** `hmac_sha256_test.json` (174 cases) and `hkdf_sha256_test.json` (86 cases), plus the 4 SHA-256 cases in Go `x/crypto` v0.57.0 `hkdf/hkdf_test.go` (the first three are marked "Tests from RFC 5869") | 0 failures in each |
| > 4 GiB spot check | coreutils `sha256sum` and `openssl dgst -sha256 -mac HMAC` (OpenSSL 3.0.13) on the 2³² + 1 pattern | SHA-256 and the kind-03 MAC equal the vector values |

Each run of each verifier took about 30 s.

**Verdict: pass**, for the draft spec as written. Rust and two independently written implementations agree on 111 vectors (72 positive, 14 domain-separation, 25 encoding), including the empty file and three inputs ≥ 4 GiB. The Python and Node checks both use OpenSSL for SHA-256 and HMAC, so they are independent *code* but not independent *primitives*. RustCrypto is the independent primitive, and Wycheproof anchors all three to a published reference set.

## Not covered

- The RFC 4231 and RFC 5869 appendix texts themselves (rfc-editor.org and datatracker.ietf.org are blocked; checked 2026-10-06). Wycheproof and the RFC 5869 cases in Go's tests are used in their place, labelled as such.
- Kotlin/Swift implementations (needed once B2/B4 code exists).
- Chunk-list IDs (kind `02`, reserved, not designed).
- Any per-person `scope` other than `family` (it waits on DR-F3-2 option F).

## Reproduce

```sh
cd spikes/A1-S3/identifiers-v1
mkdir -p /tmp/wp && cd /tmp/wp
curl -sSO https://raw.githubusercontent.com/C2SP/wycheproof/main/testvectors_v1/hmac_sha256_test.json
curl -sSO https://raw.githubusercontent.com/C2SP/wycheproof/main/testvectors_v1/hkdf_sha256_test.json
curl -sSo x.zip https://proxy.golang.org/golang.org/x/crypto/@v/v0.57.0.zip && unzip -q x.zip 'golang.org/x/crypto@v0.57.0/hkdf/*'
cd -
python3 -I py/extract_go_hkdf.py /tmp/wp/golang.org/x/crypto@v0.57.0/hkdf/hkdf_test.go > /tmp/wp/go_hkdf.json
(cd rust && cargo build --release)
rust/target/release/a1-idv1 gen > /tmp/v.json && cmp /tmp/v.json ../../../docs/spec/identifiers-vectors.json
rust/target/release/a1-idv1 verify ../../../docs/spec/identifiers-vectors.json
rust/target/release/a1-idv1 wycheproof /tmp/wp/hmac_sha256_test.json /tmp/wp/hkdf_sha256_test.json /tmp/wp/go_hkdf.json
python3 -I py/verify_idv1.py ../../../docs/spec/identifiers-vectors.json /tmp/wp/hmac_sha256_test.json /tmp/wp/hkdf_sha256_test.json /tmp/wp/go_hkdf.json
node js/verify_idv1.mjs ../../../docs/spec/identifiers-vectors.json
python3 -I py/emit.py 4294967297 | sha256sum
```

Downloaded files, with their SHA-256 on 2026-10-06:
- `hmac_sha256_test.json` `2d201cfa…7a743f`
- `hkdf_sha256_test.json` `bb2b462a…7c5f1e`

The third-party data is not committed (H3 R9).

## Evidence

`evidence/`: `rust-verify.txt`, `rust-wycheproof.txt`, `python-verify.txt`, `node-verify.txt`, `coreutils-openssl-large.txt` (UTC timestamps inside).
