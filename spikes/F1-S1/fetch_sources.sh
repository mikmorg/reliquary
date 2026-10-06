#!/usr/bin/env bash
# Fetch the candidate sources at the commits measured on 2026-09-29 (F1-S1).
# Usage: ./fetch_sources.sh <dir>   -> <dir>/src (blobless checkouts) and <dir>/tags (treeless bare clones)
set -eu
D=${1:?target dir}; mkdir -p "$D/src" "$D/tags"
PIN=(
 "ente/ente 7a5993c007398d085e0481df48638b324a12697f ente mobile server rust web android apple architecture cli"
 "immich-app/immich 6cd746ad22a9730699f94f9b8696d6aa52e6fd55 immich mobile server web machine-learning open-api"
 "restic/restic 5127c4abf921857fde4ae51f566c86028c8c2911 restic_restic"
 "kopia/kopia 87d15ded620524ff964277251cd82dac641f4d13 kopia_kopia"
 "PlakarKorp/plakar ade5fd027601110909d7da4b79f4543587def7c4 PlakarKorp_plakar"
 "PlakarKorp/kloset 5e81a8d kloset"
 "syncthing/syncthing b223f729c63561a6e9e08e3f66c3284e207eb443 syncthing_syncthing"
 "rustic-rs/rustic_core 647d00f6adde3c77836dccd9bbac61a7817e0591 rustic-rs_rustic_core"
 "rustic-rs/rustic 143d073f6039fcf29b64191ceb36c926744b6fe4 rustic-rs_rustic"
 "borgbackup/borg 153d10a8621b84d192811e4cb7391af4cde71d09 borgbackup_borg"
 "uroni/urbackup_backend a4eb72a94350364227196bda164b4f10d039fc1a uroni_urbackup_backend"
 "researchxxl/syncthing-android 02a95858e5192139353cd1188e9f5679eef0dd97 researchxxl_syncthing-android"
 "duplicati/duplicati 25734de3377f59b42e752b7cc8aa2d40bf990e92 duplicati_duplicati"
 "nextcloud/android 3c70807a0fc8300b4e452a6a76ed2c29f7da2e52 nextcloud_android"
)
for line in "${PIN[@]}"; do
  set -- $line; repo=$1 sha=$2 dir=$3; shift 3
  git clone -q --filter=blob:none --no-checkout "https://github.com/$repo.git" "$D/src/$dir"
  if [ $# -gt 0 ]; then git -C "$D/src/$dir" sparse-checkout set "$@"; fi
  git -C "$D/src/$dir" checkout -q "$sha"
done
for repo in ente/ente immich-app/immich restic/restic restic/rest-server kopia/kopia PlakarKorp/plakar syncthing/syncthing \
            rustic-rs/rustic_core borgbackup/borg uroni/urbackup_backend researchxxl/syncthing-android duplicati/duplicati nextcloud/android; do
  git clone -q --bare --filter=tree:0 "https://github.com/$repo.git" "$D/tags/$(echo $repo | tr / _).git"
done
