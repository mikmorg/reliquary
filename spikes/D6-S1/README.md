# Spike D6-S1: minimal-PII variant (EMULATED, not real R2/Cloudflare)

> Throwaway research code. It is not production code. The D6 analyst writes the research note
> (`docs/research/d6-od03-where-email-lives.md`) from this evidence. The real-sandbox run is a kit:
> `docs/research/kits/D6-S1/`.

- **Spike:** D6-S1 (workstream D6, `docs/research/PLAN.md` Track D). Exec tag **SB**. This run is the
  **local-emulator variant**. It used no Cloudflare account, no real D1, R2 or Email Service, and sent no real email.
- **Run by / date:** D6 spike runner (agent), 2026-09-29, cloud container (x86-64, Python 3.11, Node 22,
  wrangler 4.143.0 with Miniflare 5.20260926.0-alpha, Go `age` 1.1.1).
- **Hypothesis:** the homelab can hold the only copy of names and email addresses (the roster), compute
  staleness from the commits it receives, and send nudges through the provider's REST API. D1 then holds
  no name or email, and nudges still go out within 24 h of a device becoming stale.
- **Decision informed:** OD-03 (where email lives), ADR-0027. It also feeds ADR-0026 (C3), ADR-0025 (E3) and the
  C7 dead-man's switch.
- **Pass / fail (PLAN):** pass means D1 holds no email or name **and** nudges still arrive within 24 h of staleness
  → Option B (homelab-only roster). Fail → Option A (roster in D1, with the EU jurisdiction chosen at creation
  if needed, and Email preview off).
- **Budget IDs cited:** BUD-TTS (the 24 h figure in the pass criterion is PLAN's own, not a BUD-TTS number:
  BUD-TTS is "stored at home within 24 h", so it is cited only as the time-to-safe context), BUD-SUPPORT (not
  measured here; the kit records owner hands-on time).
- **Data-handling class:** `SYN → results`. Every person, address and device is synthetic
  (`zz-d6s1-*@example.invalid`, "Zz… Synthperson"). The age identities made during the run were deleted and are not in the repo.

## What was built

| Part | File | What it does |
|---|---|---|
| Control plane (Worker) | `worker/src/index.js`, `worker/migrations/0001_init.sql`, `worker/wrangler.jsonc` | Invites (stores only the SHA-256 of the code), redeem, add device, heartbeat, commit, encrypted inbox, homelab pull and ack, and a dead-man's-switch cron. **The schema has no name, email or device-name column.** A roster entry or verification code is accepted only if it starts with the age header (`age-encryption.org/v1`), so plaintext is refused. Timestamps are floored to `TIME_GRANULARITY_S`, which defaults to 1 h. |
| Owner alert | `send_email` binding `OWNER_ALERT` with `destination_address` | The only address on the cloud side. It lives in the Worker config, not in D1. |
| Homelab job | `homelab.py` | Makes outbound calls only. Pulls commits, last-seen times and age blobs, decrypts them with the homelab identity, and keeps the roster in a local SQLite. Sends a 6-digit verification code, and nudges once per staleness episode (Healthchecks-style timeout) to verified people only. Sends in the Cloudflare Email Service REST shape (`POST /client/v4/accounts/{id}/email/sending/send`, from `rest-api.mdx`). |
| Mock email API | inside `run_spike.py` | Local HTTP mock of that REST endpoint. It records requests and returns the documented success shape. It does **not** show anything about Cloudflare's real behaviour. |
| Scenario driver | `run_spike.py` | Runs a 26-day scenario on a simulated clock, with the homelab job and the dead-man's-switch check each hour. There are 4 synthetic people and 5 devices, and a homelab outage of 54 h. Afterwards it scans every local cloud-side store for the synthetic names and addresses. |

Two ways of getting the roster to the homelab were exercised: **R**, where the device encrypts `{name, email, device kind}` to the homelab key at
redemption, and **A**, where the admin enters the name and email at the homelab when making the invite, so the cloud never carries them at all.

## Results (`evidence/results.json`; emulated)

| Check | Result |
|---|---|
| D1 app tables and columns | `invites(invite_id, code_hash, expires_at, state, account_id)`, `accounts(account_id, created_hour)`, `devices(device_id, account_id, token_hash, pubkey, enrolled_hour, last_seen_hour, last_commit_hour)`, `commits(seq, device_id, object_id, committed_hour)`, `meta(k, v)`. No column name matches `name/mail/phone/addr/person/label`. |
| Synthetic family names or addresses in the D1 dump (`evidence/d1-export.sql`) | **None** (0 of 17 markers) |
| … in any file under the local cloud state (D1 and R2 SQLite and blobs, cache, observability store) | **None** |
| … in the `wrangler dev` output, in Miniflare's local observability store (2,930 log rows; the span query returned its 10,000-row cap), and in the owner-alert email file | **None** |
| Positive control: the same scan on the homelab `roster.db` | 17 of 17 markers found, so the scan does detect them |
| Owner address in D1 | None. It exists only in `wrangler.jsonc` (binding and emulator variable). |
| Worker refuses a plaintext roster blob | Yes (HTTP 400 `roster_blob_must_be_age_ciphertext`) |
| Emails sent by the homelab | 4 verification codes and 3 nudges. The unverified person got no nudge, per ADR-0002 §2. |
| Nudge delay, homelab up: beta-laptop (online, backups failing) | Stale 2026-10-22T21:00Z, nudged 2026-10-22T21:00Z, **0 h** in simulated time |
| Nudge delay, homelab up: gamma-phone (admin-entered roster, path A) | Stale 2026-10-27T12:00Z, nudged 2026-10-27T12:00Z, **0 h** in simulated time |
| Nudge delay, homelab down when the device went stale: alpha-phone | Stale 2026-10-25T14:00Z, nudged 2026-10-27T06:00Z, **40 h** (the nudge waited for the homelab to come back) |
| Dead-man's switch during the outage | Fired once at 2026-10-25T05:00Z, after 6 h of silence (`DMS_HOURS=6`), to the owner only. The alert text says only how long the server has been silent. |
| `destination_address` pin, local simulator | A send to another address was refused (`email to … not allowed`) |
| Wall-clock time for the 26 simulated days | 60.5 s, about 3,494 Worker requests (last run) |

**PLAN criterion, emulated:** *D1 holds no email or name*: **pass**. *Nudges arrive within 24 h of staleness*:
**pass while the homelab is up** (the delay is bounded by the homelab job interval, 1 h here). It is **not met while the homelab is down**:
40 h in this scenario, and in general the length of the outage. The cloud dead-man's switch alerted the owner within its 6 h threshold instead.
Overall, emulated: **pass, with the documented outage exception.** That is what the analyst's F4 item 3 predicted.

### What this emulation does not show (the kit must)

- Real Cloudflare: D1 at rest, R2, Workers Logs, and the Email Service Activity log, preview and suppression list. The note's C6–C8
  says those keep recipient addresses **regardless of** where the roster lives.
- Real delivery time from the REST call to the inbox. The "0 h" above is simulated time from the job tick to the mock, not delivery.
- Whether an API token can be limited to Email Sending only (C18), and C11 (recipient scope of an unrestricted binding).
- Request metadata the real platform attaches (client IP, `cf` object). The local `Request.cf` is a placeholder.

### Surprises

1. **Emulator discrepancy.** `send-bindings.mdx` says that with `destination_address` set, calling `send()` with `to`
   `undefined` uses the configured address. Miniflare 5.20260926.0-alpha instead throws
   `TypeError: Cannot read properties of undefined (reading 'email')` from `extractEmailAddress` (see
   `checks.local_send_with_to_omitted`). The Worker therefore passes `to` explicitly only when the emulator-only variable
   `EMULATOR_OWNER_TO` is set. The real run should test the documented default with `to` omitted.
2. **Local observability ignores the config.** `observability.logs.invocation_logs: false` was set, yet Miniflare's local
   explorer still recorded a `"<METHOD> <URL>"` message for every request. D6-S2 looks at this; the local tool is not
   evidence about hosted Workers Logs.
3. **`wrangler d1 export --local` has no `--persist-to`.** The driver dumps Miniflare's D1 SQLite file directly (`sqlite3.iterdump`).
4. The homelab also sees `last_seen_hour` for every device, so a nudge can say "switched on but not finishing a backup"
   or "not in touch" without the cloud knowing who the person is.

### Pseudonymous data that stays in D1 (for the D6 inventory)

Opaque account and device IDs, device **public** keys, hashes of invite codes and device tokens, opaque object IDs,
and times floored to the hour. None of these is a name or an address, but they are linkable per device over time. The owner address
is in the Worker's configuration, which is part of the Cloudflare account.

## How to rerun

```bash
npm install            # wrangler 4.143.0 (pulls workerd and Miniflare)
python3 run_spike.py   # about 1 min; writes evidence/ (it overwrites the committed evidence)
```

Needs the `age` and `age-keygen` CLIs, and ports 8798 and 8799 free on 127.0.0.1.
