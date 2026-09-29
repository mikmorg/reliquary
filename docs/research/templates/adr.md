# ADR-NNNN: <Decision title, stated as the choice made>

<!--
ADR template (owner: H1), MADR-style, matching the layout of ADR-0001 and ADR-0002.
Copy to docs/adr/NNNN-<short-slug>.md using the number reserved in docs/adr/README.md.
Agents always write Status: Proposed. Only the owner accepts.
Never edit an Accepted ADR: to change one, write a new ADR with "Supersedes" or "Amends".
Delete these comments before submitting.
-->

- **Status:** Proposed
- **Date:** YYYY-MM-DD
- **Owner workstream:** <ID>
- **Decider:** the owner
- **Gate:** A | B | C | P2 | build | before B-track | before adopting code (as reserved in `docs/adr/README.md`)
- **Supersedes / Amends:** None | ADR-NNNN (§x)
- **Evidence:** `docs/research/<id>-<slug>.md`
- **Traceability:** R-NN, Q1-N, OPEN-N (see `docs/research/traceability.md`)
- **Owner decisions:** OD-NN (see `docs/research/decision-queue.md`)
- **One-way door:** No | Yes, door #N in `docs/research/one-way-doors.md`

## Context and problem statement

<Two to four short paragraphs. What must be decided and why now. Which settled requirements (CLAUDE.md) and Accepted ADRs constrain it, cited by traceability ID.>

## Decision drivers

- <Settled requirement, e.g. R-18 devices can only append>
- <Security requirement from D1, e.g. SR-07>
- <Budget, e.g. BUD-HASH>
- <Owner weights from F1 / OD-02, when available>

## Considered options

1. <Option A>
2. <Option B>
3. <Option C>

## Decision

<The chosen option, stated plainly, and the key "because" in one or two sentences. Then the specifics: tables, formats, limits, names. Normative details that others must implement go in the spec file this ADR owns (e.g. `docs/spec/...`), linked here.>

### Consequences

- **Good:** <...>
- **Bad / accepted trade-offs:** <...>
- **Follow-up work:** <...>

### Confirmation

<How we will know the decision is being followed and still holds: test vectors, a spike, a CI check, a drill. Cite spike IDs and budget IDs.>

## Pros and cons of the options

### <Option A>

- Good, because <...> (claim C#)
- Bad, because <...> (claim C#)

### <Option B>

- Good, because <...>
- Bad, because <...>

## Evidence

<The load-bearing claims this decision rests on, copied from the research note's claims table with their verdicts. Every load-bearing point needs at least one Verified claim. A Contested or Secondary-only claim may appear only beside a Verified one, never as the sole support (PLAN §5.1).>

| Claim | Source (primary) | Verdict |
|---|---|---|
| | | Verified |

## Reversibility

<How hard is this to undo, and when does it become hard (e.g. once real data is hashed, once a kit ships)? For a one-way door, say what must be true before the gate.>

## Alternatives considered

<Options rejected outright, with one line each on why. Matches the "Alternatives considered" section of ADR-0001/0002.>

## Open questions

<What remains open after this decision, with the owning workstream for each.>
