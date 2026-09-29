# H3. Shared corpus and research-data governance

- **Workstream:** H3 (see `docs/research/PLAN.md`, section "H3.")
- **Status:** Draft (Wave 0). Rules take effect when the owner confirms them (owner action 1 below). Until then, apply the plan's H3 rules as the minimum.
- **Date:** 2026-09-29
- **Feeds:** every spike's "Data class" field (PLAN §2.0 spike template, `templates/research-note.md`, `templates/spike-kit/README.md`); G2 (the corpus generator); A5 (golden corpus storage); E1 (consent script and census output format); E4 (golden-set labelling); D6 (data inventory: research stores); G1 (repo guards).
- **Unblocks:** A1-S1, A6-S2, B5-S1, F3-S1, A7-S3, E4-S1.
- **Companion:** [`corpus/README.md`](corpus/README.md) lists the public sources, with licences and URLs, that make up the test corpus.
- **File name:** the plan calls this file `h3-corpus-and-data-governance.md`. It was created as `h3-research-data-governance.md` on instruction; the research index and the kit template now link here.

## Summary

- **The rule:** no family data ever enters the repo, CI, logs, agent sessions, issues, notes or the sandbox cloud. Family data stays on the device it lives on or in a private research store on the homelab. Only aggregates leave, and only after the output check (§4).
- **Six data classes** (§2): PUB (public, licensed), SYN (generated), LAB (test media the owner makes, with no people in it), AGG (checked aggregates of family data), FAM (family data) and SEC (secrets). Every spike declares which classes it reads and writes.
- **One refinement to the plan's rule** that "agents see sizes, types and counts only": a list of exact per-file sizes is a fingerprint (that is F3-S1's premise), so family sizes leave only as binned histograms or computed statistics (R3). The owner should confirm this.
- **The corpus is built from public and synthetic data** in four tiers (§6). Public sources with verified licences exist for most needs (EXIF variants, HEIC, RAW, Samsung and Pixel Motion Photos, Ultra HDR gain maps, broken files, documents, photo-size metadata). There is **no licensed public Live Photo pair, ProRAW, burst, portrait or spatial-video sample**. These need LAB fixtures, which depends on having an iPhone (OD-01).
- **All six blocked spikes can start** with the tiers here (§5). A6-S2 needs 0.8–2 TB of free homelab space, and E4-S1 and A7-S3 need the family and owner steps in §8 and §9.

## 1. The rule: no family data outside family devices and the private store

**Family data (FAM)** is any content, or information about content, that comes from a real person's device, account or archive. That includes the owner's own library and anything on a relative's device, and it includes derived data:

| Counts as FAM | Examples |
|---|---|
| Content | Photos, videos, documents, scans, thumbnails, previews, screenshots of any of these |
| Names and places | Filenames, paths, folder names, album names, device names, account names and emails |
| Embedded metadata | EXIF/XMP/QuickTime fields: GPS, capture times, camera serial numbers, owner or artist fields, face or people tags |
| Per-file derived data | Exact per-file sizes, plain or keyed hashes of real files (SHA-256, perceptual hashes, dedup IDs), per-file format IDs or decode errors, per-file labels from E4-S1 |
| Answers from people | Census raw outputs, interview notes and recordings, anything a relative said about a specific file |

**Where FAM must never go:**
- The git repo, including history, branches, pull-request text, issues and commit messages. Assume anything committed is permanent.
- CI: inputs, logs, artifacts and caches.
- Logs of any kind: spike output, shell history, crash dumps, Worker logs.
- **Agent sessions.** Transcripts are logs too, and they leave the owner's control. Never paste FAM into a Claude session.
- The sandbox Cloudflare account: R2, D1, Queues and Workers logs.
- Third-party tools: online EXIF viewers, AI services, pastebins, cloud OCR.

**The only way out** is an aggregate that passes the output check (§4) and then becomes AGG.

**If an agent finds FAM in the container** (for example, the owner uploads a real photo by mistake), it stops, does not read further, and tells the owner. §3 R12 covers the clean-up.

## 2. Data-handling classes

| Class | What it is | Examples | Licence or consent needed |
|---|---|---|---|
| **PUB** | Third-party public files or metadata with a recorded licence | Files listed in `corpus/README.md` | Licence recorded; attribution kept in the manifest |
| **SYN** | Output of the corpus generator (§7) or of a spike's own generator, from a committed config and seed | 1M-file tree, random-payload "photos", >4 GiB video, awkward filenames | None |
| **LAB** | Test media the owner makes on test devices and test accounts for a spike, under the capture rules (R8). No people in them. | A Live Photo of a houseplant, a WhatsApp-forwarded test image, a OneDrive placeholder | Owner only (no third parties appear) |
| **AGG** | Aggregates of FAM that have passed the output check | Census histograms, "% undecodable by format", precision and recall per category | Consent of the people the data came from (§9) |
| **FAM** | Family data as defined in §1 | See §1 | Consent (§9); stays in place |
| **SEC** | Secrets: keys, tokens, invite codes, dedup secrets, account recovery factors, including sandbox ones | Sandbox API token, test homelab key | Handled per D2 and D3; never logged |

**Where each class may live**

| Location | PUB | SYN | LAB | AGG | FAM | SEC |
|---|---|---|---|---|---|---|
| Git repo (history, PRs, issues) | Manifest only, until ADR-0036 (R9) | Generator, config, seed, labels; small outputs | Descriptions only, unless the owner releases a file (R8) | Yes | **Never** | **Never** |
| CI (inputs, logs, artifacts, caches) | Yes, fetched by manifest | Yes | No | Not needed | **Never** | Sandbox-scoped CI secrets only |
| Agent sessions and the research container | Yes | Yes | No, unless released | Yes | **Never** | Sandbox tokens only, never printed |
| Sandbox Cloudflare account | Yes | Yes | Yes | No | **Never** | Its own tokens |
| Owner-lab test devices | Yes | Yes | Yes | Yes | Only the owner's own data, for a spike that needs it, with a wipe step | Test credentials |
| Homelab private research store (R7) | Yes | Yes | Yes | Yes | Yes, owner only, time-limited | No (keys live where D2 says) |
| Family devices | Pushed test data only | Pushed test data only | No | Produced here | Stays here | Their own credentials |

**Declaring a spike's class.** In the research-note and kit templates, write the classes read and the classes written, for example `SYN → results`, `PUB+SYN → results` or `FAM → AGG`. Results computed only from PUB, SYN or LAB inputs are unrestricted, apart from the source licences.

## 3. Rules

| # | Rule |
|---|---|
| R1 | **Agents never see FAM.** They see only AGG that has passed §4. |
| R2 | **Filenames, paths, pixels and GPS never leave** the device or the private store. This holds even inside AGG, and even in hashed form. |
| R3 | **Sizes leave only binned or summarised.** Use log2 size bins (§7.6) or computed statistics (for example "% of files with a unique exact size"). A list of exact per-file sizes is itself a fingerprint (F3-S1), so it is FAM. |
| R4 | **No real hashes leave.** Plain SHA-256 of family files stays local, as ADR-0001 §2 already requires for the cloud. If a research script needs to compare files across devices (for example the cross-device duplicate rate for C4), it uses an HMAC key made for that one run. The owner holds the key, the keyed hashes stay in the private store, and both are deleted once the aggregate is accepted. |
| R5 | **No production keys before Gate A.** No family byte is hashed or encrypted with production keys before Gate A (PLAN §4.2). Research scripts use throwaway keys only. |
| R6 | **Show before send.** Any script or tool that runs on a family device (the E1 census, the E4-S1 labelling tool, the A7-S3 survey) shows the person the exact output on screen before anything is saved for export. It writes to a file the person hands over, and never uploads anything itself. |
| R7 | **Private research store.** FAM and LAB go in a separate dataset on the homelab, outside the repo. It is not synced to any cloud and is readable by the owner only. Raw FAM outputs (census files, keyed hashes, per-file survey results) are deleted **90 days** after their aggregate is accepted (proposed default). LAB files are kept until the owner deletes them. |
| R8 | **LAB capture rules.** Tests need byte-exact originals, so metadata cannot be stripped afterwards. Clean LAB files have to be made clean at capture: no people (family included), no home interior or exterior, house numbers, documents or screens in frame; location off, or shot at a public place; test accounts only (for example a test Google account and a test OneDrive). Before release, the owner checks each file's full metadata with ExifTool for GPS, serial numbers, and owner or artist fields. A LAB file becomes public only if the owner licenses it (for example CC0). |
| R9 | **Licences and commits.** Until ADR-0036 (OD-15) settles the repo licence, no third-party binary fixtures are committed; PUB files are fetched by manifest, pinned by SHA-256 and by upstream commit. After ADR-0036, permissive files (CC0, public domain, MIT, BSD, Apache-2.0, CC BY with attribution) up to 1 MB each may be committed. Copyleft (GPL, LGPL, AGPL, CC BY-SA) and non-commercial files stay fetch-only. |
| R10 | **Hostile fixtures.** Fuzzing crashers and deliberately malformed files are tagged `hostile` in the manifest. They are opened only in the container or a disposable VM, and never with desktop apps on the owner's workstation (D4). |
| R11 | **Logs.** Spike scripts that touch FAM print only counts and AGG. They refer to files by a per-run counter (`item 1234`), and the mapping stays in the private store. Crash reporting and telemetry follow B8, and never include paths. |
| R12 | **If FAM leaks:** stop, and do not push. If it is committed locally, remove it before pushing. If it was pushed, the owner rewrites history (for example with `git filter-repo`), force-pushes, and purges CI caches, artifacts and issue text. Treat anything pasted into an agent session as disclosed. Record the incident without the data, and tell the person concerned if the item was sensitive. |

## 4. Output check (before AGG enters the repo or an agent session)

The owner runs this check, and the person the data came from sees their own device's output first (R6).

- [ ] No filenames, paths, folder, album or device names, account names or email addresses.
- [ ] No per-file rows: every row counts at least two files, or is a statistic over many.
- [ ] Sizes are in log2 bins or statistics only; no exact-size lists (R3).
- [ ] No hashes or IDs of real files (R4).
- [ ] No GPS or place names. Time is no finer than the month.
- [ ] People appear only as pseudonyms (P1, P2 …). The mapping stays in the private store.
- [ ] Sensitive categories (medical, identity documents, intimate) appear only as family-wide totals, never per person.
- [ ] Per-person or per-device cells below 5 are shown as "<5".
- [ ] Camera and phone models are allowed (G2's device matrix needs them). Serial numbers are not.

## 5. How each blocked spike is unblocked

Tiers are defined in §6; sources are in `corpus/README.md`.

| Spike | What it needs from H3 | Corpus | Class | Where it runs | What may be committed |
|---|---|---|---|---|---|
| **A1-S1** Hash benchmark, SHA-256 vs BLAKE3, 4 device classes | Files of known sizes on each device; no real library | Tier S "size ladder" (0 B, 4 KiB … 1 GiB, 4 GiB + 1 B) plus the `seed-phone` profile (§7.5), SYN random payload | `SYN → results` | CT; test phones (OL). If the owner's own phone is used, push SYN files into a dedicated folder, delete them afterwards, and do not read the camera roll. | MB/s, energy per GB, device model, OS version |
| **A6-S2** Engine bake-off on 200–500 GB | Realistic, mostly incompressible bytes, a realistic file-size mix, some duplicates | Tier L (§6): GovDocs1 subset, Open Images originals, public media edge cases, SYN large videos and duplicates | `PUB+SYN → results` | Homelab (OL). Needs about 0.8–2 TB free: the corpus plus up to 3 engine stores of about the same size (random and media data barely compress). | Throughput, RAM, overhead, catalog size, restore time |
| **B5-S1** Scan benchmark: 500k synthetic + 200k photos, 4 filesystems | A 500k-file tree plus 200k photo-shaped files; the scan reads metadata, not content | Tier M profile `scan-700k`: 500k general files plus 200k `template`-mode photos with real JPEG/HEIC headers, sizes from the Open Images prior. Sparse content where the filesystem supports it (exFAT does not; use size-scaled mode there). | `PUB+SYN → results` | ext4/btrfs in CT; NTFS, APFS and exFAT on OL. Optional second pass over the owner's real home folder is `FAM → AGG` (timings and counts only). | Scan time vs BUD-SCAN, file count, filesystem, hardware |
| **F3-S1** Size fingerprinting | Public exact sizes; the owner library's sizes without exporting them | PUB: Open Images `OriginalSize` (≈3.35 GB CSV), GovDocs1 (sizes from zip listings), format-corpus. FAM: the script runs in the private store over the owner's library. | Public part `PUB → results`; owner part `FAM → AGG` | CT for public; homelab for the owner's part | Counts; % unique exact size before and after Padmé and 64 KiB buckets; storage overhead %; split by category. **Never the size list.** |
| **A7-S3** Format survey of the owner's library | A rehearsal set to validate the script and its output schema, then an aggregates-only run | Rehearsal: PUB format-corpus (incl. `pdfCabinetOfHorrors`, `jhove-errors`, `govdocs1-error-pdfs`), GovDocs1 `thread0`, exif-py `invalid/` | Rehearsal `PUB → results`; run `FAM → AGG` | CT (rehearsal); homelab (run) | Counts and bytes per format ID (PUID/MIME); % undecodable per format; at-risk formats as a list of **formats**, not files |
| **E4-S1** Golden set on ≥5 devices, ≥200 files per person | A labelling protocol that exports nothing identifying, plus a CT rehearsal with known answers | Rehearsal: Tier D `discovery-home` (labelled SYN home folders built from PUB files). Real run: local only (§8.2). | Rehearsal `PUB+SYN → results`; real `FAM → AGG` | CT (rehearsal); family devices (FM) | Per device and category: TP/FP/FN counts and bytes; recall and junk share. No labels, no names. |

## 6. Corpus tiers

| Tier | Size | Contents | Lives | Used by |
|---|---|---|---|---|
| **S** (small, CI-safe) | Target ≤ 0.5 GB fetched (a selection, not whole repos), plus ≤ 100 MB generated | Selected public media edge cases (EXIF variants, orientation 1–8, GPS, HEIC, AVIF, JXL, RAW, Motion Photos, Ultra HDR, broken files), size ladder, `ci-tiny` tree, filename torture set | Container, CI cache; fetched by manifest | Unit and format tests, A1-S1, A5 parser work, G2-S3 fuzz seeds |
| **M** (many files) | 1–5M files, mostly sparse or small | Generator profiles `m-1m`, `m-5m`, `scan-700k` | Container or OL machine; regenerated, never stored | H3-S1, B5-S1/S2, A1-S2 (1M-entry cache), G2 scale tests |
| **L** (large bytes) | 200–500 GB (default 300 GB) | Proposed default mix: about 100 GB GovDocs1 (about 300 of its 1,000 zips, which total 333.5 GB), about 100 GB Open Images originals (about 45k photos at the 2.24 MB mean measured in `corpus/README.md`), all Tier S media, about 80 GB SYN (videos above 4 GiB, media-shaped files, 10–20 % cross-"device" duplicates until the census sets the rate) | Homelab `research/corpus-public` (can be re-fetched) | A6-S2, A7-S2 (audit timing), A8 restore timing, A9 import rehearsal |
| **D** (discovery) | ~20k files per synthetic home folder | Labelled synthetic home folders: camera originals (PUB), downloads and memes (PUB images with no camera EXIF), screenshots (SYN PNG), scans (GovDocs PDF and TIFF), caches (`CACHEDIR.TAG` trees), app folders shaped like WhatsApp and Downloads | Generated; labels committed (they are synthetic) | E4-S1 rehearsal, E4-S2, B5 rules file |
| **G** (golden media) | ~40 items (A5-S1) | PUB composites where they exist; LAB for the rest (§8.1) | Manifest in repo; LAB files in the private store | A5-S1/S2, A8-S1 |

## 7. Synthetic corpus generator spec (G2 implements it)

### 7.1 Principles
- **Deterministic:** the same (profile, seed, generator version) gives a byte-identical tree and an identical manifest hash on the same filesystem type.
- **Honest about the filesystem:** some entries cannot be stored on some filesystems (case-only duplicates on case-insensitive volumes, invalid UTF-8 on NTFS, sparse files on exFAT). The generator records what the target filesystem **actually** stored and never fails silently.
- **No real data:** the only non-generated inputs are PUB seed files named in the manifest.

### 7.2 Profile (YAML) parameters
File count; directory shape (depth distribution, fan-out, a few directories with 100k entries); category mix; per-category size histogram (§7.6 format); duplicate rates (within a tree, across "device" trees) and near-duplicate rate (same prefix, different tail, to exercise chunking engines); timestamp distributions; edge-case quotas (§7.4); content mode per category; target filesystem.

### 7.3 Content modes
| Mode | What it writes | Use |
|---|---|---|
| `random` | ChaCha20 keystream from (seed, file index): incompressible and unique | Hashing, encryption and transfer throughput |
| `sparse` | Correct size with no data blocks | Metadata walks at 1–5M files |
| `size-scaled` | Same count and tree, sizes divided by a stated factor | Filesystems without sparse files (exFAT) |
| `template` | A real header from a PUB seed file of that type, then random payload | Magic-byte detection and discovery rules; not decodable |
| `real` | A byte-exact copy of a PUB file | Decoding, EXIF and grouping tests |
| `mutated` | `real` with truncation or bit flips at recorded offsets | Corruption detection (A7-S1), `hostile` tag |

### 7.4 Edge cases (each with a quota and a manifest tag)
| Area | Cases |
|---|---|
| Names | NFC/NFD pairs of the same name; emoji and ZWJ sequences; combining marks; RTL and bidi control characters; zero-width characters; names from the Big List of Naughty Strings; leading or trailing spaces and dots; Windows reserved names (`CON`, `NUL`, `COM1`, `AUX`); characters invalid on Windows (`: * ? " < > |`); invalid UTF-8 bytes (Linux); unpaired UTF-16 surrogates (Windows); components of 255 bytes; paths over 260 characters; case-only differences; very deep nesting |
| Sizes | 0 B; exactly 4 GiB − 1, 4 GiB and 4 GiB + 1 (the FAT32 limit); sizes at 5 MiB ± 1 and at the chosen multipart part size ± 1; videos over 4 GiB |
| Times | FAT's 2 s granularity; before 1980 (FAT cannot store it); after 2038; in the future; identical mtimes with different content (racy mtime); btime later than mtime |
| File types | Symlinks (including loops); hardlinks; unreadable files; sparse files; xattrs and NTFS alternate data streams; hidden and system attributes; `CACHEDIR.TAG`, `.nomedia`, `Thumbs.db`, `.DS_Store`; wrong extensions (a JPEG named `.png`); files with no extension |
| Media groups | RAW+JPEG pairs by basename; XMP sidecars; `.AAE` files; Motion Photos (PUB `real`). Live Photo pairs cannot be synthesised faithfully and come from Tier G. |
| Placeholders | A placeholder entry is a descriptor only. OS kits turn it into a real one: on Windows the MIT-licensed CloudMirror sample creates a cfapi sync root without a cloud account; on macOS, Apple's File Provider sample; B5-S3 uses real test accounts. |
| Videos | Valid MP4 and MOV over 4 GiB, made by concatenating a short synthetic ffmpeg `lavfi` test clip with stream copy (no licence issue, and much faster than encoding the whole length) |

### 7.5 Outputs and profiles
- **Outputs:** the tree; `manifest.jsonl` (path as raw bytes in base64 plus a display form, size, SHA-256, category, content mode, edge-case tags, expected discovery label, source PUB ID); `summary.json` (requested vs achieved per cell, unrepresentable entries, run time, filesystem, hardware).
- **Profiles:** `ci-tiny` (~1k files, < 100 MB); `m-1m` and `m-5m` (H3-S1, B5-S2); `scan-700k` (B5-S1); `seed-phone` (camera-roll-shaped set to push to test phones); `l-homelab` (Tier L filler); `discovery-home` (Tier D).

### 7.6 Census → generator interface (agreed with E1)
The E1 census exports, per device class, one CSV that the generator reads directly: `category, ext_group, log2_bin, count, bytes`. Here `log2_bin = k` means sizes in [2^k, 2^(k+1)) bytes; zero-byte files have their own bin. Cells follow §4 (for example "<5"). Until the census lands, the placeholders are the Open Images photo-size distribution and GovDocs1 for documents. Both are biased: Flickr JPEGs from 2018 and earlier, and US-government documents. They are placeholders, not estimates of the family's data.

### 7.7 H3-S1 pass criteria (tightening the plan's wording)
`m-1m` finishes in under 1 h in the container, and:
- every (category, bin) cell is within ±2 % or ±10 files of its target, whichever is larger;
- total bytes are within ±1 %;
- every edge-case quota is met or recorded as unrepresentable;
- two runs with the same seed give the same manifest hash.

**Status:** not run. The generator does not exist yet (G2).

## 8. Golden sets

### 8.1 A5-S1 golden media corpus: where each item comes from
A5 owns the spec. H3 sets storage and consent: PUB items are in the manifest, LAB items are in the private store, and nothing shows a person.

| A5-S1 item | Public candidate (see `corpus/README.md`) | Otherwise |
|---|---|---|
| Pixel Motion Photo | immich `pixel-6-pro.jpg`, `pixel-8a.jpg` | LAB on a test Pixel |
| Samsung motion photo | immich `samsung-one-ui-5.jpg`, `-6.jpg`, `-6.heic` | LAB |
| Ultra HDR / ISO 21496-1 gain map | libultrahdr `tests/data` (CC BY 4.0, plus one Apache-2.0 OR MIT file) | LAB |
| RAW+JPEG+XMP | immich and metadata-extractor RAWs and XMP sidecars; the pairing is synthetic | LAB for a true same-capture pair |
| Live Photo original + edit, burst, portrait, ProRAW, spatial video | None with a verified licence. metadata-extractor has only the video half of one Live Photo. | **LAB on an iPhone**; depends on OD-01 |
| 20-min 4K60 HEVC; ProRes | None suitable | LAB (phone) for realistic metadata; SYN (ffmpeg) for size and container tests only |
| WhatsApp-received media; Windows auto-converted imports | None | LAB: send test images between two test phones; import from a test iPhone on Windows |

### 8.2 E4-S1 labelling protocol (data handling)
1. The labelling tool runs on the person's device, offline. It samples ≥200 files locally and shows each file only to that person. The owner does not look unless invited; E1 decides whether a neutral facilitator is used (E1-S3).
2. The person may skip any file with "private: don't label", which is recorded as a count only. Skipping never reveals the file.
3. The tool compares the labels with the discovery prototype's proposals and shows the result table (R6). Only that table is exported: per category, counts and bytes of true positives, false positives and false negatives.
4. The labels, the sample list and the filenames are deleted on the device when the session ends. Nothing is kept in the private store.
5. Rehearse the whole flow first on Tier D in CT, where the right answers are known.

## 9. Consent script (draft; E1 adapts it for interviews)

Read aloud or hand over. Plain words, one page. For minors: a parent or guardian consents, and the child is also asked in words they understand; a "no" from the child is respected.

> **Helping test the family backup project**
>
> [Owner] is building a system to keep the family's photos and important files safe at home. Before building it, [Owner] needs some facts about how our devices are used. Taking part is up to you. Saying no changes nothing: your devices can still be backed up later.
>
> **What we would do:** run a small program on your phone or computer that **counts** files by type and size, for example "4,200 photos, 38 GB". Later, we may ask you to sort about 200 of your files into kinds ("important", "junk"). You do that yourself, on your own device.
>
> **What never leaves your device:** your photos and files, their names, where they were taken, and anything you mark private. Nobody else sees the files you sort.
>
> **What does leave:** only the totals. The program shows you exactly what it will save before it saves it, and you can say no at that point.
>
> **Who sees the totals:** [Owner], and the research notes for the project, where you appear as "P3", not by name. Some of this work is done with AI tools. They only ever see totals, never your files.
>
> **How long we keep things:** the raw count file is deleted within 90 days. The totals become part of the project notes and are kept.
>
> **Changing your mind:** tell [Owner] at any time. Anything not yet written into the notes is deleted. Totals already in the notes cannot point to your files.
>
> Do you agree to take part? ☐ Yes ☐ No  Name: ______ Date: ______ (For a child: parent or guardian ______; child agreed ☐)

## 10. Guards to add (proposals; G1 owns the repo, H1 owns templates, and neither is done here)

- `.gitignore`: `corpus-cache/`, `private/`, `*.fam.*`, and the generator's output directory.
- A pre-commit hook and CI check that:
  - run gitleaks for secrets;
  - reject any binary over 1 MB outside an allowlist;
  - reject media files not listed in a PUB manifest;
  - run ExifTool on every committed image or video and fail on GPS tags unless the file is a listed PUB fixture.
- Kit template, "Data handling" section: replace the interim text with a link to §2–§4 here, and add a "what to send back" box that lists allowed fields only.
- Research-note template: the "Data class" column uses the `in → out` form from §2.

## 11. Gaps, open questions and owner actions

**Gaps**
- No public Live Photo pair, ProRAW, burst, portrait or spatial-video sample with a verified licence was found. These need LAB fixtures and an iPhone (OD-01).
- Some licences could be checked only through secondary sources, because the sites are blocked from the container: raw.pixls.us (CC0 preferred; older files CC BY-NC-SA), the Blender open movies (CC BY 3.0), and the Wikimedia Commons dumps. Fetch these on the homelab and check each file's licence there.
- The immich `test-assets` repo contradicts itself: its README says "public domain" and its `LICENSE` file is AGPL-3.0. It is treated as AGPL-3.0 and fetch-only.
- The generator, H3-S1 and every measurement are not yet run. The Open Images figure in `corpus/README.md` comes from a non-random slice and is indicative only.

**Owner actions**
1. Confirm the classes and rules (§2–§4), including R3 (exact sizes count as FAM) and the 90-day retention in R7. Filed as OD-21 in the decision queue (intake Q-J6); needed in Wave 0.
2. Confirm R9: no third-party binaries are committed until ADR-0036 (part of OD-21).
3. Create the homelab private research store (R7) and `research/corpus-public`, with about 0.8–2 TB free for A6-S2.
4. Let the homelab (not the container) fetch the blocked corpus hosts, or add them to the allowlist: raw.pixls.us, pixls.us, digitalcorpora.org, dumps.wikimedia.org, download.blender.org, media.xiph.org. They are now in `sources.md`. Routes that work from the container: `git clone` over HTTPS from github.com (a blobless clone is enough to read licences), `digitalcorpora.s3.amazonaws.com`, `s3.eu-north-1.amazonaws.com/napierone.com` and `storage.googleapis.com/openimages`.
5. Decide whether to shoot LAB fixtures, and on which devices (iPhone items depend on OD-01).
6. Set up test cloud accounts (OneDrive, Google Drive, Dropbox, iCloud) for B5-S3 and the placeholder fixtures. They must hold no family data.
7. With E1: approve the consent script (§9) and decide on a neutral facilitator.

**Hand-offs**

| To | What |
|---|---|
| G2 | Implement §7 and run H3-S1 |
| E1 | §7.6 census output format; R6 show-before-send; the consent script (§9) |
| E4 | §8.2 labelling protocol; Tier D rehearsal |
| A5 | §8.1 sourcing table |
| F3, A7, A6, B5, A1 | §5 rows |
| D6 | Add the research stores (private store, corpus store, kit results) to `docs/security/data-inventory.md` |
| H1 | Fix the file-name links; add the corpus hosts to `sources.md`; add owner actions 1–2 to the decision queue; update the templates per §10. Done in the Wave 0 check, except the kit template's "what to send back" box. |
| G1 | The §10 guards |

## Sources

Accessed 2026-09-29 from the research container. Licence evidence for each corpus is in `corpus/README.md`.

| # | Source | Primary? |
|---|---|---|
| S1 | `docs/research/PLAN.md` (H3, the six blocked spikes, Gate A, §5.4) | Yes (project) |
| S2 | ADR-0001 §2 (plain SHA-256 never leaves the device) | Yes (project) |
| S3 | `microsoft/Windows-classic-samples` @ main: `Samples/CloudMirror/README.md`, `LICENSE` (MIT) | Yes |
| S4 | developer.apple.com: "Synchronizing files using file provider extensions" (sample code page) | Yes |
| S5 | `minimaxir/big-list-of-naughty-strings` @ db33ec7: `LICENSE` (MIT) | Yes |
