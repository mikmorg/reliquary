# Kit A3-S3: real-R2 multipart resume after 24 h and after 7 days

- **Spike:** A3-S3 "Real-R2 resume after 24 h and after 7 days" (workstream A3, see `docs/research/PLAN.md`, section "A3.")
- **Exec tag:** SB. Uses the dedicated **sandbox** Cloudflare account (H1, long-lead item L01), never production.
- **Prepared by / date:** A3 spike runner (agent), 2026-10-06
- **Who runs it:** an agent in a container that can reach `*.r2.cloudflarestorage.com`, or the owner on a laptop. Each step takes a few minutes, but the steps are spread over **9 calendar days** (day 0, 1, 6, 7, 8, 9).
- **Time needed:** about 10 min hands-on per visit, 6 visits; about 1 h in total, plus 9 days of waiting.
- **Data-handling class:** `SYN → results`. The script uploads only deterministic synthetic bytes it generates from a seed. Nothing from the family is used.
- **No emulated run was done.** Miniflare, the local target G2 chose, answers **501** for PutBucketLifecycleConfiguration, ListParts and ListMultipartUploads (G2-S1 checks T35 and T54, `spikes/G2-S1/README.md`). It also has no clock to fast-forward, so a local "7-day" run would only test the script. The script was smoke-tested once against moto 5.2.3 on 2026-10-06 (init, resume, checkpoint, probe, lifecycle put/get, cleanup, upload-gone path). **That smoke test is not a result**: moto is not R2.

## Purpose

Find out what really happens on R2 when a phone pauses a large multipart upload for a day, or for a week, and whether the protocol's resume and reclaim rules work there.

## Hypothesis

1. **H1 (24 h resume):** one day after the upload starts, ListParts returns the parts already uploaded with the journaled ETags. The upload then finishes without re-sending any of them (`resent_journaled_bytes = 0`), and the object's SHA-256 matches.
2. **H2 (default 7-day abort):** with no custom rule, R2 aborts an incomplete multipart upload about 7 days after **initiation**. Afterwards ListParts and UploadPart return NoSuchUpload, the protocol's "upload gone" path. Lifecycle timing is approximate, "typically within 24 hours" (A3 note K7, K8).
3. **H3 (extension):** it is undocumented whether an AbortIncompleteMultipartUpload rule can extend the window beyond 7 days (A3 note K7 and C31, open question 1). Two outcomes are possible. If R2 rejects `DaysAfterInitiation = 10`, extension is impossible. If R2 accepts it and the upload is still there on day 8, extension works.
4. **H4 (cleanup):** an `AbortIncompleteMultipartUpload` rule with `DaysAfterInitiation = 1` removes an abandoned upload within roughly 1–2 days.
5. **H5 (segment checkpoint, A3 note F2 option 1):** on day 6, the contiguous finished parts 1..k complete as segment `s0`, a new upload `s1` carries the rest, and `s0 ‖ s1` hashes to the expected whole-object SHA-256.

## Decision it informs

| If the result is… | Then… |
|---|---|
| **Pass** (PLAN): "completes without re-sending finished parts, or the protocol reclaims cleanly at the 7-day abort; lifecycle rules clean up abandoned uploads", i.e. H1 and H4 hold, H2 shows a clean NoSuchUpload, and H5 works | ADR-0009 adopts the **segment checkpoint** before day 7 for slow uploads (A3 note F2 option 1), with "restart, then suggest USB" as the fallback. C1 sets an abort rule on `staging/` and nothing else, never an Expiration rule. |
| **Pass, and H3 shows extension works** | ADR-0009 can use a longer abort window on `staging/` instead of, or as well as, the checkpoint. C1 records the rule. |
| **Fail on H1** (ListParts loses parts, ETags differ, or completion fails after 24 h) | Resume is unsafe on R2. ADR-0009 falls back to one object per segment (A2/A4) and drops multipart for long uploads. |
| **Fail on H5** (a completed prefix of parts cannot become a segment) | Restart plus the USB fallback for files that cannot finish within 7 days ("too-large-for-link"). |
| **No result** (no sandbox account, host blocked) | The 7-day behaviour stays "documented, not measured" in ADR-0009 (claims K7 and K8 remain secondary to a test). The A0 harness keeps its emulated lifecycle sweeper (G2 note F1). |

## Budget IDs cited

- **BUD-REVOKE** (outstanding URLs expire within 15 min): the script presigns every UploadPart URL with a 900 s expiry, so the resume path is tested under the budget's URL lifetime. The 60 s propagation part is D3-S5's job.
- **BUD-TMP** (phone temp disk ≤ 2 GB) is **not** measured here. It is the reason the checkpoint must not require re-encrypting finished parts. The CE spike already showed parts are byte-reproducible from the sealed per-upload key (`content-encryption-format.md` §8).
- No new thresholds are introduced. Timings in the log are context only.

## Equipment

| Item | Exact model or version | Why | Have it? |
|---|---|---|---|
| Sandbox Cloudflare account with R2 enabled (L01) | — | SB rule: never production | Owner action (H5 L01; allowlist in `docs/research/sources.md`) |
| A **dedicated** bucket, e.g. `a3s3-sandbox` | — | The kit changes the bucket's lifecycle configuration. Do not share the bucket with G2-S1 or C1-S1 | Create in step 1 |
| R2 API token scoped to this bucket with permission to change bucket lifecycle configuration (whether "Object Read & Write" is enough for PutBucketLifecycleConfiguration was **not checked**; if step 3 returns 403, either use an Admin Read & Write token or set the same rules in the dashboard and record that) | — | S3 access key and secret | Create in step 1 |
| Machine with Python ≥ 3.9 (stdlib only) that can reach `https://<ACCOUNT_ID>.r2.cloudflarestorage.com` | e.g. Python 3.11 | Runs `a3s3.py` | Blocked from the cloud container on 2026-10-06; use a laptop or an allowlisted container |
| A calendar reminder for days 1, 6, 7, 8 and 9 | — | The test is about elapsed time | — |

**Software and files needed:** this folder (`a3s3.py`) and `spikes/G2-S1/fidelity.py` (the script imports its SigV4 signer, so keep the repo layout). About 30 MB of synthetic uploads in total.

## Before you start

- [ ] Confirm that the dashboard shows the **sandbox** account, not production.
- [ ] Write down the account ID. The endpoint is `https://<ACCOUNT_ID>.r2.cloudflarestorage.com`.
- [ ] Keep the token out of the repo and out of shell history files. Use environment variables:
  `export A3S3_ENDPOINT=https://<ACCOUNT_ID>.r2.cloudflarestorage.com A3S3_BUCKET=a3s3-sandbox A3S3_AK=… A3S3_SK=…`
- [ ] Work in an empty directory outside the repo. The journals and `a3s3-log.jsonl` are written to the current directory. Call the script as `python3 -I <repo>/docs/research/kits/A3-S3/a3s3.py …`.
- [ ] Note the time zone you record in. The script logs UTC.

## Procedure

Do the steps in order. Every command prints JSON lines and appends them to `a3s3-log.jsonl`. Paste nothing by hand; the log is the record.

**Day 0**

1. In the dashboard, create bucket `a3s3-sandbox` and a token for it. **You should see:** an access key ID and a secret.
2. `a3s3.py lifecycle-get`. **You should see:** `status` 200 with the bucket's default lifecycle (R2 documents a default rule that aborts multipart uploads after 7 days), or 404 NoSuchLifecycleConfiguration. Either is a result: record which.
3. `a3s3.py lifecycle-put --rule r1:a3s3/abort1/:1 --rule r10:a3s3/abort10/:10`. **You should see:** `status` 200 (rules accepted), or a 4xx with an error code. A rejection of the 10-day rule **is the H3 result**. If it is rejected, run step 3 again with only `--rule r1:a3s3/abort1/:1`.
   - *Caution:* this replaces the bucket's lifecycle configuration. If step 2 showed a default 7-day rule, check with `lifecycle-get` that the default still applies to other prefixes. If it no longer does, record that and add `--rule r7:a3s3/:7` so the u7 upload still has a 7-day rule.
4. `a3s3.py lifecycle-get`. **You should see:** the rules you just set.
5. Start five uploads (6 parts: 5 × 5 MiB + 777 KiB; the first 3 or 4 uploaded):
   - `a3s3.py init --tag u24 --journal j-u24.json`
   - `a3s3.py init --tag u7 --journal j-u7.json`
   - `a3s3.py init --tag ck --journal j-ck.json --upload-parts 4`
   - `a3s3.py init --tag ab1 --prefix a3s3/abort1/ --journal j-ab1.json`
   - `a3s3.py init --tag ab10 --prefix a3s3/abort10/ --journal j-ab10.json` (only if the 10-day rule was accepted)

   **You should see:** `upload_part` lines with status 200 and an ETag, then `journal_written`.
6. `a3s3.py probe --journal j-u7.json`. **You should see:** `upload_listed: true` and `parts_listed: [1, 2, 3]`.

**Day 1 (24–26 h after step 5)**

7. `a3s3.py resume --journal j-u24.json`. **You should see:** `plan` with `adopted: [1,2,3]` and `to_upload: [4,5,6]`, then `RESULT` with `outcome: completed`, `sha256_ok: true` and `resent_journaled_bytes: 0`. **This is H1.**
8. `a3s3.py probe --journal j-ab1.json`. Record `upload_listed`. R2 lifecycle timing is approximate, so "still listed" on day 1 is not yet a failure.

**Day 2**

9. `a3s3.py probe --journal j-ab1.json`. **H4:** expect `upload_listed: false` and `list_parts_status` 404 NoSuchUpload by about day 2. If it is still listed, repeat daily and record the day it disappears.

**Day 6 (about 144 h after step 5, before the 7-day abort)**

10. `a3s3.py checkpoint --journal j-ck.json`. **You should see:** `complete_segment_s0` ok with `parts: 4`, `complete_segment_s1` ok, then `RESULT` with `outcome: checkpointed`, `s0_sha256_ok: true` and `s1_sha256_ok: true`. **This is H5.**

**Days 7, 8 and 9 (about 168 h, 192 h and 216 h after step 5)**

11. Each day: `a3s3.py probe --journal j-u7.json --try-part` and, if it exists, `a3s3.py probe --journal j-ab10.json --try-part`. The probe uploads one throwaway part at part number 7, beyond the journaled parts, so it never replaces a journaled part (A3 note C12).
    - **H2:** expect u7 to disappear between about 168 h and about 192 h (the documented 7 days plus lifecycle lag), with ListParts and UploadPart then returning 404 NoSuchUpload. Record `age_hours` at the first probe that shows it gone.
    - **H3:** if ab10 is still listed after u7 has gone, extension beyond 7 days works. If it disappears together with u7, the default 7-day abort wins.
12. After u7 has gone: `a3s3.py resume --journal j-u7.json`. **You should see:** `RESULT` with `outcome: upload-gone`. This is the path the protocol must handle as "ask the Worker, restart with a new upload ID" (A3 note F2, CE §8.5).

**Stop and record "No result" if:** the dashboard does not show the sandbox account; the token cannot read or write the bucket; or the machine cannot reach the endpoint.

## Cleaning up

1. `a3s3.py cleanup --prefix a3s3/`. **You should see:** `abort` and `delete` lines with 204.
2. Delete the bucket's lifecycle rules in the dashboard (or delete the bucket), and revoke the token.
3. Keep `a3s3-log.jsonl` and the five journals. They contain only synthetic data, key names and ETags.

## Data handling

H3's rules apply (`docs/research/h3-research-data-governance.md` §2–§4). This kit reads and writes only class **SYN**: deterministic bytes from the seed `a3s3-seed-1`. Nothing from any family device is touched. The log and the journals may be committed to the repo as results. The token must never be committed.

## Results

Copy this section into `docs/research/kits/A3-S3/results.md` and fill it in. Do not edit numbers afterwards; add a note instead.

- **Run by / dates / place:** <...>
- **Account:** sandbox (confirm) · **bucket:** <...> · **location hint:** <...>
- **Emulator or VM used instead of real R2?** No | Yes: <what, and why>

| Step | Expected | What happened (paste the `RESULT`/`probe` JSON) | age_hours | Pass / Fail / No result |
|---|---|---|---|---|
| 2 lifecycle-get (default) | default 7-day rule or 404 | | — | |
| 3 lifecycle-put 1 d and 10 d | 200, or a rejection of the 10-day rule | | — | |
| 7 resume u24 (H1) | completed, sha256_ok, resent_journaled_bytes = 0 | | | |
| 8–9 ab1 gone (H4) | gone by about day 2 | | | |
| 10 checkpoint ck (H5) | checkpointed, both segment SHA-256 ok | | | |
| 11 u7 gone (H2) | gone between about 168 h and 192 h; NoSuchUpload | | | |
| 11 ab10 (H3) | still listed after u7 is gone, or gone with it | | | |
| 12 resume u7 | upload-gone | | | |

| Pass criterion (PLAN A3-S3) | Budget ID | Measured value | Pass / Fail / No result |
|---|---|---|---|
| Completes without re-sending finished parts (24 h) | — | resent_journaled_bytes = | |
| Protocol reclaims cleanly at the 7-day abort | — | status / error at first gone probe = | |
| Lifecycle rules clean up abandoned uploads | — | ab1 gone at age_hours = | |
| Presigned part URLs within the revocation lifetime | BUD-REVOKE | 900 s used | |

- **Overall:** Pass | Fail | No result
- **Surprises:** <for example a lifecycle-put that silently replaced the default rule, or error codes other than NoSuchUpload>
- **Follow-ups for A3 / C1:** <...>
