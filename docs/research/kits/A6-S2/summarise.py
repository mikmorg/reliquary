#!/usr/bin/env python3
"""Summarise A6-S2 results.jsonl against the PLAN pass criteria.

usage: summarise.py results.jsonl [DOWNLINK_MBIT]
Budget IDs: BUD-INGEST (>= max(100 MB/s, 2 x home downlink)), BUD-RESTORE (single-file
read < 5 s), BUD-AUDIT (full audit of 10 TB fits a monthly window), plus PLAN's RAM < 4 GB.
Thresholds are copied from docs/research/budgets.md / PLAN A6-S2; do not change them here.
"""
import json, sys

rows = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
downlink_mbit = float(sys.argv[2]) if len(sys.argv) > 2 else None
ingest_floor = max(100.0, 2 * downlink_mbit / 8) if downlink_mbit else 100.0
TEN_TB = 10e12
corpus = next((r for r in rows if "corpus_bytes" in r), {})
eng = {}
for r in rows:
    e = r.get("engine")
    if e:
        eng.setdefault(e, []).append(r)


def pct(v, p):
    v = sorted(v)
    return v[min(len(v) - 1, int(round(p / 100 * (len(v) - 1))))] if v else None


print(f"corpus: {corpus.get('corpus_files')} files, {corpus.get('corpus_bytes')} bytes")
print(f"BUD-INGEST floor used: {ingest_floor:.0f} MB/s" + ("" if downlink_mbit else " (downlink not given: 100 MB/s floor only)"))
for e, rs in eng.items():
    print(f"\n== {e}")
    rss = max((r.get("peak_rss_mb", 0) for r in rs), default=0)
    if e in ("cas", "ocfl"):
        ing = next(r for r in rs if r.get("label") == "ingest")
        summ = next(r for r in rs if "ingest_summary" in r)
        # "ingest: N records committed, M new blobs, B plaintext bytes in ..."
        b = int(summ["ingest_summary"].split(" new blobs, ")[1].split(" ")[0])
        mbps = b / 1e6 / ing["wall_s"]
        aud = next(r for r in rs if r.get("label") == "audit-detail")
        gets = [r["wall_s"] for r in rs if r.get("label") == "get"]
        print(f"ingest: {b} unique bytes in {ing['wall_s']} s = {mbps:.1f} MB/s -> BUD-INGEST {'PASS' if mbps >= ingest_floor else 'FAIL'}")
        print(f"store: {summ['store_bytes']} bytes, {summ['store_files']} files; overhead vs unique plaintext {100*(summ['store_bytes']-b)/b:.3f} %; catalog {summ['catalog_bytes']} bytes")
        print(f"audit (keyless): {aud['MBps']:.1f} MB/s -> 10 TB in {TEN_TB/aud['MBps']/1e6/3600:.1f} h ({100*TEN_TB/aud['MBps']/1e6/(30*86400):.1f} % of a 30-day month)")
        restore_ok = next((r for r in rs if r.get("label") == "get-check"), {})
        print(f"single-file restore by SHA-256: n={len(gets)} p50 {pct(gets,50)} s, p95 {pct(gets,95)} s, max {max(gets) if gets else None} s; sha256 ok {restore_ok.get('sha256_ok')}/{restore_ok.get('of')} -> BUD-RESTORE {'PASS' if gets and max(gets) < 5 else 'FAIL'}")
        rb = next((r for r in rs if r.get("label") == "rebuild"), None)
        rbc = next((r for r in rs if r.get("label") == "rebuild-check"), {})
        if rb:
            print(f"catalog rebuild from store: {rb['wall_s']} s, byte-identical: {rbc.get('byte_identical')}")
    else:
        bk = [r for r in rs if r.get("label") == "restic-backup"]
        wall = sum(r["wall_s"] for r in bk)
        b = corpus.get("corpus_bytes", 0)
        chk = next((r for r in rs if r.get("label") == "restic-check-read-data"), None)
        repo = next((r for r in rs if r.get("label") == "restic-repo"), {})
        dumps = [r["wall_s"] for r in rs if r.get("label") == "restic-dump"]
        dc = next((r for r in rs if r.get("label") == "dump-check"), {})
        print(f"backup: {len(bk)} snapshots, {wall:.1f} s, {b/1e6/wall if wall else 0:.1f} MB/s (corpus bytes incl. duplicates)")
        print(f"repo: {repo.get('repo_bytes')} bytes, {repo.get('pack_files')} pack files")
        if chk:
            print(f"check --read-data: {chk['wall_s']} s -> {repo.get('repo_bytes',0)/1e6/chk['wall_s']:.1f} MB/s -> 10 TB in {TEN_TB/(repo.get('repo_bytes',1)/chk['wall_s'])/3600:.1f} h")
        print(f"single-file dump: n={len(dumps)} p50 {pct(dumps,50)} s, p95 {pct(dumps,95)} s, max {max(dumps) if dumps else None} s; sha256 ok {dc.get('sha256_ok')}/{dc.get('of')}")
    print(f"peak RSS over all phases: {rss} MB -> RAM < 4 GB {'PASS' if rss < 4096 else 'FAIL'}")
