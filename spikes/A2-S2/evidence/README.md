# A2-S2: kill-and-resume with PQ headers, 50 random kills (CT, run 2026-10-06)

> Throwaway spike evidence. Code: `../harness/a2s2_kill.py` and `../src/`. Synthetic data only (`SYN → results`).

- **Hypothesis (PLAN A2-S2):** with the CE resume mechanism and a post-quantum header, the following hold over 50 random kills:
  - every object decrypts to the exact SHA-256;
  - at most one segment is re-encrypted per kill;
  - no (key, nonce) pair is reused;
  - no file key survives commit.
- **Decision informed:** the resumable-encryption mechanism in ADR-0007.
  - Pass: keep the CE journaled deterministic resume.
  - Fail: spool ciphertext to a temp file.
- **Budget IDs:** BUD-TMP. No temp ciphertext file is used at all; the only per-upload state is the sealed state, the tag journal and the unsigned record fields.
- **Exec tag:** CT.
- **Status:** ran.
- **Result:** **PASS** in both configurations.

| Run | Header | Prefix | Kills (SIGKILL) | Uploads completed | Checks |
|---|---|---|---|---|---|
| `results-1stanza.json` | 1 × `mlkem768x25519` (1,627 B) | 1,643 B | 50 | 15 | 127 / 127 pass |
| `results-2stanza.json` | 2 × `mlkem768x25519` (3,184 B) | 3,200 B | 20 | 7 | 63 / 63 pass |

## Method

- **Kills.** The harness runs the real binary (`start`, then `resume` until done) and sends **SIGKILL** at a uniformly random time between 0 and 0.6 s after launch. It keeps doing this until it has killed 50 processes (20 in the 2-stanza run).
  - The simulated network sleeps 3,000 µs per 16 KiB slice (`A2_SLOW_US`, test-only), so most kills land inside a part.
  - Part sizes are 1–4 chunks (`--chunks-per-part`, test-only), so each file has many parts and the prefix is never chunk-aligned. Production parts are 80 chunks, 5,244,160 B.
- **Files.** Random bytes:
  - 3 MiB + 123 B
  - 10 MiB + 4,097 B
  - 700 KiB + 5 B
  - 6 MiB
  - 2 MiB + 65,536 − 1,643 B
  - top-up files of 4 MiB + 4,099·i B
- **After the last kill,** each upload goes through:
  1. `complete` (seal the record, sign it, encrypt it);
  2. homelab `ingest` (strict PQ profile);
  3. `check-receipt --consume`;
  4. Go `age` 1.3.2 decryption and Rust decryption of the assembled object.
- **"Re-encrypted segment per kill."** Every resume prints its plan (the parts still to generate). The number of parts in that plan that an earlier run had already started is the count of segments regenerated because of the previous kill.
  - 1-stanza run: 49 kills caused exactly 1 regenerated part and 1 kill caused 0.
  - 2-stanza run: all 20 kills caused exactly 1.
  - No kill caused more than 1.
- **No (key, nonce) reuse,** shown three ways:
  1. **Wire consistency.** Every byte ever written to the simulated network for an object offset, in every attempt including killed ones, equals the final byte at that offset. A key/nonce pair therefore never encrypted two different plaintexts.
  2. **Uniqueness.** Payload nonces and header MACs are unique across all uploads in each run.
  3. **Edit-after-kill.** A byte was changed inside a chunk that had **already been transmitted** in the interrupted part (same size, mtime restored). The upload was then resumed, 6 trials per run:
     - with the stat check on, the snapshot check refused (exit 65);
     - with `--no-stat-check`, the journal tag guard alone refused (exit 65: "SOURCE CHANGED in chunk N … refusing to re-encrypt under the same key");
     - 12 of 12 trials were refused across both runs.
- **No key survives commit.** After commit, the homelab recovers each object's file key and payload key (`debug-keys`, test-only). The harness then searches every file under the device directory (state, keystore, pending, records) for those keys in raw, hex, base64 and base64url form. It found 0 hits, and no per-upload files were left over, for every upload.

## Limits

- Kills hit `start` and `resume`, not `complete` or `ingest`.
- The keystore and the simulated R2 are local files.
- The X-Wing encapsulation randomness is hedged and injected through `HedgeRng`. The test asserts exactly 64 bytes are drawn. Because the header is generated once and persisted in the sealed state, resume never needs to regenerate the encapsulation.
- The run is on x86 Linux (ext4), not a phone.

Files: `kill_1stanza.log`, `kill_2stanza.log`, `results-*.json` (per-kill plans, edit trials, uploads), `unit_tests.txt` (10/10), `binary.sha256`.
