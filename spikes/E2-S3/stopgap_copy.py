#!/usr/bin/env python3
"""E2-S3 stopgap copy helper for the owner (THROWAWAY spike code; Python 3.8+, standard library only).

The owner runs this on his own laptop at a family visit to copy a relative's keepsake folders to an
external disk or the homelab, before Reliquary exists. It is deliberately boring:

  copy   SRC... --to DEST --label LABEL
         Copies each SRC tree into DEST/LABEL/<n>-<basename>/, preserving mtimes. Hashes every file
         (SHA-256) while copying. Writes DEST/LABEL/manifest.jsonl (one line per file) and
         DEST/LABEL/provenance.json (route, date, host, counts). Never deletes anything, never
         overwrites a different existing file (a differing file is written as '<name>.conflict-<sha8>').
         Files that change while being copied are recorded as 'changed-during-copy' and not trusted.
         Cloud placeholders (OneDrive / iCloud Drive files not on the disk) are skipped and listed,
         never downloaded: Windows via FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS / RECALL_ON_OPEN / OFFLINE,
         macOS via SF_DATALESS. The placeholder checks are UNTESTED on real Windows/macOS in this spike.
  verify DEST/LABEL
         Re-reads every copied file and checks it against manifest.jsonl. Run it again at the homelab.

The manifest holds file names and paths: it is family data (H3 class FAM). It stays with the copy,
never in the repo. A9 can later import the copy with its manifest as provenance.
"""
import argparse
import datetime
import hashlib
import json
import os
import platform
import shutil
import socket
import stat
import sys

CHUNK = 1 << 20
# Windows attribute bits (winnt.h)
FILE_ATTRIBUTE_OFFLINE = 0x1000
FILE_ATTRIBUTE_RECALL_ON_OPEN = 0x40000
FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS = 0x400000
SF_DATALESS = 0x40000000  # macOS sys/stat.h

SKIP_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini", ".Spotlight-V100", ".Trashes", "$RECYCLE.BIN",
              "System Volume Information", ".fseventsd"}


def is_placeholder(st):
    attrs = getattr(st, "st_file_attributes", 0)
    if attrs & (FILE_ATTRIBUTE_OFFLINE | FILE_ATTRIBUTE_RECALL_ON_OPEN | FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS):
        return True
    flags = getattr(st, "st_flags", 0)
    return bool(flags & SF_DATALESS)


def copy_file(src, dst, before):
    """Copy src to dst while hashing. Returns (sha256, status)."""
    h = hashlib.sha256()
    tmp = dst + ".partial"
    with open(src, "rb") as fi, open(tmp, "wb") as fo:
        while True:
            b = fi.read(CHUNK)
            if not b:
                break
            h.update(b)
            fo.write(b)
        fo.flush()
        os.fsync(fo.fileno())
    after = os.stat(src)
    status = "ok"
    if (after.st_size, after.st_mtime_ns) != (before.st_size, before.st_mtime_ns) \
            or os.path.getsize(tmp) != before.st_size:
        status = "changed-during-copy"
    digest = h.hexdigest()
    if os.path.exists(dst):
        if sha256_file(dst) == digest:
            os.remove(tmp)
            return digest, "already-present"
        dst = f"{dst}.conflict-{digest[:8]}"
        status = "conflict-kept-both" if status == "ok" else status
    os.replace(tmp, dst)
    os.utime(dst, ns=(before.st_atime_ns, before.st_mtime_ns))
    return digest, status, dst


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(CHUNK), b""):
            h.update(b)
    return h.hexdigest()


def cmd_copy(a):
    base = os.path.join(a.to, a.label)
    os.makedirs(base, exist_ok=True)
    man_path = os.path.join(base, "manifest.jsonl")
    counts = {}
    total_bytes = 0
    with open(man_path, "a", encoding="utf-8") as man:
        for n, src_root in enumerate(a.src, 1):
            src_root = os.path.abspath(src_root)
            dst_root = os.path.join(base, f"{n}-{os.path.basename(src_root.rstrip(os.sep)) or 'root'}")
            for dirpath, dirnames, filenames in os.walk(src_root, followlinks=False):
                dirnames[:] = [d for d in dirnames if d not in SKIP_NAMES]
                rel_dir = os.path.relpath(dirpath, src_root)
                os.makedirs(os.path.join(dst_root, rel_dir), exist_ok=True)
                for fn in filenames:
                    sp = os.path.join(dirpath, fn)
                    rel = os.path.normpath(os.path.join(rel_dir, fn))
                    rec = dict(src_root=n, rel=rel)
                    try:
                        st = os.lstat(sp)
                    except OSError as e:
                        rec.update(status="unreadable", error=str(e))
                    else:
                        if fn in SKIP_NAMES:
                            continue
                        if not stat.S_ISREG(st.st_mode):
                            rec.update(status="not-a-regular-file")
                        elif is_placeholder(st):
                            rec.update(status="cloud-placeholder-skipped", size=st.st_size)
                        else:
                            try:
                                r = copy_file(sp, os.path.join(dst_root, rel), st)
                                digest, status = r[0], r[1]
                                rec.update(status=status, size=st.st_size, sha256=digest,
                                           mtime_ns=st.st_mtime_ns,
                                           stored_as=os.path.relpath(r[2], base) if len(r) > 2
                                           else os.path.relpath(os.path.join(dst_root, rel), base))
                                total_bytes += st.st_size
                            except OSError as e:
                                rec.update(status="unreadable", error=str(e))
                    counts[rec["status"]] = counts.get(rec["status"], 0) + 1
                    man.write(json.dumps(rec, ensure_ascii=False) + "\n")
    prov = dict(route="stopgap: owner visit copy", label=a.label,
                copied_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                copied_on_host=socket.gethostname(), copier_os=platform.platform(),
                sources=[os.path.abspath(s) for s in a.src], counts=counts, bytes_copied=total_bytes,
                tool="spikes/E2-S3/stopgap_copy.py")
    with open(os.path.join(base, "provenance.json"), "a", encoding="utf-8") as f:
        f.write(json.dumps(prov, ensure_ascii=False) + "\n")
    print(json.dumps(dict(counts=counts, bytes_copied=total_bytes), indent=1))
    # exit 1 when something needs the owner's attention; symlinks and kept conflicts are informational
    attention = {"unreadable", "changed-during-copy", "cloud-placeholder-skipped"}
    return 1 if attention & set(counts) else 0


def cmd_verify(a):
    base = a.dir
    ok = bad = 0
    problems = []
    stored = {}   # the manifest is appended on every run; check each stored file once
    with open(os.path.join(base, "manifest.jsonl"), encoding="utf-8") as man:
        for line in man:
            rec = json.loads(line)
            if "sha256" in rec:
                stored.setdefault(rec["stored_as"], rec["sha256"])
    for stored_as, sha in stored.items():
        p = os.path.join(base, stored_as)
        if os.path.exists(p) and sha256_file(p) == sha:
            ok += 1
        else:
            bad += 1
            problems.append(stored_as)
    print(json.dumps(dict(verified=ok, failed=bad, first_failures=problems[:10]), indent=1))
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("copy")
    c.add_argument("src", nargs="+")
    c.add_argument("--to", required=True)
    c.add_argument("--label", required=True, help="e.g. 2026-10-grandma-laptop")
    v = sub.add_parser("verify")
    v.add_argument("dir")
    a = ap.parse_args()
    sys.exit(cmd_copy(a) if a.cmd == "copy" else cmd_verify(a))


if __name__ == "__main__":
    main()
