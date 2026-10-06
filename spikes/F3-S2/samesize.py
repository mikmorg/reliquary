"""Measure the largest same-exact-size cluster in random public samples (legit false-positive
input for detector D-c). Needs ../F3-S1 extraction outputs in D. Writes legit_samesize.json."""
import numpy as np, json
D = '../F3-S1/'
rng = np.random.default_rng(3)
s = np.fromfile(D+'oi_sizes.u64', dtype='<u8'); m = np.fromfile(D+'oi_md5.bin', dtype='S16')
_, first = np.unique(m, return_index=True); oi = s[np.sort(first)]
g = np.loadtxt(D+'govdocs_members.tsv', dtype=np.int64, usecols=(2, 3), delimiter='\t')
gd = np.unique(g, axis=0)[:, 0]; gd = gd[gd > 0]
def maxc(a): return int(np.unique(a, return_counts=True)[1].max())
p = [maxc(oi[rng.choice(len(oi), 57399, replace=False)]) for _ in range(20)]
d = [maxc(gd[rng.choice(len(gd), 250000, replace=False)]) for _ in range(10)]
d_big = [maxc((lambda x: x[x >= 65536])(gd[rng.choice(len(gd), 250000, replace=False)])) for _ in range(10)]
out = dict(photo_57k_max_cluster=max(p), photo_57k_cluster_samples=p,
           doc_500k_max_cluster_per_24h=max(d), doc_250k_cluster_samples=d, doc_250k_ge64KiB_cluster_samples=d_big,
           note='max number of distinct-content files sharing one exact size, in random public samples '
                '(OI photos: 57,399 = one BUD-HASH seed; GovDocs1: 250k = half of a 500k desktop seed per 24 h)')
json.dump(out, open('legit_samesize.json', 'w'), indent=1); print(out)
