# Interim protection: owner checklist (E2-S3)

For the months before Reliquary exists. One stopgap per device type that the owner can apply **this
month**, with the relative, on the relative's own device. Nothing here is built by the project apart
from `stopgap_copy.py`. Nothing here replaces the settled design. It keeps originals from being lost
or degraded until Reliquary can take them in (A9 import).

**Read first.**
- **Settings wording is unverified.** Google and Apple help pages were blocked in this research run. Setting names below come from search snippets and third-party docs (confidence in each row). Check the wording on the owner's own phone first (the E1-S2 kit does the same, "Part 0"), and fix this sheet before visiting.
- **Change nothing that deletes.** Never use "Free up space", "Move", "Sync with delete" or anything that removes the original from where it is now.
- **Priority order:** (1) things that exist in only one place (old laptops, SD cards, dead phones); (2) phones whose cloud backup is off or set to reduced quality; (3) everything else.
- **Log the time spent** in the owner support log (metric M4, BUD-SUPPORT), so the pilot starts with a baseline.
- **Record per device, on paper, with no names:** device type, which stopgap, date, "done / not possible (why)". Keep the sheet in the private store (H3).

## 1. Android phone

| Step | What to do | Confidence |
|---|---|---|
| 1 | Open Google Photos → the profile picture → Photos settings → Backup. Check backup is **on**. | Medium (snippet; wording to check) |
| 2 | Check **backup quality is "Original quality"**, not "Storage saver". Storage saver compresses photos, resizes photos above 16 MP to 16 MP and videos above 1080p to 1080p, and may convert formats. A later import then has no original, and whole-file dedup will not match the phone's copy. | Medium (Google Photos Help 6220791, snippet only) |
| 3 | Check the Google account has room. Original quality counts against Google account storage. If it is full, backup stops. | Medium (same source) |
| 4 | Ask whether **"Free up space"** has ever been used. If so, originals exist only in Google Photos; add a Takeout (§5). Agree with the relative not to use it from now on. | Medium (Google Photos Help 6128843, snippet only) |
| 5 | If there is an SD card with photos, treat it as §6 (only copy) unless the phone backs it up. | Inference |

**Avoid:** Storage saver; Free up space; third-party tools that sync through the Google Photos API. They get transcoded video, converted originals and no GPS (gphotos-sync README; that project was archived on 2024-10-04).

## 2. iPhone or iPad, with a family Mac or Windows PC in the house

| Step | What to do | Confidence |
|---|---|---|
| 1 | Settings → [name] → iCloud → Photos: check **iCloud Photos is on** and iCloud storage has room. | Medium (Apple Support 108782, snippet only) |
| 2 | "Optimize iPhone Storage" (the default) keeps full originals in iCloud only, and previews on the phone. That is acceptable for the stopgap as long as iCloud Photos stays on and has room. | Medium (same) |
| 3 | On the family computer, turn on the option that downloads **originals** from iCloud Photos: on a Mac, Photos → Settings → iCloud → "Download Originals to this Mac"; on Windows, iCloud for Windows → Photos, with full-quality downloads. **Exact wording not verified.** Check there is disk space for the whole library. | Low-medium (wording unverified; Apple pages blocked) |
| 4 | The computer now holds a local copy of the originals. Include that folder or library in the computer's copy (§4). | Inference |

**Avoid:** relying on iCloud **Shared Albums** as a backup; they hold compressed copies, not originals (Ente docs, secondary).

## 3. iPhone or iPad with no family computer

| Step | What to do | Confidence |
|---|---|---|
| 1 | As §2 steps 1–2: iCloud Photos on, with room. | Medium |
| 2 | At the next visit, **with the relative's consent**, the owner makes a one-off copy of their iCloud Photos on the owner's own machine, for example with icloudpd in its default **Copy** mode. icloudpd needs "Access iCloud Data on the Web" on and **Advanced Data Protection off**. If ADP is on, **do not ask the relative to turn it off** just for a stopgap; use step 3. | High for the tool's prerequisites and modes (icloudpd README); the decision is a proposal |
| 3 | Alternative: Apple's "transfer a copy of your iCloud Photos" to another service. It takes 3–7 days, leaves the iCloud copy unchanged, and some items (Smart Albums, Live Photos, some RAW files) may not transfer. | Medium (Apple Support 118257, snippet only) |

**Avoid:** icloudpd **Sync** (`--auto-delete`, removes local files deleted in iCloud) and **Move** (`--keep-icloud-recent-days`, deletes photos from iCloud). Also note that icloudpd's README says the project is looking for a maintainer, so do not plan on it for months. For edits, portraits and RAW, icloudpd needs extra `--size` options (adjusted, alternative); the default downloads only the original. Live Photos arrive as separate image and video files.

## 4. Windows, macOS or Linux computer

| Step | What to do | Confidence |
|---|---|---|
| 1 | At a visit, with the relative, find the keepsake folders: Pictures, Documents, Desktop, any "old camera" or phone-dump folders, the Apple Photos library, and the iCloud originals folder from §2. The E1-S1 census (kit `E1-S1`) can list where things are without copying anything. | Method |
| 2 | Copy them with `stopgap_copy.py` from the owner's laptop to an external disk or the homelab: `python3 stopgap_copy.py copy <folder> [<folder>...] --to <disk> --label <yyyy-mm>-<device>`. The tool keeps mtimes and writes a SHA-256 manifest and a provenance record. It never deletes, never overwrites a different file (it keeps both), and flags files that changed during the copy. | Tested on synthetic data in CT (see README). Windows/macOS placeholder detection **untested** |
| 3 | Run `python3 stopgap_copy.py verify <disk>/<label>` straight away, and again once the copy is on the homelab. | Tested in CT |
| 4 | **Do not download cloud placeholders** (OneDrive or iCloud Drive files not on the disk). The tool skips and lists them. Those files are in the cloud service; note them for later. | Tested on Linux only (no placeholders there) |
| 5 | Photos library on a Mac: copy the whole `.photoslibrary` package while Photos is closed. Reliquary's own handling of it is B5's decision; this is only a stopgap copy. | Inference |

**Avoid:** treating a sync folder (OneDrive, Dropbox, iCloud Drive) as the backup, since deletions propagate. Also avoid "tidying" files before copying: copy what is there.

## 5. Photos that now live only in Google Photos (lost phones, "Free up space" used)

| Step | What to do | Confidence |
|---|---|---|
| 1 | Request a Google Takeout of Google Photos only: ZIP, 50 GB parts, all photos, videos and metadata. Download **every** `takeout-NNN.zip`, and request it again if any part is missing. Do not mix ZIP and TGZ. | High (immich-go best-practices doc) |
| 2 | Keep the JSON sidecars next to the media, as exported. Dates, GPS, people and albums live there. | High (immich-go technical doc) |
| 3 | Optional: scheduled exports (every 2 months for a year) are reported, and a 2026 report says Google Photos exports became incremental. **Unverified**: the Google page was blocked and the report is secondary. They are reportedly unavailable with Advanced Protection. | Low |

**Avoid:** tools that write the Takeout JSON values back into the image EXIF. This spike measured that doing so changes the file's SHA-256 while the image data stays the same (README). A later whole-file dedup then no longer matches the phone's copy.

## 6. Only-copy items (old laptops, SD cards, external disks, dead phones)

Copy these to the homelab **first**, with `stopgap_copy.py` (§4 steps 2–3). Label each with where it came from. This is the only stopgap that prevents a loss that is already one failure away.

## How this data enters Reliquary later (to A9)

- The copies are already at the homelab or with the owner. They are imported **by the admin at the homelab**, never through devices or R2.
- Keep the bytes exactly as received, with the manifest and provenance, so the import can record "stopgap: <route>, <date>".
- Whether a Takeout or icloudpd "original" is byte-identical to the file on the phone is **unknown**. A9-S1 should measure it. If it is not, the later device upload is stored twice (a storage cost, not a loss).
