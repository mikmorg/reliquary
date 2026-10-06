"""Check every RT attack against the current F3 matrix and D1 IDs; classify and tally."""
import re, json, hashlib, sys
from attacks import A
f3p = '/home/user/reliquary/docs/research/f3-security-literature.md'
d1p = '/home/user/reliquary/docs/research/d1-threat-model.md'
f3 = open(f3p).read(); d1 = open(d1p).read()
snap = {p: hashlib.sha256(open(p, 'rb').read()).hexdigest()[:16] for p in (f3p, d1p)}
mrows = {}
for line in f3.splitlines():
    m = re.match(r'\|\s*(M-\d\d)\s*\|(.*)', line)
    if m:
        cells = [c.strip() for c in line.strip('|').split('|')]
        mrows[m.group(1)] = cells[4] if len(cells) > 4 else ''
sr = set(re.findall(r'\| (SR-\d\d) \|', d1)); ar = set(re.findall(r'\| (AR-\d\d) \|', d1)); tt = set(re.findall(r'\| (T-\d\d) \|', d1))
def status(ref):
    if ref.startswith('M-'):
        if ref not in mrows: return 'missing'
        s = mrows[ref].lower()
        return 'open' if s.startswith('**open**') or s.startswith('open') else ('accepted' if s.startswith('accepted') else 'mitigated')
    if ref.startswith('SR-'): return 'mitigated' if ref in sr else 'missing'
    if ref.startswith('AR-'): return 'accepted' if ref in ar else 'missing'
    if ref.startswith('T-'): return 'threat-listed' if ref in tt else 'missing'
    return 'missing'
out = []; tally = {}
for x in A:
    st = [status(r) for r in x['refs']]
    if not x['refs']: cls = 'UNMAPPED'
    elif 'missing' in st: cls = 'BROKEN-REF'
    elif not any(r.startswith('M-') for r in x['refs']):
        cls = 'D1-ONLY' if any(s in ('mitigated', 'accepted') for s in st) else 'UNMAPPED'
    elif any(s in ('mitigated', 'accepted') for r, s in zip(x['refs'], st) if r.startswith('M-') or r.startswith('AR-')):
        cls = 'MAPPED'
    else:
        cls = 'MAPPED-OPEN'
    x = dict(x, ref_status=dict(zip(x['refs'], st)), cls=cls); out.append(x)
    tally[cls] = tally.get(cls, 0) + 1
res = dict(snapshot_sha256_16=snap, matrix_rows_found=sorted(mrows), n_attacks=len(A), tally=tally,
           verdict='PASS' if tally.get('UNMAPPED', 0) == 0 and tally.get('BROKEN-REF', 0) == 0 else 'FAIL', attacks=out)
json.dump(res, open('evidence/f3s3_results.json', 'w'), indent=1)
print(json.dumps({k: res[k] for k in ('snapshot_sha256_16', 'n_attacks', 'tally', 'verdict')}, indent=1))
print('matrix rows', len(mrows), 'SR', len(sr), 'AR', len(ar), 'T', len(tt))
for x in out:
    if x['cls'] != 'MAPPED': print(f"{x['id']} {x['cls']:12} {x['attack'][:95]}")
