#!/usr/bin/env python3
"""C1-S4 presign 200 UploadPart URLs in one request, and check the URLs work (throwaway, stdlib only).

EMULATED when pointed at wrangler dev. The kit points it at the sandbox Worker; CPU time on real
Workers comes from the dashboard / Workers Observability (cpu_time), not from this script.

  python3 c1s4.py --worker http://127.0.0.1:8787 --s3-base http://127.0.0.1:8787 --reps 50 --out r.json
"""
import argparse, hashlib, json, os, statistics, subprocess, time, urllib.parse, urllib.request

MiB = 1024 * 1024


def get(base, path, body=None):
    req = urllib.request.Request(base + path, data=body, method="POST" if body is not None else "GET")
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=300) as r:
        out = json.loads(r.read())
    return out, (time.perf_counter() - t0) * 1000


def pct(xs, p):
    xs = sorted(xs)
    k = (len(xs) - 1) * p / 100
    f = int(k); c = min(f + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)


def summary(xs):
    return {"p50": round(pct(xs, 50), 2), "p99": round(pct(xs, 99), 2), "max": round(max(xs), 2), "n": len(xs)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--worker", required=True)
    ap.add_argument("--reps", type=int, default=50)
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--verify-n", type=int, default=10000)
    ap.add_argument("--out")
    a = ap.parse_args()
    b = a.worker
    out = {"n_parts": a.n}
    # baseline and presign-many timing
    base_ms, many_ms, many_perf = [], [], []
    for _ in range(a.reps):
        base_ms.append(get(b, "/noop")[1])
        j, ms = get(b, f"/presign-many?n={a.n}&key=c1s4/timing&uploadId=x&urls=0")
        many_ms.append(ms)
        many_perf.append(j["perf_ms"])
    out["noop_client_ms"] = summary(base_ms)
    out["presign_many_client_ms"] = summary(many_ms)
    out["presign_many_in_worker_perf_ms"] = summary(many_perf)
    # Ed25519 verify cost (BUD-CPU-REQ proxy)
    ev = []
    for _ in range(5):
        j, _ms = get(b, f"/bench/ed25519?n={a.verify_n}")
        ev.append(j["perf_ms"] / a.verify_n)
    out["ed25519_verify_ms_each_in_worker"] = {"runs": [round(x, 5) for x in ev], "verifies_per_run": a.verify_n}
    # URLs work from curl: binding creates the upload; presign 200 parts; curl parts 1, 2 and 200; binding completes
    key = f"c1s4/{os.urandom(4).hex()}/obj"
    up, _ = get(b, f"/b/mpu-create?key={key}")
    uid = up["uploadId"]
    j, ms = get(b, f"/presign-many?n={a.n}&key={urllib.parse.quote(key)}&uploadId={urllib.parse.quote(uid)}&expires=900")
    urls = j["urls"]
    out["one_call_with_urls"] = {"client_ms": round(ms, 1), "in_worker_perf_ms": j["perf_ms"],
                                 "response_bytes": len(json.dumps(j)), "unique_urls": len(set(urls)),
                                 "max_url_len": max(len(u) for u in urls)}
    parts, blobs, curl_status = [], [], {}
    for pn, size in ((1, 5 * MiB), (2, 5 * MiB), (a.n, 777)):
        d = os.urandom(size)
        path = f"/tmp/c1s4-part-{pn}"
        open(path, "wb").write(d)
        r = subprocess.run(["curl", "-s", "-o", "/dev/null", "-D", "-", "-X", "PUT", "--data-binary", f"@{path}",
                            "-H", "content-type:", urls[pn - 1]], capture_output=True, text=True)
        os.remove(path)
        lines = r.stdout.splitlines()
        status = lines[0] if lines else "none"
        etag = next((l.split(":", 1)[1].strip() for l in lines if l.lower().startswith("etag:")), "")
        curl_status[pn] = status
        parts.append({"partNumber": pn, "etag": etag.strip('"')})
        blobs.append(d)
    done, _ = get(b, f"/b/mpu-complete?key={urllib.parse.quote(key)}",
                  json.dumps({"uploadId": uid, "parts": parts}).encode())
    rb, _ = get(b, f"/b/head?key={urllib.parse.quote(key)}")
    out["curl_check"] = {"part_status": curl_status, "complete": done, "size_ok": rb.get("size") == sum(len(x) for x in blobs)}
    out["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    print(json.dumps(out, indent=1))
    if a.out:
        json.dump(out, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
