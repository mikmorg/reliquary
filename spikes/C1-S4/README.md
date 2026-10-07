# Spike C1-S4: presign 200 parts in one request, emulated leg and CPU micro-benchmark (THROWAWAY)

> **Emulated, not real Cloudflare.** The Worker ran under local `wrangler dev` (workerd), and the micro-benchmark ran in Node's V8, both on a shared x86 container on 2026-10-06. Neither is Cloudflare's CPU-time accounting. Cloudflare's own docs say that deployed Workers only advance timers on I/O, while "in local development … timers will increment regardless", and suggest measuring CPU-intensive code locally with Wrangler (Workers "Performance and timers" page, retrieved 2026-10-06). So the local in-Worker timings are a reasonable *indication*, not a measurement of billed CPU. The real run is the kit `docs/research/kits/C1-S4/README.md`.
> This is throwaway research code, not production code.

- **Spike:** C1-S4 "Presign 200 parts in one request" (workstream C1, `docs/research/PLAN.md` section "C1.")
- **Exec tag:** `[SB]`. This folder is the local variant, run as CT.
- **Budget IDs cited:** BUD-CPU-REQ (request-signature verification < 1 ms CPU), via the Ed25519 verify timing.
- **Data-handling class:** `SYN → results`. Random bytes only.

## What ran

| Part | What | Versions |
|---|---|---|
| `c1s4.py` against `spikes/C1-S1/worker/` under `wrangler dev` | 50 × `/noop`, 50 × `/presign-many?n=200` (aws4fetch, explicit `X-Amz-Expires=900`, `partNumber` and `uploadId` per URL), 5 × 10,000 Ed25519 verifies in the Worker; then a real multipart round trip: the binding creates an upload, the Worker presigns 200 part URLs, `curl` PUTs parts 1 (5 MiB), 2 (5 MiB) and 200 (777 B) to Miniflare's S3 endpoint, the binding completes | wrangler 4.143.0, Miniflare 5.20260926.0-alpha, workerd 1.20260926.1, aws4fetch 1.0.20, Python 3.11.15, curl (container default) |
| `cpu-bench.mjs` in Node | Same aws4fetch presign loop (200 URLs on an R2-style host, 120-character `uploadId`), 5 warm-up rounds then 30 measured rounds; WebCrypto Ed25519 verify, 2,000 warm-up then 5 × 10,000. CPU from `process.cpuUsage()` (user + system, whole process) | Node 22.22.2, aws4fetch 1.0.20, CPU "Intel(R) Xeon(R) Processor @ 2.10GHz" |

Container load: another workstream's Java process used about 3.5 of 4 cores during the run (load average 4–6). Tail latencies are inflated by that.

## Results

`results/miniflare.json` (finished 2026-10-06T20:15:44Z) and `results/cpu-bench-node.json`.

| Measurement | Value |
|---|---|
| Presign 200 URLs, in-Worker time (local workerd), 50 calls | p50 22.0 ms, p99 183.9 ms, max 324 ms |
| Same, client round trip | p50 28.5 ms, p99 190.6 ms (`/noop` round trip p50 3.9 ms) |
| One call returning the URLs | 17 ms in the Worker; 103,742-byte JSON response; 200 unique URLs; longest URL 515 characters |
| Presign 200 URLs, **CPU** in Node (process CPU), 30 rounds | p50 38.8 ms, max 77.3 ms (wall p50 36.7 ms) |
| `curl` to presigned part URLs 1, 2, 200 | `HTTP/1.1 200 OK` for all three; binding complete → ETag `…-3`, size 10,486,537 B = 5 MiB + 5 MiB + 777 B (`size_ok: true`) |
| Ed25519 verify, in-Worker time (local workerd), per verify | 0.055–0.079 ms over 5 runs of 10,000 |
| Ed25519 verify, **CPU** in Node (process CPU), per verify | 0.159–0.203 ms over 5 runs of 10,000 |

The Node CPU figure for Ed25519 is higher than the workerd figure. A likely reason (not verified here) is that Node dispatches each WebCrypto call as an asynchronous job, and `process.cpuUsage()` counts that overhead across all of the process's threads. Neither number is Cloudflare's billed CPU.

## Verdict (indicative only)

- **Within Paid-plan CPU limits: indicative pass.** Tens of milliseconds against a 30 s default (5 min maximum) on Workers Paid is a margin of about three orders of magnitude (Workers limits page, retrieved 2026-10-06). The same numbers are **above the Free plan's 10 ms**, so presigning a 200-part window needs Workers Paid, which L01 already assumes.
- **URLs work from curl: pass against Miniflare** (parts 1, 2 and the last part, then complete). Whether real R2 accepts presigned UploadPart is kit C1-S1 H4 and kit C1-S4 H2.
- **BUD-CPU-REQ (< 1 ms per signature check): indicative pass**, by 5× (Node process CPU) to 13× (local workerd). The real figure comes from the kit's dashboard method.
- No subrequests are made by presigning (by construction: aws4fetch `sign()` with `signQuery` only computes HMACs). The kit confirms it on the dashboard.

Sources: Workers limits `https://raw.githubusercontent.com/cloudflare/cloudflare-docs/production/src/content/docs/workers/platform/limits.mdx`; Workers "Performance and timers" `https://raw.githubusercontent.com/cloudflare/cloudflare-docs/production/src/content/docs/workers/runtime-apis/performance.mdx`. Both retrieved 2026-10-06.

## Reproduce

```sh
# in a scratch copy of spikes/C1-S1/worker after npm ci
X_LOCAL_OBSERVABILITY=false npx wrangler dev --port 8787 --ip 127.0.0.1 --persist-to .state
python3 c1s4.py --worker http://127.0.0.1:8787 --reps 50 --out results/miniflare.json
node cpu-bench.mjs            # run from the scratch Worker folder so it finds aws4fetch
```
