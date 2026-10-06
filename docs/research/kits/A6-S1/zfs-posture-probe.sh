#!/usr/bin/env bash
# A6-S1 kit: posture B ("plaintext on ZFS native encryption") probes on a THROWAWAY file-backed pool.
# THROWAWAY. Data class SYN (random bytes, made-up file names). Run in a test VM, never on the production pool host.
# Untested by its author: the cloud container has no ZFS.
# usage: N=200 ./zfs-posture-probe.sh   -> prints counts; writes ./a6-s1-zfs-<date>/
set -uo pipefail
N=${N:-200}; B=/var/tmp/a6probe; OUT=${OUT:-./a6-s1-zfs-$(date +%Y%m%d-%H%M)}; mkdir -p "$OUT" "$B"
IMG=$B/pool.img; KEY=$B/raw.key; MNT=$B/mnt; NAME=Grandma-wedding-1962; MARK=A6PROBE-CONTENT-MARKER
log() { echo "$*" | tee -a "$OUT/results.txt"; }
zfs version | tee "$OUT/zfs-version.txt"
truncate -s 2G "$IMG"; head -c 32 /dev/urandom > "$KEY"
zpool create -f -O mountpoint=none a6probe "$IMG"
zfs create -o encryption=aes-256-gcm -o keyformat=raw -o keylocation="file://$KEY" -o mountpoint="$MNT" a6probe/enc
for i in $(seq -w 1 "$N"); do { printf '%s-%s\n' "$MARK" "$i"; head -c 1048576 /dev/urandom; } > "$MNT/$NAME-$i.jpg"; done
sync; zfs snapshot a6probe/enc@s1
# P1 off-site copy: raw send (no key needed) vs non-raw send. Count name and content markers in each stream.
zfs send -w a6probe/enc@s1 > "$B/raw.zstream"; zfs send a6probe/enc@s1 > "$B/plain.zstream" 2> "$OUT/nonraw-send.err"
log "P1 raw send:     names $(grep -a -c "$NAME" "$B/raw.zstream")  content markers $(grep -a -c "$MARK" "$B/raw.zstream")  bytes $(stat -c %s "$B/raw.zstream")"
log "P1 non-raw send: names $(grep -a -c "$NAME" "$B/plain.zstream")  content markers $(grep -a -c "$MARK" "$B/plain.zstream")  bytes $(stat -c %s "$B/plain.zstream")"
# P2 stolen box: export, re-import WITHOUT loading the key; what can be listed?
zpool export a6probe; zpool import -d "$B" a6probe
log "P2 keystatus after import: $(zfs get -H -o value keystatus a6probe/enc)"
zfs list -t all -o name,used,referenced,written -p -r a6probe > "$OUT/zfs-list-nokey.txt"; log "P2 zfs list without key: $(wc -l < "$OUT/zfs-list-nokey.txt") lines (dataset and snapshot names, sizes): see zfs-list-nokey.txt"
zdb -dddd a6probe/enc > "$OUT/zdb-nokey.txt" 2>&1; log "P2 zdb -dddd without key: names found $(grep -a -c "$NAME" "$OUT/zdb-nokey.txt"), lines $(wc -l < "$OUT/zdb-nokey.txt")"
# P3 scrub without key, then with injected corruption (single file vdev: data damage is unrepairable)
zpool scrub -w a6probe; zpool status a6probe > "$OUT/scrub1.txt"; log "P3 clean scrub without key: $(grep -m1 'scan:' "$OUT/scrub1.txt")"
zpool export a6probe
dd if=/dev/urandom of="$IMG" bs=1M seek=600 count=64 conv=notrunc status=none
zpool import -d "$B" a6probe; zpool scrub -w a6probe; zpool status -v a6probe > "$OUT/scrub2-nokey.txt"
log "P3 scrub after corruption, key NOT loaded: $(grep -m1 'scan:' "$OUT/scrub2-nokey.txt"); names shown in status -v: $(grep -c "$NAME" "$OUT/scrub2-nokey.txt")"
# P4 unattended unlock with keylocation=file (no prompt), then the same status with the key loaded
s=$(date +%s.%N); zfs load-key a6probe/enc </dev/null; rc=$?; e=$(date +%s.%N)
log "P4 load-key from file without a prompt: rc=$rc in $(python3 -c "print(round($e-$s,3))") s"
zfs mount a6probe/enc; zpool status -v a6probe > "$OUT/scrub2-key.txt"; log "P4 status -v with key loaded: names shown $(grep -c "$NAME" "$OUT/scrub2-key.txt")"
# P5 change-key (rewrap) cost: time, and data untouched
s=$(date +%s.%N); head -c 32 /dev/urandom > "$KEY.new"; zfs change-key -o keylocation="file://$KEY.new" a6probe/enc; rc=$?; e=$(date +%s.%N)
log "P5 zfs change-key: rc=$rc in $(python3 -c "print(round($e-$s,3))") s"
zpool destroy -f a6probe; rm -rf "$B"
log "cleaned up"
