# F3-S3: red team against ADR-0001 and the F3 attack matrix

- **Workstream:** F3 (`docs/research/PLAN.md`, "F3."). **Exec tag:** CT.
- **Run by / date:** the F3 spike runner (an agent separate from the F3 analyst), Wave 1 batch W1-a, 2026-09-29.
- **Data-handling class:** `SYN → results`. Documents only; no data.
- **Budget IDs:** none directly. BUD-ABUSE and BUD-REVOKE are referenced by mapped rows.

## Hypothesis and decision

- **Hypothesis (PLAN):** every attack against ADR-0001 maps to a mitigation or to an accepted risk in the F3 matrix (and D1).
- **Pass →** the matrix feeds ADR-0007 and ADR-0009 as it stands. **Fail →** new matrix rows, SRs or ARs are needed first.

## Method

1. Walked ADR-0001 clause by clause (§1 staging and control plane, §2 encryption and dedup, §3 hash cache, §4 ingest, §5 USB and LAN transports, §6 restore). For each clause, applied D1's attacker profiles (AP1–AP9) and STRIDE/LINDDUN prompts.
2. Added the attack classes in the literature:
   - Tahoe convergence attacks;
   - Hofmann–Truong, MEGA and Nextcloud malicious-server classes;
   - Tarsnap and Borg nonce incidents;
   - Dark Clouds / Proofs of Ownership;
   - 2025 CDC attacks;
   - partitioning oracles;
   - Cure53/Ente presigned-header signing.
3. Added the results of F3-S1 and F3-S2, for example the receipt-timing leak seen in F3-S2 configuration C3L.
4. Recorded each attack in `attacks.py` with the IDs that claim to cover it. `check.py` parses the **current** F3 matrix (M-01…M-25 in `docs/research/f3-security-literature.md`, SHA-256 prefix `9b0eb5f457087d8b` at run time) and D1 (`docs/research/d1-threat-model.md`, prefix `b9a1b7d0d2779bac`: SR-01…SR-26, AR-01…AR-08, T-01…T-20). It checks that every reference exists, then classifies each attack:

   | Class | Meaning |
   |---|---|
   | MAPPED | A matrix row marked Mitigated or Accepted, or a D1 AR, covers it |
   | MAPPED-OPEN | Only matrix rows whose status is still **Open** cover it |
   | D1-ONLY | A D1 SR or AR covers it, but no F3 matrix row does |
   | UNMAPPED | Nothing in the matrix or D1 covers it |

   Note that D1's AR-04/05/06/08 are still "owner to accept". MAPPED via those ARs means "maps to an accepted-risk candidate".

## Result

**65 attacks: 36 MAPPED, 8 MAPPED-OPEN, 7 D1-ONLY, 14 UNMAPPED. 0 broken references.**

**Verdict: FAIL.** 14 attacks map to nothing.

Grouped, the 14 unmapped attacks are:

| Group | Attacks |
|---|---|
| New presence-oracle channels that per-person scope (DR-F3-2) does not yet close | RT-34 claim-conflict answer; RT-35 receipt or staging-deletion timing (measured in F3-S2 C3L); RT-36 per-person usage or quota display (OD-20) |
| Length leak not covered by M-05 | RT-14 encrypted metadata-record length |
| Device-side custody | RT-24 dedup secret and keys in OS cloud backups or synced keychains; RT-25 identity cloned by restoring a device backup; RT-30 hash-cache tampering → "safe" without upload (silent loss); RT-31 hash cache readable by a thief |
| Accepted-risk candidates not yet listed | RT-23 a compromised device discloses its own files; RT-43 objectionable content uploaded under a stolen device's identity and kept forever |
| Operations and scope | RT-42 ransomware doubling the keep-forever store (only PLAN D4-S3 covers it); RT-48 LAN-direct inbound listener (ADR-0037); RT-52 social-engineering the admin into a cross-person restore (A8/E7); RT-62 malicious or frozen app update (deferred to D5) |

The 7 D1-ONLY attacks (RT-06, 28, 33, 37, 41, 61, 63) need only a matrix row that points at the existing SR or AR.

The 8 MAPPED-OPEN attacks (RT-10, 11, 13, 15, 21, 22, 27, 45) close when DR-F3-1, DR-F3-2, OD-06, OD-08 and the A1 re-key procedure are decided.

Proposed coverage for each unmapped attack is in the "Note" column below. These are proposals for the F3 analyst, A2, A3, B6, D1, D2, D6 and A8, not decisions.

## All attacks

| ID | Class | ADR-0001 clause | Attacker | Attack | Covered by (status) | Note |
|---|---|---|---|---|---|---|
| RT-14 | UNMAPPED | §2 metadata record | AP2 | Length of the encrypted metadata record leaks filename/path length, EXIF presence, sidecar count | — | M-05 pads objects only; SR-26 minimises plaintext fields but not ciphertext length. Proposed row M-26: pad records to fixed size classes |
| RT-23 | UNMAPPED | §2 device holds plaintext | AP3/AP4 | A compromised device discloses the plaintext files it holds (before encryption) | — | Inherent and trivial, but not listed as an accepted risk. Proposed AR: "a compromised device discloses its own local files" |
| RT-24 | UNMAPPED | §2 dedup secret custody on device | AP2-like (Apple/Google) | Dedup secret and device keys copied into OS cloud backups (iCloud device backup, Android Auto Backup) or synced keychains, putting the family secret in a second cloud | — | SR-15 covers only the Cloudflare path; M-18 covers only the CE journal. Proposed SR: secrets and keys non-backup, non-syncing, device-bound (e.g. iOS ThisDeviceOnly keychain classes, Android allowBackup/dataExtractionRules exclusions); verify per platform in B-track |
| RT-25 | UNMAPPED | §2 device identity | AP3/ops | Device credential and signing key cloned by restoring a device backup onto a new phone: two devices share one identity and sequence | — | Same proposed SR as RT-24; SR-13 would show sequence conflicts only if it detects forks |
| RT-30 | UNMAPPED | §3 hash cache | AP4 | Local malware rewrites the hash cache so a file maps to the ID of an already-receipted file: shown "safe", never uploaded (silent loss) | — | Receipts (SR-05) prove the ID is stored, not that the local file has that ID. Proposed: "safe" requires the ID to have been computed from the current bytes; periodic re-hash sampling (B6/A1) |
| RT-31 | UNMAPPED | §3 hash cache at rest | AP3 | Thief reads the cache: SHA-256, dedup IDs and locators of all files, including ones deleted from the device | — | Proposed: cache encrypted with an OS-keystore key; prune entries of deleted files after receipt (D6 minimisation) |
| RT-34 | UNMAPPED | §4 claim conflict answer | AP3/AP4/AP5 | The "someone else is uploading this ID now" claim-conflict answer is itself a cross-person presence oracle, even under per-person scope | — | Proposed: claims scoped per person like presence answers (M-02 addition) |
| RT-35 | UNMAPPED | §4 receipt path | AP3/AP4/AP5 | Receipt latency (or staging deletion timing) reveals that the homelab already held the content, defeating per-person scope | — | Measured in F3-S2 config C3L: scope alone fails if receipts are faster for known content. Proposed: receipt path identical whether or not the homelab already has the content |
| RT-36 | UNMAPPED | §4 per-person usage | AP5 | Per-person storage usage or quota (OD-20) does not grow when the uploaded file is already stored by someone else: dedup oracle via the UI | — | Proposed: charge each person for their own uploads regardless of dedup |
| RT-42 | UNMAPPED | §4 keep-forever store | AP4 | Ransomware uploads encrypted copies of every file: valid new content that doubles the keep-forever store | T-15 (threat-listed) | Only cost-side coverage (T-15, BUD-ABUSE). Homelab storage exhaustion is covered by PLAN D4-S3 (ransomware pause) but by no SR, AR or matrix row |
| RT-43 | UNMAPPED | §4 attribution | AP3/AP4 | Stolen device uploads objectionable or illegal content signed as the victim device; stored forever | — | Proposed AR (attribution is device-level, not person-level) plus an admin quarantine/prune procedure under SR-20 |
| RT-48 | UNMAPPED | §5 LAN direct | LAN device (IoT, guest) | If LAN direct is built, the homelab gains an inbound listener reachable by any LAN device | — | Proposed for ADR-0037: device-key mutual auth, same parsers and limits, VLAN isolation; or do not build |
| RT-52 | UNMAPPED | §6 restore authorization | AP5 | A relative talks the admin into restoring another person's files to their device | — | Proposed A8/E7 rule: restore only to the owning person's devices unless an admin override is logged |
| RT-62 | UNMAPPED | updates | AP2/AP7 | Malicious or frozen app update (legal compulsion of the vendor, compromised CI) | — | D1 V22 defers this to D5 (Wave 2); no SR, AR or matrix row yet |
| RT-06 | D1-ONLY | §1 Worker secrets | AP2 | Worker-held secret (R2 parent token, invite pepper) leaks: full R2 read/write | SR-23 (mitigated) | Covered by D1 (A12, SR-23) but has no F3 matrix row |
| RT-28 | D1-ONLY | §2 secret distribution | AP1/AP5 | Rogue enrollment with a stolen or replayed QR/invite: the new device receives the dedup secret and becomes an oracle user | SR-14 (mitigated), SR-15 (mitigated), T-19 (threat-listed) | D1 covers key authenticity (SR-14, OD-05 open); no F3 matrix row links enrollment abuse to M-02 |
| RT-33 | D1-ONLY | §4 dedup index | AP3/AP4/AP5 | Dedup poisoning: upload garbage under another person's ID so their upload is skipped | SR-04 (mitigated), SR-06 (mitigated), SR-11 (mitigated), T-05 (threat-listed) | D1 covers it (T-05); the F3 matrix has no explicit row |
| RT-37 | D1-ONLY | §4 upload IDs | AP3/AP5 | Worker IDOR on another device's upload ID or claim | SR-07 (mitigated), T-17 (threat-listed) | D1 only; no F3 matrix row |
| RT-41 | D1-ONLY | §4 homelab download | AP2 | Cloud serves objects far larger than the signed size so the homelab downloads without bound | SR-22 (mitigated), SR-24 (mitigated) | D1 only; add "abort download past the signed padded size" to M-22 or M-24 |
| RT-61 | D1-ONLY | ingest VM | AP8 | Compromised ingest VM with an online key | AR-08 (accepted) |  |
| RT-63 | D1-ONLY | nudges | AP2/AP6 | Phishing-grade fake nudges | SR-25 (mitigated), T-20 (threat-listed) |  |
| RT-10 | MAPPED-OPEN | §2/§4 presence answer | AP3/AP4/AP5 | Compromised device: confirmation-of-a-file across the family | M-02 (open) |  |
| RT-11 | MAPPED-OPEN | §2/§4 presence answer | AP3/AP4/AP5 | Compromised device: learn-the-remaining-information on a family document | M-03 (open) |  |
| RT-13 | MAPPED-OPEN | §2 object size | AP2 | Exact-size fingerprinting of staged objects | M-05 (open) |  |
| RT-15 | MAPPED-OPEN | §4 multipart layout | AP2 | Part count, part sizes, Content-Length and SR-24 declared size reveal the exact size even if the payload is padded | M-05 (open) |  |
| RT-21 | MAPPED-OPEN | §2/§6 | future quantum adversary | Harvest-now-decrypt-later on X25519 wraps in staging, warm cache, restore prefix and USB | M-15 (open) |  |
| RT-22 | MAPPED-OPEN | §2 recipients | design error | PQ + classical recipients mixed, or scrypt recovery stanza, voiding PQ | M-16 (open) |  |
| RT-27 | MAPPED-OPEN | §2 rotation | AP2 + old secret | Linking old- and new-epoch IDs during re-keying | M-14 (open) |  |
| RT-45 | MAPPED-OPEN | §5 USB | finder/thief | Lost USB stick: ciphertext, manifest, sizes, device IDs; harvest-now | M-05 (open), M-15 (open) |  |
| RT-01 | MAPPED | §1 commit status | AP2 | Cloud reports "committed" for an object the homelab never saw | M-10 (mitigated), SR-05 (mitigated) |  |
| RT-02 | MAPPED | §1 queue retention / staging | AP2 | Cloud deletes staged objects before pull, or drops queue messages past retention | M-10 (mitigated), SR-12 (mitigated), AR-04 (accepted) |  |
| RT-03 | MAPPED | §1 queue | AP2 | Forged or replayed object-created events | M-09 (mitigated), SR-12 (mitigated) |  |
| RT-04 | MAPPED | §1 reconcile by listing | AP2 | Cloud hides or invents pending entries in the reconciliation listing | M-09 (mitigated), M-10 (mitigated), SR-13 (mitigated) |  |
| RT-05 | MAPPED | §1 Worker API | AP1 | Unauthenticated floods of enrollment/presence endpoints to run up cost | M-24 (mitigated), SR-21 (mitigated), SR-24 (mitigated), T-15 (threat-listed) |  |
| RT-07 | MAPPED | §1 homelab pull credential | AP8/AP1 | Homelab Cloudflare API token stolen from the homelab: read ciphertext, delete staged objects | M-10 (mitigated), AR-04 (accepted) | Effect covered (no receipt => re-upload); token scope (least privilege, no bucket admin) is specified nowhere |
| RT-08 | MAPPED | §1 status freshness | AP2 | Worker timestamps freeze or fake "last backup" freshness | M-10 (mitigated), SR-18 (mitigated), SR-19 (mitigated) |  |
| RT-09 | MAPPED | §2 dedup ID | AP2 | Cloud tests known files against IDs (plain hash) | M-01 (mitigated) |  |
| RT-12 | MAPPED | §2 no forward secrecy | AP2+AP3 | Leaked dedup secret + cloud ID history: offline test of every historical ID | M-04 (accepted), AR-06 (accepted) |  |
| RT-16 | MAPPED | §2 transport | network observer | ISP / Wi-Fi observer infers object sizes from TLS traffic volume | M-05 (open), M-06 (accepted) |  |
| RT-17 | MAPPED | §2 metadata | AP2 | Timing, per-device volume, IPs, ID equality across devices | M-06 (accepted), AR-05 (accepted) |  |
| RT-18 | MAPPED | §2 age public-key recipients | AP2/AP3 | Forge objects/records in another device's name (age has no sender authentication) | M-07 (mitigated), SR-03 (mitigated) |  |
| RT-19 | MAPPED | §2/§4 | AP2 | Swap object and record, or reuse a record in another context | M-08 (mitigated), SR-04 (mitigated) |  |
| RT-20 | MAPPED | §2 multi-recipient | malicious encryptor | Header decrypts to different plaintexts for homelab and recovery identities (key commitment) | M-13 (mitigated) |  |
| RT-26 | MAPPED | §2 A1 digest form | AP2+AP3 | After a leak, IDs testable from SHA-256 hash lists without the files | M-04 (accepted), M-25 (mitigated) |  |
| RT-29 | MAPPED | §2 revocation | AP3 | A revoked device still knows the dedup secret | M-04 (accepted), M-25 (mitigated), SR-17 (mitigated) |  |
| RT-32 | MAPPED | §4 claims | AP3/AP4/AP5 | Claim squatting; garbage or oversized uploads | M-24 (mitigated), SR-10 (mitigated), SR-24 (mitigated) |  |
| RT-38 | MAPPED | §4 presigned URLs | AP1 | Leaked presigned URL (logs, crash reports, proxies) reused to overwrite or add cost | M-24 (mitigated), SR-07 (mitigated), SR-09 (mitigated) |  |
| RT-39 | MAPPED | §4 presigned PUT headers | AP3/AP1 | Unsigned Content-Length/Type on presigned PUT (Cure53/Ente checklist item) | M-24 (mitigated), SR-09 (mitigated), SR-24 (mitigated) |  |
| RT-40 | MAPPED | §4 homelab parsers | AP2/AP3 | Crafted age headers, records, receipts against homelab parsers | M-22 (mitigated), SR-22 (mitigated) |  |
| RT-44 | MAPPED | §4 "no read rights" | AP3/AP5 | Use a dedup hit as proof of possession to obtain another person's file | M-19 (mitigated) |  |
| RT-46 | MAPPED | §5 USB | AP3/AP5 | Crafted USB stick fed to the homelab: malicious filesystem image, symlinks, oversized manifests | M-22 (mitigated) | Parser coverage only; mount hardening (read-only, nosuid/noexec, no automount, parse in a disposable VM) is specified nowhere |
| RT-47 | MAPPED | §5 USB | AP3 | Old bundle re-imported (replay) | M-09 (mitigated), SR-12 (mitigated) |  |
| RT-49 | MAPPED | §6 restore staging | AP2 | Substitute restored content | M-11 (mitigated), SR-16 (mitigated), T-10 (threat-listed) |  |
| RT-50 | MAPPED | §6 restore target | AP2 | Substitute the device key so the admin restores to the cloud | M-11 (mitigated), SR-14 (mitigated) |  |
| RT-51 | MAPPED | §6 retention windows | AP2 | Restore prefix (7 days) and warm cache (30 days) lengthen ciphertext exposure | M-15 (open), AR-05 (accepted) |  |
| RT-53 | MAPPED | §6 restore replay | AP2 | Replay an old restore manifest and objects | M-21 (mitigated), SR-16 (mitigated) |  |
| RT-54 | MAPPED | all | AP2 | Downgrade: Worker supplies recipients, versions, or empty lists | M-12 (mitigated) |  |
| RT-55 | MAPPED | all | AP2 | Key substitution of homelab recipient or receipt key | M-11 (mitigated), SR-02 (mitigated) |  |
| RT-56 | MAPPED | content encryption | bug | Nonce/keystream reuse on resume (Tarsnap 2011 class) | M-17 (mitigated) |  |
| RT-57 | MAPPED | content encryption | bug/ops | Journal rollback re-releases keystream (Borg 1.x class) | M-18 (mitigated) |  |
| RT-58 | MAPPED | age | AP2 | Partitioning oracle against homelab identities | M-23 (accepted) |  |
| RT-59 | MAPPED | homelab engine | store observer | CDC parameter recovery (2025 attacks) | M-20 (mitigated) |  |
| RT-60 | MAPPED | restore / range reads | AP2 | Truncated or extended object on restore | M-21 (mitigated) |  |
| RT-64 | MAPPED | §2 cloud ID retention | AP2 | Cloud keeps every dedup ID forever for global dedup, maximising what a later leak exposes | M-04 (accepted) |  |
| RT-65 | MAPPED | §2 epochs | AP3 | Stale-epoch IDs still accepted after rotation | M-14 (open), M-25 (mitigated) |  |
## Caveats

- One red-team pass by one agent. It is a checklist sweep, not an adversarial exercise with a live system. Other reviewers will find more.
- The matrix is a draft that the F3 analyst is editing in parallel. Re-run `python3 check.py` after it changes. The script prints the file hashes it read.
- MAPPED means a reference exists, not that the mitigation has been built or tested.

## Files

| File | Purpose |
|---|---|
| `attacks.py` | The 65-attack catalogue and references |
| `check.py` | Parses the matrix and D1, classifies, tallies → `evidence/f3s3_results.json` |
