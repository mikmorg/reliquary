#!/usr/bin/env python3
"""Turn fidelity.py JSON outputs into one Markdown comparison table.

Usage: python3 compare.py results/final/miniflare.json results/final/seaweedfs.json ... > comparison.md
"""
import json, sys

DOC = ['T04', 'T05', 'T06', 'T07', 'T09', 'T10', 'T11', 'T20', 'T23', 'T31', 'T32', 'T33', 'T34', 'T35', 'T41', 'T53', 'T54']  # rows whose R2 expectation is stated in R2 docs (see the G2 note, claim C16)



def cell(o):
    if not isinstance(o, dict):
        return json.dumps(o)
    if "status" in o and set(o) <= {"status", "code"}:
        return f"{o['status']}{(' ' + o['code']) if o.get('code') else ''}"
    parts = []
    for k, v in o.items():
        if isinstance(v, dict):
            parts.append(f"{k}: {cell(v)}")
        elif k == "status":
            parts.append(f"{v}{(' ' + o['code']) if o.get('code') else ''}")
        elif k == "code":
            continue
        elif isinstance(v, list) and len(v) > 6:
            parts.append(f"{k}: {min(v)}..{max(v)} (n={len(v)})")
        else:
            parts.append(f"{k}: {v}")
    return "; ".join(parts)


runs = [json.load(open(p)) for p in sys.argv[1:]]
ids, titles, doc = [], {}, {}
for r in runs:
    for t in r["results"]:
        if t["id"] not in titles:
            ids.append(t["id"])
            titles[t["id"]] = t["title"]
            doc[t["id"]] = t.get("r2_documented")
print("| ID | Check | R2 expectation ([doc] = stated in R2 docs; otherwise expected/unknown, to be measured by the SB kit) | " + " | ".join(r["target"] for r in runs) + " |")
print("|---|---|---|" + "---|" * len(runs))
for i in ids:
    e = doc[i] or "-"
    if i in DOC and not e.startswith("["):
        e = "[doc] " + e
    elif not e.startswith("[") and e != "-":
        e = "[expected] " + e
    row = [i, titles[i], e]
    for r in runs:
        m = [t for t in r["results"] if t["id"] == i]
        row.append(cell(m[0]["observed"]).replace("|", "/").replace("\r", " ").replace("\n", " ") if m else "not run")
    print("| " + " | ".join(str(x) for x in row) + " |")
print()
for r in runs:
    print(f"- {r['target']}: endpoint `{r['endpoint']}`, run `{r['run_id']}` finished {r.get('finished_utc', r.get('started_utc'))}, "
          f"{r['duration_s']} s, {r.get('requests_sent_by_script', '?')} S3 requests sent by the script")
