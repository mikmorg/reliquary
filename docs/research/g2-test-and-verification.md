# G2. Test and verification strategy: local emulator (Wave 1 scope, G2-S1)

- **Workstream:** G2 (see `docs/research/PLAN.md`, section "G2."). **This note covers only the Wave 1 slice:** choosing the local emulator stack that the A0 walking skeleton runs on (G2-S1). The rest of the test strategy is Wave 3: the invariant table, DST (G2-S2), fuzzing (G2-S3), the fault-injection catalogue, the device matrix and lab (G2-S4), and the release gates.
- **Status:** Final for Wave 1 (three-skeptic review and the G2-S1 emulated leg are merged; the real-R2 leg is kit-ready)
- **Date:** 2026-09-29 (last updated 2026-10-06)
- **Feeds:** ADR-0035 (Proposed, Wave 1 part only: `docs/adr/0035-test-and-verification-strategy.md`), OD-14 (clarification request), A0 (`spikes/skeleton/`, Gate B), A0's list of emulator-vs-R2 differences, and the real-R2 questions handed to C1-S1, A3-S3 and D3-S5
- **Depends on:** A3 (which behaviours the protocol relies on), C1-S1 (real R2 behaviour), H1 (sandbox account and network allowlist, `docs/research/sources.md`)
- **Traceability rows closed or advanced:** R-39 (verifiable and restorable; advanced by choosing the harness A0 runs on and fixing its integrity rules). R-18 (append-only; this note records that the local stack **cannot** verify it, and routes the check to SB and harness assertions).

## Summary

**Local target.** A0 should run on **`wrangler dev` (Miniflare) with Miniflare's experimental local R2 S3 endpoint**. It is the only target we tried where the Worker's R2 binding and presigned S3 traffic share one store. It is also the only one that enforces R2's equal-part-size rule, and it matched the other servers on signature, expiry and `If-None-Match` checks, including a clean 16-way race (emulated run, 2026-09-29).

**Rules that come with it.** Miniflare returns **200 while storing wrong or tampered bytes** in three cases: flexible checksums, a checksum signed into a presigned URL, and `aws-chunked` bodies. Its workerd process crashed once, and requests it should reject sometimes return 500 instead of 403. It is therefore adopted only with hard harness rules:
- Integrity is asserted by Content-MD5 or by reading the object back. Flexible checksums are never used for this.
- A fail-closed proxy rejects the request shapes Miniflare mishandles.
- Retry and error-class tests do not run against raw Miniflare.
- A crashed run is invalid; it is neither a pass nor a fail.
- The version is pinned through the lockfile, at no lower than wrangler 4.143.1 (miniflare 5.20260926.1-alpha), the first release with R2's 8 KiB metadata limit. A new pin is accepted only after the fidelity script passes on it.

**Secondary target.** **RustFS 1.0.0**, not SeaweedFS, is the second, AWS-shaped target for differential runs. SeaweedFS completed an upload with a stale part ETag and stored the old part data.

**Excluded.** MinIO community (archived), Garage (ignores conditional writes), moto (verifies no signatures) and LocalStack (needs an auth token).

**Real R2 stays the gate.** Every behaviour the protocol relies on is confirmed there before anything is claimed from it. That includes append-only enforcement, checksum handling, ListParts, lifecycle and the 429 race behaviour. The real-R2 kit is ready and blocked on the sandbox account and allowlist.

**Confidence: medium.** All 14 key claims are verified, but the comparison against real R2 has not run.

## Questions

| # | Question | Short answer | Confidence |
|---|---|---|---|
| 1 | Does Miniflare / `wrangler dev` support R2 **presigned URLs** locally? | **Yes**, since miniflare 4.20260722.1 / wrangler 4.115.0 (PR #14280). It is an experimental endpoint at `/cdn-cgi/local/r2/s3/<bucket-id>`, enabled per bucket by `r2_buckets[].local_dev.experimental_s3_credentials` (K2). **Run:** tamper, wrong-key, wrong-method, expiry and signed Content-Type checks were all rejected with 403 (T04–T08, T11). | High (source, changelog, emulated run) |
| 2 | Can **presigned multipart** run locally on Miniflare? | **Mostly.** Create, UploadPart, Complete and Abort work, including Worker-presigned parts (T30, W04). The 5 MiB minimum is enforced (T31). The equal-part rule is enforced, but it is **reported as 404 `NoSuchUpload`**, not an R2-style error (T32/T33). A stale part ETag gives `InvalidPart` and stores nothing (T34/T34b). **ListParts and ListMultipartUploads return 501** (T35, K6). Presigned POST returns 501, which matches R2, since R2 does not support it (T53). | High (emulated run) |
| 3 | Is **conditional create** (`If-None-Match: *`) honoured locally? | **On PutObject, yes:** 412 with the original kept (T20). 16 writers × 20 rounds gave exactly one winner per round, both header-signed (T26) and presigned (T27), as the source suggests (K5). **On CompleteMultipartUpload, no:** an existing key is overwritten (T38). R2's docs also list no conditional headers for Complete (K14). | High locally (emulated); unknown on R2 |
| 4 | Are **Queues HTTP pull consumers** emulated? | **No** (K7). wrangler refuses `type = "http_pull"` (evidence file), and the broker has no pull or ack route. ADR-0001 (Accepted) has the homelab pull queue events, so a pull path is part of the accepted architecture even though A0 v0 polls. See F5. | High |
| 5 | Are **R2 event notifications** emulated? | No route, option or doc statement was found. A0 does not use them. | Medium (absence) |
| 6 | **D1** local fidelity? | Cloudflare states that local D1 runs "the same version of D1 as Cloudflare runs globally". That is a vendor claim, not a measurement. **Run:** a D1 claim race (`INSERT … ON CONFLICT DO NOTHING`, 16-way × 10) gave exactly one winner per round (W05). Limits and latency are not emulated. | Medium |
| 7 | **MinIO** community status (PLAN exclusion rule) | **Archived** (K9): `archived=true`, last push 2026-04-24, README "NO LONGER MAINTAINED", source-only. **Excluded.** | High |
| 8 | Which standalone S3 servers are viable as a second target? | **RustFS 1.0.0** first, **versitygw v1.8.0** as fallback (versitygw has no lifecycle). **SeaweedFS** only as a negative control: it stores the old part on a stale ETag (T34b). **Garage** excluded: it ignores If-None-Match and If-Match, so 16 of 16 writers win (T20, T26; K10). **moto** verifies no signatures. **LocalStack** 2026.8.4 exits without an auth token. | High (emulated run) |
| 9 | When is a **real R2 bucket** required? | For every behaviour the protocol relies on (list in F4). This includes three behaviours no local target can show: append-only enforcement through signed `If-None-Match` and token scope, checksum validation, and 429 race losers. The cheapest route is hybrid `wrangler dev` with `remote: true` (K12). With `remote: true` the local S3 endpoint disappears for that bucket, so presigned URLs must point at the real R2 endpoint. | High |
| 10 | Worker test runner? | **`@cloudflare/vitest-plugin`** for Worker unit tests (K13; 1.3.1 on 2026-09-28, 1.3.6 by 2026-10-02). For end-to-end presigned flows, use `wrangler dev`, Miniflare's Node API, or Cloudflare's `createTestHarness()`. Whether each of these exposes the local S3 endpoint is untested (open question 4). | High (runner recommendation) / Low (endpoint availability) |
| 11 | Does the local endpoint work with standard SDK defaults? | **No.** It never answers `Expect: 100-continue`, so each request is **delayed** (not hung) until the client gives up waiting: 6.3–6.8 s for a 6 MiB PutObject with the AWS JS SDK, against 0.45–0.55 s without the middleware (S2, S5). A stream body with the default checksum setting returns 500 in 7 of 7 runs, and `WHEN_REQUIRED` fixes it (S3/S4). `aws-chunked` framing is stored as data (T44). `Transfer-Encoding: chunked` returns 500 (T46). The Rust SDK is untested. | High (JS SDK); open (Rust) |
| 12 | (new) Is the harness stable enough for CI? | **Not without a wrapper.** workerd crashed in 1 of 7 SDK runs and the port stayed dead for at least 45 s. Rejected requests with a body returned 500 instead of 403 in up to 29 of 50 tries. `wrangler dev` exited once with no logged cause (the container was shared, so the cause is undetermined). | Medium (one container, heavy shared load) |
| 13 | (new) Can the append-only property (R-18) be verified locally? | **No.** The local bucket has one full-power credential. Presigned DELETE works (T52), and a presigned PUT can be reused until it expires (T10). Token scoping is not emulated. The local harness can only assert what the Worker *mints*; enforcement is SB-only. | High |

## Method

- **Sweep:** a docs scout (cloudflare-docs source on raw GitHub, workers-sdk changelogs, npm registry, vendor READMEs) and a source scout (npm tarballs for miniflare and wrangler; Garage, SeaweedFS, versitygw and moto sources on raw GitHub; crates.io). No issues/forums or pricing scout, because they were out of scope for this slice.
- **Deep read:** the TypeScript sources in the source maps of `miniflare-5.20260926.0-alpha.tgz` (`src/workers/r2/s3/*.worker.ts`, `r2/bucket.worker.ts`), the wrangler 4.143.0 config validator, and the R2, Queues, D1 and Workers-testing doc pages listed under Sources.
- **Spike (G2-S1 emulated leg, 2026-09-29):**
  - Targets: Miniflare, RustFS, versitygw, SeaweedFS and Garage, plus moto on an earlier script revision.
  - `fidelity.py` (stdlib SigV4, byte-identical requests, about 750 per target) and the AWS JS SDK v3 defaults check `sdk_quirks.mjs`.
  - Code and results: `spikes/G2-S1/`. **Emulated, not real R2/Cloudflare.**
- **Skeptic review (2026-10-06):** three lenses (sources, logic, adversary) over K1–K14. None refuted any claim. Ten major issues were raised across the three lenses, most of them by more than one skeptic, plus several minor ones. All are addressed in "Skeptic issues and how they were handled".
- **Synthesizer re-reads (2026-10-06)** of the new facts the skeptics raised:
  - R2 `platform/limits.mdx`: 8,192-byte metadata; 1 write/s per key, and excess writes get 429.
  - miniflare CHANGELOG 5.20260926.1-alpha: #15910 raises the metadata limit to 8 KiB; #15906 preserves body length in `dispatchFetch`.
  - The pinned tarball's `getR2S3Service` skips remote buckets; `MAX_METADATA_SIZE: 2048`; the session-token screen is header-only.
  - R2 `api.mdx`: checksum table; the PutObject row lists Content-MD5 but no `x-amz-checksum-*`.
  - `workers/testing/index.mdx`: `createTestHarness()`.
  - npm registry times for wrangler 4.143.0, 4.143.1 and 4.144.0.
- **Routes used:** raw.githubusercontent.com (cloudflare-docs @ production, workers-sdk @ main, vendor repos), registry.npmjs.org, proxy.golang.org, pypi.org, crates.io, Docker Hub images, and GitHub MCP for repository archive flags.
- **Blocked sources (reported to H1):**
  - developers.cloudflare.com: the raw cloudflare-docs source was used instead (same content, but no commit dates).
  - api.github.com via curl: no per-page dates.
  - git.deuxfleurs.fr: Garage upstream; the GitHub mirror was used.
  - codeload.github.com tarballs.
  - `*.r2.cloudflarestorage.com` and `api.cloudflare.com`: these block the SB leg.
- **Stop rule:** two scouts and a deep read. The skeptics added four new primary facts, and all four were re-read at source.

### Scout conflicts resolved

| Topic | Resolution (primary) |
|---|---|
| Presigned expiry cap | `auth.worker.ts` rejects `expires > 604800`. 604,800 s is accepted, matching R2's "1 second to 7 days" (K8). Run: 604800 → 200, 604801 → 400 (T09). |
| Atomicity of local If-None-Match | One `db.txn` inside the bucket Durable Object (K5). Confirmed by the T26/T27 race (emulated). |
| Miniflare config key | Renamed twice in the 5.x alpha line. wrangler still accepts `local_dev.experimental_s3_credentials` (K2). Pin by lockfile. |
| Worker test package | `@cloudflare/vitest-plugin`, not `vitest-pool-workers` (K13). |
| Second S3 target | The draft said SeaweedFS. The spike showed SeaweedFS storing old part data on a stale ETag (T34b), so it is now **RustFS** (all three skeptics agreed). |

## Sources

All accessed 2026-09-29 unless marked; items re-read on 2026-10-06 are marked "re-read". Mirrors are cited as `repo @ branch : path`.

| # | Source | Publisher | Version / date | Accessed | Primary? |
|---|---|---|---|---|---|
| S1 | miniflare 5.20260926.0-alpha tarball, source maps `src/workers/r2/s3/*.worker.ts`, `r2/bucket.worker.ts`, `r2/constants.ts`, `queues/broker.worker.js`, `dist/src/index.js` (`getR2S3Service`, `MAX_METADATA_SIZE`) — https://registry.npmjs.org/miniflare/-/miniflare-5.20260926.0-alpha.tgz | Cloudflare | 2026-09-27 | 2026-09-29; re-read 2026-10-06 | Yes |
| S2 | miniflare CHANGELOG, `cloudflare/workers-sdk @ main : packages/miniflare/CHANGELOG.md` (4.20260722.1 #14280; 5.20260820.0-alpha #15130; #15318; 5.20260926.1-alpha #15906, #15910) | Cloudflare | main head | re-read 2026-10-06 | Yes |
| S3 | wrangler CHANGELOG, `… : packages/wrangler/CHANGELOG.md` (4.115.0 #14280) | Cloudflare | main head | 2026-09-29 | Yes |
| S4 | wrangler 4.143.0 tarball `wrangler-dist/cli.js` (config validator); https://registry.npmjs.org/wrangler (`time`, `dist-tags`, dependencies) | Cloudflare / npm | 4.143.0 2026-09-28T14:19Z; 4.143.1 2026-09-29T15:33Z; 4.144.0 2026-09-29T21:12Z (miniflare 5.20260926.1-alpha); latest 4.147.0 on 2026-10-06 | re-read 2026-10-06 | Yes |
| S5 | https://registry.npmjs.org/miniflare (dist-tags) | npm | latest 5.20261001.0-alpha on 2026-10-06 | re-read 2026-10-06 | Yes |
| S6 | Bindings per development mode, `cloudflare/cloudflare-docs @ production : src/content/partials/workers/bindings_per_env.mdx` | Cloudflare | production head | 2026-09-29 | Yes |
| S7 | Workers local development, `… : src/content/docs/workers/local-development/index.mdx` | Cloudflare | production head | 2026-09-29 | Yes |
| S8 | Queues local development, `… : docs/queues/configuration/local-development.mdx` | Cloudflare | production head | 2026-09-29 | Yes |
| S9 | Queues pull consumers, `… : docs/queues/configuration/pull-consumers.mdx` | Cloudflare | production head | 2026-09-29 | Yes |
| S10 | R2 presigned URLs, `… : docs/r2/api/s3/presigned-urls.mdx` | Cloudflare | production head | 2026-09-29 | Yes |
| S11 | R2 S3 API compatibility, `… : docs/r2/api/s3/api.mdx` (PutObject, UploadPart note, Complete, ListParts, ListMultipartUploads rows; checksum-type table) | Cloudflare | production head | re-read 2026-10-06 | Yes |
| S12 | R2 temporary credentials, `… : docs/r2/api/s3/temporary-credentials.mdx` | Cloudflare | production head | 2026-09-29 | Yes |
| S13 | R2 object lifecycles, `… : docs/r2/buckets/object-lifecycles.mdx` | Cloudflare | production head | 2026-09-29 | Yes |
| S14 | R2 event notifications, `… : docs/r2/buckets/event-notifications.mdx` | Cloudflare | production head | 2026-09-29 | Yes |
| S15 | D1 local development, `… : docs/d1/best-practices/local-development.mdx` | Cloudflare | production head | 2026-09-29 | Yes |
| S16 | Workers Vitest integration `… : docs/workers/testing/vitest-integration/index.mdx`; https://registry.npmjs.org/@cloudflare/vitest-plugin; https://registry.npmjs.org/@cloudflare/vitest-pool-workers | Cloudflare / npm | plugin 1.3.1 (2026-09-28), 1.3.6 (2026-10-02); pool 0.22.0 (2026-08-18) | 2026-09-29; skeptic re-check 2026-10-06 | Yes |
| S17 | Workers testing overview `… : docs/workers/testing/index.mdx` (`createTestHarness()` for integration tests) | Cloudflare | production head | 2026-10-06 | Yes |
| S18 | R2 limits `… : docs/r2/platform/limits.mdx` (object metadata 8,192 bytes; "Maximum concurrent writes to the same object name (key): 1 per second", footnote 5: HTTP 429) | Cloudflare | production head | 2026-10-06 | Yes |
| S19 | R2 upload objects `… : docs/r2/objects/upload-objects.mdx` ("All parts except the last must be the same size") | Cloudflare | production head | 2026-10-06 | Yes |
| S20 | MinIO README `minio/minio @ master : README.md`; repo metadata (archived=true, pushed 2026-04-24, AGPL-3.0) via GitHub MCP | MinIO | 2026-04-24 | 2026-09-29; skeptic re-check 2026-10-06 | Yes |
| S21 | LocalStack README `localstack/localstack @ main : README.md`; repo metadata (archived); `localstack/localstack:latest` = 2026.8.4 startup log | LocalStack | 2026-03-23 (repo) / 2026-09-23 (image) | 2026-09-29 | Yes |
| S22 | Garage known issues `deuxfleurs-org/garage @ main-v2 : doc/book/reference-manual/known-issues.md` (GitHub mirror of git.deuxfleurs.fr) | Deuxfleurs | mirror pushed 2026-09-28 | 2026-09-29 | Yes (mirror) |
| S23 | SeaweedFS README and `weed/s3api/s3api_object_handlers_put.go` (`seaweedfs/seaweedfs @ master`) | SeaweedFS | master head 2026-09-29 | 2026-09-29 | Yes |
| S24 | versitygw README and `s3api/controllers/object-put.go`; https://proxy.golang.org/github.com/versity/versitygw/@latest (v1.8.0) | Versity | 2026-09-04 | 2026-09-29 | Yes |
| S25 | RustFS README (`rustfs/rustfs @ main`); `rustfs/rustfs:1.0.0` image (created 2026-09-16) | RustFS | 1.0.0 | 2026-09-29 | Yes |
| S26 | s3s README (`Nugine/s3s @ main`); s3s-fs 0.17.0 | Nugine | 2026-09-24 | 2026-09-29 | Yes |
| S27 | moto CHANGELOG and `moto/s3/responses.py`; https://pypi.org/pypi/moto/json (5.2.3) | getmoto | master head | 2026-09-29 | Yes |
| S28 | **G2-S1 emulated-leg results**: `spikes/G2-S1/results/comparison.md`, `sdk-comparison.md`, `evidence/` | this project | run 2026-09-29 | 2026-09-29 | Yes (our own measurement, **emulated**) |
| S29 | alchemy-run/alchemy issue #1715 (search result only) | third party | unknown | 2026-09-29 | No (not relied on) |

## Claims

### Key claims (tally computed from the three skeptics; PLAN §5.1 rule)

All 14 key claims are **Verified**: each has a primary source, and all three skeptics declined to refute it. The "Qualification" column records corrections the skeptics required in wording or use. Those corrections are applied throughout this note.

| # | Claim | Sources | Sk1 sources | Sk2 logic | Sk3 adversary | Verdict | Qualification applied |
|---|---|---|---|---|---|---|---|
| K1 | wrangler 4.143.0 (npm `latest` on 2026-09-28) pins miniflare 5.20260926.0-alpha and workerd 1.20260926.1. The stable wrangler line ships the Miniflare 5 alpha. | S4, S5, S1 | Upheld | Upheld | Upheld | **Verified** | It is true only as a **dated snapshot**. 4.143.1 shipped on 2026-09-29, 4.144.0 the same evening, and `latest` was 4.147.0 / miniflare 5.20261001.0-alpha by 2026-10-02. The pin is therefore stated by lockfile, not as "npm latest" (see Recommendation). |
| K2 | Miniflare has an experimental local S3 endpoint at `/cdn-cgi/local/r2/s3/<bucket-id>` (miniflare 4.20260722.1 / wrangler 4.115.0, #14280). It is enabled by `r2_buckets[].local_dev.experimental_s3_credentials` and verifies SigV4 in both header and presigned form. | S2, S3, S1 | Upheld | Upheld | Upheld | **Verified** | The Miniflare-side key was renamed twice: `s3Credentials` → `localDev.experimentalS3Credentials` → `dev.experimentalS3Credentials`. |
| K3 | The local S3 endpoint and the Worker's R2 binding share one local store. | S1; S28 (W01–W04) | Upheld | Upheld | Upheld | **Verified** (locally) | **With `remote: true`, the endpoint is not served for that bucket** (`getR2S3Service` skips remote buckets; re-read). Whether binding and S3 multipart interoperate on real R2 is unknown (kit W04). The advantage only counts if C1 keeps the binding for Worker-side writes. |
| K4 | The source says the endpoint's errors and check order mimic R2's S3 endpoint, from a real-bucket capture dated 2026-06-11. | S1 | Upheld | Upheld | Upheld | **Verified** (as a statement about the source) | The capture data is not shipped, so it is weak fidelity evidence. The mimicry is partial: unequal parts give 404 `NoSuchUpload` (T32/T33), and rejected requests intermittently return 500. |
| K5 | Local PutObject `If-None-Match: *` is atomic (one `db.txn` in the bucket DO) and returns 412. Complete ignores conditional headers. | S1; S28 (T20, T26, T27, T38) | Upheld | Upheld | Upheld | **Verified** (locally) | It is **race-tested now**: exactly one winner in 20 of 20 rounds, header-signed and presigned. On R2, losers may get 429 (S18). |
| K6 | Local endpoint: ListParts, ListMultipartUploads and lifecycle return NotImplemented. Flexible checksums are ignored, `aws-chunked` is not decoded, `100 Continue` is never sent, and `x-amz-security-token` is rejected. R2 implements ListParts, lifecycle, checksums and temporary credentials. | S1, S11, S12; S28 | Upheld | Upheld | Upheld | **Verified** | (a) The effect is a **delay**, not a hang (S2/S5). (b) Only the **header** form of the token is screened; a query-form `X-Amz-Security-Token` fails as `SignatureDoesNotMatch`. (c) R2's docs list **no `x-amz-checksum-*` on PutObject**, and SHA-256 is COMPOSITE-only in the checksum table. "R2 validates SHA-256 checksums on single-part or presigned PUT" is therefore **not documented** (see N3). |
| K7 | Miniflare does not emulate Queues HTTP pull. The broker has only `/message` and `/batch`, there is no pull route, and wrangler rejects non-`worker` consumers. | S1, S4, S3; S28 evidence | Upheld | Upheld | Upheld | **Verified** | The wrangler rejection is a config rule that also applies on deploy. The proof of absence locally is the broker source. |
| K8 | The presigned expiry cap is 604,800 s inclusive, locally and in R2's docs. | S1, S10; S28 (T09) | Upheld | Upheld | Upheld | **Verified** | Not measured on R2 yet (kit). The BUD-REVOKE link is narrowed to "expiry enforcement mechanism (T08)". The 7-day cap does not bear on the 15-minute target. |
| K9 | minio/minio is archived and source-only, so it is excluded under the PLAN rule. | S20 | Upheld | Upheld | Upheld | **Verified** | — |
| K10 | Garage documents conditional writes as structurally impossible. | S22; S28 (T20, T26) | Upheld | Upheld | Upheld | **Verified** | Confirmed empirically (16 of 16 writers win). |
| K11 | SeaweedFS claims conditional writes, lifecycle, presign and multipart, and re-runs preconditions under a per-object lock. | S23 | Upheld | Upheld | Upheld | **Verified** (as a statement of vendor claims) | **Its use is withdrawn:** T34/T34b contradict R2's documented part replacement, so SeaweedFS is no longer the secondary target. |
| K12 | R2, D1 and Queues bindings can be `remote: true` while the Worker runs locally. Durable Objects cannot, and `--local` disables all remote bindings. | S6, S7 | Upheld | Upheld | Upheld | **Verified** | Remote bindings need wrangler account auth (OAuth or an API token), not just a bucket-scoped S3 token. A Queues remote binding gives no local pull consumer. |
| K13 | Cloudflare recommends `@cloudflare/vitest-plugin` and provides a migration guide from `vitest-pool-workers`. | S16 | Upheld | Upheld | Upheld | **Verified** | The version is dated: 1.3.6 by 2026-10-02. The same docs recommend `createTestHarness()` for integration tests (S17). |
| K14 | R2's S3 table lists no conditional headers for CompleteMultipartUpload, but implements ListParts and ListMultipartUploads. | S11 | Upheld | Upheld | Upheld | **Verified** | "Per-upload keys carry create-only" is an A3/C1 design conclusion (OD-04), not a fact from the table. |

Contested claims: **none**. Secondary-only claims: none load-bearing. S29 is not relied on.

### Supporting claims (not key; outside the skeptic tally)

These are new facts the skeptics raised. The synthesizer re-read each one at source on 2026-10-06, but they did **not** go through the three-skeptic tally, so none of them is the sole support for any recommendation.

| # | Claim | Source | Status |
|---|---|---|---|
| N1 | R2 allows 1 write per second to the same key; excess writes get HTTP 429. | S18 | Primary, re-read; not tallied |
| N2 | R2 object metadata limit is 8,192 bytes. The pinned miniflare 5.20260926.0-alpha has `MAX_METADATA_SIZE: 2048`. 5.20260926.1-alpha (#15910; shipped in wrangler 4.143.1 and 4.144.0, both 2026-09-29) raises it to 8 KiB, including for S3 multipart initiation (`MetadataTooLarge`). | S18, S1, S2, S4 | Primary, re-read; not tallied |
| N3 | R2 `api.mdx`: the PutObject row lists Content-MD5 but no `x-amz-checksum-*` headers. In the checksum table, CRC64NVME is FULL_OBJECT only and SHA-256 is COMPOSITE only. | S11 | Primary, re-read; not tallied |
| N4 | R2: "Uploading to the same part number replaces the previous part. If a subsequent upload to the same part fails, the original part is lost and must be re-uploaded." | S11 | Primary, re-read; not tallied |
| N5 | miniflare 5.20260926.1-alpha (#15906) preserves the request body length in `Miniflare#dispatchFetch()`. Previously such bodies failed with "Provided readable stream must have a known length", the same message as in T46 and SDK S3. Whether this changes the S3-endpoint results is **untested**. | S2 | Primary; relevance unverified |
| N6 | Cloudflare recommends `createTestHarness()` for Worker integration tests. | S17 | Primary, re-read; not tallied |

## Findings

### F1. What the A0 harness needs (from A0 and A3)

A0 v0 uses: presigned single PUT and presigned UploadPart from a Rust CLI; Create and Complete through the Worker; a per-upload staging key with conditional create; D1; a homelab puller that lists, gets and deletes; and an expiring `restore/` prefix. A0 v0 polls instead of using Queues. A3 adds ListParts adoption on resume, abort-only lifecycle on `staging/` and `meta/`, and expiry on `restore/`. A3 keeps the pull consumer as an optional latency hint (A3 note, Q6), which matches ADR-0001's "notification path plus reconcile".

The local target must at least: (a) accept Worker-minted presigned PUT and UploadPart URLs; (b) share one store with the Worker's R2 access; (c) enforce multipart part-size rules; (d) honour If-None-Match on PutObject; (e) serve List, Get and Delete with header SigV4. It must also (f) **never report success for bytes it did not store faithfully**. Requirement (f) is new and comes from the skeptic review, given "data integrity over everything".

*Assumptions handed to other workstreams, not decided here:* that the production Worker writes through the R2 binding rather than the S3 API (C1, ADR-0010); that resume uses a client ETag journal where ListParts is unavailable (A3/CE); and that per-upload keys, not conditional Complete, carry create-only (A3/C1, OD-04).

### F2. Miniflare against (a)–(f): emulated results

Every row below comes from the emulated run (S28) and is **not real R2/Cloudflare**.

| Need | Miniflare | RustFS 1.0.0 | versitygw 1.8.0 | SeaweedFS 4.48 | Garage 2.4.1 |
|---|---|---|---|---|---|
| (a) presigned PUT and UploadPart | ✅ (T02, T30, W01, W04, SDK S6) | ✅ | ✅ | ✅ | ✅ |
| (b) one store with the Worker binding | ✅ **only Miniflare** (W01–W04) | ✗ (the Worker would have to use the S3 API) | ✗ | ✗ | ✗ |
| (c) R2 part rules (5 MiB minimum; equal parts) | ✅ / ✅ but **wrong code** (404 `NoSuchUpload`, T32/T33) | ✅ / ✗ (AWS rule) | ✅ / ✗ | ✅ / ✗ | ✗ / ✗ |
| (c′) part replacement with a stale ETag → `InvalidPart` | ✅ (T34, T34b) | ✅ | ✅ | **✗ stores the old part** | ✅ |
| (d) If-None-Match on PutObject, incl. 16-way race | ✅ (T20, T22, T23, T26, T27) | ✅ | ✅ | ✅ | **✗ 16 of 16 win** |
| (e) List, Get, Delete over header SigV4 | ✅ (T50, T51) | ✅ | ✅ | ✅ | ✅ |
| (f) no silent wrong bytes | **✗** wrong checksum stored (T41); tampered body stored despite a signed checksum (T47); `aws-chunked` framing stored (T44). Content-MD5 enforced (T40, T48) | ✅ | ✅ | ✅ (T41/T47); ✗ (T34b) | ✅ (T41/T47) |
| Complete with If-None-Match on existing key | Overwrites (T38). R2 lists no conditional headers here, so this may be R2-like | 412 (AWS) | 412 | 412 | Overwrites |
| ListParts / ListMultipartUploads | 501 (T35) | 200 | 200 | 200 | 200 |
| Lifecycle configuration | 501 (T54) | 200 | 501 | 200 | 200 |
| Auth and expiry checks | ✅ (T04–T13) | ✅ | ✅ | ✅ | ✅ (different codes; T12 skew not checked) |

**Reading.** Miniflare is the best fit for (a)–(e). It is the only target with (b) and the only one enforcing R2's equal-part rule, although with a misleading code. On (f) it is the **worst** target. That does not disqualify it, but it decides how the harness must use it (F3). RustFS is the best AWS-shaped complement. It passes (f), and its only deviations from Miniflare on relied-on checks are AWS-shaped: T32/T33 (no equal-part rule), T38 (conditional Complete returns 412) and T39 (304 on CreateMultipartUpload with If-None-Match). versitygw is similar to RustFS but has no lifecycle support.

**A caution about RustFS.** Its 412 on a conditional Complete (T38) is *safer-looking* than R2's documented behaviour. A protocol bug that wrongly relied on conditional Complete would pass on RustFS and fail on R2. Differential runs must therefore treat Miniflare's overwrite, not RustFS's 412, as the expected R2 shape until SB measures it.

### F3. Harness rules for the local stack (the gaps, and what the harness does about each)

Rows marked **rule** are binding on the A0 harness (ADR-0035, decision 2). The others are handling notes.

| Gap (evidence) | Impact | Handling |
|---|---|---|
| **Silent integrity failures:** wrong `x-amz-checksum-*` stored (T41); a checksum signed into a presigned URL does not stop a tampered body (T47); `aws-chunked` framing stored as data (T44); STREAMING-* payload hashes skip body verification (S1 `auth.worker.ts`) | Any integrity test built on flexible checksums passes falsely. This is the most dangerous gap, given R-39. | **Rule:** a fail-closed screening proxy sits in front of the local S3 endpoint. It rejects, with a loud 501, any request carrying `x-amz-checksum-*`, `x-amz-sdk-checksum-algorithm`, `Content-Encoding: aws-chunked`, a `STREAMING-*` `x-amz-content-sha256` or `Transfer-Encoding: chunked`. **Rule:** local integrity assertions use signed Content-MD5 (T40, T48 pass) or a read-back SHA-256 by the homelab. **Rule:** no checksum-based control is claimed from local runs; it is tested on RustFS (differential) and on SB (C1-S1; kit T41–T43, T47). |
| Whether R2 validates SHA-256 flexible checksums on single-part or presigned PUT is **undocumented** (N3) | If A2/A3 plan a signed `x-amz-checksum-sha256` in presigned URLs as a tamper defence, it rests on Miniflare's source comment alone | The spike's "[doc]" tag on T41 is downgraded to **[unverified; Miniflare comment only]**. This is an explicit SB question for C1-S1. Until it is answered, the design must not rely on server-side checksums. The end-to-end check is the homelab's own hash and HMAC verification (ADR-0001). |
| Equal-part violation reported as 404 `NoSuchUpload` (T32/T33) | A client that treats `NoSuchUpload` on Complete as "upload gone, restart" takes a different path locally than on R2 | **Rule:** no test asserts the error *code* for part-size violations locally, only that Complete fails and nothing is stored. The client must not treat `NoSuchUpload` on Complete as terminal in tests. The R2 code is measured on SB (kit T32/T33). |
| Instability: workerd crash (1 of 7 runs, port dead ≥ 45 s); rejected-with-body requests returning 500 instead of 403 (2/50 at 1 B, 29/50 at 64 KiB, 12/50 at 1 MiB); one unexplained exit | Flaky CI. Retry-classification tests (5xx retryable, 403 terminal) are confounded. | **Rule:** the harness health-checks the endpoint and restarts `wrangler dev`. A run with a crash is **invalid** (neither pass nor fail) and is re-run. **Rule:** retry and error-classification assertions do not run against raw Miniflare. They run behind the harness fault-injection proxy (deterministic, R2-documented faults), on RustFS, or on SB. **Follow-up:** try driving Miniflare through its Node API (no wrangler ProxyWorker), or a pin with #15906, and record whether the 500s go away (open question 6). |
| No 429 on same-key writes (N1; no local target emulates it) | Claim and commit retry logic never sees 429 as a race-loser outcome | **Rule:** the fault proxy can inject 429 for a second write to the same key within 1 s. Hand-off to A3: a 412 on a staging key is never treated as success without a content or ETag check, and a 429 is never treated as "taken". This is confirmed on SB (kit T26/T27 records 412 vs 429). |
| Custom-metadata limit is 2 KiB in the 4.143.0 pin vs R2's 8 KiB (N2) | False local failures if A2/A3 put wrapped keys or envelope data in metadata | **Rule:** pin wrangler ≥ 4.143.1 (miniflare ≥ 5.20260926.1-alpha). Add an 8 KiB `x-amz-meta-*` check on PutObject and CreateMultipartUpload to `fidelity.py`. |
| ListParts / ListMultipartUploads 501 (T35) | The resume-with-adoption path cannot run locally | Tested on RustFS (differential) and on SB. **Not on SeaweedFS:** adoption is ETag-matched, which is exactly where SeaweedFS is wrong (T34b). The ETag-journal fallback is A3/CE's design. Its R2 edge case is N4: a failed re-upload loses the part, so on `InvalidPart` the client re-uploads from source and does not trust the journal (hand-off to A3/B6). |
| No lifecycle (T54) | A0-S3 "objects expire by lifecycle rule" cannot pass locally | A test-clock-driven lifecycle sweeper in the harness, labelled **emulated**. The real rule and the default 7-day abort are SB-only. |
| `Expect: 100-continue` never answered (T45; S2 6.3–6.8 s vs S5 0.45–0.55 s) | Each SDK upload is delayed by the client's continue timeout | Disable expect-continue in SDK clients. Presigned uploads from a plain HTTP client are unaffected. The Rust SDK is untested (open question 3). |
| SDK default checksum with stream body → 500 (S3, 7 of 7) | The homelab or Worker S3 client fails locally while it would work on R2 | Set `requestChecksumCalculation = WHEN_REQUIRED` (or the Rust SDK equivalent). The screening proxy makes any slip loud. |
| `x-amz-security-token` header rejected (400); query form fails as `SignatureDoesNotMatch` (K6) | R2 temporary credentials cannot be tested locally | SB-only, if C1 or D3 chooses temporary credentials. That would also change the recommendation (see "What would change this"). |
| **Append-only (R-18) not enforceable locally (Q13):** one full-power credential; presigned DELETE works (T52); a presigned PUT can be reused to overwrite until expiry (T10); token scope not emulated | A compromised-device test that passes locally proves nothing about R2 | **Rule:** harness assertions on what the Worker **mints**: never DELETE, GET or HEAD URLs for device credentials, and every device PUT URL has `if-none-match` in `X-Amz-SignedHeaders`. **SB:** T23 (signed If-None-Match enforced) and T25 (an attacker who strips or alters the signed header gets 403) are the primary R2 checks. T22 (unsigned header honoured) is secondary, because an attacker would simply omit it. Token-scope enforcement is SB-only (D4 attack suite). |
| Queues HTTP pull not emulated (K7) | ADR-0001's queue path has no local substrate; A0 v0's polling does not exercise it | See F5. |
| Experimental status; config-key churn (K2) | An upgrade can break the harness | **Rule:** pin by lockfile with integrity hashes (`npm ci`). Re-run `fidelity.py` and `sdk_quirks.mjs` on every bump and diff against the 2026-09-29 baseline before accepting it. |
| Path-prefixed endpoint (`/cdn-cgi/local/r2/s3/<bucket>`) | The S3 client must accept an endpoint URL with a path | Works with aws4fetch and the AWS JS presigner (W01, S6). Not yet tried with the Rust client (open question 3). |

### F4. When a real R2 bucket is required

Real R2 (sandbox account, [SB]) is required for every behaviour the protocol relies on. In particular:
- `If-None-Match` on a **presigned** PUT, signed (T23, T25) and unsigned (T22);
- Complete with conditional headers, repeated Complete, and UploadPart after Complete (T37, T38);
- R2's error code for part-size violations (T32, T33);
- ListParts adoption (T35);
- lifecycle and the default 7-day abort (T54);
- checksum handling (T41–T43, T47);
- temporary credentials;
- event notifications and pull consumers;
- binding and S3 multipart interop (W04);
- 412 vs 429 race losers (T26, T27);
- 5xx behaviour, latency and consistency under load;
- token-scope enforcement for append-only;
- whether rotating or deleting the R2 token invalidates outstanding presigned URLs (needed for BUD-REVOKE; hand-off to D3-S5);
- every A0 measurement feeding C4 and ADR-0009/0010.

**Hybrid route.** The cheapest route is the same `wrangler dev` harness with `remote: true` on the R2 (and optionally D1) binding (K12). Two constraints apply:
1. With `remote: true` the local S3 endpoint **disappears** for that bucket (K3 qualification). The Worker's presigner must switch endpoint *and* credentials to `<account>.r2.cloudflarestorage.com` and a real R2 token, so presigner endpoint and credentials must be config-driven per mode.
2. Remote bindings need wrangler to be authenticated to the sandbox account (OAuth or a scoped API token), not just the bucket-scoped S3 token.

Both routes need the H1 allowlist (`*.r2.cloudflarestorage.com`, `api.cloudflare.com`). That is blocked today.

### F5. Queues pull path (skeptic: conflict with Accepted ADR-0001)

ADR-0001 (Accepted) states that the homelab "pulls events from the queue", as a notification path backed by reconciliation. Miniflare cannot emulate HTTP pull (K7). A0 v0's polling is a provisional skeleton choice, not a change to ADR-0001, so the harness must plan for the queue path by default. It is not optional:

- **A0 emulated runs do not exercise ADR-0001's queue path**, and A0 reports must say so.
- **Wave 2, default component:** a harness fake of the pull/ack REST API. It needs batch, visibility timeout, ack and retry, retention, and the `api.cloudflare.com` 1,200 requests per 5 minutes limit with its 5-minute 429 lockout (A3 note). An alternative to consider then: a **real sandbox queue** used through the REST API from the harness, which avoids maintaining a fake but needs SB access.
- Dropping Queues would need a superseding ADR from A3/C1. This note does not assume that outcome.

### Skeptic issues and how they were handled

| Issue (severity, lenses) | Handling |
|---|---|
| SeaweedFS still named as secondary despite T34b (major; all three) | **Fixed.** RustFS 1.0.0 is secondary and versitygw the fallback. SeaweedFS is a negative control only, and is dropped from the ListParts-adoption path. |
| Draft not reconciled with spike results (major; all three) | **Fixed.** The Questions, F2, F3, Claims and Spikes sections are rewritten from S28. "Hang" is corrected to "delay", `NoSuchUpload` is recorded, the race is closed, and the budget citation is aligned. |
| Silent-corruption gaps understated (major; all three) | **Fixed.** Fail-closed screening proxy plus Content-MD5 or read-back rules (F3, ADR-0035 decision 2). |
| R2 checksum validation is not documented (major; adversary) | **Fixed.** Downgraded to unverified (N3); added as an SB question for C1-S1; no reliance until it is answered. |
| Append-only cannot be exercised locally (major; adversary) | **Fixed.** Harness minting assertions, with T23/T25 as primary SB checks (F3, Q13). |
| 2 KiB vs 8 KiB metadata in the pin (major; sources) | **Fixed.** Pin ≥ 4.143.1 (the skeptic proposed 4.144.0; the registry shows 4.143.1 already ships the fix), and a new `fidelity.py` check is requested (N2). |
| Harness instability not weighed (major; sources, logic) | **Fixed.** Health check and restart, invalid-run rule, no retry tests on raw Miniflare, and a new "what would change this" trigger. |
| Queues pull treated as optional against ADR-0001 (major; logic) | **Fixed.** F5: a default planned component; dropping Queues is a superseding-ADR matter. |
| Hybrid mode removes the local S3 endpoint (minor) | **Fixed** (F4, K3), and confirmed in source. |
| R2 per-key 429 missing (minor; three lenses) | **Fixed** (N1, F3, G2-S2 fault model). |
| Session-token rejection is header-only (minor) | **Fixed** (K6 qualification). |
| Versions quoted as current (minor) | **Fixed.** Every version is dated, and pinning is by lockfile. |
| Unit-test runner does not cover presigned flows (minor) | **Fixed.** Runners are split: vitest-plugin for unit tests; `wrangler dev`, Miniflare's API or `createTestHarness()` for end-to-end (open question 4). |
| DST fault model mixes emulator artifacts with R2 behaviour (minor; logic) | **Fixed** in the G2-S2 plan below. Each fault is tagged R2-documented, SB-measured or emulator-artifact. `NoSuchUpload` on part sizes and 500-on-reject are emulator artifacts, and they are not expected R2 codes. |
| BUD-REVOKE citation a stretch; revocation lever untested (minor; logic) | **Fixed.** The citation is narrowed to T08. Token-rotation invalidation is handed to D3-S5 and added to the kit errata. |
| Design choices from other workstreams stated as givens (minor; logic) | **Fixed.** F1 lists them as assumptions, and "C1 picks the S3 API" is added to the change triggers. |
| Decision-request framing inconsistent (minor; logic) | **Fixed.** It is a clarification routed through H1 to OD-14, with option 2 rewritten around RustFS. |
| Hybrid-leg kit underspecifies credentials; W05 uses local D1 (minor; adversary) | **Recorded as kit errata** (Spikes). This stage does not edit the kit. |
| Supply-chain risk of the npm toolchain holding sandbox credentials (minor; adversary) | **Fixed**: `npm ci` from the lockfile; a sandbox-only account; revoke the R2 *and* wrangler tokens after each SB run. Handed to D5/G1. |
| ETag journal R2 edge case (N4) (minor; adversary) | **Fixed** (F3 row), handed to A3/B6. |

### Alternatives compared

| Option | Fit with settled requirements | Pros | Cons | Evidence |
|---|---|---|---|---|
| **A. Miniflare / `wrangler dev` + local R2 S3 endpoint** (recommended primary) | Good: Cloudflare-only stack (ADR-0001); local only | One store for binding and S3; only target with R2's equal-part rule; clean conditional-create race; D1 in the same process; MIT | Experimental, alpha line, key churn; **silent wrong bytes on checksums and aws-chunked**; instability; no ListParts, lifecycle, pull or temporary credentials; misleading `NoSuchUpload` | K2–K7, F2, F3 |
| **B. RustFS 1.0.0** (recommended secondary, differential only) | Neutral (test only); Apache-2.0 | Passed every relied-on check apart from its AWS-shaped deviations; rejects bad checksums and decodes aws-chunked; ListParts and lifecycle configuration | AWS-shaped (no equal-part rule; 412 on conditional Complete masks R2's overwrite); not the binding's store; young 1.0; image digest not yet recorded | S28, S25 |
| C. versitygw (posix) (fallback secondary) | Neutral; Apache-2.0 | Single binary over a directory; same results as RustFS on relied-on checks | No lifecycle (T54 501); AWS-shaped | S28, S24 |
| D. SeaweedFS `weed mini` (negative control only) | Neutral; Apache-2.0 | Lifecycle, ListParts, checksums, presign | **Stores the old part on a stale ETag (T34b)**, against R2's documented part replacement | K11, S28 |
| E. Garage | AGPL (only matters if code is reused) | Presign, multipart | **Ignores conditional writes** (K10, T26: 16/16); no 5 MiB minimum | K10, S28 |
| F. MinIO community | — | Former reference | **Archived; source-only** → excluded | K9 |
| G. LocalStack | Paid-plan image; Hobby plan needs an auth token | Broad AWS emulation | Exits with code 55 without `LOCALSTACK_AUTH_TOKEN`; AWS semantics, not R2. Not evaluated beyond startup | S21, S28 |
| H. moto (server mode) | — | Easy Python mocks | **Verifies no signatures** (T04–T13 all 200); AWS conditional Complete | S27, S28 |
| I. s3s-fs | — | In-process Rust mock | Not run (time and disk); sample code; auth off by default | S26 |
| J. Real R2 only (sandbox) | Good | Ground truth | Blocked today; costs money; slow inner loop; secrets in CI | K12 |
| K. A fail-closed or fault proxy in front of A (adopted as part of A) | Good | Makes silent gaps loud; injects R2-documented 429 and 5xx deterministically | Must be written (small) | F3 |
| L. An R2-semantics shim in front of RustFS (enforcing equal parts, ignoring conditional Complete) | Neutral | R2-shaped target that keeps real checksum handling | More code to keep in sync; not needed while A plus the proxy covers the gaps. **Deferred to Wave 3** | skeptic proposal |

**Not evaluated** (missed alternatives the skeptics raised; each needs at least a one-line reason before ADR-0035 is final in Wave 3):
- Ceph RGW and the `ceph/s3-tests` conformance suite. These are heavy, but s3-tests could be a broader fidelity method alongside `fidelity.py`.
- Zenko CloudServer.
- Adobe S3Mock and gofakes3 (lightweight mocks to use instead of moto).
- AIStor Free (MinIO's successor under a proprietary licence).
- An in-process deterministic R2 model in Rust (on s3s) for the G2-S2 DST harness. A DST harness cannot drive Miniflare deterministically, so this is the likely DST answer. It belongs to the Wave 3 decision.

### Similar work and lessons

| Project | What they do | Borrow or avoid | Source |
|---|---|---|---|
| Miniflare's own design note | Copies R2 errors from a real-bucket capture and documents every gap in the source header | **Borrow** the format (gap, impact, handling) for our fidelity table, re-run on each bump. **Avoid** trusting the capture claim without our own SB leg (K4). | S1 |
| alchemy-run/alchemy #1715 | Users asked for a local R2 S3 endpoint for presigned uploads | Confirms the need; not relied on | S29 |

### Tools and libraries

| Name | Purpose | Licence | Maturity (dated) | Source |
|---|---|---|---|---|
| wrangler | Local dev, config | MIT OR Apache-2.0 | 4.143.0 tested (2026-09-28); recommend ≥ 4.143.1 (2026-09-29); latest 4.147.0 on 2026-10-06 | S4 |
| miniflare | Local runtime (Workers, D1, R2 + S3 endpoint, Queues push) | MIT | 5.20260926.0-alpha tested; 5.20261001.0-alpha latest on 2026-10-06 | S1, S5 |
| @cloudflare/vitest-plugin | Worker unit tests on Miniflare | MIT | 1.3.1 (2026-09-28); 1.3.6 (2026-10-02) | S16 |
| `createTestHarness()` (wrangler) | Worker integration tests from any Node runner | MIT OR Apache-2.0 | in wrangler 4.143.0 per skeptic; untried here | S17 |
| RustFS | Secondary differential S3 target | Apache-2.0 | 1.0.0 (image 2026-09-16) | S25, S28 |
| versitygw | Fallback secondary | Apache-2.0 | v1.8.0 (2026-09-04) | S24, S28 |
| SeaweedFS | Negative control (part replacement) | Apache-2.0 | 4.48 @ 5da137233d1a (2026-09-29) | S23, S28 |
| Garage, MinIO, LocalStack, moto | Excluded (reasons above) | AGPL / AGPL / proprietary image / Apache-2.0 | — | S20–S22, S27 |

## Spikes

| Spike | Hypothesis | Pass → / fail → (decision) | Exec tag | Budget IDs | Data class | Status | Result |
|---|---|---|---|---|---|---|---|
| **G2-S1 (emulated leg)** | The same presigned-multipart and conditional-create script behaves the same on Miniflare's local R2 S3 endpoint and on the standalone servers for every behaviour A0/A3 rely on. **Emulated, not real R2/Cloudflare.** | Pass → Miniflare primary with a differential secondary; fail → document each difference and shim it, or move that behaviour to SB-only | SB, run as CT (**emulated**) | BUD-REVOKE (expiry mechanism only: T08, T09) | `SYN → results` | **Done (emulated)** | **Inconclusive by design:** the pass criterion needs real R2. Local-vs-local findings are in F2 and F3: Miniflare is the only shared store and the only one enforcing equal parts; its conditional-create race is clean; it stores wrong bytes silently (T41, T44, T47); it is unstable; RustFS is the best secondary; SeaweedFS fails T34b; Garage and moto are unfit. Evidence: `spikes/G2-S1/README.md`, `spikes/G2-S1/results/comparison.md`, `spikes/G2-S1/results/sdk-comparison.md`, `spikes/G2-S1/results/evidence/` |
| **G2-S1 (real R2 leg)** | Real R2 matches Miniflare on every relied-on check, and differs only on Miniflare's documented gaps | Pass → Miniflare confirmed for A0; fail → each difference goes into A0's difference list and ADR-0035. Where RustFS or versitygw matches R2 on a check, use it for that behaviour; otherwise the behaviour is SB-only | SB (kit) | BUD-REVOKE (expiry mechanism only) | `SYN → results` | **Kit-ready**; blocked on the sandbox account and allowlist | — Kit: `docs/research/kits/G2-S1/README.md` |
| G2-S2 DST | Over 10k seeds, the client, claim/commit and reconcile never report "safe" without a verified homelab copy and never lose data | Pass → DST gate in CI; fail → fix and add the seed to the regression set | CT (build) | — | `SYN → results` | Deferred (build; Wave 3 picks turmoil or madsim) | Plan: one harness around the Rust core and a model of the Worker API, with a simulated R2 whose faults are **tagged by source**. R2-documented: 412 or 429 race losers (N1); Complete not conditional (K14); a failed part re-upload loses the part (N4). SB-measured: pending the kit. Emulator artifacts, to inject only as extra chaos and never as expected R2 codes: `NoSuchUpload` on part sizes, 500 on rejected requests. Also injected: partitions, kill -9 at every await, clock skew, outages longer than 7 days. |
| G2-S3 Fuzz | 24 CPU-hours of fuzzing the manifest and metadata parsers produce no panics or OOMs | Pass → corpus committed; fail → fix | CT (build) | — | `SYN → results` | Deferred (no parsers yet; A2/A4 formats) | Plan: cargo-fuzz or bolero targets per homelab-facing parser, seeded from A2/A4 golden vectors. |
| G2-S4 Proxmox lab | A VM lab lets B7-S2 be reset and re-run in under 10 min per OS | Pass → lab adopted for desktop gates | OL | — | — | Deferred to Wave 3 (device-matrix work) | — |

**Kit errata for the real-R2 leg.** This stage does not edit the kit; apply these before the SB run.
1. Step 6, hybrid: run `wrangler login` against the **sandbox** account, or use a scoped API token that can start a remote proxy session. Revoke it afterwards, along with the R2 token.
2. Step 6: `remote = true` removes the local S3 endpoint for that bucket. `S3_BASE`, `S3_AK` and `S3_SK` must point at real R2, as the kit already says. In that leg, W04 tests the remote binding plus real S3.
3. W05 in the hybrid leg uses **local** D1 unless the D1 binding also gets `remote = true` on a sandbox database. Label it accordingly.
4. Re-tag T41, T42, T43 and T47's R2 expectation from "[doc]" to "[unverified; Miniflare comment only]" (N3).
5. Add the 8 KiB metadata check (N2), and add a check for whether deleting or rotating the R2 token invalidates an already-minted presigned URL. Share the second with D3-S5.
6. Run with `npm ci` from the lockfile. Use the newest wrangler at or above 4.143.1 that has passed the emulated leg, and record its version.

## Conflicts with settled text

None that this note resolves. Two items were raised by the skeptics and are addressed, not resolved here:
- **ADR-0001 (Accepted), "pulls events from the queue":** the harness cannot emulate it. F5 makes the pull/ack substrate a default Wave 2 component. Any move away from Queues is for A3/C1 as a superseding ADR.
- **CLAUDE.md "data integrity over everything" and "devices can only append":** the recommended local store cannot verify checksum-based integrity or append-only enforcement. The harness rules in F3 forbid claiming either from local runs.

## Open questions

| # | Question | Who answers | By when |
|---|---|---|---|
| 1 | Does every relied-on behaviour match between Miniflare and real R2? In particular T22/T23/T25, T32/T33, T37/T38, T26/T27 (412 vs 429), T35, T41–T43/T47 and W04. | G2-S1 real leg with C1-S1 (SB) | Gate B |
| 2 | Does R2 reject a tampered body when `x-amz-checksum-sha256` or `-crc64nvme` is signed into a presigned PUT? | C1-S1 (SB) | Before A2/A3 rely on it |
| 3 | Does the Rust S3 client (aws-sdk-s3 or rusty-s3) work against the path-prefixed endpoint with expect-continue off and checksums `WHEN_REQUIRED`? | A0 build, re-running `sdk_quirks` in Rust | A0 |
| 4 | Is the local S3 endpoint reachable from an external HTTP client under `@cloudflare/vitest-plugin`, `createTestHarness()` and the Miniflare Node API? | A0 build / G2 | A0 |
| 5 | Does a newer pin (≥ 4.143.1, with #15906) change T46, SDK S3 or the 500-instead-of-403 rate? | G2 re-run of `fidelity.py` on the bump | Before A0 pins |
| 6 | Do the 500s on rejected requests disappear when Miniflare is driven through its Node API, without wrangler's ProxyWorker? | G2 / A0 harness | A0 |
| 7 | Does rotating or deleting the R2 API token invalidate outstanding presigned URLs on R2 (BUD-REVOKE lever)? | D3-S5 (SB) | Gate C |
| 8 | What fidelity does the Wave 2 pull/ack fake need, and is a real sandbox queue cheaper to maintain? | G2 with A3 | Wave 2 |
| 9 | Will the local S3 endpoint graduate from experimental or change shape again? | Watch the changelog on each pin bump | Ongoing |
| 10 | The skeptics raised alternatives that were not evaluated: s3-tests, CloudServer, S3Mock, gofakes3, AIStor Free, a Rust R2 model for DST. | G2 Wave 3 | ADR-0035 final |

## Recommendation

1. **Primary local target.** Use `wrangler dev` (Miniflare) with the experimental local R2 S3 endpoint as the A0 local target, configured with `r2_buckets[].local_dev.experimental_s3_credentials`.
   - Pin it through the lockfile (`npm ci`), at no lower than **wrangler 4.143.1 / miniflare 5.20260926.1-alpha**. That is the first wrangler release with R2's 8 KiB metadata limit.
   - Accept a pin only after `fidelity.py` and `sdk_quirks.mjs` pass on it and match the 2026-09-29 baseline. That baseline was taken on wrangler 4.143.0.
   - Run Worker unit tests with `@cloudflare/vitest-plugin`. Run end-to-end presigned flows on `wrangler dev`, the Miniflare Node API or `createTestHarness()`, whichever exposes the endpoint (open question 4).
   - Support: K2, K3, K5 and K13 (all verified) and the emulated run.
2. **Use it only under the F3 harness rules.**
   - A fail-closed screening proxy in front of the S3 endpoint.
   - Integrity is asserted only by Content-MD5 or read-back.
   - No retry or error-class assertions against raw Miniflare.
   - Health check and restart, and a crashed run is invalid.
   - Minting assertions for append-only.
   - A lifecycle sweeper and 429 injection, both labelled **emulated**.
3. **Secondary target.** Add **RustFS 1.0.0** (record its image digest at first use) as the differential target for G2-S1-style runs and checksum-dependent checks, with versitygw v1.8.0 as fallback. SeaweedFS is a negative control only. Exclude MinIO community, Garage, moto (except as a unit-level mock), and LocalStack (it needs an account token, and its semantics are AWS, not R2).
4. **Real R2 is the gate** for every item in F4. The route is the hybrid harness on the sandbox account, which needs the owner's sandbox account and the H1 allowlist.

**What would change this:**
- The SB leg shows Miniflare deviating from R2 on a relied-on behaviour where RustFS or versitygw does not. Swap targets for that path.
- The experimental endpoint is removed or changes shape incompatibly.
- C1/A3 choose R2 temporary credentials, which Miniflare rejects.
- C1 chooses the S3 API over the binding for Worker-side writes. Miniflare's one-store advantage (K3) then shrinks, and RustFS could become primary.
- Miniflare's crash or 500-on-reject rate stays above what CI can tolerate after the Node-API and newer-pin trials. A suggested threshold is more than 1 invalid run in 20; G1 sets the real number.
- OD-14 is scoped to include test tooling (decision request below).

## Decision requests

**Clarification for OD-14** (cost ceilings and policy on beta features; routed through H1, evidence from H2/C4).

- **Question:** Does the beta-features policy also cover test-only tooling, such as Miniflare's experimental local R2 S3 endpoint (shipped on the miniflare 5.x alpha line), or only production dependencies?
- **Options:**
  1. **Production dependencies only.** Test tooling may use experimental features when it is lockfile-pinned, re-validated by the fidelity script on every bump, and real R2 (sandbox) remains the gate for relied-on behaviour.
  2. **Test tooling included.** RustFS 1.0.0 becomes the primary local target. Consequences:
     - The Worker under test must use the S3 API (aws4fetch) instead of its R2 binding, so the code under test differs from production if production keeps the binding.
     - R2's equal-part rule is not enforced locally.
     - RustFS's 412 on conditional Complete would mask a protocol that wrongly relies on it.
     - D1 still comes from wrangler/Miniflare, which is itself on the alpha line.
- **Recommendation:** option 1.
- **Needed by:** before A0 pins its harness (Wave 1 critical path).

No other owner decision is required. The SB leg depends on existing owner actions: the sandbox Cloudflare account and the network allowlist (`docs/research/sources.md`).

## Hand-offs

| To | What | Why |
|---|---|---|
| A0 | Pin rule (≥ 4.143.1, lockfile, fidelity re-run); F3 harness rules (screening proxy, Content-MD5 or read-back, invalid-run rule, minting assertions, 429 injection, lifecycle sweeper); "emulated" labelling; A0 reports state that the ADR-0001 queue path is not exercised | A0 builds on it |
| C1 / C1-S1 | F4 list, especially T22/T23/T25, T37/T38, T41–T43/T47 (checksum validation is undocumented, N3), W04, and binding vs S3 API for Worker writes | Real-R2 truth for ADR-0010 |
| A3 / A3-S3 | 412 is never success without a content check, and 429 is never "taken" (N1). `NoSuchUpload` on Complete is not terminal. On `InvalidPart`, re-upload from source (N4). ListParts adoption is tested on RustFS or SB, not SeaweedFS. Dropping Queues needs a superseding ADR (F5). | ADR-0009 |
| A2 | Metadata above 2 KiB fails on miniflare < 5.20260926.1-alpha. Do not rely on server-side flexible checksums until C1-S1 answers open question 2. | ADR-0007 |
| D3 / D3-S5 | Does token rotation or deletion invalidate outstanding presigned URLs on R2? Token-scope enforcement for append-only is SB-only. | BUD-REVOKE, R-18, ADR-0014 |
| D4 | The local stack cannot test append-only (Q13); the attack suite must run on SB | R-18 |
| B6 | The ETag-journal edge case (N4) | ADR-0021 |
| G1 / D5 | `npm ci` with integrity hashes; sandbox-only credentials in CI; revoke the R2 and wrangler tokens after SB runs | Supply chain, ADR-0034/0015 |
| H1 | Blocked sources (developers.cloudflare.com, api.github.com dates, git.deuxfleurs.fr, codeload, `*.r2.cloudflarestorage.com`, `api.cloudflare.com`); OD-14 clarification; kit errata | Registry and queue owner |
| G2 Wave 3 | Remaining ADR-0035 decisions; the not-evaluated alternatives; the DST fault catalogue tagged by source; the R2-semantics shim (option L) | ADR-0035 final |
