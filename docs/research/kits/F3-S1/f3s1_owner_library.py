#!/usr/bin/env python3
"""F3-S1 owner-library part (FAM -> AGG). Runs on the homelab, inside the private store.

Walks one or more directory trees READ-ONLY (os.scandir + stat; file content is never
opened unless --dedup-sha256 is given) and prints aggregate statistics only:
  - % of files with a unique exact size, before and after Padme and 64 KiB buckets
  - storage overhead of Padme and 64 KiB buckets (byte-weighted, per-file mean/max)
  - the same split by coarse category (photo / video / document / other)
  - a log2 size histogram (H3 R3 bins)
It never prints or writes filenames, paths or per-file sizes (H3 R2, R3, R11).
Standard library only (Python >= 3.8). Padme matches dedis/purb padding.go.

Usage:  python3 f3s1_owner_library.py /srv/library [/more/roots ...] > f3s1_owner_agg.json
        add --dedup-sha256 to collapse identical files first (reads every byte; slow)
"""
import argparse, collections, hashlib, json, math, os, stat, sys, time

PHOTO = {'jpg', 'jpeg', 'heic', 'heif', 'png', 'gif', 'webp', 'avif', 'jxl', 'tif', 'tiff', 'bmp',
         'dng', 'cr2', 'cr3', 'nef', 'arw', 'raf', 'rw2', 'orf'}
VIDEO = {'mp4', 'mov', 'm4v', 'avi', 'mkv', '3gp', 'mts', 'm2ts', 'wmv', 'webm', 'mpg', 'mpeg'}
DOC = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'odt', 'ods', 'odp', 'txt', 'rtf',
       'csv', 'epub', 'pages', 'numbers', 'key', 'md', 'html', 'htm', 'eml', 'msg'}
MIN_CELL = 50  # categories with fewer files are reported as "suppressed"

def padme(n):
    if n < 2:
        return n
    e = n.bit_length() - 1
    z = e - e.bit_length()
    if z <= 0:
        return n
    m = (1 << z) - 1
    return (n + m) & ~m

def bucket(n, b=65536):
    return -(-n // b) * b

def category(name):
    ext = name.rsplit('.', 1)[-1].lower() if '.' in name else ''
    return 'photo' if ext in PHOTO else 'video' if ext in VIDEO else 'document' if ext in DOC else 'other'

def walk(roots, dedup):
    seen_inodes, seen_hash = set(), set()
    errors = 0
    stack = list(roots)
    while stack:
        d = stack.pop()
        try:
            it = os.scandir(d)
        except OSError:
            errors += 1
            continue
        with it:
            for e in it:
                try:
                    if e.is_dir(follow_symlinks=False):
                        stack.append(e.path)
                        continue
                    if not e.is_file(follow_symlinks=False):
                        continue
                    st = e.stat(follow_symlinks=False)
                except OSError:
                    errors += 1
                    continue
                key = (st.st_dev, st.st_ino)
                if key in seen_inodes:          # hard links count once
                    continue
                seen_inodes.add(key)
                if st.st_size == 0:
                    continue
                if dedup:
                    h = hashlib.sha256()
                    try:
                        with open(e.path, 'rb') as f:
                            for blk in iter(lambda: f.read(1 << 20), b''):
                                h.update(blk)
                    except OSError:
                        errors += 1
                        continue
                    dg = h.digest()
                    if dg in seen_hash:
                        continue
                    seen_hash.add(dg)
                yield category(e.name), st.st_size
    walk.errors = errors

def stats(sizes):
    n = len(sizes)
    out = {'files': n}
    if n < MIN_CELL:
        out['suppressed'] = True
        return out
    total = sum(sizes)
    for label, f in (('exact', lambda x: x), ('padme', padme), ('bucket_64KiB', bucket)):
        mapped = [f(s) for s in sizes]
        c = collections.Counter(mapped)
        ks = sorted(c[m] for m in mapped)
        out[label] = {'unique_share': round(sum(1 for m in mapped if c[m] == 1) / n, 4),
                      'share_k_lt_10': round(sum(1 for m in mapped if c[m] < 10) / n, 4),
                      'median_k': ks[n // 2]}
        if label != 'exact':
            rel = [(m - s) / s for m, s in zip(mapped, sizes)]
            out[label]['overhead_byte_weighted_pct'] = round((sum(mapped) / total - 1) * 100, 3)
            out[label]['overhead_mean_per_file_pct'] = round(sum(rel) / n * 100, 3)
            big = [r for r, s in zip(rel, sizes) if s >= 65536]
            out[label]['overhead_max_per_file_pct_ge_64KiB'] = round(max(big) * 100, 3) if big else None
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('roots', nargs='+')
    ap.add_argument('--dedup-sha256', action='store_true')
    a = ap.parse_args()
    t0 = time.time()
    by_cat = collections.defaultdict(list)
    for cat, size in walk(a.roots, a.dedup_sha256):
        by_cat[cat].append(size)
    allsizes = [s for v in by_cat.values() for s in v]
    hist = collections.Counter(max(0, s.bit_length() - 1) for s in allsizes)
    res = {'spike': 'F3-S1 owner library', 'class': 'FAM -> AGG (check with H3 section 4 before sharing)',
           'content_dedup': 'sha256' if a.dedup_sha256 else 'none (hard links only)',
           'unreadable_entries': getattr(walk, 'errors', 0),
           'elapsed_s': round(time.time() - t0, 1),
           'all': stats(allsizes),
           'by_category': {c: stats(v) for c, v in sorted(by_cat.items())},
           'log2_size_histogram': {f'2^{k}': (v if v >= 10 else '<10') for k, v in sorted(hist.items())}}
    json.dump(res, sys.stdout, indent=1)
    print(file=sys.stdout)

if __name__ == '__main__':
    main()
