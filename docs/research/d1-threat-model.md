# D1. Threat model and security requirements (Wave 1: malicious-cloud and dedup-poisoning tabletops)

- **Workstream:** D1 (see `docs/research/PLAN.md`, section "D1.")
- **Status:** Draft (analyst deep read; not yet through skeptic review)
- **Date:** 2026-09-29 (last updated 2026-09-29)
- **Feeds:** OD-04 (Wave 1), OD-17 (accepted-risk register), OD-05 (Wave 2, input only); ADR-0009 (A3 ingest protocol), ADR-0010 (C1 control plane and R2 key layout), ADR-0014 (D3), ADR-0028 (A8 restore); `docs/security/threat-model.md` (v0 register, owned by D1: the draft content is in §9 of this note, for the synthesis stage to lift); one-way doors #5 (receipt format), #7 (R2 key layout), #10 (pinned homelab keys)
- **Depends on:** T1 spike 2 (`content-encryption-format.md`, "CE spike"), T2 (`fact-check-adr-0001-0002.md`), C1-S1 (R2 behaviour; running in parallel), F3 (not yet delivered)
- **Traceability rows advanced:** R-18 (devices only append), R-19/R-20 (encryption, devices cannot read), R-21 (opaque IDs), R-22 (admin escrow), R-38 (no off-site copy → accepted risk), R-44 (cloud never sees plaintext)
- **Scope of this run:** the Wave 1 slice of D1 only: tabletops D1-S1 and D1-S2, the v0 register for the cloud API and the ingest protocol, and the security requirements (SR-xx) that A3 and C1 need now. The full register (all components, LINDDUN walkthrough, attack trees, D1-S3 red team) is Wave 2.

## Summary

The trust model of ADR-0001 can hold against a fully malicious Cloudflare, but not as ADR-0001 §4 is written. Three things there let a malicious or compromised control plane cause **silent data loss** or **disclosure**, not just downtime:

1. staged objects keyed by dedup ID, where R2 is last-writer-wins;
2. "committed" status that only the Worker reports;
3. device public keys, and so restore targets and dedup-secret delivery, that reach the homelab only through the Worker.

The fix is the set the plan expected, and the CE spike has already prototyped most of it:

- per-upload staging keys;
- device-signed metadata records;
- full verification at the homelab (decrypt, then check size, SHA-256 and dedup ID);
- homelab-signed receipts as the only proof of "stored at home", checked against a trust bundle pinned outside the cloud;
- dedup "hits" that never count as safe.

On top of that set this note adds five requirements:

- claims are advisory, not exclusive;
- a device re-queries and re-uploads when it gets no receipt within a timeout;
- a homelab-signed heartbeat, so a cloud that stalls or withholds updates is noticed;
- device keys authenticated by a path the Worker cannot forge;
- a homelab-signed restore manifest.

With these, every dedup-poisoning and claim-squatting scenario in D1-S2 ends in detection and automatic re-upload with no silent loss. The one condition is that the device keeps the file until it holds a receipt. **Recommendation:** OD-04 should be decided "yes" (supersede ADR-0001 §4 and reword one §2 property). Confidence is high for the storage-side facts (primary Cloudflare docs) and medium for the protocol conclusions, which are tabletop reasoning that D4-S1/S2 must still prove against a harness.

## Questions

| # | Question (PLAN D1, Wave 1 slice) | Short answer | Confidence |
|---|---|---|---|
| 1 | Assets | Listed in §9.2. Top five for this slice: homelab private key, homelab receipt-signing key, dedup secret, device signing keys, the "is it safe?" status seen by the family. | High |
| 2 | Attackers | Nine profiles in §9.3. The two that drive Wave 1 are a fully malicious Cloudflare control plane (insider, account takeover, legal compulsion, or compromised Worker code or secrets) and one compromised device holding the dedup secret. | High |
| 3a | What holds if the control plane is fully malicious? | **With the required changes:** confidentiality of content and metadata; integrity of what is stored at home; no false "safe". **Lost:** availability, and metadata privacy (sizes, timing, IPs, which devices hold equal IDs, name and email under ADR-0002). **Without the changes:** silent loss and restore redirection are possible. See §6. | Medium |
| 3b | What holds if one device and the dedup secret are compromised? | Still holds: no reading of backups and no deletion of history. The attacker gains a confirmation-of-a-file oracle over the family's library via "which are missing?", bounded only by rate limits. It can squat claims and upload garbage (cost). It can forge records only as itself. If the cloud's ID history also leaks, every historical ID can be tested for known files (no forward secrecy). | High (oracle) / Medium (bounds) |
| 3c | What holds if the ingest VM is compromised? | Nothing confidential that the VM can decrypt. It can sign false receipts, which means silent loss for new uploads. Integrity of *already-stored* data holds only if the store is append-only against the ingest credentials (D4-S4). Mostly Wave 2 (A6, D2, D4). | Medium |
| 4 | Spoofing: can the cloud substitute the homelab key, a device key, the dedup secret, or commit status? | **Yes, all four, unless:** the homelab key is pinned via QR or kit; device keys are authenticated by a path independent of the Worker; the dedup secret comes in the kit or sealed to an authenticated device key; and status is a homelab-signed receipt. Every value is classified in §5. | High |
| 5 | Tampering: overwrites, dedup poisoning, claim squatting | Overwrite: possible with dedup-ID keys (last writer wins) and closed by per-upload keys; create-only on multipart is still unproven (C1-S1). Poisoning: caught at the homelab by HMAC re-verification. Squatting: reduced to delay and cost by advisory claims with TTL. See §7. | High (mechanism) / Medium (completeness) |
| 6 | Repudiation: where does an audit trail live that the cloud cannot rewrite? | At the homelab: signed receipts (devices hold them) plus the homelab's own append-only log of accepted and rejected records. Cloudflare Audit Logs v2 help detect account takeover but are held by the untrusted party. A Merkle-log checkpoint (C2SP tlog-checkpoint) is an option for Wave 2, not needed for v0. | Medium |
| 7 | Disclosure: sizes, timing, IP logs, dedup oracle, email, local cache | Sizes and timing: exact plaintext size is derivable from ciphertext length (CE spike R-4; padding is D-7, A2/F3). IPs and timing: visible to Cloudflare (restic's threat model lists the same leaks). Dedup oracle: see 3b. Email and name: plaintext in the cloud under ADR-0002 (OD-03). Local hash cache: plaintext inventory on the device (B6). | High |
| 8 | Denial of service and cost | A malicious cloud can always deny service. A leaked URL or credential can add storage and operations cost. Community reports say presigned PUTs cannot cap size (secondary, unverified), so size is checked on Complete or on the event and the device is flagged. | Medium |
| 9 | Privilege escalation via homelab parsers and Worker IDOR | Parsers: everything relayed by the cloud (records, receipts, manifests, bundles, age headers) is hostile input (SR-22; D4-S5 owns the tests). IDOR: the Worker binds each upload ID and staging key to the authenticated device, following the Ente commit-time key-ownership check. Worker IDOR only costs availability if SR-01 holds. | Medium |

## Method

- **Sweep:** three scouts (docs, source, community) ran before this deep read; their findings came in as JSON. No policy or standards scout ran separately; the docs scout covered C2SP and the MS Threat Modeling Tool.
- **Deep read (this note):** full re-fetch and reading of these primary sources, all on 2026-09-29, into the scratchpad:
  - R2 presigned URLs;
  - the S3 compatibility table (PutObject, UploadPart, CompleteMultipartUpload and CopyObject rows, and the checksum table);
  - temporary credentials;
  - API tokens;
  - bucket locks;
  - consistency;
  - event notifications;
  - Workers R2 `put()` options;
  - Queues delivery guarantees;
  - the C2SP age spec (header MAC and scrypt sections);
  - the restic design threat model;
  - the Tahoe-LAFS convergence-secret document;
  - Borg 1.4 append-only notes;
  - rest-server `repo.go` (overwrite refusal and append-only delete);
  - Kopia `grpc_session.go` (server-side content-ID derivation).
- **Tabletops:** D1-S1 and D1-S2 were run as structured walkthroughs by one analyst (§5–§7). The inputs were ADR-0001 as written, the CE spike design (§8.5–§12), and the R2 facts above. No second human participant took part. The spike runner is running D1-S1/S2 in parallel (see Spikes).
- **Scout conflicts resolved:**
  - *Borg append-only currency.* Scout 2 read that the Borg master notes lack the append-only section. The 1.4-maint notes, fetched here, still carry it, including "Drawbacks": a later non-append-only write "will render append-only mode moot", and "a few chunks" can be deleted silently. Both branch statements are true; the lesson is the same.
  - *Revocation timing.* The consistency page says permission changes on an API key are "eventually consistent… up to a minute". The temporary-credentials page says revoking the parent token makes derived credentials "stop working immediately". These two Cloudflare pages do not agree. BUD-REVOKE planning should assume the slower figure until C1-S1 or D3-S5 measures it (claim C14).
  - *Tailnet Lock.* The doc pages were blocked. The source code (`tka/*.go`) is primary for the mechanism; the prose threat model (what a compromised coordination server can still do) rests on search extracts only.
- **Blocked sources:** developers.cloudflare.com (read via the cloudflare-docs GitHub source instead; same content). eprint.iacr.org and www.iacr.org (MLE paper, Hofmann–Truong, MEGA, Nextcloud, proofs-of-ownership; all via search extracts only). tailscale.com, words.filippo.io, linddun.org, blog.cloudflare.com, community.cloudflare.com, news.ycombinator.com, github.com web (restic #22057 could not be re-read: 403 from shell; the GitHub MCP is limited to this repo). The WebSearch budget for the session was exhausted during this deep read. **To report to H1 (sources.md is H1's file; not edited here).**
- **Stop rule:** the deep read stopped when every Wave 1 key question had at least one primary source or was explicitly marked inference. The blocked papers are only precedent, not load-bearing.

## Sources

| # | Source | Publisher | Version or date | Accessed | Primary? |
|---|---|---|---|---|---|
| S1 | R2 Presigned URLs, `cloudflare/cloudflare-docs @ production : src/content/docs/r2/api/s3/presigned-urls.mdx` (= developers.cloudflare.com/r2/api/s3/presigned-urls/) | Cloudflare | production branch HEAD | 2026-09-29 | Yes |
| S2 | R2 S3 API compatibility, `… : r2/api/s3/api.mdx` | Cloudflare | production HEAD | 2026-09-29 | Yes |
| S3 | R2 S3 extensions, `… : r2/api/s3/extensions.mdx` | Cloudflare | production HEAD | 2026-09-29 | Yes |
| S4 | R2 Temporary credentials, `… : r2/api/s3/temporary-credentials.mdx` | Cloudflare | production HEAD | 2026-09-29 | Yes |
| S5 | R2 API tokens, `… : r2/api/tokens.mdx` | Cloudflare | production HEAD | 2026-09-29 | Yes |
| S6 | R2 Bucket locks, `… : r2/buckets/bucket-locks.mdx` | Cloudflare | production HEAD | 2026-09-29 | Yes |
| S7 | R2 Consistency model, `… : r2/reference/consistency.mdx` | Cloudflare | production HEAD | 2026-09-29 | Yes |
| S8 | R2 Event notifications, `… : r2/buckets/event-notifications.mdx` | Cloudflare | production HEAD | 2026-09-29 | Yes |
| S9 | Workers R2 API reference, `… : r2/api/workers/workers-api-reference.mdx` | Cloudflare | production HEAD | 2026-09-29 | Yes |
| S10 | Queues delivery guarantees, `… : queues/reference/delivery-guarantees.mdx` | Cloudflare | production HEAD | 2026-09-29 | Yes |
| S11 | Workers Web Crypto, `… : workers/runtime-apis/web-crypto.mdx` (scout read; not re-read) | Cloudflare | production HEAD | 2026-09-29 | Yes |
| S12 | Audit Logs v2, `… : fundamentals/account/account-security/audit-logs.mdx` (scout read) | Cloudflare | production HEAD | 2026-09-29 | Yes |
| S13 | age v1 spec, `C2SP/C2SP @ main : age.md` (stable at https://c2sp.org/age) | C2SP | main HEAD | 2026-09-29 | Yes |
| S14 | C2SP signed-note and tlog-checkpoint, `C2SP/C2SP @ main : signed-note.md, tlog-checkpoint.md` | C2SP | main HEAD | 2026-09-29 | Yes |
| S15 | restic design, Threat Model section, `restic/restic @ master : doc/design.rst` | restic | master HEAD | 2026-09-29 | Yes |
| S16 | rest-server `restic/rest-server @ master : repo/repo.go` (saveBlob L549–634, deleteBlob L737, config O_EXCL L307) | restic | master HEAD | 2026-09-29 | Yes |
| S17 | Borg 1.4 usage notes, `borgbackup/borg @ 1.4-maint : docs/usage/notes.rst` (Append-only mode, Drawbacks) | BorgBackup | 1.4-maint HEAD | 2026-09-29 | Yes |
| S18 | Kopia server `kopia/kopia @ master : internal/server/grpc_session.go` (handleWriteContentRequest) and `repo/grpc_repository_client.go` | Kopia | master HEAD | 2026-09-29 | Yes |
| S19 | Tahoe-LAFS, `tahoe-lafs/tahoe-lafs @ master : docs/convergence-secret.rst` and `docs/architecture.rst` | Tahoe-LAFS | master HEAD | 2026-09-29 | Yes |
| S20 | Tailscale TKA source, `tailscale/tailscale @ main : tka/sig.go, tka.go, aum.go, state.go` (scout read) | Tailscale | main HEAD | 2026-09-29 | Yes (code); prose docs blocked |
| S21 | Ente server `ente-io/ente @ main : server/pkg/controller/file.go` and `architecture/README.md` (scout read) | Ente | main HEAD | 2026-09-29 | Yes |
| S22 | Hofmann & Truong, "End-to-End Encrypted Cloud Storage in the Wild: A Broken Ecosystem", ACM CCS 2024, https://eprint.iacr.org/2024/1616 | authors | 2024 | 2026-09-29 (search extract only; blocked) | Primary but not read |
| S23 | Bellare, Keelveedhi, Ristenpart, "Message-Locked Encryption and Secure Deduplication", EUROCRYPT 2013, https://eprint.iacr.org/2012/631 | authors | 2013 | 2026-09-29 (search extract only; blocked) | Primary but not read |
| S24 | Backendal, Haller, Paterson, "MEGA: Malleable Encryption Goes Awry", https://mega-awry.io/ ; Albrecht et al., "Share with Care: Breaking E2EE in Nextcloud", https://eprint.iacr.org/2024/546 | authors | 2022; 2024 | 2026-09-29 (search extracts) | Primary but not read |
| S25 | restic issue #22057, https://github.com/restic/restic/issues/22057 (client-supplied `--time` vs retention) | community | opened 2026-09-08 per scout | 2026-09-29 (scout read; could not re-read) | No |
| S26 | Cloudflare Workers Spectre reports (The Hacker News, eSecurity Planet, Aug 2026); Cloudflare blog post blocked | press | 2026-08 | 2026-09-29 (search extracts) | No |
| S27 | R2 presigned PUT cannot cap size (AnswerOverflow / Cloudflare Community threads) | community | 2025 | 2026-09-29 (search extracts) | No |
| S28 | Microsoft Threat Modeling Tool threats (STRIDE), `MicrosoftDocs/azure-docs @ main : articles/security/develop/threat-modeling-tool-threats.md` | Microsoft | ms.date 2017-08-17 | 2026-09-29 | Yes |
| S29 | OWASP pytm on PyPI (https://pypi.org/pypi/pytm/json, 1.4.0 uploaded 2026-07-06); Threagile on proxy.golang.org (v0.9.1, 2024-07-30) | OWASP; Threagile | as stated | 2026-09-29 | Yes (metadata) |
| S30 | CE spike note `docs/research/content-encryption-format.md` (§8.5, §9–§12, §16) and spike code `spikes/content-encryption/` | this repo (T1 spike 2) | 2026-09-29 | 2026-09-29 | Yes (in-repo evidence) |

## Claims

Skeptic columns are blank: this is the analyst draft. The **Key?** column marks the claims skeptics should attack first.

| # | Claim | Sources | Key? | Skeptic 1 | Skeptic 2 | Skeptic 3 | Verdict |
|---|---|---|---|---|---|---|---|
| C1 | An R2 presigned URL lets **anyone holding it** perform one operation (GET/HEAD/PUT/DELETE) on one object until expiry (1 s to 7 d). It is reusable until then. It is minted offline from R2 API credentials with SigV4, with no call to R2. Cloudflare says to treat it as a bearer token. | S1 | Yes | | | | pending |
| C2 | On R2, two writers to the same key: last to complete wins. The same multipart part uploaded twice: last wins. The compatibility table adds that uploading the same part number replaces the earlier part. | S7, S2 | Yes | | | | pending |
| C3 | R2 PutObject supports If-None-Match (and If-Match, Content-MD5). The CompleteMultipartUpload row lists no conditional headers. Cloudflare documents only Content-Type as a signed-header abuse control on presigned URLs. Whether a signed `If-None-Match: *` on a presigned PUT, or any create-only rule on multipart completion, is enforced is **undocumented** (C1-S1). | S1, S2 | Yes | | | | pending |
| C4 | Temporary credentials can be scoped to one bucket, an explicit action list (e.g. PutObject without DeleteObject) and exact object keys. Action scoping works only with **local** HS256 signing using the parent secret, so whoever holds the parent secret (the Worker) can mint any scope. | S4 | Yes | | | | pending |
| C5 | Write-without-delete does not mean no overwrite: PutObject on an existing key replaces it (C2). Append-only on R2 therefore needs unique keys or conditional writes, not just action scoping. | S2, S4, S7 (inference) | Yes | | | | pending |
| C6 | Bucket-lock rules (up to 1,000 per bucket, by prefix; Age, Date or Indefinite; the strictest wins; they override lifecycle) block delete and overwrite. Anyone with bucket-config rights can remove them, so they do not stop a malicious account holder. An Age lock on `staging/` would also block the homelab's own post-commit delete. | S6 (+ inference) | No | | | | pending |
| C7 | R2 object-create events fire on PutObject, CopyObject and CompleteMultipartUpload, **including overwrites**, and carry size and eTag. Queues delivers at least once. Events are cloud-originated and unauthenticated end to end, so ingest must be idempotent and treat events only as hints. | S8, S10 | Yes | | | | pending |
| C8 | age authenticates the header only relative to the sender-chosen file key (HMAC key = HKDF(file key, "header")). The spec invokes an "expectation of authentication" only for scrypt. So anyone with the homelab public key, including Cloudflare, can create a fully valid object; provenance needs a device signature. | S13 (+ inference); S30 R-3 | Yes | | | | pending |
| C9 | Under ADR-0001 §4 as written (dedup-ID object keys, Worker-reported "committed", no receipts), a malicious or compromised control plane can make a device believe a file is stored at home when it is not: **silent loss**. | ADR-0001; C2; tabletop §6–§7 | Yes | | | | pending |
| C10 | With SR-03…SR-11 in place, every D1-S2 scenario (§7) ends in detection and automatic re-upload, on one condition: the honest device keeps the file until it holds a receipt. The CE spike tests `commit:*` already reject poisoning, swap and impersonation at ingest; the Worker-side reset and re-upload loop is **not yet built or tested** (D4-S1). | S30; tabletop §7 | Yes | | | | pending |
| C11 | If device public keys reach the homelab only through the Worker, a malicious cloud can substitute them. It could then redirect admin restores (the homelab re-encrypts plaintext to the attacker), receive a dedup secret sealed "to the device", and forge records in that device's name. | ADR-0001 §6, ADR-0002 §2; S20 (analogue); S22 (precedent, extract only) | Yes | | | | pending |
| C12 | Any holder of the dedup secret (any enrolled or stolen device), combined with the Worker's "which are missing?" answer, is a confirmation-of-a-file oracle over the whole family's library. Tahoe documents the same attack class and says the only defence is keeping the secret. | S19 (+ inference); S30 R-5, C8 | Yes | | | | pending |
| C13 | rest-server refuses to overwrite (403 if the path exists) and checks SHA-256(body) = ID on upload. Kopia derives the content ID server-side. Both work because their servers can compute the ID. Reliquary's cloud cannot (the ID is an HMAC over plaintext under a secret it lacks), so ID-to-content binding can **only** be checked at the homelab. Kopia's client also trusts the server's "exists" answer, which Reliquary must not. | S16, S18 (+ inference) | Yes | | | | pending |
| C14 | Revocation timing is stated two ways by Cloudflare. Permission changes on API keys are eventually consistent (up to about a minute, S7). Revoking a parent token stops derived temporary credentials "immediately" (S4). Neither covers already-issued presigned URLs, which stay valid until expiry. | S4, S7 | Yes (BUD-REVOKE) | | | | pending |
| C15 | restic's threat model: a compromised host with append-only access cannot alter old backups, but can make new ones untrustworthy and game `forget` into deleting the good ones. Storage-location deletion is out of scope. Size and timing leak to storage and network observers. Borg notes: a later non-append-only write makes append-only "moot", and a few deleted chunks can silently corrupt an archive. | S15, S17 | No | | | | pending |
| C16 | Comparable E2EE storage services failed under malicious-server analysis mainly through unauthenticated key material and metadata that the server relays (Hofmann & Truong 2024: 4 of 5 providers; MEGA 2022; Nextcloud 2024). | S22, S24 (extracts only) | No (precedent) | | | | Secondary only until read |
| C17 | The Workers R2 binding's `put()` accepts `onlyIf` conditionals and one integrity hash (md5/sha1/sha256/sha384). A Worker-proxied upload could therefore enforce create-only writes and a ciphertext hash at the edge, but a compromised Worker can skip both. | S9 | No | | | | pending |

## Findings

### 1. Principle adopted for v0: the cloud is trusted for availability only

Tahoe-LAFS states the target property directly: storage servers "may be able to deny service" but cannot break confidentiality, integrity or unforgeability (S19, architecture.rst). Tailnet Lock applies the same idea to key distribution (S20). For Reliquary this becomes **SR-01**. Every value that decides one of the following must be verifiable with a key that Cloudflare does not hold:

- whether data is safe;
- whose key is trusted;
- what gets decrypted, or to whom it is re-encrypted.

Otherwise the value is recorded as a required change (§5). Confidence: high that this is the right target, because CLAUDE.md says "treat the cloud API as under attack" and ADR-0001 says the cloud "never sees plaintext". Medium that v1 can meet it fully: the device-key question (C11) depends on D3 and OD-05.

### 2. What R2 itself can and cannot enforce (C1–C7, C14, C17)

**R2 can enforce:**

- create-only single PUTs (If-None-Match), provided the header can be bound to a presigned URL (unproven);
- create-only CopyObject via the `cf-copy-destination-if-none-match` extension (S3);
- per-object, per-action temporary credentials (C4);
- prefix bucket locks (C6).

**R2 cannot be relied on for:**

- binding the uploaded bytes to the authorisation. The documented example signs only `host` with `UNSIGNED-PAYLOAD` (S1). Content-MD5 on PutObject is supported (S2), but whether it can be signed into a presigned URL is untested;
- create-only multipart completion (C3);
- a size cap on presigned PUTs (S27, secondary);
- anything at all against the account holder: locks can be removed (S6), and whoever holds the Worker's parent secret can mint any credential (C1, C4).

**Consequence:** R2 controls limit a *device* or a *leaked URL*. They do nothing against a malicious control plane. The design therefore uses R2 controls to cut cost and nuisance, and relies on homelab verification plus receipts for integrity.

### 3. Tabletop D1-S1 (malicious cloud): outcome

See §5 (value classification) and §6 (attack walkthrough). **Pass criterion (PLAN):** "Every value that crosses Cloudflare is either verified with a key the cloud lacks, or recorded as a required change." **Result: met as a paper exercise.** Of the 22 values in §5:

- V22 is already authenticated by ADR-0002 (update signing).
- Five groups are accepted as unauthenticated because they cost only availability, money or metadata: V3, V5, V6/V7, V20 and V21.
- Every other value needs a change from ADR-0001/0002 as written, and each change is recorded as an SR. The CE spike already designs and tests some of them: V1, V2, V8, V12, V13 and V14. This tabletop adds the rest: V4 device binding, V9, V10, V11, V15, V16 delivery, V17, V18 and V19.

All five changes the plan expected were confirmed:

- per-upload staging keys;
- homelab-signed receipts;
- a pinned homelab key;
- device-signed manifests or records;
- the dedup secret delivered encrypted by the homelab.

The tabletop found three more:

- **device-key authentication independent of the Worker** (SR-14). This is the largest remaining gap, because it guards restore redirection;
- **a homelab-signed restore manifest** (SR-16). ADR-0001 §6 restores are age files to the device key, which anyone can forge (C8);
- **a signed freshness heartbeat** (SR-18), so a cloud that freezes or withholds receipts shows as "home not confirming" rather than looking like silence.

### 4. Tabletop D1-S2 (dedup poisoning, claim squatting): outcome

See §7. **Pass criterion (PLAN):** "Detection plus automatic re-upload with no silent loss; otherwise a protocol change." **Result:**

- **Fails** under ADR-0001 §4 as written. An overwrite of a dedup-ID-keyed object, combined with Worker-reported "committed", allows silent loss (C9).
- **Passes on paper** with the changes in SR-04…SR-11. Detection is certain, because the homelab recomputes HMAC(dedup key, plaintext) and SHA-256. Automatic re-upload depends on two rules that are not in the CE spike yet:
  - (a) claims are advisory (a stale claim never blocks another uploader);
  - (b) a device holding a dedup hit or a completed upload without a receipt re-queries after T_receipt and uploads.

  The homelab-initiated signed re-upload request (SR-11d) makes recovery fast, within one ingest cycle as D4-S1 requires, rather than only eventual.
- So **a protocol change is required** (OD-04). The formal ideas support it: the MLE "tag consistency" property prevents duplicate faking (S23, extract only), and the observation that tag consistency still allows erasure means detection alone is not enough (scout, PKC 2015, extract only). Reliquary gets consistency from homelab re-verification and gets recovery from re-upload.

### 5. D1-S1: every value that crosses Cloudflare

Legend: **E2E** means verified end to end with a key the cloud lacks, as in the CE spike design. **Change** means it needs an SR not in ADR-0001/0002. **Accept** means it is unauthenticated but only costs availability, cost or metadata (goes to the accepted-risk register).

| # | Value | Direction | Today (ADR-0001/0002) | If the cloud is malicious | Status | SR |
|---|---|---|---|---|---|---|
| V1 | Content ciphertext (age, X25519 to the homelab) | device → R2 → homelab | Confidential; origin unauthenticated (C8) | Substitute or forge an object | E2E via V2 binding (size, SHA-256, dedup ID, header MAC) | SR-03, SR-04 |
| V2 | Metadata record | device → R2 → homelab | Encrypted, unsigned | Forge records as any device | **Change → E2E**: device Ed25519 signature inside the encryption (CE §9) | SR-03 |
| V3 | Dedup ID in queries and claims | device → Worker | Opaque | Lie about presence (V9); learn equality across devices | Accept (metadata); verified at homelab | SR-04, SR-21 |
| V4 | Staging key, upload ID, multipart UploadId | Worker → device | Keyed by dedup ID | Overwrite races, IDOR | **Change**: per-upload random keys bound to the device | SR-07, SR-08 |
| V5 | Presigned URL or temporary credential | Worker → device | Presigned | Point the device at an attacker bucket; over-long lifetime | Accept (ciphertext only; no receipt means not safe) | SR-09 |
| V6 | Object-create event and queue message | R2/Queues → homelab | Notification only; reconcile | Drop, replay, forge | Accept + idempotent ingest | SR-12 |
| V7 | Pending-object listing for reconciliation | D1/R2 → homelab | Trusted | Hide or invent entries | Accept (hiding = availability, detected via V13/V17) | SR-12, SR-13 |
| V8 | "Committed" status | homelab → D1 → device | **The only status signal** | Fake "committed" → silent loss | **Change → E2E**: homelab-signed receipt | SR-05 |
| V9 | "Already have it" (dedup hit) | Worker → device | Skip upload | Suppress uploads forever | **Change**: a hit never counts as safe; receipt timeout | SR-06 |
| V10 | Claim state (pending, TTL) | Worker | Exclusive conditional claim | Squat or hold claims forever | **Change**: advisory claims | SR-10 |
| V11 | Rejection or reset notice | homelab → Worker → devices | Not specified | Suppress resets | **Change**: signed re-upload request plus device timeout | SR-11 |
| V12 | Homelab recipient public key | enrollment | Not specified | Substitute → all future uploads readable by the cloud | **Change → E2E**: pinned trust bundle via QR/kit (CE D-9) | SR-02 |
| V13 | Receipt-signing public key | enrollment | Does not exist | Substitute → forge receipts | **Change → E2E**: in the pinned trust bundle | SR-02 |
| V14 | Trust-bundle rotation | homelab → device | Not specified | Push the cloud's own keys | **Change → E2E**: signed by a pinned key or an offline admin key | SR-02 |
| V15 | Device public keys (Ed25519 signing, X25519 restore) | device → Worker → homelab | Relayed by the Worker | Substitute → redirect restores, capture the dedup secret, forge records | **Change**: authenticate independently of the Worker (D3, OD-05) | SR-14 |
| V16 | Dedup secret | homelab or admin → device | Not specified | Learn it → cloud-side oracle over all IDs | **Change → E2E**: kit, or sealed to an SR-14-authenticated key | SR-15 |
| V17 | Device list and revocation state | Worker ↔ homelab | Worker-held | Un-revoke a stolen device | **Change**: homelab registry is authoritative | SR-17 |
| V18 | Restore object and restore manifest | homelab → R2 → device | age to the device key, unsigned | Substitute restored content (C8) | **Change → E2E**: homelab-signed restore manifest | SR-16 |
| V19 | Health and freshness (last backup, "home reachable") | homelab → Worker → device | Worker timestamps | Freeze or fake freshness | **Change → E2E**: signed heartbeat or checkpoint | SR-18, SR-19 |
| V20 | Nudge emails | Worker → person | Cloud-sent (ADR-0002) | Phishing-grade fake nudges | Accept with content rules; OD-03 decides where email lives | SR-25 |
| V21 | Name, email, device activity times | device → Worker | Plaintext (ADR-0002 §2) | Disclosure | Accept (ADR-0002); minimise under OD-03 | SR-26 |
| V22 | App update metadata and binaries | cloud or CDN → device | minisign-signed (ADR-0002 §5) | Freeze or rollback | E2E for authenticity; freeze and rollback go to D5 | (D5) |

Counts:

- Authenticated today: V22.
- Authenticated once the CE spike design is adopted: V1, V2, V8, V12, V13, V14.
- Changes added by this tabletop: V4 (device binding), V9, V10, V11, V15, V16 (delivery path), V17, V18, V19.
- Accepted as unauthenticated: V3, V5, V6/V7 (with SR-12/13), V20, V21.

### 6. D1-S1 attack walkthrough (malicious control plane)

| # | Attack by a malicious cloud | Against ADR-0001 as written | With the SRs | Residual |
|---|---|---|---|---|
| A1 | Report "committed" for an ID the homelab never saw | Device shows safe; the user deletes the photo → **silent loss** | No receipt → never safe; timeout → re-upload and nudge | None (availability) |
| A2 | Answer "already have it" for everything | Nothing uploads → **silent loss** | A hit is not safe; no receipt → re-query and upload (SR-06). A cloud that keeps lying stalls progress → "not safe" plus stale nudge | Availability; the nudge path runs on the device, not only by email |
| A3 | Delete staged objects before the homelab pulls | Loss if the device believes committed | No receipt → re-upload | Availability, cost |
| A4 | Swap object bytes (its own age file to the homelab key) | Homelab would verify SHA-256 and HMAC (ADR-0001 step 4), so caught if implemented | Caught (SR-04) | None |
| A5 | Serve its own homelab public key at enrollment | All future uploads readable by the cloud | Pinned bundle (SR-02) | Depends on kit and QR integrity (E5, D3) |
| A6 | Substitute a device's public keys | Restores redirected to the cloud → **plaintext disclosure** of what the admin restores; dedup secret captured | SR-14, SR-15, SR-16 | **Open until D3 picks a mechanism.** Interim: admin checks the device key fingerprint out of band before any restore |
| A7 | Replay old receipts or events | Undefined | Receipts bind (device, dedup ID, record digest, size); replay only restates a true fact. Events: idempotent | None |
| A8 | Withhold receipts or freeze status | Undefined | Signed heartbeat (SR-18) → "home not confirming" | Availability |
| A9 | Un-revoke a stolen device, or register a fake one | Fake uploads accepted | Homelab registry authoritative (SR-17); fake device needs SR-14 | Cost of fake uploads |
| A10 | Collect metadata (sizes, IPs, timing, ID equality) | Always possible | Same | Accepted risk AR-05 |
| A11 | Send phishing nudges | Possible | Nudge content rules (SR-25); OD-03 | Social engineering (D3/E5) |
| A12 | Leak or abuse Worker-held secrets (R2 parent token, invite pepper). Cross-tenant Workers Spectre research of Aug 2026 (S26, secondary) shows this is not only an insider risk | Full R2 read and write | Worst case is availability plus cost: R2 holds ciphertext only, and no Worker secret can sign trust (SR-23) | Cost (BUD-ABUSE); invite abuse → D3 |

### 7. D1-S2 scenarios (dedup poisoning, claim squatting)

Setup: device M is malicious (it holds the dedup secret and its own valid credential). Device B is honest and holds file f with ID(f). A "cloud" variant means the control plane colludes with M.

| # | Scenario | ADR-0001 as written | With SR-04…SR-11 | Detection | Recovery | Silent loss? |
|---|---|---|---|---|---|---|
| P1 | M claims ID(f) and uploads f′ ≠ f (duplicate faking) | B is told "pending/present" and skips; the homelab rejects f′; whether B ever re-uploads is **undefined** | Homelab rejects (HMAC mismatch), resets the claim, flags M, and sends a signed re-upload request to devices with records awaiting ID(f) (SR-11). B also re-queries after T_receipt (SR-06) | Certain at ingest | Automatic | **No** |
| P2 | Same, but f′ is garbage that does not decrypt (the erasure case, M′ = ⊥) | As P1 | As P1 | Certain | Automatic | No |
| P3 | M claims ID(f) and never uploads (squatting) | Exclusive claim blocks B until TTL; beyond that undefined | Advisory claim: B uploads anyway once the claim is older than the TTL; M's expired claims are counted and flagged (SR-10) | Worker-side count; homelab sees no record | Automatic after TTL | No (delay ≤ TTL) |
| P4 | M or a leaked URL overwrites B's completed staged object (same key) | Last writer wins (C2) → homelab rejects → B never re-uploads if it trusts "committed" → **loss possible** | Per-upload key known only to B; the URL can't be reused by another device; create-only where R2 enforces it (SR-07/08). If overwritten anyway: rejected, and B has no receipt → re-upload | Certain | Automatic | No |
| P5 | Leaked UploadPart URL replaces one of B's parts before Complete | Part replaced (C2) | Homelab rejects on STREAM auth failure; B has no receipt → re-upload. The CE journal adopts only ETag-matched parts | Certain | Automatic | No |
| P6 | Cloud colludes with M: stages f′ for ID(f), then says "present" to everyone | Silent loss | Present ≠ safe; no receipt for (ID(f), size) → upload | Certain | Automatic | No |
| P7 | Cloud relays a **genuine** receipt for (ID(f), size) from another device | n/a | Correct: the content really is committed. B still sends its own record and waits for its own receipt | — | — | No |
| P8 | M replays an old valid object and record | Duplicate | Idempotent (record digest or sequence); dropped | Yes | n/a | No |
| P9 | M uploads a record claiming B's device ID | Accepted | Signature fails (SR-03), provided B's key is authentic (SR-14) | Yes | n/a | No |
| P10 | Poisoned USB bundle (same attack via sneakernet) | Not specified | Same ingest verification; signed bundle manifest (A4) | Yes | Owner re-seeds from the device | No |
| P11 | Honest B deleted its only copy after the UI said "sent" | Loss | UI never says safe without a receipt (glossary §8; E3) | — | — | **Only if the UX rule is broken** |
| P12 | Hash collision on the dedup key (SVN rep-sharing on SHA-1, 2017; secondary) | n/a | HMAC-SHA-256 or successor (A1); homelab also checks SHA-256 | — | — | No |

**Numbers A3 must set (not invented here):** the claim TTL and T_receipt. Both must fit inside BUD-TTS (24 h to "stored at home" while online) and survive the 14-day queue retention with reconciliation (ADR-0001 §1).

### 8. Security requirements for A3 and C1 (v0)

Numbered for citation. "Owner" is the workstream whose artifact must satisfy the requirement; D1 only states it. Priority P0 means required before the A0 skeleton claims to model the real protocol.

| SR | Requirement | Owner (artifact) | Pri | Traces to |
|---|---|---|---|---|
| SR-01 | **Cloud = availability only.** No decision about safety, key trust, decryption or re-encryption target may rest only on a value from Cloudflare unless it is verified with a key Cloudflare does not hold. | All; A3, C1 | P0 | CLAUDE.md "treat the cloud API as under attack"; §5 |
| SR-02 | **Pinned trust bundle.** The homelab recipient key(s) and receipt/status signing key reach devices only via QR, kit or compiled-in values, pinned by digest. Rotation is signed by a currently pinned key or an offline admin key. Never learned from the Worker. | D3 (ADR-0014), D2; A2 parser | P0 | V12–V14; CE D-9 |
| SR-03 | **Device-signed records.** Every metadata record (and USB manifest) carries the device's Ed25519 signature inside the encryption. The homelab rejects unknown, revoked or mismatched keys and non-canonical bytes. | A2 (ADR-0007), A3, A4 | P0 | V2; CE §9 |
| SR-04 | **Verify before commit.** The homelab commits only after decrypting the whole object and matching size, SHA-256 and dedup ID (correct epoch and key) against the signed record. On failure it stores nothing. | A3 (ADR-0009), A6 | P0 | P1–P6; CE §11 |
| SR-05 | **Receipts are the only "safe".** Homelab-signed receipt binding device ID, dedup ID, record digest, size and commit time. The device verifies it against the pinned key. No Worker field ever marks an item safe. | A3; E3 (ADR-0024) | P0 | V8; A1; CE §10 |
| SR-06 | **Dedup hit ≠ safe; receipt timeout.** A hit only lets the device skip the content upload. The device still sends its record. With no receipt after T_receipt it re-queries and, if the ID is missing or the claim is stale, uploads. | A3; B6 (ADR-0021) | P0 | V9; A2; P1, P6 |
| SR-07 | **Per-upload staging keys.** Staging keys are Worker-generated, random, bound to the authenticated device and upload ID, never reused, never presigned if they already exist. Devices are never given DELETE, CopyObject, List or bucket-config rights. | C1 (ADR-0010 key layout) | P0 | V4; P4; C2, C5 |
| SR-08 | **Create-only where R2 supports it.** Sign `If-None-Match: *` into single-PUT URLs if C1-S1 shows R2 enforces it. Record the result for multipart completion. If R2 does not enforce it, SR-07 plus homelab verification are the fallback and the gap is recorded. | C1 (C1-S1) | P1 | C3 |
| SR-09 | **URL and credential scope.** One object per URL or credential; the shortest lifetime compatible with background queues (B4/B2 input); outstanding lifetime within BUD-REVOKE, or the conflict raised to the owner. Sign Content-Type (and Content-MD5/length if C1-S1 shows they can be signed). | C1; D3 | P0 | V5; C1, C14 |
| SR-10 | **Advisory claims.** A claim has a TTL and never blocks another device's upload once stale. Limit outstanding claims per device. Count expired and abandoned claims per device and flag them. | A3; C1; C2 (quotas) | P0 | V10; P3 |
| SR-11 | **Rejection handling.** On a failed verification the homelab (a) keeps nothing, (b) tells the control plane to reset the claim, (c) logs and flags the uploading device to the admin, (d) sends a homelab-signed re-upload request to devices whose records await that ID. | A3; D4 (recovery procedure) | P0 | V11; P1, P2; D4-S1 |
| SR-12 | **Events are hints; ingest is idempotent.** Duplicate, replayed or forged events cause at most a re-verification. Reconciliation by listing is the path of record. | A3; C1 | P0 | V6, V7; C7 |
| SR-13 | **Gap detection.** Records carry a per-device monotonic sequence number, or an equivalent signed checkpoint, so the homelab can detect suppressed or reordered records. Exact design is A3's (for example scan checkpoints, H4). | A3; A2; H4 | P1 | V7; §6 A8 |
| SR-14 | **Device keys authenticated without trusting the Worker.** The homelab accepts a device's signing and restore keys only via a path Cloudflare cannot forge. Candidates: invite-bound MAC with a memory-hard KDF; co-signature by an already-trusted device (Tailnet Lock pattern); admin fingerprint check. This is required before any restore to that device and before sealing the dedup secret to it. | D3 (ADR-0014; OD-05) | P0 for restore and secret delivery; P1 overall | V15; A6; C11 |
| SR-15 | **Dedup secret never in plaintext through Cloudflare.** It is delivered in the kit or sealed by the homelab to an SR-14-authenticated device key. | D2 (ADR-0008), D3 | P0 | V16; CE C2 |
| SR-16 | **Signed restore manifest.** Restores carry a homelab-signed manifest (hashes and sizes, with names inside the encryption). The device verifies plaintext against it before presenting. | A8 (ADR-0028) | P1 | V18; C8 |
| SR-17 | **Homelab-authoritative revocation.** The homelab rejects records signed by revoked keys whatever the cloud says. The homelab pushes a signed revocation list so the Worker stops issuing URLs within BUD-REVOKE. | D3; C1; A3 | P1 | V17; A9 |
| SR-18 | **Signed freshness.** The homelab signs a periodic heartbeat or checkpoint (time, and per-device last-committed marker). A device shows "home not confirming" when none has arrived within T_fresh. | A3; E3 | P1 | V19; A8 |
| SR-19 | **Homelab time for decisions.** Health, nudge and any future pruning decisions use the homelab's receive or commit time. Device-supplied and cloud-supplied times are context only. | A3; H4; E3 | P1 | S15, S25 (restic `forget` gaming) |
| SR-20 | **No remote destruction.** Nothing a device or the cloud sends can delete or rewrite data in the homelab store. Pruning is manual, admin-only, with a separate credential and a verify-before-destroy step (Borg lesson). | A6 (ADR-0012), D4-S4, C8 | P0 | CLAUDE.md append-only and retention; C15 |
| SR-21 | **Presence-query limits.** Rate-limit "which are missing?" per device and globally, and log volume anomalies. Answer only for IDs in the device's current batch. This bounds, but does not remove, the dedup oracle. | C1; C2 | P1 | V3; C12 |
| SR-22 | **Hostile-input parsing.** Records, receipts, manifests, bundles, trust bundles and age headers relayed by the cloud are parsed with strict limits (size, nesting, duplicate keys, canonical encodings) in memory-safe code, before expensive work (Tailscale TKA CBOR limits as precedent). | A2; A3; A4; D4-S5 | P0 | §Questions 9 |
| SR-23 | **The Worker holds no trust-forging key.** The Worker holds no key that signs receipts, device lists, trust bundles or restore manifests. Assume every Worker secret can leak; a leak must cost only availability, money or invite abuse. | C1; D2 (key inventory) | P0 | A12 |
| SR-24 | **Size and cost bounds.** The device declares the size at URL issuance. The Worker or homelab compares it with the event or HEAD size and flags or aborts mismatches. Per-device byte and operation quotas within BUD-ABUSE. | C1; C2 | P1 | S27 (secondary); BUD-ABUSE |
| SR-25 | **Nudge content rules.** Email and push nudges never contain install links, codes, or requests to act outside the app. | C3; E3; D6 | P1 | A11 |
| SR-26 | **Cloud metadata minimisation.** No filenames, paths or plaintext hashes in the cloud. Metadata-object keys do not contain the dedup ID (CE §9). Worker logs are configured without personal data where possible (D6-S2). | C1; D6 | P1 | R-44 |

**Minimum set for the A0 walking skeleton (v0):** SR-01, 03, 04, 05, 06, 07, 10, 11 (a–c), 12, 20 (plain CAS with no delete path), 22 (basic limits). SR-02 can be a static pinned test bundle. SR-14 and SR-15 are not needed while a static test credential and a test dedup secret are used (PLAN §4.1 cycle C1 ↔ D3). They are needed before any real family data (Gate A for SR-15; Gate C for SR-14).

### 9. v0 threat register content (to be lifted into `docs/security/threat-model.md`)

#### 9.1 Trust boundaries

| TB | Boundary | Trust assumption (v0) |
|---|---|---|
| TB1 | Family device (app, OS, local DB) ↔ network | The device is trusted for its own data until compromised. Its hash cache is a plaintext inventory. |
| TB2 | Cloudflare (Workers, D1/DO, R2, Queues, email) | **Availability only** (SR-01). Not trusted for confidentiality of anything but ciphertext and opaque IDs, nor for integrity. |
| TB3 | Homelab edge (outbound only) ↔ ingest VM | Ingest parses hostile input (SR-22); USB ingest in a disposable VM (D4). |
| TB4 | Ingest VM ↔ permanent store and catalog | The store must survive a compromised ingest VM (SR-20; D4-S4). |
| TB5 | Admin workstation, key ceremony machine, offline keys | Trusted; out of Wave 1 scope (D2). |
| TB6 | Physical: USB kits, printed cards, post | Carries trust anchors (SR-02); tampering risk (D5, E5). |
| TB7 | Update channel and CI | Signed updates (ADR-0002 §5); D5. |

#### 9.2 Assets (Wave 1 subset, ranked by impact)

1. Plaintext content and metadata (homelab store, catalog, devices).
2. Homelab decryption key(s).
3. Homelab receipt/status signing key. **Forgery means silent loss.**
4. Dedup secret (oracle; every ID depends on it).
5. Device signing and restore keys.
6. "Safe" status as the family sees it (receipts held).
7. Cloudflare account and Worker secrets (R2 parent token, invite pepper).
8. Invite codes, pairing and QR tokens.
9. Family PII in the cloud (name, email, activity).
10. Staged ciphertext (availability only).

#### 9.3 Attacker profiles

| ID | Profile | Wave 1 capability assumed |
|---|---|---|
| AP1 | Internet attacker | Can reach the Worker API; may hold leaked URLs. |
| AP2 | Cloudflare-side: insider, account takeover, legal compulsion, compromised Worker code or secrets (incl. cross-tenant leakage, S26) | Full control of TB2 (§6). |
| AP3 | Device thief | Holds one device, its credential and the dedup secret until revoked. |
| AP4 | Ransomware on a device | As AP3, plus encrypting local files and uploading garbage. |
| AP5 | Curious or malicious relative | As AP3 on their own device; the dedup oracle (§Questions 3b). |
| AP6 | Phisher (fake kit, fake nudge, fake update) | Wave 2 (D3, D5, E5). |
| AP7 | Compromised dependency or CI | Wave 2 (D5). |
| AP8 | Compromised ingest VM | §Questions 3c; Wave 2 (A6, D2, D4). |
| AP9 | Estranged member, incapacitated owner | Wave 2 (D2, D6, E7). |

#### 9.4 Threats (STRIDE, Wave 1 components: cloud API and ingest protocol)

| ID | STRIDE | Element | Threat | Attacker | Mitigation (SR) | Residual / owner |
|---|---|---|---|---|---|---|
| T-01 | S | Enrollment → homelab key | Substituted recipient key | AP2 | SR-02 | Kit integrity (D3, E5) |
| T-02 | S | Device key registration | Substituted device keys → restore redirection, secret capture | AP2 | SR-14, SR-15, SR-16 | **Open (D3, OD-05)** |
| T-03 | S | Metadata record | Records forged as another device | AP2, AP5 | SR-03, SR-14 | — |
| T-04 | T | Staged object | Overwrite or replace (same key, part replace) | AP1 (leaked URL), AP3 | SR-07, SR-08, SR-04 | Multipart create-only unproven (C1-S1) |
| T-05 | T | Dedup index | Duplicate faking / poisoning | AP3–AP5, AP2 | SR-04, SR-06, SR-11 | — (D4-S1 proves) |
| T-06 | T/D | Claims | Claim squatting | AP3–AP5 | SR-10 | Delay ≤ TTL |
| T-07 | S/T | Status | Fake "committed" or fake "present" | AP2 | SR-05, SR-06 | — |
| T-08 | R | Audit | The cloud rewrites history of what was uploaded | AP2 | Receipts on devices; homelab append-only log | Merkle log optional (Wave 2) |
| T-09 | T | Events and queue | Forged, replayed or dropped events | AP2 | SR-12, SR-13 | Availability |
| T-10 | T | Restore | Substituted restore content | AP2 | SR-16 | — |
| T-11 | I | Presence query | Dedup oracle (confirm file; learn remaining info) | AP3–AP5 | SR-21 | **Accepted risk AR-06** |
| T-12 | I | Cloud metadata | Sizes, timing, IPs, ID equality, PII | AP2 | SR-26; padding decision (A2/F3, CE D-7) | **Accepted risk AR-05** |
| T-13 | I | Dedup secret | Leaked secret + cloud ID history → historical file testing | AP2 + AP3 | SR-15; rotation (A1/D2) | AR-06; CE D-6 |
| T-14 | D | Staging | Delete before pull; withhold receipts; freeze | AP2 | SR-06, SR-18 | **Accepted risk AR-04** |
| T-15 | D | Cost | Oversized or garbage uploads; operation floods | AP1, AP3, AP4 | SR-09, SR-21, SR-24 | BUD-ABUSE (owner sets) |
| T-16 | E | Homelab parsers | Crafted record, receipt or manifest exploits ingest | AP2, AP3 | SR-22 | D4-S5 |
| T-17 | E | Worker | IDOR: act on another device's upload or claim | AP3, AP5 | SR-07 (binding); SR-01 limits the impact | — |
| T-18 | T | Homelab store | Device- or cloud-driven deletion; `forget`-style gaming | AP2, AP4 | SR-19, SR-20 | D4-S4 |
| T-19 | S | Revocation | Stolen device keeps uploading | AP2, AP3 | SR-17 | Within BUD-REVOKE (C14 conflict) |
| T-20 | S | Nudges | Fake nudge leads the user to malware or a code leak | AP2, AP6 | SR-25 | D3, E5 |

LINDDUN items in this slice: Linking (ID equality across devices, T-12); Identifying (IP and PII, T-12); Detecting (dedup oracle, T-11); Data disclosure (T-02, T-13); Unawareness (users believing the cloud holds plaintext → D6-S3). The full LINDDUN GO walkthrough is Wave 2.

#### 9.5 Accepted-risk candidates for OD-17

| AR | Risk | Why accepted | Settled? |
|---|---|---|---|
| AR-01 | The admin can read everything | Escrow trust model | Yes (CLAUDE.md) |
| AR-02 | Single admin (bus factor) | Owner model; D2/E7 reduce it | Yes (OD-17 as listed) |
| AR-03 | No off-site copy of the homelab | Out of scope for now | Yes (CLAUDE.md) |
| AR-04 | Cloudflare can deny service (drop, delete staged, withhold receipts). Detected, not prevented | Inherent in a single-vendor relay | **New: owner to accept** |
| AR-05 | Cloudflare sees exact sizes, timing, IPs, device count, per-device activity, ID equality across devices, plus name and email (ADR-0002) | Padding is costly (CE D-7); email is under OD-03 | **New: owner to accept** |
| AR-06 | Any holder of the dedup secret can use the Worker as a confirmation-of-a-file oracle, bounded by rate limits. A leaked secret plus the cloud's ID history allows testing of all historical IDs (no forward secrecy) | Needed for cross-user dedup | **New: owner to accept; rewords ADR-0001 §2 (CE D-6)** |
| AR-07 | Single-copy window: between staging and commit, and afterwards only at the homelab | Follows from AR-03 | Yes (OD-17 as listed) |
| AR-08 | A compromised ingest VM with an online key discloses everything it can decrypt and can sign false receipts for new uploads | Reduced by D2 (custody) and A6/D4 (store isolation) | **New: to revisit at Gate A** |

### Alternatives compared

| Option | Fit with settled requirements | Pros | Cons | Evidence |
|---|---|---|---|---|
| **Staging key = dedup ID** (ADR-0001 §4 as written) | Conflicts with "devices can only append" (overwrite = rewrite) | Idempotent keys; simple | Last-writer-wins; leaked URL or squatter can replace content; cannot tell uploads apart | C2, C5, P4 |
| **Staging key = per-upload** (`staging/<dedup_id>/<upload_id>`, CE §8.5) | Fits | No overwrite between uploads; per-device binding; duplicates resolved at the homelab | More objects; the homelab dedups; the dedup ID is still visible in the key (acceptable: the cloud sees IDs anyway) | S30, C2 |
| Direct presigned PUT / UploadPart | Fits | No Worker bandwidth; standard | Body not bound; size not capped; multipart create-only unproven | C1, C3 |
| Temporary credentials scoped to the exact object key and PutObject + Multipart actions | Fits | One credential per multipart upload; no DELETE; one bucket | Local signing only for actions; same bearer semantics; minted by the Worker (no help against AP2) | C4 |
| Worker-proxied upload (`put` with `onlyIf` + sha256) | Fits | Create-only and hash enforced at the edge | All bytes through the Worker (request limits and CPU not checked here); no help against AP2 | C17 |
| **Status via Worker "committed"** | Violates SR-01 | Simple | Silent loss (C9) | §6 A1 |
| **Per-file homelab-signed receipts** (CE §10) | Fits | Device-verifiable; tested in the CE spike | No freshness signal on its own → add SR-18 | S30 |
| Merkle log with signed checkpoints (C2SP tlog-checkpoint, device witnesses) | Fits | Anti-rewrite, anti-split-view, audit trail | Complexity; not needed for v0 | S14 |
| **Exclusive claims** (ADR-0001 §4) | Fits on paper | Saves duplicate bandwidth | Squatting blocks others | P3 |
| **Advisory claims with TTL** | Fits | Squatting reduced to delay; no loss | Occasional duplicate uploads (cost) | P3 |
| Staging-prefix bucket lock (Age) | Fits | Stops deletion by leaked non-admin tokens | Blocks the homelab's own delete; storage cost; no help against AP2 | C6 |
| No staging lock (v1) | Fits | Simple; the homelab deletes after commit | Deletion by a leaked token costs availability only (the receipt rule covers it) | C6, §6 A3 |
| Device keys trusted via the Worker | **Violates SR-01** | Zero-effort enrollment | Restore redirection (C11) | §6 A6 |
| Device keys via invite-bound MAC / co-signing / admin fingerprint / key transparency | Constrained by "near-zero enrollment" and "never requires the admin" (OD-05) | Removes T-02 | Effort or UX cost; D3 must weigh | S20, C11 |

### Similar work and lessons

| Project or paper | What they do | Borrow or avoid | Source |
|---|---|---|---|
| restic / rest-server | Append-only enforced by the server; refuses overwrite; SHA-256 = ID checked on upload; explicit threat model incl. `forget` gaming and metadata leaks | Borrow the explicit threat-model style and the server-side no-overwrite rule. Note that our cloud cannot check the ID (C13) | S15, S16 |
| Borg append-only | Low-level append-only; `prune`/`delete` still allowed; a later compaction makes deletions permanent; "check before compact" | Avoid: an append-only mode that can be switched off or undone by routine maintenance. Borrow verify-before-destroy (SR-20) | S17 |
| Kopia repository server | Server derives the content ID; the client verifies the returned ID; client trusts "exists"; HMAC secret handed to every client | Borrow "the party that stores derives the ID" (our homelab). Avoid trusting "exists" (SR-06) | S18 |
| Tahoe-LAFS | Convergence secret = dedup domain; confirmation and learn-remaining attacks; storage can only deny service | Borrow the target property (SR-01) and the honest disclosure of oracle risk (AR-06) | S19 |
| Tailscale Tailnet Lock | Node keys must carry a TKA signature the coordination server cannot make; single-use pre-signed credentials; disablement secrets | Candidate pattern for SR-14 (D3) | S20 |
| Ente | Server-generated per-upload object keys `<user>/<uuid>`; key-ownership check at commit; Verification ID for relayed public keys | Borrow per-upload keys and the commit-time ownership check (SR-07); fingerprint check as the interim for SR-14 | S21 |
| Hofmann & Truong 2024; MEGA; Nextcloud | Malicious-server attacks mainly through unauthenticated keys and metadata relayed by the server | Checklist for §5: every relayed key and blob must be authenticated | S22, S24 (extracts) |
| MLE / duplicate faking | Tag consistency prevents duplicate faking; erasure still possible | Detection plus re-upload (SR-06, SR-11) | S23 (extract) |
| Tarsnap key capabilities | Write-only keys on backup hosts | Devices already hold only the public key (ADR-0001) | scout (tarsnap-keymgmt man page) |

### Tools and libraries

| Name | Purpose | Licence | Maturity | Source |
|---|---|---|---|---|
| Markdown register + Mermaid DFD | v0 register (this note, then `docs/security/threat-model.md`) | — | — | Recommended for v0: fits the repo and review flow |
| OWASP pytm | Threat model as code (DFD, sequence diagrams, generated threats) | MIT (scout) | 1.4.0 uploaded 2026-07-06 | S29 |
| Threagile | YAML model + risk rules | (not checked) | v0.9.1, 2024-07-30 (less active) | S29 |
| LINDDUN GO | Privacy card walkthrough | (not checked; site blocked) | — | Wave 2 (D6 joint) |
| OWASP Threat Dragon, Deciduous | DFD editor; attack trees | (not checked) | — | Wave 2 (attack trees for the top 5 catastrophic outcomes) |

Recommendation: keep the register in Markdown with stable IDs (T-xx, SR-xx, AR-xx) now. Reconsider pytm in Wave 2 only if the register outgrows hand maintenance. This is low stakes and easy to reverse.

## Spikes

The spike runner is running D1-S1 and D1-S2 in parallel. Its results replace this placeholder.

| Spike | Exec tag | Budget IDs | Data class | Status | Result |
|---|---|---|---|---|---|
| D1-S1 Malicious-cloud tabletop | CT | BUD-TTS, BUD-REVOKE, BUD-ABUSE | SYN → results | Analyst paper walkthrough done (§5, §6); spike runner result pending | Paper result: criterion met; every non-accepted value maps to an SR (§5) |
| D1-S2 Dedup poisoning and claim squatting tabletop | CT | BUD-TTS | SYN → results | Analyst paper walkthrough done (§7); spike runner result pending | Paper result: fails under ADR-0001 §4 as written; passes with SR-04…SR-11. Needs D4-S1 harness proof |
| D1-S3 Red team against the full register | CT | — | SYN → results | Not started (Wave 2) | — |

Real R2 was not used. Every R2 behaviour above comes from documentation. C1-S1 (sandbox) must confirm C3 and C14 and the size-cap question (S27).

## Conflicts with settled text

These are never resolved here. Each goes to the owner through OD-04 or OD-17.

1. **ADR-0001 §4 step 2**, "objects are keyed by dedup ID so duplicate uploads are idempotent". This conflicts with SR-07: on R2, last writer wins (C2), so a dedup-ID key lets one upload rewrite another's staged bytes. That contradicts "devices can only append, never … rewrite" (CLAUDE.md). → OD-04.
2. **ADR-0001 §4 step 4**, the homelab "marks it committed". This is the only status signal, and it is unauthenticated to devices (C9). → OD-04: add homelab-signed receipts as the only definition of safe.
3. **ADR-0001 §4 step 2**, the conditional claim is exclusive. SR-10 makes it advisory. → OD-04.
4. **ADR-0001 §2**, "the cloud cannot test for known files". This is true only while no device's dedup secret has leaked (C12; CE D-6). → OD-04 (reword), with AR-06 → OD-17.
5. **ADR-0001 §6** restores to "the requesting device's own public key". Not a contradiction, but safe only with SR-14 and SR-16, and the key authenticity mechanism touches **ADR-0002 §3** "adding devices never requires the admin" (OD-05, Wave 2). Interim for v1: restore is admin-performed, so the admin checks the device key fingerprint out of band before restoring.
6. **ADR-0002 §2**: the Worker checks the invite code at redemption. If the invite code is also used to authenticate device keys to the homelab (one SR-14 candidate), a malicious Worker sees the code at redemption unless only a derived verifier is sent. D3 must design this (D3-S2 brute-force model). Not a conflict yet; flagged.

## Open questions

1. Does R2 enforce `If-None-Match: *` when it is in a presigned PUT's signed headers? Is there any create-only rule for CompleteMultipartUpload? Can Content-MD5 or length be signed? **C1-S1, Wave 1.**
2. What revocation latency applies in practice: "immediately" or "up to a minute" (C14)? And the lifetime conflict between BUD-REVOKE (15 min outstanding) and iOS/Android background queue delay. **C1-S1, D3-S5, B4.**
3. The SR-14 mechanism, and whether it fits "near-zero enrollment" and "never requires the admin". **D3, OD-05 (Wave 2).** Interim rule for v1 restores stated above.
4. Values for T_receipt, claim TTL and T_fresh inside BUD-TTS. **A3.**
5. Should SR-13 use per-record sequence numbers or signed scan checkpoints (H4 glossary)? **A3 with H4.**
6. The primary papers S22–S24 could not be read (eprint blocked). Precedent claims C16 stay "secondary only" until an unblocked route is found. **H1 (source access).**
7. Worker request-size and CPU limits for the Worker-proxied alternative were not checked. **C1.**
8. Ingest-VM compromise (AP8) and the homelab store's immutability. **Wave 2: A6, D2, D4-S4.**

## Recommendation

1. **Decide OD-04 = yes.** Supersede ADR-0001 §4 with:
   - per-upload staging keys;
   - device-signed metadata records;
   - verify-before-commit at the homelab;
   - homelab-signed receipts as the only "safe";
   - advisory claims with a device receipt timeout;
   - signed rejection or re-upload requests;
   - a signed freshness heartbeat.

   Reword ADR-0001 §2's "cannot test for known files". This is the CE spike's D-5 and D-6 plus SR-06, 10, 11 and 18 from this tabletop.
2. **A3 and C1 adopt SR-01…SR-13 and SR-20…SR-24 now.** The A0 skeleton must model at least the minimum set in §8, so Gate B measures the real protocol shape and not ADR-0001's.
3. **Treat device-key authenticity (SR-14) as the top open security item** for D3. Until it is decided, no restore goes to a device whose key fingerprint the admin has not checked out of band, and the dedup secret travels only in the physical kit.
4. **Do not rely on R2 bucket locks or Worker-proxied uploads for integrity.** Neither helps against a malicious control plane. Use R2 conditionals only to reduce cost and nuisance once C1-S1 confirms them.
5. **Put AR-04, AR-05, AR-06 and AR-08 on OD-17** so the owner accepts them explicitly at Gate A.

What would change this: (a) if C1-S1 shows R2 enforces create-only multipart completion, SR-08 becomes stronger, but receipts are still required because AP2 is unaffected; (b) if D3 finds no SR-14 mechanism compatible with near-zero enrollment, the owner must choose between admin-confirmed device keys (OD-05) and accepting restore-redirection risk for devices enrolled without a check; (c) if D4-S1 shows the reset and re-upload loop leaves a window beyond BUD-TTS, then A3 must shorten T_receipt or add homelab push.

## Decision requests

### OD-04: Supersede ADR-0001 §4 (and one §2 sentence) with the malicious-cloud-safe ingest protocol
- **Needed by:** Wave 1 exit.
- **Evidence:** this note (§5–§8); `docs/research/content-encryption-format.md` §8.5, §9–§12, §16 (D-5, D-6); C1-S1 (pending).
- **Options:**

  | Option | What it means for the family | Cost (money and owner time) | Reversibility | Risks |
  |---|---|---|---|---|
  | A. Keep ADR-0001 §4 as written | Simpler; phones may show "backed up" on the cloud's word | None now | Costly later: receipt format and key layout are one-way doors (#5, #7) | Silent data loss under a malicious or compromised Worker; overwrite of staged objects |
  | B. Adopt SR-01…SR-13 (per-upload keys, signed records, receipts, advisory claims, receipt timeout, signed re-upload and heartbeat) | "Safe" means verified at home, always; occasional re-uploads | Build effort in A3, C1 and the clients; small extra R2 operations | The formats become one-way doors at Gate A | Relies on D3 for device-key authenticity (SR-14) |
  | C. B plus a Merkle transparency log with device witnesses | As B, plus a cloud-proof audit trail | More build effort | Can be added later on top of B | Complexity before the skeleton |

- **Recommendation:** B now; revisit C in Wave 2. B is the only option where a compromised Cloudflare costs availability rather than data. The CE spike has already prototyped and tested its core (161/161 checks), and C can be layered on later without changing B's formats.
- **Touches settled text:** ADR-0001 §4 steps 2 and 4, and ADR-0001 §2 ("cannot test for known files"). A superseding ADR draft is needed. Per PLAN §2.1 it would be ADR-0009 (A3) with a note in ADR-0010 (C1); D1 owns "superseding-ADR drafts for any changes to ADR-0001/0002", so D1 supplies the delta text to A3.
- **If no decision by the deadline:** the run assumes B for the A0 skeleton, which uses throwaway v0 keys and no family data. Gate A cannot pass without a decision.

### OD-17 (addition): accept AR-04, AR-05, AR-06, AR-08
- **Needed by:** Gate A.
- **Evidence:** §9.5.
- **Options:** accept as written; or reduce AR-05 with padding (A2/F3, CE D-7); or reduce AR-06 by dropping cross-device dedup (conflicts with CLAUDE.md; not recommended).
- **Recommendation:** accept AR-04 and AR-06. Take AR-05 together with the padding decision (D-7) and OD-03. Revisit AR-08 at Gate A with D2 and A6.
- **Touches settled text:** AR-06 rewords ADR-0001 §2 (covered by OD-04).
- **If no decision by the deadline:** Gate A is blocked (PLAN §4.2 requires the accepted risks to be signed).

## Hand-offs

| To | What | Why |
|---|---|---|
| A3 | SR-03…SR-13, SR-18, SR-19; T_receipt, claim TTL, T_fresh; the superseding text for ADR-0001 §4 | ADR-0009 owns the protocol |
| C1 | SR-07, SR-08, SR-09, SR-12, SR-17, SR-21, SR-23, SR-24, SR-26; C1-S1 checks for C3 and C14 | ADR-0010 and the R2 key layout (one-way door #7) |
| D3 | SR-02, SR-14, SR-17; invite-code-at-redemption concern; interim fingerprint rule | ADR-0014; OD-05 |
| D2 | SR-15, SR-23 (key inventory: the Worker holds no trust keys); AR-08 | ADR-0008 |
| A8 | SR-16 | ADR-0028 |
| D4 | P1–P12 as D4-S1/S2 attack cases; SR-11 recovery procedure; SR-20 | Attack suite |
| E3 | SR-05 ("safe" only with a receipt), SR-18 ("home not confirming"), P11 UX rule | ADR-0024 |
| A2 / F3 | AR-05 size leakage with padding (CE D-7) | ADR-0007 |
| D6 | AR-05, SR-25, SR-26; LINDDUN items | ADR-0027 |
| H1 | Blocked sources listed under Method; the new AR items for the OD-17 row; the T-/SR-/AR- ID scheme | Registries are H1's |
| Synthesis stage | Lift §9 into `docs/security/threat-model.md` (D1-owned; not written by this analyst stage) | PLAN §2.1 |
