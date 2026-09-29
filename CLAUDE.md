# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

Reliquary is in the research & design phase. There is no source code, build system, or test suite yet. When scaffolding is added, replace this section with the real build / lint / test commands (including how to run a single test).

## Purpose

A cross-platform client application (Windows, macOS, Linux; mobile is a later consideration) that acts as an *assistant* for making sure a household's keepsakes and important data — photos, videos, documents, scans, records — are backed up to a central backup server running on the owner's homelab.

The emphasis is on "assistant", not just "sync agent": the client should help non-technical users discover what is worth protecting, tell them plainly what is and is not backed up, and flag problems (stale backups, unreachable server, files that changed but did not upload).

## Architectural shape (intended)

Two halves, designed together but deployable independently:

- **Client** (runs on each family device): discovers and watches selected locations, chunks/dedupes/encrypts data locally, uploads to the homelab, and surfaces backup health to the user. Needs a background service/daemon plus a lightweight UI (tray/menu-bar app).
- **Homelab server side**: the central backup target. Prefer building on an existing, proven backup repository format/server rather than inventing a storage format — the client's value is in the assistant/UX layer, not in reinventing deduplicating storage.

Properties the design must hold to:

- Data integrity over everything: backups must be verifiable and restorable; restore is a first-class feature, not an afterthought.
- Client-side encryption before data leaves the device.
- Tolerant of intermittent connectivity (laptops leaving the home network; optionally reachable remotely via VPN/tunnel).
- Low resource impact on user devices (throttling, battery/metered-network awareness).

## Open decisions

Record the outcome here (or in `docs/adr/`) as each is decided, so future sessions do not relitigate them:

- Client language/UI stack (e.g. Rust + Tauri, Go + Wails, Flutter, Electron).
- Backup engine/format to build on (e.g. restic, Kopia, Borg) and server target (REST server, S3-compatible store such as MinIO/Garage, SFTP).
- Remote connectivity model (Tailscale/WireGuard vs. exposed endpoint).
- Device enrollment and key management (how a new device gets credentials; how encryption keys are recovered if a device is lost).
