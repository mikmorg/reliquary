# Spike D2-S1 (CT half, emulated): plugin-protocol overhead for a plugin-held ingest key

- **Workstream / plan:** D2, `docs/research/PLAN.md` section "D2." (D2-S1 YubiKey unwrap throughput, exec `CT/OL`)
- **Status:** **emulated, not a real YubiKey.** The real measurement is the OL kit in `docs/research/kits/D2-S1/`.
- **Run by / date:** D2 spike runner (agent), 2026-10-06 (code written 2026-09-29; this is the first run whose evidence was kept)
- **Data-handling class:** `SYN → results` (random 4 KiB objects, throwaway X25519 keys made and deleted inside `/dev/shm`)
- **Budget IDs:** none directly. The pass line (≥ 20 unwraps/s unattended) comes from PLAN D2-S1. BUD-INGEST is context only.

## Hypothesis

The overhead that the age plugin protocol and process model add to a hardware-held key is small next to
the 50 ms per unwrap that 20 unwraps/s allows. If so, D2-S1's pass or fail depends only on the device's
own time (YubiKey PIV ECDH plus PC/SC), which only the OL kit can measure.

## What was built

| Path | What |
|---|---|
| `cmd/age-plugin-swtest/` | A software stand-in for a hardware-key age plugin. Its identity wraps a native `AGE-SECRET-KEY-1…`, and it unwraps native X25519 stanzas through the real plugin protocol (`filippo.io/age/plugin`). It adds no device latency. `SWTEST_DELAY_MS` adds a fixed sleep per unwrap if you want to model a device. |
| `cmd/plugbench/` | A benchmark with three paths: **stock** = the `filippo.io/age` v1.3.1 plugin client, one plugin process per object (what age does); **batched** = one `identity-v1` session carrying 100 headers (file indices 0..99), which the C2SP plugin protocol allows; **native** = in-process X25519 unwrap with no plugin. The OL kit reuses it with `-plugin age-plugin-yubikey -dir …`. |
| `run_emulation.sh` | Runs plugbench 3 times (N = 2,000, batch 100). It then times the age CLI, one `age -d` process (plus one plugin process) per object, over 200 objects, 3 times. |
| `evidence/emulation-results.jsonl` | Raw output of the run below. |

Rebuild: `go build -o bin/ ./cmd/...` (Go ≥ 1.24, fetches `filippo.io/age v1.3.1`). Run: `AGEBIN=<dir with age ≥ 1.3.0> ./run_emulation.sh`.

## Environment

Cloud container, 4 vCPU x86-64, Go 1.24.7, age v1.3.1 CLI (built from the Go module), objects in tmpfs.
Load average was 0.6–1.6 during the run (`loadavg` is recorded on each line). This is a shared VM, not the
homelab, and there was no PC/SC stack and no USB.

## Results (measured 2026-10-06, emulated)

| Path | Run 1 | Run 2 | Run 3 | Median | Per-unwrap time at the median |
|---|---|---|---|---|---|
| Native in-process X25519 unwrap | 6,066/s | 7,413/s | 9,323/s | 7,413/s | 0.13 ms |
| Batched plugin session (100 headers per session) | 4,356/s | 4,076/s | 4,479/s | 4,356/s | 0.23 ms |
| Stock plugin client (one plugin process per object) | 269/s | 392/s | 388/s | 388/s | 2.6 ms |
| age CLI, one `age -d` process per object (plus its plugin process) | 146.5/s | 145.5/s | 146.4/s | 146.4/s | 6.8 ms |

The per-unwrap column is 1 / median rate, which is arithmetic and not a separate measurement.

## Reading against the pass line (≥ 20 unwraps/s unattended)

- Software overhead does not decide D2-S1. Even the slowest path (one age CLI process per object) is about
  7× above 20/s, and the batched path is about 200× above it.
- By arithmetic only: for 20/s, each unwrap has 50 ms in total. On these numbers the plugin and process
  overhead uses about 0.2 ms (batched), 2.6 ms (stock client) or 6.8 ms (CLI per file). That leaves roughly
  43–50 ms for the YubiKey's PIV ECDH, PC/SC and USB (or Proxmox USB passthrough). **No primary source for
  YubiKey PIV P-256 ECDH latency was found** (see the scout findings), so that number is not known here.
- Unattended operation depends on policy, not speed. age-plugin-yubikey 0.5.1 defaults to touch policy
  `Always` (src/builder.rs), and a touch is a person. Only `never` (or PIN-only) identities can be unattended.
  The kit tests both.
- PQ coupling: age-plugin-yubikey writes classic `piv-p256` stanzas. age v1.3.1 refuses to mix
  post-quantum and classic recipients (measured in D2-S2). If OD-06 = post-quantum, a YubiKey cannot hold
  the online ingest key under stock age, whatever the device speed.

**Pass / fail for D2-S1: inconclusive.** The emulation shows only that protocol overhead is not the
bottleneck. The real result needs the OL kit with a spare YubiKey 5.

## Limits

- No YubiKey, no pcscd, no USB passthrough. Device time is zero here.
- Native X25519, not P-256 ECDH. On real hardware the YubiKey does the ECDH and the host does HPKE/ChaCha.
- One shared VM. The native rate varied by 1.5× between runs.
