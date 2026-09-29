# Traceability matrix

- **Owner:** H1 builds it; H6 closes it at each gate.
- **Last updated:** 2026-09-29 (first version; every row is **Open** because no workstream has delivered yet)
- **Sources:** `CLAUDE.md` (settled requirements, properties, open decisions), ADR-0001 and ADR-0002 (open questions), `docs/research/PLAN.md` §2–§4

Every CLAUDE.md requirement and every open question in ADR-0001/0002 maps to the workstream and deliverable that close it. **Lead** is the single owner. Workstreams in brackets only supply input. A row is closed when its deliverable is Accepted (for ADRs) or merged (for specs, notes and runbooks). The research phase is not done while any row is an orphan (PLAN §6 item 6).

Flags: **ORPHAN** means no workstream owns it. **DOUBLE** means two workstreams claim the same artifact. **CONFLICT** means the settled text disagrees with itself or with an ADR and an owner decision is needed.

## 1. CLAUDE.md settled requirements and properties

| ID | Requirement (short) | Lead | Closing deliverable | Gate | Flag |
|---|---|---|---|---|---|
| R-01 | v1 platforms: Windows, macOS, Linux | B1 (B7) | ADR-0017, ADR-0022 | C | |
| R-02 | v1 platform: Android | B2 (B3) | ADR-0018, ADR-0019 | C | |
| R-03 | v1 platform: iOS | B4 (E2, E1-S2) | iOS section of ADR-0004; OD-01 | A | **CONFLICT**: ADR-0002 §4 defers iOS → OD-01 |
| R-04 | Phones are first-class; desktop-only stacks are out | T1 | ADR-0003 | before B-track | |
| R-05 | iOS background limits shape the mobile design | B4 | iOS constraints memo to T1 (before ADR-0003 is accepted) | before B-track | |
| R-06 | Users are non-technical family members | E2 (E1, E6) | ADR-0004, census summary, ADR-0039 | A / C | |
| R-07 | Owner administers centrally; users never touch configuration | C8 (E3) | ADR-0032, ADR-0024 | C | **CONFLICT** risk: pause/exclude controls → OD-12 |
| R-08 | Near-zero-effort device enrollment (QR) | E5 (D3) | ADR-0038, ADR-0014 | C | **CONFLICT** risk: device approval → OD-05 |
| R-09 | Scale: 2–10 TB, 10–25 devices, several people | C4 (C1, A6, C5) | `c4-cost-model.md`, C1-S3, ADR-0012/0013, ADR-0030 | B / C | |
| R-10 | Server side on Linux/Proxmox, as containers or VMs | C6 (C5) | ADR-0031, ADR-0030 | P2 / C | |
| R-11 | Devices upload to R2 staging from anywhere | C1 (A3) | ADR-0010, ADR-0009 | A / B | |
| R-12 | Homelab never exposed; outbound connections only | C1 (A3, C6) | ADR-0010 (records the Workers VPC / Tunnel rejection), ADR-0031 egress rules | B | |
| R-13 | No AWS | H6 (C1, C3) | Architecture overview consistency check; ADR-0010, ADR-0026 | C | No single lead. Enforced by the consistency reviewer (PLAN §5.1 stage 6) |
| R-14 | USB-drive transport is required | A4 (B6) | ADR-0011, `docs/spec/bundle-format.md`, USB runbooks | A / C | |
| R-15 | LAN direct is optional | A4 | ADR-0037 | P2 | |
| R-16 | Strong per-device credentials | D3 | ADR-0014, API auth spec | C | |
| R-17 | Rate limiting on the cloud API | C2 (D3) | Quota matrix in ADR-0014 | C | |
| R-18 | Devices can only append, never delete or rewrite | A3 (C1, D4) | ADR-0009, ADR-0010 key layout; proved by the D4 attack suite (D4-S1..S4) | A / C | |
| R-19 | Content and metadata encrypted on the device to the homelab public key, before data leaves the device | A2 | ADR-0007, `docs/spec/object-format.md` | A | |
| R-20 | Devices cannot read any backup data | A2 (D2) | ADR-0007 recipients, ADR-0008 | A | |
| R-21 | Cross-user dedup via HMAC(family secret, content); the cloud sees opaque IDs only | A1 (F3) | ADR-0006, `docs/spec/identifiers.md`, F3 attack matrix | A | |
| R-22 | Admin holds the private key; privacy is against outsiders, not the admin | D2 (D6, D1) | ADR-0008, ADR-0027 consent spec, accepted-risk register (OD-17) | A / C | |
| R-23 | Whole-file dedup across all users on plaintext content | A1 | ADR-0006 | A | |
| R-24 | Clients keep a local hash cache | A1 (B6, B5, B2) | ADR-0006 cache-key contract, ADR-0021 client DB schema | A / C | |
| R-25 | Source locator, filename, mtime recorded; plaintext only at the homelab | A2 (A5, H4, A6) | ADR-0007 metadata record, `docs/design/data-model.md`, ADR-0013 | A / B | |
| R-26 | Keep forever | A6 (A7, C4) | ADR-0012, ADR-0029, capacity forecast | A / C | **CONFLICT** risk: Play account deletion → OD-11 |
| R-27 | Deleting on a device never removes the backed-up copy | A3 (H4) | ADR-0009 tombstone and sighting events; history fields in `data-model.md` | A | |
| R-28 | Pruning is a manual admin action only | A6 (C8, D4, D6) | ADR-0012 refcounting, ADR-0032, D4 pruning gate, ADR-0027 departure policy | A / C | |
| R-29 | Auto-discovery proposes what to protect | E4 (B5) | ADR-0023, ADR-0020 | C | |
| R-30 | Plain-language per-person backup health | E3 (A3, E6) | ADR-0024 copy deck, A3 state → vocabulary map | C | |
| R-31 | Proactive nudges: stale device, not yet backed up, storage issues | E3 (C3, C4) | ADR-0025, ADR-0026 | C | |
| R-32 | No admin dashboard in v1 | C8 | ADR-0032 | C | **CONFLICT** risk: read-only gallery → OD-13 |
| R-33 | v1 sources: files on the device, including the phone photo library | B5 (B2, E2) | ADR-0020, ADR-0018, ADR-0004 | C | |
| R-34 | Source layer pluggable for iCloud, Google Photos, email and social exports | B5 | Source-plugin interface spec; B5-S5 roadmap matrix | C | |
| R-35 | Restore is admin-performed in v1; no end-user restore UI | A8 (C8) | ADR-0028, `docs/runbooks/restore.md` | C | |
| R-36 | v1 focus is getting data safely in | E2 | ADR-0004 | A | |
| R-37 | Restores re-encrypted to the target device key, staged in an expiring R2 prefix | A8 (C1, D3) | ADR-0028, ADR-0010 `restore/` layout, ADR-0014 (authentic device keys) | C | |
| R-38 | Off-site copy of the homelab is out of scope for now | D1 (A6) | Accepted-risk register (OD-17); ADR-0012 keeps a future off-site copy easy | A / C | |
| R-39 | Data integrity over everything; verifiable and restorable; restore is first-class | A7 (A8, G2, A0) | ADR-0029, ADR-0028, ADR-0035; Gate B run (A0) | B / C | |
| R-40 | Tolerant of intermittent connectivity | A3 (B6, A4) | ADR-0009, ADR-0021, ADR-0011 (rarely-online devices) | A / C | |
| R-41 | Low resource impact: throttling, battery and metered-network awareness | B1 (B2) | ADR-0017, ADR-0018; BUD-DESK, BUD-BAT-D | C | |
| R-42 | Say plainly what is and is not backed up; flag stale backups, unreachable server, changed-but-not-uploaded files | E3 (B5, C7) | ADR-0024 gap reasons, ADR-0020 change detection | C | |
| R-43 | Client = background daemon + light UI (tray or menu bar on desktop) | B1 (T1, E3) | ADR-0017, ADR-0003, E3 surface map | C | |
| R-44 | Cloud never sees plaintext content, plaintext hashes or filenames | D1 (A1, A2, D6, B8) | Threat register (D1-S1), `docs/security/data-inventory.md`, B8 telemetry data dictionary | A / C | |
| R-45 | Homelab pulls, decrypts, verifies, stores, keeps the plaintext catalog, ingests USB bundles | A6 (A3, A4) | ADR-0012, ADR-0013, ADR-0009, ADR-0011 | A / B | |
| R-46 | Storage engine: prefer an existing, proven format | A6 | ADR-0012 knockout screen and bake-off | A | |
| R-47 | Bundles are transport-agnostic (R2, USB, possibly LAN) | A4 | ADR-0011 | A | |

## 2. CLAUDE.md open decisions

| ID | Open decision | Lead | Closing deliverable | Gate | Flag |
|---|---|---|---|---|---|
| OPEN-1 | Client stack | T1 | ADR-0003 | before B-track | |
| OPEN-2 | Homelab storage engine | A6 | ADR-0012 | A | |
| OPEN-3a | Device enrollment (QR), per-device keypair, credential issuance and revocation | D3 (E5) | ADR-0014, ADR-0038 | C | |
| OPEN-3b | Homelab keypair custody | D2 | ADR-0008, key-ceremony runbook | A | |
| OPEN-3c | Dedup-secret rotation | A1 (D2) | ADR-0006 (ID-side rotation), ADR-0008 (custody and rotation trigger) | A | **DOUBLE** (see §4) |
| OPEN-4 | Whether to build LAN direct | A4 | ADR-0037 | P2 | |

H6 proposes the CLAUDE.md "Open decisions" update once these close.

## 3. Open questions in the Accepted ADRs

| ID | Open question | Lead | Closing deliverable | Gate | Flag |
|---|---|---|---|---|---|
| Q1-1 | ADR-0001: homelab storage engine | A6 | ADR-0012 | A | Same as OPEN-2 |
| Q1-2a | ADR-0001: generating and storing the homelab keypair | D2 | ADR-0008 | A | |
| Q1-2b | ADR-0001: rotating the dedup secret | A1 (D2) | ADR-0006, ADR-0008 | A | **DOUBLE** (see §4) |
| Q1-2c | ADR-0001: enrollment by QR code | D3 (E5) | ADR-0014, ADR-0038 | C | |
| Q1-3 | ADR-0001: presigned UploadPart and a part-size policy | C1 (C1-S1) for UploadPart; B6 for the policy | C1-S1 results in ADR-0010; part-size policy in ADR-0021 | B / C | **DOUBLE** risk on part size (see §4) |
| Q1-4 | ADR-0001: resumable uploads vs `age` randomness | A2 (T1 spike 2) | ADR-0007 resumable content-encryption decision | A | |
| Q1-5 | ADR-0001: is LAN direct worth building | A4 | ADR-0037 (A4-S5) | P2 | Same as OPEN-4 |
| Q2-1 | ADR-0002: email provider (Cloudflare Email Service vs Resend vs Postmark) | C3 | ADR-0026 | C | Blocked on OD-03 |
| Q2-2 | ADR-0002: Play fee, 12 testers for 14 days, permanent closed track, opt-in, limited distribution | B3 (H5) | ADR-0019, OD-10; account started as a long-lead item | C | |
| Q2-3 | ADR-0002: does the Play Install Referrer survive the closed-track opt-in | E5 | E5-S4 result in ADR-0038 | C | |
| Q2-4 | ADR-0002: Windows Smart App Control, then the signing decision | B7 (T1 spike 1, D5) | B7 "cost of not signing" table, ADR-0022, OD-09 | C | |
| Q2-5a | ADR-0002: invite and QR lifetimes | E5 (D3) | ADR-0038 within D3's entropy table (ADR-0014) | C | **DOUBLE** risk (see §4) |
| Q2-5b | ADR-0002: how the admin generates and prints cards (CLI vs admin page) | C8 (E5) | ADR-0032 invite lifecycle; card template in ADR-0038 | C | **DOUBLE** risk (see §4) |

### Commitments in the Accepted ADRs that are not listed as open questions but still need an owner

| ID | Commitment | Lead | Closing deliverable | Flag |
|---|---|---|---|---|
| C-01 | ADR-0001 §1, §6: optional warm-cache window for staged objects and recent uploads | — | — | **ORPHAN**. No workstream decides whether to keep a warm cache or how long. Proposed lead: C1 (ADR-0010), with C4 for cost and A7 for its use as a repair source |
| C-02 | ADR-0001 §1: reconciliation so an outage longer than queue retention loses nothing | A3 | ADR-0009 | |
| C-03 | ADR-0001 §4: "already have it" grants no read rights; future self-service restore returns only what the device uploaded | A3 (A8) | ADR-0009, ADR-0028 provenance | |
| C-04 | ADR-0002 §2: email verification on signup; nudges only after verification | C3 | ADR-0026 verification-link design | Depends on OD-03 |
| C-05 | ADR-0002 §2: name, email and activity timestamps stored in plain text in the cloud | D6 | ADR-0027, `data-inventory.md` | OD-03 may change it |
| C-06 | ADR-0002 §3: other-devices wizard, iPhone "not yet supported" memory, ongoing nudges | E5 (E3, B4) | ADR-0038, ADR-0025 | |
| C-07 | ADR-0002 §5: self-updates signed with the project's own offline key | D5 | ADR-0015 | |
| C-08 | ADR-0002 §5: ad-hoc re-signing on macOS after self-update; Defender and AV heuristics | B7 | B7-S1, B7-S4, ADR-0022 | |
| C-09 | ADR-0002 §5: build the stick from locally built artifacts, format exFAT | B7 (D5, E5) | ADR-0022 stick layout, ADR-0015 build provenance | |

## 4. Artifacts claimed by more than one workstream

PLAN §2.1 says every normative artifact has exactly one owner. These artifacts appear in the "Owns" line of two workstreams. The proposed lead follows §2.1 where it names one, and otherwise follows the workstream that does not say "with". **These are proposals for H6 and the owner to confirm.** Nothing has been decided here.

| Artifact | Claimed by | Proposed lead | Proposed split |
|---|---|---|---|
| ADR-0033 telemetry, crash reporting, alerting | B8 and C7 | C7 (author) | B8 writes the client section and the data dictionary; C7 authors and submits the ADR |
| Default include/exclude rules file | B5 and E4 | E4 (§2.1 lists it under ADR-0023) | B5 implements and supplies OS exclusion hints |
| Dedup-secret rotation | A1 and D2 | A1 for ID-side mechanics (epochs, re-derivation) | D2 for custody, rotation trigger and ceremony |
| Multipart part-size policy | A2 (segment alignment), B6 (policy), C4 (cost scenarios), T1 spike 4 | B6 (ADR-0021) | A2 sets the segment-alignment constraint; C4 and T1 supply numbers |
| Invite and QR lifetimes | D3 (entropy and rate-limit table) and E5 (usable lifetimes) | E5 (ADR-0038) | D3 sets the maximum safe lifetime; E5 picks the value within it |
| Card template and printing | E5 (card template) and C8 (invite printing) | E5 for the card design | C8 for the generating and printing tool |
| USB stick layout | B7 ("with E5") and E5 (kit spec) | B7 for the file layout | E5's kit spec references it |
| Printed break-glass / doomsday kit | D2 (co-owned runbook) and E7 (doomsday-kit spec) | D2 for the cryptographic runbook | E7 for the people-side kit contents |
| Restore runbook | A8 (`docs/runbooks/restore.md`) and C8 (restore-request runbook) | A8 | C8's restore-request runbook links to it |
| Consent script | H3 ("with E1") and E1 ("with H3") | H3 (data governance) | E1 adapts it for interviews |
| Golden corpus spec | H3 ("with A5") and A5 | A5 (§2.1 lists it under ADR-0016) | H3 sets the storage and consent rules |
| Privacy policy for Play | D6 ("with B3") and B3 ("with D6") | D6 (ADR-0027) | B3 adapts it for the Play listing |
| Email templates | C3 ("with E6") and E3 ("with C3 and E6") | E3 (copy) | C3 owns the sending mechanics and DNS; E6 reviews language |

## 5. Summary at 2026-09-29

- 47 requirements, 6 open-decision rows and 13 ADR open-question rows are mapped. Every one has a lead except **C-01 (warm cache): ORPHAN**.
- **CONFLICT** items waiting on the owner: R-03 (OD-01), plus risks on R-07 (OD-12), R-08 (OD-05), R-26 (OD-11) and R-32 (OD-13).
- 13 artifacts are claimed by two workstreams (§4). H6 should settle them before Wave 2 fans out.
- Every row is Open. H6 updates the table at each gate.
