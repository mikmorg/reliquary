#!/usr/bin/env python3
"""A6-S3 crash-consistency harness (THROWAWAY spike code, Reliquary A6).

Repeatedly starts `a6cas ingest`, kills it with SIGKILL at a random moment and,
in --powercut mode, then tells LazyFS to drop every unsynced byte
("lazyfs::clear-cache"), which emulates a power cut at the moment of the kill.
After each crash it runs `a6cas recover` and checks the invariants:

  I1  every item ever ACKed in this cycle is in the catalog, has a manifest line,
      and its stored files hash to the manifest's stored_sha256 (keyless audit)
  I2  no catalog row points at a missing manifest entry
  I3  once all staged items are ACKed, every object decrypts with the archive
      key to the expected plaintext SHA-256 and the catalog matches truth.jsonl

Data class: SYN -> results (synthetic random bytes, throwaway keys).
"""
import argparse, json, os, random, shutil, signal, sqlite3, subprocess, sys, threading, time

ap = argparse.ArgumentParser()
ap.add_argument("--a6cas", required=True)
ap.add_argument("--corpus", required=True, help="dir made by `a6cas gen` (staging/, devices.json, truth.jsonl)")
ap.add_argument("--keys", required=True)
ap.add_argument("--work", required=True, help="dir that holds store/ and catalog.db (a LazyFS mount for --powercut)")
ap.add_argument("--kills", type=int, default=100)
ap.add_argument("--min-delay", type=float, default=0.02)
ap.add_argument("--max-delay", type=float, default=1.0)
ap.add_argument("--powercut", action="store_true", help="send lazyfs::clear-cache after each kill")
ap.add_argument("--fifo", default="/dev/shm/lfs.fifo")
ap.add_argument("--done-fifo", default="/dev/shm/lfs.done.fifo")
ap.add_argument("--nofsync", action="store_true", help="NEGATIVE CONTROL: ingest without fsync")
ap.add_argument("--layout", default="cas")
ap.add_argument("--seed", type=int, default=6)
ap.add_argument("--crashpoint", default="", help="A6CAS_CRASHPOINT (name or 'any'): the process kills itself at that point")
ap.add_argument("--crash-prob", type=float, default=0.0)
ap.add_argument("--evidence", required=True)
a = ap.parse_args()

rnd = random.Random(a.seed)
truth = [json.loads(l) for l in open(os.path.join(a.corpus, "truth.jsonl"))]
STORE = os.path.join(a.work, "store")
CAT = os.path.join(a.work, "catalog.db")
ev = open(a.evidence, "a")


def log(obj):
    obj["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    ev.write(json.dumps(obj) + "\n")
    ev.flush()


def run(args, check=True):
    p = subprocess.run([a.a6cas] + args, capture_output=True, text=True)
    if check and p.returncode != 0:
        raise RuntimeError(f"{args[0]} rc={p.returncode}: {p.stderr[-800:]}")
    return p


def clear_cache():
    """Drop all unsynced data in LazyFS. Confirmed with a canary: an unsynced file
    written just before the command must read back empty afterwards."""
    canary = os.path.join(a.work, "canary.unsynced")
    with open(canary, "wb") as f:
        f.write(b"x" * 8192)  # no fsync on purpose
    with open(a.fifo, "w") as f:
        f.write("lazyfs::clear-cache\n")
    for _ in range(300):
        time.sleep(0.05)
        if os.path.getsize(canary) == 0:
            os.remove(canary)
            return True
    return False


def fresh_store():
    for p in (STORE, CAT, CAT + "-wal", CAT + "-shm"):
        if os.path.isdir(p):
            shutil.rmtree(p)
        elif os.path.exists(p):
            os.remove(p)
    run(["init", "-store", STORE, "-layout", a.layout, "-devices", os.path.join(a.corpus, "devices.json")])


ingest_args = ["ingest", "-store", STORE, "-catalog", CAT, "-staging", os.path.join(a.corpus, "staging"),
               "-ingest-key", os.path.join(a.keys, "ingest-e1.key"), "-rcpt", os.path.join(a.keys, "stored-recipients.txt"),
               "-family", os.path.join(a.keys, "family-secret.hex")] + (["-nofsync"] if a.nofsync else [])


def ingest_once(delay):
    """Start ingest; SIGKILL after `delay` s (None = run to completion). Returns (acks, finished)."""
    env = dict(os.environ)
    if a.crashpoint and delay is not None:
        env["A6CAS_CRASHPOINT"] = a.crashpoint
        env["A6CAS_CRASH_PROB"] = str(a.crash_prob)
    p = subprocess.Popen([a.a6cas] + ingest_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1, env=env)
    acks = []
    def reader():
        for line in p.stdout:
            parts = line.split()
            if parts and parts[0] == "ACK" and len(parts) == 2:
                acks.append(parts[1])
    t = threading.Thread(target=reader)
    t.start()
    killed = False
    if delay is not None:
        try:
            p.wait(timeout=delay)
        except subprocess.TimeoutExpired:
            p.send_signal(signal.SIGKILL)
            killed = True
    p.wait()
    t.join()
    err = p.stderr.read()
    if p.returncode == -9 and not killed:
        killed = True
        cp = [l.split()[1] for l in err.splitlines() if l.startswith("CRASHPOINT")]
        crash_points.append(cp[0] if cp else "?")
    if p.returncode not in (0, -9):
        raise RuntimeError(f"ingest rc={p.returncode}: {err[-800:]}")
    return acks, killed


def check_invariants(acked):
    rec = json.loads(run(["recover", "-store", STORE, "-catalog", CAT]).stdout)
    aud_p = run(["audit", "-store", STORE], check=False)
    aud = json.loads(aud_p.stdout)
    con = sqlite3.connect(CAT)
    in_cat = {r[0] for r in con.execute("SELECT record_id FROM records")}
    con.close()
    man = set()
    mp = os.path.join(STORE, "manifest", "manifest.jsonl")
    if os.path.exists(mp):
        for l in open(mp):
            o = json.loads(l)
            if o["t"] == "record":
                man.add(o["record_id"])
    lost_cat = sorted(set(acked) - in_cat)
    lost_man = sorted(set(acked) - man)
    viol = {"acked_not_in_catalog": len(lost_cat), "acked_not_in_manifest": len(lost_man),
            "catalog_rows_without_store": rec["catalog_rows_without_store"],
            "audit_mismatch": aud["mismatch"], "audit_missing": aud["missing"]}
    return rec, aud, viol


summary = {"mode": "powercut(LazyFS clear-cache)" if a.powercut else "kill -9", "nofsync": a.nofsync, "layout": a.layout,
           "kills": 0, "cycles_completed": 0, "violations": {}, "quarantined": 0, "torn_manifest_events": 0,
           "tmp_removed": 0, "acks_total": 0, "final_checks": []}
fresh_store()
acked = set()
cycle = 0
crash_points = []
k = -1
while summary["kills"] < a.kills:
    k += 1
    delay = rnd.uniform(a.min_delay, a.max_delay)
    acks, killed = ingest_once(delay)
    acked.update(acks)
    summary["acks_total"] += len(acks)
    cleared = None
    if killed:
        summary["kills"] += 1
        if a.powercut:
            cleared = clear_cache()
    rec, aud, viol = check_invariants(acked)
    for kk, v in viol.items():
        if v:
            summary["violations"][kk] = summary["violations"].get(kk, 0) + v
    summary["quarantined"] += rec["quarantined"]
    summary["tmp_removed"] += rec["tmp_removed"]
    summary["torn_manifest_events"] += 1 if rec["torn_manifest_bytes"] else 0
    log({"iter": k, "cycle": cycle, "delay_s": round(delay, 3), "killed": killed, "clear_cache_ok": cleared,
         "acks_this_run": len(acks), "acked_cycle": len(acked), "recover": rec,
         "audit": {x: aud[x] for x in ("objects_ok", "mismatch", "missing")}, "violations": viol})
    if not killed or len(acked) >= len(truth):
        # finish the cycle (no kill), then the full keyed check
        acks, _ = ingest_once(None)
        acked.update(acks)
        rec, aud, viol = check_invariants(acked)
        ver = json.loads(run(["verify", "-store", STORE, "-archive-key", os.path.join(a.keys, "archive.key"),
                              "-recovery-key", os.path.join(a.keys, "recovery.key")]).stdout)
        con = sqlite3.connect(CAT)
        cat = {r[0]: r[1] for r in con.execute("SELECT record_id, sha256 FROM records")}
        con.close()
        truth_ok = all(cat.get(t["record_id"]) == t["sha256"] for t in truth) and len(cat) == len(truth)
        fails = {kk: v for kk, v in ver["counts"].items() if "FAIL" in kk}
        fc = {"cycle": cycle, "acked": len(acked), "truth_items": len(truth), "catalog_matches_truth": truth_ok,
              "verify_fail_counts": fails, "violations_at_end": viol}
        summary["final_checks"].append(fc)
        log({"cycle_end": fc})
        summary["cycles_completed"] += 1
        cycle += 1
        acked = set()
        fresh_store()
summary["self_crash_points"] = {c: crash_points.count(c) for c in sorted(set(crash_points))}
summary["iterations"] = k + 1
log({"summary": summary})
print(json.dumps(summary, indent=1))
