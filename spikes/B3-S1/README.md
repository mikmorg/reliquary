# B3-S1: manifest census of comparable Android backup apps

- **Spike:** B3-S1 (workstream B3, `docs/research/PLAN.md` §"B3."), exec tag `[CT]`
- **Run by / date:** B3 spike runner (Wave 1, batch W1-c), 2026-09-29, in the cloud research container
- **Data-handling class:** `PUB → results` (public source manifests only; no APKs, no user data)
- **Budget IDs:** none. The PLAN pass criterion is qualitative and cites no BUD-* ID.
- **Pass criterion (PLAN):** "At least 2 comparable apps are on Play with broad media access and background upload."
- **Result:** **Pass at source level, with qualifications.** All 5 apps request broad `READ_MEDIA_IMAGES` + `READ_MEDIA_VIDEO` in the manifests of the build their repo publishes to Play. All 5 run background upload through WorkManager, and 4 of them also through a `dataSync` foreground service. Each repo has first-party evidence that it publishes to Google Play. **Not verified:** the manifests Play actually serves (the merged manifest from a Play-downloaded APK), and whether each app is live on Play today. `play.google.com` is blocked and no Android SDK is available (`dl.google.com` is blocked).

## What was measured

For each app, `census.py` parses the app-module `AndroidManifest.xml` files that make up its Play build. That is the `main` source set, plus the Play flavour overlay where one exists (with `tools:node="remove"` applied), plus the library modules for Proton Drive. It records the permissions and foreground-service types that matter to Play policy. `apps.json` lists the exact files. `census.json` is the full output.

It does **not** reproduce the Gradle manifest merge. Permissions that third-party AARs or Flutter plugins contribute are missing unless they are listed separately below.

| App (commit, date) | Package | Play evidence in the repo (first-party) | Files censused |
|---|---|---|---|
| Immich (`6cd746a`, 2026-09-29) | `app.alextran.immich` | `mobile/android/fastlane/Appfile` names the package, and `Fastfile` calls `upload_to_play_store` (track `beta` and default) | `main` (no store flavours) |
| Ente Photos (`7a5993c`, 2026-09-29) | `io.ente.photos` | README Play link `id=io.ente.photos`; Gradle `playstore` flavour keeps the unsuffixed id | `main` + `playstore` |
| Nextcloud (`3c70807`, 2026-09-29) | `com.nextcloud.client` | README Play link; Gradle `gplay` flavour; `setup.xml` has the Play testing opt-in URL | `main` + `gplay` |
| Proton Drive (`d1c81cd`, 2026-09-22) | `me.proton.android.drive` (namespace) | `app/build.gradle.kts` uses `libs.google.play.review` and writes `src/main/play/release-notes` with a comment about the "Google Play console" 500-character limit | app `main` + 6 library modules (the `prod` flavour has no overlay) |
| Seafile (seadroid) (`9d6d490`, 2026-09-28) | `com.seafile.seadroid2` | README "Get it on Google Play" badge | `main` (no store flavours) |

Synology Photos (named in PLAN) is closed source, so it could not be censused from source. A real census needs its Play APK (see "Next step").

### Permissions in the Play-build app manifests

`Y` = declared in the censused files; `-` = not declared there. A library can still add a permission during the Gradle merge (see the next section).

| App | IMAGES | VIDEO | USER_SELECTED | MEDIA_LOCATION | MANAGE_EXTERNAL_STORAGE | MANAGE_MEDIA | FGS_DATA_SYNC | RUN_USER_INITIATED_JOBS | REQUEST_IGNORE_BATTERY_OPT. | BOOT_COMPLETED | BACKGROUND_LOCATION |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Immich | Y | Y | Y | Y | - | Y | Y | - | - | - (WorkManager adds it) | Y |
| Ente Photos | Y | Y | - | Y | - | Y | - | - | - | Y | - |
| Nextcloud | Y¹ | Y¹ | Y | Y | Y | - | Y | - | Y | Y | - |
| Proton Drive | Y | Y | Y | Y | - | - | Y | - | Y | - (WorkManager adds it) | - |
| Seafile | Y | Y | - | - | Y | - | Y | - | - | Y | - |

¹ Declared with `tools:ignore="PhotoAndVideoPolicy"`, which suppresses an Android Lint check with that id.

### Foreground-service types

| App | Services with `foregroundServiceType` |
|---|---|
| Immich | WorkManager `SystemForegroundService` = `dataSync\|shortService` |
| Ente Photos | none in the app manifests. Uses the Flutter `workmanager` plugin (0.9.0+3 → `workmanager_android` 0.9.0+2 → `androidx.work:work-runtime:2.10.2`) |
| Nextcloud | WorkManager `SystemForegroundService` = `dataSync`; `FileTransferService` = `dataSync`; `PlaybackService` = `mediaPlayback` |
| Proton Drive | WorkManager `SystemForegroundService` = `dataSync` (`tools:node="merge"`) |
| Seafile | WorkManager `SystemForegroundService` = `dataSync` (`tools:node="merge"`); `FileDaemonService` = `dataSync` |

### Library contributions that were checked

| Library | Source | What it adds to the merged manifest |
|---|---|---|
| `androidx.work:work-runtime` | `androidx/androidx` `androidx-main` @ `0a6c008` (tip on 2026-09-29, **not** the exact version each app pins; `dl.google.com`/Google Maven AARs are blocked). Copied as `lib-workmanager-androidx-main-AndroidManifest.xml` | `WAKE_LOCK`, `ACCESS_NETWORK_STATE`, `RECEIVE_BOOT_COMPLETED`, `FOREGROUND_SERVICE`; `SystemForegroundService` with **no** type (apps add the type themselves) |
| `photo_manager` 3.11.0 / 3.9.0 (pub.dev) | Ente pins 3.11.0; Immich's pubspec says 3.9.0 | `READ_EXTERNAL_STORAGE` with `maxSdkVersion="32"` only |
| `workmanager_android` 0.9.0+2 (pub.dev) | Ente, transitive | `POST_NOTIFICATIONS`; depends on `androidx.work:work-runtime:2.10.2` |

## Observations (facts from the table; interpretation is for the analyst)

1. **All 5 ask for broad media access in their Play build.** None relies on the photo picker or on selected-photos access alone. 3 also declare `READ_MEDIA_VISUAL_USER_SELECTED`.
2. **None declares `RUN_USER_INITIATED_JOBS`**, so none of the 5 uses UIDT jobs in its Play build (a UIDT job needs that permission). Background upload is WorkManager-based in all 5. 4 of the 5 type WorkManager's foreground service as `dataSync`; Immich adds `shortService`.
3. **All-files access:** 2 of 5 (Nextcloud, Seafile) keep `MANAGE_EXTERNAL_STORAGE` in the Play-build sources. Nextcloud's `gplay` overlay removes only `REQUEST_INSTALL_PACKAGES`. The photo-first apps (Immich, Ente, Proton) do not declare it.
4. **Battery-exemption request:** 2 of 5 (Nextcloud, Proton) declare `REQUEST_IGNORE_BATTERY_OPTIMIZATIONS`.
5. **`ACCESS_MEDIA_LOCATION`** (unredacted EXIF GPS): 4 of 5.
6. **`MANAGE_MEDIA`** (modify or delete media without a prompt): Immich and Ente only.
7. **Lint guard:** Nextcloud suppresses a Lint check called `PhotoAndVideoPolicy` on the media permissions. That points to a Lint check that could serve as a CI guard; its documentation was not read.

## Limits and blocked sources

- The **Play-served merged manifests** were not checked. `play.google.com` is blocked, APK mirrors are blocked, and GitHub release downloads return 403 through the proxy. So "on Play with broad media access" is shown at source level plus first-party publish evidence, not from the binary Play serves today.
- **Current Play presence** is not verified for any app, for the same reason.
- The full Gradle merge could not be run: no Android SDK, because `dl.google.com` is blocked and `maven.google.com` redirects there.
- Only 5 apps were censused, and Synology Photos is missing (closed source).

## Next step (owner lab, optional)

Add this to the B3-S3 kit session, or run it separately on a phone with Play. Install each app from Play and pull its APK with `adb shell pm path <package>` then `adb pull`. Run `apkanalyzer manifest print` (Android SDK cmdline-tools) or `aapt2 dump xmltree --file AndroidManifest.xml` on it, and add the results to `census.json` as a `play_served` field.

## Files

- `census.py`: the census script.
- `apps.json`: the files and Play evidence for each app.
- `census.json`: output from the 2026-09-29 run.
- `fetch.sh`: recreates the pinned sparse checkouts.
- `lib-workmanager-androidx-main-AndroidManifest.xml`: the WorkManager library manifest.

To reproduce: `./fetch.sh && python3 census.py apps.json > census.json`.
