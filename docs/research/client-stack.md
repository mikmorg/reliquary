# Client stack research (input to ADR-0003)

- **Date:** 2026-09-29
- **Method:** web research (2025–2026 sources). v2.tauri.app and support.microsoft.com were blocked by the egress proxy; claims about those rest on secondary sources. Items marked *[uncertain]* need a spike.

## Key finding: the background engine must not live in the UI framework

Uploading terabytes from phones is OS-scheduled background work, and each OS wants a native entry point: Android WorkManager / user-initiated data transfer (UIDT) jobs, iOS background `URLSession` + `BGProcessingTask`, desktop LaunchAgent / systemd user unit / Run key. The primary decision is therefore **where the core logic lives** (hashing, HMAC dedup IDs, encryption, bundle format, SQLite hash cache, upload state machine); the UI shell is secondary. A **Rust core** can be called natively from Kotlin, Swift and desktop, and can be the same crate the homelab ingest service uses.

## Platform facts that shape the design

- **Android 15** caps `dataSync` foreground services at **6 h per 24 h** ([FGS timeouts](https://developer.android.com/develop/background-work/services/fgs/timeout)). Google directs long user-initiated transfers to **UIDT jobs** (Android 14+) and deferrable work to **WorkManager** ([data transfer options](https://developer.android.com/develop/background-work/background-tasks/data-transfer-options)). Consequence: the initial seed goes via USB or an explicit "Back up now" UIDT job; ongoing work is short, resumable WorkManager chunks.
- **Android photo access:** request `READ_MEDIA_IMAGES`, `READ_MEDIA_VIDEO`, `READ_MEDIA_VISUAL_USER_SELECTED` and `ACCESS_MEDIA_LOCATION` together. **`MediaStore.setRequireOriginal()` is required** to read original bytes with EXIF GPS; without it location is redacted, silently breaking byte-exact dedup and integrity. Detect partial ("selected photos") access and tell the user plainly.
- **Windows Smart App Control** may block unsigned builds outright (see `fact-check-adr-0001-0002.md`, item 8). This affects every stack.

## Comparison

| Criterion | A. Rust core + Flutter | B. Rust core + Tauri 2 everywhere | C. Rust core + native UIs (UniFFI), Tauri desktop | D. Kotlin/Compose Multiplatform | E. Pure Flutter/Dart |
|---|---|---|---|---|---|
| Android background | Good if the worker is native Kotlin calling Rust; Dart workers boot a headless engine (~50 MB, 1–2 s) | Weak: no core WorkManager/BGTask support in Tauri | **Best**: Kotlin workers call Rust directly | **Best** | OK via plugins, same engine cost |
| Desktop daemon + tray | Rust daemon + Flutter UI | **Best**: tray, autostart, same Rust binary | Same as B | JVM daemon (heavy) | Weak as a daemon |
| iOS later (background URLSession) | Swift plugin or background_downloader | Swift plugin, immature | Native SwiftUI | Kotlin/Native can call it | background_downloader |
| One byte-exact crypto implementation, shared with homelab | Yes (Rust `age`, RustCrypto sha2/hmac with HW accel) | Yes | Yes | No mature Kotlin `age`/X25519 *[uncertain]* | Hobby `age` ports; slow hashing |
| Signed self-update (Ed25519) | Third-party or custom | **Built in** (tauri-plugin-updater, minisign signatures mandatory) | Same as B | Conveyor (commercial) or custom | Same as A |
| USB-runnable packaging | exe folder / .app / AppImage via third-party tool | NSIS/MSI, .app, AppImage native | Same as B | jpackage + bundled JRE | Same as A |
| Desktop size | 20–80 MB | 2–15 MB | 2–15 MB | ~60–150 MB *[estimate]* | 20–80 MB |
| Ecosystem risk | flutter_rust_bridge has a single maintainer | Tauri mobile least proven | UniFFI is Mozilla-backed, in production | Compose Multiplatform stable on iOS since 1.8 | Crypto correctness |

## Recommendation: option C

- A **Rust core workspace**, shared with the homelab ingest service.
- **UniFFI** bindings for Kotlin now and Swift later.
- **Android:** native Kotlin + Jetpack Compose app; WorkManager/UIDT workers call the Rust core; MediaStore and CameraX QR scanning in Kotlin.
- **Desktop:** **Tauri 2** tray app + Rust background daemon registered per OS; Tauri's minisign updater satisfies ADR-0002's mandatory update signing.
- **iOS later:** SwiftUI driving background `URLSession` uploads of part files encrypted by the Rust core.

Rationale: it is the only option where every platform's background path is native and first-class; there is one crypto and format implementation shared with the homelab; Tauri matches the USB kit and signed updates without custom work; and the UI is thin (status, discovery proposals, QR enrollment, nudges), so writing it per platform is cheap.

**Fallback:** option A (Flutter UI via flutter_rust_bridge, native workers via UniFFI) if a single UI codebase matters more than native mobile.

## Spikes before ADR-0003 is accepted

1. **Smart App Control / first launch:** unsigned USB exe on a clean-install Windows 11 with SAC on and on an upgraded PC; Defender scan; ad-hoc-signed .app from USB on current macOS. May force a Windows signing certificate.
2. **Resumable upload vs. encryption randomness:** `age` draws a fresh file key per encryption, so a resumed multipart upload must either keep ciphertext on disk or reproduce identical parts. Determine whether the `age` crate allows supplying the file key; otherwise use age for metadata plus a documented chunked content-encryption scheme.
3. **Android:** UIDT seed job + periodic WorkManager worker calling the Rust core via UniFFI on Android 15/16; battery and 6-hour behaviour; verify `setRequireOriginal` yields byte-identical originals (SHA-256 vs. an `adb pull` copy); partial-access UX.
4. **R2:** part-size policy (e.g. fixed 8–64 MiB; 10,000 parts caps objects at 80–640 GiB), presigned UploadPart, ETag capture from background transfers.
5. **Tauri updater:** offline minisign key; update the per-user NSIS install, AppImage and ad-hoc-signed .app after the stick is removed.
6. **Desktop process model:** single Tauri process vs. separate Rust daemon + UI over local IPC; autostart on each OS.
7. **Hash throughput:** Rust SHA-256 + HMAC on a low-end Android phone; single pass for both.
8. **iOS feasibility (paper check):** Swift shell hands Rust-produced part files to a background URLSession and records results in the Rust SQLite DB after relaunch.
