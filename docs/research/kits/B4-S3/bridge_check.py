#!/usr/bin/env python3
"""Kit B4-S3: check what an iCloud Photos bridge delivered. Prints AGGREGATES ONLY.

Run it where the bridged files are (the Mac/PC, or the homelab private store). It never
prints file names, hashes, GPS or pixels. Needs Python 3.9+ and ExifTool on PATH.

  python3 bridge_check.py --bridge DIR [--reference DIR] --download-started 2026-10-04T14:00:00+02:00 \
      [--expect-mp 12,24,48] [--no-suppress] > results-aggregate.json

--bridge     the folder the bridge filled (icloudpd output, or the Mac/PC Photos export / iCloud folder)
--reference  optional: LAB test shots copied straight off the iPhone by cable with
             "Keep Originals" (see README). Matched to bridge files by SHA-256, locally.
--download-started  when the bridge download began; used to spot file dates that are just
             the download time instead of the capture time.
--expect-mp  full-resolution megapixel classes the camera produces (from the phone model).
Small counts (1-4) are shown as "<5" unless --no-suppress (use --no-suppress only for LAB-only runs).
"""
import argparse, collections, datetime as dt, hashlib, json, os, subprocess, sys

PHOTO_EXT = {'.heic', '.heif', '.jpg', '.jpeg', '.png', '.dng', '.tif', '.tiff', '.gif', '.webp'}
VIDEO_EXT = {'.mov', '.mp4', '.m4v', '.3gp'}


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def exif(paths):
    if not paths:
        return {}
    out = {}
    tags = ['-DateTimeOriginal', '-CreateDate', '-OffsetTimeOriginal', '-ImageWidth', '-ImageHeight',
            '-Make', '-Model', '-MIMEType']
    for i in range(0, len(paths), 200):
        chunk = paths[i:i + 200]
        r = subprocess.run(['exiftool', '-json', '-n', '-q', '-q', *tags, *chunk], capture_output=True, text=True)
        for row in json.loads(r.stdout or '[]'):
            out[os.path.abspath(row['SourceFile'])] = row
    return out


def parse_exif_date(s):
    if not s or not isinstance(s, str) or s.startswith('0000'):
        return None
    try:
        return dt.datetime.strptime(s[:19], '%Y:%m:%d %H:%M:%S')
    except ValueError:
        return None


def walk(d):
    for root, _, files in os.walk(d):
        for n in files:
            if not n.startswith('.'):
                yield os.path.abspath(os.path.join(root, n))


def cell(n, suppress):
    return '<5' if suppress and 0 < n < 5 else n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--bridge', required=True)
    ap.add_argument('--reference')
    ap.add_argument('--download-started', required=True)
    ap.add_argument('--expect-mp', default='12,24,48')
    ap.add_argument('--no-suppress', action='store_true')
    a = ap.parse_args()
    sup = not a.no_suppress
    started = dt.datetime.fromisoformat(a.download_started).timestamp()
    expect = [float(x) for x in a.expect_mp.split(',') if x]

    files = list(walk(a.bridge))
    meta = exif(files)
    c = collections.Counter()
    mp_bins = collections.Counter()
    for p in files:
        ext = os.path.splitext(p)[1].lower()
        kind = 'photo' if ext in PHOTO_EXT else 'video' if ext in VIDEO_EXT else 'other'
        c['files_' + kind] += 1
        c['ext_' + ext.lstrip('.')] += 1
        m = meta.get(p, {})
        mtime = os.stat(p).st_mtime
        if mtime >= started - 60:  # a file date set at download time, not capture time
            c['mtime_is_download_time_' + kind] += 1
        if kind != 'photo':
            continue
        w, h = m.get('ImageWidth'), m.get('ImageHeight')
        if isinstance(w, (int, float)) and isinstance(h, (int, float)) and w and h:
            mp = w * h / 1e6
            # 10 % tolerance around each expected full-resolution class
            full = any(abs(mp - e) / e <= 0.10 for e in expect)
            c['photo_full_res' if full else 'photo_not_full_res'] += 1
            mp_bins[('<2' if mp < 2 else '2-6' if mp < 6 else '6-10' if mp < 10 else '10-14' if mp < 14
                     else '14-30' if mp < 30 else '30-60' if mp < 60 else '>=60') + ' MP'] += 1
        else:
            c['photo_no_dimensions'] += 1
        if m.get('Make') or m.get('Model'):
            c['photo_has_make_model'] += 1
        d = parse_exif_date(m.get('DateTimeOriginal')) or parse_exif_date(m.get('CreateDate'))
        if d is None:
            c['photo_no_exif_date'] += 1
        else:
            c['photo_has_exif_date'] += 1
            # EXIF dates are local time; compare with the file mtime allowing any UTC offset
            # that is a multiple of 15 minutes (up to 14 h), with 2 s of slack
            diff = abs(mtime - d.replace(tzinfo=dt.timezone.utc).timestamp())
            off = diff % 900
            if diff <= 14 * 3600 + 2 and (off <= 2 or off >= 898):
                c['photo_mtime_matches_exif_date'] += 1
            else:
                c['photo_mtime_differs_from_exif_date'] += 1

    out = {'kit': 'B4-S3', 'script_version': 1, 'generated_utc': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
           'expect_mp': expect, 'counts': {k: cell(v, sup) for k, v in sorted(c.items())},
           'photo_megapixel_bins': {k: cell(v, sup) for k, v in sorted(mp_bins.items())}}

    if a.reference:
        ref = list(walk(a.reference))
        bridge_hash = {}
        for p in files:
            bridge_hash.setdefault(sha256(p), p)
        rmeta = exif(ref)
        bmeta_by_date = collections.defaultdict(list)
        for p in files:
            k = meta.get(p, {}).get('DateTimeOriginal')
            if k:
                bmeta_by_date[k].append(p)
        rc = collections.Counter()
        for p in ref:
            rc['reference_files'] += 1
            if sha256(p) in bridge_hash:
                rc['byte_identical_in_bridge'] += 1
                continue
            k = rmeta.get(p, {}).get('DateTimeOriginal')
            if k and bmeta_by_date.get(k):
                rc['present_but_bytes_differ'] += 1  # re-encoded, reduced, or metadata rewritten
            else:
                rc['not_found_in_bridge'] += 1
        out['reference'] = dict(rc)  # LAB shots only: exact counts are fine
    json.dump(out, sys.stdout, indent=1)
    print()


if __name__ == '__main__':
    main()
