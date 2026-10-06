# Kit A6-S1 (posture B cells): what ZFS native encryption exposes, and what it needs online

- **Spike:** A6-S1, the at-rest posture decision matrix (workstream A6, see `docs/research/PLAN.md`, section "A6."). The spike is tagged CT → owner.
  - The CT probes for postures A, A′ and C already ran in the container: `spikes/A6-S1/README.md`.
  - This kit covers the cells for posture **B**, "plaintext on ZFS native encryption". They need real OpenZFS, which the container does not have.
- **Exec tag:** OL (a throwaway Linux VM with OpenZFS; no homelab data)
- **Prepared by / date:** A6 spike runner (agent), 2026-10-06
- **Who runs it:** Owner
- **Time needed:** about 20 min hands-on, plus about 10 min machine time
- **Data-handling class:** `SYN → results`. The files are random bytes with made-up names (`Grandma-wedding-1962-NNN.jpg`). The key is a throwaway raw key under `/var/tmp/a6probe`, deleted at the end.

## Purpose

Fill in the posture-B row of the OD-07 matrix (`docs/research/a6-homelab-storage-engine.md` §F1) with observed behaviour, not only man-page text. The kit answers five questions:

- What can someone holding the disks list without the key?
- Does a scrub detect corruption without the key, and does it name the damaged files?
- Does the key come up after a reboot with no person present?
- What does a raw `zfs send` (the future off-site copy) contain?
- How expensive is it to change the key?

## Hypothesis

Taken from the primary man pages, as cited in scout claims C10–C12 of the A6 note. Treat it as unconfirmed until this run.

1. **P1:** a raw send (`-w`) contains neither the file names nor the content markers. A non-raw send contains both.
2. **P2:** with the key unloaded:
   - `zfs list` still shows the dataset and snapshot names and their sizes;
   - `zdb` shows no file names.
3. **P3:**
   - a scrub runs and finishes with the key unloaded;
   - after injected corruption it reports errors, but `zpool status -v` shows no file names.
4. **P4:**
   - with `keylocation=file://…`, `zfs load-key` succeeds with no prompt;
   - with the key loaded, `zpool status -v` names the damaged files.
5. **P5:** `zfs change-key` returns in about a second and rewrites no data.

## Decision it informs

| If the result is… | Then… |
|---|---|
| **Pass**: P1–P5 as stated | The posture-B row of the OD-07 matrix is marked "observed". The owner chooses between A′ and B on the merits set out in the A6 note §F1. |
| **Fail** on P1 (a raw send leaks names or content) or on P3 (a scrub needs the key) | Posture B loses its "easy off-site copy" or "keyless scrub" advantage. The matrix records this. |
| **No result** | The posture-B cells stay "from the man pages only (primary, not observed)". |

## Budget IDs cited

None directly. The posture choice feeds BUD-TTS (unattended unlock), BUD-RESTORE and BUD-RECOVERY, but this kit measures none of them.

## Equipment

| Item | Exact model or version | Why | Have it? |
|---|---|---|---|
| A throwaway Linux VM (Debian 12/13) with `zfsutils-linux`, 2 vCPU, 2 GB RAM, 4 GB free in `/var/tmp` | Record `zfs version` | Real OpenZFS. Community reports advise 2.2.8+ or 2.3.3+ for native encryption with send/receive (A6 note, secondary). | |

**Software and files needed:**

- `zfs-posture-probe.sh` from this folder;
- `python3`, `grep`, `dd`.

## Before you start

- [ ] Use a VM that has **no production pool**. The script creates and destroys a pool named `a6probe`.
- [ ] Become root: `sudo -i`.

## Procedure

1. Copy `zfs-posture-probe.sh` into the VM and run `N=200 ./zfs-posture-probe.sh`. **You should see:**
   - the ZFS version;
   - lines starting `P1` to `P5`;
   - finally `cleaned up`.
2. Copy the folder `a6-s1-zfs-<date>/` out of the VM. It holds `results.txt`, the `zfs list` output and the `zpool status` outputs. Everything in it is synthetic.
3. Fill in the results table below from `results.txt`.

**Stop and record "No result" if:**

- `zpool create` fails (for example, the ZFS module is not loaded); record the error;
- `zfs send` of the non-raw stream fails; record the error and continue.

## Cleaning up

1. The script destroys the pool and deletes `/var/tmp/a6probe`. Check with `zpool list` that `a6probe` is gone.
2. Delete the VM if it was made only for this.

## Data handling

The kit uses synthetic files only. No family data and no real keys are involved. All of `a6-s1-zfs-<date>/` may be pasted into the results.

## Results

Copy this section into `docs/research/kits/A6-S1/results.md` and fill it in. Do not edit numbers afterwards; add a note instead.

- **Run by / date / place:**
- **Hardware and OS actually used:** VM OS, kernel, `zfs version`
- **Emulator or VM used instead of real hardware?** Yes: a VM with a file-backed pool. This is enough for these questions, which are about format and behaviour, not about speed.

| Probe | Expected | Observed (copy the `results.txt` line) | Matches? |
|---|---|---|---|
| P1 raw send: names / markers | 0 / 0 | | |
| P1 non-raw send: names / markers | > 0 / > 0 | | |
| P2 keystatus after import | unavailable | | |
| P2 `zfs list` without key shows names and sizes | yes | | |
| P2 `zdb -dddd` without key: file names found | 0 | | |
| P3 clean scrub without key | completes, 0 errors | | |
| P3 scrub after corruption, key not loaded: names in `status -v` | errors reported, 0 names | | |
| P4 `load-key` from file, no prompt | rc 0 | | |
| P4 `status -v` with key loaded: names | > 0 | | |
| P5 `change-key` time | about 1 s | | |

- **Overall:** Pass | Fail | No result
- **Surprises and points of confusion:**
- **Follow-ups for the workstream:**
