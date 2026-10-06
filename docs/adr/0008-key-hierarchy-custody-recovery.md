# ADR-0008: Key hierarchy, custody and recovery. Wave 1 part: homelab-written recovery recipient, SLIP-39-split recovery key, two-bundle backup, ingest-key custody

- **Status:** Proposed. This is a partial draft covering the Wave 1 decisions. Holders, the human drill result, time-delayed release and PQ signatures are to be decided in Wave 2; see "Not yet decided".
- **Date:** 2026-10-06
- **Owner workstream:** D2
- **Decider:** the owner
- **Gate:** A (the recovery recipient, PQ choice and rotation mechanics); Gate C for the drilled recovery path and holders
- **Supersedes / Amends:** None. ADR-0001 §2 ("encrypted to the homelab public key (e.g. X25519 / age)") is not amended: under Decision 1, devices still encrypt to one homelab key, the ingest key. Decision 3, however, changes **who can decrypt** compared with the CLAUDE.md encryption trust model (R-22). That needs the owner's explicit acceptance under OD-08 (see "Conflicts").
- **Evidence:** `docs/research/d2-key-hierarchy-custody-recovery.md` (Wave 1 final). Spikes:
  - `spikes/D2-S1/` (emulated, not a real YubiKey), with its kit `docs/research/kits/D2-S1/`;
  - `spikes/D2-S2/` (ran; pass);
  - kit `docs/research/kits/D2-S3/` (kit-ready, no human result).

  Normative drafts: `docs/security/key-inventory.md` and `docs/security/key-ceremony-runbook.md`.
- **Traceability:** OPEN-3b, Q1-2a, OPEN-3c and Q1-2b (trigger only), R-19, R-20, R-22, R-26 (see `docs/research/traceability.md`)
- **Owner decisions:** OD-08, coupled with OD-06 (A2) and OD-07 (A6); DR-A2-2 (joint); new DR-D2-1, DR-D2-2 (to OD-17) and DR-D2-3
- **One-way door:** Yes, door #3 in `docs/research/one-way-doors.md` (recovery recipient in the key hierarchy)

## Context and problem statement

ADR-0001 encrypts everything on the device "to the homelab public key". If that one key is lost, or the owner who holds it dies, the whole keep-forever archive (R-26) is lost. CLAUDE.md asks for data integrity over everything, and PLAN asks for a succession path that lets an heir read the archive without Reliquary (E7). Adding a recovery recipient later is expensive. It needs the ingest key online and a custom header rewrap tool (C14; D2-S2: 1M PQ header rewraps took 186 s of CPU). It also cannot reach copies outside the store. So the hierarchy must be fixed before the first real family byte is encrypted (Gate A).

The decision is constrained by three things:

- age's format: multiple recipients are native (C1); PQ and classic recipients must not be mixed (C2); a passphrase must be the only stanza in its file (C3).
- D1's security requirements: pinned recipients (SR-02); the dedup secret is never in clear through Cloudflare (SR-15); no trust-forging key in the Worker (SR-23); admission of device keys independent of the Worker (SR-14).
- A2's envelope and A6's at-rest posture: the recommended A′ rewraps headers at ingest to an offline archive key X.

## Decision drivers

- R-26 keep forever; data integrity over everything; restore is first-class.
- R-20 devices cannot read backups; R-22 the admin can decrypt everything.
- SR-02, SR-14, SR-15, SR-23 (D1).
- **BUD-RECOVERY:** a non-author recovers 10 named photos from the doomsday kit in ≤ 2 h.
- **BUD-INGEST:** ≥ max(100 MB/s, 2 × downlink). This implies roughly 90 header unwraps/s (arithmetic, note §F4).
- **BUD-TTS:** ingest must not stall for long after a power cut.
- **BUD-SUPPORT:** ≤ 2 h per month of owner time.
- A2-S1's local rule: a PQ header ≤ 3 KB per object on devices (budgets.md "Keep local").

## Considered options

1. Single homelab key (ADR-0001 as written).
2. **Ingest key on device headers; the homelab writes {archive X, recovery R} on stored headers; retired ingest keys escrowed to {X, R}** (P1 plus escrow).
3. Devices write {ingest, R} (P2), with or without disclosed encapsulation randomness (P3).
4. Two-level: stored headers carry {X} only, and X is sealed to R.
5. Recovery-key backup options: SLIP-39 over a passphrase that wraps R; SLIP-39 over R's seed; age-plugin-sss per object or on R's file only; extra YubiKeys; a paper QR plus a memorised passphrase.
6. Online-key custody options: plain file; passphrase; systemd-creds; Proxmox vTPM; physical TPM; Tang; YubiKey; HSM.

## Decision

### Decision 1 (in scope; joint with A2's DR-A2-2): recipient placement

- **Devices** encrypt every content object and metadata record to the current **ingest recipient I_e** only. With PQ, the device header is 1,627 B (C4).
- **The homelab** rewraps every stored header to **{X, R}** at ingest. The payload is never touched (C14).
  - This applies under A6 posture A′.
  - Under posture A, a rewrap is added only to include R.
  - Under plaintext postures, R instead protects the volume key (Decision 5).
- **Retired ingest keys are escrowed, not just destroyed.** When epoch e ends, I_e is sealed to {X, R} into the online bundle (Decision 5). Then every online copy is deleted, including snapshots and replicas. This happens once the drain bound has passed (A3 DR-A3-3).
- **Reasons:**
  - The homelab cannot verify an R stanza that a device wrote (A2 C9).
  - Two PQ stanzas (3,184 B) fail A2-S1's local rule (C4).
  - The argument for device-written R (note C21) is **contested** and is not relied on.
  - Escrow keeps late USB bundles readable by the admin, with X and without the share holders, and by heirs with R.
- **Accepted gap:** the staged-only window. An object can exist only as staged ciphertext under I_e while the homelab is lost before the next escrow copy leaves it (AR-07). The owner may add device-written R (P2) for defence in depth. If so, the homelab-written {X, R} remains authoritative.

### Decision 2 (in scope; coupled to OD-06): algorithms

- If OD-06 = PQ (recommended by A2 and D2), **R and X are `mlkem768x25519`**. Every stanza on any one header is PQ; mixing is never allowed (C2). R must be `mlkem768x25519`, not tagpq, so that heirs can use stock tools (C11).
- The device-side encoder route for I_e is **A2's decision**: a native Rust X-Wing stanza, `age-plugin-pq` over the plugin protocol (C22), or Rust's native `tagpq` recipient (C23) with a custom homelab identity.
- If OD-06 = classic, everything is X25519 and YubiKey recipients become possible (D2-S1 applies).
- Signatures stay Ed25519. The trust bundle carries algorithm identifiers so a PQ signature can be added later (Wave 2).

### Decision 3 (in scope; holders open): recovery key R and its offline backup

1. R is generated on the air-gapped ceremony machine (`age-keygen -pq`) and reduced to its identity line.
2. A 128-bit secret W is generated by `shamir create … -x -s 128` (python-shamir-mnemonic). Why 128 bits under PQ: the age file key is itself 128 bits (C26), so W is not the weakest link, and 128 bits gives 20-word shares instead of 33.
3. R is wrapped with `age -a -p` under W, giving a 422 B armored file (C7, C25).
4. W is split with **SLIP-39, 2-of-3 by default, extendable, with no SLIP-39 passphrase** (C8).
5. Each share card carries:
   - the 20 words;
   - a QR of the armored wrapped identity;
   - R's fingerprint (format per D3);
   - a one-page instruction.
6. The wrapped file is also on the doomsday USB.
7. Recovery uses stock tools only: `shamir recover`, then `age -d`. The kit ships Go age ≥ 1.3.0 static binaries plus `age-plugin-pq` for older age versions (C22). It also ships a way to run shamir on an offline machine (a recovery USB image or an embedded Python; choice in Wave 2, measured by D2-S3).
8. Holders and the final k-of-n follow E7-S1 (Wave 2), before the production ceremony.

### Decision 4 (in scope): admin root key A and the trust bundle

- A is an offline Ed25519 key on two offline media held by the owner.
- A signs the **trust bundle** {I_e recipient, R recipient, X recipient if pinned, receipt key K-04, epoch ID, algorithm IDs}. Its digest is what kits and QR codes pin (SR-02; the format belongs to D3).
- By default A is **not** reachable from R (DR-D2-3, recommended "read-only heir bundle").

### Decision 5 (in scope): two backup bundles

| Bundle | Contents | Sealed to | Where sealed |
|---|---|---|---|
| **Offline** | X (plus A only if DR-D2-3 = full admin) | R | Only on the air-gapped ceremony machine; re-sealed only offline |
| **Online** | Every dedup epoch secret S_e, every retired I_e, the volume and catalog keys (K-06, K-07) | {R, X} | By the homelab, which already holds these online; refreshed on change |

The account recovery codes (Cloudflare, registrar, Play) are **not** in either bundle by default. They belong to E7's credential inventory (DR-D2-3).

### Decision 6 (in scope; posture-conditional): ingest-key custody

- I_e is a **software** PQ identity, held **in RAM**:
  - under A′, loaded unattended at boot (preferably clevis/Tang into tmpfs, with a manual fallback);
  - under plaintext postures, unlocked by the same mechanism and at the same moment as the store volume.
- I_e is never stored on snapshotted, ZFS-replicated or vzdump-covered storage. **Never on a Proxmox vTPM** (C10). Never on a YubiKey under PQ (C11).
- **Requirement on A6:** the retained original header h0 is never kept in the clear on the same disks as a disk-resident I_e. Acceptable forms: h0 sealed to X, h0 kept only as a MAC or digest, or I_e kept off disk. Otherwise a disk thief who gets I_e, h0 and the payload reads every open-epoch object.
- **Epoch interval:** at least yearly and after any suspected compromise. This is a proposal with no primary source; A6 and A3 confirm it.
- **X** is admin-held. It is a passphrase-wrapped file, optionally wrapped at rest by a YubiKey (classic is acceptable for an at-rest wrap that never leaves the house) or by a Mac Secure Enclave `--pq` key (C24). It is brought online only for restores, rebuilds and drills.

### Decision 7 (in scope; trigger conditional): dedup secret

- S_e is 32 CSPRNG bytes per epoch, generated at the homelab, with K_e = HKDF(S_e, "reliquary/v1/dedup-id-key") (A1). It is never derived from R or A.
- Delivery is per enrollment path as D3 designs it under SR-15. A clear S_e on a USB stick must be sealed, or deleted after first use.
- The rotation trigger is DR-D2-1: every revocation for loss, theft, compromise or estrangement, **conditional on DR-A1-1 = construction B and A1-S2**. Otherwise, confirmed compromise only.

### Decision 8 (in scope): drills and audits

- **Human drills use throwaway drill keys only** (D2-S3).
- **Annual holder check:** each holder confirms they still have their card and that it is readable. No share is reconstructed and no card is posted.
- **Real-key check** at Gate C, after any holder change and at least every 3 years (a proposal). It runs only on the air-gapped ceremony image and includes an **R-stanza audit**: unwrap a random sample of stored headers with R and verify their header MACs.
- **Any real-card recovery while the owner is alive triggers an R rotation and rewrap.**

### Consequences

- **Good:**
  - Heirs can read the archive with R, the disks and stock age.
  - Every R stanza on stored data is written at home and can be audited.
  - The device header passes A2-S1.
  - The ingest key is disposable and cheap to rotate.
  - Tier-0 keys never touch an online machine.
- **Bad / accepted trade-offs:**
  - Any k holders can read everything (AR-D2-1).
  - There is no time-delayed release in v1 (AR-D2-2; this is a choice, not forced by SR-23).
  - The staged-only window is uncovered (AR-07).
  - Replacing R or X needs a custom store-wide header rewrap.
  - The ceremony relies on an unhardened SLIP-39 tool, mitigated by the air gap (C9).
  - PQ stored headers are 3,184 B, plus h0 per A6.
- **Follow-up work:**
  - the rewrap and escrow tool (A6/G2);
  - the R-stanza audit tool;
  - D2-S3 kit amendments and the human drill;
  - the hardened SLIP-39 option;
  - the fingerprint format (D3).

### Confirmation

- **D2-S2** (ran, pass): stock-tool recovery after the ingest key was destroyed; rewrap cost measured.
- **D2-S3** (FM, kit-ready): BUD-RECOVERY with the amended kit (PQ + 128-bit, armored, QR step). This is the Gate C confirmation.
- **G2:** CCTV hybrid vectors; a cross-implementation round trip; a CI test that no mixed PQ/classic header is ever produced; a test of the R-stanza audit tool.
- **Every real-key check:** the R-stanza audit pass rate, recorded in the ceremony log.

## Pros and cons of the options

### 1. Single homelab key

- Good, because it is the simplest.
- Bad, because losing the key or the owner loses everything, and adding R later cannot reach staged or USB copies (C14).

### 2. P1 plus escrow (chosen)

- Good, because every R stanza is homelab-written and auditable, and the 1,627 B device header passes A2-S1 (C4).
- Good, because escrow covers late bundles without per-object cost.
- Bad, because the staged-only window is uncovered, and it depends on a homelab rewrap.

### 3. P2 / P3 (device-written R)

- Good, because it covers the staged-only window.
- Bad, because the stanza cannot be verified (A2 C9), the header is 3,184 B (C4), and the justification (note C21) is contested. P3 needs custom crypto review.

### 4. Two-level ({X} only; X sealed to R)

- Good, because replacing R becomes a re-seal, and headers are smaller.
- Bad, because the heir then depends on surviving sealed copies of X, and recovery has two steps.
- Fallback if the owner weighs rewrap tooling or storage more heavily.

### 5. Backup method

- SLIP-39 over W (chosen): stock tools, 20 words, checksummed (C6, C8, C25). The tool is unhardened (C9).
- SLIP-39 of R's seed: 33 words and a non-stock bech32 step (D2-S2).
- age-plugin-sss: experimental, no Windows builds, and about n × 1.56 KB per object under PQ (C13).
- YubiKeys: classic only (C11).
- Paper QR plus a memorised passphrase: a single point of failure.

### 6. Custody

- Proxmox vTPM: excluded (C10).
- YubiKey: impossible under PQ (C11).
- HSM: out of scope.
- Software in RAM via Tang or manual unlock (chosen): unwrap is far above the rate needed (C12).

## Evidence

| Claim (note ID) | Source (primary) | Verdict |
|---|---|---|
| C1 Multiple recipients are native; unrecognised stanzas are ignored | C2SP age spec (S1); M1 | Verified |
| C2 PQ and classic must not mix; Go age refuses | S1, S2, S4; D2-S2 | Verified |
| C3 scrypt must be the only stanza | S1 | Verified |
| C4 Header sizes 1,627 / 3,184 / 168 / 266 B | M1; D2-S2 | Verified |
| C5 Rust age has no native `mlkem768x25519` (narrow) | S5 | Verified |
| C6 The stock-tool SLIP-39 → age chain works | M1; D2-S2; S7, S8 | Verified |
| C7 The wrapped identity is 260 B binary / 422 B armored | M1; M2 | Verified |
| C8 SLIP-39 sizes, extendable sets, unverifiable passphrase | S7 | Verified |
| C9 The SLIP-39 reference tool is unhardened | S8 | Verified |
| C10 A Proxmox vTPM gives no real security benefit | S13 | Verified |
| C11 YubiKey PIV is classic only (absence part corrected by C24) | S9, S4, S26 | Verified |
| C12 Software unwrap is thousands per second | M1; D2-S2 | Verified |
| C13 age-plugin-sss is experimental, about n × 1.56 KB per object | S11; D2-S2 | Verified |
| C14 / C15 A recipient change rewrites only the header; no in-place revocation of copied data | S1, S4, S19 | Verified |
| C16 Sealed S_e costs no second read under construction B | internal | **Secondary-only:** used only as a condition on DR-D2-1, not as support for DR-A1-1 |
| C21 "Devices must write R" | internal | **Contested:** not relied on; Decision 1 rests on C4 and A2 C9 instead |
| C18 NIST IR 8547 dates | secondary | **Contested:** not used |
| C22–C26 age-plugin-pq; Rust tagpq; age-plugin-se `--pq`; the M2 chain; 128-bit file key | S4, S5, S26, S1; M2 | New in synthesis, not tallied. Each appears beside verified claims only |

## Reversibility

- **Adding R later** is a one-way door (door #3). It needs the ingest key online and a custom rewrap, and it cannot reach copies outside the store. It must be decided before Gate A.
- **Moving from P1 to P2** later is a client update and is reversible.
- **Changing holders** means re-issuing an extendable card set, and is reversible. Revoking ≥ k exposed cards needs a new R and a store rewrap.
- **Changing PQ to classic** after Gate A is possible but pointless. Changing classic to PQ later leaves existing objects harvestable.
- **The two-bundle split and the ingest custody** are operational and reversible.

## Alternatives considered

- **Mixed PQ ingest key with a classic recovery key:** violates the spec's SHOULD NOT, and Go age refuses it (C2).
- **Recovery recipient added only by devices:** cannot be verified, and fails A2-S1 (C4; A2 C9).
- **Destroying retired ingest keys without escrow:** late bundles beyond the drain bound would be lost, or would need the share holders.
- **Deriving S_e from R or A:** an offline root would come online at every rotation, and key purposes would mix.
- **Proxmox vTPM custody:** excluded by Proxmox's own documentation (C10).
- **One bundle refreshed online:** would expose Tier-0 keys on an online machine.

## Open questions

- The h0 form at rest, and the epoch interval: A6 with A3 (Gate A).
- The encoder route for I_e and the CCTV vectors: A2/G2 (Gate A).
- Fingerprint format and trust-bundle encoding: D3.
- Holders and k-of-n: E7-S1.
- The hardened SLIP-39 tool: D2 Wave 2.
- Whether Go age accepts tagpq and `mlkem768x25519` together on one header: A2. This matters only if P2 is chosen with a tagpq ingest key.

## Not yet decided (Wave 2)

- Holders and the final k-of-n (OD-08 confirmation after E7-S1), and card wording (with E5/E7).
- The drilled recovery path (D2-S3 result) and how the shamir tool is delivered (recovery USB or embedded Python).
- Time-delayed, owner-blockable release (AR-D2-2), if the owner rejects accepting it.
- PQ signatures for A and the trust bundle.
- Custody of the account recovery codes (E7, DR-D2-3).
- The D2-S1 real-hardware result (needed only if OD-06 = classic).

## Conflicts

- **R-22 (CLAUDE.md encryption trust model).** Under Decision 3, any k share holders can decrypt everything. This widens "the owner (admin) holds the private key". The owner must accept it explicitly under OD-08 (AR-D2-1), or amend the wording, with D6 handling family consent. This ADR does not change CLAUDE.md.
- **R-21.** Decision 7's trigger is conditional on DR-A1-1, which rewords "HMAC(family secret, content)".
