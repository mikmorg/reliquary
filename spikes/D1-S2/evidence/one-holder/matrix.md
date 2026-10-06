| Variant | none | device (b=1) | device (b=2) | device (b=3) | leak (b=1) | leak (b=2) | leak (b=3) | fault (b=1) | fault (b=2) | fault (b=3) | cloud (b=1) | cloud (b=2) | cloud (b=3) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| V0-ADR-0001-literal | S1 (8) | S1,SL,L1 (25) | S1,SL,S3,L1 (82) | S1,SL,S3,L1 (146) | S1,SL,S3,L1 (29) | S1,SL,S3,L1 (53) | S1,SL,S3,L1 (73) | S1,SL,L1 (11) | S1,SL,L1 (11) | S1,SL,L1 (11) | S1,SL,S3 (80) | S1,SL,S3 (370) | S1,SL,S3 (1,142) |
| V1-proposed | pass (167) | pass (368) | pass (740) | pass (1,142) | pass (948) | pass (2,596) | pass (4,787) | pass (352) | pass (542) | pass (732) | pass (1,024) | pass (5,106) | pass (15,828) |
| V1+create_only | pass (172) | pass (377) | pass (757) | pass (1,167) | pass (652) | pass (1,340) | pass (2,084) | pass (377) | pass (602) | pass (832) | pass (1,114) | pass (5,670) | pass (17,880) |
| V1-no-per_upload_keys | pass (80) | pass (192) | pass (477) | pass (775) | pass (324) | pass (634) | pass (898) | pass (163) | pass (230) | pass (292) | pass (528) | pass (2,208) | pass (5,784) |
| V1-no-receipts | S1 (7) | S1 (23) | S1 (47) | S1 (79) | S1,SL,L1 (20) | S1,SL,L1 (31) | S1,SL,L1 (39) | S1,SL,L1 (9) | S1,SL,L1 (9) | S1,SL,L1 (9) | S1,SL (60) | S1,SL (199) | S1,SL (444) |
| V1-no-pinned_trust | pass (167) | pass (368) | pass (740) | pass (1,142) | pass (948) | pass (2,596) | pass (4,787) | pass (352) | pass (542) | pass (732) | S1,SL (3,643) | S1,SL (29,141) | S1,SL (118,045) |
| V1-no-ttl | pass (16) | L1 (18) | L1 (37) | L1 (39) | pass (104) | pass (386) | pass (1,050) | pass (42) | pass (76) | pass (110) | pass (114) | pass (544) | pass (1,664) |
| V1-no-staged_state | pass (179) | pass (389) | pass (779) | pass (1,199) | pass (1,016) | pass (2,788) | pass (5,155) | pass (392) | pass (614) | pass (836) | pass (1,160) | pass (5,826) | pass (18,176) |
| V1-no-reset_on_reject | pass (167) | pass (368) | pass (770) | pass (1,172) | pass (959) | pass (2,641) | pass (4,892) | pass (352) | pass (542) | pass (732) | pass (1,036) | pass (5,178) | pass (16,024) |
| V1-no-requery | pass (8) | L1 (25) | L1 (51) | L1 (85) | L1 (24) | L1 (38) | L1 (48) | L1 (10) | L1 (10) | L1 (10) | pass (61) | pass (205) | pass (462) |
| V1-no-attribution | pass (167) | pass (368) | pass (740) | pass (1,142) | S3 (948) | S3 (2,596) | S3 (4,787) | pass (352) | pass (542) | pass (732) | S3 (1,116) | S3 (6,147) | S3 (21,097) |
| V1-no-homelab_verify | pass (167) | pass (368) | S1,SL,S2,L1 (902) | S1,SL,S2,L1 (1,436) | S1,SL,S2,L1 (1,048) | S1,SL,S2,L1 (3,176) | S1,SL,S2,L1 (6,377) | pass (352) | pass (542) | pass (732) | S2 (1,029) | S1,SL,S2 (5,339) | S1,SL,S2 (17,597) |
| V1-no-registry_auth | pass (167) | pass (368) | pass (740) | pass (1,142) | pass (948) | pass (2,596) | pass (4,787) | pass (352) | pass (542) | pass (732) | pass (1,176) | pass (7,013) | pass (26,740) |
| V1-no-reconcile_missing | pass (167) | pass (368) | pass (740) | pass (1,142) | pass (948) | pass (2,596) | pass (4,787) | L1 (352) | L1 (542) | L1 (732) | pass (1,024) | pass (5,106) | pass (15,828) |
| V1-no-per_upload_keys+create_only | pass (82) | pass (190) | pass (367) | pass (566) | pass (240) | pass (392) | pass (544) | pass (172) | pass (249) | pass (321) | pass (558) | pass (2,396) | pass (6,430) |

## Counterexamples (shortest, BFS)

### V0-ADR-0001-literal / none (budget 0): S1

```
H1:query->upload
H1:PUT st/c50125+Complete
=> ['H1'] green but the homelab store lacks F
```

### V0-ADR-0001-literal / device (budget 1): S1

```
H1:query->upload
H1:PUT st/c50125+Complete
=> ['H1'] green but the homelab store lacks F
```

### V0-ADR-0001-literal / device (budget 1): SL

```
M:claim IDF
H1:query->pending
=> SILENT LOSS: ['H1'] green, store lacks F, and no honest continuation can ever store F
```

### V0-ADR-0001-literal / device (budget 1): L1

```
M:claim IDF
H1:query->pending
=> attacker stops here; honest actors can no longer reach all-green. devs=(('done', None, 0), ('noF', None, 0)) claims=[('c50125f4bd266252', 'claimed', 'M')] store=[]
```

### V0-ADR-0001-literal / leak (budget 1): S1

```
H1:query->upload
H1:PUT st/c50125+Complete
=> ['H1'] green but the homelab store lacks F
```

### V0-ADR-0001-literal / leak (budget 1): SL

```
H1:query->upload
H1:PUT st/c50125+Complete
LEAK:PUT G over st/c50125
=> SILENT LOSS: ['H1'] green, store lacks F, and no honest continuation can ever store F
```

### V0-ADR-0001-literal / leak (budget 1): S3

```
H1:query->upload
LEAK:PUT G over st/c50125
homelab:REJECT st/c50125 flag=('H1', 'rejected-upload')
=> honest device flagged [('H1', 'rejected-upload')]
```

### V0-ADR-0001-literal / leak (budget 1): L1

```
H1:query->upload
H1:PUT st/c50125+Complete
LEAK:PUT G over st/c50125
=> attacker stops here; honest actors can no longer reach all-green. devs=(('done', 'st/c50125', 1), ('noF', None, 0)) claims=[('c50125f4bd266252', 'claimed', 'H1')] store=[]
```

### V0-ADR-0001-literal / fault (budget 1): S1

```
H1:query->upload
H1:PUT st/c50125+Complete
=> ['H1'] green but the homelab store lacks F
```

### V0-ADR-0001-literal / fault (budget 1): SL

```
H1:query->upload
H1:PUT st/c50125+Complete
FAULT:staged object vanishes st/c50125
=> SILENT LOSS: ['H1'] green, store lacks F, and no honest continuation can ever store F
```

### V0-ADR-0001-literal / fault (budget 1): L1

```
H1:query->upload
H1:PUT st/c50125+Complete
FAULT:staged object vanishes st/c50125
=> attacker stops here; honest actors can no longer reach all-green. devs=(('done', 'st/c50125', 1), ('noF', None, 0)) claims=[('c50125f4bd266252', 'claimed', 'H1')] store=[]
```

### V0-ADR-0001-literal / cloud (budget 1): S1

```
H1:query->present(cloud lie)
=> ['H1'] green but the homelab store lacks F
```

### V0-ADR-0001-literal / cloud (budget 1): SL

```
H1:query->present(cloud lie)
=> SILENT LOSS: ['H1'] green, store lacks F, and no honest continuation can ever store F
```

### V0-ADR-0001-literal / cloud (budget 1): S3

```
H1:query->upload
CLOUD:inject G as c50125
homelab:REJECT st/c50125/CLOUD flag=('H1', 'rejected-upload')
=> honest device flagged [('H1', 'rejected-upload')]
```

### V1-no-receipts / none (budget 0): S1

```
H1:query->upload
H1:PUT st/c50125/H11+Complete
=> ['H1'] green but the homelab store lacks F
```

### V1-no-receipts / device (budget 1): S1

```
H1:query->upload
H1:PUT st/c50125/H11+Complete
=> ['H1'] green but the homelab store lacks F
```

### V1-no-receipts / leak (budget 1): S1

```
H1:query->upload
H1:PUT st/c50125/H11+Complete
=> ['H1'] green but the homelab store lacks F
```

### V1-no-receipts / leak (budget 1): SL

```
H1:query->upload
H1:PUT st/c50125/H11+Complete
LEAK:PUT G over st/c50125/H11
=> SILENT LOSS: ['H1'] green, store lacks F, and no honest continuation can ever store F
```

### V1-no-receipts / leak (budget 1): L1

```
H1:query->upload
H1:PUT st/c50125/H11+Complete
LEAK:PUT G over st/c50125/H11
=> attacker stops here; honest actors can no longer reach all-green. devs=(('done', 'st/c50125/H11', 1), ('noF', None, 0)) claims=[('c50125f4bd266252', 'staged', 'H1')] store=[]
```

### V1-no-receipts / fault (budget 1): S1

```
H1:query->upload
H1:PUT st/c50125/H11+Complete
=> ['H1'] green but the homelab store lacks F
```

### V1-no-receipts / fault (budget 1): SL

```
H1:query->upload
H1:PUT st/c50125/H11+Complete
FAULT:staged object vanishes st/c50125/H11
=> SILENT LOSS: ['H1'] green, store lacks F, and no honest continuation can ever store F
```

### V1-no-receipts / fault (budget 1): L1

```
H1:query->upload
H1:PUT st/c50125/H11+Complete
FAULT:staged object vanishes st/c50125/H11
=> attacker stops here; honest actors can no longer reach all-green. devs=(('done', 'st/c50125/H11', 1), ('noF', None, 0)) claims=[('c50125f4bd266252', 'staged', 'H1')] store=[]
```

### V1-no-receipts / cloud (budget 1): S1

```
H1:query->present(cloud lie)
=> ['H1'] green but the homelab store lacks F
```

### V1-no-receipts / cloud (budget 1): SL

```
H1:query->present(cloud lie)
=> SILENT LOSS: ['H1'] green, store lacks F, and no honest continuation can ever store F
```

### V1-no-pinned_trust / cloud (budget 1): S1

```
H1:query->upload
H1:PUT st/c50125/H11+Complete
CLOUD:relay receipt H1/c50125 signed CLOUD
H1:receipt verified -> GREEN
=> ['H1'] green but the homelab store lacks F
```

### V1-no-pinned_trust / cloud (budget 1): SL

```
H1:query->present(cloud lie)
CLOUD:relay receipt H1/c50125 signed CLOUD
H1:dedup-hit meta PUT
H1:receipt verified -> GREEN
=> SILENT LOSS: ['H1'] green, store lacks F, and no honest continuation can ever store F
```

### V1-no-ttl / device (budget 1): L1

```
M:claim IDF
=> attacker stops here; honest actors can no longer reach all-green. devs=(('idle', None, 0), ('noF', None, 0)) claims=[('c50125f4bd266252', 'claimed', 'M')] store=[]
```

### V1-no-requery / device (budget 1): L1

```
M:claim IDF
H1:query->pending
=> attacker stops here; honest actors can no longer reach all-green. devs=(('waiting', None, 0), ('noF', None, 0)) claims=[('c50125f4bd266252', 'claimed', 'M')] store=[]
```

### V1-no-requery / leak (budget 1): L1

```
H1:query->upload
H1:PUT st/c50125/H11+Complete
LEAK:PUT G over st/c50125/H11
=> attacker stops here; honest actors can no longer reach all-green. devs=(('awaiting', 'st/c50125/H11', 1), ('noF', None, 0)) claims=[('c50125f4bd266252', 'staged', 'H1')] store=[]
```

### V1-no-requery / fault (budget 1): L1

```
H1:query->upload
H1:PUT st/c50125/H11+Complete
FAULT:staged object vanishes st/c50125/H11
=> attacker stops here; honest actors can no longer reach all-green. devs=(('awaiting', 'st/c50125/H11', 1), ('noF', None, 0)) claims=[('c50125f4bd266252', 'staged', 'H1')] store=[]
```

### V1-no-attribution / leak (budget 1): S3

```
H1:query->upload
LEAK:PUT G over st/c50125/H11
homelab:REJECT st/c50125/H11 flag=('H1', 'rejected-upload')
=> honest device flagged [('H1', 'rejected-upload')]
```

### V1-no-attribution / cloud (budget 1): S3

```
H1:query->upload
CLOUD:inject G as c50125
homelab:REJECT st/c50125/CLOUD flag=('H1', 'rejected-upload')
=> honest device flagged [('H1', 'rejected-upload')]
```

### V1-no-homelab_verify / leak (budget 1): S2

```
H1:query->upload
H1:PUT st/c50125/H11+Complete
LEAK:PUT G over st/c50125/H11
homelab:commit st/c50125/H11 (signer H1)
=> store holds content under an ID it does not hash to
```

### V1-no-homelab_verify / leak (budget 1): S1

```
H1:query->upload
H1:PUT st/c50125/H11+Complete
LEAK:PUT G over st/c50125/H11
homelab:commit st/c50125/H11 (signer H1)
H1:receipt verified -> GREEN
=> ['H1'] green but the homelab store lacks F
```

### V1-no-homelab_verify / leak (budget 1): SL

```
H1:query->upload
H1:PUT st/c50125/H11+Complete
LEAK:PUT G over st/c50125/H11
homelab:commit st/c50125/H11 (signer H1)
H1:receipt verified -> GREEN
=> SILENT LOSS: ['H1'] green, store lacks F, and no honest continuation can ever store F
```

### V1-no-homelab_verify / leak (budget 1): L1

```
H1:query->upload
H1:PUT st/c50125/H11+Complete
LEAK:PUT G over st/c50125/H11
=> attacker stops here; honest actors can no longer reach all-green. devs=(('awaiting', 'st/c50125/H11', 1), ('noF', None, 0)) claims=[('c50125f4bd266252', 'staged', 'H1')] store=[]
```

### V1-no-homelab_verify / cloud (budget 1): S2

```
H1:query->upload
H1:PUT st/c50125/H11+Complete
CLOUD:swap content at st/c50125/H11
homelab:commit st/c50125/H11 (signer H1)
=> store holds content under an ID it does not hash to
```

### V1-no-reconcile_missing / fault (budget 1): L1

```
H1:query->upload
H1:PUT st/c50125/H11+Complete
FAULT:staged object vanishes st/c50125/H11
=> attacker stops here; honest actors can no longer reach all-green. devs=(('awaiting', 'st/c50125/H11', 1), ('noF', None, 0)) claims=[('c50125f4bd266252', 'staged', 'H1')] store=[]
```

### V0-ADR-0001-literal / none (budget 0): S1

```
H1:query->upload
H1:PUT st/c50125+Complete
=> ['H1'] green but the homelab store lacks F
```

### V0-ADR-0001-literal / device (budget 2): S1

```
H1:query->upload
H1:PUT st/c50125+Complete
=> ['H1'] green but the homelab store lacks F
```

### V0-ADR-0001-literal / device (budget 2): SL

```
M:claim IDF
H1:query->pending
=> SILENT LOSS: ['H1'] green, store lacks F, and no honest continuation can ever store F
```

### V0-ADR-0001-literal / device (budget 2): S3

```
M:claim IDF
tick
tick
H1:query->upload
M:PUT poison G as IDF at st/c50125
homelab:REJECT st/c50125 flag=('H1', 'rejected-upload')
=> honest device flagged [('H1', 'rejected-upload')]
```

### V0-ADR-0001-literal / device (budget 2): L1

```
M:claim IDF
H1:query->pending
=> attacker stops here; honest actors can no longer reach all-green. devs=(('done', None, 0), ('noF', None, 0)) claims=[('c50125f4bd266252', 'claimed', 'M')] store=[]
```

### V0-ADR-0001-literal / leak (budget 2): S1

```
H1:query->upload
H1:PUT st/c50125+Complete
=> ['H1'] green but the homelab store lacks F
```

### V0-ADR-0001-literal / leak (budget 2): SL

```
H1:query->upload
H1:PUT st/c50125+Complete
LEAK:PUT G over st/c50125
=> SILENT LOSS: ['H1'] green, store lacks F, and no honest continuation can ever store F
```

### V0-ADR-0001-literal / leak (budget 2): S3

```
H1:query->upload
LEAK:PUT G over st/c50125
homelab:REJECT st/c50125 flag=('H1', 'rejected-upload')
=> honest device flagged [('H1', 'rejected-upload')]
```

### V0-ADR-0001-literal / leak (budget 2): L1

```
H1:query->upload
H1:PUT st/c50125+Complete
LEAK:PUT G over st/c50125
=> attacker stops here; honest actors can no longer reach all-green. devs=(('done', 'st/c50125', 1), ('noF', None, 0)) claims=[('c50125f4bd266252', 'claimed', 'H1')] store=[]
```

### V0-ADR-0001-literal / fault (budget 2): S1

```
H1:query->upload
H1:PUT st/c50125+Complete
=> ['H1'] green but the homelab store lacks F
```

### V0-ADR-0001-literal / fault (budget 2): SL

```
H1:query->upload
H1:PUT st/c50125+Complete
FAULT:staged object vanishes st/c50125
=> SILENT LOSS: ['H1'] green, store lacks F, and no honest continuation can ever store F
```

### V0-ADR-0001-literal / fault (budget 2): L1

```
H1:query->upload
H1:PUT st/c50125+Complete
FAULT:staged object vanishes st/c50125
=> attacker stops here; honest actors can no longer reach all-green. devs=(('done', 'st/c50125', 1), ('noF', None, 0)) claims=[('c50125f4bd266252', 'claimed', 'H1')] store=[]
```

### V0-ADR-0001-literal / cloud (budget 2): S1

```
H1:query->present(cloud lie)
=> ['H1'] green but the homelab store lacks F
```

### V0-ADR-0001-literal / cloud (budget 2): SL

```
H1:query->present(cloud lie)
=> SILENT LOSS: ['H1'] green, store lacks F, and no honest continuation can ever store F
```

### V0-ADR-0001-literal / cloud (budget 2): S3

```
H1:query->upload
CLOUD:inject G as c50125
homelab:REJECT st/c50125/CLOUD flag=('H1', 'rejected-upload')
=> honest device flagged [('H1', 'rejected-upload')]
```

### V1-no-receipts / none (budget 0): S1

```
H1:query->upload
H1:PUT st/c50125/H11+Complete
=> ['H1'] green but the homelab store lacks F
```

### V1-no-receipts / device (budget 2): S1

```
H1:query->upload
H1:PUT st/c50125/H11+Complete
=> ['H1'] green but the homelab store lacks F
```

### V1-no-receipts / leak (budget 2): S1

```
H1:query->upload
H1:PUT st/c50125/H11+Complete
=> ['H1'] green but the homelab store lacks F
```

### V1-no-receipts / leak (budget 2): SL

```
H1:query->upload
H1:PUT st/c50125/H11+Complete
LEAK:PUT G over st/c50125/H11
=> SILENT LOSS: ['H1'] green, store lacks F, and no honest continuation can ever store F
```

### V1-no-receipts / leak (budget 2): L1

```
H1:query->upload
H1:PUT st/c50125/H11+Complete
LEAK:PUT G over st/c50125/H11
=> attacker stops here; honest actors can no longer reach all-green. devs=(('done', 'st/c50125/H11', 1), ('noF', None, 0)) claims=[('c50125f4bd266252', 'staged', 'H1')] store=[]
```

### V1-no-receipts / fault (budget 2): S1

```
H1:query->upload
H1:PUT st/c50125/H11+Complete
=> ['H1'] green but the homelab store lacks F
```

### V1-no-receipts / fault (budget 2): SL

```
H1:query->upload
H1:PUT st/c50125/H11+Complete
FAULT:staged object vanishes st/c50125/H11
=> SILENT LOSS: ['H1'] green, store lacks F, and no honest continuation can ever store F
```

### V1-no-receipts / fault (budget 2): L1

```
H1:query->upload
H1:PUT st/c50125/H11+Complete
FAULT:staged object vanishes st/c50125/H11
=> attacker stops here; honest actors can no longer reach all-green. devs=(('done', 'st/c50125/H11', 1), ('noF', None, 0)) claims=[('c50125f4bd266252', 'staged', 'H1')] store=[]
```

### V1-no-receipts / cloud (budget 2): S1

```
H1:query->present(cloud lie)
=> ['H1'] green but the homelab store lacks F
```

### V1-no-receipts / cloud (budget 2): SL

```
H1:query->present(cloud lie)
=> SILENT LOSS: ['H1'] green, store lacks F, and no honest continuation can ever store F
```

### V1-no-pinned_trust / cloud (budget 2): S1

```
H1:query->upload
H1:PUT st/c50125/H11+Complete
CLOUD:relay receipt H1/c50125 signed CLOUD
H1:receipt verified -> GREEN
=> ['H1'] green but the homelab store lacks F
```

### V1-no-pinned_trust / cloud (budget 2): SL

```
H1:query->present(cloud lie)
CLOUD:relay receipt H1/c50125 signed CLOUD
H1:dedup-hit meta PUT
H1:receipt verified -> GREEN
=> SILENT LOSS: ['H1'] green, store lacks F, and no honest continuation can ever store F
```

### V1-no-ttl / device (budget 2): L1

```
M:claim IDF
=> attacker stops here; honest actors can no longer reach all-green. devs=(('idle', None, 0), ('noF', None, 0)) claims=[('c50125f4bd266252', 'claimed', 'M')] store=[]
```

### V1-no-requery / device (budget 2): L1

```
M:claim IDF
H1:query->pending
=> attacker stops here; honest actors can no longer reach all-green. devs=(('waiting', None, 0), ('noF', None, 0)) claims=[('c50125f4bd266252', 'claimed', 'M')] store=[]
```

### V1-no-requery / leak (budget 2): L1

```
H1:query->upload
H1:PUT st/c50125/H11+Complete
LEAK:PUT G over st/c50125/H11
=> attacker stops here; honest actors can no longer reach all-green. devs=(('awaiting', 'st/c50125/H11', 1), ('noF', None, 0)) claims=[('c50125f4bd266252', 'staged', 'H1')] store=[]
```

### V1-no-requery / fault (budget 2): L1

```
H1:query->upload
H1:PUT st/c50125/H11+Complete
FAULT:staged object vanishes st/c50125/H11
=> attacker stops here; honest actors can no longer reach all-green. devs=(('awaiting', 'st/c50125/H11', 1), ('noF', None, 0)) claims=[('c50125f4bd266252', 'staged', 'H1')] store=[]
```

### V1-no-attribution / leak (budget 2): S3

```
H1:query->upload
LEAK:PUT G over st/c50125/H11
homelab:REJECT st/c50125/H11 flag=('H1', 'rejected-upload')
=> honest device flagged [('H1', 'rejected-upload')]
```

### V1-no-attribution / cloud (budget 2): S3

```
H1:query->upload
CLOUD:inject G as c50125
homelab:REJECT st/c50125/CLOUD flag=('H1', 'rejected-upload')
=> honest device flagged [('H1', 'rejected-upload')]
```

### V1-no-homelab_verify / device (budget 2): S2

```
M:claim IDF
M:PUT poison G as IDF at st/c50125/M1
homelab:commit st/c50125/M1 (signer M)
=> store holds content under an ID it does not hash to
```

### V1-no-homelab_verify / device (budget 2): S1

```
M:claim IDF
M:PUT poison G as IDF at st/c50125/M1
homelab:commit st/c50125/M1 (signer M)
H1:query->present
H1:dedup-hit meta PUT
homelab:dedup-hit receipt H1
H1:receipt verified -> GREEN
=> ['H1'] green but the homelab store lacks F
```

### V1-no-homelab_verify / device (budget 2): SL

```
M:claim IDF
M:PUT poison G as IDF at st/c50125/M1
homelab:commit st/c50125/M1 (signer M)
H1:query->present
H1:dedup-hit meta PUT
homelab:dedup-hit receipt H1
H1:receipt verified -> GREEN
=> SILENT LOSS: ['H1'] green, store lacks F, and no honest continuation can ever store F
```

### V1-no-homelab_verify / device (budget 2): L1

```
M:claim IDF
M:PUT poison G as IDF at st/c50125/M1
homelab:commit st/c50125/M1 (signer M)
=> attacker stops here; honest actors can no longer reach all-green. devs=(('idle', None, 0), ('noF', None, 0)) claims=[('c50125f4bd266252', 'committed', '-')] store=['c50125']
```

### V1-no-homelab_verify / leak (budget 2): S2

```
H1:query->upload
H1:PUT st/c50125/H11+Complete
LEAK:PUT G over st/c50125/H11
homelab:commit st/c50125/H11 (signer H1)
=> store holds content under an ID it does not hash to
```

### V1-no-homelab_verify / leak (budget 2): S1

```
H1:query->upload
H1:PUT st/c50125/H11+Complete
LEAK:PUT G over st/c50125/H11
homelab:commit st/c50125/H11 (signer H1)
H1:receipt verified -> GREEN
=> ['H1'] green but the homelab store lacks F
```

### V1-no-homelab_verify / leak (budget 2): SL

```
H1:query->upload
H1:PUT st/c50125/H11+Complete
LEAK:PUT G over st/c50125/H11
homelab:commit st/c50125/H11 (signer H1)
H1:receipt verified -> GREEN
=> SILENT LOSS: ['H1'] green, store lacks F, and no honest continuation can ever store F
```

### V1-no-homelab_verify / leak (budget 2): L1

```
H1:query->upload
H1:PUT st/c50125/H11+Complete
LEAK:PUT G over st/c50125/H11
=> attacker stops here; honest actors can no longer reach all-green. devs=(('awaiting', 'st/c50125/H11', 1), ('noF', None, 0)) claims=[('c50125f4bd266252', 'staged', 'H1')] store=[]
```

### V1-no-homelab_verify / cloud (budget 2): S2

```
H1:query->upload
H1:PUT st/c50125/H11+Complete
CLOUD:swap content at st/c50125/H11
homelab:commit st/c50125/H11 (signer H1)
=> store holds content under an ID it does not hash to
```

### V1-no-homelab_verify / cloud (budget 2): S1

```
H1:query->upload
H1:PUT st/c50125/H11+Complete
CLOUD:swap content at st/c50125/H11
homelab:commit st/c50125/H11 (signer H1)
CLOUD:relay receipt H1/c50125 signed HOMELAB
H1:receipt verified -> GREEN
=> ['H1'] green but the homelab store lacks F
```

### V1-no-homelab_verify / cloud (budget 2): SL

```
H1:query->upload
H1:PUT st/c50125/H11+Complete
CLOUD:swap content at st/c50125/H11
homelab:commit st/c50125/H11 (signer H1)
CLOUD:relay receipt H1/c50125 signed HOMELAB
H1:receipt verified -> GREEN
=> SILENT LOSS: ['H1'] green, store lacks F, and no honest continuation can ever store F
```

### V1-no-reconcile_missing / fault (budget 2): L1

```
H1:query->upload
H1:PUT st/c50125/H11+Complete
FAULT:staged object vanishes st/c50125/H11
=> attacker stops here; honest actors can no longer reach all-green. devs=(('awaiting', 'st/c50125/H11', 1), ('noF', None, 0)) claims=[('c50125f4bd266252', 'staged', 'H1')] store=[]
```

### V0-ADR-0001-literal / none (budget 0): S1

```
H1:query->upload
H1:PUT st/c50125+Complete
=> ['H1'] green but the homelab store lacks F
```

### V0-ADR-0001-literal / device (budget 3): S1

```
H1:query->upload
H1:PUT st/c50125+Complete
=> ['H1'] green but the homelab store lacks F
```

### V0-ADR-0001-literal / device (budget 3): SL

```
M:claim IDF
H1:query->pending
=> SILENT LOSS: ['H1'] green, store lacks F, and no honest continuation can ever store F
```

### V0-ADR-0001-literal / device (budget 3): S3

```
M:claim IDF
tick
tick
H1:query->upload
M:PUT poison G as IDF at st/c50125
homelab:REJECT st/c50125 flag=('H1', 'rejected-upload')
=> honest device flagged [('H1', 'rejected-upload')]
```

### V0-ADR-0001-literal / device (budget 3): L1

```
M:claim IDF
H1:query->pending
=> attacker stops here; honest actors can no longer reach all-green. devs=(('done', None, 0), ('noF', None, 0)) claims=[('c50125f4bd266252', 'claimed', 'M')] store=[]
```

### V0-ADR-0001-literal / leak (budget 3): S1

```
H1:query->upload
H1:PUT st/c50125+Complete
=> ['H1'] green but the homelab store lacks F
```

### V0-ADR-0001-literal / leak (budget 3): SL

```
H1:query->upload
H1:PUT st/c50125+Complete
LEAK:PUT G over st/c50125
=> SILENT LOSS: ['H1'] green, store lacks F, and no honest continuation can ever store F
```

### V0-ADR-0001-literal / leak (budget 3): S3

```
H1:query->upload
LEAK:PUT G over st/c50125
homelab:REJECT st/c50125 flag=('H1', 'rejected-upload')
=> honest device flagged [('H1', 'rejected-upload')]
```

### V0-ADR-0001-literal / leak (budget 3): L1

```
H1:query->upload
H1:PUT st/c50125+Complete
LEAK:PUT G over st/c50125
=> attacker stops here; honest actors can no longer reach all-green. devs=(('done', 'st/c50125', 1), ('noF', None, 0)) claims=[('c50125f4bd266252', 'claimed', 'H1')] store=[]
```

### V0-ADR-0001-literal / fault (budget 3): S1

```
H1:query->upload
H1:PUT st/c50125+Complete
=> ['H1'] green but the homelab store lacks F
```

### V0-ADR-0001-literal / fault (budget 3): SL

```
H1:query->upload
H1:PUT st/c50125+Complete
FAULT:staged object vanishes st/c50125
=> SILENT LOSS: ['H1'] green, store lacks F, and no honest continuation can ever store F
```

### V0-ADR-0001-literal / fault (budget 3): L1

```
H1:query->upload
H1:PUT st/c50125+Complete
FAULT:staged object vanishes st/c50125
=> attacker stops here; honest actors can no longer reach all-green. devs=(('done', 'st/c50125', 1), ('noF', None, 0)) claims=[('c50125f4bd266252', 'claimed', 'H1')] store=[]
```

### V0-ADR-0001-literal / cloud (budget 3): S1

```
H1:query->present(cloud lie)
=> ['H1'] green but the homelab store lacks F
```

### V0-ADR-0001-literal / cloud (budget 3): SL

```
H1:query->present(cloud lie)
=> SILENT LOSS: ['H1'] green, store lacks F, and no honest continuation can ever store F
```

### V0-ADR-0001-literal / cloud (budget 3): S3

```
H1:query->upload
CLOUD:inject G as c50125
homelab:REJECT st/c50125/CLOUD flag=('H1', 'rejected-upload')
=> honest device flagged [('H1', 'rejected-upload')]
```

### V1-no-receipts / none (budget 0): S1

```
H1:query->upload
H1:PUT st/c50125/H11+Complete
=> ['H1'] green but the homelab store lacks F
```

### V1-no-receipts / device (budget 3): S1

```
H1:query->upload
H1:PUT st/c50125/H11+Complete
=> ['H1'] green but the homelab store lacks F
```

### V1-no-receipts / leak (budget 3): S1

```
H1:query->upload
H1:PUT st/c50125/H11+Complete
=> ['H1'] green but the homelab store lacks F
```

### V1-no-receipts / leak (budget 3): SL

```
H1:query->upload
H1:PUT st/c50125/H11+Complete
LEAK:PUT G over st/c50125/H11
=> SILENT LOSS: ['H1'] green, store lacks F, and no honest continuation can ever store F
```

### V1-no-receipts / leak (budget 3): L1

```
H1:query->upload
H1:PUT st/c50125/H11+Complete
LEAK:PUT G over st/c50125/H11
=> attacker stops here; honest actors can no longer reach all-green. devs=(('done', 'st/c50125/H11', 1), ('noF', None, 0)) claims=[('c50125f4bd266252', 'staged', 'H1')] store=[]
```

### V1-no-receipts / fault (budget 3): S1

```
H1:query->upload
H1:PUT st/c50125/H11+Complete
=> ['H1'] green but the homelab store lacks F
```

### V1-no-receipts / fault (budget 3): SL

```
H1:query->upload
H1:PUT st/c50125/H11+Complete
FAULT:staged object vanishes st/c50125/H11
=> SILENT LOSS: ['H1'] green, store lacks F, and no honest continuation can ever store F
```

### V1-no-receipts / fault (budget 3): L1

```
H1:query->upload
H1:PUT st/c50125/H11+Complete
FAULT:staged object vanishes st/c50125/H11
=> attacker stops here; honest actors can no longer reach all-green. devs=(('done', 'st/c50125/H11', 1), ('noF', None, 0)) claims=[('c50125f4bd266252', 'staged', 'H1')] store=[]
```

### V1-no-receipts / cloud (budget 3): S1

```
H1:query->present(cloud lie)
=> ['H1'] green but the homelab store lacks F
```

### V1-no-receipts / cloud (budget 3): SL

```
H1:query->present(cloud lie)
=> SILENT LOSS: ['H1'] green, store lacks F, and no honest continuation can ever store F
```

### V1-no-pinned_trust / cloud (budget 3): S1

```
H1:query->upload
H1:PUT st/c50125/H11+Complete
CLOUD:relay receipt H1/c50125 signed CLOUD
H1:receipt verified -> GREEN
=> ['H1'] green but the homelab store lacks F
```

### V1-no-pinned_trust / cloud (budget 3): SL

```
H1:query->present(cloud lie)
CLOUD:relay receipt H1/c50125 signed CLOUD
H1:dedup-hit meta PUT
H1:receipt verified -> GREEN
=> SILENT LOSS: ['H1'] green, store lacks F, and no honest continuation can ever store F
```

### V1-no-ttl / device (budget 3): L1

```
M:claim IDF
=> attacker stops here; honest actors can no longer reach all-green. devs=(('idle', None, 0), ('noF', None, 0)) claims=[('c50125f4bd266252', 'claimed', 'M')] store=[]
```

### V1-no-requery / device (budget 3): L1

```
M:claim IDF
H1:query->pending
=> attacker stops here; honest actors can no longer reach all-green. devs=(('waiting', None, 0), ('noF', None, 0)) claims=[('c50125f4bd266252', 'claimed', 'M')] store=[]
```

### V1-no-requery / leak (budget 3): L1

```
H1:query->upload
H1:PUT st/c50125/H11+Complete
LEAK:PUT G over st/c50125/H11
=> attacker stops here; honest actors can no longer reach all-green. devs=(('awaiting', 'st/c50125/H11', 1), ('noF', None, 0)) claims=[('c50125f4bd266252', 'staged', 'H1')] store=[]
```

### V1-no-requery / fault (budget 3): L1

```
H1:query->upload
H1:PUT st/c50125/H11+Complete
FAULT:staged object vanishes st/c50125/H11
=> attacker stops here; honest actors can no longer reach all-green. devs=(('awaiting', 'st/c50125/H11', 1), ('noF', None, 0)) claims=[('c50125f4bd266252', 'staged', 'H1')] store=[]
```

### V1-no-attribution / leak (budget 3): S3

```
H1:query->upload
LEAK:PUT G over st/c50125/H11
homelab:REJECT st/c50125/H11 flag=('H1', 'rejected-upload')
=> honest device flagged [('H1', 'rejected-upload')]
```

### V1-no-attribution / cloud (budget 3): S3

```
H1:query->upload
CLOUD:inject G as c50125
homelab:REJECT st/c50125/CLOUD flag=('H1', 'rejected-upload')
=> honest device flagged [('H1', 'rejected-upload')]
```

### V1-no-homelab_verify / device (budget 3): S2

```
M:claim IDF
M:PUT poison G as IDF at st/c50125/M1
homelab:commit st/c50125/M1 (signer M)
=> store holds content under an ID it does not hash to
```

### V1-no-homelab_verify / device (budget 3): S1

```
M:claim IDF
M:PUT poison G as IDF at st/c50125/M1
homelab:commit st/c50125/M1 (signer M)
H1:query->present
H1:dedup-hit meta PUT
homelab:dedup-hit receipt H1
H1:receipt verified -> GREEN
=> ['H1'] green but the homelab store lacks F
```

### V1-no-homelab_verify / device (budget 3): SL

```
M:claim IDF
M:PUT poison G as IDF at st/c50125/M1
homelab:commit st/c50125/M1 (signer M)
H1:query->present
H1:dedup-hit meta PUT
homelab:dedup-hit receipt H1
H1:receipt verified -> GREEN
=> SILENT LOSS: ['H1'] green, store lacks F, and no honest continuation can ever store F
```

### V1-no-homelab_verify / device (budget 3): L1

```
M:claim IDF
M:PUT poison G as IDF at st/c50125/M1
homelab:commit st/c50125/M1 (signer M)
=> attacker stops here; honest actors can no longer reach all-green. devs=(('idle', None, 0), ('noF', None, 0)) claims=[('c50125f4bd266252', 'committed', '-')] store=['c50125']
```

### V1-no-homelab_verify / leak (budget 3): S2

```
H1:query->upload
H1:PUT st/c50125/H11+Complete
LEAK:PUT G over st/c50125/H11
homelab:commit st/c50125/H11 (signer H1)
=> store holds content under an ID it does not hash to
```

### V1-no-homelab_verify / leak (budget 3): S1

```
H1:query->upload
H1:PUT st/c50125/H11+Complete
LEAK:PUT G over st/c50125/H11
homelab:commit st/c50125/H11 (signer H1)
H1:receipt verified -> GREEN
=> ['H1'] green but the homelab store lacks F
```

### V1-no-homelab_verify / leak (budget 3): SL

```
H1:query->upload
H1:PUT st/c50125/H11+Complete
LEAK:PUT G over st/c50125/H11
homelab:commit st/c50125/H11 (signer H1)
H1:receipt verified -> GREEN
=> SILENT LOSS: ['H1'] green, store lacks F, and no honest continuation can ever store F
```

### V1-no-homelab_verify / leak (budget 3): L1

```
H1:query->upload
H1:PUT st/c50125/H11+Complete
LEAK:PUT G over st/c50125/H11
=> attacker stops here; honest actors can no longer reach all-green. devs=(('awaiting', 'st/c50125/H11', 1), ('noF', None, 0)) claims=[('c50125f4bd266252', 'staged', 'H1')] store=[]
```

### V1-no-homelab_verify / cloud (budget 3): S2

```
H1:query->upload
H1:PUT st/c50125/H11+Complete
CLOUD:swap content at st/c50125/H11
homelab:commit st/c50125/H11 (signer H1)
=> store holds content under an ID it does not hash to
```

### V1-no-homelab_verify / cloud (budget 3): S1

```
H1:query->upload
H1:PUT st/c50125/H11+Complete
CLOUD:swap content at st/c50125/H11
homelab:commit st/c50125/H11 (signer H1)
CLOUD:relay receipt H1/c50125 signed HOMELAB
H1:receipt verified -> GREEN
=> ['H1'] green but the homelab store lacks F
```

### V1-no-homelab_verify / cloud (budget 3): SL

```
H1:query->upload
H1:PUT st/c50125/H11+Complete
CLOUD:swap content at st/c50125/H11
homelab:commit st/c50125/H11 (signer H1)
CLOUD:relay receipt H1/c50125 signed HOMELAB
H1:receipt verified -> GREEN
=> SILENT LOSS: ['H1'] green, store lacks F, and no honest continuation can ever store F
```

### V1-no-reconcile_missing / fault (budget 3): L1

```
H1:query->upload
H1:PUT st/c50125/H11+Complete
FAULT:staged object vanishes st/c50125/H11
=> attacker stops here; honest actors can no longer reach all-green. devs=(('awaiting', 'st/c50125/H11', 1), ('noF', None, 0)) claims=[('c50125f4bd266252', 'staged', 'H1')] store=[]
```

