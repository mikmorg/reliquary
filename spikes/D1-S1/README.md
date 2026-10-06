# Spike D1-S1: malicious-cloud tabletop (THROWAWAY evidence)

> Throwaway research code and a tabletop record. The code is not production code.
> The research note and the threat register (`docs/security/threat-model.md`) are written by the
> D1 analyst from this evidence; this folder holds only the spike output.

- **Spike:** D1-S1 (workstream D1, `docs/research/PLAN.md` Track D). Exec tag **CT**.
- **Run by / date:** D1 spike runner (agent), 2026-09-29, cloud container (x86-64, Python 3.11, Go `age` 1.1.1).
- **Hypothesis (PLAN):** every value that crosses Cloudflare is either verified with a key the cloud
  lacks, or recorded as a required change. Expected changes: per-upload staging keys, homelab-signed
  receipts, a pinned homelab key, device-signed manifests, dedup secret delivered encrypted by the homelab.
- **Decision informed:** OD-04 (supersede details of ADR-0001 §4). Also feeds A3 (ADR-0009), C1 (ADR-0010),
  D2 (ADR-0008), D3 (ADR-0014, OD-05), A8 (ADR-0028), D5 (ADR-0015), D6/OD-03.
- **Pass → / fail →:** pass = every value classified; each unauthenticated value either becomes a required
  change (RC below) or an accepted risk proposed to the owner (OD-17). Fail = a value that can be neither.
- **Budget IDs cited:** BUD-REVOKE (only as context: see V-25). No other budget applies to a tabletop.
- **Data-handling class:** SYN → results (all inputs are generated in the run; no family data).
- **Attacker:** a fully malicious control plane: Workers, D1/Durable Objects, Queues, R2, the
  Cloudflare-hosted email path and Cloudflare's audit logs, all controlled by one party (account
  takeover, insider, or legal compulsion). It holds everything Cloudflare would hold under ADR-0001/0002
  as accepted: public keys, opaque IDs, ciphertext, invite hashes, account names and emails, and every
  value it relays. It does **not** hold the homelab private keys, device private keys or (unless a
  row says so) the family dedup secret.

## Method

1. Listed every value that crosses Cloudflare in ADR-0001, ADR-0002, `docs/research/content-encryption-format.md`
   (T1 spike 2: the current proposal) and the C1 plan text (bootstrap config, server time).
2. For each value: what the accepted ADRs say, what a malicious cloud can do with it, whether the
   proposed design authenticates it end to end with a key the cloud lacks, and the required change.
3. Checked the load-bearing claims by execution, not by argument:
   - `demos.py`: real `age` CLI and real Ed25519/HMAC. Each attack has an expected outcome; the run
     fails if any observed outcome differs. Output: `evidence/demos-output.txt`, `evidence/demos-results.json`.
   - The protocol model in `../D1-S2/model.py` with the `cloud` attacker (lies about claim state,
     deletes and swaps staged objects, injects objects, forges and replays receipts). Results are in
     `../D1-S2/evidence/`.
4. Primary sources re-read for this run (fetched 2026-09-29 from the `cloudflare/cloudflare-docs`
   production branch and C2SP `main`; developers.cloudflare.com itself is blocked from this container):
   - R2 presigned URLs: "authorizing anyone with the URL", expiry "1 second to 7 days (604,800 seconds)",
     "The same presigned URL can be reused multiple times until it expires", "Treat presigned URLs as
     bearer tokens" — <https://raw.githubusercontent.com/cloudflare/cloudflare-docs/production/src/content/docs/r2/api/s3/presigned-urls.mdx>
   - R2 consistency: "the last writer to complete 'wins'"; R2 permission changes on an API key "may take
     up to a minute" — <https://raw.githubusercontent.com/cloudflare/cloudflare-docs/production/src/content/docs/r2/reference/consistency.mdx>
   - R2 S3 compatibility: PutObject lists If-None-Match; the CompleteMultipartUpload row lists no
     conditional headers; Object Lock headers unsupported — <https://raw.githubusercontent.com/cloudflare/cloudflare-docs/production/src/content/docs/r2/api/s3/api.mdx>
   - R2 temporary credentials: per-action scoping (Write = PutObject, DeleteObject, DeleteObjects,
     CopyObject) "currently supported via local signing only" — <https://raw.githubusercontent.com/cloudflare/cloudflare-docs/production/src/content/docs/r2/api/s3/temporary-credentials.mdx>
   - R2 event notifications: object-create fires on PutObject, CopyObject, CompleteMultipartUpload,
     "or existing objects are overwritten" — <https://raw.githubusercontent.com/cloudflare/cloudflare-docs/production/src/content/docs/r2/buckets/event-notifications.mdx>
   - age v1: header MAC key = HKDF-SHA-256(ikm = file key, info = "header"); an "expectation of
     authentication" is stated only for the scrypt stanza — <https://raw.githubusercontent.com/C2SP/C2SP/main/age.md>
   - Other sources used by the tabletop come from the D1 scout set (Tailnet Lock source, restic, Borg,
     Tahoe-LAFS, Kopia, Ente); the analyst's note carries their full citations. Blocked primary sources
     (tailscale.com prose, words.filippo.io, eprint.iacr.org, linddun.org) were **not** replaced by
     secondary ones here; nothing below depends on them.

## Executable checks (`demos.py`, all 15 matched their expected outcome)

| ID | Attack by the malicious cloud | Observed |
|---|---|---|
| A1 | Makes a content object for the homelab key with no device secret | `age -d` succeeds (exit 0). Encryption to the homelab key proves nothing about origin |
| A2a | Substitutes the homelab recipient; device has no pin | Cloud decrypts the device's upload |
| A2b | Same, device compares SHA-256(trust bundle) with the kit pin | Refused |
| A3a | Learns the dedup secret in transit; tests a known file against the ID index | Confirmed |
| A3b | Dedup secret + ID index; brute-forces a 6-digit field of a 1,001-byte templated document | Recovered after 482,914 HMACs in 2.83 s, one core, CPython (see `evidence/demos-output.txt`) |
| A3c | Secret sealed to the device X25519 key and homelab-signed; cloud tries to read and swap | Cannot read; swap detected; device reads |
| A4a–d | Forged receipt (own key); H1's receipt replayed to H2; receipt for another file; edited size | All rejected |
| A4e | Genuine receipt, right device and file | Accepted |
| A4f | Device takes the receipt key from the Worker (no pin); cloud forges | **Accepted**: the pin is load-bearing |
| A5a | Substitutes H1's restore key; homelab re-encrypts a restore to it | Cloud decrypts the restore |
| A5b | Homelab admits device keys only with a signature from a key the cloud lacks | Substitute refused; genuine admitted |
| A6 | Holds a fast hash of a 50-bit invite code | Measured 1,024,717 SHA-256/s on one CPython core ⇒ 2^50 ≈ 35 core-years. GPU rates were **not** measured and are far higher; this is a floor, not a safety margin |

Protocol-level results with the `cloud` attacker (model in `../D1-S2/`): with receipts and a pinned
key, no reachable state shows a device green while the homelab lacks the file (S1), and the store
never holds content under a foreign ID (S2). Without the pin (`V1-no-pinned_trust`) or without
receipts (`V0`), S1 fails. Availability does not hold and is not claimed: the cloud can delete,
withhold and lie forever, and the device then stays visibly "not safe" (scenarios SC-5, SC-7).

## Value inventory (the tabletop record)

"E2E?" = is the value authenticated end to end with a key the cloud lacks, in the **proposed**
design (T1 spike 2 plus the required changes below)? "RC" = required change; "AR" = candidate
accepted risk for the owner (OD-17 or the named OD).

| # | Value (direction) | ADR-0001/0002 as accepted | What a malicious cloud does with it | E2E? | Required change / disposition |
|---|---|---|---|---|---|
| V-01 | Homelab age recipient (cloud → device) | Delivery not specified | Substitutes its own key; reads every later upload (A2a) | Yes, with pin (A2b) | **RC-1** pin SHA-256 of the trust bundle in the invite QR / USB kit; never learn it from the Worker (T1 D-9) |
| V-02 | Homelab receipt/signing public key (cloud → device) | Not in ADR | Substitutes; forges receipts (A4f) | Yes, with pin | RC-1 |
| V-03 | Trust-bundle rotation (cloud → device) | Not specified | Pushes its own bundle as a "rotation" | Only if signed by the pinned or an offline admin key | **RC-2** rotation signed by an offline admin key (D2) |
| V-04 | Family dedup secret (→ device) | Delivery not specified | If relayed in clear: confirms files and fills in templated documents for every ID it has ever seen (A3a, A3b); breaks ADR-0001's "the cloud cannot test for known files" | Yes if sealed by the homelab to the device X25519 key and homelab-signed (A3c), or carried in the kit | **RC-3** never through the Worker in clear. Sealing depends on V-06 being authentic; kit carriage makes the kit a secret (E5/D3 trade-off) |
| V-05 | Invite-code redemption (device → Worker) | Worker stores a hash; one-use | The cloud is the verifier: it can create accounts and devices at will; offline search of stored hashes (A6) | No (cloud-local check) | **RC-4** the homelab never treats "the Worker enrolled it" as admission; admission is V-06. Any homelab-verified secret derived from the code needs D3's entropy analysis against GPU search |
| V-06 | Device public keys: Ed25519 signing, X25519 restore (device → cloud → homelab) | "Device generates its own keypair"; path to the homelab not specified | Substitutes the restore key (A5a: restore disclosed); registers its own signing key as a device and injects signed records (model `V1-no-registry_auth`) | Only with an admission signature by a key the cloud lacks (A5b) | **RC-5** homelab-verified device admission (Tailnet Lock analogue). Who signs (admin, homelab, an existing device) is D3 / OD-05 |
| V-07 | Per-device API credential (cloud → device) | Per-device credential | Irrelevant against a malicious cloud (it is the verifier) | n/a | None here; D3 owns it against the internet attacker |
| V-08 | Account name and email (device → cloud) | Plain text in the cloud by design | Reads, links, sells, subpoenaed | No (disclosure by design) | **AR** under OD-03 / D6 |
| V-09 | Device-to-device QR / pairing token (device → cloud → new device) | Short-lived, single-use, Worker-minted | Mints its own tokens; adds devices | No | RC-5: the enrolled device signs the new device's keys; the token alone admits nothing at the homelab |
| V-10 | Batch of dedup IDs (device → cloud) | Opaque IDs | Links who holds the same file across people, when, how often | n/a (must be visible) | **AR** + rate-limit and log presence queries (T1 R-5); LINDDUN linkability row for the register |
| V-11 | Missing / pending / present answers (cloud → device) | Only missing IDs get URLs, so a not-missing ID is skipped | "Present" or "pending" makes the device skip the file: silent loss (SC-5 on V0) | No; neutralised: "present" counts only with a homelab receipt for (dedup_id, size), and a device is green only with its own receipt | **RC-6** receipts; **RC-7** a device that is not green re-asks after a timeout |
| V-12 | Presigned upload URLs (cloud → device) | Presigned multipart URLs keyed by dedup ID | Redirects or drops the upload; a leaked URL is a reusable bearer token for up to 7 days (docs) and overwrites last-writer-wins | No; harmless only because V-13 is verified later | **RC-8** per-upload staging keys and short expiry; **RC-9** create-only writes where R2 enforces them (open: C1-S1); **RC-10** blame attribution by signed header MAC (V-13) |
| V-13 | Content ciphertext (device → R2 → homelab) | age to the homelab key; homelab verifies SHA-256 and HMAC | Injects or swaps objects (A1: anyone can make a valid age file) | Yes when the object is bound to a device-signed record by its header MAC and the homelab recomputes HMAC/SHA-256 (T1 `commit:*` tests; model S2) | **RC-11** bind each object to a device-signed record (T1 proposal, D-5) |
| V-14 | Encrypted metadata record (device → R2 → homelab) | Encrypted, not signed | Injects records for any device if it controls the device list | Yes: Ed25519 device signature inside the encryption (T1), given RC-5 | RC-11 |
| V-15 | Sizes, counts, timing, IP addresses, user agents | Visible | Reads, profiles | No | **AR**; exact-size leak is T1 D-7 (padding); D6 |
| V-16 | Claim / commit state in D1 or Durable Objects (cloud-internal) | The dedup index and claim state | Flips any state | No | RC-6: no device decision ends in green on cloud state alone |
| V-17 | R2 event notifications / Queue messages (cloud → homelab) | Notification path; homelab also reconciles | Withholds, replays, forges (Cloudflare originates them) | No | **RC-12** hints only; every object is verified; ingest is idempotent |
| V-18 | Listing of pending objects for reconciliation (cloud → homelab) | Homelab lists pending objects | Hides objects | No | RC-12 + RC-7 (the device's receipt timeout is the independent detector) |
| V-19 | Staged object bytes pulled by the homelab | Verified after decrypt | Tampering is rejected | Yes (V-13) | None beyond RC-11 |
| V-20 | "Committed" status written by the homelab (homelab → cloud) | Homelab marks committed | Flips it | No | RC-6 |
| V-21 | Commit receipts (homelab → cloud → device) | Not in ADR | Forges, replays, edits: rejected (A4a–d); withholds: device stays visibly not safe | Yes: Ed25519 under the pinned key, bound to device_id, dedup_id, size, meta_sha256 | RC-6 with RC-1 |
| V-22 | Staged-object delete (homelab → R2) | After commit | Deletes earlier, before the pull (SC-7) | n/a (availability) | **RC-13** a staged claim whose object is gone becomes re-claimable (model `reconcile_missing`; SC-8) |
| V-23 | Target device identity for a restore | Re-encrypt to "the requesting device's own public key" | Substitutes the key (A5a) | Only with RC-5 | RC-5 |
| V-24 | Restore objects (homelab → R2 → device) | age to the device key, expiring prefix | Injects its own files into a restore (age has no sender authentication) | Only with a homelab-signed restore manifest | **RC-14** homelab-signed restore manifest with per-file hashes (A8) |
| V-25 | Revocation (admin → cloud) | Admin revokes | Ignores it; R2 key permission changes are eventually consistent, up to a minute (docs), against BUD-REVOKE (60 s) | No | **RC-15** the homelab keeps its own revocation list and refuses records from revoked keys; the cloud's revocation is defence in depth only |
| V-26 | Health status and nudge emails computed by the Worker | Nudges by email from activity timestamps | Suppresses warnings, sends "all good", or phishes | No | **RC-16** device-side health comes from receipts only; the email nudge is advisory (E3, C3) |
| V-27 | Server time (cloud → device) | C1 plan: a server-time header | Skews TTLs and "last backed up" | No; the receipt's committed_at is homelab-signed | RC-16: only homelab-signed times feed health |
| V-28 | Bootstrap config, hostnames, minimum client version (cloud → device) | C1 plan | Forces "update required"; redirects endpoints | No | **RC-17** no key, secret or trust decision may come from unsigned config |
| V-29 | Self-update artifacts, if served through Cloudflare | Signed with the project key (ADR-0002 §5) | Cannot substitute; can withhold or roll back | Integrity yes; freshness no | **RC-18** anti-rollback (monotonic version in signed metadata); D5 |
| V-30 | Cloudflare audit logs | Held by Cloudflare; retained 18 months ([audit-logs.mdx](https://raw.githubusercontent.com/cloudflare/cloudflare-docs/production/src/content/docs/fundamentals/account/account-security/audit-logs.mdx), fetched 2026-09-29) | Rewrites or omits | No | **RC-19** the audit trail the family relies on lives at the homelab: a homelab-signed append-only receipt log (A3 chooses per-file vs Merkle checkpoint) |
| V-31 | USB bundle manifest (does not cross Cloudflare; same format) | Unsigned | n/a to the cloud; postal interception | Needs a device signature | RC-11 extended to the manifest (A4) |
| V-32 | Dedup-secret rotation | Not specified | As V-04 | As V-04 | RC-3 |

**Count:** 32 values. In the proposed design with RC-1…RC-19:

- 13 are authenticated end to end, most only once their RC lands: V-01, 02, 03, 04, 06, 13, 14, 19, 21, 23, 24, 31, 32.
- 14 stay unauthenticated and are made harmless by an RC (no device or homelab decision rests on
  them alone): V-05, 09, 11, 12, 16, 17, 18, 20, 22, 25, 26, 27, 28, 30.
- 1 is integrity-only (V-29: no freshness).
- 3 are disclosures the cloud necessarily sees (V-08, V-10, V-15: AR candidates).
- 1 is cloud-local (V-07).

None is left unclassified.

## What holds under each compromise (input to the register)

**(a) Fully malicious control plane**, with RC-1, RC-3, RC-5, RC-6, RC-11:

- Holds: confidentiality of content and metadata; integrity of the homelab store (S2 holds in every
  model variant that keeps homelab re-verification); "green means verified at home" (S1).
- Does not hold, by design: availability (it can delete, withhold and lie indefinitely; devices stay
  visibly not safe, and USB is the fallback path); metadata privacy (V-08, V-10, V-15); cloud-side
  revocation, nudges and audit logs (V-25, V-26, V-30); account creation (V-05).
- Without RC-1, RC-3 or RC-5, confidentiality fails outright (A2a, A3a, A5a).

**(b) One device plus the dedup secret** (details in D1-S2):

- Poisoning fails at the homelab even though the attacker holds the secret: tag consistency comes from
  re-verification after decryption, not from secrecy of the secret.
- Squatting and overwrite cost delay only, given claim TTLs, requery and receipts.
- Disclosure does **not** hold: the device plus the Worker's presence answers form a
  confirmation-of-a-file oracle over the family's IDs, and templated documents can be filled in (A3b).
  T1 already proposes rewording ADR-0001's property (D-6) and rate-limiting presence queries (R-5).
- The device can upload junk forever (keep-forever amplifies storage cost): quotas and the ransomware
  circuit breaker (D4-S3, C2).

**(c) Compromised ingest VM:** not in D1-S1's scope. If one VM holds the decryption key, the receipt
key and write access to the store, it can read everything, sign false receipts (breaking S1 at its
root) and poison the store. Recorded as a Wave 2 register item for A6, D2 and D4-S4 (separation of
the receipt key and of store write rights).

## Required changes to carry forward

| RC | Change | Changes accepted text? | Owner |
|---|---|---|---|
| RC-1 | Pin the trust bundle (homelab recipient + receipt key) from the kit | No (fills a gap) | D3, E5; T1 D-9 |
| RC-2 | Trust-bundle rotation signed by an offline admin key | No | D2 |
| RC-3 | Dedup secret never in clear through the Worker; sealed to the device key and homelab-signed, or in the kit | No (fills a gap) | D2, D3 |
| RC-4 | Worker enrollment is not admission | No | D3 |
| RC-5 | Homelab-verified device admission (signature chain the cloud cannot make) | Possibly: ADR-0002 §3 "adding devices never requires the admin" (OD-05) | D3 |
| RC-6 | Homelab-signed receipts; green only with a receipt; "present" needs a receipt | **Yes**: ADR-0001 §4 (OD-04) | A3 |
| RC-7 | Requery after timeout for every not-green item | Yes: ADR-0001 §4 (OD-04) | A3 |
| RC-8 | Per-upload staging keys, short URL expiry | **Yes**: ADR-0001 §4 "objects are keyed by dedup ID" (OD-04) | A3, C1 |
| RC-9 | Create-only writes where R2 enforces them | No | C1-S1 decides |
| RC-10 | Blame attribution by signed header MAC | No | A3, D4 |
| RC-11 | Object bound to a device-signed record; signed USB manifest | Yes: ADR-0001 §4 step 3 (OD-04) | A2, A4 |
| RC-12 | Queue and listings are hints only | No (ADR-0001 already reconciles) | A3, C1 |
| RC-13 | A staged claim whose object vanished becomes re-claimable | No | A3, C1 |
| RC-14 | Homelab-signed restore manifest | No | A8 |
| RC-15 | Homelab-side revocation list | No | D3 |
| RC-16 | Device health from receipts and homelab-signed times only | No | E3, A3 |
| RC-17 | No trust decision from unsigned bootstrap config | No | C1 |
| RC-18 | Update anti-rollback | No | D5 |
| RC-19 | Homelab-held, signed, append-only receipt log as the audit trail | No | A3 |

## Result against the pass criterion

**Pass.** All 32 values are classified. Every value the proposed design does not authenticate end
to end is either neutralised by a required change (RC-1…RC-19, four of which touch ADR-0001 §4 and
go to OD-04) or proposed as an accepted disclosure (V-08, V-10, V-15). The PLAN's five expected
changes are all confirmed as necessary by execution: per-upload keys (RC-8, D1-S2 ablation), homelab-signed
receipts (RC-6; A4, SC-5), a pinned homelab key (RC-1; A2, A4f), device-signed records (RC-11; A1),
and a homelab-sealed dedup secret (RC-3; A3).

## Limits

- No real Cloudflare: the malicious cloud is modelled from primary docs, not observed. Whether R2 enforces
  a signed If-None-Match on presigned PUT and on CompleteMultipartUpload is unknown (C1-S1, [SB]).
- The protocol model is small (2 honest devices, 1 file, attacker budget ≤ 2); see D1-S2's limits.
- A6 is a CPython single-core floor, not an attacker estimate.

## Reproduce

```sh
python3 -m venv .venv && .venv/bin/pip install cryptography   # system cryptography was broken in this container
.venv/bin/python demos.py        # needs age and age-keygen on PATH; writes results.json
```
