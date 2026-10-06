#!/bin/sh
# Kit A2-S1: X25519 vs post-quantum (mlkem768x25519) envelope cost on an Android phone over adb.
# THROWAWAY spike tooling. Run on the computer the phone is paired with. Needs: adb on PATH, the
# phone in developer mode, and the a2-envelope-spike binary built for the phone (README.md, step 3).
#
#   ./run-android.sh <path-to-a2-envelope-spike-binary> <label>     e.g. ./run-android.sh ./a2-envelope-spike lowend
#
# Everything the benchmark encrypts is random bytes it makes in memory. It never reads the camera
# roll or any user file. Its only file is the binary in /data/local/tmp/a2, deleted at the end.
set -eu
BIN="$1"
LABEL="$2"
SOAK_S="${SOAK_S:-900}"        # seconds per soak (default 15 min each, X25519 then PQ)
COOL_S="${COOL_S:-600}"        # cool-down between the two soaks
SOAK_SIZE="${SOAK_SIZE:-102400}"  # object size for the soaks (100 KiB: a small-object worst case)
OUT="results-$LABEL-$(date +%Y%m%d-%H%M%S)"
D=/data/local/tmp/a2
mkdir -p "$OUT"

say() { printf '\n== %s\n' "$*"; }
battery() { adb shell dumpsys battery | grep -i -E "level|charge counter|temperature|AC powered|USB powered|Wireless powered"; }
thermal() { adb shell dumpsys thermalservice 2>/dev/null | grep -i -E "status|Temperature\{" | head -20 || true; }

say "Device facts (model, Android version, CPU ABIs, CPU features)"
{
  adb shell getprop ro.product.manufacturer
  adb shell getprop ro.product.model
  adb shell getprop ro.build.version.release
  adb shell getprop ro.product.cpu.abilist
  adb shell getprop ro.soc.model || true
  adb shell cat /proc/cpuinfo | grep -i -E "^(Features|CPU part|Hardware)" | sort | uniq -c
  adb shell cat /proc/meminfo | head -1
} | tee "$OUT/device.txt"

say "Push the benchmark"
adb shell mkdir -p "$D"
adb push "$BIN" "$D/a2" >/dev/null
adb shell chmod 755 "$D/a2"

say "Header cost per object: generate (device side) and open, 1 x X25519 / 1 x PQ / 2 x PQ. 3 rounds."
for r in 1 2 3; do adb shell "$D/a2" bench-kem --iters 500; done | tee "$OUT/bench-kem.txt"

say "Whole-object encryption throughput by object size (in memory), 2 rounds per size"
for spec in "16384 500" "102400 300" "1048576 60" "4194304 20" "26214400 4"; do
  set -- $spec
  for r in 1 2; do adb shell "$D/a2" bench-obj --size "$1" --count "$2"; done
done | tee "$OUT/bench-obj.txt"

say "Battery and thermal BEFORE soak 1 (X25519)"
{ date -u +%FT%TZ; battery; thermal; } | tee "$OUT/soak-x25519-before.txt"
adb shell "$D/a2" soak --profile x25519 --size "$SOAK_SIZE" --seconds "$SOAK_S" | tee "$OUT/soak-x25519.jsonl"
{ date -u +%FT%TZ; battery; thermal; } | tee "$OUT/soak-x25519-after.txt"

say "Cool-down for $COOL_S s (leave the phone on the table, screen off)"
sleep "$COOL_S"

say "Battery and thermal BEFORE soak 2 (PQ, one mlkem768x25519 stanza)"
{ date -u +%FT%TZ; battery; thermal; } | tee "$OUT/soak-pq-before.txt"
adb shell "$D/a2" soak --profile pq --size "$SOAK_SIZE" --seconds "$SOAK_S" | tee "$OUT/soak-pq.jsonl"
{ date -u +%FT%TZ; battery; thermal; } | tee "$OUT/soak-pq-after.txt"

say "Clean up the phone"
adb shell rm -rf "$D"
echo "Done. Results are in $OUT/. Fill in the Results section of README.md from them."
