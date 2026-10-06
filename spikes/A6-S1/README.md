# Spike A6-S1: posture probes for the OD-07 decision matrix (THROWAWAY)

> **Throwaway spike code, not production code.** Workstream A6 (`docs/research/PLAN.md`, section "A6."). The matrix itself lives in the A6 note (`docs/research/a6-homelab-storage-engine.md` §F1), and the owner picks the posture (OD-07). This spike turns some of the matrix cells from "reasoned" into "observed". It does not pick a posture.

- **Run by / date:** A6 spike runner (agent), 2026-10-06 (Wave 1, batch W1-b, second runner pass)
- **Exec tag:** CT → owner. Posture B needs real OpenZFS, which the container lacks, so its cells are an OL kit: `docs/research/kits/A6-S1/`.
- **Data class:** `SYN → results`. The corpus is `a6cas gen -n 600 -dup 0.1 -scale 0.05 -seed 3`: 600 records, 535 unique contents, 229,295,536 plaintext bytes, random content. The keys are throwaway and were made in `/dev/shm` and deleted afterwards.
- **Budget IDs:** none measured. The matrix rows relate to BUD-TTS, BUD-RESTORE and BUD-RECOVERY, but nothing here is homelab evidence.
- **Machine:** a shared 4-vCPU cloud VM with 15 GB RAM. All stores are on tmpfs, so **timings show CPU cost only and are not disk figures**.

**Tools:**

| Tool | Version | Source |
|---|---|---|
| `a6cas` | — | `spikes/A6-S3/a6cas`, rebuilt from the committed source with Go 1.26.0 |
| `retrofit` | — | this folder, Go, `filippo.io/age` v1.3.1 |
| age | v1.3.1 | Go |
| restic | 0.19.1 | — |
| Kopia | v0.23.1 | `go install github.com/kopia/kopia@v0.23.1` |

## Hypotheses and results

### Probe 1: adding a recovery recipient later, header rewrap vs re-encryption (postures A / A′)

**Hypothesis (from the age spec, A6 note C2):** adding a recipient to a stored age file is a header-only rewrap. It needs the private key and rewrites every file, because the header sits at the front, but it does no payload cryptography and leaves the payload bytes untouched.

**Method.** `retrofit rewrap` and `retrofit reencrypt` each take the 535 stored blobs of a complete A′ store (2 X25519 stanzas: archive and recovery) and write new files with 3 stanzas: archive, recovery and a new `recovery2`. Each output file goes to a temp file, then fsync, rename and directory fsync. Each mode ran 3 times, alternating.

**Results** (`evidence/retrofit-runs.jsonl`, `evidence/retrofit-check.jsonl`):

| | Header rewrap | Full re-encryption (fresh file key) |
|---|---|---|
| Bytes read / written | 229,506,822 / 229,559,252 | 229,506,822 / 229,559,252 |
| Wall time, 3 runs (tmpfs, CPU-bound) | 1.749 / 1.685 / 1.677 s | 2.514 / 2.570 / 2.579 s |
| Header bytes, all objects | 142,310 → 194,740 (+98 B per added X25519 stanza) | (same sizes) |
| Every object decrypts with `recovery2` to the SHA-256 in its name | 535/535 | 535/535 |
| Payload byte-identical to the original | **535/535** | 0/535 |
| Still decrypts with the archive key | 535/535 | (not run) |
| Decrypts with the ingest key | 0/535 | (not run) |

**Findings:**

- **(High, measured)** A later recipient addition is a header rewrap. The payload is unchanged, but **every byte of the store is rewritten anyway**, because the header sits at the front of each file. Under these conditions re-encryption cost about 1.5× the CPU time of a rewrap.
- **(Medium, inference)** On spinning disks both methods are bound by disk I/O. For 10 TB the cost is roughly *store size ÷ read rate + store size ÷ write rate*, in either mode. That supports the A6 note's advice to add the recovery recipient at ingest from day one (OD-08).
- **(High, measured)** Adding the stanza grows each header by exactly 98 B (X25519). That is negligible.

### Probe 2: which key online can read the archive (A vs A′)

**Hypothesis:** under posture A (keep the received ciphertext as it is) the online ingest key reads every stored object. Under A′ it reads none.

**Results** (`evidence/online-key-exposure.json`, decryptor age v1.3.1). Under A the stored object *is* the device upload.

| Posture | Objects the online ingest key decrypts |
|---|---|
| A | 535/535 |
| A′ | 0/535 |

### Probe 3: keyless fixity under posture C (restic, Kopia)

**Hypothesis (A6 note Q1):** an audit needs "the repository password under C".

**Results** (`evidence/restic-posture-c.txt`, `restic-keyless.json`, `kopia-posture-c.txt`):

| Engine | Without the password | Keyless file-level check | One bit flipped in one pack |
|---|---|---|---|
| restic 0.19.1 (repository format v2) | `check` refuses: "an empty password is not allowed" (rc 1) | **Every file's name equals the SHA-256 of its bytes:** data 15/15, index 1/1, snapshots 1/1, keys 2/2 | The keyless check detects it. `restic check --read-data` (with the password) also detects it (rc 1, "ciphertext verification failed"). |
| Kopia v0.23.1 (filesystem repository) | `repository connect` cannot proceed without a password (rc 1) | **Not possible from names.** No file name equals an unkeyed SHA-256, SHA-224, SHA3-256, BLAKE2s or BLAKE2b of its bytes. In the source, pack names are random (`repo/content/content_manager.go:756`, `cryptorand.Read(blobID)`; `:774`, name = prefix + random hex + session ID), and other blobs are named by the repository's hash function over the payload (`internal/blobcrypto/blob_crypto.go`, `Encrypt`). | (not run) |

**Finding (High, measured): this corrects the C cell.**

- Under restic, bit-rot detection on the stored files needs **no key**: `sha256sum` each file and compare with its name, as `design.rst` specifies. The password is needed only for the semantic check (`check --read-data`, which decrypts) and for restores.
- Under Kopia, a keyless check would need a separately kept hash list.
- **Hand-off:** the A6 note's Q1 row ("It needs … the repository password under C") should read "restic: keyless at file level; Kopia: needs the password, or an external hash list".

**Also measured (posture C):**

- `restic key add`, the C equivalent of "add a recovery recipient", took 2.979 s (scrypt dominates) and added one key file. `keys/` then held 878 B across 2 files, and no data file changed.
- The new password then read and verified everything (`check --read-data`, rc 0).
- So under C, adding a recovery key is cheap. The cost is that it is one more **symmetric read-everything** secret.

### Probe 4: what the stored layout tells someone holding the disks (A / A′)

**Hypothesis (A6 note Q14, DR-A6-3):**

- plain-SHA-256 file names let a holder of the disks confirm that a known file is present;
- age's fixed framing reveals each plaintext's exact size.

**Method.** For every stored blob: payload length L = file size − header length. The chunk count is c = max(1, ⌈(L − 16) / 65,552⌉). The predicted plaintext size is n = L − 16 − 16c (16-byte nonce, 64 KiB chunks, 16-byte tag per chunk, per the C2SP age spec). This prediction was compared with the true size. Separately, 50 candidate plaintext files were hashed and their path tested in `blobs/`.

**Results** (`evidence/size-leak.json`, script `size-leak.py`):

| Check | Result |
|---|---|
| Exact plaintext size derived from stored size | 535/535 |
| Candidate files whose presence was confirmed by path alone | 50/50 |

**Finding (High, measured):** under A and A′, someone holding the disks learns exact sizes and can test whether a known file is present. That is the same exposure as file sizes under ZFS native encryption (A6 note C10), plus file-presence confirmation, which ZFS's encrypted directory listings would hide. This is input to DR-A6-3: the options are padding (A2 / F3-S1) and HMAC-named paths. The bytes were read from the store files; nothing was decrypted.

## The cells this spike now backs with observations

| Matrix question (PLAN A6) | A (keep as received) | A′ (rewrap at ingest) | B (ZFS native encryption) | C (restic / Kopia) |
|---|---|---|---|---|
| Key needed online for audits or scrubs | No (SHA-256 of stored bytes, A6-S3/S4 `audit`) | No (same) | Kit A6-S1 P3 (man page says scrub needs no key) | restic: **no key** at file level (Probe 3); Kopia: key or an external hash list |
| What the online key can read | Everything: 535/535 (Probe 2) | Nothing stored: 0/535 (Probe 2, A6-S6) | Kit P4 (loaded key reads everything) | The repository password reads everything (restic, Kopia) |
| Cost of adding a recovery recipient later | Rewrite the whole store, payload untouched (Probe 1) | Same; avoided by adding R at ingest | Kit P5 (`change-key` rewraps one wrapping key, no data) | `restic key add`: 2.98 s, one key file (Probe 3) |
| What a stolen box exposes (content off) | Content only if the ingest key is on the box; always sizes and file presence (Probe 4) | Sizes and file presence (Probe 4); content: none | Kit P2 (names and sizes of datasets and snapshots; file names hidden) | Not probed |
| Heir can read it | Yes, `age` only (A6-S5: three decryptors) | Yes, `age` only (A6-S5) | Needs OpenZFS + key | restic or rustic + password (A6-S5 Part B) |
| Off-site copy without exposing keys | Copy the files (no probe needed) | Copy the files | Kit P1 (`zfs send -w`) | `restic copy` (not probed) |

Unattended unlock, derivative generation and the Immich/PhotoPrism view are design questions (A6 note §F1). Nothing here measures them.

## Pass / fail

**n/a. This is a decision-matrix spike; the owner decides (OD-07).**

- The CT probes ran, and all checks came out as stated, except the restic keyless-fixity result. That one contradicts the note's Q1 wording for posture C; it is handed to the analyst above.
- The posture-B cells wait on the OL kit.

## Rebuild and rerun

`probe.sh WORKDIR` repeats all four probes; Probe 4 is `size-leak.py`. It expects `a6cas`, `retrofit`, `age`, `age-keygen`, `restic` and `kopia` on `PATH`. Build `retrofit` with `cd retrofit && go build`. Clean up afterwards by deleting `WORKDIR`.
