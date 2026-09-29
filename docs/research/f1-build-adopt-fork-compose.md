# F1. Build, adopt, fork or compose, and what one maintainer can sustain

- **Workstream:** F1 (see `docs/research/PLAN.md`, section "F1.")
- **Status:** Draft (analyst deep read; not yet through skeptic review)
- **Date:** 2026-09-29 (last updated 2026-09-29)
- **Feeds:** ADR-0005 (reserved in `docs/adr/README.md`), OD-02. No one-way door.
- **Depends on:** H2 (owner hours per week, Q-B9, still unanswered), T1 (`client-stack.md`, working assumption option C), `content-encryption-format.md` (T1 spike 2)
- **Traceability rows advanced:** input to every R-row that a candidate is scored against (R-02, R-04, R-10–R-12, R-14, R-18–R-23, R-26–R-31, R-35, R-37, R-42, R-46). F1 closes none of them itself.

## Summary

None of the thirteen existing systems examined meets Reliquary's settled trust model as shipped. Every one fails at least two of these four requirements:

- devices cannot read backup data, because content is encrypted to the homelab public key (R-19, R-20);
- opaque cross-user deduplication (R-21);
- append-only devices enforced by the service (R-18);
- a homelab that only makes outbound connections (R-12).

The closest analogue, Ente, fails three of the four by design. Ente devices hold a password-derived master key. The server issues random per-user object keys. Clients call the server directly and can trash their own files. Changing that means replacing its key hierarchy, its API and its server placement, which is most of the product (C2–C5). By the PLAN's decision rule ("adopt or fork only if the patch is ≤ 30 % of the build estimate"), the answer is to **build the Reliquary-specific parts and adopt proven components**: the age format, UniFFI, Tauri and its updater, SQLite, a homelab storage engine chosen by A6, and patterns (not code) borrowed from Ente and Immich. Confidence in "no candidate fits" is **high**, because every failure cell rests on a primary source (docs or code).

Confidence in the effort model is **low**. It is an analyst estimate by analogy, not a measurement. It puts v1 at roughly 1,070–2,140 focused hours. At the provisional 8 h/week, that is 2.6–5.1 years. So the owner's weekly hours, and a phased scope with stopgap protection in the meantime, matter more than the build-versus-adopt choice itself.

## Questions

| # | Question | Short answer | Confidence |
|---|---|---|---|
| 1 | Score each candidate against every settled requirement. What does each miss, and how big is the patch? | See the fit matrix and patch table. None passes the four trust-model knockouts as shipped. The smallest credible patch is to fork Ente, estimated at ≥ 60 % of the build, because the patch has to replace the key model, the API, the delete paths and the server topology, and add the homelab, USB and assistant parts, which no candidate has. | High for the misses; Low for patch sizes |
| 2 | Which components should be adopted rather than built: an existing mobile client (AGPL, G3), rustic_core, an existing updater, an S3 multipart client, Bugsink? | **Adopt:** the age v1 format with the Go/Rust age implementations as independent decryptors; UniFFI; Tauri 2 plus tauri-plugin-updater; SQLite; A6's engine at the homelab. **Do not fork** an Ente or Immich mobile client: it is AGPL, written in Flutter (against T1 option C), and built on a crypto model we would rip out. Read it for patterns only. **rustic_core** is not usable on devices, because the restic format is symmetric; it is a candidate homelab engine for A6 only. **S3 multipart client:** devices use presigned URLs, so a plain HTTP client suffices (C1 to confirm the Worker side). **Bugsink** is PolyForm Shield 1.0.0 (source-available, not OSI); G3 decides. | Medium |
| 3 | Effort per component (Rust core, Android app, desktop app, Worker, homelab ingest, admin CLI, specs and vectors, tests)? | 1,070–2,140 focused hours in total (table in the effort model). Android (200–400 h) and the Rust core (160–320 h) are the largest items. | Low (estimate) |
| 4 | Yearly maintenance of a fork vs own code (upstream churn, licence duties, advisories, platform bumps)? | Own code: platform bumps are yearly and mandatory (Play target API 36 from 31 Aug 2026; the iOS 26 SDK from 28 Apr 2026). Estimated 60–120 h/year. A fork of Ente or Immich carries the same bumps, plus rebasing onto a fast upstream (Immich shipped major v2 in Oct 2025 and v3 in 2026) and AGPL duties. Estimated 150–300 h/year. | Medium for the facts; Low for the hours |
| 5 | *(new)* What ships in 6, 12 and 24 months at the owner's hours? | At 8 h/week (≈ 208 h in 6 months, ≈ 416 h a year): the 6-month mark is the A0 walking skeleton; 12 months adds hardened core, ingest, admin CLI and USB seeding; 24 months adds the desktop tray app and a minimal Android app. The full assistant v1 lands after 24 months unless the hours rise or the scope is cut. | Low |
| 6 | *(new)* Do the decision weights change the answer? | Not on their own. With the proposed weights, "do nothing" and "adopt Immich" score as well as "build" or better. The settled requirements, applied as knockouts, are what rule them out. The weights matter mainly for choices *within* the build: component adoption, phasing and platform order. | Medium |

## Method

- **Sweep:** four scouts ran: docs, source, issues and forums, and pricing/policy/standards. Their JSON findings were merged, and conflicts were resolved below.
- **Deep read (this note):** the analyst re-fetched and read the load-bearing primary sources on 2026-09-29, from raw GitHub mirrors, developer.android.com and developer.apple.com. It added three primary code reads the scouts had only inferred:
  - Kopia `internal/server/grpc_session.go` (the server encrypts);
  - UrBackup `urbackupclient/InternetClient.cpp` (the client dials the server);
  - Plakar/Kloset `encryption/symmetric.go` (symmetric, passphrase KDF).
- **Routes used:** `raw.githubusercontent.com` for vendor doc sources and code; developer.android.com and developer.apple.com direct; the scouts' GitHub MCP repository metadata (not re-queried).
- **Blocked sources:** listed under Sources, blocked. All are reported to H1 for `sources.md`; none was silently replaced. New in this deep read: **the WebSearch budget for the session is exhausted (200/200)**, so Synology Photos and PhotoSync could not be researched further.
- **Stop rule:** stopped once every fit-matrix cell for the four knockout requirements rested on a primary source. Two cells remain unknown (Synology Photos, PhotoSync encryption) and are marked "?".
- **Estimates:** the effort model is estimation by analogy and judgement, labelled as such. The only in-repo data point is the throwaway content-encryption spike: 2,919 lines of Rust, Python and tools, counted with `wc -l`. The F1-S1 spike runner is expected to supply tokei counts of comparable code for calibration.

## Sources

| # | Source (title and URL or mirror path) | Publisher | Published or version date | Accessed | Primary? |
|---|---|---|---|---|---|
| S1 | Ente architecture: `ente-io/ente @ main : architecture/README.md` | Ente | main | 2026-09-29 | Yes |
| S2 | Ente self-hosting, object storage: `ente-io/ente @ main : docs/docs/self-hosting/administration/object-storage.md` | Ente | main | 2026-09-29 | Yes |
| S3 | Museum README: `ente-io/ente @ main : server/README.md` | Ente | main | 2026-09-29 | Yes |
| S4 | Museum FileController: `ente-io/ente @ main : server/pkg/controller/file.go` (GetUploadURLs l.335–347, Trash l.586–610) | Ente | main | 2026-09-29 | Yes (code) |
| S5 | Museum config: `ente-io/ente @ main : server/configurations/local.yaml` (db l.119; fixed bucket keys; compliance flag) | Ente | main | 2026-09-29 | Yes (code) |
| S6 | Ente duplicate detection: `ente-io/ente @ main : docs/docs/photos/features/backup-and-sync/duplicate-detection.md` | Ente | main | 2026-09-29 | Yes |
| S7 | Ente post-install (custom endpoint via hidden developer setting): `ente-io/ente @ main : docs/docs/self-hosting/installation/post-install/index.md` | Ente | main | 2026-09-29 (scout) | Yes |
| S8 | Ente LICENSE (AGPL-3.0): `ente-io/ente @ main : LICENSE` | Ente | main | 2026-09-29 (scouts) | Yes |
| S9 | Kopia Repository Server docs: `kopia/kopia @ master : site/content/docs/Repository Server/_index.md` | Kopia | master | 2026-09-29 | Yes |
| S10 | Kopia gRPC API: `kopia/kopia @ master : internal/grpcapi/repository_server.proto`; `internal/server/grpc_session.go` (l.296 `WriteContent(ctx, gather.FromSlice(req.GetData()) …)`) | Kopia | master | 2026-09-29 | Yes (code) |
| S11 | Kopia Encryption docs: `kopia/kopia @ master : site/content/docs/Advanced/Encryption/_index.md` | Kopia | master | 2026-09-29 | Yes |
| S12 | Kopia Ransomware Protection: `kopia/kopia @ master : site/content/docs/Advanced/Ransomware Protection/_index.md` | Kopia | master | 2026-09-29 | Yes |
| S13 | restic design: `restic/restic @ master : doc/design.rst` | restic | master | 2026-09-29 | Yes |
| S14 | rest-server README: `restic/rest-server @ master : README.md` | restic | master | 2026-09-29 | Yes |
| S15 | restic README (platforms): `restic/restic @ master : README.md` | restic | master | 2026-09-29 | Yes |
| S16 | Borg changelog: `borgbackup/borg @ master : docs/changes.rst` (2.0.0b1 2022-08-08; b25 2026-09-27; "remove remainders of append-only and quota support"; `BORG_REPO_PERMISSIONS`) | Borg | 2026-09-27 | 2026-09-29 | Yes |
| S17 | Borg 1.4 append-only notes: `borgbackup/borg @ 1.4-maint : docs/usage/notes.rst` | Borg | 1.4-maint | 2026-09-29 | Yes |
| S18 | R2 S3 API compatibility: `cloudflare/cloudflare-docs @ production : src/content/docs/r2/api/s3/api.mdx` | Cloudflare | production | 2026-09-29 | Yes (mirror) |
| S19 | R2 bucket locks: `cloudflare/cloudflare-docs @ production : src/content/docs/r2/buckets/bucket-locks.mdx` | Cloudflare | production | 2026-09-29 | Yes (mirror) |
| S20 | Immich asset table: `immich-app/immich @ main : server/src/schema/tables/asset.table.ts` (unique `ownerId, checksum`; sha1) | Immich | main | 2026-09-29 | Yes (code) |
| S21 | Immich Upgrading: `immich-app/immich @ main : docs/docs/install/upgrading.md` (semver; majors only; `:v3` metatag; app/server major compatibility) | Immich | main | 2026-09-29 | Yes |
| S22 | Immich README (3-2-1 warning; background backup): `immich-app/immich @ main : README.md` | Immich | main | 2026-09-29 | Yes |
| S23 | Immich FAQ (duplicates per library): `immich-app/immich @ main : docs/docs/FAQ.mdx` l.250–252 | Immich | main | 2026-09-29 | Yes |
| S24 | Syncthing untrusted devices: `syncthing/docs @ main : users/untrusted.rst` | Syncthing | main | 2026-09-29 | Yes |
| S25 | syncthing-android README (Discontinued): `syncthing/syncthing-android @ main : README.md` | Syncthing | notice refers to the Dec 2024 release | 2026-09-29 | Yes |
| S26 | Duplicati GPG module: `duplicati/duplicati @ master : Duplicati/Library/Encryption/GPGEncryption.cs` | Duplicati Inc. | master | 2026-09-29 | Yes (code) |
| S27 | Plakar README: `PlakarKorp/plakar @ main : README.md`; Kloset README and `encryption/symmetric.go` (`PlakarKorp/kloset @ main`) | Plakar Korp | main | 2026-09-29 | Yes |
| S28 | Nextcloud E2EE app README: `nextcloud/end_to_end_encryption @ master : README.md` | Nextcloud | master | 2026-09-29 | Yes |
| S29 | Nextcloud Memories README: `pulsejet/memories @ master : README.md` | pulsejet | master | 2026-09-29 | Yes |
| S30 | UrBackup client internet mode: `uroni/urbackup_backend @ dev : urbackupclient/InternetClient.cpp` (l.330–348 reads `internet_server`/`internet_server_port`; l.424 `connect(...)`) | UrBackup | dev | 2026-09-29 | Yes (code) |
| S31 | Google Play target API level requirement: https://developer.android.com/google/play/requirements/target-sdk | Google | Last updated 2026-09-16 | 2026-09-29 | Yes |
| S32 | Apple "Upcoming SDK minimum requirements": https://developer.apple.com/news/?id=ueeok6yw | Apple | 2026-02-03 | 2026-09-29 | Yes |
| S33 | Licences (all fetched by scouts from each repo's LICENSE/COPYING at HEAD): Immich, Nextcloud, UrBackup, Memories (AGPL-3.0); Kopia (Apache-2.0); restic and rest-server (BSD-2); rustic_core (MIT OR Apache-2.0); Borg (BSD-style); Syncthing (MPL-2.0); Plakar (ISC); Duplicati (MIT with a `proprietary/` carve-out); Spacedrive (FSL-1.1-ALv2); Bugsink (PolyForm Shield 1.0.0) | respective projects | HEAD | 2026-09-29 (scouts) | Yes |
| S34 | Go module proxy, latest versions: kopia v0.23.1 (2026-06-15); restic v0.19.1 (2026-07-05); plakar v1.1.7 (2026-09-24) | proxy.golang.org | as listed | 2026-09-29 (scout) | Yes |
| S35 | crates.io API: rustic_core versions (0.10.0 2026-02-11 … 0.13.0 2026-08-16); rustic_core README (MSRV 1.91) | crates.io; rustic-rs | as listed | 2026-09-29 (scouts) | Yes |
| S36 | GitHub repository metadata (stars, open issues plus PRs, archived flag) for 11+ repos, via GitHub MCP search | GitHub | queried 2026-09-29 | 2026-09-29 (scouts) | Yes (metadata) |
| S37 | Immich issues #21022, #21921, #22850, #9129 (mobile upload); #29445, #29453 (v3.0.0 upgrade); #31485 (reported data loss, 3.1→3.2) | GitHub | 2024-04 … 2026-09 | 2026-09-29 (scout) | No (user reports) |
| S38 | restic issues #187 (asymmetric backups, since 2015), #5041 (host-compromise model), #22057 (forged `--time` defeats append-only retention) | GitHub | 2015; 2024-09-02; 2026-09-08 | 2026-09-29 (scouts; search snippets) | No |
| S39 | Kopia issues #5199, #5108 (compromised client and lock maintenance) | GitHub | — | 2026-09-29 (scout; snippets) | No |
| S40 | Cure53 audits of Ente: 2023 crypto audit PDF; Oct 2025 report and summary | Ente / Cure53 | 2023-03; 2025-10 | 2026-09-29 (scouts; search snippets only, ente.com/ente.io blocked) | Primary, but read as snippet only |
| S41 | Backblaze Help: "Backing up External Hard Drives"; "Version History FAQ" (30-day default; 1-year or forever option) | Backblaze | — | 2026-09-29 (scouts; snippets, site blocked) | Primary, but read as snippet only |
| S42 | PhotoSync support: iOS autotransfer limits; premium features | PhotoSync | — | 2026-09-29 (scouts; snippets, site blocked) | Primary, but read as snippet only |
| S43 | Vendor exits: CrashPlan for Home (9to5Mac, TidBITS 2017-08-22; TidBITS 2018-10-22); Amazon Drive (AppleInsider 2022-07-29; Amazon FAQ as a snippet) | press; Amazon | 2017–2022 | 2026-09-29 (scouts) | No (Amazon FAQ primary as a snippet only) |
| S44 | Spacedrive README and LICENSE; v2 history page (snippet); AlternativeTo pause report (snippet) | Spacedrive; AlternativeTo | 2025–2026 | 2026-09-29 (scouts) | README/LICENSE yes; history page as a snippet |
| S45 | Albrecht et al., "Share with Care: Breaking E2EE in Nextcloud" (EuroS&P 2024, ePrint 2024/546); Hofmann & Truong (CCS 2024, ePrint 2024/1616) | IACR / IEEE / ACM | 2024 | 2026-09-29 (scout; abstracts via snippets) | Primary, but read as snippet only |
| S46 | `docs/research/client-stack.md` (T1), `content-encryption-format.md` (T1 spike 2), `owner-intake.md` (H2 Q-B9), `b4-ios-decision.md` (Immich PR #28293 iOS upload extension) | this repo | 2026-09-29 | 2026-09-29 | Yes (internal) |

**Blocked or snippet-only (reported to H1):**
- gnu.org (AGPLv3 §13 text);
- fsf.org (App Store GPL enforcement);
- immich.app blog (v2.0.0 and v3.0.0 posts);
- ente.com and ente.io (Cure53 reports, pricing);
- backblaze.com;
- photosync-app.com;
- urbackup.org manual (worked around with primary source code, S30);
- eprint.iacr.org;
- ndsa.org;
- forum.syncthing.net;
- news.ycombinator.com and reddit.com;
- api.github.com from the shell;
- **WebSearch budget exhausted (200/200) during this deep read.**

## Claims

Skeptic columns are left for stage 4. "Key?" follows PLAN §5.1.

| # | Claim | Sources | Key? | Skeptic 1 | Skeptic 2 | Skeptic 3 | Verdict |
|---|---|---|---|---|---|---|---|
| C1 | No candidate below meets all four trust-model requirements (R-18, R-20/R-19, R-21, R-12) as shipped. Every candidate fails at least two. | Matrix below (C2–C14) | Yes | pending | pending | pending | pending |
| C2 | Ente generates a per-user `masterKey` on the device, protected by a password-derived `keyEncryptionKey`. "Only you have access to your masterKey", so every signed-in device can decrypt the user's data and the operator cannot (no escrow). | S1 | Yes | | | | |
| C3 | Ente museum issues presigned URLs for object keys `<userID>/<uuid>`, which are random per upload rather than content-addressed. Dedup is per user and per album by hash; the docs describe no cross-user dedup. | S4, S6 | Yes | | | | |
| C4 | Ente clients call museum directly. Museum needs Postgres. The bucket endpoint in presigned URLs must be reachable by clients and museum alike. A homelab museum therefore needs inbound reachability, or museum plus Postgres must run as a cloud server, which ADR-0001's Workers/D1 shape does not provide. | S2, S3, S5 | Yes | | | | |
| C5 | Ente's `Trash` endpoint lets an authenticated user trash files they own in collections they own, so a client credential can remove its own history. | S4 | Yes | | | | |
| C6 | Kopia repository encryption is symmetric: the master key is derived from the repository password (scrypt + HKDF, AES256-GCM). restic (AES-256-CTR + Poly1305-AES, scrypt-unlocked master key), Plakar/Kloset (symmetric, Argon2id/scrypt KDF) and Syncthing untrusted devices (shared folder password, scrypt) are symmetric too. Any device that can write can decrypt. | S11, S13, S27, S24 | Yes | | | | |
| C7 | In Kopia repository-server mode the client sends plaintext content over TLS (`WriteContentRequest.data`), and the **server** encrypts it (`ContentManager().WriteContent`). The server listens (`--address`), so the homelab would be inbound-reachable and sees plaintext. Default ACLs give each user FULL on their own snapshots and APPEND on content. | S9, S10 | Yes | | | | |
| C8 | Cloudflare R2's S3 API does not support S3 Object Lock (`x-amz-object-lock-*` headers and the `*ObjectLockConfiguration` calls are unsupported). R2 instead offers "bucket locks": retention rules per prefix, configured by dashboard, Wrangler or API. Kopia's object-lock ransomware protection therefore does not work against R2 through the S3 API. | S18, S19, S12 | Yes | | | | |
| C9 | restic rest-server `--append-only` "prevents deletion and modification of existing backups", but rest-server is a server that listens (`--listen`, default `:8000`), so an outbound-only homelab cannot host it. The retention integrity of append-only mode against a compromised client is an open issue (#5041, #22057). | S14, S38 | Yes | | | | |
| C10 | Immich dedups by SHA-1 with a unique index on `(ownerId, checksum)`, i.e. per user. Its README warns users to keep a 3-2-1 backup. It stores files unencrypted on the server (it has no client-side encryption; nothing in its docs describes one). It follows semver with breaking changes in majors, and its docs already use a `:v3` metatag. | S20–S23 | Yes | | | | |
| C11 | The UrBackup client in internet mode connects out to the configured `internet_server` host and port, so the server must accept inbound connections. The backend is AGPL-3.0. Scouts found no mobile clients. | S30, S33, S36 | Yes | | | | |
| C12 | Syncthing's untrusted-device mode is "beta / testing only". The official Android app is discontinued (its last release came with the Dec 2024 Syncthing version), with "Google making Play publishing something between hard and impossible" cited as a reason. | S24, S25 | Yes | | | | |
| C13 | Borg 2 has been in beta since 2.0.0b1 (2022-08-08); the latest is 2.0.0b25 (2026-09-27). Borg 2 removed append-only and replaced it with `BORG_REPO_PERMISSIONS=all\|no-delete\|write-only\|read-only`. | S16 | No (context) | | | | |
| C14 | Nextcloud E2EE is opt-in per folder, cannot encrypt a sync root, needs one mnemonic shared by all devices, and requires server-side encryption to be off. Automatic uploads for Memories rely on the official Nextcloud apps. | S28, S29 | Yes | | | | |
| C15 | Google Play: from 31 Aug 2026, new apps and updates must target API 36. Apple: from 28 Apr 2026, uploads must be built with the iOS 26 SDK. Own apps and forks alike carry a mandatory yearly platform bump. | S31, S32 | Yes | | | | |
| C16 | rustic_core is 0.x with four minor (breaking under Cargo semver) releases between 2026-02-11 and 2026-08-16. It implements the symmetric restic format, so it cannot be a device-side component under R-20. | S35, S13 | Yes | | | | |
| C17 | Ente, Immich, Nextcloud, Memories and UrBackup are AGPL-3.0. Forking any of their clients makes that Reliquary component AGPL (OD-15, G3). Whether AGPL is compatible with the iOS App Store is **not verified** (gnu.org and fsf.org blocked; VLC 2011 is a secondary precedent only). | S33 (+ S43-class secondary) | Yes | | | | Secondary only for the App Store part |
| C18 | **Effort estimate:** v1 as specified needs about 1,070–2,140 focused hours. At 8 h/week that is 2.6–5.1 years. | Analyst estimate; S46 | Yes | | | | Estimate, not a measurement |
| C19 | Immich shipped major versions v2.0.0 (announced as the first stable, Oct 2025) and v3.0.0 (upgrade issues filed 2026-07-02) about 9 months apart. | S21 (`:v3`), S37; blog blocked | Yes | | | | Partly secondary |
| C20 | Backblaze Personal keeps deleted versions and detached drives for 30 days by default, with 1-year or forever history as options. | S41 (snippet) | No | | | | Secondary only (site blocked) |
| C21 | Duplicati's GPG module defaults to `--symmetric`, but the encryption command is configurable (help text names `--encrypt`), so encryption to a recipient's public key is possible by option. Whether its verification and compaction work without the private key is **unknown**. | S26 | No | | | | |

### Conflicts between scouts, resolved

| Topic | Scout statements | Resolution |
|---|---|---|
| Latest Borg 2 beta | "b25 2026-09-27" vs "b24 2026-09-02" | Both are right; b25 is later (S16 read directly). Borg 2 has now been in beta for 4+ years. |
| Ente repo name | `ente-io/ente` vs `ente/ente` (a GitHub search on the former returned 422) | Raw mirrors under `ente-io/ente` still resolve. The docs link to `github.com/ente/ente`, so treat it as a rename with a redirect. The stars figure (29,150) comes from `ente/ente`. |
| Immich open issues | 680 vs 678 | `open_issues_count` includes PRs and was sampled at different times. Immaterial. |
| Ente Cure53 Oct 2025 outcome | "all but one Medium verified fixed" vs "12 of 15 fixed incl. all Critical/High" | **Unresolved.** Both come from snippets and the PDF was blocked. Not load-bearing for F1: Ente is rejected on its trust model, not its code quality. Route to F3. |
| Kopia server-side encryption | "medium, inferred from proto" | **Upgraded to high:** `grpc_session.go` l.296 passes the client's bytes to `ContentManager().WriteContent`, which encrypts on the server (S10). |
| UrBackup connection direction | manual blocked; snippet said "server public name and port" | **Confirmed** from client source (S30). |
| Borg append-only | "Borg 2 removes append-only" vs "Borg 2 uses --permissions on serve" | Both are true (S16). |

## Findings

### 1. Requirement-fit matrix (as shipped)

Legend: **Y** meets as shipped; **P** partial or only by configuration; **N** misses; **?** unknown or not researched; **n/a** not applicable. The claim IDs that back a cell are in the last column. The four knockout columns come first.

| Candidate | R-20 devices cannot read / R-19 enc. to homelab key / R-22 escrow | R-21 opaque cross-user dedup | R-18 append-only devices | R-12 outbound-only homelab (and R-11 R2 staging) | R-14 USB transport | R-02/R-04 phones first-class | R-29 discovery | R-30/31/42 health and nudges | R-26/27 keep forever | R-35/37 restore to device key | R-10 Linux/Proxmox server | Licence | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Ente self-hosted** (museum + S3) | N (per-user password-derived keys on device; no escrow) | N (random per-upload object keys; per-user hash dedup) | N (Trash by owner) | N (clients call museum; museum + Postgres must be reachable) | N | Y (Android, iOS; background upload) | P (camera roll and folders; no document discovery) | P (upload status; no plain-language per-person health or email nudges) | P (user can delete) | N (user self-restores with own keys) | Y (Docker) | AGPL-3.0 | C2–C5, S7 |
| **Immich** | N (server-side plaintext) | N (per-user SHA-1) | N (two-way sync; deletions possible) | N (app uploads to the server) | N | Y | P (albums and folders) | P (backup counts) | P | N | Y | AGPL-3.0 | C10, S37 |
| **Nextcloud + Memories** | N (server-side encryption by default; E2EE per folder with a shared mnemonic, and not the root) | N | N | N | N | P (official apps; auto-upload silent failures, F2) | N | N | P | N | Y | AGPL-3.0 | C14, S45 |
| **Synology Photos** | ? (not researched; WebSearch exhausted) | ? | ? | ? (needs DSM, not plain Proxmox) | ? | ? | ? | ? | ? | ? | ? | Proprietary | none (gap) |
| **PhotoSync → homelab** (SMB/SFTP/WebDAV) | ? (a "encrypt before transfer" claim exists as a snippet only; no public-key recipient documented) | N | N (the target share is writable) | N (targets must be reachable, except S3 targets, which are iOS premium) | N | P (iOS background ~3 min per its support page, as a snippet) | N | N | P | N | Y (any server) | Proprietary | S42 |
| **restic per desktop + rest-server --append-only** | N (symmetric) | N (per-repo; unkeyed SHA-256 blob IDs) | P (append-only, but see #22057) | N (rest-server listens) | P (a repo can sit on a disk) | N (desktop OSes only) | N | N | Y (with append-only) | N | Y | BSD-2 | C6, C9, S15 |
| **Kopia per desktop** (repository server, or S3 + object lock) | N (symmetric; server mode encrypts server-side) | P (keyed hashes, shared content IDs; any user who knows an ID can read) | P (APPEND on content, FULL on own snapshots by default; object lock not on R2) | N (server listens; direct-to-R2 has no lock) | P | N (no mobile client found) | N | N | P | N | Y | Apache-2.0 | C6–C8 |
| **Syncthing untrusted devices** | N (shared symmetric password) | N | N (sync semantics) | N (P2P; relays or inbound) | N | P (only the community fork on Android) | N | N | N (deletes propagate unless versioning is set) | N | Y | MPL-2.0 | C6, C12 |
| **UrBackup internet mode** | N (transport encryption only, per snippet) | P (server-side dedup, not opaque) | ? | N (client dials the server) | N | N (no mobile) | N | P (server-side reports) | P | N | Y | AGPL-3.0 | C11 |
| **Duplicati** (GPG to a recipient) | P (`--encrypt` possible; untested) | N (per job) | N (the storage key can delete; R2 has no object lock) | Y (writes to R2 directly) | P | N (no mobile found) | N | P | P | N | n/a | MIT + proprietary/ | C21, C8 |
| **Plakar** | N (symmetric) | N | P (immutable store; client holds the full key) | P (can write to S3) | P (`.ptar` archives) | N | N | N | Y | N | Y | ISC | C6, S27 |
| **Borg** (1.4 or 2 beta) | N (symmetric) | N (keyed chunk IDs per repo; good prior art) | P (1.4 append-only is segment-level only; 2.x `no-delete` is beta) | N (SSH server listens) | P | N | N | N | P | N | Y | BSD-style | C13, S17 |
| **Do nothing** (Backblaze Personal + each phone's cloud) | N (vendor-held; no homelab) | n/a | P (vendor controls) | n/a (no homelab) | N | Y (phone vendor apps) | Y (Backblaze backs up everything) | P (vendor emails) | N (30-day default) | N | n/a | Proprietary | C20, S43 |
| **Build Reliquary** (reference) | Y by design (ADR-0001 §2; content-encryption spike) | Y by design | Y by design (A3/C1/D4 to prove) | Y by design | Y by design | Y (Android v1; iOS per OD-01) | Build | Build | Build | Build | Y | Owner's choice (OD-15) | ADR-0001, S46 |

**Reading the matrix.** The thirteen existing candidates (Synology is a gap) split into two families:

- **Photo managers** (Ente, Immich, Nextcloud, PhotoSync). They have good phone clients, but their servers are reachable services with user-owned deletion and per-user keys or plaintext.
- **Backup engines** (restic, Kopia, Borg, Plakar, Duplicati, UrBackup). They have good storage formats but no phone clients, symmetric keys that let every writer read, and servers that listen.

Neither family has discovery, per-person health or nudges. Those are Reliquary's reason to exist (R-29–R-31), so they would have to be built in every scenario.

### 2. Patch size for the top three alternatives (the PLAN asks for "top 2 costed")

Build estimate midpoint: about 1,600 h (effort model below). The decision rule's 30 % line is about 480 h.

| Alternative | What the patch must change | Share of build (estimate) | Rule outcome |
|---|---|---|---|
| **Fork Ente** (Flutter mobile + museum) | Replace the key hierarchy: encrypt to the homelab key; devices can no longer decrypt, which breaks Ente's gallery, sync and search features, all of which assume the device can decrypt. Add HMAC dedup IDs and a cross-user index. Remove the Trash and delete paths. Move museum and Postgres to a cloud VM (outside ADR-0001's Workers/D1 shape), or rewrite museum as a Worker. Add homelab pull ingest, USB bundles, receipts, admin restore, discovery, health and nudges, and a desktop file agent (Ente desktop is a photo app). Then ship Flutter on Android against T1's option C, and carry AGPL. | ≥ 60–80 % | Fails (> 30 %) |
| **Compose**: restic or Kopia on desktops + PhotoSync on phones + glue | Asymmetric encryption for restic, requested since 2015 (#187) and still open, means forking the repository format. Append-only needs a listening server, or R2 bucket locks plus a Worker gateway (new code). No cross-user opaque dedup. Phones would need a separate proprietary app with no homelab-key encryption. Discovery, health, nudges, USB and restore-to-device-key are all new. Three tools for relatives to understand. | ≥ 70 % (most of Reliquary rebuilt as glue, plus a format fork) | Fails |
| **Adopt Immich** + nightly homelab copy | Everything in the trust model: client encryption, opaque dedup, append-only, outbound-only. Immich is a gallery, not a backup of record (its own README says so). | Not patchable without replacing its server model | Fails |

**Confidence:** High that each patch touches the trust core (C2–C10). Low on the percentages, which are judgement.

### 3. Components to adopt (not code to fork)

| Component | Use | Licence | Maturity | Verdict | Source |
|---|---|---|---|---|---|
| age v1 format; Go `age` and Rust `age` as independent decryptors | Content and metadata envelope | BSD-3 / MIT-Apache (per the spike note) | Stable spec (C2SP) | **Adopt** (already chosen in the spike) | S46 |
| UniFFI | Rust core to Kotlin (Swift later) | MPL-2.0 (per T1) | Mozilla-backed, in production | **Adopt** | S46 |
| Tauri 2 + tauri-plugin-updater (minisign) | Desktop tray, packaging, signed updates | MIT/Apache | Stable | **Adopt** (T1) | S46 |
| rustic_core | Restic-format engine | MIT OR Apache-2.0 | 0.x, 4 minor releases in 2026, 89 stars (2026-09-29) | **Not on devices** (symmetric format, R-20). A candidate for A6 at the homelab, with a churn risk. | C16, S36 |
| restic / Kopia / Plakar / Borg / PBS | Homelab storage engine behind ingest | BSD-2 / Apache-2.0 / ISC / BSD | restic 0.19.1, Kopia 0.23.1 (pre-1.0); Plakar 1.1.7; Borg 1.4 stable, 2.x beta | **A6 decides** (ADR-0012). Symmetric keys are acceptable at the homelab, which holds the private key anyway. | S34, C13 |
| Ente and Immich mobile upload code | Patterns only: multipart resume (`ente … upload/service/multipart.dart`), iOS background upload extension (Immich PR #28293, see B4) | AGPL-3.0 | Active | **Read, do not copy.** Copying makes our component AGPL. | S8, S46 |
| S3 multipart client | Devices upload through Worker-issued presigned URLs, so any HTTP client works. The Worker side uses the R2 binding (C1 to confirm). | — | — | **No SDK needed on devices** | ADR-0001 §4 |
| Bugsink | Self-hosted crash collector (B8/C7) | PolyForm Shield 1.0.0 (source-available; not OSI) | — | **G3 to decide.** Internal non-competing use is likely fine, but it does not fit an OSI licence policy. | S33 |
| Syncthing-Fork, PhotoSync, Backblaze | Interim stopgaps only (E2-S3) | MPL / proprietary | — | **Stopgap, not architecture** | C12, C20 |

### 4. Effort model (one maintainer)

**Unit:** focused engineering hours. **All numbers are analyst estimates by analogy. None is measured.** Calibrate them with:
- F1-S1 tokei counts of comparable code;
- A0 skeleton actuals (the best calibration: time the skeleton);
- the content-encryption spike (≈ 2.9k lines of throwaway code built in one run).

| Component | Scope for v1 | Low (h) | High (h) | Main risk |
|---|---|---|---|---|
| Specs and vectors | identifiers, object format, ingest protocol, bundle and manifest (A1–A4 specs; much already drafted by research) | 40 | 80 | Churn from D1 tabletops |
| Rust core | hash cache, HMAC IDs, resumable age encoder (spike exists), upload state machine, SQLite, bundle writer, receipt verification | 160 | 320 | Crypto and state-machine correctness |
| CLI client | Linux, Windows and macOS CLI on the core (skeleton first) | 30 | 60 | — |
| Worker + D1 | API v1, device auth, presign, claim/commit, rate limits, `restore/` prefix | 100 | 200 | Abuse limits (C2), R2 behaviour (C1-S1) |
| Homelab ingest | pull and reconcile, decrypt and verify, engine adapter or CAS, catalog, signed receipts, USB import | 120 | 240 | Engine choice (A6) |
| Admin CLI | invites, revoke, restore, status, key-ceremony helpers | 50 | 100 | — |
| Desktop app | Tauri tray + daemon, autostart on 3 OSes, updater, enrollment, health UI | 150 | 300 | SAC and signing (OD-09), per-OS quirks |
| Android app | Kotlin/Compose, WorkManager/UIDT, MediaStore originals, QR enrollment, health UI, Play closed track | 200 | 400 | OEM background kills (B2), Play policy (B3) |
| Assistant logic | discovery rules, health model, nudges and email | 80 | 160 | Tuning with real families (E3/E4) |
| Tests and CI | cross-platform CI, golden corpus, fault injection | 80 | 160 | Device coverage |
| Packaging and ops | USB kit build, runbooks, docs | 60 | 120 | — |
| **Total** | | **1,070** | **2,140** | |

**Owner capacity.** Q-B9 is not answered yet; the provisional figure is 8 h/week. That gives about 35 h per month, 208 h in 6 months, 416 h in 12 months and 832 h in 24 months. At that rate v1 takes about 2.6–5.1 years.

**What ships when, at 8 h/week (proposal for E2 and ADR-0004):**

| By | Cumulative hours | Ships | Family protection meanwhile |
|---|---|---|---|
| 6 months | ~210 | A0 walking skeleton: CLI → Worker/R2 → homelab → verified restore (Gate B) | Stopgaps per device type (E2-S3) |
| 12 months | ~420 | Hardened core and ingest, admin CLI, USB seeding. The owner seeds relatives' computers in person with the CLI ("concierge" mode, Q-H4) | Stopgaps for phones |
| 24 months | ~830 | Desktop tray app with health view; minimal Android app (media only, OD-19). Discovery and nudges are basic. | Stopgaps retire device by device |
| After 24 months | 1,070–2,140 | Full assistant v1; iOS per OD-01 | — |

Levers, in order of impact:
1. More owner hours (16 h/week halves the calendar time).
2. A scope cut in ADR-0004: Android media only; basic nudges by email only; no iOS until the bridge.
3. Adopting the homelab engine instead of building CAS (saves an estimated 40–80 h).
4. AI-assisted implementation. There is no evidence of its speed-up yet; measure it in A0.

**Yearly maintenance (estimates):**
- **Own code: 60–120 h/year.** This covers the yearly Android target-API and iOS SDK bumps (C15), Tauri, UniFFI and dependency advisories, Cloudflare API changes, and certificate and signing chores.
- **A fork of Ente or Immich: 150–300 h/year.** This covers the same bumps, plus rebasing onto an upstream that ships majors about yearly (C19), plus AGPL source-offer duties.

Both figures exceed BUD-SUPPORT (≤ 2 h/month), but BUD-SUPPORT measures operational support, not development upkeep. The budget sheet has no line for development upkeep (hand-off to H1).

### 5. Decision weights for OD-02 (proposal)

The proposal has two stages:

1. **Knockouts.** The settled requirements (R-12, R-18, R-19–R-22, R-26, R-02/R-04) are pass/fail. A candidate that fails a knockout survives only if its patch is ≤ 30 % of the build (the PLAN rule).
2. **Weights** among the survivors and among build variants.

| Criterion | Proposed weight | Alternative A (effort-heavy) | Alternative B (UX-heavy) |
|---|---|---|---|
| Integrity (verifiable, restorable, append-only, no silent loss) | **35 %** | 30 % | 30 % |
| Maintenance (one person, yearly bumps, bus factor, licence duties) | **20 %** | 20 % | 15 % |
| Effort to v1 | **20 %** | 30 % | 15 % |
| Family UX (non-technical, near-zero enrollment, plain status) | **15 %** | 10 % | 30 % |
| Cost (cloud and one-off) | **10 %** | 10 % | 10 % |

**Illustrative scores** (1–5, analyst judgement, *before* knockouts; shown to demonstrate sensitivity, not to decide):

| Option | Integrity | Maint. | Effort | UX | Cost | Weighted (proposed) | Knockouts |
|---|---|---|---|---|---|---|---|
| Build + adopt components | 4 | 3 | 1 | 4 | 4 | 3.20 | Passes by design |
| Fork Ente | 3 | 1 | 2 | 4 | 3 | 2.55 | Fails; patch > 30 % |
| Compose restic/Kopia + PhotoSync | 2 | 3 | 4 | 1 | 4 | 2.65 | Fails; patch > 30 % |
| Adopt Immich | 2 | 3 | 4 | 4 | 4 | 3.10 | Fails |
| Do nothing | 2 | 4 | 5 | 3 | 2 | 3.15 | Fails |

**Finding:** the weights alone barely separate "build" from "do nothing" or "adopt Immich". The **settled requirements** make the decision, not the weights. Under Alternative A (effort 30 %), "do nothing" (3.40) and "adopt Immich" (3.20) outscore "build" (2.90). So the owner should confirm the weights mainly for later choices inside the build: component adoption, phasing, platform order and A6's engine. The weights must not be used to reopen settled requirements (CLAUDE.md). Confidence: Medium.

### Similar work and lessons

| Project | What happened | Borrow or avoid | Source |
|---|---|---|---|
| Ente | Audited E2EE photo backup. Per-user keys; museum mediates everything; self-hosting via a hidden 7-tap developer setting | Borrow: presigned direct-to-bucket upload with a server-side HEAD verify; key-wrapping discipline. Avoid: device-held master key (it conflicts with R-20); hidden self-host settings (conflict with R-08) | S1–S7 |
| Immich | Very active (115k stars); majors v2 (Oct 2025) and v3 (2026); mobile background-upload issues with 42–68 comments each; user-reported upgrade data loss (#31485, cause not read) | Borrow: backup counts on screen (F2); iOS upload-extension approach (B4). Avoid: tracking a fast upstream as a fork; gallery-as-backup | C10, C19, S37 |
| Spacedrive | Rust core + Tauri + mobile; $2M seed (secondary); development paused in 2025 for funding (secondary); its own history page says V1 became unmaintainable and was rewritten (snippet); licence now FSL (source-available) | Avoid: broad scope before a narrow core works. This supports the phased plan above | S44 |
| Syncthing Android | A volunteer app discontinued, citing Play publishing friction | Budget for Play compliance as recurring work (B3) | C12 |
| Borg 2 | Beta for 4+ years (2022-08 → 2026-09) | A format rewrite takes years even for a mature team; freeze formats early (Gate A) | C13 |
| CrashPlan for Home (2017→2018), Amazon Drive (2022→2023) | Consumer backup vendors exited; Amazon migrated only photos | The "do nothing" baseline carries vendor-exit risk, a reason for a homelab of record | S43 |
| restic append-only | Append-only mode does not protect retention against a compromised client (#22057) | Reliquary's rule "no device deletes, pruning is manual only" (R-28) avoids this class, and A3/D4 must test it | C9 |
| Kopia and R2 | Object lock is unavailable through the R2 S3 API; R2 has prefix bucket locks instead | C1/D4: consider an R2 bucket lock on committed or restore prefixes as a backstop; it is not an S3 lock | C8 |

## Spikes

*Placeholder: the F1 spike runner fills this section in parallel.*

| Spike | Exec tag | Budget IDs | Data class | Status | Result |
|---|---|---|---|---|---|
| F1-S1 Fit matrix for ≥ 8 candidates (+ tokei calibration) | CT | BUD-SUPPORT (maintenance context) | Public data only | Running (spike runner) | Pending. Reconcile with the analyst matrix in Findings §1 |
| F1-S2 (optional) Ente museum + Immich soak (shared with F2-S1) | OL | BUD-TTS, BUD-BAT-D | Owner test device, no family data | Kit expected from the spike runner | Pending |

## Conflicts with settled text

None. Nothing here proposes changing a settled requirement. Two notes:
- The finding that v1 does not fit 24 months at 8 h/week is a scope and hours matter for E2 (ADR-0004) and H2, not a conflict.
- Adopting any AGPL code would bind OD-15, which is why the recommendation avoids it.

## Open questions

| Question | Who | By when |
|---|---|---|
| The owner's real weekly hours (Q-B9). This is the dominant variable in the effort model | H2 / owner | Wave 1 exit |
| Calibrate the effort model: tokei counts of Ente and Immich mobile upload code and of museum; A0 actual hours | F1-S1 runner; A0 | Wave 1 / Gate B |
| Synology Photos: encryption, dedup, reachability (not researched; WebSearch budget exhausted) | F1 follow-up, or F2 | Wave 2 (low priority: it needs DSM, which conflicts with R-10 prima facie) |
| PhotoSync: does its "encrypt before transfer" exist, and with what key model? (snippet only) | F2 | Wave 2 |
| Can an R2 API token write without delete rights? Do R2 bucket locks fit the staging lifecycle (staged objects are deleted after commit)? | C1 (C1-S1) | Wave 1 |
| AGPL §13 text and App Store compatibility (gnu.org and fsf.org blocked) | G3 | Before adopting any code |
| Duplicati with GPG to a recipient: do verification and compaction need the private key? | Not needed unless Duplicati is reconsidered | — |
| The Ente Cure53 Oct 2025 outcome (conflicting snippets) | F3 | Wave 1 |

## Recommendation

**Build the Reliquary-specific system:**
- the Rust core;
- the Worker/D1 control plane;
- homelab ingest;
- the admin CLI;
- a Tauri desktop app;
- a Kotlin Android app.

Around it, **adopt proven components**: the age format, UniFFI, Tauri and its updater, SQLite, and A6's homelab engine. Do **not** fork Ente or Immich. Read their upload code for patterns only.

Why:
1. Every existing system fails at least two of the four trust-model requirements, and each patch exceeds the 30 % rule, because it would have to replace the part that makes the candidate what it is.
2. Discovery, health and nudges have to be built in every scenario anyway.
3. An AGPL Flutter fork would add upstream churn and licence duties that one maintainer cannot sustain.

**Pair the build with:**
- the phased plan (6 months: skeleton; 12: USB/CLI concierge seeding; 24: desktop + minimal Android);
- stopgap protection for keepsakes now (E2-S3), because at 8 h/week the family is otherwise unprotected for years.

**What would change this:**
- the owner relaxing a settled requirement (not proposed);
- a candidate gaining public-key "write-only" encryption plus service-enforced append-only (for example, restic #187 landing and a Worker-fronted repository);
- the owner having far fewer hours than 8/week. Then "compose stopgaps indefinitely" becomes the honest answer, and ADR-0005 should say so.

## Decision requests

### OD-02: Build, adopt or compose, and the decision weights
- **Needed by:** Wave 1 exit (sitting 2)
- **Evidence:** this note; ADR-0005 draft (to be written by synthesis from this note)
- **Options:**

  | Option | What it means for the family | Cost (money and owner time) | Reversibility | Risks |
  |---|---|---|---|---|
  | A. Build + adopt components (recommended) | The trust model is met as settled. Desktops are protected via USB/CLI within about 12 months, apps within about 24 months at 8 h/week | ~1,070–2,140 h to v1; 60–120 h/year upkeep; cloud per C4 | Easy early; costly after Gate A formats | Long calendar time; one-person bus factor |
  | B. Fork Ente | A polished phone app sooner, but a cloud VM + Postgres for museum, AGPL, and a gutted crypto model | Patch ≥ 60–80 % of build; 150–300 h/year upkeep | Costly | Upstream churn; the audit no longer applies to changed crypto |
  | C. Compose existing tools (restic/Kopia + PhotoSync + glue) | Several apps per person; no health view; devices can read backups | Lower first effort, high glue; breaks R-12, R-18, R-20, R-21 | Easy | Violates settled requirements; silent failures |
  | D. Do nothing (commercial) | Familiar apps, vendor retention rules (30-day default at Backblaze) | ~$99/yr per computer (unverified) + phone cloud plans | Easy | Vendor exit; not keep-forever; no homelab |

- **Weights to confirm:** integrity 35 %, maintenance 20 %, effort 20 %, family UX 15 %, cost 10 %, applied **after** the settled requirements are used as knockouts.
- **Recommendation:** A, with D-style stopgaps per device type in the meantime (E2-S3). The weights only order work inside A.
- **Touches settled text:** None.
- **If no decision by the deadline:** the run assumes A with the proposed weights. Nothing downstream is blocked, but G3/OD-15 stays open.

**Related request to H2 (not an OD):** answer Q-B9 (build hours per week). The effort model's calendar dates depend on it more than on any other input.

## ADR-0005 draft outline (for the synthesis stage)

- **Decision:** build the Reliquary-specific parts; adopt the components listed in §3; do not fork AGPL clients; two-stage evaluation (settled requirements as knockouts, then the OD-02 weights); phased delivery per the effort model.
- **Evidence rows:** C1–C12, C14–C16 (after skeptic review), C18 marked "estimate".
- **Confirmation:**
  - re-run the fit matrix yearly, or when a candidate ships public-key encryption;
  - compare A0 actual hours with the effort model at Gate B.
- **Reversibility:** reversible until Gate A. After that, the formats (not the build choice) are the one-way doors.

## Hand-offs

| To | What | Why |
|---|---|---|
| A6 | Engine shortlist facts: restic/rustic_core (0.x, churn), Kopia 0.23.1, Plakar 1.1.7 (symmetric, immutable store, `.ptar`), Borg 1.4 stable / 2.x beta | ADR-0012 knockout screen |
| C1 | R2 has no S3 Object Lock; prefix bucket locks exist. Check token delete granularity | R-18 enforcement on the cloud side |
| G3 | AGPL on Ente, Immich, Nextcloud and UrBackup; Bugsink under PolyForm Shield; Duplicati `proprietary/` carve-out; Spacedrive FSL | Licence inventory, OD-15 |
| E2 | Effort model and phased plan; stopgaps per device type | ADR-0004 scope |
| F2 | Immich and Nextcloud mobile-upload issue clusters from the community scout | Silent-failure catalogue |
| F3 | Borg keyed chunk IDs (MAC over plaintext) as prior art for HMAC IDs; Ente Cure53 conflict | Attack matrix, bibliography |
| H1 | Blocked hosts list above; WebSearch budget exhausted; candidate budget line for yearly development upkeep (separate from BUD-SUPPORT) | `sources.md`, `budgets.md` |
| H2 | Q-B9 is the dominant effort input | Intake |
