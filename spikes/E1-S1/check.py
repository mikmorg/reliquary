#!/usr/bin/env python3
"""Compare census output with generator truth and run the H3 §4 output checks (SYN rehearsal).
Usage: check.py OUTDIR TRUTH.json [--exif]"""
import csv, json, os, re, sys
from collections import defaultdict

out, truth_p = sys.argv[1], sys.argv[2]
exif = "--exif" in sys.argv
truth = json.load(open(truth_p))
res = []


def ok(name, cond, detail=""):
    res.append((name, bool(cond), detail))


def rows(name):
    return list(csv.DictReader(open(os.path.join(out, name))))


def num(x):
    return None if x in ("<5", "") else int(x)


# 1. category totals per state (the census suppresses cells <5; compare only where truth is known)
got = defaultdict(lambda: [0, 0, 0])  # count, bytes, suppressed cells
for fname, st in (("census_local.csv", "local"), ("census_cloud_only.csv", "cloud-only")):
    for r in rows(fname):
        k = (r["category"], st)
        if r["count"] == "<5":
            got[k][2] += 1
        else:
            got[k][0] += int(r["count"])
            got[k][1] += int(r["bytes"])
for k, v in truth.items():
    if not k.startswith("cat|"):
        continue
    _, cat, st = k.split("|")
    g = got[(cat, st)]
    exact = g[0] == v[0] and g[1] == v[1]
    within = g[2] > 0 and v[0] - g[0] <= 4 * g[2] and g[0] <= v[0]
    ok(f"category {cat}/{st}", exact or within,
       f"truth {v[0]} files {v[1]} B; census {g[0]} files {g[1]} B (+{g[2]} suppressed cells)")

# 2. location totals (location_class, state, category)
gl = {}
for r in rows("census_locations.csv"):
    gl[(r["location_class"], r["state"], r["category"])] = (num(r["count"]), num(r["bytes"]))
for k, v in truth.items():
    if not k.startswith("loc|"):
        continue
    _, loc, st, cat = k.split("|")
    g = gl.get((loc, st, cat))
    ok(f"location {loc}/{st}/{cat}", g is not None and (g == (v[0], v[1]) or (g[0] is None and v[0] < 5)),
       f"truth {v}; census {g}")

# 3. EXIF capture months (photo, source=exif) vs truth, for months inside the 24-month window
if exif:
    gm = defaultdict(int)
    for r in rows("census_months.csv"):
        if r["category"] == "photo" and r["source"] == "exif" and re.match(r"\d{4}-\d{2}$", r["month"]):
            gm[r["month"]] += num(r["count"]) or 0
    tm = {k.split("|")[1]: v[0] for k, v in truth.items() if k.startswith("exifmonth|")}
    mism = [(m, tm[m], gm.get(m)) for m in gm if tm.get(m) != gm[m]]
    ok("exif months match truth (months in window)", not mism and gm, f"{len(gm)} months compared; mismatches {mism[:5]}")
    gc = {(r["make"], r["model"]): num(r["count"]) for r in rows("census_cameras.csv")}
    tc = {tuple(k.split("|")[1:]): v[0] for k, v in truth.items() if k.startswith("camera|")}
    ok("camera model counts match truth", gc == tc, f"census {gc} truth {tc}")

# 4. H3 §4 output check, mechanised where possible
blob = ""
for f in os.listdir(out):
    blob += open(os.path.join(out, f), encoding="utf-8").read()
ok("no generated name fragments (Qx7) in output", "qx7" not in blob.lower())
ok("no path separators in output", "/" not in blob and "\\" not in blob)
ok("no non-ASCII characters in output", all(ord(c) < 128 for c in blob))
ok("no home/user/root path words", not re.search(r"home|syn1|users?\b", blob, re.I))
ok("no day-level dates (YYYY-MM-DD)", not re.search(r"\d{4}-\d{2}-\d{2}", blob))
small = []
for f in os.listdir(out):
    for r in csv.DictReader(open(os.path.join(out, f))):
        c = r.get("count")
        if c is not None and c != "<5" and int(c) < 5:
            small.append((f, r))
ok("every exported cell counts >= 5 or is '<5'", not small, str(small[:3]))
ok("no hex strings that look like hashes (>= 32 hex chars)", not re.search(r"\b[0-9a-f]{32,}\b", blob))

fails = [r for r in res if not r[1]]
for name, good, detail in res:
    print(("PASS " if good else "FAIL ") + name + ("" if good else "  :: " + detail))
print(f"\n{len(res) - len(fails)}/{len(res)} checks passed")
sys.exit(1 if fails else 0)
