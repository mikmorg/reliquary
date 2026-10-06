# Kit A2-S1: X25519 vs post-quantum envelope cost on real devices

- **Spike:** A2-S1 (workstream A2, see `docs/research/PLAN.md`, section "A2."). This kit is the owner-lab (OL) part. The container (CT) part has been run: header sizes and x86 throughput are in `spikes/A2-S1/`. Those x86 numbers are **not** a stand-in for any device below.
- **Exec tag:** OL (the CT part is done)
- **Prepared by / date:** A2 spike runner (Wave 1, batch W1-a), 2026-10-06
- **Who runs it:** Owner
- **Time needed:** about 20 min hands-on per device: a one-time build, then about 50 min unattended per phone (two 15-minute battery soaks with a 10-minute cool-down between them), plus charging time.
- **Data-handling class:** `SYN → results`. The benchmark encrypts random bytes it makes in memory. It never reads the camera roll or any user file.

## Purpose

To find out what encrypting every keepsake to a post-quantum (PQ) recipient costs on a phone, compared with today's X25519 recipient, in speed and in battery. Reliquary would use age's `mlkem768x25519` recipient type (ML-KEM-768 + X25519 "X-Wing").

## Hypothesis

1. The PQ cost is a **fixed amount of work per object**: one X-Wing encapsulation per recipient stanza. The bulk encryption (ChaCha20-Poly1305, 64 KiB chunks) is identical, so the relative slowdown shrinks as objects get larger. On the x86 container the extra header-generation cost was about 77 µs per object for one stanza and about 239 µs for two (best of 3 on a contended machine; `spikes/A2-S1/`).
2. On a low-end phone, PQ encryption of photo-sized objects (around 1–4 MiB) loses **≤ 10 %** throughput against X25519 with one stanza.
3. Even for small objects, PQ encryption on the low-end phone stays faster than a 100 Mbit/s uplink (12.5 MB/s), so encryption is never the bottleneck.
4. The battery difference between the PQ and X25519 soaks is within the noise of a 15-minute soak, because the KEM runs once per object.

Any part can be proved wrong by the numbers in the results table.

## Decision it informs

OD-06 (post-quantum recipients from day one) and ADR-0007 (object envelope). DR-A2-1 and DR-A2-2 in `docs/research/a2-object-envelope.md` give the context.

| If the result is… | Then… |
|---|---|
| **Pass**: the header is ≤ 3 KB per object; PQ throughput loss is ≤ 10 % on the low-end phone at the typical object size; and PQ encryption is faster than 12.5 MB/s at every size | PQ from day one (DR-A2-1). The BUD-BAT-S figure goes to H1. |
| **Fail on throughput** (> 10 % loss at the typical size, or slower than 12.5 MB/s) | X25519 on the device now, with a migration plan: the homelab rewraps to PQ at ingest (A2 note §F2 fallback). The owner decides through OD-06. |
| **Fail on header size only** | Already known from the CT run. One stanza (1,627 B) passes; two stanzas (3,184 B) fail. This goes to DR-A2-2 (where the recovery stanza is written), not to this kit. |
| **No result** (no low-end phone, or the build fails) | ADR-0007 records the phone cost as unmeasured. The x86 numbers stay the only evidence, labelled "x86 container, not a phone". |

"Typical object size" comes from the E1 census once it exists. Until then, use the placeholder in `docs/research/corpus/README.md`: Open Images original photo sizes, median 1.30 MB and mean 2.24 MB. That measurement is indicative only; it was taken from the first 50 MiB of the CSV and is not a random sample. Record that a placeholder was used.

## Budget IDs cited

- **BUD-BAT-S**: seed battery cost, % per 10 GB. This kit measures the **encryption** share only. The hashing share comes from A1-S1, and network and I/O are not included.
- **BUD-HASH**: cited by PLAN for this spike. The low-end phone class is the one BUD-HASH is defined on. Encryption must not become the slower step than the BUD-HASH floor (≈ 6 MB/s).
- The A2-local rule "PQ header ≤ 3 KB per object, ≤ 10 % throughput loss on a low-end phone" is kept local, as `budgets.md` says. This kit adds no new threshold.

## Equipment

| Item | Exact model or version | Why | Have it? |
|---|---|---|---|
| Low-end Android phone, 3–4 GB RAM (H5 L12c) | | The pass rule is defined on this class | Yes / Buy (H5) / Borrow |
| Mid-range Android phone (H5 L12a or L12b) | | The typical family phone | |
| *(Optional)* Apple Silicon Mac, Windows x86 PC | | Desktop reference | |
| *(Only if OD-01 = iOS in v1)* iPhone | | No scripted path in this kit (see step 12) | |
| A computer with `adb` (Android platform-tools) and Rust (rustup) | | Builds and runs the benchmark | |
| Android NDK (r26 or newer) and `cargo-ndk` | | Cross-compiles the benchmark | |

**Software and files needed:** the spike source in `spikes/A2-S2/` (one crate serves A2-S1 to A2-S4), and `run-android.sh` in this folder. The container checked that the crate **compiles** for `aarch64-linux-android` and `aarch64-apple-ios` (`cargo check`). It was **not linked or run** on either; there is no NDK in the container.

## Before you start

- [ ] Each phone: developer options on, and **wireless debugging** paired (Android 11 or newer), so the phone is not charging while it is measured.
- [ ] Charge each phone to 100 %, then unplug it. Take the case off and put the phone on a table, screen off.
- [ ] Close other apps. Note the room temperature.

## Procedure

Do the steps in order. After each step, write down what you saw in the results table, even if it looks unimportant. If something unexpected happens, stop, take a screenshot or photo, and write it down.

### Build (once)

1. On the build computer: `rustup target add aarch64-linux-android` and `cargo install cargo-ndk`.
   **You should see:** both finish without errors.
2. Run `adb shell getprop ro.product.cpu.abilist` with each phone connected.
   **You should see:** a list starting with `arm64-v8a`. If it shows only `armeabi-v7a`, write that down. Then also run `rustup target add armv7-linux-androideabi` and use `-t armeabi-v7a` in step 3.
3. In `spikes/A2-S2/`, run `cargo ndk -t arm64-v8a build --release`.
   **You should see:** a binary at `target/aarch64-linux-android/release/a2-envelope-spike`.
4. *(Optional sanity check)* `adb push` the binary to `/data/local/tmp/`, then run `adb shell /data/local/tmp/a2-envelope-spike bench-kem --iters 50`.
   **You should see:** JSON with `"header_len":168` for `x25519x1`, `1627` for `pqx1` and `3184` for `pqx2`. Different header lengths mean the build is wrong: stop.

### Android phones (low-end first, then mid-range)

5. Connect the phone over wireless debugging and unplug the USB cable. `adb devices` should list exactly one device, by IP address.
6. From this kit folder run `./run-android.sh <path to the binary from step 3> lowend` (or `midrange`).
   **You should see:**
   1. device facts;
   2. three `bench-kem` JSON blocks;
   3. ten `bench-obj` JSON blocks;
   4. about 90 `soak` lines for X25519 (one every 10 s);
   5. a 10-minute pause;
   6. about 90 `soak` lines for PQ;
   7. "Done".
7. Recharge the phone to 100 % before the next phone or any rerun.
8. To use a different soak object size (for example 2 MiB, closer to a photo), run `SOAK_SIZE=2097152 ./run-android.sh … lowend-2m`. The default is 100 KiB, the small-object worst case.

### Desktop (optional reference)

9. Mac or Linux: in `spikes/A2-S2/`, run `cargo build --release`, then:
   - `./target/release/a2-envelope-spike bench-kem --iters 2000`
   - `./target/release/a2-envelope-spike bench-obj --size 1048576 --count 200`
   Save both outputs.
10. Windows: the same commands in PowerShell, with `.exe`. The crate uses Unix file APIs in its upload engine, so the Windows build may fail. If it does, record "No result (build)" and move on; a desktop number is not needed for the pass rule.
11. Laptop battery soaks are optional: `soak --profile x25519 --seconds 900`, then `soak --profile pq --seconds 900`, noting battery % before and after each.

### iPhone (only if OD-01 puts iOS in v1)

12. There is no scripted path. A command-line binary needs an app wrapper to run on iOS, and none was tried for this kit. Record "No result" and ask for an iOS kit if OD-01 says iOS in v1. Note that Apple's CryptoKit has X-Wing only from iOS 26 (A2 note C18), so a Rust core is the expected path.

**Stop and record "No result" if:** the build fails, the phone asks for a permission you do not want to grant, or the phone gets too hot to hold comfortably. In that case press Ctrl-C and write down the time.

## Cleaning up

1. The script deletes `/data/local/tmp/a2` at the end. Check with `adb shell ls /data/local/tmp`.
2. Turn off wireless debugging and developer options if the phone is not a dedicated test phone.

## Data handling

- Class `SYN → results`. The only inputs are random bytes the benchmark makes in memory.
- What may be committed: MB/s, objects/s, µs per header, battery % and charge counter before and after, temperatures, device model, SoC, OS version and CPU feature flags.
- Nothing from the phone's own files is read or written, and nothing outside `/data/local/tmp/a2` is touched.

## How to read the numbers

- **`bench-kem`**: `gen_us` is the cost of making one object header on the device. `open_us` is the cost of opening one (the homelab side; shown for reference). Take the **lowest** value over the 3 rounds.
- **`bench-obj`**: whole-object encryption, in memory: header plus all chunks.
  - **PQ throughput loss at size S** = 1 − (`pqx1` MB/s ÷ `x25519x1` MB/s), using the best of the 2 rounds for each.
  - Do the same with `pqx2` for the two-stanza case (DR-A2-2, option P2).
- **Uplink check:** `pqx1` MB/s at every size should exceed 12.5 MB/s (100 Mbit/s).
- **BUD-BAT-S, encryption share** (% per 10 GB) = (battery % before − after) ÷ (GB encrypted ÷ 10). GB encrypted is in the soak's final `done` line (`bytes` ÷ 1e9). If "charge counter" (µAh) was shown, compute the µAh figure too; it is finer-grained than %.
  - **PQ battery overhead** = the PQ figure minus the X25519 figure. With 15-minute soaks, a difference of 1 % or less is within noise; say so.
- **Throttling:** compare the median `MB_per_s` of the first 2 minutes of a soak with the last 2 minutes.

## Reference: x86 container numbers (CT part, not a phone)

From `spikes/A2-S1/evidence/`. The container was an Intel Xeon @ 2.10 GHz with 4 vCPUs, shared with other spike runs. Best of 3 rounds; whole-object encryption in memory; default (SIMD) build.

| Object size | X25519 MB/s | PQ ×1 MB/s (loss) | PQ ×2 MB/s (loss) |
|---|---|---|---|
| 16 KiB | 179.3 | 86.3 (51.9 %) | 48.3 (73.1 %) |
| 100 KiB | 603.9 | 381.7 (36.8 %) | 244.9 (59.4 %) |
| 1 MiB | 981.7 | 839.0 (14.5 %) | 732.6 (25.4 %) |
| 4 MiB | 1,011.1 | 964.1 (4.6 %) | 926.5 (8.4 %) |
| 25 MiB | 1,011.7 | 1,009.9 (0.2 %) | 1,047.8 (−3.6 %, noise) |

Header generation, best of 3: X25519 80.7 µs, PQ ×1 157.4 µs, PQ ×2 319.4 µs. The load average during the run was 7.6–9.1 on 4 vCPUs, so differences of a few percent are noise.

Use these only to sanity-check the shape of the phone results. Do not substitute them for phone numbers.

## Results

Copy this section into `docs/research/kits/A2-S1/results.md` and fill it in. Do not edit numbers afterwards; add a note instead.

- **Run by / date / place:** <...>
- **Hardware and OS actually used:** <exact models and versions; say if anything differed from the Equipment list>
- **Emulator or VM used instead of real hardware?** No | Yes: <what, and why>
- **Typical object size used for the pass rule:** <E1 census value, or "placeholder: median 1.30 MB / mean 2.24 MB, indicative, corpus/README.md">

| Device class | Model / SoC / OS / ABI | `gen_us` X25519 / PQ×1 / PQ×2 | MB/s at 16 KiB, 100 KiB, 1 MiB, 4 MiB, 25 MiB: X25519 | same: PQ×1 | same: PQ×2 | Soak X25519: battery % before → after, charge counter, GB | Soak PQ: same | First 2 min vs last 2 min MB/s (both soaks) |
|---|---|---|---|---|---|---|---|---|
| Low-end Android | | | | | | | | |
| Mid-range Android | | | | | | | | |
| Mac / Windows (optional) | | | | | | | | |

| Pass criterion | Budget ID | Measured value | Pass / Fail / No result |
|---|---|---|---|
| Header ≤ 3 KB per object (1 PQ stanza) | A2-local | 1,627 B (CT, exact; confirmed by step 4) | |
| Header ≤ 3 KB per object (2 PQ stanzas, DR-A2-2 option P2) | A2-local | 3,184 B (CT, exact) | Fail (known) |
| PQ×1 throughput loss ≤ 10 % on the low-end phone at the typical object size | A2-local | | |
| PQ×1 encryption > 12.5 MB/s at every size on the low-end phone | — (uplink reference) | | |
| Encryption share of BUD-BAT-S recorded (X25519 and PQ) | BUD-BAT-S | | |

- **Overall:** Pass | Fail | No result
- **Surprises and points of confusion:** <...>
- **Follow-ups for the workstream:** <...>
