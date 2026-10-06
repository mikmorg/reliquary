# Spike C4-S1: cost, capacity and storage-budget model v0 (THROWAWAY)

> Throwaway research code. It is not production code. It turns the primary unit prices and
> the stated assumptions into numbers. It measures nothing about Reliquary itself: operations per
> file, file sizes and growth are **assumptions** until A0, E1 and H2 replace them.

- **Spike:** C4-S1 "Model v0, then v1 with A0 numbers" (workstream C4, `docs/research/PLAN.md`)
- **Exec tag:** `[CT]`. It ran in the cloud container on 2026-09-29 with Python 3.11 and the standard library only.
- **Budget IDs cited:** BUD-CLOUD, BUD-ABUSE. Both are still **unset**. `budgets.md` says "Owner sets (H2)". The run tests against the owner-intake *proposed* defaults ($25 per month steady state, $50 in a seed month, $50 abuse, `owner-intake.md` B1–B3). Those defaults are unconfirmed.
- **Data-handling class:** `SYN → results`. No family data is read or written.
- **Research note:** `docs/research/c4-cost-model.md` (the analyst owns it). This folder is the "script or CSV" deliverable that PLAN assigns to C4.

## Run it

```sh
python3 spikes/C4-S1/c4_model.py            # writes spikes/C4-S1/out/*.csv, prints a summary
python3 spikes/C4-S1/c4_model.py --bud-abuse 20 --out /tmp/c4
```

A run takes about 25 s, mostly the full-factorial sensitivity sweep. `evidence/run_output.txt` holds the output of the committed run.

To change an assumption, edit `PARAMS`. Every row names the workstream that will replace it. Edit `PRICES` only after re-reading the cited source.

## What it contains

| File | Contents |
|---|---|
| `c4_model.py` | Prices with a source URL for each; parameters marked A (assumption), O (owner), D (design) or secondary; the monthly-bill function; a day-by-day R2 staging simulator (GB-month = mean of the daily **peak**, per R2 pricing); scenarios; sensitivity; abuse vectors and cap-set bound; capacity and disk-purchase trigger; ISP arithmetic; fixed costs; self-checks |
| `out/prices.csv` | Every unit price, with its unit, source URL and access date |
| `out/params.csv` | Every volume parameter, with its status and who replaces it |
| `out/scenarios.csv` | Monthly bill line by line for steady state, seed, outage, warm cache, file size, metadata batching, part size, IA staging, rounding order, homelab down, restore, and the 10 TB seed total |
| `out/sensitivity.csv` | One-at-a-time swings, the full factorial (3^10 = 59,049 combinations) per growth and warm-cache case, and leave-one-out spreads |
| `out/abuse_vectors.csv` | Cost rate per abuse vector, hours until $50 is spent, what bounds it, and which billing behaviour is undocumented |
| `out/abuse_bound.csv` | 243 cap sets (k compromised devices × T days to suspend × U presigns per device per day × E writes per URL × Q staged GB per device) and the resulting bound |
| `out/capacity.csv` | Tiers S / M / M′ / L × four (L0, g) scenarios: usable TB and TiB, years to the fill target, purchase-trigger date, stored after 10 y, expected drive failures, ARC guideline |
| `out/isp.csv` | Days to move 1–10 TB at 20–1000 Mbps; months to pull a seed under a monthly cap |
| `out/fixed_costs.csv` | Workers Paid, Apple, Azure Artifact Signing, Play/ADC, domain, email |
| `out/checks.csv` | The model re-computes the worked examples in the primary docs |

## Sources (all accessed 2026-09-29)

These are primary, from the `cloudflare/cloudflare-docs @ production` mirror on raw.githubusercontent.com, because developers.cloudflare.com is blocked from the shell: `docs/r2/pricing.mdx`, `docs/r2/platform/limits.mdx`, `docs/workers/platform/pricing.mdx`, `partials/workers/d1-pricing.mdx`, `partials/workers/queues_pricing.mdx`, `partials/durable-objects/durable-objects-pricing.mdx`, `docs/email-service/platform/pricing.mdx` and `docs/billing/manage/budget-alerts.mdx`. The runner re-read the first seven and the budget-alerts page for this run. Also primary: MicrosoftDocs `artifact-signing/how-to-change-sku.md`, developer.apple.com/programs, the developer.android.com verification FAQ and Proxmox `local-zfs.adoc`. These last four are cited from the scout and analyst passes and were not re-fetched by the runner. The drive AFR (1.36 %) is **secondary** (a Backblaze search snippet; the primary is blocked).

## Self-checks (all pass)

The model reproduces the vendors' own worked examples:

- R2 Standard example: $14.85
- R2 IA example: $29.90
- R2 asset-hosting example: $104.40
- R2 GB-month example: 2.66
- Workers example 1: $8.00
- The Queues formula for 10M messages: $11.60

It also reproduces the staging simulator identity (1 GB/day held 1 day gives 2.0 GB-month under the conservative peak).

## Results against the pass criteria

Pass criterion (PLAN C4-S1): the steady-state bill is known within ±25 %; worst-case abuse cost is bounded below BUD-ABUSE; the disk-purchase trigger date is computed.

| Criterion | Budget | Result (this run) | Verdict |
|---|---|---|---|
| Steady-state bill known within ±25 % | BUD-CLOUD (unset; $25 proposed) | Central estimates: $5.00–5.53 at g = 0.5 TB/yr, $5.00–6.19 at 1 TB/yr, $5.03–7.52 at 2 TB/yr (warm cache 0 / 30 d). Over the full factorial of the assumption ranges, the largest deviation from the central estimate is **21 %** at g = 0.5, **30–36 %** at g = 1 and **48–72 %** at g = 2. The largest deviation in dollars is +$3.64, and the highest steady-state value anywhere is **$11.16**, under the $25 proposal. Pinning CPU-ms per Worker request alone (A0 / D3-S1) brings g = 1 down to **10 %**. At g = 2, pinning one parameter still leaves **29 %**, so A0 must measure at least CPU per request and mean file size. | **Met at g ≤ 0.5 TB/yr only**. Not yet met at higher growth. Overall: inconclusive until A0 (v1) |
| Worst-case abuse bounded below BUD-ABUSE | BUD-ABUSE (unset; $50 proposed) | Cloudflare offers no spend cap (budget alerts are informational and a day late). **Without app-level caps: unbounded.** Examples: $691/day at 1,000 junk PUTs/s (about $8.00 per million objects past the free tiers), and up to $2.72 per presigned URL replayed at 1 write/s to a 604,800 s (7-day) expiry, or $0.004 at 900 s. **With caps:** 131 of 243 cap sets stay under $50. The analyst's recommended set (k = 3, T = 1 d, U = 25k/day, Q = 100 GB) gives **$5.10** with E = 1 (If-None-Match enforced), **$25.01** with E = 60 (60 s expiry) and **$308.51** with E = 900 (15 min expiry). If all 25 devices are compromised, only 21 of 81 cap sets stay under $50; all of them need Q ≤ 100 GB, and most need E = 1 or T = 1 h. The **unauthenticated Worker flood** ($27.65/day at 1,000 req/s, $276/day at 10,000 req/s) is **not** bounded by any per-device cap. | **Not demonstrated.** It holds only with C2 controls not yet built, and it depends on four billing behaviours that need a sandbox check (below) |
| Disk-purchase trigger date computed | — | Computed for scenario inputs from t0 = 2026-09-29, lead 14 d and buffer 90 d, at an 80 % fill target. Tier S (2 × 16 TB mirror): **2028-04-28** at L0 = 10, g = 1.5, and **2027-11-10** at L0 = 10, g = 2. Tier M (4 × 16 TB RAIDZ2): 2034-04-04 at L0 = 10, g = 2. Tier L: 2053 or later. The family's own date needs H2 C4 (current pool) and E1 (L0, g). | **Computed (method + scenarios)**. The family-specific date waits for owner input |

**Overall C4-S1 verdict: inconclusive.** v0 ran. v1 needs A0's measured operations per file, E1's growth and file sizes, H2's BUD-CLOUD, BUD-ABUSE and pool figures, and the C2 `[SB]` billing checks.

### Other measured model outputs

These are derived from the assumptions; they are not measurements of Reliquary.

- **Seed month, 2 TB via R2:**
  - 1-day dwell: $12.16.
  - With a 14-day homelab outage: $15.66.
  - With a 30-day warm cache left on: $42.16.
  - With a 2 MB mean file: $17.86. With an 8 MB mean file: $7.26.
  - With metadata batched (m = 0): $7.66.
- **10 TB via R2 over 5 months:** $60.80 in total, or $210.80 with the warm cache on.
- **These numbers are about $1 above the analyst's figures** ($11.16 etc.). The staging simulator counts the daily *peak*, which includes the day's uploads before that day's deletions. It therefore bills about one extra day of inflow compared with the analyst's `I·(d+W)/30` approximation: 133 GB-month instead of about 67 GB-month in a 2 TB month. This is the conservative reading of "averaging the peak storage per day". The difference in dollars is $1.00.
- **Part size is not a cost lever.** Across 8, 16 and 64 MiB parts, Class A is 1.15M, 1.08M and 1.02M against 1.24M at the T1 default. All four bill as 2M operations, so all four cost $12.16. Rounding hides the difference.
- **Rounding order** (free tier subtracted before or after rounding up) made no difference in the 2 TB seed case. R2 pricing does not say which order applies; the Durable Objects page says the excess is taken first and then rounded.
- **R2 Infrequent Access as staging:** a 2 TB seed month costs $64.70, against $12.16 in Standard (30-day minimum, $0.01/GB retrieval, double Class A rate, no free tier).
- **Homelab down all month with the whole library staged:** $34.85 at 2 TB, $79.85 at 5 TB, $154.85 at 10 TB.
- **Restore** of 500 GB staged 7 d plus 1 d lifecycle lag: +$2.10 on a steady month.
- **ISP.** Moving 1 TB takes 4.63 d at 20 Mbps, 0.93 d at 100 Mbps and 0.19 d at 500 Mbps. Under a 1.2 TB/month cap with 0.3 TB baseline use and an 80 % alert, a 10 TB seed takes **15.2 months** to pull. The cap and baseline are illustrative, not the owner's.

### Billing behaviours the model could not settle (need `[SB]`, owned by C2 / D3)

1. Are R2 requests that return 403 (bad signature or expired URL), 412 (If-None-Match) or 429 (same-key rate limit) billed? Only 401 is documented as free.
2. Does a presigned PUT or UploadPart enforce a signed `Content-Length` and a signed `If-None-Match: *`?
3. Are Worker requests blocked by a WAF rate-limiting rule billed as Worker requests?
4. Are the parts of an incomplete multipart upload billed as storage until the default 7-day abort?

This spike has no sandbox account (H5 L01), so none of these was emulated. A local emulator (Miniflare) cannot answer billing questions, so an "emulated" variant would prove nothing here. They belong in C2's `[SB]` kit.

## Plan for v1 (after A0, E1 and H2)

1. Replace these `PARAMS` rows with A0's measured values per file: `worker_req_per_file`, `cpu_ms_per_req`, `d1_rows_w_per_file`, `d1_rows_r_per_file`, `queue_msgs_per_file`, `classB_per_file`, `meta_objects_per_file`.
2. Replace these rows with E1 and H2 values: `mean_file_bytes`, `share_bytes_large`, `share_files_large`, `devices` and `people`.
3. Add the owner's pool (H2 C4) as a tier.
4. Set `--bud-abuse` to the confirmed value.
5. Narrow each range in `sensitivity()` to A0's measured spread.
6. Re-run the script. The ±25 % test then uses real spreads, not guessed ones.
7. After the C2 `[SB]` run, add the observed Cloudflare invoice lines as a new self-check.
