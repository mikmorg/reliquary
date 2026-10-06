#!/usr/bin/env bash
# A6-S3 (OL half): hard power-off of a test VM while a6cas ingest runs, x10.
# Runs ON THE PROXMOX HOST. The VM holds the store on its own disk. ACKs stream to the
# host over ssh, so they survive the VM's power cut and serve as the "acknowledged" list.
#
# usage: VMID=9101 VM=root@a6-crash-vm CUTS=10 ./powercut.sh
# The VM must have: a6cas on PATH, /srv/a6/{keys,corpus/staging,corpus/truth.jsonl},
# python3, and an EMPTY /srv/a6/work (made by the first iteration).
set -uo pipefail
: "${VMID:?}" "${VM:?}"; CUTS=${CUTS:-10}; MIN=${MIN:-5}; MAX=${MAX:-60}
OUT=${OUT:-./a6-s3-powercut-$(date +%Y%m%d-%H%M)}; mkdir -p "$OUT"
ING="a6cas ingest -store /srv/a6/work/store -catalog /srv/a6/work/catalog.db -staging /srv/a6/corpus/staging \
 -ingest-key /srv/a6/keys/ingest-e1.key -rcpt /srv/a6/keys/stored-recipients.txt -family /srv/a6/keys/family-secret.hex"
wait_ssh() { for _ in $(seq 1 120); do ssh -o ConnectTimeout=3 "$VM" true 2>/dev/null && return 0; sleep 2; done; return 1; }
wait_ssh || { echo "VM not reachable"; exit 1; }
ssh "$VM" '[ -d /srv/a6/work/store ] || a6cas init -store /srv/a6/work/store -devices /srv/a6/corpus/devices.json'
: > "$OUT/acked.txt"
for i in $(seq 1 "$CUTS"); do
  ssh "$VM" "$ING" > "$OUT/ingest-$i.out" 2> "$OUT/ingest-$i.err" &
  sshpid=$!
  d=$(python3 -c "import random;print(round(random.uniform($MIN,$MAX),1))")
  sleep "$d"
  echo "$(date -Is) cut $i after ${d}s" | tee -a "$OUT/log.txt"
  qm stop "$VMID" --skiplock 1          # hard stop: the QEMU process exits at once (no guest shutdown)
  wait $sshpid 2>/dev/null
  grep -E '^ACK [0-9a-f]+$' "$OUT/ingest-$i.out" | cut -d' ' -f2 >> "$OUT/acked.txt"
  qm start "$VMID"; wait_ssh || { echo "VM did not come back" | tee -a "$OUT/log.txt"; exit 1; }
  scp -q "$OUT/acked.txt" "$VM:/tmp/acked.txt"
  ssh "$VM" 'a6cas recover -store /srv/a6/work/store -catalog /srv/a6/work/catalog.db' > "$OUT/recover-$i.json"
  ssh "$VM" 'a6cas audit -store /srv/a6/work/store' > "$OUT/audit-$i.json"
  ssh "$VM" "python3 - <<'EOF'
import json, sqlite3
acked = set(open('/tmp/acked.txt').read().split())
cat = {r[0] for r in sqlite3.connect('/srv/a6/work/catalog.db').execute('SELECT record_id FROM records')}
man = {json.loads(l)['record_id'] for l in open('/srv/a6/work/store/manifest/manifest.jsonl') if '\"t\":\"record\"' in l}
print(json.dumps({'acked': len(acked), 'acked_not_in_catalog': len(acked - cat), 'acked_not_in_manifest': len(acked - man)}))
EOF" > "$OUT/check-$i.json"
  echo "  recover $(cat "$OUT/recover-$i.json")" | tee -a "$OUT/log.txt"
  echo "  audit   $(python3 -c "import json,sys;d=json.load(open('$OUT/audit-$i.json'));print({k:d[k] for k in ('objects_ok','mismatch','missing')})")" | tee -a "$OUT/log.txt"
  echo "  check   $(cat "$OUT/check-$i.json")" | tee -a "$OUT/log.txt"
done
echo "finishing ingest without a cut, then the keyed full check" | tee -a "$OUT/log.txt"
ssh "$VM" "$ING" > "$OUT/ingest-final.out" 2> "$OUT/ingest-final.err"
ssh "$VM" 'a6cas verify -store /srv/a6/work/store -archive-key /srv/a6/keys/archive.key -recovery-key /srv/a6/keys/recovery.key' > "$OUT/verify-final.json"
ssh "$VM" "python3 - <<'EOF'
import json, sqlite3
t = [json.loads(l) for l in open('/srv/a6/corpus/truth.jsonl')]
cat = {r[0]: r[1] for r in sqlite3.connect('/srv/a6/work/catalog.db').execute('SELECT record_id, sha256 FROM records')}
print(json.dumps({'truth': len(t), 'catalog': len(cat), 'all_match': all(cat.get(x['record_id']) == x['sha256'] for x in t)}))
EOF" | tee "$OUT/truth-final.json"
grep -o '"[a-z_]*FAIL[a-z_]*": [0-9]*' "$OUT/verify-final.json" || echo "verify: no FAIL counters" | tee -a "$OUT/log.txt"
