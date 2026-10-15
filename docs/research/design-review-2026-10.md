# Reliquary design review, October 2026

**Status:** review for the owner; not an ADR. Nothing here changes settled text until the owner decides (section 9).
**Inputs:** five critiques (goal-fit, threat-model, architecture, product, two-class, reversibility), two defences (design, family-risk), three fact-check passes, the repo at `8adaac6`, and the owner's decisions OD-23, OD-24 and OD-25 of 2026-10-15 (`docs/research/decision-queue.md` l.39–41).
**Evidence rule:** statements that carry weight below cite a repo path and line or a URL with the date it was read. Anything that could not be checked from a primary source is marked **unverified**. Every hours figure in this document, including F1's, is an uncalibrated estimate (`docs/research/f1-build-adopt-fork-compose.md` l.39, l.286–290: "No measured hours-per-line rate exists").

---

## 1. Verdict

**No. The current design does not serve the owner's goals, and the fault is the assistant's, not the owner's.**

The owner's goals, in the owner's words, are: relatives' photos, videos, scans and documents end up safely on the homelab; the owner administers centrally and can restore everything; family members never touch configuration; a USB stick plus one printed code enrols a person; privacy against outsiders; keep forever; a compromised or ransomwared device cannot destroy history; a professional feel; cross-user hash dedup is a priority (OD-23); shared photos need no application-level encryption (OD-24); set-and-forget updates and a scheduled "anything new?" audit (OD-25).

What went wrong, in order:

1. **ADR-0001 was written by the assistant and marked Accepted on the same day as the owner interview, and it rewrote the owner's requirements.** Commit `7dcc65c` (2026-09-29 06:19 UTC, "Record settled requirements from owner interview") recorded: "a public, internet-exposed endpoint (not VPN-only)", "data is encrypted client-side; the owner (admin) holds a recovery/escrow key", and "Prefer building on an existing, proven backup repository format/server rather than inventing a storage format" (`git show 7dcc65c:CLAUDE.md` l.20, l.37–38). Thirty minutes later, commit `fc9303c` ("Add ADR-0001", author `Claude <noreply@anthropic.com>`) replaced those lines with "the homelab is never exposed and only makes outbound connections", "devices cannot read any backup data", and "Cross-user dedup uses HMAC(family secret, content)" (`git diff 9fb9bc8 fc9303c -- CLAUDE.md`). CLAUDE.md then labelled them "Decided with the owner; do not relitigate without asking" and the research plan forbade reopening them (`docs/research/PLAN.md` l.9: "Nothing in this plan reopens a settled requirement"). Fact-check caveat: `7dcc65c` is also assistant-authored, so the "owner's words" are the assistant's transcription of the interview.

2. **A consequence was promoted to a requirement and then used as the test for everything else.** ADR-0001 l.34, under "Consequences of this scheme": "Devices hold only the homelab *public* key, so they cannot read any backup data (not even their own). This enforces 'devices append only' by construction." That sentence became CLAUDE.md l.45 and then F1's trust knockout 1 (`docs/research/f1-build-adopt-fork-compose.md` l.12–17), which rejected all thirteen existing systems in fifteen configurations (l.165–184). The owner has now said, for the main data class, the opposite (OD-24). The adopt/compose path was foreclosed by a criterion the owner never set.

3. **Putting Cloudflare in the data path created an adversary, and Wave 1 spent itself defending against it.** Every heavy item in Wave 1 (section 2) traces to "a third party holds the bytes and the index": per-file encryption to the homelab key, the custom resumable age encoder, homelab-signed receipts, pinned trust bundles, claim/commit, reconciliation, the HMAC dedup oracle and its defences, two buckets, two D1 databases, a bootstrap host, post-quantum recipients from day one, size padding. Of 26 threats in the register, 25 name a malicious Cloudflare side (AP2) or a device holding the dedup secret (AP3–AP5); only T-26 does not (`docs/security/threat-model.md` l.182–207, fact-checked). Disk failure, fire, bit rot and owner death have no threat row; ransomware false-"safe" (T-23) is "Wave 2"; the off-site copy is "Settled" out of scope (l.278).

4. **The result is a plan that protects nobody for years.** F1's own revised estimate is 1,260–2,520 focused hours, 3.0–6.1 years at 8 h/week, with concierge USB seeding at 17.6–35.2 months and the first apps at 35.2–70.4 months (`f1-build-adopt-fork-compose.md` l.31, l.277–279). E2 says the family stays on vendor clouds "for years, not months", "1–5 years for some devices" (`docs/research/e2-v1-scope-metrics-pilot.md` l.20, l.315). Those stopgaps violate "privacy against outsiders including the cloud provider" more thoroughly than any open-source system F1 rejected. The accepted ADR-0004 still quotes the withdrawn 2.6–5.1-year figure (`docs/adr/0004-v1-scope-platforms-non-goals.md` l.24, l.96); F1 l.281 says E2 "must re-derive its milestones", which has not happened.

5. **The research programme was sized for a funded team and made the owner the bottleneck.** About 472k words of Markdown, 28 kits, 38 spike directories, 52 workstreams, 40 ADR numbers, ~420 planned agents, ~45 owner decision requests in five sittings, zero product code, every Cloudflare, phone and Windows behaviour emulated only (`docs/research/wave1-decisions.md` l.10, l.151–156; `PLAN.md` l.1864–1872; repo counts 2026-10-15). The one-hour owner intake, including build hours Q-B9, is still unanswered (`docs/research/owner-intake.md` l.4, l.46).

**What the defences got right, and this review keeps:**

- The owner's literal sentence was "not VPN-only". Any direct-to-homelab direction over Tailscale or WireGuard needs the owner to re-read that sentence as "relatives never configure a VPN", which an auth key on the printed card and (later) an embedded node can satisfy. This is an owner decision (section 9), not an engineering one.
- On phones, an overlay network is not free: one active VPN per user on Android, a system consent dialog, OEM battery killers, and no verified way yet to embed a tailnet node inside a Kotlin app (section 7, spike S1).
- Uploads while the homelab is down are genuinely lost by removing staging (a dropped phone during an outage keeps nothing but local copies). Cheap and mitigable, but real.
- Immich is not a Class S store for this family: its duplicate check is per user, it lets users delete originals, and it has no documents. It is a viewer and a stopgap, not the archive.
- Removing the relay saves roughly a fifth of F1's hours, not half; what makes v1 long is four client platforms built by one person. The two-class model and adopt-first are what shorten the schedule, not the transport change alone.
- Custody of a long-lived key is the single most likely way a keep-forever archive is lost in year 15. SLIP-39 split custody of the at-rest key is cheap and should stay; what goes is the per-object recipient machinery around it.
- A thirty-year archive must be readable with stock tools and no Reliquary code. Class S as plain files satisfies this automatically; the Class P engine must be chosen by the same rule.

**The direction** (section 6) is the owner's two-class model, built direct to the homelab over an authenticated tunnel, with the adopted pieces (Tailscale, ZFS, restic/rest-server, Immich as a viewer and interim phone uploader) doing what they are good at and Reliquary built as the assistant and the small Class S store on top. Protection for the owner's household starts in weeks; the first relatives follow within a quarter; the kit and the single app arrive incrementally instead of after a 3–6-year gate.

---

## 2. The complexity cascade

Each row names a decision, the work it generated, where the repo records the causal link, and F1's hours where a row exists (`f1-build-adopt-fork-compose.md` l.250–270). "Relay-induced" means the item has no reason to exist once the device talks to the homelab directly over an authenticated channel; "class-induced" means it disappears when Class S is plaintext (OD-24); "owner-retired" means OD-23 removed it.

```
owner goals: at-home copy, admin escrow, privacy vs outsiders, device cannot destroy history
        │
        ▼  ADR-0001 §1 (assistant, 2026-09-29): third party holds bytes + index
        ├── §2 encrypt every file to homelab key  ──► "devices cannot read" (l.34) ──► F1 knockout 1 ──► 13 systems rejected
        │        └── age randomness vs R2 multipart ──► custom resumable encoder, tag journal, keystream guard
        ├── §2 cloud dedup index ──► HMAC(family secret) on every device ──► presence oracle, poisoning, epoch tags,
        │        per-person keys, rotation, F3-S2 simulation, SR-15/SR-21, ADR-0006
        ├── §4 cloud can lie about "committed" ──► receipts, pinned trust bundles, device-signed records,
        │        record-first, claim/commit, reconciliation by listing, hash-chained feed, TLA+ model (ADR-0009)
        ├── 7-day multipart abort, 14-day Queue retention ──► segment checkpoints, reconciliation
        ├── cloud bill + abuse surface ──► cost model, spend meters, kill switch, two buckets, two D1s,
        │        API domain + bootstrap host (ADR-0010)
        ├── ciphertext crosses a third party ──► harvest-now-decrypt-later ──► PQ hybrid from day one, padding
        └── restore via R2 ──► re-encrypt to device key, expiring prefix
```

| Root decision | Downstream work generated | Repo evidence of the link | F1 hours (est.) | Fate under the recommended direction |
|---|---|---|---|---|
| Cloudflare R2/Workers/D1 in the data path (ADR-0001 §1) | Worker + D1 control plane, presigned URLs, claim/commit, two buckets, two databases, API domain, bootstrap host | `docs/adr/0001-cloud-staging-on-r2.md` l.14–19; `docs/adr/0010-control-plane-topology-and-api-v1.md`; `wave1-decisions.md` 3.11–3.12 | 100–200 (Worker+D1) | Relay-induced: removed |
| Cloud cannot be trusted to say "committed" (ADR-0001 §4; D1) | Homelab-signed receipts, pinned trust bundles, device-signed records, record-first completion, hash-chained feed, reconciliation by listing, TLA+ model (7.9M–38.6M states) | `docs/research/d1-threat-model.md` summary; `docs/adr/0009-ingest-protocol-receipts-reconciliation.md` l.46–48, l.75 | part of homelab ingest 120–240 and Rust core 160–320 | Relay-induced transport half removed; durable-commit contract, verify-before-ack, idempotent commit, keep-until-acked, no-silent-loss kept (defence point, correct) |
| Encrypt every file to the homelab key before upload (ADR-0001 §2) | "Devices cannot read any backup data" → F1 knockout 1; resumable age encoder (~150 lines on RustCrypto), Poly1305 tag journal, keystream-reuse guard, 2.4k-line spike; A2 envelope ADR-0007 | ADR-0001 l.34; `docs/research/content-encryption-format.md` l.18, l.21, l.366, l.385; F1 l.12–17 | ~half of Rust core 80–160; part of specs 40–80 | Class-induced for Class S: removed. Stock age kept for USB bundles in the post. Class P encryption delegated to an engine |
| Cross-user dedup decided in the cloud (ADR-0001 §2) | HMAC family secret on every device, presence oracle, poisoning, scoping (DR-F3-2), epoch tags (DR-A1-2), per-person keys (DR-A1-1), rotation (DR-D2-1), SR-15/SR-21, F3 (107 KB), A1 (65 KB, 111 vectors), ADR-0006 | `wave1-decisions.md` l.55–58; `threat-model.md` l.192, l.194, l.281 (AR-06) | inside Rust core and security verification | Owner-retired (OD-23) and relay-induced: removed. Plain SHA-256 "have it?" against the homelab's verified catalog replaces it (section 2a) |
| Ciphertext crosses a third party for decades | PQ hybrid recipients from day one (pre-1.0 crates, custom X-Wing stanza, PQ device keys), size padding | `wave1-decisions.md` l.74 (4.1), 4.8; `docs/research/f3-security-literature.md` l.299–303 | part of Rust core, specs | Removed for Class S. Stock `age -pq` (Go age ≥ 1.3.0) for sneakernet bundles; transport PQ recorded as accepted risk with a 2030 review |
| Compromised ingest VM must not read the store | Offline archive key A′, attended restores in a separate environment, X audits, rotation ceremonies | `docs/adr/0012-homelab-at-rest-posture-and-storage-engine.md` l.116, l.223, l.267 | restore pipeline 40–80; owner time unmeasured | Removed (Class S is admin-visible plaintext by OD-24). ADR-0012 Decision 5 (store survives its writer) kept |
| R2 7-day multipart abort, Queue 14-day retention | Segment checkpoints, reconciliation, "needs a USB stick" fallback | ADR-0001 l.74–75; `wave1-decisions.md` "Not decisions" item 1 | inside ingest protocol | Removed; HTTP range/tus resume instead |
| Metered public cloud surface | Cost model, spend meters, kill switch, billing-alert decision (Sitting 1.1), denial-of-wallet (T-15) | `docs/research/c4-cost-model.md` l.10–12 | monitoring 20–40 (partly) | Removed; $0 marginal cloud cost (Tailscale Personal, see section 5 for plan caveats) |
| Restore through R2 | Re-encrypt to device key, expiring prefix | ADR-0001 §6; CLAUDE.md l.50 | 40–80 | Removed; admin restores over the tunnel or by stick |
| "Nothing reopens settled text" governance | 52 workstreams, ~420 agents, 40 ADR numbers, ~45 owner decisions, Gate A blocking the first byte on reversible choices | `PLAN.md` l.9, §4.2, §5.3; `docs/research/one-way-doors.md` | n/a | Replaced by section 7's spikes and section 8's stop list |

**Arithmetic (fact-checked against F1 l.250–270):** the rows that exist only because of the relay sum to about 280–560 h, 22 % of F1's 1,260–2,520. The rows every direction keeps (desktop app 150–300, Android app 200–400, onboarding 60–120, update signing 30–60, assistant logic 80–160, tests/CI 80–160, packaging/ops 60–120, admin CLI 50–100, monitoring 20–40, specs 40–80, CLI 30–60) sum to 800–1,600 h, or 1.9–3.8 years at 8 h/week on their own. The design defence is right that the relay is not the whole schedule problem. The schedule problem is a bespoke four-platform client built by one person before anyone is protected. That is why the recommended direction adopts the clients it can (Immich's phone app, restic, Tailscale's app) and builds Reliquary as the layer on top.

### 2a. What the owner's dedup decision removes from Wave 1

OD-23 (`decision-queue.md` l.39) says cross-user hash dedup is a priority and a relative learning that another relative holds a given hash is not a concern. Applied:

| Wave 1 item | Status after OD-23 | Note |
|---|---|---|
| DR-F3-2 presence-answer scoping (Sitting 3.2) | **Withdrawn** | Existed to stop intra-family probing |
| DR-A1-2 epoch-tagged dedup IDs, ID kinds 01/03/04 (3.4; ADR-0006) | **Withdrawn** | Same purpose plus rotation |
| DR-A1-1 per-person dedup keys (3.3) | **Withdrawn** | Same |
| DR-D2-1 dedup-secret rotation on revocation (3.5; ADR-0008 Decision 7) | **Withdrawn** | No family secret on devices in the recommended direction |
| F3-S2 rate-limit simulation and M-27..M-50 conditions | **Closed as history** | The finding "only removing the answer works" is moot when the answer is allowed |
| SR-15 (secret delivery per enrollment path), SR-21, T-11, T-13 | **Withdrawn** | Secret no longer exists |
| ADR-0006 content identity | **Reduced to plain SHA-256** with its test vectors (`docs/spec/identifiers.md`, kind 00 only) | Keep the vectors; drop HMAC and epoch parts |
| HMAC blinding of the cloud index | **Moot under direct-to-homelab**; keep as a one-line option if any third-party index is ever reintroduced | Exposure (a) in the owner's note |
| Dedup poisoning (a lying index makes a device skip an upload that was never stored) | **Resolved by construction under direct-to-homelab**: the homelab answers "already have SHA-256 X" only for bytes it hashed itself after receipt, so the answer is the receipt. Under any third-party index, the current design's rule survives: "present" counts only with a homelab-signed token (threat-model.md l.118 V-11, l.222 SR-06; f3 M-27). | Exposure (b). The design defence is right that receipts were the poisoning answer; they are only unnecessary when the verifier is on the other end of the connection |
| What "dedup" now means | The device computes SHA-256 locally (hash cache keyed by locator/size/mtime/file ID, ADR-0001 §3, kept), asks the homelab "have it?", uploads only misses, and records a sighting (member, device, path, mtime) for every hit so provenance is complete | Transfer saving and storage saving both achieved; the duplicate share is still unmeasured (ADR-0009 l.70; c4 l.21) and spike S5 measures it |
| Residual privacy | A device learns that *someone* in the family holds the file. Accepted by OD-23. A device credential must not be able to list other people's catalogs; the "have it?" endpoint answers only for hashes the device presents | Write-only API design, spike S3 |

---

## 3. Goals vs artifacts

Every "settled requirement" in CLAUDE.md (l.36–51), classified. **Goal** = the owner asked for it; **Artifact** = a consequence of a design choice the assistant made; **Mixed** = an owner goal stated through a mechanism the assistant chose.

| CLAUDE.md line | Requirement (abridged) | Class | Recommendation |
|---|---|---|---|
| l.36 Platforms: Windows, macOS, Linux, Android; iOS deferred but not precluded; phones first-class | Goal | **Keep.** Note that adopting Immich's apps for Class S covers iPhones immediately, which the bespoke path cannot for years |
| l.37 Non-technical users; owner administers centrally; users never touch configuration | Goal | **Keep.** Make it the pass/fail test for the tunnel spike (S1): a relative must not log into a VPN product by hand |
| l.38 USB stick + printed one-use expiring invite code; name and email only; "your other devices" wizard; self-install from stick; Play closed track; stick doubles as seeding transport | Mixed | **Keep the experience, reword the mechanics.** The code can carry a tailnet auth key and a device token. "No password" survives if the account is a Reliquary account; adopted components (Immich, restic) need credentials the app holds for the user. Play closed track stays only for a bespoke Android app |
| l.39 No Apple/Windows code signing; self-updates signed with the project's offline key | Mixed | **Keep the signed-update rule (it is what makes OD-25 safe).** Revisit "no signing" against Windows Smart App Control (`docs/adr/0022-desktop-packaging-and-self-update.md` l.22, l.32): an unsigned stick that cannot launch on a clean Windows 11 PC is not a professional feel. Store-signed adopted apps avoid it |
| l.40 Set and forget; bundled engine also self-upgrades | Goal (OD-25) | **Keep.** Weighs toward an engine the app can ship and update as a binary (restic) rather than a separately installed runtime (duplicity) |
| l.41 Email for verification and nudges; name, email and device activity plaintext in the cloud control plane | Mixed | **Reword:** drop "cloud control plane". With no cloud, these live at the homelab; an email provider still sees addresses |
| l.42 Scale 2–10 TB, 10–25 devices | Goal | **Keep** |
| l.43 Linux/Proxmox; containers or VMs | Goal | **Keep** |
| l.44 Connectivity: upload to R2 from anywhere; homelab never exposed, outbound-only; no AWS; USB required; LAN optional; cloud API under attack; devices append-only | Mixed | **Reword.** Goals inside it: upload from anywhere, never an open inbound port, no AWS, USB transport, append-only devices. Artifacts: R2 staging, "treat the cloud API as under attack". Proposed text: "devices reach a homelab ingest service only over an authenticated end-to-end tunnel (no inbound port on the home network); the homelab holds no delete or overwrite endpoint for device credentials; USB bundles are a required transport." Owner must accept the re-reading of "not VPN-only" (section 9) |
| l.45 Encryption trust model: encrypt to homelab key; devices cannot read any backup data; HMAC dedup; admin holds private key; privacy against outsiders including cloud provider | Artifact (ADR-0001 l.34) wrapping two goals | **Reword per class.** Goals: admin escrow; privacy against outsiders. Artifacts: "devices cannot read", HMAC, per-file envelopes for Class S. Proposed: "Class S travels inside an end-to-end encrypted channel and rests on an encrypted, snapshotted ZFS dataset; the admin can read it. Class P is encrypted on the device by the chosen engine; key custody per OD-24 decision." Delete "devices cannot read any backup data" |
| l.46 Deduplication: whole-file, across all users, plaintext content; local hash cache; locator/filename/mtime recorded | Goal (reaffirmed OD-23) | **Keep; reword** "plaintext content" to "SHA-256 of the file as received, answered by the homelab from its verified catalog". Applies to Class S only; Class P repositories are per member |
| l.47 Keep forever; device deletion never removes the copy; pruning manual admin only | Goal | **Keep.** Enforce at the API (no delete endpoint) and at the storage layer (ZFS snapshots with holds, releasable only by a separate credential; `zfs-hold.8`, read 2026-10-15) |
| l.48 Assistant features: discovery, plain-language health, nudges, scheduled audit; no admin dashboard | Goal (OD-25) | **Keep.** This is the product. It is transport-independent and was never the problem |
| l.49 Data sources: files on device incl. phone library; cloud/export pulls on roadmap; pluggable | Goal | **Keep** |
| l.50 Restore: admin only in v1; delivered by re-encrypting to the device key and staging in an expiring R2 prefix | Mixed | **Keep "admin only in v1"; delete the R2 mechanism.** Restores go over the tunnel or on a stick |
| l.51 Off-site copy out of scope | Goal as stated, but the largest loss vector | **Reword to a precondition:** "an encrypted off-site replica (raw ZFS send or encrypted copy) exists before the first relative's only-copy data lands". The owner's separate plans may satisfy it; the review needs to see them |
| l.26–30 (Properties) "Client-side encryption before data leaves the device" | Mixed | **Reword per class:** Class P yes; Class S "encrypted in transit end to end and at rest at the homelab". Owner confirms the reading (section 9) |

---

## 4. Threats, re-weighed

Likelihood and impact are judged for a family homelab over a keep-forever horizon, not for a SaaS. Mitigation cost is relative to the owner's 8 h/week.

| Threat | Likelihood | Impact | Wave 1 treatment | Mitigation and cost | Decision |
|---|---|---|---|---|---|
| Never shipping; family unprotected for years | **High** (F1: 3–6 years; one builder) | **Total** for whatever is lost meanwhile | Not a numbered threat; appears as E2 pre-mortem row 1 | Adopt-first protection this quarter (section 6); weeks | **Promote to the top risk** |
| Phone dropped/stolen/wiped before its photos reach home | High | High (only copy) | T-22/AR-09 "visible, not silent" | Fast first upload after enrolment; honest "not yet safe" state; never suggest "free up space" before ack (SR-28). Under direct-to-homelab the window includes homelab outages: queue locally, retry, show it | **Keep, cheap.** Spike S2 measures background upload |
| Relative deletes photos (app or OS), expects them gone or not | High | Medium | T-22 | Keep-forever at API + ZFS snapshots with holds; Immich interim: trash + snapshots, admin re-import | **Keep** |
| Ransomware on a device uploads garbage or churn with honest acks | Medium | Medium (old versions survive keep-forever; store floods; status poisoned) | T-23 "Wave 2" | Write-only credentials; per-member quota (c4 Q11); mass-change detection in the assistant; held snapshots | **Promote to v1**, a few days of work |
| Homelab disk pair failure, fire, theft, flood | **Certain over decades** without a replica | Total | AR-03 "Settled" out of scope | ZFS mirror + scrub + off-site encrypted replica (raw send only: non-raw send of encrypted datasets had corruption bugs #12014/#11688, fixed in 2.2.8/2.3.3 per GitHub release pages read 2026-10-15; one Oct-2025 comment on docs #494 disputes raw-send safety too) | **Promote to precondition** |
| Owner dies, is incapacitated, or loses the key | Certain over decades | Total | AR-02 "listed"; AP9 Wave 2; SLIP-39 proposed | One at-rest key (and the Class P admin share) split 2-of-3 with SLIP-39 (Final standard, five implementations, repo drill 48/48 in `spikes/D2-S2`), one printed heir page, a drilled non-author recovery (BUD-RECOVERY ≤ 2 h). ZFS lets the passphrase change without re-encrypting (`zfs-load-key.8`) | **Keep, re-scoped** from per-object recipients to custody of two secrets |
| Compromised homelab host or ingest service | Low–medium | High | AP8 Wave 2; A′ posture | Ordinary hardening; snapshots and holds under a separate credential; replica pulls, never pushed; catalog rebuildable from the store (A6-S4). Confidentiality of Class S against the host is moot by OD-24 | **Drop A′ and attended restores; keep ADR-0012 Decision 5** |
| Stolen device credential reads other people's data | Medium | Medium (privacy) | AP3–AP5 oracle work | Write-only per-device API; "have it?" answers only for presented hashes; fast revocation; Immich interim: per-user accounts | **Keep the API rule; drop the oracle defences** (OD-23) |
| Tailscale account takeover or coordination-server compromise enrols an attacker node | Low | High if the ingest API trusts the network alone | Not evaluated (tailscale.com was blocked in D1) | Device-level credentials in addition to tailnet identity; pin the homelab's key from the printed card (SR-02/SR-27 principle, kept as one sentence); Tailnet Lock (**unverified**, page unreachable); Headscale as exit | **Keep as a new row; cheap** |
| Malicious Cloudflare poisons dedup or lies about commit | Very low | Bounded (caught at homelab, re-upload) | 25 of 26 threats, SR-01..SR-31, receipts, model check | None needed when there is no Cloudflare | **Drop with the relay** |
| Relative probes which files another relative holds | Low | Nuisance; owner accepts it | DR-F3-2, epoch tags, rotation, F3-S2 | None | **Dropped by OD-23** |
| Harvest-now-decrypt-later on ciphertext in transit | Very low (nation-state recording of a household) | Low for photos | PQ from day one (Gate A blocker) | `age -pq` for anything leaving the house as ciphertext; accepted-risk line for the WireGuard channel (Tailscale's data plane is classical; **unverified**, PQ page unreachable) with 2030 review; symmetric Class P repositories are PQ-safe at rest by construction | **Defer to a register line** |
| Metadata leakage to Tailscale (device names, IPs, online times) | Certain | Low | Counted against Cloudflare as AR-05-style | Same class as the email provider seeing addresses; accept, record | **Accept** |
| Bytes altered on the way in (fixers, re-encodes, storage-template renames) | Medium | Irreversible (identity and dedup break) | E2-S3 measured; A9 rule | "Keep bytes exactly as received; sidecars as linked metadata" as a hard ingest rule; Immich interim must never own or move originals | **Promote to a hard rule** (family-risk defence, correct) |
| Provenance never recorded | Certain if skipped | Irreversible | one-way door #6 | Log raw first-seen time, source path, device, mtime, EXIF from the first byte | **Keep as a rule, not a format freeze** |
| Smart App Control blocks the unsigned stick | Medium | Enrolment fails on that PC | ADR-0022 "blocker to resolve" | Store-signed adopted apps now; signing decision before any bespoke Windows binary ships | **Keep open; decide before D2** |

---

## 5. Directions compared

Common facts used below (all read 2026-10-15 unless noted):

- **Tailscale.** tsnet embeds a node in a Go program with a userspace gVisor stack, no daemon, no root, auth key or OAuth client, custom `ControlURL` (`tsnet/tsnet.go`). It is Go-only; libtailscale is a C wrapper with no platform list or maturity statement; Android embedding is unverified (a third-party Flutter plugin reports Android "local only (WIP)" because `net.Interfaces()` needs CAP_NET_ADMIN; **unverified upstream**). Android allows one active VPN per user and shows a consent dialog (developer.android.com/develop/connectivity/vpn). DERP relays carry only WireGuard ciphertext and are "a last resort" (`derp/derp.go`); relayed throughput is QoS-limited and **unmeasured for this project**. Plan: snippet-level reads of tailscale.com/pricing say the Personal plan is free for 6 users with unlimited user devices since the April 2026 re-pricing; the page body was unreachable, so **confirm on tailscale.com before relying on it**. Headscale (v0.29.2, 2026-07-01) is the self-hosted exit, maintained by two people with full-time jobs who state a burnout-avoidance model (headscale `docs/about/faq.md`).
- **Cloudflare Tunnel.** Outbound-only (Tunnel index page), but the visitor's TLS ends at Cloudflare and cloudflared makes a second TLS connection to the origin (ssl/concepts.mdx; tunnel origin-parameters partial), and the proxied body limit is 100 MB on Free/Pro (workers/platform/limits.mdx; error-413 page). Cloudflare sees plaintext Class S. Not a candidate for Class S unless client encryption returns.
- **Immich.** Duplicate check scoped to the uploading user (`asset.repository.ts` `getByChecksum*` filter `ownerId`; FAQ: "no requirements for assets to be unique across users"); images and videos only (supported-formats.md); users can trash and permanently delete, trash default 30 days, emptying deletes originals (`trash.service.ts` `deleteOnDisk: true`; system-settings.md); a permanent-delete shortcut exists (docs say Ctrl+Del, the web shortcuts modal shows Shift+Del); no admin lock on user deletion found (**absence unverified**); "Immich does not handle filesystem backups for you" (backup-and-restore.md); background upload is OS-scheduled with battery and Background App Refresh caveats (mobile-backup.md) and a reproducible OEM failure report (#26115, Redmi, Android 15); 38 stable releases and two majors in 12 months (`spikes/F1-S1/evidence/cadence.csv`); external libraries mounted `:ro` cannot be deleted from the UI (libraries.md).
- **restic / rest-server.** `--append-only` prevents deletion and modification of existing backups; `--private-repos` confines each user to their own repository (rest-server README). Under append-only a device can still write snapshots with forged `--time`/`--host`, run `key add` and print the master key (`spikes/F1-S1/README.md` l.45–47; restic issue #22057 open). Several passwords per repository, all unlocking the same master key; a leaked key cannot be revoked without `copy` (restic `design.rst`). restic 0.19.1 and rustic 0.11.4 restore each other's repositories 176/176 both ways (`spikes/A6-S5`).
- **ZFS.** A held snapshot cannot be destroyed (EBUSY, `zfs-hold.8`); native encryption leaves names, sizes, holes and dedup tables in the clear and allows keyless scrub; passphrase change needs no re-encryption (`zfs-load-key.8`).
- **a6cas.** The repo's content-addressed store prototype: 0 violations over 400 kills, 130 LazyFS-emulated power cuts and 100 disk-full trials, byte-identical catalog rebuilds (`spikes/A6-S3`, `A6-S4`). Today it writes age objects; a plaintext variant is untested.

### 5.1 The directions

**A. Current design** (ADR-0001 + Wave 1 Sittings 3–4).
Goals met: escrow; privacy vs Cloudflare; append-only by construction; outbound-only; upload while homelab down; USB. Goals missed: time to protection (M2 at 17.6–35 months, M3 at 35–70 months); Class S shareable and unencrypted (OD-24) contradicts ADR-0001 l.34; owner upkeep 5–10 h/month vs BUD-SUPPORT ≤ 2 (F1 l.301; `budgets.md` l.27); attended restores; vendor-cloud stopgaps for years. Effort: 1,260–2,520 h (+20 % = 1,512–3,024). First protection: concierge at 1.5–3 years; phones at 3–6. Operating burden: highest (ceremonies, X audits, Cloudflare controls). Vendor risk: Cloudflare in the data path, unbounded abuse spend (c4 l.12). Reversibility: everything but printed material is reversible, but nothing exists. Relatives: unsigned binaries, Play test-track opt-in, SLIP-39 holder roles, caveat-laden status; no viewing or sharing.

**B. Current design simplified** (keep R2 staging and per-file encryption; cloud honest-but-curious; dedup kept via blinded index plus signed "present" tokens; drop PQ, SLIP-39-per-object, A′, second bucket/DB, bootstrap host).
Goals met: as A on paper; removes Sittings 3–4 oracle work. Missed: still years; still five toolchains; still the resumable encoder and 7-day abort; Class S plaintext requirement (OD-24) still contradicts the design unless Cloudflare is allowed to see photos, which the owner's privacy line forbids. Effort: perhaps 900–1,800 h (20–30 % off). First protection: 1–2 years concierge, 2.5+ years phones. Burden: medium-high. Vendor risk: Cloudflare. Does not address the root cause.

**C. Direct-to-homelab, own client and own server over Tailscale/WireGuard** (one class, no cloud; client-side encryption dropped or kept by owner choice).
Goals met: all owner goals including the exact kit and wizard; synchronous "stored at home" ack; SHA-256 dedup from the homelab's verified catalog; write-only API; snapshots. Missed: uploads need the homelab up; iOS still deferred until an Apple membership; phone background upload still the owner's problem; family waits 6–12 months for a desktop daemon and 12–24 for Android. Effort: ~660–1,320 h (architecture critic's cut; the "half of F1" figures in other critiques are arithmetically wrong, section 2). Burden: medium. Vendor: Tailscale (Headscale exit). Reversibility: high. Relatives: one app eventually; nothing until it ships.

**D. Adopt existing systems behind Tailscale with ZFS snapshots plus a thin assistant** (Immich for photos on all four platforms and iPhone; restic/rest-server for documents on desktops; status/nudge job reading Immich's API and ZFS).
Goals met: homelab copy within weeks; iPhones covered now; admin reads everything; privacy vs outsiders (WireGuard end to end); keep-forever at the storage layer; store-signed apps (no SAC problem); sharing for Class S (albums, partner sharing). Missed: **no cross-user transfer dedup (owner's priority, OD-23)**; users can delete originals (recovery = admin snapshot re-import); "backed up" badge means uploaded, not verified; no documents in Immich; two apps and two logins per phone (Tailscale + Immich) with the one-VPN rule; name-and-email-no-password enrolment not available; Immich churn (38 releases/yr, breaking majors) to track; professional feel is Immich's. Effort: 20–60 h setup; 150–400 h assistant layer over time; 1–3 h/month upkeep (estimates). First protection: owner's devices in days; first relative at the first visit. Burden: low-medium. Vendor: Tailscale + Immich roadmap. Reversibility: good if originals are byte-exact and provenance is exported nightly; poor if Immich's database becomes the only record. Relatives: polished gallery, but a system that violates three settled requirements (hash dedup, device cannot destroy at the app layer, verified-safe).

**E. The owner's two-class design, built direct** (Class S: plaintext photos/videos to a small custom content-addressed store with SHA-256 "have it?" and ZFS snapshots; Class P: wrapped append-only encrypted engine; one assistant app; Tailscale/WireGuard; Immich later as a read-only viewer).
Goals met: every stated goal including hash dedup in transfer and storage, admin escrow for Class S (and Class P under custody b/c), append-only at API and storage, keep forever, outbound-only in substance, one app, kit unchanged in experience (code carries tunnel key material), set-and-forget via a bundled engine the app updates, scheduled audit in the app, class decided by discovery with override and a Private drop sub-folder. Missed: uploads need the homelab up; Class P on Android depends on a spike (may be desktop-only in v1, consistent with ADR-0004's Android media-only default); cross-member dedup does not apply to Class P repositories; privacy vs outsiders for Class S rests on the tunnel plus disk encryption, not application crypto. Effort: ~650–1,300 h for the full assistant (two-class critic's cut; uncalibrated); first protective slice (desktop S + desktop P, concierge enrolment, no Android) ~150–300 h. First protection: owner's household in 2–4 weeks after spikes; desktop relatives in 4–9 months; Android Class S uploader 9–15 months. Burden: medium (own store and server to maintain, but no cloud, no ceremonies). Vendor: Tailscale (Headscale exit), restic (two implementations). Reversibility: high for Class S (plain files, rehash in a day); Class P custody is the one real one-way door. Relatives: one app, honest status, sharing later through a viewer.

**F. E with adopted components as the interim and as permanent parts (recommended).**
Same destination as E, sequenced so protection never waits for Reliquary code:
- *Phase 0 (weeks):* Tailscale on the homelab and the owner's devices; ZFS datasets with hourly/daily snapshots under holds and an off-site raw-send replica; restic + rest-server `--append-only --private-repos` per member for Class P on desktops, with custody decided first; Immich on its own snapshotted dataset as the **interim** Class S uploader for phones (per-user accounts, trash on, `:ro` exports later) with a designed exit: byte-exact originals, nightly plain-file export of per-asset provenance, hash-based import into the Reliquary store when it exists (storage dedup recovered at import; transfer dedup is lost only during the interim).
- *Phase 1 (months):* Reliquary ingest service (plaintext a6cas layout + SHA-256 "have it?" + catalog + write-only device credentials + synchronous verify-and-ack) and the desktop assistant (discovery, class rule, drop folder with Private sub-folder, health aggregated across Immich, restic and the Reliquary store, nudges, scheduled audit, invite redemption, signed self-update, restic binary bundled and updated). Desktop photo folders and the owner's archive go straight into the Reliquary store. Immich is re-pointed to read the store `:ro` as the family viewer.
- *Phase 2:* Reliquary Android uploader for Class S (or keep Immich's app if spike S2 shows it reliable enough and the exit import works), Android share-to-Reliquary for documents, embedded tunnel if spike S1 passes, Class P on Android if spike S4 passes.
Goals met: everything in E plus time to protection measured in weeks; the family's bytes never pass through a vendor cloud at any stage; iPhones covered from Phase 0 through Immich. Missed: two systems during the transition (Immich and the Reliquary store) for a year or more; relatives install two phone apps until an embedded tunnel exists; the owner must run and upgrade Immich (pin versions, snapshot before upgrade, read notes quarterly). Effort: Phase 0 20–40 h of owner setup; Phase 1 ~300–600 h; Phase 2 +150–300 h per platform uploader. Burden: low in Phase 0, medium after. Vendor: Tailscale, Immich (interim only), restic. Reversibility: high, provided the exit rules are enforced from day one. Relatives: protected this quarter with store-signed apps; the single Reliquary experience arrives on desktop first.

### 5.2 Ranking

| Rank | Direction | Why |
|---|---|---|
| 1 | **F** | Only direction that meets the dedup priority, the two-class model, append-only, keep-forever, escrow and set-and-forget *and* protects people this quarter. Its costs (two systems in transition, two phone apps for a while, homelab uptime) are operational and reversible |
| 2 | E | Same destination, but the family waits 4–15 months for the first Reliquary byte, with no plan for phones meanwhile other than vendor clouds |
| 3 | C | Meets the goals eventually; lacks the class split (so either keeps a crypto core for everything or drops Class P encryption the owner wants); 1.5–3 years to phones |
| 4 | D | Fastest protection, but as a destination it violates the owner's dedup priority and lets users destroy originals at the app layer; right as Phase 0 of F, wrong as the end state |
| 5 | B | Trims the oracle work but keeps Cloudflare, the encoder, the years and the contradiction with OD-24 |
| 6 | A | Internally rigorous about the wrong adversary; 3–6 years; already partly invalidated by OD-23/24 |

### 5.3 Class P engine choice

Screen: cross-platform incl. Android; embeddable or bundle-and-self-update (OD-25); append-only at the server; key custody options; maturity and churn; public format spec with a second implementation (the thirty-year rule); whether F1-S1 already measured it.

| Engine | Platforms | Embed / bundle | Server append-only | Custody options | Format independence | Maturity / churn | F1-S1 measured? | Verdict |
|---|---|---|---|---|---|---|---|---|
| **restic + rest-server** | Win/mac/Linux static binaries; Android builds exist as Termux packages (0.19.1), no official client | Bundle a binary the app updates; rustic_core as a future library | `--append-only` (no delete/modify); `--private-repos`; device can still forge `--time`/`--host`, `key add`, read master key | Symmetric master key; several passwords per repo → admin escrow by `key add`; member-only by withholding; leaked key needs `copy` | Written design (`design.rst`); restic ↔ rustic restore each other 176/176 | Mature; 0.19.1 | **Yes** (probes + source checks) | **Recommended** |
| rustic_core (library) | Win/mac/Linux targets; no Android target in release-cd.yml | Embeddable Rust library (brings UniFFI back if used) | Same server as restic | Same as restic | Same format | "early development stage… API subject to change"; 5 breaking 0.x minors/12 m | Yes (churn) | Watch; spike S4 decides between bundled restic and embedded rustic_core |
| Kopia + repository server | Win/mac/Linux (+BSD ports); no Android | Bundle binary | APPEND ACL blocks delete; default ACL FULL on own snapshots; ACL change took effect after restart in F1-S1 | Server holds the repository password and sees plaintext (F1 K4); device 2 read device 1's bytes by object ID in F1-S1 | One implementation; keyed IDs | Mature | **Yes** | Second choice, only if custody (b) admin escrow is chosen; weaker thirty-year story |
| Borg | Linux/mac; Windows "experimental" (installation.rst) | Bundle (SSH-based) | `borg serve --append-only` via forced command | Symmetric repo key | One implementation | Mature | Partly (F1 matrix) | Decline for Windows relatives |
| duplicity (owner's suggestion) | POSIX + Python 3.9+, "best used under GNU/Linux" (man page); no Android (no Termux package); rel.3.2.2 2026-10-14 | Python + GnuPG runtime: not bundleable in a set-and-forget app on Windows | None at the server; full+incremental chains, periodic fulls needed | GnuPG public-key mode is attractive (device holds only the public key) | Stock gpg+tar for full volumes; incrementals need librsync and intact chains | Mature but chain-fragile | No | **Decline** |
| rclone crypt | All desktops; Android via Termux (1.75.2) | Bundle binary | `rclone serve restic --append-only --private-repos` exists for the restic protocol; crypt alone has no versioning | Symmetric | Documented format; one implementation | Mature | Partly | Use as a restic REST server if wanted; not as the engine |
| Duplicacy | Win/mac/Linux | Bundle | Writers can prune; no server mode | RSA for content, metadata readable by every writer | Non-OSI licence (free personal use) | Mature | No | Decline |
| Plakar | Win/mac/Linux | Bundle | `rm -apply` through a no-delete server hid the snapshot in F1-S1 | — | No format spec | Young | **Yes** | Decline |

**Recommendation:** restic format behind rest-server `--append-only --private-repos`, one repository per member on its own ZFS dataset with a quota, snapshots with holds as the real backstop (the engine's append-only is partial, as F1-S1 measured). The app bundles the restic binary and updates it with the signed self-update (OD-25). "Safe" for Class P is declared only after the homelab runs `restic check --read-data-subset` on the member's repository, never from the client's exit code. Admin `forget` policies never run automatically (restic #22057, open).

### 5.4 Class P key custody: an owner decision

| Option | What it means | Recovery if the member loses everything | Privacy from the admin | Re-key / re-index later | Engine fit |
|---|---|---|---|---|---|
| (a) Member only | Passphrase exists only on the member's devices and printed card | **None.** Admin cannot help heirs, cannot re-key after a leak, cannot re-index. H5 fails for Class P | Full | Impossible without the member | restic (withhold the admin key) |
| (b) Admin escrow (CLAUDE.md l.45 as written) | Admin holds a key to every member's repository | Admin restores | None (like Class S) | Admin can `copy`/re-key | restic `key add`; Kopia server mode natural |
| (c) Split custody | Member passphrase + an admin-held second key whose passphrase is itself the SLIP-39-split secret (same 2-of-3 cards as the at-rest key) | Admin, or any two card holders, can recover | Privacy from a casual admin; not from a determined one with two cards | Admin can re-key with two cards present | restic `key add` (one command) |

**Recommendation:** (c) as the default, with (a) offered as an explicit per-member opt-in carrying a printed warning that nobody else can ever recover the files. The family-risk defence's point stands: "hold on to my personal private files" most often means passports, deeds and records, which are exactly what heirs need after the member is gone. Decide before the first real Class P byte; changing later means re-keying every member repository. This is one of the three genuine one-way doors left (with printed material and the Android package/signing key).

---

## 6. Recommended direction

**Adopt direction F: the owner's two-class model, direct to the homelab over an authenticated tunnel, with Tailscale, ZFS, restic/rest-server and (interim) Immich doing what they are good at, and Reliquary built as the assistant and the small Class S store on top.**

Concretely:

1. **Network.** Devices reach the homelab only over Tailscale (auth key issued at enrolment and printed on the card; system app on phones now, embedded node later if spike S1 passes). No inbound port. Headscale is the documented exit. Device credentials are separate from tailnet identity and the homelab's key is pinned from the card.
2. **Class S store.** A plaintext content-addressed store on an encrypted, snapshotted ZFS dataset (a6cas layout without the age step), a synchronous ingest API (resumable upload, hash recomputed on arrival, fsync, catalog row, then 200), a "have SHA-256 X?" endpoint that answers only from verified bytes, a sightings log (member, device, path, mtime, EXIF, first seen), write-only per-device credentials, no delete or overwrite endpoint, per-member quotas, snapshots with holds releasable only by a separate credential, monthly keyless scrub, raw-send replica off-site. Immich mounts the store `:ro` as the family viewer when wanted.
3. **Class P.** restic repositories per member behind rest-server `--append-only --private-repos`, custody (c) unless the owner chooses otherwise, homelab-side `check --read-data-subset` as the source of "safe".
4. **The app.** One Reliquary app: discovery proposes locations and a class (media → S, documents → P, member can override); drop folder with a Private sub-folder; hash cache and uploader for S; bundled restic for P; plain-language health computed from the homelab's catalog, restic checks and (interim) Immich's API; nudges by email; quarterly audit; invite redemption; signed self-update including the engine. Stack decided after spike S4 (ADR-0003 waits).
5. **Kit.** USB stick + printed one-use code as in ADR-0002; the code carries the tailnet auth key and a device token; the stick doubles as the seeding transport with `age -pq`-encrypted bundles.
6. **Interim.** Immich as the phone uploader for Class S until the Reliquary Android uploader exists, on its own snapshotted dataset, originals byte-exact, nightly provenance export, hash-based import into the store later.

**Settled requirements it rewords** (section 3): l.44 Connectivity (tunnel instead of R2; keep never-exposed, append-only, USB); l.45 Encryption trust model (per class; delete "devices cannot read"); l.46 Deduplication (SHA-256 against the homelab's verified catalog, Class S); l.50 Restore mechanism; l.51 Off-site copy (precondition); l.41 Email (no cloud control plane); Properties l.28 "client-side encryption" (per class); l.39 code signing (open, decide before D2).

**Wave 1 results it keeps:**
- Formats and vectors: plain SHA-256 identity and vectors (`docs/spec/identifiers.md`, kind 00); age v1 for USB bundles with the three-decryptor evidence (`spikes/A6-S5`, X25519 only; PQ recipients restore only with Go age ≥ 1.3); the format-independence rule (public spec, stock tool, second implementation) applied to every store and every bundle.
- Storage: a6cas crash-safe layout and A6-S4 rebuild results; ADR-0012 Decision 5 (write-once after commit, held snapshots, verify-before-destroy pruning, keyless scrub, catalog rebuildable from the store); c4 §F6 capacity forecast and 32 TB tier; c4 Q11 quotas; A6's ZFS facts and the raw-send caveat.
- Protocol principles: "safe" only after homelab verification (SR-05/SR-06 generalised); keep-until-acked and never-silent (SR-28/AR-09); no remote destruction (SR-20); append-only homelab audit log (SR-30); durable-commit contract and protocol→UX state map (ADR-0009 items 9 and 14); the trust-anchor-from-the-card principle (SR-02/SR-27, one sentence).
- Kits and delivery: ADR-0002 kit and wizard; ADR-0004 D0–D3 steps and the per-platform restore gate ("no reassuring word before a proven restore"); E2 stopgap tables and E2-S3's "fixers change the hash" finding; E1 census and consent kits; F1-S2 Immich live-check kit repurposed as the Phase 0 pilot; H3 data-governance rules.
- Platform facts: ADR-0019/B3 Play compliance; ADR-0022/B7 packaging, MOTW, Gatekeeper, SAC, signed self-update with anti-rollback; client-stack.md Android facts (dataSync 6 h/24 h cap, WorkManager, `setRequireOriginal`); B4's 16 iOS constraints as the checklist for judging Immich's iOS behaviour.
- Custody: D2/ADR-0008 SLIP-39 design and D2-S2 drill, re-scoped to two secrets (at-rest key, Class P admin share); key-ceremony runbook simplified; BUD-RECOVERY drill.
- Threat register structure, re-weighted per section 4; F1's verified per-candidate facts and churn measurements; F1-S1 probes as the Class P evidence; the budgets sheet and owner intake.
- UX: ux-drop-folder.md (OD-22) with class awareness; E3/E4 health vocabulary, discovery and nudge requirements; e2 §1.1–1.2 false-safe principle and M9.

**Conditions under which the recommendation should change:**
- Spike S1 shows relatives cannot be kept on a tunnel without hand configuration **and** no embedded option is viable within a year → fall back to a plain WireGuard config QR on the card (needs an inbound UDP port or IPv6; fails under CGNAT) or accept Cloudflare Tunnel **with Class S client-encrypted again** (which reinstates much of A2). Both are worse; the owner should see S1's result before choosing.
- Spike S2 shows phone background upload fails for most relatives under both Immich and a Reliquary prototype → the "phones first-class" goal needs a desktop bridge (B4's analysis) regardless of architecture.
- Spike S5 shows the cross-member duplicate share is negligible → nothing changes in the design (the "have it?" endpoint is nearly free), but the priority can be deprioritised in the UX.
- The owner reaffirms the literal "not VPN-only" sentence after reading section 9 → direction C/E is unavailable; the honest alternatives are B (Cloudflare with client encryption for everything) or a public HTTPS endpoint on the homelab (the owner's original ask, which ADR-0001 rejected on attack-surface grounds; a hardened TLS endpoint with device certificates is defensible for a family and should then be costed).

---

## 7. Research and spikes to validate it (2–4 weeks)

All on real hardware: the Proxmox host, the owner's laptop, one low-end Android phone, one iPhone if available. Each spike has a pass criterion; a fail changes the plan as stated in section 6.

| # | Spike | What is measured | Pass | Fail consequence | Effort |
|---|---|---|---|---|---|
| S1 | **Tunnel on phones and desktops** | Tailscale system app with a pre-authorised auth key on Android and iOS; one-VPN conflict; OEM battery behaviour over 72 h; direct vs DERP path from a relative's network; plan limits read on tailscale.com; libtailscale/gomobile embedding attempt in a Kotlin test app | Relative-side steps ≤ 3 taps with no typed credentials; connection survives 72 h on the test phone; direct path on at least the home and one mobile network; plan confirmed ≥ 6 users | Fallback decision per section 6 conditions | 8–16 h |
| S2 | **Background upload reliability** | Immich app on the Android test phone and iPhone for 7 days: share of new photos uploaded within 24 h on Wi-Fi/charging; same for a 200-line Kotlin WorkManager uploader prototype posting to a plain HTTP endpoint | ≥ 95 % of new photos uploaded within 24 h on both apps; failure modes documented | Phones need a desktop bridge or foreground nudges; informs whether Immich stays as interim | 12–20 h |
| S3 | **Class S store, plaintext** | a6cas without the age step behind an HTTP ingest with resumable upload and `have?` endpoint; rerun A6-S3 kill/power-cut harness; write-only credential tests (device cannot list, delete, or read another member's catalog); ZFS snapshot + hold + attempted destroy; catalog rebuild from the store | 0 violations in the rerun; all negative credential tests refused; EBUSY on held destroy; byte-identical rebuild | Redesign the store or adopt tusd + a plain tree | 16–30 h |
| S4 | **Class P engine on all platforms** | Bundled restic binary driven by a test app on Windows, macOS, Linux; Termux-built restic as a Play-style Android background job; rest-server `--append-only --private-repos` per member on a ZFS dataset; `key add` admin share; homelab `check --read-data-subset`; rollback of a member's dataset to a snapshot after a forged-time flood; rustic_core embedding attempt | Backup and restore on three desktops with the bundled binary; admin share recovers; rollback restores the pre-flood repository; Android result recorded either way | Android Class P deferred to a later phase (documented); engine choice confirmed or switched to Kopia under custody (b) | 12–24 h |
| S5 | **Family duplicate share and census** | Run the E1-S1 census kit on the owner's household and one relative: device count, iPhone share, library sizes, and the byte share of files whose SHA-256 appears in more than one person's library (counts only, per H3 rules) | A number, with method, recorded in the repo | None; sizes the dedup win and the Phase 0 disk purchase | 6–10 h |
| S6 | **Keep-forever and exit drill with Immich** | Immich on a snapshotted dataset; a user trashes and permanently deletes; admin restores from snapshot; nightly provenance export to plain files; hash-based import of the export into the S3 store; upgrade Immich one minor with snapshot-before-upgrade | Deleted original recovered; import reproduces (owner, filename, upload time, checksum) for every asset; upgrade reversible | Immich interim restricted to the owner's household or dropped in favour of a plain write-only drop | 8–12 h |
| S7 | **Recovery and succession drill** | ZFS at-rest key passphrase split 2-of-3 with stock `shamir`; a non-author recovers 10 named photos from a cold homelab with two cards and the one-page heir procedure (BUD-RECOVERY ≤ 2 h); passphrase rotation without re-encryption | ≤ 2 h, no author help | Simplify the procedure until it passes | 6–10 h |
| S8 | **Off-site replica** | Raw `zfs send` of the encrypted Class S dataset to a second disk or site; restore one file from the replica alone | Replica verifies and restores | Replica design changes before any only-copy data lands | 4–8 h |

Total: roughly 70–130 h, i.e. 2–4 weeks at full attention or about three months at 8 h/week; S1, S2 and S3 first, in parallel where possible.

---

## 8. What to stop now

**Withdraw** (no reason to exist under direction F):
- Wave 2 workstreams that elaborate the cloud control plane, receipts and reconciliation: C1–C8 (Cloudflare), A3 ingest-protocol transport half, D4 attack suite against the Worker, the TLA+ model's pending extensions (ADR-0009 l.46–48, l.100).
- Presence-oracle, epoch, rotation and per-person-key work: DR-F3-2, DR-A1-1, DR-A1-2, DR-D2-1, F3-S2 follow-ups, SR-15/SR-21 (OD-23).
- Content encryption for Class S: the resumable encoder, tag journal, keystream guard, part-size policy, PQ hybrid stanza work (ADR-0007 Class S half), size padding (4.8).
- Offline archive key A′, attended restores, X audits (ADR-0012 posture half; 4.5).
- Restore re-encryption pipeline and R2 restore prefixes (ADR-0001 §6).
- Cost model Cloudflare lines, sandbox account (Sitting 1.5), spend meters and kill switch (c4 Q9–Q10).
- Two-bucket/two-D1/bootstrap-host topology (3.11–3.12).
- The 40-ADR reservation table as a plan of record; ADRs 0006 (HMAC/epoch parts), 0007 (Class S envelope), 0009 (transport half), 0010 (all), 0012 (posture half) are superseded in substance and need one superseding ADR, not forty.

**Pause** (decide after the spikes):
- ADR-0003 client stack (after S4 shows whether rustic_core or a bundled binary wins).
- B3 Play work beyond keeping the facts (only if a bespoke Android app is built in Phase 2).
- Gate A as a blocking gate: replace with two rules, "keep plaintext-recoverable at the homelab" and "record raw provenance from the first byte", plus the Gate C items (#8–#12 in `one-way-doors.md`) and Class P custody as the real doors.
- The remaining ~40 pending owner decisions in `wave1-decisions.md` Sittings 1–4: most are moot; the survivors are listed in section 9.

**Continue** (transport-independent, needed under any direction): E1 census (as S5), E2 stopgap checklist with Phase 0 replacing vendor clouds, E3/E4 health vocabulary and discovery rules, B7/ADR-0022 packaging and self-update, D2 custody re-scoped (as S7), A6 storage work (as S3), G2 restore drills, H3 governance, ux-drop-folder.md with a class rule.

---

## 9. Owner decisions needed to proceed

1. **"Not VPN-only."** Does an authenticated tunnel that relatives never configure by hand (auth key from the printed card; embedded in the app later if S1 passes) satisfy the intent of that sentence? If not, say which of the honest alternatives in section 6's conditions you prefer.
2. **"Client-side encryption before data leaves the device."** Confirm the per-class reading: Class P yes; Class S encrypted in transit end to end and at rest on the homelab, admin-visible (consistent with OD-24).
3. **Class P key custody:** (a) member only, (b) admin escrow, or (c) split with SLIP-39 cards (recommended), with (a) as a per-member opt-in or not at all.
4. **Class P engine:** accept restic + rest-server as recommended (duplicity declined for platform and chain reasons), or ask for a Kopia comparison under custody (b).
5. **Off-site replica as a precondition:** share the "separate plans" so the review can check they cover the Class S dataset, or accept S8 as the plan.
6. **Interim Immich:** allow Immich as the Phase 0 phone uploader for the owner's household (and relatives after S6 passes), under the exit rules in section 6, knowing it stores cross-member duplicates until import and lets users delete at the app layer.
7. **Code signing:** keep "no signing" and accept that Smart App Control PCs need a workaround, or budget a certificate before any bespoke Windows binary ships to a relative.
8. **Build capacity:** confirm Q-B9 (8 h/week) and answer the rest of the one-hour intake (`docs/research/owner-intake.md`), especially home up/down speeds and CGNAT (Q-D1/D3), which decide between Tailscale and plain WireGuard.
9. **Governance:** authorise one superseding ADR (ADR-0041 or a renumbered 0003) that amends ADR-0001 §1–§4 and the CLAUDE.md lines in section 3, written only after S1–S4 report; and authorise withdrawing the section 8 list so the owner's decision queue shrinks to these nine items.
