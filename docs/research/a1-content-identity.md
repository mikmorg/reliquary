# A1. Content identity and dedup ID

- **Workstream:** A1 (see `docs/research/PLAN.md`, section "A1.")
- **Status:** Final for Wave 1. Skeptic-reviewed (three lenses, 2026-10-06; tally computed in code). Owner decisions DR-A1-1 and DR-A1-2 are pending. The phone part of A1-S1 is kit-ready and not yet run.
- **Date:** 2026-09-29 (last updated 2026-10-06, synthesis)
- **Feeds:**
  - ADR-0006, Proposed: [`docs/adr/0006-content-identity-and-dedup-id.md`](../adr/0006-content-identity-and-dedup-id.md)
  - [`docs/spec/identifiers.md`](../spec/identifiers.md) (Draft) and [`identifiers-vectors.json`](../spec/identifiers-vectors.json)
  - one-way door #1
  - DR-A1-1 and DR-A1-2 (H1 to number)
  - inputs to OD-04, OD-07 and OD-17, and to F3's DR-F3-2
- **Depends on:**
  - F3 (`f3-security-literature.md`: C15 contested, M-14, M-25, M-31, M-32, DR-F3-2)
  - D1 (`d1-threat-model.md` §7)
  - T1 spike 2 (`content-encryption-format.md`, "CE")
  - D2 (ADR-0008 Decision 7)
  - A6 (store addressing, posture A′)
  - A2 (`object-format.md`)
  - B5/B2/B4 (cache signals)
- **Traceability rows advanced:** R-21, R-23, R-24 (contract), OPEN-3c and Q1-2b (ID side only), R-44 (input)

## Summary

**Algorithm: keep SHA-256**, which ADR-0001 already names. It is native on every client platform and `sha256sum` can check it (verified claims K1, K6, K8). No phone has been measured. The A1-S1 kit must show that it meets BUD-HASH on the low-end class. If the `sha2` crate is too slow there, which happens on cores without SHA-2 instructions and in every 32-bit ARM build, other SHA-256 backends are tried before BLAKE3 is considered.

**ID format:** every dedup ID carries a **kind** byte and a **16-bit epoch**, and keeps the **full 256 bits**. The text form is `rd1-<kk>-<eeee>-<52 lowercase base32>`. The base32 body keeps an ID from ever being confused with a plain SHA-256, which stays hex. `docs/spec/identifiers.md` fixes the bytes. 111 vectors were cross-checked in Rust, Python and Node on 2026-10-06, and the HMAC/HKDF primitives were checked against Wycheproof.

**Construction:** this is the owner's decision (DR-A1-1), because it touches the settled wording "HMAC(family secret, content)". The proposal is **kind 01**: HMAC over the file's SHA-256 digest, with HKDF epoch keys.
- What supports it (verified or measured):
  - It costs one hash per byte instead of two (K2). On x86 that is about 0.95 vs 1.69 CPU s per GB; phones are unmeasured.
  - IDs re-derive from cached digests with no file reads (A1-S2: 1M entries in 3–6 s, x86).
- Correction to the earlier draft: the claim that HMAC over content makes rotation infeasible was **contested** by all three skeptics. It is withdrawn. Rotation under that option is costlier, not impossible.
- What kind 01 gives up (reasoning only, secondary-only): a leaked key can test **lists of SHA-256 values** without the files. That includes a stolen phone's own hash cache.
- A **nested** variant (kind 04) keeps cheap rotation *and* the "needs the file bytes" property, at the per-byte cost of the content form. It is offered as the alternative. A1-S1 will show what it costs on phones.

**Confidence:**
- High on SHA-256 and on the encoding facts.
- Medium on the format details.
- Medium-low on kind 01 over kind 04, because the deciding numbers (phone energy) and the security weighting are not measured or sourced.

## Questions

| # | Question | Short answer | Confidence |
|---|---|---|---|
| 1 | SHA-256 vs BLAKE3: throughput and energy per GB on real device classes. Is I/O the bottleneck? | **No phone measured.** SHA-256 is recommended (K1, K8 verified). On x86, BLAKE3 used about 4× less CPU per GB than SHA-NI SHA-256 (A1-S1: 0.224 vs 0.914 CPU s/GB), but both are far above BUD-HASH there. On ARMv8 phones with SHA-2 instructions, I/O, heat and energy are the likely limits; the only figure is secondary (559 MB/s, 2017). The risk class is **no `HWCAP_SHA2`, or any 32-bit ARM build**, where `sha2` 0.11 is always software (K6 verified; 32-bit case added by the skeptics). Decision rule in §1. | High (platform, settled text); **Low** (phone performance and energy) |
| 2 | HMAC(K, content), HMAC(K, SHA-256(content)) or keyed BLAKE3? Compare read passes, rotation from the cache, security | Every option reads each file in **two passes** (pass 1 hash, pass 2 encrypt; CE §14). The difference is hash work in pass 1 and at the homelab: 2 per byte for content and nested, 1 for digest (K2). **Digest (kind 01)** and **nested (kind 04)** rotate from the cache. **Content (kind 03)** rotates by a homelab re-read plus re-hashing of pending device entries, which is costlier but feasible (K3 contested and restated). Security trade in §2 (K4, K5 secondary-only). Proposal: kind 01, with kind 04 as the alternative (DR-A1-1). | Medium-low (the choice between 01 and 04); Medium (the facts) |
| 3 | Wire format: version prefix, domain label, 256 bits or truncated, encoding | Binary `kind ‖ u16be(epoch) ‖ mac` = 35 B. Text `rd1-<kk>-<eeee>-<base32>` = 64 chars. HKDF info `reliquary/v1/dedup-id-key/kind=kk/epoch=eeee/scope=family`. Full 256 bits. **Base32 for IDs, hex for plain SHA-256** (changed from the earlier draft's hex, §3). | High (encoding safety, K9); Medium (details) |
| 4 | Whole-file digest vs block or tree hash | Whole file. age STREAM already gives per-part integrity. Kind 02 is reserved for chunk lists. No CDC. | Medium-high |
| 5 | Rotation: epoch tags, procedure after a compromise, homelab re-derivation | Epoch in every ID (DR-A1-2). The homelab re-derives from the catalog (`sha256`, or `inner` for kind 04). The cloud's old-epoch history is **flushed** rather than re-keyed (F3 M-14; residual linkage goes to AR-06). Devices re-derive from their caches. D2 owns custody and the trigger. | Medium |
| 6 | Minimum safe client rules (racy mtime, TOCTOU) | `identifiers.md` §9, R1–R8: signals plus fail-safe; a racy window against a **filesystem-written** reference time; FAT local-time shifts mean rehash; stat checks before and after; homelab check end to end; sampled re-verification; check the file type after open; cache provenance. Receipt semantics, status states and cache protection are handed to A3, E3 and B6. | Medium-high |
| 7 | Same ID for items with no device of origin (A9) | The ID is a pure function of the bytes and the epoch key. The importer runs the same conformance suite. | High |
| 8 | (new) What does kind 01 newly depend on? | Unkeyed SHA-256 collision resistance, for **public precomputed pairs** only. Against an insider device holding K, HMAC over content gives about the same resistance (K5 secondary-only). No full SHA-256 collision is known; the reported state of the art is 31 of 64 steps (secondary, eprint blocked). | Medium |
| 9 | (new) Do the presence-oracle and dedup-scope decisions (DR-F3-2, D1 §7) change this door? | Yes, partly (§8). Per-person keys (option F) change key derivation. Homelab-only dedup or scoped presence shrinks the value of fast rotation. `scope=family` in the HKDF info keeps option F open, and kinds 01 and 04 make a later scope change cache-only. | Medium |

## Method

- **Sweep (2026-09-29):** three scouts (docs, source, community), then an analyst re-read of the load-bearing primary sources (S1–S44).
- **Spikes (2026-09-29):** A1-S1 (x86 reference plus OL kit), A1-S2, and A1-S3 (candidate vectors), by the spike runner.
- **Skeptic stage (2026-10-06):** three independent skeptics (sources, logic, adversary) reviewed key claims K1–K13. The verdicts in §Claims are the code-computed tally:
  - **verified** = has a primary source, and at least 2 of 3 skeptics did not refute it;
  - **secondary-only** = no primary source;
  - **contested** = everything else.
- **Synthesis (2026-10-06):**
  - Rewrote the note against every critical and major issue (see §Skeptic issues).
  - Regenerated the vectors for the exact draft spec (A1-S3 follow-up, `spikes/A1-S3/identifiers-v1/`).
  - Checked the HMAC/HKDF primitives against C2SP Wycheproof (S45) and the RFC 5869 cases in Go `x/crypto` (S46).
  - Read the F3, D1 and A6 notes, ADR-0007/`object-format.md` and Proposed ADR-0008 for consistency.
- **Routes used:** raw.githubusercontent.com, static.crates.io, proxy.golang.org, developer.android.com, developer.apple.com DocC JSON.
- **Blocked sources** (reported to H1; none silently replaced; each claim that relies on a stand-in says so):
  - rfc-editor.org and datatracker.ietf.org: RFC 2104, 4231, 4648, 5869 (re-checked 2026-10-06: CONNECT 403)
  - nvlpubs.nist.gov and csrc.nist.gov: FIPS 180-4, SP 800-107r1
  - eprint.iacr.org, iacr.org and pure.ecnu.edu.cn: SHA-256 reduced-round collision papers and Bellare's HMAC proofs (checked 2026-10-06)
  - bench.cr.yp.to (eBACS), reported by skeptic 1
  - w3c.github.io/webcrypto
  - dropbox.com/developers
  - tarsnap.com, tahoe-lafs.org, news.ycombinator.com, eclecticlight.co, daemonology.net, 00f.net, lobste.rs
- **Stand-ins, each labelled:**
  - RFC 4648 alphabet: Go `encoding/base32` and Python `base64`.
  - RFC 4231 and 5869 vectors: Wycheproof and Go's tests.
  - HMAC PRF property: unsourced reasoning (K4).
- **Stop rule:** the analyst's re-reads added four primary sources without changing the algorithm choice. The skeptics added no new primary source that reverses a verified claim; they narrowed K3, K4, K5 and K12's transfer.

## Sources

| # | Source (title and URL or mirror path) | Publisher | Published or version date | Accessed | Primary? |
|---|---|---|---|---|---|
| S1 | ADR-0001 Cloud staging on R2 — `docs/adr/0001-cloud-staging-on-r2.md` | Project | 2026-09-29, Accepted | 2026-10-06 | Yes (settled text) |
| S2 | Content encryption format spike — `docs/research/content-encryption-format.md` (§3, §6, §11, §14) | Project (T1 spike 2) | 2026-09-29 | 2026-10-06 | Yes (project measurement, x86 only) |
| S3 | BLAKE3: one function, fast everywhere — `BLAKE3-team/BLAKE3-specs @ master : blake3.pdf` | O'Connor, Aumasson, Neves, Wilcox-O'Hearn | 20211102173700 | 2026-10-06 (skeptic re-read) | Yes |
| S4 | BLAKE3 README — `BLAKE3-team/BLAKE3 @ master : README.md` | BLAKE3 team | master | 2026-09-29 | Yes |
| S5 | BLAKE3 test vectors — `BLAKE3-team/BLAKE3 @ master : test_vectors/test_vectors.json` | BLAKE3 team | master | 2026-09-29 | Yes |
| S6 | Bao spec — `oconnor663/bao @ master : docs/spec.md` | J. O'Connor | master | 2026-09-29 | Yes |
| S7 | RustCrypto `sha2` 0.11.0 — static.crates.io `sha2-0.11.0.crate` (README "Backends", Cargo.toml) | RustCrypto | 0.11.0 (latest per index, 2026-10-06) | 2026-10-06 | Yes |
| S8 | RustCrypto `hmac` 0.13.0, `hkdf` 0.13.0 — static.crates.io | RustCrypto | 0.13.0 | 2026-10-06 (built) | Yes |
| S9 | `blake3` crate 1.8.7 — static.crates.io | BLAKE3 team | 1.8.7 | 2026-09-29 | Yes |
| S10 | Racy Git — `git/git @ master : Documentation/technical/racy-git.adoc` | Git project | master | 2026-10-06 (skeptic re-read) | Yes |
| S11 | Hash function transition — `git/git @ master : Documentation/technical/hash-function-transition.adoc` | Git project | master | 2026-09-29 | Yes |
| S12 | restic "Backing up" — `restic/restic @ master : doc/040_backup.rst` | restic | master | 2026-10-06 (skeptic re-read) | Yes |
| S13 | restic design — `restic/restic @ master : doc/design.rst` | restic | master | 2026-09-29 | Yes |
| S14 | restic `internal/archiver/archiver.go` | restic | master | 2026-09-29 | Yes |
| S15 | Borg internals: security — `borgbackup/borg @ master : docs/internals/security.rst` | Borg | master | 2026-10-06 (skeptic re-read) | Yes (for Borg's own design only; it MACs content, so it does **not** support K4's digest-form comparison) |
| S16 | Kopia `repo/hashing/hashing.go`, `blake3_hashes.go` | Kopia | master | 2026-10-06 | Yes (same caveat as S15) |
| S17 | Duplicacy `src/duplicacy_config.go` | Duplicacy | master | 2026-09-29 | Yes (nearest precedent for the digest form) |
| S18 | bupstash `src/crypto.rs`, `src/keys.rs` | bupstash | master | 2026-09-29 | Yes |
| S19 | Tarsnap `lib/crypto/crypto.h`, `crypto_hash.c` | Tarsnap | master | 2026-09-29 | Yes |
| S20 | Tahoe-LAFS "The Convergence Secret" — `tahoe-lafs/tahoe-lafs @ master : docs/convergence-secret.rst` | Tahoe-LAFS | master | 2026-10-06 (skeptic re-read) | Yes |
| S21 | Tahoe-LAFS `src/allmydata/util/hashutil.py` | Tahoe-LAFS | master | 2026-09-29 | Yes |
| S22 | Dropbox content hasher — `dropbox/dropbox-api-content-hasher @ master` | Dropbox | master | 2026-09-29 | Yes (code) |
| S23 | Multicodec `table.csv` | Multiformats | master | 2026-09-29 | Yes |
| S24 | Multibase README | Multiformats | master | 2026-09-29 | Yes |
| S25 | Perkeep `pkg/blob/ref.go` | Perkeep | master | 2026-09-29 | Yes |
| S26 | R2 limits — `cloudflare/cloudflare-docs @ production : src/content/docs/r2/platform/limits.mdx` | Cloudflare | production | 2026-10-06 (skeptic re-read) | Yes |
| S27 | Workers Web Crypto — `cloudflare-docs @ production : src/content/docs/workers/runtime-apis/web-crypto.mdx` | Cloudflare | production | 2026-10-06 | Yes |
| S28 | Naming Files, Paths, and Namespaces — `MicrosoftDocs/win32 @ docs : desktop-src/FileIO/naming-a-file.md` | Microsoft | docs | 2026-10-06 | Yes |
| S29 | File Times — `MicrosoftDocs/win32 @ docs : desktop-src/SysInfo/file-times.md` | Microsoft | docs | 2026-10-06 | Yes |
| S30 | FILE_BASIC_INFO — `MicrosoftDocs/sdk-api @ docs : …/ns-winbase-file_basic_info.md` | Microsoft | docs | 2026-09-29 | Yes |
| S31 | exFAT File System Specification — `MicrosoftDocs/win32 @ docs : desktop-src/FileIO/exfat-specification.md` | Microsoft | docs | 2026-10-06 | Yes |
| S32 | Linux arm64 ELF hwcaps — `torvalds/linux @ master : Documentation/arch/arm64/elf_hwcaps.rst` | Linux kernel | master | 2026-10-06 | Yes |
| S33 | Android `MessageDigest` — https://developer.android.com/reference/java/security/MessageDigest | Google | 2026-08-03 | 2026-10-06 | Yes |
| S34 | Android `Mac` — https://developer.android.com/reference/javax/crypto/Mac | Google | 2026-08-03 | 2026-10-06 | Yes |
| S35 | Android cryptography guidance — https://developer.android.com/privacy-and-security/cryptography | Google | 2026-03-06 | 2026-09-29 | Yes |
| S36 | CryptoKit `SHA256`, `HMAC` — developer.apple.com DocC JSON | Apple | iOS 13+, macOS 10.15+ | 2026-10-06 | Yes |
| S37 | syncthing-android #839 (ARMv8 SHA-256 559 MB/s vs 10 MB/s software) | Community | 2017-01-26 | 2026-09-29 | No |
| S38 | Immich #15739 (WebCrypto > 2 GB) | Community | 2025-01-28 | 2026-09-29 | No |
| S39 | Immich #25248 (iOS hash failure blocks uploads) | Community | 2026-01-13 | 2026-09-29 | No |
| S40 | restic #2179 (mtime restored with `touch -r`, change missed), #2495 (hard links bump ctime on every file) | Community | 2019-02-21; 2019-12-02 | 2026-10-06 (skeptic, WebFetch) | No |
| S41 | Monochromatic #544 (index copies lose racy protection) | Community | unknown | 2026-09-29 | No |
| S42 | Immich #17023 (imported assets with wrong checksums) | Community | 2025-03-21 | 2026-09-29 | No |
| S43 | Immich mobile `hash.service.dart` | Immich | main | 2026-09-29 | Yes (code) |
| S44 | Go `encoding/base32` (stand-in for blocked RFC 4648) | Go project | master | 2026-09-29 | No (secondary for RFC 4648) |
| S45 | C2SP Wycheproof `testvectors_v1/hmac_sha256_test.json` (174 cases) and `hkdf_sha256_test.json` (86 cases) — `C2SP/wycheproof @ main` | C2SP / Google Wycheproof (v0.9 generator) | main | 2026-10-06 | Yes (test-vector project) |
| S46 | Go `golang.org/x/crypto` v0.57.0 `hkdf/hkdf_test.go` ("Tests from RFC 5869") via proxy.golang.org | Go project | v0.57.0 | 2026-10-06 | No (secondary for RFC 5869) |
| S47 | F3 note — `docs/research/f3-security-literature.md` (C15, M-04, M-14, M-25, M-31, M-32, DR-F3-2) | Project (F3) | updated 2026-10-06 | 2026-10-06 | Project analysis |
| S48 | D1 note — `docs/research/d1-threat-model.md` §7; register `docs/security/threat-model.md` (SR-04, SR-05, SR-15, SR-21, SR-26, AR-06) | Project (D1) | 2026-10-06 | 2026-10-06 | Project analysis |
| S49 | A6 note — `docs/research/a6-homelab-storage-engine.md` (posture A′: fixity without keys; store by SHA-256) | Project (A6), draft | 2026-10-06 | 2026-10-06 | Project analysis (not skeptic-reviewed) |
| S50 | ADR-0007 (Proposed) and `docs/spec/object-format.md` (Draft): `dedup_id` text in the signed record; unpadded hashing; padded cloud sizes | Project (A2) | 2026-10-06 | 2026-10-06 | Project draft |
| S51 | ADR-0008 (Proposed) Decision 7: `S_e`, HKDF label, rotation trigger conditional on DR-A1-1 | Project (D2) | 2026-10-06 | 2026-10-06 | Project draft |
| S52 | "The first practical collision for 31-step SHA-256" (Li, Liu, Wang, Dong, Sun, ASIACRYPT 2024) and "New records in collision attacks on SHA-2" (EUROCRYPT 2024) | IACR | 2024 | 2026-10-06 (reported by skeptic 1 from search results; the pages are blocked from the container) | No (secondary) |
| S53 | Cloudflare D1 limits — `cloudflare-docs @ production : src/content/docs/d1/platform/limits.mdx` ("10 GB (Workers Paid) / 500 MB (Free)") | Cloudflare | production | 2026-10-06 (skeptic 1) | Yes |

## Claims

### Key claims (skeptic-reviewed; verdicts are the code-computed tally)

Skeptics: 1 = sources, 2 = logic, 3 = adversary. "Upheld" means not refuted.

| # | Claim | Sources | Skeptic 1 | Skeptic 2 | Skeptic 3 | Verdict |
|---|---|---|---|---|---|---|
| K1 | ADR-0001 already fixes SHA-256 as the plain content hash and HMAC-SHA256 as the dedup MAC. BLAKE3 would supersede settled text; SHA-256 would not. | S1 | Upheld. Caveat: kind 01 also changes settled text, so K1 supports the *algorithm*, not the construction | Upheld (same caveat) | Upheld | **Verified** |
| K2 | When the plain SHA-256 is also needed, HMAC over the file costs 2 hash computations per byte and HMAC over the digest costs 1. x86: pass 1 668 vs SHA-256 alone 1,136 MB/s (portable 140 vs 299). | S2 §14; A1-S1 | Upheld; reproduced by A1-S1 (CPU s/GB 1.685 vs 0.954) | Upheld; §14's two figures are not strictly like for like (cache vs file) | Upheld; the end-to-end gain is about 1.3×, not 2×, because pass 2 is unchanged | **Verified** |
| K3 | With HMAC over content, rotation needs a homelab re-read (10 TB ≈ 27.8 h at the 100 MB/s BUD-INGEST floor, missing the 24 h target) and a phone re-read (128 GB ≈ 5.9 h at 6 MB/s). With the digest, one HMAC per cached value. | budgets.md; PLAN A1-S2; S1 | **Refuted**: 100 MB/s is a floor, not a read rate (A1-S2 median 508 MB/s ≈ 5.5 h); BUD-AUDIT already reads 10 TB; receipted device files need no new ID | **Refuted**: same, plus scoped or homelab-only presence removes the need to republish | **Refuted**: devices need no full re-read; the 24 h target was written for the digest variant | **Contested**. Withdrawn as stated; restated in §2 as a cost range. Not sole support for anything |
| K4 | While K is secret, HMAC(K, m), HMAC(K, SHA-256(m)) and keyed BLAKE3 are equally opaque to the cloud. After a leak, the digest form allows testing from a SHA-256 alone. | (Borg, Tahoe, Kopia cited; they do not say this) | **Refuted**: the sources MAC content and do not compare; reasoning only; F3 C15 contested; M-32 omitted | Upheld as reasoning; misses M-32 | Upheld; misses the online oracle any enrolled device has | **Secondary-only**. Kept as unsourced hash-then-PRF reasoning; M-32 and the oracle path added (§2) |
| K5 | The digest form inherits SHA-256 collisions even while K is secret. The homelab already depends on SHA-256. | reasoning; S1 | Upheld; cite the state of the art (S52); an insider holding K can attack HMAC with about the same effort | Upheld; "already depends" is partly circular (A6 adopted it at A1's request) | **Refuted**: circular; ADR-0001 uses SHA-256 only to verify; A's advantage applies only to precomputed public pairs | **Secondary-only**. Narrowed to public precomputed pairs; the "already depends" premise dropped |
| K6 | AArch64 SHA-2 is optional (`HWCAP_SHA2`). `sha2` 0.11.0 detects it at run time, otherwise uses software, and has no `asm` feature. Which low-end SoCs lack it is unknown. | S32, S7 | Upheld; incomplete: 32-bit targets always use software | Upheld; same gap | Upheld; same gap | **Verified** (with the 32-bit case added) |
| K7 | The BLAKE3 paper's ARM benchmark is a 32-bit ARM1176 against OpenSSL 1.1.1d SHA-256, without SHA-2 instructions. No primary source compares on ARMv8 phones. | S3 | Upheld; eBACS blocked | Upheld; an absence claim bounded by this sweep | Upheld; the project's own x86 data show BLAKE3 about 4× less CPU | **Verified** |
| K8 | SHA-256 and HMAC-SHA256 are native on Android (API 1+), CryptoKit (iOS 13+, macOS 10.15+) and Workers (`DigestStream`). BLAKE3 is in none. | S33, S34, S36, S27 | Upheld | Upheld; the Worker never sees plaintext, so this is about tooling | Upheld | **Verified** |
| K9 | A lowercase, fixed-length ID with a prefix avoids case collisions on NTFS, FAT and exFAT, cannot be a reserved name or end in a dot or space, and fits R2's 1,024-byte keys. | S28, S31, S26 | Upheld | Upheld; the A1-S3 vectors used another form (fixed, §Spikes) | Upheld; FAT32 per-directory limits not considered (handed to A4) | **Verified** (it applies equally to the base32 body now chosen) |
| K10 | git re-checks entries whose mtime is ≥ the index mtime, and zeroes the cached size of racily clean entries. FAT write time has 2 s resolution. | S10, S29 | Upheld; FAT stores local time (DST) | Upheld; same | Upheld; git uses a filesystem-written reference, while R3 used wall-clock time | **Verified**. R3 revised to a marker-file reference and a FAT local-time rule |
| K11 | restic: on Unix, unchanged = mtime, ctime, size and inode; on Windows, path, size and mtime. mtime-only missed a change (#2179); ctime gives false positives after hard-linking (#2495). | S12, S40 | Upheld; #2179 is a demonstrated case, not a field incident | Upheld; the issue parts are community sources | Upheld | **Verified** (doc parts primary; issue parts secondary) |
| K12 | Tahoe: changing the convergence secret starts a new dedup domain (storage can double until GC); the secret plus a copy of a file allows confirmation. | S20 | Upheld; the transfer to Reliquary is wrong (store by SHA-256) | Upheld; same | Upheld; Reliquary has no GC | **Verified** as a statement about Tahoe. Its use in DR-A1-2 option B is corrected (re-uploads, not storage) |
| K13 | Keeping 256 bits costs about 16 B per row (≈ 160 MB binary per 10⁷ rows), small against D1's 10 GB cap. Truncating to 128 bits gives a key holder a 2⁶⁴ collision attack. | S16, fact-check item 5 | Upheld; the 10 GB cap is Workers Paid only (500 MB Free, S53) | Upheld | Upheld | **Secondary-only** (no primary source for the cost; SP 800-107 blocked). Not load-bearing (§3) |

### Other claims (not key; not skeptic-reviewed)

| # | Claim | Sources | Status |
|---|---|---|---|
| C6 | One 2017 community measurement: 559 MB/s SHA-256 with ARMv8 instructions vs 10 MB/s in software on one phone | S37 | Secondary; indicative only |
| C13 | Duplicacy names chunks by a keyed hash of a stored hash (MAC over MAC) | S17 | Primary code; nearest precedent for kind 01 |
| C18 | Bao's root hash equals BLAKE3; age STREAM authenticates 64 KiB chunks | S6, S2 | Primary |
| C19 | One-shot WebCrypto `digest()` failed above 2 GB in a browser; second implementations must stream | S38 | Secondary |
| C20 | 2025 keyed-CDC chunking attacks (F3 owns them) | S13 | Primary mention; papers not read |
| C21 | `sha2` 0.11.0 README: "All other targets: use soft", and `cpufeatures` is a dependency only for aarch64/x86/x86_64 (and loongarch64), so 32-bit ARM builds use software SHA-256 | S7 (skeptics 1–3, 2026-10-06) | Primary; not separately tallied |
| C22 | Under A6's posture A′, fixity audits read ciphertext and need no key | S49 | Project draft (A6 not yet skeptic-reviewed) |
| C23 | End to end on x86 (arithmetic from §14): content form ≈ 387 MB/s, digest form ≈ 509 MB/s (default); ≈ 100 vs ≈ 162 MB/s (portable) | S2 | Arithmetic, not measured |
| C24 | The nested form (kind 04) rotates from the cache, needs the bytes to test after a leak, and does not inherit unkeyed SHA-256 collisions | reasoning (skeptics 2 and 3) | Analytical; not skeptic-reviewed |

## Findings

### 1. Hash algorithm: SHA-256, with a stricter decision rule

- **Settled and portable.** ADR-0001 names SHA-256 (K1). It is native on Android, Apple platforms and Workers, and `sha256sum` reads it (K8). BLAKE3 needs a superseding ADR. Confidence: high.
- **Speed, measured on x86 only (A1-S1).** With hardware paths, one core of BLAKE3 used 0.224 CPU s/GB and SHA-NI SHA-256 0.914, about 4× less for BLAKE3. Both are far above BUD-HASH. On x86, neither CPU time nor energy limits any budget, which is why the portability argument wins there.
- **Phones: unmeasured.**
  - The BLAKE3 paper says nothing about ARMv8 with SHA-2 instructions (K7).
  - One secondary figure suggests hardware SHA-256 is about 90× the BUD-HASH effective floor (C6).
  - Risk classes for slow SHA-256:
    - (a) AArch64 cores without `HWCAP_SHA2` (K6);
    - (b) **any 32-bit `armeabi-v7a` build**, where `sha2` 0.11 always uses software, even on ARMv8 cores with crypto extensions (C21; raised by all three skeptics).
  - The A1-S1 kit already records the ABI list (`ro.product.cpu.abilist`) and has a 32-bit build path. It does not yet benchmark other backends.
- **Decision rule (replaces the earlier one):**
  1. SHA-256 (`sha2`) meets BUD-HASH on the low-end class without throttling → SHA-256 is final.
  2. Otherwise, on the same device and ABI, measure other SHA-256 backends: `ring`, `aws-lc-rs`, and platform `MessageDigest` via JNI. Whether they have AArch32 hardware paths is **unverified**. If any of them meets BUD-HASH → SHA-256 with that backend.
  3. Only if no SHA-256 backend meets BUD-HASH while BLAKE3 (NEON) does → raise a decision request to supersede ADR-0001's algorithm.
  - Report BUD-BAT-S for every candidate.

### 2. Construction: where the family key is applied (DR-A1-1)

The algorithm and the structure are separate questions. The rows below assume SHA-256. "Pass 1" is the hashing pass; pass 2 (encryption) is the same in every option (CE §14), so **every option reads each file twice** (correcting the earlier "reads the file once").

| Property | **A** kind 03: HMAC(K, 0x03 ‖ content) | **B** kind 01: HMAC(K, 0x01 ‖ SHA-256(content)) (proposed) | **N** kind 04: HMAC(K, 0x04 ‖ HMAC(K_root, content)) | Keyed BLAKE3 over content |
|---|---|---|---|---|
| Hash computations per byte in pass 1, with the plain SHA-256 also needed | 2 (K2) | **1** (K2) | 2 | 2 (SHA-256 + BLAKE3) |
| x86 CPU s/GB, in memory (A1-S1) | 1.685 (C1) | **0.954** (C2) | ≈ 1.685 (same work as C1, not measured separately) | 1.135 (C5) |
| End-to-end client pipeline, x86 (arithmetic, C23) | ≈ 387 MB/s | ≈ 509 MB/s | ≈ 387 MB/s | n/a |
| Homelab verification at ingest | 2 hashes per byte | 1 per byte + one HMAC | 2 per byte | 2 per byte |
| Re-derive IDs from the cache with no file reads | **No** | Yes (A1-S2) | Yes (same mechanics) | No |
| Rotation cost at the homelab (10 TB) | Full re-read: ≈ 5.5 h at the measured 508 MB/s compute, ≈ 28 h at the 100 MB/s floor; disks unmeasured. Under A′ (C22) also needs the offline archive key online and a full decrypt, so it cannot ride on a keyless fixity read. Lazy re-derivation possible under DR-F3-2 D/E | Seconds to minutes from the catalog | Same as B (from the catalog `inner`) | Like A |
| Rotation cost per device | Only pending and un-receipted entries plus new files; **no full library re-read** (skeptics) | Seconds per 1M entries (x86) | Same as B | Like A |
| Opaque to the cloud while K is secret | Yes (K4, reasoning) | Yes (K4, reasoning) | Yes (reasoning) | Yes |
| After S_e leaks: what testing needs | The file's bytes | **A SHA-256 value** (public hash lists; a stolen device's own cache, M-32) | The file's bytes (K_root alone does not help without a current S_e) | The bytes |
| Inherits unkeyed SHA-256 collisions | No (but an insider holding K gets no more protection than SHA-256's own; K5) | Yes, for public precomputed pairs | No (same insider caveat) | No |
| Secrets | S_e | S_e | S_e + never-rotated S_root | S_e |
| Matches settled text | Yes (plus HKDF epoch keys, as T1 D-4 already proposed) | No (MAC over the digest) | No (MAC over a MAC of the content); closest in spirit | No |

**What changed after the skeptic review:**
- **The rotation argument is narrower.** Under A, rotation is a heavy but feasible homelab job. Devices need new IDs only for files without a receipt (K3 contested; F3 C15/M-25 agree). B's remaining rotation advantages:
  - it is immediate and cheap at the homelab (A1-S2);
  - it does not need the archive key online if A6 adopts posture A′ (C22, a draft);
  - a later change of key **scope** (DR-F3-2 option F) or label is cache-only.
- **B's main verified advantage is pass-1 cost.** Half the hash work per byte (K2). On x86 that is about 1.3× end to end (C23). On phones the effect on energy is unknown; if phones are I/O-bound, the time gain shrinks.
- **B's exposure is wider than first written** (K4 secondary-only; M-32; adversary skeptic):
  - a stolen device's plaintext hash cache, plus its S_e, becomes testable against the family's IDs;
  - while a compromised device is still enrolled, it can bulk-test **public SHA-256 lists** (for files it does not have) through the presence answer, at whatever rate the Worker allows. Rotation does not help until the device is revoked.
  - Under A or N, both attacks need the files. Mitigations that apply to every option: DR-F3-2 scoping, rate limits and alerts (SR-21), the hash cache encrypted under an OS keystore key (M-32, B6).
- **Collisions** (K5 secondary-only): narrowed to public precomputed SHA-256 pairs. No full-SHA-256 collision is known. The reported best is a practical collision on 31 of 64 steps (S52, secondary; eprint blocked).
- **New alternative N** (C24, from two skeptics): it combines B's cheap rotation with A's "needs the bytes" property, at A's per-byte cost. Next to A, its only downsides are the extra S_root and the `inner` column. It is analytical and not skeptic-reviewed.

**Assessment.**
- B is proposed because its advantages are verified (K2) or measured (A1-S2), and its downsides are narrow reasoning-based exposures the owner can knowingly accept.
- N is the right choice if the owner weighs "a leaked key alone cannot test hash lists" above about half the pass-1 hashing energy on phones. A1-S1 measures that energy (C1 vs C2 on the low-end class).
- A is supported but not recommended: as far as the reasoning goes, N gives the same post-leak property with much cheaper rotation.
- Confidence in B over N: **medium-low**. It needs A1-S1 phone energy and the owner's weighting.

**Key derivation** (all options): the family secret is only HKDF input material, with a separate key per purpose, kind, epoch and scope. Precedents: Tarsnap per-purpose keys (S19); Kopia's versioned labels (S16); BLAKE3 paper §7 on key reuse (S3). Putting the epoch and kind in `info` keeps keys separate even if D2 ever ratchets S_{e+1} from S_e (adversary skeptic). The exact bytes are in `identifiers.md` §3. Proposed ADR-0008 Decision 7 writes the bare label `reliquary/v1/dedup-id-key`; the bare label is a **forbidden** value (vector N03), and D2 should cite `identifiers.md` instead.

### 3. Wire format and encoding

- **Binary form** `kind ‖ u16be(epoch) ‖ mac` (35 B). **Text form** `rd1-<kk>-<eeee>-<52 base32>` (64 chars).
  - `rd1` is the text-syntax version.
  - The kind byte is the construction version: a new construction gets a new kind and is never reused. This resolves the skeptics' "rd1 conflates version and kind".
  - Kind 02 (chunk list) now has a defined text spelling.
- **Base32 for IDs, hex for plain SHA-256** (changed from the earlier hex-only proposal):
  - Both are single case and safe on NTFS, FAT and exFAT and in R2 keys (K9).
  - Base32 is chosen so a dedup ID cannot be shaped like a plain SHA-256: the Worker and log scrubbers can reject bare 64-hex values (vector E15).
  - It is 12 characters shorter.
  - The harness had already implemented and cross-checked it in three languages.
  - Plain SHA-256 stays hex to match `sha256sum`. The `sha256sum`-compatibility argument never applied to the keyed ID.
  - The alphabet source is secondary (S44; RFC 4648 blocked), cross-checked against Python `base64`.
- **Full 256 bits.**
  - It is the primitive's natural output and avoids a 2⁶⁴ collision attack by a key-holding device. That matters because a forged collision makes the Worker answer "present" for a victim's different file (silent non-upload; skeptic 1 on K13).
  - The size cost is secondary-only arithmetic (K13): about 160 MB binary per 10⁷ rows. D1's cap is 10 GB on **Workers Paid** and 500 MB on Free (S53), so on Free the margin is not small.
  - Not load-bearing.
- **Strict canonical parsing:** 25 encoding negatives in the vectors.
- **USB bundles:** a 64-character long filename takes about 6 FAT directory entries (5 LFN + 1 short entry, arithmetic). FAT32 per-directory entry limits are unverified (the FAT spec was not fetched), so sharding is handed to A4.
- **R2 keys:** whether an R2 object key contains the dedup ID at all (ADR-0001 §4 step 2 says it does) is **OD-04's** decision (D1, F3 C33, SR-26). It is not an A1 hand-off.

### 4. Whole-file digest vs block or tree hash

Unchanged.
- Whole-file SHA-256 identity.
- Per-part integrity in transit from age STREAM (C18).
- No Dropbox block hash (stock tools cannot reproduce it).
- No Bao (it only pays off if BLAKE3 were chosen).
- Kind 02 reserved.
- No CDC (C20, F3).
- Confidence: medium-high.

### 5. Rotation (ID side; D2 owns custody and the trigger)

1. The homelab creates S_{e+1} and keeps every S_e (old bundles, late uploads).
2. The homelab re-derives:
   - kinds 01 and 04 from the catalog (`sha256` or `inner`);
   - kind 03 by a full decrypt-read (§2).
   - This requires A6's catalog to keep these columns for every item.
3. **The cloud's epoch-e ID history is flushed**, and devices re-seed presence under e+1 (F3 M-14, preferred).
   - The earlier "publish the new IDs as a set" is withdrawn as a privacy measure. Old and new IDs are probably linkable through device batch timing, set sizes and padded-size classes (ADR-0007 makes every cloud-visible size the padded size, which narrows but does not remove the size channel).
   - The residual goes to **AR-06** (OD-17).
4. Non-revoked devices get S_{e+1} sealed (D2/D3) and re-derive (kinds 01/04) or compute only what is pending (kind 03).
5. Retired epochs get a "stale key" answer after a grace window, and never "present". A3 and C1 own the protocol response.
6. **What rotation achieves:** a holder of S_e can no longer compute IDs that are valid after the rotation, nor test a post-rotation index copy. Rotation does not protect anything copied before it (M-04), does not remove size-only fingerprinting (no key needed, F3-S1), and does nothing while the compromised device is still enrolled.

### 6. Hash-cache contract (A1 owns the contract; B5, B2 and B4 supply the signals)

The normative text is in `identifiers.md` §9 (R1–R8). Changes from the earlier draft:
- **Renumbering:**
  - old R1–R5 stay;
  - old R9 (sampled re-verification) becomes R6;
  - old R10 (re-check after open) becomes R7;
  - old R8 (cache provenance) stays, minus the "exclude from OS backups" part.
- **Handed to their owners** (logic skeptic, PLAN §2.1):
  - old R6, "a hit is never protection; receipts only": A3 and SR-05;
  - old R7, "hash failed" state: E3;
  - the OS-backup exclusion, cache encryption and MAC (M-31, M-32): B6.
- **R3 racy window:**
  - The reference time is now the mtime of a marker file written on the same volume at scan start, mirroring git's index-file comparison (K10; adversary skeptic). It is no longer wall-clock time.
  - FAT local-time and DST shifts of whole hours are treated as changes (rehash), never skipped (skeptics 1–3, S29).
- **R1:** Windows `ChangeTime` is used only if B5 shows it is reliable *and* cannot be set from user mode (it is a field passed to `SetFileInformationByHandle`; adversary skeptic). restic's signals and failure modes (K11) set the Unix list.

### 7. Items with no device of origin (A9)

Unchanged. The ID is a pure function of the bytes and the epoch key, and provenance goes in the metadata record. The importer equality is now enforced by test: the homelab importer must pass the same `identifiers-vectors.json` suite with streaming input (`identifiers.md` §10). The vectors cannot prove that the importer *uses* the function; conformance testing does.

### 8. Presence oracle and dedup scope (new, from the logic skeptic)

- F3 (DR-F3-2) and D1 §7 propose narrowing the cloud's "present" answer:
  - per-person scope below a threshold (C);
  - no presence answer below a threshold (D);
  - homelab-only dedup (E; the skeleton default);
  - **per-person dedup keys** (F).
- These interact with this door:
  - **Option F changes key derivation.** `identifiers.md` reserves it through the `scope=` field of the HKDF info (v1: `scope=family`). Under kinds 01 and 04, moving to per-person scopes later is a cache-only re-derivation. Under kind 03 it is a full re-read.
  - **Under D or E**, the cloud does not need a re-keyed cross-device index after rotation, so A's homelab rotation cost matters less. B's and N's rotation advantage is largest under A–C.
  - **The realistic leak path is the live oracle** used by a compromised, still-enrolled device (D1 T-11, F3 C11), not an attacker who later obtains an index copy. Against it, every construction is protected only by scoping or revocation. B additionally exposes public hash lists to that device (§2).
- So DR-A1-1 and DR-F3-2 should be **decided in the same sitting**, before Gate A, as F3 already asks.

### 9. Scout conflicts resolved (unchanged)

- Borg ID re-verification is optional (S15).
- Tahoe confirmation needs the secret **and** the file (S20).
- The BLAKE3 ARM figure is ARMv6 (K7).
- bao-tree is 0.16.1; the git racy document is `.adoc`; `sha2` has no `asm` feature (K6).

### Skeptic issues and how they were handled

| Issue (severity, lens) | Handling |
|---|---|
| A1-S3 vectors do not cover the recommended construction or encoding (major; all three) | **Fixed.** A1-S3 follow-up regenerated 111 vectors for the exact draft spec (kinds 01/03/04, HKDF info with kind, epoch and scope, `rd1` text and binary forms, encoding negatives including bare hex, importer conformance rule). Rust, Python and Node agree; Wycheproof and RFC 5869 (via Go) pass. The first A1-S3 is relabelled "harness validated on candidates". |
| Rotation-cost argument overstated; ignores F3's contested verdict (major; all three) | **Fixed.** K3 marked contested and withdrawn. §2 restates A's cost as a range: no device-wide re-read; possible laziness under DR-F3-2 D/E. "Never retired" removed. F3 C15/M-25 cited. One new consideration added in the other direction: under A6 posture A′ the fixity read is keyless, so A's re-derivation cannot ride on it (C22, draft). |
| 32-bit Android gets software SHA-256 (major; all three) | **Fixed** in the §1 decision rule (try other SHA-256 backends per ABI before BLAKE3). The A1-S1 kit records the ABI already. **Open:** the kit has no step to benchmark other backends; a kit addendum is listed as follow-up. |
| DR-A1-2 option B misstates its cost (major; sources, logic) | **Fixed.** Option B's cost is now re-upload traffic, battery and staging churn plus silent dedup misses. Storage is unaffected (store by SHA-256). |
| Presence oracle and dedup scopes ignored (major; logic) | **Fixed.** New §8; `scope=` in the HKDF info; DR-A1-1 is tied to DR-F3-2. |
| Online membership oracle ignored in B's risk (major; adversary) | **Fixed.** §2 and DR-A1-1 risk rows. Mitigations handed to A3/C1/F3 (scoping, alerts) and B6 (cache encryption). |
| Missed alternative: nested keyed digest (logic, adversary) | **Added** as option N (kind 04), vectored. |
| Default "draft on B" runs ahead of the owner (minor; logic, adversary; conflicts lists) | **Fixed.** The spec and vectors cover all three kinds. Default: no production hashing under any kind. ADR-0008's B-specific label is flagged to D2. |
| C1 hand-off contradicts ADR-0001 §4 step 2 (minor; sources, logic) | **Fixed.** Routed to OD-04 and listed under Conflicts with settled text. |
| Contract rules reach into other owners' artifacts (minor; logic) | **Fixed.** Old R6–R8 parts and the Worker behaviour handed to A3, E3, B6 and C1. |
| R3 wall clock; FAT local time and DST (minor; all three) | **Fixed** (§6). |
| Text form conflates version and kind (minor; sources, logic) | **Fixed** (§3). |
| Cloud ID shaped like plain SHA-256 (minor; adversary) | **Fixed.** Base32 body; E15 negative. |
| "Halves hashing / faster first backup" without the end-to-end figure; "reads once" wrong (minor; logic, adversary) | **Fixed.** C23 (≈ 1.3× on x86, arithmetic); two passes stated; "faster first backup" dropped. |
| x86 BLAKE3 data unused (minor; adversary) | **Fixed** (§1). |
| Collision analysis circular; cite the state of the art (minor; sources, adversary) | **Fixed.** K5 narrowed; S52 cited as secondary; eprint access requested from H1. |
| "Rotation stops all testing" ignores the size channel; M-14 and M-32 missing (minor) | **Fixed** (§5, §2). |
| A1-S2 "pass" is x86 only (minor; sources) | **Fixed.** Reported as "pass (x86 reference)". The phone run is required in the kit addendum (follow-up). |
| D1 cap without the plan (minor) | **Fixed** (§3, S53). |
| Wycheproof reachable in place of the RFC appendices (minor) | **Fixed** (S45, S46; A1-S3 follow-up). |
| USB FAT32 directory limits (minor; adversary) | **Handed to A4** (unverified). |
| eBACS as a primary benchmark source (missed alternative) | **Logged** as blocked; H1 request. |
| SHA-512/256 as a software fallback on 64-bit cores without SHA2 (logic, missed alternative) | **Not evaluated.** It would supersede ADR-0001's algorithm like BLAKE3 does. It goes into the §1 step-3 decision request only if step 2 fails. |
| Server-aided or OPRF dedup keys (logic, missed alternative) | **Not adopted.** D1 and F3 keep them open. They conflict with the outbound-only homelab and the settled construction. |

### Alternatives compared

| Option | Fit with settled requirements | Pros | Cons | Evidence |
|---|---|---|---|---|
| A: SHA-256 + HMAC over content (kind 03) | Exact (with HKDF epoch keys) | Testing needs the bytes; no public-collision inheritance | 2 hashes per byte; homelab rotation is a full decrypt-read | K2; K3 (contested, restated) |
| **B: SHA-256 + HMAC over SHA-256 (kind 01), proposed** | Needs DR-A1-1 | 1 hash per byte; rotation and scope changes from the cache | Testing hash lists after a leak (including M-32); public SHA-256 pairs | K2, A1-S2; K4, K5 (secondary-only) |
| N: nested keyed digest (kind 04) | Needs DR-A1-1 (closest in spirit) | Rotation from the cache; testing needs the bytes | 2 hashes per byte; extra S_root | C24 (analytical) |
| BLAKE3 + keyed BLAKE3 | Supersedes the algorithm | About 4× less CPU on x86; Bao | Not native anywhere; phones unmeasured | K7, K8, A1-S1 |
| Per-person dedup keys (F3 option F) | Changes the key (DR-F3-2) | Closes the cross-person oracle cryptographically | Loses cross-person upload-skip at every size | F3 C32 (analytical) |
| Tree or block hash + HMAC over the root | Supersedes ADR-0001 | Per-part plaintext verification | Tooling; age STREAM already covers transit | C18, S22 |
| FastCDC per-chunk IDs | Out of v1 | Sub-file dedup | 2025 attacks | C20 |

### Similar work and lessons

| Project | What they do | Borrow or avoid | Source |
|---|---|---|---|
| git | Racy-clean rule against the index file's own mtime; SHA-256 transition via a repository flag | Borrow the filesystem-reference racy rule; avoid untagged IDs | S10, S11 |
| restic | mtime+ctime+size+inode on Unix; unkeyed SHA-256 IDs; hex names | Borrow the signals; avoid unkeyed IDs | S12–S14, S40 |
| Borg 2 / Kopia | ID = MAC(id_key, **content**); named, versioned schemes; Kopia truncates to 128 bits | Borrow keyed IDs and versioned labels; do not truncate. Not precedent for the digest form | S15, S16 |
| Duplicacy | ID = keyed hash of a stored hash | Nearest precedent for kind 01 | S17 |
| Tarsnap | Separate HMAC key per purpose | Borrow per-purpose derivation | S19 |
| Tahoe-LAFS | Convergence secret = dedup domain; documented attacks | Borrow the threat statement. Its storage-doubling cost does not apply (store by SHA-256) | S20 |
| bupstash | Put-only keys hold hash keys but cannot decrypt | Matches "devices append only" | S18 |
| Immich | Mobile hash cache; failure states | Borrow the explicit failure state (E3) | S39, S43 |
| Wycheproof | Cross-library test vectors with invalid cases | Use as the primitive conformance set | S45 |

### Tools and libraries

| Name | Purpose | Licence | Maturity | Source |
|---|---|---|---|---|
| RustCrypto `sha2` 0.11.0 | SHA-256; SHA-NI/AArch64 detection at run time; software on 32-bit ARM | MIT/Apache-2.0 (verify at G3) | Latest per index 2026-10-06 | S7 |
| RustCrypto `hmac` 0.13.0, `hkdf` 0.13.0 | HMAC, HKDF | MIT/Apache-2.0 (verify) | Built and checked against Wycheproof 2026-10-06 | S8, S45 |
| `ring` / `aws-lc-rs` / platform `MessageDigest` | Candidate SHA-256 backends for 32-bit or no-SHA2 phones | — | **Not evaluated**; AArch32 hardware paths unverified | §1 |
| `blake3` 1.8.7 | Benchmark comparison only | CC0/Apache-2.0 (verify) | — | S9 |
| Node `node:crypto`, Python `hashlib`/`hmac` | Second and third implementations for vectors | — | Node 22.22.2, Python 3.11.15 | A1-S3 follow-up |
| C2SP Wycheproof | Primitive test vectors | Apache-2.0 (not committed) | main, 2026-10-06 | S45 |

## Spikes

| Spike | Hypothesis | Pass → / fail → (decision) | Exec tag | Budget IDs | Data class | Status | Result |
|---|---|---|---|---|---|---|---|
| A1-S1 (CT part, x86 reference) | Hashing once and MACing the digest (C2/C4) costs about half of a second keyed pass (C1/C3); BLAKE3 uses less CPU than hardware SHA-256; on x86, I/O is not the bottleneck | Reference only. Cannot pass or fail BUD-HASH or BUD-BAT-S, which are defined on a low-end phone | CT | BUD-HASH, BUD-BAT-S | `SYN → results` | **Ran; inconclusive** (by design) | One contended KVM Xeon VM (SHA-NI, AVX-512), CPU pressure 78–97 %. In memory, CPU s/GB: SHA-256 0.914; C1 1.685; **C2 0.954**; BLAKE3 0.224; C3 0.427; C4 0.233; C5 1.135. Software-only: C1 7.456 vs C2 3.794. Cold-file MB/s: read 1974, C1 460, C2 680, C4 2194. **Energy: no result** (no RAPL). [`spikes/A1-S1/README.md`](../../spikes/A1-S1/README.md), raw `evidence/*.jsonl` |
| A1-S1 (OL part: 4 device classes, energy, thermal) | On ARMv8 phones with SHA-2 instructions, SHA-256 meets BUD-HASH widely; without them BLAKE3 is clearly faster; C2 ≈ half of C1 everywhere; I/O limits at least one phone class | Pass → SHA-256 final (ADR-0006 Decision 1); fail → the §1 rule (other SHA-256 backends, then BLAKE3). C1 vs C2 energy informs B vs N (DR-A1-1) | OL | BUD-HASH, BUD-BAT-S | `SYN → results` | **Kit-ready** (addendum needed) | Kit: [`docs/research/kits/A1-S1/`](kits/A1-S1/README.md) (Android over wireless adb, desktop scripts, 30-min soak, battery and thermal readings, ABI list, 32-bit build path). **Addendum before running (follow-up):** benchmark `ring`/`aws-lc-rs`/platform `MessageDigest` per ABI; make the A1-S2 phone rotation run required, not optional |
| A1-S2 Rotation over a 1M-entry cache | Digest form: a 1M-entry client cache rotates in < 60 s with zero file reads; the homelab re-derives in < 24 h; the content form needs a full re-read | Pass → rotation-from-cache mechanics confirmed for kinds 01/04; content-form cost recorded | CT | (PLAN criterion; BUD-HASH for re-read cost) | `SYN → results` | **Pass (x86 reference)**; phone and homelab-disk confirmation pending | SQLite (rusqlite 0.40.2, WAL), 1M rows, 152 MB: in-place rotation 3.22–5.86 s wall, 2.0–3.5 CPU s; map mode 6.07 s. **Zero source-file reads** under strace. Homelab compute: 5M IDs in 1.53 s in memory. Content-form re-read: 4 KiB files 106–119 µs each cold; 1 GiB at 92–729 MB/s (median 508). Arithmetic (not measured): 10 TB ≈ 5.5 h at 508 MB/s, ≈ 30 h at 92 MB/s. Exercised the A1-S3 candidate-b labels, not the draft spec's (same mechanics). [`spikes/A1-S2/README.md`](../../spikes/A1-S2/README.md) |
| A1-S3 Vectors (candidate harness) | Rust and an independent implementation agree on ≥ 50 vectors incl. empty, > 4 GiB, and domain-separation negatives | Pass → harness validated | CT | — | `SYN → results` | **Pass for the harness on candidates only** | 51 vectors for candidates a–d (`rq1-…` base32 form): Rust 51/51, Node 51/51, Python 27/27; both BLAKE3 libraries 35/35 on the official vectors. **Did not cover the recommended construction or encoding** (skeptic major issue). [`spikes/A1-S3/README.md`](../../spikes/A1-S3/README.md) |
| A1-S3 follow-up: vectors for the draft spec | The exact `identifiers.md` bytes (kinds 01/03/04, HKDF info with kind/epoch/scope, `rd1` forms) reproduce across three independently written implementations, and the primitives match published reference vectors | Pass → `identifiers-vectors.json` is the conformance set for ADR-0006 | CT | — | `SYN → results` | **Pass** (run by the synthesis stage, 2026-10-06) | **111 vectors** (72 positive incl. 0 B and 2³²−1, 2³², 2³²+1 B; epochs 0, 1, 0x0102, 0xffff; 14 domain-separation negatives; 25 encoding negatives). Rust (RustCrypto), Python (stdlib, own HKDF) and Node (`node:crypto`) agree 111/111. Wycheproof HMAC-SHA256 174/174 and HKDF-SHA256 86/86, plus 4 Go/RFC 5869 HKDF cases, pass in Rust and Python. `sha256sum` and `openssl` agree on the 2³²+1 case. Python and Node share OpenSSL primitives; RustCrypto is the independent primitive. [`spikes/A1-S3/identifiers-v1/README.md`](../../spikes/A1-S3/identifiers-v1/README.md) |

No emulator stood in for any device. All CT figures come from one shared x86 VM and are labelled as such.

## Conflicts with settled text

1. **CLAUDE.md** "Cross-user dedup uses HMAC(family secret, content)", and **ADR-0001 §2** "Dedup ID = HMAC-SHA256(family dedup secret, content)". Kinds 01 and 04 deviate in construction (and the HKDF epoch keys in key use). Kind 03 matches. → **DR-A1-1**. Nothing was edited.
2. **ADR-0001 §3** cache key `(source locator, size, mtime, platform file ID)`. The contract adds change time or a version token, a racy rule, a FAT rule and provenance. This is an extension, not a contradiction; ADR-0006 says it amends §3.
3. **ADR-0001 §4 step 2** "objects are keyed by dedup ID". The earlier A1 hand-off ("never key R2 objects by dedup ID alone") is withdrawn as a hand-off and routed to **OD-04** (D1, F3 C33, SR-26).
4. **CLAUDE.md** "Cross-user dedup uses HMAC(family secret, content)" vs **per-person keys** (DR-F3-2 option F): F3's question, decided together with DR-A1-1.
5. **Not a conflict, but premature:** Proposed ADR-0008 Decision 7 already uses a B-specific HKDF label and makes the rotation trigger conditional on "construction B". → Question to D2 (align the label with `identifiers.md`; make the condition "kind 01 or 04").

## Open questions

- Which low-end Android SoCs lack `HWCAP_SHA2`? Are 32-bit-only phones in the fleet? How fast are `ring`, `aws-lc-rs` and platform `MessageDigest` there? → A1-S1 (kit addendum), H5 (L12c purchase).
- Phone energy per GB for C1 (A/N) vs C2 (B) (BUD-BAT-S). This decides B vs N on cost. → A1-S1.
- Rotation trigger policy and owner time (BUD-SUPPORT). → D2, with costs from A1-S2.
- Grace window for retired epochs, and offline devices across a rotation. → A3, D3, E3.
- Is Windows `ChangeTime` reliable, and can user mode set it? → B5.
- Sampling rate for R6 re-verification against BUD-SCAN and BUD-BAT-D. → B5.
- FAT32 per-directory entry limit and bundle sharding. → A4.
- Per-person scope values if DR-F3-2 option F is chosen. → F3, A1 (Wave 2).
- Blocked primary sources (RFC 2104/4231/4648/5869, FIPS 180-4, SP 800-107, eprint, eBACS). → H1 access request. Wycheproof and Go's tests stand in for the primitives.
- F3 has given no verdict on the B/N/A security trade (its C15 is contested). F3 should review C24 (option N) and the oracle exposure in Wave 2, if the owner does not decide first.

## Recommendation

1. **Algorithm:** SHA-256, as ADR-0001 says, confirmed at Gate A by A1-S1 under the §1 decision rule (other SHA-256 backends before BLAKE3).
2. **Format (DR-A1-2 plus `identifiers.md`):**
   - kind byte and u16 epoch in every ID;
   - full 256 bits;
   - binary `kind ‖ u16be(epoch) ‖ mac`;
   - text `rd1-<kk>-<eeee>-<52 lowercase base32>`;
   - plain SHA-256 stays 64 lowercase hex;
   - strict parsing;
   - HKDF info `reliquary/v1/dedup-id-key/kind=kk/epoch=eeee/scope=family`.
3. **Construction (DR-A1-1):**
   - **kind 01** (HMAC over the SHA-256 digest), *if* the owner accepts that a leaked key can test lists of SHA-256 values. It rests on K2 (verified) and A1-S2 (measured).
   - **Kind 04** (nested) if the owner does not accept that; A1-S1 gives its phone cost.
   - Kind 03 (settled wording) remains a supported fallback at a higher rotation cost.
   - Decide together with DR-F3-2.
4. **Identity layers:** plain SHA-256 is the permanent, key-independent identity. The dedup ID is a per-epoch alias the cloud sees. A6 should address the store and catalog by SHA-256 (and keep `inner` if kind 04).
5. **Cache contract:** `identifiers.md` §9 R1–R8. Receipt, status and cache-protection rules go to A3, E3 and B6.
6. **No tree hash and no CDC in v1.** Kind 02 is reserved.

**What would change this:**
- A1-S1 shows no SHA-256 backend meets BUD-HASH on the low-end class → BLAKE3 decision request.
- A1-S1 shows C1 costs little more than C2 on phones (I/O-bound) → prefer kind 04.
- A practical full-SHA-256 collision → kind 04 or a new kind.
- The owner rejects any deviation from the settled wording → kind 03.
- The owner picks DR-F3-2 option F → a per-person `scope` (cheap under 01 and 04).

## Decision requests

### DR-A1-1: How the family key is applied to a file (H1 to assign an OD number)
- **Needed by:** Gate A (one-way door #1), before any real family file is hashed with production secrets. Decide together with DR-F3-2 (F3) and OD-08 (D2).
- **Evidence:**
  - this note (§2, §5, §8, K2, K3–K5, C22–C24);
  - ADR-0006 (Proposed);
  - `identifiers.md` and its vectors (all three kinds);
  - F3 C15 (contested), M-14, M-25, M-32.
- **Options:**

  | Option | What it means for the family | Cost (money and owner time) | Reversibility | Risks |
  |---|---|---|---|---|
  | A. kind 03: HMAC over the whole file (the settled wording, with yearly epoch keys) | Same privacy; a leaked key still needs the actual files to test | Phones: 2 hashes per byte in the hashing pass (x86: 1.69 vs 0.95 CPU s/GB; phones unmeasured). A rotation means a homelab job that re-reads and decrypts the whole store (≈ 6–30 h for 10 TB; disks unmeasured; needs the archive key online under A6's A′). Devices re-hash only files not yet confirmed | One-way door; a later change of scope or label means a full re-read | Owner reluctant to rotate because of the cost |
  | **B. kind 01: HMAC over the file's SHA-256 (proposed)** | Same privacy while the key is safe | Lowest phone hashing cost (1 hash per byte; ≈ 1.3× end to end on x86, arithmetic); rotation and later scope changes in seconds per device, minutes at the homelab, no file reads | One-way door, but labels and scope re-derive from caches | A leaked key can test **lists of SHA-256 values** without the files: a stolen phone's own hash cache, or public hash lists through a still-enrolled compromised device. Relies on no public SHA-256 collision (none known; secondary source). Changes the settled wording |
  | N. kind 04: HMAC over a keyed content MAC (nested) | Same privacy; a leaked key still needs the actual files | Same phone hashing cost as A; rotation as cheap as B; one extra never-rotated secret to deliver (D2) | As B | New and analytical (not skeptic-reviewed); changes the settled wording (closest in spirit) |
  | C. keyed BLAKE3 | Same privacy | Bundled library everywhere; supersedes the algorithm | One-way door | Only if A1-S1 shows no SHA-256 backend meets BUD-HASH |

- **Recommendation:** **B**, if the owner accepts the hash-list exposure. Otherwise **N**. Its phone cost comes from A1-S1, which must run before Gate A anyway. A is supported but dominated by N on rotation.
- **Touches settled text:** yes for B, N and C. Affected: the CLAUDE.md "Encryption trust model" line, and the ADR-0001 §2 row (amended by ADR-0006). A still adds HKDF epoch keys, which is a key-use detail.
- **If no decision by the deadline:** nothing is hashed with production secrets under any kind. Prototypes (A0) may use any kind with test secrets. The spec and vectors already cover all three kinds, so no drafting work waits on the answer.

### DR-A1-2: Epoch-tagged dedup IDs, with retired epochs refused after a grace window
- **Needed by:** Gate A (with DR-A1-1 and OD-08/D2).
- **Evidence:** §3, §5; K12 (corrected transfer).
- **Options:**

  | Option | What it means for the family | Cost | Reversibility | Risks |
  |---|---|---|---|---|
  | A. Epoch in every ID; the Worker answers "stale key" for retired epochs (proposed) | A device that missed a key update is told to fetch it; old USB bundles stay verifiable | 2 bytes per ID; a key-update path (D2/D3) and a nudge (E3) | Costly to add later (every ID changes) | Offline devices need a clear "update" path |
  | B. No epoch; a rotation silently starts a new dedup domain (Tahoe style) | Devices that missed the update keep sending old-key IDs that never match | Re-upload traffic, phone battery and R2 staging churn for those devices; **storage unaffected** (the homelab stores by SHA-256) | Easy to switch to A only before the first ingest | Silent dedup misses; confusing status; old bundles need out-of-band epoch knowledge |

- **Recommendation:** A.
- **Touches settled text:** no. ADR-0001 leaves rotation open.
- **If no decision by the deadline:** assume A. It is already in `identifiers.md` and the vectors.

## Hand-offs

| To | What | Why |
|---|---|---|
| A6 (ADR-0012/0013) | Catalog keeps `sha256` (and `inner` under kind 04) for every committed item; store addressed by SHA-256. Under posture A′, a kind-03 rotation needs the archive key online for a full decrypt-read | §5; identity layers |
| A2 (ADR-0007, `object-format.md`) | `dedup_id` is the `rd1` text form; `sha256` hex; the reserved `chunk_list` field stays | `identifiers.md` §6 |
| A3 (ADR-0009) | "Stale epoch" response, grace window, never "present" for a retired epoch; receipts are the only "safe" (old R6); homelab recompute check | `identifiers.md` §7 |
| C1 (ADR-0010) | Worker rejects malformed and bare-hex IDs; whether R2 keys contain IDs goes through **OD-04** | §3; Conflicts #3 |
| A4 (ADR-0011) | Bundles accept every epoch the homelab holds; verify the FAT32 per-directory limit and shard ID-named files | §3 |
| D2 (ADR-0008) | Cite `identifiers.md` §3 for the exact HKDF info (the bare label is forbidden, vector N03); change the trigger condition to "kind 01 or 04"; custody and delivery of `S_root` if kind 04; flush vs re-key (M-14) | §2, §5 |
| F3 | Review option N (C24) and the online-oracle exposure of kind 01; decide DR-F3-2 together with DR-A1-1; per-person `scope` design if option F | §2, §8 |
| B5 / B2 / B4 | R1 signals per platform; whether `ChangeTime` is reliable and settable; marker-file reference for R3; FAT local-time handling; G, Q and the R6 sampling rate | §6 |
| B6 (ADR-0021) | Cache encryption under an OS-keystore key and MACed entries (M-31, M-32); cache excluded from OS backups; prune deleted-file entries | §6 |
| E3 (ADR-0024) | "Hash failed (reason, retry-after)" and "unstable file" states; nudge for "key update needed" | §6, DR-A1-2 |
| G2 (ADR-0035) | Invariant tests: homelab rejects a recompute mismatch; Worker rejects malformed IDs; retired epochs never get "present"; every implementation runs `identifiers-vectors.json` | ADR-0006 Confirmation |
| H1 | Number DR-A1-1 and DR-A1-2; blocked sources (RFCs, NIST, eprint, eBACS); PLAN wording fixes (`sha2` "asm", racy-git path, A1-S1 phone rotation as required) | Registry owner |
| A1 (Wave 2) | A1-S1 kit addendum (other SHA-256 backends per ABI; required phone rotation run); retire the unchosen kinds in the vectors after DR-A1-1 | Follow-up |
