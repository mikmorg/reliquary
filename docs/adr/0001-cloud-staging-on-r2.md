# ADR-0001: Cloud staging on Cloudflare R2; homelab makes outbound connections only

- **Status:** Accepted
- **Date:** 2026-09-29

## Context

Settled requirements (see `CLAUDE.md`): 10–25 family devices including phones, 2–10 TB total, non-technical users, client-side encryption with admin escrow, keep-forever retention, devices may only append. Devices must back up from anywhere, not only the home network.

The original plan exposed the homelab directly to the internet. That makes the least-managed machine in the system the one under attack, makes uploads dependent on home uplink and uptime, and gives phones a slow, fragile upload path.

## Decision

### 1. Devices upload to a cloud staging bucket, not to the homelab

- Storage: **Cloudflare R2** (S3-compatible API; no egress fees).
- Control plane: **Cloudflare Workers** (API, device auth, presigned URLs), **D1 / Durable Objects** (dedup index, claim/commit state), **Cloudflare Queues** (object-staged events). Single vendor; AWS was considered and rejected (see Alternatives).
- The **homelab only makes outbound connections**: it pulls events from the queue, downloads staged objects, verifies, stores, and reports "committed". No inbound port is opened.
- Staged objects are deleted after the homelab commits them (optionally retained for a short, configurable warm-cache window).

### 2. Encryption and deduplication

| Element | Device | Cloud (R2 / Workers / D1) | Homelab |
|---|---|---|---|
| Plain SHA-256 of content | Local cache only | Never sent | Recomputed after decrypt to verify |
| Dedup ID = HMAC-SHA256(family dedup secret, content) | Computes | Sees opaque IDs only | Can recompute |
| File content | Encrypted to the **homelab public key** (e.g. X25519 / `age`) | Ciphertext only | Decrypts with private key |
| Metadata (source locator, filename, mtime, size, EXIF date) | Encrypted the same way | Ciphertext only | Plaintext catalog (e.g. Postgres) |

Consequences of this scheme:

- Deduplication works on plaintext content across **all** users, but the cloud cannot test for known files (it lacks the dedup secret).
- Devices hold only the homelab *public* key, so they cannot read any backup data (not even their own). This enforces "devices append only" by construction and limits the blast radius of a stolen device.
- The admin (holder of the homelab private key) can decrypt everything, which matches the escrow trust model.
- Whole-file dedup for v1; keepsake media is effectively immutable. Chunk-level dedup can be revisited for large mutable files.

### 3. Client-side hash cache

Each client keeps a local cache keyed by `(source locator, size, mtime, platform file ID)` → SHA-256 and dedup ID, so it rehashes only changed files and can compute "what is not yet backed up" offline. mtime is recorded for context but is not trusted alone (unreliable on some Android copies, FAT, cloud-synced folders). On iOS the source locator is a PhotoKit asset identifier plus modification date, not a path; the data model uses a generic *source locator*.

### 4. Ingest protocol (sketch)

1. Client sends a batch of dedup IDs → Worker returns the missing ones plus presigned (multipart, resumable) upload URLs.
2. A concurrent upload of the same ID is handled by a conditional **claim** (`pending` with TTL → `committed`); objects are keyed by dedup ID so duplicate uploads are idempotent.
3. Client uploads ciphertext and an encrypted metadata record per (device, file).
4. The homelab pulls, decrypts, verifies the SHA-256 and HMAC, stores it, writes the catalog, and marks it `committed`; the staged object is then deleted.

A dedup "already have it" response grants **no read rights**. Any future self-service restore may only return files the requesting device actually uploaded and the homelab verified.

### 5. Transport-agnostic upload bundles

The encrypted object and metadata format is independent of transport. Supported transports:

- **R2 staging** (default, from anywhere).
- **USB drive (sneakernet)**: the client writes the same encrypted bundles plus a manifest to removable media; the admin loads them at the homelab. Required for initial seeding of large libraries or slow links. The same dedup IDs apply, so a mix of USB and online uploads never duplicates.
- **LAN direct** (proposed, not yet committed): devices on the home network push directly to a LAN-only homelab endpoint for the initial seed.

### 6. Restore staging

Restore is admin-initiated in v1. The homelab re-encrypts the requested files to the **requesting device's own public key** (each device gets a keypair at enrollment), uploads them to an expiring `restore/` prefix in R2 (lifecycle, e.g. 7 days), and the device downloads them through presigned URLs. No full cloud mirror is kept; an optional small warm cache (e.g. the last 30 days of each device's uploads) may be configurable.

## Alternatives considered

- **Public endpoint on the homelab:** rejected; it has the largest attack surface and ties uploads to home uplink and uptime.
- **AWS (S3 + Lambda + DynamoDB + SQS):** functionally equivalent, but S3 egress (~$0.09/GB, so ~$180–$900 for the initial 2–10 TB seed plus ongoing cost) is paid on every transfer home. Rejected in favour of R2.
- **AWS Snowball to bring data home:** reportedly unavailable to new customers since late 2024, sized for far larger volumes, and made pointless by R2's zero egress. Replaced by the USB transport.
- **Plaintext SHA-256 and metadata in the cloud:** rejected; it lets the cloud confirm known files and exposes filenames and paths, contradicting the trust model.

## Open questions

- Homelab storage engine behind the ingest service (plain content-addressed store vs. an existing format such as restic/Kopia).
- Key management details: generating and storing the homelab keypair, rotating the dedup secret, and enrollment by QR code (see the open decision on enrollment).
- Confirm current R2 and Workers pricing and limits (object size, multipart part limits, Queue throughput) against 2–10 TB.
- Whether LAN direct is worth building in addition to USB.
