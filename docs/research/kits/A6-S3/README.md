# Kit A6-S3 (OL half): hard power-off ×10 of a test VM during ingest

- **Spike:** A6-S3 (workstream A6, see `docs/research/PLAN.md`, section "A6."). The CT half (kill -9 ×100 and LazyFS power-cut emulation) already ran in the container; see `spikes/A6-S3/README.md`.
- **Exec tag:** OL (needs a real hypervisor and real disks).
- **Prepared by / date:** A6 spike runner (agent), 2026-10-06
- **Who runs it:** Owner
- **Time needed:** about 45 min to set up the VM, then about 30 min machine time for 10 cuts.
- **Data-handling class:** `SYN → results`. The corpus is made by `a6cas gen` (random bytes), and the keys are throwaway `SEC` test keys inside the VM. Results are counts only.

## Purpose

The container runs proved two things: that killing the ingest process never loses an acknowledged item, and that it holds up when LazyFS drops all unsynced file data. LazyFS cannot drop directory entries (renames and creates), and nothing in a container exercises a real disk, a real filesystem journal or a hypervisor's write path. This kit cuts the power to a VM 10 times while ingest runs on the real homelab storage stack.

## Hypothesis

After every cut, every item that was ACKed before the cut is in the catalog and the manifest, and its stored files pass the keyless audit. `a6cas recover` puts the store and catalog back in agreement with no manual step. After the last cut, ingest finishes and every object decrypts with the archive key to its expected SHA-256.

## Decision it informs

| If the result is… | Then… |
|---|---|
| **Pass**: no acknowledged item lost, nothing acknowledged before it is durable, store and catalog reconcile automatically (PLAN A6-S3) | The layout's write ordering (temp file, fsync, rename, directory fsync, manifest append and fsync, catalog commit, then ACK) goes into ADR-0012 as specified. |
| **Fail** (any acknowledged item missing, or audit mismatch) | Find the missing barrier (most likely a directory fsync or the disk cache mode), fix it and re-run. If the fault is in ZFS or the hypervisor setting, record the required setting (for example disk cache mode) in C5/C6. |
| **No result** | ADR-0012 cites only the container evidence, marked "emulated". |

## Budget IDs cited

None. The pass line is PLAN A6-S3's.

## Equipment

| Item | Exact model or version | Why | Have it? |
|---|---|---|---|
| Proxmox host with `qm` | Record the PVE version | Hard stop of a VM | |
| Test VM (Debian 12/13, 2 vCPU, 4 GB RAM, 40 GB disk) | Record the disk bus, **cache mode** and storage (ZFS zvol or file) | A store on a real disk | |
| A second run with the store on a ZFS dataset inside the VM (optional) | | ZFS's own transaction groups | |

**Software:**

- `a6cas` built from `spikes/A6-S3/a6cas/` (`go build`).
- `python3` in the VM.
- `powercut.sh` from this folder, run on the host.

## Before you start

- [ ] Create the VM and record its disk **cache mode**. The Proxmox default is "No cache": the guest is told a write is complete when it reaches the physical storage write queue, bypassing the host page cache (`pve-docs/qm.adoc`, "Cache Mode", read 2026-10-06). Run the 10 cuts with the default first. If time allows, run 10 more with `writeback` to see the difference.
- [ ] In the VM:
  - `mkdir -p /srv/a6`
  - `a6cas keygen -dir /srv/a6/keys`
  - `a6cas gen -out /srv/a6/corpus -keys /srv/a6/keys -n 3000 -scale 0.3 -seed 11`

  This gives about 3,000 synthetic items. Use a larger `-scale` if ingest finishes in under a minute.
- [ ] Copy a host ssh key into the VM's `root` account, so that `ssh root@<vm>` works with no password.
- [ ] Take a Proxmox snapshot of the VM, so it can be reset.

## Procedure

1. On the host: `VMID=<id> VM=root@<vm-ip> CUTS=10 ./powercut.sh`. **You should see:** for each cut, a line `cut i after Ns`, then `recover {...}`, `audit {...}` and `check {...}`.
2. Watch the `check` lines: `acked_not_in_catalog` and `acked_not_in_manifest` must both be 0. **You should see** `mismatch: 0, missing: 0` on every `audit` line.
3. At the end the script finishes ingest without a cut and prints `truth-final.json`. **You should see** `"all_match": true` and "verify: no FAIL counters".
4. Optional: repeat with the VM disk cache set to `writeback`, or with the store on a ZFS dataset inside the VM.

**Stop and record "No result" if:** the VM does not come back after a cut (record the error), or the host is the production homelab and other VMs are affected.

## Part B (added 2026-10-06): disk full on a real ZFS pool

**Why.** Kopia issue #4348 reports that a repository can be corrupted when the disk fills during a backup. The container run (`spikes/A6-S3/README.md`, "Disk-full fault case") found no violation in 100 trials on tmpfs and on ext4 over a loop device. It could not test ZFS, which is copy-on-write: it keeps back "slop" space, and when it is full it can fail in ways that tmpfs and ext4 do not. This part runs the same harness on a real, throwaway ZFS pool.

**Hypothesis.** When the pool fills, nothing is ACKed unless it is durable. `a6cas recover` works while the pool is still full. Retrying ingest while full ACKs nothing new. Once space is freed, ingest finishes and every object decrypts to its SHA-256.

**Equipment.** Use the same test VM as Part A, with `zfsutils-linux` installed (OpenZFS; record `zfs version`). The script makes its own file-backed pool at `/var/tmp/a6df/a6full.img`, about 3 × the corpus size, so **never run it on the production pool's host**. Set `ENC=1` for a second run on a natively encrypted pool (posture B).

**Procedure.**

1. In the VM, make a corpus that fits the test pool easily, for example `a6cas gen -out /srv/a6/corpus -keys /srv/a6/keys -n 600 -dup 0.1 -scale 0.05 -seed 3` (about 230 MB).
2. Copy the repository's `spikes/A6-S3/harness/diskfull.py` into the VM, at the same relative path as this kit, or set `HARNESS=/path/to/diskfull.py`.
3. Run `A6=/srv/a6 TRIALS=20 ./diskfull-zfs.sh`. If time allows, run it again with `ENC=1`. **You should see** one summary JSON per run.
4. In each summary, read these fields:
   - `violations` must be `{}`;
   - `retry_while_full_new_acks` must be 0;
   - `final_ok` must equal `trials`.

   Also read `recover_while_full_failed`. It is allowed to be non-zero, but only when that trial ACKed nothing. If it is non-zero, open the matching line in `diskfull-zfs.jsonl` and copy the `while_full.recover.err` field into the results.

**Untested.** The author of `diskfull-zfs.sh` could not run it, because the cloud container has no ZFS. It worked with stand-in hooks: tmpfs instead of a pool, and `mount -o remount` instead of destroying the reservation (`--placement external`, 2 trials). The ZFS hooks themselves have never run. If a hook fails, record the error and fix the hook. The harness does not need changing.

## Cleaning up

1. Roll back or delete the test VM. It holds only synthetic data and throwaway keys.
2. Keep the `a6-s3-powercut-*/` folder (logs and JSON counts) for the results.

## Data handling

Synthetic data only (`SYN`). The logs contain record IDs of synthetic items and counts. No family data is involved.

## Results

Copy this section into `docs/research/kits/A6-S3/results.md` and fill it in. Do not edit numbers afterwards; add a note instead.

- **Run by / date / place:**
- **Hardware and OS actually used:** host CPU, PVE version, storage type, VM disk bus and cache mode, guest OS and filesystem
- **Emulator or VM used instead of real hardware?** Yes: a VM hard stop (`qm stop`) stands in for a power cut. Host RAM and the physical drive's own cache are not lost.

| Cut | Seconds into ingest | ACKs before cut | acked_not_in_catalog | acked_not_in_manifest | audit mismatch / missing | recover: tmp removed / quarantined / torn manifest bytes |
|---|---|---|---|---|---|---|
| 1 | | | | | | |

| Pass criterion | Budget ID | Measured value | Pass / Fail / No result |
|---|---|---|---|
| No acknowledged item lost (10 cuts) | — | | |
| Nothing acknowledged before it is durable | — | | |
| Store and catalog reconcile automatically | — | | |

**Part B (disk full on ZFS):**

| Run | `zfs version` | Trials | `failure_kinds` | recover while full ok / failed | retry_while_full_new_acks | violations | final_ok / trials |
|---|---|---|---|---|---|---|---|
| plain dataset | | | | | | | |
| `ENC=1` (native encryption) | | | | | | | |

- **Overall:** Pass | Fail | No result
- **Surprises and points of confusion:**
- **Follow-ups for the workstream:**
