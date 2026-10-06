# B7. Packaging, install-from-USB and self-update mechanics (Wave 1: the cost of not signing, macOS identity across updates, Smart App Control)

- **Workstream:** B7 (see `docs/research/PLAN.md`, section "B7.")
- **Status:** Final for Wave 1. The rest of B7 (installers, updater mechanics, Linux, stick layout, CI sketch, antivirus) is Wave 2.
- **Date:** 2026-09-29 (last updated 2026-10-06, after skeptic review and synthesis)
- **Feeds:** OD-09 (signing spend, Gate C); ADR-0022 (B7; draft at `docs/adr/0022-desktop-packaging-and-self-update.md`, Wave 1 part only; owns the "cost of not signing" table in §7); ADR-0015 (D5, update trust root and release signing: requirements only); ADR-0014 (D3, device credential storage: requirements only); ADR-0003 (T1 spike 1 inputs)
- **Depends on:** T1 (`client-stack.md`, spikes 1, 5 and 6), T2 (`fact-check-adr-0001-0002.md`, items 8–10), H5 (`h5-long-lead-items.md`, L07, L08, L13, L14), B4 (`b4-ios-decision.md`, OD-01 overlap with the Apple membership), D5 and D3 (not yet delivered)
- **Traceability rows advanced:** Q2-4 (SAC, then the signing decision), C-08 (ad-hoc re-signing after self-update; AV heuristics are Wave 2), R-01 (desktop platforms)
- **Scope of this run:** Wave 1 only. (1) Desk evidence and the kit for B7-S1: macOS identity, TCC and Keychain across self-updates. (2) Desk evidence and a kit for Windows Smart App Control (SAC) on first launch and on self-update, which is also T1 spike 1's Windows leg. (3) The "cost of not signing" evidence for OD-09.

## Summary

**macOS.** Apple's documents and its open-source signing code agree: an ad-hoc-signed app is identified by the hash of that exact build. So with ad hoc, **every self-update loses the app's privacy grants** (Photos, Files and Folders, Full Disk Access), and the user is asked again (verified, K1). A build signed with our own **stable self-signed certificate** gets an identity made of the bundle ID plus the certificate's hash, which stays the same across releases (verified, K2). Whether TCC, the privacy-grant system, honours that identity is **still a hypothesis**; B7-S1 tests it on a real Mac.

The skeptics found one change in Apple's current source. The macOS **Keychain** does not identify self-signed apps by that stable identity. Since macOS 10.12 it uses a "partition ID". That ID is stable only for Apple-issued identities (Developer ID, App Store, Apple Development). For every other signed app, self-signed included, it is the build hash. So **a self-signed Reliquary will still get a Keychain prompt after every update**. To avoid that, the device credential has to live outside the Keychain unless the owner buys Developer ID ($99/year). This is now a D3 question, not a fallback.

**Windows.** Microsoft's developer docs (May 2026) say SAC checks **every executable, not only downloaded ones**, and blocks unsigned files that lack positive reputation (verified, K6). Each self-update runs a newly downloaded unsigned installer (verified, K5). Is any unsigned Reliquary release ever allowed by Microsoft's cloud prediction for a 10–25-device fleet? That is undocumented and is the SAC kit's hypothesis (contested, K7). A Trusted-Root signature is the only **documented, deterministic** way through. The cheapest is Azure Artifact Signing, about $9.99/month, and only if the owner is eligible (verified, K11).

2026 reports, which are secondary because the primary pages are blocked, say SAC can now be switched On and Off at any time. If so, a clean census today does not protect next month.

**Recommendation for OD-09 (medium confidence):** option **C**.
- **Windows:** sign. Use Artifact Signing if the owner is eligible, otherwise an OV certificate.
- **macOS:** no plain ad hoc. Use a stable self-signed identity for TCC, pending B7-S1, and keep the device credential outside the Keychain (D3).
- **Escalate to Developer ID only if** B7-S1's **TCC** leg fails, the owner refuses non-Keychain credential storage, or OD-01 buys the membership anyway.

## Questions

| # | Question | Short answer | Confidence |
|---|---|---|---|
| 1 | With ad-hoc signing, do TCC grants survive a self-update? | **No.** TN3127: an ad-hoc DR "is tied to that specific version of the code" and prompts repeat. Apple source: the ad-hoc default DR is an OR of cdhashes (K1). Full Disk Access is never prompted for; it stops working silently and must be re-granted in Settings. | High |
| 2 | With ad-hoc signing, do Keychain items stay silently readable after an update? | **No.** No provisioning profile, so only the file-based keychain is available (K4). Its items carry a partition list, and a non-Apple-issued app's partition is `cdhash:<cdhash>` (C32). v2 does not match, so securityd prompts or denies. | High (source; hardware test in B7-S1) |
| 3 | Does a **stable self-signed identity** keep grants across updates? | **TCC: maybe (hypothesis).** The DR is stable (K2), and TCC checks the recorded DR (C1). But no Apple document says TCC accepts a non-Apple anchor (K3, contested). **Keychain: no.** The partition ID is still the cdhash (C32), so expect a prompt after every update, as with ad hoc. | TCC: Low-medium (B7-S1 decides). Keychain: High (source) |
| 4 | Does Developer ID keep them? | **Yes.** TN3127: default DRs for Apple-issued identities carry privileges over (C6). Keychain: Developer ID maps to a stable `teamid:` partition (C32). | High |
| 5 | Does a LaunchAgent helper get TCC attribution to the app? | **Designed to**, through "responsible code"; `AssociatedBundleIdentifiers` is the fix if attribution is wrong (C11). `SMAppService` on macOS 13+ may need user approval (C12). Nothing found on ad-hoc or self-signed apps. | Low-medium (B7-S1 helper arm) |
| 6 | Must self-updated macOS binaries be "re-signed ad hoc" on the device (ADR-0002 §5)? | **No.** `tauri-plugin-updater` 2.13.0 swaps in the whole `.app` as it was signed at build time and never runs `codesign` (K5). On-device re-signing is unnecessary, and impossible for a self-signed key that is kept offline. This is a wording fix for D5. | High (source) |
| 7 | How does SAC treat the first USB launch and each unsigned self-update? | **The rule is documented:** SAC checks all executables, with or without Mark-of-the-Web, and blocks unsigned files unless they have positive reputation (K6). Every update runs a new unsigned installer (K5). **The outcome for a tiny fleet is not documented.** "Every update blocked on SAC-On PCs" is the kit's hypothesis (K7, contested). | Rule: High. Outcome: Medium (hypothesis) |
| 8 | Can SAC be switched Off and back On without reinstalling? | **Probably yes on current builds, but primary sources are unread.** The 2025 Learn pages allow Off from Settings, and On only on a clean install ("one-way"). Several 2026 reports say a 2026 cumulative update (KB5074105 preview, January 2026; KB5083769 or KB5083806 in April 2026, reports differ) made it switchable from Windows Security. The KB pages are blocked (K10, contested; C34). | Low-medium |
| 9 | How many family PCs have SAC On or in Evaluation? | **Open.** The census kit is ready (Part 0 of the SAC kit). If SAC can now be switched On at any time, the census is a snapshot only. | n/a |
| 10 | What is the cheapest route to signing that SAC accepts? | **Artifact Signing**, about $9.99/month. Individuals must be in the US or Canada and need an Azure billing account of type Individual; organisations qualify in 12 regions. A paid subscription is required (K11, C36). Otherwise an **OV certificate** at $150–300/year plus a token (K13). **SignPath Foundation** if the repo is OSS-eligible (unverified). The **Store** is free only for MSIX (C35). Self-signed does not work (K9). | Medium-high |
| 11 | Could a PC in SAC Evaluation later break an already-installed unsigned Reliquary? | **Plausible, untested.** Evaluation turns On "in most cases" (C20), and SAC checks binaries at load (C17). The opposite is also documented: Evaluation turns itself Off for users it would disrupt. Which way a PC running an unsigned agent goes is unknown (K8, secondary-only). | Low-medium |
| 12 | Defender and consumer antivirus on unsigned self-updating binaries | Out of Wave 1 scope (B7-S4, Wave 2). | n/a |

## Method

- **Sweep:** two scouts (docs; source code), an analyst deep read, a spike runner (two kits and one container spike), three skeptics (sources, logic, adversary) on 13 key claims, and this synthesis.
- **Synthesis re-checks (2026-10-06):** re-read Apple `Security @ main`: `securityd/src/clientid.cpp` (`partitionIdForProcess`), `securityd/src/acls.cpp` (`validatePartition`), and the trust and expiry path in `StaticCode.cpp`. Also re-read the Artifact Signing quickstart (billing account) and `code-signing-options.md` (MSIX vs MSI/EXE; validation time).
- **Routes used:** `developer.apple.com/tutorials/data/documentation/...json` for technotes; WebFetch for two Apple Developer Forums threads (quotes via the fetch summariser, marked); raw.githubusercontent.com for MicrosoftDocs, tauri-docs, apple-oss-distributions and similar-work repos; static.crates.io for crate source; GitHub MCP code search in the MicrosoftDocs org; WebSearch (skeptic stage only) for the 2026 SAC toggle.
- **Blocked sources (reported to H1):**
  - support.microsoft.com: the SAC consumer FAQ, and the KB5074105, KB5083769 and KB5083806 release notes (EGRESS_BLOCKED, last tried 2026-10-06).
  - blogs.windows.com: Insider posts of 2026-01-27 and 2026-03-12 (EGRESS_BLOCKED).
  - bleepingcomputer.com, pureinfotech.com and windowscentral.com article pages (blocked at the skeptic stage; seen only as search snippets).
  - techcommunity.microsoft.com (EGRESS_BLOCKED).
  - learn.microsoft.com (blocked by run rules; the MicrosoftDocs mirrors were used instead).
  - azure.microsoft.com pricing (so the $9.99 figure rests on the Learn mirror).
  - developer.apple.com/forums through curl (bot check; WebFetch worked).
- **Stop rule:** the Apple open-source code answered the DR question and, at the skeptic stage, the Keychain partition question. For the SAC toggle, no primary route is open. Two consecutive passes (GitHub code search of MicrosoftDocs; WebSearch) found no readable primary source.

## Sources

| # | Source (title and URL or mirror path) | Publisher | Published or version date | Accessed | Primary? |
|---|---|---|---|---|---|
| S1 | TN3127 Inside Code Signing: Requirements, `developer.apple.com/documentation/technotes/tn3127-inside-code-signing-requirements` (JSON endpoint) | Apple | 2022-05-03; revised 2024-04-02 | 2026-09-29; 2026-10-06 (skeptics) | Yes |
| S2 | "On File System Permissions", `developer.apple.com/forums/thread/678819` (DTS; via WebFetch summariser) | Apple DTS | 2021-04; updated 2026-09-18 | 2026-09-29 | Yes (summariser route) |
| S3 | `developer.apple.com/forums/thread/730043` (DTS replies; WebFetch) | Apple DTS | 2023-05/06 | 2026-09-29 | Yes (summariser route) |
| S4 | `apple-oss-distributions/Security @ main : OSX/libsecurity_codesigning/lib/StaticCode.cpp` (`defaultDesignatedRequirement`; trust evaluation with implicit anchors; expired-certificate retry) | Apple (open source) | main HEAD | 2026-09-29; 2026-10-06 | Yes |
| S5 | `... : OSX/libsecurity_codesigning/lib/drmaker.cpp` (`DRMaker::make`, `nonAppleAnchor`); also `signerutils.cpp` and `reqinterp.cpp` (read by skeptics) | Apple (open source) | main HEAD | 2026-09-29; 2026-10-06 | Yes |
| S6 | TN3137 On Mac keychain APIs and implementations (JSON endpoint) | Apple | 2022-11-01; revised 2026-09-24 | 2026-09-29 | Yes |
| S7 | TN3125 Inside Code Signing: Provisioning Profiles (JSON endpoint) | Apple | not recorded | 2026-09-29 | Yes |
| S8 | TN2206 macOS Code Signing In Depth (archived) | Apple | last revised 2016-08-09. **Predates keychain partition IDs (10.12); superseded for the keychain by S30–S31** | 2026-09-29 | Yes (old) |
| S9 | SMAppService, `agent(plistName:)`, `Status.requiresApproval` (JSON endpoints) | Apple | undated | 2026-09-29 | Yes |
| S10 | `tauri-plugin-updater` 2.13.0 crate, `src/updater.rs` (static.crates.io) | Tauri | 2.13.0 | 2026-09-29; 2026-10-06 (skeptics) | Yes |
| S11 | `tauri-apps/tauri-docs @ v2 : src/content/docs/distribute/Sign/macos.mdx` | Tauri | undated | 2026-09-29 | Yes |
| S12 | `tauri-apps/tauri-docs @ v2 : src/content/docs/distribute/Sign/windows.mdx` | Tauri | undated | 2026-09-29 | Yes |
| S13 | `MicrosoftDocs/windows-dev-docs @ docs : hub/apps/develop/smart-app-control/overview.md` | Microsoft | ms.date 2025-11-18 | 2026-09-29 | Yes (mirror) |
| S14 | `... : hub/apps/develop/smart-app-control/code-signing-for-smart-app-control.md` | Microsoft | ms.date 2022-09-20. **Stale:** still calls Trusted Signing "public preview" | 2026-09-29 | Yes (mirror; stale) |
| S15 | `... : hub/apps/develop/smart-app-control/test-your-app-with-smart-app-control.md` | Microsoft | ms.date 2025-10-28 | 2026-09-29 | Yes (mirror) |
| S16 | `... : hub/apps/package-and-deploy/smartscreen-reputation.md` | Microsoft | ms.date 2026-05-04 | 2026-09-29 | Yes (mirror) |
| S17 | `... : hub/apps/package-and-deploy/code-signing-options.md` | Microsoft | ms.date 2026-04-20 | 2026-09-29; 2026-10-06 | Yes (mirror) |
| S18 | `... : hub/apps/package-and-deploy/distribution-feature-status.md` | Microsoft | ms.date 2026-04-17 | 2026-09-29 | Yes (mirror) |
| S19 | `MicrosoftDocs/azure-docs @ main : articles/artifact-signing/quickstart.md` | Microsoft | ms.date 2026-05-21 | 2026-09-29; 2026-10-06 | Yes (mirror) |
| S20 | `... : articles/artifact-signing/faq.yml` | Microsoft | ms.date 2026-05-14 | 2026-09-29 | Yes (mirror) |
| S21 | `... : articles/artifact-signing/concept-trust-models.md` (ms.date 2026-01-06) and `concept-certificate-management.md` (ms.date 2026-09-30) | Microsoft | as stated | 2026-09-29; 2026-10-06 | Yes (mirror) |
| S22 | `MicrosoftDocs/winrt-api @ docs : windows.system.profile/smartappcontrolpolicy.md` | Microsoft | docs HEAD | 2026-09-29 | Yes (mirror) |
| S23 | `MicrosoftDocs/windows-dev-docs @ docs : hub/apps/get-started/best-practices.md` | Microsoft | docs HEAD | 2026-09-29 | Yes (mirror) |
| S24 | Sparkle 2.x `SUUpdateValidator.m`, `SUCodeSigningVerifier.m`, `AppInstaller.m` (raw GitHub, 2.x) | Sparkle project | 2.x HEAD | 2026-09-29 (source scout only) | Yes |
| S25 | `apple-codesign` (rcodesign) 0.29.0 crate: CLI, `src/policy.rs`; and the run in `spikes/B7-S1-dr/` | G. Szorc | 0.29.0 | 2026-09-29 | Yes |
| S26 | `apple-native-keyring-store` 1.0.2 crate (keyring v4 Apple backend) | keyring-rs project | 1.0.2 | 2026-09-29 (source scout) | Yes |
| S27 | yabai wiki "Installing yabai (from HEAD)" | koekeishiya/yabai | undated | 2026-09-29 (source scout) | Yes (similar work) |
| S28 | AskWoody, "Windows 11 Smart App Control can now be turned on or off" | AskWoody | 2026 (search snippet only) | 2026-09-29 | No |
| S29 | Windows Insider blog posts of 2026-01-27 and 2026-03-12 | Microsoft | 2026 | **blocked**; titles from a search listing | Yes, not read |
| S30 | `apple-oss-distributions/Security @ main : securityd/src/clientid.cpp` (`ClientIdentification::partitionIdForProcess`) | Apple (open source) | main HEAD | 2026-10-06 (skeptics; re-read by synthesis) | Yes |
| S31 | `... : securityd/src/acls.cpp` (`SecurityServerAcl::validatePartition`, `extendPartition`) | Apple (open source) | main HEAD | 2026-10-06 (skeptics; re-read by synthesis) | Yes |
| S32 | `jackielii/skhd.zig @ main : docs/CODE_SIGNING.md` | skhd.zig project | undated | 2026-10-06 (skeptic) | Yes (similar work; developer's own Mac) |
| S33 | Microsoft KB5074105 (2026-01, builds 26100/26200.7705), KB5083769 (2026-04-14, .8246) and KB5083806 (2026-04-30) release notes, support.microsoft.com | Microsoft | 2026 | **blocked**; known from WebSearch summaries only | Yes, not read |
| S34 | BleepingComputer "windows-11-cumulative-updates-kb5083769-and-kb5082052-released"; Pureinfotech "kb5083769-windows-11-april-2026-update"; Windows Central "8 features coming with the april 2026 security update"; Topedia "smart-app-control-in-windows-11-can-now-be-re-enabled-without-reinstalling" (2026-04) | Various | 2026-04 | 2026-10-06 (search snippets; pages blocked) | No |

## Claims

### Key claims (skeptic tally, computed in code)

Rule (PLAN §5.1): **verified** = at least one primary source and at least 2 of 3 skeptics did not refute; **secondary-only** = no primary source; **contested** = otherwise. Status is copied exactly from the computed tally. The "Note claims" column maps each key claim to the detailed claims below.

| Key | Claim | Note claims | Sources | Sources skeptic | Logic skeptic | Adversary skeptic | Status |
|---|---|---|---|---|---|---|---|
| K1 | Ad-hoc signed code has a DR tied to that exact build (an OR of cdhashes), so macOS re-asks for TCC privileges after every update. | C1, C2, C3 | S1, S4, S2 | Upheld (FDA effect inferred; kit observes) | Upheld (FDA is not prompted; it fails silently) | Upheld | **Verified** |
| K2 | codesign's default DR for a non-Apple certificate is `identifier X and certificate root/leaf = H"<sha1>"`, with no cdhash, so same-certificate releases satisfy each other's DR. | C4 | S5 | Upheld (shipped codesign vs `main` still to be captured) | Upheld (plus: implicit anchors; expired certificate tolerated without a timestamp) | Upheld | **Verified** |
| K3 | (Inference) TCC and Keychain ACLs keep grants across updates for a stable self-signed identity. | C5, C7 | S1, S8 | **Refuted** for the Keychain (partition IDs); TCC unproven | **Refuted** for the Keychain; TCC unconfirmed | **Refuted**: cannot stand as written | **Contested** |
| K4 | Without an Apple-issued identity and profile, the app cannot claim `keychain-access-groups` and is confined to the file-based keychain, whose ACLs track the creating app by DR. | C8, C9 | S6, S7, S3, S8 | Upheld; "by DR" framing incomplete (partition list) | Upheld; same correction | Upheld; same correction | **Verified** (confinement). The "by DR" wording is corrected by C32. |
| K5 | `tauri-plugin-updater` 2.13.0 never re-signs on macOS; on Windows it runs a freshly downloaded NSIS or MSI installer via `ShellExecuteW` and exits. | C13, C14 | S10 | Upheld (exit only if `ShellExecuteW` > 32) | Upheld (same nuance) | Upheld | **Verified** |
| K6 | SAC's signature checks apply to all executables, not only downloaded ones, and SAC blocks unsigned files without positive reputation. So USB (no MOTW) does not bypass SAC. | C15, C16 | S16, S13 | Upheld | Upheld | Upheld | **Verified** |
| K7 | Unsigned files start from zero reputation each version; building it takes "several weeks and hundreds of clean installs". (Inference) a 10–25 device fleet never earns it, so every unsigned update is blocked on SAC-On PCs. | C22 | S16, S15 | Upheld (inference correctly labelled) | **Refuted**: SmartScreen facts used as SAC/ISG facts | **Refuted**: same | **Contested** |
| K8 | (Inference) a PC in Evaluation may start blocking an installed unsigned Reliquary at its next load, silently stopping backups. | C20, C21 | S13, S15 | Upheld (premises; Evaluation can also turn Off) | Upheld (modal "may") | **Refuted**: unconfirmed; "silently" unsupported (a toast exists) | **Secondary-only** |
| K9 | SAC considers only RSA signatures from Trusted Root Program providers, so a self-signed Authenticode certificate, even as a local root, does not satisfy it. | C18 | S14, S17, S13 | Upheld (S14 is stale, 2022) | Upheld | Upheld | **Verified** |
| K10 | SAC can only be enabled on a clean install; Off/On is one-way (Learn 2025); 2026 reports of a reversible toggle unverified. | C19 | S13, S15, S28 | **Refuted**: outdated; 2026 KB reports | Upheld (but Off was always allowed) | **Refuted**: very likely superseded (KB notes) | **Contested** |
| K11 | Artifact Signing ≈ $9.99/month; individuals US/CA only, organisations in 12 regions; paid subscription; signing stops if validation lapses; 72 h certificates need timestamps. | C23 | S17, S19, S20, S21 | Upheld (price not checked on azure.microsoft.com; "a few business days" is documented) | Upheld (billing account must be type Individual) | Upheld | **Verified** |
| K12 | Microsoft says Artifact Signing Public Trust is designed to support SAC; RSA not confirmed. | C24 | S21, S14 | Upheld | Upheld (S14 calls it "the preferred way" for SAC) | Upheld | **Verified** |
| K13 | OV $150–300/year with HSM or token (June 2023); EV $400+/year, no SmartScreen bypass since 2024. | C25 | S17, S18 | Upheld (Microsoft's "typically" figures) | Upheld | Upheld | **Verified** |

**How the contested and secondary-only claims are used.** K3, K7, K10 and K8 are not the sole support of any recommendation below.
- **K3:** its Keychain half is replaced by C32, which says the opposite. Its TCC half is kept only as B7-S1's hypothesis.
- **K7:** the Windows recommendation rests on K5, K6 and K9 (the documented rule, and that signing is the only deterministic path), not on K7's prediction.
- **K8 and K10:** they appear only as risks that make a census snapshot weaker evidence. They do not support signing on their own.

### Supporting claims (detail)

These are the note's detailed claims. Those mapped to a key claim take its status. The others were not in the skeptic set and are marked as such.

| # | Claim | Sources | Status |
|---|---|---|---|
| C1 | macOS records an app's DR with a privacy grant, and later checks that the running code satisfies it. This is how a new version is recognised as the "same code". | S1 | Part of K1: verified |
| C2 | Apple: ad-hoc code "has a DR but it's tied to that specific version of the code"; DTS: with unsigned or ad-hoc code "the system can't tell that version N+1 … is the same as version N". | S1, S2 | Part of K1: verified |
| C3 | `SecStaticCode::defaultDesignatedRequirement` returns an OR of `cdhash` terms for ad-hoc signatures. | S4 | Part of K1: verified |
| C4 | `DRMaker` for a non-Apple chain: `identifier "<id>"` AND the SHA-1 of the highest certificate whose O matches the leaf's (root slot), or the leaf when there is no O. No cdhash. | S5 | Part of K2: verified |
| C5 | (Inference) same-certificate releases satisfy each other's DR, so TCC **may** carry grants over. Breaks on certificate re-issue, or if TCC demands a trusted anchor (no Apple document either way). | S1, S4, S5 | Part of K3: **contested**. TCC half = B7-S1 hypothesis only |
| C6 | Default DRs for Apple-issued identities are designed so privileges carry over to new versions. | S1 | Not in the skeptic set; primary. Consistent with C32 (Developer ID gets `teamid:`) |
| C7 | TN2206 (2016): keychain ACLs trust the creating app "tracked with its DR"; self-signed identities work "by default" for the keychain. | S8 | Part of K3: **contested**. **Superseded for the keychain by C32** |
| C8 | macOS has a file-based keychain and a data protection keychain; SecItem defaults to the file-based one; the data protection keychain needs a user login context; the file-based one is "on the road to deprecation". | S6 | Part of K4: verified |
| C9 | `keychain-access-groups` needs a profile, and profiles authorise only Apple-issued identities, so ad-hoc and self-signed builds are confined to the file-based keychain (keyring-rs: -34018). | S7, S3, S26 | Part of K4: verified |
| C10 | Since macOS 26.4 a file-based keychain may depend on a protected entropy file in `/var/db/SystemKeys`. | S6 | Not key; not reviewed |
| C11 | TCC uses "responsible code"; add `AssociatedBundleIdentifiers` if a launchd job is mis-attributed. Files and Folders is per user; FDA is system-wide. | S2 | Not in the skeptic set; primary |
| C12 | `SMAppService` (macOS 13+) registers bundled LaunchAgents; `requiresApproval` needs user action. | S9 | Not key |
| C13 | Updater on macOS: extract to temp, rename the old app to a backup temp dir, rename the new one in (AppleScript admin fallback), `touch`; no `codesign`. | S10 | Part of K5: verified |
| C14 | Updater on Windows: write `<app>-<version>-installer.exe` to temp, run `on_before_exit`, `ShellExecuteW` (NSIS `/UPDATE`, or msiexec), then `exit(0)` **only if** `ShellExecuteW` returns > 32; otherwise it returns an error and the app keeps running. | S10 | Part of K5: verified (nuance from skeptics) |
| C15 | SAC allows an app if app intelligence predicts it safe; otherwise if it is signed by a Trusted Root Program CA; "unknown, unsigned code are blocked by default". | S13 | Part of K6: verified |
| C16 | "Smart App Control signature checks apply to all executable files, not just those downloaded from the Internet." | S16 | Part of K6: verified |
| C17 | SAC "evaluates binaries as it loads them"; test all install and uninstall binaries; CodeIntegrity events 3076 (evaluation/audit) and 3077 (enforcement). | S15 | Not in the skeptic set as its own claim; primary; its premises were upheld under K7 and K8 |
| C18 | SAC supports RSA only and "only considers certificates issued by trusted providers". | S14, S17 | Part of K9: verified (S14 stale) |
| C19 | 2025 Learn: Off is allowed in Settings; On only on a clean install; "one-way". | S13, S15 | Part of K10: **contested**. Probably superseded (C34) |
| C20 | SAC starts in Evaluation; "in most cases" it turns On automatically; it turns Off for users it would disrupt; a toast announces enforcement. | S13 | Premises of K8; upheld by all three skeptics as a quote |
| C21 | (Inference) an Evaluation PC may block an installed unsigned Reliquary after switching to On. | S13, S15 | Part of K8: **secondary-only** |
| C22 | SmartScreen: unsigned files build reputation "anew with every update", "several weeks and hundreds of clean installs". (Inference) the same holds for SAC's ISG. | S16 | Part of K7: **contested** (the inference) |
| C23 | Artifact Signing cost, eligibility, subscription, lapse and 72 h certificates. | S17, S19, S20, S21 | Part of K11: verified |
| C24 | Artifact Signing Public Trust "designed to support" SAC; S14 names Trusted (Artifact) Signing "the preferred way" for SAC; RSA not stated. | S21, S14 | Part of K12: verified |
| C25 | OV and EV costs and the 2024 EV change. | S17, S18 | Part of K13: verified |
| C26 | Microsoft points OSS projects to SignPath Foundation (eligibility not checked). | S17 | Not key |
| C27 | (Replaced by C35.) | | |
| C28 | SAC mode in `...\CI\Policy\VerifiedAndReputablePolicyState` (0/1/2); `citool -lp`; the `SmartAppControlAuditNoISG` policy checks signing without cloud reputation. | S15 | Not key (kit method) |
| C29 | WinRT `SmartAppControlPolicy` (`IsEnabled`, `Changed`) reports the SAC state and changes to it. | S22 | Not key. Now a **condition** of option B (see Recommendation) |
| C30 | Tauri supports ad hoc (`"signingIdentity": "-"`); its Windows page does not mention SAC. | S11, S12 | Not key |
| C31 | Sparkle 2 accepts an update if EdDSA is valid **or** the new bundle satisfies the old DR, and refuses to drop code signing. | S24 | Not key (similar work; scout only) |
| C32 | **New.** securityd assigns each file-based-keychain client a partition ID. Apple code gets `apple:`. MAS, TestFlight, Developer ID and Apple Development code gets `teamid:<TEAMID>`. **Any other signed code, self-signed included, gets `cdhash:<cdhash>`.** `validatePartition` compares it with the item's partition list. On a mismatch it logs "ACL partition mismatch" and, on a read, calls `extendPartition`, a user prompt; otherwise it denies. | S30, S31 | Raised independently by all three skeptics; synthesis re-read both files on 2026-10-06. Not in the computed tally (it arose at review) |
| C33 | **New.** Code-signature validation uses implicit anchors (no trust evaluation) unless `kSecCSCheckTrustedAnchors` is set. Without a secure timestamp, an expired or not-yet-valid certificate is retried with `CSSM_TP_ACTION_ALLOW_EXPIRED`; with one, CMS validates at the signing time. | S4 | Skeptic-raised (logic); synthesis re-read. Not in the tally. Whether `tccd` sets `kSecCSCheckTrustedAnchors` is unknown |
| C34 | **New.** 2026 reports say a 2026 cumulative update (preview KB5074105, January 2026; general release in April 2026 as KB5083769 or KB5083806, reports differ) lets SAC be turned On or Off in Windows Security without a clean install. | S33 (blocked), S34 | **Secondary-only** (primary unread) |
| C35 | **New.** The Store re-signs **MSIX** packages only. Win32 MSI or EXE Store submissions must be signed with a Trusted Root Program certificate. | S17 | Skeptic-raised; synthesis re-read. Not in the tally |
| C36 | **New.** Individual Public Trust validation takes identity from an Azure billing account of type **Individual** whose legal name and address match the government ID. Organisation validation has no such requirement. Microsoft says to "plan for a few business days for verification". | S19, S17 | Skeptic-raised; synthesis re-read. Not in the tally |
| C37 | **New (similar work).** skhd.zig reports that, with a self-signed certificate, Accessibility (TCC) grants persist across rebuilds on macOS 15/26, while ad-hoc builds lose them. This was observed on the developer's own Mac, where the certificate sits in the keychain. | S32 | Secondary-strength evidence for the TCC hypothesis only |

## Findings

### 1. macOS: ad-hoc signing loses privacy grants on every update (K1; high)

TN3127 describes how this works. A grant stores the app's DR, and each later access checks the running code against it (C1). An ad-hoc app's DR is "cdhash is one of {…}" (C3), so any rebuild fails the check, and Apple says the prompts repeat (C2). For Reliquary:
- **Photos and Files and Folders** (Desktop, Documents, Downloads, removable volumes): the prompt comes back after each silent update, out of context. A relative who clicks Don't Allow stops that source's backups.
- **Full Disk Access** is never prompted for. After an update it **stops working silently**, and the user must re-grant it in System Settings. For a non-technical relative that means an owner support call per update per Mac, which counts against BUD-SUPPORT. A design that does not depend on FDA (Photos plus per-folder grants) shrinks this exposure under any arm. That is an input to B1 and E4.

### 2. macOS: a stable self-signed identity keeps the DR. Whether TCC honours it is untested (K2 verified; K3 contested)

Apple's `DRMaker` gives a non-Apple certificate the DR `identifier "<bundle id>" and certificate root = H"<sha1>"`, with no cdhash (C4, K2 verified). The container spike `spikes/B7-S1-dr/` (emulated, Linux) showed rcodesign 0.29.0 writing the same form, identical for v1 and v2 (S25). TCC checks the recorded DR (C1). So TCC **may** keep grants across updates.

That stays a **hypothesis** (K3 contested):
- No Apple document says TCC accepts a DR anchored to a non-Apple certificate.
- Code-signature validation itself uses implicit anchors unless `kSecCSCheckTrustedAnchors` is set (C33). Whether `tccd` sets that flag is unknown.
- Similar work (yabai S27; skhd.zig C37) reports grants persisting, but only on the developer's own Mac, where the certificate is in the keychain and possibly trusted. The B7-S1 kit must exclude that (kit amendment 3).

**Corrections from the spike and skeptics:**
- **Signing from Linux CI needs no hand-compiled DR.** rcodesign 0.29.0 derives the self-signed DR itself (B7-S1-dr). This replaces the scout claim (S25) quoted in the draft. Small difference: without `O=`, rcodesign pins `root` where DRMaker pins `leaf`. For a one-certificate chain these name the same certificate. **Require `O=` in the certificate subject** so `codesign` and rcodesign produce the same DR text.
- **rcodesign timestamps via `timestamp.apple.com` by default** and fails offline unless `--timestamp-url none` is set.
- **Certificate expiry** (C33): without a timestamp, macOS tolerates an expired certificate when it validates a signature (source; untested). With a timestamp it validates at signing time. Either way, use a long-lived certificate and put its expiry on D5's key-custody calendar. The kit's expiry sub-test must cover both (kit amendment 5).
- **Re-issuing the certificate** changes its hash and resets every grant once.

**Gatekeeper is unchanged.** It needs Developer ID or App Store anchors, so a self-signed app behaves like an ad-hoc one: fine from USB without quarantine (T2 item 9).

**Key custody** belongs to D5. The self-signed private key must never ship on the device. Losing it means one grant reset on every Mac. Leaking it lets an attacker sign code that inherits Reliquary's TCC grants (D1).

### 3. macOS Keychain: only an Apple-issued identity avoids a prompt after each update (K4 verified; C32)

The draft's reasoning (TN2206: keychain ACLs track the app "by DR") is **superseded**. Since macOS 10.12, file-based keychain items also carry a **partition list**. securityd gives each client a partition ID: `apple:` for Apple, `teamid:<TEAMID>` for App Store, TestFlight, Developer ID and Apple Development, and **`cdhash:<cdhash>` for every other signed app** (C32; `clientid.cpp`, re-read 2026-10-06). On a read whose partition is not listed, securityd prompts (`extendPartition`). With "Always Allow" that prompt asks for the login keychain password, which a relative may not know.

| Arm | Keychain item written by v1, read by v2 |
|---|---|
| Ad hoc | Prompt (partition `cdhash:` changes); high (source) |
| **Stable self-signed** | **Prompt** (partition is still `cdhash:`); high (source), to be observed in B7-S1 |
| Developer ID | No prompt (`teamid:` is stable); high (source). Data protection keychain only if a Developer ID profile can authorise `keychain-access-groups` (not checked) |

**Consequence (to D3 now, not as a fallback):** unless the owner buys Developer ID, keeping the device credential in the Keychain costs one prompt per update per Mac. The options for D3:
1. **A `0600` file** under `~/Library/Application Support`, optionally wrapped with a per-install secret. Weaker against other processes of the same user.
2. **A tiny, separately signed "keychain broker" helper** whose bytes rarely change. Re-signing identical bytes keeps the cdhash (B7-S1-dr), so the cost is one prompt per broker change, not per release. More moving parts.
3. **File-based keychain plus prompts.** Not acceptable for non-technical users under BUD-SUPPORT.
4. **Developer ID** (OD-09 option D).

### 4. macOS: the engine inside the app vs a LaunchAgent helper (C8, C11, C12)

T1 recommends a separate Rust daemon (client-stack.md, spike 6).
- A per-user **LaunchAgent** runs in the user's context. A LaunchDaemon is limited to the System keychain (C8).
- TCC should attribute the agent to the app ("responsible code"). `AssociatedBundleIdentifiers` is the fix if it does not (C11).
- `SMAppService` may report `requiresApproval` (C12).
- **Unknown, for B7-S1's helper arm:** whether attribution and `SMAppService` work for ad-hoc and self-signed apps.

The helper inside the bundle changes cdhash with the app, so the Keychain result in §3 applies to it too.

### 5. The Tauri updater and ADR-0002's "re-sign ad hoc" line (K5)

ADR-0002 §5 says self-updated binaries "must be re-signed ad hoc". With `tauri-plugin-updater`, the signature is applied in CI and travels in the update archive. The device only swaps directories (C13). On-device re-signing is unnecessary. Under a self-signed key kept offline, it is also impossible. This is a wording fix for D5's amending draft.

The skeptics also raised these source-level points for B7-S3 and D5 (Wave 2; read from source, none run):
- **No DR check before the swap.** The updater checks only the minisign signature. It never checks that the new bundle satisfies the running app's DR, which Sparkle does (C31). A release accidentally signed ad hoc, or with a re-issued certificate, would silently reset grants on every Mac. **Proposed requirement:** before the rename, run `SecStaticCodeCheckValidity` on the extracted bundle against the running app's DR, and refuse on mismatch. An attacker would then need both the minisign key and the code-signing key.
- **No rollback on macOS.** The backup temp dir is dropped (deleted) when `install_inner` returns. If the final rename fails, the app is gone.
- **Tar entries are joined without `..` sanitisation.** This is gated by minisign, so it matters only if the update key leaks.
- **Folder permissions.** A 0700 temp dir is renamed into place, so the updated `.app` may be owner-only (B7-S1-dr, from source).
- **Cross-volume rename** (for example, an app run from the stick) will probably fail.
- **Admin password prompt** (AppleScript) when the app folder is not writable. This favours `~/Applications`.
- **Quarantine:** whether the updated bundle gets `com.apple.quarantine` is unknown; the kit checks with `xattr -l`.

### 6. Windows: Smart App Control against unsigned builds and unsigned self-updates (K5, K6, K9 verified; K7, K10 contested; K8 secondary-only)

- **The rule (verified, K6).** SAC's signature checks "apply to all executable files, not just those downloaded from the Internet". It blocks unsigned files unless they have positive reputation. So the USB route that avoids SmartScreen (T2 item 8) does not avoid SAC.
- **The outcome for a tiny fleet (hypothesis, K7 contested).** "Reputation anew with every update … hundreds of clean installs" is documented for **SmartScreen**. SAC's allow path is Microsoft's app intelligence (ISG). No source documents how ISG treats a binary seen on a handful of PCs. The SAC kit tests this. Its NoISG audit leg shows deterministically which files would need a cloud "yes".
- **Each self-update is a new unsigned installer (verified, K5).** The installer then writes a new unsigned app exe. Two failure points, untested:
  1. **The installer is blocked at launch.** `ShellExecuteW` probably fails, the updater returns an error, and **the old app keeps running**. But `on_before_exit` has already run, which may have stopped the engine. Windows may also show its own error dialog.
  2. **The installer starts, but a later file is blocked**: an NSIS plugin DLL unpacked to `%TEMP%`, or the new app exe at relaunch. Old files may already be replaced, so **no app is left running**.

  The draft said the old app always exits first. That was wrong. The SAC kit must record which case happens, the updater's returned error, and whether the old app is still running (kit amendment 7). B7-S3 designs for both.
- **The SAC state can change after enrolment.** Evaluation turns On "in most cases" (C20). If the 2026 reports are right (C34, secondary-only), any relative or a Windows Security nudge can also switch SAC On at any time. SAC checks binaries at their next load (C17), so an installed unsigned Reliquary could stop at the next restart (K8, secondary-only). Microsoft says a toast announces enforcement, but what a user sees when an auto-started background agent is blocked is unknown. The opposite is also documented: Evaluation turns SAC Off for users it would disrupt.
- **Self-signing does not help (K9).** SAC considers only Trusted Root Program RSA signatures. S14 is dated 2022 and is stale, but no newer source contradicts it.
- **Turning SAC off (ADR-0002 §5 fallback).** Off has always been possible from Settings (2025 docs). What 2025 docs called impossible is turning it back On without a clean install. 2026 reports say that is now possible (C34). Either way it removes protection from a relative's PC. If the toggle is now two-way, "turn it off" is also not durable: the relative can turn it back on, and Reliquary then stops.

**Kit method:** the registry value or `citool -lp` for the mode (C28); CodeIntegrity 3076/3077 per file (C17); the `SmartAppControlAuditNoISG` policy on a lab PC (C28); and a real SAC-On PC (H5 L13) for the user-facing dialog.

### 7. The "cost of not signing" evidence table (for OD-09; owned by B7)

Money figures are Microsoft's and Apple's list figures as cited, not quotes. Owner-time effects are estimates for the owner to check against BUD-SUPPORT (≤ 2 h/month) and BUD-ENROLL (≤ 20 min unaided enrolment). "Expected" means not yet observed. Status tags refer to the key claims.

| Option | Money | Owner effort | First launch from USB | Each self-update | Main risk | Evidence |
|---|---|---|---|---|---|---|
| **Windows: unsigned** (ADR-0002 §5 today) | $0 | Guide screenshots; SAC triage per PC; SAC-state monitoring (C29) | SAC Off: nothing (no MOTW). SAC On: blocked unless the cloud predicts safe (K6 verified; outcome K7 contested). Evaluation: runs for now | SAC On: same rule for each new installer and exe; two failure points (§6). Later Evaluation → On or a manual switch: the installed app may stop (K8 secondary-only) | Lost backups on SAC PCs; the fallback weakens the relative's PC; no deterministic path | K5, K6, K7, K8 |
| **Windows: self-signed** | $0 | Admin install of a root on every PC | Same as unsigned for SAC | Same as unsigned | Adds a trusted root to family PCs for no SAC benefit | K9 |
| **Windows: Azure Artifact Signing** | ≈ $9.99/month (≈ $120/year); paid Azure subscription (K11) | Identity validation ("a few business days", C36; real-world time is H5 L08); Individual billing account with matching legal name and address; renewal of validation; CI integration; 72 h certificates need timestamping; **sign every PE** | Expected to run under SAC (Trusted Root signature; designed for SAC, K12) **if every loaded PE is RSA-signed and timestamped** | Expected to run, same condition | Eligibility (individuals US/CA only); signing stops if validation lapses; **online signing credential in CI/Azure** (compromise lets an attacker sign as Reliquary); **revocation blast radius** (a broad revocation could block installed builds fleet-wide); RSA not confirmed (K12) | K11, K12, C36 |
| **Windows: OV certificate** | $150–300/year plus token or cloud HSM (K13) | CA validation ("several business days", S17); HSM or token in CI; sign every PE. Possible 2026 CA/B Forum cuts to maximum validity (unverified) would raise renewal effort | Expected to run if RSA and every PE is signed | Expected to run | Key on a token complicates CI | K9, K13 |
| **Windows: SignPath Foundation** | $0 if eligible | Application; public OSS repo (OD-15) | As OV | As OV | Eligibility not verified | C26 |
| **Windows: Microsoft Store** | $0 for **MSIX** only (C35) | MSIX packaging of a background engine (unchecked); Store review per release | No SAC or SmartScreen issue (Microsoft re-signs MSIX) | Store handles updates | Changes the ADR-0002 §4 channel; an EXE/MSI Store submission still needs paid signing (C35) | C35 |
| **Windows: submit each release to Microsoft (wdsi) for review** | $0 | A submission per release | Effect on SAC/ISG undocumented | Same, every release | Not a plan; listed so it is explicitly dismissed | S20 (FAQ mention, per skeptic) |
| **macOS: ad hoc** (ADR-0002 §5 today) | $0 | Support calls after updates | Fine from USB (no quarantine) | Photos and Files and Folders prompts again; **FDA silently lost**; Keychain prompt | Relatives click Don't Allow; backups stop | K1, C32 |
| **macOS: stable self-signed + credential outside Keychain** | $0 | One more offline key (D5); CI DR check; long-lived certificate | Same as ad hoc | TCC: **hypothesis: no prompts** (B7-S1). Keychain: not used (D3 choice) | TCC may reject non-Apple anchors; re-issue resets grants once; key leak | K2, K3 (contested), C32 |
| **macOS: stable self-signed, credential in Keychain** | $0 | As above | Same as ad hoc | TCC: as above. **Keychain prompt every update** (C32) | Out-of-context keychain-password prompt | C32 |
| **macOS: Developer ID + notarisation** | $99/year (H5 L07; shared with iOS if OD-01 says yes) | Membership renewal; notarisation in CI | Fine from USB and from downloads | No prompts (Apple-documented; `teamid:` partition) | Lapse stops new signing | C6, C32 |

**Downloads (the other-computers wizard, ADR-0002).** Signed builds still show SmartScreen warnings until their hash builds reputation (S16, S18). Signing fixes SAC and the USB route, not the download warning, so the guide still needs the "More info → Run anyway" screenshots for downloads.

### 8. Conflicts between scouts, analyst and skeptics, resolved

| Conflict | Resolution |
|---|---|
| Draft: the self-signed identity keeps Keychain access (TN2206). Skeptics: partition IDs say no. | **Skeptics upheld.** Synthesis re-read `clientid.cpp` and `acls.cpp` (C32). TN2206 is superseded for the keychain. |
| Draft: rcodesign needs a hand-compiled DR (scout). Spike: it derives one. | **Spike upheld** (S25, B7-S1-dr). Require `O=` so both tools emit `certificate root`. |
| Draft: SAC can only be re-enabled on a clean install (Learn 2025), so ADR-0002 §5's "now allows this without reinstalling" is contested. Skeptics: 2026 KBs made it reversible. | **Probably the ADR text is right for current 24H2/25H2 builds** (C34, secondary-only; KB pages blocked). D5 should **not** amend that line. The SAC kit records the build and KB level and what Settings allows. |
| Draft: a blocked update leaves no app running. Skeptics: `exit(0)` only after a successful launch. | **Skeptics upheld.** Two failure points (§6). |
| Draft: identity validation time undocumented. | S17 says "a few business days" (C36); H5 L08 keeps the real-world figure. |
| Draft: Store is free with no SAC issue. | Only for MSIX (C35). |
| Artifact Signing organisation regions: 4 (S17) vs 12 (S19) | S19 (newer) is current. |

### Alternatives compared

| Option | Fit with settled requirements | Pros | Cons | Evidence |
|---|---|---|---|---|
| A. Status quo: no OS signing; macOS ad hoc | Matches ADR-0002 §5 literally | $0 | macOS grants and Keychain reset every update; Windows SAC-On PCs depend on an undocumented cloud prediction | K1, K6, C32 |
| B. $0 hardened: macOS stable self-signed (TCC) + credential outside Keychain; Windows unsigned + SAC census + SAC-state monitoring | Probably within §5's "no OS code signing" (a self-signed certificate is not an OS vendor's signature); **owner to confirm in OD-09** | $0 | macOS TCC arm unproven; weaker credential isolation; Windows SAC risk unchanged and can appear after enrolment | K2, K3 (contested), C32, K6 |
| C. B + Windows signing (Artifact Signing, else OV; SignPath if OSS) | **Amends ADR-0002 §5** (OD-09) | The only documented, deterministic route through SAC for first launch and updates; ≈ $120/year | Recurring cost; identity chores; eligibility; online signing credential; all PEs must be signed | K6, K9, K11–K13 |
| D. C + Apple Developer ID | Amends §5; overlaps OD-01 | Apple-documented TCC and Keychain persistence; notarised downloads | +$99/year; notarisation pipeline | C6, C32 |
| E. B + "turn SAC off" in the guide | Within §5; ADR-0002 names it | $0 | Weakens relatives' PCs; not durable if SAC can be turned back on; hard for non-technical users | K10, C34 |
| F. Microsoft Store (MSIX) | Changes the ADR-0002 §4 channel | Free; Microsoft re-signs | MSIX packaging of a background engine unchecked; per-release review | C35 |
| G. Apple Development certificate from a free Apple account | Probably not usable for distribution (licence terms not read); lifetime unknown | Would map to `teamid:` | Not evaluated; one line so it is ruled in or out in Wave 2 | C32 |

### Similar work and lessons

| Project | What they do | Borrow or avoid | Source |
|---|---|---|---|
| Sparkle 2 | Accepts an update if EdDSA **or** the DR matches; refuses to drop code signing | Borrow: an on-device DR-continuity check before the swap, plus a CI check | S24 |
| yabai | Self-signed "Code Signing" certificate to keep a TCC grant across rebuilds | Practice evidence for the TCC hypothesis; outcome not stated | S27 |
| skhd.zig | Self-signed certificate keeps Accessibility grants across rebuilds on macOS 15/26; ad hoc loses them | Supports the TCC hypothesis; same-machine caveat (certificate in the developer's keychain) | S32 |
| LocalSend | README says Windows binaries are signed | Comparable OSS apps obtain Windows signing | source scout |
| YARG #1695, cicada PR #129 | Reportedly: TCC lost on each ad-hoc update | Titles only; **not used as evidence** | docs scout |

### Tools and libraries

| Name | Purpose | Licence | Maturity | Source |
|---|---|---|---|---|
| `codesign`, `csreq`, `tccutil`, `xattr`, `security`, `log stream` (macOS) | Sign, show DRs, reset TCC, quarantine, keychain and trust settings, securityd `integrity` logs | Apple | Shipped with macOS | S1, S31 |
| `rcodesign` (apple-codesign 0.29.0) | Sign macOS bundles from Linux CI; derives the self-signed DR | MPL-2.0 | Active | S25 |
| `tauri-plugin-updater` 2.13.0 | Minisign-verified self-update | MIT/Apache-2.0 | Active | S10 |
| `apple-native-keyring-store` 1.0.2 | Rust Keychain access | not recorded | 1.0.2 | S26 |
| `citool.exe`, SAC audit policies, CodeIntegrity events | SAC mode and per-file blocks | Microsoft | Windows 11 | S15 |
| `SmartAppControlPolicy` (WinRT) | App-side SAC state and change events | Microsoft | Documented | S22 |

## Spikes

| Spike | Hypothesis | Pass → / fail → (decision) | Exec tag | Budget IDs | Data class | Status | Result |
|---|---|---|---|---|---|---|---|
| **B7-S1** macOS identity across updates. Kit: [`docs/research/kits/B7-S1/`](kits/B7-S1/README.md) | Arm A (ad hoc): TCC grants and the Keychain item are lost. Arm B (stable self-signed): **TCC survives (hypothesis)**; **Keychain prompts (C32; the kit README still says pass, see amendment 1)**. Arm B' (rcodesign v2 over codesign v1): as B. Arm C (Developer ID, only if H5 L07 exists): all survive. Helper arm: SMAppService LaunchAgent attributed to the app. | **TCC verdict** (per arm): B passes → self-signed for macOS in ADR-0022, $0; only C passes → OD-09 option D. **Keychain verdict**: B fails as predicted → D3 picks non-Keychain storage (§3), **not** an escalation to Developer ID by itself. | OL | BUD-SUPPORT | `SYN+LAB → results`; test signing key `SEC` | **Kit-ready** | No measurements yet. Probe (`probe/main.swift`) not compiled: the container has no Apple SDK. `update.sh` dry-run on Linux with an xattr stub. Needs Apple Silicon on macOS 26.4+ plus a macOS 15 row (VM allowed, recorded). |
| **B7-S1-dr** DR written by rcodesign (container prep for B7-S1). [`spikes/B7-S1-dr/`](../../spikes/B7-S1-dr/README.md) | Ad hoc embeds no DR and the cdhash changes per build; self-signed gets `identifier … and certificate root = H"<sha1>"`, identical across v1/v2 | Pass → Linux CI can sign the self-signed arm without a hand-compiled DR | CT (**emulated**, Linux, not macOS) | none | `PUB+SYN → results` | **Pass (emulated)** | Ad hoc: no DR; v1 cdhash `bf1be157…`, v2 `855cb1c6…`; same bytes re-signed → same cdhash. Self-signed with `O=`: DR `identifier "org.reliquary.b7s1probe" and certificate root = H"409d403c…"` in both, equal to the certificate SHA-1. Without `O=`: rcodesign still pins `root` (DRMaker would pin `leaf`). rcodesign needs `--timestamp-url none` offline; it cannot read OpenSSL 3 default `.p12` (use `-legacy`). Build outputs deleted. |
| **B7-S2-SAC** SAC first launch and self-update (T1 spike 1, Windows leg). Kit: [`docs/research/kits/B7-S2-SAC/`](kits/B7-S2-SAC/README.md) | SAC On: unsigned v1 exe and installer blocked from exFAT despite no MOTW; each self-update exposed (two failure points, §6; **the kit README's "no app left running" needs amendment 7**). Evaluation: runs now, blocked after the switch to On. NoISG audit: a 3076 for every unsigned PE. Signed arm (RSA, Trusted Root): runs. | Any SAC block → OD-09 option C (or E as last resort). No block on a real SAC-On PC including the update → option B viable for the pilot; re-test every release. | OL | BUD-ENROLL, BUD-SUPPORT | `SYN → results`; updater test key `SEC` | **Kit-ready** | No measurements yet. `tauri-probe/` (unsigned Tauri v2 app v0.1.0/v0.2.0, LAN updater) not compiled; config checked against plugin 2.13.0 source and tauri-docs v2. PowerShell scripts (`collect-state.ps1`, `export-ci-events.ps1`, `check-files.ps1`, `simulate-update.ps1`) not run (no PowerShell in the container). Six parts: census; NoISG audit; first launch on a lab PC and a real clean-install SAC-On PC; self-update; Evaluation → On with the app installed; Settings reversibility on the lab PC. |
| **B7-SAC-census** (Part 0 of the SAC kit). [`census.ps1`](kits/B7-S2-SAC/census.ps1) | Unknown share of family PCs in On or Evaluation | Any On or Evaluation → supports option C. None → evidence for B **for current PCs only**, weaker if SAC can be switched On later (C34) | FM | none | `FAM → AGG` (counts per state and build) | **Kit-ready** | No data. Read-only, no admin, sends nothing; shown to the person first. Whether a standard user can read `VerifiedAndReputablePolicyState` is unverified (recorded as "unreadable" if not). |
| B7-S2 (rest of the first-run matrix) | Non-technical tester installs from exFAT/FAT32 on Win10/11, macOS 15/26, Ubuntu, Fedora, Mint, with no admin prompt | As PLAN | OL | BUD-ENROLL | `SYN → results` | **Deferred to Wave 2** | macOS exFAT first launch is optional Part U of the B7-S1 kit. |
| B7-S3 Update mechanics | Crash-loop rollback within 2 launches; locked files replaced; offline USB update | As PLAN | CT/OL | none | `SYN → results` | **Deferred to Wave 2** | Inputs from source reading only (§5, §6): two Windows failure points; macOS no rollback; AppleScript admin fallback; cross-volume rename; 0700 temp dir; tar `..`; no on-device DR check. |
| B7-S4 Antivirus scan | Defender clean; at most 1 generic detection | As PLAN | CT/OL | none | `SYN → results` | **Deferred to Wave 2** | The SAC kit includes only T1 spike 1's single Defender `MpCmdRun` scan. |

No emulator stood in for real hardware in any result above except B7-S1-dr, which is labelled "emulated" and shows only what is written into a signature.

### Required amendments to the kits (from skeptic review)

The kit files were written before the skeptic stage and were not edited in this synthesis stage. **These amendments supersede the kit READMEs where they differ** and must be applied to the kit files before the owner runs them.

**B7-S1:**
1. **Arm B Keychain expectation → "prompt (partition mismatch)".** Arm A stays "prompt". Arm C stays "no prompt".
2. **Split the verdict** into (a) TCC continuity (Photos, Desktop/Documents, removable volume, FDA) per arm, which decides self-signed vs Developer ID, and (b) Keychain continuity per arm, which goes to D3. "TCC pass, Keychain fail" for arm B maps to **option B plus a D3 storage change**, not to Developer ID.
3. **No local trust contamination.** Create the certificate and sign in a **separate macOS user or machine** (or with rcodesign on Linux). Run the probe in a fresh test user that has never imported the certificate. Before installing v1, record `security find-certificate -a -c "Reliquary B7-S1"` and `security dump-trust-settings` (both empty for that certificate). If step 3's `add-trusted-cert` was needed to sign, it must happen in the signing user only. Record both conditions in `results.md`.
4. **Capture securityd evidence** during the v2 first launch: `log stream --predicate 'subsystem == "com.apple.securityd" AND category == "integrity"'` (look for `ACL partition mismatch: client cdhash:…`), plus the item's ACL and partition list before and after (`security dump-keychain -a` on the test keychain).
5. **Expiry sub-test** with and without a timestamp (C33).
6. **Record the TCC result separately from the FDA heuristic**, because FDA fails silently and is not prompted.

**B7-S2-SAC:**

7. Replace hypothesis 2's "no version of the app is left running" with the two failure points in §6. Record `ShellExecuteW`'s result (the updater's returned error in the probe log), whether the old app process still runs, and any OS error dialog.
8. Record the Windows build **and installed KB level** (C34), and in the reversibility observation note both directions (Off → On and On → Off).
9. The signed arm passes only with **zero 3076/3077 events across install, update and uninstall**, with every PE (app exe, NSIS installer, uninstaller, plugin DLLs) RSA-signed and timestamped.

## Conflicts with settled text

1. **ADR-0002 §5 / CLAUDE.md "No Apple or Windows code signing for now".** Options C and D amend it. They are routed through OD-09, and D5 owns any amending draft. Not resolved here.
2. **ADR-0002 §5 "self-updated binaries must be re-signed ad hoc".** With the Tauri updater this is unnecessary (K5). Under a self-signed key kept offline it is impossible. Moving from ad hoc to a stable self-signed identity is **more than wording**: it adds an offline signing key and changes the literal text. It needs D5's amending draft and the owner's confirmation in OD-09 that a $0 self-signed identity is within "no OS code signing".
3. **ADR-0002 §5 "Microsoft now allows this [turning SAC off] without reinstalling"** is **withdrawn as a conflict**. Off was always allowed from Settings (2025 docs). Re-enabling without a reinstall is reported for 2026 builds (C34, secondary-only). D5 should not amend this line. What is still open is whether to rely on it, which this note advises against (§6).
4. **Pilot default (if OD-09 is not decided).** Marking SAC-On or Evaluation PCs "unsupported for the pilot" drops some Windows PCs, while Windows is a settled v1 platform. It is acceptable only as a **temporary scope reduction the owner explicitly accepts** in OD-09.

## Open questions

| Question | Who answers | By when |
|---|---|---|
| Does TCC honour a DR anchored to a non-Apple self-signed certificate across updates (Photos, Files and Folders, FDA), with no local trust for that certificate? | B7-S1 (owner, Apple Silicon Mac, H5 L14) | Before Gate C; P0 |
| Does the codesign shipped on macOS 15/26 emit the same default DR as `DRMaker` on `main`? | B7-S1 (`codesign -d -r-`) | With B7-S1 |
| Does `tccd` validate with `kSecCSCheckTrustedAnchors`? What happens after certificate expiry, with and without a timestamp? | B7-S1 expiry sub-test | With B7-S1 |
| Does `SMAppService` register and attribute a LaunchAgent for ad-hoc or self-signed apps? | B7-S1 helper arm | Gate C |
| Does the Tauri-updated bundle carry `com.apple.quarantine`, and is it owner-only (0700)? | B7-S1 / B7-S3 | Wave 2 |
| Does SAC's cloud prediction ever allow an unsigned Reliquary build on a real SAC-On PC, first launch and update? What does the user see for a blocked background agent? | SAC kit (H5 L13) | Before ADR-0003 (T1 spike 1) |
| Can SAC be switched Off → On and On → Off on current 2026 builds without reinstalling? Which KB? | H1 allowlist (support.microsoft.com, blogs.windows.com), then the SAC kit | Wave 2 |
| How many family PCs are in SAC On or Evaluation, on which builds? Can a standard user read the registry value? | SAC census (FAM → AGG) | Before OD-09 (Gate C) |
| Do Artifact Signing public-trust certificates use RSA? | Inspect any public Artifact-Signing-signed binary before purchase; kit signed arm | Before buying L08 |
| Is the owner eligible for Artifact Signing (individual in US/CA with an Individual billing account, or an organisation in a listed region)? | Owner (H2 intake) | Gate C |
| Does the Tauri v2 bundler sign NSIS plugin DLLs and the uninstaller? | G1 / B7 Wave 2 | Wave 2 |
| Is Reliquary eligible for SignPath Foundation (OD-15)? Other low-cost Trusted-Root OSS certificates (unverified) | G3 / owner | Gate C |
| Does SAC Evaluation weigh installed unsigned apps when deciding to switch Off? | Not documented; observation only | Open |
| Can a Developer ID profile authorise `keychain-access-groups` (data protection keychain)? Is a free Apple Development certificate usable for family distribution? | B7 Wave 2 / B4 | Wave 2 |
| Defender and consumer AV on unsigned self-updates | B7-S4 | Wave 2 |

## Recommendation

1. **macOS: do not plan on plain ad hoc** (K1 verified).
   - **TCC.** The planned default is a stable self-signed identity. **The decision waits for B7-S1's TCC verdict**, because the TCC behaviour is a hypothesis (K3 contested). Use a long-lived certificate with `O=` in the subject, the key kept offline (D5), a CI check that every release has the same DR (`codesign -d -r-`), and an on-device DR check before the swap (D5/B7-S3).
   - **Keychain.** Plan for the device credential to live **outside the Keychain** (a D3 choice, §3). Apple's current source shows that only Apple-issued identities avoid a prompt after each update (C32).
   - **Escalate to Developer ID ($99/year) only if** B7-S1's **TCC** leg fails, the owner rejects non-Keychain credential storage, or OD-01 buys the membership for iOS anyway.
2. **Windows: plan to sign.**
   - The supporting facts are all verified. SAC blocks unsigned files without positive reputation, wherever they come from (K6). Each update runs new unsigned binaries (K5). Self-signing does not count (K9).
   - Whether Microsoft's cloud ever lets a low-volume unsigned build through is undocumented (K7 contested). So without a signature, each release's fate on a SAC-On PC is a gamble per release, and the SAC state can change after enrolment.
   - Use **Azure Artifact Signing** if the owner is eligible, otherwise an **OV certificate**. Check SignPath Foundation if the repo goes public.
   - Sign **every PE** (app, installer, uninstaller, NSIS plugins) with RSA and a timestamp.
   - Keep "turn SAC off" only as a last resort.
3. **What would change this:**
   - The SAC kit shows a real SAC-On PC allowing unsigned Reliquary builds, first launch and update, **and** the census finds no On or Evaluation PCs. Then option B is defensible for the pilot, provided the client watches `SmartAppControlPolicy` and the owner re-tests each release.
   - B7-S1 shows TCC rejecting the self-signed arm. Then macOS goes to option D.

## Decision requests

### OD-09: Signing spend (Windows and/or Apple Developer ID)
- **Needed by:** Gate C (earlier if the SAC kit or T1 spike 1 shows a block during the pilot)
- **Evidence:** this note (§3, §6, §7); ADR-0022 draft (`docs/adr/0022-desktop-packaging-and-self-update.md`); kits B7-S1 and B7-S2-SAC; `h5-long-lead-items.md` L07, L08, L13, L14; `b4-ios-decision.md` (OD-01 overlap)
- **Options:**
  | Option | What it means for the family | Cost (money and owner time) | Reversibility | Risks |
  |---|---|---|---|---|
  | A. No spend; macOS ad hoc | Mac users re-grant Photos and folders and lose FDA after each update, plus a Keychain prompt; SAC PCs depend on Microsoft's cloud | $0; high support time | easy | Silent backup gaps |
  | B. No spend; macOS stable self-signed (TCC, pending B7-S1) + credential outside the Keychain (D3); Windows unsigned + census + SAC-state monitoring | Macs probably keep grants (untested); SAC PCs blocked or need SAC off | $0; one more offline key; census | easy | SAC (also after enrolment); unproven TCC arm; weaker credential isolation |
  | C. B + Windows signing (Artifact Signing, else OV; SignPath if OSS) | Windows works with SAC On, including updates | ≈ $120/year (Artifact) or $150–300/year + token (OV); identity checks and renewals; every PE signed in CI | easy (stop paying; timestamped builds stay valid unless revoked) | Eligibility; lapse stops releases; online signing credential; revocation blast radius |
  | D. C + Apple Developer ID | Apple-documented macOS behaviour; Keychain without prompts; notarised | C + $99/year | easy | Lapse stops new macOS signing |
- **Also confirm:** that a $0 **self-signed** macOS identity is within ADR-0002 §5's "no OS code signing for now" (it is not an OS vendor's signature, but it replaces the literal "re-signed ad hoc").
- **Recommendation:** **C.** macOS escalates to **D** only if B7-S1's **TCC** leg fails, the owner refuses non-Keychain credential storage, or OD-01 buys the membership.
- **Touches settled text:** yes, ADR-0002 §5. D5 owns the amending draft: the signing-spend change and the "re-signed ad hoc" wording. The SAC-toggle line should **not** be amended (Conflicts, item 3).
- **If no decision by the deadline:** the run assumes **B**, with three conditions:
  1. The owner explicitly accepts that SAC-On and Evaluation PCs are a **temporary scope reduction** for the pilot.
  2. The client watches `SmartAppControlPolicy.Changed` and tells the owner when a PC turns SAC On.
  3. The census is re-checked before each release.

  The Start-here guide keeps "turn SAC off" with a warning.

### Proposed follow-up requests (for H1 to file; not added to the shared queue by this note)
- **Allowlist:** support.microsoft.com (KB5074105, KB5083769, KB5083806, the SAC FAQ) and blogs.windows.com, to settle C34 and the "no Run anyway" wording.
- **Budget question for H2:** should B7-S1's criterion get its own budget ID for "user-visible prompts per update", or stay under BUD-SUPPORT?

## Skeptic issues and how they were handled

| Severity | Issue | Disposition |
|---|---|---|
| Critical | Keychain partition IDs defeat "self-signed keeps Keychain access" | **Fixed.** C32 added and re-read; Q2/Q3, §3, §7, options, recommendation and OD-09 rewritten; D3 hand-off made primary; kit amendments 1, 2, 4 |
| Major | B7-S1 pass rule bundles TCC and Keychain | **Fixed** in the decision mapping; kit amendment 2 (kit file not edited in this stage: see unresolved issues) |
| Major | SAC toggle evidence outdated; ADR-0002 §5 line wrongly flagged | **Fixed.** C34 added (secondary-only); Conflicts item 3 withdrawn; the "SAC can be turned On later" failure mode added to §6, §7 and the no-decision default |
| Major | B7-S1 kit can be contaminated by local certificate trust | **Fixed** as kit amendment 3 (kit file not edited in this stage) |
| Major | "Blocked installer leaves no app running" contradicts source order | **Fixed.** Two failure points in §6; kit amendment 7; B7-S3 hand-off |
| Major | SmartScreen evidence used as SAC/ISG evidence at medium-high | **Fixed.** Q7 split into rule (high) and outcome (medium, hypothesis); the recommendation rests on K5, K6, K9 |
| Minor | rcodesign needs no hand-compiled DR | Fixed (§2, §8) |
| Minor | Certificate expiry partly answerable from source | Fixed (C33, §2; kit amendment 5) |
| Minor | Off was always possible; On is what was contested | Fixed (§6, Conflicts item 3) |
| Minor | Store "no SAC issue" applies to MSIX only | Fixed (C35, §7, option F) |
| Minor | Artifact Signing: Individual billing account; "a few business days" | Fixed (C36, §7) |
| Minor | ADR-0022 should not adopt D5's key and CI decisions | Fixed: stated as requirements to D5 and an OD-09 confirmation line; the ADR-0022 draft does likewise |
| Minor | The default-to-B fallback leaves Evaluation PCs failing silently | Fixed: `SmartAppControlPolicy` monitoring is a condition of the default |
| Minor | Every PE must be signed for option C | Fixed (§7, recommendation, kit amendment 9, G1 hand-off) |
| Minor | Artifact Signing online credential and revocation blast radius | Fixed (§7; D1 and D5 hand-offs) |
| Minor | No on-device DR check before the macOS swap | Fixed (§5; D5 and B7-S3 hand-offs) |
| Minor | SmartScreen still warns on signed downloads | Fixed (§7 note) |
| Minor | macOS updater has no rollback; tar `..` | Fixed (§5; B7-S3 and D5 hand-offs) |
| Minor | S14 is stale | Fixed (Sources; K9 note); RSA check kept in the kit and before purchase |
| Missed alternatives | Keychain broker helper; free Apple Development certificate; skhd.zig; wdsi submission; other OSS certificates; Store MSIX full trust; reducing FDA dependency | Added (§1, §3, §7, alternatives F and G, similar work, open questions). The CA/B Forum validity cut and other OSS certificate offers are noted as unverified |

## Hand-offs

| To | What | Why |
|---|---|---|
| D3 | **Now, not as a fallback:** on macOS without an Apple-issued identity, the device credential cannot stay in the file-based Keychain without a prompt after each update (C32). Choose a `0600` file (optionally wrapped), a rarely rebuilt keychain-broker helper, or Developer ID | ADR-0014 owns credential storage |
| D5 | (1) Self-signed macOS signing key as a second offline release key: long validity, `O=` in the subject, expiry on the custody calendar. (2) CI DR-continuity assertion, plus an on-device DR check before the swap. (3) ADR-0002 §5 amending draft: signing spend (OD-09) and the "re-signed ad hoc" wording. **Do not** amend the SAC-toggle line. (4) If C: release order (Authenticode online first, then minisign offline), and the online Artifact Signing credential. (5) The macOS updater's tar `..` handling | ADR-0015, release runbook |
| D1 | Threats: a leaked macOS signing key inherits TCC grants; CI or Azure compromise signs malware as Reliquary; a broad Authenticode revocation blocks the Windows fleet; a SAC flip stops backups on a PC | Threat register |
| B7-S3 (Wave 2) | Two Windows failure points (§6); macOS has no rollback and deletes its backup on return; cross-volume rename; 0700 temp dir; admin prompt for `/Applications`; on-device DR check | Updater mechanics |
| G1 | If C: CI signs and verifies **every PE**, including NSIS plugins and the uninstaller (check Tauri v2 bundler coverage); rcodesign flags (`--timestamp-url none`; `.p12 -legacy`) | CI pipeline |
| B1 / E3 | `SmartAppControlPolicy.Changed` as a health signal ("this PC now blocks Reliquary"), a **condition** of option B; avoid any dependency on Full Disk Access where possible | Health and nudges; desktop runtime |
| E1 / E5 | Census adds the SAC state, Windows build and KB level. The guide must not rely on SAC staying off. Signed downloads still need SmartScreen screenshots | Census and kit copy |
| T1 | The Windows leg of spike 1 is the B7-S2-SAC kit. K6 is verified; K7 is the hypothesis under test | ADR-0003 input |
| Kit maintainer (B7 spike runner) | Apply kit amendments 1–9 to `kits/B7-S1/` and `kits/B7-S2-SAC/` before the owner runs them | The kits predate the skeptic stage |
| H1 | Blocked sources in Method; allowlist request | Run rules §5.4 |
| H2 | Owner eligibility for Artifact Signing (billing account type); budget question on prompts per update | Intake |
