# ADR-0009: Ingest uses per-upload staging keys, record-first completion, homelab-only commit, device-held batch receipts, and reconciliation by listing

- **Status:** Proposed
- **Date:** 2026-10-07
- **Owner workstream:** A3
- **Decider:** the owner
- **Gate:** A
- **Supersedes / Amends:** **Amends ADR-0001 §4 (steps 1, 2 and 4), only if the owner chooses OD-04 option B** (DR-A3-1). The amendment text is D1's draft in `docs/security/threat-model.md` Appendix A, extended here with record-first completion; H1 decides whether this ADR carries it or a separate number does. ADR-0001 §1 (Queues as the notification path) is **not** amended here: that is C1's DR-C1-3 (ADR-0010).
- **Evidence:** [`docs/research/a3-ingest-protocol.md`](../research/a3-ingest-protocol.md); spike A3-S1 ([`spikes/A3-S1/README.md`](../../spikes/A3-S1/README.md)); kit A3-S3 ([`docs/research/kits/A3-S3/README.md`](../research/kits/A3-S3/README.md))
- **Normative artifact:** [`docs/spec/ingest-protocol.md`](../spec/ingest-protocol.md) (Draft): invariants, state tables, flows, answer and outcome codes, receipt format, durable-commit contract, protocol → UX map
- **Traceability:** R-11, R-12, R-18, R-27, R-30, R-40, R-45, C-02, C-03
- **Owner decisions:** OD-04 (via DR-A3-1); DR-A3-2 and DR-A3-3 (new; H1 to number). Depends on DR-F3-2 (F3) and DR-C1-3 (C1).
- **One-way door:** Yes, #5 (receipt format, with A4's manifest format)

## Context and problem statement

CLAUDE.md requires that backups are verifiable, that data integrity comes first, that devices can only append (R-18), that the protocol tolerates intermittent connectivity (R-40), and that the cloud API is treated as under attack. ADR-0001 §4 sketches the ingest flow: a dedup check, a conditional claim on an object keyed by dedup ID, an upload, then homelab verification and commit. It leaves open how a device learns that its data is safe, what happens when two devices hold the same file, when a staged object may be deleted, and how the homelab catches up after an outage that outlasts queue retention (C-02).

The D1 threat register (SR-01: the cloud is trusted for availability only) and the R2 facts (last-writer-wins on a shared key, 7-day multipart abort, approximate lifecycle deletion, D1 Time Travel) make the sketch unsafe as written: one false "already have it" answer from a compromised cloud would let a device believe a file is safe that the homelab never received.

A3-S1 model-checked the first A3 draft (v0) and found a fault-free race that could delete a slow device's staged object before its record arrived (I7). This ADR records the corrected design (v1) and marks which parts are model-checked and which still need it.

## Decision drivers

- **R-18** devices can only append; **R-40** intermittent connectivity; **R-45** homelab pulls, verifies, stores; **C-02** an outage longer than queue retention loses nothing; **C-03** "already have it" grants no read rights.
- **SR-01, SR-04, SR-05, SR-06, SR-10, SR-11, SR-12, SR-17, SR-18, SR-19, SR-21, SR-28, SR-30** (threat register).
- **BUD-TTS** (time to safe, and where it is measured), **BUD-REVOKE** (URL lifetime ≤ 15 min), **BUD-TMP** (phone temp disk), **BUD-BAT-D** (re-check cost).
- Keep-forever retention: receipts held by devices must stay verifiable (one-way door #5).
- CLAUDE.md "low resource impact (metered networks)" in tension with "data integrity over everything".

## Considered options

1. **Exclusive conditional claim on objects keyed by dedup ID** (ADR-0001 §4 sketch).
2. **Purely optimistic upload** under per-upload keys, homelab dedup, no lease.
3. **Per-upload keys + record-first completion + homelab-only commit and deletion + device safety valve, with an optional advisory lease** (recommended).
4. The v0 draft of option 3 (record sent after completion, homelab GC of record-less objects): **refuted by A3-S1**.

## Decision

Option 3, because it is the only option whose safety does not depend on the cloud being honest, on R2 conditional operations, or on any other device finishing its upload, and because its multipart path passed the A3-S1 model check (within the bounds stated under Confirmation).

### In scope for Wave 1 (decided, subject to the owner)

1. **Where the truth lives.** A paginated R2 listing of `meta/` and `staging/` is the record of what is staged. The homelab is the record of what is committed. A device counts an item as safe only when it holds a homelab-signed receipt entry for **its own record** that verifies under the pinned key (SR-05). Leases, hints and D1 are caches.
2. **Per-upload staging keys; homelab-only commit and deletion** (OD-04). Every upload gets a Worker-generated `upload_id` and its own key (layout owned by C1, ADR-0010). Only the homelab deletes staging or record objects, and only after the eight-step durable-commit contract (spec §8). Devices never get delete rights.
3. **Record-first.** No completed staging object may exist without its record already in `meta/`. For multipart uploads the Worker writes the record batch create-only, then runs CompleteMultipartUpload (model-checked). For single PUTs the record is accepted before the PUT URL is issued; for segment checkpoints before the first segment Complete (**specified, not yet model-checked**). There is **no orphan GC**.
4. **Missing content.** On a missing object the homelab retries and alerts. It answers `content-missing` only when the Worker reports the upload fenced and repeated reads over a grace window find nothing (**specified, not yet model-checked**). Objects that reappear under a rejected upload are verified, optionally committed as content, then deleted.
5. **Typed answers that never mean safe.** `MISSING / IN_FLIGHT / COMMITTED / UNKNOWN`, scoped as DR-F3-2 decides (until then, only the device's own receipts). COMMITTED carries a device-neutral homelab content statement, never another device's receipt. The device always sends its own record and waits for its own receipt (SR-06). The Worker never answers IN_FLIGHT to the lease holder itself.
6. **Advisory lease (optional optimisation).** A TTL lease renewed by progress, shorter than the multipart abort and longer than the URL lifetime (SR-10(a)); `staged` never expires on a timer (SR-10(b)). Its bandwidth value is unmeasured and is not part of the safety argument.
7. **Rejection** follows SR-11(a)–(d): keep nothing; reset only that upload; blame a device only when its own signed record matches the rejected object; send a homelab-signed re-upload request to waiting devices.
8. **Reconciliation first.** Listing is the path of record (SR-12). Hints are only hints; A3 prefers C1's Worker feed (decided under DR-C1-3). The feed cursor is hash-chained so a D1 rollback forces a resync (**not yet model-checked**). If Queues are used, ack only after the hint is in the homelab's durable inbox and set retention explicitly (the default is 4 days, not 14). Revocation never comes from the feed (SR-17).
9. **Durable-commit contract** (interface for A6): verify record → fetch and verify object → durable `put_blob` (equal content is success) → archive record → catalog and audit log → sign or return stored receipt → publish → delete staging. Idempotent on (device_id, record_id); blob keyed by SHA-256.
10. **Receipts v1** (DR-A3-2): per-device batch receipts, a C2SP signed note over per-record entries binding (device_id, record_id, record_sha256, dedup_id, padded size, committed_at, outcome). Stored before publishing; the same bytes on every redelivery. Relayed by the Worker as a cache; also carried on USB.
11. **Signed freshness and audit** (SR-18, SR-30): a homelab-signed heartbeat drives "home not confirming"; the homelab keeps an append-only log of per-entry signed notes.
12. **Safety valve and retry budget** (DR-A3-3): a timer valve gated on a fresh heartbeat, a longer timer or a prompt on metered-only devices, and a per-item retry budget that ends in a person + admin nudge. Never silence.
13. **Clocks and sequence numbers.** Worker time for leases, homelab time for commits and health decisions (SR-19), device time as context only. `device_seq` is allocated when the record is sealed (A2 to agree). BUD-TTS is measured on the device from first seen to receipt verification.
14. **Protocol → UX map** (spec §10) is handed to E3. `gone-before-safe` always alerts the person and the admin (SR-28).

### To be decided in Wave 2

- Policy numbers (lease TTL, valve timers, retry budget, T_fresh, fence grace, reconcile interval, USB fallback): proposals only, set after A3-S2 and with E3 and the owner.
- Slow uploads past the 7-day multipart abort: a longer abort rule if A3-S3 H3 shows R2 accepts one; otherwise segment checkpoints after they are modelled. Until then, restart and then route to USB.
- Receipt v2 (per-device Merkle log with C2SP checkpoints) for re-verification after a catalog rebuild.
- The `held` state policy, per-device ingest quotas and the revocation cut-over (D3, C2, D4, E3).
- Separate receipt signer (AR-08; A6, D2).

### Consequences

- **Good:** a compromised or rolled-back Cloudflare side costs availability, not data or a false "safe". Lost responses, duplicate hints, outages longer than any retention, and D1 rollback are tolerated by design (A3-S1). Concurrent duplicate uploads are harmless. Users see "stored at home" only when it is true.
- **Bad / accepted trade-offs:** more R2 objects and some duplicate uploads (rate unmeasured); devices store receipts; more states to implement and test; an item whose claimant dies misses BUD-TTS by at least the valve time; metered-only devices may use mobile data for a valve re-upload or ask the person; "append-only" is enforced at commit, not at staging (a URL holder can rewrite one uncommitted staged object within ≤ 15 min; DR-C1-6).
- **Follow-up work:** extend A3-S1 (single PUT, segments, fence, hide-then-reappear, cursor rollback, metered-only timer valve) before Gate A; A3-S2 on the A0 harness (Wave 2); A3-S3 on the sandbox; C1 to enforce record-first and fencing in the API; A2 to agree `device_seq` timing and the receipt envelope; E3 to word the states.

### Confirmation

- **A3-S1 model** (TLA+/TLC and Rust): v1 holds I1–I4, I6, I7 and L1–L4. Exhaustive at 2 devices × 1 item for every fault class and for all faults together (7,916,780 states, safety); Rust up to 38,646,964 states; 3 × 3 bounded (≥ 35.5 M states to depth 18, no violation) and simulated (800,000 runs, 0 violations). All 11 mutants caught. Limits: no wall-clock time, the valve is an oracle, nothing beyond 3 devices.
- **Before Gate A:** the model extension listed above passes; G2 adopts the invariant table and mutant list.
- **Wave 2:** A3-S2 (one blob, two receipts, empty staging after a 15-day simulated outage with 5 % hint loss; BUD-TTS split recorded).
- **Gate B:** A3-S3 and C1-S1 on real R2.
- **Continuous:** a CI or cron check that the ingest bucket has no Expiration rule (ADR-0010); D4's attack suite.

## Pros and cons of the options

### Option 1: exclusive claim on dedup-ID keys

- Good, because it is simple and avoids duplicate bytes when two devices race.
- Bad, because same-key writes are last-writer-wins (K5), and a conditional Complete aborts the losing upload (release note 2023-08-11, C32, untested).
- Bad, because a slow or malicious holder blocks others (T-06), and a takeover protocol is needed anyway.
- Bad, because the key is an existence oracle and an overwrite target (M-49), and overwrites cause false blame (SR-11(c)).

### Option 2: purely optimistic, no lease

- Good, because it has no liveness dependency on other devices and the simplest safety argument.
- Bad, because overlapping libraries upload the same bytes more than once (rate unmeasured, E1).
- It is the safety core of option 3; adopt it outright if E1 shows little overlap or DR-F3-2 removes cross-device answers.

### Option 3: recommended

- Good, because safety rests on homelab verification and device-held receipts (SR-04, SR-05), which A3-S1 confirms for the multipart path including D1 rollback, hint loss, lost responses, crashes and R2 loss.
- Good, because it tolerates outages longer than any queue retention (K1, K2, K8).
- Bad, because single-PUT, segment, fence and cursor rules are not yet model-checked.
- Bad, because the lease's bandwidth benefit is unproven (claim K13 contested).

### Option 4: v0 draft

- Bad, because A3-S1 found a four-step, fault-free trace in which the homelab deletes a slow device's object just before its record arrives; with the source gone the item is lost (T-22).

## Evidence

| Claim | Source (primary) | Verdict |
|---|---|---|
| K1 Queues retention default 4 days, max 14 (Paid), 24 h (Free) | Cloudflare docs `queues/configuration/configure-queues.mdx`, `queues/platform/limits.mdx` | Verified |
| K2 messages at `max_retries` are deleted permanently | `queues/configuration/pull-consumers.mdx` | Verified |
| K3 pull-consumer leases are not exclusive ownership after the timeout | `pull-consumers.mdx` | Verified |
| K4 client API 1,200 / 5 min with a 5-minute lockout | `partials/fundamentals/api-rate-limits.mdx` | Verified |
| K5 R2 strongly consistent listing; last-writer-wins | `r2/reference/consistency.mdx` | Verified |
| K6 conditional headers listed for PutObject, none listed for Complete | `r2/api/s3/api.mdx`, `workers-api-reference.mdx` | Verified (literal claim; see C32) |
| K7 default multipart abort 7 days after initiation | `r2/buckets/object-lifecycles.mdx` (and C31: "can be changed") | Verified |
| K8 lifecycle deletion approximate; never an Expiration rule on staging | `object-lifecycles.mdx` | Verified |
| K9 presigned URL methods and lifetime; reusable | `r2/api/s3/presigned-urls.mdx` | Verified |
| K10 D1 Time Travel 30 days | `d1/reference/time-travel.mdx` | Verified |
| K11 lost responses after commit must be answered idempotently | Dropbox `files.stone` (plus user reports) | Verified |
| K12 Immich #31622 is "every reject treated as duplicate" | github.com/immich-app/immich/issues/31622 | Verified |
| A3-S1 v0 counterexample and v1 pass | `spikes/A3-S1/README.md` | Project spike (run) |
| K13 lease + valve keeps most savings and safety | analysis | **Contested**; not used as sole support. Safety rests on K5, K10, SR-04/05/06 and A3-S1 |
| K14 R2 outage incidents | secondary press only | **Contested / secondary only**; colour only. "Retry, don't reject" rests on SR-01 |

## Reversibility

- The receipt format becomes hard to change once devices hold receipts (Gate A, door #5); `v` and origin fields are reserved for a v2 log.
- Per-upload keys and record-first become hard once real family objects are staged (Gate B, with ADR-0010's key layout).
- Leases, valve timers, the hint channel and presence scope are Worker or client policy and can change later.

## Alternatives considered

- **tus in a Worker:** every byte through the Worker; R2 multipart already resumes.
- **Two-phase token then batch-create (Google Photos):** server-trusted; borrowed only "per-item results in batch".
- **R2 temporary credentials for device-side multipart:** would let a device complete before its record exists; conflicts with record-first and SR-07.
- **Watermark receipts:** one stuck large video blocks every later item.
- **Merkle-log receipts now:** detects homelab omissions, but too complex before the pilot; v2 option.
- **Queues HTTP pull as the hint channel:** shared API rate limit, loose leases, cannot be emulated locally; acceptable only as a hint if the owner keeps Queues.
- **Orphan GC of record-less objects:** refuted by A3-S1.

## Open questions

- Model extension for single PUT, segments, fence, hide-then-reappear, cursor rollback and a metered-only timer valve (A3, before Gate A).
- Abort window > 7 days on R2 (A3-S3 H3, C1-S1).
- Presence scope (DR-F3-2, F3) and hint channel (DR-C1-3, C1).
- `device_seq` at sealing; receipt envelope text (A2).
- Separate receipt signer (AR-08; A6, D2); `held` policy, quotas, revocation cut-over (D3, C2, D4, E3).
- Cross-device overlap within and across persons (E1).
- Primary post-mortems for R2 incidents (H1; blocked).
