# B4. iOS decision and readiness

- **Workstream:** B4 (see `docs/research/PLAN.md`, section "B4.")
- **Status:** Draft (analyst deep read, Wave 1). Not yet under skeptic review.
- **Date:** 2026-09-29 (last updated 2026-09-29)
- **Feeds:** ADR-0004 (iOS section; owner E2 + B4), ADR-0003 (iOS constraints memo to T1), OD-01; inputs to A2/ADR-0007, A3/ADR-0009, A5/ADR-0016, B5/ADR-0020, B6/ADR-0021, D3/ADR-0014, E3/ADR-0024, OD-09
- **Depends on:** E1-S2 (iPhone share of camera-roll bytes; **not run yet**), T1 spike 8 (extended here as B4-S1), H2 (owner intake; Mac and Apple account availability)
- **Traceability rows closed or advanced:** R-03 (advanced: decision request written), R-05 (advanced: constraints memo written), C-06 (input: what the wizard says about iPhones)

## Summary

iOS does not need anything exotic from the Rust core, but it does need a **specific shape**. The core must hand every upload unit to the OS as a finished ciphertext file. It must read PhotoKit resources as sequential streams, with no byte-range reads. It must do its work in short, cancellable, idempotent steps that report progress, and it must keep all transfer state in its own database so a relaunched process can pick up where it stopped. These fourteen constraints (K1–K14 below) should go to T1 before ADR-0003 is accepted.

The iOS 26.1 **PhotoKit Background Resource Upload extension exists**, and iOS 27 already has a successor protocol. It **cannot carry Reliquary content**, because the system uploads the raw `PHAssetResource` bytes and the API has no hook to supply or transform the body. On its own it would therefore send plaintext to the cloud and break ADR-0001. Apple also confirms it has an open scheduling bug when iCloud Photos is on.

Background URLSession uploads of pre-encrypted part files remain the iOS content path. `BGContinuedProcessingTask` is the tool for a user-started "back up now".

Every iOS distribution route except the 7-day free profile needs the 99 USD/year Apple Developer Program. For 5–15 family iPhones the realistic routes are TestFlight (builds expire after 90 days) or Ad Hoc (UDID registration).

**Recommendation for OD-01 (medium confidence):** "iOS after the pilot, with a bridge".
- The core honours the iOS constraints now.
- iPhone photos are covered in the meantime by a desktop-side bridge.
- The gate is E1-S2: if iPhones hold ≥ 40 % of camera-roll bytes, escalate and start the Apple membership and B4-S2 at once.

This changes the CLAUDE.md platform line, so it needs the owner's decision and an amendment. Nothing has been edited.

## Questions

| # | Question | Short answer | Confidence |
|---|---|---|---|
| 1 | OD-01: iOS in v1 or deferred? | Recommend "after the pilot, with a bridge", gated on E1-S2 (≥ 40 % iPhone bytes → escalate). The owner decides. | Medium (E1-S2 not run; B4-S2 not run) |
| 2 | What must the core do now so iOS is not precluded? | 14 constraints, K1–K14 (§ "Constraints memo to T1"). None needs a new crypto design. K2, K4, K5 and K10 are changes to current drafts. | High for the platform facts; Medium for the derived constraints |
| 3 | Does the iOS 26.1 PhotoKit background upload extension exist? | Yes. `PHBackgroundResourceUploadExtension` on iOS/iPadOS 26.1, deprecated in 27.0. Successor `PHBackgroundResourceUploadJobExtension` on iOS/macOS/Mac Catalyst 27.0. | High (C1) |
| 4 | Can it upload app-encrypted files to R2 presigned URLs? | No documented way. A job is (`PHAssetResource`, `URLRequest`), and the system uploads the resource bytes itself. The app controls URL and headers, not the body. It is therefore unusable for content under ADR-0001. Download-only jobs (hydrating iCloud originals) might still help. | High that no API exists (C2); Medium that no workaround exists (needs B4-S2) |
| 5 | Other background options | Background URLSession (upload from file only; survives suspension and system termination; cancelled by user force-quit). `BGProcessingTask` (idle only; minutes). `BGAppRefreshTask` (≤ 30 s). `BGContinuedProcessingTask` (iOS 26; user-started; Live Activity; network and CPU allowed; must report progress). | High (C5–C9) |
| 6 | iCloud "Optimize iPhone Storage" | Originals may not be on the phone. `isNetworkAccessAllowed = true` makes PhotoKit download them. With the default (`false`) the request fails. There is no byte-range read, so resuming means re-reading or re-downloading from the start. | High (C10, C11); Apple Support page blocked |
| 7 | Distribution for 5–15 iPhones | Personal Team (free) is unusable: 3 devices, 7-day profiles. TestFlight: 99 USD/yr, 90-day builds, Beta App Review for external testers. Ad Hoc: 99 USD/yr, 100 iPhones per membership year, UDID registration. Unlisted App Store: full App Review, not for beta apps. Custom apps: needs an Apple Business org. EU marketplace: infeasible. | High (C13–C18) |
| 8 | Apple Developer Program implications | 99 USD/yr. Individual or organisation (organisation needs a legal entity and D-U-N-S). If it lapses, installed App Store apps keep working, but nothing new can be distributed. It collides with ADR-0002 §5's "no OS signing spend" and overlaps OD-09. | High (C13, C19) |
| 9 | Interim bridge and trust-model fit | A desktop-side bridge (iCloud originals synced to a family Mac/PC that Reliquary already backs up) fits encryption and "files on the device". icloudpd at the homelab needs ADP **off**, "Access iCloud Data on the Web" **on**, re-authentication about every two months, and the admin to hold the relative's Apple session. Its source is iCloud, not a device. It conflicts with the settled v1-source rule and needs an owner decision. | High on icloudpd facts (C20, C21); Medium on the desktop bridge (Apple Support page blocked; B4-S3 kit) |
| 10 | (new) Does the iOS transfer behaviour conflict with any budget? | Yes. **BUD-REVOKE** ("outstanding URLs expire within 15 min") conflicts with background URLSession, whose transfers started in the background are always discretionary and can be deferred until the phone has power and Wi-Fi. See K10. | Medium (inference from C6, C7) |

## Method

- **Sweep:** three scouts ran (docs; source code of similar OSS; community and forums). This analyst then re-fetched the load-bearing Apple sources in full, as DocC JSON from `developer.apple.com/tutorials/data/documentation/<path>.json`. That is the same primary content as the JS-rendered HTML page. The analyst also re-fetched the Apple distribution help pages as HTML, two Apple forum threads through WebFetch, and Nextcloud, Umbrel, UniFFI and icloudpd files from raw.githubusercontent.com.
- **Routes used:** direct HTTPS to developer.apple.com; raw.githubusercontent.com; GitHub MCP code search; WebFetch for Apple forums and github.com discussions.
- **Blocked sources:** each is listed below. None was silently replaced; where a secondary source is used instead, the claim says so. All go to H1.
  - support.apple.com/en-us/108782 (Optimize iPhone Storage)
  - datatracker.ietf.org (resumable-upload draft revision)
  - openradar.appspot.com FB23870865 (search snippet only)
  - ente.com help and photosync-app.com support (snippets only)
  - GitHub MCP `pull_request_read` for nextcloud/ios#4279 (denied)
  - github.com discussion pages, which loaded only partly through WebFetch
- **Not found:** Apple crash-report docs did not mention `0xdead10cc` when grepped. The app-group file-lock hazard therefore stays an open question and is not stated as a claim.
- **Stop rule:** the analyst's re-reads added no new primary source that changed an answer, apart from the force-quit wording in `background(withIdentifier:)`. They also resolved the scout conflicts listed under Findings §7.

## Sources

| # | Source | Publisher | Published or version date | Accessed | Primary? |
|---|---|---|---|---|---|
| S1 | Uploading asset resources in the background — https://developer.apple.com/documentation/photokit/uploading-asset-resources-in-the-background | Apple | Undated; covers iOS 26.1 and 27.0 | 2026-09-29 | Yes |
| S2 | `PHBackgroundResourceUploadExtension` — https://developer.apple.com/documentation/photos/phbackgroundresourceuploadextension | Apple | iOS 26.1, deprecated 27.0 | 2026-09-29 | Yes |
| S3 | `PHAssetResourceUploadJobChangeRequest` (+ `creationRequestForJob(destination:resource:)`) — https://developer.apple.com/documentation/photos/phassetresourceuploadjobchangerequest | Apple | iOS 26.1; macOS 27.0 | 2026-09-29 | Yes |
| S4 | `PHAssetResourceUploadJob`, `jobLimit`, `Type` — https://developer.apple.com/documentation/photos/phassetresourceuploadjob | Apple | iOS 26.1 (`downloadOnly` 26.4) | 2026-09-29 | Yes |
| S5 | `PHAssetResourceUploadJobOptions`, `enableUploadJobExtension(with:)` — https://developer.apple.com/documentation/photos/phassetresourceuploadjoboptions | Apple | iOS 27.0 | 2026-09-29 | Yes |
| S6 | `URLSessionConfiguration.background(withIdentifier:)` — https://developer.apple.com/documentation/foundation/urlsessionconfiguration/background(withidentifier:) | Apple | iOS 8.0+ | 2026-09-29 | Yes |
| S7 | Downloading files in the background — https://developer.apple.com/documentation/foundation/downloading-files-in-the-background | Apple | Undated | 2026-09-29 | Yes |
| S8 | `isDiscretionary` — https://developer.apple.com/documentation/foundation/urlsessionconfiguration/isdiscretionary | Apple | Undated | 2026-09-29 | Yes |
| S9 | `BGContinuedProcessingTask` / `…Request` — https://developer.apple.com/documentation/backgroundtasks/bgcontinuedprocessingtask | Apple | iOS, iPadOS, Mac Catalyst 26.0 | 2026-09-29 | Yes |
| S10 | Performing long-running tasks on iOS and iPadOS — https://developer.apple.com/documentation/backgroundtasks/performing-long-running-tasks-on-ios-and-ipados | Apple | Undated | 2026-09-29 | Yes |
| S11 | `BGProcessingTask` / `BGProcessingTaskRequest` — https://developer.apple.com/documentation/backgroundtasks/bgprocessingtask | Apple | iOS 13.0+ | 2026-09-29 | Yes |
| S12 | Choosing Background Strategies for Your App — https://developer.apple.com/documentation/backgroundtasks/choosing-background-strategies-for-your-app | Apple | Undated | 2026-09-29 (docs scout) | Yes |
| S13 | `PHAssetResourceManager` `requestData(…)` and `writeData(…toFile:…)` — https://developer.apple.com/documentation/photos/phassetresourcemanager | Apple | iOS 9.0+ | 2026-09-29 | Yes |
| S14 | `isNetworkAccessAllowed` — https://developer.apple.com/documentation/photos/phassetresourcerequestoptions/isnetworkaccessallowed | Apple | iOS 9.0+ | 2026-09-29 | Yes |
| S15 | `PHAssetResourceType` — https://developer.apple.com/documentation/photos/phassetresourcetype | Apple | iOS 9.0+ | 2026-09-29 | Yes |
| S16 | `fetchPersistentChanges(since:)`; `PHCloudIdentifier` — https://developer.apple.com/documentation/photos/phphotolibrary/fetchpersistentchanges(since:) | Apple | iOS 16.0+ / 15.0+ | 2026-09-29 | Yes |
| S17 | Apple Developer Program — What's included — https://developer.apple.com/programs/whats-included/ | Apple | Current page | 2026-09-29 | Yes |
| S18 | Compare memberships (Personal Team limits) — https://developer.apple.com/support/compare-memberships/ | Apple | Current page | 2026-09-29 | Yes |
| S19 | TestFlight overview — https://developer.apple.com/help/app-store-connect/test-a-beta-version/testflight-overview | Apple | Current page | 2026-09-29 | Yes |
| S20 | Devices overview (100 per product family per membership year) — https://developer.apple.com/help/account/devices/devices-overview | Apple | Current page | 2026-09-29 | Yes |
| S21 | Unlisted app distribution — https://developer.apple.com/support/unlisted-app-distribution/ | Apple | Current page | 2026-09-29 | Yes |
| S22 | Custom apps — https://developer.apple.com/custom-apps/ | Apple | Current page | 2026-09-29 | Yes |
| S23 | Alternative app marketplace in the EU — https://developer.apple.com/support/alternative-app-marketplace-in-the-eu/ | Apple | Current page | 2026-09-29 | Yes |
| S24 | Membership renewal and expiry — https://developer.apple.com/support/renewal/ | Apple | Current page | 2026-09-29 | Yes |
| S25 | Enroll — https://developer.apple.com/programs/enroll/ | Apple | Current page | 2026-09-29 (docs scout) | Yes |
| S26 | Forum 818566 "How to upload large videos with PHAssetResourceUploadJobChangeRequest?" — https://developer.apple.com/forums/thread/818566 | Apple forums (DTS + PhotoKit engineer) | 2026-03; engineer reply 2026-06 | 2026-09-29 | No (Apple staff statements) |
| S27 | Forum 822256 "…never scheduled when iCloud Photos is enabled" — https://developer.apple.com/forums/thread/822256 | Apple forums (DTS + engineer) | 2026-04; replies 2026-05, 2026-06 | 2026-09-29 | No (Apple staff statements) |
| S28 | Forum 685525 "iOS Background Execution Limits" (Quinn, DTS) — https://developer.apple.com/forums/thread/685525 | Apple forums | 2021-07, updated 2026-01-09 | 2026-09-29 (docs scout) | No |
| S29 | Forum 805554 "BGContinuedProcessingTask expiring unpredictably" — https://developer.apple.com/forums/thread/805554 | Apple forums (DTS) | 2025-10/11 | 2026-09-29 (community scout) | No |
| S30 | Forum 807754 (BGProcessingTask vs TestFlight; Quinn) and 692514 (file-backed uploads) — https://developer.apple.com/forums/thread/807754 | Apple forums | 2025-11; 2021-10 | 2026-09-29 (community scout) | No |
| S31 | nextcloud/ios @ master : `BackgroundUploadExtension/*.swift`, `NCBackgroundUploadExtensionManager.swift` | Nextcloud | master (2026) | 2026-09-29 | Yes (code) |
| S32 | nextcloud/ios PR #4279 — https://github.com/nextcloud/ios/pull/4279 | Nextcloud | Merged 2026-09-17 | 2026-09-29 (WebFetch summary only) | Yes, but read only as a summary |
| S33 | getumbrel/umbrel @ master : `clients/apple/ios/project.yml`, `…/BackgroundUploadExtension.swift` | Umbrel | master | 2026-09-29 | Yes (code) |
| S34 | immich-app/immich PR #28293 — https://github.com/immich-app/immich/pull/28293; `mobile/ios/Runner/Background/*.swift` @ main | Immich | Merged 2026-06-04 | 2026-09-29 (community + source scouts) | Yes |
| S35 | ente-io/ente @ main : `mobile/apps/photos/lib/module/upload/service/{file_uploader,multipart}.dart` | Ente | main | 2026-09-29 (source scout) | Yes (code) |
| S36 | UniFFI manual @ main : `docs/manual/src/swift/overview.md`, `futures.md`, `foreign_traits.md` | Mozilla | main | 2026-09-29 | Yes |
| S37 | icloudpd @ master : `README.md`, `docs/authentication.md`, `docs/size.md` | icloudpd project | master (links release v1.32.3) | 2026-09-29 | Yes |
| S38 | osxphotos @ main : `README.md` | R. Taylor | main | 2026-09-29 (source scout) | Yes |
| S39 | R2 presigned URLs (docs source) — cloudflare-docs @ production : `src/content/docs/r2/api/s3/presigned-urls.mdx` | Cloudflare | production branch | 2026-09-29 (docs scout) | Yes |
| S40 | 9to5Mac, "iOS 26.1 will let third-party apps back up photos in the background" — https://9to5mac.com/2025/10/24/ios-26-1-third-party-photos-backup-background/ | 9to5Mac | 2025-10-24 | 2026-09-29 (snippet) | No |
| S41 | openradar FB23870865 (enhancement request: no payload transform) | openradar | Unknown | Snippet only (fetch blocked) | No |
| S42 | Immich discussions #23358, #25777, #23583; issues #22850, #17576 | Immich community | 2025-10 to 2026-02 | 2026-09-29 (community scout) | No |
| S43 | Apple forum 776450 (unlisted distribution rejections) — https://developer.apple.com/forums/thread/776450 | Apple forums | 2025-03 to 2025-07 | 2026-09-29 (community scout) | No |

## Claims

Skeptic columns are empty: this draft has not had skeptic review yet (PLAN §5.1, stage 4).

| # | Claim | Sources | Key? | Skeptic 1 | Skeptic 2 | Skeptic 3 | Verdict |
|---|---|---|---|---|---|---|---|
| C1 | The PhotoKit Background Resource Upload extension exists. It shipped as `PHBackgroundResourceUploadExtension` (`process()`, `notifyTermination()`) on iOS/iPadOS 26.1 and is deprecated in 27.0. The async `PHBackgroundResourceUploadJobExtension` (`processJobs()`, `willTerminate()`) is on iOS, macOS and Mac Catalyst 27.0. It registers at extension point `com.apple.photos.background-upload`, is not available in Simulator, and requires full (`.readWrite`, `.authorized`) library access plus `setUploadJobExtensionEnabled(true)`. | S1, S2, S40 | Yes | | | | Pending |
| C2 | An upload job pairs one `PHAssetResource` with a destination `URLRequest`, and the system uploads the resource. The change-request class exposes only: create upload job, create download-only job, acknowledge, `retry(destination:)`, cancel and the placeholder. No documented API supplies a file, data, stream or body transform. | S1, S3, S4; S41 (secondary, corroborating) | Yes | | | | Pending |
| C3 | Apple PhotoKit engineer, June 2026: "PHBackgroundResourceUploadExtension does not support chunking the resource during the upload cycle". The recommended paths are the resumable-upload protocol, or a custom NSURLSession background upload. DTS adds that the daemon "cannot 'call back' into your code to ask for the next byte range or the next URL". | S26 | Yes | | | | Pending (Apple staff, forum) |
| C4 | With iCloud Photos on (iOS 26.4), the extension was never scheduled; assetsd logged "Result: NO". Apple DTS (2026-05) called it "a bug rather than intentional behavior". An Apple engineer (2026-06) said iCloud Photos "should have no bearing". No fix or iOS 27 status was published. | S27 | Yes | | | | Pending |
| C5 | Background URLSession runs transfers in a separate process that survives app suspension and system termination. "Only upload tasks from a file are supported (uploads from data instances or a stream fail after the app exits)." Redirects are always followed. | S6, S7; S30 corroborates | Yes | | | | Pending |
| C6 | If the user force-quits from the multitasking screen, "the system cancels all of the session's background transfers" and does not relaunch the app until the user does. | S6; S28 corroborates | Yes | | | | Pending |
| C7 | Tasks started while the app is in the background are always discretionary (the system may wait for power and Wi-Fi). A rate limiter delays tasks started from the background, and the delay grows with each relaunch until the app is foregrounded. Apple advises one session with many tasks at once, and fewer, larger transfers. | S7, S8 | Yes | | | | Pending |
| C8 | `BGContinuedProcessingTask` (iOS/iPadOS/Mac Catalyst 26.0) must be submitted from the foreground in response to a person's action. It shows a Live Activity the person can cancel, may use the network and heavy CPU in the background, and can be terminated under resource pressure, low-progress tasks first. It must report progress via `ProgressReporting`. DTS (secondary) describes a roughly 30 s "stalled" cadence. | S9, S10; S29 | Yes | | | | Pending (30 s figure: secondary only) |
| C9 | `BGProcessingTask` runs only when the device is idle, and is terminated when the user starts using it. It needs the `processing` background mode and offers `requiresExternalPower` and `requiresNetworkConnectivity`. `BGAppRefreshTask` and background pushes give ≤ 30 s. Immich measured a 20 s refresh budget in practice. | S11, S12, S34 | Yes | | | | Pending |
| C10 | `PHAssetResourceManager.requestData` delivers a resource as sequential chunks, and `writeData(…toFile:)` writes it progressively to a file. Either may download from iCloud when `isNetworkAccessAllowed = true`. With the default `false`, a non-local resource fails with a "requires network access" error. Neither API takes a byte range. | S13, S14 | Yes | | | | Pending |
| C11 | One asset maps to several resources. The originals are `.photo`, `.video`, `.pairedVideo` and `.alternatePhoto`. The modified versions are `.fullSizePhoto`, `.fullSizeVideo` and `.fullSizePairedVideo`. Edit-reconstruction data is `.adjustmentData` and `.adjustmentBase*`. | S15; S33 (Umbrel picks `fullSize*` first) | Yes | | | | Pending |
| C12 | `PHCloudIdentifier` (iOS 15+) identifies an asset across iCloud-synced devices, whereas a local identifier is valid only on one device. Mapping is expensive and can fail (`identifierNotFound`, `multipleIdentifiersFound`). Persistent change tokens (iOS 16+) can expire. | S16 | Yes | | | | Pending |
| C13 | The Apple Developer Program costs 99 USD per membership year. An organisation needs a legal entity and a D-U-N-S number. | S17, S25 | Yes (cost) | | | | Pending |
| C14 | Personal Team (free): up to 3 devices and 10 App IDs, both expiring after 7 days; profiles expire 7 days from issue; up to 3 apps per device. | S18 | Yes | | | | Pending |
| C15 | TestFlight: a build can be tested for up to 90 days. Up to 10,000 external testers and up to 100 internal testers, who must be App Store Connect users. External testing may need review; the first build added to a group is reviewed. | S19 | Yes | | | | Pending |
| C16 | Ad Hoc / development: up to 100 devices per product family per membership year. Disabling a device does not free a slot; the count resets only at renewal. | S20 | Yes | | | | Pending |
| C17 | Unlisted App Store: link-only discovery. The app must be on the App Store or be submitted in final form to App Review. Requests are declined for beta or prerelease apps. | S21; S43 (friction, secondary) | Yes | | | | Pending |
| C18 | Custom apps go only to organisations named by Organization ID in Apple Business or Apple School Manager, through MDM or redemption codes, after App Review. An EU alternative marketplace requires organisation enrollment plus a financial qualification (for example a 1,000,000 USD stand-by letter of credit), and the app must primarily distribute other apps. | S22, S23 | No (rules options out) | | | | Pending |
| C19 | If the (non-Enterprise) membership expires, apps are no longer available to download and no updates can be submitted, but already-installed apps "will still function". | S24 | Yes | | | | Pending |
| C20 | icloudpd needs "Access iCloud Data on the Web" enabled and ADP disabled, because it simulates web access. Its MFA session expires after an Apple-set interval, "currently two months". FIDO keys are not supported. The README asks for a new maintainer. | S37 | Yes | | | | Pending |
| C21 | Under Optimize Mac Storage, originals may be missing from a Mac Photos library. osxphotos' `--download-missing` works via AppleScript (fragile) or an experimental PhotoKit mode. | S38 | Yes | | | | Pending |
| C22 | UniFFI's Swift bindings are "production-quality", but a Rust panic becomes "a fatal Swift error that cannot be caught". Swift 6 support is "partial". There is no built-in cancellation of async calls; the manual recommends a library-level `cancel()` flag. Foreign traits let Swift implement Rust traits. | S36 | Yes | | | | Pending |
| C23 | Nextcloud iOS (master) ships the extension only under `@available(iOS 27)` and only for server ≥ v35. It uses an authenticated WebDAV **PUT** destination, and caps in-flight jobs at `min(jobLimit, 20)`. | S31, S32 | No (similar work) | | | | Pending |

## Findings

### 1. The PhotoKit background upload extension (C1–C4, C23)

- **It exists and is real platform direction** (High).
  - iOS 26.1 introduced it.
  - iOS 27 replaced the protocol with an async one and brought it to macOS and Mac Catalyst.
  - iOS 27 also added `PHAssetResourceUploadJobOptions.preventsExpensiveNetworkAccess`.
  - Production adopters exist: Nextcloud (iOS 27 only, merged 2026-09-17), Umbrel (the extension is its only uploader), and the third-party YAIIU Immich uploader. Immich itself has not adopted it; three feature requests have no maintainer reply.
- **It cannot carry Reliquary content** (High that the API has no hook; Medium that there is no workaround).
  - The system reads the `PHAssetResource` and uploads those bytes. The app chooses only the URL and headers.
  - Under ADR-0001 the cloud must never see plaintext. Pointing the extension at R2 or at a Worker would send plaintext photos to Cloudflare.
  - The secondary FB23870865 snippet says the same, and adds that E2EE storage apps are the affected class.
- **One variant is excluded by settled text, not by the platform:** plaintext over TLS straight to a homelab endpoint on the home LAN. It would violate the CLAUDE.md property "client-side encryption before data leaves the device". It would also add an inbound listener to the homelab, which is the optional LAN-direct transport (ADR-0037, P2). It is recorded here and not recommended.
- **Two possible uses that remain open for B4-S2 on a device:**
  1. **Download-only jobs** (iOS 26.4+) to hydrate iCloud-only originals in the background. The app then reads them through `PHAssetResourceManager`, and the Rust core encrypts them.
     - Apple warns that the system may purge downloaded resources under disk pressure.
     - It is not documented whether the extension process may run app code (the Rust core) and start its own background URLSession within its runtime limit.
  2. **Scheduling signal.** The extension is invoked by the system "based on network availability, power state and device activity" and could wake the core. This is undocumented and not recommended as a design basis.
- **Maturity risk** (Medium).
  - The iCloud-Photos scheduling bug (C4) hits exactly the family population, since most iPhones have iCloud Photos on.
  - Early adopters could not get `process()` to run (S26/S27, forum 806834).
  - Developer Mode for testing exists only on iOS 27.
  - Apple does not document the numeric job limit, the runtime limit or the memory limit.
- **Server contract** (reference only, since it is not used for content).
  - OPTIONS preflight → 200 with `Upload-Limit` (or 501), and a 104 informational response during the upload.
  - Apple's example header is `Upload-Incomplete: ?0`; the httpwg editor's copy now uses `Upload-Complete`. The draft revision Apple implements is unconfirmed (datatracker blocked).
  - Umbrel reports uploads to an endpoint whose repo has no `Upload-Limit` code (GitHub code search, 0 hits). That weakly suggests a non-resumable destination still works.
  - Umbrel also recorded that jobs uploaded to a host other than `BackgroundUploadURLBase` on iOS 26.6.1, which Apple does not document.

### 2. Background execution model for a Reliquary iOS app (C5–C9)

- **Content path:** the Rust core writes ciphertext part files, and Swift hands them to **one** background URLSession with `uploadTask(with:fromFile:)` to presigned R2 part URLs.
  - Start many tasks at once while the app is in the foreground (the rate limiter, C7).
  - Completions arrive via `handleEventsForBackgroundURLSession` after a relaunch, and the session must be recreated with the same identifier (S7).
  - This is the only mechanism whose transfers progress without app code running (S30, Quinn).
- **Seed and "back up now":** `BGContinuedProcessingTask`, started from a button.
  - It runs hashing, encryption and upload with a Live Activity, and reports byte-level progress.
  - iOS 26+ only. The person can cancel it. The 30 s stall figure is secondary (C8).
  - Piwigo and Sushitrain (a Go core on iOS) already use it (source scout; not re-read here).
- **Steady state:** `BGProcessingTask` (idle, often overnight on the charger) and `BGAppRefreshTask` (≤ 30 s, about 20 s measured by Immich) for new-photo detection, hashing and enqueueing.
  - Immich's PR #28293 shows the failure mode that K7 designs against: sequential sync, then hash, then enqueue starved the upload step.
- **Force-quit is the biggest steady-state risk for non-technical users** (C6).
  - A swipe-away cancels all queued transfers and stops background launches until the app is opened.
  - Reliquary must therefore treat "iPhone has not checked in" as a health state and nudge the person (E3; ADR-0002 email nudges).
- **BUD-TTS feasibility on iOS is unknown.** BUD-TTS asks for "stored at home" within 24 h while online. No source measures it; B4-S2 must.

### 3. Constraints memo to T1 (input to ADR-0003; B4-S1 extends T1 spike 8)

These are requirements on the shared Rust core and formats. They are cheap if adopted before ADR-0003, ADR-0007 and ADR-0009 freeze.

| ID | Constraint | Why (evidence) | Touches |
|---|---|---|---|
| K1 | **File-based handoff.** The transport is a trait. The core can emit each upload unit (one multipart part, or a single-PUT object) as a complete, closed, fsynced ciphertext file, and must never *require* a streamed request body. | C5, S30 | T1, B6, A2 |
| K2 | **Keystream guard at handoff, not at send.** The guard in `content-encryption-format.md` §1.3 ("no byte leaves until the chunk tag is journaled") must be satisfied **before** a part file is handed to the OS. After handoff, `nsurlsessiond` may send it with the app gone. | C5, C6; content-encryption-format.md §1 | A2, B6 |
| K3 | **Bounded part-file spool.** Pre-produce a batch of part files, because background-started tasks are rate-limited (C7), but keep plaintext plus ciphertext temp files inside **BUD-TMP** (≤ 2 GB, never below 10 % free). At the default 5,244,160-byte part size that is at most about 380 parts in flight. That number is arithmetic, not a measurement. | C7; budgets.md | B6, A2 |
| K4 | **Sequential-only sources.** The source-reader trait must declare whether it can seek. PhotoKit resources are sequential (C10), so regenerating a missing part means re-reading from offset 0 and skipping, which may mean re-downloading from iCloud. Otherwise the resource must be materialised as a plaintext temp file, which for large videos collides with BUD-TMP. The core must support both and choose by size. | C10, C11; Immich #22850 (storage bloat, secondary) | A2, B5, B6 |
| K5 | **Opaque source version token instead of a stat snapshot.** The change-abort check (size, mtime, ctime, file ID) has no PhotoKit equivalent. The source plugin supplies an opaque version token, for example asset local ID + resource type + asset modification date. That matches ADR-0001's iOS locator. | C12; ADR-0001 cache-key text | A1, A2, B5 |
| K6 | **Multi-resource items.** An item model where one asset owns several objects with roles: the original first, the edited `fullSize*` optional, the Live Photo paired video, RAW+JPEG as `alternatePhoto`, and adjustment data. Do not copy Umbrel's `fullSize`-first choice; keepsakes need originals. Immich #17576 shows how getting this wrong loses slow-motion originals. | C11 | A5 (ADR-0016), H4 |
| K7 | **Short, idempotent, cancellable units.** Every core entry point callable from a BG task commits progress in small transactions. It must be safe to kill at any instruction and must check a cancel flag, since UniFFI has no native cancellation. Discovery, hashing and enqueue run as interleaved slices that each fit a ≤ 20–30 s window, with the newest items first. | C9, C22; Immich PR #28293 | B6, T1 |
| K8 | **Fine-grained progress callbacks.** Byte-level progress, emitted at least every few seconds, so `BGContinuedProcessingTask` is not marked stalled. | C8 | T1, B6 |
| K9 | **Transfer state owned by the core DB.** Map OS task identifiers or `taskDescription` to (upload, part). Record the ETag and status from completions delivered to a *different* process lifetime. Reconcile orphans on launch. Whether a background task's `HTTPURLResponse` exposes the R2 `ETag` must be checked (B4-S2; T1 spike 4). | C5, C6 | B6, A3 |
| K10 | **Presigned-URL lifetime vs discretionary transfers.** Background-started transfers are always discretionary and rate-limited (C7), so a URL signed at handoff may expire before iOS sends it. This **conflicts with BUD-REVOKE's 15-minute outstanding-URL expiry.** Options: longer URL lifetimes for iOS, bounded by D3's revocation model (revocation enforced at claim/commit, abuse bounded by BUD-ABUSE), or cancel and re-sign on each app wake. Either way it is a D3/C1 decision, not a client detail. | C7, C8; budgets.md BUD-REVOKE; R2 max 7 days (S39) | D3 (ADR-0014), C1 (ADR-0010), H1 (budget) |
| K11 | **Single-writer DB, or multi-process safe.** If a PhotoKit extension or share extension is ever added, the state DB lives in an app-group container shared by two processes. Keep the Rust core single-writer, with the extension only enqueuing intents, unless a spike shows SQLite locking across processes is safe on iOS. The suspended-process file-lock hazard is an open question, not a verified claim. | C1 (app-group storage recommended by Apple) | B6 |
| K12 | **No panics across the FFI boundary.** Every exported function returns `Result`; use `catch_unwind` at the boundary. A panic in Swift is an uncatchable fatal error. Foreign traits must be `Sendable`. | C22 | T1, G1 |
| K13 | **Health must survive force-quit.** Server-side "last check-in per device" plus nudges. The client cannot promise progress after a swipe-away. | C6 | E3 (ADR-0024/0025), C1 |
| K14 | **No dependency on system-owned uploads.** Formats and protocol must not assume the OS uploads raw assets. The PhotoKit extension, if used at all, only hydrates or schedules. | C2, C3 | T1, A3 |

**Net for ADR-0003 (Medium-High).** Option C (Rust core + UniFFI, native shells) fits iOS without change. The T1 spike 8 statement ("Swift shell hands Rust-produced part files to a background URLSession and records results in the Rust SQLite DB after relaunch") holds on paper, with K2, K4, K5 and K10 added. None needs a new crypto design; K2 is a placement rule for the existing guard.

### 4. iCloud "Optimize iPhone Storage" (C10, C14; Apple Support page blocked)

- When originals are only in iCloud, PhotoKit downloads them only if `isNetworkAccessAllowed = true` (default `false`, which errors).
- That download costs time, cellular data (subject to the metered-network requirement) and temporary disk (BUD-TMP).
- A backup that reads only local data could silently fall back to reduced local renditions. That claim comes from a secondary blog with unverified resolution figures. Reliquary should instead **always request the original resource type with network access allowed**, and report "waiting to download from iCloud" as a health reason (E3). This is an inference from C10 and C11.
- Confirmed on paper by C10; still needs the B4-S2 device check with an Optimize-Storage phone.

### 5. Distribution and the Apple Developer Program (C13–C19)

| Route | Needs | Fits 5–15 iPhones? | Recurring chores | Review | Notes |
|---|---|---|---|---|---|
| Personal Team (free) | Mac + Xcode | No: 3 devices, 7-day profiles | Reinstall every 7 days by cable | None | Unusable |
| TestFlight internal | 99 USD/yr; each person added as an App Store Connect user | Yes (≤ 100) | Upload a build at least every 90 days; manage users | Not required for internal testers (the doc only says external builds "may require review") | Each relative needs an App Store Connect account; the wording on internal review is inferred |
| TestFlight external | 99 USD/yr | Yes (≤ 10,000; email or public link) | Upload at least every 90 days | First build to a group is reviewed | The easiest install for relatives (TestFlight app + link) |
| Ad Hoc | 99 USD/yr; each iPhone's UDID | Yes (≤ 100 per membership year; slots not freed until renewal) | Collect UDIDs; re-sign when adding devices; profile lifetime **unverified** | None | Install via link or Configurator; worst UX for relatives |
| Unlisted App Store | 99 USD/yr; final app | Yes | Normal App Store updates | Full App Review; declined if beta | Friction reports (S43, secondary); best steady-state UX |
| Custom app (Apple Business) | Organisation in Apple Business + MDM or codes | Technically | MDM or codes | App Review | Overkill for a family |
| EU alternative marketplace | Organisation + financial qualification | No | — | — | Infeasible |

- **Implications.**
  1. Any iOS route means paying 99 USD/yr. ADR-0002 §5 chose no OS signing spend, so OD-01 = "iOS in v1" drags OD-09 forward.
  2. The same membership issues Apple's "Developer ID" identity. It may therefore also buy macOS Developer ID signing and notarisation for the desktop app (Medium; S17 names Developer ID; details belong to B7/OD-09).
  3. A lapsed membership leaves installed App Store apps working (C19). TestFlight builds still stop after 90 days (C15), so TestFlight is **not** a fire-and-forget channel for a keep-forever backup app.
  4. Guideline 5.1.1 account deletion and `PrivacyInfo.xcprivacy` apply to any reviewed route (PLAN B3 checklist; not researched here).
- **Suggested channel if iOS goes ahead:** TestFlight external for the pilot, then unlisted App Store for steady state. This is not decided; it goes into ADR-0004's iOS section.

### 6. Interim bridge for iPhone photos (C20, C21)

| Bridge | Trust model (ADR-0001) | "Files on the device only" (v1 sources) | Chores | Risks |
|---|---|---|---|---|
| **Desktop-side**: the relative's iCloud Photos synced with originals to a Mac (Photos) or a Windows PC (iCloud for Windows) that Reliquary already protects | Fits: the desktop client encrypts before upload | Fits if the Mac/PC library or folder is treated as that device's files (B5 decides PhotoKit vs package reading on macOS) | Keep the "download originals" setting on; enough disk | Optimize Mac Storage leaves originals missing (C21); Windows placeholders (B5-S3); Apple Support page blocked, so settings wording is unverified |
| **icloudpd at the homelab** | Partly. Photos go Apple → homelab directly, with no cloud staging. The relative must **turn ADP off** (weakens their privacy against Apple). The admin holds the relative's iCloud web session (SEC class) | **Conflicts**: the source is iCloud, a roadmap item, not the device | Re-authenticate with the relative's 2FA about every two months; crash reports on invalidated sessions (secondary) | Maintainer wanted; Apple web-auth churn |
| **None** | — | — | — | iPhone keepsakes unprotected until iOS ships |

B4-S3 (kit) checks that a 500-photo sample arrives as originals with correct dates.

### 7. Scout conflicts resolved

| Conflict | Resolution |
|---|---|
| `BGContinuedProcessingTask` on Mac Catalyst: a blog says unavailable; Apple's symbol page lists Mac Catalyst 26.0 | Primary wins: iOS, iPadOS and Mac Catalyst 26.0; not native macOS. Irrelevant to the iPhone decision. |
| Force-quit: the docs scout had only Quinn's relaunch flag | Primary (S6) is stronger: force-quit **cancels** all background transfers as well. |
| Nextcloud gating: PR title "NC >= 33" vs master "v35"; a WebFetch summary said "iOS 26.1 lacks this capability" | Current master code gates on iOS 27 and server v35. The iOS 26.1 claim is wrong per S1/S2 (the protocol exists on 26.1). Nextcloud's reason for the iOS 27 gate is unverified; a plausible guess is the iOS 27 options API (S5). Live Photos, "excluded at first" in the PR, are handled in master. |
| Can a non-resumable server receive extension uploads? Apple says both OPTIONS and 104 "must" be included | Ambiguous in S1. Umbrel's repo has no `Upload-Limit` code but reports successful uploads (weak evidence). Moot for content (§1). |
| Extension "cannot encrypt": secondary FB snippet vs primary API | The primary API surface (S3) confirms no body hook (High). "No workaround" stays Medium until B4-S2. |

### Alternatives compared

| Option | Fit with settled requirements | Pros | Cons | Evidence |
|---|---|---|---|---|
| **A. iOS in v1** | Matches CLAUDE.md; contradicts ADR-0002 §4 and §5 (no signing spend) | Phones first-class; camera rolls covered natively | 99 USD/yr now, plus a Mac; a Swift app + BG task plumbing on the critical path; steady-state background weak (force-quit, discretionary); BUD-TTS unproven; K10 conflict must be settled first; 90-day TestFlight chore or App Review | C5–C9, C13–C17 |
| **B. iOS after pilot, with a bridge** (recommended, gated) | Matches ADR-0002 §4; needs a CLAUDE.md amendment | Core built iOS-ready now (K1–K14) at low cost; pilot proves the protocol on desktop + Android first; iPhone photos still protected through a desktop bridge where one exists | Relatives without a Mac/PC get no iPhone coverage until iOS ships; the bridge adds a desktop dependency | C10, C20, C21 |
| **B′. As B, with icloudpd as the bridge** | Conflicts with "files on the device only" and asks relatives to turn ADP off | Works without a family computer | Admin holds relatives' Apple sessions; re-auth every ~2 months; maintainer risk | C20 |
| **C. iOS deferred, no bridge** | Matches ADR-0002; contradicts CLAUDE.md | Cheapest | If iPhones hold much of the family's photos, the main keepsake source is unprotected | E1-S2 pending |
| **(Rejected) PhotoKit extension as the uploader** | Violates ADR-0001 (plaintext to cloud) | System-managed, efficient | See C2, C3, C4 | C2–C4 |
| **(Rejected) Extension → homelab over LAN, TLS only** | Violates "client-side encryption before data leaves the device"; inbound listener | No cloud plaintext | Needs a settled-text change and the P2 LAN transport | C1, C2 |

### Similar work and lessons

| Project | What they do | Borrow or avoid | Source |
|---|---|---|---|
| Ente Photos (E2EE) | Encrypts to a temp file, presigned multipart (20 MiB parts), persists the encryption result so resume uses the same ciphertext; BG modes fetch, processing, remote-notification | Borrow the persisted-resume idea (Reliquary's deterministic regeneration is leaner); note that Ente relies on silent pushes for short windows | S35; Ente help (snippet) |
| Immich iOS | BGAppRefresh (20 s cap) + BGProcessingTask, each booting a headless Flutter engine; uploads via background URLSession | Borrow interleaved phases and newest-first order (PR #28293); avoid an engine boot inside a 20 s window (Option C avoids it) | S34 |
| Nextcloud iOS | PhotoKit extension on iOS 27, WebDAV PUT, ≤ 20 in-flight jobs, fallback to legacy upload | Evidence that the extension is production-viable for **plaintext** servers only | S31, S32 |
| Umbrel | Extension-only uploader, durable ledger, stable resource key | Borrow the ledger and key idea; avoid preferring `fullSize*` over originals | S33 |
| Piwigo, Sushitrain | `BGContinuedProcessingTask` for uploads/sync; Sushitrain runs a Go core under Swift | Precedent for a non-Swift core doing user-started background work | Source scout |
| icloudpd, osxphotos | Pull iCloud or Mac Photos originals | Bridge candidates with the constraints in §6 | S37, S38 |

### Tools and libraries

| Name | Purpose | Licence | Maturity | Source |
|---|---|---|---|---|
| UniFFI (Swift) | Rust ↔ Swift bindings, foreign traits | MPL-2.0 | "Production-quality" Swift; Swift 6 partial | S36 |
| URLSession background configuration | Out-of-process file uploads | Apple SDK | iOS 8+ | S6, S7 |
| BackgroundTasks (`BGProcessingTask`, `BGContinuedProcessingTask`) | Scheduled and user-started background work | Apple SDK | iOS 13+ / 26+ | S9–S11 |
| PhotoKit (`PHAssetResourceManager`, persistent changes, cloud IDs) | Original access, change detection, locators | Apple SDK | iOS 9+ / 16+ / 15+ | S13–S16 |
| CryptoKit | Not needed: the Rust core does all crypto (one implementation, per T1) | Apple SDK | — | client-stack.md |

## Spikes

Placeholder: a separate spike runner is producing these in parallel. This note will be updated with their status.

| Spike | Exec tag | Budget IDs | Data class | Status | Result |
|---|---|---|---|---|---|
| B4-S1 Paper check (extends T1 spike 8) | CT | BUD-TMP, BUD-TTS | PUB → results | (spike runner) | The constraints memo above is this analyst's paper input |
| B4-S2 Minimal app: app-encrypted part files via background URLSession (and extension download-only jobs) to R2 | OL (Mac, iPhone, Apple account, sandbox R2) | BUD-TTS, BUD-TMP, BUD-BAT-D, BUD-REVOKE | SYN → results; LAB for Optimize-Storage assets | (spike runner: kit) | — |
| B4-S3 Interim bridge on one relative's iPhone | FM/OL | BUD-SUPPORT | FAM → AGG (counts, dates-match rate, original vs rendition) | (spike runner: kit) | — |

No emulator stands in for an iPhone. The PhotoKit extension does not run in Simulator (S1).

## Conflicts with settled text

1. **CLAUDE.md "Platforms (v1): … iOS …"** vs **ADR-0002 §4, "iOS: Deferred"**. This is OD-01, the existing conflict (traceability R-03). It is not resolved here.
2. **ADR-0002 §5, "no OS code signing for now"**. Any iOS route requires the paid Apple Developer Program (C13–C17), so choosing iOS in v1 re-opens that spend decision (OD-09).
3. **budgets.md BUD-REVOKE (proposed, not settled)**. The 15-minute outstanding-URL expiry conflicts with iOS discretionary background transfers (K10). Raised to H1 and D3; not changed here.
4. **CLAUDE.md "v1 data sources: files on the device only"**. The icloudpd bridge (B′) would conflict. The desktop bridge (B) does not.

## Open questions

| Question | Who | By when |
|---|---|---|
| iPhone share of camera-roll bytes (E1-S2) | E1 | Before OD-01 sitting 2 (Wave 1 exit) |
| Does the owner have a Mac and an Apple account for B4-S2? Is he willing to pay 99 USD/yr now? | H2 / owner | Wave 1 |
| Does a background URLSession upload to an R2 presigned UploadPart URL expose the `ETag` in the completion's `HTTPURLResponse`? | B4-S2, T1 spike 4 | Before ADR-0021 |
| How long do discretionary background uploads actually wait on a typical family iPhone? This sets the URL lifetime (K10). | B4-S2 | Before ADR-0014 |
| Can extension download-only jobs hydrate Optimize-Storage originals reliably with iCloud Photos on (C4 bug)? Is it fixed in iOS 27? | B4-S2 on iOS 27 | Before any iOS build |
| Is there a suspended-process file-lock hazard for a SQLite DB in an app-group container? (Unverified; relevant only if an extension is added, K11.) | B6 / B4 | Before any iOS extension |
| Ad Hoc profile lifetime, and Developer Mode requirements for Ad Hoc installs | B4 follow-up (Apple primary) | Only if Ad Hoc is chosen |
| Do internal TestFlight builds skip review for App Store Connect users with a minimal role? | B4 follow-up | Only if TestFlight is chosen |
| Exact wording of Apple's Optimize Storage / Download Originals settings (support.apple.com blocked) | H1 (blocked source) | Before the E3 copy deck |

## Recommendation

**For OD-01: option B, "iOS after the pilot, with a desktop-side bridge", gated by E1-S2.** Confidence Medium.

1. **Now (Wave 1):** send the constraints memo K1–K14 to T1 before ADR-0003 is accepted. Raise K10 to D3, C1 and H1, K6 to A5, and K4/K5 to A2 and B5. This keeps iOS cheap to add later and costs little today.
2. **Pilot:** desktop + Android. For relatives with iPhones and a family Mac/PC, turn on iCloud Photos originals sync to that computer. Reliquary protects it there, and the assistant reports "iPhone covered via <computer>". Where there is no computer, the wizard says "not yet" (as ADR-0002 §3 already does) and the health view keeps it visible.
3. **Gate:**
   - If E1-S2 shows **≥ 40 %** of camera-roll bytes on iPhones or iPads, escalate. The recommendation becomes "start the Apple membership and B4-S2 now; ship iOS right after the pilot", because deferring would leave the main keepsake source unprotected.
   - If the owner has no Mac, iOS cannot be built at all, and C becomes the practical fallback.
4. **icloudpd (B′)** is only an owner-approved exception. It needs its own decision, because it touches the v1-source rule and asks relatives to turn ADP off.

**What would change this recommendation:**
- A high iPhone share (above).
- B4-S2 showing that background URLSession meets BUD-TTS without the app being opened. That would make A cheaper than it looks.
- Apple adding a body or encryption hook to the PhotoKit upload job API. That would make the extension the natural uploader.

## Decision requests

### OD-01: iOS in v1, after the pilot, or deferred

- **Needed by:** Wave 1 exit (decision sitting 2).
- **Evidence:** this note; `client-stack.md` (T1 option C); E1-S2 (pending); B4-S2/S3 kits (pending).
- **Options:**

  | Option | What it means for the family | Cost (money and owner time) | Reversibility | Risks |
  |---|---|---|---|---|
  | A. iOS in v1 | iPhones protected from day one | 99 USD/yr + a Mac; a Swift app on the critical path; a TestFlight upload every ≤ 90 days or App Review; K10 decided first | Costly to back out once relatives install it | Weak background on iOS (force-quit, discretionary); BUD-TTS unproven; review friction |
  | B. After the pilot, desktop bridge (recommended) | iPhone photos protected where a family Mac/PC exists; others see "not yet" | No Apple spend until later; small core design cost now (K1–K14) | Easy: move to A at any time | Relatives without a computer stay unprotected for longer |
  | B′. After the pilot, icloudpd bridge | iPhone photos pulled from iCloud to the homelab | Owner re-auth about every 2 months per person | Easy | ADP off for relatives; admin holds Apple sessions; conflicts with the v1-source rule |
  | C. Deferred, no bridge | iPhones unprotected | None | Easy | Main keepsake source may be unprotected (depends on E1-S2) |

- **Recommendation:** B. The core stays iOS-ready at small cost. The pilot proves the protocol on platforms with a good background story, and iPhone photos are still covered through a computer the family already has. Escalate to A if E1-S2 ≥ 40 %.
- **Touches settled text:** yes. The CLAUDE.md "Platforms (v1)" line and ADR-0002 §4 disagree. B or C means amending CLAUDE.md; A means superseding ADR-0002 §4, and probably §5 for the Apple spend (OD-09). **Proposed CLAUDE.md wording for B (for the owner; not applied):**
  > **Platforms:** v1 ships on Windows, macOS, Linux and Android. iOS follows after the family pilot (OD-01, ADR-0004); until then iPhone photos are covered through a family computer that syncs iCloud Photos originals. Phones remain first-class, and the shared core must meet the iOS constraints in `docs/research/b4-ios-decision.md` (K1–K14) so iOS is not precluded.
- **If no decision by the deadline:** assume ADR-0002 §4 (iOS deferred, must not preclude). Adopt K1–K14 anyway. This blocks nothing on the critical path, but it leaves E5's wizard copy and E3's "iPhone" health state provisional.

### Proposed follow-up requests (for H1 to file; not added to the shared queue by this note)

- **K10 vs BUD-REVOKE:** presigned-URL lifetime for iOS background transfers vs the 15-minute outstanding-URL budget. Evidence owner D3; the budget change goes to the owner at H2.
- **icloudpd as a bridge (only if B′ is wanted):** it touches "files on the device only" and asks relatives to disable ADP.

## Hand-offs

| To | What | Why |
|---|---|---|
| T1 (ADR-0003) | K1–K14, especially K1, K2, K7, K12 | Must land before ADR-0003 is accepted (PLAN §1, question 1) |
| A2 (ADR-0007) | K2 (guard at handoff), K3, K4 (sequential sources, regenerate by re-read) | The resume design assumes seekable, stat-able sources |
| A5 (ADR-0016) | K6 (multi-resource items, originals first) | PhotoKit resource roles |
| B5 (ADR-0020) | K4, K5 (seekable flag, opaque version token), PhotoKit locator | Source-plugin interface |
| B6 (ADR-0021) | K3, K7, K9, K11 | Spool, work units, cross-process state |
| D3 / C1 / H1 | K10 vs BUD-REVOKE | Budget conflict |
| E3 / E5 | K13 force-quit health state; "iPhone covered via computer" and "waiting for iCloud download" states; wizard copy | Plain-language health |
| B7 / OD-09 | The Apple membership may also cover macOS Developer ID | Shared spend decision |
| E1 | E1-S2 is the gate for OD-01 | Evidence |
| H1 | Blocked sources: support.apple.com/108782, datatracker, openradar, ente.com, photosync-app.com, nextcloud/ios#4279 via MCP | Run rule §5.4 |
