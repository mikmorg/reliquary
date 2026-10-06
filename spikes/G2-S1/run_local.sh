#!/usr/bin/env bash
# G2-S1 emulated leg: how each local target was started on 2026-09-29 (EMULATED, NOT real R2/Cloudflare).
# Throwaway research code. Run the sections you need; each target listens on 127.0.0.1 only.
# Credentials below are local test strings, not real secrets.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="${WORK:-$HERE/.work}"   # large state goes here; delete it afterwards
mkdir -p "$WORK"
AK=g2s1-local-ak
SK=g2s1-local-secret-not-a-real-credential
target="${1:-help}"

case "$target" in
miniflare)   # wrangler 4.143.0 -> miniflare 5.20260926.0-alpha, workerd 1.20260926.1 (pinned in worker/package-lock.json)
  cd "$HERE/worker" && npm ci
  npx wrangler dev --port 8787 --ip 127.0.0.1 --persist-to "$WORK/mf-state" &
  sleep 15
  python3 "$HERE/fidelity.py" --name miniflare --endpoint http://127.0.0.1:8787/cdn-cgi/local/r2/s3 \
    --bucket staging --ak $AK --sk $SK --worker http://127.0.0.1:8787 --out "$HERE/results/miniflare.json"
  ;;
queues-http-pull)   # expected: wrangler refuses the config (see results/evidence/queues-http-pull-config-error.txt)
  cd "$HERE/worker" && npx wrangler dev -c q/wrangler.toml --port 8799 --ip 127.0.0.1 || true
  ;;
seaweedfs)   # built from source: github.com/seaweedfs/seaweedfs @ 5da137233d1a (2026-09-29), `weed version` = 4.48
  # go mod download -json github.com/seaweedfs/seaweedfs@v0.0.0-20260929035139-5da137233d1a ; copy Dir; go build -o weed ./weed
  # (plain `go install .../weed@...` fails: go.mod has replace directives; needs Go >= 1.26.6)
  weed mini -dir="$WORK/sw" -ip=127.0.0.1 -ip.bind=127.0.0.1 -s3.config="$HERE/targets/seaweedfs-s3.json" \
    -master.telemetry=false -admin.ui=false -bucket=staging &
  sleep 15
  python3 "$HERE/fidelity.py" --name seaweedfs --endpoint http://127.0.0.1:8333 --bucket staging \
    --ak $AK --sk $SK --region us-east-1 --out "$HERE/results/seaweedfs.json"
  ;;
versitygw)   # go install github.com/versity/versitygw/cmd/versitygw@v1.8.0
  mkdir -p "$WORK/vgw/data" "$WORK/vgw/iam"
  ROOT_ACCESS_KEY=$AK ROOT_SECRET_KEY=$SK versitygw --port 127.0.0.1:7070 --iam-dir "$WORK/vgw/iam" posix "$WORK/vgw/data" &
  sleep 3
  python3 - <<EOF
import sys; sys.path.insert(0, "$HERE"); import fidelity as f
print(f.S3("http://127.0.0.1:7070", "staging", "$AK", "$SK", "us-east-1").call("PUT", None)[0])  # CreateBucket
EOF
  python3 "$HERE/fidelity.py" --name versitygw --endpoint http://127.0.0.1:7070 --bucket staging \
    --ak $AK --sk $SK --region us-east-1 --out "$HERE/results/versitygw.json"
  ;;
rustfs)      # docker image rustfs/rustfs:1.0.0 (created 2026-09-16)
  mkdir -p "$WORK/rustfs" && chmod 777 "$WORK/rustfs"
  docker run -d --name g2s1-rustfs -p 127.0.0.1:9010:9000 -e RUSTFS_ACCESS_KEY=$AK -e RUSTFS_SECRET_KEY=$SK \
    -v "$WORK/rustfs:/data" rustfs/rustfs:1.0.0
  sleep 12
  python3 - <<EOF
import sys; sys.path.insert(0, "$HERE"); import fidelity as f
print(f.S3("http://127.0.0.1:9010", "staging", "$AK", "$SK", "us-east-1").call("PUT", None)[0])
EOF
  python3 "$HERE/fidelity.py" --name rustfs --endpoint http://127.0.0.1:9010 --bucket staging \
    --ak $AK --sk $SK --region us-east-1 --out "$HERE/results/rustfs.json"
  ;;
garage)      # docker image dxflrs/garage:v2.4.1; config binds IPv4 (the container panicked on [::] binds)
  mkdir -p "$WORK/garage/meta" "$WORK/garage/data"
  docker run -d --name g2s1-garage -p 127.0.0.1:3900:3900 -v "$HERE/targets/garage.toml:/etc/garage.toml" \
    -v "$WORK/garage/meta:/var/lib/garage/meta" -v "$WORK/garage/data:/var/lib/garage/data" dxflrs/garage:v2.4.1
  sleep 8
  G="docker exec g2s1-garage /garage"
  NODE=$($G status | awk '/127.0.0.1/{print $1; exit}')
  $G layout assign -z dc1 -c 1G "$NODE" && $G layout apply --version 1
  $G bucket create staging
  $G key import --yes -n g2s1 GK0123456789abcdef01234567 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
  $G bucket allow --read --write --owner staging --key g2s1
  python3 "$HERE/fidelity.py" --name garage --endpoint http://127.0.0.1:3900 --bucket staging \
    --ak GK0123456789abcdef01234567 --sk 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef \
    --region garage --out "$HERE/results/garage.json"
  ;;
moto)        # pip install "moto[server]==5.2.3" (ran with an earlier revision of fidelity.py: no T34b, T46-T49, T54)
  moto_server -H 127.0.0.1 -p 5055 &
  sleep 4
  python3 - <<EOF
import sys; sys.path.insert(0, "$HERE"); import fidelity as f
print(f.S3("http://127.0.0.1:5055", "staging", "$AK", "$SK", "us-east-1").call("PUT", None)[0])
EOF
  python3 "$HERE/fidelity.py" --name moto --endpoint http://127.0.0.1:5055 --bucket staging \
    --ak $AK --sk $SK --region us-east-1 --out "$HERE/results/moto.json"
  ;;
sdk)         # AWS SDK for JavaScript v3 default-settings check against one target: sdk <name> <endpoint> <region> [ak sk]
  cd "$HERE/sdk" && npm ci
  node sdk_quirks.mjs "$2" "$3" staging "$4" "${5:-$AK}" "${6:-$SK}" > "$HERE/results/sdkjs-$2.jsonl"
  ;;
compare)
  python3 "$HERE/compare.py" "$HERE"/results/{miniflare,rustfs,versitygw,seaweedfs,garage}.json > "$HERE/results/comparison.md"
  ;;
*)
  echo "usage: $0 {miniflare|queues-http-pull|seaweedfs|versitygw|rustfs|garage|moto|sdk|compare}"
  ;;
esac
