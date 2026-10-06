#!/bin/sh
# Runs inside swift:6.1-noble. $1 = language mode (5 or 6)
set -e
cd /w
mkdir -p bin
swiftc -swift-version "$1" -O \
  -I gen -Xcc -fmodule-map-file=gen/reliquary_ios_shapeFFI.modulemap \
  -L target/release -lreliquary_ios_shape -Xlinker -rpath -Xlinker /w/target/release \
  gen/reliquary_ios_shape.swift harness/main.swift -o bin/shell-swift$1 2>&1
echo "BUILD_OK swift$1"
