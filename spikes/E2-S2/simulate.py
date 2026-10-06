#!/usr/bin/env python3
"""E2-S2 emulated metrics pipeline (THROWAWAY spike code). EMULATED, NOT REAL R2/CLOUDFLARE.

What it does, on synthetic data only (H3 class SYN -> results):
  1. Simulates N devices over D days: discovery, uploads, homelab receipts (A3 per-device batches),
     receipts relayed back to the device, nudges, one gone-before-safe event and one injected
     false-safe UI bug.
  2. Each device writes one daily report of aggregate counters plus a digest of the record_ids its UI
     shows as "stored at home". Fields newer than the consent version the person accepted are zeroed
     (Syncthing ClearForVersion pattern). The report is padded to a fixed size and encrypted with the
     real `age` CLI to the homelab's X25519 recipient.
  3. A dict stands in for R2 and a list for the Worker's plaintext log. Nothing else reaches "cloud".
  4. The "homelab" decrypts the reports and computes M1, M2 (7 and 30 days), M6, M7, M9 and M10,
     using its own receipt ledger and the Worker's plaintext timestamps.
  5. Leak scan: searches every byte the mock cloud holds for synthetic filenames, path tokens,
     plaintext SHA-256 values, record_ids and report field names. Positive control: the same scanner
     over the plaintext reports must find the field names.
  6. Measures report sizes (plaintext, padded, ciphertext) against BUD-TEL, and the size of a
     plaintext record_id list vs the digest for a 100k-item device.
"""
import hashlib
import json
import os
import random
import statistics
import subprocess
import sys
import tempfile
import time
import uuid

SEED = 20260929
N_DEVICES = 25          # CLAUDE.md upper bound of devices
N_PERSONS = 10
DAYS = 30
PAD_TO = 2048           # fixed report size in bytes before encryption
REPORT_VERSION = 2      # current report schema version
FALSE_SAFE_DEVICE = 7   # injected bug: UI shows 3 items as stored without receipts from day 10
GONE_DEVICE = 12        # 2 items vanish before commit on day 5
CLOUD_ONLY_DEVICE = 3   # 500 items are cloud-only placeholders
STALE_DEVICE = 18       # offline days 12-20, gets an email nudge on day 15 (stale > 3 days)

# report fields: name -> consent 'since' version (None = operational, always sent)
REPORT_FIELDS = {
    "discovered_items": None, "discovered_bytes": None,
    "cloud_only_items": None, "cloud_only_bytes": None,
    "receipted_items": None, "receipted_bytes": None,
    "shown_stored_count": None, "shown_stored_digest": None, "receipt_seq_seen": None,
    "first_receipt_verified_s": None,
    "gone_before_safe": None,
    "restore_checked": None, "restore_mismatch": None,
    "nudges_shown": 2, "nudges_snoozed": 2, "nudges_muted": 2,
}


def clear_for_version(report, accepted):
    """Zero every field whose 'since' version is newer than the accepted version (Syncthing pattern)."""
    out = dict(report)
    for k, since in REPORT_FIELDS.items():
        if since is not None and (accepted is None or since > accepted):
            out[k] = 0
    return out


def digest(record_ids):
    h = hashlib.sha256()
    for r in sorted(record_ids):
        h.update(bytes.fromhex(r))
    return h.hexdigest()


class Device:
    def __init__(self, i, rng):
        self.id = f"dev-{i:02d}"
        self.idx = i
        self.person = i % N_PERSONS
        self.platform = ["windows", "macos", "linux", "android"][i % 4]
        self.consent = 1 if i % 5 == 0 else 2      # every 5th person accepted only report v1
        n = rng.randint(1000, 20000)
        user = f"u{rng.getrandbits(32):08x}"
        self.items = []
        for _ in range(n):
            folder = f"ev{rng.getrandbits(40):010x}"
            self.items.append(dict(
                path=f"/home/{user}/Pictures/{folder}/IMG_{rng.getrandbits(48):012x}.JPG",
                size=max(1, int(rng.lognormvariate(14.7, 1.0))),   # ~2.4 MB median, synthetic
                sha256=os.urandom(32).hex(),
                cloud_only=(i == CLOUD_ONLY_DEVICE and len(self.items) < 500),
                state="found", record_id=None))
        self.redeemed_day = rng.randint(0, 3)
        self.rate = rng.randint(300, 3000)         # items uploaded per online day
        self.receipts = set()                      # record_ids with verified receipts
        self.receipt_seq_seen = 0
        self.first_receipt_day = None
        self.gone = 0
        self.nudges = dict(shown=0, snoozed=0, muted=0)
        self.restore = dict(checked=0, mismatch=0)
        self.ui_bug_ids = []

    def online(self, day):
        return not (self.idx == STALE_DEVICE and 12 <= day <= 20)


class Homelab:
    def __init__(self):
        self.ledger = {}          # device_id -> list of (batch_seq, record_id, size, day)
        self.seq = {}

    def commit(self, dev, records, day):
        s = self.seq.get(dev.id, 0) + 1
        self.seq[dev.id] = s
        self.ledger.setdefault(dev.id, []).extend((s, r, sz, day) for r, sz in records)
        return s


def age_encrypt(recipient, data):
    return subprocess.run(["age", "-r", recipient], input=data, capture_output=True, check=True).stdout


def age_decrypt(identity_file, data):
    return subprocess.run(["age", "-d", "-i", identity_file], input=data, capture_output=True, check=True).stdout


def main(outdir):
    rng = random.Random(SEED)
    tmp = tempfile.mkdtemp()
    key = os.path.join(tmp, "homelab.key")
    subprocess.run(["age-keygen", "-o", key], capture_output=True, check=True)
    recipient = [l.split(": ")[1] for l in open(key) if l.startswith("# public key")][0].strip()

    devices = [Device(i, rng) for i in range(N_DEVICES)]
    home = Homelab()
    r2 = {}                 # mock R2: key -> bytes
    worker_log = []         # mock Worker plaintext: what ADR-0002 allows
    pending_batches = {d.id: [] for d in devices}   # receipt batches waiting to be relayed to the device
    plain_reports = []      # kept only for the positive control and size stats (never "uploaded")
    enc_ms = []

    for d in devices:
        worker_log.append(dict(kind="redeemed", device=d.id, day=d.redeemed_day))

    for day in range(DAYS):
        for d in devices:
            if day < d.redeemed_day or not d.online(day):
                continue
            worker_log.append(dict(kind="last_seen", device=d.id, day=day))
            # receipts published yesterday arrive today (relay lag of one day)
            for seq, ids in pending_batches[d.id]:
                d.receipts.update(ids)
                d.receipt_seq_seen = max(d.receipt_seq_seen, seq)
                for it in d.items:
                    if it["record_id"] in ids:
                        it["state"] = "committed"
                if d.first_receipt_day is None and ids:
                    d.first_receipt_day = day
            pending_batches[d.id] = []
            # gone-before-safe
            if d.idx == GONE_DEVICE and day == 5:
                for it in [x for x in d.items if x["state"] == "found"][:2]:
                    it["state"] = "gone-before-safe"
                    d.gone += 1
            # upload today's share; homelab commits and signs one batch per device per day
            todo = [x for x in d.items if x["state"] == "found" and not x["cloud_only"]][:d.rate]
            recs = []
            for it in todo:
                it["record_id"] = uuid.uuid4().hex
                it["state"] = "sent"
                recs.append((it["record_id"], it["size"]))
            if recs:
                seq = home.commit(d, recs, day)
                pending_batches[d.id].append((seq, {r for r, _ in recs}))
            # injected UI bug: three sent-but-not-receipted items shown as stored
            if d.idx == FALSE_SAFE_DEVICE and day == 10:
                d.ui_bug_ids = [x["record_id"] for x in d.items if x["state"] == "sent"][:3]
            # nudges on the device (synthetic)
            if rng.random() < 0.1:
                d.nudges["shown"] += 1
                if rng.random() < 0.3:
                    d.nudges["snoozed"] += 1
            # restore drill on day 25 for one device per platform
            if day == 25 and d.idx < 4:
                n = 10
                d.restore["checked"] += n
                worker_log.append(dict(kind="restore_staged", device=d.id, day=day))
            # --- the daily report ---
            shown = set(d.receipts) | set(d.ui_bug_ids)
            local = d.items   # gone-before-safe items stay in the denominator (possible loss)
            rep = dict(v=REPORT_VERSION, device=d.id, day=day,
                       discovered_items=len(local), discovered_bytes=sum(x["size"] for x in local),
                       cloud_only_items=sum(1 for x in local if x["cloud_only"]),
                       cloud_only_bytes=sum(x["size"] for x in local if x["cloud_only"]),
                       receipted_items=sum(1 for x in local if x["state"] == "committed"),
                       receipted_bytes=sum(x["size"] for x in local if x["state"] == "committed"),
                       shown_stored_count=len(shown), shown_stored_digest=digest(shown),
                       receipt_seq_seen=d.receipt_seq_seen,
                       first_receipt_verified_s=(None if d.first_receipt_day is None
                                                 else (d.first_receipt_day - d.redeemed_day) * 86400),
                       gone_before_safe=d.gone,
                       restore_checked=d.restore["checked"], restore_mismatch=d.restore["mismatch"],
                       nudges_shown=d.nudges["shown"], nudges_snoozed=d.nudges["snoozed"],
                       nudges_muted=d.nudges["muted"])
            rep = clear_for_version(rep, d.consent)
            rep["consent"] = d.consent
            raw = json.dumps(rep, separators=(",", ":")).encode()
            assert len(raw) <= PAD_TO - 1, len(raw)
            padded = raw + b"\n" + b" " * (PAD_TO - len(raw) - 1)
            t0 = time.perf_counter()
            ct = age_encrypt(recipient, padded)
            enc_ms.append((time.perf_counter() - t0) * 1000)
            plain_reports.append(raw)
            k = f"telemetry/{d.id}/{uuid.uuid4().hex}"
            r2[k] = ct
            worker_log.append(dict(kind="report_arrival", device=d.id, day=day, size=len(ct)))
        # email nudge from the Worker: stale device > 3 days (activity timestamps only)
        for d in devices:
            seen = [w["day"] for w in worker_log if w["kind"] == "last_seen" and w["device"] == d.id]
            if seen and day - max(seen) == 3:
                worker_log.append(dict(kind="email_nudge_sent", device=d.id, day=day, nudge="stale-device"))

    # ----------------- homelab side -----------------
    reports = {}
    for k, ct in r2.items():
        rep = json.loads(age_decrypt(key, ct).decode().rstrip())
        reports.setdefault(rep["device"], []).append(rep)
    for v in reports.values():
        v.sort(key=lambda r: r["day"])

    redeemed = {w["device"]: w["day"] for w in worker_log if w["kind"] == "redeemed"}
    metrics = {}
    # M1 from the homelab's own ledger (commit day) and the Worker's redemption day, cross-checked
    m1 = {}
    for d in devices:
        first_commit = min(e[3] for e in home.ledger[d.id])
        dev_rep = next((r["first_receipt_verified_s"] for r in reports[d.id] if r["first_receipt_verified_s"] is not None), None)
        m1[d.id] = dict(homelab_first_commit_days=first_commit - redeemed[d.id],
                        device_first_receipt_days=None if dev_rep is None else dev_rep / 86400)
    metrics["M1"] = m1
    # M2 coverage at day 7 and 30 after redemption
    m2 = {}
    for d in devices:
        out = {}
        for horizon in (7, 30):
            target = redeemed[d.id] + horizon
            cand = [r for r in reports[d.id] if r["day"] <= target]
            r = cand[-1]
            local_bytes = r["discovered_bytes"] - r["cloud_only_bytes"]
            out[f"d{horizon}"] = dict(
                bytes_pct_incl_cloud_only=round(100 * r["receipted_bytes"] / r["discovered_bytes"], 2),
                bytes_pct=round(100 * r["receipted_bytes"] / local_bytes, 2) if local_bytes else None,
                items_pct=round(100 * r["receipted_items"] / (r["discovered_items"] - r["cloud_only_items"]), 2),
                cloud_only_items=r["cloud_only_items"], report_day=r["day"],
                note="horizon beyond simulated days" if target >= DAYS else "")
        m2[d.id] = out
    metrics["M2"] = m2
    # M9: compare the device's shown-stored digest with the homelab's digest over receipts in batches <= seq seen
    m9 = []
    for d in devices:
        for r in reports[d.id]:
            ids = [e[1] for e in home.ledger.get(d.id, []) if e[0] <= r["receipt_seq_seen"]]
            if digest(ids) != r["shown_stored_digest"]:
                m9.append(dict(device=d.id, day=r["day"], shown=r["shown_stored_count"], receipted_upto_seq=len(ids),
                               excess=r["shown_stored_count"] - len(ids)))
    first_m9 = {}
    for e in m9:
        first_m9.setdefault(e["device"], e)
    metrics["M9"] = dict(mismatch_reports=len(m9), devices=sorted(first_m9), first=list(first_m9.values()))
    # M10
    metrics["M10"] = {d.id: reports[d.id][-1]["gone_before_safe"] for d in devices if reports[d.id][-1]["gone_before_safe"]}
    # M6: email nudges and whether the device came back (activity) within 3 days
    m6 = []
    for w in worker_log:
        if w["kind"] == "email_nudge_sent":
            back = [x["day"] for x in worker_log if x["kind"] == "last_seen" and x["device"] == w["device"]
                    and w["day"] < x["day"] <= w["day"] + 3]
            new_commits = [e for e in home.ledger[w["device"]] if w["day"] < e[3] <= w["day"] + 3]
            m6.append(dict(device=w["device"], day=w["day"], back_within_3d=bool(back),
                           receipts_within_3d=len(new_commits)))
    metrics["M6_email"] = m6
    metrics["M6_device_counters"] = {d.id: dict(shown=reports[d.id][-1]["nudges_shown"],
                                                snoozed=reports[d.id][-1]["nudges_snoozed"],
                                                consent=d.consent) for d in devices}
    metrics["M7"] = {d.id: dict(checked=reports[d.id][-1]["restore_checked"],
                                mismatch=reports[d.id][-1]["restore_mismatch"], platform=d.platform)
                     for d in devices if reports[d.id][-1]["restore_checked"]}

    # ----------------- leak scan over everything the mock cloud holds -----------------
    cloud_blob = json.dumps(worker_log).encode() + b"".join(k.encode() + v for k, v in r2.items())
    needles = {"filename": [], "path_token": [], "sha256_hex": [], "record_id": []}
    for d in devices:
        for it in d.items[:200]:   # 200 per device = 5,000 of each kind
            fn = it["path"].rsplit("/", 1)[1]
            needles["filename"].append(fn.encode())
            needles["path_token"].append(it["path"].split("/")[4].encode())
            needles["sha256_hex"].append(it["sha256"].encode())
            if it["record_id"]:
                needles["record_id"].append(it["record_id"].encode())
    field_names = [k.encode() for k in REPORT_FIELDS]
    leak = {k: sum(1 for n in v if n in cloud_blob) for k, v in needles.items()}
    leak["report_field_names"] = sum(1 for n in field_names if n in cloud_blob)
    needle_counts = {k: len(v) for k, v in needles.items()}
    needle_counts["report_field_names"] = len(field_names)
    plain_blob = b"".join(plain_reports)
    positive_control = sum(1 for n in field_names if n in plain_blob)

    # consent check
    v1_devs = [d.id for d in devices if d.consent == 1]
    consent_ok = all(r["nudges_shown"] == 0 and r["nudges_snoozed"] == 0 for dv in v1_devs for r in reports[dv])
    v2_nonzero = any(r["nudges_shown"] > 0 for d in devices if d.consent == 2 for r in reports[d.id])

    # ----------------- sizes -----------------
    ct_sizes = [len(v) for v in r2.values()]
    raw_sizes = [len(x) for x in plain_reports]
    big = [uuid.uuid4().hex for _ in range(100_000)]
    list_json = len(json.dumps(big, separators=(",", ":")).encode())
    list_bin = 16 * len(big)
    sizes = dict(
        reports=len(r2),
        plaintext_json_bytes=dict(min=min(raw_sizes), median=statistics.median(raw_sizes), max=max(raw_sizes)),
        padded_bytes=PAD_TO,
        ciphertext_bytes=dict(min=min(ct_sizes), max=max(ct_sizes)),
        per_device_per_day_1_report=max(ct_sizes),
        per_device_per_day_24_reports=24 * max(ct_sizes),
        outbox_30_days_unsent=30 * max(ct_sizes),
        bud_tel_network_bytes_per_day=1_000_000, bud_tel_disk_bytes=50_000_000,
        record_id_list_100k_json_bytes=list_json, record_id_list_100k_binary_bytes=list_bin,
        digest_bytes=32 + 8,
        age_encrypt_ms=dict(median=round(statistics.median(enc_ms), 2), max=round(max(enc_ms), 2),
                            note="includes process spawn of the age CLI"),
        size_distinct_values_in_cloud=sorted(set(ct_sizes)),
    )

    result = dict(
        label="EMULATED, NOT REAL R2/CLOUDFLARE; synthetic data (SYN -> results)",
        seed=SEED, devices=N_DEVICES, persons=N_PERSONS, days=DAYS,
        injected=dict(false_safe_device=f"dev-{FALSE_SAFE_DEVICE:02d}", gone_device=f"dev-{GONE_DEVICE:02d}",
                      cloud_only_device=f"dev-{CLOUD_ONLY_DEVICE:02d}", stale_device=f"dev-{STALE_DEVICE:02d}"),
        metrics=metrics,
        leak_scan=dict(hits=leak, needles=needle_counts, positive_control_field_names_in_plaintext=positive_control,
                       cloud_bytes_scanned=len(cloud_blob)),
        consent=dict(v1_devices=v1_devs, v2_fields_zeroed_for_v1=consent_ok, v2_fields_present_for_v2=v2_nonzero),
        worker_log_kinds=sorted({w["kind"] for w in worker_log}),
        worker_log_keys=sorted({k for w in worker_log for k in w}),
        sizes=sizes,
    )
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "simulate-result.json"), "w") as f:
        json.dump(result, f, indent=1)
    # short summary to stdout
    print(json.dumps(dict(leak_scan=result["leak_scan"], consent=result["consent"], M9=metrics["M9"],
                          M10=metrics["M10"], M6_email=m6, M7=metrics["M7"], sizes=sizes,
                          worker_log_keys=result["worker_log_keys"]), indent=1))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "evidence")
