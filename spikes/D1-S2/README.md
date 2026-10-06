# Spike D1-S2: dedup poisoning and claim squatting tabletop (THROWAWAY evidence)

> Throwaway research code. It is an explicit-state model of the upload, claim and ingest protocol,
> explored exhaustively by breadth-first search, plus named scenarios replayed through the same
> transition relation. It is not the A3 formal model (A3-S1 owns that, in TLA+/Stateright or
> similar); it is the tabletop made executable so that each claim below has a trace behind it.

- **Spike:** D1-S2 (workstream D1, `docs/research/PLAN.md` Track D). Exec tag **CT**.
- **Run by / date:** D1 spike runner (agent), 2026-09-29, cloud container (4 vCPU x86-64, Python 3.11,
  `cryptography` 50.0.1 in a venv).
- **Hypothesis (PLAN):** dedup poisoning and claim squatting end in detection plus automatic
  re-upload with no silent loss; otherwise a protocol change is needed.
- **Decision informed:** OD-04 (supersede details of ADR-0001 §4), A3 (ADR-0009 state machine and
  invariants), C1 (ADR-0010 claim store and key layout), D4-S1 (the attack test owner).
- **Budget IDs cited:** none apply. The pass criterion is qualitative (no silent loss). BUD-TTS is
  affected by the extra round trips in the recovery path, but the model has no wall-clock time.
- **Data-handling class:** SYN → results.

## Model

**Actors.** Two honest devices H1 and H2 that both hold the same file F; the homelab; the Worker
(claim state), R2 (key → object map); one attacker, chosen per run:

| Attacker | Capabilities (each action spends one unit of budget) |
|---|---|
| `none` | – |
| `device` | M, an **enrolled** device holding the family dedup secret and its own registered signing key. Claims F's dedup ID whenever the Worker would give it a URL, and uploads garbage G as F (duplicate faking) with a record it signs itself. Squatting = claim and never upload |
| `leak` | Holds any honest device's presigned PUT URL (bearer, reusable until expiry: R2 docs) and overwrites that key with G, replaying the device's encrypted record blob |
| `fault` | An otherwise honest cloud loses a staged object (lifecycle rule, 7-day multipart auto-abort, operator error, backend bug; the Duplicacy "missing chunks" class) |
| `cloud` | Fully malicious control plane: answers "present" or "pending" to any query (unbounded), deletes or swaps staged objects, injects objects signed with a key it controls, relays any genuine receipt to any device, forges receipts with its own key |

**What is real.** Dedup IDs are HMAC-SHA256(HKDF-SHA256(family secret, `reliquary/v1/dedup-key`), content)
(T1 D-4). Metadata records and receipts carry real Ed25519 signatures. age encryption is abstract:
anyone with the homelab public key can make an object (age has no sender authentication).

**Properties** (checked in every reachable state or over the whole graph):

| ID | Property | Meaning |
|---|---|---|
| S1 | never green early | No honest device is green unless the homelab store holds verified F |
| SL | no silent loss | No state where a device is green, F is not stored, and no honest continuation (attacker stopped) can ever store F |
| S2 | tag consistency | The store never holds content under an ID it does not hash to |
| S3 | no false blame | No honest device is ever flagged to the admin |
| L1 | recoverable | From **every** reachable state, once the attacker stops, the honest actors alone (devices, homelab, time) can still reach "H1 and H2 both green and F stored". Checked for `none`, `device`, `leak`, `fault` (not `cloud`: availability is not claimed against it) |

L1 is the PLAN's "detection plus automatic re-upload": it fails exactly when an attack can leave
the system in a state from which no honest behaviour recovers.

**Protocol variants.**

| Feature | V0 (ADR-0001 §4 read literally) | V1 (proposed) |
|---|---|---|
| Staging key | `staging/<dedup_id>` ("objects are keyed by dedup ID") | `staging/<dedup_id>/<device><upload>` |
| Create-only PUT (If-None-Match) | not stated → off | off (unverified on R2; `V1+create_only` tests it on) |
| Device is green when | its upload completes, or the Worker does not list the ID as missing ("returns the missing ones") | it holds a homelab receipt for its own record; "present" counts only with a receipt for the content |
| Receipt key | n/a | pinned from the kit |
| Claim TTL | yes ("pending with TTL") | yes, while claimed |
| Staged state (no TTL after Complete) | not stated → off | on |
| Reset claim on rejection | not stated → off | on, only for the rejected upload's own claim, never for a committed ID |
| Device requery after timeout | not stated → off | on |
| Blame attribution | flag the device the key/claim belongs to | flag the signer only if its own signed record (incl. header MAC) matches the bad object; otherwise "tamper in transit" |
| Homelab re-verifies HMAC/SHA-256 after decrypting | yes (step 4) | yes |
| Device keys | from the Worker | admitted through a channel the cloud cannot forge (D1-S1 RC-5) |
| Staged object gone | not stated → claim stays | claim becomes re-claimable (`reconcile_missing`) |

Every "not stated → off" is an interpretation of a sketch, not a claim that ADR-0001 intends it.
The ablations (`V1-no-<feature>`) remove one V1 feature at a time to show which ones carry which property.

Bounds: 1 file, 2 honest devices, claim TTL = 2 ticks, at most 3 distinct upload keys per device
(after that a device re-PUTs its last key, which stands in for "retry forever"). Attacker budget:
1, 2 and 3 for every variant with one holder; 1 for every variant with two holders, plus 2 for V0 and
for V1 against `device`, `fault` and `cloud`. The homelab can be offline for any number of ticks.

## Results

Numbers in brackets are reachable states. "pass" = none of S1, SL, S2, S3, L1 violated (L1 is not
checked against `cloud`). Full logs, JSON and every shortest counterexample: `evidence/`.

### One holder (only H1 has F; the stricter test, because no second holder can mask a loss)

Columns give the attacker and its budget.

| Variant | none | device (b=1) | device (b=2) | device (b=3) | leak (b=1) | leak (b=2) | leak (b=3) | fault (b=1) | fault (b=2) | fault (b=3) | cloud (b=1) | cloud (b=2) | cloud (b=3) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| V0-ADR-0001-literal | S1 (8) | S1,SL,L1 (25) | S1,SL,S3,L1 (82) | S1,SL,S3,L1 (146) | S1,SL,S3,L1 (29) | S1,SL,S3,L1 (53) | S1,SL,S3,L1 (73) | S1,SL,L1 (11) | S1,SL,L1 (11) | S1,SL,L1 (11) | S1,SL,S3 (80) | S1,SL,S3 (370) | S1,SL,S3 (1,142) |
| V1-proposed | pass (167) | pass (368) | pass (740) | pass (1,142) | pass (948) | pass (2,596) | pass (4,787) | pass (352) | pass (542) | pass (732) | pass (1,024) | pass (5,106) | pass (15,828) |
| V1+create_only | pass (172) | pass (377) | pass (757) | pass (1,167) | pass (652) | pass (1,340) | pass (2,084) | pass (377) | pass (602) | pass (832) | pass (1,114) | pass (5,670) | pass (17,880) |
| V1-no-per_upload_keys | pass (80) | pass (192) | pass (477) | pass (775) | pass (324) | pass (634) | pass (898) | pass (163) | pass (230) | pass (292) | pass (528) | pass (2,208) | pass (5,784) |
| V1-no-receipts | S1 (7) | S1 (23) | S1 (47) | S1 (79) | S1,SL,L1 (20) | S1,SL,L1 (31) | S1,SL,L1 (39) | S1,SL,L1 (9) | S1,SL,L1 (9) | S1,SL,L1 (9) | S1,SL (60) | S1,SL (199) | S1,SL (444) |
| V1-no-pinned_trust | pass (167) | pass (368) | pass (740) | pass (1,142) | pass (948) | pass (2,596) | pass (4,787) | pass (352) | pass (542) | pass (732) | S1,SL (3,643) | S1,SL (29,141) | S1,SL (118,045) |
| V1-no-ttl | pass (16) | L1 (18) | L1 (37) | L1 (39) | pass (104) | pass (386) | pass (1,050) | pass (42) | pass (76) | pass (110) | pass (114) | pass (544) | pass (1,664) |
| V1-no-staged_state | pass (179) | pass (389) | pass (779) | pass (1,199) | pass (1,016) | pass (2,788) | pass (5,155) | pass (392) | pass (614) | pass (836) | pass (1,160) | pass (5,826) | pass (18,176) |
| V1-no-reset_on_reject | pass (167) | pass (368) | pass (770) | pass (1,172) | pass (959) | pass (2,641) | pass (4,892) | pass (352) | pass (542) | pass (732) | pass (1,036) | pass (5,178) | pass (16,024) |
| V1-no-requery | pass (8) | L1 (25) | L1 (51) | L1 (85) | L1 (24) | L1 (38) | L1 (48) | L1 (10) | L1 (10) | L1 (10) | pass (61) | pass (205) | pass (462) |
| V1-no-attribution | pass (167) | pass (368) | pass (740) | pass (1,142) | S3 (948) | S3 (2,596) | S3 (4,787) | pass (352) | pass (542) | pass (732) | S3 (1,116) | S3 (6,147) | S3 (21,097) |
| V1-no-homelab_verify | pass (167) | pass (368) | S1,SL,S2,L1 (902) | S1,SL,S2,L1 (1,436) | S1,SL,S2,L1 (1,048) | S1,SL,S2,L1 (3,176) | S1,SL,S2,L1 (6,377) | pass (352) | pass (542) | pass (732) | S2 (1,029) | S1,SL,S2 (5,339) | S1,SL,S2 (17,597) |
| V1-no-registry_auth | pass (167) | pass (368) | pass (740) | pass (1,142) | pass (948) | pass (2,596) | pass (4,787) | pass (352) | pass (542) | pass (732) | pass (1,176) | pass (7,013) | pass (26,740) |
| V1-no-reconcile_missing | pass (167) | pass (368) | pass (740) | pass (1,142) | pass (948) | pass (2,596) | pass (4,787) | L1 (352) | L1 (542) | L1 (732) | pass (1,024) | pass (5,106) | pass (15,828) |
| V1-no-per_upload_keys+create_only | pass (82) | pass (190) | pass (367) | pass (566) | pass (240) | pass (392) | pass (544) | pass (172) | pass (249) | pass (321) | pass (558) | pass (2,396) | pass (6,430) |

### Two holders (H1 and H2 both hold F; exercises the dedup-hit path with content receipts)

| Variant | none | device | leak | fault | cloud |
|---|---|---|---|---|---|
| V0-ADR-0001-literal | S1 (61) | b1: S1,SL,L1 (159); b2: S1,SL,S3,L1 (611) | b1: S1,SL,S3,L1 (305); b2: S1,SL,S3,L1 (722) | b1: S1,SL,L1 (100); b2: S1,SL,L1 (105) | b1: S1,SL,S3 (662); b2: S1,SL,S3 (3,434) |
| V1-proposed | pass (35,322) | b1: pass (71,118); b2: pass (142,260) | b1: pass (284,671) | b1: pass (86,549); b2: pass (150,063) | b1: pass (126,873); b2: pass (971,688) |
| V1+create_only | pass (35,451) | b1: pass (71,367) | b1: pass (179,407) | b1: pass (87,387) | b1: pass (131,349) |
| V1-no-per_upload_keys | pass (9,478) | b1: pass (19,659) | b1: pass (38,215) | b1: pass (20,044) | b1: pass (37,544) |
| V1-no-receipts | S1 (48) | b1: S1 (131) | b1: S1 (197) | b1: S1 (72) | b1: S1,SL (482) |
| V1-no-pinned_trust | pass (35,322) | b1: pass (71,118) | b1: pass (284,671) | b1: pass (86,549) | not run |
| V1-no-ttl | pass (325) | b1: L1 (329) | b1: pass (2,968) | b1: pass (1,275) | b1: pass (1,062) |
| V1-no-staged_state | pass (35,613) | b1: pass (71,679) | b1: pass (287,328) | b1: pass (88,013) | b1: pass (134,249) |
| V1-no-reset_on_reject | pass (35,322) | b1: pass (71,118) | b1: pass (284,931) | b1: pass (86,549) | b1: pass (127,329) |
| V1-no-requery | L1 (73) | b1: L1 (181) | b1: L1 (306) | b1: L1 (103) | b1: pass (502) |
| V1-no-attribution | pass (35,322) | b1: pass (71,118) | b1: S3 (315,862) | b1: pass (86,549) | b1: S3 (139,073) |
| V1-no-homelab_verify | pass (35,322) | b1: pass (71,118) | b1: S1,SL,S2,L1 (304,204) | b1: pass (86,549) | b1: S2 (125,960) |
| V1-no-registry_auth | pass (35,322) | b1: pass (71,118) | b1: pass (284,671) | b1: pass (86,549) | b1: pass (138,655) |
| V1-no-reconcile_missing | pass (35,322) | b1: pass (71,118) | b1: pass (284,671) | b1: L1 (86,549) | b1: pass (126,873) |
| V1-no-per_upload_keys+create_only | pass (9,060) | b1: pass (18,541) | b1: pass (22,778) | b1: pass (19,820) | b1: pass (36,930) |

`V1-no-pinned_trust` against `cloud` with two holders was stopped at 6.3 GB of memory and not rerun; the one-holder runs above show its S1/SL failure.

### Pairwise ablations (one holder, attacker budget 2)

| Removed from V1 | device | leak | fault | cloud |
|---|---|---|---|---|
| reset_on_reject + reconcile_missing | pass | **L1** | **L1** | pass |
| ttl + reconcile_missing | **L1** | pass | **L1** | pass |
| ttl + reset_on_reject | **L1** | pass | pass | pass |
| staged_state + per_upload_keys | pass | pass | pass | pass |
| per_upload_keys + attribution | **S3** | **S3** | pass | **S3** |

Junk injection (not one of the five properties): with the malicious cloud, budget 2, the number
of reachable states in which a cloud-signed object is committed to the store is **0 of 5,106** for
V1 and **1,214 of 7,013** for `V1-no-registry_auth`. (The model lets the cloud compute G's dedup
ID, i.e. it assumes the secret has leaked; without the secret the injected object fails the HMAC check.)

### Shortest counterexamples (one holder, budget 2)

| Variant / attacker | Property | Trace |
|---|---|---|
| V0 / device | SL | M claims F's ID → H1 asks, gets "pending" (not missing, so no URL) and counts F as done → M never uploads. **Claim squatting = silent loss** |
| V0 / device | S3 | M's claim lapses → H1 claims `staging/<id>` → M, whose URL for the same key is still valid, PUTs G there → homelab rejects and blames H1 |
| V0 / fault | SL | H1 uploads, counts done → the staged object vanishes → nothing ever re-uploads |
| V0 (two holders, scenario SC-3) | SL | H1 uploads; homelab offline past the TTL; M claims the same key and overwrites with G (last writer wins); homelab rejects; F lost, both devices green |
| V1-no-receipts / leak | SL | H1 uploads and counts done → leaked URL overwrites with G → rejected; nobody re-uploads |
| V1-no-pinned_trust / cloud | S1 | Cloud relays a receipt signed with its own key; the device, which learned the receipt key from the Worker, goes green |
| V1-no-ttl / device | L1 | M claims and never uploads; the claim never lapses |
| V1-no-requery / leak | L1 | H1's object is overwritten and rejected; H1 waits for a receipt forever (visible, but never recovers) |
| V1-no-reconcile_missing / fault | L1 | The staged object vanishes; the claim stays "staged" forever and H1 gets "pending" forever |
| V1-no-attribution / leak | S3 | A leaked URL overwrites H1's object; the homelab blames H1 |
| V1-no-homelab_verify / device | S2 | M's G is committed under F's ID (duplicate faking succeeds) |

### Named scenarios (`scenarios.py`, replayed through the same transitions; `evidence/scenarios-output.txt`)

| Scenario | V1 (proposed) | V0 (ADR literal) |
|---|---|---|
| SC-1 poisoning by an enrolled device | Rejected on the first ingest, M flagged `signed-bad-content`, claim reset, H1 re-uploads, H1 then H2 (dedup hit) green | H1, H2 green; F never stored (silent loss) |
| SC-2 squatting | H1 waits, claim lapses after the TTL, H1 uploads, green | Both green; F never stored |
| SC-3 overwrite after TTL with homelab offline | The staged claim does not lapse; H2 gets "pending". Without `staged_state`, M's poison lands on its own key and is rejected; H1's copy commits | Silent loss (above) |
| SC-4 leaked URL | Rejected as `tamper-in-transit` (nobody blamed), H1 re-uploads, green | H1 blamed; silent loss |
| SC-5 cloud says "already have it" | Not green; requery | Green without data |
| SC-6 cloud forges a receipt | Not green | With an unpinned key: green without data |
| SC-7 cloud deletes the staged object | Not green; stays visibly pending (availability loss only) | Green without data |
| SC-8 staged object lost by an honest cloud | Re-claimable; H1 re-uploads, green | (V1 without `reconcile_missing`: pending forever) |

## What this means

1. **ADR-0001 §4 as literally written fails the pass criterion.** Squatting alone, poisoning,
   overwrite after a TTL lapse, a leaked URL, a lost staged object and a lying cloud each produce
   silent loss in the model. The root cause is that a device stops caring about a file on an
   unauthenticated cloud answer. **A protocol change is required** (OD-04).
2. **V1 passes** every property against every attacker within the bounds (one holder to budget 3,
   two holders to budget 2 for V1 against device, fault and cloud; see the two-holder table for
   what completed). Poisoning is detected on the first ingest cycle, the poisoner is the one flagged,
   and the genuine holder re-uploads with no human step: the D4-S1 criteria hold in the model.
3. **Load-bearing mitigations** (removing one breaks a property):
   - homelab re-verification after decryption (S2): the only defence against duplicate faking, and
     it does not depend on the dedup secret staying secret;
   - receipts (S1/SL) and a pinned receipt key (S1 against the cloud);
   - device requery after a timeout (L1). With two holders it is needed even with **no attacker**:
     the second device is told "pending" while the first uploads and, without requery, waits for ever
     (`V1-no-requery` / `none`, two holders);
   - claim TTL (L1 against squatting);
   - a way out of a stuck staged claim: reconcile a vanished staged object as missing, or reset the
     claim on rejection (together; either alone suffices only for some attackers);
   - signed-record attribution, or per-upload keys, so the homelab blames the right device (S3).
4. **Not load-bearing in this model:** per-upload staging keys, create-only PUT, and the "staged"
   claim state. With receipts, requery and reset, an overwrite only costs a re-upload. They still
   matter for reasons outside the model: multipart parts from two writers on one key mix
   (last-writer-wins per part, R2 consistency docs), the resume design binds parts to one UploadId
   and one payload key (T1 §8.5), and each overwrite forces a re-upload (griefing cost; not
   quantified here). Keep them, but do not rely on them for integrity.
5. **A second holder can mask a loss.** `V1-no-receipts` shows silent loss against `leak` and
   `fault` with one holder but only S1 with two, because H2's later upload stores F anyway. The
   one-holder runs are therefore the ones that decide the pass criterion.
6. **Device registry authentication** is not needed for integrity (poisoning fails regardless), but
   without it a cloud that holds the dedup secret can commit its own junk to the keep-forever store.

## Requirements to hand to A3 and C1 (from this spike)

Stated as protocol rules; the analyst numbers them as SR-xx in the register.

1. A device shows an item as safe only on a homelab-signed receipt that verifies under the kit-pinned
   key and binds device_id, dedup_id, size and the metadata hash. No cloud answer (present, pending,
   committed, Complete = 200) ever ends in green.
2. "Already present" counts only with a valid receipt for that content; the device still sends its
   own record and waits for its own receipt.
3. Every item that is not green is re-asked after a timeout, for ever, with back-off; and its state
   is visible to the user and the admin.
4. Claims expire while `claimed`. A `staged` claim does not expire on a timer (homelab outages outlast
   any TTL), but becomes re-claimable when its staged object no longer exists or the homelab rejects it.
5. A rejection resets only the rejected upload's own claim; a committed ID is never downgraded.
6. The homelab decrypts, recomputes HMAC and SHA-256, and checks the header MAC against the
   device-signed record before commit. The first verified copy wins; later ones are dropped.
7. Blame goes to a device only when its own valid signed record matches the rejected object
   (header MAC); anything else is "tamper in transit" and alerts the admin without blaming anyone.
8. Staging keys are per upload and never presigned for an existing key; use create-only writes if
   C1-S1 shows R2 enforces them; but correctness must not depend on either.
9. Device signing keys reach the homelab through a channel the cloud cannot forge (D1-S1 RC-5).

## Limits

- Small bounds: one file, two honest devices, one attacker at a time, budget ≤ 3 (one holder) or ≤ 2
  (two holders), TTL = 2 ticks, 3 distinct keys per device. Bigger configurations (A3-S1: 3 devices ×
  3 items, crashes, duplicated messages) belong to the A3 model.
- R2 is abstract. Whether R2 enforces a signed If-None-Match on presigned PutObject and on
  CompleteMultipartUpload is unknown; C1-S1 [SB] must answer it. Multipart part mixing is not modelled.
- Liveness is "can still recover" (EF from every state), not "will recover under every fair
  schedule"; timeouts are nondeterministic, so a device may time out early (over-approximation).
- Costs (extra uploads, time to recover against BUD-TTS) are not measured.
- The malicious cloud's lies are unbounded but its object actions are budgeted.

## Reproduce

```sh
python3 -m venv .venv && .venv/bin/pip install cryptography
HOLDERS=1 .venv/bin/python model.py 3          # all variants x attackers, one holder, budget 3 (~1 min)
.venv/bin/python model.py 1                    # two holders, budget 1 (about an hour on 4 vCPU)
.venv/bin/python model.py 2 V1-proposed device,fault,cloud
.venv/bin/python scenarios.py
HOLDERS=1 .venv/bin/python pairs.py
.venv/bin/python render.py <results json files>   # Markdown matrix + counterexamples
```

## Addendum (2026-10-06, synthesis stage): charitable ADR-0001 baseline

The skeptic review pointed out that V0 fills ADR-0001's gaps with "off", so a device counts a file
done after "pending" or after its own PUT. That makes V0 fail even with no attacker. A charitable
variant was therefore run, `V0c-charitable`. The device is green only when the Worker reports
"committed", and it re-asks otherwise. Reset-on-reject and reconcile-missing are on. Receipts and
per-upload keys are off. Patch and results: `evidence/v0-charitable/`.

| Attacker | One holder, budgets 1–3 | Two holders, budget 1 |
|---|---|---|
| none | pass | pass |
| device | pass at budget 1; S3 at budgets 2–3 | pass |
| leak | S3 | S3 |
| fault | pass | pass |
| cloud | S1, SL, S3 | S1, SL, S3 |

Read item 1 of "What this means" with this correction. Under the charitable reading, ADR-0001 §4
loses data only to a malicious control plane, and it blames honest devices (S3) for a leaked URL or
another device's poison. The honest-cloud silent-loss traces above come from V0's defaults, which
ADR-0001 does not state. The protocol change is still required, because of the cloud attacker.
