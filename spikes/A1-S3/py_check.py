"""Reliquary A1-S3: third check (Python 3 standard library only) of constructions A and B,
the SHA-256 values and the base32 text form. BLAKE3 (C, D) is not in the standard library and
is not checked here. THROWAWAY spike code."""
import base64, hashlib, hmac, json, sys

def hkdf32(ikm, info):  # RFC 5869, salt = empty (HashLen zeros), L = 32
    prk = hmac.new(b"\x00" * 32, ikm, hashlib.sha256).digest()
    return hmac.new(prk, info + b"\x01", hashlib.sha256).digest()

def K(e): return bytes((i + 32 * e) & 0xff for i in range(32))

BLOCK = bytes(i % 251 for i in range(251 * 8192))
def feed(content, n):
    if content == "ascii:abc":
        yield b"abc"; return
    while n > 0:
        k = min(n, len(BLOCK)); yield BLOCK[:k]; n -= k

def text(c, e, raw): return f"rq1-{c}-e{e}-" + base64.b32encode(raw).decode().rstrip("=").lower()

doc = json.load(open(sys.argv[1]))
ok_n = bad = 0
for v in doc["vectors"]:
    if v["kind"] != "positive":
        continue
    k = K(v["epoch"])
    sha = hashlib.sha256(); ma = hmac.new(hkdf32(k, b"reliquary/v1/dedup-key"), digestmod=hashlib.sha256)
    for b in feed(v["content"], v["length"]):
        sha.update(b); ma.update(b)
    d = sha.digest(); a = ma.digest()
    b_ = hmac.new(hkdf32(k, b"reliquary/v1/dedup-key/sha256-digest"), d, hashlib.sha256).digest()
    ok = (d.hex() == v["sha256"] and a.hex() == v["id_a"] and b_.hex() == v["id_b"]
          and text("a", v["epoch"], a) == v["text_a"] and text("b", v["epoch"], b_) == v["text_b"])
    ok_n += ok; bad += (not ok)
    if not ok: print("FAIL", v["id"], file=sys.stderr)
print(json.dumps({"impl": f"python {sys.version.split()[0]} hashlib/hmac/base64 (constructions a, b; sha256; base32)", "positives_pass": ok_n, "positives_fail": bad}))
