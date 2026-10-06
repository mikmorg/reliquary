# Kit H5-L05: register the Google Play developer account (and, optionally, the limited-distribution account)

- **Spike / item:** H5 long-lead items L05 (Play developer account) and L06 (Android Developer Console "limited distribution" account). The B3 spike runner prepared this kit because B3-S3 and B3-S4 depend on it. See `docs/research/h5-long-lead-items.md` §3.1.
- **Exec tag:** EXT (identity-verification wait), owner hands-on
- **Prepared by / date:** B3 spike runner (Wave 1, batch W1-c), 2026-09-29
- **Who runs it:** Owner
- **Time needed:** hands-on time unknown, so record it. Google says ADC full-distribution verification "typically takes about 10 minutes if you have all of the required information ready". That page does not cover Play Console sign-up. The Play verification wait is **not documented anywhere the research container can reach**, so record the actual wait.
- **Data-handling class:** `SEC → results`.
  - The owner's ID documents, account passwords and 2-Step Verification factors never enter the repo, notes or agent sessions.
  - Results record only dates, durations, which fields the forms asked for, and what the Console says will be public.

## Purpose

To get the Google Play developer account running early, because identity verification has an unknown wait. It is needed for the B3-S3 review dry run, E5-S4 and the install-referrer test. The kit also records the facts that are blocked from the research container:

- what the Play forms require;
- what they make public;
- whether a new personal account has testing requirements before production.

## Hypothesis

A **personal** Play developer account can be registered and verified with the owner's own ID. It needs no D-U-N-S number, no organisation website and no business documents. It is ready (able to create an app and a closed track) within the owner's Wave 1 window.

## Decision it informs

OD-10 (second half: personal vs organisation account), the H5 timeline, and B3-S3 start date.

| If the result is… | Then… |
|---|---|
| **Pass**: personal account verified and able to create an app | B3-S3 can start. OD-10 records "personal", and the facts about public identity go into ADR-0019. |
| **Fail**: verification refused, or it requires things a family cannot provide | Record the verbatim reasons. OD-10 considers limited distribution (Part B) or an organisation account (D-U-N-S, which "can take up to 28 days" per the developer-verification FAQ). |
| **No result** (still waiting at Wave 1 exit) | B3-S3 moves to Wave 2. The channel decision is made on paper with the risk recorded. |

## Budget IDs cited

- **BUD-SUPPORT**: record hands-on minutes. No threshold is set by this kit.

## Equipment

| Item | Exact model or version | Why | Have it? |
|---|---|---|---|
| A Google Account for publishing, with 2-Step Verification on | Preferably a dedicated account the owner controls (not a relative's). Plan its recovery with D2. | The developer account is tied to it | Owner |
| $25 one-time fee and a payment card | | Play registration fee (T2) | Owner |
| Government photo ID and proof of address | As the form asks | Individual identity verification. This is what ADC full distribution asks for; Play's own list is **unverified**. | Owner |
| A phone number and email for one-time codes | Private, owner's own | Contact verification | Owner |
| An Android phone with Google Play | A lab phone (L12) | In case the Console asks new personal accounts to verify a real device (**unverified**; a gap listed in H5 §8) | L12 |

## Before you start

- [ ] Settle OD-10's account type at the intake. The proposed default is **personal**.
- [ ] Decide the **public developer name**, and check it is one you are happy to show to relatives and to anyone who sees the listing.
- [ ] Decide which Google Account will own the developer account, and record its recovery plan (D2 key inventory).
- [ ] Note the start date and time.

## Procedure

### Part A: Google Play developer account (L05)

1. Sign in to Play Console (https://play.google.com/console) with the chosen Google Account and start registration.
   **You should see:** a choice of account type. Record the exact options and any help text about each. Choose **personal** (or what OD-10 decided).
2. Fill in the developer profile.
   - For every field, record its name and whether the Console says it will be **shown publicly** (name, address, email, phone, website). Copy these statements verbatim; this is the answer to "which developer identity is exposed" (B3 question 4).
   - Record any question about the account's purpose, experience or number of apps.
3. Pay the $25 fee. Record the date and time.
4. Complete identity verification (ID, address, phone, email).
   **You should see:** a status such as "verifying". Record the time submitted and each status change until "verified".
5. If the Console asks you to verify an Android device or to install the Play Console app, do it on the lab phone and record what it asked.
6. Once verified, open the Console's **testing requirements** information for new personal accounts. Copy verbatim how many testers and how many days are needed before **production**, and whether **closed testing** has any requirement of its own. T2 says 12 testers for 14 days for production (from Play Help 14151465). A 2026 community post claims 20; this step settles it.
7. Open **Settings → Developer account** and record what it shows about Android developer verification. Google's guide says "your existing verified identity … meets this requirement" (https://developer.android.com/developer-verification/guides/google-play-console, last updated 2026-08-18).
8. **Do not create an app with the real Reliquary package name.** Creating an app registers its package name to this account permanently (H5 F3). B3-S3 uses a throwaway name.

### Part B: Android Developer Console limited-distribution account (L06), only if B3-S4 will run

Primary source for these steps: https://developer.android.com/developer-verification/guides/limited-distribution (last updated 2026-08-20). It lists the requirements:
- a Google Account with 2-Step Verification;
- a linked Google payments profile ("so you can provide and manage your legal name and address");
- a contact email that "won't be shown publicly".

It says "you don't need to provide a government ID".

9. Decide whether to use the **same** Google Account as Part A or a different one. Record the choice and the reason.
   Google says limited accounts can be migrated to full accounts, "but not the other way around" (developer-verification FAQ). Whether a package name registered here can later be published under a separate Play Console account is **undocumented**, so do not register the real package name here either.
10. Open the Android Developer Console from the limited-distribution guide and create a **limited distribution** account. Record every field, what it says is public, and whether the Console asks about intended use (the guide's "Hobbyist: share with family and friends" category).
11. Record the time from sign-up to "account ready". The guide warns that "registering package names and authorizing devices can take some time".
12. Register a **throwaway** package name for B3-S4 and record the steps: the SHA-256 signing-certificate fingerprint, and the proof APK with the Console's challenge snippet (per https://developer.android.com/developer-verification/guides/android-developer-console, last updated 2026-09-04).

**Stop and record "No result" if** verification is refused without a reason, or it asks for something you cannot or do not want to provide. Write down what it asked.

## Cleaning up

- Nothing to undo. The accounts are long-lived.
- Store no copies of ID scans in the repo or in any agent-visible place.

## Data handling

- Class `SEC` for account credentials and 2-Step Verification factors: kept per D2, never pasted anywhere.
- The results hold only public-facing facts, form field names, dates and durations.

## Results

Copy this section into `docs/research/kits/H5-L05/results.md`, and add the durations to the H5 table (owner action 3 in `h5-long-lead-items.md` §9).

- **Run by / date:**
- **Account type chosen (Play):** personal | organisation
- **Same Google Account for ADC (Part B)?** yes | no | not done

| Step | Expected | What happened | Measurement (with unit) | Screenshot or log |
|---|---|---|---|---|
| 1 Account-type choice | Personal offered | | options (verbatim) | |
| 2 Public fields | Clear which fields are public | | fields shown publicly (list) | |
| 3 Fee | $25 | | USD paid | |
| 4 Identity verification | Verified | | hours from submit to verified | |
| 5 Device check | Asked or not | | yes / no | |
| 6 Testing requirements | Stated in Console | | testers / days (production); closed-track requirement (verbatim) | |
| 7 Developer verification status | Met by Play identity | | status text (verbatim) | |
| 10 ADC limited account | Created | | fields and public statements | |
| 11 ADC ready | Ready | | hours | |
| 12 Throwaway package registered | Registered | | hours; steps (count) | |

| Pass criterion | Budget ID | Measured value | Pass / Fail / No result |
|---|---|---|---|
| Personal Play account verified and able to create an app | — | | |
| Owner hands-on minutes (Parts A and B) | BUD-SUPPORT | | (recorded, no threshold) |

- **Overall:** Pass | Fail | No result
- **Surprises and points of confusion:**
- **Follow-ups for the workstream:**
