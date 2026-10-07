# Spike C1-S2: lease race, D1 vs Durable Objects, emulated leg (THROWAWAY)

> **Emulated, not real D1/Durable Objects/Cloudflare.** This ran against local D1 and local SQLite-backed Durable Objects inside workerd (`wrangler dev`) in the cloud container on 2026-10-06. It tests whether the **SQL and transaction logic** gives exactly one winner under a real 50-way concurrent race. It does not test real D1's or real DO's replication, durability path or network latency. The latencies below are local and come from a container that another workstream was loading heavily. The real run is the kit `docs/research/kits/C1-S2/README.md`.
> This is throwaway research code, not production code.

- **Spike:** C1-S2 "Claim race: 50 concurrent claims, 10,000 trials, D1 vs DO" (workstream C1, `docs/research/PLAN.md` section "C1.")
- **Exec tag:** `[CT/SB]`. This is the CT leg; the SB leg is the kit.
- **Hypothesis:** exactly one of 50 simultaneous lease requests for the same fresh dedup ID wins, in every one of 10,000 trials, for both stores. Every 10th trial first plants an expired lease, so 1,000 of the trials are takeover races. Afterwards no ID has two live leases.
- **Decision it informs:** D1 vs DO for the `uploads` (lease) table (C1 note F2). Pass on D1 → keep leases in D1. Fail → DO shards.
- **Budget IDs cited:** none (PLAN: "exactly one winner every time; record p50/p99").
- **Data-handling class:** `SYN → results`. Random dedup IDs only.

## What ran

| Item | Detail |
|---|---|
| Worker | `spikes/C1-S1/worker/` routes `/d1/*` and `/do/*`; wrangler 4.143.0, Miniflare 5.20260926.0-alpha, workerd 1.20260926.1, `compatibility_date` 2026-09-01, local observability off |
| D1 lease | One `DB.batch()` (one SQL transaction): `INSERT INTO uploads … SELECT ?1, ?2, ?3, 'claimed', ?4 WHERE NOT EXISTS (SELECT 1 FROM uploads WHERE dedup_id = ?2 AND state = 'claimed' AND lease_expires_at > ?5)`, then `INSERT INTO events … WHERE EXISTS (… upload_id = ?1)`. A winner is `meta.changes == 1` on the first statement. |
| DO lease | `LeaseShard` SQLite-backed DO, 16 instances by `idFromName("shard-" + first hex digit)`. Inside `ctx.storage.transactionSync()`: count live leases for the ID; if 0, insert. Called over RPC. |
| Driver | `c1s2.py --concurrency 50 --trials 10000 --takeover-every 10`, Python 3.11.15. 50 threads, one persistent HTTP connection each, released together by a barrier for every trial. |
| Run times | D1: 20:17:47Z–20:49:41Z. DO: 20:49:42Z–21:00:42Z (2026-10-06). |
| Load | Load average 4–6 on 4 vCPU during both runs; another workstream's Java process used about 3.5 cores. |

## Results (`results/miniflare-d1.json`, `results/miniflare-do.json`, and the `.log` progress files)

| Store | Trials × concurrency | Winners histogram | Bad trials | Duplicate live leases afterwards | Non-200 | Client errors | Latency p50 / p99 / max (ms, local, per request) | Wall time |
|---|---|---|---|---|---|---|---|---|
| D1 | 10,000 × 50 (500,000 requests) | `{1: 10000}` | 0 | 0 | 0 | 0 | 155.7 / 372.9 / 788.5 | 1,914 s |
| DO (16 shards) | 10,000 × 50 (500,000 requests) | `{1: 10000}` | 0 | 0 | 0 | 0 | 46.7 / 213.3 / 452.6 | 660 s |

Row counts after the runs: DO 11,000 rows for 10,000 IDs (10,000 winners plus 1,000 planted expired leases), as expected. D1 shows 11,001 rows and 10,001 IDs: the extra row is one manual probe lease (`/d1/lease?dedup=probe…`) sent by hand at about 20:20Z to check the Worker was responsive while the run was in progress. It used its own ID, so it did not affect any trial. The D1 event log has 11,001 rows, one per accepted lease, so the event insert in the same batch never fired for a losing request.

## Verdict

- **Exactly one winner in every trial: pass for both D1 and DO (emulated).** The D1 single-`batch()` conditional insert, including the takeover case, is race-free under a 50-way race locally. That matches D1's documented model: one database runs one query at a time, and `batch()` runs as one transaction (C1 note C27; D1 Worker API).
- **p50/p99 recorded**, but only as local figures. Locally, D1 was about 3× slower than the DO shards per request (p50 156 ms vs 47 ms), because all 50 racers queue on one SQLite database while the DO run spreads IDs across 16 objects. Whether that ratio holds on real Cloudflare, where D1 also persists each write to several locations, is what the kit measures.
- No "overloaded" error appeared locally at 50-way concurrency on one D1 database. That says nothing about real D1's queue limits.

## Hazards found while running

- wrangler 4.143's local observability store (`.state/v3/observability`) grew to 270 MB after about 100,000 requests in the first, interrupted pass. Set `X_LOCAL_OBSERVABILITY=false` for load runs (variable read by wrangler's `getLocalObservabilityEnabledFromEnv`, default true).
- workers-sdk #14916 (open, 2026-07-29) reports that a local D1 `SQLITE_BUSY` under concurrent writes can crash `wrangler dev` in some versions. It did not occur with 4.143.0 here.

## Cleanup done

The local `.state`, `.wrangler/` and `node_modules/` were deleted from the scratchpad after the run.
