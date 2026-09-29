# Architecture Decision Records

- **Owner:** H1 (research-run governance). Only H1 edits this file; ADR authors report status changes in their hand-off.
- **Last updated:** 2026-09-29
- **Source of the reservations:** `docs/research/PLAN.md` §2.1

This folder holds Reliquary's ADRs: one decision per file, numbered, never rewritten once Accepted. Numbers 0003–0040 are reserved so that parallel workstreams cannot collide. Use `docs/research/templates/adr.md` to start a new one.

## Registry

Status values: **Accepted**, **Proposed** (a draft exists), **Pending** (being written by an in-flight track), **Reserved** (number held, no draft yet), **Rejected**, **Superseded by ADR-NNNN**.

| ADR | Title | Owner | Gate | Status | File |
|---|---|---|---|---|---|
| 0001 | Cloud staging on Cloudflare R2; homelab makes outbound connections only | — | — | **Accepted** (2026-09-29) | [0001-cloud-staging-on-r2.md](0001-cloud-staging-on-r2.md) |
| 0002 | Onboarding via USB stick and one-use printed invite; app distribution | — | — | **Accepted** (2026-09-29) | [0002-onboarding-and-distribution.md](0002-onboarding-and-distribution.md) |
| 0003 | Client technology stack | T1 (in flight) | before B-track | **Pending** (T1; working assumption option C) | — |
| 0004 | v1 scope, platforms (incl. iOS timing), non-goals | E2 (+B4) | A | Reserved | — |
| 0005 | Build, adopt, fork or compose | F1 | A | Reserved | — |
| 0006 | Content identity and dedup ID | A1 | A | Reserved | — |
| 0007 | Object envelope and metadata record | A2 | A | Reserved | — |
| 0008 | Key hierarchy, custody, recovery | D2 | A | Reserved | — |
| 0009 | Ingest protocol, receipts, reconciliation | A3 | A | Reserved | — |
| 0010 | Control-plane topology and API v1 | C1 | B | Reserved | — |
| 0011 | Bundle and manifest; USB transport | A4 | A | Reserved | — |
| 0012 | Homelab at-rest posture and storage engine | A6 | A | Reserved | — |
| 0013 | Catalog database and schema | A6 | B | Reserved | — |
| 0014 | Enrollment, device identity, revocation, abuse limits | D3 (+C2) | C | Reserved | — |
| 0015 | Update trust root, release signing, supply chain | D5 | C | Reserved | — |
| 0016 | Keepsake item model | A5 | A (core) | Reserved | — |
| 0017 | Desktop runtime and resource governance | B1 | C | Reserved | — |
| 0018 | Android background execution and media access | B2 | C | Reserved | — |
| 0019 | Android distribution channel and Play compliance | B3 | C | Reserved | — |
| 0020 | Source layer and change detection | B5 | C | Reserved | — |
| 0021 | Client local state and transfer pipeline | B6 | C | Reserved | — |
| 0022 | Desktop packaging and self-update mechanics | B7 | C | Reserved | — |
| 0023 | Keepsake discovery policy | E4 | C | Reserved | — |
| 0024 | Health model and status vocabulary | E3 | C | Reserved | — |
| 0025 | Nudge policy and notification channels | E3 | C | Reserved | — |
| 0026 | Email provider and sending domain | C3 | C | Reserved | — |
| 0027 | Privacy and data minimisation | D6 | C | Reserved | — |
| 0028 | Restore pipeline v1 | A8 | C | Reserved | — |
| 0029 | Integrity, fixity and preservation policy | A7 | C | Reserved | — |
| 0030 | Homelab hardware, filesystem, power | C5 | C | Reserved | — |
| 0031 | Homelab deployment and IaC | C6 | P2 | Reserved | — |
| 0032 | Admin tooling and disaster recovery | C8 | C | Reserved | — |
| 0033 | Telemetry, crash reporting, alerting | B8 + C7 | C | Reserved | — |
| 0034 | Repository layout, build, CI | G1 | build | Reserved | — |
| 0035 | Test and verification strategy | G2 | build | Reserved | — |
| 0036 | Licence and release process | G3 | before adopting code | Reserved | — |
| 0037 | LAN direct: build or defer | A4 | P2 | Reserved | — |
| 0038 | Onboarding kit and code formats | E5 | C | Reserved | — |
| 0039 | Accessibility and localisation | E6 | C | Reserved | — |
| 0040 | Family roles and life events | E7 | C | Reserved | — |
| 0041+ | Superseding ADRs and anything not listed above | H1 assigns | — | Unallocated | — |

Gate meanings (PLAN §4.2): **A** formats frozen before any real family byte is hashed or encrypted with production keys; **B** walking skeleton passes on real R2; **C** pilot-ready before the first kit reaches a relative.

## Process

### Writing an ADR
1. **Use the reserved number.** File name `docs/adr/NNNN-<short-slug>.md`. If the decision has no reserved number, ask H1 for the next free number from 0041 upwards before writing.
2. **Start from the template** (`docs/research/templates/adr.md`). Set Status to **Proposed**.
3. **Back every load-bearing claim** with the workstream's research note (`docs/research/<id>-<slug>.md`). A claim counts as verified only if at least one primary source supports it and at least 2 of 3 skeptics fail to refute it (PLAN §5.1). Contested or secondary-only claims cannot be an ADR's sole support.
4. **Cite IDs, not prose:** CLAUDE.md requirements (traceability IDs in `docs/research/traceability.md`), security requirements (SR-xx from D1), budget IDs (`docs/research/budgets.md`), and owner decisions (OD-xx in `docs/research/decision-queue.md`).
5. **Consistency review** (one shared reviewer per wave) checks the draft against CLAUDE.md, the Accepted ADRs, the glossary (H4), the ownership table in PLAN §2.1 and the budget IDs.
6. **The owner accepts or rejects.** Agents never mark an ADR Accepted.

### Changing a decision
- **Never edit an Accepted ADR**, not even to fix a typo in its reasoning. A change is a new ADR with Status **Proposed** that says `Supersedes: ADR-NNNN` (whole decision) or `Amends: ADR-NNNN §x` (one section). When the owner accepts it, the old ADR's row here changes to **Superseded by ADR-NNNN** (or gains "amended by"); the old file stays untouched.
- **Settled requirements in CLAUDE.md change only with the owner.** A proposal that would change one goes to the decision queue as an OD item with a superseding-ADR draft attached.
- Known pending conflicts with CLAUDE.md or the Accepted ADRs are tracked as OD-01, OD-03, OD-04, OD-05, OD-09, OD-11, OD-12 and OD-13 in `docs/research/decision-queue.md`.

### After acceptance
- H1 updates this table (status, date, file link).
- If the ADR closes a one-way door, H1 marks it closed in `docs/research/one-way-doors.md`.
- H6 collects outcomes into a proposed update of the "Open decisions" section of CLAUDE.md, which the owner approves.

### Known ownership issue
ADR-0033 has two owners (B8 + C7), which breaks the one-owner rule in PLAN §2.1. The proposed fix is in `docs/research/traceability.md` (§ "Artifacts claimed by more than one workstream").
