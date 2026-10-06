# Kit E1-S1: run the census script on three family computers

- **Spike:** E1-S1 "Census script on 3 devices" (workstream E1, see `docs/research/PLAN.md`)
- **Exec tag:** CT build (done: `spikes/E1-S1/`) + FM run (this kit). Part A is owner-lab (OL)
  preparation.
- **Prepared by / date:** spike runner (agent), 2026-09-29
- **Who runs it:**
  - Part A: the owner alone, on test accounts;
  - Part B: the owner, on his own devices;
  - Part C: the owner with a relative, at the consolidated visit (see `visit-plan.md`).
- **Time needed (planning estimate; not measured):**
  - Part A: 2–3 h once;
  - Part B: 30 min per device;
  - Part C: about 20 min per device inside the visit.
- **Data-handling class:**
  - Part A: `LAB → results` (test accounts only);
  - Part B: `FAM (owner) → AGG`;
  - Part C: `FAM → AGG`.

## Purpose

Check that the census script counts a relative's files by kind and size in under 10 minutes and
exports nothing identifying. Also check that the person agrees the numbers look right, and that
the script finds at least one place with keepsakes the person did not mention.

## Hypothesis

On a normal family laptop or desktop:

- the census finishes in < 10 min;
- the saved folder contains only totals;
- the relative recognises the totals;
- the "folders outside the usual places" list shows at least one location the relative did not
  mention in the interview.

It never downloads OneDrive or iCloud placeholders.

## Decision it informs

| If the result is… | Then… |
|---|---|
| **Pass** (PLAN): counts and sizes per category in < 10 min; no filenames leave the device; the relative confirms the numbers; at least one unmentioned keepsake location found | Use the script at every visit. Its outputs feed C4 (growth and sizes), A7-S3 (format mix), G2 (device matrix), B1/B2 (support policy), E4 (discovery rules) and the H3 §7.6 generator. |
| **Fail on time** (≥ 10 min) | Run it without `--exif`. If it is still too slow, narrow `--root` to the user folders and record the limitation. B5 learns what a real walk costs. |
| **Fail on privacy** (anything identifying in the output) | Stop using the script. Delete the output. Fix it in CT, then rerun Part B. |
| **Fail on recognition** (the relative says the numbers are wrong) | Record why: for example cloud-only files, another user account, or an external drive. That is a finding for E3's "what is backed up" copy. |
| **No unmentioned location found on any of the 3 devices** | Not a script failure. Record it: the interview already surfaced everything, or the location vocabulary missed it. |
| **No result** (blocked by Smart App Control, EDR, a missing Mac, or no consent) | Record why. Settings readings and the interview stand in (E1 note §4). |

## Budget IDs cited

None directly. PLAN sets "< 10 min" locally for E1-S1. BUD-SCAN (500k files in < 5 min, metadata
reconciliation) is related, so record the file count and time for B5 as well. H1 is asked to list
E1-S1's threshold in the budget overlap table.

## Equipment

| Item | Exact model or version | Why | Have it? |
|---|---|---|---|
| 3 family computers for Part C. Aim for 1 Windows 10/11 (ideally with OneDrive Files On-Demand), 1 Mac, and 1 more Windows or Linux | Record make, model, OS version, disk type (HDD/SSD) | The spike's "3 devices" | |
| The owner's own computer(s) for Part B | Same | Dry run | |
| A Windows 11 test PC or VM with a **test** OneDrive account (H3 owner action 6) | | Part A: real placeholders | |
| A Mac with a **test** Apple ID and iCloud Drive (if any Mac is available) | | Part A: real dataless files | |
| A USB stick (exFAT) holding the builds and an empty `census-output` folder | ≥ 1 GB | Carry the tool in and the totals out | |
| A stopwatch (phone) | — | Time the run | |
| The paper device checklist (`device-checklist.md`) | — | Settings not visible to the script | |

**Software and files needed**

- The census built from `spikes/E1-S1/census`:
  - **Windows:** on the Windows PC with rustup and the MSVC toolchain, run `cargo build --release`
    and copy `target\release\census.exe`. Or cross-build from Linux with the
    `x86_64-pc-windows-gnu` target and a mingw-w64 linker; this was type-checked only, not linked.
  - **macOS:** on a Mac, run `cargo build --release`.
  - **Linux:** `cargo build --release`.
  - **Never** build with `--features emulate-placeholders` for a real run.
- Label each build on the stick with its OS and the git commit it came from.

## Before you start

- [ ] OD-21 (H3 data rules) confirmed, or the PLAN H3 minimum applied.
- [ ] Consent recorded (Part C) with the H3 §9 script, extended by `docs/research/kits/E1-S3/consent-addendum.md`.
- [ ] Managed work or school computers are **excluded**. Do not run the census on them. Record on
      the checklist only whether they hold keepsakes (self-report; E1 note recommendation 5).
- [ ] The relative's computer is plugged in. Note whether it is on battery.
- [ ] Nothing else heavy is running, such as a backup or a game update. Note it if something is.

## Procedure

After each step, write what you saw in the results table, even if it looks unimportant. If
something unexpected happens, stop, take a photo of the screen **only if it shows no file or
folder names**, and write it down.

### Part A: check the placeholder handling on test accounts (owner, once)

The rehearsal could only emulate placeholders (sticky-bit files on Linux). The Windows and macOS
checks compile but have never run.

1. **Windows test PC:** sign in to the **test** OneDrive account. Put 20 test files in it: SYN
   files, or LAB photos made under H3 R8. Wait for them to sync. Right-click the folder and choose
   *Free up space*.
   - **You should see:** cloud icons (online-only) on the 20 files.
2. Put 5 more files in the folder and choose *Always keep on this device*.
   - **You should see:** solid green ticks.
3. Run `census.exe --root "<test OneDrive folder>"`. Do not use `--exif` yet.
   - **You should see:** `cloud_only_files,20` and 5 local files.
   - Afterwards the 20 files still show cloud icons, and OneDrive shows no downloads in progress.
   - If any file turned into a tick, the check failed. Record which.
4. Run it again with `--exif`.
   - **You should see:** the same counts, and the cloud icons unchanged. `--exif` reads only local
     media.
5. **Hydration test** (answers E1 note C10). Pick one online-only **extensionless** test file.
   Open it in Notepad, then close it.
   - **You should see:** it downloads (the icon changes). That confirms opening a placeholder
     hydrates it, which is why the census never opens one.
   - Record what happened.
6. **Mac with a test Apple ID, if available:** in iCloud Drive, put 20 test files in a folder and
   choose *Remove Download*. In Terminal, run `ls -lO` in that folder.
   - **You should see:** a `dataless` flag on those files.
   - Run `./census --root "<that folder>"`. **You should see:** `cloud_only_files,20`, and the
     files still not downloaded.
7. **Timing on a slow disk (optional):** if an old HDD laptop is available, run the census on the
   owner's own home folder there (Part B rules). Record the time and the file count.

**Stop Part A and record "Fail" if:** any placeholder was downloaded by the census in steps 3, 4
or 6. The script must then be fixed in CT before any family run.

### Part B: dry run on the owner's own devices

8. Run `census --list-candidate-folders --out <USB>/census-output/<device-pseudonym>` with no
   `--root`, so it scans the home folder. Start the stopwatch when you press Enter.
   - **You should see:** "Counting files …", then the full printout of what would be saved, then a
     plain-words summary, then a local-only list of folders, then the question "Save these totals
     …?".
9. Stop the stopwatch at the question. Also record the tool's own `elapsed_seconds`.
10. Read the printout. Check it against the H3 §4 list: no names, paths, e-mails or places; months
    only; every small cell "<5".
11. Type `yes`. Check that the USB folder holds only the `census_*.csv` files.
12. Run it again with `--exif` added. Record the time. Decide whether `--exif` is affordable at the
    visits. It adds capture months and camera models, which help C4 growth and the "camera
    originals vs downloads" signal.
13. **macOS only:** note every permission prompt that appears, for example "Terminal would like to
    access files in your Documents folder", and what you answered.
    - Folders you refuse are counted as `unreadable_dirs`. Do **not** grant Full Disk Access on a
      relative's Mac just for the census.
    - The Photos library may be unreadable without it. That is expected, and E1-S2 M3 covers it.

### Part C: at the visit, on each of the three relatives' computers

Run it **after** the interview's "where do your photos and important files live?" questions
(`docs/research/kits/E1-S3/interview-guide.md`, section 3). Then you already have the list of
places the person mentioned, on paper.

14. Ask the relative to sit at their own computer. Explain: "This counts your files by kind and
    size. It does not look inside your photos or send anything anywhere. It shows us everything
    before it saves anything, and you decide."
15. Plug in the USB stick. Open a terminal (Windows: PowerShell; Mac: Terminal). Run the census as
    in step 8. Add `--exif` only if Part B showed it is affordable. Start the stopwatch.
    - **You should see:** the same screens as in Part B.
16. **If Windows Smart App Control, antivirus or a company policy blocks it:** stop. Do not change
    security settings on a relative's computer. Record "No result: blocked by <what the message
    said>".
17. When the question appears, stop the stopwatch. **Read the plain-words summary together.** Ask:
    "Does this look right, about 4,200 photos and 38 GB?" (use the real numbers on screen). Also
    ask: "Does anything look too big, too small or missing?"
    - Record: confirms / partly (why) / no (why).
    - If there is doubt, compare with the count at the bottom of the person's Photos app or the
      folder properties.
18. **Look at the local-only folder list together.** It is printed on screen and never saved. For
    each folder, ask: "What is in here?"
    - If a folder holds keepsakes the person did **not** mention in section 3 of the interview,
      that is an **unmentioned location**.
    - Count them on the sheet by **type only** (for example "old phone copy", "camera card dump").
      Never write the folder name.
19. Ask: "Is it OK to save these totals on my USB stick?" Type `yes` only if they agree.
    **You should see:** "Saved to …".
20. Fill in `device-checklist.md` for this computer together: OS, storage, cloud settings,
    accessibility settings, other accounts.
21. Eject the stick. At home, copy the folder into the private store (H3 R7). Delete it from the
    stick.

**Stop and record "No result" if:** the relative hesitates at any point, the tool asks for an
administrator password (it should not), or the computer belongs to an employer or school.

## Cleaning up

1. Delete the census binary from the relative's computer if you copied it there. The tool writes
   nothing else on their computer.
2. Wipe the `census-output` folder from the USB stick once it is in the private store.
3. Part A: delete the test files and sign out of the test accounts.
4. Delete raw census folders from the private store 90 days after the AGG is accepted (H3 R7).

## Data handling

H3 defines the classes, rules and output check (`docs/research/h3-research-data-governance.md`
§2–§4; draft until OD-21).

- **Collected:**
  - on the device: category × extension group × log2 size-bin counts and bytes; location class ×
    category totals; media per month (last 24 months); optionally camera models; run time and
    counters;
  - on paper: the device checklist, the confirmation answer, and the count and types of
    unmentioned locations.
- **Never collected:** file or folder names, paths, photos, hashes, GPS, e-mail or account names,
  the local-only folder list.
- **Raw data stays** in the private store.
- **May be pasted below:** family-wide totals after the H3 §4 check (cells below 5 as "<5"; no
  per-person rows unless each covers at least 5 devices), timings, pass/fail per criterion, and
  device model and OS counts.

## Results

Copy this section into `docs/research/kits/E1-S1/results.md` and fill it in. Do not edit the
numbers afterwards; add a note instead.

- **Run by / dates / places:** <...>
- **Builds used:** <OS, git commit, with or without `--exif`>
- **Emulator or VM used instead of real hardware?** Part A: <test PC or VM>. Parts B and C: No.

| Step | Expected | What happened | Measurement (with unit) | Note (no names) |
|---|---|---|---|---|
| A3–A4 | 20 cloud-only counted; none hydrated | | cloud_only_files = __ | |
| A5 | Opening a placeholder hydrates it | | | |
| A6 (Mac) | `dataless` files counted; none hydrated | | | |
| B8–B12 | Dry run under 10 min; output passes H3 §4 | | __ files in __ s (no exif); __ s (exif) | |
| C device 1 | | | __ files, __ s; disk HDD/SSD | |
| C device 2 | | | | |
| C device 3 | | | | |

| Pass criterion | Budget ID | Measured value | Pass / Fail / No result |
|---|---|---|---|
| Counts and sizes per category in < 10 min, on each of 3 devices | (local; BUD-SCAN related) | __ / __ / __ min | |
| No filenames leave the device (H3 §4 check on each output folder) | — | | |
| The relative confirms the numbers | — | confirms __ / partly __ / no __ | |
| At least one unmentioned keepsake location found | — | __ unmentioned locations across 3 devices (types: __) | |

- **Overall:** Pass | Fail | No result
- **Placeholder totals (family-wide):** cloud-only files __; logical GB __
- **Surprises and points of confusion:** <permission prompts, security blocks, wording that confused the relative>
- **Follow-ups for the workstream:** <for B5, E4, C4, G2, E3>
