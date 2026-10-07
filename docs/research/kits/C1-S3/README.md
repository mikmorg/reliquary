# Kit C1-S3: "which of 1,000 IDs are missing" against a 5-million-row D1 index (sandbox account)

- **Spike:** C1-S3 "Which of 1,000 IDs are missing against a 5M-row index" (workstream C1, see `docs/research/PLAN.md`, section "C1.")
- **Exec tag:** SB. Uses the dedicated **sandbox** Cloudflare account (H1, long-lead item L01), never production. An emulated leg (local D1 inside workerd) ran on 2026-10-06; see `spikes/C1-S3/README.md`. It says nothing about real D1 latency.
- **Prepared by / date:** C1 spike runner (agent), 2026-10-06
- **Who runs it:** the owner on a laptop, or an agent on a machine that can reach the Worker's hostname (see kit C1-S2, step 5).
- **Time needed:** about 15 min hands-on, plus the fill (50 calls of 100,000 rows; unknown on real D1, budget 30 min) and 400 query calls (a few minutes).
- **Data-handling class:** `SYN → results`. The index holds `randomblob(32)` values generated inside D1. Nothing from the family is used.
- **Run together with:** kits C1-S2 and C1-S4 (same deployed Worker). Do kit C1-S2 steps 1–6 first.

## Purpose

Measure how fast, and at what cost, the Worker can answer "which of these 1,000 dedup IDs do you not have yet?" from a D1 table of 5 million IDs. This is the call every device makes before uploading.

## Hypothesis

- **H1 (latency):** one Worker request carrying 1,000 IDs, half present and half absent, answered by one D1 statement that expands the IDs from a single JSON parameter (`json_each`), has a **p99 under 500 ms** measured at the client, over 200 calls.
- **H2 (cost):** the D1 `rows_read` reported per call is about 1,500 (1,000 JSON rows plus 500 index hits), as in the emulated leg. At the published price this costs far under **$1 per million IDs checked** (calculation in the Results section).
- **H3 (alternative shape):** the same check split into 10 statements of 100 bound parameters each (the per-query parameter cap), sent in one `batch()`, is correct and its latency and `rows_read` are recorded for comparison.
- **H4 (correctness):** both shapes return exactly the 500 absent IDs in every call.

## Decision it informs

| If the result is… | Then… |
|---|---|
| **Pass** (PLAN: "p99 < 500 ms; cost < $1 per million IDs checked") | The dedup index stays in D1 with the `json_each` statement (C1 note F2, C26). |
| p99 ≥ 500 ms, and the D1 `meta.duration` explains most of it | Shard the dedup table into SQLite-backed DOs by ID prefix (C1 note F2 fallback), then re-run this kit against the DO variant (needs a small code change in the Worker). |
| p99 ≥ 500 ms, but D1 `meta.duration` is small | The time is network or Worker overhead, not D1. Do not shard; record it and look at the client's location and the Worker placement. |
| Cost ≥ $1 per million IDs | Revisit the query shape (`rows_read` amplification). |
| **No result** | ADR-0010 cites the arithmetic in C1 note F2 plus the emulated leg, labelled as such. |

## Budget IDs cited

- **BUD-CLOUD** (monthly cloud cost ceiling, owner sets in H2): the cost per million IDs feeds the C4 cost model. PLAN's own pass criteria for this spike are "p99 < 500 ms" and "< $1 per million IDs"; they have no budget ID of their own.

## Equipment

| Item | Exact model or version | Why | Have it? |
|---|---|---|---|
| The C1 spike Worker deployed on the sandbox account, with D1 database `c1-spikes` | Kit C1-S2 steps 1–6 | Runs the query next to real D1 | — |
| Machine with Python ≥ 3.9 (stdlib only) | e.g. Python 3.11 | Runs `c1s3.py` | — |

**Software and files needed:** `spikes/C1-S3/c1s3.py` from this repository, and `SPIKE_TOKEN` and `W` exported as in kit C1-S2.

## Before you start

- [ ] Confirm the sandbox account is on **Workers Paid**. The fill writes 5 million rows. Workers Paid includes the first 50 million rows written per month; Workers Free allows only 100,000 rows written per day, so this kit cannot run on Free (D1 pricing, `https://raw.githubusercontent.com/cloudflare/cloudflare-docs/production/src/content/partials/workers/d1-pricing.mdx`, retrieved 2026-10-06). Check the month's usage in the dashboard first.
- [ ] Note your location and connection type: p99 includes your round trip.

## Procedure

1. Fill and measure in one go:
   ```sh
   cd spikes/C1-S3
   python3 c1s3.py --worker "$W" --rows 5000000 --chunk 100000 --trials 200 --present 0.5 --out results/sb-5M.json | tee results/sb-5M.log
   ```
   **You should see:** `rows 100000`, `rows 200000`, … up to `rows 5000000`, then one line for `json_each` and one for `in100`, each with `correct_missing_count` `200/200`. If a fill call fails with a D1 timeout (D1 limits a query to 30 s), run again with `--chunk 50000`; the script continues from the current row count.
2. If the fill was interrupted and finished in a second run, the measurement is still valid. Write down how many runs it took.
3. Repeat the measurement only (no fill) once more, to see whether the first run was cold: `python3 c1s3.py --worker "$W" --rows 5000000 --skip-fill --trials 200 --out results/sb-5M-rerun.json`.
4. In the D1 dashboard for `c1-spikes`, note the database size and the "rows read" and "rows written" for the run.
5. Fill in the cost calculation below from the measured `rows_read_per_call`.

**Stop and record "No result" if:** the fill cannot reach 5 million rows (record how far it got and why); or `/health` fails.

## Cleaning up

1. `npx wrangler d1 delete c1-spikes` once kits C1-S2 and C1-S4 are also done (the database is shared).
2. Nothing is stored locally except the results files.

## Data handling

Class `SYN → results`. The results contain latencies, row counts, query plans and counts of correct answers. The random IDs themselves are not written to the results. The results may be committed to `spikes/C1-S3/results/`.

## Results

Copy this section into `docs/research/kits/C1-S3/results.md` and fill it in. Do not edit numbers afterwards; add a note instead.

- **Run by / date / place / connection:**
- **Account (sandbox? yes/no), Workers plan:**
- **Emulator used instead of real D1?** No (this is the real leg). Emulated result for comparison: `spikes/C1-S3/README.md`.

| Shape | Calls | Correct | Client p50 / p99 / max (ms) | D1 `meta.duration` p50 / p99 (ms) | `rows_read` per call |
|---|---|---|---|---|---|
| `json_each` (1 statement) | 200 | | | | |
| `in100` (10 statements in one batch) | 200 | | | | |
| `json_each`, rerun | 200 | | | | |

**Cost per million IDs checked** (fill in; prices from the D1 and Workers pricing pages, re-check them on the run date):

- D1 rows read per million IDs = `rows_read per call` × 1,000 = ……
- D1 cost = that ÷ 1,000,000 × (price per million rows read above the included amount) = $……
- Worker requests per million IDs = 1,000; cost = 1,000 ÷ 1,000,000 × (price per million requests) = $……
- **Total = $……** (compare with $1)

| Pass criterion | Budget ID | Measured value | Pass / Fail / No result |
|---|---|---|---|
| p99 < 500 ms for a 1,000-ID check against 5M rows | — (PLAN) | | |
| Cost < $1 per million IDs checked | BUD-CLOUD (input) | | |

- **Overall:** Pass | Fail | No result
- **Surprises:**
- **Follow-ups for the workstream:**
