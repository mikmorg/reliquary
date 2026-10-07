# Spike A1-S1: hash and dedup-ID throughput, x86 reference run (THROWAWAY)

> **Throwaway spike code, not production code.** It measures candidate dedup-ID constructions for
> ADR-0006 (workstream A1, `docs/research/PLAN.md`). The phone and desktop runs that decide the
> spike are an owner-lab kit: [`docs/research/kits/A1-S1/`](../../docs/research/kits/A1-S1/README.md).
> The numbers below come from **one shared x86 cloud VM**. They are a reference point, not a
> measurement of any family device.

- **Run by / date:** A1 spike runner (Wave 1, batch W1-b), 2026-09-29
- **Exec tag of this part:** CT. The device part is OL (kit-ready).
- **Data class:** `SYN → results`. The only input is random bytes.
- **Budget IDs:** BUD-HASH, BUD-BAT-S. Neither can be judged here, because both are defined on a low-end phone.

## What it measures

| Workload | Construction | Hash computations per content byte |
|---|---|---|
| `C1_sha256+hmac_sha256_content` | SHA-256(content) and HMAC-SHA256(K, content), one read. This is ADR-0001's "HMAC(family secret, content)" plus the integrity SHA-256, as in the content-encryption spike (format note §6). | 2 |
| `C2_sha256_then_hmac_digest` | SHA-256(content), then HMAC-SHA256(K, digest). The ID can be re-derived from a cached digest. | 1 |
| `C3_blake3+keyed_blake3_content` | BLAKE3(content) and keyed BLAKE3(K, content) | 2 |
| `C4_blake3_then_keyed_digest` | BLAKE3(content), then keyed BLAKE3(K, digest) | 1 |
| `C5_sha256+keyed_blake3_content` | SHA-256(content) and keyed BLAKE3(K, content) | 2 |
| `*_rayon_all_cores` | BLAKE3 with `update_rayon` (all cores, 16 MiB feeds) | 1 |

Libraries: RustCrypto `sha2` 0.11.0, `hmac` 0.13.0, `blake3` 1.8.7 (features as listed). `sha2` 0.11 has no `asm` feature. It picks SHA-NI or the ARMv8 SHA-2 instructions at run time, and `RUSTFLAGS='--cfg sha2_backend="soft"'` forces the portable code.

Modes: `mem` (1 GiB random buffer in RAM, 1 MiB feeds, 1 warm-up run and 5 measured runs), `file` (a 1 GiB random file read with a 1 MiB buffer; "cold" drops the guest page cache before each run), `ladder` (the cost of one whole file at 0 B to 16 MiB, key setup included), and `soak` (used only by the device kit).

## Machine and conditions (read before using any number)

- **CPU:** "Intel(R) Xeon(R) Processor @ 2.10GHz", family 6 model 207, **KVM guest, 4 vCPUs**, with `sha_ni`, AVX2 and AVX-512. Rust 1.94, Linux 6.18, ext4 on a virtio disk.
- **Heavy CPU contention from other workloads on the same VM.** Load average was 5.8 to 15 during the runs, and `/proc/pressure/cpu` "some avg10" was 78–97 %. Wall-clock MB/s therefore varies by up to 2× between repeats (compare min and max in the evidence). **CPU seconds per GB** (`getrusage`, user + system) is the steadier figure and is given next to every rate.
- **"Cold" file reads:** `drop_caches` worked inside the guest (the page cache shrank from 2.0 GB to 0.49 GB when tested). The host may still have cached the virtual disk, so the "cold" read rate (about 2 GB/s) is **not** a disk figure for any real device.
- **Energy:** **no result.** The VM exposes no RAPL or power counters (`/sys/class/powercap` is absent). The energy side of the spike is in the kit.
- No thermal effects can be observed on a VM.

## Results (measured)

### In memory, 1 GiB, median of 5 runs

| Workload | Default: SHA-NI + BLAKE3 AVX-512 | | BLAKE3 limited to SSE4.1 | | **SHA-256 software + BLAKE3 portable (no SIMD)** | |
|---|---|---|---|---|---|---|
| | MB/s | CPU s/GB | MB/s | CPU s/GB | MB/s | CPU s/GB |
| sha256 | 988 | 0.914 | 1089 | 0.915 | 190 | 3.734 |
| hmac_sha256_content | 1027 | 0.926 | 1050 | 0.952 | 181 | 3.827 |
| **C1** sha256 + hmac(content) | 544 | 1.685 | 572 | 1.712 | 98 | 7.456 |
| **C2** sha256 → hmac(digest) | 1016 | 0.954 | 1046 | 0.942 | 212 | 3.794 |
| blake3 | 3639 | 0.224 | 1471 | 0.658 | 525 | 1.645 |
| blake3_keyed | 4472 | 0.223 | 1291 | 0.707 | 558 | 1.716 |
| **C3** blake3 + keyed(content) | 2313 | 0.427 | 683 | 1.310 | 262 | 3.329 |
| **C4** blake3 → keyed(digest) | 3885 | 0.233 | 1411 | 0.677 | 423 | 1.665 |
| **C5** sha256 + keyed blake3 | 810 | 1.135 | 561 | 1.602 | 167 | 5.110 |
| blake3_rayon_all_cores | 6658 | 0.229 | 1245 | 0.759 | 621 | 1.615 |
| C4_rayon_all_cores | 7915 | 0.233 | 1147 | 0.787 | 673 | 1.736 |

A fourth build (`sha2` software plus BLAKE3 `pure`, meaning no C/asm but still Rust SIMD intrinsics) is in `evidence/mem-soft-sha2+blake3-pure-rust-simd.jsonl`. There BLAKE3 ran at 2136 MB/s (0.455 CPU s/GB) and C2 at 259 MB/s (3.769 CPU s/GB). Note that the `pure` feature alone does **not** remove SIMD.

The rayon rows under contention are not reliable: in the SSE4.1 build, all-core BLAKE3 came out slower than single-thread BLAKE3.

### From a file, 1 GiB, median of 3 runs, default build

| Workload | Cold (guest cache dropped) MB/s | CPU s/GB | Warm (page cache) MB/s | CPU s/GB |
|---|---|---|---|---|
| read_only (no hashing) | 1974 | 0.209 | 6127 | 0.152 |
| C1 | 460 | 1.906 | 617 | 1.558 |
| C2 | 680 | 1.141 | 1197 | 0.799 |
| C3 | 551 | 1.440 | 1913 | 0.492 |
| C4 | 2194 | 0.385 | 2908 | 0.344 |
| C5 | 801 | 1.207 | 954 | 1.021 |
| C4, all cores (16 MiB reads) | 1590 | 0.418 | 2732 | 0.413 |

### Whole-file cost for small files (ns per file, median of 5, key setup included)

| Size | C1 | C2 | C3 | C4 | C5 |
|---|---|---|---|---|---|
| 0 B | 435 | 377 | 230 | 230 | 227 |
| 1 KiB | 1760 | 1108 | 2007 | 1045 | 1788 |
| 4 KiB | 5908 | 3197 | 2801 | 1411 | 4493 |
| 64 KiB | 90468 | 46202 | 23998 | 13884 | 72271 |
| 1 MiB | 1670589 | 748839 | 332915 | 168356 | 873780 |
| 16 MiB | 34533275 | 16241006 | 7947263 | 3319691 | 14340376 |

## What this does and does not show

- Measured on this VM: a second full-content keyed pass (C1, C3, C5) roughly doubles CPU seconds per GB compared with hashing the content once and then MACing the 32-byte digest (C2, C4). This held with and without hardware acceleration (for example 1.685 against 0.954 CPU s/GB with SHA-NI, and 7.456 against 3.794 in software).
- Measured on this VM: with the hardware paths, one core of BLAKE3 (AVX-512) used about 4× less CPU per GB than SHA-256 with SHA-NI (0.224 against 0.914 CPU s/GB). With both forced to portable code, the gap was about 2.3× (1.645 against 3.734).
- Not shown: anything about ARM phones. Phones use different instruction sets (the ARMv8 SHA-2 extension and NEON), storage and thermal limits. BUD-HASH and BUD-BAT-S are judged only by the kit.
- Even the slowest x86 software-only figure (C1 at 98 MB/s) is far above BUD-HASH's 6 MB/s. That is an x86 result and does not transfer to a low-end phone.

## Reproduce

```sh
cd spikes/A1-S1
cargo build --release
./target/release/a1-hashbench mem 1024 5
./target/release/a1-hashbench ladder
head -c 1073741824 /dev/urandom > /tmp/f_1GiB && ./target/release/a1-hashbench file /tmp/f_1GiB 3 cold
# software-only variants
RUSTFLAGS='--cfg sha2_backend="soft"' CARGO_TARGET_DIR=target-soft cargo build --release --features blake3-portable
CARGO_TARGET_DIR=target-sse41 cargo build --release --features blake3-sse41-only
```

The same source builds for Windows (checked with `cargo check --target x86_64-pc-windows-gnu`; CPU time is reported as `null` there) and for Android (checked with `cargo check --target aarch64-linux-android --features blake3-pure`. A full NEON build needs the Android NDK, see the kit).

## Evidence

`evidence/*.jsonl`: raw output, one JSON object per line, with `uptime` lines before and after each run.

## Addendum (2026-10-07, A1 synthesis): alternative SHA-256 backends

**Why.** All three skeptics pointed out that `sha2` 0.11 always uses software SHA-256 on 32-bit ARM, so a slow `sha2` on a low-end phone must not by itself trigger a switch to BLAKE3. The A1 decision rule now says: measure other SHA-256 backends on the same device and ABI first. This addendum adds those backends to the benchmark and checks what their code does on 32-bit ARM. Data class `SYN → results`.

**Code changes** (throwaway):
- Optional cargo features `backend-ring` (ring 0.17.14) and `backend-awslc` (aws-lc-rs 1.18.1). These add the workloads `ring_sha256`, `ring_C1_sha256+hmac_content`, `awslc_sha256` and `awslc_C1_sha256+hmac_content` to `mem` and `file`. Default builds are unchanged.
- The `info` line now also prints `at_hwcap`, `at_hwcap2` (raw auxv words, Linux and Android), `target_pointer_width` and `alt_backends`. A 32-bit process can therefore be classified on the phone.
- `soak <path> <secs> [C1|C2]`: the soak can run C1, so the battery cost of C1 and C2 can be compared (DR-A1-1 B vs N).
- `java/MdBench.java`: a platform probe. It times `MessageDigest("SHA-256")` and `Mac("HmacSHA256")` from the default provider (SHA-256, C1, C2) and prints the provider name. On Android, that provider is normally Conscrypt. It runs through `app_process` after `d8`; see the kit.

**What the source code says about 32-bit ARM** (primary sources, read 2026-10-07):

| Backend | 32-bit ARM (`armeabi-v7a`) SHA-256 path | Source |
|---|---|---|
| RustCrypto `sha2` 0.11.0 | Software only ("All other targets: use soft") | `sha2-0.11.0.crate` README (skeptic-verified 2026-10-06) |
| `ring` 0.17.14 | **NEON or plain asm only. No ARMv8 SHA-256 instructions.** The `target_arch = "arm"` branch dispatches `sha256_block_data_order_neon` or `_nohw`; only the `aarch64` branch uses `sha256_block_data_order_hw` | `ring-0.17.14.crate` `src/digest/sha2/sha2_32.rs` lines 30–43 |
| BoringSSL (main) | **Uses the ARMv8 SHA-256 instructions in 32-bit mode when the CPU reports them.** For `OPENSSL_ARM` it defines `SHA256_ASM_HW` with `sha256_hw_capable() = CRYPTO_is_ARMv8_SHA256_capable()`, and `sha256-armv4.pl` emits `sha256h`/`sha256h2` | `google/boringssl @ main`: `crypto/fipsmodule/sha/internal.h`, `crypto/fipsmodule/sha/asm/sha256-armv4.pl` |
| AWS-LC (main), under `aws-lc-rs` | Same as BoringSSL (`SHA256_ASM_HW` for `OPENSSL_ARM`) | `aws/aws-lc @ main`: `crypto/fipsmodule/sha/internal.h` |
| Android platform `MessageDigest` | Default provider is normally Conscrypt, which uses BoringSSL and is updated through Mainline. **Which BoringSSL revision a given phone's Conscrypt carries, and so whether it has the AArch32 hardware path, is not known from source.** The kit measures it | `google/conscrypt @ master` README (lines 13, 22, 28–32, 87) |

So on a 32-bit-only phone whose CPU has the ARMv8 crypto extensions, aws-lc-rs and probably the platform `MessageDigest` can use hardware SHA-256, and `sha2` and `ring` cannot. On an AArch64 core without `HWCAP_SHA2`, every backend is software, and asm (ring, aws-lc, BoringSSL) may still beat `sha2`'s Rust code. That is unmeasured on ARM.

**Measured on x86 (reference only, not a phone).** After the container restart this VM is an "Intel(R) Xeon(R) Processor @ 2.80GHz", 4 vCPU, **without SHA-NI**, with AVX-512. CPU pressure was low (PSI some avg10 0.00–2.73). That makes it a fair comparison of *software* SHA-256 implementations on x86. In memory, 1 GiB, median of 4 runs after one warm-up, two separate runs:

| Workload | MB/s (run 1 / run 2) | CPU s/GB (run 1 / run 2) |
|---|---|---|
| `sha2` sha256 (software, this host) | 201 / 203 | 4.91 / 4.86 |
| `ring` sha256 | 342 / 349 | 2.90 / 2.85 |
| `aws-lc-rs` sha256 | 353 / 340 | 2.83 / 2.92 |
| JVM `MessageDigest` (OpenJDK 21, SUN provider; logic check of `MdBench`) | 326 | 3.04 |
| `sha2` C1 / `ring` C1 / `aws-lc-rs` C1 / JVM C1 | 104 / 171 / 171 / 169 | 9.5 / 5.8 / 5.8 / 5.9 |
| `sha2` C2 / JVM C2 | 210 / 347 | 4.70 / 2.85 |
| blake3 (AVX-512) | 4,761 | 0.208 |

- On this x86 host without SHA-NI, the asm SHA-256 backends used about 40 % less CPU per GB than `sha2`'s software path (2.85–2.92 vs 4.86–4.91 CPU s/GB). This is evidence that the backend choice can matter by a large factor when the SHA-2 instructions are absent. **It does not transfer to ARM.** The phone kit measures that.
- The 2-hashes-per-byte cost of C1 shows up again in every backend (C1 ≈ 2 × SHA-256 CPU).
- **Cross-implementation check (weak):** the first byte of the final ID (`sink`) was identical across `sha2`, `ring`, aws-lc-rs and the JVM probe for SHA-256 (139), C1 (234) and C2 (8). That covers the same data and the same constructions. It is a one-byte check, not a vector test; the A1-S3 vectors are the conformance test.
- **Not done here:** Android cross-builds of the new features. `cargo check --target armv7-linux-androideabi` fails without the std target and NDK, and `aarch64-linux-android` fails in blake3's C build without the NDK compiler. `d8` could not be fetched (`dl.google.com` is blocked from the container), so `MdBench` was not dexed. Both steps are in the kit and are untested.

Raw output: `evidence/mem-altbackends-x86.jsonl`, `evidence/mem-altbackends-x86-run2.jsonl`, `evidence/mem-platform-jvm-x86.jsonl`, `evidence/altbackends-host-2026-10-07.txt`.

Reproduce: `cargo build --release --features backend-ring,backend-awslc && ./target/release/a1-hashbench mem 1024 4`; `cd java && javac --release 8 MdBench.java && java -Xmx2g -cp . MdBench 1024 4`.
