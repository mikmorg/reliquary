#!/usr/bin/env bash
# A6-S4 catalog loss -> rebuild from the store (THROWAWAY). Data class SYN.
# usage: s4.sh NAME STORE CATALOG KEYSDIR [STAGING]
#   With STAGING, scenario "mid-ingest loss": kill ingest, delete catalog, rebuild, resume.
set -uo pipefail

B=${A6CAS:-a6cas}
name=$1; st=$2; cat=$3; keys=$4; stg=${5:-}
W=$(dirname "$cat")/s4-$name; mkdir -p "$W"
TIMEFORMAT="%R"
ingest() { $B ingest -store "$st" -catalog "$cat" -staging "$stg" -ingest-key "$keys/ingest-e1.key" \
             -rcpt "$keys/stored-recipients.txt" -family "$keys/family-secret.hex"; }
if [ -n "$stg" ]; then
  # start the a6cas process itself in the background (not a shell function: killing a
  # function's subshell leaves a6cas running, which is how the first run got two writers)
  $B ingest -store "$st" -catalog "$cat" -staging "$stg" -ingest-key "$keys/ingest-e1.key"      -rcpt "$keys/stored-recipients.txt" -family "$keys/family-secret.hex" > "$W/run1.out" 2>&1 & pid=$!
  sleep 1.5
  echo "second concurrent ingest while the first runs: $(ingest 2>&1 | tail -1)"
  kill -9 $pid; wait $pid 2>/dev/null; sleep 0.2
  kill -0 $pid 2>/dev/null && echo "WARNING: the first a6cas is still running"
  echo "killed ingest after $(grep -c '^ACK' "$W/run1.out") ACKs"
  rm -f "$cat" "$cat-wal" "$cat-shm"
  echo "catalog deleted mid-ingest; rebuilding"
  $B rebuild -store "$st" -out "$cat" -archive-key "$keys/archive.key" 2>&1
  ingest > "$W/run2.out" 2>&1
  echo "resume: $(grep -c '^ACK [0-9a-f]*$' "$W/run2.out") new ACKs, $(grep -c 'ACK .* dup' "$W/run2.out") dup ACKs (stored receipt path)"
fi
$B export -catalog "$cat" > "$W/before.jsonl"
cp "$cat" "$W/catalog-before.db" 2>/dev/null
rm -f "$cat" "$cat-wal" "$cat-shm"
echo "catalog deleted; $(wc -l < "$W/before.jsonl") canonical rows before"
s=$( { time $B rebuild -store "$st" -out "$W/rebuilt.db" -archive-key "$keys/archive.key" 2> "$W/rebuild.err"; } 2>&1 )
cat "$W/rebuild.err"; echo "rebuild (manifest + records) wall s: $s"
$B export -catalog "$W/rebuilt.db" > "$W/after.jsonl"
if cmp -s "$W/before.jsonl" "$W/after.jsonl"; then echo "RESULT byte-identical canonical export: YES ($(sha256sum < "$W/after.jsonl" | cut -c1-16)...)"; else echo "RESULT byte-identical: NO"; diff "$W/before.jsonl" "$W/after.jsonl" | head -5; fi
s=$( { time $B rebuild -store "$st" -out "$W/rebuilt-nomanifest.db" -archive-key "$keys/archive.key" -no-manifest 2> "$W/rebuild-nm.err"; } 2>&1 )
cat "$W/rebuild-nm.err"; echo "rebuild (object files only, manifest ignored) wall s: $s"
$B export -catalog "$W/rebuilt-nomanifest.db" > "$W/after-nm.jsonl"
python3 - "$W/before.jsonl" "$W/after-nm.jsonl" <<'EOF'
import json, sys
a = [json.loads(l) for l in open(sys.argv[1])]; b = [json.loads(l) for l in open(sys.argv[2])]
key = lambda o: (o["t"], o.get("sha256") if o["t"] == "blob" else o["record_id"])
A = {key(o): o for o in a}; B = {key(o): o for o in b}
lost = {}
for k in A:
    if k not in B: lost["(row missing)"] = lost.get("(row missing)", 0) + 1; continue
    for f in A[k]:
        if A[k][f] != B[k].get(f): lost[f"{k[0]}.{f}"] = lost.get(f"{k[0]}.{f}", 0) + 1
print("files-only rebuild: rows", len(B), "of", len(A), "; fields that differ from the original catalog:", lost or "none")
EOF
