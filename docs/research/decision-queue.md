# Owner decision queue

- **Owner:** H1 keeps the queue; the **owner** decides; the listed workstreams supply evidence.
- **Last updated:** 2026-09-29
- **Source:** `docs/research/PLAN.md` §4.3 (OD-01 to OD-20). Items from OD-21 on are added by research notes through H1.

Decisions are batched so the owner can clear them in a few sittings. An item is closed only when the owner's answer is written in the Outcome column, with the date and a link to the ADR or note that records it.

Status values: **Open** (waiting for evidence), **Ready** (decision request written, waiting for the owner), **Decided**, **Deferred to <date>**.

## Queue

"Touches settled text?" marks items where one answer would change CLAUDE.md or an Accepted ADR. That answer needs a superseding ADR draft (see `docs/adr/README.md`).

| ID | Decision | Needed by | Evidence from | Recorded in | Touches settled text? | Status | Outcome |
|---|---|---|---|---|---|---|---|
| OD-01 | iOS in v1 or deferred (reconcile CLAUDE.md with ADR-0002) | Wave 1 | B4, E1-S2 | ADR-0004 (iOS section) | **Yes**: CLAUDE.md platforms vs ADR-0002 §4 | Open | |
| OD-02 | Build, adopt or compose, and the decision weights | Wave 1 | F1 | ADR-0005 | No | Open | |
| OD-03 | Where email lives: cloud (ADR-0002) or homelab only | Wave 1 | D6 | ADR-0027, ADR-0026 | **Yes**: ADR-0002 §2 | Open | |
| OD-04 | Per-upload staging keys, homelab-signed receipts, device-signed manifests (superseding details of ADR-0001) | Wave 1 | D1-S1/S2, C1-S1 | ADR-0009, ADR-0010, ADR-0011 | **Yes**: ADR-0001 §4 | Open | |
| OD-05 | Device approval or co-signing vs "near-zero enrollment" and "never requires the admin" | Wave 2 | D3 | ADR-0014 | **Yes**: CLAUDE.md users; ADR-0002 §3 | Open | |
| OD-06 | Post-quantum recipients from day one | Gate A | A2, F3 | ADR-0007 | No | Open | |
| OD-07 | Homelab at-rest posture | Gate A | A6 | ADR-0012 | No | Open | |
| OD-08 | Recovery recipient, k-of-n and share holders | Gate A | D2, E7 | ADR-0008, ADR-0040 | No | Open | |
| OD-09 | Signing spend (Windows and/or Apple Developer ID) | Gate C | B7-S1/S2, T1 spike 1 | ADR-0022, ADR-0015 | **Yes**: ADR-0002 §5 | Open | |
| OD-10 | Android channel (closed track vs limited distribution); personal vs organisation account | Wave 1 | B3 (H5 §6 F1, F3) | ADR-0019 | Possibly: ADR-0002 §4 prefers the closed track. H5 found that "limited distribution" installs from outside Play, close to the sideloading ADR-0002 rejected, so choosing it touches settled text. The personal vs organisation half can be answered at the intake (Q-E6). | Open | |
| OD-11 | Play account deletion vs keep-forever | Wave 1 | B3-S2 | ADR-0019 | **Yes**: CLAUDE.md retention | Open | |
| OD-12 | User pause/exclude controls vs "users never touch configuration" | Wave 2 | D6, E3 | ADR-0027, ADR-0024 | **Yes**: CLAUDE.md users | Open | |
| OD-13 | Any admin web page or read-only gallery vs "no admin dashboard in v1" | Wave 2 | C8 | ADR-0032 | **Yes**: CLAUDE.md v1 features | Open | |
| OD-14 | Cost ceilings and policy on beta features | **Wave 0** | H2, C4 | `budgets.md` (BUD-CLOUD, BUD-ABUSE); beta policy in ADR-0010 | No | **Open: needs the H2 intake now** | |
| OD-15 | Public or private repo; licence | Before adopting code | G3 | ADR-0036 | No | Open | |
| OD-16 | NDSA target level; derivative preservation copies | Wave 2 | A7 | ADR-0029 | No | Open | |
| OD-17 | Accepted-risk register (admin reads everything, single admin, no off-site copy, single-copy window) | Gate A / C | D1 | `docs/security/threat-model.md` | No; it records risks the settled text already accepts | Open | |
| OD-18 | "Safe to delete" in v1 or not | Gate C | E3 | ADR-0024, ADR-0025 | No | Open | |
| OD-19 | Documents on Android in v1 (SAF vs all-files access vs media only) | Wave 1 | E2, B3 | ADR-0004, ADR-0018, ADR-0019 | No (scope within "files on the device") | Open | |
| OD-20 | Per-person storage budgets and categories that need approval | Wave 2 | C4 | C4 fair-share proposal | Possibly: CLAUDE.md keep-forever | Open | |
| OD-21 | Confirm the research-data rules: data classes, rules R1–R12 and the output check, including exact sizes counting as family data (R3), 90-day deletion of raw outputs (R7), and no committed third-party binaries until ADR-0036 (R9). Added by the Wave 0 checker from H3's owner actions 1–2. | **Wave 0** (before any `FAM → AGG` spike) | H3 | `h3-research-data-governance.md` | No; it tightens the plan's H3 rules | **Open: needs the H2 intake now** (Q-J6) | |
| OD-22 | Add a one-way "Reliquary" drop folder (plus "Send to Reliquary" menus) as a v1 source alongside auto-discovery; two-way sync rejected for v1 | Wave 2 | E4, B5, E3 | `ux-drop-folder.md` | No; it adds a source within "files on the device" | **Decided 2026-10-06** (direction) | Yes: one-way drop folder. Details designed in Wave 2. |

## Suggested sittings

Derived from the "Needed by" column and the Wave 1 exit criterion in PLAN §4.1.

| Sitting | When | Items |
|---|---|---|
| 1 | Wave 0, during the H2 intake | OD-14, OD-21, plus confirming the values in `budgets.md` and the personal vs organisation half of OD-10 |
| 2 | Wave 1 exit | OD-01, OD-02, OD-03, OD-04, OD-10, OD-11, OD-19 (the Wave 1 exit criterion says "decided or scheduled") |
| 3 | Wave 2 | OD-05, OD-12, OD-13, OD-16, OD-20; OD-15 if F1 recommends adopting code |
| 4 | Gate A | OD-06, OD-07, OD-08, OD-17 (Gate A risks) |
| 5 | Gate C | OD-09, OD-18, OD-17 (remaining risks) |

## Decision-request format

Each item moves from Open to Ready when its evidence workstream adds a request in this shape, either below or as a section of its research note linked from the table. Keep it to one page.

```markdown
### OD-NN: <decision in one line>
- **Needed by:** <wave or gate, and the date if known>
- **Evidence:** <research note and ADR draft links>
- **Options:**
  | Option | What it means for the family | Cost (money and owner time) | Reversibility | Risks |
  |---|---|---|---|---|
  | A | | | one-way door / costly / easy | |
  | B | | | | |
- **Recommendation:** <option, with the reason in two or three sentences>
- **Touches settled text:** <none, or the CLAUDE.md line or ADR section, with the superseding draft linked>
- **If no decision by the deadline:** <the default the run will assume, and what that blocks>
```
