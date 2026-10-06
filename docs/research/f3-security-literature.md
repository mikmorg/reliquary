# F3. Security literature on E2EE storage and deduplication

- **Workstream:** F3 (see `docs/research/PLAN.md`, section "F3.")
- **Status:** Final for Wave 1 (skeptic-reviewed by three lenses: sources, logic, adversary; claim tally computed in code). The attack matrix and the G2 negative-test list in this note are F3's owned normative artifacts and are **Draft**.
- **Date:** 2026-09-29 (last updated 2026-10-06, second synthesis pass)
- **Feeds:** OD-04 (presence-query semantics, as the addition DR-F3-2), OD-06 (PQ: evidence for A2's DR-A2-1), OD-08 (recovery recipient: a constraint for D2), OD-17 (AR-05/AR-06 wording and new accepted-risk candidates); ADR-0006 (A1), ADR-0007 (A2), ADR-0009 (A3), ADR-0010 (C1), ADR-0021 (B6), ADR-0028 (A8), ADR-0035 (G2 negative tests); one-way doors #1 (dedup-ID construction), #2 (object envelope, PQ, sender authentication) and the receipt-format door (A3).
- **ADR ownership:** F3 owns no ADR (PLAN §2.1). It owns the bibliography, the attack → mitigation matrix and the negative tests required of G2, all in this note.
- **Depends on:** T2 (`fact-check-adr-0001-0002.md`); D1 (`d1-threat-model.md`, register `docs/security/threat-model.md`, SR-01…SR-31, AR-01…AR-09, T-01…T-26); T1 spike 2 (`content-encryption-format.md`, "CE"); A1 (`a1-content-identity.md`); A2 (`a2-object-envelope.md`); D2 (`d2-key-hierarchy-custody-recovery.md`); spikes F3-S1, F3-S2, F3-S3.
- **Traceability rows advanced:** R-21 (opaque IDs; the F3 matrix is named as evidence), R-19/R-20 (encryption, devices cannot read), R-44 (cloud never sees plaintext).

## Summary

ADR-0001 plus D1's requirements cover the malicious-cloud attack classes in the literature (swap, replay, drop, withhold, key substitution, downgrade). **They do not yet make the design sound.** The red-team spike (F3-S3) found 14 attacks with no coverage at all. This note adds a matrix row for every one of them, but most of those rows are still **Open**. The most serious is RT-30: tampering with the device's hash cache can make a file show as "safe" when it was never uploaded. That is silent loss, so it is P0.

The "already have it" presence answer is the largest leak. The dedup-oracle simulation (F3-S2, run in an emulator, not on real Cloudflare) found three things:

- Per-device rate limits fail the PLAN test.
- Exact per-device accounting with auto-suspend also fails. It is evaded by an attacker who uploads its misses.
- No rate limit stops a 20-candidate "does anyone have this file?" check, which finishes in the first hour.

Only one configuration passed: never answering "present" for another person's files below a size threshold T_x. It passes *by construction*, and only if no other channel reveals prior presence: receipt timing (which broke it in the simulation), the staging-key namespace (M-49), and enrollment into another person's account (M-50). It also leaves same-person probing exposed. F3 therefore recommends **C at minimum: per-person scope below T_x**. If the bandwidth cost is acceptable, it prefers **D: no upload-skip below T_x for anyone**. Both need four supporting rules (M-27 to M-30). Either one narrows how the settled "dedup across all users" works at upload time, so the owner must decide. Per-person dedup keys (option F) would close the cross-person case cryptographically, but they change the settled ID construction.

The other recommendations:

- **Padmé padding:** adopt it. It costs about 1.1 % byte-weighted on public corpora. This is provisional until the owner-library leg of F3-S1 runs (pass at per-device scale; mixed at family scale).
- **Post-quantum:** F3 supports A2's "post-quantum from day one" recommendation. Corrected cost: about 0.13–1.2 % per file, depending on the stanza layout and the file mix. The scope must extend to device keys. This is conditional on a working Rust X-Wing encoder and decoder (A2-S3).
- **Dedup-ID construction:** no F3 verdict. The comparison claim (C15) is contested, so F3 passes trade-offs to A1.

**Confidence:** high on the primary-source facts; medium on the protocol conclusions (emulated simulation, hand-set thresholds); low on anything that rests on the blocked papers.

## Questions

| # | Question (PLAN F3) | Short answer | Confidence |
|---|---|---|---|
| 1 | What leaks even with HMAC IDs? | (a) **Exact plaintext size**: age has no padding (C7), and receipts, the present-check and the SR-24 declared size all carry it (C10, verified). (b) **Timing and per-device volume**, which is inherent to any relay (C26). (c) **ID equality across devices.** (d) **Recipient type and payload size**, readable with `age-inspect`. (e) **The presence oracle**: any compromised device can use it (C11, verified). F3-S2 shows it can be used fast (§3). (f) **New:** a "present" answer relays another device's receipt, so it also reveals *which device* holds the file, and when (C29, M-27). | High (a–c, e–f); Medium (oracle bounds, emulated) |
| 2 | HMAC over content vs HMAC over SHA-256; domain separation; one root secret; rotation | Before a leak, both are equally opaque to the cloud. This rests on standard hash-then-PRF reasoning, not on a read primary source (C15, **contested**). After a leak, the digest form also allows testing from SHA-256 lists, *including the device's own hash cache* (M-32). Both forms can rotate. The digest form is cheaper on devices. The content form can re-derive IDs at the homelab during the monthly fixity read (BUD-AUDIT). **This is input to A1's DR-A1-1, not an F3 verdict.** Rule F3 adds: re-keying must not hand the cloud an old-to-new mapping, and that is probably not fully achievable (M-14). | Medium |
| 3 | Stolen dedup secret plus a curious cloud | Together they can test **every** ID the cloud ever saw, offline and without any rate limit (MLE's weakness over predictable messages; C16). There is no forward secrecy. Mitigations: SR-15; epoch rotation; short cloud-side ID retention; PQ protection for any channel that carries the secret (M-40). The residual goes to AR-06. A DupLESS-style key server in Cloudflare would make this worse. A homelab-held OPRF would change settled text (C17). | Medium-high (paper texts secondary) |
| 4 | Malicious-cloud classes; binding metadata to object, device and sequence | The published failures came from unauthenticated material relayed by the server: key material and metadata, but also unauthenticated content encryption modes and protocol downgrade (C21, **contested**: its sources are secondary). They map onto D1's SR-02/03/04/05/13/14/16/22. age gives no sender authentication (C2, verified), so provenance comes from the device-signed record. Still open: SR-13 sequencing and SR-14 device-key admission. | Medium |
| 5 | Key commitment and multi-recipient issues; what age's header MAC and STREAM guarantee | One header verifies under at most one file key, up to a SHA-256 collision (about 2^128 work). This is a reduction argument, not a spec statement (C3, **secondary only**). It assumes every reader checks the header MAC before using the file key (NT-16). STREAM detects reordering, truncation and extension if readers enforce the final-chunk rule. **Binding rules:** do not mix PQ and classical stanzas; an scrypt stanza must be alone (C4, verified). | High (spec facts); Medium (commitment) |
| 6 | Incidents | Tarsnap 2011, Borg multi-client counter reuse, Valsorda's 2017 restic review, Dark Clouds / Proofs of Ownership, the 2025 CDC attacks: all mapped (M-17…M-22). | High for vendor-primary facts; secondary for paper details |
| 7 | PQ evidence; reusable audit checklists | The harvest-now-decrypt-later argument holds for every X25519 wrap that leaves the house. That includes the device keys used for restores and for sealing the dedup secret (C24, **contested** as originally scoped; rescoped here). Go age ≥ 1.3.0 ships the hybrid recipient (C5, verified). Corrected cost: +1,459 B per age object for one stanza, i.e. about 0.13–1.2 % of transfer depending on layout and mix (C28). Checklists: Cure53/Ente is secondary only; Cryptomator and Tresorit were not reached. | Medium (PQ); Low (checklists) |
| 8 | (new) Can rate limits alone pass F3-S2? | **No, for uniform caps** (measured in emulation). Any uniform cap that lets a first seed finish in under about 170 days lets a 10k probe finish in under 30 days (F3-S2 C1s). Phase-based or credit-based budgets were **not simulated** (C12 is **contested** as originally worded). No budget of 20 or more lookups stops the 20-candidate confirmation (F3-S2). | Medium |
| 9 | (new) Does padding survive the current CE and D1 designs? | Not as written. Every cloud-visible size field must carry the padded length: receipt, present-check, SR-24, multipart layout (C10, verified; RT-15). The true length should be framed inside the encrypted payload, so that the object alone is enough for a break-glass restore (M-41). | High |
| 10 | (new) Does F3-S3 pass? | **No.** 65 attacks: 36 mapped, 8 mapped-open, 7 D1-only, 14 unmapped (F3-S3). This note adds rows M-26…M-51 and three skeptic-raised attacks (RT-66…RT-68). A re-check against this version found 0 unmapped of 68, but 25 attacks still map only to Open rows, so the PLAN criterion is still not met (§Spikes). | High |

## Method

- **Sweep (analyst stage):** four scouts ran (docs, source, community/issues, standards/papers). The analyst re-fetched the load-bearing primary sources on 2026-09-29: the age spec and README; the Tahoe convergence-secret doc; Borg master and 1.4 `security.rst`, the Borg wiki CDC page, `compress.pyx` and `help.rst.inc`; Tarsnap `NEWS.md`; restic `design.rst`; PBS `crypt_config.rs`; dedis `purb/padding.go`; the Cloudflare rate-limit and Durable Objects docs; the CCTV age README; the Wycheproof README; the X-Wing draft. Code inspected: Go `filippo.io/age` v1.3.2; Rust `age` 0.12.1; npm `cctv-age` 0.2.0; crates.io metadata for `x-wing`, `ml-kem` and `hpke`.
- **Skeptic stage:** three independent skeptics (sources, logic, adversary) re-fetched sources on 2026-10-06 and reviewed the key claims K1–K15 (= C2, C3, C4, C5, C8, C10, C11, C12, C13, C14, C15, C9, C25, C21, C24). The verdicts below are the code-computed tally:
  - **verified:** a primary source, and at least 2 of the 3 skeptics did not refute;
  - **secondary only:** no primary source;
  - **contested:** otherwise.
- **Synthesis checks (2026-10-06, this stage):**
  - CCTV `hybrid_and_x25519` header decoded from the npm `cctv-age` 0.2.0 tarball: `expect: success`.
  - borgbackup 1.4.5 sdist `docs/changes.rst` from PyPI: Padmé added in 1.4.1 (2025-04-19); "compress: make Padme size obfuscation usable" in 1.4.4 (2026-03-19).
  - X25519 header sizes measured with the container's `age` 1.1.1: one recipient 168 B, two recipients 266 B.
  - F3-S3 checker re-run in the scratchpad against this version of the matrix (second pass: 68 attacks).
  - Go module `filippo.io/age` v1.3.2 `SIGSUM.md` read from proxy.golang.org (S51), to check the adversary skeptic's update-transparency precedent.
  - Claim verdicts re-aligned with the code-computed tally: C15 is **contested**, not "secondary only"; skeptic cells for C3, C12, C15 and C21 corrected to the skeptics' actual refute flags.
- **Routes used:** raw.githubusercontent.com (vendor docs and source), proxy.golang.org, static.crates.io, crates.io API, registry.npmjs.org, pypi.org / files.pythonhosted.org.
- **Scout and skeptic conflicts resolved:**
  - *PBS keyed digest:* the code shows SHA-256(data ‖ id_key), with id_key derived by PBKDF2. It is a keyed digest, not HMAC.
  - *Padmé "12 %" vs "3.1 %":* both are right. 12 % is the small-input bound; for 64 KiB–4 GiB the bound is 1/32.
  - *Borg's "cannot try faster than backup runs":* true for Borg's repository attacker, **not** for Reliquary's interactive presence oracle.
  - *Tarsnap 2011 mechanism:* secondary only. The vendor post is blocked.
  - *Rust `age` 0.12.1 PQ support:* it has a native, encryption-only `tagpq` (ML-KEM-768 + P-256) recipient, and no `mlkem768x25519`. The analyst's B3 row was wrong and is corrected.
- **Blocked sources (reported to H1; `sources.md` not edited):**
  - eprint.iacr.org: 2024/1616, 2025/558, 2025/532, 2024/546, 2022/959, 2012/631, 2013/429, 2011/207, 2016/977, 2015/455, 2019/016, 2020/1491, 2020/1456. Re-tried by skeptics on 2026-10-06, still blocked.
  - arxiv.org; dl.acm.org; usenix.org; petsymposium.org; kclpure.kcl.ac.uk.
  - nvlpubs.nist.gov; csrc.nist.gov; ncsc.gov.uk.
  - rfc-editor.org and datatracker.ietf.org (draft-ietf-hpke-pq-03; RFC 2104/5869/9180); mailarchive.ietf.org.
  - daemonology.net; words.filippo.io; lwn.net; mega-awry.io; brokencloudstorage.info.
  - ente.com (the Cure53 PDF); tahoe-lafs.org.
  - api.osv.dev and the GitHub advisory API.
  - The github.com web UI: age issue #59 was seen only as a search snippet.
- **Stop rule:** every in-scope question has a primary source or is explicitly marked inference or secondary. The remaining leads sit behind blocked hosts. They are precedent only and carry no recommendation on their own.

## Sources

| # | Source | Publisher | Version or date | Accessed | Primary? |
|---|---|---|---|---|---|
| S1 | age v1 spec, `C2SP/C2SP @ main : age.md` (c2sp.org/age) | C2SP (Valsorda et al.) | main HEAD | 2026-09-29; 2026-10-06 | Yes |
| S2 | age README, `FiloSottile/age @ main : README.md` | F. Valsorda | main HEAD | 2026-09-29 | Yes |
| S3 | Go module `filippo.io/age` v1.3.2 (`age.go`, `pq.go`); proxy.golang.org `.info`: v1.3.0 2025-12-27T14:59Z, v1.3.1 2025-12-28, v1.3.2 2026-08-29T17:40Z (commit times of the tagged commits) | F. Valsorda | v1.3.2 | 2026-09-29; 2026-10-06 | Yes |
| S4 | Rust `age` 0.12.1 crate, static.crates.io (`src/native/`: scrypt, tag, tagpq, x25519; CHANGELOG "age::tagpq::Recipient (encryption-only)") | str4d | 0.12.1 (2026-07-14) | 2026-09-29; 2026-10-06 | Yes |
| S5 | C2SP CCTV age README, `C2SP/CCTV @ main : age/README.md`; npm `cctv-age` 0.2.0 (published 2025-12-08T02:08Z), 143 vectors | C2SP | 0.2.0 | 2026-09-29; 2026-10-06 | Yes |
| S6 | Project Wycheproof README and `testvectors_v1/` (ed25519, hmac_sha256, hkdf_sha256, chacha20_poly1305, x25519, mlkem_768, mlkem_768_encaps: HTTP 200) | C2SP | main HEAD | 2026-09-29; 2026-10-06 | Yes |
| S7 | X-Wing KEM, `dconnolly/draft-connolly-cfrg-xwing-kem @ main` | D. Connolly et al. | front matter 2026-09-23 | 2026-09-29 | Yes (draft) |
| S8 | Tahoe-LAFS "The Convergence Secret", `tahoe-lafs/tahoe-lafs @ master : docs/convergence-secret.rst` | Tahoe-LAFS | master HEAD | 2026-09-29; 2026-10-06 | Yes |
| S9 | Borg internals: security (borg 2), `borgbackup/borg @ master : docs/internals/security.rst` | BorgBackup | master HEAD | 2026-09-29 | Yes |
| S10 | Borg 1.4 internals: security, `borgbackup/borg @ 1.4-maint : docs/internals/security.rst` | BorgBackup | 1.4-maint HEAD | 2026-09-29 | Yes |
| S11 | Borg wiki "CDC issues reported 2025", `raw.githubusercontent.com/wiki/borgbackup/borg/CDC-issues-reported-2025.md` | Borg maintainers | updates dated 2025-06-04 | 2026-09-29 | Yes |
| S12 | Borg `src/borg/compress.pyx` (ObfuscateSize), `docs/usage/help.rst.inc` (level 250 = Padmé) | BorgBackup | master HEAD | 2026-09-29 | Yes |
| S13 | Tarsnap `NEWS.md` (1.0.28 2011-01-18; 1.0.29 2011-02-07; 1.0.41 2025-03-21) | Tarsnap | master HEAD | 2026-09-29 | Yes |
| S14 | restic design, Threat Model, `restic/restic @ master : doc/design.rst` | restic | master HEAD | 2026-09-29 | Yes |
| S15 | Proxmox Backup Server `pbs-tools/src/crypt_config.rs`, `docs/technical-overview.rst` | Proxmox | master HEAD | 2026-09-29 | Yes |
| S16 | Kopia v0.23.1 source (`repo/hashing/hashing.go`, `internal/crypto/key_derivation.go`) | Kopia | v0.23.1 (2026-06-15) | 2026-09-29 | Yes |
| S17 | Duplicacy `src/duplicacy_config.go` | Duplicacy | master HEAD | 2026-09-29 | Yes |
| S18 | Syncthing `lib/protocol/encryption.go` | Syncthing | main HEAD | 2026-09-29 | Yes |
| S19 | dedis PURBs `dedis/purb @ master : purbs/padding.go` (Padmé reference) | EPFL DEDIS | master HEAD | 2026-09-29 | Yes |
| S20 | Nikitin et al., "Reducing Metadata Leakage … with PURBs", PoPETs 2019(4) | authors | 2019 | blocked | Primary, not read |
| S21 | Cloudflare Workers Rate Limiting binding, `cloudflare/cloudflare-docs @ production : src/content/docs/workers/runtime-apis/bindings/rate-limit.mdx` | Cloudflare | production HEAD | 2026-09-29; 2026-10-06 | Yes |
| S22 | Cloudflare "What are Durable Objects", `… : durable-objects/concepts/what-are-durable-objects.mdx` | Cloudflare | production HEAD | 2026-09-29; 2026-10-06 | Yes |
| S23 | Hofmann & Truong, "End-to-End Encrypted Cloud Storage in the Wild", CCS 2024, https://eprint.iacr.org/2024/1616 | authors | 2024 | blocked (snippets, press) | Primary, not read |
| S24 | Backendal, Haller, Paterson, "MEGA: Malleable Encryption Goes Awry", S&P 2023, https://eprint.iacr.org/2022/959 | authors | 2022–2023 | blocked | Primary, not read |
| S25 | Albrecht et al., "Share with Care: Breaking E2EE in Nextcloud", EuroS&P 2024, https://eprint.iacr.org/2024/546 | authors | 2024 | blocked | Primary, not read |
| S26 | Harnik, Pinkas, Shulman-Peleg, "Side Channels in Cloud Services", IEEE S&P Magazine 2010 | authors | 2010 | listing only | Secondary listing |
| S27 | Halevi et al., "Proofs of Ownership in Remote Storage Systems", CCS 2011, https://eprint.iacr.org/2011/207 | authors | 2011 | blocked | Primary, not read |
| S28 | Mulazzani et al., "Dark Clouds on the Horizon", USENIX Security 2011 | authors | 2011 | blocked | Primary, not read |
| S29 | Bellare, Keelveedhi, Ristenpart, "Message-Locked Encryption", EUROCRYPT 2013, https://eprint.iacr.org/2012/631 | authors | 2013 | blocked | Primary, not read |
| S30 | Keelveedhi, Bellare, Ristenpart, "DupLESS", USENIX Security 2013, https://eprint.iacr.org/2013/429 | authors | 2013 | blocked | Primary, not read |
| S31 | Armknecht et al., "Side Channels in Deduplication", AsiaCCS 2017, https://eprint.iacr.org/2016/977 | authors | 2017 | blocked | Primary, not read |
| S32 | Liu, Asokan, Pinkas, "Secure Deduplication … without Additional Independent Servers", CCS 2015, https://eprint.iacr.org/2015/455 | authors | 2015 | blocked | Primary, not read |
| S33 | Dodis et al., "Fast Message Franking: From Invisible Salamanders to Encryptment", CRYPTO 2018, https://eprint.iacr.org/2019/016 | authors | 2018 | blocked | Primary, not read |
| S34 | Len, Grubbs, Ristenpart, "Partitioning Oracle Attacks", USENIX Security 2021, https://eprint.iacr.org/2020/1491 | authors | 2021 | blocked | Primary, not read |
| S35 | Albertini et al., "How to Abuse and Fix Authenticated Encryption Without Key Commitment", USENIX Security 2022, https://eprint.iacr.org/2020/1456 | authors | 2022 | blocked | Primary, not read |
| S36 | Truong et al., "Breaking and Fixing Content-Defined Chunking", CCS 2025, https://eprint.iacr.org/2025/558 | authors | 2025 | blocked (Borg wiki cites) | Primary, not read |
| S37 | Alexeev, Percival, Zhang, "Chunking Attacks on File Backup Services using CDC", https://eprint.iacr.org/2025/532 | authors | 2025 | blocked (restic cites) | Primary, not read |
| S38 | C. Percival, "Tarsnap critical security bug" (daemonology.net, 2011-01-18); LWN 423690 | Tarsnap; LWN | 2011-01-18 | blocked (snippets) | Primary not read; LWN secondary |
| S39 | F. Valsorda, "restic cryptography", https://words.filippo.io/restic-cryptography/ | F. Valsorda | 2017-08-29 | blocked (snippet) | Primary, not read |
| S40 | Borg issues #4883, #5711; restic issues #5291, #5447, #99 | community | as stated | metadata only | No |
| S41 | Cure53, Ente audit summary (Oct 2025), https://ente.com/reports/Cure53-Audit-Summary-Oct-2025.pdf | Cure53 | 2025-10 | blocked (snippets) | Primary, not read |
| S42 | NIST IR 8547 ipd (2024-11-12); FIPS 203/204/205 notice (2024-08-14); UK NCSC PQC timeline (2025-03-20) | NIST; NCSC | as stated | blocked (snippets) | Primary, not read |
| S43 | Signal PQXDH (2023-09); Apple iMessage PQ3 (2024-02) | Signal; Apple | as stated | snippets | Primary, not read |
| S44 | WhatsApp E2EE backups whitepaper (2021-09-10); NCC Group assessment (2021-10-27) | Meta; NCC | 2021 | snippets | Primary, not read |
| S45 | Apple Platform Security, Advanced Data Protection | Apple | current | snippets | Primary, not read |
| S46 | In-repo: `content-encryption-format.md` (CE §5, §8, §9, §10, §12, §16), `d1-threat-model.md` and `docs/security/threat-model.md` (SR, AR, T IDs), `a1-content-identity.md`, `a2-object-envelope.md` (C6, C7, C21, C22, DR-A2-1/2), `d2-key-hierarchy-custody-recovery.md`, `budgets.md`, `corpus/README.md` | this repo | 2026-09-29 … 2026-10-06 | 2026-10-06 | Yes (project evidence) |
| S47 | borgbackup 1.4.5 sdist `docs/changes.rst` (PyPI): 1.4.1 (2025-04-19) "implement padme chunk size obfuscation (SPEC 250), #8705"; 1.4.4 (2026-03-19) "compress: make Padme size obfuscation usable" | BorgBackup | 1.4.5 | 2026-10-06 | Yes |
| S48 | Spike evidence: `spikes/F3-S1/README.md`, `spikes/F3-S2/README.md`, `spikes/F3-S3/README.md` and their `evidence/` | this repo (F3 spike runner) | 2026-09-29 | 2026-10-06 | Yes (project measurement; F3-S2 emulated) |
| S49 | FiloSottile/age issue #59 ("age encryption with X25519 or ssh keys is unauthenticated …") | F. Valsorda | — | search snippet only (github.com web UI blocked) | Secondary until read |
| S50 | Measurement in this stage: `age` 1.1.1 in the container, X25519 header 168 B (one recipient), 266 B (two recipients), 1,000-byte random plaintext | this note | 2026-10-06 | 2026-10-06 | Yes (measurement) |
| S51 | Go module `filippo.io/age` v1.3.2, `SIGSUM.md` ("check their Sigsum proofs … every proof is logged in a public append-only log", binaries v1.2.0+) | F. Valsorda | v1.3.2 | 2026-10-06 | Yes |

## Claims

**Key?** marks the claims the skeptics reviewed (K-id in brackets). Skeptic verdicts are summarised. The **Verdict** column holds the code-computed tally, and it is not overridden. "Correction applied" means the note now uses narrower or corrected wording; the verdict still applies to the claim *as reviewed*. Claims C28–C34 are new in synthesis and have not been reviewed by the skeptics.

| # | Claim (as reviewed) | Sources | Key? | Skeptic 1 (sources) | Skeptic 2 (logic) | Skeptic 3 (adversary) | Verdict |
|---|---|---|---|---|---|---|---|
| C1 | age v1 file key: 16 CSPRNG bytes. Header MAC = HMAC-SHA-256 under HKDF(file key, "header") over the header up to `---`. Payload: 16-byte nonce, HKDF payload key, 64 KiB ChaCha20-Poly1305 chunks with an 11-byte counter and a final flag. A missing final chunk MUST error. | S1 | No | — | — | — | Not separately reviewed (primary S1) |
| C2 | age has no sender authentication for public-key recipients. Anyone holding the homelab public key can make a valid object, so provenance must come from the device-signed record. [K1] | S1; S49 (snippet) | Yes | Upheld (inference from construction; #59 snippet secondary) | Upheld | Upheld | **Verified** |
| C3 | The header MAC binds one file key per header, so an age file decrypts to at most one plaintext across recipients (file-level key commitment). Inference, not stated in the spec. [K2] | S1 | Yes | **Refuted as worded**: no source states it, and it holds only for readers that verify the MAC (the reduction to a SHA-256 collision, ~2^128, is accepted) | Upheld; requires every reader to verify the MAC | Upheld; the spec does not require MAC verification as a MUST | **Secondary only**. Correction applied: stated as a reduction argument with its precondition (NT-16) |
| C4 | The spec says SHOULD NOT mix `mlkem768x25519` with non-PQ recipients; Go age v1.3.2 refuses; an scrypt stanza MUST be alone. So a PQ object's recovery recipient must be PQ, not a passphrase stanza. [K3] | S1, S3 | Yes | Upheld (reproduced the refusal); "must be PQ" is a design rule built on a SHOULD NOT; `mlkem768p256tag` is also PQ | Upheld; stock decryptors still accept mixed files, so the homelab must enforce the rule itself | Upheld; a passphrase-wrapped PQ identity file is a different thing and stays valid | **Verified**. Correction applied: homelab ingest enforcement (M-16, NT-02c) |
| C5 | Go age has native hybrid PQ since v1.3.0 (2025-12-27; v1.3.2 2026-08-29). Rust `age` 0.12.1 has no `mlkem768x25519`. The PQ header is about 1,627 B. [K4] | S3, S4, S2 | Yes | Upheld; measured 1,627 B; the Rust crate *does* ship native `tagpq` (a PQ hybrid, encrypt only) | Upheld; also notes `hpke` 0.14.1 MLKEM768-X25519 (A2 C22) | Upheld; B3 corrected | **Verified**. Correction applied to B3 |
| C6 | `age-inspect` reveals recipient types, PQ use and payload size without a key. | S2 | No | — | — | — | Not separately reviewed (primary S2) |
| C7 | age defines no padding. Ciphertext length = header + 16 + n + 16·⌈n/64 KiB⌉, so the exact size is visible to anyone holding the ciphertext. | S1, S46 | No | — | — | — | Not separately reviewed (primary S1). F3-S1 confirmed injectivity |
| C8 | Padmé: 32 sizes per octave and ≤ 3.125 % for 64 KiB–4 GiB; 16 sizes and 6.25 % for 256 B–64 KiB; 64 sizes and 1.5625 % at ≥ 4 GiB. 64 KiB buckets cost +31 % at 100 KB. [K5] | S19 | Yes | Upheld; the reference pads with random bytes and uses a float log2 | Upheld; the per-file maximum of 3.125 % slightly exceeds the "< 3 %" rule, so the pass rests on byte-weighted cost | Upheld; F3-S1 cross-check had 0 mismatches | **Verified** |
| C9 | Borg computes chunk IDs before padding; Borg (level 250) and Tarsnap 1.0.41 (2025-03-21) deploy Padmé. [K12] | S11, S12, S13, S47 | Yes | Upheld; Borg Padmé added in 1.4.1 (2025-04-19), "usable" only in 1.4.4 (2026-03-19), opt-in and off by default | Upheld | Upheld; Borg pads the compressed size | **Verified**. Correction applied: dated, described as opt-in |
| C10 | The cloud sees exact plaintext size even with padded objects: the receipt carries `size`, the present-check uses (dedup_id, size), SR-24 declares size. [K6] | S46 | Yes | Upheld | Upheld; the multipart layout (RT-15) and the receipt's `device_id` also matter | Upheld | **Verified** |
| C11 | Tahoe: anyone who knows the convergence secret can run confirmation-of-a-file and learn-the-remaining-information; the defence is secrecy. Every Reliquary device holds the secret, so any compromised device can run both through the presence answer. [K7] | S8 | Yes | Upheld; SR-21's "current batch" gives no protection, because the attacker chooses the batch | Upheld; F3-S2 C0 demonstrates it | Upheld | **Verified** |
| C12 | From BUD-HASH: about 60k lookups in 6 h, so *any* per-device limit that permits seeding permits a 10k probe in well under a day; rate limiting alone cannot pass. [K8] | budgets, corpus, PLAN | Yes | **Refuted**: BUD-HASH is a hashing budget, not a lookup rate; only uniform caps were simulated | **Refuted**: phase-based, lifetime or credit budgets, or USB seeding, could pass | **Refuted**: same; true only for uniform caps | **Contested**. Not used as support. Replaced by the F3-S2 measured statement on uniform caps (Q8) |
| C13 | The Workers Rate Limiting binding: 10 s or 60 s periods, per location, "permissive, eventually consistent … not … an accurate accounting system". DOs are single-threaded and strongly consistent. [K9] | S21, S22 | Yes | Upheld verbatim; exactness depends on input/output gates | Upheld | Upheld; Miniflare is local only | **Verified** |
| C14 | Per-person-scoped, record-first presence answers with exact DO accounting turn the oracle into an audited one without changing cross-user storage dedup. [K10] | S8, S46 | Yes | **Refuted** by F3-S2 C2/C3/C3L | **Refuted**: the Worker cannot verify encrypted records, so record-first is forensic only | **Refuted** | **Contested**. Withdrawn. Replaced by the F3-S2 results in §3 |
| C15 | HMAC(K, m) and HMAC(K, SHA-256(m)) are equally opaque before a leak; the digest form adds only hash-list testing after a leak and makes rotation feasible; so F3 supports A1's construction. [K11] | S9, S16, S46 | Yes | **Refuted**: Borg and Kopia MAC the content, so they do not support it (nearest precedent: Duplicacy); rotation is cheaper, not uniquely feasible; the hash cache becomes testable | **Refuted**: only pre-leak opacity survives, as unsourced reasoning; adopting it skips the settled-text conflict (DR-A1-1) | **Refuted**: rotation is cheaper, not uniquely feasible (BUD-AUDIT, BUD-HASH); the hash cache (RT-31) becomes testable | **Contested**. Not used as support. Correction applied: pre-leak opacity kept only as unsourced reasoning; trade-offs passed to A1 as input, with no F3 verdict |
| C16 | A leaked secret plus the cloud's ID history allows offline, unlimited testing of every historical ID (MLE brute force). Rotation limits only future exposure. | S29/S30 (not read), S8 | No | — | — | — | Not separately reviewed; paper sources secondary; Tahoe primary |
| C17 | A DupLESS key server in Cloudflare is worse than today. A homelab-held asynchronous OPRF is feasible but changes the settled "HMAC(family secret, content)". | S30 (not read) + inference | No | — | — | — | Secondary only |
| C18 | Borg 1.x loses confidentiality with multiple clients (counter reservations); Borg 2 uses per-session keys and AAD binding. | S9, S10 | No | — | — | — | Not separately reviewed (primary) |
| C19 | Tarsnap 1.0.28 (2011-01-18) fixed a critical chunk-encryption bug; 1.0.29 (2011-02-07) added key rotation tools. Mechanism from snippets only. | S13; S38 | No | — | — | — | Dates primary; mechanism secondary |
| C20 | The 2025 CDC attacks recover keyed-chunker parameters; whole-file cloud objects avoid them. | S11, S14 (papers not read) | No | — | — | — | Not separately reviewed |
| C21 | Malicious-server attacks on deployed E2EE storage (Hofmann–Truong: 4 of 5; MEGA; Nextcloud) stemmed mainly from unauthenticated key material and metadata relayed by the server. [K14] | S23–S25 (not read) | Yes | **Refuted**: snippets also cite unauthenticated content encryption (Icedrive, Seafile) and downgrade; Nextcloud details unconfirmed | **Refuted**: no primary read | **Refuted**: press coverage confirms only 4 of 5 broken (file injection, tampering, plaintext access); the root cause is unconfirmed | **Contested**. The matrix does not depend on it. Correction applied: wording widened to include unauthenticated content modes and downgrade |
| C22 | Hash-as-proof-of-possession broke Dropbox dedup; ADR-0001 §4 already grants no read rights on a hit. | S27, S28 (not read); ADR-0001 | No | — | — | — | Mapping from ADR-0001 primary; paper details secondary |
| C23 | Borg's attack model (trust the client, not the repository) equals D1 SR-01. | S9 | No | — | — | — | Not separately reviewed (primary) |
| C24 | HNDL applies to every X25519 wrap leaving the house, but not to HMAC IDs or the symmetric layer directly. PQ costs < 0.1 % of transfer. [K15] | S1, S2 | Yes | **Refuted** on cost (about 0.13–0.58 % with metadata records); restore keys need PQ | **Refuted** on cost (two stanzas: 0.26–1.2 %) and scope | **Refuted**: classical device keys used for SR-15 secret sealing let HNDL reach the dedup secret, and so the IDs; cost bound wrong | **Contested**. Correction applied: cost restated as C28; scope extended to device keys (M-40). The OD-06 evidence no longer rests on C24 alone (§7) |
| C25 | `cctv-age` 0.2.0 has hybrid vectors (`hybrid_and_x25519`, `hybrid_low_order`, …) and stream edge cases; Wycheproof serves the listed primitive files. [K13] | S5, S6 | Yes | Upheld; but `hybrid_and_x25519` is `expect: success` | Upheld; NT-02 misused it | Upheld; same | **Verified**. Correction applied: NT-02 split (decrypt conformance / encoder refusal / ingest policy) |
| C26 | Timing and per-device volume leak to any relay (restic, Borg). | S14, S9 | No | — | — | — | Not separately reviewed (primary) |
| C27 | Borg and Kopia bind the ID into AEAD AAD. age has none, so Reliquary binds identity in the signed record (dedup_id, sha256, size, header_mac). | S9, S16, S46 | No | — | — | — | Not separately reviewed (primary + inference) |
| C28 | **New (arithmetic).** PQ header overhead vs X25519. One stanza: 1,627 − 168 = **1,459 B** per age object. Two stanzas: 3,184 − 266 = **2,918 B**. CE encrypts a content object and a metadata record per file, so the extra is 2,918 B per file (one stanza) or 5,836 B (two stanzas). At the F3-S1 means this is 0.131 % / 0.262 % for photos (2,229,987 B mean) and 0.577 % / 1.154 % for documents (505,744 B mean). The family mean is unmeasured. | S3/A2 C6 (1,627, 3,184), S50 (168, 266), S48 | — | — | — | — | New, not reviewed; inputs are measurements |
| C29 | **New (project evidence).** The CE §10 dedup "present" answer is a receipt from *any* device for (dedup_id, size). The receipt line carries `device_id`, `committed_at` and `meta_sha256`, so a probing device learns which device holds a file and when. | S46 (CE §10) | — | — | — | — | New, not reviewed; quoted from the repo |
| C30 | **New (spike result, emulated).** In F3-S2: only C3 (no cross-person answer below T_x) passed; C0, C1, C2 failed; C3 failed for same-person targets and under a receipt-timing leak (C3L); no configuration except C3 stopped a 20-candidate confirmation within the first hour. | S48 | — | — | — | — | New; spike result, emulated, not real Cloudflare |
| C31 | **New (spike result).** F3-S1: unique-size share 99.62 % / 96.58 % (photos at N = 10k / 100k), 82.00 % / 54.32 % (documents); falls below 50 % for photo sets ≥ 4M and document sets ≥ about 130k. Padmé cost 1.131 % (photos), 1.145 % (documents), byte-weighted. | S48 | — | — | — | — | New; measured on public data |
| C32 | **New (analytical, second pass).** Per-person dedup keys (option F) make cross-person IDs uncomputable by a compromised device and remove cross-person ID equality from the cloud, while the homelab still dedups by SHA-256. | inference from C11, ADR-0001 | — | — | — | — | New, not reviewed; analytical only |
| C33 | **New (project text + inference).** ADR-0001 §4 step 2 keys staged objects by dedup ID, so key existence (412, HEAD, multipart conflict) is a presence channel unless staging uses per-upload keys (D1 SR-07). | ADR-0001; S46 | — | — | — | — | New, not reviewed; raised by the adversary skeptic; R2 create-only behaviour not tested here (C1-S1) |
| C34 | **New (project text + inference).** ADR-0002 lets any enrolled device enroll another device without the admin, so an insider with brief access can enroll into another person's account and turn cross-person probing into same-person probing. | ADR-0002 §3 | — | — | — | — | New, not reviewed; raised by the adversary skeptic |

## Findings

### 1. What age guarantees, and what it does not (C1–C7)

- **Guaranteed (C1):**
  - one file key per object;
  - a header MAC over all stanzas;
  - chunked AEAD with a counter and final flag. Reordering, truncation and extension are detected if the reader enforces the final-chunk rule. CE §5.5 found that the Rust `StreamReader::seek` does not, and fixed Reliquary's own range reader.
- **Not guaranteed:**
  - sender identity (C2, verified);
  - length hiding (C7);
  - the object's meaning (which device, file or sequence). The signed record supplies that (C27).
- **Key commitment (C3, secondary only).** Two different file keys verifying the same header MAC would need a SHA-256 collision inside HKDF or HMAC, which is about 2^128 work. The argument holds **only if every reader verifies the header MAC before using the file key**. Go age does (`age.go`). Reliquary's own readers must as well: the range reader and any Rust homelab or restore tool (NT-16). Post-decrypt SHA-256 and HMAC verification at the homelab is an independent second guard. Since C3 is not vendor-stated, nothing in this note relies on it alone.
- **Partitioning oracles (S34, secondary):** negligible with a single homelab identity and no password stanzas on staged objects (M-23).
- **Multi-recipient rules (C4, verified):**
  - No PQ and classical mixing. This is a SHOULD NOT in the spec, enforced by Go's encrypt path only. **Stock decryptors accept mixed files** (CCTV `hybrid_and_x25519` = `expect: success`). So the homelab must reject any object whose stanza set is not exactly the pinned PQ recipients (M-16).
  - An scrypt stanza must be alone.

### 2. Size, timing and volume leakage (C7–C10, C26, C31; F3-S1)

- **Measured on public data (F3-S1).**
  - Exact size is a strong fingerprint at per-device scale: 99.6 % (photos) and 82.0 % (documents) of files have a unique size at N = 10k. At N = 100k it is 96.6 % and 54.3 %.
  - At family scale it weakens. 2–10 TB is roughly 0.9–4.5M photos at the Open Images mean. Uniqueness there is 75 % → 45 %, and documents fall to 22.8 % at 975k.
  - After Padmé: ≤ 0.43 % unique at N = 10k; the median size class holds about 45 files at 10k and about 430 at 100k.
  - Padmé cost: 1.131 % / 1.145 % byte-weighted. 64 KiB buckets cost 7.58 % on documents, which fails the cost leg.
- **Which N matters.** The cloud sees per-device upload streams and per-batch timing (C26), so the per-device rows (10k–100k) describe what an observer can attribute. The cloud also accumulates the family-wide set over time, and at that scale the PLAN uniqueness leg is mixed.
  - "Unique within the set" understates the risk. An attacker confirming a candidate needs only a size match plus set or timing correlation (adversary skeptic). After Padmé, the "classes of fewer than 10 files" share is a better measure: 1.5 % at N = 10k.
  - So F3 bases the padding recommendation on three things: the per-device uniqueness, the measured anonymity sets, and the low byte-weighted cost. It does not rely on the family-scale uniqueness leg.
  - The public corpora are old: Flickr originals from 2005–2018 and US government documents. Modern phone HEIC/HEVC output and a few-camera family library could cluster differently. **DR-F3-1 is provisional until the owner-library kit runs** (`docs/research/kits/F3-S1/`).
- **Layout requirements if padding is adopted (DR-F3-1 B):**
  - pad with zeros before age, so CE's byte-identical regeneration on resume still works;
  - compute the dedup ID and SHA-256 over the unpadded content (Borg precedent, C9; opt-in in Borg since 1.4.4);
  - **frame the true length inside the encrypted payload**, for example as a fixed trailer or prefix, so that the object alone suffices for a break-glass restore (M-41). If the length lives only in the separate metadata record, losing that record leaves stock `age -d` output with up to 3.125 % trailing zeros. Formats that are located from the end of the file (ZIP/OOXML/EPUB end-of-central-directory) would then plausibly fail to open. That is inference and untested (NT-13b);
  - carry the padded length in every cloud-visible field: receipt, present-check, SR-24, multipart part layout and Content-Length (C10, RT-15);
  - pad metadata records to fixed size classes too (RT-14, M-26).
- **Residual after padding:** set fingerprinting over time windows, timing and volume, and ID equality across devices. These stay under AR-05 (M-06).

### 3. The dedup oracle (C11, C13, C16, C29, C30; F3-S2)

- **Threat (C11, verified).** Every enrolled device holds the family secret. With ADR-0001 §4's global answer, one compromised phone can run both Tahoe attacks against the whole family.
- **F3-S2 results** (emulated: a Python 1-hour-step simulation plus a Miniflare Durable Object test; **not real Cloudflare**). The verdict is taken over the attacker's best strategy:

  | Config | What it is | 10k probe | 20-candidate confirmation |
  |---|---|---|---|
  | C0 | ADR-0001 as written | FAIL (≤ 1 h) | FAIL |
  | C1 | + per-device limit sized to BUD-HASH (9,567 lookups/h) | FAIL (2 h, no alert) | FAIL (≤ 1 h) |
  | C1s | flat 333 lookups/day | passes by time (30.04 d), but a phone's first seed takes 172 d and a 500k-file desktop > 400 d | FAIL (≤ 1 h) |
  | C2 | + record-first + exact DO accounting + auto-suspend | FAIL: an attacker that uploads its misses (about 2 GB) is never alerted; attackers that abandon misses are alerted after 1,120–2,000 probes (P(learn) 0.11–0.20) | FAIL |
  | C3 | per-person scope below T_x | **PASS by construction** for other people's files (the simulator answers "missing", so P(learn) = 0 is an input, not a finding); FAIL for the same person's files | PASS cross-person (by construction); FAIL same-person |
  | C3L | C3 with faster receipts for content already held | FAIL | — |

- **Criteria note.** The PLAN test is the 10k probe (more than 30 days, or an alert). Two criteria used here are **F3 additions** and need H1 or owner sign-off: the 20-candidate confirmation, and rejecting C1s because of its first-seed cost under BUD-TTS. All thresholds (T_x, the 333/day cap, detector and alert levels) are hand-set simulation parameters, not budget values. BUD-ABUSE has no owner value yet. H1 should add the ones that survive to `budgets.md` as proposals.
- **What this means:**
  1. **Uniform throttling cannot be the defence.** Any *uniform* cap that lets a first seed finish in under about 170 days lets a 10k probe finish in under 30 days. Phase-based budgets were *not* simulated: a seeding allowance at enrollment followed by a strict cap, credits earned only from bytes the homelab has verified, or first seeds moved onto the USB transport. They might pass the 10k branch for devices compromised after seeding. **None of them can stop the 20-candidate confirmation**, because any budget of 20 or more permits it (C30). That is the main reason to remove the answer rather than ration it.
  2. **Record-first is forensic only.** Records are encrypted to the homelab with the signature inside (SR-03), so the Worker cannot check a record against the queried ID before it answers. At the homelab, a probe hit looks exactly like a legitimate dedup hit. Record-first leaves a device-signed trail after the fact. It is not a gate. The C2 detectors are evaded by the "upload the misses" strategy, and they produce false alarms:
     - the same-size-cluster rule fires on a desktop document seed (GovDocs1 has clusters of up to 425 files per 250k);
     - the 24 h orphan rule fires on a legitimate seed if the orphan rate is 1 %. That rate is unmeasured.
  3. **Removing the answer is what works, analytically.** C3 passes for other people's files below T_x, but only by construction: it holds only if *no other device-observable channel* reveals prior presence. F3-S2 modelled one such channel (receipt timing, C3L) and it broke C3. The others are listed below as conditions and are not modelled. The same reasoning extends to an option F3-S2 did not simulate: **D, no upload-skip below T_x for anyone**. In D, small files always upload, the homelab dedups, and the device skips only on its own prior receipts. With no answer there is no oracle, so D also closes the same-person case that C3 leaves open, and the cloud needs no person-to-ID index. This is analytical, not simulated.
  4. **Alternatives the skeptics raised, assessed analytically (none simulated):**
     - **F. Per-person dedup keys**, e.g. a cloud-visible ID under HKDF(family root, person_id). The homelab still dedups storage across people by SHA-256 after decryption. A compromised device cannot compute another person's IDs at all, so the cross-person oracle is closed *cryptographically*, not by a Worker rule. The cloud sees no cross-person ID equality (shrinks M-06) and needs no person-to-ID index, and a leaked device secret exposes one person's IDs, not the family's. Costs: cross-person upload-skip is lost at *every* size, including large shared videos; same-person probing remains as under C (and so does M-50). It changes the settled "HMAC(family secret, content)", so it is an owner question (DR-F3-2 option F, together with A1's DR-A1-1).
     - **G. Randomised upload threshold** (Harnik, Pinkas and Shulman-Peleg 2010; paper not read, mechanism as described in secondary sources): the server keeps a secret random threshold per ID and allows upload-skip only after that many copies have been uploaded. D1 handed this to F3. Family duplicates are typically a handful of copies, so to hide a single existing copy the threshold range must exceed those counts. Below the threshold everything uploads, which brings the bandwidth close to E. A probe still learns presence at the threshold boundary with some probability per file, and the cloud must hold per-ID counters. F3 **rejects G for v1**: about E's cost, weaker than D, and more state. This is analytical only.
     - **H. Homelab-gated presence answers.** The homelab, which can decrypt and verify the signed record, answers "present" asynchronously through the queue. This makes record-first a real gate with attribution, at the cost of latency. It does not prevent probing, because a probe hit is indistinguishable from a legitimate dedup hit at the homelab. It adds attribution and lets homelab-side detectors run before an answer is released. It is not recommended as protection; it may complement C or F.
     - **Detectors not tried in F3-S2:** uploaded-miss volume relative to the device's discovered-file count, and a homelab content-similarity detector (the homelab sees plaintext, so it can flag bursts of near-identical documents, the learn-the-remaining-information pattern, even when the attacker uploads its misses). Both are detection, not prevention, and do not stop the 20-candidate case. They go to the Wave 2 re-run.
- **Conditions for C, D or F to hold.** Each device-observable channel must behave the same whether or not the content is already stored below T_x. Each is a matrix row:
  - **M-28 receipt independence:** below T_x, receipts follow the same path and timing whether or not the content is already stored, for example full upload, full verify and receipts released on a fixed batch schedule. Staging-deletion timing must not differ either. C3L shows that without this the oracle returns.
  - **M-29 claims:** claim-conflict answers are scoped like presence answers.
  - **M-30 usage display:** per-person usage and quotas never reveal dedup.
  - **M-27 device-neutral answers:** a cross-device "present" answer must not relay another device's `device_id`, `committed_at` or `meta_sha256` (C29). Return present/missing only, or a homelab-signed token over (dedup_id, padded size).
  - **M-49 staging namespace:** ADR-0001 §4 step 2 keys staged objects *by dedup ID*. A device holding a presigned URL for that key can learn whether another device already staged it (a create-only PUT failing with 412, a HEAD, a multipart conflict), or race and overwrite it. Below T_x, objects must be staged under per-upload keys (D1 SR-07, already in OD-04), claims must be per device, and the cloud must expose no key existence by dedup ID.
  - **M-50 enrollment:** under ADR-0002 any enrolled device can show a pairing code or QR token. A family member with brief access to another person's unlocked computer can enroll their own phone *into that person's account*, which turns cross-person probing into same-person probing, and C does not cover that. Every new enrollment must notify the account owner and the admin. Optionally, a newly enrolled device gets no "present" answers (only its own receipts) for a hold-off period.
  - Not yet assessed: USB manifest acknowledgements and the health UI. A3 and E3 must check both against the same rule.
- **What remains under C:** same-person probing (including the M-50 enrollment route) and everything at or above T_x. A device compromised after it was revoked keeps the secret (RT-29). All of this goes into AR-06 (narrowed), which already says so in D1's register.
- **Exact DO accounting is still useful** as a burst guard and as forensic evidence. It runs in the attacker-adjacent tier, though: a compromised Worker or Cloudflare account can drop its alerts and suspensions. The **authoritative** forensic record is the homelab's: device-signed records plus per-device query counts that the homelab pulls and compares. The emulated DO kept exact counts and hard caps under 2,000 concurrent requests per trial (local workerd only). The rate-limit binding is a burst guard only (C13, verified).
- **Record-first side effects.** A record created by probing pollutes the keep-forever catalog. Two rules follow. A record accepted through a presence answer **never** confers restore rights (M-19). Records from suspected probes are flagged for admin review.
- **Offline residual (C16).** A leaked secret plus the cloud's ID history can be tested offline. The mitigations are SR-15, epoch rotation, short cloud-side ID retention, and PQ protection of the channels that carry the secret (M-40). The rest stays in AR-06.

### 4. Dedup-ID construction, domain separation, rotation (C15, contested)

- **No F3 verdict.** The only claim comparing the two forms (C15) is **contested**: all three skeptics refuted it as reviewed. What survives is unsourced hash-then-PRF reasoning that both forms are equally opaque *before* a leak. The RFC 2104 text and Bellare's proofs were blocked. The nearest deployed precedent for the digest form is Duplicacy's MAC-over-MAC (S17). Borg and Kopia MAC the content itself, so they do not support it. F3 therefore neither endorses nor objects to A1's HMAC(K_e, kind ‖ SHA-256(m)); it supplies the trade-offs below.
- **Trade-offs, not a verdict:**
  - *Rotation cost.* The digest form rotates from device caches cheaply. The content form can also rotate: the homelab re-derives IDs during the monthly fixity read (BUD-AUDIT), and devices re-hash within BUD-HASH. The difference is cost, not feasibility.
  - *Added exposure.* With a leaked key, the digest form makes SHA-256 hash lists testable without the files, and that includes every device's plaintext hash cache (RT-31, M-32).
  - This is input to A1's DR-A1-1. A1 owns the decision.
- **Domain separation:** HKDF with versioned info labels (Kopia's pattern, Tahoe's versioned tags), plus A1's kind byte and epoch. All keys come from one family root under distinct labels.
- **Rotation linkage (M-14, downgraded to "Open, likely Accepted"):**
  - The homelab cannot push an unlinkable re-keyed index when every device re-queries its new-epoch IDs in batches that have per-device timing and set sizes, and when padded-size classes persist. A cloud that holds the old secret could probably link old and new IDs.
  - Alternative: **flush the cloud's ID history at rotation.** The cloud keeps no epoch-e IDs, and devices re-seed presence under e+1. The residual is accepted in AR-06.
  - A1 and D2 must analyse this. F3 does not claim it is solved.

### 5. Malicious cloud: swap, replay, drop, withhold (C2, C21, C23, C27)

- D1's "cloud = availability only" model is the same as Borg's (C23). The literature's failure classes map onto D1's SRs (matrix M-07…M-12). The precedent papers (C21) are **contested and secondary only**, so they illustrate the matrix but do not support it. Read loosely, they cover unauthenticated relayed key material, unauthenticated metadata, unauthenticated content modes and downgrade. All four are covered: SR-02/03/04/14/16, age's AEAD, and M-12.
- **F3 additions:**
  - An empty or absent answer means "not safe" (Nextcloud lesson, secondary).
  - Recipient sets and format versions are never taken from the Worker.
  - Ingest rejects any object whose stanza set differs from the pinned set (M-16).
  - Presigned-upload header signing (Cure53/Ente, secondary) maps to SR-09.

### 6. Incidents and their lessons (C18–C22)

| Incident | Lesson for Reliquary | Status |
|---|---|---|
| Tarsnap 2011 (mechanism secondary) | Nonce invariants belong in an API; a rotation and re-encryption path must exist before a bug ships | CE release rule plus mutation tests (M-17); rotation path open (D2) |
| Borg 1.x multi-client counter reuse | Never share or roll back nonce state across writers | Per-object random file keys; journal excluded from OS backups (M-18, NT-06). Extended: all device secrets are non-backup (M-33) |
| Valsorda 2017 restic review (secondary) | An informal expert review is valuable, but it is not an audit | Suggestion to D4/H2 (no cost estimate yet; not a decision request) |
| Dark Clouds / Proofs of Ownership 2011 (secondary) | A hash is not proof of possession | ADR-0001 §4; extended to probe records (M-19) |
| 2025 CDC attacks (secondary) | Keyed chunkers leak their parameters through chunk sizes | Whole-file objects in the cloud; hand-off to A6 for any future off-site copy |
| MEGA, Nextcloud, Hofmann–Truong (contested, secondary) | Authenticate everything the server relays, including the content mode | SR-02/03/14/16; M-12 |

### 7. Post-quantum (C4, C5, C24, C28)

- **What is verified:**
  - feasibility: Go age ≥ 1.3.0 ships the hybrid recipient natively, and CCTV has hybrid vectors (C5, C25);
  - the binding constraints: no mixing; scrypt alone (C4).
- **The harvest-now argument.** All three skeptics accept the reasoning: wraps are X25519, data is kept forever, and ciphertext crosses Cloudflare and USB. C24 as originally stated is **contested**, though, on its cost figure and its scope. Two corrections:
  - **Scope.** The argument extends to **device encryption keys**. Under SR-15, the dedup secret may be sealed to a device key and relayed through Cloudflare. Restores are re-encrypted to the target device's own key and staged in R2, which is settled. If those device keys are X25519, a recorded transcript later yields the family dedup secret, which makes every historical ID testable, and also yields the restored plaintext (M-40). So the OD-06 evidence covers homelab, recovery **and device** encryption keys. Signatures (Ed25519) face no harvest-now threat.
  - **Cost (C28; arithmetic on measured headers).** The extra header bytes per file over X25519 are:
    - one PQ stanza per object (A2's P1): 2,918 B. That is 0.13 % at the photo mean and 0.58 % at the document mean;
    - two PQ stanzas per object (D2's P2): 5,836 B. That is 0.26 % and 1.15 %.

    Still small, but not "under 0.1 %". The family mean file size is unmeasured.
- **What the OD-06 support rests on.** Not on C24, which is contested. It rests on: classical age wraps the file key with X25519 (C1, primary spec); keep-forever retention and ciphertext crossing R2 and USB (settled, CLAUDE.md and ADR-0001); feasibility (C5, verified); the measured cost (C28). The step from those facts to "a future quantum adversary could unwrap recorded objects" is the standard harvest-now argument; F3 read no primary PQ-policy text (NIST IR 8547 blocked, S42).
- **Signatures.** Ed25519 device signatures face no harvest-now *confidentiality* threat. But records are kept forever, and provenance (M-36) and audit could later depend on re-verifying them, which a future quantum adversary could forge. Rule: signatures are verified once at ingest, and the homelab stores the result under its own integrity chain (M-51).
- **Rust status.** The `age` 0.12.1 crate has native `tagpq` (ML-KEM-768 + P-256, encrypt only) and no `mlkem768x25519`. Its ML-KEM and HPKE code is a starting point for the X-Wing stanza. A2 C22 found that `hpke` 0.14.1's X-Wing accepts a low-order X25519 share, which CCTV `hybrid_low_order` requires decoders to reject.
  - Every Reliquary decoder needs a rejecting decapsulation. That includes the device-side restore path, if device keys are PQ (A8).
  - The crate is pre-1.0 ("beta releases for testing purposes only"), which is a maturity risk for A2 and F1.
- **Alternatives F3 notes but does not recommend:**
  - `tagpq` with a hardware-held P-256 homelab key: the stanza tag links files to the recipient, and the key custody changes;
  - the `age-plugin-pq` plugin on desktop as an interim (not viable on Android);
  - a Go encoder on devices via gomobile.

### Alternatives compared

| Topic | Option | Fit with settled requirements | Pros | Cons | Evidence |
|---|---|---|---|---|---|
| Dedup ID | A1: HMAC(K_e, kind ‖ SHA-256(m)), HKDF epoch keys | Wording deviates (DR-A1-1) | Cheap rotation from device caches | Hash-list and hash-cache testing after a leak | C15 (contested) |
| | HMAC(K, m) as settled | Exact | Testing needs the file bytes | Rotation costs a device re-read; the homelab can piggyback on BUD-AUDIT | C15 |
| | Homelab-aided asynchronous OPRF | Changes settled text | Takes the secret off devices | Latency; new primitive; USB IDs harder | C17 |
| Presence answer | A. Global + rate limits | As written | Most bandwidth saved | **FAIL** (F3-S2 C0/C1) | C30 |
| | B. A + record-first + exact DO accounting | Same | Forensic trail | **FAIL** (C2): evaded; false alarms | C30 |
| | **C. Per-person scope below T_x** + M-27…M-30 | Narrows cross-user upload-skip (owner question) | **PASS** cross-person (emulated) | Same-person and ≥ T_x exposed; cloud holds a person-to-ID index; re-uploads | C30 |
| | **D. No upload-skip below T_x for anyone** + M-27…M-30 | Narrows cross-user upload-skip (owner question) | No small-file oracle at all; no person index | More re-uploads, including the same person's own devices (not measured) | analytical |
| | E. Homelab-only dedup, all sizes (D1's option) | Same question | No cloud oracle | Most re-uploads | D1 |
| | F. Per-person dedup keys (HKDF(root, person_id)) + M-27…M-30, M-49, M-50 | Changes "HMAC(family secret, content)" (owner question) | Cross-person oracle closed cryptographically; no cross-person ID equality; no person index; leak exposes one person | Cross-person upload-skip lost at all sizes; same-person residual | analytical (§3) |
| | G. Randomised upload threshold (Harnik et al.) | Narrows upload-skip | Blurs the presence signal | Close to E's bandwidth for family duplicate counts; residual boundary leak; per-ID counters | analytical; paper not read |
| Padding | None | As written | 0 cost | Size fingerprint (AR-05) | C7, C31 |
| | **Padmé**, zeros, length framed inside the payload | Fits | 1.13–1.15 % measured | Format and kit work; all size fields change | C8, C31 |
| | 64 KiB buckets | Fits | Aligns with age chunks | 7.58 % on documents | C31 |
| | Keyed-PRF random padding (Borg's random levels) | Fits | Keeps byte-identical resume if derived from a key | Not evaluated | — |
| Recipient | X25519 only | Fits | Smallest; Rust support | HNDL on keep-forever data | C24 |
| | **mlkem768x25519 for all encryption keys** (homelab, recovery, device) | Fits; device side affects ADR-0003 | PQ throughout | 0.13–1.2 %; Rust X-Wing encode **and** decode work | C4, C5, C28 |
| | Mixed PQ + classical | Violates the SHOULD NOT | — | Loses PQ | C4 |

### Similar work and lessons (annotated bibliography, one-line lessons; normative, Draft)

| # | Work | One-line lesson for Reliquary | Source |
|---|---|---|---|
| B1 | age v1 spec (C2SP) | Header MAC and STREAM give integrity and truncation detection, but no sender authentication and no length hiding. | S1 |
| B2 | age v1.3 PQ recipients and README | Hybrid PQ is off the shelf; never mix with classical recipients; `age-inspect` shows sizes and PQ use. | S2, S3 |
| B3 | Rust `age` 0.12.1 | Native `tagpq` (ML-KEM-768 + P-256, encrypt only) but **no `mlkem768x25519`**; reuse its ML-KEM/HPKE code; pre-1.0. | S4 |
| B4 | CCTV age vectors | Decrypt-direction conformance; `hybrid_and_x25519` expects success, so it cannot test refusal to mix. | S5 |
| B5 | Wycheproof | Primitive-level negative vectors. | S6 |
| B6 | X-Wing draft | The hybrid combiner is still a draft, and low-order handling is still moving: pin the vectors. | S7 |
| B7 | Tahoe-LAFS convergence secret | Every secret holder can confirm files and brute-force the remaining fields; rotation means a new dedup domain. | S8 |
| B8 | Borg 2 security internals | Trust the client, not the repository; MAC IDs; bind the ID into authenticated data; session keys. | S9 |
| B9 | Borg 1.4 security internals | Shared nonce state across clients destroys confidentiality. | S10 |
| B10 | Borg wiki, CDC 2025 | Padding after computing the ID keeps dedup; small-file size fingerprinting survives chunker fixes. | S11 |
| B11 | Borg `obfuscate` / Padmé | Opt-in Padmé since 1.4.1 (2025-04-19), usable since 1.4.4 (2026-03-19), off by default. | S12, S47 |
| B12 | Tarsnap NEWS | Have a rotation path ready; PADME chunks since 1.0.41 (2025-03-21). | S13 |
| B13 | restic threat model | Storage readers infer sizes from timing; a leaked key means re-encrypting everything. | S14 |
| B14 | Proxmox Backup Server | A keyed digest leaves the server unable to verify: verify where the key lives. | S15 |
| B15 | Kopia | HKDF purpose labels from one master key; content ID as AEAD associated data. | S16 |
| B16 | Duplicacy | MAC-over-MAC IDs are deployed: the nearest precedent for A1's digest form. | S17 |
| B17 | Syncthing untrusted devices | Minimum-size padding and deterministic metadata encryption toward untrusted peers. | S18 |
| B18 | Padmé / PURBs (reference code) | O(log log M) leakage; measured 1.13–1.15 % byte-weighted on public corpora. | S19, S20, S48 |
| B19 | Cloudflare rate-limit binding | A per-location, eventually consistent burst guard, not accounting. | S21 |
| B20 | Durable Objects | Strongly consistent per-key state: exact counters (emulated). | S22, S48 |
| B21 | Hofmann & Truong, CCS 2024 | Server-relayed, unauthenticated keys, metadata and content modes broke 4 of 5 providers. | S23 (secondary) |
| B22 | MEGA | Sanity-check patches instead of authentication invite follow-up attacks. | S24 (secondary) |
| B23 | Nextcloud E2EE | Test empty and absent server answers. | S25 (secondary) |
| B24 | Harnik–Pinkas–Shulman-Peleg 2010 | Cross-user client-side dedup is itself a side channel. | S26 (secondary) |
| B25 | Proofs of Ownership / Dark Clouds | A hash is not proof of possession. | S27, S28 (secondary) |
| B26 | MLE 2013 | Deterministic, message-derived schemes are brute-forceable over predictable messages. | S29 (secondary) |
| B27 | DupLESS 2013 | Server-aided keys help only if the key server is trusted and online. | S30 (secondary) |
| B28 | Armknecht et al. 2017 | The leakage/efficiency trade-off of the oracle is inherent: remove it below a threshold. | S31 (secondary) |
| B29 | Liu–Asokan–Pinkas 2015 | Cross-user dedup without a key server via PAKE: more complexity than Reliquary needs. | S32 (secondary) |
| B30 | Invisible salamanders; partitioning oracles; key commitment | Multi-key settings need commitment; age's header MAC supplies it by reduction, if readers verify it. | S33–S35 (secondary) |
| B31 | 2025 CDC papers | Keyed chunker secrets leak; whole-file objects avoid the class. | S36, S37 (secondary) |
| B32 | Tarsnap 2011 post; Valsorda 2017 | Invariants in APIs; reviews are not audits. | S38, S39 (secondary) |
| B33 | WhatsApp E2EE backups; Apple ADP | Key-custody analogues for D2/OD-08. | S44, S45 (secondary) |

### Tools and libraries

| Name | Purpose | Licence | Maturity | Source |
|---|---|---|---|---|
| Go `filippo.io/age` | Homelab decrypt (hybrid PQ), reference | BSD-3-Clause (not re-checked) | v1.3.2, 2026-08-29 | S3 |
| Rust `age` | Existing crate (`tagpq`, no X-Wing) | MIT/Apache-2.0 (not re-checked) | 0.12.1, 2026-07-14, pre-1.0 | S4 |
| RustCrypto `ml-kem`, `x-wing`, `hpke` | Building the X-Wing stanza (encode and decode) | not checked | 0.3.2; 0.1.0 → 0.1.1 (2026-10-01, rejecting key type); 0.14.1 | crates.io; A2 C22 |
| `cctv-age` | age vectors, including hybrid | "allows this without attribution" | 0.2.0, 2025-12-08 | S5 |
| Wycheproof | Primitive vectors | not re-checked | main | S6 |
| Padmé `dedis/purb padding.go`; F3-S1 integer port (`spikes/F3-S1/padlib.py`) | Reference and cross-checked port | per repo | 0 mismatches in 405,243 values | S19, S48 |

## Attack → mitigation matrix (normative, Draft)

A1, A2, A3, B6, C1 and D1 must satisfy this matrix (PLAN F3). Status values:

- **Mitigated:** by the named SR or design element ("planned" where it is not built yet).
- **Accepted:** under the trust model, with an AR or AR candidate.
- **Open.**

SR, AR and T IDs are D1's (`docs/security/threat-model.md`). RT IDs are from F3-S3; RT-66…RT-68 are attacks the adversary skeptic raised, added in this version. Rows M-26…M-48 were added in the first synthesis pass; M-49…M-51 in this one.

| ID | Attack | Attacker | Mitigation | Status | Owner |
|---|---|---|---|---|---|
| M-01 | Cloud tests known files by plain hash | Cloud | Keyed IDs (ADR-0001 §2); no plain SHA-256 in the cloud (SR-26) | Mitigated | A1, C1 |
| M-02 | Confirmation-of-a-file through the presence answer (RT-10) | Compromised device | DR-F3-2 option C or D: no cross-person (C) or no (D) "present" answer below T_x, plus M-27…M-30. DO accounting is a burst guard and forensic trail only; record-first is forensic only. Residual (same person under C; ≥ T_x) → AR-06 narrowed | Open (DR-F3-2 / OD-04; F3-S2 FAIL for A and B) | A3, C1 |
| M-03 | Learn-the-remaining-information via the presence answer (RT-11) | Compromised device | As M-02 | Open (as M-02) | A3, C1 |
| M-04 | Leaked secret + cloud ID history → offline testing of every historical ID (RT-12, RT-64) | Device + cloud | SR-15; epoch rotation; short cloud-side ID retention; PQ-protected secret delivery (M-40) | Accepted (AR-06), reduced | A1, D2, C1 |
| M-05 | Exact-size fingerprinting of objects (RT-13, RT-15, RT-16) | Cloud, USB finder, network observer | Padmé before age; padded length in receipt, present-check, SR-24, multipart part layout and Content-Length | Open (DR-F3-1; provisional pass on public data) | A2, A3, C1 |
| M-06 | Timing, per-device volume, ID equality across devices, IPs (RT-17) | Cloud | None cheap | Accepted (AR-05) | D6 |
| M-07 | Forged object or record in a device's name (RT-18) | Cloud, other device | SR-03 device signatures inside the encryption; SR-14 | Mitigated (SR-14 open: D3, OD-05) | A2, D3 |
| M-08 | Object/record swap, cross-context substitution (RT-19) | Cloud | Record binds (dedup_id, sha256, size, header_mac); SR-04 | Mitigated (CE tests) | A2, A3 |
| M-09 | Replay, suppression, reordering of records (RT-03, RT-04, RT-47) | Cloud | SR-12; SR-13 sequence or checkpoint; SR-18 | Mitigated (planned; SR-13 design open) | A3 |
| M-10 | Drop, withhold, fake "committed" (RT-01, RT-02, RT-08) | Cloud | SR-05; SR-06; SR-18 | Mitigated for integrity; availability Accepted (AR-04) | A3, E3 |
| M-11 | Key substitution: homelab recipient, receipt key, device keys (RT-49, RT-50, RT-55) | Cloud | SR-02; SR-14; SR-16 | Mitigated except device keys (open, D3) | D3, A8 |
| M-12 | Downgrade: recipient type, format version, empty lists (RT-54) | Cloud | Recipient set only from the pinned bundle; no Worker-supplied versions; empty or absent = "not safe" | Mitigated (planned; NT-10, NT-11) | A2, B6, G2 |
| M-13 | Two recipients see different plaintexts (RT-20) | Malicious encryptor | Header MAC reduction (C3, secondary only) **if** every reader verifies the MAC first (NT-16); homelab post-decrypt SHA-256/HMAC check | Mitigated (planned; rests on reasoning plus an independent check) | A2 |
| M-14 | Linking old and new epoch IDs during rotation (RT-27, RT-65) | Cloud + old secret | Preferred: flush the cloud's ID history at rotation, then devices re-seed. Unlinkable push not shown achievable | Open, likely Accepted (AR-06) | A1, D2 |
| M-15 | HNDL on X25519 wraps of objects and records (RT-21, RT-45, RT-51) | Future quantum adversary | mlkem768x25519 only (OD-06) | Open (OD-06) | A2 |
| M-16 | Classical or scrypt stanza on a PQ object, voiding PQ (RT-22) | Design error, buggy or downgraded encoder | OD-08 recovery recipient PQ or none; the Rust Recipient returns the `postquantum` label; encoder refuses to mix (NT-02b); **homelab ingest rejects any stanza set ≠ the pinned PQ set** (NT-02c) | Open (OD-06, OD-08) | D2, A2, A3 |
| M-17 | Nonce or keystream reuse on resume (Tarsnap class) (RT-56) | Bug | CE release rule; mutation tests | Mitigated (CE); production review required | A2, G2 |
| M-18 | Nonce-state rollback via an OS backup restore (Borg class) (RT-57) | Bug or ops | State excluded from backups; hedged RNG | Mitigated (planned; NT-06) | B6, A2 |
| M-19 | Hash or probe record used as proof of possession (RT-44) | Device | A hit grants no read rights; a record accepted through a presence answer never confers restore rights; probe-suspect records flagged | Mitigated (planned) | A8, A3 |
| M-20 | CDC parameter recovery (RT-59) | Store observer | Whole-file objects in the cloud | Mitigated for v1; hand-off to A6 | A6 |
| M-21 | Truncated or extended object on restore or range read (RT-53, RT-60) | Cloud | Final-chunk check (CE §5.5); SR-16 | Mitigated | A8 |
| M-22 | Crafted headers, records, USB bundles against homelab parsers (RT-40, RT-46) | Cloud, device | SR-22; CCTV `stanza_*`/`header*`; fuzzing; USB mount hardening (read-only, nosuid/noexec, no automount, parse in a disposable VM) | Mitigated (planned; mount hardening unspecified: A4) | A2, A4, D4 |
| M-23 | Partitioning oracle against homelab identities (RT-58) | Cloud | Exact body-length checks; one identity; no password stanzas | Accepted (negligible; OD-17 candidate) | A2 |
| M-24 | Garbage or oversized uploads, claim squatting, leaked presigned URLs (RT-05, RT-32, RT-38, RT-39) | Device, internet | SR-07, SR-09, SR-10, SR-21, SR-24, BUD-ABUSE | Mitigated (cost bounded) | C1, C2 |
| M-25 | Rotation after a leak too costly (RT-26, RT-29) | Ops | Digest form: from device caches. Content form: homelab re-derivation in the BUD-AUDIT pass + device re-hash under BUD-HASH. A1 decides (DR-A1-1) | Mitigated (planned) under either construction | A1 |
| M-26 | Encrypted metadata-record length leaks path length, EXIF and sidecar presence (RT-14) | Cloud | Pad records to fixed size classes, or batch them (A2 §F6) | Open (A2, with DR-F3-1) | A2 |
| M-27 | "Present" answer relays another device's receipt: reveals holder device, time and record digest (C29) | Compromised device | Device-neutral answer: present/missing only, or a homelab-signed token over (dedup_id, padded size) | Open (A3, C1; with DR-F3-2) | A3, C1 |
| M-28 | Receipt or staging-deletion timing reveals prior presence (RT-35; F3-S2 C3L) | Compromised device | Below T_x, the same path and timing whether or not the content is stored (full upload, full verify, receipts on a fixed batch schedule); NT-15 | Open (A3, A6, C1) | A3, A6, C1 |
| M-29 | Claim-conflict answer as a cross-person oracle (RT-34) | Compromised device | Claims scoped like presence answers (per person under C; per device under D) | Open (A3, C1) | A3, C1 |
| M-30 | Per-person usage or quota display reveals dedup (RT-36) | Family member | Charge each person for their own uploads regardless of dedup | Open (C4, E3; OD-20) | C4, E3 |
| M-31 | Hash-cache tampering or corruption → file shown "safe" without upload: silent loss (RT-30). **P0** | Local malware, bug | "Safe" only when this device's own record for the file's current bytes has a receipt (SR-05); IDs recomputed from bytes read after the last observed change; cache entries MACed under a keystore key; random re-hash sampling with mismatch → alert. Residual: malware with the app's privileges can falsify the app → AR candidate | Open (B6, A1, E3) | B6, A1, E3 |
| M-32 | Hash cache read by a thief: SHA-256, IDs, locators, including deleted files (RT-31) | Device thief | Cache encrypted with an OS-keystore key; prune entries of deleted files after receipt (D6) | Open (B6, D6) | B6, D6 |
| M-33 | Dedup secret and device keys in OS cloud backups or synced keychains; identity cloned by a device-backup restore (RT-24, RT-25) | Apple/Google, ops | Non-backup, non-syncing, device-bound storage (per-platform verification in the B track); SR-13 fork detection | Open (B1, B2, D3) | B1, B2, D3 |
| M-34 | A compromised device discloses its own local files (RT-23) | Device compromise | Inherent | Accepted (new AR candidate for OD-17) | D1 |
| M-35 | Ransomware uploads encrypted copies: doubles the keep-forever store and shows a false "safe" (RT-42, T-23) | Device malware | Keep-forever retains old versions; mass-change detection and admin nudge; D4-S3 pause; BUD-ABUSE | Open (Wave 2: A3, E3, D4) | A3, E3, D4 |
| M-36 | Objectionable content uploaded under a stolen device identity and kept forever (RT-43) | Device thief | Attribution is device-level (AR candidate); admin quarantine and prune procedure under SR-20 | Open (D1, C8) | D1, C8 |
| M-37 | LAN-direct inbound listener reachable by any LAN device (RT-48) | LAN device | Device-key mutual authentication, the same parsers and limits, VLAN isolation; or do not build | Open (ADR-0037) | A4 |
| M-38 | Social-engineered cross-person restore (RT-52) | Family member | Restore only to the owning person's devices unless an admin override is logged | Open (A8, E7) | A8, E7 |
| M-39 | Malicious or frozen app update (RT-62, T-24). A malicious signed update is the worst case: every device hands over the family secret and its files, and becomes an unlimited oracle | Vendor compulsion, CI compromise | SR-29 (anti-rollback, freshness) for freeze and rollback. **Interim requirements F3 proposes to D5:** the offline signing key under D2's custody rules; an update transparency log checked by the client (precedent: Go age publishes Sigsum proofs for its pre-built binaries since v1.2.0, per `SIGSUM.md` in the v1.3.2 module, S51); staged rollout to one canary device first; residual as an explicit OD-17 AR candidate | Open (D5, Wave 2) | D5 |
| M-40 | HNDL on dedup-secret delivery (SR-15 sealed to a device key) and on restore staging to device keys (C24 rescoped) | Future quantum adversary | PQ device encryption keys, or secret delivery only by kit/USB; part of OD-06 | Open (OD-06; D2, D3, A8) | D2, D3, A8 |
| M-41 | Padded object unrecoverable when its metadata record is lost (break-glass) | Ops, loss | Frame the true length inside the encrypted payload; NT-13b | Open (A2, with DR-F3-1) | A2, D2 |
| M-42 | Worker-held secret leaks: full R2 read/write (RT-06) | Cloud compromise | SR-23 | Mitigated (planned) | C1 |
| M-43 | Rogue enrollment with a stolen or replayed invite: the new device gets the secret and becomes an oracle user (RT-28) | Outsider, family member | SR-14, SR-15; then bounded by M-02, and by M-50 for enrollment into another person's account | Open (SR-14 via OD-05; M-50) | D3 |
| M-44 | Dedup poisoning under another person's ID (RT-33) | Compromised device | SR-04, SR-06, SR-11 | Mitigated (planned) | A3 |
| M-45 | Worker IDOR on another device's upload ID or claim (RT-37) | Device | SR-07 | Mitigated (planned) | C1 |
| M-46 | Cloud serves an oversized object to the homelab (RT-41) | Cloud | SR-22, SR-24; abort the download past the signed padded size | Mitigated (planned) | A3, A6 |
| M-47 | Compromised ingest VM with an online key (RT-61) | Homelab compromise | Accepted under AR-08 (revisit at Gate A) | Accepted (AR-08 candidate) | D2, A6 |
| M-48 | Phishing-grade fake nudges (RT-63) | Cloud, outsider | SR-25 | Mitigated (planned) | E3, C3 |
| M-49 | Staged-object key = dedup ID: existence oracle (create-only 412, HEAD, multipart conflict) or overwrite race on another person's staged ciphertext (RT-66, adversary skeptic) | Compromised device | Below T_x (or always): per-upload staging keys (SR-07, OD-04), per-device claims, no cloud-exposed key existence by dedup ID; homelab dedups after decryption | Open (OD-04; C1, A3) | C1, A3 |
| M-50 | Insider enrolls their own device into another person's account through the ADR-0002 pairing code or QR, turning cross-person probing into same-person probing (RT-67, adversary skeptic) | Family member with brief physical access | Every enrollment notifies the account owner and the admin (email and existing devices); optional hold-off: a new device gets only its own receipts for a period. Needed under C and F, not under D | Open (D3, E5, E3; may need an owner decision because users must not touch configuration) | D3, E5, E3 |
| M-51 | Future forgery of Ed25519 device signatures undermines later re-verification of keep-forever provenance (RT-68, adversary skeptic) | Future quantum adversary | Verify signatures once at ingest and store the result under the homelab's own integrity chain (A7 fixity), so provenance never depends on re-verifying old signatures; hybrid or PQ signatures as a later-phase item | Open (A7, A2) | A7, A2 |

Also from F3-S3 (attacks that are mapped, but with gaps) are two items handed to their owners:

- **RT-07:** the least-privilege scope of the homelab's Cloudflare pull token is specified nowhere (C6, C1).
- **RT-46:** USB mount hardening (in M-22; A4).

## Negative tests and vectors required of G2 (normative, Draft)

| ID | Test | Vectors or method | Guards |
|---|---|---|---|
| NT-01 | The homelab decryptor and Reliquary's range reader pass all `cctv-age` decrypt vectors (skip armor and scrypt only if unused), including `stream_no_final*`, `stream_two_final_chunks*`, `stream_trailing_garbage_*`, `stream_last_chunk_empty` and `x25519_low_order` | CCTV (S5) | M-21, M-22 |
| NT-02a | Decrypt conformance against all CCTV `hybrid*` vectors, including `hybrid_low_order` (header failure) and `hybrid_not_canonical_*`. `hybrid_and_x25519` (`expect: success`) is listed as an **intentional policy deviation** wherever ingest rejects mixed headers | CCTV | M-15, M-16 |
| NT-02b | The Rust encoder refuses mixed or classical recipients; its X-Wing Recipient returns the `postquantum` label; its output decrypts with Go age ≥ 1.3.0 (round trip) | Unit + cross-implementation | M-16 |
| NT-02c | Homelab ingest rejects any object or record whose stanza types, count or set differ from the pinned recipient set (a fixture built from a mixed header) | Synthetic | M-16 |
| NT-03 | Header and STREAM round-trip on every non-failure vector; re-encrypting with the vector's file key reproduces the bytes | CCTV | CE encoder |
| NT-04 | Primitive vectors: HMAC-SHA256, HKDF-SHA256, ChaCha20-Poly1305, X25519 (all-zero shared secret aborts), Ed25519 (reject non-canonical and malleable signatures), ML-KEM-768 | Wycheproof (S6) | M-07, M-13 |
| NT-05 | Keystream reuse on resume aborts; mutation-kill tests stay in CI | CE harness | M-17 |
| NT-06 | A rolled-back journal does not re-release chunks under the old key | CE harness | M-18 |
| NT-07 | Object/record swap, cross-device record, wrong epoch, wrong size, padded-length mismatch: all rejected at ingest | Synthetic | M-08, M-05 |
| NT-08 | Replay, sequence gap, duplicate event: idempotent, gaps flagged; forked sequence from a cloned identity flagged | Synthetic | M-09, M-33 |
| NT-09 | Forged, tampered or wrong-key receipt; a receipt for another device's record | Synthetic | M-10 |
| NT-10 | Empty or absent receipt list, presence list or trust-bundle field → "not safe" | Synthetic Worker | M-12 |
| NT-11 | A Worker-offered recipient, extra stanza or version string is refused | Synthetic | M-11, M-12 |
| NT-12 | Presence: no cross-person (C) or no (D) answer below T_x; DO counters exact under concurrency; the F3-S2 attacker profiles replayed against the chosen option | F3-S2 harness, promoted to CI | M-02, M-03 |
| NT-13a | Padding: padded length ∈ Padmé(L); dedup ID and SHA-256 over unpadded content; ingest truncates by the signed and framed length | Unit | M-05 |
| NT-13b | A padded `.docx` and `.zip` restore byte-identical through the break-glass kit **with only the object and the identity** | Kit test | M-41 |
| NT-14 | Dedup-ID vectors across epochs and kinds (A1-S3); stale-epoch IDs rejected after the grace window | A1-S3 vectors | M-14, M-25 |
| NT-15 | Receipt latency and staging-deletion timing are statistically indistinguishable for new vs already-stored content below T_x | Timing harness | M-28 |
| NT-16 | Every Reliquary reader verifies the header MAC before using the file key (CCTV header and MAC tamper vectors) | CCTV | M-13 |
| NT-17 | A "present" answer and a claim-conflict answer carry no `device_id`, `committed_at` or other-device record digest | Synthetic | M-27, M-29 |
| NT-18 | A tampered hash-cache entry (ID of another receipted file) never yields "safe"; re-hash sampling flags it | B6 harness | M-31 |
| NT-19 | Device secrets are absent from OS backup and restore paths on each platform | Per-platform (B-track kit) | M-33 |
| NT-20 | Below T_x, no device-observable response (PUT, HEAD, multipart initiate, claim) differs by whether another device already staged or committed the same dedup ID | Synthetic Worker + R2 emulator; `[SB]` confirmation | M-49, M-29 |
| NT-21 | A new enrollment produces an owner and admin notification; under a hold-off, a newly enrolled device receives no "present" answer for IDs it has no receipt for | Synthetic | M-50 |

## Spikes

| Spike | Hypothesis | Pass → / fail → (decision) | Exec tag | Budget IDs | Data class | Status | Result |
|---|---|---|---|---|---|---|---|
| F3-S1 Size fingerprinting (public corpora) | More than 50 % of files have a unique exact size; Padmé removes this at under 3 % cost | Pass → Padmé in object v1 (DR-F3-1, ADR-0007); fail → AR-05 | CT | none (PLAN's local thresholds; BUD-CLOUD indirectly) | `PUB → results` | **Pass at per-device scale; mixed at family scale** (ran 2026-09-29) | Open Images 2018_04 (9,178,217 photos, 20.47 TB) and GovDocs1 (974,742 documents, 492.97 GB). Unique share: photos 99.62 % (10k), 96.58 % (100k), 75.29 % (1M), 51.87 % (3M), 45.06 % (4M), 26.44 % (all); documents 82.00 % (10k), 54.32 % (100k), 47.27 % (150k), 22.80 % (all). After Padmé: 0.09 % / 0.43 % at 10k, about 0 at ≥ 1M. Padmé cost 1.131 % / 1.145 % byte-weighted (per-file max 3.125 % for ≥ 64 KiB); 64 KiB buckets 1.466 % / **7.576 %**. Cross-check: 0 mismatches in 405,243 values. Evidence: `spikes/F3-S1/README.md` |
| F3-S1-owner | The owner library also has more than 50 % unique sizes, and Padmé costs < 3 % on its real mix | As F3-S1 | OL (kit) | none | `FAM → AGG` (H3 R3: never the size list) | **Kit-ready** | Standard-library script, aggregates only, small cells suppressed; rehearsed on a 25k-file synthetic tree. Kit: `docs/research/kits/F3-S1/README.md`. DR-F3-1 stays provisional until it runs |
| F3-S2 Dedup-oracle simulation | A compromised device probing 10k candidates needs > 30 days or is alerted | Pass → that presence design (DR-F3-2); fail → narrow further or accept AR-06 | CT (**emulated, not real Cloudflare**: Python simulation + Miniflare 4.20260730.0) | BUD-HASH, BUD-REVOKE, BUD-ABUSE, BUD-TTS | `SYN → results` (+ `PUB → results` priors) | **Fail** for ADR-0001 + SR-21-style limits; C3 passes cross-person only, by construction | C0 FAIL (≤ 1 h); C1 FAIL (2 h, no alert); C1s passes by time (30.04 d), but the first seed takes 172 d; C2 FAIL (mimic attacker uploads about 2 GB unseen; false alarms on document seeds); C3 PASS cross-person (P(learn) = 0 **by construction**: the simulator answers "missing"; conditional on M-27…M-30, M-49, M-50), FAIL same-person; C3L FAIL. The 20-candidate criterion and the C1s rejection are F3 additions (sign-off: open question 13). 20-candidate confirmation ≤ 1 h everywhere except C3 cross-person. DO: exact counts (20,939/20,939) and hard caps (5,000; 1,000), no over-grant. Evidence: `spikes/F3-S2/README.md`. **A sandbox `[SB]` re-run belongs to C1/C2** |
| F3-S3 Red team vs ADR-0001 + matrix | Every attack maps to a mitigation or an accepted risk | Pass → matrix feeds ADR-0007/0009; fail → new rows, SRs or ARs first | CT | none | `SYN → results` | **Fail** (run against the analyst matrix M-01…M-25) | 65 attacks: 36 MAPPED, 8 MAPPED-OPEN, 7 D1-ONLY, 14 UNMAPPED, 0 broken references. Evidence: `spikes/F3-S3/README.md`. **Re-check against this version** (scratchpad copy of `check.py`, references updated to M-26…M-48 and also reading `docs/security/threat-model.md`): see the result line below |

**F3-S3 re-check against this version** (2026-10-06, second synthesis pass). The scratchpad copy of `spikes/F3-S3/check.py` was run with `attacks.py` references updated to M-26…M-51 (and SR-29, T-23, T-24 where they apply), plus three attacks the adversary skeptic raised (RT-66 staging-key existence oracle, RT-67 enrollment into another person's account, RT-68 long-term signature forgery). It read both `d1-threat-model.md` and `docs/security/threat-model.md`, and parsed 51 matrix rows, SR-01…SR-31, AR-01…AR-09 and T-01…T-26 (note snapshot sha256 prefix `d22790d4b453c337`, taken before this paragraph was written).

- **Result:** 68 attacks: **43 MAPPED, 25 MAPPED-OPEN, 0 D1-ONLY, 0 UNMAPPED**, 0 broken references.
- **The 25 attacks that map only to Open rows:** RT-10, 11, 13, 14, 15, 21, 22, 24, 25, 27, 28, 30, 31, 34, 35, 36, 42, 43, 45, 48, 52, 62, 66, 67 and 68. RT-28 moved from MAPPED to MAPPED-OPEN because M-43 is now Open (it depends on M-50).
- **PLAN verdict: still FAIL.** The script's own verdict counts only unmapped attacks and printed "PASS". The PLAN criterion needs each attack mitigated or accepted, so MAPPED-OPEN does not count. F3-S3 passes once DR-F3-1, DR-F3-2, OD-04 (M-49), OD-06, OD-08, M-14 and the B6, D3, D5, A4, A7 and A8 rows close.
- **Caveats:** "MAPPED" means a row exists, not that anything is built. The mapping target is F3's own matrix, so the tally is self-graded; an independent re-map is requested (open question 14). The updated `attacks.py` stays in the scratchpad: changing `spikes/F3-S3/` is the spike runner's call.

## Skeptic issues and how they were addressed

| Issue (severity, lens) | Resolution |
|---|---|
| Recommendation ignores RT-30 silent loss (critical, sources) | Fixed: M-31 is P0 in Recommendation 5; NT-18; hand-off to B6/A1/E3 |
| DR-F3-2 rests on record-first and DO accounting (major, sources; K10 refuted) | Fixed: C14 withdrawn; B rejected as protection; record-first and DO accounting are forensic or burst guards only; DR-F3-2 = C at minimum, D preferred |
| "Throttling alone fails" from a mislabelled budget (major, sources and logic) | Fixed: C12 contested and unused; the statement is limited to uniform caps (measured); phase, credit, lifetime and USB budgets marked not simulated |
| Adopting A1's construction against settled text (major, sources and logic) | Fixed: C15 contested; no F3 verdict; input to DR-A1-1 only |
| PQ cost understated, scope too narrow (major, sources) | Fixed: C28 measured arithmetic (0.13–1.2 %); M-40 device keys; ADR-0003 hand-off to T1 |
| Mixed-stanza refusal on the wrong side (major, sources) | Fixed: M-16 ingest enforcement; NT-02a/b/c split; `hybrid_and_x25519` an intentional policy deviation |
| Structured payload stale vs note; D1 SR-21 encodes the withdrawn design (major, logic and adversary) | Fixed in this note and in the returned decision requests; SR-21/T-11 correction handed to D1 (F3 does not edit D1's register) |
| F3-S1 pass depends on N; threshold reinterpreted (major, logic; minor, sources and adversary) | Fixed: "pass per device, mixed at family scale, provisional"; byte-weighted cost stated as the basis; anonymity-set measure reported; owner-library kit before final |
| F3-S2 judged on added criteria; alternatives unsimulated (major, logic) | Fixed: criteria labelled as F3 additions for H1/owner sign-off (open question 13); conclusion limited to uniform caps; Wave 2 re-run scoped (open question 2) |
| Inconsistent framing with D1 on settled text (major, logic) | Fixed: one shared owner question (Conflicts #1, DR-F3-2); proposed to D1 in the hand-off |
| Randomised threshold not evaluated (major, logic) | Fixed: option G assessed analytically and rejected for v1 (§3, DR-F3-2) |
| PQ recommendation unconditional without a Rust path (major, logic) | Fixed: conditional on A2-S3, fallback stated (Recommendation 3) |
| Staging keys by dedup ID remain an oracle (major, adversary) | Fixed: M-49, RT-66, NT-20, Conflicts #6 |
| C3 "PASS" by construction (major, adversary) | Fixed: relabelled in §3, the Spikes table and the Summary; device-observable channels listed as conditions; NT-12 to replay against the full path |
| Insider enrollment bypasses per-person scope (major, adversary) | Fixed: M-50, RT-67, NT-21, Conflicts #7; M-43 re-opened |
| Compromised update channel without interim requirement (major, adversary) | Fixed: M-39 interim requirements for D5 (Sigsum precedent verified, S51) |
| Minor issues: key-commitment precondition; recovery constraint too narrow; Rust crate wording; person index in C; break-glass length; DO alert suppression; long-term signatures; self-graded F3-S3; budget IDs without values; external review phrasing | Fixed: NT-16; OD-08 lists `mlkem768p256tag` or no stanza; B3 corrected; C's cons list the index; M-41 and NT-13b; homelab-side authoritative counts (§3); M-51; independent re-map requested; thresholds marked proposed; review kept as a suggestion |
| Missed alternative: per-person dedup keys (all three) | Added as option F (§3, DR-F3-2); it changes settled text, so it is an owner question |
| Missed alternatives: homelab-gated answers, miss-volume and content-similarity detectors, keyed-PRF padding, short ID retention | Gated answers assessed (H, not protective); detectors added to the Wave 2 re-run; keyed-PRF padding stays "not evaluated"; ID retention remains a mitigation in M-04 (open question 10) |

## Conflicts with settled text

None is resolved here. Each goes to the owner.

1. **ADR-0001 §4 step 1 and CLAUDE.md "Deduplication: whole-file, across all users" / "the cross-user dedup index".** DR-F3-2 options C, D and E remove cross-user *upload-skip* below T_x. Storage dedup at the homelab is unchanged. Whether the settled line covers upload-skip or only storage is **the owner's reading to confirm, not a given**. D1 §7 reads option E as not conflicting; F3 earlier wrote "arguably conflicts". **Shared framing for the owner (F3 proposes it to D1):** in every option, storage dedup across all users is preserved at the homelab; what narrows is cross-user *upload-skip*. The single question is: *does the settled deduplication line cover upload-skip, or storage only?* → DR-F3-2, with OD-04.
2. **CLAUDE.md "Low resource impact (metered-network awareness)".** C, D and E re-upload small duplicates on phones. The cross-person and same-person duplicate byte share is unmeasured (E1/A9). → DR-F3-2 cost input.
3. **CLAUDE.md / ADR-0001 "HMAC(family secret, content)".** A1's digest form deviates. F3 provides input only (C15, contested). → DR-A1-1.
4. **CLAUDE.md "Restores … re-encrypting to the target device's own key".** With OD-06 = PQ extended to device keys (M-40), clients (including Android) need PQ *decryption*, which bears on ADR-0003. → OD-06 (A2) and A8/D3.
5. **ADR-0001 §4 (receipt and present-check content).** DR-F3-1 B changes the receipt and present-check size fields, and M-27 changes what a "present" answer carries. Both change formats proposed under OD-04 (one-way door: receipt format). → Decide them in the same owner decision.
6. **ADR-0001 §4 step 2 "objects are keyed by dedup ID so duplicate uploads are idempotent".** Under C, D and F this key namespace is itself a presence oracle and an overwrite race (M-49). D1 SR-07 already proposes per-upload staging keys under OD-04, so this joins that decision.
7. **ADR-0002 "Adding devices never requires the admin. Any enrolled device can show the QR or pairing code".** This lets an insider enroll into another person's account and bypass per-person scope (M-50). Enrollment *notification* does not need the admin to act, so it may fit the settled text; enrollment *approval* would not (OD-05). → D3, with OD-05.
8. **CLAUDE.md "Cross-user dedup uses HMAC(family secret, content)".** DR-F3-2 option F (per-person keys) changes the key. → DR-F3-2 with DR-A1-1.
9. **ADR-0001 §2 "the cloud cannot test for known files"** holds only while no secret has leaked. This is already being reworded under OD-04; AR-06 covers it.
10. **Not a text conflict, but an open risk to "data integrity over everything":** RT-30 / M-31 (silent loss through the hash cache) stays open until B6 designs the "safe" rule.

## Open questions

1. **T_x and the bandwidth cost of C/D/E/F.** This needs counts of cross-person and same-person cross-device duplicate files and bytes. **E1 (census, counts only) and A9; Wave 2.**
2. **Phase-based, credit-based, lifetime and USB-seeding presence budgets; options D and F; the miss-volume and homelab content-similarity detectors; the M-49/M-50 channels.** None was simulated. F3-S2 should be re-run with them in Wave 2 (F3), replaying attackers against the full Worker and homelab path rather than the simulator's answer function. Budgets cannot stop the 20-candidate confirmation, but they may bound the 10k case for C's same-person residual.
3. **Orphan and claim-abandon rates in real seeds**, which set the detector false-alarm rates. **B6/A3 pilot telemetry.**
4. **The F3-S1 owner-library leg** (kit ready). **Owner, before Gate A.**
5. **Rotation linkage (M-14):** flush vs re-key push. **A1 and D2, before Gate A.**
6. **Rust X-Wing interop and low-order rejection** (A2-S3), for both encode and decode (device restore). **A2, before Gate A.**
7. **Primary text of the blocked papers** (S20, S23–S37), RFC 2104 / the HMAC proofs, and NIST IR 8547. Until read, these claims stay secondary. **H1 (access route).**
8. **A primary statement on file-level key commitment** (C3), from the age authors or C2SP, and age issue #59 read in full. **H1 route; F3 follow-up.**
9. **Cryptomator, Tresorit and Ente/Cure53 audit checklists:** not reached. **F3 follow-up or D4.**
10. **How long the cloud keeps committed IDs** vs the cross-person hit rate (M-04). **C1 with A3.**
11. **SR-13 sequencing design** (per-record sequence numbers vs signed checkpoints; fork detection for cloned identities). **A3 and H4.**
12. **The family mean file size**, needed for the PQ and padding cost percentages. **E1 / F3-S1 owner leg.**
13. **Sign-off on F3-S2's added criteria** (the 20-candidate confirmation; rejecting caps by first-seed cost) and the hand-set thresholds (T_x, caps, alert levels) as `budgets.md` proposals. **H1, owner.**
14. **Independent re-mapping of F3-S3's MAPPED-OPEN attacks** (now 25: 22 plus RT-66…RT-68): the mapping target is F3's own matrix, so it is self-graded. **End-of-run critic or D1.**
15. **Whether enrollment notification (M-50) fits "users never touch configuration" and OD-05.** **D3, E5; owner if approval is wanted.**

## Recommendation

1. **Presence answer (DR-F3-2): choose C at minimum; prefer D if E1/A9 show the extra small-file uploads are affordable.**
   - C means no cross-person "present" below T_x. D means no "present" below T_x for anyone.
   - Both require M-27 (device-neutral answers), M-28 (receipt path independent of prior presence), M-29 (scoped claims), M-30 (dedup-blind usage) and M-49 (per-upload staging keys, no key existence by dedup ID). C also requires M-50 (enrollment notification).
   - C's pass is by construction and conditional on those rows; D is analytical. Neither rests on C14 (withdrawn) or C12 (contested).
   - Option F (per-person dedup keys) is the strongest cross-person defence, but it changes the settled ID construction. Offer it to the owner with DR-A1-1; F3 does not recommend it over D without bandwidth counts.
   - Keep exact DO accounting as a burst guard and forensic trail only.
   - **Option B is not an acceptable protective fallback:** F3-S2 shows it is detection-only and evadable.
   - Evidence: F3-S2 (emulated), C11 (verified). C14 is withdrawn.
2. **Padding (DR-F3-1): adopt Padmé in object format v1, provisionally.**
   - Zeros before age; IDs and SHA-256 over unpadded content.
   - **True length framed inside the encrypted payload.**
   - Padded length in every cloud-visible field; metadata records padded too.
   - Final once the F3-S1 owner leg runs. If that leg shows uniqueness of 50 % or less per device, choose A with an explicit AR-05 entry.
3. **PQ (evidence for A2's DR-A2-1 = OD-06): `mlkem768x25519` for all encryption keys,** covering homelab, recovery and **device keys** (M-40).
   - Corrected cost: 0.13–1.2 % per file (C28).
   - The homelab enforces a PQ-only stanza set at ingest (M-16).
   - The recovery recipient must be PQ or absent; never scrypt or classical (C4).
   - The skeleton may use the current X25519 encoder. PQ becomes a Gate A requirement, **conditional on A2-S3** (byte-compatible encode and decode against CCTV `hybrid*`, with low-order rejection). Fallback if A2-S3 fails: PQ at v1.1 with a re-wrap of existing objects, plus dedup-secret delivery only by kit or USB until then (M-40).
   - PQ device keys put PQ *decryption* on every client, including Android (and later iOS). That is an input to T1's ADR-0003.
4. **Dedup-ID construction: no F3 recommendation.** The comparison claim (C15) is contested, so F3 gives A1 trade-offs only: rotation is a cost difference, not a feasibility one, and the digest form makes hash lists and every device's hash cache testable after a leak (M-32). A1 decides under DR-A1-1, which is an owner question because both A1 forms differ from the settled "HMAC(family secret, content)".
5. **Treat M-31 (hash-cache → false "safe") as P0** for B6, A1 and E3 before Gate A. "Data integrity over everything" depends on it.
6. **G2 adopts NT-01…NT-21**, with CCTV and Wycheproof as mandatory vector sources and NT-02 split as above.
7. **Suggestion (not a decision request):** D4 and H2 to cost an informal external review of the object format and protocol before Gate A.

**What would change this:**

- If E1/A9 show cross-person small-file duplicates are a negligible share, D or even E becomes cheaper than C's person-to-ID index.
- If a re-run of F3-S2 shows a phase-based budget bounds same-person probing, C becomes a stronger fit.
- If the owner leg of F3-S1 shows low per-device uniqueness, padding moves to AR-05.
- If the Rust X-Wing path is not byte-compatible and does not reject low-order shares by Gate A, the choice is between PQ at v1.1 with a re-wrap and a Go or plugin path on devices.

## Decision requests

### DR-F3-2 (new, H1 to number; addition to OD-04): presence-query semantics
- **Needed by:** Wave 1 exit, together with OD-04.
- **Evidence:** §3, F3-S2 (emulated), C11, C29, C30; D1 SR-21, AR-06.
- **Options:**

  | Option | What it means for the family | Cost | Reversibility | Risks |
  |---|---|---|---|---|
  | A. Global + rate limits (as written) | Fastest seeding | Lowest | Easy | **F3-S2 FAIL**: a stolen phone tests family files in hours |
  | B. A + record-first + exact DO accounting | Same | One DO per device | Easy | **F3-S2 FAIL**: detection only, evaded by uploading misses; false alarms |
  | C. No cross-person "present" below T_x, + M-27…M-30 | Shared small files from other people re-upload (storage still deduped at home) | Extra upload (unmeasured); a person-to-ID index in the cloud | Easy (Worker rule) | Same-person and ≥ T_x residual (AR-06) |
  | D. No "present" below T_x for anyone, + M-27…M-30 | Small files always upload once per device | More extra upload (unmeasured), including between one person's own devices | Easy | ≥ T_x residual only; not simulated |
  | E. Homelab-only dedup, all sizes (D1's option) | Everything uploads once per device | Most upload | Easy | No cloud oracle |
  | F. Per-person dedup keys (HKDF(root, person_id)), + M-27…M-30, M-49, M-50 | Shared files from other people re-upload at every size (storage still deduped at home) | Extra upload (unmeasured), including large shared videos | **Hard**: changes the ID construction (one-way door #1) | Same-person residual; changes "HMAC(family secret, content)"; analytical only |
  | G. Randomised upload threshold (Harnik et al.) | Most shared files re-upload | Close to E | Easy | Residual boundary leak; per-ID counters; **F3 rejects for v1** |

- **Recommendation:** C at minimum; D preferred if E1/A9 bandwidth counts allow. A and B are not acceptable as protection. G is rejected.
  - C's pass is **by construction and conditional** on M-27…M-30, M-49 and M-50 (emulated, one side channel modelled). D's and F's merits are analytical.
  - F is the strongest option against *cross-person* probing and a leaked device secret. It must be decided with A1's DR-A1-1 before Gate A, because it changes the ID construction (a one-way door). If the owner wants it, A1 and F3 assess it in Wave 2 and re-run F3-S2 with it.
  - D is the only option that also closes same-person probing and the M-50 enrollment route below T_x.
- **Single owner question on settled text (shared framing with D1):** storage dedup across all users is preserved in every option; does the settled deduplication line also cover upload-skip?
- **Touches settled text:** ADR-0001 §4 steps 1 and 2 (M-49); ADR-0002 self-service enrollment (M-50, under C and F); option F changes "HMAC(family secret, content)"; and possibly CLAUDE.md "Deduplication: whole-file, across all users" / "cross-user dedup index" if those cover upload-skip. **The owner must confirm the reading.** Also in tension with "low resource impact (metered networks)".
- **If no decision by the deadline:** the skeleton runs E (devices skip only on their own receipts). It is the safest default, and moving to C or D later is a Worker-rule change.

### DR-F3-1 (new, H1 to number): size padding in object format v1
- **Needed by:** Gate A (one-way door #2; it also changes the receipt and present-check fields under OD-04).
- **Evidence:** §2, F3-S1 (public leg), C8, C10, C31.
- **Options:**

  | Option | What it means for the family | Cost | Reversibility | Risks |
  |---|---|---|---|---|
  | A. No padding | Nothing visible | 0 | New objects only; past uploads stay fingerprintable | AR-05 lists exact sizes |
  | B. Padmé, length framed inside the payload, padded length in all cloud-visible fields | Nothing visible | 1.13–1.15 % measured (public data) | Format version | Format and kit work |
  | C. 64 KiB buckets | Nothing visible | 7.58 % on documents (fails the cost leg) | Format version | Finer leakage for photos |

- **Recommendation:** B, provisional until the F3-S1 owner leg runs.
- **Touches settled text:** none directly. It changes the ADR-0001 §4 superseding formats (OD-04).
- **If no decision by the deadline:** A for the skeleton, with the field layout reserving the padded length and the length frame.

### OD-06 (evidence for A2's DR-A2-1; not a separate request)
- F3 supports **A: `mlkem768x25519` only, from the first real ingest**, and extends it to **device encryption keys** (M-40).
- Corrected cost: 0.13–1.2 % per file (C28).
- Mixing is excluded (C4). Ingest enforces it (M-16).
- The skeleton default stays X25519 until A2-S3 passes.

### OD-08 (constraint for D2; not a separate request)
- If OD-06 = A, the recovery recipient must be a PQ public key (`mlkem768x25519`, or `mlkem768p256tag` for hardware) or there must be no per-object recovery stanza.
- **Never** an scrypt stanza or a classical recipient on the object (C4).
- D2 and A2 choose where the stanza is written (DR-A2-2).

### OD-17 (additions)
- AR-05 lists exact sizes only if DR-F3-1 = A.
- AR-06 is narrowed per DR-F3-2's outcome. It covers offline testing of the cloud's ID history after a secret leak (bounded by rotation and M-14 flush) and the same-person and ≥ T_x residual under C.
- New accepted-risk candidates:
  - partitioning oracles negligible (M-23);
  - a compromised device discloses its own files (M-34);
  - malware with the app's privileges can falsify the app's "safe" (M-31 residual);
  - attribution is device-level, not person-level (M-36).

## Hand-offs

| To | What | Why |
|---|---|---|
| A1 | C15 as input (cost trade-off, hash-cache exposure); M-14 flush-vs-push analysis; M-25; NT-14; M-31 "ID from current bytes" | ADR-0006 |
| A2 | DR-F3-1 layout (in-payload length frame, padded records M-26); PQ for all encryption keys; NT-02a/b/c, NT-13, NT-16; Rust X-Wing encode **and** decode with low-order rejection; `tagpq` code as a starting point; pre-1.0 crate risk | ADR-0007 |
| A3 / C1 | DR-F3-2 (C/D/E), M-27 device-neutral answers, M-28 receipt independence (NT-15), M-29 claims, padded sizes in receipts, present-check, SR-24 and multipart; cloud ID retention; record-first as forensic only; probe-suspect flagging | ADR-0009, ADR-0010 |
| A6 | M-28 (homelab must not fast-path receipts for known content below T_x); M-46; CDC lesson | ADR-0012 |
| B6 / A1 / E3 | M-31 (P0), M-32, NT-18 | ADR-0021, ADR-0024 |
| B1 / B2 / D3 | M-33 (non-backup device secrets; clone detection), NT-19 | ADR-0017, ADR-0018, ADR-0014 |
| D1 | Matrix M-26…M-51 to reconcile with T-01…T-26; new AR candidates; RT-07 token scope. **Correction to SR-21 and T-11:** they still encode record-first plus admin alert and auto-suspend as the DR-F3-2 design. F3-S2 C2 shows that combination fails as protection. SR-21 should cite DR-F3-2 options C/D/F, with record-first, DO accounting and alerts as forensic or burst guards only. Also agree the shared owner framing on upload-skip (Conflicts #1). D1 edits its own register | Threat register |
| D2 / D3 / A8 | M-40 PQ device keys (SR-15 sealing, restore staging); OD-08 constraint; rotation re-wrap; break-glass with the in-payload length (NT-13b) | ADR-0008, ADR-0014, ADR-0028 |
| A4 | M-22 USB mount hardening; M-37 LAN-direct requirements | ADR-0011, ADR-0037 |
| A8 / E7 | M-38 restore authorization; M-19 probe records confer no restore rights | ADR-0028, ADR-0040 |
| C1 / A3 | M-49 per-upload staging keys and per-device claims (with OD-04 / SR-07); NT-20 | ADR-0009, ADR-0010 |
| D3 / E5 / E3 | M-50 enrollment notification and optional presence hold-off; NT-21 | ADR-0014, ADR-0038, ADR-0025 |
| A7 / A2 | M-51 verify-once-at-ingest, result under the fixity chain | ADR-0029, ADR-0007 |
| T1 | PQ decryption on all clients if device keys are PQ (M-40) | ADR-0003 |
| C4 / E3 | M-30 dedup-blind usage display (OD-20) | ADR-0024 |
| D5 | M-39 malicious signed update: interim requirements (key custody, client-checked transparency log, canary rollout, AR candidate) | ADR-0015 |
| E1 / A9 | Counts of cross-person and same-person cross-device duplicates (files and bytes); family mean file size | DR-F3-2, C28 |
| G2 | NT-01…NT-21; CCTV and Wycheproof as required sources; NT-02a lists `hybrid_and_x25519` as an intentional policy deviation | ADR-0035 |
| H1 | Blocked sources (Method); DR-F3-1/2 numbering; OD-06 evidence attached to DR-A2-1; OD-08 constraint attached to D2; F3-S2's added criteria and hand-set thresholds (T_x, caps, alert levels) as `budgets.md` proposals | Registries |
| D4 / H2 | Suggestion: cost an informal external review before Gate A | Valsorda lesson |
| F3 (Wave 2) | Re-run F3-S2 with options D and F, phase, credit and lifetime budgets, USB seeding, the miss-volume and content-similarity detectors, and the M-49/M-50 channels, against the full Worker and homelab path; `[SB]` confirmation with C1 | Open question 2 |
| End-of-run critic / D1 | Independent re-mapping of F3-S3's MAPPED-OPEN attacks | Open question 14 |
