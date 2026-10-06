# B3. Android distribution channel and Play compliance

- **Workstream:** B3 (see `docs/research/PLAN.md`, section "B3.")
- **Status:** Final for Wave 1 (desk checks, after the three-lens skeptic review and synthesis). Wave 2 items are listed under "Open questions".
- **Date:** 2026-09-29 (last updated 2026-10-06)
- **Feeds:** ADR-0019 (partial draft: `docs/adr/0019-android-distribution-and-play-compliance.md`), OD-10, OD-11, OD-19 (with E2), OD-17 (one new accepted-risk item), one-way door #12; design-change requests against CLAUDE.md "Onboarding and distribution" and ADR-0002 §2, §3 and §4; inputs to B2/ADR-0018, D5/ADR-0015, D1, D3/ADR-0014, D6/ADR-0027, E5/ADR-0038, H5 (L05, L06)
- **Depends on:** T2 (fact-check item 7), H5 (§6 F1–F4), D6 (privacy policy; not started), E2 (OD-19), B2 (background execution; not started), D5 (update trust root; not started)
- **Traceability rows closed or advanced:** R-02 (advanced), R-26 (advanced: OD-11 options rewritten against indexed policy text), Q2-2 (advanced: limited distribution characterised; the 12 vs 20 tester rule is not re-verified)
- **Scope of this run:** Wave 1 desk checks only. Encryption export (EAR, `ITSAppUsesNonExemptEncryption`, French declaration), the iOS compliance checklist and the full policy dossier were **not** done in this run. They move to Wave 2.

## Summary

The two channels in OD-10 differ in kind. On a **Play closed testing track**, Play installs and updates the app, and every Play policy applies. The free **"limited distribution" account** belongs to the **Android Developer Console (ADC)**. It installs apps **outside Play**, on up to 20 devices authorised through a QR code or link (K1, verified). ADR-0002 calls it a "Google Play" account; that is wrong. A third option is an **off-Play APK registered under the same Play Console account**. It has no device cap, and the review found it to be the more logical fallback once a Play account exists.

**Recommendation (medium confidence on the channel; low on account deletion, because the Play policy pages can only be read as search-index snippets):**
- **Channel.** Keep the Play closed track as the primary channel, as settled, gated on the B3-S3 review dry run. The proposed fallback is an off-Play APK registered under the same Play Console account and signed with the same owner-supplied key. Limited distribution is a fallback only if the owner never registers on Play. Both fallbacks change settled text (CLAUDE.md and ADR-0002), so they are owner decisions, not pre-decided.
- **Account type.** Use a personal account.
- **Signing key.** Never accept a Google-generated signing key. The Play build and an off-Play build must be separate flavours. Any off-Play self-updater must also check a detached signature from the project's offline update key, because Google holds a copy of the APK signing key.
- **Account deletion (OD-11).** The search-indexed Play text says deleting an account must also delete its data, with narrow retention exceptions. So the only way to keep "keep forever" is to make sure the **Android app never creates an account**: redemption happens only on the desktop app or a web page, and the phone only enrolls devices. That changes the CLAUDE.md onboarding text, so the owner must decide it.

The review added one finding nobody had raised: on Play, Google and whoever controls the owner's Google account can push an update to every family phone, and the offline update key does not protect that path (F8). That is an accepted-risk item for OD-17.

## Questions

| # | Question | Short answer | Confidence |
|---|---|---|---|
| 1 | Closed track vs limited distribution: install and update path | **Closed track:** Play installs and auto-updates the app after each person opts in with a listed Google account (T2). **Limited distribution:** outside Play, via a "secure handshake ... QR codes or links, user consent on the device, and registration using the Android Developer Console" (K1). Update path: not documented on developer.android.com. Silent self-update is possible only under four conditions, one of them `UPDATE_PACKAGES_WITHOUT_USER_ACTION` (C33). It is untested on a device (K5 contested). | High (channels); Low (self-update) |
| 2 | Do declarations and review apply? | **Closed track:** yes. App content declarations are per app, and FGS types must be declared for targetSdk 34+ (K9). Whether review runs on closed tracks: no primary result. **Off Play:** Play policies do not apply (inference). A Play-distributed app may not update itself by any other route (C35, secondary), so a Play build cannot contain a self-updater. | Medium |
| 3 | Replacement phones, children's devices and removals against the 20 cap | **Not documented on the developer.android.com pages read** (K2, contested as worded). The ADC Help Center was unread (blocked). The sources skeptic reports search-index text from ADC Help 17131204: "up to 20 authorized devices **at any one time**"; authorisation happens on the console's Devices page, with a QR code or a link plus an authorisation code sent back; and at 20 you must remove a device before adding one (C38, secondary, not reproduced by the synthesizer's own search). If that holds, the **owner acts for every new or replacement phone**. | Low |
| 4 | Which developer identity is shown | **No result** for either channel. The limited-distribution contact email "won't be shown publicly" (C2). Whether the payments-profile name appears in the invitation is unknown. Play's public details for personal accounts are on blocked Play Help, and H5-L05 records them. | Low |
| 5 | Can you switch channels without changing package name or key? | **Owner-supplied key: necessary, not sufficient** (K4 verified 2–1; the logic skeptic's restatement is adopted). Moving from Play to off-Play under the **same Play Console account** looks possible (C6, C7, C9). It costs **one manual install of the off-Play flavour on every phone**, because the Play build cannot carry the updater (C34, C35). Moving to a **separate ADC limited account** is undocumented, and ADC's duplicate-package rules favour the existing holder (C42). Account type moves only from limited to full (K3). | Medium |
| 6 | Does automatic whole-camera-roll backup qualify for the Photo & Video declaration? | **Secondary only.** Broad access requires a declaration and a core use that needs persistent access (C16; C43 from the search index). Selected-photos access expires (C17). B3-S1: all 5 comparable apps declare broad media access in their Play-build sources (provisional pass). Approval is unverified, so B3-S3 is the primary route. | Medium (need); Low (approval) |
| 7 | `MANAGE_EXTERNAL_STORAGE` vs SAF for documents | SAF cannot grant `Download/` or the storage root on Android 11+. Google's summary lists backup apps as a likely permitted use of all-files access (K10). Nextcloud lost all-files access on Play for 6 months (K11). The Play-side input to OD-19 is: photos and videos in v1; documents only in a flavour that can drop the permission. | High (facts); Medium (Play outcome) |
| 8 | FGS declaration and demo video vs a UIDT-only design | UIDT jobs must be scheduled while the app is visible, or under the background-activity-launch exemptions, so UIDT alone cannot drive periodic backup (K9). `dataSync` covers backup. For targetSdk 35+ it is limited to 6 h per 24 h and cannot start from `BOOT_COMPLETED` (K9). B2 owns the design. The demo-video text is blocked. | High (platform); Low (review detail) |
| 9 | Battery-optimisation exemption requests | Play prohibits the direct request "unless the core function of the app is adversely affected" (K14). The acceptable-use table is not exhaustive, and it accepts "task automation ... new photo management", which may cover automatic photo backup. This is **a trade-off for B2**, not a settled exclusion (F4). | High (text); Low (enforcement) |
| 10 | Does invite redemption count as in-app account creation? | Indexed Play text: the rule applies if the app "allows users to create an account from within your app" (C36, secondary). Under ADR-0002 §2 and CLAUDE.md, redemption creates the account, so **an Android app that redeems invites is in scope**. An Android app that only takes device-enrollment tokens is probably out of scope (inference). | Medium (secondary text); Low (Play's reading) |
| 11 | Data safety: does admin-decryptable encryption count as "collected"? | **Secondary (search index): yes, collected.** Only data that "end-to-end encryption" makes unreadable to anyone but sender and recipient is excluded (C37). The owner can decrypt as admin, so declare Photos and videos, Files and docs, and Location (EXIF; `ACCESS_MEDIA_LOCATION` plus `setRequireOriginal`, C30). | Medium |
| 12 | Privacy policy URL; prominent disclosure; stalkerware / persistent notification | **No result** (blocked). Carried to D6 and B3-S3 Part A. | — |
| 13 | Developer verification timeline | From 30 Sep 2026, enforced for installs from listed stores (including Play) in BR, ID, SG and TH on certified Android 7+ devices; global in 2027. ADB is exempt (K7). **The primary sources conflict:** the limited-distribution banner says unregistered package names "will no longer be installable on certified Android devices in those regions" (C39), but the FAQ limits this phase to the listed stores. Phase 1 has been live since 2026-09-30. | High (dates); Medium (scope) |
| 14 | Personal vs organisation account | **Personal**, subject to intake questions A5 and E6. Evidence is from the **ADC** pages (K6): organisations need a D-U-N-S number (up to 28 days), a Search Console-verified website and official documents. Play Console's own forms are on blocked Play Help; H5-L05 records them. If the owner already runs a business with a D-U-N-S number and a domain (intake A5), an organisation account becomes possible. | Medium |
| 15 | Target API deadlines | Since 31 Aug 2026, new apps and updates submitted to Play must target API 36, with an extension to 1 Nov 2026 (K8). No testing-track exemption is stated, so closed tracks are covered (inference). | High (text); Medium (tracks) |
| 16 (new) | Does an off-Play build still get automatic updates? | **Possibly, untested** (K5 contested). Four conditions must all hold, including `UPDATE_PACKAGES_WITHOUT_USER_ACTION` (C33), and the code must always handle `STATUS_PENDING_USER_ACTION`. A one-time "install unknown apps" grant per phone is also needed, which conflicts with "users never touch configuration". | Low |
| 17 (new) | Hibernation risk | Unused apps "may be put into hibernation", which resets permissions and stops jobs (C31). Hand-off to B2. One possible mitigation is the unused-app-restrictions settings intent (skeptic suggestion; not researched). | Medium |
| 18 (new) | Is the Play channel covered by the offline update key? | **No.** Play installs whatever Google signs, and the Play Console account holder controls uploads (F8). | High (structure); Medium (attack paths) |
| 19 | Encryption export; iOS compliance checklist | **Not done in Wave 1** (out of scope for this run). | — |

## Method

- **Sweep:** three scouts (docs, source, community), one analyst deep read, a spike runner (B3-S1, B3-S2 and kits for B3-S3, B3-S4 and H5-L05), three skeptics (sources, logic, adversary), then this synthesis.
- **Analyst deep read (2026-09-29):** read 21 developer.android.com pages in full. Checked the Nextcloud `gplay` manifest history with a blobless clone. Read Immich and Ente source on raw GitHub.
- **Skeptics (2026-10-06):** re-read the cited primaries and found newer "Last updated" stamps. Re-verified the Nextcloud commits independently. Used WebSearch, which works again in this session, to read search-index snippets of blocked Play Help pages.
- **Synthesizer checks (2026-10-06):**
  - Re-read the `setRequireUserAction` condition list on the primary page (Last updated 2026-08-03); the fourth condition is confirmed.
  - Re-checked the "Last updated 2026-09-30" stamps and the limited-distribution banner text.
  - Confirmed that the Nextcloud `gplay` manifest at `c8b0a653b6` removes `REQUEST_INSTALL_PACKAGES` with `tools:node="remove"` (raw GitHub). The commit message was not re-read.
  - Ran four WebSearch queries. They reproduced the indexed text of Play Help 13327111 (account deletion), 9888379 (Device and Network Abuse) and the Data safety end-to-end-encryption exclusion. They did **not** reproduce the ADC Help 17131204 snippet.
- **Routes used:** direct (developer.android.com), raw GitHub, a git partial clone, and WebSearch (search-index snippets only; always marked **secondary**).
- **Blocked sources (for H1's allowlist request):**
  - support.google.com: Play Console Help 13327111, 14115180, 13392821, 14151465, 9888379, the Data safety definitions, and the **Android Developer Console Help Center** (17131204, 16604405). The ADC Help Center was missing from the analyst's list.
  - play.google.com: Policy Center.
  - android-developers.googleblog.com, including "Limited distribution accounts are now available", which the limited-distribution guide links.
  - web.archive.org.
  - api.github.com for Nextcloud issues.
  - Context7 (quota exceeded). WebSearch is **no longer** exhausted.
- **Stop rule:** the primary policy texts cannot be reached by any route. Remaining leads need a Play Console, a browser on the owner's machine (B3-S3 Part A) or real devices (B3-S4). Search-index snippets are recorded as secondary and never stand in for the primary text.

## Sources

"Last updated" stamps are as the page showed on the access date. Where a later re-check found a newer stamp, both are given.

| # | Source | Publisher | Version date | Accessed | Primary? |
|---|---|---|---|---|---|
| S1 | Android developer verification (overview) https://developer.android.com/developer-verification | Google | No date on page | 2026-09-29; re-checked 2026-10-06 (skeptic) | Yes |
| S2 | Developer verification guides (index) https://developer.android.com/developer-verification/guides | Google | 2026-08-18 | 2026-09-29; 2026-10-06 (skeptic) | Yes |
| S3 | Limited distribution account https://developer.android.com/developer-verification/guides/limited-distribution | Google | 2026-08-20; **2026-09-30** at re-check | 2026-09-29; 2026-10-06 (synthesizer) | Yes |
| S4 | Developer verification FAQ https://developer.android.com/developer-verification/guides/faq | Google | 2026-08-27; **2026-09-30** at re-check (answers dated 2025-09-03 to 2026-09-30) | 2026-09-29; 2026-10-06 (synthesizer) | Yes |
| S5 | Register on Google Play Console https://developer.android.com/developer-verification/guides/google-play-console | Google | 2026-08-18; **2026-09-30** at re-check | 2026-09-29; 2026-10-06 (synthesizer) | Yes |
| S6 | Full distribution account requirements https://developer.android.com/developer-verification/guides/full-distribution | Google | 2026-08-18 | 2026-09-29; 2026-10-06 (skeptic) | Yes |
| S7 | Register on Android Developer Console https://developer.android.com/developer-verification/guides/android-developer-console | Google | 2026-09-04; 2026-09-30 at re-check (skeptic) | 2026-09-29; 2026-10-06 | Yes |
| S8 | Meet Google Play's target API level requirement https://developer.android.com/google/play/requirements/target-sdk | Google | 2026-09-16; 2026-10-01 at re-check (skeptic) | 2026-09-29; 2026-10-06 | Yes |
| S9 | Foreground service types https://developer.android.com/develop/background-work/services/fgs/service-types | Google | 2026-09-21; 2026-10-01 (skeptic) | 2026-09-29; 2026-10-06 | Yes |
| S10 | Foreground service types are required (Android 14) https://developer.android.com/about/versions/14/changes/fgs-types-required | Google | 2026-09-21 | 2026-09-29; 2026-10-06 | Yes |
| S11 | Android 15 behavior changes https://developer.android.com/about/versions/15/behavior-changes-15 | Google | 2026-09-16 | 2026-09-29 | Yes |
| S12 | Alternatives to dataSync FGS https://developer.android.com/about/versions/15/changes/datasync-migration | Google | 2026-02-26 | 2026-09-29 | Yes |
| S13 | User-initiated data transfer jobs https://developer.android.com/develop/background-work/background-tasks/uidt | Google | 2026-09-16; 2026-10-01 (skeptic) | 2026-09-29; 2026-10-06 | Yes |
| S14 | Manage all files on a storage device https://developer.android.com/training/data-storage/manage-all-files | Google | 2026-09-16; 2026-10-01 (skeptic) | 2026-09-29; 2026-10-06 | Yes |
| S15 | Access documents and other files (SAF) https://developer.android.com/training/data-storage/shared/documents-files | Google | 2026-09-16; 2026-10-01 (skeptic) | 2026-09-29; 2026-10-06 | Yes |
| S16 | Access media files (MediaStore) https://developer.android.com/training/data-storage/shared/media | Google | 2026-09-16 | 2026-09-29 | Yes |
| S17 | Partial photo and video access (Android 14) https://developer.android.com/about/versions/14/changes/partial-photo-video-access | Google | 2026-03-03 | 2026-09-29 | Yes |
| S18 | Optimize for Doze and App Standby https://developer.android.com/training/monitoring-device-state/doze-standby | Google | 2026-08-18 | 2026-09-29; 2026-10-06 | Yes |
| S19 | Sign your app (Play App Signing) https://developer.android.com/studio/publish/app-signing | Google | 2026-03-06 | 2026-09-29; 2026-10-06 | Yes |
| S20 | PackageInstaller.SessionParams reference (`setRequireUserAction`) https://developer.android.com/reference/android/content/pm/PackageInstaller.SessionParams | Google | 2026-08-03 | 2026-09-29; 2026-10-06 (synthesizer, full condition list) | Yes |
| S21 | Identify data collection and sharing (Data safety) https://developer.android.com/guide/topics/data/collect-share | Google | 2026-03-06 | 2026-09-29 | Yes |
| S22 | Play Install Referrer API https://developer.android.com/google/play/installreferrer | Google | 2025-07-21 | 2026-09-29 (scout) | Yes |
| S23 | `immich-app/immich` @ `main` (6cd746a): Android manifest, background worker, `mobile/lib/widgets/forms/login/login_form.dart`, `docs/docs/administration/user-management.mdx`, `docs/docs/administration/oauth.md` | Immich | 2026-09-29 | 2026-09-29; 2026-10-06 (skeptic) | Yes |
| S24 | `ente-io/ente` @ `main` (7a5993c): Photos manifest, `account_deletion_service.dart`, `server/pkg/controller/user/user.go` | Ente | 2026-09-29 | 2026-09-29; 2026-10-06 (skeptic) | Yes |
| S25 | `nextcloud/android`: `app/src/gplay/AndroidManifest.xml` history (e315793137 2024-11-29; 6c20677103 2025-05-27; **c8b0a653b6 2022-12-21**, which removes `REQUEST_INSTALL_PACKAGES`); `AccountRemovalDialog.kt` @ 3c70807 | Nextcloud | as stated | 2026-09-29; 2026-10-06 (skeptics; synthesizer, raw manifest at c8b0a653b6) | Yes |
| S26 | nextcloud/android issues #14409, #14135 | Nextcloud community | as stated | 2026-09-29 (scout) | No |
| S27 | `ProtonDriveApps/android-drive` @ `main` (d1c81cd) | Proton | 2026-09-22 | 2026-09-29 | Yes |
| S28 | `syncthing/syncthing-android` README (discontinued notice); issues #1039, #2064 | Syncthing | Dec 2024 | 2026-09-29 | README yes; issues no |
| S29 | `haiwen/seadroid` @ `master` (9d6d490) manifest | Seafile | 2026-09-28 | 2026-09-29 | Yes |
| S30 | `Catfriend1/syncthing-android` manifest, README | Syncthing-Fork | main | 2026-09-29 | Yes |
| S31 | react-native-cameraroll #618 (Photo & Video policy restatement) | community | 2024-04-29 | 2026-09-29 | No |
| S32 | aj3423/SpamBlocker #664 ("20 users for 14 days") | community | 2026-09-13 | 2026-09-29 | No |
| S33 | T2 `fact-check-adr-0001-0002.md` item 7; H5 `h5-long-lead-items.md` §6 | this repo | 2026-09-29 | 2026-09-29 | Secondary relay |
| S34 | **Search index** of Play Console Help 13327111 "Understanding Google Play's app account deletion requirements" (page blocked) | Google (via search snippet) | n/a | 2026-10-06 (skeptics; synthesizer) | **No (secondary: search index)** |
| S35 | **Search index** of Play Console Help 9888379 "Device and Network Abuse" (page blocked) | Google (via search snippet) | n/a | 2026-10-06 (skeptics; synthesizer) | **No (secondary)** |
| S36 | **Search index** of the Play Data safety help ("end-to-end encryption" exclusion) (page blocked) | Google (via search snippet) | n/a | 2026-10-06 (skeptic; synthesizer) | **No (secondary)** |
| S37 | **Search index** of ADC Help 17131204 "Limited distribution accounts in Android Developer Console" and 16604405 (blocked) | Google (via search snippet) | n/a | 2026-10-06 (sources skeptic only; synthesizer could not reproduce) | **No (secondary, unreproduced)** |
| S38 | **Search index** of Play Console Help 14115180 (Photo & Video permissions) (blocked) | Google (via search snippet) | n/a | 2026-10-06 (skeptic) | **No (secondary)** |
| S39 | B3 spike evidence: `spikes/B3-S1/` (census), `spikes/B3-S2/README.md`, kits `docs/research/kits/B3-S3/`, `B3-S4/`, `H5-L05/` | this repo | 2026-09-29 | 2026-10-06 | Primary (own work) |

## Claims

### Key claims (three-lens skeptic review)

Verdict rule (computed by the run, not by this author): **verified** means at least one primary source **and** at least 2 of the 3 skeptics did not refute. **Secondary only** means there is no primary source. **Contested** covers everything else. Contested and secondary-only claims are never the sole support for a recommendation in this note or in ADR-0019.

| # | Claim (as reviewed) | Notes C# | Sources | Skeptic 1 (sources) | Skeptic 2 (logic) | Skeptic 3 (adversary) | Verdict |
|---|---|---|---|---|---|---|---|
| K1 | Limited distribution is an ADC account for distribution **outside** Play: up to 20 user-authorised devices via a QR or link handshake. ADR-0002's "Google Play limited distribution account" wording is wrong. | C1, C4 | S2, S3 | Upheld (nuance: the owner registers and authorises each device in the console) | Upheld | Upheld | **Verified** |
| K2 | Google does not document how limited-distribution devices are counted, removed or replaced, how updates reach them, or what identity the invitation shows. | C3 | S3, S4 | Refuted: ADC Help 17131204 (search index) documents the "at any one time" cap, authorisation and removal | Refuted: absence claim over an incomplete source set (ADC Help and blog unread) | Refuted: the same, overreach | **Contested** |
| K3 | Account type migration goes one way only: limited → full is supported, full → limited is not. | C5 | S4 | Upheld | Upheld | Upheld | **Verified** |
| K4 | A name used outside Play can be used on Play; a Play Console account can register off-Play apps; Play App Signing accepts a developer key. So an owner-held key keeps the channel reversible, and a Google-generated key closes it. | C6, C7, C9 | S4, S5, S19 | Upheld (misses that the Play build cannot self-update) | Refuted: the key is necessary, not sufficient; reversible to option C under the same account with one reinstall per phone; "new package name" overstated | Upheld (caveats: Google co-holds the key; a manual sideload is needed to leave Play) | **Verified** (2–1; restated per the logic skeptic) |
| K5 | A sideloaded or limited-distribution app can update itself without user action via `setRequireUserAction(USER_ACTION_NOT_REQUIRED)` when it holds `REQUEST_INSTALL_PACKAGES`, is updating itself and targets a recent API. | C12 | S20 | Refuted: omits the fourth condition, `UPDATE_PACKAGES_WITHOUT_USER_ACTION` | Refuted: same omission; the kit inherits it; untested | Upheld (possible, not guaranteed) | **Contested** |
| K6 | Organisation accounts need D-U-N-S (up to 28 days), a verified website and official documents. Individuals need a government ID, proof of address and OTP. ADC full is $25, waived for limited. | C8 | S4, S6 | Upheld (caveat: these are ADC requirements, not Play's) | Upheld (same caveat) | Upheld (same caveat) | **Verified** (for ADC) |
| K7 | Enforced from 30 Sep 2026 only for installs from listed stores (incl. Play) in BR/ID/SG/TH; global in 2027; ADB exempt; unregistered apps install only via the advanced flow or ADB. | C10, C11 | S1, S2, S4 | Upheld (notes the limited-distribution banner reads more broadly) | Upheld | Refuted: the primaries conflict (C39); "advanced flow only" applies only once enforcement reaches the channel | **Verified** (2–1; scope reworded, conflict recorded) |
| K8 | Since 31 Aug 2026, new Play apps and updates must target API 36 (extension to 1 Nov 2026). No testing-track exemption is stated. | C13 | S8 | Upheld | Upheld | Upheld | **Verified** |
| K9 | UIDT jobs can only be scheduled while the app is visible, so UIDT alone cannot run automatic backup. `dataSync` covers backup, 6 h/24 h for targetSdk 35+, no start from `BOOT_COMPLETED`. Apps targeting 34+ declare FGS types in Play Console. | C14, C20, C21 | S9, S10, S11, S13 | Upheld (UIDT "only while visible" slightly overstated) | Upheld (same nuance) | Upheld (same nuance) | **Verified** (wording fixed in C21) |
| K10 | SAF cannot grant `Download/` or the storage root on Android 11+. Google's summary lists backup apps as a likely permitted use of `MANAGE_EXTERNAL_STORAGE`. | C18, C19 | S14, S15 | Upheld | Upheld | Upheld | **Verified** |
| K11 | Nextcloud removed all-files access from its Play flavour on 2024-11-29 and re-enabled it on 2025-05-27 (first in stable-3.32.0). Play's acceptance is inferred. | C25 | S25 | Upheld | Upheld | Upheld | **Verified** |
| K12 | The Play Photo & Video, account-deletion, Data safety and FGS policy texts could not be read, so the answers on OD-11 and the Photo & Video declaration are no result or secondary only. | C29 | blocked-source log | Upheld (partly outdated: search snippets now exist) | Upheld | Upheld | **Secondary only** |
| K13 | OD-11 precedents: Immich's mobile app has no sign-up and accounts are created by the admin; Ente marks accounts deleted and schedules data cleanup asynchronously. | C27, C28 | S23, S24 | Upheld (caveats: Immich OAuth auto-register; Ente still deletes) | Upheld (Ente defers deletion, does not retain) | Upheld (Immich deletes the library 7 days after removal) | **Verified** (caveats in C41) |
| K14 | Play prohibits the direct battery-exemption request unless the core function is adversely affected; backup is not in Google's acceptable-use table. | C23 | S18 | Upheld (the table is not exhaustive) | Upheld (the "new photo management" row) | Upheld (same) | **Verified** (the inference is weakened, see F4) |

**Restatements of the contested claims (used in this note; not re-tallied, so still treated as contested):**
- **K2 →** "The developer.android.com limited-distribution guide, ADC guide and FAQ (read 2026-09-29 and 2026-10-06) do not document device counting, removal, replacement, the update path or the identity shown. The ADC Help Center is unread (blocked). Its search-index text, as reported by one skeptic, documents the at-any-one-time cap, owner-side authorisation and removal (C38)."
- **K5 →** "Silent self-update is documented as **possible, not guaranteed**. It requires a granted `REQUEST_INSTALL_PACKAGES`, `USER_ACTION_NOT_REQUIRED`, a target API that meets the moving minimum, the app updating itself (or being the update owner or installer of record), **and** a declared `UPDATE_PACKAGES_WITHOUT_USER_ACTION`. The code must always handle `STATUS_PENDING_USER_ACTION`. Not device-tested." The condition list itself is primary and re-checked (C33). What stays contested is the conclusion that ADR-0002's "no automatic updates" objection is weakened.

### Supporting claims

"Via K#" means the claim's status follows from that key claim. Claims C33 onward were **added at synthesis** from evidence the skeptics raised. They are not part of the tally, so the run's verdict rule does not mark them verified. They are used only as **constraints** (things that cannot be done) or beside a verified claim, never as the sole support for a positive recommendation.

| # | Claim | Sources | Status |
|---|---|---|---|
| C1 | Limited distribution: "up to 20 devices that end-users have explicitly authorized", QR or link, consent, ADC registration; "Hobbyist: share with family and friends". | S2, S3 | Verified via K1 |
| C2 | Limited sign-up: Google Account with 2-Step Verification, payments profile (legal name and address), a contact email that "won't be shown publicly", no government ID. | S3 | Primary, not key-reviewed |
| C3 | Device counting, removal, replacement, update UX and identity shown are not documented on the developer.android.com pages read. Google warns that "registering package names and authorizing devices can take some time". | S3, S4, S7 | **Contested via K2** (narrowed wording above) |
| C4 | ADR-0002's "Google Play 'limited distribution' account" is inaccurate. | S1–S3; ADR-0002 line 64 | Verified via K1 |
| C5 | "We would support migrating limited distribution accounts to full accounts but not the other way around" (FAQ, 2026-06-08). | S4 | Verified via K3 |
| C6 | Play registers the package name when the app is created. "If you have been using the name outside of Google Play, you can still use it on Google Play." | S5 | Verified via K4 |
| C7 | Play Console can "register apps you distribute outside of Google Play"; Play App Signing apps are claimed automatically. | S4, S5 | Verified via K4 |
| C8 | **ADC** full distribution: individual = government photo ID, proof of address, OTP email and phone; organisation adds D-U-N-S ("up to 28 days"), Search Console website, official documents. $25, waived for limited ("similar to Play's $25 registration fee"). Play Console's own form is unread. | S4, S6 | Verified via K6 (ADC only) |
| C9 | Play App Signing: developer may "Export and upload" its own key; "provide your own signing key" to use the same key across stores. "You cannot retrieve a copy"; "Google may retain a backup copy". If the developer does nothing, Google generates the key. | S19 | Verified via K4 |
| C10 | 30 Sep 2026: listed stores (Play, HONOR, OPPO, Galaxy Store, Palm Store, V-Appstore, GetApps) in BR/ID/SG/TH on certified Android 7+; global 2027. | S1, S2, S4 | Verified via K7 |
| C11 | ADB installs never need verification. **Once enforcement covers a channel** (2027 for sideloads), unregistered apps install or update only with the advanced flow (developer mode, one-day wait, biometric) or ADB. | S4 | Verified via K7 (time-qualified) |
| C12 | Original self-update claim (three conditions). | S20 | **Contested via K5**; superseded by C33 |
| C13 | Target API 36 for submissions since 31 Aug 2026, extension to 1 Nov 2026; existing apps need 35+ to stay visible to new users; only exemption "permanently private apps ... in a specific organization". | S8 | Verified via K8 |
| C14 | Apps targeting 14+ declare FGS types in Play Console (Policy > App content); `specialUse` subtypes are reviewed. | S9, S10 | Verified via K9 |
| C15 | Syncthing's official Android app was discontinued in Dec 2024, citing Play publishing friction. | S28 | Context |
| C16 | `READ_MEDIA_IMAGES`/`VIDEO` "are restricted to specific use cases outlined in the Google Play policy". | S16 | Primary (developer docs); the policy itself is secondary only |
| C17 | Selected-photos access "expires eventually"; automatic whole-library backup needs full media permissions. | S17 | Primary, not key-reviewed |
| C18 | All-files: request only when SAF or MediaStore cannot do the job; "Backup and restore apps", "Document management apps" are likely uses. | S14 | Verified via K10 |
| C19 | `ACTION_OPEN_DOCUMENT_TREE` cannot grant the storage root, SD-card roots or `Download/` on Android 11+. | S15 | Verified via K10 |
| C20 | `dataSync` covers "Backup-and-restore operations"; 6 h/24 h for targetSdk 35+; no launch from `BOOT_COMPLETED`. | S9, S11 | Verified via K9 |
| C21 | UIDT jobs "must be scheduled while the application is visible to the user (or in one of the allowed conditions)", such as an app allowed to start activities from the background. Inference: UIDT alone cannot drive periodic automatic backup. | S13 | Verified via K9 (reworded) |
| C22 | "In most cases, WorkManager is the best option"; long-running workers inherit FGS limits. | S12 | Primary, not key |
| C23 | Doze: the direct-request prohibition; "Most apps" may open `ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS`; the table "highlights several use cases" and accepts "Task automation app ... new photo management". | S18 | Verified via K14 (non-exhaustive table) |
| C24 | Immich, Ente, Nextcloud, Proton and Seafile declare broad media access in the sources of their Play builds (B3-S1). | S23–S25, S27, S29, S39 | Primary (source); Play-served manifests unverified |
| C25 | Nextcloud's all-files history (removed 2024-11-29, re-enabled 2025-05-27). | S25 | Verified via K11 |
| C26 | Immich promotes its worker to a `dataSync` FGS only when the app is battery-exempt. | S23 | Primary (scout read), not key |
| C27 | Immich mobile has no sign-up form; the admin creates users. | S23 | Verified via K13 (caveat C41) |
| C28 | Ente: challenge, then `DELETE /users/delete`; the server calls `markAccountDeletedAndScheduleCleanup`. The data is **still deleted, later**. | S24 | Verified via K13 |
| C29 | The Data safety definitions are on blocked Play Help. | S21 | Secondary only via K12; now partly answered by C37 (secondary) |
| C30 | Unredacted EXIF location needs `ACCESS_MEDIA_LOCATION` plus `setRequireOriginal()`. | S16 | Primary, not key |
| C31 | Unused apps "may be put into hibernation", which resets runtime permissions and stops jobs. | S8 | Primary, not key |
| C32 | 12 (T2) vs 20 (2026 post) testers before production for new personal accounts. | S33, S32 | Secondary only; irrelevant unless production is chosen |
| C33 | `setRequireUserAction`: user action is skipped only when all hold: `USER_ACTION_NOT_REQUIRED`; target API "34 or higher on Android B (API 36)", "35 or higher on Android C (API 37)"; the installer is the update owner, the installer of record or "Updating itself"; and "The installer declares the `UPDATE_PACKAGES_WITHOUT_USER_ACTION` permission". "The target API level requirement will advance"; "Session owners should always be prepared to handle `STATUS_PENDING_USER_ACTION`." | S20 | Primary, re-checked 2026-10-06; added at synthesis (raised by 2 skeptics) |
| C34 | Nextcloud's `gplay` manifest removes `REQUEST_INSTALL_PACKAGES` (`tools:node="remove"`) at commit c8b0a653b6 (2022-12-21). Commit message as quoted by two skeptics: "Google Play won't let us publish updates with this permission". | S25 | Primary (code checked by synthesizer; message not re-read); added at synthesis |
| C35 | "An app distributed via Google Play may not modify, replace, or update itself using any method other than Google Play's update mechanism." | S35 | **Secondary (search index)** |
| C36 | Account deletion applies "if your app allows users to create an account from within your app". It requires an in-app path **and** a web link. "When you delete an app account based on a user's request, you must also delete the user data associated with that app account"; data may be kept only "for legitimate reasons such as security, fraud prevention or regulatory compliance", disclosed to users; "temporary account deactivation, disabling, or 'freezing' ... does not qualify". | S34 | **Secondary (search index)** |
| C37 | Data "sent using end-to-end encryption" (unreadable by anyone other than sender and recipient) need not be disclosed as collected. | S36 | **Secondary (search index)** |
| C38 | ADC Help 17131204: "up to 20 authorized devices at any one time"; devices are authorised on the Devices page with a friendly name, by QR code or by a link to which the contact replies with an authorisation code; at 20, "you will need to remove an existing device before you can add a new one". A secondary summary says the cap covers all apps on the account. | S37 | **Secondary (search index), reported by one skeptic, not reproduced** |
| C39 | The limited-distribution page (2026-09-30) says: "Any package names not registered by this date will no longer be installable on certified Android devices in those regions." This conflicts with the FAQ, which limits the phase to listed stores. | S3, S4 | Primary, re-checked 2026-10-06; **conflicting primaries** |
| C40 | Whoever controls the Play Console account can request an upload-key reset (app-signing page, as cited by the adversary skeptic). | S19 | Primary, not re-read by synthesizer; added at synthesis |
| C41 | Immich OAuth "Auto Register" (default true) creates accounts on first sign-in, including from the mobile OAuth login. Immich deletes a removed user's library after 7 days by default. | S23 | Primary (Immich docs, as read by skeptics); added at synthesis |
| C42 | ADC duplicate package names are allocated by install-share rules or an "appeal-like process"; with few installs, registration is first come, first served. | S7 | Primary as reported by two skeptics; not re-read; added at synthesis |
| C43 | Photo & Video: broad access needs a declaration and a core use case that needs persistent access. | S38 | **Secondary (search index)** |

## Findings

### F1. The channels differ in kind (K1, K6, K7; C2, C38)

| | Play closed testing track | Off-Play APK under the **same Play Console account** (option C) | ADC limited distribution (option B) | Unregistered APK |
|---|---|---|---|---|
| Installs from | Play Store | USB stick or link | Invitation (QR or link) plus consent on the device | Anywhere |
| Device cap | Tester list (T2: up to 2,000 emails) | None | 20 **at any one time** (C38, secondary) | None |
| Who acts per new device | Relative opts in with a listed Google account | Relative installs; one "install unknown apps" grant | **Owner** authorises in the ADC; relative scans or returns a code (C38, secondary) | Relative |
| Updates | Play auto-update | App self-update, untested (K5 contested, C33) | Same as option C | Advanced flow or ADB once enforced (C11) |
| Play policies | Apply | Do not apply (inference) | Do not apply | Do not apply |
| Owner identity check | Play personal account (form unread; ADC equivalent in C8) | Already done for Play | None (payments profile only) | None |
| Cost | $25 once | $0 extra | $0 | $0 |
| Settled text | As settled (CLAUDE.md; ADR-0002 §4) | **Changes** CLAUDE.md "Android ships via Google Play" and ADR-0002 §4 | **Changes** the same, plus ADR-0002 §3 "Adding devices never requires the admin" | Rejected (ADR-0002) |

Confidence: high on the Play and ADC basics; low on the limited-distribution device lifecycle.

**Why option C rather than option B as the fallback.** The logic skeptic's point is accepted. Once option A has been tried, a verified personal Play Console account exists. Option B's advantages (free, no ID check) are then gone. Its drawbacks remain:
- the 20-device cap;
- owner action for each new or replacement phone;
- a second developer account;
- a cross-account package claim that Google does not document, and that ADC's allocation rules (C42) make uncertain.

Option C uses the account the owner already has, has no cap, and needs no package transfer (C6, C7). B stays an option only on the branch where the owner never registers on Play.

### F2. Reversibility: the owner-supplied key is necessary but not sufficient (K4, C9, C33–C35, C42)

- **If Google generates the app signing key,** any off-Play build is signed with a different key. Every phone must uninstall and reinstall to change channel, and loses local state. (The analyst's "new package name" was an overstatement, because ADC allows several keys per package.)
- **If the owner supplies the key,** a later off-Play build with the same key updates the Play install in place. Leaving Play still costs **one manual install of the off-Play flavour on every phone**:
  - The Play build cannot contain the self-updater or `REQUEST_INSTALL_PACKAGES` (C34, C35 secondary).
  - Play is the installer of record, so the first off-Play install may prompt (C33).
- **Two flavours from day one.** `play` has no `REQUEST_INSTALL_PACKAGES`, no `UPDATE_PACKAGES_WITHOUT_USER_ACTION` and no updater code; G1 adds a merged-manifest CI guard for this. `direct` has those three things. Both share the package name and key. Changing channel is then a reinstall, not a rebuild.
- **The key is co-held once uploaded.** "Google may retain a backup copy" (C9), so after upload the key is held by both the owner and Google. See F8 for what that means for the off-Play updater.
- **Separate keys per channel** is the alternative. It keeps the off-Play key owner-only, but changing channel then means uninstalling and reinstalling. Recorded as an option for D5. Not recommended, because it gives up in-place migration.
- **Timing (the logic and adversary skeptics' points are accepted).** Only the *policy* can close now: "supply an owner key; never accept Play's default". The key itself is generated at the D2/D5 ceremony (ADR-0008/0015). The package name is fixed once the domain is chosen (H5 L03).
- **Squatting window.** The ADC allocates little-used package names first come, first served (C42, not re-read). The real package name should therefore be registered (Play app creation or ADC) **before any build carrying it leaves the owner's machines**. B3-S3 keeps using a throwaway name.

Confidence: medium.

### F3. ADR-0002's objections to sideloading: possibly weaker, pending B3-S4 (K5 contested, C11, C33)

ADR-0002 rejected sideloading because of "security warnings, no automatic updates". Three points stand after review:
- **Automatic updates:** possible in principle, under all four conditions in C33, with a prompted fallback that is always needed. They are untested on a device. The one-time "install unknown apps" grant on each phone is itself a configuration step for the relative (CLAUDE.md: users "should never touch configuration").
- **Warnings:** registered apps avoid the advanced flow. Whether the first install prompts is undocumented.
- **Conclusion:** "possibly weakened, pending B3-S4". This finding does **not** support choosing an off-Play channel. It only says the fallback is worth testing.

### F4. Play compliance of the app as designed (constraints B3 supplies to ADR-0018 and ADR-0004)

B2 owns the Android design (ADR-0018) and E2 owns the scope (ADR-0004, OD-19). B3 supplies these **Play-build constraints**:

- **Photo & Video (C16, C17, C24, C43):** full `READ_MEDIA_IMAGES`/`VIDEO` plus `ACCESS_MEDIA_LOCATION` (C30), with a declaration whose core use is "automatic backup of the whole library". B3-S1 found the same set in all 5 comparable apps, but only at source level (provisional). The outcome is **secondary only** until B3-S3. `MANAGE_MEDIA`, which Immich uses, has not been evaluated and is left to B2.
- **All-files (K10, K11):** documents only in a flavour that can drop `MANAGE_EXTERNAL_STORAGE`. If B3-S3 refuses all-files access, the pre-decided fallback (PLAN B3-S3) is media only.
- **FGS (K9):** declare `dataSync` only, never `specialUse`, and stay within 6 h per 24 h. UIDT is fine for "back up now" but cannot be the sole mechanism.
- **Battery exemption (K14, C23, C26):** **an open trade-off for B2**, not an exclusion (both the logic and adversary skeptics said so).
  - The prohibition is real, but the acceptable-use table is not exhaustive, and its "task automation ... new photo management" row may cover automatic photo backup.
  - Immich promotes to an FGS only when the app is exempt. Nextcloud and Proton declare the permission and publish on Play.
  - Leaving it out may cost BUD-TTS reliability.
  - B3-S3 should test it as a separate variant (kit amendment 4), so that it does not confound the main verdict.
- **Self-update:** forbidden in the Play flavour (C35, secondary; C34 precedent). See F2.
- **Target API (K8):** 36 now; plan one upgrade a year (G1, B2). The off-Play updater faces the same pressure (C33: "will advance").
- **Data safety (C37, secondary):** the owner can decrypt as admin, so declare Photos and videos, Files and docs, and Location as **collected**. This goes to D6.

### F5. Account deletion vs keep-forever (OD-11): the indexed text narrows the options (K12, K13, C36, C41)

The primary text is still blocked. The search-index text (C36, secondary) is consistent across the skeptics' searches and the synthesizer's. It says:
- the rule is triggered by account creation **from within the app**;
- deleting an account must also delete "the user data associated with that app account";
- retention is allowed only for "security, fraud prevention or regulatory compliance";
- "deactivation, disabling, or freezing" does not count as deletion.

What follows, if that text is right:
1. **Option B is weak.** Deleting the identity while keeping the backups under a "family archive" reason is not one of the listed retention reasons.
2. **A "leave" request that deletes nothing does not satisfy the rule once it applies.** So the only way to keep keep-forever on Play is to make sure **the rule does not apply**: the Android app never creates an account.
3. **Under ADR-0002 §1, the Android app can be reached from the invite card's Play QR.** If the Android app accepts invite codes, it creates accounts. The cleanest fix is **option A′, suggested by the logic skeptic**:
   - Invite redemption happens only in the desktop app, or on a small redemption web page for a person with no computer.
   - The Android app accepts only device-enrollment tokens from the wizard (ADR-0002 §3).
   - This keeps the CLAUDE.md wording "Redeeming it creates an account", but moves where redemption happens.
   - It changes ADR-0002 §1 (the card's QR would point to redemption, not to Play) and the phone-only path. E1's census must count phone-only relatives.
4. **Option A (the admin creates the account when generating the invite)** also takes account creation out of the app. It changes the CLAUDE.md text ("Redeeming it creates an account ... verified by email"), not only ADR-0002 §2. Email verification would move to invite generation or to first redemption.
5. **A "leave" flow is still useful** as user-facing courtesy and a privacy feature (D6), but it is not compliance cover. The adversary skeptic's point is accepted. Any identity deletion must be:
   - **actioned by the admin** after out-of-band confirmation to the verified email, with a delay window;
   - never triggerable by a single device credential, because one stolen phone could otherwise stop a person's backups on all their devices ("treat the cloud API as under attack").
   A public web form, if one is used, is a rate-limited request, never an action.
6. **Precedents are weaker than first stated (C41).** Immich auto-registers OAuth users on first sign-in by default, including from mobile, and deletes a removed user's library after 7 days. Ente defers deletion; it does not retain data. Neither is a precedent for keeping data after a deletion request. Nextcloud's request-to-operator flow (B3-S2) is the closest match, and whether Play accepted it is unverified.

Confidence: low for "does the rule apply under A or A′", which B3-S3 tests. Medium that option B does not comply if the rule applies.

### F6. Similar work and lessons

| Project | What they do | Borrow or avoid | Source |
|---|---|---|---|
| Immich | Broad media, `MANAGE_MEDIA`, `dataSync\|shortService` FGS; WorkManager content-URI triggers; admin-created users, but OAuth auto-register | Borrow the triggers; admin creation is only a partial precedent (C41) | S23 |
| Ente | Broad media; in-app deletion with deferred cleanup that still deletes | A precedent for asynchronous deletion only | S24 |
| Nextcloud | Flavour-specific manifests; lost and regained all-files access; no `REQUEST_INSTALL_PACKAGES` in `gplay`; deletion request goes to the operator | Borrow the flavour pattern and the operator-request flow | S25 |
| Proton Drive | Permissions split across modules; `dataSync`; battery-exemption permission | The merged manifest is what Play sees | S27 |
| Syncthing (official) | Discontinued citing Play friction | Cautionary: keep the off-Play flavour buildable | S28 |
| Syncthing-Fork | Off Play (F-Droid, GitHub); `specialUse` FGS | Avoid `specialUse` on Play | S30 |

### F7. Tools and update channels

- bundletool and apkanalyzer for the merged-manifest census (B3-S1 owner-lab step).
- A lint check named `PhotoAndVideoPolicy` (inferred from Nextcloud's suppression) as a candidate G1 guard.
- The ADC Developer ID Status API and Console API (S4, S7).
- **For off-Play updates (missed alternative, both skeptics):** a self-hosted F-Droid-format repository, or an existing updater client such as Obtainium, instead of a hand-written updater. Each still needs the C33 conditions or a prompt, plus a separate app or configuration on the phone (against "users never touch configuration"). Not researched; recorded for Wave 2.
- **Play internal testing track (missed alternative, all three skeptics):** not compared. Its tester cap and whether review differs need primary verification. Added to B3-S3 as an optional arm (kit amendment 5).
- **Managed Google Play private app:** the only target-API exemption Google states (C13). It needs an organisation or EMM setup, which conflicts with the personal-account choice. Not researched.
- **Hybrid:** Play for most phones, plus the off-Play flavour for one or two edge devices (for example, a child's phone without a suitable Google account). Possible with the two-flavour design; depends on E1's census.

### F8 (new). The Play channel is an update path the offline key does not cover (adversary skeptic; C9, C40)

ADR-0002 §5 says the offline update-signing key is "the only thing preventing a compromised update channel from pushing malware to every family device". **That guarantee does not cover Android on Play.**
- Play installs whatever is signed with the app signing key, and Google holds that key (C9).
- Whoever controls the owner's Google account controls uploads and can request an upload-key reset (C40).
- A malicious build would get the media permissions and the device credential. It could read photos **in plaintext on the phone before encryption** and send them anywhere, bypassing the homelab-only trust model. Backups already stored stay safe, because devices cannot decrypt or delete them (ADR-0001).

Mitigations to hand to D1 and D5:
- Advanced Protection or hardware security keys on the owner's Google account.
- The fewest possible Play Console users.
- Managed publishing, so that nothing goes live without an explicit owner action.
- Alerts on new releases and on upload-key reset requests.
- The upload key held in hardware or offline.

An app cannot check its own update before Play installs it, so this is a **residual risk to record under OD-17**, not something to design away.

For the **off-Play flavour**, the offline-key rule can and must hold. The updater verifies a detached minisign/Ed25519 signature from the project's offline update key (the same scheme as the desktop, D5) **before** committing the `PackageInstaller` session. Platform certificate continuity alone is not enough, because the APK key is co-held by Google.

## Spikes

| Spike | Hypothesis | Pass → / fail → (decision) | Exec tag | Budget IDs | Data class | Status | Result |
|---|---|---|---|---|---|---|---|
| B3-S1 Manifest census | ≥ 2 comparable apps on Play with broad media access and background upload | Pass → the broad-media declaration route is plausible; fail → Play primary channel at risk (OD-10) | CT | — | `PUB → results` | **Pass (source-level, provisional)** | 5 of 5 Play-build sources declare `READ_MEDIA_IMAGES`/`VIDEO`; all use WorkManager, 4 of 5 a `dataSync` FGS; none UIDT; all-files 2/5; battery exemption 2/5; `ACCESS_MEDIA_LOCATION` 4/5. Each repo has first-party evidence of Play publishing. **Not verified:** the merged manifests Play serves, and whether each app is live today. Stays provisional until the owner-lab apkanalyzer step runs. Evidence: `spikes/B3-S1/README.md`, `census.py`, `census.json`. |
| B3-S2 Account-deletion desk check | A documented compliant flow that never deletes backups exists | Pass → flow into ADR-0019; fail → design change to OD-11 | CT | BUD-SUPPORT (not measured) | `PUB → results` | **Inconclusive, so the fail branch applies** | No primary text. At synthesis, the indexed text (C36) makes the spike runner's candidate A+B flow (keep backups after deleting the identity) unlikely to comply if the rule applies. The flow is re-scoped to A′/A plus an admin-actioned leave request (F5). New precedent: Nextcloud's request-to-operator flow. Evidence: `spikes/B3-S2/README.md`. |
| B3-S3 Closed-track review dry run | A throwaway-package build with broad media, `ACCESS_MEDIA_LOCATION`, a `dataSync` FGS, UIDT for "back up now", optional all-files access and the OD-11 flow is approved | Pass → closed track stays primary; all-files refused → media only (pre-decided, PLAN); Photo & Video or deletion refused → OD-10 fallback request (option C) and verbatim policy text to OD-11; FGS refused → B2 re-plans | EXT | BUD-SUPPORT | `SYN+LAB → results` | **Kit-ready** (needs L05 and a build) | Kit `docs/research/kits/B3-S3/` (README, `declarations-draft.md`, `dryrun-AndroidManifest.xml`). Part A has the owner save the blocked policy texts verbatim from a browser. Apply kit amendments 1–5 below first. |
| B3-S4 Off-Play lifecycle on two phones (proposed; **not in PLAN**, H1 to add) | Off-Play install, manual update and silent self-update work; under limited distribution, remove and replace work | Pass → the off-Play flavour is a viable fallback (option C; B if chosen); fail → Play only, and the risk is recorded | OL | BUD-SUPPORT (≤ 2 h/month; project owner minutes per device operation per month) | `SYN → results` | **Kit-ready**, but needs kit amendments 6–9 before use | Kit `docs/research/kits/B3-S4/README.md`. As written it would probably fail step 2b for a reason unrelated to the hypothesis: v2 and v3 lack `UPDATE_PACKAGES_WITHOUT_USER_ACTION`. |
| H5-L05 Play (and optional ADC) registration | A personal Play account registers and verifies with the owner's own ID within the Wave 1 window | Pass → B3-S3 can start; fail → OD-10 decided on paper | EXT | BUD-SUPPORT | `SEC → results` | **Kit-ready** | Kit `docs/research/kits/H5-L05/README.md`. It records the Play form fields, what is public, the verification wait and the verbatim testing requirements (settles C32). It warns against registering the real package name early. Amendment 10 below reconciles that warning with the squatting window. |

No emulator stood in for real hardware or a real Play Console; every Play and device result is still to come.

**Kit amendments (to apply before running; the kits were not edited in this stage):**
1. **B3-S3 Part A:** also save ADC Help 17131204 and 16604405, Play Help 9888379 (Device and Network Abuse) and 14115180, verbatim with URL and date.
2. **B3-S3 deletion flow:** replace the A+B candidate with A′ (the Android app accepts only device-enrollment tokens) plus an admin-actioned "Ask to delete my account" request (out-of-band email confirmation, a delay window, never triggerable by a device credential). Answer the Console's deletion questions on that basis and record exactly what the form asks.
3. **B3-S3 manifest:** add a check that the merged manifest contains no `REQUEST_INSTALL_PACKAGES` or `UPDATE_PACKAGES_WITHOUT_USER_ACTION`.
4. **B3-S3 optional Variant C:** only after Variant A's verdict, resubmit with `REQUEST_IGNORE_BATTERY_OPTIMIZATIONS`, citing the "task automation ... new photo management" row as the core-function justification. Record the outcome for B2.
5. **B3-S3 optional arm:** publish the same build to the **internal testing track** first. Record whether review runs there and how long availability takes, and compare with the closed track.
6. **B3-S4 v2 and v3:** declare `UPDATE_PACKAGES_WITHOUT_USER_ACTION` as well as `REQUEST_INSTALL_PACKAGES`, and verify a detached minisign signature before committing the session (F8).
7. **B3-S4 step 5:** add a prompted-fallback step that handles `STATUS_PENDING_USER_ACTION`. Record whether update ownership or the installer of record blocks a silent update, including a Play-installed v1 being updated by the off-Play v2 (the channel-switch cost in F2).
8. **B3-S4 scope:** steps 1–3 and 7–9 (authorise, remove, replace) are only needed if the owner wants option B. Before the run, read ADC Help 17131204 from the owner's browser. Record the identity shown, the first-install prompt, and whether a removed device's app keeps running and updating.
9. **B3-S4 budget:** project owner minutes per device operation × expected operations per month against BUD-SUPPORT (≤ 2 h/month). Do not leave it as "no threshold".
10. **H5-L05:** keep the throwaway-name rule for B3-S3, but add a step to register the real package name as soon as ADR-0019 and L03 fix it, and before any build carrying it leaves the owner's machines (F2, squatting).

## Conflicts with settled text

Nothing below was edited. Each item is a decision request.

| Settled text | What conflicts | Raised in |
|---|---|---|
| CLAUDE.md "Android ships via Google Play (family closed track)"; ADR-0002 §4 | OD-10 options B and C (off-Play distribution) | OD-10 |
| ADR-0002 Alternatives (line 64): "Google Play 'limited distribution' account" | Factually wrong (K1) | New wording-correction request |
| ADR-0002 §3: "Adding devices never requires the admin" | Option B: the owner authorises each device in the ADC (C38, secondary) | OD-10 |
| CLAUDE.md "end users should never touch configuration"; ADR-0002's rejection of sideloading | Options B and C: an "install unknown apps" grant on each phone (F3) | OD-10 |
| CLAUDE.md "Redeeming it creates an account with just a name and email (verified by email; no password)"; ADR-0002 §2 | OD-11 option A (the admin creates the account) | OD-11 |
| ADR-0002 §1 (the card's QR links to the Play app) | OD-11 option A′ (redemption only on desktop or web; the card's QR must not lead to redemption in the Android app) | OD-11 |
| CLAUDE.md keep-forever retention | OD-11 options B and C, under the indexed Play text (C36) | OD-11 |
| CLAUDE.md "Self-updates must be signed with the project's own offline key and verified by the app"; ADR-0002 §5 | (a) The Play channel is outside this guarantee (F8). (b) Off-Play self-update relying only on the APK key that Google co-holds. The fix for (b) is a detached offline-key signature; (a) goes to OD-17 as an accepted risk | OD-17, D5 |
| CLAUDE.md "Treat the cloud API as under attack" | Self-service identity deletion or a public deletion form (F5) | OD-11 (design constraint) |

## Open questions

| Question | Who | By when |
|---|---|---|
| Primary texts of the Play account-deletion, Photo & Video, FGS and demo-video, Data safety, prominent-disclosure, all-files, Device and Network Abuse and stalkerware policies, and ADC Help 17131204 | H1 allowlist (support.google.com, play.google.com, android-developers.googleblog.com), or B3-S3 Part A from the owner's browser | Before OD-10 and OD-11 are decided (Wave 1 exit) |
| Under A′ or A, does Play still treat the app as allowing account creation? | B3-S3 | Wave 2 |
| Does review run on closed and internal tracks, and how long does it take? | B3-S3 (amendment 5) | Wave 2 |
| Silent self-update of the off-Play flavour on Android 15/16/17; first-install prompt; channel-switch prompt | B3-S4 (amended) | Wave 2 |
| Limited distribution: identity shown, update path, removed-device behaviour | B3-S4 (only if option B is wanted) | Wave 2 |
| Can a package registered to an ADC limited account later be claimed by a separate Play Console account? | ADC Help (blocked) | Before any real registration |
| Install referrer through the closed-track opt-in | E5-S4 | Wave 2 |
| Play-served merged manifests of Immich, Ente, Nextcloud and Proton (apkanalyzer) | B3-S1 owner-lab step | Wave 2 |
| Encryption export (EAR mass-market or publicly-available) and the iOS compliance checklist | B3 Wave 2 | Before the first store upload |
| Full policy dossier (declaration texts, final Data safety form, FGS demo-video script, privacy policy with D6) | B3 Wave 2, after B3-S3 | Gate C |
| Battery exemption vs reliability; hibernation mitigation; `MANAGE_MEDIA` | B2 (ADR-0018) | Gate C |
| How many family members have no computer (phone-only), and how many children's phones lack a suitable Google account | E1 census | Before OD-11 is decided |
| 12 vs 20 testers for production | H5-L05 records it; matters only if production is chosen | — |

## Recommendation

1. **OD-10, channel:** keep the **Play closed testing track** (as settled), **gated on B3-S3**. If Play refuses the media permissions or the account design, the proposed fallback is **option C**: an off-Play `direct` flavour, registered under the same Play Console account and signed with the same owner-supplied key. Option C needs owner approval of a change to CLAUDE.md and ADR-0002 §4, plus a pass from B3-S4. Option B (ADC limited distribution) is only for the branch where the owner never registers on Play. *Support:* K1, K3, K4 and K6 (verified). The self-update viability (K5) is contested, so the fallback stays conditional on B3-S4.
2. **Account type:** **personal**, subject to intake questions A5 and E6. *Support:* K6, verified for ADC. Play's own form is recorded by H5-L05.
3. **One-way door #12:**
   - Decide the **policy** now: an owner-supplied app signing key, never Google's default; reverse-DNS package under an owner-controlled domain; `play` and `direct` flavours sharing package and key; no self-updater or install permissions in `play`.
   - Generate the key at the D2/D5 ceremony.
   - Fix and register the package name once L03 settles, before any build carrying it leaves the owner's machines.
   - B3-S3 uses a throwaway name.
4. **OD-11:** **A′.** Invite redemption happens only in the desktop app or on a redemption web page; the Android app only accepts device-enrollment tokens and so never creates accounts. Option A (the admin creates accounts) is the alternative if the owner prefers it. Add an admin-actioned leave/delete request as a courtesy, never as compliance cover. **Never delete backups.** If the primary text shows the rule applies anyway, the only option compatible with keep-forever is to leave Play (OD-10 option C), and the owner must choose. *Support:* the indexed text (C36) is secondary only, so this recommendation is explicitly provisional until B3-S3 or the allowlist.
5. **Play-build constraints supplied to ADR-0018 and ADR-0004:**
   - `READ_MEDIA_IMAGES`/`VIDEO` and `ACCESS_MEDIA_LOCATION`, with a Photo & Video declaration.
   - A `dataSync` FGS only.
   - No `REQUEST_INSTALL_PACKAGES` or self-updater.
   - `MANAGE_EXTERNAL_STORAGE` only in a documents flavour, if OD-19 wants documents.
   - Target API 36.
   - The battery exemption is B2's trade-off to decide, tested by B3-S3 Variant C.
6. **Off-Play updater (if ever built):** verify a detached signature from the offline update key before every install (F8).
7. **Record the Play update-channel risk** (F8) under OD-17, with the account-hardening mitigations.

**What would change this:**
- **The primary account-deletion text shows the rule does not apply** to apps that never create accounts → A′ is confirmed. If it applies anyway → OD-11 is forced to choose between keep-forever and Play.
- **B3-S3 refuses broad media access** → OD-10 fallback request.
- **B3-S4 shows silent off-Play updates work cleanly** → option C becomes a strong alternative to Play, with less policy load and no Play-channel risk (F8).
- **E1 finds many phone-only relatives** → A′ needs the web redemption page, or option A becomes preferable.

## Decision requests

### OD-10: Android channel; personal vs organisation account
- **Needed by:** Wave 1 exit (the personal vs organisation half at intake, A5 and E6)
- **Evidence:** this note F1–F3, F8; K1, K3, K4, K6 (verified); K5 (contested)
- **Options:**

  | Option | What it means for the family | Cost (money and owner time) | Reversibility | Risks |
  |---|---|---|---|---|
  | A. Play closed track, personal account | Opt in with a listed Google account; install from Play; Play updates | $25; ID check; declarations; yearly target-API bump; review waits | To C: one manual install per phone (owner key) | Play refuses the design; Play update path outside the offline key (F8) |
  | C. Off-Play `direct` flavour under the same Play Console account | Install from the stick or a link; one "install unknown apps" grant; the app updates itself | $0 extra; the owner builds and hosts updates | To A: a Play install over the same key | Self-update untested (K5); changes CLAUDE.md and ADR-0002 §4 |
  | B. ADC limited distribution | Owner authorises each phone; relative scans or returns a code; the app updates itself | $0; no ID; owner action per device (BUD-SUPPORT) | Limited → full only (K3); move to Play undocumented | 20 at any one time; changes CLAUDE.md, ADR-0002 §3 and §4 |
  | Organisation account | — | D-U-N-S (up to 28 days), verified website, documents | Costly | Only if the owner already has a business entity (intake A5) |

- **Recommendation:** A, gated on B3-S3; personal account; owner-supplied key; two flavours. If A fails, the proposed fallback is C, subject to B3-S4 and the owner's approval of the settled-text change.
- **Touches settled text:** C and B change CLAUDE.md ("Android ships via Google Play (family closed track)") and ADR-0002 §4; B also changes ADR-0002 §3.
- **If no decision by the deadline:** assume A with an owner-supplied key; B3-S3 proceeds on a throwaway package; the real package is not yet registered.

### OD-11: Play account deletion vs keep-forever
- **Needed by:** Wave 1 exit
- **Evidence:** F5; C36 (secondary, search index); B3-S2 (inconclusive)
- **Options:**

  | Option | What it means for the family | Cost | Reversibility | Risks |
  |---|---|---|---|---|
  | A′. Redemption only on desktop or a web page; the Android app accepts only device tokens | Phone-only people redeem on a web page; otherwise unchanged | Web redemption page; card QR change | Easy | Play may still read the app as in scope (unknown) |
  | A. The admin creates accounts when generating the invite | The admin types name and email; redemption only enrolls | Minutes per invite; email verification moves | Easy | Changes the CLAUDE.md onboarding text |
  | B. In-app identity deletion; backups kept | User deletes identity; backups stay | Build an admin-actioned flow | Easy | Probably non-compliant under C36; an availability attack if self-service |
  | C. In-app deletion including backups | Contradicts keep-forever | — | One-way (data loss) | Breaks CLAUDE.md |
  | D. Leave Play (OD-10 C) | As OD-10 C | As OD-10 C | As OD-10 | As OD-10 C |

- **Recommendation:** A′ (or A), plus an admin-actioned leave request with out-of-band confirmation. Never C. Escalate to D only if the primary text shows the rule still applies.
- **Touches settled text:** A changes the CLAUDE.md onboarding text and ADR-0002 §2. A′ changes ADR-0002 §1 (the card QR) and the redemption location. B and C put pressure on, or break, CLAUDE.md keep-forever.
- **If no decision by the deadline:** design for A′; B3-S3 tests it.

### OD-19 (B3 input; E2 owns scope): documents on Android
- **B3 evidence:** SAF cannot reach `Download/` (K10). All-files access is likely permitted for backup apps (K10), but Nextcloud lost it on Play for 6 months (K11).
- **From the Play side:** v1 = photos and videos; documents only in a flavour that can drop `MANAGE_EXTERNAL_STORAGE`, with SAF for folders other than `Download/`.

### OD-17 (new item for the accepted-risk register): Play update channel outside the offline key
- **Question:** accept that, on Play, Google and anyone who controls the owner's Google account can ship an update to every family phone that the offline update key does not check (F8)?
- **Options:** (a) accept, with mitigations: Advanced Protection, minimal Console users, Managed publishing, release and key-reset alerts, upload key offline; (b) do not accept, and move to OD-10 option C.
- **Recommendation:** (a), with all the listed mitigations.

### New: correct the ADR-0002 wording (with OD-10)
In the superseding draft that records OD-10, correct "Google Play 'limited distribution' account" to "Android Developer Console limited-distribution account (installs outside Play)".

## Hand-offs

| To | What | Why |
|---|---|---|
| H1 | Allowlist support.google.com (including the **ADC Help Center**), play.google.com and android-developers.googleblog.com. Add B3-S4 to PLAN. Queue OD-10, OD-11, the OD-17 item and the wording correction. Update door #12 with F2 (policy now; key at the ceremony; register the name before the first build leaves). Add S34–S38 to `sources.md` as secondary search-index rows | Run rules; registries are H1's |
| D5 / D2 | Owner-supplied app signing key; co-held once uploaded (C9). Off-Play updater must verify a detached offline-key signature (F8). Option of separate keys per channel. Play Console hardening (F8) | ADR-0015, ADR-0008 |
| D1 | Threats: Play update-channel compromise (F8); identity-deletion availability attack and deletion-form abuse (F5) | Threat register |
| D3 / C1 | Delete or leave requests: admin-actioned, out-of-band confirmed, never device-triggered. Device-only enrollment API for Android (A′) | ADR-0014, ADR-0010 |
| B2 | K9 (UIDT wording), C23/C26 battery trade-off and B3-S3 Variant C, C31 hibernation, `MANAGE_MEDIA`, the `play`/`direct` flavour split | ADR-0018 |
| E5 | A′: where redemption happens; card QR target; install referrer applies only on Play | ADR-0038 |
| E1 | Census: phone-only relatives; children's phones without suitable Google accounts; Android devices and replacements per year | OD-11, OD-10 |
| D6 | Data safety: "collected" (C37, secondary); EXIF location; the privacy policy must not promise deletion of backups beyond what OD-11 decides | ADR-0027 |
| E2 | OD-19 evidence (K10, K11) | ADR-0004 |
| G1 | Merged-manifest CI guard: `play` flavour has no `REQUEST_INSTALL_PACKAGES` or `UPDATE_PACKAGES_WITHOUT_USER_ACTION`; the `PhotoAndVideoPolicy` lint | Build |
| T2 | Item 7: limited distribution is not a Play account (K1); the channel-switch cost (F2) | Fact-check correction |
| H5 | L05 kit amendment 10; L06 needed only if option B is wanted | Long-lead |
