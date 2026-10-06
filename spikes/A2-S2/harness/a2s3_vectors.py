#!/usr/bin/env python3
"""THROWAWAY SPIKE: generate Reliquary project vectors (CCTV file format) with
the seeded encoder, regenerate them to prove byte-identical determinism, and
run them through Go age, the Rust decoder, typage and kage. Not production.

Vector files use only CCTV header keys (expect, payload, file key, identity,
comment), so CCTV-style runners can consume them. Seeds and contexts are in
`comment:` lines. Synthetic data only.

Environment: BIN, AGE, NODE_TOOL, KAGE_CP, OUT (vector dir), WORK.
"""
import base64, hashlib, json, os, shutil, subprocess, sys

BIN = os.environ["BIN"]; AGE = os.environ["AGE"]; NODE_TOOL = os.environ["NODE_TOOL"]; KAGE_CP = os.environ["KAGE_CP"]
OUT = os.environ["OUT"]; WORK = os.environ["WORK"]
P = lambda *a: os.path.join(WORK, *a)
run = lambda c: subprocess.run(c, capture_output=True)

def det(label, n=32):
    """Deterministic bytes from a label (vectors must regenerate identically)."""
    out = b""
    i = 0
    while len(out) < n:
        out += hashlib.sha256(f"reliquary-a2-vectors/{label}/{i}".encode()).digest()
        i += 1
    return out[:n]

def build(outdir):
    shutil.rmtree(WORK, ignore_errors=True); os.makedirs(WORK)
    shutil.rmtree(outdir, ignore_errors=True); os.makedirs(outdir)
    ids = {}
    for name in ("pq-a", "pq-b", "pq-other"):
        r = run([BIN, "keygen", "--seed", det("id/" + name).hex(), "--out", P(name + ".id")]).stdout.decode().strip()
        ids[name] = (open(P(name + ".id")).read().strip().splitlines()[-1], r)
    xr = run([BIN, "keygen", "--type", "x25519", "--seed", det("id/x").hex(), "--out", P("x.id")]).stdout.decode().strip()
    ids["x"] = (open(P("x.id")).read().strip().splitlines()[-1], xr)

    def rfile(names):
        p = P("r_" + "_".join(names))
        open(p, "w").write("\n".join(ids[n][1] for n in names) + "\n")
        return p

    def enc(label, pt, names, extra=()):
        src = P(label + ".pt"); open(src, "wb").write(pt)
        dst = P(label + ".age")
        r = run([BIN, "encrypt", "--recipients", rfile(names), "--in", src, "--out", dst, "--seed", det("seed/" + label).hex(),
                 "--context", det("ctx/" + label).hex()] + list(extra))
        assert r.returncode == 0, r.stderr
        return open(dst, "rb").read()

    def file_key(ct, idname):
        p = P("tmp.age"); open(p, "wb").write(ct)
        open(P("tmp.id"), "w").write(ids[idname][0] + "\n")
        r = run([BIN, "debug-keys", "--identity", P("tmp.id"), "--object", p])
        return json.loads(r.stdout)["file_key"] if r.returncode == 0 else None

    def write(name, expect, ct, idname, payload=None, comments=(), fk=True):
        hdr = [f"expect: {expect}"]
        if payload is not None:
            hdr.append(f"payload: {hashlib.sha256(payload).hexdigest()}")
        k = file_key(ct, idname) if fk else None
        if k:
            hdr.append(f"file key: {k}")
        hdr.append(f"identity: {ids[idname][0]}")
        hdr += [f"comment: {c}" for c in comments]
        hdr.append(f"comment: seed={det('seed/' + name).hex()} context={det('ctx/' + name).hex()} (Reliquary encoder, hedged HKDF labels reliquary/v1/hedge/*)")
        open(os.path.join(outdir, name), "wb").write("\n".join(hdr).encode() + b"\n\n" + ct)

    pts = {"empty": b"", "1byte": b"\x00", "64k": det("pt/64k", 65536), "64k1": det("pt/64k1", 65537), "3chunks": det("pt/3c", 3 * 65536 + 5), "200": det("pt/200", 200), "1k": det("pt/1k", 1024)}
    for nm, key in [("rq_pq1_empty", "empty"), ("rq_pq1_1byte", "1byte"), ("rq_pq1_64k_exact", "64k"), ("rq_pq1_64k_plus1", "64k1"), ("rq_pq1_3chunks", "3chunks")]:
        write(nm, "success", enc(nm, pts[key], ["pq-a"]), "pq-a", pts[key], ["one mlkem768x25519 stanza (1,627-byte header), Reliquary PQ profile"])
    ct = enc("rq_pq2_second_identity", pts["200"], ["pq-a", "pq-b"])
    write("rq_pq2_second_identity", "success", ct, "pq-b", pts["200"], ["two mlkem768x25519 stanzas (3,184-byte header); decrypt with the second identity"])
    ct = enc("rq_x25519_legacy", pts["1k"], ["x"])
    write("rq_x25519_legacy", "success", ct, "x", pts["1k"], ["one X25519 stanza (168-byte header); the Reliquary PQ profile rejects this at ingest (E_PROFILE)"])
    base = enc("rq_pq1_3chunks", pts["3chunks"], ["pq-a"])
    pl = base.index(b"\n---")
    pl = base.index(b"\n", pl + 1) + 1 + 16
    body = len(base) - pl
    last = body % 65552 or 65552
    write("rq_pq1_drop_final_chunk", "payload failure", base[: len(base) - last], "pq-a", pts["3chunks"][: 3 * 65536], ["final chunk dropped; 3 non-final chunks authenticate, then truncation is detected"])
    write("rq_pq1_trailing_data", "payload failure", base + b"\x00" * 20, "pq-a", pts["3chunks"][: 3 * 65536], ["20 bytes appended after the short final chunk: they merge into it, so it fails authentication; only the 3 full chunks are released"])
    ct = enc("rq_pq1_mixed_x25519", pts["200"], ["pq-a", "x"], ("--allow-mixed",))
    write("rq_pq1_mixed_x25519", "success", ct, "pq-a", pts["200"], ["PQ + X25519 stanzas: valid age (decrypt succeeds), but violates the age SHOULD NOT and the Reliquary profile (ingest: E_PROFILE)"])
    ct = enc("rq_pq1_grease", pts["200"], ["pq-a"], ("--grease",))
    write("rq_pq1_grease", "success", ct, "pq-a", pts["200"], ["extra unknown stanza: valid age, not in the Reliquary profile (ingest: E_PROFILE)"])
    # low-order X25519 share in the X-Wing enc (MAC line left unchanged)
    v = enc("rq_pq1_low_order", pts["200"], ["pq-a"])
    e = v.index(b"\n---")
    lines = v[:e].split(b"\n")
    st = lines[1].split(b" ")
    encb = bytearray(base64.b64decode(st[2] + b"=" * (-len(st[2]) % 4)))
    encb[-32:] = bytes(32)
    st[2] = base64.b64encode(bytes(encb)).rstrip(b"=")
    lines[1] = b" ".join(st)
    write("rq_pq1_low_order", "header failure", b"\n".join(lines) + v[e:], "pq-a", None, ["X25519 part of the X-Wing enc set to the all-zero (low-order) point"], fk=False)
    ct = enc("rq_pq1_no_match", pts["200"], ["pq-a"])
    write("rq_pq1_no_match", "no match", ct, "pq-other", None, ["encrypted to pq-a, decrypted with pq-other"], fk=False)
    m = bytearray(enc("rq_pq1_bad_mac", pts["200"], ["pq-a"]))
    i = m.index(b"\n--- ") + 5
    m[i] = ord("A") if m[i] != ord("A") else ord("B")
    write("rq_pq1_bad_mac", "HMAC failure", bytes(m), "pq-a", None, ["first character of the header MAC changed"], fk=False)
    write("rq_pq1_header_truncated", "header failure", base[:1000], "pq-a", None, ["object cut inside the stanza line"], fk=False)
    return ids

def digest_dir(d):
    return {n: hashlib.sha256(open(os.path.join(d, n), "rb").read()).hexdigest() for n in sorted(os.listdir(d))}

ids = build(OUT)
d1 = digest_dir(OUT)
build(OUT + ".regen")
d2 = digest_dir(OUT + ".regen")
shutil.rmtree(OUT + ".regen")
results = {"vectors": len(d1), "regenerated_identically": d1 == d2, "decoders": {}}

def parse(path):
    raw = open(path, "rb").read()
    kv = []
    off = 0
    while True:
        i = raw.index(b"\n", off); line = raw[off:i].decode(); off = i + 1
        if not line:
            break
        k, _, v = line.partition(": "); kv.append((k, v))
    return dict((k, v) for k, v in kv if k != "comment"), raw[off:]

# Go age CLI
gores = {}
for n in sorted(os.listdir(OUT)):
    h, ct = parse(os.path.join(OUT, n))
    open(P("v.age"), "wb").write(ct); open(P("v.id"), "w").write(h["identity"] + "\n")
    r = run([AGE, "-d", "-i", P("v.id"), "-o", P("v.out"), P("v.age")])
    out = open(P("v.out"), "rb").read() if os.path.exists(P("v.out")) else b""
    if os.path.exists(P("v.out")):
        os.remove(P("v.out"))
    if h["expect"] == "success":
        ok = r.returncode == 0 and hashlib.sha256(out).hexdigest() == h["payload"]
    else:
        ok = r.returncode != 0
    gores[n] = {"pass": ok, "exit": r.returncode, "stderr": r.stderr.decode().strip()[:100]}
results["decoders"]["go-age-1.3.2"] = {"pass": sum(v["pass"] for v in gores.values()), "total": len(gores), "detail": gores}
r = run([BIN, "cctv", "--dir", OUT]); results["decoders"]["rust-strict"] = json.loads(r.stdout.decode().strip().splitlines()[-1])["summary"]
r = run(["node", NODE_TOOL, "cctv", OUT]); results["decoders"]["typage-0.3.1"] = json.loads(r.stdout.decode().strip().splitlines()[-1])["summary"]
r = run(["java", "-cp", KAGE_CP, "KageTool", "cctv", OUT]); results["decoders"]["kage-0.8.0"] = json.loads(r.stdout.decode().strip().splitlines()[-1])["summary"]
json.dump(results, open(P("vectors_results.json"), "w"), indent=1)
print(json.dumps({k: (v if k != "decoders" else {d: {kk: vv for kk, vv in s.items() if kk != "detail"} for d, s in v.items()}) for k, v in results.items()}, indent=1))
