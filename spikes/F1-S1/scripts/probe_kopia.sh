#!/usr/bin/env bash
# F1-S1 probe: Kopia v0.23.1 repository server with two device users.
# Questions: can a device delete its own history under default ACLs? can ACLs make it append-only?
# does the device hold the repository encryption key? is content deduplicated and readable across users?
# Data: SYN only. Local filesystem repo, server on 127.0.0.1 with a self-signed cert. No real R2.
set -u
BIN=${BIN:?}; export PATH=$BIN:$PATH
W=$(mktemp -d -p "${TMPDIR:-/tmp}"); trap 'kill $KS 2>/dev/null; rm -rf "$W"' EXIT
export KOPIA_CHECK_FOR_UPDATES=false KOPIA_LOG_DIR=$W/logs KOPIA_CACHE_DIRECTORY=$W/cache
res(){ printf '%-62s %s\n' "$1" "$2"; }
mkdir -p $W/repo $W/src1 $W/src2 $W/restore
head -c 3000000 /dev/urandom > $W/src1/photo1.bin; cp $W/src1/photo1.bin $W/src2/same-photo.bin
A="--config-file=$W/admin.config"; D1="--config-file=$W/dev1.config"; D2="--config-file=$W/dev2.config"
kopia $A repo create filesystem --path=$W/repo --password=REPO-PW >/dev/null 2>&1 && res "admin creates repo (symmetric repo password)" OK
kopia $A server user add dev1@host1 --user-password=dev1pw >/dev/null 2>&1
kopia $A server user add dev2@host2 --user-password=dev2pw >/dev/null 2>&1
kopia $A server acl enable >/dev/null 2>&1 && res "admin enables ACLs (installs default ACL entries)" OK
echo "--- default ACL entries"; kopia $A server acl list 2>&1 | sed 's/^/    /'
kopia $A server start --address=https://127.0.0.1:51515 --tls-generate-cert --tls-cert-file=$W/c.pem --tls-key-file=$W/k.pem \
   --server-username=admin --server-password=adminpw --password=REPO-PW >$W/server.log 2>&1 & KS=$!
for i in $(seq 1 30); do grep -q "SERVER CERT SHA256" $W/server.log 2>/dev/null && break; sleep 1; done
FP=$(grep -o 'SERVER CERT SHA256: [0-9a-f]*' $W/server.log | awk '{print $4}'); sleep 2
kopia $D1 repo connect server --url=https://127.0.0.1:51515 --server-cert-fingerprint=$FP --override-username=dev1 --override-hostname=host1 --password=dev1pw >/dev/null 2>&1 && res "dev1 connects with user password only" OK
kopia $D2 repo connect server --url=https://127.0.0.1:51515 --server-cert-fingerprint=$FP --override-username=dev2 --override-hostname=host2 --password=dev2pw >/dev/null 2>&1 && res "dev2 connects with user password only" OK
grep -qi "REPO-PW\|masterKey\|encryption" $W/dev1.config && res "device config holds repo password/key?" "FOUND" || res "device config holds repo password or encryption key?" "NO (config: $(python3 -c "import json;print(','.join(json.load(open('$W/dev1.config'))['storage']['type'] if False else json.load(open('$W/dev1.config')).keys()))"))"
kopia $D1 snapshot create $W/src1 >/dev/null 2>&1 && res "dev1 snapshot (append)" OK
before=$(kopia $A content list 2>/dev/null | wc -l)
kopia $D2 snapshot create $W/src2 >/dev/null 2>&1 && res "dev2 snapshot of an identical 3 MB file" OK
after=$(kopia $A content list 2>/dev/null | wc -l)
res "repo content count before/after dev2 snapshot" "$before -> $after"
O1=$(kopia $D1 snapshot list --json 2>/dev/null | python3 -c 'import json,sys;print(json.load(sys.stdin)[0]["rootEntry"]["obj"])')
O2=$(kopia $D2 snapshot list --json 2>/dev/null | python3 -c 'import json,sys;print(json.load(sys.stdin)[0]["rootEntry"]["obj"])')
F1=$(kopia $D1 ls -o $O1 2>/dev/null | awk '{print $1}' | head -1); F2=$(kopia $D2 ls -o $O2 2>/dev/null | awk '{print $1}' | head -1)
[ -n "$F1" ] && [ "$F1" = "$F2" ] && res "identical file from dev1 and dev2 -> same object ID (cross-user dedup)" "YES ($F1)" || res "identical file -> same object ID" "NO ($F1 vs $F2)"
kopia $D2 show $F1 2>/dev/null | cmp -s - $W/src1/photo1.bin && res "dev2 reads dev1's file bytes by object ID" "YES" 
OID=$(kopia $D1 snapshot list --json 2>/dev/null | python3 -c 'import json,sys;print(json.load(sys.stdin)[0]["rootEntry"]["obj"])')
SID=$(kopia $D1 snapshot list --json 2>/dev/null | python3 -c 'import json,sys;print(json.load(sys.stdin)[0]["id"])')
kopia $D2 snapshot list --all 2>/dev/null | grep -q host1 && res "dev2 lists dev1's snapshots" YES || res "dev2 lists dev1's snapshots" "NO (manifest ACL)"
kopia $D2 ls $OID >/dev/null 2>&1 && res "dev2 reads dev1's snapshot root by object ID" "YES: $(kopia $D2 ls $OID 2>/dev/null | head -1)" || res "dev2 reads dev1's snapshot root by object ID" "NO"
FOID=$(kopia $D1 ls -l $OID 2>/dev/null | awk '/photo1.bin/{print $0}' ) 
kopia $D1 snapshot restore $OID $W/restore >/dev/null 2>&1 && cmp -s $W/restore/photo1.bin $W/src1/photo1.bin && res "dev1 restores (server decrypts for it)" "YES (bytes identical)"
kopia $D1 snapshot delete $SID --delete >$W/del.log 2>&1; rc=$?
kopia $D1 snapshot list --json 2>/dev/null | grep -q "$SID" && st="still present" || st="GONE"
res "dev1 deletes its own snapshot (default ACL)" "exit=$rc, snapshot $st"
# Tighten: replace default FULL-on-own-snapshots with APPEND, then retry
kopia $D1 snapshot create $W/src1 >/dev/null 2>&1
SID2=$(kopia $D1 snapshot list --json 2>/dev/null | python3 -c 'import json,sys;print(json.load(sys.stdin)[-1]["id"])')
kopia $A server acl list --json 2>/dev/null > $W/acl.json
python3 - "$W/acl.json" > $W/fullids <<'PY'
import json,sys
for e in json.load(open(sys.argv[1])):
    a=e.get("acl",e); 
    if str(a.get("access","")).upper()=="FULL" and a.get("user")=="*@*": print(e.get("id",""), json.dumps(a.get("target")))
PY
echo "--- default FULL entries for *@* (id, target):"; sed 's/^/    /' $W/fullids
while read -r id tgt; do [ "$(echo $tgt | grep -c user\")" = 1 ] && continue; kopia $A server acl delete $id --delete >/dev/null 2>&1; done < $W/fullids
kopia $A server acl add --user='*@*' --target='type=snapshot,username=OWN_USER,hostname=OWN_HOST' --access=APPEND >/dev/null 2>&1
kopia $A server acl add --user='*@*' --target='type=policy,username=OWN_USER,hostname=OWN_HOST' --access=READ >/dev/null 2>&1
echo "--- tightened ACL entries"; kopia $A server acl list 2>&1 | sed 's/^/    /'
# restart the server so it certainly reloads ACL manifests (same cert, so the pinned fingerprint still matches)
kill $KS; wait $KS 2>/dev/null
kopia $A server start --address=https://127.0.0.1:51515 --tls-cert-file=$W/c.pem --tls-key-file=$W/k.pem \
   --server-username=admin --server-password=adminpw --password=REPO-PW >$W/server2.log 2>&1 & KS=$!
for i in $(seq 1 30); do curl -sk https://127.0.0.1:51515/ >/dev/null 2>&1 && break; sleep 1; done; sleep 2
res "server restarted after ACL change" "OK"
kopia $D1 snapshot delete $SID2 --delete >$W/del2.log 2>&1; rc=$?
kopia $D1 snapshot list --json 2>/dev/null | grep -q "$SID2" && st="still present" || st="GONE"
res "dev1 deletes own snapshot after ACL tightened to APPEND" "exit=$rc, snapshot $st: $(grep -io 'access denied\|permission denied\|not allowed[^\n]*' $W/del2.log | head -1)"
kopia $D1 snapshot create $W/src1 >/dev/null 2>&1 && res "dev1 can still append after tightening" YES
grep -i "delete\|denied\|permission" $W/server2.log | head -3 | sed 's/^/    server2.log: /'  || res "dev1 can still append after tightening" "NO: $(kopia $D1 snapshot create $W/src1 2>&1 | tail -1)"
res "who listens" "kopia server accepts inbound gRPC/HTTPS; clients dial it"
