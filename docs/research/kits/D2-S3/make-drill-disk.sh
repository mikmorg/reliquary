#!/usr/bin/env bash
# D2-S3 kit: build a DRILL disk and DRILL share cards (owner runs this, offline, before the drill).
#
# It uses a separate DRILL key, never the real homelab or recovery key. The layout is a stand-in
# until A2 (object format), A4 (bundle) and A6 (store) are decided; the recovery path uses stock
# tools only: SLIP-39 reference CLI (shamir) + age.
#
# Usage: make-drill-disk.sh PHOTOS_DIR OUT_DIR [--pq] [--decoys N] [--bits 128|256]
#   PHOTOS_DIR  exactly the 10 LAB photos named in the drill runbook (no people in them; H3 class LAB)
#   OUT_DIR     the drill disk folder (copy it to the USB disk afterwards)
# Needs on PATH: age, age-keygen, age-plugin-batchpass (age >= 1.3.0), shamir (pip install 'shamir-mnemonic[cli]==0.3.0')
# Prints: the 3 share texts to paste onto 3 cards, and the public-key check for the card.
# The share texts and the drill master secret are shown ONCE on screen and never written to disk.
set -euo pipefail
PHOTOS=${1:?photos dir}; OUT=${2:?out dir}; shift 2
PQ=""; DECOYS=40; BITS=128
while [ $# -gt 0 ]; do case "$1" in --pq) PQ="-pq";; --decoys) DECOYS=$2; shift;; --bits) BITS=$2; shift;; *) echo "unknown $1"; exit 2;; esac; shift; done
for t in age age-keygen age-plugin-batchpass shamir python3; do command -v "$t" >/dev/null || { echo "missing $t"; exit 1; }; done
[ -e "$OUT" ] && { echo "$OUT exists; refusing to overwrite"; exit 1; }
N=$(find "$PHOTOS" -maxdepth 1 -type f | wc -l); [ "$N" -eq 10 ] || { echo "need exactly 10 photos, found $N"; exit 1; }
umask 077
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
mkdir -p "$OUT/recovery" "$OUT/store/objects"
# 1. drill keys: an "ingest" key (destroyed at the end, as in a disaster) and a recovery key
age-keygen $PQ -o "$TMP/ingest.key" 2>/dev/null
age-keygen $PQ -o "$TMP/recovery.key" 2>/dev/null
IR=$(age-keygen -y "$TMP/ingest.key"); RR=$(age-keygen -y "$TMP/recovery.key")
# 2. random drill master secret -> SLIP-39 2-of-3 shares (shown once) -> seals the recovery identity
SECRET=$(python3 -c "import secrets;print(secrets.token_hex($BITS//8))")
echo "==== DRILL SHARE CARDS (copy each share onto its own card; 2 of 3 needed) ===="
shamir create 2of3 -S "$SECRET" | sed -n '3,5p' | nl -w1 -s': '
AGE_PASSPHRASE="$SECRET" age -e -j batchpass -o "$OUT/recovery/recovery-identity.age" "$TMP/recovery.key"
unset SECRET
# 3. content objects (random IDs stand in for dedup IDs) + decoys, and an encrypted catalog
printf 'name\tobject\tbytes\tsha256\n' > "$TMP/catalog.tsv"
for f in "$PHOTOS"/*; do
  id=$(python3 -c "import secrets;print(secrets.token_hex(16))")
  age -r "$IR" -r "$RR" -o "$OUT/store/objects/$id.age" "$f"
  printf '%s\t%s\t%s\t%s\n' "$(basename "$f")" "$id" "$(wc -c <"$f" | tr -d ' ')" "$(python3 -c "import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" "$f")" >> "$TMP/catalog.tsv"
done
for i in $(seq 1 "$DECOYS"); do
  id=$(python3 -c "import secrets;print(secrets.token_hex(16))")
  head -c $((200000 + RANDOM * 10)) /dev/urandom > "$TMP/decoy"
  age -r "$IR" -r "$RR" -o "$OUT/store/objects/$id.age" "$TMP/decoy"
  printf 'decoy-%03d.bin\t%s\t%s\t-\n' "$i" "$id" "$(wc -c <"$TMP/decoy" | tr -d ' ')" >> "$TMP/catalog.tsv"
done
age -r "$IR" -r "$RR" -o "$OUT/store/catalog.tsv.age" "$TMP/catalog.tsv"
cat > "$OUT/README-FIRST.txt" <<TXT
DRILL DISK - practice copy, not real family data.
Follow the printed "Break-glass runbook (drill)". Do not change or delete anything on this disk.
TXT
# 4. the check printed on the card: first 12 and last 8 characters of the recovery public key
echo "==== CARD CHECK LINE ===="
echo "Recovery key check: starts with ${RR:0:12}  ends with ${RR: -8}"
echo "${RR:0:12} ... ${RR: -8}" > "$OUT/recovery/KEY-CHECK.txt"
# 5. the disaster: the ingest key is destroyed (TMP is removed on exit)
echo "Drill disk ready: $OUT ($(ls "$OUT/store/objects" | wc -l) objects). Ingest key destroyed."
