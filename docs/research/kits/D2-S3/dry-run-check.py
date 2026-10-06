#!/usr/bin/env python3
"""D2-S3 kit self-check (run by an agent or the owner BEFORE the drill; it is not the drill).

Builds a drill disk from 10 synthetic "photos" with make-drill-disk.sh, then follows the tester
runbook's commands mechanically with stock tools (shamir recover, age -d with its interactive
passphrase prompt driven through a pty, age-keygen -y, age -d per photo) and checks the result.
It proves the kit's commands work; it says nothing about whether a relative can follow them.

Class: SYN -> results. Needs on PATH: age, age-keygen, age-plugin-batchpass (age >= 1.3.0), shamir.
Usage: dry-run-check.py [--pq] [--bits 128|256]
"""
import hashlib, os, pty, re, secrets, shutil, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
PQ = "--pq" in sys.argv
BITS = sys.argv[sys.argv.index("--bits") + 1] if "--bits" in sys.argv else "128"
results = []


def check(name, ok, detail=""):
    results.append(ok)
    print(("PASS " if ok else "FAIL ") + name + (f" -- {detail}" if detail else ""), flush=True)


def age_prompt(args, answer):
    pid, fd = pty.fork()
    if pid == 0:
        os.execvp("age", ["age"] + args)
    buf, sent, t0 = b"", False, time.time()
    while time.time() - t0 < 120:
        try:
            c = os.read(fd, 1024)
        except OSError:
            break
        if not c:
            break
        buf += c
        if not sent and b"passphrase" in buf.lower():
            os.write(fd, answer.encode() + b"\n")
            sent = True
    return os.waitstatus_to_exitcode(os.waitpid(pid, 0)[1]), buf.decode(errors="replace")


def main():
    work = tempfile.mkdtemp(prefix="d2s3-dry-")
    try:
        photos = os.path.join(work, "photos")
        os.makedirs(photos)
        for i in range(10):
            with open(os.path.join(photos, f"drill-photo-{i+1:02d}.jpg"), "wb") as f:
                f.write(b"\xff\xd8\xff\xe0SYNTHETIC" + secrets.token_bytes(100_000 * (i + 1)))
        disk = os.path.join(work, "DRILL-DISK")
        cmd = [os.path.join(HERE, "make-drill-disk.sh"), photos, disk, "--bits", BITS] + (["--pq"] if PQ else [])
        p = subprocess.run(cmd, capture_output=True, text=True)
        check("make-drill-disk.sh ran", p.returncode == 0, p.stderr[-300:])
        shares = [l.split(": ", 1)[1] for l in p.stdout.splitlines() if re.match(r"^[123]: ", l)]
        check("3 share texts printed", len(shares) == 3, f"words per share: {sorted({len(s.split()) for s in shares})}")
        check("no share text written to the disk", not any(" ".join(s.split()[3:7]) in open(f, errors="ignore").read()
              for s in shares for root, _, fs in os.walk(disk) for f in [os.path.join(root, x) for x in fs] ))
        # --- tester steps (runbook numbering) ---
        t0 = time.time()
        r = subprocess.run(["shamir", "recover"], input=shares[2] + "\n" + shares[0] + "\n", capture_output=True, text=True)
        m = re.search(r"master secret is: ([0-9a-f]+)", r.stdout)
        check("step 3: shamir recover with cards 3 and 1", bool(m))
        ident = os.path.join(work, "identity.txt")
        rc, out = age_prompt(["-d", "-o", ident, os.path.join(disk, "recovery", "recovery-identity.age")], m.group(1))
        check("step 4: age -d unseals the recovery identity at its passphrase prompt", rc == 0, out.strip().splitlines()[0] if out.strip() else "")
        rr = subprocess.run(["age-keygen", "-y", ident], capture_output=True, text=True).stdout.strip()
        want = open(os.path.join(disk, "recovery", "KEY-CHECK.txt")).read().split()
        check("step 5: public key matches the card check line", rr.startswith(want[0]) and rr.endswith(want[2]))
        cat = subprocess.run(["age", "-d", "-i", ident, os.path.join(disk, "store", "catalog.tsv.age")], capture_output=True, text=True)
        rows = [l.split("\t") for l in cat.stdout.splitlines()[1:]]
        named = {r[0]: r for r in rows if r[0].startswith("drill-photo-")}
        check("step 6: catalog decrypts and lists the 10 named photos among decoys", len(named) == 10, f"{len(rows)} rows")
        good = 0
        outdir = os.path.join(work, "recovered")
        os.makedirs(outdir)
        for name, row in named.items():
            dst = os.path.join(outdir, name)
            subprocess.run(["age", "-d", "-i", ident, "-o", dst, os.path.join(disk, "store", "objects", row[1] + ".age")], check=True)
            if hashlib.sha256(open(dst, "rb").read()).hexdigest() == row[3] == hashlib.sha256(open(os.path.join(photos, name), "rb").read()).hexdigest():
                good += 1
        check("step 7: all 10 photos recovered byte-identical", good == 10, f"{good}/10; mechanical run took {time.time()-t0:.1f} s")
        bad = subprocess.run(["shamir", "recover"], input=shares[1] + "\n", capture_output=True, text=True)
        check("negative: one card alone does not recover", "master secret is" not in bad.stdout)
        rc, out = age_prompt(["-d", "-o", ident + ".bad", os.path.join(disk, "recovery", "recovery-identity.age")], "0" * len(m.group(1)))
        check("negative: a wrong secret is refused by age", rc != 0, out.strip().splitlines()[-1] if out.strip() else "")
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print(f"{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
