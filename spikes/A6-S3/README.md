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

## Disk-full fault case (added 2026-10-06, second runner pass)

**Why:** the A6 note asks for disk-full to be added to the fault cases, after Kopia #4348 ("possible to corrupt a repository when … the repository runs out of free space").

**Harness:** `harness/diskfull.py`. In each trial the store and/or the catalog sits on a size-limited filesystem, with the size drawn at random between 2 % and 98 % of a complete store. Each trial then:

1. ingests until the process fails by itself (no kill);
2. while the disk is **still full**, runs `recover`, checks I1/I2, retries ingest once, and checks again;
3. grows the filesystem, recovers, and ingests to the end;
4. runs the keyed check (I3: archive and recovery keys, plus the truth file).

Corpus, keys and binary are the same as above. The binary was rebuilt from the committed source with Go 1.26.0.

**Results** (measured; `evidence/s3-diskfull-*.jsonl` and `*.summary.json`):

| Run | Filesystem | What fills up | Trials | Where it failed (syscall) | `recover` while full ok | New ACKs on retry while full | I1/I2 violations | Finished and I3 OK | Repairs (quarantined / temp removed / torn manifest) |
|---|---|---|---|---|---|---|---|---|---|
| `same-cas` | tmpfs | store + catalog (one fs) | 30 | `write` temp object: 30 | 30/30 | 0 | **0** | 30/30 | 0 / 34 / 0 |
| `same-ocfl` | tmpfs | store + catalog, OCFL layout | 15 | `write` temp object: 15 | 15/15 | 0 | **0** | 15/15 | 0 / 12 / 0 |
| `ext4same-cas` | **ext4 on a loop device** (filler file takes the space) | store + catalog | 20 | `write` temp object: 19, `mkdir` of a `blobs/aa/bb` directory: 1 | 20/20 | 0 | **0** | 20/20 | 0 / 26 / 0 |
| `manfull-cas` | tmpfs; only `store/manifest/` is tiny | the append-only manifest | 20 | `write` to `manifest.jsonl`: 20 | 20/20 | 0 | **0** | 20/20 | 40 / 0 / 40 |
| `catfull-cas` | tmpfs; only the catalog's fs is tiny | SQLite catalog (`SQLITE_FULL`) | 15 | "database or disk is full": 15 | 13/15 (see below) | 0 | **0** | 15/15 | 0 / 0 / 0 |

**Findings:**

- **(High, measured, container)** In 100 disk-full trials, across all five placements:
  - no ACKed item was ever missing from the catalog or the manifest;
  - the keyless audit never mismatched;
  - nothing was ACKed while the disk stayed full;
  - every trial finished cleanly once space was freed.

  Repairs were automatic:
  - torn manifest lines, left by a short `write` at ENOSPC, were truncated (40 events);
  - blobs that had been renamed into place but had no manifest line were quarantined (40);
  - temp files were removed.

  The manifest-full run is the strongest case: in all 20 trials the object was already renamed into place when the manifest append failed.
- **(Medium, measured)** `recover` failed while full in 2 `catfull` trials. In both, the catalog filesystem (61 KB and 66 KB) was too small even for SQLite to create the empty schema. Ingest had therefore ACKed **0** items and stored nothing, so nothing could be lost. Lesson for ADR-0013: refuse to start ingest unless the catalog can open and has free-space headroom, rather than relying on recovery.
- **(Medium) Not covered:**
  - ENOSPC raised by `fsync` (delayed allocation) never happened here. Every failure came from `write` or `mkdir`, so the fsync error path is untested.
  - ZFS is copy-on-write. It keeps "slop" space, and when full it can fail even when asked to free space. Neither tmpfs nor ext4 behaves like that.

  Both gaps are now Part B of the OL kit: `docs/research/kits/A6-S3/diskfull-zfs.sh`, a file-backed throwaway pool, optionally natively encrypted. Its ZFS hooks are **untested**. The hook mechanism (`--placement external`) was smoke-tested with tmpfs hooks, 2 trials, no violations.

## Reproduction check (2026-10-06, second runner pass)

The binary was rebuilt from the committed source (`a6cas/`), and the corpus regenerated with the same seed. The generator gave the same totals as the first run: 600 records, 535 unique contents, 229,295,536 bytes. Shorter runs with new seeds, on tmpfs (`evidence/s3-repro-*`):

| Run | Kills | Iterations | Cycles finished (I3 OK) | I1/I2 violations | Quarantined / temp removed / torn |
|---|---|---|---|---|---|
| `repro-kill9-cas` (seed 161) | 30 | 35 | 5 (5/5) | **0** | 0 / 19 / 0 |
| `repro-crashpoints-cas` (seed 162; 8 crash points, all hit at least twice) | 30 | 30 | 0 | **0** | 14 / 10 / 5 |
| `repro-kill9-ocfl` (seed 163) | 20 | 21 | 1 (1/1) | **0** | 0 / 12 / 0 |

These agree with the first run. The LazyFS runs were not repeated: LazyFS is no longer built in this container.

## Pass / fail

**CT half: Pass** (emulated power cut, labelled as such; plus 100 disk-full trials on tmpfs and ext4). The real power-off and the ZFS disk-full run (OL) are pending: `docs/research/kits/A6-S3/`.

## Rebuild and rerun

1. Build: `cd a6cas && go build -o ~/bin/a6cas .` (Go ≥ 1.25; the module asks for 1.26).
2. Make the corpus: `a6cas keygen -dir $D/keys && a6cas gen -out $D/corpus -keys $D/keys -n 600 -dup 0.1 -scale 0.05 -seed 3`.
3. Run `harness/run-tmpfs.sh kill9-cas crashpoints-cas kill9-ocfl crashpoints-ocfl`.
4. For the LazyFS runs, mount LazyFS with `harness/lazyfs.toml`:
   `lazyfs /dev/shm/lfs.mnt --config-path lazyfs.toml -o allow_other -o modules=subdir -o subdir=/dev/shm/lfs.root`
   (`user_allow_other` must be in `/etc/fuse.conf`). Then run `harness/run-lfs.sh`.
5. Disk-full runs (root needed for `mount`):
   `python3 -I harness/diskfull.py --a6cas a6cas --corpus $D/corpus --keys $D/keys --base /dev/shm/a6df --full-bytes 236000000 --placement same|catfull|manfull|ext4same --layout cas|ocfl --trials N --seed S --evidence out.jsonl`
   Seeds used: same-cas 81, same-ocfl 82, catfull-cas 83, manfull-cas 84, ext4same-cas 85.
6. Clean up afterwards: delete `$D` and the LazyFS root, and unmount anything left under `/dev/shm/a6df`.
