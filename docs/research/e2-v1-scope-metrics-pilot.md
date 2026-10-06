# E2. v1 scope, success metrics, test plan, pilot and interim protection

- **Workstream:** E2 (see `docs/research/PLAN.md`, section "E2.")
- **Status:** Final for Wave 1. It has been through skeptic review (3 lenses) and synthesis. **Provisional: the owner intake (H2) is unanswered.** Everything here uses the intake's proposed defaults (`owner-intake.md` §K and Part 2). The final scope follows the census in Wave 2.
- **Date:** 2026-09-29 (last updated 2026-10-06, after skeptic review)
- **Feeds:** ADR-0004 (draft at `docs/adr/0004-v1-scope-platforms-non-goals.md`, Status: Proposed, provisional); OD-19 (decision request ready); OD-01 (E2 agrees with B4: keep iOS deferred and add a computer bridge); OD-13 (the answer to "browse and share"); OD-17 (if the stopgaps are declined); OD-18 (how the stopgaps interact with it); candidate budget IDs for H1 (§4.5). No one-way door.
- **Depends on:** H2 (intake, not answered), T1 (`client-stack.md`, option C), T2 (`fact-check-adr-0001-0002.md`), B4 (`b4-ios-decision.md`), F1 (`f1-build-adopt-fork-compose.md`), E1 (`e1-family-research-census.md`), A3 (`a3-ingest-protocol.md`, for the state names the metrics use), B3 (`b3-android-distribution-play-compliance.md`).
- **Traceability rows advanced:** R-03 (iOS; E2 agrees with B4), R-06 (non-technical users: metrics and test plan), R-33 (v1 sources: Android documents, OD-19), R-36 (v1 focus is getting data in: the scope slice). None is closed. They close when the owner accepts ADR-0004.

## Summary

**Scope.** v1 is the settled v1: Windows, macOS, Linux and Android; R2 and USB; admin-only restore; discovery, a plain-language health view and nudges. Within that, Android is **media only** (OD-19). iOS **stays deferred**, as CLAUDE.md already says, and iPhone photos are bridged through a family computer where one exists (B4 option B). LAN direct is deferred. Browse and share is a non-goal.

**Delivery.** F1 estimates the full v1 at **1,070–2,140 focused hours. At the provisional 8 h/week that is 2.6–5.1 years** (K11, a Low-confidence estimate, not a measurement). So the plan delivers in steps, and the family is protected well before the full v1:
- **D0, now:** stopgaps.
- **D1, about 12 months:** concierge. The owner seeds computers by USB with the admin CLI and sends each person a status report.
- **D2, about 24 months:** a minimal desktop app and a minimal Android media app, with basic discovery and nudges. Which app comes first is an owner decision (DR-E2-4).
- **D3, after 24 months:** the full settled v1 kit.

The stopgaps stay on for **years, not months**.

**"Safe".** For a single item, "stored at home" means a homelab receipt (A3). Receipts do not prove the pipeline can give data back (K9), so E2 puts the restore check at **enrollment**: no relative's device on a platform is enrolled, and no reassuring status is shown, until a restore drill on that platform has passed. Concierge data is treated the same way. The word "Protected" is E3's to define. E2 hands E3 four conditions for it: receipts, the restore gate, a full permission grant, and a grace window for new items.

**Metrics.** There are ten metrics (M1–M10), each with a source that fits the trust model and none using third-party analytics. E2-S2 passed as an **emulated design-consistency check**. It found that the false-safe check (M9) needs a digest, not an ID list, and that nudge emails may only state facts about device activity.

**Confidence.** Medium on scope and metrics. Low on timing. The intake answers most likely to change this note are Q-B9 (hours), Q-F2 and Q-F3 (device mix and iPhone share), Q-H2 (Android documents), Q-H3 (platform order) and Q-H4 (concierge).

## Questions

| # | Question (PLAN E2 key questions, plus new ones) | Short answer | Confidence |
|---|---|---|---|
| 1 | The thinnest slice that delivers "your keepsakes are safe at home and you can tell" | The settled v1 with the pruning in §2, delivered as D0 stopgaps → D1 concierge → D2 minimal apps → D3 full kit (§1). F1's estimate says the full v1 is 2.6–5.1 years away (K11), so a "minimal v1" with named deferrals is put to the owner as an option (DR-E2-1 D). | Medium on scope; Low on timing |
| 2 | Must a verified restore drill come before anything is called "safe"? | **Per item: no.** A verified homelab receipt is the bar for "stored at home" (A3). **Per platform: yes, as an enrollment gate.** No relative on a platform is enrolled or shown any reassuring status until that platform's restore drill has passed. Concierge imports need their own drill (§1.3). | Medium-high (K7, K9) |
| 3 | What to prune | Android documents: prune (OD-19, media only). macOS Photos library: keep, because it is the iPhone bridge. LAN direct: prune (ADR-0037). USB return trip: keep, because it is settled; the owner seeds first. iOS: stays deferred (settled), with a bridge. Discovery: photos, videos and documents. Nudges: in the app, OS notification and email. Wizard: keep. | Medium |
| 4 | Metrics with trust-model-fit data sources; no third-party analytics | M1–M10 (§3). E2-S2 found every one compliant in an emulated design check, with three conditions: M9 uses a digest, nudge emails state activity facts only, and M6 measures the fix rather than clicks. | Medium (K10; E2-S2 emulated) |
| 5 | Pilot order, stop and rollback, kill or pivot | Owner → helper → extreme user → everyone, mapped to the delivery steps in §4.1. Stop actions depend on the cause (§4.3). Rollback is a Worker-side suspension, and nothing is ever deleted. The gate values are proposals (K15). | Medium (method); thresholds proposed only |
| 6 | Interim protection: the lowest-effort stopgap per device type | One per device type, plus a fallback for when the account has no room: a cable copy at visits (§5.1; owner checklist in `spikes/E2-S3/`). | Medium (Google and Apple help pages blocked) |
| 7 | Which stopgaps damage a later import? | API-based Google Photos sync (K5, verified), icloudpd Sync and Move (K6, verified), and metadata "fixers" (E2-S3 measured that they change the file hash). Storage saver and Free up space are **contested** (K4) and treated as a precaution. §5.2. | High for K5, K6 and E2-S3; contested for K4 |
| 8 | How does stopgap data enter Reliquary (A9)? | Copies the owner made from devices go in through admin-side import, with provenance. Cloud exports (Takeout, icloudpd) need an owner decision first (DR-E2-5); until then they are held on the homelab outside Reliquary. Bytes are kept exactly as received. Byte identity with device originals is unknown (A9-S1). | Medium |
| 9 | The answer for relatives who want to browse and share | Not in v1. Later, perhaps an owner-run, LAN-only Immich over a read-only export (K13; OD-13). | High that it is a non-goal; Medium on the later route |
| 10 | Alternatives: desktop vs Android first; owner-only dogfooding; concierge MVP | Concierge is the first build step (D1). Owner dogfooding is stage P0 only. **Which of the two D2 apps comes first is an open owner decision (DR-E2-4).** Desktop first is the provisional default, but once concierge already covers computers it is no longer clearly better. | Medium |
| 11 | *(new)* OD-19: Android documents | **Media only in v1, as the cheapest default.** SAF cannot grant the Download folder itself or the storage root on Android 11+ (K1). Subfolders and Documents/ can be granted, but only through the system picker. All-files access is a settings toggle and goes through Play review (K2). Revisit after the E1 census and B3. | Medium-high on facts; Medium on the recommendation |
| 12 | *(new)* Which intake answers could change ADR-0004? | Appendix B. | High (list); Medium (effects) |

## Method

- **Sweep:** two scouts. The docs scout covered developer.android.com, developer.apple.com, Google and Apple help (as search snippets only), Immich and Ente docs (via raw GitHub) and method references. The source scout covered Immich and Ente mobile code, Syncthing usage reporting, Home Assistant analytics, gphotos-sync, icloudpd, immich-go and the restic docs. No issues/forums scout and no standards/papers scout ran for E2 in Wave 1.
- **Analyst re-reads (2026-09-29):** the three developer.android.com storage pages; Immich `backup.repository.dart` @ 9b57f13a, `mobile-backup.md`, `libraries.md`, `README.md` and `backup-and-restore.md`; Ente `backup-and-sync.md`; Syncthing `contract.go`, `security.rst` and `db-completion-get.rst`; the gphotos-sync README; the icloudpd README; immich-go `readme.md` and `best-practices.md`; restic `045_working_with_repos.rst`. Apple facts came from B4's re-reads.
- **Skeptic re-reads (2026-10-06):** all of the above were re-fetched by at least one skeptic. The Android pages now read "Last updated 2026-10-01 UTC", and the cited content is unchanged. Apple's background URLSession, TestFlight and "What's included" pages were re-fetched directly.
- **Routes used:** direct (developer.android.com, developer.apple.com), raw.githubusercontent.com mirrors, PyPI (icloudpd release date), WebSearch snippets (Google help; marked as such).
- **Blocked sources (all reported to H1; none silently replaced):**
  - support.google.com (Photos 6220791 and 6128843; Accounts 3024190; Play Console 10467955): EGRESS_BLOCKED for curl and WebFetch, re-tried 2026-10-06.
  - developers.google.com and developers.google.cn (Google Photos API updates): CONNECT 403.
  - support.apple.com (108782, 118257, 108306); privacy.apple.com; takeout.google.com; support.microsoft.com.
  - nngroup.com, research.google, static.googleusercontent.com (HEART PDF), dl.acm.org, measuringu.com, jpattonassociates.com (RITE), 9to5google.com, backblaze.com, Wikipedia.
  - The analyst's WebSearch budget ran out (200/200) on 2026-09-29.
- **Stop rule:** the analyst re-reads added one new primary source (the MediaStore page), and the skeptic re-reads added none that changed an answer. The method references (HEART, RITE, SUS, SEQ, Nielsen) are all blocked. They name methods only and never supply numbers.

## Sources

| # | Source | Publisher | Published or version date | Accessed | Primary? |
|---|---|---|---|---|---|
| S1 | Manage all files on a storage device — https://developer.android.com/training/data-storage/manage-all-files | Google (Android) | Last updated 2026-10-01 (was 2026-09-16 at first read; content unchanged) | 2026-09-29; re-read 2026-10-06 | Yes |
| S2 | Access documents and other files from shared storage — https://developer.android.com/training/data-storage/shared/documents-files | Google (Android) | Last updated 2026-10-01 | 2026-09-29; 2026-10-06 | Yes |
| S3 | Access media files from shared storage — https://developer.android.com/training/data-storage/shared/media | Google (Android) | Last updated 2026-10-01 | 2026-09-29; 2026-10-06 | Yes |
| S4 | Choose the backup quality of your photos & videos — https://support.google.com/photos/answer/6220791 | Google | Unknown | **Snippet only; blocked** (2026-09-29, 2026-10-06) | Primary, not read |
| S5 | Free up space on your device — https://support.google.com/photos/answer/6128843 | Google | Unknown | **Snippet only; blocked** | Primary, not read |
| S6 | How to download your Google data — https://support.google.com/accounts/answer/3024190 | Google | Unknown | Snippet only | Primary, not read |
| S7 | 9to5Google, "Google Photos now lets you schedule exports…" — https://9to5google.com/2026/06/01/google-photos-schedule-export/ | 9to5Google | 2026-06-01 (from URL) | Title and snippet only | No |
| S8 | Set up and use iCloud Photos — https://support.apple.com/en-us/108782 | Apple | Unknown | Snippet only | Primary, not read |
| S9 | Transfer a copy of your iCloud Photos to another service — https://support.apple.com/en-us/118257 | Apple | Unknown | Snippet only | Primary, not read |
| S10 | `URLSessionConfiguration.background(withIdentifier:)` — https://developer.apple.com/documentation/foundation/urlsessionconfiguration/background(withidentifier:); TestFlight overview — https://developer.apple.com/help/app-store-connect/test-a-beta-version/testflight-overview; "What's included" — https://developer.apple.com/programs/whats-included/ | Apple | Current pages | B4 re-read 2026-09-29; skeptic re-read 2026-10-06 | Yes |
| S11 | immich-app/immich @ 9b57f13a : `mobile/lib/infrastructure/repositories/backup.repository.dart` (byte-identical to main on 2026-10-06) | Immich | Commit 9b57f13a | 2026-09-29; 2026-10-06 | Yes (code) |
| S12 | immich-app/immich @ main : `docs/docs/features/mobile-backup.md` | Immich | main | 2026-09-29; 2026-10-06 | Yes |
| S13 | immich-app/immich @ main : `docs/docs/features/libraries.md` | Immich | main | 2026-09-29; 2026-10-06 | Yes |
| S14 | immich-app/immich @ main : `README.md`; `docs/docs/administration/backup-and-restore.md` | Immich | main | 2026-09-29; 2026-10-06 | Yes |
| S15 | Immich issues #21921, #22248, #968 (titles and metadata only) | Immich community | 2022–2025 | 2026-09-29 (scout) | Yes, bodies unread |
| S16 | ente-io/ente @ main : `docs/docs/photos/faq/backup-and-sync.md` | Ente | main | 2026-09-29; 2026-10-06 | Yes |
| S17 | ente-io/ente @ main : `mobile/apps/photos/lib/db/files_db.dart` | Ente | main | 2026-09-29 (scout) | Yes (code) |
| S18 | syncthing/syncthing @ main : `lib/ur/contract/contract.go` | Syncthing | main | 2026-09-29; 2026-10-06 | Yes (code) |
| S19 | syncthing/docs @ main : `users/security.rst`, `rest/db-completion-get.rst` | Syncthing | main | 2026-09-29; 2026-10-06 | Yes |
| S20 | home-assistant/core @ dev : `homeassistant/components/analytics/const.py` | Home Assistant | dev | 2026-09-29 (scout) | Yes (code) |
| S21 | gilesknap/gphotos-sync @ main : `README.rst` | G. Knap | Archived 2024-10-04 | 2026-09-29; 2026-10-06 | Yes |
| S22 | icloud-photos-downloader/icloud_photos_downloader @ master : `README.md`; PyPI `icloudpd` 1.32.3 (uploaded 2026-05-30) | icloudpd | master | 2026-09-29; 2026-10-06 | Yes |
| S23 | simulot/immich-go @ main : `docs/best-practices.md`; @ f7d19fce : `adapters/googlePhotos/googlephotos.go`, `matchers.go`, `json.go` | immich-go (third party) | main; f7d19fce | 2026-09-29; 2026-10-06 | Yes for immich-go's behaviour; **not** Google's Takeout documentation |
| S24 | restic/restic @ master : `doc/045_working_with_repos.rst` | restic | master | 2026-09-29; 2026-10-06 | Yes |
| S25 | Rodden, Hutchinson, Fu, "Measuring the User Experience on a Large Scale" (CHI 2010) — https://dl.acm.org/doi/10.1145/1753326.1753687 | ACM | 2010 | Blocked | Primary, not read |
| S26 | Brooke, SUS (1996); Medlock et al., RITE; Nielsen, "test with 5 users" | various | 1996–2005 | Blocked | Not read |
| S27 | Search snippets of Google's "Updates to the Google Photos APIs" (developers.google.com) | Google (via search) | Change dated 2025-03-31 in the snippet | 2026-10-06 (skeptic; snippet only) | Primary, not read |
| S28 | Local: CLAUDE.md (iOS line as of commit `6f9f2bb`); ADR-0001; ADR-0002; T1; T2; B3; B4; F1; E1; A3; H3; `budgets.md`; `owner-intake.md`; PLAN §2–§5 | Reliquary | 2026-09-29 to 2026-10-06 | 2026-10-06 | Project text |
| S29 | E2 spikes: `spikes/E2-S2/README.md`, `spikes/E2-S3/README.md`, `docs/research/kits/E2-S1/README.md` | Reliquary (this run) | 2026-09-29 | 2026-10-06 | Measured (emulated or synthetic) |

## Claims

The key claims and their verdicts are as computed from the three skeptics. **Verified** means a primary source and at least 2 of 3 skeptics did not refute. **Secondary only** means no primary source. **Contested** covers everything else. Skeptic 1 is the sources lens, Skeptic 2 the logic lens and Skeptic 3 the adversary/user lens.

| # | Claim | Sources | Skeptic 1 | Skeptic 2 | Skeptic 3 | Verdict |
|---|---|---|---|---|---|---|
| K1 | On Android 11+, `ACTION_OPEN_DOCUMENT_TREE` cannot grant the root of internal storage, the roots of reliable SD volumes, or **the Download directory itself**. It cannot select files in `Android/data/` or `Android/obb/`. A persisted grant survives restarts, but it is lost if the document is moved or deleted. | S2 | Upheld. Caveat: subfolders of Download and Documents/ are not barred. | Upheld. Same caveat: it weakens the case against SAF less than the draft implied. | Upheld (date refreshed) | **Verified** |
| K2 | `MANAGE_EXTERNAL_STORAGE` is enabled on a system settings page (`ACTION_MANAGE_ALL_FILES_ACCESS_PERMISSION`), not in a runtime dialog. Play has evaluated apps that declare it since May 2021. The use must be core functionality, and SAF or MediaStore must be insufficient. "Backup and restore apps" is listed as a **likely** permitted use. | S1 | Upheld. This is the developer guide's summary, not the Play policy page. | Upheld. "Likely" is not approval. | Upheld | **Verified** |
| K3 | Opening another app's file in `MediaStore.Downloads` needs SAF. Other apps' files are visible through MediaStore only in Images, Video and Audio. The docs point PDF and EPUB to `ACTION_OPEN_DOCUMENT`. | S3 | Upheld | Upheld (loose paraphrase; substance holds) | Upheld. It misses Android 14 partial media access (see §3). | **Verified** |
| K4 | Google Photos Storage saver compresses photos, resizes photos above 16 MP and videos above 1080p, and may convert formats. "Free up space" removes device copies of backed-up items. | S4, S5 (snippets) | **Refuted.** Primary pages blocked. A snippet also says "certain photos and videos may not be compressed". The format-conversion clause is unverified, and the Free up space clause is unseen. | **Refuted.** No primary read. | **Refuted.** No primary read; Free up space not seen even as a snippet. | **Contested** |
| K5 | gphotos-sync (archived 2024-10-04) says the Google Photos API cannot make a true backup: videos are transcoded, originals are converted to "High Quality", and GPS is removed. | S21 | Upheld. It adds the 2025-03-31 API scope change (S27, snippet). | Upheld | Upheld | **Verified** |
| K6 | icloudpd requires "Access iCloud Data on the Web" on and ADP off. Sync (`--auto-delete`) deletes local files and Move (`--keep-icloud-recent-days`) deletes from iCloud. The README asks for a maintainer. | S22 | Upheld. Latest release 1.32.3, 2026-05-30. Only Move touches the relative's iCloud data. | Upheld. It omits that the admin then holds the relative's Apple session. | Upheld. It adds a credential-custody risk. | **Verified** |
| K7 | Immich mobile counts an asset as backed up when a server asset with the same checksum exists for that user, over selected and not excluded albums. There is no verification or restore condition. | S11 | Upheld (the provider arithmetic was not re-read) | Upheld | Upheld. The join is against the client's local mirror, which is weaker still. | **Verified** |
| K8 | Immich and Ente document unreliable mobile background backup. Ente says "Background sync isn't currently consistent on iOS and on certain Android devices", recommends desktop for large first uploads, and its iOS Backup mode needs the app open on screen. | S12, S16 | Upheld | Upheld. It does **not** show that desktop-first protects camera rolls. | Upheld | **Verified** |
| K9 | restic `check` does not verify pack data without `--read-data`. `--read-data-subset` supports `n/t` slices or random subsets, and random subsets do not guarantee full coverage. | S24 | Upheld. Reading pack data is analogous to a restore drill but not the same thing. | Upheld | Upheld | **Verified** |
| K10 | Syncthing usage reporting is off by default, asked once and previewable. `ClearForVersion` zeroes fields with a newer or empty `since` tag. `/rest/db/completion` returns a completion percentage plus byte and item counts per device and folder. | S18, S19 | Upheld. The API returns one percentage plus counts; item weighting must be computed by the caller (wording corrected here). | Upheld | Upheld (same nit) | **Verified** |
| K11 | F1 estimates v1 at 1,070–2,140 focused hours. At 8 h/week, concierge seeding lands at about 12 months, a desktop tray app plus a minimal Android app at about 24 months **with basic discovery and nudges**, and the full v1 at 2.6–5.1 years. | S28 (F1 §4; analyst estimate, Low) | Upheld as a report of F1. The draft's use of it understated the timeline. | Upheld. Same point. | Upheld. Same point. | **Secondary only** (estimate) |
| K12 | A background `URLSession` survives app suspension and system termination, but a user force-quit cancels its transfers. The Apple Developer Program costs 99 USD/yr. TestFlight builds last 90 days, and the first external build goes to App Review. | S10 | Upheld (re-fetched) | Upheld. It supports a decision that is already settled. | Upheld (re-fetched) | **Verified** |
| K13 | An Immich external library belongs to one user. Without `:ro` Immich can delete the files. Metadata added in Immich is not written to the files. Immich says "Always follow 3-2-1". | S13, S14 | Upheld | Upheld. The "actual backup tool" sentence is about backing up Immich itself; the 3-2-1 line is the stronger support. | Upheld (same nuance) | **Verified** |
| K14 | **Per immich-go (third party)**: Takeout metadata lives in JSON sidecars with matching quirks (truncated names, renamed duplicates, localised "edited" suffixes, sidecars in other folders, and the newer `.supplemental-metadata.json` naming). Its best practice is ZIP, 50 GB parts, and checking every part. | S23 | Upheld, with caveats. It is not Google's documentation. The code truncates by runes, while the comment says UTF-16 units. The newer sidecar naming was missing from the draft. | Upheld (immich-go practice, not Google's) | Upheld (runes vs UTF-16 nit) | **Verified** as a statement about immich-go only |
| K15 | The pilot thresholds BUD-COVER, BUD-FALSESAFE and the stage durations are analyst proposals with no source. | This note §4.5 | Upheld. The values have measurability problems (fixed in §4). | Upheld (same) | Upheld (same) | **Secondary only** (proposal) |

**Non-key claims** (none of them is relied on alone):

| # | Claim | Sources | Verdict |
|---|---|---|---|
| N1 | iCloud "Optimize iPhone Storage" keeps full-resolution originals in iCloud and smaller versions on the device. | S8 (snippet) | Secondary only |
| N2 | Google Takeout scheduled exports run every 2 months for a year. Scheduled Google Photos exports are reportedly incremental after the first (about June 2026). | S6 (snippet), S7 | Secondary only |
| N3 | Immich has closed issues titled "Android: background sync works 0% of the time" (#21921) and "Hashes lost, stuck at 17k assets to reupload" (#22248). | S15 (titles only) | Illustrative only |
| N4 | Google removed the `photoslibrary.readonly` scope on 2025-03-31, so the Library API lists only media the app created. Full-library API sync tools are therefore unworkable. | S27 (snippet) | Secondary only. It supports K5 and is not used alone. |
| N5 | Apple's "transfer a copy" to another service takes 3–7 days, and some formats may not transfer. | S9 (snippet) | Secondary only |

## Findings

### 1. The v1 slice and the "safe" bar (Q1, Q2)

#### 1.1 What must be true

"Your keepsakes are safe at home, and you can tell" needs four things:
1. The bytes reach the homelab and are verified there, shown by a signed receipt (A3).
2. The person can see which of their keepsakes have that receipt (CLAUDE.md: plain-language health).
3. The owner can get any of them back (CLAUDE.md: restore is first-class).
4. Nothing is shown as safe that is not safe (PLAN §3; A3's gone-before-safe state). E2 names a breach of this a **false-safe**. The term is E2's, derived from A3's principle.

Similar work sets the bar at presence on the server. Immich counts an asset as backed up once the server holds the same checksum (K7, Verified). Ente marks a file uploaded once a server ID exists (S17). Receipts raise the per-item bar to "verified and committed at home". Receipts still do not show that the pipeline as a whole (keys, catalog, restore delivery) can give data back. restic draws a similar line: a structure check is not a read of the data (K9, Verified; an analogy, not the same thing).

#### 1.2 Where the restore check sits (revised after skeptic review)

The draft put the integrity bar on withholding the word "Protected" while allowing "stored at home". The adversary lens showed why that is weak: a non-technical relative will not tell "stored at home" from "safe". E2's own E2-S1 kit scores "all stored at home" as a correct answer to "are the photos safe?", and its onboarding screens say "Keep all of these safe". So the restore check is moved to **enrollment**:

- **Enrollment gate (E2 decides this, in ADR-0004).** No relative's device on a platform (Windows, macOS, Linux, Android) is enrolled, and no relative sees any reassuring status for data that took a given path, until that platform's restore drill has passed: Gate B's restore leg (A0-S3) plus one sampled drill on that platform (M7). The concierge path counts as a platform of its own (§1.3).
- **A platform the owner does not own.** Its drill runs on the P1 helper's device with the owner present. During the drill the health view shows a neutral "not yet checked" state.
- **Requirements handed to E3 for ADR-0024.** E2 does not decide the vocabulary. A person- or device-level reassuring word ("Protected" or whatever E3 picks) needs all of:
  - (a) receipts for all accepted keepsakes on the device, except items inside a **grace window** for new items (E3 sets the window; without one an active phone would never show it);
  - (b) the platform restore gate is open;
  - (c) the media or Photos permission grant is **full**, not partial or denied (§3, M2);
  - (d) whatever E3 decides about pool redundancy and scrub freshness.
- **E3-S1 should test whether relatives can tell "stored at home" from "Protected" at all.** If they cannot, the enrollment gate carries the whole weight, and the vocabulary can stay simple.

Evidence: K7 and K9 (Verified). The gate itself is a design choice, not a measured result.

#### 1.3 Delivery steps (revised: renamed D0–D3 to avoid a clash with metrics M1–M10; timeline restated against F1)

F1 (K11, secondary only, Low confidence) gives these figures at 8 h/week: about 6 months to the A0 skeleton, about 12 months to concierge seeding, about 24 months to a desktop tray app plus a minimal Android app with basic discovery and nudges, and **2.6–5.1 years to the full v1**. The ordering below does not rest on those numbers alone. It also follows from:
- the dependency order in PLAN §4.5: ingest, the admin CLI and restore come before any app;
- the settled requirement that USB seeding exists for large libraries;
- K8 (Verified): mobile background upload is unreliable, and the advice is to do large first uploads from a desktop.

| Step | What the family gets | What must exist | F1 timing at 8 h/week (estimate) | Settled-text fit |
|---|---|---|---|---|
| **D0: stopgaps (this month)** | Phones' own cloud backups at the original setting; iCloud originals synced to a family computer where one exists; the owner copies computer keepsakes and only-copy media at visits with `stopgap_copy.py` | Nothing built (§5) | Now | Fits |
| **D1: concierge** | The owner seeds each computer's keepsakes by USB with the admin CLI at visits. Each person gets a **plain-language status report** generated only from receipts and the catalog. | A0 hardened; A4 bundle writer; admin CLI; A9 import of device copies; report generator | ~12 months | Fits. Relatives touch no configuration. Importing **cloud exports** needs DR-E2-5. |
| **D2: minimal apps** | (i) The first app, desktop or Android (DR-E2-4): upload, receipts, health view, basic discovery, basic nudges. (ii) Then the other app. The owner still seeds big libraries by USB. | B1/B2, B5, B6, B7, basic E3 and E4 | ~24 months for both | Fits as a step. If D2 is declared to be v1, that needs DR-E2-1 option D. |
| **D3: full v1 kit** | ADR-0002 in full: the kit, discovery proposals, the "other devices" wizard, the nudge ladder, the USB return trip in the app | E3, E4, E5 complete | After 24 months (total 1,070–2,140 h) | Fits ADR-0002 |
| **After the pilot** | iOS, if the owner reopens the deferral (OD-01); Android documents (OD-19 revisit) | B4, B3 | — | iOS needs a settled-text change |

**D1 is promoted from fallback to first step.** Intake Q-H4 frames concierge as a fallback in which "the app only finds files and reports status". E2 makes it the first step, with no app. That changes the intake default, so DR-E2-1 asks the owner explicitly.

**The D1 gate (new; it closes the skeptics' gap).** Relatives' real data enters only through the concierge path once all of these hold:
- Gate A is accepted. PLAN §2.0 requires it before the first real family ingest.
- Gate B has passed, including its restore leg.
- One restore drill of **concierge-imported** owner data has passed: USB bundle, then ingest, then admin restore, then a byte compare.
- Each relative has consented to owner-made copies (H3 §9; D6).

The status report is under the same rules as the apps. The report generator checks every line against the catalog before sending. Any line that claims more than the receipts show counts as an M9 false-safe and triggers the stop rule. Until the concierge drill passes, the report may say only what was copied, never that it is stored.

The report needs a delivery route. In D1 the owner hands it over or sends it himself, so it does not depend on OD-03.

### 2. What to prune (Q3, Q11)

| Candidate | Recommendation | Why | Touches settled text? | Evidence |
|---|---|---|---|---|
| **Documents on Android (OD-19)** | **Media only in v1, as the cheapest default.** Revisit after the E1 census and B3's dossier. | SAF cannot grant **Download itself** or the storage root on Android 11+ (K1). Subfolders of Download and Documents/ **can** be granted, but each grant needs the relative to use the system picker. Other apps' files in Downloads need SAF (K3). All-files access is a settings-page toggle and goes through Play review (K2). The claim that "documents usually land in Download" is an **inference with no data** until E1. Other routes (options D and E in the decision request) were not costed. | No | K1–K3 (Verified) |
| macOS Photos library | **Keep** | It is the iPhone bridge (B4 option B) | No | B4 |
| LAN direct | **Prune** (ADR-0037, P2) | ADR-0001 §5: proposed, not committed. USB covers seeding. | No | ADR-0001 §5 |
| USB return trip | **Keep.** The owner seeds first (D1), and relatives write sticks in D3. | Settled in ADR-0002 §1. Only the sequencing is a choice. | No, unless v1 ships without it (DR-E2-1 D) | ADR-0002 §1 |
| iOS | **Stays deferred**, which is the settled text, with a computer bridge (B4 option B) | CLAUDE.md since `6f9f2bb`: "iOS is deferred (revisit with the Apple Developer membership)". Matches ADR-0002 §4. Cost and fragility evidence: K12, K8. | **No** for B. Reopening (option A) would change settled text. | K12, K8; B4 |
| Discovery categories | Phones: camera roll. Desktops: photos, videos and documents in user folders. Cloud, email and messaging are roadmap. | Keeps E4's golden set small | No | CLAUDE.md |
| Nudge channels | In the app, OS notifications and email. Not in v1: widget, SMS, helper pushes. | Every channel is surface area to test (E3-S3) | No | ADR-0002 §2 |
| "Other devices" wizard | **Keep** (D3; basic in D2) | Settled in ADR-0002 §3. Bridge wording goes through E5 (§2.1). | No | ADR-0002 §3 |
| Browse and share | **Not in v1** (§6) | Non-goal; OD-13 | Possibly (OD-13) | K13 |
| End-user restore, admin dashboard | Not in v1 (settled). The D1 report is a generated document, not a dashboard. | CLAUDE.md | Only if the report becomes a web page (OD-13) | — |

#### 2.1 The iPhone bridge must not fail silently (new)

The bridge depends on several links holding at once:
- the family computer is on and signed in;
- iCloud sync is healthy;
- the Mac downloads originals and is not set to "Optimize";
- iCloud for Windows stores full files rather than placeholders. This is **unverified**; Microsoft and Apple pages were blocked.

Showing an iPhone as "covered" while any link has stalled is a false-safe that M9 cannot see. It would also silence the settled nudges about declared-but-unprotected devices (ADR-0002 §3). So, in line with B4's honesty rule:
- The wizard and health view never say "covered". They say "photos synced to <computer> are stored at home; the iPhone itself is not checked; newest photo: <date>". The wording is E3's; the rule is E2's requirement.
- Optimized libraries and placeholders on the bridge computer count as cloud-only (M2).
- Nudges continue when the newest bridged photo is older than the iPhone's last known activity.
- ADR-0002 §3 says iPhones are recorded as "not yet supported". Adding bridge text there is a change to Accepted wizard behaviour, so it goes to E5 (ADR-0038) as a proposal, or to the owner as an amendment request. ADR-0004 does not decide it.

### 3. Success metrics that fit the trust model (Q4)

**Rules.**
- No third-party analytics.
- No plaintext file names, paths, hashes or **content-derived counts** in the cloud.
- The cloud may use only what ADR-0001/0002 accept: name, email, per-device activity timestamps, opaque IDs and commit state, and **nudge text built from activity facts only**. E2-S2 found that an email saying "1,203 photos not protected" would put content-derived data in cloud plaintext and at the email provider.
- Everything else is computed at the homelab, from the catalog and receipts or from device reports encrypted to the homelab and padded to a fixed size (E2-S2).
- New fields need fresh consent, following Syncthing's `ClearForVersion` pattern (K10). D6 decides which fields are operational and which are opt-in.
- Metrics are for the owner. They are never shown to relatives as scores.

| ID | Metric | Definition | Data source (trust-model fit) | Target / budget | Notes |
|---|---|---|---|---|---|
| M1 | **Time to first item stored at home** (renamed: it measures a receipt, not "Protected") | Enrollment complete → first verified receipt on that device | Enrollment time: Worker activity timestamp (accepted plaintext). First receipt: the device's encrypted report. | Related to BUD-TTS | Per device |
| M2 | Coverage at 7 and 30 days | Bytes and items with a verified receipt ÷ bytes and items discovered and accepted. Item weighting is computed from counts (K10). | Device counters, encrypted. **Buckets kept in the denominator:** in flight; cloud-only (placeholders, optimized libraries); gone-before-safe. **A grant-scope flag** (full, partial or denied for media/Photos/Desktop-Documents) is reported separately, because under a partial grant the app cannot count what it cannot see. | Candidate BUD-COVER (§4.5) | Two figures, with and without cloud-only (E2-S2). A device with a partial or denied grant fails the gate whatever its percentage. |
| M3 | Surprise gaps found in an audit | Keepsake locations found in an audit that discovery did not propose | Visit or remote audit counts (H3 `FAM → AGG`) | E4 sets it | Also the only check for gaps hidden by a shrunken denominator |
| M4 | Owner support minutes | Minutes per month on support and operations, by cause | The owner's log | BUD-SUPPORT | Development upkeep is a separate line (F1) |
| M5 | Unaided enrollment | Share of kit enrollments done without help, and the time from **installer launched to enrollment complete** | Lab: **E5-S3** (real install, including SmartScreen and Gatekeeper warnings) is the BUD-ENROLL evidence. Pilot: a client-side timer in the encrypted report, plus no M4 entry for that device. | BUD-ENROLL | E2-S1 prototype times are reported **separately and never pooled** (no install step). Redemption → first receipt is kept as a diagnostic only. |
| M6 | Nudge outcome | Share of actionable nudges followed by the fixing state change within 3 days; share snoozed or muted | Sent: device or Worker. Fix: a state change seen at the homelab. Mute: device counter. **No click tracking.** | E3-S2's rule | Measures the fix, not the click (E2-S2) |
| M7 | Restore-drill success and time | Share of sampled drills where every file restores byte-identical, plus owner time | Admin tool log. Verification **on the target device** needs A8's device-side restore path. Until then, the byte compare is done at the homelab by the owner. | BUD-RESTORE | Rotating slices rather than random samples (K9) |
| M8 | SUS and SEQ | Questionnaires after tasks | Paper, sessions only; never in the app | E2-S1 pass rule | The wording in the E2-S1 kit was reproduced from memory (sources blocked) and must be checked before printing |
| M9 | False-safe count | Items or devices shown as stored or reassuring without a receipt, or with the restore gate closed, or a D1 report line that claims more than the catalog | The device sends a **40-byte digest** of the items it shows as stored, up to a **receipt-batch cursor**. The homelab compares it with its ledger (E2-S2). D1 reports are checked against the catalog. | Must be 0 (candidate BUD-FALSESAFE) | Counts **detected** false-safes only. It cannot see gaps hidden by a partial grant (M2 flag) or a stale bridge (§2.1). |
| M10 | Gone-before-safe count | Items that vanished before commit (A3 side state) | Device, encrypted; an admin alert per A3 | Report every one | Any case caused by a Reliquary bug is a stop condition |

**Android 14+ partial media access (new risk).** If a relative taps "Select photos" in the media permission dialog, the app sees only the chosen items. B3 C17 notes these grants expire or are revoked. The denominator shrinks silently, so coverage reads near 100 %. The mitigations: the grant-scope flag in M2, no reassuring status under a partial grant (§1.2 c), and helping the relative choose "Allow all" at the visit. Hand-offs: B2, B5, E3.

**Overlaps.** B8 owns the data dictionary. D6 owns consent. C7 owns alerts. A3 and B8 must define the receipt-batch cursor that M9 depends on.

### 4. Pilot plan (Q5)

#### 4.1 How the delivery steps map to pilot stages and gates (new)

| Step | Pilot stage | Entry gate | Exit gate (all must hold) | Strongest status wording allowed | Min. duration (proposal) |
|---|---|---|---|---|---|
| D0 | — | None | — | None (no Reliquary status) | — |
| D1 | **P0-C** concierge on owner data, then relatives' computers | Gate A; Gate B including the restore leg; the concierge restore drill (§1.3); consent | M9 = 0 on reports; one more drill on a relative's imported data passes (M7); M4 within BUD-SUPPORT | Report lines from receipts and the catalog only. Nothing reassuring until the concierge drill passes. | 30 days |
| D2 (first app) | **P0** owner's devices | D1 drill passed; the app's platform drill passes on the owner's device (or the helper's device for platforms the owner lacks) | M9 = 0; BUD-TTS met; E3-S4 passes on real devices | Per E3, subject to §1.2 | 30 days |
| D2 | **P1** helper | P0 exit; Gate C readiness for the platforms in use; runbooks printed | M9 = 0; BUD-COVER at 30 days, or a USB-seeding plan; M4 within BUD-SUPPORT; the helper can explain the health view back | Same | **≥ 30 days** (aligned to the BUD-COVER window) |
| D2 (second app) | P0 then P1 for that platform | As above, for the second platform. For Android, B2's soak test must also have passed. | As above | Same | 30 days each |
| D2/D3 | **P2** extreme user(s) | P1 exit; P1 fixes shipped | As P1, plus M5 within BUD-ENROLL (E5-S3 basis) and M6 per E3-S2 | Same | 30 days |
| D3 | **P3** everyone, in batches of 2–3 | P2 exit; E2-S1 and E5-S3 passed | M4 within BUD-SUPPORT for 2 consecutive months | Same | — |

Throughout, **each relative's stopgaps stay on**. They retire only after P3 exit and E3's OD-18 decision.

#### 4.2 Gate values that cannot be measured yet

These are marked inactive rather than treated as passed:
- **BUD-CLOUD** and **BUD-ABUSE** have no value (`budgets.md`: "Owner sets (H2)"). The stop rules that cite them are **inactive until H2 sets values**. Until then, the only spend stop is C2's auto-suspend.
- **BUD-COVER** is not sized against any bandwidth data (Q-D1/D2/D5, C4). A device whose uplink cannot move its library in 30 days meets the gate through **USB seeding**, so the 30 days run from enrollment or first seeding, whichever is later. It never meets the gate by excluding data.

#### 4.3 Stop conditions and actions (revised: by cause)

The store is append-only and kept forever. Pausing uploads lowers protection, so uploads are paused only when the upload or ingest path itself is suspect.

| Condition | Action |
|---|---|
| 1. An M9 false-safe in a display, report or vocabulary | Halt new enrollment. Freeze reassuring wording: an app update or config flag, or regenerate the report. **Uploads continue.** |
| 2. An M10 gone-before-safe caused by a Reliquary bug | Halt enrollment. Pause uploads only if the bug is in the upload path. |
| 3. A failed restore drill (M7), or a receipt that fails verification | Halt enrollment. Pause uploads for the affected platform or path by **Worker-side suspension** (D3 revocation, BUD-REVOKE). Investigate before resuming. |
| 4. A key-custody incident (D2), or a suspected credential compromise | Revoke per D3. Act per D2's runbook. (The BUD-ABUSE trigger is inactive until set.) |
| 5. Cloud spend above BUD-CLOUD, or a C2 auto-suspend | Seed by USB only. (The BUD-CLOUD trigger is inactive until set.) |
| 6. Upload on a relative's metered or capped link beyond what they agreed (Q-D5) | Suspend that device's uploads; seed by USB |

Messages to relatives are drafted by E3 and E6. Each says plainly whether the relative needs to do anything (usually nothing).

#### 4.4 Rollback

- The **primary lever is the Worker**: stop issuing presigned URLs per device or globally (D3, BUD-REVOKE). No new device-side trust root is needed. A signed device-side pause is optional, and is referred to D3 and D5.
- Committed data stays committed. Keep-forever retention is settled, and rollback deletes nothing.
- Stopgaps were never turned off, so nobody ends up worse off than before.
- A format bug found after Gate A is fixed with a new format version and a migration (A2, A3), never a silent rewrite.

#### 4.5 Kill or pivot checkpoints and candidate budgets

| Checkpoint | Signal | Pivot |
|---|---|---|
| After D1 (concierge) | The owner cannot sustain visits and CLI seeding within BUD-SUPPORT plus the Q-B9 hours | Stopgaps plus a yearly concierge import; revisit scope |
| After P1 | Coverage at 30 days far below BUD-COVER because of mobile background limits (the K8 pattern) | Android "Back up now" while charging and on Wi-Fi; USB seeding as the main path |
| After P2 | M4 above 2 × BUD-SUPPORT for 2 months, or E2-S1 or E3-S1 fails after one RITE round | A health email only, or concierge for that persona |
| F1 checkpoint (12 months) | Build hours used above 2 × F1's estimate for what has shipped | ADR-0005 revisit: compose stopgaps indefinitely |

**Candidate budget IDs for H1.** These are analyst proposals with no source (K15, secondary only). The owner confirms the values.
- **BUD-COVER:** at 30 days after enrollment or first USB seeding (whichever is later), at least 95 % of discovered, locally available keepsake bytes have receipts, **and** the device has a full permission grant, **and** every byte in the cloud-only bucket is either zero or covered by a remediation plan the owner has recorded.
- **BUD-FALSESAFE:** 0 **detected** false-safe events (M9).
- **BUD-PILOT-DUR:** the minimum durations in §4.1 (30 days per stage).

#### 4.6 Pre-mortem: "it is two years from now and Reliquary failed"

| Failure story | Evidence it is plausible | Mitigation |
|---|---|---|
| The owner ran out of hours; half-built, nobody protected | F1: full v1 in 2.6–5.1 years at 8 h/week (K11, estimate) | D0 stopgaps now; D1 concierge; the minimal-v1 option (DR-E2-1 D) |
| Phone backups "never finish" | K8 (Verified); N3 (titles only) | USB seeding; "Back up now"; honest "catching up" states |
| A lost hash cache triggers a re-upload storm | N3 (title only) | Rebuildable cache (B6); dedup "already have it" (A3) |
| Something said "safe" and was not | K7 (presence ≠ safe) | Receipts; M9 = 0; the enrollment gate (§1.2); report checks (§1.3) |
| A partial permission grant hid most of a camera roll | B3 C17 | The grant-scope flag; no reassuring status under a partial grant |
| The iPhone bridge stalled silently | §2.1 (iCloud for Windows behaviour unverified) | Freshness wording; nudges continue |
| iPhones held most photos and stayed unprotected | E1-S2 pending; B4 | Bridge; a reopening request to the owner at ≥ 40 % (OD-01) |
| Relatives used "Free up space" or "Optimize", so originals left their devices | K4 (contested), N1 | Precautionary advice; the cloud-only bucket; Takeout fallback |
| Play rejected the app | K2; B3 | Media only (OD-19); B3 dossier |
| The owner burned out on support | PLAN §3 | M4 monthly; P2 checkpoint |
| Keys lost and backups unreadable | PLAN §3 | D2 recovery drill before Gate A |

### 5. Interim protection (Q6, Q7, Q8)

#### 5.1 One stopgap per device type (E2-S3; owner checklist at `spikes/E2-S3/owner-checklist.md`)

The stopgaps must hold for **1–5 years** for some devices (F1: about 12 months to concierge; 2.6–5.1 years to the full v1; K11, estimate), not 12–24 months as the draft said.

| Device type | Lowest-effort stopgap | Check together with the relative | If there is no room in the account | Avoid | Confidence |
|---|---|---|---|---|---|
| Android phone | Google Photos backup **on**, at the **original** quality setting | Confirm the setting names on the owner's own phone first; the Google pages were blocked. Free up space not used. | Either a paid plan (cost below), or the owner **copies DCIM by cable at visits** with `stopgap_copy.py` | Storage saver and Free up space (**precaution**; K4 is contested); API sync tools (K5, N4) | Medium for the advice; the setting wording is unverified |
| iPhone / iPad with a family computer | iCloud Photos on, plus originals downloaded to the Mac or PC (wording unverified) | The computer is set to download originals, not optimize | A paid iCloud plan, or a cable import at a visit (macOS Image Capture or Photos; Windows Photos). This gives originals only if Optimize is off on the phone (unverified; Apple pages blocked). | Shared Albums as backup (S16); icloudpd Sync or Move (K6) | Medium-low |
| iPhone with no computer | At a visit, a one-off owner copy: Apple's "transfer a copy" (N5), Apple's privacy data export (unverified), or icloudpd **Copy** mode, **only if ADP is already off**, done **with the relative present** | Warn the relative beforehand about Apple's new-sign-in alert. Delete icloudpd's saved session files afterwards. Record this under H3. | Cable import at a visit (as above) | Asking anyone to turn ADP off; icloudpd as a long-term dependency (K6) | Low-medium |
| Windows / macOS / Linux computer | The owner copies keepsake folders at visits with `stopgap_copy.py` (tested on Linux, E2-S3) onto a **write-once** share on the homelab or an external disk | Skip cloud placeholders; do not hydrate them. The Windows and macOS placeholder checks are untested. | — | Sync folders as backup (deletions propagate) | Medium |
| Google-Photos-only items | One Takeout as ZIP in 50 GB parts; check every part (K14, immich-go practice) | Keep the JSON sidecars | — | Mixing ZIP and TGZ | Medium |
| Only-copy items (old laptops, SD cards) | The owner copies them **this month**, first | — | — | — | High that this is the first priority |

**Cost (new).** At original quality, phone photos count against the Google or iCloud storage quota. Some relatives will need a paid Google One or iCloud+ plan, for years. Prices were not read here (support pages blocked), so no figure is given. **Who pays, and up to what tier, goes to the owner under Q-B1/B2** (DR-E2-2). Without room, backup stops and the relative sees "storage full" or upsell prompts. E6 should write a short script telling relatives what those prompts mean. Google Photos also suggests "Free up space" on its own, so treat a relative's promise not to tap it as a **monitored risk**, not a guarantee. Ask about it at each visit.

#### 5.2 Stopgaps that damage a later import

| Stopgap | Damage | Evidence | Status |
|---|---|---|---|
| Google Photos API sync tools (gphotos-sync and similar) | Transcoded video, converted originals, GPS removed; since 2025 the API cannot list the whole library | K5; N4 | Verified (K5); N4 secondary |
| icloudpd Sync or Move | Sync deletes local copies; Move deletes from iCloud | K6 | Verified |
| Writing Takeout metadata back into files ("fixers") | Changes the file hash, so whole-file dedup will not match the device original | E2-S3 measured: SHA-256 changed and the size went from 124 to 436 bytes, while exiftool's `ImageDataHash` stayed the same | Measured (synthetic) |
| Google Photos Storage saver | Resized and re-encoded copies, so there is no original for a later import | K4 | **Contested**. The advice stands as a low-cost precaution. |
| Free up space / Optimize Storage | Originals leave the device | K4, N1 | **Contested / secondary**. Treated as a precaution and handled by the cloud-only bucket. |
| iCloud Shared Albums as "the backup" | Compressed copies | S16 (Ente docs) | Secondary for Apple's behaviour |
| Messaging-app forwards | Recompressed copies | PLAN §3 (A5) | Project text |

#### 5.3 How stopgap data enters Reliquary (to A9)

- **Copies the owner made from devices** (`stopgap_copy.py`, cable copies) are files from the device. They enter through admin-side import at the homelab, with provenance "stopgap: <route>, <date>" in the history fields (H4).
- **Cloud exports** (Takeout, icloudpd, Apple transfers) bring cloud-service data into v1. CLAUDE.md puts "pulling from iCloud / Google Photos" on the roadmap, and B4 already flagged icloudpd. They need an owner decision first (**DR-E2-5**). Until then, the owner keeps them on the homelab as plain files outside Reliquary. They are still protected there, and nothing is lost.
- **Keep bytes exactly as received.** Store sidecars as linked metadata (K14; E2-S3 measurement).
- Dedup merges a stopgap copy with a later device upload only if the bytes are identical. Whether Takeout or icloudpd "originals" are byte-identical to device originals is **unknown**. A9-S1 measures it, along with the sidecar naming and truncation on a real Takeout sample. The immich-go "46 UTF-16 characters" note is not to be adopted as a spec (K14 caveat).
- Live Photos arrive from icloudpd as separate image and video files (K6). A5 groups them.

### 6. The answer on "browse and share" (Q9)

- **Script for relatives (draft for E6):** "Reliquary is the family's safe-deposit box, not its photo album. Keep sharing and browsing the way you do now. [Owner] can get any photo back for you."
- **Why it is a non-goal:** v1 is about getting data in, restore is admin-only, and any gallery falls under OD-13.
- **Later option:** an owner-run, LAN-only Immich over a read-only (`:ro`) export. Immich warns that without `:ro` it can delete files. An external library belongs to one user, and metadata added in Immich is not written back to the files. Its README says to follow 3-2-1 (K13, Verified). This needs a browsable export from A6.

## Alternatives compared

| Option | Fit with settled requirements | Pros | Cons | Evidence |
|---|---|---|---|---|
| **D0 → D1 concierge → D2 minimal apps → D3 kit (recommended, provisional)** | Fits. D1-first changes the intake H4 default. | Protection starts early; ingest, USB and restore are proven on real data before any app | Owner visit time; years before the full kit | K8, K11 (estimate); PLAN §4.5 |
| D2 desktop app first, then Android (provisional default within D2) | Fits ADR-0002; the kit and wizard start on the desktop | Best background story; the enrollment flow already exists in ADR-0002 | Computers are already covered by D1 snapshots; phones (the main keepsake source) wait | K8; F1 desktop 150–300 h (estimate) |
| D2 Android media app first, phones enrolled by the owner at visits | Phone enrollment by an owner-issued token must be checked against ADR-0002 §3 (E5/D3) | Covers the main keepsake source continuously, sooner | Background limits (K8); Play compliance on the critical path (B3); F1's largest item, 200–400 h (estimate) | K8; B3; F1 |
| D2 as a health-only desktop app, with the owner still seeding | Fits as a step | The thinnest app; matches F1's "basic" app | Relatives cannot add new files without the owner | Logic skeptic |
| Owner-administered restic or Kopia as a "compose stopgaps" D1 | Fails client-side encryption to the homelab key and cross-user dedup if it becomes the end state | Proven tools; no build | Not Reliquary's formats; migration later; a second system to run | F1 (named pivot); not compared in depth (A6/F1) |
| Owner-only dogfooding as the whole pilot | Fits | Cheapest | Does not test non-technical users (R-06) | PLAN E2 |
| Reopen iOS into v1 | **Changes settled text** (CLAUDE.md platforms and code signing; ADR-0002 §4/§5) | Covers iPhone-heavy families | 99 USD/yr; 90-day TestFlight; force-quit cancels uploads (K12) | K12; B4 |
| Stopgaps only | Fails the settled goals | No build cost | No homelab copy, no health view | F1 |

### Similar work and lessons

| Project or paper | What they do | Borrow or avoid | Source |
|---|---|---|---|
| Immich mobile backup counts | "Backed up" means the server has the same checksum | Avoid: presence ≠ safe. Borrow the separate "processing" bucket. | K7 |
| Ente backup status and FAQ | Recommends desktop for big first uploads | Borrow desktop or USB seeding for large libraries | K8 |
| Syncthing usage reports and completion API | Opt-in, previewable, versioned consent; byte and item counts | Borrow both | K10 |
| restic check | A structure check vs reading the data; rotating subsets | Borrow rotating slices for M7 | K9 |
| gphotos-sync | Google Photos API backup; archived | Avoid as a stopgap | K5 |
| icloudpd | iCloud download | Copy mode only, occasional, with the relative present | K6 |
| immich-go | Takeout import | Study its matchers for A9; licence unchecked (G3) | K14 |
| HEART, RITE, SUS/SEQ, Nielsen | Methods | Method names only; primary sources blocked | S25, S26 |

### Tools and libraries

| Name | Purpose | Licence | Maturity | Source |
|---|---|---|---|---|
| `stopgap_copy.py` (this run) | Verified visit copies with a manifest; never deletes | Project code (throwaway) | Tested on synthetic data, Linux only | `spikes/E2-S3/` |
| icloudpd | Owner-run iCloud copy (Copy mode) | Not checked | 1.32.3 (2026-05-30); maintainer wanted | K6 |
| immich-go | Reference for Takeout import | Not checked | Active | K14 |
| exiftool 12.76 | Used in E2-S3 to measure the effect of metadata write-back | — | — | E2-S3 |

## Consolidated family test plan (skeleton; the full plan is a Wave 2 deliverable)

- **One visit per relative**, in E1's running order (`kits/E1-S1/visit-plan.md`). The interview and census come first.
- **E2 and E5 block, revised to match the E2-S1 kit:**
  1. E2-S1 and E3-S1 are **counterbalanced**. P1, P3 and P5 do E2-S1 first; P2 and P4 do E3-S1 first. Results are reported by order. If the E2-S1 pass depends on the E3-first participants, the result is "Fail (primed)".
  2. E5-S1, S3 and S4 (QR, code typing, real kit install). E5-S3 is the BUD-ENROLL evidence.
  3. D6-S3 and E7-S1 questions last.
- **Changes needed in the E2-S1 kit before it runs** (Wave 2, E2 spike runner):
  - The onboarding and wizard screens use "safe" ("Keep all of these safe" and similar), although the health view deliberately avoids the word. Use E3's wording, or neutral wording.
  - Q3's rubric counts "all stored at home" as a correct answer to "are the photos safe?". Align it with E3-S1's test of whether relatives can tell the two apart.
  - Check the SEQ and SUS wording against a primary source before printing.
- **Visit length is unmeasured.** E1 estimates about 90 minutes before this block. Split the visit for older relatives.
- **Longitudinal tests** (E3-S2, E5-S6) run separately and do not overlap pilot weeks for the same participants (a proposal).

## Spikes

| Spike | Hypothesis | Pass → / fail → (decision) | Exec tag | Budget IDs | Data class | Status | Result |
|---|---|---|---|---|---|---|---|
| E2-S1 Clickable enroll + health prototype, 5 relatives | ≥ 4 of 5 relatives get from "Get started" to the health view with no assist **and** answer all three judgement questions correctly | Pass → the D2/D3 first-run and health scope stands; tested wording goes to E3 and E5. Fail → RITE and retest; a second failure triggers the "After P2" pivot. n < 5 → no result. | FM | BUD-ENROLL (indication only; E5-S3 is the real measure) | `SYN → FAM → AGG` | **Kit-ready** | Kit: [`kits/E2-S1/README.md`](kits/E2-S1/README.md), `prototype/index.html`, `session-sheet.md`. Not run (no family access). The prototype flow was smoke-tested in jsdom. Counterbalanced with E3-S1. Needs the copy fixes listed above before it runs. |
| E2-S2 Metric feasibility | Every kept metric M1–M10 has a data source that fits the trust model | Pass → the metrics spec stands, with conditions. Fail → drop or redesign the metric. | CT | BUD-TEL | `SYN → results` | **Pass: design consistency only, emulated** (not real R2/Cloudflare; the rules, model, simulator and faults were all written by the same analyst) | [`spikes/E2-S2/README.md`](../../spikes/E2-S2/README.md). All M1–M10 compliant; 5/5 negative controls flagged. 25 devices × 30 days, 708 age-encrypted reports. 0 leak hits in 1,717,380 cloud bytes (positive control 16/16). One ciphertext size (2,248 B). M9 caught the injected false-safe (dev-07, day 10, 3 items) with no false alarms. M10 found 2/2. Consent versioning works. BUD-TEL: 2,248 B/day at daily reports and 53,952 B/day at hourly reports, both within; a 30-day outbox is 67,440 B. An ID list for 100k items (1.6–3.5 MB) would exceed the budget, hence the digest. Not tested: the real Worker, D1, R2, email, the B8 relay, real clocks. Re-run against the A0 harness. |
| E2-S3 Interim-protection recommendation | One actionable stopgap per device type the owner can apply this month | Pass → owner checklist. Fail → concierge copy for that type. | CT | BUD-SUPPORT (owner time not measured) | `PUB → results`; `SYN → results` for the tool | **Pass, with a caveat on wording** | [`spikes/E2-S3/README.md`](../../spikes/E2-S3/README.md), `owner-checklist.md`. `stopgap_copy.py`: 6/6 hashes and mtimes kept; idempotent rerun; edits keep both copies; verify caught a 1-bit flip; a file changed during the copy is flagged; 99.0 MB/s on the container disk (not representative). Windows and macOS placeholder checks untested. Writing EXIF back changed the file hash while `ImageDataHash` stayed the same. Google and Apple setting names are unverified (pages blocked); the owner confirms them on a device. The checklist still needs the new "no room", cost and icloudpd-custody rows from §5.1 (Wave 2). |

## Conflicts with settled text

1. **OD-01's premise is stale (corrected).** CLAUDE.md has said "Platforms (v1): Windows, macOS, Linux, Android. **iOS is deferred** (revisit with the Apple Developer membership)" since commit `6f9f2bb`. That matches ADR-0002 §4. The draft of this note, PLAN §4.3 and the OD-01 row in `decision-queue.md` describe a CLAUDE.md-vs-ADR-0002 conflict that no longer exists. B4 found the same thing. Options B (deferred, with a bridge) and C (deferred, no bridge) match settled text. **Option A, iOS in v1, would reopen** the "Platforms" and "Code signing" lines. A ≥ 40 % iPhone share is therefore a trigger to **ask the owner**, never an automatic rule. Reported to H1 and B4; not edited here.
2. **Cloud exports in v1 (new).** Importing Takeout or icloudpd copies brings cloud-service data into v1, while CLAUDE.md says "files on the device only" and puts iCloud and Google Photos on the roadmap. Raised as DR-E2-5.
3. **iPhone bridge wording in the wizard (new).** ADR-0002 §3 records iPhones as "not yet supported". Bridge text with a freshness date (§2.1) would change Accepted wizard behaviour. That is for E5 (ADR-0038) or an amendment request; ADR-0004 does not decide it.
4. **USB return trip.** No conflict while v1 (D3) ships it. Leaving it out of v1 (DR-E2-1 D) would amend ADR-0002 §1.
5. **D1 status report vs "no admin dashboard" (OD-13).** A generated document is not a dashboard. If it becomes a web page, OD-13 applies.
6. **Browse and share (a later Immich)** falls under OD-13.
7. **PLAN §2.0 Gate A before family ingest:** now honoured by the D1 gate (§1.3).
8. **Ownership (PLAN §2.1).** The status vocabulary is E3's (ADR-0024). ADR-0004 states only the enrollment gate, plus requirements for E3. Rollback mechanics go to D3 and D5, and drill sampling is shared with A8 and C8.

Media-only Android (OD-19) is a subset of "files on the device" and needs no settled-text change.

## Open questions

| Question | Who answers | By when |
|---|---|---|
| All intake answers in Appendix B (Q-B9, Q-F2, Q-F3, Q-H2, Q-H3 and Q-H4 matter most) | Owner (H2) | Wave 0 / decision sitting 2 |
| iPhone share of camera-roll bytes | E1-S2a | Wave 1 exit |
| What documents Android phones hold, and where | E1 visits (the census covers desktops only) | Wave 2 |
| Play review for all-files access in a backup app; Photo & Video declaration | B3 | Before OD-19 is revisited |
| Do iCloud for Windows and macOS Photos keep full originals or placeholders on a bridge computer? | B4, B5 (OL kit) | Wave 2 |
| Are Takeout and icloudpd "originals" byte-identical to device originals? Real sidecar naming and truncation | A9-S1 | Wave 2 |
| Exact Google Photos and iCloud setting wording; stopgap storage costs | Owner on a device; H1 allowlist; Q-B1/B2 | Before the checklist is handed over |
| The receipt-batch cursor that M9 relies on | A3, B8 | Wave 2 |
| Device-side restore verification for M7 | A8 | Wave 2 |
| Bandwidth sizing for BUD-COVER | C4, intake Q-D | Wave 2 |
| Values for BUD-COVER, BUD-FALSESAFE, BUD-PILOT-DUR, BUD-CLOUD, BUD-ABUSE | Owner via H1/H2 | Wave 2 |
| Visit length including this block | E1 dry run | Wave 2 |

## Recommendation

Adopt **ADR-0004 (Proposed, provisional)**:
- **Platforms:** Windows, macOS, Linux, Android. **iOS stays deferred, as already settled**, with a computer bridge that never claims more than it can see (OD-01 option B).
- **Android:** media only (OD-19 A), as the cheapest default.
- **LAN direct:** deferred.
- **Delivery:** D0 stopgaps now → D1 concierge (gated on Gate A, Gate B and a concierge restore drill) → D2 minimal apps (order per DR-E2-4) → D3 full kit.
- **Enrollment gate:** no relative on a platform is enrolled or shown reassurance until that platform's restore drill has passed.
- **Pilot:** P0-C/P0 → P1 → P2 → P3, with stop actions by cause and rollback through the Worker.
- **Metrics:** M1–M10, with no third-party analytics, a digest-based false-safe check and activity-only email text.
- **Stopgaps:** on now, for **years**, with their costs decided by the owner.

The recommendation does not rest on any contested claim. The stopgap advice about Storage saver and Free up space (K4, contested) is kept only as a low-cost precaution beside K5 (Verified) and the E2-S3 measurement. The timing (K11) and gate values (K15) are labelled as estimates and proposals.

**What would change it:**
- iPhone share ≥ 40 %, or Q-H1 "in v1": ask the owner whether to reopen the iOS deferral (a settled-text change).
- Owner hours much higher than 8 h/week: D1 could be shortened or skipped. Much lower: D1 becomes the main delivery.
- Q-F2 shows few computers and many Android phones: DR-E2-4 B (Android first).
- The census shows important phone-only documents: revisit OD-19 (options C, D or E).
- The owner declines visits: D1 is dropped, and the family waits for D2 with stopgaps only.

## Decision requests

### OD-19: Documents on Android in v1

- **Needed by:** Wave 1 exit (decision sitting 2).
- **Evidence:** §2 (K1–K3, Verified); B3 (pending).
- **Options:**

  | Option | What it means for the family | Cost | Reversibility | Risks |
  |---|---|---|---|---|
  | **A. Media only (recommended)** | Phone photos and videos protected; documents protected on computers | None extra. The Photo & Video declaration is needed anyway (B3). | Easy | Phone-only documents stay unprotected (size unknown until E1). Android 14 partial media access can hide photos (§3). |
  | B. SAF chosen folders | The relative picks folders once in the system picker | Support time per phone | Easy | Cannot include Download itself or the storage root (K1); grants are lost if folders move |
  | C. All-files access | Everything in shared storage | Play review; a settings toggle per phone (K2) | Costly if Play rejects it late | Policy rejection; the broadest data sweep (D6) |
  | D. SAF on Documents/ plus "send to Reliquary" from the share sheet for single files | Covers Documents/ and individual files, including those in Download | A share-sheet flow; one picker grant | Easy | Relies on the relative's action for each file in Download |
  | E. The owner copies the phone's Download and Documents by cable at visits | Admin-side copies, no Play exposure | Owner visit time | Easy | Snapshot only |

- **Recommendation:** A for v1, as the cheapest default. E is a free complement during D1. Revisit B–D after the census and B3.
- **Touches settled text:** none.
- **If no decision:** assume A (intake default Q-H2).

### OD-01 (input; owned by B4): iOS

- **E2's position:** agrees with B4. Keep the settled deferral and add a computer bridge (option B) with freshness wording (§2.1). The ≥ 40 % iPhone share (E1-S2a) is a trigger to put the **reopening** question (option A, a settled-text change) to the owner, not an automatic rule. The OD-01 framing ("reconcile CLAUDE.md with ADR-0002") is stale; H1 should restate it.

### DR-E2-1 (H1 to number): Adopt the provisional v1 scope and delivery plan (ADR-0004 draft)

- **Needed by:** provisional acceptance at decision sitting 2; final at Gate A.
- **Options:**
  - A. As drafted: D0 → D1 → D2 → D3, v1 = D3. Note that **making concierge the first step changes the intake Q-H4 default**, which framed it as a fallback.
  - B. Skip D1 and go straight to the apps. Needs more owner hours.
  - C. Concierge only. Does not meet the v1 assistant features, so needs a settled-text change.
  - D. Declare D2 ("minimal assistant") to be v1, with named deferrals: the nudge escalation ladder, the full wizard and the in-app USB return trip. This matches F1's ~24-month figure. Deferring the wizard or the return trip amends ADR-0002.
- **Recommendation:** A, with D as the named fallback if Q-B9 confirms ~8 h/week and the owner wants a "v1" label sooner.
- **If no decision:** the run assumes A as provisional.

### DR-E2-2 (H1 to number): Apply the interim protection this month (intake Q-H5)

- **Needed by:** now.
- **Options:** A. The stopgaps in §5.1 and `spikes/E2-S3/owner-checklist.md`, with only-copy items first. B. None.
- **Also decide:** who pays for any Google One or iCloud+ storage the stopgaps need, and up to what tier (Q-B1/B2). No prices were verified here.
- **Recommendation:** A. It is cheap and reversible, and it is the only protection for **1–5 years** on some devices (K11, estimate). Declining it should be recorded as an accepted risk (OD-17).

### DR-E2-3 (for H1's budget sheet): Candidate budget IDs

- BUD-COVER, BUD-FALSESAFE and BUD-PILOT-DUR as defined in §4.5. These are proposals with no source, for the owner to confirm. Also: mark the stop rules that use BUD-CLOUD and BUD-ABUSE inactive until H2 sets values.

### DR-E2-4 (H1 to number): Which D2 app comes first

- **Needed by:** Gate C planning (after E1-S2a and intake Q-F2/Q-H3).
- **Options:** A. Desktop first (intake Q-H3 default; ADR-0002's enrollment starts on the desktop). B. Android media app first, with phones enrolled by an owner-issued token at visits. E5 and D3 must check that against ADR-0002 §3. C. A health-only desktop app first, with the owner still seeding.
- **Evidence:** K8 (Verified): phone background upload is unreliable. F1 estimates Android at 200–400 h and desktop at 150–300 h (K11, estimate). CLAUDE.md says phones are the main keepsake source. D1 already covers computers with snapshots.
- **Recommendation:** A provisionally. Switch to B if the census shows Android camera rolls are poorly covered by the Google stopgap (no room, Storage saver or Free up space already used, Q-G2) and the family has few computers.

### DR-E2-5 (H1 to number): Admin-side import of stopgap cloud exports in v1

- **Question:** may the owner import Google Takeout, icloudpd or Apple-transfer copies into Reliquary in v1, as **admin tooling** (A9) rather than a client source?
- **Options:** A. Yes, as admin-only import with provenance; consent and credential handling per D6. B. No: keep them on the homelab outside Reliquary until the roadmap's cloud sources ship.
- **Touches settled text:** yes. "v1 data sources: files on the device only"; iCloud and Google Photos are on the roadmap.
- **Recommendation:** A. The data is already in the owner's hands, and leaving it outside the verified store protects it less. If there is no decision, B applies, and nothing is lost.

## Hand-offs

| To | What | Why |
|---|---|---|
| E3 | The requirements for a reassuring word (§1.2 a–d, including the grace window and the partial-grant rule); test whether relatives can tell "stored at home" from "Protected" (E3-S1); activity-only email text; bridge freshness wording | ADR-0024, ADR-0025 |
| E5 | iPhone bridge wording in the wizard (an ADR-0002 §3 question); E5-S3 is the BUD-ENROLL evidence; whether an owner-issued phone token fits ADR-0002 (DR-E2-4 B) | ADR-0038 |
| B2, B5 | Report a grant-scope flag; Android 14 partial access; detect bridge placeholders and optimized libraries | M2, §2.1 |
| B4 | OD-01 restated: keep the deferral and add the bridge; verify iCloud for Windows placeholder behaviour | §2.1 |
| A3, B8 | The receipt-batch cursor for the M9 digest; the M1–M10 field list; fixed-size padded reports | E2-S2 conditions |
| D6 | Consent for owner-made copies; custody of icloudpd credentials and sessions; operational vs opt-in fields; activity-only email | §1.3, §5.1, §3 |
| C3 | Nudge email text carries activity facts only | E2-S2 |
| D3, D5 | Rollback by Worker-side suspension (BUD-REVOKE); the signed device pause is optional | §4.4 |
| A8, C8 | Device-side restore verification for M7; drill sampling by rotating slices | M7 |
| A9 | Provenance; bytes kept as received; measure byte identity and Takeout naming in A9-S1; DR-E2-5 | §5.3 |
| A6 | A browsable read-only export for a later viewer | §6 |
| B3 | Play evidence for all-files access and the Photo & Video declaration | OD-19 |
| C4 | Bandwidth sizing behind BUD-COVER | §4.2 |
| E1 | Census of phone documents; the iPhone share; the visit-block order | OD-19, OD-01 |
| E6 | The "browse and share" script; scripts for "storage full" and "free up space" prompts; pause messages | §5.1, §4.3 |
| E2 spike runner (Wave 2) | Fix the E2-S1 kit copy and the Q3 rubric; add the "no room", cost and custody rows to the E2-S3 checklist; re-run E2-S2 against the A0 harness | §Spikes |
| H1 | OD-01 premise stale (decision-queue row, PLAN §4.3, R-03); candidate budgets; number DR-E2-1 to DR-E2-5; blocked sources (support.google.com, developers.google.com/.cn, support.apple.com, privacy.apple.com, takeout.google.com, support.microsoft.com, nngroup, research.google, dl.acm.org, measuringu) | Registries |

## Appendix B. Intake answers that could change this note and ADR-0004

| Intake ID | Question (short) | If the answer is… | …then |
|---|---|---|---|
| Q-B9 | Owner build hours per week | Much more than 8 h | D1 shortened or skipped; D3 sooner |
| Q-B9 | (same) | Much less than 8 h | D1 becomes the main delivery; DR-E2-1 D or F1's "compose stopgaps" pivot |
| Q-F3 / E1-S2a | iPhone share of camera-roll bytes | ≥ 40 % | Ask the owner whether to reopen the iOS deferral (a settled-text change; Apple spend Q-B8) |
| Q-F2 | Device counts | Few computers, many Android phones | DR-E2-4 B |
| Q-F2 | (same) | Many iPhones and no computers | The bridge fails; escalate OD-01 |
| Q-F4 | Total keepsake size | Over 10 TB | More USB seeding; BUD-COVER timing; C4 and C5 sizing |
| Q-F6 | People without email or a Google account | Any | Email nudges need another channel; the Play closed track fails |
| Q-F7 | Accessibility needs | Any | E6 scope inside v1 |
| Q-F8 / Q-F9 | Research participants; a helper | Fewer than 5; no helper | E2-S1 gives no result; drills for platforms the owner lacks have no host |
| Q-G2 | Cloud photo settings in use | Storage saver or Free up space already used | Originals already gone for those items; Takeout route; the cloud-only bucket matters more; DR-E2-4 B more likely |
| Q-G4 | Only-copy items | Yes | Copied first (§5.1) |
| Q-H1 | iPhone view | "In v1" | As for Q-F3 ≥ 40 % |
| Q-H2 | Android documents | Chosen folders or all files | OD-19 B, C or D; B3 work on the critical path |
| Q-H3 | Desktop or Android first | Android | DR-E2-4 B |
| Q-H4 | Concierge acceptable | No | D1 dropped |
| Q-H5 | Apply stopgaps now | No | Nothing protected for 1–5 years; record as an accepted risk (OD-17) |
| Q-H6 | Browse and share | Needed in v1 | OD-13; A6 export; scope grows |
| Q-D1 / D2 / D5 | Bandwidth and caps | Slow or capped | More USB; stop rule 6 |
| Q-B1 / B2 | Cost ceilings | Low | More USB in seed months; who pays for stopgap storage |
| Q-B8 | Apple spend | Yes | Reopening iOS becomes cheaper (still a settled-text change) |
| Q-A3 | A household in BR/ID/SG/TH | Yes | Android developer verification already applies (T2); B3 timing |
| Q-A4 | Languages | Not English only | E6 localisation inside v1 |
| Q-F5 | Managed work or school devices | Any hold keepsakes | Concierge copy or stopgap only |
