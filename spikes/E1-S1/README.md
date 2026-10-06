# Spike E1-S1 (CT part): aggregate-only census script (THROWAWAY)

> **This is throwaway spike code, not production code.** It exists to check that the census
> design in `docs/research/e1-family-research-census.md` §3 works. It was rehearsed on
> **synthetic data only** (data class `SYN → results`). It has never been run on a family
> device. The family run is kit [`docs/research/kits/E1-S1/`](../../docs/research/kits/E1-S1/README.md).

- **Spike:** E1-S1 "Census script on 3 devices" (PLAN E1). This folder covers the CT build and the
  rehearsal. The FM run is the kit.
- **Run by / date:** spike runner (agent), 2026-09-29, in the research container: Linux 6.18 x86_64,
  4 vCPU, rustc 1.94.1, ext4 on a virtual disk, plus tmpfs for the 500k-file tree.
- **Budget IDs:** none binds it directly. E1-S1's "< 10 min" is a local threshold. BUD-SCAN
  (500k files in < 5 min) is related, and the budget sheet's overlap table should record that
  (hand-off to H1).

## What it does

`census/` is a single Rust binary with no runtime dependencies. Its dependencies are `infer` 0.22.0
and `nom-exif` 3.8.0 (both MIT).

1. **Walks** the home folder, or the `--root` folders, with `std::fs::read_dir`. It does not
   follow symlinks and does not cross into other filesystems (unix `dev`). It does not use `jwalk`,
   which is deprecated, or `dua-core`, which hides the attribute bits.
2. **Checks for cloud placeholders before any read**, using only the directory-entry metadata:
   - Windows: `FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS | RECALL_ON_OPEN | OFFLINE`, via
     `MetadataExt::file_attributes`;
   - macOS: `SF_DATALESS` via `std::os::darwin::fs::MetadataExt::st_flags`.

   A placeholder is **never opened**. It is counted by extension into `census_cloud_only.csv`.
3. **Classifies by extension first**, into a fixed vocabulary of categories and extension groups.
   Only local files with no known extension are sniffed with `infer` (8 KiB read). `--no-sniff`
   turns sniffing off.
   - Inside a `.photoslibrary` package, only `originals/` (or `Masters/`) counts as media.
     Everything else is `library-internal`.
4. **Optional `--exif`:** reads the capture month and camera make/model from local photos and
   videos with `nom-exif`. Without it, or when a file has no metadata, the month comes from the file
   modification time and is labelled `mtime`.
5. **Location class:** each file gets a coarse, fixed class computed from its path on the
   device: `pictures`, `videos`, `documents`, `desktop`, `downloads`, `music`,
   `cloud-sync-folder`, `messaging-app`, `app-data-or-cache`, `apple-photos-library`, `root` or
   `other`. The path itself is never stored.
6. **Output (H3 §7.6 and §4):**

   | File | Contents |
   |---|---|
   | `census_local.csv` | `category,ext_group,log2_bin,count,bytes` for local files |
   | `census_cloud_only.csv` | The same columns for placeholders (logical size) |
   | `census_locations.csv` | Location class × local/cloud-only × category |
   | `census_months.csv` | Media by month: the last 24 months, plus `earlier`, `future` and `unknown` |
   | `census_cameras.csv` | Camera make and model (only with `--exif`; H3 allows models, not serials) |
   | `census_device.csv` | OS, architecture, run time, counters. No hostname or user name. |
   | `census_candidate_folders.csv` | Only with `--list-candidate-folders`: a count |

   - Cells with a count below 5 are written as `<5` with no bytes.
   - The capture date is never finer than the month.
7. **Show before save (H3 R6):** everything that would be saved is printed first, followed by a
   plain-words summary. The tool then asks "Save …? Type yes or no". Any answer other than yes
   saves nothing. The tool never uploads anything.
   - `--list-candidate-folders` also prints, **on the screen only**, the folders outside the usual
     places that hold 20 or more photos or videos. This supports the E1-S1 criterion "at least one
     unmentioned keepsake location found". Only the number of such folders is saved.

Emulation feature `emulate-placeholders` (Linux rehearsal only): a regular file with the sticky bit
set stands in for a cloud placeholder. It is **not** a real OneDrive or iCloud placeholder.

## How to rerun

```
./run_rehearsal.sh /path/to/workdir [/dev/shm/bigtree]
```

The script builds both variants and type-checks the Windows and macOS targets (`rustup target add
x86_64-pc-windows-gnu aarch64-apple-darwin` first). It then generates `gen_home.py` SYN trees,
runs the census, audits `open()` calls with `strace`, and runs `check.py`. `check.py` compares the
output with the generator's truth and applies the H3 §4 output check mechanically.

## Results (measured 2026-09-29; log: `evidence/rehearsal-2026-09-29.log`)

| Check | Result |
|---|---|
| Builds for Linux; `cargo check` passes for `x86_64-pc-windows-gnu` and `aarch64-apple-darwin` | Yes. The Windows and macOS placeholder code **compiles but has not run** on either OS. |
| Scale-1 SYN home (23,805 files, 59.7 GB logical), `--exif`: census totals equal generator truth per category × state and per location class; EXIF months and camera-model counts equal truth | 34/34 checks passed |
| H3 §4 mechanised checks: no name fragment (the marker `Qx7`), no path separators, no non-ASCII text, no home or user words, no day-level dates, no hash-like strings, every cell ≥ 5 or `<5` | Passed (part of the 34) |
| `open()` audit (strace), default mode: regular-file opens | **400**: exactly the 400 local files with no extension (sniffed). **0** of the 550 emulated placeholders. |
| `open()` audit, `--exif` mode | 8,950 opens (media files plus sniffed files). **0** emulated placeholders. |
| Consent prompt: answering "no" or pressing Enter | Nothing saved |
| Time, scale 1 on ext4, cold cache (after `drop_caches`) | Default: 0.3–0.4 s; `--exif`: 1.4 s (3 runs each). An earlier ad hoc `--exif` run straight after generation took 7.1 s (writeback probably still in progress). |
| Time, 499,905 files on **tmpfs** (RAM), warm | Default: 1.5–1.9 s; `--exif`: 5.7–5.8 s (3 runs each). Earlier ad hoc runs: 2.1–2.6 s and 5.9–7.4 s. |
| Sniffing misclassification at 500k scale | 2 of 4,200 extensionless **random-content** files were sniffed as `app-or-system` binaries (a false signature match by `infer`). `check.py` flags this as its only failure (33/34). Real extensionless files are not random bytes, so this rate is not a prediction. |

## What this does and does not show

- **Shows:**
  - The design produces H3 §7.6 aggregates correctly on SYN data.
  - It exports no names or paths.
  - It never opens a file its platform check marks as a placeholder.
  - Classification and walking cost little CPU. 500k files take seconds in RAM, far below both
    "< 10 min" and BUD-SCAN.
- **Does not show:**
  - Timing on a relative's device (HDD or SSD, Windows Defender or other EDR scanning each open,
    cold cache, a slow laptop). That is the kit's job.
  - That the Windows and macOS placeholder checks are right on real OneDrive and iCloud Drive
    placeholders. The Windows and macOS code has only been compiled.
  - Whether opening a placeholder would in fact hydrate it (analyst open question C10).
  - HEIC EXIF, or real MOV/MP4 metadata. The SYN HEIC and video headers carry no metadata, so
    those files fell back to `mtime` months. `nom-exif` handling of real iPhone and Android files
    is untested here.
  - Android or iOS. There is no phone census in this spike (see the E1-S2 kit).
- **Known limitations of the spike:**
  - The walk is single-threaded.
  - Unreadable directories are counted, but the container runs as root, so the "not readable"
    path was not exercised.
  - `exif_failed` counts media with no parsable metadata (for example memes and screenshots). It
    is not a count of errors.
  - The location vocabulary is English-only: localised folder names such as "Bilder" fall into
    `other`.
