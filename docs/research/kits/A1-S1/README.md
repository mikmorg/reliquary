# Kit A1-S1: hash and dedup-ID speed and battery cost on real devices

- **Spike:** A1-S1 (workstream A1, see `docs/research/PLAN.md`), the owner-lab part. The container part (an x86 reference run) has been done; its numbers are in `spikes/A1-S1/evidence/` and are **not** a stand-in for any device below.
- **Exec tag:** OL
- **Prepared by / date:** A1 spike runner (Wave 1, batch W1-b), 2026-09-29
- **Who runs it:** Owner
- **Time needed:** about 1.5 h hands-on per device (a build once, then about 50 min of unattended running per device, of which 30 min is the battery soak), plus charging time
- **Data-handling class:** `SYN → results`. The benchmark reads only random bytes it creates. It never reads the camera roll or any user file.

## Purpose

To find out how fast each candidate dedup-ID construction runs on the family's kinds of devices, whether a phone slows down as it heats up, and how much battery a first backup pass costs per 10 GB.

## Hypothesis

1. On ARMv8 phones whose CPU has the SHA-2 instructions, SHA-256 (and so constructions C1/C2) reaches at least the BUD-HASH floor (about 6 MB/s effective, including reading the file) with a wide margin, so the choice between SHA-256 and BLAKE3 does not decide whether the budget is met.
2. On a phone **without** the SHA-2 instructions (possible on the cheapest devices), SHA-256 falls to a software speed and BLAKE3 (NEON) is clearly faster.
3. C2 ("SHA-256 once, then HMAC over the 32-byte digest") costs about half of C1 ("SHA-256 and HMAC both over the content") on every device, as it does on the x86 reference.
4. Reading the file, not hashing it, limits the effective speed on at least one phone class. If so, the choice between SHA-256 and BLAKE3 hardly matters for time and matters only for battery.

Each part can be proved wrong by the numbers in the results table.

## Decision it informs

ADR-0006 (content identity and dedup ID): which hash (SHA-256 or BLAKE3) and which construction (C1 to C5). It also sets the target for BUD-BAT-S.

| If the result is… | Then… |
|---|---|
| **Pass**: the chosen algorithm meets BUD-HASH on the low-end phone, measured on the file test, and the 30-minute soak shows no sustained drop that would take it below BUD-HASH; MB/s and BUD-BAT-S (% per 10 GB) are recorded for every device | The chosen algorithm and construction stand in ADR-0006. The BUD-BAT-S value goes to H1 as the proposed target. |
| **Fail**: the SHA-256 constructions miss BUD-HASH on the low-end phone (for example no SHA-2 instructions) while BLAKE3 meets it | ADR-0006 weighs BLAKE3 (C3/C4) against SHA-256. The minimum phone specification (SHA-2 instructions required) becomes an alternative for the owner to decide. |
| **Fail for every construction** | The first-pass plan changes (charging-only seeding over several nights, or a USB seed from a desktop). This goes to E2/B2 and the owner. |
| **No result** (no low-end phone, or the build fails) | ADR-0006 records that the phone numbers are unmeasured. The x86 reference and the published claims stay the only evidence, labelled as such. |

## Budget IDs cited

- **BUD-HASH**: first pass of a 128 GB library within one 6 h charge window on a low-end phone (≈ 6 MB/s effective, including I/O); stretch goal 50 MB/s compute.
- **BUD-BAT-S**: seed battery cost, reported as % per 10 GB. The target is set after this spike.

No new threshold is introduced here. "Thermal throttling" is judged against BUD-HASH: a slowdown that stays above BUD-HASH still passes.

## Equipment

The four device classes follow the H5 hardware list (L12a–c, L19). An iPhone is included only if OD-01 puts iOS in v1.

| Item | Exact model or version | Why | Have it? |
|---|---|---|---|
| Low-end Android phone, 3–4 GB RAM (H5 L12c) | | The BUD-HASH floor is defined on this class | Yes / Buy (H5) / Borrow |
| Mid-range Android phone: Samsung or Pixel (H5 L12a or L12b) | | The typical family phone | |
| Windows 11 PC or laptop, x86 (H5) | | Desktop class | |
| Apple Silicon Mac (H5) | | Desktop class | |
| *(Only if OD-01 = iOS in v1)* iPhone (H5 L18) | | Phone class | |
| A computer with `adb` (Android platform-tools) and Rust (rustup) | | Builds and runs the benchmark | |
| Android NDK (r26 or newer) and `cargo-ndk` | | Cross-compiles the benchmark for the phones | |

**Software and files needed:** `spikes/A1-S1/` (the benchmark source); `run-android.sh` and `run-desktop.sh` in this folder. Every test file is made by the scripts from random bytes.

## Before you start

- [ ] Each phone: developer options on and USB debugging allowed. For the battery part, **wireless debugging** (Android 11 or newer) is needed so the phone is not charging while it is measured.
- [ ] Each phone: at least 5 GB of free internal storage.
- [ ] Charge each device to 100 %, then unplug it. Laptops run the soak on battery.
- [ ] Note the room temperature. Take phone cases off. Put each phone on a table, not in a hand or on a charger.
- [ ] Close other apps. Turn on flight mode after wireless debugging is connected, if the connection survives it; otherwise leave Wi-Fi on and note that.

## Procedure

Do the steps in order. After each step, write down what you saw in the results table, even if it looks unimportant. If something unexpected happens, stop, take a screenshot or photo, and write it down.

### Build the benchmark (once)

1. On the build computer, install the Android targets and the NDK helper:
   `rustup target add aarch64-linux-android armv7-linux-androideabi` and `cargo install cargo-ndk`.
   **You should see:** both commands finish without errors.
2. Connect each Android phone and run `adb shell getprop ro.product.cpu.abilist`.
   **You should see:** a list that starts with `arm64-v8a`. If it shows **only** `armeabi-v7a` (a 32-bit phone), write that down; it matters for the result.
3. In `spikes/A1-S1/`, build for 64-bit phones: `cargo ndk -t arm64-v8a build --release`.
   For a 32-bit-only phone, instead run `cargo ndk -t armeabi-v7a build --release --features blake3/neon`.
   **You should see:** a binary at `target/aarch64-linux-android/release/a1-hashbench` (or `target/armv7-linux-androideabi/release/a1-hashbench`).
4. *(Optional, also useful)* Build the SHA-256 software-only variant, so the phone's hardware SHA-256 can be compared with a software fallback on the same phone:
   `RUSTFLAGS='--cfg sha2_backend="soft"' CARGO_TARGET_DIR=target-soft cargo ndk -t arm64-v8a build --release`.

### Android phones (low-end first, then mid-range)

5. Connect the phone over **wireless debugging** (`adb pair`, then `adb connect`) and unplug the USB cable. Run `adb devices`.
   **You should see:** exactly one device, listed by IP address.
6. From this kit folder run `./run-android.sh <path to the binary from step 3> lowend` (or `midrange`).
   **You should see:** device facts, then lines of JSON for `info`, `mem`, `ladder` and `file`, then about 180 `soak` lines (one every 10 s for 30 min), then "Done".
   Check the `info` line: `"sha2":true` means the CPU has the SHA-2 instructions. Write this down; it is the most important single fact about the phone.
7. If you built the software-only variant in step 4, run `adb push target-soft/aarch64-linux-android/release/a1-hashbench /data/local/tmp/a1soft` then `adb shell /data/local/tmp/a1soft mem 256 3`, and save the output. Then `adb shell rm /data/local/tmp/a1soft`.
8. Recharge the phone to 100 % before the next phone or any rerun.

### Mac

9. On battery at 100 %, in `spikes/A1-S1/`, run `sh ../../docs/research/kits/A1-S1/run-desktop.sh mac`.
   **You should see:** the same JSON sections as on Android, then "Done".
10. *(Optional)* In a second terminal during the soak, `sudo powermetrics -i 10000 -n 6 > powermetrics.txt` records CPU power. The flag names were not checked for this kit; see `man powermetrics` if they differ.

### Windows PC or laptop

11. Install Rust with rustup (MSVC toolchain). In PowerShell, in `spikes\A1-S1\`, run `cargo build --release`.
12. Run `.\target\release\a1-hashbench.exe mem 1024 5 > mem.jsonl` and `.\target\release\a1-hashbench.exe ladder > ladder.jsonl`.
13. Make the test file: `fsutil file createnew $env:TEMP\a1_zero 4294967297` makes a file of zeros, which is enough for hashing speed but may read unrealistically fast. Prefer random bytes: `$b = New-Object byte[] 1048576; $r = [Security.Cryptography.RandomNumberGenerator]::Create(); $f = [IO.File]::OpenWrite("$env:TEMP\a1_f"); for ($i=0; $i -lt 4096; $i++) { $r.GetBytes($b); $f.Write($b,0,$b.Length) }; $f.WriteByte(120); $f.Close()`.
14. Run `.\target\release\a1-hashbench.exe file $env:TEMP\a1_f 2 > file.jsonl`. The program's "cold" option does nothing on Windows, so the second run reads from the file cache; write that down.
15. Laptop only: note the battery % from the taskbar, run `.\target\release\a1-hashbench.exe soak $env:TEMP\a1_f 1800 > soak.jsonl`, and note the battery % again. `powercfg /batteryreport` before and after gives mWh figures if you want them.
16. Delete `$env:TEMP\a1_f` and `$env:TEMP\a1_zero`.

### iPhone (only if OD-01 puts iOS in v1)

17. There is no scripted path in this kit. A command-line program cannot run on an iPhone by itself; it needs an app wrapper. A candidate tool is `cargo-dinghy`, which packages Rust binaries to run on iOS devices. It was **not** tried for this kit. Record "No result" and ask for an iOS kit if OD-01 comes back "iOS in v1".

**Stop and record "No result" if:** the build fails, the phone asks for a password or permission you do not want to grant, or the phone gets too hot to hold comfortably (stop the soak with Ctrl-C and write down the time).

## Cleaning up

1. The scripts delete their test files: `/data/local/tmp/a1` on phones and the temporary folder on Mac/Linux. Check with `adb shell ls /data/local/tmp`.
2. Turn off wireless debugging and developer options if the phone is not a dedicated test phone.

## Data handling

- Class `SYN → results`. The only inputs are random bytes the scripts make.
- What may be committed: MB/s, CPU seconds per GB, battery % and charge counter before and after, temperatures, device model, SoC, Android/OS version, and the `info` line.
- Nothing from the phone's own files is read. If the owner's own phone is used, nothing outside `/data/local/tmp/a1` is touched (H3 §5, A1-S1 row).

## How to read the numbers

- `mem` = compute only (data already in memory). `file` = reading plus computing, the closer match to BUD-HASH "effective, including I/O".
- Workload names: `C1` = SHA-256 and HMAC-SHA256 both over the content (the current content-encryption spike design, two hash computations per byte). `C2` = SHA-256 once, then HMAC over the 32-byte digest (one per byte; rotatable from the cache). `C3`/`C4` = the BLAKE3 equivalents. `C5` = SHA-256 plus keyed BLAKE3.
- BUD-BAT-S (% per 10 GB) = (battery % before − battery % after) ÷ (GB hashed during the soak ÷ 10). GB hashed = sum over the soak lines of (MB/s × 10 s) ÷ 1000. If "Charge counter" (µAh) was shown, give the µAh figure too.
- Throttling: compare the median MB/s of the first 5 minutes of soak lines with the last 5 minutes.

## Results

Copy this section into `docs/research/kits/A1-S1/results.md` and fill it in. Do not edit numbers afterwards; add a note instead.

- **Run by / date / place:** <...>
- **Hardware and OS actually used:** <exact models and versions; say if anything differed from the Equipment list>
- **Emulator or VM used instead of real hardware?** No | Yes: <what, and why>

| Device class | Model / SoC / OS | `sha2` / `neon` in `info` | ABI (64/32-bit) | mem MB/s: C1 / C2 / C3 / C4 / C5 | file (4 GiB + 1) MB/s: read_only / C1 / C2 / C4 | soak MB/s: first 5 min / last 5 min | battery % before → after, GB hashed | BUD-BAT-S (% per 10 GB) |
|---|---|---|---|---|---|---|---|---|
| Low-end Android | | | | | | | | |
| Mid-range Android | | | | | | | | |
| Windows x86 | | | | | | | | |
| Apple Silicon Mac | | | | | | | | |
| iPhone (if OD-01) | | | | | | | | |

| Pass criterion | Budget ID | Measured value | Pass / Fail / No result |
|---|---|---|---|
| Chosen algorithm meets BUD-HASH on the low-end phone (file test, effective MB/s) | BUD-HASH | | |
| No thermal throttling below BUD-HASH during the 30-minute soak | BUD-HASH | | |
| MB/s recorded for all device classes | — | | |
| % per 10 GB recorded | BUD-BAT-S | | |

- **Overall:** Pass | Fail | No result
- **Surprises and points of confusion:** <...>
- **Follow-ups for the workstream:** <...>
