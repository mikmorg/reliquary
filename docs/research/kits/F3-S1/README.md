# Kit F3-S1: size fingerprinting on the owner's library (aggregates only)

- **Spike:** F3-S1 (workstream F3; see `docs/research/PLAN.md`). This kit is the owner-library leg. The public-corpus leg has already run: `spikes/F3-S1/README.md`.
- **Exec tag:** CT in PLAN for the public part. This leg needs the owner's homelab, so it runs as an owner-lab step.
- **Prepared by / date:** F3 spike runner, 2026-09-29
- **Who runs it:** Owner
- **Time needed:** about 10 minutes hands-on. Metadata-only mode is fast: the script took 0.3 s for 25,000 files on the synthetic rehearsal, and real disks will be slower. `--dedup-sha256` reads every byte, so plan for hours on 2–10 TB.
- **Data-handling class:** `FAM → AGG`. The script reads file sizes and names only to put each file in a category, and prints statistics. Its output goes through H3's output check (`docs/research/h3-research-data-governance.md` §4) before it leaves the homelab.

## Purpose

Find out whether the family library's exact file sizes are as unique as the public corpora suggest, and what padding would cost on the real mix of photos, videos and documents.

## Hypothesis

More than 50 % of the files in the owner's library have a unique exact size. Padmé padding cuts that to near 0 % at under 3 % storage cost.

## Decision it informs

| If the result is… | Then… |
|---|---|
| **Pass**: more than 50 % unique today **and** Padmé costs under 3 % | Adopt Padmé in object format v1 (A2 / ADR-0007; DR-F3-1 in the F3 note) |
| **Fail** on uniqueness (50 % or less) | Record exact sizes as an accepted risk under AR-05 (OD-17); padding is optional |
| **Fail** on cost (3 % or more) | Record exact sizes as an accepted risk, or look at padding only below a size threshold (a new A2 question) |
| **No result** | The decision rests on the public-corpus leg alone (pass for Padmé at per-device and family photo scale), and ADR-0007 says so |

## Budget IDs cited

None. The thresholds (50 %, 3 %) come from PLAN F3-S1, and no budget ID covers storage overhead. BUD-CLOUD is affected indirectly.

## Equipment

| Item | Exact model or version | Why | Have it? |
|---|---|---|---|
| Homelab host or VM that can read the library | any Linux with Python ≥ 3.8 | Runs the script next to the data | Yes |
| Read-only access to the library path(s) | — | The script only lists and stats files | Yes |

**Software and files needed:** `f3s1_owner_library.py` (this folder; standard library only).

## Before you start

- [ ] Copy `f3s1_owner_library.py` to the homelab, into the private store, not a synced folder.
- [ ] Decide which folders count as "the library", for example the photo archive plus the documents share. Use the same roots you would back up.
- [ ] Mount the library read-only if you can.

## Procedure

1. Run `python3 f3s1_owner_library.py /path/to/library [/another/root ...] > f3s1_owner_agg.json`.
   **You should see:** no output on the screen, and a JSON file of a few kilobytes.
2. Optional, if you have hours to spare: run it again with `--dedup-sha256` so identical copies count once (Reliquary stores them once).
   **You should see:** the same shape of file, with `"content_dedup": "sha256"`.
3. Open the JSON. Check it against H3 §4:
   - no names or paths;
   - sizes only as percentages, medians and log2 bins;
   - log2 bins with fewer than 10 files show `"<10"`;
   - categories with fewer than 50 files show `"suppressed": true`.
4. If it passes the check, paste the JSON (or only the `all` and `by_category` blocks) into `results.md` next to this README.

**Stop and record "No result" if:** the script reports a large `unreadable_entries` count (permissions), or the library is not mounted.

## Cleaning up

1. Delete `f3s1_owner_agg.json` from the homelab once the checked copy is saved. It holds only aggregates, but there is no need to keep two copies.
2. Nothing else is written.

## Data handling

- The script never prints or writes names, paths or per-file sizes (H3 R2, R3, R11). It reads file names only to map extensions to photo / video / document / other.
- Hard links count once. Empty files are skipped.
- What may leave the homelab: the checked JSON (AGG).

## Results

Copy this section into `docs/research/kits/F3-S1/results.md` and fill it in. Do not edit numbers afterwards; add a note instead.

- **Run by / date / place:**
- **Roots scanned (describe, do not paste paths):** e.g. "photo archive + documents share"
- **Content dedup:** none / sha256

| Pass criterion | Budget ID | Measured value | Pass / Fail / No result |
|---|---|---|---|
| > 50 % of files have a unique exact size (`all.exact.unique_share`) | — | | |
| Padmé storage overhead < 3 % (`all.padme.overhead_byte_weighted_pct`) | — | | |
| (for comparison) 64 KiB-bucket overhead (`all.bucket_64KiB.overhead_byte_weighted_pct`) | — | | |

| Category | Files | Exact unique | Padmé unique | Padmé cost | 64 KiB cost |
|---|---|---|---|---|---|
| photo | | | | | |
| video | | | | | |
| document | | | | | |
| other | | | | | |

- **Overall:** Pass | Fail | No result
- **Surprises:**
- **Follow-ups for F3 / A2:**
