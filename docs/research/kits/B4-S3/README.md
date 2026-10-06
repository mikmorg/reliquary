# Kit B4-S3: interim iPhone bridge on one relative's iPhone (500-photo sample)

- **Spike:** B4-S3 (workstream B4, see `docs/research/PLAN.md`)
- **Exec tag:** FM/OL (a relative's iPhone and Apple Account; the owner's homelab or Mac/PC)
- **Prepared by / date:** B4 spike runner (agent), 2026-09-29
- **Who runs it:** Owner with relative
- **Time needed:** 1–2 h at the visit, plus download time (hours for 500 photos, depending on the link), plus a 60-day follow-up for re-authentication (EXT)
- **Data-handling class:** `FAM → AGG` for the 500-photo sample, and `LAB → results` for the reference shots the owner takes during the visit. The photos never enter the repo, logs or an agent session. Only the aggregate JSON printed by `bridge_check.py` leaves the machine.

## Purpose

While iOS is deferred or not yet built, can a relative's iPhone photos reach Reliquary as **originals, with correct dates**, through a bridge the owner already controls? Two variants:

- **Variant H (homelab):** `icloudpd` downloads from the relative's iCloud Photos into the homelab.
- **Variant M (Mac/PC):** a Mac or PC signed in to the relative's Apple Account keeps the originals locally (Photos for Mac with "Download Originals to this Mac", or iCloud for Windows), and Reliquary's desktop client covers those files.

## Hypothesis

A 500-photo sample arrives as originals (full camera resolution; the LAB reference shots are byte-identical), not the "optimised" device copies. Dates are correct: the EXIF capture date is present, and where a bridge sets file dates, they match the capture date rather than the download time. *Proved wrong if* reference shots arrive with different bytes, photos arrive below full resolution, or file dates equal the download time.

## Decision it informs

| If the result is… | Then… |
|---|---|
| **Pass**: 500-photo sample arrives as originals with correct dates (PLAN B4-S3) | A bridge is a workable interim for OD-01's "iOS after pilot with a bridge" option. Which variant also depends on the trust-model notes below. |
| **Fail** (not originals, or wrong dates) | No bridge. OD-01 chooses between "iOS in v1" and "iOS deferred with no bridge". |
| **No result** (relative uses Advanced Data Protection and keeps it on; no consent; no Mac/PC) | Record why. Variant H is impossible with ADP on (see below). Do **not** ask anyone to turn ADP off for this test. |

**The owner must decide these; this kit does not settle them (decision requests, not reopening CLAUDE.md):**
- CLAUDE.md fixes v1 sources as "files on the device only", with iCloud as a roadmap source. Variant H makes iCloud a source, so it needs an explicit owner decision. Variant M reads files on a desktop device and may fit the v1 rule.
- Variant H gives the homelab a long-lived iCloud web session for the relative's whole account, which reaches more than photos. That is beyond "admin can read everything that is backed up". It needs the relative's informed consent and D1/D6 review.
- icloudpd requires "Access iCloud Data on the Web" on and Advanced Data Protection **off**. That lowers the relative's protection against the cloud provider, which is the privacy goal ADR-0001 cares about.

## Budget IDs cited

BUD-SUPPORT (owner time ≤ 2 h/month: re-authentication and babysitting count against it), BUD-TTS (lag from photo taken to stored at home, measured on the reference shots). No new thresholds.

## Equipment

| Item | Exact model or version | Why | Have it? |
|---|---|---|---|
| Relative's iPhone | model + iOS version (record) | source | |
| Owner's laptop (Mac or PC) + USB/Lightning cable | | reference import of LAB shots | |
| Variant H: homelab container or VM with Python 3.9+ or Docker | icloudpd **1.32.3** (the version checked here; `pip install icloudpd==1.32.3`) | bridge | |
| Variant M: Mac with Photos, or Windows PC with iCloud for Windows | versions (record) | bridge | |
| ExifTool | 12.x or later | `bridge_check.py` | |
| Python 3.9+ | | `bridge_check.py` | |

**Software and files in this folder:**
- `bridge_check.py`: prints aggregates only. It counts full-resolution vs reduced photos, EXIF dates, file dates that are just the download time, and byte-identical reference shots. It computes hashes locally and never prints them (H3 rule R4). Small counts print as "<5".
- `selftest_fixtures.py`: SYN self-test. It was run on 2026-09-29 (ExifTool 12.76, Python 3.11) and all expected counts came out exactly (12/6 resolution split, 6 download-time dates, 5/3/2 reference split).

## Before you start

- [ ] Consent recorded with H3's consent script (`docs/research/h3-research-data-governance.md` §9). Explain that 500 of their photos will be copied to the owner's homelab or computer for the test and deleted afterwards (or kept as a backup, if they choose that separately), and that only counts are written down.
- [ ] Record, without changing them: iPhone Settings › [name] › iCloud › Photos: **Optimize iPhone Storage** or **Download and Keep Originals**; whether Advanced Data Protection is on; whether "Access iCloud Data on the Web" is on.
- [ ] Record Settings › Photos › "Transfer to Mac or PC" (Automatic / Keep Originals; the wording may differ by iOS version). You will set it to **Keep Originals** for step 3 and restore it afterwards.
- [ ] Look up the iPhone model's main-camera output resolutions in megapixels (for example 12, 24 or 48) for `--expect-mp`.

## Procedure

1. **LAB reference shots.** With the relative's permission, take 20 photos, 1 Live Photo and 1 short video of a neutral object (houseplant, no people, not the home) on their iPhone. Write down the time you took them. **You should see:** the items at the top of the library.
2. Wait until Photos shows they have uploaded to iCloud (Photos › Library, bottom status). Record the time.
3. Set "Transfer to Mac or PC" to Keep Originals. Connect the iPhone by cable to the owner's laptop and import **only those 22 items** (Image Capture on a Mac, or Windows Photos import) into an empty `ref/` folder. Restore the setting. **You should see:** HEIC/JPEG and MOV files in `ref/`.
4. **Variant H (icloudpd at the homelab).** In a throwaway container or VM:
   1. `icloudpd --username <relative's Apple Account> --auth-only --cookie-directory /secure/b4s3-cookies`. The relative enters the password and the 2FA code themselves. Record the date (for the 60-day follow-up).
   2. Dry run: `icloudpd --directory /private/b4s3 --username <…> --cookie-directory /secure/b4s3-cookies --recent 500 --size original --live-photo-size original --dry-run`. Record the start time.
   3. Real run: the same command without `--dry-run`. Record the start time (ISO 8601 with offset) for `--download-started`, and the end time.
   - **Never pass** `--auto-delete`, `--delete-after-download` or `--keep-icloud-recent-days` (they delete local files or **delete photos in iCloud**), or `--set-exif-datetime` (it **writes into the files**, so they are no longer the original bytes). Flags were checked against `icloudpd --help` for 1.32.3 on 2026-09-29.
   - If Apple returns ACCESS_DENIED: web access is off or ADP is on. Stop and record "No result" for variant H.
5. **Variant M (Mac/PC).** On a Mac signed in to the relative's account: Photos › Settings › iCloud › choose **Download Originals to this Mac**, wait until the library shows it is up to date, then File › Export › **Export Unmodified Original** for the 500 most recent items into `/private/b4s3-m`. On Windows: record exactly which iCloud for Windows Photos options exist and where the files land, then copy the 500 most recent items. Record the times as in step 4.
6. Run the check where the files are (never in an agent session):
   `python3 bridge_check.py --bridge /private/b4s3 --reference ref --download-started <ISO time from step 4 or 5> --expect-mp <classes> > results-aggregate.json`
   **You should see:** JSON with counts only. Read it before copying: no names, no hashes.
7. **Date spot check (manual).** For 10 random photos in the bridge folder, compare the date in the iPhone Photos app (swipe up for Info) with the file's EXIF date (`exiftool -DateTimeOriginal <file>`). Write down only the number that match.
8. **Lag (BUD-TTS proxy).** Minutes from taking the reference shots (step 1) to their arrival in the bridge folder, where the bridge was running then (variant H in watch mode, `--watch-with-interval 3600`, if you choose to test it).
9. **Re-authentication (EXT, 60 days).** Leave variant H's session in place only if the owner and relative agree. Set a reminder for day 60 and record whether `icloudpd --auth-only` needs a new 2FA code, and the owner minutes spent (BUD-SUPPORT). icloudpd's docs say Apple's interval is "currently two months".

**Stop and record "No result" if:** the relative declines, ADP is on (variant H), the relative does not want to share the account with a Mac/PC (variant M), or the phone's storage setting would have to be changed to run the test.

## Cleaning up

1. Restore "Transfer to Mac or PC". Delete the LAB reference shots from the iPhone if the relative wants.
2. Delete `/private/b4s3*` and `ref/` from the homelab or computer after the aggregate is accepted, unless the relative separately asks to keep them as a backup.
3. Delete the icloudpd cookie directory (SEC). Ask the relative to review signed-in sessions on their Apple Account. On the Mac/PC, sign the relative's account out if it was only added for the test.

## Data handling

- The 500 photos are FAM. They stay on the relative's phone, the homelab private research store (owner only, time-limited) or the owner's machine. Never in the repo, CI, logs or an agent session.
- `bridge_check.py` output is AGG: counts only, with cells under 5 suppressed. Run H3 §4's output check before pasting it into `results.md`.
- LAB reference shots: exact counts may be reported. They must not show people or the home (R8).
- The Apple Account password, 2FA codes and icloudpd cookies are SEC: never written down or pasted.

## Sources used to write this kit (retrieved 2026-09-29)

- icloudpd README (prerequisites: web access on, ADP off; the three modes, including Move, which deletes in iCloud): https://raw.githubusercontent.com/icloud-photos-downloader/icloud_photos_downloader/master/README.md
- icloudpd docs: authentication (2FA expiry "currently two months", ADP unsupported, FIDO unsupported), size (default original; adjusted for edits), mode: https://raw.githubusercontent.com/icloud-photos-downloader/icloud_photos_downloader/master/docs/
- `icloudpd --help` output, version 1.32.3 from PyPI, run in the research container on 2026-09-29
- osxphotos README (Optimize Mac Storage leaves originals missing; download-missing caveats): https://raw.githubusercontent.com/RhetTbull/osxphotos/main/README.md
- Blocked: Apple Support article 108782 (Optimize iPhone Storage wording) could not be fetched from the container. The storage-setting names above come from the owner's device, not from Apple docs.

## Results

Copy this section into `docs/research/kits/B4-S3/results.md` and fill it in. Do not edit numbers afterwards; add a note instead.

- **Run by / date / place:**
- **Hardware and OS actually used:** iPhone model, iOS version; bridge host and versions (icloudpd, macOS/Photos, iCloud for Windows)
- **iCloud settings found (not changed):** Optimize / Download originals; ADP on/off; web access on/off
- **Emulator or VM used instead of real hardware?** No | Yes: <what, and why>

| Step | Expected | What happened | Measurement (with unit) | Screenshot or log |
|---|---|---|---|---|
| 3 reference import | 22 files | | count | |
| 4/5 bridge download | 500 items | | count; minutes | |
| 6 photos at full resolution | all | | photo_full_res / files_photo | aggregate JSON |
| 6 reference byte-identical | 22 / 22 | | byte_identical / present_but_bytes_differ / not_found | aggregate JSON |
| 6 file date = download time | 0 (or explained) | | mtime_is_download_time_* | aggregate JSON |
| 6 EXIF date present | nearly all photos | | photo_has_exif_date / files_photo | aggregate JSON |
| 7 manual date check | 10 / 10 | | matches | |
| 8 lag, reference shots | | | minutes | |
| 9 re-auth at day 60 | needed? | | yes / no; owner minutes | |

| Pass criterion | Budget ID | Measured value | Pass / Fail / No result |
|---|---|---|---|
| 500-photo sample arrives as originals (not optimised) | — | | |
| Correct dates | — | | |
| Owner time for re-auth and babysitting | BUD-SUPPORT | | |
| Photo-to-home lag | BUD-TTS | | |

- **Overall:** Pass | Fail | No result (per variant)
- **Surprises and points of confusion:**
- **Follow-ups for the workstream:**
