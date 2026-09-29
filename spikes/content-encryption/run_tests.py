#!/usr/bin/env python3
"""End-to-end tests for the resumable age-object prototype (THROWAWAY SPIKE).

Every content object is decrypted by the Go `age` CLI (independent
implementation) and by the Rust `age` crate, and compared byte-for-byte with
the source. Metadata signatures are verified independently in Python
(`cryptography`), dedup IDs against a Python HKDF/HMAC reference. Every byte
the simulated network ever carried is logged per attempt, and the tests check
that no object offset was ever transmitted with two different values (the
keystream-reuse invariant).

Environment: CARGO_TARGET_DIR (default ./target; the binary is
$CARGO_TARGET_DIR/release/reliquary-enc-spike), WORK (default ./work, wiped at
start), AGE (default `age`), QUICK=1 skips the two slow tests.
"""
import fcntl, hashlib, hmac, json, os, random, shutil, stat, subprocess, sys, time

ROOT = os.path.dirname(os.path.abspath(__file__))
TARGET = os.environ.get("CARGO_TARGET_DIR", os.path.join(ROOT, "target"))
BIN = os.path.join(TARGET, "release", "reliquary-enc-spike")
WORK = os.environ.get("WORK", os.path.join(ROOT, "work"))
AGE = os.environ.get("AGE", "age")
ED25519_VERIFY = os.path.join(TARGET, "ed25519verify")
QUICK = os.environ.get("QUICK") == "1"
KEY = os.path.join(WORK, "key.txt")
RCPT = os.path.join(WORK, "recipient.txt")
FAMILY = "11" * 32
CHUNK_PT, CHUNK_CT, PREFIX = 65536, 65552, 184
PROD_K = 80
PROD_P = PROD_K * CHUNK_CT

results = []
H = {}  # homelab/device fixtures


def rec(name, ok, detail):
    results.append({"name": name, "passed": bool(ok), "detail": detail})
    print(("PASS " if ok else "FAIL ") + name + " :: " + detail, flush=True)


def run(args, check=True, **kw):
    p = subprocess.run(args, capture_output=True, **kw)
    if check and p.returncode != 0:
        raise RuntimeError(f"{args} -> {p.returncode}: {p.stderr.decode()[-800:]}")
    return p


def tool(*a, check=True):
    return run([BIN, *map(str, a)], check=check)


def jout(p):
    return json.loads(p.stdout.decode().strip().splitlines()[-1])


def stderr_json(p, tag):
    for l in p.stderr.decode().splitlines():
        if l.startswith(tag + " "):
            return json.loads(l[len(tag) + 1:])
    return None


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def hkdf(ikm, salt, info, n=32):
    prk = hmac.new(salt or b"\0" * 32, ikm, "sha256").digest()
    out, t, i = b"", b"", 1
    while len(out) < n:
        t = hmac.new(prk, t + info + bytes([i]), "sha256").digest()
        out += t
        i += 1
    return out[:n]


DEDUP_KEY = hkdf(bytes.fromhex(FAMILY), b"", b"reliquary/v1/dedup-key")


def dedup_ref(path):
    h = hmac.new(DEDUP_KEY, digestmod="sha256")
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def go_age_decrypt(obj, out, key=None):
    with open(out, "wb") as f:  # stdout redirect: age -o is lazy for empty plaintext
        return subprocess.run([AGE, "-d", "-i", key or KEY, obj], stdout=f, stderr=subprocess.PIPE)


def make_file(path, size, seed=None):
    rnd = random.Random(seed) if seed is not None else None
    with open(path, "wb") as f:
        left = size
        while left:
            n = min(left, 1 << 20)
            f.write(rnd.randbytes(n) if rnd else os.urandom(n))
            left -= n


def ct_len(size):
    return PREFIX + size + 16 * max(1, -(-size // CHUNK_PT))


# ------------------------------------------------------------------ fixtures

def setup():
    shutil.rmtree(WORK, ignore_errors=True)
    os.makedirs(WORK)
    env = {**os.environ, "CARGO_TARGET_DIR": TARGET}
    run(["cargo", "build", "--release", "--quiet"], cwd=ROOT, env=env)
    run(["go", "build", "-o", ED25519_VERIFY, os.path.join(ROOT, "tools", "ed25519verify.go")], cwd=ROOT)
    run(["age-keygen", "-o", KEY])
    open(RCPT, "w").write(run(["age-keygen", "-y", KEY]).stdout.decode())
    H["receipt_key"] = os.path.join(WORK, "homelab-receipt.key")
    H["receipt_pub"] = jout(tool("keygen-sign", "--out", H["receipt_key"]))["public_key"]
    H["trust"] = os.path.join(WORK, "trust.json")
    H["pin"] = jout(tool("make-trust", "--recipient-file", RCPT, "--receipt-pub", H["receipt_pub"], "--out", H["trust"]))["pin"]
    reg = {}
    for dev in ("alice", "bob", "carol", "evil", "unregistered"):
        k = os.path.join(WORK, f"device-{dev}.key")
        pub = jout(tool("keygen-sign", "--out", k))["public_key"]
        H[f"key-{dev}"] = k
        if dev != "unregistered":
            reg[dev] = pub
    H["registry"] = os.path.join(WORK, "devices.json")
    json.dump(reg, open(H["registry"], "w"))
    H["store"] = os.path.join(WORK, "homelab-store")


class Case:
    def __init__(self, label, size=None, seed=None):
        self.label = label
        self.dir = os.path.join(WORK, "cases", label)
        shutil.rmtree(self.dir, ignore_errors=True)
        os.makedirs(self.dir)
        self.src = os.path.join(self.dir, "src.bin")
        self.state = os.path.join(self.dir, "state")
        self.ks = os.path.join(self.dir, "keystore")
        self.r2 = os.path.join(self.dir, "r2")
        if size is not None:
            make_file(self.src, size, seed)

    def dev(self):
        return ["--state-dir", self.state, "--keystore", self.ks, "--r2", self.r2]

    def start(self, *extra, device="alice", src=None, check=False):
        p = tool("start", "--file", src or self.src, "--trust", H["trust"], "--trust-pin", H["pin"],
                 "--family-secret", FAMILY, "--device-id", device, "--device-key", H[f"key-{device}"],
                 *self.dev(), *extra, check=check)
        return p, stderr_json(p, "UPLOAD")

    def resume(self, uid, *extra, check=False):
        return tool("resume", "--upload-id", uid, *self.dev(), *extra, check=check)

    def complete(self, uid, check=True):
        return tool("complete", "--upload-id", uid, *self.dev(), check=check)

    def pending(self, uid):
        return os.path.join(self.state, "pending", uid + ".json")


def attempts_check(r2, object_key, part_size, obj=None):
    """No object offset was ever transmitted with two different values, and
    (if the final object is given) every transmitted byte equals it."""
    adir = os.path.join(r2, object_key, "attempts")
    groups = {}
    for f in sorted(os.listdir(adir)):
        name, _ = f.rsplit(".", 1)
        groups.setdefault(name, []).append(open(os.path.join(adir, f), "rb").read())
    n_att = sum(len(v) for v in groups.values())
    emitted = sum(len(a) for v in groups.values() for a in v)
    for name, atts in groups.items():
        off = 0 if name == "object" else (int(name.split("-")[1]) - 1) * part_size
        for i, A in enumerate(atts):
            for B in atts[i + 1:]:
                m = min(len(A), len(B))
                if A[:m] != B[:m]:
                    return False, f"{name}: two attempts differ"
            if obj is not None and obj[off:off + len(A)] != A:
                return False, f"{name}: attempt differs from final object"
    return True, f"attempts={n_att} parts_or_puts={len(groups)} bytes_on_wire={emitted}"


def verify_meta(meta_path, src, object_key, device="alice"):
    """Decrypt the metadata record with Go age; verify the Ed25519 signature
    with Go's crypto/ed25519 (independent of the Rust signer)."""
    pt = run([AGE, "-d", "-i", KEY, meta_path]).stdout
    line1, line2, rest = pt.split(b"\n", 2)
    body, sig = json.loads(line1), json.loads(line2)
    pub = json.load(open(H["registry"]))[sig["key_id"]]
    ok_sig = go_verify(pub, sig["sig"], b"reliquary-meta-v1\n" + line1)
    ok = ok_sig and (body["sha256"] == sha(src) and body["dedup_id"] == dedup_ref(src) and body["size"] == os.path.getsize(src)
          and len(pt) % 512 == 0 and rest.strip(b" ") == b"" and body["device_id"] == device == sig["key_id"]
          and (object_key is None and body["content_object"] is None or body["content_object"]["key"] == object_key))
    return ok, body


def go_verify(pub_b64, sig_b64, msg):
    path = os.path.join(WORK, "sigmsg.bin")
    open(path, "wb").write(msg)
    return subprocess.run([ED25519_VERIFY, pub_b64, sig_b64, path]).returncode == 0


def ingest(obj=None, meta=None, parts=None, out=None, store=None, check=False, receipt_key=None):
    args = ["ingest", "--identity", KEY, "--family-secret", FAMILY, "--registry", H["registry"],
            "--receipt-key", receipt_key or H["receipt_key"], "--store", store or H["store"], "--meta", meta, "--out", out]
    args += ["--object", obj] if obj else ["--parts", parts]
    return tool(*args, check=check)


def check_receipt(receipt, pending, *extra):
    return tool("check-receipt", "--trust", H["trust"], "--trust-pin", H["pin"], "--receipt", receipt,
                "--pending", pending, *extra, check=False)


# ------------------------------------------------------------------ main round trip

def upload_case(label, size, k=None, interrupts=(), shuffle=False, stream=None, sequential=False,
                tamper=False, random_access=False):
    c = Case(label, size)
    kargs = ["--chunks-per-part", k] if k else []
    opts = kargs + (["--shuffle"] if shuffle else []) + (["--stream-window", stream] if stream else []) \
        + (["--sequential-source"] if sequential else [])
    ia = ["--interrupt-after", interrupts[0]] if interrupts else []
    p, up = c.start(*opts, *ia)
    uid, okey, mode, P = up["upload_id"], up["object_key"], up["mode"], up["part_size"]
    num_parts = up["num_parts"]
    runs, resumed_generated, only_missing = 1, [], True
    if mode == "put" or not interrupts:
        assert p.returncode == 0, p.stderr
        out = jout(p)
    else:
        assert p.returncode == 75, p.stderr
        for n in list(interrupts[1:]) + [None]:
            ia = ["--interrupt-after", n] if n is not None else []
            p = c.resume(uid, *opts[len(kargs):], *ia)
            runs += 1
            if n is not None:
                assert p.returncode == 75, p.stderr
                continue
            assert p.returncode == 0, p.stderr
            out = jout(p)
            resumed_generated = out["generated_parts"]
            plan = stderr_json(p, "PLAN")
            done, todo = set(plan["already_completed"]), set(plan["todo"])
            only_missing = (set(resumed_generated) == todo and not (done & todo)
                            and done | todo == set(range(1, num_parts + 1)) and len(resumed_generated) == len(todo))
    if mode == "multipart":
        tool("regen-all", "--upload-id", uid, *c.dev(), "--out", os.path.join(c.dir, "regen.age"))
        cp = jout(c.complete(uid))
        obj = cp["object"]
    else:
        obj = out["object"]
    objb = open(obj, "rb").read()
    ok_len = len(objb) == ct_len(size)
    ok_det = mode == "put" or sha(obj) == sha(os.path.join(c.dir, "regen.age"))
    ok_wire, wire = attempts_check(c.r2, okey, P, objb)
    g = go_age_decrypt(obj, os.path.join(c.dir, "go.out"))
    ok_go = g.returncode == 0 and sha(os.path.join(c.dir, "go.out")) == sha(c.src)
    tool("age-crate", "--identity", KEY, "--object", obj, "--out", os.path.join(c.dir, "rs.out"))
    ok_rs = sha(os.path.join(c.dir, "rs.out")) == sha(c.src)
    pend = json.load(open(c.pending(uid)))
    ok_meta, _ = verify_meta(os.path.join(c.r2, pend["meta_key"]), c.src, okey)
    parts = sorted(f for f in os.listdir(os.path.join(c.r2, okey)) if f.startswith("part-"))
    sizes = [os.path.getsize(os.path.join(c.r2, okey, f)) for f in parts]
    ok_parts = mode == "put" or (len(parts) == num_parts and all(s == P for s in sizes[:-1]))
    # homelab ingest -> signed receipt -> device marks protected
    rpath = os.path.join(c.dir, "receipt")
    ig = ingest(obj=obj, meta=os.path.join(c.r2, pend["meta_key"]), out=rpath)
    cr = check_receipt(rpath, c.pending(uid), "--consume")
    ok_commit = ig.returncode == 0 and cr.returncode == 0 and not os.path.exists(c.pending(uid))
    leftovers = [f for d in (c.state, c.ks) if os.path.isdir(d) for f in os.listdir(d) if f not in ("pending",)]
    ok_clean = not leftovers
    detail = (f"mode={mode} size={size} parts={num_parts} part_size={P} runs={runs} interrupts={list(interrupts)} "
              f"stream_window={stream} sequential={sequential} final_resume_regenerated={resumed_generated or 'n/a'} "
              f"obj_len_ok={ok_len} regen_identical={ok_det} go_age_ok={ok_go} rust_age_crate_ok={ok_rs} "
              f"signed_meta_ok={ok_meta} equal_part_sizes={ok_parts} resume_only_missing={only_missing} "
              f"wire_consistent={ok_wire} ({wire}) ingest+receipt_ok={ok_commit} no_secrets_left={ok_clean}")
    rec(f"roundtrip:{label}", all([ok_len, ok_det, ok_go, ok_rs, ok_meta, ok_parts, only_missing, ok_wire, ok_commit, ok_clean]), detail)
    if random_access:
        random_access_suite(c, obj, size)
    if tamper:
        tamper_suite(c, obj, size)
    return c, obj, out


def random_access_suite(c, obj, size):
    n_chunks = max(1, -(-size // CHUNK_PT))
    mid = n_chunks // 2
    outp = os.path.join(c.dir, "chunk.out")
    src = open(c.src, "rb").read()
    tool("chunk", "--identity", KEY, "--object", obj, "--index", mid, "--expect-size", size, "--out", outp)
    ok1 = open(outp, "rb").read() == src[mid * CHUNK_PT:(mid + 1) * CHUNK_PT]
    off = mid * CHUNK_PT + 12345
    ln = min(100000, size - off)
    tool("age-crate", "--identity", KEY, "--object", obj, "--offset", off, "--len", ln, "--out", outp)
    ok2 = open(outp, "rb").read() == src[off:off + ln]
    tool("chunk", "--identity", KEY, "--object", obj, "--index", n_chunks - 1, "--out", outp)
    ok3 = open(outp, "rb").read() == src[(n_chunks - 1) * CHUNK_PT:]
    data = open(obj, "rb").read()
    tp = os.path.join(c.dir, "ra-tampered.age")

    def rejects(blob, *extra):
        open(tp, "wb").write(blob)
        return tool("chunk", "--identity", KEY, "--object", tp, "--index", min(1, n_chunks - 1), "--out", outp, *extra, check=False).returncode != 0

    b = bytearray(data); b[PREFIX + 1 * CHUNK_CT + 99] ^= 1
    ok4 = rejects(bytes(b))
    # reviewer finding: truncation exactly at a chunk boundary (final chunk dropped)
    ok5 = rejects(data[:PREFIX + (n_chunks - 1) * CHUNK_CT])
    ok6 = rejects(data[:PREFIX]) and rejects(data[:-(len(data) - PREFIX - (n_chunks - 1) * CHUNK_CT) + 5])
    ok7 = tool("chunk", "--identity", KEY, "--object", obj, "--index", 1, "--expect-size", size + 1, "--out", outp, check=False).returncode != 0
    rec(f"random-access:{c.label}", all([ok1, ok2, ok3, ok4, ok5, ok6, ok7]),
        f"chunk {mid}/{n_chunks} via prefix+final+one range read={ok1}; age crate seek {off} len {ln}={ok2}; final chunk={ok3}; "
        f"bitflip rejected={ok4}; truncated-at-chunk-boundary rejected by range read={ok5}; invalid length classes (header only, final chunk of 5 bytes) rejected={ok6}; "
        f"catalog size mismatch rejected={ok7}")


def tamper_suite(c, obj, size):
    data = open(obj, "rb").read()
    n_chunks = max(1, -(-size // CHUNK_PT))
    cs = lambda i: PREFIX + i * CHUNK_CT
    v = {"truncate-drop-final-chunk": data[:cs(n_chunks - 1)], "truncate-mid-final-chunk": data[:len(data) - 100],
         "truncate-1-byte": data[:-1], "truncate-to-header-only": data[:PREFIX]}
    if n_chunks >= 3:
        c1, c2 = data[cs(1):cs(2)], data[cs(2):cs(3)]
        v["reorder-swap-chunks-1-2"] = data[:cs(1)] + c2 + c1 + data[cs(3):]
        v["duplicate-chunk-1"] = data[:cs(2)] + data[cs(1):cs(2)] + data[cs(2):]
    b = bytearray(data); b[min(cs(n_chunks // 2) + 777, len(data) - 1)] ^= 1; v["bitflip-payload"] = bytes(b)
    b = bytearray(data); b[-1] ^= 0x80; v["bitflip-final-tag"] = bytes(b)
    b = bytearray(data); b[60] ^= 0x04; v["bitflip-header-stanza"] = bytes(b)
    b = bytearray(data); b[170] ^= 1; v["bitflip-payload-nonce"] = bytes(b)
    v["append-trailing-bytes"] = data + b"\0" * 16
    P = 2 * CHUNK_CT
    if len(data) > 3 * P:
        parts = [data[i:i + P] for i in range(0, len(data), P)]
        parts[1], parts[2] = parts[2], parts[1]
        v["reorder-swap-parts-2-3"] = b"".join(parts)
    for name, blob in v.items():
        tp = os.path.join(c.dir, "tampered.age")
        open(tp, "wb").write(blob)
        g = go_age_decrypt(tp, os.path.join(c.dir, "t.out"))
        r = tool("age-crate", "--identity", KEY, "--object", tp, "--out", os.path.join(c.dir, "t2.out"), check=False)
        rec(f"tamper:{c.label}:{name}", g.returncode != 0 and r.returncode != 0,
            f"go age exit={g.returncode} ({next((l for l in g.stderr.decode().splitlines() if 'error' in l), '')[:100]}); rust age crate exit={r.returncode}")


# ------------------------------------------------------------------ safety tests

def edit(path, off, data=b"CHANGED!", keep_mtime=False):
    st = os.stat(path)
    with open(path, "r+b") as f:
        f.seek(off)
        f.write(data)
    if keep_mtime:
        os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns))
    else:
        os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns + 5_000_000_000))


def safety_tests():
    # S1 reviewer scenario: edit inside an ALREADY-UPLOADED part, mtime changes.
    c = Case("s1-edit-completed-region", 1_000_000)
    p, up = c.start("--chunks-per-part", 2, "--interrupt-after", 3)
    old = sha(c.src)
    edit(c.src, 1000)
    r = c.resume(up["upload_id"])
    refused = r.returncode == 65 and b"SOURCE CHANGED since the pass-1 snapshot" in r.stderr
    ok_wire, _ = attempts_check(c.r2, up["object_key"], up["part_size"])
    tool("abort", "--upload-id", up["upload_id"], *c.dev())
    p2, up2 = c.start("--chunks-per-part", 2)
    obj = jout(c.complete(up2["upload_id"]))["object"]
    g = go_age_decrypt(obj, os.path.join(c.dir, "go.out"))
    new_ok = g.returncode == 0 and sha(os.path.join(c.dir, "go.out")) == sha(c.src) != old
    rec("safety:edit-in-uploaded-region-detected-by-snapshot", refused and ok_wire and new_ok and up2["upload_id"] != up["upload_id"],
        f"resume exit={r.returncode} ({r.stderr.decode().strip().splitlines()[-1][:90]}); wire consistent={ok_wire}; "
        f"after abort+restart (fresh key) the new object decrypts to the CURRENT file={new_ok}")

    # S2 buffered part, tags recorded, source edited invisibly to stat -> tag check refuses.
    c = Case("s2-invisible-edit-interrupted-part", 1_000_000)
    p, up = c.start("--chunks-per-part", 2, "--interrupt-after", 3)
    edit(c.src, 6 * CHUNK_PT + 1000, keep_mtime=True)  # chunk 6, inside interrupted part 4
    r = c.resume(up["upload_id"], "--no-stat-check")
    ok_wire, wire = attempts_check(c.r2, up["object_key"], up["part_size"])
    att2 = os.path.join(c.r2, up["object_key"], "attempts", "part-00004.2")
    zero = os.path.getsize(att2) == 0
    rec("safety:invisible-edit-in-transmitted-chunk-refused (buffered)", r.returncode == 65 and b"SOURCE CHANGED in chunk 6" in r.stderr and ok_wire and zero,
        f"resume exit={r.returncode}; bytes sent in retry attempt={os.path.getsize(att2)}; wire consistent={ok_wire} ({wire})")

    # S3 streaming (window = 1 chunk): chunk 8 was already streamed, then edited.
    c = Case("s3-invisible-edit-streamed", 2_000_000)
    p, up = c.start("--chunks-per-part", 4, "--stream-window", 1, "--interrupt-after", 2)
    a1 = os.path.join(c.r2, up["object_key"], "attempts", "part-00003.1")
    sent1 = os.path.getsize(a1)
    edit(c.src, 8 * CHUNK_PT + 5000, keep_mtime=True)
    r = c.resume(up["upload_id"], "--no-stat-check", "--stream-window", 1)
    ok_wire, wire = attempts_check(c.r2, up["object_key"], up["part_size"])
    sent2 = os.path.getsize(os.path.join(c.r2, up["object_key"], "attempts", "part-00003.2"))
    rec("safety:invisible-edit-in-streamed-chunk-refused (streaming)", r.returncode == 65 and b"chunk 8" in r.stderr and ok_wire and sent2 < sent1,
        f"first attempt streamed {sent1} B of part 3 then was cut; retry re-sent {sent2} B (identical, unchanged chunk 7 tail) and stopped before chunk 8; "
        f"resume exit={r.returncode}; no offset sent with two values={ok_wire}")

    # S4 streaming, edit in a chunk never transmitted: resume succeeds without
    # key reuse, but the object no longer matches pass 1 -> homelab rejects, no receipt.
    c = Case("s4-invisible-edit-untransmitted", 2_000_000)
    p, up = c.start("--chunks-per-part", 4, "--stream-window", 1, "--interrupt-after", 2)
    edit(c.src, 10 * CHUNK_PT + 5000, keep_mtime=True)
    r = c.resume(up["upload_id"], "--no-stat-check", "--stream-window", 1)
    obj = jout(c.complete(up["upload_id"]))["object"]
    ok_wire, _ = attempts_check(c.r2, up["object_key"], up["part_size"], open(obj, "rb").read())
    pend = json.load(open(c.pending(up["upload_id"])))
    store = os.path.join(c.dir, "store")
    ig = ingest(obj=obj, meta=os.path.join(c.r2, pend["meta_key"]), out=os.path.join(c.dir, "receipt"), store=store)
    rec("safety:invisible-edit-untransmitted-caught-end-to-end", r.returncode == 0 and ok_wire and ig.returncode == 10
        and not os.path.exists(os.path.join(c.dir, "receipt")) and not os.listdir(os.path.join(store, "objects")),
        f"resume exit={r.returncode} (no keystream reuse: wire consistent={ok_wire}); ingest exit={ig.returncode} "
        f"({ig.stderr.decode().strip()[:100]}); no receipt, nothing stored, file stays 'not yet backed up'")

    # S5 same as S4 but with the default stat check: refused at resume.
    c = Case("s5-edit-untransmitted-stat", 2_000_000)
    p, up = c.start("--chunks-per-part", 4, "--interrupt-after", 2)
    edit(c.src, 10 * CHUNK_PT + 5000)
    r = c.resume(up["upload_id"])
    rec("safety:edit-untransmitted-detected-by-snapshot", r.returncode == 65, f"resume exit={r.returncode}")

    # Pass 1 instability is reported, not hashed into a wrong dedup ID (simulated by a writer racing pass 1).
    c = Case("s6-unstable", 256 * 1024 * 1024)
    w = subprocess.Popen([sys.executable, "-c", f"import time,os\nfor i in range(600):\n  f=open({c.src!r},'r+b'); f.seek(i*1000); f.write(b'x'); f.close(); time.sleep(0.005)"])
    p, up = c.start()
    w.wait()
    rec("safety:source-written-during-pass1", p.returncode == 69 and up is None, f"start exit={p.returncode}: {p.stderr.decode().strip()[:110]}")


def state_tests():
    c = Case("state-hardening", 300_000)
    p, up = c.start("--chunks-per-part", 1, "--interrupt-after", 1)
    uid = up["upload_id"]
    sp, jp = os.path.join(c.state, uid + ".state"), os.path.join(c.state, uid + ".journal")
    kp = os.path.join(c.ks, uid + ".key")
    raw = open(sp, "rb").read()
    modes = {n: oct(stat.S_IMODE(os.stat(x).st_mode)) for n, x in (("keystore", kp), ("state", sp), ("journal", jp), ("device-key", H["key-alice"]))}
    ok_modes = all(m == "0o600" for m in modes.values())
    no_plain = b"payload_key" not in raw and c.src.encode() not in raw
    results_ = {}

    def attempt(name, mutate):
        shutil.copy(sp, sp + ".bak"); shutil.copy(jp, jp + ".bak")
        mutate()
        r = c.resume(uid)
        results_[name] = r.returncode
        shutil.copy(sp + ".bak", sp); shutil.copy(jp + ".bak", jp)

    attempt("state-truncated-20B", lambda: open(sp, "wb").write(raw[:20]))
    attempt("state-bitflip", lambda: open(sp, "wb").write(raw[:-5] + bytes([raw[-5] ^ 1]) + raw[-4:]))
    jraw = open(jp, "rb").read()
    attempt("journal-bitflip-first-record", lambda: open(jp, "wb").write(jraw[:12] + bytes([jraw[12] ^ 1]) + jraw[13:]))
    ok_corrupt = all(v == 76 for v in results_.values())
    # torn tail of the journal (crash mid-append): tolerated
    open(jp, "ab").write(b"\x01\x00\x00\x00\x30garbage")
    r_torn = c.resume(uid, "--interrupt-after", 0)
    # held lock -> BUSY, then clean resume
    lf = open(os.path.join(c.state, uid + ".lock"), "a")
    fcntl.flock(lf, fcntl.LOCK_EX)
    r_busy = c.resume(uid)
    fcntl.flock(lf, fcntl.LOCK_UN); lf.close()
    shutil.copy(sp, os.path.join(c.dir, "stale-state-copy"))
    r_ok = c.resume(uid)
    c.complete(uid)
    key_gone = not os.path.exists(kp)
    shutil.copy(os.path.join(c.dir, "stale-state-copy"), sp)
    r_stale = c.resume(uid)
    rec("safety:state-hardening", ok_modes and no_plain and ok_corrupt and r_torn.returncode == 75 and r_busy.returncode == 73
        and r_ok.returncode == 0 and key_gone and r_stale.returncode == 76,
        f"file modes={modes}; sealed state has no plaintext names/paths={no_plain}; corrupt state/journal exit codes={results_} (76 = abort+restart, no panic); "
        f"torn journal tail tolerated (resume reached next part)={r_torn.returncode == 75}; lock held elsewhere -> exit {r_busy.returncode}; "
        f"per-upload key deleted on completion={key_gone}; stale state copy after completion unusable (exit {r_stale.returncode})")

    # source deleted before resume -> defined outcome, no panic
    c = Case("source-missing", 300_000)
    p, up = c.start("--chunks-per-part", 1, "--interrupt-after", 1)
    os.remove(c.src)
    r = c.resume(up["upload_id"])
    rec("safety:source-missing", r.returncode == 66 and b"panicked" not in r.stderr, f"resume exit={r.returncode}: {r.stderr.decode().strip()[:90]}")

    # two concurrent resumers of one upload: one wins, the other exits BUSY, result valid
    c = Case("concurrent-resume", 200 * CHUNK_PT)
    p, up = c.start("--chunks-per-part", 1, "--interrupt-after", 0)
    procs = [subprocess.Popen([BIN, "resume", "--upload-id", up["upload_id"], *c.dev()], stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(2)]
    codes = sorted(pp.wait() for pp in procs)
    left = c.resume(up["upload_id"])
    obj = jout(c.complete(up["upload_id"]))["object"]
    g = go_age_decrypt(obj, os.path.join(c.dir, "go.out"))
    ok_wire, wire = attempts_check(c.r2, up["object_key"], up["part_size"], open(obj, "rb").read())
    rec("safety:concurrent-resumers", set(codes) <= {0, 73} and 0 in codes and left.returncode == 0 and g.returncode == 0
        and sha(os.path.join(c.dir, "go.out")) == sha(c.src) and ok_wire,
        f"exit codes={codes} (73 = BUSY, no panic); final object decrypts with Go age={g.returncode == 0}; wire consistent={ok_wire}")


def put_interrupt_test():
    c = Case("put-interrupted", 100_000)
    p, up = c.start("--interrupt-after", 0)
    first = open(os.path.join(c.r2, up["object_key"], "attempts", "object.1"), "rb").read()
    p2, up2 = c.start()
    obj = jout(p2)["object"]
    ob = open(obj, "rb").read()
    g = go_age_decrypt(obj, os.path.join(c.dir, "go.out"))
    no_state = not os.path.isdir(c.ks) or not os.listdir(c.ks)
    rec("put:interrupted-single-put-restarts-with-fresh-key", p.returncode == 75 and up["mode"] == "put" and first[:PREFIX] != ob[:PREFIX]
        and up["object_key"] != up2["object_key"] and g.returncode == 0 and sha(os.path.join(c.dir, "go.out")) == sha(c.src) and no_state,
        f"objects <= 1 part use one PUT, no resume state (keystore empty={no_state}); retry has a different header/key={first[:PREFIX] != ob[:PREFIX]} "
        f"and a different staging key; decrypts with Go age={g.returncode == 0}")


def trust_tests():
    c = Case("trust", 1000)
    wrong_pin = c.start("--chunks-per-part", 1, check=False)[0]
    # attacker substitutes its own recipient in the bundle (e.g. a compromised Worker)
    evil_key = os.path.join(c.dir, "evil.txt")
    run(["age-keygen", "-o", evil_key])
    evil_rcpt = run(["age-keygen", "-y", evil_key]).stdout.decode().strip()
    tb = json.load(open(H["trust"]))
    subst = os.path.join(c.dir, "subst.json")
    json.dump({**tb, "recipient": evil_rcpt}, open(subst, "w"))
    p_sub = tool("start", "--file", c.src, "--trust", subst, "--trust-pin", H["pin"], "--family-secret", FAMILY,
                 "--device-id", "alice", "--device-key", H["key-alice"], *c.dev(), check=False)
    # uppercase and Bech32m encodings of the real recipient, with matching pins
    def with_rcpt(r):
        path = os.path.join(c.dir, "t.json")
        data = json.dumps({**tb, "recipient": r}).encode()
        open(path, "wb").write(data)
        return tool("start", "--file", c.src, "--trust", path, "--trust-pin", hashlib.sha256(data).hexdigest(), "--family-secret", FAMILY,
                    "--device-id", "alice", "--device-key", H["key-alice"], *c.dev(), check=False)
    p_up = with_rcpt(tb["recipient"].upper())
    p_m = with_rcpt(bech32m_reencode(tb["recipient"]))
    p_bad = tool("start", "--file", c.src, "--trust", H["trust"], "--trust-pin", "00" * 32, "--family-secret", FAMILY,
                 "--device-id", "alice", "--device-key", H["key-alice"], *c.dev(), check=False)
    ok = all(x.returncode == 2 and b"TRUST REFUSED" in x.stderr for x in (p_sub, p_up, p_m, p_bad))
    rec("trust:recipient-pinning-and-strict-parsing", ok and wrong_pin.returncode == 0,
        f"substituted recipient refused={p_sub.returncode}; uppercase refused={p_up.returncode}; bech32m refused={p_m.returncode}; wrong pin refused={p_bad.returncode}")


def bech32m_reencode(s):
    CH = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
    hrp, data = s.split("1", 1)
    d = [CH.index(x) for x in data[:-6]]

    def polymod(v):
        g = [0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3]
        chk = 1
        for x in v:
            b = chk >> 25
            chk = (chk & 0x1ffffff) << 5 ^ x
            for i in range(5):
                chk ^= g[i] if (b >> i) & 1 else 0
        return chk
    hx = [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]
    pm = polymod(hx + d + [0] * 6) ^ 0x2bc830a3
    return hrp + "1" + "".join(CH[x] for x in d) + "".join(CH[(pm >> 5 * (5 - i)) & 31] for i in range(6))


def commit_tests():
    """Receipts, dedup hits, signed metadata, poisoning, ingest atomicity, USB bundles."""
    store = os.path.join(WORK, "commit-store")
    a = Case("commit-alice", 3 * CHUNK_PT + 999, seed=7)
    p, up = a.start("--chunks-per-part", 1, "--interrupt-after", 1)
    a.resume(up["upload_id"])
    obj = jout(a.complete(up["upload_id"]))["object"]
    pend = json.load(open(a.pending(up["upload_id"])))
    meta = os.path.join(a.r2, pend["meta_key"])
    r_ok = os.path.join(a.dir, "receipt")

    # Poisoning first (empty store): a registered-but-malicious device uploads other content
    # under a metadata record claiming Alice's dedup_id/sha256/size.
    e = Case("commit-evil", 3 * CHUNK_PT + 999, seed=8)
    p, upe = e.start("--chunks-per-part", 1, device="evil")
    eobj = jout(e.complete(upe["upload_id"]))["object"]
    epend = json.load(open(e.pending(upe["upload_id"])))
    _, ebody = verify_meta(os.path.join(e.r2, epend["meta_key"]), e.src, upe["object_key"], device="evil")
    forged = {**ebody, "dedup_id": pend["dedup_id"], "sha256": pend["sha256"]}
    fpath = os.path.join(e.dir, "forged.json"); json.dump(forged, open(fpath, "w"))
    fmeta = os.path.join(e.dir, "forged-meta.age")
    tool("sign-meta", "--trust", H["trust"], "--trust-pin", H["pin"], "--device-key", H["key-evil"], "--key-id", "evil", "--body", fpath, "--out", fmeta)
    ig_poison = ingest(obj=eobj, meta=fmeta, out=os.path.join(e.dir, "r"), store=store)
    # honest metadata + wrong object (swap) -> header MAC binding rejects
    ig_swap = ingest(obj=eobj, meta=meta, out=os.path.join(e.dir, "r"), store=store)
    # impersonation: evil signs a record with device_id "alice"
    json.dump({**ebody, "device_id": "alice"}, open(fpath, "w"))
    tool("sign-meta", "--trust", H["trust"], "--trust-pin", H["pin"], "--device-key", H["key-evil"], "--key-id", "evil", "--body", fpath, "--out", fmeta)
    ig_imp = ingest(obj=eobj, meta=fmeta, out=os.path.join(e.dir, "r"), store=store)
    tool("sign-meta", "--trust", H["trust"], "--trust-pin", H["pin"], "--device-key", H["key-evil"], "--key-id", "alice", "--body", fpath, "--out", fmeta)
    ig_imp2 = ingest(obj=eobj, meta=fmeta, out=os.path.join(e.dir, "r"), store=store)
    # unregistered device
    u = Case("commit-unreg", 5000)
    p, upu = u.start(device="unregistered")
    upend = json.load(open(u.pending(upu["upload_id"])))
    ig_unreg = ingest(obj=jout(p)["object"], meta=os.path.join(u.r2, upend["meta_key"]), out=os.path.join(u.dir, "r"), store=store)
    # truncated object (final chunk dropped at a chunk boundary) is never committed
    tr = os.path.join(a.dir, "trunc.age")
    open(tr, "wb").write(open(obj, "rb").read()[:PREFIX + 3 * CHUNK_CT])
    ig_trunc = ingest(obj=tr, meta=meta, out=os.path.join(a.dir, "r-trunc"), store=store)
    # a dedup-hit record before the content is committed: pending, no receipt
    b = Case("commit-bob", None)
    shutil.copy(a.src, b.src)
    hit = jout(tool("dedup-hit", "--file", b.src, "--trust", H["trust"], "--trust-pin", H["pin"], "--family-secret", FAMILY,
                    "--device-id", "bob", "--device-key", H["key-bob"], *b.dev()))
    bpend = json.load(open(b.pending(hit["upload_id"])))
    ig_early = ingest(meta=os.path.join(b.r2, bpend["meta_key"]), obj=None, parts=os.path.join(b.dir, "none"), out=os.path.join(b.dir, "r"), store=store)
    nothing = not os.listdir(os.path.join(store, "objects")) and not os.listdir(os.path.join(store, "tmp")) and not os.path.exists(os.path.join(e.dir, "r"))
    rejections = {"poison(meta claims other dedup_id)": ig_poison.returncode, "swap(meta for other object)": ig_swap.returncode,
                  "impersonate(device_id=alice,key=evil)": ig_imp.returncode, "impersonate(key_id=alice)": ig_imp2.returncode,
                  "unregistered device": ig_unreg.returncode, "truncated object": ig_trunc.returncode, "dedup-hit before commit": ig_early.returncode}
    rec("commit:ingest-rejections", all(v == 10 for k, v in rejections.items() if "before" not in k) and ig_early.returncode == 11 and nothing,
        f"exit codes={rejections} (10 = rejected, 11 = pending); store still empty, no temp plaintext left, no receipt={nothing}")

    # USB-style bundle: the object split at part boundaries
    ig = ingest(parts=os.path.join(a.r2, up["object_key"]), meta=meta, out=r_ok, store=store)
    good = check_receipt(r_ok, a.pending(up["upload_id"]))
    # forged receipts
    bad_key = os.path.join(WORK, "not-the-homelab.key")
    if not os.path.exists(bad_key):
        tool("keygen-sign", "--out", bad_key)
    r_forged = os.path.join(a.dir, "receipt-forged")
    ingest(obj=obj, meta=meta, out=r_forged, store=os.path.join(a.dir, "store2"), receipt_key=bad_key, check=True)
    f1 = check_receipt(r_forged, a.pending(up["upload_id"]))
    rr = open(r_ok, "rb").read()
    r_tamp = os.path.join(a.dir, "receipt-tampered")
    open(r_tamp, "wb").write(rr.replace(b'"size":%d' % (3 * CHUNK_PT + 999), b'"size":%d' % (3 * CHUNK_PT + 998)))
    f2 = check_receipt(r_tamp, a.pending(up["upload_id"]))
    # Bob's dedup hit: Alice's receipt proves the CONTENT is committed (relayed by the Worker)...
    content = check_receipt(r_ok, b.pending(hit["upload_id"]), "--content-only")
    # ...but is not Bob's own file-record receipt
    f3 = check_receipt(r_ok, b.pending(hit["upload_id"]))
    rb = os.path.join(b.dir, "receipt")
    igb = ingest(meta=os.path.join(b.r2, bpend["meta_key"]), parts=os.path.join(b.dir, "none"), out=rb, store=store)
    own = check_receipt(rb, b.pending(hit["upload_id"]), "--consume")
    cat = [json.loads(l) for l in open(os.path.join(store, "catalog.jsonl"))]
    ok_cat = len(cat) == 2 and {x["record"]["device_id"] for x in cat} == {"alice", "bob"} and cat[1]["record"]["content_object"] is None
    rec("commit:signed-receipts", ig.returncode == 0 and good.returncode == 0 and f1.returncode == 12 and f2.returncode == 12
        and content.returncode == 0 and f3.returncode == 12 and igb.returncode == 0 and own.returncode == 0 and ok_cat,
        f"USB-style part-file bundle ingested={ig.returncode == 0}; valid receipt accepted={good.returncode == 0}; receipt signed by another key rejected={f1.returncode == 12}; "
        f"tampered receipt rejected={f2.returncode == 12}; Alice's receipt accepted by Bob as content-only proof={content.returncode == 0} "
        f"but not as Bob's own record={f3.returncode == 12}; Bob's dedup-hit record committed + own receipt={own.returncode == 0}; catalog has both records={ok_cat}")


def sequential_test():
    size = 19 * CHUNK_PT + 100  # 20 chunks, 20 parts at k=1
    res = {}
    for label, per_wake in (("all-in-one-wake", None), ("5-parts-per-wake", 5), ("1-part-per-wake", 1)):
        c = Case(f"seq-{label}", size, seed=3)
        extra = ["--chunks-per-part", 1, "--sequential-source"] + (["--max-parts", per_wake] if per_wake else [])
        p, up = c.start(*extra)
        outs = [jout(p)]
        while outs[-1]["remaining_parts"]:
            outs.append(jout(c.resume(up["upload_id"], *extra[2:], check=True)))
        obj = jout(c.complete(up["upload_id"]))["object"]
        g = go_age_decrypt(obj, os.path.join(c.dir, "go.out"))
        res[label] = {"wakes": len(outs), "source_bytes_read": sum(o["source_bytes_read"] for o in outs),
                      "restarts": sum(o["source_restarts"] for o in outs), "chunks_encrypted": sum(o["chunks_encrypted"] for o in outs),
                      "ok": g.returncode == 0 and sha(os.path.join(c.dir, "go.out")) == sha(c.src)}
    one, five, single = res["all-in-one-wake"], res["5-parts-per-wake"], res["1-part-per-wake"]
    ok = (all(r["ok"] for r in res.values()) and one["source_bytes_read"] == size and one["restarts"] == 0 and one["chunks_encrypted"] == 20
          and five["source_bytes_read"] <= 4 * size and single["source_bytes_read"] > 2 * five["source_bytes_read"])
    rec("ios:forward-only-source-spool", ok,
        f"plaintext {size} B, 20 parts; {json.dumps(res)}; one sequential stream per wake reads each byte once and encrypts each boundary chunk once (cache)")


def write_amp_test():
    size = 10_000 * CHUNK_PT - 200
    c = Case("write-amp-10000-parts", size)
    t = time.time()
    p, up = c.start("--chunks-per-part", 1)
    out = jout(p)
    dt = time.time() - t
    state_sz = os.path.getsize(os.path.join(c.state, up["upload_id"] + ".state"))
    j_sz = os.path.getsize(os.path.join(c.state, up["upload_id"] + ".journal"))
    # write_bytes is accounted per dirtied 4 KiB page: each part file costs its
    # page-rounded size; every fsynced journal append re-dirties one page.
    adir = os.path.join(c.r2, up["object_key"], "attempts")
    part_pages = sum(-(-os.path.getsize(os.path.join(adir, f)) // 4096) * 4096 for f in os.listdir(adir))
    overhead = out["io_write_bytes"] - part_pages
    per_part = overhead / up["num_parts"]
    c.complete(up["upload_id"])
    rec("state:write-amplification-10000-parts", up["num_parts"] == 10_000 and j_sz < 2_000_000 and per_part <= 2.2 * 4096,
        f"parts={up['num_parts']}; sealed state written once={state_sz} B; journal file={j_sz} B (2 fsynced appends per part); "
        f"process write_bytes={out['io_write_bytes']} = part files {part_pages} (page-rounded) + state/journal/meta {overhead} "
        f"= {per_part:.0f} B per part (two 4 KiB page writes); previous prototype rewrote the whole state per part: ~10.4 GB at 10,000 parts; wall {dt:.1f}s")
    shutil.rmtree(c.dir)


def rss_test():
    size = 200 * 1024 * 1024 + 12345
    res = {}
    for label, extra in (("buffered", []), ("stream-w16", ["--stream-window", 16])):
        c = Case(f"rss-{label}", size, seed=5)
        p, up = c.start(*extra, check=True)
        res[label] = jout(p)["peak_rss_kb"]
        shutil.rmtree(c.dir)
    rec("memory:peak-rss-200MiB", res["stream-w16"] < res["buffered"] and res["stream-w16"] < 8000,
        f"peak RSS kB: {res} (buffered holds one 5,244,160 B part; streaming holds 16 chunks = 1 MiB)")


def cargo_unit_tests():
    p = run(["cargo", "test", "--release", "--quiet"], check=False, cwd=ROOT,
            env={**os.environ, "CARGO_TARGET_DIR": TARGET})
    line = next((l for l in p.stdout.decode().splitlines() if l.startswith("test result")), p.stderr.decode()[-200:])
    rec("unit:cargo-test", p.returncode == 0, line)


def main():
    setup()
    cargo_unit_tests()
    for label, s in [("0B", 0), ("1B", 1), ("1chunk", CHUNK_PT), ("1chunk+1", CHUNK_PT + 1)]:
        upload_case(label + "-prod", s, tamper=True)
        upload_case(label + "-k1", s, k=1, interrupts=(0,) if s > CHUNK_PT - 200 else ())
    rnd = random.Random(1234)
    edge = []
    for k in (1, 2, 3):
        P = k * CHUNK_CT
        for m in (1, 2, 5):
            for delta in (-17, -16, -1, 0, 1, 15, 16, 17):
                ctp = m * P - PREFIX + delta
                if ctp >= 16:
                    edge.append((k, ctp))
    for i, (k, ctp) in enumerate(edge):
        size = max(0, ctp - 16 * (-(-ctp // CHUNK_CT)))
        nparts = -(-ct_len(size) // (k * CHUNK_CT))
        ints = tuple(sorted(rnd.sample(range(0, nparts), min(2, nparts)))) if nparts > 1 else ()
        ints = tuple(x if j == 0 else 0 for j, x in enumerate(ints))
        upload_case(f"edge{i}-k{k}-{size}", size, k=k, interrupts=ints, shuffle=(i % 2 == 1),
                    stream=1 if i % 4 >= 2 else None, sequential=(i % 8 == 5))
    upload_case("200MiB", 200 * 1024 * 1024 + 12345, interrupts=(7, 9), tamper=True, random_access=True)
    upload_case("200MiB-stream", 200 * 1024 * 1024 + 777, interrupts=(3, 5), stream=16)
    upload_case("3chunks-k1", 3 * CHUNK_PT + 5, k=1, interrupts=(1,), tamper=True, random_access=True)
    put_interrupt_test()
    safety_tests()
    state_tests()
    trust_tests()
    commit_tests()
    sequential_test()
    if not QUICK:
        rss_test()
        write_amp_test()
    passed = sum(r["passed"] for r in results)
    print(f"\n{passed}/{len(results)} passed")
    json.dump(results, open(os.path.join(WORK, "results.json"), "w"), indent=1)
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
