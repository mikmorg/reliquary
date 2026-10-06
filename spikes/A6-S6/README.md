# Spike A6-S6 (proposed in the A6 note): A′ header rewrap round trip (THROWAWAY)

> **Throwaway spike code, not production code.** Workstream A6. This spike is proposed in `docs/research/a6-homelab-storage-engine.md` §Spikes and is not in PLAN's A6 table. It tests the mechanics behind the recommended posture A′ (OD-07, one-way door #4).

- **Run by / date:** A6 spike runner (agent), 2026-10-06 (Wave 1, batch W1-b)
- **Exec tag:** CT, run for real in the cloud container
- **Data class:** `SYN → results` (the same corpus and keys as A6-S5)
- **Budget IDs:** none
- **Pass criterion (A6 note):** "Header rewrap at ingest yields files that `age -d` (Go and Rust) decrypts with the archive key, and the original header still verifies against the device record." Pass leads to A′ being feasible; fail leads to A.

## What was built

The ingest path of `spikes/A6-S3/a6cas` (Go, `filippo.io/age` v1.3.1 public API plus about 100 lines of its own header code: `store.go` `buildHeader`, `rewrapCopy`, `verifyHeaderMAC`). For each object it:

1. decrypts the device's upload with the **ingest key**, streaming, and checks size, SHA-256 and dedup ID against the signed record;
2. unwraps the file key from the device header `h0` (`age.DecryptHeader`);
3. writes a **new header** with stanzas for the **archive** and **recovery** recipients, plus a fresh header MAC;
4. copies the **payload bytes unchanged** behind it (temp file, fsync, rename, directory fsync);
5. keeps `h0` in the append-only manifest, so the store stays at one file per item.

Metadata records get the same treatment. `a6cas verify` then checks the result. `s5s6.py` (in `spikes/A6-S5/`) drives it and adds a byte comparison of the payloads and the independent decryptors.

## Results (measured; `../A6-S5/evidence/s5s6.json`)

| Check (176 blobs, 200 records per variant) | X25519 archive + recovery | PQ hybrid archive + recovery |
|---|---|---|
| Stored payload byte-identical to the device upload's payload | 176/176 | 176/176 |
| Stored object decrypts to its SHA-256 with the archive key (Go lib / age 1.1.1 / age 1.3.1 / rage 0.12.1) | 176 / 176 / 176 / 176 | 176 / **0** / 176 / **0** (A6-S5) |
| … with the recovery key | 176 everywhere | as above |
| **Ingest key refused** on every stored object (all decryptors) | 176/176 | 176/176 |
| `h0`'s MAC verifies under the file key recovered from the stored header (archive key) | 176/176 | 176/176 |
| The device's original upload, rebuilt as `h0` + stored payload, decrypts with the ingest key to the right SHA-256 | 176/176 | 176/176 |
| Records: original upload bytes rebuilt from `h0` + payload; SHA-256 equals the receipt's `meta_sha256` | 200/200 | 200/200 |
| Records: kept `content_h0` matches the device-signed `header_mac` | 176/176 | 176/176 |
| Ed25519 signature on every archived record verifies after decryption with the archive key | 200/200 | 200/200 |
| Stored header size (original `h0` = 168 B) | **266 B** (2 X25519 stanzas) | **3,184 B** (2 `mlkem768x25519` stanzas) |
| Blob overhead over plaintext (mean object about 1.1 MB) | 0.0505 % | 0.312 % |

**Findings:**

- **(High, measured) A′ is mechanically sound.**
  - The rewrap needs only the public Go age API plus a stanza encoder and the header MAC (written from the C2SP spec; the same approach as D2-S2).
  - The payload is never touched.
  - Device provenance survives byte-exactly. With `h0` in the manifest and the archive key, the homelab can reproduce the exact bytes the device uploaded and re-check its signed `header_mac` and `meta_sha256`.
- **(High, measured)** After the rewrap, the online ingest key cannot read anything already stored. This is the property A′ is chosen for.
- **(Medium, inference)** `h0` and `meta_sha256` are recoverable only from the manifest. A6-S4 shows that a files-only rebuild loses them. The manifest is therefore load-bearing provenance and must be audited and copied like the objects.
- The Rust side of the rewrap (A6 note C20: `age` crate public API) was **not** built here. The ingest service will be Rust, so this stays open for the build phase. The Go prototype only shows that the format allows it.

## Pass / fail

**Pass** (X25519). For PQ, **pass on mechanics, fail on independent readers** (Go only; see A6-S5).
