# Shared budget sheet

- **Owner:** H1. Values are confirmed by the owner at intake (H2).
- **Last updated:** 2026-09-29
- **Source:** `docs/research/PLAN.md` §2.0

Spike pass criteria **cite these IDs** instead of inventing their own thresholds. Every value below is a **proposed default, owner to confirm**. None has been confirmed yet. To change a value after it is confirmed, raise it with the owner. Do not edit it inside a spike or research note.

## Budgets

| ID | Budget | Proposed default | Status | Cited by |
|---|---|---|---|---|
| BUD-TTS | Time to safe | New photo "stored at home" within 24 h while the device is online and the homelab is up; median time to "sent" under 1 h on idle Wi-Fi | Proposed, owner to confirm | A3 (defines where it is measured), B2-S2, E3-S4 |
| BUD-BAT-D | Phone steady-state battery | < 2 % per day | Proposed, owner to confirm | B2-S2 |
| BUD-BAT-S | Seed battery cost | Report % per 10 GB; target set after A1-S1 | Proposed, owner to confirm; **target still to be set** (after A1-S1) | A1-S1, A2-S1 |
| BUD-TMP | Phone temp disk | ≤ 2 GB, and never push free space below 10 % | Proposed, owner to confirm | A2 (segment staging), A5-S3, B2, B6 |
| BUD-HASH | Hash + HMAC floor | First pass of a 128 GB library within one 6 h charge window on a low-end phone (≈ 6 MB/s effective, including I/O); stretch goal 50 MB/s compute | Proposed, owner to confirm | A1-S1 |
| BUD-DESK | Desktop agent | Idle RAM < 150 MB, idle CPU < 1 % average; background work < 25 % of one core | Proposed, owner to confirm | B1-S3 |
| BUD-SCAN | Metadata reconciliation | 500k files in < 5 min on a mid-range laptop at background priority | Proposed, owner to confirm | B5-S1 |
| BUD-INGEST | Homelab ingest | ≥ max(100 MB/s, 2 × home downlink) | Proposed, owner to confirm; needs the downlink figure from H2 | A6, A6-S2 |
| BUD-RESTORE | Restore | Single-file read from the store < 5 s; owner time per single-file request < 30 min; whole-device default set by A8-S3 | Proposed, owner to confirm; **whole-device default still to be set** (A8-S3) | C8-S3, A8-S3 |
| BUD-AUDIT | Fixity | Full app-level audit of 10 TB fits a monthly window without starving ingest | Proposed, owner to confirm | A6-S2, A7-S2 |
| BUD-CPU-REQ | Worker auth | Request-signature verification < 1 ms CPU | Proposed, owner to confirm | D3-S1 |
| BUD-REVOKE | Revocation | No new presigned URLs within 60 s; outstanding URLs expire within 15 min | Proposed, owner to confirm | D3, D3-S5 |
| BUD-RECOVERY | Break-glass | A non-author recovers 10 named photos from the doomsday kit in ≤ 2 h | Proposed, owner to confirm | D2-S3 |
| BUD-ENROLL | Kit enrollment | A relative enrolls a computer from the kit unaided in ≤ 20 min | Proposed, owner to confirm | E5-S3 |
| BUD-SUPPORT | Owner time | ≤ 2 h per month at steady state | Proposed, owner to confirm | C8, PLAN §3 |
| BUD-CLOUD | Monthly cloud cost ceiling | **Owner sets (H2)** | **No value yet**; blocks OD-14 | C4, C7-S3 |
| BUD-ABUSE | Worst-case abuse spend before auto-suspend | **Owner sets (H2)** | **No value yet**; blocks OD-14 | C2, C2-S2, C4-S1 |
| BUD-TEL | Telemetry | < 1 MB/day network and < 50 MB disk per device | Proposed, owner to confirm | B8-S3 |

## Owner confirmation (fill in at H2 intake)

| ID | Confirmed value | Confirmed on | Note |
|---|---|---|---|
| BUD-CLOUD | | | |
| BUD-ABUSE | | | |
| All other IDs | "as proposed" or a new value | | |

## Thresholds set inside spikes that overlap a budget

The plan asks spikes not to set their own thresholds. A few spikes still do, and these overlap an existing budget. The owner should decide at H2 whether each becomes a budget ID or stays local to its spike.

| Spike | Local threshold in PLAN | Overlapping budget | Suggested handling |
|---|---|---|---|
| E4-S2 | Phone scan of 50k items < 15 min and < 3 % battery; 500 GB home folder < 30 min | BUD-SCAN, BUD-BAT-D | Keep local (it measures discovery, not reconciliation) but state which budget it must also respect |
| A2-S1 | PQ: header ≤ 3 KB per object, ≤ 10 % throughput loss on a low-end phone | BUD-HASH, BUD-BAT-S | Keep local (it is the PQ decision rule for OD-06) |
| C7-S1 | Dead-man's-switch alert "within the window (e.g. 2 h)" | none | Candidate new budget (alert latency) |
| D4-S3 | Ransomware pause within 5 min and < 1 GB uploaded | BUD-ABUSE (cost bound) | Keep local; check it against BUD-ABUSE once that value exists |
| C8-S1 | Revoke from the owner's phone in < 5 min | BUD-REVOKE (propagation, not owner time) | Keep local; the two measure different things |

No other conflicts between the lens drafts are recorded here. The table in PLAN §2.0 already settles the ones that existed.
