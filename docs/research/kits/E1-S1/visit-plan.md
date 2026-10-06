# E1 schedule and visit running order

This is E1's **input to E2**, not the plan. E2 owns the consolidated family test plan and will
fold this proposed running order into it together with the other FM tests; where E2's plan
differs, E2's plan wins. The weeks are counted from "go", as in the E1
note §7 and H5 (L26, L27). Nothing here has been scheduled with the family yet.

## Schedule

| When | Step | Who | Kit | Output |
|---|---|---|---|---|
| Wave 0 (now) | Answer the intake questions: F1–F11 (people, devices, iPhone-share guess Q-F3, facilitator Q-F9), G1–G6 (archives), J5. Confirm OD-21 (H3 rules) and the consent script (H3 §9 plus `E1-S3/consent-addendum.md`). Create the private store (H3 R7). | Owner | — | Inputs; consent approved |
| Week 1 | **E1-S2a** remote quick count: one call per library owner. Part 0 first (check the Settings wording on the owner's phones). | Owner | `E1-S2/` | Share range → OD-01, decision sitting 2 |
| Week 1 | Ask relatives for visit slots in weeks 3–7 (H5 L26). Name a facilitator candidate (H5 L27). | Owner | — | Bookings |
| Weeks 1–2 | **E1-S1 Part A** (placeholders on test accounts) and **Part B** (dry run on the owner's own devices). Build the Windows and macOS binaries. | Owner | `E1-S1/` | Census ready, or fixed in CT |
| Week 2 | Brief the facilitator: interview guide, consent, H3 rules. Hold one practice interview with the owner as the "relative". | Owner + facilitator | `E1-S3/` | Facilitator ready |
| End of week 2 (Wave 1 exit) | Decide OD-01 with the S2a range, or apply the straddle rule | Owner | — | OD-01 outcome |
| Week 3 | First visit: the **helper** persona (a tech-comfortable relative). Doubles as the protocol pilot. Fix the guide afterwards. | Owner | all three | Protocol fixes |
| Weeks 3–7 | Consolidated visits, from typical users to extreme users (E2's order). E1-S3: the facilitator runs 2–3 of them. E1-S2b re-reads at each visit. E1-S1 Part C on 3 computers. | Owner (+ facilitator) | all three | Raw FAM in the private store only |
| Weeks 7–8 | H3 §4 output check. Code the E1-S3 story counts. Anonymised census summary, proto-personas, journeys, ranked needs. | Owner, then agents on AGG only | — | E1 deliverables |

## Running order inside one visit (about 90 minutes; planning estimate, not measured)

The visit is one sitting per relative (PLAN). E1's parts come first because they must not be
primed by the prototype tests.

| Order | Part | Minutes (estimate) | Kit or section |
|---|---|---|---|
| 1 | Welcome. Consent (H3 §9 + addendum). Say what happens today and that they can stop at any time. | 5–10 | `E1-S3/consent-addendum.md` |
| 2 | Interview sections 1–5: devices, where keepsakes live, beliefs, past losses. **Before** any census or prototype, so that answers are not primed. | 25 | `E1-S3/interview-guide.md` |
| 3 | Device walk-through: "show me where your photos are". Check the cloud settings together (belief vs reality). | 10 | Device checklist D11 |
| 4 | Census on their computer (E1-S1 Part C), including the unmentioned-locations look | 15–20 | `E1-S1/README.md` |
| 5 | E1-S2b re-read of the phone's storage screens | 5–10 | `E1-S2/README.md` |
| 6 | Interview sections 6–8: admin access, exclusions, help network, accessibility. The owner leaves the room if a facilitator runs it. | 10–15 | `E1-S3/interview-guide.md` |
| 7 | E2 and E5 observed tasks (installing an app, QR code, typing a code, prototypes), run by their own kits | per E2 | E2 test plan |
| 8 | **Debrief** (interview guide, "Debrief"): what the check showed, any single-copy keepsakes, the E2-S3 stopgap offered or booked. Thanks; what happens next; offer a printed copy of their own census summary. | 5–10 | `E1-S3/interview-guide.md` |

**Break rule:** offer a break after part 3, and stop at any sign of fatigue.

**Length cap (proposal, unmeasured):** about 90 minutes of E1 parts plus E2/E5 tasks may come to
2–3 hours, which is likely too long for older relatives. Proposed cap: about 60–75 minutes per
sitting, checked at the week-3 pilot visit (record the real duration). When a visit must be split:

- **Sitting 1:** parts 1–6 (all of E1). These must come before any prototype, so they stay
  together.
- **Sitting 2:** part 7 (E2/E5 observed tasks), then the debrief (part 8). Nothing in E1 primes
  these tasks beyond what the interview already does, but E2 decides whether a gap of days
  matters for its tests.

Fallback for relatives who cannot be visited (H5 L26): a video-call interview and a relative
running the census from a printed guide.

## What the owner brings

- USB stick with the census builds and an empty `census-output` folder.
- Printed consent sheet, interview guide, device checklist (several device pages) and the E1-S2
  reading sheet.
- Stopwatch (phone).
- Nothing to install on phones. No iOS or Android census app exists; see the E1 note §2.2.
