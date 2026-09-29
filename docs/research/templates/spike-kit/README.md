# Kit <SPIKE-ID>: <short title>

<!--
Spike-kit template (owner: H1). For [OL], [FM] and [EXT] spikes, which a cloud agent cannot run.
Copy this folder to docs/research/kits/<spike-id>/ and fill it in. Put any scripts next to this file.
Write for the person running it: the owner, or a relative with the owner's help. Plain words,
numbered steps, one action per step, and what they should see after each step.
Delete these comments before handing the kit over. Mark the spike "kit-ready" in the research note.
-->

- **Spike:** <SPIKE-ID> (workstream <ID>, see `docs/research/PLAN.md`)
- **Exec tag:** OL | FM | EXT
- **Prepared by / date:** <agent or person>, YYYY-MM-DD
- **Who runs it:** Owner | Owner with relative | Relative, owner silent | External wait
- **Time needed:** <hands-on time> plus <waiting time>
- **Data-handling class:** <class from H3's `docs/research/h3-corpus-and-data-governance.md`; see "Data handling" below>

## Purpose

<One or two sentences: what this kit finds out, in plain words.>

## Hypothesis

<What we expect to happen, stated so the result can prove it wrong.>

## Decision it informs

| If the result is… | Then… |
|---|---|
| **Pass**: <criterion copied from PLAN> | <option X; ADR-NNNN / OD-NN> |
| **Fail** | <option Y> |
| **No result** (could not run, blocked) | <what happens, e.g. the claim stays "secondary only" and the ADR notes it> |

## Budget IDs cited

<List the IDs from `docs/research/budgets.md` the pass criterion uses, e.g. BUD-ENROLL. Do not introduce a new threshold here. If one is needed, ask H1 to add a budget ID.>

## Equipment

| Item | Exact model or version | Why | Have it? |
|---|---|---|---|
| <e.g. Windows 11 PC, clean install, Smart App Control on> | | | Yes / Buy (H5) / Borrow |
| <e.g. exFAT USB stick, 32 GB> | | | |

**Software and files needed:** <builds, scripts in this folder, test data (synthetic unless stated)>

## Before you start

- [ ] <e.g. take a VM snapshot, or note the current setting so it can be restored>
- [ ] <e.g. charge the phone to 100 %; plug in or unplug as the procedure says>
- [ ] Consent recorded (FM kits only; use H3's consent script)

## Procedure

Do the steps in order. After each step, write down what you saw in the results table, even if it looks unimportant. If something unexpected happens, stop, take a screenshot or photo, and write it down.

1. <Action.> **You should see:** <expected screen or output.>
2. <Action.> **You should see:** <...>
3. <...>

**Stop and record "No result" if:** <abort conditions, e.g. the device prompts for an admin password you do not have>

## Cleaning up

1. <Undo changes: restore the setting, delete test files, revert the snapshot.>
2. <Delete anything that must not be kept, per the data-handling class.>

## Data handling

H3 defines the classes and the rules. Until H3's document exists, apply the plan's rules (PLAN H3):

- Only **sizes, types and counts** leave the device or the homelab. Never filenames, pixels or EXIF GPS.
- Private fixtures stay on the homelab, outside the repo.
- No family data in the repo, CI, logs, issues or notes.
- Relatives whose media appears in fixtures give consent first.
- Census-style results are aggregates only.

<State what this kit collects, where raw data stays, and what may be pasted into the results below.>

## Results

Copy this section into `docs/research/kits/<spike-id>/results.md` and fill it in. Do not edit numbers afterwards; add a note instead.

- **Run by / date / place:** <...>
- **Hardware and OS actually used:** <exact models and versions; say if anything differed from the Equipment list>
- **Emulator or VM used instead of real hardware?** No | Yes: <what, and why>

| Step | Expected | What happened | Measurement (with unit) | Screenshot or log |
|---|---|---|---|---|
| 1 | | | | |

| Pass criterion | Budget ID | Measured value | Pass / Fail / No result |
|---|---|---|---|
| <copied from PLAN> | BUD-... | | |

- **Overall:** Pass | Fail | No result
- **Surprises and points of confusion:** <anything unexpected, especially dialogs, prompts and wording that confused the tester>
- **Follow-ups for the workstream:** <...>
