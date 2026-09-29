# Public test corpus: sources and licences

- **Owner:** H3. Rules: [`../h3-research-data-governance.md`](../h3-research-data-governance.md), §2–§6.
- **Status:** Draft, 2026-09-29. Sources checked from the research container on that date. Nothing has been downloaded into the repo.
- **What this is:** the list of public (PUB) files and metadata to assemble into corpus tiers S, L, D and G, with licence evidence. Synthetic edge cases (awkward names, sizes, times, placeholders) come from the generator spec in H3 §7, not from here.

## How the corpus is assembled

1. **Fetch by manifest, never commit (for now).** A manifest (to be written with G2, for example `corpus/manifest.jsonl`) lists, for each file: PUB ID, upstream URL, upstream commit or object ETag, path, size, SHA-256, licence, attribution, tier and tags (`hostile`, `gps`, `motion-photo` …). Until ADR-0036 decides the repo licence, no third-party binaries are committed (H3 R9).
2. **Pin everything.** Git sources are pinned to the commit below. Other files are pinned by SHA-256. A fetch that does not match fails loudly.
3. **Keep a copy at home.** Upstreams disappear (`ianare/exif-samples` is already archived). The homelab keeps a copy in `research/corpus-public`.
4. **Attribution travels with the files.** CC BY sources need the author and licence kept next to each file: Open Images supplies `Author` and `OriginalLandingURL` per row; libultrahdr and NapierOne need a credit line.
5. **Hostile files** (fuzzing crashers, deliberately broken files) are opened only in the container or a disposable VM (H3 R10).

## Sources

"Evidence" says how the licence was checked. **Primary** means the licence text or statement was read at the source (repo file, publisher page or registry entry). **Secondary** means search snippets only, because the site is blocked from the container. Access routes: see "Reachability" below.

### Media edge cases (Tiers S and G)

| ID | Source (pinned) | What is useful in it | Licence as stated | Evidence | Use policy |
|---|---|---|---|---|---|
| P1 | [immich-app/test-assets](https://github.com/immich-app/test-assets) @ `ec56cc6` (2026-06-03); 60 files, 358 MB | **Motion Photos**: `formats/motionphoto/pixel-6-pro.jpg`, `pixel-8a.jpg`, `samsung-one-ui-5.jpg`, `samsung-one-ui-6.jpg`, `samsung-one-ui-6.heic`. **RAW**: CR2 (3), RAF, NEF (2), RW2, DNG (Ricoh GR III), ARW (2). HEIC, AVIF (8- and 10-bit HDR), JXL (8- and 16-bit HDR), WebP. XMP sidecars; date-priority, GPS and empty-GPS cases; 3 videos (MP4, MOV). | **Conflict:** README says "All assets are public domain"; repo `LICENSE` is AGPL-3.0 | Primary (both files read) | Treat as AGPL-3.0: fetch-only, internal testing |
| P2 | [google/libultrahdr](https://github.com/google/libultrahdr) `tests/data` @ `66821e0` (2026-09-28) | **Ultra HDR / gain-map JPEGs**, including `apple_gainmap_new.jpg` and `apple_gainmap_old.jpg`; a synthetic ISO 21496-1 gain-map HEIC (`gainmap_hevc_16x16.heic`) | `tests/data/LICENSE`: CC BY 4.0. The gain-map HEIC: Apache-2.0 OR MIT (its own README) | Primary | Fetch-only until ADR-0036; then may be committed with attribution |
| P3 | [ianare/exif-py](https://github.com/ianare/exif-py) `tests/resources` @ `a69bf74` (2026-06-10). Successor of the archived [ianare/exif-samples](https://github.com/ianare/exif-samples) @ `5332a9c` | JPEGs from about 20 camera models; `gps/` (9 JPEGs with GPS); orientation 1–8 (landscape and portrait); `invalid/` and `corrupted.jpg`; HEIC (iPhone 13 Pro Max, Nokia 8.3 incl. HDR); AVIF; TIFF | **Mixed, per file.** Most JPEG and TIFF files are from Wikimedia Commons (licence on each file's Commons page). `exif-org/` and `gps/` samples have no licence stated. User contributions are CC BY-SA 4.0. The code is BSD-style. | Primary (READMEs) | Fetch-only, internal testing. Do not redistribute. |
| P4 | [drewnoakes/metadata-extractor-images](https://github.com/drewnoakes/metadata-extractor-images) @ `651ad0e` (2026-02-02); about 10.7k tracked files, including metadata text dumps | About 45 format folders: HEIC (iPhone `IMG_29xx.HEIC`), HEIF (Sony A7 IV `.HIF`), CR3, DNG (Nexus 5X, DJI), ARW, ORF, RW2, PSD, JPEG 2000; MOV and MP4 with GPS; `apple-livephoto-quicktime.mov` (**video half only**); filenames with spaces and parentheses; a `fuzzing/` folder (about 5.8k entries) | README: "You are free to use these media files however you wish." No formal licence file. | Primary (README) | Fetch-only. Tag `fuzzing/` as `hostile`. |
| P5 | [strukturag/libheif](https://github.com/strukturag/libheif) @ `5c7b41f` (2026-09-21) | `examples/example.heic`, `examples/example.avif`; `fuzzing/data/corpus/` (133 files, including crash reproducers) | `examples/COPYING`: MIT. Library: LGPL-3.0. The fuzz corpus has no separate licence, so treat it as LGPL-3.0. | Primary | Fetch-only. Fuzz corpus tagged `hostile` (G2-S3 seeds). |
| P6 | [exiftool/exiftool](https://github.com/exiftool/exiftool) `t/images` @ `2200871` (2026-05-27); 194 files | Tiny samples covering 129 distinct file extensions (JPEG, XMP, RAW variants, PDF, video and audio containers) | "Same terms as Perl itself (either the Perl Artistic License or GPL)" | Primary (README) | Fetch-only. Format-ID and parser coverage. |
| P7 | raw.pixls.us | RAW samples for most cameras, per model | CC0 preferred. Older files carried over from rawsamples.ch are CC BY-NC-SA. Check each file. | **Secondary only** (site blocked; [darktable post](https://www.darktable.org/2017/01/rawsamples-ch-replacement/), [discuss.pixls.us thread](https://discuss.pixls.us/t/14-cc0-files-from-raw-pixls-us-one-per-format-run-through-macoss-native-raw-decoder/60891)) | Fetch on the homelab. Take CC0 files only. |

### Documents, formats and broken files (Tiers S, L and D; A7-S3 rehearsal)

| ID | Source | What is useful in it | Licence as stated | Evidence | Use policy |
|---|---|---|---|---|---|
| P8 | [openpreserve/format-corpus](https://github.com/openpreserve/format-corpus) @ `366f068` (2026-06-05) | Small files covering many formats and creating tools. Broken and awkward PDFs: `pdfCabinetOfHorrors/`, `govdocs1-error-pdfs/`, `jhove-errors/`; office, ebook, JPEG 2000, TIFF and video examples | README: "All items are CC0 licenced unless otherwise stated." | Primary | Best candidate for committing once ADR-0036 allows it. Check the per-folder exceptions. |
| P9 | **GovDocs1**, `https://digitalcorpora.s3.amazonaws.com/corpora/files/govdocs1/` (`s3://digitalcorpora`) | About 1M documents gathered from US `.gov` web servers. Measured listing: `zipfiles/` has 1,000 zips totalling **333.5 GB**; `threads/` has 10 subsets of 1,000 files, each zip 0.25–0.35 GB; `by_type/` has per-type archives (doc, ppt, xls, jpg, txt, csv, log …) | AWS Open Data registry entry: "There are no restrictions on the use of this data." Digital Corpora: freely available for research and "(to the best of our knowledge) freely redistributed" | Primary ([registry YAML](https://github.com/awslabs/open-data-registry/blob/main/datasets/digitalcorpora.yaml)); digitalcorpora.org is blocked, so its wording is secondary | Tier L documents (about 300 zips ≈ 100 GB). `thread0` for rehearsals. Cite Garfinkel et al., DFRWS 2009. |
| P10 | **NapierOne**, `s3://napierone.com` (eu-north-1); [README](https://github.com/simonrdavies/NapierOne) | Over 500k files across 44 modern types (DOCX, XLSX, PPTX, PDF, EPUB, archives, images, MP3, MP4); about 2 TB in total | Edinburgh Napier University licence (MIT-style, attribution required), plus a per-subset licence: gov.uk documents under the Open Government Licence v3, TIFFs from RAISE, audio from FMA, video from Kinetics-700 | Primary (README, [registry YAML](https://github.com/awslabs/open-data-registry/blob/main/datasets/napierone.yaml)) | Optional. Use the modern Office and PDF subsets for Tier L and D. **Skip the video subset**: it is drawn from YouTube clips of people. |

### Size metadata (F3-S1, generator priors)

| ID | Source | What is useful in it | Licence as stated | Evidence | Use policy |
|---|---|---|---|---|---|
| P11 | **Open Images** `https://storage.googleapis.com/openimages/2018_04/image_ids_and_rotation.csv` (3,348,497,077 bytes; linked from the [V7 download page](https://storage.googleapis.com/openimages/web/download_v7.html)) | Per image: `OriginalSize` ("the download size of the original image"), `OriginalMD5`, `OriginalURL` (Flickr original), `License`, `Author`, `OriginalLandingURL` | "The annotations are licensed by Google LLC under CC BY 4.0 license. The images are listed as having a CC BY 2.0 license", with no warranty; verify each image ([facts and figures](https://storage.googleapis.com/openimages/web/factsfigures_v7.html)) | Primary | F3-S1 public exact sizes; photo-size prior for the generator. Tier L photos: download via `OriginalURL`, keep attribution, record dead links (not tested). |
| P12 | Wikimedia Commons `image` table dump (`img_size`, MIME) | Exact sizes and types for the Commons collection | Not verified | **Secondary only**; dumps.wikimedia.org is blocked. Old dumps were 17–19 GB ([archive.org](https://archive.org/details/commonswiki-20170220)). | Alternative to P11 if F3 wants a second distribution |

**Indicative measurement (P11 only; F3-S1 must redo it on the whole file).** Taken from the first 50 MiB of the CSV: 143,700 rows. This is **not a random sample**, and the share of unique sizes falls as the number of rows grows.

| Statistic | Value |
|---|---|
| Median `OriginalSize` | 1.30 MB |
| 10th / 90th percentile | 0.12 MB / 5.69 MB |
| Mean | 2.24 MB |
| Max | 15.7 MB |
| Files with a unique exact size | **95.1 %** |
| Type and licence | All JPEG; all CC BY 2.0 |

### Video

| ID | Source | Licence | Evidence | Use policy |
|---|---|---|---|---|
| P13 | Blender open movies (Big Buck Bunny, Sintel, Tears of Steel) | CC BY 3.0 | **Secondary only**: peach.blender.org and download.blender.org are blocked ([Wikipedia](https://en.wikipedia.org/wiki/Big_Buck_Bunny), [Tears of Steel](https://en.wikipedia.org/wiki/Tears_of_Steel)) | Optional realistic long video. Fetch on the homelab. |
| — | Synthetic: ffmpeg `lavfi` test source, concatenated by stream copy past 4 GiB | No third-party content | — | Default for videos over 4 GiB and 20-minute clips (H3 §7.4) |

### Tools that create fixtures (not data)

| ID | Tool | Licence | Evidence | Use |
|---|---|---|---|---|
| T1 | [Windows-classic-samples `Samples/CloudMirror`](https://github.com/microsoft/Windows-classic-samples/tree/main/Samples/CloudMirror) | MIT | Primary | Creates a cfapi sync root with placeholders from a local "server" folder, so placeholder fixtures (B5) need no cloud account |
| T2 | Apple sample "[Synchronizing files using file provider extensions](https://developer.apple.com/documentation/fileprovider/synchronizing-files-using-file-provider-extensions)" | Apple sample-code licence (read the `LICENSE.txt` in the download) | Primary (page reachable) | macOS dataless-file fixtures |
| T3 | [minimaxir/big-list-of-naughty-strings](https://github.com/minimaxir/big-list-of-naughty-strings) @ `db33ec7` | MIT | Primary | A pool of names for the generator's filename cases |

## Not used

| Source | Why |
|---|---|
| [nokiatech/heif](https://github.com/nokiatech/heif) sample files | The Nokia HEIF License v2.1 limits use to "the non-commercial purposes of evaluation, testing and academic research". P1–P5 cover HEIC without that restriction. |
| rawsamples.ch-era files on raw.pixls.us under CC BY-NC-SA | Non-commercial and share-alike; take CC0 files instead |
| NapierOne video subset (Kinetics-700) | Clips of real people from YouTube; not needed |
| Any family or owner file | FAM, never corpus (H3 §1). Owner-made test media goes through the LAB rules (H3 R8). |

## Gaps

- **No licensed public sample** of an iPhone Live Photo pair (photo plus video with the same content identifier), ProRAW, burst, portrait or spatial video. These need LAB capture on an iPhone (H3 §8.1; OD-01).
- **No public WhatsApp-recompressed media, Windows auto-converted imports or Google Takeout JSON sidecars** with a clear licence. These need LAB capture with test accounts.
- P1's licence conflict and P3's per-file provenance mean neither can be redistributed until someone resolves them. Asking the upstream maintainers is optional.

## Reachability from the container (2026-09-29)

| Route | Result |
|---|---|
| `git clone --filter=blob:none --depth 1 https://github.com/...` | **Works.** Used for P1–P6, P8 and T3 (the GitHub web UI, the API and the GitHub MCP tool for non-project repos do not work) |
| raw.githubusercontent.com | Works (T1, P10 README, registry YAMLs) |
| `digitalcorpora.s3.amazonaws.com` (anonymous S3 list and get) | Works (P9) |
| `s3.eu-north-1.amazonaws.com/napierone.com` (list) | Works (P10) |
| `storage.googleapis.com/openimages/...` | Works (P11) |
| developer.apple.com | Works (T2) |
| raw.pixls.us, pixls.us, digitalcorpora.org, dumps.wikimedia.org, download.blender.org, peach.blender.org, media.xiph.org | **Blocked** (proxy and WebFetch). Report to H1 for `sources.md`. |
