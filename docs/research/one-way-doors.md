# One-way-door register

- **Owner:** H1 keeps the register; the listed workstream closes each door.
- **Last updated:** 2026-09-29
- **Source:** `docs/research/PLAN.md` §4.4 (the reasons come from §3 and the workstream sections)

A one-way door is a choice that becomes very costly or impossible to undo after a certain event, for example once real family data has been hashed, once a kit has been posted, or once an app is on Play. Each door must close at its gate **before** that event. It closes when the owner accepts the ADR that fixes it. H1 then records the date here.

Status values: **Open**, **Proposed** (ADR draft exists), **Closed** (ADR Accepted).

| # | Choice | Owner | Closes at | Fixed by | Why it cannot easily be undone | Status |
|---|---|---|---|---|---|---|
| 1 | Dedup-ID construction and encoding | A1 | Gate A | ADR-0006, `docs/spec/identifiers.md` | Every hashed file, cache entry, R2 key and catalog row carries the ID. Changing it means re-hashing or re-deriving all of them. | Open |
| 2 | Object envelope, post-quantum, sender authentication | A2 | Gate A | ADR-0007, `docs/spec/object-format.md` (OD-06) | Keep-forever data: "the format is permanent". Ciphertext crosses R2 and the post, so harvest-now-decrypt-later applies. | Open |
| 3 | Recovery recipient in the key hierarchy | D2 | Gate A | ADR-0008 (OD-08) | It must exist before the first real ingest, or every file needs rewrapping or re-encryption later. | Open |
| 4 | Homelab at-rest posture | A6 | Gate A | ADR-0012 (OD-07) | It decides whether stored data stays as received ciphertext or is re-encrypted, and whether the private key must be online. Changing it later means migrating the whole store. | Open |
| 5 | Manifest and receipt formats | A4, A3 | Gate A | ADR-0011 + `docs/spec/bundle-format.md`; ADR-0009 + `docs/spec/ingest-protocol.md` | Sticks in the post and receipts held by devices must stay readable. Old devices keep verifying old receipts. | Open |
| 6 | History fields (sightings, provenance) | H4 | Gate A | `docs/design/data-model.md` (with A9 provenance fields) | History "cannot be reconstructed later". Anything not recorded from v0 is lost. | Open |
| 7 | R2 key layout | C1 | Gate B | ADR-0010 | Credential scopes, lifecycle rules per prefix and the append-only guarantee all depend on it. | Open |
| 8 | API hostname on the owner's domain + bootstrap endpoint | C1 | Gate C | ADR-0010 | Clients installed from USB kits keep the hostname they shipped with. The bootstrap endpoint is what lets the API move hosts later. | Open |
| 9 | Update trust root (two embedded keys, manifest format) | D5 | Gate C | ADR-0015 | Keys are embedded in every shipped client. Losing or leaking the update key strands every desktop client. | Open |
| 10 | Pinned homelab key(s) in the first kit | D3 | Gate C | ADR-0014 | Keys printed on cards and baked into kits cannot be recalled once handed out. | Open |
| 11 | Invite-code format printed on cards | E5 | Gate C | ADR-0038 | Printed cards already in relatives' drawers must still redeem. | Open |
| 12 | Android package name, signing key, distribution channel | B3 | First Play upload | ADR-0019 (OD-10) | Moving between channels may require a new package name or signing key (B3 is checking this). | Open |

## Rules

- A gate cannot pass while any door assigned to it is still Open. H6's readiness report for each gate lists them.
- Work that runs before a gate (for example the A0 walking skeleton) uses **v0, version-tagged, throwaway** choices. It must never touch real family data with production keys.
- If research finds a new one-way door, add it here with an owner and a gate, and tell H6.
