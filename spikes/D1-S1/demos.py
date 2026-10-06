#!/usr/bin/env python3
"""
D1-S1 malicious-cloud tabletop: executable checks for the attacks in the value inventory.
THROWAWAY research code. Uses the real Go `age` / `age-keygen` CLIs and real Ed25519/HMAC.
Every "cloud" step below uses only what Cloudflare would hold under ADR-0001/0002 as accepted
(public keys, opaque IDs, ciphertext, whatever it relays) unless the step says otherwise.

Writes results.json next to this file and prints a table. Exit status 1 if any
demo's observed outcome differs from its expected outcome.
"""
import hashlib, hmac, json, os, subprocess, sys, tempfile, time, platform
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.exceptions import InvalidSignature

AGE = os.environ.get("AGE", "age")
KEYGEN = os.environ.get("AGE_KEYGEN", "age-keygen")
W = tempfile.mkdtemp(prefix="d1s1-")
results = []

def run(args, inp=None, check=True):
    p = subprocess.run(args, input=inp, capture_output=True)
    if check and p.returncode != 0:
        raise RuntimeError(f"{args}: {p.stderr.decode()}")
    return p

def keygen(name):
    path = os.path.join(W, name + ".key")
    run([KEYGEN, "-o", path])
    pub = [l for l in open(path).read().splitlines() if l.startswith("# public key: ")][0].split(": ")[1]
    return path, pub

def enc(recipient, data):
    return run([AGE, "-r", recipient], inp=data).stdout
def dec(identity, data):
    p = run([AGE, "-d", "-i", identity], inp=data, check=False)
    return p.returncode, p.stdout

def record(id_, attack, expected, observed, detail):
    results.append({"id": id_, "attack": attack, "expected": expected, "observed": observed,
                    "match": expected == observed, "detail": detail})

def dedup_key(secret):
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b"reliquary/v1/dedup-key").derive(secret)

# ------------------------------------------------------------------ setup
homelab_id, homelab_pub = keygen("homelab")
cloud_id, cloud_pub = keygen("cloud")          # a key pair the malicious cloud controls
device_id, device_pub = keygen("device-H1")    # device X25519 restore key
receipt_sk = Ed25519PrivateKey.generate()      # homelab receipt/signing key
cloud_sk = Ed25519PrivateKey.generate()
def raw(pk):
    return pk.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
bundle = json.dumps({"v": 1, "recipient": homelab_pub, "receipt_key": raw(receipt_sk.public_key()).hex()},
                    sort_keys=True).encode()
PIN = hashlib.sha256(bundle).hexdigest()       # printed on the card / carried in the QR (kit)

# ------------------------------------------------------------------ A1: age has no origin authentication
forged = enc(homelab_pub, b"object made by the cloud, which holds only the homelab PUBLIC key")
rc, out = dec(homelab_id, forged)
record("A1", "Cloud creates a content object for the homelab key without any device secret",
       "decrypts cleanly", "decrypts cleanly" if rc == 0 else f"age exit {rc}",
       f"age -d exit {rc}; plaintext={out[:40]!r}. Encryption to the homelab key proves nothing about origin; "
       "ingest must bind every object to a device-signed record (header MAC) before it counts.")

# ------------------------------------------------------------------ A2: recipient substitution at enrollment
photo = b"\xff\xd8 synthetic keepsake bytes (SYN)"
evil_bundle = json.dumps({"v": 1, "recipient": cloud_pub, "receipt_key": raw(cloud_sk.public_key()).hex()},
                         sort_keys=True).encode()
# (a) device learns the recipient from the Worker, no pin
ct = enc(json.loads(evil_bundle)["recipient"], photo)
rc, out = dec(cloud_id, ct)
record("A2a", "Worker substitutes the homelab recipient; device has no pin",
       "cloud reads plaintext", "cloud reads plaintext" if (rc == 0 and out == photo) else "cloud cannot read",
       "Device encrypted to the key the Worker supplied; the cloud decrypted with its own identity. "
       "Every upload after enrollment is readable by the cloud.")
# (b) device checks the bundle against the pin carried in the kit
refused = hashlib.sha256(evil_bundle).hexdigest() != PIN
record("A2b", "Same substitution; device checks SHA-256(bundle) against the kit pin",
       "refused", "refused" if refused else "accepted",
       f"pin={PIN[:16]}..., offered={hashlib.sha256(evil_bundle).hexdigest()[:16]}...")

# ------------------------------------------------------------------ A3: dedup secret relayed by the Worker
family_secret = os.urandom(32)
dk = dedup_key(family_secret)
public_file = b"a widely shared meme / a known document (PUB)" * 100
index = {hmac.new(dk, public_file, hashlib.sha256).hexdigest()}          # the cloud's dedup index
# (a) cloud saw the secret in transit: confirmation-of-a-file
hit = hmac.new(dedup_key(family_secret), public_file, hashlib.sha256).hexdigest() in index
record("A3a", "Dedup secret delivered in plaintext through the Worker; cloud tests a known file",
       "cloud confirms file", "cloud confirms file" if hit else "cannot confirm",
       "Breaks ADR-0001's 'the cloud cannot test for known files'.")
# (b) learn-the-remaining-information on a templated document: brute-force a 6-digit field
template = b"Account statement. Customer PIN: %06d. " + b"boilerplate " * 80
secret_pin = 482913
index.add(hmac.new(dk, template % secret_pin, hashlib.sha256).hexdigest())
t0 = time.perf_counter(); found = None
for guess in range(1_000_000):
    if hmac.new(dk, template % guess, hashlib.sha256).hexdigest() in index:
        found = guess; break
el = time.perf_counter() - t0
record("A3b", "Holder of the dedup secret + the ID index recovers a 6-digit field of a templated document",
       "field recovered", "field recovered" if found == secret_pin else "not recovered",
       f"{found is not None and found + 1} HMACs over a {len(template % 0)}-byte document in {el:.2f} s "
       f"(one core, CPython hashlib; {platform.processor() or platform.machine()}). Tahoe-LAFS "
       "'learn-the-remaining-information' attack.")
# (c) secret sealed to the device key by the homelab and signed: cloud relays but cannot read or alter
sealed = enc(device_pub, family_secret)
sig = receipt_sk.sign(b"reliquary-dedup-secret-v1\n" + hashlib.sha256(sealed).digest())
rc_cloud, _ = dec(cloud_id, sealed)
tampered = enc(device_pub, os.urandom(32))
try:
    receipt_sk.public_key().verify(sig, b"reliquary-dedup-secret-v1\n" + hashlib.sha256(tampered).digest()); swap_ok = True
except InvalidSignature:
    swap_ok = False
rc_dev, got = dec(device_id, sealed)
record("A3c", "Secret sealed to the device X25519 key and signed by the homelab; cloud tries to read and to swap it",
       "cloud cannot read; swap detected; device reads",
       ("cloud cannot read" if rc_cloud != 0 else "cloud READS") + "; " +
       ("swap detected" if not swap_ok else "swap ACCEPTED") + "; " +
       ("device reads" if rc_dev == 0 and got == family_secret else "device cannot read"),
       "Needs the device key to reach the homelab authentically first (A5), or the cloud swaps the device key instead.")

# ------------------------------------------------------------------ A4: receipts
def rmsg(d):
    return b"reliquary-commit-v1\n" + json.dumps(d, sort_keys=True).encode()
body = {"device_id": "H1", "dedup_id": "ab" * 16, "size": 123, "meta_sha256": "cd" * 32}
genuine = receipt_sk.sign(rmsg(body))
pinned = raw(receipt_sk.public_key())
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
def device_accepts(b, s, key=pinned, me="H1", want=None):
    try:
        Ed25519PublicKey.from_public_bytes(key).verify(s, rmsg(b))
    except InvalidSignature:
        return False
    return b["device_id"] == me and (want is None or all(b[k] == v for k, v in want.items()))
want = {"dedup_id": "ab" * 16, "size": 123, "meta_sha256": "cd" * 32}
cases = [
    ("A4a", "Cloud forges a receipt with its own key", device_accepts(body, cloud_sk.sign(rmsg(body)), want=want), False),
    ("A4b", "Cloud replays H1's genuine receipt to H2", device_accepts(body, genuine, me="H2", want=want), False),
    ("A4c", "Cloud replays a genuine receipt for another file", device_accepts(body, genuine, want={**want, "dedup_id": "ef" * 16}), False),
    ("A4d", "Cloud edits the size in a genuine receipt", device_accepts({**body, "size": 999}, genuine, want=want), False),
    ("A4e", "Genuine receipt, correct device and file", device_accepts(body, genuine, want=want), True),
    ("A4f", "Unpinned: device trusts the receipt key the Worker supplies; cloud forges", device_accepts(
        body, cloud_sk.sign(rmsg(body)), key=raw(cloud_sk.public_key()), want=want), True),
]
for cid, what, got, exp in cases:
    record(cid, what, "accepted" if exp else "rejected", "accepted" if got else "rejected",
           "Ed25519 over 'reliquary-commit-v1\\n' || JSON; binding fields device_id, dedup_id, size, meta_sha256.")

# ------------------------------------------------------------------ A5: device-key substitution (restore redirection)
restore_plain = b"restored keepsake bytes (SYN)"
# (a) homelab takes H1's restore key from the Worker's device list
worker_says_H1 = cloud_pub
rc, out = dec(cloud_id, enc(worker_says_H1, restore_plain))
record("A5a", "Worker substitutes H1's restore key; homelab re-encrypts the restore to it",
       "cloud reads restore", "cloud reads restore" if rc == 0 and out == restore_plain else "cloud cannot read",
       "ADR-0001 §6 re-encrypts to 'the requesting device's own public key'; if the homelab learns that key "
       "from the Worker, a restore is disclosed.")
# (b) device key admitted only with a signature chain the cloud cannot make
enroll_sk = Ed25519PrivateKey.generate()   # e.g. an existing device's key, or a key derived from the kit
enroll_pk = raw(enroll_sk.public_key())
admission = enroll_sk.sign(b"reliquary-device-admit-v1\n" + device_pub.encode())
def homelab_admits(pub_str, sig):
    try:
        Ed25519PublicKey.from_public_bytes(enroll_pk).verify(sig, b"reliquary-device-admit-v1\n" + pub_str.encode()); return True
    except InvalidSignature:
        return False
record("A5b", "Same substitution; homelab admits device keys only with a signature by a key the cloud lacks",
       "substitute refused; genuine admitted",
       ("substitute refused" if not homelab_admits(cloud_pub, admission) else "substitute ADMITTED") + "; " +
       ("genuine admitted" if homelab_admits(device_pub, admission) else "genuine refused"),
       "Tailnet-Lock analogue. Who holds the admitting key (admin, homelab, or an existing device) is D3/OD-05.")

# ------------------------------------------------------------------ A6: invite-hash brute force cost (measured rate, extrapolated)
n = 2_000_000
code = b"ABCDEFGHJK23"
t0 = time.perf_counter()
for i in range(n):
    hashlib.sha256(code + i.to_bytes(4, "little")).digest()
rate = n / (time.perf_counter() - t0)
years50 = (2 ** 50) / rate / 86400 / 365
record("A6", "Cloud holds the stored hash of a 50-bit invite code (fast hash); offline search cost",
       "measured", "measured",
       f"measured {rate:,.0f} SHA-256/s on one core in CPython; 2^50 at that rate = {years50:,.0f} core-years. "
       "This is a single-core CPython floor, not a GPU figure: GPU rates are orders of magnitude higher and were not measured. "
       "Relevant only if a homelab-verified secret is derived from the invite code (D3).")

# ------------------------------------------------------------------ output
ok = all(r["match"] for r in results)
json.dump({"generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "age_version": run([AGE, "--version"]).stdout.decode().strip(),
           "python": sys.version.split()[0], "results": results}, open("results.json", "w"), indent=1)
for r in results:
    print(f"{r['id']:4s} {'OK ' if r['match'] else 'DIFF'} {r['attack']}\n       expected: {r['expected']} | observed: {r['observed']}\n       {r['detail']}")
print("ALL MATCH" if ok else "MISMATCH")
sys.exit(0 if ok else 1)
