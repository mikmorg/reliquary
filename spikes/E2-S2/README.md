# Spike E2-S2: metric feasibility (THROWAWAY)

> **Throwaway spike code, not production code.** Synthetic data only (H3 class `SYN → results`).
> The pipeline part is **emulated, not real R2/Cloudflare**: a Python dict stands in for R2 and a
> list for the Worker's plaintext log. The encryption is real (the `age` CLI, X25519 recipient).

- **Spike:** E2-S2 "Metric feasibility" (PLAN E2). Exec tag CT.
- **Pass rule (PLAN):** every kept metric has a trust-model-compliant data source.
- **Budget IDs:** BUD-TEL (< 1 MB/day network and < 50 MB disk per device; proposed, owner to confirm). The metrics themselves cite BUD-TTS, BUD-ENROLL, BUD-SUPPORT and BUD-RESTORE (see the E2 note §3); this spike does not measure those.
- **Run by / date:** E2 spike runner (agent), 2026-09-29, in the research container (Linux 6.18 x86_64, 4 vCPU, Python 3.11, age 1.1.1).
- **Metrics checked:** M1–M10 as defined in `docs/research/e2-v1-scope-metrics-pilot.md` §3.

## What it does

1. **`metrics_model.py`: field inventory and rule check.** Lists every data field that M1–M10 need, where it is produced, the route it takes, whether it is derived from file content or names, and whether it is per-file. It then applies six rules taken from settled text:
   - R1: no third-party analytics (PLAN E2).
   - R2: nothing content-derived in cloud plaintext (ADR-0001 §2: metadata is ciphertext only).
   - R3: cloud plaintext only in the categories ADR-0001/0002 accept: name and email, per-device activity timestamps, invite hash and state, opaque dedup IDs and claim/commit state, ciphertext objects, email send events, and nudge text derived from activity only.
   - R4: no per-file identifiers in cloud plaintext beyond the ingest protocol.
   - R5: telemetry is aggregates or digests, never per-file lists (minimisation).
   - R6: no email click tracking (PLAN §3).

   Five deliberately bad variants are included as negative controls (they are not proposals).
2. **`simulate.py`: emulated pipeline.** 25 devices (the CLAUDE.md upper bound), 10 persons, 30 days, 1k–20k synthetic items per device. Each device sends one daily report of aggregate counters, padded to 2,048 bytes and encrypted with `age` to the homelab recipient. The homelab decrypts the reports and computes M1, M2, M6, M7, M9 and M10 from them, from its own receipt ledger, and from the Worker's plaintext timestamps. Four faults are injected:
   - a false-safe UI bug (dev-07: 3 items shown "stored" one day before their receipts arrive);
   - a gone-before-safe event (dev-12: 2 items);
   - a cloud-only bucket (dev-03: 500 items);
   - a stale device (dev-18: offline on days 12–20).
   
   Consent versioning follows Syncthing's `ClearForVersion` pattern: fields whose "since" version is newer than the accepted version are zeroed. Every 5th device accepted only report v1.
3. **Leak scan.** Searches every byte the mock cloud holds (Worker log, R2 keys and objects) for synthetic filenames, path tokens, plaintext SHA-256 values, record_ids and report field names. As a positive control, the same scanner runs over the plaintext reports.

Run: `./run_all.sh` (about 1 minute; needs `age` and `age-keygen` on PATH). Record IDs, content hashes and item sizes are random on each run, so the counts vary slightly between runs. The rule results and the fixed report size do not.

## Results (measured on this run; `evidence/`)

**Rule check (`evidence/metrics-check.json`).**
- M1–M10: all **COMPLIANT**. Every field has a route allowed by settled text.
- All 5 negative-control variants are flagged:

| Variant | Rules it breaks |
|---|---|
| Coverage computed in the Worker from plaintext counts | R2, R3 |
| Nudge action measured by email click | R3, R6 |
| Nudge email quoting counts, e.g. "1,203 photos not protected" | R2, R3 |
| Hosted analytics SDK | R1 |
| False-safe check with a plaintext record_id list | R4 |

**Emulated pipeline (`evidence/simulate-result.json`).** 708 encrypted reports, 1,717,380 cloud bytes scanned.

| Check | Result |
|---|---|
| Leak scan hits in cloud bytes: 5,000 filenames, 5,000 path tokens, 5,000 SHA-256 hex, 4,800 record_ids, 16 field names | **0 / 0 / 0 / 0 / 0** |
| Positive control: field names found in the plaintext reports | 16 of 16 (the scanner works) |
| Distinct ciphertext sizes seen by the cloud | 1 (2,248 bytes); padding removes size as a signal |
| Keys in the Worker's plaintext log | `day`, `device`, `kind`, `nudge`, `size` (kinds: redeemed, last_seen, report_arrival, email_nudge_sent, restore_staged) |
| M9 false-safe detection: homelab compares the device's shown-stored digest with its own ledger up to the receipt batch the device has seen | Detected the injected bug: dev-07, day 10, 3 excess items. **No other mismatches** (no false alarms in 708 reports). |
| M10 gone-before-safe | dev-12: 2 (as injected) |
| M2 coverage | Computed per device at 7 and 30 days, by bytes and items. Two variants: excluding the cloud-only bucket (dev-03: 100 %) and including it (dev-03: 94.32 %). Gone-before-safe items stay in the denominator (dev-12 at 30 days: 99.98 %). The "30-day" value is read on day 29, the last simulated day. Synthetic rates, so the values mean nothing as targets. |
| M6 email nudge | One stale-device email (dev-18, day 14). Its outcome is computed at the homelab from activity and new commits within 3 days, with no click data. |
| M7 restore check | 4 platforms × 10 items; 0 mismatches (synthetic; the device's restore hash check is simulated, not real) |
| Consent versioning | v2 fields zeroed in every report from v1-consent devices: **true**. Present for v2 devices: **true**. |

**Sizes against BUD-TEL.**

| Quantity | Measured | BUD-TEL |
|---|---|---|
| Plaintext report (JSON) | 461–492 bytes | — |
| Encrypted padded report (age, binary) | 2,248 bytes | — |
| One report per day | 2,248 B/day | < 1 MB/day: **within** |
| Hourly reports (24/day) | 53,952 B/day | < 1 MB/day: **within** |
| 30 days of unsent reports in the device outbox | 67,440 B | < 50 MB disk: **within** |
| Plaintext list of 100k record_ids (for an ID-list false-safe check) | 3,500,001 B as JSON; 1,600,000 B as binary | Either **exceeds** 1 MB/day if sent daily |
| Digest used instead (SHA-256 + count) | 40 B | within |

- `age` encrypt time per report: median 10.83 ms, max 172.91 ms. This includes spawning the CLI process, so it is not a crypto benchmark.
- Only the report is counted. Real telemetry (B8) adds heartbeats and crash reports.

## What this means for the pass rule

**Pass (emulated).** Every metric M1–M10 has a data source that fits the trust model. The homelab can compute the device-derived metrics from encrypted aggregate reports without the cloud seeing anything beyond ADR-0002's accepted plaintext. Conditions and findings for the analyst:

1. **M9 needs a digest, not an ID list.** A per-device plaintext or even encrypted list of record_ids is 1.6–3.5 MB for 100k items, beyond BUD-TEL per day. A 40-byte digest plus a "receipt batch seen" cursor works and caught the injected bug with no false alarms. The digest must be computed over the receipts the device has actually seen (the cursor), or it raises false alarms while receipts are in flight.
2. **Nudge email text is limited to activity-derived facts.** An email that quotes counts ("1,203 photos not protected") puts content-derived aggregates in cloud plaintext (and at the email provider), which ADR-0002 §2 does not cover. Either keep emails to activity facts ("your laptop hasn't backed up in 14 days"), or raise it with the owner as a decision request (E3, C3, D6).
3. **M6 must measure the fix, not the click.** The fix can be computed at the homelab from commits and activity. No tracking links are needed.
4. **Pad the report to a fixed size.** The cloud then learns only report arrival times, which are per-device activity timestamps and already accepted by ADR-0002.
5. **M2 reports two numbers.** One excludes the cloud-only bucket and one includes it. Gone-before-safe items stay in the denominator, so coverage never looks better because data vanished.
6. **Consent versioning works as a mechanism.** Which fields are "operational" (always sent, covered by the family charter) and which are "research" (opt-in) is D6's decision. This spike marks only the nudge counters as v2 opt-in, as an example.
7. **Not tested:** the real Worker, D1, R2, Queues, email provider and B8's relay format; real clocks (the simulation counts in days); real device counters and UI; M3, M4, M5 and M8, which are paper or owner-log sources and have no code path.
