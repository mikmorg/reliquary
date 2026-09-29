# E1. Family research and census

- **Workstream:** E1 (see `docs/research/PLAN.md`, section "E1.")
- **Status:** Draft (analyst deep read, Wave 1). It has not had skeptic review yet.
- **Date:** 2026-09-29 (last updated 2026-09-29)
- **Feeds:** OD-01 (through E1-S2), ADR-0004 (v1 scope; E2 + B4), ADR-0039 (accessibility and localisation; E6), ADR-0023 (discovery; E4), C4 (growth per person), G2 (device matrix), B1/B2 (support policy), A7-S3, H3 (consent script and census output format).
- **Depends on:** H2 (owner intake: Q-F1 to Q-F11, Q-G1 to Q-G6, Q-J5), H3 (data classes, output check, consent script), B4 (the OD-01 gate definition), E2 (consolidated visit plan).
- **Traceability rows closed or advanced:** R-03 (advanced: E1-S2 method and timing), R-06 (advanced: protocol and what must be observed rather than asked).

## Summary

- **What can be known now, without the family:** the platform facts, the measurement methods, and their blind spots. This note settles those.
- **What cannot be known without the family:** everything that drives the product decisions. That includes the iPhone share of camera-roll bytes, library sizes and growth, where keepsakes really live, beliefs about backup, comfort with technology, languages, and accessibility needs. No public or vendor source gives a particular household's numbers, and population surveys cannot stand in for E1-S2 (§1).
- **The biggest finding is about timing.** OD-01 is due at Wave 1 exit (decision sitting 2), but the consolidated visits are booked for weeks 3–7 (H5 L26). E1-S2 as planned therefore lands **after** the decision it gates (C19). This note proposes splitting it:
  - **E1-S2a** is a remote quick count in Wave 1. The owner phones each library owner, who reads two or three storage figures from Settings. No installation is needed.
  - **E1-S2b** confirms the figures at the visit.
  - The gate is judged on a **range**, not a point, because iCloud "Optimize Storage" and Google Photos "Free up space" hide original bytes from the device (§2).
- **An iOS census app is not a practical E1-S2 method.** Apple's first public per-resource byte size, `PHAssetResource.dataSize`, only arrives in iOS 27.0 and can be `nil` (C1). Before 27.0, even a widely used plugin reads sizes through undocumented keys (C2). Installing any app on relatives' iPhones needs the Apple Developer Program, which is the spend OD-01 is deciding (C3).
- **The census script needs two changes to the plan.**
  - The walker the plan names, `jwalk`, is deprecated by its author, who points to `dua-core` (C11). `dua-core` hides the file attributes that mark cloud placeholders.
  - Magic-byte sniffing reads file data, so it would download OneDrive and iCloud placeholders (C9, C10).
  - Recommendation: a std-based walker that reads placeholder bits during enumeration and classifies by extension first.
- **Desk research on older users is thin but consistent.** W3C WAI's position is that its accessibility standards cover most needs of ageing users (C14). The platforms offer supporter-configured modes (Assistive Access) and 200 % text (C15, C16), so the census should record these settings.
- **Blocked:** the HCI papers named in the plan, NN/g, Pew, LoC and all Apple and Google support pages could not be read from this container. Findings that rest on them are marked secondary-only.

## Questions

| # | Question (PLAN E1 key questions, plus new ones) | Short answer | Confidence |
|---|---|---|---|
| 1 | Per person: devices, OS versions, storage, camera-roll size and monthly growth, placeholders | Unknown until the census. §3–§4 say what each platform can measure without reading content, and what it cannot see. Monthly growth: from capture-month histograms on desktop and Android; on iPhone, from two readings a few weeks apart (S2a, then S2b). | High on method; no data |
| 2 | Share of camera-roll bytes on iPhones and iPads (E1-S2) | Unknown. Define it per **library**, in original bytes, counting each iCloud library once (§2.1). Measure it without installing anything (§2.2). Judge the 40 % gate on a low–high range (§2.3). | High that it is unknown; Medium on the method |
| 3 | Chromebooks, shared computers, managed work or school devices | Census questions, plus what the script can and cannot see (§3.4). Recommend **not** running the census on managed devices: record by self-report only whether they hold keepsakes. | Medium |
| 4 | Where keepsakes live; past losses; what would hurt most | Interview only. The census finds candidate locations on desktops (the E1-S1 criterion "one unmentioned location"). Messaging apps, email, drawers, tapes and prints need interview prompts (§5). | High that only the family can answer |
| 5 | What people believe is backed up; paid cloud storage | Ask, then **check together** on the device (settings screens), and record belief and reality separately (§5). | Medium |
| 6 | Comfort with technology; own email and Google account; installing an app, scanning a QR code, typing a 12-character code; notification and email habits | Observe, don't ask: these are E2/E5 tasks at the same visit. Self-report is only a screening aid. | Medium (method judgement) |
| 7 | Feelings about the admin seeing everything; what they would exclude | Interview, after the consent script explains the trust model in plain words. Answers feed OD-12 and OD-17 as counts and themes, never per-person quotes tied to names. | Medium |
| 8 | Languages; vision, motor, hearing and cognitive needs | Census records OS settings (text size, Assistive Access, TalkBack/VoiceOver on or off) plus self-report. WAI prevalence figures give dated priors only (C14). | Medium |
| 9 | Research ethics: owner as researcher; neutral facilitator? | Owner-run by default with a written protocol; E1-S3 compares a facilitator on 2–3 relatives. Minors per H3 §9. | Medium |
| 10 | (new) Can E1-S2 land before OD-01 is due? | Not through the visits. Hence E1-S2a, a remote quick count in Wave 1 (C19). | High |
| 11 | (new) Is the census toolchain in PLAN still right? | No: `jwalk` is deprecated (C11), and sniffing hydrates placeholders (C10). PLAN also names Google Forms, which conflicts with H3's rule against third-party tools for family data (§5.3). | High |
| 12 | (new) What can and cannot be known without the family? | §1 | High |

## Method

- **Sweep:** two scouts ran: docs (Apple, Android, Microsoft, W3C, LoC, Pew, crates) and source (crate tarballs, osxphotos, pymobiledevice3, Flutter photo_manager). No issues/forums scout and no papers scout ran for E1 in this wave.
- **Analyst re-reads (2026-09-29):**
  - Apple DocC JSON for `PHAssetResource.dataSize`, `PHAuthorizationStatus.limited`, `ubiquitousItemDownloadingStatusKey` and Assistive Access.
  - developer.android.com `MediaStore.MediaColumns` and the Android 14 partial photo access page.
  - The crate tarballs of `jwalk` 0.9.0, `dua-core` 4.1.0 and `infer` 0.22.0.
  - The sdists of osxphotos 0.77.2 and pymobiledevice3 11.19.4, and the pub.dev archive of photo_manager 3.12.0.
  - W3C WAI's older-users pages, from a blobless git clone of `w3c/wai-website` (the `w3c/wai-older-users` repo is archived and points there).
- **Scout conflict resolved:** the source scout inferred that PhotoKit has no public byte-size API, because photo_manager uses the private `fileSize` key. The docs scout found `dataSize`. Both are right for different OS versions:
  - `dataSize` is documented from iOS 27.0 (C1).
  - photo_manager 3.12.0 still uses the private keys, with no `dataSize` path in its darwin sources (analyst grep).
  - Before 27.0, the analyst found no documented public size property, but did not check exhaustively (C2, Medium).
- **Blocked sources (for H1; none silently replaced):**
  - support.apple.com (108782, 105061, 102670, 108429, 108922)
  - support.google.com (Photos "Free up space"; Google One storage)
  - support.microsoft.com (OneDrive Files On-Demand), seen as snippets only
  - www.w3.org (read instead through the `w3c/wai-website` git mirror, the same primary source)
  - digitalpreservation.gov / loc.gov, archives.gov, pewresearch.org, gs.statcounter.com, limesurvey.org, exiftool.org, metacpan
  - www.nngroup.com, dl.acm.org, arxiv.org, api.crossref.org, api.openalex.org, semanticscholar.org, en.wikipedia.org (all refused from shell and WebFetch)
  - The WebSearch budget for the session was used up, so no further snippet searches were possible.
- **Stop rule:** the analyst's re-reads added one new primary source (the WAI mirror) and changed no scout claim except the dataSize/private-key conflict above. The HCI papers the plan names (Marshall, Kaye et al., Odom et al., Grinter et al., Poole et al., Kiesler et al.; *The Mom Test*; Krug) were **not read**. Where this note leans on their ideas, it says so, and those points are secondary-only.

## Sources

| # | Source | Publisher | Published or version date | Accessed | Primary? |
|---|---|---|---|---|---|
| S1 | `PHAssetResource.dataSize` — https://developer.apple.com/documentation/photos/phassetresource/datasize-5lxva (DocC JSON at `developer.apple.com/tutorials/data/documentation/photos/phassetresource/datasize-5lxva.json`) | Apple | Introduced iOS/iPadOS/macOS/tvOS/visionOS 27.0 | 2026-09-29 (analyst, full) | Yes |
| S2 | `PHAssetResource` — https://developer.apple.com/documentation/photos/phassetresource | Apple | iOS 9.0+ | 2026-09-29 | Yes |
| S3 | `PHAssetResourceManager` — https://developer.apple.com/documentation/photos/phassetresourcemanager | Apple | iOS 9.0+ | 2026-09-29 (scout; also B4 S13) | Yes |
| S4 | `PHAuthorizationStatus.limited` — https://developer.apple.com/documentation/photos/phauthorizationstatus/limited | Apple | iOS/iPadOS 14.0+ | 2026-09-29 (analyst) | Yes |
| S5 | `PHPhotoLibrary.authorizationStatus(for:)` — https://developer.apple.com/documentation/photos/phphotolibrary/authorizationstatus(for:) | Apple | iOS 14.0+ | 2026-09-29 (scout) | Yes |
| S6 | Assistive Access — https://developer.apple.com/documentation/accessibility/assistive-access | Apple | Undated | 2026-09-29 (analyst) | Yes |
| S7 | `UISupportsFullScreenInAssistiveAccess` — https://developer.apple.com/documentation/bundleresources/information-property-list/uisupportsfullscreeninassistiveaccess | Apple | iOS/iPadOS 17.0+ | 2026-09-29 (scout) | Yes |
| S8 | `URLResourceKey.ubiquitousItemDownloadingStatusKey` — https://developer.apple.com/documentation/foundation/urlresourcekey/ubiquitousitemdownloadingstatuskey | Apple | iOS 7.0+, macOS 10.9+ | 2026-09-29 (analyst) | Yes |
| S9 | `MediaStore.MediaColumns` — https://developer.android.com/reference/android/provider/MediaStore.MediaColumns | Google | Last updated 2026-08-03 | 2026-09-29 (analyst) | Yes |
| S10 | Grant partial access to photos and videos (Android 14) — https://developer.android.com/about/versions/14/changes/partial-photo-video-access | Google | Last updated 2026-03-03 | 2026-09-29 (analyst) | Yes |
| S11 | Android 14 features and APIs — https://developer.android.com/about/versions/14/features | Google | Last updated 2026-09-16 | 2026-09-29 (scout) | Yes |
| S12 | Work profiles — https://developer.android.com/work/managed-profiles | Google | Last updated 2025-02-10 | 2026-09-29 (scout) | Yes |
| S13 | File Attribute Constants — `MicrosoftDocs/win32 @ docs : desktop-src/FileIO/file-attribute-constants.md` (source of learn.microsoft.com) | Microsoft | ms.date 2025-09-23 | 2026-09-29 (scout, full) | Yes |
| S14 | Rust std 1.94.0 — `rust-lang/rust @ 1.94.0 : library/std/src/fs.rs`, `os/windows/fs.rs`, `os/darwin/fs.rs` | Rust project | Tag 1.94.0 | 2026-09-29 (scout) | Yes |
| S15 | XNU `bsd/sys/stat.h` (`SF_DATALESS`) — `apple-oss-distributions/xnu @ main` | Apple | main | 2026-09-29 (scout) | Yes |
| S16 | `jwalk` 0.9.0 crate — https://static.crates.io/crates/jwalk/jwalk-0.9.0.crate; crates.io API | jwalk author | 2026-08-05 | 2026-09-29 (analyst) | Yes |
| S17 | `dua-core` 4.1.0 crate — https://static.crates.io/crates/dua-core/dua-core-4.1.0.crate | Byron/dua-cli | CHANGELOG 4.1.0 dated 2026-09-12 | 2026-09-29 (analyst, parts) | Yes |
| S18 | `dua-cli` 2.45.0 `Cargo.toml` — https://static.crates.io/crates/dua-cli/dua-cli-2.45.0.crate | Byron/dua-cli | 2.45.0 | 2026-09-29 (scout) | Yes |
| S19 | `infer` 0.22.0 crate — https://static.crates.io/crates/infer/infer-0.22.0.crate | infer authors | 0.22.0 (2026-07-15 per scout) | 2026-09-29 (analyst, `get_from_path`, licence) | Yes |
| S20 | `nom-exif` 3.8.0 crate — https://static.crates.io/crates/nom-exif/nom-exif-3.8.0.crate | nom-exif author | 2026-09-07 | 2026-09-29 (scout) | Yes |
| S21 | `kamadak-exif` 0.6.1 crate — https://static.crates.io/crates/kamadak-exif/kamadak-exif-0.6.1.crate | kamadak | 2024-11-06 | 2026-09-29 (scout) | Yes |
| S22 | osxphotos 0.77.2 sdist — https://files.pythonhosted.org/packages/20/57/44770b159a8a3b719083d06a52709fa5851c98dc0a7c4cf8c7c1e36f6d88/osxphotos-0.77.2.tar.gz | R. Taylor | Uploaded 2026-09-27 | 2026-09-29 (analyst: `photosdb.py` l. 2058/2130, `photoinfo.py` l. 725, 1422) | Yes (code) |
| S23 | pymobiledevice3 11.19.4 sdist — https://files.pythonhosted.org/packages/b6/c4/9843e35b5836df037e2636b2b90b15ed34850dcb608a672ef0212a066017/pymobiledevice3-11.19.4.tar.gz | doronz88 et al. | Uploaded 2026-09-27 | 2026-09-29 (analyst: `tests/services/test_afc.py` l. 28, 81, 403) | Yes (code) |
| S24 | Flutter photo_manager 3.12.0 — https://pub.dev/api/archives/photo_manager-3.12.0.tar.gz | fluttercandies | Published 2026-08-09 | 2026-09-29 (analyst: `PMManager.m` l. 269, 2541) | Yes (code) |
| S25 | W3C WAI, "Older Users and Web Accessibility" — https://www.w3.org/WAI/older-users/ via `w3c/wai-website @ 06dcdd1 : pages/fundamentals/people/older-users/index.md` | W3C WAI | last_updated 2025-11-20; first published 2010 | 2026-09-29 (analyst, full) | Yes (mirror of the page source) |
| S26 | W3C WAI, "Overview of Web Accessibility for Older Users: A Literature Review" — https://www.w3.org/WAI/older-users/literature/ via the same mirror, `literature.md` | W3C WAI | last_updated 2018-02-22; first published 2008 | 2026-09-29 (analyst, full) | Yes (statistics are from the 2008 review) |
| S27 | Apple Support 108782 "Set up and use iCloud Photos"; 105061 "Manage your photo and video storage" | Apple | Unknown | Snippets only (blocked) | Primary, **unread** |
| S28 | Apple Support 108429 (check iPhone storage); 108922 (manage iCloud storage) | Apple | Unknown | Snippets only (blocked) | Primary, **unread** |
| S29 | Google Photos Help 6128843 "Free up space"; Google One Help 9312312 | Google | Unknown | Snippets only (blocked) | Primary, **unread** |
| S30 | Microsoft Support, OneDrive Files On-Demand | Microsoft | Unknown | Snippets only (blocked) | Primary, **unread** |
| S31 | Library of Congress, Personal Archiving: Digital Photos — https://digitalpreservation.gov/personalarchiving/photos.html | LoC | Unknown | Snippets only (blocked) | Primary, **unread** |
| S32 | Pew Research Center short read, 2026-01-08; Mobile Fact Sheet | Pew | 2026-01-08 | Snippets only (blocked) | Primary, **unread** |
| S33 | Project documents: `PLAN.md` (E1, §4.1, §4.3), `h3-research-data-governance.md`, `b4-ios-decision.md`, `owner-intake.md`, `h5-long-lead-items.md` (L26, L27), `budgets.md` | Reliquary | 2026-09-29 | 2026-09-29 | Yes (project) |

## Claims

Skeptic columns are empty because this draft has not had skeptic review (PLAN §5.1, stage 4).

| # | Claim | Sources | Key? | Skeptic 1 | Skeptic 2 | Skeptic 3 | Verdict |
|---|---|---|---|---|---|---|---|
| C1 | `PHAssetResource.dataSize` (Swift `Int?`) is "the size of the resource in bytes" and was introduced in iOS/iPadOS 27.0. Apple: "The size may be unknown until a resource has finished being generated or processed, and some resources never report one. `nil` means the size is unknown, not that it is zero." | S1 | Yes | | | | Pending |
| C2 | Before iOS 27 the analyst found no documented public byte-size property on `PHAssetResource`. The documented route to bytes is `PHAssetResourceManager` `requestData`/`writeData`, which reads the data. Flutter photo_manager 3.12.0 reads size via the undocumented KVC key `fileSize` and local availability via `locallyAvailable`, and has no `dataSize` path yet. | S1, S3, S24 | Yes | | | | Pending (absence not checked exhaustively) |
| C3 | Putting any app on relatives' iPhones needs the paid Apple Developer Program (TestFlight or Ad Hoc). The free Personal Team is limited to 3 devices with 7-day profiles. | B4 note C13–C16 (S33) | Yes | | | | Pending (inherits B4's review) |
| C4 | With iCloud Photos and Optimize Storage, full-resolution originals are kept in iCloud and the device keeps smaller copies when space is needed. The device's Photos figure then understates library bytes. The scout also reported that Optimize is on by default, but that was not confirmed. | S27 | Yes | | | | **Secondary only** (primary unread; snippets) |
| C5 | The on-device breakdown is at Settings > General > [device] Storage > Photos. iCloud usage by app is at Settings > [name] > iCloud > Storage. The exact wording in current iOS is unverified. | S28 | Yes (kit steps) | | | | **Secondary only**; verify on a real device (kit step) |
| C6 | Google Photos "Free up space" deletes backed-up items from the device and keeps them in Google Photos. A device or MediaStore census then cannot see them. | S29, S9 | Yes | | | | **Secondary only** for the feature; High for the inference |
| C7 | MediaStore exposes, per item, `_size` (indexed `File.length()`), `RELATIVE_PATH` (e.g. `DCIM/Vacation/`), `VOLUME_NAME`, `DATE_TAKEN`, `IS_PENDING`, `IS_TRASHED` (retained until `DATE_EXPIRES`) and `GENERATION_ADDED` (monotonic). An Android census can aggregate bytes by folder, volume and capture month without reading content or exporting names. | S9 | Yes | | | | Pending |
| C8 | iOS apps can hold `.limited` library access (iOS 14+), and Android 14 apps targeting API 34 can be limited to user-selected media (`READ_MEDIA_VISUAL_USER_SELECTED`). A census app that does not check this undercounts silently. | S4, S5, S10 | Yes | | | | Pending |
| C9 | Windows marks placeholders with `FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS` (0x00400000), `RECALL_ON_OPEN` (0x00040000; enumeration only), `PINNED`/`UNPINNED` and `OFFLINE`. Rust std returns these via `MetadataExt::file_attributes`, and `DirEntry::metadata` needs no extra system call on Windows. macOS marks dataless files with `SF_DATALESS` (0x40000000), readable via `st_flags()`. | S13, S14, S15 | Yes | | | | Pending |
| C10 | `infer::get_from_path` opens the file and reads up to 8,192 bytes. Sniffing a placeholder is a data access and (inference) triggers a download from OneDrive or iCloud, which costs time and the relative's bandwidth. | S19, S13 | Yes | | | | Pending (hydration by sniffing is an untested inference) |
| C11 | `jwalk` 0.9.0 (2026-08-05) says "This crate is no longer maintained or supported. Use `dua-core` instead." `dua-core` 4.1.0 (MIT, rust-version 1.88) is the successor. Its public `Metadata` exposes size, allocated size and times, but not Windows attribute bits or macOS `st_flags`; on macOS it tests only `SF_FIRMLINK`. | S16, S17, S18 | Yes | | | | Pending |
| C12 | osxphotos 0.77.2 reads each asset's original size from `ZADDITIONALASSETATTRIBUTES.ZORIGINALFILESIZE` (`PhotoInfo.original_filesize`). It exposes `ismissing` (not downloaded from iCloud), warning that the flag can lag, and it reads camera make from the Photos database. Whether the size field is filled for cloud-only assets is **unverified**. | S22 | Yes | | | | Pending |
| C13 | pymobiledevice3 (GPL-3.0-or-later) lists `DCIM` at the AFC root over USB. Its test mock says iOS 27.2 answers PERM_DENIED for e.g. `/PhotoData/UBF`. AFC also returns filenames, so any use must aggregate on the computer. | S23 | No (rejected method) | | | | Pending |
| C14 | W3C WAI: "existing international accessibility standards from the W3C … address most older user needs". It lists declining vision, physical ability, hearing and cognition. Its literature-review overview (updated 2018-02-22, from a 2008 review) cites: some hearing loss in 47 % of people aged 61–80 and 93 % aged 81+; significant vision loss in 16 % (65–74), 19 % (75–84) and 46 % (85+); arthritis in at least 50 % over 65; essential tremor in up to 20 % over 65. | S25, S26 | Yes (for E6 priors) | | | | Pending (statistics are old; priors only) |
| C15 | Assistive Access "tailors the iOS and iPadOS experience for people with cognitive disabilities". "A trusted supporter, such as a family member or caregiver, sets up this feature" and chooses which apps are available. Apps can declare `UISupportsFullScreenInAssistiveAccess` (iOS 17+). | S6, S7 | Yes | | | | Pending |
| C16 | Android 14 supports nonlinear font scaling up to 200 %. | S11 | No | | | | Pending |
| C17 | Android work profiles are IT-admin controlled, and "the personal and work profiles have separate storage areas". | S12 | Yes | | | | Pending |
| C18 | Pew (2025 NPORS): 78 % of U.S. adults 65+ own a smartphone, compared with 97 % under 50 and 90 % aged 50–64. | S32 | No (population prior only) | | | | **Secondary only** (snippets; page carrying the figure not confirmed) |
| C19 | OD-01 is needed at Wave 1 exit and cites E1-S2 as evidence. The consolidated visits that run FM spikes are planned for weeks 3–7 of the run. E1-S2 as written therefore cannot inform OD-01 in time. | S33 (PLAN §4.1, §4.3; H5 L26; decision-queue) | Yes | | | | Pending |
| C20 | No public, vendor or survey source gives a particular family's split of camera-roll bytes between iOS and Android. National OS-share or ownership figures (C18, StatCounter) are about people or web traffic, not bytes, and cannot substitute for E1-S2. | Analysis; S32 | Yes | | | | Pending |

## Findings

### 1. What can and cannot be known without the family

| Topic | Knowable now (desk and container) | Only from the family | Confidence |
|---|---|---|---|
| iPhone share of camera-roll bytes | How to define and measure it, and its error sources (§2) | The number itself (C20) | High |
| Library sizes, growth, file types | What each platform exposes without reading content (C7, C9, C12) | The sizes, the growth, the mix (feeds H3 §7.6, C4, A7-S3) | High |
| Placeholders (iCloud Optimize, Google Photos "Free up space", OneDrive) | That they exist and how to detect each (C4, C6, C9) | Who uses which setting, and how many bytes are cloud-only | High on detection; Medium on behaviour (C4 and C6 secondary) |
| Hidden stores | That the census cannot see work profiles (C17), limited-access grants (C8), other users' profiles on shared PCs (expected, not tested), Google Photos Locked Folder (PLAN B2), or keepsakes inside messaging apps and email | Whether any of these hold keepsakes | Medium |
| Where keepsakes live, past losses, what hurts | Generic prompts (LoC guidance, secondary: cameras, computers, memory cards, the web) | Everything specific | High |
| Beliefs about backup; paid cloud storage | That Google accounts share one quota across Gmail, Drive and Photos (secondary, S29) | Beliefs, and the gap between belief and reality | Medium |
| Comfort with technology, accounts, QR scanning, code typing | Nothing useful | Observed performance (E2/E5 tasks) | High |
| Attitudes to admin access and exclusions | Nothing | Everything | High |
| Languages; accessibility | Dated prevalence priors (C14); platform features to record (C15, C16) | Actual needs and settings per person | Medium |
| Managed devices | That work profiles have separate storage (C17), and that WDAC and EDR may block tools (PLAN B1) | Whether they exist in the family and hold keepsakes | Medium |

### 2. E1-S2: the iPhone share gate

**2.1 Define the metric before measuring (proposal).** "Share of camera-roll bytes on iPhones or iPads" is ambiguous in three ways.

1. **On-device bytes versus library bytes.** Under iCloud Optimize, the device holds smaller copies (C4). OD-01 asks whether Reliquary must protect iPhone camera rolls, and an iOS client would have to download the originals (B4 C10). The right quantity is therefore **original bytes in the library**, including cloud-only originals.
2. **One library, several devices.** An iPhone, an iPad and a Mac on the same Apple ID share one iCloud Photos library. Count each library **once**, and attribute it to "Apple" when its main capture device is an iPhone or iPad.
3. **The denominator.** Use phone and tablet camera libraries only: iOS libraries plus Android camera libraries (DCIM and Pictures on the device, plus Google Photos cloud-only originals). Exclude desktop-only archives (old camera cards, scans); they are A9's import-first seed, not a camera roll.

Proposed definition:

> share = Σ original bytes of Apple camera libraries ÷ Σ original bytes of all phone/tablet camera libraries, each library counted once.

**2.2 Measurement options (no installation on iPhones)**

| # | Method | What it measures | Error sources | Data class | Verdict |
|---|---|---|---|---|---|
| M1 | iPhone with iCloud Photos on: read the Photos figure in iCloud storage (Settings > [name] > iCloud > Storage) | Library bytes held in iCloud (≈ originals) | Path wording unverified (C5). May include items added from a Mac or iPad on the same library. Shared Library and Recently Deleted treatment unknown. | FAM → AGG | **Primary iOS method** |
| M2 | iPhone without iCloud Photos: Settings > General > [device] Storage > Photos | On-device bytes ≈ originals (nothing is optimised away) | Wording unverified (C5). The figure may include caches. | FAM → AGG | **Primary iOS method** when iCloud Photos is off |
| M3 | Mac with the same library: aggregate osxphotos query (sum of `original_filesize`, grouped by camera make and by `ismissing`) | Original bytes, split by capture device | Unverified whether the size is filled for cloud-only assets (C12). Needs a family Mac. Must run on the Mac and export totals only. | FAM → AGG | Optional cross-check at the visit (S2b) |
| M4 | iOS 27+ census app using `dataSize` | Per-resource bytes | `nil` sizes (C1). Needs full (not limited) access (C8). Needs the Apple Developer Program (C3). iOS 27 devices only. | FAM → AGG | **Reject for the gate**: it presupposes the spend OD-01 decides |
| M5 | App using private `fileSize`/`locallyAvailable` keys | Bytes, local vs cloud | Undocumented, fragile, App Review risk (C2), plus the M4 costs | — | Reject |
| M6 | USB + pymobiledevice3 AFC listing of `DCIM` | Local camera files | Returns filenames. Almost certainly misses cloud-only originals (not verified). GPL tool. Needs pairing and trust. | FAM | Reject |
| A1 | Android with Google Photos backup: cloud Photos figure (Google One storage) **and** on-device Images/Videos (Settings > Storage; labels vary by OEM, unverified) | Cloud copies; local copies | Items that are both local and backed up appear in both figures. "Storage saver" copies are re-encoded, not originals. Settings pages are secondary (C6). | FAM → AGG | **Primary Android method**: record both figures |
| A2 | Android census app (MediaStore aggregate, C7) | Local originals by folder and month | Misses "freed" items (C6) and limited access (C8). Needs a sideloaded APK. | FAM → AGG | At the visit (S2b / E1-S1 Android variant), only if B2 has a build |

**2.3 Decision rule with uncertainty (proposal).** For each library, record a low and a high estimate:

- **Android:** low = max(device, cloud); high = device + cloud.
- **iOS:** M1 or M2, with ±0 unless the reading is ambiguous.

Then:

- share_low = Apple_low ÷ (Apple_low + Android_high)
- share_high = Apple_high ÷ (Apple_high + Android_low)

The rule:

- If share_low ≥ 40 %, escalate OD-01, as B4 recommends.
- If share_high < 40 %, do not escalate.
- If the range straddles 40 %, run M3/A2 at the earliest visit. If OD-01's deadline arrives first, the owner chooses, with the range shown.

The 40 % threshold is PLAN's own; this note does not change it.

**2.4 Timing (C19).** Run **E1-S2a** in Wave 1:

- The owner makes a 10–15 minute call per library owner.
- The relative reads two or three numbers from Settings while the owner writes them in the private store (H3 R7).
- Only the family-wide share range, and per-platform totals, leave the store (H3 §4).
- The owner's intake guess (Q-F3) is a prior, not a result.

**E1-S2b** at the visit re-reads the same screens. That gives a second time point for monthly growth, and runs M3 or A2 where a straddle needs it.

**2.5 Privacy note.** With 10–25 devices, per-person library sizes are identifying within the family. Only family-wide figures enter AGG, and per-person cells below 5 are suppressed (H3 §4).

### 3. E1-S1: census script design constraints

1. **Walker.** Do not use `jwalk`, which is deprecated (C11). `dua-core` is fast but hides the placeholder bits (C11). Recommended: a std-based recursive walk.
   - On Windows, `DirEntry::metadata` gives `file_attributes()` without an extra system call (C9).
   - On macOS, `st_flags()` gives `SF_DATALESS`.
   - Measure it against E1-S1's "< 10 min" criterion. Fall back to `dua-core` for traversal plus a per-file `stat` only if it is too slow.
2. **Placeholders first.** Check `RECALL_ON_DATA_ACCESS`, `RECALL_ON_OPEN` and `OFFLINE` (Windows) and `SF_DATALESS` (macOS) **before** any read. Count placeholders by extension into a separate "cloud-only" category, and never open them (C9, C10).
   - macOS Photos libraries under "Optimize Mac Storage" are a package, not loose files. Treat the `.photoslibrary` package as one unit, and use M3 if detail is needed.
3. **Classify by extension first; sniff sparingly.** `infer` reads up to 8 KiB per file (C10). Sniff only local files whose extension is missing or ambiguous.
   - `infer` 0.22.0 has no separate DNG/NEF/ARW matchers, which report as TIFF, and no GEDCOM matcher (scout, S19). Use extension rules for RAW and genealogy files.
4. **Capture month and camera make (optional).** `nom-exif` 3.8.0 (pure Rust; images and MP4/MOV) avoids shipping ExifTool and a Perl runtime. `kamadak-exif` is image-only. Output only month-level capture histograms and camera **models** (H3 §4 allows models, not serials).
5. **Output format.** Use H3 §7.6: per device class, `category, ext_group, log2_bin, count, bytes`. Add a device record (below) and the placeholder totals. Show before sending (H3 R6), write to a file the person hands over, and never upload.
6. **Scope.** The script runs on Windows, macOS and Linux desktops. Android uses the A2 MediaStore variant if B2 produces a build; otherwise use Settings readings. There is **no iOS census app** (§2.2).
7. **Access limits to report, not hide.** Report other user profiles as "not readable", and record the census app's access level (full or limited, C8).

### 4. Census field list (proposal for the E1-S1 kit)

| Level | Field | How collected | Class after output check |
|---|---|---|---|
| Device | Type; OS and version; model (no serial); storage total and free (binned) | Script or Settings | AGG |
| Device | Upgrade eligibility: iOS 26.1+/27 (B4), Windows 10 end of life, Android version | Settings; vendor lists (Apple list blocked; H1) | AGG |
| Device | Shared or personal; number of user accounts; managed (MDM, work profile, EDR) yes/no | Self-report and Settings | AGG |
| Device | Cloud photo and file services on, and their settings (iCloud Photos + Optimize; Google Photos backup quality + "Free up space" used; OneDrive camera upload and Files On-Demand) | Settings, checked together | AGG |
| Device | Accessibility settings: text size or font scale, bold text, VoiceOver/TalkBack, Assistive Access, zoom | Settings (C15, C16) | AGG (family totals only if sensitive) |
| Library | Bytes and counts per category × log2 bin; placeholder bytes; capture-month histogram (last 24 months) | Script, MediaStore, M1–M3 | AGG |
| Person | Languages; own email; Google/Apple account; pays for cloud storage (yes/no, tier binned) | Interview | AGG |
| Person | Beliefs about what is backed up vs what the check shows | Interview + check | AGG (counts of mismatches) |
| Person | Keepsake locations beyond devices (drawers, drives, SD cards, tapes, prints, messaging apps, email) | Interview prompts | AGG (counts per type) |
| Person | Helps others / is helped by (roles, not names) | Interview | AGG (a graph by pseudonym) |

### 5. Interview protocol and methods

**5.1 Approach.** Use a semi-structured interview inside the consolidated visit.

- Ask about **past behaviour and specifics** ("the last time you changed phones", "the last photo you couldn't find") rather than opinions about a future product. This is the core idea usually attributed to *The Mom Test*; the book was not re-read in this run, so treat the attribution as secondary.
- Follow with a device walk-through (contextual inquiry): "show me where your photos are".
- Then do the census run and the E2/E5 observed tasks.
- Put attitude questions (admin access, exclusions) **after** the consent script has explained the trust model.

**5.2 Researcher bias.** The owner is family and will be the admin, so relatives may understate problems or overstate comfort. Controls:

- a written script;
- recording observed task success separately from self-report;
- E1-S3, where a neutral facilitator runs 2–3 of the interviews and the two sets of concrete past-behaviour stories are compared (PLAN's pass rule);
- the owner leaving the room for the admin-access questions when a facilitator is present.

**5.3 Tools.** PLAN names "LimeSurvey or Google Forms". **Google Forms would send family answers to a third party**, which H3 §1 forbids for FAM. Use paper or an owner-held spreadsheet in the private store (H3 R7), or a homelab-hosted form. The LimeSurvey licence and hosting were not checked (limesurvey.org blocked).

**5.4 Proto-personas (hypothesis slots, to be filled from data; no family facts here).**
1. The owner-admin.
2. The helper: a tech-comfortable relative who supports others. This is the "warm expert" idea in the plan's reading list; the papers were not read.
3. A typical phone-first adult.
4. An extreme user: older, with vision, motor or cognitive needs, possibly with Assistive Access set up by a supporter (C15).
5. A minor, with guardian consent (H3 §9).

### 6. Desk research: older and non-technical users

- **WAI position (C14).** Accessibility for people with disabilities largely covers ageing users: vision (contrast, near focus), dexterity (small targets), hearing and cognition (short-term memory, distraction). For E6 this means a WCAG-based baseline, large targets, high contrast, plain language, and no reliance on audio.
  - The prevalence figures are old (2008 review, 2018 page update), so use them only to size "how likely is at least one relative affected". For example, with several relatives over 65, some vision or dexterity need is likely.
  - That example is an inference, not a measurement of this family.
- **Supporter-configured modes (C15).** Assistive Access is set up by a "trusted supporter" who picks the apps. This matches the helper persona and CLAUDE.md's "owner administers everything". If the census finds Assistive Access users, E6 should consider `UISupportsFullScreenInAssistiveAccess`, which only matters if iOS ships (OD-01).
- **Text scaling (C16).** Android 14 scales fonts up to 200 %, so E6 layouts must survive it. The census records the setting.
- **Smartphone ownership (C18, secondary only).** Most older U.S. adults own smartphones, but fewer than younger adults. This is a population prior and says nothing about this family's iPhone share (C20).
- **Not read (blocked or not fetched):** Pew detail; NN/g senior usability; LoC and NARA personal archiving guides (secondary snippets only); every HCI paper the plan names. A papers scout, or the owner fetching them from a machine with library access, should fill this gap before E6 and E3 finalise copy. It does not block E1-S2 or the census.

### 7. Proposed schedule (weeks counted from "go"; E2 owns the combined visit plan)

| When | Step | Who | Output |
|---|---|---|---|
| Wave 0 (now) | Answer the intake (Q-F1 to F11, Q-G1 to G6, Q-J5); confirm the H3 consent script (§9) and the private store (R7) | Owner | Inputs; consent approved |
| Week 1 | E1-S2a remote quick count, one call per library owner (§2.4); invitations sent; visits booked for weeks 3–7 (H5 L26); facilitator candidate named (H5 L27) | Owner | Share range → OD-01 sitting 2 |
| Weeks 1–2 | E1-S1 census script built and rehearsed on H3 Tier D and SYN trees (CT); dry run on the owner's own devices | Spike runner, then owner | Script and kit; timing against "< 10 min" |
| End of week 2 (Wave 1 exit) | OD-01 decided with the E1-S2a range, or deferred per the §2.3 straddle rule | Owner | OD-01 outcome |
| Week 3 | First visit: the helper persona, plus the E1-S3 facilitator comparison | Owner (+ facilitator) | Protocol fixes |
| Weeks 3–7 | Consolidated visits, from typical to extreme users (E2 order); E1-S2b re-reads | Owner | Raw FAM in the private store only |
| Weeks 7–8 | Output check (H3 §4); anonymised summary, personas, journeys, ranked needs | Owner, then agents on AGG only | Census summary; E1 note final |

### Alternatives compared (research method)

| Option | Fit with settled requirements and H3 | Pros | Cons | Evidence |
|---|---|---|---|---|
| **Home visit with census script + semi-structured interview + observed tasks (recommended)** | Fits: one visit per relative (PLAN); FAM stays local | Real numbers; belief vs reality checked on the device; E2/E5 tasks in the same sitting | Weeks 3–7, too late for OD-01 alone; owner bias | C19, §5 |
| Remote quick count (E1-S2a) | Fits if the owner records numbers in the private store | Fast (Wave 1); no install | Settings wording unverified; placeholders give a range, not a point | C4–C6, §2 |
| Owner-run interviews only | Fits | Cheap; trusted | Bias; relatives may please the owner | §5.2 |
| Neutral facilitator | Fits | Less bias on attitudes and admin access | Scheduling and cost (H5 L27); needs briefing on H3 | PLAN E1-S3 |
| Survey + device checklist | Fits only without third-party form hosts | Scales; low effort | Self-report on sizes and settings is unreliable; misses observed behaviour | §5.3 |
| Diary study | Fits | Captures real nudge and backup moments | High burden on older relatives; overlaps E3-S2's longitudinal pilot | PLAN E3 |

### Similar work and lessons

| Project or paper | What they do | Borrow or avoid | Source |
|---|---|---|---|
| osxphotos | Reads original sizes and cloud state from the Mac Photos database | Borrow for M3 (aggregate only) | S22 |
| Flutter photo_manager | Reads iOS sizes via private keys | Avoid private keys; `dataSize` from iOS 27 | S24, S1 |
| dua-cli / dua-core | Parallel disk usage | Borrow the approach if std is too slow; it lacks placeholder bits | S17, S18 |
| W3C WAI older users | Needs of ageing users mapped to WCAG | Borrow as E6's baseline | S25, S26 |
| LoC personal archiving (secondary) | Identify, select, keep copies apart, check yearly | Borrow as interview prompts | S31 |
| Marshall; Kaye et al.; Odom et al.; Grinter et al.; Poole et al.; Kiesler et al. ("warm expert") | Named in PLAN | **Not read** (blocked); needed before personas are finalised | — |

### Tools and libraries

| Name | Purpose | Licence | Maturity | Source |
|---|---|---|---|---|
| Rust std (`read_dir`, `MetadataExt`) | Walker with placeholder bits | MIT/Apache-2.0 | Rust 1.94.0 | S14 |
| `dua-core` 4.1.0 | Parallel traversal (fallback) | MIT | 2026-09-12; successor to jwalk | S17 |
| `jwalk` 0.9.0 | — | MIT | **Deprecated** 2026-08-05 | S16 |
| `infer` 0.22.0 | Magic-byte type (sparingly) | MIT | 2026-07-15 | S19 |
| `nom-exif` 3.8.0 | Capture month, camera model (images + video) | MIT | 2026-09-07 | S20 |
| `kamadak-exif` 0.6.1 | EXIF (images only) | BSD-2-Clause | 2024-11-06 | S21 |
| osxphotos 0.77.2 | M3 on a family Mac | MIT | 2026-09-27 | S22 |
| pymobiledevice3 11.19.4 | Not recommended (M6) | GPL-3.0-or-later | 2026-09-27 | S23 |
| ExifTool | Reference only (R8 LAB checks); not in the census | Not checked (blocked) | — | — |

## Spikes

Placeholder: a separate spike runner is producing these in parallel, and this note will be updated with their status.

| Spike | Exec tag | Budget IDs | Data class | Status | Result |
|---|---|---|---|---|---|
| E1-S1 Census script on 3 devices | CT build + FM run | BUD-SCAN (related; the "< 10 min" local threshold should go to H1's overlap table) | Rehearsal `PUB+SYN → results`; real `FAM → AGG` | (spike runner) | — |
| E1-S2 iOS-share gate (proposed split: S2a remote in Wave 1, S2b at the visit) | FM | none | `FAM → AGG` (family-wide share range only) | (spike runner: kit) | — |
| E1-S3 Interview pilot: owner vs neutral facilitator | FM | BUD-SUPPORT (owner time, indirectly) | `FAM → AGG` (story counts only) | (spike runner: kit) | — |

No emulator or simulator stands in for a family device. There are no results yet, and none are expected before the family runs.

## Conflicts with settled text

None new.
- E1-S2 feeds the existing OD-01 conflict (CLAUDE.md "Platforms (v1)" vs ADR-0002 §4) and does not resolve it.
- Choosing M4 (an iOS census app) would touch ADR-0002 §5 ("no OS code signing for now") through the Apple Developer Program. This note recommends against M4 for that reason.
- **PLAN** (not settled text) names `jwalk` and Google Forms; §3 and §5.3 explain why both should change. These are flagged to H1, and PLAN is not edited.

## Open questions

| Question | Who | By when |
|---|---|---|
| Exact current wording and meaning of iPhone Storage > Photos and iCloud > Storage > Photos under Optimize; do they count Shared Library and Recently Deleted? | E1-S2a kit (owner on a real iPhone); H1 for blocked support.apple.com | Before the first E1-S2a call |
| Does osxphotos' `original_filesize` hold values for cloud-only assets? | M3 on the owner's Mac (OL) | Before S2b uses M3 |
| Does sniffing or opening a Windows or macOS placeholder in the census path actually trigger hydration (C10)? | E1-S1 on a test OneDrive / iCloud Drive (H3 owner action 6) | During E1-S1 |
| Google One / Google Photos storage screens: do they separate Photos bytes, and do they show original vs Storage saver? | E1-S2a kit; H1 (support.google.com blocked) | Before E1-S2a |
| Visit length acceptable to older relatives (unmeasured; E2 owns the plan) | E2 with E1-S3 | Week 3 pilot visit |
| The HCI papers and practitioner sources named in PLAN | Papers scout, or the owner from an unblocked machine | Before personas are finalised (week 8) |
| Apple's iOS 27 device-compatibility list (maps family iPhones to `dataSize` and background-upload eligibility) | H1 (blocked source) / B4 | Before ADR-0004 |

## Recommendation

1. **Split E1-S2.** Run a remote quick count (S2a) in Wave 1 so OD-01 gets evidence on time, and confirm it at the visit (S2b). Use the library-level definition and the low–high decision rule (§2). Do not build an iOS census app for this: it needs the spend OD-01 decides, and `dataSize` exists only from iOS 27 (C1–C3).
2. **Keep one consolidated home visit per relative.** It contains the semi-structured, past-behaviour interview, the device walk-through, the desktop census and E2/E5's observed tasks. The owner runs it by default, and E1-S3 tests a neutral facilitator on 2–3 relatives.
3. **Build the census script on std** with placeholder detection first and extension-first classification. Drop `jwalk`. Use `nom-exif` for month and model histograms. Output H3 §7.6 CSVs, and show them before anything is sent.
4. **No third-party form services for family answers.** Use paper, the private store, or a homelab-hosted form.
5. **Do not run the census on managed work or school devices.** Record by self-report only whether they hold keepsakes.

**What would change this:**
- If Apple Support confirms that the Settings figures do not reflect library originals, M1/M2 weaken and M3 becomes necessary where a Mac exists.
- If the owner accepts the Apple Developer Program early (OD-01 or OD-09), M4 becomes cheap on iOS 27 devices.
- If the visits can be moved into Wave 1, S2a is unnecessary.

## Decision requests

These are proposals for H1 to file. The shared queue is not edited here.

### Proposed: E1-S2 timing and method for OD-01
- **Needed by:** Wave 1 week 1, so that S2a can run before OD-01 sitting 2.
- **Evidence:** this note §2; `b4-ios-decision.md`.
- **Options:**

  | Option | What it means for the family | Cost (money and owner time) | Reversibility | Risks |
  |---|---|---|---|---|
  | A. S2a remote quick count in Wave 1, S2b at the visit (recommended) | One 10–15 min call per library owner, reading Settings | About 15 min per person of owner time; no spend | Easy | Settings wording unverified; a straddled range may leave OD-01 provisional |
  | B. Wait for the visits (weeks 3–7) | No extra contact | None extra | Easy | OD-01 slips past Wave 1 exit, or is decided on the Q-F3 guess |
  | C. Decide OD-01 on the owner's guess (Q-F3) only | None | None | Easy (B4's option B is reversible) | Wrong if the guess is off; no evidence behind the gate |
- **Recommendation:** A. It gives real evidence in time, at small cost, with no installs.
- **Touches settled text:** none. It is evidence for OD-01, which already does.
- **If no decision by the deadline:** B4's default applies (iOS deferred, not precluded), and the gate is re-checked when S2b lands.

### Proposed: family-answer tooling and managed devices
- **Needed by:** before the first visit (week 3).
- **Options:**
  - (A) paper, the private store or a homelab form, and no census on managed devices (recommended);
  - (B) Google Forms and running the census everywhere.
- **Recommendation:** A. Google Forms breaks H3 §1, and running tools on an employer's device risks policy breaches and blocked runs.
- **Touches settled text:** none.

### Proposed: neutral facilitator (with H5 L27, Q-F9)
- **Options:**
  - (A) owner-run with E1-S3 on 2–3 relatives (recommended);
  - (B) facilitator for all visits;
  - (C) owner only, with the bias recorded.
- **Recommendation:** A.
- **Touches settled text:** none.

## Hand-offs

| To | What | Why |
|---|---|---|
| B4 / OD-01 | The S2a/S2b split, the metric definition and the range rule (§2); `dataSize` is iOS 27+ and nullable (C1) | The gate input and its timing |
| E2 | The §7 schedule and the visit contents; visit-length question | E2 owns the consolidated test plan |
| H3 | Google Forms conflict; per-person suppression for small families (§2.5); census field list (§4) for the output check | Data governance |
| E6 | WAI baseline and dated priors (C14); Assistive Access and font-scale fields (C15, C16) | ADR-0039 |
| B5 / B1 | Placeholder bits via std (C9); `jwalk` deprecated (C11); sniffing hydrates (C10) | The source layer and the scanner face the same issues |
| B2 | MediaStore aggregate fields (C7); partial access (C8); work profiles (C17) | Android census variant and the product scanner |
| C4 | Growth from capture-month histograms and from S2a→S2b readings | Capacity model |
| G2 | Device and OS fields in §4 | Device matrix |
| H1 | Blocked sources (Method); PLAN names `jwalk` and Google Forms; add E1-S1's "< 10 min" to the budget overlap table | Run rules §5.4; budgets |
