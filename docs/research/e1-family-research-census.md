# E1. Family research and census

- **Workstream:** E1 (see `docs/research/PLAN.md`, section "E1.")
- **Status:** Final for Wave 1 (after three-skeptic review). No family data exists yet; the
  family-dependent parts finish after the visits (Wave 2).
- **Date:** 2026-09-29 (last updated 2026-10-06)
- **Feeds:** OD-01 (through E1-S2), ADR-0004 (v1 scope; E2 + B4), ADR-0039 (accessibility and
  localisation; E6), ADR-0023 (discovery; E4), OD-12 and OD-17 (attitude themes), C4 (growth per
  person), G2 (device matrix), B1/B2 (support policy), A7-S3, H3 (consent script and census output
  format).
- **Depends on:** H2 (owner intake: Q-F1 to Q-F11, Q-G1 to Q-G6, Q-J5), H3 (data classes, output
  check, consent script; draft until OD-21), B4 (the OD-01 gate definition), E2 (consolidated visit
  plan; E2-S3 interim stopgaps for the debrief).
- **Owns (PLAN §2.1 / E1):** the research protocol and consent script (with H3), the single
  aggregate-only census script, the anonymised summary, proto-personas, journeys and the iOS-share
  memo. E1 owns **no ADR**.
- **Traceability rows closed or advanced:** R-03 (advanced: E1-S2 method, timing and decision
  rule), R-06 (advanced: protocol, and what must be observed rather than asked).

## Summary

- **Without the family, we can know** the platform facts, the measurement methods and their blind
  spots. This note settles those (§1). **Only the family can tell us** the numbers and behaviours
  that drive decisions: the iPhone share of camera-roll bytes, library sizes and growth, where
  keepsakes live, beliefs about backup, comfort with technology, languages and accessibility needs.
  No public source can stand in for them (K15, secondary-only).
- **E1-S2 and OD-01 timing.** OD-01 is due at Wave 1 exit; the visits are in weeks 3–7 (K6,
  verified). The Wave 1 exit rule allows OD-01 to be "decided **or scheduled**", so waiting is
  allowed by the plan. A remote quick count (**E1-S2a**) would let OD-01 be *decided* at Wave 1
  exit, and would start the Apple long-lead item early if the result escalates. **E1-S2a is now
  conditional.** It relies on Settings screens whose meaning is unverified (K5, contested by all
  three skeptics), so it runs only after the owner has checked those screens on his own phones
  (kit Part 0). If that check fails, OD-01 is scheduled for after the visits (**E1-S2b**).
- **The gate is judged on a low–high estimate, widened after review.** Apple libraries now get a
  range too: iCloud may be full and paused, and Mac imports may inflate the figure. Android
  libraries with Storage-saver, pre-2021 or Pixel 1–5 history get no upper bound unless one is
  measured, and a missing reading gives "INCOMPLETE" rather than a verdict. The calculator can
  therefore no longer escalate OD-01 on readings that undercount Android. A per-person "iPhone
  user with no computer" count is reported alongside the bytes.
- **No iOS census app.** The reason was corrected after review. Cost was not the deciding factor:
  a free Personal Team could install a one-off app (K3, contested). The reasons are that the only
  documented size API is iOS 27+ and can be `nil` (K1, verified), that earlier versions have only
  undocumented keys (K2, verified), that installing would put elderly-hostile steps on relatives'
  phones, and that it would need Apple code signing, which settled text excludes for now.
- **Census script:** a std-based walker that reads placeholder bits from enumeration data, never
  opens a placeholder and classifies by extension first. The PLAN's `jwalk` is deprecated (K9), and
  sniffing reads file data, which on Windows is documented to fetch placeholder content (K7, K8;
  all verified). The CT spike passed on synthetic data with emulated placeholders. Real
  Windows/macOS runs, timings and two code fixes are gates in the kit.
- **Blocked:** the HCI papers named in PLAN, NN/g, Pew, LoC, and every Apple, Google and Microsoft
  *support* page. Findings that rest on them are marked secondary-only.

## Questions

| # | Question (PLAN E1 key questions, plus new ones) | Short answer | Confidence |
|---|---|---|---|
| 1 | Per person: devices, OS versions, storage, camera-roll size and monthly growth, placeholders | Unknown until the census. §3–§4 say what each platform exposes without reading content and what it cannot see. Growth comes from capture-month histograms (desktop census, M3, A2). Two Settings readings weeks apart are a sanity check only (§2.4). | High on method; no data |
| 2 | Share of camera-roll bytes on iPhones and iPads (E1-S2) | Unknown. Proposed metric: original bytes per camera **library**, counted once (a proposal to B4 and the owner, §2.1). Read without installs where Part 0 confirms the screens (§2.2). Judge the 40 % gate on a widened low–high estimate with an INCOMPLETE state (§2.3), plus a per-person bridge indicator (§2.5). | High that it is unknown; Medium on the method (K5 contested) |
| 3 | Chromebooks, shared computers, managed work or school devices | Census questions plus the script's known blind spots (§3, §1). Do **not** run the census on managed devices; record only by self-report whether they hold keepsakes. | Medium |
| 4 | Where keepsakes live; past losses; what would hurt most | Interview only (§5). On desktops, the census finds candidate locations, which serves the E1-S1 "unmentioned location" criterion. | High that only the family can answer |
| 5 | What people believe is backed up; paid cloud storage | Ask, then **check together** on the device. Record belief and reality separately, then debrief (§5.4). | Medium |
| 6 | Comfort with technology; accounts; app install, QR scan, 12-character code; notification habits | Observe these as E2/E5 tasks in the same visit. Self-report is only for screening. | Medium (method judgement) |
| 7 | Feelings about the admin seeing everything; exclusions | Ask in the interview, after a read-out that covers both admin access and keep-forever retention (§5.1). Report as counts and themes to OD-12/OD-17. | Medium |
| 8 | Languages; vision, motor, hearing and cognitive needs | Census records OS settings plus self-report. WAI priors are dated, mixed-country and web-scoped (§6, K12). | Medium |
| 9 | Research ethics: owner as researcher; neutral facilitator? | Owner-run by default from a written protocol. E1-S3 compares a facilitator on 2–3 relatives. Minors follow H3 §9. A debrief protects participants after collection (§5.4). | Medium |
| 10 | (new) Can E1-S2 inform OD-01 at Wave 1 exit? | Only through S2a, and only if Part 0 confirms the screens. Otherwise OD-01 is scheduled after S2b, which the plan allows (K6). | High on timing; Medium on S2a feasibility |
| 11 | (new) Is PLAN's census toolchain right? | No. `jwalk` is deprecated (K9), sniffing placeholders fetches data (K8), and Google Forms conflicts with H3 §1 once OD-21 confirms it (K14). | High |
| 12 | (new) What can and cannot be known without the family? | §1 | High |

## Method

- **Sweep:** two scouts (docs; source). No issues/forums scout and no papers scout ran for E1 in
  Wave 1.
- **Analyst re-reads (2026-09-29):** Apple DocC JSON (`PHAssetResource.dataSize`,
  `PHAuthorizationStatus.limited`, `ubiquitousItemDownloadingStatusKey`, Assistive Access);
  developer.android.com `MediaStore.MediaColumns` and the Android 14 partial-access page; the crate
  tarballs of `jwalk` 0.9.0, `dua-core` 4.1.0 and `infer` 0.22.0; the sdists of osxphotos 0.77.2 and
  pymobiledevice3 11.19.4; photo_manager 3.12.0; W3C WAI older-users pages via the
  `w3c/wai-website` git mirror.
- **Skeptic review (2026-10-06):** three skeptics (sources, logic, adversary/non-technical user)
  re-fetched the primary sources. Their additions:
  - Apple's developer-account help page (Personal Team limits);
  - the Android 15 features page (Private space);
  - the Rust 1.94.0 `sys/fs/windows.rs` source;
  - the crates.io API record for `jwalk`.
  The claim verdicts below are the computed tally: **verified** = has a primary source, and at
  least 2 of 3 skeptics did not refute it.
- **Routes used:** direct HTTPS to developer.apple.com DocC JSON and developer.android.com;
  raw.githubusercontent.com (MicrosoftDocs/win32, rust-lang/rust, apple-oss-distributions/xnu,
  w3c/wai-website); static.crates.io; PyPI; pub.dev; WebSearch snippets where pages were blocked
  (labelled secondary).
- **Blocked sources (reported to H1; none silently replaced):**
  - support.apple.com (108782, 105061, 102670, 108429, 108922), still blocked on 2026-10-06
    (curl 403 and WebFetch EGRESS_BLOCKED);
  - support.google.com (Photos "Free up space"; Google One storage); blog.google (the 2021 storage
    change);
  - support.microsoft.com (OneDrive Files On-Demand);
  - digitalpreservation.gov / loc.gov, archives.gov, pewresearch.org, gs.statcounter.com,
    limesurvey.org, exiftool.org, metacpan;
  - www.nngroup.com, dl.acm.org, arxiv.org, api.crossref.org, api.openalex.org, semanticscholar.org,
    en.wikipedia.org;
  - www.w3.org was read through its git mirror (the same primary source).
- **Stop rule:** the skeptics' re-fetches added three primary sources (the Apple account help page,
  the Android 15 features page and the Rust Windows `fs` source). They changed three verdicts and
  the M4 rationale, but no other fact. The HCI papers (Marshall, Kaye et al., Odom et al., Grinter
  et al., Poole et al., Kiesler et al.), *The Mom Test* and Krug were **not read**. Points that
  lean on them are secondary-only.

## Sources

| # | Source | Publisher | Published or version date | Accessed | Primary? |
|---|---|---|---|---|---|
| S1 | `PHAssetResource.dataSize` — https://developer.apple.com/documentation/photos/phassetresource/datasize-5lxva (DocC JSON `…/tutorials/data/documentation/photos/phassetresource/datasize-5lxva.json`; ObjC `datasize-6cf5k`) | Apple | introducedAt 27.0 (iOS, iPadOS, macOS, Mac Catalyst, tvOS, visionOS), not beta | 2026-09-29; 2026-10-06 (skeptics) | Yes |
| S2 | `PHAssetResource` topic list — https://developer.apple.com/documentation/photos/phassetresource | Apple | iOS 9.0+ | 2026-10-06 | Yes |
| S3 | `PHAssetResourceManager` — https://developer.apple.com/documentation/photos/phassetresourcemanager | Apple | iOS 9.0+ | 2026-09-29 | Yes |
| S4 | `PHAuthorizationStatus.limited` — https://developer.apple.com/documentation/photos/phauthorizationstatus/limited | Apple | iOS 14.0+ | 2026-09-29 | Yes |
| S6 | Assistive Access — https://developer.apple.com/documentation/accessibility/assistive-access | Apple | Undated | 2026-09-29; 2026-10-06 | Yes |
| S7 | `UISupportsFullScreenInAssistiveAccess` — https://developer.apple.com/documentation/bundleresources/information-property-list/uisupportsfullscreeninassistiveaccess | Apple | iOS 17.0+ | 2026-09-29 | Yes |
| S9 | `MediaStore.MediaColumns` — https://developer.android.com/reference/android/provider/MediaStore.MediaColumns | Google | Last updated 2026-08-03 | 2026-09-29; 2026-10-06 | Yes |
| S10 | Partial photo and video access (Android 14) — https://developer.android.com/about/versions/14/changes/partial-photo-video-access | Google | Last updated 2026-03-03 | 2026-09-29; 2026-10-06 | Yes |
| S11 | Android 14 features — https://developer.android.com/about/versions/14/features | Google | Last updated 2026-09-16 | 2026-09-29 | Yes |
| S12 | Work profiles — https://developer.android.com/work/managed-profiles | Google | Last updated 2025-02-10 | 2026-09-29; 2026-10-06 | Yes |
| S13 | File Attribute Constants — `MicrosoftDocs/win32 @ docs : desktop-src/FileIO/file-attribute-constants.md` | Microsoft | ms.date 2025-09-23 | 2026-09-29; 2026-10-06 | Yes |
| S14 | Rust std 1.94.0 — `rust-lang/rust @ 1.94.0 : library/std/src/fs.rs`, `os/windows/fs.rs`, `os/darwin/fs.rs`, `sys/fs/windows.rs` | Rust project | Tag 1.94.0 | 2026-09-29; 2026-10-06 | Yes |
| S15 | XNU `bsd/sys/stat.h` (`SF_DATALESS`) — `apple-oss-distributions/xnu @ main` | Apple | main | 2026-09-29; 2026-10-06 | Yes |
| S16 | `jwalk` 0.9.0 crate — https://static.crates.io/crates/jwalk/jwalk-0.9.0.crate; crates.io API | jwalk authors | 2026-08-05T03:19:24Z | 2026-09-29; 2026-10-06 | Yes |
| S17 | `dua-core` 4.1.0 crate — https://static.crates.io/crates/dua-core/dua-core-4.1.0.crate | Byron/dua-cli | CHANGELOG 4.1.0 dated 2026-09-12 | 2026-09-29; 2026-10-06 | Yes |
| S19 | `infer` 0.22.0 crate — https://static.crates.io/crates/infer/infer-0.22.0.crate (`src/lib.rs` l. 251–263) | infer authors | 0.22.0 | 2026-09-29; 2026-10-06 | Yes |
| S20 | `nom-exif` 3.8.0 crate — https://static.crates.io/crates/nom-exif/nom-exif-3.8.0.crate | nom-exif author | 2026-09-07 | 2026-09-29 | Yes |
| S21 | `kamadak-exif` 0.6.1 crate | kamadak | 2024-11-06 | 2026-09-29 | Yes |
| S22 | osxphotos 0.77.2 sdist — https://files.pythonhosted.org/packages/20/57/44770b159a8a3b719083d06a52709fa5851c98dc0a7c4cf8c7c1e36f6d88/osxphotos-0.77.2.tar.gz | R. Taylor | Uploaded 2026-09-27 (current on 2026-10-06) | 2026-09-29; 2026-10-06 | Yes (code) |
| S23 | pymobiledevice3 11.19.4 sdist | doronz88 et al. | Uploaded 2026-09-27 | 2026-09-29 | Yes (code) |
| S24 | Flutter photo_manager 3.12.0 — https://pub.dev/api/archives/photo_manager-3.12.0.tar.gz (`PMManager.m` l. 269, 2541) | fluttercandies | Published 2026-08-09 | 2026-09-29; 2026-10-06 | Yes (code) |
| S25 | W3C WAI "Older Users and Web Accessibility" — https://www.w3.org/WAI/older-users/ via `w3c/wai-website @ 06dcdd1 : pages/fundamentals/people/older-users/index.md` | W3C WAI | last_updated 2025-11-20; first published 2010 | 2026-09-29; 2026-10-06 | Yes (mirror) |
| S26 | W3C WAI literature review — https://www.w3.org/WAI/older-users/literature/ via the same mirror, `literature.md` | W3C WAI | last_updated 2018-02-22; review conducted 2008, "We do not currently plan to update it" | 2026-09-29; 2026-10-06 | Yes |
| S27 | Apple Support 108782, 105061 (iCloud Photos; Optimize) | Apple | Unknown | Snippets only (blocked) | Primary, **unread** |
| S28 | Apple Support 108429, 108922 (iPhone storage; iCloud storage) | Apple | Unknown | Snippets only (blocked) | Primary, **unread** |
| S29 | Google Photos Help 6128843 "Free up space"; Google One Help 9312312 | Google | Unknown | Snippets only (blocked) | Primary, **unread** |
| S30 | Microsoft Support, OneDrive Files On-Demand | Microsoft | Unknown | Snippets only (blocked) | Primary, **unread** |
| S31 | Library of Congress, Personal Archiving: Digital Photos — https://digitalpreservation.gov/personalarchiving/photos.html | LoC | Unknown | Snippets only (blocked) | Primary, **unread** |
| S32 | Pew Research Center short read 2026-01-08 — https://www.pewresearch.org/short-reads/2026/01/08/internet-use-smartphone-ownership-digital-divides-in-u-s/ | Pew | 2026-01-08 | Third-party citations only (blocked) | Primary, **unread** |
| S33 | Project documents: `PLAN.md` (E1, §2.1, §4.1, §4.3), `decision-queue.md`, `h3-research-data-governance.md`, `b4-ios-decision.md` (K7, K10, IOS-C6), `h5-long-lead-items.md` (L26, L27), `budgets.md` | Reliquary | 2026-09-29 | 2026-09-29; 2026-10-06 | Yes (project) |
| S34 | Apple Developer account help, "About your developer account" — https://developer.apple.com/help/account/basics/about-your-developer-account (compare-memberships redirects here) | Apple | Undated | 2026-10-06 (skeptic 1) | Yes |
| S35 | Android 15 features (Private space) — https://developer.android.com/about/versions/15/features | Google | Last updated 2026-10-01 | 2026-10-06 (skeptic 1) | Yes |
| S36 | Google "storage changes" blog (2021 Google Photos quota change) and press coverage | Google; press | 2020–2021 | Snippets only (blog.google blocked) | Primary unread; **secondary only** |

(S5, S8 and S18 from the draft support only non-key context and are kept in the draft's history;
they are not cited below.)

## Claims

Verdicts are the **computed tally** from the three skeptics (sources, logic, adversary). "Upheld"
means the skeptic did not refute the claim. Caveats the skeptics raised are folded into the
findings.

| # | Claim | Sources | Key? | Skeptic 1 (sources) | Skeptic 2 (logic) | Skeptic 3 (adversary/user) | Verdict |
|---|---|---|---|---|---|---|---|
| K1 | `PHAssetResource.dataSize` ("the size of the resource in bytes") is introduced only in iOS/iPadOS 27.0, and `nil` means the size is unknown, not zero. | S1 | Yes | Upheld (re-fetched both symbols) | Upheld. Its use to "rule out" a pre-27 app overreaches. | Upheld | **Verified** |
| K2 | Before iOS 27, no documented public byte-size property exists on `PHAssetResource`. photo_manager 3.12.0 reads size and local availability through the undocumented KVC keys `fileSize` and `locallyAvailable`. | S2, S3, S24 | Yes | Upheld (topic list) | Upheld. "App Review risk" does not apply to a one-off research build. | Upheld (stronger than "not exhaustive") | **Verified** |
| K3 | Any app on relatives' iPhones needs the paid Apple Developer Program, so an iOS census app presupposes the spend OD-01 decides. | S33 (B4 K10), S34 | Yes | **Refuted.** A free Personal Team (3 devices, 7 days) suffices for a one-shot app at a visit. | **Refuted.** "Any app" is overbroad; the circularity fails for S2b. | Upheld, but says it overstates | **Contested.** The note no longer relies on it (§2.2). |
| K4 | With iCloud Photos + Optimize, originals live in iCloud and the device keeps smaller copies, so the device's Photos figure understates library bytes. | S27 (snippets) | Yes | **Refuted** (primary blocked; secondary only). "Optimize is on by default" is contradicted by a snippet. | **Refuted** (secondary only) | Upheld (Apple's own snippets agree) | **Contested** (secondary only in substance). The range rule no longer depends on its direction. |
| K5 | The iCloud Storage > Photos and iPhone Storage > Photos screens give usable per-library byte figures without installing anything. | S28 (snippets) | Yes | **Refuted** (unverified; unknown semantics) | **Refuted.** Undercounts when iCloud is full; overcounts with Mac imports. | **Refuted.** Also unreachable under Assistive Access. | **Contested.** S2a is gated on kit Part 0 (§2.4). |
| K6 | E1-S2 via the visits cannot inform OD-01 at Wave 1 exit; visits are weeks 3–7. | S33 | Yes | Upheld. Exit allows "decided or scheduled"; L26 has a fallback. | Upheld, same nuance | Upheld, same nuance | **Verified.** Re-scoped: S2a lets OD-01 be *decided*, not just scheduled. |
| K7 | Windows placeholder bits (RECALL_ON_DATA_ACCESS 0x00400000, RECALL_ON_OPEN 0x00040000, OFFLINE, PINNED/UNPINNED) are readable during enumeration via Rust std `file_attributes()` with no extra system call; macOS `SF_DATALESS` (0x40000000) via `st_flags()`. | S13, S14, S15 | Yes | Upheld. Caveat: 0x00040000 = FILE_ATTRIBUTE_EA too. | Upheld. Caveats: directory population; pre-Sonoma `.icloud` stubs. | Upheld. Never run on Windows or macOS. | **Verified** |
| K8 | `infer` 0.22.0 `get_from_path` opens the file and reads up to 8,192 bytes; sniffing a placeholder fetches data. | S19, S13 | Yes | Upheld. Windows fetch is **documented** by Microsoft, not just inferred. | Upheld | Upheld. Whole-file vs partial is untested. | **Verified** |
| K9 | `jwalk` 0.9.0 (2026-08-05) is deprecated ("Use dua-core instead"); `dua-core` 4.1.0 exposes no Windows attribute bits or macOS `st_flags`. | S16, S17 | Yes | Upheld | Upheld. `allocated_size == 0` is a possible heuristic. | Upheld | **Verified** |
| K10 | MediaStore exposes `_size`, `RELATIVE_PATH`, `VOLUME_NAME`, `DATE_TAKEN`, `IS_PENDING`, `IS_TRASHED`, `GENERATION_ADDED`, enough for an aggregate census without reading content. It cannot see items removed by "Free up space", work-profile media, or media outside a limited-access grant. | S9, S10, S12, S29 | Yes | Upheld. "Free up space" part secondary; Private space missing. | Upheld. `.nomedia` folders not indexed. | Upheld. Partial access also hits SDK 33 apps. | **Verified** (MediaStore part); the invisible-store list is extended in §1 |
| K11 | osxphotos exposes `original_filesize` (`ZORIGINALFILESIZE`) and `ismissing`; whether the size is filled for cloud-only assets is unverified. | S22 | Yes | Upheld | Upheld. Live Photo halves and edits may bias M3 low. | Upheld | **Verified** |
| K12 | W3C WAI says its standards "address most older user needs"; its prevalence figures come from a 2008 review (page updated 2018). | S25, S26 | Yes (E6 priors) | Upheld. Web-scoped; vision figures are UK estimates. | Upheld, same | Upheld, same | **Verified** (scope caveats in §6) |
| K13 | Assistive Access is set up by a "trusted supporter" (family member or caregiver) who chooses the apps. | S6 | Yes | Upheld | Upheld. iOS only; Android simple modes not covered. | Upheld. Settings may be unreachable for S2a. | **Verified** |
| K14 | Google Forms, which PLAN names, would send family answers to a third party, contrary to H3 §1. | S33 (H3 §1; PLAN E1) | Yes | Upheld | Upheld. H3 is a draft until OD-21. | Upheld | **Verified** (binding once OD-21 confirms H3) |
| K15 | No public, vendor or survey source gives a particular family's iOS vs Android split of camera-roll bytes; population priors (Pew 78 % of 65+ own a smartphone) cannot substitute for E1-S2. | Analysis; S32 (unread) | Yes | Upheld (analytic). Pew figure secondary only. | Upheld | Upheld. Nothing depends on the Pew figure. | **Secondary only** |

Non-key supporting claims (not separately tallied; their status is from the sources alone):

| # | Claim | Sources | Status |
|---|---|---|---|
| N1 | Android 14 supports nonlinear font scaling up to 200 %. | S11 | Primary, not tallied |
| N2 | Android work profiles are IT-admin controlled with "separate storage areas". Android 15 Private space "uses a separate user profile" with separated media. | S12, S35 | Primary, not tallied (checked by skeptic 1 under K10) |
| N3 | High-quality uploads made before 2021-06-01, and Pixel 1–5 uploads, do not count toward Google storage quota. Storage-saver copies are re-encoded. | S36 | **Secondary only** |
| N4 | pymobiledevice3 AFC lists `DCIM` over USB but returns filenames; rejected method. | S23 | Primary, not tallied |

## Findings

### 1. What can and cannot be known without the family

| Topic | Knowable now (desk and container) | Only from the family | Confidence |
|---|---|---|---|
| iPhone share of camera-roll bytes | How to define and measure it, and its error sources (§2) | The number (K15) | High |
| Library sizes, growth, file types | What each platform exposes without reading content (K7, K10, K11) | Sizes, growth, mix (feeds H3 §7.6, C4, A7-S3) | High |
| Placeholders (iCloud Optimize, Google "Free up space", OneDrive) | That they exist and how to detect each on desktops (K7, K8) | Who uses which setting; cloud-only bytes | High on desktop detection; Medium on phone behaviour (K4 contested) |
| Hidden stores | The census cannot see: Android work profiles and **Private space** (N2); Samsung Secure Folder (PLAN E3); Google Photos Locked Folder (PLAN B2); media outside a limited-access grant (K10); `.nomedia` folders (MediaStore does not index them); other users' profiles on shared PCs (expected, not tested); macOS folders refused at a privacy prompt; keepsakes inside messaging apps and email | Whether any of these hold keepsakes (self-report, device checklist D16) | Medium |
| Where keepsakes live, past losses, what hurts | Generic prompts (LoC, secondary) | Everything specific | High |
| Beliefs about backup; paid storage | That Google accounts share one quota (secondary, S29) | Beliefs, and the gap between belief and reality | Medium |
| Comfort with technology, QR scanning, code typing | Nothing useful | Observed performance (E2/E5 tasks) | High |
| Attitudes to admin access and exclusions | Nothing | Everything | High |
| Languages; accessibility | Dated, web-scoped priors (K12); platform modes to record (K13, N1) | Actual needs and settings | Medium |
| Managed devices | Work profiles have separate storage (N2); WDAC/EDR may block tools (PLAN B1) | Whether they exist and hold keepsakes | Medium |
| Who has a computer for a desktop bridge | Nothing | Per person: main camera platform and computer access (§2.5) | High that only the family can answer |

### 2. E1-S2: the iPhone share gate

**2.1 The metric (a proposal to B4 and the owner; E1 does not own the gate).** "Share of
camera-roll bytes on iPhones or iPads" is ambiguous in three ways. E1 proposes:

1. **Library bytes, not on-device bytes.** An iOS client would have to protect originals (B4
   K7, IOS-C6). The right quantity is original bytes in the library, cloud-only ones included.
2. **Each library once.** An iPhone, an iPad and a Mac on one Apple ID share one iCloud library.
   It counts as "Apple" when its main capture device is an iPhone or iPad.
3. **Denominator:** phone and tablet camera libraries only. Desktop-only archives (camera cards,
   scans) are excluded; they are A9's import seed. Where such archives were imported into an
   iCloud library, the Apple figure overstates. §2.3 handles this with the `mixed` flag.

> share = Σ original bytes of Apple camera libraries ÷ Σ original bytes of all phone/tablet
> camera libraries, each library counted once.

PLAN's 40 % threshold is unchanged. If B4 or the owner prefers PLAN's looser wording, the kit
still works; only the definitions section changes.

**2.2 Measurement options**

| # | Method | Measures | Error sources | Verdict |
|---|---|---|---|---|
| M1 | iCloud > Storage > **Photos** (iCloud Photos on) | Bytes stored in iCloud | Wording and meaning unverified (K5, contested). Undercounts if iCloud is full or uploads are paused. Overcounts with Mac/PC imports, Recently Deleted, possibly Shared Library. | Use, **only after Part 0**, always together with M2 |
| M2 | General > iPhone Storage > **Photos** | On-device bytes | Unverified (K5). Optimized copies are smaller (K4, contested). | Use for every iOS library |
| M3 | osxphotos aggregate on a family Mac holding the library | Original bytes by camera make | Size may be empty for cloud-only assets (K11). Live Photo halves and edits may be missed (biases low). Needs a Mac. | S2b cross-check for straddles and `mixed` libraries |
| M4 | One-off iOS 27+ census app using `dataSize` (free Personal Team, cable install at the visit) | Per-resource bytes | iOS 27 only, `nil` sizes (K1); needs full library access (K10/S4); needs a Mac with Xcode, Developer Mode on the relative's phone and a trusted developer profile (steps unverified for current iOS, hostile to elderly users); a `requestData` fallback would download originals; **it is Apple code signing, which CLAUDE.md and ADR-0002 §5 exclude "for now"** | **Not used.** It would need an owner exception for a research-only build. Cost is not the reason (K3 contested). |
| M5 | App reading private `fileSize`/`locallyAvailable` keys (K2) | Bytes, local vs cloud | Undocumented and fragile, plus all M4 costs | Not used |
| M6 | USB + pymobiledevice3 AFC (N4) | Local camera files | Returns filenames; likely misses cloud-only originals; GPL | Not used |
| M7 | iOS Shortcuts photo actions (preinstalled) | Unknown | Unverified whether any action gives sizes without downloading originals | Open question; not used |
| A1 | Android: Settings > Storage Images + Videos **and** the Google Photos/Google One "Photos" figure | Local bytes; cloud quota bytes | Quota is not library bytes. Storage saver is re-encoded, and pre-2021 High quality and Pixel 1–5 uploads may not count (N3, secondary). Device figure includes screenshots and messaging media. Labels vary by maker. | Use, with flags (§2.3) |
| A2 | Android MediaStore aggregate app (K10) | Local originals by folder and month | Misses freed items, Private space, limited grants, `.nomedia` | S2b, only if B2 has a build; gives a bound for flagged libraries |
| X1 | Item counts at the bottom of Photos / Google Photos × typical sizes from the owner's own library | Order-of-magnitude check | Crude; typical sizes vary by device and video share | Cross-check, and a possible `bound_gb` |
| X2 | Family-plan organiser screens (iCloud+ / Google One family) | Per-member usage, perhaps | Unverified; may mix mail and drive | Check in Part 0 step 5b |

**2.3 Decision rule (revised).** For each library the owner records a low and a high figure,
plus flags (kit `share_range.py`):

| Library | Low | High |
|---|---|---|
| Apple, iCloud Photos off | M2 | M2 |
| Apple, iCloud Photos on or unsure | max(M1, M2) | M1 + M2 (covers paused uploads) |
| Apple with `mixed` (imports, scans or Shared Library) | an independent bound (M3, X1) if given, else **unknown** | as above |
| Android, backup off | device | device |
| Android, backup on or unsure | max(device, cloud) | device + cloud |
| Android with `saver`, `pre2021`, `pixel` or `shared_total` | as above | an independent bound (A2, X1) if given, else **unbounded** |
| Any required reading blank | — | — (**INCOMPLETE**: no verdict) |

Then share_low = A_low ÷ (A_low + D_high) and share_high = A_high ÷ (A_high + D_low):

- **Escalate OD-01** only if share_low is known and ≥ 40 %.
- **Do not escalate** if share_high < 40 %.
- **Straddle** otherwise. This includes "share_low unknown" when flagged libraries have no bound.
  Then run M3/A2/X1 for those libraries at the earliest visit, or the owner decides with the range
  shown.

This answers the three skeptics' major issue. A missing or quota-distorted Android figure can no
longer narrow the range and produce a false "escalate". The Apple side is no longer ±0. The cost
is more straddles, and so more S2b work. The low–high pair is an **estimate**, not a proven bound,
until Part 0 has checked the screens (K5). Tested only on synthetic inputs (Spikes).

**2.4 Timing and method (K6 re-scoped).** OD-01 is due at Wave 1 exit, where the criterion is
"decided or scheduled" (PLAN §4.1). The visits are in weeks 3–7 (H5 L26), and L26 already lists a
remote fallback (video-call interviews; a relative running the census from a printed guide). So:

- **E1-S2a (week 1), gated.** Prerequisites: OD-21 is confirmed (or the PLAN H3 minimum rules
  are applied), and the owner approves the phone consent text. Part 0 then checks the screens on
  the owner's own phones. Only then are readings taken, preferring the in-person set-ups listed
  below. The benefit: OD-01 can be *decided* at Wave 1 exit, and if it escalates, the Apple
  membership (a long-lead item, B4) starts several weeks earlier.
- **If Part 0 fails, or the result is INCOMPLETE or an unresolved straddle,** OD-01 is
  *scheduled* for after S2b. This is plan-compliant. Its cost is that ADR-0004's iOS section and
  the Apple long-lead item start later.
- **Call set-up (adversary review).** Reading Settings aloud on the same phone you are calling
  from is hard for older relatives. The kit now prefers, in order:
  1. in person (a gathering or a helper relative);
  2. a second line;
  3. an end-to-end encrypted screen share, never recorded (H3 to confirm acceptable services);
  4. the same phone on speaker.
  The call opens with "I will never ask for a password or code, or ask you to buy anything".
  This keeps the call from resembling a support scam, and it guards against tapping *Upgrade* by
  accident. Every number is read back with its unit (MB vs GB). Assistive Access users go
  through their supporter. "Could not navigate → S2b" is a recorded outcome. The "10–15 min" is
  an **estimate**; the first two calls are timed.
- **Growth.** Two Settings readings 2–6 weeks apart are rounded, and they move with deletions, so
  monthly growth may fall below their resolution. Growth comes from capture-month histograms
  (desktop census, M3, A2). The S2a→S2b difference is only a sanity check.

**2.5 A second indicator: people, not just bytes.** If share_high < 40 %, B4's default is "iOS
after the pilot, with a desktop-side bridge". A bridge only helps iPhone users who have a computer
someone can run it on. A byte share cannot reveal an older relative with an iPhone and no
computer. The kit therefore records, per person, the main capture platform and computer access
(own / with help / none). It reports family-wide counts with the H3 "<5" rule next to the share.
This does not change the 40 % rule. It is evidence for B4 and OD-01 (CLAUDE.md: phones are
first-class).

**2.6 Privacy.** Per-person library sizes identify people within a family of 10–25 devices. Only
family-wide figures enter AGG. Platform totals are withheld below 5 libraries (H3 §4).

### 3. E1-S1: census script design

1. **Walker: Rust std**, not `jwalk` (deprecated, K9). `dua-core` hides the attribute bits (K9);
   its `allocated_size == 0` heuristic or a per-entry `stat` is a fallback if std is too slow.
2. **Placeholders first, from enumeration data only.** On Windows, read `RECALL_ON_DATA_ACCESS`,
   `RECALL_ON_OPEN` and `OFFLINE` from `DirEntry::metadata` (FindFirstFileExW/FindNextFileW data;
   no extra system call, K7). Never use a path-based attribute call: `RECALL_ON_OPEN` has the same
   value as `FILE_ATTRIBUTE_EA` and is meaningful only from enumeration (S13). On macOS, read
   `SF_DATALESS` via `st_flags()` (an `lstat` per entry, no open). Placeholders are counted by
   extension as "cloud-only" and never opened. Sniffing would fetch data: Microsoft documents that
   reading a RECALL_ON_DATA_ACCESS file fetches content (K8). For macOS this is still untested.
3. **Known gaps to test in the kit (Part A):**
   - Enumerating a never-populated cloud folder may itself fetch the listing.
   - macOS before Sonoma may represent evicted iCloud Drive files as hidden `.<name>.icloud`
     stubs, not `SF_DATALESS`. This was stated by a reviewer from general knowledge and is
     unverified; a code fix is listed.
   - Placeholder "disguise" behaviour for an unpackaged exe is untested.
   - Google Drive and Dropbox, not only OneDrive.
4. **Classify by extension first; sniff only extensionless local files** (`infer` reads 8 KiB,
   K8). RAW and GEDCOM go by extension rules.
5. **Optional `--exif`** with `nom-exif` 3.8.0: month-level capture histograms and camera
   **models** only (H3 §4).
6. **Output** H3 §7.6 CSVs. **Show before saving, plain-words summary first.** The spike prints
   the summary after the table. In the SYN sample that is roughly 259 lines of CSV, which a
   relative cannot meaningfully review, so the kit requires a CT fix that puts the summary first.
   A printed copy is offered.
7. **Scope.** The census runs on Windows, macOS and Linux desktops. Android uses A2 if B2 has a
   build. There is **no iOS census app**. It never runs on managed devices. Unreadable areas
   (other profiles, refused macOS privacy prompts, the Photos library without Full Disk Access)
   are reported as known gaps, never worked around.

### 4. Census field list

The paper form is `docs/research/kits/E1-S1/device-checklist.md`. Changes since the draft:

- D16 records hidden spaces: Private space, Secure Folder, Locked Folder, work profile and other
  accounts.
- D17 records the macOS version, because of possible `.icloud` stubs.
- D13 adds Android simple modes and the Assistive Access supporter role.
- P14 is the bridge indicator (§2.5).
- P15 records debrief actions.

These are owner-only and not exported.

| Level | Field | How collected | Class after output check |
|---|---|---|---|
| Device | Type; OS and version; model (no serial); storage (binned) | Script or Settings | AGG |
| Device | Upgrade eligibility (iOS 26.1+/27, Windows 10/11, Android version) | Settings; vendor lists (Apple list blocked) | AGG |
| Device | Shared or personal; user accounts; managed; hidden spaces | Self-report and Settings | AGG |
| Device | Cloud services and settings (iCloud Photos/Optimize/Shared Library; Google Photos quality and "Free up space"; OneDrive) | Checked together | AGG |
| Device | Accessibility settings | Settings | AGG (family totals if sensitive) |
| Library | Bytes and counts per category × log2 bin; placeholder bytes; capture months (24) | Script, MediaStore, M1–M3 | AGG |
| Person | Languages; own email; accounts; pays for storage | Interview | AGG |
| Person | Belief vs check | Interview + check | AGG (mismatch counts) |
| Person | Keepsake places beyond devices | Interview prompts | AGG (counts per type) |
| Person | Helps / is helped by (roles) | Interview | AGG (graph by pseudonym) |
| Person | Main capture platform; computer access (bridge indicator) | Interview / S2a | AGG ("<5" rule) |

### 5. Interview protocol and methods

**5.1 Approach.** Semi-structured, past-behaviour interview inside the consolidated visit
(`kits/E1-S3/interview-guide.md`), then a device walk-through, the census and E2/E5's observed
tasks. The past-behaviour emphasis is the idea usually attributed to *The Mom Test*. The book was
not read, so the attribution is secondary. Attitude questions come after a read-out of the trust
model, which now includes the settled retention rule: "once something is saved at home it is kept;
deleting it from your phone does not remove it there; only [Owner] can". Exclusion preferences
(OD-12) depend on that, and non-technical users often assume that deleting something removes it
everywhere. This describes settled text accurately; it does not reopen it. The "Free up space"
question is now neutral: "makes room on the phone by keeping photos only in the cloud… that's
fine either way".

**5.2 Researcher bias.** Controls: a written script; observed task success recorded apart from
self-report; E1-S3 (a facilitator on 2–3 relatives, coded blind-swap); the owner leaving the room
for section 6 when a facilitator runs it.

**5.3 Tools.** PLAN names "LimeSurvey or Google Forms". Google Forms stores answers on Google's
servers, outside the two places H3 §1 allows (K14). PLAN's own minimum H3 rules do not name
third-party forms, so the prohibition binds once the owner confirms H3 (OD-21). Until then, E1
applies it voluntarily. Use paper, the private store, or a homelab-hosted form. LimeSurvey's
licence and hosting were not checked (blocked).

**5.4 Debrief and aftercare (adversary review).** The interview deliberately does not comment on
gaps. Leaving a relative alarmed, or still exposed with single-copy keepsakes, would be a
duty-of-care failure. After **all** data collection, the owner tells the person plainly what the
check showed. He offers or books the E2-S3 stopgap for their device type, and logs single-copy
findings by type on the owner's action list (not exported). Nothing is deleted or bought on the
spot. E1-S3 codes only notes taken before the debrief.

**5.5 Proto-personas (hypothesis slots; no family facts).** These are not final until the HCI
papers are read.

1. The owner-admin.
2. The helper (the "warm expert" idea from PLAN's reading list; papers not read).
3. A typical phone-first adult.
4. An extreme user: older, with vision, motor or cognitive needs, possibly in Assistive Access with
   a supporter (K13). They may have no computer (§2.5).
5. A minor, with guardian consent (H3 §9).

### 6. Desk research: older and non-technical users

- **WAI (K12).** WAI's position is that existing W3C standards "address most older user needs".
  That conclusion comes from the WAI-AGE work (2008–2010) and is about **web content**. Applying
  it to a native app is an inference, by analogy (for example WCAG2ICT). The prevalence figures
  come from a 2008 review that WAI does not plan to update, and they mix countries: the vision
  figures are UK estimates, and other figures come from Australian and other sources. Use them
  only as priors for "how likely is at least one relative affected". For E6 they still point to a
  WCAG-based baseline, large targets, high contrast, plain language and no reliance on audio.
- **Supporter-configured modes (K13).** Assistive Access is set up by a trusted supporter who
  picks the apps. This fits the helper persona. It also means S2a cannot assume such a relative
  can reach Settings. Android has maker-specific simple modes; the census records them (D13).
- **Text scaling (N1).** Android 14 scales fonts to 200 %; E6 layouts must survive it.
- **Smartphone ownership (K15, secondary only).** The Pew figure is a population prior and says
  nothing about this family's bytes.
- **Not read:** Pew detail; NN/g; the LoC and NARA guides (snippets only); every HCI paper PLAN
  names. A papers scout, or the owner from an unblocked machine, should fill this gap before
  personas and E3/E6 copy are finalised. It does not block E1-S2 or the census.

### 7. Proposed schedule (E1's input to E2; E2 owns the consolidated test plan)

The detail and the in-visit running order are in `kits/E1-S1/visit-plan.md`, also marked as an
input to E2.

| When | Step | Who | Output |
|---|---|---|---|
| Wave 0 (now) | Intake (Q-F1–F11, Q-G1–G6, Q-J5). **Confirm OD-21.** Approve the H3 §9 consent script, the interview addendum **and the S2a phone consent text**. Create the private store (H3 R7). | Owner | Prerequisites for any `FAM → AGG` step |
| Week 1 | E1-S2 **Part 0** on the owner's phones (gate). If it passes: S2a readings, in person where possible. Ask for visit slots in weeks 3–7 (L26). Name a facilitator candidate (L27). | Owner | Share range + bridge indicator, or "Part 0 failed" |
| Weeks 1–2 | E1-S1 gates: real Windows/macOS binaries, CT fixes (summary first, `.icloud` stubs), Part A on test accounts, Part B with real timings. Brief the facilitator. | Agent (CT), then owner | Census ready, or "No result" on blocked OSes |
| End of week 2 (Wave 1 exit) | OD-01 **decided** with the S2a range, or **scheduled** for after S2b | Owner | OD-01 outcome |
| Week 3 | Pilot visit with the helper persona; measure visit length; fix the guide | Owner | Protocol fixes; length cap confirmed |
| Weeks 3–7 | Consolidated visits (E2 order); S2b re-reads; M3/A2/X1 for flagged or straddling libraries; E1-S3 on 2–3 relatives; debrief at each visit | Owner (+ facilitator) | Raw FAM in the private store only |
| Weeks 7–8 | H3 §4 output check; summary, personas, journeys, ranked needs; E1 note updated with results | Owner, then agents on AGG only | E1 deliverables |

### Alternatives compared (research method)

| Option | Fit with settled requirements and H3 | Pros | Cons | Evidence |
|---|---|---|---|---|
| **Home visit: census + semi-structured interview + observed tasks + debrief (recommended)** | Fits; FAM stays local | Real numbers; belief vs reality checked; E2/E5 in the same sitting | Weeks 3–7; owner bias; long for older relatives (cap proposed) | K6, §5 |
| **Remote quick count (S2a), gated on Part 0 (recommended for OD-01 timing)** | Fits if readings go to the private store | Lets OD-01 be decided at Wave 1 exit; no install | Rests on unverified screens (K5); older relatives may struggle on a call; gives an estimate, not a bound | §2 |
| Schedule OD-01 after S2b | Fits; plan-compliant | No extra contact; screens read in person | ADR-0004 iOS section and the Apple long-lead item start later | K6 |
| One-off iOS census app (Personal Team) | Needs an owner exception (Apple code signing) | Exact bytes on iOS 27 devices | iOS 27-only, `nil` sizes, Mac/Xcode, Developer Mode, elderly-hostile steps | K1, K3, §2.2 |
| Survey + device checklist | Fits only without third-party form hosts | Low effort | Self-report on sizes is unreliable | §5.3 |
| Diary study | Fits | Real moments | High burden; overlaps E3-S2 | PLAN E3 |

### Similar work and lessons

| Project or paper | What they do | Borrow or avoid | Source |
|---|---|---|---|
| osxphotos | Original sizes and cloud state from the Mac Photos DB | Borrow for M3 (aggregate only) | S22 |
| Flutter photo_manager | iOS sizes via private keys | Avoid private keys; `dataSize` from iOS 27 | S24, S1 |
| dua-cli / dua-core | Parallel disk usage | Fallback traversal; lacks placeholder bits | S17 |
| W3C WAI older users | Ageing needs mapped to WCAG | E6 baseline (web-scoped) | S25, S26 |
| LoC personal archiving (secondary) | Identify, select, keep copies apart | Interview prompts | S31 |
| Marshall; Kaye et al.; Odom et al.; Grinter et al.; Poole et al.; Kiesler et al. | Named in PLAN | **Not read** (blocked) | — |

### Tools and libraries

| Name | Purpose | Licence | Maturity | Source |
|---|---|---|---|---|
| Rust std (`read_dir`, `MetadataExt`) | Walker with placeholder bits | MIT/Apache-2.0 | 1.94.0 | S14 |
| `dua-core` 4.1.0 | Fallback traversal | MIT | 2026-09-12 | S17 |
| `jwalk` 0.9.0 | — | MIT | **Deprecated** 2026-08-05 | S16 |
| `infer` 0.22.0 | Magic bytes (extensionless local files only) | MIT | 0.22.0 | S19 |
| `nom-exif` 3.8.0 | Capture month, camera model | MIT | 2026-09-07 | S20 |
| osxphotos 0.77.2 | M3 | MIT | 2026-09-27 | S22 |
| pymobiledevice3 11.19.4 | Not used (M6) | GPL-3.0-or-later | 2026-09-27 | S23 |
| ExifTool | Reference only; not in the census | Not checked (blocked) | — | — |

## Spikes

No emulator or simulator stands in for a family device. The CT rehearsal used **synthetic data
and emulated placeholders** (sticky-bit files on Linux), not real OneDrive or iCloud placeholders.

| Spike | Hypothesis | Pass → / fail → (decision) | Exec tag | Budget IDs | Data class | Status | Result |
|---|---|---|---|---|---|---|---|
| E1-S1 (CT rehearsal) | A std walker reads placeholder bits before any read, classifies by extension first, sniffs only extensionless files, writes H3 §7.6 CSVs with H3 §4 suppression, shows before saving, never opens a placeholder | Pass → use the design for the FM run; fail → fix in CT | CT build (SYN) | BUD-SCAN (related only) | `SYN → results` | **Pass** (scoped to SYN correctness and the open() audit) | Measured 2026-09-29 (Linux x86_64, 4 vCPU, rustc 1.94.1). Scale-1 SYN home (23,805 files, 59.7 GB logical) with `--exif`: totals, months and camera models equal truth, mechanised H3 §4 checks pass. strace: 400 opens in default mode, exactly the 400 extensionless local files and 0 of 550 emulated placeholders; `--exif` 8,950 opens, 0 placeholders. "No" or Enter saves nothing. 2 of 4,200 random-content extensionless files mis-sniffed at 500k scale (33/34 checks). `cargo check` passes for Windows-gnu and aarch64-darwin, but that code has **never run**. Timings (0.3–0.4 s default / 1.4 s `--exif` at scale 1 on ext4 cold; 1.5–1.9 s / 5.7–5.8 s for 499,905 files on tmpfs) are **not** evidence for BUD-SCAN or for a relative's disk. Evidence: [`spikes/E1-S1/README.md`](../../spikes/E1-S1/README.md), [`evidence/rehearsal-2026-09-29.log`](../../spikes/E1-S1/evidence/rehearsal-2026-09-29.log), [`evidence/sample-output-syn/`](../../spikes/E1-S1/evidence/sample-output-syn/) |
| E1-S1 (FM run) | On 3 real family computers: < 10 min, totals only, the relative confirms, at least one unmentioned location, no placeholder downloaded | Pass → script at every visit, feeding C4, A7-S3, G2, B1/B2, E4, H3 §7.6; fail → see kit table | FM (Part A OL) | BUD-SCAN (related; the "< 10 min" is local, for H1's overlap table) | Part A `LAB → results`; B/C `FAM → AGG` | **Kit-ready**, with new gates: real binaries, CT fixes (summary first, `.icloud` stubs), required real timings, EA/sync-client/directory-population checks | No family result. Kit: [`kits/E1-S1/README.md`](kits/E1-S1/README.md), [`device-checklist.md`](kits/E1-S1/device-checklist.md), [`visit-plan.md`](kits/E1-S1/visit-plan.md). Time figures in the kit are planning estimates. |
| E1-S2 (S2a remote, gated; S2b at the visit) | The family-wide Apple share of camera-library original bytes lies clearly on one side of 40 % | Escalate (share_low ≥ 40 %) → OD-01 before ADR-0004; do not escalate (share_high < 40 %) → B4 default; straddle/INCOMPLETE → M3/A2/X1 at S2b, or OD-01 scheduled | FM | None (40 % is PLAN's threshold) | `FAM → AGG` (family-wide range and counts only) | **Kit-ready** (revised 2026-10-06) | No family result. `share_range.py` re-tested 2026-10-06 on synthetic inputs only, 9 cases: escalate (67 %), do not escalate (2–6 %), numeric straddle (38–47 %), unbounded Android blocks escalation, the same library with a bound escalates, `mixed` Apple with unknown low blocks escalation, blank reading → INCOMPLETE, invalid rows rejected, M3 row. Kit: [`kits/E1-S2/README.md`](kits/E1-S2/README.md), [`call-script.md`](kits/E1-S2/call-script.md), [`share_range.py`](kits/E1-S2/share_range.py). |
| E1-S3 | A neutral facilitator yields at least as many concrete past-behaviour stories per interview as the owner | Pass → keep the facilitator where practical (at least section 6); fail → owner runs all, bias recorded | FM | None directly | `FAM → AGG` (story counts only) | **Kit-ready** | Nothing run. Directional only (2–3 interviews each). Guide now has the retention read-out and a debrief. Kit: [`kits/E1-S3/README.md`](kits/E1-S3/README.md), [`interview-guide.md`](kits/E1-S3/interview-guide.md), [`consent-addendum.md`](kits/E1-S3/consent-addendum.md) |

### How each skeptic issue was handled

| Issue (severity) | Handling |
|---|---|
| Android cloud figure is not original bytes; it biases toward escalation (major; skeptics 1–3) | Fixed: Android flags `saver`/`pre2021`/`pixel`/`shared_total` make the high unbounded unless a bound is measured; escalation then cannot be shown (§2.3, `share_range.py`, call script). N3 is labelled secondary. |
| The Apple side is ±0 while M1 can include imports, or miss uploads when iCloud is full (major; 1–3) | Fixed: Apple low = max(M1, M2), high = M1 + M2. The `mixed` flag makes the low unknown without M3/X1. The `icloud_full` flag is recorded. |
| A blank reading is treated as 0; a confident verdict comes from partial inputs (major; 3) | Fixed: blank = unknown; an INCOMPLETE state with no verdict. |
| Range presented as a bound (major; 2, 3) | Fixed: stated as an estimate until Part 0; the script prints this. |
| M4 rejected for the wrong reason (major; 1, 2) | Fixed: §2.2 M4 row. Personal Team listed and evaluated; the reasons are now K1/K2, burden, and the Apple-signing exception it would need. |
| S2a assumes relatives can drive Settings on the call phone; resembles a scam call (major; 2, 3) | Fixed: call set-up order, no-password/no-purchase opening, unit read-back, Assistive Access branch, "could not navigate → S2b", call timing (§2.4, call script). |
| No bridge/person indicator (major; 3) | Fixed: §2.5, P14, `persons.csv`. Reported alongside the share; the 40 % rule is unchanged. |
| No debrief or aftercare (major; 3) | Fixed: §5.4, interview guide "Debrief", visit-plan part 8, P15. |
| Census unproven on Mac/Windows; consent screen unreadable (major; 3) | Fixed in the kit as gates: real binaries, summary first (CT fix), terminal/prompt explanation script, printed copy, TCC gap recorded. Not fixed in code here: the throwaway spike code is unchanged so that it still matches its evidence. |
| Timing finding overstated (minor; 1–3) | Fixed: K6 re-scoped ("decided vs scheduled"), option B reworded, L26 fallback credited. |
| Private space / Secure Folder missing (minor; 1) | Fixed: §1, D16. |
| RECALL_ON_OPEN = FILE_ATTRIBUTE_EA (minor; 1, 3) | Fixed: §3 item 2, kit Part A step 4a. |
| Hydration is documented on Windows (minor; 1, 3) | Fixed: K8 and §3 cite Microsoft's text. Only macOS remains untested. |
| WAI priors over-generalised (minor; 1–3) | Fixed: §6. |
| S1 timing far from BUD-SCAN conditions (minor; 1) | Fixed: "pass" scoped to SYN; kit gate 3 requires real timings. |
| Legacy `.icloud` stubs; directory population (minor; 2) | Added to §3 and kit Part A (6a, 4c), with a CT fix. The stub claim is unverified. |
| Ownership overlap with E2 (minor; 2) | Fixed: §7 and `visit-plan.md` are marked as E1's input to E2. |
| Metric redefinition belongs to B4/OD-01; person-weighted share (minor; 2) | Fixed: §2.1 is a proposal; decision request 2; the bridge indicator. |
| Consent and OD-21 prerequisites for S2a (minor; 2) | Fixed: §2.4, §7, kit "Before you start". |
| Growth from two readings below resolution (minor; 2) | Fixed: §2.4; the kit step uses it only as a sanity check. |
| Retention not explained before exclusions; "Free up space" wording (minor; 3) | Fixed: §5.1, interview guide section 6, call script C4. |
| Visit length and splitting (minor; 3) | Partly: the visit plan proposes a 60–75 min cap per sitting and a split rule, both unmeasured. The week-3 pilot visit measures length. E2 decides. |
| Android limited access scope (minor; 3) | Fixed: the K10 verdict notes that SDK 33 apps are also limited. §1 says "media outside a limited-access grant" for any app. |

## Conflicts with settled text

None new.

- E1-S2 feeds the existing OD-01 conflict (CLAUDE.md "Platforms (v1)" vs ADR-0002 §4). It does
  not resolve it.
- A one-off iOS census app, even on a free Personal Team, would be Apple code signing. That
  touches CLAUDE.md "no Apple or Windows code signing for now" and ADR-0002 §5. This note does
  **not** propose it. If the owner wants it, it would need a research-only exception.
- Asking relatives to read Settings (S2a) and running the census are research activities, not
  product configuration. They do not conflict with "end users should never touch configuration".
- **PLAN** is not settled text, but it names `jwalk` and Google Forms. §3 and §5.3 explain why both
  should change. Flagged to H1; PLAN is not edited.

## Open questions

| Question | Who | By when |
|---|---|---|
| What iPhone Storage > Photos and iCloud > Storage > Photos mean: Optimize, Shared Library, Recently Deleted, behaviour when iCloud is full (K5) | Owner, kit E1-S2 Part 0; H1 (support.apple.com blocked) | Before any S2a reading |
| Do the Google One / Google Photos screens separate Photos bytes? Is the pre-2021/Pixel quota exemption as N3 says? | Part 0; H1 (support.google.com, blog.google blocked) | Before S2a on Android |
| Do family-plan organiser screens show per-member usage (X2)? | Part 0 step 5b | Week 1 |
| Can any iOS Shortcuts action report photo sizes without downloading originals (M7)? Do Apple or Google data-export flows show sizes before export? | Owner on a test device | Before S2b, if a straddle needs it |
| Is osxphotos `original_filesize` filled for cloud-only assets (K11)? | M3 on the owner's Mac (OL) | Before S2b uses M3 |
| Does sniffing a macOS dataless file hydrate it? Does a whole Windows file download? Does listing an unpopulated cloud folder fetch data? | E1-S1 Part A | Weeks 1–2 |
| Do pre-Sonoma Macs use `.icloud` stubs? | E1-S1 Part A step 6a | Before visiting such a Mac |
| Can the std walker meet "< 10 min" on real NTFS with Defender and on APFS? | E1-S1 gate 3 | Weeks 1–2 |
| An acceptable visit length per sitting for older relatives | E2, with the week-3 pilot | Week 3 |
| Which video-call services H3 accepts for S2a screen sharing | H3 | Week 1 |
| Should E1-S1's "< 10 min" become a budget ID? | H1 (overlap table) | Wave 2 |
| Apple's iOS 27 device list (maps family iPhones to `dataSize`) | H1 / B4 (blocked) | Before ADR-0004 |
| The HCI papers and practitioner sources named in PLAN | Papers scout, or the owner from an unblocked machine | Before personas are finalised (week 8) |

## Recommendation

1. **E1-S2: run S2a in week 1, but only behind the Part 0 gate.** The remote method rests on
   Settings screens whose meaning is unverified (K5, contested), so it is not recommended on its
   own. The owner first checks the screens on his own phones. If they behave as described, take
   S2a readings, in person or with a helper where possible, using the revised call script. Judge
   the 40 % gate with the widened rule (§2.3), and report the bridge indicator alongside it. If
   Part 0 fails, or the result is INCOMPLETE or straddles 40 %, **schedule** OD-01 for after S2b.
   That is plan-compliant, and its only cost is time. Do not build an iOS census app: the only
   documented size API is iOS 27+ and nullable (K1, K2), and installing would need Apple code
   signing, which settled text excludes for now.
2. **One consolidated home visit per relative.** It covers the past-behaviour interview, the device
   walk-through, the desktop census, E2/E5's observed tasks and a debrief. Split it into two
   sittings for older relatives; E2 decides. The owner runs it by default. E1-S3 tests a neutral
   facilitator on 2–3 relatives.
3. **Census script on Rust std.** Read placeholder bits from enumeration data only, never open a
   placeholder, and classify by extension first (K7, K8, K9; verified). Before any family run:
   build and run real Windows and macOS binaries, put the plain-words summary first, and measure
   real timings.
4. **No third-party form services for family answers.** Use paper, the private store or a homelab
   form. This becomes binding with OD-21 (K14).
5. **Never run the census on managed work or school devices.** Record them by self-report.

**What would change this:**

- If Part 0 shows the Settings figures are unusable, S2a is dropped, OD-01 is scheduled after the
  visits, and M3/A2/X1 carry S2b.
- If the owner grants a research-only Apple-signing exception, or accepts the Developer Program
  early (OD-01/OD-09), M4 becomes possible on iOS 27 devices.
- If the visits move into Wave 1, S2a is unnecessary.
- If B4 or the owner rejects the library-level metric, the kit's definitions change but its
  procedure does not.

## Decision requests

These are proposals for H1 to file; the shared queue is not edited here.

### 1. OD-01 evidence: E1-S2 method and timing
- **Needed by:** Wave 1 week 1 (so that Part 0 and S2a can run before OD-01 sitting 2).
- **Options:**

  | Option | What it means for the family | Cost | Reversibility | Risks |
  |---|---|---|---|---|
  | A. Part 0 gate, then S2a in Wave 1, S2b at the visit; fall back to B if Part 0 fails or the result is INCOMPLETE or straddles 40 % (recommended) | One short reading per library owner, in person or by call | Owner time per library (estimated 10–15 min, unmeasured), plus about 30 min for Part 0; no spend | Easy | Screens may still mislead (K5); older relatives may need a helper |
  | B. Schedule OD-01 for after S2b (plan-compliant) | No extra contact before the visit | None extra | Easy | ADR-0004 iOS section and the Apple long-lead item start several weeks later |
  | C. Decide OD-01 on the owner's Q-F3 guess only | None | None | Easy | No evidence behind the gate |
- **Recommendation:** A. It may give real evidence in time, and if it cannot, it falls back to B
  automatically.
- **Touches settled text:** none directly; it is evidence for OD-01, which does.

### 2. The gate metric and a second indicator (for B4 and the owner, under OD-01)
- **Question:** Measure E1-S2 as original bytes per camera library, each counted once, with
  desktop archives excluded? And report a per-person indicator (iPhone-primary people with no
  usable computer) alongside the byte share?
- **Options:** (A) adopt both, with the 40 % rule unchanged (recommended); (B) keep PLAN's wording
  and bytes only.
- **Recommendation:** A. It removes the ambiguity about double counting and on-device copies, and
  it shows people the desktop bridge would leave unprotected.

### 3. Research tooling and managed devices (related to OD-21)
- **Needed by:** before the first visit (week 3).
- **Options:** (A) paper, the private store or a homelab form; no census on managed devices
  (recommended); (B) Google Forms; run the census everywhere.
- **Recommendation:** A. Google Forms conflicts with H3 §1 once OD-21 confirms it. Running tools
  on employer devices risks policy breaches and blocked runs.

### 4. Neutral facilitator (with H5 L27, Q-F9)
- **Options:** (A) owner-run, with E1-S3 on 2–3 relatives (recommended); (B) a facilitator for
  all visits; (C) the owner only, with the bias recorded.
- **Recommendation:** A. It is cheap, and it measures the bias instead of assuming it.

## Hand-offs

| To | What | Why |
|---|---|---|
| B4 / OD-01 | The Part 0 gate, the S2a/S2b split, the metric proposal, the widened rule and the bridge indicator (§2); K1 `dataSize` iOS 27+ and nullable; M4 reasoning corrected | Gate input and timing |
| E2 | `visit-plan.md` and §7 as input to the consolidated plan; length cap and split rule; the debrief needs E2-S3's stopgap per device type by week 3 | E2 owns the test plan |
| H3 | Google Forms rule (binding with OD-21); phone consent text for S2a; acceptable video-call services; the debrief action list stays owner-only | Data governance |
| E6 | WAI scope caveats (web-scoped, 2008, mixed-country); Assistive Access supporter role; Android simple modes; 200 % font | ADR-0039 |
| B5 / B1 | Enumeration-only attribute reads (RECALL_ON_OPEN = EA value); directory population; pre-Sonoma `.icloud` stubs; Windows hydration is documented; `dua-core` `allocated_size` heuristic | Same issues in the product scanner |
| B2 | MediaStore fields; Private space, Secure Folder, Locked Folder, `.nomedia` blind spots; partial access also applies to SDK 33 apps | Android census variant and product scanner |
| D6 / E3 | Interview read-out now includes keep-forever retention; attitude themes feed OD-12/OD-17 | Exclusion preferences |
| C4 | Growth from capture-month histograms, not S2a→S2b | Capacity model |
| G2 | Device and OS fields (§4) | Device matrix |
| H1 | Blocked sources (Method); PLAN names `jwalk` and Google Forms; add E1-S1 "< 10 min" to the budget overlap table | Run rules; budgets |
