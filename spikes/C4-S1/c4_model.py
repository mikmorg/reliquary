#!/usr/bin/env python3
"""C4-S1: Reliquary cost, capacity and storage-budget model, v0.

THROWAWAY SPIKE CODE (research phase). Python 3 standard library only.

Every unit price below was read from a primary source on 2026-09-29 (see PRICES[*].src).
Every volume parameter is an ASSUMPTION ("A") or an OWNER INPUT ("O") until A0, E1, H2 and
C5 replace it. The model never invents measurements: it computes consequences of the
stated parameters and says which ones are unmeasured.

Usage:
    python3 c4_model.py              # writes CSVs into ./out and prints a summary
    python3 c4_model.py --out DIR

Outputs (CSV): prices.csv, params.csv, scenarios.csv, sensitivity.csv, abuse_vectors.csv,
abuse_bound.csv, capacity.csv, isp.csv, fixed_costs.csv, checks.csv
"""
import argparse
import csv
import datetime as dt
import itertools
import math
import os

GB = 1e9          # R2 limits page: "1 GB (gigabyte), which is 10^9 bytes"
TB = 1e12
MiB = 1 << 20
M = 1e6

CF = "https://raw.githubusercontent.com/cloudflare/cloudflare-docs/production/src/content/"
SRC_R2 = CF + "docs/r2/pricing.mdx"
SRC_R2LIM = CF + "docs/r2/platform/limits.mdx"
SRC_WK = CF + "docs/workers/platform/pricing.mdx"
SRC_D1 = CF + "partials/workers/d1-pricing.mdx"
SRC_Q = CF + "partials/workers/queues_pricing.mdx"
SRC_DO = CF + "partials/durable-objects/durable-objects-pricing.mdx"
SRC_EM = CF + "docs/email-service/platform/pricing.mdx"
SRC_AZ = ("https://raw.githubusercontent.com/MicrosoftDocs/azure-docs/main/articles/"
          "artifact-signing/how-to-change-sku.md")
SRC_APPLE = "https://developer.apple.com/programs/"
SRC_ANDROID = "https://developer.android.com/developer-verification/guides/faq"
SRC_PVE = "https://raw.githubusercontent.com/proxmox/pve-docs/master/local-zfs.adoc"
SRC_BB = "https://www.backblaze.com/blog/backblaze-drive-stats-for-q1-2026/ (search snippet only)"
ACCESSED = "2026-09-29"

# ---------------------------------------------------------------------------------------
# Unit prices (primary, accessed 2026-09-29). (value, unit, source)
# ---------------------------------------------------------------------------------------
PRICES = {
    "workers_paid_base":      (5.00,   "USD/month/account", SRC_WK),
    "workers_req_incl":       (10e6,   "requests/month", SRC_WK),
    "workers_req_rate":       (0.30,   "USD per 1M requests", SRC_WK),
    "workers_cpu_incl":       (30e6,   "CPU-ms/month", SRC_WK),
    "workers_cpu_rate":       (0.02,   "USD per 1M CPU-ms", SRC_WK),
    "r2_std_storage":         (0.015,  "USD/GB-month", SRC_R2),
    "r2_std_classA":          (4.50,   "USD per 1M", SRC_R2),
    "r2_std_classB":          (0.36,   "USD per 1M", SRC_R2),
    "r2_ia_storage":          (0.01,   "USD/GB-month (30-day minimum)", SRC_R2),
    "r2_ia_classA":           (9.00,   "USD per 1M", SRC_R2),
    "r2_ia_classB":           (0.90,   "USD per 1M", SRC_R2),
    "r2_ia_retrieval":        (0.01,   "USD/GB", SRC_R2),
    "r2_free_storage":        (10,     "GB-month/month (Standard only)", SRC_R2),
    "r2_free_classA":         (1e6,    "ops/month (Standard only)", SRC_R2),
    "r2_free_classB":         (10e6,   "ops/month (Standard only)", SRC_R2),
    "d1_read_incl":           (25e9,   "rows/month", SRC_D1),
    "d1_read_rate":           (0.001,  "USD per 1M rows", SRC_D1),
    "d1_write_incl":          (50e6,   "rows/month", SRC_D1),
    "d1_write_rate":          (1.00,   "USD per 1M rows", SRC_D1),
    "d1_storage_incl":        (5,      "GB", SRC_D1),
    "d1_storage_rate":        (0.75,   "USD/GB-month", SRC_D1),
    "q_ops_incl":             (1e6,    "ops/month", SRC_Q),
    "q_ops_rate":             (0.40,   "USD per 1M ops", SRC_Q),
    "q_ops_per_msg":          (3,      "ops/message (write+read+delete, <=64 KB)", SRC_Q),
    "do_req_incl":            (1e6,    "requests/month", SRC_DO),
    "do_req_rate":            (0.15,   "USD per 1M", SRC_DO),
    "do_dur_incl":            (400e3,  "GB-s/month", SRC_DO),
    "do_dur_rate":            (12.50,  "USD per 1M GB-s (billed at 128 MB/object)", SRC_DO),
    "email_incl":             (3000,   "emails/month/account", SRC_EM),
    "email_rate":             (0.35,   "USD per 1,000", SRC_EM),
    "apple_dev":              (99.0,   "USD/year", SRC_APPLE),
    "azure_signing_basic":    (9.99,   "USD/month (5,000 signatures)", SRC_AZ),
    "android_full_dist":      (25.0,   "USD once (Play / ADC full distribution)", SRC_ANDROID),
    "android_limited_dist":   (0.0,    "USD (ADC limited distribution, <=20 devices)", SRC_ANDROID),
}
P = {k: v[0] for k, v in PRICES.items()}

# ---------------------------------------------------------------------------------------
# Volume parameters (A = assumption, O = owner input, D = design choice). (value, status, who replaces it)
# ---------------------------------------------------------------------------------------
PARAMS = {
    "mean_file_bytes":      (4e6,        "A", "E1 census / A0 (owner-intake: 500k files per 2 TB)"),
    "share_bytes_large":    (0.6,        "A", "E1 / A5 (bytes in multipart files)"),
    "share_files_large":    (0.01,       "A", "E1 / A5"),
    "part_bytes":           (5_244_160,  "D", "T1 spike 2 default part (content-encryption-format.md); B6 decides"),
    "meta_objects_per_file": (1,         "A", "A2/A3 (1 = one metadata object per file; 0 = batched)"),
    "queue_msgs_per_file":  (2,          "A", "C1 (one R2 object-create notification per object)"),
    "worker_req_per_file":  (3,          "A", "A0 (dedup check, presign, commit)"),
    "cpu_ms_per_req":       (5,          "A", "D3-S1 (BUD-CPU-REQ < 1 ms for auth alone)"),
    "d1_rows_w_per_file":   (6,          "A", "A0 / C1"),
    "d1_rows_r_per_file":   (10,         "A", "A0 / C1"),
    "classB_per_file":      (2,          "A", "A0 (homelab HEAD/GET)"),
    "dwell_days":           (1,          "A", "A3 / C1 (upload -> commit -> delete)"),
    "warm_cache_days":      (0,          "D", "C1 (ADR-0001 optional warm cache; traceability C-01)"),
    "devices":              (25,         "O", "H2 F2 (settled range 10-25)"),
    "people":               (10,         "O", "H2 F1"),
    "heartbeat_per_dev_day": (96,        "A", "B8/C7 (status ping every 15 min)"),
    "emails_per_person_month": (4,       "A", "E3 nudge policy"),
    "dedup_ratio":          (0.0,        "A", "A1/F3 (0 = conservative)"),
    "engine_overhead":      (0.0,        "A", "A6-S2"),
    "fill_target":          (0.80,       "O", "C5 / owner (rule of thumb, no primary source)"),
    "lead_days":            (14,         "A", "H5 L21 (drive purchase + burn-in)"),
    "buffer_days":          (90,         "A", "C4 proposal"),
    "afr":                  (0.0136,     "secondary", "Backblaze 2025 annual AFR (search snippet; primary blocked)"),
}
V = {k: v[0] for k, v in PARAMS.items()}


def billed(usage, included, unit=1e6, order="round_then_subtract"):
    """Number of billable units. R2 docs: 'Cloudflare rounds up your usage to the next billing
    unit' but do not say whether the free tier is subtracted before or after rounding.
    DO docs say: excess over included, then round up. Default = the more expensive reading."""
    if order == "round_then_subtract":
        return max(0, math.ceil(usage / unit - 1e-12) - included / unit)
    return max(0, math.ceil((usage - included) / unit - 1e-12))


# ---------------------------------------------------------------------------------------
# Staging: day-by-day simulation of R2 staged bytes (GB-month = mean of daily PEAK over 30 d)
# ---------------------------------------------------------------------------------------
_SG_CACHE = {}


def staged_gb_month(inflow_gb_per_day, hold_days, outage=None, days=30, warmup=60):
    if not isinstance(inflow_gb_per_day, list):
        key = (inflow_gb_per_day, hold_days, outage, days, warmup)
        if key not in _SG_CACHE:
            _SG_CACHE[key] = _staged_gb_month(inflow_gb_per_day, hold_days, outage, days, warmup)
        return _SG_CACHE[key]
    return _staged_gb_month(inflow_gb_per_day, hold_days, outage, days, warmup)


def _staged_gb_month(inflow_gb_per_day, hold_days, outage=None, days=30, warmup=60):
    """inflow_gb_per_day: list or constant. hold_days: days an object stays before deletion
    (dwell + warm cache). outage=(start,len) in days of the billed month: homelab pulls nothing,
    so nothing is committed or deleted; backlog drains the day after (drain assumed fast, see
    isp.csv for when it is not). Peak of day k = bytes present at any time on day k
    = everything uploaded on days k-hold .. k that is not yet deleted (conservative: deletions
    happen at end of day)."""
    total = warmup + days
    inflow = [inflow_gb_per_day] * total if not isinstance(inflow_gb_per_day, list) else inflow_gb_per_day
    stored = []  # (upload_day, gb, delete_day)
    peaks = []
    for day in range(total):
        mday = day - warmup
        in_outage = outage is not None and outage[0] <= mday < outage[0] + outage[1]
        stored.append([day, inflow[day], day + hold_days])
        peaks.append(sum(g for _, g, _ in stored))
        if not in_outage:
            # end of day: delete everything whose delete_day <= today. Objects whose commit was
            # delayed by an outage get delete_day = max(original, today) once the homelab is back.
            stored = [s for s in stored if s[2] > day]
        else:
            pass
    month = peaks[warmup:]
    return sum(month) / days, max(month)


def monthly_bill(files, bytes_in, v, hold_days=None, outage=None, ia=False, order="round_then_subtract",
                 extra_worker_req=0, extra_d1_w=0, inflow_profile=None):
    """Return a dict of line items (USD) for one month of `files` new unique files carrying
    `bytes_in` bytes through R2."""
    hold = (v["dwell_days"] + v["warm_cache_days"]) if hold_days is None else hold_days
    n_large = files * v["share_files_large"]
    n_small = files - n_large
    bytes_large = bytes_in * v["share_bytes_large"]
    mean_large = bytes_large / n_large if n_large else 0
    parts_per_large = math.ceil(mean_large / v["part_bytes"]) if n_large else 0
    classA_content = n_small * 1 + n_large * (parts_per_large + 2)
    classA_meta = files * v["meta_objects_per_file"]
    classA = classA_content + classA_meta
    objects = files * (1 + v["meta_objects_per_file"])
    classB = files * v["classB_per_file"]
    # heartbeats etc.
    hb = v["devices"] * v["heartbeat_per_dev_day"] * 30
    wreq = files * v["worker_req_per_file"] + hb + extra_worker_req
    wcpu = wreq * v["cpu_ms_per_req"]
    d1w = files * v["d1_rows_w_per_file"] + hb + extra_d1_w
    d1r = files * v["d1_rows_r_per_file"] + hb
    qops = files * v["queue_msgs_per_file"] * P["q_ops_per_msg"]
    emails = v["people"] * v["emails_per_person_month"]

    gb_day = inflow_profile if inflow_profile is not None else bytes_in / GB / 30
    gbm, peak = staged_gb_month(gb_day, hold, outage=outage)

    out = {"files": files, "bytes_TB": bytes_in / TB, "classA_ops": classA, "classB_ops": classB,
           "objects": objects, "parts_per_large_file": parts_per_large,
           "staged_GB_month": gbm, "staged_peak_GB": peak,
           "worker_requests": wreq, "d1_rows_written": d1w, "queue_ops": qops}
    out["usd_workers_base"] = P["workers_paid_base"]
    if not ia:
        out["usd_r2_classA"] = billed(classA, P["r2_free_classA"], order=order) * P["r2_std_classA"]
        out["usd_r2_classB"] = billed(classB, P["r2_free_classB"], order=order) * P["r2_std_classB"]
        out["usd_r2_storage"] = billed(gbm, P["r2_free_storage"], unit=1, order=order) * P["r2_std_storage"]
        out["usd_r2_retrieval"] = 0.0
    else:
        # IA: no free tier, 30-day minimum (each byte billed >= 30 days), retrieval on every GET
        gbm_ia = max(gbm, bytes_in / GB * 30 / 30)  # every byte at least one full 30-day month
        out["usd_r2_classA"] = math.ceil(classA / M) * P["r2_ia_classA"]
        out["usd_r2_classB"] = math.ceil(classB / M) * P["r2_ia_classB"]
        out["usd_r2_storage"] = math.ceil(gbm_ia) * P["r2_ia_storage"]
        out["usd_r2_retrieval"] = math.ceil(bytes_in / GB) * P["r2_ia_retrieval"]
    out["usd_workers_req"] = billed(wreq, P["workers_req_incl"], order=order) * P["workers_req_rate"]
    out["usd_workers_cpu"] = billed(wcpu, P["workers_cpu_incl"], order=order) * P["workers_cpu_rate"]
    out["usd_d1"] = (billed(d1w, P["d1_write_incl"], order=order) * P["d1_write_rate"]
                     + billed(d1r, P["d1_read_incl"], order=order) * P["d1_read_rate"])
    out["usd_queues"] = billed(qops, P["q_ops_incl"], order=order) * P["q_ops_rate"]
    out["usd_email"] = billed(emails, P["email_incl"], unit=1000, order=order) * P["email_rate"]
    out["usd_total"] = sum(val for k, val in out.items() if k.startswith("usd_"))
    return out


def files_for(bytes_in, v):
    return bytes_in / v["mean_file_bytes"]


# ---------------------------------------------------------------------------------------
def scenarios(v):
    rows = []

    def add(name, bytes_in, **kw):
        vv = dict(v)
        vv.update(kw.pop("override", {}))
        files = files_for(bytes_in, vv)
        r = monthly_bill(files, bytes_in, vv, **kw)
        r = {"scenario": name, **r}
        rows.append(r)
        return r

    for g in (0.5, 1.0, 2.0):
        for w in (0, 30):
            add(f"steady g={g} TB/yr warm_cache={w}d", g * TB / 12, override={"warm_cache_days": w})
    add("seed 2 TB/month dwell=1d", 2 * TB)
    add("seed 2 TB/month + 14-day homelab outage", 2 * TB, outage=(8, 14))
    add("seed 2 TB/month + 30-day warm cache", 2 * TB, override={"warm_cache_days": 30})
    add("seed 2 TB/month mean file 2 MB", 2 * TB, override={"mean_file_bytes": 2e6})
    add("seed 2 TB/month mean file 8 MB", 2 * TB, override={"mean_file_bytes": 8e6})
    add("seed 2 TB/month metadata batched (m=0)", 2 * TB, override={"meta_objects_per_file": 0})
    for pmib in (8, 16, 64):
        add(f"seed 2 TB/month part={pmib} MiB", 2 * TB, override={"part_bytes": pmib * MiB})
    add("seed 2 TB/month in R2 Infrequent Access (staging)", 2 * TB, ia=True)
    add("seed 2 TB/month, free tier subtracted before rounding", 2 * TB, order="subtract_then_round")
    # whole library staged because the homelab is down all month (no new files counted)
    for lib in (2, 5, 10):
        r = monthly_bill(0, 0, v, inflow_profile=[0.0] * 90)
        gbm = lib * TB / GB
        st = billed(gbm, P["r2_free_storage"], unit=1) * P["r2_std_storage"]
        rows.append({"scenario": f"homelab down all month, {lib} TB staged", "files": 0,
                     "bytes_TB": lib, "staged_GB_month": gbm, "staged_peak_GB": gbm,
                     "usd_workers_base": P["workers_paid_base"], "usd_r2_storage": st,
                     "usd_total": P["workers_paid_base"] + st + (r["usd_total"] - P["workers_paid_base"])})
    # restore: 500 GB staged for 7 days + 1 day lifecycle lag, 125k objects (1 PUT each + 1 GET each)
    rb = 500 * GB
    prof = [0.0] * 60 + [rb / GB] + [0.0] * 29
    gbm, peak = staged_gb_month(prof, 8, days=30, warmup=60)
    objs = rb / v["mean_file_bytes"]
    rows.append({"scenario": "restore 500 GB staged 7 d (+1 d lifecycle lag), steady month",
                 "files": objs, "bytes_TB": 0.5, "classA_ops": objs, "classB_ops": objs,
                 "staged_GB_month": gbm, "staged_peak_GB": peak,
                 "usd_r2_storage": billed(gbm, P["r2_free_storage"], unit=1) * P["r2_std_storage"],
                 "usd_total_extra_vs_steady": billed(gbm, P["r2_free_storage"], unit=1) * P["r2_std_storage"]})
    # 10 TB seed via R2 over 5 months (2 TB/month), total
    r = monthly_bill(files_for(2 * TB, v), 2 * TB, v)
    rows.append({"scenario": "10 TB seed via R2 over 5 months (total)", "bytes_TB": 10,
                 "usd_total": 5 * r["usd_total"], "usd_workers_base": 25.0})
    vv = dict(v); vv["warm_cache_days"] = 30
    r30 = monthly_bill(files_for(2 * TB, vv), 2 * TB, vv)
    rows.append({"scenario": "10 TB seed via R2 over 5 months, warm cache 30 d left on (total)",
                 "bytes_TB": 10, "usd_total": 5 * r30["usd_total"], "usd_workers_base": 25.0})
    return rows


# ---------------------------------------------------------------------------------------
def sensitivity(v):
    """Steady-state sensitivity: vary each uncertain volume parameter over a stated plausible
    range (one at a time), then the full factorial of all ranges. Growth and warm cache are
    scenario/design axes, reported per value, not treated as uncertainty."""
    ranges = {
        "mean_file_bytes": (1e6, 4e6, 8e6),
        "meta_objects_per_file": (0, 1, 3),
        "worker_req_per_file": (1, 3, 10),
        "cpu_ms_per_req": (1, 5, 50),
        "d1_rows_w_per_file": (2, 6, 20),
        "queue_msgs_per_file": (0, 2, 4),
        "classB_per_file": (1, 2, 6),
        "dwell_days": (1, 1, 14),
        "heartbeat_per_dev_day": (24, 96, 1440),
        "emails_per_person_month": (1, 4, 30),
    }
    rows = []
    for g in (0.5, 1.0, 2.0):
        for w in (0, 30):
            base = dict(v); base["warm_cache_days"] = w
            b = g * TB / 12
            central = monthly_bill(files_for(b, base), b, base)["usd_total"]
            for k, (lo, mid, hi) in ranges.items():
                vals = []
                for x in (lo, hi):
                    vv = dict(base); vv[k] = x
                    vals.append(monthly_bill(files_for(b, vv), b, vv)["usd_total"])
                rows.append({"growth_TB_yr": g, "warm_cache_days": w, "param": k, "low": lo, "high": hi,
                             "central_usd": central, "usd_at_low": vals[0], "usd_at_high": vals[1],
                             "max_dev_pct": 100 * max(abs(x - central) for x in vals) / central})
            # full factorial (3^10 = 59,049 combos) -> min/max
            keys = list(ranges)
            lo_t, hi_t = float("inf"), 0.0
            for combo in itertools.product(*[ranges[k] for k in keys]):
                vv = dict(base); vv.update(dict(zip(keys, combo)))
                t = monthly_bill(files_for(b, vv), b, vv)["usd_total"]
                lo_t, hi_t = min(lo_t, t), max(hi_t, t)
            rows.append({"growth_TB_yr": g, "warm_cache_days": w, "param": "ALL (full factorial)",
                         "low": "", "high": "", "central_usd": central, "usd_at_low": lo_t,
                         "usd_at_high": hi_t,
                         "max_dev_pct": 100 * max(abs(hi_t - central), abs(central - lo_t)) / central})
            # leave-one-out: full factorial with one parameter pinned at its central value,
            # i.e. how much the spread would shrink if A0 measured that parameter exactly
            for pin in keys:
                others = [k for k in keys if k != pin]
                lo_p, hi_p = float("inf"), 0.0
                for combo in itertools.product(*[ranges[k] for k in others]):
                    vv = dict(base); vv.update(dict(zip(others, combo)))
                    t = monthly_bill(files_for(b, vv), b, vv)["usd_total"]
                    lo_p, hi_p = min(lo_p, t), max(hi_p, t)
                rows.append({"growth_TB_yr": g, "warm_cache_days": w, "param": f"ALL except {pin} (pinned)",
                             "low": "", "high": "", "central_usd": central, "usd_at_low": lo_p,
                             "usd_at_high": hi_p,
                             "max_dev_pct": 100 * max(abs(hi_p - central), abs(central - lo_p)) / central})
    return rows


# ---------------------------------------------------------------------------------------
def abuse(v, bud_abuse=50.0):
    """Abuse cost rates. All derived from primary unit prices; the behaviours marked SB are
    undocumented and must be checked in the sandbox."""
    per_obj = (P["r2_std_classA"] + P["q_ops_per_msg"] * P["q_ops_rate"] + P["workers_req_rate"]
               + 2 * P["d1_write_rate"]) / M  # past free tiers: 1 PUT, 1 notification, 1 presign req, 2 D1 rows
    vectors = []
    for rate in (10, 100, 1000):
        per_day = per_obj * rate * 86400
        vectors.append({"vector": f"junk small PUTs via presigned URLs, {rate}/s (stolen credential)",
                        "usd_per_day": per_day, "hours_to_BUD_ABUSE": bud_abuse / per_day * 24,
                        "bounded_by": "per-device presign cap/day + account spend meter (C2)",
                        "undocumented_behaviour": ""})
    for expiry in (60, 900, 604800):
        per_url = expiry * P["r2_std_classA"] / M   # 1 write/s/key limit (S2); 429 billing unknown
        vectors.append({"vector": f"replay one presigned PUT to its key until expiry ({expiry} s)",
                        "usd_per_url": per_url, "usd_per_day": per_url * 25000,
                        "hours_to_BUD_ABUSE": bud_abuse / (per_url * 25000) * 24,
                        "bounded_by": "short expiry or signed If-None-Match; overwrite -> suspend",
                        "undocumented_behaviour": "SB: are 412/429 responses billed? is If-None-Match enforced on presigned PUT?"})
    for gbps in (0.1, 1.0):
        tb_day = gbps * 1e9 / 8 * 86400 / TB
        usd_per_day_held = tb_day * 1000 * P["r2_std_storage"] / 30
        vectors.append({"vector": f"storage flood at {gbps} Gbps (Content-Length not bound)",
                        "tb_per_day": tb_day, "usd_per_day": usd_per_day_held,
                        "note": "USD per day of holding ONE day of flood; accrues daily while kept",
                        "hours_to_BUD_ABUSE": "",
                        "bounded_by": "per-device staged-byte cap; delete (free) on size mismatch",
                        "undocumented_behaviour": "SB: is signed Content-Length enforced? are incomplete multipart parts billed as storage?"})
    for rps, cpu in ((1000, 1), (10000, 1), (10000, 5)):
        req = rps * 86400
        per_day = req / M * P["workers_req_rate"] + req * cpu / M * P["workers_cpu_rate"]
        vectors.append({"vector": f"unauthenticated flood on the Worker {rps}/s, {cpu} ms CPU",
                        "usd_per_day": per_day, "hours_to_BUD_ABUSE": bud_abuse / per_day * 24,
                        "bounded_by": "NOT by per-device caps. Free-zone WAF: 1 rule, per-IP, 10 s",
                        "undocumented_behaviour": "SB: are WAF-blocked requests billed as Worker requests?"})
    vectors.append({"vector": "bad-signature requests direct to R2 (403)", "usd_per_day": "",
                    "bounded_by": "unknown", "undocumented_behaviour": "SB: only 401 is documented as free"})

    # bound for the credential-holder vectors under candidate cap sets
    bound = []
    for k, T, U_d, E_eff, Q_gb in itertools.product((1, 3, 25), (1 / 24, 1, 3), (5000, 25000, 100000),
                                                     (1, 60, 900), (10, 100, 1000)):
        per_dev_day = U_d * E_eff * P["r2_std_classA"] / M + U_d * (
            P["q_ops_per_msg"] * P["q_ops_rate"] + P["workers_req_rate"] + 2 * P["d1_write_rate"]) / M
        storage_month = k * Q_gb * P["r2_std_storage"]  # staged-byte cap held a full month
        total = k * T * per_dev_day + storage_month
        bound.append({"compromised_devices_k": k, "days_to_suspend_T": round(T, 4), "presigns_per_dev_day_U": U_d,
                      "writes_per_url_E": E_eff, "staged_cap_per_dev_GB_Q": Q_gb,
                      "usd_ops": k * T * per_dev_day, "usd_storage_month": storage_month,
                      "usd_bound": total, "below_BUD_ABUSE_50": total < bud_abuse})
    return vectors, bound, per_obj


# ---------------------------------------------------------------------------------------
TIERS = {  # usable fraction from Proxmox local-zfs.adoc: mirror 50 %, RAIDZ-P over N ~ (N-P)/N
    "S: 2x16 TB mirror": (2, 16, 0.5),
    "M: 4x16 TB RAIDZ2": (4, 16, 2 / 4),
    "M': 2x(2x16 TB) mirrors": (4, 16, 0.5),
    "L: 6x20 TB RAIDZ2": (6, 20, 4 / 6),
}


def capacity(v, t0=dt.date(2026, 9, 29)):
    rows = []
    for tier, (n, size, eff) in TIERS.items():
        usable = n * size * eff
        for L0, g in ((2, 0.5), (5, 1.0), (10, 1.5), (10, 2.0)):
            mult = (1 - v["dedup_ratio"]) * (1 + v["engine_overhead"])
            target = v["fill_target"] * usable
            years_to_target = (target / mult - L0) / g
            trigger_years = years_to_target - (v["lead_days"] + v["buffer_days"]) / 365.25
            date = t0 + dt.timedelta(days=trigger_years * 365.25) if trigger_years > 0 else t0
            rows.append({"tier": tier, "drives": n, "drive_TB": size, "usable_TB": usable,
                         "usable_TiB": usable * TB / 2**40, "L0_TB": L0, "growth_TB_yr": g,
                         "years_to_fill_target": round(years_to_target, 2),
                         "purchase_trigger_date": "BUY NOW" if trigger_years <= 0 else date.isoformat(),
                         "stored_after_10y_TB": round((L0 + 10 * g) * mult, 1),
                         "expected_drive_failures_10y": round(n * v["afr"] * 10, 2),
                         "arc_guideline_GiB": round(2 + usable * TB / 2**40, 1)})
    return rows


def isp():
    rows = []
    for lib in (1, 2, 5, 10):
        for mbps in (20, 50, 100, 500, 1000):
            days = lib * TB * 8 / (mbps * 1e6) / 86400
            rows.append({"TB": lib, "link_Mbps": mbps, "days_at_full_rate": round(days, 2),
                         "use": "pull (downlink) or restore (uplink)"})
    # cap-limited pull: months to pull a seed under a monthly cap with household baseline usage
    for cap in (1.2, 2.0):
        for base in (0.3, 0.6):
            for lib in (2, 10):
                allowance = cap * 0.8 - base  # alert at 80 % of cap
                months = lib / allowance if allowance > 0 else float("inf")
                rows.append({"TB": lib, "cap_TB_month": cap, "household_baseline_TB": base,
                             "pull_allowance_TB_month_at_80pct": round(allowance, 2),
                             "months_to_pull_seed": round(months, 1),
                             "r2_storage_usd_if_backlog_waits_1_month": round(lib * 1000 * P["r2_std_storage"], 2)})
    return rows


def fixed_costs():
    return [
        {"item": "Workers Paid (production)", "usd_year": 12 * P["workers_paid_base"], "when": "always"},
        {"item": "Workers Paid (sandbox, research only)", "usd_year": 12 * P["workers_paid_base"], "when": "research phase"},
        {"item": "Apple Developer Program", "usd_year": P["apple_dev"], "when": "OD-01 iOS in v1 / OD-09"},
        {"item": "Azure Artifact Signing Basic", "usd_year": 12 * P["azure_signing_basic"], "when": "OD-09 (US/Canada individuals only)"},
        {"item": "Google Play / ADC full distribution", "usd_once": P["android_full_dist"], "when": "OD-10 closed track"},
        {"item": "ADC limited distribution", "usd_once": P["android_limited_dist"], "when": "OD-10 limited (<=20 devices)"},
        {"item": "Domain", "usd_year": "owner quote (H5 L02 estimate $10-15, unverified)", "when": "always"},
        {"item": "Email Service", "usd_year": 0.0, "when": "inside 3,000/month; verified destinations free"},
    ]


def write_csv(path, rows):
    keys = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: (f"{x:.4f}" if isinstance(x, float) else x) for k, x in r.items()})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"))
    ap.add_argument("--bud-abuse", type=float, default=50.0, help="proposed default (owner-intake B3); unconfirmed")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    write_csv(os.path.join(a.out, "prices.csv"),
              [{"key": k, "value": val, "unit": u, "source": s, "accessed": ACCESSED} for k, (val, u, s) in PRICES.items()])
    write_csv(os.path.join(a.out, "params.csv"),
              [{"key": k, "value": val, "status": st, "replaced_by": who} for k, (val, st, who) in PARAMS.items()])
    sc = scenarios(V); write_csv(os.path.join(a.out, "scenarios.csv"), sc)
    se = sensitivity(V); write_csv(os.path.join(a.out, "sensitivity.csv"), se)
    vec, bnd, per_obj = abuse(V, a.bud_abuse)
    write_csv(os.path.join(a.out, "abuse_vectors.csv"), vec)
    write_csv(os.path.join(a.out, "abuse_bound.csv"), bnd)
    cap = capacity(V); write_csv(os.path.join(a.out, "capacity.csv"), cap)
    write_csv(os.path.join(a.out, "isp.csv"), isp())
    write_csv(os.path.join(a.out, "fixed_costs.csv"), fixed_costs())

    # ---- self-checks against the primary sources' own worked examples ----
    checks = []
    # R2 Standard example: 1,000 x 1 GB for a month, 1,000 writes, 1M reads -> $14.85
    ex = (billed(1000, 10, unit=1, order="subtract_then_round") * 0.015
          + billed(1000, 1e6) * 4.5 + billed(1e6, 10e6) * 0.36)
    checks.append({"check": "R2 Standard worked example = $14.85 (S1)", "model": round(ex, 2), "pass": abs(ex - 14.85) < 1e-9})
    # R2 IA example -> $29.90
    ex = 1000 * 0.01 + math.ceil(1000 / M) * 9.0 + math.ceil(1e6 / M) * 0.90 + 1000 * 0.01
    checks.append({"check": "R2 IA worked example = $29.90 (S1)", "model": round(ex, 2), "pass": abs(ex - 29.90) < 1e-9})
    # R2 asset example -> $104.40
    ex = billed(300e6, 10e6, order="subtract_then_round") * 0.36
    checks.append({"check": "R2 asset-hosting example = $104.40 (S1)", "model": round(ex, 2), "pass": abs(ex - 104.40) < 1e-9})
    # R2 GB-month example: 1 GB x 5 d then 3 GB x 25 d = 2.66 GB-month
    gbm = (1 * 5 + 3 * 25) / 30
    checks.append({"check": "R2 GB-month example = 2.66 (S1, truncated)", "model": round(gbm, 4), "pass": abs(gbm - 2.6667) < 1e-3})
    # Simulator sanity: constant 1 GB/day held 1 day -> peak/day = 2 GB (today's + yesterday's)
    g1, _ = staged_gb_month(1.0, 1)
    checks.append({"check": "simulator: 1 GB/day, hold 1 d -> 2.0 GB-month (conservative peak)", "model": g1, "pass": abs(g1 - 2.0) < 1e-9})
    # Workers example 1: 15M req, 7 ms -> $5 + $1.50 + $1.50 = $8.00 (per S7)
    ex = 5 + billed(15e6, 10e6, order="subtract_then_round") * 0.30 + billed(15e6 * 7, 30e6, order="subtract_then_round") * 0.02
    checks.append({"check": "Workers pricing example 1 = $8.00 (S7)", "model": round(ex, 2), "pass": abs(ex - 8.00) < 1e-9})
    # Queues formula check: 10M messages -> ((10M*3)-1M)/1M*0.40 = $11.60
    ex = billed(30e6, 1e6, order="subtract_then_round") * 0.40
    checks.append({"check": "Queues formula, 10M messages = $11.60 (S12)", "model": round(ex, 2), "pass": abs(ex - 11.60) < 1e-9})
    write_csv(os.path.join(a.out, "checks.csv"), checks)

    # ---- summary ----
    print("C4-S1 model v0 run", dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"))
    print("\n== self-checks against primary worked examples ==")
    for c in checks:
        print(f"  {'PASS' if c['pass'] else 'FAIL'}  {c['check']}: model={c['model']}")
    print("\n== monthly scenarios (USD) ==")
    for r in sc:
        t = r.get("usd_total", r.get("usd_total_extra_vs_steady"))
        extra = " (extra over steady)" if "usd_total_extra_vs_steady" in r else ""
        ca = r.get("classA_ops")
        print(f"  {r['scenario']:<66} total={t:8.2f}{extra}"
              + (f"  classA={ca/1e6:.2f}M" if ca else "")
              + (f"  stagedGBm={r['staged_GB_month']:.0f}" if r.get('staged_GB_month') else ""))
    print("\n== steady-state sensitivity (full factorial of assumption ranges) ==")
    for r in se:
        if r["param"] == "ALL (full factorial)":
            print(f"  g={r['growth_TB_yr']} W={r['warm_cache_days']:>2}: central ${r['central_usd']:.2f}, "
                  f"range ${r['usd_at_low']:.2f}-${r['usd_at_high']:.2f}, max dev {r['max_dev_pct']:.0f} %")
    for g in (1.0, 2.0):
        loo = sorted([r for r in se if r["param"].startswith("ALL except") and r["growth_TB_yr"] == g
                      and r["warm_cache_days"] == 0], key=lambda r: r["max_dev_pct"])[:3]
        print(f"  g={g} W=0, spread left after pinning one parameter (best three):",
              "; ".join(f"{r['param'][11:-9]} -> {r['max_dev_pct']:.0f} %" for r in loo))
    top = sorted([r for r in se if not r["param"].startswith("ALL")], key=lambda r: -r["max_dev_pct"])[:6]
    print("  largest one-at-a-time swings:")
    for r in top:
        print(f"    g={r['growth_TB_yr']} W={r['warm_cache_days']} {r['param']} [{r['low']}..{r['high']}]:"
              f" ${r['usd_at_low']:.2f}..${r['usd_at_high']:.2f} ({r['max_dev_pct']:.0f} %)")
    print(f"\n== abuse (per junk object past free tiers: ${per_obj*1e6:.2f} per million) ==")
    for r in vec:
        h = r.get("hours_to_BUD_ABUSE")
        d = r.get("usd_per_day")
        print(f"  {r['vector']:<70} $/day={d if d == '' else round(d, 2)}"
              + (f"  hours to ${a.bud_abuse:.0f}={h:.1f}" if isinstance(h, float) else ""))
    n_ok = sum(1 for b in bnd if b["below_BUD_ABUSE_50"])
    print(f"  cap-set grid: {n_ok}/{len(bnd)} combinations bound credential-holder abuse below ${a.bud_abuse:.0f}")
    rec = [b for b in bnd if b["compromised_devices_k"] == 3 and abs(b["days_to_suspend_T"] - 1) < 1e-9
           and b["presigns_per_dev_day_U"] == 25000 and b["staged_cap_per_dev_GB_Q"] == 100]
    for b in rec:
        print(f"    k=3 T=1d U=25k Q=100GB E={b['writes_per_url_E']:>3}: ${b['usd_bound']:.2f}"
              f" -> {'below' if b['below_BUD_ABUSE_50'] else 'ABOVE'} BUD-ABUSE")
    worst_ok_k25 = [b for b in bnd if b["compromised_devices_k"] == 25 and b["below_BUD_ABUSE_50"]]
    print(f"    all 25 devices compromised: {len(worst_ok_k25)} of {sum(1 for b in bnd if b['compromised_devices_k']==25)} cap sets stay below")
    print("\n== capacity / disk-purchase trigger (t0 = 2026-09-29, scenario inputs, not the family's) ==")
    for r in cap:
        print(f"  {r['tier']:<24} usable {r['usable_TB']:>5.1f} TB  L0={r['L0_TB']:>2} g={r['growth_TB_yr']}: "
              f"{r['years_to_fill_target']:>6} y to {int(V['fill_target']*100)} %  trigger {r['purchase_trigger_date']}")
    print(f"\nCSV written to {a.out}")


if __name__ == "__main__":
    main()
