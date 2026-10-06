# F3-S2: dedup-oracle simulation (a compromised device probes 10k candidates)

- **Workstream:** F3 (`docs/research/PLAN.md`, "F3."). **Exec tag:** CT.
- **This is emulated, not real R2/Cloudflare.** The protocol logic is a Python discrete-time simulation (1-hour steps). The Durable Object accounting check ran in Miniflare 4.20260730.0 (workerd 1.20260730.1) on localhost.
- **Run by / date:** F3 spike runner (Wave 1, batch W1-a), 2026-09-29.
- **Data-handling class:** `SYN → results`, plus `PUB → results` for the size priors (F3-S1 Open Images and GovDocs1 extracts).
- **Budget IDs cited:**
  - **BUD-HASH** sets the legitimate seeding rate a limit must allow;
  - **BUD-REVOKE** is assumed: suspension within the same hour as an alert;
  - **BUD-ABUSE** has no value yet; the attacker's upload cost is reported for it;
  - **BUD-TTS** is at risk from a strict cap.

## Hypothesis and decision

- **Hypothesis (PLAN):** under the proposed limits, a compromised device probing 10,000 candidate files either needs more than 30 days or triggers an admin alert.
- **Decision informed:**
  - presence-query semantics and limits (SR-21; the F3 note's DR-F3-2, an addition to OD-04);
  - matrix rows M-02 and M-03;
  - G2 test NT-12.
- **Pass →** adopt the configuration that passed. **Fail →** narrow the scope further, or accept AR-06 explicitly.

## What was simulated

**Attacker.** An enrolled device that holds the family dedup secret and its own valid credential (D1 AP3/AP4/AP5). Two scenarios:
- *learn-the-remaining-information*: 10,000 candidates, exactly one present;
- *confirmation-of-a-file*: 20 candidates, one present.

Target files belong to another person ("cross = 1") or to the attacker's own person ("cross = 0").

**Configurations.**

| ID | Presence answer | Limits and accounting |
|---|---|---|
| C0 | Global (ADR-0001 §4 as written) | None |
| C1 | Global | SR-21 per-device limit sized so that a BUD-HASH first seed is not slowed |
| C1s | Global | A flat cap of 10,000 / 30 = **333 lookups per day**, the only flat cap that makes 10k probes take 30 days |
| C2 | Global | C1 + record-first + exact per-device accounting (a Durable Object) + auto-suspend on alert |
| C3 | Per-person scope: files of other people below T_x always answer "missing" | C2 accounting |
| C3L | As C3 | As C3, but the homelab issues receipts faster for content it already holds (a timing leak) |

C1's limit: 128 GB ÷ the F3-S1 Open Images mean of 2,229,987 B = **57,399 lookups in 6 h**, which is **9,567 per hour**. Batches are capped at 1,000 IDs (SR-21 "current batch"; a parameter).

**Detectors** (C2/C3). All thresholds are simulation **parameters**, not proposals. An "orphan" is an ID answered "missing" whose upload does not start before the claim's TTL expires (SR-10's abandoned claim).

| ID | Rule |
|---|---|
| D-a | More than 300 orphans in 24 h (claim TTL 24 h) |
| D-b | More than 1,000 orphans, cumulative (claim TTL 24 h) |
| D-b1 | D-b, with claim TTL 1 h and at most 1,000 open claims per device |
| D-c | D-a + D-b, plus more than 50 new objects of one identical size from one device in 24 h (homelab-side) |

**Attacker strategies.**

| ID | Strategy |
|---|---|
| S1 | Burst, abandon misses |
| S2 | Drip (280 per day), abandon misses |
| S3 | Burst, upload every miss (mimic a real seed; about 2 GB for 200 KB candidates) |
| S4 | Drip, upload every miss |
| S5 | S3, with every candidate a different size |

**Legitimate profiles** (false-positive check):

| ID | Profile |
|---|---|
| L1 | Phone first seed of 57,399 files in 6 h, with orphan probability 0 / 0.1 % / 1 % and cross-person hit rate 5 % / 20 % (both unmeasured, so swept) |
| L2 | Steady state, 50 files per day |
| L3 | Reinstall that re-queries 57k files, all hits |
| L4 | Desktop seed of 500k documents in 48 h |

The same-size cluster sizes come from **measured** public samples (`samesize.py` → `legit_samesize.json`):
- 57,399 Open Images photos: at most **7** files share one exact size (20 samples);
- 250,000 GovDocs1 documents: at most **425** (10 samples; 334–371 counting only files of 64 KiB or more).

## Results

The PLAN verdict is taken **over the attacker's best strategy**: a configuration passes only if every strategy either takes more than 30 days or is alerted. Time resolution is 1 hour, so "0.04 d" means "within the first hour". "P(learn)" is the chance that the one true candidate was answered before the alert.

| Config | Detector | Target | Scenario | PLAN verdict | Strategies that beat it | Max P(learn) | Fastest full run |
|---|---|---|---|---|---|---|---|
| C0 | — | other person | 10k | **FAIL** | S1, S3, S5 | 1.0 | ≤ 1 h |
| C1 | — | other person | 10k | **FAIL** | S1, S3, S5 | 1.0 | 2 h |
| C1 | — | other person | 20 | **FAIL** | all | 1.0 | ≤ 1 h |
| C1s | — | other person | 10k | PASS (time) | — | 1.0 after 30.04 d | 30.04 d |
| C1s | — | other person | 20 | **FAIL** | all | 1.0 | ≤ 1 h |
| C2 | D-a / D-b / D-b1 | other person | 10k | **FAIL** | S3, S5 (mimic) | 1.0 | 2 h |
| C2 | D-c | other person | 10k | **FAIL** | S5 | 1.0 | 2 h |
| C2 | any | other person | 20 | **FAIL** | all | 1.0 | ≤ 1 h |
| C3 | any | other person, < T_x | 10k and 20 | **PASS** (the oracle gives no information) | — | 0.0 | — |
| C3 | D-a / D-b / D-b1 | same person | 10k | **FAIL** | S3, S5 | 1.0 | 2 h |
| C3 | any | same person | 20 | **FAIL** | all | 1.0 | ≤ 1 h |
| C3L | any | other person | 10k | **FAIL** | S3, S5 (D-c: S5) | 1.0 | 2 h |

Details of C2 with D-b1 in the 10k scenario:
- **S1:** alerted after 2,000 probes (hour 3), P(learn) 0.20.
- **S2:** alerted after 1,120 probes (day 3), P(learn) 0.11.
- **S3, S4, S5:** finished all 10,000 probes with no alert. The attacker uploaded 2.0 GB and left 10,000 device-signed records and objects at the homelab as forensic evidence.

**False positives** (legitimate profiles; `evidence/run.log`):

| Detector | Profile | Result |
|---|---|---|
| D-a (> 300 orphans per 24 h) | L1 at orphan probability 1 % | Fires at hour 27–28 |
| D-a | L1 at 0 % and 0.1 % | Silent |
| D-b / D-b1 | L1 at 1 % | Silent for one seed (≈ 574 orphans). A cumulative counter will fire eventually over a device's lifetime unless it decays; the decay rate is not modelled |
| D-c (> 50 same-size new objects per 24 h) | L4 (500k-document desktop seed) | **Fires** (GovDocs1 clusters reach 425) |
| D-c | L1 phone seed | Silent (photo clusters reach 7) |

The real orphan probability is **unmeasured**. It has to come from B6/A3 pilot telemetry.

**Cost of the strict cap (C1s).** A 57,399-file phone takes **172 days** to finish its first-pass lookups, and a 500k-file desktop more than 400 days. This defeats the purpose of BUD-HASH (first pass in one charge window) and puts BUD-TTS at risk for anything queued behind the backlog.

**Durable Object accounting, emulated** (`do-emu/`, `evidence/do_emulation_results.json`). 20 concurrent clients sent 100 requests each (2,000 requests, 1–20 IDs per request) to one device's DO.

| Trial | IDs sent | Result |
|---|---|---|
| (a) No budget | 20,939 | Counter = 20,939 exactly |
| (b) Hard cumulative budget of 5,000 | 20,751 | Granted exactly 5,000; refused 15,751 |
| (c) Open-claims cap of 1,000 | 20,671 | Granted exactly 1,000; refused 19,671 |

`used + refused = sent` in every trial, so there was no over-grant under concurrency. This supports NT-12's "counters exact under concurrency" **in workerd locally**; real multi-region behaviour is not tested. The first harness run showed a *client-side* JavaScript lost-update bug (`x += await …`), which was fixed. The DO counters were exact in both runs.

## Pass / fail

**Overall: FAIL for ADR-0001 §4 with SR-21-style limits (C0, C1, C2).**
- A per-device limit that lets a phone seed at the BUD-HASH rate lets 10k probes finish in about 2 hours.
- A cap strict enough for 30 days (333 per day) makes a first seed take about 172 days, and still does not stop a 20-candidate confirmation, which finishes in the first hour.
- Accounting with auto-suspend catches attackers who abandon their misses (alerts after 1,120–2,000 probes). It misses an attacker who uploads its misses (about 2 GB).
- The one extra homelab rule that catches that attacker (same-size clusters) is evaded by varied candidate sizes. It also false-alarms on a desktop document seed.

**The only configuration that passes is C3: per-person scope for files below T_x.** It removes the cross-person oracle outright: P(learn) = 0 for every strategy and both scenarios. Two conditions:
1. The receipt path must not reveal prior presence. C3L shows that a faster receipt for known content restores the oracle.
2. The same-person case (a thief probing the owner's own other devices) and files at or above T_x stay exposed at C2's level.

## Caveats

- Hourly granularity. Legitimate uploads resolve their claims within the hour (upload-paced lookups). Uplink limits are not modelled.
- One random placement of the target per run. P(learn) is also reported analytically as probes answered ÷ candidates.
- Detector thresholds were chosen by hand. The orphan probability and the cross-person hit rate are unmeasured.
- Miniflare is not Cloudflare. Nothing here tests the Workers rate-limit binding, multi-location behaviour, or DO latency and cost. A sandbox confirmation belongs to C1/C2 (`[SB]`) once H1's sandbox account exists.

## Files

| File | Purpose |
|---|---|
| `sim.py` | Simulation; writes `results.json`, prints tables (`python3 sim.py > run.log`) |
| `samesize.py` | Measures the same-size clusters from the F3-S1 extracts (needs `../F3-S1/` data files) → `legit_samesize.json` |
| `do-emu/worker.mjs`, `do-emu/run.mjs` | Miniflare DO accounting harness (`npm install && node run.mjs`) |
| `evidence/results.json`, `evidence/run.log`, `evidence/do_emulation_results.json` | Outputs |
