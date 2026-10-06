#!/bin/bash
# B7-S1 kit: apply an "update" to an installed app the same way tauri-plugin-updater 2.13.0
# does on macOS (src/updater.rs, `impl Update` for macOS, `install_inner`):
#   1. the update is a .app.tar.gz whose first path component is the .app folder;
#   2. it is unpacked into a fresh temp dir named tauri_updated_app*, dropping that first component;
#   3. the running app folder is renamed into a temp dir tauri_current_app*/current_app;
#   4. the unpacked dir is renamed to the app's path;
#   5. `touch <app>`.
# No codesign runs on the device: the bundle keeps the signature it had at build time.
# (The updater's admin-password AppleScript fallback for PermissionDenied is not reproduced;
# install to ~/Applications so it is never needed.)
#
# Usage: ./update.sh <signed-v2-app-path> [installed-app-path]
#   default installed path: ~/Applications/ReliquaryProbe.app
set -euo pipefail
NEW_APP="$1"
TARGET="${2:-$HOME/Applications/ReliquaryProbe.app}"
[ -d "$NEW_APP" ] && [ -d "$TARGET" ] || { echo "usage: $0 <new.app> [installed.app]"; exit 2; }

WORK="$(mktemp -d)"
# Step 1: the update archive, as the Tauri bundler would ship it (no Apple xattrs inside).
( cd "$(dirname "$NEW_APP")" && COPYFILE_DISABLE=1 tar -czf "$WORK/update.app.tar.gz" "$(basename "$NEW_APP")" )
# Step 2
EXTRACT="$(mktemp -d "${TMPDIR:-/tmp}/tauri_updated_app.XXXXXX")"
tar -xzf "$WORK/update.app.tar.gz" -C "$EXTRACT" --strip-components 1
# Step 3
BACKUP="$(mktemp -d "${TMPDIR:-/tmp}/tauri_current_app.XXXXXX")"
mv "$TARGET" "$BACKUP/current_app"
# Step 4 (mv within one volume is a rename, as in the updater)
mv "$EXTRACT" "$TARGET"
# Step 5
touch "$TARGET"
rm -rf "$WORK"
echo "updated $TARGET (old copy in $BACKUP)"
echo "--- xattrs on the updated bundle (quarantine expected: none) ---"
xattr -lr "$TARGET" | grep -v "^$" || echo "(none)"
echo "--- permissions of the updated app folder ---"
ls -ld "$TARGET"
