# Wave 1 decision brief

- **Date:** 2026-10-07
- **For:** the owner
- **Status:** Open. Nothing below is decided except OD-22 (the drop folder).
- **Sources:** the 17 Wave 1 research notes and Proposed ADRs 0004–0010, 0012, 0019, 0022, 0027 and 0035, plus `docs/security/threat-model.md`. Each item names the note to read for evidence.

## How to use this

Wave 1 produced about 45 decision requests. Many are coupled, so they are grouped into five sittings. Within a sitting, decide the items together.

- **Rec.** is the research recommendation after adversarial review. Several rest on emulated or desk evidence only; that is flagged.
- **⚠ Settled text**: choosing the recommendation changes CLAUDE.md or an Accepted ADR (0001/0002). Only you can approve those changes; each would be written up as a superseding or amending ADR.
- **Default**: what the research and prototype will assume if you have not decided by the deadline.
- IDs: `OD-nn` are in `decision-queue.md`; `DR-xx-n` are new requests H1 still has to number.

---

## Sitting 1: now (intake and housekeeping)

These are overdue and block measured work.

| # | Decision | Rec. | Default | Evidence |
|---|---|---|---|---|
| 1.1 | **OD-14 cost ceilings and beta policy.** Monthly cloud ceiling (BUD-CLOUD), first-backup-month ceiling, abuse ceiling (BUD-ABUSE), billing alerts; may an account-wide spend stop pause all uploads; may beta Cloudflare features be used | $25/month, $50 seed month, $50 abuse (provisional), alerts at $10/$20/$45. Global stop only at BUD-CLOUD + BUD-ABUSE and only after per-device suspension fails. Beta features only with a tested fallback that needs no client update; test-only tooling exempt when pinned | These values, provisionally | `c4-cost-model.md`, `g2-test-and-verification.md` |
| 1.2 | **Your build time (intake Q-B9).** Hours per week over the next 6–24 months | Answer it: it changes the plan more than anything else. At 8 h/week the estimate is roughly 3–6 years to the full v1 (contested estimate) | 8 h/week | `f1-build-adopt-fork-compose.md` §4 |
| 1.3 | **DR-E2-2 stopgaps now.** Protect the family this month with existing tools (phone-vendor clouds, Backblaze, your own copies), only-copy items first; who pays for any extra cloud storage | Yes. It is cheap, reversible, and for some devices the only protection for years. Record it as a time-limited accepted risk (OD-17) | Nothing done | `e2-v1-scope-metrics-pilot.md`, spike `E2-S3` |
| 1.4 | **OD-21 research-data rules**, including "exact file sizes count as family data" | Confirm | Rules applied as written | `h3-research-data-governance.md` |
| 1.5 | **Network and accounts** (actions, not decisions): widen the container's network access; create a Cloudflare sandbox account and a throwaway domain | Do both. Without the sandbox no Cloudflare behaviour has been measured; every C1 result is emulated | — | `sources.md`, `h5-long-lead-items.md` |

---

## Sitting 2: strategy and scope

| # | Decision | Rec. | ⚠ Settled text | Default | Evidence |
|---|---|---|---|---|---|
| 2.1 | **OD-02 build, adopt, fork or compose** | **Build** the Reliquary-specific parts; **adopt** proven components (age format, SQLite, UniFFI if Rust, an existing signed updater, the homelab engine). Fork nothing. None of 13 systems researched meets the trust requirements as shipped, and none of the near misses has a phone client. Decision weights: integrity 35, maintenance 20, effort 20, family UX 15, cost 10, used only to order work inside the build | No | Build | `f1-…md`, ADR-0005 |
| 2.2 | **DR-F1-1 upkeep budget.** Development upkeep (estimated 60–120 h/year, contested) breaks BUD-SUPPORT (≤ 2 h/month) | Add a separate development-upkeep budget line; keep BUD-SUPPORT for operations | No | — | `f1-…md` |
| 2.3 | **DR-E2-1 delivery steps.** D0 stopgaps → D1 concierge (you seed by USB) → D2 minimal apps → D3 full kit = v1, each platform gated on a proven restore | Adopt. Fallback: declare D2 as v1 if the hours are low | No | Adopt provisionally | ADR-0004 |
| 2.4 | **DR-E2-4 first app** | Desktop first provisionally; switch to Android first if the census shows few computers | No | Desktop | ADR-0004 |
| 2.5 | **OD-19 Android documents in v1** | Photos and videos only; you copy phone documents by cable during D1 visits. Revisit after the census | No | Media only | ADR-0004, ADR-0019 |
| 2.6 | **OD-01 iOS** | Keep the settled deferral, add the iPhone bridge through a family computer ("via this computer", never "iPhone covered"), and build the 16 iOS constraints into the core now. Reopen only if the census shows a large unbridgeable iPhone share (the 40 % trigger is yours to set) | No | Deferral, no bridge | `b4-ios-decision.md` |
| 2.7 | **DR-E2-5 importing cloud exports** (Google Takeout, iCloud exports) as admin-only tooling | Allow, admin-side only | **Yes**: CLAUDE.md "files on the device only" | Not allowed | ADR-0004 |
| 2.8 | **DR-B4-3 icloudpd at the homelab** for relatives with no computer | No by default; per-relative, consented, time-limited exception only | **Yes**: same line | No | `b4-…md` |

---

## Sitting 3: protocol and trust (decide together)

The core finding: as ADR-0001 §4 is written, a malicious or compromised Cloudflare can make a device believe a file is stored at home when it is not (silent loss), and can make honest devices take the blame. This was reproduced in a model of the most charitable reading of the ADR (`spikes/D1-S2`), and independently by the encryption spike.

| # | Decision | Rec. | ⚠ Settled text | Default | Evidence |
|---|---|---|---|---|---|
| 3.1 | **OD-04 amend the ingest protocol** | **B.** "Safe" only when the device holds a homelab-signed receipt verified under a pinned key; device-signed records; homelab verifies before committing; per-upload staging keys; record-first completion; only the homelab commits and deletes staging; devices re-ask with backoff; signed heartbeat. Revisit a transparency log (option C) in Wave 2 | **Yes**: ADR-0001 §2 (one sentence) and §4 steps 1, 2, 4. Draft text: threat model Appendix A | B, with throwaway keys; Gate A blocked | D1, A3, `threat-model.md`, ADR-0009 |
| 3.2 | **DR-F3-2 the "already have it?" answer.** A stolen device holding the family dedup secret can ask whether a relative owns a given file. Rate limits failed in simulation | Never answer "present" across people for files below a size threshold (C); better, for nobody below it (D) if the extra small-file uploads are affordable | Possibly: whether "dedup across all users" means skipping uploads or only storing once | C | `f3-security-literature.md`, spike `F3-S2` |
| 3.3 | **DR-A1-1 how the family key is applied** (one-way door). Kind 03 = HMAC over the whole file (settled wording); kind 01 = HMAC over the file's SHA-256 (half the hashing, key rotation without re-reading files); kind 04 = nested (rotates like 01, leaks like 03) | Kind 01 if you accept that a leaked key can test lists of known SHA-256 values; otherwise kind 04. Per-person dedup keys (F3 option F) are the strongest cross-person defence; consider them here | **Yes** for 01/04/per-person keys: CLAUDE.md and ADR-0001 §2 | Nothing hashed with production secrets | `a1-content-identity.md`, ADR-0006, `docs/spec/identifiers.md` (111 vectors) |
| 3.4 | **DR-A1-2 epoch tag** in every dedup ID | Yes (2 bytes; stale devices get a clear "update key" error) | No | Yes | ADR-0006 |
| 3.5 | **DR-D2-1 when to rotate the dedup secret** | On every revocation for loss, theft or compromise, if 3.3 = kind 01 and the rotation test meets its targets; otherwise only on confirmed compromise | No | — | `d2-…md` |
| 3.6 | **DR-A3-2 receipt format** (one-way door) | Per-device batch receipts as C2SP signed notes, with fields reserved for a later transparency log | No | — | ADR-0009 |
| 3.7 | **DR-A3-3 device safety valve.** If the device that claimed an upload dies, may another device re-upload after a wait? | Yes: 12 h (72 h or ask on metered-only devices), only while the homelab heartbeat is fresh; a retry budget ends in a nudge to the person and you | No; needs a BUD-TTS exception | — | ADR-0009 |
| 3.8 | **DR-C1-6 staging write protection.** Presigned URLs are reusable, so an uncommitted staged object can be rewritten | Rule decided now, applied at Gate B: if real measurements show Worker-proxied uploads are reliable and affordable, staging becomes create-only; otherwise presigned uploads with the risk accepted | No | — | ADR-0010 |
| 3.9 | **DR-C1-1 Worker language** | TypeScript; small formats implemented twice and pinned by shared test vectors | No | TypeScript | ADR-0010 |
| 3.10 | **DR-C1-3 how the homelab learns of new uploads** | A Worker event feed polled about every 30 s plus bucket listing (no Cloudflare API token at home) | **Yes**: ADR-0001 §1 names Queues | Queues as written | ADR-0010 |
| 3.11 | **DR-C1-2 buckets** (one-way door) | Two: `rq-ingest` (never expires) and `rq-restore` (expires) | No | — | ADR-0010 |
| 3.12 | **DR-C1-4 API domain** (one-way door) | A dedicated Reliquary domain, plus a bootstrap host elsewhere, so a Cloudflare lockout cannot take down your main domain's email | No | — | ADR-0010 |
| 3.13 | **DR-C1-7 staging cap** | Refuse new uploads above about 1.3 TB staged from the first deploy (interim) | No | Alerts only | ADR-0010, `c4-…md` |

---

## Sitting 4: encryption and keys (decide together; mostly Gate A one-way doors)

| # | Decision | Rec. | ⚠ Settled text | Default | Evidence |
|---|---|---|---|---|---|
| 4.1 | **OD-06 post-quantum from day one** | Yes (age's ML-KEM hybrid recipients). Rust implementation passed 853/853 compatibility vectors; cost 0.13–1.2 % per file. Conditional on a low-end phone speed test. Without it, every copy uploaded is exposed to "harvest now, decrypt later" | No | No production keys until decided | ADR-0007, `a2-object-envelope.md` |
| 4.2 | **OD-08 recovery key** | Every stored file also encrypted to an offline recovery key R; R wrapped by a passphrase split into SLIP-39 cards, 2-of-3 by default; holders chosen after the family roles work; recovery with unmodified open-source tools | Coupled with 4.3 | — | ADR-0008 |
| 4.3 | **DR-D2-4 trust wording.** With recovery cards, any 2 card holders with access to the ciphertext can read everything, not only you | Amend the wording, with family consent handled by D6 | **Yes**: CLAUDE.md trust model ("the admin holds the private key") | — | ADR-0008 |
| 4.4 | **DR-D2-3 what the recovery bundle unlocks** | Read-only access; successors who want to keep the system running do a re-key ceremony | No | — | ADR-0008 |
| 4.5 | **OD-07 homelab at-rest posture** (one-way door; no default) | "Offline archive key" (A′): stored files are encrypted to an archive key X and R that are never on the always-on ingest machine, so a compromised ingest VM cannot read the store. Costs: attended restores and audits in a separate environment. Several pieces are unbuilt designs | No | None; Gate A blocked | ADR-0012, `a6-…md` |
| 4.6 | **DR-A6-2 meaning of "prefer an existing, proven format"** | The proven format is age v1 per object (optionally in an OCFL layout), not a backup engine such as restic | Interpretation only; confirm | — | ADR-0012 |
| 4.7 | **DR-A6-4 / DR-A6-5 verification and audit under A′** | Write-time self-checks plus attended sampled decryption; monthly keyless bit-integrity audit instead of a full decrypt audit | Changes the BUD-AUDIT wording | — | ADR-0012 |
| 4.8 | **DR-F3-1 / DR-A2-4 size padding** | Pad stored sizes (about 1.1–1.2 % storage on public data), provisional until your own library is measured | No | Space reserved, decided later | F3, A2 |
| 4.9 | **DR-A2-3 device signatures** | Classical (Ed25519) device signatures in v1 as a recorded risk, review in 2030 | No | — | ADR-0007 |
| 4.10 | **DR-A6-3 disk thieves see file names (hashes) and sizes** | Accept and record | No | — | ADR-0012 |

---

## Sitting 5: family, privacy and distribution (decide together)

The research found a conflict: a small redemption web page for phone-only relatives (ADR-0019) cannot coexist with "never learn the homelab key from a page the cloud serves" (ADR-0027, threat model SR-02). Under both recommendations, a relative with only a phone would need you to enter them manually. Decide 5.1–5.3 as one choice.

| # | Decision | Rec. | ⚠ Settled text | Default | Evidence |
|---|---|---|---|---|---|
| 5.1 | **OD-03 where names and emails live** | The homelab keeps names and emails and sends reminder emails itself through Cloudflare Email Service; the cloud keeps only your alert address. Conditional on a real sandbox test | **Yes**: CLAUDE.md "Email" bullet; ADR-0002 §2 | Cloud, as written | `d6-…md`, ADR-0027 |
| 5.2 | **OD-10 Android channel** | Google Play closed track, personal account, your own app signing key. Fallback: an off-Play build under the same account | Fallback only: **Yes**, ADR-0002 §4 | Play closed track | ADR-0019 |
| 5.3 | **OD-11 Play account-deletion rule vs keep-forever** | An admin-actioned deletion request, confirmed out of band, never triggered by a device | Possibly | — | ADR-0019 |
| 5.4 | **OD-05 enrolling more devices** | Phones get the homelab key only from an in-app scan of the enrolled device's QR; second computers use a pairing step that resists guessing plus an installer check; you and the person are notified of every new device | Possibly ADR-0002 §3 (may be a clarification) | — | `d1-threat-model.md` |
| 5.5 | **OD-09 code-signing spend** | Windows signing (Azure Artifact Signing about $9.99/month if eligible, otherwise an OV certificate), plus a free stable self-signed identity on macOS; Apple Developer ID only if needed | **Yes**: CLAUDE.md "Code signing"; ADR-0002 §5 | No spend, with Smart App Control PCs excluded from the pilot | ADR-0022, `b7-…md` |
| 5.6 | **EU data residency** | Ask at intake whether any relatives are in the EU or UK | No | — | `d6-…md` |

---

## Accepted-risk register (OD-17)

Gate A cannot pass without these signed. Recommended for acceptance unless noted.

| Risk | Recommendation |
|---|---|
| AR-04 Cloudflare can deny service (detected, not prevented) | Accept now |
| AR-05 Cloudflare sees sizes, timing, IPs, ID equality, names and emails | Decide with 4.8 and 5.1 |
| AR-06 (narrowed) presence-answer exposure that remains after 3.2 | Decide with 3.2 |
| AR-08 a compromised ingest VM can disclose what it can decrypt and sign false receipts | Revisit at Gate A with 4.5 |
| AR-09 a file deleted on the device before its receipt cannot be repaired later (visible, not silent) | Gate C |
| AR-D2-1 any 2 recovery-card holders can read the archive | Only with 4.3 |
| Play/Google can push an app update to family phones | Accept with mitigations |
| Cloudflare Email Service keeps recipients and subjects for 31 days | Accept with disclosure in the family charter |
| Classical device signatures (4.9) | Accept, review 2030 |
| Vendor-readable stopgaps (1.3) | Accept, time-limited |

---

## Settled text that would change

| Item | CLAUDE.md | ADR-0001 | ADR-0002 |
|---|---|---|---|
| 3.1 ingest protocol | — | §2, §4 | — |
| 3.3 dedup construction (01/04/per-person) | Encryption trust model | §2 | — |
| 3.10 notification path | — | §1 | — |
| 4.3 recovery cards | Encryption trust model | — | — |
| 5.1 email at the homelab | Email | — | §2 |
| 5.2 off-Play fallback | Onboarding (Play) | — | §4 |
| 5.4 enrollment | — | — | §3 (maybe) |
| 5.5 signing | Code signing | — | §5 |
| 2.7 / 2.8 cloud exports | v1 data sources | — | — |

---

## Not decisions: contradictions the research must reconcile

Found by the batch consistency reviews; these are fixed in Wave 2 or by H6, not by you.

1. Uploads slower than R2's 7-day multipart abort: A3 says try a longer abort rule first; C1 treats 7 days as a hard ceiling and makes segment checkpoints primary.
2. When the signed record must reach the cloud for single-file uploads (A3 spec vs C1 API).
3. Error-code names and the homelab feed format differ between the ingest spec and the API outline.
4. The homelab commit steps differ between A3 (decrypt to a temp file) and A6 (streaming, no plaintext temp file, extra self-checks).
5. Metadata record batches (A2) vs per-record archiving (A3, A6).
6. Size padding is specified differently by F3 and A2; the homelab-key pin is described differently in several places.
7. Queue-less commit (C4) vs ADR-0001's queue wording (G2).
8. Registries still describe iOS as a CLAUDE.md vs ADR-0002 conflict; that was resolved in commit 6f9f2bb.
9. BUD-SUPPORT means operations in some notes and development upkeep in others (resolved by 2.2).

## What is still unmeasured

- Every Cloudflare behaviour (R2 conditional writes, token revocation, D1 capacity, proxied uploads): emulated only, until a sandbox account exists.
- Phone hashing speed, battery and post-quantum cost: kits ready, no phone run.
- Windows Smart App Control and macOS self-update behaviour: kits ready, no real-machine run.
- The family census and iPhone share: kits ready, not run.
