# ADR-0012: Homelab at-rest posture and storage engine. Wave 1 part: rewrap-at-ingest posture (A′) and a plain content-addressed store of age objects on ZFS

- **Status:** Proposed. Partial draft covering the Wave 1 decisions: the posture (pending the owner's OD-07) and the knockout screen. The bake-off result, the OCFL wrapper, object naming (DR-A6-3), store immutability details and the A″ variant are to be decided in Wave 2 (see "Not yet decided"). The catalog is ADR-0013 (Wave 2).
- **Date:** 2026-10-06
- **Owner workstream:** A6
- **Decider:** the owner
- **Gate:** A
- **Supersedes / Amends:** None. Two settled-text readings need the owner's confirmation (see "Conflicts"). One requested change to the Proposed ADR-0008 Decision 1 wording (DR-A6-4).
- **Evidence:** [`docs/research/a6-homelab-storage-engine.md`](../research/a6-homelab-storage-engine.md) (Wave 1 final). Spikes, all run in a container on synthetic data:
  - `spikes/A6-S1/` (ran);
  - `spikes/A6-S3/` (pass; power cuts emulated with LazyFS, not real);
  - `spikes/A6-S4/` (pass);
  - `spikes/A6-S5/` (pass);
  - `spikes/A6-S6/` (pass).

  Kits: `docs/research/kits/A6-S1/` (ZFS cells), `A6-S2/` (bake-off), `A6-S3/` (VM power cut, ZFS disk full).
- **Traceability:** R-09, R-26, R-28, R-38, R-45, R-46, OPEN-2 (see `docs/research/traceability.md`)
- **Owner decisions:** OD-07; DR-A6-1, DR-A6-2, DR-A6-3, DR-A6-4 (H1 assigns OD numbers); input to OD-06, OD-08, OD-13, OD-16, OD-17
- **One-way door:** Yes, door #4 in `docs/research/one-way-doors.md` (homelab at-rest posture)

## Context and problem statement

`CLAUDE.md` leaves the homelab storage engine open: "prefer an existing, proven format over inventing one" (R-46, OPEN-2). The store must keep verified content and metadata forever (R-26), restorable by hash, scrubbable, rebuildable without the catalog and readable for decades. Pruning is a manual admin action only (R-28). An off-site copy must stay easy to add later (R-38). The homelab pulls, decrypts, verifies, stores and keeps the plaintext catalog (R-45, ADR-0001 §2).

The at-rest posture must be fixed before the first real family ingest (Gate A), because changing it later means migrating the whole store (one-way door #4). The ingest design in hand (CE §11, A3 F6, SR-04) decrypts every object before commit. So some private key that can open incoming objects is online at ingest in every posture (note C1, verified). The posture decides what that key can open, what a stolen box or a compromised ingest VM exposes, and which operations need the owner.

The Proposed ADR-0008 (D2) already assumes a homelab-written {X, R} stored header and rotating ingest keys I_e escrowed to {X, R}. This ADR is the A6 side of that design.

## Decision drivers

- R-26 keep forever; R-45 the homelab decrypts, verifies and stores; R-46 prefer a proven format; R-28 admin-only pruning; R-38 keep an off-site copy easy.
- CLAUDE.md "Data integrity over everything: backups must be verifiable and restorable".
- CLAUDE.md / ADR-0001 §2: privacy against outsiders, including the cloud. The admin may read everything (R-22).
- D1: SR-04 (verify before commit), SR-20 (no remote destruction; separately credentialed pruning), AR-07, AR-08 (compromised ingest VM).
- Budgets: BUD-INGEST, BUD-RESTORE, BUD-AUDIT, BUD-RECOVERY, BUD-TTS (`docs/research/budgets.md`).
- ADR-0008 (Proposed): Decision 1 (homelab-written {X, R}, escrow at creation); Decision 6 ("h0 is never kept in the clear on the same disks as a disk-resident I_e"); Decision 8 (real-key checks).
- `docs/spec/object-format.md` (A2, Draft): `stored-v1` header profile, `h0_sha256` and `header_mac` in the signed record.

## Considered options

Posture:

1. **A:** keep the received age ciphertext under one always-online homelab key.
2. **A′:** keep the received age payload, rewrap the header at ingest to an offline archive recipient X (plus R), and rotate the ingest keys.
3. **A″:** re-encrypt at ingest under a fresh file key to {X, R}.
4. **B:** plaintext content-addressed store on ZFS native encryption.
5. **C:** re-encrypt into a backup engine (restic/rustic, Kopia or PBS).

Engine: plain CAS of age objects; the same objects in an OCFL 1.1 storage root; restic format (plaintext in, or as a container for A′ ciphertext); Kopia; Borg 2; Borg 1.4; PBS; Plakar/Kloset; bupstash; git-annex.

## Decision

### Decision 1 (in scope; owner decides OD-07): posture A′, with three amendments

The recommended posture is A′. It is the posture in which neither the always-on ingest key nor someone holding the disks can open **stored content** of retired epochs. A6-S1 Probe 2 and A6-S6 show I_e opening 0/535 and 0/176 stored files. That holds only with amendment 1.

- Every stored content object and archived metadata record is a standard age v1 file. Its payload is byte-identical to the device upload. Its header is homelab-written with profile `stored-v1`: exactly {X, R}, uniform PQ or uniform X25519 (`object-format.md` §5; ADR-0008 Decision 2).
- **Amendment 1, h0 sealed.** The device header h0 is never stored in the clear. It is age-encrypted to {X, R} and referenced from the manifest. `h0_sha256` stays in the clear for cross-checks. Without this, h0 + stored payload + I_e opens every object of an open epoch: A6-S6 measured 176/176.
- **Amendment 2, rewrap verification.** See Decision 3.
- **Amendment 3, scope of the claim.** A′ does not protect metadata (the plaintext catalog) or derivatives, and it does not protect integrity against a writer (Decision 5). Under A′, kept derivatives are either encrypted to {X, R} or kept on the catalog's encrypted dataset.
- Ingest keys rotate (interval: ADR-0008) and are escrowed as ADR-0008 Decision 1 says. Each I_e is sealed to {X, R} at creation. Plaintext online copies are deleted after the drain bound. The sealed bundle stays online and opens only with X or R.

**If the owner picks A, B or C instead,** Decisions 2–5 still apply where they make sense: CAS layout, write-once, manifest. Decision 3 shrinks to the keyless audit under A. Under B the store holds plaintext on an encrypted dataset. Under C, Decision 2 is re-screened.

### Decision 2 (in scope): engine, a plain content-addressed store of age objects on ZFS

- **Layout (v0, as prototyped in `spikes/A6-S3/a6cas`; the one-page spec is a build-phase deliverable):**
  - `blobs/<aa>/<bb>/<name>.age`: one age file per unique content. `<name>` is the plain SHA-256 (A1) **pending DR-A6-3**, which may switch it to the SHA-256 of the stored bytes.
  - `records/<rr>/<record_id>.age`: archived device-signed metadata records.
  - `manifest/`: append-only, fsynced. One line per committed object with `stored_sha256`, stored size, epoch, commit time, a sealed-h0 reference and `h0_sha256`.
  - a device registry (to re-verify record signatures without the catalog), plus `tmp/`, `quarantine/` and a single-writer lock.
- **Commit order:** temp file with O_EXCL, fsync, rename, directory fsync, manifest append and fsync, catalog commit, then ACK. Recovery truncates torn manifest lines, quarantines blobs with no manifest line, and re-ingests from staging. A6-S3: 0 violations over 400 kills, 130 emulated power cuts and 100 disk-full trials. A6-S4: byte-identical catalog rebuilds.
- **Because:** none of the screened engines passes the knockout screen (note §F4):
  - restic fails restore by whole-file hash, as plaintext engine and as ciphertext container;
  - Kopia fails on independent reader and keyed IDs;
  - Borg 2 fails maturity;
  - PBS fails per-file ingest, independent reader and restore by hash;
  - Plakar fails on spec and maturity;
  - bupstash fails maturity;
  - git-annex fails library ingest.

  age v1 per object is a specified format with independent readers (A6-S5). This reading of "proven format" is DR-A6-2.
- The A6-S2 bake-off (Wave 2, OL) confirms or overturns this against an OCFL 1.1 variant and a restic comparator.

### Decision 3 (in scope; joint with D2, DR-A6-4): fixity and rewrap verification

- Record `stored_sha256` in the manifest and the catalog. A keyless audit compares them on a read-only VM.
  - Under A′ this proves only that the bytes have not changed since they were written. It does not prove that X opens them (note C14 is **contested**; C14r).
  - It is not tamper evidence (Decision 5).
- **Write-time self-check without X, before the ACK:**
  - re-read the file from disk;
  - check the `stored-v1` stanza set and the header MAC under the in-memory file key, and the payload hash;
  - check that X and R match the fingerprints pinned at the ceremony in the A-signed trust bundle;
  - recompute each stanza with an independent encoder from the same per-stanza randomness and compare.

  The catalog state is `rewrap_selfchecked`.
- **Attended X audit:** whenever the owner brings X online, unwrap a random sample of objects committed since the last pass, and eventually every object, setting `x_verified`. A failure stops ingest and alerts. Until an epoch is covered, keep its sealed h0 entries and the I_e escrow as the fallback path to the file key.
- **DR-A6-4 asks D2 to replace** ADR-0008 Decision 1's "verify X decryption of every rewrapped header" with this scheme, which A′ can actually perform. Sample size and cadence: A7 (ADR-0029) with D2 (ADR-0008 Decision 8).

### Decision 4 (in scope): ingest behaviour

- Verify by streaming; no plaintext temp file. Plaintext reaches disk only through a sandboxed metadata parser (D4).
- ACK only after the commit order in Decision 2 and the self-check in Decision 3.
- BUD-INGEST will probably need parallel verify and rewrap. The container prototype ran single-threaded at 76.6 MB/s on tmpfs (not budget evidence).
- Check catalog and store headroom before starting (A6-S3 disk-full lesson).

### Decision 5 (direction in scope; mechanisms to be decided in Wave 2): store integrity against a compromised writer

The homelab analogue of "devices can only append" (SR-20, AR-08):

- write-once objects after commit (read-only to the ingest credentials);
- frequent ZFS snapshots with holds that only a separate admin credential can release;
- prune only through the separately credentialed, verify-before-destroy step;
- a read-only audit VM;
- an off-box anchor for the manifest head (to be designed).

D4-S4 and the Wave 2 A6-S3 fault case "attacker rewrites object + manifest line" confirm it.

Hardening direction for AR-08, decided by D1/D4 in Wave 2: an **isolated verifier** (a minimal VM, or a non-exportable TPM or HSM for I_e) that decrypts, verifies and rewraps, and hands only ciphertext to the storage writer.

### Not yet decided (Wave 2)

- The bake-off result and the OCFL wrapper, including its layout extension (the prototype uses 0003).
- DR-A6-3, object naming: plain SHA-256, stored-bytes SHA-256, keyed names, or an encrypted store dataset.
- A″ per object (reversible; stored files are standard age to {X, R} either way).
- Self-hosted S3-compatible stores as the substrate.
- The engines not yet screened: Perkeep, Duplicacy, duplicity, rdedup, Bareos/Bacula, Tahoe-LAFS.
- Store-immutability mechanisms (Decision 5).
- The catalog engine and schema (ADR-0013).

### Consequences

- **Good:**
  - Stored content of retired epochs is unreadable by any online key or by someone holding the disks (with sealed h0).
  - Heirs need only age plus X or R, and a catalog export or the decrypted records.
  - ZFS scrubs, bit-rot audits and off-site copies need no key.
  - No engine index; restore by hash is a path lookup.
  - Device provenance stays byte-exact (the payload is unchanged; the upload can be rebuilt with X).
  - The catalog is a projection rebuildable from the store (A6-S4).
- **Bad / accepted trade-offs:**
  - The owner must bring X online for restores, catalog rebuilds, real-object restore drills and X audits. Unattended drills can only use canary objects.
  - I_e rotation duty (ADR-0008).
  - The rewrapped header cannot be proven decryptable without X; the scheme in Decision 3 narrows but does not remove the gap between write and the first X audit.
  - Metadata stays exposed to a compromised online VM and, unless the catalog key is off the box, to a thief.
  - Stored names reveal sizes and file presence to someone holding the disks (A6-S1 Probe 4) until DR-A6-3 is decided.
  - A plaintext gallery (OD-13) needs a decrypted mirror, which brings back an online read key.
  - New layout code. Crash safety is ours (A6-S3 covers it in the container only).
  - If OD-06 = PQ, stored objects have one CLI reader (Go age ≥ 1.3) and library readers (typage, kage).
- **Follow-up work:**
  - the one-page store spec;
  - the Rust rewrap with sealed h0 and the self-check (G2 tests, shared vectors with A2-S3 and D2-S2);
  - A6-S7 (sealed-h0 exposure and self-check fault cases);
  - A6-S2 kit amendments (restic ciphertext mode, files/s, sealed h0);
  - the X-audit tool;
  - Decision 5 mechanisms with D4.

### Confirmation

- **A6-S2 (OL, Wave 2):** BUD-INGEST, BUD-RESTORE (single file < 5 s), BUD-AUDIT (extrapolated to 10 TB, MB/s and files/s), RAM < 4 GB.
- **A6-S3-OL:** real VM power cuts ×10 and a ZFS full pool.
- **A6-S7 (CT, proposed):** with sealed h0, nothing on the box plus I_e opens stored objects. The self-check catches a wrong-X rewrap, a corrupted stanza and a mixed profile.
- **A6-S5 / D2-S3:** the one-page heir procedure restores byte-identical files (BUD-RECOVERY).
- **CI (G2):**
  - no stored header outside `stored-v1`;
  - no clear h0 in the store;
  - a keyless audit and an X-sample audit on every fixture store.
- **Every attended session:** X-audit pass rates recorded.

## Pros and cons of the options

### A′ (recommended)

- Good, because an online I_e opens no stored file (A6-S1 Probe 2: 0/535; A6-S6: 0/176). This rests on verified C1 and C2 plus measurements.
- Good, because a recovery recipient is written at ingest, so no later whole-store rewrite is needed. Probe 1 measured such a rewrite: every byte rewritten.
- Good, because the escrow of I_e opens only with offline keys (C29, verified, reworded).
- Bad, because h0 had to be sealed (C32, measured), and the rewrap can only be self-checked without X (C14 contested).
- Bad, because restores, drills and audits need the owner.

### A

- Good, because it is simplest, and a keyless audit is complete integrity evidence (C14r).
- Bad, because the always-on key opens everything stored (Probe 2: 535/535), and adding R later rewrites the store.

### A″

- Good, because there is no h0 to protect and the stored payload is unlinkable to cloud-retained ciphertext.
- Bad, because it costs about 1.5× rewrap CPU (Probe 1, tmpfs) and loses byte-exact upload provenance. Deferred to Wave 2; reversible.

### B

- Good, because restores, derivatives and a gallery are simplest.
- Bad, because unattended unlock is a read-everything key; ZFS leaves names and sizes unencrypted (C10, verified); raw-send bug history (C12, secondary); heirs need OpenZFS.

### C (restic)

- Good, because it is a proven, specified format with two implementations (A6-S5: restic ↔ rustic 176/176), and is keyless-checkable at file level (Probe 3).
- Bad, because one symmetric key reads everything and can be changed only by moving to a new repository (C4, C25, verified), and whole-file hash is not a lookup key (C5, verified).

## Evidence

| Claim | Source (primary) | Verdict |
|---|---|---|
| C1: a decrypting key is online at ingest in every posture (given SR-04) | CE §11; A3 F6; SR-04 | Verified |
| C2: every stanza wraps the same file key; header MAC and payload key derive from it; a rewrap leaves the payload valid | C2SP `age.md` | Verified |
| C3: an scrypt stanza must be alone | C2SP `age.md` | Verified |
| C4 / C25: restic single symmetric master key; #187 open since 2015 | restic `design.rst`; #187 | Verified |
| C5: restic CDC blobs; snapshot-scoped ingest | `design.rst`; rustic_core 0.13.0 | Verified |
| C6: Kopia IDs keyed (HMAC and BLAKE2 variants) | `sha_hashes.go`, `blake_hashes.go`, `hashing.go` | Verified |
| C7 / C28: Borg 2 "do not use for production"; 2.0.0b25 | Borg README; PyPI | Verified |
| C8, C9, C17: PBS CRC-only verify and AGPL; bupstash beta since 2022; Plakar 1.1.x since 2026-06 | PBS mirror; bupstash README; Plakar releases | Verified |
| C10: ZFS leaves names, sizes and dedup tables unencrypted; keyless scrub; thorough scrub master only (absent from 2.4.0–2.4.4) | OpenZFS man pages | Verified |
| C29: ADR-0008 escrow opens only with offline keys | ADR-0008 (Proposed) | Verified (reworded) |
| C30: PQ objects: Go age 1.3.1 176/176; age 1.1.1 and rage 0/176 | `spikes/A6-S5` | Verified (inference "no second reader" withdrawn) |
| C32: clear h0 + payload + I_e opens current-epoch objects 176/176 | `spikes/A6-S6` | Measured; not reviewed. It drives amendment 1 and is not used as support for A′ |
| C14: keyless audit is complete evidence under A′ | — | **Contested. Not used as support** |
| C19: 10 TB audit ≈ 27.8 h at 100 MB/s | arithmetic | Secondary only. Feasibility hint beside A6-S2, never sole support |

## Reversibility

- **Posture:** hard to reverse once real family data is stored. Moving to B or C means decrypting or re-encrypting the whole store; moving to A means dropping a property. A′ and A″ are interchangeable per object, because both produce standard age files to {X, R}.
- **Before Gate A, these must be true:**
  - the owner has decided OD-07, with no implicit default;
  - DR-A6-4 is agreed with D2;
  - the sealed-h0 form is specified;
  - the settled-text readings (Conflicts) are confirmed.
- **Engine and layout:** reversible until the first family ingest, and afterwards by a copy job. Object naming (DR-A6-3) is a rename pass.

## Alternatives considered

- **Attended batch verification** (devices encrypt to X, verification only when the owner is present): rejected, because it breaks BUD-TTS and the A3 receipt contract and leaves unverified ciphertext in the keep-forever store.
- **Kopia:** no independent reader found; keyed per-block IDs.
- **Borg 2:** "do not use for production". **Borg 1.4:** CLI only; no restore by hash.
- **PBS:** pxar snapshot streams; one implementation; CRC-only verify of encrypted chunks; AGPL. It is kept for VM-level backups of the catalog and service VMs.
- **Plakar/Kloset:** no format spec found; behaviour changes in 1.1.x. Re-screen in 2027.
- **bupstash:** beta, no release since 2022. Its put-only key model is borrowed.
- **git-annex:** no library ingest; plaintext only.
- **restic as a container for A′ ciphertext:** fails restore by hash, and adds a second password to the heir path.

## Open questions

- Sealed-h0 form and size; self-check encoder; A6-S7. Owner: A6 with A2 and G2. By Gate A.
- Rewrap-verification wording (DR-A6-4), X-audit cadence, epoch interval or drain-triggered rotation, TPM/HSM for I_e. Owner: D2, A7. By Gate A.
- Catalog dataset unlock and dataset layout. Owner: C5, D2. By Gate A.
- Store immutability mechanisms and the isolated verifier (AR-08). Owner: D1, D4. Wave 2.
- Bake-off numbers and parallel ingest. Owner: A6-S2. Wave 2.
- Unscreened engines and S3 substrates. Owner: A6. Wave 2.
- PQ readers in the doomsday kit (Go age plus typage or kage). Owner: A2, A7, D2-S3. By Gate A.
- Restore delivery by fresh re-encryption vs rewrap. Owner: A8 (ADR-0028).
- Immich read-only view. Owner: C8 (OD-13).
- PBS 4.x behaviour (sources blocked). Owner: H1.

## Conflicts

These are readings the owner must confirm. This ADR does not change settled text.

- **"Encrypted to the homelab public key" / "the owner holds the private key"** (CLAUDE.md, ADR-0001 §2, R-22). A′ means rotating I_e plus offline X, and R if OD-08 accepts it. Confirm together with ADR-0008's DR-D2-4. Rotation also touches the pinned-key one-way door (D3, Gate C).
- **"Backups must be verifiable and restorable."** Under A′, decryptability is proven by the write-time self-check and attended X audits, not online at any moment. If the owner requires the latter, A is the alternative.
- **"Prefer an existing, proven format"** is read as age v1 per object plus a one-page layout (DR-A6-2).
