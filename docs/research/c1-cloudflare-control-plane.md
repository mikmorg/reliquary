# C1. Cloudflare control-plane mapping and API v1

- **Workstream:** C1 (see `docs/research/PLAN.md`, section "C1.")
- **Status:** Final for Wave 1. Skeptic-reviewed (three lenses: sources, logic, adversary; 2026-10-06; tally computed in code). Spike results are in. Every Cloudflare spike ran only as a local emulation (**emulated, not real R2/Cloudflare**), so the real-sandbox kits C1-S1 to C1-S4 still have to run (H5 L01, no sandbox account yet). Owner decisions DR-C1-1 to DR-C1-7 are pending.
- **Date:** 2026-09-29 (scout sweep). Last updated 2026-10-06 (synthesis). The run brief gives 2026-09-29 as "today", but the container clock and the npm registry show 2026-10-06, so re-fetch dates below are 2026-10-06.
- **Feeds:**
  - ADR-0010, Proposed: [`docs/adr/0010-control-plane-topology-and-api-v1.md`](../adr/0010-control-plane-topology-and-api-v1.md)
  - [`docs/design/api-v1.md`](../design/api-v1.md) (Draft outline; the OpenAPI document follows in Wave 2)
  - one-way door #7 (R2 key layout, Gate B) and #8 (API hostname and bootstrap, Gate C)
  - inputs to OD-04 (C1-S1 evidence), OD-14 (beta policy), OD-17 (accepted risks) and OD-20 (staging cap)
  - DR-C1-1 to DR-C1-7 (H1 to number)
- **Depends on:**
  - A3 (`a3-ingest-protocol.md`: per-upload keys, advisory lease, reconciliation, receipts)
  - D1 (`d1-threat-model.md`; register `docs/security/threat-model.md`, SR-01…SR-31)
  - B4 (`b4-ios-decision.md`: K6, P6, IOS-C10, IOS-C16, DR-B4-2)
  - the CE spike (`content-encryption-format.md`), C4 (`c4-cost-model.md`), T2 (`fact-check-adr-0001-0002.md`)
  - G2-S1 (emulator fidelity)
  - H1 sandbox (L01; not yet available)
- **Traceability rows advanced:** R-09, R-11, R-12, R-13, R-18, R-37, Q1-3 (presigned UploadPart), C-01 (warm cache)

## Summary

Recommended for the ADR-0010 draft: a **TypeScript Worker on the owner's own domain, one D1 database as the system of record (provisionally), two R2 buckets, presigned per-part URLs for content, records posted through the Worker, a Worker event feed the homelab polls, R2 listing as the path of record, and one Cron Trigger.** Durable Objects are used only where they alone fit: exact per-device counters for C2, kept in a separate Worker.

1. **D1 is a provisional choice, and its capacity is unproven.** D1 runs one query at a time per database (K1, verified). The earlier claim that one `batch()` per request keeps load low was **contested** by all three skeptics (K2). Batching saves round trips, but D1 runs a batch's statements one after another, and write time "depend[s] on the number of rows written". This note therefore no longer claims headroom. It claims three things:
   - D1 is the operationally simplest store;
   - write SQL must be set-based (one `INSERT … SELECT FROM json_each(?)` per table per request);
   - if real-D1 measurements (C1-S2/S3 kits) show too little headroom, there is a pre-agreed fallback: first several D1 databases, then sharded SQLite DOs.
   The design rule that keeps the fallback cheap is a data-access layer that hides the store.
2. **Key layout:** `rq-ingest` holds `staging/<dedup_id>/<upload_id>/s<n>` and `meta/<device_id>/<batch_id>.age`, and reserves `pack/<upload_id>/s<n>` for packed uploads (IOS-C16). It **never has an Expiration rule**. `rq-restore` holds `restore/…` with an expiry. The 7-day multipart abort probably **cannot be extended**: the lifecycle doc's own example says the earlier rule wins. The design therefore plans for a hard 7-day ceiling per multipart upload.
3. **Worker language: TypeScript.** Rust on Workers is Beta, `workers-rs` is 0.8.7, and panic recovery needs nightly (K9, verified). The opaque-artifact rule keeps the second implementation small.
4. **R2 enforcement is still unknown.** Nothing in the design depends on R2 enforcing create-only or checksums. Per-upload keys plus homelab verification are the safety basis. Miniflare disagrees with the R2 docs on the checks that matter (K14, secondary-only), so only the real-sandbox C1-S1 kit can settle them. Until H1 passes, "devices can only append" is enforced **at commit, not at staging**: a holder of a presigned URL can rewrite one not-yet-committed staged object within the URL window. DR-C1-6 asks the owner to confirm that reading.
5. **Short URLs work for the v1 platforms but are not shown for iOS.** 15-minute URLs plus an idempotent re-sign endpoint work where app code runs right before the transfer (desktop daemon, Android WorkManager). For iOS background `URLSession`, K15 is **contested**: re-sign-on-failure can loop. The API keeps every IOS-C10 option open, and the iOS policy stays DR-B4-2.
6. **New guard rails from the adversary review:**
   - a Worker-enforced **staged-bytes cap** and a presign pause when the homelab heartbeat is stale (cost backstop for a bucket that never expires);
   - a written **kill-switch and break-glass drill** before Gate B;
   - **retention rules** for the feed, idempotency and audit tables against D1's 10 GB cap.

Confidence: **high** on the Cloudflare facts (11 of 15 key claims verified against primary docs). **Medium** on the topology and language. **Low** on D1 capacity and on every R2 behaviour the real-sandbox kits have not yet run.

## Questions

| # | Question | Short answer | Confidence |
|---|---|---|---|
| 1 | D1 vs SQLite DOs vs hybrid for dedup index, claims, device registry, invites, quotas | **D1 for all records, provisionally.** Per-device counter DOs (C2's call) in a separate Worker. Fallback ladder if real D1 is too slow: (a) split into several D1 databases by function (dedup + leases vs the rest), which the D1 FAQ recommends; (b) shard dedup + leases by ID prefix into N D1 databases or 16 SQLite DOs. All behind a data-access layer. F2. | Medium-low (capacity not measured; K2 contested) |
| 2 | Is D1's single thread a ceiling during a 25-device seed? | **Unknown until measured.** With C4's 6 rows written per file and 5 ms per row-write (assumptions), one database saturates at a mean file size of about 1.9 MB at the assumed 62.5 MB/s family peak. Batching does not change that number. Set-based statements might, if D1's cost is per statement rather than per row, but nothing documents that. The C1-S2/S3 kits measure it. F2. | Low |
| 3 | How to shard DOs, if used | Counters: one DO per device (`idFromName(device_id)`), in a separate `rq-gate` Worker. Dedup and leases: only at fallback step (b), 16 shards on the first ID character. Never one global DO. | Medium |
| 4 | Key layout; one bucket or several | Two buckets (DR-C1-2). `rq-ingest`: `staging/<dedup_id>/<upload_id>/s<n>`, `meta/<device_id>/<batch_id>.age`, reserved `pack/<upload_id>/s<n>`. `rq-restore`: `restore/<device_id>/<job_id>/<object_id>`. F3. | Medium-high |
| 5 | Staging expiry vs worst outage; 7-day multipart abort | Ingest bucket: **no Expiration rule ever**; only the homelab deletes. The default 7-day abort removes only incomplete multipart uploads. Planning default: it **cannot** be lengthened (the doc example implies the earliest rule wins; K6). Uploads that might outlive 7 days must use A3's segment checkpoint, or USB. | High (docs); Medium (earliest-wins reading) |
| 6 | Which cloud state needs backup | Cloud-only, so it needs a nightly homelab-pulled export: accounts and verification state, hashed invites, enrollment tokens and pairing codes, the email suppression list, and the audit log. Rebuildable from the homelab: committed set, receipt relay, revocations, heartbeat, devices (if D3 adopts a homelab-signed list). Disposable: leases, idempotency rows, counters, feed. F6. | Medium-high |
| 7 | Notifications | **Worker event feed polled by the homelab** (about every 30 s) plus R2 listing at start and hourly as the path of record (DR-C1-3, amends the mechanism in ADR-0001 §1). Option D, a Queue push consumer that appends to the feed, keeps Queues in the picture if the owner prefers. F5. | Medium |
| 8 | Homelab authentication | To the Worker: requests signed with a homelab Ed25519 control key. To R2: Worker-minted, locally signed temporary credentials scoped by action and prefix, TTL ≤ 1 h, one per bucket. Offline break-glass token. **These are proposals handed to C2 and D3**, which own token scoping, rotation and revocation. F5. | Medium |
| 9 | Workers VPC / Tunnel push | **Rejected.** The cloud would initiate requests into the homelab (K11, verified), and it is Beta. | High |
| 10 | Worker language | **TypeScript**, under the opaque-artifact rule (DR-C1-1). F7. | Medium |
| 11 | CPU and subrequests when presigning hundreds of parts | Presigning makes no subrequests (K3, verified) and is local HMAC work. Emulated C1-S4: 200 URLs in one call, local p50 22 ms; this indicates fit, but it is not Cloudflare CPU accounting. Windows of ≤ 15 min: about 134 parts of 16 MiB at 20 Mbit/s. Always set `X-Amz-Expires` (aws4fetch defaults to 24 h). F4. | High (no subrequests); Low (CPU, emulated) |
| 12 | API conventions | `/v1/`, additive-only, with the **C1-S5 rules**: tolerant enums or version-gated enum additions; `min_version` raised in the same deploy as any breaking change; request schemas strip unknown keys. Problem details per RFC 9457 (re-read). `update_required` uses **400**, not 426, because RFC 9110 requires an `Upgrade` header on 426. F8. | Medium-high |
| 13 | API on the owner's domain | Workers Custom Domain; needs an active Cloudflare zone and no existing CNAME. `workers_dev = false`; Version, Preview **and Deployment** URLs must be handled separately (K12, verified). Clients never pin the R2 host. | High |
| 14 | Background jobs | One Cron Trigger (about every 15 min) runs idempotent "what is due" queries: stale devices, nudges, the dead-man's switch, the day-6 multipart checkpoint, D1 size alerts and table pruning. DO alarms only inside counter DOs. No Workflows in v1. F9. | Medium-high |
| 15 | Change management | **No gradual deployments in v1**: plain `wrangler deploy`. Expand/contract D1 migrations are still required, because migrations and code deploys are not atomic. DO classes go in a separate Worker, because `exports` disables `versions upload` and gradual deployments for the Worker that declares them (K10). F10. | High (docs); Medium (policy) |
| 16 | Beta dependencies (OD-14 input) | Avoided: Rust Workers, Workers VPC, D1 read replication, gradual deployments (by choice). One dependency: temporary-credential action scoping, which works by local signing only ("API support coming soon"). It is server-side, and its fallback is **documented but not yet tested** (DR-C1-5). | High (facts); Medium (policy) |
| 17 | Device multipart without per-part presigning? | Possible with a one-key temporary credential, but presigned URLs stay primary (no SigV4 on the device). A desktop temp-credential path is parked. | Medium |
| 18 | Records: presigned PUT or through the Worker? | Through the Worker, with create-only `onlyIf` and the SHA-256 in custom metadata. A retry after a precondition failure is answered by comparing hashes (F4). | Medium-high |
| 18b | Short URLs vs OS background queues | Desktop and Android: re-sign just in time, or re-sign on the specific expired-URL error, with a capped retry count. **iOS: not solved here** (K15 contested); one of the IOS-C10 options or DR-B4-2 is needed. F12. | Medium (v1 platforms); Low (iOS) |
| 19 | Warm cache (C-01) | Off in v1 (window 0). If enabled later: a homelab-side delay before deletion, never a lifecycle rule. | Medium |
| 20 | (new) What stops staging cost growing without bound when the homelab is down? | A Worker-enforced staged-bytes cap tied to BUD-CLOUD (C4 sizes it at about 1.3 TB at $25), a presign pause when the signed heartbeat is stale, and Cloudflare billing notifications. Refusing uploads needs OD-20 (DR-C1-7). F4. | Medium |

## Method

- **Sweep:** four scouts ran: docs, source, community issues, and pricing/standards.
- **Deep read:** the analyst re-fetched every Cloudflare source behind a key claim from `cloudflare/cloudflare-docs @ production` on raw.githubusercontent.com (2026-10-06). Source checks: `workers-rs` README, `worker` 0.8.7 crate source, `aws4fetch` 1.0.20 tarball, npm and crates.io metadata.
- **Spikes:**
  - A spike runner ran C1-S1 to C1-S4 against local Miniflare/workerd, **emulated, not real R2/Cloudflare**, and wrote real-sandbox kits for each.
  - C1-S5 ran for real as a CT spike. Its subject is the API contract, not Cloudflare.
- **Skeptic stage (2026-10-06):** three skeptics (sources, logic, adversary) reviewed key claims K1–K15. The verdicts in §Claims are the code-computed tally:
  - **verified** = has a primary source and at least 2 of 3 skeptics did not refute it;
  - **secondary-only** = no primary source;
  - **contested** = otherwise.
- **Synthesis re-reads (2026-10-06)** to settle skeptic points:
  - D1 `batch()` doc: "reduces latency from network round trips… each statement in the list will execute and commit, sequentially, non-concurrently".
  - D1 FAQ partial: "designed for horizontal scale out across multiple, smaller (10 GB) databases"; writes "depend on the number of rows written".
  - DO class exports page, lines 540–541: `versions upload` fails fast with `exports`; "Gradual deployments are not supported with `exports`".
  - Object-lifecycles page: the example comment "will take precedence over the one above due to its earlier expiration"; removal is "typically… within 24 hours", and existing objects "may take longer".
  - Gradual-deployments index: version affinity.
  - Web Crypto table: MD5 is supported as a non-standard digest.
  - R2 release notes: the CopyObject destination-conditional headers, 2023-06-16.
  - **RFC 9457** (WG editor's copy), the **Idempotency-Key draft** (WG editor's copy, `-latest`) and **RFC 9110 §15.5.22** (httpwg mirror).
- **Routes used:** raw.githubusercontent.com (Cloudflare docs source, `ietf-wg-httpapi/*`, `httpwg/httpwg.github.io`), registry.npmjs.org, static.crates.io, the crates.io API. Context7 was not used.
- **Blocked sources** (none silently replaced; reported to H1):
  - developers.cloudflare.com. The docs' own source repo was used, with the same content; per-file commit dates were not retrieved.
  - docs.aws.amazon.com (S3 conditional-write reference behaviour).
  - rfc-editor.org and datatracker. **Corrected from the draft:** the RFC texts *were* reachable through the working groups' raw GitHub copies. Those copies are cited as "editor's copy, not the published RFC text", and the Idempotency-Key draft's publication status could not be confirmed (the copy is `-latest`).
  - blog.cloudflare.com and cloudflarestatus.com.
  - The github.com web UI for issue bodies.
- **Stop rule:** the synthesis re-reads added primary text but no new source class. The sweep is closed for Wave 1.

## Sources

All Cloudflare docs are `cloudflare/cloudflare-docs @ production : src/content/…`, the source of developers.cloudflare.com, at branch head (commit dates not retrieved).

| # | Source | Publisher | Published or version date | Accessed | Primary? |
|---|---|---|---|---|---|
| S1 | R2 Presigned URLs, `docs/r2/api/s3/presigned-urls.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S2 | R2 S3 API compatibility, `docs/r2/api/s3/api.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S3 | R2 Temporary credentials, `docs/r2/api/s3/temporary-credentials.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S4 | R2 example "Authenticate against R2 with temporary credentials", `docs/r2/examples/authenticate-r2-temp-credentials.mdx` | Cloudflare | reviewed 2026-04-19 | 2026-10-06 | Yes |
| S5 | R2 API tokens, `docs/r2/api/tokens.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S6 | R2 Object lifecycles, `docs/r2/buckets/object-lifecycles.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S7 | R2 Bucket locks, `docs/r2/buckets/bucket-locks.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S8 | R2 Limits, `docs/r2/platform/limits.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S9 | R2 Consistency, `docs/r2/reference/consistency.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S10 | R2 Workers API reference, `docs/r2/api/workers/workers-api-reference.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S11 | R2 release notes, `release-notes/r2.yaml` | Cloudflare | latest entry 2026-04-27 | 2026-10-06 | Yes |
| S12 | R2 Upload objects, `docs/r2/objects/upload-objects.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S13 | R2 Event notifications, `docs/r2/buckets/event-notifications.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S14 | D1 limits FAQ partial, `partials/d1/faq-limits.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S15 | D1 Limits, `docs/d1/platform/limits.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S16 | D1 Worker API, `docs/d1/worker-api/d1-database.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S17 | D1 Query JSON, `docs/d1/sql-api/query-json.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S18 | D1 Time Travel, `docs/d1/reference/time-travel.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S19 | D1 read replication, `docs/d1/best-practices/read-replication.mdx` | Cloudflare | production head (Beta) | 2026-10-06 | Yes |
| S20 | D1 Migrations, `docs/d1/reference/migrations.mdx` | Cloudflare | production head | 2026-09-29 | Yes |
| S21 | DO limits FAQ partial, `partials/durable-objects/do-faq-limits.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S22 | DO Limits, `docs/durable-objects/platform/limits.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S23 | DO SQLite storage API, `docs/durable-objects/api/sqlite-storage-api.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S24 | DO class exports / lifecycle, `docs/durable-objects/reference/durable-objects-migrations.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S25 | DO Alarms, `docs/durable-objects/api/alarms.mdx` | Cloudflare | production head | 2026-09-29 | Yes |
| S26 | Workers Limits, `docs/workers/platform/limits.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S27 | Gradual deployments, `…/gradual-deployments/index.mdx` and `…/with-durable-objects.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S28 | Compatibility dates, `docs/workers/configuration/compatibility-dates.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S29 | Cron Triggers, `docs/workers/configuration/cron-triggers.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S30 | Workflows Limits, `docs/workflows/reference/limits.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S31 | Workers Custom Domains and `workers.dev` routing, `docs/workers/configuration/routing/{custom-domains,workers-dev}.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S32 | Web Crypto, `docs/workers/runtime-apis/web-crypto.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S33 | Rust language page, `docs/workers/languages/rust/index.mdx` (Beta) | Cloudflare | production head | 2026-10-06 | Yes |
| S34 | `cloudflare/workers-rs @ main : README.md` | Cloudflare | main head | 2026-10-06 | Yes |
| S35 | `worker` crate 0.8.7 source and crates.io API | Cloudflare / crates.io | 0.8.7, 2026-09-25T23:41Z | 2026-10-06 | Yes |
| S36 | `aws4fetch` 1.0.20 tarball, `dist/aws4fetch.esm.mjs` | M. Hart | 1.0.20, 2024-08-28 | 2026-10-06 | Yes |
| S37 | Workers VPC overview, `docs/workers-vpc/index.mdx` (Beta) | Cloudflare | production head | 2026-10-06 | Yes |
| S38 | Queues pull consumers and limits | Cloudflare | production head | 2026-09-29 (A3 read in full) | Yes |
| S39 | npm registry metadata (wrangler, miniflare, hono, aws4fetch, vitest-pool-workers, drizzle-orm, kysely, chanfana, zod) | npm | as listed | 2026-10-06 | Yes |
| S40 | Project notes: A3, D1, CE, C4 (`c4-cost-model.md`: w = 6 rows/file, s̄ = 4 MB, staging cap), `data-model.md` | Project | drafts | 2026-10-06 | Yes (project) |
| S41 | workerd #2572, #6561, #7190 | Cloudflare repo, users | 2024-08-21 to 2026-08-30 | 2026-09-29 | No |
| S42 | workers-sdk #14916, #15774, #15387, #15904 | users | 2026-07-29 to 2026-09-27 | 2026-09-29 | No |
| S43 | workers-rs #166, #453, #826, #967 | users | 2022-04 to 2026-04 | 2026-09-29 | No |
| S44 | Ente museum, Immich, restic rest-server, Headscale source | projects | main heads | 2026-09-29 | Yes |
| S45 | G2-S1 emulator fidelity, `spikes/G2-S1/results/comparison.md` (Miniflare run `127a684a`; **emulated**) | Project | 2026-09-29 | 2026-10-06 | Project measurement of an emulator; nothing about R2 |
| S46 | Threat register, `docs/security/threat-model.md` | Project (D1) | draft | 2026-10-06 | Yes (project) |
| S47 | B4 iOS decision note, `docs/research/b4-ios-decision.md` (K6, P6, IOS-C10, IOS-C16, DR-B4-2) | Project (B4) | draft | 2026-10-06 | Yes (project; Apple sources cited there) |
| S48 | RFC 9457 Problem Details, WG editor's copy `ietf-wg-httpapi/rfc7807bis @ main : draft-ietf-httpapi-rfc7807bis.md` | IETF HTTPAPI WG | editor's copy, not the published RFC text | 2026-10-06 | Yes (editor's copy) |
| S49 | Idempotency-Key header draft, `ietf-wg-httpapi/idempotency @ main : draft-ietf-httpapi-idempotency-key-header.md` (`-latest`) | IETF HTTPAPI WG | editor's copy; publication status not confirmed | 2026-10-06 | Yes (draft) |
| S50 | RFC 9110 HTTP Semantics, `httpwg/httpwg.github.io @ main : specs/rfc9110.html`, §15.5.22 | IETF HTTP WG mirror | RFC 9110 (2022) | 2026-10-06 | Yes (mirror) |
| S51 | C1 spike results (emulated except C1-S5): `spikes/C1-S1` … `spikes/C1-S5` | Project (spike runner) | 2026-10-06 | 2026-10-06 | Project measurements; emulated ones say nothing about Cloudflare |
| S52 | Apple `isDiscretionary` (developer.apple.com JSON), as cited by the sources skeptic and in B4 | Apple | current | 2026-10-06 (skeptic) | Yes |

## Claims

### Key claims (skeptic-reviewed; verdicts are the code-computed tally)

Skeptics: 1 = sources, 2 = logic, 3 = adversary. "Upheld" means not refuted.

| # | Claim | Sources | Skeptic 1 | Skeptic 2 | Skeptic 3 | Verdict |
|---|---|---|---|---|---|---|
| K1 | Each D1 database is single-threaded and runs queries one at a time (about 1,000 q/s at 1 ms, 10 q/s at 100 ms). A full queue returns "overloaded". Each database is backed by one DO. Writes can take several ms. | S14 | Upheld; the same page recommends scaling out across many smaller databases | Upheld; write time "depend[s] on the number of rows written" | Upheld; does not say whether batched statements count separately | **Verified** |
| K2 | One D1 `batch()` per API request keeps aggregate load at about 0.47 thread-s/s (25 devices × 20 Mbit/s, 2 MB files, 3 writes/file, 5 ms/write). A 1M-ID presence check costs far under $1 via `json_each`. | S14, S17, S40 | **Refuted**: 0.47 is the unbatched figure; `batch()` runs statements "sequentially, non-concurrently"; homelab load omitted; cost rests on emulated `rows_read` | **Refuted**: same; C4 uses w = 6 (≈ 0.94 s/s); reads omitted | **Refuted**: same; only set-based statements make "query rate track request rate" | **Contested.** Withdrawn as stated. F2 restates the capacity question as unmeasured; the cost half is kept only as "indicative, emulated" |
| K3 | Presigned URLs: GET, HEAD, PUT, DELETE only; 1 s – 7 days; made with no call to R2; reusable bearer tokens; S3 domain only, not custom domains. The documented example signs only `host` with UNSIGNED-PAYLOAD. | S1 | Upheld; the POST exclusion is about HTML-form POST, so presigned `?uploads` is undocumented rather than excluded; Content-Type signing is documented | Upheld; the example is a GET, weak evidence of PUT defaults (aws4fetch C36 is better) | Upheld; same caveat | **Verified** |
| K4 | S3 table: If-None-Match for PutObject, no conditionals for CompleteMultipartUpload. Release note 2023-08-11: a failed conditional completion aborts the upload. Release note 2022-05-27: conditional CreateMultipartUpload returns 412. | S2, S11 | Upheld; the Create row also lists no conditionals; the binding `complete()` takes no `onlyIf` at all | Upheld; "unresolved", not a contradiction | Upheld | **Verified** |
| K5 | R2 supports SHA-256 (and SHA-1, CRC32, CRC32C) only as COMPOSITE; CRC64NVME is the only FULL_OBJECT type. UploadPart lists Content-MD5 and no `x-amz-checksum-*`. | S2 | Upheld; but the table is weak negative evidence: PutObject also omits `x-amz-checksum-*`, yet a release note says putObject supports sha256 | Upheld | Upheld | **Verified.** The inference "integrity rests on per-part MD5" is softened: per-part SHA-256 is untested (new H15) |
| K6 | Default lifecycle rule aborts multipart uploads 7 days after initiation; up to 1,000 prefix rules; deletion lags up to ~24 h; whether a longer abort overrides the default is not documented. | S6 | Upheld; lag is "typically" 24 h and "may take longer"; the example implies earliest-wins | Upheld; the real question is whether the default can be removed | Upheld; H8 likely fails | **Verified**, wording corrected (F3) |
| K7 | Long-lived tokens: four levels, only Object-level scoped to buckets, no prefix scope, no delete split. Temp credentials: one bucket, action and path scope; action scoping by local HS256 signing only ("coming soon"); revoking the parent stops them "immediately". | S3, S4, S5 | Upheld; the derivation is specified in prose on the concept page, not only by example | Upheld; same correction | Upheld; no normative payload spec | **Verified** |
| K8 | API-key permission changes are eventually consistent ("up to a minute"); the temp-credential page says revoking the parent is "immediate"; last writer wins on one key. | S9, S3 | Upheld; the two statements may not conflict | Upheld; "disagree" is over-read; the proposed kill switch (a roll) is covered by neither | Upheld | **Verified.** The "conflict" framing is dropped; roll semantics are unknown (H11) |
| K9 | Rust on Workers is Beta; `worker` 0.8.7 (2026-09-25) aborts on panic by default; `--panic-unwind` needs nightly with `-Zbuild-std`. | S33, S34, S35 | Upheld; moderate evidence (with the flag, a panic fails one request) | Upheld; the choice also depends on ADR-0003 | Upheld | **Verified** |
| K10 | Gradual deployments route each request independently; each DO is pinned to one version per deployment; lifecycle changes only via `wrangler deploy`; `versions upload` fails fast with `exports`. | S27, S24 | Upheld; "Gradual deployments are not supported with `exports`" covers the whole Worker | Upheld; same implication missed | Upheld | **Verified.** F10 is corrected: DOs go in a separate Worker, and v1 does not use gradual deployments |
| K11 | Workers VPC is Beta and has the Worker initiate requests into the private network through a Tunnel. | S37 | Upheld | Upheld | Upheld | **Verified** |
| K12 | Custom Domain needs an active Cloudflare zone and no existing CNAME; `workers_dev = false` in config; disabling `workers.dev` does not disable Version or Preview URLs. | S31 | Upheld | Upheld; Deployment URLs also stay enabled | Upheld; an active zone puts the domain's DNS and the API on one account | **Verified** (Deployment URLs added) |
| K13 | Request body 100 MB Free/Pro, 200 MB Business, up to 5 GB Enterprise; 30 s grace on runtime updates, "very unlikely" to matter. | S26 | Upheld | Upheld | Upheld | **Verified** |
| K14 | Emulated only: Miniflare's R2 S3 endpoint ignores `x-amz-checksum-sha256`, overwrites on conditional Complete, returns 200 on conditional Create, lacks ListParts and lifecycle, so local runs cannot settle C1-S1. | S45 | Upheld; on Complete, Miniflare matches the S3 table | Upheld; Miniflare is also inconsistent with itself (Content-Length 403 vs 500) | Upheld; the README cites T35 for lifecycle where it means T54 | **Secondary-only** (no primary source about R2; project evidence about an emulator) |
| K15 | iOS background transfers are discretionary, so a 15-min URL can expire before sending; a re-sign endpoint keeps the revocation window without longer URLs. | S47, S1 | **Refuted**: the premise holds; the remedy is not shown, because the URL is fixed at hand-off and re-sign-on-failure can cycle | **Refuted**: holds for desktop and Android WorkManager only | **Refuted**: foreground non-discretionary tasks exist; each failed attempt may send a whole part | **Contested.** Re-scoped to desktop and Android (F12); iOS stays with DR-B4-2 |

### Other claims (not key; not separately skeptic-reviewed)

The analyst draft's detailed claim rows C1–C53 were folded into the key claims above; their wording is in the git history of this file. Mapping: K1 ← C27; K2 ← F2 arithmetic, C24, C26; K3 ← C1–C4; K4 ← C5, C7, C8, C49; K5 ← C5, C6; K6 ← C13, C17; K7 ← C10–C12, C51; K8 ← C11, C14; K9 ← C32–C34; K10 ← C42, C43; K11 ← C38; K12 ← C39, C40; K13 ← C20, C22, C50; K14 ← C52; K15 ← C53. A row tied to a key claim carries that claim's verdict. The others are listed here.

| # | Claim | Sources | Status |
|---|---|---|---|
| C9 | Same part number replaces the earlier part; part ETag = MD5; multipart ETag = MD5(concatenated part MD5s)-N; equal part sizes except the last (5 MiB – 5 GiB) | S2, S12 | Primary. Emulated C1-S1: the object formula holds; Miniflare part ETags are not MD5 |
| C15 | Bucket locks block deletion and overwrite for Age or Indefinite per prefix; the longest wins; locks take precedence over lifecycle rules; nothing is said about in-progress multipart uploads | S7 | Primary |
| C16 | Binding `put()` takes `onlyIf` and a sha256 option; `resumeMultipartUpload` does not validate the uploadId | S10 | Primary. Emulated C1-S1 C10, C14 consistent |
| C18 | R2: 1,024-byte keys; 10,000 parts; 1 write/s per key (429 above); REST API 1,200 req / 5 min per account | S8 | Primary |
| C19 | Max single upload or part 4.995 GiB; multipart 4.995 TiB | S8 | Primary |
| C21 | Workers Paid: CPU 30 s default (5 min max); 10,000 subrequests default; 128 MB; 64 MiB script | S26 | Primary |
| C23 | Cron CPU 30 s (< 1 h interval); wall 15 min; UTC; changes take up to 15 min to propagate | S26, S29 | Primary |
| C24 | D1 `batch()`: "reduces latency from network round trips"; statements "execute and commit, sequentially, non-concurrently"; one transaction; failure rolls back | S16 (re-read in synthesis) | Primary; quoted by all three skeptics in the K2 review |
| C25 | D1: 10 GB per database ("cannot be further increased"); 100 bound parameters; 100 KB statement; 1,000 queries per invocation | S14, S15 | Primary |
| C26 | `json_each` expands one bound JSON array for `IN (SELECT value FROM json_each(?))` | S17 | Primary |
| C28 | D1 Time Travel 30 days (CLI); DO PITR 30 days from object code only, not local | S18, S23 | Primary |
| C29 | D1 read replication is Beta | S19 | Primary |
| C30 | DO: single-threaded, ~1,000 req/s soft; 10 GB per object; `transactionSync()` | S21–S23 | Primary |
| C31 | DO alarms are at-least-once, with 6 retries | S25 | Primary |
| C35 | workers-rs panic-handling issue history | S43 | **Secondary only** |
| C36 | aws4fetch defaults `X-Amz-Expires` to 86,400 s, signs UNSIGNED-PAYLOAD unless set, excludes content-length unless `allHeaders`, caches the signing key per day | S36 | Primary (source); emulated C1-S1 confirms the signing behaviour |
| C37 | Workers Web Crypto has Ed25519, X25519, HMAC, SHA-256, and MD5 (non-standard, "do not rely upon MD5 for security") | S32 | Primary |
| C41 | Old compatibility dates are supported forever | S28 | Primary |
| C44 | The Workflows limits page cites 3/10 MB script size; Workers limits say 64 MiB | S30, S26 | Primary; doc inconsistency |
| C45 | Wildcard-etag bug (#2572, closed); local `SQLITE_BUSY` crash (#14916) | S41, S42 | **Secondary only**. Emulated C1-S1 H12 passed on the pinned versions |
| C46 | Workflows Paid limits | S30 | Primary; not used in v1 |
| C47 | Tool versions on 2026-10-06: wrangler 4.148.0; miniflare 5.20261006.0-alpha (the `latest` tag is an alpha); hono 4.13.13; aws4fetch 1.0.20; vitest-pool-workers 0.22.0; drizzle-orm 0.45.3; kysely 0.29.6; chanfana 3.4.0; zod 4.6.5 | S39 | Primary (registry) |
| C54 | (new) D1 FAQ: "D1 is designed for horizontal scale out across multiple, smaller (10 GB) databases" | S14 (synthesis re-read) | Primary; supports the fallback ladder |
| C55 | (new) Gradual deployments support version affinity to keep a user on one version | S27 | Primary |
| C56 | (new) R2 release note 2023-06-16: "CopyObject in the S3 compatible api now supports Cloudflare specific headers which allow the copy operation to be conditional on the state of the destination object" | S11 | Primary |
| C57 | (new) RFC 9110 §15.5.22: "The server MUST send an Upgrade header field in a 426 response to indicate the required protocol(s)" | S50 | Primary (mirror) |
| C58 | (new) RFC 9457: problem details as `application/problem+json`; members `type`, `status`, `title`, `detail`, `instance`; "Clients consuming problem details MUST ignore any such extensions that they don't recognize" | S48 | Primary (editor's copy) |
| C59 | (new) Idempotency-Key draft: missing key → 400; reuse with a different payload → 422; retry while the first is in progress → 409; the resource "SHOULD define such expiration policy and publish it" | S49 | Primary (draft, editor's copy; status unconfirmed) |

## Findings

### F1. Topology (for ADR-0010)

| Component | Role | Holds | Notes |
|---|---|---|---|
| **Worker `rq-api`** (TypeScript) on `api.<owner-domain>` | Device, homelab and enrollment API; presigning; minting homelab temp credentials; writing records to R2; cron | R2 parent secret(s) (F4), R2 and D1 bindings, the homelab's **public** control key | No trust-forging key (SR-23). `workers_dev = false`; Preview, Version and Deployment URLs handled (K12). **Declares no DO classes**, so it keeps `versions upload` (K10). |
| **D1 `rq-control`** | System of record (provisional; F2) | F6 tables | Set-based writes; a data-access layer hides the store. |
| **Worker `rq-gate`** + DO class `DeviceGate` (optional; C2 decides) | Exact per-device counters | Small per-device SQLite | Bound from `rq-api` by `script_name`. Deployed only with plain `wrangler deploy`. |
| **R2 `rq-ingest`** | Content and record staging | `staging/`, `meta/`, reserved `pack/` | **No Expiration rule, ever.** Default 7-day multipart abort only. |
| **R2 `rq-restore`** | Restore staging (ADR-0001 §6) | `restore/` | Expiration (e.g. 7 days) plus a 1-day abort rule. |
| **Cron Trigger** | Due-work runner | — | F9. |
| Queues, R2 event notifications | Not used in v1 (DR-C1-3) | — | Option D in DR-C1-3 if the owner prefers. |
| **Homelab** (outbound only) | Polls the feed, lists R2, pulls, verifies, commits, publishes receipts, deletes staging | Its control key; short-lived R2 temp credentials | F5. |

Environments: `local` (pinned wrangler/miniflare; **emulated**), `sandbox` (H1's separate account and throwaway domain), `production`. Use separate accounts rather than wrangler environments in one account, because R2 parent tokens and the REST rate limit are per account (C18).

### F2. D1 vs Durable Objects (capacity unproven; K2 contested)

**Why the choice is about operations and throughput, not correctness.** A3 made the claim an advisory lease. A lost, doubled or rolled-back lease costs bandwidth, not data (SR-01, SR-04, SR-05). C1-S2, emulated, confirms that both stores' *SQL logic* gives exactly one winner (below). It says nothing about real latency or overload.

| Criterion | D1 (one DB) | D1, several DBs | SQLite DOs, sharded | Recommended |
|---|---|---|---|---|
| Throughput | One thread per DB (K1) | One thread per DB, N DBs | One thread per object, ~1,000 req/s soft (C30) | Start with one D1; step up only on measurement |
| Atomic multi-row update | `batch()` as one transaction (C24) | Within one DB only | `transactionSync()` within one shard | Advisory lease needs no cross-shard atomicity |
| Migrations, backup, ad-hoc SQL | wrangler migrations, Time Travel, export, `d1 execute` (C28) | Same, per DB | Self-written; PITR only from object code | D1 |
| Size | 10 GB, cannot be raised (C25) | 10 GB each | 10 GB per object | See the size check below |

**Capacity: what is and is not known.**
- **Corrected arithmetic (assumptions, not measurements).** Thread time per file is w × t, where w is the rows written per file and t the time per row-write. At an aggregate bandwidth B, one database saturates when the mean file size falls to **S_sat = B · w · t**.
  - With B = 62.5 MB/s (25 devices × 20 Mbit/s, all at once; a pessimistic peak), w = 6 (C4) and t = 5 ms ("several ms", K1), S_sat ≈ 1.9 MB.
  - C4's central mean file size is 4 MB (range 2–8 MB), which is about 50 % utilisation. A 2 MB mean gives about 94 %.
  - Reads (presence checks, lease checks, feed polls, receipt fetches) and homelab-side writes (commit marks, receipt-relay insert and delete, prune) come on top. The earlier "2× headroom" claim is **withdrawn**.
- **Batching does not reduce this.** `batch()` "reduces latency from network round trips". Its statements "execute and commit, sequentially, non-concurrently" (C24), and write time depends on rows written (K1). Batching removes per-request round trips and may amortise commit cost, but that is undocumented.
- **Design rule kept:** write SQL is **set-based**, one statement per table per request (`INSERT … SELECT … FROM json_each(?1)`, `UPDATE … WHERE id IN (SELECT value FROM json_each(?1))`). This is the best available lever. Whether D1's cost is per statement or per row is exactly what the C1-S2/S3 kits must measure on real D1, using `meta.duration` for N single inserts vs a batch of N vs one set-based insert at N = 1, 100 and 1,000. This is a hand-off to the spike runner, because the kits are theirs.
- **Pre-agreed decision rule:**
  - If real-D1 utilisation at C4's central case, using E1's file-size distribution, exceeds about 50 %, take fallback step (a): split into two D1 databases, `rq-dedup` (dedup, leases) and `rq-control` (everything else). The D1 FAQ recommends this pattern (C54), and it keeps migrations, Time Travel and export.
  - Step (b): shard `rq-dedup` by the first ID character into N D1 databases, or 16 SQLite DOs if N databases prove awkward. Presence checks fan out to ≤ 16 subrequests (C21).
- **Overload behaviour:** "overloaded" maps to 503 + `Retry-After` with jittered exponential backoff (F8). Homelab commit endpoints should keep priority: a C2 brake on device bulk endpoints (Rate Limiting binding or `DeviceGate`).
- **Location hint:** create D1 with a location hint near the family and the homelab (adversary suggestion). It is unmeasured; record it in the sandbox kit.

**Presence-check cost (indicative, emulated).** Emulated C1-S3 gave `rows_read` = 1,500 per 1,000-ID call with a primary-key SEARCH per ID. At published prices that is about $0.002 per million IDs. If real D1 planned a scan instead, 1,000 calls × 5M rows would cost about $5 per million IDs and fail the < $1 criterion. The kit must record the real `meta.rows_read` and `EXPLAIN QUERY PLAN`.

**Size check (estimate).** At 100–200 B per row including the index (assumption), 5M dedup rows are 0.5–1 GB. At a 2–8 MB mean file size, 2–10 TB is roughly 0.25M–5M files, so dedup alone is far from 10 GB. Growing tables need **retention rules**:
- feed: prune 30 days after the homelab's cursor passes;
- idempotency: published 7-day expiry (C59);
- receipt relay: delete after the device fetches (A3);
- audit log: keep 90 days in D1; the nightly export is the archive (C8).
The cron reports database size and alerts the owner at 50 % and 80 % of 10 GB (F9).

**Rejected:** a KV existence cache (eventually consistent); one global DO (same single thread, worse tooling).

### F3. R2 key layout and buckets (one-way door #7)

| Bucket / prefix | Key | Writer | Reader / deleter | Lifecycle |
|---|---|---|---|---|
| `rq-ingest` `staging/` | `staging/<dedup_id>/<upload_id>/s<n>` | Device via presigned PUT/UploadPart; Worker creates and completes multipart | Homelab (GET, LIST, DELETE after durable commit) | None besides the default 7-day multipart abort |
| `rq-ingest` `meta/` | `meta/<device_id>/<record_batch_id>.age` | Worker (`put` with create-only `onlyIf`) | Homelab | None |
| `rq-ingest` `pack/` (**reserved**) | `pack/<upload_id>/s<n>` | Device (presigned), same rules as `staging/` | Homelab | None |
| `rq-restore` `restore/` | `restore/<device_id>/<restore_job_id>/<object_id>` | Homelab (temp credential) | Device via presigned GET | Expiration 7 days; abort 1 day |

- **Per-upload keys** avoid last-writer-wins and the 1 write/s per-key limit (C18, K8; SR-07).
- **No dedup ID in `meta/` keys** (SR-26).
- **The reserved `pack/` form** (logic skeptic, major) holds many encrypted objects and records in one staged object if A2/A4 adopt packing (B4 IOS-C16, USB bundle reuse). A pack has no single dedup ID, so it cannot use `staging/<dedup_id>/…`. Reserving the prefix now keeps door #7 from closing against it. The homelab lister must handle both forms, and its temp credential covers `staging/`, `meta/` and `pack/`. Whether packs are used at all is A2/A4's decision before Gate A.
- **Two buckets** (DR-C1-2):
  - long-lived tokens scope only to buckets (K7);
  - one mistyped prefix in a shared lifecycle configuration could expire staging;
  - with two buckets, "the ingest bucket has no Expiration rule" is a script check on `wrangler r2 bucket lifecycle list rq-ingest`.
- **7-day abort: plan for "cannot extend".**
  - The lifecycle page's example comment says a 1-day prefix rule "will take precedence over the one above due to its earlier expiration". That implies the earliest rule wins (K6).
  - H8 (a longer rule overrides) is therefore expected to fail. The useful test is a new **H8b**: on a fresh bucket, list the rules and try to remove or replace the default rule (`lifecycle remove --id`, or a replacing PutBucketLifecycleConfiguration), then observe the abort time. This is a hand-off to the spike runner (the A3-S3 kit holds H8).
  - Design consequence: any upload that might take more than 7 days must use A3's segment checkpoint (`s1…`), driven by the day-6 cron, as its **primary** mechanism, not a fallback. Arithmetic: at 2 Mbit/s continuous, 7 days moves about 151 GB; at a 10 % duty cycle about 15 GB. Part and segment sizes (B6) should keep any one multipart upload well under that.
  - Deletion lag: objects are "typically" removed within 24 h, and existing objects "may take longer" (K6, corrected wording). This matters for the restore bucket's expiry only.
- **Bucket locks:** defence in depth only, if C1-S1 H9 shows a lock blocks overwrite by presigned PUT and Complete without blocking in-progress uploads or the homelab's cleanup.

### F4. Upload flow, presigning, records and cost guard rails

**Content (device → R2 directly):**
1. `POST /v1/uploads` (batch). The Worker records the lease, generates `upload_id` and the key, and either returns a presigned PUT (single part) or calls `createMultipartUpload` and returns a first **window** of presigned UploadPart URLs.
   - Every URL lifetime ≤ 15 min (BUD-REVOKE).
   - `X-Amz-Expires` is always explicit (aws4fetch defaults to 24 h, C36).
2. `POST /v1/uploads/{id}/parts` returns the next window: min(remaining parts, ceil(uplink × 900 s / part size)). That is about 134 parts of 16 MiB at 20 Mbit/s, and about 14 on 2 Mbit/s.
3. `POST /v1/uploads/{id}/complete` (Worker completes via the binding; it must handle NoSuchUpload). The Worker compares the size with the declared size (SR-24) and marks the upload `staged`. The device may check the multipart ETag formula (C9) as a corruption check, not a security check.
4. Signing extras, each **only after the real C1-S1 shows R2 enforces it**: `Content-MD5` (H4), `If-None-Match: *` on single PUT (H1), Content-Length (H5), `x-amz-checksum-sha256` on single PUT (H6), and per-part `x-amz-checksum-sha256` on UploadPart with COMPOSITE completion (new **H15**, sources skeptic). Emulated C1-S1 shows aws4fetch signs all of these into `SignedHeaders`. That is a property of the signer, not of R2.
5. **Conditional Complete: not used, because under per-upload keys it adds almost nothing** (logic skeptic). The Worker generates random keys and never issues a presigned PUT for a multipart key, so the only way a key can already exist at Complete is a retry after a successful Complete. H2 stays in the kit only to close the documentation question (K4). It must use the **S3 API** CompleteMultipartUpload, because the binding `complete()` takes no condition. The emulated "binding complete() overwrote" result is relabelled "binding has no conditional complete (documented)".
   - **Considered and rejected:** create-only **CopyObject** from the per-upload key to a final key, using Cloudflare's destination-conditional headers (C56). It doubles write operations and adds a step without changing the safety basis, which is homelab verification.

**Records (device → Worker → R2):** `POST /v1/records` carries an opaque record batch.
- The Worker computes the SHA-256 of the body.
- It writes `meta/<device_id>/<batch_id>.age` with `put(…, {onlyIf: {etagDoesNotMatch: "*"}, customMetadata: {sha256}})` (H12 passed emulated, in both forms).
- In the same request it runs **one** set-based D1 statement group: feed append and idempotency rows.
- **Retry semantics** (logic skeptic). R2 and D1 are not atomic together. If `put` returns null (precondition failed), the Worker `head()`s the key and compares `customMetadata.sha256` with the body's hash. If they are equal, it replays the D1 statements, which are idempotent on natural keys, and returns success. If they differ, it returns a typed `conflict`. This keeps the opaque-artifact rule: the bytes are hashed, never parsed. A3's state table should carry this (hand-off).

**Revocation (BUD-REVOKE).**
- A revoked device gets no new URLs within 60 s, because the Worker checks D1 on every call. Outstanding URLs die within 15 min by construction. **BUD-REVOKE does not depend on any kill switch.**
- **Kill switch (extra, not required).** Rolling or deleting an R2 parent token *may* invalidate outstanding URLs and temp credentials. No doc covers a *roll* (K8), so H11 must measure it.
  - Operationally, a roll means updating the Worker secret (`wrangler secret put`) before presigning works again. Until then, uploads stop for the whole family.
- **Two parent tokens (proposal handed to C2 and D3):** one for *device signing* (`rq-ingest` only) and one for *homelab minting*. Rolling the device token then does not cut the homelab off mid-drain.
  - Limited purpose (adversary skeptic): both secrets live in the same Worker, so the split separates the kill switch from draining. It does **not** contain a Worker compromise.
  - The homelab-minting token cannot be narrowed below Object R&W, because deleting needs write and no delete-only level exists (K7).
- **What a leaked URL can do:** rewrite that one staged key until expiry, unless H1 passes. The homelab rejects mismatching bytes (SR-04), and the device re-uploads. That is availability, not loss. DR-C1-6 records the append-only interpretation.

**Cost guard rails (adversary skeptic, major).** The ingest bucket never expires objects, so a homelab outage lets staging grow, and R2 bills the mean of daily peak GB-months (C4). Arithmetic at $0.015/GB-month: a 2 TB backlog costs about $30/month, 10 TB about $150/month. ADR-0010 adds:
- **staged-bytes accounting** in D1 (declared sizes of uploads in `open` or `staged` and not yet deleted);
- **refusing new uploads above a cap** tied to BUD-CLOUD (C4 derives about 1.3 TB at a $25 ceiling). The device message is C4's "home storage full" text. *Refusing* needs OD-20 (DR-C1-7);
- **pausing or throttling presign** when the signed homelab heartbeat is older than N hours (N set with C7), with a plain-language status;
- **Cloudflare billing and usage notifications** (C2/C4).

### F5. Homelab authentication and notifications

- **Homelab → Worker:** requests signed with a homelab Ed25519 control key. The Worker holds only the public key (SR-23). D3 owns the request format, and D2 the key inventory. Endpoints: feed, commits, rejections, heartbeat, revocations, credentials, export, restore-jobs.
- **Homelab → R2 (proposal handed to C2 and D3):** `POST /v1/homelab/credentials` returns two locally minted temp credentials (one bucket each, K7), TTL ≤ 1 h:
  - **ingest:** `ListObjectsV2`, `GetObject`, `HeadObject`, `DeleteObject`, `ListMultipartUploads`, `AbortMultipartUpload` on `staging/`, `meta/` and `pack/`;
  - **restore:** `PutObject` and the multipart write actions on `restore/`.
  - The homelab stores no long-lived Cloudflare secret except an **offline break-glass** token.
  - **The fallback is untested:** H13 cannot be emulated, because Miniflare refuses session tokens. A break-glass drain drill must pass before Gate B (C8 runbook, hand-off to the spike runner).
- **Feed instead of Queues (DR-C1-3):** the homelab polls `GET /v1/homelab/feed?after=<seq>` about every 30 s (about 86k requests a month) and lists `staging/`, `meta/` and `pack/` at start and hourly. This removes a Cloudflare API token at home, the 1,200/5 min REST limit and its lockout, and the Queues retention and `max_retries` loss modes (A3 C3–C7).
  - **Option D** (logic skeptic): R2 event notifications → Queue → a *push consumer Worker* that appends to the same D1 feed. It also needs no token at home and no REST limit, it keeps Queues as ADR-0001 §1 names them, and it gives a server-side "object staged" signal for single PUTs. It costs a Queues line and still drops messages after retries (reconciliation covers that). It is offered in DR-C1-3; B remains the recommendation because the Worker already sees every record and every Complete.
- **Workers VPC / Tunnel push: rejected** (K11; R-12). It inverts who initiates requests, contradicts ADR-0001's pull model, and is Beta.

### F6. Cloud state: what is rebuildable and what needs backup (C8 input)

| Table (D1) | If lost | Backup | Retention |
|---|---|---|---|
| `accounts` (name, email, verification) | Users re-verify | **Nightly export** | Life of account |
| `invites`, `enroll_tokens`, `pair_codes` (hashed) | Printed cards stop working | **Nightly export** | Until expiry + 30 days |
| `devices` | Re-enrollment unless a homelab-signed list exists (D3) | Export | Life of device |
| `uploads` (leases, staged-bytes accounting) | Parallel uploads only | None | Delete 30 days after the terminal state |
| `dedup` | Re-uploads until the homelab republishes | Rebuild from the homelab | Keep |
| `receipt_relay` | Homelab republishes | Rebuild | Delete after the device fetches |
| `feed` | Reconciliation covers it | None | 30 days past the homelab cursor |
| `revocations`, `heartbeat` | Homelab republishes | None | Latest only |
| `idempotency` | Natural keys make it safe | None | 7 days (published, C59) |
| `audit_log` | Lost history | **Nightly export** (archive at home) | 90 days in D1 |
| `email_suppression` | Re-sending to bad addresses | **Nightly export** | Keep |

D1 Time Travel (30 days) covers mistakes, not account loss, hence the signed nightly `GET /v1/homelab/export`.

### F7. Worker language (DR-C1-1)

| Criterion | TypeScript (Hono) | Rust `workers-rs` | TS + Rust→Wasm for named functions |
|---|---|---|---|
| Platform status | GA | Beta (K9); crate 0.8.7 | TS GA |
| Failure mode | Exception per request | Panic aborts the instance unless nightly `--panic-unwind` (K9) | Panics confined to the module |
| Crypto | Native Ed25519, HMAC, SHA-256, MD5 (C37) | Crates in Wasm | Native where possible |
| Tests | `@cloudflare/vitest-pool-workers` | wrangler dev + external | Both |
| Formats implemented twice | Request auth, code hashing, ID-encoding checks, API schema | None | Fewer |

**Opaque-artifact rule:** the Worker never parses envelopes, records, receipts, manifests, bundles or dedup-ID derivations. It hashes and stores bytes. What remains (request-signature base string, code hashing, ID-encoding checks, OpenAPI schema) is pinned by shared vectors (G2). **Recommendation: A, TypeScript.** Revisit trigger: D3 picks a KDF Web Crypto lacks; then compile that one function to Wasm (option C), not the whole Worker. The skeptics did not refute K9; the choice also depends on ADR-0003 (client stack, open), which affects only which language the second implementation is checked against.

### F8. API v1 conventions (detail in `docs/design/api-v1.md`, Draft)

- **Hosts:** `api.<owner-domain>` (Custom Domain, K12). Content URLs use `<ACCOUNT_ID>.r2.cloudflarestorage.com` (K3); clients never pin it. Putting the zone on Cloudflare places the domain's DNS and the API on one account (adversary skeptic). That is a further reason for DR-C1-4's second bootstrap location on another provider.
- **Bootstrap (door #8):** `GET /v1/bootstrap`, offline-signed (key custody is D3/D5's), at two independent locations. It carries no trust material (SR-31).
- **Versioning (C1-S5 rules):**
  1. `/v1/`, additive-only within v1.
  2. **Clients decode every server enum with an `unknown` catch-all.** Otherwise a new enum value must be gated by `min_version` like any breaking change. C1-S5: a closed enum gave DECODE_ERROR on HTTP 200.
  3. **Every breaking change raises `min_version` in the same deployment.** C1-S5: an ungated rename broke both decoders on HTTP 200. This is a review-checklist item plus a contract test against the previous client build (G2).
  4. **Server request schemas strip unknown keys** (zod default) rather than reject them. C1-S5: `.strict()` gave 400 to a newer client.
  5. `Reliquary-Client: <platform>/<semver>` is required.
- **`update_required`:** a problem body with `code: "update_required"` and `min_version`, sent with **HTTP 400**. RFC 9110 says a 426 "MUST send an Upgrade header field… to indicate the required protocol(s)" (C57), which does not fit an app update. Clients key on `code`, never on status. C1-S5 used 426; the mechanism result stands, and the toy is re-run with 400 when the OpenAPI draft lands.
- **Errors:** `application/problem+json` per RFC 9457 (C58): `type`, `title`, `status`, `detail`, plus extension members `code` (stable), `retryable`, and `min_version` where relevant. Clients ignore unknown extensions, as RFC 9457 requires. 429/503 carry `Retry-After`. D1/DO "overloaded" maps to 503 retryable. Clients use **jittered exponential backoff** with a cap.
- **Idempotency:** natural keys first. `Idempotency-Key` on redeem, pair and restore-job creation, following the draft (C59): 400 when missing, 422 on a payload mismatch, 409 while in progress, and a published 7-day expiry. The draft's publication status is unconfirmed (S49).
- **Batching:** `check` ≤ 1,000 IDs; `uploads` ≤ 100; `records`; `commits`. Typed per-item results. Set-based SQL (F2).
- **Server time:** `Reliquary-Server-Time` header (present in C1-S5).
- **Re-sign:** `POST /v1/uploads/{id}/urls` (F12).

### F9. Background jobs

| Job | Mechanism | Notes |
|---|---|---|
| Lease expiry | Lazy (`lease_expires_at > now`) | No sweeper |
| Stale device, nudges | Cron, ~15 min, UTC | Idempotent "what is due"; `nudge_sent_at` |
| Dead-man's switch | Cron on the signed heartbeat | C7 adds an external check |
| Presign pause on a stale heartbeat | Cron sets a flag; the Worker checks it | F4 guard rail |
| Day-6 multipart checkpoint | Cron | **Primary** path for long uploads (F3) |
| D1 size alerts and table pruning | Cron | 50 % / 80 % of 10 GB; F6 retention |
| Per-device counters | DO alarm in `rq-gate` | At-least-once; idempotent |
| Long sequences | Workflows (not v1) | — |

### F10. Change management and beta policy

- **No gradual deployments in v1.** A single-owner system gains little from canarying. Gradual deployments split traffic per request (K10), which creates a two-version window for every multi-request upload flow. Plain `wrangler deploy` only. If gradual deployments are ever adopted, use version affinity (C55) and keep DO classes out of that Worker.
- **Expand → deploy → contract D1 migrations are still required,** because `migrations apply` and the code deploy are not atomic. Either order leaves a window where code and schema disagree. Take a Time Travel bookmark before each apply (C28). CI retries apply on 403/7403 (secondary, S42).
- **DO classes live in `rq-gate`**, a separate Worker bound by `script_name`. `exports` makes `versions upload` fail fast, and "Gradual deployments are not supported with `exports`" (K10, corrected C43 wording). Keeping DOs out of `rq-api` leaves that Worker free to use versions later. Use one call style per DO (#6561).
- **Pinned** compatibility date. Bumps go to sandbox first (C41). Emulator versions are pinned too (the miniflare `latest` tag is an alpha; C47).
- **Beta policy (OD-14 input, DR-C1-5):**

  | Feature | Status | Used? | Fallback |
  |---|---|---|---|
  | Rust Workers | Beta | No | — |
  | Workers VPC | Beta | No (rejected) | — |
  | D1 read replication | Beta | No | — |
  | Gradual deployments | GA | No (by choice) | — |
  | Temp-credential action scoping (local JWT) | Documented; "API support coming soon" | Yes (homelab, server-side) | Offline break-glass token: **documented; test pending** (H13 plus a drill) |
  | Email Service | Beta | C3's call | C3 |

### F11. Load-bearing limits list (verified 2026-10-06 unless noted)

| Limit | Value | Claim | Bites where |
|---|---|---|---|
| Presigned URL expiry | 1 s – 7 days | K3 | BUD-REVOKE |
| Presign host | S3 domain only | K3 | Hostname pinning |
| Same-key write rate | 1/s, then 429 | C18 | Key layout |
| Parts | 5 MiB – 4.995 GiB, ≤ 10,000, equal except last | C9, C19 | B6 part policy |
| Default multipart abort | 7 days; extension probably impossible | K6 | Segment checkpoint (F3) |
| Lifecycle deletion lag | typically ≤ 24 h, may be longer | K6 | Restore bucket |
| R2 REST API | 1,200 req / 5 min per account | C18 | Kept off the hot path |
| Token permission propagation | up to 1 min; roll semantics undocumented | K8 | Kill switch (H11) |
| Temp credential | one bucket; max TTL undocumented | K7 | Two homelab credentials |
| Workers CPU | 30 s default, 5 min max (Paid) | C21 | Presign windows |
| Request body | 100 MB Free/Pro zone | K13 | Records via Worker |
| D1 per DB | 10 GB (fixed), single thread, 100 params, 1,000 queries/invocation | K1, C25 | F2, F6 |
| DO per object | ~1,000 req/s soft, 10 GB | C30 | Fallback |
| Cron CPU | 30 s (< 1 h interval) | C23 | Jobs |
| Time Travel / PITR | 30 days | C28 | C8 |

### F12. Short URLs vs OS background queues (re-scoped; K15 contested)

| Option | Revocation | Works on | Verdict |
|---|---|---|---|
| A. Re-sign just in time (app code runs before the transfer) | ≤ 15 min kept | Desktop daemon, Android WorkManager | **Default for v1 platforms** |
| B. Re-sign after the *specific* expired-URL error | ≤ 15 min kept | All, as a safety net | Always on, with a cap (below) |
| C. Longer URLs for one platform | Weakened | iOS | DR-B4-2 (owner) |
| D. Worker-proxied small parts | Checked at send | All | Fallback; 100 MB body cap (K13) |
| E. Foreground-created non-discretionary tasks; `earliestBeginDate` + `willBeginDelayedRequest` swap (B4 P6, documented only for delayed-start tasks) | ≤ 15 min kept | iOS | Candidates for B4-S2 evidence |

- **For iOS, A does not apply and B can loop.** The URL is fixed at hand-off. Each re-enqueue from the background is discretionary again. A failed attempt may upload a whole part before R2 answers 403, which wastes metered data. So "15-minute URLs suffice" is claimed **for desktop and Android only**. The API supports every option, and the iOS policy is DR-B4-2 with B4-S2 evidence.
- **Client rules:**
  - Re-sign only on the expired-URL error code recorded by real C1-S1 H10 (Miniflare's 403 `ExpiredRequest` proves nothing about R2). Never re-sign on every 403.
  - At most 3 re-signs per part per hour (proposed value; B6 tunes it), with jittered backoff.
  - Repeated failures become a health problem reported to the owner.
  - The C1-S1 kit should also check whether R2 honours `Expect: 100-continue`, so an expired URL is refused before the body is sent (hand-off).
- `POST /v1/uploads/{id}/urls` returns fresh URLs for the **same keys and UploadId**. It is idempotent and refused for revoked devices and for uploads that are no longer open.

### Skeptic issues and how they were handled

| Issue (severity, lens) | Handling |
|---|---|
| Batching does not reduce D1 single-thread time (major; sources, logic, adversary) | **Fixed.** K2 contested and withdrawn as stated. F2 restates capacity as unmeasured, adopts set-based statements, adds the S_sat formula, and adds a per-statement vs per-row measurement to the C1-S2/S3 kits (hand-off). D1 confidence lowered to medium-low. |
| Write-path arithmetic undercounts and leaves no headroom (major; adversary; logic) | **Fixed.** Recomputed with C4's w = 6; headroom expressed as the saturating mean file size (≈ 1.9 MB); reads and homelab writes listed as extra load; E1 and A0 replace the assumptions. |
| `exports` disables gradual deployments for the whole Worker (major; sources; minor, logic) | **Fixed.** DOs move to the `rq-gate` Worker; v1 uses no gradual deployments; expand/contract is grounded in the non-atomic migrate/deploy gap; C43 wording corrected; version affinity noted. |
| Key layout cannot hold packed objects (major; logic) | **Fixed.** `pack/<upload_id>/s<n>` reserved in `rq-ingest`; dependency on A2/A4 recorded in DR-C1-2. |
| iOS re-sign claim overstated (major, logic; minor, sources; K15) | **Fixed.** F12 re-scoped to desktop and Android; options E added; capped, error-specific re-sign; `Expect: 100-continue` check handed to the kit. |
| No cost backstop for a never-expiring staging bucket (major; adversary) | **Fixed** in design: staged-bytes accounting, cap, presign pause on a stale heartbeat, billing notifications (F4). Refusal policy → DR-C1-7 / OD-20. |
| Kill switch and break-glass unwritten and untested (major; adversary; minor, logic) | **Partly fixed.** BUD-REVOKE now stated as not depending on the kill switch; roll semantics marked unknown; two-token split handed to C2/D3 as a proposal; DR-C1-5 says "test pending". **Open:** the timed roll and break-glass drain steps must be added to the C1-S1 kit and the C8 runbook before Gate B (hand-off; the synthesizer does not edit kits). |
| 7-day abort probably cannot be extended (major; adversary; minor, sources and logic) | **Fixed.** Earliest-wins is the planning default; the segment checkpoint is primary; H8b proposed; lag wording quoted exactly. |
| Per-part SHA-256 under-explored (minor; sources) | **Fixed.** H15 proposed; homelab verification stays the safety basis. |
| Presence-check cost rests on emulated `rows_read`; no D1 growth plan (minor; sources, adversary) | **Fixed.** Scan-case cost stated; kit to record `rows_read` and the query plan; retention table and size alerts added (F2, F6, F9). |
| Sources wrongly reported as blocked (minor; sources) | **Fixed.** RFC 9457, the Idempotency-Key draft and RFC 9110 re-read via WG/httpwg raw copies (S48–S50). This changed the `update_required` status to 400. |
| Binding conditional-complete result mislabelled (minor; sources) | **Fixed** in F4; the real H2 test must use the S3 API (hand-off). |
| In-Worker timings are not production CPU (minor; sources; logic) | **Fixed.** C1-S4 is reported as indicative only; the kit's dashboard/Workers Logs `cpuTime` is the only accepted measurement; the "needs Workers Paid" inference is dropped (Paid is needed anyway, C4). |
| C1-S2 "pass" over-reads emulation (minor; logic, adversary) | **Fixed.** Relabelled "pass (emulated, logic only)". |
| F8 lacks C1-S5's conditions; 426 semantics (minor; logic) | **Fixed** (F8). |
| Records path R2/D1 non-atomic (minor; logic) | **Fixed.** Hash-compare retry semantics in F4; handed to A3. |
| Conditional Complete argued from the wrong risk; CopyObject not discussed (minor; logic) | **Fixed** (F4 step 5). |
| DR-C1-5 claimed a "tested" fallback (minor; logic) | **Fixed.** "Documented; test pending". |
| "403 means re-sign" can loop (minor; adversary) | **Fixed** (F12 client rules). |
| No retry-storm handling (minor; adversary) | **Fixed.** Jittered backoff in F8; homelab-priority brake handed to C2. |
| Two parent tokens give limited isolation (minor; adversary; logic) | **Fixed.** Purpose stated as operability only; handed to C2/D3. |
| Missed alternatives: N D1 databases; set-based writes; separate DO Worker; version affinity; Queue push consumer; D1 location hint; desktop temp credentials | Adopted: the first three (F2, F10). Noted: version affinity (F10), Queue push consumer (DR-C1-3 option D), location hint (F2, kit). Kept parked: desktop temp credentials (Q17). |
| Conflicts with settled text: append-only at staging; ADR-0001 §1 Queues; ADR-0001 §4; ownership of token scoping and the config key | Recorded under Conflicts with settled text; DR-C1-6 added; ownership hand-offs to C2/D3/D5. |

### Alternatives compared

| Option | Fit with settled requirements | Pros | Cons | Evidence |
|---|---|---|---|---|
| **One D1 + set-based writes, fallback ladder (recommended, provisional)** | Fits ADR-0001 ("D1 / Durable Objects") | Tooling, Time Travel, export | Capacity unmeasured | K1, C24, C54; K2 contested |
| Several D1 databases from the start | Fits | Headroom by construction | More bindings and migrations | C54 |
| Sharded SQLite DOs | Fits | Horizontal | Custom migrations and PITR | C28, C30 |
| KV existence cache | Fits | Cheap reads | Eventually consistent | PLAN |
| **Feed polling + listing (recommended)** | Amends the ADR-0001 §1 mechanism | No CF token at home, no REST limit | Seconds of latency | F5 |
| Queue push consumer → feed (option D) | Closer to ADR-0001 wording | Server-side staged signal | Queues cost, dropped messages | F5 |
| Queues pulled over HTTP | Fits ADR-0001 wording | Push-ish | Token at home, REST lockout, loss modes | A3 |
| Workers VPC push | **Breaks** outbound-only intent | Instant | Cloud calls into the homelab; Beta | K11 |
| **Presigned per-part URLs, ≤ 15 min (recommended)** | Fits | Plain HTTP | Window calls; create-only unproven | K3, F4 |
| Content through the Worker | Fits | `onlyIf`, sha256 | 100 MB body cap; availability coupling | K13 |
| **Homelab temp credentials (proposal)** | Fits | No long-lived secret at home | Depends on Worker; "coming soon" API | K7 |
| Homelab long-lived token | Fits | Independent of Worker | No prefix or delete scoping | K7 |
| **TypeScript Worker (recommended)** | Fits | GA, native crypto | Small formats twice | K9 |
| Rust `workers-rs` | Fits | One implementation | Beta, pre-1.0, nightly | K9 |
| **No gradual deployments; DOs in a separate Worker (recommended)** | Fits | One version at a time | No canary | K10 |

### Similar work and lessons

| Project | What they do | Borrow or avoid | Source |
|---|---|---|---|
| Ente museum | Random per-upload keys; ≤ 50 URLs per call; presigned Complete; temp-object table with sweeper | **Borrow** per-upload keys and the temp-object table | S44 |
| Immich bulk upload check | Per-item ACCEPT/REJECT with reason | **Borrow** typed per-item results | S44 |
| restic rest-server | Append-only, 403 on existing blob | **Borrow** create-only; equal-content retry = success (as in F4 records) | S44 |
| Headscale pre-auth keys | Prefix + hash, expiry | **Borrow** for invites/codes | S44 |
| Cloudflare temp-credential example | jose + aws4fetch local minting | **Borrow** for homelab credentials | S4 |

### Tools and libraries

| Name | Purpose | Licence | Maturity | Source |
|---|---|---|---|---|
| wrangler | Deploy, D1 migrations, local dev | MIT OR Apache-2.0 | 4.148.0 (2026-10-06); spikes pinned 4.143.0 | C47, S51 |
| miniflare / workerd | Local emulation (**emulated, not Cloudflare**) | MIT / Apache-2.0 | 5.20261006.0-alpha; spikes pinned 5.20260926.0-alpha / 1.20260926.1 | C47, S51 |
| hono | Router | MIT | 4.13.13 | C47 |
| chanfana | OpenAPI from Hono routes | MIT | 3.4.0 | C47 |
| zod | Schemas (≥ 4.5; strip mode for requests) | MIT | 4.6.5 | C47, C1-S5 |
| drizzle-orm / kysely | Query layer (pick one in build) | Apache-2.0 / MIT | 0.45.3 / 0.29.6 | C47 |
| aws4fetch | SigV4 presign | MIT | 1.0.20 (2024-08-28; small, vendorable) | C36 |
| jose | JWT for temp credentials | not checked | not checked | S4 |
| @cloudflare/vitest-pool-workers | Tests in workerd | MIT | 0.22.0 | C47 |

## Spikes

No sandbox account exists (H5 L01). Every Cloudflare result below is **emulated, not real R2/Cloudflare**, and cannot settle a hypothesis about Cloudflare. Each SB spike has a real-sandbox kit.

| Spike | Hypothesis | Pass → / fail → (decision) | Exec tag | Budget IDs | Data class | Status | Result |
|---|---|---|---|---|---|---|---|
| C1-S1 | H1–H14 (kit), plus proposed H8b and H15 | H1/H12 pass → sign create-only as defence in depth; fail → per-upload keys + homelab verification (already the design). H8 fail (expected) → segment checkpoint primary. H11 → kill-switch usability. H13 fail → long-lived homelab token | SB (kit); emulated subset run as CT | BUD-REVOKE | `SYN → results` | **Emulated; kit-ready** | Inconclusive. Miniflare 5.20260926.0-alpha, 3 runs, same verdicts. Signer works: aws4fetch signs `if-none-match`, `content-md5`, `content-length`, `x-amz-checksum-sha256`. Presigned PUT + `If-None-Match: *`: 200 then 412, original kept; dropped header 403 (H1, emulated). Binding `onlyIf` wildcard refused the existing key in both forms (H12). Binding sha256 mismatch threw, nothing stored. Binding `complete()` overwrote, because it has no conditional form (documented; not an H2 result). Presigned POST Create/Complete accepted (H3, Miniflare). Tampered part with signed MD5 → 400; dropped MD5 → reset or 500. Content-Length shorter 403, longer 500. Signed SHA-256 ignored, tampered body stored (H6 fail in Miniflare). Object ETag formula holds; part ETags not MD5. Expiry checked at arrival (H10). H8, H9, H11, H13, H14 not emulable. Evidence: [`spikes/C1-S1/README.md`](../../spikes/C1-S1/README.md), `results/miniflare.json`, `results/miniflare-run1-2026-10-06T1658Z.json`; kit [`docs/research/kits/C1-S1/`](kits/C1-S1/README.md) |
| C1-S2 | 50 concurrent leases × 10,000 trials (1,000 takeover races): exactly one winner; D1 single-batch conditional INSERT vs 16 DO shards with `transactionSync` | Pass → the lease SQL is correct in both stores; store choice by C1-S3/real latency. Fail → fix the lease SQL | CT (emulated) / SB (kit) | — | `SYN → results` | **Pass (emulated, logic only); real D1/DO pending (kit)** | D1: winners {1: 10000}, 0 bad trials, 0 duplicate live leases, 0 errors over 500,000 requests; local p50 155.7 / p99 372.9 / max 788.5 ms. DO: {1: 10000}, 0 bad, 0 duplicates; p50 46.7 / p99 213.3 / max 452.6 ms. Container load average 4–6; latencies say nothing about Cloudflare. Evidence: [`spikes/C1-S2/README.md`](../../spikes/C1-S2/README.md), `results/miniflare-d1.json`, `results/miniflare-do.json`; kit [`kits/C1-S2/`](kits/C1-S2/README.md) |
| C1-S3 | 1,000-ID presence check (half present) on a 5M-row index via one `json_each` statement: p99 < 500 ms and < $1 per million IDs | Pass → D1 for dedup; fail → fallback ladder (F2) | SB (kit); emulated run as CT | BUD-CLOUD | `SYN → results` | **Emulated; inconclusive; kit-ready** | Local SQLite, 5,000,000-row WITHOUT ROWID table, 200 calls per shape. `json_each`: 200/200 correct; client p50 13.5 / p99 26.0 ms; `meta.duration` p50 5.0 / p99 10.0 ms; `rows_read` 1,500/call; PK SEARCH per ID. `in100`: p50 16.0 / p99 28.5 ms. About $0.002 per million IDs **from emulated `rows_read`** (indicative). The latency criterion has no result. Evidence: [`spikes/C1-S3/README.md`](../../spikes/C1-S3/README.md), `results/miniflare-5M.json`; kit [`kits/C1-S3/`](kits/C1-S3/README.md) |
| C1-S4 | Presign 200 UploadPart URLs in one request within Paid CPU; URLs work from curl; Ed25519 verify < 1 ms CPU | Pass → windowed presign as designed; fail → smaller windows | SB (kit); emulated run as CT | BUD-CPU-REQ | `SYN → results` | **Emulated; inconclusive; kit-ready** | Local workerd + Node micro-benchmark, shared Xeon container. 200 unique URLs per call (longest 515 chars, 103,742-byte response); in-Worker local time p50 22.0 / p99 183.9 ms (n = 50); Node CPU p50 38.8 / max 77.3 ms (n = 30). curl PUT to parts 1, 2, 200 → 200; completed object 10,486,537 B. Ed25519 verify 0.055–0.079 ms (local workerd), 0.159–0.203 ms CPU (Node). **Not Cloudflare CPU accounting**; in-Worker timers do not measure CPU in production. Only the kit's dashboard/Workers Logs `cpuTime` counts. Evidence: [`spikes/C1-S4/README.md`](../../spikes/C1-S4/README.md), `results/miniflare.json`, `results/cpu-bench-node.json`; kit [`kits/C1-S4/`](kits/C1-S4/README.md) |
| C1-S5 | Additive v2 change invisible to an old client; breaking change → machine-readable `update_required` | Pass → F8 rules; fail → stricter versioning | CT (ran for real; contract test, no Cloudflare) | — | `SYN → results` | **Pass, with two conditions** | Hono/zod toy under local `wrangler dev`, Rust v1.2.0 client; byte-identical rerun at 20:20Z. Added fields: OK. New enum value: DECODE_ERROR on HTTP 200 (closed enum), OK (tolerant). Ungated rename: DECODE_ERROR on 200 for both. Gated break: `update_required`, `min_version` 2.0.0 (sent as 426; the spec now uses 400, F8). `.strict()` request schema rejects a newer client's extra field (400); zod default strips it. Conditions: tolerant enums or gated additions; `min_version` raised with every breaking change. Evidence: [`spikes/C1-S5/README.md`](../../spikes/C1-S5/README.md), `results/client-matrix.jsonl`, `results/client-matrix-rerun-2026-10-06T2020Z.jsonl`, `results/server-side.txt` |

**Proposed kit additions (for the spike runner; the synthesizer does not edit kits):**
- **C1-S1:**
  - **H8b:** list and try to remove or replace the default abort rule.
  - **H15:** presigned UploadPart with signed `x-amz-checksum-sha256` and a tampered body; COMPOSITE completion with per-part checksums.
  - **H2** via the S3 API, not the binding.
  - **H10:** record the exact expired-URL error, and whether `Expect: 100-continue` is honoured.
  - **H11:** a timed *roll* of the device-signing token, including the Worker secret update, and the family-wide outage it causes.
  - **A break-glass drain drill** with the offline token.
  - Fix the T35 → T54 lifecycle reference in `spikes/C1-S1/README.md`.
- **C1-S2/S3:** per-statement vs per-row `meta.duration` for single, batch-of-N and set-based inserts (N = 1, 100, 1,000); real `rows_read` and `EXPLAIN QUERY PLAN`; a D1 location hint.
- **C1-S4:** `cpuTime` from Workers Logs as the only accepted measurement.

## Conflicts with settled text

- **ADR-0001 §1** names Queues as the notification path. DR-C1-3 proposes a Worker feed (option B), or option D, which is closer to the wording. Either way an "Amends: ADR-0001 §1" note is needed if the owner accepts. ADR-0010 does **not** adopt the feed as settled until the owner decides.
- **ADR-0001 §4** (dedup-ID keys, exclusive claim): superseded in substance by per-upload keys and advisory leases. This stays with **OD-04** and is not decided in ADR-0010.
- **CLAUDE.md "devices can only append backups, never delete or rewrite them":** not violated for committed history. But until real C1-S1 H1 passes, a reusable presigned PUT lets a device, or anyone holding a leaked URL, **rewrite its own staged, not-yet-committed object** within the URL window (≤ 15 min, renewable by re-sign while the upload is open). Homelab verification detects it (SR-04), and the upload is redone. ADR-0010 states that append-only is **enforced at commit, not at staging**. The owner is asked to confirm that interpretation (DR-C1-6) rather than have it silently assumed.
- **Ownership (PLAN §2.1, C2, D3, D5):** homelab token scoping and rotation belong to C2; revocation and the kill switch to D3 (ADR-0014); the bootstrap config key to D3/D5. ADR-0010 marks the two-token split, the temp-credential scopes and the config key as **proposals handed over**, not decisions.
- **ADR-0001 §6** (expiring `restore/` prefix): kept, in its own bucket.

## Open questions

| # | Question | Who | By when |
|---|---|---|---|
| 1 | C1-S1 H1–H15 and H8b on real R2 | Spike runner, sandbox (L01) | Gate B |
| 2 | Real D1 cost per statement vs per row; utilisation at E1's file-size mix; real `rows_read` and query plan | C1-S2/S3 kits; E1; A0 | Gate B |
| 3 | Roll semantics of R2 parent tokens; family-wide outage during a roll; break-glass drill | C1-S1 H11, C8, D3 | Gate B |
| 4 | Is the local-signing JWT format stable? Max temp-credential TTL? Will action scoping reach the API? | T2 watch list; H13 | Gate B |
| 5 | Does any platform need URLs longer than 15 min? iOS options (F12 E) | B4-S2, DR-B4-2, D3 | Wave 2 |
| 6 | Request-auth construction; any KDF Web Crypto lacks; BUD-CPU-REQ on real Cloudflare CPU | D3 (ADR-0014), C1-S4 kit | Gate C |
| 7 | Second bootstrap location; config-key custody; whether bootstrap signing reuses the update root | Owner (DR-C1-4), D3, D5 | Gate C |
| 8 | Packed uploads (IOS-C16): used or not | A2/A4 | Gate A |
| 9 | Staging cap value and refusal policy | Owner (OD-20, BUD-CLOUD), C2, C4 | Wave 2 |
| 10 | Idempotency-Key draft publication status (only `-latest` editor's copy read) | H1 / T2 | Before ADR-0010 is accepted |
| 11 | Queues pull REST rate limits (not documented on the pages read) | Only if DR-C1-3 picks A | — |
| 12 | Whether bucket locks block the default abort or in-progress uploads | C1-S1 H9 | Gate B |
| 13 | Exact per-device counters: DO vs D1 vs Rate Limiting binding | C2 | Wave 2 |

## Recommendation

Adopt for the ADR-0010 draft (Proposed):

- **Topology:**
  - TypeScript `rq-api` Worker on `api.<owner-domain>`, with `workers_dev = false` and Preview, Version and Deployment URLs handled.
  - One D1 database, **provisionally**, behind a data-access layer, with set-based writes and the F2 fallback ladder.
  - DO counters, if C2 wants them, in a separate `rq-gate` Worker.
  - Two R2 buckets, with `pack/` reserved.
  - One Cron Trigger.
- **Uploads:**
  - Presigned PUT/UploadPart in windows of ≤ 15 min with explicit `X-Amz-Expires`.
  - Create and Complete in the Worker, with no condition on Complete.
  - A re-sign endpoint with capped, error-specific client rules (desktop and Android; iOS open).
  - Records through the Worker with create-only `onlyIf` and hash-compare retries.
- **Guard rails:** staged-bytes cap and presign pause on a stale heartbeat (policy via OD-20); D1 retention and size alerts.
- **Homelab:** polls the Worker feed and reconciles by listing (pending DR-C1-3). The Ed25519 control key, temp credentials and two parent tokens are proposals for C2/D3.
- **Opaque-artifact rule;** F8 API conventions including the C1-S5 rules and 400 `update_required`.
- **Change management:** no gradual deployments; expand/contract; pinned compatibility date; separate accounts.
- **Safety basis:** per-upload keys plus homelab verification. R2 conditionals only after the real kit passes. Miniflare results are never evidence about R2.

**What would change this:**
- Real-D1 utilisation above ~50 % at the E1 mix → fallback (a), then (b).
- H13 fail → long-lived homelab token.
- H8b shows the default abort can be removed → simpler long uploads.
- H1/H15 pass → sign create-only and checksums in.
- The owner picks DR-C1-3 A or D → Queues in v1.
- D3 needs a KDF Web Crypto lacks → one Wasm module.

## Decision requests

### DR-C1-1: Worker language: TypeScript with the opaque-artifact rule (H1 to number)
- **Needed by:** Wave 1 exit
- **Evidence:** F7; K9 (verified)
- **Options:** A. TypeScript (Hono), formats twice with shared vectors. B. Rust `workers-rs` (Beta, pre-1.0, nightly for unwind). C. TS shell + Rust→Wasm for named functions.
- **Recommendation:** A, keeping C for any function Web Crypto cannot do.
- **Touches settled text:** none.
- **If no decision by the deadline:** the A0 skeleton uses A.

### DR-C1-2: Two R2 buckets, ingest never expires, `pack/` reserved (one-way door #7)
- **Needed by:** Gate B
- **Evidence:** F3; K6, K7 (verified)
- **Options:** A. One bucket with prefix lifecycle rules. B. `rq-ingest` (no Expiration ever; `staging/`, `meta/`, reserved `pack/`) + `rq-restore` (expiring).
- **Recommendation:** B. "Staging never expires by age" becomes a checkable property, and tokens can separate restore from ingest. Depends on A2/A4's packing decision only for whether `pack/` is used.
- **Touches settled text:** none.
- **If no decision by the deadline:** the skeleton uses B.

### DR-C1-3: v1 notification path (amends the mechanism named in ADR-0001 §1)
- **Needed by:** Wave 1 exit (OD-04 sitting), before A0 fixes the homelab puller
- **Evidence:** F5; A3 C3–C7
- **Options:** A. R2 notifications → Queues → HTTP pull (ADR-0001 wording). B. Worker feed polled about every 30 s, plus listing. C. DO WebSocket push. D. R2 notifications → Queue → push consumer Worker → the same feed.
- **Recommendation:** B. No Cloudflare API token at home, no REST lockout, no Queues loss modes; reconciliation stays the path of record. D if the owner wants to stay closer to ADR-0001's wording.
- **Touches settled text:** ADR-0001 §1; needs an "Amends: ADR-0001 §1" draft if B or D is chosen.
- **If no decision by the deadline:** the skeleton uses B as a throwaway choice; ADR-0010 stays Proposed.

### DR-C1-4: API hostname and bootstrap (one-way door #8)
- **Needed by:** Gate C (the domain is needed earlier for the sandbox)
- **Evidence:** F8; K3, K12 (verified)
- **Options:** A. `api.<owner-domain>` only. B. A plus a second bootstrap host on a different domain **and provider**, serving an offline-signed bootstrap document with no trust material (SR-31). C. `workers.dev` (rejected by PLAN).
- **Recommendation:** B. An active Cloudflare zone puts DNS and the API on one account, so the second location should be elsewhere.
- **If no decision by the deadline:** the sandbox uses its throwaway domain; Gate C stays blocked.

### DR-C1-5 (input to OD-14): beta and "coming soon" dependencies
- **Needed by:** OD-14 sitting
- **Evidence:** F10
- **Options:** A. Accept the rule "only with a documented, tested fallback that needs no client update" and the F10 classification. Temp-credential action scoping is used server-side only, with a break-glass fallback that is **documented; test pending** (H13 plus a drill, Gate B exit item). B. No beta or "coming soon" dependencies: the homelab uses a long-lived bucket token.
- **Recommendation:** A, on condition that the drill passes before Gate B. If it does not, B applies automatically.

### DR-C1-6 (input to OD-04 and OD-17): what "devices can only append" means at the staging layer
- **Needed by:** Gate B
- **Evidence:** K3 (bearer URLs, verified); emulated C1-S1 (not evidence about R2); SR-04, SR-07
- **Options:**
  - A. Confirm: append-only is enforced at **commit**. Until real H1 passes, a URL holder can rewrite one uncommitted staged object within its window; the homelab detects it and the upload is redone. Record it as an accepted risk (OD-17).
  - B. Require create-only at staging: content goes through the Worker (100 MB body cap; availability coupling) or waits for R2 create-only to be proven.
- **Recommendation:** A. No committed data is at risk, and B costs much more.
- **Touches settled text:** interprets CLAUDE.md "Connectivity"; does not change it.

### DR-C1-7 (input to OD-20 and BUD-CLOUD): refuse uploads at a staged-bytes cap
- **Needed by:** Wave 2 (OD-20 sitting)
- **Evidence:** F4; C4 staging-cap derivation
- **Options:** A. The Worker refuses new uploads above a cap (C4: ≈ 1.3 TB at a $25 BUD-CLOUD) and pauses presign when the homelab heartbeat is stale, with the C4 plain-language message. B. Alerts only; staging grows until the owner acts.
- **Recommendation:** A, with the cap value set by the owner.
- **If no decision by the deadline:** the mechanism is built; the cap is set to "alert only".

## Hand-offs

| To | What | Why |
|---|---|---|
| Spike runner (C1-S1..S4 kits) | H8b, H15, H2 via the S3 API, H10 error code and `Expect: 100-continue`, a timed token roll with secret update, a break-glass drill, per-statement vs per-row D1 timing, real `rows_read` and query plan, location hint, `cpuTime` only; fix T35 → T54 in `spikes/C1-S1/README.md` | Skeptic issues |
| A3 | Records retry semantics (hash compare); `pack/` key form; the segment checkpoint is primary for > 7-day uploads; feed polling (pending DR-C1-3) | F3, F4 |
| A2 / A4 | Packing decision (IOS-C16) before Gate A; `pack/` reserved | F3 |
| A1 | ID text encoding length (keys) | F3 |
| C2 | `rq-gate` counters; two-parent-token proposal; homelab credential scopes; homelab-priority brake; staged-bytes cap enforcement; billing notifications; Deployment URLs in hardening | F1, F4, F5 |
| C4 | Staged-bytes cap mechanism; utilisation formula S_sat = B·w·t for the cost model; feed instead of Queues | F2, F4 |
| C7 / C8 | Dead-man's switch; nightly export; retention table; break-glass runbook and drill; clients must not pin the R2 host | F5, F6, F9 |
| D2 / D3 / D5 | Homelab control key; config-signing key; R2 parent secrets; request-auth format; roll semantics in the revocation design | F4, F5, F8 |
| B2 / B4 / B6 | Re-sign client rules with caps; iOS options E for B4-S2; part/segment sizing under a hard 7-day ceiling | F3, F12 |
| G2 | Vectors for request auth, code hashing and ID-encoding checks; contract test against the previous client build; enum catch-all vector | F7, F8 |
| H1 | Blocked-source list corrected (RFC texts reachable via WG raw copies); DR-C1-1..7 to number; ADR-0010 registry row → Proposed | Method |
| T2 | Watch: temp-credential local-signing format, conditional Complete, D1 single-thread guidance, Idempotency-Key draft status | F10 |
