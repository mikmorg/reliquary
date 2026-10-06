# Kit D6-S1: minimal-PII variant on the real sandbox (homelab holds the roster and sends nudges)

- **Spike:** D6-S1 (workstream D6, see `docs/research/PLAN.md`, section "D6.")
- **Exec tag:** SB (sandbox Cloudflare account and throwaway domain from H1; never production)
- **Prepared by / date:** D6 spike runner (agent), 2026-09-29
- **Who runs it:** Owner
- **Time needed:** about 1.5 h hands-on (account setup, token, DNS, typing three codes, reading inboxes), plus about 2 h of mostly unattended running
- **Data-handling class:** `LAB → results`. The "people" are the owner's own **test inboxes** with invented names, never relatives' real addresses. The results record provider domains (gmail.com etc.), times and yes/no answers only.
- **Emulated rehearsal already done:** `spikes/D6-S1/README.md` (2026-09-29). That run passed "D1 holds no name or email" and "nudge within 24 h while the homelab is up" against a local emulator and a mock email API. This kit repeats it on real Cloudflare and adds the Cloudflare-side checks the emulator cannot do.

## Purpose

To confirm on real Cloudflare that the family roster can live only at the homelab. The cloud database should hold no names or email addresses, nudges should still arrive quickly, and the owner should still be alerted when the home server goes quiet. The kit also records what Cloudflare's email service keeps about recipients anyway.

## Hypothesis

With the Worker in `spikes/D6-S1/worker` and the homelab job `spikes/D6-S1/homelab.py`:

1. An export of the D1 database contains none of the test names or addresses.
2. A nudge reaches the test inbox soon after a test device becomes stale while the homelab is up: within one homelab job interval plus delivery time, and far inside the PLAN's 24 h.
3. While the homelab is down, the cloud dead-man's switch emails the owner's verified address, and only that address.

## Decision it informs

| If the result is… | Then… |
|---|---|
| **Pass**: D1 holds no email or name, **and** nudges arrive within 24 h of staleness while the homelab is up (PLAN D6-S1) | Option B for OD-03 (homelab-only roster; ADR-0027, with ADR-0026 for the sending path). The outage behaviour, where nudges pause and the owner is alerted, goes into ADR-0025 and C7. |
| **Fail**: a name or email is found in D1, or nudges cannot be sent from the homelab | Option A (roster in D1): choose the D1 jurisdiction at creation if relatives are in the EU (one-way door, note C14), turn Email preview off, keep invocation logs off |
| **No result** (no sandbox account, Email Sending not enabled, token cannot be made) | OD-03 is decided on the emulated evidence plus the docs. The note records that the real run is outstanding. |

## Budget IDs cited

- **BUD-TTS**, for context only. The "24 h of staleness" figure is PLAN D6-S1's own pass criterion. BUD-TTS itself is "stored at home within 24 h".
- **BUD-SUPPORT**: record your hands-on minutes, so the ongoing owner cost of the roster (adding and removing people at the homelab) can be estimated.

## Equipment

| Item | Exact model or version | Why | Have it? |
|---|---|---|---|
| Sandbox Cloudflare account on **Workers Paid** (H1) | — | Email Sending needs Workers Paid (note C1) | |
| Throwaway domain on that account, with a sending subdomain such as `notify.<domain>` onboarded to Email Service | — | Sending to arbitrary recipients needs an onboarded domain (C5) | |
| 3 test inboxes you own, ideally at different providers (Gmail, Outlook.com, iCloud) | — | Nudge recipients (the "people") | |
| 1 owner **test** inbox, verified as an Email Routing destination address | — | Dead-man's-switch recipient (C10, C12) | |
| A Linux machine acting as the homelab (a VM on the homelab is fine), outbound internet only | Python 3.11+, `age` 1.1.x, Node 22 | Runs `homelab.py` through `run_real.py` | |
| A laptop with Node 22 and `wrangler` 4.143.0 | — | Deploys the Worker | |

**Software and files needed:** `spikes/D6-S1/` (Worker, migrations, `homelab.py`); in this folder: `run_real.py`, `scan_markers.py`, `wrangler.real.example.jsonc`, and the optional `c11-probe.js`.

## Before you start

- [ ] Check that `wrangler whoami` shows the **sandbox** account ID and not a production one. Write the account ID in the results.
- [ ] Make a scratch copy of `spikes/D6-S1/` outside the repo, and run `npm install` in it.
- [ ] Write `people.json` next to `run_real.py` (**do not commit it**):
  `[{"key":"p1","name":"Testa One","email":"<test inbox 1>","path":"R"}, {"key":"p2","name":"Testb Two","email":"<test inbox 2>","path":"R"}, {"key":"p3","name":"Testc Three","email":"<test inbox 3>","path":"A"}]`.
  Path R: the "device" sends the name and email encrypted to the homelab key. Path A: you enter them at the homelab and the cloud never carries them.
- [ ] Have a clock showing UTC to hand, for recording arrival times.

## Procedure

Do the steps in order. After each step, write down what you saw in the results tables, even if it looks unimportant.

**A. Email Service setup (dashboard)**

1. Onboard the sending subdomain to Email Service (Email Sending). **You should see:** a list of DNS records that Cloudflare adds. **Record** which records were created, including any on `cf-bounce` (C13).
2. Open the sending domain's **Settings** and find **Email preview**. **Record** whether it was on by default (C7 says it is on for new domains). Then switch it **off**.
3. Under Email Routing, add the owner test inbox as a **destination address** and click the verification email Cloudflare sends. **You should see:** the address shown as verified. **Record** how long the verification email took to arrive.

**B. API token for the homelab (dashboard: My Profile → API Tokens → Create custom token)**

4. In the permission picker, look for every permission whose name contains "Email". **Record** the exact names. This answers C18: does an Email-Sending-only permission exist, and can it be limited to one account or zone?
5. Create the narrowest token that can send. `smtp.mdx` names **Email Sending: Edit**. Add a **Client IP filter** set to the homelab's public IP and a **TTL** ending the day after the run. **Record** the permissions you chose.

**C. Deploy the Worker (laptop, in the scratch copy)**

6. `npx wrangler d1 create d6s1-kit`. If the family has relatives in the EU, also try `--jurisdiction eu` on a second database, `d6s1-kit-eu`. **Record** whether it works on this plan. Use one of the two for the rest of the kit.
7. `npx wrangler r2 bucket create d6s1-kit-inbox`.
8. Copy `wrangler.real.example.jsonc` over `worker/wrangler.jsonc` and fill in the `<...>` values.
9. `npx wrangler secret put ADMIN_TOKEN` and `npx wrangler secret put HOMELAB_TOKEN`, each with a fresh random value (for example `openssl rand -hex 32`).
10. `npx wrangler d1 migrations apply d6s1-kit --remote`, then `npx wrangler deploy`. **You should see:** the Worker URL. Write it down.
11. In a second terminal, run `npx wrangler tail d6s1-kit --format json > tail.json` and leave it running until step 17. This captures exceptions, for example if the dead-man's-switch send fails.

**D. Run (homelab machine)**

12. Copy `spikes/D6-S1/homelab.py`, `run_real.py` and `people.json` to the homelab machine, keeping `run_real.py`'s relative import path or adjusting `SPIKE` at the top of the file. Run:
    `python3 run_real.py --cp <Worker URL> --admin-token <ADMIN> --homelab-token <HOMELAB> --mail-base https://api.cloudflare.com --mail-account <sandbox account ID> --mail-token <token from step 5> --mail-from nudges@<sending subdomain> --people people.json --stale-min 30 --job-every-s 300 --outage-min 60 --out results-run.json`
13. The script asks for three codes. **You should see:** an email "Your Reliquary code" in each test inbox. Type each code. **Record** each email's arrival time (the `Date:`/`Received:` header, UTC) and whether it landed in the inbox or in spam.
14. Wait. Person p1's device keeps committing; p2's and p3's devices stop after one commit. About 30–35 minutes later, **you should see** "Your backup needs a look" in inboxes 2 and 3 and nothing in inbox 1. **Record** the arrival times, and the matching `homelab_sent_nudge` times from the script output.
15. The script then stops the homelab for 60 minutes. About 30–35 minutes into that, **you should see** "Reliquary: home server has not checked in" in the **owner** test inbox, and in no other inbox. **Record** the arrival time. If nothing arrives within 45 minutes, look in `tail.json` for an exception. A likely cause is the `to`-omitted default not behaving as documented, which the emulator also failed on (see `spikes/D6-S1/README.md`, surprise 1).
16. When the script ends it writes `results-run.json`. Keep it.

**E. Evidence**

17. Stop the tail. Run `npx wrangler d1 export d6s1-kit --remote --output d1.sql`, then `python3 scan_markers.py --people people.json d1.sql tail.json`. **You should see:** `markers_found: []` for both files and exit code 0. Paste the scanner's output lines (they contain no data) into the results.
18. Dashboard, **Email Service → Activity log**, last hour. **Record** which fields each sent message shows (recipient? subject?). Do not paste the addresses. This checks C6, with the new data that exists under Option B too.
19. Try to open a message preview. **You should see:** nothing, because preview is off. **Record** what the page says.
20. **Suppression list:** **record** whether it is empty.
21. Optional, C11: deploy `c11-probe.js` as a separate Worker with an unrestricted `send_email` binding, send to a test inbox that is **not** a verified destination, and **record** the returned `sent`/`code`. Delete that Worker straight away.

**Stop and record "No result" if:** Email Sending is not offered on the sandbox account, or you would have to use production credentials or a real relative's address.

## Cleaning up

1. `npx wrangler delete d6s1-kit`, then delete the D1 database(s) and the R2 bucket, and the C11 probe Worker if you made one.
2. Revoke the API token from step 5. Remove the owner test destination address if it is not needed for C3.
3. Delete the homelab temp folder the script printed (it holds the test roster and a throwaway age identity), and delete `people.json`.
4. Note that the Email Service Activity log and metrics keep the test recipients for up to 31 days (C6). Nothing can be done about that. It is part of the finding.

## Data handling

H3 defines the classes and rules in `docs/research/h3-research-data-governance.md`, §2–§4. Only test inboxes you control are used, and no relative is involved. The results record the provider domain (`gmail.com`), UTC times, yes/no answers and permission names. Never record the test addresses, message bodies or codes. `people.json`, `tail.json`, `d1.sql` and `results-run.json` stay on your machine and are deleted after you fill in the results. Only the scanner output (file name, size, and the list of markers found) is pasted.

## Results

Copy this section into `docs/research/kits/D6-S1/results.md` and fill it in. Do not edit numbers afterwards; add a note instead.

- **Run by / date / place:**
- **Sandbox account ID (last 6 characters) / wrangler version / Python / age versions:**
- **Emulator or VM used instead of real hardware?** The homelab was a VM: Yes/No.
- **D1 created with a jurisdiction?** none / eu (did `--jurisdiction eu` work?):

| Step | Expected | What happened | Measurement (with unit) | Screenshot or log |
|---|---|---|---|---|
| 1 | DNS records added | | record names | |
| 2 | Email preview default | | on / off | |
| 3 | Destination verified | | minutes to arrive | |
| 4 | Email permission names | | exact names | |
| 5 | Token permissions and IP filter | | | |
| 13 | 3 code emails | | UTC arrival ×3; inbox/spam ×3 | |
| 14 | 2 nudges, none to p1 | | stale-at, homelab-sent, inbox arrival (UTC) ×2 | |
| 15 | Owner alert only | | UTC arrival; other inboxes empty? | |
| 17 | Scanner, no markers | | scanner output lines | |
| 18 | Activity log fields | | which fields show recipient and subject | |
| 19 | Preview off | | | |
| 20 | Suppression list | | empty? | |
| 21 | C11 probe (optional) | | sent / code | |
| — | Owner hands-on time | | minutes | |

| Pass criterion | Budget ID | Measured value | Pass / Fail / No result |
|---|---|---|---|
| D1 holds no email or name (scanner exit 0 on `d1.sql`; no name/email column) | — | | |
| Nudge arrives within 24 h of staleness while the homelab is up (PLAN D6-S1; stale-at = last commit, floored to the minute, + 30 min) | BUD-TTS (context) | worst delay, min | |
| Owner alerted while the homelab is down; no other recipient | — | min after the last pull | |

- **Overall:** Pass | Fail | No result
- **Surprises and points of confusion:**
- **Follow-ups for the workstream:** C18 (token scope), C11 (binding scope), C6/C7 (what Cloudflare keeps), the D1 jurisdiction result
