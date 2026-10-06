# A3. Ingest protocol, receipts and the client/server state machine

- **Workstream:** A3 (see `docs/research/PLAN.md`, section "A3.")
- **Status:** Draft (analyst deep read, Wave 1, batch W1-b). Not yet under skeptic review. Spike results pending (a separate spike runner is running A3-S1/S2 in parallel).
- **Date:** 2026-09-29 (last updated 2026-09-29)
- **Feeds:** ADR-0009 (reserved in `docs/adr/README.md`; draft is the next stage), `docs/spec/ingest-protocol.md` (next stage), OD-04, one-way door #5 (receipt format), new decision requests DR-A3-1 to DR-A3-3 (below; H1 assigns OD numbers)
- **Depends on:** C1-S1 (real R2 behaviour), D1-S1/S2 (threat register: **`docs/security/threat-model.md` does not exist yet**, so no SR-xx IDs are cited), A1 (dedup ID), A2 (metadata record, content object), F3, A6 (durable-commit contract), A4 (bundles)
- **Traceability rows advanced:** R-11, R-12, R-18, R-27, R-30 (state map), R-40, R-45, C-02, C-03 (see `docs/research/traceability.md`)

## Summary

Recommendation, in one line: **R2 listing is the source of truth for what is staged, the homelab is the source of truth for what is committed, and the device holds the only proof that counts, a homelab-signed receipt. The claim, the queue and D1 are optimisations that can be lost, rolled back or lie without losing data.**

1. **Uploads are optimistic and keyed per upload.** A claim is an *advisory lease*, not a lock. Each upload goes to its own staging key. The homelab keeps the first verified copy and drops the rest. The reasons: R2 is last-writer-wins on a shared key, and CompleteMultipartUpload accepts no conditional headers. A lease that a slow or dead device can hold would also block other devices. The lease exists only to save bandwidth.
2. **Reconciliation is the primary path.** The homelab lists the drained `meta/` and `staging/` prefixes, which R2 lists with strong consistency. Queue messages are hints. The homelab acks a message as soon as the work is written to its own durable inbox. Loss mechanisms beyond the 14-day retention: the queue's default retention is 4 days, not 14, and messages are deleted once they reach `max_retries`.
3. **"Already have it" is a typed answer and never means safe.** The device still sends its record. The record stays "awaiting commit" until the device's own receipt arrives. After a bounded wait the device uploads its own copy anyway (the safety valve). A lying or rolled-back cloud can therefore delay an item but not suppress it.
4. **Receipts v1 are per-record entries in homelab-signed per-device batches.** This is the CE spike receipt generalised to N entries. A Merkle log with C2SP checkpoints is deferred to v2 for re-verification.
5. **The durable-commit contract is an ordered, idempotent sequence keyed by (dedup ID, record ID):** blob fsync → raw record archive → catalog → sign receipt → publish to Worker → delete staging.

Confidence: **high** on the Cloudflare facts (primary docs source). **Medium** on the protocol design: it is reasoned from those facts and from similar systems, but it is not yet model-checked (A3-S1) or run on real R2 (A3-S3).

## Questions

| # | Question | Short answer | Confidence |
|---|---|---|---|
| 1 | States: server, client, side states | Server per upload: `claimed → staged → (committed \| rejected \| duplicate-dropped \| abandoned)`. Per dedup ID the cloud holds `absent / in-flight / committed`, a projection. Homelab per record: `received → verifying → (committed + receipt \| awaiting-commit \| rejected)`. Client: 11 states plus side states (§F1). | Medium |
| 2 | Exclusive claim with TTL vs parallel per-upload keys; takeover; 7-day abort | Per-upload keys always. The claim is an advisory lease renewed by progress, and it never blocks another device after it expires or once that device's safety valve fires. Takeover means another device simply uploads. There is no hand-over of an UploadId. For the 7-day abort, the Worker checkpoints a slow upload into segment objects before day 7 (to be spiked). The fallbacks are a restart, then "suggest USB". | Medium (design); High (R2 facts C12–C16) |
| 3 | "Already have it" semantics | Typed answers `MISSING`, `IN_FLIGHT` and `COMMITTED`, plus the committed receipt as proof (CE §10). The device always sends its own record and is safe only with its own receipt. The answer grants no read rights. Anything unknown or untyped counts as MISSING-later, never as safe (Immich #31622 lesson). | High (principle); Medium (valve timing) |
| 4 | Receipts: per file, Merkle log, watermark | v1: per-device **batch receipt**, a signed list of per-record entries, each binding (record_id, meta_sha256, dedup_id, size). N = 1 is the CE receipt. Watermarks are rejected: out-of-order commits block them. A per-device Merkle log (C2SP tlog-checkpoint/tiles) is deferred to v2 "re-verified". | Medium |
| 5 | Dedup poisoning or verification failure | The homelab rejects and logs an ingest event. The Worker resets the ID to MISSING if it is not committed and flags the uploading device (D3/D4). Waiting holders see MISSING on their next re-check, or their valve fires, and they upload. A false commit is impossible because the homelab recomputes SHA-256 and HMAC. | High (mechanism); Medium (Worker details) |
| 6 | Reconciliation, cursor, idempotent ack, outage > retention, Queues pull | Full listing of the drained prefixes needs no cursor. D1 events (rejections, revocations) use a monotonic `event_seq` cursor. The ack follows a durable inbox write. An outage longer than retention loses only hints. The pull consumer is kept as an optional latency hint. It runs on the `api.cloudflare.com` 1,200/5 min limit, whose 429 lockout lasts 5 minutes. | High |
| 7 | Durable-commit contract (interface to A6) | `put_blob(sha256, bytes)` returns only after durable storage (fsync file → rename → fsync dir, the rest-server pattern). Then `archive_record`, the catalog transaction, the receipt, publishing to the Worker, and finally deleting staging. Every step is idempotent on (dedup ID, record ID). | High (pattern); Medium (A6 engine fit) |
| 8 | Metadata-only events (renames, tombstones, sightings, batching) | Same signed-record envelope and the same `meta/` path. Records travel in record batches, one object holding N individually signed records. Each gets its own receipt entry. A rename is a new sighting (a dedup hit on committed content, so an immediate receipt) plus a tombstone. The format belongs to A2/B5. | Medium |
| 9 | Clocks, sequence numbers, where BUD-TTS is measured | TTLs use Worker time. `committed_at` uses homelab time. Device time is recorded but never used for decisions. Order comes from `device_seq`, allocated when the record is sealed (at send), not at pass 1, so a gap really means a missing record. BUD-TTS is measured on the device with a monotonic clock, from `first_seen` to receipt verification, and decomposed with server timestamps. | Medium |
| 10 | Mixed transports (USB and R2) | A record has one `record_id` whatever the transport. The homelab commits a record once and returns the *same stored receipt* on every later arrival. A different `meta_sha256` under the same `record_id` is rejected and flagged. "On USB" is a client state and never safe. If no receipt arrives within a window, the item falls back to R2. | Medium-high |
| 11 | (new) What if D1 is rolled back (Time Travel) or wiped? | Tolerated by design. Committed marks and receipt relays are rebuilt from the homelab. Lost leases only cause parallel uploads. Devices may re-upload (cost, not loss). | Medium-high |
| 12 | (new) Does a presigned PUT allow overwrite? | Yes, within its lifetime: URLs are reusable until expiry, and R2 is last-writer-wins. The damage is bounded by per-upload keys, BUD-REVOKE expiries and homelab verification. The worst case is a forced rejection (DoS), not corruption. | Medium |
| 13 | (new) Is the PLAN's Immich citation accurate? | Partly. #31622 exists, but the bug is "any *reject* treated as a duplicate and deleted", and it was not reproduced against a stock server. PLAN's wording should be corrected (H1). | High |

## Method

- **Sweep:** three scouts ran (docs, source, issues/community). Their findings are the input to this note.
- **Deep read:** the analyst re-fetched and read the load-bearing Cloudflare primary sources on 2026-09-29 from the docs' own source repo (`cloudflare/cloudflare-docs @ production`):
  - read in full: Queues pull consumers, limits, delivery guarantees; R2 consistency; R2 object lifecycles; the rate-limit partial;
  - read in the relevant sections: configure-queues, DLQ, R2 event notifications, R2 S3 API table, Workers R2 API, presigned URLs, D1 batch, D1 limits, D1 Time Travel, DO alarms.
- **Similar-work sources checked at the key line:** Ente `object_cleanup.go`, restic rest-server `repo.go`, restic `design.rst`, the Duplicacy wiki, the tus spec, Dropbox `files.stone`, C2SP tlog-checkpoint and tlog-tiles, and Immich #31622 (re-read via WebFetch).
- **Project inputs:** CLAUDE.md, ADR-0001, the CE spike (`content-encryption-format.md`), `data-model.md`, `glossary.md`, `fact-check-adr-0001-0002.md`, `budgets.md`.
- **Routes used:** raw.githubusercontent.com (vendor doc and source mirrors), registry.npmjs.org, crates.io API, WebFetch (github.com issue page).
- **Blocked sources** (none silently replaced; to report to H1):
  - developers.cloudflare.com (mirror used: the docs' own source, same content);
  - blog.cloudflare.com post-mortems (2025-02-06, 2025-03-21) and cloudflarestatus.com (2026-08-07). The R2-incident claims below are **secondary only**.
  - community.cloudflare.com;
  - developers.google.com (Google Photos guide; the discovery document was used for the facts it states);
  - backblaze.com;
  - rfc-editor.org / datatracker (RFC 9162, Idempotency-Key draft);
  - docs.stripe.com, docs.aws.amazon.com (S3 conditional writes), c2sp.org (editor's copies used), lamport.azurewebsites.net, git.sigsum.org / sigsum.org;
  - GitHub MCP for immich-app/immich (not in the session allowlist; the issue was read via WebFetch instead);
  - GitHub API (commit dates of the Cloudflare docs files were not retrieved; each is cited as "production branch head, fetched 2026-09-29").
- **Stop rule:** the analyst's re-reads added no new primary source that changed a recommendation. Two contradictions inside primary sources were found and are recorded (C5, C13).

## Sources

| # | Source (title and URL or mirror path) | Publisher | Published or version date | Accessed | Primary? |
|---|---|---|---|---|---|
| S1 | `CLAUDE.md`, ADR-0001 `docs/adr/0001-cloud-staging-on-r2.md` | Project | 2026-09-29 (ADR Accepted) | 2026-09-29 | Yes (settled text) |
| S2 | CE spike, `docs/research/content-encryption-format.md` §§4, 8, 9, 10, 11, 12 | Project (T1 spike 2) | 2026-09-29 | 2026-09-29 | Yes (project spike) |
| S3 | `docs/design/data-model.md`, `docs/design/glossary.md` | Project (H4) | v0, 2026-09-29 | 2026-09-29 | Yes (project) |
| S4 | Queues: Pull consumers, `cloudflare/cloudflare-docs @ production : src/content/docs/queues/configuration/pull-consumers.mdx` (= developers.cloudflare.com/queues/configuration/pull-consumers/) | Cloudflare | production head (commit date not retrieved) | 2026-09-29 (read in full) | Yes |
| S5 | Queues: Limits, `… : docs/queues/platform/limits.mdx` | Cloudflare | production head | 2026-09-29 (read in full) | Yes |
| S6 | Queues: Configure queues, `… : docs/queues/configuration/configure-queues.mdx` | Cloudflare | production head | 2026-09-29 | Yes |
| S7 | Queues: Delivery guarantees, `… : docs/queues/reference/delivery-guarantees.mdx` | Cloudflare | production head | 2026-09-29 (read in full) | Yes |
| S8 | Queues: Dead letter queues, `… : docs/queues/configuration/dead-letter-queues.mdx` | Cloudflare | production head | 2026-09-29 | Yes |
| S9 | Cloudflare API rate limits, `… : src/content/partials/fundamentals/api-rate-limits.mdx` (rendered into /fundamentals/api/reference/limits/) | Cloudflare | production head | 2026-09-29 (read in full) | Yes |
| S10 | R2: Event notifications, `… : docs/r2/buckets/event-notifications.mdx` | Cloudflare | production head | 2026-09-29 | Yes |
| S11 | R2: Consistency model, `… : docs/r2/reference/consistency.mdx` | Cloudflare | production head | 2026-09-29 (read in full) | Yes |
| S12 | R2: Object lifecycles, `… : docs/r2/buckets/object-lifecycles.mdx` | Cloudflare | production head | 2026-09-29 (read in full) | Yes |
| S13 | R2: S3 API compatibility, `… : docs/r2/api/s3/api.mdx` (PutObject, UploadPart, CompleteMultipartUpload, ListParts, ListMultipartUploads rows; UploadPart note) | Cloudflare | production head | 2026-09-29 | Yes |
| S14 | R2: Workers API reference, `… : docs/r2/api/workers/workers-api-reference.mdx` (resumeMultipartUpload, R2MultipartUpload, onlyIf) | Cloudflare | production head | 2026-09-29 | Yes |
| S15 | R2: Presigned URLs, `… : docs/r2/api/s3/presigned-urls.mdx` | Cloudflare | production head | 2026-09-29 | Yes |
| S16 | D1: Database Worker API (`batch()`), `… : docs/d1/worker-api/d1-database.mdx` | Cloudflare | production head | 2026-09-29 | Yes |
| S17 | D1: Limits, `… : docs/d1/platform/limits.mdx` | Cloudflare | production head | 2026-09-29 | Yes |
| S18 | D1: Time Travel, `… : docs/d1/reference/time-travel.mdx` | Cloudflare | production head | 2026-09-29 | Yes |
| S19 | Durable Objects: Alarms, `… : docs/durable-objects/api/alarms.mdx` | Cloudflare | production head | 2026-09-29 | Yes |
| S20 | Queues: Local development, `… : docs/queues/configuration/local-development.mdx` | Cloudflare | production head | 2026-09-29 (scout) | Yes |
| S21 | Ente museum `server/pkg/controller/object_cleanup.go`, `file.go`, `ente-io/ente @ main` | Ente | main head | 2026-09-29 | Yes |
| S22 | restic rest-server `repo/repo.go`, `restic/rest-server @ master` | restic | master head | 2026-09-29 | Yes |
| S23 | restic design, `restic/restic @ master : doc/design.rst` (locks, ordering) | restic | master head | 2026-09-29 | Yes |
| S24 | Duplicacy wiki "Lock-Free Deduplication", `raw.githubusercontent.com/wiki/gilbertchen/duplicacy/Lock-Free-Deduplication.md` | Duplicacy | wiki head | 2026-09-29 | Yes |
| S25 | tus resumable upload protocol, `tus/tus-resumable-upload-protocol @ main : protocol.md` | tus | 1.0.x, main head | 2026-09-29 | Yes |
| S26 | Dropbox API spec, `dropbox/dropbox-api-spec @ master : files.stone` (upload_session routes) | Dropbox | master head | 2026-09-29 | Yes |
| S27 | Google Photos Library API discovery document, `photoslibrary.googleapis.com/$discovery/rest?version=v1` | Google | revision 20260928 | 2026-09-29 (scout) | Yes (only for what it states) |
| S28 | Immich `server/src/services/asset-media.service.ts`, `immich-app/immich @ main` | Immich | main head | 2026-09-29 (scout) | Yes |
| S29 | Immich issue #31622 "`--delete-duplicates` can unlink a file the server has never confirmed as a duplicate", github.com/immich-app/immich/issues/31622 | Immich (reporter) | opened 2026-09-17, open | 2026-09-29 (WebFetch re-read) | Primary for what the issue says; the defect is unconfirmed by maintainers |
| S30 | Immich #22024 (spotty Wi-Fi: "already exists" forever), #29543 (re-upload loop; hash of different bytes) | Immich users | 2025-09-15; 2026-07-03 | 2026-09-29 (scout) | No (user reports) |
| S31 | restic rest-server #196 (retry fails in append-only mode), #175 (no-verify-upload nullifies append-only) | restic users/maintainers | 2022-09-10; 2021-11-15 | 2026-09-29 (scout) | No |
| S32 | Duplicacy #335 (backup reports 0 new chunks, check finds chunks missing) | Duplicacy users | 2018-01-24 | 2026-09-29 (scout) | No |
| S33 | C2SP tlog-checkpoint, tlog-tiles, signed-note, tlog-cosignature (editor's copies), `C2SP/C2SP @ main` | C2SP | editor's copies, main head | 2026-09-29 | Yes (stable copies at c2sp.org were blocked) |
| S34 | Tessera README, `transparency-dev/tessera @ main` | transparency-dev | main head | 2026-09-29 (scout) | Yes |
| S35 | TLA+ Examples `specifications/transaction_commit/TwoPhase.tla`, `tlaplus/Examples @ master` | L. Lamport | master head | 2026-09-29 (scout) | Yes |
| S36 | Stateright 0.31.0 crate (`src/actor/model.rs`, `network.rs`), static.crates.io; crates.io API | Stateright | 0.31.0, 2025-07-27 | 2026-09-29 | Yes |
| S37 | npm registry: `@informalsystems/quint` 0.33.0 (Apache 2.0), `wrangler` 4.143.0 (MIT OR Apache-2.0) | Informal Systems; Cloudflare | 2026-09-28 | 2026-09-29 | Yes |
| S38 | crates.io API: `ed25519-dalek` 3.0.0 (BSD-3-Clause, 2026-07-06), `rs_merkle` 1.5.0 (Apache-2.0/MIT, 2025-02-24) | crates.io | as stated | 2026-09-29 | Yes |
| S39 | R2 incidents: BleepingComputer on 2025-02-06 and 2025-03-21; IsDown/Pulsetic on 2026-08-07 (ENAM multipart objects temporarily unavailable) | Secondary press and aggregators | 2025-02, 2025-03, 2026-08 | 2026-09-29 (scout; search snippets for 2026-08) | **No** (primary post-mortems blocked) |
| S40 | Cloudflare Community "Queues HTTP Pull Consumer: max_retries: 0 causes messages to be dropped after ~60 s" | Community forum | 2026-03 (per snippet) | 2026-09-29 (search snippet only) | No |

## Claims

Skeptic columns are empty until Stage 4. "Key?" follows PLAN §5.1.

| # | Claim | Sources | Key? | Skeptic 1 (sources) | Skeptic 2 (logic) | Skeptic 3 (adversary/cost/user) | Verdict |
|---|---|---|---|---|---|---|---|
| C1 | Queues delivers at least once ("in rare occasions, may be delivered more than once"). Cloudflare recommends a producer-generated unique ID used as a primary key or idempotency key. | S7 | Yes | | | | Pending |
| C2 | Queue retention is configurable up to 14 days, and fixed at 24 h on Workers Free. Messages that reach retention are deleted. | S5 | Yes | | | | Pending |
| C3 | The **default** retention (`message-retention-period-secs`) is 345,600 s (4 days), so 14 days holds only if it is set explicitly. | S6 | Yes | | | | Pending |
| C4 | A pulled message whose `attempts` reaches `max_retries` "will not be re-delivered and will be deleted from the queue permanently". `max_retries` defaults to 3 (max 100). Without a DLQ, repeatedly failing messages are discarded. A DLQ with no consumer keeps messages 4 days. | S4, S6, S8, S5 | Yes | | | | Pending |
| C5 | Late acks are accepted: "if a consumer acknowledges a message by its lease ID *after* the visibility timeout … Queues will still accept that acknowledgment", and another consumer that received it meanwhile can ack it too. **The same page also says "A `lease_id` is no longer valid once this timeout has been reached"**, which contradicts it. Either way, a lease is not exclusive ownership. | S4 | Yes | | | | Pending (contradiction inside the primary source) |
| C6 | Pull uses short polling: an empty response when nothing is queued, no long polling. Defaults: batch 5 (max 100), visibility timeout 30 s (max 12 h). The message `id` is "a unique, read-only ephemeral identifier". The token needs queues read + write. | S4 | Yes | | | | Pending |
| C7 | The Cloudflare client API is limited to 1,200 requests per 5 minutes "per user/account token" and 200/s per IP. The note says the global limit applies per user "cumulatively regardless of" dashboard, key or token. Going over it blocks **all** API calls for 5 minutes with 429. | S9 | Yes | | | | Pending (whether an account-owned token gets its own bucket is ambiguous → T2/C1) |
| C8 | Per-queue backlog is capped at 25 GB, after which `send()` fails with Storage Limit Exceeded. Message size is ≤ 128 KB. | S5 | No | | | | Pending |
| C9 | R2 event notifications: `object-create` fires on PutObject, CopyObject and CompleteMultipartUpload; `object-delete` on DeleteObject and LifecycleDeletion. Up to 100 rules per bucket, with no overlapping rules. The page makes no delivery or ordering statement of its own. | S10 | No | | | | Pending |
| C10 | R2 is strongly consistent for read-after-write, deletes and listing ("will list all objects at that point in time"). Two writers to one key: last writer to complete wins. The same part uploaded by several writers: last write wins. | S11 | Yes | | | | Pending |
| C11 | R2's S3 table lists If-Match/If-None-Match/If-(Un)Modified-Since for PutObject. The CompleteMultipartUpload row lists **no** conditional operations. The Workers `put()` binding supports `onlyIf`, and a failed precondition returns `null` and stores nothing. | S13, S14 | Yes | | | | Pending (behaviour of If-None-Match on presigned PUT and on Complete is a C1-S1/A3-S3 test) |
| C12 | "Uploading to the same part number replaces the previous part. If a subsequent upload to the same part fails, the original part is lost and must be re-uploaded." | S13 | Yes | | | | Pending |
| C13 | Buckets have a default lifecycle rule that expires multipart uploads 7 days after **initiation**. The Workers API states that uncompleted uploads auto-abort after 7 days. Prefix rules with `AbortIncompleteMultipartUpload.DaysAfterInitiation` exist; the docs' example comment says a prefix rule "take[s] precedence … due to its earlier expiration". **Whether any rule can extend beyond 7 days is not documented.** | S12, S14 | Yes | | | | Pending (extension untested → A3-S3) |
| C14 | Lifecycle deletions are approximate: "typically removed … within 24 hours" of expiry, and old rules may linger after a change. | S12 | Yes | | | | Pending |
| C15 | `resumeMultipartUpload` does not check that the uploadId is valid or exists, and "a multipart upload can be completed or aborted at any time … by a parallel invocation of your Worker". | S14 | Yes | | | | Pending |
| C16 | Presigned URLs last 1 s to 7 days, support GET/PUT/HEAD/DELETE (POST forms not supported), "can be reused multiple times until it expires", and bind resource, operation and expiry (and Content-Type if specified). R2 also offers scoped *temporary credentials* for multi-operation sessions. | S15 | Yes | | | | Pending |
| C17 | Inference from C16: the Create and Complete multipart operations are S3 POSTs, so the client cannot run them from presigned URLs. They go through the Worker (binding or S3 API), which makes the Worker the natural place for the `staged` transition. | S15 (+ S3 API semantics) | Yes | | | | Pending (inference; C1-S1 to confirm presigned POST is impossible on R2) |
| C18 | D1 `batch()` runs statements "sequentially, non-concurrently" as one SQL transaction, and a failing statement aborts or rolls back the whole sequence. The 30 s limit applies to the whole batch. | S16, S17 | Yes | | | | Pending |
| C19 | D1 Time Travel restores to any minute in the last 30 days (7 days on Free), at most 10 restores per 10 minutes. Inference: cloud claim/commit state can be rewound by an operator. | S17, S18 | Yes | | | | Pending |
| C20 | DO alarms run at least once and are retried with backoff from 2 s, up to 6 retries, for the latest `setAlarm()` only. The docs advise catching errors and rescheduling. | S19 | No | | | | Pending |
| C21 | Ente's cleanup refuses to delete an expired temp object that has a committed DB row. For multipart it aborts the upload before deleting, and on failure it pushes the expiry out instead of retrying tightly. | S21 | No | | | | Pending |
| C22 | restic rest-server writes blobs with O_EXCL temp → fsync → rename → dir fsync before replying, returns 403 for an existing blob, forbids deletes in append-only mode (except locks), and does not remove a file after a failed dir fsync because of "race conditions with parallel upload retries". | S22 | Yes | | | | Pending |
| C23 | restic rest-server #196: in append-only mode, a retry of an upload that succeeded but whose response was lost fails. Immich #22024: a commit whose response was lost left the client retrying forever against a unique constraint. Lost acks must be answered idempotently. | S31, S30 | Yes | | | | Pending (secondary: user reports) |
| C24 | Duplicacy's lock-free dedup has an "exists vs being deleted" race, fixed by two-step fossil collection. Duplicacy #335 shows "0 new chunks" followed by missing chunks. "Exists" is not "safe". | S24, S32 | No | | | | Pending |
| C25 | Immich #31622 (opened 2026-09-17, open): the CLI treats **every** `reject` from bulk-upload-check as a duplicate, including reason `unsupported-format`, and may unlink the local file. The reporter could not reproduce data loss against a stock server. The proposed fix requires `reason === duplicate` plus an `assetId`. | S29 | Yes (citation check) | | | | Pending |
| C26 | Dropbox upload sessions last 48 h, cap files at 350 GB and requests at 150 MB. The spec says `incorrect_offset` "may occur when a previous request was received and processed successfully but the client did not receive the response". | S26 | No | | | | Pending |
| C27 | tus: a PATCH with an `Upload-Offset` different from the server's gets 409 and changes nothing. The expiration extension MAY remove unfinished uploads after `Upload-Expires`. | S25 | No | | | | Pending |
| C28 | A C2SP checkpoint is a signed note with at least three lines (origin, tree size, base64 root hash). tlog-tiles uses 256-hash (8,192-byte) full tiles with SHA-256 RFC 6962 hashing. | S33 | No | | | | Pending |
| C29 | R2 had a 59-min full outage (2025-02-06), a 67-min outage in which 100% of writes failed (2025-03-21), and on 2026-08-07 some ENAM multipart objects were temporarily unavailable. | S39 | Yes (motivates "staged ≠ safe") | | | | **Secondary only** |
| C30 | Stateright 0.31.0 (MIT) models lossy and duplicating networks, crash/recover and timers. Quint 0.33.0 (Apache 2.0) was published 2026-09-28. TLC needs Java 11+ (this container has Java 21). | S36, S37 | No | | | | Pending |

## Findings

### F1. State model (v0)

**Actors:** device D, Worker + D1 (W), R2, queue Q, homelab H. **Keys:** `upload_id` (Worker-made UUIDv4 per upload attempt), `record_id` (device-made UUIDv4, one per signed record), `dedup_id` (A1). **Idempotency key for ingest:** (dedup_id, record_id), as PLAN states. **Receipt identity:** (device_id, record_id), bound to `meta_sha256`.

**Cloud, per upload** (D1 row; C1 owns the schema):

| State | Entered by | Leaves to | Notes |
|---|---|---|---|
| `claimed` (lease: device, upload_id, UploadId, staging key, lease_expires_at in Worker time) | Worker `begin` on MISSING (idempotent on (device_id, record_id)) | `staged`, `abandoned` | The lease is renewed whenever the Worker presigns another part. It is advisory (F2). |
| `staged` | Worker `complete` (Worker runs CompleteMultipartUpload, or verifies a single PUT by HEAD and size) | `committed`, `rejected`, `duplicate-dropped` | Idempotent. A repeat `complete` returns `staged` (covers a crash after Complete, CE §8.5). |
| `committed` | Homelab publish (receipt + commit mark) | — | Terminal. |
| `rejected` (code) | Homelab publish | — | The Worker resets the dedup ID to `absent` unless another upload has already committed it, and flags the device. |
| `duplicate-dropped` | Homelab publish (another copy committed first) | — | Terminal. The staging object is deleted by the homelab. |
| `abandoned` | Lease expired with no progress, or R2 NoSuchUpload (7-day abort) | — | Parts are left for the R2 abort rule. The device restarts with a new upload. |

**Cloud, per dedup ID** (a projection over uploads plus homelab commit marks): `absent` → `in-flight` (any live lease) → `committed`. D1 holds this as a cache. It is rebuildable from the homelab (data-model §7.1).

**Homelab, per record** (system of record): `received` → `verifying` → `committed` (receipt signed) | `awaiting-commit` (dedup-hit record whose blob is not committed yet) | `rejected` (code). **Per blob:** `absent` → `committed` (durable) → later `pruned` (admin only).

**Client, per resource** (B6 owns the DB; E3 owns the words):

| # | State | Meaning | Exits |
|---|---|---|---|
| 1 | discovered | Source enumerated, not yet hashed | 2, excluded |
| 2 | hashed | Pass 1 done (SHA-256, dedup ID, stat snapshot); record body built | 3 |
| 3 | dedup-checked | Worker answered MISSING / IN_FLIGHT / COMMITTED | 4 or 6 |
| 4 | uploading | Holds `upload_id` and lease; parts in flight; journal per CE §8 | 5, restart (2), abandoned → 2 |
| 5 | staged | Worker confirmed `staged` | 6 |
| 6 | record sent / awaiting commit | Signed record (with `device_seq`) accepted by the Worker; no receipt yet | 7, valve → 4, rejected → 4 |
| 7 | committed | A receipt entry for this record verified against the pinned trust bundle (CE §10) | 8 |
| 8 | re-verified | A later homelab statement confirms the record is still present (v2, F4) | — |

Side states: `on USB, in transit` (record and object in a sealed bundle; never safe); `cloud-only` (source not local, e.g. an optimised photo library); `excluded` (by discovery policy or person); `failed(reason)` with reasons `source-changed` (auto-restart), `source-unreadable`, `permission-lost`, `rejected-by-home`, `too-large-for-link` (7-day abort repeats); and **`gone-before-safe`**: the source vanished while the item was not yet committed. This is the one client state that means possible data loss, and it must raise a nudge to the admin (E3).

### F2. Concurrency: advisory lease + per-upload keys (recommended)

- **Why not an exclusive claim with TTL (ADR-0001 §4 sketch):**
  - C10 makes a shared staging key unsafe: last writer wins, including per part.
  - C11 gives no create-only guard for multipart completion.
  - An exclusive claim adds a liveness dependency on the slowest holder: a phone on mobile data can hold a claim for days, and a compromised device can squat claims (glossary "claim squatting").
  - restic's own locks use a 30-minute stale rule plus re-check (S23), which shows that exclusive leases need a takeover protocol anyway.
- **Why not purely optimistic:** family libraries overlap heavily during seeding (shared WhatsApp media, shared event photos), so concurrent duplicate uploads waste phone data and R2 operations. The overlap rate is unmeasured (E1 census).
- **Recommendation:**
  - The Worker records a lease and answers a second device `IN_FLIGHT`.
  - That device sends its record as a dedup hit (content object `null`) and re-checks after a back-off.
  - When the lease has lapsed, or its own **safety valve** fires, it uploads in parallel under its own key.
  - Safety never depends on the lease. Only efficiency does.
  - Proposed valve: 24 h awaiting commit, aligned with BUD-TTS; the owner is to confirm in DR-A3-3.
- **Takeover when the claimant disappears mid-multipart:** there is no hand-over of the UploadId. The key is per device, and the in-flight payload key is sealed on the claimant's device (CE §8.1), so another device *cannot* continue it. The abandoned parts expire under the R2 abort rule, and the other device starts its own upload.
- **The 7-day auto-abort vs a slow phone:** C13 says the window counts from initiation and extension is undocumented. Options:
  1. **Segment checkpoint** (recommended, to be spiked in A3-S3):
     - Before about day 6, the Worker completes the upload with the contiguous finished parts 1..k as a *segment object* `staging/<dedup_id>/<upload_id>/s0`. Equal part sizes still hold.
     - It starts a new multipart upload for the remainder, `…/s1`, and the device continues at ciphertext offset k·P. CE parts are byte-reproducible from the sealed payload key, so no re-encryption is needed.
     - The homelab concatenates the segments, which it already does for USB part files (CE §11).
     - Costs: a Worker cron or DO alarm (C20: retries must be rescheduled defensively), and a segment list in D1.
  2. Restart from scratch: simple, but an upload that always needs more than 7 days never finishes.
  3. Past a size or ETA threshold, direct the file to USB ("too-large-for-link").

  Keep option 3 as the fallback in any case.
- **Resume rule** (C12, C15): never re-send a part whose ETag is journaled. Treat NoSuchUpload as a normal state: ask the Worker for the upload's state before restarting (CE §8.5).

### F3. "Already have it" and poisoning

- **Typed answers only** (lesson of C25). `COMMITTED` carries a committed receipt for (dedup_id, size) that the device verifies in content-only mode (CE §10). An untyped, unknown or unverifiable answer is treated as MISSING-later.
- **The device always sends its own record**, and is safe only with its own receipt entry (C24: "exists" ≠ "safe").
- **Dedup poisoning:**
  - The homelab recomputes SHA-256 and the HMAC (CE §11), so a false commit is impossible.
  - Rejection publishes `rejected(code)`. The Worker resets the ID to `absent` and flags the device for D3/D4.
  - Waiting devices see MISSING on their next re-check, or their valve fires. This implements "ask other holders to upload" without the Worker needing to push to devices.
- **A compromised or rolled-back Worker** (C19) can *delay* but not *suppress*: every device has its valve and needs a homelab signature to reach "safe".

### F4. Receipts

| Option | Offline-verifiable | Device storage | Handles out-of-order commits | Detects homelab omission later | Complexity |
|---|---|---|---|---|---|
| Per-file receipt (CE §10) | Yes | ~250 B per record (CE JSON; estimate, not measured) | Yes | No | Low (prototyped) |
| **Per-device batch receipt (recommended v1)** | Yes (keep the batch bytes) | Less per record (one signature per batch) | Yes | No | Low |
| Watermark ("all seq ≤ N committed") | Yes | Constant | **No**: one stuck 20 GB video blocks it | Partly | Low |
| Per-device Merkle log + C2SP checkpoint (tiles possibly served from R2) | Yes, with inclusion proofs | Constant + proofs | Yes | **Yes** (consistency proofs) | High (Tessera is Go; rs_merkle is a building block, C28, S34, S38) |

- **v1:** batch receipts.
  - Each entry binds (record_id, meta_sha256, dedup_id, size, committed_at). The signature is Ed25519 with a key_id from the pinned trust bundle.
  - Use a versioned envelope. Consider the C2SP signed-note envelope, which gives key IDs and room for later cosignatures (Worker or witness). A2/A3 decide this in the spec.
- **Relay:** the homelab keeps every receipt forever. The Worker's relay table is a cache keyed by (device_id, record_id) with a per-device fetch cursor, so a lost or rolled-back relay is republished from home.
- **v2 "re-verified":** a per-device log whose signed checkpoint lets a device check its receipt set against the homelab after a catalog rebuild (A6-S4). This is deferred, but the receipt `type` and `v` fields keep the door open (one-way door #5).
- **USB:** receipt batches go back on the stick (A4).

### F5. Reconciliation first; queue as hint

- **Source of truth for "staged":** a full listing of `meta/` and `staging/`.
  - Both prefixes drain after commit, so a full listing stays small at steady state.
  - It is strongly consistent (C10).
  - It needs no cursor.
- **Cursor:** D1 carries a monotonic `event_seq` for events that are not objects (rejections resolved, revocations, lease resets). The homelab stores the last `event_seq` it has processed.
- **When the homelab reconciles:**
  - on start;
  - every T (proposal: hourly; no measurement);
  - after an empty pull streak.
- **Queue:**
  - The hint source is an R2 event notification on the `meta/` prefix. It fires however the record was written (C9).
  - Alternatively, the Worker produces the message after accepting a record.
  - The homelab acks each message once it has written the hint to its own durable inbox. Retries and `max_retries` deletion (C4) then never matter, and neither does the ambiguous late-ack rule (C5).
  - Duplicate hints are deduplicated by record key (C1, C6: the message `id` is ephemeral).
- **Outage > retention:**
  - Messages expire (C2); the default retention is only 4 days (C3); the backlog cap is 25 GB (C8). None of these loses data, because staged objects have **no lifecycle expiration** (F7) and reconciliation finds them.
  - Set retention to 14 days anyway (C1 config) to keep latency low after short outages.
  - On Workers Free, 24 h retention (C2) and 7-day D1 Time Travel (C19) also leave safety intact.
- **Pull consumer evaluation:** useful only for latency.
  - Budget: 1,200 requests/5 min (≈ 4/s) shared per user, with a 5-minute 429 lockout (C7).
  - A seed of 1M records at batch 100 with grouped acks needs about 20,000 calls, roughly 1.4 h at the full limit. That is arithmetic, not a measurement.
  - Poll idle at a modest cadence, use a dedicated account-owned token, and never let the puller share a user with the owner's automation.
  - Reconciliation uses only the R2 S3 API and the Worker, so an `api.cloudflare.com` lockout degrades latency only.
  - Alternative for C1: the homelab holds an outbound WebSocket or long-poll to a Durable Object. That avoids `api.cloudflare.com`, but it would replace the queue ADR-0001 §1 names, so it touches settled text.

### F6. Durable-commit contract (interface for A6)

The ingest sequence is idempotent on (dedup_id, record_id). Each step is a no-op if it is already done.

1. Fetch the record. Verify the signature, device and fields (CE §11).
2. If a content object exists: fetch it (or its segments). On NoSuchKey, **retry later and alert; never reject** (C29: R2 can briefly lose multipart objects). Decrypt to temp, verify size, SHA-256 and HMAC.
3. `put_blob(sha256, bytes)`: durable before return (C22 pattern: O_EXCL temp, fsync, rename, dir fsync). An existing blob with equal content is a success, not an error (C23, rest-server #196).
4. `archive_record(record_id, raw bytes)`: durable. Same `record_id` with a different `meta_sha256` → reject and flag a clone or bug (H-13).
5. Catalog transaction (sighting, ingest event).
6. Sign the receipt entry (or return the stored one).
7. Publish the commit mark and receipts to the Worker (idempotent upsert); wait for success.
8. **Only then** delete the staging object(s) and the `meta/` object, using homelab credentials. Devices never delete (R-18).

### F7. Staging hygiene

- `staging/` and `meta/` get **only** an AbortIncompleteMultipartUpload rule, never an Expiration rule. Lifecycle deletions are approximate and lag rule changes (C14), and an expiring prefix would break "no staged object deleted before durable commit".
- **Orphans** are completed objects with no record. The homelab alone quarantines and later deletes them, after a long grace (the Ente pattern, C21). Deleting an orphan cannot lose data: the owning device has no receipt, so it still treats the item as unsafe and re-uploads while it has the source.
- **Presigned PUT overwrite window** (C16): per-upload keys plus BUD-REVOKE expiry (≤ 15 min) bound it. Records are small and can go through the Worker with `onlyIf` create-only (C11). Hand to D4.

### F8. Metadata-only events, clocks, BUD-TTS, mixed transports

- **Records:**
  - Sightings, tombstones, scan checkpoints and source records share the signed envelope (data-model §6).
  - A *record batch* object carries N signed records to cut Worker calls and Class A operations. Receipts come back as batch entries.
- **`device_seq`:**
  - Allocate at sealing time, just before a record first leaves the device, not at pass 1. A restarted upload then leaves no gap, and a gap really means a missing record.
  - The CE prototype signs at start. Signing at sealing costs nothing, because the signing key is on the device. A2 to agree.
  - Repeated seq values with different bodies mean a clone or a restored DB (D3).
- **Clocks:**
  - Worker time for leases.
  - Homelab time for `committed_at`.
  - Device times recorded only (data-model §10).
- **BUD-TTS:**
  - Measured on the device from `first_seen` to receipt verification, with a monotonic clock.
  - Reported with the server-side split: claim → staged → record received → committed → relayed → fetched.
  - "Sent" is measured from `first_seen` to Worker `staged` or record acceptance.
- **USB:**
  - The same `record_id` is used on every path. The homelab returns the stored receipt on a second arrival, so each record gets exactly one receipt.
  - The device falls back to R2 after a window with no receipt (proposal: 14 days; A4 to set).

### F9. Protocol state → user-visible state map (E3 owns the words)

| Protocol state(s) | Placeholder word (glossary §8) | Safe? | Nudge / alert |
|---|---|---|---|
| discovered, hashed, dedup-checked | found, waiting | No | Staleness if no progress (E3) |
| uploading; paused (metered, battery, lease wait) | sending / waiting (reason) | No | — |
| staged; record sent; awaiting commit | sent | **Never** | Device: receipts lag > BUD-TTS → "home server hasn't picked up"; admin alert (C7 dead-man) |
| on USB, in transit | on a USB stick | **Never** | Fallback to R2 after the window |
| committed (receipt verified) | stored at home | **Yes (only this)** | — |
| re-verified (v2) | stored at home (checked date) | Yes | — |
| failed: source-changed | waiting | No | Auto-retry |
| failed: rejected-by-home | problem, will resend | No | Admin alert (D4 forensics) |
| failed: source-unreadable, permission-lost | can't read (gap reason) | No | Person nudge |
| failed: too-large-for-link | needs a USB stick | No | Admin nudge |
| cloud-only | not on this device | n/a | E4 policy |
| excluded | (nothing shown to others) | n/a | — |
| **gone-before-safe** | was deleted before it reached home | **Loss risk** | **Admin alert, always** |

### Alternatives compared

| Option | Fit with settled requirements | Pros | Cons | Evidence |
|---|---|---|---|---|
| Exclusive claim with TTL, objects keyed by dedup ID (ADR-0001 §4 sketch) | Needs OD-04 change anyway (C10) | Saves bandwidth; simple mental model | Last-writer-wins on a shared key; no conditional Complete; claim squatting; slow-holder liveness; takeover protocol needed | C10, C11, C15, S23 |
| Optimistic parallel upload, per-upload keys, homelab dedup | Fits (append-only, homelab verifies) | No liveness dependency; simplest safety argument | Wasted bytes on concurrent duplicates | C10, S2 §8.5 |
| **Advisory lease + per-upload keys + safety valve (recommended)** | Fits; touches ADR-0001 §4 wording (OD-04) | Safety of optimistic, most of the efficiency of exclusive; tolerant of D1 loss | Valve timing is a policy knob; more states | F2, F3 |
| Two-phase upload token then batch-create (Google Photos) | Similar to staged → record batch | Per-item results in batch; bytes then commit | Tokens expire in 1 day (secondary); server-trusted | S27 |
| tus in a Worker | Would need the Worker to proxy every byte | Offset resume with 409 on mismatch | Worker CPU and bandwidth for TBs; not S3; R2 multipart already gives resume | C27 |
| One object per segment | Fits | No 7-day problem; simple resume | More objects and ops; manifest needed | A2/A4; F2 option 1 |
| Receipts: per-file / **batch** / watermark / Merkle log / none | "none" conflicts with the PLAN rule "safe only with receipt" | See F4 | See F4 | C28 |
| Notification: **queue hint + reconcile** / reconcile only / DO WebSocket | Queue named by ADR-0001 §1 | Latency; Cloudflare-endorsed | API rate limit; ack semantics loose | C1–C7 |

### Similar work and lessons

| Project or paper | What they do | Borrow or avoid | Source |
|---|---|---|---|
| Ente museum | Registers every presigned URL as a temp object; commit checks the real size by HeadObject; cleanup refuses rows that are committed, aborts multipart then deletes, and backs off | **Borrow** temp-object bookkeeping, server-side size check and the never-delete-committed rule | S21, C21 |
| restic rest-server | Append-only, write-once (403 on existing), durable write sequence | **Borrow** the durable-write sequence; **avoid** 403-on-retry (#196): answer equal content with success | S22, S31, C22, C23 |
| restic design | Ordering invariants (packs → index → snapshot); 30-min stale locks | Borrow ordering invariants for the model | S23 |
| Duplicacy | Lock-free dedup, fossil collection | Lesson: "exists" ≠ "safe"; no deletion races, because staging deletion is homelab-only after commit | S24, S32 |
| Immich | Per-user checksum dedup; CLI treats every reject as a duplicate (#31622); lost-ack loop (#22024); hash-what-you-upload failure (#29543) | **Avoid** untyped rejects and non-idempotent commits; the homelab verifies the declared hash | S28–S30, C25 |
| Dropbox upload sessions | 48 h sessions; `incorrect_offset` designed for lost responses; async batch commit | Borrow "lost response is part of the contract" and async batch commit | S26, C26 |
| Google Photos Library API | Bytes → upload token → batchCreate with per-item status | Borrow per-item results in batch responses | S27 |
| tus | Offset resume with 409 | Not adopted (see Alternatives) | S25 |
| C2SP / Sigsum / Tessera | Signed notes, checkpoints, tile logs, witnesses | Candidate v2 re-verification; signed-note envelope for v1 receipts | S33, S34 |
| AWS formal methods (Newcombe et al.) | TLA+ found subtle bugs in S3 and DynamoDB designs | Supports A3-S1 (not read by the analyst; scout only) | scout |

### Tools and libraries

| Name | Purpose | Licence | Maturity (release date, activity) | Source |
|---|---|---|---|---|
| Stateright | Rust model checker (actor model, lossy/duplicating network, crashes) | MIT | 0.31.0, 2025-07-27 | S36 |
| Quint | TLA-family spec language + simulator | Apache 2.0 | 0.33.0, 2026-09-28 | S37 |
| TLA+ TLC / Apalache | Explicit and symbolic model checking | not checked | TLC needs Java 11+ (container has Java 21); versions not checked | scout |
| P | State-machine modelling language | MIT (scout) | not checked | scout |
| wrangler / Miniflare | Local emulation of Workers, Queues, R2 (whether pull consumers and R2 notifications are emulated is unverified) | MIT OR Apache-2.0 (wrangler) | 4.143.0, 2026-09-28 | S20, S37 |
| ed25519-dalek | Receipt and record signatures | BSD-3-Clause | 3.0.0, 2026-07-06 | S38 |
| rs_merkle | Merkle trees (v2 receipts) | Apache-2.0/MIT | 1.5.0, 2025-02-24 | S38 |
| Tessera | Go tile-log library (v2 option) | not checked | "production ready since v0.2.0" per README | S34 |

## Spikes

Placeholder: a separate spike runner owns these. Results will be filled in from its output. The invariants the model must check are listed below so that the spike and the spec use the same wording.

**Invariants (safety):**
- **I1:** a staged or record object is deleted only after its content and record are durably committed at the homelab, or it is a quarantined orphan past the grace period.
- **I2:** device-visible "safe" ⇒ the device holds a valid receipt entry ⇒ the homelab holds a durable blob and an archived record.
- **I3:** a committed blob for dedup_id *d* has plaintext whose HMAC is *d* (no false merge).
- **I4:** at most one distinct receipt per (device_id, record_id).
- **I5:** no lease, queue or D1 state is needed for I1–I4 (checked by also modelling D1 rollback and queue loss).

**Liveness:**
- **L1:** a device that stays online and keeps its source eventually gets a receipt, if the homelab is eventually up (despite dropped hints, lost leases, D1 rollback, poisoning by another device).
- **L2:** every lease ends committed, released or abandoned.

| Spike | Hypothesis | Pass → / fail → (decision) | Exec tag | Budget IDs | Data class | Status | Result |
|---|---|---|---|---|---|---|---|
| A3-S1 | The F1–F6 protocol satisfies I1–I5 and L1–L2 with 3 devices × 3 items, bounded crashes, dropped or duplicated messages, homelab offline, D1 rollback | Pass → the state table goes into ADR-0009 as is; fail → each counterexample is fixed in the spec and re-checked | CT | — | `SYN → results` | Running (spike runner) | Pending |
| A3-S2 | On the A0 harness (**emulated, not real R2/Cloudflare**): two devices, same 2 GB file, one killed; homelab offline for a simulated 15 days; 5 % of hints dropped | Pass → exactly one blob, both devices receipted, no orphans after reconciliation; fail → fix the reconcile or ack design | CT (emulated) | BUD-TTS (decomposition only) | `SYN → results` | Running (spike runner) | Pending |
| A3-S3 | Real R2: resume after 24 h and after 7 days, the default abort, whether an abort rule can exceed 7 days, the segment checkpoint (F2 option 1), If-None-Match on presigned PUT and on Complete | Pass → segment checkpoint adopted; fail → restart plus the USB fallback | SB (kit; needs L01 sandbox, L30 calendar) | BUD-TMP, BUD-REVOKE | `SYN → results` | Not started (kit to be written) | — |

## Conflicts with settled text

- **ADR-0001 §4 step 2** ("conditional **claim** (`pending` with TTL → `committed`); objects keyed by dedup ID so duplicate uploads are idempotent") conflicts with per-upload staging keys and an advisory lease. This is already tracked as **OD-04**, and CE D-5 recommends the same change. It needs an "Amends: ADR-0001 §4" draft with ADR-0009.
- **ADR-0001 §1** ("Queue messages are retained for at most 14 days") is accurate as a maximum. The default is 4 days (C3), which is a configuration note for C1, not a conflict.
- **ADR-0001 §1** names Queues as the notification path. The DO WebSocket alternative (F5) would touch it, and it is not recommended here.
- **CLAUDE.md** is not contradicted. "Devices can only append, never delete or rewrite" is kept: homelab-only deletion, per-upload keys, and presigned overwrites bounded to the device's own in-flight key within ≤ 15 min (F7). D4 must test the last point.

## Open questions

| # | Question | Who | By when |
|---|---|---|---|
| 1 | Can an R2 AbortIncompleteMultipartUpload rule exceed 7 days? Does a longer prefix rule override the default? | A3-S3 / C1-S1 (SB) | Gate B |
| 2 | Does R2 honour If-None-Match on a *presigned* PUT, and any conditional behaviour on CompleteMultipartUpload? Can POST operations be presigned at all? | C1-S1 | Gate B |
| 3 | Which of the contradictory lease statements (C5) holds in practice? | A3-S2 kit on sandbox; T2 | Wave 2 |
| 4 | Does an account-owned API token get its own 1,200/5 min bucket (C7)? | T2, C1 | Wave 2 |
| 5 | Do Miniflare/`wrangler dev` emulate HTTP pull consumers and R2 event notifications? | Spike runner (A3-S2) | Wave 1 |
| 6 | Valve timing, re-check back-off, reconcile interval, orphan grace, USB fallback window: all proposals, no measurements | A3-S2, E3, owner (DR-A3-3) | Gate A |
| 7 | Receipt envelope: CE JSON-lines vs C2SP signed-note; Rust signed-note implementation availability not checked | A2, A3 spec | Gate A |
| 8 | Late `device_seq` allocation vs CE's sign-at-start | A2 | Gate A |
| 9 | Security requirements (SR-xx) once `docs/security/threat-model.md` exists | D1 | Wave 2 |
| 10 | Primary post-mortems for the R2 incidents (C29 is secondary only) | H1 (blocked source) | Before ADR-0009 cites them |

## Recommendation

Adopt the following for ADR-0009 and `docs/spec/ingest-protocol.md`, and let the owner decide the settled-text parts through OD-04:

- per-upload staging keys and an advisory lease with a device safety valve;
- reconciliation by strongly consistent prefix listing as the primary path, with the queue as a hint acked on durable inbox write;
- typed dedup answers that never mean safe;
- per-device batch receipts over per-record entries;
- the eight-step idempotent durable-commit contract;
- the F9 state map for E3.

**What would change this:**
- A3-S1 counterexamples.
- A3-S3 showing that R2 cannot checkpoint segments, which leaves restart plus USB for very large files.
- E1 showing negligible cross-device overlap, which would drop the lease entirely and go purely optimistic.
- The owner rejecting device-side re-upload after a timeout (DR-A3-3).

## Decision requests

### DR-A3-1 (for OD-04): Amend ADR-0001 §4: per-upload staging keys, advisory lease, homelab-only commit and staging deletion
- **Needed by:** Wave 1 exit (OD-04 sitting 2)
- **Evidence:** this note (F2, F5–F7; C10, C11, C13–C15); CE spike §8.5, D-5
- **Options:**
  | Option | What it means for the family | Cost (money and owner time) | Reversibility | Risks |
  |---|---|---|---|---|
  | A. Keep ADR-0001 §4 wording (exclusive claim, objects keyed by dedup ID) | Same | Same | Costly after the first ingest | Silent overwrite on a shared key (C10); a stuck phone blocks others |
  | B. Per-upload keys + advisory lease + homelab-only deletion (recommended) | Nothing visible; fewer stuck items | Some duplicate uploads during seeding (rate unknown) | Easy before Gate A | More states to test (A3-S1) |
- **Recommendation:** B. It is the only option whose safety does not depend on R2 features the docs do not list (conditional Complete) or on the cloud behaving honestly.
- **Touches settled text:** ADR-0001 §4 step 2 ("Amends: ADR-0001 §4", drafted with ADR-0009)
- **If no decision by the deadline:** the A0 skeleton uses B as a v0 throwaway choice; Gate A stays blocked.

### DR-A3-2: Receipt format for v1 (one-way door #5)
- **Needed by:** Gate A
- **Evidence:** F4; C28; CE §10
- **Options:**
  | Option | What it means for the family | Cost | Reversibility | Risks |
  |---|---|---|---|---|
  | A. Per-file receipts (CE) | "Stored at home" per file | Lowest build cost | One-way once devices hold them | Device storage per record |
  | B. Per-device batch receipts (recommended) | Same | Low | One-way; versioned | Slightly larger parsing surface |
  | C. Per-device Merkle log now | Same, plus detection of homelab omissions | High | One-way | Complexity before the pilot |
- **Recommendation:** B, with `v`/`type` fields reserved so that a v2 log checkpoint can be added for re-verification.
- **Touches settled text:** none
- **If no decision by the deadline:** A (the CE format) is used for v0 only.

### DR-A3-3: Device safety valve: re-upload after a bounded "awaiting commit" wait
- **Needed by:** Gate A (policy; tunable later)
- **Evidence:** F2, F3
- **Options:**
  | Option | What it means for the family | Cost | Reversibility | Risks |
  |---|---|---|---|---|
  | A. Never re-upload when told another device is sending | Lowest phone data | — | Easy | A dead or lying claimant leaves items unsafe indefinitely |
  | B. Re-upload after 24 h awaiting commit (recommended, aligned with BUD-TTS) | Occasional duplicate upload on Wi-Fi | Small R2 operation and byte cost | Easy (a number) | Extra mobile data if not limited to unmetered networks |
  | C. Re-upload after 7 days | Less duplicate traffic | — | Easy | Items stay unsafe for up to a week |
- **Recommendation:** B, applied only on unmetered networks.
- **Touches settled text:** none
- **If no decision by the deadline:** B is used in the prototype.

## Hand-offs

| To | What | Why |
|---|---|---|
| C1 | Worker endpoints `check/begin/presign/complete/record/receipts` (idempotent on (device_id, record_id)); the D1 upload and `event_seq` tables; lifecycle rules (abort only, no expiration on `staging/` and `meta/`); queue retention set to 14 days explicitly; a dedicated puller token; R2 event notification on `meta/` | F1, F5, F7 |
| C1-S1 | Presigned POST impossibility, If-None-Match on presigned PUT and on Complete, UploadPart after Complete | C11, C17 |
| A2 | Late `device_seq` allocation; record-batch object; receipt envelope choice | F8, F4 |
| A4 | Same `record_id` across transports; receipt batches on sticks; fallback window | F8 |
| A6 | The eight-step durable-commit contract; equal-content `put_blob` returns success | F6 |
| D1 / D4 | Presigned overwrite window, claim squatting, compromised or rolled-back Worker, poisoning flows as tabletop and test items | F3, F7 |
| E3 | F9 state map, including the `gone-before-safe` admin alert | R-30 |
| B6 | Client state list and side states for the client DB | F1 |
| H4 | "Claim" is now an advisory lease; add `abandoned`, `duplicate-dropped` and `gone-before-safe` to the glossary | F1 |
| H1 | Correct the PLAN A3 Immich wording (C25); log the blocked sources; tell T2 that the default queue retention is 4 days (C3) and that the lease-validity statement is self-contradictory (C5) | Method |
| T2 | Time-sensitive: account-token rate-limit bucket (C7); R2 abort extension (C13) | Open questions 1, 4 |
