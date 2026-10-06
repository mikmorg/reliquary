#!/usr/bin/env python3
"""Run one command (stdin/stdout/stderr inherited) and append one JSON line to
RESULTS_FILE: label, exit code, wall seconds, peak RSS of the command and its
children, CPU seconds. Portable stand-in for GNU `time -v`.

usage: measure.py RESULTS_FILE LABEL [k=v ...] -- CMD ARGS...
Extra k=v pairs are copied into the JSON line (numbers stay numbers).
"""
import json, resource, subprocess, sys, time

out, label = sys.argv[1], sys.argv[2]
sep = sys.argv.index("--")
extra = {}
for kv in sys.argv[3:sep]:
    k, v = kv.split("=", 1)
    try:
        extra[k] = json.loads(v)
    except ValueError:
        extra[k] = v
cmd = sys.argv[sep + 1:]
t0 = time.monotonic()
p = subprocess.run(cmd)
wall = time.monotonic() - t0
ru = resource.getrusage(resource.RUSAGE_CHILDREN)
row = {"label": label, "rc": p.returncode, "wall_s": round(wall, 3),
       "peak_rss_mb": round(ru.ru_maxrss / 1024, 1),  # Linux reports KiB
       "user_s": round(ru.ru_utime, 2), "sys_s": round(ru.ru_stime, 2), **extra}
with open(out, "a") as f:
    f.write(json.dumps(row) + "\n")
sys.exit(p.returncode)
