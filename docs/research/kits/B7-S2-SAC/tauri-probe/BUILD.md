# Building the SAC probe (v1 and v2)

A minimal Tauri v2 app with the updater plugin, built twice: **v0.1.0** (installed from the stick) and **v0.2.0** (delivered by the updater). Both are **unsigned** for Authenticode (the arm under test). The updater's own minisign signature is still required by Tauri; it is not an OS signature.

Build on a machine that will **not** be the SAC test PC: a Windows PC with SAC Off, a Windows VM, or a GitHub Actions `windows-latest` runner in a private repo. Nothing here was compiled in the research container (no Windows target). Note any fix you had to make in the kit's `results.md`.

Checked against: `tauri-docs` v2 `plugin/updater.mdx` and `distribute/windows-installer.mdx` (raw GitHub, read 2026-09-29), and `tauri-plugin-updater` 2.13.0 source.

1. Install Rust (stable, MSVC toolchain), Node.js LTS and the WebView2 runtime (already present on Windows 10/11).
2. `npm create tauri-app@latest` and answer: project name `reliquary-sac-probe`, identifier `org.reliquary.sacprobe`, frontend language TypeScript/JavaScript, package manager npm, UI template **Vanilla**.
3. `cd reliquary-sac-probe && npm install && npm run tauri add updater`
4. Make an updater key (test only; data class SEC; never reuse): `npm run tauri signer generate -- -w %USERPROFILE%\.tauri\sacprobe.key`. Copy the printed **public key**.
5. Replace `src-tauri\src\lib.rs` with this folder's `lib.rs`.
6. In `src-tauri\tauri.conf.json` set (merge with what is there):
   ```json
   {
     "version": "0.1.0",
     "bundle": {
       "createUpdaterArtifacts": true,
       "targets": ["nsis"],
       "windows": { "nsis": { "installMode": "currentUser" } }
     },
     "plugins": {
       "updater": {
         "pubkey": "<the public key text from step 4>",
         "endpoints": ["http://<LAN IP of the update server>:8000/latest.json"],
         "dangerousInsecureTransportProtocol": true,
         "windows": { "installMode": "passive" }
       }
     }
   }
   ```
   `dangerousInsecureTransportProtocol` is for this lab test only (plain HTTP on the LAN). Reliquary itself will use HTTPS.
7. In PowerShell: `$env:TAURI_SIGNING_PRIVATE_KEY = "$env:USERPROFILE\.tauri\sacprobe.key"; $env:TAURI_SIGNING_PRIVATE_KEY_PASSWORD = "<the password you chose>"`, then `npm run tauri build`.
8. Keep these as **v1**:
   - `src-tauri\target\release\bundle\nsis\reliquary-sac-probe_0.1.0_x64-setup.exe` (the installer)
   - `src-tauri\target\release\reliquary-sac-probe.exe` (the bare app exe, for the "run straight from the stick" case)
9. Change `"version"` to `"0.2.0"` and `BUILD_MARKER` in `lib.rs` to `"sac-probe build v2"`. Build again (step 7). Keep `reliquary-sac-probe_0.2.0_x64-setup.exe` and its `.sig` as **v2**.
10. Fill in `latest.json.template` (this folder) with the v2 `.sig` file's **content** and the v2 installer URL, and save it as `latest.json` next to the v2 installer.
11. On the update server (any LAN machine; the build machine is fine): put `latest.json` and the v2 installer in one folder and run `python -m http.server 8000` there. **Do not start it until the procedure says so**, so v1's first launch finds no update.
12. Record the SHA-256 of all four files (`Get-FileHash`) in `results.md`.
