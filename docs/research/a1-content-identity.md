# A1. Content identity and dedup ID

- **Workstream:** A1 (see `docs/research/PLAN.md`, section "A1.")
- **Status:** Draft (analyst deep read, Wave 1, batch W1-b). Not yet under skeptic review. Spike results pending (separate spike runner).
- **Date:** 2026-09-29 (last updated 2026-09-29)
- **Feeds:** ADR-0006 (reserved in `docs/adr/README.md`), `docs/spec/identifiers.md` + vectors (not written yet: next stage), one-way door #1 (`docs/research/one-way-doors.md`), new decision requests DR-A1-1 and DR-A1-2 (below; H1 assigns OD numbers)
- **Depends on:** F3 (attack matrix; 2025 CDC attacks), T1 spike 7 (x86 part done in `content-encryption-format.md` §14; phone part open), D2 (custody and delivery of the family secret, rotation trigger), A6 (catalog must store the plain SHA-256), B5/B2 (per-platform cache signals)
- **Traceability rows advanced:** R-21, R-23, R-24 (contract), OPEN-3c and Q1-2b (ID-side rotation mechanics only; custody stays with D2), R-44 (input)

## Summary

Keep **SHA-256** as the content hash, which ADR-0001 already names. Change *what* the family key is applied to: compute the dedup ID as an HMAC-SHA256 over the file's **SHA-256 digest**, not over the whole file. The HMAC key is derived per **epoch** from the family secret with HKDF. The two constructions give the cloud the same privacy. The digest version reads each byte once and hashes it once, where HMAC over the file hashes it twice. It also lets the secret be rotated from the SHA-256 values already kept in the client cache and the homelab catalog, with no file reads. HMAC over the whole file would make every rotation a full re-read of about 10 TB at the homelab and of every device, so in practice a leaked family secret could never be retired.

The ID should carry a version/kind byte and an epoch, keep all 256 bits, and be written as lowercase hex. That text is safe as an R2 key, a FAT/exFAT filename and a catalog key. Whole-file identity stays. Per-part integrity already comes from age STREAM chunks, and the kind byte leaves room for a future chunk-list ID without adopting content-defined chunking (CDC).

The construction deviates from the wording "HMAC(family secret, content)" in CLAUDE.md and ADR-0001, so it goes to the owner (DR-A1-1). Confidence: **medium-high** on the construction and encoding (reasoning from primary sources plus arithmetic). **Low** on phone performance and energy, because no phone has been measured (A1-S1 kit).

## Questions

| # | Question | Short answer | Confidence |
|---|---|---|---|
| 1 | SHA-256 vs BLAKE3: throughput and energy per GB on real device classes. Is I/O the bottleneck? | **No device measurement exists yet.** SHA-256 is recommended: it is settled in ADR-0001, every client platform ships it natively, and stock tools (`sha256sum`) can check it. On CPUs with SHA-2 instructions, SHA-256 compute appears far above the BUD-HASH floor (one 2017 community measurement: 559 MB/s on an ARMv8 phone), so I/O and heat are the likely limits there. CPUs without the AArch64 `sha2` feature fall back to software, and their speed is unknown. Switch to BLAKE3 only if A1-S1 shows SHA-256 missing BUD-HASH on the low-end class. | High for the platform-support facts; **Low** for performance |
| 2 | HMAC(K, content), HMAC(K, SHA-256(content)) or keyed BLAKE3? | **HMAC-SHA256(K_e, 0x01 ‖ SHA-256(content))**, with K_e = HKDF-SHA256(family secret of epoch e, fixed label). Each byte is read and hashed once. Rotation works from the cache with zero file reads. The security difference is small and listed in C9–C11. | Medium-high |
| 3 | Wire format: version prefix, domain label, 256 bits or truncated, encoding | Binary: `kind (1 B) ‖ epoch (u16 BE) ‖ MAC (32 B)` = 35 bytes. Text: `rd1-<epoch as 4 lowercase hex>-<64 lowercase hex>` = 73 characters. Keep all 256 bits. Domain separation comes from the HKDF label plus the kind byte. The exact strings are a strawman for `identifiers.md`. | Medium (format details); High (lowercase hex is safe on case-insensitive filesystems) |
| 4 | Whole-file digest vs block or tree hash | Whole-file SHA-256. Per-part verification in transit already comes from age STREAM's 64 KiB authenticated chunks, and hashing different files in parallel gives enough parallelism. Reserve kind `0x02` for a future chunk-list ID. Do not adopt CDC now. | Medium-high |
| 5 | Rotation: epoch-tagged IDs, procedure after device compromise, homelab re-derivation | IDs carry their epoch. The homelab re-derives every ID from its catalog SHA-256 column, and clients from their cache SHA-256 column. The Worker rejects retired epochs after a grace window. D2 owns custody and the trigger. | Medium |
| 6 | Minimum safe rules for clients (racy mtime, TOCTOU) | Ten contract rules, R1–R10 (Findings §6). The main ones: a racy window, stat checks before and after each pass, fail-safe on any missing signal, a cache hit is never proof of protection, and the homelab recomputes the ID and SHA-256 after decrypting. | Medium-high |
| 7 | The same ID for items with no device of origin (A9) | The ID is a function of the content bytes and the epoch key only. The homelab importer uses the same library, and provenance goes in the metadata record. | High |
| 8 | (new) What does the digest construction newly depend on? | SHA-256 collision resistance. A practical SHA-256 collision would give two files the same dedup ID. HMAC over the file would still need K. The homelab's content identity already depends on SHA-256, and the kind byte allows migration. | Medium |
| 9 | (new) Where must the plain SHA-256 live? | Client hash cache (ADR-0001 already has it), the encrypted metadata record, and the homelab catalog. The catalog column is what makes homelab re-derivation possible, so A6 must keep it for every item. | High |

## Method

- **Sweep:** three scouts ran: docs, source code of similar tools, and community/issues. This analyst then re-fetched and read the load-bearing primary sources: the Tahoe convergence-secret doc, git racy-git in full, the restic change-detection section and threat model, Borg's ID-hash and fingerprinting sections, Kopia `hashing.go` and `blake3_hashes.go` in full, and Duplicacy `NewKeyedHasher` and `GetChunkIDFromHash`. Also re-read: BLAKE3 paper §§ abstract, 3–4 and 7 (text extracted from the PDF), the Bao spec on root-hash equality, and the sha2 0.11.0 README and Cargo.toml. Four sources were added: MS "File Times", MS `FILE_BASIC_INFO`, the Linux arm64 `elf_hwcaps`, and the Android `Mac` and CryptoKit `HMAC` pages. The analyst also read the existing notes: ADR-0001 and `content-encryption-format.md` (T1 spike 2), whose §6 and §14 already define and measure a "pass 1".
- **Routes used:** raw.githubusercontent.com (vendor doc and source mirrors), static.crates.io (crate tarballs), developer.android.com (direct), developer.apple.com DocC JSON (direct).
- **Blocked sources:** none was silently replaced. Where a secondary source stands in, the claim says so. For H1:
  - rfc-editor.org, ietf.org and datatracker: RFC 2104 (HMAC), RFC 4231 (HMAC-SHA256 vectors), RFC 4648 (base16/32/64), RFC 5869 (HKDF, not attempted)
  - nvlpubs.nist.gov and csrc.nist.gov: FIPS 180-4 and SP 800-107r1 (hash and HMAC truncation guidance)
  - w3c.github.io/webcrypto
  - dropbox.com/developers (content_hash doc)
  - tarsnap.com/crypto.html
  - tahoe-lafs.org Hall of Fame page
  - news.ycombinator.com
  - eclecticlight.co
  - daemonology.net
  - 00f.net and lobste.rs
- **Consequence of the blocks:** the RFC 4648 alphabet is taken from Go's `encoding/base32` (secondary). The HMAC PRF property is argued from Borg, Kopia and Tahoe practice rather than RFC 2104 text. The A1-S3 vectors must get RFC 4231 and FIPS 180-4 reference values from an independent implementation (Python `hashlib`/`hmac`, Go `crypto`), labelled as such.
- **Stop rule:** the analyst's re-reads added four primary sources, and none changed the recommendation. The last two community leads (HN threads, Eclectic Light) were blocked and would be secondary anyway.

## Sources

| # | Source (title and URL or mirror path) | Publisher | Published or version date | Accessed | Primary? |
|---|---|---|---|---|---|
| S1 | ADR-0001 Cloud staging on R2 — `docs/adr/0001-cloud-staging-on-r2.md` | Project | 2026-09-29, Accepted | 2026-09-29 | Yes (settled text) |
| S2 | Content encryption format spike — `docs/research/content-encryption-format.md` (§3, §6, §12, §14, §16) | Project (T1 spike 2) | 2026-09-29 | 2026-09-29 | Yes (project measurement, x86 only) |
| S3 | BLAKE3: one function, fast everywhere — `BLAKE3-team/BLAKE3-specs @ master : blake3.pdf` | O'Connor, Aumasson, Neves, Wilcox-O'Hearn | Version 20211102173700 | 2026-09-29 | Yes |
| S4 | BLAKE3 README — `BLAKE3-team/BLAKE3 @ master : README.md` | BLAKE3 team | master | 2026-09-29 | Yes |
| S5 | BLAKE3 test vectors — `BLAKE3-team/BLAKE3 @ master : test_vectors/test_vectors.json` | BLAKE3 team | master | 2026-09-29 (scout, read in full) | Yes |
| S6 | Bao spec — `oconnor663/bao @ master : docs/spec.md` | J. O'Connor | master | 2026-09-29 | Yes |
| S7 | RustCrypto `sha2` 0.11.0 — static.crates.io `sha2-0.11.0.crate` (README "Backends", Cargo.toml) | RustCrypto | 0.11.0 (latest non-yanked 2026-09-29, per scout) | 2026-09-29 | Yes |
| S8 | RustCrypto `hmac` 0.13.0 — static.crates.io `hmac-0.13.0.crate` | RustCrypto | 0.13.0 | 2026-09-29 (scout) | Yes |
| S9 | `blake3` crate 1.8.7 — static.crates.io `blake3-1.8.7.crate` | BLAKE3 team | 1.8.7 | 2026-09-29 (scout) | Yes |
| S10 | Use of index and Racy Git problem — `git/git @ master : Documentation/technical/racy-git.adoc` (the old `.txt` path is 404) | Git project | master | 2026-09-29 (read in full) | Yes |
| S11 | Hash function transition — `git/git @ master : Documentation/technical/hash-function-transition.adoc` | Git project | master | 2026-09-29 | Yes |
| S12 | restic "Backing up", File change detection — `restic/restic @ master : doc/040_backup.rst` | restic | master | 2026-09-29 | Yes |
| S13 | restic design / threat model — `restic/restic @ master : doc/design.rst` | restic | master | 2026-09-29 | Yes |
| S14 | restic `internal/archiver/archiver.go` (`fileChanged`, fstat after open) | restic | master | 2026-09-29 (scout) | Yes |
| S15 | Borg internals: security — `borgbackup/borg @ master : docs/internals/security.rst` | Borg | master (borg 2) | 2026-09-29 | Yes |
| S16 | Kopia `repo/hashing/hashing.go`, `blake3_hashes.go` — `kopia/kopia @ master` | Kopia | master | 2026-09-29 (read in full) | Yes |
| S17 | Duplicacy `src/duplicacy_config.go` — `gilbertchen/duplicacy @ master` | Duplicacy | master | 2026-09-29 | Yes |
| S18 | bupstash `src/crypto.rs`, `src/keys.rs` — `andrewchambers/bupstash @ master` | bupstash | master | 2026-09-29 (scout) | Yes |
| S19 | Tarsnap `lib/crypto/crypto.h`, `crypto_hash.c` — `Tarsnap/tarsnap @ master` | Tarsnap | master | 2026-09-29 (scout) | Yes |
| S20 | Tahoe-LAFS "The Convergence Secret" — `tahoe-lafs/tahoe-lafs @ master : docs/convergence-secret.rst` | Tahoe-LAFS | master | 2026-09-29 (read in full) | Yes |
| S21 | Tahoe-LAFS `src/allmydata/util/hashutil.py` | Tahoe-LAFS | master | 2026-09-29 (scout) | Yes |
| S22 | Dropbox content hasher (Python reference) — `dropbox/dropbox-api-content-hasher @ master` | Dropbox | master | 2026-09-29 (scout, read in full) | Yes (code; the docs page is blocked) |
| S23 | Multicodec table — `multiformats/multicodec @ master : table.csv` | Multiformats | master | 2026-09-29 | Yes |
| S24 | Multibase README — `multiformats/multibase @ master` | Multiformats | master | 2026-09-29 (scout) | Yes |
| S25 | Perkeep `pkg/blob/ref.go` | Perkeep | master | 2026-09-29 (scout) | Yes |
| S26 | R2 limits — `cloudflare/cloudflare-docs @ production : src/content/docs/r2/platform/limits.mdx` | Cloudflare | production branch | 2026-09-29 (read in full) | Yes |
| S27 | Workers Web Crypto — `cloudflare/cloudflare-docs @ production : src/content/docs/workers/runtime-apis/web-crypto.mdx` | Cloudflare | production branch | 2026-09-29 | Yes |
| S28 | Naming Files, Paths, and Namespaces — `MicrosoftDocs/win32 @ docs : desktop-src/FileIO/naming-a-file.md` | Microsoft | docs branch | 2026-09-29 | Yes |
| S29 | File Times — `MicrosoftDocs/win32 @ docs : desktop-src/SysInfo/file-times.md` | Microsoft | docs branch | 2026-09-29 | Yes |
| S30 | FILE_BASIC_INFO — `MicrosoftDocs/sdk-api @ docs : sdk-api-src/content/winbase/ns-winbase-file_basic_info.md` | Microsoft | docs branch | 2026-09-29 | Yes |
| S31 | exFAT File System Specification — `MicrosoftDocs/win32 @ docs : desktop-src/FileIO/exfat-specification.md` | Microsoft | docs branch | 2026-09-29 (scout) | Yes |
| S32 | Linux arm64 ELF hwcaps — `torvalds/linux @ master : Documentation/arch/arm64/elf_hwcaps.rst` | Linux kernel | master | 2026-09-29 | Yes |
| S33 | Android `java.security.MessageDigest` — https://developer.android.com/reference/java/security/MessageDigest | Google | Last updated 2026-08-03 | 2026-09-29 (scout) | Yes |
| S34 | Android `javax.crypto.Mac` — https://developer.android.com/reference/javax/crypto/Mac | Google | Last updated 2026-08-03 | 2026-09-29 | Yes |
| S35 | Android cryptography guidance — https://developer.android.com/privacy-and-security/cryptography | Google | Last updated 2026-03-06 | 2026-09-29 (scout) | Yes |
| S36 | CryptoKit `SHA256` and `HMAC` — developer.apple.com DocC JSON `documentation/cryptokit/sha256.json`, `.../hmac.json` | Apple | iOS 13.0+, macOS 10.15+ | 2026-09-29 | Yes |
| S37 | "Weak Hashing is extremely slow on ARMv8 (Android)" — https://github.com/syncthing/syncthing-android/issues/839 | Community | 2017-01-26 | 2026-09-29 (scout) | No |
| S38 | Immich #15739 (WebCrypto hashing fails > 2 GB) — https://github.com/immich-app/immich/issues/15739 | Community | 2025-01-28 | 2026-09-29 (scout) | No |
| S39 | Immich #25248 (iOS hash failure blocks uploads) — https://github.com/immich-app/immich/issues/25248 | Community | 2026-01-13 | 2026-09-29 (scout) | No |
| S40 | restic #2179 (mtime-only detection missed changes), #2495 (ctime false positives after hard-linking) | Community | 2019-02-21; 2019-12-02 | 2026-09-29 (scout) | No |
| S41 | Monochromatic #544 (index copies lose racy-entry protection) — https://github.com/Aquaticat/Monochromatic/issues/544 | Community | unknown (title/snippet only) | 2026-09-29 (scout) | No |
| S42 | Immich #17023 (imported assets with wrong checksums) — https://github.com/immich-app/immich/issues/17023 | Community | 2025-03-21 | 2026-09-29 (scout) | No |
| S43 | Immich mobile `hash.service.dart` — `immich-app/immich @ main : mobile/lib/domain/services/hash.service.dart` | Immich | main | 2026-09-29 (scout) | Yes (code) |
| S44 | Go `encoding/base32` (RFC 4648 alphabets; stand-in for blocked RFC 4648) — `golang/go @ master : src/encoding/base32/base32.go` | Go project | master | 2026-09-29 (scout) | No (secondary for RFC 4648) |

## Claims

Skeptic columns are left for the review stage.

| # | Claim | Sources | Key? | Skeptic 1 (sources) | Skeptic 2 (logic) | Skeptic 3 (adversary/cost/user) | Verdict |
|---|---|---|---|---|---|---|---|
| C1 | ADR-0001 already fixes SHA-256 as the plain content hash (local cache; recomputed at the homelab) and HMAC-SHA256 as the dedup MAC. Choosing BLAKE3 would therefore change settled text; choosing SHA-256 does not. | S1 | Yes | | | | Pending |
| C2 | In T1 spike 2 on x86 (SHA-NI), SHA-256 alone ran at 1,136 MB/s and pass 1 (SHA-256 + HMAC over the file, from the page cache) at 668 MB/s. With the portable backend the figures were 299 and 140 MB/s. Hashing each byte twice roughly halves pass-1 hash throughput. | S2 §14 | Yes | | | | Pending |
| C3 | sha2 0.11.0 has no `asm` feature. On aarch64 it uses the `sha2` extension when runtime detection finds it and otherwise falls back to `soft`. The PLAN's "sha2 (asm/ARMv8)" wording is out of date. | S7 | No | | | | Pending |
| C4 | The AArch64 SHA-256 instructions are an optional CPU feature, reported through `HWCAP_SHA2` (ID_AA64ISAR0_EL1.SHA2). A phone may lack them, and nobody has checked which low-end SoCs do. | S32, S7 | Yes | | | | Pending |
| C5 | The BLAKE3 paper's only ARM benchmark is a 32-bit ARM1176 (Raspberry Pi Zero) against OpenSSL 1.1.1d SHA-256. That core has no SHA-2 instructions, so the paper says nothing about ARMv8 phones with hardware SHA-256. No primary source compares the two on such phones; secondary claims exist in both directions. | S3; scout secondary summaries | Yes | | | | Pending |
| C6 | One community measurement (Android 7, 2017) got 559 MB/s single-thread SHA-256 using the ARMv8 SHA-2 instructions, against 10 MB/s with a software implementation, on the same phone. | S37 (secondary) | No (indicative only) | | | | Pending |
| C7 | SHA-256 and HMAC-SHA256 are native on every Reliquary platform: Android `MessageDigest` SHA-256 and `Mac` HmacSHA256 on API 1+, CryptoKit `SHA256` and `HMAC` (streaming `update`) on iOS 13+ and macOS 10.15+, and Workers `crypto.DigestStream("SHA-256")`. BLAKE3 is in none of these platform APIs. | S33, S34, S36, S27 | Yes | | | | Pending |
| C8 | Keyed IDs stop a party without the key from testing for known files. This is the rationale in Borg (id_key), Kopia (HMAC secret) and Tahoe (convergence secret). Anyone holding the key can run confirmation-of-a-file (needs a copy of the file) and learn-the-remaining-information attacks. | S15, S16, S20 | Yes | | | | Pending |
| C9 | Before K leaks, HMAC(K, m), HMAC(K, SHA-256(m)) and keyed BLAKE3 look equally opaque to the cloud: each is a keyed PRF output. (Reasoning; the RFC 2104 text is blocked.) | S15, S16, S3 | Yes | | | | Pending |
| C10 | After K leaks, the digest construction lets the key holder test a candidate from its SHA-256 alone (for example a public hash list), without the file's bytes. HMAC over content needs the bytes. For the brute-force "learn the remaining information" attack the cost is about the same, because each candidate document must be hashed either way. | Reasoning from S20 | Yes | | | | Pending |
| C11 | The digest construction depends on SHA-256 collision resistance even when K is secret: two files with a SHA-256 collision get the same dedup ID. HMAC keyed over content would not inherit an unkeyed collision. ADR-0001 already makes plain SHA-256 the homelab verification value. | Reasoning; S1 | Yes | | | | Pending |
| C12 | Rotation cost with HMAC over content: the homelab must re-read the whole store. At the BUD-INGEST floor of 100 MB/s, 10 TB takes 10¹³ / 10⁸ = 10⁵ s ≈ 27.8 h, which already misses A1-S2's < 24 h. Each phone must re-read its library: about 5.9 h for 128 GB at the BUD-HASH effective floor of 6 MB/s. With the digest construction both sides need only one HMAC per cached SHA-256. (Arithmetic; A1-S2 measures it.) | S1, `budgets.md`, PLAN A1-S2 | Yes | | | | Pending |
| C13 | Precedent for keying a stored hash rather than the content: Duplicacy names chunks `hex(keyed_hash(IDKey, chunk_hash))`, so it can re-derive storage names without re-reading data. Tahoe mixes its secret into a tagged SHA-256d. | S17, S21 | No | | | | Pending |
| C14 | Tahoe says changing the convergence secret moves the client to a new "deduplication domain": old caps still work, but new uploads do not deduplicate against old data. That is the cost of rotating without re-deriving old IDs. | S20 | Yes | | | | Pending |
| C15 | git's racy-clean rule: an entry whose mtime is the same as or newer than the index file's own mtime is re-checked by content, and when an index with racily clean entries is written, their cached size is set to 0. FAT write times have 2 s resolution. | S10, S29 | Yes | | | | Pending |
| C16 | restic trusts a file as unchanged only when mtime, ctime, size and inode all match on Unix. On Windows it compares path, size and mtime only. Windows `FILE_BASIC_INFO` does expose a `ChangeTime` field for metadata changes. mtime-only detection has missed real changes (restic #2179), and ctime checks cause full-tree false positives after hard-linking (#2495). | S12, S14, S30, S40 | Yes | | | | Pending |
| C17 | Lowercase-only IDs avoid case collisions on case-insensitive volumes (Windows default, FAT/exFAT). Mixed-case base64 can collide there. A fixed-length alphanumeric ID with a letter prefix cannot hit the reserved device names or the trailing-dot/space rule. R2 keys may be up to 1,024 bytes. | S28, S31, S26 | Yes | | | | Pending |
| C18 | Bao's root hash equals the regular BLAKE3 hash, so a BLAKE3 identity would get per-range verified streaming without changing the ID. age STREAM already authenticates 64 KiB chunks in transit (T1 spike 2). | S6, S2 | No | | | | Pending |
| C19 | Web Crypto's one-shot `digest()` has failed on > 2 GB inputs in a browser (Immich #15739). A TypeScript second implementation for the > 4 GiB vector must stream: Node `crypto.createHash`, or `DigestStream` on Workers. | S38 (secondary), S27 | No | | | | Pending |
| C20 | Chunking attacks on keyed CDC were published in 2025 (scouts found two independent papers; not read here). restic cites Alexeev, Percival and Zhang (IACR 2025/532) and mitigated in 0.18.0. This supports reserving room for chunk lists rather than adopting CDC. | S13 | No (F3 owns) | | | | Pending |

## Findings

### 1. Hash algorithm: SHA-256 vs BLAKE3

- **Settled text already picks SHA-256** (C1). ADR-0001 §2 names "Plain SHA-256 of content" and "HMAC-SHA256". BLAKE3 would need a superseding ADR, so it needs strong evidence.
- **Security:** both are fine for this use. BLAKE3 targets 128-bit security against collision, preimage and second-preimage attacks and uses 256-bit keys (S3 §4.1). SHA-256 is git's chosen successor hash. git's criteria were 256 bits, wide availability in OpenSSL/CommonCrypto, and collision plus second-preimage resistance, with speed only as a tiebreaker (S11). Confidence: high.
- **Portability and 30-year verifiability** favour SHA-256 (C7):
  - Native on Android, iOS, macOS and Workers.
  - `sha256sum` is on every Linux.
  - restic names repository files by SHA-256 so `sha256sum` can check them (S13).
  - BLAKE3 would be bundled through the Rust core (acceptable under T1 option C), but the homelab fixity tools and any second-language implementation would then need a non-platform library. Multicodec lists `blake3` as "draft" and `sha2-256` as "permanent" (S23). That is a weak maturity signal and not decisive.
- **Speed:**
  - On x86 with SHA-NI the project measured 1,136 MB/s for SHA-256 alone (C2). The BLAKE3 paper reports single-thread BLAKE3 at 12× SHA-256 on Cascade Lake, but against OpenSSL 1.1.1d, whose SHA-256 is not necessarily SHA-NI-accelerated on that machine (S3 Fig. 3). Treat it as not comparable.
  - On phones, nothing primary exists (C5). The one data point is secondary (C6): with ARMv8 SHA-2 instructions, compute is about 90× the BUD-HASH effective floor of 6 MB/s. So on such phones **flash I/O, thermal throttling and energy are the likely limits, not the choice of hash**. Confidence: low.
  - The open risk is a low-end SoC **without** the `sha2` feature (C4). There sha2 0.11 uses its portable backend, whose throughput on in-order ARM cores (for example Cortex-A53/A55) is unmeasured. A1-S1 must record `HWCAP_SHA2` (`/proc/cpuinfo` "Features") for every test device.
- **Decision rule for A1-S1** (restating PLAN in budget terms):
  - SHA-256 meets **BUD-HASH** on the low-end class without thermal throttling → SHA-256 is final.
  - Otherwise, measure BLAKE3 (NEON is on by default for aarch64 in `blake3` 1.8.7, S9) on the same device. Only if BLAKE3 meets BUD-HASH where SHA-256 fails, raise a decision request to supersede ADR-0001 on the algorithm. Report **BUD-BAT-S** for both.

### 2. Construction: where the family key is applied

The PLAN's two axes are separate: **algorithm** (SHA-256 or BLAKE3) and **structure** (MAC over the content, or MAC over a digest). Keyed BLAKE3 over content has the same structure as HMAC over content.

| Property | A. HMAC(K, content) (ADR-0001 wording) | B. HMAC(K_e, 0x01 ‖ SHA-256(content)) (recommended) | C. keyed_BLAKE3(K, content) | D. keyed_BLAKE3(K, BLAKE3(content)) |
|---|---|---|---|---|
| Reads of the file | 1 | 1 | 1 | 1 |
| Hash computations per byte, given that the plain digest is also needed (ADR-0001) | **2** (SHA-256 + HMAC) (C2) | **1** | 2 (SHA-256 + BLAKE3), or 1 if BLAKE3 replaces SHA-256 as the plain digest | 1 |
| Homelab verification at ingest | SHA-256 + HMAC over the whole plaintext (2 per byte) | SHA-256 (1 per byte) + one HMAC | 2 per byte | 1 per byte |
| Rotate the family secret from the cache, no file reads | **No**. Every device and the homelab re-read everything (C12) | **Yes** | No | Yes |
| Opaque to the cloud while K is secret | Yes | Yes | Yes | Yes (C9) |
| After K leaks | Confirmation needs the file's bytes | Confirmation possible from a SHA-256 alone (C10) | Needs the bytes | From a BLAKE3 digest alone |
| Inherits unkeyed-hash collisions | No | **Yes** (C11) | No | Yes |
| Matches settled text | Yes | Changes "over content" to "over the SHA-256 of the content" (DR-A1-1) | No (algorithm and structure) | No (algorithm) |
| Stock-tool check of the inner value | n/a | `sha256sum` | n/a | `b3sum` (not preinstalled) |

**Assessment.** B keeps what matters about the settled scheme: whole-file dedup across users on plaintext, keyed so the cloud sees opaque IDs. It costs the least per byte and is the only SHA-256 option that makes rotation affordable. Rotation is the only remedy ADR-0001 leaves for a leaked family secret, and S2 R-5 notes that "one leak lets whoever holds the cloud data test all historical IDs". Under A, rotation costs about 28 h of homelab re-reading plus a full re-read on every device (C12), and a family admin will not realistically do that. The leak would stay open for all future uploads. Confidence: medium-high.

**What B gives up** (for the skeptics):
1. **K plus a digest is enough to test.** Plain SHA-256 values of family files exist only on devices, in encrypted metadata and at the homelab (ADR-0001 §2). An attacker holding K and a public hash list of *published* files (for example a banned book) can test the cloud index without downloading those files. Under A they would need the bytes, which for published files is little extra effort. Marginal. (C10)
2. **SHA-256 collisions.** A practical SHA-256 collision would let a device crafting both files force two contents onto one ID. The victim's file must then be attacker-crafted, and the homelab's SHA-256-keyed catalog would be affected anyway. No SHA-256 collision is known (none found in this sweep; FIPS 180-4 is blocked). The kind byte allows migration. (C11)

**Key derivation.** Use the family secret only as HKDF input key material and derive a separate key per purpose and epoch. This is T1 spike 2's D-4 generalised. The BLAKE3 paper (S3 §7) explains the hazard of using one key directly with both HMAC and HKDF. Tarsnap keeps a separate HMAC key per purpose: file, chunk, name, cparams (S19). Kopia versions its derive_key context string ("kopia blake3 derived key v1", S16). Strawman:

```
K_e     = HKDF-SHA256(ikm = S_e (32 random bytes, epoch e), salt = "", info = "reliquary/v1/dedup-id-key", L = 32)
digest  = SHA-256(content)                      -- plain; never leaves the device except inside ciphertext
mac     = HMAC-SHA256(K_e, 0x01 || digest)      -- 0x01 = kind "whole-file SHA-256"
id_bin  = 0x01 || u16be(e) || mac               -- 35 bytes
id_text = "rd1-" || hex4(e) || "-" || hex64(mac) -- 73 chars, lowercase
```

The info string intentionally differs from the throwaway spike's `reliquary/v1/dedup-key`, so the spike's values can never be mistaken for production IDs. `identifiers.md` fixes the exact bytes.

### 3. Wire format and encoding

- **Keep all 256 bits.**
  - Kopia defaults to a 128-bit truncation (`BLAKE2B-256-128`, S16). For accidental collisions 128 bits would be enough: for 10⁷ items the probability is ≈ n²/2¹²⁹ ≈ 1.5·10⁻²⁵ (arithmetic).
  - Truncation, though, cuts collision resistance against a key-holding device to 2⁶⁴ work. It saves 16 bytes per row (≈ 160 MB of binary per 10⁷ rows, or 320 MB in hex), which is small against D1's 10 GB cap (fact-check item 5).
  - NIST SP 800-107 truncation guidance is blocked, so the choice avoids needing it.
  - Confidence: medium-high.
- **Version, kind and epoch in the ID.** git's transition shows the cost of IDs that do not describe their own algorithm: a repository-wide format flag plus a bidirectional translation table (S11). Duplicacy picks its algorithm implicitly from the compression level (S17), a cautionary example. Perkeep (`sha224-<hex>`, S25) and multihash (S23) are prefix precedents. The epoch lets the Worker reject stale-epoch clients explicitly instead of silently missing dedup, and lets the homelab read old USB bundles.
- **Encoding: lowercase hex.**
  - Base32 (RFC 4648, via Go stdlib S44; RFC blocked) would save 12 characters but gains little.
  - Hex matches `sha256sum` output, restic file naming, and every language's standard library.
  - Canonical form is lowercase only, and parsers reject anything else. R2 keys are case-sensitive, so two spellings would be two keys. Windows/exFAT are case-insensitive, so they would collide as filenames (C17).
  - 73 characters fits R2's 1,024-byte key limit, exFAT's 255-character names and Windows naming rules: no reserved characters, no trailing dot or space, and cannot equal CON/NUL/COM1 and so on.
- **Binary form** (35 bytes) goes in CBOR records, D1 and SQLite BLOB columns. The **text form** goes in R2 keys, USB file names, logs and JSON. Both are defined together in `identifiers.md`.
- **R2 per-key write limit** (1 write/s per key, HTTP 429, S26): staging objects must not be keyed by dedup ID alone. T1 spike 2 already uses `staging/<dedup_id>/<upload_id>`. C1 owns the layout.

### 4. Whole-file digest vs block or tree hash

- **Whole-file SHA-256 stays the identity.** Confidence: medium-high.
  - Keepsakes are effectively immutable (ADR-0001 §2).
  - Transport-level per-part integrity already exists: age STREAM authenticates each 64 KiB chunk, and T1 spike 2 journals chunk tags for resume (S2 §1, §8.3).
  - Hashing different files in parallel is available without a tree.
  - The Dropbox-style block hash (S22) and a BLAKE3/Bao tree (S6) both give per-part verification, but stock tools cannot reproduce the Dropbox value, and the Bao value needs `b3sum`. Bao has one real attraction: its root hash *is* the BLAKE3 hash (C18). That would matter only if BLAKE3 were chosen for speed.
- **Reservation, not adoption:**
  - Kind `0x02` = "chunk-list ID", HMAC over the SHA-256 of a canonical chunk list under its own HKDF label.
  - A2's metadata record gets an optional, ignored-if-absent chunk-list field.
  - No CDC now: the 2025 chunking attacks recovered keyed CDC parameters from observed chunk sizes (C20; F3 owns the analysis).

### 5. Rotation (ID side; D2 owns custody and the trigger)

1. The admin creates S_{e+1}. The homelab keeps **all** epoch secrets, so old USB bundles and in-flight uploads stay verifiable.
2. **Homelab re-derivation:** for every committed item, compute `HMAC(K_{e+1}, 0x01 ‖ sha256)` from the catalog. The catalog must therefore keep the plain SHA-256 of every item (hand-off to A6). Publish the new IDs to the cloud index as a set, not as old→new pairs. Then delete the epoch-e rows.
   - Caveat: the cloud index also stores size (S2 receipts use (dedup_id, size)), so a cloud observer can partly link the epochs. That does not matter against the threat rotation addresses (an attacker holding K_e).
3. **Clients** receive S_{e+1} sealed to their enrollment key (D2/D3) and re-derive from their cache. A1-S2 target: 1M entries in < 60 s with zero file reads. Revoked devices never receive S_{e+1}.
4. **Worker:** accepts epoch e+1. For epoch e it answers "stale key, fetch the new one" after a grace window, and never answers "present" for a retired epoch.
5. **What rotation achieves:**
   - Someone holding K_e and a *later* copy of the cloud index can no longer test anything.
   - Someone who copied the index before rotation still can, for items committed before it (no forward secrecy; S2 R-5).
   - Tahoe's "new deduplication domain" (C14) is the fallback if re-derivation were impossible, and it would double storage until clean-up. Construction B avoids it.

### 6. Hash-cache contract (A1 owns the contract; B5/B2/B4 supply the signals)

Normative-draft rules for `identifiers.md`:

- **R1 Keying.**
  - The cache maps (source plugin, source locator, platform file identity, size, mtime at native precision, change time where the platform has one, opaque plugin version token) → (sha256, bytes hashed, time hashed, status).
  - Dedup IDs are derived per epoch and memoised; they are never the primary cached value. This is what makes rotation cheap.
  - Signals by platform:
    - ADR-0001 §3's tuple is the minimum.
    - Unix: add ctime (restic rationale, C16).
    - Windows: B5 checks whether `FILE_BASIC_INFO.ChangeTime` is reliable (S30).
    - iOS: the PhotoKit version token (b4 note K5).
    - Android MediaStore signals: B2.
- **R2 Fail-safe.** If any recorded signal differs, or the plugin cannot supply one it previously supplied, rehash.
- **R3 Racy window.** An entry is *racily clean* if the file's mtime is ≥ (snapshot time − G). G = max(the filesystem's timestamp granularity, 2 s); FAT write time has 2 s resolution (C15). Racily clean entries are not trusted on the next scan. Adapted from git (C15), using the same clock the filesystem reports where possible. Where it cannot, B5 defines a safe bound. **Quiescence:** do not start pass 1 on a file modified within Q ≥ 2G (S2 E5; B5 sets Q). This also avoids hashing half-written camera files.
- **R4 TOCTOU.** Take stat snapshots before and after pass 1 and around every encryption window. On any change, mark the entry "unstable" and requeue (already in S2 §6 and C3). Hashing again during encryption is optional (SHOULD NOT on phones, for cost). The end-to-end guarantee is R5.
- **R5 End-to-end check.** The homelab decrypts, recomputes SHA-256 and the dedup ID, and rejects any mismatch before any catalog write (S2 §11 steps 4–5). The client never treats pass-1 values as proof.
- **R6 A cache hit is a hint, never protection.** "Protected" requires a homelab receipt (S2 §1, item 6). A hit whose receipt is missing is re-queried and, if needed, re-uploaded. restic similarly re-stores a file whose blobs are missing from its index (S14).
- **R7 Explicit failure state.** "Hash failed (reason, retry-after)" is distinct from "not yet hashed" and is surfaced to E3. Immich's iOS app got assets stuck forever without it (S39, secondary).
- **R8 Cache provenance.** The cache records its own device and install ID. A cache that was copied or restored from an OS backup is treated as all-racy until each entry is revalidated (S41, secondary). The cache is excluded from OS and cloud backups, as S2 R-1 already requires for the upload journal.
- **R9 Sampled re-verification.** Re-hash a small random sample of cache hits over time to catch changes the signals missed. B5 sets the rate against BUD-SCAN and BUD-BAT-D. This is a proposal; it has not been measured.
- **R10 Opening.** Re-check after opening that the path is still a regular file (restic fstat after open, S14).

### 7. Items with no device of origin (A9)

The ID is a pure function of (content bytes, epoch key). The homelab importer links the same Rust core, computes SHA-256 and the current-epoch ID, and publishes the ID to the cloud index, so devices do not re-upload those files. Provenance (import batch, source medium) goes in the metadata record, never in the ID. Immich's external-library checksums that did not match content (S42, secondary, cause unknown) are the failure to test against: an A1-S3 vector must show that importer and device produce the same ID for the same bytes.

### 8. Scout conflicts resolved

- **Borg ID re-verification.** The primary text says `id == MAC(id_key, decompressed)` checking is *optional* in the AEAD modes and not done on every read (S15). The scout's "re-verified on read" was too strong.
- **Tahoe confirmation attack.** The primary text (S20) requires the attacker to hold the secret **and** a copy of the file.
- **BLAKE3 on ARM.** The paper's ARM result (1.3× SHA-256) is for 32-bit ARM1176 without SHA-2 instructions (S3). It does not support "BLAKE3 beats SHA-256 on phones".
- **Version and path fixes.** bao-tree is 0.16.1, not 1.16.1. git's racy-git document moved to `racy-git.adoc`. sha2 has no `asm` feature (C3).

### Alternatives compared

| Option | Fit with settled requirements | Pros | Cons | Evidence |
|---|---|---|---|---|
| SHA-256 + HMAC over content (ADR-0001 as written) | Exact | Matches the text; no dependence on unkeyed collisions | 2 hash computations per byte on device and at the homelab; rotation needs a full re-read (≈ 28 h homelab + every device) | C2, C12 |
| **SHA-256 + HMAC over SHA-256, HKDF epoch keys** | Needs the owner to accept a wording change (DR-A1-1) | 1 computation per byte; rotation from the cache; stock-tool fixity | K + digest enables testing; inherits SHA-256 collisions | C9–C12 |
| BLAKE3 + keyed BLAKE3 | Supersedes ADR-0001 algorithm | Fast in software; Bao tree for free | Not native on any platform; weaker 30-year tooling; performance claims on phones unverified | C5, C7, C18 |
| Tree/block hash + HMAC over the root | Supersedes ADR-0001 | Per-part plaintext verification | Stock tools can't reproduce it; per-part integrity already from age STREAM | C18, S22 |
| FastCDC per-chunk IDs | Out of v1 scope | Sub-file dedup | 2025 attacks; complexity. Reserved as kind 0x02 | C20 |

### Similar work and lessons

| Project | What they do | Borrow or avoid | Source |
|---|---|---|---|
| git | Racy-clean rule; SHA-256 transition via repo flag + translation table | Borrow the racy rule; avoid untagged IDs | S10, S11 |
| restic | mtime+ctime+size+inode; unkeyed SHA-256 IDs; hex filenames | Borrow the signals and hex naming; avoid unkeyed IDs | S12–S14 |
| Borg 2 | Chunk ID = MAC(id_key, data); HMAC-SHA256 or keyed BLAKE3 selectable | Borrow the keyed-ID rationale | S15 |
| Kopia | Named keyed hash registry; 128-bit truncated default; versioned derive_key label | Borrow named/versioned schemes; do not truncate | S16 |
| Duplicacy | ID = keyed hash of a stored hash | Borrow (the digest construction); avoid implicit algorithm choice | S17 |
| Tarsnap | Separate HMAC keys per purpose | Borrow per-purpose key derivation | S19 |
| Tahoe-LAFS | Convergence secret = dedup domain; documented attacks | Borrow the threat statement; the rotation cost warning | S20, S21 |
| bupstash | Put-only keys hold hash keys but cannot decrypt | Matches "devices append only" | S18 |
| Dropbox | 4 MiB block SHA-256 then SHA-256 of digests | Avoid (tooling burden) | S22 |
| Immich | Per-asset hash cache on mobile; failure states | Borrow cache keyed by local asset ID; add explicit failure state | S39, S43 |

### Tools and libraries

| Name | Purpose | Licence | Maturity | Source |
|---|---|---|---|---|
| RustCrypto `sha2` 0.11.0 | SHA-256 with runtime SHA-NI / AArch64 `sha2` detection | MIT/Apache-2.0 (per crate metadata; verify at G3) | Latest on crates.io 2026-09-29; edition 2024, MSRV 1.85 | S7 |
| RustCrypto `hmac` 0.13.0 | Streaming HMAC, constant-time verify | MIT/Apache-2.0 (verify) | Latest 2026-09-29 | S8 |
| RustCrypto `hkdf` | Key derivation | MIT/Apache-2.0 (verify) | Version not checked in this sweep | — |
| `blake3` 1.8.7 | Benchmark comparison only | CC0/Apache-2.0 (per repo; verify) | Latest non-yanked 2026-09-29 | S9 |
| `bao` 0.13.1 / `bao-tree` 0.16.1 | Not adopted; reference only | — | — | S6 |
| Node `crypto` (createHash / createHmac) | Second-language vectors, streaming > 4 GiB | — | Node 22 in container | C19 |
| Android `MessageDigest` / `Mac`; CryptoKit `SHA256` / `HMAC` | Platform cross-checks (optional) | — | API 1+; iOS 13+ | S33, S34, S36 |

## Spikes

The separate spike runner fills in this section. Nothing here is a measurement.

| Spike | Exec tag | Budget IDs | Data class | Status | Result |
|---|---|---|---|---|---|
| A1-S1 Hash benchmark, SHA-256 vs BLAKE3 (x86 reference in container; phones as kit `docs/research/kits/A1-S1/`) | CT (x86 reference only) + OL (kit) | BUD-HASH, BUD-BAT-S | SYN (H3 Tier S size ladder) | Running (spike runner) | Pending. The kit must record `HWCAP_SHA2` per device (Findings §1) |
| A1-S2 Rotation over a 1M-entry cache | CT | (PLAN: client < 60 s, zero reads; homelab < 24 h) | SYN (Tier M `m-1m`) | Running (spike runner) | Pending. Also record the arithmetic re-read cost of construction A (C12) |
| A1-S3 Vectors, Rust + TS or Kotlin, 50 vectors | CT | — | SYN | Running (spike runner) | Pending. Should include SHA-256 padding boundaries (55/56/63/64/65 B), 1023–1025 B, 64 KiB ± 1, 4 GiB ± 1 via a generated pattern (BLAKE3 test-vector style, S5), epoch variants, the importer/device equality case, and negatives: raw secret as key, no kind byte, HMAC over content, wrong epoch, uppercase text refused |

## Conflicts with settled text

1. **CLAUDE.md** ("Cross-user dedup uses HMAC(family secret, content)") and **ADR-0001 §2** ("Dedup ID = HMAC-SHA256(family dedup secret, content)"). The recommendation MACs the content's SHA-256 digest under an HKDF-derived epoch key. The meaning is unchanged: whole-file, plaintext content, cross-user, opaque to the cloud. The wording and construction are not. → DR-A1-1. Nothing was edited.
2. **ADR-0001 §3** cache key `(source locator, size, mtime, platform file ID)`. The contract adds change time or version token, a racy rule and failure states. This is an extension, not a contradiction; recorded in ADR-0006.
3. **ADR-0001 "the cloud cannot test for known files"** holds only while no device's secret has leaked. This is already T1's D-6; A1 supports it.

## Open questions

- Which low-end Android SoCs lack the AArch64 `sha2` feature, and what does software SHA-256 reach on them? Answered by A1-S1 (OL kit), or earlier from the device's `/proc/cpuinfo` once L12c is bought (H5).
- Phone energy per GB for SHA-256 vs BLAKE3 (BUD-BAT-S). A1-S1 kit.
- Rotation trigger policy: every lost device, or only a confirmed compromise? Also the owner time involved (BUD-SUPPORT). D2 decides; A1 supplies costs from A1-S2.
- Grace window for retired epochs, and the behaviour of devices that stay offline across a rotation. A3 (protocol) and D3.
- Whether Windows `ChangeTime` is reliable enough to act as ctime. B5.
- RFC 4231, RFC 5869 and FIPS 180-4 reference values could not be fetched (blocked). A1-S3 must cross-check them with independent implementations and label them secondary.

## Recommendation

1. **Algorithm:** SHA-256, as ADR-0001 already says. Reconsider only if A1-S1 shows the low-end phone class missing BUD-HASH with SHA-256 while BLAKE3 meets it.
2. **Construction:** `dedup_id = HMAC-SHA256(HKDF-SHA256(S_e, "reliquary/v1/dedup-id-key"), 0x01 ‖ SHA-256(content))`. It halves per-byte hash work on devices and at ingest, and it makes rotating the family secret practical. It gives up a little (C10, C11), and the owner should accept that knowingly (DR-A1-1).
3. **Format:** a 35-byte binary form and the 73-character lowercase-hex text form `rd1-eeee-<64 hex>`. Full 256 bits. Strict canonical parsing.
4. **Identity layers:** plain SHA-256 is the permanent, key-independent content identity at the homelab. The dedup ID is a per-epoch, cloud-facing alias. A6 should address the store and catalog by SHA-256, so rotation never moves stored data.
5. **Cache contract:** R1–R10 above, written into `identifiers.md` and ADR-0006.
6. **No tree hash and no CDC in v1.** Kind `0x02` is reserved.

**What would change this:**
- A1-S1 phone results (algorithm).
- A credible SHA-256 collision advance (construction B's weak point; the migration path is the kind byte).
- The owner rejecting any deviation from "HMAC(family secret, content)". Then use construction A with HKDF keys, and accept that rotation means a full re-read.

## Decision requests

### DR-A1-1: Apply the family key to the file's SHA-256 digest instead of to the whole file (H1 to assign an OD number)
- **Needed by:** Gate A (one-way door #1), before any real family file is hashed.
- **Evidence:** this note (§2, §5, C9–C12); `content-encryption-format.md` §6, §14, D-4.
- **Options:**
  | Option | What it means for the family | Cost (money and owner time) | Reversibility | Risks |
  |---|---|---|---|---|
  | A. HMAC over the whole file (as written today) | Same privacy; slower first backup on phones (2 hashes per byte) | If the secret ever leaks, retiring it means every device re-reads everything and the homelab re-reads ~10 TB (~28 h at 100 MB/s) | One-way door | In practice a leaked secret is never retired |
  | B. HMAC over the file's SHA-256 (recommended) | Same privacy while the secret is safe; faster first backup | Rotation takes minutes on devices and hours or less at the homelab, with no re-reads | One-way door | Holder of a leaked secret can test from a digest alone; relies on SHA-256 collision resistance |
  | C. Keyed BLAKE3 | Same privacy | Bundled library everywhere; weaker long-term tooling | One-way door | Only justified by A1-S1 results |
- **Recommendation:** B. It keeps the settled meaning (whole-file, cross-user, opaque to the cloud) and makes the only remedy for a leaked secret, rotation, affordable. It also cuts the hashing work on phones.
- **Touches settled text:** yes. CLAUDE.md "Encryption trust model" line and ADR-0001 §2 table row "Dedup ID = HMAC-SHA256(family dedup secret, content)". This needs a superseding ADR-0006 section; not drafted in this stage.
- **If no decision by the deadline:** the run assumes B for ADR-0006 drafting and vectors. Nothing is hashed with production keys before the owner accepts ADR-0006.

### DR-A1-2: Epoch-tagged dedup IDs, with old epochs retired after a rotation
- **Needed by:** Gate A (together with DR-A1-1 and OD-08 / D2).
- **Evidence:** §3, §5.
- **Options:**
  | Option | What it means for the family | Cost | Reversibility | Risks |
  |---|---|---|---|---|
  | A. Epoch in every ID; Worker refuses retired epochs after a grace window (recommended) | A device that missed a key update is told to update rather than silently re-uploading | Two extra bytes per ID; a key-update path (D2/D3) | Costly to add later (every ID changes) | Offline devices need a clear "update key" nudge (E3) |
  | B. No epoch; rotation = new dedup domain (Tahoe style) | After rotation old files do not deduplicate; storage can double until clean-up | Up to 2× storage for re-seen content | Easy to switch to A only before first ingest | Silent loss of dedup; confusing status |
- **Recommendation:** A.
- **Touches settled text:** no. ADR-0001 leaves "rotating the dedup secret" open.
- **If no decision by the deadline:** assume A.

## Hand-offs

| To | What | Why |
|---|---|---|
| A6 (ADR-0012/0013) | The catalog must store the plain SHA-256 of every committed item; address the store by SHA-256, not the dedup ID | Homelab re-derivation on rotation (§5); rotation never moves data |
| A2 (ADR-0007) | The metadata record carries `sha256`, `dedup_id` (binary form) and an optional reserved chunk-list field | §4 reservation; homelab verification |
| A3 (ADR-0009) | "Stale epoch" response; never answer "present" for a retired epoch; grace window | §5 step 4 |
| A4 (ADR-0011) | Use the 73-char lowercase-hex text form for any ID-named file on FAT/exFAT; accept any epoch the homelab holds | §3; bundles in the post |
| C1 (ADR-0010) | Never key R2 objects by dedup ID alone (1 write/s per key) | S26; S2 E3 |
| D2 (ADR-0008) | Custody of all epoch secrets at the homelab; rotation trigger; sealed delivery to devices | §5 |
| B5 / B2 / B4 | Provide the R1 signals per platform; set G and Q; check Windows `ChangeTime`; set the R9 sampling rate | §6 |
| E3 | Status vocabulary for "hash failed" and "unstable file" (R7) | §6 |
| F3 | Confirm the C10/C11 security assessment against the attack matrix; CDC reservation wording | §2, §4 |
| H1 | Blocked sources listed in Method; PLAN wording fixes (sha2 "asm", racy-git path) | Registry owner |
| Next A1 stage | Write ADR-0006 draft and `docs/spec/identifiers.md` from §2–§6 once spikes report | Deliverables |
