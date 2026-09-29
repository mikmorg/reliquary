# Spike: resumable content encryption (THROWAWAY)

> **Throwaway spike code. It is not production code and must not be reused as such.**
> It exists to show that the format in
> [`docs/research/content-encryption-format.md`](../../docs/research/content-encryption-format.md)
> works and can be checked by independent tools. R2, the Worker, the platform keystore and the
> network are all simulated with local files. Error handling is `unwrap`/exit codes.

## What it demonstrates

- Content objects are **standard age v1 files** made by our own encoder. The upload can resume
  after any interruption and resends parts **byte-identical**, and it never keeps more than one
  part (or one streaming window) of ciphertext.
- The **keystream-reuse guard**: every chunk's Poly1305 tag is saved in an append-only journal
  before the chunk is sent. If the plaintext has changed, re-encryption is refused. Every byte on
  the simulated wire is logged, and the tests check that no object offset was ever sent with two
  different values.
- **Signed metadata records.** Each device signs its records with Ed25519, inside the age
  encryption.
- **Homelab ingest and signed commit receipts.** A device reports a file as protected only after
  it has checked a receipt against its pinned homelab key.
- A **trust-bundle pin** for the homelab recipient and receipt key, with strict recipient parsing.
- **Hardened local state:** a per-upload key entry, AES-GCM sealed state, file mode 0600, a lock
  per upload, and stat snapshots.
- A **forward-only source mode**, which models iOS PhotoKit.

## Layout

| Path | Contents |
|---|---|
| `src/format.rs` | age v1 header encoder (hedged randomness), STREAM chunks, part layout, strict recipient parser, trust bundle |
| `src/engine.rs` | pass 1 (SHA-256 + dedup HMAC + stat snapshot), keystore stand-in, sealed state, journal, chunk sources, verified range generator |
| `src/meta.rs` | signed metadata-record and receipt framing |
| `src/main.rs` | CLI: device (`start`, `resume`, `complete`, `abort`, `dedup-hit`, `check-receipt`), homelab (`ingest`, `chunk`), verification (`age-crate`, `regen-all`), key tools, `bench` |
| `tools/ed25519verify.go` | independent Ed25519 verifier (Go standard library) used by the tests |
| `run_tests.py` | end-to-end test suite (161 checks) |
| `evidence/` | output of the last full run and the throughput benchmarks |

## Prerequisites

- Rust 1.89 or newer (`File::try_lock`). The spike was run with 1.94.
- Go 1.24 or newer. It builds the signature verifier.
- The Go `age` and `age-keygen` CLIs on `PATH`. Tested with v1.1.1.
- Python 3.9 or newer (standard library only).
- Linux or macOS. The code uses Unix file APIs (`read_exact_at`, file modes), and the tests read
  `/proc` for the memory and I/O numbers.

## Build and run

```sh
cd spikes/content-encryption
cargo build --release          # optional: run_tests.py builds as well
cargo test --release           # 6 unit tests (layout math, journal recovery, windowing, parsing)
python3 run_tests.py           # full suite, about 2.5 min; writes ./work (git-ignored)
QUICK=1 python3 run_tests.py   # skips the 10,000-part write-amplification and RSS tests
```

Environment variables:

- `CARGO_TARGET_DIR`: default `./target`.
- `WORK`: default `./work`, **wiped** at the start of every run.
- `AGE`: path to the Go `age` binary.

Results go to `$WORK/results.json`. The process exits non-zero if any check fails.

Running a single scenario means calling the functions directly, for example:

```sh
python3 -c "import run_tests as t; t.setup(); t.safety_tests()"
```

## Throughput benchmark

```sh
head -c 1073741824 /dev/urandom > /tmp/1g.bin
./target/release/reliquary-enc-spike bench --file /tmp/1g.bin
# ARM stand-in: force the portable (non-SIMD) SHA-2 / ChaCha20 / Poly1305 backends
RUSTFLAGS='--cfg sha2_backend="soft" --cfg chacha20_backend="soft" --cfg poly1305_backend="soft"' \
  cargo build --release --target x86_64-unknown-linux-gnu
./target/x86_64-unknown-linux-gnu/release/reliquary-enc-spike bench --file /tmp/1g.bin
```

## Exit codes (CLI)

| Code | Meaning |
|---|---|
| 0 | ok |
| 2 | usage error, or refused trust bundle / invalid object |
| 10 | ingest rejected |
| 11 | ingest pending: the content is not committed yet |
| 12 | receipt invalid |
| 65 | source changed: abort and restart |
| 66 | source missing |
| 69 | source changed during pass 1 |
| 73 | busy: another process holds the lock |
| 74 | I/O error |
| 75 | simulated interruption |
| 76 | state or journal corrupt: abort and restart |

## Test-only hooks (never in production)

- `--chunks-per-part k` forces tiny parts, below R2's 5 MiB minimum, to exercise part boundaries.
- `--interrupt-after i` simulates a dropped connection partway through the i-th part.
- `--no-stat-check` models an edit that `stat` cannot see.
- `sign-meta` plays a registered but malicious device.
