# A6. Homelab at-rest posture, storage engine and catalog

- **Workstream:** A6 (see `docs/research/PLAN.md`, section "A6.")
- **Status:** Final for Wave 1 (batch W1-b). Three analyst passes, three skeptic lenses (sources, logic, adversary) and two spike-runner passes are merged here. The bake-off (A6-S2) and the catalog (ADR-0013) are Wave 2.
- **Date:** 2026-09-29 (last updated 2026-10-06, Wave 1 synthesis)
- **Wave 1 scope:** the at-rest posture (OD-07, one-way door #4) and the knockout screen of storage engines, for the ADR-0012 draft. Only the bake-off kit is written now. The catalog engine is not trivially decided, so it stays in Wave 2 (§F7).
- **Feeds:** [ADR-0012 (Proposed)](../adr/0012-homelab-at-rest-posture-and-storage-engine.md); OD-07; one-way door #4; decision requests DR-A6-1 to DR-A6-4 (H1 assigns OD numbers). Evidence for OD-06 (PQ readers), OD-08 (recovery recipient), OD-13 (read-only gallery) and OD-17 (accepted risks).
- **Depends on:** the CE spike (`content-encryption-format.md`, also T1 spike 2); A1 (the store is addressed by plain SHA-256); A2 (`a2-object-envelope.md`, `docs/spec/object-format.md`); A3 (durable-commit contract F6); D1 (`docs/security/threat-model.md`: SR-04, SR-20, AR-07, AR-08); D2 (`d2-key-hierarchy-custody-recovery.md`, Proposed ADR-0008); C5 (hardware, filesystem); owner intake answers C1, C3, C5, C6 and C12 (not yet given).
- **Traceability rows advanced:** R-09, R-26, R-28, R-38, R-45, R-46, OPEN-2, Q1-1 (see `docs/research/traceability.md`)

## Summary

1. **The posture choice is narrower than the plan assumed.** The ingest design in hand (CE §11, A3 F6, SR-04) decrypts every object to verify it before commit. So, **as long as SR-04 stands**, a key that can decrypt incoming objects is online at ingest in every posture (C1, verified). The real choices are which key that is, what else it can open, which operations need a key, and what a stolen box or a compromised ingest VM exposes. A design that verifies only in attended batches would remove the online key, but it breaks SR-04's receipts and BUD-TTS, so it is listed and rejected (§F1).
2. **Recommended posture, for the owner to decide (OD-07): A′, "keep the received age payload, rewrap the header at ingest".** Each stored object stays a standard age v1 file. At ingest the homelab rewrites only the header, to an offline archive recipient X (plus R if OD-08 accepts it). The online ingest key I_e then protects only data in transit and rotates by epoch. The review forced three amendments, and the recommendation holds only with them:
   - **The device header h0 is never kept in the clear.** The earlier draft kept h0 in the manifest. With h0 and I_e, every object of a still-open epoch decrypts (A6-S6 measured 176/176). So h0 is sealed to {X, R} (ADR-0008 Decision 6).
   - **The rewrapped header is checked without X at write time, and with X in attended samples.** Nothing online can open the stored header. A keyless audit therefore proves only that the bytes have not changed since they were written, not that X can open them (C14 is **contested**).
   - **A′ protects stored content bytes of retired epochs, not metadata.** The plaintext catalog, and any derivative kept in the clear, are as exposed as under posture A. They need their own encrypted dataset.
3. **What A′ buys, stated narrowly.** Under A′ the always-on key cannot open stored content of retired epochs, and neither can someone holding the disks (A6-S1 Probe 2, A6-S6). Scrubs, bit-rot audits and future off-site copies need no key. These keyless properties are **not** unique to A′: posture A has them too, and restic (posture C) can be bit-rot-checked without a key (A6-S1 Probe 3). The costs: restores, catalog rebuilds, real-object restore drills and rewrap verification need the archive key brought online by the owner, and the ingest key must rotate.
4. **Knockout screen: none of the screened backup engines passes.** restic/rustic, Kopia, Borg 2, PBS, Plakar/Kloset, bupstash and git-annex each fail at least one criterion with a verified primary source (C4–C9). Using restic only as a container for A′ ciphertext still fails restore-by-hash and per-file ingest (§F4). The screen is **incomplete**: Perkeep, Duplicacy, duplicity, rdedup, Bareos/Bacula, Tahoe-LAFS and self-hosted S3 stores (Garage, MinIO, SeaweedFS) were not screened. The format that does pass is age v1 per object, in a **plain content-addressed store on ZFS** with a one-page layout spec. OCFL 1.1 is an optional wrapper. Wave 2 bakes off plain CAS, OCFL and a restic comparator (A6-S2 kit).
5. **Confidence:** High on the knockout facts. Medium on A′ with the amendments: the mechanics are measured in a container (A6-S1, A6-S6), but the sealed-h0 form and the write-time self-check are not built or measured yet. Low on scale numbers, where only arithmetic exists.

## Questions

| # | Question | Short answer | Confidence |
|---|---|---|---|
| 1 | Posture: must the private key be online for ingest and for scrubs? | **Ingest: yes, in every posture, given SR-04** (C1). Scrubs: a ZFS scrub never needs keys, even on native encryption, in every released OpenZFS up to 2.4.4. The opt-in "thorough" scrub that needs keys is on master only (C10). **Bit-rot audit of stored bytes:** keyless under A and A′, keyless at file level under restic (A6-S1 Probe 3), and needs the dataset key under B or the password (or an external hash list) under Kopia. **Proof that X can open the stored object:** needs X under A′ (C14 contested; §F2). | High (facts); Medium (A′ design) |
| 2 | Unattended unlock after a power cut | Under A′ only I_e must come up unattended; ADR-0008 proposes clevis/Tang into tmpfs. I_e still opens current-epoch objects still in staging and future uploads until rotation. Under A, B and C the auto-loaded key reads everything. ZFS `keylocation` can be `prompt`, `file://`, `https://` or `http://` (C11). The catalog dataset key also has to auto-load, or the catalog is offline after every power cut. The mechanism belongs to C5/D2. | High (options); Medium (ranking) |
| 3 | Derivative generation | Derivatives need plaintext. Under A′ they can be made at ingest, but **a derivative stored in the clear, or on a dataset whose key auto-loads, is a visual copy of the archive** that a thief or a compromised VM can read. So under A′ a kept derivative is either encrypted to {X, R} like the originals, or kept on the catalog's encrypted dataset and listed as exposed under that dataset's unlock. Under B: at any time. Under C: through the engine with the password. Whether derivatives are kept at all is OD-16 (A7). | Medium |
| 4 | Cost of adding a recovery recipient later | A header rewrap, not a payload re-encryption (C2, verified). It still rewrites every byte of a one-file-per-object store, because the header is at the front. A6-S1 Probe 1 measured this: payload unchanged 535/535, all 229.56 MB rewritten, and re-encryption took about 1.5× the CPU time of a rewrap on tmpfs. Avoid it by writing {X, R} at ingest from day one. A passphrase (scrypt) stanza must be the only stanza (C3, verified), so R must be an X25519, `mlkem768x25519` or tagged identity. A passphrase can still protect R's *identity file*, as ADR-0008 does. | High (spec, measured); Medium (I/O extrapolation) |
| 5 | What a stolen box exposes | See the corrected §F1 matrix. Under A′ with h0 sealed: no stored content, unless I_e is on the box, in which case current-epoch objects still in staging or on USB are exposed. Also exposed: exact plaintext sizes and file presence from plain-SHA-256 names (A6-S1 Probe 4: 535/535 sizes, 50/50 presence checks), plus the catalog and any clear derivatives unless their dataset key stays off the box. Under A, B and C: everything, if the key or password auto-loads from the box. ZFS never encrypts file sizes, dataset or snapshot names, or dedup tables (C10). | Medium |
| 6 | Can an heir read it? | Under A and A′: yes, with stock age, the archive (or recovery) identity and a catalog export or the decrypted records. If OD-06 = PQ, the only **CLI** reader today is Go age ≥ 1.3 (C30). Two library readers, typage 0.3.1 and kage 0.8.0, pass the CCTV hybrid vectors (A2-S3), so the doomsday kit should carry Go age and one non-Go reader. Under B: OpenZFS on Linux plus the passphrase. Under C: restic or rustic plus the password. | Medium |
| 7 | Optional read-only Immich/PhotoPrism view | Needs plaintext on disk. B allows it through a generated read-only tree. A and A′ need a decrypted mirror, which brings back an online read key and gives up A′'s benefit. Never let Immich own or move originals: #30919 reports thousands of missing or renamed files after a storage-template migration (secondary). OD-13 and C8 decide whether any view exists. | Medium |
| 8 | Knockout criteria | K1 library-driven per-file ingest keyed by our ID; K2 specified format with an independent reader; K3 single-file restore by hash; K4 licence (G3); K5 fit with *a* posture the owner might pick (judged against all four); K6 maturity (from CLAUDE.md "proven"). For the build-our-own candidates, K1 and K6 are n/a, and substitute evidence is named (§F4). | High |
| 9 | Snapshot engines vs continuous per-file ingest at 3–5M objects, 10 TB, +1–2 TB/yr | A plain CAS needs no engine index: the path is the hash and the catalog is the index. restic holds its index in RAM, with OOM reports around 2M files on 1 GB machines (C15, secondary). A full read of 10 TB (decimal) is at least 27.8 h at 100 MB/s, or 9.3 h at 300 MB/s (C19, arithmetic, a sequential lower bound). Per-file seeks on HDDs and the monthly ZFS scrub, which reads the same bytes again, add to it. A6-S2 measures MB/s **and files/s**. | Low (numbers); Medium (shape) |
| 10 | Readability without Reliquary: browsable tree vs opaque packs | A CAS of whole age files is not browsable, but each object is self-contained and opens with stock age. Packs (restic, Kopia, Borg, Kloset) need the engine or a reimplementation. A browsable tree can be generated from the catalog. | High |
| 11 | Catalog: Postgres vs SQLite | **Open; Wave 2 (ADR-0013).** It must also screen the PLAN alternative "event log with projections", which the manifest-plus-rebuild design already resembles (A6-S4). Requirements fixed now: §F7. | n/a |
| 12 | Admin-only pruning with cross-user dedup | A blob is deletable only when no live item from any person references it. The refcount is derived from catalog sightings and never stored alone. Deletion goes through a separately credentialed, verify-before-destroy admin step (SR-20). Store immutability against the ingest credentials is §F8. Details: ADR-0013. | Medium |
| 13 | Keep a future off-site copy easy | Under A and A′, copy the ciphertext files as they are (rclone, rsync, non-raw `zfs send`). Under B, raw `zfs send -w` (bug history, C12, secondary) or rclone crypt. Under C, `restic copy`. | Medium-high |
| 14 | Do plain-SHA-256 file names leak anything? | Yes, to someone holding the disks: file presence (A6-S1 Probe 4, 50/50). The cloud never sees these names. Options are in DR-A6-3, including naming files by the SHA-256 of their stored (ciphertext) bytes. | High (measured) |
| 15 | Is the prototype's "decrypt to a temp file" needed? | Not under A or A′. Ingest can verify SHA-256 and HMAC by streaming and store the ciphertext it already has. | Medium |
| 16 | (new, review) Can A′ verify the rewrapped header at ingest without X? | Not by decryption. It can check, without X, that the written header has the right shape and stanza types, that its MAC verifies under the in-memory file key, that the bytes on disk read back equal what was written, and that each stanza is a correct wrap to the **pinned** X and R public keys (by recomputing it with an independent encoder from the same per-stanza randomness). It cannot prove that the holder of X still has the matching private key. An attended, sampled X-unwrap pass closes that gap (§F3). | Medium (design, not built) |
| 17 | (new, review) Does A′ protect the homelab store from a compromised ingest VM or ransomware writing to it? | No. The posture is about confidentiality. Integrity against an attacker who can write to the store needs write-once objects, held snapshots and an off-box anchor (§F8). | Medium |

## Method

- **Sweep:** three scouts (docs, source, community), then three analyst passes (2026-09-29 deep read; 2026-09-29 reconciliation with the A2 and D2 drafts; 2026-10-06 re-verification of the load-bearing sources and reconciliation with the Proposed ADR-0008 and prior-run spikes).
- **Skeptic review (2026-10-06):** three lenses (sources, logic, adversary) reviewed 13 key claims. The claim tally was computed in code: **verified** = a primary source exists and at least 2 of 3 skeptics did not refute it; **secondary only** = no primary source; **contested** = otherwise. Every critical and major issue is answered in [Review response](#review-response).
- **Synthesis checks (2026-10-06):** two skeptic findings were re-fetched before use:
  - Kopia `repo/hashing/blake_hashes.go` and `hashing.go` (master);
  - OpenZFS `META` and `zpool-scrub.8` at the `zfs-2.4.4` tag (no "thorough"; `zfs-2.4.5` returned 404).
- **Spikes:** the spike runner ran A6-S1, A6-S3, A6-S4, A6-S5 and A6-S6 in the container, and wrote kits for A6-S1-B, A6-S2 and A6-S3-OL (§Spikes).
- **Routes used:** raw.githubusercontent.com (vendor docs and source mirrors); static.crates.io and the crates.io API; PyPI JSON; proxy.golang.org; registry.npmjs.org (A2); WebFetch of github.com issue and release pages (skeptics, scouts).
- **Blocked sources.** None was silently replaced. Each is reported to H1:
  - restic.readthedocs.io and restic.net (mirror `restic/restic @ master : doc/` used);
  - kopia.io (mirror `kopia/kopia @ master : site/content/docs` used);
  - ocfl.io (mirror `OCFL/spec` used);
  - openzfs.github.io (man pages used instead);
  - c2sp.org (editor's copy `C2SP/C2SP @ main : age.md` used);
  - docs.immich.app;
  - pbs.proxmox.com, pve.proxmox.com, www.proxmox.com, forum.proxmox.com, git.proxmox.com (proxy 403 and WebFetch `EGRESS_BLOCKED`): the only PBS source is the GitHub mirror, stale at 3.2.4;
  - git-annex.branchable.com (git-annex is secondary only);
  - forum.restic.net, forum.duplicati.com (snippets only);
  - www.sqlite.org, www.postgresql.org (catalog facts not gathered; Wave 2);
  - rustic.cli.rs; hn.algolia.com; reddit.com;
  - api.github.com for restic/restic (`gh api` 403: "GitHub access to this repository is not enabled"), so #187 was read through a summarising WebFetch and #533 only through search results;
  - perkeep.org (Perkeep: **no result**).
- **Stop rule:** the third pass and the skeptic re-reads added two primary facts (Kopia's keyed BLAKE2 registry; the 2.4.1–2.4.4 ZFS tags). Neither changes a knockout. No further sweep was run for the Wave 1 scope.

## Sources

| # | Source (title and URL or mirror path) | Publisher | Published or version date | Accessed | Primary? |
|---|---|---|---|---|---|
| S1 | `CLAUDE.md`; ADR-0001 `docs/adr/0001-cloud-staging-on-r2.md` | Project | Accepted | 2026-09-29 | Yes (settled text) |
| S2 | CE spike `docs/research/content-encryption-format.md` §§1, 5.5, 11, 12, 16 | Project (T1 spike 2) | 2026-09-29 | 2026-09-29 | Yes (project spike) |
| S3 | A3 `a3-ingest-protocol.md` F6; A1 `a1-content-identity.md`; D1 `d1-threat-model.md` and `docs/security/threat-model.md` (SR-04, SR-20, AR-07, AR-08, TB4); F1 `f1-build-adopt-fork-compose.md` | Project | 2026-09-29 / 2026-10-06 | 2026-10-06 | Yes (project drafts) |
| S4 | restic design, `restic/restic @ master : doc/design.rst` | restic | master head | 2026-10-06 (re-read) | Yes |
| S5 | restic "Working with repositories", `… : doc/045_working_with_repos.rst` | restic | master head | 2026-09-29 | Yes |
| S6 | restic "Backing up" and "Restoring", `… : doc/040_backup.rst`, `doc/050_restore.rst` | restic | master head | 2026-09-29 | Yes |
| S7 | rest-server README, `restic/rest-server @ master : README.md` | restic | master head | 2026-10-06 | Yes |
| S8 | restic latest version, proxy.golang.org `github.com/restic/restic/@latest` | Go module proxy | v0.19.1, 2026-07-05 | 2026-09-29 | Yes |
| S9 | rustic README, `rustic-rs/rustic @ main : README.md` | rustic-rs | main head | 2026-09-29 | Yes |
| S10 | rustic_core 0.13.0 crate: `README.md`, `Cargo.toml`, `src/repofile/configfile.rs`, `src/repository/credentials.rs`, `src/repository.rs` (static.crates.io) | rustic-rs | 0.13.0, updated 2026-08-16 | 2026-10-06 | Yes |
| S11 | C2SP age v1 spec, `C2SP/C2SP @ main : age.md` (editor's copy of c2sp.org/age) | C2SP | main head | 2026-10-06 (re-read) | Yes |
| S12 | OpenZFS `zfs-load-key(8)`, `zfsprops(7)`, `zfs-send(8)`, `zpool-scrub(8)`, `META`, `openzfs/zfs @ master : man/…` | OpenZFS | master = 2.4.99; `zfs-load-key.8` .Dd 2026-01-30 | 2026-10-06 | Yes |
| S13 | OpenZFS `zpool-scrub(8)` and `META` at tags `zfs-2.4.0` and `zfs-2.4.4` (2.4.1–2.4.3 checked by skeptics) | OpenZFS | 2.4.4 is the newest tag found; `zfs-2.4.5` 404 | 2026-10-06 | Yes |
| S14 | OCFL 1.1 spec, `OCFL/spec @ main : 1.1/spec/index.md` | OCFL editors | 2022-10-07, updated 2024-11-07 | 2026-09-29 | Yes |
| S15 | OCFL extension 0004, `OCFL/extensions @ main : docs/0004-hashed-n-tuple-storage-layout.md` | OCFL community | extensions v1.0 | 2026-09-29 | Yes |
| S16 | rocfl (crates.io API), ocfl-py (PyPI JSON) | crates.io, PyPI | rocfl 1.7.0 (2022-10-08); ocfl-py 2.1.0 (2026-06-26) | 2026-09-29 | Yes |
| S17 | Kopia docs: Architecture, Encryption, ECC, `kopia/kopia @ master : site/content/docs/Advanced/…` | Kopia | master head | 2026-10-06 | Yes |
| S18 | Kopia `repo/hashing/sha_hashes.go`, `blake_hashes.go`, `hashing.go` (master); Kopia v0.23.1 module source | Kopia | master; v0.23.1 2026-06-15 | 2026-10-06 | Yes |
| S19 | Borg README, `borgbackup/borg @ master : README.rst`; `docs/internals/data-structures.rst` (scout) | BorgBackup | master head | 2026-10-06 | Yes |
| S20 | PyPI `borgbackup` JSON | PyPI | 1.4.5 (2026-07-18T22:38Z); 2.0.0b25 (2026-09-27T22:57Z) | 2026-10-06 | Yes |
| S21 | PBS `proxmox/proxmox-backup @ master : docs/technical-overview.rst`, `pbs-tools/src/crypt_config.rs`, `docs/backup-client.rst` (scout), `debian/changelog`, `debian/copyright` | Proxmox | GitHub mirror, top changelog entry 3.2.4-1 | 2026-10-06 | Yes (stale mirror) |
| S22 | bupstash README, `andrewchambers/bupstash @ master : README.md`; 0.12.0 crate source | bupstash | 0.12.0, 2022-11-07 | 2026-10-06 | Yes |
| S23 | Kloset README, `PlakarKorp/kloset @ main : README.md`; proxy.golang.org kloset `@latest` | Plakar | v1.1.8, 2026-09-24 | 2026-09-29 | Yes |
| S24 | Immich storage template, `immich-app/immich @ main : docs/docs/partials/_storage-template.md` | Immich | main head | 2026-09-29 | Yes |
| S25 | OpenZFS #12014, PR #17340, openzfs-docs #494 (github.com, scout) | OpenZFS community | 2021-05-08 → 2025-05-20; 2024-02-12 | 2026-09-29 | No |
| S26 | openzfsonosx/openzfs-fork #104 (search-result title only) | community | unknown | 2026-09-29 | No |
| S27 | restic #1988, #2523 (github.com, scout); forum.restic.net thread 8758 (snippet) | restic community | 2018-09-07; 2019-12-20 | 2026-09-29 | No |
| S28 | Kopia #5049, #4769, #4348, PR #4839 (github.com, scout) | Kopia community | 2025 | 2026-09-29 | No |
| S29 | Plakar releases page, https://github.com/PlakarKorp/plakar/releases (WebFetch) | Plakar (vendor) | v1.1.0 2026-06-05 … v1.1.7 2026-09-24 | 2026-10-06 | **Yes** (vendor's own release notes; relabelled after skeptic review) |
| S30 | Immich #30919, #29627 (github.com, scout) | Immich community | 2026-08-22; 2026-07-06 | 2026-09-29 | No |
| S31 | restic #533 (search results only) | restic community | unknown | 2026-09-29 | No |
| S32 | Duplicati forum threads 7591, 9291; duplicati #4923 (snippets) | community | unknown | 2026-09-29 | No |
| S33 | git-annex backends page (search snippet) | git-annex | unknown | 2026-09-29 | No |
| S34 | Rust `age` 0.12.1 and `age-core` 0.12.0 crate source (static.crates.io) | str4d / rage | age 0.12.1, 2026-07-14 | 2026-09-29 | Yes |
| S35 | A2 `a2-object-envelope.md` (C5, C6, C9, C21, C25, C29, A2-S3) and `docs/spec/object-format.md` (§5 `stored-v1`, `h0_sha256`, §6.1 hedged derivation); D2 `d2-key-hierarchy-custody-recovery.md` | Project | 2026-10-06 | 2026-10-06 | Yes (project drafts) |
| S36 | restic issue #187 "Support asymmetric backups", https://github.com/restic/restic/issues/187 (summarising WebFetch) | restic tracker | opened 2015-05-14; open | 2026-10-06 | Partly (corroborates S4; never sole support) |
| S37 | ADR-0008 `docs/adr/0008-key-hierarchy-custody-recovery.md`, Decisions 1, 5, 6, 8 | Project (D2) | Proposed, 2026-10-06 | 2026-10-06 | Yes (Proposed, not Accepted) |
| S38 | Spike READMEs and evidence: `spikes/A6-S1`, `A6-S3`, `A6-S4`, `A6-S5`, `A6-S6`, `spikes/D2-S2`, `spikes/A2-S3`; kits `docs/research/kits/A6-S1`, `A6-S2`, `A6-S3` | Project (spike runners) | 2026-10-06 | 2026-10-06 | Yes (container measurements, synthetic data) |
| S39 | PBS `debian/copyright`; Kloset `LICENSE`; bupstash 0.12.0 `Cargo.toml` | Proxmox; Plakar; bupstash | mirror master; main; 0.12.0 | 2026-10-06 | Yes |

## Claims

Verdicts follow the computed claim tally exactly. The thirteen reviewed key claims (K1–K13) map to the C-numbers below. Claims outside that set were **not skeptic-reviewed**. They are marked as such and are not used as the sole support of any recommendation.

| # | Claim | Sources | Key? | Skeptic 1 (sources) | Skeptic 2 (logic) | Skeptic 3 (adversary) | Verdict |
|---|---|---|---|---|---|---|---|
| C1 (K1) | Under the current ingest design (verify-before-commit decrypts the whole object), a private key able to decrypt incoming objects is online at ingest in every posture. The posture only decides what that key can decrypt and which other operations need a key. | S2 §11, S3 (SR-04, A3 F6) | Yes | Upheld; depends on SR-04 | Upheld as a conditional | Upheld | **Verified** (conditional on SR-04) |
| C2 (K2) | age v1: every stanza wraps the same 128-bit file key; header MAC key = HKDF(file key, "header"); payload key = HKDF(file key, nonce, "payload"). Adding or replacing recipients is a header rewrite that needs the file key, and the payload stays valid. | S11 | Yes | Upheld (lines 60, 98, 121, 153) | Upheld | Upheld; A6-S1 and A6-S6 agree | **Verified** |
| C3 (K3) | An scrypt stanza MUST be the only stanza in a header, so a passphrase recovery *stanza* cannot sit next to X. | S11 | Yes | Upheld (lines 339–343) | Upheld; a passphrase-wrapped R *identity file* is still possible | Upheld; same caveat | **Verified** |
| C4 (K4) | restic encrypts the whole repository with one symmetric master key (AES-256-CTR + Poly1305-AES) unlocked by a password; any writer can decrypt everything; the master key changes only by moving to a new repository. | S4 | Yes | Upheld | Upheld | Upheld | **Verified** |
| C25 (K4) | restic #187 "Support asymmetric backups" has been open since 2015-05-14. | S36, S4 | Yes | Upheld (WebFetch summary; not the main source) | Upheld | Upheld | **Verified** (as corroboration of C4) |
| C5 (K5) | restic splits files over 512 KiB into CDC blobs of 512 KiB–8 MiB, identified per blob, so a whole-file SHA-256 is not a native lookup key. Ingest is snapshot-scoped in the CLI and in rustic_core 0.13.0 (`Repository::backup`, `archive`). | S4, S6, S10 | Yes | Upheld | Upheld; lower-level packer APIs not checked | Upheld | **Verified** |
| C6 (K6) | Kopia content IDs are keyed: the SHA-family registry has only HMAC variants, **and** (added at review) `blake_hashes.go` registers BLAKE2S/BLAKE2B through `truncatedKeyedHashFuncFactory`, `hashing.go` "encapsulates all keyed hashing algorithms", and the default is `BLAKE2B-256-128`. No independent reader was found (absence of evidence). | S18 | Yes | Upheld; BLAKE2 point added | Upheld; K2 knockout weaker than K3 | Upheld; BLAKE2 point added | **Verified** |
| C7 (K7) | Borg 2 README: "DO NOT USE BORG2 FOR YOUR PRODUCTION BACKUPS". PyPI: 2.0.0b25 uploaded 2026-09-27T22:57Z; latest stable 1.4.5, uploaded 2026-07-18T22:38Z. | S19, S20 | Yes | Upheld | Upheld | Upheld; time-sensitive | **Verified** (re-check before ADR-0012 is accepted) |
| C28 (K7) | Same facts; resolves the scouts' 07-18/07-19 conflict. | S19, S20 | Yes | (as C7) | (as C7) | (as C7) | **Verified** |
| C10 (K8) | ZFS native encryption leaves dataset and snapshot names, properties, file sizes, holes and dedup tables unencrypted; encrypted datasets can be scrubbed and resilvered without keys; `change-key` does not overwrite the old wrapped master key. The keyed "thorough" scrub is on master (2.4.99) only. It is absent from tags 2.4.0 to 2.4.4 (citation updated after review). | S12, S13 | Yes | Upheld; cite 2.4.4 | Upheld | Upheld; cite 2.4.4 | **Verified** |
| C14 (K9) | Under A and A′, a keyless SHA-256 over the stored bytes, compared with the digest recorded at ingest, is complete integrity evidence for the plaintext. | S2 §11, S11 | Yes | **Refuted** for A′: h1 is written after verification and never opened | **Refuted** for A′ | **Refuted** for A′; also not tamper evidence | **Contested.** Restated as C14r below |
| C14r | (restated after review, **not re-reviewed**) Under A, a keyless stored-bytes audit is complete integrity evidence, because the stored bytes are the bytes ingest decrypted. Under A′ it proves only that the bytes have not changed since they were written. Recoverability also needs a verified rewrap (§F3). Under neither posture is it tamper evidence against someone who can rewrite both object and manifest (§F8). | S2, S11, S38 (A6-S6) | Yes | — | — | — | Not reviewed (narrower than C14; inference) |
| C30 (K10) | Prior-run A6-S5 (container, synthetic): with `mlkem768x25519` stanzas, Go age 1.3.1 decrypted 176/176; Debian age 1.1.1 and rage 0.12.1 0/176. Go age refuses to mix PQ and X25519 recipients in one file. | S38 (A6-S5) | Yes | Upheld; Go age is now v1.3.2; typage untested | Upheld; the refusal applies to the label-enforcing path | Upheld; **the inference "no second reader" is overstated**: typage 0.3.1 and kage 0.8.0 pass CCTV hybrid vectors (A2-S3) | **Verified** (the measured facts). The inference is withdrawn: "one CLI reader; at least two library readers" |
| C29 (K11) | ADR-0008 escrows ingest keys to {X, R} rather than destroying them; A′'s property still holds because the escrow opens only with offline keys. | S37 | Yes | **Refuted on detail:** escrow is at creation; the sealed escrow stays online | Upheld; reword | Upheld; the property holds for retired epochs only | **Verified** (1 refute, 2 upheld), **reworded:** each I_e is sealed to {X, R} *at creation* into the online bundle, which is copied off-box at epoch start. Plaintext online copies are deleted after the drain bound. The sealed bundle stays online and opens only with X or R. |
| C19 (K12) | A full read of 10 TB takes about 27.8 h at 100 MB/s and 9.3 h at 300 MB/s, far inside a 720 h month. | arithmetic | Yes | Upheld; decimal TB; per-file overhead ignored | Upheld; even 20 MB/s (139 h) fits | Upheld; add the ZFS scrub's second read | **Secondary only** (no primary source). Used only as a feasibility hint; A6-S2 must measure it |
| C9 (K13) | bupstash is self-described beta, recommended only for redundant backups; last release 0.12.0 on 2022-11-07 (MIT). | S22, S39 | Yes | Upheld | Upheld | Upheld | **Verified** |
| C17 (K13) | Plakar/Kloset 1.1.x exists only since 2026-06-05, and behaviour changed within the minor series (1.1.5 plaintext refusal; 1.1.6 auth-flow cut-off). | S29 | Yes | Upheld; the release page is vendor-primary | Upheld | Upheld; not load-bearing (Kloset also fails K2) | **Verified** |
| C8 (K13) | PBS: the server checks only CRC-32 for encrypted chunks. PBS is AGPL-3.0-or-later. The mirror is stale at 3.2.4, so 4.x is unverified. | S21, S39 | Yes | Upheld; the CRC-only limit follows from the keyed digest (C24) | Upheld | Upheld | **Verified** (for the mirror's version; 4.x unverified) |
| C11 | ZFS `keylocation` is `prompt`, `file://`, `https://` or `http://`; `zfs send -w` sends encrypted datasets without loaded keys. | S12 | No (posture B only) | — | — | — | Not reviewed |
| C12 | Native encryption plus send/recv has a bug history (#12014, PR #17340); a macOS-port title reports raw-send corruption on 2.4.x. | S25, S26 | No | — | — | — | Secondary only |
| C13 | OCFL 1.1: sha512 or sha256 addressing; no links; immutable versions; one-version object = 6 files in 3 directories; ext 0004 maps IDs to hashed paths. The a6cas prototype and the A6-S2 kit use ext 0003 instead. | S14, S15, S38 | No (bake-off variant) | — | — | — | Not reviewed |
| C15 | restic index in RAM; #1988 OOM at ~2M files on 1 GB. | S27 | No | — | — | — | Secondary only |
| C16 | rustic_core 0.13.0 API is "in an early development stage"; opens only with password or master key; supports a `FixedSize` chunker. | S10 | No | — | — | — | Not reviewed |
| C18 | Kopia restore regression (#5049) and an open maintenance report (#4769). | S28 | No | — | — | — | Secondary only |
| C20 | A Rust header rewrap can use public `age` 0.12.1 APIs (`unwrap_stanza`, `wrap_file_key`, `FileKey: ExposeSecret`) plus about one screen of Reliquary header code; the parser and MAC are private. | S34 | No (build feasibility) | — | — | — | Not reviewed. The Go equivalent is measured (A6-S6) |
| C21 | Under A′ with PQ, the stored {X, R} header is 3,184 B; sealing h0 adds an age file around h0, so the stored overhead is several KB per object, well under 1 % at a mean object size of about 1 MB. | S35, S38 | No (cost) | — | — | — | Not reviewed (the sealed-h0 size is not measured) |
| C22 | A restore done as a header rewrap leaves the R2-staged payload byte-identical to the original upload, so the cloud could link the two; fresh re-encryption avoids it. | S11, S35 | No (A8 input) | — | — | — | Not reviewed |
| C23 | rest-server `--append-only` and `--private-repos`; same layout locally and remotely. | S7 | No | — | — | — | Not reviewed |
| C24 | PBS encrypted-chunk digest = SHA-256(data ‖ id_key), id_key from PBKDF2. | S21 | No | — | — | — | Not reviewed |
| C26 | Licences: restic BSD-2; Kopia Apache-2.0 (scout); Borg BSD-3 (scout); rustic_core Apache-2.0 OR MIT; Kloset ISC-style; bupstash MIT; PBS AGPL (C8). | S39, S4, S10, S17, S19 | Yes (K4) | (PBS and bupstash parts reviewed via K13) | — | — | Partly verified (PBS, bupstash); rest not reviewed |
| C27 | Kopia's ECC is "currently experimental". | S17 | No | — | — | — | Not reviewed |
| C31 | (spike, measured) Under A and A′, a holder of the disks derives exact plaintext size for 535/535 objects and confirms presence of 50/50 known files from plain-SHA-256 names. | S38 (A6-S1 Probe 4) | No (DR-A6-3) | — | — | — | Measured (container, synthetic); not reviewed |
| C32 | (spike, measured) With h0 kept in the clear, h0 + stored payload + I_e decrypts every current-epoch object (176/176). With only the stored file, I_e decrypts 0/535. | S38 (A6-S6 row 6; A6-S1 Probe 2) | Yes (A′ property) | — | — | — | Measured; raised by the logic and adversary skeptics; drives amendment 1 |

## Findings

### F1. What the posture decides (corrected after review)

**Premise (C1, verified, conditional on SR-04).** The homelab decrypts every object, recomputes SHA-256 and HMAC, commits only on a match, and signs a receipt. So a key that opens incoming objects is online whenever ingest runs. Two designs avoid that, and neither is recommended:

- **Attended batch verification:** devices encrypt directly to X, and the homelab stores ciphertext and verifies and issues receipts only when the owner brings X online. **Rejected:** "stored at home" receipts would wait for the owner, which breaks BUD-TTS (24 h) and the A3 receipt contract, and unverified ciphertext would sit in the keep-forever store. It is listed so that C1 is not read as a law of nature.
- **Isolated verifier:** I_e is held only by a minimal, network-isolated verifier VM, or in a non-exportable TPM or HSM. That VM decrypts, verifies and rewraps, and hands ciphertext to a separate storage writer. **Recommended as a hardening direction** (ADR-0012 Decision 6): it narrows AR-08 without changing the posture. D1 and D4 decide it in Wave 2, and D2 owns the TPM/HSM option (ADR-0008 excludes only the vTPM, and the YubiKey under PQ).

**Corrected matrix.** "A′" means A′ with the review amendments: h0 sealed to {X, R}, a write-time self-check, and an attended X audit (§F3).

| Consequence | A: keep received ciphertext (one homelab key) | **A′: rewrap header to offline X (+R); I_e rotates; h0 sealed** | B: plaintext CAS on ZFS native encryption | C: re-encrypt into restic/Kopia/PBS |
|---|---|---|---|---|
| Key online for ingest | Homelab identity; opens **everything ever stored** | I_e of open epochs; opens objects encrypted to those epochs **while they are in staging or on USB**, not stored objects | Homelab age identity (everything) **and** the ZFS key | Homelab age identity **and** the repository password (everything) |
| ZFS scrub | No key | No key | No key (C10) | No key |
| Bit-rot audit of stored bytes | No key (C14r) | No key (C14r) | Dataset key loaded | restic: **no key** at file level (A6-S1 Probe 3); Kopia: password or an external hash list |
| Proof the stored object opens | Ingest proved it for these exact bytes | **Needs X:** write-time self-check without X, plus attended sampled X unwrap (§F3) | Dataset key | Password (`check --read-data`) |
| Unattended unlock after a power cut | Read-everything key auto-loads | I_e auto-loads (in-transit only) **and** the catalog dataset key, if the catalog must be online | ZFS key via `file://` or `https://` (C11); read-everything | Password on the box; read-everything |
| Stolen box: stored content | Everything, if the key auto-loads from the box | Nothing (C32 with h0 sealed; **sealed form not yet measured**, A6-S7) | Everything, if `keylocation=file` is on the box | Everything, if the password is on the box |
| Stolen box: in-transit objects | (as above) | Open-epoch objects in staging/USB, if I_e is on the box | (as above) | (as above) |
| Stolen box: metadata | Catalog, unless on a dataset whose key is off the box | **Same as A.** Plus sizes and file presence from names (C31) | Sizes, dataset and snapshot names (C10) | Catalog as for A |
| Stolen box: derivatives | Same as the catalog | **Same as the catalog**, unless encrypted to {X, R} | Readable with the dataset key | Inside the engine |
| Compromised ingest VM: new uploads | Everything until cleaned up | Everything until cleaned up (it holds I_e and sees plaintext) | Same | Same |
| Compromised ingest VM: stored content | Everything | **Retired and current epochs: nothing**, if h0 is sealed and the VM cannot read the R2 copies. Open epochs plus cloud-retained ciphertext: readable | Everything it can read | Everything (C4) |
| Compromised ingest or catalog VM: metadata | Everything | **Everything:** the catalog is online plaintext. A′ does not protect metadata | Everything | Everything |
| Compromised ingest VM: integrity of the store | Can rewrite or delete unless the store is write-once (§F8) | Same | Same | Same |
| Adding a recovery recipient later | Rewrap of every object; whole store rewritten (A6-S1 Probe 1) | Added at ingest from day one; changing later costs the same as A | `change-key` (kit A6-S1-B P5); old wrapped keys stay on disk (C10) | `restic key add`: 2.98 s, one key file (Probe 3), but another read-everything secret |
| Derivatives | Need the key | At ingest (see the derivatives rows) or with X | Any time | Through the engine |
| Read-only Immich/PhotoPrism view | Decrypted mirror (online key) | Decrypted mirror, which gives up A′'s benefit | Generated tree | `restic mount` with the password |
| Heir access | `age` + identity + catalog export | `age` + X or R + catalog export (PQ: Go age CLI or a library reader, C30) | OpenZFS-capable Linux + passphrase | restic/rustic + password |
| Off-site copy later | Copy the files | Copy the files | `zfs send -w` (C11, C12) or rclone crypt | `restic copy` |
| Restore drills on real objects | Unattended possible | **Attended** (X needed). Unattended drills can use only canary objects with a drill stanza (§F3) | Unattended possible | Unattended with the password |
| Device-signed provenance kept | Byte-identical to the upload | Payload identical. h0 sealed to {X, R} lets the owner rebuild the exact upload with X (A6-S6) | Record only | Record only |

**Finding (Medium).** A′ is the posture in which neither the always-on key nor the disks reveal **stored content** of retired epochs. That holds only if h0 is sealed. The keyless properties (scrub, bit-rot audit, off-site copy) are shared with A, and partly with restic, so they are not a reason to prefer A′ over A. The reason is confidentiality. Its costs:

- the owner brings X online for restores, catalog rebuilds, real-object drills and X audits;
- I_e rotates (ADR-0008: yearly by default);
- a plaintext gallery becomes a deliberate exception (OD-13);
- A′ does nothing for metadata or derivatives, which need the catalog's own encrypted dataset;
- it does nothing for integrity against an attacker who can write to the store (§F8).

Prior art for the shape: bupstash put-only keys and the PBS offline RSA `master-pubkey` (S21, S22). Both keep the reading key off the always-on machine.

### F2. Fixity under each posture (C14 contested; restated as C14r)

- At ingest, record `stored_sha256 = SHA-256(stored bytes)` in the catalog and in the append-only manifest inside the store, so the store can be audited without the catalog.
- **Under A** a keyless audit is complete integrity evidence: the stored bytes are exactly the bytes ingest decrypted and verified.
- **Under A′** the stored header h1 ({X, R} stanzas plus a new MAC) is written after verification, and nothing online can open it. A keyless audit therefore proves only that **the bytes have not changed since they were written**. A rewrap bug, a wrong or substituted X public key, a mixed-profile header or a RAM bit flip between verification and write would be recorded in `stored_sha256` and pass every later audit. Recoverability needs the checks in §F3.
- **Under no posture** is `stored_sha256` tamper evidence. It sits on the same box as the objects, so someone who can write the store can rewrite both. That is §F8.
- Under restic, the keyless check is `sha256sum` of each file against its name (A6-S1 Probe 3; design.rst). Under B it is `sha256sum` of the plaintext with the dataset mounted.
- Audit duration: C19 (secondary only, arithmetic) says a sequential read of 10 TB fits a month by a wide margin. It ignores per-file seeks across 3–5M objects and the ZFS scrub's own read of the same disks. A6-S2 records MB/s and files/s, and A7 sets the cadence (BUD-AUDIT).

### F3. A′ mechanics (proposal for ADR-0012; A2 and D2 must agree)

1. The device encrypts to the ingest recipient of epoch e, I_e, published in the signed trust bundle (ADR-0008 Decision 4). The header shape is checked before any unwrap (ADR-0008 Decision 6; `object-format.md` §5).
2. The homelab verifies as in CE §11 and `object-format.md` (including `h0_sha256`), streaming, with no plaintext temp file.
3. The homelab writes the stored object: a `stored-v1` header with exactly {X, R} (uniform profile, both PQ or both X25519), the MAC recomputed from the file key, then the payload bytes unchanged. The result is a standard age v1 file (C2; A6-S6: 176/176 open with X and R, 0/176 with I_e).
4. **h0 is sealed, not kept in the clear (amendment 1).** The device header h0 is age-encrypted to {X, R} as its own small sealed blob, referenced from the manifest line. The signed record already carries `h0_sha256` and `header_mac` (`object-format.md` §5), so the manifest also keeps `h0_sha256` in the clear for keyless cross-checks. Reasons:
   - with h0 in the clear, h0 + stored payload + I_e opens every object of an open epoch (C32), and ADR-0008 sets a yearly epoch plus the drain bound;
   - this meets ADR-0008 Decision 6 ("h0 sealed to X");
   - with X, the owner can still rebuild the exact upload bytes and re-check the device signature (A6-S6);
   - it gives a **second, independent path to the file key** (sealed h0 + the escrowed I_e). If a rewrap defect corrupts h1, the object is still recoverable. That path uses only stock age encryption, not Reliquary's header code.

   Metadata records get the same treatment. The sealed form's exposure has not been measured: A6-S7 (CT, proposed) re-runs A6-S1 Probe 2 with the manifest and sealed h0 included.
5. **Write-time self-check without X (amendment 2).** Before the ACK, the homelab:
   - re-reads the written file from disk and checks that its header parses, has exactly the `stored-v1` stanza set, and that its MAC verifies under the in-memory file key;
   - checks that the payload read back hashes to the value expected from the upload;
   - checks that X and R in the trust bundle match the fingerprints pinned at the offline ceremony (A-signed bundle; a substitution then needs Tier-0 key A);
   - recomputes each stanza with a second, independent encoder from the same per-stanza encapsulation randomness and compares the bytes. This follows the hedged-derivation approach of `object-format.md` §6.1. It proves a correct wrap to the pinned public key, not that X's private half still exists.

   The record gets the state `rewrap_selfchecked`. This is not built yet; G2 owns the test.
6. **Attended X audit (amendment 2, continued).** Each time the owner brings X online (restore session, rebuild, rotation, real-key check), an X-unwrap pass runs over a random sample of objects committed since the last pass, plus every object not yet sampled once it is old enough. Each passing object moves to `x_verified`. A failure stops ingest and alerts. Until an epoch's objects are sampled, the sealed I_e escrow and sealed h0 are kept: they are the fallback. The sample size and cadence go to A7 (ADR-0029) and D2 (ADR-0008 Decision 8, which already has an R-stanza audit). **This replaces ADR-0008's wording "verify X decryption of every rewrapped header", which A′ cannot do online. DR-A6-4 asks D2 and the owner to accept the replacement.**
7. **Rotate** I_e (interval: D2; ADR-0008 says yearly). Under A′ with sealed h0, the epoch interval no longer sets the stored-archive exposure. It still sets how long a captured I_e opens cloud-retained ciphertext and future uploads, so a shorter interval, or rotation triggered by staging drain, is a D2 question (hand-off).
8. **Escrow (C29, reworded).** Each I_e is sealed to {X, R} at creation into the online bundle, which is copied off-box at epoch start. Plaintext online copies are deleted after the drain bound. The sealed bundle stays online and opens only with X or R. AR-07 (objects staged before the bundle copy leaves the box) remains ADR-0008's residual gap.
9. **The age rule "file key MUST NOT be reused across multiple files"** (age.md line 62). After the rewrap, the stored file (h1 + payload) and the device upload (h0 + payload) share a file key and payload nonce. A rewrap restore (C22) would make a third. No new plaintext is ever encrypted under that key and nonce: the payload is byte-identical. So the intent of the rule (no two different encryptions under one key and nonce) is respected, and the stanza-level rule in `object-format.md` §6.1 is not touched. This reasoning goes into the A2/D2 rewrap test-vector review. It is an inference, not reviewed.
10. **Derivatives under A′:** never stored in the clear outside the catalog's encrypted dataset; either encrypted to {X, R} or kept on that dataset and listed as exposed under its unlock.
11. **Throughput:** the container showed single-threaded ingest under 100 MB/s (A6-S2 smoke: 76.6 MB/s on tmpfs, not budget evidence), and PQ decapsulation and the rewrap add cost. BUD-INGEST will probably need parallel verify and rewrap. That is a design requirement for A3 and the ingest service, and a watch item for A6-S2.

### F4. Knockout screen (re-scoped after review)

Criteria: K1 library-driven per-file ingest keyed by our ID; K2 specified format with an independent reader; K3 single-file restore by hash; K4 licence (G3; AGPL flagged, not failed); K5 fit with **any** posture A, A′, B or C; K6 maturity ("proven"). For build-our-own candidates, K1 and K6 are **n/a**. The substitute evidence is the one-page spec, the crash and rebuild results (A6-S3: 0 violations over 400 kills, 130 emulated power cuts and 100 disk-full trials; A6-S4: byte-identical rebuilds) and the Wave 2 OL kits.

| Candidate | K1 | K2 | K3 | K4 | K5 | K6 | Result |
|---|---|---|---|---|---|---|---|
| **Plain CAS of age v1 objects on ZFS** (our layout) | n/a (we write it) | **Objects pass:** age v1 is a C2SP spec with independent readers (A6-S5: age 1.1.1, age 1.3.1 and rage 0.12.1 read X25519 objects 176/176). **PQ caveat:** one CLI reader (Go age ≥ 1.3) plus library readers typage and kage (C30, A2-S3). Layout: one-page spec | Pass: path = hash (A6-S2 smoke: max 0.012 s) | Pass | A, A′, B | n/a; substitute evidence A6-S3/S4 | **Survives** |
| **OCFL 1.1 storage root** | n/a | Spec plus ocfl-py (2026) and rocfl (stale) (C13) | Pass (object ID = SHA-256) | Pass | A, A′, B | Spec stable; Rust tooling stale | **Survives** (variant) |
| **restic format, plaintext in (posture C)** | Partial: snapshot-scoped (C5) | Pass: design.rst, two implementations; A6-S5 cross-read 176/176 | **Fail natively** (C5) | Pass | C only (C4, C25) | restic mature; rustic 0.x | **Comparator only** |
| **restic as a container for A′ ciphertext** (review) | Partial: snapshot-scoped | Pass | **Fail natively:** needs our hash → snapshot/path map | Pass | A′ passes: restic's key then protects only ciphertext | Mature | **Knocked out on K3.** Adds a second password to the heir path, and gains nothing from dedup or compression on random ciphertext (inference). Worth adding to A6-S2 as a mode, so the cost is measured, not assumed (hand-off) |
| Kopia | Partial: Go library | Fail: no independent reader found (C6) | Fail: keyed, per-block IDs (C6) | Pass | C; container mode also fails K3 | 0.23.1 | Knocked out |
| Borg 2 | Fail: CLI | No independent reader seen | Fail: keyed chunk IDs | Pass | C | **Fail** (C7) | Knocked out |
| Borg 1.4 | Fail | as above | Fail | Pass | C | Stable | Knocked out on K1/K3 |
| Proxmox Backup Server | Fail: pxar streams | Fail: one implementation | Fail natively | AGPL (C8) | Weak: CRC-only verify of encrypted chunks (C8) | Stable; mirror stale | Knocked out as the engine; **keep for VM-level backups of catalog and service VMs** |
| Plakar / Kloset | Partial: Go library | Fail: no format spec found | Fail: MAC-addressed | Pass | C | **Fail:** 1.1.x since 2026-06, behaviour changes in minor releases (C17) | Knocked out; re-screen in 2027 |
| bupstash | Partial | Fail: one implementation | Fail: keyed chunks | Pass (MIT) | Nearest to A′ | **Fail:** beta; last release 2022-11 (C9) | Knocked out; borrow the key model |
| git-annex | Fail: Haskell CLI | Documented (secondary) | Pass (secondary) | AGPL/GPL (secondary) | Plaintext only | Mature | Knocked out on K1 |
| Perkeep, Duplicacy, duplicity, rdedup, Bareos/Bacula, Tahoe-LAFS | — | — | — | — | — | — | **Not screened: no result.** Wave 2 adds one-line knockout rows from primary sources |
| Self-hosted S3 stores (Garage, MinIO, SeaweedFS) as the **substrate** for the age CAS | — | — | — | — | — | — | **Not screened.** It is a substrate question (versioning or object lock instead of a ZFS tree), not an engine. Wave 2, with §F8 |

**Finding (High on the facts; Medium on the reading of "proven").** None of the **screened** engines passes K1–K6. The CLAUDE.md preference for "an existing, proven format over inventing one" is met at the object level by age v1 and optionally at the layout level by OCFL 1.1, not by a backup engine. The owner confirms this reading (DR-A6-2). The screen is incomplete for the candidates listed as not screened. None of them is known to pass, but that is absence of evidence.

### F5. Scale (Low: no homelab measurements)

- **Index RAM:** a plain CAS and OCFL need no engine index. restic loads its index into RAM (C15, secondary). The A6-S2 smoke run showed CAS 20.6 MB and restic 162 MB peak RSS on 229 MB of synthetic data. That is not budget evidence.
- **Snapshots:** restic per-file ingest means batching files into each snapshot, and every restore by hash then needs our map (C5).
- **Verify cost:** disk-bound in every design (C19, secondary only). Sampled audits: restic `--read-data-subset`, Borg 2 least-recently-checked; for a CAS, audit in `stored_sha256` order, one n-th per run.
- **Ingest rate:** see §F3 item 11.

### F6. Readability, browsable views and the catalog's exposure

- A browsable tree can be generated from the catalog without moving originals (e.g. `Person/Year/Year-Month-Day/<name>`). Immich must never own or move originals (#30919, secondary). Any Immich view is an external library over a generated read-only tree. That mode is **unverified** and goes to C8 for OD-13.
- **The catalog is plaintext** (ADR-0001 §2): names, paths, dates and perhaps GPS. Under A′ it is the main thing a thief **or a compromised online VM** can read. It and its WAL and backups live on an encrypted dataset, but that dataset must be unlocked for the catalog to work, so it protects against offline theft only if its key is not on the box. The mechanism goes to C5/D2.

### F7. Catalog (ADR-0013, Wave 2): requirements fixed by this note

The catalog must:

- store the plain SHA-256 of every item, plus `stored_sha256`, the epoch, the recipient set and the rewrap state (`rewrap_selfchecked`, `x_verified`);
- keep sightings per (person, device, source locator), so refcounts for pruning are derived (SR-20);
- store ingest events, receipts, restore jobs and audit results;
- be rebuildable from the archived records plus the manifest. A6-S4: byte-identical. A files-only rebuild loses epoch, `committed_at` and `meta_sha256`, so the manifest is archival data;
- check that it has disk headroom before ingest starts (A6-S3 disk-full lesson).

ADR-0013 screens Postgres, SQLite and an event log with projections, using its own sources.

### F8. Store integrity against a compromised writer (new, from the adversary review)

CLAUDE.md's "devices can only append" is enforced in the cloud. ADR-0012 needs the same at home, because SR-20 ("nothing a device or the cloud sends can delete or rewrite data in the homelab store") and AR-08 (compromised ingest VM) are open. Proposals, all to be confirmed in Wave 2 with D4-S4:

- **Write-once objects:** after commit, files are read-only to the ingest credentials (separate dataset permissions, or the immutable attribute). Only a separately credentialed prune step can remove them (SR-20).
- **Frequent ZFS snapshots with `zfs hold`**, released only with a separate admin credential. A ransomware or rewrite event is then rolled back to the last snapshot.
- **Read-only audit VM:** the keyless audit runs with read-only access, separate from the writer.
- **Off-box anchor for the manifest:** a hash-chained manifest whose head is signed and published outside the box. Candidates are the Worker and the receipts devices already hold. An attacker who rewrites objects and manifest lines together is then detectable. Not designed yet.
- **Fault case:** "attacker rewrites an object and its manifest line" is added to A6-S3 or A7-S1 in Wave 2.

### History of passes (condensed)

- **Second pass (A2/D2 reconciliation):**
  - stored headers are always homelab-written {X, R};
  - device recipient placement (P1 vs P2) only changes when I_e may be retired (DR-A2-2, A6 accepts either);
  - Rust rewrap feasible with public `age` APIs (C20);
  - restore-by-rewrap linkability goes to A8 (C22).
- **Third pass (scout conflicts):** seven conflicts were resolved against primary text, and none changed a knockout:
  - restic storage IDs are SHA-256 of the stored bytes;
  - Kopia IDs are keyed (now including BLAKE2);
  - the PBS digest is SHA-256(data ‖ id_key);
  - Borg 1.4.5 was uploaded 2026-07-18T22:38Z;
  - bupstash is MIT;
  - the thorough scrub is master only;
  - PBS 4.x stays secondary.
- **Review pass (this version):** see [Review response](#review-response).

### Alternatives compared

| Option | Fit with settled requirements | Pros | Cons | Evidence |
|---|---|---|---|---|
| **A′ (amended) + plain CAS of age objects on ZFS** (recommended) | Fits. A settled-text reading must be confirmed (see Conflicts) | Stored content of retired epochs unreadable by online keys or a thief; heir needs only age; keyless scrubs, bit-rot audits and copies; no engine index; payload = device upload | New layout code; key rotation; attended restores, drills and X audits; rewrap verification needs design (§F3); metadata not protected; names leak presence (DR-A6-3) | C1, C2, C3, C10, C29, C32; A6-S1, S3, S4, S5, S6 |
| A″: re-encrypt at ingest under a fresh file key to {X, R} | Fits | Stored payload unlinkable to R2-retained ciphertext; no h0 handling at all; neither device nor past ingest VM knew the stored file key | About 1.5× rewrap CPU (A6-S1 Probe 1, tmpfs); upload byte identity lost (provenance becomes a homelab verification record) | A6-S1 |
| A + plain CAS | Fits | Simplest; stored bytes identical to the upload; complete keyless fixity | Always-on key reads everything; a recovery recipient later means rewriting the whole store | C1, C2, A6-S1 Probe 2 |
| B: plaintext CAS on ZFS native encryption | Fits | Simplest restores, derivatives and views | Unattended unlock = read-everything; send/recv bug history; heir needs OpenZFS; dataset names and sizes exposed | C10–C12; kit A6-S1-B |
| C: restic via rustic_core or the CLI | Fits the letter of "proven format" | Proven engine; independent reader; keyless bit-rot check | Symmetric key reads everything; restore by hash needs a map; index RAM; loses device ciphertext | C4, C5, C15, C16; A6-S1 Probe 3 |
| OCFL 1.1 layout over A′ objects | Fits | Self-describing root; standard inventories | About 9 inodes per item vs 1; stale Rust library | C9, C13 |
| Kopia, Borg 2, PBS, Plakar, bupstash, git-annex | See §F4 | — | Knocked out | C6–C9, C17 |

A″ is a variant of A′ that can be chosen per object later: stored objects are standard age files to {X, R} either way. It is therefore not part of the one-way door. It is left for Wave 2 (ADR-0012 open question).

### Similar work and lessons

| Project | What they do | Borrow or avoid | Source |
|---|---|---|---|
| restic / rest-server | Files named by SHA-256 of stored bytes; write-once; append-only server | **Borrow** keyless `sha256sum` naming (see DR-A6-3 option d), write-once, `--read-data-subset` rotation, append-only server role (C23). **Avoid** a symmetric key on the ingest host (C4) | S4, S7, A6-S1 |
| rustic | Independent reimplementation | Borrow the second-implementation test (A6-S5 cross-read 176/176) | S9, A6-S5 |
| bupstash | Put-only keys; decryption keys offline | Borrow the key model for A′ | S22 |
| PBS | `.chunks/<4 hex>/<digest>`; keyed digests; offline RSA master key; verify jobs | Borrow fan-out, verify cadence, offline recovery key. Avoid CRC-only verification of ciphertext | S21 |
| OCFL / Fedora | Plain-file longevity, inventories | Borrow the self-describing root and manifest | S14, S15 |
| Kopia | Keyed IDs, packs, experimental ECC | Avoid packs for keepsakes; SHA-256-verify every restore (C18) | S17, S28 |
| Immich storage template | `Year/Year-Month-Day/Filename` | Borrow for a generated view; never let an app move originals | S24, S30 |
| Duplicati 2 | Local DB rebuilt from remote takes days | Avoid: store auditable without the catalog; catalog rebuildable (A6-S4) | S32 |

### Tools and libraries

| Name | Purpose | Licence | Maturity | Source |
|---|---|---|---|---|
| age (Go), `age` crate (Rust), typage, kage | Object format; independent readers | BSD-3 / MIT-Apache; typage and kage per A2 | Go age v1.3.2 (2026-08-29); rage 0.12.1; typage 0.3.1; kage 0.8.0 | S11, S34, S35 |
| OpenZFS | Filesystem, scrubs, snapshots, holds, optional encryption | CDDL | 2.4.4 newest tag; master 2.4.99 | S12, S13 |
| rustic_core | restic-format library for the comparator | Apache-2.0 OR MIT | 0.13.0, "early development" | S10 |
| restic + rest-server | Comparator; append-only reference | BSD-2 | v0.19.1 | S4, S7, S8 |
| ocfl-py, rocfl | OCFL validation | not checked | 2.1.0 (2026-06-26); 1.7.0 (2022-10-08) | S16 |
| LazyFS | Crash-consistency fault injection | not checked | Used in A6-S3 | S38 |

## Spikes

The spike runner owns the results. Container figures are on synthetic data, usually on tmpfs, and are **not homelab or budget evidence**.

| Spike | Hypothesis | Pass → / fail → (decision) | Exec tag | Budget IDs | Data class | Status | Result |
|---|---|---|---|---|---|---|---|
| A6-S1 Posture probes | Container probes turn matrix cells for A, A′ and C from reasoned into observed | n/a: owner decides OD-07 | CT → owner | — (relates to BUD-TTS, BUD-RESTORE, BUD-RECOVERY) | SYN → results | **Ran** | Probe 1: a later recipient addition left the payload byte-identical 535/535 and rewrote all 229.56 MB; rewrap 1.68–1.75 s vs re-encryption 2.51–2.58 s (tmpfs, CPU only); +98 B per X25519 stanza. Probe 2: the ingest key opens 535/535 stored files under A and 0/535 under A′. **Scope correction:** the probe read blob files only, not the manifest's clear h0; A6-S6 shows h0 + payload + I_e opens 176/176 (C32). Probe 3: restic files are named by SHA-256 of their bytes (19/19), so a keyless check caught a bit flip; Kopia pack names are random. Probe 4: exact sizes 535/535 and presence 50/50 (C31). [README](../../spikes/A6-S1/README.md) |
| A6-S1-B ZFS posture cells | Raw send exposes no names or content; locked dataset shows names and sizes only; scrub needs no key and names no files; `file://` unlocks unattended; `change-key` is cheap | Informs the B column | OL | — | SYN → results | **Kit-ready** (script untested: no ZFS in container) | [kit](kits/A6-S1/README.md) |
| A6-S2 Bake-off (plain CAS, OCFL, restic comparator) | CAS meets BUD-INGEST, BUD-RESTORE and BUD-AUDIT with RAM ≪ 4 GB; OCFL similar; restic needs a hash map | Pass → plain CAS in ADR-0012; fail → reconsider OCFL or restic, or parallel ingest | OL (Wave 2) | BUD-INGEST, BUD-RESTORE, BUD-AUDIT | `PUB+SYN → results` (H3 Tier L) | **Kit-ready** | Smoke run only (tmpfs, 229 MB, not evidence): CAS ingest 76.6 MB/s, keyless audit 362.9 MB/s, restore max 0.012 s, RSS 20.6 MB; OCFL 60.2 MB/s; restic `dump` max 0.868 s, `check --read-data` 209.5 MB/s, RSS 162 MB. **Amendments requested for Wave 2:** add a "restic holding A′ ciphertext" mode; record files/s; align the OCFL layout extension (kit uses 0003, note cited 0004); add a sealed-h0 variant. [kit](kits/A6-S2/README.md) |
| A6-S3 Crash consistency | No ACKed item lost; nothing ACKed before durable; automatic reconciliation, including disk full | Pass → layout code acceptable; fail → fix or adopt an engine | CT | — | SYN → results | **Pass** (container; power cuts emulated with LazyFS, not real) | 400 kills plus 130 emulated power cuts: 0 violations; no-fsync control failed 12/12. Reproduction: 80 kills, 0 violations. Disk full: 100 trials across five placements (tmpfs CAS and OCFL, ext4 loop, manifest-only full, catalog-only full): 0 I1/I2 violations, 0 new ACKs while full, 100/100 finished. Repairs: 40 torn lines truncated, 40 orphans quarantined. `recover` while full failed only in 2 catalog-full trials with 0 ACKs. Not covered: ENOSPC at fsync, ZFS full-pool behaviour, lost directory entries. [README](../../spikes/A6-S3/README.md) |
| A6-S3-OL VM power cut ×10 + ZFS disk-full | The same invariants hold after real power-offs and a full ZFS pool | As A6-S3 | OL | — | SYN → results | **Kit-ready** (ZFS hooks untested) | [kit](kits/A6-S3/README.md) |
| A6-S4 Catalog loss | Rebuild from the store gives a byte-identical canonical export | Pass → catalog is a projection; fail → back up the catalog as primary data | CT | — | SYN → results | **Pass** | Byte-identical in 3 scenarios; fixed two defects (no single-writer lock; lock released by Go's GC). Reproduced: second writer refused; kill after 401 ACKs + catalog deletion → rebuild 0.49 s, 1,135 rows identical, 600/600 truth, audit 1,135 OK. Files-only rebuild loses epoch, `committed_at`, `meta_sha256`. [README](../../spikes/A6-S4/README.md) |
| A6-S5 Format independence | A one-page procedure (coreutils + age + optional sqlite3) restores byte-identical files; restic ↔ rustic | Pass → weight in ADR-0012 | CT | BUD-RECOVERY (proxy), BUD-RESTORE | SYN → results | **Pass** | X25519: 176/176 with age 1.1.1, age 1.3.1 and rage 0.12.1. restic 0.19.1 ↔ rustic 0.11.4: 176/176. PQ: only Go age ≥ 1.3 of those CLIs. Reused this pass: 535/535 restored with age 1.3.1. Timings tmpfs, not evidence. [README](../../spikes/A6-S5/README.md) |
| A6-S6 A′ rewrap round trip | Rewrapped files open with X (Go and Rust); h0 still verifies against the device record | Pass → A′ feasible; fail → A | CT | — | SYN → results | **Pass** (X25519); PQ: pass on mechanics, fail on CLI readers | Payload identical 176/176; X and R open all; I_e refused 176/176; h0 MAC 176/176; signatures 200/200. Stored header 266 B (X25519), 3,184 B (PQ). **Also shows the h0 exposure:** h0 + payload opens with I_e 176/176 (C32). The Rust rewrap is not built. [README](../../spikes/A6-S6/README.md) |
| A6-S7 (proposed) Sealed-h0 exposure and rewrap self-check | With h0 sealed to {X, R}, nothing on the box plus I_e opens stored objects; the §F3 self-check catches a wrong-X rewrap and a corrupted stanza | Pass → amendments 1–2 hold; fail → A″ or attended verification | CT | — | SYN → results | **Not started** | — |

No emulator stood in for real hardware except where stated (LazyFS power cuts in A6-S3).

## Review response

Each critical and major issue from the three skeptics, and what changed.

| Severity | Issue (lens) | Response |
|---|---|---|
| Critical | h0 kept in the clear in the manifest lets I_e open current-epoch stored objects (logic; adversary as major) | **Fixed in the analysis.** h0 is sealed to {X, R} (§F3 item 4; ADR-0008 Decision 6). Matrix rows and the Summary are restated. A6-S1 Probe 2 is scoped to blob files. C32 records the measured exposure. A6-S7 is proposed to measure the sealed form. **Not yet measured**, so it stays listed under unresolved issues. |
| Major | A′ cannot verify the rewrapped header at ingest; conflicts with ADR-0008 "verify X decryption of every rewrapped header" (sources, logic, adversary) | **Addressed by design, not built.** Write-time self-check without X, an attended sampled X-unwrap with `x_verified` state, and sealed h0 + escrowed I_e as an independent fallback (§F3 items 4–6). DR-A6-4 asks D2 and the owner to replace the ADR-0008 wording. Still a Gate A item. |
| Major | C14 overstates the keyless audit under A′ (sources, logic, adversary) | **Fixed.** C14 is marked contested and restated as C14r (A complete; A′ bytes-unchanged only; never tamper evidence). No recommendation rests on C14 now. |
| Major | Ingest-time derivatives and the plaintext catalog break A′'s stolen-box and compromised-VM claims (sources, logic) | **Fixed.** Matrix rows for metadata and derivatives. The A′ claim is narrowed to stored content of retired epochs. Derivative rule in §F3 item 10. Hand-off to D1 (AR-08) and A7 (OD-16). |
| Major | restic K5 knockout assumed restic must hold plaintext (logic) | **Fixed.** "restic as a container for A′ ciphertext" is screened (§F4: K5 passes, K3 fails). DR-A6-2's alternative is reworded. The A6-S2 kit should add this mode (hand-off to the Wave 2 spike runner). |
| Major | A′ breaks unattended restore drills on real objects (A7-S4) (logic) | **Fixed.** Listed as an OD-07 cost. Hand-off to A7: unattended drills can use only canary objects with a drill stanza, which prove nothing about real X or R stanzas. Real-object drills are attended and coincide with the X audit (§F3 item 6). |
| Major | No tamper or ransomware story for the homelab store (adversary) | **Added** §F8 and ADR-0012 Decision 5 (write-once, held snapshots, read-only audit VM, off-box manifest anchor). Proposals only; D4-S4 confirms in Wave 2. |
| Minor | Posture C audit cell and Q1 contradicted A6-S1 Probe 3 | Fixed (Q1, matrix). |
| Minor | "Only posture where fixity, scrubs and copies need no key" was false | Fixed: the A′ argument is confidentiality only. |
| Minor | Knockout applied asymmetrically to build-our-own | Fixed: K1 and K6 n/a, with substitute evidence; K5 judged against all postures. |
| Minor | "Conflicts with settled text: none" too strong | Fixed (see Conflicts). |
| Minor | OD-07 default "assume A′" for a one-way door | Fixed: ADR-0012 is drafted against A′, but Gate A is blocked until the owner decides. |
| Minor | BUD-INGEST risk not mentioned | Fixed (§F3 item 11). |
| Minor | OCFL extension 0003 vs 0004 | Recorded (C13). ADR-0012 does not fix the extension; Wave 2 aligns it. |
| Minor | K11 / §F3 escrow wording | Fixed (C29 reworded; §F3 item 8). |
| Minor | age "file key MUST NOT be reused" not discussed | Fixed (§F3 item 9). |
| Minor | ZFS citation to 2.4.0 only | Fixed: 2.4.4 tag re-fetched; `zfs-2.4.5` 404. |
| Minor | Kopia BLAKE2 open question | Closed (C6; S18 re-fetched). |
| Minor | "No second PQ reader" overstated | Fixed: one CLI, at least two library readers (typage, kage; A2-S3). The doomsday kit carries Go age plus one non-Go reader (hand-off to A7, D2-S3). |
| Minor | S29 classification; PBS CRC limit | S29 relabelled primary. The CRC-only limit follows from the keyed digest (C24) and is expected in 4.x, but that is unverified. |
| Minor | Audit arithmetic ignores per-file overhead | Fixed (§F2, Q9): decimal TB, sequential lower bound, plus the scrub's read; A6-S2 records files/s. |
| Minor | DR-A6-3 options under-analysed | Fixed: option (d) added, naming by stored (ciphertext) SHA-256; per-option effects; Probe 4 cited. |
| Missed | Attended batch verification; isolated verifier; A″; shorter epochs; S3 substrates; unscreened engines; event-log catalog | All named: §F1, §F4, Alternatives, F7 and Open questions. |

## Conflicts with settled text

None is resolved here. Each is a reading the owner must confirm.

- **"Encrypted to the homelab public key" / "the owner (admin) holds the private key" (CLAUDE.md, ADR-0001 §2, R-22).** A′ turns one homelab key into rotating ingest keys I_e plus an offline archive key X, and R if OD-08 accepts it. ADR-0008 already says the owner must confirm that devices encrypting to "one homelab key at a time" still fits ADR-0001 §2, or amend it (DR-D2-4). OD-07 depends on that same confirmation. Rotation also interacts with the one-way door "pinned homelab key(s) in the first kit" (D3, Gate C) and the ADR-0002 stick (hand-off to D3).
- **"Data integrity over everything: backups must be verifiable and restorable" (CLAUDE.md).** Under A′ the decryptability of stored objects cannot be proven online. It holds only with the §F3 self-check and attended X audits. If the owner reads the line as "provable at any time without the owner", A′ conflicts with it and A is the alternative.
- **"Prefer an existing, proven format over inventing one" (CLAUDE.md).** DR-A6-2 reads it as age v1 per object plus a one-page layout. That is an interpretation, not settled. If the owner disagrees, posture C with restic follows.
- **Restore delivery (CLAUDE.md: "re-encrypting to the target device's own key and staging in an expiring R2 prefix").** A rewrap-based restore (C22) or a USB restore path is not settled. Both are A8 and owner decisions, not A6 defaults.
- ADR-0001 §2 "plaintext catalog (e.g. Postgres)": still holds; "e.g." leaves ADR-0013 free.

## Open questions

| Question | Who | By when |
|---|---|---|
| Sealed-h0 form, size and exposure (A6-S7); write-time self-check design and its independent encoder | A6, A2, G2 | Gate A |
| Replace ADR-0008's "verify X decryption of every rewrapped header" with the §F3 scheme (DR-A6-4); sample size and cadence of the X audit | D2, A7 | Gate A |
| Epoch interval, or rotation triggered by staging drain; standby keys | D2 | Gate A |
| Isolated verifier VM or a non-exportable TPM/HSM for I_e (AR-08) | D1, D4, D2 | Wave 2 |
| Store immutability: write-once, holds, off-box manifest anchor (§F8) | A6, D4 (D4-S4), C5 | Wave 2 |
| Catalog dataset unlock mechanism (`https://` key server vs Tang vs prompt) and dataset layout | C5, D2 | Gate A |
| Owner's current setup: Proxmox/PBS versions, encryption, free RAM, bake-off space (intake C1, C3, C5, C6, C12) | H2 | Wave 1 exit |
| Real ingest rate (parallel verify and rewrap), index RAM, audit MB/s and files/s on the real corpus | A6-S2 (OL) | Wave 2 |
| Screen Perkeep, Duplicacy, duplicity, rdedup, Bareos/Bacula, Tahoe-LAFS and S3 substrates from primary sources | A6 | Wave 2 |
| A″ (fresh file key at ingest) vs A′, per object | A6, A2, D2 | Wave 2 (reversible) |
| OCFL wrapper and layout extension (0003 vs 0004) | A6-S2 | Wave 2 |
| If OD-06 = PQ: which readers the doomsday kit carries (Go age CLI plus typage or kage), and whole-file decrypt by typage on the A6-S5 corpus (not tested) | A2, A7, D2-S3 | Gate A |
| PBS 4.x current docs (mirror stale; git.proxmox.com blocked) | H1 (route) | Before C8 relies on PBS |
| restic #533 current state (`gh api` refused) | H1 (route) | Not blocking |
| Raw encrypted `zfs send` on Linux OpenZFS 2.4.x; relevant only to B | C5 | Gate C |
| Immich external-library read-only mode over a generated tree | C8 (OD-13) | Wave 2 |
| Restore delivery: fresh re-encryption vs rewrap (C22) | A8 | ADR-0028 |
| One shared rewrap test-vector set for A6-S6, D2-S2 and A2-S3 | A2, D2, A6 | Wave 2 |
| Does A2's padding decision apply to stored objects? (Probe 4 measured exact sizes on unpadded objects) | A2 | Gate A |

## Recommendation

1. **Posture (OD-07): A′, with the three review amendments.** Keep each object as a standard age v1 file whose payload is byte-identical to the upload; rewrap the header at ingest to {X, R}; seal h0 to {X, R}; self-check every rewrap without X and verify samples with X whenever the owner brings it online; rotate I_e.
   - **Why:** it is the posture in which neither the always-on key nor the disks reveal stored content of retired epochs. It does not protect metadata or derivatives, and it does not by itself protect integrity against a writer. Those need the catalog's encrypted dataset and §F8.
   - **Support:** verified C1, C2, C3, C29 and the measured C32 and A6-S6. The contested C14 is **not** used.
   - **What would change it:**
     - the owner wants an automatic plaintext gallery in v1 (→ B);
     - the owner reads "verifiable" as "provable without the owner at any time" or rejects attended restores (→ A);
     - A6-S7 shows the sealed-h0 or self-check design cannot be built simply (→ A″ or A);
     - D2 finds rotation too costly (→ A with R from day one).
   - **No default:** Gate A is blocked until the owner decides; ADR-0012 is drafted against A′.
2. **Engine (ADR-0012): a plain content-addressed store of age objects on ZFS,** addressed by plain SHA-256 (A1), with a hex fan-out, write-once objects and an append-only manifest specified in one page. None of the screened engines passes the knockout. The A6-S2 bake-off (Wave 2) compares plain CAS, OCFL and restic, including restic holding A′ ciphertext. Support: verified C4–C9, C17; spikes A6-S3, A6-S4, A6-S5.
3. **Catalog (ADR-0013):** Wave 2, with the requirements in §F7.

## Decision requests

### OD-07: Homelab at-rest posture

- **Needed by:** Gate A (one-way door #4). **No default:** Gate A stays blocked until the owner decides.
- **Evidence:** §F1–F3, §F8; spikes A6-S1, A6-S6; ADR-0008; D1 AR-08.
- **Options:**

  | Option | What it means for the family | Cost (money and owner time) | Reversibility | Risks |
  |---|---|---|---|---|
  | A′ amended (recommended) | Nothing visible. Restores wait for the owner's archive key | Key ceremony; automated I_e rotation; owner brings X for restores, rebuilds, real-object drills and X audits | Costly: moving to B or C later means decrypting or re-encrypting the whole store | Rewrap code path; the self-check is new; metadata still exposed through the catalog |
  | A | Nothing visible | Least work | Costly | Always-on key reads everything; recovery recipient later = whole-store rewrite |
  | B | Easiest path to a family gallery | ZFS key handling | Costly | Auto-unlock = read-everything; send/recv bug history |
  | C | Nothing visible | Engine operations | Costly | Symmetric key reads everything; restore by hash needs a map |

- **Recommendation:** A′ amended.
- **Touches settled text:** yes, as readings to confirm: "homelab public key / owner holds the private key" (with DR-D2-4) and "verifiable and restorable" (see Conflicts).

### DR-A6-1: Bake-off shortlist for A6-S2

- **Options:** (a) plain CAS + OCFL variant + restic comparator, in plaintext (C) and ciphertext-container modes; (b) plain CAS only.
- **Recommendation:** (a). ADR-0012 can then show the measured cost of not adopting a proven engine.
- **Touches settled text:** no. **Default:** (a).

### DR-A6-2: Reading of "prefer an existing, proven format over inventing one"

- **Options:**
  - (a) the format is age v1 per object (C2SP spec, independent readers), optionally in an OCFL 1.1 root, with a one-page layout of our own;
  - (b) the owner means a proven backup engine. That forces restic in posture C, or restic as a ciphertext container plus our own hash map.
- **Recommendation:** (a).
- **Touches settled text:** it interprets a CLAUDE.md line without changing it; the owner must confirm.

### DR-A6-3: Stored-object names reveal plain SHA-256 to someone holding the disks

- **Options:**
  - **(a) Accept** and record it in OD-17. Keyless audit by manifest; the heir can find a file by its hash.
  - **(b) Encrypted dataset for the store.** Names are hidden while locked, but keyless app audits then need the dataset key loaded, and auto-unlock from the box hides nothing.
  - **(c) Keyed names, HMAC(store key, sha256).** The heir procedure needs the store key.
  - **(d) Name objects by `stored_sha256`** (SHA-256 of the ciphertext). Under A′ the stored header uses fresh randomness, so names are unpredictable from content and the confirmation attack fails. The audit becomes restic-style `sha256sum == filename`, with no manifest needed. Lookup by plain SHA-256 goes through the manifest or catalog, which heirs need anyway for names. A later rewrap renames every file.
- **Recommendation:** (d), if the A6-S2 bake-off shows no material restore-time cost from the lookup; otherwise (a). Not reviewed by skeptics.
- **Reversibility:** a rename pass. **Needed by:** Gate A (first family ingest).

### DR-A6-4 (new): Rewrap verification under A′ (joint with D2)

- **Question:** replace ADR-0008 Decision 1's "verify X decryption of every rewrapped header" with:
  - a write-time self-check without X (§F3 item 5);
  - attended, sampled X unwrap with an `x_verified` state (§F3 item 6);
  - sealed h0 + escrowed I_e kept as the fallback until sampled.
- **Options:**
  - (a) the replacement above;
  - (b) keep "every header" literally, which needs X online at ingest and so means posture A in effect;
  - (c) attended verification of every object before ACK, which breaks BUD-TTS.
- **Recommendation:** (a).
- **Needed by:** Gate A.

### OD-06 (input from A6)

- If PQ is chosen, the stored objects have one CLI reader (Go age ≥ 1.3) and at least two library readers (typage, kage).
- A6 accepts either profile, but requires uniform stored headers: {X, R} both PQ or both X25519.
- The doomsday kit then carries a static Go age plus one non-Go reader.

## Hand-offs

| To | What | Why |
|---|---|---|
| D2 | DR-A6-4 (rewrap verification wording); h0 sealed to {X, R}; epoch interval or drain-triggered rotation; TPM/HSM option for I_e; uniform stored profile | ADR-0008 Decisions 1, 6, 8 |
| A2 | `stored-v1` header plus sealed h0; independent encoder for the self-check; file-key-reuse reasoning (§F3 item 9) in the rewrap vector review; does padding apply to stored objects? | `object-format.md` |
| A3 | `put_blob` stores ciphertext; streaming verify; record `stored_sha256`; ACK only after the self-check; parallel verify and rewrap for BUD-INGEST | ADR-0009 |
| A7 | Keyless audit = bit-stability only under A′; X-audit cadence; real-object drills are attended (A7-S4 can use only canaries unattended); doomsday kit readers; derivative policy under A′ (OD-16) | ADR-0029 |
| D1 / D4 | AR-08: isolated verifier; §F8 store immutability; A′ does not protect metadata from a compromised online VM; fault case "rewrite object + manifest line" | Threat register, D4-S4 |
| C5 / C6 | Datasets: store (write-once, held snapshots), catalog and derivatives (encrypted), temp; unlock mechanism | ADR-0030/0031 |
| C8 | Keep PBS for VM and catalog backups; Immich external-library check for OD-13 | ADR-0032 |
| D3 | I_e rotation vs the pinned-key one-way door and the ADR-0002 stick | Gate C |
| A8 | Restores to R2: prefer fresh re-encryption over rewrap (C22) | ADR-0028 |
| Wave 2 spike runner | A6-S2 kit amendments (restic ciphertext mode, files/s, OCFL extension, sealed h0); A6-S7 | A6-S2, A6-S7 |
| H1 | Blocked sources in Method; `gh api` restic 403; stale PBS mirror; S29 relabelled primary | `sources.md` |
