# Spike C1-S3: "which of 1,000 IDs are missing" against a 5M-row index, emulated leg (THROWAWAY)

> **Emulated, not real D1/Cloudflare.** This ran against local D1 (SQLite inside workerd, under `wrangler dev`) in the cloud container on 2026-10-06. Latency here is local SQLite on a shared x86 container, with no network and no D1 durability path, so **it cannot pass or fail PLAN's "p99 < 500 ms"**. What it does show: the query shape is correct, it uses the primary key, and how many rows D1's own accounting (`meta.rows_read`) charges per call in the emulator. The real run is the kit `docs/research/kits/C1-S3/README.md`.
> This is throwaway research code, not production code.

- **Spike:** C1-S3 (workstream C1, `docs/research/PLAN.md` section "C1.")
- **Exec tag:** `[SB]`. This folder is the local-emulator variant, run as CT.
- **Budget IDs cited:** BUD-CLOUD (input only, via the cost per million IDs). PLAN's thresholds for this spike (p99 < 500 ms; < $1 per million IDs) have no budget ID.
- **Data-handling class:** `SYN → results`. The index is `randomblob(32)` rows generated inside SQLite.

## What ran

- Worker: `spikes/C1-S1/worker/` (routes `/s3/*`), wrangler 4.143.0, Miniflare 5.20260926.0-alpha, workerd 1.20260926.1, `compatibility_date` 2026-09-01, local observability off (`X_LOCAL_OBSERVABILITY=false`).
- Driver: `c1s3.py --rows 5000000 --chunk 250000 --trials 200 --present 0.5` (Python 3.11.15). Finished 2026-10-06T20:16:50Z.
- Table: `dedup (id BLOB PRIMARY KEY, state INTEGER NOT NULL DEFAULT 1) WITHOUT ROWID`, 5,000,000 rows.
- Each call sends 1,000 hex IDs: 500 sampled from the table and 500 fresh random ones, shuffled. Two shapes:
  - `json_each`: one statement, one bound parameter: `SELECT j.value FROM json_each(?1) j WHERE NOT EXISTS (SELECT 1 FROM dedup d WHERE d.id = unhex(j.value))`.
  - `in100`: 10 statements of `WHERE id IN (unhex(?1), …, unhex(?100))` in one `batch()` (the 100-bound-parameter cap per query).
- Container load: another workstream's Java process used about 3.5 cores of 4 during the run (load average 4–6), so latencies are inflated and noisy.

## Results (`results/miniflare-5M.json`)

| Shape | Correct answers | Client latency p50 / p99 / max (ms) | D1 `meta.duration` p50 / p99 (ms) | `rows_read` per call |
|---|---|---|---|---|
| `json_each` | 200/200 | 13.5 / 26.0 / 31.2 | 5.0 / 10.0 | 1,500 (every call) |
| `in100` | 200/200 | 16.0 / 28.5 / 31.1 | 6.0 / 12.0 | 1,500 (every call) |

Query plan for `json_each` (`EXPLAIN QUERY PLAN`): `SCAN j VIRTUAL TABLE INDEX 1`, `CORRELATED SCALAR SUBQUERY 1`, `SEARCH d USING PRIMARY KEY (id=?)`. So each ID costs one primary-key lookup, not a scan.

Fill: 20 calls of 250,000 rows each via a recursive CTE. D1 `meta.duration` grew from 709 ms (first chunk) to 2,561 ms (last chunk). That is the local SQLite cost of random-key inserts into a growing B-tree, not real D1 write latency.

**Cost arithmetic from the emulated `rows_read` (to be confirmed on real D1):** 1,500 rows read per 1,000 IDs = 1.5 million rows read per million IDs. At $0.001 per million rows read above the included 25 billion per month (D1 pricing partial, retrieved 2026-10-06), that is $0.0015. Plus 1,000 Worker requests per million IDs at $0.30 per million above the included 10 million (Workers pricing page, retrieved 2026-10-06) = $0.0003. **About $0.002 per million IDs**, against PLAN's "< $1". This holds only if real D1 counts `rows_read` the same way as the emulator. The kit checks it.

## Verdict

- **Correctness and query shape: pass (emulated).** Both shapes are correct on 200 of 200 calls, and the plan uses the primary key.
- **p99 < 500 ms: no result.** Local latency is not evidence for real D1.
- **Cost < $1 per million IDs: indicative pass**, by about 500×, on emulated row accounting.
- The single-parameter `json_each` shape is as cheap as ten 100-parameter statements and simpler. It also uses 1 statement instead of 10 of the 1,000 queries D1 allows per Worker invocation.

Sources: D1 pricing `https://raw.githubusercontent.com/cloudflare/cloudflare-docs/production/src/content/partials/workers/d1-pricing.mdx`; Workers pricing `https://raw.githubusercontent.com/cloudflare/cloudflare-docs/production/src/content/docs/workers/platform/pricing.mdx`; D1 limits (100 bound parameters, 30 s per query and per batch) `https://raw.githubusercontent.com/cloudflare/cloudflare-docs/production/src/content/docs/d1/platform/limits.mdx`. All retrieved 2026-10-06.

## Cleanup

The 5M-row local database (about 440 MB of `.state`, together with the other spikes' state) stayed in the scratchpad and was deleted after the C1-S2 run. Nothing large is in the repository.
