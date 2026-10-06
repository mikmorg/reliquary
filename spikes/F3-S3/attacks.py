"""F3-S3 red-team catalogue against ADR-0001 (+ the F3 matrix draft). Each attack names the
ADR-0001 clause it targets, the D1 attacker profile (AP1..AP9), and the IDs that claim to
cover it: F3 matrix rows (M-nn), D1 security requirements (SR-nn), accepted risks (AR-nn)
or D1 threats (T-nn). 'refs' empty => nothing in the current documents covers it."""
A = []
def a(id, clause, ap, attack, refs, note='', source=''):
    A.append(dict(id=id, clause=clause, attacker=ap, attack=attack, refs=refs, note=note, source=source))

# --- ADR-0001 section 1: staging and control plane
a('RT-01', '§1 commit status', 'AP2', 'Cloud reports "committed" for an object the homelab never saw', ['M-10', 'SR-05'])
a('RT-02', '§1 queue retention / staging', 'AP2', 'Cloud deletes staged objects before pull, or drops queue messages past retention', ['M-10', 'SR-12', 'AR-04'])
a('RT-03', '§1 queue', 'AP2', 'Forged or replayed object-created events', ['M-09', 'SR-12'])
a('RT-04', '§1 reconcile by listing', 'AP2', 'Cloud hides or invents pending entries in the reconciliation listing', ['M-09', 'M-10', 'SR-13'])
a('RT-05', '§1 Worker API', 'AP1', 'Unauthenticated floods of enrollment/presence endpoints to run up cost', ['M-24', 'SR-21', 'SR-24', 'T-15'])
a('RT-06', '§1 Worker secrets', 'AP2', 'Worker-held secret (R2 parent token, invite pepper) leaks: full R2 read/write', ['SR-23'],
  note='Covered by D1 (A12, SR-23) but has no F3 matrix row')
a('RT-07', '§1 homelab pull credential', 'AP8/AP1', 'Homelab Cloudflare API token stolen from the homelab: read ciphertext, delete staged objects', ['M-10', 'AR-04'],
  note='Effect covered (no receipt => re-upload); token scope (least privilege, no bucket admin) is specified nowhere')
a('RT-08', '§1 status freshness', 'AP2', 'Worker timestamps freeze or fake "last backup" freshness', ['M-10', 'SR-18', 'SR-19'])
# --- section 2: encryption and dedup
a('RT-09', '§2 dedup ID', 'AP2', 'Cloud tests known files against IDs (plain hash)', ['M-01'])
a('RT-10', '§2/§4 presence answer', 'AP3/AP4/AP5', 'Compromised device: confirmation-of-a-file across the family', ['M-02'], source='Tahoe convergence-secret; F3-S2')
a('RT-11', '§2/§4 presence answer', 'AP3/AP4/AP5', 'Compromised device: learn-the-remaining-information on a family document', ['M-03'], source='Tahoe; F3-S2')
a('RT-12', '§2 no forward secrecy', 'AP2+AP3', 'Leaked dedup secret + cloud ID history: offline test of every historical ID', ['M-04', 'AR-06'])
a('RT-13', '§2 object size', 'AP2', 'Exact-size fingerprinting of staged objects', ['M-05'], source='F3-S1')
a('RT-14', '§2 metadata record', 'AP2', 'Length of the encrypted metadata record leaks filename/path length, EXIF presence, sidecar count', [],
  note='M-05 pads objects only; SR-26 minimises plaintext fields but not ciphertext length. Proposed row M-26: pad records to fixed size classes')
a('RT-15', '§4 multipart layout', 'AP2', 'Part count, part sizes, Content-Length and SR-24 declared size reveal the exact size even if the payload is padded', ['M-05'])
a('RT-16', '§2 transport', 'network observer', 'ISP / Wi-Fi observer infers object sizes from TLS traffic volume', ['M-05', 'M-06'])
a('RT-17', '§2 metadata', 'AP2', 'Timing, per-device volume, IPs, ID equality across devices', ['M-06', 'AR-05'])
a('RT-18', '§2 age public-key recipients', 'AP2/AP3', 'Forge objects/records in another device\'s name (age has no sender authentication)', ['M-07', 'SR-03'])
a('RT-19', '§2/§4', 'AP2', 'Swap object and record, or reuse a record in another context', ['M-08', 'SR-04'])
a('RT-20', '§2 multi-recipient', 'malicious encryptor', 'Header decrypts to different plaintexts for homelab and recovery identities (key commitment)', ['M-13'])
a('RT-21', '§2/§6', 'future quantum adversary', 'Harvest-now-decrypt-later on X25519 wraps in staging, warm cache, restore prefix and USB', ['M-15'])
a('RT-22', '§2 recipients', 'design error', 'PQ + classical recipients mixed, or scrypt recovery stanza, voiding PQ', ['M-16'])
a('RT-23', '§2 device holds plaintext', 'AP3/AP4', 'A compromised device discloses the plaintext files it holds (before encryption)', [],
  note='Inherent and trivial, but not listed as an accepted risk. Proposed AR: "a compromised device discloses its own local files"')
a('RT-24', '§2 dedup secret custody on device', 'AP2-like (Apple/Google)', 'Dedup secret and device keys copied into OS cloud backups (iCloud device backup, Android Auto Backup) or synced keychains, putting the family secret in a second cloud', [],
  note='SR-15 covers only the Cloudflare path; M-18 covers only the CE journal. Proposed SR: secrets and keys non-backup, non-syncing, device-bound (e.g. iOS ThisDeviceOnly keychain classes, Android allowBackup/dataExtractionRules exclusions); verify per platform in B-track')
a('RT-25', '§2 device identity', 'AP3/ops', 'Device credential and signing key cloned by restoring a device backup onto a new phone: two devices share one identity and sequence', [],
  note='Same proposed SR as RT-24; SR-13 would show sequence conflicts only if it detects forks')
a('RT-26', '§2 A1 digest form', 'AP2+AP3', 'After a leak, IDs testable from SHA-256 hash lists without the files', ['M-04', 'M-25'])
a('RT-27', '§2 rotation', 'AP2 + old secret', 'Linking old- and new-epoch IDs during re-keying', ['M-14'])
a('RT-28', '§2 secret distribution', 'AP1/AP5', 'Rogue enrollment with a stolen or replayed QR/invite: the new device receives the dedup secret and becomes an oracle user', ['SR-14', 'SR-15', 'T-19'],
  note='D1 covers key authenticity (SR-14, OD-05 open); no F3 matrix row links enrollment abuse to M-02')
a('RT-29', '§2 revocation', 'AP3', 'A revoked device still knows the dedup secret', ['M-04', 'M-25', 'SR-17'])
# --- section 3: client hash cache
a('RT-30', '§3 hash cache', 'AP4', 'Local malware rewrites the hash cache so a file maps to the ID of an already-receipted file: shown "safe", never uploaded (silent loss)', [],
  note='Receipts (SR-05) prove the ID is stored, not that the local file has that ID. Proposed: "safe" requires the ID to have been computed from the current bytes; periodic re-hash sampling (B6/A1)')
a('RT-31', '§3 hash cache at rest', 'AP3', 'Thief reads the cache: SHA-256, dedup IDs and locators of all files, including ones deleted from the device', [],
  note='Proposed: cache encrypted with an OS-keystore key; prune entries of deleted files after receipt (D6 minimisation)')
# --- section 4: ingest protocol
a('RT-32', '§4 claims', 'AP3/AP4/AP5', 'Claim squatting; garbage or oversized uploads', ['M-24', 'SR-10', 'SR-24'])
a('RT-33', '§4 dedup index', 'AP3/AP4/AP5', 'Dedup poisoning: upload garbage under another person\'s ID so their upload is skipped', ['SR-04', 'SR-06', 'SR-11', 'T-05'],
  note='D1 covers it (T-05); the F3 matrix has no explicit row')
a('RT-34', '§4 claim conflict answer', 'AP3/AP4/AP5', 'The "someone else is uploading this ID now" claim-conflict answer is itself a cross-person presence oracle, even under per-person scope', [],
  note='Proposed: claims scoped per person like presence answers (M-02 addition)')
a('RT-35', '§4 receipt path', 'AP3/AP4/AP5', 'Receipt latency (or staging deletion timing) reveals that the homelab already held the content, defeating per-person scope', [],
  note='Measured in F3-S2 config C3L: scope alone fails if receipts are faster for known content. Proposed: receipt path identical whether or not the homelab already has the content')
a('RT-36', '§4 per-person usage', 'AP5', 'Per-person storage usage or quota (OD-20) does not grow when the uploaded file is already stored by someone else: dedup oracle via the UI', [],
  note='Proposed: charge each person for their own uploads regardless of dedup')
a('RT-37', '§4 upload IDs', 'AP3/AP5', 'Worker IDOR on another device\'s upload ID or claim', ['SR-07', 'T-17'], note='D1 only; no F3 matrix row')
a('RT-38', '§4 presigned URLs', 'AP1', 'Leaked presigned URL (logs, crash reports, proxies) reused to overwrite or add cost', ['M-24', 'SR-07', 'SR-09'])
a('RT-39', '§4 presigned PUT headers', 'AP3/AP1', 'Unsigned Content-Length/Type on presigned PUT (Cure53/Ente checklist item)', ['M-24', 'SR-09', 'SR-24'])
a('RT-40', '§4 homelab parsers', 'AP2/AP3', 'Crafted age headers, records, receipts against homelab parsers', ['M-22', 'SR-22'])
a('RT-41', '§4 homelab download', 'AP2', 'Cloud serves objects far larger than the signed size so the homelab downloads without bound', ['SR-22', 'SR-24'],
  note='D1 only; add "abort download past the signed padded size" to M-22 or M-24')
a('RT-42', '§4 keep-forever store', 'AP4', 'Ransomware uploads encrypted copies of every file: valid new content that doubles the keep-forever store', ['T-15'],
  note='Only cost-side coverage (T-15, BUD-ABUSE). Homelab storage exhaustion is covered by PLAN D4-S3 (ransomware pause) but by no SR, AR or matrix row')
a('RT-43', '§4 attribution', 'AP3/AP4', 'Stolen device uploads objectionable or illegal content signed as the victim device; stored forever', [],
  note='Proposed AR (attribution is device-level, not person-level) plus an admin quarantine/prune procedure under SR-20')
a('RT-44', '§4 "no read rights"', 'AP3/AP5', 'Use a dedup hit as proof of possession to obtain another person\'s file', ['M-19'])
# --- section 5: transports
a('RT-45', '§5 USB', 'finder/thief', 'Lost USB stick: ciphertext, manifest, sizes, device IDs; harvest-now', ['M-05', 'M-15'])
a('RT-46', '§5 USB', 'AP3/AP5', 'Crafted USB stick fed to the homelab: malicious filesystem image, symlinks, oversized manifests', ['M-22'],
  note='Parser coverage only; mount hardening (read-only, nosuid/noexec, no automount, parse in a disposable VM) is specified nowhere')
a('RT-47', '§5 USB', 'AP3', 'Old bundle re-imported (replay)', ['M-09', 'SR-12'])
a('RT-48', '§5 LAN direct', 'LAN device (IoT, guest)', 'If LAN direct is built, the homelab gains an inbound listener reachable by any LAN device', [],
  note='Proposed for ADR-0037: device-key mutual auth, same parsers and limits, VLAN isolation; or do not build')
# --- section 6: restore
a('RT-49', '§6 restore staging', 'AP2', 'Substitute restored content', ['M-11', 'SR-16', 'T-10'])
a('RT-50', '§6 restore target', 'AP2', 'Substitute the device key so the admin restores to the cloud', ['M-11', 'SR-14'])
a('RT-51', '§6 retention windows', 'AP2', 'Restore prefix (7 days) and warm cache (30 days) lengthen ciphertext exposure', ['M-15', 'AR-05'])
a('RT-52', '§6 restore authorization', 'AP5', 'A relative talks the admin into restoring another person\'s files to their device', [],
  note='Proposed A8/E7 rule: restore only to the owning person\'s devices unless an admin override is logged')
a('RT-53', '§6 restore replay', 'AP2', 'Replay an old restore manifest and objects', ['M-21', 'SR-16'])
# --- cross-cutting / literature classes
a('RT-54', 'all', 'AP2', 'Downgrade: Worker supplies recipients, versions, or empty lists', ['M-12'], source='Nextcloud GHSA-jh3g')
a('RT-55', 'all', 'AP2', 'Key substitution of homelab recipient or receipt key', ['M-11', 'SR-02'], source='Hofmann-Truong; MEGA')
a('RT-56', 'content encryption', 'bug', 'Nonce/keystream reuse on resume (Tarsnap 2011 class)', ['M-17'])
a('RT-57', 'content encryption', 'bug/ops', 'Journal rollback re-releases keystream (Borg 1.x class)', ['M-18'])
a('RT-58', 'age', 'AP2', 'Partitioning oracle against homelab identities', ['M-23'])
a('RT-59', 'homelab engine', 'store observer', 'CDC parameter recovery (2025 attacks)', ['M-20'])
a('RT-60', 'restore / range reads', 'AP2', 'Truncated or extended object on restore', ['M-21'])
a('RT-61', 'ingest VM', 'AP8', 'Compromised ingest VM with an online key', ['AR-08'])
a('RT-62', 'updates', 'AP2/AP7', 'Malicious or frozen app update (legal compulsion of the vendor, compromised CI)', [],
  note='D1 V22 defers this to D5 (Wave 2); no SR, AR or matrix row yet')
a('RT-63', 'nudges', 'AP2/AP6', 'Phishing-grade fake nudges', ['SR-25', 'T-20'])
a('RT-64', '§2 cloud ID retention', 'AP2', 'Cloud keeps every dedup ID forever for global dedup, maximising what a later leak exposes', ['M-04'])
a('RT-65', '§2 epochs', 'AP3', 'Stale-epoch IDs still accepted after rotation', ['M-14', 'M-25'])
