# Spike G2-S1: R2 fidelity, emulated leg (THROWAWAY)

> **Emulated, not real R2/Cloudflare.** Every result here comes from local emulators and S3 servers in the cloud container on 2026-09-29. None of it says what real R2 does. The real-R2 leg is a kit, `docs/research/kits/G2-S1/README.md`, and it is blocked on the sandbox account and the network allowlist.
> This is throwaway research code, not production code.

- **Spike:** G2-S1 "R2 fidelity: the same presigned multipart and conditional-create script against real R2, Miniflare, Garage, SeaweedFS and versitygw" (workstream G2, `docs/research/PLAN.md`)
- **Exec tag:** `[SB]`. This folder is the local-emulator variant, which ran as CT. The SB leg is written as a kit.
- **Budget IDs cited:** BUD-REVOKE, only for the presigned-expiry mechanism: T08 and T09. Nothing else here is a budget measurement. Timings come from a shared container whose load average ranged from 10 to 65 on 4 vCPU, so they are indicative only.
- **Data-handling class:** `SYN → results`. The script uploads only random bytes it generates itself.
- **Research note:** `docs/research/g2-test-and-verification.md` (owned by the analyst).

## What ran

| Target | Version (how obtained) | Ran? |
|---|---|---|
| **Miniflare local R2 S3 endpoint** via `wrangler dev` | wrangler 4.143.0 → miniflare 5.20260926.0-alpha, workerd 1.20260926.1 (npm; `worker/package-lock.json`). Worker uses aws4fetch 1.0.20 to mint presigned URLs, R2 binding, D1 binding | Yes, plus binding interop W01–W05 |
| RustFS | `rustfs/rustfs:1.0.0` docker image (created 2026-09-16) | Yes |
| versitygw (posix backend) | v1.8.0, `go install` from proxy.golang.org | Yes |
| SeaweedFS `weed mini` | source at commit 5da137233d1a (2026-09-29), `weed version` 4.48, built with Go 1.26.8 | Yes |
| Garage | `dxflrs/garage:v2.4.1` docker image, single node, sqlite | Yes |
| moto server | 5.2.3 (PyPI) | Yes, with an earlier script revision (no T34b, T46–T49, T54) |
| LocalStack | `localstack/localstack:latest` = 2026.8.4 (build 2026-09-23) | **No.** It exits with code 55: "License activation failed … set the LOCALSTACK_AUTH_TOKEN variable" (`results/evidence/localstack-2026.8.4-startup.log`) |
| MinIO community | — | **No.** It is excluded by the PLAN rule because the repository is archived (the scouts verified this) |
| s3s-fs | — | **No.** Not attempted, because of time and disk (the container had 2–8 GB free). It is a sample implementation, per its own README |
| AWS SDK for JS v3 defaults | `@aws-sdk/client-s3` 3.1142.0 against each of the five servers that ran fully | Yes (`results/sdk-comparison.md`) |

`fidelity.py` is stdlib-only Python with its own SigV4 signer, so every target receives byte-identical requests. One run is about 750 S3 requests and about 64 MB of request bodies. `compare.py` builds `results/comparison.md`. `run_local.sh` records how each target was started.

## Results (details: `results/comparison.md`, `results/sdk-comparison.md`)

### Miniflare vs the protocol's needs (G2 note F1: a–e)

| Behaviour | Miniflare result | Same on RustFS / versitygw / SeaweedFS / Garage? |
|---|---|---|
| (a) Worker-minted presigned PUT and UploadPart | Works (W01, W04, T02, T30). The endpoint keeps the path prefix `/cdn-cgi/local/r2/s3/<bucket>`, and the AWS JS presigner handles it (S6) | n/a (W checks are Miniflare-only) |
| (b) One store shared by the binding and S3 | Yes. Objects written over S3 are visible to `env.BUCKET` (W01). Conditionals work across both paths (W02, W03). A binding-created multipart upload with S3-presigned parts, completed by the binding, gives a matching SHA-256 (W04) | n/a |
| Tamper, key, method, expiry and Content-Type checks on presigned URLs | All rejected with 403 (T04–T08, T11). 604,800 s is accepted; 604,801 s gets 400 (T09) | Same outcome on RustFS, versitygw, SeaweedFS and Garage (error codes differ); moto accepts everything |
| (c) Multipart part rules | 5 MiB minimum enforced (T31). The equal-part rule is enforced, but the S3 layer **reports it as 404 NoSuchUpload** (T32, T33), because every simulator 500 is mapped to NoSuchUpload (`operations.worker.ts`). A stale part ETag gives 400 InvalidPart, and nothing is stored (T34, T34b) | The equal-part rule is **not** enforced on any other server (AWS behaviour). SeaweedFS **accepts a stale part ETag and stores the old part data** (T34b). Garage has no 5 MiB minimum |
| (d) If-None-Match on PutObject | 412, with the original kept (T20). **16 concurrent writers × 20 rounds: exactly one winner in every round**, both header-signed (T26) and presigned (T27). An unsigned If-None-Match on a presigned PUT is also honoured (T22) | Same on RustFS, versitygw and SeaweedFS. **Garage ignores it: 16 of 16 writers "win" in every round**, and the last write silently survives |
| D1 claim (`INSERT … ON CONFLICT DO NOTHING`) | Exactly one winner in each of 10 rounds of a 16-way race (W05) | n/a |
| (e) List, Get, Delete over header SigV4 | Works (T50, T51) | Same |
| CompleteMultipartUpload with If-None-Match | **Ignored: an existing key is overwritten** (T38). R2's docs list no conditional headers for Complete, so per-upload keys remain necessary | RustFS, versitygw and SeaweedFS return 412 (AWS behaviour); Garage overwrites |
| ListParts, ListMultipartUploads | 501 NotImplemented (T35) | 200 on all the others |
| Lifecycle configuration | PutBucketLifecycleConfiguration returns 501 (T54) | RustFS, SeaweedFS and Garage accept it (expiry *behaviour* not tested); versitygw returns 501 |
| Flexible checksums | **Ignored.** A wrong `x-amz-checksum-sha256` is stored (T41). **A checksum signed into a presigned URL does not stop a tampered body of the same length from being stored (T47).** Content-MD5 *is* enforced, both as a header and when signed into the URL (T40, T48) | RustFS, versitygw, SeaweedFS and Garage all reject T41 and T47 |
| `aws-chunked` body with trailing checksum | **200, but the chunk framing is stored as data**: 3,080 bytes stored for a 3,000-byte payload (T44). This is silent corruption | Decoded correctly everywhere else |
| `Transfer-Encoding: chunked` (unknown length) | 500 (T46; server log: "Provided readable stream must have a known length") | RustFS and versitygw 411; SeaweedFS and Garage 200 |
| `Expect: 100-continue` | Never answered (T45). With the AWS JS SDK's defaults, a 6 MiB PutObject took 6.3–6.8 s in the 3 runs that recorded timing, against 0.45–0.55 s with the expect-continue middleware removed. It was delayed, not hung | The others answer `100 Continue` immediately |
| SDK default checksum with a stream body | HTTP 500 in 7 of 7 runs (S3). `requestChecksumCalculation: "WHEN_REQUIRED"` makes it pass (S4) | Passes on the others |
| Queues HTTP pull | wrangler refuses `type = "http_pull"` ("Only \"worker\" consumers can be configured"; `results/evidence/queues-http-pull-config-error.txt`). Miniflare has no pull route | n/a |

### Stability of the local harness (Miniflare only)

- **Runtime crash:** 1 in 7 runs of the SDK checks (the first) crashed workerd ("The Workers runtime crashed unexpectedly and is being restarted (crash #1)"). Afterwards nothing answered on port 8787 for at least 45 s, until the run was restarted by hand (`results/evidence/wrangler-runtime-crash-excerpt.txt`). It did not recur in the next 6 runs.
- **Rejected requests with a body sometimes come back as 500 instead of 403.** A presigned PUT replayed against the wrong key (the T05 shape) was sent 50 times per body size at load average about 10 (`results/evidence/miniflare-rejected-with-body-repeat.txt`):

  | Body | 403 SignatureDoesNotMatch | 500 |
  |---|---|---|
  | 0 B | 50 | 0 |
  | 1 B | 48 | 2 |
  | 64 KiB | 21 | 29 |
  | 1 MiB | 38 | 12 |

  Nothing was stored in any case. The 500 comes from wrangler's ProxyWorker ("Network connection lost"). A client whose retry policy treats 5xx as retryable and 403 as terminal will behave differently locally.
- Under heavy shared-host load (load average 20–65), one full run timed out on five check groups (`results/evidence/miniflare-under-load.log`). Separately, the `wrangler dev` process exited at about 10:02:31 UTC with no error in its log. The container is shared with other agents, so the cause is **not determined**.

### What this means for the choice (input for the analyst; not a decision)

- The PLAN pass criterion ("no difference in any behaviour the protocol relies on") can only be judged against real R2. The emulated leg is therefore **inconclusive** on its own. It does settle the local-versus-local questions:
  - Miniflare is the only target that shares one store between the Worker binding and presigned S3.
  - Miniflare is the only target that enforces R2's documented equal-part-size rule (`r2/objects/upload-objects.mdx`: "All parts except the last must be the same size"), although it reports that failure with the wrong code.
  - Miniflare matches the others on auth and If-None-Match on PutObject, and its race behaviour is clean.
- Its gaps are concrete, and several are silent: T41, T44 and T47 store wrong or tampered bytes with a 200. **The A0 harness must therefore not rely on Miniflare for any integrity check that uses flexible checksums or `aws-chunked`.** Use Content-MD5 locally, or verify by read-back.
- As the **AWS-shaped secondary target**, this run favours **RustFS 1.0.0** over SeaweedFS. SeaweedFS completes with a stale part ETag and stores the old part (T34b), which contradicts R2's documented "uploading to the same part number replaces the previous part". RustFS matched Miniflare on every relied-on check except the two where it follows AWS (T32/T33 equal parts, T38 conditional Complete). versitygw is similar but has no lifecycle support. This conflicts with the draft note's SeaweedFS recommendation, and the analyst should reconcile the two.
- **Garage is confirmed unfit:** conditional writes are ignored (16 of 16 winners). **moto is unfit** beyond unit mocks: in server mode it performs no signature verification at all (tampered, expired and wrong-key requests all return 200).
- A new documented R2 fact that affects T26/T27 on real R2: `r2/platform/limits.mdx` says "Maximum concurrent writes to the same object name (key): 1 per second", and writes at a higher rate get HTTP 429. On R2, race losers may therefore see **429 instead of 412**. No local target emulates this.

## Re-running

See `run_local.sh <target>`. Delete `.work/`, `worker/node_modules` and `sdk/node_modules` afterwards. The sandbox run is in the kit.
