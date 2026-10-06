#!/usr/bin/env python3
"""
D1-S2 / D1-S1 tabletop harness: an explicit-state model of the Reliquary upload,
claim and ingest protocol, explored exhaustively (BFS) against three attacker
profiles. THROWAWAY research code, not production.

What is real and what is abstract
- Real: dedup IDs are HMAC-SHA256(HKDF-SHA256(family_secret, "reliquary/v1/dedup-key"), content)
  (the construction proposed in docs/research/content-encryption-format.md §6, D-4).
  Receipts and device metadata records are real Ed25519 signatures (python `cryptography`).
- Abstract: age encryption is modelled as "an object that the homelab can decrypt to
  `content`". Anyone holding the homelab *public* key can make one (age has no sender
  authentication; C2SP age spec), so every attacker in this model can create objects.
  R2 is a key -> object map with last-writer-wins PUT (R2 consistency docs), optionally
  create-only (If-None-Match honoured on the presigned PUT: NOT verified on real R2, C1-S1).
  Time is a `tick` action that ages claim TTLs; the homelab may be "offline" for any number
  of ticks because ingest is just an action the scheduler may postpone.

Properties checked (see README for the exact wording)
  S1 never-green-early : an honest device never believes F is safe unless the homelab store
                          holds verified F.  (This is also "no silent loss": once a device
                          believes it is safe it never re-uploads.)
  S2 tag-consistency   : the homelab store never holds content under an ID it does not hash to.
  S3 no-false-blame    : no honest device is ever flagged to the admin.
  SL silent-loss       : an honest device is green, F is not stored, and no honest continuation
                          (attacker stopped) can ever store F.
  L1 recoverable       : (device / URL-leak / honest-fault attackers; cloud honest) from EVERY reachable
                          state, if the attacker stops, the honest actors alone can still reach
                          "both honest devices hold a valid receipt and the store holds F".
                          This is "detection plus automatic re-upload" (PLAN D1-S2 pass).
  V1 visible           : (malicious-cloud attacker) every honest device that is not green is in
                          a user-visible not-safe state; checked as S1 + no state claims green.
"""
import hashlib, hmac, itertools, json, sys, time
from collections import deque
from dataclasses import dataclass, replace, asdict
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.exceptions import InvalidSignature

# ---------------------------------------------------------------- crypto (real)
FAMILY_SECRET = b"\x11" * 32
def _dedup_key(secret):
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=None,
                info=b"reliquary/v1/dedup-key").derive(secret)
DEDUP_KEY = _dedup_key(FAMILY_SECRET)
def dedup_id(content):  # hex, truncated only for readability of traces
    return hmac.new(DEDUP_KEY, content, hashlib.sha256).hexdigest()[:16]
def sha(content):
    return hashlib.sha256(content).hexdigest()[:16]
def header_mac(key, content):
    # stands in for the age header MAC of one specific encryption: unique per object
    return hashlib.sha256(b"hdr|" + key.encode() + b"|" + content).hexdigest()[:12]

def _seed_key(name):
    return Ed25519PrivateKey.from_private_bytes(hashlib.sha256(b"seed|" + name.encode()).digest())
PRIV = {n: _seed_key(n) for n in ["HOMELAB", "H1", "H2", "M", "CLOUD"]}
PUB = {n: k.public_key() for n, k in PRIV.items()}
_sig_cache = {}
def sign(who, msg):
    k = (who, msg)
    if k not in _sig_cache:
        _sig_cache[k] = PRIV[who].sign(msg)
    return _sig_cache[k]
_ver_cache = {}
def verify(pub_name, msg, sig):
    k = (pub_name, msg, sig)
    if k not in _ver_cache:
        try:
            PUB[pub_name].verify(sig, msg); _ver_cache[k] = True
        except InvalidSignature:
            _ver_cache[k] = False
    return _ver_cache[k]

def receipt_msg(dev, did):
    return b"reliquary-commit-v1\n" + json.dumps({"device_id": dev, "dedup_id": did}, sort_keys=True).encode()
def meta_msg(body):
    return b"reliquary-meta-v1\n" + json.dumps(body, sort_keys=True).encode()

F = b"family photo F (the honest content)"
G = b"garbage G chosen by the attacker"
IDF, IDG = dedup_id(F), dedup_id(G)
HONEST = ("H1", "H2")
import os
# HOLDERS=1: only H1 holds F (H2 is enrolled but never has the file). With two holders a loss at
# one device can be masked by the other device's later upload, so the one-holder runs are the
# stricter test of "no silent loss".
HOLDERS = int(os.environ.get("HOLDERS", "2"))

# ---------------------------------------------------------------- configuration
@dataclass(frozen=True)
class Variant:
    name: str
    per_upload_keys: bool     # staging/<id>/<upload> instead of staging/<id>
    create_only: bool         # R2 refuses a PUT onto an existing key (If-None-Match; unverified on R2)
    receipts: bool            # device is green only with a homelab-signed receipt
    pinned_trust: bool        # receipt key pinned from the kit (else learned from the Worker)
    ttl: bool                 # claims expire
    staged_state: bool        # a claim stops expiring once the device reports Complete
    reset_on_reject: bool     # homelab rejection returns the claim to "missing"
    requery: bool             # a device that is not green asks again after a timeout
    attribution: bool         # flag only a device whose own signed record (incl. header MAC) is bad
    homelab_verify: bool      # homelab recomputes HMAC/SHA-256 after decryption (ADR-0001 step 4)
    registry_auth: bool       # device signing keys come from an authenticated channel, not the Worker
    reconcile_missing: bool = False  # a staged claim whose staged object has vanished counts as missing

V1 = Variant("V1-proposed", per_upload_keys=True, create_only=False, receipts=True, pinned_trust=True,
             ttl=True, staged_state=True, reset_on_reject=True, requery=True, attribution=True,
             homelab_verify=True, registry_auth=True, reconcile_missing=True)
# ADR-0001 §4 read literally; every gap filled with the most natural default (README lists them).
V0 = Variant("V0-ADR-0001-literal", per_upload_keys=False, create_only=False, receipts=False,
             pinned_trust=False, ttl=True, staged_state=False, reset_on_reject=False, requery=False,
             attribution=False, homelab_verify=True, registry_auth=False)

def ablations():
    out = [V0, V1, replace(V1, name="V1+create_only", create_only=True)]
    for f in ["per_upload_keys", "receipts", "pinned_trust", "ttl", "staged_state", "reset_on_reject",
              "requery", "attribution", "homelab_verify", "registry_auth", "reconcile_missing"]:
        out.append(replace(V1, name=f"V1-no-{f}", **{f: False}))
    # the per-upload-key question with and without conditional PUT
    out.append(replace(V1, name="V1-no-per_upload_keys+create_only", per_upload_keys=False, create_only=True))
    return out

TTL = 2
MAX_ATTEMPTS = 3

# ---------------------------------------------------------------- state
# claims: tuple of (id, status, owner, n, ttl)   status in {claimed, staged, committed}
# r2: tuple of (key, content|None, meta)          meta = (body_json, signer_claimed, sig) or None
# issued: tuple of (key, device, n, id)           every presigned URL ever issued
# devs: tuple per honest device of (phase, key, n)
# relay: tuple of receipts visible to devices     (dev, id, signer, sig)
# receipts: tuple of homelab-issued receipts       (dev, id, sig)
# store: tuple of (id, content)
# flags: tuple of (device|'-', reason)
# budget: attacker actions left
# m: malicious device's own claim state (key, n) or None
FIELDS = ["claims", "r2", "issued", "devs", "relay", "receipts", "store", "flags", "budget", "m"]

def mk(**kw):
    return tuple(tuple(sorted(set(kw[f]))) if isinstance(kw[f], (list, set, tuple)) and f not in ("devs", "m")
                 else kw[f] for f in FIELDS)
def unpack(s):
    return dict(zip(FIELDS, s))
def pack(d):
    return mk(**d)

def initial(budget):
    return mk(claims=(), r2=(), issued=(), devs=(("idle", None, 0), ("idle" if HOLDERS == 2 else "noF", None, 0)), relay=(),
              receipts=(), store=(), flags=(), budget=budget, m=None)

def claim_of(claims, did):
    for c in claims:
        if c[0] == did:
            return c
    return None
def set_claim(claims, did, new):
    rest = [c for c in claims if c[0] != did]
    if new is not None:
        rest.append(new)
    return tuple(sorted(rest))

def staging_key(v, did, dev, n):
    return f"st/{did[:6]}/{dev}{n}" if v.per_upload_keys else f"st/{did[:6]}"
def key_owner(issued, key):
    """device a per-upload key was issued to (None for dedup keys issued to several)."""
    owners = {i[1] for i in issued if i[0] == key}
    return owners.pop() if len(owners) == 1 else None

def signed_meta(dev, did, content, key, signer=None):
    body = {"device_id": dev, "dedup_id": did,
            "sha256": sha(content) if content is not None else None,
            "header_mac": header_mac(key, content) if content is not None else None}
    bj = json.dumps(body, sort_keys=True)
    s = signer or dev
    return (bj, dev, sign(s, meta_msg(body)))

def r2_put(v, r2, key, content, meta):
    if v.create_only and any(o[0] == key for o in r2):
        return None  # 412 PreconditionFailed
    rest = [o for o in r2 if o[0] != key]
    rest.append((key, content, meta))
    return tuple(sorted(rest, key=lambda o: o[0]))

# ---------------------------------------------------------------- honest Worker
def worker_answer(v, st, dev):
    """ADR-0001 step 1 for one ID. Returns (answer, new_claims, key, n, new_issued)."""
    c = claim_of(st["claims"], IDF)
    di = HONEST.index(dev) if dev in HONEST else None
    n_prev = st["devs"][di][2] if di is not None else (st["m"][1] if st["m"] else 0)
    if c is not None and v.reconcile_missing and c[1] == "staged" and \
            not any(o[0] == staging_key(v, IDF, c[2], c[3]) for o in st["r2"]):
        c = None  # the staged object is gone (lifecycle, auto-abort, operator error, deletion): re-claimable
    if c is None:
        # Upload attempts are bounded to keep the state space finite. Past the bound a device
        # re-uses its last per-upload key (same key, same bytes: an idempotent re-PUT), which
        # stands in for "retries forever with backoff" without growing the state.
        n = min(n_prev + 1, MAX_ATTEMPTS)
        key = staging_key(v, IDF, dev, n)
        claims = set_claim(st["claims"], IDF, (IDF, "claimed", dev, n, TTL if v.ttl else -1))
        issued = tuple(sorted(set(st["issued"]) | {(key, dev, n, IDF)}))
        return ("upload", claims, key, n, issued)
    if c[1] == "committed":
        return ("present", st["claims"], None, n_prev, st["issued"])
    return ("pending", st["claims"], None, n_prev, st["issued"])

def device_green(v, st, i):
    return st["devs"][i][0] == ("protected" if v.receipts else "done")

def valid_receipt_for(v, r, dev=None):
    rdev, rid, signer, sig = r
    trust = "HOMELAB" if v.pinned_trust else signer   # unpinned: device trusts whatever key the Worker says
    if not verify(trust, receipt_msg(rdev, rid), sig):
        return False
    return rid == IDF and (dev is None or rdev == dev)

# ---------------------------------------------------------------- transitions
def successors(v, s, adversary):
    st = unpack(s)
    out = []   # (label, is_attacker, new_state)
    def emit(label, attacker, **chg):
        d = dict(st); d.update(chg); out.append((label, attacker, pack(d)))

    cloud_evil = adversary == "cloud"
    # ---------- honest devices
    for i, dev in enumerate(HONEST):
        phase, key, n = st["devs"][i]
        def setdev(p, k, nn):
            devs = list(st["devs"]); devs[i] = (p, k, nn); return tuple(devs)
        if phase == "idle":
            answers = []
            ans, claims, k2, n2, issued = worker_answer(v, st, dev)
            answers.append((ans, claims, k2, n2, issued, "honest"))
            if cloud_evil:  # the control plane may answer anything
                for lie in ("present", "pending"):
                    if lie != ans:
                        answers.append((lie, st["claims"], None, n, st["issued"], "LIE"))
            for ans, claims, k2, n2, issued, tag in answers:
                lbl = f"{dev}:query->{ans}" + ("" if tag == "honest" else "(cloud lie)")
                if ans == "upload":
                    emit(lbl, tag != "honest", claims=claims, issued=issued, devs=setdev("can_upload", k2, n2))
                elif ans == "pending":
                    emit(lbl, tag != "honest", claims=claims,
                         devs=setdev("waiting" if (v.requery or v.receipts) else "done", None, n2))
                else:  # present
                    emit(lbl, tag != "honest", claims=claims,
                         devs=setdev("present" if v.receipts else "done", None, n2))
        elif phase == "can_upload":
            meta = signed_meta(dev, IDF, F, key)
            r2 = r2_put(v, st["r2"], key, F, meta)
            if r2 is None:
                emit(f"{dev}:PUT {key} refused(412)", False, devs=setdev("idle", None, n))
            else:
                claims = st["claims"]
                c = claim_of(claims, IDF)
                if v.staged_state and c and c[1] == "claimed" and c[2] == dev and c[3] == n:
                    claims = set_claim(claims, IDF, (IDF, "staged", dev, n, -1))
                emit(f"{dev}:PUT {key}+Complete", False, r2=r2, claims=claims,
                     devs=setdev("awaiting" if v.receipts else "done", key, n))
        elif phase == "present":
            # counts only with a valid receipt for this content from ANY device
            if any(valid_receipt_for(v, r) for r in st["relay"]):
                mkey = f"meta/{dev}{n}h"
                r2 = r2_put(v, st["r2"], mkey, None, signed_meta(dev, IDF, None, mkey))
                if r2 is not None:
                    emit(f"{dev}:dedup-hit meta PUT", False, r2=r2, devs=setdev("awaiting", mkey, n))
            if v.requery:
                emit(f"{dev}:timeout->requery", False, devs=setdev("idle", None, n))
        elif phase == "awaiting":
            if any(valid_receipt_for(v, r, dev) for r in st["relay"]):
                emit(f"{dev}:receipt verified -> GREEN", False, devs=setdev("protected", key, n))
            if v.requery:
                emit(f"{dev}:timeout->requery", False, devs=setdev("idle", None, n))
        elif phase == "waiting":
            if v.requery:
                emit(f"{dev}:timeout->requery", False, devs=setdev("idle", None, n))

    # ---------- time
    if v.ttl and any(c[4] > 0 for c in st["claims"]):
        claims = []
        for c in st["claims"]:
            if c[4] > 0:
                if c[4] - 1 == 0:
                    continue  # expired -> missing
                c = (c[0], c[1], c[2], c[3], c[4] - 1)
            claims.append(c)
        emit("tick", False, claims=tuple(sorted(claims)))

    # ---------- homelab ingest (one staged object at a time)
    registered = set(HONEST) | {"M"} | (set() if v.registry_auth else {"CLOUD"})
    for (key, content, meta) in st["r2"]:
        if content is None:  # dedup-hit metadata record
            ok = False
            if meta:
                bj, claimed, sig = meta
                body = json.loads(bj)
                ok = claimed in registered and verify(claimed, meta_msg(body), sig)
            if not ok:
                emit(f"homelab:reject bad meta {key}", False,
                     r2=tuple(o for o in st["r2"] if o[0] != key), flags=tuple(sorted(set(st["flags"]) | {("-", "tamper")})))
            elif any(x[0] == body["dedup_id"] for x in st["store"]):
                rc = (claimed, body["dedup_id"], sign("HOMELAB", receipt_msg(claimed, body["dedup_id"])))
                relay = st["relay"] if cloud_evil else tuple(sorted(set(st["relay"]) | {(rc[0], rc[1], "HOMELAB", rc[2])}))
                emit(f"homelab:dedup-hit receipt {claimed}", False,
                     r2=tuple(o for o in st["r2"] if o[0] != key), receipts=tuple(sorted(set(st["receipts"]) | {rc})),
                     relay=relay)
            continue
        target = key.split("/")[1]
        kid = IDF if IDF.startswith(target) else (IDG if IDG.startswith(target) else None)
        sig_ok, body, signer = False, None, None
        if meta:
            bj, signer, sig = meta
            body = json.loads(bj)
            sig_ok = signer in registered and verify(signer, meta_msg(body), sig) \
                and body["device_id"] == signer
        content_ok = sig_ok and body["dedup_id"] == kid and (
            not v.homelab_verify or (dedup_id(content) == kid and sha(content) == body["sha256"]
                                     and header_mac(key, content) == body["header_mac"]))
        if not v.homelab_verify and sig_ok and body["dedup_id"] == kid:
            content_ok = True
        r2 = tuple(o for o in st["r2"] if o[0] != key)
        claims = st["claims"]
        if content_ok:
            store = st["store"]
            if not any(x[0] == kid for x in store):
                store = tuple(sorted(set(store) | {(kid, content)}))
            rc = (signer, kid, sign("HOMELAB", receipt_msg(signer, kid)))
            claims = set_claim(claims, kid, (kid, "committed", "-", 0, -1))
            relay = st["relay"] if cloud_evil else tuple(sorted(set(st["relay"]) | {(signer, kid, "HOMELAB", rc[2])}))
            emit(f"homelab:commit {key} (signer {signer})", False, r2=r2, store=store, claims=claims,
                 receipts=tuple(sorted(set(st["receipts"]) | {rc})), relay=relay)
        else:
            issuee = key_owner(st["issued"], key)
            if v.attribution:
                if sig_ok and (issuee is None or signer == issuee) and body["header_mac"] == header_mac(key, content):
                    flag = (signer, "signed-bad-content")
                elif sig_ok and issuee is not None and signer != issuee:
                    flag = (signer, "wrote-to-foreign-key")
                else:
                    flag = ("-", "tamper-in-transit")
            else:
                c = claim_of(claims, kid) if kid else None
                who = issuee or (c[2] if c else "-")
                flag = (who, "rejected-upload")
            if v.reset_on_reject and kid:
                c = claim_of(claims, kid)
                if c and c[1] != "committed":
                    owner_n = None
                    for i in st["issued"]:
                        if i[0] == key and v.per_upload_keys:
                            owner_n = (i[1], i[2])
                    if not v.per_upload_keys or owner_n == (c[2], c[3]):
                        claims = set_claim(claims, kid, None)
            emit(f"homelab:REJECT {key} flag={flag}", False, r2=r2, claims=claims,
                 flags=tuple(sorted(set(st["flags"]) | {flag})))

    # ---------- attackers (budget-limited)
    if st["budget"] > 0:
        b = st["budget"] - 1
        if adversary == "device":
            # M is an enrolled device holding the family secret and its own signing key.
            # m = None | (key, n, spent)
            m = st["m"]
            if m is None or m[2]:
                ans, claims, k2, n2, issued = worker_answer(v, st, "M")
                if ans == "upload":
                    emit("M:claim IDF", True, claims=claims, issued=issued, m=(k2, n2, False), budget=b)
            else:
                k2, n2, _ = m
                # duplicate faking: M's own signed record says IDF, the object is G
                r2 = r2_put(v, st["r2"], k2, G, signed_meta("M", IDF, G, k2))
                if r2 is not None:
                    emit(f"M:PUT poison G as IDF at {k2}", True, r2=r2, m=(k2, n2, True), budget=b)
        elif adversary == "fault":
            # an otherwise honest cloud loses a staged object (lifecycle rule, 7-day multipart
            # auto-abort, operator error, backend bug): the Duplicacy "missing chunks" class
            for (key, content, meta) in st["r2"]:
                emit(f"FAULT:staged object vanishes {key}", True,
                     r2=tuple(o for o in st["r2"] if o[0] != key), budget=b)
        elif adversary == "leak":
            # someone holding a leaked (reusable, up to 7 d) presigned PUT URL of an honest device
            for (key, dev, n, did) in st["issued"]:
                if dev in HONEST:
                    # replace content, replaying the honest device's encrypted metadata blob if staged
                    cur = [o for o in st["r2"] if o[0] == key]
                    meta = cur[0][2] if cur else None
                    r2 = r2_put(v, st["r2"], key, G, meta)
                    if r2 is not None and r2 != st["r2"]:
                        emit(f"LEAK:PUT G over {key}", True, r2=r2, budget=b)
        elif adversary == "cloud":
            for (key, content, meta) in st["r2"]:
                emit(f"CLOUD:delete {key}", True, r2=tuple(o for o in st["r2"] if o[0] != key), budget=b)
                if content is not None and content != G:
                    emit(f"CLOUD:swap content at {key}", True,
                         r2=tuple(sorted([o for o in st["r2"] if o[0] != key] + [(key, G, meta)])), budget=b)
            # inject an object signed by a key the cloud controls
            for did, content in ((IDF, G), (IDG, G)):
                key = f"st/{did[:6]}/CLOUD"
                if not any(o[0] == key for o in st["r2"]):
                    meta = signed_meta("CLOUD", did, content, key)
                    emit(f"CLOUD:inject G as {did[:6]}", True,
                         r2=tuple(sorted(list(st["r2"]) + [(key, content, meta)])), budget=b)
            # relay receipts: genuine ones to anyone, or forged ones signed with the cloud's key
            cands = [(r[0], r[1], "HOMELAB", r[2]) for r in st["receipts"]]
            cands += [(d, IDF, "CLOUD", sign("CLOUD", receipt_msg(d, IDF))) for d in HONEST]
            for rc in cands:
                if rc not in st["relay"]:
                    emit(f"CLOUD:relay receipt {rc[0]}/{rc[1][:6]} signed {rc[2]}", True,
                         relay=tuple(sorted(set(st["relay"]) | {rc})), budget=b)
    return out

# ---------------------------------------------------------------- properties
def s1_violation(v, st):
    have = any(x == (IDF, F) for x in st["store"])
    return [HONEST[i] for i in range(2) if device_green(v, st, i) and not have]
def s2_violation(st):
    return [x for x in st["store"] if dedup_id(x[1]) != x[0]]
def s3_violation(st):
    return [f for f in st["flags"] if f[0] in HONEST]
def good(v, st):
    return all(st["devs"][i][0] in ("noF", "protected" if v.receipts else "done") for i in range(2)) and \
        any(x == (IDF, F) for x in st["store"])

def explore(v, adversary, budget, max_states=2_000_000):
    s0 = initial(budget)
    parent = {s0: None}
    edges = {}  # s -> list of (label, attacker, t)
    q = deque([s0])
    while q:
        s = q.popleft()
        succ = successors(v, s, adversary)
        edges[s] = succ
        for (lbl, att, t) in succ:
            if t not in parent:
                parent[t] = (s, lbl)
                q.append(t)
                if len(parent) > max_states:
                    raise RuntimeError("state bound exceeded")
    return s0, parent, edges

def trace(parent, s):
    out = []
    while parent[s] is not None:
        p, lbl = parent[s]; out.append(lbl); s = p
    return list(reversed(out))

def _backward(parent, edges, targets):
    rev = {}
    for s, succ in edges.items():
        for (lbl, att, t) in succ:
            if not att:
                rev.setdefault(t, []).append(s)
    can = set(targets); q = deque(targets)
    while q:
        t = q.popleft()
        for p in rev.get(t, []):
            if p not in can:
                can.add(p); q.append(p)
    return can

def check(v, adversary, budget):
    t0 = time.time()
    s0, parent, edges = explore(v, adversary, budget)
    res = {"variant": v.name, "adversary": adversary, "budget": budget, "states": len(parent)}
    cex = {}
    # states from which honest actors alone (attacker stopped) can still get verified F into the store
    can_store = _backward(parent, edges, [s for s in parent if any(x == (IDF, F) for x in unpack(s)["store"])])
    for s in parent:  # BFS insertion order => first hit has a shortest trace
        st = unpack(s)
        if "S1" not in cex and s1_violation(v, st):
            cex["S1"] = trace(parent, s) + [f"=> {s1_violation(v, st)} green but the homelab store lacks F"]
        if "SL" not in cex and s1_violation(v, st) and s not in can_store:
            cex["SL"] = trace(parent, s) + [f"=> SILENT LOSS: {s1_violation(v, st)} green, store lacks F, and no honest continuation can ever store F"]
        if "S2" not in cex and s2_violation(st):
            cex["S2"] = trace(parent, s) + ["=> store holds content under an ID it does not hash to"]
        if "S3" not in cex and s3_violation(st):
            cex["S3"] = trace(parent, s) + [f"=> honest device flagged {s3_violation(st)}"]
    if adversary in ("device", "leak", "fault", "none"):
        can = _backward(parent, edges, [s for s in parent if good(v, unpack(s))])
        s = next((x for x in parent if x not in can), None)
        if s is not None:
            st = unpack(s)
            cex["L1"] = trace(parent, s) + [f"=> attacker stops here; honest actors can no longer reach all-green. devs={st['devs']} claims={[c[:3] for c in st['claims']]} store={[x[0][:6] for x in st['store']]}"]
        res["L1_checked"] = True
    else:
        res["L1_checked"] = False
    res["violations"] = [k for k in ("S1", "SL", "S2", "S3", "L1") if k in cex]
    res["counterexamples"] = cex
    res["flags_seen"] = sorted({f for s in parent for f in unpack(s)["flags"]})
    res["seconds"] = round(time.time() - t0, 2)
    return res

def main():
    budget = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    only = set(sys.argv[2].split(",")) if len(sys.argv) > 2 else None
    advs = sys.argv[3].split(",") if len(sys.argv) > 3 else ["none", "device", "leak", "fault", "cloud"]
    results = []
    for v in ablations():
        if only and v.name not in only:
            continue
        for adv in advs:
            r = check(v, adv, 0 if adv == "none" else budget)
            results.append(r)
            print(f"{v.name:38s} {adv:7s} states={r['states']:7d} violations={','.join(r['violations']) or '-':10s} ({r['seconds']}s)", flush=True)
    json.dump({"budget": budget, "holders": HOLDERS, "ttl": TTL, "max_attempts": MAX_ATTEMPTS,
               "dedup_id_F": IDF, "dedup_id_G": IDG,
               "variants": [asdict(v) for v in ablations()], "results": results},
              open(f"results-b{budget}{'-subset' if only else ''}{'-1holder' if HOLDERS == 1 else ''}.json", "w"), indent=1)

if __name__ == "__main__":
    main()
