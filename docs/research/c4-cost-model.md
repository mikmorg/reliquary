# C4. Cost, capacity and storage-budget model (v0)

- **Workstream:** C4 (see `docs/research/PLAN.md`, section "C4.")
- **Status:** Final for Wave 1 (v0). The skeptic review ran (sources, logic and adversary lenses) and the C4-S1 spike ran. v1 follows once A0, E1, H2 and the C2 `[SB]` checks report.
- **Date:** 2026-09-29 (last updated 2026-10-06, synthesis)
- **Feeds:** OD-14 (BUD-CLOUD, BUD-ABUSE, billing alerts, beta-feature policy), OD-20 (per-person budgets and approval categories), ADR-0030 (C5 BOM: cost and capacity inputs), ADR-0010 (C1: warm cache, meters, seed admission), ADR-0014 (D3 + C2: abuse limits, conditional create), ADR-0021 (B6: part-size policy). C4 owns **no ADR** (PLAN §2.1). It owns this model, the script and CSVs (`spikes/C4-S1/`), the billing-alert list (§F4) and the fair-share proposal (§F9).
- **Depends on:** T2 (`fact-check-adr-0001-0002.md`), T1 spike 2 (`content-encryption-format.md`, part size), H2 (`owner-intake.md` B1–B4, C4, D1–D2, F4), H5 (`h5-long-lead-items.md` fee and lead-time lines). **Still missing:** A0 (measured operations per file), E1 (growth per person and file sizes), A6 (storage-engine overhead), C5 (BOM prices), H2 answers, C2 `[SB]` billing checks.
- **Traceability rows closed or advanced:** R-09 (scale), R-26 (keep forever: capacity forecast), R-31 (storage-issue nudges: pool-full behaviour), C-01 (warm-cache orphan: cost side only)

## Summary

At steady state the cloud bill is a little over the fixed $5 Workers Paid fee. The C4-S1 model gives a central $5.00–7.52 per month. Across every combination of the assumed ranges, the highest result is $11.16. Both are well below the proposed $25 BUD-CLOUD, but the ±25 % precision target is **not** met above 0.5 TB/yr of growth until A0 measures CPU per request and mean file size. A 2 TB seed month through R2 costs about $12–18. It costs about $42 if a 30-day warm cache stays on. A seed from a home behind a **data cap** can cost far more ($60–100 per month) unless the Worker paces seed uploads to what the homelab may pull. Cloudflare has no spend cap: budget alerts are informational, a day late, and exclude the $5 fee. Abuse spend is therefore **unbounded today**. It can be held under a $50 BUD-ABUSE only with Reliquary's own controls: mandatory create-only writes, per-device caps, two independent spend meters and a key-rotation kill switch. That bound is **provisional** on four billing behaviours that only a sandbox can check. On the homelab, the risk is capacity rather than money. A 2 × 16 TB mirror holding 10 TB reaches 80 % full in about 2 years at 1.5 TB/yr, so C5 should price the 32 TB tier as the reference case. Confidence: high on unit prices, medium on volumes, low on homelab running costs.

## Questions

| # | Question (PLAN C4) | Short answer | Confidence |
|---|---|---|---|
| 1 | Line items: Workers Paid, requests, CPU, D1, DOs, Queues, R2 storage and Class A/B, email | Every unit price comes from a primary source (K2, K7, K11, K15; §F1). At family scale only four lines cost money: the $5 fee, R2 Class A in seed months, staged storage, and Queues in seed months. Workers Logs is a fifth line that matters only under floods, and its pricing changes on **2026-12-01**. | High on prices; Medium on volumes (A0 pending) |
| 2 | Seed scenarios: 10 TB via R2 with 8/16/64 MiB parts, mostly USB, or legacy import; peak staging for a drain rate | 10 TB through R2 at 2 TB/month costs **$60.80** in total, or $210.80 with a 30-day warm cache (C4-S1). Part size is **not a cost lever**: at most $8.58 per 10 TB even if every byte went in parts (K9). Without an ISP cap, peak staging is set by homelab downtime and the warm cache. **With a cap**, it is set by the cap, and an unpaced R2 seed overruns the $50 seed ceiling (§F3). | Medium |
| 3 | Home ISP: caps, hairpin, restore over uplink, puller throttle | A home upload crosses the home link twice. Pacing the puller to a cap is cheap **only if seed admission is paced too**. Otherwise the backlog sits in R2 at $15/TB-month. Restores are limited by the uplink: 1 TB takes 4.63 days at 20 Mbps (§F5). | High on arithmetic; Low on ISP terms |
| 4 | Growth, dedup ratio, redundancy overhead, headroom, disk-purchase trigger | We have the method and three tiers (§F6). The trigger dates for the scenarios are computed (C4-S1). The family's own date is **no result** until H2 and E1 report. Dedup and engine overhead are also no result yet (A1/F3, A6). | High on method; no family data |
| 5 | Homelab running costs | Formulas only (§F7). The drive AFR is **contested** (secondary sources only, K13). Power price, $/TB and UPS battery life are owner or C5 inputs. | Low |
| 6 | Optional costs | Apple $99/yr; Azure Artifact Signing Basic $9.99/month (K14); Android $25 or $0; domain about $10–15/yr (estimate); email $0 within 3,000/month (K15) (§F8). Apple and Azure apply only if OD-01 or OD-09 changes the settled "no signing, iOS deferred". | High (domain Low) |
| 7 | Storage governance | A proposal for OD-20 (§F9): soft per-person budgets; approval categories uploaded at **lowest priority** rather than withheld; green, amber and red pool states; no refusal without an owner decision. | Medium |
| 8 | Alternatives | Workers Paid (K7). R2 Standard, never IA, for staging (K8). Part size chosen on non-cost grounds (K9). Mirror vs RAIDZ2 and new vs recertified drives go to C5 (§Alternatives). | High / High / Medium / Low |
| 9 | **New:** does any Cloudflare mechanism cap spend? | **No** (K1). Alerts are informational and a day late. Threshold billing only invoices early. The per-Worker CPU limit caps CPU per call, not total spend. | High |
| 10 | **New:** which abuse costs are not bounded by per-device limits? | Unauthenticated floods on the Worker ($276/day at 10k req/s, plus up to $518/day if logs are not sampled), and possibly requests straight to R2 that return 403, 412 or 429 (K6). Both need `[SB]` checks. | Medium |
| 11 | **New (skeptics):** can abuse or ransomware churn consume **keep-forever capacity**? | Yes. Anything the homelab commits stays until the admin prunes it. 100 GB/day from one device adds about 3 TB/month. Proposal: per-device ingest caps and a homelab **quarantine** area (§F4.4). | Medium |

## Method

- **Sweep:** two scouts (vendor docs and pricing; source code and similar work), an analyst deep read, the C4-S1 `[CT]` model run, three skeptics (sources, logic, adversary), and this synthesis. For the synthesis I re-fetched from `cloudflare-docs @ production` on 2026-10-06: Workers pricing (custom CPU limits), the Workers Logs pricing partial (2026-12-01 change), R2 metrics and analytics (GraphQL), R2 event notifications (overwrites fire `object-create`), the R2 S3 API table (PutObject headers; CompleteMultipartUpload conditionals), Workers limits (request body), R2 object lifecycles, R2 presigned URLs (temporary credentials), and the R2 Workers API reference (`onlyIf`).
- **Model:** `spikes/C4-S1/c4_model.py` (Python stdlib), with CSVs in `spikes/C4-S1/out/` and the run log in `spikes/C4-S1/evidence/run_output.txt`. **The note now uses the spike's day-by-day simulator figures** throughout. They supersede the analyst's `I·(d+W)/30` approximation, which under-counted R2's daily-peak metric by about one day of inflow (K3, contested). Some figures that are new in this synthesis were computed in the scratchpad using the same unit prices: abuse with included allowances, replay including Queue operations, part sizes at b_mp = 0.6, the capped-ISP seed, and the Workers Logs flood term. Each formula is shown where it is used. They are labelled **(synthesis calc)**.
- **Routes used:** `cloudflare/cloudflare-docs @ production` on raw.githubusercontent.com (primary mirror); `MicrosoftDocs/azure-docs @ main`; `proxmox/pve-docs @ master`; developer.android.com direct; GitHub raw for rclone, Ente and Immich.
- **Blocked sources (reported to H1):** developers.cloudflare.com (mirror used); azure.microsoft.com pricing (docs mirror used); backblaze.com and ir.backblaze.com (Drive Stats: **secondary only**; a skeptic re-confirmed a proxy 403 on 2026-10-06); xfinity.com (secondary only); eia.gov (electricity price: **no source**); diskprices.com and pcpartpicker.com ($/TB: **no source**); ente.com pricing (secondary only); support.google.com and play.google.com (Play fee covered indirectly by the developer.android.com FAQ). Context7 returned "monthly quota exceeded". The WebSearch budget was exhausted before the analyst pass.
- **Stop rule:** every Cloudflare line item has a primary source. The remaining gaps (disk $/TB, power price, primary AFR data, ISP terms, billing of 4xx responses) need an allowlist change, owner input or a sandbox. More sweeping would not close them.
- **Units:** R2 prices are per GB. The R2 limits page defines GB as 10^9 bytes, and the model uses that.

## Sources

| # | Source | Publisher | Version date | Accessed | Primary? |
|---|---|---|---|---|---|
| S1 | R2 Pricing: `cloudflare/cloudflare-docs @ production : src/content/docs/r2/pricing.mdx` | Cloudflare | production | 2026-09-29; skeptics 2026-10-06 | Yes |
| S2 | R2 Limits: `… : docs/r2/platform/limits.mdx` | Cloudflare | production | 2026-09-29 | Yes |
| S3 | R2 Presigned URLs: `… : docs/r2/api/s3/presigned-urls.mdx` | Cloudflare | production | 2026-10-06 | Yes |
| S4 | R2 Object lifecycles: `… : docs/r2/buckets/object-lifecycles.mdx` | Cloudflare | production | 2026-10-06 | Yes |
| S5 | R2 Event notifications: `… : docs/r2/buckets/event-notifications.mdx` | Cloudflare | production | 2026-10-06 | Yes |
| S6 | R2 S3 API compatibility: `… : docs/r2/api/s3/api.mdx` | Cloudflare | production | 2026-10-06 | Yes |
| S7 | Workers Pricing: `… : docs/workers/platform/pricing.mdx` | Cloudflare | production | 2026-10-06 | Yes |
| S8 | Workers Limits: `… : docs/workers/platform/limits.mdx` | Cloudflare | production | 2026-10-06 | Yes |
| S9 | Workers Logs pricing partial: `… : partials/workers/workers_logs_pricing.mdx` | Cloudflare | production | 2026-10-06 | Yes |
| S10 | D1 pricing partial: `… : partials/workers/d1-pricing.mdx` | Cloudflare | production | 2026-09-29 | Yes |
| S11 | D1 Limits: `… : docs/d1/platform/limits.mdx` | Cloudflare | production | 2026-09-29 | Yes |
| S12 | Queues pricing partial: `… : partials/workers/queues_pricing.mdx` | Cloudflare | production | 2026-09-29 | Yes |
| S13 | Queues Limits: `… : docs/queues/platform/limits.mdx` | Cloudflare | production | 2026-09-29 | Yes |
| S14 | Durable Objects pricing partial: `… : partials/durable-objects/durable-objects-pricing.mdx` | Cloudflare | production | 2026-09-29 | Yes |
| S15 | Changelog "Billing for SQLite Storage": `… : changelog/durable-objects/2025-12-12-…` | Cloudflare | 2025-12-12 | 2026-09-29 | Yes |
| S16 | Email Service Pricing: `… : docs/email-service/platform/pricing.mdx` | Cloudflare | production | 2026-09-29 | Yes |
| S17 | Budget alerts: `… : docs/billing/manage/budget-alerts.mdx` | Cloudflare | production | 2026-09-29; skeptics 2026-10-06 | Yes |
| S18 | Changelog "Budget alerts now on by default…": `… : changelog/billing/2026-06-15-budget-alerts-default-on.mdx` | Cloudflare | 2026-07-20 (frontmatter) | 2026-09-29 | Yes |
| S19 | Threshold billing: `… : docs/billing/threshold-billing.mdx` | Cloudflare | production | 2026-09-29 | Yes |
| S20 | Billing policy: `… : docs/billing/understand/billing-policy.mdx` | Cloudflare | production | 2026-09-29 | Yes |
| S21 | WAF rate limiting availability by plan: `… : partials/waf/rate-limiting-availability-by-plan.mdx` | Cloudflare | production | 2026-09-29 | Yes |
| S22 | Workers Rate Limiting binding: `… : docs/workers/runtime-apis/bindings/rate-limit.mdx` | Cloudflare | production | 2026-09-29 | Yes |
| S23 | Artifact Signing SKU: `MicrosoftDocs/azure-docs @ main : articles/artifact-signing/how-to-change-sku.md` | Microsoft | ms.date 2026-01-06 | 2026-09-29; skeptic 2026-10-06 | Yes |
| S24 | Artifact Signing quickstart: `… : articles/artifact-signing/quickstart.md` | Microsoft | ms.date 2026-05-21 | 2026-10-06 (skeptic) | Yes |
| S25 | Apple Developer Program, https://developer.apple.com/programs/ | Apple | undated | 2026-09-29 | Yes |
| S26 | Android developer verification FAQ, https://developer.android.com/developer-verification/guides/faq | Google | entries 2026-03-25, 2026-06-18 | 2026-09-29 | Yes |
| S27 | Proxmox VE ZFS: `proxmox/pve-docs @ master : local-zfs.adoc` | Proxmox | master | 2026-09-29; skeptics 2026-10-06 | Yes |
| S28 | rclone `backend/s3/s3.go`, `fs/chunksize/chunksize.go` | rclone | master | 2026-09-29 | Yes (code) |
| S29 | Ente `server/pkg/controller/usage.go`, `file.go` | Ente | main | 2026-09-29 | Yes (code) |
| S30 | Ente help "Family plans": `ente-io/ente @ main : docs/docs/photos/features/account/family-plans.md` | Ente | main | 2026-09-29 | Yes |
| S31 | Immich `server/src/services/asset-media.service.ts` `requireQuota` | Immich | main | 2026-09-29 | Yes (code) |
| S32 | restic `internal/repository/repository.go` | restic | master | 2026-09-29 | Yes (code) |
| S33 | kopia `repo/format/content_format.go` | kopia | master | 2026-09-29 | Yes (code) |
| S34 | Backblaze Drive Stats Q1 2026, https://www.backblaze.com/blog/backblaze-drive-stats-for-q1-2026/ | Backblaze | 2026 | **snippet only** (blocked) | No |
| S35 | Backblaze 2025 Drive Stats release, via BusinessWire: https://www.businesswire.com/news/home/20260212236512/en/ | Backblaze (publisher-issued release) | 2026-02-12 | 2026-10-06 (skeptic; not re-read in synthesis) | No (the primary data is blocked) |
| S36 | Xfinity data-usage plan FAQ | Comcast | undated | snippet only | No |
| S37 | Backblaze B2 pricing (secondary snippets) | Backblaze | unknown | snippet only | No |
| S38 | Ente pricing via saasworthy.com | third party | "September 2026" | snippet only | No |
| S39 | R2 Metrics and analytics (GraphQL `r2OperationsAdaptiveGroups`, `actionType`, `bucketName`): `… : docs/r2/platform/metrics-analytics.mdx` | Cloudflare | production | 2026-10-06 | Yes |
| S40 | R2 Workers API reference (`R2PutOptions.onlyIf`, `R2Conditional`): `… : docs/r2/api/workers/workers-api-reference.mdx` | Cloudflare | production | 2026-10-06 | Yes |
| I1 | `docs/research/content-encryption-format.md` (T1 spike 2): P = k × 65,552 B, k = 80·2^j; default 5,244,160 B | Reliquary | 2026-09-29 | 2026-10-06 | Internal |
| I2 | `docs/research/owner-intake.md` §B (B1–B4 proposed defaults) | Reliquary | 2026-09-29 | 2026-10-06 | Internal |
| I3 | `docs/research/h5-long-lead-items.md` (domain, drive estimates, marked E) | Reliquary | 2026-09-29 | 2026-09-29 | Internal |
| I4 | `spikes/C4-S1/` (model, CSVs, run log) | Reliquary | 2026-09-29 run | 2026-10-06 | Internal (evidence) |

## Claims

### Key claims (skeptic-reviewed)

Verdicts are the computed tally. A claim is **verified** if it has a primary source and at least 2 of 3 skeptics did not refute it, **secondary only** if it has no primary source, and **contested** otherwise. Where a verified claim's *figures* were corrected by the skeptics, the corrected figure is given and used in this note.

| # | Claim (as reviewed) | Sources | Sources lens | Logic lens | Adversary lens | Verdict | Used in this note as |
|---|---|---|---|---|---|---|---|
| K1 | Budget alerts are informational, never cap, are processed daily (they fire the next day) and exclude subscription fees, so Reliquary must enforce BUD-ABUSE itself | S17, S18 | Upheld | Upheld | Upheld | **Verified** | As stated |
| K2 | R2 Standard: $0.015/GB-month, Class A $4.50/M, Class B $0.36/M; free tier 10 GB-month, 1M A, 10M B (Standard only); usage rounds up; GB-month = mean of daily peak | S1 | Upheld | Upheld | Upheld | **Verified** | As stated |
| K3 | Steady state $5.00–7.36; 2 TB seed month $11.16 / $13.96 / $40.15 | analyst model | Refuted | Refuted | Refuted | **Contested** | **Superseded** by C4-S1: steady state central $5.00–7.52, maximum $11.16 over the full factorial; seed month $12.16 / $15.66 / $42.16. Not used as sole support for anything |
| K4 | Junk small objects cost about $8/M, so 1,000/s exhausts $50 in about 1.7 h | S1, S7, S10, S12 | Upheld (caveats) | Refuted (allowances) | Upheld | **Verified** | Marginal rate $8.00/M **once all allowances are used**; from zero it is about 2.5 h to $50 and about $645 for a full day (synthesis calc, §F4) |
| K5 | A presigned URL is reusable until expiry and same-key writes are limited to 1/s, so replay causes up to expiry-seconds billed writes | S2, S3 | Upheld | Upheld (+Queue ops) | Refuted (bound not established) | **Verified** | Restated as a **lower bound**, valid only if 412/429/403 responses are not billed. Each successful overwrite also fires `object-create` (S5), so the cost is $5.70/M per replayed write |
| K6 | R2 documents only 401 as unbilled; 403/412/429 are undocumented; Worker floods are billed per request | S1, S3, S7 | Upheld | Upheld | Upheld | **Verified** | As stated |
| K7 | Workers Free cannot carry a seed (Queues 10k ops/day, D1 100k rows/day, 10 ms CPU, no email to arbitrary recipients) | S10, S12, S16, S7 | Upheld | Upheld | Upheld | **Verified** | As stated. The 1,667 files/day figure assumes the event-notification queue design |
| K8 | IA is about 10× Standard for short-dwell staging | S1 | Upheld (ratio wrong) | Upheld (ratio wrong) | Upheld (ratio wrong) | **Verified** | Conclusion kept. Figures restated: 2 TB for 2 days is about $51 in IA ($20 + $20 retrieval + $11 Class A) vs about $2; seed month $64.70 vs $12.16 |
| K9 | Part size is not a cost lever; parts for 10 TB cost $8.58 at about 5.0 MiB and $0.67 at 64 MiB; about 81 % of Class A is per-file | S1, I1 | Upheld (b_mp inconsistent) | Upheld (invalid sizes) | Upheld | **Verified** | Conclusion kept. Figures recomputed at valid T1 sizes and b_mp = 0.6 (§F3) |
| K10 | The warm cache is the largest controllable line: a 30-day warm cache turns a seed month from about $11 into about $40 | model, S1 | Upheld | Upheld | Upheld | **Verified** | Figures updated to C4-S1 ($12.16 → $42.16, sustained seed month) |
| K11 | One always-on DO uses 324,000 GB-s/month; two exceed 400,000 and round up to $12.50 | S14 | Upheld | Upheld | Upheld | **Verified** | As stated |
| K12 | Tier S reaches 80 % in about 1.9 y at L0 = 10, g = 1.5; tier M lasts about 7.8–10.4 y | S27, model | Upheld (zvol caveat) | Upheld (scenario-only) | Upheld (zvol caveat) | **Verified** | A scenario statement, not a family forecast. zvol, slop and dedup caveats added (§F6) |
| K13 | Backblaze AFR is about 1.2–1.6 % | S34, S35 (secondary) | Upheld (secondary) | Refuted | Refuted | **Contested** (no primary) | Feeds only the low-confidence drive-replacement line. Not used for any recommendation |
| K14 | Azure Artifact Signing Basic $9.99/month (5,000 signatures), Premium $99.99 (100k); individuals in the US or Canada | S23, S24 | Upheld | Upheld | Upheld | **Verified** | As stated. The US/Canada rule is for Public Trust individuals; organisations elsewhere are eligible |
| K15 | Email Service: 3,000/month included on Paid, then $0.35/1,000; sends to verified addresses are free | S16 | Upheld | Upheld | Upheld | **Verified** | As stated, **plus** the dependency: verified destinations are an Email Routing feature that needs a zone on Cloudflare (the domain line) |

### Supporting claims (primary, not separately in the tally)

| # | Claim | Sources |
|---|---|---|
| C4 | Class A: PutObject, CreateMultipartUpload, UploadPart, CompleteMultipartUpload, List*, CopyObject. Class B: GetObject, HeadObject. DeleteObject and AbortMultipartUpload are free | S1 |
| C5 | Workers Paid: $5 minimum; 10M requests then $0.30/M; 30M CPU-ms then $0.02/M. A per-invocation CPU limit can be set "to prevent accidental runaway bills or denial-of-wallet attacks" | S7 |
| C6 | D1 Paid: 50M rows written included, then $1.00/M; Queues Paid: 1M ops included, then $0.40/M, about 3 ops per message, retention 4 days by default (14 max) | S10, S12, S13 |
| C8 | `object-create` fires "when new objects are created or existing objects are overwritten" (PutObject, CopyObject, CompleteMultipartUpload) | S5 |
| C9 | Workers Logs on Paid: 20M events/month included, then $0.60/M. "Beginning December 1, 2026, Workers Logs will use Cloudflare Observability pricing" | S9 |
| C12 | Threshold billing invoices early at a threshold the customer cannot change. A failed preauthorisation can make R2 buckets inaccessible, and data may be deleted after 30 days | S19, S20 |
| C13a | R2 PutObject supports If-None-Match, Content-MD5 and `x-amz-storage-class` (STANDARD **and STANDARD_IA**). UploadPart supports Content-MD5. **CompleteMultipartUpload lists no conditional headers** | S6 |
| C13b | The R2 Workers binding `put()` takes `onlyIf` (R2Conditional or Headers); a failed condition returns null | S40 |
| C13c | Request bodies to a Worker are limited to 100 MB on Free and Pro zones | S8 |
| C13d | R2 bucket operations are queryable through GraphQL `r2OperationsAdaptiveGroups` by `actionType` and `bucketName` | S39 |
| C19 | Proxmox: mirrors give 50 %; RAIDZ-P over N disks gives roughly N−P; ZVOLs on RAIDZ carry extra parity and padding (an 8k block on RAIDZ2 writes 16k); a 4-disk RAIDZ2 has the same usable space as 2 mirror vdevs | S27 |
| C22 | Android: $25 for a full-distribution developer account; waived for limited distribution (≤ 20 devices) | S26 |
| C23 | Ente: admin-set per-member limits in a family pool, 50 MiB overflow. Immich: hard per-user quota | S29–S31 |

## Model

### Parameters

**P** marks a primary price. **A** marks an assumption that the named workstream will replace. **O** marks an owner input. The full list, with each parameter's owner, is in `spikes/C4-S1/out/params.csv`.

| Parameter | Symbol | v0 value | Status |
|---|---|---|---|
| Mean file size | s̄ | 4 MB (250k files/TB); range 2–8 MB | **A**, E1, A0 |
| R2 objects per file | 1 + m | 2; m ≈ 0 if metadata records are batched | **A**, A2/A3 |
| Share of bytes in multipart files | b_mp | 0.6 | **A**, E1/A5 |
| Part size | P | 5,244,160 B (T1 default; valid sizes are 80·2^j × 65,552 B ≈ 5, 10, 20, 40, 80 MiB) | B6 |
| Queue messages per file | q | 2 | **A**, C1 |
| Worker requests per file | r | 3 | **A**, A0 |
| CPU per request | c | 5 ms | **A**, A0 / D3-S1 (**the largest single sensitivity**) |
| D1 rows written per file | w | 6 | **A**, A0/C1 |
| Staging dwell | d | 1 day nominal (range 1–14) | **A**, A3/C1; **the ISP cap overrides it** (§F3) |
| Warm-cache window | W | 0 or 30 days | C1 (C-01) |
| Library, growth | L0, g | 2–10 TB; 0.5–2 TB/yr (scenarios only) | **O** (H2 F4), E1 |
| Fill target | h | 80 % of usable | **O**, C5 (rule of thumb; no primary source) |

### Formulas

- Class A per month = N·(1 + m) + B·b_mp/P + 2·N·f_mp, billed at $4.50 per started million above 1M.
- Staged GB-month = mean over the month of each day's **peak** staged GB. The peak includes that day's uploads before that day's deletions (C4-S1 simulator, the literal reading of S1).
- Queues = 3·q·N ops; Workers = r·N requests and r·N·c CPU-ms; D1 = w·N rows; each billed above its allowance, with usage rounded up (S1, S7, S10, S12).
- Rounding order (free tier first or rounding first) made no difference in the 2 TB seed case (C4-S1).

### Results (C4-S1 simulator, `spikes/C4-S1/out/scenarios.csv`)

| Scenario | Total $/month |
|---|---|
| Steady, g = 0.5 TB/yr, W = 0 / 30 d | 5.00 / 5.53 |
| Steady, g = 1 TB/yr, W = 0 / 30 d | 5.00 / 6.19 |
| Steady, g = 2 TB/yr, W = 0 / 30 d | 5.03 / 7.52 |
| **Steady, highest value over the full factorial (59,049 combinations)** | **11.16** (g = 2, W = 30) |
| Seed month 2 TB, 1-day dwell | 12.16 |
| same, 14-day homelab outage | 15.66 |
| same, 30-day warm cache on (sustained seed month) | 42.16 |
| same, 2 MB / 8 MB mean file | 17.86 / 7.26 |
| same, metadata batched (m = 0) | 7.66 |
| same, P = 8 / 16 / 64 MiB | 12.16 (rounding hides the difference) |
| same, staged in R2 Infrequent Access | 64.70 |
| Homelab down all month, 2 / 5 / 10 TB staged | 34.85 / 79.85 / 154.85 |
| Restore 500 GB staged 7 d + 1 d lifecycle lag | +2.10 over steady |
| 10 TB seed via R2, 5 months (total) | 60.80; 210.80 with the warm cache |
| **10 TB seed from a capped home, unpaced** (synthesis calc, §F3) | up to about $100/month; about $870 in total |
| 10 TB seed from a capped home, **paced to the pull allowance** (synthesis calc) | about $5.50/month; about $88 in total over about 15 months |

Break-even against a $25 BUD-CLOUD ($20 of usage): about 1.34 TB staged on average, or about 5.4M Class A operations in a month.

## Findings

### F1. Line items (Q1). Confidence: High on prices, Medium on volumes

- All unit prices are primary (K2, K7, K11, K15, C4–C9). T2's figures and the owner intake's unit prices are confirmed.
- Two corrections to `owner-intake.md` §B. (1) **B2:** 1.5M Class A bills as 2M under S1's rounding rule, so the charge is **$4.50**, not $2.25 (K2). (2) **B1:** budget alerts exclude the $5 fee (K1), so a **$20 usage alert means a $25 bill**. Usage-alert thresholds should be set at BUD-CLOUD − $5.
- **Workers Logs** (C9) is zero at family scale but matters under floods: up to $0.60/M events beyond 20M. The pricing moves to Cloudflare Observability on **2026-12-01**, so this model expires on that line and must be re-checked then. Recommendation: head-sample logs on the public endpoint.
- **Always-on Durable Objects are a trap** (K11). Two objects kept awake for a month cost $12.50. If C1 uses DOs, they should hibernate.
- **Email** costs $0 at family scale (K15). Owner alerts to a verified destination are free, but that needs Email Routing on a Cloudflare zone (the domain line), and the channel fails together with the account (§F4.3).
- D1 and DO storage are small: about 1 GB for 5M dedup rows, assuming about 200 B per row. Cost does not decide between D1 and DO.

### F2. Workers Paid vs Free (Q8). Confidence: High

Use Paid (K7). Free fails a seed on Queues (10k ops/day ≈ 1,667 files/day with event notifications), on D1 writes (100k/day, which would bind at about 16.7k files/day in a queue-less design), on 24 h queue retention, on the 10 ms CPU limit, and on email to the family (ADR-0002 signup). Paid costs $5/month and is 70–100 % of the steady-state bill.

### F3. Seed scenarios, peak staging and part size (Q2). Confidence: Medium

- **10 TB through R2, uncapped home link:** about 5 months at 2 TB/month and **$60.80** in total, or **$210.80** with the warm cache left on (C4-S1).
- **Capped home link (new; logic skeptic).** If the puller is throttled to a cap (§F5) while the family uploads faster than the pull allowance, staged bytes grow every month. Illustration (synthesis calc; the cap is not the owner's): with a 1.2 TB/month cap, 0.3 TB baseline use and an 80 % alert, the pull allowance is about 0.66 TB/month. At 2 TB/month of inflow, staged bytes reach **6.7 TB** after 5 months, the bill peaks at **about $100/month**, the whole drain takes about 16 months, and the total is **about $870**. That overruns the $50 seed ceiling from month 2 and hits the §F9 staging cap. **Fix:** the Worker paces presigns for seed traffic to the homelab's announced pull allowance (seed admission control). Paced, the same seed costs about $5.50/month and about $88 in total, but takes about 15 months. Under a cap, large seeds should therefore go by **USB** (A4), and the $50 seed ceiling does not cover an unpaced capped R2 seed.
- **Part size is not a cost lever** (K9, corrected). Recomputed at the valid T1 sizes with b_mp = 0.6, part operations for 10 TB cost **$5.15 / $2.57 / $1.29 / $0.64 / $0.32** at about 5 / 10 / 20 / 40 / 80 MiB. The all-multipart upper bound is $8.58 / $4.29 / $2.15 / $1.07 / $0.54. About 81 % of Class A comes from the per-file floor N·(1 + m). The larger lever is **batching metadata records** (m → 0), which takes a 2 TB seed month from $12.16 to $7.66. Batching must still satisfy ADR-0001's "encrypted metadata record per (device, file)"; A2/A3 decide. Packing small files restic-style would conflict with ADR-0001's dedup-ID-keyed objects, so it is not recommended. B6 should choose part size on resume, memory and iOS grounds.
- **Peak staging, uncapped:** set by homelab downtime and the warm cache, as long as the home downlink exceeds the family's upload rate (500 Mbps drains 10 TB in 1.9 days). **Capped:** set by the cap (above).
- **The warm cache is the largest controllable line** (K10): $12.16 → $42.16 in a sustained 2 TB seed month. The first month of a seed carries roughly half of that.
- **IA staging is worse on every line** (K8, figures corrected): 2 TB held for 2 days costs about $51 in IA ($20 for the 30-day minimum, $20 retrieval and $11 of doubled Class A with no free tier) against about $2 in Standard. A whole seed month is $64.70 against $12.16.
- **USB or legacy import (A9)** costs about $0 in cloud charges. Cloud cost does not choose the route; ISP caps, calendar time and owner effort do.

### F4. Worst-case abuse cost, controls and billing alerts (Q9–Q11). Confidence: High on mechanisms, Medium on figures

#### F4.1 Cloudflare will not stop spend

Budget alerts are informational, a day late, account-wide and exclude subscriptions (K1). Usage notifications need Pro and are informational. Threshold billing only invoices early (C12). The rate-limit binding is "not … an accurate accounting system" (S22). The per-invocation CPU limit (C5) bounds CPU per request but not the request count. **A hard-limit or prepaid payment card is not a safe backstop.** A declined preauthorisation can make R2 inaccessible and lead to data deletion (C12). That trades a cost risk for a data-loss risk, against "data integrity over everything", so it is rejected.

#### F4.2 Vectors and cost rates

| Vector | Who | Cost rate | Bounded by | Status |
|---|---|---|---|---|
| Small junk objects via presigned URLs | Holder of a stolen device credential | $8.00/M once allowances are used (K4). From a zero-usage month: $50 at about 9.0M objects (**about 2.5 h** at 1,000/s); after a seed month's usage, about 2.4 h; with every allowance exhausted, 1.7 h. One full day at 1,000/s is about **$645** (synthesis calc). The rate is a floor: logs, consumer invocations and homelab GETs add to it | Per-device presign cap; homelab decrypt-failure detector; spend meters | Design (C2) |
| Replay of a presigned PUT until expiry | same | At least one write/s per key while unexpired (K5, a lower bound), at **$5.70/M** per write including Queue ops on overwrite | **Mandatory create-only** (§F4.3); expiry ≤ 15 min (BUD-REVOKE) | Whether a signed If-None-Match is enforced, and whether 412/429 are billed: `[SB]` |
| Storage flood with large bodies | same | Scales with **attacker bandwidth**, not k: 1 Gbps ≈ 10.8 TB/day ≈ $5.40 per day held. A day's peak is billed even if the objects are deleted at once (daily-peak rule, K2) | Signed Content-MD5 or Content-Length; per-device staged-byte cap; size check before GET | Enforcement: `[SB]` |
| Writes in the IA storage class | same | 30-day minimum, 2× Class A, retrieval fee on every homelab GET | Sign `x-amz-storage-class: STANDARD`, or HEAD-check the class before pulling (C13a) | `[SB]` |
| Incomplete multipart parts | same | Unknown whether parts are billed as storage until abort | Lifecycle `AbortIncompleteMultipartUpload` set well below the 7-day default (S4) | `[SB]` |
| Garbage committed into keep-forever storage | same, or a ransomwared device | Capacity rather than dollars: 100 GB/day ≈ 3 TB/month, which brings the disk purchase forward and can turn the pool red | Per-device ingest cap and homelab quarantine (§F4.4) | Design (A3, D4) |
| Unauthenticated flood on the Worker | Anyone | $0.30/M requests + CPU: **$276/day** at 10k req/s and 1 ms. With unsampled logs, **+$518/day** (C9); at 1 % sampling, +$5/day | WAF rule (Free zone: 1 rule, per IP, 10 s; S21); per-invocation CPU limit (C5); head-sampled logs. **Not bounded by per-device caps** | WAF-blocked billing: `[SB]` |
| Bad-signature requests straight to R2 | Anyone who knows the bucket host | 403 is not documented as free (K6) | Unknown | `[SB]` |

#### F4.3 Required controls (input to C2/D3, ADR-0014)

1. **Create-only writes are mandatory, not an alternative to short expiry.** Reason: CLAUDE.md settles that devices "can only append backups, never delete or rewrite them". A replayable presigned PUT without a create-only condition lets a credential holder overwrite a staged object before the homelab pulls it. Options for C2/D3: (a) a signed `If-None-Match: *` on presigned PutObject (C13a; enforcement `[SB]`); (b) **Worker-mediated writes** through the R2 binding with `onlyIf` (C13b; whether a create-only condition can be expressed needs `[SB]`), which also removes replay, the storage-class trick and unbounded bodies, and fits the 100 MB request-body limit (C13c) at the cost of streaming through the Worker; (c) R2 temporary credentials scoped to a per-device prefix (S3). **Gap:** R2's CompleteMultipartUpload lists no conditional headers (C13a), so create-only for multipart objects (files larger than one part) needs a design answer from C2/A3. Expiry stays at the BUD-REVOKE 15 minutes. A 60 s expiry is **not** recommended: it conflicts with ADR-0001's batch-presign step and with intermittent connectivity, and R2 does not say whether expiry is checked at request start or at completion.
2. **Per-device caps:** U_d presigns per day and Q_d staged, uncommitted bytes per device, from declared sizes **bound by a signed Content-MD5 or Content-Length** (`[SB]`).
3. **Detectors with stated latency:** an overwrite event on a committed key (C8); declared vs actual size; **ciphertext that fails authentication at the homelab** (cheap junk cannot pass the homelab's AEAD check, but this detector is only as fast as the pull dwell); deviation from the device's own 30-day baseline (bytes/day, hours of activity). A credential holder who uploads valid, correctly sized ciphertext under the caps is **not** detectable by these. Only the meters bound that case.
4. **Two independent spend meters.** (a) The Worker's own counters × S1/S7/S10/S12 prices, updated in minutes. (b) A **cron-triggered Worker** (or the homelab) that polls Cloudflare's GraphQL analytics (C13d) for R2 operations by action, including failed requests, plus Worker invocations, because (a) cannot see traffic that bypasses the Worker. Take the larger of the two. The analytics lag is unknown (`[SB]`). (The earlier draft's "always-on consumer Worker" was a misnomer: a consumer runs only when batches arrive.)
5. **Suspension order: per device first.** Suspend the offending device automatically. Use a **global** presign stop only at a hard threshold (proposed BUD-CLOUD + BUD-ABUSE of usage in the month), because a global stop turns one stolen credential into a family-wide backup outage. Whether to allow the global stop at all is part of OD-14.
6. **Kill switch:** rotate or revoke the R2 access key that signs presigned URLs, so every outstanding URL dies, not just new ones. Whether revocation invalidates already-issued SigV4 URLs, and how fast, needs `[SB]`. Enforce a hard maximum expiry in code.
7. **Public-endpoint hygiene:** a per-invocation CPU limit (C5), head-sampled logs (C9), and a WAF rule on a device-auth header. mTLS (API Shield) is an option to check for plan availability.

**Bound for credential-holder abuse** (C4-S1 grid, re-run with $5.70/M per replayed write; synthesis calc): cost ≤ k·T·(U_d·E_eff·$5.7e-6 + U_d·$3.5e-6) + k·Q_d·$0.015, plus a bandwidth-bounded storage-flood term, plus floods. **k is an assumption.** With U_d = 25,000/day, Q_d = 100 GB and T = 1 day:

| Case | E_eff = 1 (create-only enforced) | E_eff = 60 | E_eff = 900 (15 min, no create-only) |
|---|---|---|---|
| k = 3 compromised devices | **$5.19** | $30.41 | $389.51 |
| k = 25 (every device: a family-wide leak or a malicious update) | **$43.25** | — | — |
| k = 3, T = 3 days (owner away) | $6.57 | — | — |
| **Undetected for a whole month at the caps** (k·30·U_d·$8e-6) | k = 3: **$18/month**; k = 25: **$150/month** | | |

The k = 25 case fits under $50 only because Q_d = 100 GB. In C4-S1's grid, only 21 of 81 all-device cap sets stay under $50. A month of undetected, cap-compliant abuse across all devices exceeds $50, so the spend meters, not the per-device caps, carry the bound in that case. **The whole bound is provisional** on four `[SB]` results: create-only enforcement, billing of 412/429/403, signed size enforcement, and incomplete-multipart storage billing.

#### F4.4 Capacity abuse (new; adversary skeptic)

Junk or ransomware churn that reaches the homelab becomes keep-forever data, and only a manual admin prune removes it. Proposal for A3/D4: a **per-device committed-bytes cap per day** enforced at ingest, and a **quarantine area** on the homelab where anomalous or over-budget uploads are held before they enter the keep-forever store. Nothing is deleted, which is consistent with "pruning is a manual admin action only". The owner releases or prunes quarantined data. Align the detection latency with D4-S3 (ransomware pause within 5 minutes and < 1 GB uploaded).

#### F4.5 Billing-alert list (C4 deliverable)

| # | Alert | Where | Threshold (proposed) | Latency |
|---|---|---|---|---|
| 1 | Cloudflare budget alert (default) | Billing | $10 usage | Next day |
| 2 | Cloudflare budget alert | Billing | BUD-CLOUD − $5 (e.g. $20) | Next day |
| 3 | Cloudflare budget alert, seed level | Billing | Seed ceiling − $5 (e.g. $45), **left on permanently** (it is harmless outside seeds and saves a manual step) | Next day |
| 4 | App: per-device presigns, declared bytes, overwrite events, decrypt failures | Worker + homelab | U_d, Q_d; any overwrite or decrypt failure suspends that device | Minutes (decrypt failures: pull dwell) |
| 5 | App meter A: estimated spend today and this month (own counters) | Worker | BUD-CLOUD − $5 → owner; "seed mode" (set by the owner) raises it to the seed ceiling automatically | Minutes |
| 6 | App meter B: Cloudflare analytics poll | Cron Worker or homelab | Same thresholds; max(A, B); BUD-CLOUD + BUD-ABUSE → global stop, if OD-14 allows it | Analytics lag (`[SB]`) |
| 7 | Staged backlog GB and oldest-pending age | Homelab + Worker | > 1.34 TB staged, or oldest message > queue retention − 2 days (then reconcile by listing) | Hourly |
| 8 | Payment-method expiry | Owner calendar | 30 days before expiry (C12) | — |
| 9 | Pool fill and disk-purchase trigger | Homelab (C7) | §F6 | Daily |
| 10 | ISP month-to-date vs cap | Homelab puller | §F5 | Daily |
| 11 | **Out-of-band channel** | Homelab, through a provider other than Cloudflare | Mirrors 5–7. It still works if the Cloudflare account is restricted (C12) or down | Minutes |

### F5. Home ISP (Q3). Confidence: High on arithmetic, Low on ISP terms

- **Hairpin:** a home upload uses the uplink and then the homelab pull uses the downlink. Whether both directions count toward a cap depends on the ISP.
- **Throttle:** daily pull allowance = (cap − household baseline − margin) / days left in the cycle; alert 10 fires at 80 % of the cap. Deferring 1 TB in R2 for a month costs $15. The one overage figure found (S36, secondary, low confidence) works out to about $200/TB. **The throttle is cheap only for short backlogs.** For a seed it must be paired with seed admission pacing (§F3), or the seed should go by USB.
- **Restores are uplink-bound:** 1 TB takes 4.63 days at 20 Mbps, 1.85 at 50 Mbps and 0.93 at 100 Mbps. A8 should use this table for the BUD-RESTORE whole-device default.

### F6. Capacity forecast and disk-purchase trigger (Q4). Confidence: High on method; no family data

- Stored(t) = (L0 + g·t)·(1 − dedup)·(1 + o_engine + o_deriv + o_layout) + snapshots + scratch. dedup (A1/F3), o_engine (A6-S2) and o_deriv (A7, OD-16) are **no result**. v0 sets them to 0, which is conservative on dedup and optimistic on overhead.
- **o_layout (new):** Proxmox warns that ZVOLs on RAIDZ carry extra parity and padding: an 8k block on RAIDZ2 writes 16k (C19). If the storage engine's data sits on a VM disk (a ZVOL), a 6-wide RAIDZ2 yields about 50 %, not 67 %, so tier L drops from 80 to about 60 TB. A 4-wide RAIDZ2 and mirrors are already at 50 %. ZFS also reserves slop space (not quantified from a primary source here), and drives are sold in TB while ZFS reports TiB (16 TB = 14.55 TiB). **A6/C5 should put the store on a dataset or bind mount, not a ZVOL**, or carry this overhead.
- **Trigger:** buy when Stored(t + lead + buffer) ≥ h·Usable, with a lead of about 14 days (H5 L21) and a 90-day buffer.

| Tier (C5 prices it) | Usable (dataset) | L0 = 2, g = 0.5 | L0 = 5, g = 1 | L0 = 10, g = 1.5 | L0 = 10, g = 2 |
|---|---|---|---|---|---|
| S: 2 × 16 TB mirror | 16 TB | 21.6 y | 7.8 y | **1.87 y (trigger 2028-04-28)** | **1.4 y (2027-11-10)** |
| M: 4 × 16 TB RAIDZ2 (any 2 drives may fail) | 32 TB | 47 y | 20.6 y | 10.4 y | 7.8 y (2034-04-04) |
| M′: 2 × (2 × 16 TB) mirrors (1 drive per pair may fail) | 32 TB | same as M | | | |
| L: 6 × 20 TB RAIDZ2 | 80 TB (about 60 TB on a ZVOL) | > 100 y | 59 y | 36 y | 27 y |

Years to 80 % fill; trigger dates are from t0 = 2026-09-29 (C4-S1 `capacity.csv`). These are **scenario inputs, not the family's figures** (K12).

- **When tier S fails early:** tier S reaches the trigger within 2 years when L0 ≥ 12.8 − 2.29·g TB: about 10.5 TB at g = 1, 9.4 TB at g = 1.5 and 8.2 TB at g = 2. So tier S only suits families clearly below about 8 TB.
- **Fewer large vs more small drives:** M and M′ have the same usable space but different failure tolerance and resilver behaviour. M′ avoids the RAIDZ ZVOL padding issue. **C5 decides.** No $/TB source was reachable; the H5 estimate ($150–350 per drive) is a placeholder only.

### F7. Homelab running costs (Q5). Confidence: Low

- **Power:** kWh/yr = W × 8.766 (87.7 kWh/yr per 10 W). Wattage (smart plug, `[OL]` via C5) and tariff are owner inputs. EIA was blocked.
- **Drive replacements:** expected failures ≈ n × AFR × years. AFR is **contested** (K13, secondary only): at about 1.4 %, 6 drives over 10 years give about 0.8 failures. Data-centre AFR is a floor for home use. Budget one spare per pool. The primary Drive Stats CSV needs an allowlist change or an owner download.
- **Refresh:** a 5–7 year refresh means one full drive set inside a 10-year horizon.
- **UPS battery, new vs recertified:** no primary data. Left to C5.

### F8. Optional and fixed costs (Q6). Confidence: High (domain Low)

| Item | Cost | Needed when | Source |
|---|---|---|---|
| Workers Paid (production; sandbox during research) | $5/month each | Always | C5 |
| Apple Developer Program | $99/yr | **Only if** OD-01 or OD-09 changes the settled "iOS deferred / no Apple signing" | S25 |
| Azure Artifact Signing Basic | $9.99/month (5,000 signatures) | **Only if** OD-09 buys Windows signing, and the owner is eligible (Public Trust individual in the US or Canada, or an organisation) | K14 |
| Google Play registration | $25 once | OD-10 = closed track | C22 |
| Android limited distribution | $0 | OD-10 = limited (≤ 20 devices) | C22 |
| Domain | about $10–15/yr (E) | Always; also needed for the free alert channel (K15) | I3 (not verified) |
| Email | $0 up to 3,000/month | OD-03 = cloud email | K15 |
| Resend or Postmark fallback (B4 beta policy) | not checked | If Email Service is still beta | C3 |
| Second alert provider (alert 11) | not checked | Recommended | C7 |

Annual fixed cost: about **$70–75** (Workers Paid plus domain). **Conditional on OD-01/OD-09**, about $290–295 with Apple and Azure Basic; plus $25 once for Play.

### F9. Storage governance and fair share (Q7). Proposal for OD-20. Confidence: Medium

Principles: nothing is ever deleted; no keepsake is refused **without an owner decision**; users configure nothing; the owner decides centrally. Precedents (C23): Ente uses admin-set per-member limits with overflow tolerance (borrow this); Immich refuses at a hard quota (avoid this).

1. **Soft per-person budgets** set by the owner. Crossing a budget alerts the owner only and never blocks anything.
2. **Approval categories, uploaded at lowest priority (revised).** These are game captures, dashcam footage, VM or disk images, and single files above an owner-set size. The earlier draft held them on the device until the owner approved, which leaves them unprotected (the same harm that rules out hard quotas). Revised default: they **upload after all core keepsakes** and the owner is alerted. Holding them on the device ("waiting for [owner] to OK this") is used only if the owner chooses it (option A in OD-20) or the pool is red. Policy reaches devices as a **signed policy document** from the control plane: C1 owns the endpoint and D2/D5 the signing key. E4 owns category detection.
3. **Pool states.** Green: below the trigger. **Amber:** the purchase trigger has fired; the owner is alerted and nothing changes for users. **Red** (e.g. 90 % of usable): the homelab stops pulling non-core uploads first, and staging absorbs the backlog. Queue messages expire after 4 days by default and 14 at most (C6), so a red-state backlog is recovered by **reconciliation through ListObjects**, which A3 and G2 must cost and test. **Staging cap** ((BUD-CLOUD − $5)/$0.015 ≈ 1.3 TB at $25): once it is reached, the Worker answers "home storage full, retry later" and devices say "Your backups are waiting because home storage is full. [Owner] has been told." **Refusing at the staging cap needs the owner's OD-20 decision.** Without one, staging keeps growing and the cost alerts fire instead: up to $154.85/month at 10 TB, which the owner can stop by buying disks.
4. **Seasonal bursts:** absorbed by staging (< $1 at a 1-day dwell). The warm cache is suspended automatically above 25 % of the staging cap.

### Alternatives compared

| Option | Fit with settled requirements | Pros | Cons | Evidence |
|---|---|---|---|---|
| **Workers Paid** | Fits | Carries seeds; email; 14-day retention; CPU headroom | $5/month | K7 |
| Workers Free | Fails seeds and ADR-0002 email | $0 | Queue and D1 ceilings | K7 |
| **R2 Standard for staging** | Fits | Free tier; no minimum duration; no retrieval fee | — | K2 |
| R2 IA for staging | Fits, costly | Cheaper per GB-month for ≥ 30 days | $64.70 vs $12.16 per seed month | K8 |
| Presigned PUT + signed If-None-Match | Fits **if enforced** | Direct upload; low Worker load | Enforcement unknown; no conditional on CompleteMultipartUpload | C13a, `[SB]` |
| **Worker-mediated writes (R2 binding, `onlyIf`)** | Fits | No replay; exact metering; size and class controlled | Bytes stream through the Worker; 100 MB body limit (a 5 MiB part fits); more CPU | C13b, C13c |
| R2 temporary credentials per device prefix | Fits | Standard S3 clients; scoped | Replay within TTL; prefix design vs dedup-ID keys | S3 |
| Queue-less commit (Worker commit, homelab polls D1) | Fits (C1 decides) | Removes the Queues line; Free-plan ceiling moves to D1 | Loses push notification of staged objects | K7 |
| Part size 5–80 MiB | All fit | Larger parts → fewer ops | Savings ≤ $5 per 10 TB; memory and resume granularity | K9, I1 |
| Batch metadata records | Fits (A2/A3) | $12.16 → $7.66 per seed month | Protocol shape | C4-S1 |
| Pack small files | **Conflicts** with ADR-0001 | Largest cut in ops | Superseding ADR; not worth it | S32, S33 |
| Hard-limit or prepaid card as spend cap | **Conflicts** with data integrity | Hard stop | Failed preauthorisation can make R2 inaccessible and data deletable | C12 |
| Mirror pairs vs RAIDZ2 | Both fit | See §F6 | See §F6 | C19 |
| New vs recertified drives | Both fit | Cheaper (unverified) | No AFR data | — |

### Similar work and lessons

| Project | What they do | Borrow or avoid | Source |
|---|---|---|---|
| rclone S3/R2 | 200 MiB single-PUT cutoff; 5 MiB chunks; chunk size grows to stay within 10,000 parts | Borrow the growth rule | S28 |
| restic / kopia | Pack blobs into larger objects | Avoid for staging; relevant to A6 | S32, S33 |
| Ente family plans | Admin-set member limits; overflow tolerance | Borrow | S29, S30 |
| Immich | Hard per-user quota | Avoid | S31 |
| Ente / B2 prices | About $12 and $6.95 per TB-month (secondary snippets) | Sanity check only | S37, S38 |

### Tools and libraries

| Name | Purpose | Licence | Maturity | Source |
|---|---|---|---|---|
| `spikes/C4-S1/c4_model.py` | The v0 model, simulator, sensitivity, abuse grid, capacity | Repo | Throwaway research code, 2026-09-29 | I4 |
| Cloudflare GraphQL Analytics (`r2OperationsAdaptiveGroups`) | Spend meter B; checking the model against the sandbox bill | Vendor API | Documented | S39 |
| Smart plug with energy metering | Platform wattage | — | — | C5 `[OL]` |

## Spikes

| Spike | Hypothesis | Pass → / fail → (decision) | Exec tag | Budget IDs | Data class | Status | Result |
|---|---|---|---|---|---|---|---|
| C4-S1 Model v0, then v1 with A0 numbers | The steady-state bill is known within ±25 %; worst-case abuse is bounded below BUD-ABUSE; the disk-purchase trigger date is computed | Pass → set BUD-CLOUD, BUD-ABUSE (OD-14) and the alert list. Fail → rerun as v1 with A0, E1, H2 and C2 `[SB]` numbers | CT | BUD-CLOUD, BUD-ABUSE (both unset; tested against the proposed $25 / $50) | `SYN → results` | **Ran 2026-09-29; inconclusive** | (1) **±25 %:** met only at g ≤ 0.5 TB/yr (21 %). At g = 1 it is 30–36 % and at g = 2 it is 48–72 %. The maximum anywhere is $11.16, under $25. Pinning CPU per request cuts g = 1 to 10 %; g = 2 needs CPU and mean file size. (2) **Abuse:** unbounded without app controls. With them, 131 of 243 cap sets stay under $50 (k = 3: $5.10 at E = 1); with all devices compromised, 21 of 81. The unauthenticated flood is not bounded by device caps. Four billing behaviours need `[SB]`. (3) **Trigger:** computed for scenarios (tier S 2028-04-28 at L0 = 10, g = 1.5); the family date waits on H2/E1. All 7 self-checks reproduce the vendors' worked examples. Evidence: `spikes/C4-S1/README.md`, `spikes/C4-S1/out/*.csv`, `spikes/C4-S1/evidence/run_output.txt` |

No emulator was used. Miniflare cannot answer billing questions, so the four `[SB]` items go to C2's sandbox kit (H5 L01). No C4 kit is needed in this wave.

**Reframed decision test (logic skeptic).** OD-14 does not need ±25 % precision. It needs the bill to stay below BUD-CLOUD over the plausible ranges. That property **holds** for the uncapped steady state (maximum $11.16 against $25). It **does not hold** for an unpaced seed from a capped home (§F3). The ±25 % criterion stays as the v1 target once A0 reports.

## Conflicts with settled text

None of the recommendations contradicts CLAUDE.md, ADR-0001 or ADR-0002. The skeptics found these tensions, which are resolved here or raised as decisions:

1. **Append-only (CLAUDE.md).** The earlier draft offered "short expiry **or** If-None-Match", and expiry alone would let a credential holder overwrite a staged object. **Fixed:** create-only is mandatory (§F4.3). Open: R2's CompleteMultipartUpload has no conditional headers, so create-only for multipart objects needs a C2/D3/A3 design.
2. **Intermittent connectivity and ADR-0001's batch presign.** A 60 s expiry would conflict with both. **Dropped:** expiry stays at 15 minutes (BUD-REVOKE).
3. **Data integrity over everything.** The red state's staging-cap refusal, and withholding approval categories, both leave keepsakes unprotected. **Changed:** neither happens by default. Both are owner choices in OD-20.
4. **"Auto-discovery proposes what to protect."** Approval categories now upload at lowest priority rather than being withheld. OD-20 asks the owner whether withholding is acceptable.
5. **A global presign stop** would weaken the settled goals of tolerating intermittent connectivity and flagging problems plainly, by turning one stolen credential into a family-wide outage. It is per-device first, and the global stop is an OD-14 sub-decision.
6. **"No Apple or Windows code signing for now; iOS deferred."** The Apple and Azure lines are conditional on OD-01/OD-09 and are not in the base fixed cost.
7. Packing small files would conflict with ADR-0001 §4. It is not recommended.

## Open questions

| # | Question | Owner | By |
|---|---|---|---|
| 1 | Does R2 bill 403 (bad signature or expired URL), 412 (If-None-Match) and 429 (same-key limit) responses? | C2 `[SB]` | Wave 2 |
| 2 | Does R2 enforce a signed `If-None-Match: *`, `Content-MD5`/`Content-Length` and `x-amz-storage-class` on presigned PutObject and UploadPart? Can the binding's `onlyIf` express create-only? How is create-only achieved for multipart objects? | C2/D3 `[SB]`, A3 | Wave 2 |
| 3 | Are WAF-blocked Worker requests billed? | C2 `[SB]` | Wave 2 |
| 4 | Are incomplete multipart parts billed as storage until abort? | C2 `[SB]` | Wave 2 |
| 5 | Does revoking the signing R2 key invalidate outstanding presigned URLs, and how fast? Is expiry checked at request start or at completion? | C2 `[SB]` | Wave 2 |
| 6 | What is the lag of GraphQL analytics for R2 operations and Worker invocations? | C2 `[SB]` | Wave 2 |
| 7 | Measured operations per file and **CPU per request** (the largest sensitivity) | A0 | v1 |
| 8 | Mean file size, share of bytes in large files, growth per person | E1, H2 F4 | v1 |
| 9 | Engine, derivative and layout overhead (dataset vs ZVOL); dedup ratio | A6-S2, A7, C5, A1/F3 | Gate A |
| 10 | Disk $/TB, wattage, tariff, UPS interval, primary Drive Stats | C5 + owner; H1 allowlist | Gate C |
| 11 | The owner's ISP cap and speeds | H2 D1–D2 | Wave 0 |
| 12 | Workers Logs / Observability pricing after 2026-12-01 | C4 re-check | 2026-12 |
| 13 | Resend/Postmark fallback pricing; second alert provider | C3, C7 | Gate C |

## Recommendation

1. **Workers Paid and R2 Standard. Never use IA for staging** (K7, K8).
2. **BUD-CLOUD $25/month and a $50 seed-month ceiling.** Support: the C4-S1 full-factorial maximum is $11.16 at steady state, and an uncapped 2 TB seed month is $12–18 (with K2 prices). Usage alerts at $10, $20 and $45, left on permanently, because the alerts exclude the $5 fee (K1). **Caveat:** the seed ceiling holds only if seed admission is paced to the homelab's pull allowance when the home ISP is capped. Otherwise large seeds go by USB.
3. **BUD-ABUSE $50, provisional.** It is achievable only with the §F4.3 controls (mandatory create-only, per-device caps with signed size, decrypt-failure and overwrite detectors, two spend meters, per-device-first suspension, a key-rotation kill switch, public-endpoint hygiene) **and** only if the C2 `[SB]` results show that 403/412/429 responses are unbilled and that the signed conditions are enforced. The bound assumes k = 3 compromised devices ($5.19). With all 25 compromised it is $43.25, and only because the staged-byte cap is 100 GB. A month of undetected, cap-compliant abuse across all devices would reach $150, so the meters must carry the bound. Cloudflare will not cap spend (K1).
4. **Warm cache ≤ 30 days**, suspended automatically during seeds and above 25 % of the staging cap (K10).
5. **Part size on non-cost grounds** (B6). Batch metadata records if A2/A3 allow (K9).
6. **C5 should price the 32 TB tier (M or M′) as the reference case.** Tier S suits only libraries clearly below about 8 TB. C5 chooses between RAIDZ2 and mirror pairs, and the store should sit on a dataset, not a ZVOL (K12, C19).
7. **Adopt the revised §F9 proposal** for OD-20.
8. **Add an ingest-side per-device cap and quarantine** (§F4.4) to A3/D4.

What would change this: A0 measuring more than about 5 R2 objects per file, or CPU well above 5 ms per request; E1 finding a mean file size below 2 MB; the `[SB]` checks showing that 403/412/429 are billed or that signed conditions are not enforced (then Worker-mediated writes become necessary, not optional); an owner ISP cap below family inflow (then the default seed route becomes USB).

## Decision requests

### OD-14: Cost ceilings, abuse controls and beta-feature policy
- **Needed by:** Wave 0 / H2 intake (overdue in the queue)
- **Evidence:** this note §Model, §F3, §F4; `spikes/C4-S1/`; `owner-intake.md` B1–B4
- **Options:**
  | Option | What it means for the family | Cost (money and owner time) | Reversibility | Risks |
  |---|---|---|---|---|
  | A. $25 steady / $50 seed / $50 abuse, with the §F4.3 controls; provisional on the C2 `[SB]` results | Nothing visible; a stolen device is suspended on its own | $5–8/month modelled; C2 build effort | Easy | The bound depends on four unverified billing behaviours; a capped seed must be paced or go by USB |
  | B. $15 steady / $30 seed / $20 abuse | Seeds go slower or mostly by USB | Lower ceiling; more USB work | Easy | Little headroom for outage backlogs; $20 abuse needs tighter caps that could throttle a real seed |
  | C. No abuse cap; rely on Cloudflare alerts | Nothing visible | $0 build | Easy | Alerts are a day late and never cap; about $645/day is possible |
- **Sub-decisions:** (i) May the account-wide meter stop **all** presigning at BUD-CLOUD + BUD-ABUSE (a family-wide outage), or only alert? Recommend: allow it, only after per-device suspension has failed. (ii) **Beta-feature policy:** adopt owner-intake B4 ("only with a documented, tested fallback that needs no client update"). Note that the free alert channel and signup mail depend on Email Service, and that the Workers Logs pricing changes on 2026-12-01.
- **Recommendation:** A with both sub-decisions as stated. The value of k (3 vs 25) is an assumption the owner should see (§F4.3 table).
- **Touches settled text:** no. The create-only control implements the settled append-only property.
- **If no decision by the deadline:** A is assumed *provisionally*. C2 designs against $50 with global stop allowed.

### OD-20: Per-person storage budgets and approval categories
- **Needed by:** Wave 2
- **Evidence:** this note §F9; precedents C23
- **Options:**
  | Option | What it means for the family | Cost | Reversibility | Risks |
  |---|---|---|---|---|
  | A′. Soft budgets + approval categories **uploaded at lowest priority** + pool states; refusing at the staging cap only with this approval | Everything is protected eventually; big odd files go last | Occasional owner review (fits BUD-SUPPORT) | Easy | Pool fills faster than with A; category detection errors (E4) |
  | A. As A′, but approval categories **held on the device** until the owner says yes | Big odd files wait, unprotected | More owner workload | Easy | Unprotected files; tension with "auto-discovery proposes" |
  | B. No budgets; everything is uploaded; amber alerts only; no refusal | Simplest | Staging cost can grow if the pool fills | Easy | Pool fills early; up to $154.85/month at 10 TB staged |
  | C. Hard per-person quotas (Immich-style) | Uploads refused at the quota | Low | Easy | Unprotected keepsakes; users see configuration-like messages |
- **Recommendation:** A′.
- **Touches settled text:** A touches "auto-discovery proposes what to protect" and "data integrity over everything". A′ and B do not. Keep-forever is untouched by all of them.
- **If no decision by the deadline:** B. Nothing is refused or withheld; the cost and pool alerts fire instead.

## Hand-offs

| To | What | Why |
|---|---|---|
| C2 / D3 | §F4.3 controls; Open questions 1–6 as `[SB]` items; multipart create-only design; Worker-mediated vs presigned comparison | BUD-ABUSE is unenforceable otherwise; append-only |
| C1 | Warm-cache policy (C-01); seed admission paced to the pull allowance; cron meter B; avoid always-on DOs; policy-document endpoint; queue-less design option; staging-cap "retry later" code | Largest variable cost line; capped seeds |
| A0 | Measure the §Model A parameters, **CPU per request first** | Turns v0 into v1; ±25 % |
| A2 / A3 | Batch metadata records; size check before GET; decrypt-failure detector; red-state reconciliation by listing; ingest cap and quarantine | Cost, abuse, capacity |
| D4 | Ingest quarantine and T aligned with D4-S3 | Capacity abuse |
| D2 / D5 | Policy-document signing key | §F9 |
| B6 | Part size is not a cost lever (valid T1 sizes) | K9 |
| A6 / C5 | Tiers S/M/M′/L, the L0 threshold for tier S, dataset vs ZVOL, slop; supply $/TB, wattage, UPS; primary AFR | ADR-0030 |
| C7 | Alerts 7, 9, 10 and the out-of-band channel 11 | Monitoring |
| C3 | The free alert channel needs Email Routing on a zone; fallback pricing | K15 |
| A8 | Restore-time table (§F5) | BUD-RESTORE |
| A4 / A9 / E5 | Capped homes seed by USB; cloud cost is neutral | §F3 |
| E1 | Mean file size, bytes in large files, growth | Model inputs |
| H1 | Blocked sources (backblaze.com, xfinity.com, eia.gov, diskprices.com, azure.microsoft.com pricing, ente.com); budget sheet: record the corrected B1/B2 figures; model expiry 2026-12-01 (Workers Logs) | PLAN §5.4 |
