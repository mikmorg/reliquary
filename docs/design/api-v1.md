# Reliquary control-plane API v1 (outline)

- **Status:** Draft. This is an outline for Wave 1. The OpenAPI document (generated from Hono routes with chanfana and zod) follows in Wave 2. Request auth (D3, ADR-0014) and the ingest state machine (A3, ADR-0009) are not yet final.
- **Owner:** C1 (ADR-0010, Proposed)
- **Date:** 2026-10-06
- **Evidence:** [`docs/research/c1-cloudflare-control-plane.md`](../research/c1-cloudflare-control-plane.md) F4, F5, F8, F12; spike C1-S5 (`spikes/C1-S5/`)
- **Normative words:** MUST, SHOULD and MAY have their usual meaning. They bind only once ADR-0010 is Accepted.

## 1. Hosts and bootstrap

- **API base:** `https://api.<owner-domain>/v1/`, served from a Workers Custom Domain. The `workers.dev` hostname, Preview URLs, Version URLs and Deployment URLs are not used.
- **Content URLs:** presigned URLs point at `<ACCOUNT_ID>.r2.cloudflarestorage.com`. Clients MUST follow URLs exactly as given. They MUST NOT pin, allowlist or construct the R2 host.
- **Bootstrap:** `GET /v1/bootstrap` returns a document signed by an offline config key (D3/D5 own the key and the signature format).
  - It carries: API base URL(s), the minimum client version per platform, feature flags, and a not-after date.
  - It MUST NOT carry keys, pins or any trust decision (SR-31).
  - Clients ship with two bootstrap locations on independent hostnames and providers (DR-C1-4), cache the last valid document, and ignore an expired or unsigned one.

## 2. Versioning and compatibility (C1-S5 rules)

1. The path prefix is `/v1/`. Within v1, changes are **additive only**: new optional response fields, new endpoints, new optional request fields.
2. Clients MUST ignore unknown response fields.
3. Clients MUST decode every server enum with an `unknown` catch-all. If a client profile cannot, a new enum value counts as a breaking change and must be gated (rule 5). C1-S5: a closed enum gave a decode error on HTTP 200.
4. Server request schemas MUST strip unknown fields rather than reject them. C1-S5: a strict schema returned 400 to a newer client.
5. Every request carries `Reliquary-Client: <platform>/<semver>`. A missing header gets 400 `client_header_missing`. Any breaking change MUST raise the server's `min_version` in the **same deployment**, enforced by a review checklist and a contract test against the previous client build (G2). C1-S5: an ungated rename broke both decoders on HTTP 200.
6. Below `min_version`, the server answers **HTTP 400** with problem `code: "update_required"` and `min_version`. Clients key on `code`, never on the status, and render the localised plain-language text themselves (E6). Status 426 is not used, because RFC 9110 §15.5.22 requires an `Upgrade` header with it.
7. Every response carries `Reliquary-Server-Time: <unix ms>`.

## 3. Errors

- Media type `application/problem+json` (RFC 9457). Members: `type`, `title`, `status`, `detail`, `instance`. Extensions: `code` (stable, snake_case), `retryable` (boolean), plus problem-specific members such as `min_version`. Clients MUST ignore extensions they do not recognise (RFC 9457).
- 429 and 503 carry `Retry-After`. D1 or Durable Object "overloaded" errors map to 503 with `retryable: true`.
- Clients retry with jittered exponential backoff and a cap. They never retry a non-retryable problem automatically.
- Initial codes:
  - `update_required`, `client_header_missing`, `invalid_request`;
  - `unauthenticated`, `device_revoked`;
  - `rate_limited`, `overloaded`;
  - `staging_full`, `staging_paused` (F4 guard rails);
  - `upload_not_open`, `conflict`;
  - `idempotency_key_missing`, `idempotency_key_mismatch`, `idempotency_in_progress`.

## 4. Idempotency

- Natural keys come first: `(device_id, record_id)` for records and `(device_id, upload_id)` for uploads (A3). A repeat returns the original outcome.
- `Idempotency-Key` header on creates that have no natural key: `POST /v1/enroll/redeem`, `POST /v1/enroll/pair`, `POST /v1/homelab/restore-jobs`. Semantics follow the IETF HTTPAPI draft (editor's copy, `-latest`; publication status unconfirmed):

  | Case | Response |
  |---|---|
  | Key missing | 400 `idempotency_key_missing` |
  | Key reused with a different payload fingerprint | 422 `idempotency_key_mismatch` |
  | Retry while the first request is still in progress | 409 `idempotency_in_progress` |

- Published expiry: 7 days.

## 5. Batching and pagination

- Batch limits: `check` ≤ 1,000 IDs, `uploads` ≤ 100 items, `records` (one record batch per call), `commits` ≤ 1,000 items. Every batch response returns a **typed per-item result**, never an untyped reject (Immich lesson).
- Server rule: each request performs at most one D1 statement group, with set-based SQL per table (ADR-0010 §2).
- Pagination: an opaque `cursor` plus `limit` (with a maximum) for the feed, receipts and devices.

## 6. Endpoints (v0 outline; schemas in Wave 2)

| Group | Method and path | Purpose | Notes |
|---|---|---|---|
| Public | `GET /v1/bootstrap` | Signed config | §1 |
| Public | `POST /v1/enroll/redeem` | Redeem an invite, create an account, enroll the first device | Idempotency-Key; D3/E5 own the formats |
| Public | `POST /v1/enroll/pair` | Pair a further device | Idempotency-Key |
| Public | Email verification (GET page + POST confirm) | Verify email | C3 |
| Device | `POST /v1/check` | Which dedup IDs are MISSING / IN_FLIGHT / COMMITTED | ≤ 1,000 IDs; A3 states |
| Device | `POST /v1/uploads` | Begin uploads: lease, `upload_id`, key, first URL window | ≤ 100 items; may answer `staging_full` / `staging_paused` |
| Device | `POST /v1/uploads/{id}/parts` | Next window of UploadPart URLs | URLs ≤ 15 min |
| Device | `POST /v1/uploads/{id}/urls` | **Re-sign**: fresh URLs for the same keys and UploadId | Idempotent; refused when revoked or not open |
| Device | `POST /v1/uploads/{id}/complete` | Complete multipart (Worker) or confirm a single PUT; marks `staged` | Size check (SR-24); no condition on Complete |
| Device | `POST /v1/records` | Opaque record batch → `meta/` | Create-only; hash-compare retry → success or `conflict` |
| Device | `GET /v1/receipts?cursor=` | Homelab receipts relayed | Opaque bytes |
| Device | `GET /v1/status` | Server time, latest signed homelab heartbeat, staging state | |
| Device | `GET /v1/restores` | Restore jobs for this device | Later (A8) |
| Homelab | `GET /v1/homelab/feed?after=` | Event feed | Pending DR-C1-3 |
| Homelab | `POST /v1/homelab/commits` | Commit marks + receipts | Batch |
| Homelab | `POST /v1/homelab/rejections` | Verification failures | Batch |
| Homelab | `POST /v1/homelab/credentials` | Temp R2 credentials (ingest, restore) | Proposal; D3/C2 decide |
| Homelab | `PUT /v1/homelab/revocations` | Signed revocation list | D3 |
| Homelab | `POST /v1/homelab/heartbeat` | Signed heartbeat | Drives the presign pause |
| Homelab | `POST /v1/homelab/restore-jobs` | Stage a restore | Idempotency-Key |
| Homelab | `GET /v1/homelab/export` | Nightly export of cloud-only tables | C8 |
| Admin | Invites create/revoke/list; device revoke | | Path depends on D3/C8 |

## 7. Presigned URL rules (client side)

- URLs live ≤ 15 min. Clients fetch a window, upload, and fetch the next window.
- Desktop and Android re-sign just in time, before the transfer starts, through `POST /v1/uploads/{id}/urls`.
- After a failed presigned request, a client re-signs **only** on the expired-URL error that real-R2 C1-S1 H10 records. It does not re-sign on any other 403. At most 3 re-signs per part per hour (proposed; B6 tunes it), with jittered backoff. Repeated failures are reported as a health problem.
- iOS background transfers: not specified here (DR-B4-2).
- Signed extras (`Content-MD5`, Content-Length, `If-None-Match`, `x-amz-checksum-sha256`) are added only after real-R2 C1-S1 confirms that R2 enforces them.

## 8. R2 key layout (normative in ADR-0010 §Decision 3)

| Bucket | Key |
|---|---|
| `rq-ingest` | `staging/<dedup_id>/<upload_id>/s<n>`; `meta/<device_id>/<record_batch_id>.age`; reserved `pack/<upload_id>/s<n>` |
| `rq-restore` | `restore/<device_id>/<restore_job_id>/<object_id>` |

## 9. To be decided in Wave 2

- The request-signature construction and nonce rules (D3, ADR-0014).
- Field-level schemas for every endpoint.
- Admin endpoint placement.
- Restore endpoints (A8).
- The feed event schema (after DR-C1-3).
- The re-sign cap values (B6).
