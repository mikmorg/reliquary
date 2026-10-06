#!/usr/bin/env python3
"""SYN home-folder generator for the E1-S1 census rehearsal (THROWAWAY; data class SYN).

Writes a synthetic home folder whose files have real headers (JPEG with EXIF, ISOBMFF ftyp,
PDF, ZIP) followed by a sparse tail, so large logical sizes cost little disk. Every name contains
the marker "Qx7" so the privacy check can grep the census output for leaked names.
Emulated placeholders: files with the sticky bit set (the census must be built with
--features emulate-placeholders to treat them as cloud-only). This is an EMULATION on Linux, not a
real OneDrive/iCloud placeholder.

Usage: gen_home.py OUTDIR SCALE SEED   (SCALE 1 ~= 21k files; app-data files dominate at scale)
Writes OUTDIR/home-Qx7-user/ and OUTDIR/truth.json (expected totals per category/state/location).
"""
import json, math, os, random, struct, sys, time
from collections import defaultdict

out, scale, seed = sys.argv[1], float(sys.argv[2]), int(sys.argv[3])
rng = random.Random(seed)
home = os.path.join(out, "home-Qx7-user")
truth = defaultdict(lambda: [0, 0])  # key -> [count, bytes]
NOW = time.time()

CAMERAS = [("Apple", "iPhone 15"), ("Google", "Pixel 8"), ("samsung", "SM-S911B"), ("Canon", "Canon EOS 80D")]


def exif_jpeg(make, model, dt):
    def ascii_(s):
        b = s.encode() + b"\0"
        return b
    entries0 = []
    data = b""
    # TIFF big-endian. IFD0 at offset 8.
    mk, md = ascii_(make), ascii_(model)
    ifd0_n = 3
    ifd0_size = 2 + ifd0_n * 12 + 4
    data_off = 8 + ifd0_size
    mk_off = data_off
    md_off = mk_off + len(mk)
    exif_ifd_off = md_off + len(md)
    exif_n = 1
    exif_size = 2 + exif_n * 12 + 4
    dto = ascii_(dt)  # "YYYY:MM:DD HH:MM:SS"
    dt_off = exif_ifd_off + exif_size
    ifd0 = struct.pack(">H", ifd0_n)
    ifd0 += struct.pack(">HHII", 0x010F, 2, len(mk), mk_off)
    ifd0 += struct.pack(">HHII", 0x0110, 2, len(md), md_off)
    ifd0 += struct.pack(">HHII", 0x8769, 4, 1, exif_ifd_off)
    ifd0 += struct.pack(">I", 0)
    exif = struct.pack(">H", exif_n) + struct.pack(">HHII", 0x9003, 2, len(dto), dt_off) + struct.pack(">I", 0)
    tiff = b"MM\x00\x2a" + struct.pack(">I", 8) + ifd0 + mk + md + exif + dto
    app1 = b"Exif\x00\x00" + tiff
    return b"\xff\xd8" + b"\xff\xe1" + struct.pack(">H", len(app1) + 2) + app1 + b"\xff\xdb\x00\x43\x00" + bytes(64)


def plain_jpeg():
    return b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00" + b"\xff\xdb\x00\x43\x00" + bytes(64)


def ftyp(brand):
    b = brand.encode()
    box = b + struct.pack(">I", 0) + b + b"mp41"
    return struct.pack(">I", len(box) + 8) + b"ftyp" + box


HEADERS = {
    "pdf": lambda: b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n",
    "docx": lambda: b"PK\x03\x04\x14\x00\x06\x00" + bytes(22) + b"[Content_Types].xml",
    "png": lambda: b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + bytes(17),
    "mp4": lambda: ftyp("isom"),
    "mov": lambda: ftyp("qt  "),
    "heic": lambda: ftyp("heic"),
}


def lognorm(median, sigma):
    return max(1, int(rng.lognormvariate(math.log(median), sigma)))


def write(path, header, size, cat, loc, placeholder=False, mtime=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    size = max(size, len(header))
    with open(path, "wb") as f:
        f.write(header)
        f.truncate(size)
    if mtime is not None:
        os.utime(path, (mtime, mtime))
    if placeholder:
        os.chmod(path, 0o1644)
    st = "cloud-only" if placeholder else "local"
    for key in (f"cat|{cat}|{st}", f"loc|{loc}|{st}|{cat}", "total|files", ):
        truth[key][0] += 1
        truth[key][1] += size
    return size


def rand_time(months_back):
    return NOW - rng.uniform(0, months_back * 30.4 * 86400)


def n(x):
    return max(1, int(x * scale))


def camera_photo(path, loc, placeholder=False, exif=True):
    t = rand_time(36)
    ym = time.gmtime(t)
    dt = time.strftime("%Y:%m:%d %H:%M:%S", ym)
    make, model = rng.choice(CAMERAS)
    hdr = exif_jpeg(make, model, dt) if exif else plain_jpeg()
    # copies made later: mtime differs from capture time for ~30 % of photos
    mt = t if rng.random() > 0.3 else rand_time(3)
    size = write(path, hdr, lognorm(3_000_000, 0.5), "photo", loc, placeholder, mt)
    if exif and not placeholder:
        truth[f"exifmonth|{time.strftime('%Y-%m', ym)}"][0] += 1
        truth[f"camera|{make}|{model}"][0] += 1
        truth[f"camera|{make}|{model}"][1] += size


H = home
# Pictures: camera originals by year/event
for i in range(n(4000)):
    ev = f"{2020 + i % 6} Qx7 Event {i % 40}"
    camera_photo(f"{H}/Pictures/{ev}/IMG_Qx7_{i:05d}.JPG", "pictures")
# Pictures: non-ASCII names
for i in range(n(50)):
    camera_photo(f"{H}/Pictures/Été Qx7 😀/photo_Qx7_{i}.jpg", "pictures")
# Videos
for i in range(n(300)):
    ext = rng.choice(["mp4", "mov"])
    write(f"{H}/Videos/Qx7 clips/VID_Qx7_{i:04d}.{ext}", HEADERS[ext](), lognorm(80_000_000, 1.0), "video", "videos",
          mtime=rand_time(36))
# Documents
for i in range(n(1500)):
    ext = rng.choice(["pdf", "docx"])
    write(f"{H}/Documents/Qx7 papers {i % 20}/doc_Qx7_{i}.{ext}", HEADERS[ext](), lognorm(200_000, 1.2), "document",
          "documents", mtime=rand_time(120))
# Downloads: memes (no EXIF) and screenshots
for i in range(n(800)):
    write(f"{H}/Downloads/meme_Qx7_{i}.jpg", plain_jpeg(), lognorm(150_000, 0.8), "photo", "downloads",
          mtime=rand_time(24))
for i in range(n(600)):
    write(f"{H}/Pictures/Screenshots/Screenshot_Qx7_{i}.png", HEADERS["png"](), lognorm(400_000, 0.6), "photo",
          "pictures", mtime=rand_time(24))
# Messaging app media
for i in range(n(1200)):
    write(f"{H}/WhatsApp Qx7/Media/WhatsApp Images/IMG-Qx7-WA{i:04d}.jpg", plain_jpeg(), lognorm(180_000, 0.5),
          "photo", "messaging-app", mtime=rand_time(24))
# Cloud-sync folder with emulated placeholders (sticky bit) and some local files
for i in range(n(600)):
    ph = i % 3 != 0
    camera_photo(f"{H}/OneDrive - Qx7/Pictures/Camera Roll/IMG_Qx7_OD{i:04d}.jpg", "cloud-sync-folder", placeholder=ph)
for i in range(n(100)):
    write(f"{H}/OneDrive - Qx7/Documents/od_Qx7_{i}.pdf", HEADERS["pdf"](), lognorm(300_000, 1.0), "document",
          "cloud-sync-folder", placeholder=True)
# Extensionless placeholders: must never be opened (sniffing would hydrate them)
for i in range(n(50)):
    write(f"{H}/OneDrive - Qx7/Scans/scan_Qx7_{i}", plain_jpeg(), lognorm(1_000_000, 0.5), "other",
          "cloud-sync-folder", placeholder=True)
# Apple Photos library package: originals count as photos, derivatives as library-internal
for i in range(n(500)):
    write(f"{H}/Pictures/Photos Library.photoslibrary/originals/{i % 16:X}/Qx7-{i:06d}.heic", HEADERS["heic"](),
          lognorm(2_500_000, 0.5), "photo", "apple-photos-library", mtime=rand_time(36))
for i in range(n(1000)):
    write(f"{H}/Pictures/Photos Library.photoslibrary/resources/derivatives/{i % 16:X}/Qx7-{i:06d}_1_105_c.jpeg",
          plain_jpeg(), lognorm(300_000, 0.4), "library-internal", "apple-photos-library", mtime=rand_time(36))
# An "unmentioned" location: an old laptop copy in an odd folder
for i in range(n(700)):
    camera_photo(f"{H}/stuff Qx7/old laptop Qx7/DCIM/100CANON/IMG_Qx7_L{i:04d}.JPG", "other")
# Extensionless local files: JPEG magic (sniffed to photo) and random bytes (other)
for i in range(n(200)):
    write(f"{H}/stuff Qx7/recovered Qx7/file_Qx7_{i}", plain_jpeg(), lognorm(1_000_000, 0.5), "photo", "other",
          mtime=rand_time(60))
for i in range(n(200)):
    write(f"{H}/stuff Qx7/recovered Qx7/blob_Qx7_{i}", rng.randbytes(64), lognorm(50_000, 1.0), "other", "other",
          mtime=rand_time(60))
# Genealogy (text format; extension rule only)
for i in range(n(5)):
    write(f"{H}/Documents/Family Tree Qx7/tree_Qx7_{i}.ged", b"0 HEAD\n1 GEDC\n", lognorm(2_000_000, 0.5),
          "genealogy", "documents", mtime=rand_time(60))
# App data and caches: many small files (dominates the file count at scale)
for i in range(n(12000)):
    d = rng.choice([".cache/Qx7app", "AppData/Local/Qx7/Cache", ".local/share/Qx7", "Library/Caches/Qx7"])
    write(f"{H}/{d}/{i // 500}/c_Qx7_{i}.dat", b"", lognorm(8_000, 1.5), "app-or-system", "app-data-or-cache",
          mtime=rand_time(6))
# Symlinks (skipped by the census, not counted)
os.makedirs(f"{H}/links Qx7", exist_ok=True)
for i in range(n(20)):
    try:
        os.symlink(f"{H}/Pictures", f"{H}/links Qx7/loop_Qx7_{i}")
    except FileExistsError:
        pass

json.dump({k: v for k, v in sorted(truth.items())}, open(os.path.join(out, "truth.json"), "w"), indent=1)
print(json.dumps({"files": truth["total|files"][0], "bytes": truth["total|files"][1]}))
