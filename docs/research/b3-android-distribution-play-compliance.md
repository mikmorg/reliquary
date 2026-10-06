# B3. Android distribution channel and Play compliance

- **Workstream:** B3 (see `docs/research/PLAN.md`, section "B3.")
- **Status:** Draft (analyst deep read, Wave 1 desk checks). Not yet under skeptic review.
- **Date:** 2026-09-29 (last updated 2026-09-29)
- **Feeds:** ADR-0019 (partial draft inputs in §"ADR-0019 draft inputs" below), OD-10, OD-11, OD-19 (with E2), one-way door #12; design-change requests against ADR-0002 §2 and §4; inputs to B2/ADR-0018, D5/ADR-0015, D6/ADR-0027, E5 (install referrer), H5 (L05, L06)
- **Depends on:** T2 (fact-check item 7), H5 (§6 F1–F4), D6 (privacy policy; not started), E2 (OD-19; not started), B2 (background execution; not started)
- **Traceability rows closed or advanced:** R-02 (advanced), R-26 (advanced: OD-11 options written), Q2-2 (advanced: limited distribution characterised; 12-tester rule not re-verified)
- **Scope of this run:** Wave 1 desk checks only. Encryption export (EAR, `ITSAppUsesNonExemptEncryption`, French declaration) and the iOS compliance checklist were **not** swept in this run; they stay open for Wave 2.

## Summary

The two Android channels in OD-10 are not two flavours of Google Play. A **Play closed testing track** is a Play listing: Play installs and updates the app, and every Play policy (photo and video permissions, foreground-service declarations, account deletion, Data safety, target API) applies. The free **"limited distribution" account** is an Android Developer Console account for installing **outside Play** on up to 20 devices that users authorise through a QR code or link (primary, high confidence). ADR-0002 calls it a "Google Play" account, which is wrong. How devices are counted, removed or replaced, and how updates reach them, is **not documented**.

The one-way door is the **package name plus the app signing key**, not the channel, provided the owner generates and keeps the app signing key and uploads it to Play App Signing instead of letting Google generate it. Google's documents say a package name used outside Play can still be used on Play, and that a Play Console account can also register apps distributed outside Play. A sideloaded app can update itself without a prompt on current Android if it holds `REQUEST_INSTALL_PACKAGES` and targets a recent API level. So ADR-0002's "no automatic updates" reason for rejecting sideloading is weaker than it assumed. This is inferred from the API reference and needs a device test.

The Play policy texts that decide OD-11 (account deletion) and the Photo & Video declaration are on `support.google.com` and `play.google.com`, which are **blocked**. Those answers are **no result** or **secondary only**, and the B3-S3 dry run is the only primary route.

**Recommendation (medium-low confidence, because the policy texts are blocked):**
- Keep the Play closed track as the primary channel (ADR-0002), gated on the B3-S3 dry run.
- Make limited distribution the pre-decided fallback.
- Close the key and package door now: owner-generated app signing key, and a package name under a domain the owner controls.
- Register a **personal** account, not an organisation.
- Reduce OD-11 exposure by having the **admin create the account** when generating the invite, so that the Android app never creates accounts (a design change to ADR-0002 §2).

## Questions

| # | Question | Short answer | Confidence |
|---|---|---|---|
| 1 | Closed track vs limited distribution: install and update path | Closed track: installed and auto-updated by Play after each person opts in with a listed Google account (T2). Limited distribution: outside Play, "secure handshake ... QR codes or links, user consent on the device, and registration using the Android Developer Console" (C1). The update path for limited distribution is undocumented. Self-update through `PackageInstaller` without a prompt is possible in principle (C12). | High (channels); Medium (self-update) |
| 2 | Do declarations and review apply? | Closed track: Play Console declarations are per app. The FGS-type declaration is required for targetSdk 34+ (C14). Whether review runs on closed tracks: **no primary result** (blocked). Limited distribution: Play policies and declarations do not apply because the app is not on Play (inference). Whether any ADC terms or policy apply: **no result**. | Medium / Low |
| 3 | Replacement phones and children's devices against the 20 cap; removing devices | **No result.** The limited-distribution guide and FAQ do not say how devices are counted, removed or replaced (C3). Needs a real-device kit after ADC sign-up. | High that it is undocumented |
| 4 | Which developer identity is shown | **No result** for both channels. Limited distribution: the contact email "won't be shown publicly"; nothing says whether the legal name from the payments profile appears in the invitation (C2). Play: the listing shows a developer name; whether a personal account's address is shown is on blocked Play Help. | Low |
| 5 | Can you move between channels without changing package name or key? | Probably yes, **if the owner holds the app signing key.** A package name used outside Play "can still" be used on Play (C6). A Play Console account can register off-Play apps (C7). Play App Signing accepts a developer-supplied key (C9). Account type moves one way only: limited → full, never back (C5). Undocumented: whether a package registered to an ADC limited account conflicts with Play Console auto-registration under a separate Play account. | Medium |
| 6 | Does automatic whole-camera-roll backup qualify for the Photo & Video declaration? | **Secondary only.** developer.android.com says `READ_MEDIA_IMAGES`/`VIDEO` "are restricted to specific use cases outlined in the Google Play policy" (C16). The policy text itself is blocked. Four comparable backup apps declare broad media permissions in source (C24). The photo picker and selected-photos access cannot serve automatic backup (C17). | Medium (need is certain; approval unverified) |
| 7 | `MANAGE_EXTERNAL_STORAGE` vs SAF for documents | "Backup and restore apps" and "Document management apps" are listed as likely permitted uses (C18). Nextcloud removed all-files access from its Play build on 2024-11-29 and re-enabled it on 2025-05-27 (C25): possible, but fragile. SAF cannot grant the **Download** directory or the storage root on Android 11+ (C19), so SAF alone misses the folder where most phone documents land. | High (facts); Medium (Play outcome) |
| 8 | FGS type declaration and demo video vs a UIDT-only design | UIDT jobs can only be scheduled while the app is visible, so UIDT-only cannot run automatic backup (C21). `dataSync` explicitly covers backup (C20). It has a 6 h per 24 h cap for targetSdk 35+ and cannot start from `BOOT_COMPLETED` (C20). Google recommends WorkManager for background-initiated transfers (C22). Proposed: WorkManager as the base, a `dataSync` FGS worker for long seeding runs, and UIDT for "back up now" (B2 decides). The demo-video requirement text is blocked. | High (platform); Low (Play review detail) |
| 9 | Battery-optimisation exemption requests | Play forbids the direct-request intent "unless the core function of the app is adversely affected"; backup is not in Google's acceptable-use table (C23). Precedent: Syncthing was rejected for it in 2018 (secondary). Nextcloud and Proton Drive still declare it (source). Proposed: do not declare `REQUEST_IGNORE_BATTERY_OPTIMIZATIONS` in the Play build; send users to the settings list instead, which Google says "most apps" may do. | High (text); Medium (enforcement) |
| 10 | Account deletion: does invite redemption count as in-app account creation? | **No primary result** (Play Help 13327111 blocked). Under ADR-0002 §2, redemption "creates the account (name and email)", so it very probably does. Options that avoid deleting backups are in the OD-11 request. Immich (admin-created accounts, no mobile sign-up) and Ente (deletion request decoupled from asynchronous data cleanup) are precedents (C27, C28). | Low |
| 11 | Data safety: does admin-decryptable client-side encryption count as "collected"? | **No result.** The definitions are on blocked Play Help (C29). Working assumption for the draft form: declare Photos and videos, Files and docs, and Location (EXIF), because the admin can decrypt them. Unredacted EXIF needs `ACCESS_MEDIA_LOCATION` (C30). | Low |
| 12 | Privacy policy URL; prominent disclosure; stalkerware / persistent notification | **No result** (blocked). Carried to D6 and the B3-S3 dry run. | — |
| 13 | Developer verification timeline and effect | Launched Aug 2026. Enforced from 30 Sep 2026 for installs from listed stores (including Play) in BR, ID, SG and TH. Global on certified devices in 2027. Android 7+. Play apps are registered automatically; Play App Signing apps are claimed automatically. ADB installs are exempt (C10, C11). | High |
| 14 | Personal vs organisation account | Personal. Organisation needs a D-U-N-S number ("can take up to 28 days"), a website verified in Search Console and official documents such as IRS letters (C8). A family has none of these. | High |
| 15 | Target API deadlines | Since 31 Aug 2026, new apps and updates submitted to Play must target API 36 (extension to 1 Nov 2026 on request). Existing apps below API 35 are hidden from new users on newer Android versions (C13). The page gives no testing-track exemption (inference: it applies to closed tracks). | High (text); Medium (tracks) |
| 16 (new) | Does a sideloaded app still get automatic updates? | Possibly without prompts. `PackageInstaller.SessionParams.setRequireUserAction(USER_ACTION_NOT_REQUIRED)` skips user action when the installer holds `REQUEST_INSTALL_PACKAGES`, is updating itself or is the installer of record, and the target API is recent enough (API 34+ on Android 16, 35+ on Android 17) (C12). The user must still grant "install unknown apps" to Reliquary once (inference). | Medium |
| 17 (new) | Hibernation risk | The target-API page says unused apps "may be put into hibernation", which resets runtime permissions and stops jobs (C31). That threatens a backup app nobody opens, on any channel. Hand-off to B2. | Medium |

## Method

- **Sweep:** three scouts ran (docs, source, community); their findings are merged here. No pricing/policy scout ran separately; policy pages are blocked in any case.
- **Deep read (this analyst):** re-fetched and read in full 21 developer.android.com pages directly (HTTP 200) on 2026-09-29, extracting the text and each page's "Last updated" stamp. Checked the Nextcloud `gplay` manifest history with a blobless git clone. Checked the Immich manifest, Immich mobile login form and user-management docs, and Ente's deletion service and server controller on raw GitHub.
- **Routes used:** direct (developer.android.com), raw GitHub, a git partial clone (github.com git protocol works; the API does not).
- **Blocked sources (reported for H1; see `sources.md` rows for support.google.com and play.google.com):**
  - support.google.com: Play Console Help 13327111 (account deletion), Photo & Video Permissions, 13392821 (FGS requirements), 14151465 (testing requirements), Data safety, and personal vs organisation public details. Retested by this analyst with WebFetch: `EGRESS_BLOCKED`.
  - play.google.com: Policy Center.
  - android-developers.googleblog.com.
  - web.archive.org.
  - api.github.com for Nextcloud issues (not enabled for this session).
  - WebSearch: session budget exhausted (200/200), confirmed by this analyst.
  - Context7: quota exceeded (scout).
- **Stop rule:** the policy primaries are unreachable by every route tried, and the remaining leads need a device or a Play Console (B3-S3). No secondary source was substituted for a blocked primary.

## Sources

| # | Source | Publisher | Published or version date | Accessed | Primary? |
|---|---|---|---|---|---|
| S1 | Android developer verification (overview) https://developer.android.com/developer-verification | Google | No date on page | 2026-09-29 | Yes |
| S2 | Developer verification guides (index, comparison table) https://developer.android.com/developer-verification/guides | Google | Last updated 2026-08-18 | 2026-09-29 | Yes |
| S3 | Limited distribution account https://developer.android.com/developer-verification/guides/limited-distribution | Google | Last updated 2026-08-20 | 2026-09-29 | Yes |
| S4 | Developer verification FAQ https://developer.android.com/developer-verification/guides/faq | Google | Page 2026-08-27; answers 2025-09-03 to 2026-07-15 | 2026-09-29 | Yes |
| S5 | Register on Google Play Console https://developer.android.com/developer-verification/guides/google-play-console | Google | Last updated 2026-08-18 | 2026-09-29 | Yes |
| S6 | Full distribution account requirements https://developer.android.com/developer-verification/guides/full-distribution | Google | Last updated 2026-08-18 | 2026-09-29 | Yes |
| S7 | Register on Android Developer Console https://developer.android.com/developer-verification/guides/android-developer-console | Google | Last updated 2026-09-04 | 2026-09-29 | Yes |
| S8 | Meet Google Play's target API level requirement https://developer.android.com/google/play/requirements/target-sdk | Google | Last updated 2026-09-16 | 2026-09-29 | Yes |
| S9 | Foreground service types https://developer.android.com/develop/background-work/services/fgs/service-types | Google | Last updated 2026-09-21 | 2026-09-29 | Yes |
| S10 | Foreground service types are required (Android 14) https://developer.android.com/about/versions/14/changes/fgs-types-required | Google | Last updated 2026-09-21 | 2026-09-29 | Yes |
| S11 | Android 15 behavior changes (dataSync timeout) https://developer.android.com/about/versions/15/behavior-changes-15 | Google | Last updated 2026-09-16 | 2026-09-29 | Yes |
| S12 | Alternatives to dataSync FGS https://developer.android.com/about/versions/15/changes/datasync-migration | Google | Last updated 2026-02-26 | 2026-09-29 | Yes |
| S13 | User-initiated data transfer jobs https://developer.android.com/develop/background-work/background-tasks/uidt | Google | Last updated 2026-09-16 | 2026-09-29 | Yes |
| S14 | Manage all files on a storage device https://developer.android.com/training/data-storage/manage-all-files | Google | Last updated 2026-09-16 | 2026-09-29 | Yes |
| S15 | Access documents and other files (SAF) https://developer.android.com/training/data-storage/shared/documents-files | Google | Last updated 2026-09-16 | 2026-09-29 | Yes |
| S16 | Access media files (MediaStore) https://developer.android.com/training/data-storage/shared/media | Google | Last updated 2026-09-16 | 2026-09-29 | Yes |
| S17 | Partial photo and video access (Android 14) https://developer.android.com/about/versions/14/changes/partial-photo-video-access | Google | Last updated 2026-03-03 | 2026-09-29 | Yes |
| S18 | Optimize for Doze and App Standby https://developer.android.com/training/monitoring-device-state/doze-standby | Google | Last updated 2026-08-18 | 2026-09-29 | Yes |
| S19 | Sign your app (Play App Signing) https://developer.android.com/studio/publish/app-signing | Google | Last updated 2026-03-06 | 2026-09-29 | Yes |
| S20 | PackageInstaller.SessionParams reference https://developer.android.com/reference/android/content/pm/PackageInstaller.SessionParams | Google | Last updated 2026-08-03 | 2026-09-29 | Yes |
| S21 | Identify data collection and sharing (Data safety) https://developer.android.com/guide/topics/data/collect-share | Google | Last updated 2026-03-06 | 2026-09-29 | Yes |
| S22 | Play Install Referrer API https://developer.android.com/google/play/installreferrer | Google | Last updated 2025-07-21 | 2026-09-29 (scout) | Yes |
| S23 | `immich-app/immich` @ `main` : `mobile/android/app/src/main/AndroidManifest.xml`; `.../background/BackgroundWorker.kt`, `BackgroundWorkerApiImpl.kt` (scout); `mobile/lib/widgets/forms/login/login_form.dart`; `docs/docs/administration/user-management.mdx` | Immich | main @ 6cd746a (scout), 2026-09-29 | 2026-09-29 | Yes |
| S24 | `ente-io/ente` @ `main` : `mobile/apps/photos/android/app/src/main/AndroidManifest.xml`; `mobile/packages/account_deletion/lib/src/services/account_deletion_service.dart`; `server/pkg/controller/user/user.go` | Ente | main @ 7a5993c (scout), 2026-09-29 | 2026-09-29 | Yes |
| S25 | `nextcloud/android` @ `master` : `app/src/main/AndroidManifest.xml`, `app/src/gplay/AndroidManifest.xml`; git history of the gplay manifest (commits e315793137 2024-11-29 and 6c20677103 2025-05-27; tags `stable-3.31.0`, `stable-3.32.0`) | Nextcloud | master, 2026-09-29 | 2026-09-29 | Yes |
| S26 | nextcloud/android issues #14409 (opened 2025-01-14, closed 2026-09-07), #14135 | Nextcloud community | as stated | 2026-09-29 (scout, via WebFetch summary) | No (issue thread) |
| S27 | `ProtonDriveApps/android-drive` @ `main` (d1c81cd, 2026-09-22): app, photos/presentation, drive/backup/data manifests | Proton | 2026-09-22 | 2026-09-29 (scout) | Yes |
| S28 | `syncthing/syncthing-android` @ `main` : `README.md` (discontinued notice); issue #1039 (2018-03-14), #2064 (2024-02-27) | Syncthing | Dec 2024 notice | 2026-09-29 (scout) | README yes; issues no |
| S29 | `haiwen/seadroid` @ `master` : `app/src/main/AndroidManifest.xml` | Seafile | master | 2026-09-29 (scout) | Yes |
| S30 | `Catfriend1/syncthing-android` @ `main` : manifest, README | Syncthing-Fork | main | 2026-09-29 (scout) | Yes |
| S31 | react-native-cameraroll #618 (restatement of Photo & Video policy) | community | 2024-04-29 | 2026-09-29 (scout) | No |
| S32 | aj3423/SpamBlocker #664 ("20 users for 14 days") | community | 2026-09-13 | 2026-09-29 (scout) | No |
| S33 | T2 `docs/research/fact-check-adr-0001-0002.md` item 7; H5 `h5-long-lead-items.md` §6 | this repo | 2026-09-29 | 2026-09-29 | Secondary relay |

## Claims

Skeptic columns are empty until the Stage 4 review.

| # | Claim | Sources | Key? | Skeptic 1 | Skeptic 2 | Skeptic 3 | Verdict |
|---|---|---|---|---|---|---|---|
| C1 | Limited distribution is a free Android Developer Console account for distribution **outside Google Play**. It shares apps "with up to 20 devices that end-users have explicitly authorized" through "QR codes or links, user consent on the device, and registration using the Android Developer Console". Google lists "Hobbyist: share with family and friends ... no commercial intent" as a fitting use. | S2, S3, S1 | Yes | | | | Pending |
| C2 | Limited-distribution sign-up needs a Google Account with 2-Step Verification, a Google payments profile (legal name and address) and a contact email that "won't be shown publicly". No government ID. | S3 | Yes | | | | Pending |
| C3 | The official pages do not document how the 20 devices are counted, removed or replaced, the install or update UX, or which identity the invitation shows. Google says "registering package names and authorizing devices can take some time". | S3, S4, S7 | Yes | | | | Pending |
| C4 | ADR-0002's phrase "Google Play 'limited distribution' account" is inaccurate. The account is in the Android Developer Console, not Play. | S1, S2, S3 | Yes | | | | Pending |
| C5 | Google "would support migrating limited distribution accounts to full accounts but not the other way around" (FAQ, 2026-06-08). | S4 | Yes | | | | Pending |
| C6 | When an app is created in Play Console, Play registers its package name automatically. "If you have been using the name outside of Google Play, you can still use it on Google Play." If another developer already uses the name, Play Console asks for a different one. | S5 | Yes | | | | Pending |
| C7 | A Play Console account can register apps distributed outside Play ("the single place to manage all their verification requirements"). Play App Signing apps are claimed automatically. | S4, S5, S2 | Yes | | | | Pending |
| C8 | Full distribution (ADC $25, waived for limited): an individual needs a government photo ID, proof of address, and an OTP-verified email and phone. An organisation also needs a D-U-N-S number (free, "can take up to 28 days"), a website verified in Search Console and official documents (US examples: IRS letters, incorporation certificate). | S4, S6 | Yes | | | | Pending |
| C9 | Play App Signing is required for new Play apps. The developer may supply their own app signing key ("Export and upload"). After setup "you cannot retrieve a copy" and "Google may retain a backup copy". A key upgrade applies only on Android 13+; older devices keep the old key. | S19 | Yes | | | | Pending |
| C10 | Enforcement from 30 Sep 2026 covers installs from listed stores (Google Play, HONOR, OPPO, Galaxy Store, Palm Store, V-Appstore, GetApps) in BR, ID, SG and TH on certified Android 7+ devices. Sideloads are not enforced in that phase. Global rollout to all apps on certified devices in 2027. | S1, S2, S4 | Yes (time-sensitive) | | | | Pending |
| C11 | ADB installs never need verification and skip the advanced-flow wait. Unregistered apps install or update only with the advanced flow enabled (developer mode, a one-day wait, biometric) or over ADB. | S4 | Yes | | | | Pending |
| C12 | `setRequireUserAction(USER_ACTION_NOT_REQUIRED)` (API 31+) lets an installer holding `REQUEST_INSTALL_PACKAGES` update without user action when it is updating itself or is the installer of record/update owner, and the app targets a recent enough API (API 34+ on Android 16, API 35+ on Android 17). Inference: a limited-distribution or off-Play build can self-update silently, as the desktop clients do. | S20 | Yes | | | | Pending |
| C13 | From 31 Aug 2026, new apps and updates submitted to Play must target API 36 (extension to 1 Nov 2026). Existing apps below API 35 are unavailable to new users on newer Android. The only exemption is "permanently private apps ... in a specific organization". No testing-track exemption is stated. | S8 | Yes (time-sensitive) | | | | Pending |
| C14 | Apps targeting Android 14+ must declare their FGS types in Play Console (Policy > App content). `specialUse` subtypes are reviewed at submission. | S9, S10 | Yes | | | | Pending |
| C15 | Syncthing's official Android app was discontinued with the Dec 2024 release, citing "Google making Play publishing something between hard and impossible" plus no maintainer. | S28 | No (context) | | | | Pending |
| C16 | developer.android.com states that `READ_MEDIA_IMAGES`/`READ_MEDIA_VIDEO` "are restricted to specific use cases outlined in the Google Play policy" and recommends the photo picker. The policy text itself was not reachable. | S16 | Yes | | | | Pending |
| C17 | Selected-photos access (`READ_MEDIA_VISUAL_USER_SELECTED`) "expires eventually", and compatibility-mode grants are revoked after the app goes to the background. Automatic whole-library backup needs full `READ_MEDIA_IMAGES`/`VIDEO`. | S17 | Yes | | | | Pending |
| C18 | Play's all-files policy (summarised on developer.android.com, in effect since May 2021): request `MANAGE_EXTERNAL_STORAGE` only when SAF or MediaStore cannot do the job and the use is core. Listed likely uses include "Backup and restore apps" and "Document management apps". | S14 | Yes | | | | Pending |
| C19 | On Android 11+, `ACTION_OPEN_DOCUMENT_TREE` cannot grant the internal storage root, reliable SD-card roots, or the **Download** directory. | S15 | Yes | | | | Pending |
| C20 | `dataSync` covers "Data upload or download" and "Backup-and-restore operations". For targetSdk 35+, `dataSync` services get 6 h in total per 24 h (`onTimeout`) and may not be launched from `BOOT_COMPLETED`. | S9, S11 | Yes | | | | Pending |
| C21 | UIDT jobs (API 34+) must be scheduled while the app is visible (or under listed exemptions), need a notification, and are meant for user-initiated transfers. Inference: UIDT alone cannot drive automatic backup. | S13 | Yes | | | | Pending |
| C22 | Google: "In most cases, WorkManager is the best option". Long-running workers become an FGS and inherit FGS limits. | S12 | No | | | | Pending |
| C23 | "Google Play policies prohibit apps from requesting direct exemption from ... Doze and App Standby ... unless the core function of the app is adversely affected." Acceptable examples include task automation for "new photo management" and safety apps; backup is not listed. "Most apps" may send users to `ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS`. | S18 | Yes | | | | Pending |
| C24 | Immich, Ente, Nextcloud and Proton Drive declare `READ_MEDIA_IMAGES`/`VIDEO` plus background upload machinery in source. Immich: `dataSync\|shortService` FGS, `MANAGE_MEDIA`, `ACCESS_MEDIA_LOCATION`, no `MANAGE_EXTERNAL_STORAGE`. Play-served merged manifests were **not** checked. | S23, S24, S25, S27 | Yes (B3-S1 input) | | | | Pending |
| C25 | Nextcloud removed `MANAGE_EXTERNAL_STORAGE` from its gplay flavour on 2024-11-29 ("not possible for gplay flavor anylonger") and removed that override on 2025-05-27 ("Re-enable permission"), first in tag `stable-3.32.0`. That Play accepted the re-enabled build is inferred, not verified. | S25, S26 | Yes | | | | Pending |
| C26 | Immich promotes its WorkManager worker to a `dataSync` FGS only when the app is already battery-optimisation exempt. It uses MediaStore content-URI triggers plus a 1 h periodic worker; no UIDT. | S23 (scout read) | No | | | | Pending |
| C27 | Immich's mobile login form has no sign-up path. Accounts are created by the admin in the web UI ("Administration > Users > Create user"). | S23 | Yes (OD-11 precedent) | | | | Pending |
| C28 | Ente's in-app deletion runs a challenge (`GET /users/delete-challenge`) and then `DELETE /users/delete`. The server marks the account deleted and **schedules** data cleanup (`markAccountDeletedAndScheduleCleanup`). | S24 | Yes (OD-11 precedent) | | | | Pending |
| C29 | The Data safety guidance lists categories (Photos and videos, Files and docs, Location, ...) but leaves the definitions of "collection" and the treatment of encrypted data to blocked Play Help. | S21 | Yes | | | | Pending |
| C30 | Unredacted EXIF (including location) needs `ACCESS_MEDIA_LOCATION` plus `MediaStore.setRequireOriginal()`. Without it, the system hides location. | S16 | Yes (also T1 spike 3, A1) | | | | Pending |
| C31 | "Apps may be put into hibernation mode if they are not used over a period of time", which resets runtime permissions and stops jobs. | S8 | Yes (B2) | | | | Pending |
| C32 | Personal Play accounts created after 13 Nov 2023 need 12 testers for 14 days before **production** (T2). A 2026 indie post says 20 testers. Both are secondary, and neither applies if Reliquary stays on the closed track. | S33, S32 | No (unless production is chosen) | | | | Pending |

## Findings

### F1. The channels are different in kind (C1–C4, C11)

| | Play closed testing track | ADC limited distribution | Off-Play APK registered by a full account (Play Console or ADC, $25, ID) | Unregistered APK |
|---|---|---|---|---|
| Where it installs from | Play Store | Invitation (QR or link) plus consent on the device | Any channel (USB stick, link) | Any channel |
| Device cap | Tester list (T2: up to 2,000 emails) | 20 authorised devices | None | None |
| Updates | Play auto-update | Undocumented; app self-update possible (C12) | App self-update (C12) | Only with advanced flow or ADB (C11) |
| Play policies and declarations | Apply | Do not apply (not on Play) | Do not apply | Do not apply |
| Owner's identity checks | Play personal account: ID (C8) | None (payments profile only) | Government ID | None |
| Cost | $25 once | $0 | $25 | $0 |
| Fit with ADR-0002 | As written (§4) | Changes §4 (sideloading was rejected) | Changes §4 | Rejected (advanced flow is unfit for relatives) |

Confidence: high on the channel facts, medium on the update rows.

### F2. The one-way door is the key and package, not the channel (C5–C9, C12)

- If Google **generates** the app signing key, the owner can never sign an off-Play build that updates a Play install. Any later channel change then means a new package name and a reinstall on every phone.
- If the owner **generates** the key, keeps it offline (D2/D5 custody), and uploads it to Play App Signing, the same package and key can later go to limited distribution or a registered off-Play APK.
  - Play Console says names used outside Play can be used on Play (C6).
  - A Play Console account can also register off-Play distribution (C7).
- **Remaining unknowns:**
  - Whether a package first registered to an ADC *limited* account can later be claimed by a separate Play Console account. Google supports migrating limited → full within ADC (C5), but says nothing about ADC → Play Console.
  - Whether Google-held key backups (C9) matter to D5's supply-chain model: Google can sign builds of a Play app.
- **Recommendation:**
  - The owner generates the key.
  - Pick a reverse-DNS package name under a domain the owner controls (ties to H5 L03).
  - Create nothing in Play Console under the real package name until ADR-0019 fixes it. B3-S3 uses a throwaway name (H5 F3).

Confidence: medium.

### F3. ADR-0002's reasons for rejecting sideloading are weaker than assumed (C1, C11, C12)

ADR-0002 rejected the sideloaded APK because of "security warnings, no automatic updates".

- **Automatic updates:** limited distribution or a registered APK can update itself without a prompt on current Android. This requires `REQUEST_INSTALL_PACKAGES`, a one-time "install unknown apps" grant, and keeping `targetSdk` within the moving window in C12, which is similar to Play's own cadence (C13).
- **Security warnings:** registered apps avoid the advanced flow. Whether a first install still shows an "unknown sources" prompt is undocumented and needs a device test.

This is inference from the API reference, medium confidence.

### F4. Play compliance for the app as designed

- **Photo & Video permissions (C16, C17, C24):** automatic backup needs full `READ_MEDIA_IMAGES`/`VIDEO`, plus `ACCESS_MEDIA_LOCATION` for original bytes (C30). Comparable apps declare the same set, but their Play approval is not verified. Evidence for the declaration (proposed, unverified against the form): the core function is automatic backup of the whole library; the photo picker cannot do it (C17); a demo video shows first-run discovery and background upload. **Secondary only** until B3-S3 or the allowlist.
- **All-files access (C18, C19, C25):** Google's summary lists backup apps as a likely permitted use. Nextcloud's six-month loss shows that approval can be withdrawn. SAF cannot reach `Download/`. Proposed for OD-19 (E2 decides scope): v1 Android backs up photos and videos only. Documents are an opt-in behind a build flavour that can drop `MANAGE_EXTERNAL_STORAGE` without code changes (the Nextcloud `PermissionUtil` pattern, scout). Folders other than `Download/` may use SAF tree grants.
- **Background work (C20–C22, C26):** on Play, the `dataSync` declaration and any demo video are needed only if the app uses an FGS. A WorkManager-only design avoids the declaration but gives up long seeding runs. B2 (ADR-0018) owns the design; B3's constraint is: declare `dataSync` only, never `specialUse`, and keep FGS use inside 6 h per 24 h.
- **Battery exemption (C23):** leave `REQUEST_IGNORE_BATTERY_OPTIMIZATIONS` out of the Play build; use the settings-list intent and plain-language help instead.
- **Target API (C13):** API 36 now. Budget one upgrade a year in G1 and B2 planning. The same pressure applies off Play because of C12.

### F5. Account deletion vs keep-forever (OD-11): no primary text

- The Play requirement text is blocked. ADR-0002 §2 has redemption create the account, which on its face triggers any "apps that allow account creation" rule.
- Precedents:
  - Immich has no in-app sign-up; accounts are admin-created (C27).
  - Ente separates the deletion request from asynchronous data cleanup (C28).
- The options are in the OD-11 request below. The strongest candidate is **admin-created accounts**:
  - The admin types the person's name and email when generating the invite.
  - Redemption only enrolls a device.
  - The Android app only ever enrolls devices into an existing account, via the QR from another device.
  - As a hedge, an in-app "Leave family backup" request that revokes the device and notifies the admin.
- Whether Play accepts either is unknown. Confidence: low.

### F6. Similar work and lessons

| Project | What they do | Borrow or avoid | Source |
|---|---|---|---|
| Immich | Broad media + `MANAGE_MEDIA` + `dataSync\|shortService` FGS; WorkManager content-URI triggers; admin-created accounts | Borrow the triggers and admin-created accounts; avoid background location | S23 |
| Ente | Broad media, no all-files; in-app deletion with deferred cleanup | Borrow the deferred-cleanup separation if OD-11 needs a deletion flow | S24 |
| Nextcloud | Flavour-specific manifests; lost and regained all-files on Play | Borrow the flavour pattern; plan for losing all-files | S25 |
| Proton Drive | Permissions split across modules; `dataSync` via WorkManager; battery-exemption permission | Note that the merged manifest is what Play sees | S27 |
| Syncthing (official) | Discontinued, citing Play friction; battery-exemption rejection in 2018 | Cautionary: keep an off-Play fallback ready | S28 |
| Syncthing-Fork | Off-Play (GitHub, F-Droid); `specialUse` FGS | Avoid `specialUse` on Play | S30 |

### F7. Tools

bundletool and apkanalyzer (merged-manifest census, B3-S1). The Android Lint check id `PhotoAndVideoPolicy` is inferred from Nextcloud's suppression (docs not read) and is a candidate CI guard for G1. The Android Developer ID Status API and Console API automate package registration (S4, S7).

## Spikes

*Placeholder: a separate spike runner is running B3-S1, B3-S2 and the B3-S3 / H5 Play-registration kits in parallel. It fills in results here.*

| Spike | Hypothesis | Pass → / fail → | Exec tag | Budget IDs | Data class | Status | Result |
|---|---|---|---|---|---|---|---|
| B3-S1 Manifest census | ≥ 2 comparable apps on Play with broad media access and background upload | Pass → broad-media declaration route is plausible; fail → limited distribution becomes primary | CT | — | Public source/APKs only | Spike runner | Scout source-level evidence: C24 (4 apps; merged Play manifests not checked) |
| B3-S2 Account-deletion desk check | A documented compliant flow exists | Pass → ADR-0019 flow; fail → OD-11 design change | CT | BUD-SUPPORT | No personal data | Spike runner | Desk result in F5: **no primary text** |
| B3-S3 Closed-track review dry run | A throwaway-package build with broad media + `dataSync` + deletion flow passes review | Pass → closed track; fail → record reasons, then (a) media only if all-files is refused, (b) limited distribution if Photo & Video or deletion is refused | EXT | BUD-SUPPORT | Synthetic test media only | Kit (spike runner) | — |
| (new) B3-S4 Limited-distribution device kit | Invite, install, self-update, remove and replace a device on 2 phones | Pass → limited distribution is a viable fallback; fail → the fallback is a registered off-Play APK | OL | BUD-SUPPORT | No family data | Proposed | — |

## Conflicts with settled text

- **ADR-0002 §4 / Alternatives** call limited distribution a "Google Play" account (C4). It is an ADC off-Play channel. Choosing it reverses the "sideloaded APK rejected" alternative. That needs OD-10 plus a superseding or amending ADR.
- **ADR-0002 §2** ("Redemption creates the account") vs CLAUDE.md keep-forever, through the Play account-deletion rule (OD-11). Admin-created accounts would amend §2.
- **ADR-0002 §3** (Android QR opens the Play listing, install-referrer token) holds only for the Play channel.
- None of these was edited.

## Open questions

| Question | Who | By when |
|---|---|---|
| Play account-deletion, Photo & Video, FGS, Data safety, prominent-disclosure, all-files and stalkerware policy texts | H1 allowlist for support.google.com and play.google.com, or B3-S3 | Before OD-10/OD-11 are decided (Wave 1 exit) |
| Limited distribution: device counting, removal, replacement, update path, identity shown | B3-S4 kit on owner phones after L06 sign-up | Wave 2 |
| Can a package registered under an ADC limited account later move to a Play Console account? | B3-S4 / ADC Help (blocked) | Before the first real package registration |
| Does review apply to closed tracks, and how long does it take? | B3-S3 | Wave 2 |
| Does the install referrer survive the closed-track opt-in? | E5-S4 | Wave 2 |
| First-install prompt for a registered off-Play APK; silent self-update on real Android 15/16/17 | B3-S4 / B2 | Wave 2 |
| Encryption export and the iOS compliance checklist | B3 (Wave 2) | Before the first store upload |
| 12 vs 20 testers for production | Only if production is ever chosen | — |

## Recommendation

1. **OD-10 channel:** keep the **Play closed testing track** as the primary v1 channel. It is what ADR-0002 settled, and it gives relatives the familiar Play install and automatic updates without "install unknown apps". Make it **conditional on B3-S3**. If Play refuses the broad media permissions or the deletion design, switch to **limited distribution** (if the family's Android devices, counting expected replacements, stay well under 20) or to a registered off-Play APK with self-update. Both fallbacks need an ADR-0002 amendment.
2. **One-way door #12, close now:**
   - The owner generates the app signing key offline and supplies it to Play App Signing ("Export and upload"); never a Google-generated key.
   - Choose the package name under an owner-controlled domain.
   - B3-S3 uses a throwaway package.
3. **Account type:** **personal** (Play). The family has no D-U-N-S, verified website or IRS documents. This matches the intake proposal (Q-E6).
4. **OD-11:** adopt **admin-created accounts**, so the Android app never creates an account. Add a "leave" request in the app that revokes the device and notifies the admin, and never deletes backups. Confirm against the policy text before ADR-0019 is accepted.
5. **Manifest posture for the Play build:**
   - `READ_MEDIA_IMAGES`/`VIDEO` and `ACCESS_MEDIA_LOCATION`, with a Photo & Video declaration.
   - A `dataSync` FGS only (no `specialUse`).
   - No `REQUEST_IGNORE_BATTERY_OPTIMIZATIONS`.
   - `MANAGE_EXTERNAL_STORAGE` only in a documents flavour, if OD-19 wants documents.
   - Target API 36.

**What would change this:**
- The primary policy texts showing that invite-based accounts must allow deletion of backed-up data.
- B3-S3 refusing broad media access.
- B3-S4 showing that limited distribution updates cleanly and handles replacements. That would make it the simpler choice for a ≤ 20-device family, since it carries no Play policy load.

## Decision requests

### OD-10: Android channel; personal vs organisation account
- **Needed by:** Wave 1 exit (the personal vs organisation half at the intake)
- **Evidence:** this note (F1–F3); H5 §6 F1, F3
- **Options:**
  | Option | What it means for the family | Cost (money and owner time) | Reversibility | Risks |
  |---|---|---|---|---|
  | A. Play closed track (personal account) | Install from Play after opting in with a listed Google account; Play updates it | $25; ID check; declarations, Data safety, a yearly target-API bump; review waits | Channel reversible **if the owner holds the signing key** | Play refuses media/all-files access or the deletion design (Syncthing, Nextcloud precedents) |
  | B. ADC limited distribution | Accept an invitation by QR or link; the app updates itself | $0; no ID; per-device authorisation chores (undocumented) | Account moves limited → full only | 20-device cap; replacement handling unknown; a young programme; amends ADR-0002 |
  | C. Registered off-Play APK (full account) | Install from the stick or a link; the app updates itself | $25; ID | As B | "Install unknown apps" prompt; amends ADR-0002 |
  | Organisation account | — | D-U-N-S (up to 28 days), verified website, official documents | Costly | Not applicable to a family |
- **Recommendation:** A, gated on B3-S3, with B as the pre-decided fallback. Personal account. Owner-generated app signing key uploaded to Play App Signing.
- **Touches settled text:** ADR-0002 §4 only if B or C is chosen. Also correct the "Google Play limited distribution" wording in ADR-0002's Alternatives through the superseding draft.
- **If no decision by the deadline:** assume A with an owner-held key; B3-S3 proceeds on a throwaway package; the real package stays unregistered.

### OD-11: Play account deletion vs keep-forever
- **Needed by:** Wave 1 exit
- **Evidence:** this note (F5); the policy text is blocked (no result)
- **Options:**
  | Option | What it means for the family | Cost | Reversibility | Risks |
  |---|---|---|---|---|
  | A. Admin-created accounts; the app only enrolls devices; in-app "leave" request goes to the admin | The admin types names and emails when printing invites; nothing else changes for relatives | A few minutes per invite | Easy | Play may still treat the app as needing deletion (unknown) |
  | B. In-app deletion that deletes the cloud identity (name, email, credentials) and stops backup; stored backups kept by retention exception | The user can delete their account; backups remain until the admin prunes | Build a flow (Ente pattern) | Easy | Whether a "keep-forever family archive" retention reason is acceptable is unknown |
  | C. In-app deletion that also deletes backups | Contradicts keep-forever | — | One-way (data loss) | Breaks CLAUDE.md; a ransomware or coercion path |
  | D. Leave Play (OD-10 B or C) | As OD-10 | As OD-10 | As OD-10 | As OD-10 |
- **Recommendation:** A, plus the B-style identity deletion if the policy text requires it. Never C.
- **Touches settled text:** ADR-0002 §2 ("Redemption creates the account"). C would break CLAUDE.md retention.
- **If no decision by the deadline:** design for A; B3-S3 tests A.

### OD-19 (B3 input; E2 owns the scope question): Documents on Android
- B3 evidence: SAF cannot reach `Download/` (C19). All-files access is allowed for backup apps in Google's summary (C18), but Nextcloud lost it on Play for six months (C25).
- Recommendation from the Play side: v1 = photos and videos; documents only in a flavour that can drop `MANAGE_EXTERNAL_STORAGE`, with SAF for other folders.

### New: design-change request against ADR-0002 §4 wording (for H1 to queue with OD-10)
Correct "Google Play 'limited distribution' account" to "Android Developer Console limited-distribution account (installs outside Play)" in the superseding ADR draft that records OD-10.

## ADR-0019 draft inputs (partial)

- **Decision (proposed):**
  - Channel = Play closed track, gated on B3-S3; fallback = ADC limited distribution.
  - Personal account.
  - Owner-generated app signing key uploaded to Play App Signing; reverse-DNS package under the owner's domain.
  - Admin-created accounts.
  - Manifest posture as in the Recommendation, item 5.
- **Alternatives:** as in the OD-10 table, plus Managed Google Play private apps. These are exempt from target API (C13) but need an organisation or enterprise setup; not researched, so noted only.
- **Consequences:**
  - A yearly target-API bump.
  - Play Console App content chores (Photo & Video, FGS, Data safety, privacy policy URL from D6).
  - The key custody ceremony belongs to D2/D5.
- **Policy dossier (to write after the allowlist or B3-S3):** declaration texts, Data safety draft (working assumption in Q11), FGS declaration and demo-video script, privacy policy with D6.

## Hand-offs

| To | What | Why |
|---|---|---|
| H1 | Re-raise the allowlist for support.google.com and play.google.com; queue OD-10, OD-11 and the ADR-0002 wording correction; update one-way door #12 with F2 | Policy texts decide OD-11 |
| T2 | Item 7: limited distribution is not a Play account (C4); C6 and C7 on package portability | Correct the fact-check |
| B2 | C20, C21, C23, C26, C31 (hibernation); B3's constraints in F4 | ADR-0018 |
| D5 / D2 | App signing key custody; Google may retain a copy (C9) | ADR-0015, ADR-0008 |
| D6 | Data safety working assumption (Q11); EXIF location (C30); privacy policy URL | ADR-0027 |
| E2 | OD-19 evidence (C18, C19, C25) | Scope |
| E5 | Install-referrer test only applies on the Play channel; limited distribution uses its own invitation | ADR-0038 |
| H5 | L05 personal-account steps; L06 is needed for B3-S4; the D-U-N-S lead time only applies to organisations | Long-lead kit |
| G1 | Candidate lint guard `PhotoAndVideoPolicy`; merged-manifest check in CI | Build |
