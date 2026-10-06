#!/usr/bin/env bash
# E1-S1 CT rehearsal (SYN only). Builds the census, generates synthetic home folders, runs the
# census, audits file opens with strace, and checks output against generator truth and H3 §4.
# Usage: run_rehearsal.sh WORKDIR [BIGDIR]   (BIGDIR: where the ~500k-file tree goes, e.g. /dev/shm/x)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
W="$1"; BIG="${2:-}"
mkdir -p "$W"
echo "== host: $(uname -srm); $(nproc) vCPU; rustc $(rustc --version | cut -d' ' -f2); date $(date -u +%F)"
(cd "$HERE/census" && cargo build --release --features emulate-placeholders -q && cp target/release/census "$W/census-emu")
(cd "$HERE/census" && cargo build --release -q && cp target/release/census "$W/census-plain")
for t in x86_64-pc-windows-gnu aarch64-apple-darwin; do
  if (cd "$HERE/census" && cargo check --release -q --target "$t" 2>/dev/null); then echo "== cargo check $t: ok"; else echo "== cargo check $t: FAILED or target missing"; fi
done

echo "== generate SYN scale 1 on $(findmnt -no FSTYPE -T "$W")"
rm -rf "$W/syn1"; mkdir -p "$W/syn1"; python3 "$HERE/gen_home.py" "$W/syn1" 1 42
R="$W/syn1/home-Qx7-user"

echo "== correctness + H3 output check (--exif --list-candidate-folders)"
rm -rf "$W/out1"; "$W/census-emu" --root "$R" --exif --list-candidate-folders --out "$W/out1" --yes > "$W/run1.stdout" 2> "$W/run1.stderr"
python3 "$HERE/check.py" "$W/out1" "$W/syn1/truth.json" --exif | tail -1
echo "candidate folders shown on screen only: $(grep -c '^ ' "$W/run1.stderr" || true); exported: $(tail -1 "$W/out1/census_candidate_folders.csv")"

echo "== open() audit with strace (emulated placeholders = sticky-bit files)"
for mode in "" "--exif"; do
  rm -rf "$W/o"; strace -f -e trace=open,openat,openat2 -o "$W/st.log" "$W/census-emu" --root "$R" $mode --out "$W/o" --yes >/dev/null 2>&1
  opened=$(grep 'home-Qx7-user' "$W/st.log" | grep -v O_DIRECTORY | sed 's/^[0-9]* openat([^"]*"\(.*\)".*/\1/' || true)
  n=$(printf '%s\n' "$opened" | grep -c . || true)
  ph=0; if [ "$n" -gt 0 ]; then ph=$(printf '%s\n' "$opened" | while read -r f; do if [ -k "$f" ]; then echo x; fi; done | wc -l); fi
  echo "mode=[${mode:-default}] regular-file opens=$n  of which emulated placeholders=$ph"
done
echo "placeholders in tree: $(find "$R" -type f -perm -1000 | wc -l)"

echo "== consent prompt: answering 'no' saves nothing"
rm -rf "$W/o3"; echo no | "$W/census-emu" --root "$R" --out "$W/o3" >/dev/null 2>&1; [ -e "$W/o3" ] && echo "FAIL: saved" || echo "ok: nothing saved"

echo "== timing, scale 1 on disk (cold = after drop_caches, if permitted)"
for mode in "" "--exif"; do
  for i in 1 2 3; do
    sync; (echo 3 > /proc/sys/vm/drop_caches) 2>/dev/null && c=cold || c=warm?
    rm -rf "$W/o"; "$W/census-emu" --root "$R" $mode --out "$W/o" --yes 2>/dev/null | grep '^Counted' | sed "s/^/$c [${mode:-default}] /"
  done
done

if [ -n "$BIG" ]; then
  echo "== timing, ~500k files on $(findmnt -no FSTYPE -T "$(dirname "$BIG")") (warm; RAM-backed if tmpfs)"
  rm -rf "$BIG"; mkdir -p "$BIG"; python3 "$HERE/gen_home.py" "$BIG" 21 7
  for mode in "" "--exif"; do
    for i in 1 2 3; do rm -rf "$W/o"; "$W/census-emu" --root "$BIG/home-Qx7-user" $mode --out "$W/o" --yes 2>/dev/null | grep '^Counted' | sed "s/^/[${mode:-default}] /"; done
  done
  python3 "$HERE/check.py" "$W/o" "$BIG/truth.json" --exif | grep -E 'FAIL|checks passed'
  grep -E 'sniffed|exif_' "$W/o/census_device.csv"
  rm -rf "$BIG"
fi
