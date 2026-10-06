# C1. Cloudflare control-plane mapping and API v1

- **Workstream:** C1 (see `docs/research/PLAN.md`, section "C1.")
- **Status:** Draft (analyst deep read, Wave 1, batch W1-b). Not yet under skeptic review. Spike results pending: a separate spike runner is running the C1 spikes and writing the C1-S1 kit in parallel.
- **Date:** 2026-10-06 (scout sweep 2026-09-29; analyst re-reads 2026-10-06). The run brief gives 2026-09-29 as "today", but the container clock and the npm registry timestamps show 2026-10-06, so access dates below use 2026-10-06 where the analyst re-fetched.
- **Feeds:** ADR-0010 (reserved; the draft and `docs/design/api-v1.md` are the next stage), one-way door #7 (R2 key layout, Gate B) and #8 (API hostname and bootstrap endpoint, Gate C), OD-04 (C1-S1 evidence), OD-14 (beta-feature policy section), new decision requests DR-C1-1 to DR-C1-5 below (H1 assigns OD numbers)
- **Depends on:** A3 (`a3-ingest-protocol.md`, draft: per-upload keys, advisory lease, reconciliation, receipts), D1 (`d1-threat-model.md`, draft: SR-01…SR-26), CE spike (`content-encryption-format.md`: staging and `meta/` keys), C4 (`c4-cost-model.md`: unit prices and per-file operation assumptions), T2 (`fact-check-adr-0001-0002.md`), H1 sandbox (L01, not yet available)
- **Traceability rows advanced:** R-09, R-11, R-12, R-13, R-18, R-37, Q1-3 (presigned UploadPart, with C1-S1), C-01 (warm cache; proposal below)

## Summary

Recommended topology, in one line: **a TypeScript Worker on the owner's own domain, one D1 database as the control-plane system of record, two R2 buckets (ingest with no expiry rules at all, and restore with an expiry rule), presigned per-part URLs for content, records posted through the Worker, a Worker event feed that the homelab polls, R2 listing as the path of record, and Cron Triggers for background jobs.** Durable Objects are kept for what only they do well (exact per-device counters for C2, and later a push channel), not as the main store.

1. **D1 over Durable Objects for state, because the protocol no longer needs a strong lock.** A3 made the claim an advisory lease, so the D1-vs-DO choice is about throughput and operations, not correctness. D1 is single-threaded per database (C27), but arithmetic at family scale stays well inside its guidance *if every API request does one D1 `batch()`*, however many items it carries. D1 wins on operability: numbered migrations, Time Travel restore from the CLI, `wrangler d1 export`, ad-hoc SQL. C1-S2 and C1-S3 measure the ceiling; the fallback is to shard the dedup and lease tables into SQLite-backed DOs.
2. **Key layout: per-upload keys, and the ingest bucket gets no Expiration rule at all.** Restores go to a separate bucket whose objects expire. "Staging never has an age-based expiry" is then a property of the bucket, not of a prefix rule someone can mistype. The only age-based removal left in the ingest bucket is R2's default 7-day abort of *incomplete* multipart uploads. That never removes a staged object, and A3 handles slow uploads.
3. **Worker language: TypeScript.** Rust on Workers is labelled Beta, `workers-rs` is pre-1.0, and panic recovery needs a nightly toolchain (C32–C35). The cost of TypeScript is that a few small formats get a second implementation: request authentication, code hashing and ID encoding. That stays small only under one design rule: **the Worker never parses a Reliquary cryptographic artifact.** Records, receipts, manifests and envelopes are opaque bytes to it.
4. **What R2 itself enforces is still mostly undocumented.** That covers create-only on presigned PUT and on multipart completion, signed Content-Length, Content-MD5 and checksums, and lifecycle extension past 7 days. C1-S1 must settle these. Nothing in this design depends on a positive result: per-upload keys plus homelab verification are the safety net (SR-07, SR-04). The R2 conditionals only reduce cost and nuisance.
5. **New option found:** R2 **temporary credentials** can be scoped to one bucket, an explicit S3 action list and exact keys or prefixes, and a Worker can mint them locally (C10, C11). They are the best fit for the **homelab's** R2 access: read, list and delete on `staging/` and `meta/` only, write on `restore/` only. A long-lived token cannot express that (C12).

Confidence: **high** on the Cloudflare facts (primary docs source, re-read). **Medium** on the topology and language choice: they are reasoned from the docs and from A3/D1, with no measurement yet. **Low** on any R2 behaviour C1-S1 has not yet run.

## Questions

| # | Question | Short answer | Confidence |
|---|---|---|---|
| 1 | D1 vs SQLite DOs vs hybrid for dedup index, claims, device registry, invites, quotas | **D1** for all records. DOs only for exact per-device counters (C2) and an optional later push channel. D1's single thread is not a ceiling at family scale if each request is one `batch()` (F2 arithmetic). Fallback: shard dedup/leases into N DOs by ID prefix. | Medium (arithmetic, not measured) |
| 2 | Is D1's single thread a ceiling during a 25-device seed? | Not by arithmetic: the worst plausible aggregate upload rate gives about 0.5 thread-seconds per second at 5 ms per write query, unbatched. Small-file bursts break this **unless** writes are batched per request. C1-S2/S3 must measure. | Medium |
| 3 | How to shard DOs, if used | Per device (`idFromName(device_id)`) for counters and quotas. Per dedup-ID prefix (e.g. 16 shards on the first hex digit) only if the D1 fallback is triggered. Never one global DO for everything: same single-thread limit as D1, and worse tooling. | Medium |
| 4 | Key layout; one bucket or several | `rq-ingest`: `staging/<dedup_id>/<upload_id>/s<n>` and `meta/<device_id>/<batch_id>.age`. `rq-restore`: `restore/<device_id>/<job_id>/<object_id>`. Two buckets so the ingest bucket never carries an Expiration rule, and so long-lived tokens (bucket-scoped only) and metrics separate cleanly. | Medium-high |
| 5 | Staging expiry vs worst outage; 7-day multipart abort | Ingest bucket: **no Expiration rule**. Orphans are removed only by the homelab (A3 F7). The default 7-day abort touches only incomplete uploads. Whether it can be lengthened is undocumented (C17), so A3's segment checkpoint or the USB fallback covers long uploads. | High (docs); Low (extension, untested) |
| 6 | Which cloud state needs backup | Cloud-only: invites, enrollment tokens and pairing codes (hashed), account and verification state, email suppression list, audit log. Rebuildable from the homelab: committed set, receipt relay, revocation list, device list (if homelab-signed, D3). Disposable: leases, idempotency records, counters, event feed. D1 Time Travel (30 days) covers mistakes, not account loss, so the homelab pulls a nightly export (C8). | Medium-high |
| 7 | Notifications | **Homelab polls a Worker event feed** (cursor over a D1 event log the Worker appends when it accepts a record), plus periodic R2 listing as the path of record. Queues and R2 event notifications are not needed in v1. This touches ADR-0001 §1 wording (DR-C1-3). | Medium |
| 8 | Homelab authentication | To the Worker: requests signed with a homelab control key whose public half is in Worker config. To R2: **Worker-minted temporary credentials**, scoped by action and prefix, TTL ≤ 1 h. Fallback: a long-lived bucket-scoped Object R&W token held offline as break-glass. No Cloudflare REST API token on the homelab. | Medium |
| 9 | Workers VPC / Tunnel push | **Rejected.** It makes the homelab a server for a component the requirements treat as under attack, and it is Beta (C38). | High |
| 10 | Worker language | **TypeScript** (Hono, zod, Drizzle or Kysely, aws4fetch, jose), plus the opaque-artifact rule. Formats implemented twice: request auth, code hashing, ID encoding, API schema, all pinned by shared vectors (G2). Revisit if D3 picks a KDF that WebCrypto lacks (e.g. Argon2): compile that one Rust function to Wasm and import it into the TS Worker. | Medium |
| 11 | CPU and subrequests when presigning hundreds of parts | Presigning makes **no subrequests** (C1). It is local HMAC work, and aws4fetch caches the derived signing key per day (C36). CPU is unmeasured (C1-S4). BUD-REVOKE (15 min) caps the useful window: at 20 Mbit/s, about 2.25 GB fits in 15 min (≈ 134 parts of 16 MiB), so 200 parts per call is the upper end. Presign in windows. | High (no subrequests); Medium (window arithmetic) |
| 12 | API conventions | `/v1/` path, additive-only within v1; typed per-item results in batch calls; `Idempotency-Key` on non-natural-key creates; opaque cursors; RFC 9457-style problem bodies with a stable `code`; `update_required` problem; server-time header; signed bootstrap document. Outline in F8. | Medium |
| 13 | API on the owner's domain | Workers Custom Domain on an **active Cloudflare zone** (C39). Disable both `workers.dev` and preview URLs: disabling `workers.dev` does not disable version URLs (C40). R2 presigned URLs still use `<ACCOUNT_ID>.r2.cloudflarestorage.com` (C2), so clients must not pin that host. | High |
| 14 | Background jobs | One Cron Trigger running idempotent "what is due" queries over D1 state: stale devices, nudges, dead-man's switch, day-6 multipart checkpoint (A3). DO alarms only inside C2's counter DOs. Workflows not needed in v1. | Medium-high |
| 15 | Change management | Expand/contract D1 migrations that are compatible with two Worker versions at once (gradual deployments split traffic per request, C42). DO class changes only by plain `wrangler deploy` (C43). Pinned compatibility date. Separate sandbox and production accounts. Time Travel bookmark taken before each migration. | High (docs); Medium (policy) |
| 16 | Beta dependencies (OD-14 input) | Avoided: Rust Workers, Workers VPC, D1 read replication. Used: none required. Depended on but not labelled beta: temporary-credential local signing (JWT format documented by example; action scoping "API support coming soon"). Email Service (beta) is C3's. | High |
| 17 | (new) Can the device run multipart without the Worker presigning every part? | Yes, with a temporary credential scoped to one key and `UploadPart`/`ListParts` only. But background upload APIs (iOS URLSession, queued Android work) want fully formed requests, so **presigned URLs stay primary**. Temp credentials are kept for the homelab and optionally desktop. | Medium |
| 18 | (new) Records: presigned PUT or through the Worker? | **Through the Worker.** Records are small. The Worker writes them with a create-only `onlyIf`, checks size and quota, and appends the feed event in the same request. This removes the presigned-overwrite question for `meta/` entirely. | Medium-high |
| 19 | (new) Warm cache (C-01 orphan) | v1 default: **off** (window 0). If enabled, it is a homelab-driven delay before deleting committed staging objects, never a lifecycle rule. C4 prices a 30-day warm cache at about $42 vs about $12 for a 2 TB seed month. | Medium |

## Method

- **Sweep:** four scouts ran (docs, source, community issues, pricing/standards). Their JSON findings are the input to this note.
- **Deep read (analyst, 2026-10-06):** re-fetched from `cloudflare/cloudflare-docs @ production` on raw.githubusercontent.com.
  - Read in full: R2 presigned URLs, temporary credentials and its example page, object lifecycles, bucket locks, R2 API tokens, R2 limits, R2 consistency, D1 limits FAQ partial, DO limits FAQ partial, Workers limits, Workers VPC overview.
  - Read in the relevant sections: R2 S3 API table (checksum table, PutObject, UploadPart, CreateMultipartUpload, CompleteMultipartUpload rows); R2 Workers API reference (put options, multipart); R2 release notes; R2 upload-objects (ETags, part sizes); D1 Worker API (`batch()`); D1 query-json (`json_each`); D1 Time Travel; D1 read replication (status badge); DO SQLite storage API (PITR, transactions); DO class lifecycle (migrations); gradual deployments and gradual deployments with DOs; compatibility dates; Cron Triggers; Workflows limits; Workers custom domains; `workers.dev` routing; Web Crypto algorithm table; Rust language page.
- **Source checks:** `cloudflare/workers-rs @ main : README.md`; `worker` crate 0.8.7 source from static.crates.io (`durable.rs`, `sql.rs`, file list); `aws4fetch` 1.0.20 npm tarball (`dist/aws4fetch.esm.mjs`); npm registry and crates.io metadata.
- **Project inputs:** CLAUDE.md, ADR-0001, ADR-0002, A3, D1, CE, C4, `data-model.md`, `budgets.md`, `decision-queue.md`, `one-way-doors.md`, `traceability.md`, `fact-check-adr-0001-0002.md`, `client-stack.md`.
- **Routes used:** raw.githubusercontent.com (vendor doc and source mirrors), registry.npmjs.org, static.crates.io, crates.io API. WebSearch was exhausted (scouts); Context7 was not used.
- **Blocked sources** (none silently replaced; to report to H1):
  - developers.cloudflare.com (mirror used: the docs' own source repo, same content; per-file commit dates not retrieved because the GitHub API is blocked);
  - docs.aws.amazon.com (S3 conditional writes; the AWS reference behaviour R2 emulates);
  - rfc-editor.org and datatracker (RFC 9457 Problem Details, RFC 9110, the Idempotency-Key draft status). RFC 9457 is cited by number only and was **not re-read** in this run.
  - blog.cloudflare.com and cloudflarestatus.com (incident post-mortems);
  - github.com web UI for issue bodies: community claims rest on the community scout's reads.
- **Scout conflicts resolved:**
  1. "D1 is single-threaded" was not found by the source scout. It **is** in `partials/d1/faq-limits.mdx`, re-read in full (C27).
  2. Single-part maximum "5 GiB" vs "4.995 GiB": the table says 5 GiB, and footnote 4 says 5 MiB less, i.e. 4.995 GiB (C19).
  3. Workflows "1,024 steps" vs "10,000 steps": 1,024 is Free, and 10,000 (configurable to 25,000) is Paid (C46).
  4. Worker size "64 MiB" (Workers limits) vs "3 MB/10 MB" (a Workflows limits row): the Workflows row looks stale. Treat 64 MiB as current and re-check if a Wasm bundle ever matters (C44).
  5. Tool versions moved since the scouts: wrangler 4.143.0 → 4.147.0, miniflare 5.20260926.0-alpha → 5.20261001.0-alpha, hono 4.13.11 → 4.13.13 (C47).
- **Contradictions inside primary sources** (recorded, not resolved): conditional CompleteMultipartUpload (C7 vs C8); revocation latency "up to a minute" vs "immediately" (C14 vs C11).
- **Stop rule:** the analyst's re-reads added two primary sources the scouts had not read (the temporary-credentials example page, and the gradual-deployments-with-DOs page). Neither changes the recommendation; both refine it (F4, F10).

## Sources

All Cloudflare docs are `cloudflare/cloudflare-docs @ production : src/content/…`, the source of developers.cloudflare.com, at branch head (commit dates not retrieved).

| # | Source | Publisher | Published or version date | Accessed | Primary? |
|---|---|---|---|---|---|
| S1 | R2 Presigned URLs, `docs/r2/api/s3/presigned-urls.mdx` | Cloudflare | production head | 2026-10-06 (full) | Yes |
| S2 | R2 S3 API compatibility, `docs/r2/api/s3/api.mdx` | Cloudflare | production head | 2026-10-06 (sections) | Yes |
| S3 | R2 Temporary credentials, `docs/r2/api/s3/temporary-credentials.mdx` | Cloudflare | production head | 2026-10-06 (full) | Yes |
| S4 | R2 example "Authenticate against R2 with temporary credentials", `docs/r2/examples/authenticate-r2-temp-credentials.mdx` | Cloudflare | `reviewed: 2026-04-19` | 2026-10-06 (full) | Yes |
| S5 | R2 Authentication (API tokens), `docs/r2/api/tokens.mdx` | Cloudflare | production head | 2026-10-06 (full) | Yes |
| S6 | R2 Object lifecycles, `docs/r2/buckets/object-lifecycles.mdx` | Cloudflare | production head | 2026-10-06 (full) | Yes |
| S7 | R2 Bucket locks, `docs/r2/buckets/bucket-locks.mdx` | Cloudflare | production head | 2026-10-06 (full) | Yes |
| S8 | R2 Limits, `docs/r2/platform/limits.mdx` | Cloudflare | production head | 2026-10-06 (full) | Yes |
| S9 | R2 Consistency model, `docs/r2/reference/consistency.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S10 | R2 Workers API reference, `docs/r2/api/workers/workers-api-reference.mdx` | Cloudflare | production head | 2026-10-06 (sections) | Yes |
| S11 | R2 release notes, `release-notes/r2.yaml` | Cloudflare | latest entry 2026-04-27 | 2026-10-06 | Yes |
| S12 | R2 Upload objects (ETags, part sizes), `docs/r2/objects/upload-objects.mdx` | Cloudflare | production head | 2026-10-06 (sections) | Yes |
| S13 | R2 Event notifications, `docs/r2/buckets/event-notifications.mdx` | Cloudflare | production head | 2026-09-29 (scouts); 2026-10-06 (fetched) | Yes |
| S14 | D1 limits FAQ partial, `partials/d1/faq-limits.mdx` | Cloudflare | production head | 2026-10-06 (full) | Yes |
| S15 | D1 Limits, `docs/d1/platform/limits.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S16 | D1 Worker API, `docs/d1/worker-api/d1-database.mdx` (`batch()`) | Cloudflare | production head | 2026-10-06 | Yes |
| S17 | D1 Query JSON, `docs/d1/sql-api/query-json.mdx` (`json_each` for IN) | Cloudflare | production head | 2026-10-06 | Yes |
| S18 | D1 Time Travel and backups, `docs/d1/reference/time-travel.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S19 | D1 Global read replication, `docs/d1/best-practices/read-replication.mdx` | Cloudflare | production head (Beta badge) | 2026-10-06 | Yes |
| S20 | D1 Migrations, `docs/d1/reference/migrations.mdx` | Cloudflare | production head | 2026-09-29 (scouts) | Yes |
| S21 | DO limits FAQ partial, `partials/durable-objects/do-faq-limits.mdx` | Cloudflare | production head | 2026-10-06 (full) | Yes |
| S22 | DO Limits, `docs/durable-objects/platform/limits.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S23 | DO SQLite storage API, `docs/durable-objects/api/sqlite-storage-api.mdx` (PITR, transactions) | Cloudflare | production head | 2026-10-06 | Yes |
| S24 | DO class lifecycle / migrations, `docs/durable-objects/reference/durable-objects-migrations.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S25 | DO Alarms, `docs/durable-objects/api/alarms.mdx` | Cloudflare | production head | 2026-09-29 (scouts) | Yes |
| S26 | Workers Limits, `docs/workers/platform/limits.mdx` | Cloudflare | production head | 2026-10-06 (full) | Yes |
| S27 | Gradual deployments, `docs/workers/versions-and-deployments/gradual-deployments/index.mdx` and `…/with-durable-objects.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S28 | Compatibility dates, `docs/workers/configuration/compatibility-dates.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S29 | Cron Triggers, `docs/workers/configuration/cron-triggers.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S30 | Workflows Limits, `docs/workflows/reference/limits.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S31 | Workers Custom Domains, `docs/workers/configuration/routing/custom-domains.mdx`; `workers.dev` routing, `…/routing/workers-dev.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S32 | Web Crypto (algorithm table), `docs/workers/runtime-apis/web-crypto.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S33 | Rust language support, `docs/workers/languages/rust/index.mdx` (Beta badge) | Cloudflare | production head | 2026-10-06 | Yes |
| S34 | `cloudflare/workers-rs @ main : README.md` | Cloudflare | main head | 2026-10-06 | Yes |
| S35 | `worker` crate 0.8.7 source (static.crates.io) and crates.io API | Cloudflare / crates.io | 0.8.7, updated 2026-09-25 | 2026-10-06 | Yes |
| S36 | `aws4fetch` 1.0.20 npm tarball, `dist/aws4fetch.esm.mjs` | M. Hart (npm) | 1.0.20, 2024-08-28 | 2026-10-06 | Yes |
| S37 | Workers VPC overview, `docs/workers-vpc/index.mdx` (Beta badge) | Cloudflare | production head | 2026-10-06 | Yes |
| S38 | Queues pull consumers and limits, `docs/queues/configuration/pull-consumers.mdx`, `docs/queues/platform/limits.mdx` | Cloudflare | production head | 2026-09-29 (scouts; A3 read in full) | Yes |
| S39 | npm registry metadata: wrangler, miniflare, hono, aws4fetch, @cloudflare/vitest-pool-workers, drizzle-orm, kysely, chanfana, zod | npm | as listed in Tools | 2026-10-06 | Yes |
| S40 | Project notes: A3, D1, CE, C4, `data-model.md` | Project | drafts, 2026-09-29 to 2026-10-06 | 2026-10-06 | Yes (project) |
| S41 | workerd #2572 (R2Conditional wildcard parsed as strong etag), #6561 (DO RPC/fetch ordering), #7190 (alarm under in-memory storage crashes workerd) | Cloudflare repo, users | 2024-08-21; 2026-04-11; 2026-08-30 | 2026-09-29 (community scout) | No |
| S42 | workers-sdk #14916 (local D1 SQLITE_BUSY crashes `wrangler dev`), #15774 (D1 migrations 403/7403), #15387 (versions upload vs DO migration), #15904 (D1 REST batch atomicity question) | users | 2026-07-29 to 2026-09-27 | 2026-09-29 (community scout) | No |
| S43 | workers-rs #166, #453, #826 (panic handling history); #967 (DO sync KV API missing) | users | 2022-04 to 2026-04 | 2026-09-29 (community scout; titles and states only for some) | No |
| S44 | Ente museum `server/pkg/controller/file.go`, `object_cleanup.go`; Immich `asset-media.service.ts`; restic rest-server `repo/repo.go`; Headscale `preauth_key.go` | projects | main/master heads | 2026-09-29 (source scout; A3 re-read Ente and restic) | Yes |

## Claims

Skeptic columns are empty until Stage 4. "Key?" follows PLAN §5.1.

| # | Claim | Sources | Key? | Skeptic 1 (sources) | Skeptic 2 (logic) | Skeptic 3 (adversary/cost/user) | Verdict |
|---|---|---|---|---|---|---|---|
| C1 | Presigned URLs are generated "server-side with no communication with R2", for GET, HEAD, PUT or DELETE, with expiry from 1 s to 7 days. "`POST` (multipart form uploads via HTML forms) is not currently supported." | S1 | Yes | | | | Pending |
| C2 | Presigned URLs "work with the S3 API domain (`<ACCOUNT_ID>.r2.cloudflarestorage.com`) and cannot be used with custom domains." | S1 | Yes | | | | Pending |
| C3 | A presigned URL "can be reused multiple times until it expires". Cloudflare says to treat it as a bearer token. Changing resource, operation or expiry gives 403 SignatureDoesNotMatch. The only documented header restriction is a signed Content-Type. | S1 | Yes | | | | Pending |
| C4 | The documented example URL carries `X-Amz-Content-Sha256=UNSIGNED-PAYLOAD` and `X-Amz-SignedHeaders=host`, so by default neither body hash nor length is signed. | S1 | Yes | | | | Pending |
| C5 | The S3 table lists If-Match, If-None-Match, If-Modified-Since, If-Unmodified-Since and Content-MD5 for PutObject. UploadPart lists Content-MD5 (and SSE-C) and no `x-amz-checksum-*`. CompleteMultipartUpload lists only unsupported bucket-owner and request-payer headers. | S2 | Yes | | | | Pending |
| C6 | Checksum table: SHA-256, SHA-1, CRC32 and CRC32C are COMPOSITE only; CRC-64/NVME is FULL_OBJECT only. A release note (2023-06-16) says "S3 putObject now supports sha256 and sha1 checksums". | S2, S11 | Yes | | | | Pending |
| C7 | Release note 2023-08-11: "Users can now complete conditional multipart publish operations. When a condition failure occurs when publishing an upload, the upload is no longer available and is treated as aborted." | S11 | Yes | | | | Pending (contradicts C8's silence) |
| C8 | Neither the S3 table's CompleteMultipartUpload row nor the binding's `R2MultipartUpload.complete(parts)` signature documents any condition. `R2MultipartOptions` has no `onlyIf`. | S2, S10 | Yes | | | | Pending |
| C9 | "Uploading to the same part number replaces the previous part. If a subsequent upload to the same part fails, the original part is lost." Part ETag = MD5 of the part. Completed multipart ETag = MD5 of the concatenated binary part MD5s, plus "-" and the part count. All parts except the last must be the same size (5 MiB to 5 GiB). | S2, S12 | Yes | | | | Pending |
| C10 | Temporary credentials are derived from a parent R2 token, bound to exactly one bucket, scoped by preset scope or an explicit action list (Read, Write, Multipart groups listed separately, incl. `DeleteObject` apart from `PutObject`), optionally restricted to `prefixPaths` and exact `objectPaths`, and "cannot exceed the permissions of its parent token". | S3 | Yes | | | | Pending |
| C11 | Action scoping is "currently supported via local signing only; support in the Temporary Credentials API is coming soon". Local signing: HS256 JWT with the parent secret, carrying `bucket`, `scope`, optional `actions` and `paths`, `sub` account ID, `iss` parent key ID, `aud` endpoint host, `exp`. Temporary secret = SHA-256 hex of the JWT; session token = base64("jwt/" + JWT); `ttlSeconds` defaults to 3,600 in the example. Revoking the parent token makes all derived credentials "stop working immediately". | S3, S4 | Yes | | | | Pending |
| C12 | Long-lived R2 tokens have four levels: Admin R&W, Admin R, Object R&W, Object R. Only Object-level tokens can be scoped to buckets. No prefix scoping and no delete-vs-write split are documented. Object-level permissions work only via the S3 API, not the REST API. | S5 | Yes | | | | Pending |
| C13 | Buckets have a default lifecycle rule that expires multipart uploads 7 days after initiation. Rules can be prefix-scoped, up to 1,000. Objects are typically removed within 24 h of expiry, and rule changes can lag. Managing lifecycles needs `Workers R2 Storage Write`. | S6 | Yes | | | | Pending |
| C14 | Adding or removing R2 permissions on API keys is eventually consistent, "up to a minute". Two writers to one key: last to complete wins. Reads, deletes and listings are strongly consistent. | S9 | Yes | | | | Pending (C11 says "immediately" for derived credentials) |
| C15 | Bucket locks "prevent the deletion and overwriting of objects" for an Age (`maxAgeSeconds`) or Indefinite, per prefix. Up to 1,000 rules; the strictest (longest) retention wins; lock rules "take precedence over lifecycle rules"; a bucket cannot be emptied while any lock rule exists. Configured through dashboard, wrangler or the REST API. Nothing is said about in-progress multipart uploads or the default abort. | S7 | No | | | | Pending |
| C16 | The R2 binding `put()` takes `onlyIf` (R2Conditional or Headers) and one of md5/sha1/sha256/sha384/sha512 "to check the received object's integrity". `resumeMultipartUpload` does not validate the uploadId. Uncompleted multipart uploads abort after 7 days. | S10 | Yes | | | | Pending |
| C17 | The lifecycle page shows only *shorter* prefix abort rules (1 day overriding 7). Whether any rule can lengthen or disable the default 7-day abort is not documented. | S6 | Yes | | | | Pending (C1-S1) |
| C18 | R2: 1,024-byte keys, 8,192-byte metadata, 10,000 parts, at most 1 concurrent write per second to the same key (more returns 429), 50 bucket-management operations per second per bucket. The REST API is limited to 1,200 requests per 5 minutes across all R2 REST operations on the account. | S8 | Yes | | | | Pending |
| C19 | Maximum upload is 5 GiB less 5 MiB (4.995 GiB) per request or part, and 4.995 TiB multipart. "The max upload size limit does not apply to subrequests." | S8 | No | | | | Pending |
| C20 | Workers request body size depends on the zone plan: 100 MB Free/Pro, 200 MB Business, up to 5 GB Enterprise; 413 above. URL max 16 KB; 128 KB headers. | S26 | Yes (records through Worker) | | | | Pending |
| C21 | Workers Paid: CPU 30 s default, configurable to 5 min; waiting on network or storage is not CPU. Subrequests 10,000 per invocation by default (to 10M). 6 simultaneous connections waiting for headers. 128 MB per isolate (JS heap + Wasm). 1 s startup. Worker size 64 MiB uncompressed. 250 Cron Triggers per account. | S26 | Yes | | | | Pending |
| C22 | Runtime updates happen "a few times per week"; in-flight requests get a 30 s grace and are then terminated. | S26 | Yes (long Worker-proxied uploads) | | | | Pending |
| C23 | Cron Trigger CPU: 30 s for intervals < 1 h, 15 min for ≥ 1 h. Wall time 15 min for Cron, DO alarms and Queue consumers. Crons run in UTC. Changes take up to 15 min to propagate. | S26, S29 | No | | | | Pending |
| C24 | D1 `batch()` statements run "sequentially, non-concurrently" as one SQL transaction; a failing statement aborts or rolls back the sequence. D1 is otherwise auto-commit. | S16 | Yes | | | | Pending |
| C25 | D1: 10 GB per database ("cannot be further increased"); 100 bound parameters, 100 KB statement, 2 MB row, 30 s query, 1,000 queries per invocation (Paid). | S14, S15 | Yes | | | | Pending |
| C26 | D1 documents `json_each` to expand a JSON array bound as one parameter into rows for `WHERE … IN (SELECT value FROM json_each(?))`. | S17 | Yes (C1-S3 shape) | | | | Pending |
| C27 | "Each individual D1 database is inherently single-threaded, and processes queries one at a time." About 1,000 q/s at 1 ms and 10 q/s at 100 ms. A full queue returns "overloaded". Each database is backed by one Durable Object. Indexed point reads take < 1 ms; writes "can take several milliseconds". | S14 | Yes | | | | Pending |
| C28 | D1 Time Travel restores to any minute in the last 30 days (Paid). SQLite-backed DOs have a PITR API over 30 days, invoked from the object's own code, and not available in local development. | S18, S23 | Yes (C8) | | | | Pending |
| C29 | D1 global read replication carries a Beta badge. | S19 | No | | | | Pending |
| C30 | Each DO is single-threaded with a soft limit of 1,000 requests/s; unlimited objects; 10 GB per SQLite-backed object (writes fail with `SQLITE_FULL` after that; reads and deletes still work); CPU 30 s default per invocation, configurable to 5 min. DO SQL forbids `BEGIN`/`SAVEPOINT` in `sql.exec()`; transactions go through `transaction()`/`transactionSync()`. | S21, S22, S23 | Yes | | | | Pending |
| C31 | DO alarms: one per object, at-least-once, retried with exponential backoff from 2 s, up to 6 retries. | S25 | No | | | | Pending |
| C32 | Cloudflare's Rust page carries a **Beta** badge. Rust bindings exist for KV, DO, R2, D1, Queues (producer), rate limiting and more. | S33 | Yes | | | | Pending |
| C33 | `workers-rs`: panics abort the Wasm instance by default. `--panic-unwind` uses the **nightly** toolchain, rebuilds `std` (`-Zbuild-std`) and reinitialises the instance after hard aborts. Queue support is behind a `queue` feature flag described as beta. RPC support is experimental. | S34 | Yes | | | | Pending |
| C34 | `worker` crate 0.8.7 (rust-version 1.91, updated 2026-09-25) exposes DO `set_alarm`, `alarm`, `transaction` and `sql()`. A case-insensitive search of its `src/` found no Workflows binding. | S35 | No | | | | Pending (absence by grep) |
| C35 | workers-rs panic handling has a multi-year issue history (#166, #453, #826 open). A DO synchronous KV API request (#967) was still open as of 2026-04-09. | S43 | No | | | | **Secondary only** |
| C36 | aws4fetch 1.0.20 defaults `X-Amz-Expires` to 86,400 s (24 h) for S3 `signQuery`, signs `UNSIGNED-PAYLOAD` unless `X-Amz-Content-Sha256` is set, excludes content-length and similar headers from signing unless `allHeaders` is set, supports a session token, and caches the derived signing key per (secret, date, region, service). Last release 2024-08-28. | S36 | Yes | | | | Pending |
| C37 | Workers Web Crypto supports Ed25519 (sign/verify), X25519, HMAC and SHA-256 natively. | S32 | Yes (BUD-CPU-REQ) | | | | Pending |
| C38 | Workers VPC is Beta. It binds a Worker to private hosts through a Cloudflare Tunnel, so the cloud initiates requests into the private network. | S37 | Yes | | | | Pending |
| C39 | A Workers Custom Domain needs "an active Cloudflare zone", gets an auto-generated certificate (Advanced Certificate for deeper subdomains), and cannot be created on a hostname with an existing CNAME. | S31 | Yes | | | | Pending |
| C40 | Disabling the `workers.dev` route needs `workers_dev = false` in the config (otherwise the next deploy re-enables it). Disabling it "does not disable Version URLs". | S31 | Yes (C2) | | | | Pending |
| C41 | The runtime "will support old compatibility dates forever"; Cloudflare will contact affected developers if a breaking change is ever needed. | S28 | No | | | | Pending |
| C42 | Gradual deployments route each request independently by percentage unless version affinity is used. Each Durable Object is pinned to one version per deployment, because only one version of a DO runs at a time. | S27 | Yes | | | | Pending |
| C43 | DO class lifecycle changes apply only through `wrangler deploy`. `wrangler versions upload` fails fast when the config has `exports` entries, and gradual deployments are not supported for lifecycle changes. A class rename is not atomic at runtime for a few seconds. | S24, S42 | Yes | | | | Pending |
| C44 | The Workflows limits page still cites 3 MB/10 MB "max script size per Worker size limits", while the Workers limits page says 64 MiB uncompressed. | S30, S26 | No | | | | Pending (doc inconsistency) |
| C45 | The R2 binding put-if-absent path had a wildcard-etag parsing bug in 2024 (workerd #2572, closed; fix version not checked). Local `wrangler dev` crashed on a recoverable D1 `SQLITE_BUSY` under concurrent writes in wrangler 4.114/4.115 (#14916, open as of 2026-09-29). | S41, S42 | Yes (C1-S1/S2 design) | | | | **Secondary only** |
| C46 | Workflows (Paid): 10,000 steps by default (25,000 max), `step.sleep` up to 365 days, 1 GB persisted state per instance, 30-day retention. Free: 1,024 steps, 100 MB. | S30 | No | | | | Pending |
| C47 | npm latest on 2026-10-06: wrangler 4.147.0 (2026-10-02), miniflare 5.20261001.0-alpha (2026-10-01; the `latest` tag points at an alpha), hono 4.13.13 (2026-10-04), aws4fetch 1.0.20 (2024-08-28), @cloudflare/vitest-pool-workers 0.22.0 (2026-08-18), drizzle-orm 0.45.3 (2026-09-21), kysely 0.29.6 (2026-09-16), chanfana 3.4.0 (2026-08-17), zod 4.6.5 (2026-09-13). | S39 | No | | | | Pending |
| C48 | Workers limits page: Zod older than 4.5.0 "use[s] substantially more memory per schema". | S26 | No | | | | Pending |

## Findings

### F1. Topology (v0 proposal for ADR-0010)

| Component | Role | Holds | Notes |
|---|---|---|---|
| **Worker `rq-api`** (TypeScript) on `api.<owner-domain>` | Device, homelab and enrollment API; presigning; minting homelab R2 credentials; writing records to R2; cron jobs | R2 parent secret (for presign and temp-credential minting), R2 bindings, D1 binding, homelab **public** control key, dedup-free config | Holds no trust-forging key (SR-23). `workers_dev = false`; preview URLs disabled (C40). |
| **D1 `rq-control`** | System of record for the control plane | Tables in F6 | One database. Every API request performs **at most one** `batch()` (F2). |
| **DO class `DeviceGate`** (optional, C2 decides) | Exact per-device counters and quotas; outstanding-lease count | Small per-device SQLite | One object per device via `idFromName(device_id)`. Not on the critical path for correctness. |
| **R2 bucket `rq-ingest`** | Content and record staging | `staging/`, `meta/` | **No Expiration rule, ever.** Default 7-day multipart abort only. |
| **R2 bucket `rq-restore`** | Restore staging (ADR-0001 §6) | `restore/` | Expiration rule (e.g. 7 days; deletion lags up to ~24 h, C13) plus a 1-day abort rule. |
| **Cron Trigger** (one, e.g. every 15 min) | Due-work runner | — | F9. |
| **Queues, R2 event notifications** | Not used in v1 | — | DR-C1-3. Can be added later as a latency hint without changing the protocol. |
| **Homelab** (outbound only) | Polls the feed, lists R2, pulls, verifies, commits, publishes receipts, deletes staging | Its own control signing key; short-lived R2 temp credentials | F5. |

Environments: `local` (Miniflare/`wrangler dev`, pinned versions), `sandbox` (H1's dedicated account and throwaway domain), `production` (the owner's account and domain). Prefer **separate accounts** for sandbox and production rather than wrangler environments in one account, because the R2 parent token and account-level rate limits (C18) are per account.

### F2. D1 vs Durable Objects

**Why the choice is now about operations, not correctness.** A3 replaced the exclusive claim with an advisory lease and per-upload keys. Safety comes from homelab verification and receipts (A3 I1–I5; D1 SR-01, SR-04, SR-05). A lost, doubled or rolled-back lease costs bandwidth, not data. So the store does not need DO-grade in-memory serialisation, and D1's batch transactions (C24) are enough for "insert the lease if no live lease exists".

| Criterion | D1 (one DB) | SQLite DO, one global object | SQLite DOs, sharded | Hybrid (recommended) |
|---|---|---|---|---|
| Throughput model | One thread per DB (C27) | One thread per object, soft 1,000 req/s (C30) | N threads | D1 for records; DOs only for counters |
| Atomic multi-row update | `batch()` as one transaction (C24); no interactive transaction documented | `transactionSync()` with arbitrary logic (C30) | Only within one shard | D1 `batch()` |
| Migrations | Numbered SQL files and a tracking table via wrangler (S20) | Self-written, run in the object | Self-written, per shard | wrangler for D1 |
| Backup / restore | Time Travel 30 days from the CLI; `wrangler d1 export` (C28) | PITR 30 days, only from object code; none locally (C28) | Per shard | D1 Time Travel + homelab nightly export |
| Owner ad-hoc queries | `wrangler d1 execute`, dashboard | Custom endpoint needed | Custom, fan-out | D1 |
| Size limit | 10 GB, cannot be raised (C25) | 10 GB per object | 10 GB × N | D1 well inside (below) |
| Storage price | $0.75/GB-month above 5 GB (C4 K-table) | $0.20/GB-month above 5 GB | same | Irrelevant at < 5 GB |
| Local emulation hazards | #14916: SQLITE_BUSY crash in some wrangler versions (C45) | #7190: alarms crash workerd with in-memory storage (S41) | same | Pin versions; disk-backed storage |

**Size check (estimate, not measured):** the C1-S3 scenario is a 5M-row index. At roughly 100–200 bytes per row including the primary-key index (assumption), that is about 0.5–1 GB, well under 10 GB. The receipt relay must be pruned after the device fetches (the homelab keeps every receipt; A3 F4), or it grows by about 250 B per record (CE estimate).

**Throughput arithmetic (assumptions marked; C1-S2/S3 replace it with measurements):**
- **Aggregate upper bound:** 25 devices each saturating a 20 Mbit/s uplink at once (assumption) is about 62.5 MB/s. At a 2 MB mean file size (assumption; E1 will measure) that is about 31 files/s. At about 3 write queries per file (C4 assumes 6 rows written per file), that is about 94 write queries/s. At 5 ms each ("several ms", C27), that is about 0.47 thread-seconds per second: inside one D1 thread, with about 2× headroom.
- **Breaking case:** 100 KB files at the same bandwidth would be about 625 files/s, which would overload a per-file design. **Design rule:** check, begin, record and commit endpoints are **batch endpoints**, and each request issues one D1 `batch()` for all its items, so query rate tracks request rate, not file rate. Records already travel in batches (A3 F8).
- **Presence checks:** one `SELECT … WHERE id IN (SELECT value FROM json_each(?1))` per 1,000 IDs (C26) uses 1 bound parameter, under the 100-parameter cap (C25). Cost by unit price: 1M IDs is about 1M rows read, about $0.001 above the 25B/month included (C4), plus about 1,000 Worker requests. That is far under C1-S3's "< $1 per million IDs" even with 10× read amplification (arithmetic; C1-S3 measures p99).
- **Overload behaviour:** "overloaded" is a retryable error (C27). Clients back off; nothing is lost because the lease is advisory.

**Fallback if C1-S2/S3 fail the budget:** move `dedup` and `uploads` into a `DedupShard` SQLite DO class keyed by the first hex digit (16 shards) of the dedup ID. A presence check then fans out to at most 16 shards (16 subrequests, far under 10,000, C21). Keep accounts, devices, invites and the feed in D1. The data-access layer must hide which store is used, so this is a code change, not a protocol change.

**Rejected:** KV as an existence cache for claims (eventually consistent; PLAN already leans this way). One global DO for everything (same single thread as D1, worse tooling).

### F3. R2 key layout and buckets (one-way door #7)

| Bucket / prefix | Key | Writer | Reader / deleter | Lifecycle | Why |
|---|---|---|---|---|---|
| `rq-ingest` `staging/` | `staging/<dedup_id>/<upload_id>/s<n>` (`s0` for every upload; `s1…` only for A3's segment checkpoint) | Device via presigned PUT/UploadPart; Worker completes multipart | Homelab (GET, LIST, DELETE after durable commit) | **None** besides the default 7-day multipart abort | Per-upload keys avoid last-writer-wins and the 1 write/s per-key limit (C14, C18; SR-07). A uniform `/s<n>` suffix lets the homelab treat every upload as a list of segments, A3 F2. |
| `rq-ingest` `meta/` | `meta/<device_id>/<record_batch_id>.age` | **Worker** (`put` with create-only `onlyIf`) | Homelab | **None** | Records are small and go through the Worker (F4). No dedup ID in the key (SR-26, CE §9). |
| `rq-restore` `restore/` | `restore/<device_id>/<restore_job_id>/<object_id>` | Homelab (temp credential: Put and multipart actions on this prefix only) | Device via presigned GET | Expiration 7 days (ADR-0001 §6), abort 1 day | The only bucket where an Expiration rule may exist. |

- **Key lengths:** a hex dedup ID (64) plus a UUID (36) plus fixed parts is about 115 bytes, under 1,024 (C18). A1 may pick a shorter encoding.
- **Two buckets, not one.**
  - Long-lived tokens scope only to buckets, never prefixes (C12). Lifecycle rules are per prefix but live in one bucket-wide configuration (C13), so one mistyped prefix in a shared configuration could put an Expiration on `staging/`. With two buckets the ingest bucket simply has no Expiration rules, which an automated check can assert (`wrangler r2 bucket lifecycle list rq-ingest` shows only abort rules).
  - Metrics separate per bucket (C4 notes GraphQL by `bucketName`).
  - Cost: none extra (R2 bills per GB and per operation).
- **7-day abort:** it removes only *incomplete* uploads, which were never "staged" (A3 F1), so it cannot delete safe data. A file whose upload outlives 7 days needs A3's segment checkpoint (spike A3-S3) or the USB fallback. C1-S1 also tests whether a longer abort rule overrides the default (C17).
- **Bucket locks (optional, defence in depth only):** an Age lock on `staging/` and `meta/` (e.g. 48 h) would make R2 itself refuse overwrites in that window (C15). That might give create-only for multipart completion, which nothing else documents. But it also blocks the homelab's own deletion for that window. D1 advises against relying on locks for integrity (`d1-threat-model.md` recommendation 4). Use one only if C1-S1 shows it blocks overwrite by presigned PUT **and** Complete **without** blocking the 7-day abort or in-progress uploads.
- **Warm cache (C-01):** v1 window 0. If the owner wants one, the homelab delays its own deletion by N days. It is never a lifecycle rule, because a lifecycle Expiration is exactly what the ingest bucket must not have.

### F4. Upload flow and presigning

**Content (device → R2 directly):**
1. `POST /v1/uploads` (batch). The Worker records the lease and generates `upload_id` and the key.
   - Single PUT when size ≤ one part: returns a presigned PUT.
   - Multipart otherwise: the Worker calls `createMultipartUpload` through the binding and returns the first **window** of presigned UploadPart URLs (PUT with `partNumber` and `uploadId` query parameters).
   - Every URL lifetime ≤ 15 min (BUD-REVOKE). Set `X-Amz-Expires` explicitly: aws4fetch defaults to 24 h (C36).
2. `POST /v1/uploads/{id}/parts` gets the next window. Window ≈ min(remaining parts, ceil(uplink × 900 s / part size)). At 20 Mbit/s and 16 MiB parts that is about 134 parts; on a 2 Mbit/s phone about 14. "200 parts in one request" (C1-S4) is therefore the upper end, not the normal case.
3. `POST /v1/uploads/{id}/complete` carries the part ETags.
   - The Worker calls `resumeMultipartUpload(key, uploadId).complete(parts)` (C16; it must handle a NoSuchUpload), or HEADs a single PUT.
   - It compares the returned size with the declared size (SR-24) and marks the upload `staged` (A3 F1).
   - The device can check the completed ETag against MD5(concatenated part MD5s)-N computed locally (C9): a cheap end-to-end check for accidental corruption. MD5 gives no protection against tampering; that comes from homelab verification.
4. Signing extras, each **only if C1-S1 shows R2 enforces it**:
   - `Content-MD5` on UploadPart and PutObject (both documented as supported, C5);
   - `If-None-Match: *` on PutObject (SR-08);
   - Content-Length;
   - `x-amz-checksum-sha256` on single PUT (C6).
   aws4fetch signs these only if they are set (and, for content-length, only with `allHeaders`, C36).

**Records (device → Worker → R2):** `POST /v1/records` carries a record batch body: signed and encrypted, opaque to the Worker, and much smaller than the 100 MB body limit (C20).
- The Worker writes `meta/<device_id>/<batch_id>.age` with `put(…, {onlyIf: If-None-Match "*"})`. The wildcard-etag history (C45) means C1-S1 must test this exact call.
- In the same request it appends the feed event and upserts the (device_id, record_id) idempotency rows in one D1 `batch()`.
- This removes presigned-overwrite exposure for `meta/`, gives exact size and rate control, and replaces the R2 event notification as the feed source.

**Why presigned URLs, not temporary credentials, for devices:**
- Background upload machinery wants fully formed requests: iOS background `URLSession` later, Android queued work, possibly started hours later.
- A presigned URL is a plain HTTP PUT that needs no SigV4 code on the device.
- A temp credential scoped to one `objectPaths` key with `UploadPart` and `ListParts` only (C10, C11) is a good **desktop** option, because it saves the window calls. Keep it as an option and do not ship two paths in v1.

**Why not upload content through the Worker (the fallback if R2 behaves badly):**
- Part size would be capped by the zone's 100 MB body limit on Free/Pro (C20).
- Runtime updates kill requests still running after a 30 s grace (C22), and a 100 MB part over a slow uplink runs longer than that.
- Every byte would depend on Worker availability.
- It buys create-only (`onlyIf`) and per-object `sha256` (C16), but the homelab verifies everything anyway (SR-04).

**Revocation (BUD-REVOKE):**
- A revoked device gets no new URLs within 60 s: the Worker checks device status in D1 on every call.
- Outstanding URLs live ≤ 15 min by construction.
- **Kill switch:** rotating the R2 parent token invalidates every outstanding URL and temp credential at once. Propagation is "up to a minute" (C14) or "immediately" (C11); C1-S1 measures it. The price is that every in-flight upload restarts its current window.

### F5. Homelab authentication and notifications

- **Homelab → Worker:** requests signed with a homelab control key (Ed25519; D2 owns the key inventory, D3 the request format). The Worker holds only the public key (SR-23).
  - Endpoints: `feed`, `commits` (commit marks + receipts, batch), `rejections`, `heartbeat` (signed, SR-18), `revocations` (signed list, SR-17), `credentials`, `export`, `restore-jobs`.
- **Homelab → R2:** `POST /v1/homelab/credentials` returns a temp credential the Worker mints locally (C11), TTL ≤ 1 h:
  - actions `ListObjectsV2`, `GetObject`, `HeadObject`, `DeleteObject`, `ListMultipartUploads`, `AbortMultipartUpload` on `rq-ingest` prefixes `staging/` and `meta/`;
  - a second credential with `PutObject` and the multipart write actions on `rq-restore` prefix `restore/`.
  
  The homelab therefore stores **no long-lived Cloudflare secret** at all.
  - The cost: R2 access depends on the Worker being up. That is acceptable, because when the Worker is down nothing new is staged either.
  - **Break-glass:** one long-lived Object R&W token scoped to both buckets, kept offline (C8 runbook), for draining staging if the Worker is broken.
  - What a homelab compromise can do in the cloud is unchanged: it can delete staged-but-unsafe objects. Devices hold no receipt for those, so they re-upload (A3). It is availability, not loss.
- **Feed instead of Queues (DR-C1-3):** the homelab polls `GET /v1/homelab/feed?after=<event_seq>` (e.g. every 30 s; about 86k requests/month, inside the 10M included, C4) and lists `staging/` and `meta/` on start and hourly (A3 F5).
  - Compared with Queues + event notifications this removes:
    - a Cloudflare API token on the homelab (Queues pull needs one with read + write, S38);
    - the account-wide 1,200/5 min REST budget and its 5-minute 429 lockout (A3 C7);
    - retention defaults, `max_retries` deletion and the late-ack contradiction (A3 C3–C5);
    - a billed line in seed months (C4).
  - Latency stays at seconds, far inside BUD-TTS.
  - A DO WebSocket push channel is a later option if seconds are not enough.
- **Workers VPC / Tunnel push: rejected** (R-12).
  - It inverts the trust direction: the cloud becomes a client of a homelab server, so a compromised Worker can call ingest endpoints at will.
  - It contradicts ADR-0001 §1, under which the homelab pulls and no service is offered to the cloud.
  - It adds a Beta dependency (C38).
  - The cloudflared connection is outbound at the TCP level, but that does not change who initiates requests.

### F6. Cloud state: what is rebuildable and what needs backup (C8 input)

| Table (D1) | Contents | If lost | Backup |
|---|---|---|---|
| `accounts` | name, email, verification state (ADR-0002; OD-03 may move it home) | Users must re-verify | **Nightly export** |
| `invites`, `enroll_tokens`, `pair_codes` | keyed hash, expiry, state, issuer | Printed cards stop working | **Nightly export** (E5/D3 own the formats) |
| `devices` | device_id, account, public keys, status, last activity, client version | Re-enrollment, unless the homelab holds a signed device list (D3) | Export; rebuildable if D3 adopts a homelab-signed list |
| `uploads` (leases) | upload_id, dedup_id, device_id, key, UploadId, lease expiry, state | Parallel uploads only (A3) | None |
| `dedup` | dedup_id, state, size, committed receipt pointer | Re-uploads until the homelab republishes the committed set | Rebuild from the homelab |
| `receipt_relay` | (device_id, record_id) → receipt bytes, fetched_at | Homelab republishes | Rebuild from the homelab |
| `feed` | event_seq, kind, refs | Reconciliation by listing covers it | None |
| `revocations`, `heartbeat` | homelab-signed blobs | Homelab republishes | None |
| `idempotency` | key, fingerprint, response, expiry | Duplicate-safe by natural keys | None |
| `audit_log` | enrollments, revocations, admin actions | Lost history | **Nightly export** (C7/C8) |
| `email_suppression` | bounces, complaints (C3) | Re-sending to bad addresses | **Nightly export** |
| Counters (`DeviceGate` DOs) | rate and quota windows | Reset (C2 accepts or not) | None |

- D1 Time Travel (30 days, C28) covers operator mistakes and bad migrations. It does **not** cover loss of the Cloudflare account. Hence a signed `GET /v1/homelab/export` that the homelab pulls nightly.
- The bootstrap document and Worker config live in git.

### F7. Worker language

| Criterion | TypeScript (Hono) | Rust `workers-rs` | TS shell + Rust→Wasm module for shared verifiers |
|---|---|---|---|
| Platform status | GA language | Rust page badged **Beta** (C32); crate 0.8.7, pre-1.0 (C34) | TS GA; Wasm modules supported |
| Failure mode | Exceptions per request | Panic aborts the instance unless `--panic-unwind`, which needs **nightly** and `build-std` (C33); multi-year issue history (C35) | Rust panics confined to the module |
| API coverage | Everything first | DO SQL, alarms, R2 conditionals, D1, queue (feature flag) present; Workflows binding not found (C34); RPC experimental (C33) | TS coverage |
| Crypto | Native Web Crypto Ed25519, HMAC, SHA-256 (C37) | Rust crates compiled to Wasm (performance unmeasured) | Native for Ed25519; Wasm only where WebCrypto lacks an algorithm |
| Tests | `@cloudflare/vitest-pool-workers` 0.22.0 | wrangler dev + external tests | Both |
| Formats implemented twice | Request auth, code hashing, ID encoding, API schema | None of those | Only what is not in Wasm |
| Presign / temp creds | aws4fetch + jose, documented by Cloudflare (S4) | Hand-rolled or an SDK crate in Wasm | TS |

**What "formats implemented twice" really means here:**
- The heavy, permanent formats never enter the Worker under the **opaque-artifact rule**: age envelope, records, receipts, manifests, bundles, dedup-ID derivation. The Worker stores and relays them as bytes, and never needs to read inside them, because the cloud makes no safety decision (SR-01).
- What remains is small and testable with shared vectors (G2):
  - the request-signature base string (D3);
  - invite, enrollment and pairing code hashing (E5/D3);
  - dedup-ID textual encoding checks (A1);
  - the OpenAPI schema, which generates both sides.

**Recommendation:** TypeScript.
- **Revisit trigger:** D3 chooses a request-auth construction or a KDF that Web Crypto lacks, such as Argon2 for invite-bound MACs (SR-14 candidate). Then compile that single Rust function to Wasm and import it from the TS Worker. Do not move the whole Worker to `workers-rs`.
- Measure BUD-CPU-REQ (< 1 ms) on Web Crypto Ed25519 in D3-S1 or C1-S4.

### F8. API v1 conventions (outline for `docs/design/api-v1.md`)

- **Hosts:**
  - `api.<owner-domain>` as a Workers Custom Domain (needs the domain's zone active on Cloudflare, C39).
  - Content URLs point at `<ACCOUNT_ID>.r2.cloudflarestorage.com` (C2). Clients follow URLs as given and **never pin or allowlist** the R2 host: a move to a new account (C8-S2) changes it.
- **Bootstrap (one-way door #8):** `GET /v1/bootstrap` returns a document **signed by an offline config key pinned in the kit** (D3/D5 own the key). It carries API base URL(s), the minimum client version per platform, feature flags, and a not-after date.
  - Clients cache the last good document.
  - Clients ship with **two** bootstrap locations on two independent hostnames, so one lapsed domain or one lost account does not strand installed kits (C8 unattended survivability).
  - Proposal only: the owner decides the second location (DR-C1-4).
- **Versioning:** path prefix `/v1/`. Within v1, changes are additive only: new optional fields and endpoints. Clients ignore unknown fields. Every request carries `Reliquary-Client: <platform>/<semver>`.
  - Below the minimum version, the answer is a problem body with code `update_required` (status 426 proposed; the choice is open), carrying `min_version`.
  - The client renders the plain-language text itself, so it can be localised (E6).
  - C1-S5 tests that an old client sees nothing from an additive change and gets the typed error from a breaking one.
- **Gradual deployments:** two Worker versions serve one device in alternation (C42). So API and D1 changes must be readable by both the current and the previous version (expand/contract).
- **Server time:** a `Reliquary-Server-Time` header (Unix ms) on every response, so clients can estimate clock skew for signed requests. Presigned URLs carry Worker time, so device clocks do not affect them.
- **Auth:** a per-device signed request (format and nonce rules: D3/ADR-0014). Homelab requests use the same scheme with the homelab key.
- **Idempotency:**
  - Natural keys first: (device_id, record_id), (device_id, upload_id), as A3 requires.
  - `Idempotency-Key` header on creates that lack a natural key (redeem, pair, restore-job creation), following the IETF draft's semantics (409 while the first request is in progress; 422 on payload mismatch; a published expiry). Draft status unverified; A3 and the standards scout read the editor's copy only.
  - Stored in D1 with a fingerprint and a 7-day expiry (proposal).
- **Batching:** `check` (≤ 1,000 IDs), `uploads` (≤ 100), `records`, `commits`. All return **per-item typed results** (A3's MISSING / IN_FLIGHT / COMMITTED; never an untyped "reject", Immich lesson).
- **Pagination:** an opaque `cursor` plus `limit` (with a maximum) for feed, receipts and devices.
- **Errors:** `application/problem+json` (RFC 9457 shape; not re-read this run) with a stable `code`, `retryable`, and `Retry-After` on 429 and 503. "Overloaded" errors from D1/DO map to 503 retryable (C27, C30).
- **Endpoint outline (v0):**

  | Group | Endpoints |
  |---|---|
  | Public | `GET /v1/bootstrap`; `POST /v1/enroll/redeem`; `POST /v1/enroll/pair`; email verification as GET page plus POST confirm (C3) |
  | Device | `POST /v1/check`; `POST /v1/uploads`; `POST /v1/uploads/{id}/parts`; `POST /v1/uploads/{id}/complete`; `POST /v1/records`; `GET /v1/receipts?cursor=`; `GET /v1/status` (server time, latest signed homelab heartbeat); `GET /v1/restores` (later, A8) |
  | Homelab | `GET /v1/homelab/feed`; `POST /v1/homelab/commits`; `POST /v1/homelab/rejections`; `POST /v1/homelab/credentials`; `PUT /v1/homelab/revocations`; `POST /v1/homelab/heartbeat`; `POST /v1/homelab/restore-jobs`; `GET /v1/homelab/export` |
  | Admin (owner) | Invites create, revoke, list; device revoke. The path depends on D3/C8: owner phone or homelab CLI. |

### F9. Background jobs

| Job | Mechanism | Notes |
|---|---|---|
| Lease expiry | None (lazy) | A lease is live if `lease_expires_at > now`. No sweeper is needed. |
| Stale device, nudge emails (E3/C3) | Cron (every 15 min, UTC, C23) | Each run computes what is due from D1 state, so a missed or doubled run is harmless. Record `nudge_sent_at` to rate-limit. |
| Dead-man's switch (C7) | Cron | Alerts the owner when the homelab's signed heartbeat is older than N h. C7 adds an external second check (Healthchecks). |
| Day-6 multipart checkpoint (A3 F2) | Cron | Selects uploads initiated more than 6 days ago and still incomplete. Spike A3-S3 first. |
| Per-device window counters | DO alarm inside `DeviceGate` (C2) | At-least-once, so increments must be idempotent (C31). |
| Long multi-step sequences | Workflows (not v1) | Only if E3's nudge sequences outgrow the cron. |

Cron limits are ample: 30 s CPU and 15 min wall per run (C23). Cron changes take up to 15 min to propagate, so no job may depend on a precise first-run time.

### F10. Change management and beta policy

- **D1 migrations:** numbered SQL files applied by wrangler (S20).
  - **Expand → deploy → contract** across at least two releases, because gradual deployments run two versions at once (C42).
  - Capture a Time Travel bookmark before each `migrations apply` (C28).
  - CI retries apply on 403/7403 and fails loudly (community report #15774, S42; secondary).
- **DO classes:** lifecycle changes only by a plain `wrangler deploy`, never by `versions upload` or a gradual deploy (C43). Avoid class renames. Pin each DO to one call style (all RPC or all fetch), because of the ordering issue in workerd #6561 (S41).
- **Compatibility date:** pinned. Bump deliberately in sandbox first (C41).
- **Tool pinning for emulated spikes:** exact wrangler/miniflare versions. The miniflare `latest` tag is an alpha (C47). Use disk-backed DO storage (#7190) and record the versions in the result.
- **Beta-feature policy (OD-14 input):** the owner intake B4 proposes "only with a documented, tested fallback that needs no client update".

  | Feature | Status | Used? | Fallback if it changes |
  |---|---|---|---|
  | Rust Workers | Beta (C32) | No | — |
  | Workers VPC | Beta (C38) | No (rejected) | — |
  | D1 read replication | Beta (C29) | No | — |
  | Temp credentials, action scoping by local JWT | Documented; "API support coming soon" (C11) | Yes (homelab) | Break-glass long-lived token; or the Temporary Credentials API with `object-read-write` + prefixes. Server-side only, so no client update. |
  | Email Service | Beta (T2) | C3's call | Resend/Postmark (C3) |

### F11. Load-bearing limits list (verification date 2026-10-06 unless noted)

| Limit | Value | Source | Bites where |
|---|---|---|---|
| Presigned URL expiry | 1 s – 7 days | C1 | BUD-REVOKE window |
| Presign hosts | S3 domain only, no custom domains | C2 | Hostname pinning |
| Same-key write rate | 1/s, then 429 | C18 | Key layout |
| Parts | 5 MiB – 4.995 GiB, ≤ 10,000, equal except last | C9, C19 | Part-size policy (B6) |
| Default multipart abort | 7 days from initiation | C13 | Slow uploads (A3-S3) |
| Lifecycle rules | 1,000 per bucket; deletion lag ~24 h | C13 | Restore bucket |
| R2 REST API | 1,200 req / 5 min per account | C18 | Avoid on the hot path |
| Token permission propagation | up to 1 min (vs "immediately" for temp creds) | C14, C11 | BUD-REVOKE kill switch |
| Workers CPU / request | 30 s default, 5 min max (Paid) | C21 | Presign windows |
| Subrequests | 10,000 default | C21 | DO fan-out |
| Request body | 100 MB Free/Pro zone | C20 | Records via Worker |
| D1 per DB | 10 GB, single thread, 100 params, 100 KB statement, 30 s query | C25, C27 | Dedup index, presence checks |
| D1 queries / invocation | 1,000 (Paid) | C25 | Batch endpoints |
| DO per object | ~1,000 req/s soft, 10 GB | C30 | Sharding fallback |
| Cron CPU | 30 s (< 1 h interval) | C23 | Jobs |
| Time Travel / PITR | 30 days | C28 | C8 backups |

### Alternatives compared

| Option | Fit with settled requirements | Pros | Cons | Evidence |
|---|---|---|---|---|
| **D1 + optional per-device DOs (recommended)** | Fits ADR-0001 ("D1 / Durable Objects") | Tooling, Time Travel, export, SQL | Single thread per DB | C24–C28, F2 |
| D1 only | Fits | Simplest | Exact counters awkward (C2) | F2 |
| DO per family (+ D1 for reporting) | Fits | In-object logic, alarms | Two stores to migrate; same single thread | C30 |
| Sharded DOs for dedup/leases | Fits | Horizontal | Fan-out, custom migrations and PITR | C28, C30 |
| KV existence cache | Fits | Cheap reads | Eventually consistent; no atomic lease | PLAN |
| **Feed polling + R2 listing (recommended)** | Touches ADR-0001 §1 (Queues named) | No CF API token on homelab; no REST limit; simple | Polling latency (seconds) | F5, A3 C3–C7 |
| R2 event notifications → Queues → HTTP pull | Fits ADR-0001 wording | Push-ish latency | API token, 1,200/5 min, retention and `max_retries` pitfalls, cost line | S13, S38, A3 |
| DO WebSocket push to homelab | Touches ADR-0001 §1 | Lowest latency, no CF API token | Hibernation and reconnect complexity | A3 F5 |
| Workers VPC / Tunnel push | **Breaks** outbound-only intent (R-12) | Instant | Cloud calls into the homelab; Beta | C38 |
| **Presigned per-part URLs in ≤ 15-min windows (recommended)** | Fits | Plain HTTP; background-API friendly | Window calls; create-only unproven | C1–C5 |
| Device temp credential per upload | Fits | No window calls; ListParts resume | SigV4 on the device; JWT format by example | C10, C11 |
| Content through the Worker | Fits | `onlyIf`, `sha256`, exact size, hides account ID | 100 MB body cap; runtime-update kills; availability coupling | C16, C20, C22 |
| **Homelab R2 via Worker-minted temp credentials (recommended)** | Fits | No long-lived secret at home; action/prefix scope | Depends on Worker availability; local-signing format | C10–C12 |
| Homelab long-lived bucket token | Fits | Independent of Worker | Cannot separate delete from write or scope prefixes | C12 |
| **TypeScript Worker (recommended)** | Fits | GA, native crypto, tooling | Small formats twice | F7 |
| Rust `workers-rs` | Fits | One implementation | Beta, pre-1.0, nightly for unwind | C32–C35 |

### Similar work and lessons

| Project | What they do | Borrow or avoid | Source |
|---|---|---|---|
| Ente museum | Random per-upload keys `<userID>/<uuid>`; up to 50 upload URLs per call; presigns each part **and** CompleteMultipartUpload; signs ContentLength/MD5 into single PUTs; temp-object table with 2× validity expiry and a SKIP LOCKED sweeper | **Borrow** per-upload keys, the temp-object table and size checks. **Check** on R2 whether presigned Complete (a POST) works (C1-S1); if it does, the device could complete without the Worker, but the Worker should still complete in order to own the `staged` transition. | S44 (source scout; A3 C21) |
| Immich bulk upload check | Batch of (id, checksum) → per-item ACCEPT/REJECT with a reason | **Borrow** per-item typed results; **avoid** untyped rejects (A3 C25) | S44 |
| restic rest-server | Append-only: no deletes, 403 on an existing blob, hash check | **Borrow** create-only; answer equal-content retries with success (A3) | S44 |
| Headscale pre-auth keys | Store prefix + hash, not the secret; reusable/used/expiry fields | **Borrow** for the `invites`, `enroll_tokens` and `pair_codes` schema | S44 |
| Cloudflare temp-credential example | Local JWT minting with jose + aws4fetch | **Borrow** for homelab credentials | S4 |

### Tools and libraries

| Name | Purpose | Licence | Maturity (release date) | Source |
|---|---|---|---|---|
| wrangler | Deploy, D1 migrations, local dev | MIT OR Apache-2.0 | 4.147.0, 2026-10-02 | C47 |
| miniflare | Local emulation (5.x has an R2 S3-API emulation worker per the source scout's static read; not executed by the analyst) | MIT | 5.20261001.0-alpha, 2026-10-01 (latest tag is an alpha) | C47 |
| hono | Router | MIT | 4.13.13, 2026-10-04 | C47 |
| chanfana | OpenAPI from Hono routes | MIT | 3.4.0, 2026-08-17 | C47 |
| zod | Schemas (≥ 4.5 for memory, C48) | MIT | 4.6.5, 2026-09-13 | C47 |
| drizzle-orm / kysely | D1 query layer and migrations (pick one in build; both active) | Apache-2.0 / MIT | 0.45.3, 2026-09-21 / 0.29.6, 2026-09-16 | C47 |
| aws4fetch | SigV4 presign and S3 client | MIT | 1.0.20, 2024-08-28 (stale, small; vendor if needed) | C36 |
| jose | JWT for temp credentials | not checked | not checked | S4 |
| @cloudflare/vitest-pool-workers | Tests inside workerd | MIT | 0.22.0, 2026-08-18 | C47 |
| workers-rs (`worker`) | Rust alternative (not recommended) | not checked | 0.8.7, 2026-09-25 | C34 |

## Spikes

Placeholder: the spike runner owns execution and the C1-S1 kit (`docs/research/kits/C1-S1/`). The hypotheses below fix the wording so the kit, the results and ADR-0010 match. **No sandbox account exists yet (H5 L01).** Any local run is **emulated, not real R2/Cloudflare**, and cannot settle C1-S1.

**C1-S1 hypotheses (real R2):**
- **H1:** presigned PUT with signed `If-None-Match: *` → 412 on an existing key; the existing object is unchanged.
- **H2:** CompleteMultipartUpload (S3 API) with `If-None-Match: *` on an existing key → precondition failure. Record whether the upload is aborted (C7) or survives.
- **H3:** a presigned **POST** for CompleteMultipartUpload and for CreateMultipartUpload is accepted or rejected (C1 covers only HTML-form POST).
- **H4:** presigned UploadPart works. A signed `Content-MD5` rejects a tampered part body.
- **H5:** a signed Content-Length rejects a longer or shorter body.
- **H6:** a signed `x-amz-checksum-sha256` on a single PUT rejects a tampered body.
- **H7:** part and object ETags equal the C9 formulas. The device-side computation matches.
- **H8:** a prefix `AbortIncompleteMultipartUpload` of 14 days overrides the 7-day default, or does not (C17).
- **H9:** an Age bucket lock blocks an overwrite by presigned PUT and by Complete; whether it blocks the homelab DELETE (expected) and the default abort.
- **H10:** a presigned URL whose expiry passes **mid-transfer** completes or fails.
- **H11:** after the parent token is rolled, existing presigned URLs and temp credentials fail. Measure the delay (C11 vs C14; BUD-REVOKE).
- **H12:** the binding `put` with `onlyIf` `If-None-Match: *` refuses an existing key (C45).
- **H13:** a temp credential with `actions` and `objectPaths` denies every action and key outside its scope.

| Spike | Hypothesis | Pass → / fail → (decision) | Exec tag | Budget IDs | Data class | Status | Result |
|---|---|---|---|---|---|---|---|
| C1-S1 | H1–H13 above | Pass on H1/H2/H12 → sign create-only (SR-08) as defence in depth. Fail → per-upload keys (already mandatory) plus homelab verification; record the gap. H8 fail → segment checkpoint or USB (A3-S3). H13 fail → long-lived homelab token. | SB (kit); emulated subset CT | BUD-REVOKE | `SYN → results` | Running (spike runner; kit) | Pending |
| C1-S2 | 50 concurrent leases × 10,000 trials: exactly one live lease per ID, D1 `batch()` vs DO `transactionSync` | Pass → D1. Fail → DO shards for `uploads` (F2). | CT (emulated) / SB | — | `SYN → results` | Running (spike runner) | Pending |
| C1-S3 | 1,000-ID presence check against 5M rows via `json_each` | p99 < 500 ms and < $1/M → D1. Else → DO shards. | SB | BUD-CLOUD | `SYN → results` | Not started (needs L01) | — |
| C1-S4 | Presign 200 parts in one request (aws4fetch, explicit expiry) | Within Paid CPU, URLs work from curl → windowed presign. Also measure Ed25519 verify for BUD-CPU-REQ. | SB | BUD-CPU-REQ | `SYN → results` | Not started (needs L01) | — |
| C1-S5 | Old client against an additive and a breaking v2 change | Additive change invisible; breaking change → typed `update_required` | CT | — | `SYN → results` | Running or pending (spike runner) | Pending |

## Conflicts with settled text

- **ADR-0001 §1** names Cloudflare Queues as the notification path ("it pulls events from the queue"). F5 recommends a Worker event feed instead in v1. ADR-0001 already makes reconciliation mandatory and calls the queue "only a notification path", so the change is to the mechanism, not to the safety design. **DR-C1-3** (an "Amends: ADR-0001 §1" draft if accepted).
- **ADR-0001 §4** (objects keyed by dedup ID, exclusive claim): superseded in substance by per-upload keys and advisory leases. Already tracked as **OD-04** (A3 DR-A3-1, CE D-5). This note supplies the key layout and is consistent with it.
- **ADR-0001 §6** "expiring `restore/` prefix in R2": kept. It moves into its own bucket, which the ADR's wording allows (a prefix in R2).
- **CLAUDE.md** is not contradicted:
  - outbound-only (Workers VPC rejected);
  - append-only (devices get no DELETE, List or Copy, and no presigned URL on an existing key, SR-07);
  - no AWS (aws4fetch is a SigV4 client library and talks only to R2).

## Open questions

| # | Question | Who | By when |
|---|---|---|---|
| 1 | All of C1-S1 H1–H13 (create-only, presigned POST, signed length and checksums, abort extension, bucket locks, revocation delay) | C1-S1 on the sandbox (H5 L01) | Gate B |
| 2 | D1 contention under a real seed pattern: C1-S2/S3 numbers | Spike runner / SB | Gate B |
| 3 | Do query rates for check and commit stay batched in practice? Mean file size and small-file share | E1 census, A0 | Wave 2 |
| 4 | Request-auth format and whether it needs a KDF missing from Web Crypto | D3 (ADR-0014) | Gate C |
| 5 | Second bootstrap location (domain, host) and the config-signing key custody | Owner (DR-C1-4), D3, D5 | Gate C |
| 6 | Is the local-signing JWT format stable enough to depend on? Will Cloudflare publish a spec? | T2 watch list; C1-S1 H13 | Gate B |
| 7 | Bucket locks take precedence over lifecycle rules (C15), but does that include the default 7-day multipart abort, and do locks apply to in-progress uploads? | C1-S1 H9 | Gate B |
| 8 | Status code for `update_required` (426 vs 400 + code); whether the bootstrap signature reuses the update trust root (D5) | API draft; D5 | ADR-0010 draft |
| 9 | Primary sources for RFC 9457 and the Idempotency-Key draft status (blocked) | H1 | Before ADR-0010 cites them |
| 10 | Exact per-device counters: DO vs D1 counters vs the rate-limit binding | C2 | Wave 2 |

## Recommendation

Adopt for the ADR-0010 draft:
- the F1 topology (TS Worker on the owner's domain, one D1 database, two R2 buckets, optional per-device DOs, one Cron Trigger);
- the F3 key layout, with **no Expiration rule in the ingest bucket**;
- windowed presigned content uploads with ≤ 15-min URLs, and records through the Worker;
- the homelab polling a Worker feed and reconciling by listing, with Worker-minted, action-scoped temporary R2 credentials;
- the opaque-artifact rule for the Worker;
- the F8 API conventions;
- the F10 change-management rules.

**What would change this:**
- C1-S2/S3 showing D1 overload under batched endpoints → shard dedup and leases into DOs.
- C1-S1 H13 failing (temp credentials not enforced by action or key) → long-lived bucket token for the homelab.
- D3 needing a KDF absent from Web Crypto → add a Wasm module, not a Rust Worker.
- The owner preferring Queues (DR-C1-3) → R2 notifications on `meta/` as the hint source, with A3's ack-on-inbox-write rule.
- C1-S1 H2 or H9 giving reliable create-only on Complete → sign it in, still without relying on it.

## Decision requests

### DR-C1-1: Worker language: TypeScript, with the opaque-artifact rule
- **Needed by:** Wave 1 exit (it fixes how many implementations G2's vectors must cover)
- **Evidence:** F7; C32–C37
- **Options:**
  | Option | What it means for the family | Cost (money and owner time) | Reversibility | Risks |
  |---|---|---|---|---|
  | A. TypeScript (recommended) | Nothing visible | Small formats implemented twice; shared vectors | Costly after launch, but the API contract is language-neutral | Drift between implementations if vectors are skipped |
  | B. Rust `workers-rs` | Nothing visible | One implementation; nightly toolchain for panic recovery | Same | Beta platform; pre-1.0 crate; slower access to new platform features |
  | C. TS + Rust→Wasm for named functions | Nothing visible | Two toolchains in the Worker build | Easy | Build complexity |
- **Recommendation:** A, with C reserved for any function Web Crypto cannot do.
- **Touches settled text:** none
- **If no decision by the deadline:** the A0 skeleton uses A.

### DR-C1-2: Two R2 buckets; the ingest bucket never carries an Expiration rule
- **Needed by:** Gate B (one-way door #7)
- **Evidence:** F3; C12, C13, C17
- **Options:**
  | Option | What it means for the family | Cost | Reversibility | Risks |
  |---|---|---|---|---|
  | A. One bucket, prefixes | Nothing visible | Slightly simpler setup | Costly after first ingest (keys move) | A prefix typo in the lifecycle configuration can expire staging; tokens cannot separate restore from ingest |
  | B. `rq-ingest` + `rq-restore` (recommended) | Nothing visible | One more bucket to configure | Same | None found |
- **Recommendation:** B. "Staging never expires by age" becomes checkable by listing one bucket's rules.
- **Touches settled text:** none (ADR-0001 §6 says only "an expiring `restore/` prefix in R2")
- **If no decision by the deadline:** the skeleton uses B.

### DR-C1-3: Notification path in v1: Worker event feed polled by the homelab, not Queues
- **Needed by:** Wave 1 exit (OD-04 sitting), before the A0 skeleton fixes the homelab puller
- **Evidence:** F5; A3 C3–C7 (Queues retention, `max_retries`, lease contradiction, REST rate limit); S38
- **Options:**
  | Option | What it means for the family | Cost | Reversibility | Risks |
  |---|---|---|---|---|
  | A. Queues fed by R2 event notifications, pulled over HTTP (ADR-0001 wording) | Nothing visible | Queue operations in seed months; a Cloudflare API token on the homelab | Easy | REST 1,200/5 min lockout; delete-after-`max_retries`; another crown-jewel token |
  | B. Worker feed polled every ~30 s, plus listing (recommended) | Nothing visible; "stored at home" seconds slower at worst | About 86k Worker requests/month (inside included) | Easy (Queues can be added later as a hint) | Polling interval is a tunable |
  | C. DO WebSocket push | Nothing visible | More code | Easy | Reconnect and hibernation edge cases |
- **Recommendation:** B. It removes every Queues failure mode A3 found and needs no Cloudflare API token at home, while keeping reconciliation as the path of record.
- **Touches settled text:** ADR-0001 §1 ("Cloudflare Queues (object-staged events)"; "it pulls events from the queue"). This needs an "Amends: ADR-0001 §1" draft with ADR-0010, saying the notification path may be a Worker feed or Queues.
- **If no decision by the deadline:** the skeleton uses B as a v0 throwaway choice; ADR-0010 stays Proposed.

### DR-C1-4: API hostname and bootstrap: owner's domain plus a second, independent bootstrap location
- **Needed by:** Gate C (one-way door #8), but the domain choice is needed earlier for the sandbox (H1)
- **Evidence:** F8; C2, C39, C40
- **Options:**
  | Option | What it means for the family | Cost | Reversibility | Risks |
  |---|---|---|---|---|
  | A. `api.<owner-domain>` only | Nothing visible | Domain already owned; zone must be on Cloudflare | One-way once kits ship | Domain lapse or account loss strands every installed client |
  | B. A + a second bootstrap host on a different domain or provider, with a signed bootstrap document (recommended) | Nothing visible | One more domain registration (not priced here; C4/H5) and a config-signing key | One-way once kits ship | Key custody (D2/D5) |
  | C. `workers.dev` | — | — | — | Rejected by the PLAN |
- **Recommendation:** B.
- **Touches settled text:** none
- **If no decision by the deadline:** sandbox uses its throwaway domain; Gate C stays blocked.

### DR-C1-5 (input to OD-14): beta-feature dependencies of the control plane
- **Needed by:** Wave 0/1 (OD-14 sitting)
- **Evidence:** F10 table
- **Options:** A. Accept the intake B4 rule ("only with a documented, tested fallback that needs no client update") and the F10 classification (recommended). B. No beta or "coming soon" dependencies at all, which removes the temp-credential design for the homelab and leaves a long-lived bucket token.
- **Recommendation:** A. The only dependency is server-side, with a tested break-glass fallback.
- **Touches settled text:** none
- **If no decision by the deadline:** A is assumed for the skeleton.

## Hand-offs

| To | What | Why |
|---|---|---|
| A3 | Feed polling replaces queue hints in v1 (DR-C1-3); records go through the Worker; uniform `staging/<dedup_id>/<upload_id>/s<n>` keys | F3–F5 |
| A1 | Dedup-ID textual encoding length (key length, Worker validation) | F3 |
| D3 | Request-auth format (two implementations: Rust and TS); config-signing key for bootstrap; homelab control key; whether the device list is homelab-signed (rebuildability) | F6–F8 |
| D2 | Key inventory gains: homelab control key, config-signing key, R2 parent secret (Worker), break-glass R2 token (offline) | F5, F8 |
| C2 | `DeviceGate` DO for exact counters; `workers_dev = false` **and** preview URLs disabled; kill switch = roll the R2 parent token | F1, F4, C40 |
| C4 | Feed polling instead of Queues removes the Queues line; restore bucket is separate | F5 |
| C7 | Dead-man's switch via cron on the signed heartbeat | F9 |
| C8 | Nightly `export` of cloud-only tables; break-glass token runbook; rebuild into a new account changes the R2 host (clients must not pin it) | F6, F8 |
| B6 | Windowed presign; ETag formulas for local verification; part-size policy within C9 | F4 |
| G2 | Shared test vectors for every format the Worker implements | F7 |
| H1 | Log blocked sources (RFC Editor, datatracker, AWS docs, Cloudflare blog/status); add a new one-way-door note: bootstrap locations shipped in kits; track C-01 as proposed "off" | Method, F3 |
| T2 | Watch list: temp-credential local-signing format, R2 release notes for conditional Complete, D1 single-thread guidance | F10 |
