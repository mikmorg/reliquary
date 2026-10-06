# A2-S1: throughput and header cost, X25519 vs PQ (CT part, run 2026-10-06)

> Throwaway spike evidence. Code: `spikes/A2-S2/` (`bench-kem`, `bench-obj` and `soak` in `src/main.rs`). Synthetic data only (`SYN → results`). **These are x86 container numbers, not phone numbers.** The phone part (OL) is the kit in `docs/research/kits/A2-S1/`.

- **Hypothesis (PLAN A2-S1):**
  - Encryption is never the bottleneck against a 100 Mbit uplink.
  - The PQ header is ≤ 3 KB per object.
  - The PQ throughput loss is ≤ 10 % on a low-end phone.
  - BUD-BAT-S is recorded.
- **Decision informed:** OD-06 / ADR-0007 (DR-A2-1, DR-A2-2).
  - Pass: PQ from day one.
  - Fail: X25519 now, with a migration plan.
- **Budget IDs:** BUD-HASH and BUD-BAT-S (phone only, so not measurable here). The A2-local rule is "PQ header ≤ 3 KB, ≤ 10 % loss on a low-end phone".
- **Exec tag:** CT + OL.
- **Status:**
  - CT part: **ran**.
  - OL part: **kit-ready**.
- **Result of the CT part:**

| Criterion | Measured (x86 container) | Verdict |
|---|---|---|
| Header ≤ 3 KB per object, 1 PQ stanza | **1,627 B**. Exact and platform-independent; Rust encoder = Go age 1.3.2 = typage = kage | Pass |
| Header ≤ 3 KB per object, 2 PQ stanzas (ingest + recovery on device; DR-A2-2 option P2) | **3,184 B** (> 3,072 and > 3,000) | **Fail** |
| X25519 reference | 168 B header | — |
| Metadata record (separate age file, 1 PQ stanza, 1,024 B padded signed note) | 2,683 B on the wire | — (adds a second PQ header per file unless records are batched) |
| Encryption faster than a 100 Mbit uplink (12.5 MB/s) | Slowest case, PQ ×1 at 16 KiB objects: 86.3 MB/s (default build) and 70.9 MB/s (portable, non-SIMD build) | Pass on x86; **phone unmeasured** |
| ≤ 10 % PQ loss on a low-end phone | Not measurable in the container. x86 shape: below | **No result** (kit-ready) |
| BUD-BAT-S | Not measurable in the container | **No result** (kit-ready) |

## Measurements

Environment: see `evidence/environment.txt`.

- **Machine:** Intel Xeon @ 2.10 GHz, 4 vCPUs (AVX2, AVX-512, SHA-NI), shared with other spike runs. The 1-minute load average was 7.2–9.1 during the runs, so differences of a few percent are noise.
- **Software:** rustc 1.94.1, `hpke` 0.14.1.
- **Builds:**
  - *default*: SIMD backends;
  - *soft*: portable SHA-2, ChaCha20 and Poly1305 backends forced through `RUSTFLAGS`, as in the CE spike's "ARM stand-in". It is still x86, and ML-KEM and X25519 are unaffected.
- All values are best of 3 rounds.

**Header generation and opening per object** (`bench-kem`, 3,000 iterations per round):

| Recipients | Header | Generate, default | Generate, soft | Open, default | Open, soft |
|---|---|---|---|---|---|
| 1 × X25519 | 168 B | 80.7 µs | 87.3 µs | 75.0 µs | 78.3 µs |
| 1 × PQ | 1,627 B | 157.4 µs | 182.8 µs | 289.4 µs | 311.0 µs |
| 2 × PQ | 3,184 B | 319.4 µs | 370.8 µs | 607.6 µs | 616.1 µs |

"Open" for 2 × PQ uses the identity of the second stanza, so it includes a failed attempt on the first.

**Whole-object encryption throughput** (`bench-obj`: header plus STREAM, in memory, MB/s; loss relative to X25519):

| Object size | Default: X25519 | Default: PQ ×1 | Default: PQ ×2 | Soft: X25519 | Soft: PQ ×1 | Soft: PQ ×2 |
|---|---|---|---|---|---|---|
| 16 KiB | 179.3 | 86.3 (−51.9 %) | 48.3 (−73.1 %) | 128.1 | 70.9 (−44.7 %) | 40.8 (−68.1 %) |
| 100 KiB | 603.9 | 381.7 (−36.8 %) | 244.9 (−59.4 %) | 281.8 | 215.3 (−23.6 %) | 159.1 (−43.5 %) |
| 1 MiB | 981.7 | 839.0 (−14.5 %) | 732.6 (−25.4 %) | 372.6 | 345.9 (−7.2 %) | 335.2 (−10.0 %) |
| 4 MiB | 1,011.1 | 964.1 (−4.6 %) | 926.5 (−8.4 %) | 361.6 | 372.6 (noise) | 382.4 (noise) |
| 25 MiB | 1,011.7 | 1,009.9 (−0.2 %) | 1,047.8 (noise) | 373.1 | 366.6 (−1.7 %) | 351.5 (−5.8 %) |

An earlier round on the same code paths, with a load average of about 5, gave the same shape. For example, the PQ ×1 loss at 1 MiB was 11.1 % (default) and 5.6 % (soft). Those raw files were superseded by this run and are not kept.

## Reading (for the analyst)

- **The PQ cost is a fixed cost per object.** On this x86 machine it is about 77 µs per stanza to generate on the device and about 215 µs per stanza to open at the homelab. So the *relative* loss depends on object size and on how fast the bulk cipher is.
  - With a slower bulk cipher (the soft build, closer to a phone without fast ChaCha20/Poly1305), the relative loss at a given size goes **down**.
  - The absolute µs go up. On a phone they will be larger by an unmeasured factor.
- **Photo-sized objects.** The placeholder photo sizes are median 1.30 MB and mean 2.24 MB, indicative only (`docs/research/corpus/README.md`). At those sizes the x86 PQ ×1 loss is in the 5–15 % band. Whether a low-end phone lands under 10 % is exactly what the OL kit measures.
- **Small objects** (documents, thumbnails, metadata records) lose 35–50 % relative to X25519 even on x86. In absolute terms they stay far above 12.5 MB/s.
- **Records.** Each separate metadata record also pays one PQ header (2,683 B per record measured). Batching records (A2 note F6, A3 F8) amortizes this.

## Files

- `evidence/bench-kem-{default,soft}.txt` and `evidence/bench-obj-{default,soft}.txt`: raw rounds, with the load average per round.
- `evidence/summary.json` and `evidence/summarize.py`: best-of-3 summary.
- `evidence/environment.txt`.
