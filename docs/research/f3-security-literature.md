# F3. Security literature on E2EE storage and deduplication

- **Workstream:** F3 (see `docs/research/PLAN.md`, section "F3.")
- **Status:** Draft (analyst deep read, Wave 1, batch W1-a). Not yet under skeptic review. Spike results pending: a separate spike runner is running F3-S1/S2/S3 in parallel.
- **Date:** 2026-09-29 (last updated 2026-09-29)
- **Feeds:** OD-06 (PQ recipients), OD-08 (recovery recipient: coupling found here), OD-04 (presence-query semantics, as an addition), OD-17 (AR-05/AR-06 wording); ADR-0006 (A1), ADR-0007 (A2), ADR-0009 (A3), ADR-0010 (C1), ADR-0035 (G2 negative tests); one-way doors #1 (dedup-ID construction) and #2 (object envelope, PQ, sender authentication)
- **Depends on:** T2 (`fact-check-adr-0001-0002.md`), D1 (`d1-threat-model.md`, SR-01…SR-26, AR-04…AR-08), T1 spike 2 (`content-encryption-format.md`, "CE"), A1 (`a1-content-identity.md`)
- **Traceability rows advanced:** R-21 (opaque IDs; the F3 attack matrix is named as evidence), R-19/R-20 (encryption, devices cannot read), R-44 (cloud never sees plaintext)

## Summary

The ADR-0001 design is sound against the attack classes in the literature **once D1's requirements are in place**. Three gaps remain that the earlier notes did not close. Each gets a recommendation below.

1. **The "already have it" answer is the largest open leak.** Every enrolled device holds the family dedup secret. Tahoe-LAFS documents that any holder of such a secret can confirm whether a victim stores a known file, and can brute-force the unknown fields of a mostly known document. A per-device rate limit cannot both let a new phone seed (tens of thousands of lookups in hours, per BUD-HASH) and make a 10,000-file probe take 30 days. The oracle therefore has to be **narrowed and audited**, not just throttled:
   - scope "present" answers to the requesting person's own uploads by default;
   - require the signed metadata record *before* the answer (record-first);
   - count lookups exactly per device in a Durable Object and alert.

   The Workers rate-limit binding is documented as a burst guard only.
2. **Exact sizes leak.** age adds no padding. Padmé costs at most 3.1 % for files of 64 KiB to 4 GiB (computed from the reference code) and is already deployed by Borg and Tarsnap. It is worth adopting if F3-S1 confirms that most sizes are unique. Padding is useless unless the plaintext size is also removed from the cloud-visible receipt and index fields where the CE design currently has it.
3. **PQ and recovery are coupled.** The age spec says a file encrypted to the hybrid post-quantum recipient SHOULD NOT also be encrypted to a classical one, and Go age refuses to do it. A scrypt stanza must be alone. So if OD-06 is "PQ from day one", the OD-08 recovery recipient must also be an `mlkem768x25519` key, not a passphrase stanza.

Recommendation on OD-06: **yes, PQ from day one**, homelab-side with Go age ≥ 1.3.0. The device-side encoder must add the hybrid stanza (the Rust `age` crate 0.12.1 has no native one) and pass the CCTV hybrid vectors.

Confidence: high on the primary-source facts (age spec, Tahoe, Borg, restic, Cloudflare docs, source code). Medium on the protocol inferences. The malicious-server papers (Hofmann–Truong, MEGA, Nextcloud) and the 2025 CDC papers stay *secondary only*, because eprint, arXiv, USENIX and ACM are blocked.

## Questions

| # | Question (PLAN F3) | Short answer | Confidence |
|---|---|---|---|
| 1 | What leaks even with HMAC IDs? | (a) **Exact plaintext size**, from ciphertext length (age has no padding; C7), from receipts and from Worker size fields (C10). (b) **Timing and per-device volume**, inherent to a relay (restic states the same; C26). (c) **ID equality across devices** (linking). (d) **The presence oracle** for any holder of the dedup secret, i.e. any compromised device (C11, C12). (e) Recipient type and payload size, readable with `age-inspect` (C6). | High (a–c, e); Medium (d bounds) |
| 2 | HMAC over content vs HMAC over SHA-256; domain separation; one root secret; rotation | Equivalent to the cloud before a leak. After a leak, the digest form also allows testing from SHA-256 hash lists without the files. Both depend on SHA-256 collision resistance in practice, because the homelab already verifies by SHA-256. The digest form is what makes rotation affordable, and rotation is the only remedy after a leak. **F3 supports A1's `HMAC(K_e, 0x01 ‖ SHA-256(m))` with HKDF-derived, epoch-tagged keys** (Kopia and Tahoe precedent for HKDF info labels and versioned tags). One addition: when the index is re-keyed, it must not give the cloud an old-to-new ID mapping (M-14). | Medium |
| 3 | Stolen dedup secret plus a curious cloud | This is message-locked encryption's known weakness. The pair can test **every** ID the cloud ever saw, offline and without rate limits, against any candidate set (Tahoe's two attacks, at scale). No forward secrecy. Mitigations: keep the secret out of Cloudflare (SR-15); rotate by epoch (A1); keep cloud-side ID history short. Accept the residual as AR-06. | Medium-high |
| 4 | Malicious-cloud attack classes: swap, replay, drop, withhold; binding metadata to object, device and sequence | The literature's failures (substituted keys, unauthenticated metadata, file injection, downgrade, "empty list" answers) all map onto D1's SR-02/03/04/05/13/14/16/22. age gives **no sender authentication** (C2), so device identity and sequence must come from the signed record. The record binds (dedup_id, sha256, size, header_mac), which plays the role of Borg's AAD binding. Open: sequence numbers (SR-13) and a PQ-aware header parser. | Medium (papers secondary) |
| 5 | Key commitment and multi-recipient issues; what age's header MAC and STREAM guarantee | Header: an HMAC-SHA-256 under a key derived from the file key, over all stanzas. So one header yields one file key for every recipient: forging two keys that both verify needs an HMAC collision (inference; the spec never says "commit"). Payload: 64 KiB ChaCha20-Poly1305 chunks with counter and final flag, so reorder, truncation and extension are detected if the final-chunk rule is enforced. Partitioning oracles are mitigated by the exact 32-byte stanza-body check; they are irrelevant for a single homelab identity. **Multi-recipient rules that bind Reliquary:** no PQ + classical mixing; scrypt alone. | High (spec facts); Medium (commitment inference) |
| 6 | Incidents | Tarsnap 2011 (nonce/CTR bug; rotation tools 20 days later), Borg 1.x multi-client counter reuse, Valsorda 2017 restic review, Dropbox "Dark Clouds" 2011, Proofs of Ownership 2011, 2025 CDC attacks. Each lesson is mapped in the matrix: M-17…M-22. | High for vendor-primary facts; Medium/secondary for paper details |
| 7 | PQ evidence (harvest now, decrypt later); reusable audit checklists | Keep-forever data plus ciphertext recorded in transit through Cloudflare or on USB means an X25519 wrap is exposed to a future quantum adversary. HMAC IDs and the symmetric layers are not. age has shipped a native hybrid (X-Wing) recipient since v1.3.0 (2025-12-27). Cost: a header of about 1.6 KB per object. NIST IR 8547 dates, Signal PQXDH and iMessage PQ3 are corroborating but secondary here. Checklists: Cure53/Ente (S3 upload header signing) is secondary only; Cryptomator and Tresorit were not reached (open). | Medium-high (PQ recommendation); Low (checklists) |
| 8 | (new) Can a per-device rate limit alone pass F3-S2? | **No**, on arithmetic from BUD-HASH (C12). Detection must rest on accounting: lookups that never become an upload or a record are the signal. | Medium |
| 9 | (new) Does padding survive the current CE and D1 designs? | Not as written. The receipt relayed by the Worker carries plaintext `size`, and SR-24 declares size to the Worker. Both must carry the padded length only (M-05). | High |

## Method

- **Sweep:** four scouts ran (docs, source, community/issues, standards/papers); their findings came in as JSON. This analyst resolved the conflicts between them and re-fetched the load-bearing primary sources into the scratchpad on 2026-09-29, reading them in full or in the relevant sections:
  - age spec (header, payload, native recipients);
  - age README (PQ, `age-inspect`);
  - Tahoe convergence-secret doc (full);
  - Borg master `security.rst` (attack model, AEAD/session keys, fingerprinting);
  - Borg 1.4 `security.rst`;
  - Borg wiki "CDC issues reported 2025" (full);
  - Borg `compress.pyx` ObfuscateSize and `help.rst.inc` (Padmé 250);
  - Tarsnap `NEWS.md`;
  - restic `design.rst` threat model (full);
  - PBS `crypt_config.rs` and technical overview;
  - dedis `purb/padding.go` (full);
  - Cloudflare rate-limit binding (full) and Durable Objects overview;
  - C2SP CCTV age README;
  - Wycheproof README;
  - X-Wing draft.

  Code and packages inspected:
  - Go `filippo.io/age` v1.3.2 module source (`pq.go`, `age.go` mixing check);
  - Rust `age` 0.12.1 crate (`src/native/`);
  - the `cctv-age` 0.2.0 npm package (vector names);
  - crates.io metadata for `x-wing`, `ml-kem` and `hpke`.
- **Computation:** Padmé and 64 KiB-bucket overhead bounds, derived from the reference `paddingLength` code. These are arithmetic results, not measurements of any corpus (F3-S1 measures).
- **Routes used:** raw.githubusercontent.com (vendor docs and source), proxy.golang.org, static.crates.io, crates.io API, registry.npmjs.org.
- **Scout conflicts resolved:**
  - *PBS "keyed digest".* Docs scout: "plaintext concatenated with the key". Source scout: SHA-256(data ‖ id_key) with id_key = PBKDF2(enc_key, "_id_key", 10). Both are true. The code is more precise: the appended key is a derived id_key, not the encryption key itself. Lesson unchanged: a keyed digest, not HMAC. The server can check only CRC-32 on encrypted chunks.
  - *Padmé overhead: "at most 12 %"* (paper abstract via snippet; Borg help text) *vs "3 %" (F3-S1 threshold).* Both are consistent. The 12 % bound covers tiny inputs. For 64 KiB–4 GiB the reference formula gives at most 1/32 ≈ 3.1 % (C8).
  - *"Attacker can not try faster than you do backup runs"* (Borg wiki). True for Borg's repository-side attacker. **Not** true for Reliquary's presence oracle, which answers interactively. Flagged so it is not imported as a mitigation.
  - *Tarsnap 2011 mechanism.* The community scout (LWN via snippet) and the standards scout agree on "nonce not incremented, versions 1.0.22–1.0.27". The vendor primary (daemonology.net) is blocked, so only the NEWS.md facts (dates, "critical security bug in chunk encryption code", rotation tools) are primary.
- **Blocked sources (to report to H1; `sources.md` not edited here):**
  - eprint.iacr.org (2024/1616, 2025/558, 2025/532, 2024/546, 2022/959, 2012/631, 2013/429, 2011/207, 2016/977, 2015/455, 2019/016, 2020/1491, 2020/1456);
  - arxiv.org and export.arxiv.org;
  - dl.acm.org, usenix.org, petsymposium.org;
  - nvlpubs.nist.gov, csrc.nist.gov, ncsc.gov.uk;
  - rfc-editor.org, datatracker.ietf.org (draft-ietf-hpke-pq-03, RFC 2104/5869/9180);
  - daemonology.net, words.filippo.io, lwn.net, mega-awry.io, brokencloudstorage.info;
  - ente.com (Cure53 PDF), tahoe-lafs.org (Perttula entry);
  - api.semanticscholar.org, api.crossref.org (tried as metadata routes: no connection).

  The session's WebSearch budget was already exhausted (200/200), so no further snippet checks were possible in this stage.
- **Stop rule:** every in-scope question has a primary source or is explicitly marked inference or secondary. The remaining leads are papers behind blocked hosts. They are precedent and do not carry any recommendation on their own.

## Sources

| # | Source | Publisher | Version or date | Accessed | Primary? |
|---|---|---|---|---|---|
| S1 | age v1 spec, `C2SP/C2SP @ main : age.md` (stable at c2sp.org/age) | C2SP (Valsorda et al.) | main HEAD | 2026-09-29 | Yes |
| S2 | age README, `FiloSottile/age @ main : README.md` | F. Valsorda | main HEAD | 2026-09-29 | Yes |
| S3 | Go module `filippo.io/age` v1.3.2 (`age.go`, `pq.go`); tags via proxy.golang.org `.info` (v1.3.0 2025-12-27T14:59Z; v1.3.2 2026-08-29T17:40Z) | F. Valsorda | v1.3.2 | 2026-09-29 | Yes |
| S4 | Rust `age` 0.12.1 crate, static.crates.io (`src/native/`: scrypt, tag, tagpq, x25519) | str4d | 0.12.1 | 2026-09-29 | Yes |
| S5 | C2SP CCTV age README, `C2SP/CCTV @ main : age/README.md`; npm `cctv-age` 0.2.0 (published 2025-12-08) vector names | C2SP | 0.2.0 | 2026-09-29 | Yes |
| S6 | Project Wycheproof README and `testvectors_v1/` (ed25519, hmac_sha256, hkdf_sha256, chacha20_poly1305, x25519, mlkem_768: HTTP 200) | C2SP | main HEAD | 2026-09-29 | Yes |
| S7 | X-Wing KEM, `dconnolly/draft-connolly-cfrg-xwing-kem @ main` (editor's copy) | D. Connolly et al. | front matter 2026-09-23 | 2026-09-29 | Yes (draft) |
| S8 | Tahoe-LAFS "The Convergence Secret", `tahoe-lafs/tahoe-lafs @ master : docs/convergence-secret.rst` | Tahoe-LAFS | master HEAD | 2026-09-29 | Yes |
| S9 | Borg internals: security (borg 2), `borgbackup/borg @ master : docs/internals/security.rst` | BorgBackup | master HEAD | 2026-09-29 | Yes |
| S10 | Borg 1.4 internals: security, `borgbackup/borg @ 1.4-maint : docs/internals/security.rst` | BorgBackup | 1.4-maint HEAD | 2026-09-29 | Yes |
| S11 | Borg wiki "CDC issues reported 2025", `raw.githubusercontent.com/wiki/borgbackup/borg/CDC-issues-reported-2025.md` | Borg maintainers | updates dated 2025-06-04 | 2026-09-29 | Yes (maintainer statement) |
| S12 | Borg `src/borg/compress.pyx` (ObfuscateSize) and `docs/usage/help.rst.inc` (level 250 = Padmé) | BorgBackup | master HEAD | 2026-09-29 | Yes |
| S13 | Tarsnap `NEWS.md` (1.0.28 2011-01-18; 1.0.29 2011-02-07; 1.0.41 2025-03-21) | Tarsnap | master HEAD | 2026-09-29 | Yes |
| S14 | restic design, Threat Model, `restic/restic @ master : doc/design.rst` | restic | master HEAD | 2026-09-29 | Yes |
| S15 | Proxmox Backup Server `pbs-tools/src/crypt_config.rs` and `docs/technical-overview.rst` | Proxmox | master HEAD | 2026-09-29 | Yes |
| S16 | Kopia v0.23.1 source (`repo/hashing/hashing.go`, `internal/crypto/key_derivation.go`, AES256-GCM-HMAC-SHA256 encryptor) | Kopia | v0.23.1 (2026-06-15) | 2026-09-29 (source scout) | Yes |
| S17 | Duplicacy `src/duplicacy_config.go` | Duplicacy | master HEAD | 2026-09-29 (source scout) | Yes |
| S18 | Syncthing `lib/protocol/encryption.go` (untrusted-device encryption) | Syncthing | main HEAD | 2026-09-29 (source scout) | Yes |
| S19 | dedis PURBs `dedis/purb @ master : purbs/padding.go` (Padmé reference) and README | EPFL DEDIS | master HEAD | 2026-09-29 | Yes |
| S20 | Nikitin, Barman, Lueks, Underwood, Hubaux, Ford, "Reducing Metadata Leakage from Encrypted Files and Communication with PURBs", PoPETs 2019(4), https://petsymposium.org/popets/2019/popets-2019-0056.php | authors | 2019 | 2026-09-29 (blocked; snippet and Borg citation) | Primary, not read |
| S21 | Cloudflare Workers Rate Limiting binding, `cloudflare/cloudflare-docs @ production : src/content/docs/workers/runtime-apis/bindings/rate-limit.mdx` | Cloudflare | production HEAD | 2026-09-29 | Yes |
| S22 | Cloudflare "What are Durable Objects", `… : durable-objects/concepts/what-are-durable-objects.mdx` | Cloudflare | production HEAD | 2026-09-29 | Yes |
| S23 | Hofmann & Truong, "End-to-End Encrypted Cloud Storage in the Wild: A Broken Ecosystem", CCS 2024, https://eprint.iacr.org/2024/1616 | authors | 2024 | 2026-09-29 (blocked; snippets and press) | Primary, not read |
| S24 | Backendal, Haller, Paterson, "MEGA: Malleable Encryption Goes Awry", IEEE S&P 2023, https://eprint.iacr.org/2022/959 ; follow-up "Caveat Implementor!" (eprint 2023/329) | authors | 2022–2023 | 2026-09-29 (blocked) | Primary, not read |
| S25 | Albrecht, Backendal, Coppola, Paterson, "Share with Care: Breaking E2EE in Nextcloud", EuroS&P 2024, https://eprint.iacr.org/2024/546 ; Nextcloud advisories GHSA-4p33-rw27-j5fc, GHSA-jh3g-wpwv-cqgr | authors; Nextcloud | 2024 | 2026-09-29 (blocked) | Primary, not read |
| S26 | Harnik, Pinkas, Shulman-Peleg, "Side Channels in Cloud Services: Deduplication in Cloud Storage", IEEE S&P Magazine 8(6), 2010 | authors | 2010 | 2026-09-29 (ResearchGate listing only) | Secondary listing |
| S27 | Halevi, Harnik, Pinkas, Shulman-Peleg, "Proofs of Ownership in Remote Storage Systems", CCS 2011, https://eprint.iacr.org/2011/207 | authors | 2011 | 2026-09-29 (blocked) | Primary, not read |
| S28 | Mulazzani et al., "Dark Clouds on the Horizon", USENIX Security 2011 | authors | 2011-08 | 2026-09-29 (blocked) | Primary, not read |
| S29 | Bellare, Keelveedhi, Ristenpart, "Message-Locked Encryption and Secure Deduplication", EUROCRYPT 2013, https://eprint.iacr.org/2012/631 | authors | 2013 | 2026-09-29 (blocked) | Primary, not read |
| S30 | Keelveedhi, Bellare, Ristenpart, "DupLESS: Server-Aided Encryption for Deduplicated Storage", USENIX Security 2013, https://eprint.iacr.org/2013/429 | authors | 2013 | 2026-09-29 (blocked) | Primary, not read |
| S31 | Armknecht, Boyd, Davies, Gjøsteen, Toorani, "Side Channels in Deduplication: Trade-offs between Leakage and Efficiency", AsiaCCS 2017, https://eprint.iacr.org/2016/977 | authors | 2017 | 2026-09-29 (blocked) | Primary, not read |
| S32 | Liu, Asokan, Pinkas, "Secure Deduplication of Encrypted Data without Additional Independent Servers", CCS 2015, https://eprint.iacr.org/2015/455 | authors | 2015 | 2026-09-29 (blocked) | Primary, not read |
| S33 | Dodis, Grubbs, Ristenpart, Woodage, "Fast Message Franking: From Invisible Salamanders to Encryptment", CRYPTO 2018, https://eprint.iacr.org/2019/016 | authors | 2018 | 2026-09-29 (blocked) | Primary, not read |
| S34 | Len, Grubbs, Ristenpart, "Partitioning Oracle Attacks", USENIX Security 2021, https://eprint.iacr.org/2020/1491 | authors | 2021 | 2026-09-29 (blocked) | Primary, not read |
| S35 | Albertini et al., "How to Abuse and Fix Authenticated Encryption Without Key Commitment", USENIX Security 2022, https://eprint.iacr.org/2020/1456 | authors | 2022 | 2026-09-29 (blocked) | Primary, not read |
| S36 | Truong, Merz, Scarlata, Günther, Paterson, "Breaking and Fixing Content-Defined Chunking", CCS 2025, https://eprint.iacr.org/2025/558 | authors | 2025 | 2026-09-29 (blocked; Borg wiki cites it) | Primary, not read |
| S37 | Alexeev, Percival, Zhang, "Chunking Attacks on File Backup Services using Content-Defined Chunking", https://eprint.iacr.org/2025/532 | authors | 2025 | 2026-09-29 (blocked; restic threat model cites it) | Primary, not read |
| S38 | Colin Percival, "Tarsnap critical security bug", http://www.daemonology.net/blog/2011-01-18-tarsnap-critical-security-bug.html ; LWN 423690 | Tarsnap; LWN | 2011-01-18 | 2026-09-29 (blocked; snippets) | Primary, not read; LWN secondary |
| S39 | Filippo Valsorda, "restic cryptography", https://words.filippo.io/restic-cryptography/ | F. Valsorda | 2017-08-29 | 2026-09-29 (blocked; snippet) | Primary, not read |
| S40 | Borg issues #4883 (2019-12-17 → 2020-04-05) and #5711 (2021-02-28 → 2023-05-11); restic issues #5291 (2025-03-21 → 03-31), #5447 (open), #99 (2015) | community | as stated | 2026-09-29 (metadata only, community scout) | No |
| S41 | Cure53, Ente audit summary (Oct 2025), https://ente.com/reports/Cure53-Audit-Summary-Oct-2025.pdf | Cure53 | 2025-10 | 2026-09-29 (blocked; snippets conflict, see F1 note) | Primary, not read |
| S42 | NIST IR 8547 ipd (2024-11-12); Federal Register FIPS 203/204/205 notice (2024-08-14); UK NCSC PQC timeline (2025-03-20) | NIST; NCSC | as stated | 2026-09-29 (blocked; snippets) | Primary, not read |
| S43 | Signal PQXDH (2023-09); Apple iMessage PQ3 (2024-02) | Signal; Apple | as stated | 2026-09-29 (snippets) | Primary, not read |
| S44 | WhatsApp E2EE backups whitepaper and Meta engineering post (2021-09-10); NCC Group assessment (2021-10-27) | Meta; NCC | 2021 | 2026-09-29 (snippets) | Primary, not read |
| S45 | Apple Platform Security, Advanced Data Protection for iCloud | Apple | current guide | 2026-09-29 (snippets) | Primary, not read |
| S46 | In-repo: `content-encryption-format.md` (CE §5, §8.3, §9, §10, §12, §16), `d1-threat-model.md` (SR, AR, T-IDs), `a1-content-identity.md` (C8–C11), `corpus/README.md` (P11 indicative sizes) | this repo | 2026-09-29 | 2026-09-29 | Yes (project evidence) |

## Claims

Skeptic columns are blank: this is the analyst draft. "Key?" marks the claims skeptics should attack first.

| # | Claim | Sources | Key? | Skeptic 1 | Skeptic 2 | Skeptic 3 | Verdict |
|---|---|---|---|---|---|---|---|
| C1 | age v1 file key: 16 CSPRNG bytes, never reused. Header MAC = HMAC-SHA-256 keyed by HKDF(file key, "header") over the whole header up to `---`. Payload: 16-byte nonce; payload key = HKDF(file key, nonce, "payload"); 64 KiB ChaCha20-Poly1305 chunks with an 11-byte counter and a final-flag byte; EOF without a valid final chunk MUST error; seeking from the end MUST verify the final chunk first. | S1 | Yes | | | | pending |
| C2 | age has no sender authentication for public-key recipients. The spec invokes an "expectation of authentication" only for scrypt (which must be alone). Anyone with the homelab public key, including Cloudflare or any device, can make a valid object, so provenance must come from the device-signed record (SR-03). | S1 (+ inference; matches D1 C8, CE R-3) | Yes | | | | pending |
| C3 | Because the header MAC key derives from the file key and covers every stanza, a header cannot verify under two different file keys without an HMAC-SHA-256 collision. So an age file decrypts to at most one plaintext across all its recipients (key commitment at file level). The spec never states this; it is an inference. Reliquary also re-checks plaintext SHA-256 and HMAC after decrypting, which would catch a divergence independently. | S1, S33, S35 (not read) | Yes | | | | pending |
| C4 | A file encrypted to the `mlkem768x25519` recipient SHOULD NOT also be encrypted to non-PQ recipients (spec), and Go age v1.3.2 enforces this ("can't mix post-quantum and classic recipients"). An scrypt stanza MUST be the only stanza. **Therefore a PQ object's recovery recipient must itself be PQ, and cannot be a passphrase stanza.** | S1, S3 | Yes | | | | pending |
| C5 | Native PQ: Go age ≥ v1.3.0 (tagged 2025-12-27; latest v1.3.2, 2026-08-29). The Rust `age` 0.12.1 crate has native scrypt, tag, tagpq and x25519 only, with no `mlkem768x25519`. The container's `age` CLI is 1.1.1, which predates PQ. The stanza's KEM cites draft-ietf-hpke-pq-03 / `filippo.io/hpke-pq`, an IETF draft rather than an RFC. The RustCrypto `x-wing` crate (0.1.0, updated 2026-07-09) says it implements X-Wing "draft 06". Wire compatibility with age's stanza is **unverified**. | S1, S3, S4, crates.io metadata | Yes | | | | pending |
| C6 | The PQ header costs about 1.6 KB per object: README example, 1,627-byte header for one `mlkem768x25519` recipient, vs 168 B for X25519 in CE §5.2. `age-inspect` reveals recipient types, PQ use and payload size without a key. | S2, S46 | Yes (cost) | | | | pending |
| C7 | age defines no length padding. Ciphertext length = prefix + n + 16·⌈n/64 KiB⌉, so the exact plaintext size is visible to anyone holding the ciphertext (R2, USB finder). | S1, S46 (CE §5.4, R-4) | Yes | | | | pending |
| C8 | **Computed from the Padmé reference code** (`paddingLength`: E = ⌊log2 L⌋, S = ⌊log2 E⌋ + 1, round L up to a multiple of 2^(E−S)): (a) 64 KiB ≤ L < 4 GiB → 32 possible sizes per power-of-two range, maximum overhead 2^−5 ≈ 3.1 %; (b) 256 B–64 KiB → 16 sizes, at most 6.25 %; (c) ≥ 4 GiB → 64 sizes, at most 1.56 %. Examples: 1.30 MB → +0.83 %; 5.69 MB → +1.36 %. By contrast, 64 KiB buckets cost +31 % at 100 KB and +0.8 % at 1.3 MB. Byte-weighted totals on a real distribution are F3-S1's job. | S19 (+ arithmetic) | Yes (budget-like) | | | | pending |
| C9 | Deployed precedent: Borg `obfuscate` level 250 = Padmé ("limiting overhead to 12 %"), random-padding levels, off by default for cost. Borg computes chunk IDs over plaintext **before** padding, so enabling it does not break dedup. Tarsnap 1.0.41 (2025-03-21) pads chunks with PADME. | S11, S12, S13 | No | | | | pending |
| C10 | In the current designs the cloud sees exact plaintext size even if the object is padded: the CE commit receipt (relayed by the Worker in clear JSON) carries `size`, the dedup "present" check uses (dedup_id, size), and SR-24 has the device declare size at URL issuance. Padding therefore requires these fields to carry the padded length (or to be encrypted). | S46 (CE §10; D1 SR-24) | Yes | | | | pending |
| C11 | Tahoe-LAFS: anyone who knows the convergence secret can run *confirmation-of-a-file* and *learn-the-remaining-information*. The only defence is that the attacker lacks the secret. Changing the secret moves the client to a new "deduplication domain": old caps keep working, re-uploads use twice the space until GC. | S8 | Yes | | | | pending |
| C12 | **Arithmetic from BUD-HASH (proposed):** a low-end phone's first pass over 128 GB in 6 h at ≈ 2 MB average (P11 indicative median 1.3 MB) is on the order of 60k files, i.e. about 60k presence lookups in hours. Any per-device limit that allows this allows a 10,000-candidate probe in well under a day. A uniform rate limit therefore cannot pass F3-S2's ">30 days" branch; F3-S2 can only pass on the alert branch or with narrower answer semantics. | S46 (budgets, corpus), PLAN F3-S2 | Yes | | | | pending |
| C13 | The Workers Rate Limiting binding allows a period of only 10 s or 60 s. Counters are per Cloudflare location, cached and synced asynchronously; Cloudflare calls it "permissive, eventually consistent, and intentionally designed to not be used as an accurate accounting system". A Durable Object is single-threaded with strongly consistent storage, so it can keep exact per-device counts. | S21, S22 | Yes | | | | pending |
| C14 | Design inference for F3-S2: two changes turn the presence oracle into an audited one. (a) Record-first: the Worker answers "present" only after it holds the device's signed, encrypted record for that ID; SR-06 already requires the record to be sent. (b) Scope: "present" answers default to the requesting person's own prior uploads, with cross-person hits only above a size threshold. Every probe then leaves device-signed evidence at the homelab, and cross-person confirmation of small documents disappears. Not yet simulated. | S8, S46 (SR-06, SR-21) + inference | Yes | | | | pending |
| C15 | HMAC(K, m) and HMAC(K, SHA-256(m)) are equally opaque to a party without K (both keyed PRFs; RFC 2104 text blocked, argued from Borg, Kopia and Tahoe practice). After K leaks, the digest form also allows testing from SHA-256 lists without the files. Both depend in practice on SHA-256 collision resistance, because the homelab verifies by SHA-256 (ADR-0001 §2). The digest form makes rotation possible without re-reading 2–10 TB. Net: support A1's construction. | S9, S16, S8, S46 (A1 C9–C11) | Yes | | | | pending |
| C16 | A leaked dedup secret combined with the cloud's stored ID history allows offline, unlimited testing of every historical ID against any candidate set, with no rate limit. This is the brute-force weakness of message-locked encryption over predictable messages. Rotation limits only future exposure. | S29/S30 (not read), S8, S46 (D1 AR-06) | Yes | | | | pending |
| C17 | A DupLESS-style key server placed in Cloudflare would hold the OPRF key and see every ID, which is worse than today. An asynchronous homelab-held OPRF relayed through the queue is feasible with an outbound-only homelab. It would remove the family secret from devices, but it delays dedup decisions to the homelab's pull cycle, needs a new primitive, and changes the settled "HMAC(family secret, content)". | S30 (not read) + inference | No (alternative) | | | | pending |
| C18 | Borg 1.x loses confidentiality with multiple clients sharing a repository (AES-CTR counter reservations, replayable by a malicious repo). Borg 2 uses per-invocation random session keys with counters from 0. Borg 2 also binds id, header and slot into the AEAD AAD. | S9, S10 | No | | | | pending |
| C19 | Tarsnap 1.0.28 (2011-01-18) fixed a "critical security bug" in chunk encryption; 1.0.29 (2011-02-07) added `tarsnap-keyregen`/`tarsnap-recrypt` for key rotation. The mechanism (nonce not incremented, 1.0.22–1.0.27) is from LWN and snippets only. | S13 (primary); S38 (secondary) | No | | | | pending |
| C20 | The 2025 CDC attacks recover keyed-chunker parameters from observed chunk sizes (restic cites 2025/532 and mitigated in 0.18.0; Borg wiki cites 2025/558 and notes that chunker fixes do not stop small-file size fingerprinting). Reliquary's cloud sees whole-file objects with no chunker secret. The attacks apply only if a chunking homelab engine's store is later exposed to an untrusted party (off-site phase, out of scope now). | S11, S14 (papers not read) | No | | | | pending |
| C21 | Malicious-server failures in deployed E2EE storage came mainly from unauthenticated key material and metadata relayed by the server: Hofmann–Truong (4 of 5 providers), MEGA (RSA key recovery through tampered key ciphertexts), Nextcloud (IV reuse; client misbehaviour on an empty metadata-key list). | S23–S25 (not read; snippets) | No (precedent) | | | | Secondary only until read |
| C22 | Hash-as-proof-of-possession broke Dropbox dedup (Dark Clouds, 2011) and motivated Proofs of Ownership. ADR-0001 §4 already says a dedup hit grants no read rights, and any future self-service restore returns only files the device uploaded and the homelab verified. | S27, S28 (not read); ADR-0001 | No | | | | pending (mapping high; paper details secondary) |
| C23 | Borg's attack model trusts the client and not the repository, and guarantees against the repository: no undetected modification or archive add/rename, no plaintext, no definite structure; DoS always possible. Reliquary's D1 SR-01 ("cloud = availability only") is the same model. | S9, S46 | No | | | | pending |
| C24 | Harvest-now-decrypt-later applies to every X25519 wrap that leaves the house: staged objects and records in R2, USB bundles, restore staging to device keys. It does not apply to HMAC dedup IDs or ChaCha20-Poly1305 payloads directly, only through the key wrap. Keep-forever retention maximises the exposure window. | S1, S7, S42 (not read) + inference | Yes | | | | pending |
| C25 | Vectors available for G2: `cctv-age` 0.2.0 includes hybrid (`mlkem768x25519`) cases, among them `hybrid_and_x25519`, `hybrid_low_order`, `hybrid_not_canonical_*` and `hybrid_currupted_enc_*`. It also covers x25519, stanza and stream cases such as `stream_no_final`, `stream_two_final_chunks` and `stream_trailing_garbage_*`. Wycheproof `testvectors_v1/` serves ed25519, hmac_sha256, hkdf_sha256, chacha20_poly1305, x25519 and mlkem_768 files. CCTV cannot test encryption end to end. | S5, S6 | Yes (G2) | | | | pending |
| C26 | Timing and per-device volume leak to any relay: restic's threat model lists sizes inferred from object timestamps and traffic, and Borg lists pack proximity. No cheap mitigation exists short of cover traffic. | S14, S9 | No | | | | pending |
| C27 | Object-identity binding precedent: Borg binds id and slot into the AEAD AAD; Kopia passes the content ID as AEAD associated data. age has no AAD, so Reliquary binds identity with the signed record's (dedup_id, sha256, size, header_mac), which the homelab verifies after decrypting (CE §9, §11). The binding is equivalent for integrity. Order and completeness still need SR-13. | S9, S16, S46 + inference | Yes | | | | pending |

## Findings

### 1. What age guarantees, and what it does not (C1–C7)

- **Guaranteed** (C1):
  - one file key per object;
  - a header MAC over every stanza;
  - chunk-level AEAD with a counter and final flag, so chunks cannot be reordered, dropped, truncated or extended without detection, *if* the reader enforces the final-chunk rule. CE §5.5 found that the Rust `StreamReader::seek` does not, and fixed Reliquary's own range reader.
- **Not guaranteed:**
  - who made the object (C2);
  - that the length is hidden (C7);
  - anything about the object's *meaning* (which device, which file, which sequence). The signed record supplies these (C27).
- **Key commitment** (C3): the header MAC makes the file key unique per header, so an object cannot show different plaintexts to the homelab identity and to a future recovery identity. This is the property the "invisible salamanders" literature asks for in multi-recipient settings. It rests on reasoning, not a spec statement, so skeptics should attack it. Reliquary's post-decrypt SHA-256 and HMAC checks are a second, independent guard.
- **Partitioning oracles** (S34): age mitigates them with exact stanza-body lengths. They matter only where a decryptor tries many keys or passwords against attacker-chosen ciphertexts. The homelab has one identity (two during a rotation), so the effect is negligible. It is still a reason never to put a password-derived stanza on staged objects.
- **Multi-recipient rules** (C4): these are binding constraints for OD-06 and OD-08, not preferences. The Go reference refuses to mix PQ and classical recipients.

### 2. Size, timing and volume leakage (C7–C10, C26; F3-S1)

- Exact size is a strong fingerprint for media. The corpus README's indicative P11 sample (not random) showed 95.1 % of photos with a unique exact size. F3-S1 re-measures this on the full file and on the owner library under H3 R3.
- **Padmé vs 64 KiB buckets vs none:**
  - Padmé reduces each size to one of 32 values per power-of-two range, at ≤ 3.1 % cost for files of 64 KiB or more (C8).
  - 64 KiB buckets are cheaper for large files but cost up to 31 % for 100 KB files. They also leave ≈ 20 distinct sizes per MB for photos, which is much finer than Padmé at that size.
  - Padmé dominates for a photo-heavy library.
- **Where padding goes:** zero bytes appended to the plaintext before age encryption. This is Borg's choice; with zeros, CE's byte-identical regeneration on resume still works, which random padding would break unless derived from a key. The dedup ID and SHA-256 stay over the *unpadded* content (Borg precedent, C9). The true size travels only inside the signed, encrypted record. The homelab truncates to it after verification.
- **Side effects:**
  - Stock `age -d` output then includes the padding, so the break-glass kit (BUD-RECOVERY, D2) must include a "truncate to size" step or tool.
  - Every cloud-visible size field must switch to the padded length (C10): the receipt, the present-check and the SR-24 declared size.
- **Residual after padding:**
  - set fingerprinting is still possible across a time window (an album uploaded together);
  - timing and volume leak;
  - ID equality across devices leaks.

  These stay under AR-05; restic and Borg accept the same leaks (C26).
- **Decision owner:** A2 (ADR-0007). F3 supplies the requirement and the PLAN rule: adopt padding if more than 50 % of sizes are unique and the cost is under 3 %.

### 3. The dedup oracle (C11–C14, C16; F3-S2)

- **Threat.** Any enrolled device holds the family secret (ADR-0001 §2). With ADR-0001 §4's global "which are missing?" answer, one compromised phone can run both Tahoe attacks against the whole family's library. Examples:
  - confirmation-of-a-file: "does anyone in the family have this leaked document?";
  - learn-the-remaining-information: "which of the 10^6 possible balance values is in Mum's bank statement?".
- **Why throttling alone fails** (C12). Legitimate seeding needs about 10^4–10^5 lookups per device per day. The Borg wiki's comfort that attackers "can not try faster than you do backup runs" does not carry over, because Reliquary's oracle is interactive.
- **What works: narrow the oracle, then audit it:**
  1. **Scope.** By default, "present" means *present from this person's devices* (per-person scope; the person mapping comes from enrollment, E7). Cross-person upload-skip is allowed only for objects above a size threshold T_x (videos, where bandwidth matters most and brute-forcing unknown fields is not the concern). Storage dedup across all users is unchanged: the homelab dedups by ID and SHA-256 whatever the cloud answered. The settled requirement "whole-file, across all users" is about storage, and it still holds. What changes is ADR-0001 §4 step 1's upload-skip semantics, which OD-04 is superseding anyway.
  2. **Record-first.** The Worker answers "present" for an ID only once it holds the device's signed, encrypted record for that ID. SR-06 already requires the record to be sent; this only changes the order. Every probe then leaves a non-repudiable, homelab-readable trail: a device-signed claim of possession for a file the device may not have.
  3. **Exact accounting and alerting.** A per-device Durable Object counts lookups, hits, records with no content that never received a receipt, and abandoned claims (SR-10). The homelab alerts the admin on anomalies, for example a hit ratio or lookup volume far above the device's history. The rate-limit binding is only a burst guard (C13).
- **What remains** (C16). A leaked secret plus the cloud's ID history can be tested offline. Mitigations:
  - SR-15 (the secret never passes Cloudflare in plaintext);
  - epoch rotation after any device compromise (A1, D2);
  - C1 minimises how long the cloud keeps IDs that no longer serve dedup.

  The rest stays in AR-06, reworded to "any holder of the secret, bounded by scope, record-first auditing and accounting".
- **F3-S2 hand-off:** the spike runner should simulate three configurations: (i) the global answer with SR-21 limits; (ii) global + record-first + DO accounting; (iii) per-person scope + record-first. Expected, to be confirmed or refuted by the spike: (i) fails the 30-day branch; (ii) and (iii) pass on the alert branch; (iii) also removes cross-person confirmation below T_x.

### 4. Dedup-ID construction, domain separation, one root secret, rotation (C15)

- F3 confirms A1's C9–C11 assessment against the matrix. The digest form's one extra exposure (testing from hash lists after a leak) is small next to C16, and its rotation benefit is the only practical remedy for C16.
- Use HKDF with versioned info labels (Kopia's purpose-string pattern, Tahoe's versioned tags) plus A1's kind byte and epoch.
- Derive the dedup key and any future per-person presence key from one family root through distinct HKDF labels.
- **Rotation caveat (new):**
  - When the homelab re-derives epoch e+1 IDs from its catalog and pushes a new index to the cloud, it must not reveal the old-to-new correspondence: no paired upload, no stable ordering, no shared size field.
  - Otherwise a leaked old secret plus the cloud history still identifies new-epoch objects.
  - Tahoe's lesson applies: a new epoch is a new dedup domain, so devices must re-query under the new epoch, and stale-epoch IDs must be rejected after a grace window (A1).

### 5. Malicious cloud: swap, replay, drop, withhold (C2, C21, C23, C27)

- D1 adopted Borg's and Tahoe's model: the cloud is trusted for availability only. The literature's failure classes map one to one onto D1's SRs (matrix below). This is what the Hofmann–Truong, MEGA and Nextcloud precedents would predict: every failure there involved the server relaying key material or metadata the client did not authenticate.
- Two items F3 adds:
  - **Downgrade and empty answers** (Nextcloud GHSA-jh3g). A device must treat an empty or missing receipt, trust-bundle field or presence list as "not safe", never as "nothing to do". It must never accept a recipient set or format version from the Worker (G2 tests NT-10, NT-11).
  - **Presigned-upload header signing** (Cure53/Ente, secondary). SR-09's "sign Content-Type, and length/MD5 if possible" is the same checklist item. C1-S1 decides what R2 enforces.

### 6. Incidents and their lessons (C18–C22)

| Incident | Lesson for Reliquary | Status |
|---|---|---|
| Tarsnap 2011 (CTR nonce not incremented after a refactor; fix plus rotation tools within 20 days) | Nonce and keystream invariants must be enforced by an API, not by care. A re-encryption and rotation path must exist *before* a bug ships. | CE's release rule sits in `gen_range`, and a mutation test failed as intended (CE R-1). G2 must keep mutation tests on it. The rotation/re-wrap path is open (D2). |
| Borg 1.x multi-client counter reuse | Never share nonce state across writers. Client-side state that the security depends on must not be rolled back. | Per-object random file keys (age) and hedged RNG (CE §5.2). Residual: the CE journal rolled back by an OS backup restore (R-1). Exclude it from backups; G2 test NT-06. |
| Valsorda 2017 restic review (informal, "not a professional audit") | An informal expert review is cheap and valuable, and it is not an audit. | Recommend an external review of the object format and protocol before Gate A (D4/G2). |
| Dropbox Dark Clouds 2011 / Proofs of Ownership 2011 | A hash is not proof of possession. | ADR-0001 §4 already: a hit grants no read rights. Keep this in A8's restore rules. |
| 2025 CDC attacks | Keyed chunkers leak their key through chunk sizes. Padding helps; chunker fixes do not stop small-file fingerprinting. | Whole-file objects in the cloud. Hand-off to A6 for any off-site copy of a chunking engine. |
| MEGA, Nextcloud, Hofmann–Truong | Authenticate every key and metadata item the server relays. | SR-02, SR-03, SR-14, SR-16. Secondary only. |

### 7. Post-quantum (C4–C6, C24)

- **For:**
  - keep-forever data;
  - ciphertext crosses Cloudflare and travels on USB sticks;
  - the object format is a one-way door (#2);
  - the Go reference ships the hybrid recipient natively (Go age ≥ 1.3.0, since 2025-12-27);
  - CCTV has hybrid vectors;
  - the cost is ≈ 1.5 KB more header per object. For 1–5 M objects that is ≈ 1.5–7.5 GB of extra transfer once: under 0.1 % of 2–10 TB (arithmetic).
- **Against:**
  - the KEM is specified by an IETF draft. age pins its bytes, so later IETF churn does not break existing files, but a future format revision could;
  - Rust has no native support in the `age` crate, so the CE encoder must add HPKE with MLKEM768-X25519 and prove byte compatibility against CCTV `hybrid*` vectors;
  - recipient strings are about 2,000 characters. This does not matter for the QR, because the trust bundle is pinned by digest (CE §10);
  - it couples to OD-08 (C4).
- **Signatures** (Ed25519 device and receipt keys) face no harvest-now threat: forgery needs a quantum computer at signing time. They can migrate later behind SR-02's signed rotation.

### Alternatives compared

| Topic | Option | Fit with settled requirements | Pros | Cons | Evidence |
|---|---|---|---|---|---|
| Dedup ID | A1: HMAC(K_e, kind ‖ SHA-256(m)), HKDF epoch keys | Deviates in wording from "HMAC(family secret, content)" (DR-A1-1) | Rotation from cache; one hash pass | Hash-list testing after a leak | C15 |
| | HMAC(K, m) as settled | Exact | Needs the file bytes to test | Rotation needs a full re-read of 2–10 TB, so is impractical | C15 |
| | Keyed digest SHA-256(m ‖ k) (PBS) | Deviates | Simple | Ad hoc; not a standard MAC | S15 |
| | Server-aided MLE, key server in Cloudflare | Conflicts with "cloud sees only opaque IDs" in spirit | Rate-limited key server | Cloud holds the OPRF key and sees IDs, which is worse | C17 |
| | Homelab-aided async OPRF via the queue | Changes settled text (secret off devices) | Removes AR-06's device leg | Latency, new primitive, USB offline IDs harder | C17 |
| | Per-user dedup only (no cross-user) | Conflicts with CLAUDE.md dedup across users | No cross-user oracle | Loses storage dedup | CLAUDE.md |
| Presence answer | Global (ADR-0001 §4) + rate limits | As written | Maximum bandwidth saving | Fails F3-S2's 30-day branch | C12, C13 |
| | **Per-person scope + cross-person above T_x + record-first + DO accounting** | Storage dedup unchanged; changes §4 skip semantics (OD-04) | Oracle narrowed and audited | Some duplicate uploads of shared small files (cost not measured) | C14 |
| Padding | None | As written | Zero cost | Exact size fingerprint (AR-05) | C7 |
| | **Padmé** (zeros, before age; IDs over unpadded content) | Fits | ≤ 3.1 % for ≥ 64 KiB; deployed in Borg and Tarsnap | Break-glass must truncate; cloud-visible size fields must change | C8–C10 |
| | 64 KiB buckets | Fits | Aligns with age chunks | Up to 31 % on small files; finer leakage for photos | C8 |
| Recipient | X25519 only | Fits ADR-0001 "e.g. X25519 / age" | Smallest header; Rust support | Harvest now, decrypt later on keep-forever data | C24 |
| | **mlkem768x25519 only (incl. the recovery recipient)** | Fits | PQ; stock `age -d` ≥ 1.3.0 | ~1.6 KB/object; the Rust encoder must implement it | C4–C6 |
| | Mixed PQ + classical recovery | Violates the age SHOULD NOT; Go refuses | — | Loses PQ | C4 |

### Similar work and lessons (annotated bibliography, one-line lessons)

| # | Work | One-line lesson for Reliquary | Source |
|---|---|---|---|
| B1 | age v1 spec (C2SP) | Header MAC and STREAM give integrity and truncation detection, but no sender authentication and no length hiding. | S1 |
| B2 | age v1.3 PQ recipients and README | Hybrid PQ is available off the shelf; do not mix with classical recipients; `age-inspect` shows sizes and PQ use. | S2, S3 |
| B3 | Rust `age` 0.12.1 | No native hybrid recipient: a Rust core must implement it or use a plugin. | S4 |
| B4 | CCTV age vectors | Use them for decrypt-direction negative tests, including hybrid and stream edge cases. | S5 |
| B5 | Wycheproof | Primitive-level negative vectors (Ed25519, HMAC, HKDF, ChaCha20-Poly1305, X25519, ML-KEM). | S6 |
| B6 | X-Wing draft | The hybrid KEM combiner under age's PQ stanza is still a draft; pin versions and test vectors. | S7 |
| B7 | Tahoe-LAFS convergence secret | Every secret holder can confirm files and brute-force the remaining fields; rotation means a new dedup domain. | S8 |
| B8 | Borg 2 security internals | Trust the client, not the repository; MAC IDs, not plain hashes; bind the ID into authenticated data; session keys instead of shared counters. | S9 |
| B9 | Borg 1.4 security internals | Shared nonce state across clients destroys confidentiality. | S10 |
| B10 | Borg wiki, CDC 2025 | Padding after the ID computation does not hurt dedup; small-file size fingerprinting survives chunker fixes. | S11 |
| B11 | Borg `obfuscate` / Padmé | A production precedent for opt-in Padmé at bounded cost. | S12 |
| B12 | Tarsnap NEWS | A crypto bug needs a ready re-encryption and rotation path; PADME adopted in 2025. | S13 |
| B13 | restic threat model | Storage readers infer sizes from timestamps; a compromised host can game retention; a leaked key means re-encrypting everything. | S14 |
| B14 | Proxmox Backup Server | A keyed digest leaves the server unable to verify encrypted content: verification must happen where the key lives (the homelab). | S15 |
| B15 | Kopia | HKDF with purpose labels from one master key; content ID as AEAD associated data. | S16 |
| B16 | Duplicacy | "MAC over a MAC" IDs are deployed practice; unencrypted mode with a fixed key makes IDs public. | S17 |
| B17 | Syncthing untrusted devices | Minimum-size padding and deterministic metadata encryption toward an untrusted peer. | S18 |
| B18 | Padmé / PURBs (reference code) | O(log log M) length leakage; overhead ≤ 3.1 % in the photo and video range. | S19, S20 |
| B19 | Cloudflare rate-limit binding | A 10/60 s, per-location, eventually consistent burst guard, not an accounting system. | S21 |
| B20 | Durable Objects | Single-threaded, strongly consistent per-key state for exact per-device quotas. | S22 |
| B21 | Hofmann & Truong, CCS 2024 | Four of five E2EE clouds were broken by a malicious server through unauthenticated key material and metadata. | S23 (secondary) |
| B22 | MEGA (S&P 2023; Caveat Implementor) | Patching with sanity checks instead of authenticating key ciphertexts invites follow-up attacks. | S24 (secondary) |
| B23 | Nextcloud E2EE (EuroS&P 2024) | Test empty and absent server answers, and IV reuse. | S25 (secondary) |
| B24 | Harnik–Pinkas–Shulman-Peleg 2010 | Cross-user client-side dedup is itself a side channel. | S26 (secondary) |
| B25 | Proofs of Ownership 2011 / Dark Clouds 2011 | A hash is not proof of possession. | S27, S28 (secondary) |
| B26 | Message-locked encryption 2013 | Deterministic, key-derived-from-message schemes are brute-forceable over predictable messages. | S29 (secondary) |
| B27 | DupLESS 2013 | Rate-limited server-aided keys resist brute force only if the key server is trusted and online. | S30 (secondary) |
| B28 | Armknecht et al. 2017 | The leakage/efficiency trade-off of the dedup oracle is inherent; scope it. | S31 (secondary) |
| B29 | Liu–Asokan–Pinkas 2015 | Cross-user dedup without a key server is possible via PAKE, at protocol complexity Reliquary does not need. | S32 (secondary) |
| B30 | Invisible salamanders; partitioning oracles; key commitment | Non-committing AEADs need an explicit commitment in multi-key settings; age's header MAC appears to supply it. | S33–S35 (secondary) |
| B31 | 2025 CDC papers (2025/558, 2025/532) | Keyed chunker secrets leak; whole-file objects avoid this class in the cloud. | S36, S37 (secondary) |
| B32 | Tarsnap 2011 post; Valsorda 2017 | Invariants in APIs; informal reviews are useful but are not audits. | S38, S39 (secondary) |
| B33 | WhatsApp E2EE backups; Apple ADP | Key-custody analogues: HSM guess limits vs a user-held key; mandatory recovery contact or key. Inputs for D2/OD-08. | S44, S45 (secondary) |

### Tools and libraries

| Name | Purpose | Licence | Maturity | Source |
|---|---|---|---|---|
| Go `filippo.io/age` | Homelab decrypt (hybrid PQ), reference | BSD-3-Clause (not re-checked here) | v1.3.2, 2026-08-29 | S3 |
| Rust `age` | Existing crate (no hybrid) | MIT/Apache-2.0 (not re-checked here) | 0.12.1 | S4 |
| RustCrypto `ml-kem`, `x-wing`, `hpke` | Building the hybrid stanza in the Rust encoder | not checked | 0.3.2 (2026-05-10), 0.1.0 (2026-07-09, "draft 06"), 0.14.1 (2026-09-06) per crates.io | crates.io API |
| `cctv-age` / `c2sp.org/CCTV/age` | age negative vectors, including hybrid | README: "The license allows this without attribution" | 0.2.0, 2025-12-08 | S5 |
| Wycheproof | Primitive negative vectors | not re-checked | main | S6 |
| Padmé: `dedis/purb` `padding.go`; Rust `padme-padding` 0.1.1 (scout) | Reference for F3-S1 and A2 | per repo (not re-checked) | 2020 crate; repo HEAD | S19 |

## Attack → mitigation matrix

A1, A2, A3 and D1 must satisfy this matrix (PLAN F3). Status: **Mitigated** (by the named SR or design element; "planned" where it is not built yet), **Accepted** (under the trust model, with an AR), or **Open**. SR, AR and T IDs are D1's. F3-S3 (red team) checks this table.

| ID | Attack | Attacker | Mitigation | Status | Owner |
|---|---|---|---|---|---|
| M-01 | Cloud tests known files by plain hash | Cloud | Keyed IDs (ADR-0001 §2); no plain SHA-256 in the cloud (SR-26) | Mitigated | A1, C1 |
| M-02 | Confirmation-of-a-file through the presence answer | Compromised device (holds the secret) | Per-person scope + cross-person only above T_x + record-first + DO accounting and admin alert (C14); SR-21 | **Open** until F3-S2 and OD-04 addition; then Accepted residual (AR-06) | A3, C1 |
| M-03 | Learn-the-remaining-information via the presence answer (small documents) | Compromised device | As M-02; scope removes the cross-person case below T_x | **Open** (as M-02) | A3, C1 |
| M-04 | Leaked secret + cloud ID history → offline testing of every historical ID | Device + cloud | SR-15; epoch rotation (A1, D2); short cloud ID retention; unlinkable re-keying (M-14) | Accepted (AR-06), reduced | A1, D2, C1 |
| M-05 | Exact-size fingerprinting of objects | Cloud, USB finder | Padmé before age; padded length in every cloud-visible field (receipt, present-check, SR-24) | **Open** (DR-F3-1; A2 decides after F3-S1) | A2, A3, C1 |
| M-06 | Timing, per-device volume, ID equality across devices, IPs | Cloud | None cheap | Accepted (AR-05) | D6 |
| M-07 | Forged object or record in a device's name (age has no sender auth) | Cloud, other device | SR-03 device signatures inside the encryption; SR-14 device-key authenticity | Mitigated (SR-14 **open**: D3/OD-05) | A2, D3 |
| M-08 | Object/record swap, cross-context substitution | Cloud | Record binds (dedup_id, sha256, size, header_mac); homelab verifies after decrypt (SR-04); `type` fields; metadata keys without dedup_id | Mitigated (CE tests `commit:*`) | A2, A3 |
| M-09 | Replay, suppression or reordering of records | Cloud | Idempotent ingest (SR-12); per-device sequence or checkpoint (SR-13); signed heartbeat (SR-18) | Mitigated (planned; SR-13 design **open**) | A3 |
| M-10 | Drop, withhold, fake "committed" | Cloud | Receipts are the only "safe" (SR-05); receipt timeout and re-upload (SR-06); heartbeat (SR-18) | Mitigated for integrity; availability Accepted (AR-04) | A3, E3 |
| M-11 | Key substitution: homelab recipient, receipt key, device keys | Cloud | Pinned trust bundle (SR-02); SR-14; SR-16 for restores | Mitigated except device keys (**open**, D3) | D3, A8 |
| M-12 | Downgrade: recipient type, format version, empty lists | Cloud | Fixed recipient set from the pinned bundle; no Worker-supplied recipients or versions; an empty or absent answer means "not safe" | Mitigated (planned; G2 NT-10/11) | A2, B6, G2 |
| M-13 | Two recipients see different plaintexts (key commitment) | Malicious encryptor | Header MAC binds one file key (C3); homelab verifies SHA-256 and HMAC | Mitigated (C3 is inference: skeptics) | A2 |
| M-14 | Linking old and new epoch IDs during rotation | Cloud + old secret | Unordered, unpaired re-key push; no stable size field | **Open** (A1/D2 procedure) | A1, D2 |
| M-15 | Harvest-now-decrypt-later on X25519 wraps | Future quantum adversary recording R2 or USB | mlkem768x25519 recipients only (OD-06) | **Open** (OD-06) | A2 |
| M-16 | Mixed PQ + classical, or scrypt recovery stanza, voiding PQ | Design error | Recovery recipient is a PQ public key (OD-08); CCTV `hybrid_and_x25519` test | **Open** (OD-08) | D2, A2 |
| M-17 | Nonce or keystream reuse on resume (Tarsnap class) | Bug | CE release rule in `gen_range`; mutation tests | Mitigated (CE); production review required | A2, G2 |
| M-18 | Nonce state rollback (Borg class): journal restored from an OS backup | Bug or ops | Exclude state from backups; hedged RNG; per-upload keys deleted on completion | Mitigated (planned; G2 NT-06) | B6, A2 |
| M-19 | Hash as proof of possession (Dark Clouds) | Device | A hit grants no read rights (ADR-0001 §4); restore only of the device's own verified uploads | Mitigated | A8 |
| M-20 | CDC parameter recovery (2025) | Store observer | Whole-file objects in the cloud; applies to any future off-site copy of a chunking engine | Mitigated for v1; hand-off A6 (future) | A6 |
| M-21 | Truncated or extended object served on restore or range read | Cloud | Final-chunk check before serving (CE §5.5); SR-16 restore manifest | Mitigated | A8 |
| M-22 | Crafted headers or records against homelab parsers | Cloud, device | SR-22 strict parsing; CCTV `stanza_*`/`header*` vectors; fuzzing | Mitigated (planned; D4-S5, G2) | A2, D4 |
| M-23 | Partitioning oracle against homelab identities | Cloud | Exact body-length checks (age); one identity; no password stanzas on staged objects | Accepted (negligible) | A2 |
| M-24 | Garbage or oversized uploads, claim squatting | Device | SR-10, SR-24, BUD-ABUSE | Mitigated (cost bounded) | C1, C2 |
| M-25 | Leaked-secret rotation is impractical (full re-read) | Ops | A1 digest construction (C15) | Mitigated if DR-A1-1 is accepted | A1 |

## Negative tests and vectors required of G2

| ID | Test | Vectors or method | Guards |
|---|---|---|---|
| NT-01 | Homelab decryptor and Reliquary range reader pass all `cctv-age` decrypt vectors (skip armor and scrypt only if unused), including `stream_no_final*`, `stream_two_final_chunks*`, `stream_trailing_garbage_*`, `stream_last_chunk_empty` and `x25519_low_order` | CCTV (S5) | M-21, M-22 |
| NT-02 | If OD-06 is yes: the Rust encoder's hybrid stanza decrypts with Go age ≥ 1.3.0, and the reader passes all `hybrid*` vectors, including `hybrid_and_x25519` (mixing rejected on encrypt) and `hybrid_low_order` | CCTV + cross-implementation round trip | M-15, M-16 |
| NT-03 | Header and STREAM round-trip on every non-failure vector; STREAM re-encrypt with the vector file key reproduces the bytes | CCTV | CE encoder correctness |
| NT-04 | Primitive vectors: HMAC-SHA256, HKDF-SHA256, ChaCha20-Poly1305, X25519 (all-zero shared secret aborts), Ed25519 (reject non-canonical and malleable signatures), ML-KEM-768 | Wycheproof `testvectors_v1/` (S6) | M-07, M-13 |
| NT-05 | Keystream reuse: modify the source between parts on resume; the release rule must abort; mutation-kill tests stay in CI | CE harness | M-17 |
| NT-06 | Rolled-back journal (older copy restored) must not re-release chunks under the old key | CE harness | M-18 |
| NT-07 | Object/record swap, cross-device record, wrong epoch, wrong size and padding length mismatch all rejected at ingest | Synthetic | M-08, M-05 |
| NT-08 | Replay of an old record, gap in the sequence, duplicate event: idempotent, with gaps flagged | Synthetic | M-09 |
| NT-09 | Forged, tampered or wrong-key receipt; receipt for another device's record | Synthetic | M-10 |
| NT-10 | Worker returns an empty or absent receipt list, presence list or trust-bundle field: the device shows "not safe" | Synthetic Worker (Nextcloud lesson) | M-12 |
| NT-11 | Worker offers a different recipient, extra stanza or version string: the device refuses | Synthetic | M-11, M-12 |
| NT-12 | Presence probing: a "present" answer only after a record; DO counters exact under concurrency; alert fires on the F3-S2 profile | F3-S2 harness, promoted to CI | M-02, M-03 |
| NT-13 | Padding: padded length ∈ Padmé(L); dedup ID and SHA-256 over unpadded content; the homelab truncates by the signed size; break-glass truncation documented | Unit + kit test | M-05 |
| NT-14 | Dedup-ID vectors across epochs and kinds (A1-S3) plus an unlinkable re-key export | A1-S3 vectors | M-14, M-25 |

## Spikes

*Placeholder: the spike runner fills this section. The rows below restate the PLAN §2.0 template fields.*

| Spike | Hypothesis | Pass → / fail → (decision) | Exec tag | Budget IDs | Data class | Status | Result |
|---|---|---|---|---|---|---|---|
| F3-S1 Size fingerprinting | More than 50 % of files have a unique exact size today; Padmé cuts this sharply at under 3 % storage cost | Pass → adopt Padmé in object v1 (DR-F3-1, ADR-0007); fail → record accepted risk under AR-05 | CT (public); homelab kit for the owner library | none (storage cost only; BUD-CLOUD indirectly) | `PUB → results`; owner part `FAM → AGG` (H3 R3: never the size list) | Running (spike runner) | pending |
| F3-S2 Dedup-oracle simulation | A compromised device probing 10k candidates is either slowed past 30 days or alerted | Pass → the presence-query design in DR-F3-2; fail → narrow scope further or accept AR-06 explicitly | CT (emulated; not real Cloudflare) | BUD-HASH (seeding rate), BUD-ABUSE | `SYN → results` | Running (spike runner) | pending |
| F3-S3 Red team vs ADR-0001 + matrix | Every attack maps to a mitigation or an accepted risk | Pass → the matrix feeds ADR-0007/0009; fail → new SRs or ARs | CT | — | `SYN → results` | Running (spike runner) | pending |

## Conflicts with settled text

None is resolved here.

1. **ADR-0001 §4 step 1** ("returns the missing ones"): the recommended scoped, record-first presence answer changes the upload-skip semantics. Storage dedup across all users (CLAUDE.md) is unchanged. → Addition to OD-04 (DR-F3-2).
2. **ADR-0001 §2** "the cloud cannot test for known files": already being reworded under OD-04/D-6. F3 adds the offline-history case (C16) to AR-06.
3. **CLAUDE.md / ADR-0001 "HMAC(family secret, content)"**: A1's digest construction (DR-A1-1) is supported by F3. The homelab-aided OPRF alternative (C17) would change this settled line and is **not** recommended for v1.
4. **ADR-0001 §2 "e.g. X25519 / age"**: not a conflict ("e.g."), but OD-06 = yes means objects are no longer X25519. No superseding text needed beyond ADR-0007.

## Open questions

1. F3-S1/S2/S3 results (spike runner, this wave).
2. The value of T_x (cross-person skip threshold) and the bandwidth cost of per-person scope. This needs the share of cross-person duplicates in real libraries: E1 census or A9, as a count only. **A3 with E1, Wave 2.**
3. Wire compatibility of RustCrypto `x-wing` / `hpke` with age's `mlkem768x25519` (draft-ietf-hpke-pq-03). **A2 spike against CCTV `hybrid*` vectors before Gate A.**
4. Primary text of the blocked papers (S20, S23–S37) and of NIST IR 8547: the claims resting on them stay *secondary only*. **H1 (source access route).**
5. Cryptomator, Tresorit and Ente/Cure53 audit reports as checklists: not reached. **F3 follow-up or D4.**
6. The key-commitment inference (C3) should get a primary statement (the age authors or a C2SP issue). The age commit 2194f69 was seen only through the scout's search result. **Skeptic 2.**
7. How long the cloud keeps committed IDs vs the cross-person hit rate (M-04). **C1 with A3.**

## Recommendation

1. **Adopt A1's dedup-ID construction.** F3 finds no security reason against it, and rotation feasibility is a security gain (C15). Add the unlinkable re-key rule (M-14).
2. **Narrow and audit the presence oracle** (DR-F3-2):
   - per-person scope by default;
   - cross-person upload-skip only above T_x;
   - record-first answers;
   - exact per-device accounting in a Durable Object with admin alerts;
   - the rate-limit binding only as a burst guard.

   This is the one change that closes M-02/M-03 without touching storage dedup.
3. **Adopt Padmé in object format v1 if F3-S1 passes** (DR-F3-1): zero padding before age, IDs over unpadded content, padded length in every cloud-visible field, truncation step in the break-glass kit.
4. **OD-06: yes, `mlkem768x25519` only, from the first real ingest.** OD-08 must choose a PQ recovery recipient, not a passphrase stanza (C4).
5. **Give G2 the NT-01…NT-14 list**, with CCTV and Wycheproof as mandatory vector sources.
6. **Commission an informal external review** of the object format and protocol before Gate A (the Valsorda-style lesson). It is cheap, and it is explicitly not an audit.

What would change this:

- if F3-S2 shows that global answers plus DO accounting already alert reliably at acceptable false-positive rates, per-person scope becomes optional;
- if F3-S1 shows under 50 % unique sizes on the owner library, padding becomes an accepted risk;
- if the Rust hybrid stanza cannot be made byte-compatible by Gate A, the choice is between OD-06 = "PQ at v1.1 with re-wrap" and a Go/plugin path on devices.

## Decision requests

### OD-06: Post-quantum recipients from day one
- **Needed by:** Gate A.
- **Evidence:** this note §7, C4–C6, C24; CE D-2.
- **Options:**

  | Option | What it means for the family | Cost (money and owner time) | Reversibility | Risks |
  |---|---|---|---|---|
  | A. `mlkem768x25519` only (homelab and recovery keys PQ) | Nothing visible | ≈ 1.6 KB per object; A2 build effort; homelab needs Go age ≥ 1.3.0 | One-way door #2 | Draft KEM; Rust implementation work |
  | B. X25519 now, PQ later | Nothing visible | None now | Old staged ciphertext stays harvestable forever | Harvest now, decrypt later on keep-forever data |
  | C. Both stanzas on each object | — | — | — | Violates the age SHOULD NOT; Go refuses; no PQ benefit |

- **Recommendation:** A. The data is kept forever and passes through a third party and USB sticks. The cost is under 0.1 % of transfer, and the stock homelab tool already supports it.
- **Touches settled text:** none (ADR-0001 says "e.g. X25519").
- **If no decision by the deadline:** assume A for the skeleton; Gate A is blocked on OD-08 coupling.

### OD-08 (addition): the recovery recipient must be PQ if OD-06 = A
- **Needed by:** Gate A. **Evidence:** C4.
- **Options:** a PQ recovery key held offline (paper or hardware, k-of-n via D2), or no per-object recovery stanza (recovery by escrow of the homelab identity instead). An scrypt passphrase stanza is **not** an option.
- **Recommendation:** D2 chooses between the two valid options. F3 only rules out the invalid ones.
- **If no decision by the deadline:** a single homelab PQ identity with D2's escrow.

### DR-F3-1 (new, H1 to number): size padding in object format v1
- **Needed by:** Gate A (the object format is one-way door #2).
- **Evidence:** §2, C7–C10; F3-S1.
- **Options:**

  | Option | What it means for the family | Cost | Reversibility | Risks |
  |---|---|---|---|---|
  | A. No padding | Nothing visible | 0 | Can be added later for new objects only; past uploads stay fingerprintable | AR-05 includes exact sizes |
  | B. Padmé (zeros, before age; padded length in all cloud-visible fields) | Nothing visible, except break-glass needs a truncate step | ≤ 3.1 % transfer for ≥ 64 KiB files; homelab stores plaintext at its own posture (A6) | Format version | Kit complexity |
  | C. 64 KiB buckets | As B | Up to 31 % on small files | Format version | Finer leakage |

- **Recommendation:** B if F3-S1 passes; otherwise A with AR-05 explicitly including sizes.
- **Touches settled text:** none.
- **If no decision by the deadline:** A for the skeleton; the field layout still reserves the padded length.

### DR-F3-2 (new, H1 to number; addition to OD-04): presence-query semantics
- **Needed by:** Wave 1 exit, together with OD-04.
- **Evidence:** §3, C11–C14; F3-S2.
- **Options:**

  | Option | What it means for the family | Cost | Reversibility | Risks |
  |---|---|---|---|---|
  | A. Global answers + rate limits (ADR-0001 §4 + SR-21) | Fastest seeding of shared files | Lowest | Easy | A compromised phone can probe the whole family quickly (C12) |
  | B. A + record-first + DO accounting and alert | Same | Small (one DO per device) | Easy | Probing detected, not prevented |
  | C. B + per-person scope; cross-person skip only above T_x | Shared small files may upload twice (storage still deduped at home) | Some extra upload bandwidth (not measured) | Easy (a Worker rule) | T_x tuning |

- **Recommendation:** C (B at minimum). It is the only option in which a stolen phone cannot quietly test other family members' documents.
- **Touches settled text:** ADR-0001 §4 step 1 (via OD-04's superseding ADR-0009/0010).
- **If no decision by the deadline:** B for the skeleton.

### OD-17 (addition)
- AR-05 should list exact sizes only if DR-F3-1 = A.
- AR-06 is reworded to cover offline testing of the cloud's ID history after a secret leak (C16), bounded by rotation.
- New accepted item: partitioning oracles negligible (M-23).

## Hand-offs

| To | What | Why |
|---|---|---|
| A1 | C15 supports DR-A1-1; the unlinkable re-key rule (M-14); NT-14 | ADR-0006 |
| A2 | OD-06 = PQ only; the hybrid stanza in the Rust encoder plus the CCTV `hybrid*` spike; Padmé layout and padded-length field (DR-F3-1); general multi-stanza header parser (CE R-7) | ADR-0007, one-way door #2 |
| A3 / C1 | DR-F3-2 (scope, record-first, DO accounting, T_x); padded size in receipts, present-check and SR-24; cloud ID retention (M-04) | ADR-0009, ADR-0010 |
| D1 | Matrix M-01…M-25 to reconcile with T-01…T-20; AR-05/AR-06 wording | Threat register |
| D2 | OD-08 PQ recovery constraint; rotation re-wrap path (Tarsnap lesson); break-glass truncation | ADR-0008 |
| G2 | NT-01…NT-14; CCTV and Wycheproof as required sources | ADR-0035 |
| A6 | CDC lesson for any future off-site copy of a chunking engine | ADR-0012 |
| E1 / A9 | Count of cross-person duplicate files (counts only) for T_x | DR-F3-2 cost |
| H1 | Blocked sources list (Method); DR-F3-1/2 numbering; OD-06 → Ready; OD-08 coupling | Registries |
