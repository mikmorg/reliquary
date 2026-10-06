# Spike F1-S1: measurements behind the build / adopt / fork / compose fit matrix (THROWAWAY)

> Throwaway measurement scripts, not production code. Run on 2026-09-29 in the research cloud
> container. Workstream F1, see `docs/research/PLAN.md` ("F1. Build, adopt, fork or compose").

- **Exec tag:** CT (ran for real in the container).
- **Data class:** `PUB → results` (public source code, tags, docs) and `SYN → results` (random bytes
  made by the probes). No family data. Nothing talks to Cloudflare: every probe runs on 127.0.0.1.
- **Budget IDs:** none measured directly. The maintenance numbers below are inputs for comparing a
  fork or adoption against **BUD-SUPPORT** (owner time ≤ 2 h per month at steady state).
- **Scope of this folder:** the measurements only. The fit matrix, scores, effort model and ADR-0005
  are the analyst's (research note), not this spike's.

## Hypothesis and decision informed

PLAN F1-S1: *"Every cell backed by a primary source; top 2 alternatives costed. Decision rule: adopt or
fork if a candidate meets all settled requirements after a patch ≤ 30 % of the build estimate under an
acceptable licence; otherwise build, adopting the listed components."* This decides ADR-0005 / OD-02.

The spike supplies three kinds of evidence that the matrix and the effort model need and that docs
alone do not give:

1. **Behaviour probes.** For the three engines that run in a container (restic + rest-server, the
   Kopia repository server, and the Plakar server), what a *device credential* can actually do. Can
   it delete history, read back data, read other devices' data, deduplicate across devices? Who
   listens?
2. **Code size** (tokei) of every candidate's components, as the analogy base for the effort model
   and the "patch ≤ 30 % of build" test.
3. **Upstream churn:** stable releases, version epochs and commits in the last 12 and 24 months,
   from git tags. This is the input for the yearly cost of carrying a fork or pinning an adopted
   component.

## Results

### 1. Behaviour probes (SYN data, local only; not R2)

**restic v0.19.1 + rest-server v0.14.0, `--append-only --private-repos`** (`evidence/probe_restic.txt`)

| Probe | Result |
|---|---|
| Device `restic forget <snapshot>` | Refused: exit 3, HTTP 403 |
| Raw HTTP DELETE of a snapshot file or a data pack; raw overwrite (POST) of an existing snapshot | HTTP 403 in all three cases |
| Device `restic prune` when nothing is forgotten | exit 0; snapshot and pack counts unchanged (1 and 2) |
| Device restores its whole history | Yes, bytes identical |
| Device prints the repository master key (`restic cat masterkey`) | Yes (fields `mac`, `encrypt`) |
| Device writes a snapshot with a forged `--time 2001-01-01` and a forged `--host` | Accepted |
| Device `key add` (new password, same master key) | Allowed (exit 0) |
| Device `key remove` of the original key | Refused (exit 1) |
| Device 2 reads device 1's repo (`--private-repos`) | HTTP 401 |
| Same 3 MB file backed up by two devices | No cross-device dedup: two repos with separate keys (dev1 data 4,005,317 B incl. a 1 MB second file; dev2 3,003,025 B; exact bytes vary slightly per run) |
| Blob ID of a 1 MB single-chunk file | Equals plain, unkeyed SHA-256 of the file (visible only to key holders) |
| Who listens | rest-server accepts inbound HTTP; the device dials it |

**Kopia v0.23.1 repository server, two device users** (`evidence/probe_kopia.txt`)

| Probe | Result |
|---|---|
| Device config after `repo connect server` | No repository password or key. Keys present: `apiServer, caching, hostname, username, description, enableActions, formatBlobCacheDuration` |
| Where content is encrypted | On the server: the device sends content bytes in `WriteContentRequest.data` (source checks S1, S2). The server sees plaintext. |
| Default ACLs after `server acl enable` | `*@*`: APPEND on content; FULL on own snapshots, own policies and own user; READ on global and host policies |
| Device deletes its own snapshot under default ACLs | Allowed: exit 0, snapshot gone |
| Same after replacing the FULL snapshot and policy entries with APPEND/READ **and restarting the server** | Refused: exit 1, "access denied"; the device can still append |
| Same, before the ACL fix and without a restart (earlier run: POST to `/api/v1/control/refresh` plus a 3 s wait) | Delete still succeeded. Not investigated further; the probe now restarts the server. |
| Identical 3 MB file from two users | Same object ID (`48f4a964…`): cross-user dedup |
| Device 2 lists device 1's snapshots | No (manifest ACL) |
| Device 2 reads device 1's snapshot root and file bytes **by object ID** | Yes, bytes identical |
| Who listens | kopia server accepts inbound HTTPS/gRPC; devices dial it |

**Plakar v1.1.7 (Kloset v1.1.6) behind `plakar server`, delete disabled by default** (`evidence/probe_plakar.txt`)

| Probe | Result |
|---|---|
| Store encryption | Passphrase, Argon2id KDF, AES-GCM-SIV. Symmetric (source check S13). |
| Client restores with the passphrase it backs up with | Yes, bytes identical |
| Client `plakar rm -apply <snapshot>` through the no-delete server | **Succeeds** (exit 0). The snapshot is no longer listed. |
| Store on disk before and after that `rm` | 7 files, 3,701,123 B → 8 files, 3,701,339 B. Nothing was deleted; a 216 B state record was *added*. |
| Client backup without the passphrase (write-only device?) | Fails (exit 77); a writer needs the passphrase |
| Who listens | plakar server accepts inbound HTTP; the client dials it |

Whether a logically removed Plakar snapshot can be brought back with stock tooling was **not tested**.

**Source and doc checks** (`evidence/source-checks.md`) back the cells that could not be run here:
- Ente: random `<userID>/<uuid>` object keys; trash, delete and empty-trash routes for the user; a hidden 7-tap endpoint setting, or a build-time `endpoint` define.
- Immich: per-owner SHA-1 dedup index; `DELETE /assets` for the user.
- UrBackup: the server listens on 55415.
- Syncthing: folder key = scrypt(password, folder ID).
- Duplicati: GPG defaults to `--symmetric`.
- R2: S3 Object Lock APIs and headers are unsupported; R2 bucket locks are configured out of band.

### 2. Code size (tokei 15.0.0, code lines only) — `evidence/loc.csv`

Generated code, lockfiles, data and markup are excluded; test code is counted separately (see
`scripts/loc.py` for the globs). These are **analogy inputs**, not estimates of Reliquary's size.

| Component | Product code lines | Test code lines | Main languages |
|---|---:|---:|---|
| Ente Photos mobile app, `lib/` | 225,496 | 129 | Dart |
| Ente Photos native glue and plugins | 11,175 | 1,957 | Dart, Kotlin, Swift |
| Ente shared mobile packages | 46,715 | 4,068 | Dart, Swift, Kotlin |
| Ente Rust crates (shared by all Ente apps; ML 26.8k and vecdb 16.0k included) | 126,919 | 15,486 | Rust |
| Ente museum server | 54,491 | 19,414 | Go |
| Ente web (also the desktop UI) | 185,761 | 5,428 | TSX, TS |
| Immich mobile app, `lib/` (openapi excluded) | 56,761 | 0 | Dart |
| Immich native Android/iOS code | 9,238 | 284 | Kotlin, Swift, Dart |
| Immich server | 52,744 | 27,546 | TypeScript |
| Immich web | 32,822 | 5,340 | Svelte, TS |
| Immich ML | 5,045 | 178 | Python |
| restic | 41,369 | 32,161 | Go |
| Kopia (all) | 62,456 | 56,504 | Go |
| Kopia repository server + ACL code only | 3,877 | 1,757 | Go |
| Plakar CLI | 16,636 | 20,153 | Go |
| Kloset (Plakar's storage library) | 16,192 | 26,099 | Go |
| Syncthing | 66,565 | 29,791 | Go |
| Syncthing-Fork Android | 22,846 | 0 | Java, Kotlin |
| rustic_core | 19,906 | 2,278 | Rust |
| rustic CLI | 9,699 | 724 | Rust |
| Borg (`src/`) | 40,413 | 29,734 | Python, Cython, C |
| UrBackup backend (includes vendored C libraries) | 731,446 | 13,976 | C, C++ |
| Duplicati | 237,748 | 4,984 | C# |
| Nextcloud Android | 114,520 | 25,861 | Kotlin, Java |
| Reliquary `spikes/content-encryption` (throwaway) | 2,432 | 0 | Rust, Python |

**Upload-pipeline slices.** These are the code a fork would have to replace to change transport and crypto. They are a lower bound on patch surface.

| Slice | Code lines |
|---|---:|
| Ente `lib/module/upload` | 2,950 |
| Ente `lib/services/sync` | 2,933 |
| Ente crypto adapter packages + `file_key.dart` + `photos_crypto_api_adapter.dart` | 561 |
| Immich upload/backup services, repository, providers, hash/local-sync/background-worker services | 2,056 |
| Immich native Android `kotlin/` + iOS `Runner/` (includes the background upload workers) | 6,611 |

### 3. Upstream churn (git tags, window ending 2026-09-29) — `evidence/cadence.csv`

A "stable release" is a tag matching the per-repo pattern in `scripts/cadence.py`; RC, beta, canary
and nightly tags are excluded. An "epoch" is a new major version (or a new 0.minor for 0.x projects,
where each minor may break).

| Repo | Stable releases 12 m / 24 m | Epochs started in 24 m | Latest stable | Commits on default branch, 12 m |
|---|---|---|---|---:|
| Immich | 38 / 110 | v2.0.0 2025-10-01; v3.0.0 2026-06-30 | v3.2.4 (2026-09-28) | 2,855 |
| Ente (Photos mobile tags only; commits are the whole monorepo) | 33 / 62 | photos-v1.0.0 2025-03-21 | photos-v1.3.64 (2026-09-22) | 17,597 |
| restic | 2 / 6 | v0.18 2025-03-27; v0.19 2026-06-09 | v0.19.1 (2026-07-05) | 714 |
| rest-server | 0 / 1 | v0.14 2025-05-31 | v0.14.0 | 24 |
| Kopia | 6 / 14 | v0.19 … v0.23 (5 in 24 m) | v0.23.1 (2026-06-15) | 435 |
| Plakar | 10 / 14 | v1.0.1 2025-05-15 | v1.1.7 (2026-09-24) | 1,128 |
| Syncthing | 12 / 34 | v2.0.0 2025-08-12 | v2.1.5 (2026-09-08) | 241 |
| rustic_core | 6 / 19 | 0.8 … 0.13 (5 breaking minors in 12 m) | 0.13.0 (2026-08-16) | 99 |
| Borg 1.x stable | 4 / 6 | none | 1.4.5 (2026-07-19) | 2,141 |
| Borg 2.0 betas | 6 betas in 12 m; 25 in total, b1 2022-08-07 → b25 2026-09-27 | — | still beta | — |
| UrBackup backend (server tags) | 4 / 4 | none | 2.5.38 (2026-08-30) | 12 |
| Syncthing-Fork Android (repo created 2025-10; older tags inherited) | 18 / 18 | — | v2.1.5.0 (2026-09-08) | 333 |
| Duplicati (stable channel) | 9 / 11 | 2.2, 2.3, 2.4 in 12 m | 2.4.0.0 (2026-09-03) | 2,396 |
| Nextcloud Android | 14 / 32 | 33, 34, 35 in 12 m | 35.0.0 (2026-09-16) | 4,077 |

## Limits: what this spike did not do

- **Ente museum and Immich were not run.** The docker daemon was available, but their clients need
  an app or real E2EE sign-up (SRP, key generation) to exercise. Their cells rest on source reading
  (S4–S9) and the scouts' docs. The live run is the kit `docs/research/kits/F1-S2/`.
- **Not run at all:** Borg (not attempted in this run), Duplicati (no .NET runtime),
  Syncthing untrusted devices, UrBackup, Nextcloud, Synology Photos, PhotoSync, Backblaze. Their
  cells rely on the scouts' primary sources plus S10–S12.
- **No R2 or S3 run:** there is no sandbox account. Whether restic or Kopia straight to R2 gets
  no-delete behaviour from R2 bucket locks is a doc reading (S15, S16), not a measurement.
- **Code-line counts depend on the exclusion globs.** Examples:
  - Ente's Rust workspace serves several apps (Photos, Auth, Locker, Ensu) and includes ML.
  - UrBackup vendors large C libraries.
  - Duplicati's count includes PO files, and tokei misclassified some files as Modelica.

  Treat the counts as orders of magnitude.
- **Churn is measured by tags, not by breaking changes.** Immich's `changelog:breaking-change` label
  count was not read (the GitHub API is blocked from the shell).

## Re-run

```sh
cargo install tokei            # 15.0.0 used
WORK=/some/dir ./run_all.sh    # clones pinned sources (about 1 GB), builds 4 Go tools, rewrites evidence/
```

`fetch_sources.sh` pins every repository to the commit measured here. The probes need only the four
Go binaries plus `python3` and `curl`. The Plakar probe puts its `$HOME` under `/tmp`, because its
cache agent's unix-socket path must fit the 108-byte `sun_path` limit.
