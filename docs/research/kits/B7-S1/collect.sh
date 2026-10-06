#!/bin/bash
# B7-S1 kit: record the signing facts for one app bundle, plus the probe's latest JSON
# results, into results/<label>/. Run it after every step the procedure marks "collect".
#
# Usage: ./collect.sh <label> [app-path]
#   label example: A-adhoc_macos26_v2-after-update
#   default app: ~/Applications/ReliquaryProbe.app
set -uo pipefail
cd "$(dirname "$0")"
LABEL="$1"
APP="${2:-$HOME/Applications/ReliquaryProbe.app}"
OUT="results/$LABEL"
mkdir -p "$OUT"
{
  echo "== date"; date -u +%Y-%m-%dT%H:%M:%SZ
  echo "== sw_vers"; sw_vers
  echo "== uname -m"; uname -m
  echo "== codesign -d -r- (designated requirement)"; codesign -d -r- "$APP" 2>&1
  echo "== codesign -dvvv"; codesign -dvvv "$APP" 2>&1
  echo "== codesign --verify --strict -vv"; codesign --verify --strict -vv "$APP" 2>&1
  echo "== spctl -a -vv (Gatekeeper assessment)"; spctl -a -vv "$APP" 2>&1
  echo "== xattr -lr"; xattr -lr "$APP" 2>&1
  echo "== launchctl print (helper, if registered)"
  launchctl print "gui/$(id -u)/org.reliquary.b7s1probe.helper" 2>&1 | head -40
  echo "== sfltool dumpbtm (background items; needs admin, optional)"
  echo "(run 'sudo sfltool dumpbtm | grep -A8 -i reliquary' by hand if the procedure asks)"
} > "$OUT/signing.txt"

# TCC's own log lines about our bundle id from the last 15 minutes. Filtered to our id
# so no other app names are captured. May be empty if the OS redacts messages.
log show --last 15m --style compact \
  --predicate 'subsystem == "com.apple.TCC" AND eventMessage CONTAINS "org.reliquary.b7s1probe"' \
  > "$OUT/tcc-log.txt" 2>&1

# Newest probe results since the last collect.
RES="$HOME/Library/Application Support/org.reliquary.b7s1/results"
if [ -d "$RES" ]; then
  find "$RES" -name '*.json' -newer "$OUT/../.last-collect" -exec cp {} "$OUT/" \; 2>/dev/null \
    || cp "$RES"/*.json "$OUT/" 2>/dev/null
fi
touch "results/.last-collect"
echo "collected into $OUT"; ls -1 "$OUT"
