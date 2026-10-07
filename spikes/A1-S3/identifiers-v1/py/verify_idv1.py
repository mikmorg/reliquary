#!/usr/bin/env python3
# THROWAWAY spike code (Reliquary A1-S3 follow-up). Independent Python check of the DRAFT
# identifiers.md vectors, written from the spec text, not from the Rust source.
# Uses only the standard library: hashlib/hmac (OpenSSL) and base64; HKDF written from RFC 5869's
# extract-then-expand definition. Usage: verify_idv1.py vectors.json [wycheproof_hmac wycheproof_hkdf go_hkdf]
import base64, hashlib, hmac, json, sys, re

def hkdf(ikm, info, salt=b"", length=32):
    prk = hmac.new(salt if salt else b"\x00" * 32, ikm, hashlib.sha256).digest()
    out, t, i = b"", b"", 1
    while len(out) < length:
        t = hmac.new(prk, t + info + bytes([i]), hashlib.sha256).digest(); out += t; i += 1
    return out[:length]

def info_dedup(kind, epoch, scope="family"):
    return f"reliquary/v1/dedup-id-key/kind={kind:02x}/epoch={epoch:04x}/scope={scope}".encode()

def b32(b): return base64.b32encode(b).decode().rstrip("=").lower()
def text(kind, epoch, mac): return f"rd1-{kind:02x}-{epoch:04x}-{b32(mac)}"
def binary(kind, epoch, mac): return bytes([kind]) + epoch.to_bytes(2, "big") + mac

TEXT_RE = re.compile(r"rd1-([0-9a-f]{2})-([0-9a-f]{4})-([a-z2-7]{52})")
def parse_text(s):
    m = TEXT_RE.fullmatch(s)  # fullmatch: no trailing newline accepted
    if not m: raise ValueError("syntax")
    kind, epoch = int(m.group(1), 16), int(m.group(2), 16)
    if kind == 2: raise ValueError("reserved kind")
    if kind not in (1, 3, 4): raise ValueError("unknown kind")
    body = m.group(3)
    mac = base64.b32decode(body.upper() + "====")
    if len(mac) != 32 or b32(mac) != body: raise ValueError("non-canonical")
    return kind, epoch, mac

def parse_binary(b):
    if len(b) != 35: raise ValueError("length")
    if b[0] == 2: raise ValueError("reserved kind")
    if b[0] not in (1, 3, 4): raise ValueError("unknown kind")
    return b[0], int.from_bytes(b[1:3], "big"), b[3:]

PERIOD = bytes(i for i in range(251)) * 16384  # ~4 MB, multiple of 251
def feed(content, sinks):
    if content.startswith("ascii:"):
        for s in sinks: s.update(content[6:].encode())
        return
    n = int(content.split(":")[1]); off = 0
    mv = memoryview(PERIOD); sizes = [3, 1, 4096, 1 << 20, len(PERIOD) - 251]; i = 0
    while off < n:
        start = off % 251
        take = min(sizes[i % len(sizes)], n - off, len(PERIOD) - start)
        chunk = mv[start:start + take]
        for s in sinks: s.update(chunk)
        off += take; i += 1

def content_bytes(content):
    class Acc:
        def __init__(s): s.b = bytearray()
        def update(s, x): s.b += bytes(x)
    a = Acc(); feed(content, [a]); return bytes(a.b)

def main():
    v = json.load(open(sys.argv[1]))
    S = {k: bytes.fromhex(v["secrets"][k]) for k in ("S_0", "S_1", "S_root")}
    kroot = hkdf(S["S_root"], b"reliquary/v1/content-mac-key/scope=family")
    fails = 0
    if kroot.hex() != v["k_root"]["key"]: print("FAIL k_root"); fails += 1
    cache = {}
    for p in v["positive"]:
        kind, e, sec = int(p["kind"], 16), p["epoch"], S[p["secret"]]
        K = hkdf(sec, info_dedup(kind, e))
        k3 = hkdf(sec, info_dedup(3, e))
        key = (p["content"], e, p["secret"])
        if key not in cache:
            sh = hashlib.sha256(); h3 = hmac.new(k3, b"\x03", hashlib.sha256); hr = hmac.new(kroot, b"", hashlib.sha256)
            feed(p["content"], [sh, h3, hr])
            cache[key] = (sh.digest(), h3.digest(), hr.digest())
        d, mac3, inner = cache[key]
        if kind == 1: mac = hmac.new(K, b"\x01" + d, hashlib.sha256).digest()
        elif kind == 3: mac = mac3
        else: mac = hmac.new(K, b"\x04" + inner, hashlib.sha256).digest()
        ok = (d.hex() == p["sha256"] and K.hex() == p["key"] and mac.hex() == p["mac"]
              and binary(kind, e, mac).hex() == p["id_binary"] and text(kind, e, mac) == p["id_text"]
              and parse_text(p["id_text"]) == (kind, e, mac) and parse_binary(bytes.fromhex(p["id_binary"])) == (kind, e, mac)
              and (kind != 4 or inner.hex() == p["inner"]))
        if not ok: fails += 1; print("FAIL", p["id"])
    npos = len(v["positive"])
    # domain-separation negatives: recompute expected and forbidden independently
    c = content_bytes("pattern-mod-251:1025"); d = hashlib.sha256(c).digest(); s0 = S["S_0"]
    H = lambda k, m: hmac.new(k, m, hashlib.sha256).digest()
    k1, k3, k4 = (hkdf(s0, info_dedup(k, 0)) for k in (1, 3, 4))
    mac1 = H(k1, b"\x01" + d); mac3 = H(k3, b"\x03" + c); inner = H(kroot, c); mac4 = H(k4, b"\x04" + inner)
    k1e1 = hkdf(s0, info_dedup(1, 1)); k1e = hkdf(s0, info_dedup(1, 0x0102)); m = H(k1e, b"\x01" + d)
    mine = {
        "N01": (mac1, H(k1, d)), "N02": (mac1, H(s0, b"\x01" + d)),
        "N03": (mac1, H(hkdf(s0, b"reliquary/v1/dedup-id-key"), b"\x01" + d)),
        "N04": (mac1, H(hkdf(s0, b"reliquary/v1/dedup-key/sha256-digest"), d)),
        "N05": (mac1, H(k1, b"\x01" + d.hex().encode())), "N06": (H(k1e1, b"\x01" + d), mac1),
        "N07": (mac1, H(hkdf(s0, b"reliquary/v1/dedup-id-key/kind=01/epoch=0000"), b"\x01" + d)),
        "N08": (mac1, d), "N09": (mac3, H(k3, c)), "N10": (mac3, H(k1, b"\x03" + c)),
        "N11": (mac4, H(k4, b"\x04" + H(k4, c))), "N12": (mac4, H(k4, b"\x04" + d)),
        "N13": (mac4, H(k4, b"\x04" + H(S["S_root"], c))),
        "N14": (binary(1, 0x0102, m), bytes([1, 2, 1]) + m),
    }
    for n in v["domain_separation_negative"]:
        exp, forb = mine[n["id"]]
        e2 = n.get("expected_mac") or n.get("expected_binary")
        if exp.hex() != e2 or forb.hex() != n["forbidden"] or exp == forb: fails += 1; print("FAIL", n["id"])
    for n in v["encoding_negative"]:
        try:
            parse_text(n["text"]) if "text" in n else parse_binary(bytes.fromhex(n["binary"]))
            fails += 1; print("FAIL accepted", n["id"])
        except ValueError:
            pass
    print(f"python: positives {npos}, domain negatives {len(v['domain_separation_negative'])}, encoding negatives {len(v['encoding_negative'])}, failures {fails}")
    if len(sys.argv) > 4:
        wf = 0; h = json.load(open(sys.argv[2])); nh = 0
        for g in h["testGroups"]:
            for t in g["tests"]:
                tag = bytes.fromhex(t["tag"]); full = H(bytes.fromhex(t["key"]), bytes.fromhex(t["msg"]))
                if (full[:len(tag)] == tag) != (t["result"] == "valid"): wf += 1
                nh += 1
        k = json.load(open(sys.argv[3])); nk = 0
        for g in k["testGroups"]:
            for t in g["tests"]:
                size = t["size"]
                ok = size <= 255 * 32 and hkdf(bytes.fromhex(t["ikm"]), bytes.fromhex(t["info"]), bytes.fromhex(t["salt"]), size).hex() == t["okm"]
                if ok != (t["result"] == "valid"): wf += 1
                nk += 1
        go = json.load(open(sys.argv[4]))
        for t in go["vectors"]:
            if hkdf(bytes.fromhex(t["ikm"]), bytes.fromhex(t["info"]), bytes.fromhex(t["salt"]), len(t["okm"]) // 2).hex() != t["okm"]: wf += 1
        print(f"python: wycheproof hmac {nh}, hkdf {nk}, go/rfc5869 hkdf {len(go['vectors'])}, failures {wf}")
        fails += wf
    sys.exit(1 if fails else 0)

main()
