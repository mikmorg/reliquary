# ADR-0035: Test and verification strategy. Wave 1 part: Miniflare's local R2 S3 endpoint as the local target, under fail-closed harness rules, with real R2 as the gate

- **Status:** Proposed (partial draft; the Wave 1 decisions only. The rest is to be decided in Wave 3, see "Not yet decided")
- **Date:** 2026-10-06
- **Owner workstream:** G2
- **Decider:** the owner
- **Gate:** build. The Wave 1 part is needed earlier, by A0, before Gate B.
- **Supersedes / Amends:** None. This ADR does not change ADR-0001 or ADR-0002.
- **Evidence:**
  - Note: `docs/research/g2-test-and-verification.md` (Wave 1 final).
  - Spike: `spikes/G2-S1/` (emulated leg, 2026-09-29), with results in `spikes/G2-S1/results/comparison.md` and `sdk-comparison.md`.
  - Kit: `docs/research/kits/G2-S1/README.md` (real-R2 leg; apply the kit errata listed in the note).
- **Traceability:** R-39 (verifiable and restorable), R-18 (append-only: how it is and is not verified). See `docs/research/traceability.md`.
- **Owner decisions:** OD-14 (clarification: does the beta-features policy cover test tooling?). See `docs/research/decision-queue.md`.
- **One-way door:** No. Test tooling can be swapped. The cost is rewriting harness glue and re-running the fidelity baseline.

## Context and problem statement

A0 (the walking skeleton) runs device → Worker/R2 → homelab → restore on a local stack before it runs on a sandbox R2 bucket. It needs a local stand-in for Workers, D1 and R2, including presigned PUT and UploadPart, conditional create, and multipart rules. "Data integrity over everything" (R-39) means that stand-in must not let a test pass on behaviour R2 would not show. "Devices can only append" (R-18) means its limits around authorisation must be explicit.

The Wave 1 research read Miniflare's source. It then ran one stdlib SigV4 script, about 750 requests, against Miniflare's local R2 S3 endpoint, RustFS, versitygw, SeaweedFS, Garage and moto, plus an AWS JS SDK defaults check. All of that was emulated, not real R2. Three skeptics reviewed the 14 key claims, and all 14 are verified.

Main findings:
- **Miniflare** is the only target where the Worker's R2 binding and presigned S3 traffic share one store. It is also the only one that enforces R2's equal-part rule.
- **Miniflare's weaknesses.** It silently stores wrong or tampered bytes when flexible checksums or `aws-chunked` are used, and it is intermittently unstable.
- **Real R2** has not been measured, because the sandbox account and the network allowlist are outstanding.

The full test strategy (invariant table, DST, fuzzing, fault catalogue, device matrix, release gates) is Wave 3 and is not decided here.

## Decision drivers

- **R-39, data integrity over everything** (CLAUDE.md): a local pass must never be evidence for an integrity property the local store does not enforce.
- **R-18, devices can only append** (CLAUDE.md, ADR-0001): the harness must show where this is and is not verified.
- **ADR-0001 (Accepted):** Cloudflare-only control plane (Workers, D1/DO, R2, Queues); the homelab pulls queue events and reconciles.
- **BUD-REVOKE** (expiry mechanism only): presigned expiry is enforced locally (T08, T09). The 15-minute and 60-second targets themselves are measured by D3-S5, not here.
- **Fast, offline inner loop for A0:** no secrets in CI for the default test run.
- **OD-14** (beta-features policy): the recommended local endpoint is experimental and ships on the miniflare 5.x alpha line.

## Considered options

1. **A.** Miniflare / `wrangler dev` with its experimental local R2 S3 endpoint.
2. **B.** A standalone S3 server as the primary target: RustFS 1.0.0, versitygw v1.8.0 or SeaweedFS `weed mini`. The Worker would use the S3 API instead of its binding.
3. **C.** Real R2 (sandbox) only.
4. **D.** A with a standalone server as a differential secondary, and real R2 as the gate.
5. Also considered and rejected: Garage, MinIO community, LocalStack, moto (server mode), s3s-fs.

## Decision

**Proposed: option D.** The primary local target is Miniflare's local R2 S3 endpoint, run under the harness rules below. RustFS 1.0.0 is the differential secondary. Real R2 is the gate for every behaviour the protocol relies on.

Why Miniflare: it is the only target that runs the Worker's real R2-binding code against the same store the client and homelab reach by presigned URL and SigV4 (K3), and it enforces R2-specific rules the AWS-shaped servers do not. Why the rules: its silent integrity gaps would otherwise make local passes meaningless for R-39.

The decisions in scope for Wave 1:

1. **Primary local target.**
   - Use `wrangler dev` (Miniflare) with `r2_buckets[].local_dev.experimental_s3_credentials` (K2), so the local S3 endpoint at `/cdn-cgi/local/r2/s3/<bucket>` is enabled.
   - Pin through the lockfile and install with `npm ci`, at no lower than **wrangler 4.143.1 / miniflare 5.20260926.1-alpha**. That is the first wrangler release with R2's 8 KiB custom-metadata limit; the tested 4.143.0 has 2 KiB (note N2).
   - Accept a new pin only after `spikes/G2-S1/fidelity.py` and `sdk/sdk_quirks.mjs` pass on it with no unexplained change from the 2026-09-29 baseline.
   - Test runners:
     - Worker unit tests use `@cloudflare/vitest-plugin` (K13).
     - End-to-end presigned flows use `wrangler dev`, Miniflare's Node API or `createTestHarness()`. A0 picks whichever exposes the S3 endpoint (note, open question 4).
   - Subject to OD-14 option 1 (see Decision requests in the note).
2. **Binding harness rules** for anything that runs on the local stack (note F3):
   1. **Fail-closed screening proxy** in front of the local S3 endpoint. It returns 501 for any request carrying `x-amz-checksum-*`, `x-amz-sdk-checksum-algorithm`, `Content-Encoding: aws-chunked`, a `STREAMING-*` `x-amz-content-sha256`, or `Transfer-Encoding: chunked`. Because: Miniflare returns 200 and stores wrong or tampered bytes for these (T41, T44, T47).
   2. **Integrity assertions** use signed Content-MD5, which is enforced (T40, T48), or a read-back SHA-256 by the homelab. Never flexible checksums. No checksum-based control may be claimed from a local run.
   3. **Error-class and retry assertions** (5xx retryable, 403 terminal, 412 vs 429) do not run against raw Miniflare. They run behind the harness fault-injection proxy, which injects only R2-documented faults such as 429 on same-key writes within 1 s, or on RustFS, or on SB. Because: rejected requests intermittently come back as 500 (up to 29 of 50).
   4. **Stability.** Health-check and auto-restart the endpoint. A run during which workerd crashed is **invalid**, not failed, and is re-run.
   5. **Part-size errors.** Assert only that Complete fails and nothing is stored, not the error code. Miniflare answers 404 `NoSuchUpload` (T32/T33).
   6. **Append-only.** Assert what the Worker **mints**: never DELETE, GET or HEAD URLs for device credentials, and every device PUT URL has `if-none-match` in `X-Amz-SignedHeaders`. Enforcement itself is SB-only: the local credential is all-powerful, presigned DELETE works (T52), and token scope is not emulated.
   7. **Emulated pieces.** A test-clock lifecycle sweeper (Miniflare has no lifecycle, T54) and 429 injection. Every result that depends on them is labelled **emulated**.
   8. **Queues.** A0 reports state that ADR-0001's queue pull path is not exercised locally (K7). A pull/ack substrate is a default Wave 2 harness component: a fake of the REST pull/ack API, or a real sandbox queue. It is not conditional on a future ADR.
3. **Secondary differential target: RustFS 1.0.0**, with its image digest recorded at first use; versitygw v1.8.0 is the fallback.
   - It is used for differential runs of the fidelity script, and for checksum, ListParts and lifecycle-configuration checks that Miniflare cannot do.
   - It is not A0's store.
   - Its AWS-shaped behaviour is known and must not be read as R2 behaviour: no equal-part rule (T32/T33); 412 on conditional Complete (T38), where R2 documents no conditional Complete and Miniflare overwrites; 304 on CreateMultipartUpload with If-None-Match (T39).
   - **SeaweedFS** is a negative control only. It completes with a stale part ETag and stores the old part (T34b), against R2's documented part replacement.
4. **Real R2 (sandbox) is the gate** for every relied-on behaviour listed in note F4. Highlights: presigned `If-None-Match` (T22, T23, T25), Complete semantics (T37, T38), part-size error codes, ListParts, lifecycle and the 7-day abort, flexible-checksum validation (undocumented by R2, note N3), 412 vs 429 race losers, binding and S3 multipart interop (W04), token scope, and all measurements.
   - Route: the kit at `docs/research/kits/G2-S1/`, plus a hybrid `wrangler dev` with `remote: true`.
   - In hybrid mode the local S3 endpoint is not served for that bucket, so the presigner's endpoint and credentials are config-driven per mode.

### Not yet decided (Wave 3)

- The invariant table (from A3's state table) and the invariant → technique → CI-stage mapping.
- DST framework: turmoil vs madsim vs stateright (G2-S2). DST probably cannot drive Miniflare deterministically, so an in-process R2 model (for example on s3s) is a candidate. Its fault catalogue is tagged R2-documented, SB-measured or emulator-artifact.
- Fuzzing (G2-S3): cargo-fuzz vs bolero; ClusterFuzzLite (depends on OD-15).
- The fault-injection catalogue, mapped to B6's failure catalogue.
- The device matrix, lab and acquisition list (G2-S4, H5).
- Release gates and canary days.
- Whether to build an R2-semantics shim in front of RustFS (note, option L).
- One-line dispositions for the alternatives not yet evaluated: ceph s3-tests, Zenko CloudServer, S3Mock, gofakes3, AIStor Free.

### Consequences

- **Good:**
  - The Worker is tested with its production binding code against one store.
  - R2's equal-part rule and conditional-create races are exercised locally.
  - The inner loop is offline and needs no secrets.
  - Silent integrity gaps become loud failures instead of false passes.
  - A0 reports carry an explicit "emulated" boundary.
- **Bad / accepted trade-offs:**
  - It depends on an experimental endpoint on an alpha line, with config-key churn. Each bump needs a fidelity re-run.
  - The harness needs extra pieces: a screening and fault proxy, a lifecycle sweeper, health and restart, and later a pull/ack fake.
  - ListParts adoption, checksum controls and append-only enforcement cannot be shown locally at all.
  - RustFS adds a second server to maintain.
- **Follow-up work:**
  - Add the 8 KiB metadata check to `fidelity.py`.
  - Re-run the fidelity script on the first A0 pin. Check whether #15906 or the Node API removes the 500-on-reject problem.
  - Write the screening and fault proxy.
  - Apply the kit errata, then run the SB leg once the sandbox account and allowlist exist.
  - Wave 2: the pull/ack substrate.

### Confirmation

- **G2-S1 real-R2 leg (SB kit).** Pass means no difference between R2 and Miniflare on any relied-on check, apart from Miniflare's documented gaps. Each difference is recorded in A0's difference list and in this ADR.
- **CI check:** the fidelity script runs on every wrangler, miniflare or workerd lockfile change and diffs against the stored baseline.
- **CI check:** the screening proxy's 501 count is reported, and any non-zero count on an integrity test fails it.
- **Stability check:** the invalid-run rate on the local stack is tracked. More than 1 in 20 triggers a review of decision 1. G1 confirms the threshold.
- **BUD-REVOKE** (expiry mechanism): T08 and T09 on R2 (kit). The token-rotation lever is checked by D3-S5.

## Pros and cons of the options

### A / D. Miniflare local R2 S3 endpoint (D adds the secondary and the gate)

- Good, because the binding and S3 share one store (K3, verified; W01–W04 emulated).
- Good, because `If-None-Match` on PutObject is atomic (K5, verified): exactly one winner in 20 of 20 rounds of a 16-way race, header-signed and presigned (T26, T27).
- Good, because R2's equal-part rule is enforced (T32/T33). No other target enforces it.
- Good, because presigned expiry is capped at 604,800 s, as on R2 (K8, verified; T09).
- Bad, because flexible checksums are ignored, `aws-chunked` is not decoded, and there is no `100 Continue`, ListParts or lifecycle (K6, verified). The first two silently store wrong bytes (T41, T44, T47).
- Bad, because its R2 fidelity rests on a vendor capture with no published data (K4, verified as a statement about the source), and the capture is only partly reflected: `NoSuchUpload` for part-size violations, 500 instead of 403 on some rejects.
- Bad, because the endpoint is experimental, on an alpha line, with key churn and a stale pin within days (K1, K2, verified).
- Bad, because there is no Queues HTTP pull (K7, verified).

### B. A standalone S3 server as primary

- Good, because RustFS and versitygw reject bad checksums, decode `aws-chunked`, and answer ListParts (emulated run).
- Bad, because the Worker would have to use the S3 API instead of its binding, so the code under test would differ from production if C1 keeps the binding.
- Bad, because they are AWS-shaped: no equal-part rule, and conditional Complete returns 412 (which would mask a protocol bug that relies on it).
- Bad, because SeaweedFS stores the old part on a stale ETag (T34b; K11's use withdrawn).

### C. Real R2 only

- Good, because it is ground truth.
- Bad, because it is blocked from the container today, costs money, has a slow inner loop, and needs secrets in CI. It is kept as the gate, not the loop.

## Evidence

| Claim | Source (primary) | Verdict |
|---|---|---|
| K2 local S3 endpoint, SigV4 header and presigned, config key | miniflare and wrangler CHANGELOG (#14280); wrangler 4.143.0 validator | Verified |
| K3 one store for binding and S3 (not served for `remote: true` buckets) | miniflare 5.20260926.0-alpha source (`getR2S3Service`, s3 workers); spike W01–W04 | Verified |
| K5 atomic local `If-None-Match` on PutObject; Complete ignores it | miniflare source (`bucket.worker.ts`, `operations.worker.ts`); spike T20, T26, T27, T38 | Verified |
| K6 local gaps (ListParts, lifecycle, checksums, aws-chunked, 100-continue, session token) | miniflare `index.worker.ts`; R2 `api.mdx`, `temporary-credentials.mdx` | Verified |
| K7 no local Queues HTTP pull | miniflare broker source; wrangler validator | Verified |
| K8 604,800 s presign cap | miniflare `auth.worker.ts`; R2 `presigned-urls.mdx` | Verified |
| K9, K10 MinIO archived; Garage has no conditional writes | MinIO README and repo metadata; Garage `known-issues.md` (mirror) | Verified |
| K11 SeaweedFS vendor claims (use withdrawn by T34b) | SeaweedFS README and source | Verified (claim); not relied on |
| K12 remote bindings for R2, D1 and Queues, not DOs | `bindings_per_env.mdx`; `local-development/index.mdx` | Verified |
| K13 `@cloudflare/vitest-plugin` recommended | `vitest-integration/index.mdx`; npm registry | Verified |
| K14 R2 lists no conditional Complete; implements ListParts | R2 `api.mdx` | Verified |
| N1 R2 1 write/s per key, excess 429; N2 8 KiB metadata vs 2 KiB in pin; N3 no documented flexible checksums on PutObject | R2 `limits.mdx`, `api.mdx`; miniflare CHANGELOG #15910 and tarball constant | Primary, not tallied (supporting only; each sits beside verified claims) |

No contested or secondary-only claim supports this decision.

## Reversibility

Easy. The choice lives in harness code and a lockfile. Swapping the primary target for RustFS, or for a future official emulator, costs harness glue plus a fidelity re-run. If C1 has the Worker use the S3 API instead of the binding, that swap gets cheaper. Nothing here is persisted in user data or shipped to devices.

## Alternatives considered

- **Garage:** ignores `If-None-Match` and `If-Match`; 16 of 16 concurrent writers win (K10, T26). It cannot model conditional create.
- **MinIO community:** archived, source-only (K9). Excluded by the PLAN rule.
- **LocalStack:** the 2026.8.4 image exits without `LOCALSTACK_AUTH_TOKEN`; AWS semantics, not R2. Not evaluated further.
- **moto (server mode):** verifies no signatures (T04–T13 all 200). Acceptable only as an in-process unit mock.
- **s3s-fs:** not run; a sample implementation with auth off by default. It may come back as the base for a DST R2 model (Wave 3).

## Open questions

- Does every relied-on behaviour match on real R2? (G2-S1 SB leg with C1-S1; Gate B.)
- Does R2 reject a tampered body when a SHA-256 or CRC64NVME checksum is signed into a presigned PUT? (C1-S1.)
- Does the Rust S3 client work against the path-prefixed endpoint with expect-continue off and checksums `WHEN_REQUIRED`? (A0 build.)
- Which runner exposes the local S3 endpoint to an external client: vitest-plugin, `createTestHarness()`, or the Miniflare Node API? (A0 / G2.)
- Do newer pins (#15906) or driving Miniflare without wrangler's ProxyWorker remove the 500-instead-of-403 and crash problems? (G2.)
- Does rotating or deleting the R2 token invalidate outstanding presigned URLs? (D3-S5.)
- Pull/ack substrate: a fake or a real sandbox queue? (G2 with A3, Wave 2.)
- Everything under "Not yet decided" (G2, Wave 3).
