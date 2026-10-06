"""D6-S1 real-sandbox driver (kit script; THROWAWAY research code).

Real clock, real Worker, real D1/R2, real Cloudflare Email Service REST API. Time is compressed by using
a short staleness threshold (minutes, not 14 days) and a short dead-man's-switch threshold.

Validated only against the local emulator (`--mail-base mock` + `wrangler dev --local`), on 2026-09-29.
It has NOT been run against real Cloudflare yet; that is what the kit is for.

Example (sandbox):
  python3 run_real.py --cp https://d6s1.<sandbox>.workers.dev --admin-token $ADMIN --homelab-token $HOMELAB \
      --mail-base https://api.cloudflare.com --mail-account $ACCOUNT_ID --mail-token $EMAIL_TOKEN \
      --mail-from nudges@notify.<sandbox-domain> --people people.json --stale-min 30 --job-every-s 300 --outage-min 60
"""
import argparse, base64, datetime as dt, http.server, json, os, re, subprocess, sys, tempfile, threading, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SPIKE = os.path.normpath(os.path.join(HERE, "../../../../spikes/D6-S1"))
sys.path.insert(0, SPIKE)
from homelab import Homelab, http_json  # noqa: E402

MOCK = []


class Mock(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        b = json.loads(self.rfile.read(int(self.headers["content-length"])))
        MOCK.append({"t": time.time(), **b})
        self.send_response(200); self.send_header("content-type", "application/json"); self.end_headers()
        self.wfile.write(json.dumps({"success": True, "errors": [], "messages": [],
                                     "result": {"delivered": [b["to"]], "permanent_bounces": [], "queued": []}}).encode())

    def log_message(self, *a):
        pass


def utc(t):
    return dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def age_keygen(path):
    subprocess.run(["age-keygen", "-o", path], check=True, capture_output=True)
    return re.search(r"public key: (age1\w+)", open(path).read()).group(1)


def age_encrypt(recipient, obj):
    return subprocess.run(["age", "-r", recipient], input=json.dumps(obj).encode(), capture_output=True, check=True).stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cp", required=True)
    ap.add_argument("--admin-token", required=True)
    ap.add_argument("--homelab-token", required=True)
    ap.add_argument("--mail-base", required=True, help="https://api.cloudflare.com, or 'mock' for local validation")
    ap.add_argument("--mail-account", default="0" * 32)
    ap.add_argument("--mail-token", default="mock")
    ap.add_argument("--mail-from", required=True)
    ap.add_argument("--people", required=True, help='JSON list: [{"key","name","email","path":"R"|"A"}] (test inboxes only)')
    ap.add_argument("--stale-min", type=float, default=30)
    ap.add_argument("--job-every-s", type=float, default=300)
    ap.add_argument("--outage-min", type=float, default=60)
    ap.add_argument("--poke-scheduled", action="store_true", help="local only: call /__scheduled each loop")
    ap.add_argument("--out", default="results-run.json")
    a = ap.parse_args()

    if a.mail_base == "mock":
        srv = http.server.ThreadingHTTPServer(("127.0.0.1", 8796), Mock)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        a.mail_base = "http://127.0.0.1:8796"
        local = True
    else:
        local = False
    people = json.load(open(a.people))
    work = tempfile.mkdtemp(prefix="d6s1-homelab-")
    ident = os.path.join(work, "homelab-identity.txt")
    hpub = age_keygen(ident)
    hl = Homelab(os.path.join(work, "roster.db"), ident, a.cp, a.homelab_token, a.mail_base, a.mail_account,
                 a.mail_token, a.mail_from, int(a.stale_min * 60), sim_header=False)
    log = []

    def ev(kind, **kw):
        e = {"t": utc(time.time()), "event": kind, **kw}
        log.append(e); print(json.dumps(e), flush=True)

    def tick():
        before = len(hl.sent)
        hl.tick(int(time.time()))
        for kind, t, acct, dev in hl.sent[before:]:
            ev("homelab_sent_" + kind, account_id=acct, device_id=dev, homelab_time=utc(t))
        if a.poke_scheduled:
            urllib.request.urlopen(a.cp + "/__scheduled?cron=*+*+*+*+*", timeout=10).read()

    # 1. Enroll: one device per person. Path R sends the roster entry encrypted; path A is admin-entered.
    devs = {}
    for p in people:
        code = "KIT-" + base64.b32encode(os.urandom(10)).decode()
        st, r = http_json(a.cp + "/v1/admin/invites", {"code": code, "ttl_days": 1}, a.admin_token)
        assert st == 200, r
        if p["path"] == "A":
            hl.admin_add_person(r["invite_id"], p["name"], p["email"])
        entry = {"device_kind": "laptop"}
        if p["path"] == "R":
            entry.update(name=p["name"], email=p["email"])
        pub = age_keygen(os.path.join(work, f"{p['key']}-device.txt"))
        st, r = http_json(a.cp + "/v1/redeem", {"code": code, "device_pubkey": pub,
                                                 "roster_blob_b64": base64.b64encode(age_encrypt(hpub, entry)).decode()}, "none")
        assert st == 200, r
        devs[p["key"]] = r
        ev("enrolled", person=p["key"], path=p["path"], account_id=r["account_id"], device_id=r["device_id"])

    # 2. Verification by code (note F4 (a)): the homelab emails a code; the person types it into the "app".
    tick()
    for p in people:
        if local:
            code = re.search(r"app: (\d{6})", [m for m in MOCK if m["to"] == p["email"]][-1]["text"]).group(1)
        else:
            code = input(f"Code emailed to {p['email']} (type it; note the arrival time in the results sheet): ").strip()
        blob = base64.b64encode(age_encrypt(hpub, {"verify_code": code})).decode()
        st, r = http_json(a.cp + "/v1/inbox", {"blob_b64": blob}, devs[p["key"]]["device_token"])
        assert st == 200, r
        ev("code_submitted", person=p["key"])
    tick()

    # 3. Activity: the first person's device keeps committing; every other device commits once and stops.
    for i, p in enumerate(people):
        http_json(a.cp + "/v1/commit", {"object_id": f"kit-{p['key']}-0"}, devs[p["key"]]["device_token"])
        ev("commit", person=p["key"])
    stop_at = time.time() + a.stale_min * 60 + 3 * a.job_every_s
    n = 1
    while time.time() < stop_at:
        time.sleep(a.job_every_s)
        http_json(a.cp + "/v1/commit", {"object_id": f"kit-{people[0]['key']}-{n}"}, devs[people[0]["key"]]["device_token"])
        n += 1
        tick()

    # 4. Homelab outage: no pulls. The cloud dead-man's switch should email the owner only.
    ev("homelab_outage_start")
    end = time.time() + a.outage_min * 60
    while time.time() < end:
        time.sleep(min(a.job_every_s, 60))
        if a.poke_scheduled:
            urllib.request.urlopen(a.cp + "/__scheduled?cron=*+*+*+*+*", timeout=10).read()
    ev("homelab_outage_end")
    tick()

    json.dump({"args": {k: v for k, v in vars(a).items() if "token" not in k}, "events": log,
               "mock_mailbox": MOCK if local else "n/a (real run: record inbox arrival times by hand)"},
              open(a.out, "w"), indent=1)
    print(f"wrote {a.out}; homelab roster (test data) is in {work}: delete it after the run")


if __name__ == "__main__":
    main()
