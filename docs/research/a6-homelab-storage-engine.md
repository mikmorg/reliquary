# A6. Homelab at-rest posture, storage engine and catalog

- **Workstream:** A6 (see `docs/research/PLAN.md`, section "A6.")
- **Status:** Draft (analyst deep read, Wave 1, batch W1-b; second analyst pass reconciles it with the A2 and D2 drafts, see [Second pass](#second-pass-reconciliation-with-a2-and-d2)). Not yet under skeptic review. Spike results pending: a separate spike runner is working on the A6 spikes in parallel (see [Spikes](#spikes)).
- **Date:** 2026-09-29 (last updated 2026-09-29, second analyst pass)
- **Wave 1 scope:** the at-rest posture (OD-07, one-way door #4) and the knockout screen of storage engines for the ADR-0012 draft. The bake-off (A6-S2) is Wave 2; only its kit is written now. The catalog (ADR-0013) is Wave 2 because the choice is not trivially decided (§F7).
- **Feeds:** ADR-0012 (reserved in `docs/adr/README.md`; the draft is the next stage), OD-07, one-way door #4, new decision requests DR-A6-1 to DR-A6-3 (below; H1 assigns OD numbers). Evidence for OD-08 (recovery recipient) and OD-13 (read-only gallery).
- **Depends on:** the CE spike (`content-encryption-format.md`, which is also T1 spike 2), A1 (the store is addressed by plain SHA-256), A3 (durable-commit contract F6), D1 (SR-04, SR-20, AR-08), D2 (`d2-key-hierarchy-custody-recovery.md`, draft: key set K-01..K-07, archive identity X as K-03b), A2 (`a2-object-envelope.md`, draft: OD-06 PQ, recipient placement DR-A2-2), C5 (hardware, filesystem), owner intake answers C1, C3, C5, C6 and C12 (not yet given)
- **Traceability rows advanced:** R-09, R-26, R-28, R-38, R-45, R-46, OPEN-2, Q1-1 (see `docs/research/traceability.md`)

## Summary

1. **The posture question is narrower than the plan assumed.** The ingest design already in hand (CE §11, A3 F6, D1 SR-04) decrypts every object to verify it before commit. So **some private key is online at ingest in every posture**. The real choices are these: which key is online, what it can decrypt, whether audits and scrubs need it, and what a stolen box or a compromised ingest VM exposes.
2. **Recommended posture: "A′, keep the received age payload and rewrap the header at ingest".** The homelab keeps each object as a standard age v1 file. At ingest it rewrites only the header, to an **offline archive recipient** and, if OD-08 says so, a recovery recipient. It leaves the payload bytes untouched. The online **ingest key** only protects data in transit, so it can be rotated and its old private keys destroyed. The effects:
   - Fixity audits and ZFS scrubs run with no key at all.
   - A stolen box or a compromised ingest VM does not expose the archive. The exception is the catalog, which needs its own at-rest encryption.
   - Heirs need only `age` plus the archive identity.
   - Off-site copies can be plain `rclone`/`zfs send` of ciphertext.
   - The costs: restores, catalog rebuilds and derivative generation need the archive key brought online by the admin, and an automatic plaintext gallery view (OD-13) becomes harder.
3. **Knockout screen: no existing backup engine passes.** restic/rustic, Kopia, Borg 2, PBS, Plakar/Kloset, bupstash and git-annex each fail at least one knockout criterion. The common failures are symmetric keys only, snapshot-scoped ingest, no lookup by whole-file SHA-256, no independent reader, or pre-production maturity. The "existing, proven format" that does pass is **age v1 per object** (a C2SP spec with independent Go and Rust decryptors, already checked in the CE spike), stored in a **plain content-addressed layout on ZFS**. OCFL 1.1 is an optional self-describing wrapper for that layout.
4. **Bake-off shortlist (A6-S2, Wave 2):**
   - (1) plain CAS of age objects;
   - (2) the same objects in an OCFL 1.1 storage root;
   - (3) restic format via restic/rustic_core, as the "proven engine" comparator.

   restic is kept even though it fails the per-file-by-hash criterion natively, so that the ADR can show the cost of *not* adopting it.
5. **Confidence:**
   - **High** on the facts behind the knockouts (primary specs and source).
   - **Medium** on the recommended posture. It is reasoned, not yet measured. The D2 and A2 drafts both build on it (D2 K-03b, A2 DR-A2-2), but nobody has skeptic-reviewed it yet, and it adds a key-rotation duty.
   - **Low** on anything about scale (index RAM, audit hours). No measurement exists yet.
6. **Second pass (reconciliation with the A2 and D2 drafts, [§Second pass](#second-pass-reconciliation-with-a2-and-d2)):**
   - A6 needs one thing from the recipient-placement debate (A2 P1 vs D2 "devices include R"): **stored headers are always written by the homelab, as {X, R}**. Both drafts already agree on that. Where R sits on the *device* header only changes how long the ingest key I_e must be kept before it is destroyed.
   - If OD-06 picks PQ, the per-object header overhead is about 3.2 KB stored plus about 1.6 KB for the kept original header h0 (A2 C6). Keep h0 inside the append-only manifest, not as a second file per object, so the store stays at one file per item.
   - A Rust rewrap is feasible with the public API of the `age` 0.12.1 crate (`Identity::unwrap_stanza`, `Recipient::wrap_file_key`, `FileKey: ExposeSecret`, age-core stanza read/write). The header parser and the header MAC are private, so Reliquary writes about one screen of its own header code (C20). This matches D2's finding that Go age also has no rewrap API.
   - New for A8: a restore could also be a header rewrap to the device key. That would make the restored payload byte-identical to the first upload, which lets the cloud link the two (C22). Re-encrypting under a fresh file key avoids this.

## Questions

| # | Question | Short answer | Confidence |
|---|---|---|---|
| 1 | Posture: must the private key be online for ingest and for scrubs? | **Ingest: yes, in every posture**, because verify-before-commit decrypts the whole object (CE §11, SR-04). **Scrubs:** a ZFS scrub never needs keys, even on native encryption (C10). An app-level SHA-256 audit needs no key under A and A′ (digest of the stored bytes, §F2). It needs the ZFS key under B and the repository password under C. | High (facts); Medium (A′ design) |
| 2 | Unattended unlock after a power cut | Under A′ the ingest key must come up without a person present, or ingest stalls and BUD-TTS (24 h) slips. The stakes are low because that key only protects data in transit. Under A, B and C the unattended key is a read-everything key. ZFS offers `keylocation=file://` (key on the box) or `https://` (key fetched from another host) (C11). The mechanism belongs to C5/D2. | High (options); Medium (ranking) |
| 3 | Derivative generation (thumbnails, format migration) | Needs plaintext. A′: make derivatives at ingest while the plaintext is in hand, or later with the archive key. B: at any time. C: through the engine with the password. | Medium |
| 4 | Cost of adding a recovery recipient later | **Header rewrap, not payload re-encryption** (age: every stanza wraps the same file key; the header MAC comes from the file key; the payload key comes from the file key and the nonce) (C2). It needs the private key, and with one file per object every file is rewritten, because the header sits at the front. So it costs roughly 10 TB of write I/O, but no payload cryptography. **Avoid it by adding the recipient at ingest from day one (A′).** A passphrase (scrypt) stanza cannot be mixed with other stanzas, so a recovery recipient must be an X25519, hybrid PQ or hardware-tag identity (C3). | High (spec); Medium (I/O inference) |
| 5 | What a stolen box exposes | A′: content, nothing (archive key offline); in-transit objects under the current ingest key only if that key is stored on the box; the catalog, unless it sits on an encrypted dataset. A: everything, if the key unlocks unattended. B: everything if `keylocation=file` is on the box. File sizes, dataset and snapshot names, and dedup tables are never encrypted by ZFS (C10). C: everything if the password is on the box. | Medium |
| 6 | Can an heir read it? | A/A′: yes, with `age -d -i identity` on any OS, plus the catalog export or the decrypted metadata records for names. B: needs a Linux/OpenZFS machine able to import the pool, plus the passphrase. C: needs the restic or rustic binary plus the password. The procedure is BUD-RECOVERY; D2-S3 tests it. | Medium |
| 7 | Optional read-only Immich/PhotoPrism view | Only possible with plaintext on disk. B gives it directly (through a generated, read-only tree). A/A′ need a decrypted mirror or a decrypt-on-read layer, which brings back an online read key. Never let Immich own or move originals (issue #30919, S30, secondary). OD-13 decides whether any view exists in v1. | Medium |
| 8 | Knockout criteria | K1 library-driven per-file ingest keyed by our ID; K2 specified format with an independent reader; K3 single-file restore by hash; K4 licence (G3); K5 fit with the posture. K6 (maturity) is added from CLAUDE.md "proven". Results in §F4. | High |
| 9 | Snapshot engines vs continuous per-file ingest at 3–5M objects, 10 TB, +1–2 TB/yr | A plain CAS needs no engine index: the path is the hash, and the catalog is the index. restic keeps its index in RAM, and there are OOM reports at about 2M files on a 1 GB machine (secondary, C15). A full read audit of 10 TB is disk-bound in every design (arithmetic in §F5). No measurement exists yet; A6-S2 measures it. | Low (numbers); Medium (shape) |
| 10 | Readability without Reliquary: browsable tree vs opaque packs | A CAS of whole age files is not browsable, but it is not opaque either: each object stands alone and decrypts with stock `age`. Packs (restic, Kopia, Borg, Kloset) need the engine or a reimplementation to read. A browsable tree can be generated from the catalog (§F6). | High |
| 11 | Catalog: Postgres vs SQLite | **Open (Wave 2, ADR-0013).** Requirements fixed now: store plain SHA-256 per item (A1); archive raw metadata records in the store so the catalog can be rebuilt (A6-S4); record the stored-bytes digest for keyless audits. | n/a |
| 12 | Admin-only pruning with cross-user dedup | A blob is deletable only when no live item from any person references it, and then only through an admin-only, separately credentialed, verify-before-destroy step (SR-20). The refcount is derived from catalog sightings, never stored alone. Details are in ADR-0013 (Wave 2). | Medium |
| 13 | Keep a future off-site copy easy | A/A′: copy ciphertext files as they are to any untrusted target (rclone, rsync, non-raw `zfs send`). No second encryption layer is needed. B: `zfs send -w` raw (C12 history) or rclone crypt. C: `restic copy`. | Medium-high |
| 14 | (new) Does naming stored files by plain SHA-256 leak anything? | Yes, under A/A′: someone who steals the disks can confirm whether a known file is present. The cloud never sees these names. Under B, ZFS encrypts directory listings. See DR-A6-3. | Medium |
| 15 | (new) Is the prototype's "decrypt to a temp file" needed? | Not under A/A′. Ingest can verify SHA-256 and HMAC by streaming, and store the ciphertext it already has. Plaintext then never reaches disk, except what a sandboxed metadata parser reads. | Medium |

## Method

- **Sweep:** three scouts ran: docs, source and community. Their findings are the input to this note.
- **Deep read:** on 2026-09-29 the analyst re-fetched and read the load-bearing primary sources:
  - restic `design.rst` (repository format, encryption, chunking, threat model);
  - restic backup, restore and repository docs;
  - the rest-server README;
  - rustic and rustic_core READMEs, and rustic_core 0.13.0 source (`configfile.rs`, `credentials.rs`, `repository.rs`);
  - the C2SP age spec;
  - OpenZFS `zfs-load-key(8)`, `zfsprops(7)`, `zfs-send(8)`, `zpool-scrub(8)` (master and the zfs-2.4.0 tag), and `META`;
  - OCFL 1.1 and extension 0004;
  - Kopia architecture, encryption and ECC docs, and `sha_hashes.go`;
  - the Borg README (master);
  - PBS `technical-overview.rst`, and `debian/changelog` (to check the mirror's age);
  - the bupstash, Kloset and Immich storage-template docs.

  Release dates were re-checked on the crates.io API and PyPI JSON.
- **Project inputs:** CLAUDE.md, ADR-0001, `content-encryption-format.md` (CE), `a1-content-identity.md`, `a3-ingest-protocol.md`, `d1-threat-model.md`, `f1-build-adopt-fork-compose.md`, `budgets.md`, `decision-queue.md`, `one-way-doors.md`, `owner-intake.md`.
- **Routes used:** raw.githubusercontent.com (vendor docs and source mirrors), static.crates.io (the scouts' extracted crate source), crates.io API, PyPI JSON, proxy.golang.org (scouts). Community evidence came from the scouts' WebFetch of github.com issue pages.
- **Blocked sources.** None was silently replaced. Each is to be reported to H1:
  - restic.readthedocs.io and restic.net: mirror used, `restic/restic @ master : doc/`.
  - kopia.io: mirror used, `kopia/kopia @ master : site/content/docs`.
  - ocfl.io: mirror used, `OCFL/spec`.
  - openzfs.github.io: man pages used instead.
  - c2sp.org: editor's copy used.
  - docs.immich.app.
  - pbs.proxmox.com, pve.proxmox.com, www.proxmox.com, forum.proxmox.com.
    - The only PBS source reachable is the GitHub mirror, whose `master` is stale at 3.2.4 (C8).
    - PBS 4.x claims (S3 datastore) are **secondary only**.
  - git-annex.branchable.com: git-annex is covered by secondary sources only.
  - forum.restic.net, forum.duplicati.com: secondary snippets only.
  - www.sqlite.org, www.postgresql.org: catalog facts not gathered; Wave 2.
  - rustic.cli.rs.
  - hn.algolia.com, reddit.com.
  - api.github.com.
  - The GitHub MCP is limited to `mikmorg/reliquary`.
  - perkeep.org: Perkeep got **no result**.
- **Second pass (2026-09-29):**
  - Re-checked against the primary text: the age scrypt-only-stanza rule (`age.md`, "An scrypt stanza, if present, MUST be the only stanza"); restic's symmetric key model and its append-only threat-model paragraph (`design.rst`); the Borg 2 "DO NOT USE BORG2 FOR YOUR PRODUCTION BACKUPS" banner (`README.rst`). No change.
  - New primary source: the Rust `age` crate source, for rewrap feasibility (S34, C20).
  - Reconciled with the A2 and D2 drafts (S35).
  - Still blocked:
    - git.proxmox.com (proxy `CONNECT` 403), so current PBS 4.x behaviour remains unverified;
    - restic issues #187 and #533 through `gh api` (this session has no GitHub access to that repository), so the "no asymmetric mode" point still rests on `design.rst` (primary) plus secondary search results.
- **Stop rule:** the analyst's re-reads added one new primary fact that changes the analysis: the age scrypt-mixing rule (C3). They also added two primary facts that sharpen it: rustic_core's `FixedSize` chunker option (C16) and OCFL extension 0004 (C13). No further sources were sought for the Wave 1 scope.

## Sources

| # | Source (title and URL or mirror path) | Publisher | Published or version date | Accessed | Primary? |
|---|---|---|---|---|---|
| S1 | `CLAUDE.md`; ADR-0001 `docs/adr/0001-cloud-staging-on-r2.md` | Project | 2026-09-29 (Accepted) | 2026-09-29 | Yes (settled text) |
| S2 | CE spike `docs/research/content-encryption-format.md` §§1, 5.5, 11, 12, 16 | Project (T1 spike 2) | 2026-09-29 | 2026-09-29 | Yes (project spike) |
| S3 | A3 `docs/research/a3-ingest-protocol.md` F6; A1 `a1-content-identity.md` Q9, §5; D1 `d1-threat-model.md` SR-04, SR-20, AR-08; F1 `f1-build-adopt-fork-compose.md` | Project | 2026-09-29 (drafts) | 2026-09-29 | Yes (project drafts) |
| S4 | restic design, `restic/restic @ master : doc/design.rst` (= restic.readthedocs.io design) | restic | master head | 2026-09-29 (key sections re-read) | Yes |
| S5 | restic "Working with repositories", `restic/restic @ master : doc/045_working_with_repos.rst` | restic | master head | 2026-09-29 | Yes |
| S6 | restic "Backing up" and "Restoring", `… : doc/040_backup.rst`, `doc/050_restore.rst` | restic | master head | 2026-09-29 | Yes |
| S7 | rest-server README, `restic/rest-server @ master : README.md` | restic | master head | 2026-09-29 | Yes |
| S8 | restic latest version, proxy.golang.org `github.com/restic/restic/@latest` | Go module proxy | v0.19.1, 2026-07-05 | 2026-09-29 (scout) | Yes |
| S9 | rustic README, `rustic-rs/rustic @ main : README.md` | rustic-rs | main head | 2026-09-29 | Yes |
| S10 | rustic_core 0.13.0 crate: `README.md`, `Cargo.toml`, `src/repofile/configfile.rs`, `src/repository/credentials.rs`, `src/repository.rs` (static.crates.io) | rustic-rs | 0.13.0, updated 2026-08-16 (crates.io API) | 2026-09-29 | Yes |
| S11 | C2SP age v1 spec, `C2SP/C2SP @ main : age.md` (= c2sp.org/age) | C2SP | main head | 2026-09-29 (header, payload, scrypt, tagged sections read) | Yes |
| S12 | OpenZFS `zfs-load-key(8)`, `zfsprops(7)`, `zfs-send(8)`, `zpool-scrub(8)`, `META`, `openzfs/zfs @ master : man/…` | OpenZFS | master = 2.4.99; `zfs-load-key.8` .Dd 2026-01-30 | 2026-09-29 | Yes |
| S13 | OpenZFS `zpool-scrub(8)` at tag `zfs-2.4.0` | OpenZFS | 2.4.0 | 2026-09-29 | Yes |
| S14 | OCFL 1.1 spec, `OCFL/spec @ main : 1.1/spec/index.md` (= ocfl.io/1.1/spec) | OCFL editors | 2022-10-07, updated 2024-11-07 | 2026-09-29 | Yes |
| S15 | OCFL extension 0004 hashed n-tuple layout, `OCFL/extensions @ main : docs/0004-hashed-n-tuple-storage-layout.md` | OCFL community | extensions v1.0 | 2026-09-29 | Yes |
| S16 | rocfl (crates.io API), ocfl-py (PyPI JSON) | crates.io, PyPI | rocfl 1.7.0 (2022-10-08); ocfl-py 2.1.0 (2026-06-26) | 2026-09-29 | Yes |
| S17 | Kopia docs: Architecture, Encryption, ECC, `kopia/kopia @ master : site/content/docs/Advanced/…` (= kopia.io) | Kopia | master head | 2026-09-29 | Yes |
| S18 | Kopia `repo/hashing/sha_hashes.go` (master); Kopia v0.23.1 module source (`repo/repository.go`, `repo/open.go`) | Kopia | master; v0.23.1 2026-06-15 | 2026-09-29 (sha_hashes re-read; module source by scout) | Yes |
| S19 | Borg README (Borg 2, master), `borgbackup/borg @ master : README.rst`; Borg internals `docs/internals/data-structures.rst` (scout) | BorgBackup | master head | 2026-09-29 | Yes |
| S20 | PyPI `borgbackup` JSON | PyPI | 1.4.5 stable; 2.0.0b25 uploaded 2026-09-27 | 2026-09-29 | Yes |
| S21 | PBS technical overview, `proxmox/proxmox-backup @ master : docs/technical-overview.rst`; `pbs-tools/src/crypt_config.rs` (scout); `docs/backup-client.rst` (scout); `debian/changelog`; `debian/copyright` (scout) | Proxmox | GitHub mirror, top changelog entry 3.2.4-1 | 2026-09-29 | Yes (but possibly stale) |
| S22 | bupstash README, `andrewchambers/bupstash @ master : README.md`; 0.12.0 crate source (`src/keys.rs`, man pages, technical overview) (scout) | bupstash | 0.12.0, 2022-11-07 (crates.io API) | 2026-09-29 | Yes |
| S23 | Kloset README, `PlakarKorp/kloset @ main : README.md`; proxy.golang.org kloset `@latest` | Plakar | v1.1.8, 2026-09-24 | 2026-09-29 | Yes |
| S24 | Immich storage template, `immich-app/immich @ main : docs/docs/partials/_storage-template.md` | Immich | main head | 2026-09-29 | Yes |
| S25 | OpenZFS #12014, PR #17340, openzfs-docs #494 (github.com, via scout WebFetch) | OpenZFS community | 2021-05-08 → merged 2025-05-20; 2024-02-12 | 2026-09-29 (scout) | No |
| S26 | openzfsonosx/openzfs-fork #104 (search-result title only) | community | unknown | 2026-09-29 (scout) | No |
| S27 | restic #1988, #2523 (github.com, scout); forum.restic.net thread 8758 (snippet) | restic community | 2018-09-07; 2019-12-20 | 2026-09-29 (scout) | No |
| S28 | Kopia #5049, #4769, #4348, PR #4839 (github.com, scout) | Kopia community | 2025-11-30; 2025-08-19; 2025-01-19; 2025-09-23 | 2026-09-29 (scout) | No |
| S29 | Plakar releases page (github.com, scout) | Plakar | v1.1.0 2026-06-05 … v1.1.7 2026-09-24 | 2026-09-29 (scout) | No (release notes seen on a web page, not the repo) |
| S30 | Immich #30919, #29627 (github.com, scout) | Immich community | 2026-08-22; 2026-07-06 | 2026-09-29 (scout) | No |
| S31 | restic #187, #533 (search results only) | restic community | unknown | 2026-09-29 (scout) | No |
| S32 | Duplicati forum threads 7591, 9291; duplicati #4923 (snippets/titles) | community | unknown | 2026-09-29 (scout) | No |
| S33 | git-annex backends page (search snippet) | git-annex | unknown | 2026-09-29 (scout) | No |
| S34 | Rust `age` 0.12.1 crate source (`src/lib.rs`, `src/protocol.rs`, `src/keys.rs`) and `age-core` 0.12.0 (`src/format.rs`), from static.crates.io; version and date from index.crates.io | str4d / rage | age 0.12.1, published 2026-07-14 | 2026-09-29 (second pass) | Yes |
| S35 | A2 `a2-object-envelope.md` (C6, C9, C21, Q9, DR-A2-2) and D2 `d2-key-hierarchy-custody-recovery.md` (K-01..K-07, C14, §F2) | Project (drafts) | 2026-09-29 | 2026-09-29 (second pass) | Yes (project drafts, not skeptic-reviewed) |

## Claims

Key claims are load-bearing for OD-07 or the knockout screen. Skeptic columns are for the next stage.

| # | Claim | Sources | Key? | Skeptic 1 (sources) | Skeptic 2 (logic) | Skeptic 3 (adversary/cost/user) | Verdict |
|---|---|---|---|---|---|---|---|
| C1 | Under the current ingest design (verify-before-commit decrypts the whole object), a private key that can decrypt incoming objects must be online at ingest in **every** posture. The posture choice cannot remove it. It only decides what that key can decrypt, and which other operations need a key. | S2 §11, S3 (SR-04, A3 F6) | Yes | | | | pending |
| C2 | age: every stanza wraps the same 128-bit file key. HMAC key = HKDF(file key, "header"); payload key = HKDF(file key, nonce, "payload"). So adding or replacing recipients means rewriting the header and its MAC, which needs the file key (a private key). The payload bytes stay valid. In a one-file-per-object layout the whole file is rewritten, because the header's length changes and it sits at the front (inference). | S11 | Yes | | | | pending |
| C3 | age: an scrypt (passphrase) stanza MUST be the only stanza, so a passphrase-based recovery stanza cannot coexist with the X25519 homelab stanza. A recovery recipient must be X25519, mlkem768x25519 or a tagged (hardware) type. | S11 | Yes | | | | pending |
| C4 | restic encrypts all data with one symmetric master key (AES-256-CTR + Poly1305-AES), unlocked by scrypt-derived password keys. Any writer can decrypt the whole repository. The master key can be changed only by `copy` to a new repository. An adversary who compromises a host with append-only access can capture the password and decrypt past and future backups. | S4 | Yes | | | | pending |
| C5 | restic splits files over 512 KiB into CDC blobs of 512 KiB–8 MiB (1 MiB average), identified by the SHA-256 of each blob. A whole-file SHA-256 is therefore not a native lookup key for most photos and videos. Restore by hash needs our own map from SHA-256 to (snapshot, path) or a blob list. Ingest is snapshot-scoped (CLI `--stdin-from-command`, one snapshot per call; rustic_core `Repository::backup(opts, source, snap)`). | S4, S6, S10 | Yes | | | | pending |
| C6 | Kopia content IDs are keyed MACs (the registry lists HMAC-SHA256 and similar). Encryption is passphrase-derived (scrypt → AES256-GCM). The library is Go only. This sweep found no independent (non-Kopia) reader. The last point is absence of evidence. | S17, S18 | Yes | | | | pending |
| C7 | The Borg 2 README says "DO NOT USE BORG2 FOR YOUR PRODUCTION BACKUPS"; there is no beta-to-beta upgrade path. PyPI: 2.0.0b25 uploaded 2026-09-27; the latest stable is 1.4.5. | S19, S20 | Yes | | | | pending |
| C8 | PBS: the server cannot verify encrypted chunks against their digest and checks only CRC-32. File backups are pxar archive streams (snapshot-oriented). The reachable GitHub mirror's changelog tops out at 3.2.4-1, so current PBS 4.x behaviour is unverified. | S21 | Yes | | | | pending |
| C9 | bupstash is "beta software", recommended only for redundant backups; its last crates.io release is 0.12.0 (2022-11-07). rocfl's last release is 1.7.0 (2022-10-08). ocfl-py 2.1.0 is from 2026-06-26. | S16, S22 | Yes | | | | pending |
| C10 | ZFS native encryption does not encrypt dataset or snapshot names, properties, file sizes, holes or dedup tables. It does encrypt file data, attributes and directory listings. Datasets can be scrubbed and resilvered without keys loaded. `change-key` does not overwrite the old wrapped master key on disk. | S12 | Yes | | | | pending |
| C11 | ZFS `keylocation` is `prompt` (default), `file:///…`, `https://…` or `http://…`, and can be changed after creation. `zfs send -w` sends encrypted datasets without loaded keys, and the stream may be received on an untrusted machine. | S12 | Yes | | | | pending |
| C12 | Native encryption + send/recv has a bug history: #12014 (opened 2021-05-08) was closed by PR #17340 (merged 2025-05-20), which was backported to 2.2.8 and 2.3.3. A macOS-port issue title reports raw-send corruption on 2.4.1/2.4.3rc3 (unverified). | S25, S26 | No (context) | | | | Secondary only |
| C13 | OCFL 1.1: content addressing MUST use sha512 or sha256; links MUST NOT be used; version directories are immutable. A one-version object has 6 files in 3 directories (the spec's own figure), versus 1 file per item in a plain CAS (inference: about 9 inodes per item, about 45M at 5M items). Extension 0004 maps an object ID to `tuple/tuple/…/digest` paths. | S14, S15 | Yes | | | | pending |
| C14 | Under postures A and A′, a keyless SHA-256 over the stored bytes, checked against the digest recorded at ingest, proves that the plaintext is unchanged. The reasons: decryption is deterministic, and the ingest already verified plaintext SHA-256 and HMAC for exactly those bytes (inference). | S2 §11, S11 | Yes | | | | pending |
| C15 | restic keeps its index in RAM. #1988 reports OOM at about 480–690 MB anon-rss on a 1 GB machine after a ~3 TB, ~2M-file backup. A forum snippet reports up to 30 GB for a 1.2 TB repository (unverified). | S27 | No (bake-off input) | | | | Secondary only |
| C16 | rustic_core 0.13.0 says its API is "in an early development stage" and "subject to change". It opens repositories only with `Credentials::Password` or `Credentials::Masterkey`. Its config supports a `FixedSize` chunker as an alternative to Rabin. Whether restic accepts a repository written with it was not checked. | S10 | Yes | | | | pending |
| C17 | Plakar went 1.1.0 → 1.1.7 between 2026-06-05 and 2026-09-24. Behaviour changed inside the minor series (plaintext repositories need `PLAKAR_INSECURE_PLAINTEXT` from 1.1.5). Some features depend on a vendor authentication flow (1.1.6). | S29 | No (knockout context) | | | | Secondary only |
| C18 | Kopia had a restore regression that corrupted Canon CR2 files (v0.22.2, #5049, fixed by PR #5052). A still-open report (#4769) describes maintenance deleting live blobs on S3 with Object Lock. | S28 | No (context) | | | | Secondary only |
| C20 | The Rust `age` crate 0.12.1 (published 2026-07-14) keeps its header parser (`mod format`) and its header-MAC and payload-key derivation (`mod keys`: `mac_key`, `v1_payload_key`, both `pub(crate)`) private. It does expose `Identity::unwrap_stanza(&Stanza) -> FileKey`, `Recipient::wrap_file_key(&FileKey) -> Vec<Stanza>`, and `FileKey: ExposeSecret<[u8; 16]>`. age-core 0.12.0 exposes `format::read::age_stanza` and `format::write::age_stanza`. A Rust header rewrap therefore uses public key-wrapping APIs plus a small Reliquary-owned header parser, serializer and HKDF-SHA-256 MAC, written to the C2SP spec and tested against Go age (inference: about one screen of code) | S34 (crate source read 2026-09-29) | Yes (A′ feasibility) | | | | pending |
| C21 | Header overhead under A′ if OD-06 = PQ: the stored header {X, R} with two PQ stanzas is 3,184 B and the kept h0 is 1,627 B (A2 C6, measured with Go age 1.3.2). That is about 4.8 KB per object, or about 4.3–21.6 GB at A2's 0.9M–4.5M objects for 2–10 TB. That is about 0.2 % of stored bytes (arithmetic, not measured on family data) | S35 (A2 C6, C21) | No (cost) | | | | pending |
| C22 | If a restore (ADR-0001: "re-encrypting to the target device's own key") is done as a header rewrap under A′, the payload staged in R2 is byte-identical to the payload the device first uploaded. The cloud could then link a restore to the original upload by ciphertext equality, unless it no longer holds the original. Re-encrypting under a fresh file key avoids that link at about 28 h of CPU per 10 TB (A2 Q9 arithmetic). Single restores are small (inference) | S11, S35 | No (A8 input) | | | | pending |
| C19 | A full read audit of 10 TB takes 10¹³ B ÷ (sustained read rate). That is about 27.8 h at 100 MB/s and about 9.3 h at 300 MB/s, both far inside a 720 h monthly window. This is arithmetic, **not a measurement**; A6-S2/A7-S2 measure the real rate. | arithmetic | Yes (BUD-AUDIT feasibility) | | | | pending |

## Findings

### F1. What the posture decides, given the ingest design already in hand

The plan framed the posture as "must the private key be online for ingest?". The CE spike (S2 §11) and A3 F6 already commit the homelab to four things:

- decrypt the whole object;
- recompute SHA-256 and HMAC;
- commit only on a match;
- sign a receipt.

So a key that decrypts incoming objects is online whenever ingest runs (C1). That is continuously, if BUD-TTS is to hold while the owner is away. Nothing in the three plan options changes this. The posture decides the rest:

| Consequence | A: keep received age ciphertext (one homelab key) | **A′: keep the age payload; rewrap the header at ingest to an offline archive recipient; the ingest key rotates** | B: plaintext CAS on ZFS native encryption | C: re-encrypt into restic/Kopia/PBS |
|---|---|---|---|---|
| Key online for ingest | Homelab X25519 identity; decrypts **everything ever stored** | Ingest identity of the current epoch; decrypts **only objects encrypted to that epoch** | Homelab age identity (everything) **and** the ZFS key | Homelab age identity **and** the repository password (everything) |
| Key needed for a ZFS scrub | None | None | None (C10) | None |
| Key needed for an app-level SHA-256 audit | None (C14) | None (C14) | ZFS key loaded | Repository password (`restic check --read-data`) |
| Unattended unlock after a power cut | Read-everything key must auto-load | Only the ingest key must auto-load; it protects data in transit | ZFS key via `file://` or `https://` (C11); read-everything | Password on the box; read-everything |
| Stolen box (disks plus boot drive) | Everything, if the key auto-loads from the box | Content: nothing. Current-epoch in-transit objects, if the ingest key is on the box. Catalog: exposed unless on an encrypted dataset (§F6) | Everything, if `keylocation=file` is on the box. Sizes and dataset names always (C10) | Everything, if the password is on the box |
| Compromised ingest VM (AR-08) | Past and future: everything it can read | Future uploads until the key rotates. Past archive: nothing without the offline key | Everything it can read | Everything it can read (C4) |
| Adding a recovery recipient later | Header rewrap of every object with the private key; about 10 TB rewritten (C2) | **Not needed later:** added at ingest from day one. Changing it later costs the same as A | Not applicable. Recovery means the ZFS passphrase and wrapped keys; `change-key` leaves old wrapped keys on disk (C10) | New repository and `copy` (C4) |
| Derivatives (thumbnails, migrations) | Need the key | At ingest (plaintext in hand), or later with the archive key | Any time | Through the engine |
| Read-only Immich/PhotoPrism view | Needs a decrypted mirror (online key) | Needs a decrypted mirror, which gives up much of A′'s benefit | Possible directly (§F6) | `restic mount` (FUSE) with the password |
| Heir access | `age -d` + identity + catalog export | `age -d` + archive identity + catalog export | OpenZFS-capable Linux + passphrase | restic/rustic binary + password |
| Off-site copy later | Copy ciphertext as it is | Copy ciphertext as it is (already encrypted to an offline key) | `zfs send -w` (C11, C12) or rclone crypt | `restic copy` or rclone |
| Plaintext written to disk at ingest | No, if verification streams (Q15) | No, if verification streams | Yes, by design | Transiently, into the engine |
| Device-signed provenance kept | Yes: the stored object is byte-identical to what the device signed | Payload identical. The signed record binds the *original* header MAC, so keep the original 184-byte header next to the object (§F3) | Record kept; the ciphertext is gone | Record kept separately; the ciphertext is gone |

**Finding (Medium):** A′ is the only posture where neither the always-on key nor the box itself can reveal the archive. It is also the only one where fixity, scrubs and off-site copies need no key at all. Two costs come with it:

- **Operational:**
  - the admin must bring the archive key for restores and catalog rebuilds;
  - the ingest key must be rotated.
- **Product:** OD-13's plaintext gallery becomes a deliberate exception.

Both are acceptable because v1 restore is admin-performed anyway (CLAUDE.md), and BUD-RESTORE budgets 30 minutes of owner time per request.

Prior art for this shape:

- bupstash: put-only keys that "create new backups but not decrypt data", with decryption keys kept offline.
- PBS: a symmetric backup key plus an RSA `master-pubkey` whose private half is kept offline for recovery (S21, S22).

Both keep the reading key off the always-on machine. Neither passes the knockout (§F4), so A′ borrows their idea and uses age as the format.

### F2. Keyless fixity under A and A′ (C14)

- At ingest, record `stored_sha256 = SHA-256(stored bytes)` next to the plain `sha256` and `size`. Record it in the catalog **and** in an append-only manifest file inside the store, so the store can be audited without the catalog.
- A full audit recomputes `stored_sha256` from disk, needs no key, and can run on a separate low-privilege VM with read-only access.
- This is complete integrity evidence, for three reasons:
  - age decryption is deterministic for fixed bytes;
  - the ingest step has already proven that those exact bytes decrypt to content with the recorded SHA-256 and HMAC;
  - the per-chunk AEAD would also detect any change at decrypt time.
- What it does not prove: that the archive identity still exists and works. The restore drills (A7-S4) and BUD-RECOVERY cover that.
- Under B, the equivalent audit is `sha256sum` on the plaintext, where the filename is the expected value (like restic's storage IDs, S4). It needs the dataset mounted.

### F3. A′ mechanics (proposal for ADR-0012; D2 and A2 must agree)

1. The device encrypts to the **ingest recipient of epoch e**, `R_in,e`. This is the "homelab public key" of CLAUDE.md and ADR-0001, published in the signed trust bundle (CE §10).
2. The homelab verifies as in CE §11, streaming, with no plaintext temp file.
3. The homelab writes the stored object:
   - the new header has stanzas for `R_archive` (offline), plus `R_recovery` if OD-08 says so, plus a PQ hybrid if OD-06 says so;
   - the header MAC is recomputed with the file key;
   - the original payload bytes follow unchanged.

   The result is a standard age v1 file: `age -d -i archive.key obj` works (C2).
4. Keep the original device-written header h0 (168 B with one X25519 stanza, 1,627 B with one PQ stanza; A2 C6, CE §5). Store it as an entry in the append-only manifest (§F2), not as a second `<sha256>.h0` file, so the store stays at one file per item (second pass). The device-signed record binds `header_mac` (CE §11 step 3), so this keeps the whole provenance chain verifiable: with X online, recover the file key from the stored header, then recompute h0's MAC. Once `R_in,e` is destroyed, the old header is useless to an attacker.
5. **Rotate** the ingest key (the interval is for D2 to set). Destroy `sk_in,e` once no staged, USB or in-flight object for epoch e remains. The limit comes from the longest path: USB bundles and the device safety valve (A3 DR-A3-3).
   - The payoff: an ingest key captured later, together with R2 ciphertext the cloud may have retained, decrypts nothing older than the retained epochs. This matters because ADR-0001 treats the cloud as under attack.
6. **Metadata records** get the same rewrap and are archived in the store. The catalog is a projection that can be rebuilt from them (A6-S4). A rebuild needs the archive key and is an attended admin task.
7. The payload is never re-encrypted, so the age rule "payload MUST NOT be modified without re-encrypting" does not apply (S11).

Open costs of A′:

- key-epoch bookkeeping in the trust bundle and on the device (A2/D3);
- the restore drill needs a key (hand-off to A7: for example canary items with an extra drill stanza);
- the ingest VM still holds per-object file keys transiently.

### F4. Knockout screen

Criteria (from PLAN A6):

- **K1:** library-driven per-file ingest keyed by our ID.
- **K2:** a specified format with an independent reader.
- **K3:** single-file restore by hash.
- **K4:** licence compatible with G3. OD-15 is not decided; AGPL is flagged, not failed.
- **K5:** fits the recommended posture (A′) or another posture the owner might pick.
- **K6:** maturity. The engine is production-ready by its own statement, which follows from CLAUDE.md "proven".

| Candidate | K1 | K2 | K3 | K4 | K5 | K6 | Result |
|---|---|---|---|---|---|---|---|
| **Plain CAS of age v1 objects on ZFS** (our layout, about a one-page spec) | Pass: we write each object at `sha256` | **Pass for the objects:** age v1 is a C2SP spec with Go and Rust decryptors, both checked in the CE spike (S2). The layout is ours and must be specified in one page (A6-S5) | Pass: the path is the hash | Pass (ours; age tools BSD-3) | Pass (A, A′, B) | Format components proven; **the layout code is new** (A6-S3 crash tests) | **Survives** |
| **OCFL 1.1 storage root** (one object per SHA-256, ext. 0004 layout) | Pass: we write it. rocfl is stale (C9), so we would likely write OCFL ourselves | Pass: spec plus ocfl-py (2026) and rocfl (C9, C13) | Pass: the object ID is the SHA-256; the path is derived via ext. 0004 | Pass | Pass. Content can be age ciphertext; the `fixity` block can carry the plain SHA-256 | Spec stable (2024); Rust tooling stale | **Survives** (as a variant of the CAS) |
| **restic format via restic CLI or rustic_core** | Partial: snapshot-scoped ingest (C5). The rustic_core API is unstable (C16) | Pass: design.rst plus two implementations (S4, S9) | **Fail natively:** CDC blobs, no whole-file hash lookup (C5). Needs our map | Pass (BSD-2; Apache/MIT) | Posture C only: symmetric key, no asymmetric mode (C4; S31 secondary) | restic mature; rustic 0.x | **Survives only as the comparator** (the ADR must show the cost of not adopting it) |
| Kopia | Partial: Go library `NewObjectWriter` (S18); a Go sidecar is needed | **Fail:** no independent reader found (C6) | Fail natively: keyed IDs (C6) | Pass (Apache-2.0) | Posture C only | 0.23.1, pre-1.0; restore and maintenance incidents (C18, secondary) | Knocked out |
| Borg 2 | Fail: CLI only (Python) | Internals documented; no independent reader seen | Fail natively: keyed chunk IDs | Pass (BSD-3) | Posture C only | **Fail: "do not use for production"** (C7) | Knocked out |
| Borg 1.4 | Fail: CLI and SSH server model | as above | Fail | Pass | Posture C only | Stable | Knocked out on K1/K3 |
| Proxmox Backup Server | Fail: pxar archive and snapshot oriented (C8) | Fail: one implementation | Fail natively | AGPL-3.0 (flag for G3) | Weak: server verify of encrypted chunks is CRC-only (C8) | Stable, but the reachable docs are stale | Knocked out as the engine. **Keep it for VM-level backups of the catalog and service VMs** (C8/C12 hand-off) |
| Plakar / Kloset | Partial: Go library | Fail: no format spec found | Fail natively: MAC-addressed | Pass (ISC) | Posture C only | Fail: 1.1.x since June 2026, behaviour changes in minor releases, vendor auth coupling (C17, secondary) | Knocked out; re-screen in 2027 |
| bupstash | Partial (Rust, but CLI oriented) | Fail: one implementation | Fail: keyed BLAKE3 chunks | Pass (MIT per scout) | Nearest to A′ (put-only keys) | **Fail: beta, no release since 2022-11** (C9) | Knocked out; **borrow the key design** |
| git-annex | Fail: Haskell CLI | Plain files plus git; documented (secondary) | Pass: the key is the hash (secondary) | AGPL/GPL (secondary) | Plaintext only | Mature; scale at 5M keys unknown | Knocked out on K1. Borrow `numcopies`/`fsck` ideas (A7) |
| Perkeep | No result (docs host not read) | | | | | | Not screened |

**Finding (High on the facts, Medium on the reading of "proven"):** no backup engine passes K1–K6. The requirement to prefer "an existing, proven format over inventing one" is met at the **object** level by age v1, and optionally at the **layout** level by OCFL 1.1. It is not met by a backup engine. This reading of CLAUDE.md is for the owner to confirm (DR-A6-2).

### F5. Scale: snapshot engines vs per-file ingest (Low: no measurements yet)

- **Index RAM:**
  - Plain CAS and OCFL need no engine index; lookup is a path computation. The catalog is the only index, and its size belongs to ADR-0013.
  - restic loads its index into RAM, and OOMs are reported at about 2M files on 1 GB machines (C15, secondary).
  - At 3–5M whole files, restic holds at least one blob entry per file under 512 KiB and about size/1 MiB entries per larger file. The real count depends on the corpus size mix, so A6-S2 measures it against the RAM < 4 GB criterion. **No result yet.**
- **Snapshots:**
  - Per-file ingest into restic means batching many files into each snapshot, for example one "ingest window" snapshot per hour whose tree paths are SHA-256 names. The alternative, one snapshot per file, is millions of snapshot files.
  - Every restore by hash then needs our map (C5).
- **Verify cost:** a full audit is disk-bound in every design (C19 arithmetic). Sampled audits exist in restic (`--read-data-subset n/t`, S5) and Borg 2 (least-recently-checked first, S19). For a CAS, the same scheme is trivial: audit objects in `stored_sha256` order, one n-th per run.
- **Growth (+1–2 TB/yr):** no engine-specific issue found. Capacity is C5's.

### F6. Readability, browsable views and the catalog's own exposure

- **A browsable tree** can be generated from the catalog without moving originals. Examples: `Person/Year/Year-Month-Day/<original name>`, built with hard links under B, or a decrypted export under A/A′. This follows Immich's default template (S24).
  - Immich must never own or move the originals. #30919 reports 15,620 missing and 12,499 renamed files after a storage-template migration (S30, secondary).
  - Any Immich view must be an *external library* pointed at a read-only generated tree. That mode is **not yet verified**; it goes to C8 for OD-13.
- **The catalog is plaintext** (ADR-0001 §2): names, paths, dates and perhaps GPS. Under A′ it becomes the main thing a thief could read. The catalog and its WAL/backups should therefore live on an encrypted dataset, native ZFS or LUKS (LUKS not researched here). Its unlock mechanism is the real stolen-box question. It goes to C5/D2, for example a `keylocation=https://` key server elsewhere on the LAN (C11).

### F7. Catalog (ADR-0013, Wave 2): requirements fixed by this note

The engine is not trivially decided, so ADR-0013 stays in Wave 2. From A1, A3 and this note, the catalog must:

- store the plain SHA-256 of every item;
- store `stored_sha256`, the header epoch and the recipient set;
- keep sightings per (person, device, source locator), so refcounts for admin-only pruning (SR-20) are *derived*;
- store ingest events, receipts, restore jobs and scrub/audit results;
- be rebuildable from the store's archived records plus the manifest (A6-S4).

F1 already recommends SQLite on devices. Whether the homelab uses SQLite or Postgres (pgBackRest checksums every file and supports resume, per the scout) is left to Wave 2 with its own sources, because sqlite.org and postgresql.org were blocked this run.

### Second pass: reconciliation with A2 and D2

Since the first pass, the D2 and A2 drafts have appeared, and both build on A′. This pass checks that the three notes agree, and records what A6 needs.

| Topic | D2 draft | A2 draft | A6 position (this pass) | Confidence |
|---|---|---|---|---|
| Stored header | {X, R} rewrapped at ingest (K-03b; diagram §F2) | {X, R} written by the homelab at the A′ rewrap (P1) | **Agreed.** ADR-0012 states that every stored object and archived record carries a homelab-written {X, R} header, and that a header scrub can check the stanza set without any key, because stanza *types* are plaintext in age headers (S11). The check must tolerate any random "grease" stanza the encoder adds (age-core has `grease_the_joint`, S34). | High |
| R on the device header | Yes: {I, R}, so late USB bundles survive I's destruction | No (P1): the homelab cannot verify a device-written R stanza (A2 C9), and the PQ header grows to 3,184 B | **Orthogonal to the at-rest posture.** A6 never stores the device's R stanza: it is replaced at rewrap, and h0 is kept only for its MAC. The placement changes only **when I_e may be destroyed**. Under P1, not before the longest drain path (USB in a drawer, A3 DR-A3-3). Under P2, earlier, because R still opens late arrivals. That is an A2/D2 decision (DR-A2-2); A6 accepts either. | Medium |
| Ingest key I unlock | Unattended under A′ (key file or Tang); vTPM excluded | — | Agreed (Q2). | Medium |
| At-rest volume and catalog keys (K-06, K-07) | Must be sealed to R in the doomsday bundle | — | Agreed. Under A′ the catalog dataset is the only one that needs a key (§F6, DR-A6-3). | Medium |
| Rewrap tooling | Go age has no header-rewrite API; upstream closed the request (D2 C14) | Go age decrypts and rewraps at home | The Rust ingest service can do it with public `age` 0.12.1 APIs plus its own header code (C20). Use Go age as the interop oracle (A2-S3). Proposed A6-S6 and D2-S2 should share one test vector set. | Medium-high |
| Overhead | 3,184 B with two PQ stanzas (D2 C4) | Same (A2 C6) | About 4.8 KB per object including h0, about 0.2 % (C21). Not a reason to change posture. | Medium |
| Restore delivery | — | — | Hand-off to A8: prefer fresh re-encryption over header rewrap for R2 restores, to avoid the linkability in C22. A header rewrap is fine for USB restores that never touch the cloud. | Medium |

No conflict found that would change the recommendation.

### Alternatives compared

| Option | Fit with settled requirements | Pros | Cons | Evidence |
|---|---|---|---|---|
| **A′ + plain CAS of age objects on ZFS** (recommended) | Fits. Devices still encrypt to "the homelab public key"; the admin can decrypt everything | Keyless audits and scrubs; stolen box and ingest compromise reveal no archive; heir needs only `age`; off-site copies trivial; no engine index; stored bytes = device-uploaded payload | New layout code (crash-safety is on us: A6-S3); key-epoch rotation duty; restores need the admin's archive key; gallery harder; filenames leak SHA-256 to a disk thief (DR-A6-3) | C1–C3, C10, C11, C14 |
| A + plain CAS (keep ciphertext, one key) | Fits | Simplest; stored bytes identical to the upload | The always-on key reads everything; adding a recovery recipient later means a 10 TB rewrite | C1, C2 |
| B: plaintext CAS on ZFS native encryption | Fits | Simplest restores, derivatives and views; `sha256sum` = filename | Unattended unlock = read-everything; ZFS encryption send/recv history; heir needs OpenZFS; sizes and names of datasets exposed | C10–C12 |
| C: restic via rustic_core or the CLI | Fits the letter of "proven format" | Proven engine; independent reader; compression; `check --read-data-subset` | Symmetric key online for everything; re-key = full copy; restore by hash needs a map; index RAM; loses the device ciphertext | C4, C5, C15, C16 |
| OCFL 1.1 layout over A′ objects | Fits | Self-describing storage root (`0=ocfl_1.1`, `ocfl_layout.json`); standard inventories; two independent tool families | About 9 inodes per item vs 1; stale Rust library; little benefit for immutable single-version objects | C9, C13 |
| Kopia, Borg 2, PBS, Plakar, bupstash, git-annex | See §F4 | See §F4 | Knocked out | C6–C9, C17 |

### Similar work and lessons

| Project | What they do | Borrow or avoid | Source |
|---|---|---|---|
| restic / rest-server | Files named by the SHA-256 of their content; write-once; append-only server mode; same layout locally and over REST | **Borrow:** `sha256sum`-checkable naming, write-once, `--read-data-subset n/t` rotation. **Avoid:** a symmetric key on the ingest host | S4, S5, S7 |
| rustic | Independent reimplementation that cross-verifies with restic | Borrow the "second implementation" test (A6-S5) | S9 |
| bupstash | Put-only sub-keys; decryption keys offline | **Borrow the key model for A′** | S22 |
| PBS | `.chunks/<4 hex>/<digest>` store; keyed digests for encrypted chunks; RSA master pubkey for recovery; scheduled verify jobs | Borrow the fan-out and verify-job cadence; offline recovery key. Avoid CRC-only verification of ciphertext (we record `stored_sha256` instead) | S21 |
| OCFL / Fedora | Plain-file longevity, inventories, immutable versions | Borrow the self-describing root and the manifest idea, even without full OCFL | S14, S15 |
| Kopia | Keyed IDs, packs, Reed-Solomon ECC (experimental) | Avoid packs for keepsakes. Treat restore regressions (#5049) as a reason to SHA-256-verify every restore | S17, C18 |
| Immich storage template | Admin-set `Year/Year-Month-Day/Filename` | Borrow for a *generated* view. Never let an app move originals (#30919) | S24, S30 |
| Duplicati 2 | Local DB rebuilt from the remote takes days | **Avoid:** the store must be auditable and restorable without the catalog, and the catalog rebuildable (A6-S4) | S32 (secondary) |

### Tools and libraries

| Name | Purpose | Licence | Maturity | Source |
|---|---|---|---|---|
| age (Go), `age` crate (Rust) | Object format; independent decryptors | BSD-3 / MIT-Apache (per CE) | Used in the CE spike; 161/161 checks | S2, S11 |
| OpenZFS | Filesystem, scrubs, snapshots, optional native encryption | CDDL | master 2.4.99; 2.4.0 tagged | S12, S13 |
| rustic_core | restic-format library for the comparator | Apache-2.0 OR MIT | 0.13.0 (2026-08-16), "early development" | S10 |
| restic + rest-server | Comparator; append-only reference | BSD-2 | v0.19.1 (2026-07-05) | S4, S7, S8 |
| ocfl-py, rocfl | OCFL validation and independent reader | (not checked) | ocfl-py 2.1.0 (2026-06-26); rocfl 1.7.0 (2022-10-08) | S16 |
| LazyFS | Crash-consistency fault injection for A6-S3 | (not checked) | README tested on ext4 (scout) | scout |

## Spikes

The spike runner fills in this section. Planned spikes, from PLAN A6:

| Spike | Hypothesis | Pass → / fail → (decision) | Exec tag | Budget IDs | Data class | Status | Result |
|---|---|---|---|---|---|---|---|
| A6-S1 Posture decision matrix | This note §F1 is the matrix; the owner picks (OD-07) | Owner picks A′ → ADR-0012 as drafted; picks B or C → re-screen §F4 | CT → owner | BUD-TTS, BUD-RESTORE, BUD-RECOVERY | SYN → results | Matrix drafted here | Pending owner |
| A6-S2 Bake-off of ≤ 3 engines (plain CAS, OCFL variant, restic/rustic comparator) | Plain CAS meets every budget with RAM ≪ 4 GB | Pass → CAS; fail → reconsider restic (posture C) | OL (Wave 2; kit) | BUD-INGEST, BUD-RESTORE, BUD-AUDIT | H3 corpus → AGG | Kit (spike runner) | — |
| A6-S3 Crash consistency (kill -9 ×100, power cut ×10, LazyFS; add disk-full per Kopia #4348) | No acknowledged item lost | Pass → layout code acceptable; fail → fix or adopt an engine | CT/OL | — | SYN | Spike runner | — |
| A6-S4 Catalog loss → rebuild from store | Byte-identical canonical export | Pass → catalog is a projection; fail → back up the catalog as primary data | CT | — | SYN | Spike runner | — |
| A6-S5 Format independence (coreutils + age + sqlite3; restic ↔ rustic) | A one-page procedure restores byte-identical files | Pass → weight in ADR-0012 | CT | BUD-RECOVERY (proxy) | SYN | Spike runner | — |
| (proposed) A6-S6 A′ rewrap round-trip | Header rewrap at ingest yields files that `age -d` (Go and Rust) decrypts with the archive key, and the original header still verifies against the device record | Pass → A′ feasible; fail → A | CT | — | SYN | Proposed | — |

No emulator stands in for real hardware in any result above. None has run yet.

## Conflicts with settled text

- **None found.** A′ keeps "content and metadata are encrypted on the device to the homelab public key", and the admin still holds every private key. Two notes:
  - "the homelab private key" becomes a small set of keys: ingest epochs, archive, recovery. D2 records this in ADR-0008.
  - DR-A6-2 asks the owner to confirm the reading of "prefer an existing, proven format".
- ADR-0001 §2 says the homelab "decrypts with private key" and keeps a "plaintext catalog (e.g. Postgres)". Both still hold. "e.g." leaves ADR-0013 free.

## Open questions

| Question | Who | By when |
|---|---|---|
| Key epochs, archive and recovery custody; rotation interval; destruction proof | D2 (ADR-0008) | Gate A |
| Catalog unlock mechanism (ZFS `https://` key server vs TPM vs prompt) and the dataset layout | C5, D2 | Gate A |
| Owner's current setup: Proxmox/PBS versions, existing encryption, free RAM, bake-off space (intake C1, C3, C5, C6, C12) | H2 | Wave 1 exit |
| restic index RAM and audit throughput on the real corpus | A6-S2 (OL) | Wave 2 |
| Is raw encrypted send reliable on Linux OpenZFS 2.4.x? Relevant only to B | C5 (if B is chosen) | Gate C |
| Does restic read a rustic `FixedSize`-chunker repository? Relevant only to the comparator | A6-S2 | Wave 2 |
| Immich external-library read-only mode over a generated tree | C8 (OD-13) | Wave 2 |
| PBS 4.x current docs (mirror stale) | H1 (route) | Before C8 relies on PBS |
| Device recipient placement (P1 vs P2), which sets when I_e can be destroyed | A2 + D2 (DR-A2-2); A6 accepts either | Gate A |
| Restore delivery by fresh re-encryption vs header rewrap (C22) | A8 | ADR-0028 |
| One shared rewrap test vector set for A6-S6, D2-S2 and A2-S3 | A2, D2, A6 | Wave 2 |

## Recommendation

1. **Posture (OD-07): A′.** Keep each object as a standard age v1 file whose payload is byte-identical to what the device uploaded. Rewrap the header at ingest to an offline archive recipient, plus a recovery recipient if OD-08 wants one. Rotate and destroy ingest keys.
   - Why: it is the only option in which the always-on key and the box itself cannot reveal the archive, and in which audits, scrubs and future off-site copies need no key.
   - What would change it:
     - the owner wants an automatic plaintext gallery in v1 (OD-13), which points to B;
     - the owner rejects attended restores, which points to A;
     - D2 finds key-epoch rotation too costly, which points to A with a recovery stanza from day one.
2. **Engine (ADR-0012): a plain content-addressed store of age objects on ZFS,** addressed by plain SHA-256 (A1). Use a PBS-style hex fan-out and an append-only manifest, specified in one page. Decide the OCFL wrapper and confirm against the restic comparator in the A6-S2 bake-off. No backup engine passes the knockout.
3. **Catalog (ADR-0013):** Wave 2, with the requirements in §F7.

## Decision requests

### OD-07: Homelab at-rest posture

- **Needed by:** Gate A (one-way door #4).
- **Evidence:** this note §F1–F3; CE §11, §16 D-3; D1 AR-08.
- **Options:**

  | Option | What it means for the family | Cost (money and owner time) | Reversibility | Risks |
  |---|---|---|---|---|
  | A′ (recommended) | Nothing visible. Restores need the owner's archive key (paper or hardware) | Key ceremony; ingest-key rotation (automated); a few minutes per restore session to load the key | Costly: moving to B or C later means decrypting or re-encrypting 10 TB | New code path (rewrap); key bookkeeping |
  | A | Nothing visible | Least work | Costly | The always-on key reads everything; recovery recipient later = 10 TB rewrite |
  | B | Easiest path to a family gallery later | ZFS key handling | Costly | Auto-unlock = read-everything; ZFS encryption send/recv history |
  | C | Nothing visible | Engine operations; re-key = full copy | Costly | Symmetric key reads everything; restore by hash needs a map |

- **Recommendation:** A′, for the reasons in §Recommendation 1.
- **Touches settled text:** none (see Conflicts).
- **If no decision by the deadline:** assume A′ in the ADR-0012 draft. That blocks nothing except OD-13's gallery design.

### DR-A6-1: Bake-off shortlist for A6-S2

- **Options:**
  - (a) plain CAS, the OCFL variant and the restic comparator;
  - (b) plain CAS only.
- **Recommendation:** (a). Keeping restic lets ADR-0012 show, with measurements, the cost of not adopting a proven engine.
- **Touches settled text:** no.
- **Default:** (a).

### DR-A6-2: Reading of "prefer an existing, proven format over inventing one" (CLAUDE.md)

- **Proposed reading:** the format is age v1 per object (C2SP spec, two independent implementations), optionally in an OCFL 1.1 storage root. Our own contribution is a one-page directory convention.
- **Alternative:** the owner means "a proven backup engine", which forces posture C and restic.
- **Recommendation:** the proposed reading.
- **Touches settled text:** it interprets a CLAUDE.md line without changing it. If the owner disagrees, the alternative applies and this note's recommendation flips to C.
- **Default:** the proposed reading.

### DR-A6-3: Stored-object names reveal plain SHA-256 to someone holding the disks

- **Options:**
  - (a) accept. This fits "privacy against outsiders" only if disk theft is an accepted risk; it goes to OD-17.
  - (b) put the store on a ZFS-encrypted dataset too. Names are then hidden when locked, at the cost of the unlock question.
  - (c) keyed names, HMAC(store key, sha256). The heir procedure then needs the store key.
- **Recommendation:** (b) if C5/D2 pick a theft-resistant unlock for the catalog anyway; the same mechanism covers both. Otherwise (a), recorded in OD-17.
- **Touches settled text:** no.
- **Default:** (a), recorded as an accepted risk.

## Hand-offs

| To | What | Why |
|---|---|---|
| D2 | Key set for A′: ingest epochs (rotation, destruction), offline archive identity, recovery recipient (not scrypt: C3), hardware `p256tag` option | ADR-0008 owns custody |
| A2 | Header rewrap at ingest; keep the original header `h0` so the record's `header_mac` binding stays verifiable; epoch ID in the trust bundle | Object format, CE §10–11 |
| A3 | `put_blob` stores ciphertext; verify by streaming (no plaintext temp); record `stored_sha256` | F6 contract |
| A7 | Keyless audit by `stored_sha256`; the restore drill needs a key (canary items with a drill stanza?) | ADR-0029 |
| C5 / C6 | Datasets: store (ciphertext; encryption optional), catalog and temp (encrypted), unlock mechanism; PBS-style fan-out | ADR-0030/0031 |
| C8 | Keep PBS for VM and catalog backups (intake C12); Immich external-library check for OD-13 | ADR-0032 |
| D1 | Revisit AR-08: under A′, an ingest compromise is bounded to the open key epochs | Threat register |
| E7 / OD-08 | Recovery recipient added at ingest, not on devices (smaller device header), if D2 agrees | Life events |
| H1 | Blocked sources listed in Method; the stale PBS mirror; git.proxmox.com (403); GitHub API for restic/restic | `sources.md` |
| A8 | Restores to R2: re-encrypt under a fresh file key rather than rewrap the header, to avoid ciphertext linkability (C22) | ADR-0028 |
| A2, D2 | A6 accepts P1 or P2 (DR-A2-2). A6 requires a homelab-written {X, R} stored header and h0 kept in the manifest. A Rust rewrap can use public `age` APIs (C20) | Joint Gate A review |
