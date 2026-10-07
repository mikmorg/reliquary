#!/usr/bin/env python3
"""A3-S1 run B: write an MC module + cfg for a configuration and run TLC on it.

usage: run.py CONFIG [--design v0|v1] [--bug NAME] [--safety-only] [--no-i7]
                     [--faults a,b,c] [--max-faults N] [--K N] [--workers N] [--tag T]

Results: results/<tag>.log (full TLC output) and one JSON line per run in
results/summary.jsonl. TLC's state queue goes to /dev/shm (RAM) because the
container's disk quota is small.
"""
import argparse, json, os, re, subprocess, time

HERE = os.path.dirname(os.path.abspath(__file__))
JAR = os.environ.get("TLA2TOOLS", os.path.join(HERE, "..", "tools", "tla2tools-1.7.4.jar"))
ALL = ["kill", "devcrash", "lostresp", "homecrash", "down", "abort", "r2loss", "bad",
       "gcrace", "rollback", "spurious"]

CONFIGS = {
    # devices -> items held
    "2x1": dict(hold={"d1": ["c1"], "d2": ["c1"]}),
    "3x1": dict(hold={"d1": ["c1"], "d2": ["c1"], "d3": ["c1"]}),
    "1x2": dict(hold={"d1": ["c1", "c2"]}),
    "2x2": dict(hold={"d1": ["c1", "c2"], "d2": ["c1", "c2"]}),
    # PLAN headline: 3 devices x 3 items; each item held by two devices
    "3x3ring": dict(hold={"d1": ["c1", "c2"], "d2": ["c2", "c3"], "d3": ["c3", "c1"]}),
    # 3 devices x 3 items, everyone holds everything
    "3x3full": dict(hold={"d1": ["c1", "c2", "c3"], "d2": ["c1", "c2", "c3"], "d3": ["c1", "c2", "c3"]}),
}

SAFETY = ["TypeOK", "I1_NoDeleteBeforeCommit", "I2_SafeOnlyWithReceipt", "I3_NoFalseMerge",
          "I4_OneReceiptPerRecord", "I6_RelayIsCache"]
LIVE = ["L1_EventuallySafe", "L2_CommittedOrReclaimable", "L3_Drains", "L4_CacheConverges"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config")
    ap.add_argument("--design", default="v1")
    ap.add_argument("--bug", default="none")
    ap.add_argument("--safety-only", action="store_true")
    ap.add_argument("--no-i7", action="store_true")
    ap.add_argument("--faults", default=",".join(ALL))
    ap.add_argument("--max-faults", type=int, default=1)
    ap.add_argument("--K", type=int, default=2)
    ap.add_argument("--workers", default="4")
    ap.add_argument("--tag", default="")
    ap.add_argument("--timeout", type=int, default=1500, help="seconds; then TLC is stopped (result incomplete)")
    a = ap.parse_args()

    hold = CONFIGS[a.config]["hold"]
    devs = sorted(hold)
    items = sorted({c for v in hold.values() for c in v})
    faults = [f for f in a.faults.split(",") if f]
    for f in faults:
        assert f in ALL, f
    tag = "-".join(x for x in [a.config, a.design, "K%d" % a.K, "F%d" % a.max_faults,
                                a.tag, None if a.bug == "none" else a.bug,
                                "safety" if a.safety_only else "full"] if x)
    mod = "MC_" + re.sub(r"[^A-Za-z0-9]", "_", tag)
    pairs = ", ".join(f"<<{d}, {c}>>" for d in devs for c in hold[d])
    open(os.path.join(HERE, mod + ".tla"), "w").write("\n".join([
        f"---- MODULE {mod} ----", "EXTENDS Ingest",
        "CONSTANTS " + ", ".join(devs + items),
        "MCDev == {" + ", ".join(devs) + "}",
        "MCItem == {" + ", ".join(items) + "}",
        "MCHold == {" + pairs + "}",
        "MCFaults == {" + ", ".join('"%s"' % f for f in faults) + "}",
        "===="]) + "\n")
    inv = SAFETY + ([] if a.no_i7 else ["I7_NoDanglingRecord"])
    cfg = ["CONSTANTS"] + [f"  {x} = {x}" for x in devs + items] + [
        "  Dev <- MCDev", "  Item <- MCItem", "  Hold <- MCHold", "  Faults <- MCFaults",
        f"  K = {a.K}", f"  MaxFaults = {a.max_faults}", f'  DESIGN = "{a.design}"', f'  BUG = "{a.bug}"',
        "SPECIFICATION Spec", "INVARIANTS " + " ".join(inv)]
    if not a.safety_only:
        cfg += ["INVARIANT SlotsSuffice", "PROPERTIES " + " ".join(LIVE)]
    open(os.path.join(HERE, mod + ".cfg"), "w").write("\n".join(cfg) + "\n")

    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    log = os.path.join(HERE, "results", tag + ".log")
    meta = os.path.join("/dev/shm", "a3s1-tlc-" + tag)
    cmd = ["java", "-XX:+UseParallelGC", "-Xmx4g", "-cp", JAR, "tlc2.TLC", "-workers", a.workers,
           "-deadlock", "-cleanup", "-lncheck", "final", "-metadir", meta, "-config", mod + ".cfg", mod + ".tla"]
    t0 = time.time()
    with open(log, "w") as lf:
        try:
            subprocess.run(cmd, cwd=HERE, stdout=lf, stderr=subprocess.STDOUT, text=True, timeout=a.timeout)
        except subprocess.TimeoutExpired:
            lf.write("\n[run.py] TLC stopped after %d s (timeout); result incomplete\n" % a.timeout)
    dt = time.time() - t0
    subprocess.run(["rm", "-rf", meta])
    out = open(log).read()
    m = re.findall(r"(\d[\d,]*) states generated, (\d[\d,]*) distinct states found", out)
    depth = re.search(r"The depth of the complete state graph search is (\d+)", out)
    errs = re.findall(r"Error: (Invariant \S+ is violated\.|Temporal properties were violated\.|"
                      r".*No space left.*|.*OutOfMemory.*|.*Parsing or semantic analysis failed.*)", out)
    res = dict(tag=tag, config=a.config, hold=hold, design=a.design, bug=a.bug, K=a.K,
               faults=faults, max_faults=a.max_faults, safety_only=a.safety_only, i7=not a.no_i7,
               generated=m[-1][0] if m else None, distinct=m[-1][1] if m else None,
               depth=depth.group(1) if depth else None,
               result=("violation" if errs else
                       "pass" if "Model checking completed. No error has been found." in out else "incomplete"),
               errors=errs, seconds=round(dt, 1), tlc=JAR.split("/")[-1], log=os.path.relpath(log, HERE))
    with open(os.path.join(HERE, "results", "summary.jsonl"), "a") as f:
        f.write(json.dumps(res) + "\n")
    print(json.dumps(res))


if __name__ == "__main__":
    main()
