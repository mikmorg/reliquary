#!/usr/bin/env bash
# A6-S1 posture probes (THROWAWAY). Reproduces spikes/A6-S1/evidence/*. Data class SYN.
# Needs: a6cas (spikes/A6-S3/a6cas), retrofit (./retrofit), age + age-keygen (Go, v1.3.1),
# restic 0.19.1, kopia v0.23.1, python3. Run on tmpfs; nothing here is homelab evidence.
#   usage: probe.sh WORKDIR
set -euo pipefail
W=$1; mkdir -p "$W"; cd "$W"
HERE=$(cd "$(dirname "$0")" && pwd)
# 1. corpus and a complete posture-A' store (same seed as A6-S3)
a6cas keygen -dir keys
a6cas gen -out corpus -keys keys -n 600 -dup 0.1 -scale 0.05 -seed 3
a6cas init -store store -devices corpus/devices.json
a6cas ingest -store store -catalog catalog.db -staging corpus/staging -ingest-key keys/ingest-e1.key \
  -rcpt keys/stored-recipients.txt -family keys/family-secret.hex > /dev/null
# 2. retrofit a third recipient later: header-only rewrap vs full re-encryption (x3 each)
age-keygen -o recovery2.key 2>/dev/null
{ cat keys/stored-recipients.txt; age-keygen -y recovery2.key; } > new-rcpts.txt
mkdir -p flat-orig; find store/blobs -name '*.age' -exec cp {} flat-orig/ \;
for i in 1 2 3; do for m in rewrap reencrypt; do rm -rf out-$m
  retrofit $m -in store/blobs -out out-$m -id keys/archive.key -rcpt new-rcpts.txt | tee -a retrofit-runs.jsonl; done; done
for m in rewrap reencrypt; do retrofit check -dir out-$m -id recovery2.key -orig flat-orig | tee -a retrofit-check.jsonl; done
retrofit check -dir out-rewrap -id keys/archive.key | tee -a retrofit-check.jsonl
retrofit check -dir out-rewrap -id keys/ingest-e1.key | tee -a retrofit-check.jsonl || true
# 3. online-key exposure: posture A stores the device upload as is; A' stores the rewrapped object
ok=0; for f in corpus/staging/*.obj.age; do age -d -i keys/ingest-e1.key "$f" >/dev/null 2>&1 && ok=$((ok+1)); done; echo "A: $ok"
ok=0; for f in $(find store/blobs -name '*.age'); do age -d -i keys/ingest-e1.key "$f" >/dev/null 2>&1 && ok=$((ok+1)); done; echo "A': $ok"
# 4. plaintext for the comparators, restored with no Reliquary code (A6-S5 procedure)
AGE=age bash "$HERE/../A6-S5/restore-without-reliquary.sh" all store keys/archive.key plain
# 5. size and presence leak of the stored layout (Probe 4)
python3 -I "$HERE/size-leak.py" store plain
# 6. restic: password needs, keyless file-level fixity, key add, bit flip
echo -n throwaway-pass > pw; echo -n throwaway-recovery > pw2; export RESTIC_CACHE_DIR=$W/rcache
restic init -r rrepo --password-file pw; restic backup -q -r rrepo --password-file pw plain
RESTIC_PASSWORD= restic check -r rrepo --no-cache </dev/null || echo "rc=$? (expected: no password)"
time restic key add -r rrepo --password-file pw --new-password-file pw2
restic check -r rrepo --password-file pw2 --read-data
# 7. kopia: password needs and blob naming
export KOPIA_CONFIG_PATH=$W/kcfg/repo.config KOPIA_CHECK_FOR_UPDATES=false
kopia repository create filesystem --path krepo --password throwaway-pass; kopia snapshot create plain
kopia repository disconnect; KOPIA_PASSWORD= kopia repository connect filesystem --path krepo </dev/null || echo "rc=$? (expected)"
