#!/usr/bin/env python3
"""F1-S1 upstream-churn measurement from git tag dates and commit counts.

Reads treeless bare clones (git clone --bare --filter=tree:0) in <tags-dir>. A "release" is a tag
matching the per-repo STABLE regex (pre-releases, RCs, betas, canaries and nightlies excluded).
Window ends at AS_OF. Tag date = %(creatordate) (tagger date for annotated tags, else commit date).
Usage: cadence.py <tags-dir> > cadence.csv
"""
import subprocess, sys, re, csv, datetime as dt
D = sys.argv[1]
AS_OF = dt.date(2026, 9, 29)
REPOS = {  # clone dir: (stable-tag regex, major-version group or None, note)
 "immich-app_immich.git": (r"^v(\d+)\.\d+\.\d+$", 1, "server+mobile share tags"),
 "ente_ente.git": (r"^photos-v(\d+)\.\d+\.\d+$", 1, "Ente Photos mobile app tags only (photos-vX.Y.Z, no -beta/-rc)"),
 "restic_restic.git": (r"^v(\d+\.\d+)\.\d+$", 1, "pre-1.0: minor = format/API epoch"),
 "restic_rest-server.git": (r"^v(\d+\.\d+)\.\d+$", 1, ""),
 "kopia_kopia.git": (r"^v(\d+\.\d+)\.\d+$", 1, "pre-1.0"),
 "PlakarKorp_plakar.git": (r"^v(\d+)\.\d+\.\d+$", 1, ""),
 "syncthing_syncthing.git": (r"^v(\d+)\.\d+\.\d+$", 1, ""),
 "rustic-rs_rustic_core.git": (r"^rustic_core-v(\d+\.\d+)\.\d+$", 1, "0.x: each minor is semver-breaking"),
 "borgbackup_borg.git": (r"^(1)\.\d+\.\d+$", 1, "stable 1.x only; 2.0 betas counted separately"),
 "uroni_urbackup_backend.git": (r"^(\d+)\.\d+\.\d+$", 1, "server tags (client tags have 'client' suffix)"),
 "researchxxl_syncthing-android.git": (r"^v(\d+)\.\d+\.\d+\.\d+$", 1, "fork repo created 2025-10; older tags inherited"),
 "duplicati_duplicati.git": (r"^v(\d+\.\d+)\.\d+\.\d+_stable_", 1, "stable channel tags only"),
 "nextcloud_android.git": (r"^stable-(\d+)\.\d+\.\d+$", 1, "stable-X.Y.Z tags"),
}
EXTRA = {"borgbackup_borg.git": r"^2\.0\.0b\d+$"}

def tags(repo):
    out = subprocess.run(["git", "-C", f"{D}/{repo}", "for-each-ref", "--format=%(creatordate:short) %(refname:short)", "refs/tags"],
                         capture_output=True, text=True, check=True).stdout.split("\n")
    for line in out:
        if line.strip():
            d, t = line.split(" ", 1); yield dt.date.fromisoformat(d), t

def commits_since(repo, since):
    return subprocess.run(["git", "-C", f"{D}/{repo}", "rev-list", "--count", f"--since={since}", "HEAD"],
                          capture_output=True, text=True).stdout.strip()

w = csv.writer(sys.stdout)
w.writerow(["repo", "stable_releases_12m", "stable_releases_24m", "version_epochs_started_12m", "epochs_started_24m_list",
            "latest_stable", "latest_stable_date", "commits_default_branch_12m", "extra", "note"])
y1 = AS_OF - dt.timedelta(days=365); y2 = AS_OF - dt.timedelta(days=730)
for repo, (rx, grp, note) in REPOS.items():
    rel = sorted((d, t, re.match(rx, t).group(grp)) for d, t in tags(repo) if re.match(rx, t))
    first_of_epoch = {}
    for d, t, e in rel:
        first_of_epoch.setdefault(e, (d, t))
    r12 = [x for x in rel if x[0] > y1]; r24 = [x for x in rel if x[0] > y2]
    ep12 = [e for e, (d, t) in first_of_epoch.items() if d > y1]
    ep24 = [f"{t}@{d}" for e, (d, t) in first_of_epoch.items() if d > y2]
    extra = ""
    if repo in EXTRA:
        b = sorted((d, t) for d, t in tags(repo) if re.match(EXTRA[repo], t))
        extra = f"2.0 betas: {len(b)} total, first {b[0][1]}@{b[0][0]}, last {b[-1][1]}@{b[-1][0]}, {len([x for x in b if x[0] > y1])} in 12m"
    last = rel[-1] if rel else (None, "", "")
    w.writerow([repo.replace(".git", ""), len(r12), len(r24), len(ep12), " ".join(ep24), last[1], last[0],
                commits_since(repo, y1.isoformat()), extra, note])
