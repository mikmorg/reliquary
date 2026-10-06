# A2. Object envelope and metadata-record format

- **Workstream:** A2 (see `docs/research/PLAN.md`, section "A2.")
- **Status:** Draft (analyst deep read, Wave 1 batch W1-a; continuation pass 2026-10-06 re-checked versions, re-ran M1 and added C22–C23). Skeptic review has not started, so every claim below is **pending**. A separate spike runner is running A2-S1 to A2-S4 in parallel; see [Spikes](#spikes).
- **Date:** 2026-09-29 (last updated 2026-10-06)
- **Wave 1 scope:** the P0 **object envelope** for the ADR-0007 draft, covering the construction, the post-quantum option (OD-06), recipients, sender authentication, resumability, truncation, padding and agility. The **metadata-record schema is provisional** (P1; it follows A5 and the H4 data model).
- **Feeds:** ADR-0007 and `docs/spec/object-format.md` (both reserved for A2), OD-06 (PQ), evidence for OD-07 (A6 posture) and OD-08 (recovery recipient), one-way door #2 (object envelope, PQ, sender authentication), and new decision requests DR-A2-1 to DR-A2-4 (below; H1 assigns OD numbers).
- **Depends on:**
  - **T1 spike 2**, the CE note: `docs/research/content-encryption-format.md` and `spikes/content-encryption/`. **It exists and this note builds on it.** Its D-1, D-2, D-3 and D-7, and its open issues 6 and 8, are the starting points here.
  - D2 (`d2-key-hierarchy-custody-recovery.md`), F3 (`f3-security-literature.md`), D1 (`d1-threat-model.md`: SR-02, SR-03, SR-05, SR-13, SR-22, SR-24), A1 (`a1-content-identity.md`), A3 (`a3-ingest-protocol.md` F4, F8), A6 (`a6-homelab-storage-engine.md` F3, posture A′), B4 (`b4-ios-decision.md` K2–K5), H4 (`docs/design/data-model.md` §6).
- **Traceability rows advanced:** R-19 (content and metadata encrypted on the device), R-20 (devices cannot read), R-25 (source locator, name and mtime only at the homelab), Q1-4 (resumable uploads vs age randomness).

## Summary

**Keep the CE design: every content object is a standard age v1 file written by our own encoder.** Recommended changes:

1. **Post-quantum from day one.** Use the native age hybrid recipient `mlkem768x25519` (X-Wing) for *every* stanza. The age spec says a PQ file SHOULD NOT also carry classic stanzas, and Go age 1.3.2 refuses to write such a file. I reproduced that refusal in the container.
2. **Measured header sizes.** Go age 1.3.2 in the container gave:

   | Header | Size |
   |---|---|
   | One PQ stanza | 1,627 B |
   | Two PQ stanzas | 3,184 B |
   | One X25519 stanza | 168 B |

   Two PQ stanzas therefore **fail** A2-S1's "header ≤ 3 KB per object" as written, and one PQ stanza passes. That is why this note asks where the recovery stanza goes (DR-A2-2). The homelab cannot check a recovery stanza that a device wrote, because it cannot open it. The analyst therefore recommends:
   - devices write only the ingest stanza;
   - the homelab writes the archive and recovery stanzas when it rewraps at ingest (A6 posture A′).

   This conflicts with the D2 draft, and the owner decides.
3. **Sender authentication.** age provides none. HPKE Auth mode does not exist for the PQ KEMs: the HPKE-PQ draft says so, and the Rust `hpke` crate rejects it. So sender authentication stays a **device Ed25519 signature on the metadata record, inside the encryption**. Changes to the CE version of the record:
   - the record binds more fields (sequence, record ID, object length);
   - it is carried in a C2SP **signed-note**, so signature algorithms can be swapped later;
   - receipts bind the digest of the *signed plaintext record*, which stays stable across batching and rewrap.
4. **No stock Rust age crate can write or read PQ objects** (age 0.12.1). The client encoder must emit the X-Wing stanza itself, for example with the `hpke` 0.14.1 crate. Byte-level interop with Go age is **unverified** until A2-S3 runs.
5. **New in the continuation pass: X-Wing is not yet behaviourally frozen.** The CCTV vector `hybrid_low_order` requires a *header failure* when the X25519 part of `enc` is a low-order point (all-zero shared secret). The `hpke` 0.14.1 X-Wing decapsulation uses the RustCrypto `x-wing` key type that *accepts* that case, and `x-wing` 0.1.1 (2026-10-01) says CFRG has yet to pick one behaviour for the RFC (C22). The encrypt direction is unaffected. Any Rust *decrypt* path (A8 device restores, Rust homelab tools) must add the rejection itself, and A2-S3 must run `hybrid_low_order` against it.

**Confidence:**

| Area | Confidence |
|---|---|
| Spec and source facts | High |
| PQ recommendation | Medium-high |
| Recipient placement | Medium, because it couples to OD-07 and OD-08 |
| Record encoding | Low-medium (provisional) |

## Questions

| # | Question (PLAN A2) | Short answer | Confidence |
|---|---|---|---|
| 1 | Which construction? | **age v1 (C2SP)**, as CE D-1. It is the only candidate with a public spec, a conformance kit (CCTV), independent implementations in Go, Rust and TypeScript, a stock CLI and a written backwards-compatibility promise (C1, C3, C14). Custom HPKE + STREAM, Tink, libsodium secretstream and saltpack each lose the stock CLI, and most also lack PQ (§Alternatives). | High |
| 2 | Post-quantum from day one? Header size and phone cost? | **Yes, mlkem768x25519 for all stanzas** (DR-A2-1). Measured header sizes: one PQ stanza 1,627 B, two 3,184 B (C6). The PQ cost is a fixed number of KEM operations per object; the payload crypto is unchanged. Phone CPU and battery are not measured (A2-S1, OL kit). | Medium-high (recommendation); High (sizes); no result (phone cost) |
| 3 | Recipient set: online ingest key plus offline recovery key; rotation should only rewrap | The format carries 1–N stanzas, all PQ. Rotation is a header rewrap, because the payload key depends only on the file key and the nonce (C2; A6 C2). **Placement is a decision** (DR-A2-2). A device-written recovery stanza cannot be verified at ingest (C9). The recommendation is device = ingest stanza only, and homelab = {archive, recovery} at the A′ rewrap. | High (mechanics); Medium (placement) |
| 4 | Sender authentication | **Device Ed25519 signature over the record, inside the encryption.** HPKE Auth mode is unavailable for PQ KEMs (C10, C11). HPKE PSK mode breaks stock age decryption. saltpack-style DH authentication does not carry over to a KEM (C19). The record binds object, device, sequence and time (§F4). | High (options ruled out); Medium-high (design) |
| 5 | Resumability (segments aligned to multipart parts; deterministic regeneration vs temp file) | **CE mechanism unchanged.** Only prefix_len grows: 1,643 B with one PQ stanza, 3,200 B with two. CE's layout math is unit-tested for prefixes of 1–65,551 B. The header is built once and persisted in the sealed state, so the X-Wing encapsulation randomness never has to be re-derived; hedge it like the X25519 esk. B4 K2–K4 (guard at handoff, bounded spool, sequential sources) are placement rules and need no format change. | High (layout); Medium (hedging for X-Wing, not prototyped) |
| 6 | Truncation and reordering; random access for restores | age STREAM: a counter nonce plus a final flag. Streaming decryption MUST fail without a valid final chunk, and seeking from the end MUST verify the final chunk first (C3). CE §5.5 adds "authenticate the final chunk before serving any middle chunk" because the Rust `StreamReader::seek` does not. Keep that rule. The multi-stanza header parser (CE open issue 6) is now mandatory. | High |
| 7 | Length hiding: Padmé vs buckets vs none; zstd | **Padmé with zero padding before encryption**, if F3-S1 confirms most sizes are unique (DR-A2-4). Cost is ≤ 3.1 % for 64 KiB–4 GiB (F3 C8, arithmetic). IDs and SHA-256 stay over the unpadded bytes. The true size goes only in the signed record, and every cloud-visible size field must carry the padded length (F3 C10). **No compression in v1:** a `content_encoding` field is reserved (§F7). | Medium |
| 8 | Metadata-record fields and encoding; schema evolution | **Provisional:** a signed-note (C2SP) whose text is one line of compact I-JSON, signed with the device's Ed25519 key. The fields are from H4 §6.1 plus the A1, A3 and B4 additions (§F6). Deterministic CBOR (CDE) is the main alternative. The choice follows A5 and the D2/E7 recovery kit. | Low-medium |
| 9 | Algorithm agility and migration | Agility lives at the **stanza** level: new recipient types, rewrap only. The payload suite (ChaCha20-Poly1305, 64 KiB STREAM) is fixed by age v1. Replacing it means decrypting and re-encrypting at the homelab: about 28 h per 10 TB at BUD-INGEST's 100 MB/s (arithmetic). Signature agility comes from signed-note key names and type bytes. The record's `object.profile` names the Reliquary profile. | Medium |
| 10 | (new) Can the homelab verify a recovery stanza written by a device? | **No.** An HPKE SealBase stanza can be checked only with the recipient's private key or the sender's encapsulation randomness, and R is offline. A buggy or malicious device could write a garbage R stanza that ingest cannot detect (C9). | High (logic) |
| 11 | (new) Does the Rust ecosystem have a drop-in PQ age implementation? | **No.** The `age` crate 0.12.1 has native `x25519`, `scrypt`, `tag` and `tagpq` only (confirmed by listing `src/native/`). Its `hpke` and `ml-kem` dependencies serve the encryption-only `tagpq` recipient (C7). This resolves a conflict between scouts. Re-checked 2026-10-06: 0.12.1 is still the latest `age` crate. | High |
| 12 | (new) Is the X-Wing KEM behaviour stable across implementations? | **Not fully.** Go age (via CCTV `hybrid_low_order`) rejects a low-order X25519 share; Rust `hpke` 0.14.1 on `x-wing`'s default key accepts it; `x-wing` 0.1.1 adds a rejecting key type and says the default will change once CFRG publishes the RFC (C22). Honest encryptions are unaffected; only malformed-stanza handling differs. Treat as a decrypt-side conformance item, not a format change. | High (facts); Medium (impact) |

## Method

- **Sweep:** three scouts (docs, source, community), then this analyst deep read.
- **Read in full or in the relevant sections by the analyst:**
  - the C2SP age spec (whole: header, payload, all five native recipient types, the scrypt exclusivity rule, test vectors);
  - the HPKE-PQ draft (hybrid KEM mapping, IANA table, the "Asymmetric-Key-Authenticated Modes" section);
  - X-Wing draft §"Not an authenticated KEM";
  - HPKE (RFC 9180 source) KCI section headings;
  - C2SP signed-note (format and signature types);
  - the CCTV age README;
  - Go age v1.3.2 `age.go`/`pq.go` (mixing enforcement);
  - Rust `age` 0.12.1 `src/native/` and `Cargo.toml`;
  - Rust `hpke` 0.14.1 `src/kem/xwing.rs` and `Cargo.toml`;
  - the age(1) man page (backwards compatibility);
  - the Go age README (PQ keys).
- **Reproduction in the container:** Go age v1.3.2 binaries built earlier in this run, under `scratchpad/tools/bin`.
  - Headers were measured with `age-inspect` and file sizes, for one PQ recipient, two PQ recipients and one X25519 recipient.
  - A mixed PQ + X25519 encryption was attempted: rejected, exit 1.
  - The PQ recipient string is 1,959 characters.
  - Synthetic random bytes only; nothing else was measured.
- **Scout conflicts resolved:**
  1. *"Rust age 0.12 depends on hpke and ml-kem, so it probably has native PQ"* (community scout) vs *"no mlkem768x25519 in 0.12.1"* (docs and source scouts). Resolved by listing the crate's `src/native/` modules. The dependencies serve `tagpq`, and there is no native X-Wing recipient (C7).
  2. *The two-stanza header is "at or just over 3 KB" (derived)*. Now measured at 3,184 B. That exceeds 3 KB whether KB means 1,000 or 1,024 B (C6).
  3. *D2 "devices include R themselves" vs A6 "recovery recipient added at ingest, not on devices"*. Not resolved here. The trade-offs are set out as DR-A2-2, including the new verifiability finding (C9).
- **Routes:** raw.githubusercontent.com (C2SP, CCTV, hpkewg, dconnolly, cfrg, FiloSottile, keybase, jedisct1, rclone, borgbackup, bupstash, ente, tink-crypto, cbor-wg, openpgp-pqc), proxy.golang.org, static.crates.io, index.crates.io, registry.npmjs.org, developer.apple.com doc JSON. GitHub issue metadata came via the community scout.
- **Blocked sources** (report to H1; no secondary source was substituted for a primary one):
  - c2sp.org and age-encryption.org: the raw C2SP mirror was used, with no commit hash, because the GitHub API is restricted to mikmorg/reliquary.
  - datatracker.ietf.org and rfc-editor.org: RFC 9180 was read from CFRG source markdown. RFC 8949, RFC 8032 and RFC 9580 were not read. The status of draft-ietf-hpke-pq and draft-ietf-openpgp-pqc is unverified.
  - eprint.iacr.org and arxiv.org: the STREAM paper (2015/189), MEGA and Nextcloud papers, and PURBs/Padmé were not read.
  - csrc.nist.gov (FIPS 203/204).
  - words.filippo.io, soatok.blog, HN.
  - developers.google.com/tink (Tink source used instead).
  - WebSearch: the session budget was exhausted.
  - A COSE struct draft path on raw GitHub returned 404, so COSE was **not** evaluated from a primary source.
  - mailarchive.ietf.org (403 from shell, 2026-10-06): the CFRG message that `x-wing` 0.1.1 cites for "CFRG have decided" on non-contributory X25519 was not read; C22 relies on the crate's own statement of it.
- **Continuation pass (2026-10-06, after the session limit interrupted Wave 1):**
  - re-checked latest versions: `age` crate 0.12.1, Go age v1.3.2, typage 0.3.1, CCTV age 2026-09-25 (all unchanged); `hpke` 0.14.1 unchanged; **`x-wing` 0.1.1 published 2026-10-01** (new);
  - diffed `x-wing` 0.1.0 vs 0.1.1 source and read `hpke` 0.14.1 `src/kem/xwing.rs` in full (C22, C23);
  - read the CCTV `hybrid_low_order` vector and its generator (`internal/tests/hybrid_low_order.go`);
  - re-ran M1 with Go age v1.3.2 (M2): identical numbers.
  - The partial spike-runner tree at `scratchpad/A2/ce-pq` (a copy of the CE spike with `hpke = "=0.14.1"` added) was **not** used as evidence; its `evidence/` files are the CE run's.
- **Stop rule:** by the end of the analyst pass, no new primary source changed a finding. The last three reads (signed-note, `hpke` crate source, CCTV README) refined the design without contradicting it.

## Sources

| # | Source | Publisher | Version or date | Accessed | Primary? |
|---|---|---|---|---|---|
| S1 | age spec, editor's copy: `C2SP/C2SP @ main : age.md` (= c2sp.org/age) | C2SP | main head (commit not retrievable) | 2026-09-29 | Yes |
| S2 | Go `filippo.io/age` v1.3.2 module (proxy.golang.org): `age.go` (incompatibleLabelsError), `pq.go`, `extra/age-plugin-pq`, `cmd/age-inspect`, `go.mod` (go 1.25.0) | F. Valsorda | v1.3.2, 2026-08-29; PQ since v1.3.0, 2025-12-27 | 2026-09-29 | Yes |
| S3 | `FiloSottile/age @ main : README.md` (PQ keys, "~2000 characters", age-plugin-pq, age-inspect) and `doc/age.1.ronn` (BACKWARDS COMPATIBILITY) | F. Valsorda | main | 2026-09-29 | Yes |
| S4 | CCTV age vectors: `C2SP/CCTV @ main : age/README.md`; module `c2sp.org/CCTV/age` pseudo-versions 2026-08-29 (4448f2097b2d, pinned by age v1.3.2) and 2026-09-25 (50a8ecf2a220) | C2SP | as stated | 2026-09-29 | Yes |
| S5 | Rust `age` 0.12.1 crate (static.crates.io): `src/native/{x25519,scrypt,tag,tagpq}.rs`, `Cargo.toml` (hpke ^0.12, ml-kem ^0.2), CHANGELOG | str4d | 0.12.1, 2026-07-14 | 2026-09-29 | Yes |
| S6 | Rust `hpke` 0.14.1 crate: `src/kem/xwing.rs` (KEM_ID 0x647a, draft-ietf-hpke-pq-03, auth-mode errors), `Cargo.toml` (depends on `x-wing` 0.1.0 "hazmat", `ml-kem` 0.3; default features include x25519, mlkem, chacha; rust-version 1.85) | RustCrypto | 0.14.1 | 2026-09-29 | Yes |
| S7 | Rust `x-wing` 0.1.0 crate `Cargo.toml` ("X-Wing KEM (draft 06)"); `hpke-rs` 0.7.0 `src/kem.rs` (XWingDraft06, auth unsupported) | RustCrypto; Cryspen | 0.1.0; 0.7.0 | 2026-09-29 | Yes |
| S26 | Rust `x-wing` 0.1.1 crate (static.crates.io): `CHANGELOG.md` (0.1.1, 2026-10-01: "Fallible `DecapsulationKeyRejectNonContrib`"), `src/lib.rs` (backstory doc comment on non-contributory X25519; cites a CFRG mail-archive message) | RustCrypto | 0.1.1, 2026-10-01 (crates.io pubtime) | 2026-10-06 | Yes |
| S27 | CCTV age `testdata/hybrid_low_order` ("expect: header failure"; "the X25519 part of enc is a low-order point, so the shared secret is the disallowed all-zero value") and `internal/tests/hybrid_low_order.go` (order-8 point) | C2SP | module 2026-09-25 (50a8ecf2a220) | 2026-10-06 | Yes |
| S8 | draft-ietf-hpke-pq editor's copy: `hpkewg/hpke-pq @ main : draft-ietf-hpke-pq.md` (hybrid KEM mapping; IANA 0x647a Nenc 1120, Npk 1216, Auth "no"; §"Asymmetric-Key-Authenticated Modes of RFC9180") | IETF HPKE WG | editor's copy (-latest); age cites -03 | 2026-09-29 | Yes |
| S9 | X-Wing draft editor's copy: `dconnolly/draft-connolly-cfrg-xwing-kem @ main` (§"Not an authenticated KEM") | Connolly et al. | editor's copy | 2026-09-29 | Yes |
| S10 | HPKE source markdown: `cfrg/draft-irtf-cfrg-hpke @ master` (KCI; Auth-mode caveats; non-goals). May differ editorially from RFC 9180 | IRTF CFRG | master | 2026-09-29 | Yes (mirror) |
| S11 | C2SP signed-note: `C2SP/C2SP @ main : signed-note.md` | C2SP | main head | 2026-09-29 | Yes |
| S12 | typage (npm `age-encryption`) 0.3.1 README and package (hybrid identities and recipients) | F. Valsorda | 0.3.1, 2026-08-28 | 2026-09-29 | Yes |
| S13 | Apple CryptoKit doc JSON: HPKE.Ciphersuite, XWingMLKEM768X25519 (iOS 26+), HPKE (iOS 17+) | Apple | current | 2026-09-29 | Yes |
| S14 | Tink Java `HpkeParameters.java` (X_WING 0x647a with HKDF_SHA256 only) and `StreamingAead.java` Javadoc; tink-go v2.8.0 streaming AEAD source | Google | main; v2.8.0 | 2026-09-29 | Yes |
| S15 | libsodium `secretstream` documentation | F. Denis | master | 2026-09-29 | Yes |
| S16 | saltpack README and `specs/saltpack_encryption_v2.md` | Keybase | master | 2026-09-29 | Yes |
| S17 | Ente web crypto `types.ts` and `libsodium.ts` (per-file secretstream, 4 MiB chunks, "Existing encrypted files depend on this chunk boundary") | Ente | main | 2026-09-29 | Yes |
| S18 | rclone crypt docs (file format) | rclone | master | 2026-09-29 | Yes |
| S19 | bupstash technical overview and `bupstash-new-sub-key(1)` | A. Chambers | master | 2026-09-29 | Yes |
| S20 | Borg `docs/internals/security.rst` (borg 2 session keys, AAD binding) | BorgBackup | master | 2026-09-29 | Yes |
| S21 | draft-ietf-openpgp-pqc editor's copy | IETF OpenPGP WG | editor's copy (status unverified) | 2026-09-29 | Yes |
| S22 | draft-ietf-cbor-cde editor's copy | IETF CBOR WG | editor's copy | 2026-09-29 | Yes |
| S23 | GitHub issues: age #59 (no sender authentication), age #55 (PQ request), rage #598 (third-party X-Wing draft), restic #187 (asymmetric backups), borg #1039 (nonce reuse on rollback), duplicacy #638 (KDF diverges from docs), rclone #1712 (no plaintext checksum) | GitHub | as listed by the community scout | 2026-09-29 | No (community) |
| S24 | Reliquary CE note `content-encryption-format.md` and `spikes/content-encryption/` | this repo (T1) | 2026-09-29 | 2026-09-29 | Yes (project evidence) |
| S25 | Reliquary drafts: D2, F3, D1, A1, A3, A6, B4 notes and `docs/design/data-model.md` | this repo | 2026-09-29 | 2026-09-29 | Project evidence (drafts, not yet skeptic-reviewed) |
| M1 | Analyst reproduction with Go age v1.3.2 in the container (header sizes, mixing refusal, recipient length) | this note | 2026-09-29 | 2026-09-29 | Measurement (synthetic data) |
| M2 | Re-run of M1 (fresh keys, 1,000 random bytes): one PQ stanza header 1,627 B (file 2,659 B), two PQ 3,184 B (4,216 B), one X25519 168 B (1,200 B); recipient 1,959 chars; mixed PQ + X25519 refused (exit 1, "incompatible recipients: can't mix post-quantum and classic recipients"); two-stanza file decrypts with the second identity | this note | 2026-10-06 | 2026-10-06 | Measurement (synthetic data) |

## Claims

All verdicts are pending skeptic review.

| # | Claim | Sources | Key? | Skeptic 1 (sources) | Skeptic 2 (logic) | Skeptic 3 (adversary/cost/user) | Verdict |
|---|---|---|---|---|---|---|---|
| C1 | age v1 wraps one 128-bit CSPRNG file key in 1–N independent stanzas. The header MAC is HMAC-SHA-256 under HKDF(file key, "header") over all stanzas. The payload key is HKDF(file key, nonce, "payload"). The payload is 64 KiB ChaCha20-Poly1305 chunks with an 11-byte counter plus a final flag. Identities MUST ignore unrecognised stanzas. | S1 | Yes | | | | pending |
| C2 | Changing the recipient set is a header rewrite (new stanzas and a new MAC, which needs the file key). The payload bytes stay valid. | S1 (+ A6 C2) | Yes | | | | pending |
| C3 | Streaming decryption MUST error at EOF without a valid final chunk. Seeking relative to the end MUST first verify the final chunk. The payload MUST NOT be modified without re-encrypting with a fresh nonce. | S1 | Yes | | | | pending |
| C4 | The `mlkem768x25519` stanza is HPKE SealBase with KEM MLKEM768-X25519 (draft-ietf-hpke-pq-03 / filippo.io/hpke-pq), HKDF-SHA256, ChaCha20Poly1305, info `age-encryption.org/mlkem768x25519`, empty aad. It has two arguments (the type and base64 of a 1,120-byte enc) and a 32-byte body. Identities MUST reject a non-canonical enc or wrong lengths. | S1, S8 | Yes | | | | pending |
| C5 | The same file SHOULD NOT be encrypted to `mlkem768x25519` (or `mlkem768p256tag`) and to non-PQ recipients. Go age 1.3.2 enforces this through a `postquantum` label and fails with "can't mix post-quantum and classic recipients" (reproduced, M1). An scrypt stanza MUST be alone. | S1, S2, M1 | Yes | | | | pending |
| C6 | Measured with Go age 1.3.2 (M1, reproduced in M2): header 1,627 B with one PQ stanza, 3,184 B with two PQ stanzas, 168 B with one X25519 stanza. A PQ recipient string is 1,959 characters. These match D2's independent measurement and the README's age-inspect example. | M1, M2, S3, D2 C4 | Yes (cost; A2-S1 rule) | | | | pending |
| C7 | The Rust `age` crate 0.12.1 (latest, 2026-07-14) has native `x25519`, `scrypt`, `tag` and `tagpq` modules, and no `mlkem768x25519` recipient or identity. Its hpke and ml-kem dependencies serve the encryption-only `tagpq`. | S5 | Yes | | | | pending |
| C8 | The Rust `hpke` 0.14.1 crate implements the MLKEM768-X25519 KEM (0x647a), citing filippo.io/hpke-pq and draft-ietf-hpke-pq-03, on top of RustCrypto `x-wing` 0.1.0 ("draft 06"). It is a candidate for the client's own stanza encoder. **Byte-level interop with Go age is not verified.** CCTV vectors can test only the decrypt direction (C14), so interop needs Go age to decrypt Rust output (A2-S3). | S6, S7, S4 | Yes | | | | pending |
| C9 | The homelab cannot verify that a device-written stanza for an offline recipient R wraps the right file key. Checking a SealBase output needs skR or the sender's encapsulation randomness. A faulty device could therefore store unrecoverable R stanzas undetected, unless the homelab writes R itself (A′ rewrap) or the device discloses its encapsulation randomness to the homelab. | S1, S8 (logic) | Yes | | | | pending |
| C10 | The HPKE-PQ KEMs, MLKEM768-X25519 among them, "do not support AuthEncap/AuthDecap". The draft names PSK mode or digital signatures as alternatives. X-Wing is "not … an authenticated KEM". | S8, S9 | Yes | | | | pending |
| C11 | Rust `hpke` 0.14.1 errors on authenticated encapsulation with X-Wing ("Use Base or Psk operation mode"). `hpke-rs` 0.7.0 returns UnsupportedKemOperation for X-Wing and ML-KEM auth operations. Even with DHKEM, RFC 9180 Auth mode is exposed to key-compromise impersonation. | S6, S7, S10 | No (supporting) | | | | pending |
| C12 | age gives no sender authentication for public-key recipients. Anyone holding the recipient can produce a valid file; the only "expectation of authentication" the spec names is scrypt's. | S1; S23 (age #59) | Yes | | | | pending |
| C13 | Go age ≥ 1.3.0 decrypts PQ objects natively; older or other implementations can use `age-plugin-pq`. The age(1) man page promises that files from a stable version decrypt with any later version, possibly behind a flag if that is a security risk. | S2, S3 | Yes (30-year readability) | | | | pending |
| C14 | CCTV age has 147 vector files, including 18 `hybrid_*` plus `armor_hybrid`. It is distributed as the Go module `c2sp.org/CCTV/age` and the npm package `cctv-age`. It "can't be used to test the encryption direction end-to-end", but can test header and STREAM round trips given the file key. | S4 | Yes (A2-S3 method) | | | | pending |
| C15 | C2SP signed-note is UTF-8 text (no control characters other than newline), a blank line, and "— name base64(keyID‖sig)" lines. It defines Ed25519 (type 0x01) and a timestamped ML-DSA-44 cosignature type (0x06), and warns that PQ signatures can approach 5 kB. | S11 | Yes (record envelope) | | | | pending |
| C16 | libsodium secretstream chains state (after each message the nonce is XORed with MAC bytes) and documents no seek. Inference: no plain random access to a middle chunk, and deterministic resume needs the chain state. | S15 | No | | | | pending |
| C17 | Tink Streaming AEAD is symmetric-only, allows no append or modify, and has no rollback protection. Tink HPKE has an X_WING KEM (HKDF-SHA256 only) on Java main; which release ships it is unverified. | S14 | No | | | | pending |
| C18 | Apple CryptoKit has HPKE from iOS 17 / macOS 14, and X-Wing (XWingMLKEM768X25519, citing X-Wing draft 06) only from iOS 26 / macOS 26. A Rust core, not CryptoKit, is therefore the portable PQ path. | S13 | No | | | | pending |
| C19 | saltpack v2 authenticates the sender with per-recipient MAC keys derived by DH between the sender's long-term key and the recipient key. This needs a DH-capable recipient key, so it does not transfer to a KEM-only PQ recipient. | S16 | No | | | | pending |
| C20 | Ente fixes its secretstream chunk size permanently ("Existing encrypted files depend on this chunk boundary"). rclone crypt's documented format has no final-chunk marker. Borg 1 reused counter nonces after a rollback (borg #1039). | S17, S18, S23 | No (lessons) | | | | pending |
| C22 | CCTV `hybrid_low_order` expects **header failure** for an `mlkem768x25519` stanza whose X25519 share is a low-order point (all-zero shared secret). Rust `hpke` 0.14.1 wraps `x_wing::DecapsulationKey` and calls its infallible `decapsulate` (xwing.rs l.28, l.181). `x-wing` 0.1.1 (2026-10-01) documents that this default type *accepts* non-contributory X25519, adds `DecapsulationKeyRejectNonContrib`, states that CFRG will pick a single behaviour for the RFC, and that the default type "will be altered" when it is published. Inference (untested until A2-S3): `hpke` 0.14.1 as a decoder fails `hybrid_low_order`. | S6, S26, S27 | Yes (A2-S3; decrypt paths) | | | | pending |
| C23 | Rust `hpke` 0.14.1 X-Wing encapsulation draws its 64 bytes of encapsulation randomness from a caller-supplied `CryptoRng` (`encap_with_rng`); the deterministic entry point is `pub(crate)`. So CE-style hedged randomness can be injected only through a seeded `CryptoRng` (source reading; not prototyped). | S6 | No (supporting F5) | | | | pending |
| C21 | Header overhead arithmetic (not measured on family data). At F3's 0.9M–4.5M files for 2–10 TB, one PQ stanza per content object costs about 1.5–7.3 GB of headers; two stanzas about 2.9–14.3 GB, i.e. about 0.07 % vs 0.14 % of stored bytes. Metadata records double these unless records are batched (§F6). | C6 + F3 | Yes (cost) | | | | pending |

## Findings

### F1. Construction: age v1 stays (CE D-1 reaffirmed)

- **Why age:** it is the only candidate that satisfies all four PLAN criteria together (C1, C3, C13, C14).
  - spec stability: C2SP, a versioned `v1` line, and a compatibility promise;
  - a conformance kit: CCTV;
  - implementations in Go, Rust and TypeScript: Go reference, rage, typage;
  - a stock CLI that can decrypt.
- **What CE already settled** (S24):
  - Our own encoder writes the standard format, because the `age` crate cannot resume.
  - CE rejected a custom chunked format ("loses verification with stock age tools"). Nothing found here changes that.
- **Similar-work lessons that confirm the choice:**
  - **Publish a spec plus vectors.** Duplicacy's KDF drifted from its documentation (duplicacy #638, S23). A2's deliverable is therefore `object-format.md` **plus project vectors**. Our encoder can take injected randomness, so the encryption direction can have vectors even though CCTV's cannot (C14).
  - **Chunk size is permanent.** Ente's comment says so (C20). age fixes 64 KiB, which is fine.
  - **A final-chunk flag is essential.** rclone crypt lacks one (C20).
  - **Nonce state must never roll back.** Borg #1039 (C20). CE's hedged, per-file random keys avoid persistent counters. The journal rollback risk is R-1 in CE.
- **Devices that cannot decrypt** (restic #187, bupstash put-only keys, S19, S23): encrypting to a public key helps only when paired with append-only storage. This is already settled in CLAUDE.md and ADR-0001.

### F2. Post-quantum from day one (OD-06)

- **The threat is real for Reliquary's data.**
  - Keep-forever data travels as ciphertext through Cloudflare and by post.
  - An X25519 wrap recorded today opens the file key to a future quantum adversary.
  - The symmetric layers and HMAC IDs are not exposed the same way (F3 Q7). This is reasoning plus secondary NIST timelines; it does not rest on the NIST dates (D2 C18 is "secondary only").
- **What PQ costs:**
  - **Bytes:** 1,627 B or 3,184 B per object instead of 168 B (C6). That is about 0.07 %–0.14 % of stored bytes (C21), plus the same again for metadata records unless they are batched.
  - **CPU:** one X-Wing encapsulation per stanza per object. D2 measured software *decapsulation* at 4,904–6,827 per second in the container (D2 C12, x86). Phone encapsulation cost is **not measured**; that is the job of A2-S1 (OL kit).
  - **Distribution:** a recipient string is 1,959 characters (C6). The QR code must carry the trust-bundle **digest** (CE D-9), never the recipient itself.
  - **Tooling:** heirs need Go age ≥ 1.3.0 or the `age-plugin-pq` plugin (C13). No Rust drop-in exists (C7).
  - **Spec maturity:** the KEM is referenced from an IETF *draft* (-03) and filippo.io/hpke-pq (C4, S8). One behavioural detail is still open at CFRG: whether a non-contributory (all-zero) X25519 result is rejected. age's CCTV vectors already pin *reject* (C22). Because an honest encryptor never produces such a share, this affects only how decoders treat malformed or hostile stanzas, never the bytes of a valid object.
- **Risk if the KEM draft changes:** the age stanza name `mlkem768x25519` is bound to its referenced definition. The age(1) promise covers files already written (C13). This is an inference about maintainer behaviour, and skeptics should attack it.
- **No mixing** (C5). A PQ object cannot carry an X25519 stanza "for compatibility", and cannot carry a scrypt stanza. This binds D2's recovery design (D2 F3).
- **Fallback if A2-S3 finds no interoperable Rust X-Wing:**
  1. The device encoder emits X25519 for now.
  2. The homelab rewraps stored headers to PQ {X, R} at ingest (A′).
  3. The harvest-now exposure is then limited to transit copies: staged R2 objects and USB sticks. Those copies are short-lived in R2 but can be recorded.

  This is weaker, but it can be recovered from. A2-S1's "fail → X25519 now with a migration plan" already covers it.

### F3. Recipient set and rotation

- **Rotation cost.** Each stanza wraps the same file key (C1), so rotating or adding a recipient means rewriting the header only (C2). About 10 TB of rewrites if done late (A6 C2). Nothing is rewritten if done at ingest from day one (A′).
- **Placement choice (DR-A2-2):**

  | Option | Device header | Stored header | For | Against |
  |---|---|---|---|---|
  | **P1 (recommended): devices write {I_e} only; the homelab writes {X, R} at the A′ rewrap** | 1,627 B, which passes A2-S1 | {X, R}, written and checked at home | The recovery stanza on every stored object is produced by code the owner controls. Smallest device cost | Staged or USB copies are readable only with I_e (and the device still holds the plaintext until its receipt). An object whose device and homelab are both lost before commit is unrecoverable (AR-07 window). I_e must be kept until the R2 and USB pipeline drains (A3 DR-A3-3) |
  | P2 (D2 draft): devices write {I_e, R} | 3,184 B, which **fails** A2-S1 as written | {X, R} (rewrapped) or {I_e, R} (posture A) | In-transit copies survive losing I_e. Late USB bundles stay readable after I_e is destroyed | The R stanza cannot be verified at ingest (C9). Under posture A that unverified stanza **is** the stored recovery path. +1,557 B per object and per record |
  | P3: P2 plus the device discloses its R-encapsulation randomness inside the record, so the homelab recomputes and compares the R stanza | 3,184 B | as P2 | Verifiable R | Custom, needs crypto review; the randomness must be stripped before archiving the record. **Not recommended without review** |

- **Posture coupling.** If OD-07 ends up at posture A (keep received ciphertext, no rewrap), P1 leaves stored objects with no R. In that case the analyst recommends the homelab rewrap to add R anyway, rather than trusting device-written R stanzas.
- **Parser.** Whatever is chosen, the header parser must accept 1–N stanzas (CE open issue 6). The ingest check should be: *exactly the stanza count and types the device's trust-bundle epoch prescribes, all `mlkem768x25519`, no plugin, scrypt or armor* (SR-22).

### F4. Sender authentication and binding

- **Why a signature is needed.** age is anonymous (C12), so a forged object from anyone holding the recipient is always a *valid age file*. It must be rejected by the **signed record**, before any catalog write (A2-S4; D1 SR-03, SR-04).
- **Options:**

  | Option | Works with PQ? | Stock `age -d` still works? | Verdict |
  |---|---|---|---|
  | Device Ed25519 signature on the record, inside the encryption (CE §9) | Yes. The signature is verified at ingest now, and the homelab keeps its own verdict | Yes | **Adopt** |
  | HPKE Auth mode | **No**, not defined for the PQ KEMs (C10, C11). Even with DHKEM it has KCI caveats | No: age uses SealBase | Reject |
  | HPKE PSK mode (per-device PSK) | Yes | **No**: not the age stanza | Reject |
  | saltpack-style DH MAC keys | No (C19) | No | Reject |
  | Outer signature visible to the cloud | Yes | Yes | Not needed. The cloud already knows the device from its credential, and the homelab verifies the inner signature |

- **Fields the record signature binds.** Extends CE §9; D1 SR-03/SR-13; A3 F8.
  - **Content:** `dedup_id` (A1 text form, with epoch), `sha256`, `size` (true, unpadded).
  - **Object:** staging `key`, `header_mac` of the **device-written** header (h0; A6 keeps it), `ct_len`, `prefix_len`, `profile`. `object: null` marks a dedup hit.
  - **Device and order:** `device_id` (must equal the signing key's registered device), `device_seq`, `record_id` (random, the idempotency key).
  - **Time:** `recorded_at` (device time, context only; SR-19).
- **Why `header_mac` plus `ct_len` binds the object.** A payload is authenticated only under its file key, and the header MAC commits to the header under that key. An attacker who lacks the file key cannot pair a different payload with this header. The homelab still decrypts and matches `sha256`/`dedup_id`/`size` (SR-04), which is the binding of record to content.
- **When to sign: at sealing, not at start.** This agrees with A3 F8.
  - At upload start, persist the unsigned record fields in the sealed upload state (CE §8.1).
  - Allocate `device_seq` and sign when the record first leaves the device.
  - A restarted upload then leaves no sequence gap.
  - This fixes the CE E4 concern ("metadata built from state that Complete deletes") without signing early.
- **What receipts bind.** Bind `record_sha256`, the SHA-256 of the exact **signed plaintext record**, not the record's age ciphertext. It stays the same when records are batched (A3 F8) and when the homelab rewraps record headers (A6 F3). It reveals nothing guessable, because the record contains a random `record_id` and a signature. The receipt format belongs to A3; this is the A2 input.
- **PQ signatures.**
  - Forging a device signature needs a quantum computer *at verification time*, and the homelab verifies at ingest. So Ed25519 is adequate for v1 (inference, medium).
  - Where this fails: anyone who later relies on *old* signatures as provenance evidence after a cryptographically relevant quantum computer exists.
  - Keep signature agility: signed-note key names and type bytes (C15), and trust-bundle algorithm IDs (D2 Q9).

### F5. Resumability, truncation and random access with PQ headers

- **Layout.** Everything in CE §5–§8 holds with prefix_len = header + 16:
  - 1,643 B with one PQ stanza, or 3,200 B with two;
  - the part and chunk math is unit-tested for prefixes of 1–65,551 B;
  - the sealed state persists the whole prefix, so it grows by about 1.5–3 KB per in-flight upload.
- **Hedging.** Derive each stanza's 64-byte X-Wing encapsulation randomness from the CE hedge (HKDF over the CSPRNG seed with salt SHA-256(plaintext); new info labels such as `reliquary/v1/hedge/xwing-encap/<i>`). Feed it to the library through a seeded CSPRNG. Source reading confirms this is the only route: `hpke` 0.14.1 draws the 64 encapsulation bytes from the caller's `CryptoRng`, and its deterministic entry point is crate-private (C23). This is **not prototyped**; A2-S2 or a follow-up should cover it.
- **Decrypt-side conformance (C22).** Any Rust code that *opens* `mlkem768x25519` stanzas (A8 device restores under D2 K-10; Rust homelab tools, if any) must reject a low-order X25519 share, either via `x-wing` ≥ 0.1.1 `DecapsulationKeyRejectNonContrib` (which `hpke` 0.14.1 does not expose) or by checking the X25519 output itself. Go age already does (CCTV). The client's *encrypt* path is unaffected.
- **Truncation.** Keep CE §5.4 (valid-length classes) and §5.5 (authenticate the final chunk before serving any chunk). Error codes are specified in `object-format.md`, as A2-S4 requires.
- **iOS (B4 K2–K4).**
  - The keystream guard must hold **before** a part file is handed to `nsurlsessiond` (K2).
  - The spool is bounded by BUD-TMP (K3).
  - Sequential sources regenerate parts by re-reading (K4; CE §8.6 already measures this).
  - None of these changes the format.

### F6. Metadata record (provisional; follows A5)

- **Envelope, recommended.** Plaintext = C2SP signed-note (C15):
  - note text = one line of compact JSON, I-JSON profile: UTF-8, no duplicate keys, integers ≤ 2^53;
  - then the device's Ed25519 signature line `— <device key name> <b64(keyID‖sig)>`.
  - This is CE §9's shape (JSON line plus signature line) moved onto a published envelope that has key IDs and algorithm agility. It also matches what A3 F4 suggests for receipts.
  - Padding goes *inside* the signed JSON (a `pad` field), because signed-note allows no trailing bytes.
  - Records travel in **record batches**: one age file carrying N length-prefixed signed notes. This amortizes the PQ header (A3 F8).
- **Fields, v0.** From H4 §6.1, plus:
  - A1's text-form `dedup_id` with epoch, and a reserved `chunk_list`;
  - A3's `device_seq` and `record_id`;
  - B4 K5's opaque `source_version` token, used in place of stat fields for PhotoKit;
  - raw-bytes forms for locators and names (`*_raw_b64`), because paths are not always valid UTF-8;
  - `content_encoding` (reserved; always `identity` in v1);
  - `padded_len` (if DR-A2-4 adopts padding).
- **Evolution rules:**
  - `schema_version` is an integer; `kind` is an open set.
  - Unknown fields are preserved and ignored.
  - A field's meaning never changes within a `v`.
  - Plugin-defined `source_hints` are namespaced by plugin ID.
- **Alternative: deterministic CBOR** (CDE, S22).
  - For: native byte strings for raw paths and IDs (A1 prefers the 35-byte binary ID in CBOR); smaller.
  - Against: heirs need a decoder; no published signing envelope was checked in this run (COSE was not read, because the primary source was blocked).
  - The analyst leans JSON-in-signed-note, because the break-glass tool (D2/E7) must read names anyway and text is easiest to inspect decades later. **Low-medium confidence; revisit after A5.**

### F7. Length hiding and compression

- **Padding: Padmé, conditional on F3-S1** (DR-A2-4).
  - Mechanism: append zero bytes to the plaintext before encryption.
  - IDs and SHA-256 stay over the unpadded bytes (Borg precedent, F3 C9).
  - Resume stays byte-identical, because zero padding is deterministic.
  - Every cloud-visible size field must become the padded length: receipts, presence (dedup_id, size) and SR-24 declarations (F3 C10).
  - The break-glass kit must truncate to the size given in the record.
- **Compression:** none in v1.
  - Photos and videos, the main keepsakes, are already compressed. This is an expectation; A5 or the E1 corpus should confirm the byte mix.
  - Compression would stop stock `age -d` from giving back the original file, and would add a parser to the ingest path.
  - Reserve `content_encoding` in the record so documents can gain zstd later without a format break.

### Alternatives compared

| Option | Fit with settled requirements | Pros | Cons | Evidence |
|---|---|---|---|---|
| **age v1, mlkem768x25519 only (recommended)** | Fits: encrypted to the homelab key; devices cannot read | Stock Go age ≥ 1.3.0; C2SP spec; CCTV hybrid vectors; PQ | 1.6–3.2 KB header; client must implement the X-Wing stanza; KEM referenced from an I-D | C4–C8, C13, C14 |
| age v1, X25519 (CE today) | Fits | 168 B header; any age version; Rust crate decrypts | Harvest-now exposure of keep-forever data | C6, F3 Q7 |
| age v1, mixed PQ + X25519 | — | — | Spec SHOULD NOT; Go age refuses | C5 |
| HPKE (base/auth) + custom STREAM | Fits | Full control | No stock CLI; own spec; Auth mode unavailable with PQ | C10, CE §3 |
| Tink Hybrid (X-Wing) + Streaming AEAD | Fits | Google-maintained; nOAE definition | No stock CLI; symmetric streaming layer needs its own key wrap; release support for X-Wing unverified; Swift friction (S23) | C17 |
| libsodium sealed box + secretstream (Ente) | Fits | Audited in Ente; mobile-proven | No PQ; chained state, no documented seek; no stock CLI | C16, C20 |
| saltpack signcryption | Fits | Built-in sender authentication | No PQ; the DH-based authentication does not carry over to a KEM | C19 |
| OpenPGP RFC 9580 (+ PQC draft) via Sequoia/GnuPG | Fits | Very widespread tooling | PQC for OpenPGP still a draft (status unverified); large surface; not evaluated in depth | S21 |

### Similar work and lessons

| Project or paper | What they do | Borrow or avoid | Source |
|---|---|---|---|
| age / C2SP + CCTV | Spec plus a language-neutral vector kit | **Borrow:** publish `object-format.md` + vectors, including encrypt-direction vectors from injected randomness | S1, S4 |
| Duplicacy #638 | KDF code diverged from the docs | **Avoid:** CI must run the vectors against every implementation | S23 |
| Ente | Per-file secretstream key, 4 MiB chunks, permanent chunk size | **Borrow** per-file keys (age already does this); **note** chunk size is forever | S17 |
| rclone crypt | 64 KiB secretbox chunks, no final marker; no plaintext checksum (#1712) | **Avoid** a missing final flag; **borrow** a plaintext digest inside the signed record | S18, S23 |
| bupstash, restic #187 | Put-only keys; asymmetric crypto only helps with append-only storage | Confirms the ADR-0001 pairing | S19, S23 |
| Borg 1 / Borg 2 | Counter-nonce reuse after rollback; Borg 2 uses session keys and AAD type binding | **Avoid** persistent counters; **borrow** binding type and version into authenticated data (our record `type`/`v`) | S20, S23 |
| saltpack | Sender authentication in the format | Not applicable to KEM recipients | S16 |
| age #59 | "Anyone can replace the file": age has no sender authentication | Motivates F4 | S23 |

### Tools and libraries

| Name | Purpose | Licence | Maturity | Source |
|---|---|---|---|---|
| Go `filippo.io/age` + age-inspect, age-plugin-pq | Homelab decrypt and rewrap; heir tool; interop oracle | BSD-3-Clause (not re-checked) | v1.3.2, 2026-08-29; go.mod needs Go 1.25 | S2 |
| Rust `age` | Decrypt side (X25519 only) | MIT/Apache-2.0 | 0.12.1, 2026-07-14; no PQ identity | S5 |
| Rust `hpke` (RustCrypto) | X-Wing stanza encoder and decoder in the client core | MIT/Apache-2.0 | 0.14.1; interop unverified | S6 |
| Rust `x-wing`, `ml-kem` | X-Wing KEM building blocks | MIT/Apache-2.0 (crate ships LICENSE-MIT and LICENSE-APACHE) | 0.1.1, 2026-10-01 ("draft 06"; adds rejecting decapsulation key); ml-kem 0.3 | S7, S26 |
| typage (`age-encryption`) | TypeScript age with hybrid PQ; A2-S3 third implementation | BSD-3-Clause (not re-checked) | 0.3.1, 2026-08-28 | S12 |
| CCTV age vectors | Conformance (decrypt direction) | Not checked (README: copying allowed "without attribution") | 2026-09-25 | S4 |
| ed25519-dalek | Device record signatures | BSD-3-Clause (not re-checked) | not checked in this run | — |
| kage (Kotlin) | Possible Android-native reader | — | **PQ status unknown** (not reached) | — |

## Spikes

Placeholder: a separate spike runner is running these in parallel. Results will be merged here.

| Spike | Hypothesis | Pass → / fail → (decision) | Exec tag | Budget IDs | Data class | Status | Result |
|---|---|---|---|---|---|---|---|
| A2-S1 Throughput and energy, X25519 vs PQ | PQ adds a header ≤ 3 KB per object and ≤ 10 % throughput loss on a low-end phone; encryption is never the bottleneck against a 100 Mbit uplink | Pass → PQ from day one (DR-A2-1); fail → X25519 now plus a migration plan. **Note:** the analyst measured 3,184 B for two PQ stanzas, which fails the header limit as written; one stanza (1,627 B) passes (DR-A2-2) | CT + OL | BUD-HASH, BUD-BAT-S | SYN → results | (spike runner) | (spike runner) |
| A2-S2 Kill-and-resume, 50 random kills | Every object decrypts to the exact SHA-256, at most one segment is re-encrypted per kill, no (key, nonce) reuse, no file key survives commit. Should include a PQ-header variant and the X-Wing hedging | Pass → CE resume mechanism in ADR-0007; fail → temp-file ciphertext spool | CT | BUD-TMP | SYN → results | (spike runner) | (spike runner) |
| A2-S3 Interop | Rust output (with the X-Wing stanza) decrypts with Go age ≥ 1.3.0 and typage, and vice versa; 100 % of CCTV vectors (incl. `hybrid_*`) and project vectors pass. **Expect `hybrid_low_order` to fail on a plain `hpke` 0.14.1 decoder (C22)**; record it, then re-run with a rejecting decapsulation | Pass → Rust `hpke` X-Wing in the encoder; fail → F2 fallback (X25519 on device, PQ rewrap at home) | CT | — | SYN → results | (spike runner) | (spike runner) |
| A2-S4 Forgery and truncation | A forged object plus record (attacker holds only the public key) and a dropped final chunk are both rejected before any catalog write, with specific error codes | Pass → F4 binding set; fail → add an outer binding | CT | — | SYN → results | (spike runner) | (spike runner) |

The measurement in M1 used Go age binaries on an x86 container VM, not a phone.

## Conflicts with settled text

None that contradict. For the owner's awareness:

1. ADR-0001 §2 says content is encrypted to "the homelab public key (e.g. X25519 / age)". `mlkem768x25519` fits the "e.g.", and the singular "key" is extended by a recovery recipient. Both points are also recorded in D2's conflicts section.
2. Device-signed records and homelab-signed receipts are already queued as OD-04 (superseding details of ADR-0001 §4).
3. The A2-S1 pass rule ("PQ header ≤ 3 KB per object") is A2-local (budgets.md: "Keep local"). Two PQ stanzas fail it. This note does **not** change the threshold. It asks the owner through DR-A2-2.

## Open questions

1. **Rust X-Wing interop.** Does `hpke` 0.14.1 (on `x-wing` 0.1.0, "draft 06") produce stanzas that Go age 1.3.2 opens, and does it decrypt the CCTV `hybrid_*` vectors? Owner: A2-S3 (spike runner). Needed by Gate A.
2. **Phone cost of X-Wing encapsulation** (low-end Android, iPhone), including small-file-heavy libraries. Owner: A2-S1 OL kit. Needed by Gate A.
3. **Recipient placement**, P1 vs P2 (DR-A2-2). It couples to OD-07 (A6) and OD-08 (D2). A joint A2/A6/D2 review is needed before ADR-0007/0008/0012 drafts.
4. **Is a 128-bit file key adequate against quantum key search** for keep-forever data? The age spec fixes 16 bytes and derives a 256-bit payload key. No primary source on this was read in this run (NIST blocked). Skeptic 1 should find one.
5. **Status of draft-ietf-hpke-pq**, and whether a later revision changes MLKEM768-X25519 bytes. Datatracker was blocked. Owner: H1 source escalation.
10. **CFRG's choice on non-contributory X25519 in X-Wing** (C22), and whether it reaches age's `mlkem768x25519` definition. The CFRG mail archive was blocked. Expected impact is decoder strictness only. Owner: H1 (source), A2 (track before Gate A).
6. **Record encoding:** JSON-in-signed-note vs deterministic CBOR, after A5's item model and the E7/D2 break-glass tool requirements. Owner: A2 Wave 2.
7. **kage PQ support**, and which Tink release first ships X_WING. Relevant only if a non-Rust client is chosen (ADR-0003). Owner: T1/B-track.
8. **Device signing key storage:** Ed25519 support in Android Keystore and iOS Secure Enclave was not checked. The Secure Enclave is P-256. Owner: D3.
9. **Error-code table and strict parser limits** (maximum header size, maximum stanza count, maximum record size) for `object-format.md`. The values are spec parameters to propose in the next stage, not budgets.

## Recommendation

Adopt for the ADR-0007 draft:

1. **Construction:** standard age v1 objects from the client's own encoder, with CE's journaled resume (CE D-1). Restrict the profile to a single stanza type per object: no scrypt, plugin or armor. Use a generic multi-stanza header parser with strict limits.
2. **PQ from day one (DR-A2-1):** every stanza on every object and record is `mlkem768x25519`. This is conditional on A2-S3 showing Rust↔Go interop. If that fails, take the F2 fallback. Every decoder the project ships must pass all CCTV `hybrid_*` vectors, including the low-order rejection (C22).
3. **Recipients (DR-A2-2):** the device writes the ingest stanza only; the homelab rewraps to {archive X, recovery R} at ingest and keeps h0. Pending the joint decision with D2 and A6.
4. **Sender authentication:** device Ed25519 signature on a signed-note record inside the encryption, binding the §F4 fields. Allocate `device_seq` and sign at sealing time. Receipts bind `record_sha256`. No HPKE Auth or PSK mode.
5. **Truncation and random access:** CE §5.4 and §5.5 rules, unchanged.
6. **Length hiding (DR-A2-4):** Padmé zero padding if F3-S1 passes, with every cloud-visible size field switched to the padded size. No compression in v1.
7. **Deliverables next stage:** `docs/spec/object-format.md` with encrypt-direction project vectors (injected randomness) and decrypt-direction CCTV conformance.

**What would change this:**

- A2-S3 interop failure: X25519 on devices, PQ at home.
- A2-S1 showing PQ encapsulation is a phone bottleneck (unlikely for a per-object cost, but unmeasured).
- OD-07 choosing a posture without rewrap: then R must be written by the homelab anyway, or P2/P3 accepted knowingly.
- A5 needing binary-heavy records: then CBOR.

## Decision requests

### DR-A2-1: Post-quantum recipients from day one (this is OD-06)
- **Needed by:** Gate A (one-way door #2), before the first real ingest.
- **Evidence:** §F2; C4–C8, C13, C21; F3 Q7; D2 F3.
- **Options:**

  | Option | What it means for the family | Cost | Reversibility | Risks |
  |---|---|---|---|---|
  | A. PQ (`mlkem768x25519`) for all stanzas now (recommended) | Nothing visible | +1.5–3 KB per object (≈ 0.07–0.14 % of bytes); custom Rust stanza code; heirs need age ≥ 1.3.0 | Moving back to classic is possible but pointless | KEM referenced from an I-D; Rust interop unproven until A2-S3 |
  | B. X25519 now; PQ later by rewrap | Nothing visible | Smallest header; later rewrap of stored headers (about 10 TB of I/O unless done at ingest) | Stored copies can be upgraded; **transit copies already recorded cannot** | Harvest-now on every staged object and USB stick until the switch |
  | C. Mixed PQ + X25519 | — | — | — | Forbidden by the spec's SHOULD NOT and refused by Go age |

- **Recommendation:** A, gated on A2-S3.
- **Touches settled text:** no ("e.g. X25519 / age").
- **If no decision by the deadline:** draft ADR-0007 with A and the fallback written in. No production keys are generated before acceptance.

### DR-A2-2: Where the recovery stanza is written, and the A2-S1 header limit
- **Needed by:** Gate A, decided together with OD-07 (A6) and OD-08 (D2).
- **Evidence:** §F3; C6, C9, C21; D2 Q2; A6 F3.
- **Options:**

  | Option | What it means for the family | Cost | Reversibility | Risks |
  |---|---|---|---|---|
  | P1. Device writes {ingest}; the homelab writes {archive, recovery} at ingest (recommended) | Nothing visible | 1,627 B device header (passes A2-S1) | Can move to P2 later with a client update | Objects still in transit when both device and homelab are lost cannot be recovered (AR-07); ingest keys kept until the pipeline drains |
  | P2. Device writes {ingest, recovery} (D2 draft) | Nothing visible | 3,184 B header (fails A2-S1 as written) | Can drop R later with a client update | Recovery stanzas cannot be verified at ingest (C9); a faulty client could silently break recovery if they are the only copy |
  | P3. P2 plus disclosed encapsulation randomness so the homelab checks R | Nothing visible | As P2, plus custom crypto | As P2 | Needs expert review |

- **Recommendation:** P1. If the owner prefers P2, also confirm that A2-S1's limit is meant *per stanza*, and still require a homelab-written R on stored objects.
- **Touches settled text:** no.
- **If no decision by the deadline:** draft ADR-0007 so the format allows 1–N PQ stanzas (both options fit), and leave placement to ADR-0008/0012.

### DR-A2-3: Sender authentication by a device-signed record (not HPKE Auth), with signature agility
- **Needed by:** Gate A (one-way door #2).
- **Evidence:** §F4; C10–C12, C15.
- **Options:**

  | Option | What it means for the family | Cost | Reversibility | Risks |
  |---|---|---|---|---|
  | A. Ed25519 device signature on a signed-note record inside the encryption; receipts bind the record digest (recommended) | Nothing visible | Tiny | New signature types can be added (signed-note agility) | A compromised device can still sign junk as itself (bounded by D1 SR-10/SR-24) |
  | B. HPKE Auth mode | — | — | — | Not available with PQ KEMs; not stock age |
  | C. Hybrid Ed25519 + ML-DSA signatures now | Nothing visible | Larger records (signed-note warns PQ signatures "can be up to nearly 5kB", S11; exact ML-DSA sizes not read in this run); library maturity unchecked | — | Premature; verification happens at ingest, before any quantum computer |

- **Recommendation:** A.
- **Touches settled text:** no; this refines OD-04's "device-signed manifests".
- **If no decision by the deadline:** assume A.

### DR-A2-4: Length hiding with Padmé (conditional on F3-S1)
- **Needed by:** Gate A, because padding changes object lengths and cloud-visible size fields.
- **Evidence:** §F7; F3 C7–C10; CE D-7.
- **Options:**

  | Option | What it means for the family | Cost | Reversibility | Risks |
  |---|---|---|---|---|
  | A. Padmé zero padding (recommended if F3-S1 shows most sizes unique and cost < 3 %) | The break-glass tool must trim files to their true size | ≤ 3.1 % storage and upload for files ≥ 64 KiB (arithmetic) | Can be switched off for new objects; old objects stay padded | Useless unless every cloud-visible size field is padded too |
  | B. No padding (CE D-7 default) | None | None | Can adopt later for new objects only | Exact sizes fingerprint files (AR-05) |

- **Recommendation:** A if F3-S1 passes; otherwise B, with AR-05 accepted.
- **Touches settled text:** no.
- **If no decision by the deadline:** B, and reserve `padded_len` in the record so A can be added later.

## Hand-offs

| To | What | Why |
|---|---|---|
| D2 (ADR-0008), A6 (ADR-0012) | DR-A2-2 placement; C9 (device-written R cannot be verified); keep h0; stanza-count check per trust-bundle epoch | Recipient set and posture must agree |
| A3 (ADR-0009) | Seq and signature at sealing (agree with F8); receipts bind `record_sha256`; record-batch framing; padded sizes in receipts | §F4, §F6, §F7 |
| A4 (ADR-0011) | USB bundles carry the same objects and records; late bundles need I_e kept until drained under P1 | §F3 |
| A1 (ADR-0006) | Record carries the text-form `dedup_id` if JSON records are kept (A1 assumed the binary form in CBOR) | §F6 |
| D3 (ADR-0014), E5 | The QR carries the trust-bundle digest, never a 1,959-character PQ recipient; device Ed25519 key storage per platform | C6; open question 8 |
| A8 (ADR-0028) | Restore sealing to a device key: if PQ (D2 K-10), the client needs the Rust X-Wing *decrypt* path too, because the `age` crate lacks it; that path must reject low-order X25519 shares (`hpke` 0.14.1 alone does not) | C7, C22 |
| G2 (ADR-0035) | Run CCTV plus project vectors in CI against every implementation (Duplicacy lesson) | C14, S23 |
| F3 | F3-S1 result decides DR-A2-4 | §F7 |
| H1 | Blocked sources (Method); OD numbers for DR-A2-1..4; DR-A2-1 is OD-06 | Registry owner |
| Next A2 stage | ADR-0007 draft and `docs/spec/object-format.md` with vectors once A2-S1..S4 report | Deliverables |
