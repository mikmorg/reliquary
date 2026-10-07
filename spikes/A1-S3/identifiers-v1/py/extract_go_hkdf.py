#!/usr/bin/env python3
# THROWAWAY: extract the SHA-256 entries of hkdfTests from golang.org/x/crypto hkdf/hkdf_test.go
# (the first three are commented "Tests from RFC 5869") into JSON. Usage: extract_go_hkdf.py hkdf_test.go > out.json
import re, json, sys
src = open(sys.argv[1]).read(); body = src[src.index('var hkdfTests'):]
out = []
for e in re.split(r'\n\t\{\n\t\t', body)[1:]:
    if e.split(',', 1)[0].strip() != 'sha256.New': continue
    b = [None if m.group(0) == 'nil' else bytes(int(x, 16) for x in re.findall(r'0x([0-9a-fA-F]{2})', m.group(2)))
         for m in re.finditer(r'(\[\]byte\{(.*?)\}|nil)', e.split('\n\t},')[0], re.S)]
    ikm, salt, prk, info, okm = b[:5]
    out.append(dict(ikm=ikm.hex(), salt=(salt or b'').hex(), salt_nil=salt is None, prk=prk.hex(), info=(info or b'').hex(), okm=okm.hex()))
json.dump({"source": sys.argv[1], "vectors": out}, sys.stdout, indent=1)
