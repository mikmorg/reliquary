# Kit A6-S2: storage-engine bake-off on the homelab (plain CAS vs OCFL vs restic)

- **Spike:** A6-S2 (workstream A6, see `docs/research/PLAN.md`, section "A6."). P1, Wave 2.
- **Exec tag:** OL (needs the homelab's real disks, pool and CPU; a cloud container cannot stand in for them).
- **Prepared by / date:** A6 spike runner (agent), 2026-10-06
- **Who runs it:** Owner
- **Time needed:** about 1 h hands-on. Machine time depends on corpus size and disks. Budget roughly one night for a 300 GB corpus: staging, three ingests, three full reads and restic's own backup and check.
- **Data-handling class:** `PUB+SYN → results`. The input is the H3 Tier L corpus (`docs/research/h3-research-data-governance.md` §6), not family data. The script writes **aggregates only** to `results/results.jsonl`. Any file names stay in `$WORK`. Keys are throwaway `SEC` test keys made inside `$WORK` and deleted at clean-up.

## Purpose

Measure, on the real homelab, the three storage designs that survived the knockout screen in `docs/research/a6-homelab-storage-engine.md` §F4:

1. **Plain CAS:** one standard age v1 file per unique content, at `blobs/<aa>/<bb>/<sha256>.age`. Headers are rewrapped at ingest to an offline archive key (posture A′).
2. **OCFL variant:** the same age files, each wrapped as an OCFL 1.1 object (layout extension 0003).
3. **restic:** the "proven engine" comparator, fed plaintext in batches of `BATCH` files per snapshot.

The plan's pass line is the same for each: ingest speed, single-file restore time, full-verify time extrapolated to 10 TB, and RAM. The kit also records storage overhead and catalog size.

## Hypothesis

The plain CAS meets BUD-INGEST, BUD-RESTORE and BUD-AUDIT with peak RAM far below 4 GB, because it has no engine index (the path is the hash). OCFL costs a few extra small files per object but behaves the same. restic meets the restore and RAM criteria at this corpus size, but per-file restore by SHA-256 needs our own map from hash to snapshot and path.

What a container smoke run showed (2026-10-06, synthetic 196 MB, tmpfs; **not evidence for any budget**): the harness runs end to end. The a6cas ingest is single-threaded, and it ran at about 70 MB/s on a shared 4-vCPU cloud VM. If the homelab shows the same, BUD-INGEST would need parallel ingest, which is a code change rather than a different engine. This kit measures it.

**Second smoke run (2026-10-06, second runner pass, tmpfs on a shared 4-vCPU cloud VM; not evidence for any budget):**

- **Run:** a6cas rebuilt from the committed source; corpus of 535 files, 229,295,536 bytes; `SAMPLES=10`, `BATCH=200`, `DROP_CACHES=0`.
- **Result:** the kit ran end to end, with rc 0 in 28 s, and `summarise.py` printed every block.

Figures, quoted only to show the harness works:

| Engine | Ingest (MB/s) | Keyless audit / check (MB/s) | Single-file restore, max (s) | Catalog rebuild | Peak RSS (MB) |
|---|---|---|---|---|---|
| CAS | 76.6 | 362.9 | 0.012 | byte-identical | 20.6 |
| OCFL | 60.2 | 342.1 | 0.011 | byte-identical | 18.8 |
| restic | 74.5 (backup) | 209.5 (`check --read-data`) | 0.868 (`dump`) | n/a | 162.2 |

The single-threaded ingest observation stands. On this VM it stayed below 100 MB/s.

## Decision it informs

| If the result is… | Then… |
|---|---|
| **Pass** for plain CAS: ingest ≥ BUD-INGEST; every single-file restore by SHA-256 < 5 s; full keyless audit extrapolated to 10 TB fits BUD-AUDIT's monthly window; peak RSS < 4 GB | ADR-0012 adopts the plain CAS of age objects (OCFL wrapper optional, decided on its overhead and on DR-A6-2). |
| **Fail on ingest speed only** | Parallelise ingest (several objects at once) and re-run; this does not change the engine choice. |
| **Fail on audit, restore or RAM** for the CAS while restic passes | Reopen posture C (restic via rustic_core) in the ADR, with the cost of its symmetric key and hash map. |
| **No result** | ADR-0012 stays Proposed with the container smoke figures marked "not homelab". Gate A can still close on the posture (OD-07) because the store layout is reversible (objects can be copied into another layout). |

## Budget IDs cited

BUD-INGEST, BUD-RESTORE (store read < 5 s), BUD-AUDIT. The RAM < 4 GB line is from PLAN A6-S2 (no budget ID). `summarise.py` takes the BUD-INGEST downlink figure as an argument. Do not invent thresholds here.

## Equipment

| Item | Exact model or version | Why | Have it? |
|---|---|---|---|
| The homelab host (or a VM or LXC on it) that will run ingest | Record CPU model, cores, RAM, Proxmox version | Real CPU and memory | |
| A dataset on the real pool, with at least 3 × the corpus size free | Record pool layout (mirror, raidz), disk models, recordsize, compression | Real disk throughput | |
| H3 Tier L corpus, 200–500 GB | `research/corpus-public` on the homelab (H3 §6) | Realistic bytes and size mix | |
| Go ≥ 1.25 (to build a6cas and restic) | | Builds | |

**Software and files needed:**

- `a6cas` from `spikes/A6-S3/a6cas/` (throwaway spike code): `cd spikes/A6-S3/a6cas && go build -o ~/bin/a6cas .`
- restic 0.19.1: `GOBIN=~/bin go install github.com/restic/restic/cmd/restic@v0.19.1`
- Optional: `pip install ocfl-py==2.1.0`, which gives `ocfl-validate.py` for the OCFL store.
- `python3`, `sha256sum`, `find`, `xargs`, `split` (standard on Debian and Proxmox).
- This folder: `bakeoff.sh`, `measure.py` (wall time and peak RSS, no GNU time needed), `summarise.py`.

## Before you start

- [ ] Note the home downlink speed in Mbit/s (from H2 intake or a speed test). BUD-INGEST needs it.
- [ ] Create the work dataset, for example `zfs create -o recordsize=1M -o compression=lz4 tank/a6-bakeoff`. Record the properties you used.
- [ ] Make sure nothing else heavy runs on the pool (no scrub, resilver or backup) during the run.
- [ ] Run as root if you want cache drops (`DROP_CACHES=1`, the default). Otherwise set `DROP_CACHES=0` and say so in the results.

## Procedure

1. Build the tools (see above) and put them on `PATH`. **You should see:** `a6cas` prints a usage error, and `restic version` prints 0.19.1.
2. Start the run inside `tmux` or `screen` so it survives a disconnect:
   `CORPUS=/tank/research/corpus-public WORK=/tank/a6-bakeoff ./bakeoff.sh`
   **You should see:** time-stamped lines for stage, then ingest, audit, single-file restores and catalog rebuild for `cas` and `ocfl`, then the restic steps.
3. When it prints `done`, run `python3 summarise.py /tank/a6-bakeoff/results/results.jsonl <downlink Mbit/s>`. **You should see:** one block per engine with PASS/FAIL lines.
4. Optional, cold restores: reboot (or export and import the pool), then re-run only the restores with `ENGINES=cas SAMPLES=50 ./bakeoff.sh`. Staging is reused.
5. Paste the `summarise.py` output and `results/results.jsonl` into the results section below. They hold only counts, bytes, times and RSS.

**Stop and record "No result" if:** the pool has less than 3 × corpus free space, or another job starts using the pool.

## Cleaning up

1. `zfs destroy tank/a6-bakeoff`, or `rm -rf $WORK`. This deletes the throwaway keys, stores, restic repository and the hash-to-path map.
2. Keep only `results.jsonl`, `run.log` and the summary.

## Data handling

H3 rules apply (`docs/research/h3-research-data-governance.md` §2–§4):

- The corpus is PUB+SYN.
- The script never prints file names into `results.jsonl`.
- `run.log` contains time stamps and the a6cas summary lines only.
- Do not paste `restic/map.txt`, `ingest.out` or `stage/` contents anywhere.

## Results

Copy this section into `docs/research/kits/A6-S2/results.md` and fill it in. Do not edit numbers afterwards; add a note instead.

- **Run by / date / place:**
- **Hardware and OS actually used:** CPU, RAM, pool layout, disk models, dataset properties, kernel, ZFS version
- **Emulator or VM used instead of real hardware?** No | Yes: (for example "LXC on the homelab host")
- **Corpus:** files, bytes, unique bytes (from `results.jsonl`)

| Engine | Ingest MB/s (unique bytes) | Peak RSS MB | Store bytes / overhead % | Files in store | Catalog bytes | Audit MB/s → hours for 10 TB | Single-file restore p50 / p95 / max s | Rebuild byte-identical |
|---|---|---|---|---|---|---|---|---|
| plain CAS | | | | | | | | |
| OCFL | | | | | | | | |
| restic (`check --read-data`, `dump`) | | | | (pack files) | n/a | | | n/a |

| Pass criterion | Budget ID | Measured value | Pass / Fail / No result |
|---|---|---|---|
| Ingest ≥ max(100 MB/s, 2 × downlink) | BUD-INGEST | | |
| Single-file restore by SHA-256 < 5 s | BUD-RESTORE | | |
| Full verify of 10 TB fits a monthly window without starving ingest | BUD-AUDIT | | |
| RAM < 4 GB | (PLAN A6-S2) | | |

- **Overall:** Pass | Fail | No result
- **Surprises and points of confusion:**
- **Follow-ups for the workstream:**
