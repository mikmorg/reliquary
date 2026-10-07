# Kit C1-S1: R2 behaviour on the sandbox account (real R2)

- **Spike:** C1-S1 "R2 behaviour (one run, Wave 1)" (workstream C1, see `docs/research/PLAN.md`, section "C1."). Hypotheses H1–H14 are worded as in `docs/research/c1-cloudflare-control-plane.md`, section "Spikes".
- **Exec tag:** SB. It uses the dedicated **sandbox** Cloudflare account (H1, long-lead item L01), never production.
- **Prepared by / date:** C1 spike runner (agent), 2026-10-06
- **Who runs it:** the owner on a laptop, or an agent in a container that can reach `*.r2.cloudflarestorage.com` and `api.cloudflare.com`. Three steps need the Cloudflare dashboard or a logged-in `wrangler`: adding a bucket lock rule, deleting an API token, and cleaning up.
- **Time needed:** about 45 min hands-on. Cleanup may need a wait of up to 1 day, because a bucket with locked objects cannot be emptied until the lock expires or the rule is removed (step 12).
- **Data-handling class:** `SYN → results`. The scripts upload only random bytes they generate themselves. Nothing from the family is used.
- **Emulated leg already run (NOT real R2/Cloudflare):** on 2026-10-06 the same script ran twice against Miniflare's local R2 S3 endpoint (16:58Z and 20:15Z; the runs agree except for the rejection mode of C07). Code and results are in `spikes/C1-S1/`. Miniflare cannot answer H6, H8, H9, H11 or H13, and its answers to the rest prove nothing about R2. That is why this kit exists.

## Purpose

Find out what real R2 enforces on presigned uploads and multipart completion, and how bucket locks and token revocation behave. ADR-0010 and the ingest protocol (ADR-0009) can then rely on measured behaviour instead of undocumented assumptions.

## Hypothesis

Each line is the hypothesis, followed by the check that tests it. "T" checks are in `spikes/G2-S1/fidelity.py` (kit G2-S1) and "C" checks in `spikes/C1-S1/c1s1.py`. Where a G2-S1 check already covers a hypothesis it is reused, not repeated.

| H | Hypothesis (expected on real R2) | Checks |
|---|---|---|
| H1 | A presigned PUT with a signed `If-None-Match: *` returns 412 on an existing key, and the object is unchanged. A client that drops the signed header gets 403. | T22–T27; C01, C02 |
| H2 | CompleteMultipartUpload with `If-None-Match: *` on an existing key fails. Record whether the upload is then aborted (release note 2023-08-11) or survives. The binding's `complete()` takes no condition, so it overwrites. | T38; C03 |
| H3 | A presigned **POST** for CreateMultipartUpload and for CompleteMultipartUpload is rejected. The R2 docs list GET, HEAD, PUT and DELETE only. | T53 (form POST); C04, C05 |
| H4 | Presigned UploadPart works. A signed `Content-MD5` rejects a tampered part body. | T30; C06, C07 |
| H5 | A signed Content-Length rejects a shorter or a longer body. | T49; C08 |
| H6 | A signed `x-amz-checksum-sha256` on a single PUT rejects a tampered body. The binding `put()` with a wrong `sha256` throws and stores nothing. | T41, T43, T47; C09, C10 |
| H7 | Single-PUT ETag = MD5(body). Part ETag = MD5(part). Multipart object ETag = MD5(concatenated binary part MD5s) + `-N`. | C11, C12 |
| H8 | A prefix `AbortIncompleteMultipartUpload` rule longer than 7 days overrides the default 7-day abort, or does not. | **Kit A3-S3, hypothesis H3** (10-day rule, 9-day calendar). Not repeated here. |
| H9 | An Age bucket lock on a prefix blocks overwrite by PUT, presigned PUT and Complete. It also blocks DELETE (expected), and it does or does not block in-progress uploads and Abort. | C17 (`H9-before`, `H9-after`) |
| H10 | A presigned URL whose expiry passes while the body is still being sent completes (expiry is checked when the request arrives), or fails. | C13 |
| H11 | After the parent token is deleted, presigned URLs and temporary credentials it signed stop working. Measure the delay. | C18 (`H11-mint`, `H11-poll`) |
| H12 | The binding `put()` with `onlyIf` `If-None-Match: *` refuses an existing key, both as `Headers` and as `{etagDoesNotMatch: "*"}` (workerd #2572 wildcard history). | W02, W03; C14 |
| H13 | A locally signed temporary credential with `actions` and `prefixPaths` allows only the listed actions under the listed prefix, and is refused after its `exp`. | C15, C16 |
| H14 | S3 CreateMultipartUpload with `If-None-Match: *` on an existing key returns 412 (R2 release note 2022-05-27; Miniflare returns 200). Added at the analyst's request to close a docs conflict; low decision value. | T39 (G2-S1, run in step 5) |

## Decision it informs

| If the result is… | Then… |
|---|---|
| **Pass** on H1 and H12 (create-only works on single PUT, presigned and binding) | ADR-0010 signs `If-None-Match: *` into every presigned PUT and uses `onlyIf` for `meta/` writes, as defence in depth (D1 SR-08). Per-upload keys stay mandatory (OD-04). |
| H2: Complete refuses an existing key | Record whether the parts survive. If they do not (upload aborted), never send the condition on Complete, because a failed condition would throw away a whole upload. Per-upload keys make it unnecessary anyway. |
| H2 fail (Complete overwrites, as in Miniflare) | Per-upload keys are the only protection for multipart objects. This is already the design (A3), so record the gap in ADR-0010. |
| H3: presigned POST accepted | A device could complete without the Worker (Ente's pattern). ADR-0010 still has the Worker complete, because it owns the `staged` transition (A3 F1), but A3's claim C17 ("the client cannot run them from presigned URLs") is corrected. |
| H3: presigned POST rejected | A3 C17 is confirmed. Create and Complete go through the Worker. |
| H4, H5 pass | Sign `Content-MD5` into every UploadPart and single PUT URL, and Content-Length into single PUT URLs (SR-09). |
| H6 fail on presigned PUT | Do not rely on `x-amz-checksum-sha256` for presigned uploads. Integrity is checked by the homelab anyway (SR-04). |
| H7 differs from the formulas | The device cannot verify the completed ETag locally. Drop that cheap check from ADR-0010 F4 step 3. |
| H9: the lock blocks overwrite by Complete, and does not block in-progress uploads or the homelab's cleanup outside the lock window | An Age lock on `staging/` becomes an optional defence-in-depth setting (owner decision). Otherwise no lock on the ingest bucket. |
| H10: URL expiry mid-body fails the upload | Part size must be small enough to finish within the URL lifetime on the slowest expected uplink. ADR-0010 F4 sizes windows and parts from that. |
| H11: delay ≤ 60 s for temp credentials and URLs die too | Rolling the parent token is a usable kill switch for BUD-REVOKE. |
| H11: presigned URLs survive token deletion | Outstanding URLs are bounded only by their lifetime (≤ 15 min by design). Record it against BUD-REVOKE. |
| H13 pass | The homelab gets Worker-minted, action- and prefix-scoped temporary credentials (C1 note F5). |
| H13 fail | The homelab uses a long-lived bucket-scoped token (C1 note fallback). |
| H14 either way | Record it in ADR-0010's limits list. No design change: Create always runs in the Worker on a fresh per-upload key. |
| **No result** (no sandbox, host blocked) | Every H stays "documented, not measured" in ADR-0010. Nothing in the design depends on a positive result, because per-upload keys plus homelab verification are the safety net. |

## Budget IDs cited

- **BUD-REVOKE** ("no new presigned URLs within 60 s; outstanding URLs expire within 15 min"): H10 and H11. H11 measures the delay after a token is deleted. The "no new URLs within 60 s" part is the Worker's own check and belongs to D3-S5.
- No other budget applies. Latencies in the logs are context only. Do not record them as measurements of anything.

## Equipment

| Item | Exact model or version | Why | Have it? |
|---|---|---|---|
| Sandbox Cloudflare account with R2 enabled (L01) | — | SB rule: never production | Owner action (H5 L01) |
| A **dedicated** bucket `c1s1-sandbox` | — | The kit adds a bucket lock rule, and a bucket cannot be emptied while lock rules exist. Do not share it with G2-S1 or A3-S3. | Create in step 2 |
| R2 API token **A**: Object Read & Write, scoped to `c1s1-sandbox` | — | Used by the Worker (presigning) and by the script | Create in step 3 |
| R2 API token **B**: Object Read & Write, scoped to `c1s1-sandbox`, **disposable** | — | H11 deletes it | Create in step 3 |
| `wrangler` 4.143.0 logged in to the sandbox account (`npx wrangler@4.143.0 login`) | 4.143.0 (pinned in `spikes/C1-S1/worker/package-lock.json`) | Runs the Worker with a remote R2 binding; adds and removes the lock rule | — |
| Machine with Python ≥ 3.9 (stdlib only) and Node ≥ 22 | e.g. Python 3.11, Node 22.22 (the emulated leg) | Runs `c1s1.py` and `wrangler` | — |
| Network access to `https://<ACCOUNT_ID>.r2.cloudflarestorage.com` and `https://api.cloudflare.com` | — | Both were blocked from the cloud container on 2026-10-06 | Allowlist (H1) or run on a laptop |

**Software and files needed:** this repository, in particular `spikes/C1-S1/` (`c1s1.py`, `worker/`) and `spikes/G2-S1/fidelity.py` (imported for its SigV4 signer; keep the repository layout).

## Before you start

- [ ] Confirm in the dashboard that you are in the **sandbox** account, not production. Write down the account ID.
- [ ] Do not add lifecycle rules. H8 is kit A3-S3's job, on its own bucket.
- [ ] Keep token secrets out of the repository, shell history files and results. Use environment variables and a `.dev.vars` file that is git-ignored.
- [ ] Note the time zone you use. All times in the results are UTC.

## Procedure

Do the steps in order. After each step, write down what you saw in the results table, even if it looks unimportant.

1. Check that R2 is reachable: `curl -sS -o /dev/null -w '%{http_code}\n' https://<ACCOUNT_ID>.r2.cloudflarestorage.com/`. **You should see:** a 4xx code such as 400 or 403. A connection or TLS error means the host is blocked: stop and record "No result: host blocked".
2. Create the bucket: `npx wrangler@4.143.0 r2 bucket create c1s1-sandbox`. **You should see:** the bucket listed by `npx wrangler@4.143.0 r2 bucket list`.
3. In the dashboard, create token **A** and token **B** (both Object Read & Write, both scoped to `c1s1-sandbox` only). Export token A: `export R2_ACCOUNT=<account id> R2_AK=<A access key id> R2_SK=<A secret>`. Keep B's values for step 10. **You should see:** both tokens listed with the bucket scope.
4. Point the Worker at real R2:
   - copy `spikes/C1-S1/worker/` to a scratch folder and run `npm ci` there;
   - in its `wrangler.toml`, set `bucket_name = "c1s1-sandbox"`, add `remote = true` to the `[[r2_buckets]]` entry, delete its `local_dev` line, and set `S3_BASE = "https://<ACCOUNT_ID>.r2.cloudflarestorage.com/c1s1-sandbox"`;
   - delete `S3_AK` and `S3_SK` from `[vars]` and put token A's values in a `.dev.vars` file instead (`S3_AK=…` and `S3_SK=…` on two lines);
   - start it: `npx wrangler dev --port 8787`.

   **You should see:** `curl -s http://127.0.0.1:8787/health` prints `{"ok":true}`. Remote bindings change real data and are billed normally (Cloudflare docs, "Workers local development"). The D1 and Durable Object bindings stay local and are not used by this kit.
5. If kit G2-S1 has not yet been run on the sandbox account, run its steps 4 and 5 now. They produce T22–T27, T30, T38, T39, T41–T49 and T53 for H1–H6 and H14. **You should see:** `spikes/G2-S1/results/r2.json`.
6. Run the main checks:
   ```sh
   cd spikes/C1-S1
   python3 c1s1.py --name r2 --endpoint "https://$R2_ACCOUNT.r2.cloudflarestorage.com" --bucket c1s1-sandbox \
     --region auto --ak "$R2_AK" --sk "$R2_SK" --account "$R2_ACCOUNT" --worker http://127.0.0.1:8787 \
     --out results/r2.json | tee results/r2.log
   ```
   **You should see:** one line per check C01–C16 and no `ERR` lines. C13 (H10) pauses for about 6 s. If C01 shows 429 for the second write, that is R2's "1 write per second per key" limit: record it, because the stored-content check still decides H1.
7. Bucket lock, part 1: `python3 c1s1.py … --only H9-before --state results/h9-state.json` (same connection flags as step 6). **You should see:** a line asking you to add the lock rule.
8. Add the lock rule: `npx wrangler@4.143.0 r2 bucket lock add c1s1-sandbox c1s1-lock "c1s1-locked/" --retention-days 1`. Wait 60 s. Check it with `npx wrangler@4.143.0 r2 bucket lock list c1s1-sandbox`. **You should see:** the rule `c1s1-lock` on prefix `c1s1-locked/`.
9. Bucket lock, part 2: `python3 c1s1.py … --only H9-after --state results/h9-state.json --out results/r2-h9.json`. **You should see:** line C17 with the status of each overwrite, delete, complete and abort attempt.
10. Token revocation:
    - with token **B**'s values in `--ak/--sk`, run `python3 c1s1.py … --only H11-mint --state results/h11-state.json`. **You should see:** `pre_check` with `url: 200` and `temp: 200`. If `temp` is not 200, H13 has already failed: record it and continue;
    - delete token **B** in the dashboard and write down the UTC time to the second;
    - at once run `python3 c1s1.py … --only H11-poll --state results/h11-state.json --revoked-at <UTC time, e.g. 2026-11-02T14:03:07Z> --out results/r2-h11.json`. It polls every 5 s for up to 15 min.

    **You should see:** line C18 with `first_fail_s_after_revocation` for `url` and `temp`. `null` means it still worked when polling stopped.
11. Remove the lock rule: `npx wrangler@4.143.0 r2 bucket lock remove c1s1-sandbox --id c1s1-lock`. Then try to delete one locked object (`aws`-style DELETE with token A, or `npx wrangler@4.143.0 r2 object delete c1s1-sandbox/<key from results/h9-state.json> --remote`). **You should see:** record whether the delete now succeeds. This tells the owner whether an admin can lift a lock early, which matters if a lock is ever used on staging.
12. H8 is answered by kit A3-S3 (hypothesis H3). Copy its result into the H8 row below when it is available.

**Stop and record "No result" if:** the account is not clearly the sandbox; a bucket-scoped token cannot be created; or step 1 fails.

## Cleaning up

1. Stop `wrangler dev`. Delete the `.dev.vars` file.
2. Delete every object under `c1s1/` and `c1s1-locked/` and abort open multipart uploads (H2, H3 and H9 leave some). If step 11 showed that locked objects cannot be deleted yet, wait until the 1-day retention has passed.
3. Delete the bucket: `npx wrangler@4.143.0 r2 bucket delete c1s1-sandbox`.
4. Revoke token A. Token B was already deleted in step 10.

## Data handling

Class `SYN → results`. The scripts upload only `os.urandom` bytes and fixed test strings. The results hold status codes, error codes, booleans, ETags of random data, counts and seconds: no secrets. Object keys contain a random run ID and nothing else. The results may be committed to `spikes/C1-S1/results/`. Never commit a token or the `.dev.vars` file. The JWT in `results/h11-state.json` is signed with token B, which is deleted by then, but do not commit the state files anyway.

## Results

Copy this section into `docs/research/kits/C1-S1/results.md` and fill it in. Do not edit numbers afterwards; add a note instead.

- **Run by / date / place:**
- **Account (sandbox? yes/no), bucket, location hint:**
- **Tool versions:** Python, Node, wrangler (`npx wrangler --version`)
- **Emulator or VM used instead of real R2?** No (this is the real leg). Emulated results for comparison: `spikes/C1-S1/README.md`.

| H | Check(s) | Real R2 result | Miniflare result (2026-10-06, emulated) | Verdict |
|---|---|---|---|---|
| H1 | T22–T27, C01, C02 | | 412 on existing key; 403 when the header is dropped | |
| H2 | T38, C03 | | Complete overwrites (T38); binding `complete()` overwrites (C03) | |
| H3 | T53, C04, C05 | | Presigned POST accepted for Create and Complete | |
| H4 | T30, C06, C07 | | Tampered part 400 BadDigest; header dropped: rejected, but as a connection reset (run 1) or HTTP 500 (run 2), never 403 | |
| H5 | T49, C08 | | Shorter 403; longer 500 (nothing stored) | |
| H6 | T47, C09, C10 | | Signed SHA-256 ignored, tampered body stored; binding `sha256` enforced | |
| H7 | C11, C12 | | Single-PUT ETag = MD5; object ETag formula holds; part ETags are not MD5 | |
| H8 | A3-S3 H3 | | not emulated (lifecycle 501) | |
| H9 | C17 | | not emulated | |
| H10 | C13 | | Completes (expiry checked at arrival) | |
| H11 | C18 | URL: … s; temp credential: … s after deletion | not emulated | |
| H12 | W02, W03, C14 | | Both forms refuse an existing key | |
| H13 | C15, C16 | | not emulated (Miniflare refuses session-token credentials) | |
| H14 | T39 | | 200 (ignored), G2-S1 run 2026-09-29 | |

| Pass criterion | Budget ID | Measured value | Pass / Fail / No result |
|---|---|---|---|
| Behaviour documented for every H (PLAN: "Behaviour documented") | — | | |
| Outstanding URLs dead within 15 min of revocation, or bounded by their ≤ 15 min lifetime (H10, H11) | BUD-REVOKE | | |

- **Overall:** Pass | Fail | No result
- **Differences from Miniflare (one line each: check, R2, Miniflare, impact):**
- **Surprises:**
- **Follow-ups for the workstream:**
