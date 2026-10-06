# A2-S3: interop of the PQ envelope (CT, run 2026-10-06)

> Throwaway spike evidence. Code: `spikes/A2-S2/` (`harness/a2s3_interop.py`, `harness/a2s3_vectors.py`, `src/header.rs`). Helpers are in `tools/`. Synthetic data only (`SYN → results`). The identities in `vectors/` are **test keys**, derived from public labels, as in CCTV.

- **Hypothesis (PLAN A2-S3, as refined by the A2 note):**
  - Rust output, carrying the `mlkem768x25519` stanza written with the `hpke` 0.14.1 crate, decrypts with Go age ≥ 1.3.0, and the reverse.
  - kage and typage parse the headers.
  - 100 % of the CCTV and project vectors pass.
  - The analyst predicted (note C22) that `hybrid_low_order` fails on a plain `hpke` 0.14.1 decoder.
- **Decision informed:** ADR-0007 / OD-06.
  - Pass: the client encoder writes the X-Wing stanza with Rust `hpke`.
  - Fail: the F2 fallback (X25519 on the device, PQ rewrap at the homelab).
- **Budget IDs:** none.
- **Exec tag:** CT.
- **Status:** ran.
- **Result:** **PASS.**

## Implementations under test

| Implementation | Version | Source | PQ (`mlkem768x25519`) |
|---|---|---|---|
| Rust (this spike's own encoder and decoder) | `hpke` 0.14.1 (X-Wing on `x-wing` 0.1.0), `shake` 0.1.0 | static.crates.io | yes (own stanza code) |
| Go age (reference) | `filippo.io/age` v1.3.2 (proxy.golang.org, tagged 2026-08-29), built with `GOTOOLCHAIN=auto` (go1.27.0) | proxy.golang.org | native |
| typage | npm `age-encryption` 0.3.1 (published 2026-08-28) | registry.npmjs.org | native |
| kage | `com.github.android-password-store:kage` 0.8.0 (Maven metadata lastUpdated 2026-09-29) | repo.maven.apache.org (repo1.maven.org returned HTTP 429) | native (`MlKem768X25519Identity`/`Recipient` in the 0.8.0 sources) |

## Results

### 1. Cross-implementation matrix (`evidence/interop-results.json`, `evidence/interop.log`)

The matrix crosses:

- 4 encoders × 4 decoders;
- 3 key origins: Go `age-keygen -pq`, Rust `keygen`, typage `generateHybridIdentity`;
- 7 plaintext sizes: 0, 1, 65,535, 65,536, 65,537, 196,615 and 5,242,883 B;
- 1 or 2 PQ stanzas, decrypting with the identity of the **last** stanza.

| | → Rust | → Go age | → typage | → kage |
|---|---|---|---|---|
| **Rust →** | 42/42 | 42/42 | 42/42 | 42/42 |
| **Go age →** | 42/42 | 42/42 | 42/42 | 42/42 |
| **typage →** | 42/42 | 42/42 | 42/42 | 42/42 |
| **kage →** | 42/42 | 42/42 | 42/42 | 42/42 |

In total there are 853 checks with 0 failures. The checks include:

- header lengths: every encoder writes 1,627 B for one stanza and 3,184 B for two;
- recipient strings: 1,959 characters from all three key generators;
- derived recipients: Rust and Go derive the same recipient from each identity.

### 2. Refusing to mix PQ and classic recipients

| Encoder | Asked to encrypt to PQ + X25519 |
|---|---|
| Go age 1.3.2 | refuses: "incompatible recipients: can't mix post-quantum and classic recipients…" |
| Rust spike | refuses: `E_MIXED_RECIPIENTS` |
| kage 0.8.0 | refuses, with a misleading message: `InvalidScryptRecipientException: incompatible scrypt recipients` |
| **typage 0.3.1** | **writes the file** (exit 0). `age-inspect` reports `mlkem768x25519` + `X25519` and "This file does NOT use post-quantum encryption." |

### 3. CCTV vectors (`evidence/cctv/`)

The vectors are `c2sp.org/CCTV/age@v0.0.0-20260925130909-50a8ecf2a220`: 147 files, byte-identical to the 20260829 set that Go age 1.3.2 pins. 62 vectors are armored or passphrase-only. The Reliquary profile excludes armor and scrypt, so these are "n/a" for the three non-Go decoders.

| Decoder | Applicable | Pass | Fail |
|---|---|---|---|
| Go age 1.3.2 own testkit (`go test -run TestVectors`) | 147 | 147 | 0 |
| Rust spike decoder, **strict** (own low-order check) | 85 | **85** | 0 |
| Rust spike decoder, **lax** (`hpke` 0.14.1 decapsulation only) | 85 | 83 | **2: `hybrid_identity`, `hybrid_low_order`** (expected "header failure"; got "success") |
| typage 0.3.1 | 85 | 85 | 0 |
| kage 0.8.0 | 85 | 85 | 0 |

The Rust runner checks the outcome class (success, header failure, no match, HMAC failure or payload failure) and the partial-payload hash. The typage and kage runners check only "succeeded with the right hash" against "threw".

### 4. Project vectors (`vectors/`, `evidence/vectors_results.json`)

There are 15 vectors in CCTV file format, made by the seeded Rust encoder (`--seed`/`--context`, test-only).

- **Valid files:** 1 and 2 PQ stanzas, sizes 0 B to 3 chunks + 5 B, and an X25519 legacy file.
- **Profile violations that are still valid age:** mixed PQ + X25519, and a grease stanza.
- **Invalid files:** final chunk dropped, trailing data, low-order share, no match, bad MAC, truncated header.

Results:

- **Determinism:** two independent generations were byte-identical. This gives encrypt-direction vectors, which CCTV cannot provide.
- **Decoders:** Go age 15/15, Rust strict 15/15, typage 15/15, kage 15/15.

## Observations for the analyst

1. **C8 interop is now verified, not inferred.** The Rust `hpke` 0.14.1 X-Wing stanza interoperates byte-for-byte with Go age 1.3.2, typage 0.3.1 and kage 0.8.0, in both directions and with keys from three generators.
2. **C22 is confirmed.** A decoder built on plain `hpke` 0.14.1 accepts both CCTV low-order vectors. Adding the X25519 check on the X-Wing ciphertext share (`src/header.rs`, `unwrap_one`) fixes this.
3. **kage 0.8.0 has native PQ** and passes CCTV, so the "kage PQ support" open question in the A2 note (open question 7) is answered for the JVM/Android path. Note that kage rejects low-order points through BouncyCastle's `X25519.calculateAgreement`.
4. **The no-mixing rule is not enforced by every implementation** (typage). Reliquary must enforce its stanza profile at ingest (A2-S4 D1–D3) and in its own encoder.
5. **Partial-output semantics.** The first version of the spike decoder released no plaintext from a full chunk that authenticated as non-final before reporting truncation. CCTV's partial-payload hashes caught this. The age rule is "release only authenticated plaintext", and that plaintext includes such chunks.
6. **Not tested:**
   - an iOS (Swift/CryptoKit) decoder;
   - rage, the Rust `age` CLI, which has no PQ recipient in 0.12.1;
   - `age-plugin-pq`.
