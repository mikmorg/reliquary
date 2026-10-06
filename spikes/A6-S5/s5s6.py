#!/usr/bin/env python3
"""A6-S5 (format independence) and A6-S6 (A' rewrap round trip) driver. THROWAWAY.

Data class SYN -> results: synthetic random content, throwaway keys created in WORK.
"""
import base64, glob, hashlib, json, os, random, shutil, subprocess, sys, time

A6 = sys.argv[1]           # scratchpad A6 dir (bin/, cargo/bin/, harness/)
WORK = sys.argv[2]         # e.g. /dev/shm/a6fmt
EVID = sys.argv[3]         # evidence json path
N = int(os.environ.get("N", "200"))
SCALE = os.environ.get("SCALE", "0.1")
B = f"{A6}/bin/a6cas"
DECRYPTORS = {"age-1.1.1-debian": "/usr/bin/age", "age-1.3.1-go": f"{A6}/bin/age", "rage-0.12.1-rust": f"{A6}/cargo/bin/rage"}
PROC = f"{A6}/harness/restore-without-reliquary.sh"
res = {"started": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "N": N, "scale": SCALE, "variants": {}}


def sh(cmd, env=None, check=True):
    p = subprocess.run(cmd, capture_output=True, env=env)
    if check and p.returncode != 0:
        raise RuntimeError(f"{cmd} rc={p.returncode}: {p.stderr.decode(errors='replace')[-600:]}")
    return p


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def hdr_len(path):
    with open(path, "rb") as f:
        data = f.read(1 << 16)
    i = data.index(b"\n---")
    return data.index(b"\n", i + 1) + 1


for variant in ("x25519", "pq"):
    v = {}
    d = f"{WORK}/{variant}"
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    sh([B, "keygen", "-dir", f"{d}/keys"] + (["-pq"] if variant == "pq" else []))
    sh([B, "gen", "-out", f"{d}/corp", "-keys", f"{d}/keys", "-n", str(N), "-dup", "0.1", "-scale", SCALE, "-seed", "5"])
    sh([B, "init", "-store", f"{d}/store", "-devices", f"{d}/corp/devices.json"])
    t0 = time.time()
    p = sh([B, "ingest", "-store", f"{d}/store", "-catalog", f"{d}/cat.db", "-staging", f"{d}/corp/staging",
            "-ingest-key", f"{d}/keys/ingest-e1.key", "-rcpt", f"{d}/keys/stored-recipients.txt", "-family", f"{d}/keys/family-secret.hex"])
    v["ingest_stderr"] = p.stderr.decode().strip()
    v["acks"] = sum(1 for l in p.stdout.decode().splitlines() if l.startswith("ACK"))
    # S6: Go library checks (a6cas verify)
    v["verify_go_lib"] = json.loads(sh([B, "verify", "-store", f"{d}/store", "-archive-key", f"{d}/keys/archive.key",
                                         "-recovery-key", f"{d}/keys/recovery.key", "-ingest-key", f"{d}/keys/ingest-e1.key"]).stdout)
    man = [json.loads(l) for l in open(f"{d}/store/manifest/manifest.jsonl")]
    blobs = {m["sha256"]: m for m in man if m["t"] == "blob"}
    recs = {m["record_id"]: m for m in man if m["t"] == "record"}
    blob_paths = {s: f"{d}/store/blobs/{s[0:2]}/{s[2:4]}/{s}.age" for s in blobs}
    rec_paths = {r: f"{d}/store/records/{r[0:2]}/{r}.age" for r in recs}
    # S6: payload bytes untouched (stored[len(new hdr):] == staged[len(h0):])
    staged_by_mac = {}
    for op in glob.glob(f"{d}/corp/staging/*.obj.age"):
        hl = hdr_len(op)
        with open(op, "rb") as f:
            h = f.read(hl)
        staged_by_mac[h] = op
    same, diff = 0, 0
    for s, m in blobs.items():
        h0 = base64.b64decode(m["h0"] + "=" * (-len(m["h0"]) % 4))
        op = staged_by_mac[h0]
        sp = blob_paths[s]
        with open(op, "rb") as a, open(sp, "rb") as b:
            a.seek(len(h0)); b.seek(hdr_len(sp))
            if a.read() == b.read():
                same += 1
            else:
                diff += 1
    v["payload_identical"] = same
    v["payload_differs"] = diff
    v["stored_header_bytes"] = sorted({hdr_len(p) for p in blob_paths.values()})
    v["original_header_bytes"] = sorted({len(base64.b64decode(m["h0"] + "=" * (-len(m["h0"]) % 4))) for m in blobs.values()})
    stored_total = sum(os.path.getsize(p) for p in blob_paths.values())
    plain_total = sum(m.get("size", 0) for m in blobs.values())
    v["blob_overhead_bytes"] = stored_total - plain_total
    v["blob_overhead_pct"] = round(100 * (stored_total - plain_total) / max(plain_total, 1), 4)
    v["record_files_bytes"] = sum(os.path.getsize(p) for p in rec_paths.values())
    v["manifest_bytes"] = os.path.getsize(f"{d}/store/manifest/manifest.jsonl")
    v["catalog_bytes"] = sum(os.path.getsize(p) for p in glob.glob(f"{d}/cat.db*"))
    # S6/S5: independent decryptors
    dec = {}
    tmp = f"{d}/dec.tmp"
    for name, binary in DECRYPTORS.items():
        r = {"archive_ok": 0, "archive_fail": 0, "recovery_ok": 0, "recovery_fail": 0, "ingest_refused": 0,
             "ingest_DECRYPTED": 0, "records_ok": 0, "records_fail": 0, "errors": []}
        t0 = time.time()
        for s, p in blob_paths.items():
            for key, field in (("archive", "archive"), ("recovery", "recovery")):
                with open(tmp, "wb") as o:  # stdout, not -o (see empty-file quirk)
                    q = subprocess.run([binary, "-d", "-i", f"{d}/keys/{key}.key", p], stdout=o, stderr=subprocess.PIPE)
                if q.returncode == 0 and sha(tmp) == s:
                    r[field + "_ok"] += 1
                else:
                    r[field + "_fail"] += 1
                    if len(r["errors"]) < 3:
                        r["errors"].append(q.stderr.decode(errors="replace").strip()[:200])
                if os.path.exists(tmp):
                    os.remove(tmp)
            q = subprocess.run([binary, "-d", "-i", f"{d}/keys/ingest-e1.key", p], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            if q.returncode == 0:
                r["ingest_DECRYPTED"] += 1
            else:
                r["ingest_refused"] += 1
            if os.path.exists(tmp):
                os.remove(tmp)
        for rid, p in rec_paths.items():
            q = subprocess.run([binary, "-d", "-i", f"{d}/keys/archive.key", p], capture_output=True)
            if q.returncode == 0 and json.loads(q.stdout.split(b"\n")[0])["record_id"] == rid:
                r["records_ok"] += 1
            else:
                r["records_fail"] += 1
        r["seconds"] = round(time.time() - t0, 2)
        dec[name] = r
    v["independent_decryptors"] = dec
    # S5: the one-page procedure, with each decryptor
    proc = {}
    truth = [json.loads(l) for l in open(f"{d}/corp/truth.jsonl")]
    names = random.Random(7).sample([t for t in truth], 3)
    for name, binary in DECRYPTORS.items():
        env = dict(os.environ, AGE=binary)
        out = f"{d}/restore-{name}"
        shutil.rmtree(out, ignore_errors=True)
        t0 = time.time()
        q = sh(["bash", PROC, "all", f"{d}/store", f"{d}/keys/archive.key", out], env=env, check=False)
        r = {"all_rc": q.returncode, "all_out": q.stdout.decode().strip()[-200:], "all_err": q.stderr.decode().strip()[-300:],
             "all_seconds": round(time.time() - t0, 2)}
        restored = {os.path.basename(p): sha(p) for p in glob.glob(f"{out}/*")}
        r["all_byte_identical"] = sum(1 for k, h in restored.items() if k == h)
        r["all_expected"] = len(blobs)
        bn = []
        for t in names:
            t0 = time.time()
            q = sh(["bash", PROC, "by-name", f"{d}/store", f"{d}/keys/archive.key", t["name"], f"{out}-byname"], env=env, check=False)
            ok = q.returncode == 0 and sha(f"{out}-byname/{t['name']}") == t["sha256"]
            t1 = time.time()
            q2 = sh(["bash", PROC, "by-name-catalog", f"{d}/store", f"{d}/keys/archive.key", t["name"], f"{out}-bycat", f"{d}/cat.db"], env=env, check=False)
            ok2 = q2.returncode == 0 and sha(f"{out}-bycat/{t['name']}") == t["sha256"]
            bn.append({"size": t["size"], "no_catalog_ok": ok, "no_catalog_s": round(t1 - t0, 3),
                       "with_sqlite3_catalog_ok": ok2, "with_catalog_s": round(time.time() - t1, 3)})
        r["by_name"] = bn
        proc[name] = r
        shutil.rmtree(out, ignore_errors=True)
    v["procedure"] = proc
    # single-file restore by SHA-256 through a6cas get (container, tmpfs; not homelab hardware)
    lat = []
    big = sorted(blobs.values(), key=lambda m: -m.get("size", 0))[:5] + random.Random(9).sample(list(blobs.values()), 15)
    for m in big:
        q = json.loads(sh([B, "get", "-store", f"{d}/store", "-archive-key", f"{d}/keys/archive.key", "-sha256", m["sha256"], "-out", f"{d}/get.tmp"]).stdout)
        lat.append({"bytes": q["bytes"], "seconds": q["seconds"], "ok": q["sha256_ok"]})
    v["get_by_sha256"] = lat
    # quirk check: does "-o FILE" create FILE for an empty plaintext?
    e = hashlib.sha256(b"").hexdigest()
    quirk = {}
    for name, binary in DECRYPTORS.items():
        if os.path.exists(tmp):
            os.remove(tmp)
        q = subprocess.run([binary, "-d", "-i", f"{d}/keys/archive.key", "-o", tmp, blob_paths[e]], capture_output=True)
        quirk[name] = {"rc": q.returncode, "output_file_created": os.path.exists(tmp)}
    v["empty_plaintext_dash_o_quirk"] = quirk
    res["variants"][variant] = v
    print(variant, "done", file=sys.stderr)

json.dump(res, open(EVID, "w"), indent=1)
print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk not in ("procedure", "get_by_sha256", "independent_decryptors")} for k, v in res["variants"].items()}, indent=1))
