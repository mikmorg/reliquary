# Kit G2-S1 (real-R2 leg): R2 fidelity check against the Cloudflare sandbox

- **Spike:** G2-S1 "R2 fidelity" (workstream G2, see `docs/research/PLAN.md`, section "G2."). This kit is the **[SB] leg**. The local leg (Miniflare, RustFS, versitygw, SeaweedFS, Garage and moto) already ran in the cloud container on 2026-09-29. It is labelled "emulated, not real R2/Cloudflare", and its code and results are in `spikes/G2-S1/`.
- **Exec tag:** SB. It uses the dedicated sandbox Cloudflare account (H1) and never production.
- **Prepared by / date:** G2 spike runner (agent), 2026-09-29
- **Who runs it:** an agent in a container that can reach `*.r2.cloudflarestorage.com` and `api.cloudflare.com`, or the owner on a laptop. It needs the owner to create the sandbox account and one bucket-scoped R2 token first.
- **Time needed:** about 10 min hands-on, plus the script run. The local legs took 4.5–30 s each; R2 round trips will be slower. One run sends about 750 S3 requests with about 64 MB of request bodies.
- **Data-handling class:** `SYN → results`. The script uploads only random bytes that it generates itself.

## Purpose

Run **the same script** that ran against the local emulators against a real R2 bucket, so that every difference between Miniflare's local R2 S3 endpoint and real R2 is measured, not assumed. This kit decides whether Miniflare stays the A0 local target and which behaviours must be marked "SB-only" in A0's list of emulator-vs-R2 differences.

## Hypothesis

Real R2 behaves like Miniflare's local endpoint on every check the protocol relies on: presigned PUT and UploadPart, signature, expiry and tamper rejection, If-None-Match on PutObject including under a 16-way race, multipart part-size rules, part replacement and ETag checks, and Abort. The documented exceptions are the ones Miniflare admits in its source: ListParts, ListMultipartUploads, lifecycle, flexible checksums, `aws-chunked`, and `100 Continue`. On these R2 is expected to behave "better". The hypothesis fails if R2 differs on any check that Miniflare passes.

## Decision it informs

| If the result is… | Then… |
|---|---|
| **Pass**: no difference between R2 and Miniflare on any protocol-relied check (PLAN: "Pick the local target with no difference in any behaviour the protocol relies on; document every difference") | Miniflare (wrangler dev + `local_dev.experimental_s3_credentials`) is confirmed as the A0 local target. The documented gaps go into the A0 difference list and ADR-0035 as "SB-only". |
| **Fail**: R2 differs on a relied-on check | Record each difference in the A0 difference list. If RustFS, versitygw or SeaweedFS matches R2 on that check, use it as the differential target for that behaviour. Otherwise the behaviour is SB-only and A0 must not claim it from local runs. |
| **No result** (no sandbox account, host blocked) | Miniflare stays the provisional target. Every "R2 (documented)" cell in the comparison table stays "documented, not measured". ADR-0035 notes that the check is outstanding. |

Checks whose R2 answer is unknown today, so that R2 itself is the finding (all shared with C1-S1 and A3):

- **T22:** If-None-Match sent on a presigned PUT but *not* signed (A3 open question 2).
- **T37 and T38:** Complete twice, UploadPart after Complete, and If-None-Match on CompleteMultipartUpload. R2's docs list no conditional headers for Complete.
- **T32 and T33:** R2's error code for unequal part sizes. Miniflare enforces the rule but answers **404 NoSuchUpload**, because its S3 layer maps every simulator 500 to NoSuchUpload. A client that treats NoSuchUpload as "upload gone, start again" would react differently.
- **T43:** an unsigned wrong `x-amz-checksum-sha256` on a presigned PUT.
- **T47:** `x-amz-checksum-sha256` signed into a presigned URL with the body tampered. Miniflare **stores the tampered body**, while SeaweedFS and versitygw reject it.
- **T45 and T46:** `Expect: 100-continue`, and `Transfer-Encoding: chunked` bodies.
- **W04:** binding-created multipart with S3 UploadPart parts (hybrid step 6).
- **T26 and T27 (race):** `r2/platform/limits.mdx` limits concurrent writes to the same key to 1 per second, and excess writes get HTTP 429. On R2, record how many losers get 412 and how many get 429. Exactly one 200 per round is still the pass condition.
- **T35, T54:** ListParts, ListMultipartUploads and lifecycle configuration. R2 implements them; Miniflare answers 501.

## Budget IDs cited

- **BUD-REVOKE** ("outstanding URLs expire within 15 min"). Only the expiry mechanism is checked here: T08 (expired URL rejected) and T09 (604,800 s accepted, 604,801 s rejected). The 60 s revocation propagation is D3-S5's job, not this kit's.
- No other budget applies. This is a fidelity check, not a performance check. Do not record R2 latency from this script as a measurement of anything.

## Equipment

| Item | Exact model or version | Why | Have it? |
|---|---|---|---|
| Sandbox Cloudflare account (H1), R2 enabled | — | SB rule: never production | Owner action (`docs/research/sources.md`, allowlist request) |
| One R2 bucket, e.g. `g2s1-sandbox`, location hint of the owner's choice | — | Target | Create in step 2 |
| R2 API token: **Object Read & Write**, scoped to that bucket only | — | S3 access key and secret for the script | Create in step 3 |
| Machine with Python ≥ 3.9 (stdlib only), Node ≥ 22 | e.g. Python 3.11.15, Node 22.22.2 (what the local legs used) | Runs `fidelity.py`, `sdk_quirks.mjs` and `wrangler` | Yes |
| Network access to `https://<ACCOUNT_ID>.r2.cloudflarestorage.com` and `api.cloudflare.com` | — | Blocked in the cloud container on 2026-09-29 | Allowlist (H1) or run on a laptop |

**Software and files needed:** `spikes/G2-S1/` (this repo): `fidelity.py`, `compare.py`, `sdk/sdk_quirks.mjs`, `worker/` (wrangler 4.143.0 pinned in `package.json`), and `results/` from the local legs.

## Before you start

- [ ] Confirm that the account is the **sandbox** account (the dashboard account name), not production.
- [ ] Write down the account ID. The S3 endpoint is `https://<ACCOUNT_ID>.r2.cloudflarestorage.com`.
- [ ] Do not add lifecycle rules or bucket locks before the run. The script adds a lifecycle configuration itself in T54.
- [ ] Keep the token secret out of the repo, shell history files and the results. Use environment variables.

## Procedure

1. On the machine, check reachability: `curl -sS -o /dev/null -w '%{http_code}\n' https://<ACCOUNT_ID>.r2.cloudflarestorage.com/`. **You should see** a 4xx code such as 400 or 403, which means TLS and routing work. A connection or TLS error means the host is blocked: stop and record "No result: host blocked".
2. Create the bucket, either in the dashboard or with `npx wrangler@4.143.0 r2 bucket create g2s1-sandbox` (logged in to the sandbox account). **You should see** the bucket listed.
3. Create an R2 API token with **Object Read & Write** on `g2s1-sandbox` only. Put the values in the environment: `export R2_AK=… R2_SK=… R2_ACCOUNT=…`. **You should see** the token in the dashboard with the bucket scope.
4. Run the fidelity script:
   ```sh
   cd spikes/G2-S1
   python3 fidelity.py --name r2 --endpoint "https://$R2_ACCOUNT.r2.cloudflarestorage.com" \
     --bucket g2s1-sandbox --region auto --ak "$R2_AK" --sk "$R2_SK" --out results/r2.json | tee results/r2.log
   ```
   **You should see** one line per check (T01…T54) and no `ERR-` lines. T45 and T46 print "skipped: https target", because the raw-socket checks are plain-HTTP only. If they matter, run them later with `curl -v --http1.1 -H 'Expect: 100-continue'` against a presigned URL.
5. Run the SDK-defaults check: `cd sdk && npm ci && node sdk_quirks.mjs r2 "https://$R2_ACCOUNT.r2.cloudflarestorage.com" g2s1-sandbox auto "$R2_AK" "$R2_SK" > ../results/sdkjs-r2.jsonl`. **You should see** seven JSON lines (S1–S7).
6. **Hybrid leg** (W01–W05 against real R2; optional but recommended). In `worker/wrangler.toml`, set the bucket to `g2s1-sandbox`, add `remote = true` to the `[[r2_buckets]]` entry, remove its `local_dev` line, and set `S3_BASE = "https://<ACCOUNT_ID>.r2.cloudflarestorage.com/g2s1-sandbox"`, `S3_AK` and `S3_SK` (as `.dev.vars` secrets, not in the toml). Then run `npx wrangler dev` and `python3 fidelity.py … --worker http://127.0.0.1:8787 --only worker`. **You should see** W01–W05 results. Note: remote bindings modify real data and are billed normally (Cloudflare docs, "Workers local development").
7. Build the comparison: `python3 compare.py results/miniflare.json results/rustfs.json results/versitygw.json results/seaweedfs.json results/r2.json > results/comparison-with-r2.md`.
8. For every row where the `r2` column differs from `miniflare`, add a line to "Differences" in the results file below.

**Stop and record "No result" if:** the account is not clearly the sandbox; the bucket-scoped token cannot be created; or step 1 fails.

## Cleaning up

1. Delete every object under `g2s1/` and `sdk/` (the script's prefixes), then abort any open multipart uploads (T35 deliberately leaves one; `ListMultipartUploads` finds it), and delete the bucket: `npx wrangler@4.143.0 r2 bucket delete g2s1-sandbox`.
2. Revoke the R2 API token in the dashboard.
3. Remove the hybrid `.dev.vars` file.

## Data handling

Class `SYN → results`. The script uploads only `os.urandom` bytes and fixed test strings. The results contain status codes, error codes, booleans and counts: no data, keys or secrets. Keys contain a random run ID and nothing else. The results may be committed to `spikes/G2-S1/results/`. Never commit the token.

## Results

Copy this section into `docs/research/kits/G2-S1/results.md` and fill it in. Do not edit numbers afterwards; add a note instead.

- **Run by / date / place:**
- **Account (sandbox? yes/no), bucket, location hint:**
- **Tool versions:** Python, Node, wrangler (`npx wrangler --version`)
- **Emulator or VM used instead of real R2?** No (this is the real leg)

| Check | R2 result | Miniflare result (2026-09-29) | Same? | Relied on by (A3 / CE / C1) |
|---|---|---|---|---|
| T01–T14 presign, auth, expiry | | see `spikes/G2-S1/results/comparison.md` | | A3, D3 |
| T20–T27 conditional create, races | | | | A3 |
| T30–T39 multipart | | | | A3, CE §8 |
| T40–T49 integrity headers | | | | CE, C1-S1 |
| T50–T54 list, delete, POST, lifecycle | | | | A3, A8 |
| S1–S7 SDK defaults | | | | A0 homelab client |
| W01–W05 hybrid (optional) | | | | A0 |

| Pass criterion | Budget ID | Measured value | Pass / Fail / No result |
|---|---|---|---|
| No difference between R2 and the chosen local target on any protocol-relied check | — | | |
| Expired presigned URL rejected; 604,800 s accepted, > 604,800 s rejected | BUD-REVOKE (expiry mechanism only) | | |

- **Overall:** Pass | Fail | No result
- **Differences (one line each: check, R2, Miniflare, impact):**
- **Surprises:**
- **Follow-ups for the workstream:**
