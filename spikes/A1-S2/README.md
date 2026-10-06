# Spike A1-S2: dedup-secret rotation over a 1M-entry client cache (THROWAWAY)

> **Throwaway spike code, not production code.** Workstream A1 (`docs/research/PLAN.md`),
> input to ADR-0006 (ID-side rotation mechanics; D2 owns custody and the rotation trigger).
> Measured on **one shared x86 cloud VM** under heavy CPU contention. No phone and no homelab
> hardware was used.

- **Run by / date:** A1 spike runner (Wave 1, batch W1-b), 2026-09-29
- **Exec tag:** CT
- **Data class:** `SYN → results`. Synthetic cache rows point at paths that do not exist, and the digests are synthetic.
- **Pass criterion (PLAN):** "HMAC over SHA-256 rotates in < 60 s on the client with zero file reads and in < 24 h at the homelab. Record the full re-read cost of the content variant." No budget ID applies. The re-read cost is compared with BUD-HASH.

## Construction exercised

Candidate B from `spikes/A1-S3`:
`dk_e = HKDF-SHA256(ikm = K_e, salt = empty, info = "reliquary/v1/dedup-key/sha256-digest")`, `id = HMAC-SHA256(dk_e, SHA-256(content))`.
Rotating to epoch e+1 reads each row's cached SHA-256 and writes a new `(dedup_epoch, dedup_id)`. The content variant (candidate A, `HMAC(dk_e, content)`) has to re-read every file.

The cache is a SQLite table (rusqlite 0.40.2, bundled SQLite, WAL mode, `synchronous=NORMAL`) with columns `source_locator, size, mtime_ns, ctime_ns, inode, sha256, dedup_epoch, dedup_id`. 1,000,000 rows take 152 MB.

## Results (measured)

| Run | Rows | Wall s | CPU s | Notes |
|---|---|---|---|---|
| rotate e0→e1, in place, one transaction, under `strace` | 1,000,000 | 5.62 | 2.19 | See "zero file reads" below |
| rotate e1→e2, in place | 1,000,000 | 4.98 | 2.01 | |
| rotate e2→e3, **map mode** (keeps the old ID and writes an `old_id → new_id` table) | 1,000,000 | 6.07 | 2.85 | DB grew from 152 MB to 230 MB |
| rotate e3→e4, in place, straight after `drop_caches` (cold DB) | 1,000,000 | 5.86 | 3.52 | 168 MB read from disk |
| rotate e4→e5, e5→e6, in place | 1,000,000 | 3.70, 3.22 | 2.11, 2.04 | |
| derivation only, in memory (no DB) | 1,000,000 | 0.191 | | 5.2 M IDs/s |
| derivation only, in memory (no DB) | 5,000,000 | 1.532 | | 3.3 M IDs/s |

Every rotation passed a spot check that recomputed one row's ID independently.

**Zero file reads:** `evidence/strace-rotate-inplace.txt` traces every `openat`/`stat` call of the first rotation. The only files opened were the dynamic loader and libc, `/proc/self/*`, the database with its `-wal` and `-shm` files and directory, and `/dev/urandom` (opened by SQLite). None of the 1,000,000 cached source paths was opened or stat'ed (`grep -c nonexistent` gives 0). The paths do not exist, so a read attempt would also have failed the run.

### Content variant: re-read cost (construction A, `HMAC(dk_new, content)`)

| Input | Runs | Result |
|---|---|---|
| 50,000 files × 4 KiB, guest cache dropped before each run | 5 | 13.7, 16.2, 118.9, 106.2, 113.2 µs per file. The first two runs are suspiciously fast and may not have been cold. |
| One 1 GiB file, guest cache dropped | 5 | 114, 536, 92, 729, 508 MB/s (median 508). The spread comes from CPU contention on the VM. |

## Reading against the pass criterion

- **Client, digest variant:** 1M entries rotated in 3.2–6.1 s with zero source-file reads. That is under 60 s **on this x86 VM**. A phone has not been measured. The A1-S1 kit can run this binary on a phone as an optional extra (it cross-compiles with `cargo ndk`; the bundled SQLite needs the NDK C compiler).
- **Homelab, digest variant:** the homelab keeps the SHA-256 of every stored object in its plaintext catalog, so it re-derives each ID from the catalog alone. Measured here: 5M derivations in 1.5 s in memory and 1M catalog-row updates in about 3–6 s. The following is **arithmetic, not a measurement**: at the measured rate, 5M catalog rows would take tens of seconds on comparable hardware, far below 24 h. The homelab hardware and catalog engine (A6) are not known yet.
- **Content variant (full re-read):** the cost scales with bytes, not rows. These are **arithmetic examples, not measurements**:
  - Client: BUD-HASH defines the low-end phone floor as 6 MB/s effective, so rotating a 128 GB library by re-reading costs the same as a first pass, about 128e9 / 6e6 s ≈ 5.9 h, plus battery (BUD-BAT-S, from the A1-S1 kit). That is one full charge window per device, repeated for 10–25 devices.
  - Homelab: 10 TB at this VM's median single-thread 508 MB/s ≈ 5.5 h of compute. At the worst run (92 MB/s) it is ≈ 30 h. Real homelab disks will probably set the bound; they are unmeasured (C5/A6).
- **Overall:** pass on the x86 reference for the digest variant. The content variant's re-read cost is recorded above. Phone and homelab confirmation are open.

## Reproduce

```sh
cd spikes/A1-S2
cargo build --release
B=./target/release/a1-rotate
$B build work/cache.db 1000000
strace -f -e trace=openat,stat,statx,newfstatat -o work/strace.txt $B rotate work/cache.db 1 inplace
$B rotate work/cache.db 2 map
$B derive 5000000
$B mkfiles work/small 50000 4096 && $B reread work/small
```
