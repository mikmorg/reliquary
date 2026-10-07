# ADR-0012: Homelab at-rest posture and storage engine. Wave 1 part: an offline archive key (built as rewrap-at-ingest, A′) and a plain content-addressed store of age objects on ZFS

- **Status:** Proposed. This is a partial draft covering the Wave 1 decisions: the posture (pending the owner's OD-07) and the knockout screen. These are to be decided in Wave 2 (see "Not yet decided"):
  - the bake-off result and the OCFL wrapper;
  - store-immutability mechanisms;
  - the header-sidecar option;
  - the unscreened engines.

  The catalog is ADR-0013 (Wave 2).
- **Date:** 2026-10-07
- **Owner workstream:** A6
- **Decider:** the owner
- **Gate:** A
- **Supersedes / Amends:** None. Two settled-text readings and one budget reading need the owner's confirmation (see "Conflicts"). It requests one change to the Proposed ADR-0008 Decision 1 wording (DR-A6-4).
- **Evidence:** [`docs/research/a6-homelab-storage-engine.md`](../research/a6-homelab-storage-engine.md) (final for Wave 1 after two review rounds). All spikes ran in a container on synthetic data:
  - `spikes/A6-S1/`: ran;
  - `spikes/A6-S3/`: pass. Power cuts were emulated with LazyFS, not real;
  - `spikes/A6-S4/`: pass;
  - `spikes/A6-S5/`: pass;
  - `spikes/A6-S6/`: pass.

  Kits: `docs/research/kits/A6-S1/` (ZFS cells), `A6-S2/` (bake-off), `A6-S3/` (VM power cut and ZFS disk full).
- **Traceability:** R-09, R-26, R-28, R-38, R-45, R-46, OPEN-2 (see `docs/research/traceability.md`)
- **Owner decisions:** OD-07; DR-A6-1 to DR-A6-5 (H1 assigns OD numbers). Input to OD-06, OD-08, OD-13, OD-16 and OD-17.
- **One-way door:** Yes, door #4 in `docs/research/one-way-doors.md` (homelab at-rest posture)

## Context and problem statement

`CLAUDE.md` leaves the homelab storage engine open, with the guidance "prefer an existing, proven format over inventing one" (R-46, OPEN-2). The store must:

- keep verified content and metadata forever (R-26);
- be restorable by hash, scrubbable, rebuildable without the catalog, and readable for decades;
- allow pruning only as a manual admin action (R-28);
- keep it easy to add an off-site copy later (R-38).

The homelab pulls, decrypts, verifies, stores and keeps the plaintext catalog (R-45, ADR-0001 §2).

The at-rest posture must be fixed before the first real family ingest (Gate A), because changing it later means migrating the whole store (one-way door #4). The ingest design in hand (CE §11, A3 F6, SR-04) decrypts every object before commit. So some private key that can open incoming objects is online at ingest in every posture (note C1, verified). The posture decides:

- what that key can open;
- what a compromised running host can read;
- which operations need the owner.

What a powered-off stolen box exposes depends mostly on how keys unlock after a power cut. That is a separate choice for C5/D2 (note §F1).

The Proposed ADR-0008 (D2) already assumes homelab-written {X, R} stored headers and rotating ingest keys I_e escrowed to {X, R}. This ADR is the A6 side of that design.

## Decision drivers

- **Settled requirements:** R-26 keep forever; R-45 the homelab decrypts, verifies and stores; R-46 prefer a proven format; R-28 admin-only pruning; R-38 keep an off-site copy easy.
- **CLAUDE.md:** "Data integrity over everything: backups must be verifiable and restorable".
- **CLAUDE.md and ADR-0001 §2:** privacy is against outsiders, including the cloud. The admin may read everything (R-22).
- **D1:**
  - SR-04: verify before commit;
  - SR-20: no remote destruction; pruning is separately credentialed;
  - AR-07;
  - AR-08: a compromised ingest VM, and the candidate separate receipt signer.
- **Budgets** (`docs/research/budgets.md`): BUD-INGEST, BUD-RESTORE, BUD-AUDIT, BUD-RECOVERY, BUD-TTS, BUD-SUPPORT.
- **ADR-0008 (Proposed):**
  - Decision 1: homelab-written {X, R}, escrow at creation;
  - Decision 6: I_e in RAM and never on snapshotted storage; h0 never in the clear next to a disk-resident I_e;
  - Decision 8: real-key checks.
- **`docs/spec/object-format.md` (A2, Draft):** the `stored-v1` header profile; `h0_sha256` and `header_mac` in the signed record; §6.1 hedged derivation.

## Considered options

**Posture:**

1. **A:** keep the received age ciphertext under one always-online homelab key.
2. **Offline archive key, built as A′:** keep the received age payload, rewrap the header at ingest to an offline archive recipient X (plus R), and rotate the ingest keys.
3. **Offline archive key, built as A″:** re-encrypt at ingest under a fresh file key to {X, R}.
4. **B:** a plaintext content-addressed store on ZFS native encryption.
5. **C:** re-encrypt into a backup engine (restic/rustic, Kopia or PBS).

**Engine:**

- a plain CAS of age objects;
- the same objects in an OCFL 1.1 storage root;
- the restic format, with plaintext in or as a container for ciphertext;
- Kopia;
- Borg 2;
- Borg 1.4;
- PBS;
- Plakar/Kloset;
- bupstash;
- git-annex.

## Decision

### Decision 1 (in scope; the owner decides OD-07): an offline archive key, built as A′, with four amendments

**The posture family is the one-way door:**

- Every stored content object and archived metadata record is a standard age v1 file.
- Its header is homelab-written with profile `stored-v1`: exactly {X, R}, either uniformly PQ or uniformly X25519 (`object-format.md` §5; ADR-0008 Decision 2).
- The always-on ingest key I_e protects only data in transit. It rotates, and it is escrowed as ADR-0008 Decision 1 states: each I_e is sealed to {X, R} **at creation** into the online bundle; plaintext online copies are deleted after the drain bound; the sealed bundle stays online and opens only with X or R.

**What it buys:**

- **Compared with A on the same unlock mechanism:** neither the always-loaded key nor a compromised ingest VM can open stored content. A6-S1 Probe 2 measured I_e opening 0/535 stored files, and A6-S6 0/176.
- **Against theft of a powered-off box:** it is better than A, B or C only when their key unlocks by a route the thief can also use, such as a key file on the box or Tang in the same house. With an off-premises or attended unlock, every posture protects stored content from theft equally.
- Scrubs, bit-rot audits and off-site copies need no key under A as well, so they are **not** reasons for this choice.

**Build it as A′:** keep the payload byte-identical to the device upload and rewrite only the header. Switch to **A″** (a fresh file key) for new objects if A6-S7 shows that amendments 1–2 cannot be built simply, or if the A2/D2 crypto review rejects the file-key-reuse argument (note §F3 item 9). Both produce the same kind of stored file, so the switch is reversible for new objects. Note §F1b compares the two.

**The amendments:**

- **Amendment 1, h0 sealed (A′ only).** The device header h0 is never stored in the clear. It is age-encrypted to {X, R} and referenced from the manifest, and `h0_sha256` stays in the clear. Without this, h0 + stored payload + I_e opens every object of an open epoch (A6-S6 measured 176/176).
- **Amendment 2, rewrap verification.** See Decision 3.
- **Amendment 3, scope of the claim.** The posture does not protect:
  - metadata (the plaintext catalog);
  - derivatives;
  - integrity against a writer (Decision 5).

  Kept derivatives are encrypted to {X, R}, or kept on the catalog's encrypted dataset.
- **Amendment 4, where X is used.** Restores, catalog rebuilds, X audits and rotations run only in a **separate, freshly booted environment with read-only store access**, or on the air-gapped ceremony machine with exported objects. **They never run on the ingest VM.** Otherwise a persistent attacker on the ingest VM captures X at the first attended session, and the posture collapses to A. A VM on the same Proxmox host protects against compromise of the ingest VM, not of the host.

**If the owner picks A, B or C instead,** Decisions 2, 4 and 5 still apply where they make sense (CAS layout, write-once objects, manifest), and Decision 3 shrinks:

- under A, to the keyless audit, which is then complete evidence;
- under B, the store holds plaintext on an encrypted dataset;
- under C, Decision 2 is re-screened.

### Decision 2 (in scope): engine, a plain content-addressed store of age objects on ZFS

- **Layout** (v0, as prototyped in `spikes/A6-S3/a6cas`; the one-page spec is a build-phase deliverable):
  - `blobs/<aa>/<bb>/<sha256>.age`: one age file per unique content, named by the **plain SHA-256** (A1). This is DR-A6-3 option (a), the default; option (b) adds an encrypted dataset;
  - `records/<rr>/<record_id>.age`: archived device-signed metadata records;
  - `manifest/`: append-only and fsynced. Each committed object has one line with `stored_sha256`, stored size, epoch, commit time, the sealed-h0 reference and `h0_sha256`;
  - a device registry, so record signatures can be re-verified without the catalog;
  - `tmp/`, `quarantine/` and a single-writer lock.
- **Commit order:**
  1. write a temp file with O_EXCL and fsync it;
  2. rename it, then fsync the directory;
  3. append the manifest line and fsync;
  4. commit to the catalog;
  5. ACK.

  Recovery truncates torn manifest lines, quarantines blobs that have no manifest line, and re-ingests from staging. A6-S3 found 0 violations over 400 kills, 130 emulated power cuts and 100 disk-full trials. A6-S4 produced byte-identical catalog rebuilds.
- **Redundancy:** the store dataset sits on a redundant vdev (mirror or raidz) or uses `copies=2`, or par2 is added. Detection without repair is not enough (note §F2). C5 decides which.
- **Because:** none of the **screened** engines passes the knockout screen (note §F4). K3 (restore by plain hash using only the store) is applied the same way to every candidate.
  - restic fails restore by whole-file hash for files ≥ 512 KiB, both as a plaintext engine and as a ciphertext container.
  - Kopia fails on an independent reader and on its keyed IDs.
  - Borg 2 fails on maturity.
  - PBS fails on per-file ingest, an independent reader and restore by hash.
  - Plakar fails on a format spec and on restore by hash (its maturity point is weak).
  - bupstash fails on maturity.
  - git-annex fails on library ingest.

  age v1 per object is a specified format with independent readers (A6-S5). This reading of "proven format" is DR-A6-2.
- The A6-S2 bake-off (Wave 2) confirms or overturns this against the OCFL 1.1 variant and restic as an out-of-screen comparator (DR-A6-1).

### Decision 3 (in scope; joint with D2 as DR-A6-4; the budget reading is DR-A6-5): fixity and rewrap verification

- **Keyless audit:** record `stored_sha256` in the manifest and in the catalog, and compare them on a read-only audit VM.
  - Under A′/A″ this proves only that the bytes have not changed since they were written. It does not prove that X opens them (note C14 is **contested**; C14r).
  - It is not tamper evidence (Decision 5).
- **Write-time self-check, before the ACK, without X:**
  - re-read the file;
  - check the `stored-v1` stanza set, the header MAC under the in-memory file key, and the payload hash. Under A″, also decrypt the whole payload with the fresh key;
  - check X and R against the fingerprints pinned at the ceremony;
  - recompute each stanza with an independent encoder.

  The state is then `rewrap_selfchecked`. **This gives no assurance against a compromised ingest VM.**
- **Deterministic h1, checked by an isolated verifier** (proposed; A2/D2 review):
  - derive the stanza encapsulation randomness from the file key with a dedicated HKDF label (consistent with `object-format.md` §6.1);
  - a verifier separate from the storage writer, holding I_e and a transient copy of h0, recomputes h1 byte for byte and compares it with the bytes on disk before the receipt is signed.

  This restores the re-verifying receipt signer that D1's AR-08 candidate relies on. The alternative is that the isolated verifier performs the rewrap itself (Decision 5).
- **Attended X audit:**
  - in each X session (amendment 4), unwrap a random sample of objects committed since the last pass, and eventually every object, setting `x_verified`;
  - a failure stops ingest and alerts;
  - until an epoch is covered, keep its sealed h0 and the I_e escrow as the fallback path to the file key.
- **Requests to other workstreams:**
  - DR-A6-4 asks D2 to replace ADR-0008 Decision 1's "verify X decryption of every rewrapped header" with this scheme.
  - DR-A6-5 asks H1 and A7 to define BUD-AUDIT's "full app-level audit" as a full keyless audit plus X-sampled coverage.
  - Sample size and cadence: A7 (ADR-0029) with D2.

### Decision 4 (in scope): ingest behaviour

- Verify by streaming, with no plaintext temp file. Plaintext reaches disk only through a sandboxed metadata parser (D4).
- ACK only after the commit order in Decision 2, the self-check and, once built, the verifier's h1 recompute (Decision 3).
- BUD-INGEST will probably need parallel verify and rewrap. The container prototype ran single-threaded at 76.6 MB/s on tmpfs (not budget evidence). D2-S2 did 1M PQ header rewraps in 186.0 s of wall time with 4 workers, in memory.
- Check catalog and store headroom before starting (A6-S3 disk-full lesson).
- **Placement:**
  - I_e only in tmpfs, never on held, snapshotted, replicated or vzdump-covered datasets (ADR-0008 Decision 6);
  - sealed h0 and the sealed online bundle may sit on the store dataset.

### Decision 5 (direction in scope; mechanisms to be decided in Wave 2): store integrity against a compromised writer

This is the homelab analogue of "devices can only append" (SR-20, AR-08):

- write-once objects after commit, read-only to the ingest credentials;
- frequent ZFS snapshots with holds that only a separate admin credential can release, with I_e never on those datasets;
- pruning only through the separately credentialed, verify-before-destroy step;
- a read-only audit VM;
- an off-box anchor for the manifest head (to be designed).

D4-S4 and the Wave 2 fault cases confirm it: "attacker rewrites object + manifest line" and "targeted miswrap by a compromised VM".

**Hardening direction for AR-08,** decided by D1/D4 in Wave 2: an **isolated verifier** (a minimal VM, or a non-exportable TPM or HSM for I_e) that decrypts, verifies, **rewraps and seals h0**, and hands only ciphertext to a storage writer that never holds I_e or file keys.

### Not yet decided (Wave 2)

- The bake-off result, and the OCFL wrapper with its layout extension (the prototype uses 0003).
- A′ vs A″, if A6-S7 or the crypto review triggers the switch. This is reversible for new objects.
- Header-sidecar layout: header and payload as separate files, so rotating X or adding a recipient rewrites KB per object instead of the whole store.
- Self-hosted S3-compatible stores as the substrate.
- The engines not yet screened: Perkeep, Duplicacy, duplicity, rdedup, Bareos/Bacula, Tahoe-LAFS.
- Store-immutability mechanisms (Decision 5).
- The catalog engine and schema (ADR-0013).

### Consequences

- **Good:**
  - A compromised running host and the always-on key cannot read stored content. A thief cannot either, unless the unlock is something the thief can trigger.
  - Heirs need only age plus X or R, and a catalog export or the decrypted records. Under PQ: Go age, or an older age with `age-plugin-pq`, or a library reader.
  - ZFS scrubs, bit-rot audits and off-site copies need no key. A shares this.
  - There is no engine index: restore by hash is a path lookup.
  - Under A′, device provenance stays byte-exact.
  - The catalog is a projection that can be rebuilt from the store (A6-S4).
- **Bad / accepted trade-offs:**
  - The owner must bring X online, in a separate environment, for restores, catalog rebuilds, real-object drills and X audits. Unattended drills can use only canary objects. Owner time is not measured (BUD-RESTORE, BUD-SUPPORT).
  - I_e rotation duty (ADR-0008).
  - Nothing online can prove that a stored header opens with X. Until the deterministic h1 and the isolated verifier exist, a compromised ingest VM can silently make new commits unrecoverable while receipts say "protected".
  - Rotating or replacing X rewrites the whole store unless the sidecar layout is adopted.
  - Metadata stays exposed to a compromised online VM. It is exposed to a thief too, unless the catalog's unlock is theft-resistant; same-house Tang is not.
  - Stored names reveal sizes and file presence to someone holding the disks (DR-A6-3 (a) accepted unless (b) is chosen).
  - A plaintext gallery (OD-13) needs a decrypted mirror, which brings back an online read key.
  - New layout code, so crash safety is ours (A6-S3 covered it in the container only).
- **Follow-up work:**
  - the one-page store spec;
  - the Rust rewrap with sealed h0, self-check and deterministic h1 (G2 tests; shared vectors with A2-S3 and D2-S2);
  - A6-S7;
  - A6-S2 kit amendments;
  - the X-audit tool and the separate X environment (with C8);
  - Decision 5 mechanisms (with D4).

### Confirmation

- **A6-S2 (OL, Wave 2):**
  - BUD-INGEST;
  - BUD-RESTORE: single-file read < 5 s;
  - BUD-AUDIT, read as DR-A6-5 decides: MB/s, files/s and the effect on ingest;
  - RAM < 4 GB.
- **A6-S3-OL:** real VM power cuts ×10 and a full ZFS pool.
- **A6-S7 (CT, proposed):**
  - with sealed h0, nothing on the box plus I_e opens stored objects;
  - the self-check catches a wrong-X rewrap, a corrupted stanza and a mixed profile;
  - the isolated verifier catches a targeted miswrap through the deterministic h1 recompute;
  - the cost of A′ vs A″.
- **A6-S5 / D2-S3:** the one-page heir procedure restores byte-identical files (BUD-RECOVERY).
- **CI (G2):**
  - no stored header outside `stored-v1`;
  - no clear h0 in the store;
  - a keyless audit and an X-sample audit on every fixture store.
- **Every attended session:** X-audit pass rates are recorded, and the session environment is confirmed not to be the ingest VM.

## Pros and cons of the options

### Offline archive key, built as A′ (recommended)

- Good, because an online I_e opens no stored file (A6-S1 Probe 2: 0/535; A6-S6: 0/176). This rests on verified C1 and C2 plus measurements.
- Good, because the recovery recipient is written at ingest, so no later whole-store rewrite is needed. Probe 1 measured such a rewrite: every byte rewritten.
- Good, because sealed h0 plus the escrowed I_e is an independent fallback path to each file key.
- Bad, because h0 has to be sealed (C32) and the rewrap can only be self-checked without X (C14 contested). A compromised ingest VM can miswrap new commits until the deterministic h1 exists.
- Bad, because restores, drills and audits need the owner and X in a separate environment.

### Offline archive key, built as A″ (sub-option)

- Good, because there is no h0 to protect, the age file-key rule is honoured literally, and the stored payload cannot be linked to cloud-retained ciphertext.
- Bad, because it costs about 1.4–1.5× the wall time of a rewrap (Probe 1, tmpfs), has no in-store fallback path if h1 is bad, and loses byte-exact upload provenance. Content provenance is still provable with X.

### A

- Good, because it is simplest, a keyless audit is complete integrity evidence (C14r), and a re-verifying receipt signer works.
- Bad, because the always-on key and a compromised host open everything stored (Probe 2: 535/535), and adding R later rewrites the store.

### B

- Good, because restores, derivatives and a gallery are simplest.
- Bad, because the unlock key reads everything, ZFS leaves names and sizes unencrypted (C10, verified), raw send has a bug history (C12, secondary), and heirs need OpenZFS.

### C (restic)

- Good, because it is a proven, specified format with two implementations (A6-S5: restic ↔ rustic 176/176), and it can be checked at file level without a key (Probe 3).
- Bad, because one symmetric key reads everything and can be changed only by moving to a new repository (C4, verified, from design.rst), and a whole-file hash is not a lookup key for files ≥ 512 KiB (C5, verified).

## Evidence

| Claim | Source (primary) | Verdict (round-2 tally) |
|---|---|---|
| C1: a decrypting key is online at ingest in every posture (given SR-04) | CE §11; A3 F6; SR-04 | Verified |
| C2: every stanza wraps the same file key, and the header MAC and payload key derive from it, so a rewrap leaves the payload valid | C2SP `age.md` | Verified |
| C3: an scrypt stanza must be alone | C2SP `age.md` | Verified |
| C4: restic uses one symmetric master key, changed only by moving to a new repository | restic `design.rst` | Verified (#187, C25, is corroboration only) |
| C5: restic CDC blobs for files ≥ 512 KiB; snapshot-scoped ingest | `design.rst`; rustic_core 0.13.0 | Verified |
| C6: Kopia IDs are keyed (HMAC and BLAKE2 variants) | `sha_hashes.go`, `blake_hashes.go`, `hashing.go` | Verified |
| C7: Borg 2 "do not use for production"; 2.0.0b25 | Borg README; PyPI | Verified (time-sensitive) |
| C8, C9, C17: PBS CRC-only verify and AGPL (3.2.4 mirror); bupstash beta since 2022; Plakar facts | PBS mirror; bupstash README; Plakar releases; Go proxy | Verified. The Plakar maturity point is weak; K2/K3 carry its knockout |
| C10: ZFS leaves names, sizes and dedup tables unencrypted; keyless scrub; thorough scrub on master only | OpenZFS man pages | Verified |
| C30: PQ objects: Go age 1.3.1 176/176; age 1.1.1 and rage 0/176 natively | `spikes/A6-S5` | Verified (measured facts). Reader inference corrected with C33 (`age-plugin-pq`) |
| C32: clear h0 + payload + I_e opens current-epoch objects 176/176 | `spikes/A6-S6` | Measured; not tallied. It drives amendment 1 and is not used as support for the posture |
| C14: a keyless audit is complete evidence under A′ | — | **Contested. Not used as support** (C14r used instead) |
| C29: ADR-0008 escrows *retired* keys and deletes *every* online copy | — | **Contested as worded. Not used.** C29r (escrow at creation; the sealed bundle stays online) is read directly from ADR-0008 and supports only the escrow wording |
| C19: 10 TB audit ≈ 27.8 h at 100 MB/s | arithmetic | Secondary only. Never BUD-AUDIT evidence (DR-A6-5) |

## Reversibility

- **Posture family:** hard to reverse once real family data is stored. Moving to B or C means decrypting or re-encrypting the whole store, and moving to A means giving up a property. A′ and A″ are interchangeable for new objects.
- **Before Gate A, these must be true:**
  - the owner has decided OD-07, with no implicit default;
  - DR-A6-4 and DR-A6-5 are answered;
  - the sealed-h0 form is specified, or A″ is chosen;
  - the settled-text readings (Conflicts) are confirmed;
  - C5/D2 have chosen the catalog unlock.
- **Engine and layout:** reversible until the first family ingest, and afterwards by a copy job. Object naming (DR-A6-3) can be changed by a rename pass.

## Alternatives considered

- **Attended batch verification** (devices encrypt to X; verification only when the owner is present): rejected. It breaks BUD-TTS and the A3 receipt contract, and leaves unverified ciphertext in the keep-forever store.
- **Ciphertext-hash object names** (DR-A6-3 option d): withdrawn. Sizes still leak, it breaks path = hash idempotency, and K3 and A6-S3/S4 would have to be redone.
- **X held online in non-exportable hardware as a verification oracle** (DR-A6-4 option d): classic profile only, and it exposes a decryption oracle to a compromised host.
- **Kopia:** no independent reader found; keyed per-block IDs.
- **Borg 2:** "do not use for production". **Borg 1.4:** CLI only, and no restore by hash.
- **PBS:** pxar snapshot streams; one implementation; CRC-only verify of encrypted chunks; AGPL. It is kept for VM-level backups of the catalog and service VMs.
- **Plakar/Kloset:** no format spec found; MAC-addressed. Re-screen in 2027.
- **bupstash:** beta, with no release since 2022. Its put-only key model is borrowed.
- **git-annex:** no library ingest; plaintext only.
- **restic as a container for ciphertext:** fails restore by hash, and adds a second password to the heir path.

## Open questions

| Question | Owner | By when |
|---|---|---|
| Sealed-h0 form, self-check encoder, deterministic h1 derivation, and the A′/A″ switch (A6-S7) | A6, A2, G2 | Gate A |
| File-key reuse argument | A2, D2 | Gate A |
| Rewrap-verification wording (DR-A6-4); X-audit cadence; epoch interval or drain-triggered rotation; TPM/HSM for I_e | D2, A7 | Gate A |
| BUD-AUDIT meaning (DR-A6-5) | H1, A7, owner | Gate A |
| Separate X environment, and owner time per restore | D2, A8, C8 | Gate A (requirement); Wave 2 (timing) |
| Catalog dataset unlock (off-premises or attended for theft resistance), dataset layout, pool redundancy | C5, D2 | Gate A |
| Store immutability mechanisms, isolated verifier, separate receipt signer (AR-08) | D1, D4 | Wave 2 |
| Bake-off numbers and parallel ingest | A6-S2 | Wave 2 |
| Unscreened engines, S3 substrates, header-sidecar layout | A6 | Wave 2 |
| PQ readers in the doomsday kit (Go age v1.3.2, `age-plugin-pq`, one non-Go reader) | A2, A7, D2-S3 | Gate A |
| Restore delivery by fresh re-encryption vs rewrap | A8 (ADR-0028) | Gate C |
| Immich read-only view | C8 (OD-13) | Wave 2 |
| PBS 4.x behaviour (primary sources blocked) | H1 | Before C8 relies on PBS |

## Conflicts

These are readings the owner must confirm. This ADR does not change settled text.

- **"Encrypted to the homelab public key" and "the owner holds the private key"** (CLAUDE.md, ADR-0001 §2, R-22). This posture means rotating I_e plus an offline X, and R if OD-08 accepts it. Confirm together with ADR-0008's DR-D2-4. Rotation also touches the pinned-key one-way door (D3, Gate C).
- **"Backups must be verifiable and restorable."** Under this posture, decryptability is proven by the write-time self-check, the verifier's h1 recompute (once built) and attended X audits, not online at any moment. If the owner requires the latter, A is the alternative.
- **BUD-AUDIT "full app-level audit"** (a proposed budget, owned by H1) and **PLAN A7-S4** (an unattended real-object drill). Both are met only in a weaker reading (DR-A6-5).
- **"Prefer an existing, proven format"** is read as age v1 per object plus a one-page layout of our own (DR-A6-2).
