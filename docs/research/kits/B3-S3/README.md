# Kit B3-S3: Play closed-track review dry run

- **Spike:** B3-S3 (workstream B3, see `docs/research/PLAN.md` §"B3."). This is the only Play review dry run; it replaces any duplicates.
- **Exec tag:** EXT (Play review wait), with owner-lab steps
- **Prepared by / date:** B3 spike runner (Wave 1, batch W1-c), 2026-09-29
- **Who runs it:** Owner. A build-phase agent or the owner produces the dry-run app (step 1).
- **Time needed:** hands-on time not measured; record it (BUD-SUPPORT). Review wait **unknown**: the Play Help pages that state review times are blocked from the research container. Record the actual wait.
- **Data-handling class:** `SYN+LAB → results`.
  - The demo video and screenshots use synthetic or LAB test photos only.
  - The test server stores nothing and logs sizes only.
  - Play's rejection or approval emails and the Console's policy texts are copied **verbatim** (as quotes with URL and date) into the results. They are Google's text, not family data.
  - The reviewer credentials (invite code) count as `SEC`, but for a throwaway test family only. Revoke them after the run.

## Purpose

To find out whether Google Play accepts the Android app **as designed** on a closed testing track:

- automatic whole-library backup with broad photo and video access;
- original EXIF location;
- a `dataSync` foreground service for long uploads;
- a UIDT "Back up now" job;
- optionally, all-files access for documents;
- an account-deletion flow that never deletes backups.

Along the way, this kit captures the Play policy texts that are blocked from the research container.

## Hypothesis

A closed-track release of a throwaway-package build with the permission set in `dryrun-AndroidManifest.xml` (Variant A) is **approved**, with these accepted by review or by the Console forms:

- the Photo & Video permissions declaration;
- the `dataSync` foreground-service declaration with a demo video;
- the account-deletion answers from the OD-11 A+B flow (`spikes/B3-S2/README.md` §3).

If all-files access is included, it is the part most likely to be refused (Nextcloud's Play build lost it from 2024-11-29 to 2025-05-27; B3 note C25).

## Decision it informs

ADR-0019 (Android distribution and Play compliance), OD-10 (channel), OD-11 (account deletion vs keep-forever), OD-19 (documents on Android), and one-way door #12 (package name, signing key, channel).

| If the result is… | Then… |
|---|---|
| **Pass**: approved on the closed track (PLAN criterion) | The Play closed track stays the primary channel (ADR-0002, OD-10 option A). The OD-11 A+B flow and the declaration texts go into the ADR-0019 dossier. |
| **Fail: only all-files access refused** | Pre-decided fallback: **media only**. Resubmit Variant B once (step 9). OD-19 records that documents need SAF (without the Download folder) or are left out of v1 on Android. |
| **Fail: Photo & Video declaration refused, or the deletion flow refused** | Record the reasons verbatim. OD-10 falls back to limited distribution (if the family's Android devices stay well under 20, see B3-S4) or to a registered off-Play APK. OD-11 gets the verbatim policy wording. Both need an ADR-0002 amendment (owner decision). |
| **Fail: `dataSync` FGS declaration refused** | Record the reasons. B2/ADR-0018 moves to WorkManager-only plus UIDT for "Back up now", and the long-seed path is re-planned. Resubmit without the FGS type if time allows. |
| **No result** (no account, identity check stuck, or no build) | The Play questions stay "secondary only / no result" in ADR-0019, and OD-10/OD-11 are decided on paper, with the risk recorded. |

## Budget IDs cited

- **BUD-SUPPORT** (owner time ≤ 2 h per month at steady state). Record hands-on minutes for each part, so that the ongoing Play chores (declarations, target-API bumps, reviews) can be estimated. This run does not set a threshold; the pass criterion is approval.

## Equipment

| Item | Exact model or version | Why | Have it? |
|---|---|---|---|
| Google Play developer account, **personal** (L05, $25) | Registered with the `H5-L05` kit | Needed to create the app and the closed track | Buy (H5 L05) |
| A computer with Android Studio | Current stable; Android SDK Platform 36 installed | Builds the signed AAB (target API 36 is required on Play since 31 Aug 2026) | Owner |
| Android phone, Android 14 or later, with Google Play | Any; a lab phone (L12a–c) | Demo video, opt-in and install test | Yes / L12 |
| A second Google account for a tester | A test account, not a relative's | Checks what an invited tester sees | Owner creates |
| A test upload endpoint on HTTPS | A sandbox Worker (H1) or any small server the owner controls, which **accepts and discards** uploads and logs only sizes | The reviewer must be able to use the app | Owner / H1 sandbox |
| Two web pages on the owner's domain | Privacy policy and account-deletion pages (drafts in `declarations-draft.md` §6) | The Console may ask for these URLs (unverified) | Needs L03 |

**Software and files:**
- `dryrun-AndroidManifest.xml`: the permission set under test (Variants A and B).
- `declarations-draft.md`: text for the forms, the demo-video script, Data safety working answers and reviewer instructions.
- The dry-run app itself (step 1).

## Before you start

- [ ] Choose a **throwaway package name**, for example `<reverse owner domain>.dryrun.b3s3`. Creating an app in Play Console registers its package name to the account permanently (H5 F3). **Never** use the real Reliquary package name here.
- [ ] Write down the date and time you start, and keep a running tally of hands-on minutes.
- [ ] Put 20–50 synthetic or LAB photos and 1–2 short test videos on the lab phone. No people, no real family content.
- [ ] Make sure the test upload endpoint discards content, and check its log shows sizes only.

## Procedure

After each step, write down in the results table what you saw. Copy any policy text the Console shows **word for word**, with the page title and the date. Much of the Play policy cannot be read from the research container, so these copies are primary evidence.

### Part A: capture the blocked policy texts (about 30 min, can run any time)

1. On your own computer, open each page below. Save it as a PDF, **outside the repo**, named with today's date. Then paste the paragraphs that answer each question into `results.md`, with the URL and the "last updated" date shown on the page.
   **You should see:** each page loads normally (these are blocked only from the research container).
   - https://support.google.com/googleplay/android-developer/answer/13327111. Account deletion. Answer: does joining through an invite count as account creation? Must the app delete data itself, or may it send a request? Which retention reasons are allowed? Is a web link required?
   - Play Console Help, "Photo and video permissions". Answer: is "backing up the whole library automatically" a permitted core use? What evidence is needed? Do the rules apply to closed tracks?
   - https://support.google.com/googleplay/android-developer/answer/13392821. Foreground-service requirements and the demo video.
   - Play Console Help, "All files access" (`MANAGE_EXTERNAL_STORAGE`). Permitted uses and declaration.
   - https://support.google.com/googleplay/android-developer/answer/14151465. Testing requirements for new personal accounts: tester count and days, and whether closed tracks need them.
   - Play Console Help: the Data safety definitions of "collected", "shared", "encrypted in transit", and the "ephemeral processing" exception.
   - The Play Developer Policy Center pages on the User Data policy (prominent disclosure) and on stalkerware / persistent notifications.

### Part B: build the dry-run app (build step; not done in the container)

2. Create a minimal app (Kotlin, Jetpack WorkManager). Merge the declarations from `dryrun-AndroidManifest.xml` (Variant A) into it. Set `applicationId` to the throwaway name, `targetSdk = 36`, `compileSdk = 36`.
   The app must **really do** what it declares, because reviewers try it:
   - Enrollment by QR code or typed code (a fixed reviewer code is enough).
   - An explanation screen before the photo permission prompt (the prominent-disclosure pattern).
   - A MediaStore scan and upload of photos and videos to the test endpoint. Encryption can be a stand-in; for example, `age` to a test key if a library is handy.
   - WorkManager for routine uploads. A `dataSync` foreground notification with progress and **Pause** for runs longer than a few minutes. "Back up now" as a UIDT job.
   - A health screen: items found, sent, pending.
   - Settings → "Leave family backup" with the two options and the confirmation text from `declarations-draft.md` §6.
   **You should see:** it installs over ADB (no account needed; ADB installs are exempt from developer verification) and uploads the test photos to the endpoint.
3. Generate **your own app signing key** and a **separate upload key** with `keytool`. Store both as described in D2's key inventory (or, until that exists, in a password manager, with a note that they are throwaway).
   Why: this rehearses one-way door #12. Google says: "If you want to use the same signing key across multiple stores, make sure to provide your own signing key when you configure Play App Signing, instead of having Google generate one for you". Once configured, "you cannot retrieve a copy of your app's signing key" (https://developer.android.com/studio/publish/app-signing, last updated 2026-03-06).
4. Build a release **AAB** signed with the upload key.

### Part C: create the app and fill in App content (Console UI paths unverified)

5. In Play Console, create the app with the throwaway name, as a free app. **You should see:** the app dashboard. Record every question the creation form asked.
6. Set up **Play App Signing** and choose the option to **use your own app signing key** (upload the key in the way the Console instructs). Record the options the Console offered, word for word.
7. Go to **Policy → App content** (the path is confirmed for the foreground-service declaration by https://developer.android.com/about/versions/14/changes/fgs-types-required, last updated 2026-09-21) and complete every section the Console lists, using `declarations-draft.md`. For each section, record whether the Console required it for a closed track:
   - Privacy policy URL.
   - App access: reviewer instructions (§7) with a reviewer invite code.
   - Ads (none).
   - Content rating questionnaire.
   - Target audience (adults; not directed at children).
   - Data safety (§5), recording the Console's definitions verbatim.
   - Foreground service types: `dataSync`, with the text and demo video from §2–§3.
   - Photo and video permissions (§1).
   - All files access (§4, Variant A).
   - Account deletion (§6), if asked.
   - Any other declarations shown.
   Record the exact field names, character limits and help text.

### Part D: closed track release and review

8. Create a **closed testing** track. Add a tester list containing your own account and the second test account. Upload the AAB, add release notes, and send it for review.
   Write down the exact submission time. Record whether the Console says the release is "in review", and any stated estimate.
   **You should see:** a review status. Check once a day. Record the time of the decision and the full text of any email.
9. **If rejected only for all-files access:** remove the `MANAGE_EXTERNAL_STORAGE` line (Variant B), remove the All files access declaration if the Console allows it, raise `versionCode`, and resubmit once. Record the outcome the same way.
   **If rejected for anything else:** do not iterate. Record the reasons verbatim and stop. The decision table above says what happens next.
10. **If approved:**
    - On the lab phone, signed in as the second test account, open the tester opt-in link and install from Play.
    - Record every screen a relative would see, with screenshots showing no personal data.
    - Optional, for the ADR-0002 open question: open the Play listing through a link with a `&referrer=` parameter. In the app, log what the Play Install Referrer API returns. Record whether the referrer survived the opt-in flow.
11. Check Android developer verification. In Play Console, record whether the throwaway package shows as registered for developer verification (Play auto-registers the package name of new apps per https://developer.android.com/developer-verification/guides/google-play-console, last updated 2026-08-18).

**Stop and record "No result" if:**
- the developer account is not verified yet;
- the Console refuses the throwaway package name;
- the review has not finished within the time the owner is willing to wait (write down how long you waited).

## Cleaning up

1. After the results are recorded:
   - Unpublish the closed-track release, or leave it with only the test accounts.
   - Revoke the reviewer invite code on the test endpoint, and shut the endpoint down.
2. Keep the throwaway signing and upload keys only as long as the app exists in the Console. The package name stays registered to the account either way.
3. Delete the test photos from the lab phone if they are not needed by another kit.

## Data handling

H3 (`docs/research/h3-research-data-governance.md` §2–§4) applies, with these specifics:

- Only synthetic or LAB media appears in the demo video, the screenshots and the uploads.
- No relative's Google account is used.
- The test endpoint keeps no content.
- The saved policy PDFs stay outside the repo. Verbatim quotes, with URL and date, go into `results.md`.

## Results

Copy this section into `docs/research/kits/B3-S3/results.md` and fill it in. Do not edit numbers afterwards; add a note instead.

- **Run by / date / place:**
- **Play developer account type and creation date:**
- **Throwaway package name:**
- **Phone and Android version used:**
- **Emulator or VM used instead of real hardware?** No | Yes: …

| Step | Expected | What happened | Measurement (with unit) | Screenshot or log |
|---|---|---|---|---|
| 1 Policy texts captured | 7 pages saved and quoted | | pages captured / 7 | |
| 2 Dry-run app works over ADB | Uploads test photos | | photos uploaded | |
| 3 Own signing key generated | Upload key separate | | | |
| 5 App created | Throwaway package accepted | | | |
| 6 Play App Signing | "Use your own key" offered | | options offered (verbatim) | |
| 7 App content sections | Each section recorded | | sections required on closed track | |
| 8 Review | Decision received | | hours from submit to decision | |
| 9 Variant B resubmission (if any) | Decision received | | hours | |
| 10 Tester install | Installs from Play | | screens a relative sees (count) | |
| 10 Install referrer (optional) | Referrer present | | yes / no | |
| 11 Verification registration | Package shows registered | | yes / no | |

| Pass criterion | Budget ID | Measured value | Pass / Fail / No result |
|---|---|---|---|
| Closed-track release approved with the Variant A declarations (PLAN B3-S3) | — | | |
| Owner hands-on time for the whole run (for the BUD-SUPPORT estimate) | BUD-SUPPORT | minutes: | (recorded, no threshold) |

**Verbatim policy texts** (one block per page: URL, "last updated" date, date read, quoted paragraphs):

**Rejection or approval emails** (verbatim):

- **Overall:** Pass | Fail | No result
- **Surprises and points of confusion:**
- **Follow-ups for the workstream:**
