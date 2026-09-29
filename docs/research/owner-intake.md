# H2. Owner intake and infrastructure baseline

- **Workstream:** H2 (see `docs/research/PLAN.md`, section "H2.")
- **Status:** **Waiting for the owner's answers.** Nothing here is confirmed yet.
- **Date:** 2026-09-29
- **Time needed:** about 1 hour. Part 1 (about 40 min) and the approvals in §J are needed before Wave 1. The rest of Part 2 (about 15 min) can follow within the week.
- **Unblocks:** OD-14 and the budget sheet ([budgets.md](budgets.md)); the provisional v1 scope for E2 (§K); H5 purchases ([h5-long-lead-items.md](h5-long-lead-items.md)); C4, C5, C1, C3, D6, E1, F1 and A9 inputs.
- **File name:** PLAN calls this file `h2-owner-intake.md`. It was created as `owner-intake.md` on instruction; the research index links here.

## How to answer

- Other documents cite these questions as **Q-** plus the ID (for example Q-A1 or Q-H1). The letters are sections of this file, not workstreams.
- Write in the **Your answer** column. Leave it blank or write **"default"** to accept the proposed default. Write **"skip"** if you don't know yet. The run then uses the default and marks it *provisional*.
- **No secrets.** Do not write passwords, recovery codes, API tokens, account IDs, card details or street addresses.
- **No family data** (H3). Refer to relatives by relationship only ("my sister"), with no names or contact details. Give counts and rough sizes, never file lists.
- This file lives in the repo, which may become public (OD-15), so keep answers coarse: a country rather than a town, "about 5 TB" rather than exact figures. Anything you would not publish goes in the homelab private store (H3 R7), with a note here saying "given offline".

---

## Part 1: needed before Wave 1

### A. Where people live and who owns the accounts

| ID | Question | Why it matters | Proposed default | Your answer |
|---|---|---|---|---|
| A1 | Which country (and state or province) do you live in? | Privacy law (D6), eligibility for Windows signing (Azure individual accounts are US or Canada only), postage (H5 L31), R2 jurisdiction | — | |
| A2 | Which countries do the other households live in? Any in the EU, EEA or UK? | GDPR household exemption and R2 jurisdiction (D6) | Same as A1 | |
| A3 | Does any household live in Brazil, Indonesia, Singapore or Thailand? | Android developer verification is enforced there from **30 Sep 2026** (B3) | No | |
| A4 | Which languages do the households want for app text and email? | Localisation scope for v1 (E6) | English only | |
| A5 | Should Reliquary stay separate from your business, or may a company hold the developer accounts? | Personal vs organisation accounts for Play, Apple and Azure; D-U-N-S numbers; the developer name the public sees (D6, B3, H5 L05) | Keep it separate; use personal (individual) accounts | |

### B. Money, time and cost ceilings (OD-14)

Unit prices in B1–B3 are the verified figures from H5 §5. The volumes are assumptions, and C4 v0 will check them. Operations per file are assumed (3 Class A per upload) until A0 measures them.

| ID | Question | Why it matters | Proposed default | Your answer |
|---|---|---|---|---|
| B1 | **BUD-CLOUD:** the most the cloud may cost per month at steady state | C4, C7-S3 | **$25/month**, with billing alerts at $10 and $20. The basis: Workers Paid minimum $5, plus R2 staging at $0.015 per GB-month (200 GB staged on average is about $3), plus operations within the free allowances. That comes to about $8/month. | |
| B2 | A higher ceiling for **seed months**, while large libraries upload over R2? | C4 seed scenarios; decides how much goes by USB instead | **$50/month.** A month that moves 2 TB and 500k files, with about 300 GB staged on average, costs about $12 at the assumed volumes: $5 Workers Paid, about $4.35 of storage (290 GB-months above the 10 GB free), and about $2.25 for the 1.5M Class A operations (0.5M above the 1M free). | |
| B3 | **BUD-ABUSE:** the most a stolen device credential may cost before the system suspends it | C2 auto-suspend design, C2-S2, D4-S3 | **$50.** At R2 prices that is about 3.3 TB staged for a month, or about 11 million write (Class A) operations. | |
| B4 | **Beta-feature policy:** may the design depend on Cloudflare features still in beta (for example Email Service)? | C1, C3, C6 (§3 checklist) | **Only with a documented, tested fallback that needs no client update**. For example, Email Service with Resend or Postmark as the fallback. | |
| B5 | Monthly cap for the **sandbox** Cloudflare account | Agents stop and ask above it (H1, H5 L01) | **$20/month** | |
| B6 | One-off budget for **test hardware** | H5 batches 1 and 2, estimated at $700–3,300 in total depending on what you own | **Approve batch 1 up to $1,000**; ask before batch 2 | |
| B7 | One-off budget for **homelab hardware** (disks, UPS) | C5 BOM tiers, C4 | None assumed; C5 proposes two tiers for you to pick from | |
| B8 | Appetite for signing costs: Apple Developer $99/year; Azure Artifact Signing $9.99/month (Windows); Play $25 once | OD-09 (Gate C), H5 L05, L07, L08 | Play: yes. Apple and Azure: only if tests show they are needed. | |
| B9 | How many hours per week can you spend **building** over the next 6 months? | F1 effort model: what ships in 6, 12 and 24 months | 8 h/week, as a planning figure only | |
| B10 | How much time will you accept for **maintenance** once running? (BUD-SUPPORT) | C8, E3 nudge policy | ≤ 2 h/month | |

**B11. Confirm the budget sheet.** These are the proposed defaults from [budgets.md](budgets.md). Write "OK" or a new value. H1 copies the result into the sheet.

| Budget | Proposed default | OK / new value |
|---|---|---|
| BUD-TTS time to safe | "Stored at home" within 24 h while online and the homelab is up; median time to "sent" < 1 h on idle Wi-Fi | |
| BUD-BAT-D phone battery | < 2 % per day | |
| BUD-BAT-S seed battery | Report % per 10 GB; target set after A1-S1 | |
| BUD-TMP phone temp disk | ≤ 2 GB, and never below 10 % free | |
| BUD-HASH hashing floor | 128 GB library within one 6 h charge window on a low-end phone | |
| BUD-DESK desktop agent | Idle < 150 MB RAM, < 1 % CPU; work < 25 % of one core | |
| BUD-SCAN reconciliation | 500k files in < 5 min on a mid-range laptop | |
| BUD-INGEST homelab ingest | ≥ max(100 MB/s, 2 × home download speed) | |
| BUD-RESTORE | Single file < 5 s from the store; < 30 min of your time per request | |
| BUD-AUDIT fixity | Full audit of 10 TB fits in a monthly window | |
| BUD-CPU-REQ | Request-signature check < 1 ms CPU | |
| BUD-REVOKE | No new upload URLs within 60 s; old ones expire within 15 min | |
| BUD-RECOVERY | A relative recovers 10 named photos from the doomsday kit in ≤ 2 h | |
| BUD-ENROLL | A relative enrolls a computer from the kit unaided in ≤ 20 min | |
| BUD-SUPPORT | ≤ 2 h per month (see B10) | |
| BUD-CLOUD / BUD-ABUSE | See B1 and B3 | |
| BUD-TEL telemetry | < 1 MB/day network, < 50 MB disk per device | |
| Spike-local thresholds ([budgets.md](budgets.md), last table) | Accept the suggested handling for all five | |

### C. Homelab baseline

| ID | Question | Why it matters | Proposed default | Your answer |
|---|---|---|---|---|
| C1 | Proxmox VE version? Proxmox Backup Server too? | C6 runtime, A6 (PBS is a candidate engine) | — | |
| C2 | CPU model? ECC memory: yes, no or unknown? | C5 (ECC), A6 ingest speed | — | |
| C3 | RAM: total, and how much is usually free? | A6-S2 (engine RAM < 4 GB), H1 staging VMs | — | |
| C4 | Disks: count, size, HDD or SSD, CMR or SMR if known, rough age. Pool layout (mirror, RAIDZ1/2, other). Used and free TB. | C5, C4 capacity forecast, H5 L21 | — | |
| C5 | Can you set aside **0.8–2 TB** for the storage bake-off and a private research store? | A6-S2, H3 (H5 L20) | Yes, on the existing pool | |
| C6 | Is anything encrypted at rest today? How does it unlock after a power cut? | A6 at-rest posture (OD-07), C5-S4 | — | |
| C7 | UPS: model and VA, or none. Is NUT set up? | C5-S2, C7 (H5 L22) | — | |
| C8 | Other services on the box, and anything critical a research VM must not disturb | C6 isolation; the risk of running spikes there | — | |
| C9 | Network card speed; are VLANs available; can research VMs get an outbound-only network? | ADR-0001 outbound-only rule, C6, D4 USB-ingest VM | — | |
| C10 | Is there room for a nested Proxmox staging environment plus about 4 test VMs at once? | H1 staging, G2-S4, B7-S2 resets (H5 L25) | Yes | |
| C11 | Where does the box live (heat, noise, flood risk)? Can someone at home power-cycle it while you are away? | C5, C8 unattended survivability | — | |
| C12 | Is the homelab itself backed up today (PBS, external disk)? | C8, A6 catalog backups | — | |

### D. Home internet

| ID | Question | Why it matters | Proposed default | Your answer |
|---|---|---|---|---|
| D1 | Download and upload speeds (measured if you can) | Sets BUD-INGEST; C4 drain rate; restores over the upload link | — | |
| D2 | Is there a monthly data cap? How large? | C4 seed plan; hairpin traffic when home devices upload to R2 and the homelab pulls back (H5 L34) | No cap | |
| D3 | Behind CGNAT? IPv6 available? | Diagnostics and the LAN option only; the homelab stays outbound-only | Unknown | |
| D4 | Does the router support local DNS or NAT hairpin? | A4-S5 LAN decision | Unknown | |
| D5 | Do other households have data caps or slow upload links? | Seed mix per person (A9), USB vs R2 | Unknown; the census asks | |

### E. Domains, accounts and recovery

| ID | Question | Why it matters | Proposed default | Your answer |
|---|---|---|---|---|
| E1 | Which domains do you own that could host the Reliquary API and email (a subdomain is fine)? Registrar and DNS host? | One-way door #8 (API hostname, Gate C), C3 sending domain (H5 L03) | Register a **new dedicated domain** at Cloudflare Registrar | |
| E2 | Are auto-renew and registrar lock on? Is the registrar's recovery email on a **different** domain? | §3 checklist: the domain is a dependency | Turn on both; use a recovery email on another domain | |
| E3 | Any domain transfer planned or recently done? | ICANN blocks transfers for 60 days after registration, a transfer or a registrant change (H5 L03) | No transfer | |
| E4 | Existing Cloudflare accounts: plan, who else has access, 2FA type? | C2 hardening; keeping the sandbox separate from production | Create **two new dedicated accounts**: sandbox now, production in Wave 3. Neither is a business account. | |
| E5 | Which of these accounts do you already have, and with which 2FA type: Google Play Console, Apple Developer, Microsoft Azure, GitHub? (No IDs.) | H5 L05, L07, L08; D5 (GitHub with hardware 2FA) | — | |
| E6 | Play developer account: **personal or organisation** (first half of OD-10)? What developer name should people see? | Lets registration start at "go" (H5 L05). The channel choice waits for B3. | **Personal**; name: your choice | |
| E7 | Hardware security keys: how many do you own? Are they PIV-capable (for example YubiKey 5)? | C2, D2-S1 (H5 L04) | Buy 3 PIV-capable keys | |
| E8 | Who can recover these accounts today (you only, a spouse, password-manager emergency access)? Relationship only. | Bus factor (E7, C8, D2) | — | |
| E9 | Which email address should the project accounts use? | §3: recovery must not depend on the project's own domain | A dedicated mailbox **not** on the Reliquary domain | |
| E10 | Your alert channel: a push app (ntfy, Pushover, Telegram) and/or email? | C3, C7 dead-man's switch | Push plus email | |

### F. Family basics (counts only)

| ID | Question | Why it matters | Proposed default | Your answer |
|---|---|---|---|---|
| F1 | Number of households, and people per household: adults, teens (13–17), children (under 13) | Scale, consent (D6), roles (E7) | — | |
| F2 | Rough device counts: Android phones and tablets; iPhones and iPads; Windows PCs; Macs (Apple Silicon or Intel); Linux; Chromebooks; shared computers | G2 device matrix, B1/B2 support policy, H5 purchases | — | |
| F3 | Your guess at the **share of camera-roll photos and videos on iPhones or iPads**: under 20 %, 20–40 %, or over 40 %? | Over 40 % escalates OD-01 (E1-S2 measures it later) | Unknown | |
| F4 | Rough total size of keepsakes across all devices: under 2 TB, 2–5, 5–10, or over 10 TB? | C4, C5 capacity | — | |
| F5 | How many managed work or school devices hold family keepsakes? | E1, B1 (managed devices may block the app) | 0 | |
| F6 | How many people have no email address of their own, or no Google account on their Android phone? | E5 enrollment, C3 nudges, Play closed-track opt-in | 0 | |
| F7 | Accessibility needs to plan for: count by type (vision, motor, hearing, cognitive) | E6 | None known | |
| F8 | How many relatives would take part in research (a visit, some short tests)? Is there a tech-comfortable "helper"? | E1, E2 test plan, H5 L26 and L28 | — | |
| F9 | A possible **neutral facilitator** for interviews (relationship only)? | E1-S3 (H5 L27) | You run the interviews; E1-S3 compares | |
| F10 | Deputy or successor candidates, and how many relatives might hold a recovery share (relationships only)? | D2 and E7 (OD-08), L32 recovery drill | — | |
| F11 | Is there anyone who must not be enrolled, or who needs special handling (estrangement, a minor's consent)? Yes or no only; give details offline. | D6 consent, E7 | No | |

### G. Existing archives

| ID | Question | Why it matters | Proposed default | Your answer |
|---|---|---|---|---|
| G1 | Where do keepsakes live apart from current devices, and roughly how big is each? (NAS or homelab folders, external drives, old phones and computers, SD cards, CDs and DVDs, tapes, prints) | A9 import-first seed, §3 "drawer pile" | — | |
| G2 | Which cloud photo services are in use, and with which settings? (iCloud "Optimize Storage", Google Photos "Storage saver", OneDrive camera upload) | B5, E3: originals may be missing, and re-encoded copies never deduplicate | — | |
| G3 | Any existing Google Takeout or iCloud exports? Count and rough size | A9-S1 | — | |
| G4 | Is anything important in **only one place** right now? Yes or no, and what kind (for example "old laptop photos") | E2 interim protection, to act on this month | — | |
| G5 | Can you bring a **100 GB sample** of your own archive plus one Takeout export to the homelab for A9-S1? | A9-S1 (Wave 2) | Yes | |
| G6 | Old formats you expect (camcorder video, RAW, old Office files) | A7-S3 format survey | — | |

---

## Part 2: preferences and provisional scope (within the week)

### H. Provisional v1 scope (input to E2 and ADR-0004)

These are early views, not decisions. Each one is decided later from evidence (OD numbers given). None of them changes `CLAUDE.md` or an Accepted ADR.

| ID | Question | Why it matters | Proposed default | Your answer |
|---|---|---|---|---|
| H1 | iPhone: your early view on OD-01. In v1, after the pilot with an iPhone bridge, or later? | B4, E1-S2 (CLAUDE.md says v1; ADR-0002 defers it) | After the pilot, with a bridge. The core must not rule out iOS. | |
| H2 | Documents on Android in v1 (OD-19): media only, chosen folders, or all files? | B2, B3 policy risk | Media only | |
| H3 | Which comes first in the pilot: desktop (USB kit) or Android? | E2 pilot order | Desktop first, Android right after | |
| H4 | If the app is late, is a "concierge" start OK? You seed by USB at family visits while the app only finds files and reports status. | E2 fallback | Yes, as a fallback | |
| H5 | Will you apply one stopgap backup per device type this month (E2-S3)? | Protect keepsakes **now** (§3) | Yes | |
| H6 | Relatives will ask to browse and share. What is the v1 answer? | E2, OD-13 | Not in v1 | |

### I. Project preferences

| ID | Question | Why it matters | Proposed default | Your answer |
|---|---|---|---|---|
| I1 | Public or private repo (OD-15)? | G3, B3 export rules, CI cost | Private until ADR-0036 | |
| I2 | Licence preference, if any | G3, F1 (adopting AGPL code) | No preference yet | |
| I3 | Digital-preservation ambition (NDSA level, OD-16) | A7 | Let A7 recommend a level | |
| I4 | Test hardware you **already own or can borrow**: phones (brand and Android version), a Windows 11 PC you can clean-install, Macs (Apple Silicon or Intel, a notched MacBook), iPhone, printer, spare USB sticks, UPS, security keys | Cuts H5 purchases (L04, L12–L19, L22, L24) | Assume none; H5 buys batch 1 | |
| I5 | Are used or refurbished test devices OK? | H5 cost | Yes | |

### J. Approvals to start Wave 0 actions

Answer this section together with Part 1: these approvals start Wave 0 actions and are needed before Wave 1.

| ID | Approve? | Proposed default | Your answer |
|---|---|---|---|
| J1 | Widen the container's network access per the allowlist in [sources.md](sources.md) | Approve the "before Wave 1" rows | |
| J2 | Create the sandbox Cloudflare account and throwaway domain, capped at B5 | Approve | |
| J3 | Buy H5 batch 1 within B6 | Approve | |
| J4 | Register the Play developer account now, as answered in E6 | Approve | |
| J5 | Book the relatives' visits (weeks 3–7) and a 4-week nudge-pilot window starting by week 4 | Approve | |
| J6 | Confirm the research-data rules in [h3-research-data-governance.md](h3-research-data-governance.md) §2–§4, including R3 (exact file sizes count as family data), R7 (raw outputs deleted 90 days after their aggregate is accepted) and R9 (no third-party binaries committed until ADR-0036). This is OD-21. | Confirm as written | |

---

## K. Provisional v1 scope to hand to E2 (until the answers arrive)

E2 starts from this and updates it from Part 2. It restates the settled text and the defaults above. It decides nothing new.

| Area | Provisional assumption | Source |
|---|---|---|
| Platforms | Windows, macOS, Linux, Android. iOS is open (OD-01): ADR-0002 defers it, and the core must not rule it out. | CLAUDE.md, ADR-0002 §4, Q-H1 |
| Sources | Files on the device, including the phone photo library. Android: media only until OD-19. | CLAUDE.md, Q-H2 |
| Transports | R2 staging and USB. LAN direct is optional and not assumed for v1; whether to build it is still open (ADR-0037, P2). | ADR-0001 §5, CLAUDE.md |
| Assistant features | Discovery proposals, plain-language health per person, nudges. No admin dashboard (OD-13). | CLAUDE.md |
| Restore | Admin-initiated only | CLAUDE.md |
| Pilot order | Owner → tech-comfortable relative → extreme user → everyone; desktop first | PLAN E2, Q-H3 |
| Cost envelope | BUD-CLOUD and BUD-ABUSE as answered in B1–B3 (defaults $25/month and $50) | B1–B3 |

## After the intake

| Who | Does what with the answers |
|---|---|
| H1 | Fills the confirmation table in [budgets.md](budgets.md). Records OD-14 and OD-21 (J6) as Decided in [decision-queue.md](decision-queue.md). Applies J1. |
| H5 | Turns I4, E1–E7 and A5 into the final buy and start list, and updates [h5-long-lead-items.md](h5-long-lead-items.md) |
| E2 | Takes §K and Part 2 as the provisional scope for ADR-0004 |
| C4, C5, A6 | Use B, C, D, F4 and G as the starting parameters |
| D6, B3, B7 | Use A1–A5 (jurisdiction, account type, signing eligibility) |
| E1 | Uses F and the visit approvals to schedule the consolidated visits |
