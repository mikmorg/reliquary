# GovDocs1 (Digital Corpora, s3://digitalcorpora, "no restrictions on use"):
# read ONLY the zip central directory of each zipfiles/NNN.zip with HTTP range
# requests and record (extension, uncompressed size, crc32) per member.
import urllib.request, struct, sys, concurrent.futures as cf, re
BASE = 'https://digitalcorpora.s3.amazonaws.com/corpora/files/govdocs1/zipfiles/'
def rng(url, a, b):
    req = urllib.request.Request(url, headers={'Range': f'bytes={a}-{b}'})
    with urllib.request.urlopen(req, timeout=60) as r: return r.read()
def size(url):
    req = urllib.request.Request(url, method='HEAD')
    with urllib.request.urlopen(req, timeout=60) as r: return int(r.headers['Content-Length'])
def one(i):
    url = BASE + f'{i:03d}.zip'
    for attempt in range(4):
        try:
            L = size(url)
            tail = rng(url, max(0, L-66000), L-1)
            p = tail.rfind(b'PK\x05\x06')
            (_, _, _, _, n, cdsize, cdoff, _) = struct.unpack('<IHHHHIIH', tail[p:p+22])
            if cdoff == 0xFFFFFFFF or n == 0xFFFF:  # zip64
                q = tail.rfind(b'PK\x06\x06')
                n, cdsize, cdoff = struct.unpack('<QQQ', tail[q+32:q+56])
            cd = rng(url, cdoff, cdoff+cdsize-1)
            out = []; o = 0
            while o < len(cd) and cd[o:o+4] == b'PK\x01\x02':
                crc, csz, usz, fnl, exl, cml = struct.unpack('<III HHH', cd[o+16:o+34])
                name = cd[o+46:o+46+fnl].decode('latin1')
                ex = cd[o+46+fnl:o+46+fnl+exl]
                if usz == 0xFFFFFFFF:  # zip64 extra
                    k = 0
                    while k < len(ex):
                        hid, hl = struct.unpack('<HH', ex[k:k+4])
                        if hid == 1: usz = struct.unpack('<Q', ex[k+4:k+12])[0]; break
                        k += 4 + hl
                o += 46 + fnl + exl + cml
                if name.endswith('/'): continue
                m = re.search(r'\.([A-Za-z0-9]{1,6})$', name)
                out.append((m.group(1).lower() if m else '', usz, crc))
            return i, out
        except Exception as e:
            err = e
    return i, ('ERR', repr(err))
with cf.ThreadPoolExecutor(16) as ex, open('govdocs_members.tsv', 'w') as f:
    errs = 0
    for i, res in ex.map(one, range(1000)):
        if isinstance(res, tuple): errs += 1; print('zip', i, res, file=sys.stderr); continue
        for e, s, c in res: f.write(f'{i}\t{e}\t{s}\t{c}\n')
print('errors', errs, file=sys.stderr)
