#!/usr/bin/env bash
# Re-create the sparse checkouts that census.py reads. Needs git access to github.com.
# Pins are the commits used on 2026-09-29; drop the `git checkout <sha>` lines to census HEAD instead.
set -euo pipefail
clone() { # name url sha paths...
  local name=$1 url=$2 sha=$3; shift 3
  git clone -q --filter=blob:none --no-checkout "$url" "$name"
  git -C "$name" sparse-checkout init --no-cone
  git -C "$name" sparse-checkout set "$@"
  git -C "$name" checkout -q "$sha"
}
clone immich   https://github.com/immich-app/immich          6cd746ad22a9730699f94f9b8696d6aa52e6fd55 '/mobile/android/**/AndroidManifest.xml' '/mobile/android/fastlane/**'
clone ente     https://github.com/ente-io/ente                7a5993c007398d085e0481df48638b324a12697f '/mobile/apps/photos/android/**/AndroidManifest.xml' '/mobile/apps/photos/README.md'
clone nextcloud https://github.com/nextcloud/android          3c70807a0fc8300b4e452a6a76ed2c29f7da2e52 '/app/src/*/AndroidManifest.xml' '/README.md'
clone proton   https://github.com/ProtonDriveApps/android-drive d1c81cd2eab6c2d0715ad92c86428a4ef50b1825 '**/AndroidManifest.xml'
clone seadroid https://github.com/haiwen/seadroid              9d6d49055297991391758d56f3f211e759e2ee8c '**/AndroidManifest.xml' '/README.md'
echo "now run: python3 census.py apps.json > census.json"
