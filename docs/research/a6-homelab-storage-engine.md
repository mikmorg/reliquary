# A6. Homelab at-rest posture, storage engine and catalog

- **Workstream:** A6 (see `docs/research/PLAN.md`, section "A6.")
- **Status:** Final for Wave 1 (batch W1-b). It merges three analyst passes, two rounds of review by three skeptic lenses (sources, logic, adversary) and two spike-runner passes. The bake-off (A6-S2) and the catalog (ADR-0013) are Wave 2.
- **Date:** 2026-09-29. Last updated 2026-10-07 (second review round and synthesis). The run started on the task date of 2026-09-29 and ran to the environment date of 2026-10-07, so access dates in this note fall in that range.
- **Wave 1 scope:** the at-rest posture (OD-07, one-way door #4) and the knockout screen of storage engines, for the ADR-0012 draft. Only the bake-off kit is written now. The catalog engine is not trivially decided, so it stays in Wave 2 (§F7).
- **Feeds:** [ADR-0012 (Proposed)](../adr/0012-homelab-at-rest-posture-and-storage-engine.md); OD-07; one-way door #4; decision requests DR-A6-1 to DR-A6-5 (H1 assigns OD numbers). Also evidence for OD-06 (PQ readers), OD-08 (recovery recipient), OD-13 (read-only gallery), OD-16 (derivatives) and OD-17 (accepted risks).
- **Depends on:**
  - the CE spike (`content-encryption-format.md`, also T1 spike 2);
  - A1: the store is addressed by plain SHA-256;
  - A2: `a2-object-envelope.md` and `docs/spec/object-format.md`;
  - A3: durable-commit contract F6;
  - D1: `docs/security/threat-model.md` (SR-04, SR-20, AR-07, AR-08);
  - D2: `d2-key-hierarchy-custody-recovery.md` and the Proposed ADR-0008;
  - C5: hardware and filesystem;
  - owner intake answers C1, C3, C5, C6 and C12, not yet given.
- **Traceability rows advanced:** R-09, R-26, R-28, R-38, R-45, R-46, OPEN-2, Q1-1 (see `docs/research/traceability.md`)

## Summary

1. **The posture choice is narrower than the plan assumed.** The ingest design in hand (CE §11, A3 F6, SR-04) decrypts every object to verify it before commit. So, **as long as SR-04 stands**, a key that can decrypt incoming objects is online at ingest in every posture (C1, verified). What the owner actually chooses:
   - which key that is and what else it can open;
   - which operations need the owner;
   - what a compromised running host can read.

   What a stolen box exposes depends mostly on how keys unlock after a power cut, and that choice is separate from the posture (§F1).
2. **Recommendation for the owner (OD-07): the "offline archive key" posture.** Each stored object stays a standard age v1 file whose header names only an offline archive recipient X, plus R if OD-08 accepts it. The always-on ingest key I_e protects only data in transit, and it rotates. The one-way door is this family as a whole. There are two ways to build it, and both produce the same kind of stored file, so the choice between them can be reversed for new objects:
   - **A′, rewrap:** keep the device payload byte for byte and rewrite only the header. A6 leans this way, because it keeps an independent second path to each file key and costs about 1.4–1.5× less wall time. It needs the device header h0 sealed.
   - **A″, fresh key:** re-encrypt under a fresh file key. This is simpler: no h0 handling and no file-key reuse question.

   A6-S7 decides between them before Gate A (§F1b).
3. **What this posture buys, stated narrowly (corrected in review round 2).**
   - **Compared with A on the same unlock mechanism,** it changes what the always-loaded key and a compromised ingest VM can read: objects in transit only, never stored content (A6-S1 Probe 2: 0/535; A6-S6: 0/176). Under A that key opens everything.
   - **For a stolen box,** the advantage holds only against unlock methods a thief can also trigger: a key file on the box, or Tang in the same house. If A, B or C use a key server off the premises, or an attended unlock, all four postures protect stored content from theft of a powered-off box equally.
   - **Keyless properties are not a reason to prefer it.** ZFS scrubs, bit-rot audits and off-site copies need no key under A as well.
   - **What it does not protect:** metadata (the plaintext catalog), clear derivatives, and the integrity of the store against an attacker who can write to it (§F8).
4. **The posture has real costs, and the review made them sharper.**
   - The owner has to bring X online for restores, catalog rebuilds, real-object restore drills and X audits.
   - **X must be loaded only in a separate, freshly booted environment, never on the ingest VM.** Otherwise a persistent attacker captures X at the first attended session, and the posture collapses to A (§F3 item 6).
   - Nothing online can prove that a stored header opens with X. The unattended audit therefore proves only that bytes have not changed, so BUD-AUDIT's "full app-level audit" needs a definition for this posture (DR-A6-5).
   - A compromised ingest VM can silently write unopenable headers for new commits while receipts still say "protected". A deterministic h1 checked by an isolated verifier is proposed as the fix (§F3 item 5). It is not built.
5. **Knockout screen: none of the *screened* backup engines passes.** restic/rustic, Kopia, Borg 2, PBS, Plakar/Kloset, bupstash and git-annex each fail at least one criterion. Each knockout rests on a verified primary source, except Plakar's maturity point, which is weak; Plakar is knocked out on the missing format spec and on restore by hash (§F4). The screen is incomplete: Perkeep, Duplicacy, duplicity, rdedup, Bareos/Bacula, Tahoe-LAFS and self-hosted S3 stores were not screened. The design that passes is age v1 per object in a **plain content-addressed store on ZFS, named by plain SHA-256**, with a one-page layout spec. OCFL 1.1 is an optional wrapper. The Wave 2 bake-off covers plain CAS, the OCFL variant and restic as an out-of-screen comparator (A6-S2 kit).
6. **Confidence:**
   - **High** on the knockout facts.
   - **Medium** on recommending the offline-archive-key posture. The mechanics are measured in a container (A6-S1, A6-S6). The sealed-h0 form, the write-time self-check, the deterministic h1 and the separate X environment are designs that are not yet built.
   - **Low** on scale numbers: only arithmetic and a tmpfs smoke run exist.

## Questions

| # | Question | Short answer | Confidence |
|---|---|---|---|
| 1 | Posture: must the private key be online for ingest and for scrubs? | **Ingest: yes in every posture, given SR-04** (C1).<br>**Scrubs:** a ZFS scrub never needs keys, even under native encryption, in every released OpenZFS up to 2.4.4. The opt-in "thorough" scrub, which does need keys, exists only on master (C10).<br>**Bit-rot audit of stored bytes:** keyless under A and A′; keyless at file level under restic (A6-S1 Probe 3); needs the dataset key under B; needs the password or an external hash list under Kopia.<br>**Proof that X opens a stored object:** needs X under A′ and A″ (C14 contested; §F2). | High (facts); Medium (A′ design) |
| 2 | Unattended unlock after a power cut | Under A′/A″ only I_e has to come up unattended. ADR-0008 proposes clevis/Tang into tmpfs. Under A, B and C the auto-loaded key reads everything. ZFS `keylocation` can be `prompt`, `file://`, `https://` or `http://` (C11).<br>**A Tang server or key server in the same house gives no protection against someone who takes the whole homelab.** Theft resistance needs an off-premises key server or an attended unlock. That is equally true for every posture and for the catalog dataset. The mechanism belongs to C5/D2. | High (options); Medium (ranking) |
| 3 | Derivative generation | Derivatives need plaintext. A derivative stored in the clear, or on a dataset whose key auto-loads, is a visual copy of the archive. Under A′/A″ a kept derivative is therefore either encrypted to {X, R} or stored on the catalog's encrypted dataset, where it is exposed in the same way that dataset is. Under B derivatives can be made at any time; under C, through the engine with the password. Whether derivatives are kept at all is OD-16 (A7). | Medium |
| 4 | Cost of adding a recovery recipient later | It is a header rewrap, not a payload re-encryption (C2, verified). It still rewrites every byte of a one-file-per-object store, because the header sits at the front. A6-S1 Probe 1 (tmpfs, single process, 229.56 MB): payload unchanged 535/535, all bytes rewritten. Wall time was 1.68–1.75 s for the rewrap and 2.51–2.58 s for full re-encryption, about 1.4–1.5×. D2-S2 measured 1M in-memory PQ header rewraps in 186.0 s of **wall time with 4 workers** (pool of 1,024 objects). So the whole-store cost is I/O-bound (inference).<br>Avoid the cost by writing {X, R} at ingest from day one. A passphrase (scrypt) stanza must be the only stanza in a header (C3, verified). R must therefore be an X25519, `mlkem768x25519` or tagged identity. A passphrase can still protect R's *identity file*. | High (spec, measured); Medium (extrapolation) |
| 5 | What a stolen box exposes | See the §F1 matrix, which now has an equal-unlock comparison.<br>**Under A′/A″** (h0 sealed under A′): no stored content. If I_e can be unlocked by the thief, open-epoch objects still in staging or on USB are exposed. Exact plaintext sizes and file presence leak from plain-SHA-256 names (A6-S1 Probe 4: sizes 535/535, presence 50/50). The catalog and clear derivatives are exposed unless their dataset key is off the premises.<br>**Under A, B and C:** everything, if the key auto-loads by a route the thief can also use. Nothing extra, if the unlock is off-premises or attended.<br>ZFS never encrypts file sizes, dataset or snapshot names, or dedup tables (C10). | Medium |
| 6 | Can an heir read it? | **Under A, A′ and A″: yes,** with stock age, the archive or recovery identity, and a catalog export or the decrypted records.<br>**If OD-06 = PQ:** one independent CLI *implementation* reads `mlkem768x25519` today, Go age ≥ 1.3 (C30). Other CLIs (Debian age 1.1.1, rage) can read it through `age-plugin-pq` from Go age v1.3.2 once the identity is converted with `age-plugin-pq -identity` (C33; D2 measured Debian age 1.1.1 + plugin). The plugin is Go-age code, so independence does not improve. Library readers typage 0.3.1 and kage 0.8.0 pass the CCTV hybrid vectors (A2-S3), but neither has been tested on whole files from the A6-S5 corpus. The doomsday kit therefore carries static Go age v1.3.2, `age-plugin-pq` and one non-Go reader, aligned with D2.<br>**Under B:** OpenZFS on Linux plus the passphrase. **Under C:** restic or rustic plus the password. | Medium |
| 7 | Optional read-only Immich/PhotoPrism view | It needs plaintext on disk. B allows it through a generated read-only tree. A, A′ and A″ need a decrypted mirror, which brings back an online read key and gives up the posture's benefit. Never let Immich own or move originals: #30919 reports thousands of missing or renamed files after a storage-template migration (secondary). OD-13 and C8 decide whether any view exists. | Medium |
| 8 | Knockout criteria | K1: library-driven per-file ingest keyed by our ID.<br>K2: specified format with an independent reader.<br>K3: single-file restore by plain SHA-256 **using only the store itself** (its paths or an in-store, self-describing manifest), with no external map; applied the same way to every candidate.<br>K4: licence (G3).<br>K5: fit with *any* posture the owner might pick.<br>K6: maturity, from CLAUDE.md "proven".<br>For build-our-own candidates K1 and K6 are n/a, and substitute evidence is named (§F4). | High |
| 9 | Snapshot engines vs continuous per-file ingest at 3–5M objects, 10 TB, +1–2 TB/yr | A plain CAS needs no engine index: the path is the hash and the catalog is the index. restic holds its index in RAM, with OOM reports around 2M files on 1 GB machines (C15, secondary).<br>Full read of 10 TB, as arithmetic only (C19, secondary): **≥ 27.8 h at 100 MB/s, 9.3 h at 300 MB/s**; 10 TiB at 100 MB/s ≈ 30.5 h. Per-file seeks add roughly 8–14 h at an assumed 10 ms per access for 3–5M files. The monthly ZFS scrub reads the same disks again.<br>A6-S2 measures MB/s **and files/s**. | Low (numbers); Medium (shape) |
| 10 | Readability without Reliquary: browsable tree vs opaque packs | A CAS of whole age files is not browsable, but each object is self-contained and opens with stock age. Packs (restic, Kopia, Borg, Kloset) need the engine or a reimplementation. A browsable tree can be generated from the catalog. | High |
| 11 | Catalog: Postgres vs SQLite | **Open; Wave 2 (ADR-0013).** It must also screen the PLAN's "event log with projections" alternative, which the manifest-plus-rebuild design already resembles (A6-S4). Requirements fixed now: §F7. sqlite.org and postgresql.org were blocked. | n/a |
| 12 | Admin-only pruning with cross-user dedup | A blob is deletable only when no live item from any person references it. The refcount is derived from catalog sightings and never stored on its own. Deletion goes through a separately credentialed, verify-before-destroy admin step (SR-20). Store immutability against the ingest credentials: §F8. Details: ADR-0013. | Medium |
| 13 | Keep a future off-site copy easy | **Under A, A′ and A″:** copy the ciphertext files as they are (rclone, rsync, non-raw `zfs send`).<br>**Under B:** raw `zfs send -w`, which has a bug history (C12, secondary), or rclone crypt.<br>**Under C:** `restic copy`. | Medium-high |
| 14 | Do plain-SHA-256 file names leak anything? | Yes, to someone holding the disks: file presence (A6-S1 Probe 4, 50/50). Exact sizes also leak (535/535), so renaming alone does not stop confirmation of large or uniquely sized files. The cloud never sees these names. Options and the corrected recommendation: DR-A6-3. | High (measured) |
| 15 | Is the prototype's "decrypt to a temp file" step needed? | Not under A or A′. Ingest can verify SHA-256 and HMAC by streaming, and store the ciphertext it already has. | Medium |
| 16 | Can A′ verify the rewrapped header at ingest without X? | Not by decryption. Without X it can check that:<br>• the header has the right shape and stanza types;<br>• its MAC verifies under the in-memory file key;<br>• the bytes read back from disk equal the bytes written;<br>• each stanza is a correct wrap to the **pinned** X and R public keys, by recomputing it.<br>It cannot prove that the holder of X still has the private key. It also gives **no** assurance if the ingest VM itself is compromised (§F3 item 5). | Medium (design, not built) |
| 17 | Does the posture protect the homelab store from a compromised ingest VM or ransomware writing to it? | No. The posture is about confidentiality. Integrity against an attacker who can write needs write-once objects, held snapshots and an off-box anchor (§F8), plus redundancy for repair (§F2). | Medium |
| 18 | (new, round 2) What does rotating or replacing X cost? | Under A′/A″ it costs the same as adding R later: a rewrap of every object, which rewrites the whole store. That is the cost after a suspected X compromise. A header-sidecar layout (each header stored beside a header-free payload) would cut it to kilobytes per object. This is a Wave 2 layout option (§F8). | Medium (inference) |
| 19 | (new, round 2) Where is X used? | Not specified until now. Requirement: in a separate, freshly booted restore and audit environment with read-only store access, or on the air-gapped ceremony machine with exported objects; **never on the ingest VM**. A VM on the same Proxmox host protects against compromise of the ingest VM, not of the host. | Medium (design) |

## Method

- **Sweep:** three scouts (docs, source, community), then three analyst passes:
  - 2026-09-29: deep read;
  - 2026-09-29: reconciliation with the A2 and D2 drafts;
  - 2026-10-06: re-verification of the load-bearing sources, and reconciliation with the Proposed ADR-0008 and the prior-run spikes.
- **Skeptic review:** two rounds of three lenses (sources, logic, adversary), on 2026-10-06 and 2026-10-07. **The claim tally of record is round 2.** It was computed in code: verified = a primary source exists and at least 2 of 3 skeptics did not refute; secondary only = no primary source; contested = otherwise. Every critical and major issue from both rounds is answered in [Review response](#review-response).
- **Synthesis checks (2026-10-07):**
  - proxy.golang.org: Plakar `v1.0.1`, `v1.0.6`, `v1.1.0` and `v1.1.7` `.info`, and the Kloset version list (C34);
  - the Go age v1.3.2 module zip: `extra/age-plugin-pq/plugin-pq.go` usage text (C33);
  - ADR-0008 Decision 1 and Decision 6 text (C29r; placement rules);
  - `object-format.md` §5 and §6.1 (stored-v1 profile; hedged derivation);
  - D2-S2 README (wall time and workers);
  - the threat model's AR-08 text.
- **Spikes:** the spike runner ran A6-S1, A6-S3, A6-S4, A6-S5 and A6-S6 in the container. It wrote kits for A6-S1-B, A6-S2 and A6-S3-OL (§Spikes).
- **Routes used:** raw.githubusercontent.com (vendor docs and source mirrors); static.crates.io and the crates.io API; PyPI JSON; proxy.golang.org; registry.npmjs.org (A2); WebFetch of github.com issue and release pages (skeptics and scouts).
- **Blocked sources.** None was silently replaced. Each is reported to H1:
  - restic.readthedocs.io and restic.net: the mirror `restic/restic @ master : doc/` was used;
  - kopia.io: the mirror `kopia/kopia @ master : site/content/docs` was used;
  - ocfl.io: the mirror `OCFL/spec` was used;
  - openzfs.github.io: the man pages were used instead;
  - c2sp.org: the editor's copy `C2SP/C2SP @ main : age.md` was used;
  - docs.immich.app;
  - pbs.proxmox.com, pve.proxmox.com, www.proxmox.com, forum.proxmox.com, download.proxmox.com and git.proxmox.com (proxy CONNECT 403 and WebFetch `EGRESS_BLOCKED`). The only primary PBS source is the GitHub mirror, which is stale at 3.2.4. PBS 4.x is known only from secondary sources (C35);
  - git-annex.branchable.com: git-annex is secondary only;
  - forum.restic.net and forum.duplicati.com: snippets only;
  - www.sqlite.org and www.postgresql.org: catalog facts not gathered (Wave 2);
  - rustic.cli.rs, hn.algolia.com, reddit.com;
  - restic/restic through `gh api` and the GitHub MCP (403, "GitHub access to this repository is not enabled"). #187 was read only through a summarising WebFetch, and #533 only through search results;
  - perkeep.org: Perkeep is **no result**.
- **Stop rule:** round 2 added three primary facts: `age-plugin-pq`, Plakar's 1.0.x history and the Kloset 1.2 alphas. None changes a knockout. No further sweep was run for the Wave 1 scope.

## Sources

| # | Source (title and URL or mirror path) | Publisher | Published or version date | Accessed | Primary? |
|---|---|---|---|---|---|
| S1 | `CLAUDE.md`; ADR-0001 `docs/adr/0001-cloud-staging-on-r2.md` | Project | Accepted | 2026-09-29 | Yes (settled text) |
| S2 | CE spike `docs/research/content-encryption-format.md` §§1, 5.5, 11, 12, 16 | Project (T1 spike 2) | 2026-09-29 | 2026-09-29; skeptics 2026-10-07 | Yes (project spike) |
| S3 | A3 `a3-ingest-protocol.md` F6; A1 `a1-content-identity.md`; D1 `d1-threat-model.md` and `docs/security/threat-model.md` (SR-04, SR-20, AR-07, AR-08 §6c, TB4); F1 `f1-build-adopt-fork-compose.md` | Project | 2026-09-29 / 2026-10-06 | 2026-10-07 | Yes (project drafts) |
| S4 | restic design, `restic/restic @ master : doc/design.rst` | restic | master head | 2026-10-06; skeptics re-read 2026-10-07 | Yes |
| S5 | restic "Working with repositories", `… : doc/045_working_with_repos.rst` | restic | master head | 2026-09-29 | Yes |
| S6 | restic "Backing up" and "Restoring", `… : doc/040_backup.rst`, `doc/050_restore.rst` | restic | master head | 2026-09-29 | Yes |
| S7 | rest-server README, `restic/rest-server @ master : README.md` | restic | master head | 2026-10-06 | Yes |
| S8 | restic latest version, proxy.golang.org `github.com/restic/restic/@latest` | Go module proxy | v0.19.1, 2026-07-05 | 2026-09-29; skeptic 2026-10-07 | Yes |
| S9 | rustic README, `rustic-rs/rustic @ main : README.md` | rustic-rs | main head | 2026-09-29 | Yes |
| S10 | rustic_core 0.13.0 crate: `README.md`, `Cargo.toml`, `src/repofile/configfile.rs`, `src/repository/credentials.rs`, `src/repository.rs`, `src/chunker/fixed_size.rs` (static.crates.io) | rustic-rs | 0.13.0, updated 2026-08-16 | 2026-10-06; skeptics 2026-10-07 | Yes |
| S11 | C2SP age v1 spec, `C2SP/C2SP @ main : age.md` (editor's copy of c2sp.org/age) | C2SP | main head | 2026-10-06; skeptics re-read 2026-10-07 | Yes |
| S12 | OpenZFS `zfs-load-key(8)`, `zfsprops(7)`, `zfs-send(8)`, `zpool-scrub(8)`, `META` (`openzfs/zfs @ master : man/…`) | OpenZFS | master = 2.4.99; `zfs-load-key.8` .Dd 2026-01-30; `zpool-scrub.8` .Dd 2026-05-01 | 2026-10-06; skeptics 2026-10-07 | Yes |
| S13 | OpenZFS `zpool-scrub(8)` and `META` at tags `zfs-2.4.0` and `zfs-2.4.4` | OpenZFS | 2.4.4 is the newest tag found. `zfs-2.4.5`, `2.4.6`, `2.5.0` and `2.5.0-rc1` returned 404 on 2026-10-07 | 2026-10-06 / 2026-10-07 | Yes |
| S14 | OCFL 1.1 spec, `OCFL/spec @ main : 1.1/spec/index.md` | OCFL editors | 2022-10-07, updated 2024-11-07 | 2026-09-29 | Yes |
| S15 | OCFL extension 0004, `OCFL/extensions @ main : docs/0004-hashed-n-tuple-storage-layout.md` | OCFL community | extensions v1.0 | 2026-09-29 | Yes |
| S16 | rocfl (crates.io API); ocfl-py (PyPI JSON) | crates.io, PyPI | rocfl 1.7.0 (2022-10-08); ocfl-py 2.1.0 (2026-06-26) | 2026-09-29 | Yes |
| S17 | Kopia docs: Architecture, Encryption, ECC (`kopia/kopia @ master : site/content/docs/Advanced/…`) | Kopia | master head | 2026-10-06 | Yes |
| S18 | Kopia `repo/hashing/sha_hashes.go`, `blake_hashes.go`, `hashing.go` (master); Kopia v0.23.1 module source (`content_manager.go`) | Kopia | master; v0.23.1 2026-06-15 | 2026-10-06; skeptics 2026-10-07 | Yes |
| S19 | Borg README, `borgbackup/borg @ master : README.rst`; `docs/internals/data-structures.rst` (scout) | BorgBackup | master head | 2026-10-07 (skeptics) | Yes |
| S20 | PyPI `borgbackup` JSON | PyPI | 1.4.5 (2026-07-18T22:38:09Z); 2.0.0b25 (2026-09-27T22:57:11Z) | 2026-10-07 (skeptics) | Yes |
| S21 | PBS `proxmox/proxmox-backup @ master : docs/technical-overview.rst`, `pbs-tools/src/crypt_config.rs`, `docs/backup-client.rst` (scout), `debian/changelog`, `debian/copyright` | Proxmox | GitHub mirror, top changelog entry 3.2.4-1 | 2026-10-07 (skeptics) | Yes (stale mirror) |
| S22 | bupstash README, `andrewchambers/bupstash @ master : README.md`; 0.12.0 crate source | bupstash | 0.12.0, 2022-11-07T02:39Z | 2026-10-07 (skeptic) | Yes |
| S23 | Kloset README, `PlakarKorp/kloset @ main : README.md`; proxy.golang.org Kloset version list | Plakar | v1.1.8; v1.2.0-alpha.1 to alpha.5 listed | 2026-09-29; list 2026-10-07 | Yes |
| S24 | Immich storage template, `immich-app/immich @ main : docs/docs/partials/_storage-template.md` | Immich | main head | 2026-09-29 | Yes |
| S25 | OpenZFS #12014, PR #17340, openzfs-docs #494 (github.com, scout) | OpenZFS community | 2021-05-08 → 2025-05-20; 2024-02-12 | 2026-09-29 | No |
| S26 | openzfsonosx/openzfs-fork #104 (search-result title only) | community | unknown | 2026-09-29 | No |
| S27 | restic #1988, #2523 (github.com, scout); forum.restic.net thread 8758 (snippet) | restic community | 2018-09-07; 2019-12-20 | 2026-09-29 | No |
| S28 | Kopia #5049, #4769, #4348, PR #4839 (github.com, scout) | Kopia community | 2025 | 2026-09-29 | No |
| S29 | Plakar releases page, https://github.com/PlakarKorp/plakar/releases (WebFetch) | Plakar (vendor) | v1.1.0 2026-06-05 … v1.1.7 2026-09-24 | 2026-10-06; skeptic 2026-10-07 | Yes (vendor's own release notes) |
| S30 | Immich #30919, #29627 (github.com, scout) | Immich community | 2026-08-22; 2026-07-06 | 2026-09-29 | No |
| S31 | restic #533 (search results only) | restic community | unknown | 2026-09-29 | No |
| S32 | Duplicati forum threads 7591 and 9291; duplicati #4923 (snippets) | community | unknown | 2026-09-29 | No |
| S33 | git-annex backends page (search snippet) | git-annex | unknown | 2026-09-29 | No |
| S34 | Rust `age` 0.12.1 and `age-core` 0.12.0 crate source (static.crates.io) | str4d / rage | age 0.12.1, 2026-07-14 | 2026-09-29; skeptic 2026-10-07 | Yes |
| S35 | A2 `a2-object-envelope.md` (C5, C6, C9, C21, C25, C29, A2-S3) and `docs/spec/object-format.md` (§5 `stored-v1`, `h0_sha256`; §6.1 hedged derivation; §9 padding); D2 `d2-key-hierarchy-custody-recovery.md` (C22, C24) | Project | 2026-10-06 | 2026-10-07 | Yes (project drafts) |
| S36 | restic issue #187 "Support asymmetric backups", https://github.com/restic/restic/issues/187 (summarising WebFetch) | restic tracker | opened 2015-05-14; open | 2026-10-06; skeptic 2026-10-07 | Partly. Corroboration of S4 only, never sole support |
| S37 | ADR-0008 `docs/adr/0008-key-hierarchy-custody-recovery.md`: Decision 1 (escrow at creation), the bundle table, Decision 6 (I_e custody and placement; h0 rule), Decision 8 | Project (D2) | Proposed, 2026-10-06 | 2026-10-07 | Yes (Proposed, not Accepted) |
| S38 | Spike READMEs and evidence: `spikes/A6-S1`, `A6-S3`, `A6-S4`, `A6-S5`, `A6-S6`, `spikes/D2-S2`, `spikes/A2-S3`; kits `docs/research/kits/A6-S1`, `A6-S2`, `A6-S3` | Project (spike runners) | 2026-10-06 / 2026-10-07 | 2026-10-07 | Yes (container measurements, synthetic data) |
| S39 | PBS `debian/copyright`; Kloset `LICENSE`; bupstash 0.12.0 `Cargo.toml` | Proxmox; Plakar; bupstash | mirror master; main; 0.12.0 | 2026-10-06 | Yes |
| S40 | Go age v1.3.2 module zip (proxy.golang.org `filippo.io/age/@v/v1.3.2.zip`): `extra/age-plugin-pq/plugin-pq.go` usage text | F. Valsorda | v1.3.2, 2026-08-29T17:40Z | 2026-10-07 (synthesizer) | Yes |
| S41 | proxy.golang.org `github.com/!plakar!korp/plakar/@v/{v1.0.1,v1.0.6,v1.1.0,v1.1.7}.info` | Go module proxy | v1.0.1 2025-05-14T22:21Z; v1.0.6 2025-11-30T09:43Z; v1.1.0 2026-06-05T13:56Z; v1.1.7 2026-09-24T13:44Z | 2026-10-07 (synthesizer) | Yes |
| S42 | PBS 4.1 and 4.2 release reports (datazone.de; storagenewsletter.com 2025-12-04; a forum.proxmox.com "Proxmox Backup Server 4.2 released" thread), seen as search results by the sources skeptic | third parties | 4.1 reported 2025-11-26 | 2026-10-07 (skeptic; **not fetched by the synthesizer**) | No |

## Claims

Verdicts follow the computed round-2 claim tally exactly. The thirteen reviewed key claims (K1–K13) map to the C-numbers below. Claims outside that set were **not skeptic-reviewed**. They are marked as such and are never the sole support of a recommendation.

| # | Claim | Sources | Key? | Skeptic 1 (sources) | Skeptic 2 (logic) | Skeptic 3 (adversary) | Verdict |
|---|---|---|---|---|---|---|---|
| C1 (K1) | Under the current ingest design (verify-before-commit decrypts the whole object), a private key able to decrypt incoming objects is online at ingest in every posture. The posture decides only what that key can decrypt and which other operations need a key. | S2 §11, S3 (SR-04, A3 F6) | Yes | Upheld; conditional on SR-04 | Upheld as a conditional; SR-04 is Proposed, not settled | Upheld | **Verified** (conditional on SR-04) |
| C2 (K2) | In age v1, every stanza wraps the same 128-bit file key. The header MAC key is HKDF(file key, "header") and the payload key is HKDF(file key, nonce, "payload"). Adding or replacing recipients is therefore a header rewrite that needs the file key, and the payload stays valid. | S11 | Yes | Upheld (lines 60, 98, 121, 153) | Upheld; notes line 62 (file-key reuse; §F3 item 9) | Upheld; same caveat | **Verified** |
| C3 (K3) | An scrypt stanza MUST be the only stanza in a header, so a passphrase recovery *stanza* cannot sit next to X. | S11 | Yes | Upheld (lines 339–343) | Upheld; a passphrase-wrapped R identity file is still possible | Upheld | **Verified** |
| C4 (K4) | restic encrypts the whole repository with one symmetric master key (AES-256-CTR + Poly1305-AES), unlocked by a password. Any writer can decrypt everything. The master key changes only by moving to a new repository (design.rst lines 825–828). | S4 | Yes | Upheld | Upheld | Upheld | **Verified.** The knockout rests on S4 alone |
| C25 (K4) | restic #187 "Support asymmetric backups" has been open since 2015-05-14. | S36 | No (corroboration) | Upheld through a summarised page read only | Not verifiable here (gh refused) | Upheld through WebFetch | **Verified as part of K4**, but used **only as corroboration** of C4 |
| C5 (K5) | restic splits files of 512 KiB and over into CDC blobs of 512 KiB–8 MiB, identified per blob, so a whole-file SHA-256 is not a native lookup key **for files of 512 KiB or more**. Smaller files are one blob whose ID is their plaintext SHA-256. Ingest is snapshot-scoped in the CLI and in rustic_core 0.13.0 (`Repository::backup`, `archive`). | S4, S6, S10 | Yes | Upheld | Upheld; small-file and `FixedSize` caveats (C36) | Upheld; small-file nuance | **Verified** (qualified for the small-file case) |
| C6 (K6) | Kopia content IDs are keyed. The SHA-family registry has only HMAC variants; BLAKE2S/2B are registered through `truncatedKeyedHashFuncFactory`; the default is `BLAKE2B-256-128`. No independent reader was found, which is absence of evidence. | S18 | Yes | Upheld; the code, not the doc, is the primary | Upheld; the K3 knockout is the stronger one | Upheld | **Verified** |
| C7 (K7) | The Borg 2 README says "DO NOT USE BORG2 FOR YOUR PRODUCTION BACKUPS!". On PyPI, 2.0.0b25 was uploaded 2026-09-27T22:57Z; the latest stable is 1.4.5, uploaded 2026-07-18T22:38Z. | S19, S20 | Yes | Upheld (2026-10-07) | Upheld; no b26 or 1.4.6 yet | Upheld; time-sensitive | **Verified.** Re-check before ADR-0012 is accepted |
| C10 (K8) | ZFS native encryption leaves dataset and snapshot names, properties, file sizes, holes and dedup tables unencrypted. Encrypted datasets can be scrubbed and resilvered without keys. `change-key` does not overwrite the old wrapped master key. The keyed "thorough" scrub exists on master (2.4.99) only and is absent from tags 2.4.0 to 2.4.4. | S12, S13 | Yes | Upheld; 2.4.5+ tags 404 | Upheld | Upheld; 2.4.0 and 2.4.4 files byte-identical | **Verified** |
| C14 (K9) | Under A and A′, a keyless SHA-256 over the stored bytes, compared with the digest recorded at ingest, is complete integrity evidence for the plaintext. | S2 §11, S11 | Yes | **Refuted** for A′ | **Refuted** for A′; not tamper evidence | **Refuted** for A′ | **Contested.** Not used as support. Restated as C14r |
| C14r | Under A, a keyless stored-bytes audit is complete integrity evidence for the plaintext, because the stored bytes are the bytes ingest decrypted (provided `stored_sha256` is computed over exactly those bytes). Under A′ and A″ it proves only that the bytes have not changed since they were written. Under neither posture is it tamper evidence. | S2, S11, S38 | Yes | (all three lenses said C14r is the right restatement) | — | — | **Not tallied** (inference, narrower than C14) |
| C30 (K10) | Prior-run A6-S5 (container, synthetic data), with native `mlkem768x25519` identities: Go age 1.3.1 decrypted 176/176; Debian age 1.1.1 and rage 0.12.1 decrypted 0/176. Go age refuses to mix PQ and X25519 recipients in one file. | S38 (A6-S5) | Yes | Upheld; **the inference "no second CLI reader" is overstated** (C33) | Upheld; the mixing refusal comes from a test read; library readers exist | Upheld; mixing is a source read, not measured | **Verified** for the measured facts. The mixing refusal is a **source read** (TestHybridMixingRestrictions), consistent with age.md's SHOULD NOT. The inference is corrected: one independent CLI implementation, plus the plugin route, plus library readers |
| C29 (K11) | (as worded for review) "The Proposed ADR-0008 escrows each **retired** ingest key sealed to {X, R} and deletes **every** online copy." | S37 | Yes | **Refuted:** escrow is at creation; a sealed copy stays online | **Refuted** on both points | **Refuted** on both points | **Contested.** Not used as support |
| C29r | (restated from ADR-0008 Decision 1 and the bundle table, checked 2026-10-07) Each I_e is sealed to {X, R} **when it is created**, into the online bundle, which is copied off-box at epoch start. Plaintext online copies, including those in snapshots and replicas, are deleted after the drain bound. The sealed bundle stays online and opens only with X or R. Plaintext I_e is online for its whole epoch (yearly by default). | S37 | Supporting | (all three lenses said this rewording is accurate) | — | — | **Not tallied.** It is a direct reading of project text, and supports only §F3 item 8 |
| C19 (K12) | A full read of 10 TB takes about 27.8 h at 100 MB/s and 9.3 h at 300 MB/s, well inside a 720 h month. This is arithmetic. | arithmetic | Yes | Upheld as arithmetic; add per-file seeks; 10 TiB ≈ 30.5 h | Upheld as arithmetic; it does not address "without starving ingest", and under A′ it times only a bit-stability check | Upheld as arithmetic; a sequential lower bound | **Secondary only.** A feasibility hint, never BUD-AUDIT evidence (DR-A6-5) |
| C9 (K13) | bupstash describes itself as beta and recommends it only for redundant backups. Its last release is 0.12.0, 2022-11-07 (MIT). | S22, S39 | Yes | Upheld | Upheld | Upheld | **Verified** |
| C17 (K13) | Plakar/Kloset 1.1.x has existed since 2026-06-05, and behaviour changed within the minor series. **Restated in round 2:** Plakar has had stable 1.0.x releases since v1.0.1 (2025-05-14) through v1.0.6 (2025-11-30). In 1.1, 1.1.5 refuses unencrypted Kloset stores unless overridden, and 1.1.6 changed Plakar's login flow, which is not a store-format change. Kloset 1.2.0-alpha.1 to alpha.5 are published (C34). | S29, S41, S23 | Yes | Upheld literally but **misleading as maturity evidence** | Upheld (not re-checked) | Upheld; the "behaviour change" detail was not re-verified | **Verified** for the facts. **Weak** as a K6 knockout: Plakar is knocked out on K2 and K3 |
| C8 (K13) | PBS: the server checks only CRC-32 for encrypted chunks. PBS is AGPL-3.0-or-later. | S21, S39 | Yes | Upheld; the mirror is stale (3.2.4) | Upheld for 3.2.4 | Upheld; 4.x unverified | **Verified** for the mirror's version. 4.x: C35 |
| C11 | ZFS `keylocation` can be `prompt`, `file://`, `https://` or `http://`. `zfs send -w` sends encrypted datasets without loaded keys. | S12 | No (posture B only) | — | — | — | Not reviewed |
| C12 | Native encryption plus send/recv has a bug history (#12014, PR #17340). A macOS-port title reports raw-send corruption on 2.4.x. | S25, S26 | No | — | — | — | Secondary only |
| C13 | OCFL 1.1: sha512 or sha256 addressing; no links; immutable versions; a one-version object is 6 files in 3 directories; extension 0004 maps IDs to hashed paths. The a6cas prototype and the A6-S2 kit use extension 0003 instead. | S14, S15, S38 | No (bake-off variant) | — | — | — | Not reviewed |
| C15 | restic keeps its index in RAM; #1988 reports OOM at about 2M files on 1 GB. | S27 | No | — | — | — | Secondary only |
| C16 | The rustic_core 0.13.0 API is "in an early development stage" and opens only with a password or master key. | S10 | No | — | — | — | Not reviewed |
| C18 | Kopia restore regression (#5049) and an open maintenance report (#4769). | S28 | No | — | — | — | Secondary only |
| C20 | A Rust header rewrap can use public `age` 0.12.1 APIs (`unwrap_stanza`, `wrap_file_key`, `FileKey: ExposeSecret`) plus about one screen of Reliquary header code. The parser and MAC are private. | S34 | No (build feasibility) | — | — | — | Not reviewed. The Go equivalent is measured (A6-S6) |
| C21 | Under A′ with PQ, the stored {X, R} header is 3,184 B. Sealing h0 adds an age file around h0, so the stored overhead is several KB per object. | S35, S38 | No (cost) | — | — | — | Not reviewed. The sealed-h0 size is not measured |
| C22 | A restore done as a header rewrap leaves the R2-staged payload byte-identical to the original upload, so the cloud could link the two. Fresh re-encryption avoids this. | S11, S35 | No (A8 input) | — | — | — | Not reviewed |
| C23 | rest-server has `--append-only` and `--private-repos`; the layout is the same locally and remotely. | S7 | No | — | — | — | Not reviewed |
| C24 | PBS encrypted-chunk digest = SHA-256(data ‖ id_key), with id_key from PBKDF2. | S21 | No | — | — | — | Not reviewed |
| C26 | Licences: restic BSD-2; Kopia Apache-2.0 (scout); Borg BSD-3 (scout); rustic_core Apache-2.0 OR MIT; Kloset ISC-style; bupstash MIT; PBS AGPL (C8). | S39, S4, S10, S17, S19 | Yes (K4) | (PBS and bupstash parts reviewed via K13) | — | — | Partly verified (PBS, bupstash); the rest not reviewed |
| C27 | Kopia's ECC is "currently experimental". | S17 | No | — | — | — | Not reviewed |
| C31 | (spike, measured) Under A and A′, someone holding the disks derives the exact plaintext size of 535/535 objects and confirms the presence of 50/50 known files from plain-SHA-256 names. | S38 (A6-S1 Probe 4) | No (DR-A6-3) | — | — | — | Measured (container, synthetic); not reviewed |
| C32 | (spike, measured) With h0 kept in the clear, h0 + stored payload + I_e decrypts every current-epoch object (176/176). With only the stored file, I_e decrypts 0/535. | S38 (A6-S6 row 6; A6-S1 Probe 2) | Yes (A′ property) | — | — | — | Measured; not tallied. It drives amendment 1 |
| C33 | (new, round 2) Go age v1.3.2 ships `extra/age-plugin-pq`. Its usage text says it can "add support to any version and implementation of age that supports plugins", and that identities must first be converted with `-identity`. D2 measured Debian age 1.1.1 plus the plugin decrypting a two-PQ object. | S40, S35 (D2 C22) | Supporting (heir path) | Raised it | — | — | **Not tallied.** Primary re-read by the synthesizer on 2026-10-07 |
| C34 | (new, round 2) Plakar: v1.0.1 2025-05-14; v1.0.6 2025-11-30; v1.1.0 2026-06-05; v1.1.7 2026-09-24. Kloset: v1.1.8 latest stable, plus v1.2.0-alpha.1 to alpha.5. | S41, S23 | Supporting (C17) | Raised it | — | — | **Not tallied.** Primary (Go module proxy), checked 2026-10-07 |
| C35 | (new, round 2) PBS 4.1 (reported 2025-11-26, with S3 datastores and multithreaded verify) and 4.2 exist. The CRC-only verify of encrypted chunks is reported unchanged. | S42 | No | Raised it from search results | — | — | **Secondary only.** Not load-bearing |
| C36 | (new, round 2) rustic_core 0.13.0 has a `Chunker::FixedSize` option (configfile.rs about line 290). With a chunk size above the file size, the blob ID is the whole-file SHA-256. Chunks are read into RAM and pack sizes are u32, so large videos still split, and restic CLI writers would not use it. | S10 | No | — | Raised it | — | **Not tallied.** Read by the logic skeptic, not re-read by the synthesizer. It does not change K3 for a photo-and-video corpus |

## Findings

### F1. What the posture decides (corrected in both review rounds)

**Premise (C1, verified, conditional on SR-04).** The homelab decrypts every object, recomputes SHA-256 and HMAC, commits only on a match, and signs a receipt. So a key that opens incoming objects is online whenever ingest runs. Two designs avoid this premise:

- **Attended batch verification:** devices encrypt directly to X, and the homelab verifies and issues receipts only when the owner brings X online. **Rejected:** "stored at home" would wait for the owner, which breaks BUD-TTS (24 h) and the A3 receipt contract, and unverified ciphertext would sit in the keep-forever store.
- **Isolated verifier:** I_e is held only by a minimal, network-isolated verifier VM, or in a non-exportable TPM or HSM. The verifier decrypts, verifies and (round 2) also **performs the rewrap and the h0 sealing**, then hands only ciphertext to a separate storage writer that never holds I_e or a file key. **Recommended as the hardening direction** (ADR-0012 Decision 5). D1 and D4 decide it in Wave 2, and D2 owns the TPM/HSM option.

**Matrix.** "A′" means A′ with the amendments (h0 sealed to {X, R}, write-time self-check, attended X audit, X used only in a separate environment; §F3). A″ (fresh file key at ingest) has the same cells unless §F1b says otherwise.

| Consequence | A: keep received ciphertext (one homelab key) | **A′: rewrap header to offline X (+R); I_e rotates; h0 sealed** | B: plaintext CAS on ZFS native encryption | C: re-encrypt into restic/Kopia/PBS |
|---|---|---|---|---|
| Key online for ingest | Homelab identity, which opens **everything ever stored** | I_e of open epochs. It opens objects encrypted to those epochs **while they are in staging or on USB**, not stored objects | Homelab age identity (everything) **and** the ZFS key | Homelab age identity **and** the repository password (everything) |
| ZFS scrub | No key | No key | No key (C10) | No key |
| Bit-rot audit of stored bytes | No key (C14r) | No key (C14r) | Dataset key loaded | restic: **no key** at file level (A6-S1 Probe 3); Kopia: password or an external hash list |
| Proof that the stored object opens | Ingest proved it for these exact bytes | **Needs X:** write-time self-check without X, plus attended sampled X unwrap (§F3) | Dataset key | Password (`check --read-data`) |
| Stolen powered-off box, **unlock a thief can trigger** (key file on the box, or Tang or a key server in the same house): stored content | Everything | **Nothing** (C32 with h0 sealed; the **sealed form is not measured yet**, A6-S7) | Everything | Everything |
| Stolen powered-off box, **theft-resistant unlock** (off-premises key server, or attended): stored content | Nothing | Nothing | Nothing (names and sizes stay visible, C10) | Nothing |
| Stolen box: in-transit objects | As the stored-content row | Open-epoch objects in staging or on USB, if the thief can unlock I_e | As the stored-content row | As the stored-content row |
| Stolen box: metadata | Catalog, unless its dataset unlock is theft-resistant | **Same as A**, plus sizes and file presence from names (C31) | Sizes, dataset and snapshot names (C10); catalog as A | Catalog as A |
| Stolen box: derivatives | Same as the catalog | **Same as the catalog**, unless encrypted to {X, R} | Readable with the dataset key | Inside the engine |
| Compromised ingest VM: new uploads | Everything, until cleaned up | Everything, until cleaned up (it holds I_e and sees plaintext) | Same | Same |
| Compromised ingest VM: stored content | Everything | **Nothing of retired or current stored objects**, if h0 is sealed and the VM cannot read the R2 copies. Open-epoch cloud-retained ciphertext is readable. **Holds only while X never touches a host the attacker controls** (§F3 item 6) | Everything it can read | Everything (C4) |
| Compromised ingest or catalog VM: metadata | Everything | **Everything.** The catalog is online plaintext; A′ does not protect metadata | Everything | Everything |
| Compromised ingest VM: integrity of **new** commits (round 2) | It can store garbage or sign false receipts. A separate receipt signer that re-verifies from the append-only store **can detect this** (AR-08 candidate) | It can write an unopenable h1 and a bad sealed h0 and still sign "protected". **A re-verifying signer cannot check h1 without X** unless h1 is deterministic (§F3 item 5). The X audit catches it only by sampling | Re-verifiable with the dataset key | Re-verifiable with the password |
| Compromised ingest VM: integrity of the stored archive | It can rewrite or delete unless the store is write-once (§F8) | Same | Same | Same |
| Adding a recovery recipient later | Rewrap of every object; the whole store is rewritten (A6-S1 Probe 1) | Added at ingest from day one. Changing it later costs the same as under A | `change-key` (kit A6-S1-B P5); old wrapped keys stay on disk (C10) | `restic key add`: 2.98 s, one key file (Probe 3), but it adds another read-everything secret |
| **Rotating or replacing X** (round 2) | n/a (one key) | Rewrap of every object; the whole store is rewritten. A header-sidecar layout would cut this to KB per object (§F8) | `change-key` | New repository (C4) |
| Derivatives | Need the key | At ingest (see the derivative rows) or with X | Any time | Through the engine |
| Read-only Immich/PhotoPrism view | Decrypted mirror (online key) | Decrypted mirror, which gives up A′'s benefit | Generated tree | `restic mount` with the password |
| Heir access | `age` + identity + catalog export | `age` + X or R + catalog export (PQ: Go age, or older age with `age-plugin-pq`, or a library reader; C30, C33) | OpenZFS-capable Linux + passphrase | restic/rustic + password |
| Off-site copy later | Copy the files | Copy the files | `zfs send -w` (C11, C12) or rclone crypt | `restic copy` |
| Restore drills on real objects | Unattended possible | **Attended** (needs X). Unattended drills can use only canary objects with a drill stanza (§F3) | Unattended possible | Unattended with the password |
| Device-signed provenance kept | Byte-identical to the upload | Payload identical. Sealed h0 lets the owner rebuild the exact upload with X (A6-S6). Under A″: content provenance only (§F1b) | Record only | Record only |

**Finding (Medium; restated in round 2).** Compared with A **on the same unlock mechanism**, the offline-archive-key posture changes what the always-loaded key and a compromised ingest VM can read. Under A they read everything stored; under A′/A″, objects in transit only. That is its reason to exist.

Against theft of a powered-off box, it is better only than an A, B or C whose key a thief can also unlock. A theft-resistant unlock (an off-premises key server, or attended) protects stored content in every posture, and the catalog needs that same unlock in every posture.

The keyless properties (scrub, bit-rot audit, off-site copy) are shared with A, and partly with restic, so they do not argue for A′.

Its costs:

- the owner brings X online, in a separate environment, for restores, catalog rebuilds, real-object drills and X audits;
- I_e rotates (ADR-0008: yearly by default);
- the unattended audit is bit-stability only, so BUD-AUDIT needs a definition (DR-A6-5);
- a compromised ingest VM can silently miswrap new commits until the deterministic-h1 check exists;
- a plaintext gallery becomes a deliberate exception (OD-13);
- metadata and derivatives need their own encrypted dataset;
- integrity against a writer needs §F8.

Prior art for the shape: bupstash put-only keys and the PBS offline RSA `master-pubkey` (S21, S22). Both keep the reading key off the always-on machine.

### F1b. A′ vs A″, compared directly (new in round 2)

Both write a standard age v1 file whose header is exactly {X, R} (`stored-v1`). They differ in whether the stored payload is the device's ciphertext or a fresh encryption.

| Aspect | A′: rewrap header, keep payload | A″: fresh file key at ingest |
|---|---|---|
| File key shared with the upload | Yes, so h0 must be sealed (C32) | No. h0 need not be kept, or can be kept sealed for audit only |
| age rule "file key MUST NOT be reused across multiple files" (age.md line 62) | Letter broken; intent kept. This is an unreviewed inference (§F3 item 9) | Honoured literally |
| Stored payload linkable to R2-retained ciphertext | Yes, until R2 copies expire | No |
| Rebuild the exact device upload and re-check device bytes | Yes, with X (A6-S6) | No. Content provenance is still provable: decrypting with X gives plaintext whose SHA-256 and HMAC match the device-signed record |
| Second, independent path to the file key if h1 is bad | Yes: sealed h0 + escrowed I_e. It uses stock age, not the rewrap code | **None in the store.** Recovery from a miswrap depends on the device or the R2 copy still existing |
| Self-check at write without X | MAC under the file key; stanza recompute (§F3 item 5) | The same, plus a full decrypt of the stored payload with the in-memory fresh key (the payload is new bytes, so this matters) |
| Compromised ingest VM writes a bad h1 | Same exposure | Same exposure |
| Cost | A6-S1 Probe 1 (tmpfs, single process, 229.56 MB, wall): rewrap 1.68–1.75 s | Re-encryption 2.51–2.58 s, about 1.4–1.5× the wall time of a rewrap |
| Parts not built | Sealed h0; self-check; Rust rewrap | Self-check; Rust re-encryption path (stock `age` APIs) |
| Stored-file format | Standard age v1 to {X, R} | Standard age v1 to {X, R} |

**Finding (Medium).** A″ is simpler and has fewer unreviewed inferences. A′ is cheaper and keeps an independent path to the file key, which serves "data integrity over everything". Because both produce the same kind of stored file, the choice is reversible for new objects. **A6 leans A′, and switches to A″ if A6-S7 shows that the sealed h0 or the self-check cannot be built simply, or if the A2/D2 crypto review rejects the file-key-reuse argument.** The owner is asked only whether byte-exact upload provenance and the second recovery path matter (OD-07 sub-option).

### F2. Fixity under each posture (C14 contested; restated as C14r)

- At ingest, record `stored_sha256 = SHA-256(stored bytes)` in the catalog and in the append-only manifest inside the store, so the store can be audited without the catalog.
- **Under A,** a keyless audit is complete integrity evidence. The stored bytes are exactly the bytes ingest decrypted and verified.
- **Under A′ and A″,** the stored header h1 is written after verification, and nothing online can open it. A keyless audit therefore proves only that **the bytes have not changed since they were written**. Any of these would be recorded in `stored_sha256` and pass every later audit:
  - a rewrap bug;
  - a wrong or substituted X public key;
  - a mixed-profile header;
  - a RAM bit flip between verification and write;
  - a compromised ingest VM.

  Recoverability needs §F3 items 5–6.
- **Under no posture** is `stored_sha256` tamper evidence. The digest sits on the same box as the objects, so someone who can write the store can rewrite both. That is §F8.
- **Detection is not repair (round 2).** Keyless audits and scrubs detect corruption, but repair needs a second copy: ZFS redundancy (mirror or raidz), `copies=2` on the store dataset, or per-object forward error correction such as par2. The off-site copy is out of scope. age authenticates the payload per 64 KiB chunk (age.md), so one damaged chunk means the file cannot be restored byte-exact without a second copy. Requirement for ADR-0012 and C5: the store dataset must have redundancy, or par2 must be added. Intake C5 must ask about pool redundancy.
- **BUD-AUDIT under A′/A″ (round 2).** "Full app-level audit of 10 TB monthly" can mean:
  - a full keyless bit-stability audit plus X-sampled decryption at each attended session, which fits A′; or
  - a full decryption audit, which would keep X online for at least 28 h a month (C19 arithmetic) and so means posture A in effect.

  H1 owns the budget and A7 the fixity policy, so this is DR-A6-5. **C19 is not BUD-AUDIT evidence for A′ until that is settled.**
- Audit duration (C19, secondary only, arithmetic): at least 27.8 h for 10 TB at 100 MB/s. Seeks for 3–5M files add roughly 8–14 h at an assumed 10 ms each, and the ZFS scrub reads the same disks. A6-S2 and A7-S2 measure MB/s, files/s and the effect on ingest.

### F3. A′ mechanics (proposal for ADR-0012; A2 and D2 must agree)

1. The device encrypts to the ingest recipient of epoch e, I_e, which is published in the signed trust bundle (ADR-0008 Decision 4). The header shape is checked before any unwrap (ADR-0008 Decision 6; `object-format.md` §5).
2. The homelab verifies as in CE §11 and `object-format.md` (including `h0_sha256`), by streaming, with no plaintext temp file.
3. The homelab writes the stored object:
   - a `stored-v1` header with exactly {X, R} in a uniform profile (both PQ or both X25519);
   - the MAC recomputed from the file key;
   - then the payload bytes, unchanged.

   The result is a standard age v1 file (C2; A6-S6: 176/176 open with X and with R, 0/176 with I_e).
4. **h0 is sealed, never kept in the clear (amendment 1).** The device header h0 is age-encrypted to {X, R} as its own small sealed blob, referenced from the manifest line. `h0_sha256` stays in the clear for keyless cross-checks. Reasons:
   - with h0 in the clear, h0 + stored payload + I_e opens every object of an open epoch (C32);
   - ADR-0008 Decision 6 requires it;
   - with X, the owner can rebuild the exact upload;
   - it gives a second, independent path to the file key: sealed h0 plus the escrowed I_e.

   Metadata records get the same treatment. The sealed form's exposure is not yet measured (A6-S7).
5. **Write-time self-check (amendment 2), and its limit.** Before the ACK, the homelab checks:
   - that the file re-read from disk parses as exactly `stored-v1`;
   - that its MAC verifies under the in-memory file key;
   - that the payload read back hashes to the expected value;
   - that X and R match the fingerprints pinned at the offline ceremony (in the A-signed bundle);
   - that each stanza matches when recomputed by an independent encoder from the same encapsulation randomness.

   The state is then `rewrap_selfchecked`. Not built; G2 owns the test.

   **Limit (round 2, adversary lens):** all of this runs on the VM that holds I_e and the file key, so it gives **no assurance against a compromised ingest VM**. Such a VM can write a bad h1 and a bad sealed h0 and still sign "protected". Under A, D1's AR-08 candidate (a separate receipt signer that re-verifies from the append-only store) would catch this; under A′ it cannot, because checking h1 needs X.

   **Proposed fix, not reviewed:** make h1 **deterministic** by deriving the stanza encapsulation randomness from the file key with its own HKDF label. This follows `object-format.md` §6.1, which already derives per-stanza randomness and forbids combining randomness with a *different* file key; here it is tied to the same file key. A separate verifier holding I_e and a transient copy of h0 can then recompute h1 byte for byte and compare it with the bytes on disk before the receipt is signed. Anyone who can recompute a stanza already holds the file key, so this leaks nothing new (inference; A2/D2 review). The alternative is that the isolated verifier performs the rewrap itself (§F1). Both go into A6-S7 and D4-S4 as the fault case "targeted miswrap by a compromised VM".
6. **Attended X audit, and where X may run (amendment 2, extended in round 2).**
   - Each time the owner brings X online, an X-unwrap pass runs over a random sample of objects committed since the last pass, plus every object not yet sampled once it is old enough. Passing objects become `x_verified`. A failure stops ingest and alerts.
   - Until an epoch is covered, its sealed h0 entries and its I_e escrow are kept as the fallback.
   - Sample size and cadence go to A7 (ADR-0029) and D2 (ADR-0008 Decision 8). DR-A6-4 asks D2 to replace "verify X decryption of every rewrapped header", which nothing can do online under A′.
   - **New requirement (amendment 4):** X-requiring work (restores, rebuilds, X audits, rotations) runs **in a separate, freshly booted environment with read-only access to the store**, such as a VM or live system booted from a read-only image, or on the air-gapped ceremony machine with exported objects. **Never on the ingest VM.** Otherwise an attacker who persists on the ingest VM captures X at the first attended session, and A′ collapses to A.
   - A VM on the same Proxmox host protects against compromise of the ingest VM but not of the host. The strongest form is the air-gapped machine.
   - The owner-time cost against BUD-RESTORE (< 30 min per single-file request) and BUD-SUPPORT (≤ 2 h per month) is **not measured** (A8, C8).
   - D1 adds the attack-tree case "persistent ingest compromise, then attended restore".
7. **Rotate I_e.** D2 sets the interval; ADR-0008 says yearly. With sealed h0, the interval no longer bounds stored-archive exposure. It still bounds how long a captured I_e opens cloud-retained ciphertext and future uploads (D2 hand-off).
8. **Escrow (C29r; C29 as first worded is contested).** Each I_e is sealed to {X, R} **at creation** into the online bundle, which is copied off-box at epoch start. Plaintext online copies are deleted after the drain bound. The sealed bundle stays online and opens only with X or R. AR-07 (objects staged before the bundle copy leaves the box) remains ADR-0008's residual gap.
9. **The age rule "file key MUST NOT be reused across multiple files"** (age.md line 62).
   - After the rewrap, the stored file and the device upload share a file key and payload nonce. A rewrap restore would make a third file (C22).
   - No new plaintext is ever encrypted under that key and nonce, because the payload is byte-identical. So the rule's intent is respected, and the stanza-level rule in `object-format.md` §6.1 is untouched.
   - This is an inference and has not been reviewed. A2/D2 must sign it off explicitly, or A″ is chosen (§F1b). Restores should use fresh re-encryption (A8).
10. **Derivatives:** never stored in the clear outside the catalog's encrypted dataset. Either encrypt them to {X, R}, or keep them on that dataset and list them as exposed under its unlock.
11. **Throughput.** The container ran single-threaded ingest below 100 MB/s (A6-S2 smoke: 76.6 MB/s on tmpfs, not budget evidence). D2-S2 is a CPU-bound proxy for the PQ header work: 1M rewraps in 186.0 s of wall time with 4 workers. BUD-INGEST will probably need parallel verify and rewrap. This is a design requirement for A3 and a watch item for A6-S2.
12. **Placement constraints (round 2).**
    - **I_e:** tmpfs only. Never on the store dataset, on any dataset under the §F8 held-snapshot policy, or on replicated or vzdump-covered storage (ADR-0008 Decision 6).
    - **Sealed h0 and the online bundle:** may sit on the store dataset, because they are sealed to {X, R}.
    - **Catalog and derivatives:** on an encrypted dataset whose unlock C5/D2 choose.

    These go to the C5/C6 dataset hand-off.

### F4. Knockout screen (re-scoped in both rounds)

**Criteria:**

- **K1:** library-driven per-file ingest keyed by our ID.
- **K2:** specified format with an independent reader.
- **K3 (made uniform in round 2):** single-file restore by plain SHA-256 using only the store itself (its paths or an in-store, self-describing manifest), with no external map.
- **K4:** licence (G3). AGPL is flagged, not failed.
- **K5:** fit with **any** posture A, A′/A″, B or C.
- **K6:** maturity ("proven").

For build-our-own candidates K1 and K6 are **n/a**. The substitute evidence is:

- the one-page spec;
- A6-S3: 0 violations over 400 kills, 130 emulated power cuts and 100 disk-full trials;
- A6-S4: byte-identical catalog rebuilds;
- the Wave 2 OL kits.

| Candidate | K1 | K2 | K3 | K4 | K5 | K6 | Result |
|---|---|---|---|---|---|---|---|
| **Plain CAS of age v1 objects on ZFS** (our layout, plain-SHA-256 names) | n/a (we write it) | **Objects pass:** age v1 is a C2SP spec with independent readers (A6-S5: age 1.1.1, age 1.3.1 and rage 0.12.1 read X25519 objects 176/176). **PQ caveat:** one independent CLI implementation (Go age ≥ 1.3), usable from other CLIs through `age-plugin-pq`, plus library readers typage and kage (C30, C33). Layout: a one-page spec | **Pass natively:** the path is the hash (A6-S2 smoke: max 0.012 s) | Pass | A, A′/A″, B | n/a; substitute evidence A6-S3/S4 | **Survives** |
| **OCFL 1.1 storage root** (counted as a CAS variant) | n/a | Spec, plus ocfl-py (2026) and rocfl (stale) (C13) | Pass (object ID = SHA-256) | Pass | A, A′/A″, B | Spec stable; Rust tooling stale | **Survives** (variant) |
| **restic format, plaintext in (posture C)** | Partial: snapshot-scoped (C5) | Pass: design.rst; two implementations; A6-S5 cross-read 176/176 | **Fail** for files ≥ 512 KiB (C5). `FixedSize` chunking (C36) would not fix large videos | Pass | C only (C4) | restic mature; rustic 0.x | **Out-of-screen comparator** (DR-A6-1) |
| **restic as a container for A′ ciphertext** | Partial: snapshot-scoped | Pass | **Fail:** the repository has no hash → snapshot/path map; ours would sit outside it | Pass | A′ passes: restic's key then protects only ciphertext | Mature | **Knocked out on K3.** Adds a second password to the heir path. Add it to A6-S2 as a mode so the cost is measured, not assumed |
| Kopia | Partial: Go library | Fail: no independent reader found (C6) | Fail: keyed, per-block IDs (C6) | Pass | C; container mode also fails K3 | 0.23.1 | Knocked out |
| Borg 2 | Fail: CLI | No independent reader seen | Fail: keyed chunk IDs | Pass | C | **Fail** (C7) | Knocked out |
| Borg 1.4 | Fail | As above | Fail | Pass | C | Stable | Knocked out on K1 and K3 |
| Proxmox Backup Server | Fail: pxar streams | Fail: one implementation | Fail natively | AGPL (C8) | Weak: CRC-only verify of encrypted chunks (C8; 4.x reported unchanged, C35 secondary) | Stable; 4.1/4.2 exist (C35, secondary); mirror stale | Knocked out as the engine. **Keep it for VM-level backups of the catalog and service VMs** |
| Plakar / Kloset | Partial: Go library | **Fail:** no format spec found | **Fail:** MAC-addressed | Pass | C | **Weak:** stable 1.0.x since 2025-05; 1.1 changed defaults; 1.2 alphas in progress (C17, C34) | Knocked out on **K2 and K3**. Re-screen in 2027 |
| bupstash | Partial | Fail: one implementation | Fail: keyed chunks | Pass (MIT) | Nearest to A′ | **Fail:** beta; last release 2022-11 (C9) | Knocked out; borrow the key model |
| git-annex | Fail: Haskell CLI | Documented (secondary) | Pass (secondary) | AGPL/GPL (secondary) | Plaintext only | Mature | Knocked out on K1 |
| Perkeep, Duplicacy, duplicity, rdedup, Bareos/Bacula, Tahoe-LAFS | — | — | — | — (Duplicacy's licence would need G3) | — | — | **Not screened: no result.** Wave 2 adds one-line rows from primary sources |
| Self-hosted S3 stores (Garage, MinIO, SeaweedFS) with object lock, as the **substrate** for the age CAS | — | — | — | — | — | — | **Not screened.** This is a substrate question that belongs with §F8, not an engine. Wave 2 |

**Finding (High on the facts; Medium on the reading of "proven").** None of the **screened** engines passes K1–K6. The CLAUDE.md preference for "an existing, proven format over inventing one" is met at the object level by age v1, and optionally at the layout level by OCFL 1.1, not by a backup engine. The owner confirms this reading (DR-A6-2). The screen is incomplete for the candidates marked not screened. None of them is known to pass, but that is absence of evidence. **Naming stays plain SHA-256** (DR-A6-3 default), so the CAS passes K3 by path alone. If ciphertext-hash naming is ever adopted, the CAS's K3 rests on the in-store manifest, and the restic-container mode must be re-scored under the same rule.

### F5. Scale (Low: no homelab measurements)

- **Index RAM:** a plain CAS and OCFL need no engine index. restic loads its index into RAM (C15, secondary). The A6-S2 smoke run showed 20.6 MB peak RSS for the CAS and 162 MB for restic on 229 MB of synthetic data. Not budget evidence.
- **Snapshots:** per-file ingest into restic means batching files into each snapshot, and every restore by hash then needs our map (C5).
- **Verify cost:** disk-bound in every design, and seek-bound for millions of small objects on HDDs (C19, secondary only; §F2). Sampled audits: restic `--read-data-subset`; Borg 2 least-recently-checked. For a CAS, audit in `stored_sha256` order, one n-th per run.
- **Ingest rate:** §F3 item 11.

### F6. Readability, browsable views and the catalog's exposure

- A browsable tree can be generated from the catalog without moving originals (for example `Person/Year/Year-Month-Day/<name>`).
- Immich must never own or move originals (#30919, secondary). Any Immich view is an external library over a generated read-only tree. That mode is **unverified** and goes to C8 for OD-13.
- **The catalog is plaintext** (ADR-0001 §2): names, paths, dates and perhaps GPS. Under A′ it is the main thing a thief or a compromised online VM can read. It lives, with its WAL and backups, on an encrypted dataset. That dataset protects against theft only if its unlock is theft-resistant: an off-premises key server or attended unlock, **not Tang in the same house**. The mechanism goes to C5/D2.

### F7. Catalog (ADR-0013, Wave 2): requirements fixed by this note

The catalog must:

- store the plain SHA-256 of every item, plus `stored_sha256`, the epoch, the recipient set and the rewrap state (`rewrap_selfchecked`, `x_verified`);
- keep sightings per (person, device, source locator), so that pruning refcounts are derived (SR-20);
- store ingest events, receipts, restore jobs and audit results;
- be rebuildable from the archived records plus the manifest. A6-S4 showed byte-identical rebuilds. A files-only rebuild loses epoch, `committed_at` and `meta_sha256`, so the manifest is archival data;
- check disk headroom before ingest starts (A6-S3 disk-full lesson).

ADR-0013 screens Postgres, SQLite and an event log with projections, from its own sources.

### F8. Store integrity against a compromised writer

CLAUDE.md's "devices can only append" is enforced in the cloud. ADR-0012 needs the same at home, because SR-20 and AR-08 are still open. Proposals, all to be confirmed in Wave 2 with D4-S4:

- **Write-once objects:** after commit, files are read-only to the ingest credentials. Only a separately credentialed prune step can remove them (SR-20).
- **Frequent ZFS snapshots with `zfs hold`,** released only with a separate admin credential. **I_e must never sit on a held or snapshotted dataset** (§F3 item 12; ADR-0008 Decision 6).
- **A read-only audit VM,** separate from the writer.
- **An off-box anchor for the manifest:** a hash-chained manifest whose signed head is published off the box. Candidates are the Worker and the receipts devices already hold. Not designed.
- **Redundancy for repair:** mirror or raidz, `copies=2`, or par2 (§F2).
- **Header-sidecar layout (round 2, Wave 2 option):** store each object's header and payload as separate files. `cat hdr payload | age -d` keeps the heir path stock. Rotating or adding recipients then rewrites kilobytes per object instead of about 10 TB. It costs twice the inodes and a slightly longer heir procedure. A speculative variant (fixed-length padded headers plus OpenZFS block cloning) has a corruption bug history to check first.
- **Fault cases for Wave 2:**
  - "attacker rewrites an object and its manifest line" (A6-S3 or A7-S1);
  - "targeted miswrap by a compromised VM" (A6-S7, D4-S4).

### History of passes (condensed)

- **Second pass (A2/D2 reconciliation):**
  - stored headers are always homelab-written {X, R};
  - device recipient placement (P1 vs P2) changes only when I_e may be retired;
  - a Rust rewrap is feasible with public `age` APIs (C20);
  - restore-by-rewrap linkability goes to A8 (C22).
- **Third pass (scout conflicts):** seven conflicts were resolved against primary text. None changed a knockout.
- **Review round 1 (2026-10-06):**
  - h0 sealed;
  - write-time self-check plus X audit;
  - C14 restated;
  - metadata and derivative rows added;
  - restic container mode screened;
  - §F8 added.
- **Review round 2 (2026-10-07):** see [Review response](#review-response).

### Alternatives compared

| Option | Fit with settled requirements | Pros | Cons | Evidence |
|---|---|---|---|---|
| **Offline-archive-key posture (A′, or A″) + plain CAS of age objects on ZFS** (recommended) | Fits, if the settled-text readings are confirmed (Conflicts) | A compromised running host and the always-on key cannot read stored content; same for a thief when the unlock is triggerable on the box; heir needs only age; keyless scrubs, bit-rot audits and copies; no engine index | New layout code; key rotation; attended restores, drills and X audits in a separate environment; rewrap verification is design only (§F3); silent miswrap by a compromised VM until deterministic h1 exists; metadata not protected; names leak presence | C1, C2, C3, C10, C32; A6-S1, S3, S4, S5, S6 |
| A + plain CAS | Fits | Simplest; stored bytes identical to the upload; complete keyless fixity; a re-verifying receipt signer works | The always-on key reads everything; adding a recovery recipient later rewrites the whole store | C1, C2, A6-S1 Probe 2 |
| B: plaintext CAS on ZFS native encryption | Fits | Simplest restores, derivatives and views | Unattended unlock = read-everything; send/recv bug history; heir needs OpenZFS; dataset names and sizes exposed | C10–C12; kit A6-S1-B |
| C: restic via rustic_core or the CLI | Fits the letter of "proven format" | Proven engine; independent reader; keyless bit-rot check | Symmetric key reads everything; restore by hash needs a map; index RAM; loses device ciphertext | C4, C5, C15, C16; A6-S1 Probe 3 |
| OCFL 1.1 layout over age objects | Fits | Self-describing root; standard inventories | About 9 inodes per item vs 1; stale Rust library | C13 |
| Kopia, Borg 2, PBS, Plakar, bupstash, git-annex | See §F4 | — | Knocked out | C6–C9, C17 |

### Similar work and lessons

| Project | What they do | Borrow or avoid | Source |
|---|---|---|---|
| restic / rest-server | Files named by the SHA-256 of their stored bytes; write-once; append-only server | **Borrow:** write-once, `--read-data-subset` rotation, the append-only server role (C23). **Avoid:** a symmetric key on the ingest host (C4) | S4, S7, A6-S1 |
| rustic | Independent reimplementation | Borrow the second-implementation test (A6-S5 cross-read 176/176) | S9, A6-S5 |
| bupstash | Put-only keys; decryption keys offline | Borrow the key model | S22 |
| PBS | `.chunks/<4 hex>/<digest>`; keyed digests; offline RSA master key; verify jobs | Borrow the fan-out, verify cadence and offline recovery key. Avoid CRC-only verification of ciphertext | S21 |
| OCFL / Fedora | Plain-file longevity; inventories | Borrow the self-describing root and manifest | S14, S15 |
| Kopia | Keyed IDs; packs; experimental ECC | Avoid packs for keepsakes; SHA-256-verify every restore (C18) | S17, S28 |
| Immich storage template | `Year/Year-Month-Day/Filename` | Borrow for a generated view; never let an app move originals | S24, S30 |
| Duplicati 2 | Local DB rebuilt from remote takes days | Avoid: the store must be auditable without the catalog, and the catalog rebuildable (A6-S4) | S32 |

### Tools and libraries

| Name | Purpose | Licence | Maturity | Source |
|---|---|---|---|---|
| age (Go), `age-plugin-pq`, `age` crate (Rust), typage, kage | Object format; readers | BSD-3 / MIT-Apache; typage and kage per A2 | Go age v1.3.2 (2026-08-29); rage 0.12.1; typage 0.3.1; kage 0.8.0 | S11, S34, S35, S40 |
| OpenZFS | Filesystem, scrubs, snapshots, holds, optional encryption | CDDL | 2.4.4 newest tag; master 2.4.99 | S12, S13 |
| rustic_core | restic-format library for the comparator | Apache-2.0 OR MIT | 0.13.0, "early development" | S10 |
| restic + rest-server | Comparator; append-only reference | BSD-2 | v0.19.1 | S4, S7, S8 |
| ocfl-py, rocfl | OCFL validation | Not checked | 2.1.0 (2026-06-26); 1.7.0 (2022-10-08) | S16 |
| LazyFS | Crash-consistency fault injection | Not checked | Used in A6-S3 | S38 |
| par2cmdline-turbo | Optional per-object repair data (§F2) | Not checked | Not evaluated (A7) | PLAN A7 |

## Spikes

The spike runner owns the results. Container figures are on synthetic data, usually on tmpfs, and are **not homelab or budget evidence**.

| Spike | Hypothesis | Pass → / fail → (decision) | Exec tag | Budget IDs | Data class | Status | Result |
|---|---|---|---|---|---|---|---|
| A6-S1 Posture probes | Container probes turn matrix cells for A, A′ and C from reasoned into observed | n/a: the owner decides OD-07 | CT → owner | — (relates to BUD-TTS, BUD-RESTORE, BUD-RECOVERY) | SYN → results | **Ran** | **Probe 1** (tmpfs, wall time): adding a recipient later left the payload byte-identical in 535/535 objects and rewrote all 229.56 MB. Rewrap took 1.68–1.75 s, re-encryption 2.51–2.58 s. Each X25519 stanza adds 98 B.<br>**Probe 2:** the ingest key opens 535/535 stored files under A and 0/535 under A′. The probe covered blob files only; A6-S6 shows the clear-h0 exposure (C32).<br>**Probe 3:** restic files are named by the SHA-256 of their bytes (19/19), so a keyless check caught a bit flip. `key add` took 2.98 s. Kopia pack names are random.<br>**Probe 4:** exact sizes 535/535; presence 50/50 (C31).<br>[README](../../spikes/A6-S1/README.md) |
| A6-S1-B ZFS posture cells | A raw send exposes no names or content. A locked dataset shows names and sizes only. A scrub needs no key and names no files. `file://` unlocks unattended. `change-key` is cheap | Informs the B column | OL | — | SYN → results | **Kit-ready.** The script is untested: no ZFS in the container | [kit](kits/A6-S1/README.md) |
| A6-S2 Bake-off (plain CAS, OCFL variant, restic out-of-screen comparator) | The CAS meets BUD-INGEST, BUD-RESTORE and BUD-AUDIT with RAM well below 4 GB; OCFL is similar; restic needs a hash map | Pass → plain CAS in ADR-0012. Fail → reconsider OCFL or restic, or parallel ingest | OL (Wave 2) | BUD-INGEST, BUD-RESTORE, BUD-AUDIT | `PUB+SYN → results` (H3 Tier L) | **Kit-ready** | Smoke run only (tmpfs, 229 MB, rc 0, 28 s; not evidence):<br>• CAS ingest 76.6 MB/s, keyless audit 362.9 MB/s, restore max 0.012 s, catalog rebuild byte-identical, RSS 20.6 MB;<br>• OCFL 60.2 MB/s;<br>• restic `dump` max 0.868 s, `check --read-data` 209.5 MB/s, RSS 162 MB.<br>**Amendments for Wave 2:**<br>• add restic-holding-ciphertext mode;<br>• record files/s and ingest impact during audit;<br>• align OCFL extension 0003 vs 0004;<br>• add sealed-h0 and A″ variants.<br>[kit](kits/A6-S2/README.md) |
| A6-S3 Crash consistency | No ACKed item is lost; nothing is ACKed before it is durable; reconciliation is automatic, including when the disk fills | Pass → layout code acceptable. Fail → fix it or adopt an engine | CT | — | SYN → results | **Pass** (container; power cuts emulated with LazyFS, not real) | 400 kills and 130 emulated power cuts: 0 violations. The no-fsync control failed 12/12. Reproduction: 80 kills, 0 violations.<br>**Disk full:** 100 trials across five placements: 0 I1/I2 violations; 0 new ACKs while full; 100/100 finished; 40 torn lines truncated; 40 orphans quarantined. `recover` while full failed only in 2 catalog-full trials, both with 0 ACKs.<br>**Not covered:** ENOSPC at fsync, ZFS full-pool behaviour, lost directory entries.<br>Measured with plain-hash naming only. [README](../../spikes/A6-S3/README.md) |
| A6-S3-OL VM power cut ×10 + ZFS disk full | The same invariants hold after real power-offs and with a full ZFS pool | As A6-S3 | OL | — | SYN → results | **Kit-ready.** ZFS hooks untested; the hook mechanism was smoke-tested on tmpfs (2 trials, 0 violations) | [kit](kits/A6-S3/README.md) |
| A6-S4 Catalog loss | Rebuilding from the store gives a byte-identical canonical export | Pass → the catalog is a projection. Fail → back up the catalog as primary data | CT | — | SYN → results | **Pass** | Byte-identical in 3 scenarios. Fixed two defects: no single-writer lock, and the lock being released by Go's GC.<br>Reproduced: a second writer was refused. A kill after 401 ACKs plus catalog deletion, then rebuild: 0.49 s, 1,135 rows identical, 600/600 truth, audit 1,135 OK.<br>A files-only rebuild loses epoch, `committed_at` and `meta_sha256`. [README](../../spikes/A6-S4/README.md) |
| A6-S5 Format independence | A one-page procedure (coreutils + age + optional sqlite3) restores byte-identical files; restic ↔ rustic | Pass → weighted in ADR-0012 | CT | BUD-RECOVERY (proxy), BUD-RESTORE | SYN → results | **Pass** | X25519: 176/176 with age 1.1.1, age 1.3.1 and rage 0.12.1. restic 0.19.1 ↔ rustic 0.11.4: 176/176. PQ: only Go age ≥ 1.3 of those CLIs **natively**; the `age-plugin-pq` route (C33) was not part of this spike. Procedure reused in this pass: 535/535 with age 1.3.1. Timings are tmpfs, not evidence. [README](../../spikes/A6-S5/README.md) |
| A6-S6 A′ rewrap round trip | Rewrapped files open with X (Go and Rust); h0 still verifies against the device record | Pass → A′ feasible. Fail → A | CT | — | SYN → results | **Pass** (X25519). PQ: pass on mechanics; native CLI readers Go only | Payload identical 176/176. X and R open all; I_e refused 176/176. h0 MAC 176/176; signatures 200/200. Stored header 266 B (X25519), 3,184 B (PQ). **Also shows the h0 exposure:** h0 + payload opens with I_e 176/176 (C32). The Rust rewrap is not built. [README](../../spikes/A6-S6/README.md) |
| A6-S7 (proposed) Sealed h0, self-check, deterministic h1, A′ vs A″ | With h0 sealed, nothing on the box plus I_e opens stored objects. The self-check catches a wrong-X rewrap, a corrupted stanza and a mixed profile. An isolated verifier recomputes a deterministic h1 byte for byte and catches a targeted miswrap. A mixed-header decrypt test is included | Pass → A′ amendments hold. Fail → A″, or attended verification | CT | BUD-INGEST (cost of A′ vs A″) | SYN → results | **Not started** | — |

Real hardware was replaced only where stated: LazyFS emulated power cuts in A6-S3.

## Review response

### Round 2 (2026-10-07): every critical and major issue, plus the minors

There were no critical issues in round 2.

| Severity | Issue (lens) | Response |
|---|---|---|
| Major | The PQ heir/reader conclusion ignored `age-plugin-pq`, contradicting D2 C22 (sources) | **Fixed.** C33 was added after the synthesizer re-read the v1.3.2 module source. Q6, §F4 and OD-06 input now say: one independent CLI implementation; other CLIs through the plugin (identities converted with `-identity`); library readers typage and kage. The doomsday kit carries Go age v1.3.2, `age-plugin-pq` and one non-Go reader, aligned with D2. |
| Major | JSON key claims and recommendation lagged the note's corrections (sources, adversary) | **Fixed at the source.** The structured output returned with this note is regenerated from it: K9 → C14r, K11 → C29r, "no plaintext online copy", the corrected Q1, and DR-A6-3 = (a). |
| Major | A′'s protection lasts only until the next attended X session if X is loaded on the ingest host (logic) | **Fixed by a new requirement.** X-requiring work runs only in a separate, freshly booted environment with read-only store access, or on the air-gapped machine (amendment 4, §F3 item 6). The same-host limit is stated. Owner-time cost is listed under OD-07, unmeasured. D1 gets the attack-tree case. |
| Major | The stolen-box comparison was applied unevenly (logic) | **Fixed.** The matrix splits stolen-box rows by unlock type. The finding now rests on what the running-host key and a compromised ingest VM can read. OD-07's rationale is rewritten, and the keyless argument is dropped. Same-house Tang is stated to give no theft protection (adversary). |
| Major | BUD-AUDIT and "verifiable" are met only under a weaker reading (logic) | **Raised as DR-A6-5** to H1/A7/owner. C19 is no longer cited as BUD-AUDIT evidence for A′. A7-S4 can pass unattended on canaries only; this is recorded as a conflict with the PLAN spike. |
| Major | DR-A6-3 option (d) contradicted K3 and A1 (logic); (d) does not stop size confirmation and breaks path = hash idempotency (adversary) | **Fixed.** K3 is now one rule for all candidates. (d) is **withdrawn as a recommendation**. Default (a) plain-SHA-256 names, or (b) if C5/D2 choose a theft-resistant unlock. (d) needs K3 re-scoring and an A6-S3/S4 re-run first. Size padding is referred to A2. |
| Major | A″ was deferred without a convincing reason (logic) | **Fixed.** Direct comparison in §F1b. A″ is presented as a sub-option of OD-07 with an explicit switch rule (A6-S7 result, A2/D2 crypto review). A6 still leans A′, for the independent recovery path and lower cost. Reasons are stated. |
| Major | The self-check gives no assurance against a compromised ingest VM, and A′ removes AR-08's re-verifying signer (adversary) | **Acknowledged; mitigation proposed, not built.** New matrix row. §F3 item 5 states the limit and proposes deterministic h1, re-checked by an isolated verifier, or having the verifier perform the rewrap. Added to A6-S7 and D4-S4. **Listed as unresolved.** |
| Major | The stolen-box guarantee rests on an unmeasured design and an unspecified unlock (adversary) | **Fixed in wording.** Matrix cells are marked conditional on A6-S7 and on the unlock type. Same-house Tang gives no theft protection. Off-premises or attended unlock is required if theft resistance is a goal (C5/D2). |
| Minor | Plakar maturity framing (sources) | Fixed. C17 is restated with C34. K6 for Plakar is marked weak, and K2/K3 carry the knockout. |
| Minor | PBS 4.x exists (sources) | Added as C35, secondary only, not load-bearing. |
| Minor | Date inconsistency (sources) | Fixed. The run span is stated in the header; Sources carry the real access dates. |
| Minor | Audit arithmetic needs a seek term (sources, logic) | Fixed: Q9 and §F2. |
| Minor | #187 dependence (sources, logic) | Fixed. C4's knockout rests on design.rst alone; C25 is corroboration only. |
| Minor | CPU vs wall time (logic) | Fixed: wall time, with worker counts and conditions. |
| Minor | Bake-off goes beyond "at most three survivors" (logic) | Fixed. OCFL is counted as a CAS variant, so there are two survivors. restic is labelled an out-of-screen comparator in DR-A6-1, and the deviation goes to H1 and the owner. |
| Minor | Key epochs vs held snapshots (logic) | Fixed: placement constraints in §F3 item 12 and §F8, with a C5/C6 hand-off. |
| Minor | Detection without repair (adversary) | Fixed: redundancy requirement in §F2 and §F8; intake C5. |
| Minor | File-key reuse sign-off (adversary) | Kept as an explicit A2/D2 sign-off. If it is rejected, choose A″ (§F1b). |
| Minor | restic K3 small-file nuance (adversary) | Fixed (C5). |
| Minor | K10 mixing restriction is a code read (adversary) | Labelled as a source read; a mixed-header decrypt test is added to A6-S7. |
| Missed | Header-sidecar layout; padded headers and block cloning; rustic `FixedSize`; X in non-exportable hardware as an online oracle; network-bound unlock for A/B/C; separate X environment; unscreened engines; deterministic h1; par2/`copies=2`; size padding; off-premises unlock | All named: §F1, §F2, §F3, §F4, §F8, DR-A6-4 option (d), and the hand-offs. |

### Round 1 (2026-10-06), condensed

| Severity | Issue | Response |
|---|---|---|
| Critical | Clear h0 in the manifest lets I_e open current-epoch stored objects | h0 sealed to {X, R} (§F3 item 4). C32 records the measurement. A6-S7 will measure the sealed form, which is **still unmeasured**. |
| Major | A′ cannot verify the rewrapped header; conflict with ADR-0008 wording | Self-check, attended X audit and fallback (§F3 items 4–6); DR-A6-4. |
| Major | C14 overstated | Contested; C14r. |
| Major | Derivatives and catalog break the A′ claims | Matrix rows; the claim is narrowed. |
| Major | restic K5 assumed plaintext | Container mode screened. |
| Major | Unattended real-object drills impossible | Listed as a cost; A7 hand-off. |
| Major | No tamper story for the store | §F8. |
| Minors | Q1 vs Probe 3; keyless claim; asymmetric knockout; "Conflicts: none"; OD-07 default; BUD-INGEST; OCFL extension; escrow wording; file-key reuse; ZFS tags; Kopia BLAKE2; PQ readers; S29; audit arithmetic; DR-A6-3 options | All fixed in round 1 and kept here. |

## Conflicts with settled text

None is resolved here. Each is a reading the owner must confirm.

- **"Encrypted to the homelab public key" and "the owner (admin) holds the private key"** (CLAUDE.md, ADR-0001 §2, R-22). This posture turns one homelab key into rotating ingest keys I_e plus an offline archive key X, and R if OD-08 accepts it. ADR-0008 already asks the owner to confirm this or amend ADR-0001 §2 (DR-D2-4), and OD-07 depends on the same confirmation. Rotation also interacts with the one-way door "pinned homelab key(s) in the first kit" (D3, Gate C) and with the ADR-0002 stick.
- **"Data integrity over everything: backups must be verifiable and restorable"** (CLAUDE.md). Under A′/A″ the decryptability of stored objects cannot be proven online. It holds only through the §F3 self-check and attended X audits. A compromised ingest VM can make new commits silently unrecoverable until deterministic h1 plus an isolated verifier exist. If the owner reads the line as "provable at any time without the owner", this posture conflicts with it, and A is the alternative.
- **BUD-AUDIT "full app-level audit"** (a proposed budget owned by H1, not settled text) and the **PLAN A7-S4 "unattended nightly restore drill"**. Under A′ both are met only in a weaker reading (DR-A6-5).
- **"Prefer an existing, proven format over inventing one"** (CLAUDE.md). DR-A6-2 reads this as age v1 per object plus a one-page layout of our own. That is an interpretation, not settled text. Sealed h0 and any sidecar files add further layout of our own.
- **Restore delivery** (CLAUDE.md: "re-encrypting to the target device's own key and staging in an expiring R2 prefix"). This is compatible with the posture, but each restore needs X on some host. Where that host is now has a requirement (§F3 item 6). A rewrap-based restore (C22) is A8's decision.
- ADR-0001 §2 "plaintext catalog (e.g. Postgres)" still holds; the "e.g." leaves ADR-0013 free.

## Open questions

| Question | Who | By when |
|---|---|---|
| Sealed-h0 form, size and exposure; self-check encoder; deterministic h1; A′ vs A″ switch (A6-S7) | A6, A2, G2 | Gate A |
| File-key reuse argument (§F3 item 9): accept, or choose A″ | A2, D2 crypto review | Gate A |
| Rewrap verification wording (DR-A6-4); X-audit sample size and cadence | D2, A7 | Gate A |
| BUD-AUDIT meaning under A′ (DR-A6-5); A7-S4 scope | H1, A7, owner | Gate A |
| Where X runs (separate environment vs air-gapped machine); owner time per restore against BUD-RESTORE and BUD-SUPPORT | D2, A8, C8 | Gate A (requirement); Wave 2 (timing) |
| Epoch interval, or rotation triggered by staging drain; standby keys | D2 | Gate A |
| Isolated verifier VM or a non-exportable TPM/HSM for I_e; separate receipt signer (AR-08) | D1, D4, D2 | Wave 2 (AR-08 revisited at Gate A) |
| Store immutability: write-once, holds, off-box manifest anchor; header-sidecar layout (§F8) | A6, D4 (D4-S4), C5 | Wave 2 |
| Pool redundancy, `copies=2` or par2 for the store dataset | C5, A7 | Gate A (intake C5) |
| Catalog dataset unlock (off-premises key server vs Tang vs prompt) and dataset layout | C5, D2 | Gate A |
| Owner's current setup: Proxmox/PBS versions, encryption, free RAM, bake-off space (intake C1, C3, C5, C6, C12) | H2 | Wave 1 exit |
| Real ingest rate (parallel verify and rewrap), index RAM, audit MB/s and files/s on the real corpus | A6-S2 (OL) | Wave 2 |
| Screen Perkeep, Duplicacy, duplicity, rdedup, Bareos/Bacula, Tahoe-LAFS and S3 substrates from primary sources | A6 | Wave 2 |
| OCFL wrapper and layout extension (0003 vs 0004) | A6-S2 | Wave 2 |
| If OD-06 = PQ: doomsday-kit readers (Go age v1.3.2, `age-plugin-pq`, one non-Go reader); whole-file decrypt by typage or kage on the A6-S5 corpus (not tested) | A2, A7, D2-S3 | Gate A |
| Does A2's padding apply to stored objects? (Probe 4 measured exact sizes on unpadded objects) | A2 | Gate A |
| PBS 4.x current docs (primary routes blocked) | H1 (route) | Before C8 relies on PBS |
| restic #533 current state (`gh api` refused) | H1 (route) | Not blocking |
| Raw encrypted `zfs send` on Linux OpenZFS 2.4.x (relevant only to B) | C5 | Gate C |
| Immich external-library read-only mode over a generated tree | C8 (OD-13) | Wave 2 |
| Restore delivery: fresh re-encryption vs rewrap (C22) | A8 | ADR-0028 |
| One shared rewrap test-vector set for A6-S6, D2-S2 and A2-S3 | A2, D2, A6 | Wave 2 |

## Recommendation

1. **Posture (OD-07): the offline-archive-key posture.** Every stored object is a standard age v1 file whose header is exactly {X, R}, and the ingest key I_e rotates. Build it as **A′** (rewrap the header and keep the payload) with four amendments:
   - h0 sealed to {X, R};
   - a write-time self-check;
   - attended X audits;
   - X used only in a separate, freshly booted environment.

   Switch to **A″** (a fresh file key) if A6-S7 or the A2/D2 crypto review goes against A′.

   **Why:** compared with A on the same unlock, a compromised running host or the always-loaded key cannot read stored content. A thief can read it only if the unlock is something the thief can trigger. It does not protect metadata, derivatives or store integrity; those need the catalog's encrypted dataset, a theft-resistant unlock and §F8.

   **Support:** verified C1, C2, C3 and C10; the measured C32 and A6-S1/A6-S6. Contested C14 and C29 are **not** used.

   **What would change it:**
   - the owner wants an automatic plaintext gallery in v1 (→ B);
   - the owner reads "verifiable" as "provable without the owner at any time", or rejects attended restores in a separate environment (→ A);
   - DR-A6-5 is answered "full decryption audit monthly" (→ A);
   - D2 finds rotation too costly (→ A, with R from day one).

   **No default:** Gate A is blocked until the owner decides. ADR-0012 is drafted against this recommendation.
2. **Engine (ADR-0012): a plain content-addressed store of age objects on ZFS,** named by plain SHA-256 (A1). It has a hex fan-out, write-once objects, an append-only manifest specified in one page, and a redundant pool (or par2). None of the screened engines passes the knockout. The A6-S2 bake-off (Wave 2) compares plain CAS, the OCFL variant and restic as an out-of-screen comparator, including restic holding ciphertext. **Support:** verified C4–C9 and C17 (facts), and spikes A6-S3, A6-S4 and A6-S5.
3. **Catalog (ADR-0013):** Wave 2, with the requirements in §F7.

## Decision requests

### OD-07: Homelab at-rest posture

- **Needed by:** Gate A (one-way door #4). **No default:** Gate A stays blocked until the owner decides.
- **Evidence:** §F1, §F1b, §F2, §F3, §F8; spikes A6-S1 and A6-S6; ADR-0008; D1 AR-08.
- **Options:**

  | Option | What it means for the family | Cost (money and owner time) | Reversibility | Risks |
  |---|---|---|---|---|
  | **Offline archive key, built as A′** (recommended) | Nothing visible. Restores wait for the owner's archive key | Key ceremony; automated I_e rotation; the owner brings X, in a separate freshly booted environment, for restores, rebuilds, real-object drills and X audits (time not measured) | Costly to leave: moving to B or C means decrypting or re-encrypting the whole store. A′ ↔ A″ is reversible for new objects | New rewrap path and self-check; silent miswrap by a compromised VM until deterministic h1 exists; metadata still exposed through the catalog |
  | Offline archive key, built as A″ (sub-option) | Same | Same, plus about 1.4–1.5× ingest wall time (tmpfs) | Same | No independent recovery path if h1 is bad; loses byte-exact upload provenance |
  | A | Nothing visible | Least work | Costly | The always-loaded key and a compromised host read everything; adding R later rewrites the whole store |
  | B | Easiest path to a family gallery | ZFS key handling | Costly | Unlock = read-everything key; send/recv bug history |
  | C | Nothing visible | Engine operations | Costly | Symmetric key reads everything; restore by hash needs a map |

- **Recommendation:** the offline archive key, built as A′. Its advantage is about what the running host's key and a compromised ingest VM can read. It is **not** that audits, scrubs or copies need no key, since A has that too. Theft resistance comes from the unlock choice (C5/D2), whatever the posture.
- **Touches settled text:** yes, as readings to confirm: "homelab public key / owner holds the private key" (with DR-D2-4), and "verifiable and restorable" (with DR-A6-5).

### DR-A6-1: Bake-off shortlist for A6-S2

- **Options:**
  - (a) plain CAS and its OCFL variant (the two survivors), plus restic as an **out-of-screen comparator** in plaintext and ciphertext-container modes;
  - (b) plain CAS and OCFL only.
- **Recommendation:** (a). ADR-0012 can then show the measured cost of not adopting a proven engine. This goes beyond PLAN's "at most three survivors", because restic did not survive the screen. H1 and the owner should accept the deviation.
- **Touches settled text:** no. **Default:** (a).

### DR-A6-2: Reading of "prefer an existing, proven format over inventing one"

- **Options:**
  - (a) the format is age v1 per object (C2SP spec, independent readers), optionally in an OCFL 1.1 root, with a one-page layout of our own;
  - (b) the owner means a proven backup engine. That forces restic in posture C.
- **Recommendation:** (a).
- **Touches settled text:** it interprets a CLAUDE.md line without changing it. The owner must confirm.

### DR-A6-3: Stored-object names reveal plain SHA-256 to someone holding the disks

- **Options:**
  - **(a) Accept it** and record it in OD-17. Audits work from the manifest; the heir can find a file by its hash; path = hash keeps `put_blob` idempotent.
  - **(b) Encrypted dataset for the store.** Names are hidden while it is locked. This helps only with a theft-resistant unlock.
  - **(c) Keyed names, HMAC(store key, sha256).** The heir procedure then needs the store key.
  - **(d) Name objects by their ciphertext SHA-256.** This hides name-based confirmation only, because sizes still leak (C31). It breaks path = hash idempotency, its K3 would rest on the in-store manifest, and the A6-S3/S4 results do not carry over to it.
- **Recommendation (changed in round 2):** **(a) as the default**, or (b) if C5/D2 choose a theft-resistant unlock for the catalog anyway. (d) is withdrawn until K3 has been re-scored for every candidate and A6-S3/S4 have been re-run. Size leakage goes to A2 (padding).
- **Reversibility:** a rename pass. **Needed by:** Gate A.

### DR-A6-4: Rewrap verification under A′ (joint with D2)

- **Question:** should ADR-0008 Decision 1's "verify X decryption of every rewrapped header" be replaced?
- **Options:**
  - **(a) Replace it with:**
    - a write-time self-check;
    - a deterministic h1 recomputed by an isolated verifier before the receipt is signed;
    - attended, sampled X unwrap with an `x_verified` state;
    - sealed h0 plus the escrowed I_e kept as the fallback.
  - (b) Keep "every header" literally. That needs X online at ingest, which is posture A in effect.
  - (c) Attended verification of every object before the ACK. This breaks BUD-TTS.
  - (d) (round 2) Hold X in non-exportable hardware online, as a rate-limited decryption oracle used to verify every header. On a Linux homelab this works for the classic profile only (ADR-0008). It exposes a decryption oracle to a compromised host.
- **Recommendation:** (a).
- **Needed by:** Gate A.

### DR-A6-5 (new): What "full app-level audit" means in BUD-AUDIT under A′/A″

- **To:** H1 (budget owner) and A7 (ADR-0029). The owner confirms.
- **Options:**
  - (a) A monthly full keyless bit-stability audit, plus X-sampled decryption at each attended session, with a minimum coverage rate set by A7. A7-S4 runs unattended on canaries; real-object drills are attended.
  - (b) A monthly full decryption audit. That keeps X online for 28 h or more a month (arithmetic), so it means posture A.
  - (c) Keep the wording and accept that A′ does not meet it.
- **Recommendation:** (a).
- **Needed by:** Gate A, because it bears on OD-07.

### OD-06 (input from A6)

- If PQ is chosen, stored objects have one independent CLI implementation (Go age ≥ 1.3). Other CLIs can read them through `age-plugin-pq`, after converting the identity. Library readers typage and kage also exist.
- A6 accepts either profile, but requires uniform stored headers: {X, R} both PQ or both X25519.
- The doomsday kit then carries static Go age v1.3.2, `age-plugin-pq` and one non-Go reader.

## Hand-offs

| To | What | Why |
|---|---|---|
| D2 | DR-A6-4 (including option d); h0 sealed; epoch interval or drain-triggered rotation; TPM/HSM for I_e; uniform stored profile; **X used only in a separate environment**; file-key reuse sign-off | ADR-0008 Decisions 1, 6, 8 |
| A2 | `stored-v1` header plus sealed h0; **deterministic h1 derivation (HKDF label tied to the file key)**; independent encoder for the self-check; file-key reuse reasoning; does padding apply to stored objects? | `object-format.md` §5, §6.1, §9 |
| A3 | `put_blob` stores ciphertext; streaming verify; record `stored_sha256`; ACK only after the self-check and the verifier's h1 recompute; parallel verify and rewrap for BUD-INGEST | ADR-0009 |
| A7 | DR-A6-5; keyless audit = bit-stability only under A′; X-audit cadence; A7-S4 on canaries; doomsday-kit readers; derivative policy (OD-16); par2 vs `copies=2` | ADR-0029 |
| H1 | DR-A6-5 (BUD-AUDIT wording); DR-A6-1 deviation from "at most three survivors"; blocked sources (Proxmox domains, restic `gh api`); run date span | `budgets.md`, `sources.md` |
| D1 / D4 | AR-08: new row "silent unrecoverability of new commits"; attack-tree case "persistent ingest compromise, then attended restore"; isolated verifier performing the rewrap; §F8; fault cases "rewrite object + manifest line" and "targeted miswrap" | Threat register, D4-S4 |
| C5 / C6 | Datasets and placement: store (write-once, held snapshots, redundancy); catalog and derivatives (encrypted); I_e in tmpfs only, never on held or snapshotted datasets; sealed h0 and online bundle allowed on the store; **theft-resistant unlock (off-premises or attended); same-house Tang gives no theft protection**; intake question on pool redundancy | ADR-0030/0031 |
| A8 / C8 | X environment for restores; owner time per restore against BUD-RESTORE and BUD-SUPPORT; prefer fresh re-encryption for restores (C22); keep PBS for VM and catalog backups; Immich check for OD-13 | ADR-0028, ADR-0032 |
| D3 | I_e rotation vs the pinned-key one-way door and the ADR-0002 stick | Gate C |
| Wave 2 spike runner | A6-S2 amendments (restic ciphertext mode, files/s, ingest impact, OCFL extension, sealed-h0 and A″ variants); A6-S7 | A6-S2, A6-S7 |
