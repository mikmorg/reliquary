# Reliquary research phase

- **Owner:** H1 (research-run setup and governance)
- **Last updated:** 2026-09-29
- **State:** Wave 0 (foundations). The plan is a draft for owner review, and nothing beyond Wave 0 runs until the owner says "go".

This folder holds the research that turns the settled requirements in `CLAUDE.md` and the Accepted ADRs into a verified prototype and a complete set of decisions. Every workstream ends in a decision (an ADR, a spec, a runbook or an owner decision request) or an explicit accepted risk.

## Start here

| If you want to… | Read |
|---|---|
| Understand the whole plan | [PLAN.md](PLAN.md): workstreams (§2), checklist (§3), waves and gates (§4), how agents run (§5), definition of done (§6) |
| Answer the owner intake (about 1 hour) | [owner-intake.md](owner-intake.md) |
| See what the owner must decide | [decision-queue.md](decision-queue.md) |
| See which choices cannot be undone, and when they close | [one-way-doors.md](one-way-doors.md) |
| Check a threshold before writing a pass criterion | [budgets.md](budgets.md) |
| Use the agreed terms and data model | [../design/glossary.md](../design/glossary.md), [../design/data-model.md](../design/data-model.md) |
| Handle test data or family data | [h3-research-data-governance.md](h3-research-data-governance.md) |
| Check that every requirement has an owner | [traceability.md](traceability.md) |
| Find out whether a source can be reached from the container | [sources.md](sources.md) |
| Find or reserve an ADR number | [../adr/README.md](../adr/README.md) |
| Write something new | [templates/](templates/): [research note](templates/research-note.md), [ADR](templates/adr.md), [spike kit](templates/spike-kit/README.md) |

## Inputs already in hand

| Track | File | Status |
|---|---|---|
| T1 Client technology stack (→ ADR-0003) | [client-stack.md](client-stack.md) | In flight. Working assumption: option C (Rust core + UniFFI, Kotlin/Compose Android, Tauri 2 desktop + Rust daemon). |
| T2 Fact-check of ADR-0001/0002 | [fact-check-adr-0001-0002.md](fact-check-adr-0001-0002.md) | In flight. All pricing and limit facts come from T2. |
| Accepted decisions | [ADR-0001](../adr/0001-cloud-staging-on-r2.md), [ADR-0002](../adr/0002-onboarding-and-distribution.md) | Accepted 2026-09-29. Never edited; changes need a superseding ADR. |

## Where things go

| Artifact | Location |
|---|---|
| Research note per workstream | `docs/research/<id>-<slug>.md` (e.g. `a1-content-identity.md`) |
| Kit for an owner-lab, family or external spike | `docs/research/kits/<spike-id>/` (README from the template, scripts, `results.md`) |
| Throwaway spike code | `spikes/<id>/`. Throwaway by default. Licence header per ADR-0036 once decided (OD-15); until then mark files "throwaway research code". |
| ADRs | `docs/adr/NNNN-<slug>.md`, with the number reserved in the registry |
| Normative specs and test vectors | `docs/spec/` (identifiers, object format, ingest protocol, bundle format) |
| Design documents | `docs/design/` (glossary, data model, API v1, observability, architecture overview) |
| Security documents | `docs/security/` (threat model, data inventory, assurance plan) |
| Runbooks | `docs/runbooks/` |

## Conventions (summary of PLAN §2.0 and §5)

**Priorities:** P0 is on the critical path, or a one-way door that must close before Gate A (a few Gate C doors are also P0 and flagged). P1 blocks the family pilot (Gate C). P2 comes after the pilot.

**Execution tags:** `[CT]` cloud container; `[SB]` sandbox Cloudflare account and throwaway domain, never production; `[OL]` owner-lab hardware, where agents deliver a kit; `[FM]` family participants, with consent; `[EXT]` external calendar wait; `(build)` needs real code, after research.

**Gates:** **A** formats frozen before any real family byte is hashed or encrypted with production keys. **B** walking skeleton passes on real R2. **C** pilot-ready before the first kit reaches a relative.

**Evidence:** every source is logged with URL (or mirror path), access date and primary/secondary. A key claim is **verified** only with a primary source and at least 2 of 3 skeptics failing to refute it. Otherwise it is **contested** or **secondary only**, and cannot be an ADR's sole support.

**Run rules:**
- "No result" is a valid result. Measurements are never invented.
- Blocked sources are reported to H1 ([sources.md](sources.md)), not quietly replaced.
- Never edit Accepted ADRs, `CLAUDE.md` or `.claude/` settings. Proposals go to the decision queue.
- No production credentials. Use the sandbox account only.
- No family data in the repo, logs or CI. Agents see sizes, types and counts only (H3).
- Never substitute an emulator for real hardware without saying so.
- The Wave 0 pilot (H1-S2) must pass before Wave 1 fans out.

## Workstream index

Wave numbers from PLAN §4.1. The ADR column lists reserved numbers from PLAN §2.1.

| ID | Workstream | Priority | Wave | ADRs |
|---|---|---|---|---|
| A0 | Walking skeleton on provisional choices | P0 | 1 (build) → 2 (runs) | none (feeds 0009, 0010, 0012) |
| A1 | Content identity and dedup ID | P0 | 1 | 0006 |
| A2 | Object envelope and metadata-record format | P0 envelope / P1 schema | 1 | 0007 |
| A3 | Ingest protocol, receipts, state machine | P0 | 1 | 0009 |
| A4 | Bundle and manifest, USB transport, LAN | P0 manifest / P1 USB / P2 LAN | 2 | 0011, 0037 |
| A5 | Keepsake item model and media semantics | P1 (core feeds Gate A) | 2 | 0016 |
| A6 | Homelab at-rest posture, storage engine, catalog | P0 posture / P1 bake-off | 1 → 2 | 0012, 0013 |
| A7 | Integrity, fixity and preservation | P1 | 2 | 0029 |
| A8 | Restore pipeline v1 | P1 | 2 | 0028 |
| A9 | Admin import of existing archives; seed campaign | P1 | 2 | none |
| B1 | Desktop runtime and resource governance | P1 | 2 | 0017 |
| B2 | Android runtime and media access | P1 | 2 | 0018 |
| B3 | Android distribution and Play compliance | P0 desk checks / P1 | 1 (+ EXT review wait) | 0019 |
| B4 | iOS decision and readiness | P0 decision / P2 build | 0–1 | part of 0004 |
| B5 | Source layer and change detection | P1 | 2 | 0020 |
| B6 | Client engine, local state, transfer, USB writer | P1 | 2 | 0021 |
| B7 | Packaging, install from USB, self-update | P1 (B7-S1 P0) | 1 (kit) → 2 | 0022 |
| B8 | Client diagnostics and crash reporting | P1 | 3 | 0033 (with C7) |
| C1 | Cloudflare control plane and API v1 | P0 | 1 | 0010 |
| C2 | Abuse resistance, quotas, account hardening | P1 | 2 | part of 0014 |
| C3 | Email delivery and owner alert channel | P1 | 2 | 0026 |
| C4 | Cost, capacity and storage-budget model | P1 (v0 in Wave 1) | 1 (v0); v1 after A0 measurements | none |
| C5 | Homelab hardware, filesystem, power | P1 | 2 | 0030 |
| C6 | Homelab deployment, IaC, secrets, upgrades | P2 (P1 minimum README) | 3 | 0031 |
| C7 | Alerting, SLOs, dead-man's switch | P1 | 2 | 0033 (with B8) |
| C8 | Admin tooling, DR, unattended survivability | P1 | 3 | 0032 |
| D1 | Threat model and security requirements | P0 | 1 (tabletops) → 2 | none (threat register) |
| D2 | Key hierarchy, custody, recovery | P0 | 1 | 0008 |
| D3 | Trust anchors, enrollment, credentials, revocation | P1 (Gate C door) | 2 | 0014 |
| D4 | Integrity enforcement and ransomware resistance | P1 | 2 | none (attack suite) |
| D5 | Update trust root and supply chain | P0 design / P1 | 2 | 0015 |
| D6 | Privacy, consent, family charter, legal | P1 (OD-03 in Wave 1) | 1 → 3 | 0027 |
| D7 | Security assurance programme | P2 | 3 | none |
| E1 | Family research and census | P0 (iOS share) | 1 (schedule) → 2 | none |
| E2 | v1 scope, metrics, test plan, pilot, interim protection | P0 | 0 (provisional) → 2 | 0004 |
| E3 | Health model, vocabulary, nudges | P1 | 2 | 0024, 0025 |
| E4 | Keepsake discovery | P1 | 2 | 0023 |
| E5 | Onboarding kit, first run, wizard | P1 | 2 | 0038 |
| E6 | Plain language, accessibility, localisation | P1 | 2 | 0039 |
| E7 | Family roles, life events, legacy | P0 hand-off / P1 | 1 → 3 | 0040 |
| F1 | Build, adopt, fork or compose | P0 | 1 | 0005 |
| F2 | Consumer backup apps: patterns and silent failures | P1 | 2 | none |
| F3 | Security literature on E2EE storage and dedup | P0 | 1 | none (attack matrix) |
| G1 | Repository layout, build, CI | P1 | 3 | 0034 |
| G2 | Test strategy, local emulator, device lab | P1 (emulator P0) | 1 → 3 | 0035 |
| G3 | Licence, versioning, release, docs system | P1 licence / P2 | 3 | 0036 |
| H1 | Research-run setup, governance, templates | P0 | 0 | none (this folder's governance files) |
| H2 | Owner intake and infrastructure baseline | P0 | 0 | none ([owner-intake.md](owner-intake.md); PLAN calls it `h2-owner-intake.md`) |
| H3 | Shared corpus and research-data governance | P0 | 0 → 1 | none ([h3-research-data-governance.md](h3-research-data-governance.md) and [corpus/](corpus/README.md); PLAN calls it `h3-corpus-and-data-governance.md`) |
| H4 | Glossary and canonical data model | P0 | 0 → 2 | none ([glossary.md](../design/glossary.md), [data-model.md](../design/data-model.md)) |
| H5 | Long-lead items and procurement | P0 | 0 (start) | none ([h5-long-lead-items.md](h5-long-lead-items.md); PLAN calls it `h5-long-lead.md`) |
| H6 | Integration synthesis and architecture overview | P0 at each gate | 3 (and each gate) | none (`docs/design/architecture-overview.md`) |

## Wave 0 status (H1)

| Item | Status |
|---|---|
| Templates: research note, ADR, spike kit | Done |
| ADR registry with reservations | Done ([../adr/README.md](../adr/README.md)) |
| Budget sheet, decision queue, one-way doors, traceability | Done. Budget values await the owner (H2). |
| H1-S1 source reachability | **Failed**: 3 of 10 sources not fully reachable; allowlist request raised ([sources.md](sources.md)) |
| Separate spike-report and decision-request templates | Covered for now by the results section of the spike-kit template and the request format in [decision-queue.md](decision-queue.md) |
| Proposed `.claude/agents` definitions and settings diff | Not started. Needs owner approval before anything is applied. |
| H1-S2 pilot run of F3 end to end | Not started. Must pass before Wave 1 fans out. |
| Sandbox Cloudflare account, throwaway domain, nested Proxmox | **Owner action**. Also blocked from the container until `api.cloudflare.com` and related hosts are allowed. |
| H2 owner intake and provisional E2 scope | Questions ready ([owner-intake.md](owner-intake.md), §K is the provisional scope). **Waiting for the owner's answers**; OD-14 and the budget values depend on them. |
| H3 research-data rules and corpus | Draft ([h3-research-data-governance.md](h3-research-data-governance.md), [corpus/](corpus/README.md)). Rules take effect when the owner confirms them (OD-21). H3-S1 not run: the generator does not exist yet (G2). |
| H4 glossary and data model | v0 started ([glossary.md](../design/glossary.md), [data-model.md](../design/data-model.md)); completed in Wave 2. |
| H5 long-lead items | List ready ([h5-long-lead-items.md](h5-long-lead-items.md)); the §2 start list runs on the day the owner says "go". |
| Questions to T1 and T2 (PLAN §1) | **Not yet recorded as sent.** Neither `client-stack.md` nor the fact-check shows them yet. |
