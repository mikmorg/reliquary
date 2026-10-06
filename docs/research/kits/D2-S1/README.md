# Kit D2-S1: YubiKey unwrap throughput for an unattended ingest key

- **Spike:** D2-S1 (workstream D2, see `docs/research/PLAN.md`, section "D2.")
- **Exec tag:** CT/OL. The CT half (plugin-protocol overhead with a software plugin, no YubiKey) was run
  by an agent (code 2026-09-29, evidence-keeping run 2026-10-06, emulated with a software plugin): see `spikes/D2-S1/README.md`. This kit is the OL half, which needs a real YubiKey.
- **Prepared by / date:** D2 spike runner (agent), 2026-09-29
- **Who runs it:** Owner
- **Time needed:** about 1.5 h hands-on, plus an optional 30 min unattended soak
- **Data-handling class:** `SYN → results` (random 4 KiB test objects made by the script). `SEC`: a spare YubiKey's
  PIV PIN, PUK and test identities (never written to results; the YubiKey's PIV applet is reset at the end).

## Purpose

Find out whether a YubiKey can hold the homelab's **online ingest key** and still unwrap object headers
fast enough for unattended ingest, or whether hardware keys should be used only for offline recovery.

## Hypothesis

A YubiKey 5 identity made by `age-plugin-yubikey` with touch policy `never` sustains **≥ 20 header
unwraps per second** without a person present, at least when many headers are sent in one plugin
session. We expect the stock per-object path (one plugin process and one PC/SC session per object) to be
slower than the batched path, and identities with touch policy `always` (the plugin's default) or
`cached` (a touch is reused for 15 seconds, per the plugin source) to need a person and so fail the
"unattended" part.

## Decision it informs

| If the result is… | Then… |
|---|---|
| **Pass**: ≥ 20 unwraps/s unattended, sustained through the soak with 0 errors (policy `never`/`never` or `once`/`never`) | A YubiKey stays a candidate for online-ingest-key custody in ADR-0008, with the policy that passed and the ingest design that reached the rate (per object vs batched sessions). The weaker security of touch `never` (anyone with the key and host access can decrypt) is weighed there. |
| **Fail** | Hardware keys are used only for offline recovery. Online-key custody in ADR-0008 is chosen from the software options (encrypted file, systemd-creds or clevis TPM sealing). |
| **No result** (no spare YubiKey, pcscd will not run, the VM cannot see the key) | ADR-0008 cannot pick YubiKey custody for the online key; it defaults to the Fail branch and records D2-S1 as open. |

Note on post-quantum (OD-06): `age-plugin-yubikey` 0.5.1 writes classic P-256 (`piv-p256`) stanzas.
age v1.3.x refuses to mix post-quantum and classic recipients in one file (measured in D2-S2). If the
owner chooses PQ recipients from day one, a YubiKey cannot hold the online key at all under stock age,
whatever this kit measures. Record the result anyway: it matters if the PQ decision changes.

## Budget IDs cited

- **BUD-INGEST** only as context: ingest must reach ≥ max(100 MB/s, 2 × home downlink). The unwrap rate
  bounds ingest of small objects, so the analyst converts unwraps/s into MB/s for the family's object-size
  mix. The spike's own pass line (≥ 20 unwraps/s) comes from PLAN D2-S1 and is not a budget ID; H1 may want
  to add one.

## Equipment

| Item | Exact model or version | Why | Have it? |
|---|---|---|---|
| **Spare** YubiKey 5 series (not the owner's everyday key) | Record model and firmware from `ykman info` | The plugin changes the default PIN and management key, and the kit resets PIV at the end | Buy (H5) / Borrow |
| Optional: YubiKey 4 | Record firmware | The plugin README says PIN-cache preservation does not work on the 4 series | |
| Linux machine that would run ingest | Record CPU, distro and kernel. Ideally the Proxmox ingest VM with the key passed through by USB; if not, the Proxmox host or a laptop, and say which | The real path includes USB passthrough | |
| pcscd | Distro package; running (`systemctl status pcscd`) | Required by the plugin on Linux | |
| age | v1.3.0 or later (v1.3.2 is current) | Encrypting the test objects; CLI path | |
| age-plugin-yubikey | 0.5.1 (`cargo install age-plugin-yubikey --version 0.5.1`, or the release binary) | The plugin under test | |
| ykman | Any recent version | Record firmware; reset PIV at the end | |
| Go | 1.24 or later | Builds `plugbench` | |

**Software and files needed:** `run-yubikey.sh` (this folder); `plugbench`, built from `spikes/D2-S1`:

```sh
cd spikes/D2-S1 && go build -o ~/bin/ ./cmd/plugbench   # needs network once to fetch filippo.io/age v1.3.1
```

## Before you start

- [ ] Use a **spare** YubiKey. Run `ykman info` and write down model and firmware.
- [ ] `ykman piv info`: note whether PIV has any keys. If it has keys you need, **stop**: use another key.
- [ ] Check `pcscd` is running and `age-plugin-yubikey --list-all` sees the key.
- [ ] If testing in the Proxmox VM: pass the YubiKey through (USB device passthrough) and confirm `--list-all` inside the VM.
- [ ] Close anything else that uses the YubiKey (FIDO2 in a browser, SSH agents). Switching applets ends the PIN session.

## Procedure

Do the steps in order and write what you saw in the results table after each one.

1. Generate identity **A** (fully unattended):
   `age-plugin-yubikey --generate --slot 1 --name d2s1-A --pin-policy never --touch-policy never > idA.txt`
   On first use the plugin asks you to change the default PIN (it sets the PUK to the same value). Pick a test PIN.
   **You should see:** an identity file with a `# Recipient: age1yubikey1...` line and an `AGE-PLUGIN-YUBIKEY-1...` line.
2. Generate identity **B** (PIN once per session, no touch):
   `age-plugin-yubikey --generate --slot 2 --name d2s1-B --pin-policy once --touch-policy never > idB.txt`
3. Generate identity **C** with the plugin defaults (PIN once, touch always):
   `age-plugin-yubikey --generate --slot 3 --name d2s1-C > idC.txt`
4. Run A: `./run-yubikey.sh idA.txt A-never-never 1000`
   **You should see:** three JSON lines with `stock_client_unwraps_per_s` and `batched_unwraps_per_s`, then one `cli_per_file` line. No prompts.
5. Run B: `PLUGBENCH_PIN=<test PIN> ./run-yubikey.sh idB.txt B-once-never 1000`
   Watch for PIN prompts in the CLI part (step 2 of the script). Write down whether the PIN was asked once, every time, or never.
6. Run C with a small count and stay at the key: `PLUGBENCH_PIN=<test PIN> ./run-yubikey.sh idC.txt C-default 20`
   **You should see:** the key blinking and waiting for a touch on each unwrap. Touch it each time and write down roughly how long each touch took. Do not leave it: this is the "not unattended" baseline.
7. Soak the best of A and B: `./run-yubikey.sh idA.txt A-soak 1000 30` (or the B equivalent with `PLUGBENCH_PIN`). Walk away for 30 minutes.
   **You should see:** one line per minute with `batched_unwraps_in_minute` and `errors`.
8. Unplug test (B only): during a B run, unplug and re-plug the key once. Write down what failed, the error message, and whether the next run needed the PIN again.
9. If you have a YubiKey 4, repeat steps 2 and 5 on it.

**Stop and record "No result" if:** `--list-all` does not see the key, `pcscd` cannot start, or the key asks for a management key the plugin cannot set.

## Cleaning up

1. `ykman piv reset` on the spare key (wipes the PIV applet: keys, PIN, PUK). Confirm with `ykman piv info`.
2. Delete `idA.txt`, `idB.txt`, `idC.txt`. The results files contain no secrets; keep them.
3. Stop and remove anything installed only for this kit if you do not want it.

## Data handling

- Test objects are random bytes made by the script and deleted when it exits (`SYN`).
- The PIN is passed only through the `PLUGBENCH_PIN` environment variable and is never written to results.
  Do not paste it into notes. `SEC` material (identity stubs, PIN) stays on the test machine and is wiped by the PIV reset.
- Results may go into the repo as-is: they contain rates, counts, timestamps, versions and error messages.

## Results

Copy this section into `docs/research/kits/D2-S1/results.md` and fill it in. Do not edit numbers afterwards; add a note instead.

- **Run by / date / place:** <...>
- **Hardware and OS actually used:** <YubiKey model and firmware; host CPU, distro, kernel; bare metal or Proxmox VM with USB passthrough>
- **Emulator or VM used instead of real hardware?** No | Yes: <what, and why>
- **Versions:** age <...>, age-plugin-yubikey <...>, pcscd <...>, plugbench commit/date <...>

| Step | Expected | What happened | Measurement (with unit) | Log |
|---|---|---|---|---|
| 4 A never/never | No prompts | | stock: __ /s; batched: __ /s; CLI: __ /s (median of 3) | results-A-never-never.jsonl |
| 5 B once/never | PIN once per session | | stock: __ /s; batched: __ /s; CLI: __ /s; PIN asked: once / every object / never | results-B-once-never.jsonl |
| 6 C default | Touch per unwrap | | seconds per touch: __ | results-C-default.jsonl |
| 7 Soak | ≥ 20/s every minute | | min __ /s, median __ /s over __ min; errors __ | results-*-soak.jsonl |
| 8 Unplug | Recovers after re-plug | | error text: __; PIN re-asked: yes/no | |
| 9 YubiKey 4 | PIN cache not kept | | | |

| Pass criterion | Budget ID | Measured value | Pass / Fail / No result |
|---|---|---|---|
| ≥ 20 unwraps/s unattended (PLAN D2-S1), sustained through the soak with 0 errors | (BUD-INGEST context only) | <policy, path (stock/batched), minimum per-minute rate> | |

- **Overall:** Pass | Fail | No result
- **Surprises:** <prompts, PC/SC errors, VM passthrough problems, heat, blinking>
- **Follow-ups for the workstream:** <e.g. whether the ingest service must batch headers per plugin session>
