# Key ceremony runbook

- **Status:** Draft (Wave 1, D2). It has **not** been dry-run as a whole. Individual steps were exercised in the container (D2-S2, and checks M2/M3 in the D2 note). Do not use it with real keys until:
  - ADR-0008 is Accepted;
  - OD-06, OD-08, DR-D2-3 and DR-D2-4 are decided;
  - a full dry run with throwaway keys has passed.
- **Owner:** D2. The printed break-glass runbook is co-owned with E7.
- **Date:** 2026-10-06
- **Evidence:** `docs/research/d2-key-hierarchy-custody-recovery.md` (§F6, §F7); `spikes/D2-S2/`; `docs/research/kits/D2-S3/`
- **Assumes:** OD-06 = PQ (`mlkem768x25519`); A6 posture A′; OD-08 option A, 2-of-3. Adjust the parameters if the owner decides otherwise.
- **Data class:** the ceremony handles `SEC` material. No output of this runbook goes into the repo except the secret-free ceremony log.

## 0. Roles and timing

- **Operator:** the owner.
- **Witness:** optional. A holder may watch, but never sees W or other holders' cards.
- **Duration:** about half a day (an estimate; not measured).
- **When it runs:**
  - before the first real ingest (Gate A, initial ceremony);
  - at each real-key check;
  - at each R, X or A rotation;
  - at each holder change.

## 1. Preparation (online machine, days before)

1. Download the pinned tools:
   - Go `filippo.io/age` **v1.3.2** static binaries for every heir platform, including `age-plugin-pq`. Use one pinned version for the ceremony and the kit.
   - python-shamir-mnemonic 0.3.0 wheels and their dependencies.
   - A QR encoder and decoder (candidates: segno, zxing-cpp).
   - The A-signing tool chosen by D3 (candidate: minisign).
2. Verify every artifact against hashes from **two independent sources**, for example the Go checksum database plus the upstream release, or PyPI plus the upstream repository tag. Record the hashes.
3. Prepare an ephemeral live OS image (for example a Tails-class live system, as the shamir README recommends). It must have no network drivers enabled and no persistent storage.
4. Write the tools, the ceremony script (§3.2) and the I_e/K-04 **public** keys onto a read-only medium. Generate I_e, K-04 and the optional standby I_{e+1} **at the homelab beforehand**. Their secret halves never enter the ceremony.
5. Prepare:
   - five or more fair dice;
   - a printer **with no network and no storage**, or a QR-capable label printer;
   - the card stock;
   - two blank offline media for A and the bundles;
   - the doomsday USB.

## 2. Environment rules (apply throughout)

- The machine is air-gapped: Wi-Fi and Bluetooth off or removed; no network cable.
- Shell history is off (`unset HISTFILE`, or the equivalent).
- **Never** run `script(1)`, a pty recorder, terminal logging or screen recording. The D2-S2 run 1 harness leaked a test passphrase into its results through pty capture.
- Secrets never appear on a command line (argv). Enter them at prompts, or read them from tmpfs files.
- Keep all working files in a RAM-backed directory (tmpfs) only.
- Before any log or file leaves the machine, grep it for each secret (W hex, the identity line prefix, the share words). Destroy any file that matches.

## 3. Recovery key R

### 3.1 Generate R

1. Generate R with `age-keygen -pq` into a tmpfs file.
2. Strip the comment lines, keeping only the identity line, which is about 78 B (`grep -v '^#'`). The full file is too large for a practical QR.
3. Derive and record R's public recipient (`age-keygen -y`) and its fingerprint (format per D3).

### 3.2 Generate W and the shares

Run the ceremony script. It is short and reviewed, uses the shamir library API, and reads its input from the terminal:

1. Read dice rolls with no echo (at least 50 rolls of a d6, about 129 bits).
2. Compute W = first 16 bytes of SHA-256(32 bytes from the OS CSPRNG ‖ dice string).
3. Call `generate_mnemonics(group_threshold=1, groups=[(2, 3)], master_secret=W, passphrase=b"", extendable=True)`.
4. Show the shares on screen one at a time for printing.
5. Show W's hex **once**, for step 3.3.

- **No SLIP-39 passphrase.** A wrong one would silently yield a different W.
- **Group option:** owner 1-of-1 OR family 2-of-3 is `group_threshold=1, groups=[(1, 1), (2, 3)]`. Use it only if OD-08 chooses it.
- Optional (Wave 2): cross-check the shares with a second, independent SLIP-39 implementation before printing.

### 3.3 Wrap R

1. Run `age -a -p -o R.age <identity file>` and type W's hex at the prompt, twice.
2. Expect an ASCII file of about 422 B.
3. Clear the screen.

### 3.4 Test before printing

1. For **every** k-subset of shares, run `shamir recover`, then `age -d -i R.age`, and decrypt a test object encrypted to R's recipient. All subsets must succeed.
2. Check that one share alone is refused, and that a wrong W gives "incorrect passphrase".
3. Print the cards (§6). **Scan each printed QR back** on the air-gapped machine and compare it byte for byte with R.age.

## 4. Archive key X and admin root key A

1. Generate X the same way as R (`age-keygen -pq`). Wrap it with an owner passphrase (`age -a -p`). Optionally add a Secure Enclave `--pq` or YubiKey wrap later, on the owner's machine.
2. Generate A (Ed25519, tool per D3). Protect it with an owner passphrase. Write it to the two offline media.
3. If this is a rotation, sign the new A with the old A.

## 5. Bundles and trust bundle

1. **Offline bundle:** an age file to R containing X's identity, and A only if DR-D2-3 = full admin. Decrypt-test it with R.
2. **Online bundle (initial):** an age file to {R, X} containing S_0 and I_0. These come from the homelab sealed to R or X, so they are never in the clear here. On later epochs the homelab refreshes this bundle itself.
3. **Trust bundle:**
   - Assemble {I_e, R, X?, K-04, epoch, not_after, revoked[], algorithm IDs}.
   - Sign it with A.
   - Compute its digest; this is the pin printed on cards and kits (SR-02, SR-27).
   - Optionally also sign a standby bundle for I_{e+1}.
4. Copy the offline bundle, the initial online bundle, R.age and the signed trust bundle onto the doomsday USB and the second medium.

## 6. Cards (share plan)

Each card carries:

- the holder's 20 words, with the group and member line;
- a QR of R.age;
- R's fingerprint;
- the trust-bundle digest;
- a one-page instruction pointing to the printed heir runbook (co-owned with E7).

R's fingerprint is **also** printed in the runbook and on the kit. The heir checks that it matches on at least two cards.

| Default (OD-08 A) | Holder (example; E7-S1 confirms) |
|---|---|
| Share 1 | Partner |
| Share 2 | An adult relative outside the household |
| Share 3 | Safe-deposit box or executor |

Holders never receive W, R.age on its own, or another holder's card.

## 7. Close-down

1. Grep every file that will leave the machine (§2).
2. Write the ceremony log. It may contain only:
   - date, attendees, and tool versions and hashes;
   - fingerprints of R, X and A, and the trust-bundle digest;
   - the number of k-subsets tested and the pass result;
   - QR scan-back results;
   - audit pass rates (§8).

   **No secrets.**
3. Power off. The tmpfs is lost on power-off. Destroy any printer buffers if they cannot be confirmed empty.

## 8. Real-key check (Gate C, after any holder change, and at least every 3 years)

The interval is an owner-tunable default with no primary source.

1. k holders bring their cards to the owner. The check runs only on the air-gapped ceremony image with the owner present. This check is **exempt** from the "rotate R after any real-card recovery" rule, because it uses the same controlled environment as the ceremony.
2. Recover R (§3.4 steps, with the real cards).
3. **R-stanza audit:**
   - unwrap with R a random sample of stored headers, exported as headers only;
   - unwrap **every** I_e escrow entry;
   - unwrap the online bundle and the offline bundle;
   - verify each header MAC;
   - record the pass rates.

   **Any failure:** treat it as a broken R stanza. Stop, investigate, and rewrap the affected objects from X.
4. Re-run §7.

The first real-key check should come within the first months after the first family ingest (a proposal), so that broken R stanzas are found early.

## 9. Annual holder check (no reconstruction)

Each year, for each holder (by phone or in person):

1. "Do you still have your card? Is it readable and stored where we agreed?"
2. "Has anyone else seen or photographed it?" If yes, and k cards may be exposed, run an R rotation.
3. Note any change of address, health or relationship that affects holding (E7).
4. Refresh the doomsday USB's online-bundle copy, if E7/C8 put the refresh here.

Record only the date and yes/no answers in the ceremony log. Never ask a holder to read out or send their words.

## 10. Rotations

| Event | Action |
|---|---|
| New ingest epoch | Homelab generates I_{e+1}; A signs the new bundle (or the standby bundle is activated); the homelab escrows I_{e+1} into the online bundle and copies it off-box |
| I_e compromise | As above, with I_e in `revoked[]` |
| ≥ k cards possibly exposed, or any recovery outside §8 | New R (§3), new offline bundle, new trust bundle, store-wide header rewrap (A6 tool) |
| Holder lost, card retrieved | Re-issue an extendable share set for the same W (§3.2 with the existing W) |
| X rotation | New X (§4), store rewrap with old and new X online, new offline bundle |
| A rotation | New A signed by the old A; re-pin through kits (D3) |
