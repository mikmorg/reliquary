# Kit B3-S4: limited-distribution device lifecycle on two phones

- **Spike:** B3-S4. **Proposed** by the B3 analyst (`docs/research/b3-android-distribution-play-compliance.md`, Spikes table) and **not yet in PLAN.md**. H1 should add it to the plan if the owner wants the OD-10 fallback tested. It answers the questions in PLAN B3's first bullet that the documentation leaves open.
- **Exec tag:** OL
- **Prepared by / date:** B3 spike runner (Wave 1, batch W1-c), 2026-09-29
- **Who runs it:** Owner
- **Time needed:** hands-on time not measured; record it. Plus the ADC wait for package registration and device authorisation, which Google warns "can take some time".
- **Data-handling class:** `SYN → results`. A throwaway app on lab phones, with no user data.

## Purpose

To find out, on real phones, how Google's free **limited distribution** account (Android Developer Console, up to 20 authorised devices, outside Play) behaves across a family device's life:

- invite and install;
- updates;
- what the relative sees about the developer;
- removing a device;
- replacing a phone, and whether that frees a slot.

## Hypothesis

1. A relative can authorise a phone from a QR code or link and install the app without enabling developer options or the "advanced flow".
2. A newer version signed with the same key installs as an update on an authorised phone:
   - (a) when the user taps an APK or link;
   - (b) silently, through the app's own `PackageInstaller` session with `USER_ACTION_NOT_REQUIRED` once "install unknown apps" is granted to it. This is B3 note claim C12, inferred from the API reference and never tested on a device.
3. Removing a device in the Console frees one of the 20 slots, and a replacement phone can be authorised the same way.

Any step that behaves differently proves the matching part wrong.

## Decision it informs

OD-10 (channel), ADR-0019, and whether the ADR-0002 amendment for a non-Play channel is workable.

| If the result is… | Then… |
|---|---|
| **Pass**: invite, install, update (at least 2a), remove and replace all work on 2 phones, and removal frees a slot | Limited distribution is a viable **pre-decided fallback** for OD-10 (and a candidate primary channel if B3-S3 fails). |
| **Fail**: updates need developer options or ADB, or slots are not freed on removal | The fallback becomes a **registered off-Play APK** (full-distribution ADC account, $25, government ID) with self-update, or Play only. |
| **No result** (no ADC account, or authorisation never completes) | OD-10's fallback stays "on paper"; record the risk. |

## Budget IDs cited

- **BUD-SUPPORT**: record owner minutes per device operation (authorise, update, replace). The same operations recur whenever a relative changes phone.
- **BUD-ENROLL** does not apply directly (it covers computers from the kit). Note the relative-facing step count for E5.

## Equipment

| Item | Exact model or version | Why | Have it? |
|---|---|---|---|
| Phone 1: Android 15 or 16, Google-certified, with Play Protect on | L12a–c | Main test phone | L12 |
| Phone 2: a different maker or Android version, certified | L12a–e | Second device, and later the "replacement" | L12 |
| ADC limited-distribution account with a throwaway package registered | `H5-L05` kit, Part B | Required | Owner |
| Throwaway app, 3 versions (v1, v2, v3), signed with the owner's key for the throwaway package | Built in Android Studio; targetSdk 36; v2 and v3 hold `REQUEST_INSTALL_PACKAGES` and can install a downloaded APK through `PackageInstaller` with `setRequireUserAction(USER_ACTION_NOT_REQUIRED)` | Tests install, manual update and self-update | Build step |
| An HTTPS location for the APK files | Any owner-controlled host | Update downloads | Owner |

## Before you start

- [ ] Factory-reset both phones, or use a fresh user profile, and note Android version, security patch and Play Protect status.
- [ ] Confirm the ADC shows the throwaway package as registered, and note the device count (should be 0 of 20).
- [ ] Do not turn on developer options on either phone. If a step requires them, that is a result.

## Procedure

1. In the ADC, start authorising Phone 1 (QR code or link, whichever the Console offers). Record each Console screen.
   **You should see:** a QR code or link.
2. On Phone 1, scan or open it. Record every screen the phone shows, especially what it says about the developer (name, email, "unverified" warnings) and any consent wording. Photograph the screens; they contain no personal data.
   **You should see:** a consent screen, then the app installs, or you are told how to install it.
3. Record the device count in the ADC.
4. Install **v2** on Phone 1 by tapping the APK or link (update path 2a). Record every prompt.
5. From inside v2, have the app download **v3** and install it through `PackageInstaller` (update path 2b).
   Record:
   - whether Android asked the user to allow "install unknown apps" for the app;
   - whether it asked for confirmation on this update;
   - whether the install finished with the screen off (repeat once with the screen locked).
6. Repeat steps 1–3 for Phone 2.
7. In the ADC, **remove** Phone 1. Record whether:
   - the app still runs on Phone 1;
   - it can still be updated there;
   - the device count went down.
8. Treat Phone 1 as a "replacement phone": factory-reset it, authorise it again as a new device, and record the device count.
9. Look for any per-device naming or labelling in the ADC (useful for "Grandma's new phone"), and any cap on authorisations or removals over time.

**Stop and record "No result" if:** authorisation needs developer options, ADB or the advanced flow (that is a Fail for hypothesis 1), or the Console never completes authorisation within the time you are willing to wait.

## Cleaning up

1. Remove both devices in the ADC and uninstall the app.
2. Keep the throwaway package registered, since nothing depends on releasing it.

## Data handling

Only the throwaway app is involved. Screenshots may show the owner's developer name, which is fine because it is the owner's own data. Do not photograph notifications from other apps.

## Results

Copy this section into `docs/research/kits/B3-S4/results.md`.

- **Run by / date:**
- **Phones (model, Android version, patch level):**

| Step | Expected | What happened | Measurement (with unit) | Screenshot or log |
|---|---|---|---|---|
| 1–2 Authorise and install Phone 1 | Installs without developer options | | screens (count); minutes; developer identity shown (verbatim) | |
| 3 Device count | 1 / 20 | | count | |
| 4 Manual update (2a) | Installs as update | | prompts (count, verbatim) | |
| 5 Self-update (2b) | No prompt after one-time grant | | prompts; screen-off result | |
| 6 Phone 2 | As Phone 1 | | minutes | |
| 7 Remove Phone 1 | Count drops; app behaviour recorded | | count; app runs? updates? | |
| 8 Replacement | New slot used, old freed | | count | |
| 9 Labels / limits | Recorded | | | |

| Pass criterion | Budget ID | Measured value | Pass / Fail / No result |
|---|---|---|---|
| Invite, install, update (at least 2a), remove and replace work on 2 phones; removal frees a slot | — | | |
| Owner minutes per device operation | BUD-SUPPORT | | (recorded, no threshold) |

- **Overall:** Pass | Fail | No result
- **Surprises and points of confusion:**
- **Follow-ups for the workstream:**
