# F1-S1 source checks (read from pinned commits, 2026-09-29)

Each row is a fact read directly from upstream source or docs at the stated commit. File paths are
relative to the repository root. "Probe" means it was also exercised by a script in `../scripts/`.
These rows back fit-matrix cells; they do not score them (the analyst does).

| # | Candidate | Repo @ commit | File:line | What it shows |
|---|---|---|---|---|
| S1 | Kopia server mode | kopia/kopia @ 87d15de | `internal/grpcapi/repository_server.proto:91-95` | `WriteContentRequest { prefix, bytes data, compression }`: the device sends content bytes, not ciphertext. |
| S2 | Kopia server mode | kopia/kopia @ 87d15de | `internal/server/grpc_session.go:283,296` | `handleWriteContentRequest` calls `dw.ContentManager().WriteContent(... req.GetData() ...)` on the server, so encryption happens on the server. Probe: the device config holds no repository password or key. |
| S3 | Kopia server mode | kopia/kopia @ 87d15de | `internal/grpcapi/repository_server.proto:53` | `bytes hmac_secret` is sent to clients (content-ID HMAC secret held by every device). |
| S4 | Ente museum | ente/ente @ 7a5993c | `server/pkg/controller/file.go:347,392,1121` | Upload object keys are `<userID>/<uuid.NewString()>`: random per upload, not content-addressed. |
| S5 | Ente museum | ente/ente @ 7a5993c | `server/cmd/museum/main.go:638,654,655,775` | Authenticated user routes `POST /files/trash`, `POST /trash/delete`, `POST /trash/empty`, `DELETE /collections/v3/:id`: a device credential can delete its own history. |
| S6 | Ente mobile | ente/ente @ 7a5993c | `mobile/apps/photos/lib/ui/settings/developer_settings_tap_area.dart:25` | `_tapCountThreshold = 7`: the self-host endpoint is set through a hidden 7-tap developer setting. |
| S7 | Ente mobile | ente/ente @ 7a5993c | `mobile/apps/photos/lib/core/network/endpoint_config.dart:11-13` | `defaultEndpoint = String.fromEnvironment("endpoint", ...)`: a custom build can bake in the endpoint at compile time (relevant to a fork's enrollment). |
| S8 | Immich | immich-app/immich @ 6cd746a | `server/src/schema/tables/asset.table.ts:34,39,90` | Unique indexes on `(ownerId, checksum)` and `(ownerId, libraryId, checksum)`; `checksum` is SHA-1. Dedup is per user. |
| S9 | Immich | immich-app/immich @ 6cd746a | `server/src/controllers/asset.controller.ts:80-90`; `server/src/dtos/asset.dto.ts:57` | `DELETE /assets` with permission `AssetDelete` and optional `force`: a device's user session can delete assets. |
| S10 | UrBackup internet mode | uroni/urbackup_backend @ a4eb72a | `urbackupserver/dllmain.cpp:889,909`; `urbackupclient/InternetClient.cpp:305` | The server starts `InternetService` listening on port 55415 by default; the client dials `server_port="55415"`. The server must accept inbound connections. |
| S11 | Syncthing untrusted | syncthing/syncthing @ b223f72 | `lib/protocol/encryption.go:562` | Folder key = `scrypt(password, folderID, 32768, 8, 1)`: a symmetric shared password. Every trusted device holding it can decrypt. |
| S12 | Duplicati | duplicati/duplicati @ 25734de | `Duplicati/Library/Encryption/GPGEncryption.cs:87,178` | GPG module default `--symmetric`; the help text names `--encrypt` as the alternative (public-key mode by option). Not run: no .NET runtime in the container. |
| S13 | Plakar | PlakarKorp/kloset @ 5e81a8d (plakar v1.1.7 pins kloset v1.1.6) | `encryption/symmetric.go:22`; `encryption/keypair/keypair.go` | Default KDF `ARGON2ID` over a passphrase, AES-GCM-SIV (symmetric). The only keypair is Ed25519, used to sign snapshots (`snapshot/verify.go:33`), not to encrypt. |
| S14 | Plakar | plakar v1.1.7 `plakar help server` | man page | `plakar server` has delete **disabled by default** (`-allow-delete` to enable); it listens (default localhost:9876). Probe: logical delete still works (see probe_plakar.txt). |
| S15 | R2 (for restic/Kopia straight to R2) | cloudflare/cloudflare-docs @ production, fetched 2026-09-29 | `src/content/docs/r2/api/s3/api.mdx:58,92,116,139` | `x-amz-bucket-object-lock-enabled`, `GetObjectLockConfiguration`, `PutObjectLockConfiguration` and the `x-amz-object-lock-*` headers on PutObject are marked unsupported (❌). |
| S16 | R2 | cloudflare/cloudflare-docs @ production, fetched 2026-09-29 | `src/content/docs/r2/buckets/bucket-locks.mdx` (intro) | R2 bucket locks are retention rules per prefix, set through the dashboard, Wrangler or the API. They prevent deletion and overwrite "for a specified period, or indefinitely". They are configured out of band, not through S3 object-lock headers. |

Primary URLs (raw):
- https://raw.githubusercontent.com/cloudflare/cloudflare-docs/production/src/content/docs/r2/api/s3/api.mdx
- https://raw.githubusercontent.com/cloudflare/cloudflare-docs/production/src/content/docs/r2/buckets/bucket-locks.mdx
- Git sources were cloned from `https://github.com/<owner>/<repo>.git` at the commits above (see `../fetch_sources.sh`).
