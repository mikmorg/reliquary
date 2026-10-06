# Spike E2-S3: interim-protection recommendation (THROWAWAY tool + owner checklist)

> **Throwaway spike code, not production code.** `stopgap_copy.py` is a small helper the owner can
> use now. It was tested on **synthetic data only** (H3 `SYN → results`). The checklist rests on
> public sources (`PUB → results`); several were blocked (see below).

- **Spike:** E2-S3 "Interim-protection recommendation" (PLAN E2). Exec tag CT.
- **Pass rule (PLAN):** one actionable stopgap per device type the owner can apply this month.
- **Budget IDs:** BUD-SUPPORT (≤ 2 h per month at steady state; proposed). The checklist tells the owner to log the time spent. **No owner time was measured here.**
- **Run by / date:** E2 spike runner (agent), 2026-09-29, research container (Linux 6.18 x86_64, Python 3.11, exiftool 12.76).

## Files

| File | What it is |
|---|---|
| `owner-checklist.md` | The deliverable: one stopgap per device type, what to avoid, and the A9 hand-off |
| `stopgap_copy.py` | Verified copy for visit copies: SHA-256 manifest, provenance, never deletes, keeps both files on conflict, flags files that change during the copy, skips cloud placeholders. Python 3.8+, standard library only. |
| `test_stopgap.py` | Tests on a synthetic tree, plus the EXIF write-back measurement |
| `evidence/test-output.json` | Output of the run below |

## Results (measured; `evidence/test-output.json`)

The synthetic tree has 6 regular files, including a 256 MiB file, an empty file, NFC and NFD variants of the same accented name, an emoji name, a `.DS_Store` and a symlink.

| Test | Result |
|---|---|
| First copy | 6 files `ok`. `.DS_Store` skipped. Symlink recorded as `not-a-regular-file`. Exit code 0. |
| Hashes and mtimes | 6/6 SHA-256 match (source = manifest = copy); 6/6 mtimes preserved |
| Verify | 6 verified, 0 failed |
| Rerun (same visit again) | 6 `already-present`, no new files written |
| Source file edited between visits | Both copies kept (`IMG_0001.JPG` and `IMG_0001.JPG.conflict-<sha8>`). Original copy unchanged. |
| One bit flipped in a copy | Verify reports 1 failed of 7 stored, exit code 1 |
| File appended while being copied | Status `changed-during-copy`. This is a logic test: a hooked `open` appends to the source during the read. |
| Placeholder detection | Returns false on Linux as expected. **Windows (`RECALL_ON_DATA_ACCESS`, `RECALL_ON_OPEN`, `OFFLINE`) and macOS (`SF_DATALESS`) paths are untested.** |
| Copy speed | 271 MB in 2.74 s (99.0 MB/s; an earlier run gave 128.5 MB/s) on the container's virtual disk. **Not representative** of a USB disk or NAS. |

**EXIF write-back measurement.** This checks what happens when Takeout JSON values are written back into a photo. A minimal JPEG was used, and exiftool set `DateTimeOriginal` and GPS values of the kind a Takeout sidecar carries.
- The file's SHA-256 **changed**, and its size went from 124 to 436 bytes.
- exiftool's `ImageDataHash` (SHA-256 of the image data) was **unchanged**.
- So a tool that "fixes" Takeout metadata produces a file that whole-file dedup (A1) will not match to the phone's original, even though the pixels are the same. The checklist says to keep bytes exactly as received.

## Sources behind the checklist

Primary sources that were read, from the E2 scouts on 2026-09-29, via raw.githubusercontent.com:
- icloudpd README (modes, prerequisites, maintainer banner), `docs/size.md` and `docs/reference.md`.
- immich-go `readme.md`, `docs/technical.md` and `docs/best-practices.md`.
- gphotos-sync README (archived 2024-10-04).
- Immich and Ente docs.

Primary sources seen only as **search snippets** (the pages were blocked):
- Google Photos Help 6220791 (backup quality) and 6128843 (Free up space).
- Google Account Help 3024190 (Takeout scheduling).
- Apple Support 108782 (iCloud Photos, Optimize) and 118257 (transfer a copy).

Secondary and unverified:
- 9to5Google 2026-06-01 and Android Authority (incremental Google Photos export).
- Ente on Shared Albums.

Blocked in this run, with no substitute used:
- support.google.com, support.apple.com, privacy.apple.com, takeout.google.com.
- support.microsoft.com (Windows Backup and OneDrive as desktop stopgaps).
- WebSearch: this session's budget was exhausted, so no further setting-wording searches were possible.

## Verdict against the pass rule

**Pass, with a caveat on wording.** Each device type has a stopgap the owner can apply this month:
- Android: Original-quality backup kept on.
- iPhone with a computer: iCloud Photos plus originals downloaded to the computer.
- iPhone without a computer: an owner-run icloudpd Copy, or Apple's transfer.
- Computers: `stopgap_copy.py`, tested.
- Google-only items: Takeout.
- Only-copy items: copied first.

The Android and iPhone steps rely on setting names that could not be checked against the primary pages. The checklist tells the owner to confirm them on his own phone first. The desktop tool is tested on Linux only; its Windows and macOS placeholder checks are untested.
