#!/usr/bin/env python3
"""E1-S2 share-range calculator. Runs on the OWNER'S machine, next to the private store (H3 R7).

Revised 2026-10-06 after skeptic review (E1 note §2.3). The low-high pair is an ESTIMATE, not a
proven bound, until kit Part 0 has checked what the Settings figures mean on real phones.

Input: a CSV kept in the private store (never in the repo), one row per camera LIBRARY (not per
device), with these columns:

  library,platform,method,cloud_on,device_gb,cloud_gb,flags,bound_gb,note

  library   pseudonym only, e.g. L1 (the mapping to people stays in the private store)
  platform  apple | android
  method    M1 | M2 | M3 | A1 | A2 (see README "Methods")
  cloud_on  yes | no | unsure   iCloud Photos (apple) or Google Photos backup (android)
  device_gb apple: iPhone Storage > Photos (M2).  android: Settings > Storage, Images + Videos (A1)
            or the A2 MediaStore total.  Blank = not read.
  cloud_gb  apple: iCloud > Storage > Photos (M1), or the M3 osxphotos total when method is M3.
            android: the Google Photos / Google One "Photos" figure.  Blank = not read.
  flags     ';'-separated tokens, a trailing '?' means "unsure" and counts as yes:
              apple:   icloud_full  iCloud storage full or uploads paused
                       mixed        Mac/PC imports or scans in the same library, or Shared Library on
              android: saver        Storage saver / High quality ever used for backup
                       pre2021      backup started before June 2021
                       pixel        the phone is or was a Pixel 1-5
                       shared_total only a shared Google quota total was visible (cloud_gb blank)
  bound_gb  optional independent bound from M3, A2 or an item-count estimate (say which in note):
              apple + mixed      -> used as the library's LOW figure
              android unbounded  -> used as the library's HIGH figure
  note      free text; STAYS in the private store; never printed by this script

Rule (E1 note §2.3; the 40 % threshold is PLAN's and is not changed here):
  apple, cloud_on=no:           low = high = device
  apple, cloud_on=yes|unsure:   low = max(device, cloud), high = device + cloud
                                (high covers paused uploads; low may be too high if 'mixed')
  apple, method M3:             low = high = cloud_gb (the osxphotos total)
  apple with 'mixed':           low = bound_gb if given, else UNKNOWN
  android, cloud_on=no:         low = high = device
  android, cloud_on=yes|unsure: low = max(device, cloud), high = device + cloud
  android with saver/pre2021/pixel/shared_total:
                                high = bound_gb if given, else UNBOUNDED
  share_low  = A_low  / (A_low  + D_high)   (unknown if any A_low is UNKNOWN or any D_high UNBOUNDED)
  share_high = A_high / (A_high + D_low)
  share_low known and >= 0.40 -> ESCALATE OD-01
  share_high < 0.40           -> DO NOT ESCALATE
  otherwise                   -> STRADDLE (with the reason), run M3/A2 or decide with the range shown
  any required figure missing -> INCOMPLETE: no verdict at all

Output: ONLY family-wide totals and the range (AGG). No per-library row is printed.
Usage: share_range.py libraries.csv
"""
import csv
import math
import sys

THRESHOLD = 0.40
APPLE_FLAGS = {"icloud_full", "mixed"}
ANDROID_FLAGS = {"saver", "pre2021", "pixel", "shared_total"}


def num(x):
    x = (x or "").strip()
    if not x:
        return None
    v = float(x)
    if v < 0:
        raise ValueError("negative")
    return v


def parse_flags(s):
    out = set()
    for t in (s or "").replace(",", ";").split(";"):
        t = t.strip().lower().rstrip("?")
        if t:
            out.add(t)
    return out


def main(path):
    a_low = a_high = d_low = d_high = 0.0
    a_low_unknown = 0      # apple libraries whose low figure is unknown ('mixed', no bound)
    d_high_unbounded = 0   # android libraries whose high figure is unbounded
    n = {"apple": 0, "android": 0}
    problems, incomplete = [], []
    with open(path, newline="", encoding="utf-8") as fh:
        for i, r in enumerate(csv.DictReader(fh), start=2):
            p = (r.get("platform") or "").strip().lower()
            method = (r.get("method") or "").strip().upper()
            on = (r.get("cloud_on") or "").strip().lower()
            try:
                dev, cloud, bound = num(r.get("device_gb")), num(r.get("cloud_gb")), num(r.get("bound_gb"))
            except ValueError:
                problems.append(f"row {i}: a GB field is not a non-negative number")
                continue
            flags = parse_flags(r.get("flags"))
            if p not in ("apple", "android"):
                problems.append(f"row {i}: platform must be apple or android")
                continue
            if on not in ("yes", "no", "unsure"):
                problems.append(f"row {i}: cloud_on must be yes, no or unsure")
                continue
            allowed = APPLE_FLAGS if p == "apple" else ANDROID_FLAGS
            if flags - allowed:
                problems.append(f"row {i}: unknown flag(s) for {p}: {', '.join(sorted(flags - allowed))}")
                continue

            if p == "apple":
                if method == "M3":
                    if cloud is None:
                        incomplete.append(f"row {i}: M3 row without the osxphotos total in cloud_gb")
                        continue
                    lo = hi = cloud
                elif on == "no":
                    if dev is None:
                        incomplete.append(f"row {i}: apple, iCloud Photos off, device_gb missing")
                        continue
                    lo = hi = dev
                else:
                    if dev is None or cloud is None:
                        incomplete.append(f"row {i}: apple, iCloud Photos on/unsure, needs both device_gb and cloud_gb")
                        continue
                    lo, hi = max(dev, cloud), dev + cloud
                if "mixed" in flags:
                    if bound is not None:
                        lo = min(lo, bound)
                    else:
                        lo = None
                if lo is None:
                    a_low_unknown += 1
                else:
                    a_low += lo
                a_high += hi
            else:
                if dev is None:
                    incomplete.append(f"row {i}: android, device_gb missing")
                    continue
                if on == "no":
                    lo = hi = dev
                else:
                    if cloud is None and "shared_total" not in flags:
                        incomplete.append(f"row {i}: android, backup on/unsure, cloud_gb missing (use flag shared_total if only a total was shown)")
                        continue
                    c = cloud or 0.0
                    lo, hi = max(dev, c), dev + c
                    if flags & {"saver", "pre2021", "pixel", "shared_total"}:
                        hi = max(hi, bound) if bound is not None else math.inf
                if math.isinf(hi):
                    d_high_unbounded += 1
                else:
                    d_high += hi
                d_low += lo
            n[p] += 1

    if problems:
        print("Fix these rows first (row numbers only; nothing else is shown):")
        print("\n".join("  " + q for q in problems))
        return 2
    if incomplete:
        print("INCOMPLETE: no verdict. Missing readings (row numbers only):")
        print("\n".join("  " + q for q in incomplete))
        print("Take the missing readings (or re-read at S2b), then rerun.")
        return 3
    if n["apple"] + n["android"] == 0 or a_high + d_low == 0:
        print("No bytes recorded; nothing to compute.")
        return 2

    hi_share = a_high / (a_high + d_low)
    low_known = a_low_unknown == 0 and d_high_unbounded == 0
    lo_share = a_low / (a_low + d_high) if low_known and (a_low + d_high) > 0 else None

    if lo_share is not None and lo_share >= THRESHOLD:
        verdict = "ESCALATE OD-01 (share_low >= 40 %)"
    elif hi_share < THRESHOLD:
        verdict = "DO NOT ESCALATE (share_high < 40 %)"
    elif lo_share is None:
        verdict = ("STRADDLE: share_low is unknown because some libraries have no bound "
                   "(see the counts above). Escalation cannot be shown from these readings; "
                   "get M3/A2 or an item-count bound for those libraries, or the owner decides with the range shown")
    else:
        verdict = "STRADDLE: the range contains 40 %. Run M3/A2 at the earliest visit, or the owner decides with the range shown"

    def cnt(k):
        return str(k) if k >= 5 else ("0" if k == 0 else "<5")

    print("E1-S2 family-wide result (AGG; safe to paste into results.md after the H3 §4 check)")
    print("  NOTE: low-high is an estimate, not a proven bound, until Part 0 has verified the screens.")
    print(f"  libraries: apple {cnt(n['apple'])}, android {cnt(n['android'])}")
    print(f"  apple libraries with unknown low (mixed, no bound): {cnt(a_low_unknown)}")
    print(f"  android libraries with unbounded high (saver/pre2021/pixel/shared_total, no bound): {cnt(d_high_unbounded)}")
    # H3 §4: a platform total over fewer than 5 libraries is close to a per-person figure; withhold it.
    if n["apple"] >= 5:
        lo_txt = "unknown" if a_low_unknown else f"{a_low:.0f}"
        print(f"  apple library bytes:   {lo_txt}-{a_high:.0f} GB (low-high)")
    else:
        print("  apple library bytes:   withheld (<5 libraries)")
    if n["android"] >= 5:
        hi_txt = "unbounded" if d_high_unbounded else f"{d_high:.0f}"
        print(f"  android library bytes: {d_low:.0f}-{hi_txt} GB (low-high)")
    else:
        print("  android library bytes: withheld (<5 libraries)")
    lo_txt = "unknown" if lo_share is None else f"{lo_share:.0%}"
    print(f"  share of camera-library bytes on Apple devices: {lo_txt} - {hi_share:.0%}")
    print(f"  verdict: {verdict}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
