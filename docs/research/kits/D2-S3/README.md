# Kit D2-S3: combined recovery drill (the only one)

- **Spike:** D2-S3 (workstream D2, see `docs/research/PLAN.md`, section "D2.")
- **Exec tag:** FM
- **Prepared by / date:** D2 spike runner (agent), 2026-09-29
- **Who runs it:** Relative, owner silent. An observer (not the owner if possible) times and logs.
- **Time needed:** owner preparation about 2 h (once); the drill itself up to 2 h (BUD-RECOVERY) plus 30 min debrief
- **Data-handling class:** `LAB → results` for the drill photos (owner-made test photos with no people in them, H3 R8); `SEC` for the drill key and drill shares (a throwaway drill key, destroyed after the drill); results are `AGG`-style notes only (timings, counts, confusion log). No family data.

## Purpose

Find out whether a relative who did not build Reliquary can get 10 named photos back using only
the doomsday kit: the printed runbook, two of three share cards, the backup disk and stock tools,
with no help from the owner.

This one drill also covers the stock-tools decryption check (A2), no-software recovery (A6-S5),
cold restore (preservation) and the break-glass tabletops of A8 and E7 (see "Tabletop add-on").

## Hypothesis

A non-author relative following `tester-runbook-drill.md` recovers all 10 named photos within
BUD-RECOVERY (≤ 2 h) with no owner help. We expect the points of confusion to be: opening a
terminal, typing 20 or 33 words exactly, pasting a secret into a prompt that does not echo, and
typing object codes.

## Decision it informs

| If the result is… | Then… |
|---|---|
| **Pass**: all 10 photos recovered within BUD-RECOVERY with no owner help; every point of confusion logged | The recovery-recipient design (sealed recovery identity + SLIP-39 2-of-3 shares, stock tools) goes into ADR-0008 as drilled. Gate C item "D2-S3 recovery drill passed" is met. OD-08 can be confirmed with the tested k-of-n and holders. |
| **Fail** (over 2 h, owner help needed, or photos not recovered) | Fix the runbook, card wording or tooling (for example a one-command recovery script shipped on the disk, a bootable recovery USB, or 128-bit instead of 256-bit shares) and re-run with a different relative. If the stock-tools path itself is the blocker, ADR-0008 must add a supported recovery tool and say how it stays runnable for decades. |
| **No result** (drill not run) | Gate C cannot pass (PLAN §4.2 lists this drill). ADR-0008 records the recovery path as "tested mechanically only" (see `dry-run-check.py`). |

## Budget IDs cited

- **BUD-RECOVERY**: a non-author recovers 10 named photos from the doomsday kit in ≤ 2 h.

No other threshold is introduced here.

## Equipment

| Item | Exact model or version | Why | Have it? |
|---|---|---|---|
| Recovery computer | Record make, OS and version. Prefer a computer the relative did not set up. Linux or macOS (the runbook's commands are Unix shell commands) | Where the relative types the commands | |
| age | Official release, v1.3.0 or later (v1.3.2 is current, tagged 2026-08-29); record the exact version. v1.3.0+ is needed for post-quantum keys and for `age-plugin-batchpass` in `make-drill-disk.sh` | Decryption | |
| python-shamir-mnemonic | 0.3.0 with the CLI extra: `pip install 'shamir-mnemonic[cli]==0.3.0'` | SLIP-39 share recovery. Its README warns it is a reference implementation that does not protect secrets, so use it only on an offline computer | |
| DRILL USB disk | Any USB disk, labelled "DRILL" | Holds the drill store made by `make-drill-disk.sh` | |
| 3 share cards | Paper or card, one per share, labelled Card 1/2/3 and "DRILL" | Two of them are handed to the relative | |
| 10 LAB photos | Photos the owner takes for the drill, with no people in them (for example a houseplant or a mug) | The "10 named photos" | |
| Printed runbook | `tester-runbook-drill.md`, printed, with the 10 names filled in | The only help the relative gets | |
| Timer and observer sheet | Phone timer, `observer-log.md` printed | Timing and the confusion log | |

**Software and files needed:** `make-drill-disk.sh` and `dry-run-check.py` in this folder; `tester-runbook-drill.md`; `observer-log.md`.

## Before you start

- [ ] Consent recorded for the relative (H3's consent script; this is a family session, E2 test plan).
- [ ] Decide the variant with the owner and write it on the observer sheet: classic (X25519) or post-quantum
      (`--pq`), and 128-bit shares (20 words each) or 256-bit shares (33 words each). Use what ADR-0008 proposes (OD-06, OD-08).
- [ ] On an **offline** computer that has age ≥ 1.3.0 and `shamir`, run `./dry-run-check.py` (add `--pq` or
      `--bits 256` for the chosen variant). All checks must pass. This proves only that the commands work.
- [ ] Run `./make-drill-disk.sh ~/drill-photos /path/to/DRILL [--pq] [--bits 256]` on the offline computer.
      Copy the three share texts it prints onto three cards by hand, plus the "Recovery key check" line on each card.
      Do not save the share texts anywhere. Copy the `DRILL` folder onto the USB disk.
- [ ] Fill in the 10 file names on the last page of the runbook and print it. Do not print the object codes.
- [ ] Prepare the recovery computer: install age and `shamir`, and check that `age --version` and
      `shamir --help` run. Do not leave any other notes on it.
- [ ] Brief the observer: they time each step, write down every hesitation, question or wrong turn, and
      **do not help**. If the relative asks for help, the observer says "Please use the sheet" and logs it.

## Procedure

Do the steps in order. The observer writes what happens after every step on `observer-log.md`, even if it looks unimportant.

1. The observer gives the relative the runbook, cards 1 and 3 (or any two), the DRILL disk and the recovery computer, and starts the timer. **You should see:** the relative reading the sheet.
2. The relative follows runbook steps 1 to 8 on their own. The observer logs the start and end time of each runbook step, every point of confusion (what they were trying to do, what they saw, what they did), and every wrong command.
3. If the relative is stuck for 15 minutes on one step, the observer may give **one** prepared hint (the next line of the runbook read aloud) and must log it as "help given". Owner help ends the attempt as **Fail** for the pass criterion, but carry on to the end to find the later problems.
4. When the relative says they are done, stop the timer. The observer checks that the 10 photos open and match (look at them; optionally compare SHA-256 with the catalog).
5. Debrief for 15 to 30 minutes: ask what was hardest, which words on the sheet were unclear, and what they would want printed differently. Log answers in their words.
6. **Tabletop add-on (A8, E7), 20 minutes, after the debrief:** walk through these scenarios on paper with the relative and log what they say they would do:
   - The owner is unreachable and the homelab will not start. Where is the disk? Who holds the other cards?
   - One card is lost. (Expected: any two of the three still work; the owner re-issues cards.)
   - A card holder has died or left the family. (Expected: re-issue cards; SLIP-39 extendable shares allow this without changing the recovery key; see the D2 note.)
   - Someone asks them to "just photograph the cards and send them". (Expected: refuse.)

**Stop and record "No result" if:** the recovery computer cannot run `age` or `shamir`, the DRILL disk does not mount, or `dry-run-check.py` did not pass beforehand.

## Cleaning up

1. Delete `~/recovery-key.txt`, `~/catalog.txt` and the recovered photos from the recovery computer (runbook step 8 does the first two; check).
2. Shred the three drill share cards, or keep them sealed in the drill envelope for next year's drill with the same DRILL disk.
3. The DRILL disk holds only LAB photos and decoys. It may be kept for the annual drill.
4. Never reuse the drill key or drill shares for real data.

## Data handling

Applies H3 (`docs/research/h3-research-data-governance.md` §2 to §4, draft until OD-21):

- The drill uses LAB photos only (no people in them) and random decoy files. No family photos.
- The drill secret and share texts are SEC: shown once on screen, copied by hand to cards, never saved, never photographed, never pasted into notes, issues or chat.
- Results that may go into the repo: timings, counts, the variant used, tool versions, OS names, and the confusion log **without the relative's name** (use "Relative A").
- Screenshots: only of error messages, never of a share card or the secret.

## Results

Copy this section into `docs/research/kits/D2-S3/results.md` and fill it in. Do not edit numbers afterwards; add a note instead.

- **Run by / date / place:** <observer>, <relative code, e.g. Relative A>, <date>, <place>
- **Variant:** classic | pq; shares 128-bit (20 words) | 256-bit (33 words); decoys: <N>
- **Hardware and OS actually used:** <recovery computer model, OS and version; age version; shamir-mnemonic version>
- **Emulator or VM used instead of real hardware?** No | Yes: <what, and why>
- **`dry-run-check.py` passed beforehand:** Yes (<date>, <checks passed>) | No

| Runbook step | Expected | What happened | Time taken (min) | Help given? |
|---|---|---|---|---|
| 1 Start / open terminal | Terminal open | | | |
| 2 Go to the disk | No error | | | |
| 3 Share cards | `SUCCESS!` | | | |
| 4 Unlock key | No error | | | |
| 5 Check key | Start and end match the card | | | |
| 6 Catalog | 10 names found | | | |
| 7 Photos | 10 photos open | | | |
| 8 Clean up | Files removed | | | |

| Pass criterion | Budget ID | Measured value | Pass / Fail / No result |
|---|---|---|---|
| A non-author relative recovers the 10 named photos from the doomsday kit with no owner help, and every point of confusion is logged | BUD-RECOVERY (≤ 2 h) | <total minutes>; <photos recovered>/10; <help events> | |

- **Overall:** Pass | Fail | No result
- **Surprises and points of confusion:** <from `observer-log.md`, in the relative's words where possible>
- **Tabletop answers (A8, E7):** <one line per scenario>
- **Follow-ups for the workstream:** <runbook wording, card layout, tooling, k-of-n, holder choice>

## Agent dry run of this kit (2026-10-06)

`dry-run-check.py` was run in the research container (x86-64 Linux, age v1.3.1 built from
`proxy.golang.org`, shamir-mnemonic 0.3.0, SYN photos) for the classic 128-bit and PQ 256-bit variants:
10/10 checks passed for each. The output is in `dry-run-2026-10-06.txt` (it contains no share text or secret).
An earlier draft of this section, dated 2026-09-29, referred to a `dry-run-2026-09-29.txt` that was never
saved; this run replaces it. The dry run shows only that the commands work mechanically (about 1 s of tool
time). It is not a result for D2-S3, which needs a real relative.
