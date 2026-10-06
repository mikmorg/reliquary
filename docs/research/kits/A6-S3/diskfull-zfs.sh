#!/usr/bin/env bash
# A6-S3 (OL half, Part B): disk-full (ENOSPC) on a REAL ZFS pool, in a throwaway test VM.
# THROWAWAY. Data class SYN. Untested by its author: no ZFS in the cloud container (see README).
# Uses spikes/A6-S3/harness/diskfull.py --placement external with ZFS hooks:
#   prep: a fresh file-backed pool; a reservation dataset takes all but $SIZE bytes of free space
#   grow: destroy the reservation
# usage: A6=/srv/a6 TRIALS=20 ./diskfull-zfs.sh   (A6 holds keys/ and corpus/ from `a6cas keygen` / `a6cas gen`)
set -euo pipefail
: "${A6:?}"; TRIALS=${TRIALS:-20}; ENC=${ENC:-0}
HARNESS=${HARNESS:-$(cd "$(dirname "$0")/../../../.." && pwd)/spikes/A6-S3/harness/diskfull.py}
BASE=${BASE:-/var/tmp/a6df}; mkdir -p "$BASE"
OUT=${OUT:-./a6-s3-diskfull-zfs-$(date +%Y%m%d-%H%M)}; mkdir -p "$OUT"
# size of a complete store for this corpus: plaintext bytes + about 1 % (age overhead, records, manifest)
FULL=$(python3 -c "import json;u={};[u.__setitem__(o['sha256'],o['size']) for o in map(json.loads,open('$A6/corpus/truth.jsonl'))];print(int(sum(u.values())*1.01))" 2>/dev/null \
       || du -sb "$A6/corpus/staging" | cut -f1)
IMG=$BASE/a6full.img; IMGSIZE=$(( FULL * 3 ))
ENCOPTS=""
if [ "$ENC" = 1 ]; then head -c 32 /dev/urandom > "$BASE/a6full.key"
  ENCOPTS="-O encryption=aes-256-gcm -O keyformat=raw -O keylocation=file://$BASE/a6full.key"; fi
export IMG IMGSIZE ENCOPTS
PREP='zpool destroy -f a6full 2>/dev/null || true; rm -f "$IMG"; truncate -s "$IMGSIZE" "$IMG"; mkdir -p "$MNT";
      zpool create -f $ENCOPTS -O mountpoint="$MNT" a6full "$IMG";
      AV=$(zfs get -Hp -o value available a6full);
      zfs create -o mountpoint=none -o refreservation=$(( AV - SIZE )) a6full/filler'
GROW='zfs destroy a6full/filler'
{ zfs version; zpool get -H -o value size a6full 2>/dev/null || true; echo "FULL=$FULL ENC=$ENC TRIALS=$TRIALS"; } | tee "$OUT/env.txt"
python3 "$HARNESS" --a6cas "$(command -v a6cas)" --corpus "$A6/corpus" --keys "$A6/keys" --base "$BASE" \
  --placement external --prep-cmd "$PREP" --grow-cmd "$GROW" --full-bytes "$FULL" --trials "$TRIALS" --seed 91 \
  --evidence "$OUT/diskfull-zfs.jsonl" | tee "$OUT/diskfull-zfs.summary.json"
zpool destroy -f a6full; rm -f "$IMG" "$BASE/a6full.key"
