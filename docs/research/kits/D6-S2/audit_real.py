#!/usr/bin/env python3
"""D6-S2 kit driver: audit what hosted Cloudflare Workers observability keeps for one config variant.

THROWAWAY research code for the SANDBOX account only (never production). Standard library only.

One run = one config variant (V0..V3) already deployed with `wrangler deploy --config wrangler.<V>.jsonc`.
The script:
  1. asks the probe Worker (/whoami) which client IP Cloudflare saw (kept in memory and in the local
     raw folder only; never printed),
  2. sends one request per route, each carrying a fresh synthetic marker in exactly one place,
  3. waits for ingestion, then queries the Workers Observability REST API
     (POST /accounts/{id}/workers/observability/telemetry/query, path taken from the official
     `cloudflare` npm SDK 7.3.0, resources/workers/observability/telemetry.js) for the events,
     invocations and traces views, plus the keys endpoint,
  4. searches every raw API response, and an optional `wrangler tail --format json` capture,
     for each marker and for the client IP,
  5. prints a results JSON that holds only booleans, counts and field NAMES (no values), safe to paste.

Raw API output (which may hold the owner's IP and the synthetic markers) goes to --raw-dir and must be
deleted after the results are filled in (kit README, "Cleaning up").

Usage:
  python3 audit_real.py --variant V1 --worker-url https://d6s2-probe.<sub>.workers.dev \
      --account <sandbox account id> --api-token <token> [--tail-file tail-V1.json] [--wait-min 5]
  python3 audit_real.py --variant L --worker-url http://127.0.0.1:8797 --no-api --tail-file dev.log
      (local rehearsal against `wrangler dev`; tests the driver only, says nothing about Cloudflare)
"""
import argparse, json, os, re, secrets, sys, time, urllib.error, urllib.request

API = "https://api.cloudflare.com/client/v4"
SCRIPT = "d6s2-probe"
# Field-name patterns worth reporting (names only, never values).
INTERESTING = re.compile(r"(ip|addr|connecting|asn|city|locality|region|postal|latitude|longitude|"
                         r"user.?agent|country|colo|url|query|path|header|tls|email|asOrganization)", re.I)


def http(method, url, body=None, headers=None, timeout=30):
    data = json.dumps(body).encode() if isinstance(body, (dict, list)) else (body.encode() if body else None)
    r = urllib.request.Request(url, data=data, method=method)
    for k, v in (headers or {}).items():
        r.add_header(k, v)
    if isinstance(body, (dict, list)):
        r.add_header("content-type", "application/json")
    try:
        with urllib.request.urlopen(r, timeout=timeout) as x:
            return x.status, x.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return 0, f"{type(e).__name__}: {e}"


def markers(variant):
    tag = secrets.token_hex(3)
    m = {k: f"zz-d6s2-{variant.lower()}-{tag}-{k}@example.invalid" for k in
         ("query", "path", "header", "ua", "body_clean", "body_leaky", "body_structured", "body_throw", "body_caught")}
    m["path"] = m["path"].replace("@", "-at-")  # keep the path segment URL-safe
    return m


def send(base, m):
    """One request per placement. Returns HTTP status per route (no data)."""
    s = {}
    s["clean"] = http("POST", base + "/clean", json.dumps({"device_id": "opaque-1234", "email": m["body_clean"]}))[0]
    s["leaky_console"] = http("POST", base + "/leaky-console", json.dumps({"email": m["body_leaky"]}))[0]
    s["leaky_structured"] = http("POST", base + "/leaky-structured", json.dumps({"email": m["body_structured"]}))[0]
    s["throw"] = http("POST", base + "/throw", json.dumps({"email": m["body_throw"]}))[0]
    s["caught"] = http("POST", base + "/caught", json.dumps({"email": m["body_caught"]}))[0]
    s["query"] = http("GET", base + "/query?email=" + m["query"])[0]
    s["path"] = http("GET", base + "/path/" + m["path"])[0]
    s["header"] = http("GET", base + "/header", headers={"X-Probe-Email": m["header"]})[0]
    s["ua"] = http("GET", base + "/ua", headers={"User-Agent": "d6s2-probe " + m["ua"]})[0]
    st, cf = http("GET", base + "/cf")
    s["cf"] = st
    try:
        cf_info = json.loads(cf)
    except Exception:  # noqa: BLE001
        cf_info = {}
    return s, cf_info


def flatten_keys(obj, prefix="", out=None):
    out = set() if out is None else out
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{prefix}.{k}" if prefix else str(k)
            out.add(p)
            flatten_keys(v, p, out)
    elif isinstance(obj, list):
        for v in obj:
            flatten_keys(v, prefix + "[]", out)
    return out


def api_queries(acc, token, t0, t1):
    h = {"Authorization": f"Bearer {token}"}
    url = f"{API}/accounts/{acc}/workers/observability/telemetry"
    flt = [{"key": "$metadata.service", "operation": "=", "type": "string", "value": SCRIPT}]
    out = {}
    for view in ("events", "invocations", "traces"):
        body = {"queryId": f"d6s2-adhoc-{view}", "timeframe": {"from": t0, "to": t1}, "view": view,
                "limit": 2000, "dry": True, "parameters": {"filters": flt}}
        st, txt = http("POST", url + "/query", body, h, timeout=60)
        if st >= 400 or st == 0:  # retry without the service filter; the timeframe still bounds it
            body["parameters"] = {}
            st2, txt2 = http("POST", url + "/query", body, h, timeout=60)
            out[view] = {"status": st2, "status_with_filter": st, "text": txt2}
        else:
            out[view] = {"status": st, "text": txt}
    st, txt = http("POST", url + "/keys", {"from": t0, "to": t1, "limit": 1000}, h, timeout=60)
    out["keys"] = {"status": st, "text": txt}
    return out


def summarise_api(resp):
    """Counts and field names only."""
    s = {}
    for view, r in resp.items():
        d = {"http_status": r["status"]}
        if "status_with_filter" in r:
            d["http_status_with_service_filter"] = r["status_with_filter"]
        try:
            j = json.loads(r["text"])
        except Exception:  # noqa: BLE001
            d["parse_error"] = True
            s[view] = d
            continue
        d["api_success"] = j.get("success")
        res = j.get("result")
        if view == "events" and isinstance(res, dict):
            ev = (res.get("events") or {}).get("events") or []
            d["event_count"] = len(ev)
            keys = set()
            for e in ev:
                keys |= flatten_keys(e)
            d["interesting_field_names"] = sorted(k for k in keys if INTERESTING.search(k))
            d["all_field_name_count"] = len(keys)
        elif view == "invocations" and isinstance(res, dict):
            inv = res.get("invocations") or {}
            d["invocation_groups"] = len(inv)
        elif view == "traces" and isinstance(res, dict):
            d["trace_count"] = len(res.get("traces") or [])
        elif view == "keys":
            names = [k.get("key") for k in (res or []) if isinstance(k, dict) and k.get("key")]
            d["key_count"] = len(names)
            d["interesting_key_names"] = sorted(n for n in names if INTERESTING.search(n))
        if not j.get("success", True):
            d["api_errors"] = [e.get("code") for e in (j.get("errors") or []) if isinstance(e, dict)]
        s[view] = d
    return s


def scan(text, m, ip):
    found = sorted(k for k, v in m.items() if v in text)
    return {"markers_found": found, "client_ip_found": bool(ip) and ip in text}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", required=True, help="V0, V1, V2, V3 (or L for a local rehearsal)")
    ap.add_argument("--worker-url", required=True)
    ap.add_argument("--account")
    ap.add_argument("--api-token")
    ap.add_argument("--no-api", action="store_true", help="skip the REST queries (local rehearsal)")
    ap.add_argument("--tail-file", help="wrangler tail --format json capture (or wrangler dev log) to scan")
    ap.add_argument("--wait-min", type=float, default=5.0, help="minutes to wait for ingestion before querying")
    ap.add_argument("--raw-dir", default="raw-d6s2", help="local folder for raw API output (delete after)")
    a = ap.parse_args()
    if not a.no_api and not (a.account and a.api_token):
        sys.exit("--account and --api-token are required unless --no-api")
    base = a.worker_url.rstrip("/")
    os.makedirs(a.raw_dir, exist_ok=True)

    st, who = http("GET", base + "/whoami")
    try:
        ip = json.loads(who).get("ip", "")
    except Exception:  # noqa: BLE001
        ip = ""
    m = markers(a.variant)
    t0 = int(time.time() * 1000) - 120_000
    statuses, cf_info = send(base, m)
    json.dump({"markers": m, "client_ip": ip}, open(os.path.join(a.raw_dir, f"secrets-{a.variant}.json"), "w"))
    print(f"[d6s2] sent probes for {a.variant}; waiting {a.wait_min} min for ingestion", file=sys.stderr)
    time.sleep(a.wait_min * 60)
    t1 = int(time.time() * 1000) + 60_000

    result = {
        "label": "REAL Cloudflare sandbox" if not a.no_api else "LOCAL REHEARSAL (driver test only, not Cloudflare)",
        "variant": a.variant,
        "whoami_status": st,
        "client_ip_seen_by_worker": bool(ip),
        "client_ip_family": ("v6" if ":" in ip else "v4") if ip else None,
        "route_http_status": statuses,
        "request_cf_keys_visible_to_code": cf_info.get("cf_keys"),
        "marker_names": sorted(m),
    }
    if not a.no_api:
        resp = api_queries(a.account, a.api_token, t0, t1)
        json.dump(resp, open(os.path.join(a.raw_dir, f"api-{a.variant}.json"), "w"))
        result["api"] = summarise_api(resp)
        result["api_scan"] = {v: scan(r["text"], m, ip) for v, r in resp.items()}
    if a.tail_file:
        try:
            txt = open(a.tail_file, encoding="utf-8", errors="replace").read()
            result["tail_scan"] = scan(txt, m, ip)
            result["tail_bytes"] = len(txt)
        except OSError as e:
            result["tail_scan"] = {"error": str(e)}
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
