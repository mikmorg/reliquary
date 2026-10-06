# A2. Object envelope and metadata-record format

- **Workstream:** A2 (see `docs/research/PLAN.md`, section "A2.")
- **Status:** Final for Wave 1 (batch W1-a). This version merges the analyst deep read, the continuation pass, three skeptic reviews (sources, logic, adversary) of claims K1–K13, and spikes A2-S1 (CT part) to A2-S4. The claim verdicts are the code-computed tally and are not overridden. The metadata-record schema stays **provisional** (P1; it follows A5).
- **Date:** 2026-09-29 (last updated 2026-10-06)
- **Wave 1 scope:** the P0 **object envelope** for the ADR-0007 draft: construction, post-quantum option (OD-06), recipients, sender authentication, resumability, truncation, padding and agility.
- **Feeds:**
  - ADR-0007 draft: `docs/adr/0007-object-envelope-and-metadata-record.md` (Proposed, partial);
  - spec draft: `docs/spec/object-format.md` (Draft);
  - OD-06 (PQ);
  - evidence for OD-04 (device-signed records), OD-05 (device-key admission), OD-07 (A6 posture), OD-08 (recovery recipient) and OD-17 (accepted risks);
  - one-way door #2 (object envelope, PQ, sender authentication);
  - new decision requests DR-A2-2 to DR-A2-4 (H1 assigns OD numbers). DR-A2-1 is OD-06.
- **Depends on:**
  - **T1 spike 2**, the CE note: `docs/research/content-encryption-format.md` and `spikes/content-encryption/`. It exists. This note builds on its D-1, D-2, D-3, D-7 and D-9, §5 (byte layout), §8 (resumption) and its open issues 6 and 8.
  - Drafts: D2 (`d2-key-hierarchy-custody-recovery.md`, ADR-0008), F3 (`f3-security-literature.md`, incl. C8, C28, C31), D1 (`docs/security/threat-model.md`: SR-03, SR-04, SR-13, SR-14, SR-22, SR-24), A1, A3 (F4, F8, Q10), A6 (F3, posture A′), B4 (K2–K5) and H4 (`docs/design/data-model.md` §6.1).
- **Traceability rows advanced:** R-19 (content and metadata encrypted on the device), R-20 (devices cannot read), R-25 (locator, name and mtime only at the homelab), Q1-4 (resumable uploads vs age randomness). Touches R-18 (append-only) and R-22 (admin holds the key).

## Summary

**Every content object is a standard age v1 file, written by the client's own resumable encoder (CE design).** The recommendation is to use the native age post-quantum recipient type `mlkem768x25519` (X-Wing) for every stanza.

What the spikes show (all on x86 in a container, not on a phone):
- **Interop (A2-S3).** Stanzas written with Rust `hpke` 0.14.1 interoperate byte for byte with Go age 1.3.2, typage 0.3.1 and kage 0.8.0, in both directions: 853/853 checks.
- **Resume (A2-S2).** CE's journaled resume survives 70 random kills with a PQ header.
- **Forgery and truncation (A2-S4).** A device-signed record inside the encryption makes ingest reject 26/26 forgery, truncation and downgrade attacks before any catalog write. That run used the earlier record layout, which signed the R2 staging key, so it has to be repeated for the final layout (see Spikes).

The main open question for OD-06 is **phone cost**. PQ adds a fixed cost to every object. On x86 that costs 35–52 % throughput on 16–100 KiB objects and 5–15 % at photo sizes. The phone figure needs the A2-S1 OL kit.

Changes in this final pass, after the skeptics:
1. **Ingest key escrow at creation.** Each ingest key I_e is escrowed to {X, R} when it is created and copied off the homelab before devices may use it. Escrowing only at retirement would leave transit data unreadable if the homelab were lost mid-epoch. ADR-0008 (revised 2026-10-06) now escrows at creation; A2 adds the "off-box before publication" ordering.
2. **Exact header match is a security check.** Ingest requires the object header to equal the signed `h0_sha256` exactly. This is the only check that catches someone who knows the file key and re-wraps the header.
3. **Exact stanza count.** The profile requires exactly the number of stanzas the device's epoch prescribes, which closes a covert exfiltration channel.
4. **Device keys must be admitted through a path the cloud cannot forge** (SR-14 / OD-05). Otherwise a malicious cloud can enroll a rogue device whose signatures verify.
5. **Classical device signatures are an owner risk acceptance, not a verified finding.** The adequacy argument is **contested** (C24). The format therefore carries signature agility from day one, with a dated review trigger.
6. **Two-layer conformance.** An age decoder that passes CCTV, plus a separate Reliquary profile validator.

**Confidence:**

| Area | Confidence |
|---|---|
| Spec and source facts; interop | High (verified claims; A2-S3) |
| PQ from day one | Medium-high, pending phone cost (A2-S1 OL) |
| Recipient placement (P1 + escrow at creation) | Medium-high (agrees with ADR-0008 Decision 1 as revised 2026-10-06; couples to OD-07 and OD-08) |
| Sender authentication architecture | High (C10–C12 verified; A2-S4) |
| Classical signature adequacy for v1 | Low (C24 contested); handled as a risk acceptance |
| Record encoding | Low-medium (provisional) |

## Questions

| # | Question (PLAN A2) | Short answer | Confidence |
|---|---|---|---|
| 1 | Which construction? | **age v1 (C2SP)**, as in CE D-1. It is the only candidate that has all four: a public spec, a conformance kit (CCTV), independent Go/Rust/TS/Kotlin implementations, and a stock CLI with a written backwards-compatibility promise (C1, C13, C14; A2-S3). | High |
| 2 | Post-quantum from day one? Header size and phone cost? | **Yes, `mlkem768x25519` for all stanzas (OD-06), if the A2-S1 OL kit shows acceptable phone cost.** Header sizes: one stanza 1,627 B, two 3,184 B, X25519 168 B (C6, **verified**). Rust↔Go/typage/kage interop is shown (C25, A2-S3). x86 cost: about +77 µs per stanza to generate and +215 µs to open; throughput loss vs X25519 is 52 % at 16 KiB, 37 % at 100 KiB, 15 % at 1 MiB and 5 % at 4 MiB (C26). Phone cost: **no result** (kit-ready). | Medium-high (recommendation); High (sizes, interop); none (phone) |
| 3 | Recipient set; rotation by rewrap only | All stanzas PQ; no mixing (C5). Changing recipients is a header rewrite (C2, **verified**). **Rewrap is not revocation** (§F3). Placement: devices write {I_e} only; the homelab writes the stored {X, R}; each I_e is escrowed to R **at creation** (DR-A2-2). | High (mechanics); Medium (placement) |
| 4 | Sender authentication | **A device signature on the record, inside the encryption.** HPKE Auth mode does not exist for PQ KEMs (C10, C11, **verified**). age authenticates no sender (C12, **verified**; A2-S4 premise). The signature is meaningful only if the homelab admits device keys through a path the cloud cannot forge (SR-14, OD-05). Whether a classical signature is enough for v1 is **contested** (C24). | High (architecture); Low (classical adequacy) |
| 5 | Resumability | **CE mechanism, tested with PQ.** prefix_len is 1,643 B (one stanza) or 3,200 B (two). A2-S2 passed: at most one part re-encrypted per kill, no (key, nonce) reuse, no key survives commit, no temp ciphertext spool (C27). The X-Wing randomness comes from the same hedge derivation as the file key (C23). | High |
| 6 | Truncation, reordering, random access | age STREAM, plus CE §5.4 and §5.5. A2-S4 showed two independent layers (C28). Restore output is exposed only after the final chunk and the record's SHA-256 verify. | High |
| 7 | Length hiding; zstd | **Padmé zero padding**, provisionally, following F3 (F3-S1 passed at per-device scale and was mixed at family scale). Every cloud-visible size is padded. The overhead bound depends on size class (§F7). No compression in v1; `content_encoding` is reserved. | Medium |
| 8 | Metadata-record fields and encoding | **Provisional:** a C2SP signed-note whose text is one line of I-JSON. Records travel in batches of per-(device, file) signed units. Deterministic CBOR (CDE) is the main alternative. Revisit after A5. | Low-medium |
| 9 | Algorithm agility and migration | Stanza-level agility: a new recipient type needs only a rewrap. The payload suite is fixed by age v1; replacing it means re-encryption, about 28 h per 10 TB at 100 MB/s (arithmetic). Signature agility comes from signed-note types (0x01 Ed25519, 0x02 ECDSA, 0xff for new types such as a hybrid or PQ signature). | Medium |
| 10 | (new) Can the homelab verify a device-written recovery stanza? | **No**, without skR or the encapsulation randomness (C9, **secondary only**: logic). A homelab-written R stanza cannot be verified without skR either. Only a sampled recovery drill with the real R key checks R stanzas, under any placement. | Medium-high (logic) |
| 11 | (new) Is there a drop-in Rust PQ age implementation? | **No.** `age` 0.12.1 has no `mlkem768x25519` (C7, **verified**). The spike's own stanza code on `hpke` 0.14.1 works (A2-S3). | High |
| 12 | (new) Is X-Wing behaviour stable across implementations? | **Not fully.** A decoder on plain `hpke` 0.14.1 accepts low-order shares and fails CCTV `hybrid_low_order` and `hybrid_identity` (C22, **verified**; A2-S3). `x-wing` says its default key type "will be altered" once the RFC is published. Pin exact versions and keep the rejection in project code. As of draft-ietf-hpke-pq-05 (6 July 2026), the code point and sizes are unchanged (C32). | High |

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
- **Synthesis checks (2026-10-06):**
  - `signed-note.md` re-read to correct C15.
  - **draft-ietf-hpke-pq-05 read** from the gh-pages mirror (S30), as skeptic 1 suggested. It is dated 6 July 2026; its page header reads "draft-ietf-hpke-pq-latest" inside the `-05` directory. Table 3 keeps 0x647a MLKEM768-X25519 with Nenc 1,120, Npk 1,216, Nsk 32 and Auth "no", and refers to concrete-hybrid-kems-03. The -03 and -04 texts are not on the mirror (404), so the A.5 test vectors were not compared with -03.
  - The A2-S2 spike source (`src/main.rs`) was read to check which fields the A2-S4 record signed. It signs `object.key` (the R2 staging key), `header_mac`, `ct_len`, `prefix_len`, `profile` and `stanzas`, and no `h0_sha256`.
  - The CCTV `hybrid_*` expectations were read from `spikes/A2-S3/evidence/cctv/rust-strict.jsonl` to build the profile-rejection list in `object-format.md`.
- **New measurement M3** (synthesizer, 2026-10-06; Go age v1.3.2 built with toolchain go1.25.0; a key pair from `filippo.io/hpke` v0.4.0 `MLKEM768P256().GenerateKey()` wrapped with `tag.NewHybridRecipient`). Header length = file length − 32 B (16 B nonce + 16 B empty final chunk), which reproduces 1,627 B for one X-Wing stanza. Results:
  - one `mlkem768p256tag` stanza: **1,679 B**;
  - {`mlkem768x25519`, `mlkem768p256tag`}: **3,236 B**, accepted by Go age (both are PQ) and decryptable with the X-Wing identity;
  - `age1tagpq1…` recipient: **2,015 characters**;
  - `mlkem768p256tag` + X25519: refused ("can't mix post-quantum and classic recipients").

  The program was a 50-line throwaway in the scratchpad and is not kept in the repo. It answers skeptic 1's "unmeasured" note on the hardware recovery option.
- **Reproductions:** M1/M2 (Go age v1.3.2 header sizes, mixing refusal, recipient length) by the analyst; repeated independently by skeptics 1, 2 and 3 on 2026-10-06 with the same numbers; A2-S3 repeated the sizes across 4 encoders.
- **Routes:** raw.githubusercontent.com (C2SP, CCTV, hpkewg incl. gh-pages, dconnolly, cfrg, FiloSottile, keybase, jedisct1, rclone, borgbackup, bupstash, ente, tink-crypto, cbor-wg, openpgp-pqc), proxy.golang.org, static.crates.io, index.crates.io, registry.npmjs.org, repo.maven.apache.org (kage; repo1.maven.org returned HTTP 429), developer.apple.com doc JSON.
- **Blocked sources** (reported to H1; no secondary source was substituted for a primary one):
  - c2sp.org and age-encryption.org: the raw C2SP mirror was used, without a commit hash.
  - datatracker.ietf.org, www.ietf.org and rfc-editor.org. RFC 8949, RFC 8032 and RFC 9580 were not read. hpke-pq -05 was read through the gh-pages mirror instead (S30); -04 was not read.
  - eprint.iacr.org and arxiv.org: the STREAM paper, the MEGA and Nextcloud papers and PURBs/Padmé were not read. The Padmé bounds used here come from F3's verified C8 (reference code).
  - csrc.nist.gov and nvlpubs.nist.gov (FIPS 203/204; **NIST IR 8547**). Both returned CONNECT 403 from the shell on 2026-10-06. The IR 8547 dates quoted in §F4 are skeptic-reported from a secondary summary and are **unverified**.
  - mailarchive.ietf.org: 403 from the shell and EGRESS_BLOCKED for WebFetch (2026-10-06). The CFRG message on non-contributory X25519 is unread; C22 relies on the `x-wing` crate's own statement.
  - The GitHub API: restricted for this session, so age #59 was not re-read. C12 does not rest on it.
  - A COSE draft path returned 404, so COSE was not evaluated.
  - words.filippo.io, soatok.blog and HN.
- **Stop rule:** the last four primary reads (signed-note, `x-wing` 0.1.1, the CCTV generator, hpke-pq -05) refined the design without changing a finding. The spikes confirmed the predictions rather than adding new primary sources.

## Sources

| # | Source | Publisher | Version or date | Accessed | Primary? |
|---|---|---|---|---|---|
| S1 | age spec: `C2SP/C2SP @ main : age.md` (= c2sp.org/age) | C2SP | main head | 2026-09-29; 2026-10-06 | Yes |
| S2 | Go `filippo.io/age` v1.3.2 module (proxy.golang.org): `age.go`, `pq.go`, `tag/tag.go`, `cmd/age-inspect`; `@v/list` (v1.3.0 2025-12-27T14:59Z, v1.3.2 2026-08-29T17:40Z) | F. Valsorda | v1.3.2 | 2026-09-29; 2026-10-06 | Yes |
| S3 | `FiloSottile/age @ main : README.md` and `doc/age.1.ronn` (BACKWARDS COMPATIBILITY) | F. Valsorda | main | 2026-09-29 | Yes |
| S4 | CCTV age: `C2SP/CCTV @ main : age/README.md`; module `c2sp.org/CCTV/age` 2026-08-29 (4448f2097b2d) and 2026-09-25 (50a8ecf2a220) | C2SP | as stated | 2026-09-29 | Yes |
| S5 | Rust `age` 0.12.1 crate (static.crates.io; index.crates.io pubtime 2026-07-14) | str4d | 0.12.1 | 2026-09-29; 2026-10-06 | Yes |
| S6 | Rust `hpke` 0.14.1 crate: `src/kem/xwing.rs` (KEM_ID 0x647a; cites draft-ietf-hpke-pq-03 and concrete-hybrid-kems-02; `assert!` on auth mode), `Cargo.toml` (caret `x-wing = "0.1.0"`); README (says draft-connolly-cfrg-xwing-kem-10) | RustCrypto | 0.14.1 (pubtime 2026-09-06) | 2026-09-29; 2026-10-06 | Yes |
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
| S23 | GitHub issues: age #59, age #55, rage #598, restic #187, borg #1039, duplicacy #638, rclone #1712 | GitHub | via the community scout | 2026-09-29 | No (community; age #59 is a 2019 user request, context only) |
| S24 | Reliquary CE note and `spikes/content-encryption/` | this repo (T1) | 2026-09-29 | 2026-09-29 | Project evidence |
| S25 | Reliquary drafts: D2 + ADR-0008, F3 (incl. C8, C28, C31), D1, A1, A3, A6, B4, H4 | this repo | Wave 1 | 2026-10-06 | Project evidence (drafts) |
| S26 | Rust `x-wing` 0.1.1: `CHANGELOG.md`, `src/lib.rs` (`DecapsulationKeyRejectNonContrib`; default "accepts non-contributory behaviour" and "will be altered") | RustCrypto | 0.1.1, 2026-10-01 | 2026-10-06 | Yes |
| S27 | CCTV `testdata/hybrid_low_order` and `internal/tests/hybrid_low_order.go` | C2SP | module 2026-09-25 | 2026-10-06 | Yes |
| S28 | `cfrg/draft-irtf-cfrg-concrete-hybrid-kems @ main` (where the hpke-pq editor's copy anchors MLKEM768-X25519), as cited by skeptic 1 | IRTF CFRG | main | 2026-10-06 (skeptic 1) | Yes |
| S29 | kage 0.8.0 (`com.github.android-password-store:kage`, repo.maven.apache.org; `MlKem768X25519Identity`/`Recipient`) | android-password-store | 0.8.0 | 2026-10-06 (spike runner) | Yes |
| S30 | draft-ietf-hpke-pq-05: `hpkewg/hpke-pq @ gh-pages : draft-ietf-hpke-pq-05/draft-ietf-hpke-pq.txt` (§4, §"Asymmetric-Key-Authenticated Modes", §8.2 Table 3) | IETF HPKE WG | 6 July 2026 (expires 7 January 2027) | 2026-10-06 | Yes (mirror) |
| S31 | NIST IR 8547 (ipd), Transition to PQC Standards | NIST | draft | **blocked** 2026-10-06 | Primary not read; dates skeptic-reported from a secondary summary (postquantum.com) |
| M1/M2 | Analyst reproduction with Go age v1.3.2 (header sizes, mixing refusal, recipient length) | this note | 2026-09-29; 2026-10-06 | — | Measurement (synthetic) |
| M3 | Synthesizer measurement with Go age v1.3.2: `mlkem768p256tag` header and recipient sizes (Method) | this note | 2026-10-06 | — | Measurement (synthetic) |
| SP1–SP4 | Spikes A2-S1 (CT), A2-S2, A2-S3, A2-S4 (§Spikes) | this workstream | 2026-10-06 | — | Measurement (synthetic, x86) |

## Claims

**Key?** marks the claims the skeptics reviewed (K-id in brackets). The **Verdict** column is the code-computed tally and is not overridden:
- **verified**: a primary source, and at least 2 of 3 skeptics did not refute;
- **secondary only**: no primary source;
- **contested**: otherwise.

"Correction applied" means the wording below was narrowed or fixed after review; the verdict still applies to the claim as reviewed. Claims C25–C32 are new in synthesis, come from measurements or the synthesizer's own reads, and were not reviewed by the skeptics.

| # | Claim | Sources | Key? | Skeptic 1 (sources) | Skeptic 2 (logic) | Skeptic 3 (adversary) | Verdict |
|---|---|---|---|---|---|---|---|
| C1 | age v1 wraps one 128-bit file key in 1–N stanzas. Header MAC = HMAC-SHA-256 under HKDF(file key, "header"). Payload key = HKDF(file key, nonce, "payload"). 64 KiB ChaCha20-Poly1305 chunks with a counter and a final flag. | S1 | No (background) | — | — | — | Not separately reviewed |
| C2 | Changing the recipient set rewrites only the header (new stanzas and MAC, which need the file key); the payload stays valid. [K10] | S1 | Yes | Upheld; rewrap is not revocation | Upheld; a rewrap needs an existing identity, and under an X25519 fallback a recorded transit stanza opens the "upgraded" stored copy | Upheld; a malicious cloud keeps old copies | **Verified**. Correction applied: "not revocation" (§F3); fallback consequence (§F2) |
| C3 | Streaming decryption MUST fail without a valid final chunk; seeking from the end MUST verify the final chunk first. | S1 | No | — | — | — | Not separately reviewed (exercised by A2-S4 C1–C8) |
| C4 | The `mlkem768x25519` stanza is HPKE SealBase with MLKEM768-X25519 (draft-ietf-hpke-pq-03 / filippo.io/hpke-pq), HKDF-SHA256, ChaCha20Poly1305, info `age-encryption.org/mlkem768x25519`, empty aad, a 1,120-byte enc and a 32-byte body. [K1] | S1, S8, S30 | Yes | Upheld; -05 keeps 0x647a, Nenc 1,120, Auth no | Upheld; the KEM is anchored to an I-D | Upheld; a later revision could change bytes | **Verified** |
| C5 | A file SHOULD NOT mix PQ and non-PQ recipients. Go age 1.3.2 refuses. [K2] | S1, S2, M1/M2 | Yes | Upheld; the refusal is Go-specific; CCTV `hybrid_and_x25519` expects decoders to *succeed* | Upheld; "forces R to be PQ" is a project rule | Upheld; only the ingest profile enforces it | **Verified**. Correction applied: an ingest profile rule, not a property of the format |
| C6 | Go age 1.3.2: header 1,627 B (one PQ), 3,184 B (two PQ), 168 B (X25519); PQ recipient 1,959 chars. [K3] | M1/M2, S3, SP3 | Yes | Upheld (reproduced) | Upheld; "drives DR-A2-2" does not follow | Upheld (reproduced) | **Verified**. Correction applied: not used as the driver of DR-A2-2 |
| C7 | Rust `age` 0.12.1 (latest) has native `x25519`, `scrypt`, `tag` and `tagpq`; no `mlkem768x25519`. [K4] | S5 | Yes | Upheld | Upheld | Upheld | **Verified** |
| C8 | Rust `hpke` 0.14.1 implements MLKEM768-X25519 (0x647a) on RustCrypto `x-wing` ("draft 06"). [K5] | S6, S7 | Yes | Upheld; "interop unverified" is stale; caret dep resolves `x-wing` 0.1.1; hpke README says xwing-kem-10 | Upheld; a later 0.1.x could change decoder behaviour, so pin exactly | Upheld; pin exactly | **Verified**. Correction applied: interop shown (C25); labels inconsistent, so the KEM is defined by the C2SP spec plus vectors, with the tested crate set recorded |
| C9 | The homelab cannot verify that a device-written recovery stanza wraps the right file key, because checking a SealBase output needs skR or the encapsulation randomness. [K9] | logic (S1, S8) | Yes | Upheld; deriving the randomness from homelab-known material would allow checking | Upheld; also true of a homelab-written R; the real difference is the trust boundary | Upheld; it also means an attacker-key stanza cannot be told from a genuine R | **Secondary only**. Not the sole support of any recommendation |
| C10 | The HPKE-PQ KEMs do not support AuthEncap/AuthDecap; X-Wing is not an authenticated KEM. [K7] | S8, S9, S30 | Yes | Upheld; -05 says the same; the draft names PSK or signatures as alternatives | Upheld | Upheld | **Verified** |
| C11 | `hpke` 0.14.1 refuses auth mode with X-Wing by **panicking** (`assert!`), not by returning an error. `hpke-rs` 0.7.0 returns UnsupportedKemOperation. [K7] | S6, S7, SP4 | Yes (with C10) | "refuse" only if a panic counts | Same | Same | **Verified** (as K7). Correction applied: "panics" |
| C12 | age gives no sender authentication for public-key recipients; the only "expectation of authentication" is scrypt's. [K8] | S1; SP4 premise | Yes | Upheld; age #59 is secondary context only | Upheld (inference plus demonstration) | Upheld | **Verified**. Correction applied: supported by the construction and A2-S4, not by #59 |
| C13 | Go age ≥ 1.3.0 decrypts PQ natively; age(1) promises that files from a stable version decrypt with later versions, possibly behind a flag. [K11] | S2, S3 | Yes | Upheld; the promise covers files from the age tool | Upheld; "30 years" is extrapolation; with padding, `age -d` returns trailing zeros | Upheld | **Verified**. Correction applied: our objects are covered only through CCTV + project-vector conformance |
| C14 | CCTV age: 147 vector files incl. 18 `hybrid_*`; Go module and npm package; decrypt direction only. | S4 | No | — | — | — | Not separately reviewed (used by A2-S3) |
| C15 | signed-note: UTF-8 text, a blank line, "— name base64(keyID‖sig)" lines. Types: 0x01 Ed25519; 0x02 ECDSA (P-256/384/521, SHOULD be P-256); 0x04–0x06 transparency-log cosignatures (0x06 = timestamped ML-DSA-44 tree cosignature, *not* a general signature); 0xff for types without an assigned byte. It warns PQ signatures can approach 5 kB. | S11 | No | — | — | — | Not separately reviewed. Corrected on re-read of S11 |
| C16–C20 | libsodium secretstream chains state and has no documented seek; Tink Streaming AEAD is symmetric-only; CryptoKit has X-Wing only from iOS 26; saltpack DH authentication needs a DH-capable recipient; Ente/rclone/Borg lessons. | S13–S20, S23 | No | — | — | — | Not separately reviewed |
| C21 | Header overhead ≈ 0.07 % (one stanza) / 0.14 % (two) "at F3's 0.9M–4.5M files over 2–10 TB". [K12] | C6 + F3 | Yes | **Refuted**: the figure *is* in F3 (§2), but it is derived from the same assumed mean, so the citation is circular; wrong stored posture | **Refuted**: the count adds nothing; it counts photos at the Open Images mean, not family files; omits records and stored {X, R} + h0 | **Refuted**: understates stored cost several-fold (~0.22 % at the photo mean, ~0.95 % at the document mean) | **Contested**. Not used as support. Replaced by the per-mean-size table in §F2 |
| C22 | CCTV `hybrid_low_order` expects header failure for a low-order X25519 share; `hpke` 0.14.1 uses `x_wing::DecapsulationKey` (infallible, accepts non-contributory); `x-wing` 0.1.1 says CFRG will pick one behaviour. [K6] | S6, S26, S27 | Yes | Upheld; CFRG message unread | Upheld; now measured, also `hybrid_identity` | Upheld; now measured | **Verified**. Correction applied: tested in A2-S3 |
| C23 | `hpke` 0.14.1 draws the 64-byte X-Wing encapsulation randomness from a caller-supplied `CryptoRng`; the deterministic entry point is crate-private. | S6, SP2 | No | — | — | — | Not separately reviewed; prototyped in A2-S2 (`HedgeRng` asserts exactly 64 bytes) |
| C24 | Forging an Ed25519 device signature requires a quantum computer at verification time, and the homelab verifies at ingest, so classical signatures are adequate for v1 sender authentication (inference). [K13] | reasoning | Yes | **Refuted**: no primary source; once a CRQC exists, an exposed key allows forging *new* uploads at any later ingest; NIST IR 8547 timeline not considered | **Refuted**: a forgery needs a CRQC when it is made, not at verification; adequacy needs verify-once, agility before a CRQC, and device public keys not exposed; key exfiltration is the realistic classical path | Upheld only in a narrowed form (verify once, persist the verdict, rotate to PQ/hybrid before a CRQC) | **Contested**. Not the sole support of anything; handled as an owner risk acceptance (DR-A2-3) |
| C25 | **New (SP3).** Rust (`hpke` =0.14.1, `x-wing` 0.1.1, `ml-kem` 0.3.2) × Go age 1.3.2 × typage 0.3.1 × kage 0.8.0, all directions, 3 key origins, 7 sizes, 1–2 stanzas: 853/853. All encoders write 1,627 / 3,184 B. CCTV: Go 147/147; Rust strict, typage and kage 85/85 applicable. The typage and kage runners check only success+hash vs throw. 15 project vectors regenerate byte-identically and pass in all four decoders. | SP3 | — | — | — | — | New, not reviewed (measurement) |
| C26 | **New (SP1, x86 container, not a phone).** Generate/open per object: X25519 80.7/75.0 µs; PQ×1 157.4/289.4 µs; PQ×2 319.4/607.6 µs. Whole-object throughput loss of PQ×1 vs X25519 (default build): 51.9 % @16 KiB, 36.8 % @100 KiB, 14.5 % @1 MiB, 4.6 % @4 MiB, ~0 @25 MiB. The slowest PQ case is 70.9 MB/s (portable build, 16 KiB). Host load 7–9. | SP1 | — | — | — | — | New, not reviewed (measurement) |
| C27 | **New (SP2).** 70 SIGKILLs (50 with one stanza, 20 with two); every object decrypts to the exact SHA-256 in Go age and Rust; at most 1 part re-encrypted per kill; no (key, nonce) reuse; 12/12 edit-after-kill refusals; 0 key hits after commit. | SP2 | — | — | — | — | New, not reviewed (measurement) |
| C28 | **New (SP4).** 26 attacks rejected with specific codes and a byte-identical store; stock Go `age -d` accepts the forged object; the length binding and STREAM reject truncation independently. The record signed the R2 staging key and `header_mac`, not `h0_sha256`. | SP4; spike source | — | — | — | — | New, not reviewed (measurement) |
| C29 | **New (SP3).** typage 0.3.1 writes a mixed PQ+X25519 header without error; kage refuses with a misleading scrypt error. | SP3 | — | — | — | — | New, not reviewed (measurement) |
| C30 | **New (arithmetic on C6).** Header overhead as a share of stored bytes = header bytes / mean object size (table in §F2). | C6, F3 C28 | — | — | — | — | New, not reviewed; family mean unmeasured |
| C31 | **New (M3).** Go age 1.3.2: one `mlkem768p256tag` stanza gives a 1,679 B header; {`mlkem768x25519`, `mlkem768p256tag`} gives 3,236 B and is accepted (both PQ); the `age1tagpq1` recipient is 2,015 chars; tagpq + X25519 is refused. | M3, S2 | — | — | — | — | New, not reviewed (measurement) |
| C32 | **New (S30).** draft-ietf-hpke-pq-05 (6 July 2026) keeps 0x647a MLKEM768-X25519 with Nenc 1,120, Npk 1,216, Nsk 32 and Auth "no", and says these KEMs do not support AuthEncap/AuthDecap. Byte equality of its test vectors with -03 was not checked. | S30 | — | — | — | — | New, not reviewed (synthesizer read) |

## Findings

### F1. Construction: age v1 stays (CE D-1 reaffirmed)

- **Why age.** It is the only candidate meeting all four PLAN criteria together (C1, C13, C14, C25):
  - spec stability (C2SP);
  - a conformance kit (CCTV);
  - independent implementations, now including Kotlin (kage 0.8.0, which has native PQ);
  - a stock CLI that decrypts.
- **The stock-CLI promise covers our files only if they conform** (C13 correction). So `object-format.md` ships encrypt-direction project vectors, and CI runs CCTV plus the project vectors against every decoder (Duplicacy #638 lesson).
- **What heirs can rely on** (logic skeptic). Today, stock age ≥ 1.3.0 reads our objects. In future it will as long as CCTV and project-vector conformance holds. Heirs also need the record (true size, names). The "30 years" wording in PLAN is a goal; the D2-S3 drill tests it.
- **Lessons that still hold:**
  - chunk size is permanent (Ente);
  - a final-chunk flag is essential (rclone crypt);
  - never roll back nonce state (Borg #1039);
  - public-key encryption helps only together with append-only storage (restic #187, bupstash).

### F2. Post-quantum from day one (OD-06)

- **Threat.** Keep-forever data crosses Cloudflare and the post. A recorded X25519 wrap opens the file key to a future quantum adversary. F3 §7 extends this to device restore and sealing keys (M-40; D2 K-10).
- **Feasibility is demonstrated** (C4, C7, C8, C22, C25):
  - the client writes its own stanza code, since the Rust `age` crate has none;
  - the spike's code on `hpke` =0.14.1 interoperates with every reference implementation;
  - a strict decoder passes all applicable CCTV vectors.
- **Cost: bytes** (C6 **verified**; C30 arithmetic; the family mean is unmeasured, E1):

  | Configuration | Bytes per object | @ 4 MiB | @ 2.23 MB (F3-S1 photo mean) | @ 1.30 MB (corpus median) | @ 0.51 MB (F3-S1 doc mean) |
  |---|---|---|---|---|---|
  | Device transit, one stanza (P1) | 1,627 | 0.04 % | 0.07 % | 0.13 % | 0.32 % |
  | Device transit, two stanzas (P2′) | 3,184 | 0.08 % | 0.14 % | 0.25 % | 0.63 % |
  | Stored {X, R} + kept h0 (A′) | 4,811 | 0.11 % | 0.22 % | 0.37 % | 0.95 % |
  | X25519 reference | 168 | — | — | — | — |

  - Each **unbatched** metadata record adds another full age file: 2,683 B measured, of which 1,627 B is header. Batching amortizes it (§F6).
  - F3 C28 gives the extra over X25519 as 0.13–1.2 % per file with records unbatched.
  - The earlier "0.07–0.14 % at F3's 0.9M–4.5M files" (C21) is **contested** and withdrawn. The reason is not a missing source: F3 §2 does say "2–10 TB is roughly 0.9–4.5M photos at the Open Images mean". The problems are that the count is derived from the same mean (circular), it counts public-dataset photos rather than family files, and it ignores records and the stored posture.
- **Cost: CPU** (C26, x86 only):
  - **Per object.** PQ adds a fixed ~77 µs per stanza to generate and ~215 µs per stanza to open.
  - **Throughput.** The relative loss is large for small objects (35–52 % at 16–100 KiB) and 5–15 % at photo sizes. It never fell below 12.5 MB/s on x86.
  - **A2-S1's rule** ("≤ 10 % loss on a low-end phone") is **not tested** (no phone). Applied per object at every size, it would already fail on x86 for small objects. Applied at the typical object size, as the kit does, it may pass. **A2 does not reinterpret the rule**; DR-A2-1 asks the owner/H1 how it aggregates.
  - A low-end phone several times slower than this host could bring small-file PQ throughput towards the uplink rate. That is an inference; it is unmeasured.
  - If small files dominate the phone cost, one option is to pack many small files into one age object (restic/Borg style). That keeps stock-CLI recovery but changes the object model (A1/A4), so it is listed as an alternative, not recommended (adversary skeptic).
- **Tooling:** heirs need Go age ≥ 1.3.0, typage, kage or `age-plugin-pq`. The QR carries the trust-bundle digest, never the 1,959-character recipient (CE D-9).
- **Spec maturity:**
  - the KEM is referenced from draft-ietf-hpke-pq-03; -05 (6 July 2026) keeps the code point, sizes and "no Auth" (C32), and the editor's copy anchors the KEM in concrete-hybrid-kems (S28);
  - CFRG has not yet fixed the X-Wing low-order behaviour (C22);
  - the crate labels disagree (`hpke` README says xwing-kem-10; `x-wing` says draft 06). So ADR-0007 defines the KEM **by the C2SP age spec plus CCTV and project vectors**, and records the tested crate set (`hpke` =0.14.1, `x-wing` =0.1.1, `ml-kem` =0.3.2).

  A valid object's bytes are unaffected by the low-order question; only decoder strictness is.
- **No mixing** (C5 **verified**; C29). Not every encoder prevents mixing, so ingest enforces the profile (E_PROFILE, A2-S4 D1–D3). The recovery recipient must therefore be PQ: `mlkem768x25519`, or the PQ hardware type `mlkem768p256tag`. Its header is now measured: 1,679 B alone, 3,236 B together with one X-Wing stanza, and Go age accepts that pair (C31).
- **Fallback if the phone cost fails (option B):** devices encrypt with X25519, and the homelab writes PQ {X, R} for storage. **State the exposure plainly** (logic skeptic): every object uploaded under B is exposed to anyone who recorded its transit copy (R2 or USB) and later has a CRQC. A rewrap keeps the same file key (C2), so the transit stanza also opens the stored payload. The homelab should therefore **re-encrypt** (fresh file key and nonce) rather than rewrap when it stores, and A6 must not keep the classical h0. That protects stored copies against an adversary who has stored copies or kept headers, but it **does not** reduce the transit exposure. The extra cost is one encryption pass at ingest; a later migration of an X25519 store would cost about 28 h per 10 TB at 100 MB/s (arithmetic).
- **Device restore keys** (sources skeptic). Restores are re-encrypted to the target device's own key (settled). If that key stays X25519 while the archive is PQ, every restore reintroduces harvest-now exposure (F3 M-40). Device restore keys should be PQ (hand-off to A8/D2/D3).

### F3. Recipient set, rotation and placement

- **Rotation mechanics** (C2 **verified**). Every stanza wraps the same file key, so adding or rotating recipients is a header rewrite.
- **Rewrap is not revocation.** The file key never changes. Consequences:
  - Anyone who ever held a wrapping key, and any recorded copy carrying the old stanzas, keeps access. That includes R2 copies the cloud kept, USB sticks, and A6's kept h0.
  - **Compromise of an ingest key I_e exposes every transit copy wrapped to it, permanently.**
  - Only re-encryption under a fresh file key (with a new payload nonce) restores confidentiality for a given object.
- **Requirements that follow** (to D2/A6): short I_e epochs; the online copy destroyed at epoch end; I_e kept out of homelab VM backups (D2 K-03); a decision on whether A6 keeps h0 at rest.
- **Who can check an R stanza** (C9, **secondary only**). The homelab cannot verify a device-written R stanza; nobody can verify a homelab-written one without skR either. Under any placement:
  - the homelab pins pkR from the **owner-signed trust bundle**, as devices do;
  - a **periodic sampled recovery drill** with the real R key, or R-canary objects, is the only true check (D2-S3, C8).
- **Availability of transit data if the homelab is lost** (adversary skeptic, major). Under P1, devices encrypt only to I_e. If I_e were escrowed only when retired, a homelab lost mid-epoch would strand everything still in transit: objects staged in R2, USB sticks in the post, and objects whose device copy is already gone. R cannot open them, because no R stanza exists before ingest. **Fix adopted: escrow at creation.** The homelab seals each new I_e to {X, R} and copies that escrow off-box **before** a trust bundle announcing I_e is published. Devices therefore never encrypt to an ingest key that only the homelab holds.
  - **D2 agrees.** ADR-0008 Decision 1 (revised 2026-10-06) and the D2 key inventory (K-03) now escrow each I_e at creation and copy the online bundle off-box at the start of the epoch. An earlier ADR-0008 text escrowed only at epoch end and accepted the staged-only window (AR-07). A2 adds one ordering rule: the off-box copy must exist **before** devices can learn I_e. With that, AR-07 is closed except for the escrow copy's own survival.
- **Exact stanza count, as a confidentiality control** (adversary skeptic, major). Stanzas are anonymous, and nobody without skR can check a SealBase output (C9). If ingest accepted any 1–N stanzas, a tampered trust bundle, a client bug or a malicious update could add a stanza to an attacker's key, and ingest could not tell. So:
  - the profile requires **exactly** the stanza count and types the device's trust-bundle epoch prescribes (1 × `mlkem768x25519` under P1);
  - under P1, the single stanza must open with that epoch's I_e (current or escrowed), or ingest rejects.
  - Under P2′, the second (R) stanza can never be checked at ingest. That is a further point for P1. If P2′ is chosen, devices pin pkR from the owner-signed bundle and the residual risk is accepted.
- **Placement options (DR-A2-2).** The 3 KB rule is a cost note, not a driver.

  | Option | Device writes | Stored header | Late USB bundle / long-offline upload after I_e retires | Homelab lost mid-epoch | Device cost | Stanzas no one can check at ingest |
  |---|---|---|---|---|---|---|
  | **P1 + escrow at creation (recommended)** | {I_e} | {X, R} by the homelab | Readable: R or X → escrowed I_e → object | Readable with R → off-box escrow | 1 encapsulation; 1,627 B | none |
  | P1 + escrow at retirement (earlier ADR-0008 text) | {I_e} | {X, R} by the homelab | Readable | **Unreadable** for that epoch (AR-07) | as above | none |
  | P2′: device writes {I_e, R}; the homelab rewrites stored headers to {X, R} | {I_e, R} | {X, R} by the homelab | Readable with R | Readable with R | 2 encapsulations; 3,184 B (+1,557 B; ~+160 µs on x86; phone unmeasured) | the transit R stanza (could be an attacker's key) |
  | P2: device R is the stored recovery path | {I_e, R} | {I_e, R} | Readable with R | Readable with R | as P2′ | **the stored** R, never checked |
  | P3/P3′: P2 plus the homelab recomputes the device's R stanza (disclosed randomness, or randomness derived from the file key) | {I_e, R} | as P2/P2′ | Readable with R | Readable with R | as P2′ | none, but a custom construction; P3′ makes the randomness depend on the shared file key. **Crypto review required** |
  | Two-level: stored headers carry only X; skX is sealed to R (D2 §F2) | {I_e} | {X} | Readable via X or R → skX | Readable via the escrow and the sealed skX | as P1 | none |

- **Reasoning.** P1 + escrow at creation keeps device cost minimal, needs no unverifiable stanza, and survives homelab loss as long as the escrow copy survives. P2′ makes transit objects self-contained for recovery, at one extra encapsulation and 1.5 KB per object and an unverifiable stanza. The two-level design gives a smaller stored header and makes replacing R a re-seal, at the cost of one escrow artifact that must be kept safe; D2 owns that comparison. C9 (secondary only) is not what separates the options: the recommendation rests on C6 (verified sizes), C26 (measured cost) and the availability and exact-count arguments above.
- **Epoch change:** the client re-seals any **un-receipted** item to the new I_e when the source is still present (hand-off to A3/A4). Bundles sealed under a retired key are opened through the escrow.
- **Homelab header rewrite** (adversary skeptic). Rewriting stored headers to {X, R} changes the prefix length (1,627 → 3,184 B), so every stored object is rewritten. It must be write-new, verify (open with X; sample with R in the drill), fsync, then atomic swap. Never rewrite in place (hand-off to A6, ADR-0012/0013).

### F4. Sender authentication and binding

- **A signature is needed.** age is anonymous (C12 **verified**). A2-S4 shows stock `age -d` decrypting an attacker's forged object with exit 0 (C28). Forgery resistance rests on the signed record plus homelab verification (D1 SR-03, SR-04).
- **Options:**

  | Option | PQ-compatible? | Stock `age -d` still works? | Verdict |
  |---|---|---|---|
  | Device signature on a signed-note record, inside the encryption | Depends on the algorithm (signed-note types are agile) | Yes | **Adopt** |
  | HPKE Auth mode | No (C10, C11 **verified**; C32); `hpke` 0.14.1 panics | No | Reject |
  | HPKE PSK mode | Yes | No (not the age stanza) | Reject |
  | saltpack-style DH MAC keys | No (C19) | No | Reject |
  | Per-device symmetric MAC key, wrapped to the homelab PQ key at enrollment, verified only at home | **Yes, PQ-secure today** | Yes | **Candidate complement** for D3. Adds enrollment state; a homelab compromise allows forgery, but that is already total compromise |
  | Outer signature visible to the cloud | Yes | Yes | Not needed |

- **Precondition: the device-key registry must be authentic** (logic skeptic, major). Under ADR-0002, enrollment is brokered by the cloud. A malicious or compromised cloud could mint a "new device" for an account, register its key, and upload forged objects with valid signatures. A2-S4's attacker held only the public key, so it did not test this. ADR-0007 therefore states: **the homelab accepts records only from device signing keys it has admitted through a path Cloudflare cannot forge** (D1 SR-14). The mechanism belongs to D3 (ADR-0014) and couples to OD-05. Until it exists, this is a residual risk for D1/OD-17. A2-S4 gets a new case: "cloud registers a rogue device for an existing account".
- **Fields the signature binds:**
  - **Content:** `dedup_id` (A1 text form, with epoch), `sha256`, `size` (true, unpadded), and `padded_len` if padding is adopted.
  - **Object, transport-neutral:** `h0_sha256` (SHA-256 of the device-written header bytes, including the MAC line), `header_mac`, `ct_len`, `prefix_len`, `profile`, `stanzas`. `object: null` marks a dedup hit.
    - **The R2 staging key is not signed.** The A2-S4 record signed it; that broke the settled transport-agnostic bundles (ADR-0001: the same objects travel via R2 or USB) and A3 Q10's single `record_id` across USB→R2 fallback. The staging key or USB path maps to `h0_sha256` outside the signature (A4 confirms).
  - **Device and order:** `device_id` (must equal the signing key's admitted device), `device_seq`, `record_id` (random; the idempotency key).
  - **Time:** `recorded_at` (device time, context only).
- **Ingest checks, in order** (C28; adversary skeptic, major):
  1. **Exact header match (mandatory).** SHA-256 of the received header bytes must equal the signed `h0_sha256` (E_BINDING_HEADER). Against a public-key-only forger this is just a fast filter. Against someone who **knows the file key** (a leaked or retired I_e, a substituted recipient), it is the **only** check: that party can rewrap the header to the genuine I_e and recompute a valid MAC, and every later check would pass. A mismatch is a reject **and an alarm**, because it signals a confidentiality compromise. This must happen before any homelab rewrap. (The A2-S4 code compared `header_mac`, which gives the same protection, because a rewrapped header has a different MAC unless SHA-256 collides. That is inference; the rewrap case was not run.)
  2. Profile: exact stanza count and types; low-order rejection (E_PROFILE, E_OBJECT_HEADER).
  3. Header MAC verified under the file key the homelab unwraps (E_OBJECT_HMAC).
  4. Length binding, then STREAM final chunk (E_BINDING_LENGTH, E_STREAM_*).
  5. SHA-256, dedup_id and size of the decrypted plaintext (E_CONTENT_MISMATCH, E_DEDUP_MISMATCH).
- **When to sign:** at sealing. Allocate `device_seq` and sign when the record first leaves the device (agrees with A3 F8).
- **Rollback of `device_seq`.** Restored app data or a disk snapshot can roll the counter back while the key survives; honest records would then hit E_REPLAY_SEQ. A3 must make E_REPLAY_SEQ for a registered device a **visible health issue**, and define seq-epoch recovery.
- **Receipts** bind `record_sha256`, the digest of the exact signed plaintext record (A3 owns the format).
- **Classical signatures for v1: a risk acceptance, not a finding.** C24 is **contested**. Two skeptics refuted it as stated: once a CRQC exists, anyone with a device's public key can forge *new* records at any later ingest, and late USB ingest can be delayed without limit. So ADR-0007 does **not** claim classical signatures are adequate. It requires:
  - **verify once, persist the verdict:** the homelab verifies each device signature at ingest and its own signed receipt becomes the durable authority. Catalog rebuilds (A6/ADR-0013), fixity (A7), provenance and late-USB policy never re-verify device signatures as authority;
  - **agility in the format from day one:** the record accepts any signed-note type registered for that device in the trust bundle, and a hybrid or PQ type (via 0xff) is reserved now, so migration is a trust-bundle change, not a format change;
  - **a dated review trigger:** register and roll out a hybrid or PQ device signature type before 2030, or earlier on a credible CRQC signal. The 2030 date is a planning proposal. It is informed by NIST IR 8547's draft timeline (EdDSA deprecated after 2030, disallowed after 2035), which is **skeptic-reported from a secondary source and unverified** (primary blocked, S31);
  - **device signing public keys are not used as the cloud API credential**, so they are not exposed to the cloud more than necessary (D3).

  The owner accepts the remaining risk under DR-A2-3 / OD-17, or chooses option B (adds the PQ-secure symmetric MAC key), which removes the reliance on C24.
- **Which signature algorithm** is D3's call (ADR-0014): Ed25519 (0x01) in software, wrapped by the keystore; or ECDSA P-256 (0x02), which can be hardware-backed (the iOS Secure Enclave and Android StrongBox offer P-256; skeptic-reported, not checked here). A software Ed25519 key can be exfiltrated by malware on a stolen device, which allows forging as that device until it is revoked. This classical path matters more today than the quantum one.

### F5. Resumability, truncation, random access and decoding

- **Layout:** CE §5–§8 with prefix_len = header + 16 (1,643 / 3,200 B). Tested by A2-S2 (C27).
- **Hedging:** each stanza's 64-byte X-Wing randomness comes from the same seed and salt as the file key and payload nonce: HKDF(seed, salt = SHA-256(plaintext), info = `reliquary/v1/hedge/xwing-encap/<i>`). It is injected through a seeded RNG that asserts exactly 64 bytes are drawn (C23; A2-S2). The header is built once and kept in the sealed state.
  - **Rollback rule** (logic and adversary skeptics). Every per-object secret (file key, encapsulation randomness, payload nonce) is derived from one seed + salt, never mixed with an independently drawn value. Then a rolled-back seed with the same plaintext reproduces the same header (no reuse), and a different plaintext changes everything. A fresh file key combined with old encapsulation randomness would reuse the stanza's ChaCha20-Poly1305 key and nonce; the spec forbids that combination. G2 adds a snapshot-rollback-and-edit case (not yet tested).
  - The assertion couples the encoder to `hpke`'s internal RNG use: another reason to pin exactly.
- **Device-side state** (adversary skeptic). The sealed state and journal hold a per-upload file key while in flight. They must be excluded from OS backups (Android `noBackupFilesDir` / `allowBackup=false`; Time Machine and VSS exclusions) and sealed by a non-exportable keystore key (hand-off to B6/B2/D3). A2-S2 searched only the live filesystem after commit.
- **Truncation and order:** CE §5.4 (valid lengths) and §5.5 (authenticate the final chunk before serving a middle chunk). A2-S4 shows that the length binding and STREAM reject independently (C28).
- **Restore output rule.** age releases authenticated non-final chunks before truncation is detected. Restore tools write to a temporary file and expose it only after the final chunk and the record's SHA-256 both verify.
- **Two-layer conformance** (sources skeptic, major). CCTV `hybrid_and_x25519`, `hybrid_grease` and `hybrid_multiple_recipients` expect *success*, but the Reliquary profile rejects mixed, grease and extra stanzas. If the layers are merged, an implementer will either fail CCTV or loosen the profile. So `object-format.md` defines:
  1. an **age v1 decoder** that passes every applicable CCTV vector, including the low-order rejection;
  2. a separate **Reliquary profile validator** (allowed stanza types, exact count, size limits) that runs before decryption and any catalog write. The spec lists which CCTV and project vectors the validator is expected to reject.
- **Decoder conformance (C22 verified):** every Rust decoder rejects an all-zero X25519 shared secret in the X-Wing ciphertext share, in project code. It must not rely on the crate default, which `x-wing` says "will be altered".
- **Dependency pinning:** the client and any Rust homelab tool pin `hpke`, `x-wing` and `ml-kem` with `=`. The tested set is `hpke` =0.14.1, `x-wing` 0.1.1, `ml-kem` 0.3.2 (the spike pinned only `hpke`; the lock resolved the rest). CCTV `hybrid_*` and the project vectors gate every bump (G2). Cryspen `hpke-rs`/libcrux is a candidate second backend for differential testing (logic skeptic); not evaluated.
- **Panic safety:** `hpke` 0.14.1 panics on X-Wing auth mode (C11). Server code must never reach auth paths and treats a decoder panic as a reject.
- **iOS (B4 K2–K4):** placement rules only; no format change.

### F6. Metadata record (provisional; follows A5)

- **Envelope.** The plaintext is a C2SP signed-note (C15): one line of I-JSON, then one signature line. Records travel in **record batches**: one age file carrying N length-prefixed signed notes, to amortize the PQ header. Each note stays a distinct **per-(device, file) signed unit**, matching ADR-0001's "encrypted metadata record per (device, file)".
- **Relation to A4 manifests.** The device signature lives on the per-(device, file) record. A4 manifests and USB bundles should **reference record digests** (`record_sha256`) rather than re-sign the same facts. A4 decides; this note asks it to avoid two signed structures. Batching and manifest structure are A4's (ADR-0011).
- **Fields v0:** H4 §6.1, plus A1's text `dedup_id` with epoch and a reserved `chunk_list`; A3's `device_seq` and `record_id`; B4's `source_version`; `*_raw_b64` path forms; `content_encoding` (`identity` in v1); `padded_len`; and the transport-neutral object block (§F4). H4 §6.1 still lists `content_object {key, header_mac}`; that should become the §F4 object block (hand-off to H4).
- **Evolution rules:** integer `v`; an open `kind`; unknown fields preserved and ignored; no change of meaning within a `v`; plugin `source_hints` namespaced.
- **Alternative: deterministic CBOR (CDE).** Revisit after A5 and the D2/E7 break-glass requirements. The analyst leans JSON for heir readability. Low-medium confidence.

### F7. Length hiding and compression

- **Padmé, provisionally adopted** (DR-A2-4, which is the same decision as F3's DR-F3-1). F3-S1 passed at per-device scale and was mixed at family scale; F3 recommends adoption pending the owner-library leg.
  - zero padding before encryption;
  - IDs and SHA-256 over the unpadded bytes;
  - every cloud-visible size padded (receipts, presence checks, SR-24, multipart layout, Content-Length).
- **Overhead by size class** (F3 C8, **verified** in F3; logic skeptic asked for this):
  - 64 KiB to 4 GiB: ≤ 3.125 % per file;
  - 256 B to 64 KiB: ≤ 6.25 % per file;
  - ≥ 4 GiB: ≤ 1.5625 % per file;
  - measured byte-weighted on public corpora: 1.13 % (photos), 1.15 % (documents) (F3 C31). The family mix is unmeasured (E1).
- **Trade-offs:** stock `age -d` returns the file plus trailing zeros, so recovery needs the true size from the record. Some formats may break with trailing data (ZIP's end-of-central-directory search is the skeptic's example; not checked against a primary source). If the record or its batch is lost, an heir has no true size. F3 mentions framing the length inside the payload, which would keep the size without the record but would also change what stock `age -d` outputs. To D2-S3 and E7.
- **Size buckets** are an alternative; F3-S1 measured 64 KiB buckets at 7.58 % on documents, which fails F3's cost rule.
- **No compression in v1.** `content_encoding` is reserved.

### Alternatives compared

| Option | Fit with settled requirements | Pros | Cons | Evidence |
|---|---|---|---|---|
| **age v1, `mlkem768x25519` only (recommended)** | Fits | Stock Go age ≥ 1.3.0, typage, kage; C2SP spec; CCTV hybrid vectors; interop shown | 1.6–3.2 KB header; own stanza code; KEM from an I-D; X-Wing low-order behaviour not fixed at CFRG; large relative cost for small objects | C4–C8, C13, C22, C25, C26, C32 |
| age v1, X25519 (CE today) | Fits | 168 B header; any age version | Harvest-now exposure of **every** transit copy uploaded under it, and of device keys | C2, C6; F3 §7 |
| age v1 with `mlkem768p256tag` for a hardware R (with `mlkem768x25519` elsewhere) | Fits (both PQ, so Go age allows the pair) | Hardware-held recovery identity | 1,679 B stanza header (C31); Rust `tagpq` is encrypt-only; hardware support unevaluated | C7, C31; D2/OD-08 |
| age v1, mixed PQ + X25519 | — | — | SHOULD NOT; Go refuses; typage does not refuse | C5, C29 |
| Many small files packed per age object | Fits if dedup stays whole-file in the index | Amortizes PQ cost for small files | Changes the object model (A1/A4); partial restores read more | Adversary skeptic; not evaluated |
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
| Rust `hpke` (RustCrypto) | X-Wing stanza encode/decode in the client core | MIT/Apache-2.0 | 0.14.1; interop shown (C25); pre-1.0; panics on X-Wing auth | S6, SP3 |
| Rust `x-wing`, `ml-kem` | KEM building blocks | MIT/Apache-2.0 | 0.1.1 (2026-10-01), ml-kem 0.3.2; **pin exactly** | S26 |
| Cryspen `hpke-rs` / libcrux | Possible second backend and differential-testing oracle | not checked | `hpke-rs` 0.7.0 read for auth behaviour only | S7 |
| Rust `age` | X25519 decrypt only | MIT/Apache-2.0 | 0.12.1; no PQ | S5 |
| typage | TS age with PQ | BSD-3-Clause (not re-checked) | 0.3.1; writes mixed headers | S12, SP3 |
| kage | Kotlin age with native PQ | not checked | 0.8.0; passes CCTV (weaker runner) | S29, SP3 |
| `age-plugin-pq`, rage with a plugin | Alternative heir decode path | not checked | not evaluated | — |
| CCTV age | Decrypt-direction conformance | README allows copying | 2026-09-25 | S4 |
| ed25519-dalek | Record signatures (spike) | not checked | as locked in the spike | — |

## Spikes

All four ran in the cloud container on synthetic data (`SYN → results`), on x86 Linux and **not on a phone**. R2 and the keystore were simulated by local files: **emulated, not real R2/Cloudflare**. The spike code is in `spikes/A2-S2/` and is shared by all four.

| Spike | Hypothesis | Pass → / fail → (decision) | Exec tag | Budget IDs | Data class | Status | Result |
|---|---|---|---|---|---|---|---|
| A2-S1 Throughput and energy, X25519 vs PQ | Encryption is never the bottleneck vs a 100 Mbit uplink; PQ header ≤ 3 KB per object; ≤ 10 % PQ loss on a low-end phone; BUD-BAT-S recorded | Pass → PQ from day one (OD-06); fail → X25519 now plus a migration plan (§F2 fallback) | CT + OL | BUD-HASH, BUD-BAT-S | SYN → results | **CT ran; OL kit-ready.** Overall: **inconclusive** | **Header:** 1 PQ = 1,627 B (pass); 2 PQ = 3,184 B (**fail** as written); X25519 168 B; record file 2,683 B. **x86 throughput:** never below 70.9 MB/s (> 12.5 MB/s). **PQ×1 loss:** 52 % @16 KiB, 37 % @100 KiB, 15 % @1 MiB, 5 % @4 MiB (C26). Crate passes `cargo check` for aarch64-linux-android and aarch64-apple-ios (not linked or run). **Phone loss and BUD-BAT-S: no result.** Evidence: [`spikes/A2-S1/`](../../spikes/A2-S1/README.md). Kit: [`docs/research/kits/A2-S1/`](kits/A2-S1/README.md) (`run-android.sh`, soak workload) |
| A2-S2 Kill-and-resume, 50 random kills | With PQ headers: exact SHA-256; ≤ 1 segment re-encrypted per kill; no (key, nonce) reuse; no file key survives commit | Pass → CE journaled resume in ADR-0007; fail → temp-file spool | CT | BUD-TMP | SYN → results | **Pass** | 50 kills (1 stanza, 127/127 checks) + 20 kills (2 stanzas, 63/63). Max 1 part per kill. Wire consistency; 12/12 edit-after-kill refusals; 0 key hits; no temp ciphertext. Limits: kills only in start/resume; parts of 1–4 chunks; no snapshot rollback; live filesystem only. Evidence: [`spikes/A2-S2/evidence/`](../../spikes/A2-S2/evidence/README.md) |
| A2-S3 Interop | Rust `hpke` X-Wing output ↔ Go age ≥ 1.3.0, typage, kage; 100 % CCTV + project vectors; `hybrid_low_order` predicted to fail on plain `hpke` | Pass → Rust `hpke` X-Wing in the encoder; fail → F2 fallback | CT | — | SYN → results | **Pass** | 853/853 matrix. CCTV: Go 147/147; Rust strict, typage and kage 85/85 applicable. Rust **lax** decoder fails `hybrid_low_order` and `hybrid_identity`, as predicted. 15 project vectors are deterministic and pass 15/15 everywhere. typage writes mixed headers. kage 0.8.0 has native PQ. Evidence: [`spikes/A2-S3/`](../../spikes/A2-S3/README.md) (its "x-wing 0.1.0" should read 0.1.1, per the lock file) |
| A2-S4 Forgery and truncation | A forged object + record (attacker holds only the public key) and a dropped final chunk are rejected before any catalog write, with specific codes | Pass → F4 binding set; fail → outer binding | CT | — | SYN → results | **Pass, for the earlier record layout** | 30/30. Stock `age -d` accepts the forgery (exit 0). 26 attacks rejected with their own codes and an unchanged store; an honest replay is idempotent. **The record signed the R2 staging key and `header_mac`, not `h0_sha256`** (spike source), so this pass does not yet cover the recommended transport-neutral record. **Re-run needed before Gate A** with: the §F4 record; USB→R2 fallback with the same `record_id`; staging-key / USB-path substitution; a file-key holder rewrapping to the genuine I_e (expect E_BINDING_HEADER); the cloud registering a rogue device for an existing account. Not covered (A3/D4): a registered device claiming another device's dedup_id with the correct sha256/size. Evidence: [`spikes/A2-S4/`](../../spikes/A2-S4/README.md) |

## Conflicts with settled text

- None that contradict CLAUDE.md, ADR-0001 or ADR-0002.
- **Avoided conflict.** The earlier draft (and the A2-S4 spike) bound the R2 staging key in the signed record, which would break the settled transport-agnostic bundles. Replaced with transport-neutral fields (§F4).
- **Tension to raise, not resolve here:**
  - **Device-key admission vs ADR-0002.** Device signatures stop a malicious cloud only if the homelab admits device keys through a path the cloud cannot forge (SR-14). ADR-0002's cloud-brokered, admin-free enrollment does not provide that by itself. This is OD-05 (D3), and ADR-0007 states it as a precondition.
  - **Recovery recipient and R-22.** Encrypting to an offline recovery key is compatible with "encrypted to the homelab public key" only if R counts as admin-held homelab trust. Under the recommended P1, devices do not encrypt to R at all. ADR-0008 already raises R-22 for OD-08.
  - **Device signature algorithm.** CLAUDE.md lists the per-device credential format as open. ADR-0007 states requirements only and leaves the algorithm to D3 (ADR-0014). The D1 register's SR-03 says "Ed25519"; that should read "the registered signature type".
- For awareness: ADR-0001's "the homelab public key (e.g. X25519 / age)" admits `mlkem768x25519`. The A2-S1 header and throughput rules are A2-local (budgets.md "Keep local"); this note does not change them and asks how they aggregate (DR-A2-1).

## Open questions

1. **Phone cost of X-Wing** (low-end Android; iPhone later), including small-file-heavy libraries and BUD-BAT-S. Owner: A2-S1 OL kit. Needed by Gate A.
2. **How the A2-S1 rules aggregate:** "≤ 10 % loss" (per object, at the typical size, or byte-weighted over the E1 mix) and "≤ 3 KB" (per object or per stanza). Owner: owner/H1.
3. **A2-S4 re-run** on the transport-neutral record with the five new cases (§Spikes). Owner: A2 spike runner, Wave 2, before Gate A.
4. **Escrow ordering.** ADR-0008 copies the escrow off-box "at the start of the epoch"; A2 asks that this precede publication of the trust bundle announcing I_e. Owner: D2.
5. **Device-key admission mechanism** (SR-14) that the record signature depends on. Owner: D3 (ADR-0014), OD-05.
6. **Is a 128-bit age file key adequate against quantum key search** for keep-forever data? No primary source was read (NIST blocked). Owner: H1 source escalation; F3.
7. **CFRG's choice on non-contributory X25519 in X-Wing**, and whether it changes age's definition. Mail archive blocked. Owner: H1, A2 tracks before Gate A.
8. **Byte equality of hpke-pq -05 test vectors with -03** (code point and sizes are unchanged, C32). Owner: A2, by running the -05 A.5 vectors through the pinned crates (Wave 2).
9. **NIST IR 8547 timeline** for EdDSA, to confirm the 2030 review trigger. Primary blocked. Owner: H1.
10. **Record encoding:** JSON-in-signed-note vs CBOR. Owner: A2, Wave 2 (after A5).
11. **Device signing-key algorithm and storage** (Ed25519 software vs P-256 hardware; the symmetric MAC complement; Android Keystore Ed25519 support unchecked). Owner: D3.
12. **Strict parser limits.** Proposed in `object-format.md`: header ≤ 16 KiB, ≤ 16 stanzas parsed, record ≤ 1 MiB, as in the spike. Confirm in Wave 2 (G2 fuzzing).
13. **`mlkem768p256tag` for a hardware-held R:** sizes now measured (C31); hardware support and a Rust decrypt path are open. Owner: D2 (OD-08).
14. **Which Tink release ships X_WING:** relevant only if ADR-0003 leaves a Rust core. Owner: T1/B-track.

## Recommendation

For the ADR-0007 draft (`docs/adr/0007-object-envelope-and-metadata-record.md`):

1. **Construction:** standard age v1 objects from the client's own encoder with CE's journaled resume (C1, C13, C25, C27).
   - Profile: only `mlkem768x25519` stanzas, in exactly the count the epoch prescribes; no scrypt, plugin, armor or grease.
   - Two layers: a CCTV-conformant age decoder plus a separate profile validator, enforced **at ingest**, because not every encoder enforces it (C29).
2. **PQ from day one (OD-06): recommended**, resting on C4, C5, C6, C7, C13 (verified) and A2-S3. It is **conditional on the A2-S1 OL phone result**, read under the owner's choice of how the 10 % rule aggregates. If it fails, use option B and state its exposure plainly (§F2).
3. **Recipients (DR-A2-2):** devices write {I_e} only; the homelab writes the stored {X, R} with pkR pinned from the owner-signed trust bundle; each I_e is **escrowed to {X, R} at creation and copied off-box before publication**; a sampled R drill; short I_e epochs, I_e out of backups. This matches ADR-0008 Decision 1 (revised 2026-10-06), plus the ordering rule. Rewrap is not revocation.
4. **Sender authentication:** a device signature on a signed-note record inside the encryption (C10, C11, C12 verified; A2-S4).
   - It binds content, the **transport-neutral** object block (`h0_sha256` etc.), device, sequence and time, and is signed at sealing.
   - Ingest requires an **exact header match** with `h0_sha256`, before any rewrap.
   - Receipts bind `record_sha256`, and the homelab's signed verdict is the durable authority.
   - **Precondition:** device keys are admitted through a path the cloud cannot forge (SR-14, OD-05).
   - The algorithm is any trust-bundle-registered signed-note type (D3). Using a classical type in v1 is an **owner risk acceptance** with a dated review trigger, because C24 is contested. No HPKE Auth or PSK mode.
5. **Truncation, random access and restore:** CE §5.4/§5.5, plus restore output exposed only after full verification.
6. **Dependencies:** exact pins for `hpke`, `x-wing` and `ml-kem`; the low-order rejection in project code; CCTV + project vectors in CI on every bump.
7. **Length hiding (DR-A2-4):** Padmé, provisionally, following F3 (overhead by size class in §F7). No compression in v1.
8. **Deliverables:** ADR-0007 (Proposed, partial) and `docs/spec/object-format.md` (Draft), referencing the A2-S3 project vectors until they move under `docs/spec/`.

**What would change this:**
- the phone shows PQ cost matters → option B, with its exposure accepted explicitly;
- the A2-S4 re-run fails on the transport-neutral record → add an outer binding;
- OD-07 picks a posture with no rewrap → the homelab must still add R, or P2 is accepted knowingly;
- D2 rejects escrow → P2′ (with the unverifiable-stanza risk);
- A5 needs binary-heavy records → CBOR;
- a later hpke-pq or CFRG revision changes the MLKEM768-X25519 bytes before Gate A → re-run A2-S3.

## Decision requests

### DR-A2-1: Post-quantum recipients from day one (this is OD-06)
- **Needed by:** Gate A (one-way door #2).
- **Evidence:** §F2; C4–C8, C13, C22 (verified); C25–C27, C32 (measurements and reads); C30 (arithmetic).
- **Options:**

  | Option | What it means for the family | Cost | Reversibility | Risks |
  |---|---|---|---|---|
  | A. PQ for all stanzas now (recommended, if the phone cost is acceptable) | Nothing visible | +1.5 KB per transit object; stored {X, R} + h0 ≈ 4.8 KB (0.1–1 % of bytes depending on mean size); x86: +77 µs per stanza per object; phone unmeasured | Moving back is possible but pointless | KEM from an I-D; X-Wing low-order behaviour still open at CFRG; pre-1.0 Rust crates |
  | B. X25519 on devices; the homelab re-encrypts to PQ when it stores | Nothing visible | Smallest device cost; one extra encryption pass at ingest | Later switch to A for new uploads only | **Every object uploaded under B stays exposed to whoever recorded its transit copy** (R2, USB); re-encryption protects stored copies only |
  | C. Mixed PQ + X25519 | — | — | — | SHOULD NOT; Go refuses |

- **Also asked:** how A2-S1's "≤ 10 % loss on a low-end phone" aggregates: per object, at the typical object size (the kit's reading), or byte-weighted over the E1 mix. On x86 the per-object loss is 37–52 % below 100 KiB and 5–15 % at photo sizes.
- **Recommendation:** A, once the A2-S1 OL result is in under the agreed reading; otherwise B, with its exposure accepted explicitly.
- **If no decision by the deadline:** draft with A and the fallback written in. No production keys are generated before acceptance.

### DR-A2-2: Who writes the recovery stanza, and when ingest keys are escrowed (H1 to number; couples OD-07, OD-08)
- **Needed by:** Gate A.
- **Evidence:** §F3; C2, C6 (verified), C26 (measured), C9 (secondary only); D2 §F2 and ADR-0008 Decision 1 (which already chose P1 + escrow at creation); A6 F3.
- **Options:**

  | Option | What it means for the family | Cost | Reversibility | Risks |
  |---|---|---|---|---|
  | P1 + escrow at creation (recommended) | Nothing visible | 1,627 B device header; one escrow artifact per epoch, copied off-box before use | Can move to P2′ with a client update | The escrow copies must survive (kept with the recovery kit) |
  | P1 + escrow at retirement (earlier ADR-0008 text) | Nothing visible | As above | As above | Homelab lost mid-epoch → that epoch's transit data unreadable (AR-07) |
  | P2′. Device writes {I_e, R}; the homelab rewrites stored headers to {X, R} | Nothing visible | 3,184 B and one more encapsulation per object (phone cost unmeasured) | Can drop R later | The transit R stanza cannot be checked and could point to an attacker's key |
  | P2. Device R as the stored recovery path | Nothing visible | 3,184 B | — | The stored R is never verified (C9) |
  | Two-level: stored headers carry only X; skX sealed to R | Nothing visible | Smaller stored header | Replacing R is a re-seal | One more escrow artifact to protect (D2 compares) |

- **Also asked:** is A2-S1's "≤ 3 KB" rule per object or per stanza? Here it is a cost note, not the driver.
- **Recommendation:** P1 + escrow at creation. In every case: homelab-written stored R, pkR pinned from the trust bundle, exact stanza count at ingest, a sampled R drill, short I_e epochs, I_e out of backups.
- **If no decision by the deadline:** ADR-0007 requires the exact count the epoch prescribes; placement follows ADR-0008.

### DR-A2-3: Sender authentication by a device-signed record; classical signatures as a risk acceptance (refines OD-04; feeds OD-05 and OD-17; H1 to number)
- **Needed by:** Gate A.
- **Evidence:** §F4; C10, C11, C12 (verified); C24 (**contested**); C28.
- **Options:**

  | Option | What it means for the family | Cost | Reversibility | Risks |
  |---|---|---|---|---|
  | A. Signed-note signature (type per D3, e.g. Ed25519 or P-256) on the record inside the encryption; exact header match at ingest; receipts bind the record digest; the homelab verdict is the durable authority; hybrid/PQ type reserved; review by 2030 (recommended architecture) | Nothing visible | Tiny | Type agility through the trust bundle | Relies on an owner risk acceptance for classical signatures (C24 contested); a software key can be exfiltrated; needs SR-14 device-key admission |
  | B. A plus a per-device symmetric MAC key, wrapped to the homelab PQ key, verified only at home | Nothing visible | Enrollment state | Removable | More key management (D3); needs the same SR-14 path |
  | C. Hybrid classical + ML-DSA signature now | Nothing visible | Larger records (PQ signatures up to ~5 kB per S11) | — | No general ML-DSA signed-note type yet (only 0xff); immature |
  | D. HPKE Auth mode | — | — | — | Not available with PQ KEMs |

- **Recommendation:** the architecture of A is recommended on verified evidence. **Whether a classical signature alone is acceptable for v1 is the owner's risk acceptance**, recorded in OD-17 with the verify-once rule and the 2030 review trigger. If the owner does not want to rely on that, choose B.
- **If no decision by the deadline:** A with Ed25519, with the risk recorded as open in OD-17.

### DR-A2-4: Length hiding (same decision as DR-F3-1; H1 to merge and number)
- **Needed by:** Gate A.
- **Evidence:** §F7; F3 C8 (verified), C31; CE D-7.
- **Options:**

  | Option | What it means for the family | Cost | Reversibility | Risks |
  |---|---|---|---|---|
  | A. Padmé zero padding (recommended, provisional) | Heirs must trim to the true size; stock `age -d` output has trailing zeros | ≤ 3.125 % per file for 64 KiB–4 GiB, ≤ 6.25 % for 256 B–64 KiB; 1.13–1.15 % byte-weighted on public corpora | Off for new objects only | Useless unless every cloud-visible size is padded; some formats may break with trailing zeros (skeptic-reported); depends on the record surviving |
  | B. Size buckets | As A | 64 KiB buckets: 7.58 % on documents (F3-S1) | As A | Fails F3's cost rule at that bucket size |
  | C. No padding | None | None | Can adopt later for new objects | Exact sizes fingerprint files (AR-05) |

- **Recommendation:** A, provisional until F3-S1's owner-library leg; otherwise C, with `padded_len` reserved.
- **If no decision by the deadline:** C, with `padded_len` reserved.

## Hand-offs

| To | What | Why |
|---|---|---|
| D2 (ADR-0008), A6 (ADR-0012/0013) | DR-A2-2: aligned with ADR-0008 Decision 1 (escrow at creation). Add the ordering rule: the off-box escrow copy exists **before** the trust bundle announcing I_e is published; pkR pinned from the owner-signed trust bundle at the homelab; sampled R drill or R-canaries (D2-S3); short I_e epochs, I_e out of backups; decide whether to keep h0 at rest; stored-header rewrite as write-new → verify → fsync → atomic swap; `mlkem768p256tag` sizes measured (C31) | §F3 |
| D3 (ADR-0014), D1 | **SR-14 device-key admission is a precondition for record signatures** (OD-05); add the "cloud registers a rogue device" case; signature type per device (Ed25519 software vs P-256 hardware); optional symmetric MAC key; device signing keys not used as cloud API credentials; amend SR-03 "Ed25519" to "registered signature type" | §F4 |
| A3 (ADR-0009) | Sign at sealing; receipts bind `record_sha256`; record batches of per-(device, file) signed units; padded sizes; E_REPLAY_SEQ as a visible health issue plus seq-epoch recovery; re-seal un-receipted items on an ingest-key epoch change; the homelab's signed verdict is the durable authority; restore selection must not trust dedup-hit claims alone | §F3, §F4 |
| A4 (ADR-0011) | The record binds `h0_sha256`, not the R2 key; the staging key or USB path maps outside the signature; manifests reference record digests rather than re-sign; same `record_id` across USB→R2 | §F4, §F6 |
| A6/A7/C8 (ADR-0013, 0029, 0032) | Never re-verify device signatures as authority in rebuilds, fixity or provenance; rely on homelab receipts | §F4 (C24) |
| A8 (ADR-0028), D2, D3 | PQ device restore keys (otherwise restores reintroduce harvest-now exposure); a Rust X-Wing decrypt path with its own low-order check; restore output exposed only after full verification | §F2, §F5 |
| B6, B2, D3 | Sealed state and journal excluded from OS backups and sealed by a non-exportable keystore key | §F5 |
| G2 (ADR-0035), G1 | Exact pins for `hpke`/`x-wing`/`ml-kem`; CCTV + project vectors on every bump; the two-layer conformance split; a snapshot-rollback-and-edit case; label the typage/kage CCTV runners as weaker; parser fuzzing against the spec limits; consider `hpke-rs`/libcrux as a differential oracle | §F5, C25 |
| H4 | Replace `content_object {key, header_mac}` in data-model §6.1 with the §F4 object block | §F6 |
| D2, F3 | Restate the "0.9M–4.5M" figure as photos at the Open Images mean (F3 states it correctly); per-file overhead depends on mean size and stored posture (§F2 table) | C21 |
| F3 | DR-A2-4 = DR-F3-1; owner-library leg of F3-S1 | §F7 |
| H1 | Blocked sources (Method; incl. NIST IR 8547); OD numbers for DR-A2-2..4; DR-A2-1 = OD-06; merge DR-A2-4 with DR-F3-1; the A2-S1 aggregation questions | Registry owner |
| A2 spike runner (Wave 2) | Fix the A2-S3 README's `x-wing` version; re-run A2-S4 on the transport-neutral record with the five new cases; run hpke-pq -05 A.5 vectors through the pinned crates | §Spikes |
