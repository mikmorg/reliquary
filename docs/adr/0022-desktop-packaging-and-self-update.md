# ADR-0022: Desktop packaging and self-update mechanics. Wave 1 part: a signing identity stable across releases, and planning to sign on Windows

- **Status:** Proposed (partial draft; the Wave 1 decisions only. The rest is to be decided in Wave 2, see "Not yet decided")
- **Date:** 2026-10-06
- **Owner workstream:** B7
- **Decider:** the owner
- **Gate:** C
- **Supersedes / Amends:** None directly. Decisions 1 and 4 depend on **OD-09**. If the owner chooses option C or D, ADR-0002 §5 ("No OS code signing for now"; "self-updated binaries must be re-signed ad hoc") must be amended by D5's ADR-0015 draft. This ADR does not amend it.
- **Evidence:** `docs/research/b7-packaging-self-update.md` (Wave 1 final). Kits `docs/research/kits/B7-S1/` and `docs/research/kits/B7-S2-SAC/`. Spike `spikes/B7-S1-dr/`.
- **Traceability:** R-01, Q2-4, C-08 (see `docs/research/traceability.md`)
- **Owner decisions:** OD-09 (see `docs/research/decision-queue.md`); touches OD-01 (Apple membership shared with iOS) and OD-15 (SignPath eligibility)
- **One-way door:** No. A signing identity can be changed later. Each change costs one grant reset on every Mac, and on Windows it means a new publisher identity.

## Context and problem statement

Reliquary's desktop app installs from a USB stick and then updates itself (ADR-0002 §4–§5). ADR-0002 §5 chose no Apple or Windows code signing for now, with ad-hoc signatures on macOS and a mandatory app-level update signature (minisign, D5). B7 was asked to quantify what "no OS signing" costs, in particular whether macOS still recognises the app after a self-update, and how Windows Smart App Control (SAC) treats an unsigned app and each unsigned update.

The Wave 1 research found four things:
- **Ad hoc.** An ad-hoc identity is the hash of that exact build. Every update therefore loses Photos and Files and Folders grants (the user is asked again) and Full Disk Access (it stops silently).
- **Self-signed.** A stable self-signed identity keeps the code-signing requirement the same across releases. Whether macOS's privacy system (TCC) honours it is untested.
- **Keychain.** It keys non-Apple-issued apps by build hash in every case, so only an Apple-issued identity avoids a Keychain prompt after each update.
- **Windows.** SAC checks every executable, wherever it came from, and blocks unsigned files without positive reputation. Each Tauri self-update runs a new unsigned installer.

This ADR records what packaging must do given those facts. Spending money on signing is the owner's call (OD-09). Release-key custody and CI signing belong to D5 (ADR-0015), and device-credential storage to D3 (ADR-0014). Both get requirements from this ADR.

## Decision drivers

- **Settled:** Windows, macOS and Linux are v1 platforms; users are non-technical and never touch configuration (CLAUDE.md, R-01).
- **Settled:** no OS code signing for now. Self-updates are signed with the project's offline key and verified before installing (ADR-0002 §5).
- **Settled:** distribution is by USB stick, the desktop app updates itself, and the stick doubles as the seeding transport (ADR-0002 §4).
- **BUD-SUPPORT** (owner time ≤ 2 h/month): every prompt after an update on every family Mac, and every blocked update on a Windows PC, is a likely support call.
- **BUD-ENROLL** (unaided computer enrolment ≤ 20 min): a SAC block on first launch makes enrolment impossible on that PC.
- **Data integrity:** a device whose agent silently stops running is the failure the client exists to prevent.

## Considered options

The options are those of OD-09 (see the note's §7 table and decision request).
1. **A.** No spend; macOS ad hoc (ADR-0002 §5 literally).
2. **B.** No spend. macOS: a stable self-signed identity for TCC, with the device credential outside the Keychain. Windows: unsigned, plus a SAC census and SAC-state monitoring.
3. **C.** B plus Windows Authenticode signing (Azure Artifact Signing if eligible, else an OV certificate; SignPath Foundation if the repo is OSS-eligible).
4. **D.** C plus Apple Developer ID and notarisation.
5. Also considered: "turn SAC off" in the Start-here guide; Microsoft Store (MSIX); a free Apple Development certificate.

## Decision

**Proposed: plan for option C**, subject to OD-09. macOS escalates to D only on the conditions in decision 2. The decisions in scope for Wave 1:

1. **macOS release builds are signed at build time with an identity whose designated requirement (DR) is the same in every release. Plain ad hoc is not the plan of record.**
   - Because: an ad-hoc DR is a list of build hashes, so every update resets privacy grants (K1, verified).
   - The default candidate is a **stable self-signed certificate**. Its default DR is `identifier "<bundle id>" and certificate root = H"<sha1>"`, with no build hash (K2, verified; reproduced with rcodesign in `spikes/B7-S1-dr/`, emulated).
   - Requirements to D5 (ADR-0015): long validity; `O=` in the subject, so `codesign` and `rcodesign` emit identical DRs; key kept offline next to the update key; expiry on the custody calendar; a CI check that `codesign -d -r-` is identical across releases.
   - Whether a self-signed identity is within ADR-0002 §5's "no OS code signing" is for the owner to confirm in OD-09.
2. **Which macOS identity, self-signed or Developer ID, is decided by B7-S1's TCC verdict, not its Keychain verdict.**
   - Self-signed passes TCC: keep it ($0).
   - Only Developer ID passes TCC: OD-09 option D.
   - Escalate to D also if the owner refuses to keep the device credential outside the Keychain, or if OD-01 buys the Apple membership anyway.
   - Because: TCC behaviour under a non-Apple anchor is undocumented (K3, contested; it is the hypothesis B7-S1 tests). The Keychain outcome is already known from Apple's source.
3. **Requirement to D3 (ADR-0014): without an Apple-issued identity, the macOS device credential is not kept in the file-based Keychain.**
   - Because: the keychain partition ID of any non-Apple-issued app, self-signed included, is `cdhash:<build hash>`. Every update would therefore prompt, sometimes for the login keychain password (note C32, Apple `securityd` source).
   - D3 chooses between a `0600` file (optionally wrapped), a rarely rebuilt keychain-broker helper, and Developer ID.
4. **Windows release builds are planned to be Authenticode-signed with an RSA certificate from a Microsoft Trusted Root Program CA**, subject to OD-09.
   - Choice: Azure Artifact Signing if the owner is eligible (individual in US/CA with an Individual billing account, or an organisation in a listed region), otherwise an OV certificate.
   - Because: SAC checks every executable and blocks unsigned files without positive reputation, whether they came by download or by USB (K6, verified). Each update runs a new unsigned installer (K5, verified). Self-signed certificates do not count (K9, verified).
   - Whether Microsoft's cloud ever allows a low-volume unsigned build is undocumented (K7, contested). That makes an unsigned release a per-release gamble on SAC-On PCs, not a known block. This ADR does not rely on K7.
5. **If Windows is signed, every PE that install, update, run and uninstall load is signed and timestamped.** That covers the app exe, any sidecar, the NSIS installer and uninstaller, and the NSIS plugin DLLs. CI verifies this (requirement to G1; Tauri v2 bundler coverage to check in Wave 2). Because: SAC evaluates each binary as it loads (note C17).
6. **If Windows stays unsigned (OD-09 option B, or no decision by Gate C):**
   - the client watches `Windows.System.Profile.SmartAppControlPolicy` (`Changed`) and reports a SAC switch to On as a health problem (requirement to B1/E3);
   - SAC-On and Evaluation PCs are a temporary scope reduction the owner explicitly accepts;
   - the Start-here guide keeps "turn SAC off" only as a last resort, with a warning.
7. **No on-device re-signing.** The updater installs the bundle exactly as signed in CI. `tauri-plugin-updater` 2.13.0 already does this (K5, verified).
   - Proposed for Wave 2 (B7-S3 with D5): before the macOS swap, check that the new bundle satisfies the running app's DR, and refuse on mismatch. This is the Sparkle model, and it means an attacker needs both the update key and the code-signing key.
8. **The "cost of not signing" table** in `docs/research/b7-packaging-self-update.md` §7 is the evidence table this ADR owns. It is re-checked when B7-S1, the SAC kit or the census report.

### Not yet decided (to be decided in Wave 2)

- Windows installer format and install location (Tauri NSIS per-user, Velopack, Inno, WiX, portable); WebView2 offline on Windows 10; ARM64.
- macOS container (`.app` on exFAT vs DMG), `~/Applications` vs `/Applications`, universal2, app translocation.
- Linux packaging (AppImage static runtime, exec bit on FAT/exFAT, Flatpak, .deb/.rpm, glibc baseline).
- Updater choice and mechanics: two-process updates, locked files, atomic swap, rollback after a crash loop (B7-S3), deltas, offline updates by USB, version skew and forced-update threshold (with C1).
- USB stick layout and "Start here" files (with E5); CI release pipeline sketch (with G1); antivirus (B7-S4).

### Consequences

- **Good:**
  - Mac grants are planned to survive updates at $0, if B7-S1 confirms.
  - Windows works on SAC-On PCs for first launch and every update, deterministically rather than by cloud prediction.
  - The ADR-0002 §5 "re-sign ad hoc" step disappears.
- **Bad / accepted trade-offs:**
  - About $120/year (Artifact Signing) or $150–300/year plus a token (OV), with identity validation and renewal.
  - A new **online** signing credential in CI/Azure beside the offline minisign key. Its compromise lets an attacker sign as Reliquary.
  - A broad Authenticode revocation could block the installed Windows fleet.
  - A second offline key (macOS self-signed).
  - Weaker credential isolation on macOS if D3 picks a `0600` file.
  - Signed downloads still show SmartScreen warnings until reputation builds.
- **Follow-up work:** D5 (key custody, CI DR check, ADR-0002 §5 amendment, signing order: Authenticode online first, then minisign offline); D3 (macOS credential store); D1 (threats above); G1 (sign and verify every PE); B1/E3 (SAC-state signal); E1/E5 (census fields; guide copy); B7 Wave 2 (the open list above).

### Confirmation

- **B7-S1** (OL, BUD-SUPPORT), with the note's kit amendments 1–6 applied. TCC verdict per arm; Keychain verdict per arm; captured `codesign -d -r-`; securityd `integrity` log lines; no local trust for the test certificate in the run user.
- **B7-S2-SAC** (OL, BUD-ENROLL, BUD-SUPPORT), with amendments 7–9. Unsigned arm on a real SAC-On PC (first launch and update). The NoISG audit lists every PE to sign. The signed arm passes with zero 3076/3077 events across install, update and uninstall.
- **Census** (FM, `FAM → AGG`): SAC state, build and KB level per family PC.
- **CI** (G1/D5): DR equality across releases; every PE signed, RSA, timestamped.

## Pros and cons of the options

### A. Ad hoc, unsigned Windows
- Good, because it costs $0 and matches ADR-0002 §5 literally.
- Bad, because every update resets macOS privacy grants and FDA (K1) and prompts for the Keychain (C32).
- Bad, because SAC-On PCs depend on an undocumented cloud prediction for every release (K6; K7 contested).

### B. Stable self-signed (macOS) + credential outside Keychain; unsigned Windows + census + SAC monitoring
- Good, because it costs $0, the DR is stable across releases (K2), and TCC may keep grants (hypothesis, K3 contested; skhd.zig and yabai practice reports, same-machine caveat).
- Bad, because the TCC arm is unproven and needs an extra offline key.
- Bad, because the Windows SAC risk is unchanged and can appear after enrolment (Evaluation → On; a 2026 user toggle, secondary-only).

### C. B + Windows signing
- Good, because a Trusted-Root RSA signature is the documented SAC path (K6, K9). Artifact Signing is designed to support SAC (K12) at about $9.99/month (K11).
- Bad, because of the recurring cost, eligibility limits (K11), the online credential and revocation exposure, every PE needing a signature, and RSA for Artifact Signing being unconfirmed (K12).

### D. C + Developer ID
- Good, because Apple documents grant continuity for Apple-issued identities (note C6), and the Keychain partition is a stable `teamid:` (C32).
- Bad, because of the extra $99/year and a notarisation pipeline.

## Evidence

| Claim | Source (primary) | Verdict |
|---|---|---|
| K1: ad-hoc DR is a list of cdhashes; prompts repeat after each change | TN3127; Apple `StaticCode.cpp` | Verified |
| K2: self-signed default DR is identifier + certificate hash, no cdhash | Apple `drmaker.cpp`; rcodesign 0.29.0 (emulated spike) | Verified |
| K3: TCC (and Keychain) keep grants under a stable self-signed identity | TN3127, TN2206 (inference) | **Contested.** Keychain half refuted by `securityd` source (note C32); TCC half is B7-S1's hypothesis. Not the sole support of any decision here |
| K4: without an Apple-issued identity, only the file-based keychain | TN3137, TN3125, DTS | Verified |
| C32: keychain partition ID is `cdhash:` for non-Apple-issued code | Apple `securityd/src/clientid.cpp`, `acls.cpp` | Skeptic-raised by all three; primary re-read 2026-10-06; not in the computed tally |
| K5: Tauri updater ships the build-time signature; runs a new installer on Windows | `tauri-plugin-updater` 2.13.0 source | Verified |
| K6: SAC checks all executables; blocks unsigned without positive reputation | MicrosoftDocs `smartscreen-reputation.md` (2026-05-04), SAC overview | Verified |
| K7: every unsigned update blocked for a tiny fleet | SmartScreen reputation doc (inference) | **Contested**: hypothesis for the SAC kit; not relied on |
| K8: Evaluation → On may block an installed app | SAC overview, testing guide (inference) | **Secondary-only**; used only as a risk |
| K9: self-signed Authenticode does not satisfy SAC | SAC signing page (2022, stale), code-signing options | Verified |
| K10: SAC toggle one-way (2025 docs) | SAC overview, testing guide | **Contested**: probably superseded by 2026 KBs (secondary-only); not relied on |
| K11–K13: Artifact Signing, OV and EV cost and eligibility | MicrosoftDocs mirrors (2026) | Verified |

## Reversibility

- **macOS identity.** It can be changed at any release. Each change resets grants once on every Mac (a new certificate hash). Moving from self-signed to Developer ID later costs exactly one reset.
- **Windows signing.** Paying can stop at any time. Timestamped builds stay valid unless revoked. Changing publisher identity resets SmartScreen reputation.
- **Gets harder** once the first family kit ships, because every installed copy carries the identity it was signed with.

## Alternatives considered

- **Turn SAC off in the Start-here guide:** last resort only. It weakens the relative's PC, and if SAC can now be turned back On (2026 reports) it is not durable.
- **Self-signed Authenticode:** rejected; SAC ignores it (K9), and it needs an admin-installed root on every PC.
- **Microsoft Store (MSIX):** not evaluated in depth. Free only for MSIX; packaging a background engine is unchecked; it changes the ADR-0002 §4 channel. Wave 2 note.
- **Free Apple Development certificate:** would get a `teamid:` partition, but is probably not licensed for distribution to others; not evaluated.
- **Submitting each unsigned release to Microsoft for review:** its effect on SAC is undocumented; a per-release chore; dismissed.

## Open questions

- Does TCC honour a non-Apple-anchored DR across updates, with no local trust? (B7-S1)
- Does `tccd` require trusted anchors? What happens after certificate expiry, with and without a timestamp? (B7-S1)
- Helper attribution and `SMAppService` for self-signed apps. (B7-S1 helper arm)
- SAC on a real SAC-On PC for unsigned first launch and update, and what a blocked background agent looks like to the user. (SAC kit)
- Current SAC toggle behaviour and KB level. (H1 allowlist; SAC kit)
- Artifact Signing key algorithm (RSA?) and the owner's eligibility. (Before purchase; H2)
- Tauri v2 bundler signing coverage for NSIS plugins and the uninstaller. (G1, Wave 2)
- Everything listed under "Not yet decided". (B7 Wave 2)
