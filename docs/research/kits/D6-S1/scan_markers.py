"""Scan exported files for personal-data markers (D6-S1 and D6-S2 kits; THROWAWAY research code).

Usage: python3 scan_markers.py --people people.json [--extra MARKER ...] FILE [FILE ...]
Markers: each person's full name, first name, full email address and email local part (case-insensitive).
Exit code 0 = no marker found in any file; 1 = at least one hit (the hits are printed, never the file contents).
"""
import argparse, json, sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--people", required=True)
    ap.add_argument("--extra", action="append", default=[])
    ap.add_argument("files", nargs="+")
    a = ap.parse_args()
    markers = set(a.extra)
    for p in json.load(open(a.people)):
        markers |= {p["name"], p["name"].split()[0], p["email"], p["email"].split("@")[0]}
    hits = 0
    for f in a.files:
        data = open(f, "rb").read().lower()
        found = sorted(m for m in markers if m.lower().encode() in data)
        print(json.dumps({"file": f, "bytes": len(data), "markers_found": found}))
        hits += bool(found)
    sys.exit(1 if hits else 0)


if __name__ == "__main__":
    main()
