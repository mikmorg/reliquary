# Kit C1-S4: presign 200 upload parts in one request, and Ed25519 verify cost, on real Workers (sandbox account)

- **Spike:** C1-S4 "Presign 200 parts in one request" (workstream C1, see `docs/research/PLAN.md`, section "C1.")
- **Exec tag:** SB. Uses the dedicated **sandbox** Cloudflare account (H1, long-lead item L01), never production. An emulated leg (local workerd) and a CPU micro-benchmark in Node ran on 2026-10-06; see `spikes/C1-S4/README.md`.
- **Prepared by / date:** C1 spike runner (agent), 2026-10-06
- **Who runs it:** the owner on a laptop, or an agent on a machine that can reach the Worker's hostname **and** `https://<ACCOUNT_ID>.r2.cloudflarestorage.com` (both were blocked from the cloud container on 2026-10-06).
- **Time needed:** about 30 min hands-on, plus about 15 min waiting for dashboard metrics to appear.
- **Data-handling class:** `SYN → results`. Only random bytes are uploaded.
- **Run together with:** kits C1-S2 and C1-S3 (same Worker code). Do kit C1-S2 steps 1–6 first.

## Purpose

Check that one Worker request can presign 200 multipart part URLs well inside the Workers Paid CPU limit, that those URLs work from plain `curl` against real R2, and how much CPU one Ed25519 signature check costs, because every authenticated API request will do one (BUD-CPU-REQ).

## Hypothesis

- **H1 (CPU):** presigning 200 UploadPart URLs with aws4fetch 1.0.20 in one request uses far less than the Paid default of 30 s CPU (Workers limits page). The emulated leg suggests tens of milliseconds; only the dashboard's "CPU Time per execution" on real Workers counts.
- **H2 (URLs work):** parts 1, 2 and 200 of a real R2 multipart upload, sent by `curl` to the presigned URLs, return 200, and the upload completes with the right size.
- **H3 (BUD-CPU-REQ):** one WebCrypto Ed25519 `verify` costs **< 1 ms CPU** on real Workers.
- **H4 (subrequests):** presigning makes no subrequests (C1 note C1). The dashboard shows 0 subrequests for the presign Worker.

## Decision it informs

| If the result is… | Then… |
|---|---|
| **Pass** (PLAN: "within Paid-plan CPU limits; URLs work from curl") | ADR-0010 keeps windowed presigning of part URLs by the Worker (C1 note F4). The window size is set by BUD-REVOKE, not by CPU. |
| H1 fails (presigning 200 parts is too expensive) | Presign smaller windows, or mint one scoped temporary credential per upload instead (C1 note, Questions row 17). |
| H2 fails (presigned UploadPart rejected by R2) | Uploads of large files go through the Worker binding, bounded by the request-body limit (C1 note C20). Cross-check with kit C1-S1 H4. |
| H3 fails (Ed25519 verify ≥ 1 ms) | D3 reconsiders the request-auth scheme (e.g. HMAC session keys after one signature check). |
| **No result** | ADR-0010 cites the emulated leg and the Node micro-benchmark, labelled as such. |

## Budget IDs cited

- **BUD-CPU-REQ** (request-signature verification < 1 ms CPU): H3.
- **BUD-REVOKE** is context only: it caps how many parts are worth presigning at once (C1 note F4), not what this kit measures.

## Equipment

| Item | Exact model or version | Why | Have it? |
|---|---|---|---|
| Sandbox account on **Workers Paid** (L01) | — | Free allows only 10 ms CPU per request | Owner action |
| R2 bucket `c1s4-sandbox` and an R2 API token, **Object Read & Write, scoped to that bucket only** | — | The Worker presigns with it; the URLs are tested against it | Create in steps 1–2 |
| `wrangler` | 4.143.0 | Deploys three copies of the Worker | — |
| Python ≥ 3.9 and `curl` | — | `c1s4.py` | — |

**Software and files needed:** `spikes/C1-S1/worker/` (the Worker) and `spikes/C1-S4/c1s4.py`.

## Before you start

- [ ] Confirm the sandbox account. Write down the account ID.
- [ ] Have `SPIKE_TOKEN` and the scratch copy of the Worker from kit C1-S2 ready.

## Procedure

1. Create the bucket: `npx wrangler r2 bucket create c1s4-sandbox`. **You should see:** it in `npx wrangler r2 bucket list`.
2. In the dashboard, create an R2 API token (Object Read & Write, scoped to `c1s4-sandbox`). In the scratch Worker folder, set:
   ```sh
   printf %s "https://<ACCOUNT_ID>.r2.cloudflarestorage.com/c1s4-sandbox" | npx wrangler secret put S3_BASE
   printf %s "auto" | npx wrangler secret put S3_REGION
   printf %s "<access key id>" | npx wrangler secret put S3_AK
   printf %s "<secret access key>" | npx wrangler secret put S3_SK
   npx wrangler deploy
   ```
   **You should see:** the deploy succeed. (`S3_BASE` is not secret, but keeping all four together is simpler.)
3. Run the functional check and the in-Worker timings:
   ```sh
   cd spikes/C1-S4
   python3 c1s4.py --worker "$W" --reps 50 --out results/sb.json | tee results/sb.log
   ```
   **You should see:** `curl_check.part_status` showing `HTTP/1.1 200 OK` (or `HTTP/2 200`) for parts 1, 2 and 200, and `size_ok: true`. The `perf_ms` numbers in this file are **not CPU time** on real Workers: deployed Workers only advance timers on I/O (Workers "Performance and timers" page), so they may read 0. Record them, but do not use them.
4. Deploy three single-purpose copies, so that each one's dashboard CPU chart contains only one kind of request:
   ```sh
   for n in c1s4-noop c1s4-presign c1s4-ed25519; do npx wrangler deploy --name $n; done
   ```
   Set the same four `S3_*` secrets and `SPIKE_TOKEN` on `c1s4-presign` (`npx wrangler secret put … --name c1s4-presign`) and `SPIKE_TOKEN` on the other two. **You should see:** three Worker URLs. Export them as `WN`, `WP` and `WE`.
5. Send 300 requests to each:
   ```sh
   H="x-spike-token: $SPIKE_TOKEN"
   for i in $(seq 300); do curl -s -o /dev/null -H "$H" "$WN/noop"; done
   for i in $(seq 300); do curl -s -o /dev/null -H "$H" "$WP/presign-many?n=200&key=c1s4/cpu&uploadId=x&urls=0"; done
   for i in $(seq 300); do curl -s -o /dev/null -H "$H" "$WE/bench/ed25519?n=1000"; done
   ```
   **You should see:** no output (every call returns quickly). Spot-check one call of each with `-w '%{http_code}\n'`: 200.
6. Wait about 15 minutes. In the dashboard, open each Worker's **Metrics** tab, choose a time range covering step 5, and write down **CPU Time per execution** p50, p75, p99 and p999, the request count, errors and subrequests.
7. Compute: presign CPU per call = `c1s4-presign` p50 and p99. Ed25519 verify CPU ≈ (`c1s4-ed25519` p50 − `c1s4-noop` p50) ÷ 1,000. Write both in the results table.

**Stop and record "No result" if:** the account is not clearly the sandbox, or the R2 host is unreachable from the machine (H2 cannot run; H1 and H3 still can).

## Cleaning up

1. `npx wrangler delete --name c1s4-noop`, the same for `c1s4-presign` and `c1s4-ed25519`.
2. Abort any open multipart uploads and delete every object under `c1s4/` in `c1s4-sandbox`, then `npx wrangler r2 bucket delete c1s4-sandbox`.
3. Revoke the R2 token from step 2.

## Data handling

Class `SYN → results`. The results contain status lines, sizes, ETags of random data and CPU figures. The presigned URLs in `sb.json`'s raw response are not written to the results (`urls` are only counted), but a log may still show the account ID in the R2 hostname: redact it before committing `results/` to `spikes/C1-S4/results/`.

## Results

Copy this section into `docs/research/kits/C1-S4/results.md` and fill it in. Do not edit numbers afterwards; add a note instead.

- **Run by / date / place:**
- **Account (sandbox? yes/no), Workers plan, `limits.cpu_ms` (default unless changed):**
- **Emulator used instead of real Workers?** No (this is the real leg). Emulated and Node results for comparison: `spikes/C1-S4/README.md`.

| Worker | Requests | CPU p50 / p75 / p99 / p999 (ms) | Errors | Subrequests |
|---|---|---|---|---|
| `c1s4-noop` | 300 | | | |
| `c1s4-presign` (200 URLs per call) | 300 | | | |
| `c1s4-ed25519` (1,000 verifies per call) | 300 | | | |

| Pass criterion | Budget ID | Measured value | Pass / Fail / No result |
|---|---|---|---|
| Presign 200 parts within Paid-plan CPU limits (30 s default) | — (PLAN) | | |
| URLs work from curl (parts 1, 2, 200; complete; size) | — (PLAN) | | |
| Ed25519 verify < 1 ms CPU | BUD-CPU-REQ | | |

- **Overall:** Pass | Fail | No result
- **Surprises:**
- **Follow-ups for the workstream:**
