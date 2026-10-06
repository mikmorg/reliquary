#!/usr/bin/env python3
"""B3-S1 manifest census: source-level permission / FGS census of comparable Android backup apps.

Reads AndroidManifest.xml files from sparse git checkouts, merges the main manifest with the
Play-flavour overlay (honouring tools:node="remove"), and reports the permissions and
foreground-service types that matter for Play policy. It does NOT reproduce the full Gradle
manifest merge: permissions contributed by third-party libraries (AARs, Flutter plugins) are
not included unless a library manifest is passed explicitly with --lib.
"""
import json, subprocess, sys, xml.etree.ElementTree as ET
from pathlib import Path

A = "{http://schemas.android.com/apk/res/android}"
T = "{http://schemas.android.com/tools}"

WATCH = [
    "android.permission.READ_MEDIA_IMAGES",
    "android.permission.READ_MEDIA_VIDEO",
    "android.permission.READ_MEDIA_VISUAL_USER_SELECTED",
    "android.permission.ACCESS_MEDIA_LOCATION",
    "android.permission.READ_EXTERNAL_STORAGE",
    "android.permission.WRITE_EXTERNAL_STORAGE",
    "android.permission.MANAGE_EXTERNAL_STORAGE",
    "android.permission.MANAGE_MEDIA",
    "android.permission.FOREGROUND_SERVICE",
    "android.permission.FOREGROUND_SERVICE_DATA_SYNC",
    "android.permission.FOREGROUND_SERVICE_SPECIAL_USE",
    "android.permission.FOREGROUND_SERVICE_MEDIA_PROCESSING",
    "android.permission.FOREGROUND_SERVICE_LOCATION",
    "android.permission.RUN_USER_INITIATED_JOBS",
    "android.permission.REQUEST_IGNORE_BATTERY_OPTIMIZATIONS",
    "android.permission.RECEIVE_BOOT_COMPLETED",
    "android.permission.ACCESS_BACKGROUND_LOCATION",
    "android.permission.REQUEST_INSTALL_PACKAGES",
    "android.permission.POST_NOTIFICATIONS",
    "android.permission.SCHEDULE_EXACT_ALARM",
    "android.permission.WAKE_LOCK",
]

def parse(path):
    root = ET.parse(path).getroot()
    perms, removed, fgs = {}, set(), []
    for tag in ("uses-permission", "uses-permission-sdk-23"):
        for el in root.iter(tag):
            name = el.get(A + "name")
            if el.get(T + "node") == "remove":
                removed.add(name)
                continue
            perms[name] = {k: el.get(A + k) for k in ("maxSdkVersion",) if el.get(A + k)}
            if el.get(T + "ignore"):
                perms[name]["tools:ignore"] = el.get(T + "ignore")
    for el in root.iter("service"):
        t = el.get(A + "foregroundServiceType")
        if t:
            sub = None
            for p in el.iter("property"):
                if p.get(A + "name") == "android.app.PROPERTY_SPECIAL_USE_FGS_SUBTYPE":
                    sub = p.get(A + "value")
            fgs.append({"service": el.get(A + "name"), "types": t,
                        "tools_node": el.get(T + "node"), "special_use_subtype": sub})
    return perms, removed, fgs

def census(app):
    base = Path(app["root"])
    merged, removed_all, fgs_all, files = {}, set(), [], []
    for rel in app["manifests"]:
        p = base / rel
        perms, removed, fgs = parse(p)
        files.append(rel)
        for n in removed:
            merged.pop(n, None)
        removed_all |= removed
        merged.update(perms)
        fgs_all += [dict(f, file=rel) for f in fgs]
    head = subprocess.run(["git", "-C", str(base), "log", "-1", "--format=%H %cI"],
                          capture_output=True, text=True).stdout.split()
    return {
        "app": app["name"], "package": app["package"], "repo": app["repo"],
        "commit": head[0] if head else None, "commit_date": head[1] if len(head) > 1 else None,
        "play_build_manifests": files, "removed_by_overlay": sorted(removed_all),
        "watched_permissions": {p: merged[p] for p in WATCH if p in merged},
        "fgs_services": fgs_all,
        "play_presence_evidence": app["play_evidence"],
    }

def main():
    cfg = json.load(open(sys.argv[1]))
    out = [census(a) for a in cfg]
    json.dump(out, sys.stdout, indent=2)

if __name__ == "__main__":
    main()
