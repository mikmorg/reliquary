# Spike A6-S4: catalog loss → rebuild from the store (THROWAWAY)

> **Throwaway spike code, not production code.** Workstream A6 (`docs/research/PLAN.md`, section "A6."). Input to ADR-0012 (the store is the source of truth) and to ADR-0013 (Wave 2: the catalog is a projection). The catalog engine is **not** decided. SQLite (WAL, `synchronous=FULL`) stands in only because it embeds easily.

- **Run by / date:** A6 spike runner (agent), 2026-10-06 (Wave 1, batch W1-b)
- **Exec tag:** CT, run for real in the cloud container (tmpfs)
- **Data class:** `SYN → results` (the `a6cas gen` corpora of A6-S3 and A6-S5; throwaway keys)
- **Budget IDs:** none
- **Pass criterion (PLAN):** "Rebuild from the store gives a byte-identical canonical export."

## Method

- `s4.sh NAME STORE CATALOG KEYS [STAGING]`:
  1. exports the catalog canonically (`a6cas export`: blobs and records as fixed-order JSON lines, sorted; the operational `ingest_events` table is excluded);
  2. deletes `catalog.db`, `-wal` and `-shm`;
  3. rebuilds with `a6cas rebuild` (manifest plus archived records, decrypted with the **archive key**, so the step is attended under A′);
  4. compares the two exports byte for byte.

  It also runs a **files-only** rebuild that ignores the manifest and lists which fields are lost.
- With `STAGING` the script first runs the "mid-ingest loss" scenario:
  1. start ingest;
  2. try a second, concurrent ingest (which must be refused);
  3. `kill -9` the first;
  4. delete the catalog;
  5. rebuild;
  6. resume ingest from staging (already-committed records take the stored-receipt path, "ACK … dup");
  7. delete and rebuild again.

## Results (measured; `evidence/s4.txt`)

| Scenario | Canonical rows | Rebuild (manifest + records) | Byte-identical | Truth check |
|---|---|---|---|---|
| Clean store, 200 records (176 blobs) | 376 | 0.29 s | **Yes** | n/a |
| Store left by the A6-S3 `crashpoints-cas` run (100 self-kills at 8 points, incl. 18 torn manifest lines and 46 quarantines), then killed again mid-ingest, catalog deleted, rebuilt, resumed (267 new ACKs, 333 stored-receipt ACKs), then deleted and rebuilt again | 1,135 | 0.90 s | **Yes** | 600/600 records with the right SHA-256; keyless audit 1,135 objects OK |
| The same for the OCFL layout (`crashpoints-ocfl`) | 1,135 | 0.92 s | **Yes** | 600/600; audit OK |

**What a files-only rebuild (manifest lost too) cannot recover:**

- `blob.epoch` and `blob.committed_at`;
- `record.committed_at`;
- `record.meta_sha256`, the SHA-256 of the device's original upload, which the receipt binds. The stored file is rewrapped, so the original bytes exist only as `h0` (manifest) plus the payload.

All rows and every other field come back from the objects alone (blobs are decrypted fully to prove their names).

**Finding:** the manifest is part of the archive, not a cache. Either `epoch`, `committed_at` and `h0` also go into each stored record object, or the manifest gets the same audits and copies as the objects. This goes to ADR-0012 and ADR-0013.

**Two real defects found by this spike** (kept as evidence; both fixed before the final run):

1. **No single-writer lock** (`evidence/s4-first-run-two-writers-BUG.txt`, `s4-two-writers-manifest-summary.json`).
   - A harness slip left a killed ingest still running (killing a shell function's subshell does not kill its child), and a second ingest ran beside it.
   - The manifest got 370 keys written twice, 0.1 s apart, with different `stored_sha256` values: the second writer had replaced the first writer's file.
   - No content was lost (the audit with last-line-wins passed). But the rebuild, which then took the *first* line, produced a catalog whose `stored_sha256` no longer matched the files.
   - Fix: an exclusive `flock` on `store/LOCK` for `ingest` and `recover`; `rebuild` now takes the last line for a repeated key and reports how many there were.
2. **The lock was released by Go's garbage collector** (`evidence/s4-second-run-lock-released-by-GC-BUG.txt`).
   - The first fix kept the locked `*os.File` in a local variable. Its finalizer closed the fd, and the second ingest got in.
   - Its start-up `recover` then quarantined files that the first writer had just renamed into place but not yet put in the manifest. In the OCFL run, 6 committed records ended up in `quarantine/` while the catalog said committed, so the truth check failed (364/600).
   - Fix: keep the file in a package variable. The final run shows `store is locked by another writer` for the second ingest in both scenarios.

**Lesson for ADR-0012:** the CAS layout is only "trivially safe" with exactly one writer. The production ingest service needs a store-wide writer lock that a test checks, and the same lock for any repair or prune tool (SR-20).

## Pass / fail

**Pass** (final run, after the two fixes): byte-identical canonical export in all three scenarios. The failures before the fixes are recorded above.
