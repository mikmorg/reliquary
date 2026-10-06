# ADR-0007: Content objects are standard age v1 files with post-quantum recipients, written by a resumable client encoder and bound to a device-signed record. Wave 1 part: the envelope

- **Status:** Proposed. This is a partial draft covering the Wave 1 (P0) envelope decisions. The metadata-record schema and encoding, the device signature algorithm and the confirmed parser limits are to be decided in Wave 2; see "Not yet decided".
- **Date:** 2026-10-06
- **Owner workstream:** A2
- **Decider:** the owner
- **Gate:** A
- **Supersedes / Amends:** None. ADR-0001 §2 ("encrypted to the homelab public key (e.g. X25519 / age)") is satisfied: devices encrypt to one homelab-held key, the current ingest key, of type `mlkem768x25519`. ADR-0002 is not amended, but Decision 5's precondition depends on OD-05 (see "Consequences").
- **Evidence:** `docs/research/a2-object-envelope.md` (Wave 1 final). Spikes:
  - `spikes/A2-S1/` (CT part ran) and kit `docs/research/kits/A2-S1/` (OL, kit-ready, no phone result);
  - `spikes/A2-S2/` (ran; pass), `spikes/A2-S3/` (ran; pass, with project vectors in `spikes/A2-S3/vectors/`);
  - `spikes/A2-S4/` (ran; pass for the earlier record layout; re-run required).

  Builds on the T1 spike 2 note `docs/research/content-encryption-format.md` (CE). Normative draft: `docs/spec/object-format.md`.
- **Traceability:** R-19, R-20, R-25, Q1-4; touches R-18 and R-22 (see `docs/research/traceability.md`)
- **Owner decisions:** OD-06 (= DR-A2-1); new DR-A2-2 (joint with OD-07, OD-08), DR-A2-3 (refines OD-04; feeds OD-05, OD-17) and DR-A2-4 (= DR-F3-1). H1 numbers them.
- **One-way door:** Yes, door #2 in `docs/research/one-way-doors.md` (object envelope, PQ, sender authentication)

## Context and problem statement

Every keepsake leaves a family device as ciphertext, crosses Cloudflare R2 or a USB stick in the post, and is kept forever. The envelope therefore has to be readable by stock tools long after Reliquary's own code is gone. It has to resist a future quantum adversary who records transit copies today ("harvest now, decrypt later"). It must survive app kills mid-upload without temp copies of large files. And it must let the homelab reject forged objects, because age gives anyone holding the public key the power to make a valid file. This must be fixed before any real family byte is encrypted with production keys (Gate A).

Settled constraints: content and metadata are encrypted on the device to a homelab-held public key (R-19); devices cannot read backups (R-20); source locator, name and mtime are plaintext only at the homelab (R-25); devices can only append (R-18); the same encrypted objects travel via R2 or USB (ADR-0001). ADR-0001 left open how resumable uploads coexist with age's randomness (Q1-4). T1 spike 2 answered that for X25519; this ADR extends it to post-quantum recipients, recipients for recovery, and sender authentication.

## Decision drivers

- R-19, R-20, R-25: encryption on the device, devices cannot decrypt, metadata plaintext only at home.
- R-18 and ADR-0001: append-only devices; transport-agnostic objects (R2, USB).
- Keep forever and "data integrity over everything" (CLAUDE.md): readable by stock tools; harvest-now resistance; nothing stranded if the homelab is lost.
- D1 security requirements: SR-03 (device-signed records), SR-04 (verify before commit), SR-13 (gap detection), SR-14 (device keys admitted without trusting the Worker), SR-22 (hostile-input parsing), SR-24 (size bounds).
- Budgets: BUD-HASH and BUD-BAT-S (A2-S1 phone cost), BUD-TMP (no temp ciphertext spool), BUD-RESTORE (random access).
- A2-S1's local rule: PQ header ≤ 3 KB per object and ≤ 10 % throughput loss on a low-end phone (budgets.md "Keep local").

## Considered options

1. age v1 with `mlkem768x25519` (X-Wing) stanzas only, from the client's own resumable encoder.
2. age v1 with X25519 stanzas (CE today), with a later PQ upgrade at the homelab.
3. age v1 with mixed PQ and X25519 stanzas.
4. HPKE (base or auth mode) plus a custom STREAM format.
5. Tink Hybrid plus Streaming AEAD.
6. libsodium sealed box plus `secretstream` (Ente style).
7. saltpack signcryption.
8. OpenPGP RFC 9580 with the PQC draft.

## Decision

Option 1, **conditional on the A2-S1 phone result** (Decision 2). age v1 is the only candidate with a public spec, a conformance kit, independent implementations in Go, Rust, TypeScript and Kotlin, and a stock CLI with a backwards-compatibility promise. Its native PQ recipient interoperates with our Rust stanza code (A2-S3, 853/853).

Normative details are in `docs/spec/object-format.md` (Draft).

### Decision 1 (in scope): construction and profile

- Every content object is a **standard age v1 file** (C2SP age spec), written by the client's own encoder with CE's hedged randomness and journaled resume (CE §5–§8; A2-S2 pass with PQ headers). No temp ciphertext spool.
- **Reliquary profile v1** (a strict subset of age v1):
  - stanza type `mlkem768x25519` only; no X25519, scrypt, plugin, tag or grease stanzas on device-written objects; no armor;
  - **exactly** the stanza count and recipients that the device's trust-bundle epoch prescribes (one stanza under Decision 3);
  - header and record size limits as in the spec.
- **Two layers, kept separate:**
  1. an age v1 decoder that passes every applicable CCTV vector, including the low-order rejection;
  2. a Reliquary profile validator that rejects anything outside the profile before decryption and before any catalog write.

  CCTV `hybrid_and_x25519`, `hybrid_grease` and `hybrid_multiple_recipients` expect success from the decoder and are rejected by the validator. The spec lists them.
- The profile is enforced **at ingest**, not assumed from encoders: typage 0.3.1 writes mixed headers (A2-S3).
- The KEM is defined **by the C2SP age spec plus the CCTV and project vectors**, not by a crate's draft label. The tested crate set is `hpke` =0.14.1, `x-wing` 0.1.1, `ml-kem` 0.3.2, all pinned with `=`. Every Rust decoder rejects a low-order X25519 share in project code.

### Decision 2 (in scope, conditional): post-quantum from day one (OD-06)

- **Recommended:** every stanza is `mlkem768x25519`. Header 1,627 B for one stanza (measured with four encoders).
- **Condition:** the A2-S1 OL kit shows acceptable phone cost, under the owner's choice of how the "≤ 10 % loss" rule aggregates (per object, at the typical object size, or byte-weighted). On x86 the loss is 52 % at 16 KiB, 37 % at 100 KiB, 15 % at 1 MiB and 5 % at 4 MiB.
- **Fallback (option 2) if the condition fails:** devices encrypt with X25519; the homelab **re-encrypts** (fresh file key and nonce) to PQ {X, R} when it stores and keeps no classical header. This must be accepted knowing that **every object uploaded under the fallback stays exposed** to whoever recorded its transit copy; re-encryption protects only the stored copies.
- No production keys are generated before the owner decides OD-06.

### Decision 3 (in scope; joint with ADR-0008 Decision 1): recipients and placement

- Devices write **one stanza, to the current ingest key I_e**.
- The homelab writes the stored header **{archive X, recovery R}** after verification, by writing a new object, verifying it, fsyncing, then swapping atomically. pkR is pinned from the owner-signed trust bundle.
- **Each I_e is escrowed to {X, R} at creation, and the escrow is copied off the homelab before any trust bundle announcing I_e is published.** If the homelab is lost mid-epoch, transit objects (R2, USB) stay recoverable with R. ADR-0008 Decision 1 (revised 2026-10-06) already escrows at creation and copies off-box at the start of the epoch; this ADR adds only the ordering rule (DR-A2-2).
- Ingest requires the single device stanza to open with that epoch's I_e (current or escrowed).
- **Rewrap is not revocation.** Changing recipients rewrites the header and keeps the file key. Only re-encryption under a fresh file key restores confidentiality after a key compromise.

### Decision 4 (in scope): truncation, random access and restore

- age STREAM plus CE §5.4 (valid lengths) and §5.5 (authenticate the final chunk before serving any middle chunk).
- Restore and admin tools write to a temporary file and expose output only after the final chunk and the record's SHA-256 both verify.

### Decision 5 (in scope): sender authentication and binding (refines OD-04)

- Each per-(device, file) metadata record is a **signed-note signed by the device**, inside the encryption, and **signed at sealing**. No HPKE Auth or PSK mode: Auth mode does not exist for PQ KEMs, and PSK breaks stock age.
- The signature binds:
  - content: `dedup_id`, `sha256`, true `size`, `padded_len`;
  - a **transport-neutral** object block: `h0_sha256`, `header_mac`, `ct_len`, `prefix_len`, `profile`, `stanzas`, or `null` for a dedup hit;
  - device and order: `device_id`, `device_seq`, `record_id`;
  - time: `recorded_at`.

  The R2 staging key and USB paths are **not** signed.
- **Ingest order:**
  1. **exact header match** with the signed `h0_sha256` (reject and alarm on mismatch, before any rewrap);
  2. profile and low-order checks;
  3. header MAC under the unwrapped file key;
  4. length binding and STREAM final chunk;
  5. SHA-256, dedup ID and size of the plaintext.

  Nothing is written to the catalog before all five pass.
- **Precondition:** the homelab accepts records only from device signing keys it admitted through a path Cloudflare cannot forge (SR-14). The mechanism is D3's (ADR-0014, OD-05). Until it exists, a malicious cloud enrolling a rogue device is a residual risk for OD-17.
- **Durable authority:** the homelab verifies each device signature once, at ingest. Its own signed receipt (which binds `record_sha256`) is the durable authority. Catalog rebuilds, fixity checks, provenance and late-USB policy never re-verify device signatures as authority.
- **Signature agility:** the record accepts any signed-note type registered for that device in the trust bundle. A hybrid or PQ type is reserved now. **Using a classical signature type in v1 is an owner risk acceptance** (DR-A2-3, OD-17), not a verified finding. Review it before 2030, or earlier on a credible signal of a cryptographically relevant quantum computer.

### Decision 6 (in scope, provisional): length hiding

- Padmé zero padding before encryption (same decision as DR-F3-1), provisional until F3-S1's owner-library leg.
- Dedup ID and SHA-256 are computed over unpadded bytes. Every cloud-visible size is the padded size.
- No compression in v1; `content_encoding` is reserved.

### Not yet decided (to be decided in Wave 2)

- **Metadata-record schema and encoding:** signed-note with one I-JSON line (provisional) vs deterministic CBOR. This follows A5 (ADR-0016) and the D2/E7 break-glass needs. Batching of records and the relation to manifests are A4's (ADR-0011).
- **Device signature algorithm** (Ed25519 in software vs ECDSA P-256 in hardware), and an optional symmetric MAC key: D3 (ADR-0014).
- **Confirmed parser limits** and the final error-code table: A2 with G2 fuzzing.
- **The A2-S1 phone result** that settles Decision 2.

### Consequences

- **Good:**
  - Stock age ≥ 1.3.0 (Go), typage and kage read every object as long as conformance holds.
  - PQ protection for transit and stored copies from the first byte (under Decision 2).
  - No temp ciphertext spool on phones (BUD-TMP).
  - Recipient changes never touch payloads.
  - Forgery, truncation and downgrade are rejected before any catalog write (A2-S4, earlier layout).
- **Bad / accepted trade-offs:**
  - 1,627 B per device object; about 4.8 KB per stored object with {X, R} and a kept h0 (0.1–1 % of bytes depending on mean size).
  - PQ costs 35–52 % throughput on 16–100 KiB objects on x86; phone cost unknown.
  - Custom stanza code on pre-1.0 Rust crates, with exact pins.
  - The KEM is anchored to an Internet-Draft, and CFRG has not fixed X-Wing's low-order behaviour.
  - Heirs need the record for the true size when padding is on.
  - Rewrap is not revocation.
  - Classical device signatures remain a stated risk until a hybrid or PQ type is rolled out.
- **Follow-up work:**
  - A2-S1 OL phone run.
  - A2-S4 re-run on the transport-neutral record. Cases: USB→R2 fallback with the same `record_id`; staging-key and USB-path substitution; a file-key holder rewrapping to the genuine I_e; the cloud registering a rogue device.
  - G2: CCTV and project vectors in CI; a snapshot-rollback case; parser fuzzing.
  - D2: the escrow ordering rule (off-box before publication).
  - D3: SR-14 admission and the signature type.
  - A8: PQ device restore keys.
  - H4: update data-model §6.1.

### Confirmation

- CI runs CCTV (all applicable vectors) and the project vectors (`spikes/A2-S3/vectors/`, moving to `docs/spec/vectors/`) against every decoder on every dependency bump (G2, ADR-0035).
- A negative test shows that no encoder path produces a mixed or extra stanza.
- The A2-S4 re-run passes with the transport-neutral record before Gate A.
- The A2-S1 OL result is recorded against BUD-HASH and BUD-BAT-S.
- The D2-S3 recovery drill decrypts sampled stored objects with R and stock age, and opens one transit object through the off-box I_e escrow.

## Pros and cons of the options

### 1. age v1, `mlkem768x25519` only

- Good, because the stanza is HPKE SealBase with MLKEM768-X25519, specified in C2SP age (C4, verified), and draft-ietf-hpke-pq-05 keeps its code point and sizes (C32).
- Good, because Go age ≥ 1.3.0 decrypts it natively and age(1) promises backward compatibility (C13, verified), and Rust↔Go/typage/kage interop is 853/853 (C25).
- Good, because rotating recipients rewrites only the header (C2, verified).
- Bad, because the Rust `age` crate has no PQ recipient, so the client writes its own stanza (C7, verified), and a decoder on plain `hpke` 0.14.1 fails two CCTV vectors (C22, verified).
- Bad, because of the header size (C6, verified) and the small-object CPU cost (C26).

### 2. age v1, X25519 now, PQ later

- Good, because of a 168 B header and the cheapest device cost (C6).
- Bad, because every transit copy recorded today stays exposed to a future quantum adversary, and a rewrap keeps the same file key (C2).

### 3. Mixed PQ + X25519

- Bad, because the spec says SHOULD NOT and Go age refuses (C5, verified); it gives no PQ protection.

### 4. HPKE + custom STREAM

- Good, because of full control.
- Bad, because there is no stock CLI, and Auth mode is unavailable for PQ KEMs (C10, verified).

### 5–8. Tink, libsodium, saltpack, OpenPGP

- Bad, because of no stock age-compatible CLI (Tink), no PQ (libsodium, saltpack), DH-only sender authentication (saltpack), or an unverified PQC draft status (OpenPGP). See the note's alternatives table.

## Evidence

| Claim | Source (primary) | Verdict |
|---|---|---|
| C4: `mlkem768x25519` = HPKE SealBase, MLKEM768-X25519, 1,120-byte enc, 32-byte body | C2SP age.md; hpke-pq editor's copy | Verified |
| C5: no mixing of PQ and classic recipients; Go age refuses | C2SP age.md; Go age v1.3.2 | Verified |
| C6: headers 1,627 / 3,184 / 168 B | Go age v1.3.2 measurements (M1/M2, reproduced by three skeptics) | Verified |
| C7: Rust `age` 0.12.1 has no `mlkem768x25519` | age-0.12.1 crate | Verified |
| C8: `hpke` 0.14.1 implements 0x647a on `x-wing` | hpke-0.14.1 crate | Verified |
| C2: recipient change rewrites only the header | C2SP age.md | Verified |
| C10/C11: no Auth mode for PQ KEMs; `hpke` panics | hpke-pq draft; X-Wing draft; hpke-0.14.1 | Verified |
| C12: age authenticates no sender | C2SP age.md; A2-S4 premise | Verified |
| C13: Go age ≥ 1.3.0 decrypts PQ; backward-compatibility promise | proxy.golang.org; age.1.ronn | Verified |
| C22: plain `hpke` decoder accepts low-order shares | x-wing 0.1.1; CCTV; A2-S3 | Verified |
| C9: a device-written R stanza cannot be verified at home | logic | Secondary only (beside C6 and C26, never alone) |
| C24: classical signatures adequate for v1 | reasoning | **Contested**: not relied on; handled as an owner risk acceptance |
| C21: "0.07–0.14 % overhead" | arithmetic | **Contested**: withdrawn; the note's per-mean-size table is used instead |
| C25–C28, C31, C32 | spikes A2-S1..S4; M3; hpke-pq -05 | New measurements and reads (not skeptic-reviewed) |

## Reversibility

- **One-way once real data is encrypted with production keys** (Gate A). Objects are kept forever, so the payload suite (age v1 STREAM, 64 KiB chunks) is permanent for every stored object. Changing it means re-encrypting the archive (about 28 h per 10 TB at 100 MB/s, arithmetic).
- Recipient types and placement can change by rewrap, and the record format can evolve by version. The device signature type can change through the trust bundle.
- Before Gate A: the A2-S1 phone result, the A2-S4 re-run, OD-06, DR-A2-2 and DR-A2-3 decided, and the project vectors in CI.

## Alternatives considered

- **Mixed PQ + X25519 headers:** forbidden by the spec's SHOULD NOT and refused by Go age; gives no PQ protection.
- **HPKE Auth mode for sender authentication:** not defined for PQ KEMs; `hpke` 0.14.1 panics.
- **HPKE PSK mode:** breaks stock age decryption.
- **Signing the R2 staging key in the record:** breaks transport-agnostic bundles (ADR-0001).
- **Accepting 1–N stanzas at ingest:** an unverifiable extra stanza could wrap the file key to an attacker.
- **Temp-file ciphertext spool:** unnecessary after A2-S2; costs BUD-TMP.
- **Tink, libsodium `secretstream`, saltpack, OpenPGP:** no stock age-compatible CLI or no PQ (see the note).

## Open questions

- Phone cost and how the A2-S1 rules aggregate (owner/H1; A2-S1 OL kit).
- Escrow ordering: off-box copy before the trust bundle is published (D2).
- The SR-14 device-key admission mechanism (D3, OD-05).
- CFRG's X-Wing low-order decision; byte equality of hpke-pq -05 vectors with -03 (A2, H1).
- 128-bit file key against quantum key search (F3, H1; NIST sources blocked).
- NIST IR 8547's EdDSA timeline for the review trigger (H1; primary blocked).
- Record encoding and schema (A2 after A5); manifest relation (A4).
- PQ device restore keys (A8, D2, D3).
- `mlkem768p256tag` hardware R: hardware support and a Rust decrypt path (D2, OD-08).
