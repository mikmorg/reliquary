# Spike B7-S1-dr: what designated requirement a self-signed macOS signature carries (emulated, Linux)

- **Parent spike:** B7-S1 (kit `docs/research/kits/B7-S1/`). This is a container-side preparation step, tag CT, **emulated**: it runs `rcodesign` on Linux. It shows what is **written into** the signature. It does **not** show how macOS (TCC, Keychain) evaluates it; only the kit can.
- **Run by / date:** B7 spike runner (agent), 2026-09-29, research container (Linux x86_64, OpenSSL 3.0.13).
- **Tool:** `apple-codesign` (rcodesign) **0.29.0**, built from crates.io with `cargo install apple-codesign --version 0.29.0 --no-default-features --locked` (MPL-2.0).
- **Inputs:** the arm64 Mach-O `esbuild` executables from npm `@esbuild/darwin-arm64` 0.25.0 and 0.25.1, used only as stand-in bytes for "v1" and "v2". Each is wrapped in a `ReliquaryProbe.app` with bundle id `org.reliquary.b7s1probe`. The tgz SHA-256 values are at the end of `run-output.txt`. Throwaway self-signed RSA-2048 certificates (code-signing EKU) made with the same OpenSSL recipe as the kit's `make-cert.sh`, once with `O=` and once without.
- **Data class:** `PUB+SYN → results`. The test keys were generated in a scratch directory and deleted with it.
- **Budget IDs:** none (this is an input to B7-S1, whose criterion cites BUD-SUPPORT).

## Hypothesis

1. An ad-hoc signature carries no explicit DR, and its cdhash changes between two different builds. It stays the same when the same bytes are re-signed.
2. rcodesign 0.29.0 derives a DR for a self-signed certificate on its own: `identifier "<id>" and certificate root = H"<SHA-1 of the certificate>"`. That DR is identical for v1 and v2 signed with the same certificate, and the hash equals the certificate's SHA-1 fingerprint. (A scout reported that rcodesign derives DRs only for Apple-issued certificates; the 0.29.0 source, `src/policy.rs` `non_apple_signed_expression`, suggests otherwise.)

## How to run

`RCS=/path/to/rcodesign ./run.sh` (needs `curl`, `openssl`, network access to registry.npmjs.org). It writes to `./work/`.

## Result (measured; full output in `run-output.txt`)

| Case | v1 cdhash | v2 cdhash | DR embedded in the signature |
|---|---|---|---|
| Ad hoc (`--code-signature-flags runtime`) | `bf1be157…` | `855cb1c6…` | none (empty requirement set; macOS computes the implicit cdhash DR at run time) |
| Ad hoc, same bytes re-signed | `bf1be157…` (same) | `855cb1c6…` (same) | none |
| Self-signed, certificate with `O=` | `914ac865…` | `973a7096…` | `identifier "org.reliquary.b7s1probe" and certificate root = H"409d403c…"`, **identical in v1 and v2**, equal to the certificate's SHA-1 |
| Self-signed, certificate without `O=` | `190ccc36…` | `cce9a1d6…` | `… and certificate root = H"13655742…"`, identical in v1 and v2 |
| PKCS#12 made with OpenSSL 3 `-legacy` | — | signed | same DR as the `O=` row |
| PKCS#12 made with OpenSSL 3 defaults | — | **failed**: "incorrect password given when decrypting PFX data" (the password was correct) | — |

**Hypotheses 1 and 2 hold, as far as a Linux emulation can show.**

## Findings for the B7-S1 kit and the research note

- rcodesign 0.29.0 **does** derive a self-signed DR automatically. A Linux CI does not need to hand-compile a requirement for the "stable self-signed" arm. This corrects the source-scout claim quoted in the research note (§2 "Signing from Linux CI", S25).
- The DR form matches the one the research note derives from Apple's `DRMaker` for a certificate with an Organization field (C4). **Difference from source reading (not observed on a Mac):** Apple's `DRMaker::nonAppleAnchor` pins `certificate leaf` when the leaf has no Organization, whereas rcodesign pins `certificate root` in both cases. For a one-certificate chain both refer to the same certificate. The kit's certificate has `O=`, and arm B' checks that a v1 signed by Apple `codesign` and a v2 signed by rcodesign are treated as the same app.
- rcodesign timestamps by default through `http://timestamp.apple.com/ts01` (`src/cli/mod.rs`, `APPLE_TIMESTAMP_URL`). Offline, or with that host blocked (as here), signing fails with "Time-Stamp Protocol error: bad HTTP response" unless `--timestamp-url none` is given. The kit's `sign.sh` passes it.
- rcodesign 0.29.0 cannot read a PKCS#12 file written with OpenSSL 3's default encryption, and gives a misleading "incorrect password" error. Use `-legacy` with OpenSSL 3 (macOS's `/usr/bin/openssl` is LibreSSL and was not tested here). Noted in the kit.
- Incidental, from the kit's `update.sh` dry run on Linux (not on macOS): the directory created by `mktemp -d` is mode 0700, and because the updater renames that temp directory into place, the updated `.app` folder inherits it. `tauri-plugin-updater` 2.13.0 does the same with `tempfile::Builder::tempdir()` (source reading; not run on a Mac). If confirmed on a Mac, other user accounts could not open an app in `/Applications` after an update. Input for B7-S3 (Wave 2).

## Limits

- Emulated: no macOS. Whether TCC and the Keychain honour this DR across updates is exactly what the kit tests.
- `rcodesign verify` is flagged by its authors as unreliable ("known to be buggy") and reported a CMS error even for the ad-hoc signatures, so verification was not used as evidence.
- The stand-in binaries are not the probe app; only the signature structure is under test.
