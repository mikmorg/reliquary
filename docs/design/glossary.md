# Glossary (v0, provisional)

- **Owner:** H4 (glossary and canonical data model). Other workstreams propose changes through H4 and do not redefine terms in their own documents.
- **Status:** **v0, provisional.** Wave 0 start, 2026-09-29. Nothing here is a decision. Where a meaning depends on an ADR that is not yet written, the "Fixed by" column names the ADR or workstream that will settle it.
- **Companion:** [data-model.md](data-model.md) (entities, fields, IDs, and what is plaintext where).
- **Inputs:** `CLAUDE.md`; ADR-0001; ADR-0002; `docs/research/PLAN.md` §2–§4; `client-stack.md` (T1); `fact-check-adr-0001-0002.md` (T2); `content-encryption-format.md` (a spike result that is not yet accepted, cited below as **CE spike**).
- **Kept current by:** H4-S1, the consistency review of every Wave 1–2 draft against this file. Gate A requires zero undefined terms in the Gate A ADRs.

## How to use it

1. Use the **bold term** exactly. Words in the "Avoid" column are ambiguous in this project; qualify them or use the preferred term.
2. Engineering words (claimed, staged, committed) are for specs. People never see them. The words people see come from E3 (ADR-0024), mapped from A3's state table; §8 lists placeholders only.
3. Need a term that is not here? Put it in your draft's open questions and tell H4. Do not coin a synonym.
4. "v0" means a meaning picked so work can start. It can change until the ADR in "Fixed by" is Accepted.

## 1. People, roles and accounts

| Term | Meaning (v0) | Avoid / not the same as | Fixed by |
|---|---|---|---|
| **Family** | The whole installation: one homelab, one cloud control plane, one dedup secret, and the people it protects. One per deployment. The sandbox is a separate family. | "tenant", "org" | H4 |
| **Person** | A human whose keepsakes are in the archive. Lives in the homelab catalog. A person may have **no account**: a deceased grandparent whose photos were imported, a young child, or the "unknown person" bucket for unattributed imports (A9). | "user" | H4; E7 (roles and states) |
| **Account** | The cloud-side identity of an enrolled person: name, email and a list of devices (ADR-0002 §2). Created by redeeming an invite. No password. At most one per person. | person | ADR-0002; D3; OD-03 may move email to the homelab |
| **Owner** | The specific human who runs Reliquary and holds the admin role. | | CLAUDE.md |
| **Admin** | The role that administers everything and controls the homelab private key, so it can decrypt everything. In v1 only the owner holds it; E7 may add a deputy. | "owner" when you mean the role | CLAUDE.md; E7 (ADR-0040) |
| **Helper** | A person who acts for another, e.g. receives an elderly relative's nudges or enrolls their devices. Proposed role; not yet in scope. | | E7, E3 |
| **Deputy / successor** | A person who can take over admin duties or recover the keys if the owner cannot. Proposed. | | E7, D2 |
| **Person status** | Proposed values: active, departed, deceased. Departed or deceased stops every nudge to or about the person. | | E7 |
| **Attribution** | Which person a sighting (and so an item) belongs to. By default, the person whose device made the sighting. For imports, set by the admin. Corrections are recorded, never overwritten. | "ownership" (a legal word) | H4, A9 |

## 2. Devices, enrollment and trust

| Term | Meaning (v0) | Avoid / not the same as | Fixed by |
|---|---|---|---|
| **Device** | One enrolled installation of the client, identified by its own keypairs and device ID. A reinstall, factory reset or new phone is a **new** device, linked to the one it replaces. | "machine"; client | D3 (ADR-0014) |
| **Client** | The Reliquary software on a device: background engine plus a light UI. | device | T1 (ADR-0003) |
| **Device encryption key** | Keypair made on the device at enrollment (X25519 in current drafts). The homelab re-encrypts restores to it (ADR-0001 §6). Cannot read backups. | "device key" alone | D3, D2 |
| **Device signing key** | Keypair made on the device at enrollment (Ed25519 in the CE spike). Signs metadata records and manifests, because age alone does not say who encrypted a file. | "device key" alone | D3, A2 |
| **Device credential** | What the device presents to the Worker to authenticate API calls. Form still open (bearer token, request signatures, mTLS and others). | device keys | D3 |
| **Enrollment** | Making a device part of the family: keys generated, device registered under an account, credential issued, trust bundle pinned. | "registration"; pairing (one route only) | D3, E5 |
| **Invite** | Admin-created, one-use, expiring right to create an account and enroll its first device (ADR-0002 §2). | | ADR-0002; D3, E5 |
| **Invite code** | The human-typable code on the printed card (≥ 50 bits, with a check character). The cloud stores only a keyed hash of it. A secret, not an ID. | "password", "token" | ADR-0002; E5 (format), D3 (storage) |
| **Enrollment token** | Short-lived, single-use token inside the "other devices" QR code shown by an enrolled device (ADR-0002 §3). | invite code | ADR-0002; D3 |
| **Pairing code** | Short-lived, single-use code typed on a new computer, shown by an enrolled device (ADR-0002 §3). | | ADR-0002; D3, E5 |
| **Kit** | The onboarding package: a USB stick with desktop builds, plus a separate printed invite card (ADR-0002 §1). | bundle | ADR-0002; E5 |
| **Revocation** | Admin action that stops a device using the API. Never deletes its backed-up data or its history. | "delete device" | D3 |
| **Trust anchor** | A key a device trusts without asking the cloud: the homelab recipient key(s) and the receipt-signing key. | | D3 |
| **Trust bundle** | The set of trust anchors a device holds. CE spike: `{recipient, receipt_key}`, pinned by its SHA-256 carried in the QR code or kit, never learned from the Worker. | | D3 (ADR-0014) |

## 3. Keepsakes and content

| Term | Meaning (v0) | Avoid / not the same as | Fixed by |
|---|---|---|---|
| **Keepsake** | People-facing word for anything worth protecting: photos, videos, documents, scans, records (CLAUDE.md). In specs, say **item**. | "file" | CLAUDE.md; E4 (taxonomy) |
| **Item** | What a person thinks of as one keepsake: one photo, one video, one scan, or one Live Photo (still plus video). Made of one or more resources. Derived at the homelab from resources and grouping hints; never an upload unit. | "file", "asset", "object" | A5 (ADR-0016) |
| **Asset group** | The record tying several resources into one item, with the grouping key that justified it (Live Photo content identifier, Motion Photo XMP, RAW+JPEG basename). A one-resource item needs no group. | "album" | A5 |
| **Resource** | One byte-exact component of an item, with a **role**: original, paired video, edit render, adjustment data, RAW, sidecar (A5's list). A resource's bytes are exactly one blob. | "file" (a PhotoKit resource is not a file) | A5 |
| **Blob** | One distinct plaintext byte sequence, stored once for the whole family however many devices hold it. Identified at the homelab by its content hash and in the cloud by its dedup ID. | object (an encrypted envelope of a blob) | A1, A6 |
| **Content hash** | SHA-256 of the plaintext (ADR-0001). Never leaves the device in plaintext; the homelab recomputes it to verify. A1 may choose BLAKE3; the role stays the same. | "hash" alone; dedup ID | A1 (ADR-0006) |
| **Dedup secret** (= **family secret**) | The family-wide secret used to compute dedup IDs. Every device holds it; the cloud never does. | | A1, D2 |
| **Dedup key** | CE spike proposal: a key derived from the dedup secret with HKDF and a version label, used instead of the raw secret (decision D-4 in that note). | dedup secret | A1 |
| **Dedup ID** | The opaque content identifier the cloud sees: an HMAC of the content under the dedup secret, with a version prefix. Same content gives the same ID for every person. Three constructions are in flight (§11). | content hash; "file ID" | A1 (ADR-0006, `docs/spec/identifiers.md`) |
| **Dedup epoch** | The version of the dedup secret a dedup ID was made with. Rotation starts a new epoch. | | A1, D2 |
| **Capture time** | When a photo or video was taken, from EXIF or QuickTime, with its timezone offset if known and a note of which field it came from. | mtime | A5 |
| **Grouping hint** | A value in a metadata record that lets the homelab group resources into an item (e.g. the Live Photo content identifier). | | A5 |
| **Transcoded copy** | A re-encoded version of a keepsake (HEIC→JPEG, messenger recompression). Different bytes, so a different blob; never deduplicated against the original. | "duplicate" | A5 |

## 4. Sources, locators and history

| Term | Meaning (v0) | Avoid / not the same as | Fixed by |
|---|---|---|---|
| **Source** | A place resources are enumerated from: a folder tree, Android MediaStore, iOS PhotoKit, an admin-import medium, a Takeout export. Pluggable. | "folder" (only one kind) | B5 (ADR-0020) |
| **Source plugin** | The code for one kind of source (`enumerate(since_token)` plus a reader). Its name and version are recorded on every sighting. | | B5 |
| **Source locator** | Where a resource lives inside its source: a path for files; a PhotoKit asset identifier plus modification date on iOS (ADR-0001 §3); a MediaStore ID or URI on Android. Stored as raw bytes plus a display form. Plaintext only on the device and at the homelab. | "path" (only one kind) | B5; ADR-0001 |
| **Platform file ID** | The OS's stable identity for a file (NTFS file ID, inode plus device, APFS file ID). Used to spot renames and moves without rehashing. | dedup ID | B5; A1 (cache-key contract) |
| **Snapshot** | The stat values captured when a resource was read and hashed (size, mtime, ctime, platform file ID). They describe exactly the version that was uploaded. | | B5, A2 |
| **Hash cache** | The client's table from (source locator, size, mtime, platform file ID) to content hash and dedup ID (ADR-0001 §3). A plaintext inventory of the device's files, so sensitive. | "index" | A1 (contract), B6 (schema) |
| **Sighting** | The fact that a device (or an admin import) saw a given blob at a given source locator, with its snapshot and first/last seen times. The basic unit of history. A dedup hit still creates a sighting. | upload | H4, A3 |
| **Tombstone** | The fact that a previously sighted resource is gone from its locator, with when it was noticed and why (deleted, moved, content changed, out of scope, source gone, permission lost). **Never** deletes the backed-up copy. | "deletion" | H4, A3 |
| **Scan checkpoint** | Proposed: a record that a device finished a complete pass over one source at time T. Lets the homelab work out "last seen" for every sighting without one record per file per scan. | | H4 → A3, B5 |
| **First seen / last seen** | The first and latest times a sighting was confirmed, kept in both device time and server time. | | H4 |
| **Provenance** | Where a sighting came from: device, source and locator; or admin import (medium, operator, date, attributed person). | | H4, A9 |
| **Admin import** | Homelab-side ingest of existing archives (NAS folders, old drives, SD cards, Takeout or iCloud exports) with the same IDs and catalog. Its sightings have **no device of origin**. | "seed" (seeding is wider) | A9 |
| **Import batch** | One admin-import run: medium, operator, date, default attributed person, tool version. | | A9, H4 |
| **Device of origin** | The device that made a sighting. Empty for admin imports. | | H4 |
| **Placeholder** | A file whose content lives in a cloud service, not on the device (OneDrive, iCloud Optimize Storage, macOS dataless files). Never silently downloaded; reported honestly. | | B5 |
| **Discovery** / **proposal** | The assistant's search for keepsakes, and its suggestion of what to protect. The person's accept or decline is kept on the device; a decline must leak nothing. | | E4 (ADR-0023) |

## 5. Objects, formats and transport

| Term | Meaning (v0) | Avoid / not the same as | Fixed by |
|---|---|---|---|
| **Content object** | The encrypted form of one blob as uploaded by one device. In the CE spike, a standard age v1 file for the homelab recipient key(s). Several content objects can carry the same blob; the homelab keeps the first verified copy. | blob; "R2 object" | A2 (ADR-0007) |
| **Metadata record** | Encrypted, device-signed record per (device, resource): content binding (dedup ID, content hash, size), source locator, name, snapshot and grouping hints (ADR-0001 §4; CE spike §9). Separate from the content object. It carries sightings and, as proposed here, tombstones and scan checkpoints. | "metadata" alone | A2 (format), A5 (fields), H4 (history fields) |
| **Record kind** | Proposed field, inside the encryption, that tells sighting, tombstone, scan-checkpoint, source and device-info records apart. | | H4 → A2, A3 |
| **Envelope** | The encryption format around content and metadata: algorithms, recipients, chunking, signatures. | | A2 |
| **Recipient** | A public key that can decrypt an object: the homelab ingest key today; a recovery key and possibly a post-quantum stanza are to be decided before Gate A. | | A2, D2 |
| **STREAM chunk** | The 64 KiB unit of age's STREAM encryption, each with its own authentication tag (CE spike). | dedup chunk | A2 |
| **Part** | One piece of an R2 multipart upload: 5 MiB–5 GiB, at most 10,000, all equal except the last (T2). | chunk | A2, C1 |
| **Part file** | One piece of a content object split for a size-limited medium such as a FAT32 stick (CE spike: split at part boundaries). | segment | A4 |
| **Dedup chunk** | Reserved for future content-defined chunking. Not used in v1. | STREAM chunk | A1 |
| **Upload** | One device's attempt to put one content object into staging. It has our **upload ID**, and for multipart R2's **multipart UploadId**, which is a different thing. | "sync" | A3, C1 |
| **Staging key** | The R2 key of one upload. CE spike: `staging/<dedup_id>/<upload_id>`, one per upload, never overwritten. | | C1 (ADR-0010, R2 key layout) |
| **Bundle** | A transport-agnostic set of content objects and metadata records plus a signed manifest. The same whether it travels by R2, USB or LAN. | kit | A4 (ADR-0011) |
| **Manifest** | Device-signed list of what a bundle holds: bundle ID, device ID, device sequence numbers, a hash link to the previous manifest, and objects with ciphertext digests and layout. Written last. | receipt; restore manifest | A4 |
| **Sealed** | A bundle whose manifest has been written and verified. Unsealed bundles are ignored at ingest. | | A4 |
| **Device sequence number** | A per-device counter on every signed record and manifest. A gap shows a missing upload; a repeat shows a cloned device or a restored client DB. | | A3, A4 |
| **Transport** | How a bundle travels: R2 staging (default), USB drive (required), LAN direct (optional, undecided). | | ADR-0001 §5; A4 |

## 6. Protocol states and events

| Term | Meaning (v0) | Avoid / not the same as | Fixed by |
|---|---|---|---|
| **Claim** / **claimed** | The Worker's conditional reservation of a dedup ID for one upload, with a TTL. ADR-0001 §4 calls this state `pending`. | "lock"; "pending" (§11) | A3 (ADR-0009) |
| **Staged** | The content object is fully in R2 staging (multipart completed) but not yet committed. | "sent" (a UI word) | A3 |
| **Verifying** | The homelab has pulled the object and is decrypting and checking it. | | A3 |
| **Commit** / **committed** | The homelab has decrypted and verified the object (size, content hash, dedup ID, signatures), durably stored the blob and written the catalog. Only then is a receipt signed and the staged object deleted. | "done", "uploaded" | A3; A6 (durable-commit contract) |
| **Durable commit** | A commit whose data is fsynced before it is acknowledged (A3's commit contract). | | A3, A6 |
| **Rejected** | Verification failed. Nothing is stored and the claim is reset. | | A3 |
| **Receipt** (**commit receipt**) | A homelab-signed statement that one device's metadata record and its blob are committed. CE spike fields: dedup ID, device ID, record digest, size, commit time, key ID, signature. Relayed by the Worker; checked by the device against its trust bundle. The only proof that something is stored at home. | "ack" or "confirmation" from the Worker | A3 (ADR-0009) |
| **Awaiting commit** | A device's record is at the homelab but its content is not committed yet (e.g. a dedup hit whose original upload is still in flight). No receipt yet. | "pending" (§11) | A3 |
| **Dedup hit** ("already have it") | The Worker reports a dedup ID as present. Grants no read rights and does not make this device's copy safe: the device still sends its metadata record and waits for its own receipt. | "duplicate means safe" | ADR-0001 §4; A3 |
| **Reconciliation** | The homelab listing pending state in D1/R2 to catch up, whatever notifications said. The primary path; queues and events only speed it up. | | ADR-0001 §1; A3 |
| **Cursor** | How far the homelab has reconciled. | | A3, C1 |
| **Ingest event** | The homelab's log entry for each ingest outcome: committed, duplicate dropped, rejected (with a code). | | A6, A7 |
| **Dedup poisoning** | A device uploading content that does not match the dedup ID it claims. Caught at the homelab. | | D4, A3 |
| **Claim squatting** | Taking claims on IDs without uploading, to block others. | | D4, A3 |
| **Dedup oracle** | Using the "which are missing?" check to learn whether the family already holds a known file. | | F3, A1 |

## 7. Places and stores

| Term | Meaning (v0) | Avoid / not the same as | Fixed by |
|---|---|---|---|
| **Cloud staging** | Cloudflare R2 + Workers + D1/Durable Objects (+ optional Queues). The only internet-facing part. Sees ciphertext and opaque IDs; holds data only briefly. | "the server", "cloud backup" | ADR-0001; C1 |
| **Worker** | The Cloudflare Worker API: authenticates devices, issues presigned URLs, holds claims, relays receipts. | | C1 |
| **Control plane** | The Worker plus its D1/DO state: dedup index, claims, devices, accounts, invites. | | C1 (ADR-0010) |
| **Staging prefix** | The R2 area for uploads awaiting commit. | | C1 |
| **Restore prefix** | The expiring R2 area (`restore/`) for restore objects. | | ADR-0001 §6; C1, A8 |
| **Warm cache** | Optional short retention of committed objects in R2 (e.g. the last 30 days per device). | | ADR-0001; no owner yet (traceability C-01 is an orphan; proposed lead C1 with C4) |
| **Homelab** | The owner's Proxmox server. Outbound connections only. The **system of record**. | "server" | CLAUDE.md |
| **Ingest service** | The homelab service that pulls, decrypts, verifies, stores, catalogs and signs receipts. Also ingests USB bundles (in a disposable VM, per D4). | | A6, A3 |
| **Store** | The homelab's permanent content storage. Engine still open (plain CAS vs restic, Kopia and others). | "the backup" | A6 (ADR-0012) |
| **Catalog** | The homelab's plaintext database of persons, devices, blobs, items, sightings, receipts, restores and fixity results. The most sensitive plaintext store. Must be rebuildable from the store plus the raw record archive. | "index" | A6 (ADR-0013) |
| **Raw record archive** | The homelab's permanent copy of every signed metadata record and manifest exactly as received, so the catalog can be rebuilt and re-read. | | A6, H4 |
| **At-rest posture** | Whether the store keeps the received ciphertext, plaintext on encrypted disks, or re-encrypts into another format. | | A6 (OD-07) |
| **Client DB** | The device's local database: hash cache, upload journal, receipts held, sequence counter. Not a system of record; it can be lost. | | B6 (ADR-0021) |

## 8. Status words (placeholders)

A3 owns the map from protocol state to user state; E3 owns the words. These placeholders come from PLAN E3 and are **not** final.

| Condition (engineering) | Placeholder word | Rule |
|---|---|---|
| Found by discovery, not yet sent | found, waiting (with a reason) | |
| Upload in progress | sending | |
| Staged in R2, no receipt | sent | Never reads as safe |
| In a sealed USB bundle, not yet ingested | on a USB stick, in transit | Never reads as safe |
| Receipt held and verified | stored at home | The only condition that may be called safe |
| Declined by the person | (nothing shown to others) | Leaks nothing |

| Term | Meaning (v0) | Fixed by |
|---|---|---|
| **Safe** / **protected** | People-facing only. The device holds a valid homelab-signed receipt for the item's resources. A Worker answer, a finished upload or a dedup hit never counts (PLAN §3; CE spike §10). | E3 (ADR-0024), A3 |
| **Stored at home** | Engineering phrase for "committed, and this device holds the receipt". | A3 |
| **Time to safe** | From a new photo existing to it being stored at home (BUD-TTS). | H1 budgets; A3 (where measured) |
| **Health** | Plain-language summary per person, device and category. | E3 |
| **Gap reason** | Why something is not safe, with a fix and who must act. | E3 |
| **Staleness** | A device not making progress against its expected activity. | E3 |
| **Nudge** | A proactive message (in-app, OS notification, email) about a problem someone can fix. | E3 (ADR-0025) |
| **Single-copy window** | After commit, the homelab may hold the only copy (no off-site copy yet). Why "safe to delete" is dangerous (OD-18). | E3, D1 (OD-17) |

## 9. Restore, integrity and retention

| Term | Meaning (v0) | Avoid / not the same as | Fixed by |
|---|---|---|---|
| **Restore job** | An admin-started request to return blobs to a target device or person. Admin only in v1. | | A8 (ADR-0028) |
| **Restore object** | A blob re-encrypted by the homelab to the target device's encryption key and placed in the restore prefix. | content object | A8 |
| **Restore manifest** | Homelab-signed list of the restore objects in one job, checked by the device before it writes anything. | manifest (a device-signed bundle manifest) | A8, A4 |
| **Fixity** | Evidence that stored bytes have not changed: checksums recomputed on a schedule. | | A7 (ADR-0029) |
| **Scrub** | A filesystem-level check (e.g. a ZFS scrub). | audit | C5 |
| **Audit** | An app-level re-verification of blobs against their content hash. | scrub | A7 |
| **Restore drill** | A scheduled test restore that proves the archive can be restored. | | A7 |
| **Retention** | Keep forever. Deleting on a device only creates a tombstone. | | CLAUDE.md |
| **Pruning** | Manual, admin-only removal of stored bytes. The catalog keeps the record that the blob existed and was pruned. | "delete", "cleanup" | A6, C8 |
| **Recovery recipient** | An offline key that can decrypt everything if the online key is lost. Must exist before the first real ingest. | | D2 (ADR-0008) |
| **Doomsday kit** | The printed runbook and key shares for break-glass recovery. | | D2, E7 |

## 10. Words to avoid or qualify

| Word | Problem | Say instead |
|---|---|---|
| backup | The archive, the act, or one copy? | the archive (the homelab store); upload; stored at home |
| file | Resources and items are not always files | resource, item; "file" only for a filesystem file |
| object | An R2 object, or a content object? | content object, metadata record, restore object, "R2 object" |
| hash | SHA-256 or HMAC? | content hash; dedup ID |
| pending | Two meanings in current inputs (§11) | claimed; awaiting commit |
| user | Person, account holder or admin? | person; account; admin |
| sync | Reliquary never mirrors or deletes | upload; back up |
| uploaded, done | Does not say whether it is committed | staged; committed; stored at home |
| safe | Only true with a receipt | stored at home (in specs) |
| chunk | STREAM chunk or dedup chunk? | STREAM chunk; dedup chunk |
| segment | Used loosely in PLAN A2/A4, never defined | part (R2); part file (USB). A4 may define it. |
| device key | Which key? | device encryption key; device signing key; device credential |
| upload ID | Ours or S3's? | upload ID; multipart UploadId |
| server | Worker or homelab? | Worker; homelab |

## 11. Known inconsistencies in current inputs

Recorded for the owning workstreams. H4 does not resolve them; the v0 wording above avoids depending on either side.

| # | Inconsistency | Where | v0 handling | Resolved by |
|---|---|---|---|---|
| 1 | Three dedup-ID constructions: HMAC-SHA256(family secret, content) (ADR-0001 §2); `v0:` + HMAC(K, SHA-256(content)) (PLAN A0); HMAC(HKDF(family secret, `reliquary/v1/dedup-key`), content) (CE spike §6) | ADR-0001, PLAN A0, CE spike | Say "dedup ID" without assuming the construction | A1 (ADR-0006) |
| 2 | "pending" means the claim state (ADR-0001 §4) and also a record whose content is not yet committed (CE spike §11) | ADR-0001, CE spike | "claimed" and "awaiting commit" | A3 |
| 3 | "segment" is used for resumable pieces aligned to parts (PLAN A2) and for USB transfer units (PLAN A4); the CE spike uses parts and part files instead | PLAN | "part" and "part file" | A2, A4 |
| 4 | ADR-0002 treats the account as the person's identity; A9 and E7 need persons who have no account | ADR-0002, PLAN A9/E7 | Person and account are separate entities | H4 → E7, A6 |
| 5 | ADR-0002 puts name, email and per-device activity times in the cloud in plaintext; PLAN D6 proposes homelab-only email (OD-03) and no plaintext device names in the cloud | ADR-0002, PLAN D6 | Data model marks these "cloud per ADR-0002 unless OD-03 changes it" | D6, owner (OD-03) |
| 6 | "Family secret" (CLAUDE.md) vs "family dedup secret" (ADR-0001) | CLAUDE.md, ADR-0001 | Same thing: **dedup secret** | none needed |
| 7 | "Protected" (CE spike), "safe" (PLAN §3) and "stored at home" (PLAN E3) name the same condition | CE spike, PLAN | "stored at home" in specs; E3 picks the people-facing word | E3 |
| 8 | The CE spike uses `device_id` as the signature `key_id`; D2/D3 may give keys their own IDs so a device can rotate keys | CE spike, PLAN D2/D3 | Data model keeps device ID and key ID separate | D3 |

## Change log

| Date | Change |
|---|---|
| 2026-09-29 | v0 created (H4, Wave 0 start). |
