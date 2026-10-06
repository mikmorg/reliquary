# E1-S2a call script (remote quick count)

Revised 2026-10-06 after skeptic review (E1 note §2.4 and §2.6). Read it in your own words. You
are asking for **numbers on a screen**, not for opinions, and not about a future app. Do not
describe or promise a product.

**Time:** 10–15 minutes is a **planning estimate, not a measurement**. Time the first two calls
and write the real durations in `results.md`.

## Before the call: set it up so the relative can see and hear

The relative has to read Settings on the phone while talking to you. Doing that on the same phone
as the call is hard: they must use the speaker, leave the call screen and find their way back.
Pick the first option that works for this person:

1. **In person** (best). A family gathering in weeks 1–2, or a helper relative who lives with
   them or is visiting, reads the screens with them.
2. **Call on a second line.** Phone them on a landline or another phone or tablet, so the phone
   being read is free.
3. **Video call with screen sharing**, where you read the figures from their shared screen. Use
   only an end-to-end encrypted service the family already uses, and never record. Check with the
   H3 rules (owner action; H3 does not yet list acceptable video services).
4. **Same phone, on speaker.** Only if the person is comfortable with that.

If the person uses **Assistive Access** (a simplified iPhone set up by a supporter), Settings may
not be reachable. Ask the supporter to take the readings with them, or leave it to the visit
(S2b).

## A. Opening and consent (read aloud)

> "I'm trying to plan how much space the family's photos take up, so that I can keep them safe at
> home later. Could you help me read two or three numbers from your phone's settings? It takes
> about ten or fifteen minutes.
>
> **I will never ask you for a password or a code, and never ask you to buy or change anything.**
> If you see a button like *Buy*, *Upgrade* or *Get more storage*, don't tap it; just tell me.
>
> I only write down the numbers, for example '38 gigabytes', and whether a couple of settings are
> on or off. I don't look at your photos, and I don't write down any names of photos, albums or
> places. You appear in my notes as a code, not by name. Some of the planning uses AI tools, and
> they only ever see family-wide totals.
>
> You can say no, or stop at any time, and nothing changes. The raw numbers are deleted within 90
> days. Is that OK?"

Tick on the sheet: ☐ Yes ☐ No. If no: thank them and end the call.

(A child's phone: ask the parent or guardian first. Also ask the child in simple words, and respect
a no. See H3 §9.)

This phone consent text needs the owner's approval together with H3 §9 and OD-21 before the
first call.

## B. The readings (guide them; they read aloud)

Use the exact wording you found in Part 0 of the kit. If a screen looks different, ask them to
read out what they see. Do not guess.

**Units:** after every number, ask "Does it say MB or GB?" and repeat the number and unit back
("so that's 38 **gigabytes**?"). A slip between MB and GB changes the result by a factor of 1,000.

**If a screen says "Calculating…"**, wait. If it is still calculating after about two minutes,
move on and note "not read".

**If it is an iPhone or iPad:**

1. "Open **Settings**. Tap your name at the top, then **iCloud**."
   - "Is **Photos** switched on there?" → iCloud Photos on, off or unsure.
   - If on: "Tap **Photos**. Does it say *Optimize iPhone Storage* or *Download and Keep
     Originals*?"
   - "Does it say anything about **Shared Library**?" → yes, no or unsure.
2. "Go back. At the top there is a storage bar. Does it say the storage is **full**, or is there a
   message that photos are **not uploading** or **paused**?" → yes, no or unsure (flag
   `icloud_full`).
3. If iCloud Photos is on: "Tap **Manage Account Storage** (or **Storage**). What number is next
   to **Photos**?" → M1 (`cloud_gb`).
4. "Now go back to the first Settings screen. Tap **General**, then **iPhone Storage**. Wait for it
   to finish loading. What number is next to **Photos**?" → M2 (`device_gb`). Always record it,
   even when M1 exists.
5. "Open the **Photos** app, go to the bottom of the library. What does it say: how many photos and
   how many videos?" → item counts (a cross-check; never a name).
6. "Tap **General**, then **About**. What does it say for **iOS Version** and **Model Name**?"

**If it is an Android phone:**

1. "Open **Settings**, then **Storage** (it may be under *Battery and device care* or *Device
   care*). What numbers are next to **Images** and **Videos**?" → `device_gb`.
2. "Open **Google Photos**. Tap your picture in the top corner. Is backup on? What does it say about
   backup quality: **Original quality** or **Storage saver**?" Then: "Has it ever been set to
   *Storage saver* or *High quality*, as far as you know?" → yes, no or unsure (flag `saver`).
3. "Is there a storage number there, or a link to account storage? What does it say for
   **Photos**?" → `cloud_gb`. If only a shared total for Gmail, Drive and Photos appears, record
   the total in `note`, leave `cloud_gb` blank and add flag `shared_total`.
4. "At the bottom of the Google Photos library, or in your gallery app, how many photos and videos
   does it say?" → item counts, if shown.
5. "Open **Settings > About phone**. What are the **model** and the **Android version**?"

## C. Short questions

1. "Apart from this phone, do you take photos or videos with anything else: a tablet, an old
   phone, a camera?" → yes, no or unsure, and the device type only.
2. "Has a computer ever **added** old photos or scans into your iCloud Photos / Google Photos, for
   example from a camera card or a scanner?" → yes, no or unsure (Apple: flag `mixed`).
3. Android only: "Roughly when did you start backing up photos to Google: before 2021, or later?"
   → before / later / unsure (flag `pre2021` for before or unsure). "Is this phone, or was an
   earlier one, a Google **Pixel**?" If yes, which number, roughly → flag `pixel` for Pixel 1–5.
4. "Have you ever used a button that **makes room on the phone by keeping photos only in the
   cloud**, such as *Free up space* or *Optimize storage*? That's fine either way." → yes, no or
   unsure.
5. "Which device do you **mostly** take photos with?" → platform only. "Do you have a computer at
   home that you use, or that someone in the household uses with you?" → yes (own) / yes (with
   help) / no. (This is the per-person bridge indicator, E1 note §2.5.)

## D. Close

> "Thank you, that's all. If you think of anything, or change your mind, just tell me."

If the person could not find the screens, say "No problem at all, we'll look at it together when I
visit", and record the outcome **could not navigate → S2b**.

---

## Reading sheet (one per library; keep with the private-store papers)

| Field | Value |
|---|---|
| Pseudonym (L-number); person pseudonym(s) | |
| Consent (yes/no), date; call set-up (in person / second line / screen share / speaker / supporter) | |
| Call duration (minutes) | |
| Outcome: read / partly read / could not navigate → S2b / declined | |
| Platform (apple / android) | |
| Devices on this library (types only) | |
| `cloud_on`: iCloud Photos or Google Photos backup (yes/no/unsure); Optimize / Originals; backup quality | |
| M1 iCloud > Storage > Photos (number **and unit**) → `cloud_gb` | |
| M2 iPhone Storage > Photos (number and unit) → `device_gb` | |
| A1 device Images + Videos (number and unit) → `device_gb` | |
| A1 cloud Photos (number and unit) → `cloud_gb`; or shared total only | |
| Item counts: photos __ videos __ | |
| Flags (Apple): `icloud_full`, `mixed` (Mac/PC imports or Shared Library); `?` if unsure | |
| Flags (Android): `saver`, `pre2021`, `pixel`, `shared_total`; `?` if unsure | |
| Model; OS version | |
| Other capture devices (yes/no/unsure; types) | |
| "Free up space" / Optimize ever used (yes/no/unsure) | |
| Person: main capture platform; usable computer (own / with help / none) | |
| Wording that differed from the script | |
