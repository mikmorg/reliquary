# ADR-0008: Key hierarchy, custody and recovery. Wave 1 part: homelab-written recovery recipient, SLIP-39-split recovery key, two-bundle backup, ingest-key custody

- **Status:** Proposed. Partial draft covering the Wave 1 decisions. Holders, the drilled recovery path, time-delayed release, PQ signatures and emergency ingest rotation are to be decided in Wave 2 (see "Not yet decided").
- **Date:** 2026-10-06
- **Owner workstream:** D2
- **Decider:** the owner
- **Gate:** A (recovery recipient, PQ choice, rotation mechanics). Gate C for the drilled recovery path, the holders and the kit pin.
- **Supersedes / Amends:** None proposed. ADR-0001 §2 says content is "encrypted to the homelab public key (e.g. X25519 / age)". Under Decision 1, devices still encrypt to one homelab key at a time (the current ingest key). The owner must confirm that this reading holds under OD-07/OD-08; if it does not, this ADR must amend ADR-0001 §2. Decision 3 changes **who can decrypt** compared with the CLAUDE.md trust model (R-22). That needs the owner's explicit amendment (DR-D2-4; see "Conflicts").
- **Evidence:** `docs/research/d2-key-hierarchy-custody-recovery.md` (Wave 1 final). Spikes:
  - `spikes/D2-S1/` (emulated, not a real YubiKey), with its kit `docs/research/kits/D2-S1/`;
  - `spikes/D2-S2/` (ran; pass);
  - kit `docs/research/kits/D2-S3/` (kit-ready; no human result).

  Normative drafts: `docs/security/key-inventory.md`, `docs/security/key-ceremony-runbook.md`.
- **Traceability:** OPEN-3b, Q1-2a, OPEN-3c, Q1-2b (trigger only), R-19, R-20, R-22, R-26 (see `docs/research/traceability.md`)
- **Owner decisions:** OD-08, coupled with OD-06 (A2) and OD-07 (A6); DR-A2-2 (joint); new DR-D2-1, DR-D2-2 (to OD-17), DR-D2-3, DR-D2-4
- **One-way door:** Yes, door #3 in `docs/research/one-way-doors.md` (recovery recipient in the key hierarchy)

## Context and problem statement

ADR-0001 encrypts everything on the device "to the homelab public key". If that one key is lost, or the owner who holds it dies, the whole keep-forever archive (R-26) is lost. CLAUDE.md puts data integrity over everything, and PLAN §E7 asks for a succession path that lets an heir read the archive without Reliquary.

Adding a recovery recipient later is costly:

- it needs the ingest key online and a custom header-rewrap tool (note C14; D2-S2: 1M PQ header rewraps took 186 s of CPU);
- it cannot reach copies outside the store.

The hierarchy must therefore be fixed before the first real family byte is encrypted (Gate A).

The decision is constrained by three things:

- **age's format:** multiple recipients are native (C1); PQ and classic recipients must not share a header (C2); a passphrase stanza must be alone in its header (C3).
- **D1's requirements:**
  - pinned trust bundle (SR-02, SR-27);
  - device-key admission independent of the Worker (SR-14);
  - the dedup secret never in the clear through Cloudflare (SR-15);
  - no trust-forging key in the Worker (SR-23);
  - update anti-rollback (SR-29).
- **A2's envelope and A6's at-rest posture:** the recommended A′ rewraps headers at ingest.

## Decision drivers

- R-26 keep forever; data integrity over everything; restore is first-class.
- R-20 devices cannot read backups. R-22 the admin can decrypt everything (affected; see Conflicts).
- SR-02, SR-14, SR-15, SR-23, SR-27, SR-29 (D1).
- **BUD-RECOVERY:** a non-author recovers 10 named photos from the doomsday kit in ≤ 2 h.
- **BUD-INGEST:** ≥ max(100 MB/s, 2 × downlink). By arithmetic this implies about 90 header unwraps/s (note §F4).
- **BUD-TTS:** ingest must not stall for long after a power cut.
- **BUD-SUPPORT:** ≤ 2 h per month of owner time.
- **A2-S1's local rule:** a PQ device header ≤ 3 KB per object.

## Considered options

1. Single homelab key (ADR-0001 as written).
2. **Ingest key on device headers; the homelab writes {archive X, recovery R} on stored headers; ingest keys escrowed to {X, R} when created** (P1 plus escrow).
3. Devices write {ingest, R} (P2), with or without disclosed encapsulation randomness (P3).
4. Two-level: stored headers carry {X} only, and X is sealed to R.
5. Backup of the recovery key:
   - SLIP-39 over a passphrase that wraps R;
   - SLIP-39 over R's seed;
   - group SLIP-39;
   - age-plugin-sss;
   - extra YubiKeys;
   - a paper QR plus a memorised passphrase.
6. Online-key custody: plain file; passphrase; systemd-creds; Proxmox vTPM; physical TPM; Tang; YubiKey; HSM.

## Decision

### Decision 1 (in scope; joint with A2's DR-A2-2): recipient placement and escrow

- **Devices** encrypt every content object and metadata record to the current ingest recipient **I_e only**. Under PQ the device header is 1,627 B, measured in D2-S2 and A2-S1.
- **The homelab** rewraps every stored header to **{X, R}** at ingest. The payload is never touched (C14).
  - Under A6 posture A′ this is part of ingest.
  - Under posture A, a rewrap is added only to include R.
  - Under plaintext postures, R protects the volume key instead (Decision 5).
- **Escrow at creation.** Each I_e is sealed to {X, R} into the online bundle when it is created. The bundle is copied off-box (to the doomsday USB) at the start of the epoch. Online copies of I_e, including those in snapshots and replicas, are deleted after the drain bound (A3 DR-A3-3).
- **Reasons:**
  - The homelab cannot verify an R stanza written by a device (A2 C9).
  - Two PQ stanzas (3,184 B) fail A2-S1's local rule. The size is measured; note C4 is contested only for its percentage.
  - The case for device-written R (note C21) is **contested** and is not relied on.
  - Escrow keeps late USB bundles readable, by the admin with X and by heirs with R. With the off-box copy it also keeps staged-only objects readable if the homelab dies mid-epoch.
- **Residual gap:** objects staged under I_e before the epoch's bundle copy has left the box (AR-07). The owner may add device-written R (P2) for defence in depth. If so, the homelab-written {X, R} stays authoritative.
- **Production rewrap tool requirements:**
  - drop the I_e stanza;
  - wrap through the label-enforcing path and refuse any mix of PQ and classic stanzas (note C27: a raw `Recipient.Wrap` bypasses Go age's check, and the D2-S2 spike tool did exactly that);
  - write atomically or as a new version;
  - verify X decryption of every rewrapped header.

### Decision 2 (in scope; coupled to OD-06): algorithms

- If OD-06 = PQ (recommended by A2 and D2), **R and X are `mlkem768x25519`**, and every stanza on any one header is PQ (C2).
- R must be `mlkem768x25519` rather than tagpq, so that heirs can use upstream tools.
- The device-side encoder route for I_e is **A2's decision**: a native Rust X-Wing stanza, `age-plugin-pq` over the plugin protocol (C22), or Rust's native `tagpq` recipient (C23). Note C5 is contested; only its narrow absence (no native `mlkem768x25519` in Rust age 0.12.1) is used.
- If OD-06 = classic: X25519 throughout, YubiKey recipients become possible, and D2-S1 applies.
- Signatures stay Ed25519. The trust bundle carries algorithm IDs so a PQ signature can be added later (Wave 2).

### Decision 3 (in scope; holders open): recovery key R and its offline backup

1. R is generated on the air-gapped ceremony machine (`age-keygen -pq`) and reduced to its identity line.
2. W is 128 bits, computed as SHA-256(OS CSPRNG ‖ dice), truncated, by a short ceremony script using the python-shamir-mnemonic library. W never appears in argv or logs (runbook §2, §3.2).
   - **Why 128 bits:** a uniformly random 128-bit secret behind scrypt is out of reach of classical search, and generic quantum search would still need on the order of 2^64 sequential evaluations of a memory-hard function. This is reasoning only; the NIST sources were blocked.
   - 256 bits would mean 33-word cards instead of 20, which counts against BUD-RECOVERY.
3. R is wrapped with `age -a -p` under W: a 422 B armored file (C7; C25).
4. W is split with **SLIP-39: 2-of-3 by default, extendable, no SLIP-39 passphrase** (C8).
5. Each card carries:
   - the 20 words;
   - a QR of the armored file;
   - R's fingerprint and the trust-bundle digest (formats per D3);
   - a one-page instruction.

   R's fingerprint is also printed in the runbook and on the kit. The heir checks that it matches on at least two cards.
6. The wrapped file is also on the doomsday USB.
7. **Recovery** uses unmodified upstream tools: `shamir recover`, then `age -d`.
   - The kit ships Go age **v1.3.2** (one pinned version for the ceremony and the kit), plus `age-plugin-pq` as a fallback (C22).
   - It also ships a recovery USB, so the unhardened shamir tool (C9) runs in an ephemeral, offline environment. D2-S3 measures this packaging.
8. Holders and the final k-of-n follow E7-S1 (Wave 2), before the production ceremony.

### Decision 4 (in scope): admin root key A, the trust bundle and anti-rollback

- **A** is an offline Ed25519 key, kept on two offline media by the owner.
- **The trust bundle** is signed by A and contains:
  - the I_e, R and (if pinned) X recipients;
  - the receipt key K-04;
  - a **monotonic epoch**;
  - a **not_after** date;
  - a **revoked[]** list;
  - algorithm IDs.

  Its digest is what kits and QR codes pin (SR-02, SR-27).
- **Device rules:**
  - devices refuse bundles with a lower epoch;
  - a fresh install fetches and verifies a current bundle before its first upload;
  - devices name the epoch in their signed manifests, so the homelab can quarantine objects sent under a revoked key.

  The encoding, and what a device does with an expired bundle, belong to D3.
- By default **A is not reachable from R** (DR-D2-3, the read-only heir bundle).
- **The update-signing key (D5) is ranked Tier 0.** A signed update can change pins, so for future uploads it is as powerful as A, and no in-app pin rule can stop a malicious signed update. Its custody is D5's (ADR-0015).

### Decision 5 (in scope): two backup bundles

| Bundle | Contents | Sealed to | Where it is sealed |
|---|---|---|---|
| **Offline** | X (plus A only if DR-D2-3 = full admin) | R | Only on the air-gapped ceremony machine |
| **Online** | Every S_e, every I_e (escrowed at creation), the volume and catalog keys (K-06, K-07) | {R, X} | By the homelab; copied off-box at each epoch start, each S_e rotation, and at the annual holder check (cadence: E7/C8) |

- The online bundle never contains Tier-0 material.
- Account recovery codes are not in either bundle by default (E7, DR-D2-3).

### Decision 6 (in scope; posture-conditional): ingest-key custody and ingest hardening

- **I_e** is a software PQ identity held **in RAM**:
  - under A′, loaded unattended at boot, preferably through clevis/Tang into tmpfs, with a manual fallback;
  - under plaintext postures, unlocked with the store volume.
- **Never** on snapshotted, replicated or vzdump-covered storage. **Never** on a Proxmox vTPM (C10). Never on a YubiKey under PQ (note C11 is contested overall, but its YubiKey part was upheld by all three lenses and by D2-S1's reading of the crate).
- **Requirement on A6:** h0 is never kept in the clear on the same disks as a disk-resident I_e. Acceptable forms:
  - h0 sealed to X;
  - h0 kept only as a MAC or digest;
  - I_e kept off disk.
- **Requirement on A2/A3: header-shape check before any unwrap.** Exactly one stanza of the chosen type, under about 1.7 KB, and nothing else; anything else is rejected and alerted. Go age otherwise accepts up to 1,024 stanzas in a 2 MiB header (C27). Software unwrap is far above the rate BUD-INGEST implies (C12), but only for well-formed headers.
- **Epoch interval:** yearly and after any suspected compromise. This is an owner-tunable default with no primary source.
- **X** is admin-held: a passphrase-wrapped file, optionally wrapped at rest by a YubiKey (a classic at-rest wrap is acceptable) or by a Mac Secure Enclave `--pq` key (C24). It is brought online only for restores, rebuilds, rotations and drills.

### Decision 7 (in scope; trigger conditional): dedup secret

- S_e is 32 CSPRNG bytes per epoch, generated at the homelab. K_e = HKDF(S_e, "reliquary/v1/dedup-id-key") (A1). It is never derived from R or A.
- Delivery follows each enrollment path as D3 designs it (SR-15, SR-14). A clear S_e on a USB stick must be sealed, or deleted after first use.
- Whether delivery is compatible with near-zero enrollment is **open**. Note C16 is contested and is not relied on.
- The rotation trigger is DR-D2-1: every revocation for loss, theft, compromise or estrangement, **conditional on DR-A1-1 = construction B and A1-S2**. Otherwise rotate on confirmed compromise only.

### Decision 8 (in scope): drills and audits

- **Human drills** use throwaway drill keys only (D2-S3).
- **Annual holder check:** each holder confirms the card exists and is readable. No share is reconstructed, and no card is sent anywhere.
- **Real-key check:** at Gate C, after any holder change, and at least every 3 years (an owner-tunable default). The first one runs within the first months after the first family ingest (proposal).
  - It runs only on the owner-controlled air-gapped ceremony image. It is therefore **exempt** from the rotation rule below.
  - It includes an **R-stanza audit:** unwrap with R a random sample of stored headers, every I_e escrow entry, and both bundles; verify the MACs; record the pass rates.
- **Any other real-card recovery while the owner is alive** (holder- or heir-initiated, or any use on a networked machine) triggers a new R and a store rewrap.

### Consequences

- **Good:**
  - Heirs can read the archive with R, the disks and upstream age on a recovery USB.
  - Every stored R stanza is written at home and audited.
  - The device header passes A2-S1.
  - The ingest key is disposable, and escrow covers late bundles and staged objects.
  - Tier-0 keys never touch an online machine.
  - Rollback of the trust bundle is refused.
- **Bad / accepted trade-offs:**
  - Any k holders with access to the ciphertext can read everything (AR-D2-1). This needs DR-D2-4.
  - There is no time-delayed release in v1 (AR-D2-2; a choice).
  - A residual staged window remains before each epoch's bundle copy leaves the box (AR-07).
  - Replacing R or X needs a store-wide rewrap and revokes nothing already copied (C14).
  - The ceremony relies on an unhardened SLIP-39 tool; mitigated by the air gap and dice entropy (C9).
  - The stored PQ form costs about 4.8 KB per object including h0 (A2 §F2).
  - The update key is as powerful as A.
- **Follow-up work:**
  - the production rewrap/escrow tool (A6/G2);
  - the R-stanza audit tool;
  - the header-shape rule and fuzz case (A2/A3/G2);
  - the trust-bundle encoding (D3);
  - D2-S3 kit amendments and the human drill;
  - a second SLIP-39 implementation for cross-checks;
  - standby ingest keys.

### Confirmation

- **D2-S2** (ran; pass): recovery with upstream tools after the ingest key was destroyed; rewrap cost measured.
- **D2-S3** (FM; kit-ready): BUD-RECOVERY with the amended kit (PQ + 128-bit, armored, QR step, recovery USB, fingerprint cross-check). This is the Gate C confirmation.
- **G2:**
  - CCTV hybrid vectors;
  - a cross-implementation round trip;
  - a CI test that no mixed PQ/classic header is ever produced, **including by the rewrap tool**;
  - a header-shape fuzz case;
  - a test of the R-stanza audit tool.
- **Every real-key check:** the R-stanza audit pass rates, recorded in the ceremony log.

## Pros and cons of the options

### 1. Single homelab key

- Good, because it is the simplest.
- Bad, because losing the key or the owner loses everything, and adding R later cannot reach staged or USB copies (C14).

### 2. P1 plus escrow at creation (chosen)

- Good, because every R stanza is homelab-written and auditable, and the device header is 1,627 B (measured).
- Good, because escrow covers late bundles and, with the off-box copy, staged objects, at a cost per epoch.
- Bad, because a residual staged window remains, it depends on a homelab rewrap, and k holders can read in-flight objects of the current epoch.

### 3. P2 / P3 (device-written R)

- Good, because it covers the staged window on its own.
- Bad, because the stanza cannot be verified (A2 C9), the header is 3,184 B, and the justification (C21) is contested. P3 needs a custom crypto review.

### 4. Two-level ({X} only; X sealed to R)

- Good, because replacing R is a re-seal, and headers are smaller.
- Bad, because the heir depends on sealed copies of X surviving. Kept as the fallback.

### 5. Backup method

- SLIP-39 over W (chosen): upstream tools, 20 words, checksummed (C6, C8 verified; C25).
- Group SLIP-39 (owner 1-of-1 or family 2-of-3): the owner can recover alone, but the owner card is a single point of exposure. This is an OD-08 option B.
- SLIP-39 of R's seed: 33 words and a non-stock bech32 step (D2-S2).
- age-plugin-sss: experimental, no Windows builds, a 6,548 B PQ header (D2-S2; C13 contested on stanza structure only).
- YubiKeys: classic only.
- Paper QR plus a memorised passphrase: a single point of failure.

### 6. Custody

- Proxmox vTPM: excluded (C10).
- YubiKey: impossible under PQ.
- HSM: out of scope.
- Software key in RAM through Tang or manual unlock (chosen): unwrap is far above the needed rate (C12), given the header-shape check.

## Evidence

Verdicts are the computed tally from the D2 note. Contested claims appear only beside verified support.

| Claim (note ID) | Source (primary) | Verdict |
|---|---|---|
| C1 Multiple recipients are native; unrecognised stanzas ignored | C2SP age spec (S1); M1; D2-S2 | Verified |
| C2 No mixing of PQ and classic on one header; Go age refuses | S1, S2, S4; D2-S2 | Verified |
| C3 scrypt must be the only stanza | S1 | Verified |
| C6 The upstream SLIP-39 → age chain works | M1; M2; D2-S2; S7, S8 | Verified |
| C7 Wrapped identity 260 B binary / 422 B armored | M1; M2 | Verified |
| C8 SLIP-39 sizes, extendable sets, unverifiable passphrase | S7 | Verified |
| C9 The SLIP-39 reference tool is unhardened | S8 | Verified |
| C10 A Proxmox vTPM gives no real security benefit | S13 | Verified |
| C12 Software unwrap: thousands per second | M1; D2-S2 | Verified |
| C14 A recipient change rewrites only the header; nothing already copied is revoked | S1, S4, S19 | Verified |
| C4 Header sizes 1,627 / 3,184 / 168 / 266 B (sizes undisputed; the percentage is wrong) | M1; D2-S2; A2 §F2 | **Contested**: only the measured sizes are used, beside D2-S2 and A2-S1 |
| C5 Rust age has no native `mlkem768x25519` (the consequences are refuted) | S5 | **Contested**: only the narrow absence, beside C22/C23 |
| C11 YubiKey PIV is classic only; the "no PQ hardware" part is refuted | S9, S26 | **Contested**: the YubiKey part is used beside D2-S1's crate reading and C2 |
| C13 age-plugin-sss is experimental; stanza structure corrected | S11; D2-S2 | **Contested**: the rejection rests on the D2-S2 measurement plus undisputed maturity facts |
| C16 Sealed S_e is compatible with instant enrollment | internal | **Contested**: not used |
| C18 NIST IR 8547 dates | secondary | **Contested**: not used |
| C21 "Devices must write R" | internal | **Contested**: not relied on |
| C22–C27 age-plugin-pq; Rust tagpq; age-plugin-se `--pq`; the M2 chain; 128-bit file key; Go age header limits and the label-check bypass | S4, S5, S26, S1; M2; M3 | New in synthesis; not tallied; each appears beside verified claims |

## Reversibility

- **Adding R later** is a one-way door (door #3). It needs the ingest key online and a custom rewrap, and cannot reach copies outside the store. It must be decided before Gate A.
- **Moving from P1 to P2** later is a client update and is reversible.
- **Holders** change by re-issuing an extendable card set. Revoking ≥ k exposed cards needs a new R and a rewrap.
- **Classic to PQ later** leaves existing objects harvestable.
- **The bundle split, ingest custody and trust-bundle fields** can be changed before Gate C. The trust-bundle pin becomes hard to change once the first kit ships (D3, Gate C).

## Alternatives considered

- **Mixed PQ ingest with classic recovery:** the spec says SHOULD NOT and Go age refuses (C2).
- **Recovery recipient written only by devices:** cannot be verified, and fails A2-S1.
- **Destroying ingest keys without escrow:** late bundles would be lost, or would need the share holders.
- **Deriving S_e from R or A:** an offline root would come online at every rotation, and key purposes would mix.
- **Proxmox vTPM custody:** excluded by Proxmox's own documentation (C10).
- **One bundle refreshed online:** would expose Tier-0 keys on an online machine.

## Open questions

- The h0 form at rest; the epoch interval and rotation latency: A6 with A3 and H1 (Gate A).
- The encoder route for I_e, and the CCTV vectors: A2/G2 (Gate A).
- The header-shape rule: A2/A3 (Gate A).
- The trust-bundle encoding and fingerprint format, and expired-bundle behaviour: D3 (Gate C).
- Holders and k-of-n: E7-S1.
- A second SLIP-39 implementation, or a hardened tool: D2 Wave 2.
- A PQ device sealing key on Android: D3/A2.
- Custody of the update key: D5.

## Not yet decided (Wave 2)

- Holders and the final k-of-n (OD-08 confirmation after E7-S1), and card wording (E5/E7).
- The drilled recovery path (D2-S3 result) and the recovery-USB packaging.
- Time-delayed, owner-blockable release (AR-D2-2), if the owner does not accept its absence.
- PQ signatures for A and the trust bundle.
- Standby or derived ingest keys for emergency rotation.
- Custody of the account recovery codes (E7, DR-D2-3).
- The D2-S1 real-hardware result (only if OD-06 = classic).

## Conflicts

- **R-22 (CLAUDE.md trust model).** Under Decision 3, any k share holders with access to the ciphertext can decrypt everything. That widens "the owner (admin) holds the private key". The owner must explicitly amend the wording (DR-D2-4), with D6 handling family consent. This ADR does not change CLAUDE.md.
- **ADR-0001 §2.** See "Supersedes / Amends".
- **R-21.** Decision 7's trigger is conditional on DR-A1-1, which rewords "HMAC(family secret, content)".
- **ADR-0002 §3 (near-zero enrollment).** Uploads wait for S_e delivery. Resolution belongs to D3/OD-05.
- **AR-03 (no off-site copy).** The doomsday USB carries keys only, never archive data. The owner confirms this under DR-D2-4.
