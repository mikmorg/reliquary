#!/usr/bin/env bash
# A6-S2 bake-off: (1) plain CAS of age objects, (2) the same objects in an OCFL 1.1
# storage root, (3) restic as the "proven engine" comparator. Runs on the homelab
# against the H3 corpus. Saves AGGREGATES ONLY (counts, bytes, seconds, RSS) to
# $WORK/results/results.jsonl. File names and paths never leave $WORK.
#
# usage:  CORPUS=/path/to/h3-corpus WORK=/pool/a6-bakeoff ./bakeoff.sh
# options (environment):
#   SAMPLES=50          single-file restores per engine
#   BATCH=5000          files per restic snapshot ("ingest window")
#   ENGINES="cas ocfl restic"
#   DROP_CACHES=1       drop the page cache before each timed read phase (needs root)
#   A6CAS=a6cas RESTIC=restic   binaries to use
set -euo pipefail
: "${CORPUS:?set CORPUS}" "${WORK:?set WORK}"
SAMPLES=${SAMPLES:-50}; BATCH=${BATCH:-5000}; ENGINES=${ENGINES:-"cas ocfl restic"}
DROP_CACHES=${DROP_CACHES:-1}; A6CAS=${A6CAS:-a6cas}; RESTIC=${RESTIC:-restic}
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=$WORK/results; mkdir -p "$OUT"; RES=$OUT/results.jsonl
m() { local label=$1; shift; python3 "$HERE/measure.py" "$RES" "$label" "$@"; }   # m LABEL [k=v..] -- cmd
note() { echo "$1" >> "$RES"; }
log() { echo "$(date -Is) $*" | tee -a "$OUT/run.log" >&2; }
drop() { if [ "$DROP_CACHES" = 1 ]; then sync; echo 3 > /proc/sys/vm/drop_caches; fi; }
want() { case " $ENGINES " in *" $1 "*) return 0 ;; esac; return 1; }

log "A6-S2 bake-off started"
note "{\"kernel\":\"$(uname -r)\",\"cpus\":$(nproc),\"mem_kb\":$(awk '/MemTotal/{print $2}' /proc/meminfo),\"work_fs\":\"$(df -T "$WORK" | awk 'NR==2{print $2}')\",\"restic\":\"$($RESTIC version | cut -d' ' -f2)\",\"drop_caches\":$DROP_CACHES,\"samples\":$SAMPLES,\"batch\":$BATCH}"
note "{\"corpus_files\":$(find "$CORPUS" -type f | wc -l),\"corpus_bytes\":$(du -sb "$CORPUS" | cut -f1)}"

# ---- 1. keys and device-side staging (one time; this is what devices would upload) ----
if [ ! -d "$WORK/stage/staging" ]; then
  $A6CAS keygen -dir "$WORK/keys"
  m stage -- $A6CAS stage -src "$CORPUS" -out "$WORK/stage" -keys "$WORK/keys" 2>> "$OUT/run.log"
fi
samples_from_manifest() {
  python3 - "$1" "$SAMPLES" <<'EOF'
import json, random, sys
s = [json.loads(l)["sha256"] for l in open(sys.argv[1] + "/manifest/manifest.jsonl") if '"t":"blob"' in l]
random.seed(42); print("\n".join(random.sample(s, min(int(sys.argv[2]), len(s)))))
EOF
}

# ---- 2. plain CAS and OCFL variants (a6cas) ----
for layout in cas ocfl; do
  want $layout || continue
  S=$WORK/$layout; rm -rf "$S"; mkdir -p "$S"
  $A6CAS init -store "$S/store" -layout $layout -devices "$WORK/stage/devices.json"
  drop; log "ingest $layout"
  m ingest engine=$layout -- $A6CAS ingest -store "$S/store" -catalog "$S/catalog.db" -staging "$WORK/stage/staging" \
      -ingest-key "$WORK/keys/ingest-e1.key" -rcpt "$WORK/keys/stored-recipients.txt" \
      -family "$WORK/keys/family-secret.hex" > "$S/ingest.out" 2> "$S/ingest.err"
  note "{\"engine\":\"$layout\",\"ingest_summary\":\"$(tail -1 "$S/ingest.err" | tr -d '"')\",\"acks\":$(grep -c '^ACK' "$S/ingest.out"),\"rejects\":$(grep -c '^REJECT' "$S/ingest.out" || true),\"store_bytes\":$(du -sb "$S/store" | cut -f1),\"store_files\":$(find "$S/store" -type f | wc -l),\"catalog_bytes\":$(du -cb "$S"/catalog.db* | tail -1 | cut -f1)}"
  drop; log "audit $layout"
  m audit engine=$layout -- $A6CAS audit -store "$S/store" > "$S/audit.json"
  python3 -c "import json,sys;d=json.load(open(sys.argv[1]));d.pop('problems');d['engine']=sys.argv[2];d['label']='audit-detail';print(json.dumps(d))" "$S/audit.json" $layout >> "$RES"
  drop; log "single-file restores $layout"
  for h in $(samples_from_manifest "$S/store"); do
    m get engine=$layout -- $A6CAS get -store "$S/store" -archive-key "$WORK/keys/archive.key" -sha256 "$h" -out "$S/get.tmp" >> "$S/get.jsonl"
  done
  note "{\"engine\":\"$layout\",\"label\":\"get-check\",\"sha256_ok\":$(grep -c '"sha256_ok":true' "$S/get.jsonl"),\"of\":$(wc -l < "$S/get.jsonl")}"
  rm -f "$S/get.tmp"
  log "catalog rebuild $layout"
  m rebuild engine=$layout -- $A6CAS rebuild -store "$S/store" -out "$S/rebuilt.db" -archive-key "$WORK/keys/archive.key" 2> "$S/rebuild.err"
  $A6CAS export -catalog "$S/catalog.db" > "$S/e1"; $A6CAS export -catalog "$S/rebuilt.db" > "$S/e2"
  note "{\"engine\":\"$layout\",\"label\":\"rebuild-check\",\"byte_identical\":$(cmp -s "$S/e1" "$S/e2" && echo true || echo false)}"
  if [ $layout = ocfl ] && command -v ocfl-validate.py > /dev/null; then
    m ocfl-validate engine=ocfl -- ocfl-validate.py "$S/store/ocfl" > "$S/ocfl-validate.txt" 2>&1 || true
  fi
done

# ---- 3. restic comparator: plaintext source, one snapshot per BATCH unique files ----
if want restic; then
  R=$WORK/restic; rm -rf "$R"; mkdir -p "$R"
  export RESTIC_PASSWORD=bakeoff-throwaway RESTIC_REPOSITORY=$R/repo RESTIC_CACHE_DIR=$R/cache
  $RESTIC init -q
  log "restic: hashing corpus for the sha256 -> path map (stays in WORK)"
  find "$CORPUS" -type f -print0 | xargs -0 sha256sum | sort -u -k1,1 > "$R/map.txt"
  split -l "$BATCH" -d -a 5 "$R/map.txt" "$R/batch."
  drop; log "restic backup"
  for b in "$R"/batch.?????; do
    cut -c67- "$b" > "$b.list"
    m restic-backup engine=restic -- $RESTIC backup -q --files-from-verbatim "$b.list" --tag "$(basename "$b")"
  done
  note "{\"engine\":\"restic\",\"label\":\"restic-repo\",\"repo_bytes\":$(du -sb "$R/repo" | cut -f1),\"pack_files\":$(find "$R/repo/data" -type f | wc -l),\"snapshots\":$(ls "$R"/batch.?????.list | wc -l)}"
  drop; log "restic check --read-data"
  m restic-check-read-data engine=restic -- $RESTIC check --read-data -q
  drop; log "restic single-file restores"
  python3 - "$R/map.txt" "$SAMPLES" > "$R/samples.txt" <<'EOF'
import random, sys
rows = [l.rstrip("\n").split("  ", 1) for l in open(sys.argv[1])]
random.seed(42)
for h, p in random.sample(rows, min(int(sys.argv[2]), len(rows))):
    print(h + "\t" + p)
EOF
  ok=0; n=0
  while IFS=$'\t' read -r h p; do
    tag=$(basename "$(grep -l -F -x -- "$p" "$R"/batch.?????.list | head -1)" .list)
    m restic-dump engine=restic -- $RESTIC dump --tag "$tag" latest "$p" > "$R/dump.tmp"
    [ "$(sha256sum < "$R/dump.tmp" | cut -c1-64)" = "$h" ] && ok=$((ok+1)); n=$((n+1))
  done < "$R/samples.txt"
  note "{\"engine\":\"restic\",\"label\":\"dump-check\",\"sha256_ok\":$ok,\"of\":$n}"
  rm -f "$R/dump.tmp"
fi
log "done. Aggregates in $RES; summarise with: python3 $HERE/summarise.py $RES"
