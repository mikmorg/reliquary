#!/usr/bin/env bash
# F1-S1 probe: restic v0.19.1 + rest-server v0.14.0 in --append-only --private-repos mode.
# Question: which Reliquary settled requirements does "restic per device, append-only repo" meet?
# Data: SYN only (random bytes generated here). Everything local (127.0.0.1). No real R2.
set -u
BIN=${BIN:?set BIN to dir with restic and rest-server}
W=$(mktemp -d -p "${TMPDIR:-/tmp}"); trap 'kill $RS 2>/dev/null; rm -rf "$W"' EXIT
export PATH=$BIN:$PATH RESTIC_CACHE_DIR=$W/cache
res(){ printf '%-58s %s\n' "$1" "$2"; }
mkdir -p $W/data $W/src1 $W/src2 $W/restore
head -c 3000000 /dev/urandom > $W/src1/photo1.bin; cp $W/src1/photo1.bin $W/src2/same-photo.bin
head -c 1000000 /dev/urandom > $W/src1/doc1.bin
sha(){ python3 -c "import hashlib,base64,sys;print('{SHA}'+base64.b64encode(hashlib.sha1(sys.argv[1].encode()).digest()).decode())" "$1"; }
{ echo "dev1:$(sha dev1pw)"; echo "dev2:$(sha dev2pw)"; } > $W/data/.htpasswd   # {SHA} is one of rest-server's accepted formats
rest-server --path $W/data --listen 127.0.0.1:18000 --append-only --private-repos --htpasswd-file $W/data/.htpasswd >$W/rs.log 2>&1 & RS=$!
sleep 1
R1=rest:http://dev1:dev1pw@127.0.0.1:18000/dev1/
R2=rest:http://dev2:dev2pw@127.0.0.1:18000/dev2/
export RESTIC_PASSWORD=device1-repo-password
restic -r $R1 init -q >/dev/null 2>&1 && res "init dev1 repo over rest-server" OK
restic -r $R1 backup -q $W/src1 >/dev/null 2>&1 && res "backup (append) by dev1" OK
SNAP=$(restic -r $R1 snapshots --json 2>/dev/null | python3 -c 'import json,sys;print(json.load(sys.stdin)[0]["short_id"])')
restic -r $R1 forget $SNAP >$W/f.log 2>&1; res "dev1 'restic forget <snap>' (delete history)" "exit=$? $(grep -oi 'forbidden\|403\|error[^\n]*' $W/f.log | head -1)"
cnt(){ echo "snapshots=$(ls $W/data/dev1/snapshots | wc -l) packs=$(find $W/data/dev1/data -type f | wc -l)"; }
before=$(cnt); restic -r $R1 prune >$W/p.log 2>&1; rc=$?
res "dev1 'restic prune' (nothing forgotten, so nothing to delete)" "exit=$rc; before [$before] after [$(cnt)]"
# raw HTTP delete / overwrite of an existing snapshot file with the device credential
SF=$(ls $W/data/dev1/snapshots | head -1)
code=$(curl -s -o /dev/null -w '%{http_code}' -X DELETE http://dev1:dev1pw@127.0.0.1:18000/dev1/snapshots/$SF); res "raw HTTP DELETE of existing snapshot file" "HTTP $code"
code=$(curl -s -o /dev/null -w '%{http_code}' -X POST --data-binary garbage http://dev1:dev1pw@127.0.0.1:18000/dev1/snapshots/$SF); res "raw HTTP overwrite (POST) of existing snapshot file" "HTTP $code"
DF=$(find $W/data/dev1/data -type f | head -1); DID=$(basename $DF); DPRE=$(basename $(dirname $DF))
code=$(curl -s -o /dev/null -w '%{http_code}' -X DELETE http://dev1:dev1pw@127.0.0.1:18000/dev1/data/$DID); res "raw HTTP DELETE of existing data pack" "HTTP $code"
# device can read everything it ever wrote (symmetric repo key)
restic -r $R1 restore latest --target $W/restore -q >/dev/null 2>&1; cmp -s $W/restore$W/src1/photo1.bin $W/src1/photo1.bin && res "dev1 restores (decrypts) its whole history" "YES (bytes identical)"
restic -r $R1 cat masterkey >$W/mk.json 2>/dev/null && res "dev1 can print the repository master key" "YES ($(python3 -c "import json;print(','.join(json.load(open('$W/mk.json')).keys()))" ))"
# forged timestamp (restic issue #22057 scenario)
restic -r $R1 backup -q --time "2001-01-01 00:00:00" --host other-laptop $W/src1 >/dev/null 2>&1 && res "dev1 writes snapshot with forged --time and --host" "ACCEPTED"
# key management under append-only
restic -r $R1 key list --json >$W/k.json 2>/dev/null; KID=$(python3 -c "import json;print(json.load(open('$W/k.json'))[0]['id'])")
printf 'newpw\nnewpw\n' > $W/np; restic -r $R1 key add --new-password-file $W/np -q >/dev/null 2>&1; res "dev1 'key add' (new password for same master key)" "exit=$?"
restic -r $R1 key remove $KID >/dev/null 2>&1; res "dev1 'key remove' of original key" "exit=$?"
# cross-device isolation and dedup
code=$(curl -s -o /dev/null -w '%{http_code}' http://dev2:dev2pw@127.0.0.1:18000/dev1/config); res "dev2 reads dev1 repo config (--private-repos)" "HTTP $code"
export RESTIC_PASSWORD=device2-repo-password
restic -r $R2 init -q >/dev/null 2>&1; restic -r $R2 backup -q $W/src2 >/dev/null 2>&1
b1=$(du -sb $W/data/dev1/data | cut -f1); b2=$(du -sb $W/data/dev2/data | cut -f1)
res "cross-device dedup of identical 3 MB file" "none: dev1 data=$b1 B, dev2 data=$b2 B (separate repos/keys)"
# blob IDs are unkeyed SHA-256 of plaintext: compute and compare with index
export RESTIC_PASSWORD=device1-repo-password
H=$(sha256sum $W/src1/doc1.bin | cut -d' ' -f1)
restic -r $R1 list blobs 2>/dev/null | grep -q $H && res "blob ID == plain SHA-256(file) for a 1 MB file (single chunk)" "YES (unkeyed; visible to key holders only)" || res "blob ID == plain SHA-256(file)" "not found (file may be chunked)"
res "who listens" "rest-server (server) accepts inbound HTTP; client dials it"
echo "--- rest-server log tail"; tail -5 $W/rs.log
