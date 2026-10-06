# D6. Privacy, consent, family charter and legal: OD-03 (where email lives)

- **Workstream:** D6 (see `docs/research/PLAN.md`, section "D6."). **Wave 1 scope: OD-03 only.** The rest of D6 (full data inventory, consent, charter, departures, side channels, the full legal memo) is Wave 2 and is not covered here.
- **Status:** Draft (analyst deep read, Wave 1 batch W1-c). Skeptic review has not run yet.
- **Date:** 2026-09-29 (last updated 2026-09-29)
- **Feeds:** OD-03; ADR-0027 (privacy and data minimisation); ADR-0026 (C3: email provider and sending domain); ADR-0025 (E3: nudge policy); ADR-0033 (C7: dead-man's switch)
- **Depends on:** ADR-0001 and ADR-0002 (Accepted); T2 (`fact-check-adr-0001-0002.md` item 6); D1 (`d1-threat-model.md`: V20, V21, A11, SR-25, AR-05); C4 (`c4-cost-model.md` C10, C18); H2 (`owner-intake.md` B4, E1, E9, E10, F6); B3 (`b3-android-distribution-play-compliance.md`, admin-created accounts option)
- **Traceability rows closed or advanced:** C-05 (advanced: decision request written), C-04 (advanced: verification design consequence stated), Q2-1 (unblocked once OD-03 is decided), R-44 (advanced: email-provider row of the inventory)

## Summary

Cloudflare's own email service can be driven from outside a Worker: its REST API and SMTP endpoint accept a Cloudflare API token from "any backend" (C2, C3). The homelab, which only makes outbound connections, can therefore keep the family roster (names and email addresses) and send the nudges itself. The cloud database then holds no name or email, and the only cloud-side contact is the owner's address, fixed in the configuration of the dead-man's-switch Worker (C12). **The privacy gain is real but bounded.** While Cloudflare delivers the mail, Cloudflare still holds recipient addresses and subjects in its sending logs (queryable for 31 days), full message copies for about 7 days unless "Email preview" is turned off, and some suppressed addresses with no expiry (C6–C8). What the homelab-only option removes is a durable, queryable roster in D1, stored next to device credentials and activity times, where any Worker bug or leaked D1 token exposes it. Deliverability does not change, because REST, SMTP and Worker sends go through the same Cloudflare pipeline (C4). The costs are design work: the signup verification link and any unsubscribe link cannot point at the homelab, and nudges pause while the homelab is down. **Recommendation: Option B, homelab-only roster; the homelab sends through the chosen provider's API; the cloud keeps only the owner's contact.** It is also the more reversible choice: moving the roster into the cloud later is easy, while removing it later leaves copies in D1 Time Travel for 30 days (C16). Confidence: high on the Cloudflare facts, medium on the design consequences (D6-S1 must confirm them), low on the legal points, because every primary legal source was blocked in this run.

## Questions

| # | Question (OD-03 scope of the PLAN D6 key questions) | Short answer | Confidence |
|---|---|---|---|
| 1 | Can email be held only at the homelab while still using the ADR-0002 provider (Cloudflare Email Service)? | Yes. The REST API (`POST /accounts/{id}/email/sending/send`) and SMTP (`smtp.mx.cloudflare.net:465`, implicit TLS) both work from outside Workers with an API token (C2, C3). No Worker or D1 needs to see an address. | High |
| 2 | What personal data does the email provider keep, whichever option is chosen? | Per-event sending records with sender, recipient, subject and message ID, queryable and retained for 31 days (C6). A full stored copy of each message for about 7 days while "Email preview" is on, which is the default for new sending domains (C7). Suppression entries keyed by address, with no expiry after complaints or non-existent-mailbox bounces (C8). | High |
| 3 | Does where the address is stored change deliverability? | No, not while the same provider sends. SMTP, REST and Worker-binding sends share limits, DKIM/ARC signing and logs (C4), so authentication and IPs are the same (C13). Direct-to-MX delivery from a residential homelab IP is a separate and much worse option (C19, secondary source only). | High (same provider); Medium (direct-to-MX) |
| 4 | What must the cloud still hold? | The owner's contact, for the dead-man's switch that has to work when the homelab is down (PLAN C7). It can be fixed in the Worker's `send_email` binding with `destination_address`, and sends to a verified destination address are free on every plan (C10, C12). The cloud also keeps opaque device IDs and last-seen times, which it needs for auth and rate limiting in any case. | High (mechanism); Medium (design) |
| 5 | What breaks in ADR-0002 §2 if email leaves the cloud? | (a) The signup verification link cannot point at the homelab, which is never exposed; use an in-app code or a Worker endpoint that holds only a token hash. (b) Any unsubscribe or mute link has the same problem. (c) Nudges pause while the homelab is down. (d) The "Consequence" sentence of §2 (name, email and activity timestamps in plain text in the cloud) changes. Each needs the owner to decide (OD-03) and a superseding ADR draft. | Medium (inference; D6-S1 tests it) |
| 6 | Legal: does GDPR's household exemption, or US law, force either option? | Neither option is forced. Conservative default: design as if GDPR applied (data minimisation favours B), treat nudges as non-commercial service messages with a working opt-out, and ask counsel the questions in §Legal. **No primary legal source could be read in this run** (EUR-Lex, legislation.gov.uk, ICO, eCFR, Cornell LII, govinfo, FTC all blocked). | Low |
| 7 | R2 or D1 jurisdiction if relatives live in the EU? | If any family PII stays in D1, the `eu` jurisdiction has to be chosen when the database is created and cannot be changed afterwards (C14). This is a small one-way door that Option B avoids. Cloudflare-side logs and metadata cannot be localised without the Enterprise Data Localization Suite (C15). | High |
| 8 | Is push-only or in-app-only an alternative to email? | Not on its own. The case email exists for is a device that is dead, lost, uninstalled or never opened, and that device cannot nudge anyone. Push also moves tokens to Google/Apple. In-app nudges are complementary, as E2 and ADR-0002 already have it. | Medium |

## Method

- **Sweep:** two scouts (vendor docs; source code and similar work), then this analyst pass. The analyst re-fetched and read in full, from the Cloudflare docs source: Email Service overview, pricing, limits, REST API, SMTP, logs, metrics/analytics (datasets and retention), domain configuration (Email preview), suppressions, send bindings, Workers API (error codes), deliverability, headers (List-Unsubscribe), email-routing destination addresses, Workers Logs, D1 data location, D1 Time Travel, Data Localization Suite, and API token restriction and permission reference pages. Source-level claims were spot-checked for Ente (`email.go`), Immich (email notification docs) and ntfy (privacy policy).
- **Routes used:** `raw.githubusercontent.com/cloudflare/cloudflare-docs/production/src/content/docs/...`, which is the source of developers.cloudflare.com and therefore the same primary, not a stand-in. Also raw GitHub for the similar-work repos, and the repo's own ADRs and notes.
- **Blocked sources** (to be reported to H1; none replaced by a secondary source):
  - GDPR Art. 2(2)(c), Art. 3 and Recital 18 (EUR-Lex; `publications.europa.eu`; `data.europa.eu/eli`), all 403 or EGRESS_BLOCKED. Lindqvist C-101/01 and Ryneš C-212/13 (EUR-Lex, curia). EDPB and the European Commission site.
  - UK GDPR and DPA 2018 (legislation.gov.uk); ICO domestic-purposes guidance.
  - CAN-SPAM 15 USC 7702 and 16 CFR 316 (Cornell LII, govinfo, uscode.house.gov, eCFR); FTC compliance guide; CCPA Civ. Code 1798.140 (leginfo.legislature.ca.gov); COPPA 16 CFR 312.
  - Cloudflare Customer DPA, sub-processor list and privacy policy (www.cloudflare.com).
  - Gmail, Yahoo and Outlook.com sender requirements; Spamhaus PBL.
  - Postmark and Resend retention and DPA pages.
  - WebSearch: the session budget of 200 calls was used up, so no searches ran.
- **Stop rule:** the Cloudflare side was covered with primary sources. The legal side cannot advance without a network route to the primary texts, or copies supplied by the owner.

## Sources

| # | Source | Publisher | Published or version date | Accessed | Primary? |
|---|---|---|---|---|---|
| S1 | Email Service overview: `cloudflare/cloudflare-docs @ production : src/content/docs/email-service/index.mdx` | Cloudflare | undated (production branch) | 2026-09-29 | Yes |
| S2 | Pricing: `… : email-service/platform/pricing.mdx` | Cloudflare | undated | 2026-09-29 | Yes |
| S3 | Limits (incl. Compliance section): `… : email-service/platform/limits.mdx` | Cloudflare | undated | 2026-09-29 | Yes |
| S4 | REST API: `… : email-service/api/send-emails/rest-api.mdx` | Cloudflare | undated | 2026-09-29 | Yes |
| S5 | SMTP: `… : email-service/api/send-emails/smtp.mdx` | Cloudflare | undated | 2026-09-29 | Yes |
| S6 | Email logs: `… : email-service/observability/logs.mdx` | Cloudflare | undated | 2026-09-29 | Yes |
| S7 | Metrics and analytics: `… : email-service/observability/metrics-analytics.mdx` | Cloudflare | undated | 2026-09-29 | Yes |
| S8 | Domain configuration (Email preview): `… : email-service/configuration/domains.mdx` | Cloudflare | undated | 2026-09-29 | Yes |
| S9 | Suppression lists: `… : email-service/concepts/suppressions.mdx` | Cloudflare | undated | 2026-09-29 | Yes |
| S10 | Send bindings: `… : email-service/configuration/send-bindings.mdx` | Cloudflare | undated | 2026-09-29 | Yes |
| S11 | Workers API (error codes): `… : email-service/api/send-emails/workers-api.mdx` | Cloudflare | undated | 2026-09-29 | Yes |
| S12 | Deliverability: `… : email-service/concepts/deliverability.mdx` | Cloudflare | undated | 2026-09-29 | Yes |
| S13 | Postmaster: `… : email-service/reference/postmaster.mdx` | Cloudflare | undated | 2026-09-29 | Yes |
| S14 | Routing rules and destination addresses: `… : email-service/configuration/email-routing-addresses.mdx` | Cloudflare | undated | 2026-09-29 | Yes |
| S15 | Email headers (List-Unsubscribe): `… : email-service/reference/headers.mdx` | Cloudflare | undated | 2026-09-29 | Yes |
| S16 | Workers Logs: `… : workers/observability/logs/workers-logs.mdx` | Cloudflare | undated | 2026-09-29 | Yes |
| S17 | D1 data location: `… : d1/configuration/data-location.mdx` | Cloudflare | undated | 2026-09-29 | Yes |
| S18 | D1 Time Travel: `… : d1/reference/time-travel.mdx` | Cloudflare | undated | 2026-09-29 | Yes |
| S19 | Data Localization Suite: `… : data-localization/index.mdx` | Cloudflare | undated | 2026-09-29 | Yes |
| S20 | R2 data location: `… : r2/reference/data-location.mdx` (read by scout) | Cloudflare | undated | 2026-09-29 | Yes |
| S21 | Restrict tokens (IP filter, TTL): `… : fundamentals/api/how-to/restrict-tokens.mdx` | Cloudflare | undated | 2026-09-29 | Yes |
| S22 | API token permissions reference: `… : fundamentals/api/reference/permissions.mdx` | Cloudflare | undated | 2026-09-29 | Yes |
| S23 | Immich email notifications: `immich-app/immich @ main : docs/docs/administration/email-notification.mdx` | Immich | undated | 2026-09-29 | Yes |
| S24 | Ente museum email utility: `ente-io/ente @ main : server/pkg/utils/email/email.go` | Ente | undated | 2026-09-29 | Yes |
| S25 | ntfy privacy policy: `binwiederhier/ntfy @ main : docs/privacy.md` | ntfy | undated | 2026-09-29 | Yes |
| S26 | docker-mailserver relay hosts: `docker-mailserver/docker-mailserver @ master : docs/content/config/advanced/mail-forwarding/relay-hosts.md` | docker-mailserver | undated | 2026-09-29 | No (not an ISP or blocklist source) |
| S27 | lettre 0.11.23 crate source (`AsyncSmtpTransport::relay()` defaults to 465 with implicit TLS; scout read) | lettre | 0.11.23 | 2026-09-29 | Yes |
| S28 | Healthchecks `hc/api/models.py` (timeout + grace staleness; scout read) | Healthchecks | undated | 2026-09-29 | Yes |
| S29 | ADR-0002 §2 (`docs/adr/0002-onboarding-and-distribution.md`) | Reliquary | 2026-09-29 | 2026-09-29 | Yes |
| S30 | ADR-0001 (`docs/adr/0001-cloud-staging-on-r2.md`): homelab makes outbound connections only | Reliquary | 2026-09-29 | 2026-09-29 | Yes |
| S31 | PLAN D6, C3, C7, §4.3 (`docs/research/PLAN.md`) | Reliquary | 2026-09-29 | 2026-09-29 | Yes |

## Claims

Every Cloudflare claim below was re-read by the analyst in the primary docs source, unless it says otherwise.

| # | Claim | Sources | Key? | Skeptic 1 (sources) | Skeptic 2 (logic) | Skeptic 3 (adversary/cost/user) | Verdict |
|---|---|---|---|---|---|---|---|
| C1 | Email Sending carries a **Beta** badge and needs Workers Paid. Email Routing is on all plans. Arbitrary recipients need Workers Paid (3,000/month included, then $0.35 per 1,000). Sends to verified destination addresses are free on all plans and count toward neither the quota nor the daily limits. | S1, S2, S3 | Yes | | | | Pending |
| C2 | The REST API `POST /accounts/{account_id}/email/sending/send` is usable "from any backend … no Cloudflare Workers binding is required", authenticated with a Cloudflare API token. | S4, S1 | Yes | | | | Pending |
| C3 | SMTP submission is only on `smtp.mx.cloudflare.net:465` with implicit TLS; 587/STARTTLS and port-25 relay are not supported. The username is `api_token` and the password is a token with **Email Sending: Edit**. It needs at least one onboarded domain, and "anyone with it can send email from any onboarded domain on the matching account". | S5 | Yes | | | | Pending |
| C4 | SMTP, REST and Worker-binding sends enter "the same delivery pipeline": the same limits, the same DKIM and ARC signing, the same delivery logs. | S5, S3 | Yes | | | | Pending |
| C5 | Before a sending domain is onboarded, mail can go only to verified destination addresses; after onboarding, to any recipient. New accounts start with a "conservative daily quota" that rises automatically; the number is not published. | S3 | Yes | | | | Pending |
| C6 | The `emailSendingAdaptive` GraphQL dataset holds per-event `from`, `to`, `subject`, `messageId`, `sessionId`, `errorDetail`. "Metrics can be queried (and are retained) for the past 31 days." The dashboard Activity log shows the same per-event data. | S7, S6 | Yes | | | | Pending |
| C7 | "Email preview" stores sent messages (HTML, text, headers, attachments, raw RFC 5322) for about seven days. It is on automatically for new sending domains and can be switched off per domain. | S8, S6 | Yes | | | | Pending |
| C8 | Suppression entries keyed by recipient address: spam complaint means no expiry; a hard bounce for a non-existent mailbox or domain, or one that persists, means no expiry; other hard bounces 7 days; soft bounces 24 h by default. Some Cloudflare-managed entries are `read_only` and need Support to remove. | S9, S12 | Yes | | | | Pending |
| C9 | The Limits page's Compliance section names CAN-SPAM, GDPR and CASL and requires "proper unsubscribe mechanisms" and honouring opt-outs "promptly". `List-Unsubscribe` must carry an `https:` and/or `mailto:` URI; one-click (`List-Unsubscribe-Post`) needs an HTTPS URI. | S3, S15 | Yes | | | | Pending |
| C10 | Destination addresses are account-level (shared across domains), at most 200 per account. Verification means Cloudflare emails the address and the recipient clicks "Verify email address". | S14, S3 | Yes | | | | Pending |
| C11 | Per the send-bindings page, a `send_email` binding with **no restriction attribute** "can send to any verified destination address in your account". This reads inconsistently with C5 ("after onboarding … any recipient"). Unresolved; the real sandbox run must test it. | S10, S3 | No | | | | Pending |
| C12 | A binding can be pinned with `destination_address` (one recipient) or `allowed_destination_addresses` (an allowlist). A send outside the allowlist fails with `E_RECIPIENT_NOT_ALLOWED`. | S10, S11 | Yes | | | | Pending |
| C13 | Outbound mail is SPF- and DKIM-authenticated and DMARC-aligned (SPF on the `cf-bounce` subdomain, `include:_spf.mx.cloudflare.net`; DKIM selector `cf-bounce`; sending prefixes 104.30.0.0/19 and 2405:8100:c000::/38). Cloudflare manages IP reputation and complaint feedback, and recommends a separate subdomain per mail type with targets of delivery > 95 %, hard bounces < 2 % and complaints < 0.1 %. | S13, S12 | Yes | | | | Pending |
| C14 | A D1 jurisdiction (`eu`, `fedramp`) "can only be set on database creation and cannot be added or updated". It controls where the database runs and persists; Workers still reach it from anywhere. | S17 | Yes | | | | Pending |
| C15 | Control over where "traffic metadata — logs and analytics that could identify your end users" is kept (Customer Metadata Boundary) is part of the Data Localization Suite, an **Enterprise add-on**. | S19 | Yes | | | | Pending |
| C16 | D1 Time Travel can restore a database to any minute in the last 30 days (Workers Paid; 7 days on Free). Data deleted from D1 therefore stays recoverable for that window. | S18 | Yes | | | | Pending |
| C17 | Workers Logs are on for new Workers. Invocation logs record request and response details, "enriched with information available to Cloudflare"; for the email handler the message is the recipient. They can be disabled with `invocation_logs: false`, sampled with `head_sampling_rate` (default 1), and are kept for at most 7 days. The page does not say whether request bodies or client IPs are included. | S16 | Yes | | | | Pending |
| C18 | API tokens can be restricted by client-IP range and by TTL; by default they never expire and work from any IP. The token-permission reference page (S22) has no row named "Email Sending", although S5 requires "Email Sending: Edit". So whether a token can be scoped to sending only is **not confirmed** from the reference. | S21, S22, S5 | Yes | | | | Pending |
| C19 | A relay (smarthost) is advised when the network provider blocks outbound port 25, and to gain the relay's reputation. | S26 | No | | | | Secondary only |
| C20 | Similar work keeps addresses on the self-hosted server and relays through an operator-configured SMTP: Immich (admin SMTP settings, per-user opt-outs), Ente museum (SMTP config; its "skip" path logs the recipient address at Info level), ntfy.sh (recipient and content pass through Amazon SES). | S23, S24, S25 | No | | | | Pending |
| C21 | **Inference.** Option B changes where the durable roster lives, not whether Cloudflare sees addresses: while Cloudflare delivers, recipient addresses stay in C6/C7/C8. A Cloudflare **account** takeover still reveals about 31 days of recipients and subjects; a **Worker or D1 bug**, or a leaked D1-scoped token, reveals none. | C2, C6–C8 | Yes | | | | Pending |
| C22 | **Inference.** Under Option B, the ADR-0002 verification link and any unsubscribe link cannot resolve at the homelab (ADR-0001: outbound only). Each needs an in-app code, a `mailto:` to an Email Routing address, or a Worker endpoint holding only a token hash. | S29, S30, C9 | Yes | | | | Pending |
| C23 | **Inference.** Starting with B and moving to A later is a data upload. Starting with A and moving to B later leaves the PII recoverable from D1 Time Travel for 30 days (C16), plus in any exports and logs. B is therefore the more reversible starting point. | C16 | Yes | | | | Pending |

## Findings

### F1. The homelab-only variant is feasible with the ADR-0002 provider (C2–C4, C12; high)

The homelab already reaches Cloudflare over outbound HTTPS to pull staged objects (ADR-0001). It can make one more outbound call, to `api.cloudflare.com/.../email/sending/send`, or submit on SMTP 465. lettre's default `relay()` builder already speaks 465 with implicit TLS (S27), should the homelab service be in Rust. No Worker ever handles a family member's address. A split falls out naturally:

| Held where | What | Why |
|---|---|---|
| D1 / Durable Objects | opaque account ID, opaque device IDs, credentials, last-seen time per device (coarse), invite hashes | Auth, rate limiting, revocation; ADR-0001 and ADR-0002 need these anyway |
| Homelab catalog | person name, email, verification state, device labels, the devices a person said they own but has not enrolled, nudge history and mute settings | Needed to write and send nudges; plaintext only at home, like filenames (CLAUDE.md) |
| Worker config (not D1) | the owner's alert address, fixed with `destination_address` on the dead-man's-switch binding | Must work when the homelab is down (C7 cron) |
| Email provider | per-send recipient and subject (31 days), preview copies (off by mandate), suppression entries | Unavoidable while that provider delivers (C6–C8) |

The homelab computes staleness from what it already sees: commits and receipts per device, plus the per-device last-seen times it pulls from the control plane. This is the Healthchecks "timeout + grace" pattern (S28). It then joins those times to the roster locally. The address reaches the homelab without the cloud reading it: at redemption the device encrypts `{name, email}` to the homelab public key (the ADR-0001 metadata pattern) and sends it as an opaque blob. Alternatively, the admin types names and emails when printing invites, which is B3's "admin-created accounts" option; then the address never passes through the cloud at all.

### F2. What Cloudflare holds regardless (C6–C8, C15, C17, C21; high on facts, medium on the framing)

Minimising D1 does not make Cloudflare blind to email while Cloudflare sends the mail:

- **Sending records:** recipient, sender, subject and message ID, 31 days, readable by anyone who holds Analytics Read on the zone (C6).
- **Email preview:** full message bodies for about 7 days, **on by default** (C7). Option B's ADR must require it off. So should Option A's.
- **Suppression list:** the addresses of relatives who marked a nudge as spam, or whose mailbox was deleted, stay with no expiry (C8). The admin should expect to raise a Support ticket to clear `read_only` entries.
- **Logs and metadata:** a family on a self-serve plan cannot localise Cloudflare's logs; that takes the Enterprise DLS (C15). Workers Logs are on by default, and whether they carry request bodies or IPs is undocumented (C17). That is D6-S2's job. Under Option B, no Worker request ever carries a plaintext address, which removes the email part of that risk entirely.

Option C (homelab-only with a non-Cloudflare provider, or the owner's own mailbox over SMTP) would take addresses away from Cloudflare altogether and put them with another processor. Retention at Postmark and Resend could not be checked (blocked). ntfy.sh's policy shows the general rule: any hosted relay sees the address and the content (C20).

### F3. Deliverability does not depend on where the address is stored (C4, C5, C13, C19; high for the same provider)

- Same provider, same pipeline: Options A and B send from the same Cloudflare IPs with the same SPF, DKIM, DMARC and ARC (C4, C13). Inbox placement is a property of the domain and provider, which is C3-S1's measurement, not of OD-03.
- Direct-to-MX delivery from the homelab (its own MTA on a residential IP) is **rejected**. Relay guidance (C19, secondary only) and common experience point the same way. Primary ISP and Spamhaus sources were blocked, so this rests on secondary evidence.
- Ramp-up: a new account's daily quota is "conservative" and unpublished (C5). At family scale (C4 cost note: 25 people × a few nudges per month ≪ 3,000), the only volume risk is a burst of verification mails on kit day. Stagger them.
- Use a dedicated sending subdomain for nudges (C13). DMARC and unsubscribe details belong to C3.
- Beta risk (C1) is the same under A and B. Under B the fallback (owner-intake B4: Resend or Postmark) is a homelab configuration change; under A it is a Worker redeploy. Neither needs a client update.

### F4. What Option B costs (C18, C22; medium, D6-S1 to confirm)

1. **Verification (ADR-0002 §2).** "A confirmation link is sent" cannot land on the homelab. Two options:
   - (a) The homelab emails a short code; the person types it into the app; the app sends it encrypted to the homelab key through the normal channel; the homelab checks it. The Worker learns nothing, and link scanners cannot consume it (a C3-S2 concern).
   - (b) A link to a Worker endpoint that stores only a hash of the token (GET shows a page, POST confirms, as in C3). The homelab polls it.

   (a) is the more minimal; (b) is the more familiar.
2. **Unsubscribe and mute.** The provider asks for an unsubscribe mechanism (C9). Use `List-Unsubscribe: <mailto:…>` to an Email Routing address that forwards to the owner, or an HTTPS Worker endpoint holding a token hash, plus an in-app mute. Interacts with E3 and OD-12.
3. **Homelab downtime.** Nudges pause while the homelab is down. That is acceptable only because the cloud-side dead-man's switch pages the owner (C7 in PLAN), and a homelab outage longer than the 24 h D6-S1 criterion is itself an owner incident.
4. **One more homelab secret.** An Email Sending token that can send as any onboarded domain on the account (C3). Mitigations: onboard only the nudge subdomain; restrict the token by IP where the homelab has a stable egress IP; set a TTL with rotation (C18). Whether the token can be limited to sending only is unconfirmed (C18). Hand to D2 and D3 for the key inventory. Keep the address out of homelab logs: Ente's skip path logs recipients (C20).
5. **Build effort.** A small homelab mail job (templating, retries with an idempotency key per C3-S3, suppression handling). The Worker side shrinks by the same amount.

### F5. Legal (low confidence: no primary text was readable in this run)

What follows is the analyst's background understanding, **not verified against primary text in this run**. It must not support an ADR until the primary texts are read or counsel answers.

- **EU/EEA (GDPR).** Art. 2(2)(c) takes processing "by a natural person in the course of a purely personal or household activity" out of scope. As understood here, Recital 18 adds that the Regulation still applies to controllers or processors that provide the means for such processing, i.e. Cloudflare and any email provider. CJEU case law (Lindqvist C-101/01; Ryneš C-212/13) reads the exemption narrowly. A private, non-commercial family backup run by one family member for relatives plausibly fits. Three things would weaken it: relatives in separate households, anything that ties the service to the owner's business, and publication beyond the family.
  - **Conservative default:** act as if GDPR applied. Minimisation (Art. 5(1)(c)) and transparency then favour Option B and a plain notice in the charter.
  - **For counsel:** does the exemption cover an extended family across households and countries? Is the owner then Cloudflare's customer as a private individual?
- **UK.** UK GDPR keeps a domestic or household exemption (the ICO calls it "domestic purposes"). The exact wording as amended was not verified. Same default as the EU.
- **US.** No general federal privacy law covers a private individual running a family service. CAN-SPAM rules "commercial electronic mail messages"; backup-status nudges with no commercial purpose look out of scope, or at most "transactional or relationship" messages (definitions in 15 USC 7702 and 16 CFR 316.3 not verified). CCPA/CPRA applies to for-profit "businesses" above thresholds, which a family is not (not verified). COPPA is aimed at commercial operators.
  - **Conservative default:** collect no email for under-13s; nudges about a child's device go to a parent.
- **Provider terms apply in every option.** Cloudflare's Compliance section requires unsubscribe and prompt opt-out handling (C9), so an opt-out path is needed under A or B. Whether Cloudflare's self-serve terms fit a private family service could not be read (www.cloudflare.com blocked).
- **Outside OD-03 but in the inventory:** the Play closed track needs each Android user's Google-account email in Play Console (ADR-0002 §4; T2 item 7). Google holds those addresses whatever OD-03 decides.

### Alternatives compared

| Option | Fit with settled requirements | Pros | Cons | Evidence |
|---|---|---|---|---|
| **A. Cloud roster (ADR-0002 as written):** D1 holds name, email and activity times; a Worker sends | Fits ADR-0002 exactly | Simplest; the verification link is a Worker route; nudges work while the homelab is down | A durable plaintext roster sits in the only internet-facing component, next to credentials. A Worker bug or leaked D1 token exposes it (D1 threat model V21, AR-05). An EU jurisdiction choice at D1 creation is a one-way door (C14). Removing it later leaves 30 days of Time Travel (C16) | C1, C14, C16 |
| **B. Homelab roster; the homelab sends through Cloudflare Email Service (REST/SMTP); the cloud holds only the owner's contact** (recommended) | Amends ADR-0002 §2 (OD-03). Fits "homelab never exposed" (outbound only) | No name or email in D1 or in Worker traffic. Deliverability unchanged. Provider fallback is a homelab config change. Most reversible | Verification and unsubscribe need redesign (F4). Nudges pause during homelab outages. A new send-token secret at home. Cloudflare still holds 31 days of recipients and subjects (C21) | C2–C4, C6–C8, C12, C21–C23 |
| **C. Homelab roster; the homelab sends through another provider** (Postmark/Resend, or the owner's own mailbox over SMTP) | As B; no AWS (so no SES) | A Cloudflare account takeover reveals no addresses. Mail from the owner's own address may feel familiar to relatives | Adds a processor. Its retention and DPA are unverified (blocked). The owner's personal mailbox mixes project and personal accounts, against intake E9 | C20; lead for C3 |
| **D. Verified-destination roster** (every relative is a Cloudflare destination address; free) | Adds a Cloudflare verification click per relative, against near-zero enrollment | $0 even on Workers Free | Addresses sit in an account-level list (C10). An extra step for each relative. Only useful for the owner | C1, C10 |
| **E. Push or in-app only, no email** | Contradicts ADR-0002 §2 email nudges | No email PII at all | Cannot reach a dead, lost, never-opened or uninstalled device's owner; push tokens go to Google/Apple; relatives without email (F6) are a separate case | Q8 |
| **F. Direct-to-MX from the homelab** (own MTA) | Fits outbound-only | No third party sees mail | Residential IP and port-25 blocks mean poor delivery (secondary evidence); running an MTA adds owner time against BUD-SUPPORT | C19 |

### Similar work and lessons

| Project | What they do | Borrow or avoid | Source |
|---|---|---|---|
| Immich | The server holds user emails and sends through admin-configured SMTP (Gmail/M365 guides); per-user opt-out per event | Borrow per-person opt-out and admin-held addresses | S23 |
| Ente museum | SMTP-only sender; logs the recipient address at Info when SMTP is unset | Avoid: never log addresses (D6-S2, B8) | S24 |
| ntfy.sh | Email relay through Amazon SES; addresses kept until removed; anonymous email disabled because of abuse | Lesson: any relay sees the address and content; authenticate senders | S25 |
| Healthchecks | Staleness from the last ping (timeout + grace); SMTP relay on 587 | Borrow the staleness model for the homelab job | S28 |

## Spikes

The spike runner is working these in parallel. This section is a placeholder; results and kit links will be filled in by that stage.

| Spike | Hypothesis | Pass → / fail → (decision) | Exec tag | Budget IDs | Data class | Status | Result |
|---|---|---|---|---|---|---|---|
| D6-S1 Minimal-PII variant | The homelab can compute staleness from receipts and last-seen, and send through REST/SMTP, with D1 holding no name or email | Pass → Option B for OD-03 / ADR-0027; fail → Option A with EU jurisdiction and preview off | SB (emulated variant, if any, is not real Cloudflare) | BUD-TTS (24 h staleness to nudge), BUD-SUPPORT | SYN → results | (spike runner) | (spike runner) |
| D6-S2 Worker log audit | A Worker configuration with no personal data in logs is achievable | Pass → ADR-0027 log settings; fail → invocation logs off plus custom structured logs only | SB | BUD-TEL | SYN → results | (spike runner) | (spike runner) |
| D6-S3 Privacy comprehension | Out of Wave 1 scope | — | FM | — | — | Not started | — |

Additional checks for the real sandbox run: C11 (the recipient scope of an unrestricted binding after onboarding); C18 (whether a token can be scoped to Email Sending only); whether `emailSendingAdaptive` is readable with an Analytics-Read-only token; and whether Email preview is off by default for a domain onboarded through the API.

## Conflicts with settled text

- **ADR-0002 §2** says "Consequence: name, email and per-device activity timestamps are stored in plain text in the cloud control plane", that the email "confirmation link is sent", and that "email is also used for backup nudges". Option B changes where the first lives and how the second works; the third stays. This is **not resolved here**: it is OD-03, and choosing B needs a superseding ADR draft of §2 (ADR-0027 with ADR-0026).
- **ADR-0002 Open questions** name Cloudflare Email Service "(Workers binding)". B uses the same service through REST or SMTP, so no conflict.
- CLAUDE.md is not contradicted. Option B strengthens "homelab … keeps the plaintext catalog".

## Open questions

| Question | Who | By when |
|---|---|---|
| Primary legal texts: GDPR Art. 2(2)(c), Recital 18, Lindqvist, Ryneš; UK GDPR / ICO; 15 USC 7702, 16 CFR 316.3; Cal. Civ. Code 1798.140; COPPA 16 CFR 312.2 | H1 (network route) or owner-supplied copies; then D6 Wave 2 legal memo | Before ADR-0027 (Gate C) |
| Cloudflare self-serve terms, DPA and Email Service sub-processors: does a private individual fit? | H1 route; D6 | Gate C |
| Can a Cloudflare API token be limited to Email Sending, and to one domain? (C18) | D6-S1 sandbox; D2/D3 key inventory | Wave 2 |
| Do Workers Logs invocation logs include request bodies or client IPs? (C17) | D6-S2 | Wave 2 |
| Retention at Postmark and Resend (Option C and the B4 fallback) | C3 | Gate C |
| Relatives with no email (intake F6): a parent or helper address, or in-app only | E3, E7 | Wave 2 |
| Owner's jurisdiction and relatives' countries (EU/UK/US) | Owner, at the H2 intake | Wave 1 exit |

## Recommendation

**Option B.** The homelab holds names and email addresses and sends nudges itself through Cloudflare Email Service's REST API, with SMTP 465 as an equivalent. D1 and all Worker traffic hold no name or email. The cloud keeps only the owner's alert address, fixed in the dead-man's-switch binding. Required settings under B:

- Email preview **off** on the sending domain.
- Generic subjects, and no device names in subjects.
- A dedicated nudge subdomain.
- Invocation logs reviewed per D6-S2.
- A send-only token at the homelab, IP-restricted where possible and rotated.
- Verification by in-app code (preferred) or a token-hash Worker route.
- Unsubscribe through `mailto:` to an Email Routing address, plus an in-app mute.

Why:

- It is the minimisation the PLAN proposes, and it costs nothing in deliverability.
- It avoids a D1 jurisdiction one-way door.
- It is the reversible starting point (C23).
- It fits the existing split: the cloud sees opaque IDs, the homelab holds plaintext.

Be honest with the family charter: Cloudflare still sees who is emailed and when while it delivers the mail.

**What would change this:**

- D6-S1 fails, for example if staleness cannot be computed at home within BUD-TTS. Then choose Option A with EU jurisdiction if relatives are in the EU, preview off, and SR-25 content rules.
- The owner values nudges during homelab outages above minimisation. Then choose A.
- Counsel says Cloudflare holding addresses is itself the problem. Then choose Option C.

## Decision requests

### OD-03: Where family names and email addresses live, and who sends nudges
- **Needed by:** Wave 1 exit (sitting 2)
- **Evidence:** this note; `d1-threat-model.md` (V20, V21, AR-05); `c4-cost-model.md` (C10); D6-S1/S2 results (spike runner)
- **Options:**

  | Option | What it means for the family | Cost (money and owner time) | Reversibility | Risks |
  |---|---|---|---|---|
  | A. Cloud (ADR-0002 as written) | Nothing visible changes; nudges keep coming while the homelab is down | $0 extra; least build | Costly: removing the data later leaves D1 Time Travel copies for 30 days; the D1 jurisdiction is fixed at creation | Roster exposed by any Worker or D1 bug; needs an EU-jurisdiction D1 if relatives are in the EU |
  | B. Homelab only; the homelab sends through Cloudflare Email Service (recommended) | They enter a code from an email in the app instead of clicking a link; nudges pause while the homelab is down (the owner is paged) | $0 extra (same 3,000/month); a small homelab mail job; one more secret to rotate | Easy: the roster can be uploaded to the cloud later | Cloudflare still sees recipients and subjects for 31 days; homelab downtime delays nudges |
  | C. Homelab only; another provider (Postmark/Resend) or the owner's mailbox | As B; mail may come from a familiar address | A provider fee (not checked); another account | Easy | Another processor; its retention not verified |
- **Recommendation:** B. It keeps names and addresses out of the internet-facing component at no deliverability cost, avoids a D1 jurisdiction one-way door, and is the reversible starting point. The cloud keeps only the owner's alert address.
- **Touches settled text:** ADR-0002 §2 (the "Consequence" sentence and the verification link). Choosing B needs a superseding draft of §2, to be written in ADR-0027 with ADR-0026 (C3).
- **If no decision by the deadline:** the run assumes B for design work (C3, E3, C1 API), because it is the reversible option. C3 continues provider evaluation either way. Nothing is built until decided.

## Hand-offs

| To | What | Why |
|---|---|---|
| C3 | Verification by in-app code or token-hash route; `mailto:` unsubscribe through Email Routing; Email preview off; nudge subdomain; C11 test | ADR-0026 depends on OD-03 |
| C7 | Owner alert address fixed with `destination_address`; a free verified destination for the owner | Dead-man's switch needs no roster |
| C1 | API v1 carries the roster only as a blob encrypted to the homelab key; D1 schema without name or email | ADR-0010 |
| D2 / D3 | Add the homelab Email Sending token (scope, IP filter, TTL, rotation) to the key inventory | New secret |
| E3 | Nudges are computed at the homelab; behaviour during an outage; mute and opt-out | ADR-0025 |
| H1 | Blocked legal and Cloudflare-terms sources listed in Method | Run rule: escalate blocked sources |
