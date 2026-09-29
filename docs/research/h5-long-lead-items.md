# H5. Long-lead items and procurement

- **Workstream:** H5 (see `docs/research/PLAN.md`, section "H5.")
- **Status:** Draft (Wave 0). Skeptic review not yet run. Every price marked **E** is an unverified estimate.
- **Date:** 2026-09-29
- **Feeds:** OD-09 and OD-10 (prerequisites and lead times), C4 (optional-cost lines), G2 (device matrix and acquisition list), E2 (field calendar), C5 (disk timing)
- **Depends on:** H2 answers ([owner-intake.md](owner-intake.md)), T2 ([fact-check-adr-0001-0002.md](fact-check-adr-0001-0002.md)), H1 source register ([sources.md](sources.md))
- **File name:** PLAN calls this file `h5-long-lead.md`. It was created as `h5-long-lead-items.md` on instruction; the research index links here.

## Summary

- **Start five things on the day the owner says "go".** In-flight T1 spikes and the Wave 1 critical path are waiting on them:
  1. The sandbox Cloudflare account and throwaway domain (L01, L02), plus the network allowlist request that H1 has already raised.
  2. Hardware security keys (L04).
  3. Test-hardware batch 1 (L12a–c, L13, L14, two sticks from L19).
  4. DNS for the sandbox sending domain, so that the 2-week email observation (L09) finishes inside Wave 2.
  5. Booking the relatives' visits and the 4-week nudge-pilot window (L26, L28).
- **The Play developer account (L05) can also start at "go" if the owner picks personal vs organisation at the intake.** The proposed choice is personal. The account is **not** needed for the phone spikes, because installs over ADB are exempt from Android developer verification (S7).
- **Apple Developer (L07) and Azure Artifact Signing (L08) should wait.** Both are conditional (OD-01, OD-09). Apple's individual route takes about a day, so waiting costs little. Azure's identity check cannot be expedited and its duration is not documented, so start it as soon as SAC testing shows signing is needed.
- **Hold off on homelab disks (L21) until C5's BOM exists.** The exception is when the homelab cannot spare 0.8–2 TB for the A6-S2 bake-off (L20). Allow about 1–2 weeks from order to burned-in drives.
- **Money.** The only verified recurring cost at "go" is **$5/month** (Workers Paid on the sandbox) plus a domain. One-off test hardware comes to roughly **$700–3,300 (E)** before homelab disks and any iPhone, and borrowing can avoid much of it.
- **Research turned up four facts that change other workstreams** (§6). Android "limited distribution" is a sideloading channel outside Play, not a Play account. Creating a Play app registers its package name permanently. Target API 36 has been mandatory since 31 Aug 2026. Developer verification is enforced in four countries from tomorrow (30 Sep 2026).

## 1. How to read the tables

| Column | Meaning |
|---|---|
| **Cost** | **V** = verified from a primary source in §7. **T2** = taken from the T2 fact-check and not re-verified here. **E** = estimate from general market knowledge in USD, not checked against a live price (retail sites are blocked from the container, and this session's web-search budget was used up). C4 and C5 replace every E with a real quote. |
| **Lead** | Calendar time from the first action until the item is usable. |
| **Who** | Owner, Agent, Relative, or External (a third party's queue). |
| **Start** | "go" = day 0, the day the owner approves the run. Waves follow PLAN §4.1: Wave 0 is days 1–3, Wave 1 about weeks 1–2, Wave 2 about weeks 3–7, Wave 3 about weeks 8–10. |
| **Blocks** | The workstreams and spikes that wait for the item. |

## 2. Start list for "go" (week 0)

| # | Action | Who | Item |
|---|---|---|---|
| 1 | Approve the network allowlist in [sources.md](sources.md) (api.cloudflare.com, *.r2.cloudflarestorage.com, test domain, policy sites) | Owner | Prerequisite for L01 |
| 2 | Create the dedicated sandbox Cloudflare account: card on file, R2 checkout, Workers Paid, billing alerts at the H2 sandbox cap | Owner | L01 |
| 3 | Register the throwaway domain in that account and add SPF, DKIM and DMARC records | Owner, with an agent drafting the records | L02, L09 |
| 4 | Order 3 hardware security keys (FIDO2 + PIV) if you do not already own them | Owner | L04 |
| 5 | Order test-hardware batch 1: Samsung, Pixel and low-end Android phones; a Windows 11 PC you can clean-install; an Apple Silicon Mac if you have none; 2 USB sticks | Owner | L12a–c, L13, L14, L19 |
| 6 | Register the Google Play developer account, if the intake settled personal vs organisation | Owner | L05 |
| 7 | Start any domain transfer the intake calls for (the ICANN 60-day lock applies) | Owner | L03 |
| 8 | Ask relatives for visit slots in weeks 3–7 and for 5 volunteers for a 4-week pilot starting by week 4 | Owner | L26, L28 |

## 3. Items

### 3.1 Accounts, identity and domains

| ID | Item | Cost | Lead | Who | Start (prerequisite) | Blocks | Fallback |
|---|---|---|---|---|---|---|---|
| L01 | **Sandbox Cloudflare account**: dedicated, never production, with a scoped token and a budget alert | Account $0. **Workers Paid minimum $5/month (V)**, needed for Email Service sending to arbitrary recipients and for Paid-plan CPU limits (C1-S4). R2 requires a checkout (payment method) even within the free tier of 10 GB-month, 1M Class A and 10M Class B operations (V). | < 1 day | Owner (account, card, 2FA); H1 (token scoping) | go (sandbox cap from H2 Q-B5; allowlist approved) | Every `[SB]` spike: **C1-S1 and G2-S1 on the critical path**, A0-S1/S3, A3-S3, B6-S2, C2, C3, C7-S1, C8-S1/S2, D3, D6-S1/S2 | Local emulators only (`[CT]`). Gate B cannot pass without real R2. |
| L02 | **Throwaway sandbox domain** | Registry price with no markup at Cloudflare Registrar (V). Price per TLD not checked; **E** about $10–15/year for a .com. | Minutes. Cloudflare Registrar requires Cloudflare nameservers (V). | Owner | go | C3-S1/S2; a test Worker on a custom domain (the container cannot reach `*.workers.dev`) | A subdomain of the owner's domain. Avoid this: it mixes sandbox and production reputation. |
| L03 | **Owner's production domain**, for the API hostname, the sending subdomain and the privacy-policy page | Renewal only if already owned; otherwise as L02 | None if the owner keeps the current registrar. A transfer takes up to about 10 days, and ICANN blocks transfers for **60 days** after registration, after a previous transfer, or after a change of registrant name, organisation or email (V). | Owner | Decide at intake (Q-E1–E3); start any transfer at go | One-way door #8 (API hostname, Gate C); L09b; the Play listing's privacy-policy URL (B3 to confirm it is required); key fingerprints printed on cards (D3) | Register a new dedicated domain now (no transfer wait) |
| L04 | **Hardware security keys**, 2–3, FIDO2 **and** PIV-capable | **E** $50–90 each | Shipping (days) | Owner | go, if not owned (Q-E7) | C2 hardening (hardware-key 2FA on Cloudflare, registrar, Google, Apple, GitHub); D2-S1 unwrap throughput (age-plugin-yubikey needs PIV); D2 recovery-recipient options | TOTP for the sandbox in the meantime; D2-S1 recorded as "no result" |
| L05 | **Google Play developer account** | **$25 one-time (T2)** | The fee is paid at once. How long identity verification takes is **not verified** (the Play help pages are blocked), so record the actual time. Organisation accounts reportedly need a D-U-N-S number (B3 to confirm); Apple quotes up to 5 business days to issue one (V). | Owner | go, if the intake settles **personal vs organisation** (first half of OD-10; proposed: personal) and the public developer name | B3-S3 closed-track review dry run (`[EXT]`); E5-S4 joining via Play; the install-referrer test (ADR-0002 open question); Play App Signing (D5) | Test with ADB installs, which are exempt from verification (V). The channel decision waits for B3. |
| L06 | **Android Developer Console "limited distribution" account** (only to evaluate it) | **Free (V).** Needs a Google Account with 2-Step Verification and a Google payments profile; no government ID (V). | Google says registering package names and authorising devices "can take some time" (V). Record the actual time. | Owner | Wave 1, only if B3 wants to test it | B3 (the OD-10 comparison) | Not needed if B3 rules it out on paper. **Note:** it is a sideloading channel outside Play (up to 20 devices, authorised by QR or link), not a Play account (V); see §6. |
| L07 | **Apple Developer Program** (conditional) | **$99 per membership year (V).** Also covers Developer ID for macOS signing. | **Individual:** Apple says to contact support if there is no confirmation within 24 h of purchase (V). It needs an Apple Account with 2FA, and Apple may ask for photo ID (V). **Organisation:** a D-U-N-S number takes up to 5 business days, with escalation after 2 weeks (V), and the legal entity is shown as the seller (V). | Owner | Only when (a) B7-S1 reaches its Developer ID arm because the ad-hoc and self-signed arms failed, or (b) OD-01 puts iOS in v1 | B7-S1 Developer ID arm → OD-09; B4-S2 beyond the free tier; iOS distribution | For a first B4-S2 test, Xcode's free personal team: up to 3 devices, with apps expiring after 7 days (V) |
| L08 | **Azure Artifact Signing** (conditional) | **$9.99/month Basic (T2);** billing is not pro-rated (V) | Identity validation **cannot be expedited** and its email link expires after 7 days (V). The docs give no duration, so record it. | Owner | Only if T1 spike 1 or B7-S2 shows that Smart App Control blocks unsigned builds **and** the owner is eligible: individuals in the US or Canada only; organisations in the US, Canada, EU, UK, Australia, New Zealand, Japan, South Korea, Singapore, Switzerland, Norway and Israel (V, docs dated 21 May 2026) | OD-09 (Gate C) | The Start-here guide turns SAC off (ADR-0002 §5), or affected PCs are recorded as unsupported |
| L10 | **Production Cloudflare account** (dedicated, separate from the sandbox) | Workers Paid $5/month (V) plus usage (C4) | < 1 day. Adding a second super-admin (deputy) and hardware keys needs coordination. | Owner | Wave 3, before the first real family ingest | C2 hardening checklist; C8-S2; the D1 accepted risks | None. It is required before the pilot. |

### 3.2 Email reputation and test accounts

| ID | Item | Cost | Lead | Who | Start (prerequisite) | Blocks | Fallback |
|---|---|---|---|---|---|---|---|
| L09 | **Sandbox sending domain**: SPF, DKIM, DMARC, then **2 weeks of DMARC reports and inbox placement** (C3-S1) | No cost beyond L01/L02. Email Service includes 3,000 emails/month on Workers Paid, then $0.35 per 1,000 (V). Resend and Postmark trials not checked. | **≥ 2 weeks** after DNS is live (C3-S1 method) | Owner (DNS); Agent (sending, report parsing) | DNS at go; sending from the start of Wave 1, so the window ends in Wave 2. **Not blocked by OD-03**, because any provider needs an authenticated domain. | C3-S1 → ADR-0026 | Shorter observation, with the result marked provisional |
| L09b | **Production sending subdomain warm-up** | $0 beyond the provider | ≥ 2 weeks | Owner | ≥ 2 weeks before the first pilot nudge email (OD-03, ADR-0026, L03 decided) | Nudge emails in the pilot (E3, Gate C) | In-app and OS notifications only until it is ready |
| L11 | **Test accounts:** 4 mailboxes (Gmail, Outlook.com, iCloud, Yahoo) for C3-S1; 2–3 test Google accounts for test phones; a test Apple Account if an iPhone is used; cloud-drive accounts for B5-S3 | Mostly $0. B5-S3 wants **10 GB** of cloud-only content in each of OneDrive, Google Drive, Dropbox and iCloud Drive. Some free tiers may be smaller than 10 GB (not verified), which would mean a month of paid storage or a smaller test. | < 1 day. Sign-ups may ask for a phone number (L17). | Owner | Wave 1 | C3-S1, B5-S3, E5-S4, B3-S3 | B5 scales the test down to the free tiers and says so |

### 3.3 Test hardware (owner lab)

Batch 1 is needed by the in-flight T1 spikes (1, 3, 5, 7) and the Wave 1 kits (B7-S1, A1-S1). Batch 2 is needed by Wave 2 spikes. Before buying any phone, check that its maker still sends OS updates (the support pages are blocked from here).

| ID | Item | Cost | Lead | Batch | Blocks | Fallback |
|---|---|---|---|---|---|---|
| L12a | Samsung mid-range phone on current Android and One UI | **E** $100–200 used | Shipping 3–10 days (**E**) + 1 day of setup | 1 | T1 spike 3, A1-S1, B2-S1/S2, F2-S1, E3-S3 | Borrow an old relative's phone (consent per H3). Firebase Test Lab is **not** a stand-in for background-survival tests. |
| L12b | Pixel on the current Android release (16 or 17) | **E** $150–350 used | as above | 1 | T1 spike 3, B2-S1, B2-S3 on a real device (emulator images are blocked: `dl.google.com`), A5-S1 Motion Photo and Ultra HDR fixtures | as above |
| L12c | Low-end phone, 3–4 GB RAM | **E** $50–120 | as above | 1 | A1-S1 and A2-S1 (the BUD-HASH floor), T1 spike 7 | as above |
| L12d | Xiaomi or Redmi phone (HyperOS) | **E** $80–180 used | as above | 2 | B2-S1 OEM matrix, F2-S1 | Drop Xiaomi from the matrix and record the gap |
| L12e | Android 10 phone | **E** $30–80 used | as above | 2 | B2-S1, the minimum-Android-version policy | Set the minimum at 11 and record it as untested |
| L13 | **Windows 11 PC with Smart App Control on.** SAC is only switched on by a clean install (sources.md, H1-S1 #10). | **E** $0 (spare PC, reinstalled) to $350 (mini PC) | Shipping + half a day to clean-install | 1 | **T1 spike 1 (in flight; before ADR-0003)**, B7-S2, A0-S1 Windows run, B1-S1..S4, E3-S3 | A Proxmox VM (G2-S4). Whether SAC behaves the same in a VM is **unverified**, and PLAN §5.5 asks for real hardware. Windows 10 22H2 legs can use VMs; the owner should check licensing for test VMs. |
| L14 | **Apple Silicon Mac** on macOS 26 | **E** $300–550 used | Shipping | 1, if the owner has none | **B7-S1 (P0 kit, Wave 1)**, the macOS legs of T1 spikes 1 and 5, B1-S1, B4-S2 (Xcode), ad-hoc-signed macOS builds | Borrow one. B7-S1 cannot run in the container. |
| L15 | Intel Mac | **E** $0 (borrow) to $250 | Shipping | 2 | The Intel leg of B7-S2; B1 support policy | Drop Intel and record the risk |
| L16 | MacBook with a notch | Borrow | — | Wave 2 | E3-S3 menu-bar visibility | Test with a notch simulator and say so |
| L17 | 2 prepaid SIMs or phone numbers | **E** $10–30 each | Days | 2 | WhatsApp-received media fixtures between two test phones (H3 §8); metered-network tests (A5-S3, B1-S2, B2); test-account sign-ups | The owner's phone as a hotspot for the metered tests |
| L18 | iPhone (conditional on OD-01). A Pro model is needed for ProRAW, and for spatial video a model that records it. | **E** $0 (borrow) to $700 | Shipping | Wave 1–2 | A5-S1 fixtures: no licensed public Live Photo, ProRAW, burst, portrait or spatial-video sample exists (H3 §11). Also B4-S2/S3 and E5-S2. | Borrow a relative's phone for fixture-only captures with no people in them; otherwise those corpus items stay "no result" |
| L19 | **USB storage set**: 3–4 cheap sticks (USB 2.0 and 3.x); 1 deliberately fake-capacity stick; 1 USB SSD; 2 dual USB-A/USB-C sticks | **E** $100–250 in total | Days. Fake sticks come from marketplaces with uncertain delivery. | 2 sticks in batch 1, the rest in batch 2 | T1 spike 1 and B7-S1 (apps copied from USB), A4-S1, E5-S5, B7-S2, the B6 writer, D4-S5 | Fewer sticks. A simulated fake-capacity stick is not the same test, so say so. |

### 3.4 Homelab

| ID | Item | Cost | Lead | Who | Start (prerequisite) | Blocks | Fallback |
|---|---|---|---|---|---|---|---|
| L20 | 0.8–2 TB of free space for the A6-S2 bake-off and the H3 private research store | $0 if the space is free; otherwise a scratch drive, **E** $60–150 | Shipping | Owner | Wave 1 (Q-C4/C5) | A6-S2, B5-S1, H3 private store | Bake off on the smaller 200 GB end of the corpus and say so |
| L21 | **Production disks + burn-in** | Set by C5's BOM. **E** roughly $150–350 per 8–20 TB CMR NAS drive. | Shipping, plus burn-in. **Arithmetic, not a measurement:** one full write-and-read pass of a 16 TB drive at an assumed 200 MB/s average takes about 44 h, and a 4-pattern destructive badblocks run is 8 passes, so about 7–8 days. Drives burn in in parallel. Buying from two sellers to mix batches (C5) means waiting for the slower one. | Owner | After C5's BOM draft (Wave 2) and **before the first real family ingest**. Earlier only if L20 cannot be met. | C5-S3 resilver, A7-S2 audit timing, the first real ingest, the pilot | Run the spikes on the existing pool; the pilot moves later |
| L22 | **UPS**: line-interactive, pure sine wave, USB for NUT | **E** $150–400 | Shipping | Owner | Wave 1, if none (Q-C7) | C5-S2 power-cut test, C7-S2 | C5-S2 recorded as "no result"; unattended recovery stays an untested Gate C risk |
| L23 | Key-ceremony machine (an offline laptop or single-board computer) and a trusted print path | **E** $0–150 | Days | Owner | Wave 1–2 | D2 ceremony dry run, D2-S2/S3, D1 asset list | A live-boot USB on an existing laptop, if D2 judges it acceptable |
| L24 | Printer, card stock, tamper-evident envelopes | **E** $20–50 (printer assumed owned) | Days | Owner | Wave 2 | E5-S1/S2 printed cards and QR sizes, D2-S3, E7 | Print at a local shop, a weaker option for cards that carry secrets |
| L25 | CPU and RAM headroom for the nested-Proxmox staging environment (H1) and test VMs (G2-S4) | $0 if there is headroom; otherwise a RAM upgrade (**E**, depends on the platform) | Days | Owner | Wave 1 (Q-C3, Q-C10) | H1 staging, B7-S2 resets, B1 VM legs, C6-S1 | Run fewer VMs at a time |

### 3.5 Family and field time

| ID | Item | Cost | Lead | Who | Start (prerequisite) | Blocks | Fallback |
|---|---|---|---|---|---|---|---|
| L26 | **One consolidated visit per relative**, covering the E1 census and every FM test (E2 test plan) | Travel only | Depends on relatives' calendars; book weeks ahead | Owner + relatives | Ask at go for slots in weeks 3–7. Needs H3's consent script (owner confirms) and the E1-S1 census script. | E1-S2 iPhone share (feeds OD-01), E2-S1, E3-S1, E4-S1, E5-S1/S3/S4, D6-S3, E7-S1, F3-S1 (owner library sizes) | Video-call interviews; a relative runs the census from a printed guide |
| L27 | Neutral facilitator for interviews (E1-S3) | Owner decides (volunteer or paid) | Weeks | Owner | Name a candidate at intake (Q-F9) | E1-S3 | The owner runs every interview, and the note records the bias |
| L28 | **Wizard-of-Oz nudge pilot: 5 people for 4 weeks** (E3-S2) | $0 | 4 weeks + recruiting | Owner + 5 relatives | Must start by about week 4 to finish before Wave 3. Needs E3's draft nudges. | ADR-0025 | Shorter pilot, with ADR-0025 marked provisional |
| L29 | 7-day soaks (F2-S1: Immich, Ente and Nextcloud on a Samsung or Xiaomi with default OEM settings) | $0 (uses L12a or L12d) | 7 days + setup | Owner | Wave 2 | F2 failure catalogue → E3, B2 | Issue mining only (F2-S2), stated as such |
| L30 | Calendar-bound sandbox runs: A3-S3 real-R2 resume after 24 h and after **7 days**; A7-S4 nightly restore drill for **2 weeks**; the B3-S3 review wait | R2 usage (C4) | 7–14 days each | Agent (on a homelab VM that stays up, not a chat session) | Early Wave 2 (L01 live) | ADR-0009, ADR-0029, ADR-0019 | Shorter runs, marked provisional |
| L31 | **Post an encrypted test stick to a relative and back** (E5-S6) | Postage both ways, which depends on the country (Q-A1). **E** $5–20 each way for a tracked domestic small parcel. | Transit both ways + up to 48 h for the confirmation. Allow 2 weeks. | Owner + relative | Late Wave 2 or the build phase. Needs a kit build (B6, E5). | ADR-0038, A4 USB runbook | Hand-carry the stick and record that postage was not tested |
| L32 | **Combined recovery drill** with a relative who did not write the kit (D2-S3) | $0 | Booked visit, about 2 h (BUD-RECOVERY) | Owner + relative | Before Gate C | Gate C | None. The drill is required. |

### 3.6 Conditional or later

| ID | Item | When it applies | Lead |
|---|---|---|---|
| L33 | Play "12 testers for 14 days" rule | Only if a production track is ever needed (T2). The closed track does not need it. | ≥ 14 days, plus recruiting 12 testers |
| L34 | ISP plan with no data cap | Only if the intake shows a cap below the seed volume (C4) | Depends on the ISP |
| L35 | Safe-deposit box or a lawyer to hold key shares | Owner option under D2/E7 (OD-08) | Unknown; banks may have waiting lists |
| L36 | Paid external crypto and design review | D7 (P2); decide before the pilot or iOS | Weeks to months to book |

## 4. Timeline

| When | Start or order | Calendar waits running |
|---|---|---|
| **Week 0 (go, Wave 0)** | Allowlist; L01, L02, L04; L05 (if the intake settled it); batch 1 (L12a–c, L13, L14, 2× L19); any L03 transfer; L09 DNS; ask for L26/L28 slots | Shipping; domain transfer lock |
| **Weeks 1–2 (Wave 1)** | Batch 2 (L12d–e, L15, L17, rest of L19); L11, L20, L22, L23, L25; L06 if B3 asks; L07 only if B7-S1 needs Developer ID | **L09 observation** (2 weeks); Play identity check; B3-S3 review |
| **Weeks 3–7 (Wave 2)** | L26 visits; **L28 pilot starts by week 4**; L29; L30; L21 ordered after the BOM; borrow L16 and L18; L24 | L28 (4 weeks), L29 (7 days), L30 (7–14 days), L21 burn-in (about 1 week) |
| **Weeks 8+ (Wave 3 → Gate C)** | L08 if OD-09 needs it; L09b; L10; L31; L32 | Azure validation; L09b (2 weeks); L31 postage |

## 5. Cost summary (USD)

| Kind | Items | Amount |
|---|---|---|
| Recurring from go (**V**) | L01 Workers Paid on the sandbox | $5/month minimum, plus usage above the free allowances |
| Recurring, later (**V**) | L10 production Workers Paid | $5/month minimum, plus usage (C4) |
| Recurring, domains | L02 (+ L03 if new) | Registry price per year (not checked; **E** about $10–15 for a .com) |
| Recurring, conditional | L07 Apple $99/year (**V**); L08 Azure $9.99/month (**T2**) | $0 until OD-01 or OD-09 calls for them |
| One-off fee | L05 Play | $25 (**T2**) |
| One-off, batch 1 (**E**) | L04, L12a–c, L13, L14, 2 sticks | about $420–1,900. The low end assumes 2 keys, and that you already own a Windows PC you can reinstall and a Mac. |
| One-off, batch 2 (**E**) | L12d–e, L15, L17, rest of L19, L22, L23, L24 | about $250–1,400. The low end assumes you already own a UPS. |
| One-off, conditional (**E**) | L18 iPhone; L20 scratch drive; L21 disks (C5 BOM) | $0–700; $0–150; set by C5 |
| **Test hardware in total (E)** | batches 1 + 2 | **about $700–3,300**, before homelab disks and any iPhone. Borrowing cuts it a lot. |

For scale on the ceilings asked at intake: at the verified R2 prices, **$50** buys about 3.3 TB of staging for a month ($0.015 per GB-month) or about 11 million write (Class A) operations ($4.50 per million).

## 6. Findings for other workstreams

| # | Finding | Source | For |
|---|---|---|---|
| F1 | **"Limited distribution" is an Android Developer Console account for installs outside Play, not a Play account.** It is free and needs no government ID. It serves up to 20 devices that users authorise through a QR code or link. Accounts can be upgraded from limited to full distribution, but not back. ADR-0002 "Alternatives" calls it a Google Play account, and T2 lists it under its Play item 7. Because installs come from outside Play, Play's automatic updates would presumably not apply (inferred; B3 to confirm). That makes it close to the sideloading ADR-0002 rejected, so OD-10 **touches settled text** if B3 recommends it. | S7 | B3, T2, H1 (decision queue, OD-10 row) |
| F2 | **ADB installs are exempt from developer verification.** Test phones can run spike builds with no Play or Console account. The Play account is needed only for B3-S3, E5-S4 and the referrer test. | S7 (FAQ) | B2, A1, A2, T1 spike 3, G2 |
| F3 | **Creating an app in Play Console registers its package name to the account automatically.** The B3-S3 dry run should use a throwaway package name unless ADR-0019 has already fixed the real one (one-way door #12). | S7 (Play Console guide) | B3, H1 (one-way doors) |
| F4 | **Target API 36 has been required for new apps and updates on Play since 31 Aug 2026.** Developer verification is enforced from **30 Sep 2026** in Brazil, Indonesia, Singapore and Thailand, and globally in 2027. This confirms two items on T2's time-sensitive list. | S7, S8 | T2, B2, B3 |
| F5 | Artifact Signing organisation validation is available in more regions than T2 listed: EU, UK, Australia, New Zealand, Japan, South Korea, Singapore, Switzerland, Norway and Israel, as well as the US and Canada. Individuals are still limited to the US and Canada. Validation cannot be expedited, and billing is not pro-rated. | S12 | T2, B7, OD-09 |
| F6 | Email Service overage is $0.35 per 1,000 emails after the 3,000 included. Sends to verified destination addresses are free. | S4 | C3, C4 |
| F7 | Cloudflare Registrar tries to auto-renew about 30 days before expiry and retries 3 times. A domain is suspended 30 days after expiry and enters redemption on day 40. | S5 | C3, C8 (unattended survivability) |
| F8 | Xcode's free personal team (3 devices, 7-day expiry) is enough for a first B4-S2 background-upload test before paying $99. | S11 | B4 |

## 7. Sources

All accessed 2026-09-29 from the research container. Mirrors are cited as `repo @ branch : path`.

| # | Source | Primary? |
|---|---|---|
| S1 | `cloudflare/cloudflare-docs @ production : src/content/docs/workers/platform/pricing.mdx` | Yes (mirror) |
| S2 | `… : src/content/docs/r2/pricing.mdx`; `… : r2/get-started/index.mdx` (R2 subscription checkout) | Yes (mirror) |
| S3 | `… : src/content/docs/queues/platform/pricing.mdx` (the price table is in a partial that was not fetched; not used for any number) | Yes (mirror, partial) |
| S4 | `… : src/content/docs/email-service/platform/pricing.mdx` | Yes (mirror) |
| S5 | `… : src/content/docs/registrar/index.mdx`, `registrar/get-started/register-domain.mdx`, `registrar/faq.mdx` | Yes (mirror) |
| S6 | `… : src/content/docs/registrar/get-started/transfer-domain-to-cloudflare.mdx` | Yes (mirror) |
| S7 | developer.android.com/developer-verification, `/guides`, `/guides/limited-distribution` (updated 2026-08-20), `/guides/google-play-console`, `/guides/android-developer-console`, `/guides/faq` | Yes (direct) |
| S8 | developer.android.com/google/play/requirements/target-sdk | Yes (direct) |
| S9 | developer.apple.com/programs/enroll/, /programs/whats-included/, /help/account/membership/program-enrollment/, /help/account/membership/enrolling-in-the-app/, /help/account/membership/identity-verification/ | Yes (direct) |
| S10 | developer.apple.com/support/D-U-N-S/ | Yes (direct) |
| S11 | developer.apple.com/support/compare-memberships/ | Yes (direct) |
| S12 | `MicrosoftDocs/azure-docs @ main : articles/artifact-signing/quickstart.md` (ms.date 2026-05-21) and `faq.yml` | Yes (mirror) |
| S13 | T2: [fact-check-adr-0001-0002.md](fact-check-adr-0001-0002.md), items 7 and 10 (the Play fee, the 12-tester rule and the Azure price) | Secondary relay |
| S14 | H1: [sources.md](sources.md), H1-S1 #10 (SAC is enabled only by a clean install) | Relay of a primary mirror |

## 8. Gaps and open questions

| Gap | Why | Who closes it |
|---|---|---|
| Every **E** price | Retail and price sites are blocked from the container, and the session's web-search budget was used up | C4 and C5 with real quotes; the owner at purchase |
| How long Play identity verification takes; whether organisation accounts need D-U-N-S; whether new personal accounts must prove they own a physical Android device; whether a privacy-policy URL is required | support.google.com and play.google.com are blocked (H1 allowlist request) | B3 (secondary only until the allowlist is granted) |
| How long Azure identity validation takes; the $9.99 price was not re-checked | The docs give no duration; azure.microsoft.com is blocked | B7, with the owner recording the actual time |
| Postage cost and transit time | Depends on the owner's country | H2 Q-A1, then E5 |
| Whether SAC behaves the same in a VM; licensing for test VMs | Not verified | B7 and G2 |
| Cloud-drive free-tier sizes for B5-S3 | Not verified | B5 |
| Skeptic review of this note | Not run in Wave 0 | H1 pilot process |

## 9. Owner actions

1. Answer the intake ([owner-intake.md](owner-intake.md)), especially Q-A1, Q-A5, Q-B5, Q-B6, Q-E1–E7 and Q-I4. Those answers settle whether L03, L04, L05, L13, L14 and L22 must be bought or started.
2. Carry out the start list in §2 on the day you say "go".
3. Record the actual waiting time for L05, L06, L07 and L08 here (or tell an agent), because those durations are not documented anywhere reachable.

## 10. Hand-offs

| To | What |
|---|---|
| H1 | Fix the file-name links (`h5-long-lead.md` → this file). Add F1 and F3 to the decision queue (OD-10) and the one-way-door register (#12). Add H5 to the Wave 0 status table. Done in the Wave 0 check. |
| T2 | F1 (limited distribution is outside Play), F4, F5 and F6: corrections and additions to items 7 and 10 |
| B3 | F1, F2, F3; the L05 prerequisites; use a throwaway package name for B3-S3 |
| C4 | The fee lines in §5 and the ceiling arithmetic; replace every E |
| C5 | L21 burn-in timing; buy after the BOM; L22 |
| G2 | L12–L19 as the first device matrix and acquisition list |
| E2 | L26–L32 as the field calendar for the consolidated test plan |
| D2 | L04 must be PIV-capable; L23 |
