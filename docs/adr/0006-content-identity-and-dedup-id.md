# ADR-0006: Content identity is SHA-256; dedup IDs are kind- and epoch-tagged keyed MACs re-derivable from a cached digest

- **Status:** Proposed
- **Date:** 2026-10-06
- **Owner workstream:** A1
- **Decider:** the owner
- **Gate:** A
- **Supersedes / Amends:** **Amends ADR-0001 §2** (the row "Dedup ID = HMAC-SHA256(family dedup secret, content)") and **ADR-0001 §3** (the cache-key tuple), **only if** the owner chooses option B or N under DR-A1-1. If the owner chooses option A, nothing is amended except the §3 cache-key extension, which adds to §3 and does not contradict it.
- **Evidence:** [`docs/research/a1-content-identity.md`](../research/a1-content-identity.md); spikes A1-S1 (x86 reference, plus OL kit), A1-S2, A1-S3 and its follow-up `spikes/A1-S3/identifiers-v1/`
- **Normative artifact:** [`docs/spec/identifiers.md`](../spec/identifiers.md) (Draft), with [`identifiers-vectors.json`](../spec/identifiers-vectors.json)
- **Traceability:** R-21, R-23, R-24, R-44 (input), OPEN-3c and Q1-2b (ID side; custody belongs to ADR-0008)
- **Owner decisions:** DR-A1-1 and DR-A1-2 (new; H1 to assign OD numbers). Related: OD-04, OD-07, OD-08, OD-17, and DR-F3-2 (F3)
- **One-way door:** Yes, door #1 in `docs/research/one-way-doors.md` (dedup-ID construction and encoding)

## Context and problem statement

Every file a device protects gets two values: a plain content hash, used for integrity, and a keyed dedup ID, which is all the cloud sees. ADR-0001 fixes SHA-256 for the first and "HMAC-SHA256(family dedup secret, content)" for the second. It leaves open:
- the encoding;
- the versioning;
- rotation of the secret;
- the cache-key rules.

Once real family files are hashed, every cache entry, record, receipt, R2 key and catalog row carries these values. Changing them afterwards means re-hashing or re-deriving all of them (one-way door #1, Gate A).

Several things constrain the choice:
- **Settled requirements:** whole-file dedup across all users on plaintext (R-23); a local hash cache (R-24); the cloud never sees plaintext hashes (R-44); devices can only append; phones are first-class; low battery impact.
- **D1 and F3:** the main way the family secret leaks is any one of 10–25 consumer devices. Every holder of the secret can use the presence answer as an oracle (F3 C11; SR-21; AR-06). Rotation is the only remedy for a leaked secret.

## Decision drivers

- **BUD-HASH:** first pass of 128 GB on a low-end phone within a 6 h charge window, about 6 MB/s effective. **BUD-BAT-S:** seed battery cost, to be reported.
- **BUD-INGEST**, **BUD-AUDIT:** homelab verification and fixity work at 10 TB scale (R-09).
- **R-21/R-23/R-44:** keyed, whole-file, cross-user IDs; no plain hash in the cloud (SR-26).
- **SR-04:** the homelab recomputes SHA-256 and the dedup ID after decrypting. **SR-05:** only receipts mean "safe". **SR-15:** delivery of the dedup secret.
- **Rotation after a device compromise:** OPEN-3c, ADR-0008 Decision 7 / DR-D2-1, F3 M-04/M-14/M-25.
- **Thirty-year verifiability:** stock tools must be able to check the plain identity.
- The encoding must be safe as an R2 key, a FAT/exFAT/NTFS filename and a catalog key (A4, C1, A6).

## Considered options

Algorithm:
1. SHA-256 (as ADR-0001 says).
2. BLAKE3.

Construction (DR-A1-1):
- **A** (kind `03`): HMAC over the content, with HKDF epoch keys. This is the settled wording.
- **B** (kind `01`): HMAC over the content's SHA-256 digest.
- **N** (kind `04`): nested. HMAC over a long-lived keyed content MAC.
- **C:** keyed BLAKE3.

Format:
- Untagged IDs vs kind- and epoch-tagged IDs (DR-A1-2).
- Full 256 bits vs truncated.
- Hex vs base32 text.

Granularity: whole file vs block or tree hash vs content-defined chunking (CDC).

## Decision

**1. Algorithm: SHA-256.** It is unchanged from ADR-0001. It is native on every platform (Android `MessageDigest`/`Mac` API 1+, CryptoKit, Workers `DigestStream`), and `sha256sum` can check it.
- *Confirmation pending (Gate A):* A1-S1 must show SHA-256 meeting BUD-HASH on the low-end phone class.
- If the `sha2` crate misses BUD-HASH on a device, first measure other SHA-256 backends on that device and ABI, including 32-bit `armeabi-v7a`, where `sha2` 0.11 is always software: `ring`, `aws-lc-rs`, and platform `MessageDigest`. Only after that may BLAKE3 be proposed, as a superseding decision.

**2. Identifier structure (proposed as written; DR-A1-2 asks the owner to confirm the epoch tag):**
- Every dedup ID carries a **kind** byte and a **u16 epoch**, and keeps the **full 256-bit** MAC.
- Binary form: `kind ‖ u16be(epoch) ‖ mac` (35 bytes).
- Text form: `rd1-<kk>-<eeee>-<52 lowercase base32>` (64 characters).
- The plain content SHA-256 stays 64 lowercase hex. The two can never be confused, and the cloud rejects bare hex.
- Keys are per purpose, epoch and scope: `K(e, kind) = HKDF-SHA256(S_e, info = "reliquary/v1/dedup-id-key/kind=kk/epoch=eeee/scope=family")`.
- Exact bytes, strict parsing rules and 111 vectors are in `docs/spec/identifiers.md`.

**3. Construction: proposed kind `01` (option B, digest form), `HMAC-SHA256(K(e,01), 0x01 ‖ SHA-256(content))`, *subject to the owner's DR-A1-1*.**
- **Because:**
  - When the plain SHA-256 is also computed, B hashes each byte once in pass 1 where A and N hash it twice. That is verified on x86: 0.954 vs 1.685 CPU s/GB. The phone cost is unmeasured.
  - B re-derives every ID from cached and catalogued digests with zero file reads. A1-S2 measured 1M entries in 3.2–6.1 s on x86.
- **Options the owner may pick instead:**
  - **N (kind `04`)** if the owner prefers that a leaked key alone cannot test lists of SHA-256 values: with N, testing needs the file's bytes, as in the settled wording. N keeps rotation from the cache, at A's per-byte cost and with one extra never-rotated secret. A1-S1 will report N's real cost on phones.
  - **A (kind `03`)** if the owner rejects any deviation from the settled wording. It is supported, at a higher rotation cost: a full homelab re-read and decrypt, and devices re-hash only entries without a receipt.
- **Exactly one kind becomes active.** The other two are retired permanently.
- **Default until decided:** no production hashing under any kind. Prototypes (A0) may use any kind with test secrets.

**4. Granularity: whole file.**
- Per-part integrity in transit already comes from age STREAM's 64 KiB chunks.
- Kind `02` is reserved for a future chunk-list ID.
- No CDC in v1.

**5. Rotation mechanics (ID side):**
- The homelab keeps every `S_e` and re-derives from its catalog: `sha256` for kind 01, `inner` for kind 04. Kind 03 needs a full decrypt-read.
- The cloud's old-epoch ID history is flushed, not re-keyed. Residual linkage goes to AR-06 (F3 M-14).
- Devices re-derive from their caches.
- The rotation trigger, custody and delivery are ADR-0008's (D2).

**6. Hash-cache contract:** rules R1–R8 in `identifiers.md` §9. They extend ADR-0001 §3's cache-key tuple with:
- change time or a version token;
- a racy window against a filesystem-written reference time;
- a FAT local-time rule;
- TOCTOU stat checks;
- sampled re-verification;
- cache provenance.

Receipt semantics, status vocabulary and cache protection are requirements handed to A3, E3 and B6.

**7. Dedup scope:** `scope=family` in v1 key derivation. Per-person keys (DR-F3-2 option F) are **to be decided in Wave 2** with F3. Under kinds 01 and 04 the change is a cache-only re-derivation. Under kind 03 it is a re-read.

### Consequences

- **Good:**
  - The format is self-describing, through kind and epoch. A rotation is explicit, and a stale device gets a clear error instead of silent dedup misses.
  - Old USB bundles stay verifiable.
  - Under kinds 01 and 04, rotation and a later change of key scope or label cost seconds per device and no file reads.
  - Under kind 01, pass-1 hashing CPU on devices and verification hashing at the homelab are about halved. From T1's x86 figures, the end-to-end client pipeline goes from about 387 to about 509 MB/s (arithmetic, not measured).
  - The base32 text form keeps dedup IDs and plain hashes apart by construction.
- **Bad / accepted trade-offs:**
  - Under kind 01, a holder of a leaked `S_e` can test **lists of SHA-256 values** without the files. That includes a stolen device's own hash cache (F3 M-32) and, while the device is enrolled, any public hash list through the presence answer.
  - Kind 01 also inherits any published SHA-256 collision pair. No full SHA-256 collision is known: the best practical result reported is 31 of 64 steps, ASIACRYPT 2024, a secondary source. Against an insider device that holds the key, HMAC over content gives about the same collision resistance, so the difference only matters for precomputed public pairs.
  - These two are reasoning, not sourced (claims K4 and K5 are secondary-only). The owner accepts them knowingly, or picks N.
  - The ID deviates from the settled wording unless option A is chosen.
  - The homelab catalog must keep `sha256` (and `inner` for kind 04) for every item.
- **Follow-up work:**
  - Before running, the A1-S1 kit needs an addendum: benchmark other SHA-256 backends, make the phone rotation run required, and benchmark C1 (A/N) against C2 (B) on phones.
  - A3 defines the stale-epoch response and its grace window.
  - A4 defines bundle directory sharding.
  - D2 aligns ADR-0008 Decision 7 with the exact HKDF info bytes, and with the conditional "kind 01 or 04" in place of "construction B".
  - C1/OD-04 decides whether R2 keys contain IDs.

### Confirmation

- **Vectors:** every implementation (Rust core, homelab importer, Kotlin, Swift) passes `identifiers-vectors.json` and Wycheproof HMAC/HKDF. The vectors were cross-checked on 2026-10-06 in Rust, Python and Node (A1-S3 follow-up).
- **A1-S1 (OL kit):** SHA-256 meets BUD-HASH without thermal throttling on the low-end class. Record BUD-BAT-S for C1 (A/N) and C2 (B).
- **A1-S2 on a phone:** a 1M-entry rotation in < 60 s with zero file reads.
- **G2 invariant tests:**
  - the homelab rejects records whose recomputed `sha256` or `dedup_id` differs (SR-04);
  - the Worker rejects bare-hex and malformed IDs;
  - retired epochs never get "present".

## Pros and cons of the options

### SHA-256 (chosen)
- Good, because ADR-0001 already names it (K1, verified). It is native on Android, Apple platforms and Workers (K8, verified), and stock tools check it.
- Good, because with ARMv8 SHA-2 instructions, compute is likely far above BUD-HASH. That rests on one secondary 2017 figure (559 MB/s), so it is indicative only.
- Bad, because on AArch64 cores without `HWCAP_SHA2`, and in every 32-bit ARM build, `sha2` 0.11 uses software code of unmeasured speed (K6, verified; the 32-bit case was added by the skeptics).

### BLAKE3
- Good, because on x86 it used about 4× less CPU per GB than SHA-NI SHA-256 (A1-S1: 0.224 vs 0.914 CPU s/GB).
- Bad, because it is in no platform API (K8). It would supersede ADR-0001's algorithm. The paper's only ARM result is a 32-bit ARM1176 without SHA-2 instructions (K7, verified), so nothing primary compares it on ARMv8 phones.

### A: HMAC over content (kind 03)
- Good, because it is the settled wording, a leaked key still needs the file bytes to test, and it does not inherit public SHA-256 collisions.
- Bad, because it costs 2 hash computations per byte in pass 1 and at the homelab (K2, verified).
- Bad, because rotation needs a full homelab re-read and decrypt: about 5.5 h at the 508 MB/s compute measured on x86, about 28 h at the 100 MB/s BUD-INGEST floor; disks are unmeasured. If OD-07 is A′, it also needs the offline archive key online. Devices re-hash pending entries. K3 was **contested**: rotation under A is costlier, not infeasible. No full device re-read is needed, and under DR-F3-2 options D/E the homelab re-derivation can be lazy.

### B: HMAC over SHA-256 (kind 01, proposed)
- Good, because it costs one hash per byte (K2) and rotates from the cache (A1-S2).
- Bad, because of the testing from a digest alone and the collision inheritance described above (K4, K5, secondary-only).

### N: nested (kind 04)
- Good, because it rotates from the cache like B, while testing after a leak still needs the bytes, as with A (reasoning, raised by two skeptics; not itself skeptic-reviewed).
- Bad, because it costs 2 hashes per byte like A, and it adds `S_root`, which can never be rotated cheaply. A leak of `S_root` alone is harmless without a current `S_e`.

### C: keyed BLAKE3
- Bad, for the BLAKE3 reasons above. Reconsider only with phone evidence (A1-S1).

### Format
- **Epoch tag:** costs 2 bytes. Without it, a stale device's IDs silently miss dedup and cause re-uploads. Storage is unaffected, because the homelab stores by SHA-256 (correcting the earlier "storage doubles").
- **256 bits:** avoids 2⁶⁴-work collisions by a key-holding device. The 16 bytes per row (about 160 MB per 10⁷ rows) is small. K13 is secondary-only, so the choice rests on it being the primitive's natural output, not on the cost figure.
- **base32 vs hex:** both are safe single-case encodings (K9, verified). base32 is chosen so that dedup IDs and plain SHA-256 values (hex) are distinguishable.

## Evidence

| Claim | Source (primary) | Verdict |
|---|---|---|
| K1 ADR-0001 fixes SHA-256 and HMAC-SHA256 | ADR-0001 §2 | Verified |
| K2 2 vs 1 hash computations per byte; x86 668 vs 1,136 MB/s (portable 140 vs 299) | CE §14; A1-S1 | Verified |
| K6 AArch64 SHA-2 is optional (`HWCAP_SHA2`); `sha2` 0.11 detects it at run time, has no `asm` feature, and uses software elsewhere | Linux `elf_hwcaps.rst`; `sha2-0.11.0.crate` | Verified |
| K7 The BLAKE3 paper's ARM result is on a 32-bit ARM1176 | `blake3.pdf` | Verified |
| K8 SHA-256 and HMAC-SHA256 are native on Android, CryptoKit and Workers; BLAKE3 is not | developer.android.com; Apple DocC; Cloudflare docs | Verified |
| K9 A single-case fixed-length ID is filesystem- and R2-safe | MS naming, exFAT spec, R2 limits | Verified |
| K10 git's racy-clean rule; FAT 2 s write time | `racy-git.adoc`; MS File Times | Verified |
| K11 restic change-detection signals and failure cases | restic `040_backup.rst`; issues #2179, #2495 | Verified |
| K12 Tahoe: a new secret means a new dedup domain | Tahoe `convergence-secret.rst` | Verified (its "storage doubles" does **not** carry over to Reliquary) |
| A1-S2 rotation from the cache with zero file reads (x86) | `spikes/A1-S2` | Measured (x86 reference) |
| A1-S3 follow-up: Rust, Python and Node agree on 111 vectors; Wycheproof passes | `spikes/A1-S3/identifiers-v1` | Measured |
| K3 rotation cost of option A | arithmetic | **Contested**. Restated; not used as sole support |
| K4 opacity before a leak; testing from a digest after a leak | reasoning | Secondary-only. Stated as an accepted trade-off |
| K5 collision inheritance | reasoning | Secondary-only. Stated as an accepted trade-off |
| K13 cost of keeping 256 bits | arithmetic | Secondary-only. Not load-bearing |

## Reversibility

This is a one-way door once production secrets hash real family files.
- **Before Gate A:** free.
- **After:**
  - Under kinds 01 and 04, a change of label, scope or epoch is a cache-only re-derivation.
  - Under kind 03, it is a full re-read.
  - Changing the algorithm or the kind means re-reading every file on every device and at the homelab, so it must be right at Gate A.

What must be true before the gate:
- DR-A1-1 is answered;
- A1-S1 phone results are in;
- D2 has fixed the custody and delivery of `S_e` (and of `S_root` if kind 04);
- the vectors have been regenerated for any change.

## Alternatives considered

- **Tree or block hash (Dropbox `content_hash`, BLAKE3/Bao):** stock tools cannot reproduce it, and age STREAM already gives per-part integrity.
- **FastCDC per-chunk IDs:** rejected because of the 2025 chunking attacks (F3) and the added complexity. Kind 02 is reserved.
- **Truncated 128-bit IDs (Kopia's default):** they cut collision resistance against a key holder to 2⁶⁴ work.
- **Untagged IDs (git's SHA-1 experience):** these lead to repository-wide flags and translation tables.
- **Server-aided keys (DupLESS-style or a homelab OPRF):** these conflict with an outbound-only homelab and with the settled construction. D1 and F3 keep them open but do not recommend them.

## Open questions

- Which low-end SoCs lack `HWCAP_SHA2`; whether 32-bit-only phones are in the fleet; and the speed of SHA-256 backends there (A1-S1, H5).
- The phone energy difference between C1 and C2, which decides B vs N on cost (A1-S1).
- The rotation trigger and owner time (D2, BUD-SUPPORT); the grace window and offline devices (A3, D3, E3).
- Per-person scope (F3, DR-F3-2 option F), Wave 2.
- Whether Windows `ChangeTime` is reliable and whether user mode can set it (B5).
- The rate for sampled re-verification (B5).
- FAT32 per-directory limits for bundles (A4).
- RFC 2104/4231/5869, FIPS 180-4, SP 800-107 and eprint are blocked (H1). Wycheproof is used for the primitives.
