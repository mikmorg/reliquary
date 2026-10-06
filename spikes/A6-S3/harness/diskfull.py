#!/usr/bin/env python3
"""A6-S3 disk-full (ENOSPC) fault case (THROWAWAY spike code, Reliquary A6).

Added after Kopia issue #4348 ("possible to corrupt a repository when ... the
repository runs out of free space"). For each trial, the store and catalog sit on
a size-limited tmpfs that fills somewhere during ingest. Then:

  1. ingest until it fails (no kill: the process hits ENOSPC / SQLITE_FULL itself)
  2. while the disk is STILL FULL: run `recover`, re-check invariants, and retry
     ingest once (a retry storm must not ACK anything that is not durable)
  3. grow the filesystem (mount -o remount,size=...), recover, ingest to the end
  4. keyed check: every object decrypts with archive and recovery keys, catalog
     equals truth.jsonl

Invariants (same as crash.py): I1 every ACKed item is in catalog and manifest and
the keyless audit passes; I2 no catalog row without a store entry; I3 keyed check.

Placement "same": store and catalog on one full filesystem.
Placement "catfull": store on a roomy filesystem, catalog alone on a tiny one
(exercises SQLITE_FULL after the object and manifest line are already durable).

Data class: SYN -> results. Needs root (mount). tmpfs ENOSPC arrives at write();
real ZFS can also fail at fsync/txg time, which this does not emulate.
"""
import argparse, json, os, random, sqlite3, subprocess, time

ap = argparse.ArgumentParser()
ap.add_argument("--a6cas", required=True)
ap.add_argument("--corpus", required=True)
ap.add_argument("--keys", required=True)
ap.add_argument("--base", required=True, help="dir under which tmpfs mounts are made")
ap.add_argument("--trials", type=int, default=20)
ap.add_argument("--placement", default="same", choices=["same", "catfull", "manfull", "ext4same", "external"])
ap.add_argument("--layout", default="cas")
ap.add_argument("--full-bytes", type=int, required=True, help="approx bytes of a complete store")
ap.add_argument("--seed", type=int, default=1)
ap.add_argument("--evidence", required=True)
ap.add_argument("--prep-cmd", default="", help="external: shell command run per trial with $SIZE and $MNT set; must leave an "
                "empty filesystem mounted at $MNT whose free space is about $SIZE bytes (kit: ZFS file-backed pool)")
ap.add_argument("--grow-cmd", default="", help="external: shell command that gives $MNT lots of free space")
a = ap.parse_args()
rnd = random.Random(a.seed)
truth = [json.loads(l) for l in open(os.path.join(a.corpus, "truth.jsonl"))]
ev = open(a.evidence, "a")
SM = os.path.join(a.base, "mnt-store")  # for --placement external this is $MNT
CM = os.path.join(a.base, "mnt-cat")


def sh(*cmd):
    subprocess.run(cmd, check=True)


def mount(path, size):
    os.makedirs(path, exist_ok=True)
    subprocess.run(["umount", path], capture_output=True)
    sh("mount", "-t", "tmpfs", "-o", f"size={size}", "tmpfs", path)


def run(args):
    p = subprocess.run([a.a6cas] + args, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def classify(err):
    e = err.lower()
    if "no space left" in e:
        return "ENOSPC"
    if "disk is full" in e or "sqlite_full" in e or "database or disk is full" in e:
        return "SQLITE_FULL"
    return err.strip().splitlines()[-1][-160:] if err.strip() else ""


def where(err):
    e = err.lower()
    for key, label in (("manifest", "manifest"), ("records/", "record-object"), ("blobs/", "blob-object"),
                       ("/tmp/", "temp-object"), ("tmp", "temp-object"), ("database", "catalog"), ("sqlite", "catalog"),
                       ("catalog", "catalog")):
        if key in e:
            return label
    return "other"


def paths():
    store = os.path.join(SM, "store")
    cat = os.path.join(CM if a.placement == "catfull" else SM, "catalog.db")
    return store, cat


def ingest(store, cat):
    rc, out, err = run(["ingest", "-store", store, "-catalog", cat, "-staging", os.path.join(a.corpus, "staging"),
                        "-ingest-key", os.path.join(a.keys, "ingest-e1.key"),
                        "-rcpt", os.path.join(a.keys, "stored-recipients.txt"),
                        "-family", os.path.join(a.keys, "family-secret.hex")])
    acks = [l.split()[1] for l in out.splitlines() if l.startswith("ACK ") and len(l.split()) == 2]
    return rc, acks, classify(err) if rc else "", err


def check(store, cat, acked):
    rc, out, err = run(["recover", "-store", store, "-catalog", cat])
    rec = json.loads(out) if rc == 0 and out.strip() else {"rc": rc, "err": classify(err)}
    arc, aout, aerr = run(["audit", "-store", store])
    aud = json.loads(aout) if aout.strip() else {"rc": arc, "err": classify(aerr)}
    try:
        con = sqlite3.connect(f"file:{cat}?mode=ro", uri=True)
        in_cat = {r[0] for r in con.execute("SELECT record_id FROM records")}
        con.close()
        cat_err = None
    except Exception as e:  # noqa
        in_cat, cat_err = set(), str(e)
    man = set()
    mp = os.path.join(store, "manifest", "manifest.jsonl")
    if os.path.exists(mp):
        for l in open(mp):
            try:
                o = json.loads(l)
            except Exception:
                continue  # torn line (recover may not have run if it failed)
            if o.get("t") == "record":
                man.add(o["record_id"])
    viol = {"acked_not_in_catalog": len(set(acked) - in_cat), "acked_not_in_manifest": len(set(acked) - man),
            "catalog_rows_without_store": rec.get("catalog_rows_without_store", 0),
            "audit_mismatch": aud.get("mismatch", 0), "audit_missing": aud.get("missing", 0)}
    return rc == 0, rec, aud, viol, cat_err


summary = {"placement": a.placement, "layout": a.layout, "trials": 0, "failure_kinds": {},
           "recover_while_full_ok": 0, "recover_while_full_failed": 0, "retry_while_full_new_acks": 0,
           "violations": {}, "final_ok": 0, "final_fail": 0, "quarantined": 0, "tmp_removed": 0, "torn": 0,
           "trials_without_enospc": 0}
for t in range(a.trials):
    for m in ((os.path.join(SM, "store", "manifest"), SM, CM) if a.placement != "external" else ()):
        subprocess.run(["umount", m], capture_output=True)
    if a.placement == "same":
        size = int(rnd.uniform(0.02, 0.98) * a.full_bytes)
        mount(SM, size)
    elif a.placement == "catfull":
        size = int(rnd.uniform(16 * 1024, 900 * 1024))
        mount(SM, 2 * a.full_bytes)
        mount(CM, size)
    elif a.placement == "ext4same":  # real ext4 on a loop device; a filler file takes the space away
        img = os.path.join(a.base, "img.ext4")
        subprocess.run(["umount", SM], capture_output=True)
        if os.path.exists(img):
            os.remove(img)
        sh("truncate", "-s", str(int(1.6 * a.full_bytes)), img)
        sh("mkfs.ext4", "-q", "-F", img)
        os.makedirs(SM, exist_ok=True)
        sh("mount", "-o", "loop", img, SM)
        st = os.statvfs(SM)
        avail = st.f_bavail * st.f_frsize
        size = int(rnd.uniform(0.02, 0.98) * a.full_bytes)
        sh("fallocate", "-l", str(max(avail - size, 4096)), os.path.join(SM, "filler"))
        sh("sync")
    elif a.placement == "external":
        size = int(rnd.uniform(0.02, 0.98) * a.full_bytes)
        subprocess.run(a.prep_cmd, shell=True, check=True, env=dict(os.environ, SIZE=str(size), MNT=SM))
    else:  # manfull: only store/manifest/ is a tiny filesystem (append-only manifest hits ENOSPC)
        size = int(rnd.uniform(4 * 1024, 640 * 1024))
        subprocess.run(["umount", os.path.join(SM, "store", "manifest")], capture_output=True)
        mount(SM, 2 * a.full_bytes)
    store, cat = paths()
    rc, _, err = run(["init", "-store", store, "-layout", a.layout, "-devices", os.path.join(a.corpus, "devices.json")])
    if rc:
        raise SystemExit(f"init failed: {err}")
    MM = os.path.join(store, "manifest")
    if a.placement == "manfull":
        keep = {f: open(os.path.join(MM, f), "rb").read() for f in os.listdir(MM)}
        mount(MM, size)
        for f, b in keep.items():
            with open(os.path.join(MM, f), "wb") as fh:
                fh.write(b)
    acked = set()
    rc1, acks1, kind, err1 = ingest(store, cat)
    acked.update(acks1)
    if rc1 == 0:
        summary["trials_without_enospc"] += 1
    wk = (kind or "none") + ("@" + where(err1) if rc1 else "")
    summary["failure_kinds"][wk] = summary["failure_kinds"].get(wk, 0) + 1
    ok_full, rec_full, aud_full, viol_full, cerr_full = check(store, cat, acked)
    summary["recover_while_full_ok" if ok_full else "recover_while_full_failed"] += 1
    rc2, acks2, kind2, _ = ingest(store, cat)  # retry while still full
    acked.update(acks2)
    summary["retry_while_full_new_acks"] += len(acks2)
    _, rec_full2, _, viol_full2, _ = check(store, cat, acked)
    # grow the filesystem and finish
    if a.placement == "ext4same":
        os.remove(os.path.join(SM, "filler"))
        sh("sync")
    elif a.placement == "external":
        subprocess.run(a.grow_cmd, shell=True, check=True, env=dict(os.environ, MNT=SM))
    else:
        grow = {"catfull": CM, "same": SM, "manfull": MM}[a.placement]
        sh("mount", "-o", f"remount,size={3 * a.full_bytes}", grow)
    ok_g, rec_g, aud_g, viol_g, _ = check(store, cat, acked)
    rc3, acks3, kind3, err3 = ingest(store, cat)
    acked.update(acks3)
    ok_e, rec_e, aud_e, viol_e, _ = check(store, cat, acked)
    vrc, vout, verr = run(["verify", "-store", store, "-archive-key", os.path.join(a.keys, "archive.key"),
                           "-recovery-key", os.path.join(a.keys, "recovery.key")])
    ver = json.loads(vout) if vrc == 0 else {"counts": {"VERIFY_RC_FAIL": vrc}}
    con = sqlite3.connect(cat)
    catm = {r[0]: r[1] for r in con.execute("SELECT record_id, sha256 FROM records")}
    con.close()
    truth_ok = len(catm) == len(truth) and all(catm.get(x["record_id"]) == x["sha256"] for x in truth)
    fails = {k: v for k, v in ver["counts"].items() if "FAIL" in k}
    final_ok = rc3 == 0 and truth_ok and not fails and len(acked) == len(truth)
    summary["final_ok" if final_ok else "final_fail"] += 1
    for vv in (viol_full, viol_full2, viol_g, viol_e):
        for k, v in vv.items():
            if v:
                summary["violations"][k] = summary["violations"].get(k, 0) + v
    for r in (rec_full, rec_full2, rec_g, rec_e):
        summary["quarantined"] += r.get("quarantined", 0)
        summary["tmp_removed"] += r.get("tmp_removed", 0)
        summary["torn"] += 1 if r.get("torn_manifest_bytes") else 0
    summary["trials"] += 1
    ev.write(json.dumps({"trial": t, "fs_size_bytes": size, "ingest1": {"rc": rc1, "acks": len(acks1), "failure": kind, "where": where(err1) if rc1 else None,
                                     "err_tail": err1.strip().splitlines()[-1][-200:] if rc1 and err1.strip() else None},
                         "while_full": {"recover_ok": ok_full, "recover": rec_full, "audit_ok": aud_full.get("objects_ok"),
                                        "catalog_read_error": cerr_full, "violations": viol_full,
                                        "retry_rc": rc2, "retry_new_acks": len(acks2), "retry_failure": kind2,
                                        "after_retry_violations": viol_full2},
                         "after_grow": {"recover": rec_g, "violations": viol_g},
                         "finish": {"rc": rc3, "acks": len(acks3), "err": kind3, "violations": viol_e,
                                    "catalog_matches_truth": truth_ok, "verify_fail_counts": fails,
                                    "acked_total": len(acked)},
                         "final_ok": final_ok, "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}) + "\n")
    ev.flush()
for m in ((os.path.join(SM, "store", "manifest"), SM, CM) if a.placement != "external" else ()):
    subprocess.run(["umount", m], capture_output=True)
print(json.dumps(summary, indent=1))
