#!/bin/bash
# B7-S1 kit: sign build/unsigned/v1 and v2 for one arm into build/<arm>/v1 and v2.
#
# Usage:
#   ./sign.sh adhoc                       arm A: ad hoc ("-"), what Tauri does with signingIdentity "-"
#   ./sign.sh selfsigned <SHA1-of-cert>   arm B: stable self-signed identity via Apple codesign
#   ./sign.sh selfsigned-rcs <p12-path>   arm B': same certificate, signed with rcodesign (the
#                                          tool a Linux CI would use); password b7s1test
#   ./sign.sh devid "<Developer ID Application: NAME (TEAMID)>"   arm C (only if L07 exists)
#
# All arms use the same flags as tauri-macos-sign (codesign --force -s <id> --options runtime
# --entitlements ...), so the only variable is the identity.
set -euo pipefail
cd "$(dirname "$0")"
ARM="$1"; ID="${2:-}"
ENT="probe/entitlements.plist"
for V in 1 2; do
  SRC="build/unsigned/v$V/ReliquaryProbe.app"
  DST="build/$ARM/v$V/ReliquaryProbe.app"
  rm -rf "build/$ARM/v$V"; mkdir -p "build/$ARM/v$V"
  ditto "$SRC" "$DST"
  case "$ARM" in
    adhoc)
      codesign --force -s - --options runtime --entitlements "$ENT" "$DST" ;;
    selfsigned)
      [ -n "$ID" ] || { echo "need the certificate SHA-1 (see make-cert.sh output)"; exit 2; }
      # If this fails with a trust error, record the exact message in results.md, then run
      # the trust step in README Part B step 3 and retry.
      codesign --force -s "$ID" --options runtime --entitlements "$ENT" "$DST" ;;
    selfsigned-rcs)
      [ -n "$ID" ] || { echo "need the p12 path"; exit 2; }
      # --timestamp-url none: rcodesign 0.29.0 otherwise contacts http://timestamp.apple.com/ts01
      # (its default); a timestamp does not change the DR. Remove it to test with a timestamp.
      rcodesign sign --p12-file "$ID" --p12-password b7s1test --timestamp-url none \
        --code-signature-flags runtime --entitlements-xml-file "$ENT" "$DST" ;;
    devid)
      [ -n "$ID" ] || { echo "need the Developer ID Application identity name"; exit 2; }
      codesign --force -s "$ID" --options runtime --timestamp --entitlements "$ENT" "$DST" ;;
    *) echo "unknown arm $ARM"; exit 2 ;;
  esac
  echo "== $DST"; codesign -d -r- "$DST" 2>&1 | sed 's/^/   /'
done
echo "Compare the two designated requirements above: arm A should differ (cdhash),"
echo "arms B, B' and C should be identical between v1 and v2."
