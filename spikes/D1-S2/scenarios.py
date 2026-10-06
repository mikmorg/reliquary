#!/usr/bin/env python3
"""Named tabletop scenarios replayed step by step through model.py (same transition relation
the exhaustive checker explores). Each step names the label prefix of the transition to take;
the run fails loudly if that transition is not enabled in the current state."""
import json, sys
import model as m

def replay(v, adversary, budget, steps):
    s = m.initial(budget)
    log = []
    for want in steps:
        succ = m.successors(v, s, adversary)
        pick = [x for x in succ if x[0].startswith(want)]
        if not pick:
            log.append(f"!! step '{want}' NOT ENABLED; enabled: {[x[0] for x in succ]}")
            return s, log, False
        lbl, att, s = pick[0]
        log.append(lbl)
    return s, log, True

def summary(v, s):
    st = m.unpack(s)
    return {"devices": {m.HONEST[i]: st["devs"][i][0] for i in range(2)},
            "store_has_F": any(x == (m.IDF, m.F) for x in st["store"]),
            "claims": [(c[1], c[2]) for c in st["claims"]],
            "flags": [list(f) for f in st["flags"]],
            "S1_green_without_F": m.s1_violation(v, st)}

INGEST = "homelab:"
SCEN = [
  ("SC-1 dedup poisoning (duplicate faking) by an enrolled device", "device", 2, [
      "M:claim", "M:PUT poison", "H1:query->pending", "H2:query->pending",
      INGEST, "H1:timeout->requery", "H1:query->upload", "H1:PUT", INGEST, "H1:receipt",
      "H2:timeout->requery", "H2:query->present", "H2:dedup-hit", INGEST, "H2:receipt"],
   {"V0": ["M:claim", "M:PUT poison", "H1:query->pending", "H2:query->pending", INGEST]}),
  ("SC-2 claim squatting (claim, never upload)", "device", 1, [
      "M:claim", "H1:query->pending", "tick", "tick", "H1:timeout->requery", "H1:query->upload",
      "H1:PUT", INGEST, "H1:receipt"],
   {"V0": ["M:claim", "H1:query->pending", "H2:query->pending", "tick", "tick"]}),
  ("SC-3 overwrite of a staged object after the claim TTL lapses (homelab offline)", "device", 2, [
      "H1:query->upload", "H1:PUT", "H2:query->pending"],
   {"V1-no-staged_state": ["H1:query->upload", "H1:PUT", "tick", "tick", "M:claim", "M:PUT poison",
                           "H2:query->pending", "homelab:REJECT", "homelab:commit", "H1:receipt"],
    "V0": ["H1:query->upload", "H1:PUT", "tick", "tick", "M:claim", "M:PUT poison", "H2:query->pending", INGEST]}),
  ("SC-4 leaked presigned PUT URL reused to overwrite", "leak", 1, [
      "H1:query->upload", "H1:PUT", "LEAK:PUT G", INGEST, "H1:timeout->requery", "H1:query->upload",
      "H1:PUT", INGEST, "H1:receipt"],
   {"V0": ["H1:query->upload", "H1:PUT", "H2:query->pending", "LEAK:PUT G", INGEST]}),
  ("SC-5 malicious cloud says 'already have it'", "cloud", 0, [
      "H1:query->present(cloud lie)", "H1:timeout->requery"],
   {"V0": ["H1:query->present(cloud lie)"]}),
  ("SC-6 malicious cloud forges a receipt", "cloud", 1, [
      "H1:query->upload", "H1:PUT", "CLOUD:relay receipt H1/", ],
   {"V1-no-pinned_trust": ["H1:query->upload", "H1:PUT", "CLOUD:relay receipt H1/", "H1:receipt"]}),
  ("SC-8 honest-cloud fault: a staged object vanishes before the homelab pulls it", "fault", 1, [
      "H1:query->upload", "H1:PUT", "FAULT:", "H1:timeout->requery", "H1:query->upload", "H1:PUT",
      INGEST, "H1:receipt"],
   {"V1-no-reconcile_missing": ["H1:query->upload", "H1:PUT", "FAULT:", "H1:timeout->requery",
                                "H1:query->pending", "H1:timeout->requery", "H1:query->pending"]}),
  ("SC-7 malicious cloud deletes the staged object before the homelab pulls it", "cloud", 1, [
      "H1:query->upload", "H1:PUT", "CLOUD:delete", "H1:timeout->requery"],
   {"V0": ["H1:query->upload", "H1:PUT", "CLOUD:delete"]}),
]

def main():
    variants = {v.name: v for v in m.ablations()}
    out = []
    for name, adv, budget, v1steps, others in SCEN:
        runs = [("V1-proposed", v1steps)] + [(k if k in variants else next(n for n in variants if n.startswith(k)), st)
                                            for k, st in others.items()]
        for vname, steps in runs:
            v = variants[vname]
            s, log, ok = replay(v, adv, budget, steps)
            res = {"scenario": name, "variant": vname, "adversary": adv, "replayed": ok, "trace": log,
                   "end": summary(v, s)}
            out.append(res)
            print(f"\n## {name}  [{vname}]  replayed={ok}")
            for l in log: print("   ", l)
            print("   END:", json.dumps(res["end"]))
    json.dump(out, open("scenarios.json", "w"), indent=1)
    if not all(r["replayed"] for r in out):
        sys.exit(1)

if __name__ == "__main__":
    main()
