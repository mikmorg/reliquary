# D6. Privacy, consent, family charter and legal: OD-03 (where email lives)

- **Workstream:** D6 (see `docs/research/PLAN.md`, section "D6."). **Wave 1 scope: OD-03 only.** The rest of D6 is Wave 2 and is not covered here: the full data inventory, consent, the charter, departures, side channels and the full legal memo.
- **Status:** Final for Wave 1. Three skeptics reviewed it (sources, logic, adversary), and the synthesis pass ran on 2026-10-06.
- **Date:** 2026-09-29 (last updated 2026-10-06)
- **Feeds:** OD-03; ADR-0027 (privacy and data minimisation; partial draft `docs/adr/0027-privacy-and-data-minimisation.md`); `docs/security/data-inventory.md` (Wave 1 partial draft); ADR-0026 (C3: email provider and sending domain); ADR-0025 (E3: nudge policy); ADR-0033 (C7: dead-man's switch); OD-17 (AR-05)
- **Depends on:** ADR-0001 and ADR-0002 (Accepted); CLAUDE.md "Email" settled requirement; T2 (`fact-check-adr-0001-0002.md` item 6); D1 (`d1-threat-model.md`: V12, V20, V21, A5, A11, SR-02, SR-25, SR-26, AR-05); C4 (`c4-cost-model.md` K15, K7); H2 (`owner-intake.md` B4, E1, E9, E10, F6); B3 (admin-created accounts option)
- **Traceability rows closed or advanced:** C-05 (advanced: decision request written, and the CLAUDE.md conflict named); C-04 (advanced: verification consequences stated and handed to C3); Q2-1 (unblocked once OD-03 is decided); R-44 (advanced: partial inventory)

## Summary

Cloudflare's email service can be driven from outside a Worker. Its REST API and its SMTP endpoint (beta) accept an API token "from any backend" (C2, C3, verified). The outbound-only homelab can therefore hold the family roster (names and email addresses) and send nudges itself, so that D1 and Worker code never hold a readable roster. Deliverability is the same either way, because REST, SMTP and Worker sends share one pipeline (C4, verified).

**The privacy gain is real but smaller than the first draft said.** While Cloudflare delivers the mail, it keeps a lot whatever OD-03 decides:
- recipients and subjects, queryable for 31 days (C6);
- full message copies for about 7 days unless Email preview is off (C7);
- suppressed addresses with no expiry (C8);
- Email Routing and Queues event records if those paths are used (C26, C27).

At family scale, someone who takes over the Cloudflare account probably sees most of the roster under either option (C21, secondary only). What B removes is a durable, readable roster in D1. That protects against D1 bugs, leaked D1-scoped tokens, D1 exports, Time Travel copies and Worker logic bugs. A cheaper middle option that the draft missed, **A′**, covers part of that: the roster stays in D1, encrypted under a key held as a Worker secret.

**Recommendation: Option B (the homelab holds the roster and sends through Cloudflare Email Service), conditional on the real-sandbox D6-S1 run.** B contradicts settled text: the CLAUDE.md "Email" bullet and ADR-0002 §2. It is therefore the owner's call (OD-03), and **until the owner rules, the run designs to the settled text (Option A), kept B-compatible.** A′ is the runner-up if the owner wants nudges during homelab outages and click-to-verify links.

Confidence is high on the Cloudflare facts, medium on the design consequences (only an emulated run so far), and low on the legal points: every primary legal source was blocked, and the legal claim is contested (C24).

## Questions

| # | Question (OD-03 scope of the PLAN D6 key questions) | Short answer | Confidence |
|---|---|---|---|
| 1 | Can email be held only at the homelab while still using the ADR-0002 provider (Cloudflare Email Service)? | Yes. Use the REST API (`POST /accounts/{id}/email/sending/send`) or SMTP (`smtp.mx.cloudflare.net:465`, implicit TLS, beta since 2026-06-08) from outside Workers with an API token (C2, C3, C28). No Worker or D1 row needs to hold an address. | High |
| 2 | What personal data does the email provider keep, whichever option is chosen? | Several stores (details in F2): sending events, preview copies, suppressions, a raw-message API, account-level destination addresses, Email Routing events for anything routed through Cloudflare, and Queues events if they are consumed (C6–C8, C10, C25–C27). | High |
| 3 | Does where the address is stored change deliverability? | No, not while the same provider sends (C4, C13). Direct-to-MX from a residential homelab IP is a separate, much worse option, and the evidence for that is secondary only (C19). | High (same provider); Medium (direct-to-MX) |
| 4 | What must the cloud still hold? | The owner's alert address, for the dead-man's switch, pinned in Worker config with `destination_address` (C12). Under B, also a mail-health heartbeat with no address in it (F4). And in every option, opaque account and device IDs, credentials, and per-device activity times floored to the hour. These are pseudonymous personal data if GDPR applies (unverified). | High (mechanism); Medium (design) |
| 5 | What breaks in settled text under homelab-only? | The CLAUDE.md "Email" bullet ("Account name, email and device activity times are plaintext in the cloud control plane") and ADR-0002 §2: the Consequence sentence and "a confirmation link is sent". The verification and unsubscribe links cannot land on the never-exposed homelab. Verification on kit day comes to depend on the homelab being up. Nudges pause during homelab outages, and a mail-job failure can be silent unless it is monitored (F4). | Medium |
| 6 | Legal (US; EU/UK GDPR household exemption): does either option become mandatory? | Not established. **Every primary legal text was blocked, and the legal claim is contested (C24).** It supports nothing in this note. The conservative defaults in F5 are design choices that hold whether or not GDPR applies. | Low |
| 7 | R2/D1 jurisdiction if relatives live in the EU? | A D1 jurisdiction (`eu`, `fedramp`, `us`) can be set only when a database is created (C14). Changing it later means creating a new database and migrating, which is a migration cost, not a one-way door. The question exists **under both A and B**, because D1 holds per-device activity data in either. B lowers what an EU jurisdiction would be protecting; it does not remove the choice. Cloudflare-side logs cannot be localised below the Enterprise tier (C15). | High (facts); Medium (framing) |
| 8 | Is push-only or in-app-only an alternative? | Not on its own: it cannot reach the owner of a dead, lost or never-opened device, and push tokens go to Google or Apple. As a first channel, with email kept for silent devices, it shrinks the email footprint (F6). | Medium |

## Method

- **Sweep:** two scouts (vendor docs; source code and similar work), then an analyst deep read, then three skeptics (sources, logic, adversary) and this synthesis. The analyst read in full, from the Cloudflare docs source: the Email Service pages (overview, pricing, limits, REST, SMTP, logs, metrics and analytics, domains, suppressions, send bindings, the Workers API, deliverability, postmaster, routing addresses, headers), Workers Logs, D1 data location, D1 Time Travel, the Data Localization Suite, and the API token restriction and permission pages. At synthesis (2026-10-06) the skeptics' leads were re-read in primary sources:
  - the SMTP changelog;
  - D1 `data-location.mdx`, which lists the `us` jurisdiction;
  - Cloudflare's OpenAPI schema, for the `x-cfPermissionsRequired` scopes on `/email/sending/*`;
  - `metrics-analytics.mdx`, for the `emailRoutingAdaptive` fields;
  - the Queues partial `email-sending-events.mdx`, for the `recipient` field.
- **Routes used:** `raw.githubusercontent.com/cloudflare/cloudflare-docs/production/src/content/...`, which is the source of developers.cloudflare.com and so the same primary, not a stand-in. Also `raw.githubusercontent.com/cloudflare/api-schemas/main/openapi.json`, raw GitHub for the similar-work repos, and the repo's own ADRs and notes.
- **Blocked sources** (to be reported to H1; none was replaced by a secondary source):
  - GDPR Art. 2(2)(c), Art. 3, Recital 18 and Recital 26 (EUR-Lex, `publications.europa.eu`, `data.europa.eu/eli`, gdpr-info.eu). Lindqvist C-101/01, Ryneš C-212/13 and TK C-708/18 (EUR-Lex, curia). EDPB.
  - ePrivacy Directive 2002/58/EC Art. 13 (EUR-Lex).
  - UK GDPR, DPA 2018, PECR 2003 reg. 22 and the Data (Use and Access) Act 2025 amendments (legislation.gov.uk). ICO domestic-purposes guidance.
  - CAN-SPAM 15 USC 7702 and 16 CFR 316 (Cornell LII, govinfo, uscode.house.gov, eCFR). FTC guide. CCPA Civ. Code 1798.140 (leginfo). COPPA 16 CFR 312.
  - Cloudflare Customer DPA, sub-processor list, privacy policy and self-serve terms (www.cloudflare.com).
  - Gmail, Yahoo and Outlook.com sender requirements; Spamhaus PBL.
  - Postmark and Resend retention and DPA pages.
  - The GitHub API listing of the cloudflare-docs changelog folder (403 from this session). Because of it, skeptic 1's reported Email Sending public-beta date of 2026-04-16 could not be located again at synthesis.
  - Skeptics re-probed EUR-Lex, legislation.gov.uk, eCFR, gdpr-info.eu, ICO, curia and LII on 2026-10-06: all were EGRESS_BLOCKED or proxy 403.
- **Stop rule:** the Cloudflare side was covered from primary sources, and the skeptics added no new contradicting primary source. The legal side cannot advance without a network route to the primary texts or copies supplied by the owner.

## Sources

| # | Source | Publisher | Published or version date | Accessed | Primary? |
|---|---|---|---|---|---|
| S1 | Email Service overview: `cloudflare/cloudflare-docs @ production : src/content/docs/email-service/index.mdx` | Cloudflare | undated | 2026-09-29, 2026-10-06 | Yes |
| S2 | Pricing: `… : email-service/platform/pricing.mdx` | Cloudflare | undated | 2026-09-29 | Yes |
| S3 | Limits (incl. Compliance): `… : email-service/platform/limits.mdx` | Cloudflare | undated | 2026-09-29 | Yes |
| S4 | REST API: `… : email-service/api/send-emails/rest-api.mdx` | Cloudflare | undated | 2026-09-29 | Yes |
| S5 | SMTP: `… : email-service/api/send-emails/smtp.mdx` | Cloudflare | undated | 2026-09-29 | Yes |
| S6 | Email logs: `… : email-service/observability/logs.mdx` | Cloudflare | undated | 2026-09-29 | Yes |
| S7 | Metrics and analytics: `… : email-service/observability/metrics-analytics.mdx` | Cloudflare | undated | 2026-09-29, 2026-10-06 | Yes |
| S8 | Domain configuration (Email preview): `… : email-service/configuration/domains.mdx` | Cloudflare | undated | 2026-09-29 | Yes |
| S9 | Suppression lists: `… : email-service/concepts/suppressions.mdx` | Cloudflare | undated | 2026-09-29 | Yes |
| S10 | Send bindings: `… : email-service/configuration/send-bindings.mdx` | Cloudflare | undated | 2026-09-29 | Yes |
| S11 | Workers API (error codes): `… : email-service/api/send-emails/workers-api.mdx` | Cloudflare | undated | 2026-09-29 | Yes |
| S12 | Deliverability: `… : email-service/concepts/deliverability.mdx` | Cloudflare | undated | 2026-09-29 | Yes |
| S13 | Postmaster: `… : email-service/reference/postmaster.mdx` | Cloudflare | undated | 2026-09-29 | Yes |
| S14 | Routing destination addresses: `… : email-service/configuration/email-routing-addresses.mdx` | Cloudflare | undated | 2026-09-29 | Yes |
| S15 | Email headers (List-Unsubscribe): `… : email-service/reference/headers.mdx` | Cloudflare | undated | 2026-09-29 | Yes |
| S16 | Workers Logs: `… : workers/observability/logs/workers-logs.mdx` | Cloudflare | undated | 2026-09-29, 2026-10-06 (D6-S2 kit) | Yes |
| S17 | D1 data location: `… : d1/configuration/data-location.mdx` | Cloudflare | undated | 2026-09-29, 2026-10-06 | Yes |
| S18 | D1 Time Travel: `… : d1/reference/time-travel.mdx` | Cloudflare | undated | 2026-09-29 | Yes |
| S19 | Data Localization Suite: `… : data-localization/index.mdx` | Cloudflare | undated | 2026-09-29 | Yes |
| S20 | R2 data location: `… : r2/reference/data-location.mdx` (scout read) | Cloudflare | undated | 2026-09-29 | Yes |
| S21 | Restrict tokens (IP filter, TTL): `… : fundamentals/api/how-to/restrict-tokens.mdx` | Cloudflare | undated | 2026-09-29 | Yes |
| S22 | API token permissions reference: `… : fundamentals/api/reference/permissions.mdx` | Cloudflare | undated | 2026-09-29 | Yes |
| S23 | Immich email notifications: `immich-app/immich @ main : docs/docs/administration/email-notification.mdx` | Immich | undated | 2026-09-29 | Yes |
| S24 | Ente museum email utility: `ente-io/ente @ main : server/pkg/utils/email/email.go` | Ente | undated | 2026-09-29 | Yes |
| S25 | ntfy privacy policy: `binwiederhier/ntfy @ main : docs/privacy.md` | ntfy | undated | 2026-09-29 | Yes |
| S26 | docker-mailserver relay hosts: `docker-mailserver/docker-mailserver @ master : docs/content/config/advanced/mail-forwarding/relay-hosts.md` | docker-mailserver | undated | 2026-09-29 | No (not an ISP or blocklist source) |
| S27 | lettre 0.11.23 crate source (`AsyncSmtpTransport::relay()`: 465, implicit TLS; scout read) | lettre | 0.11.23 | 2026-09-29 | Yes |
| S28 | Healthchecks `hc/api/models.py` (timeout plus grace; scout read) | Healthchecks | undated | 2026-09-29 | Yes |
| S29 | ADR-0002 §2 | Reliquary | 2026-09-29 | 2026-10-06 | Yes |
| S30 | ADR-0001 (homelab makes outbound connections only) | Reliquary | 2026-09-29 | 2026-10-06 | Yes |
| S31 | PLAN D1, D6, C3, C7, §4.3, §5.4 | Reliquary | 2026-09-29 | 2026-10-06 | Yes |
| S32 | CLAUDE.md, Settled requirements, "Email" bullet | Reliquary | undated | 2026-10-06 | Yes |
| S33 | SMTP changelog: `… : src/content/changelog/email-service/2026-06-08-smtp-submission.mdx` ("Authenticated SMTP submission now available in beta") | Cloudflare | 2026-06-08 | 2026-10-06 | Yes |
| S34 | Cloudflare OpenAPI schema: `cloudflare/api-schemas @ main : openapi.json` (`x-cfPermissionsRequired`, `x-fern-availability`, `x-cfPlanAvailability` on `/accounts/{id}/email/sending/*` and `/zones/{id}/email/sending/*`) | Cloudflare | undated | 2026-10-06 | Yes |
| S35 | Queues event subscriptions, Email Sending events: `… : src/content/partials/queues/event-subscriptions/email-sending-events.mdx` | Cloudflare | undated | 2026-10-06 | Yes |
| S36 | D1 threat model (`docs/research/d1-threat-model.md`): V12, V20, V21, A5, A11, SR-02, SR-25, SR-26, AR-05 | Reliquary (D1) | 2026-09-29 | 2026-10-06 | Yes (project text) |
| S37 | Spike D6-S1, emulated (`spikes/D6-S1/README.md`, `evidence/results.json`) and kit (`docs/research/kits/D6-S1/README.md`) | Reliquary (D6) | 2026-09-29 | 2026-10-06 | Yes (emulated, not real Cloudflare) |
| S38 | Spike D6-S2, emulated (`spikes/D6-S2/README.md`) and kit (`docs/research/kits/D6-S2/README.md`) | Reliquary (D6) | 2026-09-29 / 2026-10-06 | 2026-10-06 | Yes (emulated, not real Cloudflare) |

## Claims

A claim is **verified** only if it has a primary source and at least 2 of the 3 skeptics did not refute it. The verdicts for key claims K1–K14 are the computed claim tally, copied as computed. Claims outside the skeptics' key-claim set are marked **untallied**: they are support or context, never the sole support for the recommendation or the ADR. C25–C29 were added at synthesis from the skeptics' leads, and each was re-read in its primary source on 2026-10-06.

| # | Claim | Sources | Key? (tally ID) | Skeptic 1 (sources) | Skeptic 2 (logic) | Skeptic 3 (adversary) | Verdict |
|---|---|---|---|---|---|---|---|
| C1 | Email Sending carries a **Beta** badge and needs Workers Paid. Email Routing is on all plans. Arbitrary recipients need Workers Paid (3,000/month included, then $0.35 per 1,000). Sends to verified destination addresses are free on all plans. The OpenAPI schema marks `/email/sending/send` as `generally-available` with `free: false`, which conflicts with the docs' Beta badge (C28 dates SMTP beta). | S1, S2, S3, S34 | Context | (beta date lead) | — | — | Untallied (primary) |
| C2 | The REST API `POST /accounts/{account_id}/email/sending/send` is usable "from any backend … no Cloudflare Workers binding is required", with a Bearer API token. | S4, S1 | Yes (K1) | Upheld | Upheld | Upheld | **Verified** |
| C3 | SMTP submission is only on `smtp.mx.cloudflare.net:465` (implicit TLS; 587 and 25 are not supported). The username is `api_token`, with a token holding **Email Sending: Edit**. "Anyone with it can send email from any onboarded domain on the matching account." | S5, S33 | Yes (K1) | Upheld (beta caveat) | Upheld | Upheld | **Verified** |
| C4 | SMTP, REST and Worker-binding sends enter "the same delivery pipeline": the same limits, the same DKIM and ARC signing, the same delivery logs. So where the address is stored does not change deliverability. | S5, S3 | Yes (K2) | Upheld | Upheld (a bounce-feedback path is still needed) | Upheld (does not cover availability) | **Verified** |
| C5 | Before onboarding, mail goes only to verified destination addresses; after onboarding, to any recipient. New accounts start on an unpublished "conservative daily quota". | S3 | Context | — | — | — | Untallied (primary) |
| C6 | `emailSendingAdaptive` holds per-event `from`, `to`, `subject`, `messageId`, `sessionId`, `errorDetail`, "retained for the past 31 days", and is readable with zone-level Analytics Read. The dashboard Activity log filter goes back 30 days. | S7, S6 | Yes (K3) | Upheld (31 days is the analytics product's retention; internal retention is unknown) | Upheld | Upheld | **Verified** |
| C7 | Email preview stores sent messages for "about seven days". It is on automatically for new sending domains and is toggled per domain. The toggle affects only messages sent while it is on. The default for API-onboarded domains is undocumented. | S8, S6 | Yes (K4) | Upheld | Upheld | Upheld (limits noted) | **Verified** |
| C8 | Suppressions keyed by address: complaint, no expiry; a non-existent mailbox or domain, or a persistent recipient-side issue, no expiry; other hard bounces 7 days; soft bounces 24 h. `read_only` entries (Cloudflare-managed, for example the `policy` reason) cannot be changed; "to investigate one, contact Cloudflare Support". Complaint entries that are not `read_only` can be deleted by the account. "Drop suppressed recipients" is off by default, so one suppressed recipient fails the whole REST or SMTP send. | S9, S8, S12 | Yes (K5) | Upheld (read_only wording corrected) | Upheld | Upheld (read_only wording corrected) | **Verified** |
| C9 | The Limits page: "All email sending must follow **applicable** anti-spam laws and regulations", naming CAN-SPAM, GDPR and CASL, and asking for "proper unsubscribe mechanisms" and honouring opt-outs "promptly". This is a developer-docs page, not contract terms. `List-Unsubscribe` takes `https:` and/or `mailto:`; one-click needs HTTPS. | S3, S15 | Yes (K10) | Upheld ("applicable") | Upheld ("applicable") | Upheld | **Verified** |
| C10 | Destination addresses are account-level, at most 200 per account. Verification is a click in a Cloudflare email. | S14, S3 | Context | — | — | — | Untallied (primary) |
| C11 | A `send_email` binding with no restriction attribute "can send to any verified destination address", which reads inconsistently with C5. Unresolved; to be tested in the sandbox. | S10, S3 | No | — | — | — | Untallied (open) |
| C12 | A binding can be pinned with `destination_address` (one recipient) or `allowed_destination_addresses`. `E_RECIPIENT_NOT_ALLOWED` is documented for the allowlist only; the error for a `destination_address` violation is undocumented. The pin limits compromised Worker code, not an account-level attacker, who can redeploy the config. | S10, S11 | Yes (K6) | Upheld | Upheld | Upheld (not a control against account takeover) | **Verified** |
| C13 | Outbound mail is SPF/DKIM/DMARC-aligned from Cloudflare prefixes. Cloudflare manages IP reputation and recommends a subdomain per mail type. | S13, S12 | Context | — | — | — | Untallied (primary) |
| C14 | A D1 jurisdiction (`eu`, `fedramp`, `us`) "can only be set on database creation and cannot be added or updated after the database exists". Workers still reach the database from anywhere. Changing it means a new database plus a migration. | S17 | Yes (K7) | Upheld (`us` added; "one-way door" withdrawn) | Upheld (same) | Upheld (same) | **Verified** |
| C15 | Localising "traffic metadata — logs and analytics that could identify your end users" (Customer Metadata Boundary) needs the Data Localization Suite, an Enterprise add-on. | S19 | Yes (K9) | Upheld | Upheld | Upheld | **Verified** |
| C16 | D1 Time Travel restores to any minute in the last 30 days (Workers Paid; 7 days on Free). Deleted rows stay recoverable for that window, which then expires on its own. | S18 | Yes (K8) | Upheld (weak support for reversibility) | Upheld | Upheld (bounded exposure) | **Verified** |
| C17 | Workers Logs are on for new Workers. The fetch invocation message is `<Method> <URL>`, and for the email handler the message is the recipient. They can be disabled with `invocation_logs: false`. Retention is 3 days on Free and 7 days on Paid. Whether request bodies or client IPs are kept is undocumented, and that is D6-S2's question. | S16, S38 | Context | — | (retention by plan) | — | Untallied (primary) |
| C18 | The token-permission reference has no "Email Sending" row, although SMTP requires "Email Sending: Edit". Per-domain scoping is effectively answered **no**: such a token "can send email from any onboarded domain". Tokens can be IP-filtered and given a TTL. | S22, S5, S21 | Yes (K11) | Upheld (better source: C25) | Upheld | Upheld | **Verified** |
| C19 | A relay (smarthost) is advised when port 25 is blocked, and to gain the relay's reputation. | S26 | No | — | — | — | Secondary only |
| C20 | Immich and Ente keep addresses on the self-hosted server and relay through configured SMTP. Ente's skip path logs the recipient at Info level. ntfy.sh relays through SES. | S23, S24, S25 | No | — | — | — | Untallied (primary) |
| C21 | **Inference.** B protects the roster against D1 bugs, leaked D1-scoped tokens, D1 exports, Time Travel and Worker logic bugs. An account takeover, or any holder of Analytics Read, still sees **at least** 31 days of recipients and subjects, plus the suppression list (no expiry), the owner and destination addresses, and Email Routing events. The attacker can also re-enable preview for future bodies. At family scale this probably covers most of the active roster under either option. A Worker compromise could also read device-entered roster blobs **unless** the homelab key is pinned outside the cloud (SR-02). | S7, S9, S10, S14, S36 | Yes (K13) | Upheld (understated) | Upheld (understated) | **Refuted** (restated here) | **Secondary only** (restated) |
| C22 | **Inference.** Under B the ADR-0002 verification link and any unsubscribe link cannot resolve at the homelab, which is outbound only. Each needs an in-app code, a token-hash Worker route, or `mailto:` through Email Routing. Under B the verification email can only be sent after the homelab has pulled the roster entry. | S29, S30, C9 | Yes (K12) | Upheld | Upheld (homelab-uptime cost) | Upheld (SR-25 conflict) | **Secondary only** |
| C23 | **Inference (restated).** Reversibility differs only slightly. Moving A to B leaves a Time Travel tail that expires after 30 days (C16). Moving B to A is a data upload, and the D1 jurisdiction choice is needed in both directions. The real asymmetry is in design: a client and API built for B (code entry, an encrypted roster blob) still work under A, but not the other way round. | C16, C14 | Tie-breaker only | (weak) | (weak) | (weak) | Untallied inference |
| C24 | **Legal background, unverified.** The GDPR household exemption plausibly covers a private, non-commercial family service but is read narrowly. Recital 18 keeps providers such as Cloudflare in scope. CAN-SPAM and CCPA likely do not reach family backup nudges. | none readable (all blocked) | Yes (K14) | **Refuted** (unconfirmable; ePrivacy Art. 13, PECR reg. 22, UK DUAA 2025, C-708/18 omitted) | **Refuted** (unconfirmable) | **Refuted** (unconfirmable) | **Contested**: supports nothing |
| C25 | In the OpenAPI schema, `POST …/email/sending/send` and `send_raw` need scope `com.cloudflare.api.account.email.sending.create`. The **same** scope covers `POST /zones/{zone}/email/sending/subdomains` (onboarding a sending subdomain) and `POST …/subdomains/{id}/dns`. `update` and `delete` scopes cover PATCH and DELETE of subdomains. `email.sending.read` covers `GET …/email/sending/messages/{message_id}` ("raw RFC 5322 MIME message"). So a token able to send can very probably also onboard sending subdomains. How the dashboard group "Email Sending: Edit" maps onto these scopes is an inference for the sandbox to confirm. | S34 | Added at synthesis | (lead) | — | — | Untallied (primary) |
| C26 | `emailRoutingAdaptive` holds per-event `from`, `to`, `subject`, `messageId`, `sessionId`, `errorDetail`, `ruleMatched` for routed (inbound) mail. A `mailto:` unsubscribe through Email Routing therefore puts the relative's address in Cloudflare analytics. | S7 | Added at synthesis | (lead) | — | (lead) | Untallied (primary) |
| C27 | Email Sending events published to Queues (`message.delivered`, `bounced`, `rejected`, `complained`, …) carry a `recipient` field. A rejection for a suppressed address reads "Recipient is suppressed". | S35 | Added at synthesis | — | (lead) | — | Untallied (primary) |
| C28 | SMTP submission was announced as **beta** on 2026-06-08. | S33 | Added at synthesis | (lead) | — | — | Untallied (primary) |
| C29 | Emulated only: with the roster at the homelab, D1 held 0 of 17 synthetic name and email markers (positive control 17 of 17). The Worker refused a plaintext roster blob. Nudge delay was 0 h of simulated time while the homelab was up and 40 h during a 54 h outage. The dead-man's switch alerted only the owner after 6 h. | S37 | Spike evidence | — | (emulated only) | — | Emulated, not real Cloudflare |

## Findings

### F1. The homelab-only variant is feasible with the ADR-0002 provider (C2–C4, C29; high on feasibility, medium on design)

The homelab already makes outbound HTTPS calls to Cloudflare (ADR-0001). It can make one more, to the REST send endpoint, or submit on SMTP 465 (beta, C28). lettre's default `relay()` already speaks 465 with implicit TLS (S27). The homelab computes staleness from the commits and receipts it receives and from the per-device last-seen times it pulls, following the Healthchecks timeout-plus-grace pattern (S28). It then joins those to the roster locally. D6-S1 exercised this under emulation (C29).

The roster can reach the homelab in two ways. They differ in what they touch:

| Path | How | Precondition | Touches settled text |
|---|---|---|---|
| **B-R** (device-entered) | At redemption the device encrypts `{name, email}` to the homelab public key and sends it as an opaque blob. The Worker accepts only age ciphertext (C29). | **SR-02**: the homelab key is pinned from the kit or QR, never learned from the Worker (D1 V12, A5). Otherwise a compromised Worker serves its own key and reads every roster entry. SR-02 is already P0 for content encryption, so it adds no new dependency, but it is a stated precondition here. | ADR-0002 §2 Consequence sentence; CLAUDE.md "Email" bullet |
| **B-A** (admin-entered) | The admin types names and emails at the homelab when printing invites (B3's "admin-created accounts"). The address never crosses the cloud. | None beyond B | Also the settled onboarding flow: "Redeeming it creates an account with just a name and email" (CLAUDE.md, ADR-0002 §2). Verification semantics and owner time (BUD-SUPPORT) change. |

### F2. What Cloudflare holds regardless of OD-03 (C6–C8, C10, C15, C17, C21, C25–C27; high on facts, medium on framing)

The per-store inventory is in `docs/security/data-inventory.md` (Wave 1 partial draft). In short, while Cloudflare sends the mail it holds the following:

| Store | What | Retention | Avoidable? |
|---|---|---|---|
| Email Sending events (`emailSendingAdaptive`, Activity log) | from, to, subject, message ID | 31 days (C6) | No, while Cloudflare sends |
| Email preview | Full bodies | About 7 days; on by default (C7) | Yes, by switching it off. That is a secondary control: an account-level attacker can switch it back on, and sends made before it was switched off stay stored |
| Raw-message API `GET …/messages/{id}` | Raw MIME, to any `email.sending.read` token (C25) | Undocumented, and unknown with preview off | Test in the sandbox |
| Suppression list (listable by API) | Addresses after complaints and hard bounces | No expiry for some (C8) | Partly. Never add unsubscribes as manual suppressions; keep a mute list with the roster holder |
| Destination addresses | The owner's address (and every relative's under Option D) | Until removed (C10) | No for the owner |
| Email Routing events (`emailRoutingAdaptive`) | Address and subject of any mail routed through Cloudflare, for example a `mailto:` unsubscribe | 31 days (C26) | Yes, if unsubscribe is in-app or HTTPS rather than `mailto:` via Routing |
| Queues event subscriptions | `recipient` on every delivery, bounce or complaint event (C27) | Queue retention (not checked) | Yes, by not subscribing: poll the suppression API from the roster holder instead |
| Workers Logs | `<Method> <URL>`; recipient for email handlers; bodies and IPs undocumented (C17) | 3 days Free / 7 days Paid | Partly, pending D6-S2: no personal data in URLs, no body logging, scrubbed exceptions |
| Cloudflare logs and metadata | Traffic metadata | Not localisable below Enterprise (C15) | No |

**Who B helps against** (C21, secondary only):

| Adversary | A (cloud roster) | A′ (D1 roster encrypted with a Worker secret) | B (homelab roster) |
|---|---|---|---|
| D1 bug, D1 export, leaked D1-scoped token, Time Travel restore | Roster exposed | Protected | Protected |
| Worker logic bug (for example an IDOR) | Exposed | Exposed (the Worker decrypts) | Protected |
| Compromised Worker code | Exposed | Exposed | Protected only if SR-02 holds (B-R), or with B-A |
| Cloudflare account takeover, or any Analytics Read holder | ≥ 31 days of recipients, plus everything | ≥ 31 days of recipients, plus suppressions and destinations; the Worker secret is usable through a redeploy | ≥ 31 days of recipients, plus suppressions and destinations; no full roster with names |
| Malicious provider | Sees everything it delivers | Same | Same |

### F3. Deliverability does not depend on where the address is stored (C4, C5, C13, C19; high for the same provider)

- Options A, A′ and B send from the same Cloudflare IPs with the same SPF, DKIM, DMARC and ARC (C4, C13). Inbox placement depends on the domain and provider (C3-S1), not on OD-03.
- Direct-to-MX from the homelab is **rejected**. The evidence is secondary only (C19); the primary ISP and Spamhaus sources were blocked.
- A new account starts on an unpublished quota (C5), so stagger the verification mails on kit day.
- **Beta.** Email Sending carries a Beta badge (C1), and SMTP has been beta since 2026-06-08 (C28). The OpenAPI schema says `generally-available` (C1); the conflict is unreconciled. The risk is the same under A and B. Keep the owner-intake B4 fallback (Resend or Postmark) as a **tested** configuration. Under B it is a homelab config change; under A, a Worker redeploy.

### F4. What Option B costs (C8, C18, C22, C25, C29; medium)

1. **Settled text.** B contradicts the CLAUDE.md "Email" bullet and ADR-0002 §2 (see Conflicts). The owner must decide it, and acceptance needs a superseding draft, owned by D1 per PLAN D1 "Owns", with D6 and C3 contributing, plus a CLAUDE.md amendment by the owner.
2. **Verification.** Under B the homelab can send the verification email only after it has pulled the roster entry. That is up to one job interval later (1 h in D6-S1), or never while the homelab is down. ADR-0002 starts nudges only after verification, so unverified relatives never get nudges. Both designs need evaluating against **BUD-ENROLL** (≤ 20 min unaided) and the E5 kit-day flow. That evaluation is C3's and E5's, not D6's:
   - (a) The person types an emailed code into the app. Link scanners cannot consume it, and it is phishing-resistant: an attacker's code typed into the genuine app gains nothing. But the person has to switch between email and app and come back later.
   - (b) A link to a Worker route that stores only a token hash. This keeps ADR-0002's click-to-verify flow.
   - Mitigations: a short homelab poll interval during enrollment windows; UX copy for the delay; and, on path B-A, the homelab can send the mail ahead of kit day.
   - The draft's preference for (a) had no usability evidence and is withdrawn. Usability goes to E2 testing.
3. **SR-25 conflict (D1).** SR-25 says nudges "never contain install links, codes, or requests to act outside the app". A verification code or link, and an unsubscribe link, conflict with it under **any** option, including ADR-0002 as written. D1 should decide whether verification mail gets an explicit carve-out (codes typed into the app only) while nudges stay link-free.
4. **Homelab downtime and silent failure.** Nudges pause while the homelab is down. The dead-man's switch pages the owner, but it watches homelab liveness, not mail health. Under B, nudges can stop while the homelab looks healthy, for any of these reasons:
   - the token expired (the recommended TTL);
   - one suppressed recipient failed the whole send (C8);
   - the quota was hit;
   - the beta service had an outage;
   - the IP filter broke after the ISP changed the address.

   **Requirement:** the homelab sends the Worker an address-free mail-health heartbeat (last successful send, failure count), and the dead-man's switch pages the owner when it goes stale, plus an alert before the token expires. Hand to C7.
5. **Token blast radius.** A homelab token that can send very probably also onboards sending subdomains and DNS records (`email.sending.create`, C25). It sends as any onboarded domain (C3), and may read raw messages if `read` is included. A "send-only token" is **probably not achievable**. Use the narrowest token available, restricted by IP and TTL and rotated (C18), and consider a separate Cloudflare account just for email (a lead, not verified). Hand to D2 and D3.
6. **Mail job rules** (D6 privacy requirements; C8, C20, C27):
   - one recipient per send call;
   - map a suppression rejection to an "unreachable" state shown to the owner, with no blind retry loop;
   - never log addresses (the Ente pattern);
   - learn about bounces and complaints by polling the suppression API rather than consuming Queues events;
   - record unsubscribes in the roster holder's mute list, never as Cloudflare manual suppressions.
7. **Build effort.** A small homelab mail job plus the heartbeat. The Worker side shrinks by about as much.

### F5. Legal (low confidence; C24 is contested and supports nothing)

All of the following is the analyst's unverified background. None of it supports the recommendation or the ADR.

- **EU/EEA.** GDPR Art. 2(2)(c) (household exemption), Recital 18 (providers still in scope), Recital 26 (pseudonymous data is personal data), and Lindqvist, Ryneš and TK (C-708/18) on its narrow reading. The rules on unsolicited email are in the **ePrivacy Directive Art. 13**, not the GDPR. EU data residency is not automatically required when relatives are in the EU; transfers are a separate regime.
- **UK.** UK GDPR domestic-purposes exemption; **PECR reg. 22**; the **Data (Use and Access) Act 2025** amendments.
- **US.** CAN-SPAM covers "commercial" mail, and nudges are probably out of scope, or at most transactional. CCPA covers for-profit businesses. COPPA covers commercial operators.
- **Conservative defaults** that do not rely on any of the above:
  - every message has a working opt-out (Cloudflare's own Compliance section, C9, verified);
  - no email is collected for under-13s, and nudges about a child's device go to a parent;
  - the family charter says plainly what Cloudflare sees;
  - send as little personal data to processors as possible.

  The GDPR framing of the last point is "security (Art. 32) and processor-exposure reduction", not Art. 5(1)(c) minimisation, because B collects the same data. That framing is unverified.
- **Counsel questions:**
  - Does the exemption cover an extended family across households and countries?
  - Are ePrivacy Art. 13 and PECR reg. 22 engaged by service nudges to relatives?
  - Is the owner Cloudflare's customer as a private individual, and do the self-serve terms and DPA fit?
  - Is EU residency needed for D1?
- **Outside OD-03:** the Play closed track puts each Android user's Google-account email in Play Console (ADR-0002 §4). Google holds those addresses whatever OD-03 decides.

### F6. Alternatives compared

| Option | Fit with settled requirements | Pros | Cons | Evidence |
|---|---|---|---|---|
| **A. Cloud roster** (ADR-0002 as written): D1 holds name, email and activity times; a Worker sends | Fits exactly | Simplest; click-to-verify link; nudges during homelab outages | A readable roster sits in the only internet-facing component, next to credentials, exposed by any D1 or Worker bug or leaked D1 token (V21, AR-05); Time Travel tail (C16) | C1, C16, C21 |
| **A′. Cloud roster encrypted at rest** (name and email encrypted under a key held as a Worker secret, HMAC lookup; or a separate PII-only D1 bound only to the mailer Worker) | Arguably fits: the control plane still processes plaintext; this is a hardening, and the owner should confirm | Protects against D1 dumps, exports, Time Travel and D1-scoped tokens; keeps link verification and outage nudges | No protection against Worker logic bugs, Worker compromise or account takeover; key management in the Worker | F2 table; missed in draft (logic and adversary skeptics) |
| **B. Homelab roster; the homelab sends via Cloudflare REST/SMTP; the cloud holds only the owner's contact** (recommended) | **Contradicts** the CLAUDE.md "Email" bullet and ADR-0002 §2; B-A also touches onboarding | No readable roster anywhere in the cloud's own stores; same deliverability; provider fallback is a homelab config change; design is a superset (C23) | Verification redesign and a kit-day homelab dependency; nudges pause during outages; silent mail failure unless a heartbeat is added; wide token scope (C25); Cloudflare still sees at least 31 days of recipients (C21) | C2–C4, C6–C8, C12, C21, C22, C25, C29 |
| **B + outage fallback** | As B | The Worker holds per-person addresses encrypted to a key the homelab releases, or pre-staged outage nudges | Gives back part of the minimisation; more complex | Skeptic leads; not evaluated further |
| **C. Homelab roster; another provider** (Postmark/Resend) or the owner's mailbox | As B; no AWS | Cloudflare account takeover reveals no relative addresses | Another processor, with unverified retention and DPA; the owner's personal mailbox mixes accounts (intake E9) | C20; lead for C3 |
| **D. Verified-destination roster** (each relative is a Cloudflare destination address) | Adds a Cloudflare verification click per relative | $0 even on Workers Free; Cloudflare's click replaces a custom verification link | Account-level list (C10); an extra step for relatives | C1, C10 |
| **E. Push or in-app only** | Contradicts ADR-0002 email nudges | No email PII | Cannot reach dead or never-opened devices; push tokens go to Google/Apple | Q8 |
| **E′. Device notifications first, email only for silent devices** | Fits; it is a nudge-policy choice (E3) | Less email volume, so a smaller 31-day log footprint | Needs E3 policy | Lead for E3 |
| **G. Owner-mediated nudges** (the homelab alerts only the owner, who contacts the relative personally) | Contradicts ADR-0002 "email is also used for backup nudges" | Almost no relative PII at Cloudflare; no verification mail needed | Owner time against BUD-SUPPORT (≤ 2 h/month) | Skeptic lead |
| **F. Direct-to-MX from the homelab** | Fits outbound-only | No third party | Poor delivery (secondary evidence); MTA upkeep against BUD-SUPPORT | C19 |
| **Dedicated Cloudflare account for email** (orthogonal to A/A′/B) | Fits | Limits the blast radius of an account takeover and of Analytics Read tokens | A second account to manage | Skeptic lead; not verified |

### Similar work and lessons

| Project | What they do | Borrow or avoid | Source |
|---|---|---|---|
| Immich | Server holds user emails and sends through admin-configured SMTP; per-user, per-event opt-out | Borrow per-person opt-out and server-held addresses | S23 |
| Ente museum | SMTP-only sender; logs the recipient at Info when SMTP is unset | Avoid: never log addresses | S24 |
| ntfy.sh | Relays through Amazon SES; keeps addresses until removed | Any relay sees address and content | S25 |
| Healthchecks | Staleness from the last ping (timeout plus grace) | Borrow for the homelab job and the mail-health heartbeat | S28 |

## Spikes

| Spike | Hypothesis | Pass → / fail → (decision) | Exec tag | Budget IDs | Data class | Status | Result |
|---|---|---|---|---|---|---|---|
| D6-S1 Minimal-PII variant | The homelab holds the only roster, computes staleness from receipts and last-seen times, and sends through REST. D1 holds no name or email, and nudges arrive within 24 h of staleness. | Pass → Option B for OD-03, ADR-0027. Fail → Option A or A′ (preview off; jurisdiction chosen at creation if wanted) | SB. **Emulated run only** (wrangler 4.143.0 / Miniflare, mock email API; **not real R2/Cloudflare**) | BUD-SUPPORT (kit records owner minutes). BUD-TTS is context only: the 24 h figure is PLAN's own criterion, not a budget; question to H1 | `SYN → results` (emulated); `LAB → results` (kit) | **Emulated: provisional pass, D1-schema part only.** Real-sandbox kit ready (about 1.5 h hands-on) | 0 of 17 markers in D1, local R2, cache, wrangler output, the local observability store and the owner-alert mail (positive control 17 of 17). Plaintext roster blob refused (HTTP 400). Nudge delay 0 h simulated while the homelab was up; **criterion not met during an outage (40 h)**; the dead-man's switch alerted only the owner after 6 h. Under the emulator, the `destination_address` pin refused other recipients. The documented `to`-omitted default failed in Miniflare. Evidence: `spikes/D6-S1/README.md`, `spikes/D6-S1/evidence/results.json`, `spikes/D6-S1/evidence/d1-export.sql`. Kit: `docs/research/kits/D6-S1/README.md` |
| D6-S2 Worker log audit | A Worker configuration with no personal data in logs is achievable. Expected: V1 (`invocation_logs: false`) or V2 (observability off), plus three code rules. | Pass → ADR-0027 log settings. Fail → `observability.enabled: false` on person- or device-facing Workers; residual recorded in the inventory and OD-17 | SB. **Emulated run only** (`wrangler dev --local`; not real Cloudflare) | BUD-TEL (context only) | `SYN → results`; kit `SYN + LAB → results` | **Emulated: inconclusive. Kit ready** (2026-10-06) | Locally, all three configs gave identical results, because the local tool ignored both settings. The query-string marker appeared via `<METHOD> <URL>`, and a console-logged body appeared. The uncaught-exception body reached `wrangler dev` stdout. Header marker and fake IP not found. Supports three code rules: no personal data in URLs, never log bodies, scrub exceptions. The kit deploys V0–V3 with markers in the query, path, header, user agent, bodies and exceptions, and queries the Workers Observability API. Driver rehearsed locally (script only). Evidence: `spikes/D6-S2/README.md`, `spikes/D6-S2/evidence/results.json`. Kit: `docs/research/kits/D6-S2/README.md` |
| D6-S3 Privacy comprehension | ≥ 5 of 6 adults correctly say who can see their files | — | FM | — | — | **Deferred** (outside Wave 1 scope; consolidated family visit, E2 test plan) | No kit written |

**Real-sandbox checks the D6-S1 kit does not yet cover.** These are for the next D6 spike-runner pass; the kit is not edited in this stage.
1. `GET …/email/sending/messages/{id}` with preview off: is content returned? (C25)
2. List the suppressions and the Activity log with the homelab's sending token: can it read recipients? (C25)
3. Mint a token with only the `create` scope, and record what else it can do, such as onboarding a subdomain. (C25)
4. Send to a suppressed recipient with "Drop suppressed recipients" off: is the whole send a 400? (C8)
5. Send with an expired token, and check that the heartbeat or alert path notices. (F4.4)
6. Is preview on by default for an API-onboarded domain? (C7)
7. What error does a `destination_address` violation return? (C12)
8. After a `mailto:` unsubscribe through Email Routing, inspect `emailRoutingAdaptive`. (C26)
9. C11, the scope of an unrestricted binding (already in the kit, step 21).

## Conflicts with settled text

None is resolved here. Each goes to the owner as OD-03.

1. **CLAUDE.md, Settled requirements, "Email" bullet:** "Account name, email and device activity times are plaintext in the cloud control plane; file content and metadata are not." **Option B contradicts this.** The draft wrongly said that CLAUDE.md is not contradicted, and all three skeptics caught it. Choosing B needs the owner to amend this bullet; the run must not edit it.
2. **ADR-0002 §2 (Accepted):** "a confirmation link is sent" and "Consequence: name, email and per-device activity timestamps are stored in plain text in the cloud control plane." B changes both. A superseding draft is owned by **D1** (PLAN D1 "Owns … superseding-ADR drafts for any changes to ADR-0001/0002"), with D6 and C3 contributing. ADR-0027 does not itself amend ADR-0002.
3. **CLAUDE.md and ADR-0002 §2 onboarding**, where redemption creates the account with name and email: path **B-A** (admin-entered roster) moves data entry to the admin. It is a separate sub-option for the owner, not an implementation detail.
4. **CLAUDE.md "end users should never touch configuration"** against an in-app mute or opt-out. This is a minor tension, deferred to OD-12 and E3.
5. Not settled text, but a cross-note conflict: **D1 SR-25** against any verification code, verification link or unsubscribe link in email, under every option (F4.3).
6. The draft's "if undecided, assume B" conflicted with PLAN §5.4 (proposals only). It is withdrawn: the default is now the settled text, kept B-compatible.

## Open questions

| Question | Who | By when |
|---|---|---|
| Primary legal texts: GDPR Art. 2(2)(c), Recitals 18 and 26; Lindqvist, Ryneš, TK C-708/18; ePrivacy Art. 13; UK GDPR, PECR reg. 22, DUAA 2025; ICO; 15 USC 7702, 16 CFR 316.3; Civ. Code 1798.140; COPPA 16 CFR 312 | H1 (network route) or owner-supplied copies; then the D6 Wave 2 legal memo; counsel | Before ADR-0027 is accepted (Gate C) |
| Cloudflare self-serve terms, DPA and Email Service sub-processors: does a private individual fit? | H1 route; D6 | Gate C |
| Token scope: what can the narrowest sending token do (C25)? Is a separate email-only Cloudflare account worth it? | D6-S1 sandbox; D2/D3 | Wave 2 |
| Do hosted Workers Logs keep request bodies or client IPs (C17)? | D6-S2 kit | Wave 2 |
| Real-sandbox D6-S1, including the additional checks listed under Spikes | Owner with the kit; D6 | Before ADR-0027 is accepted |
| Verification design (code vs token-hash link) against BUD-ENROLL and the kit-day flow | C3, E5; E2 usability | Gate C |
| SR-25 carve-out for verification mail | D1 | Wave 2 |
| Postmark and Resend retention and DPA (Option C; the B4 fallback) | C3 | Gate C |
| Owner's jurisdiction, relatives' countries, and whether EU data residency is wanted at all (this decides the D1 jurisdiction under **any** OD-03 option) | Owner at H2 intake | Before the production D1 is created |
| Relatives without an email address (intake F6) | E3, E7 | Wave 2 |
| Should a nudge-latency budget (the 24 h figure) go into `budgets.md`? | H1 | Wave 2 |

## Recommendation

**Option B, path B-R, conditional on the real-sandbox D6-S1 run passing.** The homelab holds names and email addresses and sends nudges through Cloudflare Email Service's REST API. SMTP is an alternative, but it is beta (C28). Device-entered entries reach the homelab encrypted to the **pinned** homelab key (SR-02). The cloud keeps only the owner's alert address, pinned on the dead-man's-switch binding, and an address-free mail-health heartbeat.

Why, resting only on verified claims and the emulated spike:
- It is feasible with the provider ADR-0002 already names (C2, C3).
- Deliverability does not change (C4).
- It leaves no readable roster in any store the cloud control plane controls, which matches the system's pattern of plaintext at home and opaque IDs in the cloud. D6-S1 showed this under emulation (C29).
- Its client and API design also works under A (C23, a tie-breaker only).

What the draft overstated and this version drops:
- "avoids a D1-jurisdiction one-way door": the question exists under both options, and a change is a migration (C14);
- "most reversible" as a main reason (C23);
- "a send-only token" (C25);
- any legal support (C24, contested).

What the owner should know: the margin over **A′** is smaller than first presented. Cloudflare still sees at least 31 days of recipients and subjects, suppressions with no expiry, and the owner's address under every option (F2). B adds a homelab dependency at enrollment, a possible silent mail failure (mitigated by the heartbeat), and a settled-text change.

**D6-owned minimisation requirements that hold under every option** (recorded in the ADR-0027 draft):
- Content minimisation: generic subjects and bodies, no device names, no links in nudges (SR-25).
- Email preview off on the sending domain, as a secondary control.
- No personal data in URLs; never log bodies; scrub exception messages (D6-S2 code rules). Observability settings come from the D6-S2 real run.
- Unsubscribes recorded in the roster holder's mute list, never as Cloudflare manual suppressions.
- Prefer an in-app mute or an HTTPS opt-out to `mailto:` through Email Routing (C26).
- No Queues subscription for sending events; poll the suppression API instead (C27).
- One recipient per send call; never log addresses.
- The narrowest sending token available, IP-restricted, with a TTL, rotated, and alerted before expiry.
- Name and email kept in a separable store, so that A, A′ and B stay buildable.

**What would change this:**
- The real D6-S1 fails, or E5/E2 find the B verification flow cannot meet BUD-ENROLL. Then choose A′.
- The owner values nudges during homelab outages and click-to-verify above minimisation. Then choose A′, or A.
- Counsel objects to Cloudflare holding relatives' addresses at all. Then choose C.
- The owner prefers to contact relatives personally. Then choose G.

## Decision requests

### OD-03: Where family names and email addresses live, and who sends nudges
- **Needed by:** Wave 1 exit (sitting 2)
- **Evidence:** this note; `d1-threat-model.md` (V12, V20, V21, SR-02, SR-25, AR-05); `c4-cost-model.md` (K15); D6-S1 (emulated, provisional pass) and D6-S2 (emulated, inconclusive); kits `docs/research/kits/D6-S1/` and `docs/research/kits/D6-S2/`
- **Options:**

  | Option | What it means for the family | Cost (money and owner time) | Reversibility | Risks |
  |---|---|---|---|---|
  | A. Cloud (as written) | Nothing changes; click a link to verify; nudges continue while the homelab is down | $0 extra; least build | Moderate: a later move to B leaves a Time Travel tail that expires after 30 days | A readable roster sits next to credentials in the internet-facing component |
  | A′. Cloud, encrypted at rest | As A | $0; small Worker key management | Moderate | Protects against D1 leaks, not Worker bugs or account takeover |
  | B. Homelab only, sent via Cloudflare (recommended; sub-paths B-R device-entered and B-A admin-entered) | Verify by an emailed code typed into the app, or a link (C3 decides); nudges pause during outages and the owner is paged | $0 extra; a small homelab mail job plus a heartbeat; one more secret (wide scope) | Easy to move to A (data upload); the design works under A too | At least 31 days of recipients at Cloudflare anyway; kit-day homelab dependency; silent failure without the heartbeat |
  | C. Homelab only, another provider | As B | A provider fee (not checked); another account | Easy | Another processor, with unverified retention |
- **Recommendation:** B with path B-R, conditional on the real-sandbox D6-S1 run. A′ is the runner-up.
- **Touches settled text:** **CLAUDE.md "Email" bullet** and **ADR-0002 §2** (Consequence sentence and verification link). B-A also touches the onboarding text (redemption creates the account with name and email). Choosing B needs the owner to amend CLAUDE.md, plus a superseding draft of ADR-0002 §2 by D1, with D6 and C3 contributing. H1 is asked to set the decision queue's "Touches settled text?" column for OD-03 to include the CLAUDE.md bullet.
- **If no decision by the deadline:** design to the settled text (A), **kept B-compatible**:
  - the C1 API accepts a roster entry only as an opaque blob encrypted to the pinned key, or as an admin-entered record;
  - name and email sit in a separable D1 table;
  - C3 designs a verification flow that works by code or by link.

  Nothing is built that only works under B, and the owner is asked again at the next sitting. Alternatively, the owner may explicitly allow B as the working assumption.

### D1 jurisdiction (new; owner intake, not an OD item yet)
- **Question:** Are any relatives in the EU, and does the owner want EU data residency for D1 (and R2)? This applies under every OD-03 option.
- **Recommendation:** ask at H2 intake and decide before the production D1 is created. A later change means a new database plus a migration (C14).

### OD-17 (addition): accept the email-provider residue
- **Question:** Accept that Cloudflare Email Service holds recipients and subjects for 31 days, suppressions with no expiry, and the owner's destination address, under every option (an extension of AR-05)?
- **Recommendation:** accept, with content minimisation and preview off, and state it in the family charter.

## Hand-offs

| To | What | Why |
|---|---|---|
| D1 | Superseding draft of ADR-0002 §2 if OD-03 = B (D6 and C3 contribute); SR-02 as a precondition of path B-R; decide an SR-25 carve-out for verification mail; add AR-05 email residue | PLAN D1 owns superseding drafts and the SR list |
| C3 | Verification design (code vs token-hash link) evaluated against BUD-ENROLL; `mailto:` vs HTTPS opt-out (C26); handling of the "Drop suppressed recipients" setting; tested fallback provider; dedicated sending subdomain; consider a dedicated email-only Cloudflare account; C11 test | ADR-0026 |
| C7 | Address-free mail-health heartbeat from the homelab, with the dead-man's switch paging the owner on staleness and before token expiry; owner alert address pinned with `destination_address` | ADR-0033 |
| C1 | API accepts the roster only as a pinned-key-encrypted blob or an admin-entered record; name and email in a separable table under A | ADR-0010; keeps A, A′ and B buildable |
| D2 / D3 | The homelab sending token is wider than send (C25): scope, IP filter, TTL, rotation, blast radius | ADR-0008, ADR-0014 |
| E3 | Nudges computed at the homelab under B; outage behaviour; mute and opt-out against OD-12; device notifications first (E′) | ADR-0025 |
| E5 / E2 | Kit-day behaviour when the homelab is down; usability test of code entry against BUD-ENROLL | ADR-0038; E2 test plan |
| H1 | Blocked sources (Method); OD-03 "Touches settled text" column to include the CLAUDE.md Email bullet; whether a nudge-latency budget belongs in `budgets.md` | Run rules; registries |
| H2 | Relatives' countries; EU-residency wish; relatives without email | D1 jurisdiction; F6 |
