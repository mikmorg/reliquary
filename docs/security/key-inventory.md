# Key inventory

- **Status:** Draft (Wave 1, D2). This is not normative until ADR-0008 is Accepted.
- **Owner:** D2 (PLAN §2.1). Other workstreams supply requirements for the rows they own. They do not edit custody rules for Tier-0 keys.
- **Date:** 2026-10-06
- **Evidence:** `docs/research/d2-key-hierarchy-custody-recovery.md` (§F1, §F2, §F4, §F5); ADR-0008 (Proposed)
- **Conditional on:**
  - OD-06 (PQ or classic);
  - OD-07 (at-rest posture; this draft assumes A′);
  - OD-08 / DR-D2-3 / DR-D2-4 (recovery holders and bundle scope);
  - DR-A1-1 (dedup construction).

## Tiers

| Tier | Meaning | Rule |
|---|---|---|
| 0 | Offline roots | In the clear only on the air-gapped ceremony image, during a recovery, or (for X) during an admin restore. Never in an online bundle. |
| 1 | Homelab online | May sit in RAM on the ingest VM. Never on snapshotted, replicated or vzdump-covered storage unless sealed. |
| 2 | Device | Platform keystore, or keystore-wrapped. No backup: re-enroll instead. |
| P | Project / cloud | Custody owned by another workstream. Listed here so that compromise responses are coordinated. |

## Inventory

| ID | Key | Algorithm (if OD-06 = PQ) | Tier | Created where | Custody | Backup | Rotation | Compromise response | Owner |
|---|---|---|---|---|---|---|---|---|---|
| K-01 | Recovery identity R | `mlkem768x25519` age identity | 0 | Ceremony | Armored scrypt-wrapped identity file (422 B) under a 128-bit W. W exists only as SLIP-39 shares | Wrapped file as a QR on every card and on the doomsday USB. W in k-of-n cards | Only on suspected exposure of ≥ k cards or of R, or after any recovery outside an owner-run air-gapped check | New R, then an A-signed bundle, then a store-wide header rewrap. Copies already made (snapshots, replicas, h0, sidecars, staged or USB) stay exposed | D2 |
| K-02 | Admin root signing key A | Ed25519 | 0 | Ceremony | Passphrase-protected file on two offline media held by the owner | Second medium. In the offline bundle only if DR-D2-3 = full admin | Rare. The new A is signed by the old A | Re-pin through kits (D3); devices refuse bundles not chained to a pinned A | D2 |
| K-02b | Update-signing key(s) | Per D5 | **0** | D5 | D5 | D5 | D5 | **As powerful as A for future uploads.** A signed update can change pins or recipients, and in-app rules cannot prevent that. Joint response with D5/B7 | D5 (ranked by D2) |
| K-03 | Ingest identity I_e | `mlkem768x25519` (the encoder route is A2's choice) | 1 | Homelab | RAM only; loaded through Tang into tmpfs, with a manual fallback | **Sealed to {X, R} into the online bundle when created**; the bundle is copied off-box at epoch start | New epoch through an A-signed bundle. Default: yearly and after suspected compromise (owner-tunable; no primary source) | Rotate; list I_e in the bundle's `revoked[]`; treat staged objects of that epoch as disclosed (AR-08); quarantine later objects under it | D2 / A6 |
| K-03s | Standby ingest identity I_{e+1} (optional, Wave 2) | as K-03 | 1 | Homelab | As K-03 | As K-03 | Pre-signed by A at the ceremony | Helps only if I_e leaked without the homelab being exposed | D2 |
| K-03b | Archive identity X | `mlkem768x25519` | 0/1 | Ceremony or admin machine | Passphrase-wrapped file; optionally wrapped at rest by a YubiKey (classic at-rest wrap) or a Secure Enclave `--pq` key | Sealed to R in the offline bundle, plus a second offline copy | Rare; store rewrap with X online | Rotate and rewrap | D2 / A6 |
| K-04 | Receipt signing key | Ed25519 | 1 | Homelab | Ingest VM (a separate signer is a Wave 2 option, AR-08) | None | Certified by A in the trust bundle | Rotate; list in `revoked[]` | D2 / A3 |
| K-05 | Dedup epoch secret S_e | 32 random bytes; K_e = HKDF(S_e, "reliquary/v1/dedup-id-key") | 1 (homelab), 2 (device copy) | Homelab | Homelab keeps all epochs; devices keep the current one in keystore-wrapped storage | Online bundle | DR-D2-1: every revocation for loss, theft, compromise or estrangement (conditional on DR-A1-1 = B) | Rotate; the historical-ID oracle remains (AR-06) | D2 (trigger), A1 (mechanics) |
| K-06 | Store volume key | A6 | 1 | Homelab | A6 | Online bundle | A6 | A6 | A6 |
| K-07 | Catalog key | A6 | 1 | Homelab | A6 | Online bundle | A6 | A6 | A6 |
| K-08 | Homelab Cloudflare pull tokens | Cloudflare | 1 | Cloudflare | Ingest VM | Owner's password manager | Replace | Revoke | C1 |
| K-09 | Device signing key | Ed25519 or P-256 per D3 | 2 | Device | Platform keystore | None | Re-enroll | Revoke (SR-17) | D3 |
| K-10 | Device sealing / restore key | PQ recommended (Android feasibility open) | 2 | Device | Keystore-wrapped | None | Re-enroll | Revoke | D3 / A8 |
| K-11 | Play upload key | Per B3 | P | — | B3 | B3 | B3 | B3 | B3 |
| K-12 | Worker secrets, invite pepper | — | P | Cloudflare | Never trust-forging (SR-23) | — | — | Rotate; may cost availability only | C1 / D3 |
| K-13 | DKIM keys | — | P | Provider | C3 | — | — | C3 | C3 |
| — | Account recovery codes (Cloudflare, registrar, Play) | — | P | — | **E7 credential inventory**; not in R-reachable bundles by default (DR-D2-3) | E7 | — | E7 | E7 |

## Bundles

| Bundle | Contents | Encrypted to | Sealed where | Refreshed | Copies |
|---|---|---|---|---|---|
| Offline bundle | X, plus A only if DR-D2-3 = full admin | R | **Only** on the air-gapped ceremony image | Only at a ceremony | Doomsday USB; second offline medium |
| Online bundle | Every S_e, every I_e (escrowed at creation), K-06, K-07 | {R, X} | Homelab | On any change; copied off-box at epoch start, at each S_e rotation, and at the annual holder check (proposal) | Homelab; doomsday USB (E7/C8 set the cadence) |

**Rule:** the online bundle never contains Tier-0 material. Re-sealing a bundle requires its plaintext, so a bundle that holds A or X can only be re-sealed offline.

## Trust bundle (signed by A)

Contents:

- recipient I_e;
- recipient R;
- recipient X (if pinned);
- K-04 public key;
- `epoch` (monotonic);
- `not_after`;
- `revoked[]`;
- algorithm IDs.

Device rules:

- refuse any bundle whose epoch is lower than the stored one;
- fetch and verify a current bundle before the first upload;
- name the epoch in each signed manifest.

The encoding and the fingerprint format belong to D3.

## Audit

Each real-key check (see `key-ceremony-runbook.md`) unwraps with R:

- a random sample of stored headers;
- every I_e escrow entry;
- the online bundle;
- the offline bundle.

The pass rate is recorded in the ceremony log.
