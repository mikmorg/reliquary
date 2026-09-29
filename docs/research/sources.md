# Source-reachability register

- **Owner:** H1. Workstreams report blocked sources here (through H1). They do not quietly swap in secondary sources (PLAN §5.4).
- **Tested:** 2026-09-29, from the cloud research container, through its egress proxy. Test method: `curl` with the proxy CA, one request per URL. Also tested: the WebFetch, WebSearch, Context7 and GitHub MCP tools.
- **Result of spike H1-S1:** **Fail.** 7 of the 10 required primary sources are reachable by some primary route. Smart App Control is only partly covered. NDSA Levels and the Play photo/video policy are reachable only as search snippets. Per the plan, this raises an **allowlist request to the owner before Wave 1** (below), and the affected claims are marked **secondary only** until it is granted.

## How to read a result

| Result | Meaning |
|---|---|
| **Direct** | The vendor's page loads from the container. Primary. |
| **Primary mirror** | The vendor's own documentation source repository loads from `raw.githubusercontent.com`. Treat it as primary, and record repo, branch, path and access date. |
| **Search only** | Only WebSearch result titles and snippets are available. **Secondary only**: never the sole support for an ADR. |
| **Blocked** | The proxy refuses the connection (HTTP 403 on CONNECT). WebFetch reports `EGRESS_BLOCKED` for the same hosts. |

## H1-S1: the ten primary sources

| # | Source | Direct URL result | Working route | Verdict |
|---|---|---|---|---|
| 1 | R2 limits and presigned URLs | developers.cloudflare.com: Blocked | Primary mirror: `cloudflare/cloudflare-docs` @ `production`, `src/content/docs/r2/platform/limits.mdx` and `r2/api/s3/presigned-urls.mdx` (both HTTP 200). Context7 `/cloudflare/cloudflare-docs` also returns excerpts that cite the same files. | Reachable (mirror) |
| 2 | Queues pull consumers | developers.cloudflare.com: Blocked | Primary mirror: `.../queues/configuration/pull-consumers.mdx` (200) | Reachable (mirror) |
| 3 | Tauri updater | v2.tauri.app: Blocked | Primary mirror: `tauri-apps/tauri-docs` @ `v2`, `src/content/docs/plugin/updater.mdx` (200) | Reachable (mirror) |
| 4 | Android data-transfer options | developer.android.com: **Direct** (200) | — | Reachable (direct) |
| 5 | C2SP age spec | c2sp.org: Blocked | Primary mirror: `C2SP/C2SP` @ `main`, `age.md` (200). The file calls itself the "editor's copy", so note the commit you cite. | Reachable (mirror) |
| 6 | Immich mobile backup | docs.immich.app: Blocked | Primary mirror: `immich-app/immich` @ `main`, `docs/docs/features/mobile-backup.md` (200) | Reachable (mirror) |
| 7 | OCFL spec | ocfl.io: Blocked | Primary mirror: `OCFL/spec` @ `main`, `1.1/spec/index.md` (200) | Reachable (mirror) |
| 8 | NDSA Levels of Digital Preservation | ndsa.org: Blocked; osf.io: Blocked | WebSearch only. Result titles mention a version 2.1 announcement on ndsa.org, but the page itself could not be read. Route that claim to T2. | **Secondary only** |
| 9 | Play photo and video permissions policy | support.google.com and play.google.com: Blocked | No mirror found. WebSearch only. | **Secondary only** |
| 10 | Smart App Control FAQ | support.microsoft.com and learn.microsoft.com: Blocked | Partial primary mirror: `MicrosoftDocs/windows-dev-docs` @ `docs`, `hub/apps/develop/smart-app-control/overview.md` (200, `ms.date: 11/18/2025`). This is the developer overview, not the consumer FAQ. It covers blocking of unsigned code, signing via the Trusted Root Program, evaluation and enforcement modes, and clean-install-only enablement. It does **not** cover the FAQ's "no Run anyway" and "turn off without reinstalling" points. | **Partial**: FAQ-only claims are secondary only |

## Host register

### Documentation and research hosts

| Host | Result | Workaround | Used by |
|---|---|---|---|
| developer.android.com | **Direct** | — | B2, B3, T1 |
| developer.apple.com | **Direct** | — | B4 |
| kotlinlang.org | **Direct** | — | B2 |
| raw.githubusercontent.com | **Direct** | The main route for vendor doc sources (see mirrors below) | all |
| developers.cloudflare.com, blog.cloudflare.com, www.cloudflare.com | Blocked | Mirror `cloudflare/cloudflare-docs` (`production` branch; changelog entries are in the same repo); Context7 `/cloudflare/cloudflare-docs` | C1, C2, C3, C7, C8, T2 |
| v2.tauri.app, tauri.app | Blocked | Mirror `tauri-apps/tauri-docs` (`v2` branch) | B7, D5 |
| docs.rs | Blocked | Download the crate from static.crates.io and read its source and doc comments, or run `cargo doc` locally (cargo is installed) | all Rust work |
| learn.microsoft.com | Blocked | Mirrors under `MicrosoftDocs/*` (for example `windows-dev-docs`) | B1, B7, E3 |
| support.microsoft.com | Blocked | No mirror. Secondary only. | B7, T2 |
| support.google.com, play.google.com | Blocked | No mirror. Secondary only. `developer.android.com/google/play/...` pages load directly and cover some requirements (for example target API). | B3, E5, T2 |
| android-developers.googleblog.com, source.android.com | Blocked | Search only | B2, B3, T2 |
| support.apple.com | Blocked | Search only | B4, B7 |
| c2sp.org, age-encryption.org | Blocked | Mirrors `C2SP/C2SP`, `C2SP/CCTV` | A2, F3 |
| ocfl.io | Blocked | Mirror `OCFL/spec` | A4, A6 |
| restic.readthedocs.io, restic.net | Blocked | Mirror `restic/restic` `doc/` (for example `doc/design.rst`, 200) | A6, F1 |
| kopia.io | Blocked | Mirror `kopia/kopia` | A6, F1 |
| docs.immich.app, immich.app, ente.io | Blocked | Mirror `immich-app/immich` `docs/`; Ente source on raw GitHub | F1, F2, B2 |
| openzfs.github.io, pve.proxmox.com, www.proxmox.com | Blocked | Mirrors `openzfs/zfs`, `proxmox/pve-docs` (both 200) | C5, C6 |
| ndsa.org, osf.io, www.loc.gov, www.digitalpreservation.gov | Blocked | Search only | A7 |
| www.rfc-editor.org, www.ietf.org, datatracker.ietf.org | Blocked | Search only. No general RFC mirror found. | D3, A4, C3 |
| eprint.iacr.org, arxiv.org, dl.acm.org, www.usenix.org | Blocked | Search only | F3, D1, E-track literature |
| csrc.nist.gov, nvlpubs.nist.gov, owasp.org, www.w3.org | Blocked | Mirrors `OWASP/ASVS`, `w3c/wcag` (both 200); NIST search only | D2, D7, E6 |
| dontkillmyapp.com, www.reddit.com, news.ycombinator.com, hn.algolia.com | Blocked | Search only; GitHub issue search for issue data | B2, F2 |
| aws.amazon.com, textslashplain.com, www.backblaze.com, resend.com, postmarkapp.com, tus.io, sigsum.org, www.sqlite.org, www.postgresql.org, doc.rust-lang.org, docs.syncthing.net, mozilla.github.io, en.wikipedia.org, web.archive.org, gitlab.com, context7.com, www.google.com | Blocked | Search only, or the project's GitHub repo on raw where one exists (for example `mozilla/uniffi-rs`, `cloudflare/workers-rs`, both 200) | various |

### GitHub

| Route | Result |
|---|---|
| raw.githubusercontent.com | Works for any public repo. |
| github.com, api.github.com, codeload.github.com (curl) | The tunnel opens, but GitHub answers 403 "GitHub access to this repository is not enabled for this session" for repos outside this project. |
| GitHub MCP `search_issues` | Works across public repos (tested on `immich-app/immich`), with issue numbers, titles, dates and total counts. Use it for F1/F2 issue mining. |
| GitHub MCP `get_file_contents` | Limited to `mikmorg/reliquary`. Use raw.githubusercontent.com instead. |

### Other tools

| Tool | Result | How to use it |
|---|---|---|
| WebFetch | Same egress policy as curl: `EGRESS_BLOCKED` on every blocked host tested | No extra reach |
| WebSearch | Works; returns titles, URLs and a summary | Discovery and secondary evidence only. Load-bearing claims need a primary route. |
| Context7 | Works (`/cloudflare/cloudflare-docs` tested) | Its excerpts cite the vendor's source file. Treat them as primary content, but re-fetch the cited file from raw GitHub for any load-bearing claim and record the path. |
| Cloudflare plugin MCP | Not present in this session | The plan lists it as a route. If the owner enables it, record it here. |

### Build and package hosts (for spikes and the build phase)

| Host | Result |
|---|---|
| crates.io API (needs a User-Agent), static.crates.io, index.crates.io | Direct |
| pypi.org, files.pythonhosted.org, registry.npmjs.org, proxy.golang.org, nodejs.org | Direct |
| repo1.maven.org, maven.google.com, services.gradle.org, static.rust-lang.org | Direct |
| sh.rustup.rs | Blocked (a Rust toolchain is already installed) |
| dl.google.com (Android SDK and emulator images) | **Blocked**: affects B2-S3 (16 KB-page emulator) and any Android build in the container |
| Local tools present | cargo, rustc, node/npm, python3, go |

### Cloudflare sandbox endpoints (needed by every `[SB]` spike)

| Host | Result | Impact |
|---|---|---|
| api.cloudflare.com | **Blocked** | wrangler cannot deploy Workers, create buckets or read Queues from the container |
| dash.cloudflare.com | Blocked | Owner uses it from a browser anyway |
| *.workers.dev | **Blocked** | The container cannot call a deployed test Worker unless it sits on an allowed custom domain |
| r2.cloudflarestorage.com (bare) | Blocked | — |
| `<account>.r2.cloudflarestorage.com` | Inconclusive: CONNECT allowed, TLS handshake failed for a made-up account ID | Retest with the real sandbox account endpoint |

**Consequence:** no `[SB]` spike (C1-S1, G2-S1, A0 on real R2, A3-S3, C2, C3, D3 and others) can run from this container until the owner widens network access. `[CT]` work on local emulators is not affected.

## Owner action: allowlist request

Change it in the environment's settings: open the cloud environment menu in the session's title bar, choose **Edit**, then under **Network access** either pick a broader access level or add the domains below to the allowed list.

| Priority | Hosts | Unblocks |
|---|---|---|
| **Before Wave 1** | api.cloudflare.com, *.workers.dev (or the sandbox's own test domain), *.r2.cloudflarestorage.com | All `[SB]` spikes, including C1-S1 and G2-S1 on the critical path |
| **Before Wave 1** | support.google.com, play.google.com | Play policy (H1-S1 #9; B3 desk checks for OD-10, OD-11, OD-19) |
| **Before Wave 1** | support.microsoft.com, learn.microsoft.com | SAC FAQ (H1-S1 #10), B1, B7 |
| **Before Wave 1** | ndsa.org, osf.io | NDSA Levels (H1-S1 #8; OD-16) |
| **Before Wave 1** | developers.cloudflare.com, docs.rs, v2.tauri.app | Rendered pages, including content pulled in from partials that the raw mirrors do not show |
| Wave 1–2 | www.rfc-editor.org, datatracker.ietf.org, eprint.iacr.org, arxiv.org, c2sp.org | D3 (RFC 9421, 9449, 8628), F3 literature, A2 |
| Wave 1–2 | dl.google.com | B2-S3 emulator; Android builds |
| Wave 2 | android-developers.googleblog.com, support.apple.com, blog.cloudflare.com, ocfl.io, restic.readthedocs.io, kopia.io, docs.immich.app, ente.io, openzfs.github.io, pve.proxmox.com, www.loc.gov, csrc.nist.gov, owasp.org, www.w3.org, dontkillmyapp.com | Rendered versions of pages now read via mirrors or search |

If the owner declines, the rows marked "Secondary only" stay that way and cannot be the sole support for an ADR.

## Rules for mirrors

- **Record the exact source.** Cite a mirror as `repo @ branch : path (accessed YYYY-MM-DD)`. Add the commit SHA when a claim is load-bearing.
- **Check partials.** Doc-source files (MDX) may pull text from partials, for example `<Render file=... />` in the Cloudflare docs. Fetch the partial too, or the claim is incomplete.
- **Branch drift.** A repo branch can be ahead of or behind the published site. If the published page and the mirror could differ on a time-sensitive fact, mark the claim "mirror only" and send it to T2.
- **Re-check T2's Cloudflare facts.** T2 took them from search-engine extracts because developers.cloudflare.com was blocked. The `cloudflare/cloudflare-docs` mirror now allows a primary re-check. This is a question for T2.

## Log of blocked sources reported by workstreams

| Date | Workstream | Source | Route tried | H1 action |
|---|---|---|---|---|
| 2026-09-29 | H1 | Initial sweep (above) | curl, WebFetch, WebSearch, Context7, GitHub MCP | Allowlist request raised to the owner |
