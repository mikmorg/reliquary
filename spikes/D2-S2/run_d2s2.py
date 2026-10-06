#!/usr/bin/env python3
"""D2-S2 throwaway spike driver (Reliquary research, Wave 1).

Recovery recipient: encrypt synthetic "photos" to an ingest key plus a 2-of-3 split
recovery recipient, destroy the ingest key, recover with stock tools; then measure the
cost of adding a recipient later (header rewrap) against full re-encryption.

Data-handling class: SYN -> results. All keys are throwaway test keys (SEC, sandbox-only),
created and destroyed inside WORK; no secret is written to the evidence files (runs before
2026-10-06 kept the pty-echoed test passphrase in results.json; the repo copies are redacted).

Environment variables:
  WORK      work dir (wiped at start), default ./work
  BIN       dir with age v1.3.1 CLIs, age-plugin-sss, rewrap; default ./bin
  VENV      venv with shamir-mnemonic[cli]==0.3.0; default ./venv
  EVIDENCE  output dir for results; default ./evidence
  QUICK=1   small rewrap/throughput sizes (smoke test only)
"""
import hashlib, json, os, pty, re, secrets, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.environ.get("WORK", os.path.join(HERE, "work"))
BIN = os.environ.get("BIN", os.path.join(HERE, "bin"))
VENV = os.environ.get("VENV", os.path.join(HERE, "venv"))
EVID = os.environ.get("EVIDENCE", os.path.join(HERE, "evidence"))
QUICK = os.environ.get("QUICK") == "1"
SHM = os.environ.get("SHM", "/dev/shm/d2s2")
AGE = os.path.join(BIN, "age")
KEYGEN = os.path.join(BIN, "age-keygen")
INSPECT = os.path.join(BIN, "age-inspect")
SSS = os.path.join(BIN, "age-plugin-sss")
REWRAP = os.path.join(BIN, "rewrap")
SHAMIR = os.path.join(VENV, "bin", "shamir")
DEBIAN_AGE = "/usr/bin/age"  # stock distro age 1.1.1, no PQ

ENV = dict(os.environ, PATH=BIN + ":" + os.environ["PATH"])
checks = []
results = {"started": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "variants": {}, "rewrap": {}, "throughput": {}}
log_lines = []


def log(msg):
    print(msg, flush=True)
    log_lines.append(msg)


def check(name, ok, detail=""):
    checks.append({"check": name, "pass": bool(ok), "detail": detail})
    log(("PASS " if ok else "FAIL ") + name + (" -- " + detail if detail else ""))


def run(cmd, input=None, env=None, ok_codes=(0,), capture=True):
    p = subprocess.run(cmd, input=input, env=env or ENV, capture_output=capture)
    if p.returncode not in ok_codes:
        raise RuntimeError(f"{cmd[0]} rc={p.returncode}: {p.stderr.decode(errors='replace')[:500]}")
    return p


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def loadavg():
    return open("/proc/loadavg").read().strip()


def destroy(path):
    """Overwrite then unlink (best effort on a journalled/CoW fs; the point here is only that the key is gone)."""
    n = os.path.getsize(path)
    with open(path, "r+b") as f:
        f.write(secrets.token_bytes(n))
        f.flush()
        os.fsync(f.fileno())
    os.unlink(path)
    return not os.path.exists(path)


def recipient_of(keyfile):
    return run([KEYGEN, "-y", keyfile]).stdout.decode().strip()


def fp(recipient):
    """Short fingerprint to print on cards: first 16 hex of SHA-256 of the recipient string."""
    return hashlib.sha256(recipient.encode()).hexdigest()[:16]


# ---------- bech32 (BIP-173), used only by variant C to show the non-stock step ----------
CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"


def _polymod(values):
    gen = [0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3]
    chk = 1
    for v in values:
        b = chk >> 25
        chk = (chk & 0x1FFFFFF) << 5 ^ v
        for i in range(5):
            chk ^= gen[i] if ((b >> i) & 1) else 0
    return chk


def _hrp_expand(hrp):
    return [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]


def _convertbits(data, frombits, tobits, pad=True):
    acc = bits = 0
    ret = []
    maxv = (1 << tobits) - 1
    for v in data:
        acc = (acc << frombits) | v
        bits += frombits
        while bits >= tobits:
            bits -= tobits
            ret.append((acc >> bits) & maxv)
    if pad and bits:
        ret.append((acc << (tobits - bits)) & maxv)
    elif not pad and (bits >= frombits or ((acc << (tobits - bits)) & maxv)):
        raise ValueError("bad padding")
    return ret


def bech32_encode(hrp, data8):
    hrp = hrp.lower()
    d5 = _convertbits(data8, 8, 5)
    pm = _polymod(_hrp_expand(hrp) + d5 + [0] * 6) ^ 1
    chk = [(pm >> 5 * (5 - i)) & 31 for i in range(6)]
    return (hrp + "1" + "".join(CHARSET[d] for d in d5 + chk)).upper()


def bech32_decode(s):
    s = s.lower()
    pos = s.rfind("1")
    hrp, data = s[:pos], [CHARSET.find(c) for c in s[pos + 1:]]
    if _polymod(_hrp_expand(hrp) + data) != 1:
        raise ValueError("checksum")
    return hrp, bytes(_convertbits(data[:-6], 5, 8, pad=False))


def identity_line(keyfile):
    for line in open(keyfile):
        if line.startswith("AGE-SECRET-KEY-"):
            return line.strip()
    raise ValueError("no identity")


# ---------- SLIP-39 via the reference CLI ----------
def slip39_split(secret_hex):
    out = run([SHAMIR, "create", "2of3", "-S", secret_hex]).stdout.decode().splitlines()
    shares = [l.strip() for l in out if len(l.split()) >= 20 and not l.startswith(("Using", "Group"))]
    return shares


def slip39_recover(shares):
    p = run([SHAMIR, "recover"], input=("\n".join(shares) + "\n").encode(), ok_codes=(0, 1))
    m = re.search(r"master secret is: ([0-9a-f]+)", p.stdout.decode())
    return (m.group(1) if m else None), p.stdout.decode()[-300:]


def age_pty_decrypt_identity(sealed, out, passphrase):
    """Drive the stock interactive `age -d` passphrase prompt through a pty, as a person would type it."""
    pid, fd = pty.fork()
    if pid == 0:
        os.execve(AGE, [AGE, "-d", "-o", out, sealed], ENV)
    buf = b""
    t0 = time.time()
    sent = False
    while time.time() - t0 < 60:
        try:
            chunk = os.read(fd, 1024)
        except OSError:
            break
        if not chunk:
            break
        buf += chunk
        if not sent and b"passphrase" in buf.lower():
            os.write(fd, passphrase.encode() + b"\n")
            sent = True
    _, status = os.waitpid(pid, 0)
    return os.waitstatus_to_exitcode(status), buf.decode(errors="replace")


# ---------- synthetic photos ----------
def make_photos(d, n=10):
    os.makedirs(d)
    rng_sizes = [180_000, 420_000, 950_000, 1_600_000, 2_300_000, 3_100_000, 3_900_000, 4_700_000, 250_000, 5_200_000]
    hashes = {}
    for i in range(n):
        name = f"photo-{i+1:02d}.jpg"
        path = os.path.join(d, name)
        with open(path, "wb") as f:
            f.write(b"\xff\xd8\xff\xe0SYNTHETIC-NOT-A-PHOTO" + secrets.token_bytes(rng_sizes[i % len(rng_sizes)]))
        hashes[name] = sha(path)
    return hashes


def header_len(path):
    data = open(path, "rb").read(1 << 16)
    i = data.find(b"\n--- ")
    j = data.find(b"\n", i + 1)
    return j + 1


def encrypt_photos(photos, outdir, recipients):
    os.makedirs(outdir)
    args = []
    for r in recipients:
        args += ["-r", r]
    hl = []
    for name in sorted(os.listdir(photos)):
        dst = os.path.join(outdir, name + ".age")
        run([AGE] + args + ["-o", dst, os.path.join(photos, name)])
        hl.append(header_len(dst))
    return hl


def decrypt_all(objdir, identity_file, outdir, hashes, age_bin=AGE):
    os.makedirs(outdir, exist_ok=True)
    ok = 0
    errs = []
    t0 = time.time()
    for name in sorted(hashes):
        dst = os.path.join(outdir, name)
        p = subprocess.run([age_bin, "-d", "-i", identity_file, "-o", dst, os.path.join(objdir, name + ".age")], env=ENV, capture_output=True)
        if p.returncode == 0 and sha(dst) == hashes[name]:
            ok += 1
        else:
            errs.append(p.stderr.decode(errors="replace").strip()[:200])
    return ok, errs, time.time() - t0


def inspect(path):
    p = subprocess.run([INSPECT, "--json", path], env=ENV, capture_output=True)
    try:
        return json.loads(p.stdout)
    except Exception:
        return {"raw": p.stdout.decode(errors="replace")[:500], "stderr": p.stderr.decode(errors="replace")[:300]}


# ---------- variants ----------
def variant_sealed(tag, pq, bits, photos, hashes):
    """Ingest key + recovery identity; recovery identity sealed (age scrypt) under a random secret;
    that secret split 2-of-3 with SLIP-39. Stock tools only on the recovery path."""
    v = {"kind": "pq" if pq else "classic", "slip39_secret_bits": bits}
    d = os.path.join(WORK, tag)
    os.makedirs(d)
    kg = [KEYGEN] + (["-pq"] if pq else [])
    # --- ceremony (simulated) ---
    ingest_key, rec_key = os.path.join(d, "ingest.key"), os.path.join(d, "recovery.key")
    run(kg + ["-o", ingest_key])
    run(kg + ["-o", rec_key])
    ingest_r, rec_r = recipient_of(ingest_key), recipient_of(rec_key)
    v["recipient_lengths"] = {"ingest": len(ingest_r), "recovery": len(rec_r)}
    v["recovery_fingerprint_printed_on_card"] = fp(rec_r)
    secret_hex = secrets.token_hex(bits // 8)
    shares = slip39_split(secret_hex)
    v["share_count"] = len(shares)
    v["words_per_share"] = sorted({len(s.split()) for s in shares})
    sealed = os.path.join(d, "recovery-identity.age")
    t0 = time.time()
    run([AGE, "-e", "-j", "batchpass", "-o", sealed, rec_key], env=dict(ENV, AGE_PASSPHRASE=secret_hex))
    v["seal_seconds"] = round(time.time() - t0, 3)
    v["sealed_identity_bytes"] = os.path.getsize(sealed)
    v["sealed_identity_inspect"] = inspect(sealed)
    check(f"{tag}: sealed identity is a single native scrypt stanza",
          open(sealed, "rb").read().split(b"\n")[1].startswith(b"-> scrypt "))
    check(f"{tag}: recovery.key destroyed after sealing", destroy(rec_key))
    del secret_hex
    # --- normal operation: every object carries both stanzas ---
    hl = encrypt_photos(photos, os.path.join(d, "objects"), [ingest_r, rec_r])
    v["header_bytes_per_object"] = sorted(set(hl))
    v["object_inspect_sample"] = inspect(os.path.join(d, "objects", "photo-01.jpg.age"))
    # ingest key still works
    ok, errs, _ = decrypt_all(os.path.join(d, "objects"), ingest_key, os.path.join(d, "ingest-out"), hashes)
    check(f"{tag}: ingest identity decrypts all 10 objects before destruction", ok == 10, "; ".join(errs[:2]))
    # --- disaster: ingest key destroyed ---
    check(f"{tag}: ingest key destroyed", destroy(ingest_key))
    # --- recovery with 2 of 3 shares, stock tools ---
    neg_secret, neg_out = slip39_recover([shares[1]])
    check(f"{tag}: one share alone does not recover", neg_secret is None, neg_out.strip().splitlines()[-1] if neg_out.strip() else "")
    t0 = time.time()
    got_hex, _ = slip39_recover([shares[0], shares[2]])
    v["slip39_recover_seconds"] = round(time.time() - t0, 3)
    check(f"{tag}: SLIP-39 2-of-3 (shares 1+3) reconstructs the secret", got_hex is not None and len(got_hex) == bits // 4)
    rec_out = os.path.join(d, "recovered.key")
    # wrong passphrase must fail loudly (SLIP-39 itself would not tell us)
    p = subprocess.run([AGE, "-d", "-j", "batchpass", "-o", rec_out + ".bad", sealed], env=dict(ENV, AGE_PASSPHRASE="0" * len(got_hex)), capture_output=True)
    check(f"{tag}: wrong secret is rejected by age (scrypt stanza MAC)", p.returncode != 0, p.stderr.decode(errors="replace").strip()[:120])
    t0 = time.time()
    rc, transcript = age_pty_decrypt_identity(sealed, rec_out, got_hex)
    v["unseal_interactive_seconds"] = round(time.time() - t0, 3)
    # The pty can echo the typed secret if it is written before age turns echo off; never keep it.
    v["unseal_prompt_seen"] = [l.replace(got_hex, "[REDACTED]") for l in transcript.splitlines() if "passphrase" in l.lower()][:2]
    v["unseal_secret_echoed_in_pty_transcript"] = got_hex in transcript
    check(f"{tag}: stock `age -d` unseals the recovery identity via its interactive passphrase prompt (pty)", rc == 0 and os.path.exists(rec_out), f"rc={rc}")
    rr = recipient_of(rec_out)
    check(f"{tag}: recovered identity matches the fingerprint printed on the card", fp(rr) == v["recovery_fingerprint_printed_on_card"])
    ok, errs, secs = decrypt_all(os.path.join(d, "objects"), rec_out, os.path.join(d, "recovered-photos"), hashes)
    v["decrypt_10_seconds"] = round(secs, 3)
    check(f"{tag}: recovery identity alone decrypts all 10 photos, SHA-256 identical", ok == 10, "; ".join(errs[:2]))
    # the stock distro age (1.1.1) path
    ok2, errs2, _ = decrypt_all(os.path.join(d, "objects"), rec_out, os.path.join(d, "recovered-debian-age"), hashes, age_bin=DEBIAN_AGE)
    v["debian_age_1_1_1_decrypts"] = ok2
    v["debian_age_1_1_1_error_sample"] = errs2[:1]
    if pq:
        check(f"{tag}: (expected) distro age 1.1.1 cannot decrypt PQ objects", ok2 == 0, errs2[0] if errs2 else "")
    else:
        check(f"{tag}: distro age 1.1.1 also decrypts classic objects", ok2 == 10)
    # direct use of the sealed identity file as -i (the CLI prompts for the passphrase each run)
    results["variants"][tag] = v
    return rec_out, os.path.join(d, "objects")


def variant_raw_slip39(tag, pq, photos, hashes):
    """SLIP-39 of the raw 32-byte identity. Needs one non-stock step (bech32 encode)."""
    v = {"kind": "pq" if pq else "classic"}
    d = os.path.join(WORK, tag)
    os.makedirs(d)
    kg = [KEYGEN] + (["-pq"] if pq else [])
    ingest_key, rec_key = os.path.join(d, "ingest.key"), os.path.join(d, "recovery.key")
    run(kg + ["-o", ingest_key])
    run(kg + ["-o", rec_key])
    ingest_r, rec_r = recipient_of(ingest_key), recipient_of(rec_key)
    hrp, raw = bech32_decode(identity_line(rec_key))
    v["identity_hrp"] = hrp.upper()
    v["identity_secret_bytes"] = len(raw)
    shares = slip39_split(raw.hex())
    v["words_per_share"] = sorted({len(s.split()) for s in shares})
    destroy(rec_key)
    encrypt_photos(photos, os.path.join(d, "objects"), [ingest_r, rec_r])
    destroy(ingest_key)
    got_hex, _ = slip39_recover([shares[1], shares[2]])
    ident = bech32_encode(hrp, bytes.fromhex(got_hex))
    rec_out = os.path.join(d, "recovered.key")
    with open(rec_out, "w") as f:
        f.write(ident + "\n")
    check(f"{tag}: re-encoded identity parses and matches the recovery recipient", recipient_of(rec_out) == rec_r)
    ok, errs, _ = decrypt_all(os.path.join(d, "objects"), rec_out, os.path.join(d, "out"), hashes)
    check(f"{tag}: raw-identity SLIP-39 recovery decrypts all 10 photos (non-stock bech32 step needed)", ok == 10, "; ".join(errs[:2]))
    v["non_stock_step"] = "bech32-encode the recovered 32 bytes with HRP " + hrp.upper() + " (about 40 lines of Python; not in any stock tool checked)"
    results["variants"][tag] = v


def variant_sss(tag, pq, photos, hashes):
    """age-plugin-sss v0.4.0: file key split 2-of-3 per object to three holder recipients."""
    v = {"kind": "pq" if pq else "classic", "plugin": "age-plugin-sss v0.4.0 (experimental per its README)"}
    d = os.path.join(WORK, tag)
    os.makedirs(d)
    kg = [KEYGEN] + (["-pq"] if pq else [])
    ingest_key = os.path.join(d, "ingest.key")
    run(kg + ["-o", ingest_key])
    ingest_r = recipient_of(ingest_key)
    holders = []
    for i in range(3):
        k = os.path.join(d, f"holder{i+1}.key")
        run(kg + ["-o", k])
        holders.append(k)
    pol = os.path.join(d, "policy.yaml")
    with open(pol, "w") as f:
        f.write("threshold: 2\nshares:\n" + "".join(f"  - {recipient_of(h)}\n" for h in holders))
    sss_r = run([SSS, "--generate-recipient", pol]).stdout.decode().strip()
    v["sss_recipient_length"] = len(sss_r)
    try:
        hl = encrypt_photos(photos, os.path.join(d, "objects"), [ingest_r, sss_r])
    except RuntimeError as e:
        check(f"{tag}: encrypt to ingest + sss recipient", False, str(e)[:200])
        results["variants"][tag] = v
        return
    v["header_bytes_per_object"] = sorted(set(hl))
    v["object_inspect_sample"] = inspect(os.path.join(d, "objects", "photo-01.jpg.age"))
    p = subprocess.run([SSS, "--inspect", os.path.join(d, "objects", "photo-01.jpg.age")], env=ENV, capture_output=True)
    v["sss_inspect"] = p.stdout.decode(errors="replace")[:400]
    destroy(ingest_key)
    idy = os.path.join(d, "ids.yaml")
    with open(idy, "w") as f:
        f.write("identities:\n" + "".join(f"  - {identity_line(h)}\n" for h in (holders[0], holders[2])))
    ident = os.path.join(d, "sss-identity.txt")
    with open(ident, "w") as f:
        f.write(run([SSS, "--generate-identity", idy]).stdout.decode())
    ok, errs, secs = decrypt_all(os.path.join(d, "objects"), ident, os.path.join(d, "out"), hashes)
    v["decrypt_10_seconds"] = round(secs, 3)
    check(f"{tag}: holders 1+3 decrypt all 10 photos via age-plugin-sss after ingest key destroyed", ok == 10, "; ".join(errs[:2]))
    idy1 = os.path.join(d, "ids1.yaml")
    with open(idy1, "w") as f:
        f.write("identities:\n" + f"  - {identity_line(holders[1])}\n")
    ident1 = os.path.join(d, "sss-identity1.txt")
    with open(ident1, "w") as f:
        f.write(run([SSS, "--generate-identity", idy1]).stdout.decode())
    ok1, errs1, _ = decrypt_all(os.path.join(d, "objects"), ident1, os.path.join(d, "out1"), {"photo-01.jpg": hashes["photo-01.jpg"]})
    check(f"{tag}: one holder alone cannot decrypt", ok1 == 0, errs1[0][:150] if errs1 else "")
    results["variants"][tag] = v


def mixing_rules():
    d = os.path.join(WORK, "mixing")
    os.makedirs(d)
    run([KEYGEN, "-o", os.path.join(d, "c.key")])
    run([KEYGEN, "-pq", "-o", os.path.join(d, "q.key")])
    c, q = recipient_of(os.path.join(d, "c.key")), recipient_of(os.path.join(d, "q.key"))
    src = os.path.join(d, "x.txt")
    open(src, "w").write("x")
    p = subprocess.run([AGE, "-r", c, "-r", q, "-o", os.path.join(d, "mix.age"), src], env=ENV, capture_output=True)
    msg = p.stderr.decode(errors="replace").strip()
    results["mixing_pq_classic"] = {"rc": p.returncode, "stderr": msg[:300]}
    check("mixing: age v1.3.1 refuses X25519 + ML-KEM hybrid recipients in one file", p.returncode != 0, msg[:160])
    p = subprocess.run([AGE, "-p", "-r", c, "-o", os.path.join(d, "mix2.age"), src], env=ENV, capture_output=True, stdin=subprocess.DEVNULL)
    msg = p.stderr.decode(errors="replace").strip()
    results["mixing_passphrase_plus_recipient"] = {"rc": p.returncode, "stderr": msg[:300]}
    check("mixing: age refuses a passphrase (-p) together with a recipient", p.returncode != 0, msg[:160])


# ---------- rewrap cost ----------
def rewrap_costs():
    # (1) the PLAN's 1M count, once per kind with 4 workers; (2) 3 repetitions of 100k at 1 and 4
    # workers, because the shared container is heavily loaded and single runs are noisy.
    plan = []
    big, small = (20000, 5000) if QUICK else (1_000_000, 100_000)
    for kind in ("classic", "pq"):
        plan.append((f"inmem_{kind}_w4_1M", kind, 4, big))
        for workers in (1, 4):
            for rep in range(3):
                plan.append((f"inmem_{kind}_w{workers}_100k_rep{rep+1}", kind, workers, small))
    for key, kind, workers, n in plan:
        p = run([REWRAP, "bench", "-kind", kind, "-n", str(n), "-pool", "1024", "-workers", str(workers), "-unwrap-n", str(max(n // 10, 1000))])
        r = json.loads(p.stdout)
        results["rewrap"][key] = r
        log(f"rewrap {key}: {r['n_rewraps']} in {r['elapsed_s']:.1f}s = {r['rewraps_per_s']:.0f}/s; unwrap-only {r['unwrap_only_per_s']:.0f}/s; header {r['header_bytes_before']}->{r['header_bytes_after']} B; load {r['loadavg_before']} -> {r['loadavg_after']}")
        check(f"rewrap {key}: every pool object verified after rewrap", r["verified_roundtrips"] == 1024)
    # on-disk rewrap: whole-object rewrite vs header-only sidecar, 1 MiB objects
    nfiles, size = (50, 1 << 20) if QUICK else (500, 1 << 20)
    d = os.path.join(SHM, "rewrap-files")
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(os.path.join(d, "in"))
    run([KEYGEN, "-o", os.path.join(d, "ingest.key")])
    run([KEYGEN, "-o", os.path.join(d, "recovery.key")])
    ir, rr = recipient_of(os.path.join(d, "ingest.key")), recipient_of(os.path.join(d, "recovery.key"))
    pt = os.path.join(d, "pt.bin")
    for i in range(nfiles):
        with open(pt, "wb") as f:
            f.write(secrets.token_bytes(size))
        run([AGE, "-r", ir, "-o", os.path.join(d, "in", f"o{i:05d}.age"), pt])
    for mode, extra in (("whole_object_rewrite", []), ("header_sidecar_only", ["-header-only"])):
        out = os.path.join(d, "out-" + mode)
        p = run([REWRAP, "file", "-in", os.path.join(d, "in"), "-out", out, "-ingest", os.path.join(d, "ingest.key"), "-recipient", rr] + extra)
        r = json.loads(p.stdout)
        r["object_plaintext_bytes"] = size
        r["storage"] = "tmpfs (/dev/shm): excludes disk I/O; homelab disks not measured"
        results["rewrap"]["files_" + mode] = r
        log(f"file rewrap {mode}: {r['files']} x 1 MiB in {r['elapsed_s']:.2f}s, wrote {r['bytes_written']} B")
    # verify a sample of whole-object rewrites with stock CLIs, recovery identity only
    out = os.path.join(d, "out-whole_object_rewrite")
    good = 0
    names = sorted(os.listdir(out))[:10]
    for nme in names:
        a = subprocess.run([AGE, "-d", "-i", os.path.join(d, "recovery.key"), os.path.join(out, nme)], env=ENV, capture_output=True)
        b = subprocess.run([DEBIAN_AGE, "-d", "-i", os.path.join(d, "recovery.key"), os.path.join(out, nme)], capture_output=True)
        o = subprocess.run([AGE, "-d", "-i", os.path.join(d, "ingest.key"), os.path.join(d, "in", nme)], env=ENV, capture_output=True)
        if a.returncode == 0 and b.returncode == 0 and a.stdout == o.stdout == b.stdout:
            good += 1
        # payload bytes unchanged
    same_payload = 0
    for nme in names:
        src = open(os.path.join(d, "in", nme), "rb").read()
        dst = open(os.path.join(out, nme), "rb").read()
        if src[header_len(os.path.join(d, "in", nme)):] == dst[header_len(os.path.join(out, nme)):]:
            same_payload += 1
    check("file rewrap: 10 sampled rewritten objects decrypt with the recovery key under age v1.3.1 and distro age 1.1.1", good == len(names), f"{good}/{len(names)}")
    check("file rewrap: payload bytes after the header are byte-identical", same_payload == len(names), f"{same_payload}/{len(names)}")
    shutil.rmtree(d, ignore_errors=True)


def throughput():
    """Full re-encryption cost: stock age decrypt | encrypt on a 1 GiB synthetic file in tmpfs."""
    size = (64 << 20) if QUICK else (1 << 30)
    d = os.path.join(SHM, "tp")
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    ik, rk = os.path.join(d, "i.key"), os.path.join(d, "r.key")
    run([KEYGEN, "-o", ik])
    run([KEYGEN, "-o", rk])
    ir, rr = recipient_of(ik), recipient_of(rk)
    pt = os.path.join(d, "pt.bin")
    with open(pt, "wb") as f:
        for _ in range(size >> 20):
            f.write(secrets.token_bytes(1 << 20))
    enc = os.path.join(d, "ct.age")
    runs = {"encrypt": [], "decrypt": [], "reencrypt_pipe": [], "copy": []}
    for rep in range(3):
        t0 = time.time(); run([AGE, "-r", ir, "-o", enc, pt]); runs["encrypt"].append(time.time() - t0)
        t0 = time.time(); run([AGE, "-d", "-i", ik, "-o", os.path.join(d, "dec.bin"), enc]); runs["decrypt"].append(time.time() - t0)
        os.unlink(os.path.join(d, "dec.bin"))
        t0 = time.time()
        subprocess.run(f"'{AGE}' -d -i '{ik}' '{enc}' | '{AGE}' -r '{ir}' -r '{rr}' -o '{d}/re.age'", shell=True, check=True, env=ENV)
        runs["reencrypt_pipe"].append(time.time() - t0)
        os.unlink(os.path.join(d, "re.age"))
        t0 = time.time(); shutil.copyfile(enc, os.path.join(d, "copy.age")); runs["copy"].append(time.time() - t0)
        os.unlink(os.path.join(d, "copy.age"))
    mib = size / (1 << 20)
    res = {"bytes": size, "storage": "tmpfs (/dev/shm)", "loadavg_after": loadavg(), "runs_s": {k: [round(x, 3) for x in v] for k, v in runs.items()}}
    res["median_MiB_per_s"] = {k: round(mib / sorted(v)[1], 1) for k, v in runs.items()}
    results["throughput"] = res
    log(f"throughput MiB/s (median of 3): {res['median_MiB_per_s']}; load {res['loadavg_after']}")
    shutil.rmtree(d, ignore_errors=True)


def main():
    shutil.rmtree(WORK, ignore_errors=True)
    os.makedirs(WORK)
    os.makedirs(EVID, exist_ok=True)
    results["env"] = {
        "age": run([AGE, "--version"]).stdout.decode().strip(),
        "distro_age": run([DEBIAN_AGE, "--version"]).stdout.decode().strip(),
        "shamir_mnemonic": "0.3.0 (pip, [cli] extra)",
        "age_plugin_sss": "v0.4.0 (go install from proxy.golang.org)",
        "go": run(["go", "version"]).stdout.decode().strip(),
        "python": sys.version.split()[0],
        "nproc": os.cpu_count(),
        "loadavg_start": loadavg(),
        "host": "shared cloud container (other agents running; timings are noisy upper bounds)",
    }
    photos = os.path.join(WORK, "photos")
    hashes = make_photos(photos)
    results["photos"] = {"count": len(hashes), "total_bytes": sum(os.path.getsize(os.path.join(photos, n)) for n in hashes), "class": "SYN (random bytes with a JPEG-like prefix)"}
    mixing_rules()
    variant_sealed("A-classic-sealed-slip39-128", False, 128, photos, hashes)
    variant_sealed("B-pq-sealed-slip39-256", True, 256, photos, hashes)
    variant_raw_slip39("C1-classic-raw-slip39", False, photos, hashes)
    variant_raw_slip39("C2-pq-raw-slip39", True, photos, hashes)
    variant_sss("D1-classic-age-plugin-sss", False, photos, hashes)
    variant_sss("D2-pq-age-plugin-sss", True, photos, hashes)
    rewrap_costs()
    throughput()
    results["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    results["loadavg_end"] = loadavg()
    results["checks"] = checks
    results["checks_passed"] = sum(c["pass"] for c in checks)
    results["checks_total"] = len(checks)
    with open(os.path.join(EVID, "results.json"), "w") as f:
        json.dump(results, f, indent=2)
    with open(os.path.join(EVID, "run-log.txt"), "w") as f:
        f.write("\n".join(log_lines) + "\n")
    shutil.rmtree(WORK, ignore_errors=True)
    shutil.rmtree(SHM, ignore_errors=True)
    log(f"{results['checks_passed']}/{results['checks_total']} checks passed")
    sys.exit(0 if results["checks_passed"] == results["checks_total"] else 1)


if __name__ == "__main__":
    main()
