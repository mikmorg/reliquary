# Spike A6-S5: format independence (THROWAWAY)

> **Throwaway spike code, not production code.** Workstream A6 (`docs/research/PLAN.md`, section "A6."). Input to ADR-0012 (K2 "specified format with an independent reader" and the "readable for decades" weight).

- **Run by / date:** A6 spike runner (agent), 2026-10-06 (Wave 1, batch W1-b)
- **Exec tag:** CT, run for real in the cloud container
- **Data class:** `SYN → results`. The content is random bytes from `a6cas gen` (seed 5, 200 records, 176 unique contents, 196,375,916 bytes). The keys are throwaway and were made and deleted in `/dev/shm`.
- **Budget IDs:** BUD-RECOVERY, by proxy only. It is a recovery by a *non-author* from the doomsday kit, which this spike does not test. Single-file timings are also given against BUD-RESTORE, but they come from tmpfs in a cloud VM, **not homelab hardware**.
- **Pass criterion (PLAN):** "Restore with an independent implementation (restic↔rustic), or with coreutils + age + sqlite3 and a one-page procedure. Byte-identical; weighted in the ADR."

## Hypothesis

A store written by the A6 prototype (`spikes/A6-S3/a6cas`, plain CAS of age v1 objects, posture A′) can be restored byte-identically with no Reliquary code, using any of three age implementations plus coreutils, and optionally `sqlite3`. As a cross-check of the restic comparator's K2 claim, restic and rustic restore each other's repositories.

## What was run

| Path | What |
|---|---|
| `restore-without-reliquary.sh` | **The one-page procedure.** Uses bash, coreutils (`sha256sum`, `cut`), `find`, `grep`, an age v1 decryptor (`AGE=` selects which), and optionally `sqlite3`. Modes: `by-hash`, `by-name` (no catalog: decrypts the archived metadata records and greps them), `by-name-catalog` (`sqlite3`), and `all`. Every restored file is checked against the SHA-256 in its own name. |
| `s5s6.py` | Driver for this spike and A6-S6. Expects `$A6/bin/{a6cas,age}` and `$A6/cargo/bin/rage`. Run as `python3 s5s6.py $A6 /dev/shm/a6fmt evidence/s5s6.json`. |
| `restic-rustic.sh` | restic 0.19.1 writes and rustic 0.11.4 reads, then the reverse: `check --read-data`, full restore and a single-file `dump`, with every file checked by its SHA-256 name. |
| `evidence/s5s6.json`, `evidence/s5-restic-rustic.txt` | Raw output. |

Tools:

- `age` 1.1.1 (Debian package, Go)
- `age` v1.3.1 (built from `filippo.io/age`)
- `rage` 0.12.1 (Rust, `cargo install rage`; the latest on crates.io, last updated 2026-07-14)
- `sqlite3` 3.45.1
- restic 0.19.1 (Go module proxy; latest, 2026-07-05)
- rustic-rs 0.11.4 (crates.io)

## Results (measured)

**Part A: the store needs no Reliquary software.** All counts are from `evidence/s5s6.json`.

| Archive and recovery recipients | Decryptor | Blobs decrypted to the right SHA-256 (archive key / recovery key) | Records | Ingest key on stored objects | Procedure `all`: byte-identical | `by-name`, no catalog | `by-name-catalog` (`sqlite3`) |
|---|---|---|---|---|---|---|---|
| X25519 | age 1.1.1 (Debian) | 176/176 / 176/176 | 200/200 | refused 176/176 | 176/176 in 3.1 s | 3/3 (1.5–1.6 s each, 200 records scanned) | 3/3 (≤ 0.07 s) |
| X25519 | age 1.3.1 (Go) | 176/176 / 176/176 | 200/200 | refused 176/176 | 176/176 in 3.1 s | 3/3 (1.8–2.0 s) | 3/3 (≤ 0.07 s) |
| X25519 | rage 0.12.1 (Rust) | 176/176 / 176/176 | 200/200 | refused 176/176 | 176/176 in 2.4 s | 3/3 (1.3–1.4 s) | 3/3 (≤ 0.06 s) |
| **ML-KEM-768 + X25519 hybrid (PQ)** | age 1.1.1 (Debian) | **0/176**: "unknown identity type" | 0/200 | refused | **fails** | fails | fails |
| PQ | age 1.3.1 (Go) | 176/176 / 176/176 | 200/200 | refused 176/176 | 176/176 in 2.6 s | 3/3 | 3/3 |
| PQ | rage 0.12.1 (Rust) | **0/176**: "identity file contains non-identity data on line 1" | 0/200 | refused | **fails** | fails | fails |

- **Finding (High, measured):** with X25519 recipients, the store passes the "coreutils + age + sqlite3" criterion with two independent age implementations (Go and Rust) and an older distro build.
- **Finding (High, measured):** with hybrid PQ recipients (`mlkem768x25519`, which OD-06 may choose), **only Go age ≥ 1.3 can read the store today**.
  - The Rust `age` crate 0.12.1 contains the `tag` and `tagpq` recipient types (encrypt-only, for hardware tags). A grep of its source finds no `mlkem768x25519` identity.
  - If OD-06 puts PQ stanzas in *stored* headers, K2 (independent reader) drops to one implementation until rage catches up.
  - Keeping an X25519 archive stanza next to a PQ one is **not** an option: Go age refuses to mix hybrid and X25519 recipients in one file (`recipients_test.go` `TestHybridMixingRestrictions`, age v1.3.1).
  - Handed to A2/D2 for OD-06.
- **Quirk (measured):** `age -d -o FILE` with an empty plaintext does **not create FILE** in age 1.1.1 and rage 0.12.1 (exit code 0). age 1.3.1 does create it. The procedure therefore redirects stdout instead of using `-o`. Any doomsday-kit instructions must do the same.
- Single-file restore by SHA-256 with `a6cas get`: 20 samples per variant (the 5 largest, up to 15.4 MB, plus 15 random), all SHA-256 correct, maximum 0.067 s (X25519) and 0.064 s (PQ). This is **tmpfs on a cloud VM**; BUD-RESTORE needs the A6-S2 homelab run.

**Part B: restic ↔ rustic** (176 plaintext files, 196,375,916 bytes, repository format version 2)

| Direction | `check --read-data` by the other tool | Full restore by the other tool | Single-file `dump` |
|---|---|---|---|
| restic 0.19.1 writes, rustic 0.11.4 reads | rc 0 | 176/176 files hash to their names | OK |
| rustic 0.11.4 writes, restic 0.19.1 reads | rc 0 | 176/176 | OK |

**Finding (High, measured, small sample):** the restic format's independent-reader claim (scout C, rustic README) holds in both directions for a v2 repository with these versions. Random content does not compress, so this sample does not exercise zstd.

## Pass / fail

**Pass** for posture A′ with X25519 recipients, on both routes the PLAN allows: byte-identical restores with three age decryptors plus coreutils (`sqlite3` optional), and restic ↔ rustic. **Conditional** for PQ recipients: the one-page procedure works only with Go age ≥ 1.3.

No emulator stood in for anything here, but the machine is a shared cloud VM, so the timings are not homelab figures.

## Rebuild

1. Build `a6cas`: `cd ../A6-S3/a6cas && go build`.
2. Build age v1.3.1: `go install filippo.io/age/cmd/...@v1.3.1`.
3. Install rage and rustic: `cargo install rage rustic-rs`.
4. Install restic: `go install github.com/restic/restic/cmd/restic@v0.19.1`.
5. Run `s5s6.py`.
6. Run `restore-without-reliquary.sh all <store> <archive.key> <plaindir>`, then `restic-rustic.sh <plaindir> <work>`.
