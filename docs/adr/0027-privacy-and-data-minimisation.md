# ADR-0027: Privacy and data minimisation. Wave 1 part: where family names and email addresses live, and minimisation rules for email and Worker logs

- **Status:** Proposed. This is a partial draft covering the Wave 1 decisions only. The rest is to be decided in Wave 2; see "Not yet decided".
- **Date:** 2026-10-06
- **Owner workstream:** D6
- **Decider:** the owner
- **Gate:** C
- **Supersedes / Amends:** None directly.
  - Decision 1 depends on **OD-03**. If the owner chooses Option B, the CLAUDE.md "Email" settled requirement must be amended by the owner. ADR-0002 §2 (the Consequence sentence and "a confirmation link is sent") must be amended by a superseding draft owned by **D1** (PLAN D1 "Owns"), with D6 and C3 contributing.
  - This ADR does not amend either of them.
- **Evidence:** `docs/research/d6-od03-where-email-lives.md` (Wave 1 final). Spikes `spikes/D6-S1/` and `spikes/D6-S2/` (emulated, not real Cloudflare). Kits `docs/research/kits/D6-S1/` and `docs/research/kits/D6-S2/`. Inventory `docs/security/data-inventory.md` (Wave 1 partial draft).
- **Traceability:** C-05, C-04, R-44, Q2-1 (see `docs/research/traceability.md`)
- **Owner decisions:** OD-03; also touches OD-17 (AR-05) and OD-12 (in-app mute)
- **One-way door:** No. The D1 jurisdiction attribute is fixed per database. Changing it means creating a new database and migrating to it, which is a cost but not a one-way door (note C14).

## Context and problem statement

CLAUDE.md and ADR-0002 §2 put each person's name, email address and device activity times in plain text in the cloud control plane. The reason given is that the cloud needs them to send verification and nudge emails. The cloud control plane (Workers, D1) is the only internet-facing component, and the project treats it as under attack (R-12, ADR-0001). PLAN D6 asks whether email could live only at the homelab, which already keeps the plaintext catalog, with the homelab sending the nudges itself.

Wave 1 research found four things:
- **Feasibility.** Cloudflare Email Service, the provider ADR-0002 names, can be driven from any backend over REST, or over SMTP (beta). So the outbound-only homelab can send (C2, C3).
- **Deliverability.** It does not depend on where the address is stored (C4).
- **Cloudflare keeps data under any option.** Recipients and subjects for 31 days, suppressions with no expiry, and so on (C6–C8, C26, C27). Moving the roster therefore narrows the exposure; it does not remove it.
- **The B design changes.** Verification, opt-out and failure monitoring all have to change under the homelab-only option (C22, F4).

The choice between options touches settled text, so this ADR **proposes** an option and records the minimisation rules that hold under every option. The owner decides OD-03.

## Decision drivers

- **Settled:**
  - R-12: the homelab is never exposed and makes outbound connections only.
  - R-44: the cloud never sees plaintext content, plaintext hashes or filenames.
  - R-13: no AWS.
  - The CLAUDE.md "Email" bullet and ADR-0002 §2 (these constrain Option A; Option B changes them).
- **Security requirements (D1):**
  - SR-02: pinned trust bundle.
  - SR-25: nudge content rules.
  - SR-26: cloud metadata minimisation.
  - AR-05: accepted metadata risk.
- **Budgets:**
  - BUD-ENROLL: unaided kit enrollment in ≤ 20 min. Verification must not break it.
  - BUD-SUPPORT: ≤ 2 h per month of owner time.
  - BUD-TEL: context for log settings only.
- **Provider terms:** Cloudflare's Compliance section asks for unsubscribe mechanisms under applicable anti-spam law (C9, verified).
- **Not a driver:** legal claims. C24 is contested because every primary legal text was blocked.

## Considered options

For decision 1 (where the roster lives):

1. **A.** Cloud roster, as ADR-0002 is written.
2. **A′.** Cloud roster, with name and email encrypted at rest under a key held as a Worker secret.
3. **B.** The homelab holds the roster and sends through Cloudflare Email Service (REST, or SMTP in beta). The cloud holds only the owner's alert address. There are two sub-paths:
   - **B-R:** the device enters the details, encrypted to the pinned homelab key;
   - **B-A:** the admin enters the details at the homelab.
4. **C.** The homelab holds the roster and sends through another provider (Postmark/Resend) or the owner's mailbox.
5. **G.** Owner-mediated nudges: the homelab alerts only the owner.

## Decision

### Decision 1 (proposed; owner decides under OD-03): Option B, path B-R, conditional on the real-sandbox D6-S1 run

The homelab keeps each person's name, email address, verification state, mute state and nudge history. It sends nudges and verification mail through Cloudflare Email Service's REST API. A device-entered roster entry crosses the cloud only as age ciphertext, encrypted to the homelab key **pinned per SR-02**. The Worker rejects anything else (C29, emulated).

D1 and Worker code hold no name or email. Cloudflare-side, the only contact data is the owner's alert address, pinned with `destination_address` on the dead-man's-switch binding (C12), and the account-level destination list (C10).

**Because:** it is feasible with the ADR-0002 provider (C2, C3, verified), and it costs nothing in deliverability (C4, verified). It also leaves no readable roster in any store the control plane controls. That protects against D1 bugs, D1 exports, Time Travel, leaked D1-scoped tokens and Worker logic bugs (C21, secondary only; C29, emulated).

**Honest limit:** Cloudflare still sees at least 31 days of recipients and subjects under every option (C6). At family scale this probably covers most of the roster.

**Conditions:**
- (a) The real-sandbox D6-S1 run passes, including the added checks listed in the note's Spikes section.
- (b) C3 and E5 show that a B-compatible verification flow meets BUD-ENROLL.
- (c) The owner accepts the settled-text change.

If (a) or (b) fails, fall back to **A′**.

**Until the owner decides:** the build follows the settled text (Option A) and keeps B buildable (decision 3).

### Decision 2 (in scope now, holds under every option): minimisation rules for email

| # | Rule | Evidence |
|---|---|---|
| M1 | Nudge subjects and bodies are generic. They contain no device names, no file details, and no links or requests to act outside the app (SR-25). Any code or link in verification mail awaits D1's ruling on an SR-25 carve-out. | C6 (subjects are logged for 31 days); SR-25 |
| M2 | Email preview is **off** on every sending domain before the first real send. Content minimisation (M1) is the primary control, because preview can be switched back on by anyone with account access. | C7 |
| M3 | Unsubscribes and mutes are recorded in the roster holder's own mute list (the homelab under B), never as Cloudflare manual suppressions. An in-app mute or an HTTPS opt-out is preferred to `mailto:` through Email Routing. | C8, C9, C26 |
| M4 | Bounce and complaint state is learned by polling the suppression API. Email Sending events are not subscribed to Queues. | C27 |
| M5 | One recipient per send call. A suppression rejection becomes an "unreachable" state for the owner, not a retry loop. Addresses are never written to any log (homelab, Worker or client). | C8, C20 |
| M6 | The sending token is the narrowest available, restricted to the sender's IP where stable, has a TTL, is rotated, and triggers an alert before it expires. It is listed in D2's key inventory. A send-only token is probably not achievable (C25). | C18, C25 |
| M7 | Under B, the homelab sends the Worker an address-free mail-health heartbeat (last successful send time, failure count). The dead-man's switch pages the owner when the heartbeat is stale. | F4.4; C7 hand-off |

### Decision 3 (in scope now): keep the roster location reversible

- Whatever OD-03 decides, name and email live in a store separable from credentials and activity: a separate table or database under A, the homelab catalog under B.
- The C1 API accepts a roster entry only as an opaque blob encrypted to the pinned homelab key, or as an admin-entered record.
- C3 designs verification so that it works by code or by link.

Under this rule, moving between A, A′ and B needs no client change.

### Decision 4 (in scope now, provisional until the D6-S2 real run): Worker logging

- **L1.** No personal data or secrets in URLs, including query strings. The fetch invocation message is `<Method> <URL>` (C17).
- **L2.** Never log request bodies. Log opaque IDs and outcomes as structured JSON.
- **L3.** Catch exceptions and replace their messages before they reach logs.
- **L4.** The observability setting (`invocation_logs: false`, or `observability.enabled: false`, for Workers handling person or device traffic) is chosen from the D6-S2 kit results.

  Until those results exist: `invocation_logs: false`, no traces.

  The D6-S2 emulated run was inconclusive. L1–L3 rest on the documented message format and on local positive controls only.

### Consequences

- **Good:**
  - Under B, the internet-facing component holds no readable roster.
  - Under every option, the email footprint at Cloudflare is reduced to what delivery needs (M1–M5).
  - The roster location stays a reversible choice (decision 3).
- **Bad / accepted trade-offs:**
  - Under B:
    - nudges pause during homelab outages, and the owner is paged;
    - the verification email waits for the homelab (kit-day dependency);
    - the homelab gains a wide-scope secret (C25).
  - Under every option, Cloudflare keeps recipients and subjects for 31 days and some suppressions indefinitely. This goes to OD-17 as an AR-05 extension.
- **Follow-up work:**
  - D1: the superseding draft of ADR-0002 §2, and an SR-25 carve-out.
  - C3: the verification design and opt-out mechanism (ADR-0026).
  - C7: the heartbeat (ADR-0033).
  - C1: the API roster blob (ADR-0010).
  - D2/D3: the token (ADR-0008, ADR-0014).
  - E3: mute and outage behaviour (ADR-0025).
  - E5/E2: kit-day usability.
  - H2: relatives' countries and the EU-residency wish.

### Confirmation

- **D6-S1 real-sandbox kit** (`docs/research/kits/D6-S1/`). Pass when:
  - the D1 export holds 0 roster markers;
  - while the homelab is up, nudges arrive within the PLAN's 24 h. That figure is not a BUD ID; H1 has been asked whether it should become one.
  - the dead-man's switch reaches only the owner.

  It also covers the added checks listed in the note's Spikes section.
- **D6-S2 real-sandbox kit** (`docs/research/kits/D6-S2/`). It selects the L4 setting, and L1–L3 are confirmed against hosted Workers Logs.
- **CI checks (G2):**
  - no D1 migration adds a name or email column outside the separable store;
  - grep tests show no address-shaped strings in log statements.
- **Before the first real send:** check that preview is off on the sending domain.

## Pros and cons of the options

### A. Cloud roster
- Good, because it is the simplest, keeps a click-to-verify link, and keeps nudging during homelab outages.
- Bad, because a readable roster sits next to credentials in the only internet-facing component (D1 V21, AR-05), plus a Time Travel tail (C16).

### A′. Cloud roster, encrypted at rest
- Good, because it protects against D1 dumps, exports, Time Travel and D1-scoped token leaks, and keeps the A user experience. It arguably fits the settled text; the owner should confirm.
- Bad, because it does not protect against Worker logic bugs, Worker compromise or account takeover (note F2).

### B. Homelab roster, sent through Cloudflare
- Good, because there is no readable roster in any cloud store (C29, emulated), deliverability is unchanged (C4), and the design is a superset of A (C23, tie-breaker).
- Bad, because:
  - it changes settled text;
  - verification depends on the homelab;
  - it can fail silently without M7;
  - the token scope is wide (C25);
  - Cloudflare still sees at least 31 days of recipients (C6, C21).

### C. Homelab roster, another provider
- Good, because a Cloudflare account takeover reveals no relative addresses.
- Bad, because it adds a processor whose retention and DPA could not be verified (blocked).

### G. Owner-mediated nudges
- Good, because almost no relative PII reaches the provider.
- Bad, because it contradicts ADR-0002 email nudges and spends owner time against BUD-SUPPORT.

## Evidence

| Claim | Source (primary) | Verdict |
|---|---|---|
| C2: REST send works from any backend with an API token | `email-service/api/send-emails/rest-api.mdx` | Verified |
| C3: SMTP 465, `api_token`, Email Sending: Edit; the token can send from any onboarded domain | `email-service/api/send-emails/smtp.mdx`; changelog 2026-06-08 (beta) | Verified |
| C4: one delivery pipeline for REST, SMTP and binding | `smtp.mdx`, `platform/limits.mdx` | Verified |
| C6: per-event from/to/subject, 31 days | `observability/metrics-analytics.mdx` | Verified |
| C7: preview about 7 days, on by default | `configuration/domains.mdx`, `observability/logs.mdx` | Verified |
| C8: suppressions with no expiry; one suppressed recipient fails the whole send | `concepts/suppressions.mdx` | Verified |
| C9: unsubscribe under applicable anti-spam law | `platform/limits.mdx` | Verified |
| C12: `destination_address` pin | `configuration/send-bindings.mdx`, `workers-api.mdx` | Verified |
| C14: D1 jurisdiction set at creation only (`eu`, `fedramp`, `us`) | `d1/configuration/data-location.mdx` | Verified |
| C16: D1 Time Travel, 30 days | `d1/reference/time-travel.mdx` | Verified |
| C18: no Email Sending row in the permission reference; no per-domain scoping | `fundamentals/api/reference/permissions.mdx`, `smtp.mdx` | Verified |
| C21: what B protects against | inference | Secondary only (beside C6, C29) |
| C22: links cannot resolve at the homelab | ADR-0001, ADR-0002 | Secondary only (beside C2) |
| C25: the send scope also onboards subdomains | `cloudflare/api-schemas openapi.json` | Untallied primary (risk caveat only) |
| C29: D1 holds no roster markers; plaintext blob refused | `spikes/D6-S1/` | Emulated, not real Cloudflare |
| C24: legal background | blocked | **Contested**; supports nothing here |

## Reversibility

Decision 1 is reversible in either direction:
- **B to A** is a data upload.
- **A to B** leaves a 30-day Time Travel tail (C16).

Decision 3 is what keeps it cheap. It becomes harder once kits ship with a verification flow that only works one way, which is why C3 must keep verification usable both by code and by link until OD-03 is decided.

The D1 jurisdiction is chosen when the production D1 is created, under every option. A later change is a new database plus a migration.

## Alternatives considered

- **D. Every relative as a Cloudflare verified destination:** rejected as the default. It puts addresses in an account-level list and adds a Cloudflare click for each relative (C10).
- **E. Push or in-app only:** rejected. It cannot reach the owner of a dead or never-opened device. Device notifications first, with email kept for silent devices, is handed to E3.
- **F. Direct-to-MX from the homelab:** rejected. Delivery from a residential IP is poor (secondary evidence only, C19), and running an MTA costs owner time.
- **B with an outage fallback** (the cloud holds addresses encrypted to a key the homelab releases): not evaluated in Wave 1. It gives back part of the minimisation.
- **A dedicated Cloudflare account for email only:** orthogonal to all options. Handed to C3 and D2 as a lead.

## Open questions

- Primary legal texts and counsel questions: the GDPR household exemption, ePrivacy Art. 13, PECR reg. 22, UK DUAA 2025, CAN-SPAM, CCPA, COPPA. D6 Wave 2 legal memo; H1 route.
- Cloudflare self-serve terms, DPA and sub-processors (H1 route; D6).
- Token scope in practice (D6-S1 kit, D2/D3).
- Hosted Workers Logs fields (D6-S2 kit).
- An SR-25 carve-out for verification mail (D1).
- A verification flow that meets BUD-ENROLL (C3, E5, E2).
- Relatives' countries and the EU-residency wish (owner at H2).
- Relatives without email (E3, E7).

## Not yet decided (Wave 2)

The rest of ADR-0027 is to be decided in Wave 2:
- the full data inventory across every store;
- coarse timestamps (the emulated D6-S1 floors to 1 h);
- no plaintext device names;
- R2 jurisdiction;
- side channels (padding, with A2/F3; the within-family dedup oracle);
- consent and the family charter (D6-S3);
- coercive-control safeguards (with OD-12);
- departures, deaths and deletion requests (with E7);
- the legal memo.
