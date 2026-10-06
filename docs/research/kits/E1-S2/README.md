# Kit E1-S2: how much of the family's camera-roll data is on iPhones and iPads?

- **Spike:** E1-S2 "iOS-share gate" (workstream E1, see `docs/research/PLAN.md`). This kit runs it
  in two parts, as `docs/research/e1-family-research-census.md` §2 proposes:
  - **S2a:** a remote quick count in Wave 1, so OD-01 gets evidence before it is due;
  - **S2b:** the same readings repeated at the home visit, as a check and a second time point.
- **Exec tag:** FM
- **Prepared by / date:** spike runner (agent), 2026-09-29; revised by the E1 synthesizer
  2026-10-06 after skeptic review (wider Apple range, Android flags, INCOMPLETE verdict, call
  safety and set-up, per-person bridge indicator).
- **Who runs it:** the owner, with each relative who owns a camera library. It is done by phone or
  video call (S2a) and again in person (S2b).
- **Time needed (planning estimate; not measured):**
  - Part 0: about 30 min of owner preparation;
  - S2a: 10–15 min per library owner (time the first two calls; older relatives may need longer
    or a helper);
  - S2b: about 10 min inside each visit.
- **Data-handling class:** `FAM → AGG`. Raw readings go on paper or into the private store (H3 R7).
  Only the family-wide share range, plus platform totals where a platform has at least 5
  libraries, leave the store (H3 §4).

## Purpose

Find out whether iPhones and iPads hold 40 % or more of the family's camera-roll bytes. If they do,
OD-01 ("iOS in v1 or deferred") is escalated before ADR-0004 (PLAN E1-S2; B4's recommendation).

## Hypothesis

The owner's intake guess (Q-F3: under 20 %, 20–40 % or over 40 %) is right. The remote readings
put the family-wide share clearly on one side of 40 %, not in a range that straddles it.

## Decision it informs

| If the result is… | Then… |
|---|---|
| **Pass (escalate):** share_low ≥ 40 % of camera-library bytes on iPhones or iPads | Escalate OD-01 before ADR-0004. B4's note: start the Apple membership and B4-S2 now. |
| **Fail (do not escalate):** share_high < 40 % | OD-01 goes ahead on B4's default recommendation ("iOS after the pilot, with a bridge"). |
| **Straddle:** the range contains 40 % | Run M3 (a family Mac) or A2 (an Android census build) at the earliest visit (S2b). If OD-01 is due first, the owner decides with the range shown. |
| **Incomplete** (`share_range.py` prints INCOMPLETE: a required reading is blank) | No verdict. Take the missing readings, or wait for S2b. |
| **No result** (Part 0 failed, not enough calls done, readings unusable) | OD-01 is decided on the Q-F3 guess and B4's default. The decision record says "E1-S2 not run", and the gate is rechecked after S2b. |

PLAN states the 40 % threshold. This kit does not change it.

## Budget IDs cited

None. The 40 % gate is PLAN's own threshold for E1-S2, not a budget.

## Definitions (the metric)

Take these from the E1 note §2.1. Check them before the first call, because they decide what you
write down.

- **Library, not device.** An iPhone, an iPad and a Mac on the same Apple ID with iCloud Photos on
  share **one** library. Count it once.
  - A Google account with Google Photos backup is one Android library. The phone's own storage
    belongs to it.
- **Original bytes, including cloud-only originals.** Under iCloud "Optimize iPhone Storage" or
  after Google Photos "Free up space", the phone holds less than the library does. Read the
  cloud-side figure as well.
- **Denominator:** phone and tablet camera libraries only. Old camera cards, scans and desktop-only
  archives are A9's seed, not a camera roll. Leave them out.
- **Apple share** = Σ Apple library bytes ÷ Σ all phone/tablet camera-library bytes.

## Methods (which reading to take)

The Settings paths below come from Apple and Google support pages that could only be seen as search
snippets (blocked from the research container; E1 note K4, K5 and K10). **They are unverified.** Part 0 checks
them on the owner's own phones first.

| Code | When | What to read | Write down |
|---|---|---|---|
| **M1** | iPhone/iPad with iCloud Photos **on** | Settings > [your name] > iCloud > (Manage Account) Storage: the **Photos** figure | `cloud_gb` = that figure |
| **M2** | Every iPhone/iPad (also when M1 exists) | Settings > General > iPhone (iPad) Storage: the **Photos** figure | `device_gb` = that figure |
| **M3** | Only at S2b, if the range straddles 40 % and a family Mac holds the same library | osxphotos on that Mac: an aggregate query (see step 19) | `method` = M3, `cloud_gb` = the total of original sizes (or `bound_gb` for a `mixed` library) |
| **A1** | Android phone | (a) Device: Settings > Storage, the Images and Videos figures (labels vary by maker). (b) Cloud: Google Photos > profile picture > the account storage figure, or the Google One storage breakdown for **Photos** | `device_gb` = (a) Images + Videos; `cloud_gb` = (b) Photos |
| **A2** | Only at S2b, if needed and B2 has a build | An Android MediaStore census app | `device_gb` from the app |

Also note, for every library, **without** writing down any photo or file name:

- iCloud Photos on or off, and Optimize or Download Originals;
- Google Photos backup on or off, and its quality (Original quality or Storage saver);
- whether "Free up space" has ever been used (yes, no or unsure);
- the **flags** that widen the range (see `share_range.py`'s header): Apple `icloud_full`
  (storage full or uploads paused) and `mixed` (Mac/PC imports, scans or Shared Library in the
  same library); Android `saver` (Storage saver or High quality ever used), `pre2021` (backup
  started before June 2021), `pixel` (a Pixel 1–5) and `shared_total` (only a shared quota total
  was visible). Add `?` when unsure; unsure counts as yes. Why: uploads in High quality before
  June 2021, and Pixel 1–5 uploads, reportedly do not count toward the Google quota, so the cloud
  figure can be far below the library (secondary only; support.google.com blocked);
- the item counts at the bottom of the Photos / Google Photos library (a cross-check only);
- per **person** (not per library): the main capture platform, and whether they have a computer
  they use, alone or with help. This is the bridge indicator for OD-01 (E1 note §2.5);
- the device model and OS version (Settings > General > About; Settings > About phone). B4 needs
  iOS 26.1+ and 27 eligibility.

## Equipment

| Item | Exact model or version | Why | Have it? |
|---|---|---|---|
| The owner's own iPhone (or a family iPhone the owner may handle) | Record the model and iOS version | Part 0: check the M1/M2 wording | |
| The owner's own Android phone (or a test one) | Record the model and Android version | Part 0: check the A1 wording on at least one maker's Settings | |
| A phone or video-call line to each library owner | — | S2a | |
| The paper reading sheet (`call-script.md`, last page) or the private-store spreadsheet | — | Raw readings | |
| A computer with Python 3 that can reach the private store | Python 3.8+ | `share_range.py` | |
| (S2b, optional) A family Mac with the same iCloud Photos library | macOS with Photos | M3 cross-check | |

**Software and files:** `call-script.md` (what to say and ask), `share_range.py` (the calculator; tested on
synthetic inputs only), and the CSV layout in `share_range.py`'s header.

## Before you start

- [ ] OD-21 (H3 data rules) is confirmed, or you agree to apply the PLAN H3 minimum rules.
- [ ] The H3 §9 consent script is approved, plus the short phone version in `call-script.md`.
- [ ] The private store exists (H3 R7), with a folder `e1-s2/` for `libraries.csv`. If there is no
      store yet, use paper kept at home.
- [ ] A list of library owners, using **pseudonyms only** (L1, L2 …). The name ↔ pseudonym mapping
      stays in the private store.
- [ ] Part 0 is done.

## Procedure

### Part 0: check the Settings wording on the owner's own phones (about 30 min)

1. On an iPhone with iCloud Photos on, open Settings > [your name] > iCloud. **You should see:**
   a storage bar and an entry such as "Manage Account Storage" or "Storage". Write down the exact
   wording.
2. Open it and find **Photos**. Write down the figure and its unit.
3. Open Settings > General > iPhone Storage > Photos. Write down the figure. **You should see:** a
   figure smaller than step 2 if Optimize iPhone Storage is on (E1 note K4, contested). Record whether it
   is smaller.
4. Open the Photos app > Library and scroll to the bottom. **You should see:** "N Photos, M Videos".
   Note whether the figures in steps 2 and 3 would plausibly fit that many items.
5. Check whether the Photos figure in step 2 includes **Recently Deleted** and a **Shared Library**
   (look for any label that says so). Write "unknown" if nothing says. The E1 note lists this as an
   open question. If you can, also test it: note the M1 figure, delete a few large **test** videos,
   and read M1 again before and after emptying Recently Deleted.
5a. If iCloud storage on a test account is full (or can be made full), check whether the Photos
   figure stops growing while new photos stay on the phone. This tests the `icloud_full` flag.
5b. If the family shares an **iCloud+ or Google One family plan** that you organise, check whether
   your organiser screens show each member's usage. If they do, that may replace some calls; note
   exactly what it shows (it may include mail and drive, not only photos).
6. On an Android phone, open Settings > Storage. Write down the exact labels for images and videos.
   **You should see:** separate Images and Videos rows on most phones; the labels vary by maker.
7. In Google Photos, tap the profile picture and find the account storage figure. If it shows a
   breakdown, write down the **Photos** figure. If it shows only a shared total for Gmail, Drive and
   Photos, open Google One (app or web) and look for the per-service breakdown. Write down where
   you found it.
8. Update the Methods table in your copy of this kit with the exact wording. Use that wording in
   the calls.
8a. **Gate.** If Part 0 cannot find a Photos-only figure that behaves as described (steps 2–5),
   do **not** run S2a for that platform. Record "Part 0 failed" and tell the owner: OD-01 is then
   **scheduled** for after the visits (decision request option B in the E1 note), with M3/A2 at the
   visits. The whole S2a method rests on these screens (E1 note claim K5, contested).

**Stop and record "No result" for a method if:** you cannot find a Photos-only figure. For
example, iCloud may show only a total, or Google may show only the shared quota. Then use the other
method for that platform, or take the reading at the visit (S2b).

### Part S2a: remote quick count (Wave 1, week 1; one call per library owner)

9. Choose the set-up (`call-script.md`, "Before the call"): in person or with a helper first,
   then a second line, then screen sharing, then the same phone on speaker. Book about 15
   minutes. Say it is about "how much space photos take", not about any product. Time the first
   two calls.
10. Read the short consent text in `call-script.md`, and record yes or no on the sheet. **No means
    stop.** Thank them; nothing changes for them.
11. Ask them to have the phone in hand and to read the screens aloud **as you guide them**
    (`call-script.md`, part B). Write only the figures and the settings (on/off/quality) on the
    sheet.
    - Never ask for or write down a photo, album or file name, a place, or an account e-mail.
12. If the person has more than one device on the same Apple ID or Google account, take the
    readings **once**, from the phone.
13. Ask the two extra questions in `call-script.md`, part C: other devices they take photos with,
    and whether they have ever used "Free up space". Note the answers as yes, no or unsure.
14. After the call, type the row into `libraries.csv` in the private store, with the columns in
    `share_range.py`'s header: `library` (pseudonym), `platform`, `method`, `cloud_on`,
    `device_gb`, `cloud_gb` (both in GB; convert MB), `flags`, `bound_gb` (blank unless you have an
    independent bound), `note`. Leave a figure **blank** if it was not read; never type 0 for
    "not read". The note stays in the store. Keep the per-person bridge indicator in a separate
    `persons.csv` (pseudonym, main platform, computer own / with help / none).
15. When all the calls are done (or on the day before OD-01 sitting 2), run on the owner's machine:
    `python3 share_range.py /path/to/private-store/e1-s2/libraries.csv`
    **You should see:** the library counts (or "<5"), the counts of unbounded libraries, platform
    totals (or "withheld"), the share range and a verdict: ESCALATE, DO NOT ESCALATE, STRADDLE or
    INCOMPLETE. Nothing per library is shown. INCOMPLETE means a required reading is missing:
    there is no verdict until it is taken. A STRADDLE with "share_low unknown" means some flagged
    libraries need M3, A2 or an item-count bound before escalation can be shown.
15a. From `persons.csv`, count family-wide (H3 §4 "<5" rule): people whose main camera is an
    iPhone or iPad, and how many of them have no usable computer. Report this next to the share;
    it does not change the 40 % rule.
16. Apply the H3 §4 output check to that printout. Then copy it into `results.md`.

### Part S2b: at the consolidated visit (weeks 3–7)

17. Repeat steps 11–13 on the device itself, looking at the screen together. Record the new
    figures in a **new** row with the same pseudonym and method, and write "S2b" in `note`.
    - The difference from S2a, divided by the weeks between the two readings, is only a **sanity
      check** on growth. Settings figures are rounded and move with deletions and Recently
      Deleted purges, so over 2–6 weeks the change may be below their resolution. Prefer the
      capture-month histograms (M3, A2, desktop census) for growth (C4).
18. **If the S2a range straddled 40 %** and a family Mac holds that iCloud Photos library, run M3
    (step 19). Otherwise skip to step 20.
19. **M3 (optional, on the family Mac, with the Mac owner's consent):**
    - Install osxphotos in a virtual environment (osxphotos 0.77.2 on PyPI, MIT; `pip install
      osxphotos`).
    - Run an aggregate-only query that prints the **sum** of `original_filesize` over all assets,
      and the sum over assets whose `ismissing` is true.
    - Print **no** per-asset rows, and never write them to a file.
    - This step has not been rehearsed. The E1 note (K11) flags that `original_filesize` may be
      empty for cloud-only assets. If the "missing" subset sums to zero while Photos shows
      cloud-only items, write M3 as "No result".
    - The macOS privacy prompt for Photos access may appear. The Mac owner decides whether to
      allow it.
20. Rerun `share_range.py` with the S2b rows substituted for the S2a rows of the same libraries.
    Record both results.

**Stop and record "No result" if:** the person seems uneasy, is asked to type a password, or the
Settings screen asks them to sign in again. Do not guide anyone through a sign-in, and never guide
anyone through a purchase or upgrade screen.

**Considered and not used: a one-off iOS census app.** The free Apple Personal Team could install a
throwaway census app by cable on up to 3 iPhones at a time for 7 days (B4 K10), so cost alone does
not rule it out at S2b. It is not used because: the only documented byte size (`dataSize`) exists
from iOS 27 and can be `nil`; it needs a Mac with Xcode, Developer Mode on the relative's phone
(restart and warning screens; unverified for current iOS) and trusting a developer profile; it
needs full library access; and a Personal Team build is still Apple code signing, which CLAUDE.md
and ADR-0002 §5 exclude "for now", so it would need an owner exception (E1 note §2.2).

## Cleaning up

1. Paper sheets: store them with the private-store papers. Shred them 90 days after the AGG result
   is accepted (H3 R7).
2. `libraries.csv`: delete it 90 days after the AGG is accepted, together with the pseudonym
   mapping for E1-S2, unless the census (E1) still needs it.
3. M3: delete the virtual environment and any osxphotos cache or export folder on the family Mac.
   osxphotos may write a local database copy; check its output folder and delete it.

## Data handling

H3 defines the classes, rules and output check (`docs/research/h3-research-data-governance.md`
§2–§4; draft until OD-21).

- **Collected:**
  - per library: GB figures, on/off and quality settings, device model and OS version;
  - per person: consent yes or no.
- **Never collected:** names of photos, albums or files, places, account e-mails, screenshots of
  Settings with the account name visible.
- **Raw data stays in** the private store or on paper at home.
- **May be pasted below:** only `share_range.py`'s printout after the H3 §4 check. That is:
  - the library counts, shown as "<5" below 5;
  - platform totals only where a platform has at least 5 libraries;
  - the share range and the verdict;
  - the counts of libraries per setting (for example "Optimize on: 3 of 6"), with "<5" rules
    applied;
  - the device-model and OS-version counts that G2 needs.

## Results

Copy this section into `docs/research/kits/E1-S2/results.md` and fill it in. Do not edit the
numbers afterwards; add a note instead.

- **Run by / dates:** S2a <dates>; S2b <dates>
- **Part 0 wording found:** M1 path "<exact>"; M2 path "<exact>"; A1 device labels "<exact>";
  A1 cloud figure found at "<exact>"; Recently Deleted and Shared Library included? <yes/no/unknown>
- **Emulator or VM used instead of real hardware?** No (none is possible for this spike)

| Step | Expected | What happened | Measurement (with unit) | Note |
|---|---|---|---|---|
| Part 0 (steps 1–8) | Photos-only figures found for M1, M2, A1 | | | |
| S2a calls | One call per library owner | | Libraries read: apple __ / android __ ; declined __ | |
| S2a calculator | Share range and verdict | | __ % – __ % | |
| S2b re-reads | Same screens at the visit | | Libraries re-read __ | |
| M3 (if run) | Original-size total available | | | |

| Pass criterion | Budget ID | Measured value | Pass / Fail / No result |
|---|---|---|---|
| ≥ 40 % of camera-roll bytes on iPhones or iPads → escalate OD-01 (PLAN E1-S2), judged on share_low; straddle rule as above | none | S2a: __–__ %; S2b: __–__ % | Escalate / Do not escalate / Straddle / No result |

- **Overall:** Escalate | Do not escalate | Straddle | No result
- **Call durations (first two calls, minutes) and set-ups used:** __ / __; outcomes: read __,
  partly __, could not navigate → S2b __, declined __ ("<5" rule)
- **Bridge indicator (people, "<5" rule):** main camera iPhone/iPad __; of those with no usable
  computer __
- **Settings in use (counts of libraries, "<5" rule):** iCloud Photos on __; Optimize on __;
  Google Photos Original __ / Storage saver __; "Free up space" used __
- **OS versions (counts):** iOS/iPadOS ≥ 27 __; 26.1–26.x __; older __; Android by major version __
- **Surprises and points of confusion:** <for example, wording that confused the relative, or
  figures that did not add up>
- **Follow-ups for the workstream:** <for OD-01, B4, C4, G2>
