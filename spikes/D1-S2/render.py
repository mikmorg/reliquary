#!/usr/bin/env python3
"""Render results-b*.json into a Markdown matrix and a counterexample listing."""
import json, sys
paths = sys.argv[1:]
rows = []
for p in paths:
    d = json.load(open(p))
    for r in d["results"]:
        rows.append(r)
advs = ["none", "device", "leak", "fault", "cloud"]
variants = []
for r in rows:
    if r["variant"] not in variants:
        variants.append(r["variant"])
cell = {}
for r in rows:
    v = ",".join(r["violations"]) or "pass"
    cell[(r["variant"], r["adversary"], r["budget"])] = (v, r["states"])
budgets = sorted({r["budget"] for r in rows if r["adversary"] != "none"})
print("| Variant | " + " | ".join(f"{a} (b={b})" if a != "none" else "none" for a in advs for b in (budgets if a != "none" else [0])) + " |")
print("|---|" + "---|" * sum(len(budgets) if a != "none" else 1 for a in advs))
for v in variants:
    cells = []
    for a in advs:
        for b in (budgets if a != "none" else [0]):
            c = cell.get((v, a, b))
            cells.append(f"{c[0]} ({c[1]:,})" if c else "–")
    print(f"| {v} | " + " | ".join(cells) + " |")
print()
print("## Counterexamples (shortest, BFS)\n")
for r in rows:
    for k, tr in r["counterexamples"].items():
        print(f"### {r['variant']} / {r['adversary']} (budget {r['budget']}): {k}\n")
        print("```")
        print("\n".join(tr))
        print("```\n")
