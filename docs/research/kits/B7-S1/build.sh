#!/bin/bash
# B7-S1 kit: build v1 and v2 of the probe app (unsigned) on the test Mac.
# Needs the Xcode Command Line Tools (xcode-select --install). Not run in the
# research container (no Apple SDK there).
#
# Usage: ./build.sh            -> build/unsigned/v1/ReliquaryProbe.app and build/unsigned/v2/...
# v1 and v2 differ in their Info.plist version AND in a string compiled into the binary,
# so their code directory hashes (cdhash) are guaranteed to differ, like a real release.
set -euo pipefail
cd "$(dirname "$0")"
KIT_DIR="$(pwd)"
OUT="$KIT_DIR/build/unsigned"
ARCH="$(uname -m)"          # arm64 on Apple Silicon, x86_64 on Intel
MIN_OS="13.0"               # SMAppService needs macOS 13+
rm -rf "$OUT"; mkdir -p "$OUT"

for V in 1 2; do
  VERSION="0.${V}.0"
  APP="$OUT/v$V/ReliquaryProbe.app"
  mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Library/LaunchAgents"
  SRC="$OUT/v$V/main.swift"
  sed "s/B7S1_BUILD_MARKER/v${V}-$(date -u +%Y%m%dT%H%M%SZ)/" probe/main.swift > "$SRC"
  swiftc -swift-version 5 -O -target "${ARCH}-apple-macos${MIN_OS}" \
    -o "$APP/Contents/MacOS/ReliquaryProbe" "$SRC"
  sed "s/@VERSION@/${VERSION}/g" probe/Info.plist.in > "$APP/Contents/Info.plist"
  cp probe/org.reliquary.b7s1probe.helper.plist "$APP/Contents/Library/LaunchAgents/"
  plutil -lint "$APP/Contents/Info.plist" "$APP/Contents/Library/LaunchAgents/org.reliquary.b7s1probe.helper.plist"
  echo "built $APP"
done
shasum -a 256 "$OUT"/v*/ReliquaryProbe.app/Contents/MacOS/ReliquaryProbe
