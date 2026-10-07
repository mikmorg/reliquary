#!/usr/bin/env python3
"""C1-S2 lease race (EMULATED leg when pointed at wrangler dev; throwaway research code, stdlib only).

For each trial, N threads (one per simulated device) fire one lease request for the same fresh
dedup ID at the same moment (a barrier releases them together). Exactly one must win. Every
`takeover_every`-th trial first plants an expired lease, so the race is a takeover race.
After all trials the store is checked for any dedup ID with more than one live lease.

  python3 c1s2.py --worker http://127.0.0.1:8787 --store d1|do --concurrency 50 --trials 10000 --out r.json
"""
import argparse, http.client, json, os, statistics, threading, time, urllib.parse, uuid


def pct(xs, p):
    xs = sorted(xs)
    if not xs:
        return None
    k = (len(xs) - 1) * p / 100
    f = int(k)
    c = min(f + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--worker", required=True)
    ap.add_argument("--store", choices=["d1", "do"], required=True)
    ap.add_argument("--concurrency", type=int, default=50)
    ap.add_argument("--trials", type=int, default=10000)
    ap.add_argument("--takeover-every", type=int, default=10)
    ap.add_argument("--out")
    a = ap.parse_args()
    u = urllib.parse.urlsplit(a.worker)
    host = u.netloc

    hdrs = {"x-spike-token": os.environ["SPIKE_TOKEN"]} if os.environ.get("SPIKE_TOKEN") else {}

    def conn():
        cls = http.client.HTTPSConnection if u.scheme == "https" else http.client.HTTPConnection
        return cls(host, timeout=120)

    c0 = conn()

    def get(c, path):
        c.request("GET", path, headers=hdrs)
        r = c.getresponse()
        return r.status, json.loads(r.read())

    if a.store == "d1":
        print(get(c0, "/d1/init"))
    else:
        print(get(c0, "/do/reset"))

    n = a.concurrency
    barrier = threading.Barrier(n + 1)
    run = uuid.uuid4().hex[:6]
    state = {"dedup": None, "stop": False}
    results = [None] * n
    lat_ms = []
    lat_lock = threading.Lock()
    errors = []

    def worker(i):
        c = conn()
        while True:
            barrier.wait()
            if state["stop"]:
                return
            d = state["dedup"]
            t0 = time.perf_counter()
            try:
                st, j = get(c, f"/{a.store}/lease?dedup={d}&device=dev{i}&ttl=600000")
                results[i] = (st, bool(j.get("won")))
            except Exception as e:
                results[i] = (0, False)
                errors.append(f"{type(e).__name__}: {e}")
                c = conn()
            dt_ = (time.perf_counter() - t0) * 1000
            with lat_lock:
                lat_ms.append(dt_)
            barrier.wait()

    ths = [threading.Thread(target=worker, args=(i,), daemon=True) for i in range(n)]
    for t in ths:
        t.start()

    winners_hist = {}
    bad_trials = []
    non200 = 0
    t_start = time.time()
    for trial in range(a.trials):
        d = f"{os.urandom(1).hex()[0]}{run}{trial:06d}"  # first hex char spreads DO shards
        if a.takeover_every and trial % a.takeover_every == 0:
            get(c0, f"/{a.store}/lease?dedup={d}&device=old&ttl=1")
            get(c0, f"/{a.store}/expire?dedup={d}")
        state["dedup"] = d
        barrier.wait()   # release
        barrier.wait()   # all done
        w = sum(1 for r in results if r and r[1])
        non200 += sum(1 for r in results if r and r[0] != 200)
        winners_hist[w] = winners_hist.get(w, 0) + 1
        if w != 1:
            bad_trials.append({"trial": trial, "winners": w, "statuses": [r[0] for r in results]})
        if trial % 1000 == 0:
            print(f"trial {trial} winners {w} elapsed {time.time() - t_start:.0f}s", flush=True)
    state["stop"] = True
    barrier.wait()
    wall = time.time() - t_start
    st, dup = get(c0, f"/{a.store}/dupcheck")
    out = {"store": a.store, "concurrency": n, "trials": a.trials, "takeover_every": a.takeover_every,
           "winners_histogram": winners_hist, "bad_trials": bad_trials[:20], "bad_trial_count": len(bad_trials),
           "non200_responses": non200, "client_errors": errors[:10], "client_error_count": len(errors),
           "post_check": dup, "wall_s": round(wall, 1), "requests": n * a.trials,
           "latency_ms": {"p50": round(pct(lat_ms, 50), 2), "p99": round(pct(lat_ms, 99), 2), "max": round(max(lat_ms), 2),
                          "mean": round(statistics.fmean(lat_ms), 2)},
           "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    print(json.dumps(out, indent=1))
    if a.out:
        json.dump(out, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
