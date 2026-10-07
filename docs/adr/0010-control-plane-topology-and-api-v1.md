# ADR-0010: The control plane is a TypeScript Worker on the owner's domain over two D1 databases and two R2 buckets, with server-chosen upload targets; API v1 is versioned, batched and additive-only

- **Status:** Proposed
- **Date:** 2026-10-07 (first draft 2026-10-06; revised after the second skeptic round)
- **Owner workstream:** C1
- **Decider:** the owner
- **Gate:** B (R2 key layout, one-way door #7; default upload-target kind); C for the hostname and bootstrap parts (one-way door #8)
- **Supersedes / Amends:** None by itself.
  - **If the owner chooses DR-C1-3 option B or D**, a separate "Amends: ADR-0001 §1" note is needed, because ADR-0001 §1 names Queues as the notification path. This ADR does not settle that until the owner decides.
  - ADR-0001 §4 (dedup-ID keys, exclusive claim) stays with **OD-04**. The key layout in §Decision 3 presupposes OD-04's per-upload keys.
- **Evidence:** [`docs/research/c1-cloudflare-control-plane.md`](../research/c1-cloudflare-control-plane.md). Spikes C1-S1 to C1-S5 are in `spikes/C1-S*/`, and the kits in `docs/research/kits/C1-S1` to `C1-S4`. C1-S1 to C1-S4 are **emulated, not real R2/Cloudflare**, and their kits are "kit-ready (pending additions)".
- **Normative artifact:** [`docs/design/api-v1.md`](../design/api-v1.md) (Draft outline; the OpenAPI document is Wave 2). The R2 key layout is normative in §Decision 3 below.
- **Traceability:** R-09, R-11, R-12, R-13, R-18, R-37, Q1-3, C-01
- **Owner decisions:** DR-C1-1 to DR-C1-7 (new; H1 to number). Inputs to OD-04, OD-14, OD-17 and OD-20.
- **One-way door:** Yes, #7 (R2 key layout, Gate B) and #8 (API hostname and bootstrap, Gate C)

## Context and problem statement

ADR-0001 puts a Cloudflare control plane between family devices and the homelab. It names R2, Workers, D1/Durable Objects and Queues. A3 then defined the ingest protocol: per-upload staging keys, an advisory lease instead of an exclusive claim, homelab verification, receipts, and reconciliation by listing. This ADR maps that protocol onto Cloudflare. It decides:
- where state lives;
- the R2 key layout;
- how content reaches R2;
- the Worker language;
- how the homelab is notified;
- background jobs and detection;
- change management;
- the API v1 conventions.

Some choices become hard to change at Gate B, once the skeleton runs on real R2: the key layout and the stores behind the API. Others become hard at Gate C, once kits ship with a hostname baked in.

Constraints from settled text:
- the homelab is never exposed and only makes outbound connections (R-12);
- devices can only append and never delete or rewrite backups (R-18);
- the API is treated as under attack;
- no AWS;
- the API runs on the owner's own domain (PLAN C1);
- client-side encryption, with the cloud seeing only opaque IDs.

Important evidence gaps:
- No sandbox account exists. Every Cloudflare spike so far ran on Miniflare/workerd, and Miniflare departs from the R2 docs on the very checks that matter (claim K14, secondary-only).
- D1's capacity at family seed scale is **not established**. The claim that batching keeps load low was contested in both skeptic rounds (K2).
- The cost of streaming parts through the Worker is **not measured**.

This ADR is therefore written so that no decision rests on an unproven R2 behaviour, on D1 capacity, or on an unmeasured cost. Where one of those matters, it states a rule that the Gate B evidence will apply.

## Decision drivers

- **R-18 / SR-07, SR-08:** devices append only. C4 §F4.3 reads this as requiring create-only writes at staging. Per-upload keys and homelab verification (SR-04) are the integrity basis.
- **R-12:** outbound-only homelab. No service is offered to the cloud.
- **BUD-REVOKE:** no new presigned URLs within 60 s; outstanding URLs expire within 15 min.
- **BUD-CPU-REQ:** request-signature verification < 1 ms CPU.
- **BUD-CLOUD, BUD-ABUSE:** owner-set cost ceilings (H2). Staging must not grow without bound, and replayed writes must be bounded.
- **BUD-TTS:** "stored at home" within 24 h. Seconds of notification latency are fine.
- **BUD-SUPPORT:** ≤ 2 h/month of owner time. Operability (migrations, backups, ad-hoc SQL, few secrets) matters.
- **SR-23:** a Worker compromise costs availability, money or invite abuse, never trust. The Worker holds no trust-forging key.
- **SR-26, SR-31:** no dedup ID in `meta/` keys; the bootstrap config carries no trust material.
- **ADR-0001 §6:** restores travel through an expiring R2 location.
- **OD-14:** policy on beta dependencies.

## Considered options

1. **State store:** one D1 database; two D1 databases by function; D1 sharded; SQLite Durable Objects (sharded or one per family); a hybrid with per-device DOs; KV as an existence cache.
2. **Buckets:** one bucket with prefixes; two buckets (ingest, restore).
3. **Content path:** presigned URLs only; Worker-proxied parts only; **server-chosen upload targets** (either kind); device temporary credentials.
4. **Worker language:** TypeScript (Hono); Rust `workers-rs`; TypeScript plus Rust→Wasm modules.
5. **Homelab notification:** R2 notifications → Queues → HTTP pull (ADR-0001 wording); a Worker feed polled by the homelab; DO WebSocket push; R2 notifications → Queue → push consumer Worker → feed; Workers VPC / Tunnel push.
6. **Homelab R2 access:** Worker-minted temporary credentials; a long-lived bucket token.
7. **Deployments:** gradual deployments; plain `wrangler deploy`.

## Decision

### 1. Topology (in scope, Wave 1)

| Component | Decision |
|---|---|
| `rq-api` Worker | TypeScript (Hono, zod, Drizzle or Kysely, aws4fetch pinned and cross-checked, jose) on a **Workers Custom Domain** `api.<domain>`; the domain itself is DR-C1-4. `workers_dev = false` **in config** (the source of truth). Preview, Version and Deployment URLs handled separately. **Declares no Durable Object classes.** |
| `rq-dedup` D1 | Dedup index, leases, uploads and parts, staged-bytes accounting. **Provisional** (§2). |
| `rq-control` D1 | Accounts, devices, invites and codes, feed, receipt relay, idempotency, audit, flags. **Provisional** (§2). |
| `rq-gate` Worker + `DeviceGate` DO | Optional, C2's decision: exact per-device counters, one object per device. A separate Worker bound by `script_name`, so `rq-api` keeps `versions upload`. |
| `rq-ingest` R2 bucket | `staging/`, `meta/`, reserved `pack/`, sentinels. **No Expiration rule, ever.** |
| `rq-restore` R2 bucket | `restore/`. Expiration about 7 days; 1-day abort. |
| Cron Trigger | One, about every 15 min (§7). |
| Queues, R2 event notifications | Pending DR-C1-3. |
| Environments | `local` (pinned emulators), `sandbox` and `production` as **separate Cloudflare accounts**. |

### 2. State store: two D1 databases by function, provisionally, behind a data-access layer (in scope; capacity to be confirmed at Gate B)

- **D1 is chosen for operability:** numbered migrations, 30-day Time Travel on Paid, export, and ad-hoc SQL. Correctness does not need DO-grade serialisation, because the lease is advisory (A3). Emulated C1-S2 shows the lease SQL yields exactly one winner in 10,000 of 10,000 trials. That covers the logic only.
- **Two databases from day one**, because:
  - the D1 FAQ says D1 is "designed for horizontal scale out across multiple, smaller (10 GB) databases";
  - one database is a family-wide failure domain: an overloaded dedup index would also block enrollment and homelab commits (K1, adversary review);
  - splitting later would be a live migration under the very load that forced it.
  No operation needs atomicity across the two. Cross-database steps (revocation check then lease; commit mark then receipt) are idempotent on natural keys.
- **Capacity is not claimed.**
  - D1 runs one query at a time per database (K1).
  - `batch()` saves round trips but runs its statements sequentially.
  - Write time depends on rows written, and index entries count as extra rows.
  - With C4's assumptions (6 rows per file, 5 ms per row-write) and a pessimistic 62.5 MB/s family peak, one database saturates at a mean file size of about 1.9 MB. That is an assumption-based figure, not a measurement.
- **Rules:**
  - All D1 access goes through a data-access layer that hides which store and which database is used.
  - Writes are **set-based**: one statement per table per request (`INSERT … SELECT … FROM json_each(?1)`).
  - Every API request touches each database at most once (one batch).
- **Pre-agreed next step:** if the real-D1 kits show more than about 50 % utilisation of `rq-dedup` at E1's file-size mix, shard `rq-dedup` by a dedup-ID character into N D1 databases, or 16 SQLite DOs. This is a code change, not a protocol change. A per-family DO variant is measured in the same kits.
- **Retention**, against D1's fixed 10 GB per database:
  - feed: 30 days past the homelab cursor;
  - idempotency: 7 days;
  - receipt relay: until the device fetches;
  - audit log: 90 days in D1, archived by the nightly export;
  - uploads and leases: 30 days after the terminal state.
  The cron alerts at 50 % and 80 % of 10 GB, per database.
- **Backup:** a signed, paginated `GET /v1/homelab/export` (keyset cursors, bounded pages, quiet hour) over the cloud-only tables. `wrangler d1 export` is not run against production in use, because "a running export will block other database requests".
- **Rejected:** KV for leases (eventually consistent); one global DO (same single thread, worse tooling).

### 3. R2 key layout and buckets (in scope; one-way door #7, normative; conditional on OD-04)

| Bucket | Key form | Written by | Read / deleted by |
|---|---|---|---|
| `rq-ingest` | `staging/<dedup_id>/<upload_id>/s<n>` (`s0` always; `s1…` only for A3's segment checkpoint) | Device, through its upload target (§4); Worker creates and completes multipart | Homelab (get, list, delete after durable commit) |
| `rq-ingest` | `meta/<device_id>/<record_batch_id>.age` | Worker only, create-only | Homelab |
| `rq-ingest` | `pack/<upload_id>/s<n>` (**reserved**; used only if A2/A4 adopt packed uploads, IOS-C16) | Device, same rules as `staging/` | Homelab |
| `rq-ingest` | `staging/_sentinel/<yyyy-mm-dd>`; `canary/<token>` | Cron, via the binding | Homelab checks sentinels; both are ignored by reconciliation |
| `rq-restore` | `restore/<device_id>/<restore_job_id>/<object_id>` | Homelab | Device (presigned GET) |

- `<dedup_id>` is A1's text form (`rd1-…`, alphabet `[a-z0-9-]`; ADR-0006), so `_sentinel` cannot collide with it. `<upload_id>` is generated by the Worker and is random. Keys stay well under 1,024 bytes.
- **The ingest bucket never carries an Expiration rule.** Only the homelab deletes staged objects. This is guarded two ways:
  - token-free: the homelab alerts if a sentinel younger than 30 days disappears without its own delete;
  - config: a scheduled check of `rq-ingest`'s lifecycle list from the owner's admin machine or CI with a read-only token (C8).
- **7-day multipart abort:** a hard ceiling. The lifecycle doc's example implies the earliest rule wins (K6). Uploads that might take longer use A3's segment checkpoint, driven by the day-6 cron, as their primary mechanism. C1-S1 H8/H8b confirm or relax this.
- **Two buckets** because long-lived tokens scope only to buckets (K7), and because "staging never expires by age" becomes a property of one bucket (DR-C1-2). ADR-0001 §6's "expiring R2 prefix" for restores is kept as a prefix in its own expiring bucket.

### 4. Content and record paths (abstraction in scope; default target kind decided at Gate B by the rule below)

- **Server-chosen upload targets (decided).** For each single object or part, `POST /v1/uploads` and `POST /v1/uploads/{id}/parts` return a target `{method, url, headers, auth}`. The two kinds are:
  - `auth: none`: a presigned R2 URL on `<ACCOUNT_ID>.r2.cloudflarestorage.com`;
  - `auth: device`: a Worker URL on the API host that needs the device's request signature (D3), streamed to R2 through the binding.
  Every client supports both kinds from its first release, sends exactly what the target says, and never constructs or pins hosts. The server can switch kinds, per object class, without a client update.
- **Default target kind: pre-agreed rule (DR-C1-6).**
  1. At Gate B, run the real C1-S1 kit and the C1-S4 **proxied-part leg** (16 MiB parts through the binding; Workers Logs `cpuTime`, wall time, errors).
  2. If proxied parts are reliable and their CPU keeps a 10 TB seed within C4's seed allowance under BUD-CLOUD, **multipart objects default to proxied parts**. This is the only way to make multipart staging create-only, because re-uploading a part number replaces the part.
  3. Single-PUT objects default to presigned PUT with a signed `If-None-Match: *` **if real R2 enforces it** (H1); otherwise to proxied.
  4. If the proxied leg fails, presigned is the default everywhere, and the owner records the staging-rewrite risk as accepted (OD-17).
  - Until Gate B, the skeleton uses presigned targets.
  - C1 leans to proxied parts for multipart objects, but that lean rests on unmeasured CPU. **It is not decided here.**
- **Presigned targets:** every URL lives ≤ 15 min, with `X-Amz-Expires` always explicit. Signed extras (`Content-MD5`, `If-None-Match: *`, Content-Length, `x-amz-checksum-sha256` single and per part, CRC64NVME full-object) are added **only after the real-R2 C1-S1 kit shows R2 enforces them**. Miniflare results are not evidence about R2.
- **Proxied targets:** the Worker refuses a second write of the same `(upload_id, part)` with a D1 conditional insert. A retry whose part MD5 matches the stored part's ETag is answered as success. Part size stays below about 95 MB while this kind remains possible (100 MB body cap on Free/Pro zones).
- **Multipart control:** CreateMultipartUpload and CompleteMultipartUpload run in the Worker. **No condition is sent on Complete:** under random per-upload keys it adds almost nothing, and R2 may abort the upload on a failed condition (K4).
- **Deletion rule:** the Worker **never presigns DELETE**, and no device credential ever includes `DeleteObject` or `AbortMultipartUpload`. A device may cancel its own *open* upload only through the Worker, which refuses once the upload is `staged`.
- **Re-sign:** `POST /v1/uploads/{id}/urls` returns fresh targets for the same keys and UploadId.
  - It is idempotent and refused for revoked devices and closed uploads.
  - For single-PUT uploads the Worker first `head()`s the key. If the object exists, it marks the upload `staged` and refuses (SR-07).
  - Clients re-sign just in time (desktop daemon, Android WorkManager), or after the specific expired-URL error. The re-sign cap is **enforced by the Worker**, not only by clients.
  - **This is decided for the v1 platforms only.** For iOS, the policy is DR-B4-2 with B4-S2 evidence (K15 contested). Proxied targets are one of the iOS options.
- **Records:** device → Worker → R2. The Worker hashes the opaque body, writes `meta/…` with a create-only `onlyIf` and the SHA-256 in custom metadata, and appends the feed event and idempotency rows in one `rq-control` statement group. On a precondition failure it compares hashes: equal means success plus a D1 replay; different means a typed `conflict`.
- **Staging guard rails:**
  - the Worker accounts declared staged bytes in `rq-dedup`;
  - observed bytes come from the homelab's hourly listing and, while the homelab is silent, a daily Worker `list()`;
  - the cap and alerts key on **max(declared, observed)**;
  - an alert fires on "committed but not deleted after N hours";
  - presign is paused or throttled when the signed homelab heartbeat is older than N hours (N with C7);
  - the Worker refuses new uploads above a staged-bytes cap tied to BUD-CLOUD (DR-C1-7). An **interim hard ceiling** (C4's ≈ 1.3 TB at $25 unless the owner sets another) applies from the first production deploy;
  - Cloudflare billing notifications are a Gate B exit item.
- **Append-only at staging:** while any presigned target is in use, a URL holder can rewrite one uncommitted staged object within its window. For multipart parts this holds even if R2 enforces `If-None-Match`. Homelab verification detects it. Whether that is acceptable ("append-only enforced at commit") or whether staging must be create-only is the owner's decision (DR-C1-6, via OD-04/OD-17). This ADR does not assume either answer.

### 5. Worker language (in scope; DR-C1-1)

**TypeScript**, because Rust on Workers is Beta, `workers-rs` is 0.8.7 (pre-1.0), and panic recovery needs nightly with `-Zbuild-std` (K9).

**Opaque-artifact rule:** the Worker never parses envelopes, records, receipts, manifests, bundles or dedup-ID derivations; it hashes and stores bytes. Only these exist in two implementations, pinned by shared G2 vectors:
- request auth;
- invite, enrollment and pairing code hashing;
- ID-encoding checks;
- the OpenAPI schema.

aws4fetch (1.0.20, last published 2024-08-28) is pinned, vendor-reviewed, and cross-checked in G2 vectors against an independent SigV4 implementation used only at test time. A small in-house presigner is the fallback. If D3 needs a primitive Web Crypto lacks, that one function is compiled to Wasm.

### 6. Homelab notification and authentication (partly in scope)

- **Notification: pending DR-C1-3.** The candidates are:
  - **B:** the homelab polls `GET /v1/homelab/feed?after=<seq>` about every 30 s and lists `staging/`, `meta/` and `pack/`;
  - **D:** R2 notifications → Queue → push consumer Worker → the same feed, which is closer to ADR-0001's wording.
  They are roughly equal, and B is preferred by a small margin. Listing is the path of record in both. Listing cadence adapts to backlog size (A3/C4), because a full listing costs one Class A call per 1,000 objects. The skeleton uses B as a throwaway v0 choice.
- **Workers VPC / Tunnel push: rejected.** A Tunnel is an outbound connection, so network direction is not the objection. The objection is that the cloud would initiate application requests to homelab services, so a compromised Worker or Cloudflare account could reach the homelab (K11). It is also Beta.
- **Authentication: proposals handed to D3, C2 and D2, to be decided in ADR-0014 (Wave 2):**
  - homelab → Worker: requests signed with a homelab Ed25519 control key; the Worker holds only the public key.
  - homelab → R2: two Worker-minted temporary credentials, TTL ≤ 1 h:
    - ingest: list, get, head, delete and abort on `staging/`, `meta/`, `pack/`;
    - restore: put and multipart on `restore/`.
    The fallback ladder is local-JWT action scoping → the Temporary Credentials API with the `object-read-write` preset and prefixes → an offline break-glass bucket token. None of it is tested yet.
  - R2 parent tokens in the Worker:
    - device-signing (`rq-ingest`);
    - homelab-minting;
    - **restore-signing** (Object Read on `rq-restore`, for device restore GETs).
    Rolling one does not stop the others. The purpose is operability, not containment. The simpler one-token-plus-break-glass alternative stays open (DR-C1-5).
  - **BUD-REVOKE does not depend on any kill switch:** it is met by the 60 s status check and the 15-min URL lifetime, or by the per-part check on proxied targets.

### 7. Background jobs and detection (in scope)

One Cron Trigger runs idempotent "what is due" work:
- stale devices and nudges (E3/C3);
- the dead-man's switch on the signed heartbeat (C7);
- **R2 parent-token canaries**: per token, presign and `fetch` a PUT and a HEAD on `canary/<token>`; the binding cleans up. On failure the Worker sets `presign_paused`, answers `503 r2_credentials_unavailable` (retryable), and alerts the owner out of band;
- **staging sentinels** (daily);
- **observed staged bytes** (daily, while the homelab is silent);
- the presign-pause flag;
- the day-6 multipart checkpoint;
- D1 size alerts and table pruning;
- **plan and quota error alerts** (CPU limit exceeded, D1 quota errors).

Lease expiry is lazy. DO alarms are used only inside `rq-gate` (at-least-once, idempotent). No Workflows in v1.

### 8. Change management and plan dependencies (in scope)

- **No gradual deployments in v1:** plain `wrangler deploy`. Gradual deployments route each request independently (K10). If they are adopted later, use version affinity and keep DO classes out of that Worker. `exports` disables `versions upload` and gradual deployments for the Worker that declares them (K10).
- **D1 migrations are expand → deploy → contract** across two releases, per database, because `migrations apply` and the code deploy are not atomic. Take a Time Travel bookmark before each apply.
- **DO class lifecycle changes only via `wrangler deploy` of `rq-gate`.** One call style per DO.
- Pinned compatibility date, bumped in sandbox first. Pinned wrangler/miniflare versions for emulated tests.
- **Workers Paid is a hard dependency.** A lapse would break:
  - CPU above Free's 10 ms;
  - D1 queries per invocation (Free 50 vs Paid 1,000);
  - Time Travel (Free 7 days vs Paid 30);
  - seed-month D1 write volume.
  The §7 alerts and a C2 billing and card-expiry check detect a lapse.
- **Beta policy (DR-C1-5 → OD-14):** no Rust Workers, Workers VPC or D1 read replication. One dependency: temp-credential action scoping by local JWT ("API support coming soon"). It is server-side only, and its fallback ladder is **documented; test pending** (C1-S1 H13 plus a drill, a Gate B exit item).

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
- 503 + `Retry-After` for overload and for `r2_credentials_unavailable`, with jittered backoff.
- Upload targets (§4); clients never pin the R2 or API host.
- A signed bootstrap document at two independent locations (DR-C1-4; key custody D3/D5).

These rest on C1-S5 (ran for real; pass with two conditions; rerun with 400 pending).

### Consequences

- **Good:**
  - No decision depends on an unproven R2 behaviour or an unmeasured cost. Where one matters, a pre-agreed rule decides at Gate B.
  - The content path can move between presigned and proxied without a client update.
  - Staging can never expire by age, and that is checked.
  - A broken or rolled token pauses uploads with a clear error instead of a silent retry storm.
  - The homelab holds no long-lived Cloudflare secret in normal operation.
  - The Worker stays small and needs few second implementations.
  - Owner operations use stock wrangler tooling.
  - The API can evolve without stranding old clients.
- **Bad / accepted trade-offs:**
  - D1 capacity is unproven, and sharding adds work if triggered. Two databases mean two migration sets.
  - Clients implement two target kinds.
  - Proxied parts, if chosen, put the Worker in the data path.
  - Short URLs cost window and re-sign calls.
  - iOS background uploads are not solved here.
  - The homelab's R2 access depends on the Worker being up (break-glass covers it).
  - No canary deployments.
  - While presigned targets are used, a URL holder can rewrite an uncommitted staged object (DR-C1-6).
  - The temp-credential claim names are documented only by example.
  - An interim staging ceiling can refuse uploads during a long homelab outage.
- **Follow-up work:**
  - Wave 2: the OpenAPI document.
  - Gate B: real-sandbox runs of the C1-S1 to C1-S4 kits with the proposed additions (H8b, H15, H16, token roll, break-glass drill, per-row D1 timing, proxied-part leg).
  - ADR-0014: credentials, revocation and request auth (including replay rules for proxied parts).
  - C2: quotas, the cap, and hardening.
  - An "Amends ADR-0001 §1" note if DR-C1-3 is B or D.

### Confirmation

- **C1-S1 (SB kit):** create-only, checksums (H6, H15, H16), lifecycle (H8/H8b), bucket locks, token roll (H11), temp-credential scope and claim names (H13), expired-URL error (H10), billing of 412/429.
- **C1-S2/S3 (SB kits):** real D1 lease race, per-row write cost, presence-check p99 and `rows_read` against BUD-CLOUD, per-family DO variant.
- **C1-S4 (SB kit):** presign CPU and Ed25519 verify via Workers Logs `cpuTime` against BUD-CPU-REQ; the proxied-part leg against BUD-CLOUD (C4 seed allowance).
- **C1-S5** contract test rerun with status 400, kept in CI as a test against the previous client build (G2).
- Sentinel and lifecycle-config checks in operation.
- Canary alert fired and cleared in a sandbox token roll.
- The A0 skeleton on real R2 at Gate B.

## Pros and cons of the options

### State store
- **Two D1 databases by function (chosen, provisionally).** Good: migrations, Time Travel, export, SQL; failure isolation; recommended scale-out pattern (C54). Bad: two migration sets; capacity unmeasured (K2 contested).
- **One D1.** Good: simplest. Bad: one failure domain (K1); a later split would be a live migration.
- **Sharded D1 or SQLite DOs, or one DO per family.** Good: horizontal. Bad (DOs): self-written migrations; PITR only from object code. Kept as the next step and measured in the kits.
- **KV.** Bad: eventually consistent. Rejected.

### Buckets
- **Two (chosen).** Good: bucket-scoped tokens separate restore from ingest; no Expiration rule can reach staging (K6, K7). Bad: one more bucket to configure.
- **One.** Bad: one mistyped prefix rule can expire staging.

### Content path
- **Server-chosen targets (chosen).** Good: the default can change without a client update; either kind available per object class. Bad: two client code paths.
- **Presigned only.** Good: plain HTTP; Worker off the data path; no subrequests (K3). Bad: bearer replay (K3); multipart parts can never be create-only (C9); replay cost.
- **Worker-proxied only.** Good: create-only per part; revocation at send; iOS option. Bad: Worker in the data path; CPU per part unmeasured. The 100 MB body cap (K13) is **not** a reason against it for 5–16 MiB parts.
- **Device temporary credentials.** Bad: SigV4 on devices; still bearer tokens. Parked for desktop.

### Worker language
- **TypeScript (chosen).** Good: GA, native Ed25519/HMAC/SHA-256 (C37), Workers test pool. Bad: small formats implemented twice.
- **Rust.** Good: one implementation. Bad: Beta, pre-1.0, nightly for unwind (K9).

### Notification
- **Worker feed (B) or push consumer → feed (D).** Good: no Cloudflare API token at home. B: no Queues line. D: closer to ADR-0001. Bad: both amend ADR-0001 §1's mechanism.
- **Queues HTTP pull (A).** Bad: a token at home; the 1,200/5 min REST limit is shared with other REST use.
- **VPC push.** Rejected (K11; trust direction).

### Deployments
- **Plain deploy (chosen).** Good: one version at a time. Bad: no canary.
- **Gradual.** Bad: per-request split (K10); unavailable with `exports`.

## Evidence

| Claim | Source (primary) | Verdict |
|---|---|---|
| K1 D1 single-threaded; writes depend on rows written | D1 FAQ partial | Verified |
| K2 batching keeps D1 load low | arithmetic + D1 docs | **Contested.** Not used as support; §2 claims no capacity |
| K3 presigned URL properties (bearer, reusable, S3 host only) | R2 presigned-urls.mdx | Verified |
| K4 conditional Create/Complete docs | R2 S3 API table, release notes | Verified |
| K5 checksum types | R2 S3 API table | Verified |
| K6 default 7-day abort; earliest rule wins (example) | R2 object-lifecycles.mdx | Verified |
| K7 token levels; temp-credential scoping | R2 tokens, temporary-credentials | Verified |
| K8 consistency; last writer wins | R2 consistency | Verified |
| K9 Rust Beta; panic handling | Rust page; workers-rs README; crates.io | Verified |
| K10 gradual deployments; `exports` | Workers and DO docs | Verified |
| K11 Workers VPC | VPC overview | Verified |
| K12 Custom Domains; `workers.dev`; Deployment URLs | Workers routing docs | Verified |
| K13 request body limits | Workers limits | Verified. Shows that parts fit; not used against proxying |
| K14 Miniflare ≠ R2 on the checks that matter | Project emulator results | Secondary-only. Supports only "do not rely on emulation", beside K4/K5 |
| K15 re-sign suffices for background queues | B4; R2 presigned-urls | **Contested.** Re-scoped to desktop/Android; iOS left to DR-B4-2 |
| Part replacement on re-upload (C9) | R2 S3 API, upload-objects | Primary |
| Export blocks D1; Free-plan limits; index rows count as writes (C60–C62) | D1 docs (2026-10-07) | Primary |
| Temporary Credentials API presets and prefixes (C63) | R2 temporary-credentials | Primary |
| Replay cost and create-only position | C4 §F4.3 (project, verified prices) | Project model |
| C1-S5 contract rules | Project spike (ran for real) | Project measurement |

## Reversibility

- **Key layout:** hard once real family objects are staged (Gate B). `pack/` is reserved now for that reason.
- **Hostname and bootstrap:** hard once kits ship (Gate C).
- **Content path:** easy, by design: a server setting, once every client supports both target kinds.
- **Stores:** reversible behind the data-access layer until production data is large. Sharding `rq-dedup` is a migration, not a protocol change.
- **Worker language:** costly after launch, but the API contract is language-neutral.
- **Notification path:** easy to change; reconciliation is the path of record.

## Alternatives considered

- **Workers VPC / Tunnel push:** cloud-initiated application requests into the homelab; Beta.
- **Create-only CopyObject to a final key:** doubles writes without changing the safety basis.
- **Conditional CompleteMultipartUpload:** adds almost nothing under per-upload keys, and may abort uploads.
- **Device temporary credentials:** SigV4 on devices; still bearer tokens. Parked for desktop.
- **Per-device or per-epoch R2 signing tokens:** would avoid a family-wide outage on a roll; handed to D3.
- **One D1 database:** single failure domain; rejected as a starting point.
- **`workers.dev`:** rejected by PLAN.

## Open questions

- Real R2 behaviour (C1-S1 H1–H16, H8b), real D1 capacity (C1-S2/S3), real CPU and the proxied-part leg (C1-S4): spike runner, sandbox, Gate B.
- Notification path (DR-C1-3), hostname, zone and second bootstrap location (DR-C1-4), beta policy and token count (DR-C1-5/OD-14), staging append-only and default target (DR-C1-6), staging cap and interim ceiling (DR-C1-7/OD-20): owner.
- Request-auth format and replay rules, revocation, credential scoping and rotation: D3/C2 (ADR-0014), Wave 2.
- Whether R2 bills 412/429/403 on replayed or refused writes: C2/C4 `[SB]`.
- Packed uploads: A2/A4, Gate A.
- iOS URL policy: B4, D3 (DR-B4-2).
- Idempotency-Key draft publication status: H1/T2.
- OpenAPI document and endpoint schemas: C1, Wave 2.
