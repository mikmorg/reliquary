# D1. Threat model and security requirements (Wave 1: malicious-cloud and dedup-poisoning tabletops)

- **Workstream:** D1 (see `docs/research/PLAN.md`, section "D1.")
- **Status:** Final for Wave 1 (after three-skeptic review). The full register is Wave 2.
- **Date:** 2026-09-29 (last updated 2026-10-06)
- **Feeds:** OD-04 (Wave 1), OD-17 (accepted-risk register), OD-05 (Wave 2, input only), DR-F3-2 (with F3); ADR-0009 (A3), ADR-0010 (C1), ADR-0014 (D3), ADR-0008 (D2), ADR-0028 (A8), ADR-0015 (D5), ADR-0022 (B7), ADR-0024 (E3); one-way doors #5 (receipt format), #7 (R2 key layout), #10 (pinned homelab keys)
- **Normative artifact written:** `docs/security/threat-model.md` (v0 register, **Draft**; D1-owned). It holds the value inventory, threats, SR list, accepted-risk candidates and, in Appendix A, the draft amendment text for ADR-0001 §2 and §4. This note holds the evidence and reasoning.
- **Depends on:** T1 spike 2 (`content-encryption-format.md`, "CE spike"), T2 (`fact-check-adr-0001-0002.md`), F3 (`f3-security-literature.md`, F3-S2), A3 (`a3-ingest-protocol.md`, draft), D2 (`d2-key-hierarchy-custody-recovery.md`, draft), C1-S1 (R2 behaviour; not yet run)
- **Traceability rows advanced:** R-18 (devices only append), R-19/R-20 (encryption, devices cannot read), R-21 (opaque IDs), R-22 (admin escrow), R-38 (no off-site copy → accepted risk), R-44 (cloud never sees plaintext)
- **Scope of this run:** the Wave 1 slice of D1: tabletops D1-S1 and D1-S2, the v0 register for the cloud API, the ingest protocol and the enrollment and restore values that cross Cloudflare, and the security requirements (SR-xx) that A3 and C1 need now.

## Summary

ADR-0001's trust model can hold against a fully malicious Cloudflare, but not as §4 is written. The problem is **not** mainly the dedup-ID staging keys. It is that devices learn "safe" from unauthenticated cloud answers. Under a charitable reading of §4 (a device trusts only a Worker-reported "committed" and re-asks otherwise), the D1-S2 model survives a misbehaving device, a leaked URL and an honest cloud fault. It fails only against a malicious control plane, where one false "already have it" answer makes a device count a file as safe that never reached home (silent loss). It also blames honest devices for others' overwrites.

The fix:

- homelab-signed receipts, verified under a pinned key, as the only "safe";
- device-signed records and verify-before-commit at the homelab;
- devices re-ask every not-green item, with backoff;
- advisory claims that cannot get stuck;
- device keys admitted through a path the Worker cannot forge;
- the dedup secret never in clear through Cloudflare.

Per-upload staging keys stay, but as hygiene (attribution, multipart part mixing, resume, griefing cost), not as what makes integrity hold. With these rules the model passes every property against every attacker within its bounds. The one precondition is that the device still has the file, or its encrypted copy, when a re-upload is needed.

**Recommendation:** decide OD-04 = B (amend ADR-0001 §4 steps 1, 2 and 4, fill its gaps, reword one §2 sentence; draft text in the register's Appendix A). Put the narrowed AR-06, plus AR-04, AR-05, AR-08 and AR-09, on OD-17.

**Confidence:** high for the R2 and age facts (primary sources, verified). Medium for the protocol conclusions: they rest on tabletop reasoning and a small-bound model, which the tally classes as secondary-only. D4-S1 must still prove them on a harness.

## Questions

| # | Question (PLAN D1, Wave 1 slice) | Short answer | Confidence |
|---|---|---|---|
| 1 | Assets | Register §3. Top five: homelab decryption key; receipt/status signing key (forgery means silent loss); dedup secret; device signing and restore keys; the "safe" status the family sees. New: the first installer and trust bundle (V-33). | High |
| 2 | Attackers | Register §4: AP1–AP9. Wave 1 is driven by AP2 (fully malicious Cloudflare side) and AP3–AP5 (one device holding the dedup secret). The cross-tenant Workers reports in AP2 are secondary-only. | High |
| 3a | What holds if the control plane is fully malicious? | Holds: confidentiality of content and metadata (SR-02, SR-14, SR-15, SR-23, SR-27); integrity of the store (SR-03, SR-04, SR-22, SR-14, SR-20); no false "safe" and no silent loss (SR-02, SR-05, SR-06, SR-23, with the SR-28 precondition); no false blame (SR-03, SR-11c). Lost: availability (AR-04) and metadata privacy (AR-05). Register §6(a). | Medium |
| 3b | What holds if one device and the dedup secret are compromised? | Backups cannot be read or deleted; poisoning fails at the homelab; squatting and overwrite cost delay and re-uploads; forgery only as itself. **Not** held: privacy of which files the family holds, through the presence answer (T-11). F3-S2 (emulated) shows rate limits alone do not bound it, while per-person scope removes the cross-person oracle below T_x. Register §6(b). | Medium |
| 3c | What holds if the ingest VM is compromised? | It discloses what it can decrypt and can sign false receipts for new uploads; stored data survives only if the store is append-only against it (SR-20, D4-S4). Wave 2; AR-08 to revisit at Gate A. | Medium |
| 4 | Spoofing: can the cloud substitute the homelab key, a device key, the dedup secret or commit status? | Yes, all four, unless protected: SR-02 (pin), SR-14 (admission), SR-15 (sealed or local delivery), SR-05 (receipts). All 34 values that cross Cloudflare are classified (register §5). | High |
| 5 | Tampering: overwrites, dedup poisoning, claim squatting | Overwrite: R2 is last-writer-wins and a re-sent part number replaces the earlier part (K2), but with receipts and re-asking it costs only a re-upload. Poisoning: always caught at the homelab (SR-04). Squatting: at most a lease-TTL delay (SR-10a). D1-S2 passes with SR-02..SR-07, SR-10, SR-11(b, c). | Medium |
| 6 | Repudiation: where does the audit trail live? | At the homelab (SR-30) and on devices (receipts). Cloudflare audit logs are held by the untrusted party. A Merkle checkpoint log is a Wave 2 option. | Medium |
| 7 | Disclosure: sizes, timing, IPs, dedup oracle, email, local cache | Exact sizes (unless padded; A2/F3), timing, IPs and ID equality are visible to Cloudflare (AR-05). The presence oracle is narrowed by DR-F3-2 (AR-06). Name and email are plaintext under ADR-0002 (OD-03). The hash cache is a plaintext inventory on the device (B6). | High |
| 8 | Denial of service and cost | A malicious cloud can always deny service (AR-04) and can force re-upload loops, so SR-06 needs backoff and a retry budget. Leaked URLs and credentials cost money. Community reports (secondary) say presigned PUTs cannot cap size, so SR-24 checks declared size. | Medium |
| 9 | Privilege escalation via homelab parsers and Worker IDOR | Everything the cloud relays is hostile input (SR-22; D4-S5 tests). Worker IDOR is limited by binding uploads to the device (SR-07) and costs availability only under SR-01. | Medium |
| 10 | (new) Does the first install leak trust to the cloud? | Yes on the ADR-0002 download route if the download is served from Cloudflare: trust on first install with no OS signing. SR-27; open for D3, D5, B7. | Medium |
| 11 | (new) Is "device keeps the file until a receipt" enforceable? | No. Users and OS storage features delete originals regardless of the UI. SR-28 (keep the source reference or encrypted object until the receipt, within BUD-TMP) and AR-09 (visible loss). | Medium |

## Method

- **Sweep:** three scouts (docs, source, community) before the deep read. No separate policy/standards scout; the docs scout covered C2SP and the Microsoft Threat Modeling Tool.
- **Deep read:** full reading of the primary sources in the Sources table, fetched 2026-09-29 from the `cloudflare/cloudflare-docs` production branch and C2SP, restic, Borg, rest-server, Kopia and Tahoe-LAFS repositories via raw.githubusercontent.com. Skeptics re-fetched the Cloudflare and C2SP pages on 2026-10-06.
- **Spikes:** D1-S1 and D1-S2 ran as executable tabletops (see Spikes). In synthesis, a charitable-ADR baseline (V0c) was added to the D1-S2 model at the skeptics' request.
- **Adversarial review:** three skeptics (sources, logic, adversary). The claim verdicts below are the computed tally. Every critical and major issue is answered in "Skeptic issues and how they were handled".
- **Routes used:** raw GitHub mirrors (Cloudflare docs, C2SP, OSS source), WebSearch extracts for blocked papers, in-repo spike evidence.
- **Blocked sources (to report to H1; `sources.md` is H1's file):** developers.cloudflare.com (read through the cloudflare-docs GitHub source instead; same content); eprint.iacr.org and www.iacr.org (Hofmann–Truong, MLE, Nextcloud, proofs-of-ownership); mega-awry.io; brokencloudstorage.info; kclpure.kcl.ac.uk; tailscale.com; words.filippo.io; linddun.org; blog.cloudflare.com; community.cloudflare.com; news.ycombinator.com; github.com web UI (restic issue #22057 could not be re-read). Blocked sources were not replaced with secondary ones: claims that rest on them are marked secondary-only or contested.
- **Stop rule:** the sweep stopped when every Wave 1 key question had a primary source or was explicitly marked as inference or model evidence.

## Sources

| # | Source | Publisher | Version or date | Accessed | Primary? |
|---|---|---|---|---|---|
| S1 | R2 presigned URLs, `cloudflare/cloudflare-docs @ production : src/content/docs/r2/api/s3/presigned-urls.mdx` | Cloudflare | production HEAD | 2026-09-29; re-read 2026-10-06 | Yes |
| S2 | R2 S3 API compatibility, `… : r2/api/s3/api.mdx` | Cloudflare | production HEAD | 2026-09-29; 2026-10-06 | Yes |
| S3 | R2 S3 extensions, `… : r2/api/s3/extensions.mdx` (`cf-copy-destination-if-none-match`) | Cloudflare | production HEAD | 2026-09-29; 2026-10-06 | Yes |
| S4 | R2 temporary credentials, `… : r2/api/s3/temporary-credentials.mdx` | Cloudflare | production HEAD | 2026-09-29; 2026-10-06 | Yes |
| S5 | R2 API tokens, `… : r2/api/tokens.mdx` | Cloudflare | production HEAD | 2026-09-29 | Yes |
| S6 | R2 bucket locks, `… : r2/buckets/bucket-locks.mdx` | Cloudflare | production HEAD | 2026-09-29; 2026-10-06 | Yes |
| S7 | R2 consistency model, `… : r2/reference/consistency.mdx` | Cloudflare | production HEAD | 2026-09-29; 2026-10-06 | Yes |
| S8 | R2 event notifications, `… : r2/buckets/event-notifications.mdx` | Cloudflare | production HEAD | 2026-09-29; 2026-10-06 | Yes |
| S9 | Workers R2 API reference, `… : r2/api/workers/workers-api-reference.mdx` (`put()` `onlyIf` and hashes; `R2MultipartUpload.complete()` takes no conditionals; 7-day auto-abort of incomplete multipart uploads) | Cloudflare | production HEAD | 2026-09-29; 2026-10-06 | Yes |
| S10 | Queues delivery guarantees, `… : queues/reference/delivery-guarantees.mdx` | Cloudflare | production HEAD | 2026-09-29; 2026-10-06 | Yes |
| S11 | Workers Web Crypto, `… : workers/runtime-apis/web-crypto.mdx` (scout read) | Cloudflare | production HEAD | 2026-09-29 | Yes |
| S12 | Audit Logs v2, `… : fundamentals/account/account-security/audit-logs.mdx` | Cloudflare | production HEAD | 2026-09-29 | Yes |
| S13 | age v1 spec, `C2SP/C2SP @ main : age.md` | C2SP | main HEAD | 2026-09-29; 2026-10-06 | Yes |
| S14 | C2SP signed-note and tlog-checkpoint, `C2SP/C2SP @ main` | C2SP | main HEAD | 2026-09-29 | Yes |
| S15 | restic design, Threat Model section, `restic/restic @ master : doc/design.rst` | restic | master HEAD | 2026-09-29 | Yes |
| S16 | rest-server `restic/rest-server @ master : repo/repo.go` (saveBlob, deleteBlob) | restic | master HEAD | 2026-09-29; 2026-10-06 | Yes |
| S17 | Borg 1.4 usage notes, `borgbackup/borg @ 1.4-maint : docs/usage/notes.rst` (append-only mode, Drawbacks) | BorgBackup | 1.4-maint HEAD | 2026-09-29 | Yes |
| S18 | Kopia `kopia/kopia @ master : internal/server/grpc_session.go`, `repo/grpc_repository_client.go` | Kopia | master HEAD | 2026-09-29; 2026-10-06 | Yes |
| S19 | Tahoe-LAFS `tahoe-lafs/tahoe-lafs @ master : docs/convergence-secret.rst`, `docs/architecture.rst` | Tahoe-LAFS | master HEAD | 2026-09-29; 2026-10-06 | Yes |
| S20 | Tailscale TKA source, `tailscale/tailscale @ main : tka/sig.go, tka.go, aum.go, state.go` (prose docs blocked) | Tailscale | main HEAD | 2026-09-29 | Yes (code) |
| S21 | Ente server `ente-io/ente @ main : server/pkg/controller/file.go`, `architecture/README.md` (scout read) | Ente | main HEAD | 2026-09-29 | Yes |
| S22 | Hofmann & Truong, "End-to-End Encrypted Cloud Storage in the Wild: A Broken Ecosystem", ACM CCS 2024, https://eprint.iacr.org/2024/1616 | authors | 2024 | blocked; search extracts and press only | Primary, **not read** |
| S23 | Bellare, Keelveedhi, Ristenpart, "Message-Locked Encryption and Secure Deduplication", EUROCRYPT 2013, https://eprint.iacr.org/2012/631 | authors | 2013 | blocked; extracts only | Primary, **not read** |
| S24 | Backendal, Haller, Paterson, "MEGA: Malleable Encryption Goes Awry", https://mega-awry.io/ ; Albrecht et al., "Share with Care" (Nextcloud), https://eprint.iacr.org/2024/546 | authors | 2022; 2024 | blocked; extracts only | Primary, **not read** |
| S25 | restic issue #22057 (client-supplied `--time` vs retention), https://github.com/restic/restic/issues/22057 | community | 2026-09-08 per scout | could not re-read | No |
| S26 | Workers cross-tenant Spectre reports (The Hacker News, eSecurity Planet), August 2026; Cloudflare blog blocked | press | 2026-08 | 2026-09-29 (extracts) | No |
| S27 | "R2 presigned PUT cannot cap size" (AnswerOverflow / Cloudflare Community threads) | community | 2025 | 2026-09-29 (extracts) | No |
| S28 | Microsoft Threat Modeling Tool threats, `MicrosoftDocs/azure-docs @ main : articles/security/develop/threat-modeling-tool-threats.md` | Microsoft | ms.date 2017-08-17 | 2026-09-29 | Yes |
| S29 | OWASP pytm on PyPI (1.4.0, uploaded 2026-07-06); Threagile on proxy.golang.org (v0.9.1, 2024-07-30) | OWASP; Threagile | as stated | 2026-09-29 | Yes (metadata) |
| S30 | CE spike note `docs/research/content-encryption-format.md` and code `spikes/content-encryption/` | this repo (T1 spike 2) | 2026-09-29 | 2026-09-29 | In-repo evidence |
| S31 | D1-S1 spike `spikes/D1-S1/README.md`, `demos.py`, `evidence/` | this repo | 2026-09-29 | 2026-10-06 | In-repo evidence |
| S32 | D1-S2 spike `spikes/D1-S2/README.md`, `model.py`, `evidence/` including `evidence/v0-charitable/` (added 2026-10-06) | this repo | 2026-09-29; 2026-10-06 | 2026-10-06 | In-repo evidence |
| S33 | F3-S2 dedup-oracle simulation `spikes/F3-S2/README.md` (emulated, not real Cloudflare) | this repo (F3) | 2026-09-29 | 2026-10-06 | In-repo evidence |
| S34 | ADR-0001, ADR-0002 (Accepted) | this repo | 2026-09-29 | 2026-10-06 | Yes (settled text) |

## Claims

Statuses are the computed tally, unchanged: **verified** = a primary source and at least 2 of 3 skeptics did not refute; **secondary-only** = no primary source; **contested** = otherwise. "Corrected statement" is how this note now uses the claim after review; it does not change the status.

| # | Claim (as reviewed) | Sources | Sources skeptic | Logic skeptic | Adversary skeptic | Status | Corrected statement used in this note |
|---|---|---|---|---|---|---|---|
| K1 | An R2 presigned URL is a bearer token: anyone holding it can perform one operation on one object until expiry (1 s to 7 days), reusable until then; minted offline with SigV4, so R2 cannot tell who minted it. | S1 | Upheld | Upheld | Upheld | **Verified** | As stated. |
| K2 | On R2 the last writer to complete wins; re-uploading a part number replaces the earlier part; so dedup-ID staging keys let one upload rewrite another's staged bytes. | S7, S2 | Upheld (per-upload keys not load-bearing for integrity) | Upheld (same caveat) | Upheld (same caveat) | **Verified** | As stated, but it supports per-upload keys for attribution, part mixing, resume and cost, **not** as the reason for OD-04. |
| K3 | R2 lists If-None-Match on PutObject and no conditionals on CompleteMultipartUpload; enforcement on presigned PUT and any create-only multipart completion are undocumented. | S2, S1 | Upheld (adds: the Workers binding's `complete()` takes no conditionals; 7-day auto-abort) | Upheld (adds: CopyObject create-only extension, S3) | Upheld (same) | **Verified** | As stated, plus: a create-only CopyObject from a per-upload key to a final key is documented (S3). |
| K4 | The age header MAC is keyed only from the sender-chosen file key; "expectation of authentication" is stated only for scrypt; anyone with the homelab public key can make a valid object, so provenance needs device and homelab signatures. | S13; S30; S31 demo A1 | Upheld | Upheld | Upheld | **Verified** | As stated. |
| K5 | Under ADR-0001 §4 as written, a malicious or compromised control plane can make a device believe a file is stored when it is not: silent loss. | S34; S7; S32 | Upheld (caveat: V0 defaults) | Upheld (caveat: cause is trust in cloud status) | Upheld (rest it on AP2 only) | **Secondary-only** | Restricted to AP2. The charitable baseline V0c confirms it: silent loss against the malicious cloud, and against no other attacker (Spikes). |
| K6 | With SR-04..SR-11, every D1-S2 poisoning and squatting scenario ends in detection and automatic re-upload, given the device keeps the file. | S30; S16; S18 | Upheld (wrong sources cited; real evidence is S32) | **Refuted** (SR set incomplete; SR-10 contradicts spike rule 4) | Upheld (model V1 ≠ SR text) | **Secondary-only** | "The model's V1 = SR-02, 03, 04, 05, 06, 07, 10(a, b), 11(b, c) plus device admission passes every property within small bounds; L1 is 'can still recover'; the device must still hold the file (SR-28)." Evidence is S32, not S16/S18. |
| K7 | If device keys reach the homelab only through the Worker, a malicious cloud can substitute them, redirect restores, capture a sealed secret and forge records; so device keys need a Worker-independent path (SR-14). | S34; S20 (analogue); S31 demos A5a/A5b | Upheld | Upheld (missed PAKE and USB return trip) | Upheld | **Secondary-only** | As stated; candidate list extended (SR-14). |
| K8 | Any holder of the dedup secret plus the Worker's "which are missing?" answer is a confirmation-of-a-file oracle; the only structural defence is keeping the secret; ADR-0001's "cloud cannot test for known files" holds only while no secret has leaked. | S19; S30 | Upheld (with overstatement) | **Refuted** ("only defence" is false) | **Refuted** (same) | **Contested** | Not used as support. The attack class itself comes from S19 and was executed in D1-S1 (A3a, A3b). "Only structural defence" is withdrawn: the presence answer can be scoped or removed (F3 DR-F3-2; homelab-only dedup). |
| K9 | R2 temporary credentials can be scoped to one bucket, exact keys and an action list, but action scoping works only with local HS256 signing; write-without-delete is not no-overwrite. | S4, S7 | Upheld (time-sensitive) | Upheld (time-sensitive) | Upheld (time-sensitive) | **Verified** | As stated; re-verify "API support coming soon" before ADR-0010 (Gate B). |
| K10 | Cloudflare documents revocation timing two ways (key permission changes up to a minute; parent-token revocation "immediately"); neither covers issued presigned URLs, which stay valid until expiry. | S7, S4 | **Refuted** (URL survival after token revocation unsourced) | Upheld (the two pages are about different operations) | **Refuted** (same as sources) | **Contested** | Not used as support. Narrowed: an individual presigned URL cannot be revoked, and revoking one device at the Worker does not recall URLs already issued to it. Whether rolling the signing token kills outstanding URLs is untested (C1-S1). |
| K11 | Bucket locks cannot protect staging against a malicious account holder; an Age lock would block the homelab's own delete; no staging lock for v1. | S6 | Upheld (locks also prevent overwrite) | Upheld (blocks only for the lock period) | Upheld | **Verified** | As stated; a short Age lock is listed as a non-integrity option for C1. |
| K12 | R2 object-create events fire on overwrites; Queues deliver at least once; events are unauthenticated hints; ingest must be idempotent and reconcile by listing. | S8, S10 | Upheld | Upheld | Upheld | **Verified** | As stated. |
| K13 | rest-server refuses overwrites and checks SHA-256 = ID; Kopia's server derives IDs; both can because the storage side can compute the ID; Reliquary's cloud cannot, so ID-content binding is checked only at home; Kopia's client trusts "exists", which Reliquary must not. | S16, S18 | Upheld (nuances: `--no-verify-upload`; non-atomic stat; Kopia trusts "exists" only ≥ 50,000 bytes and checks the returned ID) | Upheld | Upheld | **Verified** | As stated, with the nuances. A ciphertext-SHA-256 binding could still be checked in the cloud against a leaked URL (not against AP2). |
| K14 | Comparable E2EE storage products failed under malicious-server analysis mainly through unauthenticated keys and metadata (4 of 5 in Hofmann–Truong; MEGA; Nextcloud). | S22, S24 (extracts) | **Refuted** (primary unread; failure classes broader) | **Refuted** (unverified) | Upheld (keep secondary-only) | **Contested** | Precedent only. Not cited as support for any SR or ADR text. |

**Non-key supporting statements (not skeptic-reviewed):** restic's threat model lists `forget` gaming and size/timing leaks, and Borg's append-only mode can be made moot by a later non-append-only write (S15, S17; used only for SR-19 and SR-20 wording). The Workers R2 `put()` accepts `onlyIf` and one integrity hash, so a Worker-proxied single PUT could enforce create-only and a ciphertext hash at the edge, but a compromised Worker can skip both (S9).

**Where contested and secondary-only claims are used.** No recommendation rests on a contested claim alone:

- OD-04 rests on verified K1, K2, K4, K12 and K13, plus K5 and K6 (secondary-only, upheld by 3 and 2 skeptics) and the executed model runs.
- The §2 rewording rests on S19 (the attack class) and D1-S1 demos A3a/A3b, not on K8.
- SR-02 and SR-14 rest on K4, K7 and demos A2 and A5, not on K14.
- SR-09 states a test for C1-S1, not a conclusion from K10.

The owner should still know that the central OD-04 argument (K5) is classed secondary-only. It is a logical consequence of the ADR text, reproduced in a model, not a sourced external fact.

## Findings

### 1. Principle: the cloud is trusted for availability only (SR-01)

Tahoe-LAFS states the target directly: storage servers "may be able to deny service" but cannot break confidentiality, integrity or unforgeability (S19). Tailnet Lock applies the same idea to key distribution (S20). Borg's repository model is the same (F3 note C23). For Reliquary this is SR-01 (register §1). Confidence: high that this is the right target, because CLAUDE.md says to treat the cloud API as under attack. Medium that v1 meets it fully, because device-key admission (SR-14) is still open.

### 2. What R2 can and cannot enforce (K1, K2, K3, K9, K11, K12)

- **R2 can enforce:** create-only single PUTs (If-None-Match), if the header can be bound into a presigned URL (unproven); create-only CopyObject through `cf-copy-destination-if-none-match` (S3); per-object, per-action temporary credentials (K9, local signing only); prefix bucket locks (K11).
- **R2 cannot be relied on for:**
  - binding uploaded bytes to the authorisation (the documented example signs only `host` with `UNSIGNED-PAYLOAD`, S1);
  - create-only multipart completion (K3; the Workers binding's `complete()` has no conditionals either, S9);
  - a size cap on presigned PUTs (S27, secondary);
  - anything against the account holder: locks can be removed (K11), and whoever holds the parent secret can mint any credential (K1, K9).
- **Consequence:** R2 controls limit a device or a leaked URL. They do nothing against AP2. Integrity therefore comes from homelab verification plus receipts. R2 controls only cut cost and nuisance (SR-07, SR-08).
- **Timers from R2 that A3 must respect:** incomplete multipart uploads are auto-aborted after 7 days (S9), and presigned URLs last at most 7 days (S1). Lease TTL and URL lifetimes must sit inside these, and BUD-REVOKE wants outstanding URLs gone within 15 minutes. That conflict with long mobile background queues stays open (C1-S1, D3-S5, B2/B4).

### 3. D1-S1 (malicious cloud): outcome

**Pass.** The spike classified 32 values. Synthesis added V-33 (first installer and trust bundle by download link) and V-34 (rejection and re-upload request), for 34. All 34 are classified (register §5): 13 E2E, 15 made harmless by a required change, 1 integrity-only (updates have no freshness yet), 3 necessary disclosures, 1 cloud-local, and 1 open with a recorded required change (V-33 → SR-27).

All five changes PLAN expected are confirmed, with one re-framing:

- homelab-signed receipts (demos A4a–f; model);
- a pinned homelab key (demo A2b; `V1-no-pinned_trust` fails S1 against the cloud);
- device-signed records (demo A1);
- the dedup secret delivered sealed or locally (demos A3a–c);
- per-upload staging keys: kept, but the model shows they are not load-bearing for integrity.

The tabletop added device admission independent of the Worker (SR-14), a signed restore manifest (SR-16), a signed heartbeat (SR-18), and SR-27 to SR-31.

### 4. D1-S2 (poisoning, squatting): outcome, with the charitable baseline

**Pass for the proposal. A protocol change is required, but only because of AP2.**

- **V0 (ADR-0001 §4 read literally, gaps filled with "off")** fails even with no attacker, because the device counts a file done after "pending" or after its own PUT. The skeptics rightly called this partly a strawman.
- **V0c (charitable; added in synthesis).** The device is green only on a Worker-reported "committed" and re-asks otherwise. Reset-on-reject and reconcile-by-listing are on; per-upload keys are off. Results:
  - one holder, budgets 1–3: passes against none and fault; fails **S3** (false blame) against device (budgets 2 and 3) and leak; fails **S1, SL and S3** against the malicious cloud;
  - two holders, budget 1: the same pattern (S3 against leak; S1, SL, S3 against the cloud).
  - Adding per-upload keys removes false blame against a misbehaving device but not against a leaked URL or the cloud.
  - Shortest silent-loss trace: `H1:query → present (cloud lie) ⇒ H1 green, store lacks F, unrecoverable`.

  Evidence: `spikes/D1-S2/evidence/v0-charitable/results.md` and `model_v0c.patch`. This is a local model, not real R2.
- **V1 (proposal)** passes S1, SL, S2, S3 and L1 against every attacker within the bounds. With one holder that is budgets 1–3, up to 15,828 states. With two holders it is budget 1 for all attackers and budget 2 against device, fault and cloud, up to 971,688 states.
- **Load-bearing in V1 (ablations):**
  - SR-04 homelab re-verification (S2);
  - SR-05 receipts (S1, SL);
  - SR-02 pinned receipt key (S1 against the cloud);
  - SR-06 re-ask, needed even with no attacker when two devices hold a file;
  - SR-10(a) lease TTL (L1 against squatting);
  - SR-10(b) re-claimable when the staged object vanishes (L1 against fault);
  - SR-11(c) attribution (S3 against leak and cloud).
- **Not load-bearing:** per-upload keys (SR-07), create-only PUT (SR-08), and the no-timer staged state. The last is kept only to avoid duplicate uploads during homelab outages.
- **What this means for OD-04:** the honest-cloud failures in the original D1-S2 write-up ("squatting alone gives silent loss", the fault and leak cases) came from V0's gap-filling defaults. They do not support amending ADR-0001. The amendment rests on AP2 (silent loss) and on false blame (S3), which ADR-0001 is silent about.
- **Limits:**
  - small bounds (1 file, 2 honest devices, budget ≤ 3);
  - L1 is "can still recover", not "will recover under fair scheduling";
  - age is abstract and multipart is not modelled;
  - SR-11(d) and the A3 safety valve are not modelled;
  - costs and BUD-TTS impact are not measured;
  - the `V1-no-pinned_trust` two-holder run against the cloud was stopped at 6.3 GB.

### 5. The device-keeps-the-file precondition (T-22, SR-28, AR-09)

The no-silent-loss result assumes the honest device can re-upload after a rejection or a cloud loss. Under poisoning with the homelab offline, or a cloud that delays receipts, that window is attacker-extendable. Camera-roll deletion and OS "free up space" features are not gated by the app. SR-28 asks the client to keep either the source reference or the encrypted object until the receipt arrives, within BUD-TMP, and to show loudly when neither remains. The residual (AR-09) is visible, not silent, loss. This ties to OD-18 ("safe to delete") and E3.

### 6. Enrollment paths and the dedup secret (SR-14, SR-15, SR-27)

The earlier interim rule ("the dedup secret travels only in the physical kit") is **withdrawn**. It would have blocked phones and second computers, which ADR-0002 §3 enrolls without a kit and without the admin. It would also have turned a one-use, expiring printed card into a permanent secret.

Requirements per path (D3 designs the mechanism):

| Path (ADR-0002) | Pin of the trust bundle | Dedup secret | Device-key admission (SR-14) candidates |
|---|---|---|---|
| Kit-enrolled desktop | On the USB stick and card (a digest, not a secret) | On the USB stick only, never on the card; or sealed after admission | USB return trip with a device-signed manifest; PAKE keyed by the invite code |
| Phone via the wizard QR | From the enrolled device's QR scanned **in the app** (ADR-0002 already allows "scans the same QR on first launch") | Same local scan, or sealed after admission. **Never** through the Play Install Referrer (it passes through Google) | Co-signature by the enrolled device over the local QR (Tailnet Lock pattern) |
| Second computer, USB copy | Written to the stick by the enrolled device | Same, or sealed | Co-signature via the stick |
| Second computer, download + typed pairing code | Cannot come from the download (SR-27); needs a PAKE-authenticated channel to the enrolled device | Sealed after admission only | PAKE (CPace, SPAKE2) keyed by the pairing code over the Worker relay: a malicious relay gets one online guess per run |

If the Play Install Referrer route is used on its own, the phone has no authentic pin. That may need an extra in-app scan, which touches ADR-0002 §3 wording, so it is a decision request (OD-05 input). No relative is onboarded before Gate C, so no interim rule that overrides ADR-0002 is needed: until then only the admin places a production secret on a device. For restores, which the admin performs in v1, the interim is an out-of-band key-fingerprint check. It is **not** proposed as an admission mechanism.

### 7. The presence oracle (T-11, SR-21, AR-06)

The attack class is primary-sourced (Tahoe, S19) and was executed in D1-S1: with the secret and the ID index, one CPython core recovered a 6-digit field of a 1,001-byte templated document after 482,914 HMACs in 2.83 s. The claim that keeping the secret is "the only structural defence" is withdrawn (K8 contested). Cross-user dedup of *storage* happens at the homelab, and the cloud's presence answer is only a bandwidth optimisation. F3-S2 (emulated) found:

- per-device rate limits sized for a first seed fail (probes finish within hours);
- a flat 333/day cap takes 172 days for a 57,399-file phone's first pass;
- per-person scope gives no information on other people's files below T_x.

SR-21 is rewritten to follow F3's DR-F3-2: scope, record-first, and exact accounting of queried IDs. AR-06 is narrowed to the remaining same-person and above-T_x oracle plus leaked-secret history. Homelab-only dedup (devices always upload unless they hold their own receipt) would remove the cloud oracle entirely without conflicting with CLAUDE.md. Its bandwidth cost is unmeasured (C4, E1).

Two further options the skeptics raised are left to F3, which already evaluates them: a randomised upload threshold (Harnik, Pinkas and Shulman-Peleg 2010; F3 has a secondary listing only) and server-aided dedup keys (DupLESS-style). F3 finds that a key server inside Cloudflare would be worse than today, and that a homelab-held asynchronous OPRF would change the settled "HMAC(family secret, content)" construction (F3 claim C17, secondary-only; the DupLESS paper is blocked). D1 recommends neither in Wave 1; both stay open under DR-F3-2 and A1.

### 8. Revocation (K10 contested, SR-09, SR-17)

What is documented: R2 key permission changes "may take up to a minute" (S7), and revoking a parent token stops derived temporary credentials "immediately" (S4). These describe different operations rather than a conflict. Not documented: whether rolling or revoking the token that signed presigned URLs invalidates them. If it does, per-epoch or per-device signing tokens are the BUD-REVOKE kill switch. C1-S1 must test it.

SR-17 now lets the admin revoke at the Worker directly, which works while the homelab is down. The homelab list stays authoritative for accepting records.

### Alternatives compared

| Option | Fit with settled requirements | Pros | Cons | Evidence |
|---|---|---|---|---|
| Status via Worker "committed" (ADR-0001 §4, charitable) | Violates SR-01 | Simple | Silent loss under AP2; false blame | K5; V0c runs |
| **Per-file homelab-signed receipts + signed heartbeat** | Fits | Device-verifiable; prototyped in CE; model passes | Needs a pinned key; receipt storage on devices | K4; S30; S32 |
| Merkle log with signed checkpoints and device witnesses (C2SP tlog-checkpoint) | Fits | Anti-rewrite, anti-split-view audit trail | Complexity; not needed for v0 | S14 |
| Staging key = dedup ID | Fits only with receipts | Idempotent keys | Part mixing on multipart; false blame; griefing cost | K2; V0c |
| **Per-upload staging keys** (hygiene) | Fits | Attribution against a misbehaving device, no part mixing, clean resume | More objects; duplicate uploads cost operations | K2; S21 (Ente) |
| Create-only via presigned If-None-Match / CopyObject `cf-copy-destination-if-none-match` / Worker-proxied `put(onlyIf, sha256)` | Fits | Cuts overwrite nuisance; CopyObject route is documented | None helps against AP2; proxy puts bytes through the Worker (limits not checked) | K3; S3; S9 |
| Exclusive claims | Fits on paper | Saves duplicate bandwidth | Squatting blocks others | D1-S2 |
| **Advisory leases (claimed: TTL; staged: no timer, re-claimable on vanish/reject)** | Fits | No stuck claims; no duplicate uploads during outages | Occasional duplicate uploads | D1-S2 ablations |
| Staging bucket lock (short Age, hours) | Fits | Stops deletion or overwrite by leaked non-admin tokens | Storage-days cost; removable by AP2; not integrity | K11 |
| Device keys trusted via the Worker | Violates SR-01 | Zero effort | Restore redirection; junk in store | K7; demos A5a |
| Device keys via PAKE / co-signing / USB return trip / key transparency | Constrained by ADR-0002 §3 (OD-05) | Removes T-02 | Effort; D3 must weigh | K7; S20 |
| Global presence answer + rate limits | Fits | Fastest seeding | Oracle not bounded (F3-S2) | S33 |
| **Scoped presence (DR-F3-2)** or homelab-only dedup | Fits (storage dedup unchanged) | Removes the cross-person oracle | Duplicate uploads (cost unmeasured) | S33; F3 note |
| Randomised upload threshold (Harnik et al. 2010) | Fits (storage dedup unchanged) | Blurs the presence signal | Bandwidth; weaker than scoping; source secondary | F3 note (B24) |
| Server-aided dedup keys: DupLESS-style server in Cloudflare, or a homelab-held asynchronous OPRF | Cloudflare server: violates SR-01. Homelab OPRF: **changes settled text** (HMAC construction) | Takes the offline-usable secret off devices | Latency against an outbound-only homelab; new primitive; USB IDs harder | F3 note (C17, secondary-only) |
| Register tooling: Markdown + Mermaid vs pytm vs Threagile | — | Markdown fits repo review | pytm/Threagile add toolchains; Threagile last release 2024-07-30 | S29 |

### Similar work and lessons

| Project or paper | What they do | Borrow or avoid | Source |
|---|---|---|---|
| restic / rest-server | Server refuses overwrite; checks SHA-256 = ID (unless `--no-verify-upload`); explicit threat model incl. `forget` gaming | Borrow the explicit threat-model style. Our cloud cannot check the ID (K13) | S15, S16 |
| Borg append-only | Append-only that later compaction can make moot | Avoid switch-off-able append-only; borrow verify-before-destroy (SR-20) | S17 |
| Kopia server | Server derives IDs; client trusts "exists" above 50,000 bytes and checks the returned ID | Avoid trusting "exists" (SR-06) | S18 |
| Tahoe-LAFS | Convergence secret; confirmation and learn-remaining attacks; storage may only deny service | Borrow SR-01 and honest disclosure of the oracle (AR-06) | S19 |
| Tailscale Tailnet Lock | Node keys need a signature the coordination server cannot make | Candidate for SR-14 co-signing | S20 |
| Ente | Server-generated per-upload keys; key-ownership check at commit; Verification ID for relayed keys | Borrow SR-07 binding; fingerprint check only as the restore interim | S21 |
| magic-wormhole / CPace / SPAKE2 | PAKE over an untrusted relay | Candidate for SR-14 on the pairing-code path | skeptic review (no source fetched; D3 to cite) |
| Hofmann–Truong 2024; MEGA; Nextcloud | Malicious-server attacks on E2EE storage | Precedent only (K14 contested) | S22, S24 |

### Tools and libraries

| Name | Purpose | Licence | Maturity | Source |
|---|---|---|---|---|
| Markdown register + Mermaid DFD | v0 register | — | — | Chosen for v0 (`docs/security/threat-model.md`) |
| OWASP pytm | Threat model as code | MIT (scout) | 1.4.0, 2026-07-06 | S29 |
| Threagile | YAML model + risk rules | not checked | v0.9.1, 2024-07-30 | S29 |
| LINDDUN GO, Threat Dragon, Deciduous | Privacy cards; DFD editor; attack trees | not checked | — | Wave 2 |
| Python explicit-state model (`spikes/D1-S2/model.py`) | Executable tabletop | repo | throwaway | S32; A3-S1 owns the real model |

## Spikes

| Spike | Hypothesis | Pass → / fail → (decision) | Exec tag | Budget IDs | Data class | Status | Result |
|---|---|---|---|---|---|---|---|
| D1-S1 Malicious-cloud tabletop | Every value that crosses Cloudflare is verified with a key the cloud lacks, or recorded as a required change | Pass → OD-04 option B with the RC list; fail → a value that can be neither | CT | BUD-REVOKE (context only) | `SYN → results` | **Pass** | 32 values classified (34 with V-33, V-34). 19 required changes RC-1..RC-19 (mapped to SRs in register §8.2). 15 of 15 executable checks matched expectations with real age 1.1.1, Ed25519 and HMAC (`spikes/D1-S1/README.md`, `evidence/`). Hash-rate floor: 1,024,717 SHA-256/s on one CPython core (2^50 ≈ 35 core-years; GPU not measured). **Local model and demos, not real R2/Cloudflare.** |
| D1-S2 Dedup poisoning and claim squatting | Poisoning and squatting end in detection and automatic re-upload with no silent loss; otherwise a protocol change | Pass → V1 rules into A3/C1; fail → protocol change (OD-04) | CT | none (qualitative) | `SYN → results` | **Pass** (V1); ADR-0001 §4 fails against AP2 | V1 passes all properties against all attackers within bounds (up to 971,688 states). V0 (literal) fails broadly; V0c (charitable, added 2026-10-06) fails only S3 against device and leak, and S1/SL/S3 against the cloud (`spikes/D1-S2/README.md`, `evidence/v0-charitable/`). **Local model, not real R2/Cloudflare.** |
| D1-S3 Red team against the full register | Every attack maps to a mitigation or an accepted risk | — | CT | — | `SYN → results` | Deferred to Wave 2 | Inputs ready: the value inventory, the RC/SR list, and the D1-S2 attacker set (extend with ingest-VM compromise and a colluding device plus cloud). |

No kits are needed in Wave 1 (both spikes are CT). Real R2 behaviour (If-None-Match on presigned PUT, multipart completion, token-roll revocation, size caps) is left to C1-S1 [SB].

## Skeptic issues and how they were handled

| Issue (severity, skeptic) | Handling |
|---|---|
| Two inconsistent inventories (22 vs 32 values; SR vs RC) (major, sources + logic) | **Fixed.** One inventory, V-01..V-34, in the register; RC→SR crosswalk (§8.2); retired V1..V22 crosswalk (§11); each "property holds" lists its SRs (register §6). |
| V0 baseline partly a strawman (major, sources + adversary) | **Fixed.** Ran V0c (charitable) and two neighbours. OD-04 now rests on AP2 and false blame only; the literal-V0 honest-cloud failures are labelled "ADR silent; defaults assumed". |
| Interim "dedup secret only in the kit" conflicts with ADR-0002 (major, all three) | **Fixed.** Withdrawn; per-path requirements (Finding 6, SR-15); remaining gap raised as a decision request. |
| First-install download path missing (major, sources) | **Fixed.** V-33, T-21, SR-27; routed to D3, D5, B7. |
| SR set behind the pass incomplete; SR-10 contradicts spike rule 4 (major, logic + adversary) | **Fixed.** SR-10 split into (a) claimed lease with TTL and (b) staged, no timer, re-claimable on vanish or reject. SR-02 and SR-11(c) named in the pass set. A0 minimum set updated (register §8.1). SR-11(d) marked not modelled. |
| Note not reconciled with the spikes (major, logic; minor, adversary) | **Fixed.** Spikes section filled; counts and budget IDs corrected (D1-S1 cites BUD-REVOKE only; D1-S2 none). |
| "Device keeps the file" not enforceable (major, logic) | **Fixed.** SR-28, T-22, AR-09; linked to OD-18 and E3. |
| AR-06 / OD-17 option 3 false dichotomy (major, logic + adversary) | **Fixed.** K8 not used as support; SR-21 rewritten per DR-F3-2; AR-06 narrowed; homelab-only dedup offered as an option that does not conflict with CLAUDE.md. |
| Per-upload keys argued as integrity (major, adversary; minor, sources) | **Fixed.** SR-07 re-framed as attribution, part mixing, resume and cost. The "contradicts devices can only append" conflict is withdrawn: staged ciphertext is not backup history. |
| K6, K10 cite unsupporting sources (minor) | **Fixed.** K6 now cites S32; K10 narrowed (corrected statement). |
| SR-21 batch clause bounds nothing; count IDs, not requests (minor, sources + adversary) | **Fixed** in SR-21. |
| 7-day multipart auto-abort and 7-day URL maximum (minor, sources) | **Fixed.** Added to SR-10(a) and Finding 2 as A3 timer inputs. |
| Time-sensitive facts need re-verify dates (minor, sources) | **Fixed.** K9 and S26 tagged "re-verify by Gate B" (register §10). |
| SR-14 misses PAKE and the USB return trip; invite MAC offline-attackable (minor, logic) | **Fixed** in SR-14. |
| K10 framing; missed token-roll kill switch (minor, logic) | **Fixed** in SR-09 and Finding 8. |
| SR-17 depends on the homelab being up (minor, logic) | **Fixed.** Worker fast path plus homelab-authoritative list. |
| Unbounded re-ask conflicts with low resource impact (minor, logic) | **Fixed.** SR-06 adds backoff, a retry budget tied to BUD-BAT-D and BUD-TTS, then a visible nudge. |
| "Supersede §4" overstates; draft ownership unclear (minor, logic) | **Fixed.** OD-04 now reads "amend steps 1, 2 and 4 and fill gaps". Draft text is in register Appendix A; H1 decides whether ADR-0009 carries it or a 0041+ number is assigned. |
| RC-18/RC-19 not lifted to SRs (minor, adversary) | **Fixed.** SR-29, SR-30 (and RC-17 → SR-31). |
| Receipt key on the ingest VM (minor, adversary) | **Recorded.** A separate receipt signer is listed as a Wave 2 alternative under AR-08 (register §6c, T-26). |
| Ransomware false green (minor, adversary) | **Recorded.** T-23, deferred to Wave 2 (E3, A3, D4-S3). |
| K14 precedent unread (minor, all) | **Kept** as contested precedent; not cited as support. Access escalated to H1. |
| Missed alternatives (all three skeptics) | **Recorded.** Homelab-only dedup, scoped presence, short Age bucket lock, token-roll kill switch, per-device signing tokens, PAKE, USB return trip, local QR hand-over, keep-encrypted-until-receipt, cloud-side ciphertext-hash binding and CopyObject create-only are now in Findings 2, 6–8, SR-09, SR-14, SR-15, SR-28 or the alternatives table. Randomised thresholds and DupLESS/OPRF are listed and left to F3 (Finding 7). |

## Conflicts with settled text

These are never resolved here. Each goes to the owner.

1. **ADR-0001 §4 step 4:** the homelab "marks it committed", and that is the only status signal devices get. It is unauthenticated, so a malicious cloud causes silent loss (K5; V0c). → OD-04: receipts as the only "safe".
2. **ADR-0001 §4 step 2:** "objects are keyed by dedup ID", and the claim is exclusive. Not an integrity conflict once receipts exist. Per-upload keys and advisory leases are hygiene and liveness changes. → OD-04. (The earlier claim that this contradicts "devices can only append" is withdrawn.)
3. **ADR-0001 §4 step 1:** "returns the missing ones". Scoped presence (DR-F3-2) or homelab-only dedup would change the skip semantics. → OD-04 together with F3's DR-F3-2.
4. **ADR-0001 §2:** "the cloud cannot test for known files". This holds only while no device's secret has leaked. → OD-04 rewording (register Appendix A); AR-06 → OD-17.
5. **ADR-0001 §6** restores to "the requesting device's own public key". Safe only with SR-14 and SR-16. The admission mechanism touches **ADR-0002 §3** "adding devices never requires the admin" → OD-05 (Wave 2). The interim fingerprint check applies to admin restores only.
6. **ADR-0002 §3:** the Play Install Referrer path. If it carries the enrollment token alone, the phone has no authentic trust-bundle pin. An in-app scan of the enrolled device's QR may become mandatory. → decision request (input to OD-05; D3 and B3).
7. **ADR-0002 §3:** the download-link route for a second computer. With no OS signing, first install is trust on first use if served from Cloudflare (SR-27). → D3, D5, B7; raise to the owner only if the chosen fix changes the wizard.
8. **ADR-0002 §2:** the Worker checks the invite code at redemption. If the code also authenticates device keys, a malicious Worker must see only a PAKE transcript or derived verifier, not the code (SR-14; D3-S2).

## Open questions

1. Does R2 enforce a signed `If-None-Match: *` on presigned PUT? Is there any create-only rule for CompleteMultipartUpload? Can Content-MD5 or length be signed? Does rolling the signing token invalidate outstanding URLs? **C1-S1 [SB].**
2. How do BUD-REVOKE (15 min outstanding) and long mobile background queues fit together? **C1-S1, D3-S5, B2, B4.**
3. Which SR-14 mechanism, per enrollment path, fits "near-zero enrollment" and "adding devices never requires the admin"? **D3, OD-05 (Wave 2).**
4. Does the Play Install Referrer path need an extra in-app scan to carry the pin? **D3 with B3; ADR-0002 §3 open question on the referrer.**
5. Values for the lease TTL, T_receipt or safety valve, T_fresh and the retry budget, within BUD-TTS, BUD-BAT-D and the 7-day auto-abort. **A3.**
6. SR-13: per-record sequence or signed scan checkpoints? **A3 with H4.**
7. Bandwidth cost of homelab-only dedup or per-person scope (cross-person duplicate bytes). **C4, E1.**
8. Worker request-size and CPU limits for a Worker-proxied upload. **C1** (not checked).
9. Ingest-VM compromise: store immutability, online-key custody, separate receipt signer. **Wave 2: A6, D2, D4-S4.**
10. Primary papers S22–S24 remain unread (blocked). **H1** (source access).

## Recommendation

1. **Decide OD-04 = B: amend ADR-0001 §4 steps 1, 2 and 4, fill its gaps, and reword one §2 sentence** (draft text: register Appendix A):
   - receipts verified under a pinned key as the only "safe";
   - device-signed records and verify-before-commit;
   - re-ask with backoff;
   - advisory leases that cannot get stuck;
   - signed rejection handling with correct attribution;
   - a signed heartbeat;
   - per-upload keys as hygiene.

   This is the only option where a compromised Cloudflare costs availability rather than data (K5, V0c), and its core is already prototyped in the CE spike (161/161 checks). Take DR-F3-2 (presence scope) in the same decision.
2. **A3 and C1 build to SR-01..SR-13, SR-20..SR-24, SR-30 and SR-31.** The A0 skeleton models at least the register §8.1 minimum set, so Gate B measures the real protocol shape.
3. **D3 treats SR-14, SR-15 and SR-27 as one per-path design**, guided by Finding 6, before Gate C. Until then, only the admin places production secrets on devices, and admin restores require an out-of-band key-fingerprint check.
4. **Do not rely on R2 bucket locks, create-only writes or Worker-proxied uploads for integrity.** Use them only to cut cost and nuisance, once C1-S1 confirms what R2 enforces.
5. **Put AR-04, the narrowed AR-06, AR-05 (with DR-F3-1 and OD-03), AR-08 (at Gate A) and AR-09 (at Gate C, with OD-18) on OD-17.**

**What would change this:**

- If C1-S1 shows R2 enforces create-only multipart completion, SR-08 gets stronger, but receipts are still needed because AP2 is unaffected.
- If D3 finds no SR-14 mechanism compatible with ADR-0002 §3, the owner chooses between admin-confirmed devices (OD-05) and accepting restore-redirection risk.
- If D4-S1 or A3-S1 finds a recovery path that exceeds BUD-TTS, A3 tightens timers or adds homelab push.
- If C4 or E1 shows cross-person duplicates are rare, homelab-only dedup becomes the cheaper way to remove AR-06.

## Decision requests

### OD-04: Amend ADR-0001 §4 (steps 1, 2, 4) and one §2 sentence for a malicious-cloud-safe ingest protocol
- **Needed by:** Wave 1 exit.
- **Evidence:** this note (Findings 2–4, 7); `docs/security/threat-model.md` §5–§8 and Appendix A; `spikes/D1-S1/`, `spikes/D1-S2/` (incl. `evidence/v0-charitable/`); `content-encryption-format.md`; C1-S1 (pending).
- **Options:**

  | Option | What it means for the family | Cost (money and owner time) | Reversibility | Risks |
  |---|---|---|---|---|
  | A. Keep §4 as written (Worker-reported "committed", dedup-ID keys, exclusive claims) | Phones may show "backed up" on the cloud's word | None now | Costly later: receipt format and key layout are one-way doors (#5, #7) | Silent loss under a malicious or compromised Cloudflare; honest devices blamed for others' overwrites |
  | **B. Amend §4 per register Appendix A** (receipts under a pinned key, signed records, verify-before-commit, re-ask with backoff, advisory leases, attribution, heartbeat; per-upload keys as hygiene) | "Safe" always means verified at home; occasional re-uploads | Build effort in A3, C1 and clients; small extra R2 operations | Formats become one-way doors at Gate A | Device-key admission still depends on D3 (SR-14) |
  | C. B plus a Merkle transparency log with device witnesses | As B, plus a cloud-proof audit trail | More build effort | Can be layered on B later | Complexity before the skeleton |

- **Recommendation:** B now, revisit C in Wave 2.
- **Touches settled text:** ADR-0001 §4 steps 1, 2, 4 and §2. H1 decides whether ADR-0009 carries "Amends: ADR-0001 §2, §4" or a 0041+ number is assigned.
- **If no decision by the deadline:** the A0 skeleton assumes B with throwaway v0 keys and no family data. Gate A cannot pass without a decision.

### OD-17 (additions): accepted risks AR-04, AR-05, AR-06 (narrowed), AR-08, AR-09
- **Needed by:** Gate A (AR-04, AR-05, AR-06, AR-08); Gate C (AR-09).
- **Evidence:** register §6 and §9; F3-S2.
- **Options:** (1) accept all as written; (2) accept AR-04 now, accept AR-06 in its narrowed form together with DR-F3-2, decide AR-05 with DR-F3-1 (padding) and OD-03, revisit AR-08 at Gate A with D2/A6/D4, decide AR-09 at Gate C with OD-18; (3) as (2), but remove AR-06 by choosing homelab-only dedup (devices always upload unless they hold their own receipt). This keeps cross-user storage dedup and so does **not** conflict with CLAUDE.md; its bandwidth cost is unmeasured (C4, E1).
- **Recommendation:** option 2.
- **Touches settled text:** AR-06 rewords ADR-0001 §2 (covered by OD-04).
- **If no decision by the deadline:** Gate A is blocked (PLAN §4.2).

### New (input to OD-05; H1 to number): trust anchors on the phone and download enrollment paths
- **Question:** may the ADR-0002 §3 wizard require that phones get the trust-bundle pin (and any admission secret) from an in-app scan of the enrolled device's QR, never from the Play Install Referrer alone? And may the download-link route for a second computer require a PAKE-authenticated pairing step and an installer-digest comparison?
- **Options:** (a) yes, an in-app scan is always required on phones, plus PAKE on the pairing code; (b) referrer-only phones carry no production secret until homelab admission seals it, accepting a weaker pin; (c) drop the download route and keep USB copy only.
- **Recommendation:** (a). ADR-0002 already allows "scans the same QR on first launch", so this may be a clarification rather than a change. D3 confirms in Wave 2.
- **Needed by:** Gate C.

## Hand-offs

| To | What | Why |
|---|---|---|
| A3 | SR-02..SR-06, SR-10 (a, b), SR-11 (a–d), SR-12, SR-13, SR-18, SR-19, SR-30; timer inputs (7-day auto-abort, BUD-TTS, BUD-BAT-D); register Appendix A as the amendment text; V0c and V1 model results for A3-S1 | ADR-0009 owns the protocol |
| C1 | SR-07, SR-08, SR-09 (incl. the token-roll test), SR-12, SR-17, SR-21, SR-23, SR-24, SR-26, SR-31; C1-S1 checks for K3 and K10; re-verify K9 and S26 by Gate B | ADR-0010 and the R2 key layout (#7) |
| D3 | SR-02, SR-14 (candidates incl. PAKE and USB return trip), SR-15 per-path table (Finding 6), SR-17, SR-27; the referrer decision request | ADR-0014; OD-05 |
| D2 | SR-15, SR-23; AR-08 and the separate-receipt-signer alternative | ADR-0008 |
| D5, B7 | SR-27 (first install), SR-29 (anti-rollback) | ADR-0015, ADR-0022 |
| B6, E3 | SR-06 (backoff, retry budget, nudge), SR-28 (keep until receipt), SR-05, SR-18; AR-09 with OD-18; T-23 ransomware false green | ADR-0021, ADR-0024 |
| F3 | SR-21 now defers to DR-F3-2; AR-06 narrowed accordingly | DR-F3-2 |
| A8 | SR-16 | ADR-0028 |
| D4 | P-scenarios and D1-S2 attackers as D4-S1/S2 cases; SR-11 recovery; SR-20 | Attack suite |
| D6 | AR-05, SR-25, SR-26; LINDDUN items; retired IDs V20/V21 → V-26/V-08 | ADR-0027 |
| H1 | Blocked sources (Method); AR-04..AR-09 for the OD-17 row; number for the new decision request; ADR number for the ADR-0001 amendment (or confirm ADR-0009 carries it); `docs/security/threat-model.md` now exists | Registries are H1's |
