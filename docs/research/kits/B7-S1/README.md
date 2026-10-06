# Kit B7-S1: macOS app identity, privacy grants and Keychain across a self-update

- **Spike:** B7-S1 (workstream B7, see `docs/research/PLAN.md`, section "B7."). P0.
- **Exec tag:** OL (needs a real Mac; a cloud container cannot run macOS).
- **Prepared by / date:** B7 spike runner (agent), 2026-09-29
- **Who runs it:** Owner
- **Time needed:** about 1 h setup, then about 45 min per signing arm and macOS version (4 to 6 h in total for the required rows). The optional expiry sub-test adds a 24 h wait.
- **Data-handling class:** `SYN+LAB → results`, plus `SEC` for the throwaway test signing key (never committed, deleted at the end). Run everything in a **new, empty macOS test user account** (suggested short name `b7test`): no family photos, documents or keychain items are ever touched. The probe records counts, status codes and hashes of synthetic secrets only.
- **Also covers:** the macOS leg of T1 spike 1 ("ad-hoc-signed .app from USB on current macOS"), as optional Part U.

## Purpose

Reliquary will update itself on family Macs. This kit finds out whether macOS still recognises the updated app as the same app, so that permissions already granted (Photos, Desktop and Documents folders, USB drives, Full Disk Access) and a saved Keychain secret keep working **without new prompts**. It compares three ways of signing the app, and checks whether a background helper (LaunchAgent) is treated as part of the app.

## Hypothesis

From Apple documents and Apple's open-source signing code (research note `docs/research/b7-packaging-self-update.md`, claims C1–C12):

| Arm | Signing | Expected after the v1 → v2 update |
|---|---|---|
| **A** | Ad hoc (`codesign -s -`), what ADR-0002 §5 and Tauri's `"signingIdentity": "-"` give | **Fail.** The designated requirement (DR) is the build's cdhash, so every privacy grant is lost: prompts come back, Full Disk Access stops working, and the Keychain asks for permission. |
| **B** | Stable self-signed certificate, same certificate for every release (Apple `codesign`) | **Pass (medium confidence).** DR = `identifier "org.reliquary.b7s1probe" and certificate root = H"<SHA-1 of our cert>"`, identical in v1 and v2. No Apple document confirms that TCC honours a non-Apple anchor; this arm decides it. |
| **B'** | Same certificate, but v2 signed with `rcodesign` (the tool a Linux CI would use) | **Pass** if B passes. The container spike `spikes/B7-S1-dr/` showed that rcodesign 0.29.0 writes the same DR form (emulated, not verified by macOS). |
| **C** | Developer ID Application (only if the Apple membership, H5 L07, exists) | **Pass** (Apple-documented). |
| **Helper** (with A and B) | Engine runs as a LaunchAgent registered with `SMAppService` | macOS attributes the helper's access to the app ("responsible code"), so the helper needs no grants of its own. Unknown for ad hoc and self-signed code. |

The hypothesis is proved wrong for arm B if any prompt appears after the update, or if any check that worked in v1 fails in v2.

## Decision it informs

| If the result is… | Then… |
|---|---|
| **Pass**: arm B passes (Photos, Desktop/Documents, Full Disk Access and a Keychain item all survive the update to v2 with no prompts) | ADR-0022 (B7) plans a stable self-signed macOS identity at $0. D5 adds the signing key to the offline key inventory; CI checks that the DR is the same in every release. OD-09 needs no Apple spend for macOS (unless OD-01 buys the membership for iOS anyway). |
| B passes, B' fails | Same as above, but release signing must run on a Mac (`codesign`), not on Linux CI. Input to G1 and D5. |
| **Fail**: only arm C passes | OD-09: Developer ID ($99/year, H5 L07) is needed for macOS, which partly reverses ADR-0002 §5 (D5 owns the amendment). |
| A passes (unexpected) | Ad hoc is enough; record the macOS versions, because Apple documents the opposite (TN3127). |
| Helper arm fails (the helper is prompted separately, or is blocked) | T1 spike 6 / B1: run the engine inside the app process on macOS, or give the helper its own grants; record which. |
| **No result** (no Mac available) | The macOS column of the "cost of not signing" table stays "expected, untested". OD-09 is decided on paper evidence, and ADR-0022 says so. |

## Budget IDs cited

- **BUD-SUPPORT** (owner time ≤ 2 h per month). Each prompt after an update on each family Mac is a likely support call. The pass criterion itself is PLAN's: **zero prompts and zero lost access after the update**. No new threshold is introduced. (The research note asks H2 whether a separate budget for "prompts per update" is wanted.)

## Equipment

| Item | Exact model or version | Why | Have it? |
|---|---|---|---|
| Apple Silicon Mac on **macOS 26.4 or later** | record model and `sw_vers` | required row; TN3137's 26.4 keychain change | Yes / Borrow / Buy (H5 L14) |
| macOS **15.x** on Apple Silicon | a second Mac, or a macOS 15 VM on the same Mac (record that it was a VM) | required row: the version most family Macs may still run | |
| Intel Mac (any supported macOS) | optional | only if family Macs are Intel | |
| USB stick | any; format it as exFAT and name it `B7S1STICK` | removable-volume grant; Part U | |
| Xcode Command Line Tools | `xcode-select --install` | builds the probe with `swiftc` | |
| `rcodesign` 0.29.0 | `cargo install apple-codesign --version 0.29.0 --no-default-features --locked` (needs Rust) | arm B' only | optional |
| Apple Developer ID Application certificate | only if H5 L07 is already bought | arm C only | conditional |

**Software and files in this folder:**
- `probe/main.swift`: the probe app. **Not compiled in the research container** (no Apple SDK there). Expect to fix small compile errors in the first build; note each fix in `results.md`.
- `probe/Info.plist.in`, `probe/org.reliquary.b7s1probe.helper.plist`, `probe/entitlements.plist`: bundle files.
- `build.sh` (build v1 and v2), `make-cert.sh` (throwaway self-signed identity), `sign.sh` (sign one arm), `update.sh` (apply an update exactly as `tauri-plugin-updater` 2.13.0 does on macOS), `collect.sh` (record signing facts, TCC log lines and probe results).

**What the probe checks** (each run writes one JSON file):
`self` (the DR, cdhash and certificate hashes that macOS computes for the running build), `photos` (PhotoKit authorisation; asset count only), `documents`, `desktop`, `downloads`, `removable_volume` (directory listing: entry count or the error code), `full_disk_access` (can it open the per-user TCC database: a heuristic), `keychain_file_based` (reads the item written by an earlier version, or writes a synthetic one), `keychain_data_protection` (the same with `kSecUseDataProtectionKeychain`; expected to fail with -34018 because there is no provisioning profile), and `helper_status`.

## Before you start

- [ ] Create a new **standard** macOS user (System Settings > Users & Groups), short name `b7test`. Log in as that user for everything below. Do not sign in to iCloud in it.
- [ ] In the test user, open Photos once so an empty library exists. Optionally import 3 to 5 LAB pictures (no people, no home, location off; H3 R8).
- [ ] Copy this kit folder to `~/b7s1` in the test user (not inside a git checkout, so `secrets/` can never be committed).
- [ ] Install the Command Line Tools, then run `cd ~/b7s1 && chmod +x *.sh && ./build.sh`. **You should see:** "built …/v1/ReliquaryProbe.app", "built …/v2/…", and two **different** SHA-256 lines.
- [ ] Format the stick as exFAT named `B7S1STICK`, plug it in, then run:
  `mkdir -p ~/Library/Application\ Support/org.reliquary.b7s1 && echo /Volumes/B7S1STICK > ~/Library/Application\ Support/org.reliquary.b7s1/volume-path.txt`
- [ ] Write down `sw_vers` and the Mac model in `results.md`.

## Procedure

Launch the probe **only with `open` or a double-click**, never by running the binary from Terminal. Otherwise macOS attributes access to Terminal, not to the probe.

**Recording rule:** for every prompt or dialog, write down its exact words, its buttons and which one you clicked, and take a screenshot. When a prompt appears after an update, click **Allow** or **OK** (write down that you did), so the later steps can continue.

### Per-arm run (repeat for arms A, B, B' and, if available, C; on macOS 26 first, then macOS 15)

Set `ARM` to `adhoc`, `selfsigned`, `selfsigned-rcs` or `devid`.

**Part B / B' only, once:** make the identity.
1. Run `./make-cert.sh`. **You should see:** a SHA-1 fingerprint, and the identity listed by `security find-identity` (possibly marked as not trusted). Write the fingerprint down.
2. Arm B: `./sign.sh selfsigned <SHA-1 without colons>`. Arm B': `./sign.sh selfsigned-rcs secrets/selfsigned-3650d/id.p12`, **except** that for B' you install v1 from `build/selfsigned/v1` (signed by `codesign`) and update to `build/selfsigned-rcs/v2` (signed by rcodesign). This checks that a Linux-CI-signed release satisfies a Mac-signed one. If rcodesign reports "incorrect password given when decrypting PFX data", the `.p12` uses an encryption rcodesign 0.29.0 cannot read (seen with OpenSSL 3 defaults in `spikes/B7-S1-dr/`): re-export it with an OpenSSL 3 `pkcs12 -export -legacy` and record that you did. **You should see:** two identical DR lines of the form `designated => identifier "org.reliquary.b7s1probe" and certificate root = H"…"`, where the hash equals your fingerprint.
3. If `codesign` refuses the untrusted certificate, copy the exact error into `results.md`. Then trust it for code signing in the test user's own trust settings and retry step 2: `security add-trusted-cert -r trustRoot -p codeSign -k ~/Library/Keychains/login.keychain-db secrets/selfsigned-3650d/cert.pem` (it asks for the test user's password). Record whether this was needed: it is an extra release-pipeline step, not a family-device step.

**Arm A:** `./sign.sh adhoc`. **You should see:** two **different** `cdhash H"…"` DR lines. **Arm C:** `./sign.sh devid "Developer ID Application: …"`.

**Pass 1: engine inside the app.**

1. **Reset.** Run `tccutil reset All org.reliquary.b7s1probe`, then `security delete-generic-password -s org.reliquary.b7s1.file-keychain` (repeat until it says the item could not be found). Remove any "ReliquaryProbe" entry from System Settings > Privacy & Security > Full Disk Access (select it, click −). Run `rm -rf ~/Applications/ReliquaryProbe.app`.
2. **Install v1.** Run `mkdir -p ~/Applications && ditto build/$ARM/v1/ReliquaryProbe.app ~/Applications/ReliquaryProbe.app`. (For B', use `build/selfsigned/v1`.)
3. **First launch of v1.** Run `open ~/Applications/ReliquaryProbe.app`. **You should see:** permission prompts for Photos, Documents, Desktop, Downloads and the USB volume (order may vary). Click Allow each time (for Photos, full access). Then a summary window appears: everything OK except Full Disk Access (DENIED). Keychain file-based shows status -25300 (not found; the probe then writes an item). Keychain data-protection shows an error (expected -34018). Click Quit. Run `./collect.sh ${ARM}_$(sw_vers -productVersion)_v1-first`.
4. **Grant Full Disk Access.** System Settings > Privacy & Security > Full Disk Access > + > choose `~/Applications/ReliquaryProbe.app` and turn it on. Record whether an admin password was asked for (a standard user needs an admin to approve).
5. **Second launch of v1 (baseline).** `open ~/Applications/ReliquaryProbe.app`. **You should see:** no prompts. Everything OK, including Full Disk Access, and Keychain file-based status 0 with "found_existing_item": true. Run `./collect.sh ${ARM}_$(sw_vers -productVersion)_v1-baseline`. If anything is still prompted or denied here, stop: the baseline is broken; record it and fix it before going on.
6. **Update to v2.** Run `./update.sh build/$ARM/v2/ReliquaryProbe.app`. **You should see:** "updated …", "(none)" for extended attributes (no quarantine flag), and the folder permissions. Record them: the updater renames a temp folder into place, so the app folder may end up as `drwx------` (readable by this user only; source reading, see `spikes/B7-S1-dr/README.md`).
7. **First launch of v2.** `open ~/Applications/ReliquaryProbe.app`. **Count and record every prompt** (Photos, folders, USB volume, Keychain). Click Allow on each, and for the Keychain prompt click **Allow** (not Always Allow). In the summary, note each check's status. Run `./collect.sh ${ARM}_$(sw_vers -productVersion)_v2-after-update`.
8. **Look at System Settings.** Under Privacy & Security, open Photos, Files & Folders and Full Disk Access. Record whether "ReliquaryProbe" appears once or twice, and whether its switches are on. Take screenshots.
9. **Second launch of v2.** `open ~/Applications/ReliquaryProbe.app`. Record any prompts; there should be none now. Run `./collect.sh ${ARM}_$(sw_vers -productVersion)_v2-second`.
10. **Optional, strong evidence: what TCC stored.** Give **Terminal** Full Disk Access in this test user only, then run:
    `sqlite3 ~/Library/Application\ Support/com.apple.TCC/TCC.db "select service, auth_value, hex(csreq) from access where client='org.reliquary.b7s1probe';"`
    For each row, save the hex to a file and decode it: `echo <hex> | xxd -r -p > /tmp/req.bin && csreq -r /tmp/req.bin -t`. Paste the decoded requirement text into `results.md`. It should equal v1's DR for arms B, B' and C. Full Disk Access lives in the system database (`/Library/Application Support/com.apple.TCC/TCC.db`, needs `sudo`); query it the same way if you can. Remove Terminal's Full Disk Access afterwards.

**Pass 2: engine as a LaunchAgent helper** (arms A and B; C too if available).

1. Reset as in Pass 1 step 1. Also run `open ~/Applications/ReliquaryProbe.app --args --unregister-helper` if a previous run registered it. Install v1 as in step 2.
2. **Register the helper.** `open ~/Applications/ReliquaryProbe.app --args --register-helper`. **You should see:** a summary with "status_after" `enabled` or `requiresApproval`, and possibly a macOS notification about a background item. If it says `requiresApproval`, turn on "ReliquaryProbe" in System Settings > General > Login Items & Extensions. Record every notification and the wording shown there. Run `./collect.sh ${ARM}_helper_v1-registered`.
3. **Let the helper ask first.** The agent runs at load; if not, run `launchctl kickstart -k gui/$(id -u)/org.reliquary.b7s1probe.helper`. Record every prompt, and **whose name** it shows (ReliquaryProbe, or something else). Click Allow. Run `./collect.sh ${ARM}_helper_v1-first`.
4. **Then the app.** `open ~/Applications/ReliquaryProbe.app`. Record whether the app is prompted again for things the helper was already granted. None means attribution works.
5. Grant Full Disk Access to the app as in Pass 1 step 4, then kickstart the helper again (step 3 command). Record whether the helper's `full_disk_access` is OK (FDA granted to the app covering its helper).
6. **Update.** `./update.sh build/$ARM/v2/ReliquaryProbe.app`, then kickstart the helper. Record prompts and statuses, whether `launchctl print gui/$(id -u)/org.reliquary.b7s1probe.helper` still shows the agent, and whether Login Items still lists it. Run `./collect.sh ${ARM}_helper_v2-after-update`.

**Optional Part X: certificate expiry (arm B).** Run `./make-cert.sh 1` and sign v1 and v2 with that certificate's SHA-1. Do Pass 1 steps 1–5 with it. After more than 24 hours, launch v1 again and record whether all checks are still OK and what `codesign --verify --strict -vv` says. Then try `./sign.sh selfsigned <SHA-1>` again and record whether signing with the expired certificate still works. This tells D5 whether the self-signed certificate's lifetime matters.

**Optional Part U: first launch from a USB stick (T1 spike 1, macOS leg).**

1. Copy `build/adhoc/v1/ReliquaryProbe.app` onto the exFAT stick with Finder. Eject it, then plug it back in.
2. On the stick, run `ls -la` and `xattr -lr`, and `codesign --verify --strict -vv /Volumes/B7S1STICK/ReliquaryProbe.app`. Record whether `._` files exist and whether the signature still verifies.
3. Double-click the app **on the stick**. Record every Gatekeeper dialog word for word. Then drag it to `~/Applications`, launch it there, and record again. Run `xattr -lr ~/Applications/ReliquaryProbe.app` and check for `com.apple.quarantine`.

**Stop and record "No result" if:** the probe cannot be built after small fixes; macOS refuses to run any arm at all (record the dialog); or the baseline (Pass 1 step 5) cannot be reached.

## Cleaning up

1. For each arm: `tccutil reset All org.reliquary.b7s1probe`; `open ~/Applications/ReliquaryProbe.app --args --unregister-helper`; `rm -rf ~/Applications/ReliquaryProbe.app`; `security delete-generic-password -s org.reliquary.b7s1.file-keychain`.
2. Delete the test identities: `security delete-identity -c "Reliquary B7-S1 Test Code Signing" ~/Library/Keychains/login.keychain-db` (repeat per certificate). If you added trust in Part B step 3, remove it: `security remove-trusted-cert secrets/selfsigned-3650d/cert.pem`.
3. **Delete `~/b7s1/secrets/`** (SEC). Keep only `results/` and `results.md`.
4. Remove Terminal's Full Disk Access if you gave it. Delete the `b7test` user when all rows are done.

## Data handling

H3 classes (`docs/research/h3-research-data-governance.md` §2): inputs are SYN (probe, synthetic keychain secrets) and optional LAB pictures; the signing key is SEC. The JSON files contain status codes, counts, cdhashes, DRs, certificate subjects and SHA-1s, the OS version, and 16-hex-digit prefixes of synthetic secrets' hashes. They contain no file names and no content. `tcc-log.txt` is filtered to the probe's bundle id, but it may contain the test user's home path: check that before sharing. Arm C's JSON contains the owner's Developer ID name and Team ID; redact them if the results are to be shared beyond the owner. Only `results.md` and the `results/` folder may be pasted into the repo or an agent session.

## Results

Copy this section into `docs/research/kits/B7-S1/results.md` and fill it in. Do not edit numbers afterwards; add a note instead.

- **Run by / date / place:**
- **Hardware and OS actually used:** (model, chip, `sw_vers` for each row; say which rows were VMs)
- **Emulator or VM used instead of real hardware?** No | Yes: (which rows)
- **Compile fixes needed for `probe/main.swift`:** (none, or list)
- **Needed to trust the self-signed certificate before `codesign` would sign?** Yes / No (exact error text)

**Per arm and macOS version** (one table per row of the matrix):

| Step | Expected | What happened (prompts: exact words, button clicked) | Measurement | Evidence file |
|---|---|---|---|---|
| DR v1 / DR v2 (`signing.txt`) | A: different cdhash; B/B'/C: identical | | DR text | |
| P1-3 first launch v1 | 5 prompts; FDA denied; DP keychain -34018 | | prompt count; status codes | |
| P1-5 baseline v1 | 0 prompts, all OK | | | |
| P1-7 first launch v2 | A: prompts; B/B'/C: 0 prompts | | **prompt count**; each check OK / DENIED; keychain read_status and read_seconds | |
| P1-8 System Settings | | | entries shown once or twice | screenshots |
| P1-10 stored csreq (optional) | equals v1 DR (B/B'/C) | | decoded text | |
| P2-2 helper registration | enabled or requiresApproval | | status; notification words | |
| P2-3/4 helper attribution | prompts name the app; the app is not prompted again | | | |
| P2-6 helper after update | as Pass 1 for that arm | | | |

| Pass criterion (PLAN) | Budget ID | Measured value | Pass / Fail / No result |
|---|---|---|---|
| Arm B: Photos, Desktop/Documents, Full Disk Access grants and a Keychain item all survive the update to v2 **without prompts** (macOS 26) | BUD-SUPPORT | prompts after update = ; checks lost = | |
| Same, macOS 15 | BUD-SUPPORT | | |
| Arm A (expected Fail), for the cost table | BUD-SUPPORT | | |
| Arm B' (rcodesign-signed v2 over codesign-signed v1) | — | | |
| Arm C (if run) | BUD-SUPPORT | | |
| Helper attribution works (arm A / arm B) | — | | |

- **Overall:** Pass (B passes) | Fail (only C passes) | No result
- **Surprises and points of confusion:** (especially the exact prompt words a relative would see after an update)
- **Follow-ups for the workstream:**
