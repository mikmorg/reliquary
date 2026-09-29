# <ID>. <Workstream title>

<!--
Research-note template (owner: H1). Copy to docs/research/<id>-<slug>.md, for example a1-content-identity.md.
Keep it short and plain. Use tables where they help. Delete these comments and any section that is truly empty
(write "None" rather than deleting Open questions or Decision requests).
Never invent a measurement: "no result" is a valid result. No family data: sizes, types and counts only (H3).
-->

- **Workstream:** <ID> (see `docs/research/PLAN.md`, section "<ID>.")
- **Status:** Draft | Under skeptic review | Final
- **Date:** YYYY-MM-DD (last updated YYYY-MM-DD)
- **Feeds:** ADR-NNNN (reserved in `docs/adr/README.md`), OD-NN, one-way door #N
- **Depends on:** <workstreams, T1/T2 items, spikes>
- **Traceability rows closed or advanced:** R-NN, Q1-N (see `docs/research/traceability.md`)

## Summary

<Three to five sentences: the answer, the recommendation, and how confident we are. Written for the owner.>

## Questions

<The key questions from PLAN, numbered, each with a one-line answer or "open". Add any new question the research raised.>

| # | Question | Short answer | Confidence |
|---|---|---|---|
| 1 | | | High / Medium / Low |

## Method

- **Sweep:** <which scouts ran: docs, source, issues and forums, pricing/policy/standards>
- **Routes used:** <direct, raw GitHub mirror, Context7, GitHub issue search, WebSearch; see `docs/research/sources.md`>
- **Blocked sources:** <each blocked source, and that it was reported to H1; "None" if none>
- **Stop rule:** <when the sweep stopped, e.g. two consecutive scouts added no new primary source>

## Sources

Every source that supports a claim below. "Primary" means the vendor's or author's own document, spec, code or data. Cite mirrors as `repo @ branch : path`.

| # | Source (title and URL or mirror path) | Publisher | Published or version date | Accessed | Primary? |
|---|---|---|---|---|---|
| S1 | | | | YYYY-MM-DD | Yes / No |

## Claims

Key claims are those that are load-bearing for a decision, time-sensitive, or used as a budget or cost number (PLAN §5.1). A claim is **verified** only if at least one primary source supports it **and** at least 2 of the 3 skeptics fail to refute it. Otherwise mark it **contested** or **secondary only**. Neither can be the sole support for an ADR.

| # | Claim | Sources | Key? | Skeptic 1 (sources) | Skeptic 2 (logic) | Skeptic 3 (adversary/cost/user) | Verdict |
|---|---|---|---|---|---|---|---|
| C1 | | S1 | Yes | Upheld / Refuted: reason | | | Verified / Contested / Secondary only |

## Findings

<Organised by question or theme. Each finding cites claim IDs (C1, C2) and states confidence. Cover what the plan asks for where relevant: methods, alternatives, best practice, similar work, implementation goals, tools and libraries.>

### Alternatives compared

| Option | Fit with settled requirements | Pros | Cons | Evidence |
|---|---|---|---|---|
| | | | | C1 |

### Similar work and lessons

| Project or paper | What they do | Borrow or avoid | Source |
|---|---|---|---|
| | | | S1 |

### Tools and libraries

| Name | Purpose | Licence | Maturity (release date, activity) | Source |
|---|---|---|---|---|
| | | | | |

## Spikes

| Spike | Exec tag | Budget IDs | Data class | Status | Result |
|---|---|---|---|---|---|
| <ID>-S1 | CT / SB / OL / FM / EXT | BUD-... | <H3 class> | Not started / Running / Kit-ready / Pass / Fail / No result | <measured numbers, or link to the kit's results file> |

Say so explicitly if an emulator stood in for real hardware.

## Conflicts with settled text

<Anything that contradicts CLAUDE.md, ADR-0001 or ADR-0002. These are never resolved here: each becomes an OD item plus, where needed, a superseding ADR draft. Write "None" if none.>

## Open questions

<What is still unknown, who will answer it, and by when.>

## Recommendation

<The recommended option and why, in plain words. Say what would change the recommendation.>

## Decision requests

<Each item added to `docs/research/decision-queue.md`, written in its decision-request format. Write "None" if none.>

## Hand-offs

| To | What | Why |
|---|---|---|
| <workstream> | | |
