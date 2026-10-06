"""F3-S2 dedup-oracle simulation (SYN -> results). Emulated protocol logic, not Cloudflare.

A compromised device (holds the family dedup secret and its own valid credential)
probes 10,000 candidate files against the presence endpoint. We simulate, hour by hour,
four server configurations and four attacker strategies, and the same detectors against
synthetic legitimate device profiles (false-positive check).

Every threshold below is a PARAMETER of this simulation, not a proposal measured
anywhere; values derived from budgets say so. Output: results.json + printed tables.
"""
import json, math, itertools
import numpy as np

HOUR = 1
DAYS = 400                     # simulation horizon
N_PROBE = 10_000               # PLAN F3-S2
# ---- values derived from repo budgets / F3-S1 (see README) ----
BUD_HASH_BYTES_6H = 128e9      # BUD-HASH: 128 GB first pass in one 6 h window
MEAN_FILE = 2_229_987          # F3-S1: Open Images mean OriginalSize after content dedup
SEED_FILES = int(BUD_HASH_BYTES_6H / MEAN_FILE)          # ~57k lookups in 6 h
SEED_RATE_PER_H = math.ceil(SEED_FILES / 6)               # per-device limit that does not slow BUD-HASH
STRICT_RATE_PER_DAY = N_PROBE // 30                       # the only flat cap that makes 10k probes take 30 d
BATCH = 1000                   # SR-21 "answer only for IDs in the current batch" (parameter)

rng = np.random.default_rng(20260929)

# ------------------------------------------------------------------ detectors
class Accounting:
    """Exact per-device counters, as a Durable Object would keep them (C13).
    orphan = an ID answered 'missing' whose upload never starts within T_ORPHAN hours."""
    def __init__(self, theta_orphan_day, theta_orphan_total, theta_samesize, t_orphan_h=24, claim_cap=None):
        self.claim_cap = claim_cap
        self.th_day, self.th_total, self.th_ss, self.t_orph = theta_orphan_day, theta_orphan_total, theta_samesize, t_orphan_h
        self.pending = []      # (deadline_hour, count)
        self.orphans_by_hour = {}
        self.total_orphans = 0
        self.samesize_24h = []  # (hour, max same-size cluster of new objects that hour)
        self.alert = None
    def missing_answered(self, h, n_missing, n_uploaded_later):
        orph = n_missing - n_uploaded_later
        if orph > 0:
            self.pending.append((h + self.t_orph, orph))
    def new_objects_same_size(self, h, cluster):
        self.samesize_24h.append((h, cluster))
    def outstanding(self):
        return sum(c for (_, c) in self.pending)
    def tick(self, h):
        due = [c for (d, c) in self.pending if d <= h]
        self.pending = [(d, c) for (d, c) in self.pending if d > h]
        if due:
            self.orphans_by_hour[h] = self.orphans_by_hour.get(h, 0) + sum(due)
            self.total_orphans += sum(due)
        day = sum(v for k, v in self.orphans_by_hour.items() if k > h - 24)
        if self.alert is None:
            if self.th_day is not None and day > self.th_day:
                self.alert = (h, 'orphans_24h')
            elif self.th_total is not None and self.total_orphans > self.th_total:
                self.alert = (h, 'orphans_cumulative')
            elif self.th_ss is not None and sum(c for (t, c) in self.samesize_24h if t > h - 24) > self.th_ss:
                self.alert = (h, 'same_size_new_objects_24h')

# ------------------------------------------------------------------ configurations
CONFIGS = {
    # name: (rate limit per hour, per-day cap, record_first+accounting, per_person_scope, receipt_timing_leak)
    'C0 ADR-0001 as written (global, no limit)':        dict(rate_h=None, cap_day=None, acct=False, scope=False, leak=False),
    'C1 global + SR-21 rate limit sized for BUD-HASH':   dict(rate_h=SEED_RATE_PER_H, cap_day=None, acct=False, scope=False, leak=False),
    'C1s global + strict cap (333/day)':                 dict(rate_h=None, cap_day=STRICT_RATE_PER_DAY, acct=False, scope=False, leak=False),
    'C2 C1 + record-first + DO accounting':              dict(rate_h=SEED_RATE_PER_H, cap_day=None, acct=True, scope=False, leak=False),
    'C3 C2 + per-person scope (file < T_x)':             dict(rate_h=SEED_RATE_PER_H, cap_day=None, acct=True, scope=True, leak=False),
    'C3L C3 but receipt latency reveals prior presence': dict(rate_h=SEED_RATE_PER_H, cap_day=None, acct=True, scope=True, leak=True),
}
# detector parameters (swept)
DETECTORS = {
    'D-a orphans/24h > 300 (claim TTL 24 h)':         dict(theta_orphan_day=300, theta_orphan_total=None, theta_samesize=None),
    'D-b cumulative orphans > 1000 (claim TTL 24 h)': dict(theta_orphan_day=None, theta_orphan_total=1000, theta_samesize=None),
    'D-b1 D-b + claim TTL 1 h + <=1000 open claims':  dict(theta_orphan_day=None, theta_orphan_total=1000, theta_samesize=None,
                                                           t_orphan_h=1, claim_cap=1000),
    'D-c D-a + D-b + same-size new objects/24h > 50': dict(theta_orphan_day=300, theta_orphan_total=1000, theta_samesize=50),
}
# attacker strategies
STRATS = {
    'S1 burst, abandon misses':           dict(pace='max', upload_misses=False),
    'S2 drip under 24h orphan threshold': dict(pace='drip', upload_misses=False),
    'S3 burst, upload every miss (mimic)': dict(pace='max', upload_misses=True),
    'S4 drip, upload every miss (mimic)': dict(pace='drip', upload_misses=True),
    'S5 burst, mimic, candidate sizes all differ': dict(pace='max', upload_misses=True, varied_sizes=True),
}

def run_attack(cfg, det, strat, cross_person=True, cand_size_bytes=200_000, same_size=True, n_probe=N_PROBE):
    """Learn-the-remaining-information on one victim document: 10k candidates, 1 present
    (placed uniformly at random).  Returns time to finish, alert time, answers learned."""
    acct = Accounting(**det) if cfg['acct'] else None
    target = int(rng.integers(n_probe))
    sent = 0; learned_true = None; h = 0; finished = None
    # per-person scope answers 'missing' for other persons' files below T_x; with the receipt-timing
    # leak (C3L) an attacker that uploads its candidates still tells the present one apart
    oracle_blind = cfg['scope'] and cross_person and not (cfg['leak'] and strat['upload_misses'])
    same_size = same_size and not strat.get('varied_sizes', False)
    drip_per_day = 280  # stays under D-a's 300/day
    per_day_sent = {}
    while h < DAYS * 24 and sent < n_probe:
        if acct and acct.alert:           # auto-suspend on alert (BUD-REVOKE: < 60 s, i.e. same hour)
            break
        budget = n_probe - sent
        if acct and acct.claim_cap and not strat['upload_misses']:
            budget = min(budget, max(0, acct.claim_cap - acct.outstanding()))
        if cfg['rate_h'] is not None: budget = min(budget, cfg['rate_h'])
        if cfg['cap_day'] is not None:
            used = per_day_sent.get(h // 24, 0); budget = min(budget, cfg['cap_day'] - used)
        if strat['pace'] == 'drip':
            used = per_day_sent.get(h // 24, 0); budget = min(budget, max(0, drip_per_day - used))
        budget = max(0, budget)
        # send in batches of BATCH within the hour
        n = budget
        if n:
            lo, hi = sent, sent + n
            hit = lo <= target < hi
            n_missing = n - (1 if hit else 0)
            if cfg['scope'] and cross_person:
                n_missing = n            # cross-person below T_x: always "missing"
            uploaded = n_missing if strat['upload_misses'] else 0
            if acct:
                acct.missing_answered(h, n_missing, uploaded)
                if strat['upload_misses'] and same_size:
                    acct.new_objects_same_size(h, uploaded)
            if hit and not oracle_blind:
                learned_true = h   # C0-C2: 'present' answer; C3L: faster receipt for the target
            sent += n
            per_day_sent[h // 24] = per_day_sent.get(h // 24, 0) + n
        if acct: acct.tick(h)
        h += 1
    if sent >= n_probe and finished is None:
        finished = h
    # let the orphan timers run out after the last probe
    if acct and not acct.alert:
        for hh in range(h, h + 48): acct.tick(hh)
    p_learn = 0.0 if oracle_blind else min(1.0, sent / n_probe)
    return dict(finished_h=finished, probes_answered=sent, p_learn=round(p_learn, 3),
                alert=(acct.alert if acct else None),
                learned_target=learned_true is not None and (not acct or not acct.alert or learned_true <= acct.alert[0]),
                oracle_blind=oracle_blind,
                attacker_upload_GB=round((sent - 1) * cand_size_bytes / 1e9, 2) if strat['upload_misses'] else 0.0)

def verdict(r):
    days = (r['finished_h'] / 24) if r['finished_h'] is not None else None
    if r['alert']: return 'PASS (alert)'
    if r['oracle_blind']: return 'PASS (oracle gives no information)'
    if days is None or days > 30: return 'PASS (>30 d)'
    return 'FAIL'

# ------------------------------------------------------------------ legitimate profiles (false positives)
def legit_profile(name, lookups, hours, p_orphan, p_upload_hit, samesize_max):
    return dict(name=name, lookups=lookups, hours=hours, p_orphan=p_orphan, p_hit=p_upload_hit, ss=samesize_max)

def run_legit(cfg, det, prof):
    acct = Accounting(**det)
    per_h = math.ceil(prof['lookups'] / prof['hours'])
    if cfg['rate_h'] is not None: per_h = min(per_h, cfg['rate_h'])
    sent = 0; h = 0; day_used = {}
    while sent < prof['lookups'] and h < DAYS * 24:
        n = min(per_h, prof['lookups'] - sent)
        if cfg['cap_day'] is not None: n = min(n, cfg['cap_day'] - day_used.get(h // 24, 0))
        if acct.claim_cap: n = min(n, max(0, acct.claim_cap - acct.outstanding()))
        day_used[h // 24] = day_used.get(h // 24, 0) + n
        miss = int(round(n * (1 - prof['p_hit'])))
        orph = int(rng.binomial(miss, prof['p_orphan']))
        acct.missing_answered(h, miss, miss - orph)
        acct.new_objects_same_size(h, prof['ss'] if h % 24 == 0 else 0)
        acct.tick(h); sent += n; h += 1
    for hh in range(h, h + 48): acct.tick(hh)
    return dict(hours_to_finish_lookups=h, alert=acct.alert)

def main():
    res = {'derived': dict(SEED_FILES=SEED_FILES, SEED_RATE_PER_H=SEED_RATE_PER_H,
                           STRICT_RATE_PER_DAY=STRICT_RATE_PER_DAY, BATCH=BATCH),
           'attack': [], 'legit': []}
    for (cn, cfg), (sn, st) in itertools.product(CONFIGS.items(), STRATS.items()):
        dets = DETECTORS.items() if cfg['acct'] else [('none', None)]
        for dn, det in dets:
            for cross in (True, False):
                if not cfg['scope'] and not cross: continue
                for scen, n_probe in (('learn-remaining 10k', N_PROBE), ('confirm-file 20', 20)):
                    r = run_attack(cfg, det or {}, st, cross_person=cross, n_probe=n_probe)
                    r.update(config=cn, strategy=sn, detector=dn, cross_person=cross, scenario=scen, verdict=verdict(r))
                    res['attack'].append(r)
    # legitimate profiles. SAME-SIZE maxima: measured from F3-S1 public samples (see README)
    ss = json.load(open('legit_samesize.json'))
    profiles = []
    for p_orph in (0.0, 0.001, 0.01):
        for p_hit in (0.05, 0.2):
            profiles.append(legit_profile(f'L1 phone first seed {SEED_FILES} files/6h, p_orphan={p_orph}, hit={p_hit}',
                                          SEED_FILES, 6, p_orph, p_hit, ss['photo_57k_max_cluster']))
    profiles.append(legit_profile('L2 steady state 50 files/day, p_orphan=0.01', 50, 24, 0.01, 0.05, 1))
    profiles.append(legit_profile('L3 reinstall re-query 57k files, all own hits', SEED_FILES, 6, 0.0, 1.0, 0))
    profiles.append(legit_profile('L4 desktop 500k docs over 48 h, p_orphan=0.001', 500_000, 48, 0.001, 0.05,
                                  ss['doc_500k_max_cluster_per_24h']))
    for cn in ('C1 global + SR-21 rate limit sized for BUD-HASH', 'C1s global + strict cap (333/day)',
               'C2 C1 + record-first + DO accounting'):
        cfg = CONFIGS[cn]
        for dn, det in DETECTORS.items():
            for prof in profiles:
                r = run_legit(cfg, det, prof); r.update(config=cn, detector=dn, profile=prof['name'])
                res['legit'].append(r)
    print('derived', res['derived'])
    # worst case over attacker strategies, per (config, detector, cross, scenario)
    worst = {}
    for r in res['attack']:
        k = (r['config'], r['detector'], r['cross_person'], r['scenario'])
        w = worst.setdefault(k, dict(plan_verdict='PASS', learned_by_best_strategy=False, fastest_days=None, strategies_failing=[], max_p_learn=0.0))
        w['max_p_learn'] = max(w['max_p_learn'], r['p_learn'])
        if r['verdict'] == 'FAIL':
            w['plan_verdict'] = 'FAIL'; w['strategies_failing'].append(r['strategy'][:2])
        w['learned_by_best_strategy'] |= bool(r['learned_target'])
        if r['learned_target'] and r['finished_h'] is not None:
            d = r['finished_h'] / 24
            w['fastest_days'] = d if w['fastest_days'] is None else min(w['fastest_days'], d)
    res['worst_case'] = [dict(config=k[0], detector=k[1], cross_person=k[2], scenario=k[3], **v) for k, v in worst.items()]
    print('\nWORST CASE OVER STRATEGIES (PLAN rule: pass if >30 d or alert)')
    for w in res['worst_case']:
        fd = f"{w['fastest_days']:.2f}" if w['fastest_days'] is not None else '-'
        print(f"{w['config'][:4]:5} {w['detector'][:5]:6} cross={int(w['cross_person'])} {w['scenario']:20} | PLAN {w['plan_verdict']:4} {','.join(w['strategies_failing']):12} | max P(learn) {w['max_p_learn']:.2f} | fastest full run {fd} d")
    print('\nATTACK detail')
    for r in res['attack']:
        d = f"{r['finished_h']/24:.2f} d" if r['finished_h'] is not None else 'not finished'
        a = f"alert@{r['alert'][0]}h {r['alert'][1]} after {r['probes_answered']} probes" if r['alert'] else 'no alert'
        print(f"{r['config'][:4]:5} {r['strategy'][:3]} {r['detector'][:5]:6} cross={int(r['cross_person'])} {r['scenario'][:7]} | {d:13} | {a:62} | learned={int(r['learned_target'])} | up={r['attacker_upload_GB']}GB | {r['verdict']}")
    print('\nLEGIT (false positives)')
    for r in res['legit']:
        a = f"ALERT@{r['alert'][0]}h {r['alert'][1]}" if r['alert'] else 'no alert'
        print(f"{r['config'][:4]:5} {r['detector'][:5]:6} {r['profile'][:70]:70} | lookups done in {r['hours_to_finish_lookups']/24:.2f} d | {a}")

    json.dump(res, open('results.json', 'w'), indent=1)

if __name__ == '__main__':
    main()
