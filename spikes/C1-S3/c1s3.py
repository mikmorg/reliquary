#!/usr/bin/env python3
"""C1-S3 "which of 1,000 IDs are missing" against an N-row dedup index (throwaway, stdlib only).

EMULATED when pointed at wrangler dev (local D1 = SQLite inside workerd); the kit points it at a
Worker deployed on the sandbox account with a real D1 database.

  python3 c1s3.py --worker http://127.0.0.1:8787 --rows 5000000 --trials 200 --present 0.5 --out r.json
"""
import argparse, json, os, random, statistics, time, urllib.request


def call(base, path, body=None, timeout=600):
    req = urllib.request.Request(base + path, data=json.dumps(body).encode() if body is not None else None,
                                 method="POST" if body is not None else "GET",
                                 headers={"content-type": "application/json"})
    if os.environ.get("SPIKE_TOKEN"):
        req.add_header("x-spike-token", os.environ["SPIKE_TOKEN"])
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        out = json.loads(r.read())
    return out, (time.perf_counter() - t0) * 1000


def pct(xs, p):
    xs = sorted(xs)
    k = (len(xs) - 1) * p / 100
    f = int(k); c = min(f + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--worker", required=True)
    ap.add_argument("--rows", type=int, default=5_000_000)
    ap.add_argument("--chunk", type=int, default=100_000)
    ap.add_argument("--trials", type=int, default=200)
    ap.add_argument("--batch", type=int, default=1000)
    ap.add_argument("--present", type=float, default=0.5)
    ap.add_argument("--sample", type=int, default=5000)
    ap.add_argument("--skip-fill", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()
    b = a.worker
    call(b, "/s3/init")
    cnt = call(b, "/s3/count")[0]["c"]
    fill_log = []
    if not a.skip_fill:
        while cnt < a.rows:
            n = min(a.chunk, a.rows - cnt)
            r, ms = call(b, f"/s3/fill?n={n}")
            fill_log.append({"n": n, "client_ms": round(ms), "rows_written": r["meta"].get("rows_written"),
                             "duration": r["meta"].get("duration")})
            cnt = call(b, "/s3/count")[0]["c"]
            print(f"rows {cnt}", flush=True)
    plan = call(b, "/s3/plan")[0]
    present = []
    while len(present) < a.sample:
        present += call(b, "/s3/sample?n=500")[0]["ids"]
    present = [x.lower() for x in present]
    out = {"rows": cnt, "trials": a.trials, "batch": a.batch, "present_fraction": a.present, "query_plan": plan,
           "fill": {"chunks": len(fill_log), "first": fill_log[:2], "last": fill_log[-2:]}}
    for variant in ("json_each", "in100"):
        lat, dur, rows_read, miss_ok = [], [], [], 0
        for t in range(a.trials):
            k = int(a.batch * a.present)
            ids = random.sample(present, k) + [os.urandom(32).hex() for _ in range(a.batch - k)]
            random.shuffle(ids)
            r, ms = call(b, f"/s3/missing?variant={variant}", {"ids": ids})
            lat.append(ms)
            dur.append(r["meta"].get("duration") or 0)
            rows_read.append(r["meta"].get("rows_read") or 0)
            miss_ok += r["missing"] == a.batch - k
        out[variant] = {
            "client_latency_ms": {"p50": round(pct(lat, 50), 1), "p99": round(pct(lat, 99), 1), "max": round(max(lat), 1)},
            "d1_meta_duration_ms": {"p50": round(pct(dur, 50), 2), "p99": round(pct(dur, 99), 2)},
            "rows_read_per_call": {"min": min(rows_read), "median": statistics.median(rows_read), "max": max(rows_read)},
            "correct_missing_count": f"{miss_ok}/{a.trials}",
        }
        print(variant, json.dumps(out[variant]), flush=True)
    out["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    print(json.dumps(out, indent=1))
    if a.out:
        json.dump(out, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
