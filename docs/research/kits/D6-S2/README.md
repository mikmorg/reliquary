# Kit D6-S2: Worker log audit on the real sandbox (what hosted Workers observability keeps)

- **Spike:** D6-S2 (workstream D6, see `docs/research/PLAN.md`, section "D6.")
- **Exec tag:** SB (sandbox Cloudflare account from H1; never production)
- **Prepared by / date:** D6 spike runner (agent), 2026-10-06
- **Who runs it:** Owner
- **Time needed:** about 45 min hands-on, plus about 30 min of waiting (four variants, about 5 min ingestion wait each)
- **Data-handling class:** `SYN + LAB → results`. The markers are synthetic (`zz-d6s2-…@example.invalid`). The only real values are the owner's own sandbox account and the public IP of the machine running the kit. The results hold only yes/no answers, counts and **field names**, never field values, IPs or markers.
- **Emulated rehearsal already done:** `spikes/D6-S2/README.md` (2026-09-29). Under `wrangler dev --local`, all three observability settings gave identical results. The local tool ignored `invocation_logs: false` and `enabled: false`, so that run was **inconclusive** about hosted Workers Logs. This kit is the real test. The kit's driver (`audit_real.py`) and probe Worker (`probe-worker.js`) were rehearsed locally on 2026-10-06 against `wrangler dev` 4.143.0 with `--no-api`. All ten routes returned the expected status codes, and the positive-control markers were found in the local log. That rehearsal tests only the script, not Cloudflare.

## Purpose

To find out which personal data Cloudflare's hosted Workers logging keeps for a Worker under each observability setting. Personal data here means addresses sent in URLs, headers or bodies, the client IP, the user agent and location. The goal is a configuration for the Reliquary control plane whose logs hold no personal data.

## Hypothesis

PLAN D6-S2: "A Worker configuration with no personal data in logs is achievable." Concretely, with **V1** (`invocation_logs: false`) and the code rules from the emulated run (no personal data in URLs, no logging of bodies, catch exceptions and replace their messages):

1. Workers Logs holds none of the markers sent in the query string, path, custom header, user agent or bodies, except the two deliberate positive controls (`/leaky-console`, `/leaky-structured`) and the uncaught exception (`/throw`).
2. Workers Logs holds no client IP.
3. With **V2** (`enabled: false`), Workers Logs holds nothing for the probe Worker.

The docs suggest where this could fail. Invocation logs are "enriched with information available to Cloudflare", and the query builder can group by `$workers.event.request.cf.country`. The fetch message is `<Method> <URL>`, so in V0 a query-string marker is expected to appear. Fetch-handler trace spans document `url.full`, `user_agent.original`, `geo.locality.name` and `cloudflare.asn` (V3). Whether the client IP itself appears anywhere is undocumented (note C17).

## Decision it informs

| If the result is… | Then… |
|---|---|
| **Pass**: some variant (expected V1 or V2) leaves no marker other than the positive controls, and no client IP, in Workers Logs (PLAN D6-S2) | ADR-0027 fixes that variant as the control-plane observability setting, plus the three code rules. ADR-0033 (B8/C7) inherits it. The D6 inventory row "Workers logs and analytics" lists only the residual fields named in the results (for example `cf.country`, `asn`, user agent). |
| **Fail**: every variant that keeps any logs also keeps the client IP or a marker from a non-logging route | ADR-0027 sets `observability.enabled: false` for every Worker that handles device or person traffic. Debugging relies on `wrangler tail` (live, not stored) and on custom metrics that carry no identifiers. The D6 inventory records the residual, and the owner sees it in OD-17 (accepted risks). |
| **No result** (no sandbox account, the observability API cannot be reached, or the token cannot be made) | The setting is chosen from the docs alone: `invocation_logs: false`, no traces, the code rules. The note records that D6-S2 is outstanding and C17 stays "undocumented". |

## Budget IDs cited

- **BUD-TEL**, for context only. That budget covers device telemetry volume. No log-volume number is measured here, and this kit sets no threshold of its own.

## Equipment

| Item | Exact model or version | Why | Have it? |
|---|---|---|---|
| Sandbox Cloudflare account (H1). Workers Logs is included on Workers Free and Paid (S-c); the sandbox will be on Paid for D6-S1 anyway. Tracing (V3) is Beta, so record it if it is unavailable | — | Hosted Workers Logs | |
| A laptop with Node 22, `wrangler` 4.143.0 and Python 3.11+ | — | Deploys the probe and runs `audit_real.py` | |
| An API token on the sandbox account that can **read Workers observability data** (see step 2) | — | The script queries the Workers Observability REST API | |

**Software and files needed:** in this folder: `probe-worker.js`, `wrangler.V0-default.jsonc`, `wrangler.V1-no-invocation-logs.jsonc`, `wrangler.V2-observability-off.jsonc`, `wrangler.V3-traces-on.jsonc`, `audit_real.py` (standard library only).

## Before you start

- [ ] Check that `wrangler whoami` shows the **sandbox** account ID and not a production one. Write the last 6 characters in the results.
- [ ] Copy this folder to a scratch directory outside the repo and work there. The script writes a `raw-d6s2/` folder with your IP and the raw API answers. That folder must never enter the repo.
- [ ] Have the account ID to hand (dashboard → Workers & Pages → right-hand panel).

## Procedure

Do the steps in order. After each step, write down what you saw in the results tables, even if it looks unimportant.

**A. Token and first deploy**

1. In the scratch folder run `npx wrangler@4.143.0 deploy --config wrangler.V0-default.jsonc`. **You should see:** a `https://d6s2-probe.<subdomain>.workers.dev` URL. Write it down.
2. Dashboard → My Profile → API Tokens → **Create custom token**. In the permission picker, search for "Observability" and "Workers". **Record** the exact names offered. Pick the narrowest read permission that sounds like it covers Workers Observability or Workers Logs. Scope it to the sandbox account only, add a **Client IP filter** for your current IP, and set a **TTL** ending tomorrow. **Record** what you chose.
3. Dashboard → Workers & Pages → `d6s2-probe` → **Settings** → **Observability**. **Record** what is shown as on or off for logs, invocation logs, traces and Issues under V0. This checks the documented default ("Defaults to true for all new Workers").

**B. Run the four variants.** Run steps 4–6 once for each variant, in the order V0, V1, V2, V3.

4. Deploy the variant: `npx wrangler@4.143.0 deploy --config wrangler.<variant file>.jsonc`. For V0 this was already done in step 1. Wait 1 minute after each deploy.
5. In a **second terminal**, start a live capture: `npx wrangler@4.143.0 tail d6s2-probe --format json > tail-<V>.json`. Leave it running.
6. In the first terminal run:
   `python3 audit_real.py --variant <V> --worker-url <URL from step 1> --account <account ID> --api-token <token> --tail-file tail-<V>.json --wait-min 5 > result-<V>.json`
   It sends ten requests, waits 5 minutes, queries the API, and writes `result-<V>.json`. **You should see:** `result-<V>.json` with `"api_success": true` for `events`, and a non-empty `route_http_status`. Stop the tail (Ctrl-C) **after** the script finishes.
   - If `api.events.http_status` is 401 or 403, the token lacks a permission. Add the next most likely permission, **record** which one worked, and rerun this variant.
   - If `event_count` is 0 under V0 or V1, wait 5 more minutes and rerun with `--wait-min 0`. **Record** this, because it is an ingestion-delay result in itself.

**C. Dashboard cross-checks** (the API answer may not be the whole picture)

7. Under V3, open **Observability → Traces** for `d6s2-probe` and open one `/query` trace. **Record** which attribute names appear on the fetch-handler span (for example `url.full`, `url.query`, `user_agent.original`, `geo.locality.name`, `cloudflare.asn`), and whether any attribute name looks like a client IP. Record names only.
8. Under V0, open **Observability → Events**, open the invocation log for `/query`, and **record** the field names under `$workers.event.request` (for example `url`, `headers`, `cf.*`). Is any of them a client IP field? Record names only.
9. Optional: dashboard → Analytics → Workers (GraphQL-backed metrics). **Record** whether any per-request view shows a client IP or URL. Workers metrics are aggregates. This is a quick look, not a test.

**Stop and record "No result" if:** the account is not the sandbox, or the observability API and the dashboard both give nothing for V0 after 15 minutes.

## Reading `result-<V>.json`

- `api_scan.<view>.markers_found`: which placements reached that hosted view. `body_leaky`, `body_structured` and `body_throw` are expected in any variant that keeps console output or exceptions. Any other name is a leak of a placement the Worker never logged.
- `api_scan.<view>.client_ip_found`: whether your public IP appears anywhere in that API answer.
- `api.events.interesting_field_names` and `api.keys.interesting_key_names`: field **names** that look like IP, location, user agent, URL or header fields. Copy them into the results as they are.
- `tail_scan`: the same checks against the live tail, which is streamed and not stored. It is reported separately because it is not a retained log.

## Cleaning up

1. `npx wrangler@4.143.0 delete d6s2-probe`.
2. Revoke the API token from step 2.
3. Delete `raw-d6s2/`, `tail-*.json` and the scratch folder. The `result-*.json` files contain no IPs or markers; keep them only until the results table is filled in.
4. Hosted Workers Logs for the probe stay at Cloudflare for 3 days on Workers Free or 7 days on Paid (S-c), and traces for 7 days (S-d). The kit cannot shorten that, and the retention is part of the finding.

## Data handling

H3 defines the classes and rules in `docs/research/h3-research-data-governance.md`, §2–§4. No family member or family data is involved. The probe receives only synthetic markers. The one real personal value is the public IP of the machine running the kit (the owner's own). It stays in `raw-d6s2/secrets-<V>.json` and the raw API answers on that machine, and is deleted at clean-up. Paste into the results only yes/no answers, counts, HTTP status codes and field **names**. Never paste field values, IPs, markers, the Worker subdomain or the account ID beyond its last 6 characters.

## Results

Copy this section into `docs/research/kits/D6-S2/results.md` and fill it in. Do not edit numbers afterwards; add a note instead.

- **Run by / date / place:**
- **Sandbox account ID (last 6 characters) / wrangler version / Python version:**
- **Emulator or VM used instead of real hardware?** No (real Cloudflare); the runner was: laptop / VM
- **Token permission(s) that made the observability API work (step 2/6):**
- **Dashboard defaults under V0 (step 3):** logs / invocation logs / traces / Issues =

| Variant | events: markers found | events: client IP found | events: count | keys / field names that look like IP, location, UA, URL or headers | invocations / traces: markers, IP | tail: markers, IP |
|---|---|---|---|---|---|---|
| V0 default | | | | | | |
| V1 invocation logs off | | | | | | |
| V2 observability off | | | | | | |
| V3 V1 + traces | | | | | | |

| Step | Expected | What happened | Measurement (with unit) | Screenshot or log |
|---|---|---|---|---|
| 7 | Span attribute names under V3 | | names | |
| 8 | Invocation-log request field names under V0 | | names | |
| 9 | Workers Analytics (optional) | | | |
| — | Ingestion delay (minutes until events appeared) | | min | |
| — | Owner hands-on time | | min | |

| Pass criterion | Budget ID | Measured value | Pass / Fail / No result |
|---|---|---|---|
| A configuration with no personal data in logs is achievable (PLAN D6-S2): some variant's retained logs (events, invocations, traces) contain no marker except `body_leaky`, `body_structured` and `body_throw`, and no client IP | BUD-TEL (context) | variant(s) meeting it | |

- **Overall:** Pass | Fail | No result
- **Surprises and points of confusion:**
- **Follow-ups for the workstream:** C17 (bodies and IPs in invocation logs) resolved or not; the setting to write into ADR-0027 and ADR-0033; whether `/caught` (the recommended exception pattern) kept the marker out

## Sources (all fetched 2026-10-06 from the cloudflare-docs source on raw.githubusercontent.com; developers.cloudflare.com is blocked from this container)

- S-a `workers/observability/logs/workers-logs.mdx`: https://raw.githubusercontent.com/cloudflare/cloudflare-docs/production/src/content/docs/workers/observability/logs/workers-logs.mdx. Covers new Workers having observability on by default, invocation logs "enriched with information available to Cloudflare", the fetch message `<Method> <URL>`, `invocation_logs = false`, the `head_sampling_rate` default of 1, and the 7-day maximum retention.
- S-b `workers/wrangler/configuration.mdx` (Observability section): https://raw.githubusercontent.com/cloudflare/cloudflare-docs/production/src/content/docs/workers/wrangler/configuration.mdx. States that `observability.enabled` "Defaults to true for all new Workers", and covers `observability.issues.enabled`.
- S-c partial `workers_logs_pricing.mdx`: https://raw.githubusercontent.com/cloudflare/cloudflare-docs/production/src/content/partials/workers/workers_logs_pricing.mdx. Workers Logs is on Free (200,000 events/day, 3-day retention) and Paid (7-day retention), with a pricing change from 2026-12-01.
- S-d `workers/observability/traces/index.mdx` (Beta) and `traces/spans-and-attributes.mdx`: https://raw.githubusercontent.com/cloudflare/cloudflare-docs/production/src/content/docs/workers/observability/traces/index.mdx and https://raw.githubusercontent.com/cloudflare/cloudflare-docs/production/src/content/docs/workers/observability/traces/spans-and-attributes.mdx. Traces are kept for 7 days. Fetch-handler span attributes include `url.full`, `url.path`, `user_agent.*`, `geo.*` (including `geo.locality.name`) and `cloudflare.asn`. Email-handler attributes include `cloudflare.email.from` and `cloudflare.email.to`. No client-IP attribute is listed.
- S-e (fetched 2026-09-29) `workers/observability/query-builder.mdx`: https://raw.githubusercontent.com/cloudflare/cloudflare-docs/production/src/content/docs/workers/observability/query-builder.mdx. Gives the example group-by `$workers.event.request.cf.country` and mentions the Workers Observability REST API.
- S-f `cloudflare` npm SDK 7.3.0, `resources/workers/observability/telemetry.{js,d.ts}`: https://registry.npmjs.org/cloudflare/-/cloudflare-7.3.0.tgz. Source of the endpoint paths `/accounts/{id}/workers/observability/telemetry/{query,keys}` and the body fields `queryId`, `timeframe`, `view`, `limit`, `dry` and `parameters.filters` used by `audit_real.py`. The required token permission is not stated there; step 2 records it.
