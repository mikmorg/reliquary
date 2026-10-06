"""F3-S1 follow-up: where does the exact-size unique share cross 50 %? (3 reps each)"""
import numpy as np, json
rng = np.random.default_rng(7)
def uniq(s):
    _, inv, cnt = np.unique(s, return_inverse=True, return_counts=True)
    return float(np.mean(cnt[inv] == 1))
s = np.fromfile('oi_sizes.u64', dtype='<u8'); m = np.fromfile('oi_md5.bin', dtype='S16')
_, first = np.unique(m, return_index=True); oi = s[np.sort(first)]
g = np.loadtxt('govdocs_members.tsv', dtype=np.int64, usecols=(2, 3), delimiter='\t')
gd = np.unique(g, axis=0)[:, 0]; gd = gd[gd > 0].astype(np.uint64)
out = {}
for name, arr, Ns in (('OpenImages', oi, [250_000, 500_000, 2_000_000, 3_000_000, 4_000_000]),
                      ('GovDocs1', gd, [25_000, 50_000, 150_000, 200_000, 300_000, 500_000])):
    for N in Ns:
        v = [uniq(arr[rng.choice(len(arr), N, replace=False)]) for _ in range(3)]
        out[f'{name}:{N}'] = [round(min(v), 4), round(float(np.mean(v)), 4), round(max(v), 4)]
        print(name, N, out[f'{name}:{N}'], flush=True)
json.dump(out, open('f3s1_crossover.json', 'w'), indent=1)
