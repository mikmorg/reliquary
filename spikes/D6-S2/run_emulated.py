"""D6-S2 emulated log audit. EMULATED, NOT REAL CLOUDFLARE.

Runs the probe Worker under `wrangler dev --local` with two observability configs and records which
local log surfaces (wrangler dev stdout, Miniflare local-explorer `logs`/`spans` tables) contain the
synthetic markers sent in the query string, a header, the body, a console.log and an exception.
The local explorer is NOT Workers Logs; this run only shows what the local toolchain records and is
not evidence about Cloudflare's hosted Workers Logs (that is the kit's job).
"""
import json, os, shutil, signal, subprocess, time, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
WR = os.path.join(HERE, "node_modules/.bin/wrangler")
PORT = 8797
BASE = f"http://127.0.0.1:{PORT}"
M = {  # one distinct synthetic marker per surface
    "query": "zz-d6s2-q@example.invalid",
    "header": "zz-d6s2-h@example.invalid",
    "body_clean": "zz-d6s2-bc@example.invalid",
    "body_leaky": "zz-d6s2-bl@example.invalid",
    "body_throw": "zz-d6s2-bt@example.invalid",
    "fake_client_ip": "203.0.113.77",
}
CONFIGS = {
    "invocation_logs_true": {"enabled": True, "logs": {"invocation_logs": True}},
    "invocation_logs_false": {"enabled": True, "logs": {"invocation_logs": False}},
    "observability_disabled": {"enabled": False},
}


def req(path, body=None, headers=None):
    r = urllib.request.Request(BASE + path, data=body.encode() if body else None, method="POST" if body else "GET")
    for k, v in (headers or {}).items():
        r.add_header(k, v)
    try:
        with urllib.request.urlopen(r, timeout=20) as x:
            return x.status, x.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def oq(sql):
    r = urllib.request.Request(BASE + "/cdn-cgi/local/explorer/api/local/observability/query",
                               data=json.dumps({"sql": sql}).encode(), headers={"content-type": "application/json"})
    try:
        return json.loads(urllib.request.urlopen(r, timeout=20).read())["result"]["rows"]
    except Exception as e:  # noqa: BLE001
        return f"query failed: {e}"


def run(name, obs):
    wd = os.path.join(HERE, "worker")
    cfg = {"name": "d6s2-log-probe", "main": "src/index.js", "compatibility_date": "2026-09-01", "observability": obs}
    json.dump(cfg, open(os.path.join(wd, "wrangler.json"), "w"), indent=1)
    shutil.rmtree(os.path.join(wd, ".wrangler"), ignore_errors=True)
    logp = os.path.join(HERE, "evidence", f"wrangler-dev-{name}.log")
    lf = open(logp, "w")
    p = subprocess.Popen([WR, "dev", "--local", "--port", str(PORT), "--ip", "127.0.0.1"], cwd=wd, stdout=lf,
                         stderr=subprocess.STDOUT, start_new_session=True,
                         env=dict(os.environ, WRANGLER_SEND_METRICS="false"))
    try:
        for _ in range(120):
            try:
                if req("/cf")[0] == 200:
                    break
            except Exception:
                pass
            time.sleep(1)
        cf = req("/cf", headers={"CF-Connecting-IP": M["fake_client_ip"]})
        out = {
            "clean": req("/clean", json.dumps({"device_id": "opaque-1234", "email": M["body_clean"]}))[0],
            "leaky": req("/leaky-console", json.dumps({"email": M["body_leaky"]}))[0],
            "throw": req("/throw", json.dumps({"email": M["body_throw"]}))[0],
            "query": req("/query?email=" + M["query"])[0],
            "header": req("/header", headers={"x-probe-email": M["header"], "CF-Connecting-IP": M["fake_client_ip"]})[0],
        }
        time.sleep(2)
        logs = oq("SELECT level, message FROM logs")
        spans = oq("SELECT name, kind, outcome, error, attributes FROM spans")
    finally:
        os.killpg(p.pid, signal.SIGTERM)
        p.wait(timeout=30)
        lf.close()
    devlog = open(logp).read()
    surfaces = {"wrangler_dev_stdout": devlog, "local_explorer_logs": json.dumps(logs),
                "local_explorer_spans": json.dumps(spans)}
    found = {s: sorted(k for k, v in M.items() if v in txt) for s, txt in surfaces.items()}
    return {"config": obs, "http_status": out, "cf_probe": cf, "markers_found_per_surface": found,
            "local_explorer_log_rows": logs if isinstance(logs, str) else len(logs),
            "local_explorer_span_rows": spans if isinstance(spans, str) else len(spans),
            "local_explorer_log_messages": logs if isinstance(logs, str) else [r[1] for r in logs]}


def main():
    shutil.rmtree(os.path.join(HERE, "evidence"), ignore_errors=True)
    os.makedirs(os.path.join(HERE, "evidence"))
    res = {"label": "EMULATED, not real Cloudflare: wrangler dev --local; local explorer is not Workers Logs",
           "wrangler_version": subprocess.run([WR, "--version"], capture_output=True, text=True).stdout.strip().splitlines()[-1],
           "markers": M, "runs": {n: run(n, c) for n, c in CONFIGS.items()}}
    json.dump(res, open(os.path.join(HERE, "evidence", "results.json"), "w"), indent=2)
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
