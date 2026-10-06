#!/usr/bin/env python3
"""THROWAWAY SPIKE B4-S1: emulates the out-of-process background transfer service.
Takes handoff/<session>-<task>.json (file-backed upload tasks), PUTs the FILE, writes
events/<session>-<task>.json (what the delegate would receive after relaunch), removes the handoff.
Options: --drop-all (user force-quit: all tasks cancelled, no events), --delay S, --duplicate,
--path-map CONTAINER_PREFIX=HOST_PREFIX."""
import argparse, glob, json, os, time, urllib.request, urllib.error
ap = argparse.ArgumentParser()
ap.add_argument('--state'); ap.add_argument('--drop-all', action='store_true')
ap.add_argument('--delay', type=float, default=0); ap.add_argument('--duplicate', action='store_true')
ap.add_argument('--path-map', default='')
a = ap.parse_args()
cp, hp = (a.path_map.split('=', 1) + [''])[:2] if a.path_map else ('', '')
def tid(p): return int(p.rsplit('-', 1)[1].split('.')[0])
jobs = sorted(glob.glob(os.path.join(a.state, 'handoff', '*.json')), key=tid)
stats = {'taken': 0, 'ok': 0, 'failed': 0, 'dropped': 0}
for j in jobs:
    job = json.load(open(j))
    if a.drop_all:
        os.remove(j); stats['dropped'] += 1; continue
    time.sleep(a.delay)
    stats['taken'] += 1
    ev = {'session': job['session'], 'task': job['task'], 'status': 0, 'etag': None, 'error': None}
    path = job['file'].replace(cp, hp, 1) if cp else job['file']
    try:
        body = open(path, 'rb').read()  # upload-from-file: the file must still exist
        req = urllib.request.Request(job['url'], data=body, method='PUT')
        with urllib.request.urlopen(req) as r:
            ev['status'] = r.status; ev['etag'] = r.headers.get('ETag')
    except urllib.error.HTTPError as e:
        ev['status'] = e.code
    except FileNotFoundError:
        ev['error'] = 'NSURLErrorFileDoesNotExist (emulated)'
    stats['ok' if ev['status'] == 200 else 'failed'] += 1
    evp = os.path.join(a.state, 'events', os.path.basename(j))
    json.dump(ev, open(evp + '.tmp', 'w')); os.replace(evp + '.tmp', evp)
    if a.duplicate:
        json.dump(ev, open(evp.replace('.json', '.dup.json'), 'w'))
    os.remove(j)
print(json.dumps(stats))
