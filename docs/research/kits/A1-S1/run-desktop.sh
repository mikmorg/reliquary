#!/bin/sh
# Kit A1-S1: run the hash benchmark on a Mac or Linux computer (THROWAWAY spike tooling).
# Windows: follow the PowerShell steps in README.md instead.
#
#   ./run-desktop.sh <label>        run from the repository root's spikes/A1-S1 folder, e.g. ./../../docs/research/kits/A1-S1/run-desktop.sh mac-m2
#
# Writes only synthetic data, in a temporary folder that it deletes at the end.
set -eu
LABEL="$1"
OUT="$PWD/results-$LABEL-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$OUT"
cargo build --release
BIN=./target/release/a1-hashbench
TMP=$(mktemp -d)

uname -a | tee "$OUT/device.txt"
if [ "$(uname)" = "Darwin" ]; then
  sysctl -n machdep.cpu.brand_string hw.memsize | tee -a "$OUT/device.txt"
  sw_vers | tee -a "$OUT/device.txt"
  pmset -g batt | tee -a "$OUT/device.txt"
else
  grep -m1 "model name" /proc/cpuinfo | tee -a "$OUT/device.txt" || true
  grep -m1 MemTotal /proc/meminfo | tee -a "$OUT/device.txt"
fi

$BIN mem 1024 5 | tee "$OUT/mem.jsonl"
$BIN ladder | tee "$OUT/ladder.jsonl"

# 4 GiB + 1 byte synthetic file
dd if=/dev/urandom of="$TMP/f_4GiB_plus_1" bs=1048576 count=4096 2>/dev/null
printf x >> "$TMP/f_4GiB_plus_1"
$BIN file "$TMP/f_4GiB_plus_1" 2 cold | tee "$OUT/file-cold.jsonl"

echo "Battery before soak:" | tee "$OUT/soak-before.txt"
date -u +%FT%TZ | tee -a "$OUT/soak-before.txt"
if [ "$(uname)" = "Darwin" ]; then pmset -g batt | tee -a "$OUT/soak-before.txt"; else cat /sys/class/power_supply/BAT*/capacity 2>/dev/null | tee -a "$OUT/soak-before.txt" || true; fi
$BIN soak "$TMP/f_4GiB_plus_1" 1800 | tee "$OUT/soak.jsonl"
echo "Battery after soak:" | tee "$OUT/soak-after.txt"
date -u +%FT%TZ | tee -a "$OUT/soak-after.txt"
if [ "$(uname)" = "Darwin" ]; then pmset -g batt | tee -a "$OUT/soak-after.txt"; else cat /sys/class/power_supply/BAT*/capacity 2>/dev/null | tee -a "$OUT/soak-after.txt" || true; fi

rm -rf "$TMP"
echo "Done. Results are in $OUT/."
