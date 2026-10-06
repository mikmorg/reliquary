#!/usr/bin/env python3
"""A6-S1 Probe 4 (THROWAWAY): what plain-SHA-256 paths and age framing reveal to whoever holds the disks.
usage: python3 -I size-leak.py STORE PLAINDIR   (PLAINDIR = files named by their SHA-256, e.g. from the A6-S5 procedure)
Reads only stored bytes' lengths and headers; decrypts nothing. Data class SYN."""
import os, sys, glob, json, math, hashlib
st, plain = sys.argv[1], sys.argv[2]
ok = bad = 0; known_present = 0
for p in glob.glob(os.path.join(st, "blobs", "*", "*", "*.age")):
    data = open(p, "rb").read(4096)
    h = data.index(b"\n---"); h = data.index(b"\n", h + 1) + 1   # canonical age header length
    L = os.path.getsize(p) - h                                    # payload: 16 B nonce + 64 KiB chunks + 16 B tag each
    c = max(1, math.ceil((L - 16) / (65536 + 16)))
    n = L - 16 - 16 * c
    if n == os.path.getsize(os.path.join(plain, os.path.basename(p)[:-4])): ok += 1
    else: bad += 1
for f in sorted(os.listdir(plain))[:50]:                          # "is this known file in the archive?"
    s = hashlib.sha256(open(os.path.join(plain, f), "rb").read()).hexdigest()
    if os.path.exists(os.path.join(st, "blobs", s[:2], s[2:4], s + ".age")): known_present += 1
print(json.dumps({"objects": ok + bad, "plaintext_size_exactly_derived_from_stored_size": ok, "mismatch": bad,
                  "candidate_files_tested": 50, "candidate_presence_confirmed_by_path": known_present}))
