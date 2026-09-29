# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

Reliquary is in the research & design phase. There is no source code, build system, or test suite yet. When scaffolding is added, replace this section with the real build / lint / test commands (including how to run a single test).

## Purpose

A cross-platform client application (Windows, macOS, Linux, iOS, Android) that acts as an *assistant* for making sure a household's keepsakes and important data — photos, videos, documents, scans, records — are backed up to a central backup server running on the owner's homelab.

The emphasis is on "assistant", not just "sync agent": the client should help non-technical users discover what is worth protecting, tell them plainly what is and is not backed up, and flag problems (stale backups, unreachable server, files that changed but did not upload).

## Architectural shape (intended)

Two halves, designed together but deployable independently:

- **Client** (runs on each family device): discovers and watches selected locations, chunks/dedupes/encrypts data locally, uploads to the homelab, and surfaces backup health to the user. Needs a background service/daemon plus a lightweight UI (tray/menu-bar app).
- **Homelab server side**: the central backup target. Prefer building on an existing, proven backup repository format/server rather than inventing a storage format — the client's value is in the assistant/UX layer, not in reinventing deduplicating storage.

Properties the design must hold to:

- Data integrity over everything: backups must be verifiable and restorable; restore is a first-class feature, not an afterthought.
- Client-side encryption before data leaves the device.
- Tolerant of intermittent connectivity (devices away from home, flaky mobile networks).
- Low resource impact on user devices (throttling, battery/metered-network awareness).

## Settled requirements

Decided with the owner; do not relitigate without asking:

- **Platforms (v1):** Windows, macOS, Linux, iOS, Android. Phones are first-class (camera rolls are the main keepsake source), so desktop-only stacks are out, and iOS background-execution limits shape the mobile design.
- **Users:** non-technical family members. The owner administers everything centrally; end users should never touch configuration. Device enrollment must be near-zero-effort (e.g. QR code).
- **Scale:** 2–10 TB total across 10–25 devices, multiple people.
- **Server host:** Linux / Proxmox in the homelab; the server side runs as containers or VMs.
- **Connectivity:** a public, internet-exposed endpoint (not VPN-only). Treat the server as under attack: TLS, strong per-device credentials, rate limiting, and **devices can only append backups, never delete or rewrite them**, so a compromised or ransomwared device cannot destroy its own history.
- **Encryption trust model:** data is encrypted client-side; the owner (admin) holds a recovery/escrow key and can decrypt any family member's backups. Privacy is against outsiders, not against the admin.
- **Retention:** keep forever. Deleting a file on a device never removes the backed-up copy; pruning is a manual admin action only.
- **Off-site copy of the homelab:** out of scope for now; handled by the owner's separate plans and to be revisited in a later phase.

## Open decisions

Record the outcome here (or in `docs/adr/`) as each is decided:

- Client stack able to cover desktop + mobile (e.g. Flutter, Kotlin Multiplatform, or a shared Rust core with native/Tauri shells).
- Backup engine/format to build on (e.g. restic, Kopia, Borg) and server target (REST server, S3-compatible store such as MinIO/Garage, SFTP), given the append-only and admin-escrow requirements.
- Device enrollment and credential issuance/revocation flow.
