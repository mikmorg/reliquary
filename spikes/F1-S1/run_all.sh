#!/usr/bin/env bash
# Re-run every F1-S1 measurement. Needs: git, python3, tokei (cargo install tokei), Go >= 1.24
# (plakar v1.1.7 asks for the go1.26 toolchain, which `go install` fetches), curl. About 3 GB of disk.
set -eu
H=$(cd "$(dirname "$0")" && pwd); D=${WORK:-$H/work}; mkdir -p "$D/bin" "$H/evidence"
[ -d "$D/src" ] || "$H/fetch_sources.sh" "$D"
GOBIN=$D/bin go install github.com/restic/restic/cmd/restic@v0.19.1
GOBIN=$D/bin go install github.com/restic/rest-server/cmd/rest-server@v0.14.0
GOBIN=$D/bin go install github.com/kopia/kopia@v0.23.1
GOBIN=$D/bin go install github.com/PlakarKorp/plakar@v1.1.7
python3 "$H/scripts/loc.py" "$D/src" > "$H/evidence/loc.csv"
python3 "$H/scripts/cadence.py" "$D/tags" > "$H/evidence/cadence.csv"
for p in restic kopia plakar; do BIN=$D/bin TMPDIR=$D "$H/scripts/probe_$p.sh" > "$H/evidence/probe_$p.txt" 2>&1 || true; done
