# Kit B7-S2-SAC: Smart App Control on first launch from a USB stick and on every self-update

- **Spike:** the Smart App Control (SAC) part of **B7-S2** (workstream B7, see `docs/research/PLAN.md`, section "B7."), which is also the Windows leg of **T1 spike 1** (`docs/research/client-stack.md`: "unsigned USB exe on a clean-install Windows 11 with SAC on and on an upgraded PC; Defender scan"). The rest of B7-S2 (the full first-run matrix on macOS and Linux, run by a non-technical tester) is Wave 2.
- **Exec tag:** OL (lab PCs) for Parts 1–6; FM for the census in Part 0.
- **Prepared by / date:** B7 spike runner (agent), 2026-09-29
- **Who runs it:** Owner (Parts 1–6). Part 0: each relative with a Windows PC, or the owner during a visit.
- **Time needed:** about 2 h to build the probe (once), then about 1.5 h per PC and SAC state. The Evaluation → On leg needs two reboots.
- **Data-handling class:** Parts 1–6: `SYN → results` (the probe app only, on a test Windows account named `sactest`). Part 0: `FAM → AGG`: one line per PC (SAC state, Windows build, edition, CPU type), shown to the person before sharing. The updater test key is `SEC` (throwaway).

## Purpose

Find out what Windows Smart App Control does to an **unsigned** Reliquary app: when it is first started from an exFAT USB stick, and every time it updates itself (each update is a new, unsigned installer and a new app `.exe`). Also count how many family PCs have SAC On or in Evaluation. Together these decide whether Reliquary needs a Windows code-signing certificate (OD-09).

## Hypothesis

From Microsoft's developer documentation (research note `docs/research/b7-packaging-self-update.md`, claims C14–C22, C28):

1. **SAC On:** the unsigned v1 exe and the unsigned v1 installer are **blocked** from the stick, even though files on a stick carry no Mark-of-the-Web. The only exception would be Microsoft's cloud ("app intelligence") predicting the file is safe, which is unlikely for a file only a few PCs have ever seen. *Proved wrong if* v1 installs and runs with no block and no 3077 event for the probe's files.
2. **Every self-update is exposed:** the updater writes a new unsigned installer to `%TEMP%` and runs it, and the installer writes a new unsigned app exe. On SAC On, the update is blocked, and because the old app has already exited, **no version of the app is left running** until someone starts it again (inference from the `tauri-plugin-updater` 2.13.0 source, which exits the app right after launching the installer).
3. **SAC Evaluation:** nothing is blocked now. When SAC switches itself to On later, the installed app is blocked at its next start.
4. **NoISG audit policy** (SAC's signing rule without the cloud): a 3076 event for every unsigned executable file the install and update load (the app exe, the NSIS installer, NSIS plugin DLLs unpacked to `%TEMP%`, the uninstaller). This list is the set of files Reliquary must sign.
5. **Signed arm** (only if a certificate exists): RSA-signed files from a Trusted Root Program CA run under SAC On, first launch and update.

## Decision it informs

| If the result is… | Then… |
|---|---|
| **Pass** (for "no Windows spend"): on a real SAC-On PC, v1 installs from the stick **and** the v2 self-update installs and runs, with no SAC block | Option B (no Windows signing) stays viable for the pilot. Re-test every release, because the cloud prediction is not guaranteed. The census still matters. |
| **Fail**: any SAC block of a probe file (3077 event or block dialog) on first launch or update | OD-09: buy Windows signing (Azure Artifact Signing if eligible, else OV; option C in the note). Without it, SAC-On PCs are unsupported and the Start-here guide keeps the "turn SAC off" fallback (option E). |
| Evaluation → On leg blocks an already-installed app | Even PCs in Evaluation today are at risk: counts towards signing in OD-09, and B1/E3 should watch the SAC state (`SmartAppControlPolicy`) as a health signal. |
| Signed arm runs without blocks | Confirms signing fixes it; the certificate's key algorithm (RSA) and every file the NoISG leg listed go into the release runbook (D5, G1). |
| Census: no family PC has SAC On or Evaluation | Evidence for option B for **current** PCs only; new or reset PCs start in Evaluation. |
| **No result** (no SAC-capable PC) | The SAC risk stays "documented, untested". The note's recommendation (plan to sign) stands on the documents alone, and ADR-0003 / ADR-0022 say so. |

## Budget IDs cited

- **BUD-ENROLL** (a relative enrolls a computer from the kit unaided in ≤ 20 min). A SAC block on first launch makes this impossible on that PC. This kit records the owner's time and every dialog; it does not time a relative (that is B7-S2 proper, Wave 2).
- **BUD-SUPPORT** (owner time ≤ 2 h per month). A blocked self-update means a visit or a call per PC per release.
No new thresholds are introduced.

## Equipment

| Item | Exact model or version | Why | Have it? |
|---|---|---|---|
| **PC-S**: Windows 11 on real hardware, **clean-installed** (or reset), SAC **On** | record model, `winver`, build | the real user-facing dialogs (H5 L13; PLAN §5.5 asks for real hardware) | Yes / Buy (H5 L13) |
| **PC-L**: any Windows 11 PC or VM you can change freely | record; say if it is a VM | NoISG audit leg, Evaluation → On leg, Settings toggle check | |
| Windows 10 22H2 PC or VM | optional | baseline: no SAC on Windows 10 | |
| Windows 11 PC **upgraded** from Windows 10 (not clean-installed) | optional | T1 spike 1 row "upgraded PC" (SAC expected Off) | |
| USB stick formatted **exFAT** | any | the first-launch medium | |
| A LAN machine for the update server | anything with Python 3 | serves `latest.json` and v2 | |
| Build machine (not PC-S) | Windows with Rust + Node, or a GitHub Actions Windows runner | builds the probe (`tauri-probe/BUILD.md`) | |
| SAC audit policies zip | from `https://aka.ms/sacauditpolicies` (link given in Microsoft's SAC testing guide; not fetched by the agent) | `SmartAppControlAuditNoISG.bin` | |
| A Windows code-signing certificate | only if one exists (H5 L08 or OV) | Part 6 only | conditional |

**Files in this folder:**
- `tauri-probe/` (`BUILD.md`, `lib.rs`, `latest.json.template`): builds the unsigned v1 and v2 probe app, a minimal Tauri v2 app with `tauri-plugin-updater` that checks for an update at every start and logs each start to `%LOCALAPPDATA%\ReliquarySacProbe\probe.log`. **Not compiled in the research container.**
- `census.ps1`: Part 0, read-only, no admin.
- `collect-state.ps1`: SAC registry state, `citool -lp`, Defender versions.
- `export-ci-events.ps1`: CodeIntegrity/Operational events since a time (all IDs, plus a 3076/3077 extract).
- `check-files.ps1`: hash, Authenticode status, key algorithm and Mark-of-the-Web for a set of files.
- `simulate-update.ps1`: fallback that reproduces the updater's download-and-run steps, if the in-app update cannot be made to work.

The PowerShell scripts were written for Windows PowerShell 5.1 and were **not run or syntax-checked** in the research container (no PowerShell there). If one fails, note the error and the fix in `results.md`.

## Before you start

- [ ] Build v1 and v2 with `tauri-probe/BUILD.md`, and record the four SHA-256 values.
- [ ] Copy `reliquary-sac-probe_0.1.0_x64-setup.exe` and `reliquary-sac-probe.exe` (v1) to the exFAT stick, in a folder `probe`. Copy this kit folder to the stick too.
- [ ] On each test PC, create a local **standard** account `sactest` and do the tests while logged in as it. Admin steps use a separate admin account (record every time you had to type admin credentials).
- [ ] Note each PC's current SAC state in Settings (Windows Security > App & browser control > Smart App Control settings) before changing anything. PC-L will be changed; PC-S must stay On.
- [ ] Keep each PC online unless a step says otherwise (SAC's cloud check needs the internet).

## Procedure

**Recording rule:** for every dialog, notification or toast, write down its exact words, its buttons and what you clicked, and take a photo or screenshot. Write down the clock time before each launch; `export-ci-events.ps1` needs it.

### Part 0: SAC census (family PCs; FM)

1. Ask the person to open **Settings > Privacy & security > Windows Security > App & browser control > Smart App Control settings** and read out which option is selected: **On**, **Evaluation** or **Off**. Also note the Windows version from **Settings > System > About** (Windows 10 or 11, and the "OS build" number).
2. Alternatively run `census.ps1` from the stick. **You should see:** one line such as `SAC=Evaluation; OS=Windows 11; build=26100.xxxx; edition=Core; arch=AMD64; api_IsEnabled=…`. The person decides whether to share it. If the script itself is blocked, record "script blocked" (that is a SAC result too) and use step 1.
3. Only the aggregate goes into results: counts of PCs per SAC state and per Windows build family. No names of people or PCs.

### Part 1: set up the lab PC (PC-L) for the NoISG audit leg

1. On PC-L, admin PowerShell: `.\collect-state.ps1 -Label L_initial`.
2. Apply the NoISG audit policy exactly as Microsoft's testing guide says (SAC must be Evaluation or Off): run `mountvol S: /S`, copy `SmartAppControlAuditNoISG.bin` to `S:\efi\microsoft\boot\cipolicies\active\{5283AC0F-FFF1-49AE-ADA1-8A933130CAD6}.cip`, then run `citool.exe -r`.
3. `.\collect-state.ps1 -Label L_noisg-applied`. **You should see:** `citool.txt` lists `VerifiedAndReputableDesktopEvaluationAuditNoISG`.

### Part 2: first launch from the stick (run on PC-L with NoISG, then on PC-S with SAC On; optional rows: Windows 10, upgraded Windows 11)

1. Plug in the stick. As `sactest`: `.\check-files.ps1 -Label <PC>_stick -Path E:\probe\*.exe` (use the stick's drive letter). **You should see:** `SigStatus` NotSigned and an empty `ZoneIdentifier` for both files.
2. Note the time. Double-click `E:\probe\reliquary-sac-probe.exe` (the bare exe, straight from the stick). Record what happens. Close the app if it opens.
3. Note the time. Double-click `E:\probe\reliquary-sac-probe_0.1.0_x64-setup.exe`. Record every screen. If it installs, leave "Run" ticked on the last page. Record whether any admin (UAC) prompt appeared; the per-user installer should need none.
4. If the app opened, check `%LOCALAPPDATA%\ReliquarySacProbe\probe.log`. **You should see:** `started version=0.1.0` and `no update available` or `update check error` (the update server is not running yet). Record where the app was installed (the folder of the running exe in the log).
5. Admin PowerShell: `.\export-ci-events.ps1 -Label <PC>_first-launch -Since '<time from step 2>'`, then `.\collect-state.ps1 -Label <PC>_after-first-launch`. **Expect:** on PC-L, 3076 events naming the probe exe, the installer and any DLLs it unpacked; on PC-S, 3077 events if blocked.
6. Defender check (T1 spike 1): `& "$env:ProgramFiles\Windows Defender\MpCmdRun.exe" -Scan -ScanType 3 -File "E:\probe"`. Record the result line.
7. **Stick removal and reboot** (B7-S2 criterion, if v1 installed): eject the stick, reboot, log in as `sactest`, start the app from the Start menu. Record whether it starts and what `probe.log` says.

### Part 3: self-update v1 → v2 (on every PC where v1 got installed)

1. On the update server, start `python -m http.server 8000` in the folder with `latest.json` and the v2 installer. From the test PC, open `http://<server IP>:8000/latest.json` in a browser to check that it is reachable.
2. Note the time. Start the installed app from the Start menu. **You should see:** the app close, a small progress window (passive NSIS), and the app start again. Record every dialog. Wait 2 minutes.
3. Check `probe.log`. **You should see:** `update found: 0.2.0`, then a new line `started version=0.2.0`. If there is no v2 start line, start the app from the Start menu again, and record which version starts (or whether nothing starts).
4. `.\check-files.ps1 -Label <PC>_after-update -Path "<install folder>\*.exe", "$env:TEMP\reliquary-sac-probe-0.2.0-updater-*\*.exe"`. Record whether the downloaded installer has a Zone.Identifier (expected: none).
5. Admin: `.\export-ci-events.ps1 -Label <PC>_update -Since '<time from step 2>'`.
6. If the in-app update failed for a reason that is **not** SAC (see `probe.log`), use the fallback instead: `.\simulate-update.ps1 -Url http://<server IP>:8000/reliquary-sac-probe_0.2.0_x64-setup.exe`, then repeat steps 3–5, and mark the row "simulated update".

### Part 4: Evaluation → On with the app already installed (PC-L; tests note C21)

1. On PC-L, remove the NoISG policy: delete the `.cip` file copied in Part 1 step 2 (`mountvol S: /S` first), run `citool.exe -r`, reboot, and check that `citool -lp` no longer lists the NoISG policy. (Removal is not described in Microsoft's guide; record exactly what you did.)
2. Make sure v2 (or v1) is installed and runs under Evaluation or Off.
3. Force SAC **On** with the registry method in Microsoft's testing guide ("for testing purposes only"): the `manage-bde -protectors c: -disable -rebootcount 2` and `MpCmdRun.exe -RemoveDefinitions -DynamicSignatures` commands, then Advanced Startup > Troubleshoot > Advanced > Command Prompt, and the `reg load` / `reg add` commands with value **1** for `VerifiedAndReputablePolicyState` and `VerifiedAndReputablePolicyStateMinValueSeen`, and `SacLearningModeSwitch` 0. Reboot.
4. `.\collect-state.ps1 -Label L_forced-on`. **You should see:** `VerifiedAndReputableDesktop` enforced in `citool.txt`.
5. Note the time. Start the installed app from the Start menu. Record what happens. Run `export-ci-events.ps1` from that time.
6. If the app was allowed, uninstall it, try to install v1 from the stick, and update to v2 (Parts 2 and 3) under On, recording the same way.

### Part 5: can SAC be switched back? (note C19; record only)

1. On **every** test PC, open Smart App Control settings and record which options can be selected, and the exact wording on the page, together with the Windows build.
2. On **PC-L only**: switch SAC to **Off** in Settings. Then reopen the page and record whether **On** or **Evaluation** can be selected again. This checks, on that build, whether the reported 2026 change (switching back without reinstalling) is present. Never do this on a family PC or on PC-S.

### Part 6 (conditional): signed builds

Only if a Windows code-signing certificate exists. Sign both installers and the app exes (Tauri's Windows signing configuration, see Tauri's "Windows Code Signing" guide), rebuild `latest.json` with the new `.sig`, and repeat Parts 2 and 3 on PC-S (SAC On). `check-files.ps1` must show `SigStatus` Valid and `KeyAlgorithm` RSA.

**Stop and record "No result" if:** no PC with SAC On or in Evaluation is available; the probe cannot be built; or the NoISG policy cannot be applied (record the error).

## Cleaning up

1. Uninstall the probe (Settings > Apps) on every test PC. Delete `%LOCALAPPDATA%\ReliquarySacProbe` and any `%TEMP%\reliquary-sac-probe-*` folders.
2. PC-L: remove the NoISG policy (Part 4 step 1) and return SAC to the state you want; check with `manage-bde -status c:` that BitLocker protection is back on after Part 4 step 3 (`-rebootcount 2` suspends it for two reboots); if not, run `manage-bde -protectors c: -enable`.
3. Delete the `sactest` accounts. Stop the update server.
4. Delete the updater key (`%USERPROFILE%\.tauri\sacprobe.key*`) on the build machine (SEC).

## Data handling

H3 classes (`docs/research/h3-research-data-governance.md` §2). Parts 1–6 use only the synthetic probe on a test account (SYN). The CodeIntegrity CSVs contain file paths that include the account name (`sactest`) and may name other system files loaded during the window: keep the CSVs in the private research store, and paste into the repo only the rows for the probe's own files. Part 0 (FAM → AGG): only the one-line census result, and only after the person has seen it; the repo gets counts per SAC state and build only (H3 §4 output check).

## Results

Copy this section into `docs/research/kits/B7-S2-SAC/results.md` and fill it in. Do not edit numbers afterwards; add a note instead.

- **Run by / date / place:**
- **Hardware and OS actually used:** (per PC: model, real or VM, Windows edition, build, SAC state at start)
- **Emulator or VM used instead of real hardware?** No | Yes: (which PC; PC-S must be real hardware)
- **Build fixes needed for the probe:** (none, or list)
- **SHA-256 of v1 installer, v1 exe, v2 installer, v2 app exe:**

| PC / SAC state | Step | Expected | What happened (dialog words, buttons) | 3076 / 3077 events for probe files (file names) | Evidence |
|---|---|---|---|---|---|
| PC-L NoISG | P2 bare exe from stick | 3076 | | | |
| PC-L NoISG | P2 installer from stick | 3076 for installer, plugin DLLs, app exe | | | |
| PC-L NoISG | P3 self-update | 3076 for new installer and new app exe | | | |
| PC-S On | P2 bare exe from stick | blocked | | | |
| PC-S On | P2 installer from stick | blocked | | | |
| PC-S On | P3 self-update (if v1 ran) | blocked; old app not running | | | |
| PC-L forced On | P4 installed app | blocked at next start | | | |
| any | P2.6 Defender scan | clean | | | |
| any | P2.7 stick removed + reboot | app starts | | | |
| each PC | P5 Settings options | | | | |

| Pass criterion | Budget ID | Measured value | Pass / Fail / No result |
|---|---|---|---|
| SAC On (PC-S): unsigned v1 installs and runs from the exFAT stick with no SAC block | BUD-ENROLL | | |
| SAC On (PC-S): unsigned v2 self-update installs and runs with no SAC block | BUD-SUPPORT | | |
| No admin prompt during install; app survives stick removal and reboot (B7-S2) | BUD-ENROLL | | |
| Signed arm (if run): no SAC block, key algorithm RSA | — | | |
| Census: PCs per SAC state (On / Evaluation / Off / unreadable), per build family | — | counts | n/a |

- **Overall:** Pass (unsigned is not blocked) | Fail (blocked) | No result
- **Surprises and points of confusion:**
- **Follow-ups for the workstream:**
