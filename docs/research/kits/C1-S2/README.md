# Kit C1-S2: lease race on real D1 and real Durable Objects (sandbox account)

- **Spike:** C1-S2 "Claim race: 50 concurrent claims, 10,000 trials, D1 vs DO" (workstream C1, see `docs/research/PLAN.md`, section "C1.")
- **Exec tag:** CT/SB. The CT (emulated) leg ran on 2026-10-06; see `spikes/C1-S2/README.md`. This kit is the SB leg. It uses the dedicated **sandbox** Cloudflare account (H1, long-lead item L01), never production.
- **Prepared by / date:** C1 spike runner (agent), 2026-10-06
- **Who runs it:** the owner on a laptop, or an agent on a machine that can reach the Worker's hostname. The cloud container cannot reach `*.workers.dev` (H5, L02), so from a container use a route on the sandbox domain instead (step 5).
- **Time needed:** about 20 min hands-on, plus 1–2 h of unattended running (two runs of 10,000 trials; the time depends on your round-trip time to Cloudflare).
- **Data-handling class:** `SYN → results`. The driver sends random dedup IDs it generates itself. Nothing from the family is used.
- **Run together with:** kits C1-S3 and C1-S4. All three use the same deployed Worker (`spikes/C1-S1/worker/`). Do steps 1–6 once.

## Purpose

Check that the lease ("claim") insert the ingest protocol uses gives exactly one winner when 50 devices race for the same dedup ID, on real D1 and on real SQLite-backed Durable Objects, and record the latency each one shows from a real client.

## Hypothesis

- **H1 (D1):** a single `D1Database.batch()` holding `INSERT … SELECT … WHERE NOT EXISTS (live lease)` plus an event-log insert gives **exactly one winner in every one of 10,000 trials** of 50 concurrent requests, including the 1,000 trials (every 10th) that first plant an expired lease, so the race is a takeover. Afterwards no dedup ID has two live leases.
- **H2 (DO):** the same logic inside a SQLite-backed Durable Object (`transactionSync`, 16 shards keyed by the first hex digit of the ID) gives the same result.
- **H3 (latency):** record the client-observed p50 and p99 per request for each store. PLAN sets no threshold, so this is context for C1-S3 and the D1-vs-DO choice, not a pass criterion.
- **H4 (overload):** record any non-200 response. D1 and DO return an "overloaded" error when one object's queue is full (C1 note C27, C30). Any such error is a finding.

## Decision it informs

| If the result is… | Then… |
|---|---|
| **Pass** (PLAN: "exactly one winner every time") on D1 | ADR-0010 keeps leases in D1 (C1 note F2). |
| D1 fails (two winners in any trial, or a duplicate live lease afterwards) and DO passes | Move the `uploads` (lease) table into DO shards (C1 note F2 fallback). Raise it as a defect in the D1 SQL first: a double winner in a single-threaded database means the statement is wrong, not D1. |
| D1 passes but shows "overloaded" errors or a p99 far above DO | Feed into the C1-S3 result and the F2 throughput arithmetic before choosing. |
| Both fail | The lease design is wrong. A3 must review it (the lease is advisory, so a double lease costs bandwidth, not data; record it). |
| **No result** (no sandbox, Worker unreachable) | ADR-0010 cites only the emulated leg, labelled "emulated, not real Cloudflare". |

## Budget IDs cited

None. PLAN's criterion for C1-S2 is "exactly one winner every time; record p50/p99", with no budget ID. Do not invent a latency threshold.

## Equipment

| Item | Exact model or version | Why | Have it? |
|---|---|---|---|
| Sandbox Cloudflare account on **Workers Paid** (L01) | — | SB rule; Paid plan limits (Free allows 100,000 requests/day, and this kit makes about 1 million) | Owner action (L01) |
| `wrangler` logged in to the sandbox account | 4.143.0 (pinned in `spikes/C1-S1/worker/package-lock.json`) | Creates D1, deploys the Worker | `npx wrangler@4.143.0 login` |
| Machine with Python ≥ 3.9 (stdlib only) and Node ≥ 22 | e.g. Python 3.11, Node 22 | Runs `c1s2.py` and wrangler | — |
| Wired or stable Wi-Fi connection | — | 50 parallel connections for an hour; flaky Wi-Fi shows up as client errors | — |

**Software and files needed:** this repository: `spikes/C1-S1/worker/` (the Worker) and `spikes/C1-S2/c1s2.py` (the driver).

## Before you start

- [ ] Confirm in the dashboard that you are in the **sandbox** account. Write down the account ID.
- [ ] Check that a billing alert exists (L01). Expected use is about 1 million Worker requests and 0.5 million DO requests, inside the Paid plan's included amounts (C4 note; not re-checked here).
- [ ] Pick a random token for the Worker and keep it in an environment variable: `export SPIKE_TOKEN=$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')`. Do not write it into any file in the repository.
- [ ] Write down your location (city) and connection type. Latency depends on them.

## Procedure

1. Copy `spikes/C1-S1/worker/` to a scratch folder outside the repository and run `npm ci` there. **You should see:** no errors; `npx wrangler --version` prints 4.143.0.
2. Create the database: `npx wrangler d1 create c1-spikes`. **You should see:** a `database_id`. Put it in the scratch `wrangler.toml` in place of `00000000-0000-0000-0000-0000000000c1`.
3. Edit the scratch `wrangler.toml`:
   - delete the whole `[vars]` block and the `local_dev = …` line;
   - set the R2 `bucket_name` to the bucket created in kit C1-S4 step 1 (`c1s4-sandbox`), or create it now with `npx wrangler r2 bucket create c1s4-sandbox`;
   - add `workers_dev = true` (or a route on the sandbox domain, see step 5);
   - add `[observability]` with `enabled = true`, so per-invocation logs are kept.

   **You should see:** the file still has the `[[durable_objects.bindings]]` and `[[migrations]]` blocks for `LeaseShard`.
4. Set the secrets: `printf %s "$SPIKE_TOKEN" | npx wrangler secret put SPIKE_TOKEN`. C1-S2 does not use R2, but kit C1-S4 needs `S3_BASE`, `S3_REGION`, `S3_AK` and `S3_SK` (see kit C1-S4 step 2), so set them now if you run C1-S4 too.
5. Deploy: `npx wrangler deploy`. **You should see:** a URL such as `https://c1spikes.<subdomain>.workers.dev`. From a machine that cannot reach `workers.dev`, add a route on the sandbox domain instead (for example `c1.<sandbox domain>/*`) and use that URL. Export it: `export W=https://…`.
6. Check it: `curl -s $W/health` prints `{"ok":true}`, and `curl -s $W/d1/init` prints `{"error":"forbidden"}` (the token check works). **You should see:** both.
7. Run the D1 race:
   ```sh
   cd spikes/C1-S2
   python3 c1s2.py --worker "$W" --store d1 --concurrency 50 --trials 10000 --out results/sb-d1.json | tee results/sb-d1.log
   ```
   **You should see:** a progress line every 1,000 trials with `winners 1`. At the end, a JSON summary with `winners_histogram` `{"1": 10000}`, `bad_trial_count` 0 and `post_check.dup_ids` 0.
8. Run the DO race: the same command with `--store do` and `--out results/sb-do.json`. **You should see:** the same shape of summary.
9. In the dashboard, open the Worker's **Metrics** tab and write down the error count and the "CPU Time per execution" p50/p99 for the run window. Open **Durable Objects** and **D1** metrics and note any errors.

**Stop and record "No result" if:** the account is not clearly the sandbox; the Worker answers anything other than 200 to `/health`; or more than 1 % of requests fail with client-side connection errors (your network, not Cloudflare: retry from a wired connection).

## Cleaning up

1. `npx wrangler delete` in the scratch folder (removes the Worker and its Durable Object namespace).
2. `npx wrangler d1 delete c1-spikes`.
3. Delete the scratch folder. Unset `SPIKE_TOKEN`.

## Data handling

Class `SYN → results`. The results hold counts, HTTP status codes, latencies and random dedup IDs. No secrets and no family data. `results/sb-*.json` and `.log` may be committed to `spikes/C1-S2/results/`. Never commit the token or the scratch `wrangler.toml` with the real `database_id` (harmless, but keep account identifiers out of the repository).

## Results

Copy this section into `docs/research/kits/C1-S2/results.md` and fill it in. Do not edit numbers afterwards; add a note instead.

- **Run by / date / place / connection:**
- **Account (sandbox? yes/no), Workers plan:**
- **Tool versions:** Python, Node, wrangler
- **Emulator or VM used instead of real Cloudflare?** No (this is the real leg). Emulated result for comparison: `spikes/C1-S2/README.md`.

| Store | Trials × concurrency | Winners histogram | Bad trials | Duplicate live leases after | Non-200 responses | Client errors | p50 / p99 (ms, client) | Wall time |
|---|---|---|---|---|---|---|---|---|
| D1 | 10,000 × 50 | | | | | | | |
| DO (16 shards) | 10,000 × 50 | | | | | | | |

| Pass criterion | Budget ID | Measured value | Pass / Fail / No result |
|---|---|---|---|
| Exactly one winner in every trial (D1) | — | | |
| Exactly one winner in every trial (DO) | — | | |
| p50/p99 recorded for both | — | | |

- **Dashboard:** Worker errors, CPU p50/p99, D1 errors, DO errors:
- **Overall:** Pass | Fail | No result
- **Surprises:**
- **Follow-ups for the workstream:**
