# B3-S3 dry run: draft declaration texts

These are **drafts for the dry run only**. They are not the final policy dossier, which belongs to ADR-0019. Every form's exact fields and character limits are **unverified**, because the Play Console Help pages are blocked from the research container. Fit the text to what the Console actually shows, and record any difference in the kit results.

The texts describe the app as designed: ADR-0001, ADR-0002, and the OD-11 option A+B flow in `spikes/B3-S2/README.md`.

## 1. Photo and video permissions (`READ_MEDIA_IMAGES`, `READ_MEDIA_VIDEO`)

**Core purpose (draft):**

> Reliquary is a family backup app. Its core function is to back up the whole photo and video library on this phone, automatically and in the background, to the family's own backup server at home. It has to find new photos and videos as they are taken, without the user choosing them one by one, and read the original files (including their dates and location data) so the backup is a faithful copy. The system photo picker and "selected photos" access cannot do this: the picker needs the user to choose each item, and selected-photos access only covers items already chosen and is not available for items taken later. Photos and videos are encrypted on the phone before upload; the app does not show, edit, share or analyse them.

**Evidence to attach or show:** the demo video (§3) plus a screenshot of the first-run screen that explains automatic backup before the permission prompt.

## 2. Foreground service type `dataSync`

**Task description (draft):**

> Uploads the user's photos and videos to the family backup server. A foreground service with a visible notification is used only for long transfers, such as the first full backup of an existing library or a large video, so that the transfer is not cut off and the user can see its progress and stop it. Short, routine uploads of new photos run as ordinary background jobs (WorkManager) without a foreground service.

**User impact if deferred or interrupted (draft):**

> If the transfer is deferred or interrupted, the user's photos and videos stay unprotected. The only copy may be on this phone until the upload completes, so a lost or broken phone would lose them. The first backup of a large library can take many hours and would restart repeatedly if interrupted.

**How the user starts it:** the transfer starts automatically after enrollment (first backup), or when the user taps "Back up now". The notification has a "Pause" action.

## 3. Demo video script (for the FGS declaration and the photo/video declaration)

Record the screen of a real phone (Android 14 or later) using **synthetic or LAB test photos only** (H3). Make sure no people, faces, contacts or notifications from other apps appear. Keep it short. The Console may state a length limit; record what it says. Upload the video unlisted wherever the Console asks for a link (for example YouTube unlisted). The Console's requirement is unverified.

| # | Show | Say on screen (caption) |
|---|---|---|
| 1 | Open the app for the first time; the enrollment screen | "Reliquary backs up this phone's photos to the family's home server." |
| 2 | Scan the reviewer QR code or type the invite code | "The family administrator sends an invite; nothing else to set up." |
| 3 | Explanation screen, then the Android permission prompt; choose "Allow all" | "Automatic backup needs access to all photos and videos." |
| 4 | The health screen showing N items found, backup starting | "New and existing photos are found automatically." |
| 5 | Pull down the notification shade: the ongoing "Backing up 1,234 photos" notification with progress and a Pause action | "Long backups run with a visible notification (foreground service, data sync)." |
| 6 | Press Home and open another app; come back after about 30 s: the progress has advanced | "The backup continues while the app is in the background." |
| 7 | The notification disappears when the backup finishes; the health screen shows "All photos backed up" | "When the backup is done, the notification goes away." |
| 8 | Take a new photo with the camera; within a few minutes it shows as backed up, **with no foreground notification** | "Routine new photos upload as normal background work." |
| 9 | Settings → "Leave family backup": show both options and the confirmation text (§6) | "Users can remove the device or ask to delete their account." |

## 4. All files access (`MANAGE_EXTERNAL_STORAGE`), Variant A only

**Core purpose (draft):**

> Reliquary backs up a family's important files, not only photos: scanned documents, PDFs and other records kept anywhere on the phone, including the Download folder. It needs to find these files automatically and back up changed files in the background without the user picking each one. The Storage Access Framework cannot grant access to the Download folder or the root of shared storage on Android 11 and later, which is where most documents on a phone are saved, and MediaStore does not cover non-media files saved by other apps. Files are encrypted on the phone before upload; the app never modifies or deletes the user's files.

(Source for the Storage Access Framework fact: https://developer.android.com/training/data-storage/shared/documents-files, last updated 2026-09-16, read 2026-09-29. On Android 11 (API 30) and higher, `ACTION_OPEN_DOCUMENT_TREE` cannot request access to the root of internal storage, the root of a reliable SD card, or the Download directory.)

## 5. Data safety form: working answers (to be confirmed with D6)

These are a **working assumption** from the B3 note (Q11), because the definitions are on blocked Play Help. Record the Console's own definitions verbatim in the results.

| Data type | Collected? | Shared? | Why | Optional? | Notes |
|---|---|---|---|---|---|
| Photos and videos | Yes | No | App functionality (backup) | No (core) | Encrypted in transit and at rest; the family admin can decrypt them |
| Files and docs | Yes (Variant A) | No | App functionality | No | Same |
| Approximate/precise location | Yes (EXIF inside photos) | No | App functionality | No | Only as embedded in the photo files |
| Name, email address | Yes (entered by the admin) | No | Account management | No | Name and email are held for the admin's nudges and invites |
| Device or other IDs | Yes (device credential) | No | App functionality, security | No | |
| Crash logs / diagnostics | Only if B8 adds telemetry | No | Analytics | Record the actual answer | |

**Security practices:** data is encrypted in transit (yes). "Users can request that data be deleted": answer per the §6 flow, and record the Console's exact wording for this question.

## 6. Account deletion (OD-11 option A+B, from `spikes/B3-S2/README.md` §3)

**In-app path:** Settings → "Leave family backup".

**Confirmation text for "Ask to delete my account" (draft):**

> This asks your family administrator to delete your Reliquary account: your name, email and this device's access. Photos and files already backed up are part of the family archive and are kept until your administrator removes them. Your administrator will act on this request within [N] days.

**Web deletion page (draft URL):** `https://<owner domain>/reliquary/delete-account`. It holds the same text and a form that sends the request to the admin queue (for the dry run, a form that emails the owner is enough).

**Privacy policy URL:** `https://<owner domain>/reliquary/privacy`. D6 owns the text. For the dry run, use D6's draft if one exists; otherwise use a plain page that states §5 and §6 honestly, marked as a draft.

## 7. App access instructions for the reviewer (draft)

> The app needs an invite from a family administrator. Use invite code `<REVIEW-CODE>`, or scan the QR code at `<URL of a PNG>`. It enrolls the phone into a test family whose server accepts uploads and immediately discards them. No personal data is kept.
