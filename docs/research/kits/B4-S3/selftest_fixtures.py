#!/usr/bin/env python3
"""Kit B4-S3 self-test: makes SYN fixtures (random-noise JPEGs, no real photos) for bridge_check.py.
Run in an empty folder with Pillow and ExifTool installed, then:
  python3 bridge_check.py --bridge bridge --reference ref --download-started <5 minutes ago, ISO> --expect-mp 0.48 --no-suppress
Expected: photo_full_res 12, photo_not_full_res 6, mtime_is_download_time_photo 6,
reference byte_identical 5, present_but_bytes_differ 3, not_found 2 (measured 2026-09-29)."""
# SYN fixtures for bridge_check.py: random-noise JPEGs, no real photos.
import os, random, shutil, subprocess, time, datetime as dt
from PIL import Image
random.seed(7)
os.makedirs('bridge', exist_ok=True); os.makedirs('ref', exist_ok=True)
def mk(path, w, h, when):
    im = Image.frombytes('RGB', (w, h), os.urandom(w*h*3)); im.save(path, quality=80)
    subprocess.run(['exiftool','-q','-overwrite_original','-Make=SYN','-Model=SYN-1',
                    f'-DateTimeOriginal={when:%Y:%m:%d %H:%M:%S}', path], check=True)
base = dt.datetime(2026,5,1,12,0,0)
# 12 "originals" (full-res class scaled down: use expect-mp 0.48 = 800x600), 6 "optimised" (400x300)
for i in range(12):
    t = base + dt.timedelta(hours=i); p=f'bridge/o{i}.jpg'; mk(p,800,600,t)
    ts = t.replace(tzinfo=dt.timezone(dt.timedelta(hours=2))).timestamp(); os.utime(p,(ts,ts))  # bridge set mtime = capture (UTC+2)
for i in range(6):
    t = base + dt.timedelta(days=1,hours=i); mk(f'bridge/s{i}.jpg',400,300,t)  # mtime left = now (download time)
# reference: 5 identical copies, 3 with rewritten metadata, 2 missing from bridge
for i in range(5): shutil.copy2(f'bridge/o{i}.jpg', f'ref/r{i}.jpg')
for i in range(5,8):
    shutil.copy2(f'bridge/o{i}.jpg', f'ref/r{i}.jpg')
    subprocess.run(['exiftool','-q','-overwrite_original','-Artist=x',f'bridge/o{i}.jpg'],check=True)
    ts = (base+dt.timedelta(hours=i)).replace(tzinfo=dt.timezone(dt.timedelta(hours=2))).timestamp(); os.utime(f'bridge/o{i}.jpg',(ts,ts))
for i in range(2): mk(f'ref/m{i}.jpg',800,600,base+dt.timedelta(days=9,hours=i))
