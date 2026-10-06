# Spike crate for A2-S1 to A2-S4: PQ age envelope, resumable uploads, signed records (THROWAWAY)

> **Throwaway spike code. It is not production code and must not be reused as such.**
> R2, the Worker, the platform keystore, the network and the homelab are simulated with local
> files. Error handling is `unwrap` plus exit codes. Only synthetic random data is used (`SYN → results`).

This crate is a fork of the T1 spike 2 crate (`spikes/content-encryption/`, research note
`docs/research/content-encryption-format.md`). The CE resume engine (`src/engine.rs`: pass 1,
keystore stand-in, sealed state, tag journal, keystream guard, range generator) is **unchanged**.
The changes are in four places.

1. **`src/header.rs` (new): a multi-stanza age v1 header.**
   - The encoder writes the native hybrid PQ recipient `mlkem768x25519` (X-Wing, through HPKE SealBase with the Rust `hpke` 0.14.1 crate) and/or `X25519`.
   - It **refuses to mix** PQ and classic recipients.
   - Randomness is hedged: the 64 bytes of X-Wing encapsulation randomness are derived from the CE hedge seed and fed through a `CryptoRng` (`HedgeRng`) that panics if the library draws more than expected.
   - The **strict generic decoder** parses 1–16 stanzas, ignores unknown stanzas, and enforces canonical base64 and the stanza lengths.
   - The decoder **rejects low-order X25519 shares inside X-Wing ciphertexts**. `hpke` 0.14.1 does not do this; `--lax-low-order` turns the check off to show the difference.
   - It also implements STREAM decryption with age's final-chunk rules.
2. **`src/meta.rs`: records are C2SP signed-notes.**
   - The note text is one line of compact JSON. An Ed25519 signature line follows, whose key name is the device ID.
   - Padding to a multiple of 512 bytes goes inside the JSON.
   - Receipts are signed-notes as well.
3. **`src/main.rs`, device side: records are sealed at the end of the upload, not at the start.**
   - At start, the unsigned record fields are persisted. `device_seq` and `record_id` are allocated, and the record is signed, only when it leaves the device.
   - The record binds the object's `header_mac`, `ct_len`, `prefix_len`, `profile` and stanza count.
   - Receipts bind `record_sha256`, the SHA-256 of the signed plaintext record.
4. **`src/main.rs`, homelab side: strict `ingest` with specific rejection codes.**
   - Checks: the stanza profile, the record signature, the device/key-name match, replay of `record_id` and `device_seq`, the object binding, and the full decryption with SHA-256 and dedup-HMAC match.
   - Every rejection prints `REJECT {"code": ...}` and exits 10 **before** any catalog, object, by-dedup or seen-set write.

The `age` crate dependency is gone: the Rust `age` 0.12.1 crate has no `mlkem768x25519` recipient.

## Layout

| Path | Contents |
|---|---|
| `src/header.rs` | Recipients and identities (`age1…`, `age1pq1…`, `AGE-SECRET-KEY-[PQ-]1…`), hedged multi-stanza encoder, strict decoder, STREAM decryption, unit tests |
| `src/format.rs` | Part/chunk layout math (unchanged; tested for any prefix length), chunk cipher, `encrypt_small`, trust bundle v2 (recipient list + profile) |
| `src/engine.rs` | CE resume engine, unchanged |
| `src/meta.rs` | Signed-note sign/verify, record padding |
| `src/main.rs` | CLI: device (`start`, `resume`, `complete`, `abort`, `dedup-hit`, `check-receipt`), homelab (`ingest`, `chunk`), tools (`keygen`, `recipient`, `make-trust`, `encrypt`, `decrypt`, `inspect`, `cctv`), benchmarks (`bench`, `bench-kem`, `bench-obj`, `soak`), test-only adversary tools (`sign-meta`, `debug-keys`, `hpke-auth-probe`) |
| `harness/a2s2_kill.py` | A2-S2: real SIGKILLs during multipart uploads, then resume, ingest and checks |
| `harness/a2s3_interop.py` | A2-S3: 4 encoders × 4 decoders × 3 key origins × 7 sizes × 1–2 stanzas |
| `harness/a2s3_vectors.py` | A2-S3: deterministic project vectors (CCTV file format), regenerated twice, run through 4 decoders |
| `harness/a2s4_forgery.py` | A2-S4: forgery, substitution, truncation, downgrade and replay attacks against `ingest` |
| `evidence/` | A2-S2 logs and `results.json` (A2-S1, S3 and S4 evidence is in `spikes/A2-S1/`, `spikes/A2-S3/` and `spikes/A2-S4/`) |

## Prerequisites

- **Rust:** 1.89 or newer (`File::try_lock`). Run with 1.94.1. Linux or macOS: the engine uses Unix file APIs, so a Windows build is not expected to work.
- **Go age:** `filippo.io/age` **v1.3.2** (`age`, `age-keygen`, `age-inspect`), for native PQ.
  - Built with `GOTOOLCHAIN=auto`; the module needs Go ≥ 1.25, and the container's Go 1.24 fetched a newer toolchain.
  - The distro `age` 1.1.1 has no PQ support.
- **A2-S3 only:**
  - Node 22 with `age-encryption` 0.3.1 (typage); see `spikes/A2-S3/tools/`.
  - Java 21 with Maven Central jars:
    - `com.github.android-password-store:kage:0.8.0`
    - `kotlin-stdlib` 2.4.20
    - `bcprov-jdk15to18` 1.86
    - `at.favre.lib:hkdf` 2.0.0
    - `kotlin-result-jvm` 2.3.1
  - The CCTV age vectors: Go module `c2sp.org/CCTV/age@v0.0.0-20260925130909-50a8ecf2a220`. The vector set is byte-identical to the 20260829 set that age v1.3.2 pins.

## Build and run

```sh
cargo build --release && cargo test --release        # 10 unit tests
B=target/release/a2-envelope-spike
export BIN=$PWD/$B AGE=<go age 1.3.2> AGE_KEYGEN=<go age-keygen 1.3.2>
WORK=/tmp/a2s2 KILLS=50 STANZAS=1 python3 harness/a2s2_kill.py     # A2-S2 (also STANZAS=2 KILLS=20)
WORK=/tmp/a2s4 python3 harness/a2s4_forgery.py                       # A2-S4
$B cctv --dir <CCTV testdata>  [--lax-low-order]                      # A2-S3 CCTV
NODE_TOOL=… KAGE_CP=… WORK=/tmp/a2s3 python3 harness/a2s3_interop.py # A2-S3 matrix
$B bench-kem --iters 3000; $B bench-obj --size 1048576 --count 300   # A2-S1 (x86)
```

`A2_SLOW_US` (test-only) makes the simulated network sleep per 16 KiB slice, so that random kills
land inside parts. The A2-S2 harness sets it to 3000 µs.

## Ingest rejection codes (spike set; input to `object-format.md`)

| Code | Meaning |
|---|---|
| `E_RECORD_TOO_LARGE` | Record ciphertext over 1 MiB |
| `E_PROFILE` | Record or object header is not exactly *n* × `mlkem768x25519` (extra, classic, grease or mixed stanzas) |
| `E_RECORD_DECRYPT` | Record is not a decryptable age file for the homelab identity |
| `E_RECORD_FORMAT` | Not a well-formed signed-note / one-line JSON record |
| `E_SIG_UNKNOWN_KEY` | Signing key name not in the device registry |
| `E_SIG_KEY_HASH` | Key hash does not match the registered key |
| `E_SIG_INVALID` | Ed25519 signature does not verify (strict verification) |
| `E_RECORD_KIND`, `E_RECORD_FIELDS` | Wrong record kind or version, or missing or ill-typed fields |
| `E_DEVICE_MISMATCH` | `device_id` in the record differs from the signing key's device |
| `E_REPLAY_RECORD_ID`, `E_REPLAY_SEQ` | A `record_id` or `device_seq` already committed with different content |
| `E_OBJECT_HEADER` | Malformed object header, or a low-order X25519 share in an X-Wing stanza |
| `E_BINDING_HEADER_MAC`, `E_BINDING_PREFIX`, `E_BINDING_LENGTH`, `E_BINDING_SIZE`, `E_LENGTH_INVALID` | Object does not match the signed record's header MAC, prefix length or ciphertext length; or the implied plaintext size differs; or the length is impossible |
| `E_OBJECT_NO_MATCH`, `E_OBJECT_HMAC` | No stanza opens with the homelab identity; the header MAC fails under the unwrapped file key |
| `E_STREAM_TRUNCATED`, `E_STREAM_TRAILING`, `E_STREAM_AUTH` | Missing or empty final chunk; data after the final chunk; a chunk fails authentication |
| `E_CONTENT_MISMATCH`, `E_DEDUP_MISMATCH` | Decrypted size, SHA-256 or dedup HMAC differs from the record; a dedup-hit record does not match committed content |

A replay of an already committed record (the same `record_id` and the same signed bytes) is
idempotent: the receipt is re-issued and no catalog row is added.

## Test-only hooks (never in production)

`--chunks-per-part`, `--interrupt-after`, `--no-stat-check`, `A2_SLOW_US`, `encrypt --seed/--context/--allow-mixed/--grease`,
`keygen --seed`, `ingest --skip-binding-precheck` and `--lax-low-order`, `sign-meta` (including `--keyhash-pk`), `debug-keys`.
