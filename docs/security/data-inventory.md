# Personal-data inventory

- **Status:** Draft. **Wave 1 partial:** only the rows OD-03 needs (names, email addresses, activity times, and the email provider). The full per-store inventory is D6 Wave 2.
- **Owner:** D6 (PLAN §2.1; normative artifact of ADR-0027)
- **Date:** 2026-10-06
- **Evidence:** `docs/research/d6-od03-where-email-lives.md` (claim IDs C# below); `docs/adr/0027-privacy-and-data-minimisation.md` (Proposed)
- **Rule:** this file lists kinds of data and where they live. It never contains family data.

## Personal data by store, per OD-03 option

"A" is ADR-0002 as written. "B" is the homelab-only roster proposed in ADR-0027 (path B-R: the device enters the roster, encrypted to the pinned homelab key).

| Store | Data | Under A | Under B | Retention | Evidence / status |
|---|---|---|---|---|---|
| D1 | Person name, email address | Plaintext | **None** | Until deleted, plus a 30-day Time Travel tail (7 days on Free) | C16; C29 (emulated) |
| D1 | Opaque account and device IDs, device public keys, hashes of invite codes and tokens, last-seen and last-commit times (floored to 1 h in D6-S1) | Yes | Yes | Until deleted, plus Time Travel | C29. Pseudonymous: linkable per device over time |
| D1 / R2 inbox | Roster entry in transit (B-R only) | — | age ciphertext to the pinned homelab key; deleted after the homelab acks | Until ack | C29; precondition SR-02 |
| Worker config | Owner's alert address (`destination_address`) | Yes | Yes | Until changed | C12 |
| Email Routing destination list (account-level) | Owner's address; relatives' addresses only under option D | Yes | Yes | Until removed | C10 |
| Email Sending events (`emailSendingAdaptive`, Activity log) | from, to, subject, message ID for every send | Yes | Yes | 31 days | C6, verified |
| Email preview | Full message bodies | Off by rule M2 | Off by rule M2 | About 7 days while on | C7, verified |
| Raw-message API (`GET …/messages/{id}`) | Raw MIME | Unknown with preview off | Unknown with preview off | Undocumented | C25; D6-S1 kit addition |
| Suppression list | Addresses after complaints or hard bounces | Yes | Yes | No expiry for complaints and non-existent mailboxes | C8, verified |
| Email Routing events (`emailRoutingAdaptive`) | from, to, subject of routed mail (for example a `mailto:` unsubscribe) | Only if `mailto:` is used | Only if `mailto:` is used | 31 days | C26; avoid per rule M3 |
| Queues (Email Sending event subscriptions) | `recipient` on each delivery, bounce or complaint event | Not used (rule M4) | Not used (rule M4) | — | C27 |
| Workers Logs | `<Method> <URL>`; bodies and IPs undocumented | Per rules L1–L4 | Per rules L1–L4 | 3 days Free / 7 days Paid | C17; D6-S2 pending (emulated: inconclusive) |
| Cloudflare traffic metadata | IPs, timing, sizes | Yes | Yes | Not localisable below Enterprise | C15; AR-05 |
| Homelab catalog | Name, email, verification and mute state, nudge history, declared devices | — (or a mirror) | Plaintext | Keep-forever policy applies; departures are Wave 2 | F1 |
| Homelab secrets | Email Sending token (wide scope) | — | Yes | Rotated, with a TTL | C25; D2 key inventory |
| Google Play Console | Android users' Google-account emails (closed-track tester list) | Yes | Yes | Until removed | ADR-0002 §4; outside OD-03 |

## Open items (Wave 2)

These rows are still to come:
- device local state and hash cache;
- R2 objects;
- the USB sticks and printed cards;
- device names;
- client telemetry (with B8);
- the restore prefix;
- the catalog's file metadata.

R2 and D1 jurisdiction depend on the owner's answer at H2 intake.
