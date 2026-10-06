# B4. iOS decision and readiness

- **Workstream:** B4 (see `docs/research/PLAN.md`, section "B4.")
- **Status:** Final (Wave 1). Synthesised after three-skeptic review; the claim verdicts come from the computed tally.
- **Date:** 2026-09-29 (last updated 2026-10-06)
- **Feeds:** ADR-0004 (iOS section; owner E2, with B4 input; draft text in Appendix A), ADR-0003 (iOS constraints memo to T1, §3), OD-01. Also inputs to A2/ADR-0007, A3/ADR-0009, A4/ADR-0011, A5/ADR-0016, B5/ADR-0020, B6/ADR-0021, C1/ADR-0010, D3/ADR-0014, D5/ADR-0015, E3/ADR-0024, OD-09.
- **Depends on:** E1-S2 (iPhone share of camera-roll bytes; **not run**), T1 spike 8 (extended here as B4-S1, **run**), H2 (owner intake: Mac and Apple account availability; not answered)
- **Traceability rows closed or advanced:** R-03 (advanced; **the "CONFLICT" status is stale**, see Conflicts §1), R-05 (advanced: constraints memo final for Wave 1), C-06 (input: what the wizard says about iPhones)

## Summary

**The deferral of iOS is already settled.** Since commit `6f9f2bb` (2026-09-29), CLAUDE.md reads "**iOS is deferred** (revisit with the Apple Developer membership), but the client stack must not preclude it". That matches ADR-0002 §4. The CLAUDE.md-vs-ADR-0002 conflict that OD-01, PLAN B4 and traceability R-03 describe no longer exists. What is left for the owner is smaller: confirm the deferral, choose an **interim bridge** for iPhone photos, and set the trigger for **reopening** the deferral. Moving iOS into v1 (option A) would reopen two settled lines, "Platforms" and "Code signing", and needs the owner's explicit consent.

**Recommendation (Medium confidence):**
- Keep iOS deferred, with no change to CLAUDE.md.
- Cover iPhone photos through a family computer: iCloud Photos originals synced to a Mac or PC that Reliquary protects, or a periodic cable import. The health view must report that coverage honestly, as "via <computer>; the iPhone itself is not checked".
- Make the shared Rust core iOS-ready now: the 16 constraints IOS-C1 to IOS-C16 in §3.
- Reopen the deferral only if E1 shows that a material share of the family's iPhone keepsakes cannot be bridged.

**Platform facts (verified against primary sources):**
- The iOS 26.1 PhotoKit background upload extension exists.
- It cannot carry Reliquary content: the system uploads the raw `PHAssetResource` bytes, so it would send plaintext to the cloud and break ADR-0001.
- On iOS, content would go as pre-encrypted part files through a background `URLSession`.

**B4-S1 result.** This spike ran for real, with the iOS side emulated on Linux. Option C (Rust core + UniFFI) is viable as a stack, but the core API needs specific changes. These are now merged into §3.

## Questions

| # | Question | Short answer | Confidence |
|---|---|---|---|
| 1 | OD-01: iOS in v1 or deferred? | Already settled as "deferred, must not preclude" (CLAUDE.md since `6f9f2bb`, and ADR-0002 §4). Recommend keeping it deferred, adding a desktop or cable bridge, and reopening only if E1 finds many unbridgeable iPhone keepsakes. Option A means reopening settled text. | Medium (E1-S2 and B4-S2 not run) |
| 2 | What must the core do now so iOS is not precluded? | 16 constraints, IOS-C1 to IOS-C16 (§3). This merges the analyst's memo with the B4-S1 change list. Several are already in `content-encryption-format.md` (CE) §8.3, §8.6 and E2 and only need confirming in ADR-0007. No new crypto primitive is needed. One iOS-specific storage rule, IOS-C15 (backup exclusion and protection classes), is a precondition of the existing keystream-reuse invariant. | High on the platform facts; Medium on the derived constraints |
| 3 | Does the iOS 26.1 PhotoKit background upload extension exist? | Yes. `PHBackgroundResourceUploadExtension` on iOS/iPadOS 26.1, deprecated in 27.0. The async successor `PHBackgroundResourceUploadJobExtension` is on iOS, iPadOS, macOS and Mac Catalyst 27.0. | High (K1, verified) |
| 4 | Can it upload app-encrypted files to R2 presigned URLs? | No documented way. A job pairs a `PHAssetResource` with a `URLRequest`, and the system uploads the resource's own bytes. It is unusable for content under ADR-0001. Download-only jobs (iOS 26.4+) might still hydrate iCloud originals; B4-S2 tests this. | High that no API exists (K2, verified); Medium that no workaround exists |
| 5 | Other background options | Background `URLSession` (uploads from a file only; survives suspension and system termination; a force-quit cancels everything). `BGProcessingTask` (only while idle). `BGAppRefreshTask` and pushes (≤ 30 s). `BGContinuedProcessingTask` (iOS 26; user-started; Live Activity; must show progress; **also cancelled silently by a force-quit**). | High (K5, K8, K9 verified) |
| 6 | iCloud "Optimize iPhone Storage" | Originals may be only in iCloud. PhotoKit downloads them only with `isNetworkAccessAllowed = true`. Reads are sequential with no byte range. A purged spool part means re-reading the stream, and possibly re-downloading it (IOS-C4). | High on the API (K7); the Apple Support page was blocked |
| 7 | Distribution for 5–15 iPhones | Personal Team: unusable. TestFlight: 90-day builds; the first external build is reviewed. Ad Hoc: UDIDs, 100 per year. Unlisted App Store: full review, no beta apps. Custom apps and the EU marketplace: infeasible. All paid routes also need **export-compliance** answers. | High (K10, verified) |
| 8 | Apple Developer Program implications | 99 USD per membership year. An individual's legal name appears as the App Store seller. Distribution stops if the membership lapses (installed App Store apps keep working). Conflicts with CLAUDE.md "Code signing" and ADR-0002 §5. On iOS the update trust root becomes Apple plus the developer account (Conflicts §3). | High (K10, K11) |
| 9 | Interim bridge and trust-model fit | Desktop or cable bridge: fits encryption and "files on the device", but it cannot verify the iPhone itself. icloudpd at the homelab conflicts with "files on the device only", needs ADP turned off, and means the admin holds the relative's Apple session. | High on icloudpd (K12); Medium on the desktop bridge |
| 10 | (new) Does iOS transfer behaviour conflict with a budget? | Yes. BUD-REVOKE's 15-minute expiry for outstanding URLs vs discretionary background transfers. There are more options than "longer URLs" (IOS-C10). Longer URLs are **not** recommended by default. | Medium (K6 verified; wait times not measured) |
| 11 | (new) Does Apple's "fewer, larger transfers" guidance pressure the formats? | Possibly. Whole-file objects plus a metadata object per file could mean tens of thousands of background tasks. This is open for A2, A4 and C1 (IOS-C16). | Low (not measured) |

## Method

- **Sweep:** three scouts (Apple docs; source code of similar OSS; community and forums), then an analyst deep read.
  - Apple pages were re-fetched as DocC JSON (`developer.apple.com/tutorials/data/documentation/<path>.json`, the same content as the rendered page) or as HTML help pages.
  - Forum threads were read through WebFetch.
  - Nextcloud, Umbrel, UniFFI and icloudpd were read from raw.githubusercontent.com.
- **Skeptics:** three (sources, logic, adversary). They re-read the primary pages on 2026-10-06. The synthesiser re-checked these new quotes on 2026-10-06 against the primary pages:
  - `willBeginDelayedRequest`;
  - "The system cancels any running tasks if a person closes the app in the app switcher";
  - "change your design to perform fewer, larger transfers";
  - Xcode Cloud "25 compute hours/month";
  - the Enroll page's seller-name sentence;
  - the TestFlight "export compliance" help pages (titles only).
- **Spikes:** B4-S1 ran (CT, iOS side emulated on Linux). B4-S2 and B4-S3 are kits.
- **Routes used:** direct HTTPS to developer.apple.com; raw.githubusercontent.com; GitHub MCP code search; WebFetch (Apple forums); Docker Hub's `swift:6.1-noble` image for Swift (download.swift.org was blocked).
- **Blocked sources** (all reported to H1; none silently replaced):
  - support.apple.com/en-us/108782 (Optimize iPhone Storage);
  - datatracker.ietf.org (which resumable-upload draft revision Apple uses);
  - openradar.appspot.com FB23870865 (search snippet only);
  - ente.com help and photosync-app.com (snippets only);
  - GitHub MCP `pull_request_read` on nextcloud/ios#4279 (denied);
  - github.com discussion pages (partial loads);
  - download.swift.org (the Docker Hub image was used instead, and the README says so);
  - the `minio/minio` image pull (moto was used for the kit helper test, labelled "emulated S3, not R2").
- **Not found:** Apple's crash-report docs do not mention `0xdead10cc`, so the app-group file-lock hazard stays an open question.
- **Stop rule:** the skeptics' re-reads added three primary facts that change constraints: `willBeginDelayedRequest`, force-quit cancelling `BGContinuedProcessingTask`, and "fewer, larger transfers". No further sweep was run in Wave 1.

## Sources

| # | Source | Publisher | Published or version date | Accessed | Primary? |
|---|---|---|---|---|---|
| S1 | Uploading asset resources in the background — https://developer.apple.com/documentation/photokit/uploading-asset-resources-in-the-background | Apple | Undated; covers iOS 26.1 and 27.0 | 2026-09-29; skeptics 2026-10-06 | Yes |
| S2 | `PHBackgroundResourceUploadExtension` — https://developer.apple.com/documentation/photos/phbackgroundresourceuploadextension | Apple | iOS 26.1, deprecated 27.0 | 2026-09-29; 2026-10-06 | Yes |
| S3 | `PHAssetResourceUploadJobChangeRequest` — https://developer.apple.com/documentation/photos/phassetresourceuploadjobchangerequest | Apple | iOS 26.1 (`creationRequestForJob` 26.4); macOS 27.0 | 2026-09-29; 2026-10-06 | Yes |
| S4 | `PHAssetResourceUploadJob`, `jobLimit`, `Type` — https://developer.apple.com/documentation/photos/phassetresourceuploadjob | Apple | iOS 26.1 (`downloadOnly` 26.4) | 2026-09-29 | Yes |
| S5 | `PHAssetResourceUploadJobOptions` — https://developer.apple.com/documentation/photos/phassetresourceuploadjoboptions | Apple | iOS 27.0 | 2026-09-29; 2026-10-06 | Yes |
| S6 | `URLSessionConfiguration.background(withIdentifier:)` — https://developer.apple.com/documentation/foundation/urlsessionconfiguration/background(withidentifier:) | Apple | iOS 8.0+ | 2026-09-29; 2026-10-06 | Yes |
| S7 | Downloading files in the background — https://developer.apple.com/documentation/foundation/downloading-files-in-the-background | Apple | Undated | 2026-09-29; 2026-10-06 | Yes |
| S8 | `isDiscretionary` — https://developer.apple.com/documentation/foundation/urlsessionconfiguration/isdiscretionary | Apple | Undated | 2026-09-29; 2026-10-06 | Yes |
| S9 | `BGContinuedProcessingTask` — https://developer.apple.com/documentation/backgroundtasks/bgcontinuedprocessingtask | Apple | iOS, iPadOS, Mac Catalyst 26.0 | 2026-09-29; 2026-10-06 | Yes |
| S10 | Performing long-running tasks on iOS and iPadOS — https://developer.apple.com/documentation/backgroundtasks/performing-long-running-tasks-on-ios-and-ipados | Apple | Undated | 2026-09-29; 2026-10-06 | Yes |
| S11 | `BGProcessingTask` — https://developer.apple.com/documentation/backgroundtasks/bgprocessingtask | Apple | iOS 13.0+ | 2026-09-29 | Yes |
| S12 | Choosing Background Strategies for Your App — https://developer.apple.com/documentation/backgroundtasks/choosing-background-strategies-for-your-app | Apple | Undated | 2026-09-29 | Yes |
| S13 | `PHAssetResourceManager` `requestData(…)`, `writeData(…toFile:…)` — https://developer.apple.com/documentation/photos/phassetresourcemanager | Apple | iOS 9.0+ | 2026-09-29; 2026-10-06 | Yes |
| S14 | `isNetworkAccessAllowed` — https://developer.apple.com/documentation/photos/phassetresourcerequestoptions/isnetworkaccessallowed | Apple | iOS 9.0+ | 2026-09-29; 2026-10-06 | Yes |
| S15 | `PHAssetResourceType` — https://developer.apple.com/documentation/photos/phassetresourcetype | Apple | iOS 9.0+ | 2026-09-29 | Yes |
| S16 | `fetchPersistentChanges(since:)`; `PHCloudIdentifier` — https://developer.apple.com/documentation/photos/phphotolibrary/fetchpersistentchanges(since:) | Apple | iOS 16.0+ / 15.0+ | 2026-09-29 | Yes |
| S17 | Apple Developer Program, What's included — https://developer.apple.com/programs/whats-included/ | Apple | Current page | 2026-09-29; 2026-10-06 | Yes |
| S18 | Compare memberships (now redirects to https://developer.apple.com/help/account/basics/about-your-developer-account) | Apple | Current page | 2026-09-29; 2026-10-06 | Yes |
| S19 | TestFlight overview — https://developer.apple.com/help/app-store-connect/test-a-beta-version/testflight-overview | Apple | Current page | 2026-09-29; 2026-10-06 | Yes |
| S20 | Devices overview — https://developer.apple.com/help/account/devices/devices-overview | Apple | Current page | 2026-09-29; 2026-10-06 | Yes |
| S21 | Unlisted app distribution — https://developer.apple.com/support/unlisted-app-distribution/ | Apple | Current page | 2026-09-29; 2026-10-06 | Yes |
| S22 | Custom apps — https://developer.apple.com/custom-apps/ | Apple | Current page | 2026-09-29 | Yes |
| S23 | Alternative app marketplace in the EU — https://developer.apple.com/support/alternative-app-marketplace-in-the-eu/ | Apple | Current page | 2026-09-29 | Yes |
| S24 | Membership renewal (now redirects to https://developer.apple.com/help/account/membership/renewal) | Apple | Current page | 2026-09-29; 2026-10-06 | Yes |
| S25 | Enroll — https://developer.apple.com/programs/enroll/ | Apple | Current page | 2026-09-29; 2026-10-06 | Yes |
| S26 | Forum 818566 (large videos; no chunking) — https://developer.apple.com/forums/thread/818566 | Apple forums (DTS, PhotoKit engineer) | 2026-03; 2026-06 | 2026-09-29; 2026-10-06 | No |
| S27 | Forum 822256 (extension not scheduled with iCloud Photos on) — https://developer.apple.com/forums/thread/822256 | Apple forums | 2026-04 to 2026-06 | 2026-09-29; 2026-10-06 | No |
| S28 | Forum 685525 "iOS Background Execution Limits" (Quinn, DTS) | Apple forums | 2021-07, updated 2026-01-09 | 2026-09-29 | No |
| S29 | Forum 805554 (BGContinuedProcessingTask expiry; DTS "~30s") | Apple forums | 2025-10/11 | 2026-09-29; 2026-10-06 | No |
| S30 | Forums 807754 and 692514 (BGProcessingTask vs TestFlight; file-backed uploads) | Apple forums | 2025-11; 2021-10 | 2026-09-29 | No |
| S31 | nextcloud/ios @ master : `BackgroundUploadExtension/*.swift`, `NCBackgroundUploadExtensionManager.swift` | Nextcloud | master (2026) | 2026-09-29 | Yes (code) |
| S32 | nextcloud/ios PR #4279 | Nextcloud | Merged 2026-09-17 | 2026-09-29 (summary only) | Yes, summary only |
| S33 | getumbrel/umbrel @ master : `clients/apple/ios/…/BackgroundUploadExtension.swift` | Umbrel | master | 2026-09-29 | Yes (code) |
| S34 | immich-app/immich PR #28293 and `mobile/ios/Runner/Background/*.swift` @ main | Immich | Merged 2026-06-04 | 2026-09-29; 2026-10-06 | Yes |
| S35 | ente-io/ente @ main : `mobile/apps/photos/lib/module/upload/service/{file_uploader,multipart}.dart` | Ente | main | 2026-09-29 | Yes (code) |
| S36 | UniFFI manual @ main : `docs/manual/src/swift/overview.md`, `futures.md`, `foreign_traits.md` | Mozilla | main | 2026-09-29; 2026-10-06 | Yes |
| S37 | icloudpd @ master : `README.md`, `docs/authentication.md` | icloudpd project | master (release v1.32.3) | 2026-09-29; 2026-10-06 | Yes |
| S38 | osxphotos @ main : `README.md` | R. Taylor | main | 2026-09-29 | Yes |
| S39 | cloudflare-docs @ production : `src/content/docs/r2/api/s3/presigned-urls.mdx` | Cloudflare | production | 2026-09-29 | Yes |
| S40 | 9to5Mac, "iOS 26.1 will let third-party apps back up photos in the background" | 9to5Mac | 2025-10-24 | 2026-09-29 (snippet) | No |
| S41 | openradar FB23870865 | openradar | Unknown | Snippet only (blocked) | No |
| S42 | Immich discussions #23358, #25777, #23583; issues #22850, #17576 | Immich community | 2025-10 to 2026-02 | 2026-09-29 | No |
| S43 | Apple forum 776450 (unlisted rejections) | Apple forums | 2025 | 2026-09-29 | No |
| S44 | Forum 819034 (Apple engineer: the extension "will automatically download resources from iCloud Photos") — https://developer.apple.com/forums/thread/819034 | Apple forums | 2026-06 | 2026-10-06 (skeptic) | No |
| S45 | `urlSession(_:task:willBeginDelayedRequest:completionHandler:)` — https://developer.apple.com/documentation/foundation/urlsessiontaskdelegate/urlsession(_:task:willbegindelayedrequest:completionhandler:) | Apple | iOS 11+ (per skeptic) | 2026-10-06 | Yes |
| S46 | App Store Connect help: "Provide export compliance information for beta builds", "Overview of export compliance" (linked from S19; titles seen, bodies not read) | Apple | Current | 2026-10-06 | Yes (unread) |
| S47 | Forum 796915 (DTS: pair continued-processing tasks with a background session) | Apple forums | 2025-08 | 2026-10-06 (skeptic; not re-read) | No |
| S48 | `docs/research/content-encryption-format.md` (T1 spike 2): §8.3, §8.5, §8.6, §12.1 R-1, §12.2 E2 | Reliquary | 2026-09 | 2026-10-06 | Yes (project) |
| S49 | `spikes/B4-S1/README.md` and `evidence/` | Reliquary (B4-S1) | Run 2026-09-29 | 2026-10-06 | Yes (measured) |

## Claims

### Key claims (three-skeptic tally, computed)

"Upheld" means the skeptic did not refute the claim. Verdicts are exactly as computed: verified = a primary source, and at least 2 of 3 skeptics did not refute; secondary-only = no primary source; contested = otherwise.

| # | Claim | Sources | Skeptic 1 (sources) | Skeptic 2 (logic) | Skeptic 3 (adversary) | Verdict |
|---|---|---|---|---|---|---|
| K1 | The PhotoKit Background Resource Upload extension exists: `PHBackgroundResourceUploadExtension` on iOS/iPadOS 26.1 (deprecated 27.0), and `PHBackgroundResourceUploadJobExtension` on iOS, macOS and Mac Catalyst 27.0. It is not available in Simulator and needs full library access. | S1, S2 | Upheld | Upheld | Upheld | **Verified** |
| K2 | A job is (`PHAssetResource`, `URLRequest`), and the system uploads the resource's own bytes. There is no documented file, data, stream or body-transform hook, so the extension cannot carry app-encrypted content and would send plaintext, violating ADR-0001. | S1, S3, S4 (S41 corroborates; blocked) | Upheld | Upheld | Upheld; the adversary asks B4-S2 to probe whether a body set on the destination `URLRequest` is ignored | **Verified** |
| K3 | An Apple PhotoKit engineer (June 2026): the extension "does not support chunking"; recommends the resumable-upload protocol. DTS (March 2026), not the engineer, said "sticking with your custom NSURLSession implementation is the right call" (and did not say "background"). | S26 | Upheld; attribution split as stated here | Upheld | Upheld | **Secondary only** |
| K4 | *As drafted:* the extension is never scheduled when iCloud Photos is on (iOS 26.4); Apple called it a bug. *Corrected reading:* one developer's report on iOS 26.4, not reproduced by Apple. DTS said it "looks like a bug rather than intentional behavior"; an engineer said iCloud Photos "should have no bearing" and asked for a Feedback report. Fix status unknown. Counter-evidence: S44, and Nextcloud and Umbrel ship the extension. | S27 (S44 counter) | Refuted (overgeneralised) | Refuted | Refuted | **Contested.** Used only as a B4-S2 test item, never as support. |
| K5 | Background `URLSession` supports uploads from a file only ("uploads from data instances or a stream fail after the app exits"). A user force-quit cancels all of the session's background transfers and blocks relaunch until the user opens the app. | S6, S7 | Upheld | Upheld | Upheld | **Verified** |
| K6 | Transfers started in the background are always discretionary. A rate limiter delays tasks started from the background, and the delay grows with each relaunch and resets on foreground. So a URL signed at handoff can **expire before iOS sends it** (BUD-REVOKE, 15 min). The rate-limiter text speaks of downloads; applying it to uploads is an inference. "May wait hours" is not measured. | S7, S8, budgets.md | Upheld (wording fixed as here) | Upheld | Upheld | **Verified** (upload extension of the rate limiter: inference) |
| K7 | PhotoKit `requestData` and `writeData` are sequential with no byte range, and download from iCloud only if `isNetworkAccessAllowed = true` (the default `false` errors). Rebuilding a purged part therefore means re-reading from offset 0, or using a plaintext temp copy, **or** an `AVURLAsset` file URL for video (CE §8.6; readability for originals unverified). Keeping ciphertext parts in the spool until their ETag is journaled avoids rebuilding. | S13, S14, S48 | Upheld | Upheld (consequence was incomplete; completed here) | Upheld | **Verified** |
| K8 | `BGContinuedProcessingTask` (iOS, iPadOS, Mac Catalyst 26.0) is submitted from the foreground in response to a person's action. It shows a cancellable Live Activity, may use the network and heavy CPU, and low-progress tasks are terminated first. DTS (secondary): about 30 s without progress counts as stalled. **Added from S10:** "The system cancels any running tasks if a person closes the app in the app switcher, but the app doesn't receive an indication of cancellation". | S9, S10, S29 | Upheld | Upheld | Upheld | **Verified** (30 s figure: secondary) |
| K9 | `BGProcessingTask` runs only while idle and is terminated when the user starts using the device. `BGAppRefreshTask` and background pushes get up to 30 s. Immich **reports** (does not measure) a 20 s refresh budget, in which sync and hashing starved the enqueueing of backup candidates. | S11, S12, S34 | Upheld (wording fixed) | Upheld (wording fixed) | Upheld (wording fixed) | **Verified** |
| K10 | 99 USD per membership year. Personal Team: 3 devices, 7-day profiles. TestFlight: up to 90 days per build; up to 100 internal and 10,000 external testers; the first build to a group is reviewed. Ad Hoc: 100 devices per product family per membership year. Unlisted: full App Review; declined if beta. | S17–S21 | Upheld (export compliance missing; added in §5) | Upheld (also conflicts with CLAUDE.md "Code signing") | Upheld | **Verified** |
| K11 | If a non-Enterprise membership expires, apps are no longer downloadable and no updates can be submitted, but already-installed apps "will still function". This applies to App Store and unlisted installs. TestFlight builds still stop at 90 days. Ad Hoc depends on profile and certificate lifetimes (unverified). | S24 | Upheld (scope caveat added) | Upheld (same) | Upheld (same) | **Verified** |
| K12 | icloudpd needs "Access iCloud Data on the Web" on and ADP off. Its MFA session lasts "currently two months". It is looking for a maintainer. | S37 | Upheld | Upheld | Upheld | **Verified** |
| K13 | *As drafted:* UniFFI Swift is production-quality, but a Rust panic becomes an uncatchable fatal Swift error; Swift 6 support is partial; there is no built-in async cancellation. *Corrected reading (same primary):* panics surface as a catchable `Error` in **throwing** functions and are fatal only in **non-throwing** ones (or with `panic = "abort"`). The other parts are confirmed. | S36 | Refuted (panic half) | Refuted (panic half) | Refuted (panic half) | **Contested.** IOS-C12 uses the corrected reading. The cancellation half (upheld by all three) supports IOS-C7 together with B4-S1's measurement. |
| K14 | *As drafted:* T1 option C fits iOS "without change", provided K1–K14 are adopted; no new crypto. *Corrected:* option C is a viable **stack** for iOS (B4-S1: bindings compile in Swift 5 and 6 modes; the core cross-compiles). The **core API** needs the IOS-C list. "No new crypto primitive" holds only together with IOS-C15 (backup exclusion and protection classes, CE R-1). | S48, S49, S7 | Refuted (as stated) | Refuted | Refuted | **Contested.** The ADR-0003 input in §3 rests on B4-S1's measured results and on K5, not on K14. |

### Supporting claims (primary sources; not part of the skeptic tally, so not load-bearing alone)

| # | Claim | Source | Note |
|---|---|---|---|
| P1 | One asset has several resources: originals (`.photo`, `.video`, `.pairedVideo`, `.alternatePhoto`), edits (`.fullSize*`) and adjustment data. | S15 | Used by IOS-C6 |
| P2 | `PHCloudIdentifier` (iOS 15+) works across devices; persistent change tokens (iOS 16+) can expire. | S16 | Used by IOS-C5 |
| P3 | Organisation enrollment needs a legal entity and a D-U-N-S number. For an individual, "Your name will be displayed as the seller name of your apps on the App Store." | S25 (re-checked 2026-10-06) | §5 |
| P4 | Custom apps need Apple Business or School Manager. The EU marketplace needs organisation enrollment plus a financial qualification. | S22, S23 | Rules those routes out |
| P5 | Under Optimize Mac Storage, originals may be missing from a Mac Photos library. | S38 | Bridge risk |
| P6 | `willBeginDelayedRequest` "is called when a background session task with a delayed start time (as set with the `earliestBeginDate` property) is ready to start", and should be implemented "if the request might become stale while waiting … and needs to be replaced by a new request". | S45 (re-checked 2026-10-06) | Documented only for `earliestBeginDate` tasks; whether it fires for discretionary deferral is unknown (IOS-C10) |
| P7 | "If you find you need to launch thousands of download tasks, change your design to perform fewer, larger transfers." | S7 (re-checked 2026-10-06) | IOS-C16 |
| P8 | The membership "includes 25 compute hours/month" of Xcode Cloud. | S17 (re-checked 2026-10-06) | A Mac is not strictly needed to build |
| P9 | Nextcloud iOS ships the extension only on iOS 27 with server v35+, using a WebDAV PUT destination and at most `min(jobLimit, 20)` jobs in flight. | S31, S32 | Similar work |

## Findings

### 1. The PhotoKit background upload extension (K1–K4)

- **It exists and is the platform's direction** (High; K1).
  - iOS 27 made it async, added macOS and Mac Catalyst, and added `preventsExpensiveNetworkAccess` (S5).
  - Production adopters: Nextcloud (iOS 27 only), Umbrel (its only uploader), and YAIIU for Immich. Immich itself has not adopted it.
- **It cannot carry Reliquary content** (High that no API exists, K2; Medium that no workaround exists).
  - The app chooses only the destination URL and headers; the system sends the resource bytes.
  - Pointed at R2 or a Worker, it sends plaintext to Cloudflare, which violates ADR-0001.
  - Pointed at the homelab over the LAN, it violates "client-side encryption before data leaves the device" and needs the P2 LAN transport. Rejected.
- **Possible uses left for B4-S2:**
  - `downloadOnly` hydration of iCloud-only originals (iOS 26.4+). S44 (secondary) says upload jobs auto-download from iCloud.
  - Whether the extension can run the Rust core and start its own `URLSession` is undocumented (kit step A8).
- **Maturity risk** (Medium).
  - One unreproduced report says the extension was never scheduled with iCloud Photos on (K4, **contested**; restated as above).
  - Early adopters struggled to get `process()` called (S26, S27).
  - Job, runtime and memory limits are undocumented.
  - The kit's A7 step (iCloud Photos on vs off) decides it.
  - This risk is **not** used to reject download-only hydration. It is only a reason to test before relying on it.

### 2. Background execution model if iOS is built (K5–K9)

- **Content path:** the core writes ciphertext part files, and Swift hands them to one background `URLSession` using `uploadTask(with:fromFile:)` (K5).
  - Create the bulk of tasks while the app is **in the foreground**, with `isDiscretionary = false`. Apple forces discretionary mode only for tasks started in the background (K6, S8).
  - Whether tasks created during a `BGContinuedProcessingTask` count as started in the background is unknown. DTS endorses pairing the two (S47, secondary). B4-S2 must test it.
- **"Back up now" and the seed:** `BGContinuedProcessingTask` with byte-level progress (K8).
  - A swipe-away cancels it **silently** (K8, S10). It must be reconciled on the next launch, just like URLSession orphans (IOS-C9, IOS-C13).
- **Steady state:** `BGProcessingTask` (idle, often overnight) plus refresh (≤ 30 s; Immich reports about 20 s) for detection, hashing and enqueueing, in interleaved slices (K9).
  - Each foreground open resets the rate limiter (K6). An occasional "open Reliquary" nudge is therefore a legitimate iOS steady-state tool (E3).
- **Force-quit is the largest steady-state risk for non-technical users** (K5, K8). The client cannot promise progress after a swipe-away. Health must come from the server's view of the device's last check-in (IOS-C13).
- **BUD-TTS on iOS is unknown.** No source measures it; B4-S2 Part B must.

### 3. Constraints memo to T1 (input to ADR-0003; final for Wave 1)

These are requirements on the shared Rust core and formats. They merge the analyst memo with the B4-S1 change list (S49, items 1–11). They are renamed **IOS-C** to avoid a clash with the key-claim IDs.
- "In CE" means `content-encryption-format.md` already says it: confirm it in ADR-0007, nothing new.
- "B4-S1 n" means item n of the spike's list, which was exercised in the emulated run.

| ID | Constraint | Evidence | Status | Touches |
|---|---|---|---|---|
| IOS-C1 | **Produce and transfer are separate.** The core can write each upload unit (one multipart part or one single-PUT object) as a closed, fsynced ciphertext file in a spool, then stop. It never *requires* a streamed request body. Desktop and Android may keep in-process streaming. | K5; B4-S1 1 (scenarios A–I) | New API mode | T1, B6, A2 |
| IOS-C2 | **The release rule covers the spool.** No ciphertext enters the spool until CE §8.3 holds (tag equals the journal, or the tag is journaled). After handoff, `nsurlsessiond` may send the file while the app is gone. | K5; CE §8.3 ("the network, a shared temp file or the spool") | In CE: confirm | A2 |
| IOS-C3 | **Bounded spool, budgeted work units.** `produce_parts` streams forward once per wake and writes as many consecutive parts as a byte budget allows, then all of them are enqueued. Plaintext plus ciphertext temp data stays within **BUD-TMP**. The spool lives in **Application Support, not Caches**, which iOS may purge. Arithmetic, not measured: 2 GB ÷ 5,244,160 B ≈ 380 parts at most. | K6; B4-S1 2, 6 (spool peak = budget, never above) | New API | B6, A2 |
| IOS-C4 | **Forward-only sources and read amplification.** The source trait declares whether it can seek. PhotoKit is forward-only (K7). B4-S1 measured **3.50× the file size** in source reads over 5 producing wakes with a 2-part spool. That is the exact sum for 9 parts; CE's S·(w+1)/2 approximation gives 3.0×. A sizing rule is therefore required: (a) prefer random access (`AVURLAsset` file URL for video, CE §8.6; whether originals are readable that way is unverified); otherwise (b) size the spool so a resource completes in ≤ 2 producing wakes; otherwise (c) materialise it with `writeData(toFile:)` when it fits within a BUD-TMP fraction (A2 and B6 pick the fraction). Never re-read an iCloud-only original over a metered network: B4-S2 must measure whether repeated `requestData` re-downloads. | K7; S49 scenario A; CE §8.6 | Partly in CE; sizing rule new | A2, B5, B6 |
| IOS-C5 | **Opaque source version token and a resource-level locator.** Locator `{kind, local_identifier, cloud_identifier?, resource_role, content_version, raw_path?}`. The change check uses an opaque token (asset ID + resource role + modification date) instead of a stat snapshot. | P2; B4-S1 8; ADR-0001 cache-key text | New interface | A1, A2, B5 |
| IOS-C6 | **Multi-resource items, originals first.** The dedup and upload unit is the resource, not the asset. Originals come first; `fullSize*` edits, paired video, RAW+JPEG and adjustment data are separate roles. Do not copy Umbrel's `fullSize`-first choice. | P1; B4-S1 8; Immich #17576 (secondary) | Model input | A5 (ADR-0016), H4 |
| IOS-C7 | **Short, idempotent, cancellable units.** A `CancelToken` is checked per 64 KiB chunk (B4-S1: 486–595 µs cancel latency on x86, **not a phone**). Committed parts survive cancel and SIGKILL. Discovery, hashing and enqueue run as interleaved slices that fit a 20–30 s window, newest first. | K9; K13 (cancellation half, upheld); B4-S1 5 (scenarios B, C) | New API | T1, B6 |
| IOS-C8 | **Byte-level progress** through a `ProgressSink`, emitted at least every few seconds. | K8 | New API | T1, B6 |
| IOS-C9 | **Transfer bookkeeping in the core DB.** Call `mark_enqueued(session, task_id, upload, part)` **before** `resume()`. `record_task_result` is idempotent (B4-S1: 3 of 3 duplicates detected). `reconcile_session(live_task_ids)` runs after every launch (force-quit: 4 of 4 orphans reset), and also covers `BGContinuedProcessingTask` work cancelled without notice. `taskDescription` holds upload/part as a second key. On **NoSuchUpload** (an R2 multipart upload auto-aborts after 7 days, per ADR-0001, for example after a week-long force-quit), ask the Worker for claim status, then restart with a fresh upload (CE §8.5). The returned ETag is compared with the ciphertext MD5; R2's ETag format is still T1 open issue 1. Whether `taskIdentifier` stays unique across relaunches is undocumented (B4-S2). | K5, K8; B4-S1 4, 11; CE §8.5 | New API | B6, A3 |
| IOS-C10 | **The URL can be refreshed.** A queued task whose URL expired returns its part to "spooled" for a fresh URL (B4-S1 scenario D: 5 of 5 re-uploads byte-identical). The *policy* is D3's and C1's to set (decision request 2). The API must support every candidate: re-sign on wake; `earliestBeginDate` + `willBeginDelayedRequest` to swap a stale request (P6); non-discretionary tasks created in the foreground; a Worker-proxied part upload; or longer URL lifetimes only with the preconditions in decision request 2. This must be reconciled with CE E2 ("presigned URL expiry covers queue delay"), which predates BUD-REVOKE. | K6; P6; B4-S1 7; CE E2 | New API; policy open | D3 (ADR-0014), C1 (ADR-0010), H1 |
| IOS-C11 | **Single-writer DB.** If a PhotoKit or share extension is ever added, it only enqueues intents. The suspended-process SQLite lock hazard in an app-group container is unverified. | K1 (app-group storage) | Design rule | B6 |
| IOS-C12 | **Panics.** Every exported function is throwing (returns `Result`). Release profiles keep `panic = "unwind"` (no `abort` for size tuning). No `unwrap` or `expect` on reachable paths. A separate `catch_unwind` is redundant. Foreign traits are `Sendable` (B4-S1: generated protocols require it). | K13 corrected reading; B4-S1 10 | Coding rule | T1, G1 |
| IOS-C13 | **Health survives force-quit.** The server records each device's last check-in, and nudges follow from it. Force-quit cancels both URLSession transfers and `BGContinuedProcessingTask` silently, so the client never claims progress it cannot see. | K5, K8 | Health rule | E3 (ADR-0024/0025), C1 |
| IOS-C14 | **No dependency on system-owned uploads.** Formats and protocol never assume the OS uploads raw assets. The PhotoKit extension, if used at all, only hydrates. | K2 | Design rule | T1, A3 |
| IOS-C15 | **Storage protection and backup exclusion (precondition of the crypto invariant).** The DB, tag journal and spool are marked excluded from backup (`isExcludedFromBackup`). Files use `NSFileProtectionCompleteUntilFirstUserAuthentication` so overnight work runs while locked. Keychain items (K_upload, the device credential) use `kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly`. On launch, the core detects a restored or migrated install and **aborts** in-flight uploads instead of resuming them. Otherwise a restored journal plus a surviving K_upload could reuse a keystream against ciphertext already in R2 (CE R-1). | CE §12.1 R-1, §12.2 E2; B4-S1 6 | In CE (E2) except the restore detection, which is new | A2, D2, B6 |
| IOS-C16 | **Background task count (open).** Apple: avoid "thousands" of tasks; "perform fewer, larger transfers" (P7). Whole-file dedup means one single-PUT object per photo plus a metadata object, so a camera roll could need tens of thousands of tasks and presigned URLs. Options for A2, A4 and C1, decided before the Gate A formats freeze: pack many encrypted objects and records into one staged pack for iOS (reusing the USB bundle format), or a batched single-PUT. B4-S2 should measure the practical limit. | P7 | Open question | A2, A4 (ADR-0011), C1 (ADR-0010) |

**Build-host note (not a platform constraint).** B4-S1's cross-compile with bundled SQLite failed only because cc-rs needs `xcrun`, which a Linux host lacks. iOS builds either link the system `libsqlite3`, or build bundled SQLite on a Mac or Xcode host. The core's SQL must not need a newer SQLite than iOS ships (not checked).

**Net for ADR-0003 (Medium-High).** Option C (Rust core + UniFFI, native shells) is a viable stack for iOS:
- B4-S1 compiled the UniFFI Swift bindings with 0 warnings in both Swift 5 and Swift 6 modes.
- It passed 26 of 26 emulated lifecycle checks.
- It cross-compiled the core and T1's crypto crate for `aarch64-apple-ios`. This was compile-only; nothing was linked or run on Apple hardware.

The **core API is not unchanged**: IOS-C1, C3, C4, C5, C7, C8, C9, C10 and C12 are API or coding requirements. No new crypto primitive is needed, provided IOS-C15 is adopted.

### 4. iCloud "Optimize iPhone Storage" (K7)

- When an original exists only in iCloud, PhotoKit downloads it only with `isNetworkAccessAllowed = true`.
- That download costs time, metered data and BUD-TMP space.
- Reliquary should request the **original** resource roles with network access allowed, only on unmetered networks, and show "waiting to download from iCloud" as a health reason (E3). This is an inference from K7 and P1.
- The Apple Support page on the setting was blocked, so the user-facing wording is unverified.

### 5. Distribution and the Apple Developer Program (K10, K11, P3, P8)

| Route | Needs | Fits 5–15 iPhones? | Recurring chores | Review | Notes |
|---|---|---|---|---|---|
| Personal Team (free) | Mac + Xcode | No: 3 devices, 7-day profiles | Reinstall weekly | None | Unusable |
| TestFlight internal | 99 USD/yr; each relative an App Store Connect user | Yes (≤ 100) | New build every ≤ 90 days; user management | External builds "may require review"; whether internal builds skip review is inferred, not verified | Relatives hold App Store Connect accounts |
| TestFlight external | 99 USD/yr | Yes | New build every ≤ 90 days | First build to a group is reviewed | Easiest install (TestFlight app + link) |
| Ad Hoc | 99 USD/yr; collect UDIDs | Yes (100 per year; slots freed only at renewal) | Collect UDIDs, re-sign; profile lifetime unverified | None | Worst UX for relatives |
| Unlisted App Store | 99 USD/yr; a final, non-beta app | Yes | Normal updates | Full App Review | Best steady-state UX; friction reports (S43, secondary) |
| Custom app / EU marketplace | Organisation (+ MDM or financial qualification) | No | — | — | Infeasible |

Implications:
1. **Every paid route conflicts with CLAUDE.md** ("no Apple or Windows code signing for now") and with ADR-0002 §5. OD-09 would move forward.
2. **Export compliance.** Reliquary ships its own cryptography (age, X25519, ChaCha20-Poly1305). Every TestFlight, App Store or unlisted route asks export-compliance questions (S46: page titles only, bodies not read). The obligations are **not** asserted here; H5 or a B4 follow-up must read Apple's pages before any build.
3. **Seller identity.** Enrolling as an individual shows the owner's legal name as the App Store seller (P3). This matters for an unlisted listing.
4. **Lapse.** Installed App Store or unlisted apps keep working, but no security fix can ship (K11). TestFlight builds stop at 90 days regardless. TestFlight is therefore not a fire-and-forget channel for a keep-forever app.
5. **Update trust root.** On iOS, updates arrive only through Apple's channel, so the trust root is Apple plus the owner's developer account, **not** the project's offline key (Conflicts §3). Account hardening (dedicated Apple Account, hardware security keys, least-privilege App Store Connect roles) becomes a security requirement.
6. **No Mac is a cost, not a blocker.** Xcode Cloud (25 h/month included, P8) or hosted macOS CI (not sourced here) can build and upload. Debugging, device work and B4-S2 realistically need a Mac.
7. **macOS Developer ID overlap.** The draft inferred this from S17, but S17's "Apple-verified Developer ID" sentence concerns identity verification, not the signing certificate. This is **unsourced here** and left to B7/OD-09.

Suggested channel if iOS goes ahead (not decided): TestFlight external for a pilot, then unlisted App Store.

### 6. Interim bridge for iPhone photos (K12, P5)

| Bridge | Trust model | "Files on the device only" | Chores | Risks |
|---|---|---|---|---|
| **Desktop iCloud sync:** the relative's iCloud Photos synced with originals to a Mac (Photos) or PC (iCloud for Windows) that Reliquary protects | Fits: the desktop client encrypts | Fits: the library is that computer's files (B5 decides PhotoKit vs package on macOS) | Owner sets it up; "Download Originals" on; enough disk (roughly the whole library, possibly hundreds of GB) | **Cannot see the iPhone:** iCloud storage full (common on the free tier), sync paused, computer off, or Optimize Mac Storage (P5) / Windows placeholders all leave gaps that look like coverage. Needs the relative's Apple Account signed into Photos or iCloud for Windows **per OS user**. On a shared computer this mixes people and exposes photos to that user. Photos are attributed to the computer, not the phone. A compromised Apple Account can delete items before they are backed up (already-backed-up copies are kept forever). |
| **Cable import:** periodic iPhone-to-computer import (Image Capture or Windows Photos, "keep originals"; later perhaps Reliquary reading the phone over PTP/WPD) into a protected folder | Fits | Fits (copies of the phone's own files) | The relative or owner plugs the phone in on visits | Coverage is only as fresh as the last import. Same attribution issue. No iCloud plan or Apple-session custody needed |
| **icloudpd at the homelab** (B′) | Partly: the relative must turn **ADP off**, and the admin holds their iCloud web session | **Conflicts**: the source is iCloud, a roadmap item | Re-authenticate about every 2 months per person (K12) | Maintainer wanted; Apple web-auth churn; whole-account session at the homelab |
| iCloud Shared Photo Library into a family Mac | Unverified | Unverified | Unverified | Not checked: participant limits, ADP compatibility, whether originals sync. Listed so it is not forgotten |
| None | — | — | — | iPhone keepsakes unprotected until iOS ships |

**Honesty rule for every bridge (input to E3).** Health says "photos synced to <computer> are protected; the iPhone itself is not checked". It adds a staleness signal: the newest photo date seen through the bridge compared with today. It never says "iPhone covered". This keeps the CLAUDE.md promise to tell people plainly what is and is not backed up.

### 7. Scout conflicts resolved

| Conflict | Resolution |
|---|---|
| `BGContinuedProcessingTask` on Mac Catalyst | The primary source (S9) lists iOS, iPadOS and Mac Catalyst 26.0. |
| Force-quit | S6: cancels all background transfers. S10: also cancels continued-processing tasks silently. |
| Nextcloud gating (PR title vs master) | Master gates on iOS 27 and server v35. The reason is unverified. |
| Non-resumable server as extension destination | Ambiguous in S1. Moot for content. |
| "Apple confirmed an iCloud-Photos bug" (draft) | Overstated. One unreproduced report (K4, contested). |
| CLAUDE.md lists iOS in v1 (draft, PLAN, decision queue, traceability) | Stale. CLAUDE.md has deferred iOS since `6f9f2bb` (checked in `git log`, 2026-10-06). |

### Alternatives compared

| Option | Fit with settled requirements | Pros | Cons | Evidence |
|---|---|---|---|---|
| **C. Keep deferral, no bridge** (status quo) | Matches CLAUDE.md and ADR-0002 §4 | No cost, no text change | iPhone keepsakes unprotected until iOS; size depends on E1-S2 | — |
| **B. Keep deferral + desktop/cable bridge** (recommended) | Matches; the bridge reads files on a computer. The owner sets it up (admin configuration, not end-user) | Covers iPhone photos where a computer exists; the core is built iOS-ready now | Cannot verify the phone; per-person Apple sign-in on the computer; iCloud storage plan; attribution | K12, P5; §6 |
| **B′. Keep deferral + icloudpd exception** | Conflicts with "files on the device only" | Works without a family computer | ADP off; admin holds Apple sessions; re-auth every ~2 months; maintainer risk | K12 |
| **A. Reopen: iOS in v1** | **Reopens** CLAUDE.md "Platforms" and "Code signing", and ADR-0002 §4/§5. The update trust root departs from the offline-key rule | Phones covered natively | 99 USD/yr; a Swift app and background plumbing on the critical path; force-quit and discretionary weaknesses; BUD-TTS unproven; IOS-C10 policy first; 90-day TestFlight or App Review; export compliance | K5–K11 |
| (Rejected) PhotoKit extension as uploader | Violates ADR-0001 | System-managed | Plaintext to cloud | K2 |
| (Rejected) Extension to homelab over LAN, TLS only | Violates client-side encryption; inbound listener | — | Needs the P2 LAN transport | K2 |

### Similar work and lessons

| Project | What they do | Borrow or avoid | Source |
|---|---|---|---|
| Ente Photos (E2EE) | Encrypt to a temp file; presigned multipart (20 MiB); persist the encryption result | Borrow persisted resume (Reliquary regenerates deterministically) | S35 |
| Immich iOS | Refresh (~20 s, reported) + processing, each booting a Flutter engine; background URLSession | Borrow interleaved phases and newest-first order; avoid engine boot in short windows | S34 |
| Nextcloud iOS | Extension on iOS 27, WebDAV PUT, ≤ 20 jobs | Viable only for **plaintext** servers | S31, S32 |
| Umbrel | Extension-only uploader, durable ledger | Borrow the ledger; avoid `fullSize`-first | S33 |
| Piwigo, Sushitrain | `BGContinuedProcessingTask`; Sushitrain runs a Go core | Precedent for a non-Swift core (source scout; not re-read) | — |
| icloudpd, osxphotos | Pull iCloud or Mac originals | Bridge candidates (§6) | S37, S38 |

### Tools and libraries

| Name | Purpose | Licence | Maturity | Source |
|---|---|---|---|---|
| UniFFI 0.32.2 (Swift) | Rust ↔ Swift bindings, foreign traits | MPL-2.0 | "Production-quality"; Swift 6 partial; used in B4-S1 | S36, S49 |
| rusqlite 0.40 | Core DB (system libsqlite3 on iOS builds from Linux) | MIT | Used in B4-S1 | S49 |
| URLSession background | Out-of-process file uploads | Apple SDK | iOS 8+ | S6, S7 |
| BackgroundTasks | Scheduled and user-started work | Apple SDK | iOS 13+ / 26+ | S9–S11 |
| PhotoKit | Original access, change tokens, cloud IDs | Apple SDK | iOS 9+ / 15+ / 16+ | S13–S16 |
| CryptoKit | Not needed: the Rust core does all crypto | Apple SDK | — | client-stack.md |

## Spikes

| Spike | Hypothesis | Pass → / fail → (decision) | Exec tag | Budget IDs | Data class | Status | Result |
|---|---|---|---|---|---|---|---|
| B4-S1 Paper check with emulated Swift shell (extends T1 spike 8) | The Rust core, driven by a Swift shell through UniFFI, writes pre-encrypted part files, hands them off as files, and records results after relaunch, force-quit or crash | Pass → the change list reaches T1 before ADR-0003 is accepted (PLAN criterion); fail → the stack choice must be revisited for iOS | CT | BUD-TMP (mechanism only) | `SYN → results` | **Pass**: list delivered (§3) | **Emulated:** no Apple SDK, Simulator or device; PhotoKit, nsurlsessiond and R2 were stand-ins. 26 of 26 checks passed in Swift 6 mode and in Swift 5 mode (and again from the repo copy). Spool peak 10,488,320 B equal to the budget, never above. Forward-only reads 3.50× file size. Cancel latency 486–595 µs (x86). Core DB 61,440 B. Bindings: 0 warnings. Staticlibs for `aarch64-apple-ios` (18,026,584 B) and `-sim` (18,015,016 B), compile only. Verdict: **core API changes needed** (§3). Not measured: BUD-TTS, BUD-BAT-D, BUD-HASH. Evidence: `spikes/B4-S1/README.md`, `spikes/B4-S1/evidence/` |
| B4-S2 Minimal iOS app: extension probe; core + background URLSession to sandbox R2; continued processing; overnight; battery | H-A: the extension sends raw bytes only. H-B: core part files via background URLSession reach R2 presigned parts while the app is suspended, within BUD-TTS/BUD-TMP. H-C: `BGContinuedProcessingTask` carries "back up now" | Pass → iOS architecture = core + background URLSession; extension at most for hydration. Fail (H-B) → iOS cannot meet BUD-TTS unattended, which strengthens keeping the deferral. Surprise (H-A wrong) → re-evaluate the extension | OL (+SB for R2) | BUD-TTS, BUD-TMP, BUD-BAT-D, BUD-BAT-S, BUD-REVOKE | `SYN+LAB → results` (test Apple Account) | **Kit-ready** | Kit: `docs/research/kits/B4-S2/README.md`. Helpers tested in the container: `probe_server.py` (curl self-test) and `presign_parts.py` (against moto, **emulated S3, not R2**: ETag = MD5, SHA-256 matched). Swift sketches **not compiled**. Needs a Mac, an iPhone and an account |
| B4-S3 Interim bridge on one relative's iPhone | A 500-photo sample arrives through a bridge as originals, with correct dates | Pass → bridge B is viable for the pilot; fail → C (or B′ if the owner approves) | FM/OL | BUD-SUPPORT, BUD-TTS | `FAM → AGG` (`bridge_check.py` prints aggregates only) | **Kit-ready** | Kit: `docs/research/kits/B4-S3/README.md`. `bridge_check.py` self-test on SYN JPEGs gave the expected counts (12 vs 6 full vs reduced; 6 download-time mtimes; 5/3/2 identical/altered/missing). Variant H (icloudpd) forbids deleting or rewriting flags. Needs a relative, their Apple Account and consent |

**Kit addenda required before the owner runs them.** These come from skeptic review; the kits were not edited in this stage, so the B4 spike runner applies them in Wave 2.
- **B4-S2:**
  - (i) Set `earliestBeginDate`, implement `willBeginDelayedRequest`, and record whether it fires for discretionary deferral and whether that wake can fetch a fresh URL.
  - (ii) Compare tasks created in the foreground with `isDiscretionary = false` against tasks created during `BGContinuedProcessingTask`.
  - (iii) Measure whether repeated `requestData` on an Optimize-Storage asset re-downloads.
  - (iv) Test `AVURLAsset` random-access reads of an original-version video.
  - (v) Force-quit during a running `BGContinuedProcessingTask`, then reconcile.
  - (vi) Find the practical limit on the number of background tasks (IOS-C16).
  - (vii) Probe whether a body set on the destination `URLRequest` is ignored.
  - (viii) Device backup and restore of the test app: does IOS-C15's restore detection fire?
  - (ix) Record which export-compliance questions App Store Connect asks at upload.
- **B4-S3:**
  - (i) **Do not run Variant H until decision request 3 is answered "yes".**
  - (ii) Add a coverage check: asset count on the phone vs on the computer.
  - (iii) Add a disk-needed estimate, the iCloud storage-plan check and the per-OS-user account setup.

## Conflicts with settled text

1. **None on platforms, unless option A is chosen.**
   - CLAUDE.md "Platforms (v1)" (since `6f9f2bb`) and ADR-0002 §4 both say iOS is deferred and must not be precluded.
   - The "CONFLICT" recorded for OD-01 in PLAN §4.3, `decision-queue.md` and `traceability.md` R-03 is stale. H1 should correct them; this note does not edit them.
   - E2's ADR-0004 draft (Appendix A of `e2-v1-scope-metrics-pilot.md`) also says "Adopting the iOS row needs a CLAUDE.md amendment"; that sentence is stale as well.
2. **Option A reopens settled text.**
   - It changes CLAUDE.md "Platforms (v1)" and "Code signing: no Apple … code signing for now", and supersedes ADR-0002 §4 and §5 (OD-09).
   - It needs the owner's explicit consent, not a reconciliation.
3. **The iOS update channel vs "self-updates must be signed with the project's own offline key".**
   - On iOS, only Apple's channels install updates, so the offline key cannot be the gate.
   - If iOS is ever built, D5 (ADR-0015) must define either an accepted exception with account-hardening requirements, or an in-app check of signed core and config payloads. This affects Google Play too; B3 and D5 should handle both together.
4. **"Devices can only append; treat the cloud API as under attack" vs longer-lived iOS URLs.**
   - A long-lived presigned single-object PUT lets whoever holds it overwrite the staging object until it expires. A key unique per upload (CE §8.5) does not stop a replay to the same key before the homelab pulls it.
   - BUD-REVOKE itself is only proposed.
   - Hence decision request 2 does **not** recommend longer URLs by default.
5. **"V1 data sources: files on the device only".** icloudpd (B′) conflicts. The desktop and cable bridges do not.
6. **"End users should never touch configuration".** A desktop bridge needs Apple Account sign-in and Photos settings on a family computer. That is acceptable only if the owner does it as admin setup, and the B4-S3 kit should record who did what.

## Open questions

| Question | Who | By when |
|---|---|---|
| Share of camera-roll bytes, and of **people**, whose iPhone keepsakes cannot be bridged (no family computer, no iCloud Photos) | E1 (E1-S2; census) | Before OD-01 sitting 2 |
| Does the owner have a Mac and an Apple Account? Is Apple spend acceptable (Q-B8)? | H2 / owner | Wave 1 |
| Is the ETag exposed in a background task's `HTTPURLResponse` for an R2 UploadPart? R2 ETag format? | B4-S2; T1 spike 4 | Before ADR-0021 |
| Real discretionary queue delay on family iPhones; does `willBeginDelayedRequest` fire for it? | B4-S2 | Before ADR-0014 |
| Practical limit on background task count; is packing needed (IOS-C16)? | B4-S2; A2, A4, C1 | Before Gate A formats freeze |
| Does repeated `requestData` re-download iCloud-only originals? Is `AVURLAsset` readable for originals? | B4-S2 | Before ADR-0007 |
| Can `downloadOnly` jobs hydrate originals with iCloud Photos on (K4, contested)? | B4-S2 (A7, A9) | Before any iOS build |
| Can the extension run the Rust core and start its own URLSession? | B4-S2 (A8) | Before any iOS extension |
| App-group SQLite lock hazard for suspended processes | B6 / B4 | Before any iOS extension |
| Ad Hoc profile lifetime; Developer Mode for Ad Hoc; whether internal TestFlight builds skip review | B4 follow-up (Apple primary) | Only if those routes are chosen |
| Export-compliance obligations for an app with its own crypto (TestFlight and App Store) | H5 / B4 follow-up, reading Apple's pages | Before any iOS upload |
| Does iCloud Shared Photo Library work as a bridge (limits, ADP, originals)? | B4 follow-up | Only if bridge B lacks coverage |
| Wording of Apple's Optimize Storage / Download Originals settings (support.apple.com blocked) | H1 | Before the E3 copy deck |
| Which resumable-upload draft revision Apple implements (datatracker blocked) | H1 | Only if the extension is used |

## Recommendation

**OD-01: keep iOS deferred, as settled, with a bridge (option B).** Confidence Medium.

1. **Now (Wave 1), whatever the owner decides:**
   - Send IOS-C1 to IOS-C16 to T1 before ADR-0003 is accepted, and the relevant items to A2, A3, A4, A5, B5, B6, C1, D2 and D3 (see Hand-offs).
   - The cost today is a handful of API shapes and rules, which B4-S1 shows are implementable.
2. **Pilot (desktop + Android):**
   - Where a relative has an iPhone and a family computer, the owner sets up iCloud Photos originals sync, or periodic cable import, to that computer.
   - Health reports it as "via <computer>; iPhone not checked", with a staleness signal.
   - Where there is no computer, the wizard says "not yet" (ADR-0002 §3).
3. **Reopen trigger (an owner request, not automatic):**
   - Ask the owner to reopen the deferral (option A) if E1 shows a material share of iPhone keepsakes, by bytes or by people, that no bridge can cover.
   - PLAN (line 1176) proposes "≥ 40 % of camera-roll bytes on iPhones". That number has no derivation in B4's evidence and measures the wrong thing (bridged bytes are not at risk). It is the owner's to set; B4 suggests gating on unbridgeable bytes or people instead.
   - Reopening also requires the Apple spend (OD-09), an iOS update-trust-root decision (D5) and the URL-lifetime policy (decision request 2).
4. **icloudpd** is an opt-in exception only, decided separately (decision request 3).
5. **Never** use the PhotoKit extension as the content uploader (K2). Download-only hydration stays a B4-S2 question.

**What would change this:**
- E1 finding many unbridgeable iPhone keepsakes.
- B4-S2 showing that background URLSession meets BUD-TTS without the app being opened (A becomes cheaper).
- Apple adding a body or encryption hook to upload jobs.
- The owner buying the Apple membership anyway for macOS (B7/OD-09), which lowers A's marginal cost.

## Decision requests

### OD-01 (reframed): confirm the iOS deferral, choose the interim bridge, and set the reopen trigger

- **Needed by:** Wave 1 exit (decision sitting 2).
- **Settled position:** "iOS is deferred (revisit with the Apple Developer membership), but the client stack must not preclude it" (CLAUDE.md since `6f9f2bb`; ADR-0002 §4).
- **Evidence:** this note; `client-stack.md`; B4-S1 (run); E1-S2 (pending); B4-S2 and B4-S3 kits.
- **Options:**

  | Option | What it means for the family | Cost | Reversibility | Settled text |
  |---|---|---|---|---|
  | C. Keep deferral, no bridge | iPhones unprotected until iOS | None | Easy | None changed |
  | **B. Keep deferral + desktop/cable bridge (recommended)** | iPhone photos protected where a family computer exists, shown honestly | Owner setup per relative; disk on the computer; possibly an iCloud plan | Easy | None changed (optional one-line note in ADR-0004, not CLAUDE.md) |
  | B′. Keep deferral + icloudpd exception | Works without a computer | Re-auth about every 2 months per person; ADP off | Easy | Conflicts with "files on the device only" (decision request 3) |
  | A. Reopen: iOS in v1 | Native iPhone backup | 99 USD/yr; Mac or Xcode Cloud; Swift app on the critical path; 90-day TestFlight or App Review; export compliance | Costly once relatives install it | **Reopens** CLAUDE.md Platforms + Code signing; supersedes ADR-0002 §4/§5; update trust root exception (D5) |

- **Recommendation:** B. Adopt IOS-C1 to IOS-C16 under any option. Reopen (A) only on the E1 trigger above; the owner sets the threshold.
- **If no decision by the deadline:** C, the settled status quo, with the constraints adopted. Nothing on the critical path is blocked, but E3's bridge health copy and E5's wizard text stay provisional.

### DR-B4-2 (H1 to number): presigned-URL lifetime for iOS background transfers vs BUD-REVOKE

- **Evidence owner:** D3 (ADR-0014), with C1. Not urgent while iOS is deferred, but the API must support every option (IOS-C10).
- **Options:**
  1. Keep 15 min; re-sign on each wake.
  2. Keep 15 min; `earliestBeginDate` + `willBeginDelayedRequest` swaps stale requests (P6; firing for discretionary deferral unverified).
  3. Keep 15 min; create most tasks in the foreground as non-discretionary, and nudge occasional app opens.
  4. A Worker-proxied part upload authenticated per request. Revocation is then checked at send time, at the cost of Worker CPU and requests, and it departs from ADR-0001's presigned design.
  5. Longer iOS lifetimes. Allowed only if **all** hold: multipart parts only, or a single PUT with a signed conditional (`If-None-Match`) header (R2 support for this on presigned PUTs is unverified); commit checks ETags against the device journal; ingest re-verifies, with a dedup-index rollback path; and BUD-ABUSE has an owner-set value.
- **Recommendation:** options 2 and 3, with 1 as the fallback, measured in B4-S2. Option 5 is not a default. Reconcile with CE E2.

### DR-B4-3 (H1 to number; only if B′ is wanted): icloudpd at the homelab as an interim iPhone source

- **Options:** no (desktop or cable bridge only); yes, as a time-limited, opt-in, per-relative exception with written consent; yes, generally.
- **Recommendation:** no by default. Allow it only per relative, time-limited, with consent, and only for relatives with no family computer.
- B4-S3 Variant H must not run before a "yes".

### DR-B4-4 (H1 to number; conditional on option A): iOS update trust root

- **Question:** accept Apple's distribution channel as the iOS update trust root, which is an exception to the offline-key rule, with mandatory developer-account hardening? Or require in-app verification of payloads signed with the offline key, on top of Apple's channel?
- **Evidence owner:** D5 (with B3 for Play).
- **Recommendation:** decide together with Play, under ADR-0015.

## Hand-offs

| To | What | Why |
|---|---|---|
| T1 (ADR-0003) | IOS-C1, C3–C5, C7–C10, C12; the "stack viable, API changes needed" net | Must land before ADR-0003 is accepted |
| A2 (ADR-0007) | IOS-C2 and C15 (confirm the CE text, add restore detection); C4 sizing rule; C16 | Release rule, R-1, read amplification |
| A3 (ADR-0009) | IOS-C9 (NoSuchUpload / 7-day auto-abort, reconcile); C14 | Protocol states |
| A4 (ADR-0011), C1 (ADR-0010) | IOS-C16 packing vs task count; conditional PUT question | Gate A/B formats and key layout |
| A5 (ADR-0016) | IOS-C6 | Resource roles |
| B5 (ADR-0020) | IOS-C4, C5 | Source interface |
| B6 (ADR-0021) | IOS-C3, C7, C9, C11, C15; build-host SQLite note | Client engine |
| D2 (ADR-0008) | IOS-C15 keychain accessibility classes | Key custody |
| D3 / C1 / H1 | DR-B4-2 (URL lifetime vs BUD-REVOKE) | Budget conflict |
| D5 / B3 (ADR-0015) | DR-B4-4: update trust root on Apple and Play channels | Settled offline-key rule |
| E1 | Measure unbridgeable iPhone bytes **and** people (family computer, iCloud Photos use) | OD-01 trigger |
| E2 (ADR-0004) | Lift Appendix A; remove "needs a CLAUDE.md amendment" from the iOS row | Stale premise |
| E3 / E5 | Bridge honesty rule and staleness signal; force-quit health; "waiting for iCloud download"; open-the-app nudge | Plain-language health |
| B7 / OD-09 | The Developer ID overlap needs a proper Apple primary source | Unsourced here |
| H5 | Export-compliance obligations (Apple primary) | Any iOS upload |
| H1 | Correct OD-01 / R-03 / PLAN B4 framing; file DR-B4-2 to 4; blocked sources listed in Method | Run rules §5.4 |

## Appendix A. Draft text for the iOS section of ADR-0004 (for E2 to lift; Proposed)

> **iOS (platforms).** iOS stays **deferred**, as settled in CLAUDE.md and ADR-0002 §4. The shared Rust core meets the iOS constraints IOS-C1 to IOS-C16 (`docs/research/b4-ios-decision.md` §3) from the start, so iOS is not precluded.
>
> **Interim coverage.** Until iOS ships, iPhone photos are protected through a family computer that Reliquary already covers, either by iCloud Photos originals sync set up by the owner or by periodic cable import. The health view reports this as "via <computer>; the iPhone itself is not checked", with a staleness signal. It never reports "iPhone covered". The icloudpd route is excluded unless the owner grants a per-relative exception (DR-B4-3).
>
> **Reopening.** The owner revisits the deferral if E1 shows a material share of iPhone keepsakes, by bytes or by people, that no bridge covers (threshold set by the owner; PLAN's placeholder is 40 % of camera-roll bytes). Reopening is a change to settled text: CLAUDE.md "Platforms" and "Code signing", and ADR-0002 §4/§5. It requires the Apple Developer Program (OD-09), an iOS update-trust-root decision (ADR-0015) and a presigned-URL lifetime policy for background transfers (ADR-0014).
>
> **If built.** Content uploads go as pre-encrypted part files through a background `URLSession`. "Back up now" and the seed use `BGContinuedProcessingTask`, and steady state uses `BGProcessingTask` plus refresh. The PhotoKit background upload extension is never the content uploader (it sends plaintext); at most it hydrates iCloud originals. Distribution: TestFlight external for a pilot, then unlisted App Store (to be confirmed).
>
> **Evidence:** K1, K2, K5–K12 (verified); B4-S1 (run, emulated). B4-S2 and B4-S3 (kits) confirm on hardware.
