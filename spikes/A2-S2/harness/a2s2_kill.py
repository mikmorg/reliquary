#!/usr/bin/env python3
"""THROWAWAY SPIKE harness for A2-S2 (kill-and-resume with PQ headers). Not production.

Real SIGKILLs at uniformly random times during `start` / `resume` of
multipart uploads whose objects carry a 1-stanza (1,643-byte prefix) or
2-stanza (3,200-byte prefix) mlkem768x25519 header. After every kill the
upload is resumed (and may be killed again) until it finishes; then
complete -> homelab ingest -> receipt check -> Go age decrypt.

Checks (PLAN A2-S2):
  * every object decrypts (Go age 1.3.2 and the Rust decoder) to the exact SHA-256;
  * at most one part (segment) is re-encrypted/re-sent per kill;
  * no (key, nonce) reuse: every byte ever transmitted for an object offset is
    identical across attempts (wire consistency), payload nonces / stanza encs
    are unique across uploads, and an edit after a kill is refused (exit 65);
  * no file key or payload key survives commit anywhere on the device side.

Environment: BIN, AGE, AGE_KEYGEN, WORK, KILLS (default 50), SEED (optional).
"""
import base64, glob, hashlib, json, os, random, shutil, signal, subprocess, sys, time

BIN = os.environ["BIN"]; AGE = os.environ["AGE"]; KEYGEN = os.environ["AGE_KEYGEN"]; WORK = os.environ["WORK"]
KILLS = int(os.environ.get("KILLS", "50")); STANZAS = int(os.environ.get("STANZAS", "1"))
rng = random.Random(int(os.environ.get("SEED", str(int(time.time())))))
SLOW_US = os.environ.get("A2_SLOW_US", "3000")
shutil.rmtree(WORK, ignore_errors=True); os.makedirs(WORK)
P = lambda *a: os.path.join(WORK, *a)
results = []

def check(name, ok, detail=""):
    results.append({"check": name, "pass": bool(ok), "detail": detail})
    print(("PASS " if ok else "FAIL ") + name + (" :: " + str(detail) if detail != "" else ""), flush=True)

def run(cmd, env=None):
    return subprocess.run(cmd, capture_output=True, env=env)

def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()

# ------------------------------------------------------------ setup
for d in ["dev", "dev/state", "dev/keystore", "r2", "home", "home/store", "src"]:
    os.makedirs(P(d), exist_ok=True)
ids = []
for i in range(STANZAS):
    run([KEYGEN, "-pq", "-o", P("home", f"id{i}.txt")])
    ids.append(P("home", f"id{i}.txt"))
with open(P("home", "identity.txt"), "w") as f:
    f.write("".join(open(i).read() for i in ids))
with open(P("home", "recipients.txt"), "w") as f:
    f.write("\n".join(run([KEYGEN, "-y", i]).stdout.decode().strip() for i in ids) + "\n")
rk = json.loads(run([BIN, "keygen-sign", "--out", P("home", "receipt.key")]).stdout)["public_key"]
dk = json.loads(run([BIN, "keygen-sign", "--out", P("dev", "device.key")]).stdout)["public_key"]
json.dump({"dev-a": dk}, open(P("home", "registry.json"), "w"))
pin = json.loads(run([BIN, "make-trust", "--recipients-file", P("home", "recipients.txt"), "--profile", "pq", "--receipt-pub", rk, "--out", P("dev", "trust.json")]).stdout)["pin"]
FAMILY = os.urandom(32).hex()
DEV = ["--state-dir", P("dev", "state"), "--keystore", P("dev", "keystore"), "--r2", P("r2"), "--trust", P("dev", "trust.json"), "--trust-pin", pin]
ENV = dict(os.environ, A2_SLOW_US=SLOW_US)

# files: (name, size, chunks_per_part) -> many parts each, prefix not chunk-aligned
FILES = [("a", 3 * 1024 * 1024 + 123, 2), ("b", 10 * 1024 * 1024 + 4097, 3), ("c", 700 * 1024 + 5, 1), ("d", 6 * 1024 * 1024, 4), ("e", 2 * 1024 * 1024 + 65536 - 1643, 1)]
for n, s, _ in FILES:
    with open(P("src", n), "wb") as f:
        f.write(os.urandom(s))

def attempts(object_key):
    return sorted(glob.glob(P("r2", object_key, "attempts", "*")))

def run_killable(cmd, kill_prob):
    """Runs cmd; with probability kill_prob SIGKILLs it at a random time.
    Returns (killed, returncode, stdout, stderr)."""
    t0 = time.time()
    pr = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=ENV)
    killed = False
    if rng.random() < kill_prob:
        # uniform over an estimate of the run time (10 parts' worth at SLOW_US)
        time.sleep(rng.uniform(0.0, 0.6))
        if pr.poll() is None:
            pr.send_signal(signal.SIGKILL)
            killed = True
    out, err = pr.communicate()
    return killed, pr.returncode, out.decode(), err.decode(), time.time() - t0

def plan_of(stderr):
    for line in stderr.splitlines():
        if line.startswith("PLAN "):
            return json.loads(line[5:])
    return None

kills_done = 0
per_kill_resent = []
uploads = []
def file_queue():
    for f in FILES:
        yield f
    i = 0
    while kills_done < KILLS:  # top up with extra files until the kill count is reached
        n, s, k = f"x{i}", 4 * 1024 * 1024 + 4099 * i, 2
        with open(P("src", n), "wb") as fh:
            fh.write(os.urandom(s))
        yield (n, s, k)
        i += 1

for (name, size, k) in file_queue():
    kill_budget = min(12, KILLS - kills_done)
    src = P("src", name)
    base = ["--device-key", P("dev", "device.key"), "--device-id", "dev-a"] + DEV
    # start (may itself be killed; if killed before the sealed state exists, start again)
    upload_id = None
    attempted_parts = set()
    kills_here = 0
    while upload_id is None:
        before = set(os.listdir(P("dev", "state")))
        killed, rc, out, err, _ = run_killable([BIN, "start", "--file", src, "--family-secret", FAMILY, "--chunks-per-part", str(k)] + base, 1.0 if kills_here < kill_budget else 0.0)
        for line in err.splitlines():
            if line.startswith("UPLOAD "):
                up = json.loads(line[7:])
                upload_id, object_key = up["upload_id"], up["object_key"]
        if killed:
            kills_here += 1
            kills_done += 1
            if upload_id is None or not os.path.exists(P("dev", "state", f"{upload_id}.state")):
                # killed before the sealed state was durable: nothing to resume; a fresh start uses a fresh key
                per_kill_resent.append({"file": name, "kill": kills_here, "phase": "start-before-state", "resent_parts": 0})
                if upload_id is not None:
                    run([BIN, "abort", "--upload-id", upload_id] + DEV)
                upload_id = None
                continue
        elif rc != 0:
            check(f"{name}:start", False, f"rc={rc} {err[-300:]}")
            break
    if upload_id is None:
        continue
    attempted_parts |= {int(os.path.basename(a).split(".")[0].split("-")[1]) for a in attempts(object_key)}
    done = (not killed) and rc == 0 and json.loads(out.strip().splitlines()[-1]).get("remaining_parts") == 0
    while not done:
        want_kill = kills_here < kill_budget
        killed, rc, out, err, _ = run_killable([BIN, "resume", "--upload-id", upload_id] + DEV, 1.0 if want_kill else 0.0)
        plan = plan_of(err)
        if plan is not None:
            # parts this run had to (re)generate that an earlier run had already started
            resent = [p for p in plan["todo"] if p in attempted_parts]
            per_kill_resent.append({"file": name, "kill": kills_here, "phase": "resume-after-kill", "resent_parts": len(resent), "parts": resent})
        attempted_parts |= {int(os.path.basename(a).split(".")[0].split("-")[1]) for a in attempts(object_key)}
        if killed:
            kills_here += 1
            kills_done += 1
            continue
        if rc != 0:
            check(f"{name}:resume", False, f"rc={rc} {err[-300:]}")
            break
        done = json.loads(out.strip().splitlines()[-1]).get("remaining_parts") == 0
    # complete -> ingest -> receipt
    c = run([BIN, "complete", "--upload-id", upload_id, "--device-key", P("dev", "device.key")] + DEV)
    check(f"{name}:complete", c.returncode == 0, c.stderr.decode()[-200:])
    cj = json.loads(c.stdout.decode().strip().splitlines()[-1])
    obj = cj["object"]
    uploads.append({"name": name, "upload_id": upload_id, "object_key": object_key, "object": obj, "kills": kills_here})
    # wire consistency: every attempt of every part is a prefix of the final part
    finals = {}
    consistent = True
    for a in attempts(object_key):
        part = os.path.basename(a).split(".")[0]
        fin = open(P("r2", object_key, part), "rb").read()
        b = open(a, "rb").read()
        if fin[: len(b)] != b:
            consistent = False
    check(f"{name}:wire-consistent (no offset ever sent with two values)", consistent, f"attempt files={len(attempts(object_key))}")
    # decrypt with Go age and the Rust decoder
    g = run([AGE, "-d", "-i", P("home", "identity.txt"), "-o", P("home", f"{name}.go.out"), obj])
    check(f"{name}:go-age-decrypts-exact-sha256", g.returncode == 0 and sha(P("home", f"{name}.go.out")) == sha(src), g.stderr.decode()[-200:])
    r = run([BIN, "decrypt", "--identity", P("home", "identity.txt"), "--in", obj])
    check(f"{name}:rust-decrypts-exact-sha256", r.returncode == 0 and json.loads(r.stdout)["sha256"] == sha(src))
    ins = json.loads(run([BIN, "inspect", "--in", obj]).stdout)
    check(f"{name}:prefix-len", ins["prefix_len"] == {1: 1643, 2: 3200}[STANZAS], ins["prefix_len"])
    # homelab ingest + receipt
    pend = json.load(open(json.loads(c.stdout.decode().strip().splitlines()[-1])["pending"]))
    ing = run([BIN, "ingest", "--identity", P("home", "identity.txt"), "--family-secret", FAMILY, "--registry", P("home", "registry.json"),
               "--receipt-key", P("home", "receipt.key"), "--store", P("home", "store"), "--meta", pend["meta_file"], "--object", obj,
               "--profile", "pq", "--stanzas", str(STANZAS), "--out", P("home", f"{name}.receipt")])
    check(f"{name}:ingest", ing.returncode == 0, ing.stderr.decode()[-300:])
    pf = glob.glob(P("dev", "state", "pending", "*.json"))
    pfile = [x for x in pf if json.load(open(x))["object_key"] == object_key][0]
    rc_ = run([BIN, "check-receipt", "--pending", pfile, "--receipt", P("home", f"{name}.receipt"), "--consume"] + DEV[-4:])
    check(f"{name}:receipt-valid", rc_.returncode == 0, rc_.stderr.decode()[-200:])
    # key residue scan (device side only: state dir, keystore, pending, everything under dev/)
    keys = json.loads(run([BIN, "debug-keys", "--identity", P("home", "identity.txt"), "--object", obj]).stdout)
    uploads[-1].update({"payload_nonce": keys["payload_nonce"], "header_mac": keys["header_mac"]})
    needles = []
    for k_ in ("file_key", "payload_key"):
        raw = bytes.fromhex(keys[k_])
        needles += [raw, keys[k_].encode(), base64.b64encode(raw), base64.b64encode(raw).rstrip(b"="), base64.urlsafe_b64encode(raw).rstrip(b"=")]
    hits = []
    for root, _, fs in os.walk(P("dev")):
        for fn in fs:
            data = open(os.path.join(root, fn), "rb").read()
            if any(nd in data for nd in needles):
                hits.append(os.path.join(root, fn))
    leftovers = [f for f in os.listdir(P("dev", "state")) if f.startswith(upload_id)] + [f for f in os.listdir(P("dev", "keystore")) if f.startswith(upload_id)]
    check(f"{name}:no-key-survives-commit", not hits and not leftovers, {"hits": hits, "leftover_files": leftovers})

# uniqueness across uploads (fresh randomness per upload; hedged)
nonces = [u["payload_nonce"] for u in uploads]
macs = [u["header_mac"] for u in uploads]
check("all-uploads:payload-nonces-unique", len(set(nonces)) == len(nonces), len(nonces))
check("all-uploads:header-macs-unique", len(set(macs)) == len(macs), len(macs))

# per-kill re-encryption bound
mx = max([r["resent_parts"] for r in per_kill_resent] or [0])
check("per-kill:at-most-one-segment-re-encrypted", mx <= 1, {"kills": kills_done, "max_resent_parts_per_kill": mx, "total_resent": sum(r["resent_parts"] for r in per_kill_resent)})
check("kills:count", kills_done >= KILLS, kills_done)

# edit-after-kill: edit a plaintext byte inside a chunk that was ALREADY transmitted
# in the interrupted (incomplete) part, so the resume must regenerate that chunk.
# The keystream guard must refuse (exit 65) rather than send different bytes under
# the same (key, nonce). Odd trials bypass the stat check (--no-stat-check) so the
# journal tag guard alone is tested; even trials keep the stat check.
CHUNK_CT, CHUNK_PT = 65552, 65536
guard = []
trial = 0
while len([g for g in guard if "resume_exit" in g]) < 6 and trial < 40:
    src = P("src", f"edit{trial}")
    with open(src, "wb") as f:
        f.write(os.urandom(2 * 1024 * 1024 + 17))
    base = ["--device-key", P("dev", "device.key"), "--device-id", "dev-a"] + DEV
    pr = subprocess.Popen([BIN, "start", "--file", src, "--family-secret", FAMILY, "--chunks-per-part", "4"] + base, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=ENV)
    time.sleep(rng.uniform(0.05, 0.3))
    pr.send_signal(signal.SIGKILL)
    out, err = pr.communicate()
    trial += 1
    up = [json.loads(l[7:]) for l in err.decode().splitlines() if l.startswith("UPLOAD ")]
    if not up or not os.path.exists(P("dev", "state", f"{up[0]['upload_id']}.state")):
        continue
    up = up[0]
    ps, pl = up["part_size"], up["prefix_len"]
    incomplete = []
    for at in attempts(up["object_key"]):
        part = os.path.basename(at).split(".")[0]
        fin = P("r2", up["object_key"], part)
        if not (os.path.exists(fin) and os.stat(fin).st_ino == os.stat(at).st_ino):
            incomplete.append((int(part.split("-")[1]) - 1, os.path.getsize(at)))
    # sent object range of the interrupted part, restricted to whole-chunk payload bytes
    cand = []
    for p_, L in incomplete:
        lo, hi = p_ * ps, p_ * ps + L
        for c in range(max(0, (lo - pl) // CHUNK_CT), (hi - pl) // CHUNK_CT + 1):
            cs = pl + c * CHUNK_CT
            if cs >= lo and cs + 1 <= hi and c * CHUNK_PT < up["pt_len"]:
                cand.append(c)
    if not cand:
        run([BIN, "abort", "--upload-id", up["upload_id"]] + DEV)
        continue
    c = rng.choice(cand)
    st = os.stat(src)
    off = c * CHUNK_PT + rng.randrange(0, min(CHUNK_PT, st.st_size - c * CHUNK_PT))
    with open(src, "r+b") as f:  # same size; then restore mtime (ctime still changes)
        f.seek(off)
        old = f.read(1)
        f.seek(off)
        f.write(bytes([old[0] ^ 0xFF]))
    os.utime(src, ns=(st.st_atime_ns, st.st_mtime_ns))
    bypass = len(guard) % 2 == 1
    r1 = run([BIN, "resume", "--upload-id", up["upload_id"]] + (["--no-stat-check"] if bypass else []) + DEV, env=ENV)
    ok_wire = all(open(P("r2", up["object_key"], os.path.basename(a_).split(".")[0]), "rb").read()[: os.path.getsize(a_)] == open(a_, "rb").read()
                  for a_ in attempts(up["object_key"]) if os.path.exists(P("r2", up["object_key"], os.path.basename(a_).split(".")[0])))
    guard.append({"trial": trial, "edited_chunk": c, "stat_check_bypassed": bypass, "resume_exit": r1.returncode,
                  "stderr": r1.stderr.decode().strip().splitlines()[-1][:160] if r1.stderr else "", "wire_consistent": ok_wire})
    run([BIN, "abort", "--upload-id", up["upload_id"]] + DEV)
real = [g for g in guard if "resume_exit" in g]
check("edit-after-kill:refused-with-exit-65", len(real) >= 4 and all(g["resume_exit"] == 65 for g in real), guard)
check("edit-after-kill:journal-guard-alone-refuses", any(g["stat_check_bypassed"] for g in real) and all(g["resume_exit"] == 65 for g in real if g["stat_check_bypassed"]))
check("edit-after-kill:wire-consistent", all(g.get("wire_consistent", True) for g in guard))

json.dump({"stanzas": STANZAS, "kills": kills_done, "slow_us": SLOW_US, "per_kill": per_kill_resent, "edit_trials": guard, "uploads": uploads, "results": results,
           "passed": sum(r["pass"] for r in results), "failed": sum(not r["pass"] for r in results)}, open(P("results.json"), "w"), indent=1)
print(json.dumps({"stanzas": STANZAS, "kills": kills_done, "passed": sum(r["pass"] for r in results), "failed": sum(not r["pass"] for r in results)}))
sys.exit(0 if all(r["pass"] for r in results) else 1)
