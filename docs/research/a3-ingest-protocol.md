# A3. Ingest protocol, receipts and the client/server state machine

- **Workstream:** A3 (see `docs/research/PLAN.md`, section "A3.")
- **Status:** Final for Wave 1 (batch W1-b). Skeptic review done (sources, logic, adversary); the claim tally below is the computed one. Spike A3-S1 ran (pass for the corrected design **v1**, within stated bounds); A3-S2 is deferred to Wave 2 (needs the A0 harness); A3-S3 is kit-ready (needs the sandbox account).
- **Date:** 2026-09-29 (last updated 2026-10-07)
- **Feeds:** ADR-0009 (Proposed: `docs/adr/0009-ingest-protocol-receipts-reconciliation.md`), `docs/spec/ingest-protocol.md` (Draft), OD-04, one-way door #5 (receipt format), decision requests DR-A3-1 to DR-A3-3 (H1 assigns OD numbers). Inputs to DR-F3-2 (F3) and DR-C1-3 (C1).
- **Depends on:** C1-S1 (real R2 behaviour), D1 threat register `docs/security/threat-model.md` (SR-01…SR-31, updated 2026-10-06), A1 (dedup ID, ADR-0006), A2 (record and object format, `docs/spec/object-format.md`), F3 (DR-F3-2 presence scope), C1 (ADR-0010 API and key layout), A6 (durable-commit contract), A4 (bundles).
- **Traceability rows advanced:** R-11, R-12, R-18, R-27, R-30 (state map), R-40, R-45, C-02, C-03 (see `docs/research/traceability.md`)

## Summary

The recommendation, in one line: **R2 listing is the record of what is staged, the homelab is the record of what is committed, and only a homelab-signed receipt held by the device means "safe". Leases, the notification channel and D1 are optimisations that may be lost, rolled back or lie without losing data.**

1. **The analyst's first design (v0) was wrong in one place, and the model check found it.** In v0 the device sent its record *after* the upload completed, and the homelab garbage-collected completed staging objects that had no record. Both A3-S1 models found the same four-step trace with no fault and no attacker: a slow device's object is deleted just before its record arrives (I7). With the source gone, that is a lost item. **v1 fixes it with "record-first"**: the Worker writes the device's signed record to `meta/` *before* it completes the multipart upload, orphan GC is removed, and a record whose upload is gone gets a typed `content-missing` answer. v1 passed every check that completed (up to 38.6 M states, Rust; 7.9 M states exhaustive all-faults safety, TLC; L1–L4 liveness per fault class).
2. **Every upload has its own staging key; the homelab alone commits and deletes.** The claim is an advisory lease. Its bandwidth value is **unmeasured** (claim K13 is contested) and depends on the owner's presence-scope decision (DR-F3-2) and E1's overlap census, so the safety argument never rests on it.
3. **"Already have it" is a typed, scoped answer that never means safe.** The device still sends its own record and waits for its own receipt. A bounded safety valve with a retry budget ends in a visible nudge, never in silence (SR-06).
4. **Reconciliation by listing is the path of record** (SR-12). Any notification channel is a hint. A3 now **agrees with ADR-0010's recommended homelab-polled Worker feed** over a Queues HTTP pull consumer, because of the 1,200-requests-per-5-minutes API limit and the loose lease semantics (K3, K4). The feed cursor must detect D1 rollback.
5. **Receipts v1 are per-device batch receipts** (one homelab signature over many per-record entries), in the C2SP signed-note envelope A2 already uses for records. A Merkle log is a v2 option.

Confidence: **high** on the Cloudflare facts (K1–K12 verified). **Medium** on the protocol: v1 multipart is model-checked within small bounds, but the single-PUT path, segment checkpoints, the fence rule for `content-missing`, the feed-cursor rollback rule and "hide then reappear" R2 faults are **specified here but not yet model-checked** (Wave 2 extension of A3-S1, before ADR-0009 can be accepted).

## Questions

| # | Question | Short answer | Confidence |
|---|---|---|---|
| 1 | States: server claim/commit machine, client per-file states, side states | Cloud per upload: `claimed → staged → (committed \| duplicate \| rejected \| fenced)`. Per dedup ID the cloud holds only a rebuildable projection. Homelab per record (system of record): `received → awaiting-content → verifying → (committed + receipt \| awaiting-blob \| held \| rejected)`. Client: 8 main states plus side states, including `gone-before-safe`, the only possible-loss state (F1). | Medium |
| 2 | Exclusive claim vs per-upload keys; takeover; 7-day abort | Per-upload keys always (OD-04). Lease is advisory and renewed by progress; never IN_FLIGHT to the lease holder itself (F-B1). Takeover = another device uploads; no UploadId hand-over. 7-day abort: first test whether a longer abort rule is accepted (A3-S3 H3; the docs say the default "can be changed", C31). Baseline until then: restart, then "needs a USB stick". Segment checkpoint is a fallback that needs record-first and a model run (F2). | Medium (design); High (R2 facts) |
| 3 | "Already have it" semantics | Typed `MISSING / IN_FLIGHT / COMMITTED / UNKNOWN`, scoped per DR-F3-2 (per person by default). COMMITTED carries a **device-neutral** homelab-signed content statement, not another device's receipt (M-27). Never safe; the device always sends its own record (SR-05, SR-06). | High (principle); Medium (scope and timing) |
| 4 | Receipts | v1 per-device batch receipt: signed-note, entries bind (device_id, record_id, record_sha256, dedup_id, padded size, committed_at). Watermark rejected (out-of-order commits). Merkle log v2. Relay is a cache; USB carries receipts too (F4). | Medium |
| 5 | Dedup poisoning or verification failure | Homelab keeps nothing; resets only that upload's claim; never downgrades a committed ID; blames a device only if its own signed record matches the rejected object, otherwise logs "tamper in transit" (SR-11(a)–(c)). Waiting holders recover by re-check, a homelab-signed re-upload request (SR-11(d)) or their valve (F3). | High (mechanism); Medium (details) |
| 6 | Reconciliation, cursor, ack, outage > retention, Queues pull | Listing of `meta/` and `staging/` (paginated) is the path of record. Hints come from the Worker feed (ADR-0010, DR-C1-3); the feed cursor is a hash-chained `event_seq` so a D1 rollback forces a resync. If Queues are used, ack once the hint is in the homelab's durable inbox; set retention explicitly (default is 4 days, K1). The pull consumer is not recommended (K4; it cannot be emulated locally, G2-S1). | High |
| 7 | Durable-commit contract (A6 interface) | Eight idempotent steps keyed by (device_id, record_id), with the blob keyed by SHA-256: verify record → fetch and verify object (retry, never reject, unless fenced) → `put_blob` durable → archive record → catalog → sign or return stored receipt → publish → only then delete staging (F6). | High (pattern); Medium (engine fit) |
| 8 | Metadata-only events | Same signed-record envelope and `meta/` path, in record batches; each record gets its own receipt entry. Rename = new sighting (dedup hit) + tombstone. Formats belong to A2/B5. Not model-checked. | Medium |
| 9 | Clocks; where BUD-TTS is measured | Worker time for leases and URL expiry; homelab time for commit and every health decision (SR-19); device time recorded only. `device_seq` allocated at sealing (A2 to agree). BUD-TTS measured on device from `first_seen` to receipt verification (monotonic clock), decomposed with server timestamps. | Medium |
| 10 | Mixed transports | One `record_id` across USB and R2; the homelab commits once and returns the stored receipt on every later arrival; same `record_id` with different bytes is `E_REPLAY_RECORD_ID`. "On USB" is never safe; R2 fallback after a window A4 sets. | Medium-high |
| 11 | (new) D1 Time Travel rollback or wipe | Tolerated for leases, marks and relays (modelled). The feed cursor is **not** rollback-safe as first drafted; fixed by a hash-chained cursor plus resync (F5; not yet modelled). | Medium |
| 12 | (new) Presigned PUT overwrite | Yes within the URL lifetime (K9 inference, untested). Bounded by per-upload keys, ≤ 15 min URLs (BUD-REVOKE) and homelab verification; "append-only" is enforced at commit, not at staging (ADR-0010 DR-C1-6). D4 tests it. | Medium |
| 13 | (new) PLAN's Immich #31622 citation | Inaccurate: the bug is "every *reject* treated as a duplicate and unlinked", not reproduced against a stock server (K12). H1 to correct PLAN. | High |

## Method

- **Sweep:** three scouts (docs, source, issues/community), then an analyst deep read of the load-bearing Cloudflare sources on 2026-09-29 from the docs' source repo (`cloudflare/cloudflare-docs @ production`).
- **Skeptic review (2026-10-07):** three lenses (sources, logic, adversary) re-fetched the primaries. Their verdicts are tallied in code (rule: verified = a primary source and at least 2 of 3 skeptics did not refute; secondary-only = no primary; contested = otherwise). This note uses the tally as computed.
- **Synthesizer checks (2026-10-07):** re-fetched the two primary sources the skeptics raised: `r2/objects/upload-objects.mdx` (abort configurability, C31) and `release-notes/r2.yaml` (2023-08-11 conditional multipart completion, C32). Both quotes match.
- **Project inputs:** CLAUDE.md, ADR-0001/0002 (Accepted), the CE spike, `data-model.md`, `glossary.md`, `docs/security/threat-model.md` (D1, SR-01…SR-31), `docs/spec/object-format.md` (A2), ADR-0010 and `docs/design/api-v1.md` (C1), the F3 note (DR-F3-2, M-27…M-30, M-49), `budgets.md`, `spikes/A3-S1/`, `spikes/G2-S1/README.md`.
- **Routes used:** raw.githubusercontent.com (vendor doc and source mirrors), registry.npmjs.org, crates.io API, WebFetch (github.com issue pages), WebSearch (snippets only, for the R2 incidents).
- **Blocked sources** (none silently replaced; reported to H1):
  - developers.cloudflare.com (the docs' own source repo used instead: same content);
  - blog.cloudflare.com post-mortems (2025-02-06, 2025-03-21), cloudflarestatus.com (2026-08-07), bleepingcomputer.com and isdown.app (blocked for the skeptics on 2026-10-07): the R2 incident claim K14 stays **secondary only**;
  - community.cloudflare.com; developers.google.com; backblaze.com; rfc-editor.org / datatracker; docs.stripe.com; docs.aws.amazon.com; c2sp.org (editor's copies used); lamport.azurewebsites.net; sigsum.org;
  - GitHub API (403 on 2026-09-29 and 2026-10-07): **commit dates of the Cloudflare docs files were not retrieved**; each is cited as "production branch head" with the access date;
  - GitHub MCP for immich-app/immich (issues read via WebFetch instead).
- **Stop rule:** the skeptics' re-reads added two primary sources (C31, C32); both narrow existing claims rather than reverse a recommendation. No further sweep.

## Sources

| # | Source (title and URL or mirror path) | Publisher | Published or version date | Accessed | Primary? |
|---|---|---|---|---|---|
| S1 | `CLAUDE.md`; ADR-0001 `docs/adr/0001-cloud-staging-on-r2.md`; ADR-0002 | Project | Accepted | 2026-10-07 | Yes (settled text) |
| S2 | CE spike, `docs/research/content-encryption-format.md` §§4, 8, 9, 10, 11, 12 | Project (T1 spike 2) | 2026-09-29 | 2026-09-29 | Yes (project spike) |
| S3 | `docs/design/data-model.md`, `docs/design/glossary.md` | Project (H4) | v0 | 2026-09-29 | Yes (project) |
| S4 | Queues: Pull consumers, `cloudflare/cloudflare-docs @ production : src/content/docs/queues/configuration/pull-consumers.mdx` | Cloudflare | production head (commit date not retrieved) | 2026-09-29; 2026-10-07 | Yes |
| S5 | Queues: Limits, `… : docs/queues/platform/limits.mdx` | Cloudflare | production head | 2026-09-29; 2026-10-07 | Yes |
| S6 | Queues: Configure queues, `… : docs/queues/configuration/configure-queues.mdx` | Cloudflare | production head | 2026-09-29; 2026-10-07 | Yes |
| S7 | Queues: Delivery guarantees, `… : docs/queues/reference/delivery-guarantees.mdx` | Cloudflare | production head | 2026-09-29 | Yes |
| S8 | Queues: Dead letter queues, `… : docs/queues/configuration/dead-letter-queues.mdx` | Cloudflare | production head | 2026-09-29; 2026-10-07 | Yes |
| S9 | Cloudflare API rate limits, `… : src/content/partials/fundamentals/api-rate-limits.mdx` | Cloudflare | production head | 2026-09-29; 2026-10-07 | Yes |
| S10 | R2: Event notifications, `… : docs/r2/buckets/event-notifications.mdx` | Cloudflare | production head | 2026-09-29 | Yes |
| S11 | R2: Consistency model, `… : docs/r2/reference/consistency.mdx` | Cloudflare | production head | 2026-09-29; 2026-10-07 | Yes |
| S12 | R2: Object lifecycles, `… : docs/r2/buckets/object-lifecycles.mdx` | Cloudflare | production head | 2026-09-29; 2026-10-07 | Yes |
| S13 | R2: S3 API compatibility, `… : docs/r2/api/s3/api.mdx` | Cloudflare | production head | 2026-09-29; 2026-10-07 | Yes |
| S14 | R2: Workers API reference, `… : docs/r2/api/workers/workers-api-reference.mdx` | Cloudflare | production head | 2026-09-29; 2026-10-07 | Yes |
| S15 | R2: Presigned URLs, `… : docs/r2/api/s3/presigned-urls.mdx` | Cloudflare | production head | 2026-09-29; 2026-10-07 | Yes |
| S16 | D1: Database Worker API (`batch()`), `… : docs/d1/worker-api/d1-database.mdx` | Cloudflare | production head | 2026-09-29 | Yes |
| S17 | D1: Limits, `… : docs/d1/platform/limits.mdx` | Cloudflare | production head | 2026-09-29; 2026-10-07 | Yes |
| S18 | D1: Time Travel, `… : docs/d1/reference/time-travel.mdx` | Cloudflare | production head | 2026-09-29; 2026-10-07 | Yes |
| S19 | Durable Objects: Alarms, `… : docs/durable-objects/api/alarms.mdx` | Cloudflare | production head | 2026-09-29 | Yes |
| S20 | Queues: Local development, `… : docs/queues/configuration/local-development.mdx` | Cloudflare | production head | 2026-09-29 | Yes |
| S21 | Ente museum `server/pkg/controller/object_cleanup.go`, `file.go`, `ente-io/ente @ main` | Ente | main head | 2026-09-29 | Yes |
| S22 | restic rest-server `repo/repo.go`, `restic/rest-server @ master` | restic | master head | 2026-09-29 | Yes |
| S23 | restic design, `restic/restic @ master : doc/design.rst` | restic | master head | 2026-09-29 | Yes |
| S24 | Duplicacy wiki "Lock-Free Deduplication" | Duplicacy | wiki head | 2026-09-29 | Yes |
| S25 | tus protocol, `tus/tus-resumable-upload-protocol @ main : protocol.md` | tus | 1.0.x | 2026-09-29 | Yes |
| S26 | Dropbox API spec, `dropbox/dropbox-api-spec @ master : files.stone` | Dropbox | master head | 2026-09-29; 2026-10-07 | Yes |
| S27 | Google Photos Library API discovery document | Google | revision 20260928 | 2026-09-29 | Yes (only for what it states) |
| S28 | Immich `server/src/services/asset-media.service.ts` | Immich | main head | 2026-09-29 | Yes |
| S29 | Immich issue #31622, github.com/immich-app/immich/issues/31622 | Immich (reporter) | opened 2026-09-17, open | 2026-09-29; 2026-10-07 | Primary for what the issue says |
| S30 | Immich #22024, #29543 | Immich users | 2025-09-15; 2026-07-03 | 2026-09-29; 2026-10-07 | No (user reports) |
| S31 | restic rest-server #196, #175 | restic users/maintainers | 2022-09-10; 2021-11-15 | 2026-09-29; 2026-10-07 | No |
| S32 | Duplicacy #335 | Duplicacy users | 2018-01-24 | 2026-09-29 | No |
| S33 | C2SP tlog-checkpoint, tlog-tiles, signed-note, tlog-cosignature, `C2SP/C2SP @ main` | C2SP | main head | 2026-09-29 | Yes |
| S34 | Tessera README, `transparency-dev/tessera @ main` | transparency-dev | main head | 2026-09-29 | Yes |
| S35 | TLA+ Examples `TwoPhase.tla`, `tlaplus/Examples @ master` | L. Lamport | master head | 2026-09-29 | Yes |
| S36 | Stateright 0.31.0 crate | Stateright | 0.31.0, 2025-07-27 | 2026-09-29 | Yes |
| S37 | npm: `@informalsystems/quint` 0.33.0, `wrangler` 4.143.0 | Informal Systems; Cloudflare | 2026-09-28 | 2026-09-29 | Yes |
| S38 | crates.io: `ed25519-dalek` 3.0.0, `rs_merkle` 1.5.0 | crates.io | 2026-07-06; 2025-02-24 | 2026-09-29 | Yes |
| S39 | R2 incidents: BleepingComputer (2025-02-06, 2025-03-21); IsDown/Pulsetic and search snippets (2026-08-07) | Secondary press, aggregators | 2025-02, 2025-03, 2026-08 | 2026-09-29; 2026-10-07 (snippets) | **No** (primaries blocked) |
| S40 | Cloudflare Community, Queues HTTP pull `max_retries: 0` thread | Community forum | 2026-03 (snippet) | 2026-09-29 (snippet) | No |
| S41 | R2: Upload objects, `… : docs/r2/objects/upload-objects.mdx` §"Incomplete upload lifecycles" (L839–841) | Cloudflare | production head | 2026-10-07 | Yes |
| S42 | R2 release notes, `… : src/content/release-notes/r2.yaml`, entry 2023-08-11 | Cloudflare | 2023-08-11 | 2026-10-07 | Yes |
| S43 | Threat register `docs/security/threat-model.md` (SR-01…SR-31, T-06, T-11, T-22, T-23, AR-06, AR-08, AR-09, Appendix A) | Project (D1) | Draft, updated 2026-10-06 | 2026-10-07 | Yes (project) |
| S44 | `docs/spec/object-format.md` §§7–8 (signed-note records, `record_sha256`, padded sizes, E_* codes) | Project (A2) | Draft | 2026-10-07 | Yes (project) |
| S45 | ADR-0010 (Proposed) and `docs/design/api-v1.md` (feed, key layout, record path, staging guard rails) | Project (C1) | 2026-10-06 | 2026-10-07 | Yes (project) |
| S46 | F3 note `docs/research/f3-security-literature.md` (DR-F3-2, M-27…M-30, M-49, F3-S2) | Project (F3) | Wave 1 | 2026-10-07 | Yes (project) |
| S47 | A3-S1 model check, `spikes/A3-S1/README.md` and `evidence/` | Project (A3 spike runner) | 2026-10-06 | 2026-10-07 | Yes (project spike) |
| S48 | G2-S1, `spikes/G2-S1/README.md` (wrangler refuses `http_pull`; Miniflare has no pull route; 501 for lifecycle APIs) | Project (G2) | Wave 1 | 2026-10-07 | Yes (project spike) |

## Claims

### Key claims (skeptic-reviewed; status as computed)

Rule (PLAN §5.1): **verified** = at least one primary source and at least 2 of 3 skeptics did not refute; **secondary only** = no primary source; **contested** = otherwise. A contested or secondary-only claim is never the sole support of a recommendation.

| # | Claim | Sources | Skeptic 1 (sources) | Skeptic 2 (logic) | Skeptic 3 (adversary) | Status |
|---|---|---|---|---|---|---|
| K1 | Queues default retention is 345,600 s (4 days); 14 days is the configurable maximum on Paid; Free is fixed at 24 h; messages at retention are deleted. | S6, S5 | Upheld | Upheld | Upheld | **Verified** |
| K2 | A pulled message whose attempts reach `max_retries` (default 3, max 100) is deleted permanently, or goes to a DLQ. Hints can be lost by processing failure as well as by retention. | S4, S6 | Upheld | Upheld (the default 3 is documented for consumers generally, inferred for pull) | Upheld (same caveat) | **Verified** |
| K3 | The pull-consumer page both accepts late acks and says "A `lease_id` is no longer valid once this timeout has been reached". A lease is not exclusive ownership after the visibility timeout. | S4 | Upheld | Upheld; reworded: delivery is exclusive *during* the timeout, not after | Upheld | **Verified** |
| K4 | Client API limit 1,200 requests / 5 min per user/account token and 200/s per IP; exceeding it blocks all API calls for 5 min (429). Pull and ack are `api.cloudflare.com` calls. That Queues calls count against the global bucket is an **inference**; whether an account-owned token has its own bucket is ambiguous. | S9, S4 | Upheld | Upheld (inference labelled) | Upheld | **Verified** |
| K5 | R2 is strongly consistent for read-after-write, delete and listing; same key and same part are last-writer-wins. | S11 | Upheld | Upheld; per-upload keys justified by liveness and attribution, not integrity | Upheld | **Verified** |
| K6 | R2's S3 table lists conditional headers for PutObject and none for CompleteMultipartUpload; Workers `put()` with `onlyIf` returns `null` on a failed precondition. | S13, S14 | Upheld | Upheld | Upheld for the literal claim; the inference "no create-only guard on Complete" is **contradicted by C32** | **Verified** (literal claim only; inference withdrawn) |
| K7 | R2 expires incomplete multipart uploads 7 days after **initiation** by default; the docs' example says the earlier-expiring rule takes precedence. | S12, S14 | **Refuted in part**: "extension not documented" is wrong; upload-objects.mdx says the default can be changed (C31) | Upheld | Upheld | **Verified** (core facts; the "not documented" sub-claim is corrected by C31) |
| K8 | R2 lifecycle deletions are approximate ("typically … within 24 hours") and old rules can linger; so `staging/` and `meta/` never carry an Expiration rule. | S12 | Upheld | Upheld; the real reasons are "Expiration ignores commit state" and "a mistaken rule lingers" | Upheld (also caught by the `staging_expiry` mutant) | **Verified** |
| K9 | Presigned URLs: GET/PUT/HEAD/DELETE, 1 s–7 days, reusable until expiry. Inferences: Create/Complete go through the Worker; a presigned PUT can overwrite its own key within its lifetime. | S15 | Upheld | Upheld; "must go through the Worker" overstated (temporary credentials exist) | **Refuted in part**: the POST exclusion is about HTML forms; presigned Create/Complete is undocumented, not excluded | **Verified** (facts; Worker-side Complete is now a protocol choice required by record-first, not an R2 constraint) |
| K10 | D1 Time Travel restores to any minute in the last 30 days (7 on Free); safety must be anchored at the homelab. | S18, S17 | Upheld | Upheld; flagged that a rollback also rewinds `event_seq` | Upheld; same flag | **Verified** |
| K11 | Lost responses after a successful commit are a known failure mode (Dropbox `incorrect_offset` text; restic rest-server #196; Immich #22024); equal-content re-puts and repeated records must succeed or return the stored receipt. | S26, S31, S30 | Upheld | Upheld | Upheld | **Verified** |
| K12 | Immich #31622 is not "duplicate treated as safe": the CLI treats every reject as a duplicate and may unlink the file; not reproduced against a stock server. | S29 | Upheld | Upheld | Upheld | **Verified** |
| K13 | An advisory lease + per-upload keys + device safety valve gives the safety of optimistic upload while keeping most of the bandwidth savings of exclusive claims; safety never depends on the lease, the queue or D1. | Analysis; S11; S47 | **Refuted**: the safety half holds only for v1, and the savings half has no evidence | **Refuted**: same; plus DR-F3-2 may remove cross-person answers, and an unmetered-only valve is the failing `no_valve` mutant on metered-only devices | **Refuted**: same; plus small bounds, unmodelled single-PUT and hide-then-reappear | **Contested** |
| K14 | R2 outages (2025-02-06 all ops, 59 min; 2025-03-21 all writes, 67 min; 2026-08-07 some ENAM multipart objects unavailable): staged ≠ safe; retry, don't reject, on a missing object. | S39 | Upheld as corroborated through secondary channels only | **Refuted**: cannot confirm from a primary | **Refuted**: same; and the 2026-08 report conflicts with an immediate `content-missing` reject | **Contested** (and secondary only) |

**How the contested claims are handled.**
- **K13** no longer supports any recommendation on its own. The safety basis is now: per-upload keys plus homelab-only commit and delete (K5, and SR-07's stated purpose), verification before commit (SR-04), receipts as the only "safe" (SR-05), the valve and retry budget (SR-06), and the A3-S1 v1 result within its bounds (S47). The lease is kept as an **optional efficiency layer**, cheap because ADR-0010 already builds the lease SQL; its bandwidth value is explicitly unmeasured (E1) and conditional on DR-F3-2.
- **K14** is kept as colour only. "Staged ≠ safe" rests on SR-05 and the single-copy window (AR-07); "retry rather than reject on a missing object" rests on SR-01 (cloud trusted for availability only) and the fence rule in F6. A3 still needs H1 to fetch the primary post-mortems before ADR-0009 cites any incident detail.

### Supporting claims (primary source; not individually skeptic-tallied)

These support details, never a recommendation by themselves.

| # | Claim | Sources | Note |
|---|---|---|---|
| C1 | Queues delivers at least once; Cloudflare recommends a producer-generated unique ID as idempotency key. | S7 | |
| C6 | Pull uses short polling; batch 5 (max 100); visibility timeout 30 s (max 12 h); message `id` is ephemeral; token needs queues read+write. | S4 | |
| C8 | Queue backlog capped at 25 GB; message ≤ 128 KB. | S5 | |
| C9 | R2 `object-create` fires on PutObject, CopyObject, CompleteMultipartUpload; up to 100 rules per bucket; no delivery or ordering statement. | S10 | |
| C12 | Re-uploading a part number replaces the previous part; if that upload fails the original part is lost. | S13 | |
| C15 | `resumeMultipartUpload` does not validate the uploadId; a parallel Worker invocation can complete or abort at any time. | S14 | |
| C18 | D1 `batch()` runs statements sequentially as one transaction. | S16, S17 | |
| C20 | DO alarms: at least once, up to 6 retries, latest `setAlarm()` only. | S19 | |
| C21 | Ente cleanup refuses to delete temp objects with a committed row; aborts multipart before delete; backs off. | S21 | |
| C22 | restic rest-server: O_EXCL temp → fsync → rename → dir fsync before replying; 403 on an existing blob; no deletes in append-only mode. | S22 | |
| C24 | Duplicacy "exists vs being deleted" race; "0 new chunks" then missing chunks (#335). | S24, S32 | user report for #335 |
| C26 | Dropbox upload sessions: 48 h, 350 GB, 150 MB per request. | S26 | |
| C27 | tus: offset mismatch → 409, no change. | S25 | |
| C28 | C2SP checkpoint = signed note with origin, tree size, root hash; tiles of 256 hashes. | S33 | |
| C30 | Stateright 0.31.0 models lossy/duplicating networks and crashes; Quint 0.33.0; TLC needs Java 11+. | S36, S37 | |
| **C31** | "Incomplete multipart uploads are automatically aborted after 7 days by default. You can change this by configuring a custom lifecycle policy." The page does not say a value above 7 days is accepted. | S41 | Raised by skeptic 1; checked by the synthesizer 2026-10-07 |
| **C32** | R2 release note 2023-08-11: "Users can now complete conditional multipart publish operations. When a condition failure occurs when publishing an upload, the upload is no longer available and is treated as aborted." | S42 | Raised by skeptic 3 (and C1's K4); checked by the synthesizer 2026-10-07; behaviour untested (C1-S1 H2) |

## Findings

### F1. State model (v1)

**Actors:** device D, Worker + D1 (W), R2, homelab H, optional hint channel. **Identifiers:** `upload_id` (Worker-made, random, one per upload attempt), `record_id` (device-made, random 128-bit, A2), `dedup_id` (A1), `record_sha256` (SHA-256 of one record's signed-note bytes, A2), `h0_sha256` (binds the record to an object, A2). **Idempotency key:** (device_id, record_id) everywhere, with `dedup_id` and `record_sha256` as bound fields (fixes the adversary skeptic's inconsistency; PLAN's "(dedup ID, record ID)" is kept in meaning, since `record_id` is per device). Blobs are keyed by SHA-256.

**Cloud, per upload** (D1 row; C1 owns the schema):

| State | Entered by | Leaves to | Notes |
|---|---|---|---|
| `claimed` (lease: device, upload_id, UploadId, key, `lease_expires_at` in Worker time) | `POST /v1/uploads` on MISSING | `staged`, `fenced` | Lease renewed by progress (each URL window). Advisory (F2). |
| `staged` | `complete` **after** the record batch is in `meta/` (record-first, F6) | `committed`, `duplicate`, `rejected` | Never expires on a timer (SR-10(b)). Treated as IN_FLIGHT for other devices (Run B choice). |
| `fenced` | Lease lapsed with no progress, NoSuchUpload, or device revoked | — | The Worker refuses any later URL, re-sign or `complete` for this `upload_id`. Once the last URL has expired, no object can appear under its key (honest cloud). **Not modelled.** |
| `committed` / `duplicate` | Homelab publish | — | `duplicate` = the content was already committed; the record still gets its receipt. |
| `rejected(code)` | Homelab publish | — | Resets only this upload's claim; never downgrades a committed ID (SR-11(b)). |

**Cloud, per dedup ID:** a projection (`absent / in-flight / committed`), rebuildable from the homelab (I5). Scope per DR-F3-2 (F3).

**Homelab, per record** (system of record): `received` → `awaiting-content` (record seen, upload still live or not yet listed) → `verifying` → `committed` (receipt signed) | `awaiting-blob` (dedup hit whose blob is not yet committed; A2 "record waits") | `held` (accepted for review: anomaly or revocation cut-over; policy D3/D4/E3; **not modelled**) | `rejected(code)` (including `content-missing`). **Per blob:** `absent → committed → pruned (admin only)`.

**Client, per item** (B6 owns the DB; E3 owns the words):

| # | State | Meaning | Exits |
|---|---|---|---|
| 1 | discovered | Enumerated, not hashed | 2, excluded |
| 2 | hashed | Pass 1 done (SHA-256, dedup ID); header fixed so the record can be sealed | 3 |
| 3 | dedup-checked | Typed answer received | 4 or 6 |
| 4 | uploading | Holds `upload_id` and lease; parts in flight; journal per CE §8 | 5; `fenced` or abort → 4 (new upload) |
| 5 | record accepted + staged | Worker accepted the record and completed (record-first) | 6 |
| 6 | awaiting receipt | No receipt yet; re-check with backoff; valve; retry budget | 7; valve → 4; `content-missing` or re-upload request → 4 |
| 7 | committed | Own receipt entry verified against the pinned trust bundle | 8 |
| 8 | re-verified | Later homelab statement confirms presence (v2) | — |

Side states: `on USB` (never safe); `cloud-only`; `excluded`; `failed(reason)` with `source-changed`, `source-unreadable`, `permission-lost`, `rejected-by-home`, `too-large-for-link`; `budget-spent` (retry budget exhausted → visible nudge, SR-06); and **`gone-before-safe`**: the source and the encrypted object are both gone and there is no receipt. It is the only possible-loss state and always alerts the person and the admin (SR-28, T-22, AR-09).

### F2. Concurrency: per-upload keys, homelab-only commit, optional advisory lease

- **Why not an exclusive claim on a shared key (ADR-0001 §4 sketch).** Corrected rationale after review:
  - Same-key writes are last-writer-wins (K5). R2 does support conditional multipart completion (C32), but a failed condition **aborts the loser's upload**, destroying its parts; behaviour is untested (C1-S1 H2).
  - An exclusive claim can be squatted or held for days by a slow phone (T-06), and needs a takeover protocol (restic stale locks, S23).
  - A dedup-ID key is an existence oracle and an overwrite target for another person's staged ciphertext (M-49).
  - Shared keys cause false blame when a leaked URL or the cloud overwrites (SR-11(c)).
  - **Per-upload keys are not what makes integrity hold** (D1-S2): verification before commit (SR-04) does. The case for them is liveness, attribution, resume and the M-49 oracle, which is enough.
- **The lease.** The Worker records a lease and answers other devices IN_FLIGHT within the scope DR-F3-2 allows. It never answers IN_FLIGHT to the device that holds the live lease (**F-B1**, found by A3-S1 Run B). A device told IN_FLIGHT sends its record as a dedup hit and re-checks with backoff. Safety never depends on the lease (A3-S1 v1, within bounds).
- **Its value is unmeasured.** Under DR-F3-2 option E (the skeleton default) there are no cross-device IN_FLIGHT answers at all, and the lease only stops a device racing itself. Under C, it helps within a person and above T_x across persons. E1 must measure the overlap within and across persons before anyone claims savings (K13 contested).
- **Takeover:** none. The in-flight payload key is sealed on the claimant's device (CE §8.1), so another device simply uploads under its own key.
- **The 7-day multipart abort vs a slow phone** (K7, C31):
  1. **Gate on A3-S3 H3 first.** The docs say the default "can be changed by configuring a custom lifecycle policy" (C31) but not that values above 7 days are accepted. If R2 accepts a longer `AbortIncompleteMultipartUpload` on `staging/`, prefer it, keep the lease TTL shorter than the abort and URL lifetimes (SR-10(a)), and treat the rest as fallbacks.
  2. **Baseline until then:** restart under a new upload, then after a size or ETA threshold, route the file to USB (`too-large-for-link`).
  3. **Segment checkpoint** (complete parts 1..k as `…/s0`, continue in a new multipart `…/s1`; or server-side UploadPartCopy into one final object): a fallback only. It creates a completed object before the upload ends, so it **must be record-first** (the record is accepted before the first segment Complete) and must be added to the model before use. ADR-0010 currently calls it primary; that needs to change with C1 (hand-off).
- **Resume rule** (C12, C15): never re-send a journaled part; treat NoSuchUpload as normal and ask the Worker for the upload's state first.

### F3. "Already have it", poisoning and rejection

- **Typed answers only** (K12): `MISSING`, `IN_FLIGHT`, `COMMITTED`, `UNKNOWN`. Anything untyped or unverifiable is MISSING-later. None is ever "safe" (SR-05; mutants `safe_on_committed_answer` and `safe_on_staged` caught).
- **Scope** (SR-21, DR-F3-2): per person by default; cross-person only above T_x if the owner chooses C; none under D/E. Claims (IN_FLIGHT) are scoped the same way (M-29). A3 owns the protocol but F3 owns the presence design.
- **COMMITTED proof is device-neutral** (M-27; adversary skeptic): a homelab-signed content statement over (dedup_id, padded size, statement epoch), never another device's receipt, so no device_id, record digest or commit time leaks between devices. It lets the device skip the content upload (SR-06); it does not make the item safe.
- **The device always sends its own record** and is safe only with its own receipt entry (C24, SR-06).
- **Rejection (SR-11):**
  - (a) the homelab keeps nothing;
  - (b) resets only the rejected upload's claim, never downgrades a committed ID;
  - (c) flags a device **only** if its own valid signed record matches the rejected object (header MAC, `h0_sha256`); otherwise logs "tamper in transit" and alerts the admin without blame. This replaces the draft's "flag the uploading device", which a leaked URL or the cloud could abuse;
  - (d) sends a homelab-signed **re-upload request** for that `dedup_id` to devices whose records await it. Not modelled; it only speeds recovery. Re-check and the valve remain the guarantee.
- **A compromised or rolled-back Worker** can delay but not suppress: every device has a re-check, a retry budget that ends in a nudge, and needs a homelab signature to reach "safe".
- **Pruned blobs:** after an admin prune, the homelab answers new dedup-hit records for that content with `content-missing`; COMMITTED statements carry an epoch so old statements can be retired (adversary skeptic, minor).

### F4. Receipts

| Option | Offline-verifiable | Device storage | Out-of-order commits | Detects later homelab omission | Complexity |
|---|---|---|---|---|---|
| Per-file receipt (CE §10) | Yes | One signature per record | Yes | No | Low (prototyped) |
| **Per-device batch receipt (recommended v1)** | Yes (keep batch bytes) | One signature per batch | Yes | No | Low |
| Watermark ("all seq ≤ N committed") | Yes | Constant | **No**: one stuck 20 GB video blocks it | Partly | Low |
| Watermark + exception list (SACK-style) | Yes | Small | Yes | Partly | Medium (not assessed further) |
| Per-device Merkle log + C2SP checkpoint | Yes, with proofs | Constant + proofs | Yes | **Yes** | High (C28, S34, S38) |

- **v1 envelope:** a C2SP signed-note signed by the homelab receipt key (key from the pinned trust bundle, SR-02), matching A2's record envelope. Entries bind (device_id, record_id, record_sha256, dedup_id, padded size, committed_at in homelab time, outcome). `record_sha256` binds the true size through the record; every cloud-visible size is the padded one (A2 §9).
- **Identity:** at most one receipt entry per (device_id, record_id) (I4); the homelab stores it before publishing and returns the stored bytes on every redelivery (mutant `resign_receipt` caught).
- **Relay:** the Worker's relay is a cache; the homelab republishes after a D1 rollback (mutant `no_republish` caught). USB sticks carry receipt batches back (A4).
- **Signed freshness (SR-18):** a homelab-signed heartbeat note (homelab time, per-device last receipt batch number, ingest backlog counts) relayed through `GET /v1/status`. A device shows "home not confirming" after T_fresh without one. It also gates the valve (F7).
- **Audit log (SR-30):** v1 is an append-only file of per-entry homelab-signed notes (accepted, rejected, receipt issued), kept at the homelab. C2SP tlog checkpoints are the Wave 2 option, shared with receipts v2.
- **Separate signer (AR-08):** the contract keeps "sign receipt" as its own step behind an interface so A6/D2 can move it to a signer that re-verifies from the append-only store. Not decided here.

### F5. Reconciliation first; hints second

- **Path of record (SR-12):** a paginated listing of `meta/` and `staging/` (K5: listing is strongly consistent), on homelab start, after any hint gap, and periodically (proposal: hourly; no measurement).
- **"Listings stay small" is only true at steady state.** During a multi-day homelab outage while seeding, `staging/` can hold up to one object per file uploaded in that window (2–10 TB, perhaps 500k+ files). At up to 1,000 keys per list call (S14: "Defaults to `1000`, with a maximum of `1000`", checked 2026-10-07) that is about 500 list calls per full listing (arithmetic, not a measurement). Mitigations: paginate with a `start-after` checkpoint; and ADR-0010's guard rail already pauses presigning when the signed heartbeat is stale, which bounds staging growth during outages. Cost to C4.
- **Hint channel:** A3 recommends the **Worker feed** (`GET /v1/homelab/feed?after=…`, ADR-0010, pending DR-C1-3) over the Queues HTTP pull consumer:
  - the pull consumer shares the 1,200 / 5 min client-API bucket, with a 5-minute lockout (K4);
  - lease semantics are loose (K3) and messages can be dropped by retention or `max_retries` (K1, K2);
  - wrangler refuses `type = "http_pull"` and Miniflare has no pull route, so it cannot be tested locally (G2-S1);
  - the feed keeps no Cloudflare API token at home.
  If the owner keeps Queues (to stay close to ADR-0001 §1), use them only as a hint: ack once the hint is in the homelab's durable inbox; dedupe by record key; set retention to 14 days explicitly (default 4, K1). Hints arrive one per record-batch object, not one per record, so the earlier "≈ 20,000 calls per 1M records" figure overstated the load; it is withdrawn.
- **Cursor and D1 rollback** (logic and adversary skeptics): a plain `event_seq` rewinds under Time Travel (K10) and new events would reuse numbers below the homelab's cursor. Rule: each feed event carries the hash of the previous event; the homelab polls with `after=<seq>&expect=<hash>`; the Worker answers `resync` if the event at `seq` is missing or differs, and the homelab then does a full listing and restarts the cursor. An operator restore also bumps a feed epoch (C8 runbook). **Not modelled**; add to A3-S1 in Wave 2.
- **Nothing trust-relevant comes from the feed.** Revocation is homelab-authoritative (SR-17): the homelab keeps and signs its own revocation list; the cloud only relays it.
- **Outage longer than any retention** loses only hints, because `staging/` and `meta/` have no Expiration rule (K8). Proven in the model by the `no_reconcile` mutant (one dropped hint suffices without listing).

### F6. Record-first ordering and the durable-commit contract

**Record-first (the A3-S1 fix):** no completed content object may exist in `staging/` unless the record that references it is already in `meta/`.

| Path | Rule | Model status |
|---|---|---|
| Multipart | `complete` carries (or references) the record batch; the Worker writes `meta/` create-only, then runs CompleteMultipartUpload | **Model-checked** (A3-S1 v1) |
| Single PUT (small files) | The Worker accepts the record before it issues the PUT URL (record-first at begin) | **Not modelled** (all three skeptics) |
| Segment checkpoint | The record is accepted before the first segment Complete | **Not modelled** |
| Alternative for small files | Upload as a one-part multipart so the object appears only at Worker Complete | Costs two extra S3 operations per file (Create and Complete); C4 to classify and price |

With record-first on every path there is **no orphan class and no orphan GC**. The draft's "deleting an orphan cannot lose data" is withdrawn: A3-S1 refuted it (T-22/AR-09 with no fault).

**`content-missing` (fence rule).** The homelab answers a record with `content-missing` only when (1) the Worker reports the upload `fenced` (no further URLs can be issued and the last URL has expired), and (2) the object is absent on repeated reads over a grace window (proposal: three reads over 24 h; no measurement), checking the multipart upload first and then the object (the spike's TOCTOU note). Otherwise it retries and alerts the admin. A lying cloud can force `content-missing`, which costs a re-upload (availability only, SR-01). This answers the "transient R2 loss" contradiction raised by all three skeptics.

**Hide then reappear** (adversary skeptic): the homelab keeps the `upload_id`s it answered `content-missing`. If an object appears later under such a key, it verifies it against the archived record; if valid it commits the blob (no receipt for the rejected attempt; the device's new attempt then becomes a dedup hit); in every case it then deletes the object. **Not modelled.**

**Durable-commit contract (A6 interface)**, idempotent on (device_id, record_id), blob keyed by SHA-256:

1. Fetch and parse the record batch strictly (SR-22); verify signature, admitted key, replay checks (A2 §8 steps 1–4).
2. If the record references content: fetch the object; on NoSuchKey retry and alert, apply the fence rule; decrypt to temp and verify per A2 §8 steps 5–10 (SR-04).
3. `put_blob(sha256, bytes)`: durable before return (O_EXCL temp, fsync, rename, dir fsync, C22); equal existing content is success (K11).
4. `archive_record(device_id, record_id, bytes)`: durable; same `record_id` with different bytes → `E_REPLAY_RECORD_ID`.
5. Catalog transaction (sighting, ingest event) and audit-log entry (SR-30).
6. Sign the receipt entry, or return the stored one (I4).
7. Publish commit marks and receipts to the Worker; wait for success.
8. **Only then** delete the staging object(s) and the `meta/` object, with homelab credentials. Devices never delete (R-18).

Each step's necessity is shown by a caught mutant: `no_verify` (I3), `delete_on_pull` and `delete_before_archive` (I1), `staging_expiry` (I1), `resign_receipt` (I4), `no_republish` (L1).

### F7. Safety valve and retry budget

- **Why it exists:** without it, a dead or lying claimant leaves an item unsafe forever (`no_valve` mutant fails L1).
- **The model's valve is an oracle** that fires fairly whenever the item is stuck (S47 limits). A real device has only timers, so the policy must keep firing possible on every device:
  - fires after T_valve awaiting a receipt (proposal 12 h, so the re-upload can still land inside BUD-TTS for typical photos; no measurement);
  - deferred while the latest signed heartbeat is stale (homelab down: a re-upload cannot help and BUD-TTS does not apply), and while the competing upload is `staged` and the heartbeat shows the homelab is up (SR-10(b)). Deferral is bounded: the time spent deferred counts against the retry budget, so a cloud that claims "staged" or withholds heartbeats for ever ends in a nudge, not silence;
  - on metered-only devices it fires after a longer T_valve_metered (proposal 72 h) **or** asks the person, and when the per-item retry budget is spent the item becomes a visible nudge to the person and the admin (SR-06). This removes the "unmetered only" starvation the logic and adversary skeptics found.
- **BUD-TTS honesty:** in the dead-claimant case the item will miss BUD-TTS by at least T_valve plus upload time. This is a stated exception for H1 to record in `budgets.md`, not a pass.
- **Seeding and outages:** the heartbeat gate stops mass duplicate re-uploads during homelab outages or ingest backlogs (adversary skeptic). Its effect must be measured in A3-S2.

### F8. Metadata-only events, clocks, BUD-TTS, mixed transports

- **Records:** sightings, tombstones, scan checkpoints, source records share the signed envelope (A2 §7) and travel in record batches. Each record gets its own receipt entry. Not model-checked.
- **`device_seq`:** allocate at sealing, just before a record first leaves the device, so a gap means a missing record (SR-13). Since the header is fixed after pass 1, a record can be sealed before upload and reused across restarts and transports. A2 to agree (the CE prototype signs at start). `E_REPLAY_SEQ` surfaces as an admin alert "possible cloned or restored device" (D3).
- **Clocks:** Worker time for leases and URL expiry; homelab time for `committed_at` and every health or nudge decision (SR-19); device time recorded only.
- **BUD-TTS:** measured on the device from `first_seen` to receipt verification (monotonic), split with server timestamps (claim, staged, record accepted, committed, relayed, fetched). "Sent" = first_seen to record accepted and staged.
- **USB:** same `record_id` on every path; the homelab returns the stored receipt on a second arrival; fallback to R2 after a window A4 sets (proposal 14 days).
- **Stolen or ransomwared device** (adversary skeptic, T-23): a valid device can fill the keep-forever store. A3 provides the `held` homelab state; per-device ingest quotas, anomaly rules and the revocation cut-over (homelab receive time plus a `device_seq` watermark at revocation) belong to D3/C2/D4/E3.

### F9. Protocol state → user-visible state map (E3 owns the words)

| Protocol state(s) | Placeholder word (glossary §8) | Safe? | Nudge / alert |
|---|---|---|---|
| discovered, hashed, dedup-checked | found, waiting | No | Staleness if no progress (E3) |
| uploading; paused (metered, battery, lease wait) | sending / waiting (reason) | No | — |
| record accepted + staged; awaiting receipt | sent | **Never** | Receipts lag past BUD-TTS → "home server hasn't picked up" |
| heartbeat older than T_fresh (SR-18) | home not confirming | No change | Device banner; admin alert (dead-man, C7) |
| on USB | on a USB stick | **Never** | Fallback to R2 after the window |
| committed (own receipt verified) | stored at home | **Yes (only this)** | — |
| re-verified (v2) | stored at home (checked date) | Yes | — |
| failed: source-changed | waiting | No | Auto-retry |
| failed: rejected-by-home | problem, will resend | No | Admin alert (D4 forensics); blame only per SR-11(c) |
| held (homelab review) | waiting for the admin | No | Admin alert |
| failed: source-unreadable, permission-lost | can't read (gap reason) | No | Person nudge |
| failed: too-large-for-link | needs a USB stick | No | Admin nudge |
| budget-spent (SR-06) | stuck, admin told | No | Person + admin nudge |
| cloud-only | not on this device | n/a | E4 policy |
| excluded | (not shown to others) | n/a | — |
| **gone-before-safe** | was deleted before it reached home | **Loss risk** | **Person + admin alert, always** (SR-28) |

### SR crosswalk (D1 register → this note and the spec)

| SR | How A3 meets it | Where |
|---|---|---|
| SR-01 | Safety never rests on a cloud value; cloud lies cost availability | F3, F5, F6 |
| SR-03, SR-13 | Device-signed records; `device_seq` at sealing | F8; A2 |
| SR-04 | Verify before commit; first verified copy wins | F6 steps 1–3 |
| SR-05 | Own receipt is the only "safe" | F1, F4, F9 |
| SR-06 | Re-check with backoff, retry budget, visible nudge | F7 |
| SR-07 | Per-upload keys (purpose: attribution, resume, oracle) | F2; key layout is C1's |
| SR-10 | Advisory lease with TTL < abort and URL lifetime; `staged` never expires on a timer | F1, F2 |
| SR-11 | (a)–(d) adopted | F3 |
| SR-12 | Listing is the path of record; hints only | F5 |
| SR-17 | Revocation homelab-authoritative; never from the feed | F5 |
| SR-18 | Signed heartbeat; "home not confirming" | F4, F9 |
| SR-19 | Homelab time for decisions | F8 |
| SR-21 | Answers and claims scoped per DR-F3-2 | F3 |
| SR-22 | Strict parsing before work | F6 step 1 |
| SR-26 | `meta/` keys carry no dedup ID (ADR-0010 layout) | C1 |
| SR-28 | `gone-before-safe` always alerts | F1, F9 |
| SR-30 | Per-entry signed audit log v1 | F4 |

Tension to note for C1: SR-07 says staging keys are "random"; ADR-0010's `staging/<dedup_id>/<upload_id>/s<n>` puts the dedup ID in the key. Devices have no List or HEAD-by-guess rights, and the cloud already sees dedup IDs in checks, so this is a privacy-minimisation question (SR-26, M-49) for C1 and D6, not a safety one.

### Alternatives compared

| Option | Fit with settled requirements | Pros | Cons | Evidence |
|---|---|---|---|---|
| Exclusive claim, objects keyed by dedup ID (ADR-0001 §4 sketch) | Needs OD-04 to change | Simple model; saves bytes on races | Last-writer-wins; conditional Complete aborts the loser (C32); squatting; slow holder; M-49 oracle; false blame | K5, C32, T-06, M-49 |
| Purely optimistic, per-upload keys, homelab dedup | Fits | No liveness dependency on others | Duplicate bytes when libraries overlap (unmeasured) | K5; S47 |
| **Per-upload keys + homelab-only commit + record-first + valve, optional advisory lease (recommended)** | Fits; touches ADR-0001 §4 (OD-04) | Model-checked safety for multipart; lease adds efficiency if overlap is real | More states; single-PUT, segments and fence not yet modelled | S47; K5, K10 |
| Record-first at begin for every path | Fits | Covers single PUT and segments uniformly; matches SR-21 "record-first" | Records arrive before content; needs the fence rule | F6; skeptics |
| Worker fence + GC of fenced uploads only | Fits | Lets single PUTs keep their record after the PUT | A slow device past the fence must re-upload | F6 |
| One-part multipart for small files | Fits | Reuses the model-checked path | Two extra S3 operations per file (C4 to price) | F6 |
| Two-phase token then batch-create (Google Photos) | Similar to record batches | Per-item results | Server-trusted; tokens expire (secondary) | S27 |
| tus in a Worker | Worker proxies every byte | Offset resume | TBs through the Worker; duplicates R2 multipart | C27 |
| R2 temporary credentials for device multipart | Conflicts with record-first Complete and SR-07 (no device List/Copy) | Fewer Worker calls | Device could Complete before the record | K9; SR-07 |
| Durable Object per dedup ID as lease authority | Fits | Strong single-threaded leases | More moving parts; leases are advisory anyway | ADR-0010 rejected one global DO |
| Longer abort rule on `staging/` | Fits | Simplest slow-phone fix | Untested whether > 7 days is accepted (C31) | A3-S3 H3 |
| Segment checkpoint / UploadPartCopy | Fits | Works if the abort cannot be extended | Complexity; must be record-first; not modelled | F2 |
| Receipts: per-file / **batch** / watermark / SACK / Merkle log / none | "none" breaks "safe only with receipt" | See F4 | See F4 | C28 |
| Hint channel: **Worker feed** / Queues pull / Queue → push consumer → feed / DO WebSocket | Feed and DO touch ADR-0001 §1 wording (DR-C1-3) | Feed: no API token at home, no lockout | Pull: rate limit, loose leases, no local emulation | K3, K4, S45, S48 |

### Similar work and lessons

| Project or paper | What they do | Borrow or avoid | Source |
|---|---|---|---|
| Ente museum | Temp-object bookkeeping; HeadObject size check; never deletes committed | **Borrow** bookkeeping and size check | S21, C21 |
| restic rest-server | Append-only, durable write sequence; 403 on existing | **Borrow** durable writes; **avoid** 403 on retry (#196) | S22, S31, C22, K11 |
| restic design | Ordering invariants; stale locks | Borrow ordering invariants | S23 |
| Duplicacy | Lock-free dedup, fossil collection | "Exists" ≠ "safe" | S24, S32 |
| Immich | CLI treats every reject as duplicate (#31622); lost-ack loop (#22024) | **Avoid** untyped rejects and non-idempotent commits | S28–S30, K12 |
| Dropbox upload sessions | Lost response is part of the contract | Borrow | S26, K11 |
| Google Photos Library API | Per-item results in batch | Borrow | S27 |
| C2SP / Sigsum / Tessera | Signed notes, checkpoints, witnesses | Signed-note now; log in v2 | S33, S34 |

### Tools and libraries

| Name | Purpose | Licence | Maturity | Source |
|---|---|---|---|---|
| TLA+ TLC (tla2tools v1.7.4, TLC 2.19) | Model check, LTL liveness | MIT | Used in A3-S1 | S47 |
| Stateright | Rust model checker (cross-check in A3-S1) | MIT | 0.31.0, 2025-07-27 | S36 |
| Quint | TLA-family language | Apache 2.0 | 0.33.0, 2026-09-28 | S37 |
| wrangler / Miniflare | Local Worker emulation (no HTTP pull, no lifecycle API) | MIT OR Apache-2.0 | wrangler 4.143.0 | S37, S48 |
| ed25519-dalek | Signatures | BSD-3-Clause | 3.0.0, 2026-07-06 | S38 |
| rs_merkle | Merkle trees (v2) | Apache-2.0/MIT | 1.5.0, 2025-02-24 | S38 |

## Spikes

| Spike | Hypothesis | Pass → / fail → (decision) | Exec tag | Budget IDs | Data class | Status | Result |
|---|---|---|---|---|---|---|---|
| A3-S1 | The protocol satisfies I1–I4, I6 and L1–L4 with bounded crashes, dropped or duplicated hints, homelab offline, D1 rollback (PLAN: 3 devices × 3 items) | Pass → state table into ADR-0009; fail → fix each counterexample in the spec | CT (run for real) | none (no time in the model) | `SYN → results` | **Pass for v1 within stated bounds; v0 failed** | See below; evidence `spikes/A3-S1/README.md`, `spikes/A3-S1/evidence/` |
| A3-S2 | On the A0 harness (emulated, not real R2/Cloudflare): two devices, same 2 GB file, one killed; homelab offline 15 simulated days; 5 % of hints dropped | Pass → one blob, two receipts, empty staging and multipart after reconciliation; fail → fix reconcile or ack design | CT (emulated) | BUD-TTS (decomposition only) | `SYN → results` | **Deferred to Wave 2** (A0 harness does not exist yet) | Protocol-level stand-in only: A3-S1 TLC 2x1 with `kill`, `down` and unbounded hint drops passes I1–I4, I6, I7 and L1–L4. Not a harness measurement. |
| A3-S3 | Real R2: H1 resume after 24 h; H2 default abort counts from initiation; H3 whether an abort rule > 7 days is accepted; H4 1-day abort cleans up; H5 segment checkpoint | H3 accepted → longer abort on `staging/`, segments fallback; H3 rejected → restart + USB baseline, segments only after modelling | SB (kit) | BUD-REVOKE, BUD-TMP | `SYN → results` | **Kit-ready**, needs sandbox account (H5 L01) and 9 calendar days | `docs/research/kits/A3-S3/README.md`. No emulated run: Miniflare returns 501 for lifecycle and ListParts and has no clock (G2-S1). Smoke-tested against moto 5.2.3 only (not a result). H3 framing should be updated to "confirm the documented configurability" (C31). |

**A3-S1 detail** (two independent models, run 2026-10-06 in the container: 4 vCPU, 15 GB RAM, OpenJDK 21, rustc 1.94.1):

- **v0 (the draft design) fails** the strengthened invariant I7 (no dangling record) with no fault and no attacker: Start, Complete, orphan-GC, SendRecord. Run A E1: 1,860,254 states; Run B: 41 states. 175,069 of 200,000 random 3 × 3 v0 runs hit it. I1 as worded and liveness still hold (the valve recovers), at the cost of a re-upload, or loss if the source is gone.
- **v1 (record-first Complete, no orphan GC, `content-missing`, self-lease rule F-B1):**
  - TLC, 2 devices × 1 item, all 11 fault classes together, budget 1, safety exhaustive: **pass, 7,916,780 states, 282 s**.
  - TLC liveness L1–L4 per fault class (K = 3, budget 1), all pass: none 28,756; kill 93,698; lostresp 567,560; homecrash 84,320; down 92,716; abort 1,199,442; bad 1,372,056; rollback 311,084; spurious 1,072,860; r2loss 1,550,304; devcrash 3,459,668 states.
  - Run A (Rust BFS, AG EF liveness, counts cross-checked with Stateright): all invariants hold up to 38,646,964 states (2 devices, 3 attempts, 2 faults) and 19,843,663 states (3 devices × 1 item).
  - Item independence: 0 of about 28.8 M transitions touch more than one dedup ID (D1 wipe excepted).
  - 3 × 3 random simulation: 4 × 200,000 runs, 0 safety violations; 17 runs attempt-exhausted (a bound artifact).
  - Stopped at 25 min with no violation (evidence, not proof): TLC 3x3 ring no faults ≥ 35.5 M states to depth 18; 3x1 all faults ≥ 43.9 M; 2x1 budget 2 ≥ 53.4 M.
  - Mutants: all caught (7 in Run A; 11 in Run B).
- **What "pass" covers** (logic skeptic): exhaustive at 2 devices × 1 item per fault class and for all-faults safety; 3 × 3 only bounded or simulated; nothing beyond 3 devices; the valve is an oracle; no wall-clock time, so BUD-TTS is not measured. **Not modelled:** single-PUT path, segment checkpoints, the fence rule, hide-then-reappear R2 faults, feed-cursor rollback, USB, record batches and metadata-only records, a malicious Worker beyond IN_FLIGHT lies, two homelab ingest workers.

## Conflicts with settled text

- **ADR-0001 §4 step 2** (conditional claim; objects keyed by dedup ID): conflicts with per-upload keys and the advisory lease. Routed through **OD-04** (DR-A3-1). The amendment text is D1's Appendix A in `docs/security/threat-model.md`; ADR-0009 proposes to carry it (H1 decides the carrier).
- **ADR-0001 §1** names Queues as the notification path. A3 now recommends the Worker feed (C1's DR-C1-3 option); choosing it needs an "Amends: ADR-0001 §1" owner decision under DR-C1-3, not here. ADR-0001 §1's "at most 14 days" is accurate as a maximum (K1).
- **CLAUDE.md "devices can only append, never delete or rewrite":** a presigned PUT is reusable until expiry, so its holder can rewrite one uncommitted staged object within ≤ 15 min. Homelab verification catches it. A3 agrees with ADR-0010 that append-only is enforced at commit, not at staging; the owner confirms under DR-C1-6. D4 tests it.
- **CLAUDE.md restores "staging in an expiring R2 prefix":** the expiring rule must never match `staging/` or `meta/`. ADR-0010 puts restores in a separate bucket (`rq-restore`), which satisfies this.
- **CLAUDE.md "low resource impact (metered networks)" vs "data integrity over everything":** the valve on metered-only devices is an explicit trade-off for the owner (DR-A3-3), not a default buried in the spec.
- **CLAUDE.md "cross-user dedup":** presence-answer scope (DR-F3-2) may limit cross-person upload-skip; storage dedup across all users is unchanged. F3 owns that owner question.

## Open questions

| # | Question | Who | By when |
|---|---|---|---|
| 1 | Does R2 accept an AbortIncompleteMultipartUpload rule > 7 days on a prefix, and does it override the default? (C31 says configurable) | A3-S3 H3 / C1-S1 (SB) | Gate B |
| 2 | If-None-Match on presigned PUT; conditional Complete behaviour (C32); can Create/Complete be presigned at all? | C1-S1 | Gate B |
| 3 | Which Queues lease statement holds in practice (only if Queues are kept) | T2 / C1 sandbox | Wave 2 |
| 4 | Does an account-owned token get its own 1,200 / 5 min bucket? (only if the pull consumer is kept) | T2, C1 | Wave 2 |
| 5 | ~~Do Miniflare / wrangler emulate HTTP pull?~~ **Answered**: no (G2-S1). R2 event notifications locally: not checked | — / C1 | — |
| 6 | Model-check record-first for single PUT and segments, the fence rule, hide-then-reappear, feed-cursor rollback, a metered-only device with a timer valve | A3 (A3-S1 extension) | Before Gate A |
| 7 | Policy numbers: T_valve, T_valve_metered, retry budget, re-check backoff, lease TTL, T_fresh, fence grace window, reconcile interval, USB fallback window. All proposals; no measurements | A3-S2, E3, owner (DR-A3-3) | Gate A |
| 8 | Receipt envelope detail (signed-note text layout) and a Rust signed-note implementation (not checked) | A2, A3 spec | Gate A |
| 9 | Late `device_seq` allocation vs CE's sign-at-start | A2 | Gate A |
| 10 | Primary post-mortems for the R2 incidents (K14 secondary only) | H1 | Before ADR-0009 cites them |
| 11 | Cross-device overlap within a person and across persons during seeding (decides whether the lease is worth keeping) | E1 census | Wave 2 |
| 12 | Commit dates of the Cloudflare docs files (GitHub API blocked) | H1 | Wave 2 |
| 13 | Separate receipt signer (AR-08), `held` policy, revocation cut-over | A6, D2, D3, D4 | Gate A (AR-08) / Wave 2 |

## Recommendation

Adopt for ADR-0009 and `docs/spec/ingest-protocol.md`:

- **Truth:** listing for staged, homelab for committed, the device's own receipt for safe.
- **Uploads:** per-upload staging keys; homelab-only commit and deletion; **record-first on every path** (model-checked for multipart; single PUT and segments to be modelled before Gate A); no orphan GC; `content-missing` only under the fence rule.
- **Lease:** an optional advisory lease with the self-lease rule (F-B1), scoped per DR-F3-2. Its value is unmeasured; it is never part of the safety argument.
- **Answers:** typed, scoped, never safe; COMMITTED proofs are device-neutral.
- **Rejection:** SR-11(a)–(d).
- **Valve:** timer-based with heartbeat gating, a metered fallback and a retry budget that ends in a nudge (DR-A3-3).
- **Reconciliation:** paginated listing is the path of record; Worker feed as the hint channel (with C1, pending DR-C1-3); hash-chained cursor with resync.
- **Receipts v1:** per-device batch receipts in signed-note form (DR-A3-2); signed heartbeat (SR-18); per-entry signed audit log (SR-30).
- **Slow phones:** test the longer abort rule first (A3-S3 H3); restart + USB is the baseline; segments only as a modelled fallback.
- **UX:** hand the F9 map to E3.

**What would change this:** a counterexample in the Wave 2 model extension; A3-S3 showing a longer abort rule is accepted (segments dropped) or that segments fail; E1 showing negligible overlap (drop the lease); the owner choosing DR-F3-2 option E permanently (lease reduced to per-device use); the owner declining the metered valve fallback (accept a documented liveness gap on metered-only devices).

## Decision requests

### DR-A3-1 (for OD-04): Amend ADR-0001 §4: per-upload staging keys, advisory lease, record-first, homelab-only commit and deletion
- **Needed by:** Wave 1 exit (OD-04).
- **Evidence:** F2, F6; K5, K10, C32; A3-S1 (S47); SR-04, SR-07, SR-10, SR-11; D1 Appendix A.
- **Options:**
  | Option | What it means for the family | Cost | Reversibility | Risks |
  |---|---|---|---|---|
  | A. Keep ADR-0001 §4 (exclusive claim, objects keyed by dedup ID) | Same | Same | Costly after first ingest | A conditional Complete aborts the losing upload (C32); squatting and slow holders block others; existence oracle (M-49); false blame |
  | B. Per-upload keys + advisory lease + record-first + homelab-only commit/delete (recommended) | Nothing visible; fewer stuck items | Some duplicate uploads (rate unmeasured) | Easy before Gate A | More states; parts not yet modelled (F6) |
- **Recommendation:** B. Its case is liveness, attribution and the oracle, not integrity (homelab verification carries integrity in both). Its multipart path is model-checked; it does not depend on the cloud being honest.
- **Touches settled text:** ADR-0001 §4 steps 1, 2, 4 ("Amends: ADR-0001 §4").
- **If no decision by the deadline:** the A0 skeleton uses B as a throwaway; Gate A stays blocked.

### DR-A3-2: Receipt format for v1 (one-way door #5)
- **Needed by:** Gate A.
- **Evidence:** F4; C28; CE §10; A2 §7 (signed-note records).
- **Options:** A. per-file receipts (CE format); B. per-device batch receipts over per-record entries, signed-note, versioned (recommended); C. per-device Merkle log with C2SP checkpoints now.
- **Recommendation:** B, with the `v` and type fields reserved so a v2 log checkpoint can be added for re-verification. One signature per batch, offline-verifiable, handles out-of-order commits, and consistent with A2's envelope.
- **Touches settled text:** none.
- **If no decision by the deadline:** A for v0 only.

### DR-A3-3: Device safety valve and retry budget
- **Needed by:** Gate A (numbers tunable later).
- **Evidence:** F7; A3-S1 `no_valve` mutant; SR-06, SR-10, SR-18; BUD-TTS, BUD-BAT-D.
- **Options:**
  | Option | What it means for the family | Cost | Reversibility | Risks |
  |---|---|---|---|---|
  | A. Never re-upload when told another device is sending | Lowest data use | — | Easy | A dead or lying claimant leaves items unsafe forever (fails L1) |
  | B. Timer valve (proposal 12 h awaiting receipt), gated on a fresh homelab heartbeat; on metered-only devices a longer timer (proposal 72 h) or ask the person; retry budget ends in a person + admin nudge (recommended) | Occasional duplicate upload; a rare stuck item becomes a visible message | Some extra data and R2 operations | Easy (numbers) | Mobile data on metered-only devices; dead-claimant items miss BUD-TTS |
  | C. As B but unmetered networks only | Lowest mobile data | — | Easy | Metered-only devices never recover from a dead claimant (the failing mutant) |
- **Recommendation:** B. It is the only option that keeps L1 on every device. The owner must accept the stated BUD-TTS exception for the dead-claimant case (H1 to record in `budgets.md`).
- **Touches settled text:** none directly; it is a trade-off between CLAUDE.md "low resource impact (metered networks)" and "data integrity over everything", so it needs the owner.
- **If no decision by the deadline:** B is used in the prototype.

Related decisions owned elsewhere that A3 depends on: **DR-F3-2** (presence scope; F3, with OD-04) and **DR-C1-3** (notification path; C1). A3's input: DR-F3-2 changes only the lease's value, never safety; for DR-C1-3, A3 prefers the Worker feed.

## Hand-offs

| To | What | Why |
|---|---|---|
| C1 | Enforce record-first in `/v1/uploads/{id}/complete` (refuse Complete unless the record batch is in `meta/`) and for single PUT at `/v1/uploads`; add the `fenced` upload state; hash-chained feed with `expect=` and `resync`; self-lease rule F-B1; device-neutral COMMITTED statement; ADR-0010 to stop calling segment checkpoint "primary" until A3-S3 H3 and the model extension; note C31 and C32; SR-07 vs dedup ID in staging keys | F2, F3, F5, F6 |
| C1-S1 | Conditional Complete behaviour (C32), If-None-Match on presigned PUT, abort > 7 days (with A3-S3) | Open 1–2 |
| A2 | `device_seq` at sealing; receipt envelope as signed-note; `content-missing` and `held` outcomes; record reused across restarts | F4, F8 |
| A4 | Same `record_id` across transports; receipt batches on sticks; fallback window | F8 |
| A6 | Eight-step contract; equal-content `put_blob` is success; signer step behind an interface (AR-08) | F6 |
| D1 / D4 | Presigned overwrite window; fence abuse; hide-then-reappear; SR-11(c) blame tests; ransomware `held` flow (T-23) | F3, F6, F8 |
| D3 / C2 | Revocation cut-over by homelab receive time and `device_seq` watermark; per-device ingest quotas | F8 |
| F3 | IN_FLIGHT and COMMITTED answers scoped per DR-F3-2; device-neutral proof (M-27); timing side channel M-28 needs a fixed receipt schedule below T_x | F3 |
| E1 | Measure overlap within a person and across persons | F2 |
| E3 | F9 map, including `home not confirming`, `budget-spent`, `held` and the `gone-before-safe` alert | F9 |
| G2 | Invariant table I1–I7, L1–L4 and the mutant list | Spikes |
| C4 | Listing cost during long outages; one-part multipart cost for small files | F5, F6 |
| H1 | Correct PLAN's Immich wording (K12); log blocked sources; record the BUD-TTS dead-claimant exception; update the A3-S3 kit's H3 framing (C31) | Method, F7 |
| H4 | Glossary: claim = advisory lease; add `fenced`, `duplicate`, `awaiting-content`, `held`, `content-missing`, `budget-spent`, `gone-before-safe` | F1 |
