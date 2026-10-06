# D2. Key hierarchy, custody, recovery and succession cryptography

- **Workstream:** D2 (see `docs/research/PLAN.md`, section "D2.")
- **Status:** Final for Wave 1 (batch W1-a). Three skeptic lenses (sources, logic, adversary) reviewed this note. The claim verdicts below are the computed tally, used exactly. Holders, the human drill (D2-S3), time-delayed release and the hardened SLIP-39 tool carry over to Wave 2.
- **Date:** 2026-09-29 (last updated 2026-10-06). The run's frame date is 2026-09-29. Later stages ran on a container clock that read 2026-10-06, so spike and review evidence carries that date. Both dates are given as recorded and none is back-dated.
- **Feeds:**
  - ADR-0008 (`docs/adr/0008-key-hierarchy-custody-recovery.md`, Proposed, partial);
  - `docs/security/key-inventory.md` (Draft);
  - `docs/security/key-ceremony-runbook.md` (Draft; includes the share plan and the annual check checklist);
  - OD-08; OD-06 (coupling; A2 owns it); OD-07 (coupling; A6 owns it); OD-17 (AR-D2-1, AR-D2-2);
  - DR-A2-2 (joint with A2 and A6); new DR-D2-1..4;
  - one-way door #3 (recovery recipient in the key hierarchy).
- **Depends on:**
  - D1 (SR-02, SR-14, SR-15, SR-23, SR-27, SR-29, AR-03, AR-06, AR-07, AR-08);
  - A1 (dedup-ID construction and epochs, DR-A1-1);
  - A2 (envelope, OD-06, DR-A2-2, its C9, and the per-mean-size table in its §F2);
  - A3 (drain bound, DR-A3-3);
  - A6 (posture A′, h0 handling);
  - E7 (break-glass requirement). No E7 note exists yet, so the requirement is taken from PLAN §E7.
  - T1 spike 2 (`content-encryption-format.md`) and F3.
- **Traceability rows advanced:**
  - OPEN-3b and Q1-2a: homelab keypair custody and generation.
  - OPEN-3c and Q1-2b: dedup-secret custody and rotation trigger. A1 keeps the ID mechanics.
  - R-20, R-22 (see "Conflicts with settled text"), R-26.

> **Source of record.** This note is the D2 source of record. The analysis summary passed to the synthesis stage still described a design that the analysis itself had already withdrawn. "Superseded statements" below lists those statements so nobody ratifies them by mistake.

## Summary

Reliquary needs two ways into the archive:

- an **online ingest key I_e** at the homelab, rotated per epoch;
- an **offline recovery key R** that nobody holds in one piece.

age supports this natively (C1, verified). If the owner chooses post-quantum (OD-06), every recipient on a header must be PQ, because the age spec says not to mix PQ and classic recipients and Go age refuses to (C2, verified).

**Design (P1 plus escrow):**

- **Devices** write only the ingest stanza.
- **The homelab** rewraps stored headers to {X, R}, where X is the admin's archive key.
- **Every ingest key** is sealed to {X, R} when it is created. Its online copies are deleted after the drain bound.

Two reasons for this design:

- the homelab cannot check an R stanza that a device wrote;
- escrow covers late bundles at a cost per epoch rather than per object.

The earlier "devices must also write R" argument was refuted by all three lenses (C21, contested) and is not used.

**R itself:**

- R is a PQ age identity, stored as a 422-byte armored file wrapped with a passphrase W.
- W is 128 bits, split with SLIP-39 into 20-word cards: 2-of-3 by default, extendable, with no SLIP-39 passphrase.
- Each card also carries the wrapped file as a QR code.
- In the container the whole chain ran end to end, including a QR round trip (C6 verified; C25 new). No relative has tried it yet; D2-S3 is kit-ready.

This round's review added four requirements:

1. a trust bundle with anti-rollback and expiry;
2. strict header-shape checks before any unwrap;
3. a rewrap tool that enforces the no-mixing rule and drops the ingest stanza;
4. independent entropy for W at the ceremony.

The review also made clear that the **update-signing key is as powerful as A** for future uploads.

**Confidence:**

- High for the format facts.
- Medium for the custody and recovery design, which depends on OD-06, OD-07 and on real people (E7-S1, D2-S3).

## Questions

| # | Question (PLAN D2, Wave 1 scope) | Short answer | Confidence |
|---|---|---|---|
| 1 | Key inventory: custody, backup, rotation and compromise response for each key | 16 rows in four tiers (§F1; normative draft `docs/security/key-inventory.md`). Backups are split into an **offline bundle**, sealed only on the air-gapped machine, and an **online bundle** that the homelab may refresh. The online bundle never holds Tier-0 keys. The update-signing key (D5) is ranked Tier 0. | Medium |
| 2 | Online ingest key plus an offline recovery recipient from day one? | **Yes, on every stored object from day one.** The homelab writes the R stanza at the A′ rewrap (P1). Each I_e is escrowed to {X, R} when it is created (§F2). | High (format); Medium (placement, a joint decision, DR-A2-2) |
| 3 | Rotation by rewrap only; what the at-rest posture implies | Payloads are never touched; only headers change (C14). I_e is rotated by an A-signed trust bundle. Replacing R or X needs a store-wide header rewrap. Neither a rewrap nor re-issued cards revokes copies already made: snapshots, replicas, h0, sidecars, staged or USB copies (C15, scoped by the adversary lens). | High (mechanics); Medium (tooling) |
| 4 | Custody of the online key | A software PQ identity, held in RAM. Under A′ it is loaded unattended through Tang into tmpfs, with a manual fallback. It must never be on snapshotted, replicated or backed-up storage. A6 must ensure h0 and a disk-resident I_e never sit together in the clear (§F4). It is never on a Proxmox vTPM (C10). A YubiKey (PIV) cannot hold a PQ key (C11, contested overall; the YubiKey part was upheld by all three lenses and by D2-S1's reading of the crate). | Medium |
| 5 | Offline backup method; k-of-n; holders; drill cadence | SLIP-39 over a 128-bit W that wraps R. W is drawn from the OS plus dice. Shares are 20 words. Each card carries a QR of the armored wrapped identity, and the doomsday USB carries the file. Default 2-of-3; holders after E7-S1. Human drills use throwaway keys. A real-key check runs only on the air-gapped image and includes an R-stanza audit (§F6). Cadences are owner-tunable defaults with no primary source. | Medium |
| 6 | Dedup secret sealed by the homelab; compatible with instant enrollment? | **Open.** Under A1 construction B no second file read is needed. However, every upload that needs a dedup ID waits until S_e arrives, and the delivery path is D3's to design (SR-15, SR-14). C16 is **contested** and is not used as support. | Low |
| 7 | Dedup-secret derivation and rotation | 32 random bytes per epoch, generated at the homelab; not derived from R or A. Backed up in the online bundle. DR-D2-1: rotate on every revocation for loss, theft, compromise or estrangement, conditional on DR-A1-1 = B and A1-S2. | Medium |
| 8 | Key ceremony | Draft runbook `docs/security/key-ceremony-runbook.md`. W combines OS and dice entropy and never appears on a command line. Interactive prompts are never captured, and logs are grepped for secrets before leaving the machine. Every k-subset is tested and the printed QR is scanned back. Both bundles are sealed at the ceremony. | Medium |
| 9 | PQ and crypto agility | Recommend `mlkem768x25519` for R and X, decided together with OD-06. The encoder route for I_e is A2's choice. Signatures stay Ed25519, with algorithm IDs in the trust bundle. | Medium-high |
| 10 | E7 succession: can an heir read the archive without Reliquary? | Yes, with R, the disks, and upstream Go age ≥ 1.3.0 (or an older age plus `age-plugin-pq`), provided stored headers carry R. A non-technical heir needs these delivered on a recovery USB; this is not proven until D2-S3. A time-delayed release is not forbidden by SR-23. v1 leaves it out by choice (AR-D2-2). | Medium |
| 11 | Does D2-S1 (YubiKey ≥ 20 unwraps/s) still matter? | Only if OD-06 = classic. Its 20/s line is also below the roughly 90/s that BUD-INGEST implies (arithmetic, §F4). Flagged to H1. | High (logic) |

## Method

- **Sweep:** docs, source, and issues/forums scouts. There was no standards scout, because NIST was blocked.
- **Deep read:** the analyst read the load-bearing primaries and ran container checks (M1).
- **Spikes:** the spike runner ran D2-S1 (emulated) and D2-S2, and prepared the D2-S3 kit.
- **Skeptic review:** three lenses, each re-running part of the measurements. Their verdicts are in Claims.
- **Synthesis checks (M2; data class `SYN`, tmpfs, deleted afterwards):**
  1. Built `age-plugin-pq` from `filippo.io/age` v1.3.2. With it on `PATH`, Debian age 1.1.1 decrypted a two-PQ-recipient object written by Go age v1.3.2. Without it, the decrypt failed with "couldn't start plugin".
  2. Ran the recommended construction end to end:
     - PQ R;
     - `shamir create custom -t 1 -g 2 3 -x -s 128`, with shamir drawing W (20-word shares);
     - an armored scrypt wrap of R's identity line (422 B);
     - a QR of the armored file (segno 1.6.6, version 16-M), decoded back byte-identical with zxing-cpp 3.1.1;
     - every 2-subset recovered W, unwrapped the scanned file and decrypted an {I, R} object;
     - a single share was refused, and so was a wrong secret.
  3. Re-read the age spec (SHA-256 `b0a767b9…0232f`), the age-plugin-se README and the rage CHANGELOG.
- **Final synthesis checks (M3, 2026-10-06; reading only):**
  1. `f3-security-literature.md` §2 ("Measured on public data") contains "2–10 TB is roughly 0.9–4.5M photos at the Open Images mean". The earlier claim that "F3 does not contain them" was wrong (both A2 C21 and the previous version of this note). The figure counts photos only.
  2. Go age v1.3.2 `internal/format/format.go` caps headers at 2 MiB (`maxHeaderBytes = 2 << 20`) and 1,024 stanzas (`maxRecipientStanzas`).
  3. Go age v1.3.2 `age.go` applies the PQ/classic mixing check (line 215) only through `Encrypt` and `WrapWithLabels`.
  4. `spikes/D2-S2/rewrap/main.go` calls `extra.Wrap` directly and appends stanzas after the existing ones, so it bypasses that check and keeps the I stanza. That is acceptable for a spike, but not for production (§F2).
  5. python-shamir-mnemonic 0.3.0 `cli.py` accepts a custom secret only as `-S HEX` on the command line. The library `generate_mnemonics(group_threshold, groups, master_secret, passphrase, extendable, iteration_exponent)` takes bytes.
- **Routes used:** raw.githubusercontent.com, proxy.golang.org, static.crates.io and pypi.org.
- **Blocked sources:** reported to H1 and not silently replaced.
  - csrc.nist.gov and nvlpubs.nist.gov: NIST IR 8547 and SP 800-57. SP 800-57 Pt 1 r5 was retried on 2026-10-06 and returned `EGRESS_BLOCKED`.
  - rfc-editor.org and datatracker.ietf.org.
  - support.apple.com, bitwarden.com/help, support.1password.com, tarsnap.com, signal.org and keybase.
  - Yubico developer docs.
  - GitHub issue threads beyond their bodies, and the GitHub API for C2SP and rage.
  - c2sp.org/age (the stable spec).
- **Stop rule:** the third scout added no new primary source. The skeptics then found three primaries the sweep had missed (C22–C24), and all three were re-read.

## Sources

| # | Source | Publisher | Version or date | Accessed | Primary? |
|---|---|---|---|---|---|
| S1 | C2SP age spec, `C2SP/C2SP @ main : age.md` (editor's copy; the stable c2sp.org/age is blocked). SHA-256 `b0a767b91a184c536e8a04002f7bba7521388fee3989f5891e23cc1aaa00232f` | C2SP | main | 2026-09-29; re-read 2026-10-06 | Yes |
| S2 | C2SP age plugin spec, `C2SP/C2SP @ main : age-plugin.md` | C2SP | main | 2026-09-29 | Yes |
| S3 | `FiloSottile/age @ main : README.md` | F. Valsorda | main (v1.3.2) | 2026-09-29 | Yes |
| S4 | Go module `filippo.io/age` v1.3.2 via proxy.golang.org: `age.go`, `pq.go`, `internal/format/format.go`, `extra/age-plugin-pq`, `extra/age-plugin-tagpq`, `cmd/age-plugin-batchpass` | F. Valsorda | v1.3.0 2025-12-27; v1.3.2 2026-08-29 | 2026-09-29; re-read 2026-10-06 | Yes |
| S5 | `str4d/rage @ main : age/CHANGELOG.md`; crate age 0.12.1 (`src/native/`) | str4d | 0.12.1 2026-07-14 | 2026-09-29; 2026-10-06 | Yes |
| S6 | rage #621 (PQ recipients; open per skeptic 1's page fetch; skeptic 3 could not verify) and #598 | GitHub | 2026-05-30; 2026-01-09 | 2026-10-06 | No |
| S7 | SLIP-0039, `satoshilabs/slips @ master : slip-0039.md` | SatoshiLabs | Final | 2026-09-29 | Yes |
| S8 | python-shamir-mnemonic 0.3.0 (`README.rst`, `cli.py`, `shamir.py`) | Trezor | 0.3.0, 2024-05-16 | 2026-09-29; 2026-10-06 | Yes |
| S9 | age-plugin-yubikey README and crate 0.5.1 (`builder.rs`, `format.rs`) | str4d | 0.5.1, 2026-04-08 | 2026-09-29 | Yes |
| S10 | age-plugin-tpm README | Foxboron | v1.0.1 | 2026-09-29 | Yes |
| S11 | age-plugin-sss README, `SPEC.md`, v0.4.0 | olastor | v0.4.0 | 2026-09-29 | Yes |
| S12 | PaperAge README | M. Korhonen | main | 2026-09-29 | Yes |
| S13 | Proxmox VE `pve-docs @ master : qm.adoc` (TPM section) | Proxmox | master | 2026-09-29 | Yes |
| S14 | systemd-creds(1) man page source | systemd | main | 2026-09-29 | Yes |
| S15 | Clevis and Tang READMEs | latchset | master | 2026-09-29 | Yes |
| S16 | systemd #39049, #40159 | GitHub | 2025 | 2026-09-29 (bodies) | No |
| S17 | Ente Legacy docs, `ente-io/ente @ main` | Ente | main | 2026-09-29 | Yes |
| S18 | Bitwarden server `EmergencyAccess*.cs` | Bitwarden | main | 2026-09-29 | Yes |
| S19 | restic `doc/design.rst` | restic | master | 2026-09-29 | Yes |
| S20 | age #136 (closed; the close reason is reported differently by the skeptics) | GitHub | 2020-07-23 | 2026-10-06 | No |
| S22 | vsss-rs 6.0.1 README | M. Lodder | 6.0.1 | 2026-09-29 | Yes |
| S23 | SOPS v3.13.3 source | getsops | v3.13.3 | 2026-09-29 | Yes |
| S24 | NIST IR 8547 ipd. **Primary not read** (blocked). Secondary sources only | NIST | ipd 2024-11-12 | blocked | No |
| S25 | In-repo notes: `a1-content-identity.md`, `a2-object-envelope.md` (§F2, C9, C21, DR-A2-2), `a3-ingest-protocol.md` (DR-A3-3), `a6-homelab-storage-engine.md` (§F3), `d1-threat-model.md` (§6), `docs/security/threat-model.md` (SR-02, SR-23, SR-27, SR-29, AR-03, AR-07, AR-08), `f3-security-literature.md` (§2) | Reliquary | 2026-09-29 to 10-06 | 2026-10-06 | No (internal) |
| S26 | age-plugin-se README, `remko/age-plugin-se @ main` (`keygen --pq`) | R. Tronçon | main | 2026-10-06 | Yes |
| S27 | minisign README | F. Denis | master | 2026-09-29 | Yes |
| M1 | Analyst container checks (Go age v1.3.2, python-shamir-mnemonic 0.3.0) | this note | 2026-09-29 | — | Measurement |
| M2 | Synthesizer checks (Method): Go age v1.3.2, age-plugin-pq, Debian age 1.1.1, shamir-mnemonic 0.3.0, segno 1.6.6, zxing-cpp 3.1.1 | this note | 2026-10-06 | — | Measurement |
| M3 | Final synthesis reading of source (Method) | this note | 2026-10-06 | — | Source reading |
| D2-S1/S2/S3 | Spike evidence (see Spikes). These used **age v1.3.1**; M1 and M2 used v1.3.2 | spike runner | 2026-09-29, 2026-10-06 | — | Measurement |

## Claims

**How to read this table:**

- **Verdict** is the computed tally, used exactly:
  - **verified**: a primary source, and at least 2 of 3 skeptics did not refute;
  - **secondary-only**: no primary source;
  - **contested**: anything else.
- **Tally ID** maps to the skeptic batch. U = upheld (not refuted); R = refuted.
- The claim text is the original, followed by the correction that the skeptics' reasons require.
- **Contested claims are never the sole support of a recommendation.** Where one is used, the independent support is named.
- C22–C27 are new in synthesis. They were not tallied and appear only beside verified claims.

| # | Tally ID | Claim (with review correction) | Sources | Key? | S1 sources | S2 logic | S3 adversary | Verdict |
|---|---|---|---|---|---|---|---|---|
| C1 | K1 | Each stanza wraps the same file key independently, and identities MUST ignore unrecognised stanzas, so {ingest, recovery} is native. Nuance: a recipient type may refuse to be mixed (the basis of C2). Adversary caveat: this also means the ingest side never sees whether an R stanza is good. | S1; M1; D2-S2 | Yes | U | U | U | **Verified** |
| C2 | K2 | The same file SHOULD NOT be encrypted to PQ and non-PQ recipients, and Go age refuses (reproduced three times). **Correction (logic):** the constraint binds per header. Under P1 the stored header {X, R} must be homogeneous; the device header {I_e} stands alone. "PQ excludes all hardware" is too broad (see C11, C24). | S1, S2, S4; M1; D2-S2 | Yes | U | U | U | **Verified** |
| C3 | K3 | An scrypt stanza MUST be the only stanza, so a passphrase can only protect an identity file. | S1; D2-S2 | Yes | U | U | U | **Verified** |
| C4 | K4 | Header sizes: 1 PQ 1,627 B; 2 PQ 3,184 B; 1 X25519 168 B; 2 X25519 266 B. These were reproduced by all three lenses and are not in dispute. **The cost statement is wrong.** R's increment of 1,557 B is about 0.07 % at a 2.2 MB mean, not 0.15 %, which was the whole two-stanza header. The 0.9M–4.5M figure is F3's *photo* count, which F3 §2 does contain. The statement also left out records and h0. Use A2 §F2's per-mean-size table: stored {X, R} + h0 = 4,811 B per object, which is 0.22 % at the photo mean and 0.95 % at the document mean, plus about 2.7 KB for each unbatched metadata record. | M1; D2-S2; A2 §F2; F3 §2 | Yes (cost) | R | R | U | **Contested.** The sizes are used as measurements (also D2-S2, A2-S1). The percentage is not used |
| C5 | K5 | Rust age 0.12.1 has no native `mlkem768x25519`: verified as a narrow absence by all three lenses. **The consequences are refuted.** The encoder does not *have to* implement X-Wing (`age-plugin-pq` over the plugin protocol, C22, or Rust's native `tagpq`, C23), and heirs do not *strictly* need Go age ≥ 1.3.0 (C22). | S5, S6, S4 | Yes | R | R | R | **Contested.** Only the narrow absence is relied on, and only beside C22/C23 |
| C6 | K6 | The chain SLIP-39 → hex passphrase → scrypt-wrapped PQ identity → decrypting a two-recipient object works with unmodified upstream tools, and a wrong passphrase fails loudly. Agents only; no human yet. | M1; M2; D2-S2; S3, S7, S8 | Yes | U | U | U | **Verified** |
| C7 | K7 | A wrapped identity line is 260 B binary or **422 B armored**; the full key file wrapped is 2,266 B. PaperAge's ~1.9 KiB limit is on its own plaintext input, so the comparison is loose. Practical form: the armored identity line. | M1; M2; S12 | Yes | U | U | U | **Verified** |
| C8 | K8 | SLIP-39: ≥ 128 bits, a multiple of 16; 20 words at 128 bits and 33 at 256; extendable share sets; the SLIP-39 passphrase cannot be verified. Adversary note: every extendable set stays valid forever. | S7 | Yes | U | U | U | **Verified** |
| C9 | K9 | python-shamir-mnemonic is unhardened and "should not be used for handling sensitive secrets"; it recommends an air-gapped live system and prints the secret. **Scope:** this also applies to the heir's machine, to real-key checks and to re-issue. A tampered package could also emit a predictable W that passes its own self-tests. | S8 | Yes | U | U | U | **Verified** |
| C10 | K10 | Proxmox: an emulated vTPM "does *not* provide any real security benefits". Its state also travels in vzdump backups. | S13 | Yes | U | U | U | **Verified** |
| C11 | K11 | age-plugin-yubikey 0.5.1 writes classic `piv-p256` stanzas (PIN policy Once, touch policy Always, no agent): **upheld by all three lenses.** "No mlkem768p256tag identity exists" is **refuted**: age-plugin-se `--pq` is one (C24). So a YubiKey (PIV) cannot hold a PQ key, but PQ hardware custody is not ruled out in general. | S4, S9, S26 | Yes | R | R | R | **Contested.** The YubiKey exclusion also rests on D2-S1's independent reading of the crate (`builder.rs`, `format.rs`) plus C2 |
| C12 | K12 | Software unwrap in the container: thousands per second; the lowest rate measured is about 1,489/s (PQ second stanza). That is about 74× D2-S1's 20/s and about 16× the roughly 90/s that BUD-INGEST implies. Not homelab hardware. Rates assume benign headers (see C27). | M1; skeptic re-runs; D2-S2 | Yes (custody) | U | U | U | **Verified** |
| C13 | K13 | age-plugin-sss is experimental (v0.4.0) and has no Windows builds: upheld. **Corrected:** it writes **one** `sss` stanza that embeds n wrapped shares, not one stanza per share. The size outcome holds (6,548 B under PQ, measured). It supports password shares. | S11; D2-S2 | Yes | R | U | R | **Contested.** The rejection rests on D2-S2's measured 6,548 B header and on the maturity and Windows facts, which no lens disputed |
| C14 | K14 | The payload key and header MAC key derive from the file key, so a recipient change rewrites only the header. Go age has no public header writer (D2-S2 built one). Re-issued SLIP-39 cards do not revoke old cards. No rewrap revokes copies already made. **Scope (adversary):** "copies already made" includes the homelab's own snapshots, replicas, immutable holds, retained h0 and old sidecars. | S1, S4, S19, S20; D2-S2 | Yes | U | U | U | **Verified** |
| C16 | K15 | "Under A1 construction B, sealed S_e delivery costs no second file read, so it is compatible with instant enrollment except that the first upload waits." **Refuted by all three lenses:** every ID-needing upload waits; SR-14 admission is undesigned; local delivery (D1 §6) was ignored; a homelab-down case was not analysed. Only the "no second read" part follows by construction. | S25 (internal) | Yes | R | R | R | **Contested.** Not used as support anywhere |
| C17 | — | TPM-sealed secrets have failed to unseal after routine OS changes, so TPM auto-unlock needs a manual fallback. | S16 | No | — | — | — | Secondary-only (not tallied) |
| C18 | K17 | NIST IR 8547 ipd deprecation and disallow dates. Per secondary sources, 112-bit quantum-vulnerable algorithms are deprecated after 2030 and all are disallowed after 2035. The blanket wording was wrong. | S24 (secondary) | No | R | R | R | **Contested.** Not used |
| C19 | — | Ente Legacy: trusted contacts start recovery; the owner can block within 7, 14 or 30 days. | S17 | No | — | — | — | Not tallied (similar work) |
| C20 | — | systemd-creds `auto` skips TPM2 in containers; `host` keeps its key on the same disk. | S14 | No | — | — | — | Not tallied |
| C21 | K16 | "Devices must also write R, or late bundles become unreadable forever once I is destroyed." Refuted: escrowing I_e removes the premise, and device-written R cannot be verified. | S25, S1 | Was key | R | R | R | **Contested.** Withdrawn; §F2 replaces it |
| C22 | new | Go age v1.3.2 ships `age-plugin-pq`, which adds `mlkem768x25519` to "any version and implementation of age that supports plugins". M2: Debian age 1.1.1 plus the plugin decrypted a two-PQ object. | S4; M2 | Supporting | — | — | — | New; primary re-read |
| C23 | new | Rust age 0.12.0 added `age::tagpq::Recipient` (encryption only). | S5 | Supporting | — | — | — | New; primary re-read |
| C24 | new | age-plugin-se `--pq` makes non-exportable Secure Enclave keys of the tag (tagpq) type, and advises also encrypting to a backup key. | S26 | Supporting | — | — | — | New; primary re-read |
| C25 | new | M2: PQ R, shamir-drawn 128-bit W (20 words), 422 B armored wrap, QR v16-M round trip byte-identical; all 2-subsets recover; one share alone and a wrong secret are refused. | M2 | Supporting | — | — | — | New measurement |
| C26 | new | The age file key is 128 bits ("16 bytes of CSPRNG output"). | S1 | Context | — | — | — | Primary; not tallied |
| C27 | new | Go age v1.3.2 accepts headers up to 2 MiB and 1,024 stanzas, and calls the PQ/classic mixing check only via `Encrypt`/`WrapWithLabels`. A raw `Recipient.Wrap` bypasses it. | S4 (M3) | Supporting | — | — | — | New; primary source reading |

### Superseded statements (from the analysis summary; do not ratify)

| Superseded statement | Replaced by | Why |
|---|---|---|
| Devices write {I, R} (P2) | P1: devices write {I_e}; the homelab writes {X, R}; I_e escrowed | C21 contested; device R is unverifiable (A2 C9); 3,184 B fails A2-S1's local rule |
| One doomsday bundle "refreshed online because it needs only R's public key" | Offline bundle {X, A?} sealed only at the ceremony; online bundle without Tier-0 keys | Re-sealing needs the plaintext, so A and X would sit on an online machine (critical, logic and adversary lenses) |
| R stored as a 260 B wrapped file | 422 B armored (the QR and USB form) | C7 |
| "SR-23 forbids time delay" | v1 leaves it out by choice (AR-D2-2) | SR-23 concerns trust-forging *signing* keys only |
| "The encoder must implement X-Wing; heirs need Go age ≥ 1.3.0" | The encoder route is A2's choice; `age-plugin-pq` is the heir fallback | C5 contested; C22, C23 |
| "Under A′, I only guards transit" | True only if h0 is not kept in the clear beside a disk-resident I_e | §F4 |
| "R adds about 0.15 % of storage" | About 0.07 % per content object at the photo mean; the stored form costs 0.22–0.95 % | C4 contested |
| "No PQ hardware identity exists" | age-plugin-se `--pq` exists | C11 contested; C24 |
| "Compatible with instant enrollment except that the first upload waits" | Open question for D3/OD-05 | C16 contested |

## Findings

### F1. Key inventory (normative draft: `docs/security/key-inventory.md`)

| # | Key | Tier | Custody (summary) | Backup | Rotation | Compromise response |
|---|---|---|---|---|---|---|
| K-01 | Recovery identity R (`mlkem768x25519`) | 0 offline | In the clear only during a ceremony, an air-gapped real-key check or a recovery. Stored as a 422 B armored scrypt-wrapped identity file | W split SLIP-39 k-of-n. Wrapped file as a QR on every card and on the doomsday USB | Only on suspected exposure of ≥ k cards or of R | New R → A-signed bundle → store rewrap. Copies already made stay exposed (C14) |
| K-02 | Admin root signing key A (Ed25519) | 0 offline | Passphrase-protected file on two offline media held by the owner | Whether A is reachable through R is DR-D2-3; recommended: not | Rare; the new A is signed by the old A | Re-pin through kits (D3) |
| K-02b | Update-signing key(s) (D5) | **0** (ranked by D2; custody is D5's) | D5 | D5 | D5 | **As severe as A for future uploads:** a signed update can ship a client that pins another A or adds recipients. In-app pin rules cannot stop a malicious *signed* update. Joint response with D5/B7 |
| K-03 | Ingest identity I_e | 1 online | Software PQ identity in RAM (§F4); never on snapshotted, replicated or backed-up storage | **Escrowed when created:** sealed to {X, R} into the online bundle | New epoch through an A-signed bundle. Default: yearly and after suspected compromise (owner-tunable; no primary source) | Rotate now; the bundle revokes I_e (§F2). Treat staged and in-flight objects of that epoch as disclosed (AR-08) |
| K-03b | Archive identity X (A′) | 0/1 admin | Passphrase-wrapped file, optionally wrapped at rest by a YubiKey (classic is acceptable for an at-rest wrap) or a Mac Secure Enclave `--pq` key (C24) | Sealed to R in the offline bundle, plus a second offline copy | Rare; store rewrap with X online | Rotate and rewrap; the copies scope in C14 applies |
| K-04 | Receipt signing key (Ed25519) | 1 online | Ingest VM. A separate signer is a Wave 2 option under AR-08 | None (disposable) | Certified by A in the trust bundle | Rotate; listed as revoked in the next bundle |
| K-05 | Dedup epoch secrets S_e | 1 online | The homelab keeps every epoch; devices keep the current one in keystore-wrapped storage | Online bundle | DR-D2-1 | Rotate. The historical-ID oracle remains (AR-06) |
| K-06/07 | Volume and catalog keys (A6) | 1 | A6 | Online bundle (a D2 requirement) | A6 | A6 |
| K-08 | Homelab Cloudflare pull tokens | 1 | Ingest VM | Owner's password manager | Replace | Revoke |
| K-09 | Device Ed25519 signing key | 2 | Platform keystore | None: re-enroll | Re-enroll | Revoke (SR-17) |
| K-10 | Device sealing / restore key | 2 | Keystore-wrapped. **Recommended PQ.** Whether Android Keystore can hold ML-KEM is **not checked**; it is probably a software key wrapped by the Keystore | None | Re-enroll | Revoke |
| K-11..14 | Play upload key (B3), Worker secrets (C1/D3; never trust-forging, SR-23), DKIM (C3), invite pepper (D3) | project / cloud | Owners named | — | — | — |

**Two bundles, not one.**

- **Offline bundle** (age file to R): {X, plus A only if DR-D2-3 = full admin}. It is created and re-sealed **only** on the air-gapped ceremony machine.
- **Online bundle** (age file to {R, X}): {every S_e, every I_e (escrowed at creation), K-06, K-07}. The homelab refreshes it because it holds all of these online already. **It never contains Tier-0 material.**
- **Account recovery codes** (Cloudflare, registrar, Play) belong to E7's credential inventory. DR-D2-3 keeps them out of R-reachable bundles by default.

### F2. Hierarchy, trust bundle and where each stanza is written

```
offline                       homelab (online)                                      devices
R  (PQ; W split k-of-n) ──►   trust bundle {I_e, R, X?, K-04, epoch, not_after,
A  (Ed25519, 2 copies)          revoked[], alg ids} signed by A  ─────────────►   pin + monotonic epoch
X  (PQ, admin)                create I_e → seal to {X, R} → online bundle → copy off-box
                              ingest: device header {I_e} → stored header {X, R}    write {I_e} only (P1)
                              drain bound passed → delete every online copy of I_e
```

**Placement: P1 (devices write {I_e}; the homelab writes {X, R} at the rewrap).** This matches A2's DR-A2-2 recommendation. Reasons:

1. The homelab cannot check a device-written R stanza (A2 C9; C1's adversary caveat).
2. 1,627 B passes A2-S1's local ≤ 3 KB rule; 3,184 B fails it. The sizes are measured in D2-S2 and A2-S1. C4 is contested, but only for its percentage.
3. The P2 argument (C21) is contested and is not used.

**Escrow at creation, not at retirement.** The previous version of this note said "at creation" in §F1 and "at retirement" in §F2. This version settles on **at creation**:

- the online bundle, with the current I_e, is refreshed and copied off-box (to the doomsday USB; see §F8) at each epoch start;
- objects that exist only as staged ciphertext under I_e then stay readable by heirs with R, even if the homelab dies mid-epoch;
- this narrows the AR-07 staged-only window to "the bundle copy had not yet left the box";
- the cost is one file of about 3.3 KB per epoch (arithmetic: two PQ stanzas, the identity line and age overhead), instead of 1,557 B per object;
- the trade-off is AR-D2-1: k holders with access to R2 staging can read in-flight objects of the current epoch.

**Trust bundle requirements (adversary lens, major).** These are new requirements; D3 owns the encoding and D5 the update side.

1. A **monotonic epoch** that devices persist; they refuse any bundle with a lower epoch.
2. A **not_after** date. A device that holds only an expired bundle keeps encrypting under it, but shows "needs refresh" and fetches a new one. Whether it must stop uploading is D3's call, weighed against BUD-TTS.
3. A **revoked[]** list of compromised I_e and K-04 keys.
4. A freshly installed device must fetch and verify a current bundle **before its first upload**. A pin taken from an old onboarding stick (SR-27) authenticates, but does not prove freshness.
5. Devices name the I_e epoch in their signed manifest, so the homelab can quarantine objects sent to a revoked key.

**Production rewrap tool requirements** (from the adversary lens and M3; the spike tool does not meet them):

- **Drop** the I_e stanza. Do not append to it.
- Wrap with the **label-enforcing** path, or check labels explicitly, and refuse any classic stanza on a PQ header (C27).
- Write atomically, or as a new version.
- Check **X** decryption on every rewrapped header.
- R is checked only by the audit (§F6).
- Log counts only.

**Header-shape check before any unwrap (adversary lens, major).** Go age will trial-decapsulate up to 1,024 stanzas in a header of up to 2 MiB (C27). A hostile device, or a cloud injecting staged objects, could therefore make each object cost hundreds of PQ decapsulations. Before unwrapping, A2/A3 must enforce: exactly one stanza, of the chosen type, under about 1.7 KB, and nothing else. Anything else is rejected and alerted. C12's rates assume this check is in place. A G2/D4 fuzz case is needed.

**Posture coupling (OD-07):**

- Under A′, P1 is complete.
- Under posture A (keep received ciphertext), the homelab still rewraps to add R.
- Under plaintext postures, K-06 goes into the online bundle and the heir needs a volume runbook.

**Two-level alternative:** stored headers carry {X} only, and X is sealed to R.

| | {X, R} on stored headers (recommended) | {X} only; X sealed to R |
|---|---|---|
| Heir steps | `age -d -i R` on objects | Decrypt the bundle to get X, then `age -d -i X` |
| Replacing R | Store-wide header rewrap (1M PQ rewraps: 186 s CPU, D2-S2) | Re-seal one small file |
| Single point of failure | None beyond R | Every sealed copy of X |
| Stored header bytes | 3,184 B (+h0 per A6) | 1,627 B (+h0) |

R replacement should be rare, and the direct heir path survives losing the bundles, so the recommendation stays {X, R} (confidence medium). The two-level design is the fallback.

**Adding R later** needs I online and a custom tool, and cannot reach copies outside the store (C14, D2-S2). One-way door #3 holds.

### F3. PQ coupling

- With PQ, every stanza on the **stored** header is PQ, so R and X are PQ. The device header {I_e} is a separate header (C2 correction). OD-06 should still be decided as a whole.
- **Excluded as stored-object recipients under PQ:**
  - YubiKey PIV (`piv-p256`), per C11's YubiKey part (upheld by all three lenses; also D2-S1's crate reading);
  - age-plugin-tpm (classic);
  - scrypt (C3).
- **age-plugin-se `--pq`** (C24) is PQ hardware, but non-exportable and macOS-only. Possible uses: wrapping X's file at rest, or as an extra owner recipient at about +1.5 KB per object (not recommended for v1).
- **R must be `mlkem768x25519`,** so that heirs can use upstream tools. The only software tagpq identity found is test-internal Go code, and that absence was not tallied separately.
- **Encoder routes for I_e are A2's choice:**
  - (a) a native Rust X-Wing stanza, with CCTV vectors;
  - (b) the Rust plugin protocol with a bundled `age-plugin-pq` (C22): a subprocess per object, awkward on Android;
  - (c) Rust's native `tagpq` recipient (C23) with a custom homelab identity.
- **Heir kit:** Go age static binaries **pinned to one version** for both the ceremony and the kit (v1.3.2 recommended; the spikes used v1.3.1), plus `age-plugin-pq` as the fallback (C22).
- **If OD-06 = classic:** R and X may be X25519, YubiKeys become possible, and D2-S1 matters.

### F4. Custody of the online ingest key

| Option | Verdict |
|---|---|
| Plain file on the VM's normal disk | Not acceptable under A′ while h0 is kept in the clear |
| Passphrase-wrapped identity, manual unlock | Good if A6 also unlocks by hand. It stalls ingest after a power cut (BUD-TTS) |
| systemd-creds `host` | Weak (C20) |
| Proxmox vTPM | **Excluded** (C10) |
| Physical TPM (systemd-creds / clevis) | Acceptable with a tested manual fallback (C17, secondary-only) |
| clevis + Tang on another host, key loaded into **tmpfs** at boot | **Preferred** under A′ |
| YubiKey holding I | Impossible under PQ; not recommended under classic |
| HSM | Out of scope |

- **h0 plus I_e is a read key at rest.** "I only guards transit" holds only if h0 is sealed to X (or stored only as a MAC or digest), or if I_e never touches the store's disks. ADR-0008 makes this a requirement on A6.
- **Snapshots and replication:** I_e must not live on any snapshotted, ZFS-replicated or vzdump-covered volume. Deleting I_e must cover all of them.
- **Rates.** BUD-INGEST at ≥ 100 MB/s, at about 2.2 MB per object (F3's photo mean; video-heavy libraries differ) with one record each, implies about 90 unwraps/s. That is arithmetic. Software is about 16× above it on the container (C12), given the header-shape check (§F2).
- **Emergency rotation.** A new I_e needs an A-signed bundle, so it needs an owner session. One option: at each ceremony, A also signs a bundle for a **standby I_{e+1}** generated at the homelab. Limitation: the standby secret lives on the same homelab, so it helps only when I_e leaked by a path that did not also expose the homelab (for example a misplaced backup). An alternative is deterministic offline derivation of I_e from a sealed seed (adversary lens), which would need custom key derivation for ML-KEM and is not checked. Wave 2, with a rotation-latency budget from H1.
- No custody choice addresses a live compromise of the ingest VM (AR-08).

### F5. Dedup secret

- **Derivation:** S_e = 32 CSPRNG bytes per epoch, generated at the homelab; K_e = HKDF(S_e, "reliquary/v1/dedup-id-key") (A1). It is not derived from R or A: that would put an offline root online for every rotation and mix key purposes.
- **Backup:** the online bundle.
- **Delivery:** per enrollment path (D1 §6, SR-15), designed by D3. D1 lists a local in-app scan of the enrolled device's QR for phones, or sealed delivery after SR-14 admission.
  - If device keys reach the homelab through the Worker without SR-14 admission, a malicious cloud can substitute the key and capture S_e (D1 V-04/V-06).
  - **A clear S_e on a USB stick must be sealed, or deleted after first use.** The stick is also the ADR-0002 seeding transport and can be lost.
- **Enrollment latency: open.** Under construction B there is no second file read, but **every** upload that needs a dedup ID waits until S_e arrives. That wait is unbounded if the homelab or the admin is unavailable. C16 is contested and is not used. This goes to D3/OD-05, with E3 on wording.
- **Rotation trigger (DR-D2-1):**
  - rotate on every revocation for loss, theft, suspected compromise or estrangement;
  - not on an admin-wiped retirement;
  - not on a calendar, because rotation gives no forward secrecy for historical IDs (AR-06).

  This is conditional on DR-A1-1 = B and A1-S2. Otherwise fall back to (b), confirmed compromise only.
- **Device sealing key:** PQ recommended (K-10), because a sealed S_e crosses Cloudflare. Platform feasibility is open (D3, A2).

### F6. Recovery design, k-of-n, holders, drills

**Construction** (ADR-0008 Decision 3; the ceremony detail is in the runbook):

1. **R:** `age-keygen -pq`, stripped to the identity line (78 B).
2. **W:** 128 bits.
   - **Entropy:** W = first 16 bytes of SHA-256(OS CSPRNG 32 bytes ‖ dice rolls), computed by a short ceremony script that calls the python-shamir-mnemonic library and reads input from the terminal, never from argv. The CLI takes a custom secret only on the command line (M3).
   - The dice input is an adversary-lens fix: a tampered package or OS could otherwise emit a predictable W that passes its own self-tests (C9).
   - Cross-checking the shares with a second, independent SLIP-39 implementation before printing is recommended. **No second implementation has been checked yet** (Wave 2).
3. **Why 128 bits under PQ (re-argued, logic lens).** The earlier argument, "objects are only 128-bit anyway" (C26), confused breaking one object with breaking R, which opens everything. The argument rests on the absolute margin instead:
   - W is uniformly random 128 bits behind scrypt;
   - a classical search costs about 2^128 scrypt evaluations;
   - a generic quantum search (Grover) still needs on the order of 2^64 sequential evaluations of a memory-hard function.

   This is reasoning without a primary source, because the NIST sources are blocked. 256 bits would mean 33 words instead of 20, which costs BUD-RECOVERY directly. C26 remains context: no object is stronger than 128 bits whatever protects R.
4. **Wrap:** `age -a -p`, armored, 422 B (C7, C25).
5. **Cards** carry:
   - the 20 words and the group and member line;
   - a QR of the armored file;
   - R's fingerprint (format: D3);
   - a one-page instruction.

   The doomsday USB also holds the file. **R's fingerprint is also printed in the runbook and on the kit**, and the heir cross-checks it across at least two cards and the kit. That defeats a single substituted, self-consistent card (adversary lens). An A-signed card set is a Wave 2 option.
6. **No SLIP-39 passphrase** (C8).

**Heir path:**

- Use an offline machine.
- Boot a **recovery USB** with the pinned age and shamir builds (recommended), so the unhardened tool runs in a known, ephemeral environment (C9 scope).
- Write R only into RAM-backed storage.
- Calling this "stock tools" overstates it: the tools are upstream and unmodified, but a non-technical heir needs them packaged. D2-S3 must measure the chosen packaging against BUD-RECOVERY.

**Holders (OD-08; E7-S1 confirms):**

| Scheme | Holders (example) | Survives | Risk |
|---|---|---|---|
| **2-of-3 (default)** | Partner; an adult relative outside the household; a safe-deposit box or executor | Any one lost card; the owner's death | Any two holders, together with access to the ciphertext, can read everything (AR-D2-1) |
| 3-of-5 | As above, plus two | Two lost cards | More people, more drift |
| Two groups: owner 1-of-1 **or** family 2-of-3 (SLIP-39 group threshold 1) | Owner card in the safe; family as above | The owner recovers alone; family needs a quorum | The owner card alone opens everything. Harder to explain. Not run in any spike |

**Life events:**

- Holder lost, card retrieved: re-issue an extendable set.
- ≥ k cards possibly in hostile hands: new R and rewrap (C14 scope).
- **Any recovery outside an owner-run air-gapped check, while the owner is alive:** new R and rewrap. This includes a holder- or heir-initiated recovery, and any use of real cards on a networked machine.

**Drills and checks.** This resolves the logic lens's inconsistency.

- **Human drills always use throwaway keys** (D2-S3).
- **Annual holder check:** each holder confirms by phone or in person that they have their card and it is readable. No share is reconstructed and no card is sent anywhere.
- **Real-key check:** at Gate C, after any holder change, and at least every 3 years. The cadence is an owner-tunable default with no primary source; SP 800-57 is blocked.
  - **Exempt from the rotation rule:** it runs only on the owner-controlled air-gapped ceremony image, with the owner present, every step is logged without secrets, and the image is wiped afterwards. The exemption is justified because this is exactly the controlled environment the ceremony itself uses.
  - **Cost:** k holders bring their cards to the owner (time against BUD-SUPPORT; to be costed in Wave 2).
  - It includes an **R-stanza audit** of (1) a random sample of stored headers, (2) **every** I_e escrow and the online bundle, and (3) the offline bundle. Each is unwrapped with R and its MAC verified, and the pass rate is recorded.
  - Under P1, homelab-written R stanzas are as unverifiable between audits as device-written ones would be. That residual risk is covered by: G2 cross-implementation tests in CI; X verification at rewrap; and **a first real-key check within the first months after the first family ingest** (proposal), not years later.
  - A "verifiable R stanza" design (record the encapsulation randomness sealed to X, so X holders can recompute R stanzas) is custom cryptography and needs review. Wave 2 option.

### F7. Key ceremony

See `docs/security/key-ceremony-runbook.md` (Draft). Its main points:

- pinned tools, with hashes from two sources;
- an offline live OS;
- shell history off, and **no pty or script(1) capture of interactive prompts** (the D2-S2 run 1 harness leaked a test passphrase that way);
- W from the OS plus dice;
- every k-subset tested and the printed QR scanned back;
- both bundles sealed;
- I_e, K-04 and the standby key are generated at the homelab, and only their public keys enter the ceremony;
- a **grep-for-secret check** on every log before it leaves the machine;
- a ceremony log that holds no secrets.

### F8. Succession (E7 requirement from PLAN §E7)

- **Read without Reliquary:** met when stored headers carry R. The heir needs R, the disks and upstream age (C1, C6, C22), delivered on a recovery USB.
- **Dependency on surviving disks.** If the homelab is destroyed, the archive is lost to heirs too. That is AR-03 (no off-site copy, settled). D2 does not reopen it.
- **The doomsday USB** carries only key material sealed to R: the wrapped R and copies of both bundles. It is *not* a copy of the archive. Its online-bundle copy is only as fresh as its last refresh. Proposed refresh points: each epoch start, each S_e rotation, and the annual holder check. The owner should confirm that a keys-only USB stored away from home does not conflict with "off-site copy out of scope" (part of DR-D2-4).
- **What k holders can do (AR-D2-1, restated precisely).** k holders **plus access to stored or staged ciphertext** can:
  - with homelab disks or their backups: read the whole archive;
  - with R2 staging access: read in-flight objects under any escrowed I_e, including the current one;
  - with a full-admin bundle (DR-D2-3 (ii)): also sign trust bundles and take over accounts.

  The read-only bundle (DR-D2-3 (i)) removes the third.
- **Time-delayed, owner-blockable release (AR-D2-2).** SR-23 forbids only trust-forging *signing* keys in the Worker. Possible designs:
  - a cloud-held, heir-encrypted share released by a cancellable Durable Object alarm;
  - drand/tlock: not owner-blockable, depends on drand continuing, and uses classic pairing crypto; no source read;
  - professional escrow.

  Costs: heir keys kept for decades, Cloudflare billing surviving the owner, and complexity. **v1 leaves this out by choice.** The owner decides (DR-D2-2).
- **Compartmented recovery** (per-person R, so one person's heirs cannot read the others) is a missed alternative from the adversary lens. Under cross-user dedup, one object can belong to several people, so it would need several R stanzas per object, each about 1.5 KB under PQ. Not analysed further; Wave 2 if the owner wants it.

### Alternatives compared

| Option | Fit with settled requirements | Pros | Cons | Evidence |
|---|---|---|---|---|
| Single homelab key (ADR-0001 as written) | Fits | Simplest | Losing the key or the owner loses everything | PLAN D2, E7 |
| **P1: I_e on device headers; homelab rewrap to {X, R}; I_e escrowed at creation (recommended)** | Fits; R-22 affected (Conflicts) | Every stored R stanza is written at home and auditable; 1,627 B device header; heir path with upstream tools | Residual staged window until the bundle copy leaves the box; depends on A′ or a rewrap | C1, C2, C14 (verified); D2-S2 sizes; A2 C9 |
| P2: devices write {I_e, R} | Fits | Covers the staged window | Unverifiable stanzas; 3,184 B fails A2-S1 | C21 contested |
| P3: P2 plus disclosed encapsulation randomness | Fits | Verifiable R | Custom crypto | A2 |
| Two-level: stored {X}; X sealed to R | Fits | R rotation is a re-seal | Heir depends on a sealed copy of X | §F2 |
| I and R both X25519 | Fits | Small; YubiKeys possible | Harvest-now on keep-forever data | C2 |
| Mixed PQ and classic on one header | — | — | Spec SHOULD NOT; Go age refuses | C2 |
| **SLIP-39 over a 128-bit W wrapping R; armored QR on cards (recommended)** | — | Upstream tools; 20 words; checksummed; QR and USB paths | Unhardened tool (air gap, recovery USB); a scan step | C3, C6–C9 (verified); C25 |
| SLIP-39 of R's seed (33 words) | — | One artifact | Non-stock bech32 step | D2-S2 |
| Group SLIP-39 (owner 1-of-1 or family 2-of-3) | — | Owner self-recovery | Owner card is a single point of exposure | C8 |
| age-plugin-sss per object | — | Threshold inside age | Experimental; 6,548 B PQ header; no Windows builds | D2-S2; C13 contested |
| age-plugin-sss protecting only R's file (password shares) | — | No word cards | Experimental; plugin needed for decades | C13 contested |
| Extra YubiKeys as recipients | Only if OD-06 = classic | No transcription | Classic only | C11 (YubiKey part); D2-S1 |
| Secure Enclave `--pq` as an extra recipient | — | PQ hardware | Non-exportable; macOS only | C24 |
| Cloud-held, heir-encrypted share with a cancellable delay | Compatible with SR-23 in principle | Owner can block a release | Heir keys; billing; complexity | §F8 |
| Sealed 1-of-n paper emergency kit (executor, safe-deposit box) | — | Simple | A single envelope opens everything | E7 (PLAN) |

### Similar work and lessons

| Project | What they do | Borrow or avoid | Source |
|---|---|---|---|
| age-plugin-se | Hardware-bound keys; advises a backup key | I/X plus R is the same pattern | S26 |
| restic | A leaked master key cannot be rotated in place | State the limit honestly (C14) | S19 |
| SOPS | Shamir over key groups, per file | Avoid per-object thresholds | S23 |
| Ente Legacy, Bitwarden Emergency Access | Time-delayed trusted-contact release | Feasible later without trust-forging keys (§F8) | S17, S18 |
| Trezor SLIP-39 | Word shares | Test every k-subset before printing | S7 |
| Apple ADP/Legacy, 1Password Emergency Kit, Tarsnap, Signal SVR, Keybase, Dark Crystal, Banana Split, Horcrux | — | **Not read** (blocked or not checked) | open |

### Tools and libraries

| Name | Purpose | Licence | Maturity | Source |
|---|---|---|---|---|
| Go `filippo.io/age` (+ `age-plugin-pq`, `age-plugin-batchpass`) | Homelab, ceremony, heir tool | BSD-3-Clause (not re-checked) | v1.3.2, 2026-08-29 | S4 |
| Rust `age` | Client; `tagpq` encryption only | MIT/Apache-2.0 | 0.12.1 | S5 |
| python-shamir-mnemonic | SLIP-39 | MIT (not re-checked) | 0.3.0; unhardened | S8 |
| age-plugin-se | Secure Enclave, PQ via `--pq` | not checked | main | S26 |
| age-plugin-yubikey, age-plugin-tpm | Classic hardware wrap of files at rest | not checked | 0.5.1; v1.0.1 | S9, S10 |
| age-plugin-sss | Threshold | not checked | v0.4.0, experimental | S11 |
| clevis/tang, systemd-creds | Auto-unlock | not checked | mature | S14, S15 |
| segno, zxing-cpp | QR encode and decode (kit candidates) | not checked | 1.6.6; 3.1.1 | PyPI |

## Spikes

| Spike | Hypothesis | Pass → / fail → (decision) | Exec tag | Budget IDs | Data class | Status | Result |
|---|---|---|---|---|---|---|---|
| D2-S1 YubiKey unwrap throughput | A YubiKey 5 identity with touch policy `never` does ≥ 20 unwraps/s unattended; plugin overhead is small next to 50 ms | Pass → a YubiKey may hold I under classic; fail → hardware only offline. **Not applicable if OD-06 = PQ.** Threshold flagged to H1 (about 90/s from BUD-INGEST) | CT/OL | BUD-INGEST | `SYN → results` | **Emulated, not a real YubiKey**; OL kit ready | Run 2026-10-06 (4 vCPU, age v1.3.1, software stand-in plugin, N = 2,000, 3 runs). Medians: native X25519 7,413/s; batched plugin session 4,356/s; stock plugin client, one process per object, 388/s; age CLI per object 146.4/s. By arithmetic that leaves about 43–50 ms for the device at 20/s, but only about 8–11 ms at 90/s. No source for YubiKey ECDH latency was found. Defaults: touch Always; "cached" reuses a touch for 15 s. **Pass: inconclusive.** Evidence: [`spikes/D2-S1/README.md`](../../spikes/D2-S1/README.md), `spikes/D2-S1/evidence/emulation-results.jsonl`. Kit: [`docs/research/kits/D2-S1/`](kits/D2-S1/README.md) (`run-yubikey.sh`) |
| D2-S2 Ingest + 2-of-3 split recovery; destroy the ingest key; recover; rewrap vs re-encrypt | Upstream tools recover after I is destroyed; adding a recipient later costs much less as a header rewrap, but needs I online and a custom tool | Pass → recovery construction for ADR-0008; rewrap cost recorded for door #3 | CT | BUD-RECOVERY (indirect), BUD-INGEST (context) | `SYN → results` | **Ran; pass** | 48/48 checks in both runs (2026-09-29 and 2026-10-06; age v1.3.1). Mixing refused; `-p` with `-r` refused. Variants A (classic, 128-bit, 20 words) and B (PQ, 256-bit, 33 words) recovered 10/10 SHA-identical photos from shares 1+3 after the ingest key was destroyed. Wrong secret rejected. Debian age 1.1.1: classic 10/10, PQ 0/10 without a plugin (M2: PQ works with `age-plugin-pq`). Headers: classic 168 → 266 B; PQ 1,627 → 3,184 B; sss PQ 6,548 B. Rewrap of 1M headers with 4 workers: classic 97.0 s, PQ 186.0 s (run 2). Sidecar rewrap of 500 × 1 MiB: 0.55 s, payload byte-identical. Re-encrypt pipe 324.4 MiB/s, about 1.6 h / 8.2 h CPU for 2 / 10 TB (arithmetic; disk I/O not measured). **Gaps:** the recommended PQ + 128-bit armored QR construction is covered only by M2 (C25); the rewrap tool keeps the I stanza and bypasses the label check (M3), so it is not a production design; run 1's pty leaked the test passphrase (now redacted, and the script is fixed). Evidence: [`spikes/D2-S2/README.md`](../../spikes/D2-S2/README.md), `spikes/D2-S2/evidence/run1-2026-09-29/`, `spikes/D2-S2/evidence/run2-2026-10-06/` |
| D2-S3 Combined recovery drill (the only one) | A non-author relative with only the kit recovers 10 named photos within BUD-RECOVERY, without owner help | Pass → recovery path "as drilled", Gate C item met; fail → fix the runbook or tooling (recovery USB, one command, 33-word direct shares) and re-run | FM | BUD-RECOVERY | `LAB → results`; drill keys `SEC`, throwaway | **Kit-ready; no human result** | Mechanical self-check 2026-10-06: 10/10 (classic, 128-bit) and 10/10 (PQ, 256-bit), about 1 s each (`dry-run-2026-10-06.txt`). **Amendments needed before the family session** (not made in this stage): (1) default to PQ + 128-bit, armored, with W from OS + dice; (2) a QR-scan step from the printed card; (3) the recovery-USB packaging and offline-machine instruction, timed; (4) a fingerprint cross-check across two cards; (5) pin a single age version (v1.3.2); (6) re-run the dry run. Kit: [`docs/research/kits/D2-S3/`](kits/D2-S3/README.md) |

## Conflicts with settled text

1. **R-22 / CLAUDE.md encryption trust model.** The settled text: "The owner (admin) holds the private key and can decrypt everything; privacy is against outsiders … not against the admin."
   - Under OD-08 option A, any k share holders, possibly outsiders such as an executor, can read every family member's archive, given access to the ciphertext.
   - **This widens who can decrypt.** It is raised as an explicit decision to amend the settled wording (DR-D2-4, with OD-08), not just as an accepted-risk entry.
   - D6 is cross-referenced for family consent. Not resolved here.
2. **ADR-0001 §2 / CLAUDE.md "encrypted on the device to the homelab public key."** Under P1, devices encrypt to one homelab key at a time (I_e), so the device side arguably fits. The homelab key becomes a rotating ingest key plus the homelab-written {X, R} stored form. The owner should confirm that this reading is acceptable under OD-07/OD-08. If not, ADR-0008 must explicitly amend ADR-0001 §2. The Accepted ADR is not edited.
3. **R-21 ("HMAC(family secret, content)").** The F5 rotation trigger depends on DR-A1-1 construction B, which rewords R-21. It is conditional.
4. **ADR-0002 §3 near-zero enrollment.** Every upload waits for S_e delivery. An admin-gated or homelab-dependent path conflicts with "adding devices never requires the admin". This goes to D3/OD-05.
5. **AR-03 ("off-site copy out of scope").** The doomsday USB stored away from home carries keys only, never archive data. The owner confirms this under DR-D2-4.

## Open questions

1. **Placement (DR-A2-2):** joint A2/A6/D2 sign-off on P1 plus escrow at creation. Owner: A2, A6, D2. When: Gate A.
2. **The h0 form at rest.** Owner: A6. When: Gate A.
3. **Ingest-key epoch interval and rotation latency** (default yearly; no primary source). Owner: A6/D2 with A3 and H1. When: Gate A.
4. **Encoder route for I_e**, plus CCTV vectors. Owner: A2/G2. When: Gate A.
5. **Header-shape rule before unwrap**, and a fuzz case. Owner: A2/A3, G2/D4. When: Gate A.
6. **Trust-bundle encoding** with epoch, not_after and revoked[], plus the fingerprint format. Owner: D3, with D5 for SR-29 consistency. When: Gate C (kit pin).
7. **D2-S3 human result** with the amended kit and recovery-USB packaging. Owner: D2 Wave 2 with E7. When: Gate C.
8. **Holders and k-of-n** (E7-S1). Owner: E7. When: before the production ceremony.
9. **A second SLIP-39 implementation for cross-checking**, and a hardened tool (a Trezor in custom-secret mode, or a reviewed Rust crate). Not checked. Owner: D2 Wave 2.
10. **PQ device sealing key on Android** (Keystore support for ML-KEM is not checked). Owner: D3/A2.
11. **Standby or derived ingest keys for emergency rotation.** Owner: D2 Wave 2.
12. **Time-delayed release design**, if wanted. Owner: D2/E7 Wave 2.
13. **Update-key custody** strong enough for Tier 0. Owner: D5 (ADR-0015).
14. **Blocked sources:** SP 800-57 cryptoperiods, NIST IR 8547, and the unread similar work. Owner: H1.

## Recommendation

Draft ADR-0008 (Proposed, partial). In-scope decisions for Wave 1:

1. **Placement (P1 plus escrow at creation).** Devices write {I_e} only. The homelab writes the stored header {X, R}. Every I_e is sealed to {X, R} into the online bundle when it is created, and the bundle is copied off-box at epoch start. All stanzas are `mlkem768x25519` if OD-06 = PQ; never mixed. **Support:** C1, C2, C14 (verified), D2-S2 measured sizes, A2 C9.
2. **R** is a PQ identity, stored as a 422 B armored scrypt-wrapped file. W is 128 bits from the OS plus dice, split with SLIP-39 (2-of-3 default, extendable, no SLIP-39 passphrase, 20 words). Each card carries a QR of the file and R's fingerprint, and the fingerprint is cross-checked against the kit. **Support:** C3, C6, C7, C8, C9 (verified); C25.
3. **A** is an offline Ed25519 key on two offline media. It signs the trust bundle {I_e, R, X?, K-04, epoch, not_after, revoked[], algorithm IDs}. Devices refuse rollback. By default A is not reachable from R (DR-D2-3).
4. **I_e** is software, held in RAM, never on a vTPM, and never on snapshotted or replicated storage. h0 is never kept in the clear alongside a disk-resident I_e. A strict header-shape check runs before any unwrap. **Support:** C10, C12 (verified).
5. **Two bundles:** offline {X (+A if chosen)}, sealed only at the ceremony; online {S_e, I_e, K-06, K-07}, sealed to {R, X}.
6. **Dedup secrets:** random per epoch, delivered per D3, rotated per DR-D2-1 (conditional).
7. **Drills:** human drills use throwaway keys. Real-key checks run only on the air-gapped image (exempt from the rotation rule) and audit sampled headers, every escrow file and both bundles. Any other real-card recovery while the owner is alive triggers a new R.
8. **Production rewrap tool:** drops I_e, enforces labels, writes atomically and verifies X.

**What would change this:**

- OD-06 = classic: X25519 R and X, YubiKeys possible, and D2-S1 matters.
- The owner prefers P2 for the staged window.
- OD-07 picks a plaintext posture: a volume runbook goes in the kit.
- D2-S3 fails at the SLIP-39 or QR step: one-command recovery USB, or 33-word direct shares.
- E7-S1 finds relatives will not hold cards: professional escrow, or group SLIP-39 with an owner card.
- The owner rejects widening R-22: no recovery recipient (and no succession path), or an escrow-only design.

## Decision requests

### OD-08: Recovery recipient, k-of-n and share holders (decide with OD-06 and DR-D2-4)

- **Needed by:** Gate A (one-way door #3), before the first real ingest.
- **Evidence:** §F2, §F3, §F6; D2-S2; C1, C2, C3, C6, C14 (verified); C25.

| Option | What it means for the family | Cost | Reversibility | Risks |
|---|---|---|---|---|
| **A. PQ R and X on every stored object (homelab-written); SLIP-39 2-of-3 over the passphrase wrapping R; QR on cards (recommended)** | Three people each keep a card; any two plus the kit and the disks recover everything | Half-day ceremony; stored {X, R} + h0 ≈ 4.8 KB per object (0.22 % at the photo mean, 0.95 % at the document mean, A2 §F2); one escrow file per epoch; a yearly holder check | One-way for existing objects; holders change by re-issue | AR-D2-1 |
| B. As A, but 3-of-5, or group SLIP-39 (owner 1-of-1 or family 2-of-3) | More people, or owner self-recovery | Same | Same | Coordination; the owner card is a single exposure point |
| C. No recovery recipient | The archive dies with the key or the owner | None now | A later rewrap cannot reach USB or staged copies | Permanent loss |
| D. Classic X25519 R, or YubiKeys | Hardware possible | Smaller headers | Same | Harvest-now on keep-forever data |

- **Recommendation:** A. Choose holders after E7-S1.
- **Touches settled text:** yes, R-22 (see DR-D2-4).
- **Default if no decision:** the run assumes A with 2-of-3, but no production ceremony runs, so Gate A cannot pass.

### DR-D2-4 (new; H1 to number): amend the settled trust-model wording (R-22) for share holders

- **Question:** CLAUDE.md says only the admin can decrypt everything. Should it be amended so that "any k recovery-share holders, with access to the ciphertext, can also decrypt everything"? Should a keys-only doomsday USB stored away from home be confirmed as not being an "off-site copy" (AR-03)?
- **Options:**
  - (a) amend the wording, with D6 family consent;
  - (b) keep the wording and choose OD-08 C (no succession path);
  - (c) professional escrow only.
- **Recommendation:** (a).
- **Needed by:** Gate A, together with OD-08.

### OD-06 coupling (A2 owns)

Decide OD-06 and OD-08 in the same sitting. PQ forces a PQ stored header (R and X); classic re-enables YubiKeys and D2-S1.

### DR-A2-2 (joint; A2 owns): where the recovery stanza is written

D2 recommends **P1 plus escrow at creation**. P2 remains an owner option for defence in depth; if chosen, the homelab-written {X, R} stays authoritative.

### DR-D2-1 (new; H1 to number): dedup-secret rotation trigger

- **Options:**
  - (a) every revocation for loss, theft, compromise or estrangement;
  - (b) confirmed compromise only;
  - (c) a calendar schedule.
- **Recommendation:** (a), conditional on DR-A1-1 = B and A1-S2. Otherwise (b).

### DR-D2-2 (new; to the OD-17 register): accepted risks

- **AR-D2-1:** any k holders, **plus access to stored or staged ciphertext**, can read the archive, including in-flight objects under the escrowed current I_e. With a full-admin bundle they can also forge trust.
- **AR-D2-2:** v1 has no time-delayed, owner-blockable release. This is a choice; SR-23 does not forbid one.
- **Options:**
  - accept both;
  - reject AR-D2-1: raise k, use group SLIP-39, or use professional escrow;
  - reject AR-D2-2: build a cancellable cloud-held share (Wave 2+).
- **Recommendation:** accept both for v1, with DR-D2-3 (i). AR-D2-1 is only acceptable if DR-D2-4 (a) is decided.

### DR-D2-3 (new; H1 to number): what the share holders' bundle unlocks

- **Options:**
  - (i) read-only: X, S_e, volume keys and I_e;
  - (ii) full admin: (i) plus A and the account recovery codes.
- **Recommendation:** (i). The account codes go to E7's inventory. Successors who want to keep the system running perform a re-key ceremony.

### OD-07 coupling (A6 owns)

h0 is never kept in the clear on the same disks as a disk-resident ingest key, and the stored header carries R in every posture that keeps ciphertext.

## Hand-offs

| To | What | Why |
|---|---|---|
| A2 (ADR-0007) | P1 plus escrow at creation (DR-A2-2). Encoder route. The header-shape rule before unwrap. A negative test that no mixed header is ever produced. **Correct A2 C21's "0.9M–4.5M is not in F3":** F3 §2 has it, as a photo count | §F2, §F3, M3 |
| A6 (ADR-0012) | The homelab writes {X, R}, also under posture A. The h0 form. I_e in tmpfs and off snapshots and replication. K-06/07 in the online bundle. Rewrap tool requirements | §F2, §F4 |
| A3 (ADR-0009) | The drain bound sets when online copies of I_e are deleted. The header-shape check at ingest. Quarantine of objects under a revoked I_e | §F2 |
| A1 (ADR-0006) | DR-D2-1 is conditional on construction B. C16 is contested and is not support for DR-A1-1 | §F5 |
| D3 (ADR-0014) | Trust bundle: epoch, not_after, revoked[], fresh fetch before the first upload. Fingerprint format. Per-path S_e delivery. A USB S_e sealed or deleted after first use. K-10 as PQ on Android | §F1, §F2, §F5 |
| D5 (ADR-0015) | The update key is ranked Tier 0 (as powerful as A). Consistent anti-rollback (SR-29) | §F1 |
| D1 | Amend AR-08 (h0 plus I_e at rest). AR-D2-1 restated. V-03 needs anti-rollback | §F2, §F4, §F8 |
| D6 (ADR-0027) | Share holders as decryptors: consent and charter (DR-D2-4) | Conflicts 1 |
| E7 (ADR-0040) | Holders (E7-S1). Account-code custody. Doomsday-USB refresh cadence and storage location. Social delay | §F6, §F8 |
| G2 (ADR-0035) | CCTV vectors. A cross-implementation round trip. A test for the R-stanza audit tool. A header-shape fuzz case | §F2, §F6 |
| C8 (ADR-0032) | Doomsday-USB refresh in the DR calendar | §F8 |
| D2 Wave 2 / spike runner | D2-S3 kit amendments (six items in Spikes) and a re-run of its dry run | Spikes |
| H1 | Blocked sources (SP 800-57 retried 2026-10-06: blocked). Restate D2-S1's threshold against BUD-INGEST. Number DR-D2-1..4. Reconcile the 2026-09-29 frame date with the 2026-10-06 evidence dates | Method, §F4 |
