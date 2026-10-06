#!/usr/bin/env python3
"""Tests for stopgap_copy.py on synthetic data (SYN -> results), plus the EXIF write-back demonstration."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import stopgap_copy as sc  # noqa: E402

TOOL = [sys.executable, os.path.join(HERE, "stopgap_copy.py")]
results = {}


def run(*args):
    p = subprocess.run(TOOL + list(args), capture_output=True, text=True)
    return p.returncode, json.loads(p.stdout) if p.stdout.strip().startswith("{") else p.stdout, p.stderr


def manifest(d):
    return [json.loads(l) for l in open(os.path.join(d, "manifest.jsonl"), encoding="utf-8")]


def make_tree(root):
    os.makedirs(os.path.join(root, "Pictures", "2019 Summer"), exist_ok=True)
    os.makedirs(os.path.join(root, "Pictures", "Sub", "Deep"), exist_ok=True)
    files = {
        "Pictures/2019 Summer/IMG_0001.JPG": os.urandom(3_000_000),
        "Pictures/Sub/Deep/empty.txt": b"",
        "Pictures/" + unicodedata.normalize("NFD", "Café Noël.jpg"): os.urandom(4096),
        "Pictures/" + unicodedata.normalize("NFC", "Café Noël.jpg"): os.urandom(4096),
        "Pictures/emoji 🎂 birthday.heic": os.urandom(10_000),
        "Pictures/.DS_Store": b"junk",
    }
    for rel, data in files.items():
        with open(os.path.join(root, rel), "wb") as f:
            f.write(data)
    with open(os.path.join(root, "Pictures", "big.mov"), "wb") as f:
        for _ in range(256):
            f.write(os.urandom(1 << 20))
    os.symlink("IMG_0001.JPG", os.path.join(root, "Pictures", "2019 Summer", "link.jpg"))
    return len(files) - 1 + 1  # regular files copied (minus .DS_Store, plus big.mov)


def main():
    t = tempfile.mkdtemp(prefix="e2s3-")
    src, dst = os.path.join(t, "src"), os.path.join(t, "dst")
    expected = make_tree(src)
    # 1. first copy
    t0 = time.perf_counter()
    rc, out, err = run("copy", os.path.join(src, "Pictures"), "--to", dst, "--label", "syn-visit")
    secs = time.perf_counter() - t0
    base = os.path.join(dst, "syn-visit")
    m = manifest(base)
    results["1_first_copy"] = dict(rc=rc, counts=out["counts"], expected_regular_files=expected,
                                   ds_store_skipped=not any(r["rel"].endswith(".DS_Store") for r in m),
                                   symlink_status=[r["status"] for r in m if r["rel"].endswith("link.jpg")],
                                   seconds=round(secs, 2), bytes=out["bytes_copied"],
                                   mb_per_s=round(out["bytes_copied"] / secs / 1e6, 1),
                                   note="container virtual disk; not representative of USB or NAS speed")
    # hashes match source, mtimes preserved
    okhash = okm = 0
    for r in m:
        if "sha256" in r:
            sp = os.path.join(src, "Pictures", r["rel"])
            dp = os.path.join(base, r["stored_as"])
            okhash += sc.sha256_file(sp) == r["sha256"] == sc.sha256_file(dp)
            okm += os.stat(sp).st_mtime_ns == os.stat(dp).st_mtime_ns
    results["1_hash_and_mtime"] = dict(files=sum(1 for r in m if "sha256" in r), hash_match=okhash, mtime_match=okm)
    # 2. verify
    rc, out, _ = run("verify", base)
    results["2_verify"] = dict(rc=rc, **out)
    # 3. rerun is idempotent
    rc, out, _ = run("copy", os.path.join(src, "Pictures"), "--to", dst, "--label", "syn-visit")
    n_files = sum(len(f) for _, _, f in os.walk(os.path.join(base, "1-Pictures")))
    results["3_rerun"] = dict(rc=rc, counts=out["counts"], files_in_dest=n_files)
    # 4. a source file changed between visits -> both kept, nothing overwritten
    p = os.path.join(src, "Pictures", "2019 Summer", "IMG_0001.JPG")
    old = sc.sha256_file(os.path.join(base, "1-Pictures", "2019 Summer", "IMG_0001.JPG"))
    with open(p, "r+b") as f:
        f.write(b"EDITED")
    rc, out, _ = run("copy", os.path.join(src, "Pictures"), "--to", dst, "--label", "syn-visit")
    d = os.path.join(base, "1-Pictures", "2019 Summer")
    results["4_changed_between_visits"] = dict(
        rc=rc, counts=out["counts"], files_in_folder=sorted(os.listdir(d)),
        original_kept=sc.sha256_file(os.path.join(d, "IMG_0001.JPG")) == old)
    # 5. corrupt one byte in the copy -> verify catches it
    q = os.path.join(base, "1-Pictures", "emoji 🎂 birthday.heic")
    with open(q, "r+b") as f:
        f.seek(100)
        b = f.read(1)
        f.seek(100)
        f.write(bytes([b[0] ^ 1]))
    rc, out, _ = run("verify", base)
    results["5_bitflip_detected"] = dict(rc=rc, **out)
    # 6. file changing during copy (logic test: simulated by bumping the source mtime from a read hook)
    s2 = os.path.join(t, "src2")
    os.makedirs(s2)
    live = os.path.join(s2, "growing.mp4")
    with open(live, "wb") as f:
        f.write(os.urandom(5 << 20))
    real_open = open

    def hooked_open(path, mode="r", *a, **k):
        fh = real_open(path, mode, *a, **k)
        if path == live and "r" in mode:
            with real_open(live, "ab") as g:     # the "camera app" appends while we copy
                g.write(b"more")
        return fh
    sc.open = hooked_open
    st = os.stat(live)
    r = sc.copy_file(live, os.path.join(t, "growing.copy"), st)
    sc.open = real_open
    results["6_changed_during_copy"] = dict(status=r[1])
    # 7. placeholder detection on Linux is a no-op (Windows/macOS bits untested here)
    results["7_placeholder_check_linux"] = dict(is_placeholder=sc.is_placeholder(os.stat(p)),
                                               note="Windows and macOS attribute checks not exercised in CT")
    shutil.rmtree(t)
    print(json.dumps(results, indent=1, ensure_ascii=False))


def exif_demo():
    """Does writing Takeout JSON values back into EXIF change the file bytes (and so whole-file dedup)?"""
    # a minimal JPEG segment structure (SOI, APP0 JFIF, DQT, SOF, DHT-free arithmetic-coded 1x1, EOI)
    jpg = bytes.fromhex(
        "FFD8FFE000104A46494600010101004800480000FFDB004300030202020203020202030303030406040404040408060605"
        "0609080A0A090809090A0C0F0C0A0B0E0B09090D110D0E0F101011100A0C12131210130F101010FFC9000B080001000101"
        "011100FFCC000600101005FFDA0008010100003F00D2CF20FFD9")
    t = tempfile.mkdtemp(prefix="e2s3exif-")
    p = os.path.join(t, "IMG_TEST.JPG")
    with open(p, "wb") as f:
        f.write(jpg)
    before = hashlib.sha256(open(p, "rb").read()).hexdigest()

    def image_data_hash():
        o = subprocess.run(["exiftool", "-s3", "-api", "RequestAll=3", "-api", "ImageHashType=SHA256",
                            "-ImageDataHash", p], capture_output=True, text=True).stdout.strip()
        return o or None
    idh_before = image_data_hash()
    # values of the kind a Takeout JSON sidecar carries (photoTakenTime, geoData)
    subprocess.run(["exiftool", "-overwrite_original", "-DateTimeOriginal=2019:07:04 12:00:00",
                    "-GPSLatitude=51.5", "-GPSLatitudeRef=N", "-GPSLongitude=0.12", "-GPSLongitudeRef=W", p],
                   capture_output=True, check=True)
    after = hashlib.sha256(open(p, "rb").read()).hexdigest()
    idh_after = image_data_hash()
    out = dict(exiftool=subprocess.run(["exiftool", "-ver"], capture_output=True, text=True).stdout.strip(),
               file_sha256_changed=before != after, size_before=len(jpg), size_after=os.path.getsize(p),
               image_data_hash_before=idh_before, image_data_hash_after=idh_after,
               image_data_unchanged=(idh_before == idh_after) if idh_before else None)
    shutil.rmtree(t)
    print(json.dumps(dict(exif_writeback=out), indent=1))


if __name__ == "__main__":
    main()
    exif_demo()
