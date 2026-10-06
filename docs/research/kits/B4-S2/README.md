# Kit B4-S2: minimal iOS app uploads app-encrypted parts to R2 in the background

- **Spike:** B4-S2 (workstream B4, see `docs/research/PLAN.md`)
- **Exec tag:** OL (needs a Mac, an iPhone and an Apple account). Parts A6 and B use the H1 **sandbox** Cloudflare account (SB).
- **Prepared by / date:** B4 spike runner (agent), 2026-09-29
- **Who runs it:** Owner
- **Time needed:** about 1 day hands-on (Xcode setup, parts A–C), plus 3–7 days of waiting (overnight runs in part D, two 24 h battery days in part E, TestFlight processing if used)
- **Data-handling class:** `SYN+LAB → results`. No family data. Use a **test Apple Account** and LAB shots only (H3 rule R8: no people, no home, location off). The PhotoKit extension uploads **raw, unencrypted** bytes, so it may only ever point at the LAN probe server or the sandbox bucket.

## Purpose

Find out, on real hardware, which iOS background path can carry Reliquary's encrypted uploads: the PhotoKit Background Resource Upload extension (iOS 26.1+), a background `URLSession` fed with part files that the Rust core has already encrypted, or a user-started `BGContinuedProcessingTask`. The answer fixes the iOS architecture and is evidence for OD-01.

## Hypothesis

1. **H-A (extension):** the extension uploads each `PHAssetResource`'s own bytes to the destination `URLRequest`. It offers no way to supply app-encrypted bytes, so it cannot carry content under ADR-0001. *Proved wrong if* the bytes that arrive at the probe server differ from the resource bytes, or if the extension can run Reliquary's own read–encrypt–upload pipeline within its runtime limit.
2. **H-B (background URLSession):** part files produced by the Rust core (B4-S1 API) and handed to a background `URLSession` with `uploadTask(with:fromFile:)` reach R2 presigned UploadPart URLs while the app is suspended or terminated. After a background relaunch the results are recorded in the core's SQLite DB. The spool stays within its budget. *Proved wrong if* transfers stall until the app is opened, if completions are lost, or if ETags cannot be read.
3. **H-C (continued processing):** a "Back up now" tap can hash and encrypt a multi-GB seed as a `BGContinuedProcessingTask` with the app in the background, provided progress is reported at least every few seconds.

## Decision it informs

| If the result is… | Then… |
|---|---|
| **Pass** (H-B holds; H-A confirmed, i.e. the extension cannot carry encrypted content) | iOS architecture = Rust core + background `URLSession` of pre-encrypted part files. "Back up now" uses `BGContinuedProcessingTask`. The extension is used at most for `downloadOnly` iCloud hydration (A9). Feeds ADR-0003 (T1 spike 8), the ADR-0004 iOS section, and OD-01 (iOS is feasible without changing ADR-0001). |
| **Fail**: H-B fails (transfers only progress in the foreground) | iOS cannot meet BUD-TTS unattended. Evidence for OD-01 "defer iOS" or "iOS after pilot, with a bridge" (see kit B4-S3). |
| **Surprise**: H-A proved wrong (encrypted payload possible) | Re-evaluate the extension as the primary uploader. Server work: the IETF resumable-upload endpoint (OPTIONS + 104) on a Worker. |
| **No result** (no Mac, iPhone or account) | iOS claims stay "paper only" (B4-S1). OD-01 is decided on paper, and the ADR-0004 iOS section says so. |

## Budget IDs cited

BUD-TTS (time to "sent"), BUD-TMP (spool ≤ 2 GB and ≥ 10 % free), BUD-BAT-D (< 2 %/day steady state), BUD-BAT-S (report % per 10 GB), BUD-REVOKE (presigned URLs expire within 15 min; tested against the discretionary queue delay). No new thresholds.

## Equipment

| Item | Exact model or version | Why | Have it? |
|---|---|---|---|
| Mac | Apple Silicon, a macOS version that runs an Xcode with the **iOS 26.4 SDK or later** (`creationRequestForJob` is iOS 26.4+). The iOS 27 SDK is needed for the async extension protocol and its Developer Mode | build the app, extension and XCFramework | |
| iPhone A | on **iOS 26.4 or later**; record the model and exact build | main device | |
| iPhone B (optional) | on **iOS 27.x** | the iOS 27 extension protocol and Developer Mode | |
| Test Apple Account | new account, iCloud Photos **on**, no family content | extension scheduling with iCloud Photos on (a reported bug) | |
| Apple Developer Program | the free Personal Team is enough for Xcode runs (profiles expire after 7 days, max 3 devices). The paid program (99 USD/year) is needed for TestFlight / Ad Hoc builds (step B7) | Apple DTS warns that background behaviour tested from Xcode is misleading | Yes / Buy (OD-09) |
| LAN computer | any, with Python 3.9+ | `probe_server.py` and `presign_parts.py` | |
| Sandbox R2 bucket + API token | H1 sandbox account only | A6 and part B | |
| USB cable | | Xcode runs, log export | |

**Software and files in this folder:**
- `build_xcframework.sh`: builds the B4-S1 Rust core (`spikes/B4-S1/core`) for `aarch64-apple-ios` and `-sim` and generates the Swift bindings.
- `swift/*.swift`: **sketches, not compiled** (the research container has no Apple SDK). `BackgroundUploader.swift` (background session, relaunch, reconcile), `PhotoKitSource.swift` (PhotoKit → core source), `UploadExtensionProbe.swift` (extension probe), `ContinuedBackup.swift` ("Back up now"). Expect to fix small things in Xcode, and note each fix in the results.
- `probe_server.py`: logs every request (method, headers, body SHA-256) and answers OPTIONS with 501, 200 or 404; it can send a `104` informational response. Self-tested with curl on 2026-09-29.
- `presign_parts.py`: stands in for the Worker. It presigns UploadPart URLs and can list and complete uploads. Tested on 2026-09-29 against the moto S3 emulator (emulated S3, **not R2**): part ETags equalled the parts' MD5, and the completed object's SHA-256 matched.
- SYN data is generated on the phone: `head -c` is not available there, so the app writes random bytes (1 GB and 2 GB files) into its own container.

## Before you start

- [ ] Take LAB shots on iPhone A with the test account: 20 photos, 2 Live Photos, 1 video of 1–3 min, 1 video over 1 GB (for example 4K 60 fps), all of a houseplant, with location off. Wait until Photos says they are uploaded to iCloud.
- [ ] On iPhone A, set Settings › Photos to **Optimize iPhone Storage** for part A9. Note the original setting so you can restore it.
- [ ] Note iPhone A's free space and battery health.
- [ ] Put the LAN computer and the iPhone on the same Wi-Fi. Start `probe_server.py --port 8080 --dir probe-out`.
- [ ] In the app's Info.plist add `NSPhotoLibraryUsageDescription`, `NSLocalNetworkUsageDescription`, ATS `NSAllowsLocalNetworking = YES` (for the LAN probe over http), `UIBackgroundModes = [processing]`, and `BGTaskSchedulerPermittedIdentifiers`. Create an **app group** shared by the app and the extension.
- [ ] Consent: not needed (no family participants).

## Procedure

Do the steps in order. After each step write down what you saw, even if it looks unimportant. Export the app's `b4s2-log.txt` (and the extension's app-group log) after each part.

**Part 0: build**
1. On the Mac, run `docs/research/kits/B4-S2/build_xcframework.sh` from the repo root. **You should see:** `ReliquaryCore.xcframework` in `spikes/B4-S1/`. Record the Xcode and SDK versions.
2. Create an iOS app project (SwiftUI) plus a Generic Extension target for the Photos background upload (steps in Apple's article, cited below). Add the XCFramework, `gen-ios/reliquary_ios_shape.swift` and the `swift/` sketches. Link `libsqlite3.tbd`. **You should see:** a build that runs on iPhone A. Record every compile fix you needed.

**Part A: PhotoKit Background Resource Upload extension (LAB only)**
3. (A1) In the app, request `.readWrite` photo access and call `setUploadJobExtensionEnabled(true)`. **You should see:** no error; `uploadJobExtensionEnabled == true`.
4. (A2) Queue jobs for 3 LAB resources (one photo, one Live Photo's `.pairedVideo`, the long video), destination `http://<LAN-IP>:8080/probe/<n>` with method **PUT**. Lock the phone and leave it on the charger on Wi-Fi. Record how long until the probe log shows the first request (check every 15 min for up to 24 h). On iOS 27 builds run from Xcode, run this step once with **Resource Upload Test Mode** off and once with it on (Settings › Developer › Photos).
5. (A3) For each upload, compare `body_sha256` in `probe-out/requests.jsonl` with the SHA-256 of the same resource that the app wrote with `PHAssetResourceManager.writeData(for:toFile:)`. **Expected (H-A):** equal, i.e. raw resource bytes. Also record whether an `OPTIONS` came first, the method, `Content-Type`, `Transfer-Encoding` / `Content-Length`, and any `Upload-*` headers.
6. (A4) Record the `jobLimit` value the extension logs.
7. (A5) Set `BackgroundUploadURLBase` to a different host (for example `http://base.invalid`) and repeat step 4 for one photo. Record whether the upload still reaches the probe server. Umbrel's code comments report that it did on iOS 26.6.1; Apple does not document this.
8. (A6) Sandbox R2: destination = a presigned **PUT** object URL from the sandbox bucket (`presign_parts.py` can be adapted, or use a single-object presign) for **one LAB photo**. Record the result, the job's `error`, and `responseHeaderFields` (the ETag?). R2 presigned URLs support only GET/PUT/HEAD/DELETE, on the S3 API host only.
9. (A6b) Restart the probe with `--options 200` and then `--send-104`, and repeat step 4 for the long video. Record whether the request pattern changes (resumable flow).
10. (A7) iCloud Photos is on for the test account. If step 4 never fires within 24 h, turn iCloud Photos off, repeat, and record the difference. (An April 2026 forum report on iOS 26.4 says the extension never ran with iCloud Photos on. Apple called it a bug.)
11. (A8) Enable `ProbeConfig.tryOwnPipeline`: inside `processJobs()` the extension reads one LAB resource through `PhotoKitSource`, encrypts it through the core, and starts its own `URLSession` upload of the parts to the probe server. Record: whether it is allowed at all, the seconds from start until `willTerminate`, the bytes done, and any memory termination (Console: jetsam). This tells whether the extension can be a wake-up source for encrypted uploads, which Apple does not document.
12. (A9) Pick a LAB video that shows the iCloud download badge (optimised). Create a `downloadOnly` job for its original resource. After it succeeds, read the resource in the app with `isNetworkAccessAllowed = false`. Record whether the read succeeds without network, and how long the file stays before the system purges it.

**Part B: background URLSession + Rust core (sandbox R2)**
13. (B1) Start `presign_parts.py serve --port 8081 --ttl 900` (TTL = BUD-REVOKE's 15 min). In the app, press **Prepare** to plan uploads for the 1 GB SYN file and the 20 LAB photos, set the spool budget to 256 MiB, call `produceParts` and `handOffPending`, then **press Home and lock the phone**. Do not open the app again during the step.
14. (B2) Wait. From the log, record the time until every part completed (compare BUD-TTS "sent < 1 h on idle Wi-Fi"), the number of background relaunches (`relaunched for background session` lines), 403s from expired URLs (the discretionary queue delay against the 15-min TTL), and whether `ETag` was present on every success. Check the ETags with `GET /parts` on the helper.
15. (B3) Force-quit: prepare again, swipe the app away in the app switcher, and wait 30 min. Open the app. **Expected:** `reattach` reports orphaned tasks (`orphans_reset > 0`) and they are re-queued. Record whether any completion events arrived after the force-quit.
16. (B4) Airplane mode for 10 min in the middle of a transfer. Record recovery without opening the app.
17. (B5) Spool: during B1–B4 record the app's disk use (Settings › General › iPhone Storage) against BUD-TMP.
18. (B6) Complete one upload with `POST /complete` and download the object from the sandbox bucket on the Mac. Decrypt it with `spikes/B4-S1` `verify` (adapt the paths) and compare its SHA-256 with the SYN file.
19. (B7) Repeat B1–B2 with a **TestFlight or Ad Hoc** build, not one run from Xcode. Record any difference.
20. (B8) Repeat B1 for the long LAB video with `RequestDataSource` and with `FileCopySource`. Record peak memory (Xcode memory gauge) and whether blocking PhotoKit's data handler causes errors.

**Part C: "Back up now" (BGContinuedProcessingTask)**
21. Generate a 2 GB SYN file. Tap **Back up now** (`ContinuedBackup.submit`), then background the app. **You should see:** a Live Activity with progress. Record the time to completion, how many times it expired, whether it ran with the screen locked, and the battery % used (BUD-BAT-S: % per 10 GB, scaled).
22. Repeat with `strategy = .fail` while another app runs a continued task, if you can arrange that. Record the submit result.

**Part D: BGProcessingTask overnight**
23. Register a `BGProcessingTaskRequest` with `requiresExternalPower = true` and `requiresNetworkConnectivity = true` that runs `produceParts` + `handOffPending` on new LAB photos. Leave the phone on the charger for 3 nights. Record how many times it fired, when, and for how long.

**Part E: steady-state battery**
24. With the app installed and idle, and the extension enabled or disabled as noted, record Settings › Battery › app % over 24 h, twice (BUD-BAT-D).

**Stop and record "No result" if:** Xcode refuses the Photos background upload extension point or App Groups under a Personal Team (record the exact message; this is evidence for OD-09); the phone cannot be updated to iOS 26.4 or later; the sandbox account does not exist yet (run parts A and C against the probe server only).

## Cleaning up

1. `setUploadJobExtensionEnabled(false)`, delete the app, restore the Photos storage setting.
2. Abort or delete all sandbox multipart uploads and objects under `b4s2/`. Revoke the sandbox API token if it was made for this kit.
3. Delete `probe-out/` after the results are written (LAB content only, but it is raw photo data).

## Data handling

- Class `SYN+LAB → results`. The test Apple Account holds LAB shots only. Do not sign the test iPhone into a family account.
- The probe server stores raw LAB bodies; keep them on the LAN computer and delete them after the run. Only sizes, hashes of LAB/SYN files, timings, counts and log excerpts go into `results.md`.
- API tokens and presigned URLs are SEC: never paste them into results. `probe_server.py` redacts `Authorization` and `X-Amz-Signature`.

## Sources used to write this kit (retrieved 2026-09-29)

- Apple, "Uploading asset resources in the background", https://developer.apple.com/documentation/photokit/uploading-asset-resources-in-the-background (read from the DocC JSON endpoint)
- Apple, PHAssetResourceUploadJobChangeRequest / PHAssetResourceUploadJob / jobLimit / PHBackgroundResourceUploadExtension reference pages (developer.apple.com/documentation/photos/…)
- Apple, "Downloading files in the background" and `URLSessionConfiguration.background(withIdentifier:)`
- Apple, "Performing long-running tasks on iOS and iPadOS" and `BGContinuedProcessingTaskRequest`
- Apple Developer Forums threads 822256 (extension not scheduled with iCloud Photos on), 818566 (no chunking; stay on NSURLSession if the backend cannot change), 807754 (do not trust Xcode-run background tests), 805554 (continued task marked stalled without progress) (secondary)
- Cloudflare R2 presigned URLs (docs source): https://raw.githubusercontent.com/cloudflare/cloudflare-docs/production/src/content/docs/r2/api/s3/presigned-urls.mdx
- Umbrel iOS `project.yml` comment on BackgroundUploadURLBase (secondary evidence of undocumented behaviour)

## Results

Copy this section into `docs/research/kits/B4-S2/results.md` and fill it in. Do not edit numbers afterwards; add a note instead.

- **Run by / date / place:**
- **Hardware and OS actually used:** Mac model and macOS; Xcode and SDK versions; iPhone model(s) and iOS build(s)
- **Signing:** Personal Team / paid program; Xcode run / TestFlight / Ad Hoc
- **Emulator or VM used instead of real hardware?** No | Yes: <what, and why> (the extension does not run in Simulator)

| Step | Expected | What happened | Measurement (with unit) | Screenshot or log |
|---|---|---|---|---|
| A2 first extension invocation | within 24 h | | h:mm after lock | |
| A3 bytes at server = resource bytes | equal | | equal / differ | |
| A3 OPTIONS preflight sent? | ? | | yes / no | |
| A4 jobLimit | ? | | integer | |
| A5 upload to host ≠ BackgroundUploadURLBase | ? | | yes / no | |
| A6 R2 presigned PUT as destination | ? | | status, error | |
| A7 scheduling with iCloud Photos on vs off | ? | | invocations / 24 h each | |
| A8 own pipeline inside extension | ? | | allowed?; s until willTerminate; bytes | |
| A9 downloadOnly then offline read | ? | | yes / no; purge time | |
| B2 all parts sent, app never opened | < 1 h (BUD-TTS "sent") | | minutes; relaunch count; 403 count | |
| B2 ETag present on every part | yes | | n / N | |
| B3 force-quit orphans re-queued | yes | | orphans_reset | |
| B5 spool peak | ≤ 256 MiB set; BUD-TMP | | MB | |
| B6 decrypted object = SYN | equal | | equal / differ | |
| B7 TestFlight/Ad Hoc vs Xcode | same | | differences | |
| B8 RequestData vs FileCopy memory | | | MB peak each | |
| C continued task, 2 GB | completes in background | | minutes; expirations; % battery | |
| D BGProcessingTask fires, 3 nights | ≥ 1 per night | | count, durations | |
| E idle battery, 24 h ×2 | < 2 % (BUD-BAT-D) | | % | |

| Pass criterion | Budget ID | Measured value | Pass / Fail / No result |
|---|---|---|---|
| Defines the iOS architecture: H-B holds with the app never opened | BUD-TTS | | |
| Spool within budget | BUD-TMP | | |
| Steady-state battery | BUD-BAT-D | | |
| Seed battery cost reported | BUD-BAT-S | | |
| Presigned TTL survives queue delay | BUD-REVOKE | | |
| H-A: extension cannot carry app-encrypted bytes | — | | Confirmed / Refuted |

- **Overall:** Pass | Fail | No result
- **Surprises and points of confusion:**
- **Follow-ups for the workstream:**
