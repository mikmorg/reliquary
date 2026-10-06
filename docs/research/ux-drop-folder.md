# UX addition: the one-way "Reliquary" drop folder

- **Status:** Accepted direction from the owner (2026-10-06); details to be designed in Wave 2.
- **Owners:** E4 (discovery and proposal UX) with B5 (source layer). Status wording: E3. Wizard and first-run placement: E5.
- **Decision record:** OD-22 in `decision-queue.md`.

## What it is

Every enrolled device gets a folder named **Reliquary** (desktop: in the user's home folder, with a shortcut on the desktop and in the Explorer or Finder sidebar; Android: a folder in shared storage). Anything placed in it is backed up and kept forever, like any other keepsake.

It complements auto-discovery. Discovery proposes what the assistant can find; the folder gives family members a simple rule for everything else: *"If it matters, put it in the Reliquary folder."*

## What it is not

- **Not two-way sync.** The folder never shows other devices' files and never downloads anything. Two-way sync was considered and rejected for v1:
  - it would require devices to decrypt backups, which ADR-0001 and the threat model forbid;
  - it would propagate deletions and edits, which keep-forever and append-only exist to stop;
  - it is a different, much larger product.
- **Not a mirror.** Removing a file from the folder never removes the backed-up copy (keep-forever, CLAUDE.md).

## Behaviour to design (Wave 2)

| Topic | Proposed default | Owner |
|---|---|---|
| Source type | A watched source like any other in the source layer; files enter the same pipeline, receipts and status | B5 |
| Leaving the folder | Files may stay or be removed. Once a homelab receipt exists, removal is safe; before that, the app warns | E3, B5 |
| "Safe to delete" wording | Only after a receipt, and only under E3's general "safe to delete" policy (OD-18) | E3 |
| Moves vs copies | Dragging *into* the folder on the same disk moves the file by default on Windows and macOS. Decide whether the app suggests copying, or treats the folder as the new home | E4 |
| Large and odd items | Same size and type rules as discovery; nothing is silently skipped, and anything refused is shown with a reason | E4, E3 |
| Cloud placeholders dropped in | Never hydrated silently; reported as "only in the cloud" (PLAN §3 checklist) | B5 |
| Status ticks | Per-file "safe at home" badges in Explorer and Finder are desirable; feasibility without code signing is unknown | B5, B7 |
| Entry points | "Send to Reliquary" in the Android share menu and the desktop right-click menu, feeding the same path | E4, B2, B1 |
| Android | Shared-storage folder access under Play policy (no `MANAGE_EXTERNAL_STORAGE` in the Play flavour); ties into OD-19 | B2, B3 |
| Onboarding | Introduced in first run and in the Start-here guide as the one rule to remember | E5, E6 |

## Questions for Wave 2

1. On Android, is a shared-storage folder reachable without all-files access under current Play policy, or does the share menu have to be the primary entry point there?
2. Can Windows and macOS file badges work with an unsigned or ad-hoc-signed app (Windows shell overlay slots or Cloud Files API; macOS Finder Sync extensions)?
3. Do relatives understand "put it in the Reliquary folder" better than discovery proposals? Add to the E2-S1 and E5 usability sessions.
