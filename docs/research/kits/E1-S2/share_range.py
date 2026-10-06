#!/usr/bin/env python3
"""E1-S2 share-range calculator. Runs on the OWNER'S machine, next to the private store (H3 R7).

Input: a CSV kept in the private store (never in the repo), one row per camera LIBRARY (not per
device), with these columns:

  library,platform,method,device_gb,cloud_gb,apple_gb,note

  library   pseudonym only, e.g. L1 (the mapping to people stays in the private store)
  platform  apple | android
  method    M1 | M2 | M3 | A1 | A2 (see README "Methods")
  device_gb on-device Photos/Images+Videos figure in GB (blank if not read)
  cloud_gb  cloud Photos figure in GB (iCloud Photos, or Google Photos in Google One) (blank if none)
  apple_gb  apple only: the single figure used for the library (M1 iCloud Photos figure, or M2
            iPhone Storage > Photos when iCloud Photos is off, or M3 osxphotos total)
  note      free text; STAYS in the private store; never printed by this script

Rule (docs/research/e1-family-research-census.md §2.3; the 40 % threshold is PLAN's):
  android: low = max(device, cloud), high = device + cloud
  apple:   low = high = apple_gb
  share_low  = A_low  / (A_low  + D_high)
  share_high = A_high / (A_high + D_low)
  share_low >= 0.40  -> ESCALATE OD-01
  share_high < 0.40  -> DO NOT ESCALATE
  otherwise          -> STRADDLE: run M3/A2 at the earliest visit, or the owner decides with the range

Output: ONLY family-wide totals and the range (AGG). No per-library row is printed.
Usage: share_range.py libraries.csv
"""
import csv
import sys

THRESHOLD = 0.40


def f(x):
    x = (x or "").strip()
    return float(x) if x else None


def main(path):
    a_low = a_high = d_low = d_high = 0.0
    n = {"apple": 0, "android": 0}
    problems = []
    with open(path, newline="", encoding="utf-8") as fh:
        for i, r in enumerate(csv.DictReader(fh), start=2):
            p = (r.get("platform") or "").strip().lower()
            if p == "apple":
                v = f(r.get("apple_gb"))
                if v is None:
                    problems.append(f"row {i}: apple library without apple_gb")
                    continue
                a_low += v
                a_high += v
            elif p == "android":
                dev, cloud = f(r.get("device_gb")), f(r.get("cloud_gb"))
                if dev is None and cloud is None:
                    problems.append(f"row {i}: android library with neither device_gb nor cloud_gb")
                    continue
                dev, cloud = dev or 0.0, cloud or 0.0
                d_low += max(dev, cloud)
                d_high += dev + cloud
            else:
                problems.append(f"row {i}: platform must be apple or android")
                continue
            n[p] += 1
    if problems:
        print("Fix these rows first (row numbers only; nothing else is shown):")
        print("\n".join("  " + p for p in problems))
        return 2
    if a_low + d_high == 0 or a_high + d_low == 0:
        print("No bytes recorded; nothing to compute.")
        return 2
    lo = a_low / (a_low + d_high)
    hi = a_high / (a_high + d_low)
    if lo >= THRESHOLD:
        verdict = "ESCALATE OD-01 (share_low >= 40 %)"
    elif hi < THRESHOLD:
        verdict = "DO NOT ESCALATE (share_high < 40 %)"
    else:
        verdict = "STRADDLE: the range contains 40 %. Run M3/A2 at the earliest visit, or the owner decides with the range shown"

    def cnt(k):
        return str(n[k]) if n[k] >= 5 else "<5"

    print("E1-S2 family-wide result (AGG; safe to paste into results.md after the H3 §4 check)")
    print(f"  libraries: apple {cnt('apple')}, android {cnt('android')}")
    # H3 §4: a platform total over fewer than 5 libraries is close to a per-person figure; withhold it.
    print("  apple library bytes:   " + (f"{a_low:.0f} GB" if n["apple"] >= 5 else "withheld (<5 libraries)"))
    print("  android library bytes: " + (f"{d_low:.0f}-{d_high:.0f} GB (low-high)" if n["android"] >= 5
                                          else "withheld (<5 libraries)"))
    print(f"  share of camera-library bytes on Apple devices: {lo:.0%} - {hi:.0%}")
    print(f"  verdict: {verdict}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
