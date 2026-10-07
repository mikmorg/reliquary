# Spike A3-S1: model check of the v0 ingest protocol (THROWAWAY)

> **Throwaway research models, not production code.** Workstream A3 (`docs/research/PLAN.md`, section "A3."). This spike is input to ADR-0009 and `docs/spec/ingest-protocol.md`. It checks the protocol drafted in `docs/research/a3-ingest-protocol.md` §F1–F7 (the "analyst design", called **v0** here) against the invariants in that note's "Spikes" section, using two independent models:
>
> - **Run A:** a Rust explicit-state model. It does exhaustive BFS, checks AG EF liveness, and cross-checks its state counts with Stateright 0.31.0.
> - **Run B:** a TLA+ specification checked by TLC, with LTL liveness under weak fairness.

- **Run by / date:** A3 spike runner (agent), 2026-10-06 (Wave 1, batch W1-b).
  - The Rust model was written earlier the same day by a previous spike-runner session that did not publish it.
  - This session rebuilt it and re-ran every suite from the same sources (SHA-256 below); the results reproduced exactly.
  - The TLA+ model was written in this session.
- **Exec tag:** CT, run for real in the cloud container: 4 vCPU x86-64, 15 GB RAM, OpenJDK 21.0.10, rustc/cargo 1.94.1.
- **Data class:** `SYN → results`. The models contain no data at all.
- **Budget IDs:** none apply. The models have no wall-clock time, so BUD-TTS cannot be measured here: a model state says nothing about hours. Timers (lease TTL, the 24 h valve, the 7-day abort, the orphan grace period) are nondeterministic events.
- **Hypothesis (PLAN):** with 3 devices × 3 items, bounded crashes, dropped or duplicated messages and the homelab offline, these invariants hold:
  - no staged object is deleted before a durable commit;
  - every claimed item is eventually committed or re-claimable;
  - "safe" is shown only with a valid receipt;
  - dedup never merges different plaintexts.

  Every counterexample is to be fixed in the spec.
- **Decision informed:** ADR-0009, specifically the state table, the invariants and the orphan-handling rule. It also feeds OD-04 (via DR-A3-1), SR-10 and SR-11 in `docs/security/threat-model.md`, and the G2 invariant table.

## Result

**Verdict: pass for v1 (the analyst design plus two fixes); fail as written for v0.** Every counterexample has a proposed spec fix.

What the two models showed:

1. **The analyst design (v0) breaks a strengthened invariant.** The device sends its record *after* Complete, and the homelab GCs staged objects that have no record (F7). Both models found the same 4-step trace with **no fault and no attacker**: a slow device's completed object is orphan-GC'd just before its record arrives (Run A E1/E2: "I1-strong"; Run B: I7, 41 states).
   - I1 as worded still holds, because the deleted object counts as an "orphan".
   - Liveness also holds (the valve recovers), but the cost is a full re-upload, and the item is lost if the source is gone (T-22/AR-09).
   - **Fix (v1): record-first Complete.** The Worker writes the signed record to `meta/` before completing the multipart upload. Orphan GC goes away, and a record whose upload is gone gets the typed reject `content-missing`.
2. **v1 passes the checks that completed.**
   - Exhaustive safety for every fault class together (budget 1), 2 devices × 1 item: TLC, 7.9 M states.
   - Run A, up to 38.6 M states. Configurations: 3 devices × 1 item; 2 devices with 2 faults; a poisoner; D1 wipe; a Worker that lies.
   - LTL liveness L1–L4 under weak fairness for each of the 10 v1 fault classes separately (TLC).
   - AG EF liveness for every Run A configuration.
   - 3 × 3: 1.2 M random runs (Run A), plus a bounded BFS (Run B: 35 M states to depth 18, no violation). Exhaustive 3 × 3 did not finish in this container, and the larger TLC runs (3 × 1, and budget 2) were stopped at 25 min with no violation.
3. **F-B1, the self-lease rule (Run B).** After a device loses its journal, the Worker must not answer IN_FLIGHT to the device that holds the live lease. Otherwise the device sends a dedup-hit record and waits on its own dead upload until the lease expires. That is a delay and a wasted attempt, not a safety issue. Run A had assumed this rule ("lease held by *another* slot") without stating it, so the spec must state it.
4. **Mutants: every deliberately broken variant was caught** (7 in Run A, 11 in Run B). The tests that make the design work are:
   - verification before put (I3);
   - no deletion before archive/commit (I1);
   - no Expiration rule on `staging/` (I1);
   - storing the receipt before publishing it (I4);
   - never treating COMMITTED / IN_FLIGHT / "staged" as safe (I2);
   - the valve or re-check (L1);
   - reconciliation by listing rather than relying on the queue (L1, with only queue drops);
   - republishing receipts from home after a D1 rollback (L1).

**Against the PLAN pass criteria:**

| Criterion | Result |
|---|---|
| No staged object deleted before a durable commit | holds (I1) in v0 and v1. v0 needs the stronger I7, which only v1 meets. |
| Every claimed item eventually committed or re-claimable | holds (L2, Run B; AG EF goal, Run A) |
| "Safe" only with a valid receipt | holds (I2) |
| Dedup never merges different plaintexts | holds (I3), including with a poisoner and with corrupted bytes |
| Every counterexample fixed in the spec | v0 → v1 (record-first Complete, `content-missing` reject, no orphan GC); F-B1 (self-lease). Both are recommended to ADR-0009. |

## What is modelled

Both models describe the same objects and actions:

- **Devices:** each holds items. Each attempt of a device for an item is one record, with at most one upload under its own staging key.
- **Worker + D1:**
  - advisory leases;
  - typed answers MISSING / IN_FLIGHT / COMMITTED, where COMMITTED requires a relayed receipt for the content;
  - receipt relay and commit marks, which are a cache.
- **R2:** multipart uploads in progress, staged objects, `meta/` record objects.
- **Queue:** at-least-once hints that can be lost.
- **Homelab:**
  - durable inbox;
  - verify + `put_blob` → archive record and store the receipt → publish → delete staging;
  - reconciliation by listing `meta/`, plus republishing receipts and marks.

| Fault or nondeterminism | Run A (Rust) | Run B (TLA+) |
|---|---|---|
| Lost responses (begin, complete, record) | counted fault | `lostresp` (Complete) |
| Worker crash between the record write and Complete (v1) | counted fault | not modelled separately |
| Device loses its upload journal and restarts | `DeviceReset` | `devcrash` |
| Device killed for good | — (AG EF: a device may stop acting) | `kill` |
| 7-day abort hits a live upload | `AbortLive` | `abort` |
| R2 loses a staged object | — | `r2loss` |
| Corrupted or poisoned bytes | a poisoner device uploads BAD bytes under a valid dedup ID | `bad` |
| D1 rollback or wipe | `D1Wipe` (whole cache) | `rollback` (one fact per fault: relay entry, commit mark, row reverted to `claimed` with a live lease, or row reverted to `staged`) |
| Worker lies "IN_FLIGHT" | counted fault | — (D1-S2 covers a malicious Worker) |
| Queue hint dropped (retention 24 h / 4 d / 14 d, `max_retries`, 5 % loss) | unbounded | unbounded, never fair |
| Duplicate hints | idempotent inbox | idempotent inbox (set semantics) |
| Homelab offline | homelab steps are never forced (AG EF) | `down` (volatile progress lost), then `Up` (fair) |
| Homelab crash mid-ingest | each step is durable and atomic | `homecrash` (volatile step counter reset) |
| Orphan GC racing a slow device (v0 only) | homelab action | `gcrace` |
| Valve fires while the item was still progressing | — | `spurious` |

**Invariants** (names follow `a3-ingest-protocol.md` "Spikes"):

| ID | Meaning | Run A | Run B |
|---|---|---|---|
| I1 | A staged or record object is deleted only after a durable commit (blob + archived record), a durable rejection, or as a no-record orphan | `I1` | `I1_NoDeleteBeforeCommit` |
| I1-strong / I7 | **New:** the homelab never deletes (GCs) a staged object whose record arrives later (no "dangling record") | `I1-strong` | `I7_NoDanglingRecord` |
| I2 | "safe" on a device ⇒ it holds a receipt ⇒ blob durable and its record archived | `I2` | `I2_SafeOnlyWithReceipt` |
| I3 | Dedup never merges different plaintexts | `I3` | `I3_NoFalseMerge` |
| I4 | At most one distinct receipt per record | `I4` | `I4_OneReceiptPerRecord` |
| I5 | No lease, queue or D1 state is needed for I1–I4 | by modelling D1 wipe, Worker lies and hint loss | by modelling D1 rollback and hint loss |
| I6 | The relay holds only homelab-signed receipts (relay ⊆ archived) | `I6` | `I6_RelayIsCache` |
| L1 | Every live holder eventually reaches "safe" | AG EF goal (from every reachable state, a fault-free continuation reaches "all safe + R2 clean") | `L1_EventuallySafe` (LTL under weak fairness of honest actions) |
| L2 | Every claimed item ends committed or re-claimable | inside the AG EF goal | `L2_CommittedOrReclaimable` |
| L3 | No orphans after reconciliation (staging and multipart drain; consumed records) | inside the AG EF goal ("R2 clean") | `L3_Drains` |
| L4 | The Worker's cache converges after rollback | — | `L4_CacheConverges` |

## Designs checked

- **v0:** the analyst design as written. The device sends its record *after* Complete. The homelab garbage-collects completed staging objects that have no record after a grace period (F7).
- **v1:** the same design with one change, **record-first Complete**:
  - The Complete call carries the signed record, and the Worker writes `meta/` *before* completing the multipart upload. A completed staging object therefore always has a record, and orphan GC is removed.
  - A record whose upload is gone (no multipart upload and no object, checked multipart first) gets the typed reject `content-missing`, and the device re-uploads.
  - Run B also adds the **self-lease rule** (F-B1 below).

<!-- results sections below are filled in after the runs -->

## Run A: Rust explicit-state model (`rust/`)

- **Build:** `cargo build --release` in `rust/`. Stateright 0.31.0 is a dependency, used only for the cross-check (`Cargo.lock` is pinned).
- **Source SHA-256:**
  - `src/main.rs`: `95ca4f40dc1fe24caba4ebdc6ab9629d86741f0be61c5519af8606800f16ca65`
  - `src/model.rs`: `1de8e76140c640c0ff3b60dc86878100c72184e03cfc7b3f1e94fb0f0562d0db`
- **Commands:** `a3s1-model variants | mutants | xcheck --stateright | indep | v1`, and `a3s1-model sim <honest> <items> <att> <faults> <poisoner> 200000 300 <seed> --v1|--nogcfix`.
- **Evidence:**
  - `evidence/rust-suites-rerun-2026-10-06.txt` holds the full output, including counterexample traces.
  - `evidence/rust-sim3x3-rerun-2026-10-06.txt` holds the 3 × 3 simulations.
- **Reproducibility:**
  - Every state count and verdict below came out identical in the earlier session's output and in this session's re-run.
  - Stateright's BFS found the same number of unique states as the custom checker in all three cross-check runs.
- **Symmetry:** reduction over identical devices is on unless a run says "no symmetry".

**Liveness method.** "AG EF goal" means that from every reachable state (faults included), some continuation with no further faults reaches the goal. The goal is: every honest device SAFE, R2 `staging/`, `meta/` and multipart uploads empty, and every receipt relayed.

**Bound artifacts.** "Attempt-exhausted" states, where a slot used all its bounded attempts, are counted and reported separately. They are a model bound, not a protocol result.

| Run | Design | Configuration | States | Time | Safety | Liveness (AG EF) |
|---|---|---|---|---|---|---|
| E1 | v0 | 1 honest + poisoner, att ≤ 2, faults ≤ 1 | 1,860,254 | 2.8 s | **I1-strong violated** (trace below); I1–I4, I6 hold | holds |
| E1 | v0 | 2 honest | 1,043,879 | 2.7 s | **I1-strong violated** | holds |
| E2 | v0 + typed `content-missing` reject for GC'd objects | 1 honest + poisoner | 3,146,758 | 5.5 s | **I1-strong violated** | holds |
| E2 | same | 2 honest | 1,856,453 | 5.1 s | **I1-strong violated** | holds |
| E3 | **v1** | 1 honest + poisoner | 424,298 | 0.6 s | all hold | holds |
| E3 | **v1** | 2 honest | 183,511 | 0.4 s | all hold | holds |
| E3b | **v1** | 2 honest + poisoner (1 attempt) | 6,072,717 | 20.7 s | all hold | holds |
| E4 | **v1** | 3 honest × 1 shared item, att ≤ 2, faults ≤ 1 | 19,843,663 | 143.9 s | all hold | holds |
| E5 | **v1** | 2 honest × 1 item, att ≤ 3, faults ≤ 2 (lost responses off) | 38,646,964 | 181.5 s | all hold | holds |
| E6 | **v1** | 1 honest + poisoner (1 attempt), att ≤ 3, faults ≤ 2 | 1,465,227 | 2.7 s | all hold | holds |
| E7 | **v1** | 1 honest, att ≤ 4, faults ≤ 3 | 924,603 | 1.4 s | all hold | holds |
| X1–X3 | v1 / v0 / v1, no symmetry | as E3 / E1 / E3 | 424,298 / 1,860,254 / 366,834 | — | as above | Stateright `unique_states` equal in all three |

**Item independence** (`indep`). In multi-item models, every transition except a D1 wipe changes the state of at most one dedup ID. Results:

- 1 honest × {A, B}: 196,056 states, 1,078,892 transitions, 0 touching more than one ID.
- 1 honest × {A, B} + a poisoner × {B}: 4,349,624 states, 27,752,540 transitions, 0 touching more than one ID.

This is the argument for why the per-item results above carry over to N items. A D1 wipe touches several IDs, but it is a fault after which the per-item argument applies again.

**Random simulation, 3 × 3** (not exhaustive). Each configuration ran 200,000 runs of up to 300 random steps, each followed by a fault-free continuation of up to 4,000 steps:

| Configuration | Design | Safety violations | Goal reached / not reached / attempt-exhausted |
|---|---|---|---|
| 3 honest × 3 items, att 3, faults 2 | v1 | none | 200,000 / 0 / 0 |
| 2 honest + poisoner × 3 items, faults 2 | v1 | none | 200,000 / 0 / 0 |
| 3 honest × 3 items, faults 3 | v1 | none | 199,988 / 0 / 12 |
| 2 honest + poisoner, faults 3 | v1 | none | 199,995 / 0 / 5 |
| 3 honest × 3 items, faults 2 | v0 | **I1-strong in 175,069 runs** | 196,008 / 0 / 3,992 |
| 2 honest + poisoner, faults 2 | v0 | **I1-strong in 175,595 runs** | 178,996 / 0 / 21,004 |

**Mutants** run against v1 (1 honest + poisoner, att ≤ 2, faults ≤ 1). Each mutant must be caught; the M0 control (unmodified v1) must pass.

| Mutant | Caught by |
|---|---|
| M1 homelab skips SHA-256/HMAC verification | I1, I2, I3 |
| M2 staging deleted before durable commit | I1 |
| M3 a dedup hit (IN_FLIGHT / COMMITTED) shown as safe | I2, plus liveness (385 states cannot reach the goal) |
| M4 queue-only ingest (no reconciliation listing), hints droppable | liveness (161,170 states cannot reach the goal). The M4 control, queue-only with hints never dropped, holds. |
| M5 no re-check and no safety valve | liveness (211 states) |
| M6 receipts published once, never republished | liveness (30,936 states) |
| M7 receipt re-signed on redelivery | I4 |

**Counterexample for v0 (Run A, E1).** Reproduced by Run B (I7, 41 states) and by the v0 simulations.

1. dev0 checks and begins an upload of A.
2. dev0 uploads its parts and completes them. The staging object now exists, but the device has **not yet sent its record**.
3. The homelab orphan-GCs the staging object, because it has no record and the grace period has elapsed.
4. dev0 sends its record, which points at content that no longer exists.

The device then sits "awaiting" until its valve fires and it uploads the whole file again. If the source was deleted in the meantime, the item is lost. That is the D1 register's T-22/AR-09 case, here reached with **no attacker and no fault**, only a slow device. The typed `content-missing` reject (E2) shortens the wait but does not remove the race.

## Run B: TLA+ / TLC (`tla/`)

- **Tool:** TLC2 Version 2.19 of 08 August 2024 (rev: 5a47802), the stable release `tla2tools.jar` v1.7.4, downloaded 2026-10-06 from `https://github.com/tlaplus/tlaplus/releases/download/v1.7.4/tla2tools.jar` (SHA-256 `936a262061c914694dfd669a543be24573c45d5aa0ff20a8b96b23d01e050e88`). The jar is not committed.
- **Run settings:** 4 workers, `-deadlock` (terminal "all done" states are legitimate), `-lncheck final` (added after the first two sweep runs), and the state queue on `/dev/shm`.
- **Spec:** `tla/Ingest.tla`, 446 lines, SHA-256 `5e05a1eaf46b3a5fc6a90e244ed813b62b1e73c5485641a6cf28c6598ea1c99d`.
- **Runner:** `tla/run.py` writes an `MC_*.tla` / `.cfg` pair per configuration. It takes a set of enabled fault classes and **one shared fault budget** (`--max-faults`). The `batch*.sh` files are the exact command lists.
- **Fairness:** every honest action (device, homelab, lease expiry, lifecycle abort of abandoned parts, `Up`) is weakly fair. Faults and queue drops are never fair.
- **The valve:** it is modelled as fair only when the item is *stuck*, meaning nothing already in the system will produce this device's receipt. Firing early is the separate `spurious` fault.
- **SlotsSuffice** is a model-adequacy invariant: a live device never runs out of attempt slots while stuck. With K = 2 it fails even without the self-lease bug: d2's hit, lease expiry, re-check, a new upload, then a crash. So K = 3 is used for every liveness run.
- **"Incomplete"** means TLC was stopped at the per-run time limit. The figures given are from the last progress report before the stop; no violation had been found by then.

### Proposed design (v1), configuration "2x1" (two devices hold the same item: the A3-S2 scenario), K = 3, fault budget 1

| Enabled fault class | Distinct states | Depth | Time | Safety I1–I4, I6, I7 | Liveness L1–L4 |
|---|---|---|---|---|---|
| none (lease expiry and unbounded queue drops only) | 28,756 | 31 | 18 s | pass | **pass** |
| `kill` (one device dies for good) | 93,698 | 32 | 62 s | pass | **pass** |
| `lostresp` | 567,560 | 41 | 259 s | pass | **pass** |
| `homecrash` | 84,320 | 33 | 35 s | pass | **pass** |
| `down` (homelab offline; queue drops meanwhile) | 92,716 | 33 | 34 s | pass | **pass** |
| `abort` (7-day abort hits a live upload) | 1,199,442 | 43 | 591 s | pass | **pass** |
| `bad` (corrupted or poisoned bytes) | 1,372,056 | 40 | 696 s | pass | **pass** |
| `rollback` (D1 rollback, one fact) | 311,084 | 33 | 140 s | pass | **pass** |
| `spurious` (valve fires early) | 1,072,860 | 40 | 540 s | pass | **pass** |
| `r2loss` | 1,550,304 | 41 | 737 s (re-run with a 2,400 s limit; the first try stopped at 700 s) | pass | **pass** |
| `devcrash` (journal lost, restart) | 3,459,668 | 43 | 2,199 s | pass | **pass** |
| **all 11 classes, budget 1, safety only** | **7,916,780** | 43 | 282 s | **pass (complete)** | — |
| all classes, budget 2, safety only | ≥ 53,398,548 at BFS depth 21 | — | stopped at 1,500 s | no violation found | — |
| "3x1" (3 devices, 1 item), all classes, budget 1, safety | ≥ 43,936,169 at depth 20 | — | stopped at 1,500 s | no violation found | — |
| "3x3ring" (3 devices × 3 items, each item on 2 devices), K = 2, no faults, safety | ≥ 35,475,653 at depth 18 | — | stopped at 1,500 s | no violation found | — |

`gcrace` is not in the per-class sweep because v1 has no orphan GC, so the class enables nothing there.

The 3 × 3 configuration with faults was started and then stopped by hand after 30 s, so it has no result. Exhaustive 3 × 3 checking is out of reach for TLC on this machine. The 3 × 3 evidence is therefore:

- Run A's random simulation (above);
- the bounded 3x3ring BFS above;
- the item-independence check (Run A), which reduces N items to 1.

### Analyst design (v0), "2x1", K = 3, fault budget 1

| Run | Distinct states | Result |
|---|---|---|
| `gcrace` enabled, all invariants | 41 | **I7_NoDanglingRecord violated** (trace: Start, Complete, OrphanGCRace, SendRecord). This is the same counterexample as Run A E1. |
| `gcrace` enabled, I7 removed, full liveness | 1,546,143 | I1–I4, I6 and **L1–L4 pass**: the valve recovers. The race costs a re-upload and a valve wait; it does not livelock. |
| no faults, full liveness | 30,455 | pass |

### Mutants (every one must fail; all did)

| Mutant (`--bug`) | Fault classes | Caught by | States to the counterexample |
|---|---|---|---|
| `no_verify` (homelab skips verification) | `bad` | I3 | 105 |
| `delete_on_pull` (delete staging when the hint is pulled) | none | I1 | 21 |
| `delete_before_archive` | none | I1 | 82 |
| `staging_expiry` (an Expiration lifecycle rule on `staging/`) | none | I1 | 31 |
| `resign_receipt` (re-sign on redelivery) | `homecrash` | I4 | 867 |
| `safe_on_committed_answer` (COMMITTED answer shown as safe) | none | I2 | 349 |
| `safe_on_staged` (v0: "staged" shown as safe) | none | I2 | 28 |
| `no_valve` (no re-check, no valve) | `r2loss` | L1 (Start, Start, Complete, Pull, Pull, R2Loss, IngestA → content-missing, IngestD, then stuttering) | 6,076 |
| `no_reconcile` (queue-only ingest) | none: a single queue drop suffices | L1 (Start, Start, Complete, Pull, QueueDrop, then stuttering) | 1,813 |
| `no_republish` (relay and marks never rebuilt from home) | `rollback` | L1. A rollback drops d1's relayed receipt after staging is deleted. d1's record is archived, so it is not "stuck" and its valve never fires; d1 waits for ever. | 188,644 |
| `self_lease` (the Worker answers IN_FLIGHT to the lease holder itself) | `devcrash` | with K = 2: SlotsSuffice at depth 4 (Start, DevCrash, Start → dedup hit waiting on its own dead lease). With K = 3: no violation in 1,500 s. It is a delay up to the lease TTL plus a wasted attempt, not a livelock. | 21 |

## Limits (read before citing)

- **Abstraction, not code.** The models check the protocol *design*. The A0 harness (A3-S2, Wave 2) and G2's deterministic simulation must check the implementation.
- **No time.** Nothing here measures or bounds BUD-TTS, the lease TTL, the 24 h valve or the 7-day abort. They are ordering-only events. "Liveness holds" means *eventually*, not *within 24 h*.
- **The valve is an oracle.** In Run B the valve fires fairly only when the item is stuck, judged from global state. A real device sees only a timer. Firing early is covered by the `spurious` fault. Firing late, or never (a device with no timer), is the `no_valve` mutant, which fails.
- **Bounded:**
  - Small device and item counts.
  - At most 3 attempts per device per item (K = 3) for TLC liveness.
  - Fault budgets of 1–3.
  - Larger TLC runs were stopped with no violation found. That is evidence, not proof.
  - Run A's item-independence check is the argument for scaling to many items. Nothing scales the device count beyond 3.
- **Not modelled:**
  - a malicious or lying Worker beyond IN_FLIGHT lies (D1-S2 covers this);
  - forged receipts and a compromised ingest VM (AP8, D4);
  - USB transport and receipts across both paths (A4-S3);
  - metadata-only records (tombstones, renames);
  - segment checkpoints for slow uploads (A3-S3);
  - the record-batch format;
  - two homelab ingest workers racing each other (A6-S4 tested this on the store side).
- **Simplified atomicity.**
  - In Run B the Worker writes the record and completes the upload in one step. Run A splits this with a "Worker crash after record write" fault.
  - The `content-missing` check reads "no multipart upload, no object" atomically. In reality the homelab must check the multipart upload first, then the object. Otherwise an upload that completes between the two reads would be rejected wrongly.
- **The two models differ on one point.** Run B treats a `staged` D1 row as IN_FLIGHT (SR-10(b): staged claims never time out). Run A answers IN_FLIGHT only for a live lease. Both pass, so the choice is about efficiency, not safety.

## Files

- `rust/`: Run A source (`cargo build --release`). The binary and `target/` are not committed.
- `tla/Ingest.tla`: Run B spec.
- `tla/run.py`: MC generator and runner (needs `tla2tools.jar` v1.7.4 at `../tools/` or `$TLA2TOOLS`).
- `tla/batch*.sh`: the exact run lists.
- `evidence/rust-*.txt`: Run A output.
- `evidence/tlc/summary.jsonl`: one line per TLC run.
- `evidence/tlc/*.log`: full TLC output, including every counterexample trace. The first entries in `summary.jsonl` come from development runs before the self-lease rule was added. Rows in this README cite only runs of the final spec.
