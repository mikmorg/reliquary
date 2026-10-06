#!/usr/bin/env bash
# F1-S1 probe: Plakar v1.1.7 store served by 'plakar server' (delete disabled by default).
# Questions: can a writing client delete snapshots? does the writing client hold the decryption key?
# Data: SYN only; local; no real R2.
set -u
BIN=${BIN:?}; export PATH=$BIN:$PATH
W=$(mktemp -d -p "${TMPDIR:-/tmp}"); # plakar's cache agent uses a unix socket under $HOME; long paths exceed the 108-byte sun_path limit
H=$(mktemp -d /tmp/pk.XXXX)
trap 'kill $PS 2>/dev/null; rm -rf "$W" "$H"' EXIT
export HOME=$H PLAKAR_PASSPHRASE=family-store-passphrase; mkdir -p $W/src $W/restore
res(){ printf '%-58s %s\n' "$1" "$2"; }
plakar -disable-security-check >/dev/null 2>&1
head -c 2000000 /dev/urandom > $W/src/photo1.bin
timeout 60 plakar at $W/store create >$W/c.log 2>&1 && res "create encrypted store (passphrase, Argon2id KDF)" OK || { res create FAIL; cat $W/c.log; }
timeout 60 plakar at $W/store server -listen 127.0.0.1:19876 >$W/srv.log 2>&1 & PS=$!; sleep 2
timeout 120 plakar at http://127.0.0.1:19876 backup $W/src >$W/b.log 2>&1 && res "client backup through plakar server" OK || { res "client backup" "FAIL: $(tail -2 $W/b.log)"; }
SNAP=$(timeout 60 plakar at http://127.0.0.1:19876 ls 2>/dev/null | awk 'NR==1{print $2}')
res "snapshot id" "${SNAP:-none}"
timeout 120 plakar at http://127.0.0.1:19876 restore -to $W/restore $SNAP >/dev/null 2>&1
F=$(find $W/restore -name photo1.bin | head -1); [ -n "$F" ] && cmp -s "$F" $W/src/photo1.bin && res "same client restores (decrypts) with the passphrase it writes with" "YES (bytes identical)" || res "restore" "not verified ($(ls -R $W/restore | head -3 | tr '\n' ' '))"
files(){ echo "files=$(find $W/store -type f | wc -l) bytes=$(du -sb $W/store | cut -f1)"; }
before=$(files)
timeout 60 plakar at http://127.0.0.1:19876 rm -apply $SNAP >$W/rm.log 2>&1; rc=$?
N=$(timeout 60 plakar at http://127.0.0.1:19876 ls 2>/dev/null | wc -l)
res "client 'plakar rm -apply <snap>' via server (delete off)" "exit=$rc, snapshots listed afterwards=$N; $(tail -1 $W/rm.log | cut -c1-80)"
res "store on disk before/after rm (server has delete off)" "before [$before] after [$(files)]"
unset PLAKAR_PASSPHRASE
timeout 30 plakar at http://127.0.0.1:19876 backup $W/src </dev/null >$W/nopw.log 2>&1; res "client backup WITHOUT passphrase (write-only device?)" "exit=$? $(tail -1 $W/nopw.log | cut -c1-70)"
res "who listens" "plakar server accepts inbound HTTP; clients dial it"
