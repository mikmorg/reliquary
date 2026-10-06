# ADR-0019: Android distribution channel and Play compliance. Wave 1 part: Play closed track gated on a review dry run, an owner-supplied signing key with two build flavours, and an Android app that never creates accounts

- **Status:** Proposed (partial draft: the Wave 1 decisions only. The rest is to be decided in Wave 2; see "Not yet decided")
- **Date:** 2026-10-06
- **Owner workstream:** B3
- **Decider:** the owner
- **Gate:** C (one-way door #12 closes at the first Play upload under the real package name)
- **Supersedes / Amends:** None directly. **Decision 4 (account creation) needs the owner to approve a change to CLAUDE.md "Onboarding and distribution" and ADR-0002 §1/§2 (OD-11).** The fallback channel in decision 1 needs approval of a change to CLAUDE.md ("Android ships via Google Play (family closed track)") and ADR-0002 §4 (OD-10) if it is ever used. This ADR does not amend either. It also asks that the superseding draft correct ADR-0002's "Google Play 'limited distribution' account" wording.
- **Evidence:** `docs/research/b3-android-distribution-play-compliance.md` (Wave 1 final). Spikes `spikes/B3-S1/` and `spikes/B3-S2/`. Kits `docs/research/kits/B3-S3/`, `docs/research/kits/B3-S4/` and `docs/research/kits/H5-L05/`, with the kit amendments listed in the note.
- **Traceability:** R-02, R-26, Q2-2 (see `docs/research/traceability.md`)
- **Owner decisions:** OD-10, OD-11, OD-19 (input; E2 owns it), OD-17 (one new accepted-risk item)
- **One-way door:** Yes, door #12 (Android package name, signing key, distribution channel) in `docs/research/one-way-doors.md`

## Context and problem statement

The settled text says Android ships through Google Play on a family closed testing track (CLAUDE.md; ADR-0002 §4). Relatives are non-technical and never touch configuration. Backups are kept forever, and devices can only append. Self-updates must be verified against the project's own offline key (ADR-0002 §5).

Wave 1 desk research (B3) found five things:
1. **Limited distribution is not Play.** The free "limited distribution" account that ADR-0002 lists as an alternative belongs to the Android Developer Console and installs apps **outside Play**, on up to 20 authorised devices (K1, verified).
2. **Leaving Play costs a manual step.** A Play-distributed app may not update itself by any other means (search-index text, secondary; Nextcloud precedent). Changing channel later costs one manual install per phone, even with the same signing key (K4, verified as restated).
3. **The account-deletion rule threatens keep-forever.** Play's rule, as seen in search-index snippets, is triggered when an app lets users create an account. Deleting the account must also delete its data, with only security, fraud and regulatory exceptions (secondary). If Reliquary's Android app created accounts, the rule would collide with keep-forever.
4. **The Play policy texts cannot be read here** (support.google.com and play.google.com are blocked). Every Play-review question stays open until the B3-S3 dry run.
5. **The Play channel is outside the offline update key.** Play installs whatever Google signs, so ADR-0002 §5's update-key guarantee does not cover Android on Play.

This ADR fixes what can be fixed now (channel policy, key and flavour policy, where accounts are created) and the Play-side constraints that it supplies to ADR-0018 (B2) and ADR-0004 (E2). Media permissions, foreground services and document scope are **owned by those ADRs**; here they appear only as Play-compliance requirements.

## Decision drivers

- **Settled:** Android is a v1 platform. Phones are first-class (R-02). Android ships via the Play family closed track (CLAUDE.md, ADR-0002 §4).
- **Settled:** keep forever; deleting on a device never removes backups (R-26). Devices can only append (R-18). Treat the cloud API as under attack.
- **Settled:** self-updates are verified against the project's offline key (ADR-0002 §5). Users never touch configuration (R-07).
- **BUD-SUPPORT** (owner time ≤ 2 h/month): per-device owner actions, review chores and yearly target-API bumps all count against it.
- **BUD-TTS** (time to safe): background reliability on Android (battery exemption trade-off, owned by B2).
- **Time-sensitive platform rules:** target API 36 for Play submissions since 31 Aug 2026 (K8). Developer verification is enforced from 30 Sep 2026 in four countries and globally in 2027 (K7).

## Considered options

Channel:
1. **A.** Play closed testing track, personal account.
2. **C.** Off-Play `direct` flavour registered under the same Play Console account, same key, self-updating.
3. **B.** ADC limited distribution (free, ≤ 20 devices at any one time, owner authorises each device).
4. Unregistered APK (advanced flow).
5. Managed Google Play private app (not researched).

Account creation:
- **A′.** Redemption only on desktop or web.
- **A.** The admin creates accounts.
- **B.** In-app identity deletion with backups kept.
- **C.** In-app deletion including backups.
- **D.** Leave Play.

## Decision

The decisions below are **proposed**. Decisions 1, 2 and 4 wait on the owner (OD-10, OD-11). Decision 3 is a policy that can be accepted now. Decision 5 consists of requirements supplied to other ADRs.

### 1. Channel: Play closed testing track, gated on B3-S3 (OD-10 option A)

- The primary channel is the Play closed testing track, as settled, **conditional on the B3-S3 review dry run** being approved for the design below.
- If B3-S3 refuses only all-files access, the pre-decided fallback is **media only** (PLAN B3-S3). Nothing else changes.
- If B3-S3 refuses the Photo & Video declaration or the account design, the **proposed fallback is option C**: the `direct` flavour, registered under the same Play Console account and signed with the same key. Option C is **not pre-decided**. It needs:
  - the owner's approval of the settled-text change (CLAUDE.md and ADR-0002 §4);
  - a passing B3-S4 (silent self-update is contested, K5).
- Option B (limited distribution) applies only if the owner never registers on Play. It adds per-device owner authorisation, which conflicts with ADR-0002 §3 and BUD-SUPPORT.

### 2. Account type: personal (OD-10, second half)

A personal developer account in the owner's name, subject to intake questions A5 and E6. An organisation account needs a D-U-N-S number (up to 28 days), a verified website and official documents (K6, ADC requirements; Play's own form is to be recorded by H5-L05). It is reconsidered only if the owner already runs a suitable business entity.

### 3. Signing key, package name and build flavours (one-way door #12): decided as policy now

| Item | Decision | When |
|---|---|---|
| App signing key | **Owner-supplied** to Play App Signing ("Export and upload"). **Never accept a Google-generated key.** The release runbook makes this an explicit step, because the default is that Google generates it. | Key generated at the D2/D5 ceremony (ADR-0008, ADR-0015) |
| Upload key | Separate from the app signing key; held offline or in hardware | D5 |
| Package name | Reverse-DNS under an owner-controlled domain | Fixed once H5 L03 (domain) settles. Registered (Play app creation) **before any build carrying it leaves the owner's machines**. B3-S3 uses a throwaway name |
| Flavours | `play`: **no** `REQUEST_INSTALL_PACKAGES`, **no** `UPDATE_PACKAGES_WITHOUT_USER_ACTION`, no updater code. `direct`: may carry them. Same package name and key | From the first build. G1 adds a merged-manifest CI guard on `play` |
| Off-Play updater (`direct` only) | Before committing a `PackageInstaller` session, verify a detached minisign/Ed25519 signature from the project's **offline update key** (as on desktop, D5). APK certificate continuity alone is not enough, because Google co-holds the APK key. Always handle `STATUS_PENDING_USER_ACTION` with a prompted path | Only if option C or B is ever used |

### 4. The Android app never creates accounts (OD-11 option A′; A as alternative)

- **A′ (recommended):**
  - Invite codes are redeemed only in the desktop app, or on a small redemption web page for a person with no computer. Redemption creates the account there, as the CLAUDE.md wording says.
  - The Android app accepts **only device-enrollment tokens** from the "your other devices" wizard (ADR-0002 §3).
  - The invite card's QR must not lead to redemption in the Android app. That changes ADR-0002 §1, so the owner must approve it.
- **A (alternative):** the admin creates the account (name and email) when generating the invite. Redemption only enrolls devices. This changes the CLAUDE.md onboarding text and ADR-0002 §2, so the owner must approve it.
- **Leave/delete request (a courtesy, not compliance cover):**
  - The app offers "Remove this device" (revokes this device's credential locally and server-side; touches no backup) and "Ask to delete my account".
  - The second option is a **request** that the admin actions after out-of-band confirmation to the verified email, with a delay window.
  - It is **never** triggerable by a single device credential.
  - Any public web form is a rate-limited request, never an action.
- **Never delete backups** (option C is rejected).
- **If the primary Play text shows the rule still applies under A′ or A,** this ADR returns to the owner with option D (leave Play, OD-10 option C) as the only choice compatible with keep-forever.

Evidence status: the trigger and data-deletion wording (C36) is **secondary only** (search index). This decision is therefore **provisional until B3-S3 Part A or the allowlist yields the primary text**. It is also supported by the verified precedent that a self-hosted photo app ships with no mobile sign-up (K13, with caveats).

### 5. Play-build compliance requirements supplied to ADR-0018 (B2) and ADR-0004 (E2)

These are **requirements**, not design decisions. The owning ADRs decide.

| Requirement | Basis |
|---|---|
| Full `READ_MEDIA_IMAGES`/`READ_MEDIA_VIDEO` plus `ACCESS_MEDIA_LOCATION` (with `setRequireOriginal`), and a Photo & Video declaration whose core use is automatic backup of the whole library. The photo picker cannot serve this use | C16, C17, C30; B3-S1 provisional pass; approval unverified until B3-S3 |
| Foreground service type `dataSync` only, never `specialUse`; FGS types declared in Play Console; stay within 6 h per 24 h; no FGS start from `BOOT_COMPLETED` | K9 |
| UIDT only for user-initiated "back up now", not as the sole mechanism | K9 |
| `MANAGE_EXTERNAL_STORAGE` only in a separate documents flavour that can be dropped, and only if OD-19 wants documents. SAF cannot reach `Download/` | K10, K11 |
| `REQUEST_IGNORE_BATTERY_OPTIMIZATIONS`: an open trade-off for B2 (prohibited unless the core function is adversely affected; the use-case table is not exhaustive). To be tested as B3-S3 Variant C | K14 |
| Target API 36 now; plan an upgrade every year | K8 |
| Data safety: declare Photos and videos, Files and docs, and Location as **collected**, because the admin can decrypt them. Not end-to-end encrypted in Play's sense | C37 (secondary); D6 confirms |

### 6. Accepted-risk item for OD-17: the Play update channel

On Play, Google (which holds the app signing key) and anyone who controls the owner's Google account (uploads, upload-key reset) can ship an update to every family phone that the offline update key does not check. A malicious build could read photos on the phone before encryption. Backups already stored are not exposed.

Proposed mitigations (D1, D5):
- Advanced Protection or hardware security keys on the owner's Google account.
- The fewest possible Play Console users.
- Managed publishing.
- Alerts on new releases and upload-key reset requests.
- The upload key held offline.

### Not yet decided (to be decided in Wave 2)

- The **policy dossier**: declaration texts (draft in `docs/research/kits/B3-S3/declarations-draft.md`), the final Data safety form, the FGS demo-video script, and the privacy policy with D6. Written after B3-S3 or the allowlist.
- **Encryption export** (EAR mass-market or publicly-available; effect of a public vs private repo, OD-15) and the later App Store and French declarations.
- The **iOS compliance checklist** (Guideline 5.1.1, `PrivacyInfo.xcprivacy`), handed to B4 and E2 for OD-01.
- Whether to use the **internal testing track** alongside or instead of the closed track (B3-S3 amendment 5).
- The **off-Play update client**: a hand-written updater vs a self-hosted F-Droid-format repository or Obtainium (only if option C is used).
- Whether one app signing key or separate keys per channel (D5).

### Consequences

- **Good:**
  - Relatives keep the familiar Play install and automatic updates.
  - No "install unknown apps" grant on the primary channel.
  - The channel stays reversible at the cost of one manual install per phone.
  - The Android app stays outside the trigger of the account-deletion rule, as that rule is currently understood.
  - Keep-forever is preserved.
- **Bad / accepted trade-offs:**
  - All Play policies apply, and their texts are unread.
  - A yearly target-API bump.
  - Review waits.
  - The update channel is outside the offline key (OD-17).
  - The owner's Google account becomes a high-value target.
  - A′ needs a redemption web page for phone-only people and changes where the invite card's QR leads.
  - Two build flavours to maintain.
- **Follow-up work:**
  - H1: allowlist, B3-S4 added to PLAN, update door #12.
  - D5/D2: key ceremony, upload key, Play Console hardening, offline-key check in the `direct` updater.
  - D1: threats.
  - D3/C1: device-only enrollment API for Android; admin-actioned deletion requests.
  - E5: card QR and redemption location.
  - E1: phone-only census.
  - B2: requirements in decision 5.
  - G1: manifest guard.
  - D6: Data safety and privacy policy.

### Confirmation

- **B3-S3** (EXT, BUD-SUPPORT), with kit amendments 1–5. Pass: the closed-track release is approved with the decision-5 set and the A′ account answers. Policy texts are captured verbatim.
- **B3-S4** (OL, BUD-SUPPORT), only if option C or B is pursued, with kit amendments 6–9. Pass: silent update with the four conditions met; the prompted fallback works; the channel-switch cost is measured.
- **H5-L05** (EXT): the personal account is verified; the public identity fields are recorded.
- **CI (G1):** the `play` merged manifest contains no install permissions; target API is checked.
- **Review trigger:** reopen this ADR if Google publishes changes to the account-deletion, self-update or Photo & Video policies, or to the developer-verification rules.

## Pros and cons of the options

### Channel A: Play closed track

- Good, because Play installs and updates the app with no configuration on the phone (T2; ADR-0002).
- Good, because it is the settled choice, so no settled-text change is needed (CLAUDE.md).
- Bad, because every Play policy applies and the texts are unread (K12, secondary only).
- Bad, because updates are outside the offline key (F8).
- Bad, because of the yearly target-API bump (K8).

### Channel C: off-Play `direct` flavour, same Play Console account

- Good, because it has no device cap and the Play Console account can register off-Play apps (K4).
- Good, because updates can be checked against the offline key (F8).
- Bad, because silent self-update is untested and documented as possible, not guaranteed (K5 contested; C33).
- Bad, because each phone needs an "install unknown apps" grant (against R-07), and leaving Play costs one manual install per phone (C34, C35).
- Bad, because it changes CLAUDE.md and ADR-0002 §4.

### Channel B: ADC limited distribution

- Good, because it is free with no ID check (K1, K6).
- Bad, because the cap is 20 at any one time and the owner authorises each device (C38, secondary). That conflicts with ADR-0002 §3 and weighs on BUD-SUPPORT.
- Bad, because the account type only moves limited → full (K3) and a move to Play is undocumented (C42).

### Account A′ / A vs B

- A′ and A are good, because the app never creates an account, so by the indexed text the deletion rule is not triggered (C36, secondary). There is precedent in Immich (K13).
- B is bad, because the indexed text requires deleting the associated data, and "keep-forever archive" is not a listed retention reason (C36, secondary).
- B is also bad, because self-service identity deletion is an availability attack: one device stops all of a person's backups.

## Evidence

| Claim | Source (primary) | Verdict |
|---|---|---|
| K1 Limited distribution is ADC, outside Play, ≤ 20 authorised devices | developer.android.com limited-distribution guide (2026-09-30), guides index (2026-08-18) | Verified |
| K3 Account type moves only from limited to full | Verification FAQ (answer 2026-06-08) | Verified |
| K4 Name usable on Play after off-Play use; Play Console registers off-Play apps; developer-supplied key accepted | google-play-console guide (2026-09-30); app-signing (2026-03-06) | Verified (2–1, restated: necessary, not sufficient) |
| K6 ADC identity requirements; D-U-N-S up to 28 days | full-distribution guide (2026-08-18); FAQ | Verified (ADC only) |
| K7 Enforcement dates and scope | overview; guides index; FAQ | Verified (2–1; scope conflict recorded, C39) |
| K8 Target API 36 for Play submissions | target-sdk (2026-10-01) | Verified |
| K9 UIDT, `dataSync` and FGS declaration rules | uidt, service-types, behavior-changes-15, fgs-types-required | Verified |
| K10 SAF limits; all-files likely uses | documents-files, manage-all-files (2026-10-01) | Verified |
| K11 Nextcloud all-files history on Play | nextcloud/android git history | Verified |
| K13 Admin-created accounts precedent | Immich source and docs; Ente server | Verified (with caveats, C41) |
| K14 Battery-exemption prohibition | doze-standby (2026-08-18) | Verified |
| K5 Silent self-update | PackageInstaller.SessionParams (2026-08-03) | **Contested**. Used only beside K4 and as a B3-S4 gate, never as the sole support |
| K2 Limited-distribution device lifecycle undocumented | limited-distribution guide, FAQ | **Contested**. Not used as support. Narrowed in the note |
| K12 Play policy texts unreadable | blocked-source log | **Secondary only**. Caps confidence |
| C36 Account-deletion trigger and data-deletion wording | Play Help 13327111 via search index | **Secondary only**, beside K13. Decision 4 is provisional |
| C35 Play apps may not self-update | Play Help 9888379 via search index; Nextcloud c8b0a653b6 (primary code) | **Secondary** policy text with a primary precedent. Used only as a constraint |

## Reversibility

- **Package name:** effectively permanent once family phones have it installed.
- **App signing key:** permanent per package once uploaded. Only Play's key upgrade on Android 13+ partly reopens it. That is why decision 3 must hold **before the first Play upload under the real name**.
- **Channel:** reversible at the cost of one manual install per phone, provided decision 3 holds.
- **Where accounts are created (decision 4):** reversible before the first invite cards are printed (E5's gate). After that, the cards' QR target is fixed in print.
- **Account type:** personal → organisation means a new account and an app transfer (not researched). The ADC direction is one way: limited → full only.

## Alternatives considered

- **Unregistered APK (advanced flow):** rejected. Developer mode, a one-day wait and biometric confirmation are unfit for relatives (K7, C11).
- **Managed Google Play private app:** the only target-API exemption Google states, but it needs an organisation or EMM setup, which conflicts with the personal account. Not researched.
- **UIDT-only background design:** rejected as the sole mechanism, because it cannot run periodic automatic backup (K9).
- **Accepting a Google-generated app signing key:** rejected, because it forces an uninstall and reinstall on every phone to change channel (K4).
- **In-app deletion including backups (OD-11 C):** rejected, because it breaks keep-forever.
- **Hybrid (Play for most phones; `direct` for one or two edge devices):** possible with the two-flavour design. Revisit after E1's census.

## Open questions

- Primary texts of the Play account-deletion, Photo & Video, FGS and demo-video, Data safety, Device and Network Abuse and stalkerware policies, and ADC Help 17131204: H1 allowlist or B3-S3 Part A.
- Does Play still treat the app as allowing account creation under A′ or A? (B3-S3)
- Does review run on closed and internal tracks, and how long does it take? (B3-S3)
- Silent self-update and the channel-switch prompt on real Android 15/16/17 devices (B3-S4).
- Number of phone-only relatives (E1), which decides between A′ and A.
- Install referrer through the opt-in (E5-S4).
- Encryption export and the iOS checklist (B3 Wave 2).
- Battery exemption, hibernation and `MANAGE_MEDIA` (B2, ADR-0018).
