# ADR-0002: Onboarding via USB stick and one-use printed invite; app distribution

- **Status:** Accepted
- **Date:** 2026-09-29

## Context

Users are non-technical family members (see `CLAUDE.md`). The owner wants to hand each person a physical kit: a USB stick with the app on it and a printed, one-use invite code, with which the person creates an account using only a name and an email. ADR-0001 already requires a USB-drive transport for seeding large libraries.

## Decision

### 1. The onboarding kit

- **USB stick** containing:
  - desktop builds for Windows, macOS and Linux (e.g. AppImage), plus a plain "Start here" guide;
  - space for the **return trip**: after enrollment, the client can write its initial encrypted upload bundles (ADR-0001 format) back onto the same stick, to be mailed or handed back to the owner for ingest at the homelab.
- **Printed invite card** with a human-typable code and a QR code encoding the same invite (the QR also links to the Android app on Google Play).

The stick and the card are deliberately separate: losing the stick alone does not give anyone an account.

### 2. Invite codes and accounts

- The admin generates an invite; the Worker stores only a hash of the code, its expiry, and state `unused → redeemed`.
- Codes are **one-use**, **expire** (e.g. 30 days), and have enough entropy (≥ 50 bits, e.g. 10–12 base32 characters grouped for readability, with a check character to catch typos) to rule out guessing when combined with per-IP rate limiting on redemption.
- Redemption creates the **account** (name and email) and enrolls the **first device**, which generates its own keypair (ADR-0001, restore delivery) and receives a per-device credential.
- **No password.** Devices hold no key that can read backups, and restores go through the admin, so an account is just an identity plus a list of devices. A lost device is revoked by the admin; a replacement is enrolled with a new invite or from another enrolled device.
- **Email verification on signup:** a confirmation link is sent; the account is active for backup immediately, but nudges begin only after verification.
- **Email is also used for backup nudges** (e.g. "your laptop hasn't backed up in 14 days") when the person isn't opening the app.
- Consequence: name, email and per-device activity timestamps are stored in plain text in the cloud control plane (needed to send mail). File contents and file metadata remain encrypted per ADR-0001.

### 3. Adding more devices: the "your other devices" wizard

The desktop app actively guides the person to protect their other devices; it is part of the assistant, not a hidden menu item.

- **During first-run onboarding,** right after the first device is enrolled, the wizard asks which other devices the person uses (Android phone or tablet, iPhone or iPad, another computer) and walks through each one. It can be skipped, but not silently.
- **Android:** the wizard shows a QR code that opens the Google Play listing (closed track) and carries a **short-lived, single-use enrollment token** (e.g. 10 minutes). After installing, the phone app either receives the token automatically (via the Play install referrer, if feasible) or scans the same QR on first launch. It then enrolls under the same account and starts with a phone-specific discovery of the camera roll.
- **Another computer:** the wizard offers two routes: (a) "Copy installer to a USB stick", which writes the desktop builds and a Start-here guide to any stick; or (b) a download link for use on that computer. The new computer enrolls with a short **pairing code** shown by the first device (typed rather than scanned, since computers may lack cameras), which is single-use and short-lived like the QR token.
- **iPhone/iPad:** recorded as "not yet supported". The assistant remembers it and notifies the person when iOS support arrives.
- **Ongoing nudges:** devices the person said they own but has not enrolled appear in the plain-language health view ("Your Android phone isn't protected yet — set it up") and in email nudges, until enrolled or dismissed.
- Adding devices never requires the admin. Any enrolled device can show the QR or pairing code, including the phone (e.g. to set up a second computer).

### 4. Platforms and distribution

| Platform | v1 distribution |
|---|---|
| Windows, macOS, Linux | USB stick; the app installs itself to the local disk (it must keep running after the stick is removed), registers background start, and **self-updates** |
| Android | **Google Play**, preferably a **closed testing track** restricted to the family's email list, which avoids a public listing |
| iOS | **Deferred.** Revisit together with the Apple Developer membership. The client stack chosen in ADR-0003 must not preclude iOS. |

### 5. No OS code signing for now; app-level update signing is mandatory

The owner chose not to pay for Apple or Windows code signing yet. Consequences and mitigations:

- **First launch from USB is likely less hostile than a download.** Windows SmartScreen relies on the Mark-of-the-Web, and macOS Gatekeeper's first-launch check on the quarantine attribute; both are normally set on *downloaded* files, not on files copied from a USB stick. **This must be verified on real hardware** (current Windows 11 and macOS releases) before relying on it. On Apple Silicon, binaries must still be at least ad-hoc signed to run, which is free.
- If warnings do appear, the "Start here" guide shows the exact steps with screenshots (Windows: *More info → Run anyway*; macOS: *System Settings → Privacy & Security → Open Anyway*).
- **Self-updates must be signed with the project's own key** (e.g. Ed25519 / minisign), and the app must verify the signature before installing. Without OS signing, this is the only thing preventing a compromised update channel from pushing malware to every family device. The update signing key is kept offline by the admin.
- Unsigned, self-updating binaries may trip antivirus heuristics; test with Windows Defender.

## Alternatives considered

- **Unlisted App Store and public Play listings from day one:** deferred for cost and review overhead; Android via a closed track gets most of the benefit.
- **Android APK sideloaded from the stick:** rejected for non-technical users (security warnings, no automatic updates) and increasingly restricted by Google's developer-verification requirements.
- **Invite embedded on the stick:** rejected; a lost stick would then be a usable account. The printed card acts as a separate physical factor.
- **Passwords or passkeys:** unnecessary under this trust model (devices cannot read data; admin-mediated restore) and a support burden.
- **Admin issues a new invite per device:** rejected in favour of the device wizard (QR or pairing code from an enrolled device); less work for the owner.

## Open questions

- Email sending provider reachable from Workers (e.g. Cloudflare's own email sending if available, or Resend or Postmark); must not be AWS.
- Google Play specifics: the one-time developer fee and any testing-track requirements for new personal accounts (Google has required a period of closed testing with a minimum number of testers before production for newer accounts). Confirm current rules; a family closed track may be the permanent channel.
- Whether the Play Install Referrer can carry the invite from the QR into the Android app, so nobody types the code on a phone.
- Invite and QR lifetimes, and how the admin generates and prints cards (CLI vs. small admin page).
