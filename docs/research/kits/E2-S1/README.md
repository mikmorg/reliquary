# Kit E2-S1: clickable enroll + health prototype with 5 relatives

- **Spike:** E2-S1 (workstream E2, see `docs/research/PLAN.md`, section "E2.")
- **Exec tag:** FM
- **Prepared by / date:** E2 spike runner (agent), 2026-09-29. Not yet run.
- **Who runs it:** The owner, or better the neutral facilitator from E1 (`kits/E1-S1/visit-plan.md`), with one relative at a time. **The relative works unaided; the facilitator stays silent** apart from the scripted lines.
- **Time needed:** about 20–25 minutes per relative inside the consolidated visit (a planning estimate, not measured), plus about 1 hour of preparation once, and one dry run with the helper persona.
- **Data-handling class:** `SYN → FAM → AGG`. The prototype shows only synthetic numbers and stores nothing. The observation sheets are family data (FAM) and stay in the private store. Only aggregates (counts, medians) go into `results.md`. See "Data handling".

## Purpose

To find out whether non-technical relatives can set up Reliquary on a computer from the kit card and then say correctly whether their photos are safe, without help. It tests the first-run flow and the health view that ADR-0004 (draft) puts in milestone M2, before anything is built.

## Hypothesis

At least 4 of 5 non-technical relatives, using the clickable prototype in `prototype/index.html` on a laptop, (a) get from "Get started" to the health view with no assist, and (b) answer all three judgement questions correctly (rubric in `session-sheet.md`).

## Decision it informs

| If the result is… | Then… |
|---|---|
| **Pass**: ≥ 4 of 5 complete "enroll and tell me if your photos are safe" unaided (PLAN E2) | The first-run and health-view scope in ADR-0004 (draft) for M2 stands. The screens and words that worked go to E3 (ADR-0024 copy deck) and E5 (ADR-0038 kit spec) as tested input. |
| **Fail** | RITE, as PLAN says: fix the screen or wording that caused the failure in `prototype/index.html` before the next session and retest (see "RITE rule" below). If a second round still fails, the analyst's pivot checkpoint "After P2" applies (`docs/research/e2-v1-scope-metrics-pilot.md` §4.4): simplify the UX (for example a health email only) or keep that persona on the concierge route. |
| **No result** (fewer than 5 relatives can take part, intake Q-F8/Q-F9; or visits do not happen) | ADR-0004 stays Proposed with its UX scope marked "untested". Report whatever sessions ran as counts only, and say that n < 5. Do not turn a smaller sample into a pass. |

## Budget IDs cited

- **BUD-ENROLL** (a relative enrolls a computer from the kit unaided in ≤ 20 min; proposed, owner to confirm). This kit records the prototype enrollment time as an **indication only**: the prototype has no install step, no OS warnings and no real network. The real measure is E5-S3.
- The pass rule itself (≥ 4 of 5) is PLAN's criterion for this spike, not a budget. No new threshold is introduced here.

## Equipment

| Item | Exact model or version | Why | Have it? |
|---|---|---|---|
| A laptop the relative has not used before, or their own computer | Any current Chrome, Edge, Firefox or Safari. Record the browser and OS. | Runs the prototype. Using the relative's own computer is more realistic; either is fine, but record which. | |
| External mouse | — | Many older users struggle with trackpads. Offer it; record whether it was used. | |
| USB stick with the `prototype/` folder | exFAT, any size | Mimics the kit: the relative opens `index.html` from the stick. Run it from the stick, not from a download. | |
| Printed **practice card** | See `session-sheet.md` §0 | Carries the synthetic code `K7QM-4TXD-9HRP` and a practice name and email, so no real data is typed | |
| Printed `session-sheet.md` | One copy per relative | Script, timings, rubric, SEQ and SUS | |
| Stopwatch | Phone | Task times | |
| Optional: screen recording of the prototype window only | OBS or the OS recorder | Helps the RITE fix. Only with explicit consent (H3 §9), and no camera or audio unless separately agreed | |

**Software and files needed:** `prototype/index.html` (this folder, one self-contained file, no network, no storage), `session-sheet.md`.

## Before you start

- [ ] Consent recorded (H3 §9 consent script plus `kits/E1-S3/consent-addendum.md`). Mention that this is a test of the app, not of them.
- [ ] Open `prototype/index.html` from the stick once yourself. Press **F2** (or Ctrl+Shift+F) to show the facilitator panel, click **Reset to start**, and press F2 again to hide it. Check it is on the "Welcome" screen.
- [ ] Put the practice card face down next to the laptop.
- [ ] Check the task order for this participant (counterbalancing table below) and write it on the sheet.
- [ ] Run one **dry run with the helper persona** before the counted sessions (E1 treats the first visit as a protocol pilot). The dry run does not count towards the 5.

### Counterbalancing with E3-S1 (anti-pre-training rule)

E3-S1 shows three alternative health screens and asks the same kind of question ("are last month's photos safe?"). Whichever test comes second is primed by the first. So the order alternates, and the results are reported by order.

| Participant | First | Second |
|---|---|---|
| P1, P3, P5 | E2-S1 (this kit) | E3-S1 |
| P2, P4 | E3-S1 | E2-S1 (this kit) |

- If more than 5 take part, continue alternating.
- **Analysis rule:** report the E2-S1 pass count for each order. If the overall pass depends on participants who did E3-S1 first (for example, all failures are in the E2-first group), record the result as **"Fail (primed)"** and apply the RITE rule.
- This rule replaces the order "E3-S1, then E2-S1" proposed in the E2 note's test-plan skeleton. The analyst asked the spike runner to define the counterbalancing.
- The prototype's health wording is a placeholder. If E3's copy deck exists before the visits, replace the wording in `renderHealth()` with E3's front-runner, and note the version on each sheet.

## Procedure

Do the steps in order. After each step, write down what you saw on the session sheet, even if it looks unimportant. If something unexpected happens, stop, note it, and carry on only if the relative is comfortable.

1. Read the **introduction** in `session-sheet.md` §1 aloud, word for word. **You should see:** the relative nods or asks a question; answer only with the scripted replies.
2. Plug in the stick and open `index.html` in the browser yourself, so the "Welcome" screen is showing. Start the stopwatch when you hand over the mouse. **You should see:** "Welcome" and a **Get started** button.
3. Hand over the practice card and read **Task 1** (§2) aloud. **You should see:** the relative works through code, name and email, the "Looking for your keepsakes" screen, the proposal, and the "Do you use any of these?" screen. Say nothing. If asked "what do I do?", say only "Please do what you would do if you were at home on your own." That is not an assist.
4. Record every **assist** (definition in §2). An assist means the task is not unaided, but let them finish so the later questions can still be asked.
5. When "You're all set" appears, stop the stopwatch for the enrollment time. Let them click **Show me how things are**. **You should see:** the health view, scenario 1 ("Most of your keepsakes are stored at home. Some are still on their way.").
6. Ask **Q1** and **Q2** (§3) exactly as written. Write their answer in their words, but leave out names and places. Press F2 and click **Mark "participant answered"** after each answer, then F2 again to hide the panel.
7. Say "Now imagine it is the next day." Press F2, click **Health: scenario 2 (all stored)**, press F2 to hide the panel, and ask **Q3**. **You should see:** "Everything on this computer is stored at home."
8. Hand over the **SEQ** for each task and then the **SUS** (§4). They fill them in themselves. Help only by reading the items aloud if they ask.
9. Ask the two debrief questions (§5). Note any word that confused them.
10. Copy the facilitator panel's timing log onto the sheet (it holds only screen names and seconds). Click **Reset to start** before the next participant, or close the browser tab.

**Stop and record "No result" for that participant if:** the relative becomes uncomfortable or tired, the laptop fails, or the facilitator has to take over the mouse for more than a moment. Never push to finish.

### RITE rule (only if a counted participant fails)

- Right after the session, decide with the analyst notes whether the failure has an obvious cause in one screen or one phrase. If so, change `prototype/index.html` before the next session. Note the change and the participant after which it was made in `results.md` ("v2 after P2: 'stored at home' replaced by …").
- The pass criterion is judged on participants who used the **final** version: ≥ 4 of 5 on it. A family of this size may not supply 5 new people after a change. If it does not, report "No result (n < 5 on final version)", with the counts.
- Never re-test the same relative on the judgement questions: they already know the answers.

## Cleaning up

1. Close the browser tab. The prototype saves nothing, so nothing is left on the laptop.
2. If you recorded the screen, keep the file in the private store only. Delete it once the RITE fixes and the results are written.
3. File the paper sheets in the private store (H3 R7). Type only the aggregate results into `results.md`.

## Data handling

H3 defines the classes, rules and output check in `docs/research/h3-research-data-governance.md` (§2–§4; a draft until the owner confirms it, OD-21). This kit applies at least the plan's rules (PLAN H3):

- Only **counts, times and scores** leave the private store. Never names, email addresses, pictures of the relative, or quotes that identify them or their places.
- Participants are coded P1…Pn on the sheets. The key linking codes to people stays in the private store.
- The prototype data is synthetic (SYN). The practice card means no real code, name or email is typed. If a relative types their own name anyway, it stays in the browser tab only, and closing the tab erases it.
- `results.md` holds aggregates only and passes the H3 §4 output check before it enters the repo.

## Results

Copy this section into `docs/research/kits/E2-S1/results.md` and fill it in. Do not edit numbers afterwards; add a note instead.

- **Run by / dates / places:** <...>
- **Prototype version(s) used:** v1 (this commit) | v2 after P… (describe each change)
- **Hardware and browsers actually used:** <laptop models, OS, browser, relative's own or not, mouse yes/no>
- **Emulator or VM used instead of real hardware?** No | Yes: <what, and why>
- **Dry run with the helper done?** Yes/No; changes made after it: <...>

Per participant (codes only):

| Participant | Order (E2 first / E3 first) | Prototype version | Enrollment time (mm:ss) | Assists (count) | Q1 | Q2 | Q3 | Unaided pass? | SEQ task 1 | SEQ task 2 | SUS score |
|---|---|---|---|---|---|---|---|---|---|---|---|
| P1 | | | | | ✓/✗ | ✓/✗ | ✓/✗ | Y/N | | | |

| Pass criterion | Budget ID | Measured value | Pass / Fail / No result |
|---|---|---|---|
| ≥ 4 of 5 relatives complete "enroll and tell me if your photos are safe" unaided (on the final prototype version) | — (PLAN E2-S1 rule) | <n of N> | |
| Prototype enrollment time, indication only (no install step) | BUD-ENROLL (≤ 20 min, proposed) | <median, max> | Indicative only |

- **Pass count by order:** E2 first <n of N>; E3 first <n of N>.
- **Overall:** Pass | Fail | Fail (primed) | No result
- **Surprises and points of confusion:** <words or screens that confused people, counted, not quoted by name>
- **Follow-ups for the workstream:** <for E3 copy deck, E5 kit spec, ADR-0004>
