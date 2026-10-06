"""D6-S1 homelab nudge job (THROWAWAY spike code, emulated).

The homelab is the only place that holds names and email addresses (the "roster"). It makes
outbound calls only: it pulls commits, device last-seen times and age-encrypted inbox blobs from the
control plane, decrypts the blobs with the homelab identity, computes staleness from what it has
received (Healthchecks-style timeout, S28 in the D6 note), and sends email through the provider's
REST API (Cloudflare Email Service REST shape, rest-api.mdx; here a local mock).
"""
import base64, hashlib, json, secrets, sqlite3, subprocess, urllib.request

HOUR = 3600


def http_json(url, body, token, extra_headers=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST")
    req.add_header("content-type", "application/json")
    req.add_header("authorization", f"Bearer {token}")
    for k, v in (extra_headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


class Homelab:
    def __init__(self, db_path, identity_path, cp_base, cp_token, mail_base, mail_account, mail_token,
                 mail_from, stale_after_s, sim_header=True):
        self.db = sqlite3.connect(db_path)
        self.identity = identity_path
        self.cp_base, self.cp_token = cp_base, cp_token
        self.mail_base, self.mail_account, self.mail_token, self.mail_from = mail_base, mail_account, mail_token, mail_from
        self.stale_after = stale_after_s
        self.sim_header = sim_header  # emulation only: tell the mock the simulated time
        self.sent = []  # (kind, sim_now, account_id, device_id)
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS people(account_id TEXT PRIMARY KEY, invite_id TEXT, name TEXT, email TEXT,
            verified INTEGER DEFAULT 0, code_hash TEXT, code_sent_at INTEGER, verified_at INTEGER);
        CREATE TABLE IF NOT EXISTS pending_people(invite_id TEXT PRIMARY KEY, name TEXT, email TEXT);
        CREATE TABLE IF NOT EXISTS devices(device_id TEXT PRIMARY KEY, account_id TEXT, kind TEXT,
            last_backup INTEGER, last_seen INTEGER, enrolled INTEGER, nudged_for INTEGER);
        CREATE TABLE IF NOT EXISTS state(k TEXT PRIMARY KEY, v TEXT);
        """)

    # Admin-entered roster (B3 "admin-created accounts"): the address never passes through the cloud.
    def admin_add_person(self, invite_id, name, email):
        self.db.execute("INSERT INTO pending_people VALUES(?,?,?)", (invite_id, name, email))
        self.db.commit()

    def _decrypt(self, blob):
        r = subprocess.run(["age", "-d", "-i", self.identity], input=blob, capture_output=True, check=True)
        return json.loads(r.stdout)

    def _send(self, now, to, subject, text):
        status, resp = http_json(
            f"{self.mail_base}/client/v4/accounts/{self.mail_account}/email/sending/send",
            {"to": to, "from": self.mail_from, "subject": subject, "text": text},
            self.mail_token, {"x-sim-now": str(now)} if self.sim_header else None)
        return status == 200 and resp.get("success") is True

    def tick(self, now):
        cur = int((self.db.execute("SELECT v FROM state WHERE k='cursor'").fetchone() or ["0"])[0])
        status, pull = http_json(f"{self.cp_base}/v1/homelab/pull", {"commit_cursor": cur}, self.cp_token)
        assert status == 200, pull
        acked = []
        for b in pull["blobs"]:
            msg = self._decrypt(base64.b64decode(b["b64"]))
            parts = b["key"].split("/")
            if parts[1] == "roster":
                account_id, device_id = parts[2], parts[3].removesuffix(".age")
                if msg.get("name"):
                    self.db.execute("INSERT OR IGNORE INTO people(account_id, name, email) VALUES(?,?,?)",
                                    (account_id, msg["name"], msg["email"]))
                self.db.execute("INSERT OR IGNORE INTO devices(device_id, account_id, kind) VALUES(?,?,?)",
                                (device_id, account_id, msg["device_kind"]))
            elif parts[1] == "msg":
                account_id = parts[2]
                row = self.db.execute("SELECT code_hash FROM people WHERE account_id=?", (account_id,)).fetchone()
                if row and row[0] and hashlib.sha256(msg["verify_code"].encode()).hexdigest() == row[0]:
                    self.db.execute("UPDATE people SET verified=1, verified_at=?, code_hash=NULL WHERE account_id=?",
                                    (now, account_id))
            acked.append(b["key"])
        if acked:
            http_json(f"{self.cp_base}/v1/homelab/ack", {"keys": acked}, self.cp_token)
        for d in pull["devices"]:
            # Bind admin-entered people to the account that redeemed their invite.
            pend = self.db.execute("SELECT name, email FROM pending_people WHERE invite_id=?", (d["invite_id"],)).fetchone()
            if pend:
                self.db.execute("INSERT OR IGNORE INTO people(account_id, invite_id, name, email) VALUES(?,?,?,?)",
                                (d["account_id"], d["invite_id"], pend[0], pend[1]))
                self.db.execute("DELETE FROM pending_people WHERE invite_id=?", (d["invite_id"],))
            self.db.execute("INSERT OR IGNORE INTO devices(device_id, account_id, kind) VALUES(?,?,?)",
                            (d["device_id"], d["account_id"], "device"))
            self.db.execute("UPDATE devices SET last_seen=?, enrolled=COALESCE(enrolled, ?) WHERE device_id=?",
                            (d["last_seen_hour"], d["last_seen_hour"], d["device_id"]))
        for c in pull["commits"]:
            # Staleness is computed from commits the homelab has actually received (its receipts).
            self.db.execute("UPDATE devices SET last_backup=MAX(COALESCE(last_backup,0), ?) WHERE device_id=?",
                            (c["committed_hour"], c["device_id"]))
            cur = max(cur, c["seq"])
        self.db.execute("INSERT INTO state VALUES('cursor',?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (str(cur),))

        # Verification: email a short code; the app returns it encrypted to the homelab key (note F4 (a)).
        for account_id, name, email in self.db.execute(
                "SELECT account_id, name, email FROM people WHERE verified=0 AND code_sent_at IS NULL").fetchall():
            code = f"{secrets.randbelow(10**6):06d}"
            if self._send(now, email, "Your Reliquary code",
                          f"Hi {name.split()[0]}, type this code into the Reliquary app: {code}"):
                self.db.execute("UPDATE people SET code_hash=?, code_sent_at=? WHERE account_id=?",
                                (hashlib.sha256(code.encode()).hexdigest(), now, account_id))
                self.sent.append(("verify", now, account_id, None))

        # Nudges: one per staleness episode, only to verified people (ADR-0002 section 2).
        for device_id, account_id, kind, last_backup, last_seen, enrolled, nudged_for, name, email in self.db.execute(
                "SELECT d.device_id, d.account_id, d.kind, d.last_backup, d.last_seen, d.enrolled, d.nudged_for, p.name, p.email "
                "FROM devices d JOIN people p ON p.account_id=d.account_id WHERE p.verified=1").fetchall():
            ref = last_backup or enrolled
            if ref is None or now - ref < self.stale_after or nudged_for == ref:
                continue
            days = max(1, (now - ref) // 86400)
            online = last_seen is not None and now - last_seen < min(2 * 86400, self.stale_after)
            why = "is switched on but has not finished a backup" if online else "has not been in touch"
            if self._send(now, email, "Your backup needs a look",
                          f"Hi {name.split()[0]}, your {kind} {why} for {days} days. Open the Reliquary app on it."):
                self.db.execute("UPDATE devices SET nudged_for=? WHERE device_id=?", (ref, device_id))
                self.sent.append(("nudge", now, account_id, device_id))
        self.db.commit()
        return pull
