# Spike D2-S2: ingest key + 2-of-3 split recovery recipient; destroy the ingest key; recover; cost of adding a recipient later

- **Workstream / plan:** D2, `docs/research/PLAN.md` section "D2." (exec `CT`)
- **Run by / dates:** D2 spike runner (agent). Run 1 on 2026-09-29 (host heavily loaded). Run 2 on 2026-10-06, same code, which started on a quiet host; other work raised the load during the later rewrap and throughput steps. Both runs: 48/48 checks passed.
- **Data-handling class:** `SYN → results`. The 10 "photos" are random bytes with a JPEG-like prefix. Every key and share is a throwaway made and destroyed inside the work directory. Run 1's harness kept the pty-echoed test passphrase in `results.json`; the copies here are redacted (see "Harness note").
- **Budget IDs:** BUD-RECOVERY applies only indirectly. It needs a person, so it is measured by D2-S3, not here. BUD-INGEST is context for the rewrap rate. No new thresholds are introduced.

## Hypothesis

1. With stock age (v1.3.x), every object can carry an **ingest** recipient and a **recovery** recipient. The
   recovery identity can be split 2-of-3, and after the ingest key is destroyed any two holders recover
   the photos with stock tools only.
2. Adding a recipient to existing objects later costs much less as a **header rewrap** (the payload is
   unchanged) than as a full re-encryption, but it needs the ingest key online and a custom tool.

## What was built (`run_d2s2.py`, `rewrap/`)

| Variant | Construction | Stock tools on the recovery path? |
|---|---|---|
| A classic, sealed, SLIP-39 128-bit | X25519 ingest + X25519 recovery recipient on every object. The recovery identity file is sealed with age scrypt under a random 128-bit secret, and that secret is split 2-of-3 with SLIP-39 (20 words per share). | Yes: `shamir recover`, then `age -d` with its interactive passphrase prompt, then `age -d -i` |
| B PQ, sealed, SLIP-39 256-bit | Same, with `age-keygen -pq` (mlkem768x25519) keys and a 256-bit secret (33 words per share) | Yes (needs age ≥ 1.3.0) |
| C1/C2 raw SLIP-39 | SLIP-39 of the raw 32-byte identity (classic / PQ), 33 words per share | **No**: one bech32 re-encoding step that no stock tool checked does (about 40 lines of Python) |
| D1/D2 age-plugin-sss | The per-object file key is split 2-of-3 to three holder age keys (classic / PQ) by `age-plugin-sss` v0.4.0, which its README calls experimental | Needs the plugin binary (no Windows builds per its README) |
| Mixing rules | `age -r classic -r pq` and `age -p -r …` | n/a |
| Rewrap | `rewrap/main.go`: recover the file key with the ingest identity (`age.DecryptHeader`), add an X25519 or PQ recovery stanza, recompute the header MAC from the C2SP spec, and keep the payload bytes | Custom tool (upstream age has none) |

Rebuild: `go install filippo.io/age/cmd/...@v1.3.1` (Go ≥ 1.25 for v1.3.2; v1.3.1 builds on 1.24),
`go install github.com/olastor/age-plugin-sss@v0.4.0`, `cd rewrap && go build -o ../bin/rewrap .`,
`python3 -m venv venv && venv/bin/pip install 'shamir-mnemonic[cli]==0.3.0'`, then `BIN=bin VENV=venv ./run_d2s2.py`
(`QUICK=1` runs a smaller smoke test). The script also expects a distro `age` 1.1.1 at `/usr/bin/age` for the old-version check.

## Environment

Cloud container, 4 vCPU x86-64, Go 1.24.7, Python 3.11.15, age v1.3.1 built from `proxy.golang.org`, Debian
age 1.1.1, shamir-mnemonic 0.3.0, age-plugin-sss v0.4.0. Work files are in tmpfs (`/dev/shm`). **This is not
homelab hardware, and disk I/O is excluded everywhere.** Load averages are recorded per step in
`evidence/*/results.json`.

## Results: recovery (hypothesis 1), both runs

| Check | Result |
|---|---|
| age v1.3.1 refuses X25519 + mlkem768x25519 in one file | **Refused**: "incompatible recipients: can't mix post-quantum and classic recipients…" |
| age refuses `-p` (passphrase) together with `-r` | **Refused** |
| A and B: ingest key destroyed; one share alone recovers nothing; shares 1+3 rebuild the secret; stock `age -d` unseals the recovery identity through its prompt; the recovered recipient matches the 16-hex fingerprint "printed on the card"; all 10 photos decrypt SHA-256-identical | **Pass** (A and B, both runs) |
| A wrong secret is rejected by age (scrypt stanza MAC), not silently accepted | **Pass** (SLIP-39 itself would not detect it) |
| Debian age 1.1.1 decrypts classic objects (A) | **10/10** |
| Debian age 1.1.1 on PQ objects (B) | **0/10**: it cannot even parse the PQ identity. A doomsday kit for PQ needs age ≥ 1.3.0 |
| C1/C2 raw SLIP-39 of the identity | **Pass**, but only with the non-stock bech32 step |
| D1/D2 age-plugin-sss: holders 1+3 decrypt all 10; one holder alone fails | **Pass**. The D2 PQ variant is labelled post-quantum by `age-inspect`, so it may sit beside a PQ ingest key |

Sizes (run 2; run 1 is the same except where noted):

| Item | Classic | PQ |
|---|---|---|
| Recipient string length | 62 chars | 1,959 chars |
| Header per object, ingest + recovery (2 stanzas) | 266 B (168 B with ingest only) | 3,184 B (1,627 B with ingest only) |
| Header per object, ingest + age-plugin-sss 2-of-3 | 631–638 B (run 1: 633–638) | 6,548–6,553 B |
| `age-plugin-sss` recipient string | 325 chars (run 1: 323) | 6,050 chars |
| Sealed recovery identity file | 366 B | 2,266 B |
| Words per SLIP-39 share | 20 (128-bit secret) | 33 (256-bit secret) |

Recovery timings in tooling only, not a person (run 2): SLIP-39 recover 0.06–0.10 s; interactive unseal
about 1.0 s; decrypting 10 photos (22.6 MB total) 0.10–0.11 s. The person-time question is D2-S3.

## Results: cost of adding a recipient later (hypothesis 2)

In-memory header rewrap (unwrap with the ingest identity, add one recovery stanza, re-MAC). The pool has
1,024 distinct objects, and every pool object was verified after rewrap: it decrypts with the recovery
identity alone and with the ingest identity alone, and a 1-bit header flip is rejected.

| Case | Run 2 (2026-10-06) | Run 1 (2026-09-29, load 9–40) |
|---|---|---|
| Classic, 4 workers, **1,000,000 rewraps** | **97.0 s** (10,313/s) | 277.8 s (3,600/s) |
| PQ, 4 workers, **1,000,000 rewraps** | **186.0 s** (5,376/s) | 317.7 s (3,148/s) |
| Classic, 1 worker, 100k ×3 (median) | 2,882/s (2,882 / 2,921 / 2,882) | 2,107/s |
| Classic, 4 workers, 100k ×3 (median) | 10,546/s (10,295 / 10,546 / 11,437) | 4,177/s |
| PQ, 1 worker, 100k ×3 (median) | 2,407/s (2,400 / 2,431 / 2,407) | 2,332/s |
| PQ, 4 workers, 100k ×3 (median) | 4,153/s (4,060 / 4,153 / 4,333) | 4,051/s |

On-disk rewrap of 500 × 1 MiB objects in tmpfs, verified with both age v1.3.1 and Debian age 1.1.1 (10/10
sampled), with payload bytes after the header byte-identical (10/10):

| Mode | Run 2 | Run 1 | Bytes written |
|---|---|---|---|
| Rewrite the whole object (new header + copied payload) | 1.28 s | 1.13 s | 524,557,000 B |
| Header sidecar only (payload file untouched) | 0.55 s | 0.62 s | 133,000 B (266 B per object) |

Full re-encryption baseline: stock `age -d | age -r ingest -r recovery` on one 1 GiB file in tmpfs, median of 3:

| Operation | Run 2 MiB/s | Run 1 MiB/s |
|---|---|---|
| encrypt | 697.0 | 572.6 |
| decrypt | 464.2 | 485.4 |
| decrypt → re-encrypt pipe | **324.4** | 421.4 |
| plain copy (memory bandwidth reference) | 2,050.9 | 1,790.8 |

**Arithmetic, not measured:** at the run-2 pipe rate, re-encrypting 2 TB / 10 TB takes about 1.6 h / 8.2 h
of CPU on 4 such vCPUs before any disk I/O. Reading and rewriting 2–10 TB on homelab disks is likely to
dominate, and that was not measured. The header rewrap of 1M objects took 1.6–5.3 minutes of CPU and writes
about 0.27 GB (classic) or 3.2 GB (PQ) of headers. That is cheap in CPU, but:

- it needs the **ingest identity online** to recover each file key;
- it cannot reach objects that are no longer in the store (USB sticks in drawers, R2 staging, restores
  already handed out);
- it needs a custom tool. The spike's tool computes the header MAC itself from the C2SP spec because Go age
  v1.3.1 has no public "re-header" API;
- unless the store keeps headers separate from payloads (sidecar) or the engine tolerates in-place header
  growth, the whole object is rewritten anyway (classic 168 → 266 B, PQ 1,627 → 3,184 B), so the I/O cost
  approaches a full copy. Which applies depends on A6's engine choice.

## Pass / fail against PLAN D2-S2

**Pass.** Recovery succeeded with a 2-of-3 split after the ingest key was destroyed, in all six variants. The
cost of adding a recipient later was measured as 1M header rewraps against a full re-encryption rate. The
stock-tools-only paths are A (classic) and B (PQ, age ≥ 1.3.0). A PQ ingest key forces a PQ recovery
recipient, because age refuses to mix them.

## Harness note

In run 1 the pty harness wrote the test passphrase before age had switched off terminal echo, so the echoed
secret appeared in `unseal_prompt_seen`. That secret belonged to a throwaway key whose objects were deleted.
It is redacted in `evidence/run1-2026-09-29/results.json`, and `run_d2s2.py` now redacts it and records
`unseal_secret_echoed_in_pty_transcript`. Run 2 did not hit the race. This is a harness timing artefact, not
evidence that age echoes passphrases.

## Limits

- Shared VM, tmpfs only, 4 vCPU. Rates vary up to about 3× between runs with host load. Homelab disks and the
  A6 engine were not measured.
- One recovery recipient was added. Rotating the ingest key (replacing a stanza) costs the same per object.
- Synthetic data only. Nobody followed the recovery steps by hand (that is D2-S3).
