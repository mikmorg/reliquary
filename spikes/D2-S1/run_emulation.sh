#!/usr/bin/env bash
# D2-S1 emulation (throwaway): plugin-protocol overhead ceiling with a SOFTWARE plugin.
# Emulated: no YubiKey, no PC/SC. Measures only what any plugin-held key pays on top of device time.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
# age >= 1.3.0 must be on PATH (or in $AGEBIN). The two Go tools are built into $BIN.
BIN=${BIN:-$HERE/bin}
[ -x "$BIN/plugbench" ] || (cd "$HERE" && go build -o "$BIN/" ./cmd/...)
export PATH=$BIN:${AGEBIN:+$AGEBIN:}$PATH
W=${W:-/dev/shm/d2s1}; rm -rf "$W"; mkdir -p "$W/objs" "$W/out"
EVID=${EVID:-$HERE/evidence}; mkdir -p "$EVID"
N=${N:-2000}; NCLI=${NCLI:-200}
K=$(age-keygen 2>/dev/null | grep AGE-SECRET)
R=$(echo "$K" | age-keygen -y)
PID=$(plugbench -print-identity -native "$K")
echo "$PID" > "$W/plugin-identity.txt"
{
echo "# D2-S1 emulation run $(date -u +%FT%TZ)"
echo "# age $(age --version); $(go version); nproc $(nproc); loadavg $(cat /proc/loadavg)"
for rep in 1 2 3; do
  plugbench -n "$N" -batch 100 -native "$K"
done
# CLI path: one age process + one plugin process per object
for i in $(seq -w 1 "$NCLI"); do head -c 4096 /dev/urandom | age -r "$R" -o "$W/objs/o$i.age"; done
for rep in 1 2 3; do
  s=$(date +%s.%N)
  for f in "$W"/objs/*.age; do age -d -i "$W/plugin-identity.txt" -o "$W/out/x" "$f"; done
  e=$(date +%s.%N)
  python3 -c "import json;n=$NCLI;el=$e-$s;print(json.dumps({'cli_per_file_n':n,'elapsed_s':round(el,3),'unwraps_per_s':round(n/el,1),'loadavg':open('/proc/loadavg').read().strip()}))"
done
} | tee "$EVID/emulation-results.jsonl"
rm -rf "$W"
