# Spike B4-S1: iOS paper check with an emulated Swift shell (THROWAWAY)

> **Throwaway spike code. It is not production code and must not be reused as such.**
> It is **not** an iOS test. There is no Apple SDK, Simulator or device in the research
> container. The iOS pieces (PhotoKit, background `URLSession`, relaunch) are **emulated on Linux**.
> What is real: the Rust core, the UniFFI-generated Swift bindings, Swift 6.1.3 compiling and
> calling them, SQLite, the file handoff and crash/cancel behaviour, and a cross-compile of the
> core to `aarch64-apple-ios` / `-sim` static libraries.

- **Spike:** B4-S1 "Paper check (extends T1 spike 8)", exec tag CT, workstream B4 (`docs/research/PLAN.md`)
- **Run:** 2026-09-29, research container (x86_64 Linux, 4 CPUs), see `evidence/environment.txt`
- **Data class:** `SYN → results` (deterministic pseudo-random files; no photos)
- **Budget IDs:** BUD-TMP (spool bound; mechanism only, no phone measurement). BUD-TTS, BUD-BAT-D and BUD-HASH are **not** measured here; kit B4-S2 measures them on a device.
- **Pass criterion (PLAN):** "No core API change is needed for iOS, or the list of changes reaches T1 before ADR-0003 is accepted."
- **Result:** changes **are** needed. The list is below and is written for T1 / ADR-0003. The emulated shell passed all 26 checks in both the Swift 5 and Swift 6 language modes, and a third time from this repo copy.

## Question

T1 spike 8 asks: can a Swift shell hand Rust-produced part files to a background URLSession and record the results in the Rust SQLite DB after a relaunch? B4 adds: what must the core's API look like **now** so that iOS is not precluded? Specifically: file-based upload handoff, pre-encrypted part files, short cancellable work units, persisted resumable state, asset-identifier source locators, and Swift bindings through UniFFI.

## What was built

| Path | What it is |
|---|---|
| `core/src/lib.rs` | Rust core API exported with UniFFI 0.32.2 (proc macros): `Core` (open, plan_upload, find_upload, produce_parts, pending_handoffs, mark_enqueued, record_task_result, reconcile_session, upload_status), `CancelToken`, foreign traits `PlaintextSource` (forward-only `read(max_len)`) and `ProgressSink`, `SourceLocator` record, an async export (to check async bindings). SQLite (rusqlite 0.40, WAL, `synchronous=FULL`, STRICT tables). **Stand-in encryption**: ChaCha20-Poly1305 per 64 KiB chunk with a counter nonce, so parts are real ciphertext and regenerate byte-identically. The real format is T1 spike 2 (`docs/research/content-encryption-format.md`). |
| `core/src/bin/verify.rs` | Reassembles the parts the mock server stored, checks ETags against the DB, decrypts, compares SHA-256 with the source, and checks that every re-upload of a part carried identical bytes. |
| `harness/main.swift` | The emulated iOS shell. One process run = one app wake (launch or background relaunch). It applies delivered task results, reconciles live tasks, runs one `produceParts` work unit and hands every spooled part off as a **file**. |
| `mock/nsurlsessiond_mock.py` | Emulates the out-of-process transfer service: takes file-backed tasks, PUTs the file, writes completion events. It can drop everything (user force-quit), delay, or duplicate events. |
| `mock/mock_r2.py` | Emulated presigned UploadPart endpoint (not R2): ETag = MD5, URL expiry returns 403, injected 500s, and every attempt logged with the body's SHA-256. |
| `run_s1.py` | The scenarios below; writes `evidence/results.json`. |
| `build_swift.sh` | Compiles bindings + harness inside the `swift:6.1-noble` container. |

## Results (measured 2026-09-29)

All 26 checks passed with the Swift 6 build (`evidence/results-swift6.json`, `evidence/run-swift6.log`) and the Swift 5 build (`evidence/results-swift5.json`).

| Scenario | What it emulates | Outcome |
|---|---|---|
| A | 40 MiB + 12,345 B source, 5,244,160 B parts (T1 default), spool budget 2 parts, 6 wakes | Reassembled + decrypted = source. Spool peak 10,488,320 B = budget, never above. Spool empty at the end. Forward-only source read **3.50× the file size** over 5 producing wakes, consistent with T1 §8.6's S·(w+1)/2. |
| B | BG task expiration: cancel after 7 MiB read | Only part 1 committed, the torn part 2 `.tmp` deleted, `cancelled = true`. Cancel latency **486 µs** (Swift 6 run) / **595 µs** (Swift 5 run) on the x86 container. The flag is checked every 64 KiB chunk. **Not a phone number.** Completed afterwards. |
| C | SIGKILL mid-part (jetsam / crash); spool held 2 `.part` + 1 `.tmp` | On relaunch the `.tmp` was removed and production continued; the object verified. |
| D | Presigned URLs expired while queued (TTL 1 s) | 5 failure events → the parts returned to `spooled` → re-handed off with fresh URLs. Re-uploads byte-identical (0 conflicting part bodies). |
| E | User force-quit: the system cancels all tasks, no events | `reconcile_session` reset 4/4 orphaned tasks. The parts were re-handed off and the object verified. |
| F | Duplicate completion events | 3 recorded, 3 detected as duplicates, no double count. |
| G | Spool purged after handoff (as if the spool lived in Caches) + one 500 | The purged part was regenerated **byte-identical** to the first attempt (server log). |
| H | Spool purged and source edited (1 byte in part 2) | `SourceChanged`: refused to re-encrypt with the same key and nonces, and no part-2 ciphertext left. |
| I | 0 B, 1 B, exactly 2 parts | All round-trip. |

Other measurements:
- **Swift bindings:** UniFFI 0.32.2 generated 2,314 lines of Swift + a C header and modulemap. They compiled with `swiftc -swift-version 5` and `-swift-version 6` (Swift 6.1.3, Linux) with **0 warnings**. Generated protocols, including the foreign traits, require `Sendable`.
- **iOS cross-compile** (`evidence/ios-crosscompile.txt`): the core builds as a static library for `aarch64-apple-ios` (18,026,584 B) and `aarch64-apple-ios-sim` (18,015,016 B) **without** bundled SQLite (it links the system `libsqlite3`). With bundled SQLite it fails: cc-rs needs `xcrun`, so that build needs a Mac. Swift bindings generated from the iOS `.a` are byte-identical to the Linux ones. T1 spike 2's crate (age 0.11.5, RustCrypto 0.11 generation, dalek 2) passes `cargo check` for `aarch64-apple-ios`. Nothing was linked or run on Apple hardware.
- The core DB for scenario A was 61,440 B (WAL + main).

## Changes the core API needs for iOS (input to T1 / ADR-0003)

1. **Split "produce" from "transfer".** The core must be able to write **pre-encrypted part files to a spool** and stop, leaving the upload to the platform: `uploadTask(with:fromFile:)`, since Apple documents that uploads from Data or a stream fail once the app exits. The in-process streaming uploader can stay for desktop and Android. T1 §8.6 already expects "the iOS spool"; this makes it an API mode, not an implementation detail.
2. **Budgeted batch work units.** `produce_parts(upload, source, cancel, progress)` streams the source forward once per wake and writes as many consecutive parts as a **byte budget** allows (BUD-TMP). Apple rate-limits tasks started from the background and recommends many tasks per wake, so all spooled parts are enqueued in one go.
3. **Foreign-trait sources, forward-only, pass-by-value.** The source is a UniFFI foreign trait `read(max_len) -> bytes` that Swift implements over PhotoKit (`requestData` push bridged to pull, or `writeData(toFile:)`). UniFFI does not support references in foreign-trait methods. A regenerated part re-reads from the start of the stream (measured amplification above).
4. **Transfer-task bookkeeping in the core DB.** Three calls: `mark_enqueued(session, task_id, upload, part)`, called **before** `resume()`; idempotent `record_task_result(session, task_id, status, etag, error)`; and `reconcile_session(session, live_task_ids)` after every launch, because a force-quit cancels all tasks and delivers no events. Also set `task.taskDescription` = upload/part as a durable second key. Whether `taskIdentifier` values stay unique across relaunches is not documented and needs checking on a device (kit B4-S2).
5. **Cancellation and progress as first-class parameters.** A `CancelToken` object checked per chunk (UniFFI has no built-in cancellation; its manual recommends a library flag), and a per-chunk `ProgressSink`: `BGContinuedProcessingTask` terminates low-progress tasks first, and DTS reports a stall rule of about 30 s (forum, secondary). Committed parts must survive cancellation and SIGKILL.
6. **Startup reconciliation of spool vs DB.** Delete `.tmp` files and unreferenced `.part` files. Mark rows whose file vanished as `missing` and regenerate them. Regeneration must be **refused** if the plaintext changed (demonstrated at part granularity here; T1 spike 2's per-chunk tag journal is the real guard). The spool belongs in Application Support, not Caches, which iOS may purge; exclude it from backup, and give it file protection "until first user authentication", as T1 §E2 already says.
7. **URL refresh on retry.** Tasks started in the background are always discretionary (Apple), so a presigned URL can expire in the queue. A failed task must return its part to `spooled` for a fresh URL (scenario D). **For D3/C1:** this conflicts with BUD-REVOKE's 15-min URL expiry. B4-S2 step B2 measures the real queue delay.
8. **Generic source locator** `{kind, local_identifier, cloud_identifier?, resource_role, content_version, raw_path?}`. On iOS it is `PHAsset.localIdentifier` + `PHAssetResource` role + `modificationDate`. One asset has several resources (original, paired video, full-size edit, adjustment data), so the dedup/upload unit is the **resource**, not the asset (input to A5/ADR-0016).
9. **SQLite on iOS:** use the system `libsqlite3` (rusqlite without `bundled`), or build bundled SQLite on the Mac. Either way the core's SQL must not depend on a newer SQLite than iOS ships (not checked here).
10. **No panics across the FFI.** UniFFI's Swift docs say a Rust panic in a non-throwing function becomes an uncatchable fatal error. This spike still uses `expect`/`unwrap` internally; production code must not.
11. **ETag handling:** the core compares the returned ETag with the ciphertext MD5. This held for the mock and for the moto S3 emulator used by kit B4-S2's helper. R2's ETag format is still T1 open issue 1.

**No change is needed** for the PhotoKit Background Resource Upload extension. It cannot be the content uploader: its documented API uploads a `PHAssetResource` to a `URLRequest` and has no hook for app-supplied or transformed bytes (Apple reference pages, retrieved 2026-09-29). It could at most hydrate iCloud originals through `downloadOnly` jobs; kit B4-S2 (A8, A9) tests what it can do on a device.

## Reproduce

```sh
cd spikes/B4-S1
export CARGO_TARGET_DIR=$PWD/target
cargo build --release --manifest-path core/Cargo.toml
(cd core && cargo run --release --features=uniffi/cli --bin uniffi-bindgen -- \
   generate --library ../target/release/libreliquary_ios_shape.so --language swift --out-dir ../gen)
docker run --rm --network none -v $PWD:/w swift:6.1-noble sh /w/build_swift.sh 6   # or 5
python3 run_s1.py          # about 35 s; needs Docker, Python 3.9+; writes work/ and evidence/results.json
# iOS static libraries (compile only):
rustup target add aarch64-apple-ios aarch64-apple-ios-sim
(cd core && cargo rustc --release --lib --target aarch64-apple-ios --no-default-features --crate-type staticlib)
```

In the research container the Docker daemon had to be started by hand (`dockerd &`).
`download.swift.org` was blocked, so Swift came from Docker Hub's `swift:6.1-noble` image (digest in `evidence/environment.txt`).

## Limits

- Emulated. A Linux process run stands in for an iOS launch or relaunch, and a Python script stands in for nsurlsessiond. Nothing here shows how iOS schedules, throttles or kills. Kit B4-S2 does that.
- The stand-in cipher is not the Reliquary format, and the payload key sits unsealed in the DB.
- Timings are from an x86 container and say nothing about iPhone speed or battery.
