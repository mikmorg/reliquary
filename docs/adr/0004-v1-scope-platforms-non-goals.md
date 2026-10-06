# ADR-0004: v1 scope, platforms (iOS timing) and non-goals: settled platforms with media-only Android and iOS kept deferred, delivered in steps behind a restore gate

- **Status:** Proposed. **PROVISIONAL:** this ADR uses the owner-intake defaults (`docs/research/owner-intake.md` §K and Part 2). The owner intake (H2) and the E1 census have not been answered yet. Any row marked † may change; Appendix B of the evidence note says how.
- **Date:** 2026-10-06
- **Owner workstream:** E2 (+B4)
- **Decider:** the owner
- **Gate:** A
- **Supersedes / Amends:** None. Nothing here changes CLAUDE.md or ADR-0001/0002. The items that would change settled text are kept out of the decision and listed under "Open questions" as decision requests: reopening iOS, importing cloud exports, iPhone bridge wording in the wizard, and a minimal-v1 cut.
- **Evidence:** `docs/research/e2-v1-scope-metrics-pilot.md` (claims K1–K15); `docs/research/b4-ios-decision.md`; `docs/research/f1-build-adopt-fork-compose.md`; `docs/research/b3-android-distribution-play-compliance.md`; spikes `spikes/E2-S2/`, `spikes/E2-S3/`, kit `docs/research/kits/E2-S1/`
- **Traceability:** R-03, R-06, R-33, R-36
- **Owner decisions:** OD-19, OD-01 (B4 owns it; E2 input), OD-13, OD-17, DR-E2-1 to DR-E2-5 (numbers to be assigned by H1)
- **One-way door:** No

## Context and problem statement

CLAUDE.md settles the v1 platforms as Windows, macOS, Linux and Android. iOS is deferred ("revisit with the Apple Developer membership"; commit `6f9f2bb`), and ADR-0002 §4 agrees. The settled v1 also includes:
- discovery, plain-language health and proactive nudges;
- R2 staging plus a required USB transport;
- admin-only restore;
- keep-forever retention.

Some of PLAN, the decision queue and the analyst draft describe a conflict between CLAUDE.md and ADR-0002 over iOS. That premise is stale. There is no conflict to resolve.

Three things remain open: how far v1 can be pruned without changing settled text, in what order it is delivered, and what bar a status must clear before the family is reassured. Two inputs bear on the order. The first is F1's estimate (K11; secondary only, Low confidence): 1,070–2,140 focused hours, which is **2.6–5.1 years at the provisional 8 h/week**. At that rate, owner-run concierge seeding lands at about 12 months, and minimal desktop and Android apps at about 24 months. The second is that mobile background upload is unreliable even in mature apps (K8, Verified). The family needs protection long before the full v1.

The data-integrity requirement is "verifiable and restorable". Similar products count "backed up" as soon as the server has a copy (K7, Verified). A storage-level check does not prove that data can be read back (K9, Verified, used here as an analogy).

## Decision drivers

- Settled: data integrity over everything; restore is first-class (R-36); non-technical users never touch configuration (R-06); phones are first-class; USB transport is required; devices may only append.
- Settled: iOS is deferred, and the client stack must not preclude it (R-03).
- Settled: v1 data sources are files on the device only; cloud sources are on the roadmap (R-33).
- Budgets: BUD-TTS, BUD-ENROLL, BUD-SUPPORT, BUD-RESTORE, BUD-TEL, BUD-REVOKE. BUD-CLOUD and BUD-ABUSE have no value yet. The candidates BUD-COVER, BUD-FALSESAFE and BUD-PILOT-DUR are proposals (K15).
- Owner capacity: Q-B9, unanswered; provisionally 8 h/week (F1).
- Owner decision weights (F1 / OD-02): not yet set.

## Considered options

1. **Settled platforms; Android media only; iOS kept deferred with a computer bridge; delivery in steps D0–D3 behind a per-platform restore gate** (recommended).
2. The same platforms, delivered as the full kit in one release with no concierge step.
3. Concierge only (no apps) as v1.
4. Reopen iOS into v1.
5. A "minimal v1" with named deferrals (the D2 apps declared to be v1).

## Decision

Option 1. It is the thinnest scope that changes no settled text, it starts protection now, and it proves ingest and restore on real data before any app reaches a relative.

1. **Platforms v1:** Windows, macOS, Linux, Android. **iOS stays deferred** (settled text; OD-01 option B). iPhone photos are bridged through a family computer that syncs iCloud originals. The bridge never claims "covered": status says what reached home through the computer, with the date of the newest photo, and nudges keep running. Reopening iOS is an owner decision that changes settled text, and an iPhone share of 40 % or more is only a trigger to ask that question.
2. **Sources v1:** files on the device.
   - Android: **camera roll and media only**† (OD-19 option A, the cheapest default; revisit after the E1 census and B3).
   - Desktop: photos, videos and documents in user folders, plus the macOS Photos library (the iPhone bridge).
   - Importing cloud exports (Takeout, icloudpd) is **not** decided here (DR-E2-5).
3. **Transports v1:** R2 and USB. The owner seeds first; the relatives' return trip arrives in the full kit. LAN direct is deferred (ADR-0037).
4. **Assistant v1:** discovery proposals, plain-language health, and nudges in the app, as OS notifications and by email. **Nudge emails carry facts about device activity only, never content-derived counts** (E2-S2).
5. **Restore gate (enrollment, per platform).**
   - No relative's device on a platform is enrolled, and no relative sees any reassuring status for data that took that path, until that platform has passed two things: Gate B's restore leg, and one sampled restore drill (M7).
   - The concierge path counts as its own platform.
   - Platforms the owner does not own are drilled on the helper's device, with the owner present.
   - **Requirements on ADR-0024 (E3 owns the vocabulary).** A person- or device-level reassuring word needs all of:
     - (a) receipts for all accepted keepsakes, outside a grace window for new items;
     - (b) the platform gate is open;
     - (c) a full permission grant, not a partial one;
     - (d) E3's redundancy and scrub conditions.
6. **Delivery steps†:**
   - **D0:** stopgaps now.
   - **D1:** concierge. The owner seeds by USB with the admin CLI and sends a status report generated only from receipts and the catalog. Gated on Gate A, Gate B including the restore leg, a restore drill of concierge-imported data, and the relatives' consent.
   - **D2:** minimal apps (basic discovery and nudges). Which app comes first is decided in DR-E2-4; desktop first is the provisional default.
   - **D3:** the full ADR-0002 kit, which is v1.
7. **Pilot†:**
   - Stages: P0-C (concierge), then for each app P0 owner → P1 helper → P2 extreme user → P3 everyone. Each stage lasts at least 30 days.
   - Stop actions depend on the cause. Display or vocabulary bugs freeze reassuring wording, and uploads continue. Ingest, receipt or restore failures pause uploads through **Worker-side suspension** (D3, BUD-REVOKE).
   - Nothing is ever deleted. Stopgaps stay on throughout.
   - Stop rules that cite BUD-CLOUD or BUD-ABUSE are inactive until the owner sets those values.
8. **Success metrics:** M1–M10 as defined in evidence note §3. There are no third-party analytics. The false-safe check (M9) compares a digest against the homelab ledger. Coverage (M2) keeps cloud-only and gone-before-safe items in the denominator and reports the permission scope.

**Non-goals for v1:**
- end-user restore (settled);
- browse and share (a later read-only, LAN-only viewer, OD-13);
- an admin dashboard (settled);
- import from cloud services, email or social media (roadmap; DR-E2-5 covers admin-side stopgap imports);
- LAN direct;
- Android documents†;
- iOS (settled deferral);
- widgets and SMS nudges;
- an off-site copy of the homelab (settled).

### Consequences

- **Good:**
  - Protection starts in D0 and D1, years before the full kit.
  - Ingest, USB and restore are proven on real data before any relative uses an app.
  - The restore check sits where relatives cannot misread it, at enrollment, so it does not depend on wording.
  - No settled text changes.
- **Bad / accepted trade-offs:**
  - The full v1 is estimated at 2.6–5.1 years at 8 h/week (K11, estimate), and some devices rely on stopgaps for that long.
  - Stopgaps may need paid cloud storage; who pays is the owner's call (DR-E2-2).
  - Phone-only documents and iPhones with no family computer stay on stopgaps.
  - D1 costs the owner visit time.
- **Follow-up work:**
  - E3: ADR-0024 wording under the requirements in item 5.
  - E5: bridge wording in the wizard, an ADR-0002 §3 question.
  - A3 and B8: the receipt-batch cursor that M9 needs.
  - A8: device-side restore verification.
  - A9-S1: byte identity of stopgap copies.
  - B2 and B5: the permission-scope flag.
  - C4: bandwidth sizing for BUD-COVER.
  - H1: number the decision requests and record the candidate budgets.

### Confirmation

- E2-S1 (FM kit, ≥ 4 of 5 relatives). E5-S3 is the BUD-ENROLL evidence.
- E2-S2 (emulated design check passed; re-run on the A0 harness).
- E2-S3 (stopgap checklist passed; setting wording to be confirmed on a device).
- E3-S4 (no "safe" while the homelab is down).
- Pilot gates in evidence note §4.1.
- M9 = 0 detected false-safes.
- Per-platform restore drills (M7, BUD-RESTORE).

## Pros and cons of the options

### 1. Stepped delivery behind a restore gate (chosen)

- Good, because ingest and restore come first (PLAN §4.5), and large first uploads go by USB or desktop rather than phone background upload (K8, Verified).
- Good, because receipts plus an enrollment-time restore drill raise the bar above "the server has a copy" (K7, K9, Verified).
- Bad, because the full kit is far away (K11, estimate), and the concierge step costs owner visits.

### 2. Full kit in one release

- Good, because there is one release to test.
- Bad, because nothing reaches home until the whole kit exists, an estimated 2.6–5.1 years (K11, estimate).

### 3. Concierge only as v1

- Good, because it is cheapest.
- Bad, because it does not deliver the settled v1 assistant features, so adopting it would change settled text.

### 4. Reopen iOS into v1

- Good, because it covers iPhone-heavy families natively.
- Bad, because it reopens CLAUDE.md "Platforms" and "Code signing" and ADR-0002 §4/§5. It also brings 99 USD/yr, 90-day TestFlight builds, and force-quit cancelling background transfers (K12, Verified).

### 5. Minimal v1 (D2 declared as v1)

- Good, because it matches F1's ~24-month figure.
- Bad, because deferring the wizard or the in-app USB return trip amends ADR-0002. It is kept as the named fallback in DR-E2-1.

## Evidence

| Claim | Source (primary) | Verdict |
|---|---|---|
| K1: On Android 11+, SAF tree grants cannot include Download itself or the storage root | developer.android.com documents-files (updated 2026-10-01) | Verified |
| K2: All-files access is a settings toggle under Play review; backup apps are "likely" permitted | developer.android.com manage-all-files | Verified |
| K3: Other apps' downloads need SAF; MediaStore shows other apps' media only | developer.android.com media | Verified |
| K7: Immich counts "backed up" by checksum presence, with no verification | immich `backup.repository.dart` @ 9b57f13a | Verified |
| K8: Mobile background backup is unreliable; do large first uploads from a desktop | Immich `mobile-backup.md`; Ente FAQ | Verified |
| K9: A structure check is not a data read; random subsets do not guarantee coverage | restic `045_working_with_repos.rst` | Verified |
| K10: Versioned consent; completion counts | Syncthing `contract.go`, docs | Verified |
| K12: iOS background transfer limits and Apple costs | Apple developer pages | Verified |
| K13: Immich is a viewer, not a backup; use `:ro` | Immich docs | Verified |
| K5: Google Photos API sync tools are lossy | gphotos-sync README | Verified |
| K6: icloudpd prerequisites and deleting modes | icloudpd README | Verified |
| K11: Effort and timeline | F1 (analyst estimate) | Secondary only; used for sizing beside PLAN §4.5 and K8, never alone |
| K15: Pilot threshold values | Analyst proposal | Secondary only; the values await the owner |
| K4: Storage saver and Free up space behaviour | support.google.com (blocked) | **Contested**; used only as a precaution beside K5 and the E2-S3 measurement |

## Reversibility

Easy to reverse. No format or key decision is involved. The platform order, the OD-19 choice and the delivery steps can all change until the first kit ships at Gate C. The restore gate and the false-safe rules should not be loosened once relatives are enrolled.

## Alternatives considered

- **Full kit in one release:** rejected. Nothing would be protected for years (K11, estimate).
- **Concierge only:** rejected as the end state, because it misses the settled assistant features. Kept as a pivot.
- **iOS in v1:** not chosen. It reopens settled text, so it is the owner's call (OD-01).
- **Gating only the word "Protected", not enrollment:** rejected. Relatives do not tell "stored at home" from "safe" (skeptic finding; E3-S1 to test).
- **Owner-run restic or Kopia as the end state:** rejected. It does not meet the trust model (encryption to the homelab key, cross-user dedup). Acceptable only as a stopgap pivot (F1).

## Open questions

| Question | Owner | When |
|---|---|---|
| OD-19: Android documents (A media only, B SAF folders, C all-files, D Documents/ plus share sheet, E owner cable copy) | Owner; evidence from E2, B3, E1 | Decision sitting 2 |
| OD-01: confirm the deferral plus bridge; whether to reopen iOS if iPhones hold ≥ 40 % of camera-roll bytes. The OD-01 framing is stale. | Owner; evidence from B4, E1-S2a | Wave 1 exit |
| DR-E2-1: adopt the steps (A), or a minimal v1 (D). Concierge-first changes the Q-H4 default. | Owner | Decision sitting 2 / Gate A |
| DR-E2-2: stopgaps now, and who pays for cloud storage | Owner | Now |
| DR-E2-3: candidate budgets BUD-COVER, BUD-FALSESAFE, BUD-PILOT-DUR | H1, then the owner | Wave 2 |
| DR-E2-4: which D2 app comes first | Owner; evidence from E1, Q-F2, Q-H3 | Gate C planning |
| DR-E2-5: admin-side import of stopgap cloud exports (changes settled text) | Owner; evidence from D6, A9 | Before D1 |
| iPhone bridge wording in the ADR-0002 §3 wizard | E5 (ADR-0038) | Gate C |
| Restore-gate vocabulary | E3 (ADR-0024) | Gate C |
| Byte identity of stopgap copies; Takeout naming | A9-S1 | Wave 2 |
| Rows marked †: final after the intake (H2) and the E1 census | E2 | Wave 2 |
