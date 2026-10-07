# ADR-0010: The control plane is a TypeScript Worker on the owner's domain over D1 and two R2 buckets; API v1 is versioned, batched and additive-only

- **Status:** Proposed
- **Date:** 2026-10-06
- **Owner workstream:** C1
- **Decider:** the owner
- **Gate:** B (R2 key layout, one-way door #7); C for the hostname and bootstrap parts (one-way door #8)
- **Supersedes / Amends:** None by itself. **If the owner chooses DR-C1-3 option B or D**, a separate "Amends: ADR-0001 §1" note is needed, because ADR-0001 §1 names Queues as the notification path. This ADR does not settle that until the owner decides. ADR-0001 §4 (dedup-ID keys, exclusive claim) stays with OD-04 and is not decided here.
- **Evidence:** [`docs/research/c1-cloudflare-control-plane.md`](../research/c1-cloudflare-control-plane.md). Spikes C1-S1 to C1-S5: `spikes/C1-S*/`, and kits `docs/research/kits/C1-S1` to `C1-S4`. C1-S1 to C1-S4 are **emulated, not real R2/Cloudflare**.
- **Normative artifact:** [`docs/design/api-v1.md`](../design/api-v1.md) (Draft outline; the OpenAPI document is Wave 2). The R2 key layout is normative in §Decision 3 below.
- **Traceability:** R-09, R-11, R-12, R-13, R-18, R-37, Q1-3, C-01
- **Owner decisions:** DR-C1-1 to DR-C1-7 (new; H1 to number). Inputs to OD-04, OD-14, OD-17 and OD-20.
- **One-way door:** Yes, #7 (R2 key layout, Gate B) and #8 (API hostname and bootstrap, Gate C)

## Context and problem statement

ADR-0001 puts a Cloudflare control plane between family devices and the homelab. It names R2, Workers, D1/Durable Objects and Queues. A3 then defined the ingest protocol: per-upload staging keys, an advisory lease instead of an exclusive claim, homelab verification, receipts, and reconciliation by listing. This ADR maps that protocol onto Cloudflare. It decides:
- where state lives;
- the R2 key layout;
- the Worker language;
- how the homelab is notified and authenticates;
- background jobs;
- change management;
- the API v1 conventions.

Some choices become hard to change at Gate B, once the skeleton runs on real R2: the key layout and the store behind the API. Others become hard at Gate C, once kits ship with a hostname baked in.

Constraints from settled text:
- the homelab is never exposed and only makes outbound connections (R-12);
- devices can only append and never delete or rewrite backups (R-18);
- the API is treated as under attack;
- no AWS;
- the API runs on the owner's own domain (PLAN C1);
- client-side encryption, with the cloud seeing only opaque IDs.

Important evidence gaps:
- No sandbox account exists. Every Cloudflare spike so far ran on Miniflare/workerd, and Miniflare departs from the R2 docs on the very checks that matter (claim K14, secondary-only).
- D1's capacity at family seed scale is **not established**: the claim that batching keeps load low was contested (K2).

This ADR is therefore written so that no decision rests on an unproven R2 behaviour or on D1 capacity alone.

## Decision drivers

- **R-18 / SR-07, SR-08:** devices append only. Per-upload keys and homelab verification (SR-04) are the safety basis.
- **R-12:** outbound-only homelab. No service is offered to the cloud.
- **BUD-REVOKE:** no new presigned URLs within 60 s; outstanding URLs expire within 15 min.
- **BUD-CPU-REQ:** request-signature verification < 1 ms CPU.
- **BUD-CLOUD, BUD-ABUSE:** owner-set cost ceilings (H2). Staging must not grow without bound.
- **BUD-TTS:** "stored at home" within 24 h. Seconds of notification latency are fine.
- **BUD-SUPPORT:** ≤ 2 h/month of owner time. Operability (migrations, backups, ad-hoc SQL) matters.
- **SR-23:** a Worker compromise costs availability, money or invite abuse, never trust. The Worker holds no trust-forging key.
- **SR-26, SR-31:** no dedup ID in `meta/` keys; bootstrap config carries no trust material.
- **ADR-0001 §6:** restores travel through an expiring R2 location.
- **OD-14:** policy on beta dependencies.

## Considered options

1. **State store:** one D1 database; several D1 databases; SQLite Durable Objects sharded (per family or by ID prefix); a hybrid of D1 plus per-device DOs; KV as an existence cache.
2. **Buckets:** one bucket with prefixes; two buckets (ingest, restore).
3. **Worker language:** TypeScript (Hono); Rust `workers-rs`; TypeScript plus Rust→Wasm modules.
4. **Homelab notification:** R2 notifications → Queues → HTTP pull (ADR-0001 wording); a Worker feed polled by the homelab; DO WebSocket push; R2 notifications → Queue → push consumer Worker → feed; Workers VPC / Tunnel push.
5. **Content path:** presigned URLs; device temporary credentials; content through the Worker.
6. **Homelab R2 access:** Worker-minted temporary credentials; a long-lived bucket token.
7. **Deployments:** gradual deployments; plain `wrangler deploy`.

## Decision

### 1. Topology (in scope, Wave 1)

| Component | Decision |
|---|---|
| `rq-api` Worker | TypeScript (Hono, zod, Drizzle or Kysely, aws4fetch, jose) on a **Workers Custom Domain** `api.<owner-domain>`. `workers_dev = false`; Preview, Version and Deployment URLs handled separately. **Declares no Durable Object classes.** |
| `rq-control` D1 | The control-plane system of record, **provisionally** (§2). |
| `rq-gate` Worker + `DeviceGate` DO | Optional, C2's decision: exact per-device counters, one object per device. A separate Worker bound by `script_name`, so `rq-api` keeps `versions upload`. |
| `rq-ingest` R2 bucket | `staging/`, `meta/`, reserved `pack/`. **No Expiration rule, ever.** |
| `rq-restore` R2 bucket | `restore/`. Expiration about 7 days; 1-day abort. |
| Cron Trigger | One, about every 15 min (§7). |
| Queues, R2 event notifications | Not used in v1, **pending DR-C1-3**. |
| Environments | `local` (pinned emulators), `sandbox` and `production` as **separate Cloudflare accounts**. |

### 2. State store: one D1 database, provisionally, behind a data-access layer (in scope; capacity to be confirmed at Gate B)

- **D1 is chosen for operability:** numbered migrations, 30-day Time Travel, export, and ad-hoc SQL. Correctness does not need DO-grade serialisation, because the lease is advisory (A3). Emulated C1-S2 shows the lease SQL yields exactly one winner in 10,000 of 10,000 trials. That is the logic only.
- **Capacity is not claimed.**
  - D1 runs one query at a time per database (K1).
  - `batch()` saves round trips, but runs its statements sequentially (C24).
  - Write time depends on rows written (K1).
  - With C4's assumptions (6 rows written per file, 5 ms per row-write) and a pessimistic 62.5 MB/s family peak, one database saturates at a mean file size of about 1.9 MB. That is an assumption-based figure, not a measurement.
- **Rules:**
  - All D1 access goes through a data-access layer that hides which store and which database is used.
  - Writes are **set-based**: one statement per table per request (`INSERT … SELECT … FROM json_each(?1)`).
  - Every API request touches D1 at most once (one batch).
- **Pre-agreed fallback**, triggered if the real-D1 kits show more than about 50 % utilisation at E1's file-size mix:
  - (a) split dedup and leases into a second D1 database (the D1 FAQ recommends scale-out across databases);
  - (b) shard that database by ID prefix into N D1 databases, or 16 SQLite DOs.
  - Both are code changes, not protocol changes.
- **Retention**, against D1's fixed 10 GB:
  - feed: 30 days past the homelab cursor;
  - idempotency: 7 days;
  - receipt relay: until the device fetches;
  - audit log: 90 days in D1, archived by the nightly export;
  - leases: 30 days after the terminal state.
  The cron alerts at 50 % and 80 % of 10 GB.
- **Rejected:** KV for leases (eventually consistent); one global DO (same single thread, worse tooling).

### 3. R2 key layout and buckets (in scope; one-way door #7, normative)

| Bucket | Key form | Written by | Read / deleted by |
|---|---|---|---|
| `rq-ingest` | `staging/<dedup_id>/<upload_id>/s<n>` (`s0` always; `s1…` only for A3's segment checkpoint) | Device (presigned PUT/UploadPart); Worker creates and completes multipart | Homelab (get, list, delete after durable commit) |
| `rq-ingest` | `meta/<device_id>/<record_batch_id>.age` | Worker only, create-only | Homelab |
| `rq-ingest` | `pack/<upload_id>/s<n>` (**reserved**; used only if A2/A4 adopt packed uploads, IOS-C16) | Device (presigned) | Homelab |
| `rq-restore` | `restore/<device_id>/<restore_job_id>/<object_id>` | Homelab | Device (presigned GET) |

- `<dedup_id>` is A1's text encoding (ADR-0006). `<upload_id>` is generated by the Worker and is random. Keys stay well under 1,024 bytes.
- **The ingest bucket never carries an Expiration rule.** A CI or cron check asserts that `rq-ingest`'s lifecycle list contains abort rules only. Only the homelab deletes staged objects.
- **7-day multipart abort:** treated as a hard ceiling. The lifecycle doc implies the earliest rule wins (K6), so it probably cannot be extended. Uploads that might take longer use A3's segment checkpoint, driven by the day-6 cron, as their primary mechanism. This is confirmed or relaxed by C1-S1 H8/H8b.
- Two buckets because long-lived tokens scope only to buckets (K7), and because "staging never expires by age" then becomes a checkable property of one bucket (DR-C1-2).

### 4. Upload and record paths (in scope)

- **Content:** device → R2 through presigned PUT (single part) or presigned UploadPart (multipart), issued in windows.
  - Every URL lives ≤ 15 min, with `X-Amz-Expires` always explicit.
  - CreateMultipartUpload and CompleteMultipartUpload run in the Worker.
  - **No condition is sent on Complete:** under per-upload random keys it adds almost nothing, and R2 may abort the upload on a failed condition (K4).
- **Re-sign:** `POST /v1/uploads/{id}/urls` returns fresh URLs for the same keys and UploadId. It is idempotent and refused for revoked devices.
  - Clients re-sign just in time (desktop daemon, Android WorkManager), or after the specific expired-URL error, with a capped retry count.
  - **This is decided for the v1 platforms only.** For iOS, the policy is DR-B4-2 with B4-S2 evidence (K15 contested). The API keeps every IOS-C10 option possible.
- **Records:** device → Worker → R2. The Worker hashes the opaque body, writes `meta/…` with a create-only `onlyIf` and the SHA-256 in custom metadata, and appends the feed event and idempotency rows in one D1 statement group. On a precondition failure it compares hashes: equal means success plus a D1 replay; different means a typed `conflict`.
- **Signed extras** (`Content-MD5`, `If-None-Match: *` on single PUT, Content-Length, `x-amz-checksum-sha256` single and per part) are added **only after the real-R2 C1-S1 kit shows R2 enforces them**. They are defence in depth, never the safety basis. Miniflare results are not evidence about R2.
- **Staging guard rails:**
  - the Worker keeps staged-bytes accounting in D1;
  - it pauses or throttles presigning when the signed homelab heartbeat is older than N hours (N with C7);
  - it refuses new uploads above a staged-bytes cap tied to BUD-CLOUD, **subject to OD-20 / DR-C1-7**. Until that is decided, the cap is "alert only".
- **Append-only at staging:** until real C1-S1 H1 passes, a presigned PUT is a reusable bearer URL. Its holder can rewrite that one uncommitted staged object within the window. Homelab verification detects it. This ADR states that "devices can only append" is **enforced at commit, not at staging**, and asks the owner to confirm (DR-C1-6).

### 5. Worker language (in scope; DR-C1-1)

**TypeScript**, because Rust on Workers is Beta, `workers-rs` is 0.8.7 (pre-1.0), and panic recovery needs nightly with `-Zbuild-std` (K9).

**Opaque-artifact rule:** the Worker never parses envelopes, records, receipts, manifests, bundles or dedup-ID derivations; it hashes and stores bytes. Only these exist in two implementations, pinned by shared G2 vectors:
- request auth;
- invite, enrollment and pairing code hashing;
- ID-encoding checks;
- the OpenAPI schema.

If D3 needs a primitive Web Crypto lacks, that one function is compiled to Wasm.

### 6. Homelab notification and authentication (partly in scope)

- **Notification: pending DR-C1-3.** Recommended: the homelab polls `GET /v1/homelab/feed?after=<seq>` about every 30 s and lists `staging/`, `meta/` and `pack/` at start and hourly. Listing is the path of record. Alternative D (R2 notifications → Queue → push consumer Worker → the same feed) stays closer to ADR-0001's wording. The skeleton uses the feed as a throwaway v0 choice.
- **Workers VPC / Tunnel push: rejected.** The cloud would initiate requests into the homelab (K11), and it is Beta.
- **Authentication: proposals handed to D3, C2 and D2, to be decided in ADR-0014 (Wave 2):**
  - homelab → Worker: requests signed with a homelab Ed25519 control key; the Worker holds only the public key;
  - homelab → R2: two Worker-minted, locally signed temporary credentials (ingest: list/get/head/delete/abort on `staging/`, `meta/`, `pack/`; restore: put and multipart on `restore/`), TTL ≤ 1 h;
  - an offline break-glass bucket token;
  - two R2 parent tokens in the Worker (device-signing, homelab-minting), so that rolling the device token does not cut off the homelab. Their purpose is operability, not containment.
  - **BUD-REVOKE does not depend on any kill switch:** it is met by the 60 s status check and the 15-min URL lifetime.

### 7. Background jobs (in scope)

One Cron Trigger runs idempotent "what is due" queries:
- stale devices and nudges (E3/C3);
- the dead-man's switch on the signed heartbeat (C7);
- the presign-pause flag;
- the day-6 multipart checkpoint;
- D1 size alerts and table pruning.

Lease expiry is lazy. DO alarms are used only inside `rq-gate` (at-least-once, idempotent). No Workflows in v1.

### 8. Change management (in scope)

- **No gradual deployments in v1:** plain `wrangler deploy`. Gradual deployments split traffic per request (K10). If they are adopted later, use version affinity and keep DO classes out of that Worker. `exports` disables `versions upload` and gradual deployments for the Worker that declares them (K10).
- **D1 migrations are expand → deploy → contract** across two releases, because `migrations apply` and the code deploy are not atomic. Take a Time Travel bookmark before each apply.
- **DO class lifecycle changes only via `wrangler deploy` of `rq-gate`.** One call style per DO.
- Pinned compatibility date, bumped in sandbox first. Pinned wrangler/miniflare versions for emulated tests.
- **Beta policy (DR-C1-5 → OD-14):** no Rust Workers, Workers VPC or D1 read replication. One dependency: temp-credential action scoping by local JWT ("API support coming soon"). It is server-side only, and its fallback (the break-glass token) is **documented; test pending** (C1-S1 H13 plus a drill, a Gate B exit item).

### 9. API v1 conventions (in scope as conventions; endpoint schemas to be decided in Wave 2)

Normative detail in [`docs/design/api-v1.md`](../design/api-v1.md) (Draft). In short:
- `/v1/`, additive-only.
- Clients decode enums with an `unknown` catch-all, or enum additions are version-gated.
- Every breaking change raises `min_version` in the same deployment.
- Request schemas strip unknown keys.
- `Reliquary-Client` header required.
- `update_required` as an RFC 9457 problem with **HTTP 400** (426 requires an `Upgrade` header per RFC 9110).
- `Reliquary-Server-Time` header on every response.
- Natural-key idempotency, plus the `Idempotency-Key` header for redeem, pair and restore-job.
- Typed per-item batch results; opaque cursors.
- 503 + `Retry-After` for overload, with jittered backoff.
- A signed bootstrap document at two independent locations (DR-C1-4; key custody D3/D5).

These rest on C1-S5 (ran for real; pass with two conditions).

### Consequences

- **Good:**
  - No decision depends on an unproven R2 behaviour.
  - Staging can never expire by age.
  - The homelab holds no long-lived Cloudflare secret in normal operation.
  - The Worker stays small and needs few second implementations.
  - Owner operations use stock wrangler tooling.
  - The API can evolve without stranding old clients.
- **Bad / accepted trade-offs:**
  - D1 capacity is unproven, and the fallback adds work if triggered.
  - Short URLs cost window and re-sign calls.
  - iOS background uploads are not solved here.
  - The homelab's R2 access depends on the Worker being up (break-glass covers it).
  - No canary deployments.
  - A URL holder can rewrite one uncommitted staged object until R2 create-only is proven (DR-C1-6).
  - The temp-credential format is documented in prose and example, with no normative spec.
- **Follow-up work:**
  - Wave 2: the OpenAPI document.
  - Gate B: real-sandbox runs of the C1-S1 to C1-S4 kits with the proposed additions (H8b, H15, token roll, break-glass drill, per-row D1 timing).
  - ADR-0014: credentials and revocation.
  - C2: quotas and the cap.
  - An "Amends ADR-0001 §1" note if DR-C1-3 is B or D.

### Confirmation

- **C1-S1 (SB kit):** create-only, checksums, lifecycle (H8/H8b), bucket locks, token roll (H11), temp-credential scope (H13), expired-URL error (H10).
- **C1-S2/S3 (SB kits):** real D1 lease race, per-row write cost, presence-check p99 and `rows_read` against BUD-CLOUD.
- **C1-S4 (SB kit):** presign CPU and Ed25519 verify via Workers Logs `cpuTime` against BUD-CPU-REQ.
- **C1-S5** contract test rerun with status 400, kept in CI as a test against the previous client build (G2).
- A CI or cron assertion that `rq-ingest` has no Expiration rule.
- The A0 skeleton on real R2 at Gate B.

## Pros and cons of the options

### State store
- **One D1 (chosen, provisionally).** Good: migrations, Time Travel, export, SQL (C28). Bad: single thread (K1); capacity unmeasured (K2 contested).
- **Several D1 databases.** Good: headroom; recommended by the D1 FAQ (C54). Bad: more bindings. Kept as fallback (a).
- **Sharded SQLite DOs.** Good: horizontal. Bad: self-written migrations; PITR only from object code (C28). Kept as fallback (b).
- **KV.** Bad: eventually consistent. Rejected.

### Buckets
- **Two (chosen).** Good: bucket-scoped tokens separate restore from ingest; no Expiration rule can reach staging (K6, K7). Bad: one more bucket to configure.
- **One.** Bad: one mistyped prefix rule can expire staging.

### Worker language
- **TypeScript (chosen).** Good: GA, native Ed25519/HMAC/SHA-256 (C37), Workers test pool. Bad: small formats twice.
- **Rust.** Good: one implementation. Bad: Beta, pre-1.0, nightly for unwind (K9).

### Notification
- **Worker feed (recommended; DR-C1-3).** Good: no Cloudflare API token at home, no REST lockout. Bad: amends ADR-0001 §1's mechanism.
- **Queues HTTP pull.** Bad: a token at home, 1,200/5 min REST limit, retention and `max_retries` loss modes (A3).
- **Queue push consumer → feed.** Good: closer to ADR-0001. Bad: Queues cost; dropped messages.
- **VPC push.** Rejected (K11).

### Content path
- **Presigned URLs (chosen).** Good: plain HTTP, no SigV4 on the device, no subrequests (K3). Bad: bearer tokens; create-only unproven.
- **Through the Worker.** Bad: 100 MB body cap on Free/Pro zones (K13); availability coupling.

### Deployments
- **Plain deploy (chosen).** Good: one version at a time. Bad: no canary.
- **Gradual.** Bad: per-request split (K10); unavailable with `exports`.

## Evidence

| Claim | Source (primary) | Verdict |
|---|---|---|
| K1 D1 single-threaded; writes depend on rows written | D1 FAQ partial | Verified |
| K2 batching keeps D1 load low | arithmetic + D1 docs | **Contested.** Not used as support; §2 claims no capacity |
| K3 presigned URL properties | R2 presigned-urls.mdx | Verified |
| K4 conditional Create/Complete docs | R2 S3 API table, release notes | Verified |
| K5 checksum types | R2 S3 API table | Verified |
| K6 default 7-day abort; earliest rule wins (example) | R2 object-lifecycles.mdx | Verified |
| K7 token levels; temp-credential scoping | R2 tokens, temporary-credentials | Verified |
| K8 consistency; last writer wins | R2 consistency | Verified |
| K9 Rust Beta; panic handling | Rust page; workers-rs README; crates.io | Verified |
| K10 gradual deployments; `exports` | Workers and DO docs | Verified |
| K11 Workers VPC | VPC overview | Verified |
| K12 Custom Domains; `workers.dev` | Workers routing docs | Verified |
| K13 request body limits | Workers limits | Verified |
| K14 Miniflare ≠ R2 on the checks that matter | Project emulator results | Secondary-only. Supports only "do not rely on emulation", beside K4/K5 |
| K15 re-sign suffices for background queues | B4; R2 presigned-urls | **Contested.** Re-scoped to desktop/Android; iOS left to DR-B4-2 |
| C1-S5 contract rules | Project spike (ran for real) | Project measurement |

## Reversibility

- **Key layout:** hard once real family objects are staged (Gate B). `pack/` is reserved now for that reason.
- **Hostname and bootstrap:** hard once kits ship (Gate C).
- **Store:** reversible behind the data-access layer until production data is large. Moving a 10 GB-capped D1 to shards is a migration, not a protocol change.
- **Worker language:** costly after launch, but the API contract is language-neutral.
- **Notification path:** easy to change; reconciliation is the path of record.

## Alternatives considered

- **Workers VPC / Tunnel push:** cloud-initiated requests into the homelab; Beta.
- **Content through the Worker:** body cap and availability coupling.
- **Create-only CopyObject to a final key:** doubles writes without changing the safety basis.
- **Conditional CompleteMultipartUpload:** adds almost nothing under per-upload keys, and may abort uploads.
- **Device temporary credentials:** SigV4 on devices; still bearer tokens. Parked for desktop.
- **Per-device R2 tokens:** would need a token-creating API token in the Worker.
- **`workers.dev`:** rejected by PLAN.

## Open questions

- Real R2 behaviour (C1-S1 H1–H15, H8b), real D1 capacity (C1-S2/S3), real CPU (C1-S4): spike runner, sandbox, Gate B.
- Notification path (DR-C1-3), second bootstrap location (DR-C1-4), beta policy (DR-C1-5/OD-14), append-only reading (DR-C1-6), staging cap (DR-C1-7/OD-20): owner.
- Request-auth format, revocation, credential scoping and rotation: D3/C2 (ADR-0014), Wave 2.
- Packed uploads: A2/A4, Gate A.
- iOS URL policy: B4, D3 (DR-B4-2).
- Idempotency-Key draft publication status: H1/T2.
- OpenAPI document and endpoint schemas: C1, Wave 2.
