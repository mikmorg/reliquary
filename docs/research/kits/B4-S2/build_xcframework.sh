#!/bin/sh
# Kit B4-S2: build the B4-S1 Rust core as an XCFramework + Swift bindings. Run on the Mac, from
# the repo root. Needs Xcode (command-line tools) and rustup. Not run in the research container
# (no Xcode there); the container only proved that the staticlibs compile for both targets and that
# bindings generated from the iOS .a are identical to the ones that compiled and ran with Swift 6.1 on Linux.
set -e
cd spikes/B4-S1/core
rustup target add aarch64-apple-ios aarch64-apple-ios-sim
export CARGO_TARGET_DIR="$PWD/../target"
# iOS links the system libsqlite3: build without the bundled-sqlite feature, add libsqlite3.tbd in Xcode.
for t in aarch64-apple-ios aarch64-apple-ios-sim; do
  cargo rustc --release --lib --target "$t" --no-default-features --crate-type staticlib
done
cargo run --release --features=uniffi/cli --bin uniffi-bindgen -- generate \
  --library ../target/aarch64-apple-ios/release/libreliquary_ios_shape.a --language swift --out-dir ../gen-ios
mkdir -p ../gen-ios/headers
cp ../gen-ios/reliquary_ios_shapeFFI.h ../gen-ios/headers/
cp ../gen-ios/reliquary_ios_shapeFFI.modulemap ../gen-ios/headers/module.modulemap
rm -rf ../ReliquaryCore.xcframework
xcodebuild -create-xcframework \
  -library ../target/aarch64-apple-ios/release/libreliquary_ios_shape.a -headers ../gen-ios/headers \
  -library ../target/aarch64-apple-ios-sim/release/libreliquary_ios_shape.a -headers ../gen-ios/headers \
  -output ../ReliquaryCore.xcframework
echo "Add ReliquaryCore.xcframework + gen-ios/reliquary_ios_shape.swift to the app target (and to the"
echo "extension target if you run step A8). Link libsqlite3.tbd. Record the Xcode and SDK versions."
