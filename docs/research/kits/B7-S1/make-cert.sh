#!/bin/bash
# B7-S1 kit: make a THROWAWAY self-signed code-signing identity for arm B and import it
# into the TEST user's login keychain. Data class SEC (test only): never commit key.pem
# or id.p12, never reuse this key for real releases, delete it in "Cleaning up".
#
# Usage: ./make-cert.sh [days]     (default 3650; use 1 for the optional expiry sub-test)
# Uses /usr/bin/openssl (LibreSSL on macOS), whose PKCS#12 output `security import` accepts.
# If you use Homebrew OpenSSL 3 instead, add -legacy to the pkcs12 command.
set -euo pipefail
cd "$(dirname "$0")"
DAYS="${1:-3650}"
D="secrets/selfsigned-${DAYS}d"
mkdir -p "$D"; chmod 700 secrets "$D"
cat > "$D/cert.cnf" <<'EOF'
[req]
distinguished_name = dn
x509_extensions = ext
prompt = no
[dn]
CN = Reliquary B7-S1 Test Code Signing
O = Reliquary Test
[ext]
basicConstraints = critical, CA:FALSE
keyUsage = critical, digitalSignature
extendedKeyUsage = critical, codeSigning
subjectKeyIdentifier = hash
EOF
/usr/bin/openssl req -x509 -newkey rsa:2048 -nodes -days "$DAYS" \
  -config "$D/cert.cnf" -keyout "$D/key.pem" -out "$D/cert.pem"
/usr/bin/openssl pkcs12 -export -inkey "$D/key.pem" -in "$D/cert.pem" \
  -name "Reliquary B7-S1 Test Code Signing (${DAYS}d)" -out "$D/id.p12" -passout pass:b7s1test
chmod 600 "$D"/*
security import "$D/id.p12" -k "$HOME/Library/Keychains/login.keychain-db" \
  -P b7s1test -T /usr/bin/codesign
echo "Certificate SHA-1 (expect this inside the DR as certificate root = H\"...\"):"
/usr/bin/openssl x509 -in "$D/cert.pem" -noout -fingerprint -sha1 | tee "$D/sha1.txt"
/usr/bin/openssl x509 -in "$D/cert.pem" -noout -subject -enddate
echo "Identities visible to codesign (untrusted ones are listed without -v):"
security find-identity -p codesigning "$HOME/Library/Keychains/login.keychain-db" || true
