#!/usr/bin/env python3
"""Kit B4-S2 presign helper: stands in for the Worker on the owner's LAN during the kit.

  pip install boto3
  export R2_ENDPOINT=https://<ACCOUNT_ID>.r2.cloudflarestorage.com   # SANDBOX account only (H1)
  export R2_BUCKET=<sandbox bucket>  R2_ACCESS_KEY_ID=...  R2_SECRET_ACCESS_KEY=...
  python3 presign_parts.py serve --port 8081 --ttl 900

The phone asks  GET /presign?upload=<core upload_id>&part=<n>   -> text/plain presigned UploadPart URL
and finally     POST /complete?upload=<core upload_id>  body {"1": "<etag>", ...}  -> CompleteMultipartUpload
                GET /parts?upload=<core upload_id>      -> ListParts result (JSON), to compare ETags
Credentials are read from the environment and never printed (SEC class). The Worker replaces this
helper in the real design; this only exists so the phone can talk to sandbox R2 in the kit.
"""
import json, os, sys, threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

import boto3
from botocore.config import Config

S3 = boto3.client('s3', endpoint_url=os.environ['R2_ENDPOINT'], region_name=os.environ.get('R2_REGION', 'auto'),
                  aws_access_key_id=os.environ['R2_ACCESS_KEY_ID'],
                  aws_secret_access_key=os.environ['R2_SECRET_ACCESS_KEY'],
                  config=Config(signature_version='s3v4', s3={'addressing_style': 'path'}))
BUCKET = os.environ['R2_BUCKET']
TTL = 900
LOCK = threading.Lock()
UPLOADS = {}  # core upload_id -> (object key, S3 UploadId); kept in memory: restart = new uploads


def s3_upload(core_id):
    with LOCK:
        if core_id not in UPLOADS:
            key = f'b4s2/{core_id}'
            r = S3.create_multipart_upload(Bucket=BUCKET, Key=key)
            UPLOADS[core_id] = (key, r['UploadId'])
        return UPLOADS[core_id]


class H(BaseHTTPRequestHandler):
    def log_message(self, fmt, *a):
        sys.stderr.write('%s %s\n' % (self.command, urlparse(self.path).path))

    def _reply(self, code, body, ctype='text/plain'):
        b = body.encode()
        self.send_response(code); self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(b))); self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        u = urlparse(self.path); q = {k: v[0] for k, v in parse_qs(u.query).items()}
        key, uid = s3_upload(q['upload'])
        if u.path == '/presign':
            url = S3.generate_presigned_url('upload_part', ExpiresIn=TTL, HttpMethod='PUT',
                                            Params={'Bucket': BUCKET, 'Key': key, 'UploadId': uid,
                                                    'PartNumber': int(q['part'])})
            return self._reply(200, url)
        if u.path == '/parts':
            r = S3.list_parts(Bucket=BUCKET, Key=key, UploadId=uid)
            return self._reply(200, json.dumps([{'part': p['PartNumber'], 'etag': p['ETag'], 'size': p['Size']}
                                                for p in r.get('Parts', [])]), 'application/json')
        self._reply(404, 'no')

    def do_POST(self):
        u = urlparse(self.path); q = {k: v[0] for k, v in parse_qs(u.query).items()}
        if u.path != '/complete':
            return self._reply(404, 'no')
        key, uid = s3_upload(q['upload'])
        etags = json.loads(self.rfile.read(int(self.headers.get('Content-Length', '0'))))
        parts = [{'PartNumber': int(n), 'ETag': e if e.startswith('"') else f'"{e}"'}
                 for n, e in sorted(etags.items(), key=lambda kv: int(kv[0]))]
        r = S3.complete_multipart_upload(Bucket=BUCKET, Key=key, UploadId=uid, MultipartUpload={'Parts': parts})
        self._reply(200, json.dumps({'key': key, 'etag': r.get('ETag')}), 'application/json')


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument('cmd', choices=['serve'])
    ap.add_argument('--port', type=int, default=8081); ap.add_argument('--ttl', type=int, default=900)
    a = ap.parse_args(); TTL = a.ttl
    print(f'presign helper on :{a.port}, ttl {TTL}s, bucket {BUCKET}', flush=True)
    ThreadingHTTPServer(('0.0.0.0', a.port), H).serve_forever()
