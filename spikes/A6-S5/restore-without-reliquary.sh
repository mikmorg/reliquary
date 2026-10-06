#!/usr/bin/env bash
# A6-S5: restore from a Reliquary store WITHOUT any Reliquary software.
# Needs only: bash, coreutils (sha256sum, cut, mkdir), find, grep, an age v1 decryptor
# (age >= 1.1 or rage), and optionally sqlite3. THROWAWAY spike procedure.
#
#   restore-without-reliquary.sh by-hash  STORE IDENTITY SHA256 OUTFILE
#   restore-without-reliquary.sh by-name  STORE IDENTITY NAME   OUTDIR   (no catalog: decrypts records)
#   restore-without-reliquary.sh by-name-catalog STORE IDENTITY NAME OUTDIR CATALOG.db
#   restore-without-reliquary.sh all      STORE IDENTITY OUTDIR          (every blob, checked)
# AGE=<decryptor binary> selects the implementation (default: age).
set -euo pipefail
AGE=${AGE:-age}
mode=$1; store=$2; id=$3
blobpath() {  # plain CAS layout: blobs/<aa>/<bb>/<sha>.age ; OCFL variant: find by name
  local s=$1 p="$store/blobs/${1:0:2}/${1:2:2}/$1.age"
  if [ -f "$p" ]; then echo "$p"; else find "$store/ocfl" -path "*/$s/v1/content/$s.age" -print -quit; fi
}
restore_hash() {  # $1 sha256, $2 outfile ; decrypt, then prove the bytes by their name
  # redirect stdout, do not use -o: age 1.1.1 and rage 0.12.1 create no -o file for an empty plaintext
  "$AGE" -d -i "$id" "$(blobpath "$1")" > "$2"
  [ "$(sha256sum "$2" | cut -c1-64)" = "$1" ] || { echo "HASH MISMATCH $1" >&2; return 1; }
}
case $mode in
  by-hash) restore_hash "$4" "$5" ;;
  by-name)
    mkdir -p "$5"
    # each record decrypts to: line 1 = JSON body with "sha256" and "name"; line 2 = signature (not checked here)
    for r in $(find "$store/records" -name '*.age'); do
      body=$("$AGE" -d -i "$id" "$r" | head -n1)
      if grep -q "\"name\":\"$4\"" <<<"$body"; then
        sha=$(grep -o '"sha256":"[0-9a-f]\{64\}"' <<<"$body" | cut -d'"' -f4)
        restore_hash "$sha" "$5/$4" && echo "restored $4 ($sha)"
      fi
    done ;;
  by-name-catalog)
    mkdir -p "$5"
    for sha in $(sqlite3 "$6" "SELECT DISTINCT sha256 FROM records WHERE name='$4'"); do
      restore_hash "$sha" "$5/$4" && echo "restored $4 ($sha)"
    done ;;
  all)
    mkdir -p "$4"; n=0
    for p in $(find "$store" -name '*.age' -path '*blobs*' -o -name '*.age' -path '*/v1/content/*'); do
      sha=$(basename "$p" .age); restore_hash "$sha" "$4/$sha"; n=$((n+1))
    done
    echo "restored and verified $n blobs" ;;
esac
