#!/bin/bash
# B7-S1-dr (CT, emulated): what designated requirement (DR) and cdhash does rcodesign 0.29.0
# produce for ad-hoc and for a self-signed identity, across two different builds (v1, v2)?
# EMULATED: runs on Linux with rcodesign; no macOS, no TCC. It shows what is written into
# the signature, not how macOS evaluates it (that is the B7-S1 kit).
# Inputs: two real arm64 Mach-O executables (esbuild 0.25.0 and 0.25.1 from npm, used only as
# stand-in "v1" and "v2" program bytes), wrapped in an .app bundle with a fixed bundle id.
set -euo pipefail
RCS="${RCS:-rcodesign}"
W="${W:-$(pwd)/work}"
rm -rf "$W"; mkdir -p "$W"; cd "$W"
ID=org.reliquary.b7s1probe

for v in 0.25.0 0.25.1; do
  curl -sSfL -o esb-$v.tgz https://registry.npmjs.org/@esbuild/darwin-arm64/-/darwin-arm64-$v.tgz
  mkdir -p esb-$v && tar xzf esb-$v.tgz -C esb-$v
done

mkapp() { # $1 dir, $2 version, $3 macho
  mkdir -p "$1/ReliquaryProbe.app/Contents/MacOS"
  cp "$3" "$1/ReliquaryProbe.app/Contents/MacOS/ReliquaryProbe"
  cat > "$1/ReliquaryProbe.app/Contents/Info.plist" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleExecutable</key><string>ReliquaryProbe</string>
<key>CFBundleIdentifier</key><string>$ID</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>CFBundleShortVersionString</key><string>$2</string>
<key>CFBundleVersion</key><string>$2</string>
</dict></plist>
PL
}

# Self-signed identity, same recipe as the B7-S1 kit's make-cert.sh (with and without O=).
mkcert() { # $1 name, $2 subject
  cat > $1.cnf <<CN
[req]
distinguished_name = dn
x509_extensions = ext
prompt = no
[dn]
$2
[ext]
basicConstraints = critical, CA:FALSE
keyUsage = critical, digitalSignature
extendedKeyUsage = critical, codeSigning
subjectKeyIdentifier = hash
CN
  openssl req -x509 -newkey rsa:2048 -nodes -days 3650 -config $1.cnf -keyout $1.key -out $1.pem 2>/dev/null
  openssl x509 -in $1.pem -noout -fingerprint -sha1 | sed 's/.*=//; s/://g' | tr 'A-F' 'a-f' > $1.sha1
}
mkcert withO  $'CN = Reliquary B7-S1 Test Code Signing\nO = Reliquary Test'
mkcert noO    $'CN = Reliquary B7-S1 Test Code Signing NoO'

sig() { # $1 label, $2 app, extra args...  (never aborts the run; failures are recorded)
  local label=$1 app=$2; shift 2
  local bin="$app/Contents/MacOS/ReliquaryProbe"
  "$RCS" sign "$@" "$app" > $label.sign.log 2>&1 && echo signed > $label.status || echo SIGN-FAILED > $label.status
  "$RCS" print-signature-info "$bin" > $label.info.yaml 2>&1 || true
  "$RCS" extract code-directory-raw "$bin" > $label.cd.bin 2>/dev/null || true
  "$RCS" extract requirements "$bin" > $label.req.txt 2>&1 || true
  "$RCS" extract code-directory "$bin" > $label.cd.txt 2>&1 || true
  # cdhash = first 20 bytes of the hash of the code directory (SHA-256 CD here).
  local cdh; cdh=$(sha256sum $label.cd.bin | cut -c1-40)
  local flags; flags=$(grep -m1 -A1 -E "^ *flags:" $label.cd.txt | tail -1 | tr -d " ,")
  printf '%-18s %-6s cdhash=%s  %s\n    DR embedded: %s\n' "$label" "$(cat $label.status)" "$cdh" "$flags" \
    "$(grep -v '^\s*$' $label.req.txt | tr '\n' ' ' | sed 's/  */ /g')"
}

for arm in adhoc adhoc-again selfO selfNoO; do
  mkapp $arm-v1 0.1.0 esb-0.25.0/package/bin/esbuild
  mkapp $arm-v2 0.2.0 esb-0.25.1/package/bin/esbuild
done
echo "rcodesign: $("$RCS" --version 2>&1)"
echo "cert withO sha1=$(cat withO.sha1)   cert noO sha1=$(cat noO.sha1)"
for v in v1 v2; do
  sig adhoc-$v       adhoc-$v/ReliquaryProbe.app       --code-signature-flags runtime
  sig adhoc-again-$v adhoc-again-$v/ReliquaryProbe.app --code-signature-flags runtime
  sig selfO-$v       selfO-$v/ReliquaryProbe.app       --pem-file withO.pem --pem-file withO.key --timestamp-url none --code-signature-flags runtime
  sig selfNoO-$v     selfNoO-$v/ReliquaryProbe.app     --pem-file noO.pem --pem-file noO.key --timestamp-url none --code-signature-flags runtime
done

# The B7-S1 kit's arm B' command (sign.sh selfsigned-rcs) takes a PKCS#12 file.
# Check which PKCS#12 encodings rcodesign 0.29.0 accepts: OpenSSL 3 "-legacy" vs its default.
cat > ent.plist <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict><key>com.apple.security.personal-information.photos-library</key><true/></dict></plist>
PL
echo "openssl: $(openssl version)"
for mode in legacy default; do
  extra=""; [ $mode = legacy ] && extra="-legacy"
  openssl pkcs12 -export $extra -inkey withO.key -in withO.pem -out id-$mode.p12 -passout pass:b7s1test
  mkapp p12-$mode 0.2.0 esb-0.25.1/package/bin/esbuild
  if "$RCS" sign --p12-file id-$mode.p12 --p12-password b7s1test --timestamp-url none \
       --code-signature-flags runtime --entitlements-xml-file ent.plist p12-$mode/ReliquaryProbe.app > p12-$mode.log 2>&1; then
    echo "p12 $mode: signed; DR: $("$RCS" extract requirements p12-$mode/ReliquaryProbe.app/Contents/MacOS/ReliquaryProbe | tr -s ' \n' ' ')"
  else
    echo "p12 $mode: FAILED: $(tail -1 p12-$mode.log)"
  fi
done
