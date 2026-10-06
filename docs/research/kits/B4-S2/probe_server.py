#!/usr/bin/env python3
"""Kit B4-S2 probe server. Logs what an iPhone actually sends; for LAN use during the kit.

  python3 probe_server.py --port 8080 --dir ./probe-out [--options 501|200|404] [--send-104]

- Logs every request (method, path, query, headers; Authorization/X-Amz-Signature redacted) to
  <dir>/requests.jsonl, and saves each body to <dir>/bodies/<n>.bin with its SHA-256 and length.
- OPTIONS answers --options (default 501 = "no resumable uploads"); 200 adds Upload-Limit.
- PUT/POST/PATCH answer 200/201 with ETag = quoted MD5 of the body (the S3 convention).
- --send-104 sends "104 Upload Resumption Supported" with a Location header before reading the
  body, to see whether the PhotoKit extension switches to the IETF resumable-upload flow.
  This is only a probe; it does not implement the resumable protocol (offsets, HEAD, PATCH append).

Only LAB/SYN content may be sent to it (the PhotoKit extension uploads raw, unencrypted bytes).
"""
import argparse, hashlib, json, os, threading, time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

ap = argparse.ArgumentParser()
ap.add_argument('--port', type=int, default=8080)
ap.add_argument('--dir', default='probe-out')
ap.add_argument('--options', type=int, default=501, choices=[200, 404, 501])
ap.add_argument('--send-104', action='store_true')
A = ap.parse_args()
os.makedirs(os.path.join(A.dir, 'bodies'), exist_ok=True)
LOCK = threading.Lock(); N = [0]
REDACT = {'authorization', 'x-amz-signature', 'cookie'}


def log(entry):
    with LOCK, open(os.path.join(A.dir, 'requests.jsonl'), 'a') as f:
        f.write(json.dumps(entry) + '\n')


class H(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, *a):
        pass

    def _entry(self):
        u = urlparse(self.path)
        q = '&'.join(p if not p.lower().startswith('x-amz-signature') else 'X-Amz-Signature=REDACTED'
                     for p in u.query.split('&')) if u.query else ''
        return {'t': time.time(), 'client': self.client_address[0], 'method': self.command, 'path': u.path,
                'query': q, 'headers': {k: ('REDACTED' if k.lower() in REDACT else v) for k, v in self.headers.items()}}

    def do_OPTIONS(self):
        e = self._entry(); e['answer'] = A.options; log(e)
        self.send_response(A.options)
        if A.options == 200:
            self.send_header('Upload-Limit', 'max-size=107374182400')
        self.send_header('Content-Length', '0'); self.end_headers()

    def _body(self):
        e = self._entry()
        with LOCK:
            N[0] += 1; n = N[0]
        if A.send_104:
            loc = f'http://{self.headers.get("Host", "localhost")}/resume/{n}'
            self.wfile.write(f'HTTP/1.1 104 Upload Resumption Supported\r\nLocation: {loc}\r\n\r\n'.encode())
            self.wfile.flush(); e['sent_104'] = True
        h, m, total = hashlib.sha256(), hashlib.md5(), 0
        path = os.path.join(A.dir, 'bodies', f'{n:05}.bin')
        with open(path, 'wb') as f:
            if 'chunked' in self.headers.get('Transfer-Encoding', '').lower():
                while True:
                    size = int(self.rfile.readline().split(b';')[0].strip(), 16)
                    if size == 0:
                        self.rfile.readline(); break
                    b = self.rfile.read(size); self.rfile.readline()
                    f.write(b); h.update(b); m.update(b); total += len(b)
            else:
                left = int(self.headers.get('Content-Length', '0'))
                while left:
                    b = self.rfile.read(min(left, 1 << 20))
                    if not b:
                        break
                    f.write(b); h.update(b); m.update(b); total += len(b); left -= len(b)
        e.update({'body_file': path, 'body_len': total, 'body_sha256': h.hexdigest()})
        log(e)
        self.send_response(201 if self.command == 'POST' else 200)
        self.send_header('ETag', '"%s"' % m.hexdigest())
        self.send_header('X-Probe-Request', str(n))
        self.send_header('Content-Length', '0'); self.end_headers()

    do_PUT = do_POST = do_PATCH = _body

    def do_HEAD(self):
        log(self._entry()); self.send_response(404); self.send_header('Content-Length', '0'); self.end_headers()

    do_GET = do_HEAD


print(f'probe server on :{A.port}, OPTIONS -> {A.options}, 104 -> {A.send_104}, logging to {A.dir}', flush=True)
ThreadingHTTPServer(('0.0.0.0', A.port), H).serve_forever()
