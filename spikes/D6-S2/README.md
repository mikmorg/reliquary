# Spike D6-S2: Worker log audit (EMULATED, not real Cloudflare)

> Throwaway research code. The real audit of hosted Workers Logs is a kit: `docs/research/kits/D6-S2/`.
> This folder holds the probe Worker, which the kit reuses, and the output of a local run.

- **Spike:** D6-S2 (workstream D6, `docs/research/PLAN.md` Track D). Exec tag **SB**. This run is the
  **local-emulator variant** (`wrangler dev --local`). Miniflare's local explorer is **not** Workers Logs.
- **Run by / date:** D6 spike runner (agent), 2026-09-29, cloud container, wrangler 4.143.0 (Miniflare 5.20260926.0-alpha).
- **Hypothesis (PLAN):** a Worker configuration with no personal data in its logs is achievable.
- **Decision informed:** the log settings in ADR-0027 (with B8/C7, ADR-0033), and the OD-03 inventory row "Workers logs and analytics".
  Pass → ADR-0027 fixes the observability settings and logging rules. Fail → turn invocation logs off, emit only custom
  structured logs, and record the residual in the D6 inventory.
- **Budget IDs cited:** BUD-TEL (context only; that budget covers device telemetry volume, and no log-volume number is measured here).
- **Data-handling class:** `SYN → results` (markers `zz-d6s2-*@example.invalid` and the documentation IP 203.0.113.77).

## Method

`worker/src/index.js` is a probe Worker. Each route places one synthetic marker in one place: the query string, a request header, the body
logged with an opaque ID only (`/clean`), the whole body logged (`/leaky-console`, a positive control), and the body inside an
uncaught exception (`/throw`). A fake `CF-Connecting-IP` header is sent as well. `run_emulated.py` runs the Worker three times, with
`observability.logs.invocation_logs: true`, then `invocation_logs: false`, then `observability.enabled: false`. After each run it searches three places
for every marker: the `wrangler dev` output and Miniflare's local-explorer `logs` and `spans` tables.

## Results (`evidence/results.json`)

| Marker placed in… | `wrangler dev` output | Local explorer `logs` | Local explorer `spans` |
|---|---|---|---|
| Query string (`/query?email=…`) | no | **yes**: the invocation message is `"GET http://…/query?email=…"` | no |
| Request header | no | no | no |
| Body, `/clean` (logs only an opaque ID) | no | no | no |
| Body, `/leaky-console` (positive control) | **yes** | **yes** | no |
| Body, inside an uncaught exception | **yes**: `[wrangler:error] Error: could not process {…}` | no | no |
| Fake client IP header (203.0.113.77) | no | no | no |

**All three configurations gave identical results.** The local toolchain did not honour `invocation_logs: false` or `enabled: false`:
the local explorer still recorded the invocation messages. **The emulated result is therefore inconclusive for the hypothesis.**
It says nothing about what hosted Workers Logs record under each setting.

What the local run does support, as a code-level rule for the kit and for ADR-0027, and consistent with the documented fetch
invocation message `<Method> <URL>` (`workers-logs.mdx`, fetched 2026-09-29):

1. Never put personal data or secrets in URLs, including query strings. Put them in bodies or headers.
2. Never log request bodies. Log opaque IDs and outcomes as structured JSON.
3. Catch exceptions and replace their messages, because an uncaught exception message built from request data reaches the log output.

## How to rerun

```bash
npm install
python3 run_emulated.py   # about 1 min; needs port 8797 free
```
