#!/bin/sh
# Kit A1-S1: run the hash benchmark on an Android phone over adb (THROWAWAY spike tooling).
# Run on the computer the phone is paired with. Needs: adb on PATH, the phone in developer mode,
# and the a1-hashbench binary built for the phone (see README.md, "Build the benchmark").
#
#   ./run-android.sh <path-to-a1-hashbench-binary> <label>      e.g. ./run-android.sh ./a1-hashbench lowend
#
# Everything the script writes is synthetic (random bytes) and goes to /data/local/tmp/a1 on the
# phone. It never reads the camera roll or any user file. It deletes its files at the end.
set -eu
BIN="$1"
LABEL="$2"
OUT="results-$LABEL-$(date +%Y%m%d-%H%M%S)"
D=/data/local/tmp/a1
mkdir -p "$OUT"

say() { printf '\n== %s\n' "$*"; }

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

battery() { adb shell dumpsys battery | grep -i -E "level|charge counter|temperature|AC powered|USB powered|Wireless powered"; }
thermal() { adb shell dumpsys thermalservice 2>/dev/null | grep -i -E "status|Temperature\{" | head -20 || true; }

say "Push the benchmark"
adb shell mkdir -p "$D"
adb push "$BIN" "$D/a1-hashbench" >/dev/null
adb shell chmod 755 "$D/a1-hashbench"
adb shell "$D/a1-hashbench" info | tee "$OUT/info.jsonl"

say "In-memory benchmark (256 MiB buffer, 5 runs). Takes a few minutes."
adb shell "$D/a1-hashbench" mem 256 5 | tee "$OUT/mem.jsonl"

say "Small-file ladder (0 B .. 16 MiB)"
adb shell "$D/a1-hashbench" ladder | tee "$OUT/ladder.jsonl"

say "Make a 4 GiB + 1 byte synthetic file on internal storage (needs about 4.5 GB free)"
adb shell "dd if=/dev/urandom of=$D/f_4GiB_plus_1 bs=1048576 count=4096 2>/dev/null && printf x >> $D/f_4GiB_plus_1 && ls -l $D/f_4GiB_plus_1"

say "File benchmark, cold-ish (fadvise DONTNEED on the file; root is not needed for that), 2 runs"
adb shell "$D/a1-hashbench" file "$D/f_4GiB_plus_1" 2 cold | tee "$OUT/file-cold.jsonl"

say "Battery and thermal state BEFORE the soak"
date -u +%FT%TZ | tee "$OUT/soak-before.txt"
battery | tee -a "$OUT/soak-before.txt"
thermal | tee -a "$OUT/soak-before.txt"

say "Soak: 30 minutes of C2 (SHA-256 + HMAC over the digest) over the file. Watch MB/s per 10 s window."
adb shell "$D/a1-hashbench" soak "$D/f_4GiB_plus_1" 1800 | tee "$OUT/soak.jsonl"

say "Battery and thermal state AFTER the soak"
date -u +%FT%TZ | tee "$OUT/soak-after.txt"
battery | tee -a "$OUT/soak-after.txt"
thermal | tee -a "$OUT/soak-after.txt"

say "Clean up the phone"
adb shell rm -rf "$D"
echo "Done. Results are in $OUT/. Fill in the Results section of README.md from them."
