"""D6-S1 emulated run: minimal-PII variant (homelab holds the roster and sends nudges).

EMULATED, NOT REAL R2/CLOUDFLARE: the control plane runs in `wrangler dev --local` (workerd +
Miniflare's local D1/R2/send_email simulators); the Cloudflare Email Service REST endpoint is a local
mock that only records requests. All people, addresses and devices are synthetic (data class SYN).

Usage: python3 run_spike.py   (from this directory; needs node_modules/wrangler, the `age` CLI)
"""
import base64, datetime as dt, http.server, json, os, re, shutil, signal, subprocess, sys, threading, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from homelab import Homelab, http_json, HOUR  # noqa: E402

CP = "http://127.0.0.1:8799"
MAIL_PORT = 8798
ADMIN_TOKEN, HOMELAB_TOKEN = "synthetic-admin-token-d6s1", "synthetic-homelab-token-d6s1"
MAIL_ACCOUNT, MAIL_TOKEN = "00000000000000000000000000000d61", "synthetic-email-send-token-d6s1"
OWNER = "zz-d6s1-owner@example.invalid"
STALE_AFTER = 14 * 86400        # ADR-0002 example ("hasn't backed up in 14 days"); E3 owns the real value
NUDGE_WITHIN = 24 * HOUR        # PLAN D6-S1 pass criterion
T0 = int(dt.datetime(2026, 10, 5, tzinfo=dt.timezone.utc).timestamp())
DAYS = 26
OUTAGE = (20 * 24, 22 * 24 + 6)  # homelab down [start, end) in sim hours
EV = os.path.join(HERE, "evidence")

PEOPLE = {  # synthetic only
    "alpha": ("Zzalpha Synthperson", "zz-d6s1-alpha@example.invalid", "R"),
    "beta": ("Zzbeta Synthperson", "zz-d6s1-beta@example.invalid", "R"),
    "gamma": ("Zzgamma Synthperson", "zz-d6s1-gamma@example.invalid", "A"),  # admin-entered at the homelab
    "delta": ("Zzdelta Synthperson", "zz-d6s1-delta@example.invalid", "R"),  # never verifies
}
# device: (person, kind, heartbeat hours, commit hour, last commit day (None = never stops), stop heartbeat after stop)
DEVICES = {
    "alpha-laptop": ("alpha", "laptop", range(8, 23), 20, None, False),
    "alpha-phone": ("alpha", "phone", range(0, 24), 14, 6, True),    # lost phone: stale during the outage
    "beta-laptop": ("beta", "laptop", range(9, 22), 21, 3, False),   # online but backups failing
    "gamma-phone": ("gamma", "phone", range(0, 24), 12, 8, True),
    "delta-laptop": ("delta", "laptop", range(9, 18), 17, 2, True),
}
FAMILY_MARKERS = [p[0] for p in PEOPLE.values()] + [p[0].split()[0] for p in PEOPLE.values()] + \
    [p[1] for p in PEOPLE.values()] + [p[1].split("@")[0] for p in PEOPLE.values()] + ["Synthperson"]
OWNER_MARKERS = [OWNER, OWNER.split("@")[0]]

mailbox = []  # recorded REST calls (mock)


class MockEmail(http.server.BaseHTTPRequestHandler):
    """Records POST /client/v4/accounts/{id}/email/sending/send (request/response shape per rest-api.mdx)."""
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["content-length"])))
        ok_path = re.fullmatch(r"/client/v4/accounts/([0-9a-f]+)/email/sending/send", self.path)
        if not ok_path or self.headers.get("authorization") != f"Bearer {MAIL_TOKEN}":
            self.send_response(401); self.end_headers()
            self.wfile.write(json.dumps({"success": False, "errors": [{"code": 10101}], "result": None}).encode()); return
        mailbox.append({"sim_now": int(self.headers.get("x-sim-now", 0)), **body})
        self.send_response(200); self.send_header("content-type", "application/json"); self.end_headers()
        self.wfile.write(json.dumps({"success": True, "errors": [], "messages": [],
                                     "result": {"delivered": [body["to"]], "permanent_bounces": [], "queued": []}}).encode())

    def log_message(self, *a):
        pass


def age_keygen(path):
    subprocess.run(["age-keygen", "-o", path], check=True, capture_output=True)
    return re.search(r"public key: (age1\w+)", open(path).read()).group(1)


def age_encrypt(recipient, obj):
    return subprocess.run(["age", "-r", recipient], input=json.dumps(obj).encode(), capture_output=True, check=True).stdout


def post(path, body, token=None):
    return http_json(CP + path, body, token or "none")


def iso(t):
    return dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def scan_bytes(data, markers):
    low = data.lower()
    return sorted({m for m in markers if m.lower().encode() in low})


def scan_tree(root, markers):
    hits = {}
    for dp, _, fns in os.walk(root):
        for fn in fns:
            fp = os.path.join(dp, fn)
            try:
                h = scan_bytes(open(fp, "rb").read(), markers)
            except OSError:
                continue
            if h:
                hits[os.path.relpath(fp, HERE)] = h
    return hits


def main():
    for d in ("state", "worker/.wrangler", "homelab-data", "evidence"):
        shutil.rmtree(os.path.join(HERE, d), ignore_errors=True)
    os.makedirs(EV); os.makedirs(os.path.join(HERE, "homelab-data"))
    env = dict(os.environ, WRANGLER_SEND_METRICS="false")
    wr = os.path.join(HERE, "node_modules/.bin/wrangler")
    subprocess.run([wr, "d1", "migrations", "apply", "d6s1", "--local", "--persist-to", "../state"],
                   cwd=os.path.join(HERE, "worker"), env=env, check=True, capture_output=True)
    devlog = open(os.path.join(EV, "wrangler-dev.log"), "w")
    dev = subprocess.Popen([wr, "dev", "--local", "--persist-to", "../state", "--port", "8799", "--ip", "127.0.0.1",
                            "--test-scheduled"], cwd=os.path.join(HERE, "worker"), env=env, stdout=devlog,
                           stderr=subprocess.STDOUT, start_new_session=True)
    import atexit
    def _kill():
        try:
            os.killpg(dev.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    atexit.register(_kill)
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", MAIL_PORT), MockEmail)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    for _ in range(120):
        try:
            st, _r = post("/v1/sim/now", {"now": T0})
            if st == 200:
                break
        except Exception:
            pass
        time.sleep(1)
    else:
        raise SystemExit("wrangler dev did not come up")
    wall0 = time.time()
    homelab_pub = age_keygen(os.path.join(HERE, "homelab-data/homelab-identity.txt"))
    hl = Homelab(os.path.join(HERE, "homelab-data/roster.db"), os.path.join(HERE, "homelab-data/homelab-identity.txt"),
                 CP, HOMELAB_TOKEN, f"http://127.0.0.1:{MAIL_PORT}", MAIL_ACCOUNT, MAIL_TOKEN,
                 "nudges@notify.d6s1.example.invalid", STALE_AFTER)
    checks = {}
    dev_state = {}      # device -> {token, account_id, device_id}
    last_commit = {}    # device -> sim time of last commit (ground truth, device side)
    used_codes = set()
    dms_fired = []
    requests = 0

    for h in range(DAYS * 24):
        now = T0 + h * HOUR
        day, hod = divmod(h, 24)
        if hod == 0:
            print(f"sim day {day} wall {time.time() - wall0:.0f}s", file=sys.stderr, flush=True)
        post("/v1/sim/now", {"now": now}); requests += 1
        if h == 9:
            for key, (name, email, path) in PEOPLE.items():
                code = f"SYNTH-{key.upper()}-CODE"
                st, r = post("/v1/admin/invites", {"code": code, "ttl_days": 30}, ADMIN_TOKEN); requests += 1
                assert st == 200, r
                PEOPLE[key] = (name, email, path, code, r["invite_id"])
                if path == "A":
                    hl.admin_add_person(r["invite_id"], name, email)
            st, r = post("/v1/sim/try-send-other", {"to": "zz-d6s1-not-owner@example.invalid"})
            checks["local_pin_blocks_non_owner_recipient"] = {"http": st, **r}
            st, r = post("/v1/sim/try-send-other", {})
            checks["local_send_with_to_omitted"] = {"http": st, **(r if isinstance(r, dict) else {})}
            # Negative test: the Worker must refuse a plaintext roster blob.
            st, r = post("/v1/redeem", {"code": PEOPLE["delta"][3], "device_pubkey": "x",
                                        "roster_blob_b64": base64.b64encode(json.dumps({"name": "plaintext"}).encode()).decode()})
            checks["plaintext_roster_blob_rejected"] = {"http": st, "response": r,
                                                        "pass": st == 400 and r.get("error") == "roster_blob_must_be_age_ciphertext"}
        if h == 10 or h == 11:
            for dname, (pkey, kind, *_rest) in DEVICES.items():
                first = dname in ("alpha-laptop", "beta-laptop", "gamma-phone", "delta-laptop")
                if (h == 10) != first or dname in dev_state:
                    continue
                pub = age_keygen(os.path.join(HERE, f"homelab-data/{dname}-device-identity.txt"))
                name, email, path, code, _ = PEOPLE[pkey]
                entry = {"device_kind": kind}
                if first and path == "R":
                    entry.update(name=name, email=email)
                blob = base64.b64encode(age_encrypt(homelab_pub, entry)).decode()
                if first:
                    st, r = post("/v1/redeem", {"code": code, "device_pubkey": pub, "roster_blob_b64": blob})
                else:
                    st, r = post("/v1/device/add", {"device_pubkey": pub, "roster_blob_b64": blob},
                                 dev_state["alpha-laptop"]["device_token"])
                requests += 1
                assert st == 200, (dname, r)
                dev_state[dname] = r
        # device activity
        for dname, (pkey, kind, hb_hours, c_hour, stop_day, hb_stops) in DEVICES.items():
            if dname not in dev_state:
                continue
            stopped = stop_day is not None and (day > stop_day or (day == stop_day and hod > c_hour))
            tok = dev_state[dname]["device_token"]
            if hod == c_hour and not stopped and h > 11:
                st, _ = post("/v1/commit", {"object_id": f"hmac-{dname}-{day}"}, tok); requests += 1
                last_commit[dname] = now
            elif hod in hb_hours and not (stopped and hb_stops):
                post("/v1/heartbeat", {}, tok); requests += 1
        # people read their (mock) mailbox and type the code into the app (not delta)
        for pkey, (name, email, *_x) in PEOPLE.items():
            if pkey == "delta":
                continue
            for m in mailbox:
                if m["to"] == email and m["subject"] == "Your Reliquary code" and id(m) not in used_codes:
                    code = re.search(r"app: (\d{6})", m["text"]).group(1)
                    dname = next(d for d, v in DEVICES.items() if v[0] == pkey and d in dev_state)
                    blob = base64.b64encode(age_encrypt(homelab_pub, {"verify_code": code})).decode()
                    st, _ = post("/v1/inbox", {"blob_b64": blob}, dev_state[dname]["device_token"]); requests += 1
                    used_codes.add(id(m))
        homelab_up = not (OUTAGE[0] <= h < OUTAGE[1])
        if homelab_up:
            hl.tick(now); requests += 2
        st, r = http_json(CP + "/v1/sim/run-dms", {}, "none"); requests += 1
        if r.get("fired"):
            dms_fired.append({"sim_now": iso(now), "silent_hours": r["silentH"]})

    # Also exercise the real scheduled() entry point once (same code path as the cron trigger).
    urllib.request.urlopen(CP + "/__scheduled?cron=0+*+*+*+*", timeout=10).read()
    wall = time.time() - wall0

    # ---------------- measurements ----------------
    dev_by_id = {v["device_id"]: k for k, v in dev_state.items()}
    nudges = [(t, dev_by_id[d]) for kind, t, a, d in hl.sent if kind == "nudge"]
    rows = []
    for dname in DEVICES:
        if dname not in last_commit:
            continue
        crossed = last_commit[dname] + STALE_AFTER
        if crossed >= T0 + DAYS * 86400:
            rows.append({"device": dname, "stale_at": None, "note": "not stale within the run"}); continue
        sent = [t for t, d in nudges if d == dname]
        in_outage = OUTAGE[0] <= (crossed - T0) // HOUR < OUTAGE[1]
        rows.append({"device": dname, "last_commit": iso(last_commit[dname]), "stale_at": iso(crossed),
                     "nudge_sent_at": iso(sent[0]) if sent else None,
                     "delay_hours": (sent[0] - crossed) / HOUR if sent else None,
                     "homelab_down_at_crossing": in_outage,
                     "person_verified": DEVICES[dname][0] != "delta"})
    # local observability store (Miniflare local explorer) - emulated stand-in for Workers Logs
    q = CP + "/cdn-cgi/local/explorer/api/local/observability/query"
    def oq(sql):
        rq = urllib.request.Request(q, data=json.dumps({"sql": sql}).encode(), headers={"content-type": "application/json"})
        return json.loads(urllib.request.urlopen(rq, timeout=30).read())["result"]["rows"]
    obs_logs = oq("SELECT level, message FROM logs")
    obs_spans = oq("SELECT name, kind, attributes FROM spans")
    obs_blob = json.dumps([obs_logs, obs_spans]).encode()

    alert_dir = os.path.join(EV, "owner-alert-emails")
    os.makedirs(alert_dir, exist_ok=True)
    for dp, _, fs in os.walk(os.path.join(HERE, "worker/.wrangler/tmp")):
        for f in fs:
            if "email" in dp:
                shutil.copy(os.path.join(dp, f), os.path.join(alert_dir, os.path.basename(dp) + "__" + f))
    _kill(); dev.wait(timeout=30); srv.shutdown(); devlog.close()
    # `wrangler d1 export --local` has no --persist-to, so dump Miniflare's D1 SQLite file(s) directly.
    import sqlite3, glob
    dumps = []
    for f in sorted(glob.glob(os.path.join(HERE, "state/v3/d1/**/*.sqlite"), recursive=True)):
        con = sqlite3.connect(f)
        dumps.append(f"-- {os.path.relpath(f, HERE)}\n" + "\n".join(con.iterdump()))
        con.close()
    open(os.path.join(EV, "d1-export.sql"), "w").write("\n".join(dumps))
    d1_sql = open(os.path.join(EV, "d1-export.sql"), "rb").read()
    schema = re.findall(rb"CREATE TABLE[^;]+;", d1_sql)
    results = {
        "label": "EMULATED, not real R2/Cloudflare: wrangler dev --local (workerd + Miniflare local D1/R2/send_email); email REST endpoint is a local mock",
        "wrangler_version": subprocess.run([wr, "--version"], capture_output=True, text=True, env=env).stdout.strip().splitlines()[-1],
        "age_version": subprocess.run(["age", "--version"], capture_output=True, text=True).stdout.strip(),
        "sim_period": [iso(T0), iso(T0 + DAYS * 86400)], "stale_after_days": STALE_AFTER / 86400,
        "homelab_outage": [iso(T0 + OUTAGE[0] * HOUR), iso(T0 + OUTAGE[1] * HOUR)],
        "wall_clock_seconds": round(wall, 1), "http_requests_to_worker_approx": requests,
        "checks": checks,
        "d1_schema": [s.decode() for s in schema],
        "family_markers_in_d1_export": scan_bytes(d1_sql, FAMILY_MARKERS),
        "owner_markers_in_d1_export": scan_bytes(d1_sql, OWNER_MARKERS),
        "family_markers_in_local_cloud_state_files": scan_tree(os.path.join(HERE, "state"), FAMILY_MARKERS),
        "family_markers_in_worker_dot_wrangler": scan_tree(os.path.join(HERE, "worker/.wrangler"), FAMILY_MARKERS),
        "owner_markers_in_worker_dot_wrangler": scan_tree(os.path.join(HERE, "worker/.wrangler"), OWNER_MARKERS),
        "family_markers_in_wrangler_dev_log": scan_bytes(open(os.path.join(EV, "wrangler-dev.log"), "rb").read(), FAMILY_MARKERS),
        "family_markers_in_local_observability": scan_bytes(obs_blob, FAMILY_MARKERS),
        "local_observability_rows": {"logs": len(obs_logs), "spans": len(obs_spans)},
        "local_observability_log_message_samples": sorted({r[1] for r in obs_logs})[:12],
        "positive_control_family_markers_in_homelab_roster_db": scan_bytes(
            open(os.path.join(HERE, "homelab-data/roster.db"), "rb").read(), FAMILY_MARKERS),
        "emails_sent_by_homelab": {"verify": sum(1 for s in hl.sent if s[0] == "verify"),
                                   "nudge": sum(1 for s in hl.sent if s[0] == "nudge")},
        "nudge_rows": rows,
        "dead_mans_switch_fired": dms_fired,
        "owner_alert_email_files": sorted(os.listdir(os.path.join(EV, "owner-alert-emails"))),
        "family_markers_in_owner_alert_emails": scan_tree(os.path.join(EV, "owner-alert-emails"), FAMILY_MARKERS),
        "owner_markers_in_owner_alert_emails": scan_tree(os.path.join(EV, "owner-alert-emails"), OWNER_MARKERS),
    }
    up_rows = [r for r in rows if r.get("stale_at") and r["person_verified"] and not r["homelab_down_at_crossing"]]
    app_cols = {}
    for f in sorted(glob.glob(os.path.join(HERE, "state/v3/d1/**/*.sqlite"), recursive=True)):
        con = sqlite3.connect(f)
        for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type='table'"):
            if t.startswith("_cf_") or t in ("d1_migrations", "sqlite_sequence"):
                continue
            app_cols[t] = [c[1] for c in con.execute(f"PRAGMA table_info('{t}')")]
        con.close()
    results["d1_app_table_columns"] = app_cols
    results["d1_pii_like_columns"] = [f"{t}.{c}" for t, cs in app_cols.items() for c in cs
                                      if re.search(r"name|mail|phone|addr|person|label", c, re.I)]
    results["pass_d1_no_name_or_email"] = not results["family_markers_in_d1_export"] \
        and not results["family_markers_in_local_cloud_state_files"] and not results["d1_pii_like_columns"]
    results["pass_nudge_within_24h_while_homelab_up"] = bool(up_rows) and all(
        r["delay_hours"] is not None and 0 <= r["delay_hours"] <= NUDGE_WITHIN / HOUR for r in up_rows)
    json.dump(results, open(os.path.join(EV, "results.json"), "w"), indent=2)
    json.dump([{k: v for k, v in m.items()} for m in mailbox], open(os.path.join(EV, "mock-mailbox-SYN.json"), "w"), indent=1)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
