# D2. Key hierarchy, custody, recovery and succession cryptography

- **Workstream:** D2 (see `docs/research/PLAN.md`, section "D2.")
- **Status:** Draft (analyst deep read, Wave 1 batch W1-a). Skeptic review has not started, so every claim below is still **pending**.
- **Date:** 2026-09-29 (last updated 2026-09-29)
- **Feeds:** ADR-0008 (key hierarchy, custody, recovery; reserved for D2), OD-08 (recovery recipient, k-of-n, holders), OD-06 (PQ, owned by A2: this note adds the recovery coupling), OD-07 (A6 at-rest posture: custody coupling), OD-17 (new accepted-risk candidates AR-D2-1/2), one-way door #3 (recovery recipient in the key hierarchy)
- **Depends on:** D1 (SR-02, SR-14, SR-15, SR-23, AR-08), A1 (dedup-ID construction and epochs, DR-A1-1), A2 (envelope, OD-06), A6 (at-rest posture, OD-07; the A6 draft `a6-homelab-storage-engine.md` appeared during this stage and recommends posture **A′**: keep the received age payload and rewrap the header at ingest to an offline archive recipient plus R), E7 (break-glass requirement; no E7 note exists yet, so the requirement is taken from PLAN §E7), T1 spike 2 (`content-encryption-format.md`, D-2/D-3/D-4), F3 (C4–C6 PQ findings)
- **Traceability rows advanced:** OPEN-3b (homelab keypair custody), Q1-2a (generating and storing the homelab keypair), OPEN-3c / Q1-2b (custody and rotation trigger of the dedup secret; A1 keeps the ID-side mechanics), R-20, R-22 (input)

## Summary

Every object a device writes should be encrypted to **two recipients from day one**:

- an online **ingest key** held by the homelab;
- an offline **recovery key** that nobody holds in one piece.

age supports this natively. In the container, stock Go `age` 1.3.2 encrypted to and decrypted from two hybrid post-quantum (`age1pq`) recipients. It **refused** to mix a post-quantum recipient with a classic one. This is the most important coupling: if the owner chooses post-quantum (OD-06), the recovery key must also be post-quantum. That rules out YubiKeys, TPMs and passphrase stanzas as recovery *recipients*.

The recommended recovery design uses only stock tools:

1. The recovery identity is a post-quantum age identity. It is stored only as a small passphrase-encrypted age file (260 bytes).
2. That file's 128-bit random passphrase is split with **SLIP-39** into k-of-n word shares (20 words each). The default is 2-of-3, pending E7-S1.
3. Every share card also carries the encrypted identity as a QR code, so any k cards are enough to recover.

The analyst ran this whole chain once in the container, using python-shamir-mnemonic and Go age: 2 of 3 shares, then the passphrase, then the identity, then a decrypted object. The real test is still the family drill (D2-S3).

Under A6's draft posture A′, the homelab rewraps every stored header to an offline **archive key X**, held by the admin, plus R. Devices should still include R themselves. That keeps USB bundles and staged objects readable after an ingest key has been rotated and destroyed.

The online ingest key should be a plain software key. Under A′ it protects only data in transit, so unattended unlock is acceptable. Under postures that store plaintext, it should be unlocked in the same way and at the same time as the store volume. Hardware keys add ceremony without addressing the real risk, a live compromise of the ingest VM (AR-08). Software unwrap runs at thousands of objects per second in the container.

The dedup secret should be random per epoch (A1). It should be sealed by the homelab to each authenticated device key, and rotated on every loss, theft or compromise revocation.

Confidence:

- **High:** the format facts.
- **Medium:** the recovery design and the custody recommendation. Both depend on OD-06, OD-07 and on real people (E7-S1, D2-S3).

## Questions

| # | Question (PLAN D2, Wave 1 scope) | Short answer | Confidence |
|---|---|---|---|
| 1 | Key inventory: custody, backup, rotation and compromise response for each key | Draft inventory in §F1: 15 items across four tiers (offline, homelab online, device, cloud/project). D2 fixes custody for the homelab and recovery keys and only lists D3/D5/C3 keys. | Medium |
| 2 | Online ingest key plus an offline recovery recipient from day one? | **Yes.** Two stanzas on every content object and metadata record. Measured cost with two PQ recipients: a 3,184 B header, against 1,627 B for one PQ recipient. age identities ignore stanzas that are not theirs, so the extra stanza does not affect ingest. | High (format); Medium (value, which depends on OD-07) |
| 3 | Rotation by rewrap only; what the at-rest posture implies | Rotating any key never touches payloads: the payload key is derived from the file key, so only the header changes. The ingest key needs **no** rewrap under any posture: rotate it with a signed bundle. Under A′ the stored headers never carry I. Destroy the old I after the longest drain path. Replacing the recovery key needs a header rewrap of every stored ciphertext, and Reliquary must write that tool, because upstream age has none. No rewrap revokes access to ciphertext someone has already copied. | High (mechanics); Medium (tooling) |
| 4 | Custody of the online key: encrypted file, TPM-sealed (systemd-creds, clevis, Proxmox vTPM), YubiKey, HSM | A software age identity. Under A′ (A6 draft) it protects only data in transit, so unattended unlock is fine: a key file, or Tang/TPM with a manual fallback. It is rotated per epoch and destroyed after draining. Under plaintext postures it uses the **same unlock mechanism as the store volume**. The offline archive key X (A′) is admin-held: a passphrase- or YubiKey-wrapped file, brought online only for restores and rebuilds. Keep I off VM backups. Proxmox vTPM is excluded: its own documentation says it has no real security benefit. A YubiKey cannot hold a PQ ingest key. HSM is out of scope for cost. | Medium |
| 5 | Offline backup: SLIP-39 vs raw Shamir of an age identity (age-plugin-sss) vs paper QR vs extra hardware keys; k-of-n, holders, drill cadence | **SLIP-39 over a passphrase that wraps the PQ recovery identity, with a QR of the wrapped identity on every card.** age-plugin-sss is rejected: experimental, n stanzas per object, no Windows builds. Extra hardware keys are rejected under PQ. Default 2-of-3; E7-S1 checks it with real people. Card check every year; full drill at Gate C and whenever holders change. | Medium |
| 6 | Dedup secret delivered encrypted to the device key by the homelab; compatible with instant enrollment? | **Yes, if A1's construction B is adopted** (HMAC over the SHA-256). The device starts discovery and hashing at once, and derives IDs within seconds when the sealed secret arrives. Only the first upload waits until the homelab is reachable. Under construction A, late delivery would force a second full read. | Medium |
| 7 | Dedup-secret derivation and rotation (Wave 1 scope) | S_e is 32 random bytes per epoch, generated at the homelab and **not** derived from the recovery or admin root. A copy sealed to R goes in the doomsday kit. Rotate on every revocation for loss, theft, compromise or estrangement. No calendar rotation. | Medium |
| 8 | Key ceremony: air-gapped generation; fingerprints on cards and kits | Runbook draft in §F7. Use a live-boot offline machine, Go age ≥ 1.3.0 and python-shamir-mnemonic, verified against their checksums. Test-recover from every k-subset before printing. Print short fingerprints of the recipients and the admin root key. | Medium |
| 9 | PQ and crypto agility for keep-forever data (with A2) | Recommend **PQ for both the ingest and recovery recipients** (OD-06 and OD-08 decided together). Signatures can stay Ed25519 for now; the trust bundle must carry algorithm IDs so a PQ signature can be added later. | Medium-high |
| 10 | E7's succession requirement: can an heir read the archive without Reliquary? | Yes with this design, provided the stored form is age ciphertext decryptable by R. Otherwise the kit must also carry the volume key sealed to R, plus a runbook. The only non-stock step is transcribing words into the SLIP-39 tool. Time-delayed, owner-blockable release (Ente/Bitwarden) needs an online party and is not offered in v1 cryptography. | Medium |
| 11 | New: does D2-S1 (YubiKey ≥ 20 unwraps/s) still matter? | Only if OD-06 is "classic". A PQ ingest key cannot live on a YubiKey (§F3). If OD-06 is "PQ", mark D2-S1 "not applicable" and do not buy hardware for it. | High (logic) |

## Method

- **Sweep:** three scouts ran (docs, source, issues/forums), and their findings were merged. There was no separate pricing/standards scout; NIST material was blocked (see below).
- **Deep read (this stage):** the analyst re-fetched and read the load-bearing primaries:
  - the age spec in full;
  - the plugin spec label rules;
  - the age README (PQ and identity-file sections);
  - Go `filippo.io/age` v1.3.2 (`age.go`, `pq.go`, `extra/`, `cmd/age-plugin-batchpass`);
  - SLIP-39;
  - python-shamir-mnemonic 0.3.0 (`cli.py`);
  - age-plugin-yubikey 0.5.1 (`builder.rs`, `format.rs`, README);
  - age-plugin-sss, age-plugin-tpm and PaperAge READMEs;
  - Proxmox `qm.adoc` (TPM section);
  - the systemd-creds man page;
  - the rage `age` CHANGELOG;
  - the Ente Legacy docs.
- **Analyst checks run in the container** (scratchpad `d2-analyst/`; not the D2-S2 spike, which the spike runner owns; synthetic random bytes only, data class `SYN`):
  1. Built Go age v1.3.2 from the module proxy. The toolchain resolved to go1.27.0.
  2. Tested `age-keygen -pq`, a mixed PQ + X25519 encryption, two-PQ-recipient encryption and decryption with either identity, and `age-inspect`.
  3. Wrapped a PQ identity with a 128-bit hex passphrase (`age-plugin-batchpass`), split it with `shamir create 2of3 -S <hex>` and recovered it from shares 1 and 3 (`shamir_mnemonic.combine_mnemonics`). Decrypted a two-recipient object with the recovered identity. Also tried a wrong passphrase.
  4. A 2,000-iteration Go micro-benchmark of `DecryptHeader`, repeated 3 times, on a shared 4-vCPU Xeon @ 2.10 GHz. This is **not** homelab hardware, and the numbers varied about 2× between runs.
- **Routes used:** raw.githubusercontent.com mirrors, proxy.golang.org, static.crates.io and pypi.org.
- **Blocked sources, to be reported to H1** (none were silently replaced):
  - csrc.nist.gov and nvlpubs.nist.gov (NIST IR 8547, SP 800-57): PQ timeline claims are therefore **secondary only** and not load-bearing here.
  - rfc-editor.org and datatracker.ietf.org (RFC 5869, draft-ietf-hpke-pq-03, X-Wing).
  - support.apple.com (Legacy Contact, ADP recovery key), bitwarden.com/help, support.1password.com, tarsnap.com, signal.org, keybase.
  - Yubico developer docs (no performance figure found).
  - GitHub issue comment threads: age #136, age-plugin-yubikey #132 and rage #598/#621 are known from issue bodies and metadata only.
  - WebSearch: the scouts exhausted the budget.
  - During this stage the Go checksum database timed out once (`sum.golang.org`). The benchmark was built with the age module's own `go.sum` instead.
- **Stop rule:** the third scout added community evidence but no new primary source on custody or recovery. The deep read closed three scout leads:
  - the X25519 identity is also 32 CSPRNG bytes;
  - no tagpq identity plugin exists in Go age (the plugin says "the identity side is handled by a different plugin");
  - the yubikey defaults were re-checked in the crate.

## Sources

| # | Source | Publisher | Version or date | Accessed | Primary? |
|---|---|---|---|---|---|
| S1 | C2SP age spec, `C2SP/C2SP @ main : age.md` (editor's copy; stable at c2sp.org/age, which is blocked) | C2SP / F. Valsorda | editor's copy, main | 2026-09-29 | Yes |
| S2 | C2SP age plugin spec, `C2SP/C2SP @ main : age-plugin.md` (labels extension) | C2SP | main | 2026-09-29 | Yes |
| S3 | `FiloSottile/age @ main : README.md` (PQ keys, passphrase-protected key files, age-inspect) | F. Valsorda | main (download links v1.3.2) | 2026-09-29 | Yes |
| S4 | Go module `filippo.io/age` v1.3.2 via proxy.golang.org (`age.go` incompatibleLabelsError, `pq.go`, `extra/age-plugin-tagpq`, `cmd/age-plugin-batchpass`, `go.mod` "go 1.25.0"); tag times v1.3.0 2025-12-27, v1.3.2 2026-08-29 | F. Valsorda | v1.3.2 | 2026-09-29 | Yes |
| S5 | Rust `age` crate CHANGELOG, `str4d/rage @ main : age/CHANGELOG.md`; crate 0.12.1 source (scout) | str4d | 0.12.0 2026-07-13; 0.12.1 2026-07-14; Unreleased | 2026-09-29 | Yes |
| S6 | rage #621 "Add support for post-quantum recipients" (open) and #598 (community X-Wing draft) | GitHub | 2026-05-30; 2026-01-09 | 2026-09-29 (bodies only) | No |
| S7 | SLIP-0039, `satoshilabs/slips @ master : slip-0039.md` | SatoshiLabs | Status Final, created 2017-12-18 | 2026-09-29 | Yes |
| S8 | python-shamir-mnemonic 0.3.0 (PyPI; `README.rst`, `shamir_mnemonic/cli.py`) | Trezor | 0.3.0, 2024-05-16 | 2026-09-29 | Yes |
| S9 | age-plugin-yubikey README (main) and crate 0.5.1 (`src/builder.rs`, `src/format.rs`) | str4d | 0.5.1, 2026-04-08 | 2026-09-29 | Yes |
| S10 | age-plugin-tpm README (`Foxboron/age-plugin-tpm @ master`); v1.0.1 module (scout) | Foxboron | v1.0.1, 2026-01-24 | 2026-09-29 | Yes |
| S11 | age-plugin-sss README (`olastor/age-plugin-sss @ main`); v0.4.0 module and SPEC.md (scout) | olastor | v0.4.0, 2026-05-03 | 2026-09-29 | Yes |
| S12 | PaperAge README (`matiaskorhonen/paper-age @ main`) | M. Korhonen | main | 2026-09-29 | Yes |
| S13 | Proxmox VE docs, `proxmox/pve-docs @ master : qm.adoc` §"Trusted Platform Module (TPM)" | Proxmox | master | 2026-09-29 | Yes |
| S14 | systemd-creds(1), `systemd/systemd @ main : man/systemd-creds.xml` | systemd | main | 2026-09-29 | Yes |
| S15 | Clevis and Tang READMEs (`latchset/*`) (scout) | latchset | master | 2026-09-29 | Yes |
| S16 | systemd #39049 (TPM2 unlock fails without system change), #40159 (v259 unseal regression) | GitHub | 2025-09-20; 2025-12-20 | 2026-09-29 (bodies) | No |
| S17 | Ente Photos Legacy docs, `ente-io/ente @ main : docs/docs/photos/features/account/legacy/index.md`; Ente `architecture/README.md` (scout) | Ente | main | 2026-09-29 | Yes |
| S18 | Bitwarden server `EmergencyAccess.cs`, `EmergencyAccessService.cs` (scout) | Bitwarden | main | 2026-09-29 | Yes |
| S19 | restic `doc/design.rst` (keys; threat model on leaked master key) | restic | master | 2026-09-29 | Yes |
| S20 | age #136 "Changing recipients of existing encrypted files" (closed 2025-12-07, reportedly not planned) | GitHub | 2020-07-23 | 2026-09-29 (body only) | No |
| S21 | age-plugin-yubikey #132 (PIN cache expiring during bulk re-encryption) | GitHub | 2023-02-17 | 2026-09-29 (body only) | No |
| S22 | vsss-rs 6.0.1 README (scout) | M. Lodder | 6.0.1 | 2026-09-29 | Yes |
| S23 | SOPS v3.13.3 `sops.go`, `shamir/shamir.go` (scout) | getsops | v3.13.3 | 2026-09-29 | Yes |
| S24 | NIST IR 8547 ipd (2024-11-12), known from search snippets and secondary summaries only (encryptionconsulting.com, pqcmandates.com) | NIST | ipd 2024-11-12 | blocked | Primary **not read** |
| S25 | In-repo: `content-encryption-format.md` (T1 spike 2), `a1-content-identity.md`, `d1-threat-model.md`, `f3-security-literature.md` | Reliquary | 2026-09-29 | 2026-09-29 | No (internal) |
| S26 | age-plugin-se README, `remko/age-plugin-se @ main` (scout; not re-read) | R. Tronçon | main | 2026-09-29 | Yes |
| S27 | minisign README, `jedisct1/minisign @ master` (scout; not re-read) | F. Denis | master | 2026-09-29 | Yes |
| M1 | **Analyst container checks** (Method items 1–4): Go age 1.3.2 CLI and library, python-shamir-mnemonic 0.3.0 | this note | 2026-09-29 | — | Measurement |

## Claims

All skeptic columns are pending; skeptics should attack every row marked "Key".

| # | Claim | Sources | Key? | Skeptic 1 | Skeptic 2 | Skeptic 3 | Verdict |
|---|---|---|---|---|---|---|---|
| C1 | An age header wraps the same 128-bit file key independently in one or more stanzas. Identity implementations MUST ignore unrecognised stanzas. An ingest recipient plus a recovery recipient is therefore native, and the extra stanza does not stop the ingest identity from decrypting. | S1; M1 (both identities decrypt) | Yes | | | | pending |
| C2 | The same file SHOULD NOT be encrypted to `mlkem768x25519` (or `mlkem768p256tag`) and to non-PQ recipients. Go age 1.3.2 **refuses** it: `incompatible recipients: can't mix post-quantum and classic recipients` (reproduced). The `postquantum` plugin label enforces the same rule for plugins. | S1, S2, S4; M1 | Yes | | | | pending |
| C3 | An scrypt stanza MUST be the only stanza. A passphrase can therefore never be a second recipient on objects; it can only protect an identity file. | S1, S2 | Yes | | | | pending |
| C4 | Measured header sizes with Go age 1.3.2: one PQ recipient 1,627 B; two PQ recipients 3,184 B; two X25519 recipients 266 B. The second PQ recipient adds 1,557 B per object. | M1 (`age-inspect`, file sizes, benchmark) | Yes (cost) | | | | pending |
| C5 | The Rust `age` crate (0.12.1, 2026-07-14; the Unreleased section too) has no native `mlkem768x25519` recipient or identity. A rage feature request for PQ recipients was still open on 2026-09-29. So the Reliquary encoder must implement the X-Wing HPKE stanza itself, and the stock tool for heirs must be Go age ≥ 1.3.0. | S5, S6; S25 (F3 C5) | Yes | | | | pending |
| C6 | Stock-tool recovery chain: SLIP-39 2-of-3 shares (python-shamir-mnemonic 0.3.0, custom 128-bit secret) → hex passphrase → scrypt-wrapped PQ identity → decryption of a two-recipient object with Go age 1.3.2. It worked end to end once in the container. A wrong passphrase fails loudly (`incorrect passphrase`). | M1; S3, S7, S8 | Yes | | | | pending |
| C7 | A wrapped PQ identity is 260 B if only the `AGE-SECRET-KEY-PQ-1…` line (78 B) is wrapped. Wrapping the full `age-keygen -pq` output, including its ~1,960-character public-key comment, gives 2,266 B, which exceeds PaperAge's ~1.9 KiB QR limit. | M1; S12 | Yes (ceremony) | | | | pending |
| C8 | SLIP-39 (Final) needs secrets of at least 128 bits, a multiple of 16. 128-bit secrets give 20-word shares and 256-bit secrets 33-word shares. New shares SHOULD set the extendable flag, which lets more share sets with new identifiers reconstruct the same secret. Sets must not be mixed. SLIP-39's own passphrase cannot be verified: a wrong one silently yields a different secret. | S7 | Yes | | | | pending |
| C9 | The SLIP-39 reference implementation says it uses no hardening, is likely vulnerable to side channels, and "should not be used for handling sensitive secrets". Its CLI prints the recovered master secret as hex. | S8 | Yes (ceremony) | | | | pending |
| C10 | Proxmox VE documentation: an emulated vTPM "does *not* provide any real security benefits" compared with a physical TPM. | S13 | Yes | | | | pending |
| C11 | age-plugin-yubikey 0.5.1 writes classic P-256 stanzas (`piv-p256`; age1tag recipients on main). Defaults are PIN policy Once and touch policy **Always**. It has no decryption agent; the PIN cache is lost on unplug or applet switch and does not work on YubiKey 4. Go age ships `age-plugin-tagpq` only for the recipient side, and no identity plugin for `mlkem768p256tag` was found. **Inference:** under PQ, a YubiKey can hold neither the ingest key nor a recovery recipient. | S4, S9, S21 | Yes | | | | pending |
| C12 | Software unwrap rate in the container (single goroutine, N = 2,000, 3 runs): PQ first stanza 4,904–6,827/s; PQ second stanza (the recovery identity tries both) 1,489–2,797/s; X25519 3,359–7,676/s. That is two orders of magnitude above D2-S1's 20/s threshold. Not homelab hardware; noisy shared VM. | M1 | Yes (custody) | | | | pending |
| C13 | age-plugin-sss is "experimental until v1.0.0" (v0.4.0), has no Windows builds, splits each file's own key into n stanzas (one per share recipient), may prompt interactively for which share to decrypt, and produces long recipient strings. | S11 | Yes | | | | pending |
| C14 | Header MAC key = HKDF(file key, "header") and payload key = HKDF(file key, nonce, "payload"). Adding, removing or replacing a recipient rewrites only the header and MAC. Go age exposes `ExtractHeader`/`DecryptHeader`/`NewInjectedFileKeyIdentity` but no header-rewrite API. Upstream closed the "change recipients" request (#136). Reliquary must build its own rewrap tool. | S1, S4, S20 | Yes | | | | pending |
| C15 | Re-issuing SLIP-39 cards for the same secret (extendable) does not revoke old cards: any k old cards still reconstruct it. Only a new recovery key plus a header rewrap revokes, and never for ciphertext already copied. restic documents the same limit for a leaked master key. | S7, S19; inference | Yes | | | | pending |
| C16 | Under A1 construction B, a device can hash its whole library before it receives the dedup secret and derive IDs from cached SHA-256 values afterwards. Delivery of the sealed secret by the homelab therefore does not cost a second read; only the first upload waits. | S25 (A1 §5, D1 SR-15) + inference | Yes | | | | pending |
| C17 | TPM-sealed secrets have failed to unseal after routine OS changes (systemd #39049, #40159). TPM auto-unlock needs a tested manual fallback. | S16 (issue bodies) | No (supporting) | | | | Secondary only |
| C18 | NIST IR 8547 (ipd, 2024-11-12) proposes deprecating quantum-vulnerable key establishment after 2030 and disallowing it after 2035. | S24 (secondary only) | No: the PQ recommendation rests on C2, C4, C5 and keep-forever retention, not on these dates | | | | Secondary only |
| C19 | Ente Legacy: trusted contacts (Ente users, must accept) can start recovery; the owner can block it within 7, 14 or 30 days; the main use case is passing on memories after death. | S17 | No (similar work) | | | | pending |
| C20 | systemd-creds `auto` does not use the TPM2 when running in a container; `null` gives no confidentiality; the host key lives in `/var/lib/systemd/credential.secret` on the same disk. | S14 | No (custody detail) | | | | pending |

## Findings

### F1. Key inventory (draft for ADR-0008)

"Owner of spec" is the workstream that fixes the details; D2 fixes custody and backup for tiers 0 and 1.

| # | Key | Tier | Algorithm | Custody | Backup | Rotation | Compromise response | Owner of spec |
|---|---|---|---|---|---|---|---|---|
| K-01 | **Recovery identity R** | 0 offline | age mlkem768x25519 (32-byte seed) | Exists in the clear only during the ceremony and a recovery. Stored as a 260 B scrypt-wrapped identity file under passphrase W. | W split SLIP-39 k-of-n. The wrapped file is printed as a QR on every card and copied onto the doomsday USB. | Only on suspected exposure of ≥ k cards or of R itself. New R' → signed bundle → header rewrap of stored ciphertext (if A6 keeps ciphertext). | Rotate R and rewrap. Accept that ciphertext copied before the rotation stays readable (C15). | D2 |
| K-02 | **Admin root signing key A** | 0 offline | Ed25519 (minisign-style file) | Password-protected file on two offline media held by the owner | Copy sealed to R in the doomsday kit | Rare. The new key is signed by the old key, or re-pinned by kit if the old key is lost. | Re-pin through kits (painful): hence the two offline copies | D2 (custody); D3 (what it signs) |
| K-03 | **Ingest identity I_n** | 1 homelab online | age mlkem768x25519 | Software identity on the ingest VM, unlocked with the A6 volume mechanism (§F4), excluded from VM backups | **None needed**: disposable. In-flight objects are recoverable with R or by re-upload (SR-11d). | New I_{n+1} in an A-signed trust bundle, at least yearly and after any suspected ingest-VM compromise. The interval is a proposal with no primary source. Keep I_n until the R2 and USB pipeline drains (A3 DR-A3-3 bounds this), then destroy it. Late bundles stay readable through R. | Rotate now; treat everything staged under I_n as disclosed (AR-08) | D2 |
| K-03b | **Archive identity X** (only under A6 posture A′) | 0/1 admin, offline except for restores | age mlkem768x25519 | Passphrase-wrapped file on the admin's offline machine, or a file wrapped to a YubiKey. That wrap stays inside the house, so classic is fine. Brought online only for restores, catalog rebuilds and drills | Sealed to R in the doomsday bundle; a second offline copy | Rare. New X' means a header rewrap of the store, done with X online | Rotate and rewrap; ciphertext already copied stays exposed (C15) | A6 (posture); D2 (custody) |
| K-04 | Receipt / status signing key | 1 online | Ed25519 | Ingest VM, same protection as K-03 | None: disposable | New key certified by A in the trust bundle | Rotate; re-issue receipts if D4 requires it (A3) | A3 format; D2 custody |
| K-05 | Dedup epoch secrets S_e | 1 online | 32 random bytes → HKDF → HMAC key (A1) | Homelab keeps all epochs. Devices keep the current epoch in keystore-wrapped storage. | Each S_e sealed to R into the doomsday bundle | New epoch on trigger (§F5) | Rotate; the oracle over historical IDs remains (AR-06) | A1 (ID mechanics); D2 (custody, trigger) |
| K-06 | At-rest volume or dataset key(s) | 1 homelab | A6's choice (ZFS native, LUKS, or none) | A6 | Sealed to R into the doomsday bundle (a hard requirement from D2) | A6 | A6 | A6 |
| K-07 | Catalog key (if the catalog is encrypted separately) | 1 homelab | A6 | A6 | Sealed to R | A6 | A6 | A6 |
| K-08 | Homelab Cloudflare API tokens (pull-only) | 1 homelab | Bearer | Ingest VM | Password manager (owner) | Replace | Revoke in the Cloudflare dashboard | C1 |
| K-09 | Device Ed25519 signing key | 2 device | Ed25519 | Platform keystore, non-exportable where possible | **None**: re-enroll on loss | Re-enroll | Revoke (SR-17) | D3 |
| K-10 | Device restore / sealing key | 2 device | Recommended **mlkem768x25519** (see §F6); ADR-0001 says X25519 | Keystore-wrapped | None | Re-enroll | Revoke; the admin checks the fingerprint before restores (D1 SR-14 interim) | D3, A8 |
| K-11 | Update signing keys (two embedded) | project | Ed25519/minisign | Offline (D5) | D5 | D5 | D5 | D5 |
| K-12 | Play upload key | project | Play | D5/B3 | B3 | B3 | B3 | B3 |
| K-13 | Worker secrets (invite pepper, etc.) | cloud | HMAC | Worker secrets; **not trust-forging** (SR-23) | Password manager | Replace | Replace; the cost is availability and invites only | C1, D3 |
| K-14 | DKIM keys | cloud | C3 | C3 | C3 | C3 | C3 | C3 |

The Cloudflare account, domain registrar and Play console credentials are **accounts**, not keys. E7 owns the credential inventory. D2 requires only that their recovery codes go in the same R-sealed bundle.

**The doomsday bundle** is one age file encrypted to R. It holds K-02, K-03b (X, under A′), every S_e, K-06, K-07 and the account recovery codes, and is refreshed when any of them changes. Copies are safe anywhere, because R guards them. Refresh needs only R's *public* key, so it runs online with no ceremony.

### F2. The hierarchy and why a recovery recipient goes on every object from day one

```
             offline                                  homelab (online)                       devices
  R (PQ age identity; W split k-of-n) ──┐     I_n (PQ ingest identity) ─────────────┐     encrypt every object and
  A (Ed25519 root, 2 offline copies) ───┼──►  signs trust bundle: {I_n, R, K-04, S-epoch id, alg ids}   record to {I_n, R}
                                        │     K-04 receipts; S_e epochs  ───────────┴──► pinned by QR/kit (SR-02)
  doomsday bundle = age file to R ◄─────┘     (backups of A, X, S_e, volume keys, account codes)

  Under A6 posture A′, at ingest: header {I_n, R} → stored header {X, R}; the payload is unchanged; X is admin-held and offline
```

- **The format supports it** (C1). The cost is +1,557 B per object and per metadata record under PQ (C4); an X25519 second stanza would add 98 B.
  - At F3's arithmetic of 0.9M–4.5M files for 2–10 TB, two PQ stanzas mean roughly 2.9–14.3 GB of headers for content objects (3,184 B each). Records double that, to about 0.3 % of stored bytes, and about half of it is due to R. This is arithmetic, not measured on family data.
  - Header parsing must handle more than one stanza (CE §15 item 6 is already open).
- **Why devices should include R themselves, even under A′.** A′ destroys old ingest keys after draining. A USB bundle that sits in a drawer past that point, or an object from a device that was offline for months, would then be unreadable forever unless R is also a recipient. The device-side cost is 1.5 KB per upload.
- **Adding R later is expensive, and part of it is impossible.** The rewrap needs I online to recover each file key (C14). It rewrites every stored ciphertext header. It cannot reach objects already on USB sticks in drawers, or in R2 staging. It needs a custom tool, because upstream has none (C14). D2-S2 measures the rewrap cost. The one-way door (#3) is real.
- **What R protects depends on A6** (OD-07):
  - *If the store keeps the received age ciphertext* (A6 posture A, or A6's recommended **A′**, where headers are rewrapped at ingest to {X, R}), then R plus the disks is the whole doomsday story, using stock `age -d` alone. This is D2's preferred family of postures for succession (BUD-RECOVERY). A′ fits this note well:
    - I then guards only transit, so its custody can be light;
    - R is added to stored headers at ingest, even for anything a device sent without it.
  - *If the store is plaintext on an encrypted volume*, R-on-objects protects only staged and in-transit objects. The heir instead needs the volume key (K-06, sealed to R) plus a ZFS/LUKS import runbook, which is harder for a non-author. Either way, R is the root of the doomsday bundle.
- **Separation of duties.** Devices never hold R or I (settled: devices cannot read backups). The Worker holds nothing that forges trust (SR-23). I is disposable. A and R are offline.

### F3. PQ couples to every custody and recovery choice

- With a PQ ingest key, stock age forbids a classic second recipient (C2). So R must be `age1pq`. These are all excluded as recipients: YubiKey (`piv-p256`/age1tag), age-plugin-tpm (age1tag), age-plugin-se (P-256), and passphrase stanzas (C3).
- `mlkem768p256tag` (age1tagpq) exists in the spec for hardware, but no identity implementation was found. The ML-KEM half cannot run on a PIV applet as far as this sweep shows (C11). That last point is an absence claim for skeptics to attack.
- Hardware keys can still **protect an identity file at rest**: for example, a PQ identity file encrypted to a YubiKey and unlocked with a touch at boot. That file never leaves the house, so harvest-now does not apply to it.
- The Rust stack has no native PQ recipient (C5). Two consequences:
  - The client encoder must add the X-Wing HPKE stanza. The CE encoder is already custom, and F3 notes that the RustCrypto `x-wing` crate's wire compatibility is unverified.
  - The heir's stock tool is **Go age ≥ 1.3.0**. The doomsday kit must ship static Go age binaries for Windows, macOS and Linux, plus the source zip and the Sigsum-verifiable release reference (S4 `SIGSUM.md`).
- **If the owner declines PQ (OD-06 "classic")**, R can be X25519 and extra YubiKeys become possible recovery recipients. D2-S1 also becomes relevant again. The rest of this design is unchanged.

### F4. Custody of the online ingest key

| Option | What it protects against | Fits "unattended" and BUD-TTS? | Verdict |
|---|---|---|---|
| Plain file (0400, dedicated user) | Nothing at rest | Yes | Acceptable only if A6 also has no at-rest protection |
| Passphrase-wrapped identity (`age -p`, native `-i` support, S3) unlocked at service start | Stolen disks, VM backups, snapshots | No. After a power cut, ingest waits for the admin. Data stays staged and devices keep their files, so nothing is lost, but it is delayed. | Good if A6 also unlocks by hand |
| systemd-creds `host` in the VM | Only partial copies: the host key sits on the same disk (C20) | Yes | Weak; do not rely on it |
| systemd-creds `tpm2` on a **Proxmox vTPM** | Nothing real (C10) | Yes | **Excluded** |
| Physical TPM on the host (systemd-creds / clevis tpm2 with a PCR policy) | Disks removed from the machine | Yes, but PCR changes after upgrades can break unseal (C17) | Needs the manual fallback |
| clevis + Tang on another homelab host | Disks or backups taken off the LAN | Yes | Good auto-unlock option; one more service to run |
| YubiKey holding I | Key extraction | Unknown throughput; touch default is Always; PIN cache fragile (C11, S21) | **Impossible under PQ**; not recommended under classic |
| YubiKey wrapping I's file (touch once at boot) | Stolen disks, backups | No (needs a touch at boot) | Equivalent to the passphrase option, with hardware |
| HSM | Key extraction | Yes | Out of scope: cost and PQ support unknown |

**Recommendation.**

1. I is a software PQ identity. Software unwrap is not the bottleneck (C12).
2. **Under A′ (A6 draft), prefer unattended unlock.** I protects only data in transit, and a stall after a power cut threatens BUD-TTS. Use a key file on the ingest VM's disk, excluded from backups, or Tang auto-unlock where the owner already runs it. Short epochs plus destruction after draining limit what a later capture of I can open.
3. **Under postures that keep plaintext (A6 B)**, I sits on the same protected volume or dataset as the store and is unlocked by **the same mechanism and at the same moment** that A6 chooses for the store: a manual passphrase at boot, or Tang/TPM auto-unlock with a manual fallback. That means one unlock ceremony, and I is never weaker or stronger than the data it guards.
4. Keep I out of the VM's system-disk backups.
5. The archive key X (A′ only) is brought online only by the admin, for restores, rebuilds and drills. Store it as a passphrase- or YubiKey-wrapped file; D2-S1's throughput question does not arise for it.
6. No custody choice defends against a live ingest-VM compromise (AR-08). Only short-lived I (cheap rotation), store immutability (D4-S4) and SR-01 bound it.

Confidence: medium, because it depends on OD-07.

### F5. Dedup secret: derivation, custody, delivery, rotation

- **Derivation.** S_e = 32 CSPRNG bytes per epoch, as in A1. The dedup-ID key K_e = HKDF(S_e, "reliquary/v1/dedup-id-key"), which is A1's construction and CE D-4 generalised.
  - Do **not** derive S_e from R or A. That would put an offline root online at every rotation (so rotations would not happen), and it would reuse an age identity seed as a KDF root (key separation).
  - The backup problem is solved by sealing each S_e to R in the doomsday bundle.
  - Losing every S_e is survivable: start a new epoch and re-derive IDs from the catalog's SHA-256 values (A1 §5).
- **Delivery (SR-15).** The homelab seals S_e as a small age file to the device's sealing key. It does this only after the device key is authenticated by a path Cloudflare cannot forge (SR-14, D3). The Worker only relays the ciphertext.
  - Never put S_e on printed cards: cards sit in drawers for years and are photographed.
  - A USB kit may carry S_e in the clear for kit-enrolled desktops as the D1 interim, until SR-14 exists.
- **Instant enrollment.** Compatible under A1 construction B (C16). This is one more argument for DR-A1-1 option B.
  - Enrollment feels instant: discovery and hashing start immediately.
  - Uploads start when the sealed secret arrives. That is one homelab poll interval when the homelab is up, and indefinitely when it is down, which E3 should phrase plainly.
  - D3 decides whether that delay is acceptable against "near-zero-effort enrollment".
- **Harvest-now on delivery.** A sealed S_e that crosses Cloudflare under an X25519 device key could be opened by a future quantum adversary. Combined with the recorded cloud ID history, that adversary could test IDs for known files. Recommend the device sealing/restore key (K-10) be `mlkem768x25519` too. Restores re-encrypted to device keys carry plaintext content, so the same reasoning applies there with more force (hand-off to D3, A8, A2).
- **Rotation trigger (proposed; the owner decides).**
  - Rotate on **every revocation for loss, theft, suspected compromise or estrangement**.
  - Do not rotate on routine retirement of a device the admin has wiped.
  - No calendar rotation: rotation gives no forward secrecy for historical IDs (AR-06), so a schedule buys little.
  - Cost is A1-S2's measurement (target < 60 s per client, zero file reads, homelab < 24 h). If that holds, one admin command per incident fits BUD-SUPPORT.

### F6. Recovery design: offline backup, k-of-n, holders, drills

**Recommended construction (option A below).**

1. At the ceremony, generate R with `age-keygen -pq`. Keep only the `AGE-SECRET-KEY-PQ-1…` line (C7).
2. Generate W = 16 random bytes and write it as 32 lowercase hex characters. This matches age's own 128-bit file-key strength.
3. Wrap R: `age -p` (or batchpass during the ceremony) produces `recovery-identity.age` (260 B), which fits easily into a QR code (C7).
4. Split W with SLIP-39: `shamir create` with the extendable flag set and no SLIP-39 passphrase (C8's silent-wrong-passphrase hazard).
5. Each **share card** carries:
   - the 20 words;
   - the group and member numbers, as SLIP-39's first words show;
   - the QR of `recovery-identity.age`;
   - a short fingerprint of R's recipient (for example the first 8 hex digits of SHA-256 over the `age1pq1…` string; D3 fixes the exact format);
   - a one-page plain-language instruction.
6. **Recovery:**
   1. Collect k cards.
   2. Run `shamir recover`; it prints the hex (C9).
   3. Scan any card's QR into a file.
   4. Run `age -d -i recovery-identity.age <object>` and type the hex when asked. A wrong entry fails loudly (C6).

Verified once in the container (C6); D2-S3 tests it with a relative.

**Why this beats the alternatives:**
- It needs only stock tools; direct SLIP-39 of the seed would need a Bech32 re-encoding script.
- Shares are 20 words, not 33.
- Errors are detected: RS1024 checksums per share (C8), plus the scrypt MAC at the end.
- Any k cards are self-sufficient.
- A single card reveals nothing.

**Holders and k-of-n.** These are proposals for OD-08, pending E7-S1 with real people.

| Scheme | Holders (example) | Survives | Risk |
|---|---|---|---|
| **2-of-3 (default)** | Partner; an adult relative outside the household; a safe-deposit box or executor | Loss of any one card; the owner's death (partner + executor) | Any two holders together can read everything (AR-D2-1) |
| 3-of-5 | As above, plus two more relatives | Two lost cards | More people, and more drift over decades |
| Two groups, GT = 1: owner 2-of-2 (home safe + bank box) **or** family 2-of-3 | — | The owner can self-recover without relatives; the family can recover without the owner | Doubles the paths to R; more complex to explain |

**Life events** (E7 hands these back to D2):

| Event | Action |
|---|---|
| A holder dies, leaves or becomes estranged, and their card is retrieved | Re-issue a new extendable set for the same W and destroy the old cards. No cryptographic rotation. |
| A card may be in hostile hands | If fewer than k cards are at risk, re-issue and accept the risk. If k or more are at risk, rotate R and rewrap (C15). |

**Drill cadence.**
- **Every year:** a card check. Each holder confirms they still have the card, and the owner validates each share's checksum on an offline machine. A single share is useless alone, and the owner is admin anyway.
- **Full recovery drill:** at Gate C (D2-S3), after any holder change, and at least every 3 years. This is a proposal; there is no primary source for the interval.

### F7. Key-ceremony runbook (draft; D2 owns the final version)

Data class: the ceremony handles production secrets, so it is never run with family content present and never logged to the repo (H3).

1. **Prepare (online machine, before the day).**
   1. Download Go age ≥ 1.3.0 release archives for Linux, Windows and macOS. Verify them with Sigsum (S4 `SIGSUM.md`), or build from the proxy.golang.org module zip and record its hash.
   2. Download the python-shamir-mnemonic wheel (and `click`) and record their hashes.
   3. Get a printer with no network, or a PDF-to-USB path, PaperAge (optional) and qrencode.
   4. Write everything onto a read-only USB.
2. **Air-gapped machine.** Boot a Linux live image with networking hardware disabled or unplugged. Mount the tools USB read-only and check every hash.
3. **Generate R.**
   1. `age-keygen -pq -o r.txt`, then `age-keygen -y r.txt > r.pub`.
   2. Strip `r.txt` to the identity line.
   3. Compute and write down the fingerprint of `r.pub`.
4. **Generate and split W.**
   1. `shamir create custom -t 1 -g 2 3 -x -S $(head -c16 /dev/urandom | xxd -p)` (or the chosen scheme). This prints W as "Using master secret".
   2. Wrap: `age -p -o recovery-identity.age r.txt` and enter W.
5. **Verify before printing.**
   1. For **every** k-subset of shares, run `shamir recover`, check that the hex matches, then `age -d -i recovery-identity.age test.age`. Here `test.age` is a test file encrypted to `r.pub`.
   2. Run `age-inspect` on a test object encrypted to {I, R}.
6. **Generate A** (Ed25519, minisign-style, password-protected). Print A's public-key fingerprint.
7. **Assemble the trust bundle** {I_1 recipient, R recipient, K-04 public key, epoch id, algorithm ids}. I_1 and K-04 are generated on the homelab beforehand and brought in as public keys. Sign the bundle with A. Its digest is what QR and kits pin (SR-02, D3).
8. **Print** the cards (§F6), the fingerprint sheet (R, A, bundle digest) and the recovery instruction page. Verify each printed QR by scanning it on the air-gapped machine.
9. **Destroy.** Wipe `r.txt`; W only ever existed on screen and in RAM. Power off, which clears the live system's RAM. Keep only:
   - `recovery-identity.age`;
   - `r.pub`;
   - A's encrypted key file on two offline media;
   - the signed bundle.
10. **Seal the doomsday bundle** online later: it needs R's public key only.
11. **Record** the date, tool versions and hashes, fingerprints and the holder list (names only) in the owner's ceremony log. Do not record W or any shares.

### F8. Succession (E7 requirement as handed over)

Since no E7 note exists, D2 took the requirement from PLAN §E7:
- break-glass without the owner;
- an heir can read the archive without Reliquary;
- a doomsday kit;
- life events.

This design meets them *cryptographically*, provided the stored form is decryptable by R, or K-06 is in the doomsday bundle.

**Time-delayed, owner-blockable release** (Ente Legacy's 7/14/30-day window, C19; Bitwarden's WaitTimeDays, S18) needs an online party that holds a wrapped key and enforces the delay. In Reliquary the candidates are:
- the homelab, which may be the thing that died;
- the Worker, which must hold no trust keys (SR-23).

So v1 offers **no cryptographic time delay**. E7 can add social friction instead: holders agree to call the owner first. Gate C's dead-man's switch can send *instructions*, never keys. Recorded as AR-D2-2.

### Alternatives compared

| Option | Fit with settled requirements | Pros | Cons | Evidence |
|---|---|---|---|---|
| Single homelab key (ADR-0001 as written) | Fits the text | Simplest | Loss of the key or the owner = loss of everything; no succession | PLAN D2, E7 |
| **Ingest I + offline R on every object, both PQ (recommended)** | Fits: devices still cannot read; the admin still decrypts everything | Native age; stock-tool recovery; I disposable | +1.56 KB per object; custom PQ encoder in Rust; heirs need Go age ≥ 1.3.0 | C1, C2, C4, C5 |
| I + R, both X25519 | Fits | Smallest header; Rust support; YubiKeys possible as R | Harvest-now on keep-forever data | C4; F3 C24 |
| Mixed PQ I + classic R | — | — | Violates the spec's SHOULD NOT; Go age refuses | C2 |
| R added only at homelab ingest (A′ rewrap), not by devices | Fits | No per-object cost on devices | Objects still in transit when their ingest key is destroyed (USB bundles in drawers, long-offline devices) become unreadable forever | F2 |
| **Offline backup: SLIP-39 over W wrapping R, QR on each card (recommended)** | — | Stock tools; 20 words; errors caught; cards self-sufficient | Needs a QR scanner or a typed QR; relies on python-shamir-mnemonic (unhardened) | C6–C9 |
| SLIP-39 directly over R's 32-byte seed (33 words) | — | One artifact type | Bech32 script needed (non-stock); 33 words; verify by fingerprint only | C8 |
| age-plugin-sss as R | — | Threshold inside age | Experimental; n × 1.56 KB per object under PQ; holders need age identities for decades; no Windows builds | C13 |
| Paper QR of R + a memorised passphrase (PaperAge) | — | Simple | Single point of failure; dies with the owner unless written down | S12 |
| Extra YubiKeys as recipients | Only if OD-06 = classic | No shares to transcribe | Classic only; PINs must be passed on; hardware ages over decades; needs the plugin | C11 |
| Time-delayed online escrow (Ente/Bitwarden style) | Conflicts with SR-23 / homelab-only | Owner can block | Needs a trusted online party | C19, S18 |

### Similar work and lessons

| Project | What they do | Borrow or avoid | Source |
|---|---|---|---|
| age-plugin-se README | Hardware-bound keys cannot move; advises also encrypting to a backup key | Borrow: I + R is the same pattern | S26 |
| restic | A master key wrapped by several key files; a leaked master key cannot be rotated in place | Borrow the honest limit (C15) | S19 |
| SOPS | Data key split across key groups with Vault's Shamir | Shows threshold-over-recipients works, but per file: avoid for objects | S23 |
| Ente recovery key and Legacy | Recovery key wraps the master key; time-delayed trusted-contact recovery | Borrow the plain-language framing; the time delay needs a server (not v1) | S17 |
| Bitwarden Emergency Access | Grantee public key, KeyEncrypted, WaitTimeDays, View vs Takeover | Same as Ente | S18 |
| Trezor SLIP-39 | Word shares; multi-share flows have had repeated UX bugs | Expect ceremony errors: verify every k-subset before printing | S7; scout issues (low confidence) |
| Apple ADP / Legacy Contact, 1Password Emergency Kit, Tarsnap keymgmt, Signal SVR, Keybase paper keys, Dark Crystal | — | **Not read** (blocked or not reached) | open |

### Tools and libraries

| Name | Purpose | Licence | Maturity | Source |
|---|---|---|---|---|
| Go `filippo.io/age` + `age-keygen`, `age-inspect`, `age-plugin-batchpass` | Homelab decrypt, ceremony, heir tool | BSD-3-Clause (not re-checked) | v1.3.2, 2026-08-29; PQ since v1.3.0 (2025-12-27) | S4 |
| Rust `age` | Client decrypt side; no PQ recipient | MIT/Apache-2.0 | 0.12.1, 2026-07-14 | S5 |
| python-shamir-mnemonic | SLIP-39 split and recover | MIT (not re-checked) | 0.3.0, 2024-05-16; self-declared unhardened | S8 |
| vsss-rs | Rust Shamir/Feldman if Reliquary ever builds its own share tool | Apache-2.0 | 6.0.1; audits funded per README (reports not read) | S22 |
| age-plugin-yubikey | Hardware-wrapped identity *file* at rest (classic) | MIT/Apache-2.0 | 0.5.1, 2026-04-08 | S9 |
| age-plugin-tpm | TPM-held classic identity | MIT (not checked) | v1.0.1; awesome-age marks it experimental | S10 |
| age-plugin-sss | Per-file threshold | not checked | v0.4.0, experimental | S11 |
| clevis/tang, systemd-creds | Auto-unlock of I's file or the volume | GPL/LGPL (not checked) | mature | S14, S15 |
| PaperAge | QR PDF of a passphrase-encrypted payload (≤ ~1.9 KiB) | MIT (not checked) | main | S12 |
| minisign | Admin root key A (Ed25519) | ISC (not checked) | mature | S27 |

## Spikes

The spike runner fills this section; it runs in parallel. The rows below restate the PLAN spikes plus this note's view on applicability.

| Spike | Hypothesis | Pass → / fail → (decision) | Exec tag | Budget IDs | Data class | Status | Result |
|---|---|---|---|---|---|---|---|
| D2-S1 YubiKey unwrap throughput | ≥ 20 unwraps/s unattended | Pass → a YubiKey may hold I; fail → hardware only offline. **Analyst view: not applicable if OD-06 = PQ (C11).** The software baseline is C12. | CT/OL | BUD-INGEST, BUD-TTS | SYN | (spike runner) | (spike runner) |
| D2-S2 Encrypt to I + 2-of-3 split R; destroy I; recover; rewrap vs re-encrypt cost | Recovery succeeds; the cost of adding R later is measured | Pass → ADR-0008 as recommended; the rewrap cost goes into one-way door #3. Fail → revisit the recovery construction before Gate A | CT | BUD-RECOVERY (indirect) | SYN | (spike runner) | (spike runner) |
| D2-S3 Combined recovery drill (the only one) | A non-author recovers 10 named photos with the kit and stock tools | Within BUD-RECOVERY and without owner help → Gate C passes | FM | BUD-RECOVERY | FAM (owner's own photos, consented) | (spike runner: kit) | (spike runner) |

## Conflicts with settled text

- **None that contradict.** Three points for the owner to see:
  1. ADR-0001 says content is encrypted "to the homelab public key", singular. Adding R extends this; it does not change who can read. The admin still decrypts everything, and devices still cannot.
  2. **However,** k colluding share holders can also decrypt everything. CLAUDE.md scopes privacy "against outsiders … not against the admin". Share holders become admin-equivalent collectively. Recorded as AR-D2-1 for OD-17; no settled-text change is needed if the owner accepts it.
  3. ADR-0001 says "e.g. X25519 / age". PQ fits the "e.g.", and ADR-0001 §6's device X25519 restore key likewise. Recommending PQ device sealing keys (K-10) is a hand-off, not a conflict.

## Open questions

1. **A6 posture (OD-07):** the A6 draft recommends A′ (ciphertext rewrapped to {X, R}), which suits this design. Open points:
   - whether X and R should both exist or be merged; this note says keep both, because merging would force a k-of-n gathering for every restore;
   - the ingest-key epoch interval;
   - how long the original 184-byte header (`.h0`) must be kept.

   Owner: A6 with D2, Gate A.
2. **Wire compatibility** of a Rust X-Wing HPKE stanza (RustCrypto `x-wing` "draft 06") with Go age's `mlkem768x25519`, tested against CCTV hybrid vectors. Owner: A2/G2, before Gate A.
3. **Existence of any hardware identity for `mlkem768p256tag`.** This is an absence claim (C11). Owner: D2 skeptics.
4. **Rewrap tool design and cost** (D2-S2), and whether A6 addresses the store by plaintext SHA-256 so that header rewrites never move data. Owner: D2-S2, A6.
5. **Exact fingerprint format** on cards and kits. Owner: D3 (ADR-0014).
6. **Whether any SLIP-39 tool other than the unhardened reference suits the ceremony** (for example Trezor hardware with an imported custom secret: not checked). Owner: D2 follow-up.
7. **Similar-work sources not read** (Apple ADP/Legacy Contact, 1Password, Tarsnap keymgmt, Signal SVR, Dark Crystal, NIST SP 800-57 cryptoperiods). Owner: H1, via alternative routes.
8. **Whether "uploads wait for the sealed dedup secret"** is acceptable under near-zero enrollment when the homelab is down. Owner: D3 (OD-05 neighbourhood), E3 wording.

## Recommendation

**ADR-0008 strawman:**

1. **Two recipients on every age file a device writes:** a disposable online ingest key I and an offline recovery key R. Both are `mlkem768x25519` if OD-06 = PQ, which this note recommends. Both are X25519 otherwise. Never mix the two kinds.
2. **R is stored only as a 260-byte passphrase-wrapped age identity.** Its 128-bit passphrase is split with SLIP-39: default 2-of-3, extendable, no SLIP-39 passphrase. Every card carries the wrapped identity as a QR plus R's fingerprint. Recovery uses only python-shamir-mnemonic and Go age ≥ 1.3.0, which ship in the doomsday kit.
3. **An offline Ed25519 admin root key A signs the trust bundle** {I, R, receipt key, epoch, algorithm ids}. A is backed up on two offline media and sealed to R.
4. **I is software and rotated per epoch by a signed bundle.** Under A6's A′ it unlocks unattended; under plaintext postures it shares the volume unlock. It is excluded from VM backups, never on a Proxmox vTPM, and never on a YubiKey under PQ. Under A′, stored headers are rewrapped to an **admin-held offline archive key X plus R**. X is kept separate from R, so that restores do not need the share holders.
5. **Dedup secrets are random per epoch,** sealed by the homelab to authenticated device keys, backed up sealed to R, and rotated on every loss, theft, compromise or estrangement revocation.
6. **One doomsday bundle** (an age file to R) holds every other secret the heir needs. It is refreshed online.

**What would change this:**

- OD-06 = classic: R may be X25519 or YubiKeys, and D2-S1 matters again.
- E7-S1 shows relatives will not hold word cards: move to hardware tokens (classic only) or to professional escrow of shares.
- D2-S3 fails BUD-RECOVERY on the SLIP-39 step: switch to direct 33-word shares with a printed conversion tool, or to fewer, simpler steps.
- A6 chooses plaintext at rest with a complex volume stack: the kit needs a much longer runbook, so D2 would argue for keeping ciphertext.

## Decision requests

### OD-08: Recovery recipient, k-of-n and share holders (with OD-06)
- **Needed by:** Gate A, before the first real ingest (one-way door #3).
- **Evidence:** this note (§F2, §F3, §F6); F3 note C4–C6; `content-encryption-format.md` D-2/D-3.
- **Options:**
  | Option | What it means for the family | Cost (money and owner time) | Reversibility | Risks |
  |---|---|---|---|---|
  | A. PQ I + PQ R, SLIP-39 2-of-3 over the wrapped R (recommended) | Three people each keep one card; any two plus the kit recover everything | One ceremony (half a day); about 1.5 KB extra per file; yearly card check | One-way door for existing objects; holders can be changed by re-issuing cards | Two holders together can read everything (AR-D2-1) |
  | B. Same, 3-of-5 or two groups | More people involved; survives two lost cards | Same | Same | More coordination over decades |
  | C. No recovery recipient (ADR-0001 as written) | The archive dies with the homelab key or the owner | None now | Adding R later means a rewrap, and cannot reach USB or staged objects | Permanent loss (D1 catastrophic outcome) |
  | D. Classic I + R (X25519 / YubiKeys) | Hardware keys possible | Smaller headers | Same door | Harvest-now on keep-forever data |
- **Recommendation:** A. It is the only option that gives heirs a stock-tool path without the owner, at a cost of about 0.15 % of storage for R's stanzas (all PQ headers together come to about 0.3 %; arithmetic). Choose holders after E7-S1.
- **Touches settled text:** none. It records AR-D2-1 for OD-17.
- **If no decision by the deadline:** the run assumes option A with 2-of-3. No production ceremony runs, so Gate A cannot pass.

### OD-06 coupling (to A2; not a new item)
Decide OD-06 and OD-08 in the **same sitting**. A "PQ" answer forces a PQ recovery key and excludes hardware recipients. A "classic" answer re-enables D2-S1.

### DR-D2-1 (new, to H1 for numbering): dedup-secret rotation trigger
- **Needed by:** Gate A (with ADR-0006/0008).
- **Options:**
  - (a) every loss, theft, compromise or estrangement revocation (recommended);
  - (b) confirmed compromise only;
  - (c) a calendar schedule.
- **Recommendation:** (a). It is cheap if A1-S2 meets its targets, and it bounds a leaked secret's use against future uploads.
- **Touches settled text:** none.
- **Default if no decision:** (a).

### DR-D2-2 (new, to H1 → OD-17): accepted-risk candidates
- **AR-D2-1:** any k share holders together can decrypt the whole archive.
- **AR-D2-2:** v1 has no cryptographic time-delayed or owner-blockable release; succession friction is social.
- **Recommendation:** accept both.

## Hand-offs

| To | What | Why |
|---|---|---|
| A2 (ADR-0007) | Two stanzas per object and per record; PQ-only or classic-only header parser; the encoder needs the X-Wing stanza (C5); CE §15 item 6 | The recipient set is D2's; the envelope is A2's (PLAN cycle A2 ↔ D2) |
| A6 (ADR-0012) | Under A′: stored headers are {X, R} (both PQ if OD-06 = PQ); keep X separate from R; the proposed I epoch interval; unattended I unlock. Under B: I shares the volume unlock. In every posture, K-06/K-07 must be sealed to R | F1, F2, F4 |
| A1 (ADR-0006) | Construction B also makes sealed delivery of the dedup secret cheap (C16); trigger policy DR-D2-1 | F5 |
| D3 (ADR-0014) | Trust-bundle contents and signature by A; fingerprint format; K-10 as `mlkem768x25519`; S_e sealing only after SR-14; enrollment wording when the homelab is down | F1, F5 |
| A8 (ADR-0028) | Restores to PQ device keys (harvest-now) | F5 |
| D5 (ADR-0015) | Update keys stay outside this hierarchy; algorithm IDs for a future PQ signature | F1 |
| E7 (ADR-0040) | Holder selection (E7-S1); life-event actions for card re-issue; social delay in place of a time lock; kit contents (Go age binaries, shamir tool, cards, instructions) | F6, F8 |
| G2 (ADR-0035) | CCTV hybrid vectors; a negative test that a mixed PQ + classic header is never produced | C2, C5 |
| H1 | Blocked-source list (Method); numbering for DR-D2-1/2 | PLAN §5.4 |
