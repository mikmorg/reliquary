# Spike C1-S1: R2 behaviour, emulated leg (THROWAWAY)

> **Emulated, not real R2/Cloudflare.** Every result in this folder comes from Miniflare's local R2 S3 endpoint under `wrangler dev`, in the cloud container, on 2026-10-06. None of it says what real R2 does. The G2-S1 fidelity run already showed that Miniflare departs from the R2 docs on exactly the checks C1-S1 cares about (checksums, conditional Create). The real-R2 leg is the kit `docs/research/kits/C1-S1/README.md`. It is blocked on the sandbox account (H5 L01) and on network access to `*.r2.cloudflarestorage.com`.
> This is throwaway research code, not production code.

- **Spike:** C1-S1 "R2 behaviour (one run, Wave 1)" (workstream C1, `docs/research/PLAN.md` section "C1.")
- **Exec tag:** `[SB]`. This folder is the local-emulator variant, run as CT. The SB leg is the kit.
- **Hypotheses:** H1–H14, as worded in the kit and in `docs/research/c1-cloudflare-control-plane.md` section "Spikes".
- **Budget IDs cited:** BUD-REVOKE (H10, H11). The emulated leg cannot measure either: H11 needs a real token, and H10 below only shows what Miniflare does.
- **Data-handling class:** `SYN → results`. Only `os.urandom` bytes and fixed test strings are uploaded. The credentials in `worker/wrangler.toml` are local test strings for Miniflare, not secrets.
- **Research note:** `docs/research/c1-cloudflare-control-plane.md` (owned by the analyst).

## Contents

| Path | What |
|---|---|
| `c1s1.py` | Driver, Python 3.9+ stdlib only. It imports the SigV4 signer from `../G2-S1/fidelity.py` (keep the repository layout). Checks C01–C18. `--only H9-before/H9-after/H11-mint/H11-poll` are the kit's account-action sub-steps. |
| `worker/` | One throwaway Worker shared by C1-S1 to C1-S4: aws4fetch presigning, R2 binding helpers, D1 and Durable Object lease race (C1-S2), presence check (C1-S3), bulk presign and Ed25519 timing (C1-S4). If the `SPIKE_TOKEN` secret is set, every route except `/health` requires the `x-spike-token` header (the kits set it, because `/presign` hands out signed URLs). |
| `results/miniflare.json` | Run 2 (the rerun), 2026-10-06T20:15Z, run ID `de4731c7` |
| `results/miniflare-run1-2026-10-06T1658Z.json` | Run 1, 2026-10-06T16:58Z, run ID `ec6aa413` (first spike-runner pass, interrupted before this README was written) |

## What ran

| Item | Version |
|---|---|
| wrangler / Miniflare / workerd | 4.143.0 / 5.20260926.0-alpha / 1.20260926.1 (npm, pinned in `worker/package-lock.json`) |
| aws4fetch (presigning inside the Worker) | 1.0.20 |
| Python, Node | 3.11.15, 22.22.2 |
| Worker `compatibility_date` | 2026-09-01 |

Start (from a scratch copy of `worker/`, after `npm ci`):

```sh
X_LOCAL_OBSERVABILITY=false npx wrangler dev --port 8787 --ip 127.0.0.1 --persist-to .state
python3 c1s1.py --name miniflare --endpoint http://127.0.0.1:8787/cdn-cgi/local/r2/s3 --bucket staging \
  --ak c1-local-ak --sk c1-local-secret-not-a-real-credential --account 0000000000000000000000000000c1c1 \
  --worker http://127.0.0.1:8787 --out results/miniflare.json
```

`X_LOCAL_OBSERVABILITY=false` turns off wrangler 4.143's local trace store. With it on, the first pass's state directory grew to 270 MB of traces after about 100,000 requests, which matters on a nearly full disk (the container had 1.3–1.7 GB free).

## Results (emulated; both runs agree except C07)

| H | Check | Miniflare result | Verdict (emulated only) |
|---|---|---|---|
| H1 | C01 | aws4fetch presign with `If-None-Match: *` signed (`SignedHeaders=host;if-none-match`): first PUT 200, second PUT 412 PreconditionFailed, first body kept | Create-only works in Miniflare |
| H1 | C02 | Same URL, client drops the signed header: 403 SignatureDoesNotMatch, original kept | Header binding works |
| H2 | C03 | Binding `resumeMultipartUpload().complete()` onto an existing key: 200, object **overwritten** (the binding `complete()` has no condition parameter) | Gap: completion overwrites |
| H3 | C04, C05 | Presigned **POST** `?uploads` (Create) and `?uploadId=` (Complete), used with no credentials: both **200**, and the completed object matches | Accepted by Miniflare. R2 docs list only GET, HEAD, PUT, DELETE for presigned URLs |
| H4 | C06 | Presigned UploadPart with `Content-MD5` signed: tampered same-length body 400 BadDigest, genuine 200 | Pass |
| H4 | C07 | Same URL, client drops the signed `Content-MD5` (5 MiB body) | Rejected, but not with 403: run 1 connection reset, run 2 HTTP 500. The rejection mode is not stable |
| H5 | C08 | `allHeaders: true` signs `content-length`: shorter body 403 SignatureDoesNotMatch, longer body **500**, exact 200; nothing stored after the wrong lengths | Rejected, wrong status for "longer" |
| H6 | C09 | Signed `x-amz-checksum-sha256`, tampered same-length body: **200, tampered body stored** | Fail in Miniflare (consistent with G2-S1 T47). The R2 release note of 2023-06-16 says "S3 putObject now supports sha256 and sha1 checksums", so real R2 may differ |
| H6 | C10 | Binding `put()` with a wrong `sha256`: throws "The SHA-256 checksum you specified did not match", nothing stored | Pass |
| H7 | C11 | Single PUT: S3 ETag = `"<MD5 hex>"`; binding `etag` unquoted, `httpEtag` quoted | Matches the formula |
| H7 | C12 | Multipart 5 MiB + 5 MiB + 12,345 B: object ETag = MD5(concatenated binary part MD5s) + `-3` (holds); **part ETags are not MD5** (opaque 100+ character strings) | Object formula holds; part ETags are Miniflare-specific |
| H8 | — | Not emulated: Miniflare answers 501 to lifecycle configuration (G2-S1 T35) | Kit A3-S3 |
| H9 | — | Not emulated: no bucket locks in Miniflare | Kit only |
| H10 | C13 | `X-Amz-Expires=3`, headers sent at t = 0, rest of body at t = 6 s: 200, stored | Expiry checked at arrival in Miniflare |
| H11 | — | Not emulated: no account tokens | Kit only |
| H12 | C14 | Binding `put()` with `onlyIf` as `Headers({"If-None-Match": "*"})` and as `{etagDoesNotMatch: "*"}`: absent key stored, existing key refused (`put` returns null), original kept | Pass in both forms |
| H13 | C15, C16 | Locally signed temporary credential: **every** request is refused with 403 SignatureDoesNotMatch, including the in-scope PUT | Not emulated: Miniflare does not accept session-token credentials |
| H14 | G2-S1 T39 | CreateMultipartUpload with `If-None-Match: *` on an existing key: 200 (G2-S1 run, 2026-09-29) | Miniflare ignores it. The R2 release note of 2022-05-27 says R2 returns 412 for conditional headers on `CreateMultipartUpload` when the object exists |

Run time: 15.6 s (run 1) and 16.1 s (run 2).

A third run at 2026-10-06T20:26Z used the repository copy of `worker/` with the `SPIKE_TOKEN` gate switched on (`.dev.vars`) and `SPIKE_TOKEN` set for the driver. It was a smoke test of the token path, so its JSON was not kept, but its verdicts for C01–C16 were identical to runs 1 and 2 (compared by script); C07 was again a connection reset.

Release notes cited: `https://raw.githubusercontent.com/cloudflare/cloudflare-docs/production/src/content/release-notes/r2.yaml`, retrieved 2026-10-06.

## What this does and does not show

- It shows the **Worker-side code works**: aws4fetch can sign `If-None-Match`, `Content-MD5`, `Content-Length` and `x-amz-checksum-sha256` into a presigned URL (`SignedHeaders` in C01, C06, C08, C09), the binding `onlyIf` wildcard works in both forms (C14), and the binding `sha256` check works (C10). These are properties of aws4fetch and of workerd's binding code, which is the same open-source runtime Cloudflare runs, so they carry more weight than the S3-endpoint results.
- It does **not** show what the R2 S3 endpoint does. The Miniflare S3 layer is a separate emulation (`dist/src/workers/r2/s3/index.worker.js`). On H2, H3, H6 and H14 it either contradicts or is silent on the R2 docs.
- For the design, the safe reading is unchanged: per-upload keys plus homelab verification (SR-04, SR-07) do not depend on any of H1–H14 passing on real R2.

## Cleanup done

The local `.state` directory, `node_modules/` and `.wrangler/` stayed in the scratchpad and are not in the repository.
