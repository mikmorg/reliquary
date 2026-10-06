# A2. Object envelope and metadata-record format

- **Workstream:** A2 (see `docs/research/PLAN.md`, section "A2.")
- **Status:** Final for Wave 1 (batch W1-a). Analyst deep read, continuation pass, three skeptic reviews (sources, logic, adversary) and spikes A2-S1 (CT part) to A2-S4 are all merged. The claim verdicts are the code-computed tally and are not overridden. The metadata-record schema stays **provisional** (P1; it follows A5).
- **Date:** 2026-09-29 (last updated 2026-10-06)
- **Wave 1 scope:** the P0 **object envelope** for the ADR-0007 draft: construction, post-quantum option (OD-06), recipients, sender authentication, resumability, truncation, padding and agility.
- **Feeds:**
  - ADR-0007 draft: `docs/adr/0007-object-envelope-and-metadata-record.md` (Proposed, partial);
  - spec draft: `docs/spec/object-format.md` (Draft);
  - OD-06 (PQ);
  - evidence for OD-07 (A6 posture), OD-08 (recovery recipient) and OD-04 (device-signed records);
  - one-way door #2 (object envelope, PQ, sender authentication);
  - new decision requests DR-A2-2 to DR-A2-4 (H1 assigns OD numbers). DR-A2-1 is OD-06.
- **Depends on:**
  - **T1 spike 2**, the CE note: `docs/research/content-encryption-format.md` and `spikes/content-encryption/`. It exists, and this note builds on its D-1, D-2, D-3, D-7 and D-9 and its open issues 6 and 8.
  - Drafts: D2 (`d2-key-hierarchy-custody-recovery.md`), F3 (`f3-security-literature.md`, incl. C28), D1 (`docs/security/threat-model.md`: SR-03, SR-04, SR-13, SR-14, SR-22, SR-24), A1, A3 (F4, F8, Q10), A6 (F3, posture A′), B4 (K2–K5) and H4 (`docs/design/data-model.md` §6).
- **Traceability rows advanced:** R-19 (content and metadata encrypted on the device), R-20 (devices cannot read), R-25 (locator, name and mtime only at the homelab), Q1-4 (resumable uploads vs age randomness).

## Summary

**Keep the CE design: every content object is a standard age v1 file written by the client's own resumable encoder.** Use the native age post-quantum recipient `mlkem768x25519` (X-Wing) for every stanza.

The spikes now back this:
- **Interop (A2-S3).** The Rust `hpke` 0.14.1 X-Wing stanza interoperates byte for byte with Go age 1.3.2, typage 0.3.1 and kage 0.8.0, in both directions: 853/853 checks.
- **Resume (A2-S2).** CE's journaled resume survives 70 random kills with a PQ header.
- **Forgery and truncation (A2-S4).** A device-signed record inside the encryption rejects 26/26 forgery, truncation and downgrade attacks before any catalog write.

The main remaining unknown for OD-06 is **phone cost**. PQ is a fixed cost per object. On x86 it costs 35–52 % throughput on 16–100 KiB objects and 5–15 % at photo sizes; the phone figure needs the A2-S1 OL kit.

Changes from the earlier draft, after the skeptic review:
1. **Recipient placement no longer rests on the 3 KB budget or on verifiability alone.** The recommendation is P1 with escrowed retired ingest keys ("P1-E"), with P2′ as a close alternative. In both, the homelab writes the stored recovery stanza.
2. **"Rotation by rewrap" is not revocation.** This is now explicit.
3. **The signed record binds a transport-neutral object identity**, not the R2 staging key.
4. **The signature algorithm is left to D3**, so that hardware-backed P-256 keys stay possible.
5. **Rust crypto dependencies must be pinned exactly**, and the X-Wing low-order rejection lives in project code.

**Confidence:**

| Area | Confidence |
|---|---|
| Spec and source facts; interop | High (verified claims; A2-S3) |
| PQ from day one | Medium-high, pending phone cost (A2-S1 OL) |
| Recipient placement | Medium (couples to OD-07 and OD-08; P1-E is new and unreviewed) |
| Record encoding | Low-medium (provisional) |

## Questions

| # | Question (PLAN A2) | Short answer | Confidence |
|---|---|---|---|
| 1 | Which construction? | **age v1 (C2SP)**, as in CE D-1. It is the only candidate with all of: a public spec, a conformance kit (CCTV), independent Go/Rust/TS/Kotlin implementations and a stock CLI with a written backwards-compatibility promise (C1, C13, C14; A2-S3). | High |
| 2 | Post-quantum from day one? Header size and phone cost? | **Yes, `mlkem768x25519` for all stanzas (OD-06)**, provided the A2-S1 OL kit shows acceptable phone cost. Header sizes: one stanza 1,627 B, two 3,184 B, X25519 168 B (C6, **verified**). Rust↔Go/typage/kage interop is verified (C25, A2-S3). x86 cost per object: about +77 µs per stanza to generate and +215 µs to open. Throughput loss vs X25519 is 52 % at 16 KiB, 37 % at 100 KiB, 15 % at 1 MiB and 5 % at 4 MiB (C26). Phone cost: **no result** (kit-ready). | Medium-high (recommendation); High (sizes, interop); none (phone) |
| 3 | Recipient set; rotation by rewrap only | 1–N stanzas, all PQ (no mixing, C5). Changing recipients is a header rewrite (C2, **verified**). **Rewrap is not revocation**: the file key never changes, so an old ingest key still opens every recorded copy that was wrapped to it (§F3). **Placement is a decision** (DR-A2-2): P1-E is recommended and P2′ is the alternative. In both, the homelab writes the stored R. | High (mechanics); Medium (placement) |
| 4 | Sender authentication | **A device signature on the record, inside the encryption.** HPKE Auth mode does not exist for PQ KEMs (C10, C11, **verified**). age authenticates no sender (C12, **verified**; A2-S4 premise). The record binds content, transport-neutral object identity, device, sequence and time (§F4). Keeping a classical signature for v1 rests on reasoning only (C24, **secondary only**) plus a design rule: the homelab's signed ingest verdict is the durable authority. | High (options ruled out); Medium (classical-signature adequacy) |
| 5 | Resumability | **CE mechanism unchanged; tested with PQ.** prefix_len is 1,643 B (one stanza) or 3,200 B (two). A2-S2 passed: at most one part re-encrypted per kill, no (key, nonce) reuse, no key survives commit, no temp ciphertext spool (C27). X-Wing encapsulation randomness is hedged through a seeded RNG that asserts exactly 64 bytes are drawn (C23, now prototyped). | High |
| 6 | Truncation, reordering, random access | age STREAM, plus CE §5.4 and §5.5. A2-S4 showed two independent layers: the length binding catches truncation and append before decryption, and STREAM catches them without it (C28). **New rule:** restore output is exposed only after the final chunk and the record's SHA-256 verify. | High |
| 7 | Length hiding; zstd | **Padmé zero padding if F3-S1 passes** (DR-A2-4), with every cloud-visible size padded. Size buckets are an added option. With padding, stock `age -d` output carries trailing zeros, so heirs need the true size. No compression in v1; `content_encoding` is reserved. | Medium |
| 8 | Metadata-record fields and encoding | **Provisional:** a C2SP signed-note whose text is one line of I-JSON, in batches of per-(device, file) signed units. CBOR (CDE) is the main alternative. Revisit after A5. | Low-medium |
| 9 | Algorithm agility and migration | Stanza-level agility gives new recipient types by rewrap. The payload suite is fixed by age v1; replacing it means re-encryption, about 28 h per 10 TB at 100 MB/s (arithmetic). Signature agility comes from signed-note types: 0x01 Ed25519, 0x02 ECDSA, and 0xff for future types such as a PQ signature (C15, corrected). | Medium |
| 10 | (new) Can the homelab verify a device-written recovery stanza? | **No** without skR or the encapsulation randomness (C9, **secondary only**: logic). Nobody can check a *homelab-written* R stanza without skR either. Only a sampled recovery drill with the real R key checks R stanzas under any placement. | Medium-high (logic) |
| 11 | (new) Is there a drop-in Rust PQ age implementation? | **No.** `age` 0.12.1 has no `mlkem768x25519` (C7, **verified**). The spike's own stanza code on `hpke` 0.14.1 works (A2-S3). | High |
| 12 | (new) Is X-Wing behaviour stable across implementations? | **Not fully.** A decoder built on plain `hpke` 0.14.1 accepts low-order shares and fails CCTV `hybrid_low_order` **and** `hybrid_identity` (C22, **verified**; A2-S3). `x-wing` says its default key type "will be altered" once the RFC is published. So pin exact versions and keep the rejection in project code. | High |

## Method

- **Sweep:** three scouts (docs, source, community), the analyst deep read, a continuation pass (2026-10-06), three skeptics (sources, logic, adversary) and the spike runner (A2-S1 to A2-S4).
- **Read by the analyst, in full or the relevant sections:**
  - the C2SP age spec;
  - the HPKE-PQ draft editor's copy;
  - the X-Wing draft §"Not an authenticated KEM";
  - the HPKE source markdown;
  - C2SP signed-note;
  - the CCTV age README and `hybrid_low_order`;
  - Go age v1.3.2 `age.go`/`pq.go`;
  - Rust `age` 0.12.1 `src/native/`;
  - Rust `hpke` 0.14.1 `src/kem/xwing.rs`;
  - `x-wing` 0.1.0 and 0.1.1;
  - the age(1) man page and the Go age README.
- **Synthesis re-check (2026-10-06):** signed-note.md was re-read to correct C15. It defines type `0x02` (ECDSA P-256/384/521, SHOULD be P-256), and `0xff` for types without an assigned byte. `0x06` is a timestamped ML-DSA-44 *(sub)tree cosignature*, not a general signature type.
- **Reproductions:**
  - M1/M2: Go age v1.3.2 header sizes, the mixing refusal and recipient length (analyst);
  - re-run independently by skeptic 1 (2026-10-06) with the same numbers;
  - A2-S3 repeated the sizes across 4 encoders.
- **Scout conflicts resolved:**
  1. Rust `age` 0.12 has no native PQ; its `hpke` and `ml-kem` dependencies serve `tagpq` (C7).
  2. The two-stanza header is 3,184 B (measured).
  3. Device-written R (D2) vs homelab-written R (A6): reframed as DR-A2-2 with P1-E and P2′ (§F3).
- **Routes:** raw.githubusercontent.com (C2SP, CCTV, hpkewg, dconnolly, cfrg, FiloSottile, keybase, jedisct1, rclone, borgbackup, bupstash, ente, tink-crypto, cbor-wg, openpgp-pqc), proxy.golang.org, static.crates.io, index.crates.io, registry.npmjs.org, repo.maven.apache.org (kage; repo1.maven.org returned HTTP 429), developer.apple.com doc JSON.
- **Blocked sources** (reported to H1; no secondary source was substituted for a primary one):
  - c2sp.org and age-encryption.org: the raw C2SP mirror was used, without a commit hash.
  - datatracker.ietf.org, www.ietf.org and rfc-editor.org. RFC 8949, RFC 8032 and RFC 9580 were not read. Skeptic 1's web search (2026-10-06) *lists* draft-ietf-hpke-pq-04 (March 2026) and -05 (July 2026); their contents were **not read**. The hpkewg editor's copy keeps 0x647a, Nenc 1120 and Npk 1216, and now defines the KEM through draft-irtf-cfrg-concrete-hybrid-kems, which states it "is identical to the X-Wing construction". age still cites -03.
  - eprint.iacr.org and arxiv.org: the STREAM paper, the MEGA and Nextcloud papers and PURBs/Padmé were not read.
  - csrc.nist.gov (FIPS 203/204).
  - mailarchive.ietf.org: 403 from shell and EGRESS_BLOCKED for WebFetch (2026-10-06). The CFRG message on non-contributory X25519 is unread; C22 relies on the `x-wing` crate's own statement.
  - The GitHub API: restricted for this session, so age #59 could not be re-read. It is not needed (C12 rests on the spec and on A2-S4).
  - A COSE draft path returned 404, so COSE was not evaluated.
  - words.filippo.io, soatok.blog and HN.
- **Stop rule:** the last three primary reads (signed-note, `x-wing` 0.1.1 and the CCTV generator) refined the design without changing a finding. The spikes confirmed the predictions rather than adding new primary sources.

## Sources

| # | Source | Publisher | Version or date | Accessed | Primary? |
|---|---|---|---|---|---|
| S1 | age spec: `C2SP/C2SP @ main : age.md` (= c2sp.org/age) | C2SP | main head | 2026-09-29; 2026-10-06 | Yes |
| S2 | Go `filippo.io/age` v1.3.2 module (proxy.golang.org): `age.go`, `pq.go`, `cmd/age-inspect`; `@v/list` (v1.3.0 2025-12-27T14:59Z, v1.3.2 2026-08-29T17:40Z) | F. Valsorda | v1.3.2 | 2026-09-29; 2026-10-06 | Yes |
| S3 | `FiloSottile/age @ main : README.md` and `doc/age.1.ronn` (BACKWARDS COMPATIBILITY) | F. Valsorda | main | 2026-09-29 | Yes |
| S4 | CCTV age: `C2SP/CCTV @ main : age/README.md`; module `c2sp.org/CCTV/age` 2026-08-29 (4448f2097b2d) and 2026-09-25 (50a8ecf2a220) | C2SP | as stated | 2026-09-29 | Yes |
| S5 | Rust `age` 0.12.1 crate (static.crates.io; index.crates.io pubtime 2026-07-14) | str4d | 0.12.1 | 2026-09-29; 2026-10-06 | Yes |
| S6 | Rust `hpke` 0.14.1 crate: `src/kem/xwing.rs` (KEM_ID 0x647a; cites draft-ietf-hpke-pq-03 and concrete-hybrid-kems-02; `assert!` on auth mode), `Cargo.toml` (caret `x-wing = "0.1.0"`) | RustCrypto | 0.14.1 (pubtime 2026-09-06) | 2026-09-29; 2026-10-06 | Yes |
| S7 | Rust `x-wing` 0.1.0 (`Cargo.toml`: "draft 06"); `hpke-rs` 0.7.0 `src/kem.rs` (UnsupportedKemOperation for XWingDraft06 auth) | RustCrypto; Cryspen | 0.1.0; 0.7.0 | 2026-09-29 | Yes |
| S8 | draft-ietf-hpke-pq editor's copy: `hpkewg/hpke-pq @ main` | IETF HPKE WG | editor's copy; age cites -03 | 2026-09-29; 2026-10-06 | Yes |
| S9 | X-Wing draft editor's copy: `dconnolly/draft-connolly-cfrg-xwing-kem @ main` | Connolly et al. | editor's copy (2026-09-23) | 2026-09-29 | Yes |
| S10 | HPKE source markdown: `cfrg/draft-irtf-cfrg-hpke @ master` | IRTF CFRG | master | 2026-09-29 | Yes (mirror) |
| S11 | C2SP signed-note: `C2SP/C2SP @ main : signed-note.md` (signature types 0x01–0x06, 0xff) | C2SP | main head | 2026-09-29; re-read 2026-10-06 | Yes |
| S12 | typage (npm `age-encryption`) 0.3.1 | F. Valsorda | 0.3.1, 2026-08-28 | 2026-09-29 | Yes |
| S13 | Apple CryptoKit doc JSON: HPKE (iOS 17+), XWingMLKEM768X25519 (iOS 26+) | Apple | current | 2026-09-29 | Yes |
| S14 | Tink Java `HpkeParameters.java`, `StreamingAead.java`; tink-go v2.8.0 | Google | main; v2.8.0 | 2026-09-29 | Yes |
| S15 | libsodium `secretstream` docs | F. Denis | master | 2026-09-29 | Yes |
| S16 | saltpack README and `specs/saltpack_encryption_v2.md` | Keybase | master | 2026-09-29 | Yes |
| S17 | Ente web crypto `types.ts`, `libsodium.ts` | Ente | main | 2026-09-29 | Yes |
| S18 | rclone crypt docs | rclone | master | 2026-09-29 | Yes |
| S19 | bupstash technical overview | A. Chambers | master | 2026-09-29 | Yes |
| S20 | Borg `docs/internals/security.rst` | BorgBackup | master | 2026-09-29 | Yes |
| S21 | draft-ietf-openpgp-pqc editor's copy | IETF OpenPGP WG | status unverified | 2026-09-29 | Yes |
| S22 | draft-ietf-cbor-cde editor's copy | IETF CBOR WG | editor's copy | 2026-09-29 | Yes |
| S23 | GitHub issues: age #59, age #55, rage #598, restic #187, borg #1039, duplicacy #638, rclone #1712 | GitHub | via the community scout | 2026-09-29 | No (community) |
| S24 | Reliquary CE note and `spikes/content-encryption/` | this repo (T1) | 2026-09-29 | 2026-09-29 | Project evidence |
| S25 | Reliquary drafts: D2, F3 (incl. C28), D1, A1, A3, A6, B4, H4 | this repo | Wave 1 | 2026-10-06 | Project evidence (drafts) |
| S26 | Rust `x-wing` 0.1.1: `CHANGELOG.md`, `src/lib.rs` (`DecapsulationKeyRejectNonContrib`; default "accepts non-contributory behaviour" and "will be altered") | RustCrypto | 0.1.1, 2026-10-01 | 2026-10-06 | Yes |
| S27 | CCTV `testdata/hybrid_low_order` and `internal/tests/hybrid_low_order.go` | C2SP | module 2026-09-25 | 2026-10-06 | Yes |
| S28 | `cfrg/draft-irtf-cfrg-concrete-hybrid-kems @ main` (where the hpke-pq editor's copy now anchors MLKEM768-X25519), as cited by skeptic 1 | IRTF CFRG | main | 2026-10-06 (skeptic 1) | Yes |
| S29 | kage 0.8.0 (`com.github.android-password-store:kage`, repo.maven.apache.org; `MlKem768X25519Identity`/`Recipient`) | android-password-store | 0.8.0 | 2026-10-06 (spike runner) | Yes |
| M1/M2 | Analyst reproduction with Go age v1.3.2 (header sizes, mixing refusal, recipient length) | this note | 2026-09-29; 2026-10-06 | — | Measurement (synthetic) |
| SP1–SP4 | Spikes A2-S1 (CT), A2-S2, A2-S3, A2-S4 (§Spikes) | this workstream | 2026-10-06 | — | Measurement (synthetic, x86) |

## Claims

**Key?** marks the claims the skeptics reviewed (K-id in brackets). The **Verdict** column is the code-computed tally, and it is not overridden:
- **verified**: a primary source, and at least 2 of 3 skeptics did not refute;
- **secondary only**: no primary source;
- **contested**: otherwise.

"Correction applied" means the wording below has been narrowed or fixed after review; the verdict still applies to the claim as reviewed. Claims C25–C30 are new in synthesis, come from the spike runner's measurements, and were not reviewed by the skeptics.

| # | Claim | Sources | Key? | Skeptic 1 (sources) | Skeptic 2 (logic) | Skeptic 3 (adversary) | Verdict |
|---|---|---|---|---|---|---|---|
| C1 | age v1 wraps one 128-bit file key in 1–N stanzas. Header MAC = HMAC-SHA-256 under HKDF(file key, "header"). Payload key = HKDF(file key, nonce, "payload"). 64 KiB ChaCha20-Poly1305 chunks with a counter and a final flag. | S1 | No (background) | — | — | — | Not separately reviewed |
| C2 | Changing the recipient set rewrites only the header (new stanzas and MAC, which need the file key); the payload stays valid. [K10] | S1 | Yes | Upheld; rewrap ≠ revocation | Upheld; a rewrap does not re-key | Upheld; a malicious cloud keeps old copies, so nothing is revoked | **Verified**. Correction applied: "not revocation" (§F3) |
| C3 | Streaming decryption MUST fail without a valid final chunk; seeking from the end MUST verify the final chunk first. | S1 | No | — | — | — | Not separately reviewed (exercised by A2-S4 C2/C6) |
| C4 | The `mlkem768x25519` stanza is HPKE SealBase with MLKEM768-X25519 (draft-ietf-hpke-pq-03 / filippo.io/hpke-pq), HKDF-SHA256, ChaCha20Poly1305, info `age-encryption.org/mlkem768x25519`, empty aad, a 1,120-byte enc and a 32-byte body. [K1] | S1, S8 | Yes | Upheld; the editor's copy now anchors the KEM in concrete-hybrid-kems (S28) | Upheld; byte stability past -03 is open | Upheld | **Verified** |
| C5 | A file SHOULD NOT mix PQ and non-PQ recipients. Go age 1.3.2 refuses. [K2] | S1, S2, M1/M2 | Yes | Upheld; the refusal is Go-specific | Upheld; typage writes mixed headers | Upheld; only the ingest profile check enforces it | **Verified**. Correction applied: enforced at ingest (E_PROFILE), not assumed from encoders |
| C6 | Go age 1.3.2: header 1,627 B (one PQ), 3,184 B (two PQ), 168 B (X25519); PQ recipient 1,959 chars. [K3] | M1/M2, S3, SP3 | Yes | Upheld (reproduced) | Upheld; the inference "drives DR-A2-2" does not follow | Upheld | **Verified**. Correction applied: no longer used as the driver of DR-A2-2 |
| C7 | Rust `age` 0.12.1 (latest) has native `x25519`, `scrypt`, `tag` and `tagpq`; no `mlkem768x25519`. [K4] | S5 | Yes | Upheld | Upheld | Upheld | **Verified** |
| C8 | Rust `hpke` 0.14.1 implements MLKEM768-X25519 (0x647a) on RustCrypto `x-wing` ("draft 06"). [K5] (Its "interop unverified" part is superseded by C25.) | S6, S7 | Yes | Upheld; stale (interop now verified); caret dep resolves `x-wing` 0.1.1 | Upheld; same | Upheld; same; pin exactly | **Verified**. Correction applied: interop verified (C25); `x-wing` resolves to 0.1.1 in `spikes/A2-S2/Cargo.lock` (the A2-S3 README's "0.1.0" is wrong) |
| C9 | The homelab cannot verify that a device-written recovery stanza wraps the right file key, because checking a SealBase output needs skR or the encapsulation randomness. [K9] | logic (S1, S8) | Yes | Upheld; a sampled drill can catch systematic bugs | Upheld; does not rule out P2′ | Upheld; also true of a homelab-written R; deriving the randomness from the file key would allow checking | **Secondary only**. Not used as the sole support for DR-A2-2 |
| C10 | The HPKE-PQ KEMs do not support AuthEncap/AuthDecap; X-Wing is not an authenticated KEM. [K7] | S8, S9 | Yes | Upheld | Upheld | Upheld | **Verified** |
| C11 | `hpke` 0.14.1 refuses auth mode with X-Wing by **panicking** (`assert!`), not by returning an error. `hpke-rs` 0.7.0/0.8.0-pre.1 return UnsupportedKemOperation. [K7] | S6, S7, SP4 | Yes (with C10) | "errors" was wrong: panic | Same | Same | **Verified** (as K7). Correction applied: "panics" |
| C12 | age gives no sender authentication for public-key recipients; the only "expectation of authentication" is scrypt's. [K8] | S1; SP4 premise | Yes | Upheld (inference from the construction) | Upheld | Upheld | **Verified** |
| C13 | Go age ≥ 1.3.0 decrypts PQ natively; age(1) promises that files from a stable version decrypt with later versions, possibly behind a flag. [K11] | S2, S3 | Yes | Upheld; the promise covers files from the age tool, and ours only if conformant | Upheld; "30 years" is extrapolation | Upheld; a later version may refuse by default | **Verified**. Correction applied: our objects are covered only through CCTV + project-vector conformance |
| C14 | CCTV age: 147 vector files incl. 18 `hybrid_*`; Go module and npm package; decrypt direction only. | S4 | No | — | — | — | Not separately reviewed (used by A2-S3) |
| C15 | signed-note: UTF-8 text, a blank line, "— name base64(keyID‖sig)" lines. Types: 0x01 Ed25519; **0x02 ECDSA (P-256/384/521, SHOULD be P-256)**; 0x04–0x06 transparency-log cosignatures (0x06 = timestamped ML-DSA-44 tree cosignature, *not* a general signature); 0xff for types without an assigned byte. It warns PQ signatures can approach 5 kB. | S11 | No | — | (skeptic 2 flagged the original wording) | — | Not separately reviewed. Correction applied on re-read of S11 |
| C16–C20 | libsodium secretstream chains state and has no documented seek; Tink Streaming AEAD is symmetric-only; CryptoKit has X-Wing only from iOS 26; saltpack DH authentication needs a DH-capable recipient; Ente/rclone/Borg lessons. | S13–S20, S23 | No | — | — | — | Not separately reviewed |
| C21 | Header overhead ≈ 0.07 % (one stanza) / 0.14 % (two) "at F3's 0.9M–4.5M files over 2–10 TB". [K12] | C6 + F3 | Yes | **Refuted**: 0.9M–4.5M is not in F3; the percentage depends on mean size, not TB | Upheld on arithmetic; attribution wrong; no stored posture has 0.07 % | **Refuted**: circular citation; stored cost under P1 + A′ is ~0.22 % | **Contested**. Not used as support. Replaced by the per-mean-size table in §F2, which builds on F3 C28 |
| C22 | CCTV `hybrid_low_order` expects header failure for a low-order X25519 share; `hpke` 0.14.1 uses `x_wing::DecapsulationKey` (infallible, accepts non-contributory); `x-wing` 0.1.1 says CFRG will pick one behaviour. [K6] | S6, S26, S27 | Yes | Upheld; CFRG message unread | Upheld; also `hybrid_identity` | Upheld; now measured | **Verified**. Correction applied: tested in A2-S3; lax decoder fails `hybrid_low_order` **and** `hybrid_identity` |
| C23 | `hpke` 0.14.1 draws the 64-byte X-Wing encapsulation randomness from a caller-supplied `CryptoRng`; the deterministic entry point is crate-private. | S6, SP2 | No | — | — | — | Not separately reviewed; prototyped in A2-S2 (`HedgeRng` asserts exactly 64 bytes) |
| C24 | Forging an Ed25519 device signature is useful only if done before the homelab verifies it at ingest, so a classical signature is adequate for v1 *if* nothing later re-verifies device signatures as authority. [K13] | reasoning | Yes | Upheld (inference); "by the time of verification"; exercise agility before a CRQC | Upheld with a condition: a catalog rebuild, fixity or late USB ingest must not re-verify device signatures as authority | Upheld; state "verify once; persist the verdict" | **Secondary only**. Used only beside C10/C12 and with the design rule in §F4 |
| C25 | **New (SP3).** Rust (`hpke` =0.14.1, `x-wing` 0.1.1) × Go age 1.3.2 × typage 0.3.1 × kage 0.8.0, all directions, 3 key origins, 7 sizes, 1–2 stanzas: 853/853. All encoders write 1,627 / 3,184 B. CCTV: Go 147/147; Rust strict, typage and kage 85/85 applicable. The typage and kage runners check only success+hash vs throw (weaker than the Rust strict runner). 15 project vectors regenerate byte-identically and pass in all four decoders. | SP3 | — | — | — | — | New, not reviewed (measurement) |
| C26 | **New (SP1, x86 container, not a phone).** Generate/open per object: X25519 80.7/75.0 µs; PQ×1 157.4/289.4 µs; PQ×2 319.4/607.6 µs. Whole-object throughput loss of PQ×1 vs X25519 (default build): 51.9 % @16 KiB, 36.8 % @100 KiB, 14.5 % @1 MiB, 4.6 % @4 MiB, ~0 @25 MiB. The slowest PQ case is 70.9 MB/s (portable build, 16 KiB), above 12.5 MB/s. Host load 7–9. | SP1 | — | — | — | — | New, not reviewed (measurement) |
| C27 | **New (SP2).** 70 SIGKILLs (50 with one stanza, 20 with two); every object decrypts to the exact SHA-256 in Go age and Rust; at most 1 part re-encrypted per kill; no (key, nonce) reuse (wire consistency, unique nonces/MACs, 12/12 edit-after-kill refusals); 0 key hits after commit. | SP2 | — | — | — | — | New, not reviewed (measurement) |
| C28 | **New (SP4).** 26 attacks rejected with specific codes and a byte-identical store; stock Go `age -d` accepts the forged object; the record's `header_mac` string is only a pre-filter (B4, D4); the length binding and STREAM reject truncation independently. | SP4 | — | — | — | — | New, not reviewed (measurement) |
| C29 | **New (SP3).** typage 0.3.1 writes a mixed PQ+X25519 header without error; kage refuses with a misleading scrypt error. | SP3 | — | — | — | — | New, not reviewed (measurement) |
| C30 | **New (arithmetic on C6).** Header overhead as a share of stored bytes = header bytes / mean object size (table in §F2). | C6, F3 C28 | — | — | — | — | New, not reviewed; inputs measured, family mean unmeasured |

## Findings

### F1. Construction: age v1 stays (CE D-1 reaffirmed)

- **Why age.** It is the only candidate meeting all four PLAN criteria together (C1, C13, C14, C25):
  - spec stability (C2SP);
  - a conformance kit (CCTV);
  - independent implementations, now including Kotlin (kage 0.8.0, which has native PQ);
  - a stock CLI that decrypts.
- **The stock-CLI promise covers our files only if they conform** (C13 correction). That is why `object-format.md` ships encrypt-direction project vectors and CI runs CCTV + project vectors against every decoder (Duplicacy #638 lesson).
- **Lessons that still hold:**
  - chunk size is permanent (Ente);
  - a final-chunk flag is essential (rclone crypt);
  - never roll back nonce state (Borg #1039);
  - public-key encryption helps only together with append-only storage (restic #187, bupstash).

### F2. Post-quantum from day one (OD-06)

- **Threat.** Keep-forever data crosses Cloudflare and the post. A recorded X25519 wrap opens the file key to a future quantum adversary. F3 §7 extends this to device restore and sealing keys (M-40; D2 K-10).
- **Feasibility is now demonstrated, not inferred** (C4, C7, C8, C22, C25):
  - the client must write its own stanza code, since the Rust `age` crate has none;
  - the spike's code on `hpke` =0.14.1 interoperates with every reference implementation;
  - a strict decoder passes all applicable CCTV vectors.
- **Cost: bytes** (C6 **verified**; C30 arithmetic; the family mean is unmeasured, E1):

  | Configuration | Bytes per object | @ 4 MiB | @ 2.23 MB (F3-S1 photo mean) | @ 1.30 MB (corpus median) | @ 0.51 MB (F3-S1 doc mean) |
  |---|---|---|---|---|---|
  | Device transit, one stanza (P1/P1-E) | 1,627 | 0.04 % | 0.07 % | 0.13 % | 0.32 % |
  | Device transit, two stanzas (P2′) | 3,184 | 0.08 % | 0.14 % | 0.25 % | 0.63 % |
  | Stored {X, R} + kept h0 (A′) | 4,811 | 0.11 % | 0.22 % | 0.37 % | 0.95 % |
  | X25519 reference | 168 | — | — | — | — |

  - Each **unbatched** metadata record adds another full age file: 2,683 B measured, of which 1,627 B is header.
  - Batching amortizes this (§F6).
  - F3 C28 gives the extra over X25519 as 0.13–1.2 % per file with records unbatched.
  - The earlier "0.07–0.14 % at F3's 0.9M–4.5M files" (C21) is **contested** and withdrawn.
- **Cost: CPU** (C26, x86 only):
  - **Per object.** PQ adds a fixed ~77 µs per stanza to generate and ~215 µs per stanza to open.
  - **Throughput.** The relative loss is large for small objects (35–52 % at 16–100 KiB) and 5–15 % at photo sizes. It never fell below 12.5 MB/s on x86.
  - **A2-S1's rule.** "≤ 10 % loss on a low-end phone" is **not tested** (no phone). Applied per object at every size, it would already fail on x86 for small objects. Applied at the typical object size, as the kit does, it may pass. **A2 does not reinterpret the rule.** DR-A2-1 asks the owner/H1 how it aggregates (per object, at the typical size, or byte-weighted over the E1 mix).
  - A low-end phone several times slower than this host could bring small-file PQ throughput towards the uplink rate. That is an inference; it is unmeasured.
- **Tooling:**
  - heirs need Go age ≥ 1.3.0, typage, kage or `age-plugin-pq`;
  - the QR carries the trust-bundle digest, never the 1,959-character recipient (CE D-9).
- **Spec maturity:**
  - the KEM is referenced from draft-ietf-hpke-pq-03;
  - -04/-05 exist but were not read;
  - the editor's copy keeps the ID and sizes, and defers to concrete-hybrid-kems (S28);
  - CFRG has not yet fixed the X-Wing low-order behaviour (C22).

  A valid object's bytes are unaffected by the low-order question; only decoder strictness is. The age(1) promise covers files already written (C13).
- **No mixing** (C5 **verified**; C29). Mixing is not prevented by every encoder, so ingest enforces the profile (E_PROFILE, A2-S4 D1–D3). The recovery recipient must therefore be PQ: either `mlkem768x25519`, or the PQ hardware type `mlkem768p256tag` (hand-off to D2/OD-08; its stanza size was not measured).
- **Fallback if the phone cost fails:**
  1. Devices encrypt with X25519.
  2. The homelab rewraps stored headers to PQ {X, R} at ingest.
  3. Harvest-now exposure is limited to the transit copies already recorded.

### F3. Recipient set, rotation and placement

- **Rotation mechanics** (C2 **verified**). Every stanza wraps the same file key, so adding or rotating recipients is a header rewrite.
- **Rewrap is not revocation.** The file key never changes. Consequences:
  - Anyone who ever held a wrapping key, and any recorded copy carrying the old stanzas, keeps access. That includes R2 copies the cloud kept, USB sticks, and A6's kept h0.
  - **Compromise of an ingest key I_e exposes every transit copy wrapped to it, permanently.**
  - Only re-encryption under a fresh file key (with a new payload nonce) restores confidentiality for a given object.
  - Rewrap gives recipient *agility*, not recovery from a compromise.
- **Requirements that follow** (to D2/A6):
  - short I_e epochs, with the online copy destroyed at epoch end;
  - I_e kept out of homelab VM backups (D2 K-03 already says so);
  - a decision on whether A6 keeps h0 at rest. If it does, anyone who later obtains an old I_e can also open those stored objects through h0.
- **Who can check an R stanza** (C9, **secondary only**):
  - The homelab cannot verify a device-written R stanza.
  - Nobody can verify a homelab-written R stanza without skR either. A tampered config or a compromised ingest VM could point R at an attacker's key, silently, for every object.
  - Mitigations, under any placement:
    - (a) the homelab pins pkR from the **owner-signed trust bundle**, as devices do;
    - (b) a **periodic sampled recovery drill** with the real R key, or R-canary objects, is the only true check (hand-off to D2-S3 and C8).
- **Placement options (DR-A2-2).** The 3 KB rule is no longer a driver; it only appears as a cost note.

  | Option | Device writes | Stored header | Late USB bundle / long-offline upload after I_e is retired | Device cost | Unverified stanzas |
  |---|---|---|---|---|---|
  | **P1-E (recommended, provisional):** P1 plus escrow of each retired I_e, encrypted to R, kept with the store and off-box with the recovery kit | {I_e} | {X, R} by the homelab | Readable: R → escrowed I_e → object. Needs the escrow blob to survive | 1 encapsulation; 1,627 B | none on devices |
  | P1 (earlier draft): retired I_e destroyed | {I_e} | {X, R} by the homelab | **Unreadable** once I_e is destroyed. The device still has the plaintext until its receipt, unless the user has since deleted it | as P1-E | none |
  | **P2′ (alternative):** device writes {I_e, R}; the homelab rewrites stored headers to {X, R} | {I_e, R} | {X, R} by the homelab | Readable with R directly, with no escrow blob needed | 2 encapsulations; 3,184 B (+1,557 B; about +160 µs on x86; phone unmeasured) | the transit R stanza (fallback only) |
  | P2 (D2 draft under posture A): device R is the stored recovery path | {I_e, R} | {I_e, R} | Readable with R | as P2′ | **the stored** R, which is never checked |
  | P3/P3′: P2 plus the homelab recomputes the device's R stanza (disclosed randomness, or randomness derived from the file key) | {I_e, R} | as P2/P2′ | Readable with R | as P2′ | none, but custom construction; P3′ has a key-dependent-randomness question. **Crypto review required** |

- **Reasoning:**
  - P1-E and P2′ both keep the stored R homelab-written and pinned, so C9 does not separate them.
  - The real trade-off: P2′ costs every device one extra X-Wing encapsulation and 1.5 KB per object (and a second record header unless batched). It keeps transit objects self-contained for recovery.
  - P1-E keeps device cost minimal and the online I_e retention bounded to one epoch. It costs an escrow artifact that must be stored safely.
  - P1-E is **new in synthesis and not skeptic-reviewed**, so this is a provisional lean, decided with D2 and A6.
  - If phone cost (A2-S1 OL) turns out small, P2′'s simplicity may win.
- **P1 mitigation either way:**
  - On an ingest-key epoch change, the client re-seals any **un-receipted** item to the new I_e, when the source is still present (hand-off to A3/A4).
  - Bundles sealed under a retired key are opened through the escrow (P1-E) or flagged for re-upload (P1).
- **Parser:** see F5. Ingest requires *exactly* the stanza count and types that the device's trust-bundle epoch prescribes (SR-22; A2-S4 D1–D3).

### F4. Sender authentication and binding

- **A signature is needed.** age is anonymous (C12 **verified**). A2-S4 shows stock `age -d` decrypting an attacker's forged object with exit 0 (C28). Forgery resistance rests entirely on the signed record plus homelab verification (D1 SR-03, SR-04).
- **Options:**

  | Option | PQ-compatible? | Stock `age -d` still works? | Verdict |
  |---|---|---|---|
  | Device signature on a signed-note record, inside the encryption | Yes (the signature is classical, see below) | Yes | **Adopt** |
  | HPKE Auth mode | No (C10, C11 **verified**); `hpke` 0.14.1 panics | No | Reject |
  | HPKE PSK mode | Yes | No (not the age stanza) | Reject |
  | saltpack-style DH MAC keys | No (C19) | No | Reject |
  | Per-device symmetric MAC key, enrolled and wrapped to the homelab key, verified only at home (missed alternative raised by skeptics) | **Yes, PQ-secure today** | Yes | **Candidate complement** for D3. It adds enrollment state; a homelab compromise allows forgery, but that is already total compromise |
  | Outer signature visible to the cloud | Yes | Yes | Not needed |

- **Fields the signature binds:**
  - **Content:** `dedup_id` (A1 text form, with epoch), `sha256`, `size` (true, unpadded), and `padded_len` if DR-A2-4 adopts padding.
  - **Object: transport-neutral.** `h0_sha256` (SHA-256 of the device-written header bytes, including the MAC line), `header_mac`, `ct_len`, `prefix_len`, `profile`, `stanzas`. `object: null` marks a dedup hit.
    - **The R2 staging key is not signed.** It was in the earlier draft and broke the settled transport-agnostic bundles. A3 Q10 keeps one `record_id` across USB→R2 fallback, and a per-upload key would produce a different signed record.
    - The staging key or USB path maps to `h0_sha256` outside the signature (confirm with A4).
  - **Device and order:** `device_id` (must equal the signing key's registered device), `device_seq`, `record_id` (random; the idempotency key).
  - **Time:** `recorded_at` (device time, context only).
- **What actually binds the record to the object** (C28 correction). The record's `header_mac` and `h0_sha256` are **pre-filters**: an attacker can copy a MAC line. The security checks are, in order:
  1. verify the header MAC under the file key the homelab unwraps (E_OBJECT_HMAC);
  2. check the STREAM final chunk and the length (E_BINDING_LENGTH / E_STREAM_*);
  3. match SHA-256, dedup_id and size on the decrypted plaintext (E_CONTENT_MISMATCH, E_DEDUP_MISMATCH).
- **When to sign:** at sealing. Allocate `device_seq` and sign when the record first leaves the device (agrees with A3 F8).
- **Rollback of `device_seq`** (adversary skeptic). Restored app data or a disk snapshot can roll the counter back while the key survives. Honest records would then hit E_REPLAY_SEQ. Requirements for A3:
  - E_REPLAY_SEQ for a registered device must become a **visible health issue**, not a silent drop;
  - define seq-epoch recovery: the homelab returns the highest seen seq and the device jumps forward, or the device re-keys.
- **Receipts** bind `record_sha256`, the digest of the exact signed plaintext record (A3 owns the format).
- **Classical signatures for v1: design rule, not just reasoning.** C24 is **secondary only**. It holds only if:
  - the homelab verifies each device signature **once**, at ingest;
  - it persists its own **signed ingest verdict** (the receipt);
  - that verdict is the durable authority. Catalog rebuilds (A6/ADR-0013), fixity (A7), provenance and late-USB policy must never re-verify device signatures as the source of authority.

  After a cryptographically relevant quantum computer exists, an exposed long-lived classical device key could be used to forge *new* uploads. Signature agility must therefore be exercised before then: signed-note 0xff types, and trust-bundle algorithm IDs.
- **Which signature algorithm.** This is D3's call (ADR-0014). Any signed-note type registered for that device in the trust bundle is acceptable:
  - **Ed25519 (0x01)** in software, wrapped by the keystore; or
  - **ECDSA P-256 (0x02)**, which can be hardware-backed. The iOS Secure Enclave and Android StrongBox offer P-256; that is skeptic-reported and was not checked here.

  A software Ed25519 key can be exfiltrated by malware on a stolen device, which allows forging as that device until it is revoked.

### F5. Resumability, truncation, random access and decoding

- **Layout:** CE §5–§8 with prefix_len = header + 16 (1,643 / 3,200 B). Tested by A2-S2 (C27).
- **Hedging:**
  - each stanza's 64-byte X-Wing randomness comes from HKDF(seed, salt = SHA-256(plaintext), info = `reliquary/v1/hedge/xwing-encap/<i>`);
  - it is injected through a seeded RNG that **asserts exactly 64 bytes are drawn** (C23; A2-S2);
  - the header is built once and kept in the sealed state.

  This assertion couples the encoder to `hpke`'s internal RNG use, so it is another reason to pin exactly.
- **Truncation and order:** CE §5.4 (valid lengths) and §5.5 (authenticate the final chunk before serving a middle chunk). A2-S4 shows that the length binding and STREAM reject independently (C28).
- **Restore output rule (new).** age releases authenticated non-final chunks before truncation is detected (A2-S3 obs. 5). Restore tools must therefore write to a temporary file and expose it only after the final chunk and the record's SHA-256 both verify (spec §8).
- **Decoder conformance (C22 verified):**
  - every Rust decoder rejects an all-zero X25519 shared secret in the X-Wing ciphertext share, in project code (A2-S3 strict decoder; A2-S4 D4 → E_OBJECT_HEADER);
  - it must not rely on the crate default, which `x-wing` says "will be altered".
- **Dependency pinning (major skeptic issue):**
  - the client and any Rust homelab tool pin `hpke`, `x-wing` and `ml-kem` with `=`;
  - CCTV `hybrid_*` and the project vectors gate every bump (G2);
  - the spike pinned only `hpke` (`=0.14.1`), and its lock resolved `x-wing` 0.1.1 and `ml-kem` 0.3.2.
- **Panic safety:** `hpke` 0.14.1 panics on X-Wing auth mode (C11). Server code must never reach auth paths and should treat a panic in a decoder as a reject.
- **iOS (B4 K2–K4):** placement rules only; no format change.

### F6. Metadata record (provisional; follows A5)

- **Envelope.** The plaintext is a C2SP signed-note (C15): one line of I-JSON, then one signature line.
  - Records travel in **record batches**: one age file carrying N length-prefixed signed notes, to amortize the PQ header.
  - Each note stays a distinct **per-(device, file) signed unit**, so this matches ADR-0001's "encrypted metadata record per (device, file)" (logic skeptic).
- **Relation to A4 manifests.** The device signature lives on the per-(device, file) record. A4 manifests and USB bundles should **reference record digests** (`record_sha256`) rather than re-sign the same facts. A4 decides, and this note asks it to avoid two signed structures.
- **Fields v0:** H4 §6.1, plus:
  - A1's text `dedup_id` with epoch, and a reserved `chunk_list`;
  - A3's `device_seq` and `record_id`;
  - B4's `source_version`;
  - `*_raw_b64` path forms;
  - `content_encoding` (`identity` in v1);
  - `padded_len`;
  - the transport-neutral object block (§F4).
- **Evolution rules:**
  - integer `v`; an open `kind`;
  - unknown fields preserved and ignored;
  - no change of meaning within a `v`;
  - plugin `source_hints` namespaced.
- **Alternative: deterministic CBOR (CDE).** Revisit after A5 and the D2/E7 break-glass requirements. The analyst leans JSON for heir readability. Low-medium confidence.

### F7. Length hiding and compression

- **Padmé, conditional on F3-S1 (DR-A2-4):**
  - zero padding before encryption;
  - IDs and SHA-256 over the unpadded bytes;
  - every cloud-visible size padded (receipts, presence checks, SR-24, multipart layout).
- **Trade-off added in review.** Stock `age -d` then returns the file plus up to about 3.1 % trailing zeros. Recovery needs the true size from the record.
  - The adversary skeptic notes that some formats break with that much trailing data. Their example: ZIP readers look for the end-of-central-directory record only near the end of the file. That is skeptic-reported and was not checked against a primary source here.
  - If the record or its batch is lost, an heir has no true size.
  - Options: accept this, or also carry the true length somewhere recoverable without the record (to D2-S3 and E7).
- **Size buckets** are listed as an option in DR-A2-4. F3 discussed them.
- **No compression in v1.** `content_encoding` is reserved.

### Alternatives compared

| Option | Fit with settled requirements | Pros | Cons | Evidence |
|---|---|---|---|---|
| **age v1, `mlkem768x25519` only (recommended)** | Fits | Stock Go age ≥ 1.3.0, typage, kage; C2SP spec; CCTV hybrid vectors; interop verified | 1.6–3.2 KB header; own stanza code; KEM from an I-D; X-Wing low-order behaviour not yet fixed at CFRG; large relative cost for small objects | C4–C8, C13, C22, C25, C26 |
| age v1, X25519 (CE today) | Fits | 168 B header; any age version | Harvest-now on transit copies and device keys | C6; F3 §7 |
| age v1 with `mlkem768p256tag` for a hardware R (with `mlkem768x25519` elsewhere) | Fits (both PQ, so mixing is allowed) | Hardware-held recovery identity | Stanza size not measured; Rust `tagpq` is encrypt-only; hardware support unevaluated | C7; D2/OD-08 |
| age v1, mixed PQ + X25519 | — | — | SHOULD NOT; Go refuses; typage does not refuse | C5, C29 |
| HPKE base/auth + custom STREAM | Fits | Full control | No stock CLI; Auth unavailable with PQ | C10 |
| Tink Hybrid + Streaming AEAD | Fits | Google-maintained | No stock CLI; separate key wrap; X-Wing release unverified | C17 |
| libsodium sealed box + secretstream | Fits | Audited (Ente) | No PQ; no documented seek | C16 |
| saltpack | Fits | Built-in sender authentication | No PQ; DH authentication does not carry over to KEMs | C19 |
| OpenPGP RFC 9580 + PQC draft | Fits | Widespread tooling | PQC draft status unverified; not evaluated in depth | S21 |

### Similar work and lessons

| Project or paper | What they do | Borrow or avoid | Source |
|---|---|---|---|
| age / C2SP + CCTV | Spec plus a vector kit | **Borrow:** spec + encrypt-direction project vectors (done in A2-S3) | S1, S4 |
| Duplicacy #638 | Code diverged from the docs | **Avoid:** CI runs vectors on every implementation | S23 |
| Ente | Per-file keys; permanent chunk size | Chunk size is forever | S17 |
| rclone crypt | No final marker; no plaintext checksum | **Avoid** both | S18, S23 |
| bupstash, restic #187 | Put-only keys | Confirms ADR-0001 | S19, S23 |
| Borg 1 / 2 | Nonce reuse after rollback; AAD type binding | **Avoid** counters; **borrow** type/version binding | S20, S23 |
| saltpack | Sender authentication in the format | Not applicable to KEMs | S16 |

### Tools and libraries

| Name | Purpose | Licence | Maturity | Source |
|---|---|---|---|---|
| Go `filippo.io/age` + age-inspect | Homelab rewrap; heir tool; interop oracle | BSD-3-Clause (not re-checked) | v1.3.2, 2026-08-29 | S2 |
| Rust `hpke` (RustCrypto) | X-Wing stanza encode/decode in the client core | MIT/Apache-2.0 | 0.14.1; **interop verified** (C25); pre-1.0; panics on X-Wing auth | S6, SP3 |
| Rust `x-wing`, `ml-kem` | KEM building blocks | MIT/Apache-2.0 | 0.1.1 (2026-10-01), ml-kem 0.3.2; **pin exactly** | S26 |
| Rust `age` | X25519 decrypt only | MIT/Apache-2.0 | 0.12.1; no PQ | S5 |
| typage | TS age with PQ | BSD-3-Clause (not re-checked) | 0.3.1; writes mixed headers | S12, SP3 |
| kage | Kotlin age with native PQ | not checked | 0.8.0; passes CCTV (weaker runner) | S29, SP3 |
| CCTV age | Decrypt-direction conformance | README allows copying | 2026-09-25 | S4 |
| ed25519-dalek | Record signatures (spike) | not checked | as locked in the spike | — |

## Spikes

All four ran in the cloud container on synthetic data (`SYN → results`), on x86 Linux and **not on a phone**. R2 and the keystore were simulated by local files; this is emulated, not real R2. The spike code is in `spikes/A2-S2/` and is shared by all four.

| Spike | Hypothesis | Pass → / fail → (decision) | Exec tag | Budget IDs | Data class | Status | Result |
|---|---|---|---|---|---|---|---|
| A2-S1 Throughput and energy, X25519 vs PQ | Encryption is never the bottleneck vs a 100 Mbit uplink; PQ header ≤ 3 KB per object; ≤ 10 % PQ loss on a low-end phone; BUD-BAT-S recorded | Pass → PQ from day one (OD-06); fail → X25519 now plus a migration plan (§F2 fallback) | CT + OL | BUD-HASH, BUD-BAT-S | SYN → results | **CT ran; OL kit-ready.** Overall: **inconclusive** | **Header:** 1 PQ = 1,627 B (pass); 2 PQ = 3,184 B (**fail** as written); X25519 168 B; record file 2,683 B. **x86 throughput:** never below 70.9 MB/s (> 12.5 MB/s). **PQ×1 loss:** 52 % @16 KiB, 37 % @100 KiB, 15 % @1 MiB, 5 % @4 MiB (C26). **Phone loss and BUD-BAT-S: no result.** Evidence: [`spikes/A2-S1/`](../../spikes/A2-S1/README.md). Kit: [`docs/research/kits/A2-S1/`](kits/A2-S1/README.md) (`run-android.sh`, soak workload) |
| A2-S2 Kill-and-resume, 50 random kills | With PQ headers: exact SHA-256; ≤ 1 segment re-encrypted per kill; no (key, nonce) reuse; no file key survives commit | Pass → CE journaled resume in ADR-0007; fail → temp-file spool | CT | BUD-TMP | SYN → results | **Pass** | 50 kills (1 stanza, 127/127 checks) + 20 kills (2 stanzas, 63/63). Max 1 part per kill. Wire consistency; 12/12 edit-after-kill refusals; 0 key hits; no temp ciphertext. Limits: kills only in start/resume; parts of 1–4 chunks. Evidence: [`spikes/A2-S2/evidence/`](../../spikes/A2-S2/evidence/README.md) |
| A2-S3 Interop | Rust `hpke` X-Wing output ↔ Go age ≥ 1.3.0, typage, kage; 100 % CCTV + project vectors; `hybrid_low_order` predicted to fail on plain `hpke` | Pass → Rust `hpke` X-Wing in the encoder; fail → F2 fallback | CT | — | SYN → results | **Pass** | 853/853 matrix. CCTV: Go 147/147; Rust strict, typage and kage 85/85 applicable. Rust **lax** decoder fails `hybrid_low_order` and `hybrid_identity`, as predicted. 15 project vectors are deterministic and pass 15/15 everywhere. typage writes mixed headers. kage 0.8.0 has native PQ. Evidence: [`spikes/A2-S3/`](../../spikes/A2-S3/README.md) (its "x-wing 0.1.0" should read 0.1.1, per the lock file) |
| A2-S4 Forgery and truncation | A forged object + record (attacker holds only the public key) and a dropped final chunk are rejected before any catalog write, with specific codes | Pass → F4 binding set; fail → outer binding | CT | — | SYN → results | **Pass** | 30/30. Stock `age -d` accepts the forgery (exit 0). 26 attacks rejected with their own codes and an unchanged store; an honest replay is idempotent. `header_mac` in the record is only a pre-filter. Not covered: a registered device claiming another device's dedup_id with the correct sha256/size (A3/D4), and USB→R2 fallback (to add once the staging key is dropped from the record). Evidence: [`spikes/A2-S4/`](../../spikes/A2-S4/README.md) |

## Conflicts with settled text

- None that contradict CLAUDE.md, ADR-0001 or ADR-0002.
- **Avoided conflict.** The earlier draft bound the R2 staging key in the signed record. That would have broken the settled transport-agnostic bundles ("the same encrypted objects and manifest travel via R2, via USB drive…"). It is now replaced with transport-neutral fields (§F4).
- For awareness:
  - ADR-0001's "the homelab public key (e.g. X25519 / age)" admits `mlkem768x25519` and an added recovery recipient.
  - Device-signed records and homelab-signed receipts are OD-04.
  - The A2-S1 header and throughput rules are A2-local (budgets.md "Keep local"). This note does not change them, and it asks how they aggregate (DR-A2-1, DR-A2-2).

## Open questions

1. **Phone cost of X-Wing** (low-end Android; iPhone later), including small-file-heavy libraries and BUD-BAT-S. Owner: A2-S1 OL kit. Needed by Gate A.
2. **How the A2-S1 rules aggregate:** "≤ 10 % loss" (per object, at the typical size, or byte-weighted over the E1 mix) and "≤ 3 KB" (per object or per stanza). Owner: owner/H1.
3. **Recipient placement:** P1-E vs P2′ (DR-A2-2), jointly with OD-07 (A6) and OD-08 (D2). P1-E's escrow needs D2 review.
4. **Is a 128-bit age file key adequate against quantum key search** for keep-forever data? No primary source was read (NIST blocked). Owner: H1 source escalation; F3.
5. **draft-ietf-hpke-pq -04/-05 contents vs -03** for MLKEM768-X25519 bytes. Datatracker blocked. Owner: H1.
6. **CFRG's choice on non-contributory X25519 in X-Wing**, and whether it reaches age's definition. Mail archive blocked. Owner: H1, with A2 tracking before Gate A.
7. **Record encoding:** JSON-in-signed-note vs CBOR. Owner: A2, Wave 2 (after A5).
8. **Device signing-key algorithm and storage** (Ed25519 software vs P-256 hardware; symmetric MAC complement). Owner: D3.
9. **Which Tink release ships X_WING:** relevant only if ADR-0003 leaves a Rust core. kage is answered (0.8.0 has PQ). Owner: T1/B-track.
10. **Strict parser limits.** Proposed in `object-format.md`: header ≤ 16 KiB, ≤ 16 stanzas, record ≤ 1 MiB, as in the spike. Confirm in Wave 2 (G2 fuzzing).
11. **`mlkem768p256tag` for a hardware-held R:** stanza size, hardware support and Rust decrypt support. Owner: D2 (OD-08).
12. **A2-S4 gaps:** USB→R2 fallback with the same `record_id`; cross-device dedup_id claims. Owners: A2 (re-run once the record change lands), A3/D4.

## Recommendation

For the ADR-0007 draft (`docs/adr/0007-object-envelope-and-metadata-record.md`):

1. **Construction:** standard age v1 objects from the client's own encoder with CE's journaled resume (C1, C13, C25, C27).
   - Profile: only `mlkem768x25519` stanzas; no scrypt, plugin, armor or grease.
   - Use a strict multi-stanza parser.
   - Enforce the profile **at ingest**, because not every encoder does (C29).
2. **PQ from day one (OD-06): recommended**, resting on C4, C5, C6, C7, C13 (verified) and A2-S3. It is now **conditional only on the A2-S1 OL phone result**, and on the owner's reading of how the 10 % rule aggregates. If it fails, use the F2 fallback.
3. **Recipients (DR-A2-2):**
   - The format allows 1–N PQ stanzas.
   - The **homelab writes the stored {X, R}** in every recommended option, with pkR pinned from the owner-signed trust bundle and a sampled R drill.
   - The provisional lean is **P1-E** (devices write {I_e}; retired ingest keys are escrowed to R), with **P2′** as the alternative. The owner decides with OD-07 and OD-08.
   - State that rewrap is not revocation.
4. **Sender authentication:** a device signature on a signed-note record inside the encryption.
   - It binds content, the **transport-neutral** object block, device, sequence and time, and is signed at sealing.
   - Receipts bind `record_sha256`.
   - The homelab's signed verdict is the durable authority (C10, C12 verified; C24 secondary only, with that rule).
   - The algorithm is any trust-bundle-registered signed-note type (Ed25519 or P-256 per D3).
   - No HPKE Auth or PSK mode.
5. **Truncation, random access and restore:** CE §5.4/§5.5, plus restore output exposed only after full verification.
6. **Dependencies:** exact pins for `hpke`, `x-wing` and `ml-kem`; the low-order rejection in project code; CCTV + project vectors in CI on every bump.
7. **Length hiding (DR-A2-4):** Padmé (or buckets) only if F3-S1 passes. No compression in v1.
8. **Deliverables:** ADR-0007 (Proposed, partial) and `docs/spec/object-format.md` (Draft), referencing the A2-S3 project vectors until they move under `docs/spec/`.

**What would change this:**
- the phone shows PQ cost matters → F2 fallback;
- OD-07 picks a posture with no rewrap → the homelab must still add R, or P2 is accepted knowingly;
- D2 rejects the escrow → P2′;
- A5 needs binary-heavy records → CBOR;
- a later hpke-pq or CFRG revision changes the MLKEM768-X25519 bytes before Gate A → re-run A2-S3.

## Decision requests

### DR-A2-1: Post-quantum recipients from day one (this is OD-06)
- **Needed by:** Gate A (one-way door #2).
- **Evidence:** §F2; C4–C8, C13, C22 (verified); C25–C27 (spike measurements); C30 (arithmetic).
- **Options:**

  | Option | What it means for the family | Cost | Reversibility | Risks |
  |---|---|---|---|---|
  | A. PQ for all stanzas now (recommended, if the phone cost is acceptable) | Nothing visible | +1.5 KB per transit object; stored {X, R} + h0 ≈ 4.8 KB (0.1–1 % of bytes depending on mean size); x86: +77 µs per stanza per object; phone unmeasured | Moving back is possible but pointless | KEM from an I-D; X-Wing low-order behaviour still open at CFRG; pre-1.0 Rust crates |
  | B. X25519 on devices; PQ rewrap at home | Nothing visible | Smallest device cost | Stored copies upgradeable; **recorded transit copies are not** | Harvest-now on every staged object and USB stick |
  | C. Mixed PQ + X25519 | — | — | — | SHOULD NOT; Go refuses |

- **Also asked:** how A2-S1's "≤ 10 % loss on a low-end phone" aggregates. On x86 the per-object loss is already 37–52 % below 100 KiB, while at photo sizes it is 5–15 %. Choose one: per object, at the typical object size (the kit's reading), or byte-weighted over the E1 mix.
- **Recommendation:** A, once the A2-S1 OL result is in under the agreed reading; otherwise B.
- **If no decision by the deadline:** draft with A and the fallback written in. No production keys are generated before acceptance.

### DR-A2-2: Who writes the recovery stanza (H1 to number; couples OD-07, OD-08)
- **Needed by:** Gate A.
- **Evidence:** §F3; C2 (verified), C6 (verified), C9 (secondary only); D2 §F2; A6 F3.
- **Options:**

  | Option | What it means for the family | Cost | Reversibility | Risks |
  |---|---|---|---|---|
  | P1-E. Device writes {I_e}; the homelab writes {X, R}; retired I_e escrowed to R (recommended, provisional) | Nothing visible | 1,627 B device header; escrow artifacts per epoch | Can move to P2′ with a client update | New, unreviewed; the escrow must survive (keep it off-box with the recovery kit) |
  | P2′. Device writes {I_e, R}; the homelab rewrites stored headers to {X, R} | Nothing visible | 3,184 B and one more encapsulation per object (phone cost unmeasured) | Can drop R later | Transit R stanzas unverified (fallback use only) |
  | P1. As P1-E, but retired I_e destroyed | Nothing visible | Smallest | — | Late bundles after destruction are unreadable unless re-sealed or re-uploaded |
  | P2. Device R as the stored recovery path | Nothing visible | 3,184 B | — | The stored R is never verified (C9) |

- **Also asked:** is the "≤ 3 KB" rule per object or per stanza? It is a cost note here, not the driver.
- **Recommendation:** P1-E, or P2′ if D2 prefers self-contained transit objects. In every case: homelab-written stored R, pkR pinned from the trust bundle, a sampled R drill, short I_e epochs, and I_e kept out of backups.
- **If no decision by the deadline:** ADR-0007 allows 1–N PQ stanzas, and placement goes to ADR-0008/0012.

### DR-A2-3: Sender authentication by a device-signed record (refines OD-04; H1 to number)
- **Needed by:** Gate A.
- **Evidence:** §F4; C10, C11, C12 (verified); C24 (secondary only); C28.
- **Options:**

  | Option | What it means for the family | Cost | Reversibility | Risks |
  |---|---|---|---|---|
  | A. Classical signed-note signature (Ed25519 or ECDSA P-256, per D3) on the record inside the encryption; receipts bind the record digest; the homelab verdict is durable authority (recommended) | Nothing visible | Tiny | signed-note type agility | Relies on reasoning (C24) plus the verify-once rule; a software key can be exfiltrated |
  | B. A plus a per-device symmetric MAC key verified only at home | Nothing visible | Enrollment state | Removable | Adds key management (D3) |
  | C. Hybrid Ed25519 + ML-DSA now | Nothing visible | Larger records (up to ~5 kB per S11) | — | No general ML-DSA signed-note type yet (only a 0xff extension); premature |
  | D. HPKE Auth mode | — | — | — | Not available with PQ KEMs |

- **Recommendation:** A, with the verify-once design rule written into ADR-0007/0009/0013. B is worth D3's evaluation if the owner wants no reliance on C24.
- **If no decision by the deadline:** A with Ed25519.

### DR-A2-4: Length hiding (conditional on F3-S1; H1 to number)
- **Needed by:** Gate A.
- **Evidence:** §F7; F3 C7–C10; CE D-7.
- **Options:**

  | Option | What it means for the family | Cost | Reversibility | Risks |
  |---|---|---|---|---|
  | A. Padmé zero padding (if F3-S1 passes) | Heirs must trim to the true size; stock `age -d` output has trailing zeros | ≤ 3.1 % for files ≥ 64 KiB (arithmetic) | Off for new objects only | Useless unless every cloud-visible size is padded; some formats may break with trailing zeros (skeptic-reported); depends on the record surviving |
  | B. Size buckets | As A | Depends on bucket design (not computed) | As A | Coarser or finer leakage than Padmé (F3) |
  | C. No padding | None | None | Can adopt later for new objects | Exact sizes fingerprint files (AR-05) |

- **Recommendation:** A if F3-S1 passes; otherwise C, with `padded_len` reserved.
- **If no decision by the deadline:** C.

## Hand-offs

| To | What | Why |
|---|---|---|
| D2 (ADR-0008), A6 (ADR-0012/0013) | DR-A2-2. P1-E escrow of retired I_e to R (review needed); pkR pinned from the owner-signed trust bundle at the homelab; sampled R drill or R-canaries (D2-S3); short I_e epochs, I_e out of backups; decide whether to keep h0 at rest (an old I_e opens it); `mlkem768p256tag` for a hardware R | §F3 |
| A3 (ADR-0009) | Sign at sealing; receipts bind `record_sha256`; record batches of per-(device, file) signed units; padded sizes; **E_REPLAY_SEQ as a visible health issue plus seq-epoch recovery**; re-seal un-receipted items on ingest-key epoch change; the homelab's signed verdict is the durable authority | §F3, §F4 |
| A4 (ADR-0011) | The record binds `h0_sha256`, not the R2 key; the staging key or USB path maps outside the signature; manifests reference record digests rather than re-sign; same `record_id` across USB→R2 | §F4, §F6 |
| A6/A7/C8 (ADR-0013, 0029, 0032) | Never re-verify device signatures as authority in rebuilds, fixity or provenance; rely on homelab receipts | §F4 (C24) |
| D3 (ADR-0014), E5 | Signature algorithm per device (Ed25519 software vs P-256 hardware); optional symmetric MAC key; QR carries the trust-bundle digest only | §F4 |
| A8 (ADR-0028) | PQ device restore keys need a Rust X-Wing decrypt path with its own low-order check; restore output exposed only after full verification | §F5 |
| G2 (ADR-0035), G1 | Exact pins for `hpke`/`x-wing`/`ml-kem`; CCTV + project vectors on every bump; label the typage/kage CCTV runners as weaker; parser fuzzing against the spec limits | §F5, C25 |
| D2, F3 | **Correct the copied "0.9M–4.5M files" figure** (C21 contested); use F3 C28 / §F2 table | C21 |
| F3 | F3-S1 decides DR-A2-4 | §F7 |
| H1 | Blocked sources (Method); OD numbers for DR-A2-2..4; DR-A2-1 = OD-06; the A2-S1 aggregation questions | Registry owner |
| Spike runner (A2) | Fix the A2-S3 README's `x-wing` version; add a USB→R2 fallback case to A2-S4 after the record change | §Spikes |
