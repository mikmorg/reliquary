AWS SDK for JavaScript v3 (`@aws-sdk/client-s3` 3.1142.0), `forcePathStyle: true`, `maxAttempts: 1`, 20 s timeout per check. Timings are single runs on a shared, heavily loaded 4-vCPU container: indicative only, not measurements of any budget.

| ID | Check | miniflare | rustfs | versitygw | seaweedfs | garage |
|---|---|---|---|---|---|---|
| S1 | PutObject 4 KiB Buffer, SDK defaults | ok, 236 ms | ok, 160 ms | ok, 224 ms | ok, 288 ms | ok, 108 ms |
| S2 | PutObject 6 MiB Buffer, SDK defaults (includes the SDK expect-continue middleware) | ok, 6318 ms | ok, 360 ms | ok, 1299 ms | ok, 242 ms | ok, 194 ms |
| S3 | PutObject stream body with ContentLength, SDK default checksum setting (wire encoding not captured) | FAIL http 500: Error: @aws-sdk XML parse error: unexpected content (server log: TypeError 'Provided readable stream must have a known length'), 58 ms | ok, 39 ms | ok, 32 ms | ok, 21 ms | ok, 22 ms |
| S4 | Same as S3 with requestChecksumCalculation WHEN_REQUIRED | ok, 135 ms | ok, 24 ms | ok, 69 ms | ok, 21 ms | ok, 16 ms |
| S5 | Same as S2 with the expect-continue middleware removed | ok, 452 ms | ok, 415 ms | ok, 196 ms | ok, 137 ms | ok, 190 ms |
| S6 | getSignedUrl PutObject + UploadPart (path-prefixed endpoint), fetch() upload, SDK Complete | ok, 716 ms | ok, 413 ms | ok, 675 ms | ok, 276 ms | ok, 277 ms |
| S7 | PutObject IfNoneMatch '*' via SDK on existing key | 412 PreconditionFailed, 148 ms | 412 PreconditionFailed, 11 ms | 412 PreconditionFailed, 95 ms | 412 PreconditionFailed, 18 ms | 200, 14 ms |

S7 on garage: 200 means the If-None-Match header was ignored and the object was overwritten.
