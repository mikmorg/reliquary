#!/usr/bin/env bash
# D2-S1 kit: YubiKey unwrap throughput for an unattended ingest key.
# Run on the machine (or Proxmox VM with USB passthrough) that would run ingest, with a SPARE YubiKey.
#
# Usage: run-yubikey.sh IDENTITY_FILE LABEL [N] [SOAK_MINUTES]
#   IDENTITY_FILE  output of: age-plugin-yubikey --identity --slot SLOT > id.txt
#   LABEL          e.g. A-never-never, B-once-never, C-default
#   N              objects per pass (default 1000)
#   SOAK_MINUTES   optional sustained run with batched sessions (default 0 = skip)
# Env: PLUGBENCH_PIN  the PIV PIN, only for identities whose PIN policy is not "never"
# Needs on PATH: age (>= 1.3.0), age-plugin-yubikey (0.5.1), plugbench (built from spikes/D2-S1), pcscd running.
# Writes results to ./results-LABEL.jsonl. No secrets are written (the PIN is never logged).
set -euo pipefail
ID=${1:?identity file}; LABEL=${2:?label}; N=${3:-1000}; SOAK=${4:-0}
for t in age age-plugin-yubikey plugbench; do command -v "$t" >/dev/null || { echo "missing $t"; exit 1; }; done
OUT=$PWD/results-$LABEL.jsonl
W=$(mktemp -d); trap 'rm -rf "$W"' EXIT
R=$(grep -m1 '^#.*[Rr]ecipient' "$ID" | awk '{print $NF}')
[ -n "$R" ] || { echo "could not read the recipient comment from $ID"; exit 1; }
PID=$(grep -m1 '^AGE-PLUGIN-YUBIKEY-' "$ID")
echo "# $LABEL $(date -u +%FT%TZ) N=$N age=$(age --version) plugin=$(age-plugin-yubikey --version 2>/dev/null || echo '?') host=$(uname -srm) load=$(cut -d' ' -f1-3 /proc/loadavg 2>/dev/null)" | tee -a "$OUT"
mkdir -p "$W/objs"
for i in $(seq -w 1 "$N"); do head -c 4096 /dev/urandom | age -r "$R" -o "$W/objs/o$i.age"; done
# 1. stock plugin client (one plugin process and one PC/SC session per object) and batched sessions of 100
for rep in 1 2 3; do
  plugbench -dir "$W/objs" -n "$N" -batch 100 -plugin age-plugin-yubikey -identity "$PID" | tee -a "$OUT"
done
# 2. the age CLI, one process per object (first 100 objects)
s=$(date +%s.%N); ok=0
for f in $(ls "$W"/objs/*.age | head -100); do age -d -i "$ID" -o /dev/null "$f" && ok=$((ok+1)); done
e=$(date +%s.%N)
python3 -c "import json;print(json.dumps({'label':'$LABEL','cli_per_file_n':100,'ok':$ok,'elapsed_s':round($e-$s,3),'unwraps_per_s':round(100/($e-$s),2)}))" | tee -a "$OUT"
# 3. optional soak: batched sessions back to back for SOAK minutes, one line per minute
if [ "$SOAK" -gt 0 ]; then
  end=$(( $(date +%s) + SOAK*60 ))
  while [ "$(date +%s)" -lt "$end" ]; do
    m0=$(date +%s); cnt=0; err=0
    while [ $(( $(date +%s) - m0 )) -lt 60 ]; do
      if plugbench -skip-stock -dir "$W/objs" -n 100 -batch 100 -plugin age-plugin-yubikey -identity "$PID" > "$W/last.json" 2> "$W/last.err"; then
        cnt=$((cnt + $(python3 -c "import json;print(json.load(open('$W/last.json'))['batched_file_keys'])")))
      else err=$((err+1)); fi
    done
    echo "{\"label\":\"$LABEL\",\"soak_minute_end\":\"$(date -u +%FT%TZ)\",\"batched_unwraps_in_minute\":$cnt,\"errors\":$err}" | tee -a "$OUT"
  done
fi
echo "done: $OUT"
