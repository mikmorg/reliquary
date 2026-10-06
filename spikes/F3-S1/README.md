# F3-S1: size fingerprinting on public corpus data

- **Workstream:** F3 (`docs/research/PLAN.md`, "F3."). **Exec tag:** CT (public part). The owner-library part is a kit: `docs/research/kits/F3-S1/`.
- **Run by / date:** F3 spike runner (Wave 1, batch W1-a), 2026-09-29, in the research container.
- **Data-handling class:** `PUB → results`. Only `OriginalSize`/`OriginalMD5` (Open Images) and zip-member extension/size/CRC-32 (GovDocs1) were written to disk, in the scratchpad, not the repo. Nothing per-file is committed; `evidence/` holds aggregates only.
- **Budget IDs:** none. The PLAN pass rule sets its own thresholds (> 50 % unique, < 3 % cost); no budget in `budgets.md` covers storage overhead. BUD-CLOUD is affected indirectly (transfer and staging bytes) and has no value yet.

## Hypothesis and decision

- **Hypothesis:** more than 50 % of files have a unique exact size today, and Padmé removes this at under 3 % storage cost.
- **Decision informed:** size padding in object format v1 (A2 / ADR-0007; F3 note DR-F3-1; one-way door #2). Pass → adopt padding. Fail → record an accepted risk under AR-05.

## Method

1. **Open Images 2018_04 `image_ids_and_rotation.csv`** (corpus P11; `https://storage.googleapis.com/openimages/2018_04/image_ids_and_rotation.csv`, 3,348,497,077 bytes, ETag `f7f38346dcd57968e473758cbabfc488`, Last-Modified 2018-05-17; fetched 2026-09-29). Streamed with `extract_oi.py`. It reads 9,178,275 rows with 0 parse errors. Identical content is collapsed by `OriginalMD5`, because Reliquary stores identical files once. That leaves **9,178,217** photos (all JPEG, CC BY 2.0 per the corpus README), 20.47 TB in total. `OriginalSize` is "the download size of the original image".
2. **GovDocs1** (corpus P9; `s3://digitalcorpora/corpora/files/govdocs1/zipfiles/000.zip … 999.zip`, fetched 2026-09-29). `extract_govdocs.py` reads only each zip's central directory, using HTTP range requests, and records the uncompressed size per member. It reads 986,279 members from 1,000 zips with 0 errors. Members are collapsed by (size, CRC-32), which approximates content dedup, and empty files are dropped. That leaves **974,742** documents, 492.97 GB in total.
3. **Padding functions** (`padlib.py`):
   - Padmé in integer arithmetic. `crosscheck.py` compares it with the reference `paddingLength` from `dedis/purb purbs/padding.go` (master, fetched 2026-09-29), compiled as Go in `gocheck/`. Result: **0 mismatches in 405,243 values**, covering 0–5,000, every power of two ±2 up to 2^49, and 400k random values up to 2^40 (`evidence/crosscheck.txt`).
   - 64 KiB buckets (round up to a multiple of 65,536 bytes, which is one age STREAM chunk).
   - Padding is applied to the plaintext before age. The script checks that the age v1 ciphertext length (`header + 16 + n + 16·⌈n/64 KiB⌉`) is injective, which it is. So age neither adds nor removes size classes: plaintext uniqueness equals ciphertext uniqueness.
4. **Metrics** (`analyze_s1.py`, `crossover.py`), computed on random subsamples of N files (seeded; 5 repetitions for N ≤ 100k, 3 for larger subsamples, 1 for the full set):
   - share of files whose size is unique within the set (the PLAN metric);
   - share in size classes of fewer than 10 files;
   - median class size;
   - byte-weighted storage overhead, plus mean and maximum per-file overhead.

   N stands for a single device (10k–100k files) up to a whole family. At the Open Images mean of 2.23 MB, 2 TB ≈ 0.9M files and 10 TB ≈ 4.5M files. That conversion is arithmetic, not a family measurement.

## Results (measured, 2026-09-29)

**Share of files with a unique exact size** (mean over repetitions; min–max spread was under 0.7 percentage points everywhere):

| N (random subsample) | Open Images photos | GovDocs1 documents |
|---|---|---|
| 1,000 | 99.92 % | 94.24 % |
| 10,000 | 99.62 % | 82.00 % |
| 25,000 | — | 74.28 % |
| 50,000 | — | 65.79 % |
| 100,000 | 96.58 % | 54.32 % |
| 150,000 | — | 47.27 % |
| 250,000 | 92.07 % | — |
| 500,000 | 85.58 % | 29.55 % |
| 974,742 (all GovDocs1) | — | 22.80 % |
| 1,000,000 | 75.29 % | — |
| 2,000,000 | 61.21 % | — |
| 3,000,000 | 51.87 % | — |
| 4,000,000 | 45.06 % | — |
| 5,000,000 | 39.85 % | — |
| 9,178,217 (all) | 26.44 % | — |

The 50 % crossing lies between 3M and 4M files for photos, and between 100k and 150k for documents.

**After padding** (share unique / share in classes of fewer than 10 files):

| N | Photos, Padmé | Photos, 64 KiB | Documents, Padmé | Documents, 64 KiB |
|---|---|---|---|---|
| 1,000 | 4.28 % / 90.7 % | 4.02 % / 36.0 % | 7.58 % / 76.7 % | 2.94 % / 11.9 % |
| 10,000 | 0.09 % / 1.53 % | 0.22 % / 3.92 % | 0.43 % / 5.51 % | 0.73 % / 3.49 % |
| 100,000 | 0.01 % / 0.08 % | 0.00 % / 0.04 % | 0.03 % / 0.38 % | 0.17 % / 0.65 % |
| ≥ 1,000,000 / all | 0.00 % / ≤ 0.01 % | 0.00 % / 0.00 % | 0.00 % / 0.03 % | 0.04 % / 0.18 % |

Median class size after Padmé: 45 files at N = 10k and about 438 at N = 100k (photos); 45 and about 429 (documents).

**Storage cost** (full sets; byte-weighted cost was stable across N):

| | Photos, Padmé | Photos, 64 KiB | Documents, Padmé | Documents, 64 KiB |
|---|---|---|---|---|
| Byte-weighted overhead | **1.131 %** | 1.466 % | **1.145 %** | **7.576 %** |
| Mean per-file overhead | 1.17 % | 9.87 % | 1.66 % | 573 % |
| Max per-file overhead, files ≥ 64 KiB | 3.125 % | 99.997 % | 3.125 % | 99.997 % |
| Max per-file overhead, all files | 6.25 % | 10,859 % | 11.63 % (tiny files) | 936,129 % |
| Byte-weighted overhead, files < 64 KiB | 1.99 % | 45.8 % | 2.02 % | 171 % |

For comparison, age's own X25519 overhead on these sets is 0.033 % (photos) and 0.063 % (documents), computed with a 168-byte header.

**Size bands, full sets** (exact-unique share → Padmé-unique share):

- Photos: < 64 KiB 1.8 % → 0.003 %; 64 KiB–1 MiB 3.8 % → 0; 1–16 MiB 45.3 % → 0.
- Documents: < 64 KiB 0.8 % → 0.0004 %; 64 KiB–1 MiB 42.0 % → 0; 1–16 MiB 71.7 % → 0; ≥ 16 MiB (2,272 files) 96.3 % → 1.19 %.

## Pass / fail against the PLAN rule

| Leg | Criterion | Measured | Result |
|---|---|---|---|
| Uniqueness | > 50 % of files unique today | Photos: 96.6 % at 100k, 75.3 % at 1M, 51.9 % at 3M, 45.1 % at 4M. Documents: 82.0 % at 10k, 54.3 % at 100k, 22.8 % at 975k | **Pass** for any one device's library (≤ 100k) and for a family photo set up to about 3M files (≈ 6.7 TB at the Open Images mean). **Fail** for document sets above about 130k files and for photo sets of 4M or more |
| Cost | Padding costs < 3 % storage | Padmé 1.13 % (photos), 1.15 % (documents). 64 KiB buckets 1.47 % (photos), **7.58 % (documents)** | **Pass** for Padmé; 64 KiB buckets fail on documents |

**Overall (public part): pass for Padmé at per-device and family photo scale.** The 64 KiB-bucket alternative fails the cost leg on documents. The owner-library leg is **pending** (kit `docs/research/kits/F3-S1/`); the family object count and its size mix decide which row of the uniqueness table applies.

## Caveats

- These are public corpora, not family libraries. Open Images sizes are Flickr originals uploaded between roughly 2005 and 2018; phone HEIC/JPEG sizes today may cluster differently. GovDocs1 is US government web documents.
- The attack surface is per device as well as per family, because the cloud sees which device uploaded each object. The per-device rows (10k–100k) are the most relevant, and they are the most unique.
- Size uniqueness within a set is a proxy. The attacker's real question ("is my candidate file here?") also depends on how many other files outside the family share the candidate's padded size. Padmé with 32 classes per octave leaves at least tens of family files per class at N ≥ 10k.
- Content dedup for GovDocs1 uses (size, CRC-32). It can merge distinct files that share both size and CRC-32, which can slightly overstate the unique share. Identical files always share both, so no true duplicate is missed.
- Padding hides nothing if any cloud-visible field still carries the exact size: receipts, the present-check, SR-24 declared size, multipart layout (F3 note C10; F3-S3 RT-15).

## Files

| File | Purpose |
|---|---|
| `extract_oi.py` | Stream the Open Images CSV from stdin and keep only `OriginalSize` and `OriginalMD5` (binary) |
| `extract_govdocs.py` | Read the GovDocs1 zip central directories with range requests |
| `padlib.py` | Padmé, 64 KiB buckets, age ciphertext length |
| `crosscheck.py`, `gocheck/` | Padmé cross-check against the dedis Go reference (`cd gocheck && go build -o padme_ref .`) |
| `analyze_s1.py`, `crossover.py` | Metrics |
| `evidence/f3s1_results.json`, `evidence/f3s1_crossover.json` | Aggregate results |
| `evidence/syn_rehearsal.json` | Output of the kit script on a 25k-file synthetic sparse tree (sizes drawn from these priors) |

Reproduce:

```sh
curl -sS https://storage.googleapis.com/openimages/2018_04/image_ids_and_rotation.csv | python3 extract_oi.py
python3 extract_govdocs.py
python3 analyze_s1.py
python3 crossover.py
```

Needs numpy. Run time in the container: about 2 min to extract each corpus, 2 min for the analysis.
