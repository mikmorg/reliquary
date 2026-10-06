# A2-S4: forgery and truncation (CT, run 2026-10-06)

> Throwaway spike evidence. Code: `spikes/A2-S2/` (`harness/a2s4_forgery.py`, `src/main.rs` `cmd_ingest`). Synthetic data only (`SYN → results`).

- **Hypothesis (PLAN A2-S4):** an attacker who holds only the homelab public key can make valid age objects, because age is sender-anonymous. A forged object plus record, and a dropped final chunk, must both be rejected **before any catalog write**, each with a specific error code. "Record" stands in for "manifest" here; the manifest format belongs to A4.
- **Decision informed:** the F4 binding set in ADR-0007, the device-signed record (OD-04), and the error-code table for `object-format.md`.
  - Pass: keep the F4 binding set.
  - Fail: add an outer binding.
- **Budget IDs:** none.
- **Exec tag:** CT.
- **Status:** ran.
- **Result:** **PASS**, 30/30 checks. Every attack is rejected with exit 10 and its own `REJECT` code, and a hash of every file in the homelab store (catalog, objects, by-dedup, devices, receipts) is unchanged afterwards. The honest uploads ingest before and after the attacks.

## Setup

- **Homelab:** one `mlkem768x25519` identity from Go `age-keygen -pq` (v1.3.2), and an Ed25519 receipt key.
- **Registry:** two devices, `dev-a` and `dev-b`, each with an Ed25519 key.
- **Trust bundle:** v2, profile `pq`, one recipient.
- **Ingest policy:** strict. Exactly 1 × `mlkem768x25519` stanza in the record and in the object, with the low-order check on.
- **TEST-ONLY flag:** `--skip-binding-precheck` disables the record/object length and MAC pre-checks. It shows that the layer below (STREAM, header MAC, SHA-256) still rejects each attack on its own.

**Stock age accepts the forgery.** Go `age -d` decrypts the attacker's forged object (`evil.age`) with the homelab identity and exit code 0 (2026-10-06). This is the premise of the spike: the ciphertext alone authenticates nothing.

## Results

| Attack | Attacker | Rejection | Exit | Store unchanged |
|---|---|---|---|---|
| A1 forged object + record signed by the attacker's key under its own name | public-key holder | `E_SIG_UNKNOWN_KEY` | 10 | yes |
| A2 forged record claims a registered device name, attacker's key | public-key holder | `E_SIG_KEY_HASH` | 10 | yes |
| A3 forged record with the victim's key hash, attacker's signature | public-key holder | `E_SIG_INVALID` | 10 | yes |
| A4 unsigned record (valid age file, no signature line) | public-key holder | `E_RECORD_FORMAT` | 10 | yes |
| A5 forged dedup-hit record (`object: null`), attacker's key | public-key holder | `E_SIG_KEY_HASH` | 10 | yes |
| B1 staged object replaced by the attacker's valid age object (same size) | public-key holder | `E_BINDING_HEADER_MAC` | 10 | yes |
| B2 same, pre-check disabled: the content check must still reject | public-key holder | `E_CONTENT_MISMATCH` | 10 | yes |
| B3 another honest object presented under the victim's record | public-key holder | `E_BINDING_HEADER_MAC` | 10 | yes |
| B4 attacker's object carrying a copy of the victim's MAC line | public-key holder | `E_OBJECT_HMAC` | 10 | yes |
| C1 dropped final chunk (record intact) | public-key holder | `E_BINDING_LENGTH` | 10 | yes |
| C2 dropped final chunk, pre-check disabled | public-key holder | `E_STREAM_TRUNCATED` | 10 | yes |
| C3 one byte cut from the end | public-key holder | `E_BINDING_LENGTH` | 10 | yes |
| C4 one byte cut, pre-check disabled | public-key holder | `E_STREAM_AUTH` | 10 | yes |
| C5 full-chunk object, final chunk dropped at a chunk boundary | public-key holder | `E_BINDING_LENGTH` | 10 | yes |
| C6 same, pre-check disabled (STREAM final-flag check) | public-key holder | `E_STREAM_TRUNCATED` | 10 | yes |
| C7 trailing data appended after the final chunk | public-key holder | `E_BINDING_LENGTH` | 10 | yes |
| C8 trailing data, pre-check disabled | public-key holder | `E_STREAM_AUTH` | 10 | yes |
| C9 two chunks swapped (reordering) | public-key holder | `E_STREAM_AUTH` | 10 | yes |
| D1 object with PQ + X25519 stanzas (downgrade) | public-key holder | `E_PROFILE` | 10 | yes |
| D2 object with an extra unknown stanza (valid age, not in the profile) | public-key holder | `E_PROFILE` | 10 | yes |
| D3 honest record re-encrypted with an extra X25519 stanza | public-key holder | `E_PROFILE` | 10 | yes |
| D4 victim's object with the stanza's X25519 share set to a low-order point | public-key holder | `E_OBJECT_HEADER` | 10 | yes |
| E1 record signed with `dev-a`'s key but `device_id` says `dev-b` | registered device | `E_DEVICE_MISMATCH` | 10 | yes |
| E2 new record reusing a committed `device_seq` | registered device | `E_REPLAY_SEQ` | 10 | yes |
| E3 committed `record_id` reused with different content | registered device | `E_REPLAY_RECORD_ID` | 10 | yes |
| E4 oversized record (> 1 MiB) | public-key holder | `E_RECORD_TOO_LARGE` | 10 | yes |
| F1 replay of a committed honest record | anyone with cloud access | idempotent: same receipt re-issued, no new catalog row | 0 | yes |

Evidence: `evidence/forgery.log` and `evidence/results.json`.

## Observations for the analyst

1. **The `header_mac` string in the record binds nothing on its own.** An attacker can copy the MAC line onto its own object (B4) or alter a stanza and keep the MAC line (D4); the record's `header_mac` then still matches. The binding comes from the homelab **verifying** that MAC under the file key it unwraps (B4 → `E_OBJECT_HMAC`), plus the SHA-256 and dedup-ID match on the plaintext (B2). The `header_mac` comparison is a cheap pre-filter. `object-format.md` should say that it is not a security check.
2. **The length binding catches every truncation and append before any decryption** (C1, C3, C5, C7). Even without it, STREAM rejects each one (C2, C4, C6, C8), so the two layers are independent.
3. **The stanza profile check is the only control against downgrade and mixing** (D1–D3). The A2-S3 matrix found that typage 0.3.1 *writes* a mixed PQ + X25519 header when asked, without error. So the profile must be enforced at ingest, not assumed from the encoder.
4. **A Rust decoder needs its own low-order check** (D4, and CCTV `hybrid_low_order` / `hybrid_identity` in A2-S3). `hpke` 0.14.1 accepts a low-order share.
5. **HPKE Auth mode with X-Wing:** `hpke-auth-probe` shows that `hpke` 0.14.1 **panics** ("X-Wing doesn't support authenticated encapsulation. Use Base or Psk operation mode.") rather than returning an error (`evidence/hpke_auth_probe.json`). This refines A2 note claim C11, which says it "errors".
6. **Not covered here:**
   - A registered device claiming someone else's committed `dedup_id` with the correct `sha256` and `size` is *accepted* as a sighting. That is the dedup-poisoning question, owned by A3 and D4.
   - Replay protection is a per-device seen-set of `record_id` and `device_seq`, which allows out-of-order arrival over R2 and USB. Gap detection is for A3 and A4.
