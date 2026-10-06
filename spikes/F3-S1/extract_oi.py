# Stream the Open Images 2018_04 image_ids_and_rotation.csv from stdin; keep only
# OriginalSize and OriginalMD5 (no URLs, titles or authors are written to disk).
import sys, csv, base64, struct
out_s = open('oi_sizes.u64', 'wb'); out_m = open('oi_md5.bin', 'wb')
r = csv.reader(sys.stdin)
hdr = next(r); iS = hdr.index('OriginalSize'); iM = hdr.index('OriginalMD5')
n = bad = 0
for row in r:
    try:
        s = int(row[iS]); m = base64.b64decode(row[iM])
        if len(m) != 16: raise ValueError
    except Exception:
        bad += 1; continue
    out_s.write(struct.pack('<Q', s)); out_m.write(m); n += 1
print('rows', n, 'bad', bad, file=sys.stderr)
