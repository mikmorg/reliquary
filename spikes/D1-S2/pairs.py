"""Extra one-holder checks: pairwise ablations and the junk-injection measure (not a property in model.py)."""
import os, json
os.environ.setdefault("HOLDERS", "1")
import model as m
from dataclasses import replace
out = []
pairs = [("reset_on_reject", "reconcile_missing"), ("ttl", "reconcile_missing"),
         ("staged_state", "per_upload_keys"), ("per_upload_keys", "attribution"), ("ttl", "reset_on_reject")]
for a, b in pairs:
    v = replace(m.V1, name=f"V1-no-{a}-no-{b}", **{a: False, b: False})
    for adv in ("device", "leak", "fault", "cloud"):
        r = m.check(v, adv, 2)
        out.append(r)
        print(f"{v.name:44s} {adv:7s} states={r['states']:7d} violations={','.join(r['violations']) or '-'}")
# junk injection: can a CLOUD-signed object ever be committed?
for v in (m.V1, replace(m.V1, name="V1-no-registry_auth", registry_auth=False)):
    s0, parent, edges = m.explore(v, "cloud", 2)
    junk = sum(1 for s in parent if any(x[0] == m.IDG for x in m.unpack(s)["store"]))
    print(f"{v.name:44s} cloud   states={len(parent):7d} states-with-cloud-junk-committed={junk}")
    out.append({"variant": v.name, "adversary": "cloud", "budget": 2, "junk_states": junk, "states": len(parent)})
json.dump(out, open("pairs-1holder-b2.json", "w"), indent=1, default=str)
