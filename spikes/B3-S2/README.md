# B3-S2: account-deletion desk check

- **Spike:** B3-S2 (workstream B3, `docs/research/PLAN.md` §"B3."), exec tag `[CT]`
- **Run by / date:** B3 spike runner (Wave 1, batch W1-c), 2026-09-29
- **Data-handling class:** `PUB → results`
- **Budget IDs:** none in the PLAN pass criterion. BUD-SUPPORT (owner time, ≤ 2 h per month) matters to how the flows are designed, but nothing here measures it.
- **Pass criterion (PLAN):** "A documented compliant flow; otherwise a design change goes to the queue (OD-11)."
- **Result:** **Inconclusive, so the fail branch applies.** The Play account-deletion requirement could not be read from any primary source, so no flow can be shown to comply. OD-11 stays in the owner queue as the design-change request (the analyst has drafted the options in `docs/research/b3-android-distribution-play-compliance.md`). Two first-party precedent flows were read. One of them is new: **Nextcloud's request-to-provider flow**.

## 1. Primary policy text: attempts (2026-09-29)

| Source | Route | Outcome |
|---|---|---|
| Play Console Help 13327111 "Understanding Google Play's app account deletion requirements" (`support.google.com/googleplay/android-developer/answer/13327111`) | WebFetch | `EGRESS_BLOCKED` (support.google.com) |
| Same | curl through the proxy | connection refused (HTTP 000) |
| Play Developer Policy Center, User Data (`play.google.com/about/privacy-security-deception/user-data/`) | WebFetch | `EGRESS_BLOCKED` (play.google.com) |
| developer.android.com pages that might restate the rule: `guide/topics/data/collect-share` (Data safety guidance), `privacy-and-security/about`, `privacy-and-security/risks`, `identity/sign-in/credential-manager` | curl, then text search for "account deletion" / "delete your account" | HTTP 200; **no mention** of account deletion |
| `developer.android.com/google/play/data-safety`, `.../guide/topics/data/account-deletion` (guessed URLs) | curl | 404 |

No secondary restatement was used in place of the policy text. The questions below therefore have **no primary answer**:

- Does redeeming an invite count as "account creation in the app"?
- Is a deletion request that goes to an administrator acceptable?
- Which retention reasons may keep data after an account is deleted?
- Is a web deletion link required?

## 2. Precedent flows (first-party source, read 2026-09-29)

| App | What the app does | Evidence | Relevance to Reliquary |
|---|---|---|---|
| **Nextcloud Android** (Play build `gplay`, `com.nextcloud.client`) | The "Remove account" dialog offers two choices: **"Remove account from device and delete all local files"**, and, only if the server advertises the `drop-account` capability, **"Request account deletion"** ("Request permanent deletion of account by service provider"). The request option just opens `<server>/settings/user/drop_account` in the browser. The server-side app handles the request. The Android app deletes nothing on the server itself. | `app/src/main/java/com/owncloud/android/ui/dialog/AccountRemovalDialog.kt` (`hasDropAccount()`, `DROP_ACCOUNT_URI = "/settings/user/drop_account"`) and `app/src/main/res/values/strings.xml` lines 298–302, `nextcloud/android` @ `3c70807` (2026-09-29) | This is the closest match to Reliquary: self-hosted, accounts created by an administrator, and the deletion request goes **to the operator**. It fits OD-11 option A's "leave request goes to the admin". The Nextcloud app also offers "Sign up with provider" (`strings.xml` line 1074), so it does create accounts in the app. Whether Play has accepted this flow is **not verified**. The app appears on Play per its README, but its listing and review history were not seen (blocked). |
| **Ente Photos** | In-app deletion: a reason step, then a challenge (`GET /users/delete-challenge`) the client decrypts, then `DELETE /users/delete`. The server marks the account deleted and **schedules** cleanup of stored data. | Analyst claim C28, `ente-io/ente` @ `7a5993c` | Shows that deleting the identity can be separated from removing data. That is the pattern for OD-11 option B. |
| **Immich** | No sign-up form in the mobile app; the administrator creates accounts in the web UI. | Analyst claim C27. Not re-checked by this runner: the shared `i18n/en.json` has a `sign_up` string, but whether the mobile client uses it was not checked. | Precedent for OD-11 option A (accounts created by the admin) |

## 3. Candidate flow to put through the B3-S3 dry run

This is **not** documented as compliant, because the policy text is missing. It combines OD-11 options A and B so that a single review tests both. It never deletes backups, as the settled keep-forever rule requires.

1. **No account is created in the Android app.** The admin creates the person (name and email) when generating the invite. On Android, redeeming only **enrolls a device** into that existing person. This is a design change against ADR-0002 §2, which says "Redemption creates the account"; it is queued as OD-11 option A.
2. **In the app, Settings → "Leave family backup / delete my account":**
   - **(a) "Remove this device":** revokes the device credential and deletes local state. Nothing already backed up is touched. This matches Nextcloud's local-removal option.
   - **(b) "Ask to delete my account":** sends a signed request to the admin queue, in the same way that Nextcloud's `drop_account` request goes to the operator.
     - The admin must act within a stated number of days (value to be set by the owner).
     - Acting on it deletes the person's cloud identity: name, email, device credentials and mailing-list entry (OD-11 option B).
     - Backed-up files are **kept under a retention statement** unless the admin prunes them by hand.
     - The confirmation screen says so in plain words.
3. **Web deletion link:** a static page on the owner's domain with the same "ask to delete" form, for people who no longer have the app. It is listed in the Play Console if the form asks for one. The requirement is unverified, and it depends on L03 (domain).
4. The **privacy policy** (D6) states the retention reason: a family archive that is kept until the family administrator removes it.

The B3-S3 kit (`docs/research/kits/B3-S3/`) builds this flow into the dry-run app and records whether review accepts it.

## 4. What would change the result

- **Read access to support.google.com and play.google.com (H1 allowlist request):**
  - If the requirement allows an operator-handled request plus a retention statement, the flow above becomes "documented compliant" and B3-S2 passes.
  - If it requires deleting the data within the app, OD-11 option D (leave Play) is the only option that keeps the settled keep-forever rule.
- **B3-S3 review outcome:** approval gives an empirical pass; the rejection text gives the primary wording.
