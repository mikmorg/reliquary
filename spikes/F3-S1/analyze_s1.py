"""F3-S1: size fingerprinting on public corpus data (PUB -> results).
Outputs aggregate statistics only (no per-file rows)."""
import numpy as np, json, sys
from padlib import padme, bucket, age_ct_len

rng = np.random.default_rng(20260929)

def classes(s):
    _, inv, cnt = np.unique(s, return_inverse=True, return_counts=True)
    k = cnt[inv]
    return {'unique_share': float(np.mean(k == 1)),
            'share_k_lt_10': float(np.mean(k < 10)),
            'median_k': float(np.median(k)),
            'distinct_sizes': int(len(cnt))}

def overhead(s, p):
    s = s.astype(np.float64); p = p.astype(np.float64)
    rel = np.where(s > 0, (p - s) / np.maximum(s, 1), 0.0)
    return {'byte_weighted_pct': float((p.sum() / s.sum() - 1) * 100),
            'mean_per_file_pct': float(rel.mean() * 100),
            'max_per_file_pct': float(rel.max() * 100),
            'max_per_file_pct_ge_64KiB': float(rel[s >= 65536].max() * 100) if (s >= 65536).any() else None}

def study(name, sizes, Ns):
    res = {'corpus': name, 'files_after_content_dedup': int(len(sizes)),
           'total_bytes': int(sizes.sum()),
           'size_percentiles_bytes': {q: int(np.percentile(sizes, q)) for q in (1, 10, 50, 90, 99)},
           'mean_bytes': float(sizes.mean()), 'by_N': []}
    pad_p = padme(sizes); pad_b = bucket(sizes)
    # age ciphertext length is a strictly increasing function of plaintext length:
    ct = age_ct_len(sizes, 168)
    assert len(np.unique(ct)) == len(np.unique(sizes)), 'age length map not injective?'
    ct_p = age_ct_len(pad_p, 168)
    assert len(np.unique(ct_p)) == len(np.unique(pad_p))
    res['overhead_full'] = {'padme': overhead(sizes, pad_p), 'bucket_64KiB': overhead(sizes, pad_b),
                            'age_x25519_ct_vs_plain': overhead(sizes, ct)}
    for N in Ns:
        if N > len(sizes): continue
        reps = 5 if N <= 100_000 else (3 if N < len(sizes) else 1)
        rows = []
        for r in range(reps):
            idx = rng.choice(len(sizes), N, replace=False) if N < len(sizes) else np.arange(len(sizes))
            s = sizes[idx]
            rows.append({'exact': classes(s), 'padme': classes(padme(s)), 'bucket_64KiB': classes(bucket(s)),
                         'padme_cost': overhead(s, padme(s))['byte_weighted_pct'],
                         'bucket_cost': overhead(s, bucket(s))['byte_weighted_pct']})
        agg = {'N': N, 'reps': reps}
        for key in ('exact', 'padme', 'bucket_64KiB'):
            for m in ('unique_share', 'share_k_lt_10', 'median_k'):
                v = [x[key][m] for x in rows]
                agg[f'{key}.{m}'] = [min(v), float(np.mean(v)), max(v)]
        for key in ('padme_cost', 'bucket_cost'):
            v = [x[key] for x in rows]; agg[key + '_pct'] = [min(v), float(np.mean(v)), max(v)]
        res['by_N'].append(agg)
        print(name, N, json.dumps({k: (round(v[1], 4) if isinstance(v, list) else v) for k, v in agg.items()}), flush=True)
    # size-band breakdown on the full set
    bands = [(0, 65536), (65536, 1 << 20), (1 << 20, 16 << 20), (16 << 20, 1 << 62)]
    full = classes(sizes); pfull = padme(sizes)
    _, inv, cnt = np.unique(sizes, return_inverse=True, return_counts=True); k = cnt[inv]
    _, inv2, cnt2 = np.unique(pfull, return_inverse=True, return_counts=True); k2 = cnt2[inv2]
    res['bands_full'] = []
    for lo, hi in bands:
        m = (sizes >= lo) & (sizes < hi)
        if not m.any(): continue
        res['bands_full'].append({'lo': lo, 'hi': hi, 'files': int(m.sum()),
            'exact_unique_share': float(np.mean(k[m] == 1)), 'padme_unique_share': float(np.mean(k2[m] == 1)),
            'padme_cost_pct': overhead(sizes[m], pfull[m])['byte_weighted_pct'],
            'bucket_cost_pct': overhead(sizes[m], bucket(sizes[m]))['byte_weighted_pct']})
    return res

out = []
# Open Images 2018_04 (P11): dedup identical content by OriginalMD5
s = np.fromfile('oi_sizes.u64', dtype='<u8'); m = np.fromfile('oi_md5.bin', dtype='S16')
print('OI rows', len(s), 'zero-size', int((s == 0).sum()), file=sys.stderr)
_, first = np.unique(m, return_index=True)
s_oi = s[np.sort(first)]; s_oi = s_oi[s_oi > 0]
print('OI after md5 dedup and dropping 0-byte', len(s_oi), file=sys.stderr)
out.append(study('OpenImages-2018_04-OriginalSize', s_oi, [1_000, 10_000, 100_000, 1_000_000, 5_000_000, len(s_oi)]))
# GovDocs1 (P9): dedup by (size, crc32)
g = np.loadtxt('govdocs_members.tsv', dtype=np.int64, usecols=(2, 3), delimiter='\t')
ukey = np.unique(g, axis=0)
s_gd = ukey[:, 0].astype(np.uint64); s_gd = s_gd[s_gd > 0]
print('GovDocs members', len(g), 'after (size,crc) dedup, non-empty', len(s_gd), file=sys.stderr)
out.append(study('GovDocs1-zipfiles-uncompressed-size', s_gd, [1_000, 10_000, 100_000, len(s_gd)]))
json.dump(out, open('f3s1_results.json', 'w'), indent=1)
