# G2. Test and verification strategy: local emulator (Wave 1 scope, G2-S1)

- **Workstream:** G2 (see `docs/research/PLAN.md`, section "G2."). **This draft covers only the Wave 1 slice:** choosing the local emulator stack that the A0 walking skeleton runs on. The full test strategy (invariant table, DST, fuzzing, fault injection, device matrix, release gates, ADR-0035) is Wave 3.
- **Status:** Draft (analyst deep read; skeptic review and spike results pending)
- **Date:** 2026-09-29 (last updated 2026-09-29)
- **Feeds:** A0 (`spikes/skeleton/`, Gate B), ADR-0035 (later), the A0 list of emulator vs R2 differences; C1-S1 and A3-S3 (real-R2 questions handed over)
- **Depends on:** A3 (which behaviours the protocol relies on), C1-S1 (real R2 behaviour), H1 sandbox account and network allowlist (`docs/research/sources.md`)
- **Traceability rows closed or advanced:** R-39 (verifiable, restorable: advanced by choosing the harness A0 runs on)

## Summary

The recommended A0 local stack is **wrangler dev (Miniflare) with its built-in local S3-compatible R2 endpoint**, pinned to an exact version (wrangler 4.143.0, which ships miniflare 5.20260926.0-alpha and workerd 1.20260926.1). This one process gives the Worker, D1 and a single R2 store. The Worker reaches the store through its R2 binding, and the client and homelab reach the same store through SigV4 and presigned URLs. None of the standalone S3 servers can offer that, and Miniflare's endpoint was written to copy R2's own error codes and header screening. It has known gaps, which the harness has to fill or test elsewhere. It does not implement ListParts, ListMultipartUploads, lifecycle rules (so there is no 7-day abort and no `restore/` expiry), flexible checksums, R2 event notifications or temporary credentials, and Queues HTTP pull is not emulated. A0 v0 avoids Queues and notifications anyway. **SeaweedFS (`weed mini`)** is proposed as a second, generic S3 target for differential runs of the G2-S1 script, and **real R2 stays the gate** for every behaviour the protocol relies on. MinIO community is excluded because the repository is archived. Garage is excluded because it cannot do conditional writes. LocalStack community is archived. Confidence: **medium**. The choice rests on reading the source and the changelog. It has not yet been run against real R2: the spike runner's emulated leg is in progress, and the SB leg is blocked on the sandbox account and network allowlist.

## Questions

| # | Question | Short answer | Confidence |
|---|---|---|---|
| 1 | Does Miniflare / `wrangler dev` support R2 **presigned URLs** locally? | **Yes, since miniflare 4.20260722.1 / wrangler 4.115.0**. It is an experimental S3-compatible endpoint at `/cdn-cgi/local/r2/s3/<bucket-id>`, enabled per bucket by `r2_buckets[].local_dev.experimental_s3_credentials`. It checks SigV4 in both header and presigned-query form (C1–C4). | High (source + changelog); behaviour not yet run |
| 2 | Can **presigned multipart** run locally on Miniflare? | Partly. CreateMultipartUpload, UploadPart, UploadPartCopy, Complete and Abort exist, and the 5 MiB minimum and equal-part-size rules are enforced. **ListParts and ListMultipartUploads return NotImplemented** (C5, C7). Presigned POST is NotImplemented, which R2 also does not support (C6). | High (source) |
| 3 | Is **conditional create** (`If-None-Match: *`) honoured locally? | On PutObject, yes. The headers are forwarded to the local R2 binding's `put(onlyIf)`, the check and the insert run in one SQLite transaction inside the bucket's Durable Object, and a failure returns 412 (C8). On CompleteMultipartUpload the headers are ignored. R2's own docs list no conditional headers for Complete (C16), so the A3 design uses per-upload keys and does not rely on it. | Medium-high (source; concurrency not yet run) |
| 4 | Are **Queues HTTP pull consumers** emulated? | **No.** The local broker has only producer routes (`/message`, `/batch`) and push delivery to consumer Workers, and wrangler rejects a non-`worker` consumer type in config (C10–C12). A0 v0 does not use Queues (the homelab polls a "pending since cursor" endpoint), so this does not block A0. A later pull path needs a small fake of the REST pull/ack API, and SB for the real limits. | Medium-high (source; absence can only be inferred) |
| 5 | Are **R2 event notifications** emulated? | No evidence that they are. There is no route, option or doc statement for them (C13). A0 does not use them. | Medium |
| 6 | **D1** local fidelity? | Cloudflare says local D1 "runs the same version of D1 as Cloudflare runs globally" (C14). This is the vendor's claim, not a measurement. Limits, latency and multi-region behaviour are not emulated. | High (claim exists) / Low (fidelity measured) |
| 7 | **MinIO** community status (PLAN exclusion rule) | **Archived.** The repository is `archived=true` (last push 2026-04-24). The README says it is "NO LONGER MAINTAINED" and that there are no more pre-built community binaries (source only). → **Excluded.** | High |
| 8 | Which standalone S3 servers are viable as a second target? | **SeaweedFS** (Apache-2.0, active; claims conditional writes, lifecycle and presigned URLs; conditional checks run under a per-object write lock). Then **versitygw** (Apache-2.0, single binary on POSIX; PutObject forwards If-Match/If-None-Match; presigned support not stated). Then **RustFS** (Apache-2.0; conditional support unverified). **Garage** is excluded: its docs say conditional writes are "structurally impossible". **LocalStack** community is archived. **moto** and **s3s-fs** are unit-level mocks at most (C17–C24). | Medium (docs and source; spike runner is installing them) |
| 9 | When is a **real R2 bucket** required? | For every behaviour the protocol relies on that Miniflare either does not implement or implements from a 2026-06-11 capture rather than from R2 itself (list in F4). In short: If-None-Match on a *presigned* PUT, anything on Complete, ListParts, the 7-day abort and lifecycle expiry, checksums, temporary credentials, notifications, 5xx/429 behaviour, consistency under load, and all cost and CPU measurements. Hybrid mode (`remote: true` on the R2 binding in `wrangler dev`) lets a local Worker use a sandbox bucket (C15). | High |
| 10 | Worker test runner? | **`@cloudflare/vitest-plugin`** (1.3.1, 2026-09-28) is what Cloudflare now recommends. `@cloudflare/vitest-pool-workers` (0.22.0) has a "migrate to Vitest plugin" guide. The scouts named only the pool, so this is a correction (C25). | High |
| 11 | (new) Does the local endpoint work with standard SDK defaults? | Not without some configuration. workerd never sends `100 Continue`, so SDKs that send `Expect: 100-continue` hang. `aws-chunked` bodies (which the SDKs use for default trailing checksums) are not decoded. `x-amz-security-token` is rejected (C9). Presigned uploads from a plain HTTP client are not affected. | High (source comments) |

## Method

- **Sweep:** docs scout (cloudflare-docs source on raw GitHub, workers-sdk READMEs and changelogs, npm registry, vendor READMEs) and source scout (npm tarballs for miniflare and wrangler, Garage, SeaweedFS, versitygw and moto sources on raw GitHub, crates.io). No issues/forums or pricing scout: out of scope for this slice.
- **Deep read (this note):** I fetched and read in full the TypeScript sources embedded in the source maps of `miniflare-5.20260926.0-alpha.tgz` (`src/workers/r2/s3/{index,auth,dispatch,account,operations}.worker.ts` and the relevant parts of `r2/bucket.worker.ts`), the #14280 entries in the miniflare and wrangler changelogs, the later miniflare 5.x entries that renamed the config key, the bindings-per-mode partial, Queues local development, the R2 presigned URL, temporary credentials and S3 compatibility pages (relevant rows), Garage known issues, the s3s README, and wrangler 4.143.0's config validator.
- **Routes used:** raw.githubusercontent.com (cloudflare-docs @ production, workers-sdk @ main, vendor repos), registry.npmjs.org tarballs, proxy.golang.org, pypi.org, crates.io, and GitHub MCP `search_repositories` (archive flags, used by the scouts).
- **Blocked sources:** developers.cloudflare.com (the raw cloudflare-docs source was used instead: same primary content, but commit dates could not be retrieved); api.github.com via curl (no per-page last-modified dates); git.deuxfleurs.fr (Garage upstream and issue tracker, so the GitHub mirror was used); codeload.github.com tarballs. All are already listed in `docs/research/sources.md` or should be reported to H1.
- **Stop rule:** two scouts plus this deep read. The analyst read added one new primary source (the `@cloudflare/vitest-plugin` registry entry and doc line) and resolved every scout conflict from primary code.
- **Not done here:** nothing was *executed*. The spike runner is installing and running the candidates (see Spikes).

### Scout conflicts resolved

| Topic | Scout A | Scout B | Resolution (primary) |
|---|---|---|---|
| Presigned expiry cap | Constant 604800 present | "rejects one week or more" | `auth.worker.ts`: rejects `expires > 604800`. **604,800 s is accepted**, which matches R2's "1 second to 7 days (604,800 seconds)". |
| Operation list | Changelog list incl. ListBuckets | Operations table incl. GetBucketLocation; ListParts NotImplemented | Both are right. The changelog lists the implemented set; `index.worker.ts` "Gaps" lists ListParts, ListMultipartUploads, lifecycle, CORS, encryption and versioning config as NotImplemented. |
| s3s-fs auth | Accepts anonymous without `set_auth` | Signed requests fail with NotImplemented | Both are right (s3s README, "Authentication is required for production deployments"). |
| Atomicity of local If-None-Match | Not stated | "not verified" | `bucket.worker.ts`: the `put` statement is a `db.txn(...)` that reads the previous row, runs `validate.condition`, then inserts, inside a single Durable Object. Atomic by construction; still to be confirmed by a race test. |
| Miniflare config key | `s3Credentials` (Miniflare API) | `dev.experimentalS3Credentials` | Renamed twice in the 5.x alpha line (`s3Credentials` → `localDev.experimentalS3Credentials` → `dev.experimentalS3Credentials`). The wrangler key is still `local_dev.experimental_s3_credentials` in 4.143.0. **Pin exact versions.** |
| Worker test package | vitest-pool-workers 0.22.0 | same | Docs now recommend `@cloudflare/vitest-plugin` (1.3.1). |

## Sources

| # | Source (title and URL or mirror path) | Publisher | Published or version date | Accessed | Primary? |
|---|---|---|---|---|---|
| S1 | miniflare 5.20260926.0-alpha tarball, source maps: `src/workers/r2/s3/*.worker.ts`, `src/workers/r2/bucket.worker.ts`, `r2/constants.ts`, `queues/broker.worker.js`, `dist/src/index.js` — https://registry.npmjs.org/miniflare/-/miniflare-5.20260926.0-alpha.tgz | Cloudflare | 2026-09-27 | 2026-09-29 (s3 sources read in full) | Yes |
| S2 | miniflare CHANGELOG, `cloudflare/workers-sdk @ main : packages/miniflare/CHANGELOG.md` (4.20260722.1 #14280; 5.20260820.0-alpha #15130; #15318) | Cloudflare | main head | 2026-09-29 | Yes |
| S3 | wrangler CHANGELOG, `… : packages/wrangler/CHANGELOG.md` (4.115.0 #14280) | Cloudflare | main head | 2026-09-29 | Yes |
| S4 | wrangler 4.143.0 tarball, `wrangler-dist/cli.js` (config validator), and https://registry.npmjs.org/wrangler (dist-tags) | Cloudflare | 2026-09-28 | 2026-09-29 | Yes |
| S5 | https://registry.npmjs.org/miniflare (dist-tags: latest = 5.20260926.0-alpha; last 4.x = 4.20260730.0) | npm | 2026-09-27 | 2026-09-29 | Yes |
| S6 | Supported bindings per development mode, `cloudflare/cloudflare-docs @ production : src/content/partials/workers/bindings_per_env.mdx` | Cloudflare | production head | 2026-09-29 (full) | Yes |
| S7 | Workers local development / remote bindings, `… : docs/workers/local-development/index.mdx` | Cloudflare | production head | 2026-09-29 | Yes |
| S8 | Queues local development, `… : docs/queues/configuration/local-development.mdx` | Cloudflare | production head | 2026-09-29 (full) | Yes |
| S9 | Queues pull consumers, `… : docs/queues/configuration/pull-consumers.mdx` | Cloudflare | production head | 2026-09-29 (scout) | Yes |
| S10 | R2 presigned URLs, `… : docs/r2/api/s3/presigned-urls.mdx` | Cloudflare | production head | 2026-09-29 (full) | Yes |
| S11 | R2 S3 API compatibility, `… : docs/r2/api/s3/api.mdx` (PutObject, UploadPart, Complete, ListParts, ListMultipartUploads rows; UploadPart note; checksum table) | Cloudflare | production head | 2026-09-29 | Yes |
| S12 | R2 temporary credentials, `… : docs/r2/api/s3/temporary-credentials.mdx` | Cloudflare | production head | 2026-09-29 | Yes |
| S13 | R2 object lifecycles, `… : docs/r2/buckets/object-lifecycles.mdx` | Cloudflare | production head | 2026-09-29 | Yes |
| S14 | R2 event notifications, `… : docs/r2/buckets/event-notifications.mdx` | Cloudflare | production head | 2026-09-29 (scout) | Yes |
| S15 | D1 local development, `… : docs/d1/best-practices/local-development.mdx` | Cloudflare | production head | 2026-09-29 | Yes |
| S16 | Workers Vitest integration, `… : docs/workers/testing/vitest-integration/index.mdx`; https://registry.npmjs.org/@cloudflare/vitest-plugin (1.3.1, 2026-09-28); https://registry.npmjs.org/@cloudflare/vitest-pool-workers (0.22.0, 2026-08-18) | Cloudflare / npm | as stated | 2026-09-29 | Yes |
| S17 | Miniflare README, `cloudflare/workers-sdk @ main : packages/miniflare/README.md` | Cloudflare | main head | 2026-09-29 (scout) | Yes |
| S18 | MinIO README `minio/minio @ master : README.md`; repo metadata (archived=true, pushed 2026-04-24, AGPL-3.0) via GitHub MCP | MinIO | 2026-04-24 | 2026-09-29 | Yes |
| S19 | LocalStack README `localstack/localstack @ main : README.md`; repo metadata (archived=true, pushed 2026-03-23) | LocalStack | 2026-03-23 | 2026-09-29 | Yes |
| S20 | Garage known issues `deuxfleurs-org/garage @ main-v2 : doc/book/reference-manual/known-issues.md`; S3 compatibility page (main-v1/main-v2); `src/api/s3/{put,multipart,get}.rs`; `src/garage/Cargo.toml` (2.4.1). GitHub mirror of git.deuxfleurs.fr | Deuxfleurs | mirror pushed 2026-09-28 | 2026-09-29 | Yes (mirror) |
| S21 | SeaweedFS README and `weed/s3api/s3api_object_handlers_put.go` (`seaweedfs/seaweedfs @ master`); repo pushed 2026-09-29, Apache-2.0 | SeaweedFS | master head | 2026-09-29 | Yes |
| S22 | versitygw README and `s3api/controllers/object-put.go` (`versity/versitygw @ main`); https://proxy.golang.org/github.com/versity/versitygw/@latest (v1.8.0, 2026-09-04) | Versity | 2026-09-04 | 2026-09-29 | Yes |
| S23 | RustFS README (`rustfs/rustfs @ main`), repo pushed 2026-09-29, Apache-2.0 | RustFS | main head | 2026-09-29 | Yes |
| S24 | s3s README (`Nugine/s3s @ main`); s3s-fs 0.17.0 crate; crates.io API (0.17.0, 2026-09-24) | Nugine | 2026-09-24 | 2026-09-29 | Yes |
| S25 | moto CHANGELOG (`getmoto/moto @ master`), `moto/s3/responses.py`; https://pypi.org/pypi/moto/json (5.2.3) | getmoto | master head | 2026-09-29 | Yes |
| S26 | alchemy-run/alchemy issue #1715 "Support a local R2 S3 HTTP endpoint for presigned uploads" (search result only) | third party | unknown | 2026-09-29 | No (not relied on) |

## Claims

Skeptic columns are empty until the Wave 1 skeptic pass.

| # | Claim | Sources | Key? | Skeptic 1 (sources) | Skeptic 2 (logic) | Skeptic 3 (adversary/cost/user) | Verdict |
|---|---|---|---|---|---|---|---|
| C1 | wrangler 4.143.0 (2026-09-28) is npm `latest` and pins miniflare 5.20260926.0-alpha and workerd 1.20260926.1. miniflare's own `latest` dist-tag is that 5.x alpha, and the last 4.x is 4.20260730.0. miniflare requires Node ≥ 22. | S4, S5, S1 (`package.json`) | Yes (time-sensitive pin) | | | | Pending |
| C2 | miniflare 4.20260722.1 / wrangler 4.115.0 (PR #14280) added a local S3-compatible API for R2 at `/cdn-cgi/local/r2/s3/<bucket-id>`, authenticated with SigV4 (header and presigned query). In wrangler it is enabled per bucket by `local_dev.experimental_s3_credentials {accessKeyId, secretAccessKey}`, and `<bucket-id>` is `bucket_name`, or the binding name if that is unset. | S2, S3, S4 | Yes | | | | Pending |
| C3 | The feature is experimental and undocumented on the docs site. Its Miniflare API key was renamed twice within the 5.x alpha line (`s3Credentials` → `localDev.experimentalS3Credentials` → `dev.experimentalS3Credentials`). | S2, S4 (scout: not in `wrangler/configuration.mdx`) | Yes (stability risk) | | | | Pending |
| C4 | Presigned checks: `X-Amz-Expires` > 604,800 → 400; expired or < 1 → 403 `ExpiredRequest`; signature mismatch → 403 `SignatureDoesNotMatch` (timing-safe compare); payload is `UNSIGNED-PAYLOAD`. Header auth adds a ±15 min skew check (`RequestTimeTooSkewed`) and verifies a literal `x-amz-content-sha256`. The source says error codes and check order "mimic R2's S3 endpoint", captured from a real bucket on 2026-06-11. | S1 (`auth.worker.ts`, `index.worker.ts`) | Yes | | | | Pending |
| C5 | The local endpoint implements Get/Head/Put/Copy/Delete/DeleteObjects, ListObjects(V2), HeadBucket, ListBuckets, GetBucketLocation, Create/UploadPart/UploadPartCopy/Complete/Abort multipart. **ListParts, ListMultipartUploads, the `partNumber` GET, lifecycle, CORS, encryption and versioning config, CreateBucket and DeleteBucket answer NotImplemented.** | S1 (`index.worker.ts` "Gaps"), S2 | Yes | | | | Pending |
| C6 | A bucket-level POST with no auth returns NotImplemented "Presigned post requests are not yet implemented not implemented", which the source says is R2's own message, verbatim. | S1 (`dispatch.worker.ts`), S10 | No | | | | Pending |
| C7 | Complete enforces R2's multipart rules locally: every part except the last ≥ 5 MiB (`EntityTooSmall`); every part except the last equal in size, and the last not larger (`BadUpload`); part numbers 1–10,000; duplicate part numbers give `InvalidPart`. Re-uploading a part number replaces the row (`INSERT OR REPLACE`). | S1 (`bucket.worker.ts`, `constants.ts`, `operations.worker.ts`), S11 | Yes | | | | Pending |
| C8 | Local PutObject forwards If-Match / If-None-Match / If-(Un)Modified-Since to `bucket.put(onlyIf)` and returns 412 `PreconditionFailed` on null. The precondition check and the insert run in one `db.txn` inside the bucket Durable Object. Content-MD5 is verified (`BadDigest`). CompleteMultipartUpload does not read conditional headers (they are silently ignored). | S1 | Yes | | | | Pending (race test in G2-S1) |
| C9 | Local endpoint quirks from the source header comment: flexible `x-amz-checksum-*` headers are **silently ignored** (R2 validates them); `aws-chunked` bodies are **not decoded**; workerd never sends `100 Continue`, so SDKs using `Expect: 100-continue` hang; `x-amz-security-token` (R2 temporary credentials) is rejected with 400; SSE-C writes and non-default storage classes return NotImplemented; CORS is always permissive. | S1 (`index.worker.ts`, `operations.worker.ts`), S11, S12 | Yes | | | | Pending |
| C10 | Miniflare's local Queues broker exposes only producer routes (`/message`, `/batch`) and push delivery to consumer Workers. The local routes under `/cdn-cgi/local/` are `scheduled`, `r2/s3`, `r2/public`, `platform-proxy`, `explorer` and `email`: there is no pull or ack route. | S1 | Yes | | | | Pending (absence inferred) |
| C11 | wrangler maps `queues.consumers` entries to Miniflare push-consumer options without modelling `http_pull`, and the changelog says it now errors on a non-`worker` consumer type. HTTP pull is a REST call to `api.cloudflare.com/.../queues/{id}/messages/pull` with a Bearer token. | S4, S3, S9 | Yes | | | | Pending |
| C12 | Queues local limits in the docs: consumer concurrency is not supported locally; `wrangler dev --remote` is not supported; running producer and consumer Workers from one command is experimental. | S8 | No | | | | Pending |
| C13 | No R2 event-notification emulation was found in Miniflare (no route, option or doc statement). R2 `object-create` fires on PutObject, CopyObject and CompleteMultipartUpload. | S1, S14, S17 | No (A0 does not use it) | | | | Pending (absence inferred) |
| C14 | "D1 has fully-featured support for local development, running the same version of D1 as Cloudflare runs globally." | S15 | No | | | | Pending (vendor claim) |
| C15 | R2, D1 and Queues support both local simulation and remote-binding connections. Durable Objects are local only. With `remote: true` the Worker still runs locally but that binding's operations hit the real resource (billed, real data). `wrangler dev --local` turns every remote binding off. | S6, S7 | Yes (hybrid SB leg) | | | | Pending |
| C16 | R2's S3 table lists If-Match / If-None-Match / If-(Un)Modified-Since for PutObject and **no** conditional headers for CompleteMultipartUpload. ListParts and ListMultipartUploads **are** implemented on R2. UploadPart to the same number replaces the previous part. Presigned URLs: GET, PUT, HEAD, DELETE only, 1 s–604,800 s. Temporary credentials carry `X-Amz-Security-Token`. Buckets have a default rule that aborts multipart uploads 7 days after initiation. | S10, S11, S12, S13 | Yes | | | | Pending |
| C17 | MinIO community is archived (archived=true, last push 2026-04-24, AGPL-3.0). The README says "THIS REPOSITORY IS NO LONGER MAINTAINED" and that there will be no more pre-compiled community binaries; it points to AIStor Free / Enterprise. | S18 | Yes (PLAN exclusion rule) | | | | Pending |
| C18 | The LocalStack community repo is archived and read-only. Development has moved to a unified image with plans (a free Hobby plan for non-commercial use). Whether an auth token is now required to run it was not checked. | S19 | No | | | | Pending |
| C19 | Garage states that conditional writes (`if-none-match`), locking and WORM are "structurally impossible" without a consensus algorithm. Its PutObject and multipart code have no precondition handling. It also documents O(n²) metadata cost for very large objects (#1366, long multipart uploads). | S20 | Yes (exclusion) | | | | Pending |
| C20 | SeaweedFS (Apache-2.0, active) claims conditional reads and writes, lifecycle, versioning, presigned URLs and multipart, and says the single-node `weed mini` is "fine for single-node production, such as an S3 gateway that issues presigned URLs". PutObject evaluates If-Match / If-None-Match and re-runs the precondition under a per-object write lock. | S21 | Yes | | | | Pending (spike runner) |
| C21 | versitygw (Apache-2.0, v1.8.0 on 2026-09-04) serves S3 from a POSIX directory as a single binary. PutObject forwards IfMatch / IfNoneMatch to the backend. Its README does not state presigned-URL or conditional-Complete support. | S22 | No | | | | Pending (spike runner) |
| C22 | RustFS is Apache-2.0 and active, and its README marks S3 core, versioning, lifecycle and event notifications as "Available". Conditional-write support was not checked. | S23 | No | | | | Pending |
| C23 | moto added put_object conditional writes (5.0.15) and IfNoneMatch on complete_multipart_upload (5.0.23, fixed 5.1.11). That follows AWS, not R2, whose docs list no conditional Complete. The scout saw no SigV4 recomputation for presigned requests (low confidence). | S25 | No | | | | Pending |
| C24 | s3s-fs is a filesystem sample "designed for integration testing" inside an "experimental" framework. Without `set_auth` it accepts anonymous requests and signed requests fail with NotImplemented. | S24 | No | | | | Pending |
| C25 | Cloudflare now recommends `@cloudflare/vitest-plugin` (1.3.1, 2026-09-28) for Worker tests. It runs tests fully locally on Miniflare with isolated per-test-file storage, and there is a migration guide for `@cloudflare/vitest-pool-workers` users. | S16 | No | | | | Pending |

## Findings

### F1. What the A0 harness actually needs (from A0 and A3)

A0 v0 (PLAN A0 table) uses: presigned single PUT and presigned UploadPart from a Rust CLI; Create and Complete through the Worker; a per-upload staging key with conditional create; D1 only; **no Queues** (the homelab polls a signed "pending since cursor" endpoint); a homelab puller that lists, gets and deletes staged objects; and a restore leg through an expiring `restore/` prefix. A3 and CE add: ListParts with ETag-matched adoption on resume, abort-only lifecycle on `staging/` and `meta/`, expiry on `restore/`, and `onlyIf` create-only for small records written by the Worker.

So the local target must at least: (a) accept Worker-minted presigned PUT and UploadPart URLs, (b) share one store with the Worker's own R2 access, (c) enforce multipart part-size rules, (d) honour If-None-Match on PutObject, and (e) serve List, Get and Delete to the homelab with header SigV4. Lifecycle and ListParts are needed for A0-S2 and A0-S3 but can be simulated or deferred to SB.

### F2. Miniflare's local R2 S3 endpoint fits (a)–(e) better than any standalone server (C2–C8)

- **One store.** The endpoint is a Worker in front of the same local R2 binding the application Worker uses (`R2S3Bindings.BUCKET_PREFIX`). An object uploaded by presigned URL is visible to `env.BUCKET.get()`, and an upload created by the binding can be completed over S3 (the local Complete itself calls `bucket.resumeMultipartUpload(...).complete()`). With a standalone S3 server the Worker would have to talk S3 (aws4fetch) instead of its binding. That changes the Worker code under test and loses the binding's `onlyIf` path.
- **R2-shaped errors.** Error codes, messages and check order are taken from a real R2 bucket (capture dated 2026-06-11), including R2-specific choices such as 401 `Unauthorized` for unknown keys and `InvalidPart` for duplicate part numbers.
- **Multipart rules** (C7) match R2's documented limits (5 MiB minimum, equal parts, last part not larger, 10,000 parts).
- **Conditional create** on PutObject is enforced atomically within the bucket's Durable Object (C8). The spike still needs to run a concurrent-PUT race to confirm.
- **Confidence:** high that these code paths exist, medium that they behave exactly like R2, because the comparison with R2 is Cloudflare's own capture and not ours.

### F3. Gaps the harness must fill or push to SB (C5, C9–C13)

| Gap | A0 impact | Proposed handling |
|---|---|---|
| ListParts / ListMultipartUploads NotImplemented | Resume-with-adoption path (CE §8, A3) cannot be exercised locally | Client keeps its ETag journal (the CE design already treats it as authoritative). Test ListParts adoption on SB (C1-S1 / A3-S3) or against SeaweedFS as the second target. |
| No lifecycle (no 7-day abort, no `restore/` expiry) | A0-S3 "objects expire by lifecycle rule" cannot pass locally | A test-clock-driven "lifecycle sweeper" in the harness that aborts or deletes by rule, labelled *emulated*. The real rule is SB-only. |
| Flexible checksums ignored; `aws-chunked` not decoded | An SDK with default trailing checksums would work on R2 but fail or behave differently locally, or the reverse | Configure the homelab and Worker S3 clients to send checksums only when required, and send Content-MD5 where integrity is wanted locally. Checksum behaviour is SB-only. |
| `Expect: 100-continue` hangs | SDK-based uploads (homelab restore leg) may hang | Disable Expect/continue in the SDK. Presigned uploads from `reqwest` are unaffected. **Spike to confirm for the Rust SDK.** |
| `x-amz-security-token` rejected | R2 temporary credentials (an alternative to presigned UploadPart, S12) cannot be tested locally | SB-only, if C1 or D3 picks temporary credentials. |
| No Queues HTTP pull; no R2 event notifications | None for A0 (v0 uses polling) | Wave 2: if ADR-0009/0010 keep the pull consumer as a latency hint, add a small fake of the REST pull/ack API (visibility timeout, ack/retry, retention) in the harness, and measure the real limits (the A3 note records a 1,200/5 min API limit) on SB. |
| Experimental and alpha status; config-key churn | Upgrades can break the harness | Pin exact wrangler, miniflare and workerd versions in the lockfile, keep the config in wrangler form (`local_dev.experimental_s3_credentials`), and re-run the G2-S1 fidelity script on every bump. |
| The endpoint lives under a path prefix (`/cdn-cgi/local/r2/s3/<bucket>`) | The homelab S3 client must accept an endpoint URL with a path and use path-style addressing | Spike check. The Worker's presigner (aws4fetch or equivalent) takes a base URL, so this is trivial there. |

### F4. When a real R2 bucket is required (Q9)

Real R2 (sandbox account, [SB]) is required for: If-None-Match on a **presigned** PUT (does R2 enforce an unsigned conditional header? A3 open question 2); any behaviour of CompleteMultipartUpload with conditional headers; UploadPart after Complete; ListParts adoption; whether an abort rule can exceed 7 days, and the default abort itself; lifecycle expiry on `restore/`; checksum handling; temporary credentials; event notifications and pull consumers; interop between binding-created uploads and S3 UploadPart on real R2; 5xx and 429 behaviour, latency and consistency under load; and every A0 measurement that feeds C4 and ADR-0009/0010 (Class A/B ops, Worker CPU, D1 rows). The cheapest route is **hybrid**: the same `wrangler dev` harness with `remote: true` on the R2 (and optionally D1) binding against a sandbox bucket (C15), plus presigned URLs pointed at `<account>.r2.cloudflarestorage.com`. That needs the H1 allowlist (`*.r2.cloudflarestorage.com`, `api.cloudflare.com`), which is blocked today (`docs/research/sources.md`).

### Alternatives compared

| Option | Fit with settled requirements | Pros | Cons | Evidence |
|---|---|---|---|---|
| **A. Miniflare / `wrangler dev` + local R2 S3 endpoint** (recommended primary) | Good: Cloudflare-only stack (ADR-0001); local only | One store for binding and S3; R2-captured errors; SigV4 and presign; multipart rules; atomic If-None-Match PUT; D1 in the same process; MIT licence; vitest-plugin for unit tests | Experimental, alpha line, key churn; no ListParts, lifecycle, checksums, notifications, pull or temp credentials; SDK quirks (100-continue, aws-chunked) | C1–C15 |
| **B. SeaweedFS `weed mini`** (recommended secondary, for differential runs) | Neutral (test only); Apache-2.0 | Claims conditional writes (under lock), lifecycle, presign, multipart incl. ListParts; single binary; active | AWS-shaped, not R2-shaped; Worker must talk S3 instead of its binding; not the same store as Miniflare's binding | C20 |
| C. versitygw (posix) | Neutral; Apache-2.0 | Single binary over a directory; forwards If-None-Match; easy to inspect on disk | Presign and lifecycle support unstated; AWS-shaped | C21 |
| D. RustFS | Neutral; Apache-2.0 | MinIO-like feature set, "Available" lifecycle and notifications | Conditional writes unverified; heavier; young 1.0 | C22 |
| E. Garage | AGPL (licence matters only if code is reused, not for a test service) | Presign, multipart, lifecycle subset | **No conditional writes, structurally**; O(n²) for large objects; no notifications | C19 |
| F. MinIO community | — | Historically the S3 test reference | **Archived; source only** → excluded by the PLAN rule | C17 |
| G. LocalStack | Paid-plan image | Broad AWS emulation | Community repo archived; AWS semantics, not R2 | C18 |
| H. moto (server mode) | — | Python, easy for unit mocks; conditional Complete | AWS semantics (conditional Complete that R2 does not document); weak presign verification (low confidence) | C23 |
| I. s3s-fs | — | In-process Rust mock possible | Experimental sample; auth off by default; not R2-shaped | C24 |
| J. Real R2 only (sandbox) | Good | Ground truth | Blocked from the container today; costs money; slow inner loop; not usable offline or in CI without secrets | C15, sources.md |

### Similar work and lessons

| Project or paper | What they do | Borrow or avoid | Source |
|---|---|---|---|
| alchemy-run/alchemy #1715 | Users asked for a local R2 S3 endpoint for presigned uploads before Miniflare shipped one | Confirms the need; not relied on | S26 (secondary) |
| Miniflare's own design note | Copies R2 error behaviour from a capture of a real bucket and documents every gap in the source header | **Borrow**: keep our own fidelity table in the same form (gap, impact, handling) and re-run it on each version bump | S1 |

### Tools and libraries

| Name | Purpose | Licence | Maturity (release date, activity) | Source |
|---|---|---|---|---|
| wrangler | Local dev, config | MIT OR Apache-2.0 | 4.143.0, 2026-09-28 | S4 |
| miniflare | Local runtime (Workers, D1, R2 + S3 endpoint, Queues push) | MIT | 5.20260926.0-alpha, 2026-09-27 (shipped by stable wrangler) | S1, S5 |
| @cloudflare/vitest-plugin | Worker unit and integration tests on Miniflare | (per package) | 1.3.1, 2026-09-28 | S16 |
| SeaweedFS | Second S3 target | Apache-2.0 | master active 2026-09-29 | S21 |
| versitygw | Alternative second S3 target | Apache-2.0 | v1.8.0, 2026-09-04 | S22 |
| Garage | Excluded (no conditional writes) | AGPL-3.0 | 2.4.1 (main-v2) | S20 |
| MinIO | Excluded (archived) | AGPL-3.0 | last push 2026-04-24 | S18 |

## Spikes

*Placeholder: the G2-S1 spike runner is working in parallel. Results will be merged here.*

| Spike | Hypothesis | Pass → / fail → (decision) | Exec tag | Budget IDs | Data class | Status | Result |
|---|---|---|---|---|---|---|---|
| G2-S1 (emulated leg) | The same presigned-multipart and conditional-create script behaves identically on Miniflare's local R2 S3 endpoint, SeaweedFS and versitygw (and Garage for contrast), for every behaviour in F1 | Pass → Miniflare primary + SeaweedFS secondary as in the Recommendation; fail → document each difference and either shim it or move that behaviour to SB-only | CT (**emulated, not real R2/Cloudflare**) | — (fidelity, no budget) | `SYN → results` | Running (spike runner) | Pending |
| G2-S1 (real R2 leg) | Real R2 matches the chosen local target on every protocol-relied behaviour | Pass → local target confirmed for A0; fail → each difference is recorded in the A0 difference list and in ADR-0035 | SB (kit; needs the sandbox account and allowlist) | BUD-REVOKE (presign expiry only) | `SYN → results` | Not started (kit to be written) | — |

Checks the spike should cover beyond the PLAN line, from this read: (1) concurrent `If-None-Match: *` PUT race (N clients, same key → exactly one 200); (2) If-None-Match sent on a *presigned* PUT, both signed and unsigned, on every target; (3) If-None-Match on Complete (expected: ignored locally; unknown on R2); (4) re-uploading the same part number, then Complete with the old ETag; (5) expiry at exactly 604,800 s and at 604,801 s; (6) Rust SDK with default checksum and Expect settings against the local endpoint; (7) endpoint-with-path-prefix support in the homelab's S3 client; (8) a binding-created upload with presigned S3 UploadPart parts, then binding Complete.

## Conflicts with settled text

None. The choice of test tooling does not touch CLAUDE.md or ADR-0001/0002. (ADR-0001 names Queues for object-staged events. A0 v0 dropping Queues is A3/A0's call, already tracked under OD-04 and ADR-0009/0010, not this note's.)

## Open questions

| # | Question | Who answers | By when |
|---|---|---|---|
| 1 | Does every protocol-relied behaviour in F1 match between Miniflare and real R2? | G2-S1 real-R2 leg (SB) together with C1-S1 | Gate B |
| 2 | Is local If-None-Match on PutObject race-free in practice? | G2-S1 emulated leg | Wave 1 |
| 3 | Does the Rust S3 client (aws-sdk-s3 or rusty-s3) work against the path-prefixed local endpoint without the 100-continue or aws-chunked problems? | G2-S1 / A0 build | Wave 1 |
| 4 | Do SeaweedFS and versitygw enforce presigned expiry and signatures, and support ListParts and If-None-Match on PutObject? | G2-S1 emulated leg | Wave 1 |
| 5 | If a pull consumer is kept (ADR-0009/0010), what fake of the pull/ack REST API does the harness need? | G2 Wave 2/3 with A3 | Wave 2 |
| 6 | Will the local S3 endpoint graduate from "experimental" in wrangler or change shape again? | Watch the workers-sdk changelog on each pin bump | Ongoing |

## Recommendation

Use **`wrangler dev` (Miniflare) with the local R2 S3 endpoint as the A0 local target**, pinned to wrangler 4.143.0 / miniflare 5.20260926.0-alpha / workerd 1.20260926.1 (or whatever the spike runner validates). Configure the bucket with `local_dev.experimental_s3_credentials`, and run Worker unit tests with `@cloudflare/vitest-plugin`. Fill the known gaps in the harness: a clock-driven lifecycle sweeper for the 7-day abort and `restore/` expiry, an ETag journal instead of ListParts, and SDK settings for Expect/continue and checksums. Label every such result **emulated**. Add **SeaweedFS `weed mini`** as a second target, used only to run the G2-S1 fidelity script differentially, not as A0's store. Do not use MinIO community (archived), Garage (no conditional writes), LocalStack community (archived), or moto or s3s-fs beyond unit-level mocks. **Real R2 stays the gate.** Every item in F4 is SB-only, and the cheapest route there is the same harness with `remote: true` bindings against the sandbox bucket.

What would change this: the G2-S1 emulated leg showing that Miniflare deviates from R2 on a relied-on behaviour where SeaweedFS does not (then swap primary and secondary for that path); a breaking change or removal of the experimental endpoint; or C1/A3 choosing R2 temporary credentials over presigned URLs (Miniflare rejects session tokens, so a standalone server or SB would carry that path).

## Decision requests

No new owner decision is required for this slice. One clarification for H1 to attach to **OD-14** (policy on beta features): the policy should cover production dependencies only. Test-only tooling, such as Miniflare's experimental S3 endpoint, may be used if it is pinned and the real-R2 leg stays the gate. Recommended answer: yes, scope OD-14 to production. The SB leg still depends on the existing owner actions (the sandbox Cloudflare account and the network allowlist in `docs/research/sources.md`).

## Hand-offs

| To | What | Why |
|---|---|---|
| A0 | Stack pin, wrangler config snippet, gap table (F3), "emulated" labelling | A0 builds on it |
| C1 / C1-S1 | The F4 list, especially the presigned If-None-Match, Complete-conditional and binding/S3 interop checks | Real-R2 truth for ADR-0010 |
| A3 / A3-S3 | Local ListParts and lifecycle gaps; the pull-API fake needed if the pull consumer stays | The A3-S2 harness runs emulated |
| H1 | Blocked sources (developers.cloudflare.com, api.github.com dates, git.deuxfleurs.fr); OD-14 scope note | Registry and queue owner |
| G2 Wave 3 | Fidelity table format; re-run on version bumps; DST and fault-injection hooks around the harness | ADR-0035 |
