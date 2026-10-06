#!/usr/bin/env python3
"""THROWAWAY SPIKE B4-S1: mock of an R2 presigned UploadPart endpoint (emulated, not real R2).
PUT /<upload_id>/<part>?exp=<unix> stores the body; ETag = quoted MD5 (S3 convention; R2 unverified).
Expired URL -> 403. Faults from <store>/faults.json: [{"part": 3, "times": 1, "status": 500}].
Every attempt (including failed ones) is logged with the body SHA-256 to <store>/attempts.jsonl."""
import hashlib, json, os, sys, threading, time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

STORE = sys.argv[1]; PORT = int(sys.argv[2])
lock = threading.Lock()

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_PUT(self):
        u = urlparse(self.path); upload_id, part = u.path.strip('/').split('/')
        n = int(self.headers.get('Content-Length', '0')); body = self.rfile.read(n)
        exp = int(parse_qs(u.query).get('exp', ['0'])[0])
        status = 200
        with lock:
            fp = os.path.join(STORE, 'faults.json')
            faults = json.load(open(fp)) if os.path.exists(fp) else []
            for f in faults:
                if f['part'] == int(part) and f.get('times', 0) > 0:
                    f['times'] -= 1; status = f['status']; break
            json.dump(faults, open(fp, 'w'))
            if time.time() > exp: status = 403
            with open(os.path.join(STORE, 'attempts.jsonl'), 'a') as log:
                log.write(json.dumps({'upload_id': upload_id, 'part': int(part), 'len': len(body),
                                      'sha256': hashlib.sha256(body).hexdigest(), 'status': status}) + '\n')
            if status == 200:
                d = os.path.join(STORE, upload_id); os.makedirs(d, exist_ok=True)
                tmp = os.path.join(d, f'{int(part):05}.tmp'); open(tmp, 'wb').write(body)
                os.replace(tmp, os.path.join(d, f'{int(part):05}.bin'))
        self.send_response(status)
        if status == 200: self.send_header('ETag', '"%s"' % hashlib.md5(body).hexdigest())
        self.send_header('Content-Length', '0'); self.end_headers()

os.makedirs(STORE, exist_ok=True)
ThreadingHTTPServer(('127.0.0.1', PORT), H).serve_forever()
