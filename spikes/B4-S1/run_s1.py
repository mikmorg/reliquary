#!/usr/bin/env python3
"""THROWAWAY SPIKE B4-S1 orchestrator (emulated iOS shell on Linux; not a device test).

Each scenario runs the Swift shell (UniFFI bindings -> Rust core) once per "wake" inside the
swift:6.1-noble container, then the mock transfer daemon on the host, then verifies the
reassembled, decrypted object against the SYN source. Writes evidence/results.json."""
import glob, hashlib, json, os, shutil, subprocess, sys, time

ROOT = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(ROOT, 'work'); STORE = os.path.join(WORK, 'r2store'); PORT = 18555
IMAGE = 'swift:6.1-noble'; SHELL = os.environ.get('SHELL_BIN', '/w/bin/shell-swift6')
MiB = 1 << 20
results = {'scenarios': {}, 'checks': []}

def check(name, cond, detail=''):
    results['checks'].append({'check': name, 'pass': bool(cond), 'detail': detail})
    print(('PASS ' if cond else 'FAIL ') + name + (' :: ' + str(detail) if detail else ''), flush=True)

def syn(path, size, seed):
    # SYN class: deterministic pseudo-random bytes (not a real photo)
    h = hashlib.sha256(seed.encode()).digest(); out = bytearray()
    while len(out) < size:
        h = hashlib.sha256(h).digest(); out += h * 64
    open(path, 'wb').write(bytes(out[:size]))

def cpath(p): return p.replace(ROOT, '/w', 1)

def wake(scen, extra=(), name=None, background=False):
    st = os.path.join(WORK, scen)
    cmd = ['docker', 'run', '--rm', '--network', 'none', '-v', f'{ROOT}:/w']
    if name: cmd += ['--name', name]
    cmd += [IMAGE, SHELL, '--state', cpath(st), '--src', cpath(os.path.join(st, 'src.bin')),
            '--port', str(PORT), *extra]
    if background:
        return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    r = subprocess.run(cmd, capture_output=True, text=True)
    line = [l for l in r.stdout.splitlines() if l.startswith('{')]
    if not line:
        return {'ok': False, 'raw': r.stdout[-2000:] + r.stderr[-2000:], 'rc': r.returncode}
    return json.loads(line[-1])

def daemon(scen, *flags):
    r = subprocess.run([sys.executable, os.path.join(ROOT, 'mock', 'nsurlsessiond_mock.py'),
                        '--state', os.path.join(WORK, scen), '--path-map', f'/w={ROOT}', *flags],
                       capture_output=True, text=True)
    return json.loads(r.stdout.strip().splitlines()[-1])

def verify(scen, upload_id):
    st = os.path.join(WORK, scen)
    r = subprocess.run([os.path.join(ROOT, 'target', 'release', 'verify'), os.path.join(st, 'core.sqlite'),
                        STORE, os.path.join(st, 'src.bin'), upload_id], capture_output=True, text=True)
    return json.loads(r.stdout)

def faults(lst): json.dump(lst, open(os.path.join(STORE, 'faults.json'), 'w'))

def setup(scen, size, seed):
    st = os.path.join(WORK, scen); os.makedirs(st, exist_ok=True)
    syn(os.path.join(st, 'src.bin'), size, seed); return st

def drive(scen, budget, max_wakes=40, first_extra=(), dflags=()):
    """Wake / transfer loop until complete. Returns the list of wake reports."""
    wakes = []
    for i in range(max_wakes):
        w = wake(scen, ['--budget', str(budget), *(first_extra if i == 0 else ())])
        w['daemon'] = daemon(scen, *dflags) if w.get('ok') else None
        wakes.append(w)
        if not w.get('ok'): break
        if w['status']['complete'] and not w['handed_off']: break
    # final wake applies the last events
    return wakes

def spool_dir(scen): return os.path.join(WORK, scen, 'spool')

def main():
    shutil.rmtree(WORK, ignore_errors=True); os.makedirs(STORE)
    srv = subprocess.Popen([sys.executable, os.path.join(ROOT, 'mock', 'mock_r2.py'), STORE, str(PORT)])
    time.sleep(0.5)
    try:
        run_all()
    finally:
        srv.terminate()
    results['summary'] = {'checks': len(results['checks']),
                          'passed': sum(c['pass'] for c in results['checks'])}
    os.makedirs(os.path.join(ROOT, 'evidence'), exist_ok=True)
    json.dump(results, open(os.path.join(ROOT, 'evidence', 'results.json'), 'w'), indent=1)
    print(json.dumps(results['summary']))
    sys.exit(0 if results['summary']['checks'] == results['summary']['passed'] else 1)

def run_all():
    faults([])
    PART_CT = 80 * (65536 + 16)  # 5,244,160 B, the T1 spike 2 default part size

    # A. happy path, spool budget of 2 parts per wake
    size = 40 * MiB + 12345; setup('A', size, 'A')
    budget = 2 * PART_CT
    wakes = drive('A', budget)
    uid = wakes[0]['upload_id']
    peak = max(w.get('spool_bytes_after', 0) for w in wakes)
    reads = [w['source_bytes_read'] for w in wakes if w.get('produced_parts')]
    results['scenarios']['A_happy_multiwake'] = {
        'source_bytes': size, 'spool_budget': budget, 'wakes': len(wakes),
        'parts_per_wake': [w.get('produced_parts') for w in wakes],
        'source_bytes_read_per_wake': [w.get('source_bytes_read') for w in wakes],
        'source_read_total_over_size': round(sum(reads) / size, 3),
        'peak_spool_bytes_after_produce': peak, 'produce_ms': [w.get('produce_ms') for w in wakes]}
    check('A: every wake ok', all(w.get('ok') for w in wakes), [w.get('error') for w in wakes if not w.get('ok')])
    check('A: spool never above budget', peak <= budget, f'peak {peak} budget {budget}')
    v = verify('A', uid); results['scenarios']['A_happy_multiwake']['verify'] = v
    check('A: reassembled + decrypted == source', v['ok'], v)
    check('A: spool empty at end', not os.listdir(spool_dir('A')))

    # B. cancellation mid-part (BGTask expiration / willTerminate)
    size = 30 * MiB; setup('B', size, 'B')
    w1 = wake('B', ['--budget', str(64 * MiB), '--cancel-after', str(7 * MiB)])
    tmp_left = [f for f in os.listdir(spool_dir('B')) if f.endswith('.tmp')]
    results['scenarios']['B_cancel'] = {'first_wake': w1}
    check('B: cancelled flag set', w1.get('cancelled') is True, w1)
    check('B: only whole parts committed (part 1)', w1.get('produced_parts') == [1], w1.get('produced_parts'))
    check('B: no torn .tmp left in spool', not tmp_left, tmp_left)
    check('B: cancel latency recorded', 'cancel_latency_us' in w1, w1.get('cancel_latency_us'))
    daemon('B')
    wakes = drive('B', 64 * MiB); uid = w1['upload_id']
    v = verify('B', uid); results['scenarios']['B_cancel']['verify'] = v
    check('B: completes after cancel', v['ok'], v)

    # C. SIGKILL while producing (jetsam / crash)
    size = 60 * MiB; setup('C', size, 'C')
    p = wake('C', ['--budget', str(128 * MiB)], name='b4s1kill', background=True)
    killed_with = None; t0 = time.time()
    while time.time() - t0 < 120:
        sp = spool_dir('C')
        if os.path.isdir(sp):
            fs = os.listdir(sp)
            if sum(f.endswith('.part') for f in fs) >= 2 and any(f.endswith('.tmp') for f in fs):
                subprocess.run(['docker', 'kill', '-s', 'KILL', 'b4s1kill'], capture_output=True)
                killed_with = sorted(fs); break
        if p.poll() is not None: break
        time.sleep(0.005)
    p.wait()
    results['scenarios']['C_sigkill'] = {'spool_at_kill': killed_with}
    check('C: killed mid-part (a .tmp existed)', killed_with is not None, killed_with)
    w2 = wake('C', ['--budget', str(128 * MiB)])
    tmp_left = [f for f in os.listdir(spool_dir('C')) if f.endswith('.tmp')]
    results['scenarios']['C_sigkill']['relaunch'] = w2
    check('C: relaunch ok, torn .tmp removed', w2.get('ok') and not tmp_left, (w2.get('error'), tmp_left))
    daemon('C'); drive('C', 128 * MiB)
    v = verify('C', w2['upload_id']); results['scenarios']['C_sigkill']['verify'] = v
    check('C: completes after SIGKILL', v['ok'], v)

    # D. transient 500 on part 3, then an expired presigned URL on a whole wake
    size = 25 * MiB; setup('D', size, 'D'); faults([{'part': 3, 'times': 1, 'status': 500}])
    w1 = wake('D', ['--budget', str(64 * MiB), '--ttl', '1'])
    d1 = daemon('D', '--delay', '0.6')  # tasks after ~1 s find the URL expired -> 403
    w2 = wake('D', ['--budget', str(64 * MiB)])
    results['scenarios']['D_failures'] = {'wake1': w1, 'daemon1': d1, 'wake2': w2}
    check('D: failures reported as events', w2.get('event_outcomes', {}).get('failed', 0) >= 1, w2.get('event_outcomes'))
    check('D: failed parts re-handed off with fresh URLs', len(w2.get('handed_off', [])) >= 1, w2.get('handed_off'))
    daemon('D'); drive('D', 64 * MiB); faults([])
    v = verify('D', w1['upload_id']); results['scenarios']['D_failures']['verify'] = v
    check('D: completes; re-uploads byte-identical', v['ok'] and v['part_numbers_with_conflicting_bodies'] == 0, v)

    # E. user force-quit: the system cancels every background task, no events arrive
    size = 20 * MiB; setup('E', size, 'E')
    w1 = wake('E', ['--budget', str(64 * MiB)]); d = daemon('E', '--drop-all')
    w2 = wake('E', ['--budget', str(64 * MiB)])
    results['scenarios']['E_force_quit'] = {'wake1': w1, 'daemon': d, 'wake2': w2}
    check('E: orphaned tasks reset on relaunch', w2.get('orphans_reset') == len(w1['handed_off']), (w2.get('orphans_reset'), w1.get('handed_off')))
    check('E: orphaned parts re-handed off', sorted(w2.get('handed_off', [])) == sorted(w1['handed_off']), w2.get('handed_off'))
    daemon('E'); drive('E', 64 * MiB)
    v = verify('E', w1['upload_id']); check('E: completes after force-quit', v['ok'], v)

    # F. duplicate event delivery
    size = 12 * MiB; setup('F', size, 'F')
    w1 = wake('F', ['--budget', str(64 * MiB)]); daemon('F', '--duplicate')
    w2 = wake('F', ['--budget', str(64 * MiB)])
    results['scenarios']['F_duplicates'] = {'wake2': w2}
    oc = w2.get('event_outcomes', {})
    check('F: duplicates detected, not double-counted', oc.get('duplicate') == len(w1['handed_off']) and w2['status']['complete'], oc)

    # G. spool purged after handoff (file-backed task finds no file) -> regenerate byte-identical
    size = 18 * MiB; setup('G', size, 'G'); faults([{'part': 1, 'times': 1, 'status': 500}])
    w1 = wake('G', ['--budget', str(64 * MiB)])
    daemon('G')  # part 1 PUT reaches the server (logged) but gets 500; others succeed
    for f in os.listdir(spool_dir('G')): os.remove(os.path.join(spool_dir('G'), f))  # purge
    w2 = wake('G', ['--budget', str(64 * MiB)])  # records results; open() marks part 1 missing -> regenerated
    results['scenarios']['G_purge_regen'] = {'wake1': w1, 'wake2': w2}
    check('G: purged part regenerated', 1 in w2.get('produced_parts', []), w2.get('produced_parts'))
    daemon('G'); drive('G', 64 * MiB); faults([])
    v = verify('G', w1['upload_id']); results['scenarios']['G_purge_regen']['verify'] = v
    check('G: regenerated part byte-identical to first attempt', v['ok'] and v['server_put_attempts'] > w1['status']['n_parts'], v)

    # H. purge + source changed -> refuse to re-encrypt (keystream-reuse guard at part level)
    size = 18 * MiB; st = setup('H', size, 'H'); faults([{'part': 2, 'times': 1, 'status': 500}])
    w1 = wake('H', ['--budget', str(64 * MiB)]); daemon('H')
    for f in os.listdir(spool_dir('H')): os.remove(os.path.join(spool_dir('H'), f))
    with open(os.path.join(st, 'src.bin'), 'r+b') as fh:  # edit a byte inside part 2
        fh.seek(6 * MiB); b = fh.read(1); fh.seek(6 * MiB); fh.write(bytes([b[0] ^ 1]))
    w2 = wake('H', ['--budget', str(64 * MiB)]); faults([])
    results['scenarios']['H_source_changed'] = {'wake2': w2}
    check('H: SourceChanged raised, nothing re-encrypted', (not w2.get('ok')) and 'SourceChanged' in w2.get('error', ''), w2.get('error'))
    check('H: no part 2 ciphertext left in spool', not [f for f in os.listdir(spool_dir('H')) if '.00002.' in f])

    # I. boundaries: 0 B, 1 B, exactly 2 parts
    for nm, sz in (('I0', 0), ('I1', 1), ('I2', 2 * 80 * 65536)):
        setup(nm, sz, nm); ws = drive(nm, 64 * MiB)
        v = verify(nm, ws[0]['upload_id']); check(f'{nm}: size {sz} round-trips', v['ok'], v)

    # DB size after all runs (scenario A)
    results['scenarios']['A_happy_multiwake']['db_bytes'] = sum(
        os.path.getsize(f) for f in glob.glob(os.path.join(WORK, 'A', 'core.sqlite*')))

if __name__ == '__main__':
    main()
