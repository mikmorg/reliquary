# Kit F1-S2: live check of self-hosted Ente and Immich against Reliquary's requirements (optional)

- **Spike:** F1-S2 (workstream F1, see `docs/research/PLAN.md`). It is optional, and PLAN shares it with **F2-S1** (the 7-day phone soak).
- **Exec tag:** OL
- **Prepared by / date:** F1 spike-runner agent, 2026-09-29
- **Who runs it:** Owner
- **Time needed:** about 4–6 h hands-on (two installs, the fit probes, one upgrade), plus 7 days of waiting for the soak. The soak adds about 10 min a day to read the counters.
- **Data-handling class:** `LAB → results`. Only test media the owner makes, with no people in it, on a test phone and test accounts. Test credentials count as `SEC` and stay in the homelab.

## Purpose

The F1 fit matrix scores Ente (self-hosted museum) and Immich from their source code and docs (see `spikes/F1-S1/evidence/source-checks.md`, rows S4–S9). This kit checks the same cells on a real install. It also measures what the matrix cannot get from reading:

- how long each system takes the owner to install and upgrade;
- whether a phone's account can delete its history;
- whether the admin can read the stored data;
- whether identical photos from two accounts are stored once;
- what exposure the phone needs to reach the server.

## Hypothesis

These are the results expected from reading the source. Each one can be proved wrong:

1. In both systems, a phone account can delete its own photos from the server. Ente: trash, then delete or empty trash. Immich: delete, then empty trash. Neither has a server setting that stops this.
2. Ente: the admin cannot open photo content from the server's disk or bucket, because it is end-to-end encrypted. Immich: the admin can open originals directly from `UPLOAD_LOCATION`.
3. The same photo uploaded from two accounts takes space twice in both systems (dedup is per user).
4. The phone must reach the server directly: museum's API plus the bucket for Ente, the Immich server for Immich. It does not work if the homelab only makes outbound connections.
5. Ente needs the hidden 7-tap developer setting to point the app at the server; Immich asks for the server URL on first launch.

## Decision it informs

| If the result is… | Then… |
|---|---|
| **Pass**: every observation in the results table is recorded (yes, no or a value) for both systems | The Ente and Immich rows in the F1 matrix are marked "confirmed live" for these cells. Any hypothesis that proved wrong is fed back into ADR-0005 / OD-02: for example, a server setting that blocks device deletes would shrink the "patch size" for that candidate. |
| **Fail** (a system could not be installed or the phone could not connect after the documented steps) | Record where it failed. The install difficulty is itself evidence for the effort and maintenance axes. The affected cells stay "source only". |
| **No result** (not run: the kit is optional) | The cells stay "source only" (S4–S9), and ADR-0005 says so. |

## Budget IDs cited

- **BUD-SUPPORT**: owner time ≤ 2 h per month at steady state. Compare the measured install and upgrade times against it.
- **BUD-TTS**: new photo "sent" (a median under 1 h on idle Wi-Fi) and "stored at home" within 24 h. Measured during the soak.
- **BUD-BAT-D**: phone battery < 2 % per day. Measured during the soak.

## Equipment

| Item | Exact model or version | Why | Have it? |
|---|---|---|---|
| Proxmox VM for Immich | ≥ 4 vCPU, 8 GB RAM, CPU type x86-64-v2 or better. Immich's requirements page gives 6 GB RAM minimum (8 GB recommended) and 2 cores minimum (4 recommended). Since v3, its ML container on amd64 needs x86-64-v2 or better. | Immich server, Postgres, Redis, ML | |
| Proxmox VM for Ente | ≥ 1 vCPU, 2 GB RAM. Ente's quickstart says at least 1 GB RAM and 1 core; the extra RAM is headroom. | museum, Postgres, MinIO (Ente's default S3-compatible store) | |
| Test Android phone | Mid-range Samsung (H5 item L12a) or Xiaomi (L12d), default OEM settings, current OS | Same phone as F2-S1 | Buy or borrow (H5) |
| Wi-Fi network | The LAN the VMs are on. A VPN on the phone is also acceptable. **Do not open ports to the internet.** | Phone must reach both servers | |
| A second test account per system | e.g. `test-a`, `test-b` | Cross-user dedup check | |
| 20 LAB photos and 2 LAB videos | Houseplants or objects, no people, no location. Make them on the test phone. | Test media | |

**Software and files needed:**
- Ente: `sh -c "$(curl -fsSL https://raw.githubusercontent.com/ente/ente/main/server/quickstart.sh)"`, per Ente's quickstart (`docs/docs/self-hosting/index.md` in ente-io/ente, read 2026-09-29).
- Immich: Docker Compose, per `docs/docs/install/docker-compose.mdx` in immich-app/immich (read 2026-09-29). Use the current stable release and write down its version.
- The Ente Photos app and the Immich app, from Play or F-Droid. Write down the versions.

## Before you start

- [ ] Take a Proxmox snapshot of both VMs straight after the OS install, so you can reset.
- [ ] Charge the phone to 100 %. Turn off the phone's own cloud photo backup (Google Photos) for the test period, so the tests do not compete with it.
- [ ] Write down the exact software versions in the results.
- [ ] Start a timer for each install: the install time is a measurement.

## Procedure

Do the steps in order. After each step, write what you saw in the results table, even if it looks unimportant. If something unexpected happens, stop, take a screenshot, and write it down.

**Part A: install (time each one)**

1. Install Immich with Docker Compose following its docs. Stop the timer when you can log in on the web page as admin. **You should see:** the Immich web UI at `http://<vm-ip>:2283`. Record the minutes and any step that needed a doc other than the install page.
2. Install Ente with the quickstart command. Get the sign-up verification code from `docker compose logs`, as the doc says. Stop the timer when you can upload one photo in the web app at `http://<vm-ip>:3000`. Record the minutes.
3. Create two users in each system: `test-a` and `test-b`.

**Part B: connect the phone (enrollment effort)**

4. Immich app: enter the server URL and log in as `test-a`. Turn on backup for the camera folder. Count the screens and taps until backup is on.
5. Ente app: on the first screen, tap 7 times to open developer settings, enter `http://<vm-ip>:8080` (museum's default port in the quickstart; use the port in your `compose.yaml` if different), and log in as `test-a`. Turn on backup. Count the screens and taps. **You should see:** uploads start. If the uploads fail, check the MinIO endpoint in `museum.yaml`. The quickstart script writes `endpoint: localhost:3200` for its buckets (`server/quickstart.sh` lines 181, 189 and 198 at ente commit 7a5993c), and a phone cannot reach `localhost` on the VM. Ente's object-storage doc says the phone and museum must both reach the bucket at the same address, so you will probably have to change it to `<vm-ip>:3200`. Record what you had to change.
6. Write down what network exposure each system needed for the phone to work: which ports, and whether they are reachable only on the LAN or VPN.

**Part C: fit probes**

7. **Delete from the device.** In each app, as `test-a`, delete 3 backed-up photos from the server. Empty the trash if the app offers it. Then check on the server whether the originals are still there (Immich: look in `UPLOAD_LOCATION`; Ente: count objects in the MinIO bucket before and after). **Record:** could the phone delete them (yes/no), and how many hours or days until they were gone from disk?
8. **Can the admin stop step 7?** Look in each admin settings page and config file for any option that stops users from deleting or emptying trash. Record the option name, or "none found". Do not change the source code.
9. **Can the admin read the data?** On the VM, try to open one original photo from storage. Immich: copy a file from `UPLOAD_LOCATION` and open it. Ente: download one object from the MinIO bucket and try to open it as an image. **Record:** opened (yes/no).
10. **Cross-user dedup.** Note the storage used on the server (a `du -sb` of the upload or bucket directory). Upload the same 5 photos from `test-b` (share them to the phone, or use a second profile). Note the storage again. **Record:** the bytes added, compared with the bytes of the 5 photos.
11. **Restore.** Delete the app's local copy of one photo and restore it from the server. Compare the checksum (SHA-256) with the original you kept on your computer. **Record:** identical (yes/no).

**Part D: 7-day soak (shared with F2-S1; skip it if F2-S1 runs it separately)**

12. Leave both apps logged in with backup on and default OEM battery settings. Each day, take 5 new LAB photos at different times. Each evening, record:
    - how many of the day's photos each app shows as backed up;
    - the time of the newest photo on the server (from the web UI);
    - the battery use per app from Android Settings > Battery.
13. On day 4, upgrade each server by one release if one exists, following its upgrade doc. Time the upgrade, and record whether the phone app needed an update too.
14. On day 7, record the totals.

**Stop and record "No result" if:** either install needs you to expose the homelab to the internet to work at all; or the phone cannot connect after following the docs for 1 hour.

## Cleaning up

1. Log out of both apps and uninstall them from the test phone. Delete the LAB photos from the phone if you do not need them for F2.
2. Revert both VMs to the snapshots, or delete them.
3. Delete the test accounts' credentials from wherever you wrote them down. They are `SEC`, and must not go into the repo or the results.

## Data handling

This kit uses LAB media only (no people, no location) and test accounts. Only counts, sizes, times, versions and yes/no answers go into the results. Do not paste file names, photos, logs containing server IPs or tokens, or credentials. Do not use family phones or family photos for this kit.

## Results

Copy this section into `docs/research/kits/F1-S2/results.md` and fill it in. Do not edit numbers afterwards; add a note instead.

- **Run by / date / place:**
- **Versions:** Immich server __ / app __; Ente museum image __ / app __; phone model __ / Android __ / OEM skin __
- **Emulator or VM used instead of real hardware?** VMs for the servers (expected). Phone: No | Yes (what, and why)

| Step | Observation | Immich | Ente | Notes / screenshot |
|---|---|---|---|---|
| 1–2 | Install time to a working web UI (min) | | | |
| 1–2 | Extra docs or fixes needed | | | |
| 4–5 | Screens and taps to connect the phone and start backup | | | |
| 5 | Changes needed so the phone could reach storage | | | |
| 6 | Ports and exposure the phone needed | | | |
| 7 | Phone could delete photos from the server (yes/no) | | | |
| 7 | Time until the deleted originals were gone from disk | | | |
| 8 | Admin setting that blocks user deletes ("none found" or its name) | | | |
| 9 | Admin could open an original from storage (yes/no) | | | |
| 10 | Bytes added by the same 5 photos from a second user ÷ bytes of the photos | | | |
| 11 | Restored photo byte-identical (yes/no) | | | |
| 12 | Photos taken over 7 days / shown as backed up / found on the server | | | |
| 12 | Median time from photo to "on server" (from daily checks) | | | |
| 12 | Battery % per day (Android Settings) | | | |
| 13 | Upgrade time (min); phone app update needed (yes/no) | | | |

| Pass criterion | Budget ID | Measured value | Pass / Fail / No result |
|---|---|---|---|
| Every row above recorded for both systems | — | | |
| Install + one upgrade time, compared with the owner-time budget | BUD-SUPPORT | | (record only; the analyst compares) |
| Photo "on server" within 24 h, median under 1 h on Wi-Fi | BUD-TTS | | |
| Battery < 2 % per day | BUD-BAT-D | | |

- **Overall:** Pass | Fail | No result
- **Hypotheses 1–5:** confirmed or refuted, one line each
- **Surprises and points of confusion:**
- **Follow-ups for F1 (matrix) and F2 (failure catalogue):**
