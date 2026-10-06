# Spike A6-S3: crash consistency of the plain CAS store (CT half) + the `a6cas` prototype (THROWAWAY)

> **Throwaway spike code, not production code.** Workstream A6 (`docs/research/PLAN.md`, section "A6."). Input to ADR-0012: the knockout screen marks the CAS layout code as "new", so crash safety has to be shown, not assumed. `a6cas` is also the engine under test in A6-S4, A6-S5, A6-S6 and the A6-S2 bake-off kit.

- **Run by / date:** A6 spike runner (agent), 2026-10-06 (Wave 1, batch W1-b)
- **Exec tag:** CT/OL. This folder is the CT half. The OL half (a real VM power-off ×10) is the kit in `docs/research/kits/A6-S3/`.
- **Data class:** `SYN → results`:
  - corpus `a6cas gen -n 600 -dup 0.1 -scale 0.05 -seed 3`: 600 records, 535 unique contents, 229,295,536 bytes;
  - throwaway keys in `/dev/shm`.
- **Budget IDs:** none
- **Pass criterion (PLAN):** "No acknowledged item lost; nothing acknowledged before it is durable; store and catalog reconcile automatically." The PLAN asks for kill -9 ×100 and a VM power cut ×10 (LazyFS in a container).
- **Emulation label:** the "power cut" rows below are **emulated with LazyFS, not a real power cut.**

## The prototype (`a6cas/`, Go 1.26, `filippo.io/age` v1.3.1, `modernc.org/sqlite` v1.60.1)

**Layout ("REL-STORE-v0", written into each store as a self-description):**

```
blobs/<aa>/<bb>/<sha256>.age     one standard age v1 file per unique content; <sha256> = plaintext SHA-256
records/<rr>/<record_id>.age     each device-signed metadata record, also age v1
manifest/manifest.jsonl          append-only, fsynced; per object: stored_sha256, stored_size, h0
                                 (original device header), epoch, commit time
devices/devices.json             device registry (needed to re-verify record signatures without the catalog)
tmp/  quarantine/  LOCK
```

The OCFL variant (`-layout ocfl`) puts each blob into an OCFL 1.1 object under `ocfl/`, using storage layout extension 0003, with the object ID being the plaintext SHA-256 hex.

**Ingest, per item, in order.** The ACK is the receipt point (A3 F6):

1. decrypt and verify the record with the ingest key;
2. check the content header MAC against the signed `header_mac`;
3. stream-decrypt the content and check size, SHA-256 and dedup ID;
4. **rewrap the header** to {archive, recovery} (posture A′, see A6-S6);
5. write to `tmp/` (O_EXCL), then fsync;
6. rename into place, then fsync the directory (and fsync parents of new directories);
7. append the manifest line, then fsync;
8. archive the record the same way;
9. commit the SQLite catalog transaction;
10. print `ACK`.

Re-sent items that are already committed get `ACK … dup` (the stored-receipt path).

**Recovery** (`recover`, and also at ingest start):

- delete `tmp/`;
- truncate a torn last manifest line;
- **quarantine** any object file that has no manifest line (renamed but not yet committed; never ACKed);
- report catalog rows that have no store entry (this must be 0).

Incomplete items are then re-ingested from staging, because staging is deleted only after the ACK has been published (A3 F6 step 8).

**Other commands:**

- `audit` is keyless: it compares SHA-256 of stored bytes with the manifest;
- `get` restores one file by SHA-256 (archive key);
- `rebuild` and `export` are for A6-S4;
- `verify` is for A6-S6;
- `stage` is for the A6-S2 kit;
- crash-point injection uses `A6CAS_CRASHPOINT=<name>|any` and `A6CAS_CRASH_PROB`.

## Harness (`harness/`)

`crash.py` loops: start `a6cas ingest`, SIGKILL it after a random delay (or let it SIGKILL itself at a crash point), optionally tell LazyFS to drop all unsynced data, then run `recover` and check:

- **I1:** every item ACKed in this cycle is in the catalog and the manifest, and the keyless audit passes for every manifest entry.
- **I2:** no catalog row points at a missing store entry.

When all 600 items are in, it lets ingest finish and runs the keyed check:

- **I3:** every blob and record decrypts with the archive key **and** the recovery key to the expected SHA-256, signatures verify, and the catalog equals `truth.jsonl`.

It then starts a fresh store (a new "cycle").

**LazyFS** (github.com/dsrhaslab/lazyfs @ `fa7d32ee`, 2026-08-24; built from source with libfuse3 3.14 and a local spdlog v1.10.0 clone, because the CMake tarball download from github.com/archive returned 403):

- It holds file data in its own page cache until fsync. `lazyfs::clear-cache` drops every unsynced byte.
- The harness confirms each drop with a canary: an unsynced 8 KiB file must read back as 0 bytes. The FIFO completion handshake hung once, so the canary replaced it.
- **Limit (measured before the runs):** LazyFS drops unsynced *data* only. A rename or create done without a directory fsync still survives a clear-cache, so missing **directory** fsyncs are *not* detected here. The OL kit (real VM power-off) covers that.

## Results (measured; `evidence/`; final build after the A6-S4 lock fixes)

| Run | Store on | Crashes | How | Cycles finished (keyed check I3) | Iterations with an I1/I2 violation | Quarantined / temp removed / torn manifest lines repaired |
|---|---|---|---|---|---|---|
| `kill9-cas` | tmpfs | **100** | SIGKILL after 0.02–0.8 s | 8 (all 600/600, no FAIL) | **0** of 108 | 1 / 63 / 0 |
| `crashpoints-cas` | tmpfs | **100** | self-SIGKILL at 8 named points (p = 0.01 per point) | 1 (600/600, no FAIL) | **0** of 101 | 46 / 31 / 18 |
| `kill9-ocfl` | tmpfs | **100** | SIGKILL | 7 (all OK) | **0** of 106 | 1 / 58 / 0 |
| `crashpoints-ocfl` | tmpfs | **100** | crash points (incl. `ocfl-objdir-built`) | 1 (OK) | **0** of 101 | 38 / 37 / 14 |
| `lfs-kill9-cas` | **LazyFS** | **50** | SIGKILL, then clear-cache (emulated power cut) | 6 (all OK) | **0** of 56 | 0 / 28 / 0 |
| `lfs-crashpoints-cas` | LazyFS | **50** | crash points, then clear-cache | 0 (no cycle finished within 50 crashes; I1/I2 checked after each) | **0** of 50 | 19 / 17 / 8 |
| `lfs-kill9-ocfl` | LazyFS | **30** | SIGKILL, then clear-cache | 2 (all OK) | **0** of 32 | 1 / 20 / 0 |
| **`lfs-nofsync` (NEGATIVE CONTROL)** | LazyFS | 10 | as `lfs-kill9-cas`, but ingest with **every fsync disabled** | 2 (**both failed** I3: catalog had 569 and 574 of 600 correct) | **12 of 12** | 2,190 / 5 / 0 |

Crash-point hit counts (`crashpoints-cas`):

| Crash point | Hits |
|---|---|
| tmp-written-unsynced | 16 |
| tmp-synced | 11 |
| renamed-before-dirsync | 12 |
| renamed-before-manifest | 16 |
| manifest-torn | 18 |
| manifest-before-catalog | 5 |
| catalog-before-ack | 9 |
| after-ack | 9 |

In the crash-point runs, "acked 593 of 600" at cycle end is expected. Items whose ACK was lost (`catalog-before-ack`) were already committed and came back as `ACK … dup`, which the harness does not count. They are present in the catalog and in the truth check.

**Findings:**

- **(High, measured, container):**
  - Across 400 process kills and 130 emulated power cuts, no ACKed item was ever missing from the catalog or manifest, and no audit mismatch occurred.
  - Recovery needed no manual step: temp files were deleted, torn manifest lines truncated, uncommitted renames quarantined, and the remaining items re-ingested from staging.
  - Both layouts (plain CAS and OCFL) behaved the same.
- **(High, measured)** The harness can detect a durability bug. With fsync disabled, every iteration showed violations: ACKed items missing from the manifest, and catalog rows pointing at objects that were gone. So the clean runs are not a blind test.
- **(Medium)** The emulation does not cover:
  - lost directory entries (see the LazyFS limit above);
  - disk write caches and ZFS transaction groups;
  - SQLite on a real disk.

  These are the OL kit's job.
- **(High, measured, from A6-S4)** The layout is safe only with **one writer**. See `../A6-S4/README.md` for the two lock defects this work found and fixed.
- Throughput seen while testing (single-threaded ingest, tmpfs, shared 4-vCPU VM): 70–105 MB/s, varying between runs. **Not homelab evidence and not a BUD-INGEST result.** It does show that single-threaded ingest may be close to the 100 MB/s floor, so A6-S2 must measure it on real hardware.

## Pass / fail

**CT half: Pass** (emulated power cut, labelled as such). The real power-off (OL) is pending: `docs/research/kits/A6-S3/`.

## Rebuild and rerun

1. Build: `cd a6cas && go build -o ~/bin/a6cas .` (Go ≥ 1.25; the module asks for 1.26).
2. Make the corpus: `a6cas keygen -dir $D/keys && a6cas gen -out $D/corpus -keys $D/keys -n 600 -dup 0.1 -scale 0.05 -seed 3`.
3. Run `harness/run-tmpfs.sh kill9-cas crashpoints-cas kill9-ocfl crashpoints-ocfl`.
4. For the LazyFS runs, mount LazyFS with `harness/lazyfs.toml`:
   `lazyfs /dev/shm/lfs.mnt --config-path lazyfs.toml -o allow_other -o modules=subdir -o subdir=/dev/shm/lfs.root`
   (`user_allow_other` must be in `/etc/fuse.conf`). Then run `harness/run-lfs.sh`.
5. Clean up afterwards: delete `$D` and the LazyFS root.
