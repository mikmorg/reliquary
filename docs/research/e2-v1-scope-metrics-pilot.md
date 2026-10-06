# E2. v1 scope, success metrics, test plan, pilot and interim protection

- **Workstream:** E2 (see `docs/research/PLAN.md`, section "E2.")
- **Status:** Draft (analyst deep read, Wave 1). Not yet through skeptic review. **Provisional: the owner intake (H2) is unanswered.** Everything below uses the intake's proposed defaults (`owner-intake.md` §K and Part 2). The final scope follows the census in Wave 2.
- **Date:** 2026-09-29 (last updated 2026-09-29)
- **Feeds:** ADR-0004 (reserved in `docs/adr/README.md`; the draft text is in Appendix A of this note, so the synthesis stage can lift it into `docs/adr/0004-*.md`), OD-19 (decision request ready), OD-01 (E2 agrees with B4's recommendation), OD-13 (the answer to "browse and share"), OD-18 (interim-protection interaction), candidate budget IDs for H1 (§4.4). No one-way door.
- **Depends on:** H2 (intake, not answered), T1 (`client-stack.md`, option C), T2 (`fact-check-adr-0001-0002.md`), B4 (`b4-ios-decision.md`), F1 (`f1-build-adopt-fork-compose.md`), E1 (`e1-family-research-census.md`), A3 (`a3-ingest-protocol.md`, the state names used for the metrics).
- **Traceability rows advanced:** R-03 (iOS; E2 agrees with B4), R-06 (non-technical users: metrics and test plan), R-33 (v1 sources: Android documents, OD-19), R-36 (v1 focus is getting data in: the scope slice). None is closed. They close when the owner accepts ADR-0004.

## Summary

**Scope.** The thinnest v1 that delivers "your keepsakes are safe at home, and you can tell" is the settled v1 with nothing added. It covers:
- Desktop (Windows, macOS, Linux) and Android, with **media only on Android**.
- R2 staging and USB transport.
- Admin-only restore.
- Discovery of photos, videos and documents on desktops, plus camera rolls on phones.
- A plain-language health view, and nudges in the app and by email.
- iPhones covered through a family computer (B4 option B) until iOS ships.

The scope is delivered in three milestones:
1. A **concierge milestone**: the owner seeds by USB with the admin CLI, imports stopgap copies at the homelab, and sends each person a plain-language status report.
2. The desktop app.
3. The Android app.

Pruned from v1: LAN direct, Android documents (OD-19), import from cloud services and messaging exports (already roadmap), browse and share (answered as "not in v1"), widgets and other extra nudge channels. None of this changes settled text, except where §9 flags it.

**"Safe" and restore drills.** For a single item, "safe" means a homelab-signed receipt (A3). The word "Protected" for a person or device is also gated at system level: nobody sees it until the restore leg of the walking skeleton has passed, and a sampled restore drill has passed for that platform in the pilot. Receipts show a file arrived. A restore drill shows it can come back (restic precedent: a structure check does not prove the data is readable, C13).

**Metrics.** Every metric has a data source that fits the trust model, and none uses third-party analytics. Sources:
- the homelab catalog and receipts;
- the cloud's plaintext per-device activity timestamps, which ADR-0002 already accepts;
- device counters sent **encrypted to the homelab** through B8's relay;
- the owner's own log and the usability sessions.

The field-level consent versioning Syncthing uses for its usage reports is the pattern to borrow (C12).

**Interim protection now.**
- Phones: keep each phone's own cloud photo backup on at **original quality**. Do not use "Storage saver" or "Free up space" (C4, C5).
- iPhones: where a family computer exists, sync iCloud originals to it.
- Computers: the owner copies keepsake folders to the homelab at visits.

The copies enter Reliquary later through A9's admin-side import, which keeps their provenance.

**Confidence.** Medium on scope and metrics. Low on timing: F1's effort model says desktop plus Android lands in about 24 months at the provisional 8 h/week (C14, an estimate). The intake answers most likely to change this note are Q-B9 (hours), Q-F3 (iPhone share), Q-H2 (Android documents) and Q-H4 (concierge start). The full list is in §8.

## Questions

| # | Question (PLAN E2 key questions, plus new ones) | Short answer | Confidence |
|---|---|---|---|
| 1 | The thinnest slice that delivers "your keepsakes are safe at home and you can tell" | The settled v1 with the pruning in §2, delivered in three milestones: concierge, then desktop, then Android. The concierge milestone gives the "you can tell" part early, as an owner-sent report (§1). | Medium |
| 2 | Must a verified restore drill come before anything is called "safe"? | **Per item: no.** A verified homelab receipt is the bar (A3). **Per person or device, for the word "Protected": yes, at system level.** The pipeline must have passed a restore drill (Gate B restore leg, plus a sampled drill per platform during the pilot) before any relative sees "Protected". | Medium-high (C8, C13; A3) |
| 3 | What to prune | Android documents: prune in v1 (OD-19, media only). macOS Apple Photos library: **keep**, because it is the iPhone bridge. LAN direct: prune (ADR-0037, P2). USB return trip: keep (settled), but the owner seeds first and relatives write sticks later. iOS: after the pilot, with a bridge (B4). Discovery categories: photos, videos and documents only. Nudge channels: in the app, OS notification and email only. Wizard: keep, minimal. | Medium (§2) |
| 4 | Metrics, each with a data source that fits the trust model; no third-party analytics | Ten metrics, M1–M10, in §3. Each has a named source: the homelab catalog, plaintext Worker data already accepted by ADR-0002, encrypted device counters, the owner's log, or observed sessions. Two new "must be zero" counters come from A3: **false-safe** and **gone-before-safe**. | Medium (C8, C12; E2-S2 pending) |
| 5 | Pilot order, stop and rollback conditions, kill or pivot criteria | Owner → tech-comfortable relative → extreme user → everyone, desktop first. Each stage has entry and exit gates stated as budget IDs. There are immediate stop conditions, and a rollback that keeps the stopgaps on throughout. Kill or pivot to "concierge only" or "compose stopgaps" at named checkpoints (§4). | Medium (method); thresholds proposed only |
| 6 | Interim protection: the lowest-effort stopgap per device type | One stopgap per device type in §5.1. The owner can apply each one this month. | Medium (Google and Apple help pages were snippet-only) |
| 7 | Which stopgaps would damage a later import? | Google Photos Storage saver (resizes and re-encodes); tools built on the Google Photos API (transcoded video, GPS removed); iCloud Shared Albums (compressed copies); "Free up space" and "Optimize Storage" (originals leave the device); icloudpd Sync and Move modes (they delete); messaging-app copies. §5.2. | High for gphotos-sync and icloudpd (C6, C7); Medium for the Google and Apple settings (C4, C5) |
| 8 | How does stopgap data enter Reliquary later (A9)? | Through admin-side import at the homelab, with provenance "stopgap: <route>". Bytes are kept exactly as received. Takeout JSON sidecars are kept as metadata and not written back into EXIF. Whole-file dedup merges only byte-identical copies. Whether Takeout originals are byte-identical to device originals is **unknown**; A9-S1 must measure it. §5.3. | Medium (C16); byte identity unknown |
| 9 | Answer to relatives who want to browse and share | Not in v1. "Reliquary is the family's safe-deposit box, not its photo album. Keep sharing the way you do now." Later, perhaps an owner-run, LAN-only Immich over a **read-only** export. This depends on A6's store layout and on OD-13. §6. | High that it is a non-goal; Medium on the later route (C15) |
| 10 | Alternatives: desktop first vs Android first; owner-only dogfooding; concierge MVP | Desktop first (supported by C9 and T1). Owner-only dogfooding as stage 0 of the pilot, not as the whole plan. The concierge MVP as the first milestone and the named fallback. §7. | Medium |
| 11 | *(new)* Documents on Android (OD-19): media only, chosen folders (SAF) or all-files access? | **Media only in v1.** SAF tree grants **cannot cover the Download folder or the storage root** on Android 11+ (C1), and other apps' downloads need SAF (C3). "Chosen folders" therefore misses the most common place documents land. All-files access is a settings-page toggle, not a dialog, and Google Play reviews it (C2), although backup apps are a listed use. Revisit after B3's policy dossier and E1's census of what documents phones actually hold. | Medium-high on platform facts; Medium on the recommendation |
| 12 | *(new)* Which intake answers could change ADR-0004? | Q-B9, Q-F2, Q-F3, Q-F4, Q-F6, Q-G2, Q-G4, Q-H1–H6, Q-D1/D2/D5, Q-B1/B2/B8, Q-A3, Q-A4, Q-F7. What each would change is in §8. | High (list); effects Medium |

## Method

- **Sweep:** two scouts ran: docs (developer.android.com, developer.apple.com, Google and Apple help as search snippets, Immich and Ente docs via raw GitHub, method references) and source (Immich and Ente mobile code, Syncthing usage reporting, Home Assistant analytics, gphotos-sync, icloudpd, immich-go, restic docs). No issues/forums scout and no standards/papers scout ran for E2 in this wave.
- **Analyst re-reads (2026-09-29).** These were fetched and read in full or at the cited passages:
  - developer.android.com "Manage all files", "Access documents and other files from shared storage" and "Access media files from shared storage" (all "Last updated 2026-09-16 UTC");
  - Immich `backup.repository.dart` @ 9b57f13a, `mobile-backup.md`, `libraries.md`, `README.md` and `backup-and-restore.md`;
  - Ente `backup-and-sync.md`;
  - Syncthing `contract.go`, `security.rst` and `db-completion-get.rst`;
  - gphotos-sync `README.rst`; icloudpd `README.md`; immich-go `readme.md` and `best-practices.md`; restic `045_working_with_repos.rst`.
  - Apple facts are taken from B4's analyst re-reads (B4 sources S6, S17, S19), not fetched again.
- **Local notes used as inputs:** CLAUDE.md, ADR-0001, ADR-0002, `client-stack.md` (T1), `fact-check-adr-0001-0002.md` (T2), B4, F1, E1, A3, H3, `budgets.md`, `owner-intake.md`, `decision-queue.md`, H5 (L26), PLAN §3 and §4.
- **Scout conflicts resolved:**
  1. The docs scout said SAF cannot grant "the root" or Download. The analyst re-read confirms it, and adds from the MediaStore page that other apps' files in `MediaStore.Downloads` need SAF, and that non-media files such as PDFs are pointed to `ACTION_OPEN_DOCUMENT` (C3). This strengthens the OD-19 finding.
  2. The source scout said Immich's "backed up" count is `total - remainder` in the provider. The analyst read only the repository, whose doc comment defines `backup` as "already exist on the server for [userId]". The claim is kept at that level; the provider arithmetic was not re-read.
- **Blocked sources.** All go to H1. None was silently replaced; any claim resting on a snippet says so.
  - support.google.com (Photos 6220791 and 6128843; Accounts 3024190; Play Console 10467955): EGRESS_BLOCKED, re-tried by WebFetch on 2026-09-29.
  - support.apple.com (108782, 118257, 108306).
  - nngroup.com (re-tried, blocked).
  - research.google, static.googleusercontent.com (HEART PDF) and dl.acm.org: all re-tried by curl, CONNECT 403.
  - developers.google.com (Photos API updates): re-tried, blocked.
  - measuringu.com, jpattonassociates.com (RITE), 9to5google.com, backblaze.com, support.microsoft.com, Wikipedia.
  - The WebSearch budget for this session was exhausted (200/200) when the analyst tried to re-check the Google snippets, so the Google claims rest on the scout's snippets only.
- **Stop rule:** the analyst's re-reads added one new primary source (the MediaStore page) and no source that changed an answer. The method references (HEART, RITE, SUS, SEQ, Nielsen) are all blocked. They are used only to name methods and never as numbers.

## Sources

| # | Source | Publisher | Published or version date | Accessed | Primary? |
|---|---|---|---|---|---|
| S1 | Manage all files on a storage device — https://developer.android.com/training/data-storage/manage-all-files | Google (Android) | Last updated 2026-09-16 | 2026-09-29 | Yes |
| S2 | Access documents and other files from shared storage — https://developer.android.com/training/data-storage/shared/documents-files | Google (Android) | Last updated 2026-09-16 | 2026-09-29 | Yes |
| S3 | Access media files from shared storage — https://developer.android.com/training/data-storage/shared/media | Google (Android) | Last updated 2026-09-16 | 2026-09-29 (analyst) | Yes |
| S4 | Choose the backup quality of your photos & videos — https://support.google.com/photos/answer/6220791 | Google | Unknown | 2026-09-29 (**snippet only; blocked**) | Yes, but snippet only |
| S5 | Free up space on your device — https://support.google.com/photos/answer/6128843 | Google | Unknown | 2026-09-29 (**snippet only**) | Yes, but snippet only |
| S6 | How to download your Google data — https://support.google.com/accounts/answer/3024190 | Google | Unknown | 2026-09-29 (**snippet only**) | Yes, but snippet only |
| S7 | 9to5Google, "Google Photos now lets you schedule exports…" — https://9to5google.com/2026/06/01/google-photos-schedule-export/ | 9to5Google | 2026-06-01 (from URL) | Title and snippet only (blocked) | No |
| S8 | Set up and use iCloud Photos — https://support.apple.com/en-us/108782 | Apple | Unknown | Snippet only (blocked) | Yes, but snippet only |
| S9 | Transfer a copy of your iCloud Photos to another service — https://support.apple.com/en-us/118257 | Apple | Unknown | Snippet only (blocked) | Yes, but snippet only |
| S10 | `URLSessionConfiguration.background(withIdentifier:)`; TestFlight overview; Apple Developer Program "What's included" (B4 S6, S19, S17) | Apple | Current pages | 2026-09-29 (B4 analyst re-read) | Yes |
| S11 | immich-app/immich @ 9b57f13a : `mobile/lib/infrastructure/repositories/backup.repository.dart` | Immich | Commit 9b57f13a | 2026-09-29 (analyst) | Yes (code) |
| S12 | immich-app/immich @ main : `docs/docs/features/mobile-backup.md` | Immich | main | 2026-09-29 (analyst) | Yes |
| S13 | immich-app/immich @ main : `docs/docs/features/libraries.md` | Immich | main | 2026-09-29 (analyst) | Yes |
| S14 | immich-app/immich @ main : `README.md`; `docs/docs/administration/backup-and-restore.md` | Immich | main | 2026-09-29 (analyst) | Yes |
| S15 | Immich issues #21921 ("Android: background sync works 0% of the time", opened 2025-09-13), #22248 ("Hashes lost, stuck at 17k assets to reupload", opened 2025-09-20), #968 (negative remainder counter, opened 2022-11-14) | Immich community | See titles | 2026-09-29 (scout; **titles and metadata only**) | Yes, but bodies unread |
| S16 | ente-io/ente @ main : `docs/docs/photos/faq/backup-and-sync.md` | Ente | main | 2026-09-29 (analyst) | Yes |
| S17 | ente-io/ente @ main : `mobile/apps/photos/lib/db/files_db.dart` | Ente | main | 2026-09-29 (scout) | Yes (code) |
| S18 | syncthing/syncthing @ main : `lib/ur/contract/contract.go`, `lib/ur/usage_report.go` | Syncthing | main | 2026-09-29 (analyst: contract.go) | Yes (code) |
| S19 | syncthing/docs @ main : `users/security.rst`, `rest/db-completion-get.rst` | Syncthing | main (completion API versionadded 1.8.0 and 1.20.0) | 2026-09-29 (analyst) | Yes |
| S20 | home-assistant/core @ dev : `homeassistant/components/analytics/const.py` | Home Assistant | dev | 2026-09-29 (scout) | Yes (code) |
| S21 | gilesknap/gphotos-sync @ main : `README.rst` | G. Knap | Archived 2024-10-04 | 2026-09-29 (analyst) | Yes |
| S22 | icloud-photos-downloader/icloud_photos_downloader @ master : `README.md`, `docs/size.md` | icloudpd | master (links release v1.32.3) | 2026-09-29 (analyst: README) | Yes |
| S23 | simulot/immich-go @ main : `readme.md`, `docs/best-practices.md`, `docs/technical.md`; @ f7d19fce : `adapters/googlePhotos/googlephotos.go`, `matchers.go` | immich-go | main; commit f7d19fce | 2026-09-29 (analyst: readme and best-practices; scout: the rest) | Yes (code and docs); licence not checked |
| S24 | restic/restic @ master : `doc/045_working_with_repos.rst` | restic | master | 2026-09-29 (analyst) | Yes |
| S25 | Rodden, Hutchinson, Fu, "Measuring the User Experience on a Large Scale" (CHI 2010) — https://dl.acm.org/doi/10.1145/1753326.1753687 | ACM | 2010 | Blocked; search listing only | Primary, but not read |
| S26 | Brooke, "SUS: a quick and dirty usability scale" (1996); Medlock et al., RITE (2002/2005); Nielsen, "Why you only need to test with 5 users" | various | 1996–2005 | Blocked or not fetched | Not read |
| S27 | Local: CLAUDE.md; ADR-0001; ADR-0002; `client-stack.md`; `fact-check-adr-0001-0002.md`; `b4-ios-decision.md`; `f1-build-adopt-fork-compose.md`; `e1-family-research-census.md`; `a3-ingest-protocol.md`; `budgets.md`; `owner-intake.md`; PLAN §3–§5 | Reliquary | 2026-09-29 | 2026-09-29 | Project text (settled or draft) |

## Claims

Skeptic columns are empty: this draft has not had skeptic review yet (PLAN §5.1, stage 4).

| # | Claim | Sources | Key? | Skeptic 1 | Skeptic 2 | Skeptic 3 | Verdict |
|---|---|---|---|---|---|---|---|
| C1 | On Android 11 (API 30) and higher, `ACTION_OPEN_DOCUMENT_TREE` cannot request access to the root of internal storage, the root of reliable SD-card volumes, or the **Download** directory. It also cannot be used to select files in `Android/data/` or `Android/obb/`. A persisted grant (`takePersistableUriPermission`) survives restarts, but it is lost if the document is moved or deleted. | S2 | Yes | | | | Pending |
| C2 | All-files access (`MANAGE_EXTERNAL_STORAGE`): the app declares it in the manifest and sends the user through `ACTION_MANAGE_ALL_FILES_ACCESS_PERMISSION` to a **system settings page** to turn on "Allow access to manage all files". It is not a runtime dialog. It grants read and write access to all of shared storage, the `MediaStore.Files` table, and the USB OTG and SD roots, but not other apps' `Android/data`. Since May 2021, Google Play evaluates apps that target API 30+ and declare it. They must use it only when SAF or MediaStore cannot effectively be used, and the use must be tied to core functionality. "Backup and restore apps" is listed as a likely permitted use. | S1 | Yes | | | | Pending (Play policy page itself blocked: B3) |
| C3 | To open a file in `MediaStore.Downloads` that the app did not create, the app must use SAF. With scoped storage, other apps' files are visible through MediaStore only in the Images, Video and Audio collections. For non-media files such as PDF or EPUB, the docs point to `ACTION_OPEN_DOCUMENT`. | S3 | Yes | | | | Pending |
| C4 | Google Photos "Storage saver" compresses photos, resizes photos above 16 MP to 16 MP and videos above 1080p to 1080p, and may convert photos to another format. | S4 (snippet) | Yes | | | | **Secondary only** until S4 is read |
| C5 | Google Photos "Free up space" deletes the device copies of items already backed up; the items stay visible from the cloud copy. iCloud Photos "Optimize iPhone Storage" (the default) keeps full-resolution originals in iCloud and smaller versions on the device. | S5, S8 (snippets) | Yes | | | | **Secondary only** |
| C6 | gphotos-sync was archived on 2024-10-04. Its README says the Google Photos API cannot make a true backup: "Videos are transcoded to lower quality", "Raw or Original photos are converted to 'High Quality'", "GPS info is removed from photos metadata". | S21 | Yes | | | | Pending |
| C7 | icloudpd requires "Access iCloud Data on the Web" **on** and Advanced Data Protection **off**. Its modes are Copy (the default), Sync (`--auto-delete` deletes local files removed in iCloud) and Move (`--keep-icloud-recent-days` deletes photos from iCloud). Live Photos are saved as separate image and video files. The README's first line is "Looking for MAINTAINER for this project". | S22 | Yes | | | | Pending |
| C8 | Immich mobile (commit 9b57f13a) counts backup status over assets in albums marked "selected" and not in an "excluded" album. An asset counts as backed up when a server asset with the same checksum exists for that user. `processing` counts assets with no checksum yet. There is no condition on server-side verification or restorability. | S11 | Yes | | | | Pending |
| C9 | Immich's docs say iOS needs Background App Refresh and that the OS decides when background uploads run, and that battery optimisation on some Android models breaks the background worker. Ente's FAQ says: "Background sync isn't currently consistent on iOS and on certain Android devices." It recommends the desktop app for large initial uploads, and its iOS "Backup mode" requires the app to stay open on screen, on power and on Wi-Fi. | S12, S16 | Yes | | | | Pending |
| C10 | A background `URLSession` continues transfers while the iOS app is suspended or terminated by the system. If the user force-quits the app, the system cancels the session's background transfers and does not relaunch the app. | S10 (B4 C5, C6) | Yes | | | | Pending (B4) |
| C11 | The Apple Developer Program costs 99 USD per membership year. TestFlight builds are available for up to 90 days. The first build sent to external testers goes to App Review. | S10 (B4 C13, C15) | Yes | | | | Pending (B4) |
| C12 | Syncthing usage reporting is off by default and asked about once. The report is previewable, and is sent at startup and then every 24 h. Consent is versioned: `Report.ClearForVersion` zeroes every field whose `since` tag is newer than the accepted version, or that has no `since` tag. `GET /rest/db/completion` returns `completion`, `globalBytes`, `needBytes`, `globalItems` and `needItems` per device and folder, or aggregated. | S18, S19 | Yes | | | | Pending |
| C13 | restic's `check` does not by default verify that pack files are unmodified; that needs `--read-data`. `--read-data-subset` supports rotating `n/t` slices, a random percentage or a random size. Random subsets "will not guarantee to cover all available pack files". | S24 | Yes | | | | Pending |
| C14 | F1's effort model puts v1 at about 1,070–2,140 focused hours. At a provisional 8 h/week, a desktop tray app and a minimal Android app land at about 24 months, with USB/CLI concierge seeding at about 12 months. | S27 (F1 §4) | Yes | | | | **Estimate** (F1 confidence Low) |
| C15 | An Immich external library can belong to only one user. The docs show read-only (`:ro`) mounts and warn that without `:ro` "Immich will be able to delete the files". Metadata added in Immich (albums, descriptions) "will not be persisted to the external asset file". The Immich README says "Always follow 3-2-1 backup plan", and its backup docs say users must still use "an actual backup tool". | S13, S14 | Yes | | | | Pending |
| C16 | In Google Takeout exports, capture time, geodata, people, albums and status flags live in per-file JSON sidecars. immich-go documents matching quirks: names truncated at 46 UTF-16 characters, renamed duplicates, localised "edited" suffixes, and sidecars in other folders. Its best practice is ZIP with 50 GB parts, checking that every part downloaded, not mixing ZIP and TGZ, and re-requesting incomplete takeouts. | S23 | Yes | | | | Pending |
| C17 | Google Takeout scheduled exports run every 2 months for 1 year. Scheduled Google Photos exports are reportedly incremental after the first (secondary reports date this to about June 2026). | S6 (snippet), S7 (secondary) | No (not relied on for a decision) | | | | **Secondary only** |
| C18 | Immich has closed issues titled "Android: background sync works 0% of the time" (#21921) and "Hashes lost, stuck at 17k assets to reupload" (#22248). Only titles and metadata were read. | S15 | No (illustrative) | | | | Titles only |

## Findings

### 1. The v1 slice and the "safe" bar (Q1, Q2)

**What must be true for "your keepsakes are safe at home and you can tell".** Four things, all already in settled text or in A3:
1. The bytes reach the homelab and are verified there, shown by a signed receipt (A3).
2. The person can see which of their keepsakes have that receipt and which do not (CLAUDE.md: plain-language health).
3. The owner can get any of them back (CLAUDE.md: restore is first-class, admin-run in v1).
4. Nothing is shown as safe that is not safe (PLAN §3; A3 "gone-before-safe" and "already have it never means safe").

**Similar work sets the bar too low, which is the lesson.** Immich's backup screen counts an asset as backed up once the server holds the same checksum for that user (C8). Ente's client marks a file uploaded once a server file ID exists (S17). Neither says anything about the file being durable or restorable. Reliquary's settled "data integrity over everything" rules out copying that definition. Receipts (A3) raise the per-item bar to "verified and committed at home". But receipts cannot show that the **pipeline as a whole** can give data back: key custody, the catalog and restore delivery. restic makes the same distinction: a structure check is not a data check (C13).

**Recommendation (Medium-high).**
- **Per item:** "stored at home" = a verified receipt (A3 client state 7). There is no restore drill per item.
- **Per person or device, the word "Protected" (E3's vocabulary):** shown only when all of these hold:
  - (a) every accepted keepsake on that device has a receipt;
  - (b) the system-level restore gate is open: Gate B's restore leg has passed (A0-S3), and for that **platform** (Windows, macOS, Linux, Android) at least one sampled restore drill has passed during the pilot (§4);
  - (c) whatever E3 decides about pool redundancy and scrub freshness.
- Until (b) holds, the strongest wording is "stored at home", never "Protected" or "safe".
- This is a hand-off to E3 (ADR-0024). E2 only sets the gate.

**The thinnest slice.** Nothing settled can be removed without an owner decision. The slice is the settled v1 after the pruning in §2, **sequenced** so that the family gets value long before the apps exist (F1's 24-month estimate, C14):

| Milestone | What the family gets | What must exist | Settled-text fit |
|---|---|---|---|
| **M0: stopgaps (this month)** | Phones' own cloud backups kept at original quality; iCloud originals synced to a family computer where one exists; the owner copies computer keepsakes at visits | Nothing built (§5) | Fits (no Reliquary data path) |
| **M1: concierge** (the fallback in intake Q-H4, made the first milestone) | The owner seeds each computer's keepsakes by USB with the admin CLI at visits, and imports M0 copies at the homelab. Each person gets a **plain-language status report** from the owner. | A0 skeleton hardened; USB bundle writer (A4); admin CLI; A9 import; a report generator run at the homelab | Fits. It is a delivery step toward the settled v1, not a replacement. Relatives touch no configuration (CLAUDE.md). |
| **M2: desktop app** | The kit (ADR-0002): enrollment, discovery proposals, health view, nudges (in the app and by email), the "other devices" wizard, USB return trip | B1, B5, B6, B7, E3, E4, E5 | Fits ADR-0002 |
| **M3: Android app** | Camera roll protected from anywhere; media only | B2, B3 | Fits ADR-0002 §4 |
| **After the pilot** | iOS (per OD-01); Android documents (per OD-19 revisit) | B4 | Per OD-01 and OD-19 |

The report in M1 needs a delivery route. Email lives in the cloud per ADR-0002 §2, and OD-03 is open. In M1 the owner can simply hand over or send the report himself, so no new channel is needed. (Inference; C8 and A3 support the "receipts, not presence" definition the report would use.)

### 2. What to prune (Q3, Q11)

| Candidate | Recommendation | Why | Touches settled text? | Evidence |
|---|---|---|---|---|
| **Documents on Android (OD-19)** | **Prune from v1: media only.** Revisit after B3's policy dossier and E1's census of what documents phones hold. | SAF tree grants cannot include **Download** or the storage root on Android 11+ (C1). Other apps' downloads need SAF (C3). "Chosen folders" therefore misses the most common place documents land and needs the user to operate the system picker, against "users never touch configuration". All-files access covers everything, but it is a settings-page toggle (C2), which is a support step for non-technical relatives. It also adds a Play policy review on top of the photo/video declarations B3 already faces (PLAN §3). Desktop covers documents in v1. | No (a subset of "files on the device"; decision-queue says so) | C1–C3 |
| macOS Apple Photos library | **Keep** in v1 | It is the iPhone bridge under B4 option B (iCloud originals synced to a Mac). Pruning it would leave iPhone photos unprotected until iOS ships. B5 decides between PhotoKit and reading the package. | No | B4 §6 |
| LAN direct | **Prune** (ADR-0037, P2) | ADR-0001 §5 marks it "proposed, not yet committed". USB covers seeding. | No | ADR-0001 §5 |
| USB return trip | **Keep**, but phase it: the owner seeds by USB first (M1). Relatives write sticks from the desktop app in M2. | ADR-0002 §1 and CLAUDE.md require the USB transport. Only its sequencing is a choice. | No, unless v1 ships without it (then an ADR-0002 amendment) | ADR-0002 §1 |
| iOS | **After the pilot, with a desktop bridge** (B4 option B, gated on E1-S2a) | B4's evidence: 99 USD/yr; 90-day TestFlight builds; force-quit cancels uploads (C10, C11). Mobile background sync is unreliable even in mature apps (C9). | **Yes** (OD-01, CLAUDE.md platforms vs ADR-0002 §4) | B4; C9–C11 |
| Discovery categories | v1: camera rolls on phones; photos, videos and documents in user folders on desktops. Messaging-app exports, email and cloud services are roadmap (settled). E4 sets the rules. | Keeps E4's golden set small; cloud and email are already roadmap in CLAUDE.md | No | CLAUDE.md |
| Nudge channels | v1: health view in the app, OS notifications and email. **Not** in v1: Android widget, SMS, pushes to a helper. The owner alert channel is C7's, not a nudge. | ADR-0002 §2 settles email nudges. Every extra channel is surface area to test (E3-S3). | No | ADR-0002 §2 |
| "Other devices" wizard | **Keep, minimal.** iPhone shows "not yet, covered via <computer>" or "not yet". | Settled in ADR-0002 §3 | No | ADR-0002 §3 |
| Browse and share | **Not in v1** (§6) | Non-goal; OD-13 | Possibly (OD-13) | C15 |
| End-user restore | Not in v1 (settled) | CLAUDE.md | No | — |
| Admin dashboard | Not in v1 (settled). M1's status report is a generated document, not a dashboard. | CLAUDE.md; OD-13 | Possibly, if the report grows into a web page (OD-13) | — |

### 3. Success metrics that fit the trust model (Q4)

**Rules.**
- No third-party analytics.
- No plaintext file names, paths or hashes leave a device except inside the ADR-0001 encrypted envelope.
- The cloud may use only what ADR-0002 already accepts in plaintext: name, email, per-device activity timestamps, and what it needs to send mail.
- Everything else is computed **at the homelab** from the catalog and receipts, or from device counters sent **encrypted to the homelab** through B8's relay (encrypted like any other record).
- Adding a counter later needs fresh consent under D6's family charter. Borrow Syncthing's versioned-consent rule: fields newer than the accepted version are zeroed before sending (C12).
- Metrics are for the owner. They are never shown to relatives as scores.

| ID | Metric | Definition | Data source (trust-model fit) | Where computed | Budget / target | Notes |
|---|---|---|---|---|---|---|
| M1 | Time to first protected keepsake | Enrollment (invite redemption) → first receipt verified on that device | Redemption time: Worker (plaintext; ADR-0002 accepts per-device activity timestamps). First-receipt time: the device's own log, sent encrypted. | Homelab | Related to BUD-TTS (measured on the device, per A3) | Per device and per person |
| M2 | Coverage at 7 and 30 days | (bytes with a verified receipt) ÷ (bytes of keepsakes discovered and accepted, not excluded), and the same by items | Device-local counters (only the device knows what is discovered but not sent), encrypted to the homelab. "Cloud-only" (placeholder, iCloud-optimised) is reported **as a separate bucket, never dropped from the denominator**. | Homelab | Candidate budget **BUD-COVER** (§4.4) | Denominator = discovered, not user-selected (C8 contrast). Weight by both bytes and items (Syncthing precedent, C12). |
| M3 | Surprise gaps found in an audit | Keepsake locations or sources found by the owner or relative in an audit that discovery did not propose | Visit or remote audit, recorded as counts (H3 `FAM → AGG`) | Owner | Target set by E4 (E1-S1's "one unmentioned location" criterion) | Feeds E4's rules |
| M4 | Owner support minutes | Minutes per month the owner spends on support and ops, by cause | The owner's own log (a one-line entry per incident) | Owner | **BUD-SUPPORT** (≤ 2 h/month, proposed) | F1 notes that development upkeep is a separate line (hand-off to H1) |
| M5 | Unaided enrollment | Share of kit enrollments completed without help, and the time taken | In the lab: observation (E5-S3). In the pilot: redemption → first receipt with no support entry in M4's log for that device. | Owner / homelab | **BUD-ENROLL** (≤ 20 min, proposed) | |
| M6 | Nudge action vs mute rate | Share of actionable nudges followed by the fixing state change within 3 days, and share of nudges snoozed or muted | Nudge sent: device (in the app) or Worker (email; it sends them). Fix: a state change seen at the homelab (receipts, heartbeat). Mute: device counter, encrypted. **No email click tracking** (link scanners and phishing optics, PLAN §3). | Homelab | E3-S2's rule (≥ 60 % fixed within 3 days) | Measure the fix, not the click |
| M7 | Restore-drill success and time | Share of sampled drills where every file restores byte-identical, **verified on the target device**, plus the owner's time per drill | Homelab admin tool log, plus the device's check of the restored hash | Homelab | **BUD-RESTORE** | Sample by device and platform; rotating slices beat pure random (C13) |
| M8 | SUS and SEQ | Standard questionnaires after tasks | Paper sheets in usability sessions only; **never in the app** | Owner (`FAM → AGG`) | E2-S1 pass rule | Benchmarks (the "68" SUS average, SEQ norms) are secondary only (blocked); do not set targets from them |
| M9 | False-safe count | Items or devices shown "stored at home" or "Protected" without a verified receipt, or with the restore gate closed | Device self-check against its receipt set, encrypted; E3-S4 on the harness | Homelab | **Must be 0** (candidate BUD-FALSESAFE) | Stop condition (§4.2) |
| M10 | Gone-before-safe count | Items that vanished from the source before commit (A3 side state) | Device, encrypted; an admin nudge per A3 | Homelab | Report every one. Any case caused by a Reliquary bug is a stop condition. | The only state that means possible loss |

**Where this overlaps other owners.** B8 owns the data dictionary: each field, whether it is plaintext or encrypted, and how long it is kept. D6 owns consent and minimisation. C7 owns alerts. E2-S2 checks that every kept metric has a source that fits. Home Assistant's tiered analytics (S20) is a useful consent pattern, but it sends to a vendor endpoint, which the "no third-party analytics" rule excludes.

### 4. Pilot plan (Q5)

#### 4.1 Stages

| Stage | Who | Entry gate | Exit gate (all must hold) | Minimum duration (proposed) |
|---|---|---|---|---|
| **P0 owner dogfood** | Owner's own devices: first SYN and LAB data, then real data after Gate A | Gate A accepted; Gate B passed (restore leg) | M9 = 0; one restore drill per platform passes (M7); BUD-TTS met; E3-S4 passes on real devices | 4 weeks (proposal) |
| **P1 helper** | One tech-comfortable relative (E1's first visit persona) | P0 exit; Gate C readiness list (PLAN §4.2) for the platforms in use; runbooks printed | M9 = 0; M2 at 30 days meets BUD-COVER; M4 within BUD-SUPPORT; the helper can explain the health view back (E3-S1 style) | 4 weeks after enrollment |
| **P2 extreme user(s)** | The least tech-comfortable relative, and the one with the largest or most iPhone-heavy library (E1 personas) | P1 exit; fixes from P1 shipped | As P1, plus M5 unaided enrollment within BUD-ENROLL, and M6 per E3-S2 | 30 days after enrollment |
| **P3 everyone** | The remaining relatives, in batches of 2–3 | P2 exit | Steady state: M4 within BUD-SUPPORT for 2 consecutive months | — |

Desktop comes first in each stage (intake Q-H3 default). Android joins from P1 once B2's soak passes. Throughout P0–P3, **each relative's stopgaps stay on** (§5). Reliquary does not replace them until the person has passed P3 exit and E3's OD-18 decision allows it.

#### 4.2 Stop conditions (halt new enrollment and uploads; tell affected relatives plainly)

1. Any M9 false-safe event.
2. Any M10 gone-before-safe event caused by a Reliquary bug.
3. Any restore drill failure (M7), or any receipt that fails verification against the pinned trust bundle.
4. A key-custody incident (D2), or suspected compromise of a device credential beyond BUD-ABUSE.
5. Cloud spend above BUD-CLOUD for the month, or any auto-suspend (C2).
6. Upload traffic on a relative's metered or capped link beyond what they agreed (D5 intake answer).

#### 4.3 Rollback

- Pause through a signed config or kill switch (B8 and D5). Devices stop uploading but keep their local state and receipts.
- Data already committed stays committed. Keep-forever retention is settled, and rollback never deletes anything.
- Stopgaps were never turned off (§4.1), so rollback leaves nobody worse off than before the pilot.
- If a format bug is found after Gate A, the fix is a new format version with migration (A2 and A3), never a silent rewrite.

#### 4.4 Kill or pivot checkpoints

| Checkpoint | Signal | Pivot |
|---|---|---|
| After M1 (concierge) | The owner cannot sustain visits and CLI seeding within BUD-SUPPORT plus the Q-B9 build hours | Stay on stopgaps plus a yearly concierge import; revisit scope |
| After P1 | M2 at 30 days far below BUD-COVER because of mobile background limits (the C9 pattern) | Android "Back up now" plus desktop-first seeding as the primary path; drop background ambitions to charge-and-Wi-Fi windows |
| After P2 | M4 > 2 × BUD-SUPPORT for 2 months, or E2-S1 or E3-S1 fails after one RITE round | Simplify the UX (health email only), or return to concierge for that persona |
| F1 checkpoint (12 months) | Build hours used > 2 × F1's estimate for the milestones shipped | ADR-0005 revisit: "compose stopgaps indefinitely" (F1 names this) |

**Candidate budget IDs for H1** (proposed values, owner to confirm; E2 does not set them):
- **BUD-COVER:** ≥ 95 % of discovered, locally available keepsake bytes have receipts 30 days after enrollment. The cloud-only bucket is reported separately.
- **BUD-FALSESAFE:** 0 false-safe events.
- **BUD-PILOT-DUR:** the minimum stage durations in §4.1.

These values are the analyst's proposals. They are not measured and have no source.

#### 4.5 Pre-mortem: "it is two years from now and Reliquary failed"

| Failure story | Evidence it is plausible | Mitigation (owner) |
|---|---|---|
| The owner ran out of hours; half-built, nobody protected | F1: 1,070–2,140 h (C14) | M0 stopgaps now; M1 concierge first (E2); scope cuts in this note |
| Phone backups "never finish" | Immich and Ente docs (C9); Immich #21921 (C18, title only) | Desktop and USB seeding; UIDT "Back up now" (B2); honest "catching up" states (E3) |
| A lost local hash cache triggers a re-upload storm or a false gap | Immich #22248 title (C18) | Durable, rebuildable cache (B6); dedup "already have it" makes re-sends cheap (A3) |
| Something said "safe" and was not | Immich counts server presence only (C8) | Receipts (A3); M9 = 0 stop rule; restore gate on "Protected" (§1) |
| iPhones held most photos and were never covered | E1-S2 pending; B4 | B4 bridge; escalation gate at ≥ 40 % |
| Relatives turned on "Free up space" or "Optimize", so originals were gone from devices | C5 (snippet) | Interim advice (§5); cloud-only bucket in M2; E3 and OD-18 |
| Play rejected the app, or policy changes stranded Android | C2; F1's Syncthing Android lesson | Media only in v1 (OD-19); B3 dossier |
| The owner burned out on support | PLAN §3 "warm expert" | M4 tracked monthly; P2 kill checkpoint |
| Keys lost and backups unreadable | PLAN §3 | D2 recovery drill before Gate A |

### 5. Interim protection (Q6, Q7, Q8)

#### 5.1 One stopgap per device type (E2-S3 candidate answer; the spike runner produces the owner checklist)

| Device type | Lowest-effort stopgap this month | Settings to check together with the relative | Avoid | Confidence |
|---|---|---|---|---|
| Android phone | Keep Google Photos backup **on**, at **Original quality** | Backup quality is not "Storage saver" (C4). "Free up space" has **not** been used and is not used from now on (C5). Check that the account has room. | Storage saver; Free up space; third-party Google Photos API sync tools (C6) | Medium (Google pages snippet-only) |
| iPhone / iPad | Keep iCloud Photos **on**. Where the relative has a Mac or Windows PC, turn on originals download there ("Download Originals" in iCloud for Windows, or "Download Originals to this Mac"; exact wording to be checked on device, since the Apple pages were blocked) | "Optimize iPhone Storage" is the default and leaves originals in iCloud only (C5). That is acceptable for the stopgap, provided the account has room. | Relying on Shared Albums (compressed copies, S16); icloudpd **Sync** or **Move** (C7) | Medium |
| iPhone with no family computer | iCloud Photos on. At the next visit, the owner makes a one-off copy (for example with icloudpd **Copy** mode on the owner's machine, only with the relative's consent and only if ADP is already off), **or** Apple's "transfer a copy" to another service (S9, snippet: takes 3–7 days; some formats may not transfer) | Do not ask a relative to turn ADP off just for a stopgap (C7) | icloudpd Sync or Move; a long-term icloudpd dependency (maintainer wanted, C7) | Low-medium |
| Windows / macOS / Linux computer | The owner copies the keepsake folders at a visit, onto the homelab (a read-only share) or an external disk, and records where it came from and when | Look for placeholders (OneDrive, iCloud Drive). Copy only local originals; do not hydrate silently. | Relying on sync folders as backup (deletes propagate) | Medium (method; OS backup pages blocked) |
| Google-Photos-only items (lost phones, "Free up space" already used) | One Google Takeout of Google Photos, then scheduled exports if available (C17, secondary) | ZIP, 50 GB parts, download every part, re-request if incomplete (C16) | Mixing ZIP and TGZ | Medium |
| Only-copy items (intake Q-G4: old laptops, SD cards) | The owner copies them to the homelab **this month**, before anything else | — | — | High that this is the top priority (PLAN §3) |

#### 5.2 Stopgaps that damage a later import

| Stopgap | Damage | Evidence |
|---|---|---|
| Google Photos Storage saver | Photos resized above 16 MP and videos above 1080p, re-encoded, possibly converted. A later import has no original, and whole-file dedup will not match the device copy. | C4 (snippet) |
| Google Photos API sync tools (gphotos-sync and similar) | Transcoded video; originals converted; GPS removed | C6 |
| iCloud Shared Albums as "the backup" | Compressed copies, not originals | S16 (Ente docs) |
| Free up space / Optimize Storage | Originals leave the device, so on-device discovery later finds nothing or only previews | C5 (snippet); PLAN §3 |
| icloudpd Sync or Move | Deletes local files or iCloud photos | C7 |
| Messaging-app forwarding as backup | Recompressed copies escape dedup | PLAN §3 (A5) |

#### 5.3 How stopgap data enters Reliquary (to A9)

- **Admin-side import at the homelab only.** Stopgap copies are already in the owner's hands, so they never go through the devices or R2.
- Provenance "stopgap: <route>, <date>" goes into the history fields (H4, Gate A). The owner can then tell a Takeout copy from a device original.
- **Keep bytes exactly as received.** Do not write Takeout JSON values back into EXIF (tools that do so change the bytes and break dedup). Store the sidecar as linked metadata (C16).
- Whole-file dedup merges a stopgap copy with the later device upload **only if the bytes are identical**. Whether a Google Takeout or icloudpd "original" is byte-identical to the file on the phone is **unknown**. A9-S1 should measure it with SHA-256 on the owner's own sample (H3 `FAM → AGG`). Either way nothing is lost; the cost is duplicate storage.
- Live Photos arrive from icloudpd as separate image and video files (C7). A5 must group them.

### 6. The answer on "browse and share" (Q9)

- **Script for relatives (draft for E6):** "Reliquary is the family's safe-deposit box, not its photo album. Keep sharing and browsing the way you do now. [Owner] can get any photo back for you."
- **Why it is a non-goal:** CLAUDE.md focuses v1 on getting data in; restore is admin-only; any gallery is OD-13.
- **Later option:** an owner-run, LAN-only Immich over a read-only view of the homelab store. Immich's own docs support treating it as a viewer, not a backup (C15). The read-only mount matters: without `:ro`, Immich can delete files. Limits: one user per external library, and albums made in Immich are not written back to the files (C15).
- **Dependency (inference):** Immich scans a directory tree of media files. If A6 picks a content-addressed or restic/Kopia-style store, a browsable view needs an export or a mounted view. That is an A6 hand-off, not a v1 task.

## Alternatives compared

| Option | Fit with settled requirements | Pros | Cons | Evidence |
|---|---|---|---|---|
| **Desktop first, then Android (recommended)** | Fits ADR-0002 (the kit is desktop-centred) | Best background story; USB kit; T1 option C desktop shell is the most mature; Ente recommends desktop for large initial uploads | Phones are the main keepsake source (CLAUDE.md), so camera rolls wait unless a bridge or stopgap covers them | C9; T1; ADR-0002 |
| Android first | Fits | Covers the main keepsake source sooner | Background limits (C9); Play compliance on the critical path (B3); Android is F1's largest effort item | C9; F1 |
| Owner-only dogfooding as the whole pilot | Fits | Cheapest, safest | Does not test non-technical users (R-06); the owner is the least representative user | PLAN E2 |
| **Concierge MVP first (recommended as M1 and as the fallback)** | Fits as a milestone, not as the end state | Protects data years earlier at 8 h/week (C14); proves ingest, USB and restore on real data | Owner visit time; relatives get a report, not an app; does not meet the v1 assistant features alone | C14; Q-H4 |
| iOS first | Conflicts with ADR-0002 §4 | Covers iPhone-heavy families | 99 USD/yr, TestFlight 90-day builds, force-quit cancels uploads (C10, C11) | B4 |
| Do nothing but stopgaps | Fails the settled goals | Zero build cost | No homelab copy, no health view | F1 |

### Similar work and lessons

| Project or paper | What they do | Borrow or avoid | Source |
|---|---|---|---|
| Immich mobile backup counts | Denominator = selected albums; "backed up" = server has the same checksum | Avoid: presence ≠ safe. Borrow: a single-query count with a separate "processing" bucket | C8 |
| Ente backup status | Shows backed-up, pending and errors; recommends desktop for big first uploads | Borrow the three-bucket status and the desktop-first seeding advice | C9, S16 |
| Syncthing usage reporting and completion API | Opt-in, previewable, versioned consent; byte- and item-weighted completion | Borrow both patterns for M2 and consent | C12 |
| restic check | Structure check vs reading the data; rotating subsets | Borrow rotating slices for M7 drills | C13 |
| gphotos-sync | Google Photos API backup; archived | Avoid as a stopgap | C6 |
| icloudpd | iCloud download in Copy, Sync or Move mode | Copy mode only, as an occasional owner-run tool; not a long-term dependency | C7 |
| immich-go | Imports Takeout and iCloud exports | Study its matchers for A9 (licence unchecked; G3) | C16 |
| HEART (CHI 2010), RITE, SUS/SEQ, Nielsen 5 users | Metric and usability methods | Use HEART's goals-signals-metrics to organise M1–M10; RITE for E2-S1's fail branch. **Primary sources blocked**: method names only, no numbers | S25, S26 |

### Tools and libraries

| Name | Purpose | Licence | Maturity | Source |
|---|---|---|---|---|
| Paper prototypes, Penpot | E2-S1 clickable prototype | MPL-2.0 (Penpot) | Not checked this wave | PLAN |
| SUS / SEQ paper sheets | Post-task questionnaires | Public-domain instruments (not verified) | — | S26 |
| icloudpd | Owner-run iCloud copy (Copy mode) | Not checked | Release v1.32.3 linked; maintainer wanted | C7 |
| immich-go | Reference for Takeout import (A9) | Not checked | Active on main | C16 |

## Consolidated family test plan (skeleton; the full plan is an E2 Wave 2 deliverable)

- **One visit per relative** (PLAN; H5 L26), in E1's running order (`kits/E1-S1/visit-plan.md`). The interview and census come first, so answers are not primed.
- **E2 and E5 block (order 7 in E1's plan), proposed order inside it:**
  1. E3-S1 comprehension of health screens, **before** the relative sees our enroll prototype. The screen order is counterbalanced across relatives.
  2. E2-S1 "enroll and tell me if your photos are safe" (prototype).
  3. E5-S1, S3 and S4 (QR, code typing, kit enrollment).
  4. D6-S3 and E7-S1 questions last.
- **Anti-pre-training:** a relative who did E3-S1 variant X is not counted for E2-S1's "tell me if safe" wording if X's wording is the prototype's own. The spike runner's kit must define the counterbalancing.
- **Visit length is unmeasured.** E1 estimates about 90 minutes before the E2/E5 block. For older relatives, split the visit over two sittings (E1's break rule). E4-S1 labelling runs remotely on AGG output where possible.
- **Longitudinal tests** (E3-S2 nudge pilot, E5-S6 posted stick) run separately. They must not overlap P1–P2 pilot participants in the same weeks (a proposal, to avoid double burden).
- **Order of visits:** helper → typical → extreme, which matches pilot order P1 → P2.

## Spikes

The spike runner is running this workstream's spikes in parallel. **Placeholder:** results and kit links are to be filled in by the spike runner and synthesis.

| Spike | Hypothesis | Pass → / fail → (decision) | Exec tag | Budget IDs | Data class | Status | Result |
|---|---|---|---|---|---|---|---|
| E2-S1 Clickable enroll + health prototype, 5 relatives | Non-technical relatives can enroll and judge "are my photos safe" unaided | Pass (≥ 4 of 5) → ADR-0004 UX scope stands; fail → RITE and retest | FM | BUD-ENROLL | `FAM → AGG` | (spike runner: kit) | — |
| E2-S2 Metric feasibility | Every kept metric M1–M10 has a source that fits the trust model | Pass → the metrics spec stands; fail → drop or redesign the metric | CT | BUD-TEL | `SYN → results` | (spike runner) | — |
| E2-S3 Interim-protection recommendation | One actionable stopgap per device type the owner can apply this month | Pass → owner checklist; fail → the owner does a concierge copy for that device type | CT | BUD-SUPPORT | `PUB → results` | (spike runner) | — |

## Conflicts with settled text

1. **OD-01 (inherited):** CLAUDE.md "Platforms (v1) … iOS" vs ADR-0002 §4 "Deferred". E2 agrees with B4's option B. Not resolved here.
2. **USB return trip phasing:** no conflict while v1 still ships it (in M2). If the owner wants v1 without it, that amends ADR-0002 §1.
3. **M1 status report vs "no admin dashboard" (OD-13):** a generated document is not a dashboard. If it becomes a web page, OD-13 applies.
4. **Browse and share (a later Immich)** falls under OD-13.

No other conflicts. Media-only Android (OD-19) is a subset of "files on the device" and needs no settled-text change.

## Open questions

| Question | Who answers | By when |
|---|---|---|
| All intake answers in §8 | Owner (H2) | Wave 0 / week 1 |
| iPhone share of camera-roll bytes | E1-S2a | Wave 1 exit |
| What documents do Android phones actually hold, and where (Download vs Documents vs app folders)? | E1 census (desktop only) and visit walk-through | Wave 2 |
| Play review outcome and timing for all-files access for a backup app | B3 (policy page blocked here) | Before OD-19 is revisited |
| Are Takeout and icloudpd "originals" byte-identical to device originals? | A9-S1 | Wave 2 |
| Exact Google Photos and iCloud settings wording (support pages blocked) | Owner on device during E2-S3; H1 allowlist | Before the stopgap checklist is handed over |
| Whether M1's report needs email (OD-03) | D6 / owner | Wave 1 |
| Stage durations and BUD-COVER value | Owner via H1 | Wave 2 |

## Recommendation

Adopt the **provisional ADR-0004 in Appendix A**:
- The settled v1 platforms, minus iOS until after the pilot (bridge via a family computer; OD-01 option B).
- Android media only (OD-19).
- LAN direct deferred.
- Delivery in milestones M0 (stopgaps now) → M1 (concierge) → M2 (desktop) → M3 (Android).
- Pilot P0 → P3 with the gates, stop rules and kill checkpoints in §4.
- The word "Protected" gated on receipts plus a passed restore drill.
- Metrics M1–M10, with no third-party analytics.

**What would change it:**
- iPhone share ≥ 40 % → OD-01 option A, and iOS moves into v1 with Apple spend.
- Owner hours ≫ 8 h/week → M1 may be skipped.
- The census shows phones hold important documents in Download → revisit OD-19 with all-files access after B3.
- The owner declines visits → M1 is replaced by relatives' USB return trips.

## Decision requests

### OD-19: Documents on Android in v1

- **Needed by:** Wave 1 exit (decision sitting 2).
- **Evidence:** this note §2 (C1–C3); B3 (pending).
- **Options:**

  | Option | What it means for the family | Cost (money and owner time) | Reversibility | Risks |
  |---|---|---|---|---|
  | A. Media only (recommended) | Phone photos and videos protected; documents protected on computers only | None extra | Easy: add B or C later | Documents only on a phone stay unprotected (size unknown until E1) |
  | B. Chosen folders (SAF) | Relative picks folders once in the system picker | Support time per phone | Easy | Cannot include **Download** or storage root on Android 11+ (C1); grants lost if folders move; users must operate the picker |
  | C. All-files access | Everything in shared storage | Play policy review; settings-page toggle per phone (C2) | Costly if Play rejects late | Policy rejection; a settings trip for relatives; broadest data sweep (D6 optics) |

- **Recommendation:** A for v1. Revisit C after B3's policy dossier and the census.
- **Touches settled text:** none.
- **If no decision by the deadline:** assume A (the intake default Q-H2). This blocks nothing.

### DR-E2-1 (H1 to number): Adopt the provisional v1 scope and milestone plan (ADR-0004 draft, Appendix A)

- **Needed by:** Gate A (ADR-0004 is a Gate A ADR); provisional acceptance at decision sitting 2.
- **Options:** A. As drafted (M0–M3, pilot P0–P3). B. Skip M1 and go straight to the kit (needs more owner hours). C. Concierge only for v1 (no apps). This does not meet the CLAUDE.md v1 assistant features, so it needs a settled-text change.
- **Recommendation:** A.
- **Touches settled text:** only through OD-01, which is already queued.
- **If no decision:** the run assumes A as provisional.

### DR-E2-2 (H1 to number): Apply the interim protection this month (intake Q-H5)

- **Needed by:** now.
- **Options:** A. One stopgap per device type (§5.1) plus copying only-copy items first. B. None.
- **Recommendation:** A. It is cheap, reversible, and the only protection for the next 12–24 months (C14).
- **Touches settled text:** none.
- **If no decision:** nothing is protected in the meantime.

### DR-E2-3 (for H1, not the owner queue): Candidate budget IDs BUD-COVER, BUD-FALSESAFE and BUD-PILOT-DUR (§4.4)

These are for the budget sheet, with the owner to confirm at the next sitting.

## Hand-offs

| To | What | Why |
|---|---|---|
| E3 | Gate "Protected" on receipts plus a passed platform restore drill; M9 false-safe = 0; cloud-only bucket | ADR-0024 vocabulary |
| B8 / D6 | M1–M10 field list (plaintext vs encrypted); Syncthing versioned-consent pattern | Data dictionary, consent |
| A9 | Stopgap provenance; keep bytes as received; measure Takeout and icloudpd byte identity in A9-S1 | Import design |
| A6 | A browsable read-only view is needed for a later Immich viewer | §6 dependency |
| B3 | Play review evidence for all-files access (page blocked here) | OD-19 revisit |
| E1 | Census question: documents on phones (Download vs Documents); visit block order | OD-19, test plan |
| E6 | "Browse and share" script; stopgap checklist wording | Plain language |
| H1 | Candidate budget IDs; blocked sources (support.google.com, support.apple.com, nngroup, research.google, dl.acm.org, measuringu, developers.google.com); WebSearch budget exhausted | Registries, allowlist |
| Synthesis | Lift Appendix A into `docs/adr/0004-v1-scope-platforms-non-goals.md` (Status: Proposed, provisional) | PLAN §5.1 stage 5 |

---

## Appendix A. ADR-0004 draft text (Proposed, **PROVISIONAL**, pending owner intake)

> **ADR-0004: v1 scope, platforms (including iOS timing) and non-goals**
>
> - **Status:** Proposed. **PROVISIONAL:** it is built on the intake defaults (`owner-intake.md` §K and Part 2). The owner intake (H2) and the E1 census are not answered yet, so every row marked † may change.
> - **Date:** 2026-09-29
> - **Owner workstream:** E2 (+B4)
> - **Decider:** the owner
> - **Gate:** A
> - **Supersedes / Amends:** None. Adopting the iOS row needs a CLAUDE.md amendment through OD-01.
> - **Evidence:** `docs/research/e2-v1-scope-metrics-pilot.md`, `docs/research/b4-ios-decision.md`, `docs/research/f1-build-adopt-fork-compose.md`
> - **Traceability:** R-03, R-06, R-33, R-36
> - **Owner decisions:** OD-01, OD-19, OD-13 (browse), DR-E2-1
> - **One-way door:** No
>
> **Context.** The settled v1 (CLAUDE.md) covers five platforms, discovery, health and nudges, R2 plus USB, admin restore and keep-forever retention. ADR-0002 defers iOS. F1 estimates 1,070–2,140 h to v1, about 24 months to desktop plus Android at 8 h/week†. The family needs protection long before that.
>
> **Decision.**
> 1. **Platforms v1:** Windows, macOS, Linux, Android. **iOS after the pilot†** (OD-01 option B), with iPhone photos covered through a family computer syncing iCloud originals. The core honours B4's constraints K1–K14.
> 2. **Sources v1:** files on the device. Android: **camera roll and media only†** (OD-19). Desktop: photos, videos and documents in user folders, plus the macOS Photos library (the iPhone bridge).
> 3. **Transports v1:** R2 and USB (the owner seeds first; relatives' return trip in the desktop app). LAN direct deferred (ADR-0037).
> 4. **Assistant v1:** discovery proposals; plain-language health; nudges in the app, as OS notifications and by email. "Protected" is shown only with receipts **and** a passed restore drill for that platform.
> 5. **Delivery milestones:** M0 stopgaps → M1 concierge† (owner USB seeding and a status report) → M2 desktop kit → M3 Android.
> 6. **Pilot:** P0 owner → P1 helper → P2 extreme user → P3 everyone, with the gates, stop rules and rollback in the evidence note §4. Stopgaps stay on throughout.
> 7. **Success metrics:** M1–M10 (evidence note §3). No third-party analytics.
>
> **Non-goals for v1:** end-user restore; browse and share (answer: a later LAN-only viewer, OD-13); an admin dashboard; import from cloud services, email or social media (roadmap); LAN direct; Android documents†; iOS†; widgets and SMS nudges; off-site copy of the homelab (settled).
>
> **Consequences.**
> - Good: protection starts in M0 and M1; the scope is sized to one maintainer.
> - Bad: phone-only documents and iPhones without a family computer stay on stopgaps longer.
>
> **Confirmation:** E2-S1, E2-S2 and E2-S3; pilot gates; M9 = 0.
>
> **† Rows the intake or census may change:** see §8 of the evidence note.

## Appendix B (§8). Intake answers that could change this note and ADR-0004

| Intake ID | Question (short) | If the answer is… | …then |
|---|---|---|---|
| Q-B9 | Owner build hours per week | Much more than 8 h/week | M1 can be shortened or skipped; iOS may move earlier |
| Q-B9 | (same) | Much less than 8 h/week | M1 concierge becomes v1's main delivery; F1's "compose stopgaps" pivot |
| Q-F3 | iPhone share of camera-roll bytes (and E1-S2a) | Over 40 % | OD-01 option A: iOS in v1, Apple spend (Q-B8), the platform order changes |
| Q-F2 | Device counts by type | Few desktops, many Android phones | Android first instead of desktop first |
| Q-F2 | (same) | Many iPhones and no family computers | The bridge fails; escalate OD-01 |
| Q-F4 | Total keepsake size | Over 10 TB | More USB seeding; C4 and C5 sizing; BUD-COVER timing |
| Q-F6 | People without email or a Google account | Any | Email nudges and M1 reports need another channel; Play closed-track opt-in fails |
| Q-F7 | Accessibility needs | Any | E6 scope inside v1; test plan changes |
| Q-F8 / Q-F9 | Relatives willing to take part; a helper | Fewer than 5 | E2-S1's 5-relative pass rule cannot run; P1 has no helper |
| Q-G2 | Cloud photo settings in use | Storage saver or Free up space already used | Originals are already gone for those items; the Takeout route in §5.1; the cloud-only bucket matters more |
| Q-G4 | Only-copy items today | Yes | The owner copies them before anything else (§5.1) |
| Q-H1 | iPhone view (OD-01) | "In v1" | As for Q-F3 over 40 % |
| Q-H2 | Android documents (OD-19) | Chosen folders or all files | B3 policy work on the critical path; the documents row changes |
| Q-H3 | Desktop or Android first | Android | The pilot order and M2/M3 swap |
| Q-H4 | Concierge start acceptable | No | M1 is dropped; the family waits for M2 with stopgaps only |
| Q-H5 | Apply stopgaps this month | No | Nothing is protected for 12–24 months (C14); flag as an accepted risk (OD-17) |
| Q-H6 | Browse and share | "Needed in v1" | OD-13; A6 must provide a read-only view; scope grows |
| Q-D1 / Q-D2 / Q-D5 | Home and relatives' bandwidth and caps | Slow uplinks or caps | More USB; stop condition 6 matters more |
| Q-B1 / Q-B2 | Cost ceilings | Low | More USB seeding instead of R2 in seed months |
| Q-B8 | Signing and Apple spend | Yes to Apple | iOS becomes cheaper to bring forward |
| Q-A3 | A household in BR/ID/SG/TH | Yes | Android developer verification is already enforced there (T2); B3 timing |
| Q-A4 | Languages | Not English only | E6 localisation inside v1 |
| Q-F5 | Managed work or school devices | Any hold keepsakes | Out of scope for the app; concierge copy or stopgap only |
