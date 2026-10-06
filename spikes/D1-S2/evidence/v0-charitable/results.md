# V0-charitable runs (synthesis stage, 2026-10-06)

Patched copy of `../../model.py` (see `model_v0c.patch`). Python 3.11, cryptography in a venv, cloud container.

Variants: `V0c-charitable` = V0 + device green only when the Worker answers 'present' (committed), requery after timeout, reset_on_reject, reconcile_missing. `V0c-min` = V0 + green only on Worker 'committed' + requery. `V0c+per_upload_keys` = V0c-charitable with per-upload keys.

## one holder, budget 1

| Variant | Attacker | States | Violations |
|---|---|---|---|
| V0-ADR-0001-literal | none | 8 | S1 |
| V0-ADR-0001-literal | device | 25 | S1,SL,L1 |
| V0-ADR-0001-literal | leak | 29 | S1,SL,S3,L1 |
| V0-ADR-0001-literal | fault | 11 | S1,SL,L1 |
| V0-ADR-0001-literal | cloud | 80 | S1,SL,S3 |
| V0c-charitable | none | 57 | pass |
| V0c-charitable | device | 143 | pass |
| V0c-charitable | leak | 228 | S3 |
| V0c-charitable | fault | 123 | pass |
| V0c-charitable | cloud | 719 | S1,SL,S3 |
| V0c-min | none | 57 | pass |
| V0c-min | device | 143 | pass |
| V0c-min | leak | 255 | S3 |
| V0c-min | fault | 123 | pass |
| V0c-min | cloud | 753 | S1,SL,S3 |
| V0c+per_upload_keys | none | 95 | pass |
| V0c+per_upload_keys | device | 221 | pass |
| V0c+per_upload_keys | leak | 547 | S3 |
| V0c+per_upload_keys | fault | 221 | pass |
| V0c+per_upload_keys | cloud | 1275 | S1,SL,S3 |

## one holder, budget 2

| Variant | Attacker | States | Violations |
|---|---|---|---|
| V0-ADR-0001-literal | none | 8 | S1 |
| V0-ADR-0001-literal | device | 82 | S1,SL,S3,L1 |
| V0-ADR-0001-literal | leak | 53 | S1,SL,S3,L1 |
| V0-ADR-0001-literal | fault | 11 | S1,SL,L1 |
| V0-ADR-0001-literal | cloud | 370 | S1,SL,S3 |
| V0c-charitable | none | 57 | pass |
| V0c-charitable | device | 490 | S3 |
| V0c-charitable | leak | 441 | S3 |
| V0c-charitable | fault | 164 | pass |
| V0c-charitable | cloud | 3581 | S1,SL,S3 |
| V0c-min | none | 57 | pass |
| V0c-min | device | 564 | S3 |
| V0c-min | leak | 522 | S3 |
| V0c-min | fault | 164 | pass |
| V0c-min | cloud | 3856 | S1,SL,S3 |
| V0c+per_upload_keys | none | 95 | pass |
| V0c+per_upload_keys | device | 443 | pass |
| V0c+per_upload_keys | leak | 1535 | S3 |
| V0c+per_upload_keys | fault | 355 | pass |
| V0c+per_upload_keys | cloud | 7446 | S1,SL,S3 |

## one holder, budget 3

| Variant | Attacker | States | Violations |
|---|---|---|---|
| V0-ADR-0001-literal | none | 8 | S1 |
| V0-ADR-0001-literal | device | 146 | S1,SL,S3,L1 |
| V0-ADR-0001-literal | leak | 73 | S1,SL,S3,L1 |
| V0-ADR-0001-literal | fault | 11 | S1,SL,L1 |
| V0-ADR-0001-literal | cloud | 1142 | S1,SL,S3 |
| V0c-charitable | none | 57 | pass |
| V0c-charitable | device | 954 | S3 |
| V0c-charitable | leak | 621 | S3 |
| V0c-charitable | fault | 196 | pass |
| V0c-charitable | cloud | 11532 | S1,SL,S3 |
| V0c-min | none | 57 | pass |
| V0c-min | device | 1036 | S3 |
| V0c-min | leak | 756 | S3 |
| V0c-min | fault | 196 | pass |
| V0c-min | cloud | 12587 | S1,SL,S3 |
| V0c+per_upload_keys | none | 95 | pass |
| V0c+per_upload_keys | device | 695 | pass |
| V0c+per_upload_keys | leak | 2901 | S3 |
| V0c+per_upload_keys | fault | 489 | pass |
| V0c+per_upload_keys | cloud | 27988 | S1,SL,S3 |

## two holders, budget 1

| Variant | Attacker | States | Violations |
|---|---|---|---|
| V0-ADR-0001-literal | none | 61 | S1 |
| V0-ADR-0001-literal | device | 159 | S1,SL,L1 |
| V0-ADR-0001-literal | leak | 305 | S1,SL,S3,L1 |
| V0-ADR-0001-literal | fault | 100 | S1,SL,L1 |
| V0-ADR-0001-literal | cloud | 662 | S1,SL,S3 |
| V0c-charitable | none | 2649 | pass |
| V0c-charitable | device | 5935 | pass |
| V0c-charitable | leak | 15521 | S3 |
| V0c-charitable | fault | 5906 | pass |
| V0c-charitable | cloud | 44224 | S1,SL,S3 |
| V0c-min | none | 2649 | pass |
| V0c-min | device | 5935 | pass |
| V0c-min | leak | 16397 | S3 |
| V0c-min | fault | 5906 | pass |
| V0c-min | cloud | 45696 | S1,SL,S3 |
| V0c+per_upload_keys | none | 6117 | pass |
| V0c+per_upload_keys | device | 12687 | pass |
| V0c+per_upload_keys | leak | 58410 | S3 |
| V0c+per_upload_keys | fault | 17766 | pass |
| V0c+per_upload_keys | cloud | 109330 | S1,SL,S3 |

## Shortest counterexamples (one holder, budget 2)

- device / S3: M:claim IDF -> tick -> tick -> H1:query->upload -> M:PUT poison G as IDF at st/c50125 -> homelab:REJECT st/c50125 flag=('H1', 'rejected-upload') -> => honest device flagged [('H1', 'rejected-upload')]
- leak / S3: H1:query->upload -> LEAK:PUT G over st/c50125 -> homelab:REJECT st/c50125 flag=('H1', 'rejected-upload') -> => honest device flagged [('H1', 'rejected-upload')]
- cloud / S1: H1:query->present(cloud lie) -> => ['H1'] green but the homelab store lacks F
- cloud / SL: H1:query->present(cloud lie) -> => SILENT LOSS: ['H1'] green, store lacks F, and no honest continuation can ever store F
- cloud / S3: H1:query->upload -> CLOUD:inject G as c50125 -> homelab:REJECT st/c50125/CLOUD flag=('H1', 'rejected-upload') -> => honest device flagged [('H1', 'rejected-upload')]
