#!/bin/bash
# A6-S3 crash runs on tmpfs (process-crash atomicity; kernel page cache survives).
B=${A6CAS:-a6cas}
H=$(cd "$(dirname "$0")" && pwd)/crash.py
D=${D:-/dev/shm/a6crash}  # holds corpus/ and keys/ from `a6cas keygen` + `a6cas gen -n 600 -scale 0.05 -seed 3`
mkdir -p "$D/ev"
run() {
  name=$1; shift
  rm -rf "$D/work-$name" "$D/ev/s3-$name.jsonl"
  mkdir -p "$D/work-$name"
  TIMEFORMAT="real %R s, user %U s, sys %S s"; time python3 "$H" --a6cas "$B" --corpus "$D/corpus" --keys "$D/keys" --work "$D/work-$name" \
    --evidence "$D/ev/s3-$name.jsonl" "$@" > "$D/ev/s3-$name.summary.json" 2> "$D/ev/s3-$name.time.txt"
  echo "$name rc=$?"
}
for spec in "$@"; do
  case $spec in
    kill9-cas) run kill9-cas --kills 100 --max-delay 0.8 --seed 61 ;;
    crashpoints-cas) run crashpoints-cas --kills 100 --max-delay 3 --seed 62 --crashpoint any --crash-prob 0.01 ;;
    kill9-ocfl) run kill9-ocfl --kills 100 --max-delay 0.8 --seed 63 --layout ocfl ;;
    crashpoints-ocfl) run crashpoints-ocfl --kills 100 --max-delay 3 --seed 64 --layout ocfl --crashpoint any --crash-prob 0.01 ;;
  esac
done
