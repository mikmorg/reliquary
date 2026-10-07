# C1. Cloudflare control-plane mapping and API v1

- **Workstream:** C1 (see `docs/research/PLAN.md`, section "C1.")
- **Status:** Final for Wave 1. Two skeptic rounds (three lenses each: sources, logic, adversary), on 2026-10-06 and 2026-10-07. The verdicts below are the code-computed tally from the **second** round, which matches the first. Spike results are in. C1-S1 to C1-S4 ran only as local emulations (**emulated, not real R2/Cloudflare**). The real-sandbox kits still have to run (H5 L01: no sandbox account yet) and still lack some additions this note proposes, so their status is "kit-ready (pending additions)". C1-S5 ran for real. Owner decisions DR-C1-1 to DR-C1-7 are pending.
- **Date:** 2026-09-29 (scout sweep). Last updated 2026-10-07 (second synthesis). The run brief gives 2026-09-29 as "today". The container clock read 2026-10-06 during the first synthesis and 2026-10-07 during this one, so re-fetch dates below use those dates.
- **Feeds:**
  - ADR-0010, Proposed: [`docs/adr/0010-control-plane-topology-and-api-v1.md`](../adr/0010-control-plane-topology-and-api-v1.md)
  - [`docs/design/api-v1.md`](../design/api-v1.md) (Draft outline; the OpenAPI document follows in Wave 2)
  - one-way door #7 (R2 key layout, Gate B) and #8 (API hostname and bootstrap, Gate C)
  - inputs to OD-04 (C1-S1 evidence, key layout), OD-14 (beta policy), OD-17 (accepted risks) and OD-20 (staging cap)
  - DR-C1-1 to DR-C1-7 (H1 to number)
- **Depends on:**
  - A3 (`a3-ingest-protocol.md`: per-upload keys, advisory lease, reconciliation, receipts)
  - A1 (`docs/spec/identifiers.md`: dedup-ID text form `rd1-…`, alphabet `[a-z0-9-]`)
  - D1 (`d1-threat-model.md`; register `docs/security/threat-model.md`, SR-01…SR-31)
  - B4 (`b4-ios-decision.md`: K6, P6, IOS-C10, IOS-C16, DR-B4-2)
  - C4 (`c4-cost-model.md`, especially §F4.3 "create-only writes are mandatory" and the staging-cap derivation)
  - the CE spike (`content-encryption-format.md`), T2 (`fact-check-adr-0001-0002.md`)
  - G2-S1 (emulator fidelity)
  - H1 sandbox (L01; not yet available)
- **Traceability rows advanced:** R-09, R-11, R-12, R-13, R-18, R-37, Q1-3 (presigned UploadPart), C-01 (warm cache)

## Summary

Recommended for the ADR-0010 draft: a **TypeScript Worker on the owner's own domain; two D1 databases split by function (provisional); two R2 buckets; content uploaded to server-chosen "upload targets" (presigned R2 URLs or Worker-proxied parts); records posted through the Worker; a Worker event feed the homelab polls; R2 listing as the path of record; one Cron Trigger with synthetic canaries.** Durable Objects are used only where they alone fit: exact per-device counters for C2, kept in a separate Worker.

1. **D1 capacity is unproven, so the store is provisional.** D1 runs one query at a time per database (K1, verified). The claim that one `batch()` per request keeps load low is **contested** (K2, refuted by all three skeptics in both rounds). Batching saves round trips, but D1 runs a batch's statements "sequentially, non-concurrently", and write time depends on rows written, index rows included. This note claims no headroom. It now recommends **two D1 databases from day one**: `rq-dedup` (dedup, leases, uploads) and `rq-control` (everything else). The D1 FAQ recommends scaling out this way, and the split means an overloaded dedup database cannot also block enrollment and homelab commits. All access goes through a data-access layer, write SQL is set-based, and real-D1 kits decide whether `rq-dedup` must be sharded further.
2. **Content path: the choice is now open, with a rule for deciding it.** The previous draft dismissed Worker-proxied uploads because of the 100 MB request-body cap. That argument was invalid, because 5–16 MiB parts fit (K13). Re-evaluated:
   - Presigned UploadPart can **never** be create-only per part, because re-uploading a part number replaces the part (C9).
   - Presigned single PUT is create-only only if real R2 enforces a signed `If-None-Match` (C1-S1 H1, untested).
   - C4 §F4.3 holds that create-only writes are **mandatory**, both for the settled "never delete or rewrite" rule and for the BUD-ABUSE bound.
   - ADR-0010 therefore decides an **upload-target abstraction**: the server tells the client, for each part, where to send it and how to authenticate. Clients never care whether that is R2 or the Worker.
   - The default target kind is chosen at Gate B by a pre-agreed rule (F4, DR-C1-6), using real C1-S1 and a new Worker-proxied-part leg in the C1-S4 kit. C1 leans towards Worker-proxied parts for multipart objects, but the evidence is unmeasured, and choosing presigned-only means the owner accepts the staging-rewrite risk (OD-17).
3. **Key layout:** `rq-ingest` holds `staging/<dedup_id>/<upload_id>/s<n>` and `meta/<device_id>/<batch_id>.age`, and reserves `pack/<upload_id>/s<n>`. It **never has an Expiration rule**, and a token-free sentinel check guards that. `rq-restore` holds `restore/…` with an expiry. The 7-day multipart abort is treated as a **hard ceiling**. The layout presupposes OD-04 (per-upload keys).
4. **Worker language: TypeScript.** Rust on Workers is Beta, `workers-rs` is 0.8.7, and panic recovery needs nightly (K9, verified). The opaque-artifact rule keeps the second implementation small.
5. **R2 enforcement is still unknown.** Miniflare disagrees with the R2 docs on the checks that matter (K14, secondary-only), so only the real-sandbox C1-S1 kit can settle them. Until then, nothing depends on R2 enforcing create-only or checksums: homelab verification (SR-04) is the integrity basis.
6. **Short URLs are shown to work only where app code runs just before the transfer** (desktop daemon, Android WorkManager). K15 is **contested**, so iOS is not solved here. It stays with DR-B4-2. Worker-proxied parts are one of the iOS options, which is one more reason to keep the upload-target abstraction.
7. **Guard rails added in the second round** (adversary lens):
   - a cron **synthetic canary** for each R2 parent token, so a broken or rolled token pauses presigning with a typed retryable error instead of causing a silent client retry storm;
   - **staging-cost accounting** on max(declared, observed) bytes, and an **interim hard ceiling** asked of the owner now (DR-C1-7);
   - a written list of **Workers Paid dependencies**, so a lapsed card is detected;
   - a paginated export endpoint instead of `wrangler d1 export`, which blocks the database.

Confidence: **high** on the Cloudflare facts (11 of 15 key claims verified against primary docs). **Medium** on the topology and language. **Low** on D1 capacity, on the presigned-vs-proxied cost comparison, and on every R2 behaviour the real-sandbox kits have not yet run.

## Questions

| # | Question | Short answer | Confidence |
|---|---|---|---|
| 1 | D1 vs SQLite DOs vs hybrid for dedup index, claims, device registry, invites, quotas | **Two D1 databases from day one, provisionally:** `rq-dedup` (dedup, leases, uploads, staged-bytes accounting) and `rq-control` (accounts, devices, invites, feed, receipts, audit, idempotency). Per-device counter DOs (C2's call) live in a separate Worker. If real D1 is too slow, the next step is to shard `rq-dedup` by ID prefix into N D1 databases or 16 SQLite DOs. A data-access layer hides all of this. F2. | Medium-low (capacity not measured; K2 contested) |
| 2 | Is D1's single thread a ceiling during a 25-device seed? | **Unknown until measured.** Using C4's w = 6 rows written per file (index rows must be included; C62), 5 ms per row-write (an assumption) and an assumed 62.5 MB/s family peak, one database saturates at a mean file size of about 1.9 MB. Batching does not change that number. Splitting off `rq-dedup` takes non-dedup load off that thread. The C1-S2/S3 kits must measure per-statement vs per-row cost. F2. | Low |
| 3 | How to shard DOs, if used | Counters: one DO per device (`idFromName(device_id)`), in a separate `rq-gate` Worker. Dedup and leases: only at the sharding step, 16 shards on a dedup-ID character. Never one global DO. A **per-family DO** variant is added to the real kits rather than dismissed by assertion. | Medium |
| 4 | Key layout; one bucket or several | Two buckets (DR-C1-2, conditional on OD-04). `rq-ingest`: `staging/<dedup_id>/<upload_id>/s<n>`, `meta/<device_id>/<batch_id>.age`, reserved `pack/<upload_id>/s<n>`, and `staging/_sentinel/<date>` (cannot collide with `rd1-…` IDs). `rq-restore`: `restore/<device_id>/<job_id>/<object_id>`. F3. | Medium-high |
| 5 | Staging expiry vs worst outage; 7-day multipart abort | Ingest bucket: **no Expiration rule ever**; only the homelab deletes. The default 7-day abort removes only incomplete multipart uploads. Treat it as a **hard ceiling**: the doc example says the earlier rule wins (K6). Uploads that might outlive 7 days use A3's segment checkpoint as their primary mechanism, or USB. | High (docs); Medium (earliest-wins reading) |
| 6 | Which cloud state needs backup | Cloud-only, so it needs a nightly homelab-pulled export: accounts and verification state, hashed invites, enrollment tokens and pairing codes, the email suppression list, and the audit log. Rebuildable from the homelab: committed set, receipt relay, revocations, heartbeat, and devices (if D3 adopts a homelab-signed list). Disposable: leases, idempotency rows, counters, feed. The export is a paginated, signed Worker endpoint, never `wrangler d1 export` on production (it blocks the database, C60). F6. | Medium-high |
| 7 | Notifications | **Pending DR-C1-3.** B (a Worker event feed polled about every 30 s, plus R2 listing) and D (R2 notifications → Queue → push consumer Worker → the same feed) are **roughly equal**, and B is preferred by a small margin. The gains over ADR-0001 §1's Queues HTTP pull are real but modest. F5. | Medium |
| 8 | Homelab authentication | To the Worker: requests signed with a homelab Ed25519 control key. To R2: Worker-minted temporary credentials, TTL ≤ 1 h, one per bucket. Fallback ladder: local-JWT action scoping → Temporary Credentials API with a preset scope plus prefixes (C63) → offline break-glass token. **These are proposals handed to C2 and D3**, which own scoping, rotation and revocation. F5. | Medium |
| 9 | Workers VPC / Tunnel push | **Rejected.** The Tunnel itself is an outbound connection, so the objection is not network direction. It is that the cloud would **initiate application requests** to homelab services, so a compromised Worker or Cloudflare account could reach the homelab. It is also Beta (K11). | High |
| 10 | Worker language | **TypeScript**, under the opaque-artifact rule (DR-C1-1). F7. | Medium |
| 11 | CPU and subrequests when presigning hundreds of parts | Presigning makes no subrequests (K3) and is local HMAC work. Emulated C1-S4: 200 URLs in one call, local p50 22 ms. That indicates fit but is not Cloudflare CPU accounting. A 15-min window is about 134 parts of 16 MiB at 20 Mbit/s. Always set `X-Amz-Expires` (aws4fetch defaults to 24 h). Pin aws4fetch and cross-check it against a second SigV4 implementation in G2 vectors. F4, F7. | High (no subrequests); Low (CPU, emulated) |
| 12 | API conventions | `/v1/`, additive-only, with the **C1-S5 rules**: tolerant enums or version-gated enum additions; `min_version` raised in the same deploy as any breaking change; request schemas strip unknown keys. RFC 9457 problems. `update_required` uses **400**, not 426, because RFC 9110 requires an `Upgrade` header on 426; C1-S5 is to be re-run with 400. F8. | Medium-high |
| 13 | API on the owner's domain | Workers Custom Domain, which needs an active Cloudflare zone and no existing CNAME. `workers_dev = false` **in config**; the config is the source of truth, because a dashboard-only disable is undone by the next deploy. Version, Preview **and Deployment** URLs must be handled separately (K12). Consider a **dedicated Reliquary domain** on Cloudflare rather than moving the family's main zone (DR-C1-4). Clients never pin the R2 host. | High |
| 14 | Background jobs | One Cron Trigger (about every 15 min) runs idempotent "what is due" queries: stale devices, nudges, the dead-man's switch, the day-6 multipart checkpoint, **R2 parent-token canaries**, staging sentinels, D1 size alerts and pruning, and plan or quota error alerts. DO alarms only inside counter DOs. No Workflows in v1. F9. | Medium-high |
| 15 | Change management | **No gradual deployments in v1**: plain `wrangler deploy`. Expand/contract D1 migrations are still required, because migrations and code deploys are not atomic. DO classes go in a separate Worker, because `exports` disables `versions upload` and gradual deployments for the Worker that declares them (K10). F10. | High (docs); Medium (policy) |
| 16 | Beta dependencies (OD-14 input) | Avoided: Rust Workers, Workers VPC, D1 read replication, gradual deployments (by choice). One dependency: temp-credential action scoping, which works by local signing only ("API support coming soon"). It is server-side only, with a two-step fallback (API preset scope, then break-glass) that is **documented but not yet tested** (DR-C1-5). | High (facts); Medium (policy) |
| 17 | Device multipart without per-part presigning? | Possible with a one-key temporary credential, but no SigV4 on devices in v1. Parked for desktop. | Medium |
| 18 | Records: presigned PUT or through the Worker? | Through the Worker, with create-only `onlyIf` and the SHA-256 in custom metadata. A retry after a precondition failure is answered by comparing hashes (F4). | Medium-high |
| 18b | Short URLs vs OS background queues | Desktop and Android: re-sign just in time, or on the specific expired-URL error, with a **Worker-enforced** cap. **iOS: not solved here** (K15 contested). Options are one of IOS-C10, Worker-proxied parts, or DR-B4-2. F12. | Medium (v1 platforms); Low (iOS) |
| 19 | Warm cache (C-01) | Off in v1 (window 0). If enabled later: a homelab-side delay before deletion, never a lifecycle rule. | Medium |
| 20 | What stops staging cost growing without bound when the homelab is down? | Worker-side accounting of declared bytes; a daily Worker-side `list()` of observed bytes; homelab-observed bytes and a count of open multipart uploads; a cap keyed on max(declared, observed); a "committed but not deleted" alert; a presign pause on a stale heartbeat; Cloudflare billing notifications. **An interim hard ceiling** is asked of the owner now (DR-C1-7, OD-20). F4. | Medium |
| 21 | (new) Presigned URLs vs Worker-proxied parts | **Decided:** server-chosen upload targets, so the choice can change without a client update. **Open:** the default kind, chosen by the F4 rule at Gate B. C1 leans to proxied parts for multipart objects. F4. | Medium (abstraction); Low (default kind) |
| 22 | (new) How is a broken credential, a plan lapse or an R2 outage detected? | Cron canaries per parent token. On failure the Worker sets a presign-paused flag, returns `503 r2_credentials_unavailable` (retryable), and alerts the owner out of band (C3/C7). Plus alerts on CPU-limit and D1 quota errors, and a C2 card-expiry check. F9, F10. | Medium |

## Method

- **Sweep:** four scouts ran: docs, source, community issues, and pricing/standards.
- **Deep read:** the analyst re-fetched every Cloudflare source behind a key claim from `cloudflare/cloudflare-docs @ production` on raw.githubusercontent.com (2026-10-06). Source checks: `workers-rs` README, `worker` 0.8.7 crate source, `aws4fetch` 1.0.20 tarball, npm and crates.io metadata.
- **Spikes:**
  - A spike runner ran C1-S1 to C1-S4 against local Miniflare/workerd (**emulated, not real R2/Cloudflare**) and wrote a real-sandbox kit for each.
  - C1-S5 ran for real as a CT spike. Its subject is the API contract, not Cloudflare.
- **Skeptic stage, two rounds.** Round 1 was on 2026-10-06. Round 2, on 2026-10-07, reviewed the analyst's JSON payload; part of that payload was stale against the round-1 synthesis. Each round had three skeptics (sources, logic, adversary) over key claims K1–K15. The verdicts in §Claims are round 2's code-computed tally:
  - **verified** = has a primary source and at least 2 of 3 skeptics did not refute it;
  - **secondary-only** = no primary source;
  - **contested** = otherwise.
  The two rounds produced the same verdicts.
- **Synthesis re-reads.**
  - 2026-10-06: the D1 `batch()` doc; the D1 FAQ partial; the DO class-exports page (lines 540–541); the object-lifecycles page; the gradual-deployments index; the Web Crypto table; R2 release notes 2023-06-16; RFC 9457, the Idempotency-Key draft and RFC 9110 §15.5.22 (WG raw copies).
  - **2026-10-07** (second synthesis, raw GitHub, container clock 2026-10-07T01:26Z):
    - `d1/best-practices/import-export-data.mdx`: "A running export will block other database requests."
    - `d1/reference/time-travel.mdx`: "up to 30 days in the past (Workers Paid plan) or 7 days (Workers Free plan)".
    - `d1/platform/limits.mdx`: "Queries per Worker invocation … 1000 (Workers Paid) / 50 (Free)".
    - `partials/workers/d1-pricing.mdx`, note 6: "Indexes will add an additional written row when writes include the indexed column".
    - `r2/api/s3/temporary-credentials.mdx`: the API takes a parent API token; `scope` presets `object-read-only` and `object-read-write`; API `prefixes` and `objects`; "`actions` is currently supported via local signing only".
    - `workers/configuration/routing/workers-dev.mdx`, line 64 (Deployment URLs).
    - `release-notes/r2.yaml`, 2023-08-11 (conditional multipart publish).
    - `r2/api/s3/api.mdx` checksum table (CRC64NVME).
- **Routes used:** raw.githubusercontent.com (Cloudflare docs source, `ietf-wg-httpapi/*`, `httpwg/httpwg.github.io`), registry.npmjs.org, static.crates.io, the crates.io API. Context7 was not used.
- **Blocked sources** (none silently replaced; reported to H1):
  - developers.cloudflare.com. The docs' own source repo was used, with the same content; per-file commit dates were not retrieved.
  - docs.aws.amazon.com (S3 conditional-write reference behaviour).
  - rfc-editor.org and datatracker. The RFC texts were read through the working groups' raw GitHub copies and are cited as "editor's copy, not the published RFC text". The Idempotency-Key draft's publication status is unconfirmed.
  - blog.cloudflare.com and cloudflarestatus.com.
  - The github.com web UI for issue bodies.
- **Not found:** the sources skeptic cites an R2 release note of 2025-07-03 about CRC64NVME on multipart uploads. It is **not** in `release-notes/r2.yaml` at production head (2026-10-07). Only the api.mdx checksum table (CRC64NVME = FULL_OBJECT) was confirmed.
- **Stop rule:** the second-round re-reads added primary text but no new source class. The sweep is closed for Wave 1.

## Sources

All Cloudflare docs are `cloudflare/cloudflare-docs @ production : src/content/…`, the source of developers.cloudflare.com, at branch head (commit dates not retrieved). Raw base: `https://raw.githubusercontent.com/cloudflare/cloudflare-docs/production/src/content/`.

| # | Source | Publisher | Published or version date | Accessed | Primary? |
|---|---|---|---|---|---|
| S1 | R2 Presigned URLs, `docs/r2/api/s3/presigned-urls.mdx` | Cloudflare | production head | 2026-10-06; skeptics 2026-10-07 | Yes |
| S2 | R2 S3 API compatibility, `docs/r2/api/s3/api.mdx` | Cloudflare | production head | 2026-10-07 | Yes |
| S3 | R2 Temporary credentials, `docs/r2/api/s3/temporary-credentials.mdx` | Cloudflare | production head | 2026-10-07 | Yes |
| S4 | R2 example "Authenticate against R2 with temporary credentials", `docs/r2/examples/authenticate-r2-temp-credentials.mdx` | Cloudflare | reviewed 2026-04-19 | 2026-10-06 | Yes |
| S5 | R2 API tokens, `docs/r2/api/tokens.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S6 | R2 Object lifecycles, `docs/r2/buckets/object-lifecycles.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S7 | R2 Bucket locks, `docs/r2/buckets/bucket-locks.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S8 | R2 Limits, `docs/r2/platform/limits.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S9 | R2 Consistency, `docs/r2/reference/consistency.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S10 | R2 Workers API reference, `docs/r2/api/workers/workers-api-reference.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S11 | R2 release notes, `release-notes/r2.yaml` | Cloudflare | latest entry 2026-04-27 | 2026-10-07 | Yes |
| S12 | R2 Upload objects, `docs/r2/objects/upload-objects.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S13 | R2 Event notifications, `docs/r2/buckets/event-notifications.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S14 | D1 limits FAQ partial, `partials/d1/faq-limits.mdx` | Cloudflare | production head | 2026-10-06; skeptics 2026-10-07 | Yes |
| S15 | D1 Limits, `docs/d1/platform/limits.mdx` | Cloudflare | production head | 2026-10-07 | Yes |
| S16 | D1 Worker API, `docs/d1/worker-api/d1-database.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S17 | D1 Query JSON, `docs/d1/sql-api/query-json.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S18 | D1 Time Travel, `docs/d1/reference/time-travel.mdx` | Cloudflare | production head | 2026-10-07 | Yes |
| S19 | D1 read replication, `docs/d1/best-practices/read-replication.mdx` | Cloudflare | production head (Beta) | 2026-10-06 | Yes |
| S20 | D1 Migrations, `docs/d1/reference/migrations.mdx` | Cloudflare | production head | 2026-09-29 | Yes |
| S21 | DO limits FAQ partial, `partials/durable-objects/do-faq-limits.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S22 | DO Limits, `docs/durable-objects/platform/limits.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S23 | DO SQLite storage API, `docs/durable-objects/api/sqlite-storage-api.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S24 | DO class exports / lifecycle, `docs/durable-objects/reference/durable-objects-migrations.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S25 | DO Alarms, `docs/durable-objects/api/alarms.mdx` | Cloudflare | production head | 2026-09-29 | Yes |
| S26 | Workers Limits, `docs/workers/platform/limits.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S27 | Gradual deployments: `…/gradual-deployments/index.mdx` (per-request routing, line 98; version affinity) and `…/with-durable-objects.mdx` (version pinning per DO) | Cloudflare | production head | 2026-10-06 | Yes |
| S28 | Compatibility dates, `docs/workers/configuration/compatibility-dates.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S29 | Cron Triggers, `docs/workers/configuration/cron-triggers.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S30 | Workflows Limits, `docs/workflows/reference/limits.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S31 | Workers Custom Domains and `workers.dev` routing, `docs/workers/configuration/routing/{custom-domains,workers-dev}.mdx` | Cloudflare | production head | 2026-10-07 | Yes |
| S32 | Web Crypto, `docs/workers/runtime-apis/web-crypto.mdx` | Cloudflare | production head | 2026-10-06 | Yes |
| S33 | Rust language page, `docs/workers/languages/rust/index.mdx` (Beta) | Cloudflare | production head | 2026-10-06 | Yes |
| S34 | `cloudflare/workers-rs @ main : README.md` | Cloudflare | main head | 2026-10-06; skeptics 2026-10-07 | Yes |
| S35 | `worker` crate 0.8.7 source and crates.io API | Cloudflare / crates.io | 0.8.7, 2026-09-25T23:41Z | 2026-10-06; skeptics 2026-10-07 | Yes |
| S36 | `aws4fetch` 1.0.20 tarball, `dist/aws4fetch.esm.mjs` | M. Hart | 1.0.20, 2024-08-28 (last npm publish) | 2026-10-06 | Yes |
| S37 | Workers VPC overview, `docs/workers-vpc/index.mdx` (Beta) | Cloudflare | production head | 2026-10-06 | Yes |
| S38 | Queues pull consumers and limits | Cloudflare | production head | 2026-09-29 (A3 read in full) | Yes |
| S39 | npm registry metadata (wrangler, miniflare, hono, aws4fetch, vitest-pool-workers, drizzle-orm, kysely, chanfana, zod) | npm | as listed | 2026-10-06 | Yes |
| S40 | Project notes: A3; D1; CE; **C4** (`c4-cost-model.md`: w = 6 rows/file; s̄ = 4 MB; Class A $4.50/M; Workers $0.30/M requests and $0.02/M CPU-ms; §F4.3 "create-only writes are mandatory"; E_eff = 900 replays per URL; staging cap ≈ 1.3 TB at $25); `data-model.md` | Project | drafts | 2026-10-07 | Yes (project) |
| S41 | workerd #2572, #6561, #7190 | Cloudflare repo, users | 2024-08-21 to 2026-08-30 | 2026-09-29 | No |
| S42 | workers-sdk #14916, #15774, #15387, #15904 | users | 2026-07-29 to 2026-09-27 | 2026-09-29 | No |
| S43 | workers-rs #166, #453, #826, #967 | users | 2022-04 to 2026-04 | 2026-09-29 | No |
| S44 | Ente museum, Immich, restic rest-server, Headscale source | projects | main heads | 2026-09-29 | Yes |
| S45 | G2-S1 emulator fidelity, `spikes/G2-S1/results/comparison.md` (Miniflare run `127a684a`; **emulated**) | Project | 2026-09-29 | 2026-10-07 | Project measurement of an emulator; nothing about R2 |
| S46 | Threat register, `docs/security/threat-model.md` | Project (D1) | draft | 2026-10-06 | Yes (project) |
| S47 | B4 iOS decision note, `docs/research/b4-ios-decision.md` (K6, P6, IOS-C10, IOS-C16, DR-B4-2) | Project (B4) | draft | 2026-10-06 | Yes (project; Apple sources cited there) |
| S48 | RFC 9457 Problem Details, WG editor's copy `ietf-wg-httpapi/rfc7807bis @ main` | IETF HTTPAPI WG | editor's copy, not the published RFC text | 2026-10-06 | Yes (editor's copy) |
| S49 | Idempotency-Key header draft, `ietf-wg-httpapi/idempotency @ main` (`-latest`) | IETF HTTPAPI WG | editor's copy; publication status not confirmed | 2026-10-06 | Yes (draft) |
| S50 | RFC 9110 HTTP Semantics, `httpwg/httpwg.github.io @ main : specs/rfc9110.html`, §15.5.22 | IETF HTTP WG mirror | RFC 9110 (2022) | 2026-10-06 | Yes (mirror) |
| S51 | C1 spike results (emulated except C1-S5): `spikes/C1-S1` … `spikes/C1-S5` | Project (spike runner) | 2026-10-06 | 2026-10-07 | Project measurements; emulated ones say nothing about Cloudflare |
| S52 | Apple `isDiscretionary` (developer.apple.com JSON), as cited by the sources skeptic and in B4 | Apple | current | 2026-10-06 (skeptic) | Yes |
| S53 | D1 import and export, `docs/d1/best-practices/import-export-data.mdx` | Cloudflare | production head | 2026-10-07 | Yes |
| S54 | D1 pricing partial, `partials/workers/d1-pricing.mdx` (notes 1–7) | Cloudflare | production head | 2026-10-07 | Yes |
| S55 | Dedup-ID text form, `docs/spec/identifiers.md` (`rd1-` prefix, alphabet `[a-z0-9-]`) | Project (A1) | draft | 2026-10-07 | Yes (project) |

## Claims

### Key claims (skeptic-reviewed; verdicts are the code-computed tally, round 2)

Skeptics: 1 = sources, 2 = logic, 3 = adversary/cost. "Upheld" means not refuted. The reasons are round 2's (2026-10-07). Round 1 reached the same verdicts.

| # | Claim | Sources | Skeptic 1 | Skeptic 2 | Skeptic 3 | Verdict |
|---|---|---|---|---|---|---|
| K1 | Each D1 database is single-threaded and runs queries one at a time (about 1,000 q/s at 1 ms, 10 q/s at 100 ms). A full queue returns "overloaded". Each database is backed by one DO. Writes can take several ms. | S14 | Upheld, quoted word for word; the page also says write time depends on rows written and recommends scaling out across smaller databases | Upheld; it cannot be used as evidence that batching relieves the single thread | Upheld; one overloaded database is a **family-wide failure domain** (enrollment, commits, presign) | **Verified** |
| K2 | One D1 `batch()` per API request keeps aggregate load at about 0.47 thread-s/s (25 devices × 20 Mbit/s, 2 MB files, 3 writes/file, 5 ms/write). A 1M-ID presence check costs far under $1 via `json_each`. | S14, S17, S40 | **Refuted**: 0.47 is the unbatched figure; `batch()` runs statements "sequentially, non-concurrently"; C4's w = 6 gives ≈ 0.94; 5 ms is unsourced; the cost half rests on emulated `rows_read` | **Refuted**: same; reads, feed polls and homelab commits omitted; no primary source for any premise | **Refuted**: same; index rows add written rows (S54 note 6); a scan plan would cost ≈ $5 per 1M IDs | **Contested.** Withdrawn as stated and not used as support anywhere. F2 states capacity as unmeasured; the cost half is kept only as "indicative, emulated" |
| K3 | Presigned URLs: GET, HEAD, PUT, DELETE only; 1 s – 7 days; made with no call to R2; reusable bearer tokens; S3 domain only, not custom domains. The documented example signs only `host` with UNSIGNED-PAYLOAD. | S1 | Upheld; the example is a GET | Upheld; the POST exclusion is about HTML-form POST, so presigned Create/Complete are undocumented, not excluded | Upheld; same caveats | **Verified** |
| K4 | S3 table: If-None-Match for PutObject, no conditionals for CompleteMultipartUpload. Release note 2023-08-11: a failed conditional completion aborts the upload. Release note 2022-05-27: conditional CreateMultipartUpload returns 412. | S2, S11 | Upheld; the 2023 note does not say whether it covers the S3 API, the binding, or both | Upheld; "unresolved", not a contradiction | Upheld; a failed conditional Complete would also waste a whole part set of paid operations | **Verified** |
| K5 | R2 supports SHA-256 (and SHA-1, CRC32, CRC32C) only as COMPOSITE; CRC64NVME is the only FULL_OBJECT type. UploadPart lists Content-MD5 and no `x-amz-checksum-*`. | S2 | Upheld; the table is internally inconsistent (PutObject also omits checksums, yet a release note says putObject supports sha256); CRC64NVME FULL_OBJECT is a non-cryptographic transport check not used | Upheld; weak negative evidence | Upheld | **Verified.** "Integrity rests on per-part MD5" stays soft; homelab verification is the basis. CRC64NVME becomes proposed H16 |
| K6 | Default lifecycle rule aborts multipart uploads 7 days after initiation; up to 1,000 rules; deletion lags (typically ≤ 24 h); whether a longer abort overrides the default is not documented. | S6 | Upheld; the example comment implies earliest-wins | Upheld; plan for a hard 7-day ceiling | Upheld; "typically", with no upper bound | **Verified**; wording corrected (F3) |
| K7 | Long-lived tokens: four levels, only Object-level scoped to buckets, no prefix scope, no delete split. Temp credentials: one bucket, action and path scope; action scoping by local HS256 signing only ("coming soon"); revoking the parent stops them "immediately". | S3, S4, S5 | Upheld; the derivation is specified in prose; only the claim names (bucket, actions, expiry) come solely from the example | Upheld; the payload schema's stability and the max TTL are undocumented | Upheld; no max TTL stated | **Verified**, restated precisely (F5) |
| K8 | API-key permission changes are eventually consistent ("up to a minute"); the temp-credential page says revoking the parent is "immediate"; last writer wins on one key. | S9, S3 | Upheld; neither page covers *rolling* a token | Upheld; "disagree" is over-read; the kill-switch inference is unsupported | Upheld; a roll is a family-wide upload outage | **Verified.** No "conflict" framing; roll semantics unknown (H11) |
| K9 | Rust on Workers is Beta; `worker` 0.8.7 (2026-09-25) aborts on panic by default; `--panic-unwind` needs nightly with `-Zbuild-std`. | S33, S34, S35 | Upheld | Upheld; the choice also depends on ADR-0003 | Upheld; GA TypeScript is the lower burden for one owner | **Verified** |
| K10 | Gradual deployments route each request independently; each DO is pinned to one version per deployment; lifecycle changes only via `wrangler deploy`; `versions upload` fails fast with `exports`. | S27, S24 | Upheld; the per-request split is on `gradual-deployments/index.mdx` (now cited) | Upheld; expand/contract follows from non-atomic migrate/deploy, not from K10 alone | Upheld; DOs belong in a separate Worker | **Verified** |
| K11 | Workers VPC is Beta and has the Worker initiate requests into the private network through a Tunnel. | S37 | Upheld; a Tunnel is outbound at network level, so the rejection must rest on trust direction | Upheld | Upheld | **Verified**; rationale reworded (Q9) |
| K12 | Custom Domain needs an active Cloudflare zone and no existing CNAME; `workers_dev = false` in config; disabling `workers.dev` does not disable Version or Preview URLs. | S31 | Upheld; Deployment URLs omitted; a dashboard-only disable is re-enabled by the next deploy | Upheld; same | Upheld; an active zone puts the domain's DNS on the API's account | **Verified** (Deployment URLs added; config is the source of truth) |
| K13 | Request body 100 MB Free/Pro, 200 MB Business, up to 5 GB Enterprise; 30 s grace on runtime updates, "very unlikely" to matter. | S26 | Upheld | Upheld as fact; **the use made of it is invalid**: 5–16 MiB parts fit, so it is no reason against proxying | Upheld | **Verified.** No longer cited against Worker-proxied parts (F4) |
| K14 | Emulated only: Miniflare's R2 S3 endpoint ignores `x-amz-checksum-sha256`, overwrites on conditional Complete, returns 200 on conditional Create, lacks ListParts and lifecycle, so local runs cannot settle C1-S1. | S45 | Upheld; on Complete, Miniflare matches the S3 table; missing lifecycle is an absence, not a disagreement | Upheld; same | Upheld; same | **Secondary-only** (project evidence about an emulator, nothing about R2) |
| K15 | iOS background transfers are discretionary, so a 15-min URL can expire before sending; a re-sign endpoint keeps the revocation window without longer URLs. | S47, S1 | **Refuted**: the premise holds; the remedy is inference; no app code runs before a queued iOS transfer | **Refuted**: holds only for desktop and Android WorkManager; other IOS-C10 options exist | **Refuted**: re-sign-on-failure can cycle, and each failed attempt may send a whole part | **Contested.** Re-scoped to desktop and Android (F12); iOS stays with DR-B4-2 |

### Other claims (not key; not separately skeptic-reviewed)

The analyst draft's detailed claim rows C1–C53 were folded into the key claims above; their full wording is in the git history of this file. Mapping: K1 ← C27; K2 ← F2 arithmetic, C24, C26; K3 ← C1–C4; K4 ← C5, C7, C8, C49; K5 ← C5, C6; K6 ← C13, C17; K7 ← C10–C12, C51; K8 ← C11, C14; K9 ← C32–C34; K10 ← C42, C43; K11 ← C38; K12 ← C39, C40; K13 ← C20, C22, C50; K14 ← C52; K15 ← C53. A row tied to a key claim carries that claim's verdict.

| # | Claim | Sources | Status |
|---|---|---|---|
| C9 | Uploading the same part number again replaces the earlier part; part ETag = MD5; multipart ETag = MD5(concatenated part MD5s)-N; equal part sizes except the last (5 MiB – 5 GiB) | S2, S12 | Primary. Emulated C1-S1: the object formula holds; Miniflare part ETags are not MD5 |
| C15 | Bucket locks block deletion and overwrite for Age or Indefinite per prefix; the longest wins; locks take precedence over lifecycle rules; nothing is said about in-progress multipart uploads | S7 | Primary |
| C16 | Binding `put()` takes `onlyIf` and a sha256 option; `resumeMultipartUpload` does not validate the uploadId | S10 | Primary. Emulated C1-S1 C10, C14 consistent |
| C18 | R2: 1,024-byte keys; 10,000 parts; 1 write/s per key (429 above); REST API 1,200 req / 5 min per account | S8 | Primary |
| C19 | Max single upload or part 4.995 GiB; multipart 4.995 TiB | S8 | Primary |
| C21 | Workers Paid: CPU 30 s default (5 min max); 10,000 subrequests default; 128 MB; 64 MiB script | S26 | Primary |
| C23 | Cron CPU 30 s (< 1 h interval); wall 15 min; UTC; changes take up to 15 min to propagate | S26, S29 | Primary |
| C24 | D1 `batch()`: "reduces latency from network round trips"; statements "execute and commit, sequentially, non-concurrently"; one transaction; failure rolls back | S16 | Primary; quoted by all three skeptics in both rounds |
| C25 | D1: 10 GB per database ("cannot be further increased"); 100 bound parameters; 100 KB statement; 1,000 queries per invocation (Paid) | S14, S15 | Primary |
| C26 | `json_each` expands one bound JSON array for `IN (SELECT value FROM json_each(?))` | S17 | Primary |
| C28 | D1 Time Travel 30 days on Paid (CLI); DO PITR 30 days from object code only, not local | S18, S23 | Primary |
| C29 | D1 read replication is Beta | S19 | Primary |
| C30 | DO: single-threaded, ~1,000 req/s soft; 10 GB per object; `transactionSync()` | S21–S23 | Primary |
| C31 | DO alarms are at-least-once, with 6 retries | S25 | Primary |
| C35 | workers-rs panic-handling issue history | S43 | **Secondary only** |
| C36 | aws4fetch defaults `X-Amz-Expires` to 86,400 s, signs UNSIGNED-PAYLOAD unless set, excludes content-length unless `allHeaders`, caches the signing key per day; last published 2024-08-28 | S36, S39 | Primary (source); emulated C1-S1 confirms the signing behaviour |
| C37 | Workers Web Crypto has Ed25519, X25519, HMAC, SHA-256, and MD5 (non-standard, "do not rely upon MD5 for security") | S32 | Primary |
| C41 | Old compatibility dates are supported forever | S28 | Primary |
| C44 | The Workflows limits page cites 3/10 MB script size; Workers limits say 64 MiB | S30, S26 | Primary; doc inconsistency |
| C45 | Wildcard-etag bug (#2572, closed); local `SQLITE_BUSY` crash (#14916) | S41, S42 | **Secondary only**. Emulated C1-S1 H12 passed on the pinned versions |
| C46 | Workflows Paid limits | S30 | Primary; not used in v1 |
| C47 | Tool versions on 2026-10-06: wrangler 4.148.0; miniflare 5.20261006.0-alpha (the `latest` tag is an alpha); hono 4.13.13; aws4fetch 1.0.20; vitest-pool-workers 0.22.0; drizzle-orm 0.45.3; kysely 0.29.6; chanfana 3.4.0; zod 4.6.5 | S39 | Primary (registry) |
| C54 | D1 FAQ: "D1 is designed for horizontal scale out across multiple, smaller (10 GB) databases" | S14 | Primary; supports the two-database start |
| C55 | Gradual deployments support version affinity | S27 | Primary |
| C56 | R2 release note 2023-06-16: CopyObject can be conditional on the destination object's state | S11 | Primary |
| C57 | RFC 9110 §15.5.22: "The server MUST send an Upgrade header field in a 426 response" | S50 | Primary (mirror) |
| C58 | RFC 9457: `application/problem+json`; members `type`, `status`, `title`, `detail`, `instance`; clients "MUST ignore any such extensions that they don't recognize" | S48 | Primary (editor's copy) |
| C59 | Idempotency-Key draft: missing key → 400; reuse with a different payload → 422; retry while in progress → 409; publish an expiry policy | S49 | Primary (draft; status unconfirmed) |
| C60 | (new) "A running export will block other database requests." | S53 | Primary (2026-10-07) |
| C61 | (new) Workers Free: D1 queries per invocation 50 (Paid 1,000); Time Travel 7 days (Paid 30) | S15, S18 | Primary (2026-10-07) |
| C62 | (new) "Indexes will add an additional written row when writes include the indexed column" | S54 note 6 | Primary (2026-10-07) |
| C63 | (new) The Temporary Credentials API "accepts a parent API token, the bucket name, and optional scoping parameters"; `scope` presets `object-read-only` / `object-read-write`; API `prefixes` and `objects` fields; `actions` "via local signing only" | S3 | Primary (2026-10-07) |
| C64 | (new) Release note 2023-08-11: "Users can now complete conditional multipart publish operations. When a condition failure occurs … the upload is no longer available and is treated as aborted." No API surface named | S11 | Primary (2026-10-07) |
| C65 | (new, from C4) R2 Class A $4.50/M (Standard); DeleteObject and AbortMultipartUpload free; Workers $0.30/M requests, $0.02/M CPU-ms above the included amounts | S40 (C4 K2, C4, C5; verified there) | Primary via C4 |

## Findings

### F1. Topology (for ADR-0010)

| Component | Role | Holds | Notes |
|---|---|---|---|
| **Worker `rq-api`** (TypeScript) on `api.<owner-domain>` | Device, homelab and enrollment API; presigning; optional part proxy; minting homelab temp credentials; writing records to R2; cron | R2 parent secrets (F4), R2 and D1 bindings, the homelab's **public** control key | No trust-forging key (SR-23). `workers_dev = false` in config; Preview, Version and Deployment URLs handled (K12). **Declares no DO classes**, so it keeps `versions upload` (K10). |
| **D1 `rq-dedup`** | Dedup index, leases, uploads, staged-bytes accounting (provisional; F2) | F6 tables | Set-based writes; the hottest store. |
| **D1 `rq-control`** | Everything else: accounts, devices, invites, feed, receipt relay, idempotency, audit | F6 tables | Isolates enrollment and homelab commits from dedup load. |
| **Worker `rq-gate`** + DO class `DeviceGate` (optional; C2 decides) | Exact per-device counters | Small per-device SQLite | Bound from `rq-api` by `script_name`. Deployed only with plain `wrangler deploy`. |
| **R2 `rq-ingest`** | Content and record staging | `staging/`, `meta/`, reserved `pack/`, sentinels | **No Expiration rule, ever.** Default 7-day multipart abort only. |
| **R2 `rq-restore`** | Restore staging (ADR-0001 §6) | `restore/` | Expiration (e.g. 7 days) plus a 1-day abort rule. |
| **Cron Trigger** | Due-work runner and canaries | — | F9. |
| Queues, R2 event notifications | Pending DR-C1-3 (option D uses them) | — | F5. |
| **Homelab** (outbound only) | Polls the feed, lists R2, pulls, verifies, commits, publishes receipts, deletes staging | Its control key; short-lived R2 temp credentials | F5. |

Environments: `local` (pinned wrangler/miniflare; **emulated**), `sandbox` (H1's separate account and throwaway domain), `production`. Use separate accounts rather than wrangler environments in one account, because R2 parent tokens and the REST rate limit are per account (C18).

### F2. D1 vs Durable Objects (capacity unproven; K2 contested)

**Why the choice is about operations and throughput, not correctness.** A3 made the claim an advisory lease. A lost, doubled or rolled-back lease costs bandwidth, not data (SR-01, SR-04, SR-05). C1-S2 (emulated) confirms that both stores' *SQL logic* gives exactly one winner. It says nothing about real latency or overload.

| Criterion | D1, one DB | **D1, two DBs by function (recommended start)** | D1 `rq-dedup` sharded | SQLite DOs, sharded or per family |
|---|---|---|---|---|
| Throughput | One thread for everything (K1) | One thread for dedup, one for the rest | One thread per shard | One thread per object, ~1,000 req/s soft (C30) |
| Failure domain | Overload blocks enrollment, commits and presign together (adversary) | Dedup overload cannot block enrollment or commits | Smaller | Smaller |
| Atomicity | `batch()` is one transaction (C24) | Within one DB only; cross-DB steps use idempotent natural keys | Within one shard | `transactionSync()` per object |
| Migrations, backup, ad-hoc SQL | wrangler migrations, Time Travel, export (C28) | Same, two sets | Same, N sets | Self-written; PITR only from object code |
| Size | 10 GB, fixed (C25) | 10 GB each | 10 GB each | 10 GB per object |

**Why two databases from day one (changed in round 2).** The D1 FAQ says D1 "is designed for horizontal scale out across multiple, smaller (10 GB) databases" (C54). The adversary skeptic notes that one overloaded database is a family-wide failure domain (K1). Splitting later would be a live data migration under exactly the load that made it necessary. The cost is a second migration set and binding. No operation needs atomicity across the two groups:
- presign checks revocation in `rq-control` and writes the lease in `rq-dedup`; the revocation check is advisory at that moment anyway (BUD-REVOKE's 60 s);
- a homelab commit marks dedup in `rq-dedup` and inserts receipts in `rq-control`; both are idempotent on natural keys, so a partial failure is retried.

**Capacity: what is and is not known.**
- **Arithmetic (assumptions, not measurements).** Thread time per file is w × t, where w is the rows written per file **including index rows** (C62) and t the time per row-write. At an aggregate bandwidth B, one database saturates when the mean file size falls to **S_sat = B · w · t**.
  - With B = 62.5 MB/s (25 devices × 20 Mbit/s, all at once; a pessimistic peak), w = 6 (C4; whether C4's w counts index rows is unstated) and t = 5 ms ("several ms", K1; the 5 ms is not sourced), S_sat ≈ 1.9 MB.
  - C4's central mean file size is 4 MB (range 2–8 MB), about 50 % utilisation. A 2 MB mean gives about 94 %.
  - Reads (presence checks, lease checks, feed polls, receipt fetches) and homelab writes (commit marks, receipt-relay inserts and deletes, pruning) come on top. With two databases, part of this load moves off the dedup thread. How much has not been computed, because the per-table write mix is not yet known.
- **Batching does not reduce this.** `batch()` "reduces latency from network round trips". Its statements "execute and commit, sequentially, non-concurrently" (C24), and write time depends on rows written (K1).
- **Design rule:** write SQL is **set-based**, one statement per table per request (`INSERT … SELECT … FROM json_each(?1)`). Whether D1's cost is per statement or per row is what the real C1-S2/S3 kits must measure: `meta.duration` and `meta.rows_written` for N single inserts vs a batch of N vs one set-based insert, at N = 1, 100 and 1,000 (hand-off).
- **Pre-agreed decision rule:** if real-D1 utilisation of `rq-dedup` at C4's central case, with E1's file-size distribution, exceeds about 50 %, shard `rq-dedup` by a dedup-ID character into N D1 databases, or 16 SQLite DOs if N databases prove awkward. Presence checks then fan out to ≤ 16 subrequests (C21). The C1-S3 kit's fail path must follow this ladder, not jump straight to DOs (hand-off).
- **Overload behaviour:** "overloaded" maps to 503 + `Retry-After` with jittered exponential backoff (F8). Homelab commit endpoints keep priority through a C2 brake on device bulk endpoints (Rate Limiting binding or `DeviceGate`).
- **Location hint:** create both databases with a location hint near the family and homelab. It is unmeasured; recorded in the sandbox kit.

**Presence-check cost (indicative, emulated).** Emulated C1-S3 gave `rows_read` = 1,500 per 1,000-ID call with a primary-key SEARCH per ID: about $0.002 per million IDs at published prices. If real D1 planned a scan instead, 1,000 calls × 5M rows would cost about $5 per million IDs and fail the < $1 criterion. The kit records real `meta.rows_read` and `EXPLAIN QUERY PLAN`.

**Size check (estimate).** At 100–200 B per row including the index (assumption), 5M dedup rows are 0.5–1 GB. 2–10 TB at a 2–8 MB mean is roughly 0.25M–5M files. Growing tables need retention rules:
- feed: prune 30 days after the homelab's cursor passes;
- idempotency: 7-day published expiry (C59);
- receipt relay: delete after the device fetches (A3);
- audit log: keep 90 days in D1; the nightly export is the archive (C8).
The cron reports each database's size and alerts at 50 % and 80 % of 10 GB (F9).

**Rejected:** a KV existence cache (eventually consistent); one global DO (same single thread, worse tooling). **Not rejected, to be measured:** a per-family SQLite DO with the logic next to the data. PLAN lists it, and emulated C1-S2 showed lower local DO latency. The real kits add it as a variant (hand-off).

### F3. R2 key layout and buckets (one-way door #7)

| Bucket / prefix | Key | Writer | Reader / deleter | Lifecycle |
|---|---|---|---|---|
| `rq-ingest` `staging/` | `staging/<dedup_id>/<upload_id>/s<n>` | Device via its upload target (presigned or Worker-proxied, F4); Worker creates and completes multipart | Homelab (GET, LIST, DELETE after durable commit) | None besides the default 7-day multipart abort |
| `rq-ingest` `meta/` | `meta/<device_id>/<record_batch_id>.age` | Worker (`put` with create-only `onlyIf`) | Homelab | None |
| `rq-ingest` `pack/` (**reserved**) | `pack/<upload_id>/s<n>` | Device, same rules as `staging/` | Homelab | None |
| `rq-ingest` sentinels | `staging/_sentinel/<yyyy-mm-dd>` | Cron (binding) | Homelab checks presence; deletes after 30 days | None |
| `rq-restore` `restore/` | `restore/<device_id>/<restore_job_id>/<object_id>` | Homelab (temp credential) | Device via presigned GET | Expiration 7 days; abort 1 day |

- **Per-upload keys** avoid last-writer-wins and the 1 write/s per-key limit (C18, K8; SR-07). They are A3's design and depend on **OD-04**, which supersedes ADR-0001 §4's "objects keyed by dedup ID". DR-C1-2 is therefore conditional on OD-04.
- **No dedup ID in `meta/` keys** (SR-26).
- **Reserved `pack/`:** holds many encrypted objects in one staged object if A2/A4 adopt packing (B4 IOS-C16, USB bundle reuse). Whether packs are used is A2/A4's decision before Gate A.
- **Sentinels** cannot collide with dedup IDs, which are `rd1-…` over `[a-z0-9-]` (S55), while the sentinel segment starts with `_`.
- **Two buckets** (DR-C1-2):
  - long-lived tokens scope only to buckets (K7);
  - one mistyped prefix in a shared lifecycle configuration could expire staging;
  - with two buckets, "the ingest bucket has no Expiration rule" is a property of one bucket.
- **Checking that property without a token at home (adversary, minor).** Reading lifecycle configuration needs a Cloudflare API token, which the design keeps away from the homelab. Two checks are proposed:
  - (a) **behavioural, token-free:** the cron writes a dated sentinel each day; the homelab alerts if any sentinel younger than 30 days disappears without the homelab having deleted it;
  - (b) **config:** `wrangler r2 bucket lifecycle list rq-ingest` run on a schedule from the owner's admin machine or CI with a read-only admin token, as a C8 checklist item.
- **7-day abort: a hard ceiling.**
  - The lifecycle page's example comment says a 1-day prefix rule "will take precedence over the one above due to its earlier expiration", which implies the earliest rule wins (K6). H8 (a longer rule overrides) is expected to fail and is kept only as confirmation. **H8b** tests removing or replacing the default rule.
  - Design consequence: any upload that might take more than 7 days uses A3's segment checkpoint (`s1…`), driven by the day-6 cron, as its **primary** mechanism. At 2 Mbit/s continuous, 7 days moves about 151 GB; at a 10 % duty cycle about 15 GB. B6's part and segment sizes must keep any one multipart upload well under that.
  - Lifecycle deletion is "typically" within 24 h, and existing objects "may take longer" (K6). This matters only for the restore bucket's expiry, which can bill past day 7.
- **Bucket locks:** defence in depth only, if C1-S1 H9 shows a lock blocks overwrite without blocking in-progress uploads or the homelab's cleanup.
- **Restore bucket wording:** ADR-0001 §6 and CLAUDE.md say "an expiring R2 prefix". The design uses a prefix in its own expiring bucket. That keeps the intent; DR-C1-2 states the difference so it is not later read as a deviation.

### F4. Upload flow, upload targets, records and cost guard rails

**Upload targets (decided in principle; default kind open).** `POST /v1/uploads` and `POST /v1/uploads/{id}/parts` return, for each part, a **target**: `{method, url, headers, auth}`, where `auth` is `none` (a presigned R2 URL) or `device` (a Worker URL that needs the device's request signature, D3). Clients send exactly what the target says, never construct or pin hosts, and handle both kinds from the first release. Which kind the server issues is a server-side setting, per object class if needed. It can therefore change after Gate B without a client update.

**Why the default kind is open again (logic skeptic, major; C4 conflict).**

| | Presigned direct to R2 | Worker-proxied parts |
|---|---|---|
| Create-only, single PUT | Only if real R2 enforces a signed `If-None-Match: *` (H1, untested) | Binding `put` with `onlyIf` (documented, C16; emulated H12 pass; real untested) |
| Create-only, multipart | **Not possible per part:** re-uploading a part number replaces the part (C9); UploadPart lists no conditions (K5) | Worker records each `(upload_id, part)` in D1 with a conditional insert and refuses a second write of that part (the C1-S2 lease logic) |
| Replay of a leaked target | Bearer URL, reusable until expiry (K3); up to 1 write/s per key (C18); C4's E_eff = 900 writes per URL | Needs the device signature; nonce/replay rules are D3's; a replayed part is refused before the body is read |
| Revocation | ≤ 60 s for new URLs, ≤ 15 min for outstanding ones (BUD-REVOKE) | Checked on every part, so ≤ 60 s |
| iOS background (K15 contested) | URL fixed at hand-off; may expire | Device auth can be checked at send time; one of B4's IOS-C10 options |
| Body limit | Part ≤ 4.995 GiB (C19) | 100 MB on Free/Pro zones (K13); 5–16 MiB parts fit; B6 must cap parts below ~95 MB if proxying stays possible |
| Cost per TB (C65 prices; synthesis arithmetic) | R2 Class A per part, the same in both columns | Plus Workers requests: 1 TB / 16 MiB ≈ 59,605 requests ≈ $0.018. Plus CPU at $0.02 per million CPU-ms: CPU would cost $1/TB only at about 840 ms per part. **CPU per streamed part is unmeasured.** |
| Availability | Worker needed to presign; transfer itself independent | Worker in the data path for each part; runtime updates give 30 s grace (K13), so a long part can be cut and must be retried |
| Worker load | Presign HMAC only | Stream pass-through plus one D1 conditional insert per part (adds to `rq-dedup` load, F2) |

The previous draft rejected proxying because of the 100 MB body cap. That was wrong for 5–16 MiB parts (K13; logic skeptic). The real costs, CPU per streamed part and availability coupling, are not measured.

**Pre-agreed rule for the Gate B default (DR-C1-6):**
1. Run the real C1-S1 kit (H1, H4, H15) and a new **C1-S4 leg** that streams 16 MiB parts through the binding and records Workers Logs `cpuTime`, wall time and errors per part (hand-off).
2. If proxied parts complete reliably and their cpuTime keeps a 10 TB seed within C4's seed allowance under BUD-CLOUD, **Worker-proxied parts become the default for multipart objects.** This is the only way to make multipart staging create-only.
3. For single-PUT objects: presigned with a signed `If-None-Match: *` if real H1 passes; otherwise proxied.
4. If proxying fails the leg, presigned stays the default everywhere, and the owner records the staging-rewrite risk as accepted (DR-C1-6 option A, OD-17).

This replaces the previous draft's unconditional "nothing depends on create-only; accept the risk". C4 §F4.3 states the opposing position: create-only writes are **mandatory**, both because CLAUDE.md settles "never delete or rewrite" and because C4's BUD-ABUSE bound assumes E_eff = 1. C1 now agrees that create-only at staging should be the target. It disagrees only that it can be demanded before the proxy cost is measured.

**Replay cost if staging is not create-only (synthesis arithmetic on C4 inputs).** Each replayed overwrite is one Class A write at $4.50/M (C65). Without Queues, C4's $5.70/M figure drops to $4.50/M. Whether R2 bills 429/412 responses is a C4/C2 `[SB]` item.
- Per URL, at C4's E_eff = 900: about $0.004.
- Per 134-URL window held for 15 minutes: about $0.54.
- Kept up all day by a compromised device that re-signs every 15 minutes: about $52 per day.
This is why the re-sign cap must be **enforced by the Worker**, not only stated as a client rule (F12), and why C2 needs a per-device cap on outstanding URLs.

**Content flow (either target kind):**
1. `POST /v1/uploads` (batch). The Worker records the lease in `rq-dedup`, generates `upload_id` and the key, and returns a single-PUT target, or calls `createMultipartUpload` and returns a first **window** of part targets.
   - Presigned targets live ≤ 15 min (BUD-REVOKE), with `X-Amz-Expires` always explicit (aws4fetch defaults to 24 h, C36).
2. `POST /v1/uploads/{id}/parts` returns the next window: min(remaining parts, ceil(uplink × 900 s / part size)).
3. `POST /v1/uploads/{id}/complete`: the Worker completes via the binding (handling NoSuchUpload), compares the size with the declared size (SR-24), and marks the upload `staged`.
4. **Signed extras** on presigned targets, each **only after the real C1-S1 shows R2 enforces it:** `Content-MD5` (H4), `If-None-Match: *` (H1), Content-Length (H5), `x-amz-checksum-sha256` (H6, and per part H15), CRC64NVME FULL_OBJECT on multipart (proposed **H16**: api.mdx lists CRC64NVME as FULL_OBJECT, K5; it is a non-cryptographic transport check R2 might verify on Complete). Emulated C1-S1 shows aws4fetch signs these into `SignedHeaders`. That is a property of the signer, not of R2.
5. **Conditional Complete: not used.** Under random per-upload keys the key can already exist only after a successful Complete is retried, and R2 may abort the upload on a failed condition (K4, C64). The binding `complete()` takes no condition. The kit still tests conditional Complete via the **S3 API**, checks the binding's type definitions for any conditional option on `createMultipartUpload`/`complete`, and records which, if either, refuses (K4: the 2023-08-11 note names no API surface).
   - **Rejected:** create-only CopyObject to a final key (C56). It doubles write operations without changing the safety basis.
6. **Never presign DELETE; no device credential ever includes `DeleteObject` or `AbortMultipartUpload`** (sources skeptic). A device may cancel its own *open* upload only through the Worker, which aborts it through the binding and refuses once the upload is `staged`. An incomplete upload is not a backup, so this does not touch "never delete backups".

**Records (device → Worker → R2):** `POST /v1/records` carries an opaque record batch.
- The Worker computes the SHA-256 of the body and writes `meta/<device_id>/<batch_id>.age` with `put(…, {onlyIf: {etagDoesNotMatch: "*"}, customMetadata: {sha256}})` (H12 passed emulated, in both forms).
- In the same request it runs one set-based statement group in `rq-control`: feed append and idempotency rows.
- **Retry semantics.** R2 and D1 are not atomic together. If `put` returns null (precondition failed), the Worker `head()`s the key and compares `customMetadata.sha256` with the body's hash. Equal: replay the idempotent D1 statements and return success. Different: return a typed `conflict`. The bytes are hashed, never parsed (opaque-artifact rule). A3's state table should carry this (hand-off).

**Re-sign (F12) and SR-07 (logic skeptic).** SR-07 says staging keys are never presigned for an existing key. For a **single-PUT** upload, `POST /v1/uploads/{id}/urls` first `head()`s the key through the binding. If the object exists, the Worker marks the upload `staged` and refuses the re-sign with `upload_not_open`. Multipart re-signs are for parts of an open UploadId, so no completed key can exist yet. This becomes a G2 test vector.

**Revocation (BUD-REVOKE).**
- A revoked device gets no new targets within 60 s, because the Worker checks `rq-control` on every call. Outstanding presigned URLs die within 15 min by construction; proxied parts are refused at once. **BUD-REVOKE does not depend on any kill switch.**
- **Kill switch (extra, not required).** Rolling or deleting an R2 parent token *may* invalidate outstanding URLs and temp credentials, but no doc covers a roll (K8). A roll stops every presigned upload in the family until the Worker secret is updated (`wrangler secret put`). The C1-S1 kit's decision row that infers roll behaviour from a deletion test must be corrected, and a timed roll added (hand-off).
- **Parent tokens (proposal handed to C2 and D3):**
  - *device-signing*: Object Read & Write on `rq-ingest`;
  - *homelab-minting*: the parent for the homelab's temp credentials on both buckets;
  - *restore-signing* (**new**, logic skeptic): Object Read on `rq-restore` only, used to presign device restore GETs, so rolling it does not stop ingest and vice versa.
  - All three live in the same Worker, so the split gives operability, not containment of a Worker compromise.
  - The adversary skeptic notes that each extra token is another secret for one owner to rotate and monitor. Keep the split only if the canary (F9) and the C8 runbook cover every token. The simpler alternative is one parent token plus the offline break-glass token for draining during a roll. It is recorded for C2/D3.
  - Per-epoch or per-device signing tokens (D1 note), so a kill switch need not cause a family-wide outage, are handed to D3.
- **What a leaked presigned URL can do** while staging is not create-only: rewrite that one staged key until expiry. The homelab rejects mismatching bytes (SR-04), and the device re-uploads. For data, that is availability, not loss. For money, it is the replay cost above.

**Cost guard rails (adversary skeptic, major).** The ingest bucket never expires objects, and R2 bills the mean of daily peak GB-months (C4). At $0.015/GB-month a 2 TB backlog costs about $30/month and 10 TB about $150/month (C4). ADR-0010 adds:
- **Declared-bytes accounting** in `rq-dedup`: declared sizes of uploads in `open` or `staged` and not yet deleted.
- **Observed bytes**, because declared bytes miss abandoned multipart parts (billed until the 7-day abort), over-length bodies (H5 untested) and objects committed but not deleted:
  - the **homelab's** hourly listing reports bytes per prefix plus a `ListMultipartUploads` count;
  - while the homelab is down, a **daily Worker cron** sums object sizes with the binding's `list()`. Cost: one Class A call per 1,000 objects, so about $0.0045 per full listing of 1M objects (C65).
  - The cap and the alerts key on **max(declared, observed)**. Open multipart uploads are counted at their declared size, since part bytes are not listed.
- **"Committed but not deleted after N hours"** alert, for a broken delete path such as a temp-credential scope bug.
- **Refusing new uploads above a cap** tied to BUD-CLOUD (C4: about 1.3 TB at $25), with C4's "home storage full" text. **An interim hard ceiling is asked of the owner now** (DR-C1-7), not left alert-only until Gate B.
- **Pausing or throttling presign** when the signed homelab heartbeat is older than N hours (N with C7), with a plain-language status.
- **Cloudflare billing and usage notifications**, required as a Gate B exit item (C2/C4).

### F5. Homelab authentication and notifications

- **Homelab → Worker:** requests signed with a homelab Ed25519 control key. The Worker holds only the public key (SR-23). D3 owns the request format, and D2 the key inventory.
- **Homelab → R2 (proposal handed to C2 and D3):** `POST /v1/homelab/credentials` returns two temp credentials (one bucket each, K7), TTL ≤ 1 h:
  - **ingest:** `ListObjectsV2`, `GetObject`, `HeadObject`, `DeleteObject`, `ListMultipartUploads`, `AbortMultipartUpload` on `staging/`, `meta/` and `pack/`;
  - **restore:** `PutObject` and the multipart write actions on `restore/`.
  - **K7 restated precisely:** the derivation (HS256 JWT signed with the parent secret; temporary secret = SHA-256 hex of the signed JWT; session token = `base64("jwt/" + jwt)`; `paths.prefixPaths`/`objectPaths`) is specified in prose (S3). The **claim names for bucket, actions and expiry appear only in the example** (S4, reviewed 2026-04-19), and no maximum TTL is stated. H13 must pin the claim names with a test vector (hand-off), and the example page goes on the T2 watch list.
  - **Fallback ladder** (sources skeptic, missed alternative):
    1. locally signed JWT with `actions` and prefixes (preferred);
    2. if that breaks: the **Temporary Credentials API** with the `object-read-write` preset and `prefixes` (C63). It gives prefix scoping without action scoping, which is wider (the homelab could also write staging). It also needs a Cloudflare API token reachable from the Worker;
    3. the offline **break-glass** bucket token.
  - **None of the fallbacks is tested.** H13 cannot be emulated (Miniflare refuses session tokens). A break-glass drain drill must pass before Gate B (C8 runbook; hand-off).
- **Notification path (DR-C1-3), rebalanced (logic skeptic).**
  - **B, the feed:** `GET /v1/homelab/feed?after=<seq>` about every 30 s (about 86k requests a month) plus listing.
  - **D, the push consumer:** R2 event notifications → Queue → a push consumer Worker that appends to the same feed. It needs no token at home and no REST pull, keeps Queues as ADR-0001 §1 names them, and gives a server-side "object staged" signal for single PUTs. It costs a Queues line, and messages can still be dropped after retries (reconciliation covers that).
  - **A, ADR-0001's wording (Queues HTTP pull):** about 10 pulls per 5 min against the 1,200 per 5 min account limit. The lockout risk comes from **sharing** that limit with other REST use, not from polling. 14-day retention plus reconciliation already covers message loss. Its real costs are a Cloudflare API token at home and the shared limit.
  - The gains of B and D over A are **real but modest**. B and D are roughly equal; B is preferred by a small margin, because the Worker already sees every record and every Complete.
  - **Listing cost** (logic skeptic): a full listing is one Class A call per 1,000 objects. During a backlog of 1M staged objects, hourly listing is about 720k Class A calls a month, about $3.24 at list price, and most of the 1M free tier. Proposal for A3/C4: list hourly only while staging holds fewer than about 10k objects; otherwise list at start and daily, and rely on the feed.
- **Workers VPC / Tunnel push: rejected** (K11; R-12). A Tunnel is an outbound connection, so network direction is not the issue. The issue is that the cloud would initiate application requests to homelab services, so a compromised Worker or Cloudflare account could reach the homelab. ADR-0001's pull model exists to prevent that. Beta is a secondary reason.

### F6. Cloud state: what is rebuildable and what needs backup (C8 input)

| Table (D1) | DB | If lost | Backup | Retention |
|---|---|---|---|---|
| `accounts` (name, email, verification) | control | Users re-verify | **Nightly export** | Life of account |
| `invites`, `enroll_tokens`, `pair_codes` (hashed) | control | Printed cards stop working | **Nightly export** | Until expiry + 30 days |
| `devices` | control | Re-enrollment unless a homelab-signed list exists (D3) | Export | Life of device |
| `uploads` (leases, parts, staged-bytes accounting) | dedup | Parallel uploads only | None | Delete 30 days after the terminal state |
| `dedup` | dedup | Re-uploads until the homelab republishes | Rebuild from the homelab | Keep |
| `receipt_relay` | control | Homelab republishes | Rebuild | Delete after the device fetches |
| `feed` | control | Reconciliation covers it | None | 30 days past the homelab cursor |
| `revocations`, `heartbeat`, flags | control | Homelab republishes | None | Latest only |
| `idempotency` | control | Natural keys make it safe | None | 7 days (published, C59) |
| `audit_log` | control | Lost history | **Nightly export** (archive at home) | 90 days in D1 |
| `email_suppression` | control | Re-sending to bad addresses | **Nightly export** | Keep |

- **Export mechanism (adversary, minor):** "A running export will block other database requests" (C60). The nightly backup is therefore a signed, **paginated** `GET /v1/homelab/export` over the cloud-only tables only, with keyset cursors and a bounded page size, run at a quiet hour. `wrangler d1 export` is never run against production while it is in use.
- D1 Time Travel (30 days on Paid, 7 on Free; C61) covers mistakes, not account loss.
- An export-restore drill into the sandbox account belongs in the C8 runbook (hand-off).

### F7. Worker language (DR-C1-1)

| Criterion | TypeScript (Hono) | Rust `workers-rs` | TS + Rust→Wasm for named functions |
|---|---|---|---|
| Platform status | GA | Beta (K9); crate 0.8.7 | TS GA |
| Failure mode | Exception per request | Panic aborts the instance unless nightly `--panic-unwind` (K9) | Panics confined to the module |
| Crypto | Native Ed25519, HMAC, SHA-256, MD5 (C37) | Crates in Wasm | Native where possible |
| Tests | `@cloudflare/vitest-pool-workers` | wrangler dev + external | Both |
| Formats implemented twice | Request auth, code hashing, ID-encoding checks, API schema | None | Fewer |

**Opaque-artifact rule:** the Worker never parses envelopes, records, receipts, manifests, bundles or dedup-ID derivations. It hashes and stores bytes. What remains (request-signature base string, code hashing, ID-encoding checks, OpenAPI schema) is pinned by shared vectors (G2). **Recommendation: A, TypeScript.** Revisit trigger: D3 picks a KDF Web Crypto lacks; then compile that one function to Wasm (option C). The choice also depends on ADR-0003 (client stack, open), but only for which language the second implementation is checked against.

**aws4fetch** (sources skeptic, minor): 1.0.20, last published 2024-08-28 (C36), sits on the presign path, and its 24 h default expiry shows its defaults can be unsafe. Pin it, vendor-review it, and cross-check its presigned URLs in G2 vectors against an independent SigV4 implementation (for example botocore or `@aws-sdk/s3-request-presigner` as a **test-time library only**; no AWS service is involved). A small in-house SigV4 presigner is the fallback if the review fails.

### F8. API v1 conventions (detail in `docs/design/api-v1.md`, Draft)

- **Hosts:** `api.<owner-domain>` (Custom Domain, K12). Presigned content targets use `<ACCOUNT_ID>.r2.cloudflarestorage.com` (K3); proxied ones use the API host. Clients never pin or construct either.
- **Zone choice (adversary, missed alternative):** a Custom Domain needs an active Cloudflare zone (K12). Moving the family's main domain onto the API's account means an account lockout, suspension or billing lapse also takes down that domain's DNS and email. A **dedicated, cheap Reliquary domain** on Cloudflare avoids this, and pairs with DR-C1-4's second bootstrap location on another provider.
- **`workers_dev = false` in `wrangler` config is the source of truth.** A dashboard-only disable is re-enabled by the next deploy. Version, Preview and Deployment URLs stay enabled unless handled separately, for example with Cloudflare Access (S31). This item goes to the C2 hardening checklist.
- **Bootstrap (door #8):** `GET /v1/bootstrap`, offline-signed (key custody is D3/D5's), at two independent locations. It carries no trust material (SR-31).
- **Versioning (C1-S5 rules):**
  1. `/v1/`, additive-only within v1.
  2. Clients decode every server enum with an `unknown` catch-all; otherwise a new enum value must be gated by `min_version`.
  3. Every breaking change raises `min_version` in the same deployment (checklist plus a G2 contract test against the previous client build).
  4. Server request schemas strip unknown keys (zod default).
  5. `Reliquary-Client: <platform>/<semver>` is required.
- **`update_required`:** a problem body with `code: "update_required"` and `min_version`, sent with **HTTP 400**. RFC 9110 requires an `Upgrade` header on 426 (C57), which does not fit an app update. Clients key on `code`, never on status. C1-S5 used 426. The mechanism result stands, and the toy is re-run with 400 when the OpenAPI draft lands (hand-off).
- **Errors:** RFC 9457 problems (C58) with extension members `code` (stable), `retryable`, and `min_version` where relevant. 429 and 503 carry `Retry-After`. D1/DO "overloaded" → 503 retryable. **New: `r2_credentials_unavailable`** (503, retryable) while presign is paused by a failed canary (F9). Clients use jittered exponential backoff with a cap.
- **Idempotency:** natural keys first; `Idempotency-Key` on redeem, pair and restore-job creation, following the draft (C59), with a published 7-day expiry. The draft's publication status is unconfirmed (S49).
- **Batching:** `check` ≤ 1,000 IDs; `uploads` ≤ 100; `records`; `commits`. Typed per-item results; set-based SQL (F2).
- **Server time:** `Reliquary-Server-Time` header.

### F9. Background jobs and detection

| Job | Mechanism | Notes |
|---|---|---|
| Lease expiry | Lazy (`lease_expires_at > now`) | No sweeper |
| Stale device, nudges | Cron, ~15 min, UTC | Idempotent "what is due"; `nudge_sent_at` |
| Dead-man's switch | Cron on the signed heartbeat | C7 adds an external check |
| **Parent-token canaries** (new) | Cron, every run | For each parent token: presign a PUT to `canary/<token>` in its bucket, `fetch` it, then presign and `fetch` a HEAD. The binding removes the object. On failure: set `presign_paused`, answer `503 r2_credentials_unavailable`, alert the owner out of band (C3/C7). Clear on recovery. The Worker never hands out a DELETE URL, and the canary needs none |
| **Staging sentinels** (new) | Cron, daily | Writes `staging/_sentinel/<date>` via the binding (F3); the homelab checks them |
| **Observed staged bytes** (new) | Cron, daily | Binding `list()` over `rq-ingest` while the homelab is silent (F4) |
| Presign pause on a stale heartbeat | Cron sets a flag; the Worker checks it | F4 |
| Day-6 multipart checkpoint | Cron | **Primary** path for long uploads (F3) |
| D1 size alerts and table pruning | Cron | 50 % / 80 % of 10 GB, per database; F6 retention |
| **Plan and quota errors** (new) | Worker and cron | Alert on CPU-limit-exceeded, D1 quota errors, and Cron failures (signs of a plan lapse, F10) |
| Per-device counters | DO alarm in `rq-gate` | At-least-once; idempotent |
| Long sequences | Workflows (not v1) | — |

The homelab ignores `canary/` and `staging/_sentinel/` when reconciling.

### F10. Change management, plan dependencies and beta policy

- **No gradual deployments in v1.** A single-owner system gains little from canarying. Gradual deployments route each request independently (K10), which creates a two-version window for every multi-request upload flow. If they are adopted later, use version affinity (C55) and keep DO classes out of that Worker.
- **Expand → deploy → contract D1 migrations are still required,** because `migrations apply` and the code deploy are not atomic. Take a Time Travel bookmark before each apply (C28). With two databases, each has its own migration set.
- **DO classes live in `rq-gate`**, a separate Worker bound by `script_name`, because `exports` makes `versions upload` fail fast and "Gradual deployments are not supported with `exports`" (K10). One call style per DO (#6561).
- **Pinned** compatibility date, bumped in sandbox first (C41). Emulator versions pinned too (miniflare `latest` is an alpha; C47).
- **Workers Paid dependencies (adversary, major; new).** The design silently needs Workers Paid. A lapsed card or downgrade would break:
  - CPU above Free's 10 ms per request (emulated C1-S4 presign timings exceed it; indicative only);
  - D1 queries per invocation: Free 50 vs Paid 1,000 (C61). A 100-item upload batch with set-based SQL fits 50, but cron jobs may not;
  - D1 Time Travel: Free 7 days vs Paid 30 (C61), which shortens the recovery window;
  - D1 rows-written volume during a seed (C4: 50M included on Paid).
  Detection: plan and quota error alerts (F9); a C2 check of billing state with a card-expiry reminder 30 days ahead.
- **Beta policy (OD-14 input, DR-C1-5):**

  | Feature | Status | Used? | Fallback |
  |---|---|---|---|
  | Rust Workers | Beta | No | — |
  | Workers VPC | Beta | No (rejected) | — |
  | D1 read replication | Beta | No | — |
  | Gradual deployments | GA | No (by choice) | — |
  | Temp-credential action scoping (local JWT) | Documented; API support "coming soon" | Yes (homelab, server-side) | API preset scope (C63), then offline break-glass. **Documented; test pending** (H13 plus a drill) |
  | Email Service | Beta | C3's call | C3 |

### F11. Load-bearing limits list (verified 2026-10-06/07 unless noted)

| Limit | Value | Claim | Bites where |
|---|---|---|---|
| Presigned URL expiry | 1 s – 7 days | K3 | BUD-REVOKE |
| Presign host | S3 domain only | K3 | Hostname pinning |
| Same-key write rate | 1/s, then 429 | C18 | Key layout; replay cost |
| Parts | 5 MiB – 4.995 GiB, ≤ 10,000, equal except last; re-upload replaces | C9, C19 | B6 part policy; create-only |
| Default multipart abort | 7 days; extension probably impossible | K6 | Segment checkpoint (F3) |
| Lifecycle deletion lag | typically ≤ 24 h, may be longer | K6 | Restore bucket |
| R2 REST API | 1,200 req / 5 min per account | C18 | Kept off the hot path |
| Token permission propagation | up to 1 min; roll semantics undocumented | K8 | Kill switch (H11) |
| Temp credential | one bucket; max TTL undocumented; actions by local signing only | K7, C63 | Homelab credentials |
| Workers CPU | 30 s default, 5 min max (Paid); 10 ms Free | C21, K13 | Presign windows; proxied parts |
| Request body | 100 MB Free/Pro zone | K13 | Records and proxied parts |
| D1 per DB | 10 GB (fixed), single thread, 100 params, 1,000 queries/invocation (Paid; 50 Free) | K1, C25, C61 | F2, F6 |
| D1 export | Blocks other requests while running | C60 | F6 |
| D1 rows written | Index entries count as extra rows | C62 | F2, C4 |
| DO per object | ~1,000 req/s soft, 10 GB | C30 | Fallback |
| Cron CPU | 30 s (< 1 h interval) | C23 | Jobs |
| Time Travel / PITR | 30 days Paid, 7 Free | C28, C61 | C8 |

### F12. Short URLs vs OS background queues (re-scoped; K15 contested)

| Option | Revocation | Works on | Verdict |
|---|---|---|---|
| A. Re-sign just in time (app code runs before the transfer) | ≤ 15 min kept | Desktop daemon, Android WorkManager | **Default for v1 platforms** with presigned targets |
| B. Re-sign after the *specific* expired-URL error | ≤ 15 min kept | All, as a safety net | Always on, with a **Worker-enforced** cap |
| C. Longer URLs for one platform | Weakened | iOS | DR-B4-2 (owner) |
| D. Worker-proxied parts | Checked at send (≤ 60 s) | All | Possible default (F4 rule); also an iOS option |
| E. Foreground-created non-discretionary tasks; `earliestBeginDate` + `willBeginDelayedRequest` (B4 P6) | ≤ 15 min kept | iOS | Candidates for B4-S2 evidence |

- **For iOS, A does not apply and B can loop.** The URL is fixed at hand-off, each re-enqueue from the background is discretionary again, and a failed attempt may upload a whole part before R2 answers. "15-minute URLs suffice" is claimed **for desktop and Android only**.
- **Client rules:**
  - Re-sign only on the expired-URL error code that real C1-S1 H10 records; never on every 403. Any other 403 is reported as a health problem, not retried.
  - At most 3 re-signs per part per hour (proposed; B6 tunes it), with jittered backoff. **The Worker enforces the same cap** (F4 replay cost).
  - Repeated failures are reported to the owner.
  - The C1-S1 kit should check whether R2 honours `Expect: 100-continue`, so an expired URL is refused before the body is sent (hand-off).
- `POST /v1/uploads/{id}/urls` returns fresh targets for the **same keys and UploadId**. It is idempotent, refused for revoked devices and closed uploads, and HEAD-checks single-PUT keys first (F4, SR-07).

### Skeptic issues and how they were handled

**Round 2 (2026-10-07).** Several round-2 issues concern the analyst's JSON payload, which had drifted from the round-1 synthesis. They are handled here, and this note is the source of truth for ADR-0010 and the decision queue.

| Issue (severity, lens) | Handling |
|---|---|
| Analysis JSON stale against the note (major; sources, adversary) | **Fixed.** This note and ADR-0010 are the source of truth; the returned recommendation and DR-C1-1..7 are regenerated from them. Q2, Q5, Q12 and Q15 carry the corrected answers, and DR-C1-6/7 are included. |
| Capacity argument relies on batching (major; sources, logic) | **Fixed** (round 1, kept). K2 contested and not used; S_sat formula; w must include index rows (C62); set-based SQL; per-statement vs per-row timing in the kits; homelab read load named. **Changed:** two D1 databases from day one; the C1-S3 kit's fail path to follow the ladder (hand-off). |
| Append-only residual missing; C4's "create-only is mandatory" not engaged (major; sources, logic, adversary) | **Fixed.** F4 states C4's position and the replay cost. The 100 MB argument against proxying is withdrawn. ADR-0010 decides upload targets, so the default can change without a client update. DR-C1-6 is rewritten with a pre-agreed rule and routed through OD-04/OD-17 with C4 and C2. "Never presign DELETE" rule added. |
| Worker-proxied uploads dismissed with an invalid 100 MB argument (major; logic) | **Fixed.** F4 compares the options on create-only, replay, revocation, iOS, cost and availability. A C1-S4 proxied-part leg is handed off. The comparison remains unmeasured on CPU, so no default is claimed. |
| Kill switch: BUD-REVOKE misattributed; roll inferred from a deletion test (major; logic) | **Fixed** in this note (BUD-REVOKE needs no kill switch). The C1-S1 kit's decision row still says otherwise, so a correction plus a timed roll are handed to the spike runner. Per-epoch or per-device tokens handed to D3. |
| Decisions owned by other workstreams written as ADR-0010 decisions (major; logic) | **Fixed.** Tokens, temp-credential scopes, the control key, request auth and bootstrap signing are labelled "proposal handed to C2/D3/D2/D5" in the note and ADR-0010. |
| No canary for a broken or rolled token; 403 retry storm (major; adversary) | **Fixed.** Cron canaries, the presign-paused flag, `r2_credentials_unavailable`, error-specific re-sign, other 403s reported as health problems (F9, F12). The roll runbook goes to C8. |
| Denial of wallet: cap alert-only, declared bytes only (major; adversary) | **Fixed.** max(declared, observed) accounting, a daily Worker `list()`, homelab-observed bytes, a "committed but not deleted" alert, an interim hard ceiling asked now (DR-C1-7), billing notifications as a Gate B exit item. |
| Lapsed payment / plan downgrade unnamed (major; adversary) | **Fixed.** Paid-plan dependency list (F10) with primary sources (C61); plan and quota error alerts (F9); card-expiry check to C2. |
| C1-S5 used 426 without `Upgrade` (minor; sources) | **Partly fixed.** The spec uses 400; the C1-S5 rerun with 400 is handed to the spike runner. |
| K10 per-request split cited to the wrong page (minor; sources) | **Fixed.** S27 now names `gradual-deployments/index.mdx`. |
| K12 omits Deployment URLs; config as source of truth (minor; sources, logic) | **Fixed** (F8; C2 checklist). |
| Temp-credential JWT better specified than claimed (minor; sources, logic) | **Fixed.** K7 restated in F5; claim-name vector for H13 and T2 watch handed off. |
| 2023-08-11 note names no API (minor; sources) | **Fixed.** The kit tests the S3 API and checks the binding's conditional options (F4 step 5; hand-off). |
| aws4fetch recency (minor; sources) | **Fixed.** Pin, vendor-review, cross-check vectors; in-house presigner as fallback (F7). |
| VPC rejection rationale (minor; sources) | **Fixed.** Trust-direction wording (Q9, F5). |
| 7-day abort as a ceiling (minor; sources) | **Fixed** (round 1, kept). |
| Re-sign can violate SR-07 for single PUT (minor; logic) | **Fixed.** HEAD before re-sign (F4, F12). |
| Restore GET signer unspecified (minor; logic) | **Fixed.** A restore-signing token is proposed (F4), handed to C2/D3. |
| Case for amending ADR-0001 §1 overstated; LIST cost uncosted (minor; logic) | **Fixed.** DR-C1-3 rebalanced (B and D roughly equal); listing cost computed; adaptive cadence proposed to A3/C4. |
| Key layout presupposes OD-04 (minor; logic) | **Fixed.** DR-C1-2 is conditional on OD-04 and names ADR-0001 §4. |
| Kits lack the hand-off items (minor; logic) | **Fixed** by relabelling: "kit-ready (pending additions)". The synthesizer does not edit kits. |
| Smaller slips: JWT wording, Miniflare on Complete, C1-S4 Free inference, C1-S2 "pass", per-family DO (minor; logic) | **Fixed.** Wording corrected; C1-S2 "pass (emulated, logic only)"; per-family DO variant added to the kit hand-offs. |
| Nightly export blocks D1 (minor; adversary) | **Fixed.** Paginated signed endpoint; never `wrangler d1 export` on production (F6, C60). |
| "No Expiration rule" check needs a token (minor; adversary) | **Fixed.** Sentinel check (token-free) plus an admin-machine config check (F3). |
| Rows written omit index rows (minor; adversary) | **Fixed.** w defined to include index rows (C62); hand-off to C4 and the kits. |
| Two parent tokens double rotation work (minor; adversary) | **Fixed.** Purpose stated; the simpler one-token alternative recorded for C2/D3 and in DR-C1-5. |
| Missed alternatives | Adopted: two D1 databases from day one; Worker-proxied parts as a candidate default; canaries; sentinels; observed bytes; dedicated domain (DR-C1-4); temp-credential API fallback; restore-signing token. Handed off: CRC64NVME (H16); Rate Limiting binding as the first quota layer (C2); per-device/epoch tokens (D3); per-family DO variant (kits). Noted: version affinity (F10); Queue push consumer (DR-C1-3 D); desktop temp credentials (Q17). |
| Conflicts with settled text | See §Conflicts with settled text. |

**Round 1 (2026-10-06)**, summary. All issues were fixed or handed off:
- batching and capacity (K2 withdrawn);
- write-path arithmetic recomputed with w = 6;
- `exports` vs gradual deployments (DOs moved to `rq-gate`);
- `pack/` reserved;
- K15 re-scoped;
- staging cost backstop;
- kill switch not required for BUD-REVOKE;
- 7-day abort ceiling;
- H15 proposed;
- presence-check scan cost and D1 retention;
- RFC sources re-read (400 `update_required`);
- binding conditional-complete relabelled;
- C1-S4 CPU caveats;
- C1-S2 relabelled;
- records hash-compare retry;
- conditional Complete argued from the right risk;
- DR-C1-5 "test pending";
- "403 means re-sign" capped.
The full table is in the git history of this file.

### Alternatives compared

| Option | Fit with settled requirements | Pros | Cons | Evidence |
|---|---|---|---|---|
| **Two D1 DBs by function + set-based writes (recommended, provisional)** | Fits ADR-0001 ("D1 / Durable Objects") | Tooling, Time Travel, export; failure isolation | Two migration sets; capacity unmeasured | K1, C24, C54; K2 contested |
| One D1 | Fits | Simplest | One failure domain; migration under load later | K1 |
| Sharded SQLite DOs, or one per family | Fits | Horizontal; logic next to data | Custom migrations and PITR | C28, C30 |
| KV existence cache | Fits | Cheap reads | Eventually consistent | PLAN |
| **Feed polling + listing (preferred by a small margin)** | Amends the ADR-0001 §1 mechanism | No CF token at home, no REST limit | Seconds of latency | F5 |
| Queue push consumer → feed (option D, roughly equal) | Closer to ADR-0001 wording | Server-side staged signal | Queues cost; dropped messages | F5 |
| Queues pulled over HTTP | Fits ADR-0001 wording | Push-ish | Token at home; shared REST limit | A3, F5 |
| Workers VPC push | **Breaks** the outbound-only intent (cloud-initiated requests) | Instant | Cloud reaches homelab services; Beta | K11 |
| **Server-chosen upload targets (decided)** | Fits | Default can change without a client update | Clients implement two target kinds | F4 |
| Presigned per-part URLs, ≤ 15 min | Fits only with DR-C1-6 A (append-only enforced at commit) unless H1 passes; multipart never create-only | Plain HTTP; Worker off the data path | Bearer replay; replay cost | K3, C9, F4 |
| Worker-proxied parts | Fits the literal append-only reading | Create-only per part; revocation at send; iOS option | Worker in the data path; CPU unmeasured | K13, C16, F4 |
| **Homelab temp credentials (proposal)** | Fits | No long-lived secret at home | Depends on the Worker; unspecified claim names | K7, C63 |
| Homelab long-lived token | Fits | Independent of the Worker | No prefix or delete scoping | K7 |
| **TypeScript Worker (recommended)** | Fits | GA, native crypto | Small formats twice | K9 |
| Rust `workers-rs` | Fits | One implementation | Beta, pre-1.0, nightly | K9 |
| **No gradual deployments; DOs in a separate Worker (recommended)** | Fits | One version at a time | No canary | K10 |

### Similar work and lessons

| Project | What they do | Borrow or avoid | Source |
|---|---|---|---|
| Ente museum | Random per-upload keys; ≤ 50 URLs per call; presigned Complete; temp-object table with sweeper | **Borrow** per-upload keys and the temp-object table | S44 |
| Immich bulk upload check | Per-item ACCEPT/REJECT with reason | **Borrow** typed per-item results | S44 |
| restic rest-server | Append-only, 403 on existing blob | **Borrow** create-only; equal-content retry = success (records, proxied parts) | S44 |
| Headscale pre-auth keys | Prefix + hash, expiry | **Borrow** for invites and codes | S44 |
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
| aws4fetch | SigV4 presign (pin, vendor-review, cross-check) | MIT | 1.0.20 (2024-08-28) | C36 |
| jose | JWT for temp credentials | not checked | not checked | S4 |
| @cloudflare/vitest-pool-workers | Tests in workerd | MIT | 0.22.0 | C47 |

## Spikes

No sandbox account exists (H5 L01). Every Cloudflare result below is **emulated, not real R2/Cloudflare**, and cannot settle a hypothesis about Cloudflare. Each SB spike has a real-sandbox kit. The kits do not yet contain the additions proposed below, so they are **kit-ready (pending additions)**.

| Spike | Hypothesis | Pass → / fail → (decision) | Exec tag | Budget IDs | Data class | Status | Result |
|---|---|---|---|---|---|---|---|
| C1-S1 | H1–H14 (kit), plus proposed H8b, H15, H16 | H1 pass → presigned single PUT may be create-only (F4 rule step 3); fail → proxied single PUT or DR-C1-6 A. H8 fail (expected) → segment checkpoint primary. H11 → roll semantics only (BUD-REVOKE does not depend on it). H13 fail → API-preset fallback, then a long-lived homelab token | SB (kit); emulated subset run as CT | BUD-REVOKE | `SYN → results` | **Emulated; inconclusive; kit-ready (pending additions)** | Miniflare 5.20260926.0-alpha, 3 runs on 2026-10-06, same verdicts. The signer works: aws4fetch signs `if-none-match`, `content-md5`, `content-length` and `x-amz-checksum-sha256`. Presigned PUT + `If-None-Match: *`: 200 then 412, original kept; header dropped 403 (H1, emulated). Binding `onlyIf` wildcard refused the existing key in both forms (H12). Binding sha256 mismatch threw; nothing stored. Binding `complete()` overwrote: it has no conditional form (documented; not an H2 result). Presigned POST Create/Complete accepted (H3, Miniflare only). Tampered part with signed MD5 → 400; MD5 header dropped → reset or 500. Content-Length shorter 403, longer 500. Signed SHA-256 ignored; tampered body stored (H6 fail in Miniflare). Object ETag formula holds; part ETags not MD5. Expiry checked at arrival (H10). H8, H9, H11, H13, H14 not emulable. Evidence: [`spikes/C1-S1/README.md`](../../spikes/C1-S1/README.md), `results/miniflare.json`, `results/miniflare-run1-2026-10-06T1658Z.json`; kit [`kits/C1-S1/`](kits/C1-S1/README.md) |
| C1-S2 | 50 concurrent leases × 10,000 trials (1,000 takeover races): exactly one winner; D1 single-batch conditional INSERT vs 16 DO shards with `transactionSync` | Pass → the lease SQL is correct in both stores; store choice by real latency. Fail → fix the lease SQL | CT (emulated) / SB (kit) | — | `SYN → results` | **Pass (emulated, logic only); real D1/DO pending; kit-ready (pending additions)** | D1: winners {1: 10000}, 0 bad trials, 0 duplicate live leases, 0 errors over 500,000 requests; local p50 155.7 / p99 372.9 / max 788.5 ms. DO: {1: 10000}, 0 bad, 0 duplicates; p50 46.7 / p99 213.3 / max 452.6 ms. Container load average 4–6. The latencies say nothing about Cloudflare. One extra D1 row comes from a documented manual probe. Evidence: [`spikes/C1-S2/README.md`](../../spikes/C1-S2/README.md), `results/miniflare-d1.json`, `results/miniflare-do.json`; kit [`kits/C1-S2/`](kits/C1-S2/README.md) |
| C1-S3 | 1,000-ID presence check (half present) on a 5M-row index via one `json_each` statement: p99 < 500 ms and < $1 per million IDs | Pass → D1 for dedup; fail → shard `rq-dedup` (F2 ladder) | SB (kit); emulated run as CT | BUD-CLOUD | `SYN → results` | **Emulated; inconclusive; kit-ready (pending additions)** | Local SQLite, 5,000,000-row WITHOUT ROWID table, 200 calls per shape (2026-10-06T20:16Z). `json_each`: 200/200 correct; client p50 13.5 / p99 26.0 / max 31.2 ms; `meta.duration` p50 5.0 / p99 10.0 ms; `rows_read` 1,500/call; PK SEARCH per ID. `in100`: 200/200; p50 16.0 / p99 28.5 ms. About $0.002 per million IDs **from emulated `rows_read`** (indicative pass on cost). The latency criterion has no result. Evidence: [`spikes/C1-S3/README.md`](../../spikes/C1-S3/README.md), `results/miniflare-5M.json`; kit [`kits/C1-S3/`](kits/C1-S3/README.md) |
| C1-S4 | Presign 200 UploadPart URLs in one request within Paid CPU; URLs work from curl; Ed25519 verify < 1 ms CPU | Pass → windowed presign as designed; fail → smaller windows. **Proposed proxied-part leg:** pass → proxied parts eligible as default (F4 rule) | SB (kit); emulated run as CT | BUD-CPU-REQ, BUD-CLOUD (proxied leg) | `SYN → results` | **Emulated; inconclusive; kit-ready (pending additions)** | Local workerd + Node micro-benchmark, shared Xeon container (2026-10-06). 200 unique URLs per call (longest 515 chars; 103,742-byte response); in-Worker local time p50 22.0 / p99 183.9 ms (n = 50); Node CPU p50 38.8 / max 77.3 ms (n = 30). curl PUT to parts 1, 2, 200 → 200; completed object 10,486,537 B. Ed25519 verify 0.055–0.079 ms (local workerd), 0.159–0.203 ms CPU (Node). **Not Cloudflare CPU accounting.** Only the kit's Workers Logs `cpuTime` counts. Evidence: [`spikes/C1-S4/README.md`](../../spikes/C1-S4/README.md), `results/miniflare.json`, `results/cpu-bench-node.json`; kit [`kits/C1-S4/`](kits/C1-S4/README.md) |
| C1-S5 | Additive v2 change invisible to an old client; breaking change → machine-readable `update_required` | Pass → F8 rules; fail → stricter versioning | CT (ran for real; contract test, no Cloudflare) | — | `SYN → results` | **Pass, with two conditions** (rerun with status 400 pending) | Hono/zod toy under local `wrangler dev`, Rust v1.2.0 client; byte-identical rerun at 2026-10-06T20:20Z. Added fields: OK. New enum value: DECODE_ERROR on HTTP 200 (closed enum), OK (tolerant). Ungated rename: DECODE_ERROR on 200 for both. Gated break: `update_required`, `min_version` 2.0.0 (sent as 426; the spec now uses 400, F8). `.strict()` request schema rejects a newer client's extra field (400); zod's default strips it. Conditions: tolerant enums or gated additions; `min_version` raised with every breaking change. Evidence: [`spikes/C1-S5/README.md`](../../spikes/C1-S5/README.md), `results/client-matrix.jsonl`, `results/client-matrix-rerun-2026-10-06T2020Z.jsonl`, `results/server-side.txt` |

**Proposed kit additions (for the spike runner; the synthesizer does not edit kits):**
- **C1-S1:**
  - **H8b:** list and try to remove or replace the default abort rule.
  - **H15:** presigned UploadPart with signed `x-amz-checksum-sha256` and a tampered body; COMPOSITE completion.
  - **H16:** CRC64NVME FULL_OBJECT checksum on a multipart upload with a tampered part.
  - **H2** via the S3 API, and an inspection of the binding's types for any conditional option on `createMultipartUpload`/`complete`.
  - **H10:** record the exact expired-URL error, and whether `Expect: 100-continue` is honoured.
  - **H11:** a timed *roll* of the device-signing token, including the Worker secret update and the family-wide outage it causes. Correct the decision row that infers "usable kill switch for BUD-REVOKE" from a deletion test.
  - **H13:** pin the JWT claim names with a test vector; also test the Temporary Credentials API preset-scope fallback.
  - A break-glass drain drill with the offline token.
  - Whether R2 bills 412/429 on replayed writes (shared with C2/C4).
  - Fix the T35 → T54 lifecycle reference in `spikes/C1-S1/README.md`.
- **C1-S2/S3:** per-statement vs per-row `meta.duration` and `meta.rows_written` for single, batch-of-N and set-based inserts (N = 1, 100, 1,000); real `rows_read` and `EXPLAIN QUERY PLAN`; a D1 location hint; a **per-family DO** variant; the C1-S3 fail path aligned with the F2 ladder (shard `rq-dedup`).
- **C1-S4:** `cpuTime` from Workers Logs as the only accepted measurement; a **proxied-part leg** (16 MiB parts streamed through the binding: `cpuTime`, wall time, errors, plus a runtime-update cut test if feasible).
- **C1-S5:** rerun with HTTP 400 for `update_required`.

## Conflicts with settled text

- **CLAUDE.md "devices can only append backups, never delete or rewrite them".** Committed history is never at risk. But a presigned PUT or UploadPart URL is a reusable bearer token. Until real H1 passes, it lets its holder **rewrite a not-yet-committed staged object** within the URL window. For multipart parts this holds even if H1 passes, because a re-uploaded part number replaces the part (C9). C4 §F4.3 reads the settled rule as requiring create-only writes at staging. Resolution: ADR-0010 makes the target kind switchable and sets a Gate B rule (F4). The owner chooses between "append-only enforced at commit" (accepted risk) and "create-only at staging" (proxied parts) in **DR-C1-6**, via OD-04/OD-17. It is not assumed.
- **ADR-0001 §1** names Queues as the notification path. DR-C1-3 options B and D both need an "Amends: ADR-0001 §1" note if chosen. ADR-0010 does **not** adopt the feed as settled.
- **ADR-0001 §4** ("objects are keyed by dedup ID", exclusive claim): per-upload keys and advisory leases supersede it in substance. That is **OD-04**, and DR-C1-2 (door #7) is conditional on it.
- **ADR-0001 §6 / CLAUDE.md "expiring R2 prefix"** for restores: kept as a prefix in its own expiring bucket. The wording difference is stated in DR-C1-2.
- **Ownership (PLAN §2.1):** homelab token scoping and rotation belong to C2; revocation, the kill switch and request auth to D3 (ADR-0014); the key inventory to D2; the bootstrap config key to D3/D5. ADR-0010 labels the parent-token split, the temp-credential scopes, the control key and the config key as **proposals handed over**.

## Open questions

| # | Question | Who | By when |
|---|---|---|---|
| 1 | C1-S1 H1–H16 and H8b on real R2 | Spike runner, sandbox (L01) | Gate B |
| 2 | Real D1 cost per statement vs per row (index rows included); utilisation at E1's file-size mix; real `rows_read` and query plan; per-family DO variant | C1-S2/S3 kits; E1; A0 | Gate B |
| 3 | CPU and reliability of Worker-proxied 16 MiB parts (decides the default target kind) | C1-S4 kit (proxied leg) | Gate B |
| 4 | Roll semantics of R2 parent tokens; family-wide outage during a roll; break-glass drill; one vs three parent tokens | C1-S1 H11, C8, D3, C2 | Gate B |
| 5 | Stability of the local-signing JWT format and claim names; max temp-credential TTL; action scoping in the API | T2 watch list; H13 | Gate B |
| 6 | Does R2 bill 412/429/403 on replayed or refused writes? | C2/C4 `[SB]`, C1-S1 | Gate B |
| 7 | Does any platform need URLs longer than 15 min? iOS options (F12 C–E) | B4-S2, DR-B4-2, D3 | Wave 2 |
| 8 | Request-auth construction and replay rules (also for proxied parts); any KDF Web Crypto lacks; BUD-CPU-REQ on real CPU | D3 (ADR-0014), C1-S4 kit | Gate C |
| 9 | Second bootstrap location; dedicated domain vs main zone; config-key custody; whether bootstrap signing reuses the update root | Owner (DR-C1-4), D3, D5 | Gate C |
| 10 | Packed uploads (IOS-C16): used or not | A2/A4 | Gate A |
| 11 | Staging cap value, interim ceiling and refusal policy | Owner (DR-C1-7, OD-20, BUD-CLOUD), C2, C4 | Interim: Wave 1 exit; final: Wave 2 |
| 12 | Idempotency-Key draft publication status (only the `-latest` editor's copy read) | H1 / T2 | Before ADR-0010 is accepted |
| 13 | Queues pull REST rate limits beyond the account REST limit (not documented on the pages read) | Only if DR-C1-3 picks A | — |
| 14 | Whether bucket locks block the default abort or in-progress uploads | C1-S1 H9 | Gate B |
| 15 | Exact per-device counters: DO vs D1 vs Rate Limiting binding (first layer) | C2 | Wave 2 |
| 16 | Adaptive listing cadence during backlogs | A3, C4 | Wave 2 |

## Recommendation

Adopt for the ADR-0010 draft (Proposed):

- **Topology:**
  - TypeScript `rq-api` Worker on `api.<owner-domain>`, ideally a dedicated Reliquary domain (DR-C1-4), with `workers_dev = false` in config and Preview, Version and Deployment URLs handled.
  - **Two D1 databases from day one** (`rq-dedup`, `rq-control`), provisionally, behind a data-access layer, with set-based writes. Shard `rq-dedup` if real-D1 kits show > ~50 % utilisation.
  - DO counters, if C2 wants them, in a separate `rq-gate` Worker.
  - Two R2 buckets with `pack/` reserved (conditional on OD-04).
  - One Cron Trigger, including parent-token canaries, staging sentinels and observed-bytes checks.
- **Uploads:**
  - **Server-chosen upload targets** (presigned R2 URL or Worker-proxied part), which every client supports from the first release.
  - The Gate B default kind follows the F4 rule (DR-C1-6). C1 leans to proxied parts for multipart objects and to presigned single PUT only if real H1 passes. **This lean rests on unmeasured CPU and is not a decision.**
  - Presigned targets: ≤ 15 min with explicit `X-Amz-Expires`.
  - Create and Complete in the Worker; no condition on Complete; never presign DELETE.
  - Re-sign with a Worker-enforced cap and a HEAD check for single-PUT keys (desktop and Android; iOS open).
  - Records through the Worker with create-only `onlyIf` and hash-compare retries.
- **Guard rails:** staged-bytes cap on max(declared, observed) with an interim hard ceiling (DR-C1-7); presign pause on a stale heartbeat or a failed canary; D1 retention and size alerts; a Paid-plan dependency list with plan and quota alerts; a paginated export.
- **Homelab:** feed polling plus listing, or option D, pending DR-C1-3. The Ed25519 control key, temp credentials with their fallback ladder, and the parent-token split (device-signing, homelab-minting, restore-signing) are **proposals for C2/D3**.
- **Opaque-artifact rule;** aws4fetch pinned and cross-checked; F8 API conventions including the C1-S5 rules and 400 `update_required`.
- **Change management:** no gradual deployments; expand/contract per database; pinned compatibility date; separate accounts.
- **Safety basis:** per-upload keys plus homelab verification for integrity. R2 conditionals only after the real kit passes. Miniflare results are never evidence about R2.

**What would change this:**
- Real-D1 utilisation above ~50 % → shard `rq-dedup`.
- The proxied-part leg fails or is costly → presigned default everywhere, and the owner accepts the staging-rewrite risk (DR-C1-6 A).
- Real H1 passes → presigned single PUT with `If-None-Match: *`.
- H13 fails → API preset fallback, then a long-lived homelab token.
- H8b shows the default abort can be removed → simpler long uploads.
- The owner picks DR-C1-3 A or D → Queues in v1.
- D3 needs a KDF Web Crypto lacks → one Wasm module.

## Decision requests

### DR-C1-1: Worker language: TypeScript with the opaque-artifact rule (H1 to number)
- **Needed by:** Wave 1 exit
- **Evidence:** F7; K9 (verified)
- **Options:** A. TypeScript (Hono), small formats implemented twice with shared vectors. B. Rust `workers-rs` (Beta, pre-1.0, nightly for unwind). C. TS shell + Rust→Wasm for named functions.
- **Recommendation:** A, keeping C for any function Web Crypto cannot do.
- **Touches settled text:** none.
- **If no decision by the deadline:** the A0 skeleton uses A.

### DR-C1-2: Two R2 buckets, ingest never expires, `pack/` reserved (one-way door #7; conditional on OD-04)
- **Needed by:** Gate B
- **Evidence:** F3; K6, K7 (verified)
- **Options:** A. One bucket with prefix lifecycle rules. B. `rq-ingest` (no Expiration ever; `staging/`, `meta/`, reserved `pack/`, sentinels) + `rq-restore` (expiring).
- **Recommendation:** B. "Staging never expires by age" becomes a property of one bucket, guarded by sentinels, and tokens can separate restore from ingest.
- **Touches settled text:** the per-upload key form presupposes **OD-04** (superseding ADR-0001 §4's dedup-ID keys). Restores use "an expiring prefix" (ADR-0001 §6, CLAUDE.md) in its own bucket, which keeps the intent.
- **If no decision by the deadline:** the skeleton uses B.

### DR-C1-3: v1 notification path (amends the mechanism named in ADR-0001 §1)
- **Needed by:** Wave 1 exit (OD-04 sitting), before A0 fixes the homelab puller
- **Evidence:** F5; A3 C3–C7
- **Options:** A. R2 notifications → Queues → HTTP pull (ADR-0001 wording). B. Worker feed polled about every 30 s, plus listing. C. DO WebSocket push. D. R2 notifications → Queue → push consumer Worker → the same feed.
- **Recommendation:** B or D. They are roughly equal, and B is preferred by a small margin because the Worker already sees every record and Complete. The gains over A are modest: no Cloudflare API token at home and no shared REST limit. Reconciliation is the path of record in all options.
- **Touches settled text:** ADR-0001 §1. B or D needs an "Amends: ADR-0001 §1" draft after owner approval.
- **If no decision by the deadline:** the skeleton uses B as a throwaway choice; ADR-0010 stays Proposed.

### DR-C1-4: API hostname, zone and bootstrap (one-way door #8)
- **Needed by:** Gate C (a domain is needed earlier for the sandbox)
- **Evidence:** F8; K3, K12 (verified)
- **Options:** A. `api.<owner's main domain>` only. B. A **dedicated Reliquary domain** on Cloudflare for the API, plus a second bootstrap host on a different domain **and provider**, serving an offline-signed bootstrap document with no trust material (SR-31). C. `workers.dev` (rejected by PLAN).
- **Recommendation:** B. An active zone puts DNS and the API on one account, so a lockout or billing lapse should not also take down the family's main domain and email.
- **If no decision by the deadline:** the sandbox uses its throwaway domain; Gate C stays blocked.

### DR-C1-5 (input to OD-14): beta and "coming soon" dependencies
- **Needed by:** OD-14 sitting
- **Evidence:** F5, F10; K7, C63
- **Options:**
  - A. Accept the rule "only with a documented, tested fallback that needs no client update" and the F10 classification. Temp-credential action scoping is used server-side only, with the fallback ladder (API preset scope, then break-glass), **documented; test pending** (H13 plus a drill; Gate B exit item).
  - B. No beta or "coming soon" dependencies: the homelab uses a long-lived bucket token.
- **Recommendation:** A, on condition that the drill passes before Gate B; otherwise B applies automatically. Also for the owner (with C2/D3): one parent token plus break-glass is the simpler alternative to the three-token split, if the extra rotation work outweighs the operability gain.

### DR-C1-6 (input to OD-04 and OD-17, with C4 and C2): staging-layer append-only and the default upload target
- **Needed by:** Gate B
- **Evidence:** F4; K3 (bearer URLs), C9 (part replacement), K13 (parts fit the body cap), C4 §F4.3 (create-only mandatory; E_eff); emulated C1-S1 (not evidence about R2)
- **Options:**
  - A. **Append-only enforced at commit.** Presigned targets everywhere. Until real H1 passes (and for multipart parts always), a URL holder can rewrite an uncommitted staged object within its window. The homelab detects it, and the device re-uploads. Replays cost Class A writes (F4 arithmetic). Recorded as an accepted risk (OD-17).
  - B. **Create-only at staging.** Worker-proxied parts for multipart objects. Single PUT presigned with `If-None-Match: *` if real H1 passes, otherwise proxied. Costs Worker CPU per part (unmeasured) and puts the Worker in the data path.
  - C. **Rule-based (recommended):** the target abstraction is built either way. At Gate B, B applies if the C1-S4 proxied-part leg passes (reliable, CPU within C4's seed allowance under BUD-CLOUD); otherwise A, with the owner's explicit risk acceptance.
- **Recommendation:** C. C4 holds that create-only is mandatory (§F4.3); C1 agrees that it should be the target, but the cost of the only multipart-capable route is unmeasured.
- **Touches settled text:** interprets CLAUDE.md "Connectivity" (append-only); does not change it.
- **If no decision by the deadline:** both target kinds are built; the skeleton uses presigned; ADR-0010 stays Proposed.

### DR-C1-7 (input to OD-20 and BUD-CLOUD): staging cap and interim ceiling
- **Needed by:** interim ceiling at Wave 1 exit; final policy at the OD-20 sitting (Wave 2)
- **Evidence:** F4; C4 staging-cap derivation
- **Options:** A. The Worker refuses new uploads above a cap on max(declared, observed) staged bytes (C4: ≈ 1.3 TB at a $25 BUD-CLOUD) and pauses presign when the homelab heartbeat is stale or a canary fails, with C4's plain-language message. B. Alerts only; staging grows until the owner acts.
- **Recommendation:** A, with an **interim hard ceiling set now** (C4's value unless the owner gives another), not alert-only until Gate B.
- **If no decision by the deadline:** the mechanism is built, and the interim ceiling defaults to C4's derived value, because alert-only leaves the bill unbounded during a homelab outage. The owner can raise or remove it.

## Hand-offs

| To | What | Why |
|---|---|---|
| Spike runner (C1-S1..S5 kits) | All additions under §Spikes, including H8b, H15, H16, H2 via the S3 API and binding types, H10 error and `Expect: 100-continue`, a timed roll and corrected decision row, H13 claim-name vector and API fallback, a break-glass drill, 412/429 billing, per-row D1 timing, query plan, a per-family DO variant, the C1-S3 ladder, `cpuTime` only, the proxied-part leg, the C1-S5 rerun with 400, and the T35 → T54 fix | Skeptic issues, rounds 1–2 |
| A3 | Records hash-compare retry; upload-target abstraction in the ingest protocol; `pack/` key form; segment checkpoint primary for > 7-day uploads; feed (pending DR-C1-3); adaptive listing cadence; canary and sentinel keys to ignore | F3, F4, F5, F9 |
| A2 / A4 | Packing decision (IOS-C16) before Gate A; `pack/` reserved | F3 |
| A1 | Keep `_` out of the dedup-ID alphabet (sentinel keys rely on it) | F3 |
| B6 | Part size ≤ ~95 MB while proxied parts remain possible; segment sizing under a hard 7-day ceiling; re-sign cap values | F3, F4, F12 |
| C2 | `rq-gate` counters and the Rate Limiting binding as the first layer; parent-token proposal (three tokens vs one); homelab credential scopes and fallback ladder; per-device cap on outstanding URLs; Worker-enforced re-sign cap; staged-bytes cap enforcement; billing notifications and card-expiry check; Deployment URLs and `workers_dev` in config in the hardening checklist; 412/429 billing `[SB]` | F4, F5, F8, F10 |
| C4 | Upload-target comparison and proxied-part cost line; w including index rows (C62); S_sat; replay cost without Queues ($4.50/M); listing cost during backlogs; feed instead of Queues; observed-bytes cap | F2, F4, F5 |
| C7 / C8 | Dead-man's switch; canary and plan-lapse alerts; paginated nightly export and export-restore drill; retention table; break-glass runbook and drill; token-roll runbook; scheduled lifecycle config check; clients must not pin hosts | F5, F6, F9 |
| D2 / D3 / D5 | Homelab control key; config-signing key; R2 parent secrets (including restore-signing); per-epoch or per-device signing tokens; request auth with replay rules for proxied parts; roll semantics in the revocation design | F4, F5, F8 |
| B2 / B4 | Re-sign client rules with caps; iOS options C–E, including proxied parts, for B4-S2 | F12 |
| G2 | Vectors for request auth, code hashing and ID-encoding checks; aws4fetch cross-check against an independent SigV4 implementation; HEAD-before-re-sign vector; contract test against the previous client build; enum catch-all vector | F4, F7, F8 |
| H1 | Blocked-source list; DR-C1-1..7 to number; ADR-0010 registry row stays Proposed; the 2025-07-03 CRC64NVME release note was not found | Method |
| T2 | Watch: temp-credential local-signing format and the example page (claim names); conditional Complete; D1 single-thread guidance; Idempotency-Key draft status; aws4fetch releases | F5, F7, F10 |
