# Spike C1-S5: old client against a v2 API (THROWAWAY)

> Ran for real in the cloud container (CT). The server is a toy Hono Worker under local `wrangler dev`, **not deployed to Cloudflare**. That is enough for this spike, because it tests how the API contract and the client's decoder behave, not anything Cloudflare does.
> This is throwaway research code, not production code.

- **Spike:** C1-S5 "Old client against v2 API" (workstream C1, `docs/research/PLAN.md` section "C1.")
- **Exec tag:** `[CT]`
- **Hypothesis:** an additive server change is invisible to an old client, and a breaking change returns a machine-readable "update required" instead of a decode failure.
- **Decision it informs:** the API evolution rules in ADR-0010 and `docs/design/api-v1.md` (C1 note F8): which changes count as additive, which client decoding rules the spec must impose, and how the minimum-version gate answers.
- **Budget IDs cited:** none (PLAN gives no budget for this spike).
- **Data-handling class:** `SYN → results`. Fixed synthetic IDs only.
- **Runs:** 2026-10-06 (first spike-runner pass, before 17:04Z) and a rerun at 2026-10-06T20:20Z with the same binary. The rerun output is byte-identical (`results/client-matrix-rerun-2026-10-06T2020Z.jsonl`).

## What ran

| Part | What | Versions |
|---|---|---|
| `server/` | One `POST /v1/check` endpoint served as five "server generations", selected per request by a test-only header `X-Test-Server-Mode`. A middleware on `/v1/*` requires `Reliquary-Client: <app>/<semver>` and answers **426** with an RFC 9457-style `application/problem+json` body, `code: "update_required"` and `min_version`, when the client is older than the generation's minimum. Every response carries `Reliquary-Server-Time`. | hono 4.13.11, zod 4.6.5, wrangler 4.143.0 (`server/package-lock.json`), Node 22.22.2 |
| `oldclient/` | A Rust "v1.2.0 desktop client" compiled against the **v1** schema, with two decoders for the same response: `naive` (closed enum for the item status) and `tolerant` (an `Unknown` catch-all via `#[serde(other)]`). Neither denies unknown object fields (serde's default). Run with version strings 1.2.0 and 2.0.0. | rustc 1.94.1; serde 1.0.229, serde_json 1.0.151, ureq 2.12.1 (`oldclient/Cargo.lock`) |

The server generations:

| Mode | Change relative to v1 | Kind |
|---|---|---|
| `v1` | none | baseline |
| `v2-add-field` | new item field `committed_at`, new top-level `server_hint` | additive |
| `v2-add-enum` | new status value `QUARANTINED` on some items | additive in intent, breaking for closed enums |
| `v2-rename` | field `status` renamed to `state`, without a version gate | breaking, ungated (the mistake to forbid) |
| `v2-break-gated` | same kind of breaking change, but the server's minimum client version is raised to 2.0.0 | breaking, gated |

Reproduce: `npm ci && X_LOCAL_OBSERVABILITY=false npx wrangler dev --port 8790` in a scratch copy of `server/`; `cargo build --release` in `oldclient/`; then `oldclient http://127.0.0.1:8790 1.2.0` and `oldclient http://127.0.0.1:8790 2.0.0`.

## Results (`results/client-matrix.jsonl`, `results/server-side.txt`)

| Server mode | Client 1.2.0, naive | Client 1.2.0, tolerant | Client 2.0.0 (both decoders) |
|---|---|---|---|
| `v1` | OK | OK | OK |
| `v2-add-field` | OK (new fields ignored) | OK | OK |
| `v2-add-enum` | **DECODE_ERROR** (HTTP 200): unknown variant `QUARANTINED` | OK, 2 of 8 items decoded as `Unknown` | naive: DECODE_ERROR; tolerant: OK, 2 Unknown |
| `v2-rename` | **DECODE_ERROR** (HTTP 200): missing field `status` | **DECODE_ERROR** (HTTP 200) | DECODE_ERROR (both) |
| `v2-break-gated` | **UPDATE_REQUIRED** (HTTP 426, min_version 2.0.0) | **UPDATE_REQUIRED** (HTTP 426) | OK |

Server-side checks (`results/server-side.txt`):

- A newer client that sends an extra request field (`priority`) to the v1 server: 200 when the request schema uses zod's default object (unknown keys stripped); **400 `invalid_request` with `unrecognized_keys`** when the schema is `.strict()`.
- No `Reliquary-Client` header: 400 `client_header_missing`.
- `Reliquary-Server-Time` is present on responses.

## Verdict

**Pass, with two conditions the spec must state.** The hypothesis holds for additive fields and for a gated breaking change. It fails in two cases, and each needs a rule in `docs/design/api-v1.md`:

1. **Adding an enum value is breaking for a client with a closed enum.** Either clients must decode every server enum with an "unknown" catch-all (the `tolerant` profile), or a new enum value must be gated by `min_version` like any other breaking change. Pick one rule and pin it with a test vector (G2).
2. **An ungated breaking change gives a decode error on HTTP 200, not "update required".** The minimum-version gate only helps if every breaking change raises `min_version` in the same deployment. That is a process rule (review checklist plus a contract test against the previous client build), not something the runtime can enforce.

Also: request schemas should strip unknown keys (zod default) rather than reject them, or a newer client talking to an older server (rollback, gradual deployment) gets 400s.

## Cleanup done

`oldclient/target/` (84 MB) and `server/node_modules/` were deleted from the scratchpad after the rerun. Only source, lockfiles and results are in the repository.
