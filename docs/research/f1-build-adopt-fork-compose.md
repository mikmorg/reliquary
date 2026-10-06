# F1. Build, adopt, fork or compose, and what one maintainer can sustain

- **Workstream:** F1 (see `docs/research/PLAN.md`, section "F1.")
- **Status:** Final (Wave 1). Synthesised after three-skeptic review; the key-claim verdicts are exactly as computed by the tally. Rows added during synthesis (Duplicacy, bupstash, split restic/Kopia rows) rest on primary sources read on 2026-10-06 but have **not** been through skeptic review, and are marked so.
- **Date:** 2026-09-29 (last updated 2026-10-06)
- **Feeds:** ADR-0005 (`docs/adr/0005-build-and-adopt-components.md`, Proposed), OD-02, input to ADR-0004 (E2, phasing) and ADR-0012 (A6, engine shortlist). No one-way door.
- **Depends on:** H2 (owner hours per week, Q-B9, still unanswered), T1 (`client-stack.md`; ADR-0003 still pending), `content-encryption-format.md` (T1 spike 2)
- **Traceability rows advanced:** input to every R-row a candidate is scored against (R-02, R-04, R-10–R-12, R-14, R-18–R-23, R-26–R-31, R-35, R-37, R-42, R-44–R-46). F1 closes none of them itself.

## Summary

**No researched system meets Reliquary's settled trust model as shipped.** Thirteen systems were researched, in fifteen configurations, against four trust-model knockouts:

- devices cannot read backup data, because content and metadata are encrypted to the homelab public key (R-19, R-20, R-22);
- opaque cross-user deduplication (R-21);
- append-only devices enforced by the service (R-18);
- a homelab that only makes outbound connections (R-12).

None passes all four, and **none of them has a phone client that would also pass**. The closest engines each miss at least one knockout clearly:
- Duplicacy with RSA leaves metadata readable by every writer, and its writers can prune.
- bupstash needs an ssh-reachable repository host.
- Duplicati has no cross-user dedup.
- Kopia writing directly to R2 gives every device the symmetric key.

The photo managers (Ente, Immich, Nextcloud) fail three or four knockouts. Synology Photos was not researched and is a gap. The do-nothing option (Backblaze Personal plus phone clouds) is treated as a baseline and a stopgap, not as a candidate.

The recommendation is to **build the Reliquary-specific parts and adopt proven components**: the age format, UniFFI, SQLite, an updater, and A6's homelab engine. The client UI stack follows ADR-0003, which is still pending. **Do not fork** Ente, Immich or any other AGPL client. Read them for patterns only.

This recommendation rests on the **verified** per-candidate claims K2–K9 and K14. It does not rest on the contested aggregate K1, the contested patch percentages K11, or the contested effort and upkeep hours K10 and K13. Confidence that no candidate fits is **medium-high**: primary sources back the knockout cells of every researched system except the snippet-only cells marked below.

**The effort model is an estimate and was contested by all three skeptics.** Revised for this wave, it puts v1 at about **1,260–2,520 focused hours before contingency**. At the provisional 8 h/week that is **3.0–6.1 years**, or **3.6–7.3 years with 20 % contingency**. The phased dates handed to E2 earlier were optimistic and are withdrawn (see §4). The owner's weekly hours (Q-B9), the scope cuts in ADR-0004, and stopgap protection in the meantime matter more than the build-versus-adopt choice.

## Questions

| # | Question | Short answer | Confidence |
|---|---|---|---|
| 1 | Score each candidate against every settled requirement. What does each miss, and how big is the patch? | See the fit matrix (§1). No researched system meets all four trust knockouts, and none has a phone client that would. Patch size: the PLAN's "patch ≤ 30 % of build" test is close to tautological as applied. Every path must build the Reliquary-only parts (ingest, USB, discovery, health, nudges, admin restore), and those alone are about 30 % of the build. §2 therefore replaces the percentages with a delta test: what would a fork save against the component it replaces? For the top two alternatives the saving is bounded by one component line, and the trust-model rewrite eats into it. | High for the misses on primary-sourced cells; Low for any hours |
| 2 | Which components should be adopted rather than built: an existing mobile client (AGPL, G3), rustic_core, an existing updater, an S3 multipart client, Bugsink? | **Adopt:** the age v1 format (Go and Rust age as independent decryptors), UniFFI, SQLite, a signed-update mechanism (B7/D5 choose; tauri-plugin-updater if ADR-0003 picks Tauri), and A6's homelab engine. **Do not fork** Ente or Immich mobile. Both are AGPL and built on a key model Reliquary would remove (devices decrypt). This holds whatever stack ADR-0003 chooses. **rustic_core** cannot run on devices because the restic format is symmetric. It is an A6 homelab candidate with 0.x churn. **No device S3 SDK:** devices use presigned URLs. **Bugsink:** PolyForm Shield 1.0.0 (source-available); G3 decides. | Medium |
| 3 | Effort per component? | 1,260–2,520 focused hours before contingency (§4), including rows the skeptics found missing: onboarding and enrollment, update signing, the restore pipeline, the security suite, and monitoring. This is an estimate, **contested** (K10), and not calibrated: no measured hours-per-unit rate exists in this repo yet. | Low |
| 4 | Yearly maintenance of a fork vs own code? | **Measured churn (F1-S1):** Immich made 38 stable releases in 12 months, with two majors in 24 months. Ente Photos made 33 stable releases in 12 months, and the Ente monorepo had 17,597 commits. **Mandatory platform bump (K12, verified):** Play target API 36 from 31 Aug 2026, with an extension to 1 Nov 2026 available. The Apple iOS 26 SDK rule costs nothing while iOS is deferred. **Hours:** 60–120 h/year for own code and 150–300 h/year for a fork are estimates and are **contested** (K13). They are not used as sole support. Either figure exceeds BUD-SUPPORT as written. This is reported as a breach (§4.4), not reinterpreted. | Medium for the facts; Low for the hours |
| 5 | *(new)* What ships in 6, 12 and 24 months at the owner's hours? | At 8 h/week the walking skeleton takes about 7.5–15 months, concierge USB/CLI seeding about 18–35 months, and desktop plus minimal Android about 35–70 months, all before contingency. At 16 h/week, halve these. The earlier "6/12/24 months" table only worked if every component landed at its low estimate, and is withdrawn. | Low |
| 6 | *(new)* Do the decision weights change the answer? | No. The settled requirements, used as pass/fail knockouts, decide build versus adopt. The weights only order choices inside the build. Under illustrative scores, build, do-nothing and Immich are nearly tied, and build drops below both if its own unproven integrity is scored 3 instead of 4 (§5). This shows that the weights must not be used to decide what the knockouts already decide. | Medium |

## Method

- **Sweep:** four scouts ran: docs, source, issues and forums, and pricing/policy/standards. An analyst then did a deep read of the load-bearing primary sources on 2026-09-29.
- **Spike F1-S1 (CT, run):** behaviour probes of restic, Kopia and Plakar on SYN data; pinned-commit source checks; tokei counts; git-tag churn. See [Spikes](#spikes).
- **Skeptic review:** three lenses (sources, logic, adversary) reviewed 17 key claims K1–K17. Verdicts are from the computed tally.
- **Synthesis additions (2026-10-06):** in response to the skeptics' "missed alternatives", the synthesiser read primary sources for **Duplicacy** and **bupstash** (S47–S51). It split the restic and Kopia rows into server and direct-to-R2 configurations, and folded the F1-S1 probe results into the matrix. These additions have **not** been skeptic-reviewed.
- **Routes used:** `raw.githubusercontent.com` (vendor docs, code and GitHub wikis), the crates.io API, developer.android.com and developer.apple.com, and pinned clones in F1-S1.
- **Blocked sources:** listed under Sources. All are reported to H1; none was silently replaced. The WebSearch budget ran out during the analyst pass, which is why Synology Photos and PhotoSync are gaps.
- **Stop rule:** stopped when every knockout cell of the researched self-hostable systems rested on a primary source, or was marked snippet-only or "?".
- **Estimates:** every hour figure is analyst judgement by analogy, labelled as such. The tokei counts serve as size anchors only. No measured hours-per-line or hours-per-feature rate exists, so none is assumed.

## Sources

| # | Source (title and URL or mirror path) | Publisher | Published or version date | Accessed | Primary? |
|---|---|---|---|---|---|
| S1 | Ente architecture: `ente-io/ente @ main : architecture/README.md` (l.23–60, 114–120; recovery key l.192–214) | Ente | main | 2026-09-29; re-read by skeptics 2026-10-06 | Yes |
| S2 | Ente self-hosting, object storage: `ente-io/ente @ main : docs/docs/self-hosting/administration/object-storage.md` (l.26–31) | Ente | main | 2026-09-29 | Yes |
| S3 | Museum README: `ente-io/ente @ main : server/README.md` | Ente | main | 2026-09-29 | Yes |
| S4 | Museum FileController: `ente/ente @ 7a5993c : server/pkg/controller/file.go:347,392` (pinned in F1-S1). On `main` (2026-10-06) GetUploadURLs is l.328–347 and Trash l.579–603 | Ente | 7a5993c | 2026-09-29 / 2026-10-06 | Yes (code) |
| S5 | Museum routes and config: `ente/ente @ 7a5993c : server/cmd/museum/main.go:638,654,655,775` (trash, delete, empty-trash routes); `server/configurations/local.yaml` (db l.119) | Ente | 7a5993c | 2026-09-29 | Yes (code) |
| S6 | Ente duplicate detection: `ente-io/ente @ main : docs/docs/photos/features/backup-and-sync/duplicate-detection.md` | Ente | main | 2026-09-29 | Yes |
| S7 | Ente hidden endpoint setting: `ente/ente @ 7a5993c : mobile/apps/photos/lib/ui/settings/developer_settings_tap_area.dart:25`; `endpoint_config.dart:11-13` | Ente | 7a5993c | 2026-09-29 | Yes (code) |
| S8 | Ente LICENSE (AGPL-3.0) | Ente | HEAD | 2026-10-06 (skeptics) | Yes |
| S9 | Kopia Repository Server docs: `kopia/kopia @ master : site/content/docs/Repository Server/_index.md` (default ACLs l.138–147) | Kopia | master | 2026-09-29 | Yes |
| S10 | Kopia gRPC: `kopia/kopia @ 87d15de : internal/grpcapi/repository_server.proto:53,91-95`; `internal/server/grpc_session.go:283,296` | Kopia | 87d15de | 2026-09-29 | Yes (code) |
| S11 | Kopia Encryption docs: `kopia/kopia @ master : site/content/docs/Advanced/Encryption/_index.md` (l.103–105) | Kopia | master | 2026-09-29 | Yes |
| S12 | Kopia Ransomware Protection docs | Kopia | master | 2026-09-29 | Yes |
| S13 | restic design: `restic/restic @ master : doc/design.rst` | restic | master | 2026-09-29 | Yes |
| S14 | rest-server README (`--listen` default `:8000`; append-only l.84) | restic | master | 2026-09-29 | Yes |
| S15 | restic README (platforms) | restic | master | 2026-09-29 | Yes |
| S16 | Borg changelog: `borgbackup/borg @ master : docs/changes.rst` | Borg | 2026-09-27 | 2026-09-29 | Yes |
| S17 | Borg 1.4 append-only notes: `borgbackup/borg @ 1.4-maint : docs/usage/notes.rst` | Borg | 1.4-maint | 2026-09-29 | Yes |
| S18 | R2 S3 API compatibility: `cloudflare/cloudflare-docs @ production : src/content/docs/r2/api/s3/api.mdx` (l.58, 92, 116, 139) | Cloudflare | production | 2026-09-29; 2026-10-06 | Yes (mirror) |
| S19 | R2 bucket locks: `cloudflare/cloudflare-docs @ production : src/content/docs/r2/buckets/bucket-locks.mdx` | Cloudflare | production | 2026-09-29; 2026-10-06 | Yes (mirror) |
| S20 | Immich asset table: `immich-app/immich @ 6cd746a : server/src/schema/tables/asset.table.ts:34,39,90` | Immich | 6cd746a | 2026-09-29 | Yes (code) |
| S21 | Immich Upgrading: `immich-app/immich @ main : docs/docs/install/upgrading.md` (l.31–35) | Immich | main | 2026-09-29 | Yes |
| S22 | Immich README (3-2-1 warning l.46) | Immich | main | 2026-09-29 | Yes |
| S23 | Immich FAQ (duplicates per library) l.250–252; `asset.controller.ts:80-90` (`DELETE /assets`) @ 6cd746a | Immich | main / 6cd746a | 2026-09-29 | Yes |
| S24 | Syncthing untrusted devices: `syncthing/docs @ main : users/untrusted.rst`; `syncthing/syncthing @ b223f72 : lib/protocol/encryption.go:562` | Syncthing | main / b223f72 | 2026-09-29 | Yes |
| S25 | syncthing-android README ("Discontinued") | Syncthing | notice refers to the Dec 2024 release | 2026-09-29; 2026-10-06 | Yes |
| S26 | Duplicati GPG module: `duplicati/duplicati @ 25734de : Duplicati/Library/Encryption/GPGEncryption.cs:87,178` | Duplicati Inc. | 25734de | 2026-09-29 | Yes (code) |
| S27 | Plakar README; Kloset `encryption/symmetric.go:22` @ 5e81a8d; `plakar help server` (v1.1.7) | Plakar Korp | v1.1.7 | 2026-09-29 | Yes |
| S28 | Nextcloud E2EE app README | Nextcloud | master | 2026-09-29 | Yes |
| S29 | Nextcloud Memories README | pulsejet | master | 2026-09-29 | Yes |
| S30 | UrBackup: `uroni/urbackup_backend @ dev : urbackupclient/InternetClient.cpp` (l.330–348, 424); `@ a4eb72a : urbackupserver/dllmain.cpp:889,909` (listens on 55415) | UrBackup | dev / a4eb72a | 2026-09-29 | Yes (code) |
| S31 | Google Play target API level requirement: https://developer.android.com/google/play/requirements/target-sdk | Google | Last updated 2026-10-01 (was 2026-09-16 at first read) | 2026-09-29; 2026-10-06 | Yes |
| S32 | Apple "Upcoming SDK minimum requirements": https://developer.apple.com/news/?id=ueeok6yw | Apple | 2026-02-03 | 2026-09-29; 2026-10-06 | Yes |
| S33 | Licences from each repo's LICENSE/COPYING at HEAD: Immich, UrBackup backend, Memories (AGPL-3.0); Nextcloud Android (GPLv2 for pre-2016 code, AGPL-3.0-or-later since 16 June 2016, per its README and REUSE.toml); Kopia (Apache-2.0); restic and rest-server (BSD-2); rustic_core (MIT OR Apache-2.0); Borg (BSD-style); Syncthing (MPL-2.0); Plakar (ISC); Duplicati (MIT with a `proprietary/` carve-out); Spacedrive (FSL-1.1-ALv2); Bugsink (PolyForm Shield 1.0.0) | respective projects | HEAD | 2026-09-29; 2026-10-06 | Yes |
| S34 | Go module proxy versions: kopia v0.23.1 (2026-06-15); restic v0.19.1 (2026-07-05); plakar v1.1.7 (2026-09-24) | proxy.golang.org | as listed | 2026-09-29 | Yes |
| S35 | crates.io API: rustic_core 0.10.0 (2026-02-11), 0.10.1 (2026-03-04), 0.11.0 (2026-04-05), 0.12.0 (2026-06-01), 0.13.0 (2026-08-16) | crates.io | as listed | 2026-09-29; 2026-10-06 | Yes |
| S36 | GitHub repository metadata (stars, open issues, archived flag) via GitHub MCP search and web UI; rustic_core 89 stars | GitHub | 2026-09-29; 2026-10-06 | 2026-10-06 | Yes (metadata) |
| S37 | Immich issues #21022, #21921, #22850, #9129 (mobile upload); #29445, #29453 (v3.0.0 upgrade); #31485 (reported data loss) | GitHub | 2024-04 … 2026-09 | 2026-09-29 | No (user reports) |
| S38 | restic issues #187 (asymmetric backups, open since 2015); #5041 (host-compromise model, created 2024-09-02; not re-verified); #22057 (forged `--time` defeats append-only retention, user report, opened 2026-09-08, open) | GitHub | as listed | 2026-09-29; #22057 2026-10-06 | No |
| S39 | Kopia issues #5199, #5108 | GitHub | — | 2026-09-29 (snippets) | No |
| S40 | Cure53 audits of Ente (2023; Oct 2025) | Ente / Cure53 | 2023-03; 2025-10 | snippets only (ente.com and ente.io blocked) | Primary, read as snippet only |
| S41 | Backblaze Help: external drives; version history (30-day default; 1-year or forever options) | Backblaze | — | snippets only (site blocked) | Primary, read as snippet only |
| S42 | PhotoSync support pages | PhotoSync | — | snippets only (site blocked) | Primary, read as snippet only |
| S43 | Vendor exits: CrashPlan for Home (2017/2018), Amazon Drive (2022/2023) | press; Amazon | 2017–2022 | 2026-09-29 | No |
| S44 | Spacedrive README, LICENSE, history page (snippet) | Spacedrive | 2025–2026 | 2026-09-29 | README/LICENSE yes |
| S45 | Albrecht et al. (EuroS&P 2024, ePrint 2024/546); Hofmann & Truong (CCS 2024, ePrint 2024/1616) | IACR | 2024 | snippets | Primary, read as snippet only |
| S46 | In-repo notes: `client-stack.md` (T1), `content-encryption-format.md`, `owner-intake.md` (Q-B9), `b4-ios-decision.md`, `e2-v1-scope-metrics-pilot.md` (C14), `budgets.md` (BUD-SUPPORT) | this repo | 2026-09-29 … 2026-10-06 | 2026-10-06 | Yes (internal) |
| S47 | Duplicacy README and LICENSE.md: `gilbertchen/duplicacy @ master : README.md` ("only cloud backup tool that allows multiple computers to back up to the same cloud storage, taking advantage of cross-computer deduplication"; storage backends incl. Amazon S3); `LICENSE.md` (free for personal use; $50/year per computer for non-trial commercial CLI use; derivative works under the same terms) | Acrosync | master | 2026-10-06 | Yes |
| S48 | Duplicacy code: `gilbertchen/duplicacy @ master : src/duplicacy_config.go` (l.70–73: chunk hash = HMAC-SHA256(hashKey, plaintext), chunk file name = HMAC-SHA256(idKey, chunk hash); RSA public key in config; config keys protected by a storage password, l.403–446); `src/duplicacy_chunk.go` (l.256–258: RSA only for non-metadata chunks; l.289 `rsa.EncryptOAEP` of a random per-chunk key; l.635–638 private key needed to decrypt) | Acrosync | master | 2026-10-06 | Yes (code) |
| S49 | Duplicacy wiki "RSA encryption": `raw.githubusercontent.com/wiki/gilbertchen/duplicacy/RSA-encryption.md` ("only file contents are encrypted by the RSA encryption. File metadata … not protected by the RSA encryption (but still protected by the storage password)"; "You can run the check and prune commands without the RSA private key") | Acrosync | wiki HEAD | 2026-10-06 | Yes |
| S50 | bupstash: `andrewchambers/bupstash @ master : README.md` ("Offline decryption keys"; "Secure remote access controls"; "beta software … REDUNDANT backups"); `doc/technical_overview.md` (keyed blake3 chunk addresses; per-session ephemeral keypairs addressed to the decryption key; sub-keys divide decryption capabilities; metadata encrypted; server-side GC); `doc/man/bupstash-serve.1.md` (`--allow-put`, `--allow-get`, `--allow-remove`, `--allow-gc`, enforced via ssh `authorized_keys`); `LICENSE` (MIT); `Cargo.toml` version 0.12.1 | A. Chambers | master | 2026-10-06 | Yes |
| S51 | crates.io API, bupstash: latest published 0.12.0 (2022-11-07); 0.11.1 (2022-09-07) | crates.io | as listed | 2026-10-06 | Yes |
| S52 | F1-S1 evidence: `spikes/F1-S1/evidence/{probe_restic.txt, probe_kopia.txt, probe_plakar.txt, source-checks.md, loc.csv, cadence.csv}` | this repo | run 2026-09-29 | 2026-10-06 | Yes (measured) |

**Blocked or snippet-only (reported to H1):** gnu.org (AGPLv3 §13 text); fsf.org (App Store GPL enforcement); the immich.app blog; ente.com and ente.io (Cure53 reports); backblaze.com (so the Backblaze price is **not verified**); photosync-app.com; the urbackup.org manual (worked around with source code, S30); eprint.iacr.org; ndsa.org; forum.syncthing.net; news.ycombinator.com and reddit.com; api.github.com from the shell. The WebSearch budget ran out (200/200) during the analyst pass.

## Claims

### Key claims (three-skeptic tally, computed)

"Upheld" means the skeptic did not refute the claim. Verdicts are exactly as computed: verified = a primary source, and at least 2 of 3 skeptics did not refute; secondary-only = no primary source; contested = otherwise. Where a skeptic upheld a claim but corrected its wording, the correction is applied in Findings and noted here.

| # | Claim | Sources | Skeptic 1 (sources) | Skeptic 2 (logic) | Skeptic 3 (adversary) | Verdict |
|---|---|---|---|---|---|---|
| K1 | None of the 13 existing candidates (Ente, Immich, Nextcloud+Memories, PhotoSync, restic+rest-server, Kopia, Syncthing untrusted, UrBackup, Duplicati, Plakar, Borg, do-nothing; Synology unresearched) meets the four trust-model knockouts as shipped; each fails at least two. | Matrix (K2–K9) | Refuted: Synology is all "?"; do-nothing fails only one; R-12 cells score different configurations; Duplicacy missing | Refuted: same, plus Duplicati could be P/P/N/Y with a bucket lock; restic/Kopia direct-to-R2 not scored | Refuted: same, plus snippet cells; F1-S1 not reconciled | **Contested.** Re-scoped in §1 as "no researched system meets all four as shipped", backed by the verified per-candidate claims, not by K1 |
| K2 | Ente keeps a per-user masterKey on the device ("only you have access to your masterKey"). Every signed-in device can decrypt and the operator cannot. No admin escrow (conflicts with R-20/R-22). | S1 | Upheld; wording fix: the masterKey is random and *wrapped* by a password-derived key, not derived from the password | Upheld | Upheld | **Verified** |
| K3 | Ente museum issues presigned URLs for random `<userID>/<uuid>` keys and has user trash/delete routes. Clients call museum directly and museum needs Postgres, so it must be reachable inbound or run as a cloud server outside ADR-0001's Workers/D1 shape. | S2, S4, S5 | Upheld; line numbers drifted (pin commit); Trash is a soft delete, with hard delete via `/trash/delete` and `/trash/empty` | Upheld | Upheld; say explicitly that Tunnel is excluded by R-12 | **Verified** |
| K4 | In Kopia repository-server mode the client sends plaintext over TLS and the listening server encrypts it. Default ACLs grant FULL on the user's own snapshots. | S9, S10, S52 | Upheld; R-18 reachable with a custom APPEND ACL | Upheld; same nuance | Upheld; add cross-user read by object ID (F1-S1) | **Verified** |
| K5 | restic, Kopia, Plakar/Kloset, Borg and Syncthing untrusted mode use symmetric, password-derived keys, so any device that can write can also decrypt (fails R-20). | S11, S13, S24, S27 | Upheld; no Borg source cited; Kopia server mode: device holds no key but reads through the server | Upheld; "whole engine family" overreaches (Duplicacy, bupstash); Plakar exit 77 is a TTY failure | Upheld; restate as "every writer can obtain plaintext" | **Verified** (as restated: every writer can obtain plaintext; Borg cell secondary) |
| K6 | The R2 S3 API does not support S3 Object Lock; R2 has prefix bucket locks configured out of band, so Kopia/restic object-lock protection does not work on R2 through the S3 API. | S18, S19 | Upheld | Upheld; but the inference "blocks compose-on-R2" does not follow: admin-set bucket locks are where append-only belongs; the obstacles are engine lock and index deletes and the staging lifecycle (C1-S1) | Upheld | **Verified** (inference narrowed in §1) |
| K7 | restic rest-server `--append-only` needs a listening server (default :8000). Retention protection against a compromised client is an open issue (#5041, #22057). | S14, S38, S52 | Upheld; #22057 is a user report, not primary | Upheld; #5041 not re-verified; direct-to-R2 path not scored | Upheld | **Verified** |
| K8 | UrBackup internet-mode clients dial the configured server host and port, so the server must accept inbound connections. | S30 | Upheld | Upheld | Upheld | **Verified** |
| K9 | Immich dedups by SHA-1 with a unique index on `(ownerId, checksum)`, has no client-side encryption, tells users to keep a 3-2-1 backup, and ships breaking majors (v2 Oct 2025, v3 2026). | S20–S23, S52 | Upheld | Upheld | Upheld | **Verified** |
| K10 | Effort model: v1 needs about 1,070–2,140 focused hours, 2.6–5.1 years at 8 h/week; 24 months delivers skeleton, USB/CLI seeding, desktop tray and minimal Android. | Analyst estimate | Refuted: phasing needs every low estimate; no onboarding line; no contingency | Refuted: low-end sum of the 24-month scope ≈ 990 h > 832 h; Gate C items uncosted | Refuted: inconsistent and incomplete; F1-S1 tokei unused | **Contested.** Revised in §4; still an estimate, never sole support |
| K11 | Fork patch sizes: Ente ≥ 60–80 % of the build, compose ≥ 70 %, both above the 30 % threshold (≈ 480 h). | Analyst judgement | Refuted: no measured basis; Duplicacy weakens the "format fork" driver | Refuted: rule is predetermined, because shared Reliquary-only work alone ≈ 30 % | Refuted: near-tautological; F1-S1 slices unused | **Contested.** Percentages withdrawn; replaced by the delta test in §2 |
| K12 | Google Play requires target API 36 from 31 Aug 2026; Apple requires the iOS 26 SDK from 28 Apr 2026. | S31, S32 | Upheld; page now "Last updated 2026-10-01"; extension to 1 Nov 2026 | Upheld; the Apple bump costs nothing while iOS is deferred | Upheld; same | **Verified** |
| K13 | Estimated yearly upkeep: 60–120 h for own code vs 150–300 h for an AGPL Ente or Immich fork. | Analyst estimate | Refuted: no derivation; churn data unused | Refuted: and the build path breaches BUD-SUPPORT, which the note reinterpreted away | Refuted: own-code figure looks low | **Contested.** Kept as an estimate beside measured churn; BUD-SUPPORT breach reported (§4.4) |
| K14 | Forking Ente, Immich, Nextcloud or UrBackup code makes that component AGPL-3.0; App Store compatibility unverified. | S8, S33 | Upheld; Nextcloud Android is GPL-2.0-only + AGPL-3.0-or-later mixed | Upheld; same | Upheld; UrBackup client licence not checked | **Verified** |
| K15 | Under weights 35/20/20/15/10 with illustrative scores, build (3.20), do-nothing (3.15) and Immich (3.10) are nearly tied before knockouts; the settled requirements decide. | Note §5 | Upheld (arithmetic) | Upheld; scores are priors; integrity partly double-counts knockouts | Upheld; build's integrity 4 is unearned | **Secondary only** (illustrative judgement) |
| K16 | rustic_core is 0.x, with four minor releases between 2026-02-11 and 2026-08-16, and 89 stars on 2026-09-29. | S35, S36 | Upheld; stars come from GitHub, not crates.io | Upheld | Upheld; same attribution fix | **Verified** |
| K17 | The official syncthing-android app is discontinued (last release with the Dec 2024 Syncthing), citing Play publishing difficulty; Syncthing untrusted mode is "beta / testing only". | S24, S25 | Upheld; the README also cites "no active maintenance" | Upheld | Upheld; both reasons must be quoted | **Verified** (both reasons now quoted) |

### Synthesis claims (primary-sourced, not skeptic-reviewed)

| # | Claim | Sources | Verdict |
|---|---|---|---|
| N1 | Duplicacy with RSA encrypts each file-content chunk with a random key that is wrapped by RSA-OAEP to a public key, so a writer cannot read file contents without the private key. **Metadata chunks (snapshot file lists) are not RSA-encrypted.** They are protected only by keys derived from the storage password, which every writer holds. Chunk names are HMAC-SHA256(idKey, HMAC-SHA256(hashKey, chunk)), which gives cross-computer dedup on plain cloud storage. `prune` runs without the private key. The licence is free for personal use, not OSI. | S47–S49 | Not reviewed (primary) |
| N2 | bupstash encrypts chunks and metadata on the client to a decryption key that need not be on the client ("offline decryption keys"). It addresses chunks by keyed blake3. `bupstash serve --allow-put` (forced through ssh `authorized_keys`) can deny remove and GC to a client. The repository is reached over ssh, so its host must accept inbound connections. It is "beta software", MIT-licensed, and its last crates.io release is 0.12.0 (2022-11-07). | S50, S51 | Not reviewed (primary) |
| N3 | F1-S1 probes: a restic device printed the master key, wrote snapshots with forged `--time`/`--host`, and could `key add`. A Kopia server user read another user's file bytes by object ID; an APPEND snapshot ACL blocked deletes only after a server restart. Plakar `rm -apply` through a no-delete server hid the snapshot from listings while retaining the data. | S52 | Measured (SYN, local, not R2) |

### Context claims (not key; not reviewed)

| # | Claim | Sources | Note |
|---|---|---|---|
| X1 | Borg 2 has been in beta since 2.0.0b1 (2022-08-07), with b25 on 2026-09-27. It replaced append-only with `BORG_REPO_PERMISSIONS`. | S16, S52 | Primary |
| X2 | Nextcloud E2EE is opt-in per folder, cannot encrypt a sync root, needs a mnemonic shared by all devices, and requires server-side encryption to be off. | S28, S29 | Primary |
| X3 | Backblaze Personal keeps deleted versions for 30 days by default, with 1-year or forever options. | S41 | Snippet only |
| X4 | Duplicati's GPG module defaults to `--symmetric`; `--encrypt` to a recipient is possible by option (not run). | S26 | Primary |

## Findings

### 1. Requirement-fit matrix (as shipped; configuration stated per row)

Legend: **Y** meets as shipped; **P** partial or only by configuration; **N** misses; **?** unknown; **n/a** not applicable; *(snippet)* = the cell rests on a search snippet, not a read primary source. Rows marked † were added at synthesis and have not been skeptic-reviewed.

**Knockouts:** the four trust-model columns come first. Phones (R-02/R-04) is a settled requirement and a fifth knockout for any whole-system candidate.

| Candidate (configuration) | R-19/R-20/R-22 devices cannot read | R-21 opaque cross-user dedup | R-18 append-only devices | R-12 outbound-only homelab | R-02/R-04 phones | R-14 USB | R-29 discovery | R-30/31/42 health, nudges | R-26/27 keep forever | R-35/37 restore to device key | Licence | Clear trust-knockout fails | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Ente** (museum + Postgres; bucket may be R2) | N (device-held, wrapped masterKey) | N (random `<userID>/<uuid>` keys; per-user dedup) | N (trash, delete, empty-trash routes) | P (museum + Postgres on a non-Cloudflare cloud VM with an R2 bucket: outbound-only homelab, but outside ADR-0001's Workers/D1 shape) | Y | N | P | P | P | N | AGPL-3.0 | 3 | K2, K3 |
| **Immich** | N (plaintext on server) | N (per-user SHA-1) | N (`DELETE /assets`) | N | Y | N | P | P | P | N | AGPL-3.0 | 4 | K9 |
| **Nextcloud + Memories** | N | N | N | N | P | N | N | N | P | N | AGPL-3.0 / GPL-2.0-only mix | 4 | X2, K14 |
| **PhotoSync → homelab share** | ? *(snippet)* | N | N (writable share) | N (S3 targets iOS-premium, *snippet*) | P *(snippet)* | N | N | N | P | N | Proprietary | ≥ 3 | S42 |
| **restic + rest-server `--append-only`** (server mode) | N (device printed the master key) | N (per-repo; unkeyed SHA-256 blob IDs) | P (forget, DELETE, overwrite refused; forged `--time`/`--host` accepted; `key add` allowed; #22057) | N (listens :8000) | N | P | N | N | Y | N | BSD-2 | 3 | K5, K7, N3 |
| **restic direct to R2** (homelab pulls) | N | N (a shared repo dedups only by giving every device the key) | N as shipped (device S3 credentials can delete; an admin R2 bucket lock is untested against restic's lock and index deletes) | Y | N | P | N | N | P | N | BSD-2 | 3 | K5, K6 |
| **Kopia repository server** | N (server sees plaintext and decrypts for readers; user 2 read user 1's bytes by object ID) | P (keyed IDs, cross-user dedup; HMAC secret on every client) | P (default FULL allowed delete; custom APPEND ACL + restart blocked it) | N (server listens) | N | P | N | N | P | N | Apache-2.0 | 2 | K4, N3 |
| **Kopia direct to R2** (homelab pulls) | N (every device holds the repository password) | P (keyed IDs opaque to R2; key and HMAC secret on every device) | N as shipped (S3 Object Lock unsupported on R2; bucket lock untested against maintenance deletes) | Y | N | P | N | N | P | N | Apache-2.0 | 2 | K5, K6 |
| **Syncthing untrusted devices** | N (trusted devices share the folder password; scrypt(password, folderID)) | N | N (sync semantics) | N (P2P, relays) | P (community fork only; official app discontinued) | N | N | N | N | N | MPL-2.0 | 4 | K5, K17 |
| **UrBackup internet mode** | N *(snippet: transport encryption only)* | P (server-side, not opaque) | ? | N (server listens on 55415) | N | N | N | P | P | N | AGPL-3.0 (backend) | ≥ 1 primary (R-12) + 1 snippet | K8 |
| **Duplicati** (GPG `--encrypt` to a recipient, direct to R2) | P (by option; untested) | N (per job) | P (only through an admin R2 bucket lock; compaction needs deletes; untested) | Y | N | P | N | P | P | N | MIT + `proprietary/` | 1 (R-21) + 2 untested P | X4, K6 |
| **Plakar** (`plakar server`, delete off) | N (symmetric passphrase) | N | P (data physically retained, but `rm -apply` hides the snapshot from the device's listing) | N (server listens); P writing to S3 | N | P (`.ptar`) | N | N | P | N | ISC | 2–3 | K5, N3 |
| **Borg** (1.4, or 2.x beta) | N (symmetric; Borg key-model source not re-read: secondary) | N (keyed IDs per repo) | P (1.4 segment-level append-only; 2.x `no-delete` beta) | N (SSH server listens) | N | P | N | N | P | N | BSD-style | 3 | X1, S17 |
| **Duplicacy (RSA)** † (direct to S3-compatible storage; R2 untested) | P (content RSA-wrapped; **metadata chunks readable by every writer**) | Y (HMAC chunk names, cross-computer dedup; keys on every writer) | N (writers hold storage credentials; `prune` needs no private key) | Y (no server; homelab could pull) | N | P (local-disk backend) | N | N | P | N | Acrosync licence (free personal use; not OSI) | 1 (R-18) + 1 P | N1 |
| **bupstash** † (repository over ssh) | Y/P (offline decryption key; put-only use untested) | P (keyed blake3; dedup across devices that share the key's hash secret) | Y by config (`--allow-put` via ssh `authorized_keys`) | N (ssh-reachable host; P if on a cloud VM outside ADR-0001's shape) | N | P | N | N | P | N | MIT; beta; last release 2022-11-07 | 1 (R-12) | N2 |
| **Do nothing** (baseline: Backblaze Personal + phone clouds) | N (vendor-held) *(snippet)* | n/a | P (vendor controls) | n/a (no homelab: fails R-45) | Y | N | Y | P | N (30-day default) *(snippet)* | N | Proprietary | Baseline, not a candidate | X3, S43 |
| **Synology Photos** | ? | ? | ? | ? (needs DSM, not plain Proxmox) | ? | ? | ? | ? | ? | ? | Proprietary | Gap | none |
| **Build Reliquary** (reference) | Y by design (ADR-0001 §2), **unproven until A0, D4 and review** | Y by design | Y by design (A3/C1/D4 to prove) | Y by design | Y (Android v1) | Y | Build | Build | Build | Build | OD-15 | 0 by design | ADR-0001 |

**Reading the matrix.**
- **No researched system passes all four trust knockouts, and none that comes close has a phone client.** The nearest engines each miss one knockout clearly:
  - Duplicacy RSA misses R-18, and its metadata readability is a partial R-19/R-20/R-44 miss.
  - bupstash misses R-12.
  - Duplicati misses R-21.

  All three also miss R-02/R-04. This re-scoped statement replaces K1. It rests on primary per-candidate evidence (K2–K9, N1, N2). The † rows are not yet reviewed.
- **Photo managers** (Ente, Immich, Nextcloud, PhotoSync) have phone clients. Their servers are reachable services with user-owned deletion, and they use per-user keys or plaintext.
- **Backup engines** have no phone clients. Most give every writer the means to read: either a symmetric key, or a server that decrypts on the writer's behalf. Two exceptions are worth borrowing from as prior art, not as products:
  - Duplicacy RSA: a public-key content key plus keyed cross-computer chunk IDs.
  - bupstash: offline decryption keys plus a put-only serve mode.
- **No candidate has discovery, per-person health or nudges** (R-29–R-31). These have to be built on every path.
- **Excluded explicitly, not overlooked:**
  - Immich or Ente fronted by Cloudflare Tunnel or Workers VPC. R-12 says the homelab is "never exposed", and traceability R-12 assigns that rejection to ADR-0010.
  - The Immich or Ente app used unmodified against a Worker shim. Plaintext would cross TLS to the shim, which fails R-19.
- **Not scored (gaps):**
  - Synology Photos.
  - Proxmox Backup Server. It belongs in A6's engine bake-off. The skeptics describe its client as holding a symmetric key, with an RSA master key for recovery; this is not verified here.
  - Tarsnap. It is AWS-hosted, so it fails "No AWS". Its write-only key split is cited by skeptics as prior art and was not read here.
  - Bareos/Bacula PKI, duplicity with GPG, Seafile, PhotoPrism, Arq.

### 2. Patch size: the delta test (replaces the contested K11 percentages)

The PLAN rule says: "adopt or fork if a candidate meets all settled requirements after a patch ≤ 30 % of the build estimate". The logic skeptic showed that, as applied, this rule cannot be passed. Some work must be built on every path, because no candidate has it:
- homelab ingest: 120–240 h;
- assistant logic: 80–160 h;
- admin CLI: 50–100 h;
- USB and packaging: 60–120 h;
- the restore pipeline: 40–80 h.

That shared work is about 350–700 h, roughly 28 % of the revised build at either end. So the percentages are withdrawn. The meaningful test is the **delta**: hours a fork or adoption saves against the component it replaces, minus the hours its trust-model patch costs, compared on the same scope.

| Alternative (top 2) | Component it would replace | Gross saving (upper bound) | What the patch must still do (size anchors from F1-S1) | Net | Rule outcome |
|---|---|---|---|---|---|
| **Fork Ente's mobile app for Android** (no museum) | Android app line, 200–400 h (§4) | ≤ 200–400 h, and only if most of the app survives | Replace the upload, sync and crypto slice: about 6.4k lines (upload 2,950 + sync 2,933 + crypto adapters 561) of about 283k lines of mobile Dart, shared packages and native glue. Remove or disable every gallery feature that assumes the device decrypts (K2), add HMAC IDs, and swap Ente's museum API for the Worker API. Carry AGPL (K14) and rebase on an upstream with 33 stable releases in 12 months (F1-S1). | Unknown. No measured rate turns 6.4k replaced lines into hours. The saving is capped by one line item, and the patch hits the part the fork exists for. | Fails on knockouts R-19/R-20 unless the crypto core is replaced. Rejected on licence and churn grounds even if the hours net positive. |
| **Hybrid compose: Duplicacy (RSA) on desktops + own phone app + Worker** | CLI 30–60 h, plus the desktop share of the core | Small. The Rust core is needed for Android anyway (UniFFI), so a desktop engine does not remove the core. It adds a second on-wire format. | Close the metadata gap (snapshot lists readable by every writer: N1, a R-19/R-44 miss). Make deletes impossible: storage credentials can prune (N1). Teach homelab ingest a second format, and accept a non-OSI licence (OD-15). | Likely negative: a second data path to verify forever. | Fails R-18 and R-19 (metadata) as shipped. Not recommended. |
| Adopt Immich (+ nightly homelab copy) | Everything | — | The whole trust model (K9) | Not patchable without replacing its server model | Fails |

**Confidence:** high that every alternative's patch hits the trust core (K2–K9 verified; N1 primary). The net hours are **unknown**, and this note does not invent them.

### 3. Components to adopt (not code to fork)

| Component | Use | Licence | Maturity | Verdict | Source |
|---|---|---|---|---|---|
| age v1 format; Go `age` and Rust `age` | Content and metadata envelope; independent decryptors | BSD-3 / MIT-Apache (per spike note) | Stable spec (C2SP) | **Adopt** (A2 owns the format decision) | S46 |
| UniFFI | Rust core → Kotlin (Swift later) | MPL-2.0 (per T1) | In production | **Adopt** if ADR-0003 keeps a shared Rust core | S46 |
| Signed self-update | Desktop updates verified against the project's offline key (settled) | — | — | **Adopt an existing updater** (tauri-plugin-updater if ADR-0003 picks Tauri; B7/D5 decide) | S46 |
| SQLite | Client hash cache and state | Public domain | Mature | **Adopt** | — |
| rustic_core | restic-format engine | MIT OR Apache-2.0 | 0.x; 4 minors 2026-02 → 2026-08 (K16); 5 breaking minors in 12 m (F1-S1) | **Not on devices** (symmetric, K5). A6 candidate at the homelab, with churn risk | K16 |
| restic / Kopia / Plakar / Borg / PBS | Homelab engine behind ingest | as S33 | as S34, X1 | **A6 decides** (ADR-0012). Symmetric keys are acceptable at the homelab, which holds the private key anyway | K5 |
| Ente and Immich mobile upload code | Patterns only: multipart resume; iOS upload extension (B4) | AGPL-3.0 | Active | **Read, do not copy** | K14 |
| Duplicacy, bupstash | Prior art for keyed chunk IDs, public-key content keys, put-only serve | Acrosync / MIT | Duplicacy active; bupstash beta, last release 2022 | **Prior art for A1/A2/A3/D2, not a dependency** | N1, N2 |
| S3 multipart client | Devices upload via Worker-issued presigned URLs | — | — | **No SDK on devices** (C1 confirms the Worker side) | ADR-0001 §4 |
| Bugsink | Crash collector (B8/C7) | PolyForm Shield 1.0.0 | — | **G3 decides** | S33 |
| Syncthing-Fork, PhotoSync, Backblaze, phone clouds | Interim stopgaps (E2-S3) | MPL / proprietary | — | **Stopgap only.** Vendor-readable, so they need an explicit accepted-risk decision (see Decision requests) | K17, X3 |

### 4. Effort model (one maintainer), revised after skeptic review

**Status: estimate, contested (K10). Not measured.** Unit: focused engineering hours. Changes from the analyst draft:
- five rows the skeptics found missing are added;
- the milestone table is derived from the component sums, as ranges;
- a contingency line is added;
- calendar time is shown at both 8 and 16 h/week.

| Component | Scope for v1 | Low (h) | High (h) | Milestone |
|---|---|---|---|---|
| Specs and vectors | A1–A4 specs, vectors | 40 | 80 | M1 |
| Rust core | hash cache, HMAC IDs, resumable age encoder, upload state machine, SQLite, bundle writer, receipt verification | 160 | 320 | ½ M1, ½ M2 |
| CLI client | Linux/Windows/macOS CLI on the core | 30 | 60 | M1 |
| Worker + D1 | API v1, device auth, presign, claim/commit, rate limits, `restore/` prefix | 100 | 200 | ½ M1, ½ M2 |
| Homelab ingest | pull, decrypt, verify, engine adapter, catalog, signed receipts, USB import | 120 | 240 | ½ M1, ½ M2 |
| Admin CLI | invites, revoke, restore, status, key-ceremony helpers | 50 | 100 | M2 |
| **Restore pipeline** *(new)* | re-encrypt to the device key, stage in the expiring prefix, device-side decrypt (R-37) | 40 | 80 | M2 |
| Tests and CI | cross-platform CI, golden corpus, fault injection | 80 | 160 | ½ M2, ½ M3 |
| Packaging and ops | USB kit build, runbooks, docs | 60 | 120 | ½ M2, ½ M3 |
| Desktop app | tray + daemon, autostart on 3 OSes, enrollment UI, health UI (stack per ADR-0003) | 150 | 300 | M3 |
| Android app | background upload, MediaStore originals, QR enrollment, health UI, Play closed track | 200 | 400 | M3 |
| **Onboarding and enrollment** *(new)* | ADR-0002: invite codes + QR, passwordless email verification and provider integration, Play enrollment token, pairing codes, "your other devices" wizard | 60 | 120 | M3 |
| **Update signing and release** *(new)* | offline-key signing, manifest, verification, release runbook (D5) | 30 | 60 | M3 |
| **Security verification** *(new)* | D4 attack suite, fuzzing, preparing for an external crypto review (the review's fee is not costed: C4/owner) | 40 | 80 | M3 |
| **Monitoring and alerting** *(new)* | crash reporting, alerts, dead-man's switch (B8/C7/C8) | 20 | 40 | M3 |
| Assistant logic | discovery rules, health model, nudges and email | 80 | 160 | ½ M3, ½ v1 |
| **Subtotal** | | **1,260** | **2,520** | |
| Contingency (+20 %, analyst assumption) | | 252 | 504 | |
| **Total with contingency** | | **1,512** | **3,024** | |

**What ships when.** The milestone split above is an analyst assumption. Hours are cumulative and before contingency. At 8 h/week the owner has ≈ 34.7 h per month.

| Milestone | Cumulative hours (low–high) | Months at 8 h/week | Months at 16 h/week | Family protection meanwhile |
|---|---|---|---|---|
| M1 walking skeleton: CLI → Worker/R2 → homelab → verified restore (Gate B) | 260–520 | 7.5–15 | 3.8–7.5 | Stopgaps per device type (E2-S3) |
| M2 concierge seeding: hardened core and ingest, admin CLI, USB, admin restore | 610–1,220 | 17.6–35.2 | 8.8–17.6 | Stopgaps for phones |
| M3 desktop tray + minimal Android + onboarding, update signing, security suite | 1,220–2,440 | 35.2–70.4 | 17.6–35.2 | Stopgaps retire device by device |
| Full assistant v1 | 1,260–2,520 (1,512–3,024 with contingency) | 36–73 (44–87) | 18–36 (22–44) | — |

The earlier "6 / 12 / 24 months" table is **withdrawn**. E2 (`e2-v1-scope-metrics-pilot.md` C14) relies on it and must re-derive its milestones (hand-off).

**Calibration.** The F1-S1 tokei counts are size anchors only:
- Immich's whole mobile client is 66k lines including native code, and its upload slice is about 8.7k.
- Ente Photos' mobile Dart alone is 225k lines.
- The Reliquary encryption spike is 2.4k lines.

No measured hours-per-line rate exists, so these cannot be turned into hours without inventing a rate. A0's actual hours at Gate B are the first real calibration point.

**Ordering trade-off (for E2).** Camera rolls are the main keepsake source (CLAUDE.md), yet M3 ships Android last. A phone-earlier variant moves a minimal media-only Android uploader (part of the 200–400 h line) ahead of the desktop tray. It does not change the totals. It is a scope and ordering choice for ADR-0004.

#### 4.4 Yearly maintenance and the BUD-SUPPORT breach

- **Measured inputs (F1-S1):**
  - Immich: 38 stable releases in 12 months; majors v2.0.0 (2025-10-01) and v3.0.0 (2026-06-30); 2,855 commits in 12 months.
  - Ente Photos: 33 stable releases in 12 months; the monorepo had 17,597 commits.
  - rustic_core: 5 breaking 0.x minors in 12 months.
  - Kopia: 5 epochs in 24 months.
- **Verified platform rule (K12):** Play target API 36 for new apps and updates from 31 Aug 2026, with an extension to 1 Nov 2026 available. This repeats yearly. The Apple iOS 26 SDK rule applies only once an iOS app exists (OD-01).
- **Estimates (K13, contested):** own code 60–120 h/year; an Ente or Immich fork 150–300 h/year. Neither is used as sole support. The case against forking rests on K2/K9 (trust model), K14 (AGPL) and the measured churn.
- **Budget breach, reported:** BUD-SUPPORT is "owner time ≤ 2 h per month at steady state" (`budgets.md`). Option A's own estimated upkeep, 5–10 h/month, **breaches it as written**, and so does every option that runs self-built or forked software. Only the do-nothing baseline plausibly fits. Whether BUD-SUPPORT was meant to cover development upkeep is H1's and the owner's call, not F1's (decision request below).

### 5. Decision weights for OD-02 (proposal)

The proposal has two stages:
1. **Knockouts.** The settled requirements (R-12, R-18, R-19–R-22, R-26, R-02/R-04) are pass/fail.
2. **Weights** apply only among options that pass the knockouts. In practice that means among build variants: component adoption, phasing, platform order, and A6's engine.

| Criterion | Proposed weight | Alternative A (effort-heavy) | Alternative B (UX-heavy) |
|---|---|---|---|
| Integrity (verifiable, restorable, no silent loss) | **35 %** | 30 % | 30 % |
| Maintenance (one person, yearly bumps, bus factor, licence duties) | **20 %** | 20 % | 15 % |
| Effort to v1 | **20 %** | 30 % | 15 % |
| Family UX (non-technical, near-zero enrollment, plain status) | **15 %** | 10 % | 30 % |
| Cost (cloud and one-off) | **10 %** | 10 % | 10 % |

**Illustrative scores** (1–5, analyst priors, *before* knockouts; K15, secondary only):

| Option | Integrity | Maint. | Effort | UX | Cost | Weighted (proposed) | Knockouts |
|---|---|---|---|---|---|---|---|
| Build + adopt components | 4 | 3 | 1 | 4 | 4 | 3.20 | Pass by design (unproven) |
| Build, with integrity scored 3 (unproven new crypto and state machine) | 3 | 3 | 1 | 4 | 4 | 2.85 | Same |
| Fork Ente | 3 | 1 | 2 | 4 | 3 | 2.55 | Fails |
| Compose restic/Kopia + PhotoSync | 2 | 3 | 4 | 1 | 4 | 2.65 | Fails |
| Adopt Immich | 2 | 3 | 4 | 4 | 4 | 3.10 | Fails |
| Do nothing (baseline) | 2 | 4 | 5 | 3 | 2 | 3.15 | Fails |

**Finding.** Weights alone do not separate build from do-nothing or Immich. With build's integrity scored at 3, which is defensible until A0, D4 and an external review pass, build ranks below both. The integrity criterion also partly double-counts what the knockouts encode. So the weights must **not** decide build versus adopt. The settled requirements do. Use the weights to order work inside the build. **Build's own implementation risk** is real: a novel crypto, dedup and append-only system written by one maintainer. Its mitigation (A0, the D4 attack suite, G2 vectors, and an external review whose fee is not yet costed) belongs in the plan, not in a higher score.

### Similar work and lessons

| Project | What happened | Borrow or avoid | Source |
|---|---|---|---|
| Ente | Audited E2EE photo backup. Per-user wrapped keys; museum mediates everything; self-hosting via a hidden 7-tap setting | Borrow: presigned direct upload with server-side verify; key-wrapping discipline. Avoid: device-held master key; hidden self-host settings | K2, K3, S7 |
| Immich | Very active; majors v2 (2025-10-01) and v3 (2026-06-30); 38 stable releases in 12 months; mobile background-upload issue clusters | Borrow: backup counts on screen; iOS upload-extension approach (B4). Avoid: forking a fast upstream; gallery-as-backup | K9, S37, S52 |
| Kopia | Sends the content-ID HMAC secret to every client (source-check S3); cross-user read by object ID (F1-S1) | Same exposure class as Reliquary's family secret on every device: a stolen device enables confirmation-of-file attacks (hand-off F3/D2) | K4, N3 |
| Duplicacy | RSA content keys; keyed chunk names; lock-free cross-computer dedup on dumb storage; metadata left under the shared password | Borrow: keyed-name construction and lock-free dedup as prior art. Avoid: unprotected metadata; writer-side prune | N1 |
| bupstash | Offline decryption keys; put-only serve permissions | Prior art for "devices can append but not read or delete" (A3/D2/D4) | N2 |
| Spacedrive | Rust core + Tauri + mobile; paused, rewritten; licence now FSL | Avoid broad scope before a narrow core works | S44 |
| Syncthing Android | Discontinued, citing Play publishing difficulty **and** no active maintenance | Budget for Play compliance as recurring work (B3) | K17 |
| Borg 2 | Beta for 4+ years | Freeze formats early (Gate A) | X1 |
| CrashPlan for Home, Amazon Drive | Consumer vendors exited | The do-nothing baseline carries vendor-exit risk | S43 |
| restic append-only | Forged `--time` defeats retention (#22057, user report; reproduced in F1-S1) | Reliquary's "no device deletes; pruning manual only" (R-28) avoids the class; A3/D4 must test it, including forged timestamps | K7, N3 |
| R2 | No S3 Object Lock; prefix bucket locks exist, admin-set | C1/D4: consider a bucket lock on committed or restore prefixes as a backstop; check against the staging lifecycle | K6 |

## Spikes

| Spike | Hypothesis | Pass → / fail → (decision) | Exec tag | Budget IDs | Data class | Status | Result |
|---|---|---|---|---|---|---|---|
| F1-S1 Fit matrix for ≥ 8 candidates, plus behaviour probes, tokei and churn | No candidate meets all settled requirements after a patch ≤ 30 % of the build, so build and adopt components | Pass → build + adopt (ADR-0005); fail (a candidate fits) → adopt or fork it | CT (ran for real; local only, **not R2**) | BUD-SUPPORT (maintenance context) | `PUB → results`, `SYN → results` | **Ran; inconclusive as a pass/fail** (the pass criterion belongs to the matrix; all measurement inputs are complete) | Probes: restic, Kopia, Plakar (N3, summarised in §1). Source checks: 16 rows at pinned commits. tokei and churn: §2, §4. Did not run: Ente/Immich live, Borg, Duplicati (no .NET), Syncthing, UrBackup, Synology, PhotoSync, Backblaze, anything on R2. Evidence: [`spikes/F1-S1/README.md`](../../spikes/F1-S1/README.md), `spikes/F1-S1/evidence/`. Matrix status after synthesis: every knockout cell of the researched systems is primary-backed except the snippet cells marked; the top 2 alternatives are assessed by the delta test (§2), but their net hours are **unknown** |
| F1-S2 (optional) Ente museum + Immich live check and soak (shared with F2-S1) | On real installs: a phone account can delete its own history in both; the admin can read Immich originals but not Ente objects; the same photo from two accounts is stored twice; phones need direct reach; Ente needs the 7-tap setting | Pass (all observations recorded) → mark the Ente/Immich cells "confirmed live"; a disproved hypothesis feeds back into ADR-0005. Fail or not run → cells stay "source only" | OL | BUD-SUPPORT, BUD-TTS, BUD-BAT-D | `LAB → results`; test credentials `SEC`, kept in the homelab | **Kit-ready; not run** (no owner hardware in the container) | Kit: [`docs/research/kits/F1-S2/README.md`](kits/F1-S2/README.md). It includes timed installs with VM sizing from the vendors' requirement docs, a warning that Ente's quickstart writes a `localhost:3200` bucket endpoint, LAN/VPN-only exposure, the fit probes, an optional 7-day soak and one timed upgrade |

**Corrections to the F1-S1 README's interpretation**, recorded here because this stage does not edit the spike folder:
- Plakar's "backup without the passphrase fails" result (exit 77, "inappropriate ioctl for device") is a TTY prompt failure, not proof of a cryptographic requirement. That writers need the key follows from the symmetric design (source check S13).
- In Kopia server mode, the device "can read" because the server decrypts for it; it does not hold the key.

## Conflicts with settled text

None outright. Four watch items:
1. **Stopgaps are vendor-readable.** Backblaze Personal and phone-vendor clouds (E2-S3) put keepsakes where a provider can read them. That cuts against "privacy against outsiders, including the cloud provider". They are interim and outside Reliquary's data path, so they need an explicit, time-limited owner decision (OD-17 accepted-risk register), not an implied default.
2. **BUD-SUPPORT** (a proposed budget, not settled text) is breached by option A's estimated upkeep (§4.4).
3. **ADR-0003 is not pre-decided.** ADR-0005 names client apps "per ADR-0003". The case against forking rests on the trust model and AGPL, not on Flutter.
4. **No fallback that relaxes the trust model is adopted here.** If the owner's hours are far below 8 h/week, the honest choice is between relaxing a settled requirement and accepting a much longer timeline. Only the owner can make it (decision request below). F1 does not decide it.

## Open questions

| Question | Who | By when |
|---|---|---|
| The owner's real weekly build hours (Q-B9), the dominant variable | H2 / owner | Wave 1 exit |
| Calibrate the effort model with A0 actual hours | A0 | Gate B |
| Skeptic review of the † rows (Duplicacy, bupstash) and the split restic/Kopia rows | Wave 2 review | Wave 2 |
| Synology Photos (not researched; it needs DSM, which conflicts with R-10 on its face) | F2 or F1 follow-up | Wave 2, low priority |
| PhotoSync encryption key model (snippet only) | F2 | Wave 2 |
| Can an R2 API token write without delete rights? Do R2 bucket locks fit the staging lifecycle? Do they hold against restic, Kopia or Duplicati lock and index deletes? | C1 (C1-S1) | Wave 1 |
| AGPL §13 text and App Store compatibility (gnu.org and fsf.org blocked); UrBackup client licence | G3 | Before adopting code |
| Ente Cure53 Oct 2025 outcome (conflicting snippets) | F3 | Wave 1 |
| Fee for an external crypto/design review | C4 / owner | Gate C |
| Does Duplicacy's lock-free fossil collection survive an R2 bucket lock? (Only matters if Duplicacy is reconsidered) | — | — |

## Recommendation

**Build the Reliquary-specific system:**
- the shared core;
- the Worker/D1 control plane;
- homelab ingest;
- the admin CLI;
- the restore pipeline;
- desktop and Android clients, in the stack ADR-0003 chooses (T1's working assumption is option C).

Around it, **adopt proven components**: the age format, UniFFI (if a Rust core), SQLite, an existing signed updater, and A6's homelab engine. **Do not fork** Ente, Immich, Nextcloud or UrBackup code. Read Ente, Immich, Duplicacy and bupstash for patterns and prior art only.

Why:
1. No researched system meets the four trust knockouts as shipped, and none that comes close has a phone client. This rests on verified K2–K9 plus the primary-sourced N1–N2.
2. For the top two alternatives, the patch hits the very part that makes the candidate useful, and the saving is capped at one component line (§2).
3. Forking AGPL clients binds OD-15 (K14). It would also tie one maintainer to upstreams shipping 33–38 stable releases a year (F1-S1).

**Pair the build with:**
- **phasing as ranges, not dates.** M1 skeleton, M2 concierge USB/CLI seeding, M3 desktop + minimal Android. At 8 h/week, M2 lands in about 18–35 months and M3 in about 35–70 months. These are estimates (contested, K10) for E2 to re-derive in ADR-0004.
- **stopgap protection now** (E2-S3), as an explicit accepted risk.

**What would change this:**
- a candidate gaining public-key write-only encryption, including metadata, plus service-enforced append-only, plus a phone client (watch Duplicacy, bupstash, restic #187);
- F1-S2 showing that Ente or Immich has a server-side setting that blocks device deletes (this would narrow one cell, not the trust-model gap);
- the owner choosing, through a decision request, to relax a settled requirement.

## Decision requests

### OD-02: Build, adopt or compose, and the decision weights
- **Needed by:** Wave 1 exit
- **Evidence:** this note; `docs/adr/0005-build-and-adopt-components.md` (Proposed)
- **Options:**

  | Option | What it means for the family | Cost (money and owner time) | Reversibility | Risks |
  |---|---|---|---|---|
  | A. Build + adopt components (recommended) | The trust model is met as settled. Concierge USB seeding in about 18–35 months and apps in about 35–70 months at 8 h/week (estimates, contested); halve at 16 h/week | Estimated 1,260–2,520 h before contingency; estimated 60–120 h/year upkeep (contested); **breaches BUD-SUPPORT as written**; cloud per C4 | Easy early; costly after Gate A formats | Long calendar time; one-person bus factor; unproven new crypto until A0, D4 and review |
  | B. Fork Ente (mobile ± museum) | A polished phone app sooner, but with a gutted crypto model, AGPL, and a cloud VM + Postgres if museum is kept | Net hours unknown (§2); fork upkeep estimated 150–300 h/year (contested) against 33 releases/year upstream | Costly | Upstream churn; the audit no longer covers the changed crypto |
  | C. Hybrid compose (Duplicacy RSA on desktops + own phone app + Worker) | Two backup paths; desktops faster | Saving small (§2); non-OSI licence | Moderate | Fails R-18 and R-19 (metadata) unless patched; a second format to verify forever |
  | D. Do nothing (baseline/stopgap only) | Familiar apps, vendor retention rules | Price not verified (backblaze.com blocked; see C4) | Easy | **Not an end state:** it fails R-19/R-20, R-26 and R-45. Choosing it permanently would need a change to settled requirements |

- **Weights to confirm:** integrity 35 %, maintenance 20 %, effort 20 %, family UX 15 %, cost 10 %. They apply **after** the settled requirements are used as knockouts, and only to order work inside the chosen option.
- **Recommendation:** A, with stopgaps per device type until the apps ship.
- **Touches settled text:** None for A. C and D as end states would.
- **If no decision by the deadline:** the run assumes A with the proposed weights.

### DR-F1-1 (to H1 and the owner; no OD yet): BUD-SUPPORT vs development upkeep
- **Question:** BUD-SUPPORT (≤ 2 h/month) is breached by option A's estimated upkeep (5–10 h/month). Should the owner (a) add a separate development-upkeep budget line, (b) accept the breach, or (c) cut scope until upkeep fits?
- **Recommendation:** (a). Keep BUD-SUPPORT for operational support. Add a development-upkeep line that the owner sets after Q-B9, revisited at Gate B with A0 actuals.

### DR-F1-2 (maps to OD-17, accepted-risk register): vendor-readable stopgaps
- **Question:** Accept Backblaze Personal and phone-vendor clouds as **interim** protection (E2-S3) until Reliquary apps ship, knowing that the vendor can read the data?
- **Recommendation:** Yes, as a time-limited accepted risk. Each stopgap retires when that device is protected by Reliquary.

### DR-F1-3 (to H2, not an OD): build hours (Q-B9)
- **Recommendation:** answer before the Wave 1 exit. At 8 h/week the estimated v1 takes 3.0–6.1 years before contingency. At 16 h/week it takes 1.5–3.0 years.

## Hand-offs

| To | What | Why |
|---|---|---|
| E2 | The 6/12/24-month table is withdrawn. Re-derive `e2-v1-scope-metrics-pilot.md` C14 from §4's ranges. Consider a phone-earlier ordering (a minimal media-only Android uploader before the desktop tray) | ADR-0004 scope and ordering |
| T1 | ADR-0005 is stack-neutral. A Flutter choice would not revive the Ente/Immich fork option, which is rejected on trust model and AGPL | ADR-0003 |
| A6 | Engine facts: restic/rustic_core (0.x churn), Kopia 0.23.1 (5 epochs in 24 m), Plakar 1.1.7 (logical delete via `rm`), Borg 1.4 / 2.x beta, PBS not scored here | ADR-0012 |
| A1, F3, D2 | Kopia ships its content-ID HMAC secret to every client, and Duplicacy keeps hashKey/idKey on every writer. Both are prior art for, and share the stolen-device weakness of, HMAC(family secret). Relevant to dedup-secret rotation | Attack matrix; ADR-0006/0008 |
| A2, A3, D4 | bupstash `--allow-put` and offline keys; Duplicacy's metadata-not-RSA gap (metadata must be encrypted to the homelab key too, R-19); restic forged `--time` (#22057): the D4 suite must include forged timestamps | ADR-0007/0009 |
| C1 | R2 has no S3 Object Lock; prefix bucket locks are admin-set. Check token delete granularity and the staging lifecycle | R-18 cloud side |
| G3 | AGPL on Ente, Immich, UrBackup, Memories; Nextcloud Android GPL-2.0-only + AGPL mix; Duplicacy non-OSI; Bugsink PolyForm Shield; Duplicati `proprietary/`; Spacedrive FSL | OD-15 |
| C4 | The external crypto review fee and the stopgap prices are not verified | Cost model |
| H1 | Blocked hosts; WebSearch exhausted; DR-F1-1 (budget line); `budgets.md` unchanged by F1 | `sources.md`, `budgets.md`, decision queue |
| H2 | Q-B9 is the dominant effort input | Intake |
| F2 | Synology Photos and PhotoSync gaps; Immich/Nextcloud upload issue clusters; F1-S2 kit shared with F2-S1 | Wave 2 |
