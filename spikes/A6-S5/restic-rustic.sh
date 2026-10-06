#!/usr/bin/env bash
# A6-S5 part B: restic <-> rustic cross-implementation restore (THROWAWAY).
# usage: restic-rustic.sh PLAINDIR WORKDIR   (PLAINDIR: files named by their SHA-256)
set -uo pipefail

RESTIC=${RESTIC:-restic}; RUSTIC=${RUSTIC:-rustic}
PLAIN=$1; W=$2
rm -rf "$W"; mkdir -p "$W"
export RESTIC_PASSWORD=spike-only-throwaway RUSTIC_PASSWORD=spike-only-throwaway
export RUSTIC_NO_PROGRESS=true
check_dir() {  # every restored file must hash to its own name
  local d=$1 ok=0 bad=0
  for f in $(find "$d" -type f); do
    if [ "$(sha256sum "$f" | cut -c1-64)" = "$(basename "$f")" ]; then ok=$((ok+1)); else bad=$((bad+1)); fi
  done
  echo "$ok ok, $bad bad"
}
t() { local s=$(date +%s.%N); "$@"; local rc=$?; echo "  [rc=$rc, $(echo "$(date +%s.%N) - $s" | bc) s] $*" >&2; return $rc; }
N=$(find "$PLAIN" -type f | wc -l); echo "input: $N files, $(du -sb "$PLAIN" | cut -f1) bytes"
one=$(find "$PLAIN" -type f -size +5M | head -1); oneh=$(basename "$one")

echo "== A: restic writes, rustic reads"
t $RESTIC -r "$W/repo-restic" init -q
t $RESTIC -r "$W/repo-restic" backup -q "$PLAIN" --host spike
echo "repo format: $(grep -o '"version":[0-9]*' "$W/repo-restic/config" 2>/dev/null || $RESTIC -r "$W/repo-restic" cat config | grep -o '"version": *[0-9]*')"
t $RUSTIC -r "$W/repo-restic" check --read-data > "$W/A-rustic-check.log" 2>&1; echo "rustic check --read-data on restic repo: rc=$?"
t $RUSTIC -r "$W/repo-restic" restore latest "$W/A-restore" > "$W/A-rustic-restore.log" 2>&1; echo "rustic restore rc=$?"
echo "rustic-restored: $(check_dir "$W/A-restore")"
t $RUSTIC -r "$W/repo-restic" dump "latest:$PLAIN/$oneh" > "$W/A-dump" 2>"$W/A-dump.err"; echo "rustic dump single file: $( [ "$(sha256sum "$W/A-dump" | cut -c1-64)" = "$oneh" ] && echo OK || echo FAIL)"

echo "== B: rustic writes, restic reads"
t $RUSTIC -r "$W/repo-rustic" init > "$W/B-init.log" 2>&1; echo "rustic init rc=$?"
t $RUSTIC -r "$W/repo-rustic" backup "$PLAIN" > "$W/B-backup.log" 2>&1; echo "rustic backup rc=$?"
t $RESTIC -r "$W/repo-rustic" check --read-data > "$W/B-restic-check.log" 2>&1; echo "restic check --read-data on rustic repo: rc=$?"
t $RESTIC -r "$W/repo-rustic" restore latest --target "$W/B-restore" > "$W/B-restic-restore.log" 2>&1; echo "restic restore rc=$?"
echo "restic-restored: $(check_dir "$W/B-restore")"
t $RESTIC -r "$W/repo-rustic" dump latest "$PLAIN/$oneh" > "$W/B-dump" 2>"$W/B-dump.err"; echo "restic dump single file: $( [ "$(sha256sum "$W/B-dump" | cut -c1-64)" = "$oneh" ] && echo OK || echo FAIL)"
echo "== sizes"
du -sb "$W/repo-restic" "$W/repo-rustic"
echo "pack files: restic $(find "$W/repo-restic/data" -type f | wc -l), rustic $(find "$W/repo-rustic/data" -type f | wc -l)"
