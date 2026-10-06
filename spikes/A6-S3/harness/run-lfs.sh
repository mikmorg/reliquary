#!/bin/bash
# A6-S3 power-cut emulation on LazyFS (unsynced data dropped after each kill). Emulated, not a real power cut.
B=${A6CAS:-a6cas}
H=$(cd "$(dirname "$0")" && pwd)/crash.py
D=${D:-/dev/shm/a6crash}
M=${M:-/dev/shm/lfs.mnt}  # LazyFS mount (see README)
run() {
  name=$1; shift
  rm -rf "$M/work-$name" "$D/ev/s3-$name.jsonl"
  mkdir -p "$M/work-$name"
  TIMEFORMAT="real %R s, user %U s, sys %S s"; time python3 "$H" --a6cas "$B" --corpus "$D/corpus" --keys "$D/keys" --work "$M/work-$name" \
    --powercut --evidence "$D/ev/s3-$name.jsonl" "$@" > "$D/ev/s3-$name.summary.json" 2> "$D/ev/s3-$name.err.txt"
  echo "$name rc=$?"
  rm -rf "$M/work-$name"
}
run lfs-kill9-cas --kills 50 --max-delay 3 --seed 71
run lfs-crashpoints-cas --kills 50 --max-delay 6 --seed 72 --crashpoint any --crash-prob 0.01
run lfs-kill9-ocfl --kills 30 --max-delay 3 --seed 73 --layout ocfl
run lfs-nofsync-NEGATIVE-CONTROL --kills 10 --max-delay 3 --seed 74 --nofsync
