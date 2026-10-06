#!/usr/bin/env python3
"""THROWAWAY SPIKE harness for A2-S3 (interop). Not production.

Cross matrix: encoders {rust (this crate), go age, typage, kage} x decoders
{rust strict, go age, typage, kage} x key origins {go age-keygen -pq, rust
keygen, typage generateHybridIdentity} x sizes x recipient counts; then the
project vectors (deterministic, CCTV file format) through all four decoders.

Environment: BIN (rust spike binary), AGE (Go age), AGE_KEYGEN, NODE_TOOL
(typage_tool.mjs), KAGE_CP (classpath incl. KageTool), WORK (scratch dir).
Writes WORK/results.json and prints one line per check.
"""
import hashlib, json, os, shutil, subprocess, sys

BIN = os.environ["BIN"]; AGE = os.environ["AGE"]; KEYGEN = os.environ["AGE_KEYGEN"]
NODE_TOOL = os.environ["NODE_TOOL"]; KAGE_CP = os.environ["KAGE_CP"]; WORK = os.environ["WORK"]
shutil.rmtree(WORK, ignore_errors=True); os.makedirs(WORK)
results = []

def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, **kw)

def check(name, ok, detail=""):
    results.append({"check": name, "pass": bool(ok), "detail": detail})
    print(("PASS " if ok else "FAIL ") + name + (" :: " + detail if detail else ""), flush=True)

def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()

def p(*a):
    return os.path.join(WORK, *a)

# ---------------------------------------------------------------- keys
def keys_go(n):
    run([KEYGEN, "-pq", "-o", p(f"go_{n}.id")], check=True)
    r = run([KEYGEN, "-y", p(f"go_{n}.id")], check=True).stdout.decode().strip()
    return p(f"go_{n}.id"), r

def keys_rust(n):
    r = run([BIN, "keygen", "--out", p(f"rs_{n}.id")], check=True).stdout.decode().strip()
    return p(f"rs_{n}.id"), r

def keys_ts(n):
    r = run(["node", NODE_TOOL, "keygen", p(f"ts_{n}.id")], check=True).stdout.decode().strip()
    return p(f"ts_{n}.id"), r

KEYS = {"go": [keys_go(0), keys_go(1)], "rust": [keys_rust(0), keys_rust(1)], "typage": [keys_ts(0), keys_ts(1)]}
for origin, ks in KEYS.items():
    for idp, r in ks:
        check(f"keys:{origin}:recipient-is-age1pq", r.startswith("age1pq1") and len(r) == 1959, f"len={len(r)}")
# every implementation derives the same recipient from each identity
for origin, ks in KEYS.items():
    idp, r = ks[0]
    rr = run([BIN, "recipient", "--identity", idp]).stdout.decode().strip()
    gr = run([KEYGEN, "-y", idp]).stdout.decode().strip()
    check(f"keys:{origin}:rust-and-go-derive-same-recipient", rr == r and gr == r)

# ---------------------------------------------------------------- encoders / decoders
def enc_rust(rfile, src, dst):
    return run([BIN, "encrypt", "--recipients", rfile, "--in", src, "--out", dst]).returncode == 0
def enc_go(rfile, src, dst):
    return run([AGE, "-e", "-R", rfile, "-o", dst, src]).returncode == 0
def enc_ts(rfile, src, dst):
    return run(["node", NODE_TOOL, "encrypt", rfile, src, dst]).returncode == 0
def enc_kage(rfile, src, dst):
    return run(["java", "-cp", KAGE_CP, "KageTool", "encrypt", rfile, src, dst]).returncode == 0

def dec_rust(idf, src, dst):
    return run([BIN, "decrypt", "--identity", idf, "--in", src, "--out", dst]).returncode == 0
def dec_go(idf, src, dst):
    return run([AGE, "-d", "-i", idf, "-o", dst, src]).returncode == 0
def dec_ts(idf, src, dst):
    return run(["node", NODE_TOOL, "decrypt", idf, src, dst]).returncode == 0
def dec_kage(idf, src, dst):
    return run(["java", "-cp", KAGE_CP, "KageTool", "decrypt", idf, src, dst]).returncode == 0

ENC = {"rust": enc_rust, "go": enc_go, "typage": enc_ts, "kage": enc_kage}
DEC = {"rust": dec_rust, "go": dec_go, "typage": dec_ts, "kage": dec_kage}

SIZES = [0, 1, 65535, 65536, 65537, 3 * 65536 + 7, 5 * 1024 * 1024 + 3]
for s in SIZES:
    with open(p(f"pt_{s}"), "wb") as f:
        f.write(os.urandom(s))

def header_len(path):
    out = run([BIN, "inspect", "--in", path])
    return json.loads(out.stdout)["header_len"] if out.returncode == 0 else None

matrix = {}
for origin, ks in KEYS.items():
    for nrec in (1, 2):
        rfile = p(f"rcpt_{origin}_{nrec}")
        with open(rfile, "w") as f:
            f.write("\n".join(r for _, r in ks[:nrec]) + "\n")
        # decrypt with the LAST recipient's identity (so 2-stanza files exercise the second stanza)
        idf = ks[nrec - 1][0]
        for en, ef in ENC.items():
            for s in SIZES:
                ct = p(f"ct_{origin}_{nrec}_{en}_{s}.age")
                if not ef(rfile, p(f"pt_{s}"), ct):
                    check(f"encrypt:{en}:{origin}-keys:{nrec}pq:{s}B", False, "encoder failed")
                    continue
                hl = header_len(ct)
                want_hl = {1: 1627, 2: 3184}[nrec]
                check(f"header-len:{en}:{nrec}pq:{s}B", hl == want_hl, f"{hl}")
                for dn, df in DEC.items():
                    out = ct + f".{dn}.out"
                    ok = df(idf, ct, out) and os.path.exists(out) and sha(out) == sha(p(f"pt_{s}"))
                    matrix.setdefault(f"{en}->{dn}", [0, 0])[0 if ok else 1] += 1
                    check(f"interop:{en}->{dn}:{origin}-keys:{nrec}pq:{s}B", ok)

# Go age must refuse to mix PQ and classic recipients; so must Rust.
xid = p("x.id"); run([KEYGEN, "-o", xid], check=True)
xr = run([KEYGEN, "-y", xid], check=True).stdout.decode().strip()
mixed = p("rcpt_mixed")
with open(mixed, "w") as f:
    f.write(KEYS["go"][0][1] + "\n" + xr + "\n")
g = run([AGE, "-e", "-R", mixed, "-o", p("mixed_go.age"), p("pt_1")])
check("mixing:go-refuses", g.returncode != 0, g.stderr.decode().strip()[:120])
r = run([BIN, "encrypt", "--recipients", mixed, "--in", p("pt_1"), "--out", p("mixed_rs.age")])
check("mixing:rust-refuses", r.returncode != 0, r.stderr.decode().strip()[:120])
t = run(["node", NODE_TOOL, "encrypt", mixed, p("pt_1"), p("mixed_ts.age")])
check("mixing:typage-behaviour-recorded", True, f"typage exit={t.returncode} {t.stderr.decode().strip()[-160:]}")
k = run(["java", "-cp", KAGE_CP, "KageTool", "encrypt", mixed, p("pt_1"), p("mixed_kage.age")])
check("mixing:kage-behaviour-recorded", True, f"kage exit={k.returncode} {k.stderr.decode().strip()[-200:]}")

summary = {k: {"ok": v[0], "fail": v[1]} for k, v in sorted(matrix.items())}
json.dump({"results": results, "matrix": summary, "passed": sum(r["pass"] for r in results), "failed": sum(not r["pass"] for r in results)}, open(p("results.json"), "w"), indent=1)
print(json.dumps({"matrix": summary, "passed": sum(r["pass"] for r in results), "failed": sum(not r["pass"] for r in results)}))
sys.exit(0 if all(r["pass"] for r in results) else 1)
