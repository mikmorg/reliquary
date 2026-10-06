#!/usr/bin/env python3
"""THROWAWAY SPIKE harness for A2-S4 (forgery and truncation). Not production.

Attacker model: holds only what is public or cloud-visible: the homelab PQ
recipient(s) from the trust bundle, the registered device public keys, and
the staged ciphertext. A second class is a *registered but malicious* device
(holds a real device key). Each attack must be rejected by `ingest` with a
specific REJECT code BEFORE any catalog/object/by-dedup/seen-set write.

Environment: BIN, AGE_KEYGEN, WORK.
"""
import base64, glob, hashlib, json, os, shutil, subprocess, sys

BIN = os.environ["BIN"]; KEYGEN = os.environ["AGE_KEYGEN"]; WORK = os.environ["WORK"]
shutil.rmtree(WORK, ignore_errors=True); os.makedirs(WORK)
P = lambda *a: os.path.join(WORK, *a)
results = []
table = []

def check(name, ok, detail=""):
    results.append({"check": name, "pass": bool(ok), "detail": detail})
    print(("PASS " if ok else "FAIL ") + name + (" :: " + str(detail) if detail != "" else ""), flush=True)

def run(cmd):
    return subprocess.run(cmd, capture_output=True)

for d in ["dev", "dev/state", "dev/keystore", "r2", "home", "home/store", "src", "evil"]:
    os.makedirs(P(d), exist_ok=True)
run([KEYGEN, "-pq", "-o", P("home", "identity.txt")])
hr = run([KEYGEN, "-y", P("home", "identity.txt")]).stdout.decode().strip()
open(P("home", "recipients.txt"), "w").write(hr + "\n")
rk = json.loads(run([BIN, "keygen-sign", "--out", P("home", "receipt.key")]).stdout)["public_key"]
dk = json.loads(run([BIN, "keygen-sign", "--out", P("dev", "device.key")]).stdout)["public_key"]
ek = json.loads(run([BIN, "keygen-sign", "--out", P("evil", "evil.key")]).stdout)["public_key"]
json.dump({"dev-a": dk, "dev-b": json.loads(run([BIN, "keygen-sign", "--out", P("dev", "device_b.key")]).stdout)["public_key"]}, open(P("home", "registry.json"), "w"))
pin = json.loads(run([BIN, "make-trust", "--recipients-file", P("home", "recipients.txt"), "--profile", "pq", "--receipt-pub", rk, "--out", P("dev", "trust.json")]).stdout)["pin"]
FAMILY = os.urandom(32).hex()
DEV = ["--state-dir", P("dev", "state"), "--keystore", P("dev", "keystore"), "--r2", P("r2"), "--trust", P("dev", "trust.json"), "--trust-pin", pin]

def store_state():
    s = {}
    for root, _, fs in os.walk(P("home", "store")):
        for f in fs:
            fp = os.path.join(root, f)
            s[os.path.relpath(fp, P("home", "store"))] = hashlib.sha256(open(fp, "rb").read()).hexdigest()
    return s

def ingest(meta, obj=None, extra=()):
    cmd = [BIN, "ingest", "--identity", P("home", "identity.txt"), "--family-secret", FAMILY, "--registry", P("home", "registry.json"),
           "--receipt-key", P("home", "receipt.key"), "--store", P("home", "store"), "--meta", meta, "--profile", "pq", "--stanzas", "1",
           "--out", P("home", "receipt.out")] + (["--object", obj] if obj else []) + list(extra)
    r = run(cmd)
    code = None
    for line in r.stderr.decode().splitlines():
        if line.startswith("REJECT "):
            code = json.loads(line[7:])["code"]
    return r.returncode, code, r.stderr.decode().strip()[-240:]

def expect_reject(name, want, meta, obj=None, extra=(), attacker="public-key holder"):
    before = store_state()
    rc, code, err = ingest(meta, obj, extra)
    after = store_state()
    unchanged = before == after
    ok = rc == 10 and code == want and unchanged
    table.append({"attack": name, "attacker": attacker, "expected": want, "got": code, "exit": rc, "store_unchanged": unchanged, "flags": " ".join(extra)})
    check(f"{name}: rejected with {want}, no store write", ok, {"exit": rc, "code": code, "store_unchanged": unchanged, "stderr": err if not ok else ""})

def upload(name, size, k=None):
    src = P("src", name)
    open(src, "wb").write(os.urandom(size))
    cmd = [BIN, "start", "--file", src, "--family-secret", FAMILY, "--device-key", P("dev", "device.key"), "--device-id", "dev-a"] + DEV
    if k:
        cmd += ["--chunks-per-part", str(k)]
    r = run(cmd)
    j = json.loads(r.stdout.decode().strip().splitlines()[-1])
    if j.get("mode") == "multipart":
        c = run([BIN, "complete", "--upload-id", j["upload_id"], "--device-key", P("dev", "device.key")] + DEV)
        j = json.loads(c.stdout.decode().strip().splitlines()[-1])
    pend = json.load(open(j["pending"]))
    return {"src": src, "object": str(j["object"]), "meta": pend["meta_file"], "pending": j["pending"]}

def decrypt_record(meta):
    """Homelab-side helper: plaintext signed note of a record (to reuse its fields)."""
    out = P("home", "rec.pt")
    run([BIN, "decrypt", "--identity", P("home", "identity.txt"), "--in", meta, "--out", out])
    note = open(out, "rb").read().decode()
    return json.loads(note.split("\n")[0])

def sign_record(body, key, name, out, keyhash_pk=None):
    bf = out + ".body.json"
    json.dump(body, open(bf, "w"))
    cmd = [BIN, "sign-meta", "--trust", P("dev", "trust.json"), "--trust-pin", pin, "--device-key", key, "--key-name", name, "--body", bf, "--out", out]
    if keyhash_pk:
        cmd += ["--keyhash-pk", keyhash_pk]
    r = run(cmd)
    assert r.returncode == 0, r.stderr
    return out

def encrypt(src, out, recips=None, extra=()):
    r = run([BIN, "encrypt", "--recipients", recips or P("home", "recipients.txt"), "--in", src, "--out", out] + list(extra))
    assert r.returncode == 0, r.stderr
    return out

# ------------------------------------------------------------ baseline: honest uploads ingest
legit = upload("legit1", 300_000)
rc, code, err = ingest(legit["meta"], legit["object"])
check("baseline: honest single-PUT upload ingests", rc == 0, err)
legit2 = upload("legit2", 5 * 65536, k=2)  # multi-part, payload ends on a full chunk
rc, code, err = ingest(legit2["meta"], legit2["object"])
check("baseline: honest multipart upload ingests", rc == 0, err)
lrec = decrypt_record(legit["meta"])

# fresh, not-yet-ingested honest upload used as the victim for substitution/truncation
victim = upload("victim", 3 * 65536 + 999, k=2)
vrec = decrypt_record(victim["meta"])
vobj = open(victim["object"], "rb").read()

# ------------------------------------------------------------ A. forged object + forged record (public key only)
evil_src = P("evil", "evil.bin"); open(evil_src, "wb").write(b"forged keepsake " * 5000)
evil_obj = encrypt(evil_src, P("evil", "evil.age"))
evil_sha = hashlib.sha256(open(evil_src, "rb").read()).hexdigest()
ins = json.loads(run([BIN, "inspect", "--in", evil_obj]).stdout)
mac = json.loads(run([BIN, "debug-keys", "--identity", P("home", "identity.txt"), "--object", evil_obj]).stdout)["header_mac"]  # (attacker knows its own header MAC)
body = dict(lrec)
body.update({"device_id": "dev-a", "sha256": evil_sha, "size": os.path.getsize(evil_src), "record_id": "f" * 32, "device_seq": 999,
             "dedup_id": "a" * 64, "object": {"key": "staging/x/y", "header_mac": mac, "ct_len": os.path.getsize(evil_obj), "prefix_len": ins["prefix_len"], "profile": "pq", "stanzas": 1}})
body.pop("pad", None)
expect_reject("A1 forged object + record signed by attacker key under its own name", "E_SIG_UNKNOWN_KEY",
              sign_record(dict(body, device_id="evil"), P("evil", "evil.key"), "evil", P("evil", "a1.age")), evil_obj)
expect_reject("A2 forged record claims registered device name, attacker key", "E_SIG_KEY_HASH",
              sign_record(body, P("evil", "evil.key"), "dev-a", P("evil", "a2.age")), evil_obj)
expect_reject("A3 forged record with victim's key hash, attacker signature", "E_SIG_INVALID",
              sign_record(body, P("evil", "evil.key"), "dev-a", P("evil", "a3.age"), keyhash_pk=dk), evil_obj)
# record that is a valid age file but not a signed note at all
open(P("evil", "plain.txt"), "w").write(json.dumps(body) + "\n")
expect_reject("A4 unsigned record (valid age file, no signature line)", "E_RECORD_FORMAT", encrypt(P("evil", "plain.txt"), P("evil", "a4.age")), evil_obj)
# dedup-hit forgery: object null (claim a sighting of committed content without uploading)
expect_reject("A5 forged dedup-hit record (object null), attacker key", "E_SIG_KEY_HASH",
              sign_record(dict(body, object=None, sha256=lrec["sha256"], size=lrec["size"], dedup_id=lrec["dedup_id"]), P("evil", "evil.key"), "dev-a", P("evil", "a5.age")))

# ------------------------------------------------------------ B. object substitution (honest record, attacker object)
sub = P("evil", "victim_sized.bin"); open(sub, "wb").write(os.urandom(3 * 65536 + 999))
sub_obj = encrypt(sub, P("evil", "sub.age"))
expect_reject("B1 staged object replaced by attacker's valid age object (same size)", "E_BINDING_HEADER_MAC", victim["meta"], sub_obj)
expect_reject("B2 same, binding pre-check disabled (TEST flag): content check must still reject", "E_CONTENT_MISMATCH", victim["meta"], sub_obj, extra=("--skip-binding-precheck",))
# attacker copies the victim's MAC line onto its own object (header_mac string matches)
so = open(sub_obj, "rb").read(); vi = vobj.index(b"\n--- "); si = so.index(b"\n--- ")
v_mac_line = vobj[vi:vobj.index(b"\n", vi + 1) + 1]; s_end = so.index(b"\n", si + 1) + 1
open(P("evil", "maccopy.age"), "wb").write(so[:si] + v_mac_line + so[s_end:])
expect_reject("B4 attacker object carrying a copy of the victim's MAC line", "E_OBJECT_HMAC", victim["meta"], P("evil", "maccopy.age"))
# swap in another honest device object (legit2) under the victim's record
expect_reject("B3 another honest object presented under the victim's record", "E_BINDING_HEADER_MAC", victim["meta"], legit2["object"])

# ------------------------------------------------------------ C. truncation
CH = 65552
pl = vrec["object"]["prefix_len"]
body_len = len(vobj) - pl
last_len = body_len % CH or CH
open(P("evil", "drop_final.age"), "wb").write(vobj[: len(vobj) - last_len])
expect_reject("C1 dropped final chunk (record intact)", "E_BINDING_LENGTH", victim["meta"], P("evil", "drop_final.age"))
expect_reject("C2 dropped final chunk, binding pre-check disabled (TEST flag)", "E_STREAM_TRUNCATED", victim["meta"], P("evil", "drop_final.age"), extra=("--skip-binding-precheck",))
open(P("evil", "cut1.age"), "wb").write(vobj[:-1])
expect_reject("C3 one byte cut from the end", "E_BINDING_LENGTH", victim["meta"], P("evil", "cut1.age"))
expect_reject("C4 one byte cut, pre-check disabled", "E_STREAM_AUTH", victim["meta"], P("evil", "cut1.age"), extra=("--skip-binding-precheck",))
# multipart object whose payload ends exactly on a full chunk: dropping the final chunk leaves a valid non-final chunk at EOF
# use a fresh honest upload of the same shape so the record is not already committed
fresh_full = upload("fullchunks", 5 * 65536, k=2)
ff = open(fresh_full["object"], "rb").read()
open(P("evil", "ff_drop.age"), "wb").write(ff[: len(ff) - CH])
expect_reject("C5 full-chunk object, final chunk dropped at a chunk boundary", "E_BINDING_LENGTH", fresh_full["meta"], P("evil", "ff_drop.age"))
expect_reject("C6 same, pre-check disabled: STREAM final-flag check", "E_STREAM_TRUNCATED", fresh_full["meta"], P("evil", "ff_drop.age"), extra=("--skip-binding-precheck",))
open(P("evil", "append.age"), "wb").write(vobj + vobj[pl:pl + CH])
expect_reject("C7 trailing data appended after the final chunk", "E_BINDING_LENGTH", victim["meta"], P("evil", "append.age"))
expect_reject("C8 trailing data, pre-check disabled", "E_STREAM_AUTH", victim["meta"], P("evil", "append.age"), extra=("--skip-binding-precheck",))
# reorder two middle chunks
v = bytearray(vobj)
c0, c1 = v[pl:pl + CH], v[pl + CH:pl + 2 * CH]
v[pl:pl + CH], v[pl + CH:pl + 2 * CH] = c1, c0
open(P("evil", "reorder.age"), "wb").write(bytes(v))
expect_reject("C9 two chunks swapped (reordering)", "E_STREAM_AUTH", victim["meta"], P("evil", "reorder.age"))

# ------------------------------------------------------------ D. profile / downgrade (valid age files the profile forbids)
xid = P("evil", "x.id"); run([KEYGEN, "-o", xid])
open(P("evil", "x_rcpt.txt"), "w").write(run([KEYGEN, "-y", xid]).stdout.decode())
# homelab X25519 key does not exist in the PQ profile; attacker uses some X25519 key + the PQ key (mixed)
open(P("evil", "mixed.txt"), "w").write(hr + "\n" + open(P("evil", "x_rcpt.txt")).read())
mixed_obj = encrypt(sub, P("evil", "mixed.age"), P("evil", "mixed.txt"), ("--allow-mixed",))
expect_reject("D1 object with PQ + X25519 stanzas (downgrade)", "E_PROFILE", victim["meta"], mixed_obj)
grease_obj = encrypt(sub, P("evil", "grease.age"), extra=("--grease",))
expect_reject("D2 object with an extra unknown stanza (valid age, not in profile)", "E_PROFILE", victim["meta"], grease_obj)
# record encrypted to the PQ key plus an extra X25519 stanza
rec_pt = P("evil", "rec_from_victim.pt")
run([BIN, "decrypt", "--identity", P("home", "identity.txt"), "--in", victim["meta"], "--out", rec_pt])
expect_reject("D3 honest record re-encrypted with an extra X25519 stanza", "E_PROFILE", encrypt(rec_pt, P("evil", "rec_mixed.age"), P("evil", "mixed.txt"), ("--allow-mixed",)), victim["object"])
# low-order X25519 share inside the mlkem768x25519 stanza
hdr_end = vobj.index(b"\n---")
lines = vobj[:hdr_end].split(b"\n")
st = lines[1].split(b" ")
enc = bytearray(base64.b64decode(st[2] + b"=" * (-len(st[2]) % 4)))
enc[-32:] = bytes(32)
st[2] = base64.b64encode(bytes(enc)).rstrip(b"=")
lines[1] = b" ".join(st)
open(P("evil", "loworder.age"), "wb").write(b"\n".join(lines) + vobj[hdr_end:])
# (the MAC line is copied unchanged, so the record's header_mac string still matches;
#  the strict decoder must reject the low-order share before any decapsulation)
expect_reject("D4 victim object with its stanza's X25519 share set to a low-order point", "E_OBJECT_HEADER", victim["meta"], P("evil", "loworder.age"))

# ------------------------------------------------------------ E. registered-but-malicious device (holds dev-a key)
expect_reject("E1 record signed with dev-a key but device_id says dev-b", "E_DEVICE_MISMATCH",
              sign_record(dict(body, device_id="dev-b", object=None), P("dev", "device.key"), "dev-a", P("evil", "e1.age")), attacker="registered device")
lr = dict(lrec); lr.pop("pad", None)
expect_reject("E2 new record reusing a committed device_seq", "E_REPLAY_SEQ",
              sign_record(dict(lr, record_id="e" * 32), P("dev", "device.key"), "dev-a", P("evil", "e2.age")), legit["object"], attacker="registered device")
expect_reject("E3 committed record_id reused with different content", "E_REPLAY_RECORD_ID",
              sign_record(dict(lr, device_seq=777, size=lr["size"]), P("dev", "device.key"), "dev-a", P("evil", "e3.age")), legit["object"], attacker="registered device")
big = P("evil", "big.age"); open(big, "wb").write(os.urandom((1 << 20) + 1))
expect_reject("E4 oversized record (> 1 MiB)", "E_RECORD_TOO_LARGE", big)

# ------------------------------------------------------------ F. replay of an honest, committed record (idempotent, no new catalog row)
cat_before = open(P("home", "store", "catalog.jsonl")).read().count("\n")
rc, code, err = ingest(legit["meta"], legit["object"])
cat_after = open(P("home", "store", "catalog.jsonl")).read().count("\n")
check("F1 replayed honest record: idempotent (exit 0), no new catalog row, receipt re-issued", rc == 0 and cat_before == cat_after and "DUPLICATE" in err, {"rc": rc, "rows": [cat_before, cat_after]})
table.append({"attack": "F1 replay of a committed honest record", "attacker": "anyone with cloud access", "expected": "idempotent re-ack", "got": "duplicate" if rc == 0 else code, "exit": rc, "store_unchanged": cat_before == cat_after, "flags": ""})

# victim still ingests fine after all of that
rc, code, err = ingest(victim["meta"], victim["object"])
check("final: the untouched victim upload still ingests", rc == 0, err)
codes = sorted({t["expected"] for t in table})
json.dump({"table": table, "results": results, "codes": codes, "passed": sum(r["pass"] for r in results), "failed": sum(not r["pass"] for r in results)}, open(P("results.json"), "w"), indent=1)
print(json.dumps({"passed": sum(r["pass"] for r in results), "failed": sum(not r["pass"] for r in results), "codes": codes}))
sys.exit(0 if all(r["pass"] for r in results) else 1)
