# C4. Cost, capacity and storage-budget model (v0)

- **Workstream:** C4 (see `docs/research/PLAN.md`, section "C4.")
- **Status:** Draft (analyst deep read, Wave 1 batch W1-c). Skeptic review has not run yet.
- **Date:** 2026-09-29 (last updated 2026-09-29)
- **Feeds:** OD-14 (BUD-CLOUD, BUD-ABUSE, billing alerts), OD-20 (per-person budgets and approval categories), ADR-0030 (C5 BOM: cost and capacity inputs), ADR-0010 (C1: warm cache, meters), ADR-0014 (D3 + C2: abuse limits), ADR-0021 (B6: part-size policy)
- **Depends on:** T2 (`fact-check-adr-0001-0002.md`), T1 spike 2 (`content-encryption-format.md`, part size), H2 (`owner-intake.md` B1–B3, C4, D1–D2, F4), H5 (`h5-long-lead-items.md` fee and lead-time lines). **Still missing:** A0 (measured operations per file), E1 (growth per person), A6 (storage-engine overhead), C5 (BOM prices), H2 answers.
- **Traceability rows closed or advanced:** R-09 (scale), R-26 (keep forever: capacity forecast), R-31 (storage-issue nudges: pool-full behaviour), C-01 (warm-cache orphan: cost side only)

## Summary

The steady-state cloud bill is **about $5–7 per month**, and $5 of that is the fixed Workers Paid fee. Usage charges stay inside the free allowances unless staged objects are kept in R2 as a warm cache. A seed month that pushes 2 TB through R2 costs **about $11–17**, or **about $40** if a 30-day warm cache is left on during the seed. Every figure is below the owner-intake defaults ($25 steady, $50 seed). The number that is **not** bounded today is abuse spend. Cloudflare budget alerts are informational, arrive a day late and never cap anything. A stolen device credential that makes small PUTs at 1,000/s spends $50 in under 2 hours. A presigned URL can be replayed until it expires, which multiplies the per-URL cost by up to its expiry in seconds. Reliquary therefore needs its own meters and auto-suspend in the Worker. With those, the worst case can be held under a $50 BUD-ABUSE. For the homelab, capacity rather than money is the risk: a 2-disk 16 TB mirror holding 10 TB reaches 80 % full in about 2 years at 1.5 TB/year growth. The model is v0. Operation counts are assumptions until A0 measures them. Growth is a scenario range until the E1 census. Disk prices and power are owner inputs, because no primary price source could be reached.

## Questions

| # | Question (PLAN C4) | Short answer | Confidence |
|---|---|---|---|
| 1 | Line items: Workers Paid, requests, CPU, D1, DOs, Queues, R2 storage and Class A/B, email | All unit prices come from primary sources (§Findings F1). At family scale the only non-zero lines are the $5 base, R2 Class A in seed months, staged storage, and Queues in seed months. The rest sit inside the included usage. | High on prices; Medium on volumes (A0 pending) |
| 2 | Seed scenarios: 10 TB via R2 with 8/16/64 MiB parts, mostly USB, or legacy import; peak staging for a drain rate | 10 TB via R2 costs about $55 over 5 months (about $30 above the base fee). Part size changes the bill by less than $1 per 2 TB month, because per-file operations dominate. Peak staging depends on homelab downtime and the warm-cache window, not on drain rate, whenever the home downlink exceeds family upload (§F3). Cloud cost does not choose between R2, USB and legacy import. ISP caps, time and owner effort do. | Medium |
| 3 | Home ISP: caps, hairpin, restore over uplink, puller throttle schedule | A byte uploaded from home crosses the home link twice, once up and once down on the pull. Holding 1 TB in R2 for a month costs $15. Overage on one ISP's legacy capped plan costs about $200/TB (secondary source, low confidence). So throttling the puller to fit a cap is cheap. Restores are limited by the home uplink: 1 TB takes 4.6 days at 20 Mbps (§F5). | High on arithmetic; Low on ISP terms |
| 4 | Growth per person, dedup ratio, redundancy overhead, headroom, disk-purchase trigger | Formula and three hardware tiers are in §F6. Growth and dedup are **no result** until E1 and A1/F3. The trigger fires when the projected fill reaches the headroom target within lead time plus a buffer. | High on formula; no data yet |
| 5 | Homelab running costs: power, UPS, drive replacements, refresh | Formulas only (§F7). The Backblaze failure rates are secondary (1.2–1.6 % AFR from search snippets). Power, $/TB and UPS battery life are owner inputs. No primary price source was reachable. | Low (inputs missing) |
| 6 | Optional costs | Apple $99/yr; Azure Artifact Signing Basic $9.99/month (5,000 signatures); Android: $25 (Play, or ADC full distribution) or $0 (ADC limited distribution, ≤ 20 devices); domain about $10–15/yr (estimate); email $0 inside 3,000/month (§F8). | High (domain: Low) |
| 7 | Storage governance: soft budgets, approval categories, pool-full behaviour, seasonal bursts | Proposal in §F9 (for OD-20): soft per-person budgets that alert the owner and never refuse or delete; a short list of approval-gated categories, held on the device as "waiting for approval"; a green/amber/red pool state that backs up into a capped R2 staging area and then pauses presigning. | Medium (design proposal) |
| 8 | Alternatives: Workers Paid vs Free; R2 Standard vs IA for staging; part sizes; fewer large vs more small drives; new vs recertified | Paid (Free cannot run a seed); Standard (IA costs about 10× more for staging); part size is not a cost lever, so B6 should choose it on other grounds; drive count and recertified drives are C5 decisions and lack price data here (§Alternatives). | High / High / Medium / Low |
| 9 | **New:** does any Cloudflare mechanism cap spend? | **No.** Budget alerts and usage notifications are informational only, and alerts are processed daily. Threshold billing only invoices early. The application must cap itself (§F4). | High |
| 10 | **New:** which abuse costs are not bounded by per-device limits? | Unauthenticated floods against the Worker, which are billed per request. Also possibly bad-signature (403) requests against R2, since only 401 is documented as free. Both need `[SB]` checks (§F4). | Medium |

## Method

- **Sweep:** two scouts (vendor docs and pricing; source code and similar work), then this analyst pass. The analyst re-fetched and read in full: R2 pricing, limits, presigned URLs, lifecycles, event notifications and the S3 compatibility table; Workers pricing and limits; the D1, Queues, Workers Logs and Durable Objects pricing partials; the DO SQLite-billing changelog; Email Service pricing; budget alerts, the 2026-07-20 budget-alert changelog, threshold billing and billing policy; WAF rate-limiting availability; the Workers rate-limit binding; Azure Artifact Signing SKU; the Android developer-verification FAQ; Proxmox `local-zfs.adoc`; and the rclone, Ente and Immich code lines cited below.
- **Model:** a small Python calculation, run in the scratchpad (not committed). The formulas are written out in §Model so anyone can re-run them. The C4-S1 spike runner owns the committed script or CSV.
- **Routes used:** `cloudflare/cloudflare-docs @ production` on raw.githubusercontent.com (primary mirror); `MicrosoftDocs/azure-docs @ main`; `proxmox/pve-docs @ master`; developer.android.com direct; GitHub raw for rclone, Ente and Immich.
- **Blocked sources (report to H1):** developers.cloudflare.com (mirror used); azure.microsoft.com pricing page (docs mirror used); backblaze.com and ir.backblaze.com (Drive Stats: **secondary only**); xfinity.com (**secondary only**); eia.gov (electricity price: **no source**); diskprices.com and pcpartpicker.com ($/TB: **no source**); ente.com pricing (**secondary only**); support.google.com / play.google.com (Play fee: covered indirectly by the developer.android.com FAQ). Context7 returned "monthly quota exceeded". The WebSearch budget for this session was exhausted before the analyst pass, so no new searches ran.
- **Stop rule:** every Cloudflare line item has a primary source. The remaining gaps (disk $/TB, power price, AFR raw data, ISP terms) need an allowlist change or owner input. More sweeping from here would not close them.
- **Units:** R2 prices are per GB. The R2 limits page defines GB as 10^9 bytes (distinct from GiB), and the model uses that. The pricing page itself does not define GB. If Cloudflare meant GiB, storage figures shift by at most 7.4 %.

## Sources

| # | Source | Publisher | Version date | Accessed | Primary? |
|---|---|---|---|---|---|
| S1 | R2 Pricing: `cloudflare/cloudflare-docs @ production : src/content/docs/r2/pricing.mdx` (renders at developers.cloudflare.com/r2/pricing/) | Cloudflare | production branch | 2026-09-29 | Yes |
| S2 | R2 Limits: `… : docs/r2/platform/limits.mdx` | Cloudflare | production | 2026-09-29 | Yes |
| S3 | R2 Presigned URLs: `… : docs/r2/api/s3/presigned-urls.mdx` | Cloudflare | production | 2026-09-29 | Yes |
| S4 | R2 Object lifecycles: `… : docs/r2/buckets/object-lifecycles.mdx` | Cloudflare | production | 2026-09-29 | Yes |
| S5 | R2 Event notifications: `… : docs/r2/buckets/event-notifications.mdx` | Cloudflare | production | 2026-09-29 | Yes |
| S6 | R2 S3 API compatibility: `… : docs/r2/api/s3/api.mdx` | Cloudflare | production | 2026-09-29 | Yes |
| S7 | Workers Pricing: `… : docs/workers/platform/pricing.mdx` | Cloudflare | production | 2026-09-29 | Yes |
| S8 | Workers Limits: `… : docs/workers/platform/limits.mdx` | Cloudflare | production | 2026-09-29 | Yes |
| S9 | Workers Logs pricing partial: `… : partials/workers/workers_logs_pricing.mdx` | Cloudflare | production | 2026-09-29 | Yes |
| S10 | D1 pricing partial: `… : partials/workers/d1-pricing.mdx` | Cloudflare | production | 2026-09-29 | Yes |
| S11 | D1 Limits: `… : docs/d1/platform/limits.mdx` | Cloudflare | production | 2026-09-29 | Yes |
| S12 | Queues pricing partial: `… : partials/workers/queues_pricing.mdx` | Cloudflare | production | 2026-09-29 | Yes |
| S13 | Queues Limits: `… : docs/queues/platform/limits.mdx` | Cloudflare | production | 2026-09-29 | Yes |
| S14 | Durable Objects pricing partial: `… : partials/durable-objects/durable-objects-pricing.mdx` | Cloudflare | production | 2026-09-29 | Yes |
| S15 | Changelog "Billing for SQLite Storage": `… : changelog/durable-objects/2025-12-12-durable-objects-sqlite-storage-billing.mdx` | Cloudflare | 2025-12-12 | 2026-09-29 | Yes |
| S16 | Email Service Pricing: `… : docs/email-service/platform/pricing.mdx` | Cloudflare | production | 2026-09-29 | Yes |
| S17 | Budget alerts: `… : docs/billing/manage/budget-alerts.mdx` | Cloudflare | production | 2026-09-29 | Yes |
| S18 | Changelog "Budget alerts now on by default for Pay-as-you-go accounts": `… : changelog/billing/2026-06-15-budget-alerts-default-on.mdx` | Cloudflare | 2026-07-20 (frontmatter) | 2026-09-29 | Yes |
| S19 | Threshold billing: `… : docs/billing/threshold-billing.mdx` | Cloudflare | production | 2026-09-29 | Yes |
| S20 | Billing policy: `… : docs/billing/understand/billing-policy.mdx` | Cloudflare | production | 2026-09-29 | Yes |
| S21 | WAF rate limiting availability by plan: `… : partials/waf/rate-limiting-availability-by-plan.mdx` | Cloudflare | production | 2026-09-29 | Yes |
| S22 | Workers Rate Limiting binding: `… : docs/workers/runtime-apis/bindings/rate-limit.mdx` | Cloudflare | production | 2026-09-29 | Yes |
| S23 | Change an Artifact Signing account SKU: `MicrosoftDocs/azure-docs @ main : articles/artifact-signing/how-to-change-sku.md` | Microsoft | ms.date 2026-01-06 | 2026-09-29 | Yes |
| S24 | Artifact Signing quickstart (individual eligibility: US/Canada): `… : articles/artifact-signing/quickstart.md` | Microsoft | main | 2026-09-29 (scout) | Yes |
| S25 | Apple Developer Program, https://developer.apple.com/programs/ | Apple | undated | 2026-09-29 (scout; also H5 L07 "V") | Yes |
| S26 | Android developer verification FAQ, https://developer.android.com/developer-verification/guides/faq | Google | entries updated 2026-03-25 and 2026-06-18 | 2026-09-29 | Yes |
| S27 | Proxmox VE ZFS: `proxmox/pve-docs @ master : local-zfs.adoc` | Proxmox | master | 2026-09-29 | Yes |
| S28 | rclone `backend/s3/s3.go` (lines 975–977) and `fs/chunksize/chunksize.go` | rclone | master | 2026-09-29 | Yes (code) |
| S29 | Ente `server/pkg/controller/usage.go` (l. 33, 54–98) and `file.go` (l. 65) | Ente | main | 2026-09-29 | Yes (code) |
| S30 | Ente help "Family plans": `ente-io/ente @ main : docs/docs/photos/features/account/family-plans.md` | Ente | main | 2026-09-29 (scout) | Yes |
| S31 | Immich `server/src/services/asset-media.service.ts` `requireQuota` (l. 368–372) | Immich | main | 2026-09-29 | Yes (code) |
| S32 | restic `internal/repository/repository.go` (pack sizes) | restic | master | 2026-09-29 (scout) | Yes (code) |
| S33 | kopia `repo/format/content_format.go` (MaxPackSize) | kopia | master | 2026-09-29 (scout) | Yes (code) |
| S34 | Backblaze Drive Stats for Q1 2026, https://www.backblaze.com/blog/backblaze-drive-stats-for-q1-2026/ | Backblaze | 2026 | 2026-09-29 (**search snippet only**) | No (primary blocked) |
| S35 | Backblaze IR: 2025 Drive Stats report press release | Backblaze | 2026 | 2026-09-29 (**search snippet only**) | No (primary blocked) |
| S36 | Xfinity data-usage plan FAQ, https://www.xfinity.com/support/articles/data-usage-plan | Comcast | undated | 2026-09-29 (**search snippet only**) | No |
| S37 | Backblaze B2 pricing (via secondary sites' snippets) | Backblaze | unknown | 2026-09-29 (**snippet only**) | No |
| S38 | Ente pricing via saasworthy.com aggregator | third party | "September 2026" | 2026-09-29 (**snippet only**) | No |
| I1 | `docs/research/content-encryption-format.md` (T1 spike 2): default part P = 5,244,160 B; single PUT for files of at most one part | Reliquary | 2026-09-29 | 2026-09-29 | Internal |
| I2 | `docs/research/owner-intake.md` §B (proposed BUD-CLOUD $25, seed $50, BUD-ABUSE $50) | Reliquary | 2026-09-29 | 2026-09-29 | Internal |
| I3 | `docs/research/h5-long-lead-items.md` (L02 domain E $10–15/yr; L21 drive E $150–350; L31 postage E) | Reliquary | 2026-09-29 | 2026-09-29 | Internal (estimates marked E) |

## Claims

Skeptic columns are empty until the skeptic stage runs. "Derived" means arithmetic on primary numbers, and each derivation is shown in §Model.

| # | Claim | Sources | Key? | Skeptic 1 | Skeptic 2 | Skeptic 3 | Verdict |
|---|---|---|---|---|---|---|---|
| C1 | R2 Standard: $0.015/GB-month, Class A $4.50/M, Class B $0.36/M, no retrieval fee, free egress. IA: $0.01/GB-month, Class A $9.00/M, Class B $0.90/M, retrieval $0.01/GB, 30-day minimum. | S1 | Yes | | | | Pending |
| C2 | R2 free tier per month: 10 GB-month, 1M Class A, 10M Class B, **Standard only**. Usage is rounded **up** to the next billing unit (1,000,001 ops → 2M). | S1 | Yes | | | | Pending |
| C3 | R2 GB-month is the average of each day's **peak** storage over 30 days. | S1 | Yes | | | | Pending |
| C4 | PutObject, CreateMultipartUpload, UploadPart, CompleteMultipartUpload, ListParts, ListMultipartUploads, ListObjects, CopyObject and lifecycle tier transitions are Class A. GetObject and HeadObject are Class B. DeleteObject and AbortMultipartUpload are free. Operations that return **401** are not billed. Nothing is documented for 403, 412 or 429. | S1 | Yes | | | | Pending |
| C5 | Workers Paid: $5/month minimum; 10M requests then $0.30/M; 30M CPU-ms then $0.02/M; no duration charge; subrequests and Service Binding calls add no request fee. Free: 100,000 requests/day, 10 ms CPU. | S7, S8 | Yes | | | | Pending |
| C6 | D1 on Paid: 25B rows read, 50M rows written and 5 GB included per month, then $0.001/M read, $1.00/M written, $0.75/GB-month. Each indexed column adds a written row. Free: 5M read/day, 100k written/day. | S10 | Yes | | | | Pending |
| C7 | Queues on Paid: 1M operations/month included, then $0.40/M. One operation per 64 KB written, read or deleted. About 3 operations per message. Retries add reads. Free: 10,000 ops/day, 24 h retention. Paid retention: 4 days default, up to 14. | S12, S13 | Yes | | | | Pending |
| C8 | R2 event notifications for `object-create` (PutObject, CopyObject, CompleteMultipartUpload) are delivered as Queue messages, so they incur Queues operations. | S5, S12 | Yes | | | | Pending |
| C9 | Durable Objects on Paid: 1M requests then $0.15/M; 400,000 GB-s then $12.50/M GB-s, billed at 128 MB per object and rounded up to 1M GB-s; SQLite storage 5 GB-month then $0.20/GB-month, billable from a target date of 2026-01-07. | S14, S15 | No | | | | Pending |
| C10 | Email Service sending to arbitrary recipients needs Workers Paid: 3,000/month included, then $0.35 per 1,000. Sends to verified destination addresses are free on every plan. | S16 | Yes | | | | Pending |
| C11 | Cloudflare budget alerts are account-wide, informational only, and never pause or cap usage. Usage is processed once a day, so an alert fires the day after its threshold is crossed. Subscription fees (the $5 Workers Paid fee) are excluded. Eligible Pay-as-you-go accounts get a default $10 alert. | S17, S18 | **Yes** | | | | Pending |
| C12 | Threshold billing raises one mid-cycle invoice at a threshold Cloudflare sets and the customer cannot change. If preauthorisation of the payment method fails, R2 buckets become inaccessible, and the data may be deleted if the payment method is not fixed within 30 days. | S19, S20 | Yes | | | | Pending |
| C13 | A presigned URL is valid for 1 s to 7 days and can be reused until it expires. Signed headers such as Content-Type are enforced (a mismatch returns 403). Writes to one key are limited to 1 per second (HTTP 429 above that). R2 PutObject supports If-None-Match. | S2, S3, S6 | **Yes** | | | | Pending |
| C14 | **Derived.** A small-object abuse stream costs about $8 per million junk objects: Class A $4.50, Queues 3 ops $1.20, Worker request $0.30, and about 2 D1 rows once past the 50M included ($2.00). At 1,000 objects/s that is about $690/day, which exhausts $50 in about 1.7 h. | C4–C8, §Model | **Yes** | | | | Pending |
| C15 | **Derived.** Replaying a presigned PUT against its own key can create up to one billed write per second until expiry, so one URL with a 900 s expiry can cause up to 900 Class A operations. At 25,000 URLs/day that is about $101/day, compared with $6.75/day at a 60 s expiry. | C1, C13 | **Yes** | | | | Pending |
| C16 | **Derived.** Steady state is $5.00–7.36/month for 0.5–2 TB/year of family growth, with or without a 30-day warm cache. A 2 TB seed month costs $11.16 (1-day dwell), $13.96 (14-day homelab outage) or $40.15 (30-day warm cache), at 250k files/TB and 2 R2 objects per file. | C1–C8, §Model | **Yes** | | | | Pending |
| C17 | **Derived.** Across 8, 16 and 64 MiB part sizes, part operations for 10 TB cost $5.36, $2.68 and $0.67. At the T1 default of about 5.0 MiB they cost $8.58. Per-file operations dominate at a 4 MB mean file size. | C1, I1 | Yes | | | | Pending |
| C18 | Workers Free cannot carry a seed: Queues allows 10,000 ops/day, about 1,667 files/day at 6 ops per file; D1 allows 100,000 rows written/day; the CPU limit is 10 ms per invocation; there is no email to arbitrary recipients. | C5–C7, C10 | Yes | | | | Pending |
| C19 | Proxmox docs: mirror vdevs give 50 % usable; RAIDZ-P over N disks gives about N−P disks; ZFS needs at least 8 GB RAM, and ECC is recommended; ARC rule of thumb is 2 GiB plus 1 GiB per TiB of storage. | S27 | Yes | | | | Pending |
| C20 | Backblaze AFR: 1.24 % (Q1 2026 quarter), 1.36 % (2025 annual), 1.30 % or 1.39 % lifetime (the snippets conflict). | S34, S35 | No | | | | **Secondary only** |
| C21 | Azure Artifact Signing Basic costs $9.99/month with 5,000 signatures; Premium $99.99/month with 100,000; $0.005 per signature above quota. Individuals must be in the US or Canada. | S23, S24 | Yes (OD-09) | | | | Pending |
| C22 | Android: $25 for a full-distribution Android Developer Console account, "similar to Play's $25 registration fee"; waived for limited distribution (≤ 20 devices). | S26, T2 item 7 | Yes (OD-10) | | | | Pending |
| C23 | Precedents: Ente allows 50 MiB of overflow above a quota, uses a cached "can upload" answer below 100 MiB, and supports admin-set per-member limits in a family pool. Immich refuses uploads beyond a hard per-user quota. | S29, S30, S31 | No | | | | Pending |

## Model

### Parameters

Values marked **P** are primary prices. **A** marks an assumption to be replaced by the named workstream. **O** marks an owner input.

| Parameter | Symbol | v0 value | Status |
|---|---|---|---|
| Mean file size | s̄ | 4 MB (so 250k files/TB); sensitivity 2 MB and 8 MB | **A**, the owner-intake figure (500k files per 2 TB); E1, A0 |
| R2 objects per file (content + metadata record) | 1 + m | 2 (m = 1, one metadata object per file); m ≈ 0 if records are batched | **A**, A2/A3 |
| Share of bytes in multipart files | b_mp | 0.6 | **A**, E1/A5 |
| Share of files that are multipart | f_mp | 0.01 | **A** |
| Part size | P | 5,244,160 B (T1 default, I1) | B6 |
| Queue messages per file | q | 2 (one `object-create` per object) | **A**, C1 |
| Worker requests per file | r | 3 (amortised dedup check, presign, commit) | **A**, A0 |
| CPU per request | c | 5 ms (BUD-CPU-REQ allows < 1 ms for auth) | **A**, D3-S1 |
| D1 rows written per new file | w | 6 (claim + index, state change + index, metadata row) | **A**, A0/C1 |
| Class B per file (homelab GET/HEAD) | b | 2 | **A**, A0 |
| Staging dwell (upload → commit → delete) | d | 1 day nominal | **A**, A3/C1 |
| Warm-cache window | W | 0 or 30 days (ADR-0001 §6, "optional") | C1 (traceability C-01) |
| Library size, growth | L0, g | 2–10 TB; 0.5–2 TB/yr (scenario range only) | **O** (H2 F4), E1 |
| Fill target | h | 80 % of usable | **O**, C5 (a common rule of thumb; no primary source was read) |

### Formulas (per calendar month)

- Class A = N·(1 + m) + B·b_mp / P + 2·N·f_mp. Cost = $4.50 × (⌈Class A / 1M⌉ − 1)⁺.
- Staged GB-month = mean of daily peak staged GB. With inflow I GB/month and dwell d: ≈ I·(d + W)/30. Cost = $0.015 × (⌈GB-month⌉ − 10)⁺.
- Queues = $0.40 × (⌈3·q·N / 1M⌉ − 1)⁺. Workers = $0.30 × (⌈r·N / 1M⌉ − 10)⁺ + $0.02 × (⌈r·N·c / 1M⌉ − 30)⁺. D1 = $1.00 × (⌈w·N / 1M⌉ − 50)⁺. Class B = $0.36 × (⌈b·N / 1M⌉ − 10)⁺.
- Rounding: the model rounds usage up and then subtracts the free tier, which is the more expensive reading of S1's rule. S1 does not say which comes first. The difference is at most one unit per line per month: ≤ $4.50 Class A, $0.36 Class B, $0.40 Queues, $0.015 storage.

### Results

| Scenario | Files/month | Class A | R2 A $ | Storage $ | Queues $ | Other usage $ | **Total $/month** |
|---|---|---|---|---|---|---|---|
| Steady, g = 0.5 TB/yr, W = 0 | 10k | 26k | 0 | 0 | 0 | 0 | **5.00** |
| Steady, g = 1 TB/yr, W = 30 d | 21k | 52k | 0 | 1.11 | 0 | 0 | **6.11** |
| Steady, g = 2 TB/yr, W = 30 d | 42k | 103k | 0 | 2.35 | 0 | 0 | **7.36** |
| Seed month 2 TB, d = 1 d, W = 0 | 500k | 1.24M | 4.50 | 0.85 | 0.80 | 0 | **11.16** |
| same, 14-day homelab outage mid-month | 500k | 1.24M | 4.50 | 3.66 | 0.80 | 0 | **13.96** |
| same, **30-day warm cache left on** | 500k | 1.24M | 4.50 | 29.85 | 0.80 | 0 | **40.15** |
| same, 2 MB mean file (1M files) | 1M | 2.25M | 9.00 | 0.85 | 2.00 | 0 | **16.86** |
| same, 8 MB mean file | 250k | 0.73M | 0 | 0.85 | 0.40 | 0 | **6.26** |
| same, metadata batched (m ≈ 0) | 500k | 0.74M | 0 | 0.85 | 0.80 | 0 | **6.66** |
| same, P = 8 / 16 / 64 MiB | 500k | 1.15M / 1.08M / 1.03M | 4.50 | 0.85 | 0.80 | 0 | **11.16** (rounding hides the difference) |
| Homelab down, whole library staged: 2 / 5 / 10 TB | — | — | — | 29.85 / 74.85 / 149.85 | — | — | **+$5 base** |
| Whole-device restore, 500 GB staged 7 days (+1 day lifecycle lag) | ~125k objects | ~0.13M | 0 | ~1.9 | — | 0 | **< $2 extra** |

Break-even against a $25 BUD-CLOUD (a $20 usage allowance): about 1.34 TB staged on average, or about 5.4M Class A operations in a month.

## Findings

### F1. Line items (Q1). Confidence: High on prices, Medium on volumes

- All unit prices come from primary sources (C1–C10). T2's Cloudflare figures are confirmed, and so are the owner intake's unit prices.
- Two small corrections to `owner-intake.md` §B:
  1. **B2** gives "$2.25 for 1.5M Class A (0.5M above free)". Under S1's rounding rule, 1.5M bills as 2M, so the charge is **$4.50**. The seed-month total is about $11–14, not $12.
  2. **B1** puts alerts at "$10 and $20". Cloudflare budget alerts exclude the $5 subscription (C11), so an alert at **$20 usage** means a **$25 bill**. Set usage-alert thresholds at BUD-CLOUD minus $5.
- Always-on Durable Objects are a trap. One DO kept awake for a month uses 324,000 GB-s. Two exceed the 400,000 GB-s included, and because the overage rounds up to 1M GB-s, the first extra second costs $12.50 (C9). If C1 uses DOs, it should use hibernation and avoid holding WebSockets open.
- Email costs $0 at family scale (25 people × a few nudges ≪ 3,000/month). **Owner alerts can go to a verified destination address for free, even on Workers Free** (C10). This makes a zero-cost admin alert channel.
- D1 and Durable Object storage are small either way. Assuming about 200 B per index row, 5M dedup rows is about 1 GB, inside the 5 GB included and under D1's 10 GB database cap (S11). Cost does not decide D1 vs DO; C1 decides on design grounds.

### F2. Workers Paid vs Free (Q8). Confidence: High

Use Paid. Free fails a seed on Queues (10k ops/day, about 1,667 files/day), D1 writes (100k/day), 24 h queue retention (ADR-0001's reconciliation still works, but homelab outages then turn into reconciliation events), the 10 ms CPU limit, and email (C18). Paid costs $5/month and makes up 70–100 % of the steady-state bill.

### F3. Seed scenarios and peak staging (Q2). Confidence: Medium

- **10 TB via R2** takes about 5 months at 2 TB/month and costs about $55 in total, or about $30 above the base fee. It costs about $200 in total if the warm cache stays on through the seed.
- **Part size is not a cost lever.** At 10 TB, parts cost $8.58 at the T1 default of about 5.0 MiB and $0.67 at 64 MiB (C17). At the assumed file mix, 81 % of Class A comes from the per-file floor N·(1 + m). The cheaper lever is **batching metadata records** (m → 0), which about halves Class A. Packing small files into restic- or kopia-style packs (16–128 MiB, S32, S33) would cut Class A further, but it conflicts with ADR-0001's "objects keyed by dedup ID", so it is not recommended. B6 should choose the part size on resume, memory and iOS-wake grounds, not on cost.
- **Peak staging is set by homelab downtime and the warm cache, not by drain rate,** as long as the home downlink exceeds the family's combined upload. A 500 Mbps downlink drains 10 TB in 1.9 days, and a 100 Mbps downlink in 9.3 days. The worst case, the whole library staged because the homelab is down, costs $149.85/month at 10 TB. A 14-day outage in a 2 TB month adds $2.81.
- **The warm cache is the largest controllable line.** Recommendation for C1 (traceability C-01): a warm cache of at most 30 days at steady state, **suspended automatically during seed months or above a staged-bytes cap**.
- **IA for staging is worse on every line.** Using S1's own IA example: 2 TB staged for 2 days in IA costs about $40 (a 30-day minimum of $20 plus $20 retrieval), against about $2 in Standard (C1).
- **USB-heavy or legacy import (A9)** costs about $0 in cloud charges. The choice between R2, USB and import is therefore about ISP caps, calendar time and owner effort (A4, A9, E5), not about the cloud bill.

### F4. Worst-case abuse cost and billing alerts (Q9, Q10). Confidence: High on mechanisms, Medium on figures

**Cloudflare will not stop spend.** Budget alerts are informational, day-lagged, account-wide and exclude subscriptions (C11). Per-product usage notifications need a Pro zone and are also informational. Threshold billing only invoices early (C12). The Workers rate-limit binding is "permissive, eventually consistent" and "not … an accurate accounting system" (S22), so it can throttle but cannot meter. A $50 BUD-ABUSE must therefore be enforced by Reliquary.

Abuse vectors and their cost rates:

| Vector | Who | Cost rate (derived) | Bounded by | Status |
|---|---|---|---|---|
| Stream of small junk PUTs via presigned URLs | Holder of a stolen device credential | ~$8 per 1M objects (C14); $69/day at 100/s, $690/day at 1,000/s | Per-device presign cap per day; account-wide circuit breaker | Needs design (C2) |
| Replay of one presigned PUT until it expires | same | Up to 1 write/s per key (C13): 900 Class A per URL at 15 min expiry | Short single-PUT expiry (≤ 60 s where the client can keep up), `If-None-Match: *` as a signed header, and auto-suspend on an overwrite event | Enforcement and billing of 412/429 unknown → `[SB]` |
| Storage flood (large bodies; Content-Length not bound) | same | 1 Gbps ≈ 10.8 TB/day; each day that volume is held accrues ≈ $5.40 | Per-device cap on staged, uncommitted bytes (from declared sizes); homelab rejects declared/actual size mismatches **before** download; auto-delete (free) | Whether a signed Content-Length is enforced is unknown → `[SB]` |
| Garbage pulled home | same | No dollars, but ISP cap and homelab bandwidth | Size check against the event message before GET | Design (A3) |
| Unauthenticated flood on the Worker | Anyone | $0.30/M requests + CPU ($259/day at 10k req/s) | WAF rule on a Free zone: 1 rule, per-IP, 10 s period (S21). Keep rejection CPU < 1 ms. **Not bounded by per-device caps.** | Whether WAF-blocked requests are billed as Worker requests is unknown → `[SB]` |
| Bad-signature requests direct to R2 | Anyone who knows the bucket host | 403 is not documented as free (only 401 is) | Unknown | `[SB]` |

**A bound that meets BUD-ABUSE, to be confirmed in C2:** cost ≤ k·T·(U_d·E_eff·$4.5e-6 + U_d·$3.5e-6) + k·Q_d·$0.015/GB-month + flood cost. Here k is the number of compromised devices, T the days until auto-suspend, U_d the presigns per device per day, E_eff the effective writes per URL (1 with If-None-Match enforced, otherwise the expiry in seconds), and Q_d the staged-byte cap per device. **Example:** k = 3, T = 1 day, U_d = 25,000, E_eff = 1, Q_d = 100 GB gives **≈ $0.60 per day of exposure plus $4.50/month of storage**, far below $50. With E_eff = 900 it becomes about $304/day, which is the reason a short expiry or If-None-Match matters.

**Billing-alert list (a C4 deliverable).**

| # | Alert | Where | Threshold (proposed) | Latency |
|---|---|---|---|---|
| 1 | Cloudflare budget alert (default) | Billing → Billable Usage | $10 usage | Next day |
| 2 | Cloudflare budget alert | same | BUD-CLOUD − $5 (e.g. $20) | Next day |
| 3 | Cloudflare budget alert: seed month | same | Seed ceiling − $5 (e.g. $45); add it during planned seeds | Next day |
| 4 | **App meter: per-device presigns, declared bytes, overwrite events** | Worker + consumer Worker (always on, not the homelab puller) | U_d, Q_d; any overwrite of a committed key suspends the device | Minutes |
| 5 | **App meter: estimated account spend today** (from its own counters × S1/S7/S10/S12 prices) | Worker | BUD-ABUSE / 2 → owner email; BUD-ABUSE → global presign stop | Minutes |
| 6 | Staged backlog GB and oldest-pending age | Homelab reconciliation + Worker | > 1.34 TB staged (the $20 break-even) or oldest message > retention − 2 days | Hourly |
| 7 | Payment-method expiry reminder | Owner calendar | 30 days before card expiry (a failed preauthorisation can make R2 inaccessible, C12) | — |
| 8 | Pool fill and disk-purchase trigger | Homelab (C7) | §F6 | Daily |
| 9 | ISP month-to-date usage vs cap | Homelab puller | §F5 | Daily |

Alerts 4–5 go to a verified destination address, which costs nothing (C10).

### F5. Home ISP (Q3). Confidence: High on arithmetic, Low on ISP terms

- **Hairpin:** a home device that uploads to R2 uses the home uplink, and the homelab pull then uses the downlink. Whether an ISP counts both directions toward a cap is ISP-specific and unknown here.
- **Throttle economics:** deferring 1 TB for a month in R2 costs $15. The one secondary figure found for overage (a legacy capped plan at $10 per 50 GB, up to $100/month, S36, low confidence) works out to about $200/TB. **Proposed puller schedule:** daily pull allowance = (cap − household baseline − margin) / days left in the cycle; let the backlog wait in R2; alert 9 fires at 80 % of the cap. Home devices should seed by USB or LAN (A4) when the owner reports a cap (H2 D2).
- **Restore time is bound by the home uplink:** 1 TB takes 4.63 days at 20 Mbps, 1.85 at 50 Mbps and 0.93 at 100 Mbps. A8 should use these to set the whole-device default in BUD-RESTORE.

### F6. Capacity forecast and disk-purchase trigger (Q4). Confidence: High on the method; no data yet

- Stored(t) = (L0 + g·t)·(1 − dedup)·(1 + o_engine + o_deriv) + snapshots + scratch. dedup comes from A1/F3; o_engine from A6-S2; o_deriv (preservation derivatives, OD-16) from A7. **All are no result today.** v0 uses dedup = 0 and o = 0, which is conservative for dedup and optimistic for overhead.
- Usable = drives × size × layout efficiency: mirrors 50 %, RAIDZ-P over N disks ≈ (N − P)/N (C19). Drives are sold in TB; ZFS reports TiB (16 TB = 14.55 TiB). ZFS slop space is not modelled (C5).
- **Trigger:** buy when Stored(t + lead + buffer) ≥ h·Usable. Lead is about 1–2 weeks to burned-in drives (H5 L21); a 90-day buffer is proposed.

| Tier (C5 prices it) | Usable | L0 = 2, g = 0.5 | L0 = 5, g = 1 | L0 = 10, g = 1.5 | L0 = 10, g = 2 |
|---|---|---|---|---|---|
| S: 2 × 16 TB mirror | 16 TB | 21.6 y to 80 % | 7.8 y | **1.9 y** | **1.4 y** |
| M: 4 × 16 TB RAIDZ2 (same usable as 2 mirrors, C19) | 32 TB | 47 y | 20.6 y | 10.4 y | 7.8 y |
| L: 6 × 20 TB RAIDZ2 | 80 TB | > 100 y | 59 y | 36 y | 27 y |
| Stored after 10 years (no dedup) | — | 7 TB | 15 TB | 25 TB | 30 TB |

- **Reading:** at the top of the settled 2–10 TB range, tier S needs expansion inside the first 2 years, so it only fits families near 2–5 TB. Tier M covers the settled range for about a decade. Because retention is keep-forever, tier L's advantage is mainly the 5–7 year refresh cycle, not headroom. Also, per C19, the ARC guidance scales with storage: 2 GiB + 1 GiB/TiB is about 31 GiB for tier M.
- **Fewer large vs more small drives:** a mirror pair gives the lowest drive count and the best performance but a 50 % yield. RAIDZ2 over 6 drives yields 67 % and survives any two failures. Larger drives mean longer resilvers (C5-S3). No $/TB source was reachable (diskprices.com blocked), so cost per usable TB is left to C5 with the H5 estimate (E $150–350 per 8–20 TB drive) as a placeholder.

### F7. Homelab running costs (Q5). Confidence: Low (inputs missing)

- **Power:** kWh/year = W × 8.766. Each 10 W of continuous draw is 87.7 kWh/year. The platform wattage (smart plug, `[OL]`) and the owner's tariff are **owner inputs**. EIA was blocked, so no default price is given.
- **Drive replacements:** expected failures over the horizon ≈ n × AFR × years. With AFR ≈ 1.4 % (C20, secondary), 6 drives over 10 years ≈ 0.8 failures. Budget one spare drive per pool. Backblaze runs data-centre fleets, so home conditions may differ; treat this as a floor.
- **Refresh:** a 5–7 year refresh (PLAN) means one full drive set inside a 10-year horizon: refresh cost ≈ drive-set price at the time.
- **UPS battery:** replacement interval is a C5 input. No primary source was read.
- **New vs recertified:** no primary AFR or price data for recertified drives → C5, with the owner's view.

### F8. Optional and fixed costs (Q6). Confidence: High, except the domain (Low)

| Item | Cost | Needed when | Source |
|---|---|---|---|
| Workers Paid (production + sandbox accounts) | $5/month each | Always (production); sandbox during research | C5 |
| Apple Developer Program | $99/year | OD-01 puts iOS in v1, or OD-09 buys Developer ID | S25 |
| Azure Artifact Signing Basic | $9.99/month (5,000 signatures) | OD-09, if Smart App Control blocks unsigned builds and the owner is eligible (US/Canada individual) | C21 |
| Google Play registration | $25 once | OD-10 = closed track | C22, T2 |
| Android Developer Console, limited distribution | $0 | OD-10 = limited (≤ 20 devices) | C22 |
| Domain | about $10–15/year (E) | Always | I3 (not verified) |
| Email | $0 up to 3,000/month | OD-03 = cloud email | C10 |
| Resend or Postmark fallback (B4 beta policy) | not checked | If Email Service stays in beta | — |

Annual fixed cost: **$60** (Workers Paid) + domain, about **$70–75**. With Apple and Azure Basic both bought it is about **$290–295**, plus $25 once for Play.

### F9. Storage governance and fair share (Q7). Proposal for OD-20. Confidence: Medium

Principles: nothing is ever deleted or refused silently (keep forever); users never configure anything; the owner decides centrally. Precedents: Ente uses admin-set per-member limits inside a family pool, with 50 MiB of overflow and a cached check for small files (C23). Immich refuses uploads at a hard quota. Reliquary should **not** copy the hard refusal, because a refused keepsake is an unprotected keepsake.

1. **Soft per-person budgets** (the owner sets them, e.g. equal shares of h·Usable). Crossing a budget alerts the **owner**, not the user, and never blocks core keepsakes (camera roll, documents, discovered keepsake folders). The health view never shows a quota to the user.
2. **Approval-gated categories:** game captures, dashcam footage, VM or disk images, and any single file above a size threshold (e.g. 20 GB; owner sets it). The device hashes and counts them but does not upload, and shows "Waiting for [owner] to OK this". The owner approves from the admin CLI. The policy reaches devices as a **signed policy document fetched from the control plane**, so users touch nothing. The E4 discovery rules decide the category detection.
3. **Pool-full states:**
   - **Green:** below the trigger.
   - **Amber:** the purchase trigger has fired (§F6). The owner is alerted; nothing changes for users.
   - **Red:** h·Usable reached, e.g. 90 %. The homelab stops pulling approval-gated and over-budget uploads, then everything except core keepsakes. Staging absorbs the backlog up to a **staging cap** of (BUD-CLOUD − $5)/$0.015 GB-month ≈ 1.3 TB at $25.
   - **Staging cap reached:** the Worker stops issuing presigned URLs with a "home storage full, retry later" code. Devices say plainly: "Your backups are waiting because home storage is full. [Owner] has been told." Hash caches keep "not yet backed up" accurate.
   - **Emergency expansion runbook:** C5/C8.
4. **Seasonal bursts** (holidays, trips): absorbed by staging. At 2 TB/month of inflow and a 1-day dwell, the cost is < $1. Suspend the warm cache automatically when staged bytes exceed 25 % of the staging cap.

### Alternatives compared

| Option | Fit with settled requirements | Pros | Cons | Evidence |
|---|---|---|---|---|
| **Workers Paid** | Fits | Carries seeds; email; 14-day retention; CPU headroom | $5/month fixed | C5–C7, C10, C18 |
| Workers Free | Fails seeds; no email to family (ADR-0002) | $0 | 1,667 files/day queue ceiling | C18 |
| **R2 Standard for staging** | Fits | Free tier; no minimum duration; no retrieval fee | — | C1, C2 |
| R2 IA for staging | Fits, but costly | Cheaper per GB-month when held ≥ 30 d | 30-day minimum, $0.01/GB retrieval, 2× Class A, no free tier: about 10× Standard for short dwell | C1 |
| Part size 5 / 8 / 16 / 64 MiB | All fit | Larger parts → fewer operations | Savings ≤ $8 per 10 TB; larger parts cost memory and resume granularity (T1 E9) | C17, I1 |
| Batch metadata records (m → 0) | Fits (A2/A3 decide) | About halves Class A in seed months | Changes the protocol shape | §Model |
| Pack small files | **Conflicts** with ADR-0001's dedup-ID-keyed objects | Largest cut in operations | Would need a superseding ADR; not worth it at < $10/month | S32, S33 |
| Mirror pair vs RAIDZ2 × 6 | Both fit | Mirror: fewer drives, simple; RAIDZ2: 67 % yield, two-failure tolerance | Mirror: 50 % yield; RAIDZ2: longer resilver, more drives | C19 |
| New vs recertified drives | Both fit | Recertified: cheaper (unverified) | No AFR data | — |

### Similar work and lessons

| Project | What they do | Borrow or avoid | Source |
|---|---|---|---|
| rclone S3/R2 | 200 MiB single-PUT cutoff; 5 MiB chunks; 10,000-part cap; chunk size grows to fit the cap | Borrow the growth rule for huge files; the cutoff logic is similar to T1's "single PUT at ≤ 1 part" | S28 |
| restic / kopia | Pack blobs into 4–128 MiB (restic) or 20 MiB (kopia) objects | Avoid for R2 staging (conflicts with ADR-0001); relevant to A6's storage engine | S32, S33 |
| Ente family plans | Admin-set per-member limits in a shared pool; 50 MiB overflow; cached check below 100 MiB | Borrow central, admin-set budgets and the overflow tolerance; avoid hard refusal | S29, S30 |
| Immich | Hard per-user quota at upload | Avoid hard refusal of keepsakes | S31 |
| Ente / B2 prices | About $12/TB-month (Ente 1 TB plan) and about $6.95/TB-month (B2), secondary snippets only | Sanity check only: the homelab is a capital cost, not a per-TB rent | S37, S38 |

### Tools and libraries

| Name | Purpose | Notes |
|---|---|---|
| Python 3 (stdlib) | The v0 calculation | Committed version is the C4-S1 runner's deliverable |
| Cloudflare billable-usage dashboard and GraphQL analytics | Checking the model against the sandbox bill | `[SB]`, needs H5 L01 |
| Smart plug with energy metering | Platform wattage | `[OL]` kit (C5) |

## Spikes

Placeholder. The C4-S1 spike runner works in parallel and fills in this table.

| Spike | Hypothesis | Pass → / fail → (decision) | Exec tag | Budget IDs | Data class | Status | Result |
|---|---|---|---|---|---|---|---|
| C4-S1 Model v0, then v1 with A0 numbers | The steady-state bill is known within ±25 %; worst-case abuse is bounded below BUD-ABUSE; the disk-purchase trigger date is computed | Pass → set BUD-CLOUD and BUD-ABUSE (OD-14) and the alert list; fail → rerun with A0 and C2 numbers | CT | BUD-CLOUD, BUD-ABUSE | `SYN → results` | Running (separate runner) | *(runner fills in)* |

Analyst view for the runner: ±25 % holds for steady state because $5 of about $5–7 is fixed. The abuse bound holds **only** with the app-level caps in §F4, and three billing behaviours are undocumented (items 1–3 in Open questions). The trigger date cannot be computed until H2 F4/C4 and E1 give L0 and g. §F6 gives scenario dates.

## Conflicts with settled text

- None directly.
- Packing small files would conflict with ADR-0001 §4 (objects keyed by dedup ID). It is not recommended.
- The OD-20 proposal (§F9) keeps keep-forever and "users never touch configuration" intact. The owner should confirm that approval-gated categories are an acceptable reading of "auto-discovery proposes what to protect".

## Open questions

1. Does R2 bill requests that return 403 (bad signature, expired URL), 412 (If-None-Match failed) or 429 (same-key rate limit)? Only 401 is documented as free. **Owner:** C2 via an `[SB]` spike (sandbox, H5 L01).
2. Does R2 enforce a signed `Content-Length` and a signed `If-None-Match: *` on presigned PUT and UploadPart? **Owner:** C2/D3 `[SB]`.
3. Are Worker requests blocked by WAF rate-limiting rules billed? **Owner:** C2 `[SB]`.
4. Operations per file (Class A, Class B, Worker requests, D1 rows, Queue messages), measured. **Owner:** A0 (v1 of this model).
5. Mean file size, bytes in large files, growth per person per year. **Owner:** E1 census; H2 F4.
6. Storage-engine and derivative overhead. **Owner:** A6-S2, A7.
7. Disk $/TB (new and recertified), platform wattage, electricity tariff, UPS battery interval. **Owner:** C5 plus owner inputs. The price sites are blocked, so either allowlist diskprices.com or have the owner supply quotes.
8. The owner's ISP cap and up/down speeds (H2 D1–D2). These set the throttle schedule and restore times.
9. Whether incomplete multipart parts are billed as storage until the 7-day default abort. This is not stated in S1 or S4, and it affects the abuse storage bound. **Owner:** C2 `[SB]`.

## Recommendation

1. **Workers Paid, R2 Standard, no IA** for staging.
2. **Set BUD-CLOUD at $25/month and a $50 seed-month ceiling** (the intake defaults). Modelled use is $5–7 at steady state and $11–17 in a seed month, so the defaults leave about 3× headroom. Set Cloudflare usage alerts at $10, $20 and (during seeds) $45, because the alerts exclude the $5 fee.
3. **Set BUD-ABUSE at $50, conditional on the app-level controls** in §F4: per-device presign and staged-byte caps, a short single-PUT expiry or a signed If-None-Match, auto-suspend on overwrite and on declared/actual size mismatch, and an account-wide spend meter with a global presign stop. The meter runs in an always-on consumer Worker. Without these controls, no BUD-ABUSE value can be honoured, because Cloudflare will not cap spend.
4. **Warm cache:** at most 30 days at steady state, suspended automatically during seeds and above 25 % of the staging cap.
5. **Choose part size on non-cost grounds** (B6). Prefer batching metadata records if A2/A3 allow it.
6. **Homelab tier M (4 × 16 TB RAIDZ2 or 2 mirror pairs) as the default** for C5 to price. Choose tier S only if the family library is at the 2–5 TB end.
7. **Adopt the §F9 governance proposal** for OD-20.

What would change this: A0 measuring more than about 5 R2 objects per file; E1 finding a mean file size below 2 MB; or the `[SB]` checks showing that 403, 412 or 429 responses are billed, which would make unauthenticated R2 floods an unbounded cost.

## Decision requests

### OD-14: Cost ceilings (BUD-CLOUD, BUD-ABUSE) and alert thresholds
- **Needed by:** Wave 0 / H2 intake (already overdue per the queue)
- **Evidence:** this note §Model, §F4; `owner-intake.md` §B
- **Options:**
  | Option | What it means for the family | Cost (money and owner time) | Reversibility | Risks |
  |---|---|---|---|---|
  | A. $25 steady / $50 seed / $50 abuse, with app-level caps | Nothing visible | $5–7/month modelled; build effort for the meters (C2) | Easy | Caps set too tight could throttle a legitimate seed; mitigate with an owner "seed mode" |
  | B. $15 steady / $30 seed / $20 abuse | Seeds go slower or mostly by USB | Lower ceiling; more USB work for the owner | Easy | Too little headroom for outage backlogs (+$3.66) plus a warm cache |
  | C. No abuse cap, rely on Cloudflare alerts | Nothing visible | $0 build | Easy | Alerts are a day late and never cap: $690/day is possible (C14) |
- **Recommendation:** A. The modelled bill is about a quarter of the ceiling, and the $50 abuse figure is achievable once the §F4 controls exist.
- **Touches settled text:** none
- **If no decision by the deadline:** the run assumes A as *provisional*. C2 designs the caps against $50.

### OD-20: Per-person storage budgets and categories that need approval
- **Needed by:** Wave 2
- **Evidence:** this note §F9; precedents C23
- **Options:**
  | Option | What it means for the family | Cost | Reversibility | Risks |
  |---|---|---|---|---|
  | A. Soft budgets (owner alerts only) + approval-gated categories + pool-full states (§F9) | Core keepsakes are never blocked; big odd files wait for the owner's OK | Owner approves occasional items (fits BUD-SUPPORT) | Easy | Category detection errors (E4) |
  | B. No budgets; everything is uploaded | Simplest | Capacity risk: dashcam and game captures can dominate | Easy | Pool fills early; tier S fails sooner |
  | C. Hard per-person quotas (Immich-style) | Uploads refused at the quota | Low | Easy | Unprotected keepsakes, and users see configuration-like messages |
- **Recommendation:** A.
- **Touches settled text:** possibly CLAUDE.md "auto-discovery proposes what to protect" (the gating is owner-side). Keep-forever is untouched: nothing is deleted.
- **If no decision by the deadline:** B, with the pool-full states from A, because they are safety behaviour.

## Hand-offs

| To | What | Why |
|---|---|---|
| C2 / D3 | §F4 cap set (U_d, Q_d, expiry, If-None-Match, overwrite and size-mismatch auto-suspend, account spend meter) and Open questions 1–3 and 9 as `[SB]` spikes | BUD-ABUSE is not enforceable otherwise |
| C1 | Warm-cache policy (traceability C-01); always-on consumer Worker for meters; avoid always-on DOs; staging-cap "retry later" code | Largest variable cost line; DO rounding trap |
| A0 | Measure the §Model **A** parameters (objects, Class A/B, requests, D1 rows and queue messages per file) | Turns v0 into v1 |
| A2 / A3 | Consider batching metadata records; size check against the event message before GET | About halves seed Class A; avoids pulling garbage home |
| B6 | Part size is not a cost lever; choose it on resume, memory and iOS grounds | C17 |
| C5 | Tiers S/M/L, the trigger formula, AFR (secondary), ARC sizing; supply $/TB, wattage, UPS | BOM (ADR-0030) |
| C7 | Alerts 6, 8 and 9 | Monitoring |
| A8 | Restore-time table (§F5) for the BUD-RESTORE whole-device default | Uplink-bound |
| A4 / A9 / E5 | Home devices on capped ISPs seed by USB or LAN; the cloud cost is neutral | §F3, §F5 |
| H1 | Blocked sources: backblaze.com, xfinity.com, eia.gov, diskprices.com, azure.microsoft.com pricing, ente.com; WebSearch budget exhausted | PLAN §5.4 |
| E1 | Mean file size, bytes in large files, growth per person | Model inputs |
