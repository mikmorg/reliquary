# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

Reliquary is in the research & design phase. There is no source code, build system, or test suite yet. When scaffolding is added, replace this section with the real build / lint / test commands (including how to run a single test).

## Purpose

A cross-platform client application (Windows, macOS, Linux, Android; iOS later) that acts as an *assistant* for making sure a household's keepsakes and important data — photos, videos, documents, scans, records — are backed up to a central backup server running on the owner's homelab.

The emphasis is on "assistant", not just "sync agent": the client should help non-technical users discover what is worth protecting, tell them plainly what is and is not backed up, and flag problems (stale backups, unreachable server, files that changed but did not upload).

## Architectural shape (intended)

Three parts (details and rationale in `docs/adr/0001-cloud-staging-on-r2.md`):

- **Client** (runs on each family device): discovers keepsakes, keeps a local hash cache, computes dedup IDs, encrypts content and metadata to the homelab public key, uploads, and surfaces backup health to the user. Needs a background service/daemon plus a lightweight UI (tray/menu-bar app on desktop).
- **Cloud staging (Cloudflare R2 + Workers + D1/Durable Objects + Queues)**: the only internet-facing component. Issues presigned upload URLs, holds the cross-user dedup index and claim/commit state, and briefly stages ciphertext for ingest and for restores. It never sees plaintext content, plaintext hashes, or filenames.
- **Homelab (Proxmox)**: makes outbound connections only. Pulls staged objects, decrypts, verifies, stores permanently, and keeps the plaintext catalog. It also ingests USB-drive bundles. The storage engine behind it is still open; prefer an existing, proven format over inventing one.

Upload bundles are transport-agnostic: the same encrypted objects and manifest travel via R2, via USB drive (sneakernet, a required feature for seeding large libraries), or potentially via LAN.

Properties the design must hold to:

- Data integrity over everything: backups must be verifiable and restorable; restore is a first-class feature, not an afterthought.
- Client-side encryption before data leaves the device.
- Tolerant of intermittent connectivity (devices away from home, flaky mobile networks).
- Low resource impact on user devices (throttling, battery/metered-network awareness).

## Settled requirements

Decided with the owner; do not relitigate without asking:

- **Platforms (v1):** Windows, macOS, Linux, Android. **iOS is deferred** (revisit with the Apple Developer membership), but the client stack must not preclude it. Phones are first-class (camera rolls are the main keepsake source), so desktop-only stacks are out.
- **Users:** non-technical family members. The owner administers everything centrally; end users should never touch configuration.
- **Onboarding and distribution (ADR-0002):** each person receives a USB stick with the desktop app and a printed **one-use, expiring invite code** (with QR). Redeeming it creates an account with just a **name and email** (verified by email; no password) and enrolls the first device. Additional devices are enrolled by scanning a short-lived QR code shown on an already-enrolled device. Desktop apps install themselves from the stick and self-update; Android ships via Google Play (family closed track). The same stick doubles as the USB seeding transport.
- **Code signing:** no Apple or Windows code signing for now. Self-updates **must** be signed with the project's own offline key and verified by the app before installing.
- **Email:** used for signup verification and backup nudges. Account name, email and device activity times are plaintext in the cloud control plane; file content and metadata are not.
- **Scale:** 2–10 TB total across 10–25 devices, multiple people.
- **Server host:** Linux / Proxmox in the homelab; the server side runs as containers or VMs.
- **Connectivity (ADR-0001):** devices upload to Cloudflare R2 staging from anywhere; the homelab is never exposed and only makes outbound connections. No AWS. USB-drive transport is required; LAN direct is optional. Treat the cloud API as under attack: strong per-device credentials, rate limiting, and **devices can only append backups, never delete or rewrite them**, so a compromised or ransomwared device cannot destroy its own history.
- **Encryption trust model (ADR-0001):** content and metadata are encrypted on the device to the homelab public key; devices cannot read any backup data. Cross-user dedup uses HMAC(family secret, content), so the cloud sees only opaque IDs. The owner (admin) holds the private key and can decrypt everything; privacy is against outsiders (including the cloud provider), not against the admin.
- **Deduplication:** whole-file, across all users, based on plaintext content. Clients keep a local cache of file hashes; source locator, filename and mtime are recorded for context (plaintext only at the homelab).
- **Retention:** keep forever. Deleting a file on a device never removes the backed-up copy; pruning is a manual admin action only.
- **v1 assistant features:** auto-discovery of keepsakes (propose what to protect rather than making users pick folders), plain-language per-person backup health, and proactive nudges (stale device, not yet backed up, storage issues). An admin dashboard is not a v1 goal.
- **v1 data sources:** files on the device only (including the phone photo library). Pulling from iCloud / Google Photos and email / social-media exports is on the roadmap, so keep the source layer pluggable.
- **Restore:** performed by the admin in v1; no end-user restore UI yet. v1 focus is getting data safely *in*. Restores are delivered by re-encrypting to the target device's own key and staging in an expiring R2 prefix.
- **Off-site copy of the homelab:** out of scope for now; handled by the owner's separate plans and to be revisited in a later phase.

## Open decisions

Record the outcome here (or in `docs/adr/`) as each is decided:

- Client stack able to cover desktop + Android now and iOS later (e.g. Flutter, Kotlin Multiplatform, or a shared Rust core with native/Tauri shells). Planned as ADR-0003.
- Homelab storage engine behind the ingest service (plain content-addressed store vs. an existing format such as restic/Kopia).
- Per-device credential format and revocation, homelab keypair custody, dedup-secret rotation, and the email sending provider (not AWS).
- Whether to build the LAN-direct transport.
