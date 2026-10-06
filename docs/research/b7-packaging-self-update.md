# B7. Packaging, install-from-USB and self-update mechanics (Wave 1: the cost of not signing, macOS identity across updates, Smart App Control)

- **Workstream:** B7 (see `docs/research/PLAN.md`, section "B7.")
- **Status:** Draft (analyst deep read; not yet through skeptic review)
- **Date:** 2026-09-29 (last updated 2026-09-29)
- **Feeds:** OD-09 (signing spend, Gate C); ADR-0022 (B7, desktop packaging and self-update; owns the "cost of not signing" table); ADR-0015 (D5, update trust root and release signing: supplied with requirements only); ADR-0003 (T1 spike 1 inputs)
- **Depends on:** T1 (`client-stack.md`, spikes 1 and 5), T2 (`fact-check-adr-0001-0002.md`, items 8–10), H5 (`h5-long-lead-items.md`, L07, L08, L13, L14), B4 (`b4-ios-decision.md`, OD-01 overlap with the Apple membership), D5 (not yet delivered)
- **Traceability rows advanced:** Q2-4 (SAC, then the signing decision), C-08 (ad-hoc re-signing after self-update; AV heuristics are Wave 2), R-01 (desktop platforms)
- **Scope of this run:** Wave 1 only. (1) Desk evidence for the B7-S1 kit: macOS identity, TCC and Keychain across ad-hoc-signed self-updates. (2) Desk evidence for a Windows Smart App Control first-launch and self-update test kit, which is also T1 spike 1. (3) The "cost of not signing" evidence for OD-09. Installer formats, updater mechanics (B7-S3), the antivirus scan (B7-S4), Linux, the stick layout and the CI pipeline sketch are Wave 2.

## Summary

**macOS.** Apple says in so many words that ad-hoc-signed code cannot be tracked across versions. Apple's open-source signing code shows why: the identity an ad-hoc app presents is the hash of that exact build. So with ad-hoc signing, **every self-update will lose its privacy grants and trip Keychain prompts**. Here, privacy grants means Photos, Files and Folders, and Full Disk Access (confidence: high).

The same source code shows that a build signed with our own self-signed certificate gets an identity made of the bundle identifier plus that certificate's hash. That identity should therefore survive updates, **at no cost**, as long as every release is signed with the same certificate. No Apple document confirms that TCC honours it, so B7-S1 must test it on a real Mac (medium).

Developer ID ($99/year) is the only arm Apple documents as keeping grants across updates (high).

**Windows.** Microsoft's own developer docs now confirm the ADR-0002 §5 blocker from a primary source: Smart App Control (SAC) checks **every executable, not just downloaded ones**. It blocks unsigned code that has no positive cloud reputation. Each unsigned self-update is a new file with zero reputation. For a family-sized fleet, the realistic outcome is that **every PC with SAC On blocks the first launch and every update** (medium-high until tested).

A signature from a publicly trusted CA is the documented way through. The cheapest is Azure Artifact Signing, at about $9.99/month, and only if the owner is eligible.

**Recommendation for OD-09 (medium confidence):**
- Keep macOS at $0 for now, but build B7-S1's "stable self-signed" arm into the release plan.
- Run the SAC census and the SAC kit before Gate C.
- Plan to buy Windows signing unless the census finds no family PC with SAC in On or Evaluation. Even then, the fallback depends on future PCs and on the SAC state machine, which Microsoft is changing.

## Questions

| # | Question | Short answer | Confidence |
|---|---|---|---|
| 1 | With ad-hoc signing, do TCC grants survive a self-update? | **No.** Apple: an ad-hoc DR "is tied to that specific version of the code"; prompts repeat after each change (C1, C2). Apple source: the ad-hoc default DR is a list of cdhashes (C3). | High |
| 2 | With ad-hoc signing, do Keychain items stay silently readable after an update? | **Expected no.** Without a provisioning profile the app is confined to the file-based keychain (C8, C9). Its ACL trusts the creating app "tracked with its DR" (C7), and that DR is a cdhash (C3). Expect an "allow access" prompt after each update. | Medium-high (inference; hardware test in B7-S1) |
| 3 | Does a **stable self-signed identity** keep TCC and Keychain grants across updates? | **Probably yes.** The default DR for a non-Apple certificate is `identifier` plus the SHA-1 of a certificate in the chain (C4). A v2 signed with the same certificate satisfies v1's DR. TCC checks the recorded DR (C1), and TN2206 says self-signed identities "work by default" for the keychain (C7). No Apple document covers TCC with a non-Apple anchor. | Medium (B7-S1 decides) |
| 4 | Does Developer ID keep them? | **Yes.** Apple designs default DRs for Apple-issued identities so privileges carry over to new versions (C6). | High |
| 5 | Does a LaunchAgent helper get TCC attribution to the app? | **Designed to**, through "responsible code". DTS says to add `AssociatedBundleIdentifiers` if attribution is wrong (C11). On macOS 13+, `SMAppService` registers an agent bundled in `Contents/Library/LaunchAgents`, and it may need user approval (C12). Nothing found on how this behaves with ad-hoc or self-signed code. | Low-medium (B7-S1 helper arm) |
| 6 | Must self-updated binaries be "re-signed ad hoc" on the device (ADR-0002 §5 wording)? | **No, not with the Tauri updater.** It swaps in the whole `.app` as it was signed at build time, and never runs `codesign` on the device (C13). The on-device step is unnecessary, and it would be impossible for the self-signed arm (the private key is not on the device). This refines the wording of ADR-0002 §5; it does not change the decision. | High (source) |
| 7 | How does SAC treat the first launch from USB and each self-update? | SAC checks all executables whether or not they carry Mark-of-the-Web (C16). It evaluates binaries as they load (C17), and blocks unknown, unsigned code unless app intelligence predicts it is safe (C15). The Tauri updater runs a freshly downloaded NSIS installer on every update (C14). Every release is a new unsigned hash starting with zero reputation (C22). **Expect a block on SAC-On PCs, first launch and every update.** | Medium-high (mechanism documented; the ISG prediction for a tiny fleet is untested) |
| 8 | Can the Start-here guide turn SAC off, and can the family turn it back on later? | **Conflicting.** Learn (Nov 2025): SAC can only be *enabled* on a clean install. The testing guide (Oct 2025) says Off/On is "one-way" in Settings. Secondary 2026 reports say a Windows update made it reversible; the primary pages are blocked (C19). | Low |
| 9 | How many family PCs have SAC On or in Evaluation? | **Open.** Needs the census. A census method that needs no admin rights is proposed (C28, C29). | n/a |
| 10 | What is the cheapest route to signing that SAC accepts? | Artifact Signing, about $9.99/month (individuals: US/Canada only; needs a paid Azure subscription). Otherwise an OV certificate at $150–300/year plus a hardware token. SignPath Foundation is free if the repo is open source and qualifies (not verified). The Microsoft Store is free but changes the channel (C23–C27). Self-signed does **not** work for SAC (C18). | Medium-high |
| 11 | Could a PC in SAC Evaluation later break an already-installed unsigned Reliquary? | **Plausible.** Evaluation automatically switches to On "in most cases" (C20). SAC checks binaries at load time (C17). So the next launch after the switch could be blocked. Untested. | Medium (inference) |
| 12 | Defender and consumer antivirus on unsigned self-updating binaries | Out of Wave 1 scope (B7-S4, Wave 2). | n/a |

## Method

- **Sweep:** two scouts (docs; source code), then this analyst's deep read. The analyst re-fetched and read in full: TN3127, TN3137, TN2206 (the subsystem table and the self-signed section), the four MicrosoftDocs SAC and signing pages, the SmartScreen reputation page, and the code-signing-options page. The analyst also read Apple's `Security` sources for the default-DR logic (not covered by the scouts), `tauri-plugin-updater` 2.13.0 `src/updater.rs` (install paths re-checked), both Tauri signing pages, and the Artifact Signing quickstart, FAQ, trust-models and certificate-management pages.
- **Routes used:**
  - `developer.apple.com/tutorials/data/documentation/...json` for technotes, because the HTML renders client-side;
  - WebFetch for two Apple Developer Forums threads; curl got a "verify-human" page, so the quotes come through the fetch summariser, marked as such;
  - raw.githubusercontent.com for the MicrosoftDocs, tauri-docs and apple-oss-distributions sources;
  - static.crates.io for crate source;
  - GitHub MCP code search across the MicrosoftDocs org, to look for any primary statement on the SAC toggle.
- **Blocked sources (to report to H1):**
  - support.microsoft.com, the SAC consumer FAQ. It is still the only claimed primary source for "no Run anyway" and "turn off without reinstalling". EGRESS_BLOCKED.
  - blogs.windows.com: the Windows Insider posts of 2026-01-27 and 2026-03-12, reported to announce a reversible SAC toggle. EGRESS_BLOCKED.
  - techcommunity.microsoft.com (EGRESS_BLOCKED).
  - learn.microsoft.com (blocked by run rules; the MicrosoftDocs source repos were used instead).
  - azure.microsoft.com pricing (the $9.99 figure rests on the Learn page's "approximately $9.99/month").
  - developer.apple.com/forums through curl (bot check; WebFetch worked).
  - WebSearch: this session's search budget was exhausted, so no new searches were possible.
- **Stop rule:** a GitHub code search of the MicrosoftDocs org for SAC toggle wording found no primary source beyond the pages already read. The Apple open-source DR code closed the main unknown the scouts left. No further primary route is known to be open for the SAC toggle.

## Sources

| # | Source (title and URL or mirror path) | Publisher | Published or version date | Accessed | Primary? |
|---|---|---|---|---|---|
| S1 | TN3127 Inside Code Signing: Requirements, `developer.apple.com/documentation/technotes/tn3127-inside-code-signing-requirements` (read via the `/tutorials/data/...json` endpoint) | Apple | 2022-05-03; revised 2024-04-02 | 2026-09-29 | Yes |
| S2 | "On File System Permissions", `developer.apple.com/forums/thread/678819` (Quinn, DTS; via WebFetch summariser with verbatim quotes) | Apple DTS | 2021-04; updated 2026-09-18 | 2026-09-29 | Yes (summariser route) |
| S3 | "How to handle TCC permissions on machines for UI test automation?", `developer.apple.com/forums/thread/730043` (DTS replies; WebFetch) | Apple DTS | 2023-05/06 | 2026-09-29 | Yes (summariser route) |
| S4 | `apple-oss-distributions/Security @ main : OSX/libsecurity_codesigning/lib/StaticCode.cpp` (`defaultDesignatedRequirement`) | Apple (open source) | main HEAD | 2026-09-29 | Yes |
| S5 | `apple-oss-distributions/Security @ main : OSX/libsecurity_codesigning/lib/drmaker.cpp` (`DRMaker::make`, `nonAppleAnchor`) | Apple (open source) | main HEAD | 2026-09-29 | Yes |
| S6 | TN3137 On Mac keychain APIs and implementations (JSON endpoint) | Apple | 2022-11-01; revised 2026-09-24 | 2026-09-29 | Yes |
| S7 | TN3125 Inside Code Signing: Provisioning Profiles (JSON endpoint; "Entitlements on macOS" read) | Apple | not recorded | 2026-09-29 | Yes |
| S8 | TN2206 macOS Code Signing In Depth, `developer.apple.com/library/archive/technotes/tn2206/_index.html` | Apple (archived) | last revised 2016-08-09 | 2026-09-29 | Yes (old) |
| S9 | SMAppService, `agent(plistName:)`, `Status.requiresApproval` (JSON endpoints) | Apple | undated | 2026-09-29 | Yes |
| S10 | `tauri-plugin-updater` 2.13.0 crate, `src/updater.rs` (static.crates.io) | Tauri | 2.13.0 | 2026-09-29 | Yes |
| S11 | `tauri-apps/tauri-docs @ v2 : src/content/docs/distribute/Sign/macos.mdx` | Tauri | undated | 2026-09-29 | Yes |
| S12 | `tauri-apps/tauri-docs @ v2 : src/content/docs/distribute/Sign/windows.mdx` | Tauri | undated | 2026-09-29 | Yes |
| S13 | `MicrosoftDocs/windows-dev-docs @ docs : hub/apps/develop/smart-app-control/overview.md` | Microsoft | ms.date 2025-11-18 | 2026-09-29 | Yes (mirror) |
| S14 | `... : hub/apps/develop/smart-app-control/code-signing-for-smart-app-control.md` | Microsoft | ms.date 2022-09-20 | 2026-09-29 | Yes (mirror) |
| S15 | `... : hub/apps/develop/smart-app-control/test-your-app-with-smart-app-control.md` | Microsoft | ms.date 2025-10-28 | 2026-09-29 | Yes (mirror) |
| S16 | `... : hub/apps/package-and-deploy/smartscreen-reputation.md` | Microsoft | ms.date 2026-05-04 | 2026-09-29 | Yes (mirror) |
| S17 | `... : hub/apps/package-and-deploy/code-signing-options.md` | Microsoft | ms.date 2026-04-20 | 2026-09-29 | Yes (mirror) |
| S18 | `... : hub/apps/package-and-deploy/distribution-feature-status.md` | Microsoft | ms.date 2026-04-17 ("last reviewed April 2026") | 2026-09-29 | Yes (mirror) |
| S19 | `MicrosoftDocs/azure-docs @ main : articles/artifact-signing/quickstart.md` | Microsoft | ms.date 2026-05-21 | 2026-09-29 | Yes (mirror) |
| S20 | `... : articles/artifact-signing/faq.yml` | Microsoft | main HEAD | 2026-09-29 | Yes (mirror) |
| S21 | `... : articles/artifact-signing/concept-trust-models.md` and `concept-certificate-management.md`; `how-to-signing-integrations.md` (via code search fragment) | Microsoft | main HEAD | 2026-09-29 | Yes (mirror) |
| S22 | `MicrosoftDocs/winrt-api @ docs : windows.system.profile/smartappcontrolpolicy.md` | Microsoft | docs HEAD | 2026-09-29 | Yes (mirror) |
| S23 | `MicrosoftDocs/windows-dev-docs @ docs : hub/apps/get-started/best-practices.md` | Microsoft | docs HEAD | 2026-09-29 | Yes (mirror) |
| S24 | Sparkle 2.x `SUUpdateValidator.m`, `SUCodeSigningVerifier.m`, `AppInstaller.m` (raw GitHub, branch 2.x) | Sparkle project | 2.x HEAD | 2026-09-29 (source scout; not re-read by the analyst) | Yes |
| S25 | `apple-codesign` (rcodesign) 0.29.0 crate: CLI, signing settings, certificate docs | G. Szorc | 0.29.0 | 2026-09-29 (source scout) | Yes |
| S26 | `apple-native-keyring-store` 1.0.2 crate (keyring v4 Apple backend): README, `lib.rs`, `protected.rs` | keyring-rs project (publisher not re-checked) | 1.0.2 | 2026-09-29 (source scout) | Yes |
| S27 | yabai wiki "Installing yabai (from HEAD)" (raw GitHub wiki) | koekeishiya/yabai | undated | 2026-09-29 (source scout) | Yes (similar work) |
| S28 | AskWoody, "Windows 11 Smart App Control can now be turned on or off" | AskWoody | 2026 (search snippet only) | 2026-09-29 (docs scout) | No |
| S29 | Windows Insider blog posts of 2026-01-27 and 2026-03-12 (Release Preview builds 26100/26200 .7701 and .8106) | Microsoft | 2026 | **blocked**; titles from a search listing only | Yes, but not read |

## Claims

Skeptic columns are left for the skeptic stage. Claims marked **(inference)** combine primary sources; they are not stated by any one source.

| # | Claim | Sources | Key? | Skeptic 1 (sources) | Skeptic 2 (logic) | Skeptic 3 (adversary/cost/user) | Verdict |
|---|---|---|---|---|---|---|---|
| C1 | macOS records an app's designated requirement (DR) with a privacy grant. On each later access it checks that the running version satisfies that original DR. This is how v1.3 is recognised as the "same code" as v1.2. | S1 | Yes | | | | pending |
| C2 | Apple: "Ad hoc signed code … has a DR but it's tied to that specific version of the code." Unsigned code has no DR, so "macOS can't reliably track the identity". DTS: with unsigned or ad-hoc code "the system can't tell that version N+1 … is the same as version N, and thus you'll encounter excessive prompts." | S1, S2 | Yes | | | | pending |
| C3 | Apple's `SecStaticCode::defaultDesignatedRequirement`: for an ad-hoc signature it returns an OR of `cdhash` terms, one for each architecture's code directory. So any rebuild changes the DR. | S4 | Yes | | | | pending |
| C4 | Apple's `DRMaker`, for a certificate that does not chain to Apple, builds: `identifier "<id>"` AND the SHA-1 hash of one certificate in the chain. That is the highest certificate whose Organization matches the leaf's, up to the root. For a single self-signed certificate it pins that certificate's own hash (as root, or as leaf when there is no O field). The DR does not include the cdhash. | S5 | Yes | | | | pending |
| C5 | **(inference)** Releases signed with the **same** self-signed certificate and the same identifier satisfy each other's default DR. Given C1, TCC and keychain ACLs should therefore carry grants across updates. Two things break this: re-issuing the certificate (its hash changes), and any macOS policy that also demands a trusted anchor for TCC. No Apple document found says TCC does or does not demand one. | S1, S4, S5, S8 | Yes | | | | pending |
| C6 | Default DRs for Apple-issued identities (Apple Development, Developer ID) are designed so that "a privilege … acquired by an existing version of your app is still available to a new version". | S1 | Yes | | | | pending |
| C7 | TN2206 (2016): for Keychain Access Controls, "the creating application is automatically trusted with its item … tracked with its DR". Subsystems that only need code to be "validly signed and stable" (the keychain is named) work with "self-signed identities and homemade certificate authorities … by default". Gatekeeper and the Application Firewall need a trusted anchor. TCC is not covered; the document predates it in its current form. | S8 | Yes | | | | pending |
| C8 | macOS has a file-based keychain (ACLs, `SecAccess`) and a data protection keychain (access groups taken from entitlements that a provisioning profile must authorise). SecItem defaults to the file-based keychain. The data protection keychain is available only in a user login context (not in a launchd daemon). The file-based keychain is "on the road to deprecation" but not deprecated. | S6 | Yes | | | | pending |
| C9 | `keychain-access-groups` is a restricted entitlement that a profile must authorise (TN3125). DTS: "a profile can only authorise code signed with signing identity whose certificate was issued by Apple", so ad-hoc code cannot use an App ID. Therefore ad-hoc and self-signed builds are confined to the file-based keychain. The keyring-rs Apple backend documents the same (error -34018 without entitlements). | S7, S3, S26 | Yes | | | | pending |
| C10 | Since macOS 26.4 a file-based keychain file may depend on a protected entropy file in `/var/db/SystemKeys`. Copying the keychain file alone may not make it usable on another Mac. | S6 | No (incidental; relevant to what "backing up a Mac" means) | | | | pending |
| C11 | DTS: TCC relies on "responsible code". If a launchd agent or daemon is not attributed to its app, add `AssociatedBundleIdentifiers` to its plist. Files and Folders grants are per user; Full Disk Access is system-wide. | S2 | Yes (helper arm) | | | | pending |
| C12 | On macOS 13+, `SMAppService` registers LaunchAgents bundled in the app's `Contents/Library/LaunchAgents`, replacing plists copied into `~/Library/LaunchAgents`. Status `requiresApproval` means the user must act in System Settings before the agent runs. | S9 | No | | | | pending |
| C13 | `tauri-plugin-updater` 2.13.0 on macOS extracts the new `.app` into a temp dir and renames it over the old one (with an admin-password AppleScript fallback on `PermissionDenied`), then runs `touch`. It never runs `codesign`, so the bundle keeps its build-time signature. | S10 | Yes | | | | pending |
| C14 | `tauri-plugin-updater` 2.13.0 on Windows writes the downloaded NSIS or MSI installer to a temp dir, launches it with `ShellExecuteW` (`/UPDATE` for NSIS), and exits. Every update runs a newly downloaded installer executable. | S10 | Yes | | | | pending |
| C15 | SAC allows an app if Microsoft's app intelligence predicts it is safe. If no prediction can be made, it allows the app when it is signed by a CA in the Microsoft Trusted Root Program. "Malware, PUA, and unknown, unsigned code are blocked by default." | S13 | Yes | | | | pending |
| C16 | Microsoft (2026-05-04): "Smart App Control will block execution of unsigned files unless the file has a positive reputation. Smart App Control signature checks apply to all executable files, not just those downloaded from the Internet." So the USB (no Mark-of-the-Web) route does not bypass SAC. This gives T2 item 8's core point a primary source. | S16 | Yes | | | | pending |
| C17 | "Because Smart App Control evaluates binaries as it loads them", developers must test all install and uninstall binaries and every code path. Blocks are logged per file in CodeIntegrity/Operational: event 3076 in evaluation, 3077 in enforcement. | S15 | Yes | | | | pending |
| C18 | SAC supports only RSA signatures (no ECC). "Code can be signed with any certificate, but Smart App Control only considers certificates issued by trusted providers." So a self-signed Authenticode certificate, even one installed as a local root, does not satisfy SAC. | S14, S17 | Yes | | | | pending |
| C19 | **Contested.** Learn (2025-11-18): SAC "can only be enabled on a clean install" (a reset counts). Testing guide (2025-10-28): setting Off or On in Settings is "a one-way operation". The only way to force another mode is an offline registry edit "for testing purposes only". Secondary 2026 reports say a Windows update made SAC switchable on and off without reinstalling; the primary posts are blocked. ADR-0002 §5's "Microsoft now allows this without reinstalling" rests on this unresolved point. | S13, S15, S28, S29 (not read) | Yes | | | | pending |
| C20 | SAC starts in Evaluation. "In most cases Smart App Control automatically turns on"; it is turned off automatically for users it judges would be disrupted. A toast announces enforcement. | S13 | Yes | | | | pending |
| C21 | **(inference)** On a PC in Evaluation, an unsigned Reliquary may run today and be blocked at its next load once SAC moves to enforcement. That would stop backups on that PC with no action by the user. | S13, S15 | Yes | | | | pending |
| C22 | An unsigned file builds SmartScreen reputation "anew with every update", from zero. Reputation carries over only between versions signed with the same publisher identity. There is no threshold, but "it can take several weeks and hundreds of clean installs from a wide audience". **(inference)** A 10–25 device family cannot build reputation for each unsigned release. | S16 | Yes | | | | pending |
| C23 | Azure Artifact Signing: "approximately $9.99/month" (S17). Public Trust is open to individuals in the US or Canada only, and to organisations in the US, Canada, EU, UK, AU, NZ, JP, KR, SG, CH, NO and IL (S19, 2026-05-21; S17 of 2026-04-20 lists fewer). It needs a paid Azure subscription; free, trial and sponsored ones are refused (S20). Signing stops if identity validation lapses (S20). Certificates are valid 72 h and renewed daily, so timestamping is required (S21). | S17, S19, S20, S21 | Yes (cost) | | | | pending |
| C24 | Microsoft says Artifact Signing's Public Trust model is designed to support Authenticode and features such as Smart App Control. It says apps signed with it "enjoy a productive experience … with … Smart App Control and SmartScreen" enabled. Whether its certificates use RSA (which SAC requires) is not stated in the pages read. | S21, S14 | Yes | | | | pending |
| C25 | OV certificates cost "typically $150–300/year". Their keys must be on an HSM or token (CA/B Forum, June 2023). EV costs "$400+/year", and since 2024 it no longer bypasses SmartScreen. | S17, S18, S12 | Yes (cost) | | | | pending |
| C26 | Microsoft points open-source projects to SignPath Foundation for free OV-level signing, subject to eligibility (not checked). | S17 | No | | | | pending |
| C27 | Microsoft Store MSIX distribution is free and worldwide. Microsoft re-signs the package, so there are no SmartScreen warnings. | S17 | No (a channel change, outside ADR-0002 §4) | | | | pending |
| C28 | The SAC mode lives in `...\Control\CI\Policy\VerifiedAndReputablePolicyState` (0 Off, 1 On, 2 Evaluation). `citool.exe -lp` shows the active policy (`VerifiedAndReputableDesktop` or `...Evaluation`). The `SmartAppControlAuditNoISG` policy checks the signing requirement alone, without cloud reputation, and can be applied with SAC Off. | S15 | Yes (kit method) | | | | pending |
| C29 | A WinRT API, `Windows.System.Profile.SmartAppControlPolicy` (`IsEnabled` and a `Changed` event), lets an app read the SAC state and watch for changes. | S22 | No (a later health feature) | | | | pending |
| C30 | Tauri supports ad-hoc signing (`"signingIdentity": "-"`). Its docs warn that this does not avoid the Privacy & Security allow step, and that a free Apple account cannot notarise. Tauri says Windows signing "is not required to execute your application" when users accept SmartScreen or do not download via a browser. It does not mention SAC. | S11, S12 | No | | | | pending |
| C31 | Sparkle 2 accepts an update if the EdDSA signature is valid **or** the new bundle satisfies the old bundle's DR. It refuses updates that remove code signing, and says: "If no Apple Code Signing certificate is available, adhoc signing can be used at minimum". (Read by the source scout; not re-read by the analyst.) | S24 | No (similar work) | | | | pending |

## Findings

### 1. macOS: why ad-hoc signing loses grants on every update (C1–C3, C6)

TN3127 describes the mechanism exactly. When the user grants microphone, Photos or Files and Folders access, macOS stores the app's DR. On each later access, it asks whether the running code satisfies the stored DR (C1). Apple's own code sets an ad-hoc app's default DR to "cdhash is one of {…}" (C3). A rebuild, even an unchanged rebuild with a new version string, fails that requirement. Apple states the resulting behaviour directly: prompts repeat (C2). **Confidence: high.**

What that means for Reliquary:
- **Photos and Files and Folders** (Desktop, Documents, Downloads, removable volumes): the family sees the permission prompt again after each auto-update. The update is silent, so a relative may see "Reliquary would like to access your Photos" out of context and click Don't Allow. Backups of that source then stop.
- **Full Disk Access** cannot be requested by a prompt; the user toggles it in System Settings. After an update the old entry no longer matches the new code (C1, C3). The user would probably have to remove and re-add it; the kit must record exactly what the user sees. For a non-technical relative this effectively means one owner support call per update per Mac, which counts against BUD-SUPPORT.
- **Keychain:** see §3.

### 2. macOS: the "stable self-signed" arm looks viable and costs $0 (C4, C5, C7)

This is the most important new evidence in this run. The scouts could not find what DR `codesign` gives to a non-Apple certificate. Apple's open-source `DRMaker` answers it (C4): `identifier "<bundle id>" and certificate root = H"<sha1>"`, where the hash is of our own certificate. There is no cdhash term. Every release signed with the **same certificate** therefore satisfies the DR recorded for the previous release. The mechanism in C1 then predicts that TCC and Keychain grants carry over (C5). TN2206 explicitly says self-signed identities work "by default" for DR-tracked subsystems such as the keychain (C7). One similar project uses this in practice: yabai asks users of its self-built binary to create a self-signed "Code Signing" certificate and re-sign after each update, to keep its Accessibility grant (S27; the page does not state the outcome).

**Confidence: medium.** Three gaps keep it below high:
- The DRMaker file is the current `main` of Apple's open-source Security project. The kit must still capture `codesign -d -r-` on the real build.
- No Apple document says TCC accepts a DR anchored to a non-Apple certificate. TCC might also check trust (an untrusted self-signed root) when it evaluates the stored requirement; nothing found either way.
- If the certificate is ever re-issued, its hash changes and every grant resets once. So the certificate should be generated with a long validity. Whether macOS rejects the signature after the certificate expires is unknown; the kit should record `codesign --verify` behaviour with a short-lived test certificate.

Practical notes for this arm:
- **Gatekeeper is unchanged.** Gatekeeper needs Developer ID or App Store anchors (S8 table), so a self-signed app behaves like an ad-hoc one: fine from USB without quarantine (T2 item 9), same "Open Anyway" path if quarantined.
- **One more secret for D5's key inventory.** The self-signed code-signing private key must never ship on the device. It sits next to the minisign update key. Losing it means one grant reset on every Mac; leaking it lets an attacker produce code that inherits Reliquary's TCC grants. That is a smaller risk than the update key, because the attacker still needs a delivery route, but it belongs in D1's register.
- **Signing from Linux CI** is possible with `rcodesign`. It derives a default DR only for Apple-issued certificates, so the release pipeline must pass the explicit DR above as a compiled requirement (S25). Alternatively, sign on a Mac with `codesign -s <cert>`, which applies C4 automatically. Either way, CI must assert in every release that `codesign -d -r-` shows the same DR.

### 3. macOS Keychain (C7–C10)

Without a provisioning profile, a Reliquary build cannot use the data protection keychain (C8, C9). The file-based keychain's ACL trusts the creating app by its DR (C7). So:
- **ad hoc:** expect an "allow access to keychain item" prompt after every update, which may ask for the login password (inference, medium-high);
- **stable self-signed:** expect no prompt (inference, medium);
- **Developer ID:** no prompt. It can also claim keychain access groups through a provisioning profile (C9), which opens the data protection keychain that Apple is steering developers towards (C8). Whether a Developer ID profile authorises `keychain-access-groups` was not checked (TN3125 says some entitlements are not supported by Developer ID profiles).

A fallback for the ad-hoc case is not to keep the device credential in the Keychain at all: a `0600` file under `~/Library/Application Support`. That is weaker against other processes of the same user, and D3 must accept it. It is listed only as the fallback if B7-S1's self-signed arm fails and OD-09 refuses Developer ID.

### 4. macOS: the engine inside the app vs a LaunchAgent helper (C8, C11, C12)

The helper arm matters because T1 recommends a separate Rust daemon (client-stack.md, spike 6). Facts:
- a per-user **LaunchAgent** runs in a user context, so either keychain works. A system **LaunchDaemon** is limited to the file-based System keychain (C8);
- TCC should attribute the agent's accesses to the app ("responsible code"), with `AssociatedBundleIdentifiers` as the fix when it does not (C11);
- on macOS 13+ the supported way to register the agent is `SMAppService`, which may put it in "requires approval" (C12).

Two things are unknown and must be observed in B7-S1:
- whether attribution works for ad-hoc and self-signed apps;
- whether `SMAppService` accepts non-Apple-signed apps at all.

The Tauri updater replaces the whole bundle (C13), so a helper inside the bundle changes cdhash together with the app. Under ad hoc, both lose grants.

### 5. The Tauri updater and ADR-0002's "re-sign ad hoc" line (C13, C14)

ADR-0002 §5 says self-updated binaries "must be re-signed ad hoc". With `tauri-plugin-updater`, the signature is applied in CI and travels inside the update archive; the device only swaps directories (C13). Nothing needs re-signing on the device, and under the self-signed arm the device could not do it anyway. The same source shows two more things for B7-S3 (Wave 2):
- the updater uses `rename` between the system temp dir and the app location, so an app on another volume (for example, run from the stick) will probably fail to update. This is the source scout's inference; untested;
- if the app sits in a folder the user cannot write to, the update asks for an **admin password** through AppleScript. That favours installing to `~/Applications`.

Also unknown: whether the updated bundle gets a `com.apple.quarantine` attribute. The updater downloads with its own HTTP client and nothing in the source sets quarantine, but the kit should run `xattr -l` after an update.

### 6. Windows: Smart App Control against unsigned builds and unsigned self-updates (C14–C22)

- **First launch from USB:** SAC's checks "apply to all executable files, not just those downloaded from the Internet" (C16). The USB route that avoids SmartScreen (T2 item 8) does not avoid SAC. An unknown, unsigned binary is blocked unless Microsoft's app intelligence predicts it is safe (C15). **Confidence: high** for the rule. Whether the cloud ever predicts "safe" for a binary seen on a handful of PCs is not documented. C22 suggests not.
- **Every self-update:** the updater downloads and executes a new NSIS installer (C14), which then writes a new app executable. Both are new unsigned hashes starting at zero reputation (C22), and SAC checks them when they load (C17). **Expected result on SAC-On PCs: every update is blocked.** Worse, the update can half-apply: the old app exits before the installer runs, so the installer's block leaves the old app not running until someone relaunches it (C14; inference). B7-S3 must design for that.
- **PCs in Evaluation today** may switch to On later (C20). SAC then checks Reliquary's binaries at their next load (C17). A PC that installed fine in the pilot could stop backing up months later (C21). Whether SAC's evaluation counts an installed unsigned app as a reason to switch itself off is not documented.
- **"No Run anyway":** the primary pages read do not say this in those words. They say apps "cannot be run unless recognized … or signed" (S13). The explicit wording is still only in the blocked consumer FAQ, so it stays **secondary only** (T2 item 8).
- **Self-signing does not help** (C18). Installing our own root on each PC needs admin rights and is still ignored by SAC, which considers only "trusted providers".
- **Turning SAC off** (ADR-0002 §5 fallback): the primary sources disagree with the 2026 secondary reports (C19). Even where it is possible, it removes protection from a relative's PC to make room for our app. The owner should weigh that against about $120/year.

**Kit method (for the spike runner):** use the registry value or `citool -lp` for the mode (C28), CodeIntegrity events 3076/3077 for per-file blocks (C17), and the `SmartAppControlAuditNoISG` policy on a lab PC. That policy deterministically shows which Reliquary files would be blocked without cloud reputation, including after a simulated self-update (C28), so it does not depend on getting a clean-install SAC PC. A real SAC-On PC (H5 L13) is still needed to see the user-facing dialog.

### 7. The "cost of not signing" evidence table (for OD-09; owned by B7)

Costs are Microsoft's and Apple's list figures as cited, not quotes. Owner-time effects are estimates for the owner to check. Budget ID: BUD-SUPPORT (≤ 2 h/month).

| Option | Money | Owner effort | What the family sees (first launch from USB) | What the family sees on each self-update | Main risk | Evidence |
|---|---|---|---|---|---|---|
| **Windows: unsigned** (ADR-0002 §5 today) | $0 | Guide screenshots; SAC triage per PC | SAC Off: nothing (no MOTW). SAC On: **blocked**. Evaluation: runs for now | SAC On: **blocked**. SAC switching Evaluation → On: the installed app stops launching | Silent loss of backups on SAC PCs; the fallback weakens the relative's PC | C15–C22 |
| **Windows: self-signed** | $0 | Admin install of a root on every PC | Same as unsigned for SAC and SmartScreen | Same as unsigned | Adds a trusted root to family PCs for no SAC benefit | C18, S17 |
| **Windows: Azure Artifact Signing** | ≈ $9.99/month (≈ $120/year); paid Azure subscription | Identity validation (duration undocumented; H5 L08); renewal before expiry; CI integration; 72 h certificates need timestamping | Expected to run under SAC (Trusted Root Program signature) | Expected to run: every update is signed | Eligibility (individuals in US/CA only); signing stops if validation lapses; revocation for misuse | C23, C24 |
| **Windows: OV certificate** | $150–300/year plus token or cloud HSM | CA validation; HSM or token handling in CI | Expected to run under SAC (RSA certificate required) | Expected to run | Key on a token complicates CI | C18, C25 |
| **Windows: SignPath Foundation** | $0 if eligible | Application; public OSS repo (OD-15) | As OV | As OV | Eligibility not verified; depends on OD-15 | C26 |
| **Windows: Microsoft Store (MSIX)** | $0 (per S17) | Store submission and review per release | No SAC or SmartScreen issue (Microsoft-signed) | Store handles updates | Changes the channel (ADR-0002 §4); packaging limits for a background daemon not checked | C27 |
| **macOS: ad hoc** (ADR-0002 §5 today) | $0 | Support calls after updates | Fine from USB (no quarantine) | **Photos and Files and Folders prompts again; Full Disk Access must be re-granted; Keychain prompt** | Relatives click "Don't Allow"; backups stop | C1–C3, C7–C9 |
| **macOS: stable self-signed** | $0 | Keep one more private key offline; CI checks the DR | Same as ad hoc | **Expected: no prompts** (not yet tested) | TCC could reject non-Apple anchors (unknown); certificate re-issue resets grants once; key leak | C4, C5, C7 |
| **macOS: Developer ID + notarisation** | $99/year (H5 L07; shared with iOS if OD-01 says yes) | Membership renewal; notarisation in CI | Fine from USB and from downloads | No prompts (Apple-documented) | Membership lapse stops new signing | C6, C30; B4 |

### 8. Scout conflicts resolved

| Conflict | Resolution |
|---|---|
| The docs scout could not find the default DR for self-signed code; the source scout said rcodesign derives DRs only for Apple certificates | Apple's `DRMaker` (S5) gives the rule. rcodesign's limitation applies only when signing from Linux, and is solved with an explicit DR. |
| "SAC can be turned on or off without reinstalling" (ADR-0002 §5, secondary 2026) vs "clean install only" and "one-way" (Learn, 2025) | **Not resolved.** Both are recorded (C19). The SAC kit must record what Settings allows on the test PC's actual build, and the census should record the Windows build. H1: request that blogs.windows.com and support.microsoft.com be allowlisted. |
| Artifact Signing organisation regions: US/CA/EU/UK (S17, Apr 2026) vs a 12-region list (S19, May 2026) | The newer quickstart (S19) is taken as current; H5 F5 agrees. The individual limit (US/CA) is the same in both. |
| Is SAC's "signature check applies to all executables" primary? T2 cited only the FAQ | Yes. S16 (Microsoft Learn source, 2026-05-04) states it. The "no Run anyway" wording is still FAQ-only. |

### Alternatives compared

| Option | Fit with settled requirements | Pros | Cons | Evidence |
|---|---|---|---|---|
| A. Status quo: no OS signing; macOS ad hoc | Matches ADR-0002 §5 literally | $0 | macOS grants reset on every update; Windows SAC-On PCs blocked | C1–C3, C15–C22 |
| B. $0 hardened: macOS stable self-signed; Windows unsigned + SAC census | Within ADR-0002 §5 ("no OS signing spend") | $0; probably fixes macOS | Windows SAC risk unchanged; macOS arm unproven | C4, C5, C16 |
| C. B + Windows signing (Artifact Signing, else OV) | **Changes ADR-0002 §5** (OD-09) | Removes the SAC blocker for first run and updates; ≈ $120/year | Recurring cost and identity chores; eligibility | C23–C25 |
| D. C + Apple Developer ID | Changes ADR-0002 §5; overlaps OD-01 | Apple-documented macOS behaviour; a path to the data protection keychain (profile support not checked); notarised downloads | +$99/year; notarisation pipeline | C6, C9 |
| E. B + "turn SAC off" in the guide | Within §5; ADR-0002 already names it | $0 | Weakens relatives' PCs; reversibility unclear; a relative must navigate Windows Security | C19 |

### Similar work and lessons

| Project | What they do | Borrow or avoid | Source |
|---|---|---|---|
| Sparkle 2 (macOS updater) | Accepts an update if EdDSA **or** the DR matches; refuses to drop code signing; recommends ad hoc "at minimum" | Borrow: CI asserts DR continuity between releases, as Sparkle does at install time | S24 |
| yabai | Self-signed "Code Signing" certificate, re-sign after each update, to keep a TCC grant | Evidence that the self-signed arm is used in practice; the outcome is not stated | S27 |
| LocalSend | README states "Windows binaries are signed" (the source scout read the README; the policy itself was not read) | Suggests comparable OSS apps pay for or obtain Windows signing | source scout |
| YARG #1695, cicada PR #129 | Reportedly: TCC grants lost on each ad-hoc update; fixed with a stable identity | Titles only; **not used as evidence** | docs scout |

### Tools and libraries

| Name | Purpose | Licence | Maturity | Source |
|---|---|---|---|---|
| `codesign`, `csreq`, `tccutil`, `xattr` (macOS) | Sign, show DRs, reset TCC for tests, inspect quarantine | Apple | Shipped with macOS | S1 |
| `rcodesign` (apple-codesign 0.29.0) | Sign macOS bundles from Linux CI, including self-signed with an explicit DR | not recorded | Active | S25 |
| `tauri-plugin-updater` 2.13.0 | Minisign-verified self-update | MIT/Apache-2.0 | Active | S10 |
| `apple-native-keyring-store` 1.0.2 | Rust Keychain access (legacy keychain for apps without a profile) | not recorded | 1.0.2 | S26 |
| `citool.exe`, SAC audit policies (aka.ms/sacauditpolicies), Event Viewer CodeIntegrity | SAC mode and per-file blocks | Microsoft | Shipped with Windows 11 | S15 |
| `SmartAppControlPolicy` (WinRT) | App-side SAC state and change events (future health signal) | Microsoft | Documented | S22 |

## Spikes

A separate spike runner is building these kits in parallel. This section is a placeholder that the runner (or the synthesis stage) completes. The rows below give the analyst's hypotheses and the design inputs the kits should cover.

| Spike | Hypothesis | Pass → / fail → (decision) | Exec tag | Budget IDs | Data class | Status | Result |
|---|---|---|---|---|---|---|---|
| B7-S1 macOS identity across updates (kit: `docs/research/kits/B7-S1/`, path set by the spike runner) | Ad hoc: grants and Keychain prompts reset on v1→v2 (expected fail). Stable self-signed: all survive (expected pass, medium). Developer ID: all survive (expected pass; run only if self-signed fails, per H5 L07). Helper arm: attribution to the app works with `AssociatedBundleIdentifiers`. | Pass (self-signed) → option B for macOS in ADR-0022, $0. Only Developer ID passes → OD-09 Apple spend. | OL | BUD-SUPPORT | SYN/LAB → results; signing keys are SEC | Kit pending (spike runner) | — |
| SAC first-launch and self-update (T1 spike 1; the SAC part of B7-S2; kit path set by the spike runner) | Unsigned exe from exFAT: blocked with SAC On, allowed with Off. A NoISG audit logs 3076 for the app exe and for each updated binary and installer. A signed build (if a trial signature is available) is allowed. | Blocked → OD-09 Windows signing (option C) or guide fallback (E). Not blocked (ISG predicts safe) → option B stays viable; re-test each release. | OL | BUD-ENROLL (first-run path) | SYN → results | Kit pending (spike runner) | — |
| SAC census (inside the E1 census or the SAC kit) | Unknown share of family PCs in On or Evaluation | Any On or Evaluation → option C recommended | FM | none | FAM → AGG (counts per SAC state and Windows build only) | Not started | — |

**Design inputs for the kits:**
1. **B7-S1:**
   - capture `codesign -d -r-`, `codesign -dvvv` and `spctl -a -vv` for v1 and v2 of each arm;
   - build v2 from different source (e.g. a changed string) so the cdhash really changes;
   - test Photos (PhotoKit prompt), Desktop/Documents, a removable volume, Full Disk Access, and one Keychain generic password written by v1 and read by v2;
   - record `SecItem` errors with and without `kSecUseDataProtectionKeychain` (expect -34018 without a profile);
   - update via the real Tauri updater path, not a Finder copy, and run `xattr -l` on the updated bundle;
   - run on macOS 15 and macOS 26 (26.4 or later, per C10);
   - include a short-lived self-signed certificate case to see behaviour after expiry;
   - reset between runs with `tccutil reset All <bundle id>`.
2. **SAC:**
   - record the Windows build, SAC state (registry value, `citool -lp`), and whether Settings allows Off → On and On → Off on that build (C19);
   - log every dialog and every 3076/3077 event for the app exe, the NSIS installer, NSIS plugin DLLs extracted to `%TEMP%`, and the WebView2 bootstrapper (if bundled);
   - simulate a self-update by installing v1 and then applying v2 through the updater;
   - check the signature algorithm (RSA) of any signed build.
3. **Census:** a read-only PowerShell one-liner on the registry value. It needs no admin rights (to be confirmed in the kit), and the result is shown to the person before export (H3 R6).

## Conflicts with settled text

1. **ADR-0002 §5 ("No OS code signing for now")**
   - The primary evidence now supports the §5 blocker on Windows (C16).
   - If B7-S1's self-signed arm fails, the same section also fails on macOS.
   - Changing the signing spend is OD-09. D5 owns any amendment of §5 (traceability "Superseding or amending drafts").
   - Not resolved here.
2. **ADR-0002 §5, "self-updated binaries must be re-signed ad hoc"**
   - With the Tauri updater, re-signing on the device is unnecessary (C13).
   - Under a self-signed identity, re-signing on the device is impossible, and it must not happen, because the key stays offline.
   - This is a wording correction for D5's amendment, not a change of decision.
3. **ADR-0002 §5, "Microsoft now allows this without reinstalling"**
   - This is contested by the primary Microsoft pages that are reachable (C19).
   - It should stay flagged until a primary 2026 source is read or the kit observes the behaviour.

## Open questions

| Question | Who answers | By when |
|---|---|---|
| Does TCC honour a DR anchored to a non-Apple self-signed certificate across updates (Photos, Files and Folders, Full Disk Access)? | B7-S1 (owner, Apple Silicon Mac, H5 L14) | Before Gate C; P0 |
| Does `SMAppService` register and attribute a LaunchAgent for ad-hoc or self-signed apps? | B7-S1 helper arm | Gate C |
| Does SAC's cloud prediction ever allow an unsigned Reliquary build on a real SAC-On PC? What exactly does the user see? | SAC kit (H5 L13) | Before ADR-0003 (T1 spike 1) |
| Can SAC be switched On → Off and back on current Windows 11 builds without reinstalling (2026 change)? | H1 allowlist (blogs.windows.com, support.microsoft.com), then the SAC kit | Wave 2 |
| How many family PCs have SAC On or in Evaluation, and on which builds? | SAC census (FAM → AGG) | Before OD-09 (Gate C) |
| Do Artifact Signing public-trust certificates use RSA? | Kit check on a signed build, or the Artifact Signing docs | When L08 is bought |
| Is the owner eligible for Artifact Signing (individual in US/CA, or an organisation in a listed region)? | Owner (H2 intake) | Gate C |
| Is Reliquary eligible for SignPath Foundation (depends on OD-15 public repo)? | G3 / owner | Gate C |
| Does SAC Evaluation weigh installed unsigned apps when it decides to switch itself off? | Not documented; observation only | Open |
| Defender and consumer AV on unsigned self-updates | B7-S4 | Wave 2 |

## Recommendation

1. **macOS: keep $0, but stop using plain ad hoc.**
   - Adopt a **stable self-signed code-signing identity** as the planned default in ADR-0022, subject to B7-S1. Use a long-lived certificate, keep the private key offline next to the update key, and have CI check that every release has the same DR.
   - Evidence from Apple's own documents and code says ad hoc will re-prompt after every update. For non-technical relatives that means silent backup gaps and owner support time.
   - If B7-S1's self-signed arm fails on TCC, recommend Developer ID ($99/year). If OD-01 brings iOS into v1, the same membership pays for it.
2. **Windows: plan to sign.**
   - Microsoft's primary documents describe the SAC rule, per-hash reputation and load-time checks. Together they make it very likely that an unsigned, self-updating agent is blocked on any PC where SAC is On, and on any PC that later moves from Evaluation to On.
   - Recommend Azure Artifact Signing if the owner is eligible, otherwise an OV certificate. Check SignPath Foundation if the repo goes public.
   - Keep "turn SAC off" as a documented last resort only, not as the plan.
3. **Evidence that would change this:**
   - the census finds every family Windows PC with SAC Off (and the owner accepts that new or reset PCs will arrive with it in Evaluation);
   - or the SAC kit shows the cloud allowing unsigned Reliquary builds, including after an update.

   Either result would make option B (no Windows spend) defensible for the pilot.

## Decision requests

### OD-09: Signing spend (Windows and/or Apple Developer ID)
- **Needed by:** Gate C (earlier if T1 spike 1 or the SAC kit shows a block during the pilot)
- **Evidence:** this note (§6, §7); B7-S1 kit and SAC kit (spike runner); `h5-long-lead-items.md` L07, L08, L13, L14; `b4-ios-decision.md` (OD-01 overlap)
- **Options:**
  | Option | What it means for the family | Cost (money and owner time) | Reversibility | Risks |
  |---|---|---|---|---|
  | A. No spend; macOS ad hoc | Mac users re-grant permissions after each update; SAC PCs cannot run Reliquary | $0; high support time | easy | Silent backup gaps |
  | B. No spend; macOS stable self-signed; Windows unsigned | Macs probably fine; SAC PCs blocked or need SAC off | $0; key custody; census | easy | SAC; unproven macOS arm |
  | C. B + Windows signing (Artifact Signing, else OV) | Windows works with SAC on, including updates | ≈ $120/year (Artifact) or $150–300/year + token (OV); identity checks and renewals | easy (stop paying; already-signed builds stay valid with timestamps) | Eligibility; lapse stops releases |
  | D. C + Apple Developer ID | Apple-documented macOS behaviour; notarised | C + $99/year | easy | Lapse stops new macOS signing |
- **Recommendation:** **C**, with B7-S1 deciding whether macOS needs D. Windows signing is the only documented way through SAC, which checks every executable, including each self-update. The cost is small next to the risk of a relative's PC silently stopping backups. On macOS, a stable self-signed identity should keep grants at no cost; pay for Developer ID only if B7-S1 shows otherwise, or if OD-01 buys the membership anyway.
- **Touches settled text:** yes. ADR-0002 §5 ("No OS code signing for now"). D5 owns the amending draft. It should also correct the "re-signed ad hoc" line (Conflicts, item 2) and the SAC-toggle claim (item 3).
- **If no decision by the deadline:** the run assumes option B. Windows PCs with SAC On (or in Evaluation) are recorded as unsupported for the pilot, and the Start-here guide keeps the "turn SAC off" fallback with a warning. This blocks enrolling any SAC PC.

### Proposed follow-up requests (for H1 to file; not added to the shared queue by this note)
- **Allowlist request:** blogs.windows.com and support.microsoft.com, to resolve C19 and the "no Run anyway" wording. This extends the H1-S1 Wave 1 request.
- **Budget question for H2:** should B7-S1's pass criterion ("no prompts after an update") be tied to BUD-SUPPORT, or get its own budget ID for "user-visible prompts per update"?

## Hand-offs

| To | What | Why |
|---|---|---|
| D5 | Self-signed macOS code-signing key as a second offline release key; CI DR-continuity check; wording fix for ADR-0002 §5 "re-signed ad hoc" | D5 owns the release runbook and the §5 amendment |
| D1 | Threat: a leaked macOS signing key lets new code inherit TCC grants; a Windows signing identity lapse or revocation stops releases | Threat register |
| D3 | If macOS stays ad hoc: where the device credential lives (file-based keychain with prompts vs a `0600` file) | Credential storage belongs to D3 |
| T1 | C16 turns spike 1's SAC risk into a primary-sourced expectation; use the NoISG audit method | ADR-0003 input |
| E1 / E5 | Add the SAC state and Windows build to the device census; the Start-here guide must not promise SAC can be turned back on | Census and kit copy |
| B1 / E3 | Consider `SmartAppControlPolicy` as a health signal ("this PC now blocks Reliquary updates") | Nudges and health |
| B7-S3 (Wave 2) | Half-applied Windows update when the installer is blocked; cross-volume rename on macOS; admin prompt for `/Applications` | Updater mechanics |
| H1 | Blocked sources listed in Method; allowlist request | Run rules §5.4 |
