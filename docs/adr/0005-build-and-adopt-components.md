# ADR-0005: Build the Reliquary-specific system and adopt proven components; do not fork existing products

- **Status:** Proposed
- **Date:** 2026-10-06
- **Owner workstream:** F1
- **Decider:** the owner
- **Gate:** A
- **Supersedes / Amends:** None
- **Evidence:** `docs/research/f1-build-adopt-fork-compose.md` (Final, Wave 1); `spikes/F1-S1/`; kit `docs/research/kits/F1-S2/` (not run)
- **Traceability:** input to R-02, R-04, R-10–R-12, R-14, R-18–R-23, R-26–R-31, R-35, R-37, R-42, R-44–R-46 (see `docs/research/traceability.md`). Closes none of them.
- **Owner decisions:** OD-02 (this decision and the weights); related DR-F1-1 (development-upkeep budget), DR-F1-2 / OD-17 (vendor-readable stopgaps), Q-B9 (hours)
- **One-way door:** No

## Context and problem statement

Reliquary's settled requirements (CLAUDE.md, ADR-0001, ADR-0002) set a specific trust model:
- Devices encrypt content and metadata to the homelab public key and cannot read any backup (R-19, R-20, R-22).
- The cloud sees only opaque cross-user dedup IDs (R-21).
- Devices can only append (R-18).
- The homelab is never exposed and only makes outbound connections (R-12).
- Phones are first-class (R-02, R-04).
- The client is an *assistant*: it discovers keepsakes, reports health in plain language, and nudges (R-29–R-31).

Before committing one maintainer to a large custom build, PLAN F1 asks whether an existing system can be adopted, forked or composed instead. It also asks for decision weights for later choices. PLAN's rule is: adopt or fork if a candidate meets all settled requirements after a patch of at most 30 % of the build estimate, under an acceptable licence. Otherwise build, adopting the listed components.

This must be settled at Gate A, because it decides whether tracks A and B write specs for Reliquary's own formats or adapt to someone else's.

## Decision drivers

- Settled trust model as pass/fail knockouts: R-12, R-18, R-19–R-22; plus R-02/R-04 (phones) and R-26 (keep forever).
- Data integrity over everything (R-39). Build's own crypto and state machine are unproven until A0, the D4 attack suite and an external review.
- One maintainer at a provisional 8 h/week (Q-B9 unanswered): effort and yearly upkeep.
- **BUD-SUPPORT** (owner time ≤ 2 h/month at steady state). Every option that runs self-built or forked software breaches it as written (DR-F1-1).
- Licence freedom for OD-15 (G3).
- Owner weights (OD-02, proposed): integrity 35 %, maintenance 20 %, effort 20 %, family UX 15 %, cost 10 %. They apply only after the knockouts.

## Considered options

1. **Build** the Reliquary-specific system and adopt proven components.
2. **Fork Ente** (mobile app, with or without the museum server).
3. **Adopt Immich** (plus a homelab copy).
4. **Compose existing tools.** Either restic or Kopia on desktops plus PhotoSync on phones, or a hybrid of Duplicacy (RSA) on desktops plus Reliquary's own phone app and Worker.
5. **Do nothing** (Backblaze Personal plus phone-vendor clouds). This is a baseline and stopgap, not an end state.

## Decision

**Option 1.** Build the parts that make Reliquary what it is:
- the shared client core;
- the Worker/D1 control plane;
- homelab pull-ingest;
- the admin CLI;
- the restore pipeline;
- desktop and Android clients.

**Adopt** proven components around them. **Do not fork** any existing product. The reason: no researched system meets the settled trust model as shipped, and none that comes close has a phone client. For the top two alternatives, the patch would replace the very part that makes the candidate useful.

Specifics:

| Item | Decision |
|---|---|
| Client UI stack | **Per ADR-0003** (T1; pending). This ADR does not choose it. T1's working assumption is option C. |
| Envelope | Adopt the age v1 format. Go and Rust age serve as independent decryptors. A2/ADR-0007 owns the details. |
| Core bindings | Adopt UniFFI if ADR-0003 keeps a shared Rust core. |
| Local state | Adopt SQLite. |
| Self-update | Adopt an existing signed updater (B7/ADR-0022, D5/ADR-0015), verified against the project's offline key (settled). |
| Homelab storage | Adopt an existing engine chosen by A6/ADR-0012. rustic_core, restic, Kopia, Plakar, Borg and PBS are candidates **at the homelab only**. Their symmetric keys are acceptable there and not on devices. |
| Device uploads | No S3 SDK on devices. Devices use Worker-issued presigned URLs (ADR-0001 §4). |
| AGPL code (Ente, Immich, Nextcloud, UrBackup) | **Not copied or forked.** Read for patterns only. |
| Duplicacy, bupstash | Prior art for keyed chunk IDs, public-key content keys and put-only access. Not dependencies. |
| Evaluation method for later choices | Two stages. The settled requirements are pass/fail knockouts. The OD-02 weights then order choices **inside** the build: components, phasing, platform order. The weights never reopen settled requirements. |
| Phasing | **To be decided in ADR-0004 (E2), Wave 2**, after Q-B9 and A0 calibration. F1's milestone ranges (M1 skeleton, M2 concierge USB/CLI seeding, M3 desktop + minimal Android) are estimates and are contested. They are inputs, not part of this decision. |

### Consequences

- **Good:**
  - The settled trust model is met by design, with no AGPL obligations.
  - Formats stay under Reliquary's control, so they can be frozen at Gate A.
  - There is no upstream to rebase on. Upstreams like Immich and Ente ship 33–38 stable releases a year (F1-S1).
- **Bad / accepted trade-offs:**
  - A long build. F1 estimates 1,260–2,520 focused hours before contingency, or 3.0–6.1 years at 8 h/week. This is an estimate and is contested.
  - A one-person bus factor.
  - New crypto and state-machine code is unproven until A0, D4, G2 vectors and an external review pass.
  - Yearly upkeep (estimated 60–120 h/year, contested) breaches BUD-SUPPORT as written (DR-F1-1).
  - The family relies on vendor-readable stopgaps for years (DR-F1-2 / OD-17).
- **Follow-up work:**
  - E2 re-derives ADR-0004 phasing from F1 §4 and considers a phone-earlier ordering.
  - C4 costs an external crypto review.
  - H1 resolves DR-F1-1.
  - A1, A2, A3, D2 and D4 take the prior-art hand-offs: Kopia's and Duplicacy's shared HMAC secrets, bupstash's put-only access, and restic's forged-timestamp issue.

### Confirmation

- **Gate B:** compare A0's actual hours with the F1 effort model. If M1 overruns its high estimate (520 h), revisit scope in ADR-0004.
- **Yearly, or when a candidate ships public-key write-only encryption covering metadata plus service-enforced append-only plus a phone client:** re-run the fit matrix. Watch Duplicacy, bupstash and restic #187.
- **If the owner runs F1-S2:** a server-side setting that blocks device deletes in Ente or Immich updates that cell. It does not by itself reopen this decision.
- **D4 attack suite (R-18):** must prove what this ADR assumes by design, that devices cannot delete or rewrite. It includes forged timestamps.

## Pros and cons of the options

### 1. Build + adopt components
- Good, because it is the only option that passes every knockout (by design; still to be proven by A0 and D4).
- Good, because it creates no AGPL obligations and no upstream to track (K14; F1-S1 churn).
- Bad, because of the effort and calendar time (K10, contested), and because its integrity is unproven until tested.

### 2. Fork Ente
- Good, because Ente is the closest audited E2EE analogue and has a mature phone app.
- Bad, because every signed-in device holds the user's wrapped masterKey, so devices can read (K2). That breaks R-20/R-22.
- Bad, because object keys are random `<userID>/<uuid>` with per-user dedup, user trash and delete routes exist, and museum plus Postgres must be reachable, or else hosted on a cloud VM outside ADR-0001's shape (K3).
- Bad, because the patch replaces the upload, sync and crypto slice (about 6.4k of about 283k mobile lines) and every feature that assumes the device decrypts. The saving is capped at the Android line. Net hours are unknown.
- Bad, because it is AGPL (K14), with an upstream shipping 33 stable releases a year (F1-S1).

### 3. Adopt Immich
- Good, because it is very active and has good phone clients.
- Bad, because it stores plaintext on the server, dedups per user by SHA-1, lets users delete, ships breaking majors (v2 2025-10, v3 2026-06), and its own README calls for a 3-2-1 backup (K9). It is not patchable without replacing its server model.

### 4. Compose
- restic or Kopia: every writer can obtain plaintext (K5). rest-server and the Kopia server listen inbound (K4, K7). R2 has no S3 Object Lock (K6). F1-S1 probes showed forged `--time` accepted by restic and cross-user reads by object ID in Kopia.
- Duplicacy (RSA) hybrid: content is wrapped to a public key and chunk IDs are keyed, which comes close. But metadata chunks are readable by every writer, and writers can prune (N1, not skeptic-reviewed). The core is needed for Android anyway, so the saving is small. It also adds a second format to verify forever.
- No phone client in any composition passes R-19/R-20.

### 5. Do nothing (baseline)
- Good, because it costs no build effort and is protection today.
- Bad, because the vendor can read the data, there is no homelab of record (R-45), the default retention is 30 days (snippet only), and vendors have exited before. Choosing it as an end state would require changing settled requirements.

## Evidence

Load-bearing claims, with verdicts copied from the research note's computed tally. Contested or secondary-only claims appear only beside verified ones.

| Claim | Source (primary) | Verdict |
|---|---|---|
| K2 Ente devices hold a wrapped per-user masterKey; operator cannot decrypt; no admin escrow | `ente-io/ente : architecture/README.md` | Verified |
| K3 Ente random per-user object keys; user trash/delete routes; museum + Postgres must be reachable or cloud-hosted outside ADR-0001's shape | `ente/ente @ 7a5993c : server/pkg/controller/file.go`, `server/cmd/museum/main.go`; object-storage doc | Verified |
| K4 Kopia server mode: server sees plaintext; default FULL on own snapshots | `kopia/kopia @ 87d15de : repository_server.proto`, `grpc_session.go`; Repository Server docs | Verified |
| K5 restic, Kopia, Plakar, Borg, Syncthing: every writer can obtain plaintext | restic `design.rst`; Kopia Encryption docs; Kloset `symmetric.go`; Syncthing `encryption.go` | Verified (Borg cell secondary) |
| K6 R2 S3 API has no Object Lock; bucket locks are admin-set by prefix | cloudflare-docs `r2/api/s3/api.mdx`, `r2/buckets/bucket-locks.mdx` | Verified |
| K7 rest-server listens; append-only retention issue | rest-server README; restic #22057 (user report) | Verified |
| K8 UrBackup server must accept inbound connections | `urbackup_backend : InternetClient.cpp`, `dllmain.cpp` | Verified |
| K9 Immich: plaintext, per-user SHA-1 dedup, user deletes, breaking majors | `immich-app/immich @ 6cd746a : asset.table.ts`; README; upgrading.md | Verified |
| K12 Play target API 36 from 31 Aug 2026 (yearly bump) | developer.android.com target-sdk page | Verified |
| K14 Forking AGPL code makes the component AGPL | Ente and Immich LICENSE | Verified |
| K16 rustic_core 0.x churn | crates.io API; GitHub metadata | Verified |
| K17 Syncthing Android discontinued (Play difficulty and no active maintenance) | syncthing-android README | Verified |
| N1 Duplicacy RSA: metadata not RSA-encrypted; prune without private key | `gilbertchen/duplicacy : duplicacy_chunk.go`, `duplicacy_config.go`; wiki "RSA encryption" | Primary, not skeptic-reviewed (beside K5) |
| N2 bupstash: ssh-served repository; put-only via `--allow-put` | `andrewchambers/bupstash : README.md`, `doc/man/bupstash-serve.1.md` | Primary, not skeptic-reviewed (beside K7/K8) |
| K1 No candidate meets all four knockouts (aggregate) | — | **Contested.** Superseded by the per-candidate rows above |
| K10 Effort 1,070–2,140 h; 24-month phasing | estimate | **Contested.** Revised in the note; phasing deferred to ADR-0004 |
| K11 Patch percentages | judgement | **Contested.** Withdrawn; replaced by the delta test |
| K13 Upkeep hours | estimate | **Contested.** Not sole support; measured churn used instead |
| K15 Weighted scores near-tied | illustrative | Secondary only. Supports only "weights do not decide" |

## Reversibility

Easy to reverse until Gate A. Nothing is built yet, and the decision mainly sets which specs tracks A and B write. After Gate A, the formats (ADR-0006, 0007, 0009, 0011) are the one-way doors, not this choice. Switching later to a different product would mean migrating data out of Reliquary's formats. Those formats are specified and have independent decryptors (age), so migration stays possible.

## Alternatives considered

- **Synology Photos:** not researched (gap). It needs DSM, which conflicts with R-10 on its face.
- **Nextcloud + Memories, PhotoSync, Syncthing untrusted devices, UrBackup internet mode, Duplicati, Plakar, Borg:** each fails at least one trust knockout clearly and has no phone client that passes (note §1).
- **Immich or Ente behind Cloudflare Tunnel or Workers VPC:** excluded by R-12 ("never exposed"). ADR-0010 records the rejection.
- **Immich or Ente app used unmodified against a Worker shim:** plaintext crosses TLS to the shim, which fails R-19.
- **Proxmox Backup Server, Tarsnap, Bareos/Bacula PKI, duplicity with GPG, Seafile, PhotoPrism, Arq:** not scored. PBS goes to A6's engine bake-off. Tarsnap is AWS-hosted, which fails "No AWS".

## Open questions

- Owner build hours (Q-B9): H2, by the Wave 1 exit.
- Phasing and ordering, including a phone-earlier minimal Android uploader: E2, ADR-0004, **to be decided in Wave 2**.
- Development-upkeep budget vs BUD-SUPPORT (DR-F1-1): H1 and the owner.
- Vendor-readable stopgaps as an accepted risk (DR-F1-2 / OD-17): the owner.
- Fee for an external crypto review: C4 and the owner, by Gate C.
- R2 token delete granularity and bucket locks against the staging lifecycle: C1 (C1-S1).
- AGPL §13 and App Store compatibility; licence policy (OD-15): G3.
- Skeptic review of the Duplicacy and bupstash rows: Wave 2.
