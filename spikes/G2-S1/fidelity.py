#!/usr/bin/env python3
"""G2-S1 R2 fidelity script (throwaway research code, stdlib only).

Runs the same presigned-multipart and conditional-create checks against any S3-compatible
endpoint: Miniflare's local R2 S3 endpoint, SeaweedFS, versitygw, Garage, moto, s3s-fs, and
(in the SB kit) real R2 at https://<ACCOUNT_ID>.r2.cloudflarestorage.com.

It uses its own SigV4 signer so that every target gets byte-identical requests and so that
tampering, expiry and unsigned-header cases can be constructed exactly.

Usage:
  python3 fidelity.py --name miniflare --endpoint http://127.0.0.1:8787/cdn-cgi/local/r2/s3 \
      --bucket staging --ak AK --sk SK [--region auto] [--worker http://127.0.0.1:8787] \
      [--out results/miniflare.json] [--only T14,T18]

Data-handling class: SYN -> results (random bytes only).
"""
import argparse, base64, concurrent.futures as cf, datetime as dt, hashlib, hmac, http.client
import json, os, re, socket, sys, time, urllib.parse, uuid

MiB = 1024 * 1024
T26_EXPECT = '[doc: r2/platform/limits.mdx] at most 1 concurrent write/s per key, excess -> HTTP 429; so on R2 expect exactly one 200 and losers as 412 OR 429'
UNSIGNED = "UNSIGNED-PAYLOAD"


def q(s, safe="-_.~"):
    return urllib.parse.quote(s, safe=safe)


class S3:
    def __init__(self, endpoint, bucket, ak, sk, region="auto", timeout=60):
        u = urllib.parse.urlsplit(endpoint)
        self.scheme, self.host, self.base_path = u.scheme, u.netloc, u.path.rstrip("/")
        self.bucket, self.ak, self.sk, self.region, self.timeout = bucket, ak, sk, region, timeout

    # --- SigV4 -------------------------------------------------------------------------
    def path(self, key=None):
        p = f"{self.base_path}/{q(self.bucket)}"
        if key is not None:
            p += "/" + q(key, safe="-_.~/")
        return p

    def _key(self, date):
        k = hmac.new(("AWS4" + self.sk).encode(), date.encode(), hashlib.sha256).digest()
        for part in (self.region, "s3", "aws4_request"):
            k = hmac.new(k, part.encode(), hashlib.sha256).digest()
        return k

    @staticmethod
    def _cq(params):
        return "&".join(f"{q(k)}={q(str(v))}" for k, v in sorted(params.items()))

    def _sign(self, method, path, params, headers, signed, payload_hash, amzdate, sk=None):
        ch = "".join(f"{h}:{' '.join(str(headers[h]).split())}\n" for h in signed)
        creq = "\n".join([method, path, self._cq(params), ch, ";".join(signed), payload_hash])
        scope = f"{amzdate[:8]}/{self.region}/s3/aws4_request"
        sts = "\n".join(["AWS4-HMAC-SHA256", amzdate, scope, hashlib.sha256(creq.encode()).hexdigest()])
        key = self._key(amzdate[:8]) if sk is None else S3(f"{self.scheme}://{self.host}", self.bucket, self.ak, sk, self.region)._key(amzdate[:8])
        return hmac.new(key, sts.encode(), hashlib.sha256).hexdigest(), scope

    def presign(self, method, key, expires=900, params=None, sign_headers=None, now=None, ak=None):
        """Return (path_with_query, headers_that_must_be_sent)."""
        now = now or dt.datetime.now(dt.timezone.utc)
        amzdate = now.strftime("%Y%m%dT%H%M%SZ")
        params = dict(params or {})
        hdrs = {"host": self.host}
        for k, v in (sign_headers or {}).items():
            hdrs[k.lower()] = v
        signed = sorted(hdrs)
        params.update({
            "X-Amz-Algorithm": "AWS4-HMAC-SHA256",
            "X-Amz-Credential": f"{ak or self.ak}/{amzdate[:8]}/{self.region}/s3/aws4_request",
            "X-Amz-Date": amzdate,
            "X-Amz-Expires": str(expires),
            "X-Amz-SignedHeaders": ";".join(signed),
        })
        path = self.path(key)
        sig, _ = self._sign(method, path, params, hdrs, signed, UNSIGNED, amzdate)
        params["X-Amz-Signature"] = sig
        send = {k: v for k, v in hdrs.items() if k != "host"}
        return path + "?" + self._cq(params), send

    def signed_headers(self, method, key, params=None, headers=None, body=b"", skew=0, sk=None, ak=None,
                       payload_hash=None, sign_extra=True):
        now = dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=skew)
        amzdate = now.strftime("%Y%m%dT%H%M%SZ")
        ph = payload_hash or hashlib.sha256(body).hexdigest()
        hdrs = {"host": self.host, "x-amz-date": amzdate, "x-amz-content-sha256": ph}
        extra = {k.lower(): v for k, v in (headers or {}).items()}
        if sign_extra:
            hdrs.update(extra)
        signed = sorted(hdrs)
        path = self.path(key)
        sig, scope = self._sign(method, path, params or {}, hdrs, signed, ph, amzdate, sk=sk)
        out = {k: v for k, v in hdrs.items() if k != "host"}
        out.update(extra)
        out["authorization"] = (f"AWS4-HMAC-SHA256 Credential={ak or self.ak}/{scope}, "
                                f"SignedHeaders={';'.join(signed)}, Signature={sig}")
        qs = ("?" + self._cq(params)) if params else ""
        return path + qs, out

    # --- transport ---------------------------------------------------------------------
    requests_sent = 0
    bytes_sent = 0

    def raw(self, method, pathq, headers=None, body=b""):
        S3.requests_sent += 1
        S3.bytes_sent += len(body or b"")
        C = http.client.HTTPSConnection if self.scheme == "https" else http.client.HTTPConnection
        c = C(self.host, timeout=self.timeout)
        try:
            h = dict(headers or {})
            if body or method in ("PUT", "POST"):
                h.setdefault("content-length", str(len(body)))
            c.request(method, pathq, body=body if body else None, headers=h)
            r = c.getresponse()
            data = r.read()
            return r.status, {k.lower(): v for k, v in r.getheaders()}, data
        finally:
            c.close()

    def call(self, method, key=None, params=None, headers=None, body=b"", **kw):
        pq, h = self.signed_headers(method, key, params=params, headers=headers, body=body, **kw)
        return self.raw(method, pq, h, body)

    def call_presigned(self, method, key, body=b"", expires=900, params=None, sign_headers=None,
                       extra_headers=None, tamper=None, send_method=None, send_key=None, now=None):
        pq, h = self.presign(method, key, expires, params, sign_headers, now=now)
        if tamper:
            pq = tamper(pq)
        if send_key is not None:
            pq = pq.replace(self.path(key) + "?", self.path(send_key) + "?", 1)
        h.update(extra_headers or {})
        return self.raw(send_method or method, pq, h, body)


def err_code(body):
    m = re.search(rb"<Code>([^<]+)</Code>", body or b"")
    return m.group(1).decode() if m else None


def obs(status, body=b"", **extra):
    o = {"status": status, "code": err_code(body) if status >= 300 else None}
    o.update(extra)
    return o


def etag_of(h):
    return h.get("etag")


class Runner:
    def __init__(self, s3, name, worker=None):
        self.s3, self.name, self.worker = s3, name, worker
        self.run_id = uuid.uuid4().hex[:8]
        self.results = []

    def k(self, suffix):
        return f"g2s1/{self.run_id}/{suffix}"

    def rec(self, tid, title, observed, expect_r2=None, note=None):
        self.results.append({"id": tid, "title": title, "observed": observed,
                             "r2_documented": expect_r2, "note": note})
        print(f"[{self.name}] {tid} {title}: {json.dumps(observed)}", flush=True)

    # ---------------------------------------------------------------------------------
    def put(self, key, data, **kw):
        return self.s3.call("PUT", key, body=data, **kw)

    def get_sha(self, key):
        st, h, b = self.s3.call("GET", key)
        return st, (hashlib.sha256(b).hexdigest() if st == 200 else None), len(b)

    def mpu_create(self, key, headers=None):
        st, h, b = self.s3.call("POST", key, params={"uploads": ""}, headers=headers)
        m = re.search(rb"<UploadId>([^<]+)</UploadId>", b)
        return st, (m.group(1).decode() if m else None), b

    def part_presigned(self, key, upload_id, n, data):
        st, h, b = self.s3.call_presigned("PUT", key, body=data, params={"partNumber": str(n), "uploadId": upload_id})
        return st, etag_of(h), b

    def mpu_complete(self, key, upload_id, parts, headers=None):
        xml = "<CompleteMultipartUpload>" + "".join(
            f"<Part><PartNumber>{n}</PartNumber><ETag>{e}</ETag></Part>" for n, e in parts) + "</CompleteMultipartUpload>"
        return self.s3.call("POST", key, params={"uploadId": upload_id}, body=xml.encode(), headers=headers)

    def mpu(self, key, sizes, complete_headers=None):
        st, uid, b = self.mpu_create(key)
        if st != 200:
            return {"create": obs(st, b)}, None, None
        parts, blobs = [], []
        for i, sz in enumerate(sizes, 1):
            d = os.urandom(sz)
            blobs.append(d)
            pst, e, pb = self.part_presigned(key, uid, i, d)
            if pst != 200:
                return {"part": i, **obs(pst, pb)}, uid, None
            parts.append((i, e))
        cst, ch, cb = self.mpu_complete(key, uid, parts, complete_headers)
        return {"complete": obs(cst, cb)}, uid, hashlib.sha256(b"".join(blobs)).hexdigest()

    # ---------------------------------------------------------------------------------
    def t_basic(self):
        s3 = self.s3
        d = os.urandom(1024)
        st, h, b = self.put(self.k("t01"), d)
        g = self.get_sha(self.k("t01"))
        self.rec("T01", "PutObject (header SigV4) then GetObject round-trip",
                 obs(st, b, roundtrip=g[1] == hashlib.sha256(d).hexdigest()), "200; round-trip")
        d = os.urandom(2048)
        st, h, b = s3.call_presigned("PUT", self.k("t02"), body=d)
        g = self.get_sha(self.k("t02"))
        self.rec("T02", "Presigned PUT then header GET round-trip",
                 obs(st, b, roundtrip=g[1] == hashlib.sha256(d).hexdigest()), "200; round-trip")
        st, h, b = s3.call_presigned("GET", self.k("t02"))
        st2, h2, b2 = s3.call_presigned("HEAD", self.k("t02"))
        self.rec("T03", "Presigned GET and HEAD", {"get": obs(st, b, ok=b == d), "head": obs(st2, b2)}, "200 / 200")
        st, h, b = s3.call_presigned("PUT", self.k("t04"), body=b"x",
                                     tamper=lambda p: re.sub(r"X-Amz-Signature=([0-9a-f])", lambda m: "X-Amz-Signature=" + ("0" if m.group(1) != "0" else "1"), p))
        self.rec("T04", "Presigned PUT with tampered signature", obs(st, b), "403 SignatureDoesNotMatch")
        st, h, b = s3.call_presigned("PUT", self.k("t05a"), body=b"x", send_key=self.k("t05b"))
        self.rec("T05", "Presigned PUT URL replayed against a different key", obs(st, b), "403 SignatureDoesNotMatch")
        st, h, b = s3.call_presigned("PUT", self.k("t02"), send_method="GET")
        self.rec("T06", "Presigned PUT URL used with GET", obs(st, b), "403 SignatureDoesNotMatch")
        st, h, b = s3.call_presigned("PUT", self.k("t07"), body=b"x",
                                     tamper=lambda p: p.replace("X-Amz-Expires=900", "X-Amz-Expires=3600"))
        self.rec("T07", "Presigned URL with expiry changed after signing", obs(st, b), "403 SignatureDoesNotMatch")
        pq, hh = s3.presign("PUT", self.k("t08"), expires=1)
        time.sleep(2.5)
        st, h, b = s3.raw("PUT", pq, hh, b"x")
        self.rec("T08", "Presigned PUT used after X-Amz-Expires=1 elapsed", obs(st, b), "403 (expired)")
        st, h, b = s3.call_presigned("PUT", self.k("t09a"), body=b"x", expires=604800)
        st2, h2, b2 = s3.call_presigned("PUT", self.k("t09b"), body=b"x", expires=604801)
        self.rec("T09", "X-Amz-Expires=604800 vs 604801",
                 {"604800": obs(st, b), "604801": obs(st2, b2)}, "604800 allowed (1 s-7 days); >604800 rejected")
        pq, hh = s3.presign("PUT", self.k("t10"))
        r1 = s3.raw("PUT", pq, hh, b"first")
        r2 = s3.raw("PUT", pq, hh, b"second")
        g = s3.call("GET", self.k("t10"))
        self.rec("T10", "Same presigned PUT URL used twice before expiry",
                 {"first": obs(r1[0], r1[2]), "second": obs(r2[0], r2[2]), "stored": g[2].decode(errors="replace")},
                 "reusable until expiry (both 200, last write wins)")
        st, h, b = s3.call_presigned("PUT", self.k("t11"), body=b"x", sign_headers={"content-type": "application/octet-stream"},
                                     extra_headers={"content-type": "image/jpeg"})
        st2, h2, b2 = s3.call_presigned("PUT", self.k("t11"), body=b"x", sign_headers={"content-type": "application/octet-stream"})
        self.rec("T11", "Presigned PUT with signed Content-Type: mismatch vs match",
                 {"mismatch": obs(st, b), "match": obs(st2, b2)}, "mismatch 403; match 200")
        st, h, b = self.put(self.k("t12"), b"x", skew=20 * 60)
        self.rec("T12", "Header-auth request with clock 20 min ahead", obs(st, b), "[unverified] 403 RequestTimeTooSkewed (Miniflare says it mirrors a 2026-06-11 R2 capture)")
        st, h, b = self.put(self.k("t13"), b"x", sk="wrong-secret")
        st2, h2, b2 = self.put(self.k("t13"), b"x", ak="UNKNOWNACCESSKEY")
        self.rec("T13", "Wrong secret key vs unknown access key",
                 {"wrong_secret": obs(st, b), "unknown_ak": obs(st2, b2)}, "[unverified] 403 SignatureDoesNotMatch / 401 Unauthorized (per Miniflare's R2 capture)")
        st, h, b = s3.call("GET", self.k("does-not-exist"))
        self.rec("T14", "GetObject on missing key", obs(st, b), "404 NoSuchKey")

    def t_conditional(self):
        s3 = self.s3
        key = self.k("c01")
        st1, h1, b1 = self.put(key, b"one", headers={"if-none-match": "*"})
        st2, h2, b2 = self.put(key, b"two", headers={"if-none-match": "*"})
        g = s3.call("GET", key)
        self.rec("T20", "PutObject If-None-Match:* on absent then existing key",
                 {"absent": obs(st1, b1), "existing": obs(st2, b2), "stored": g[2].decode(errors="replace")},
                 "200 then 412 PreconditionFailed; stored 'one'")
        st, h, b = self.put(key, b"three", headers={"if-match": '"0123456789abcdef0123456789abcdef"'})
        st2, h2, b2 = self.put(key, b"four", headers={"if-match": etag_of(h1) or '""'})
        self.rec("T21", "PutObject If-Match wrong ETag vs correct ETag",
                 {"wrong": obs(st, b), "correct": obs(st2, b2)}, "412 / 200")
        # presigned + conditional header NOT in SignedHeaders (A3 open question 2)
        st, h, b = s3.call_presigned("PUT", key, body=b"five", extra_headers={"if-none-match": "*"})
        g = s3.call("GET", key)
        self.rec("T22", "Presigned PUT, If-None-Match:* sent but NOT signed, key exists",
                 {**obs(st, b), "stored": g[2].decode(errors="replace")},
                 "undocumented (A3 open question 2) -> SB leg")
        st, h, b = s3.call_presigned("PUT", key, body=b"six", sign_headers={"if-none-match": "*"})
        g = s3.call("GET", key)
        self.rec("T23", "Presigned PUT, If-None-Match:* signed (in X-Amz-SignedHeaders), key exists",
                 {**obs(st, b), "stored": g[2].decode(errors="replace")}, "412 expected (PutObject supports If-None-Match)")
        k2 = self.k("c02")
        st, h, b = s3.call_presigned("PUT", k2, body=b"seven", sign_headers={"if-none-match": "*"})
        self.rec("T24", "Presigned PUT, If-None-Match:* signed, key absent", obs(st, b), "200")
        st, h, b = s3.call_presigned("PUT", k2, body=b"eight", sign_headers={"if-none-match": "*"}, extra_headers={"if-none-match": "abc"},
                                     )
        self.rec("T25", "Presigned PUT with signed If-None-Match value changed by client", obs(st, b), "403 SignatureDoesNotMatch")

    def t_race(self, rounds=20, n=16):
        wins = []
        errors = {}
        for r in range(rounds):
            key = self.k(f"race/{r}")
            def one(i):
                st, h, b = self.put(key, f"writer-{i}".encode(), headers={"if-none-match": "*"})
                return st, err_code(b)
            with cf.ThreadPoolExecutor(n) as ex:
                res = list(ex.map(one, range(n)))
            w = sum(1 for s, _ in res if s == 200)
            wins.append(w)
            for s, c in res:
                if s != 200:
                    errors[f"{s} {c}"] = errors.get(f"{s} {c}", 0) + 1
        self.rec("T26", f"Race: {n} concurrent header-auth PutObject If-None-Match:* on one fresh key, {rounds} rounds",
                 {"winners_per_round": wins, "rounds_with_exactly_one_winner": sum(1 for w in wins if w == 1), "loser_responses": errors},
                 T26_EXPECT)
        # same, via presigned URLs with signed If-None-Match
        wins = []
        errors = {}
        for r in range(rounds):
            key = self.k(f"race-presigned/{r}")
            urls = [self.s3.presign("PUT", key, sign_headers={"if-none-match": "*"}) for _ in range(n)]
            def one(i):
                pq, hh = urls[i]
                st, h, b = self.s3.raw("PUT", pq, hh, f"writer-{i}".encode())
                return st, err_code(b)
            with cf.ThreadPoolExecutor(n) as ex:
                res = list(ex.map(one, range(n)))
            w = sum(1 for s, _ in res if s == 200)
            wins.append(w)
            for s, c in res:
                if s != 200:
                    errors[f"{s} {c}"] = errors.get(f"{s} {c}", 0) + 1
        self.rec("T27", f"Race: {n} concurrent presigned PUT (signed If-None-Match:*) on one fresh key, {rounds} rounds",
                 {"winners_per_round": wins, "rounds_with_exactly_one_winner": sum(1 for w in wins if w == 1), "loser_responses": errors},
                 T26_EXPECT)

    def t_multipart(self):
        s3 = self.s3
        key = self.k("m01")
        r, uid, sha = self.mpu(key, [5 * MiB, 5 * MiB, 1 * MiB])
        st, gsha, n = self.get_sha(key)
        hst, hh, _ = s3.call("HEAD", key)
        self.rec("T30", "Presigned multipart 5+5+1 MiB, Complete via header auth",
                 {**r, "get_sha_match": gsha == sha, "size": n, "etag": hh.get("etag")}, "200; content matches; ETag '-3' suffix")
        r, uid, sha = self.mpu(self.k("m02"), [1 * MiB, 1 * MiB])
        self.rec("T31", "Multipart with non-last part < 5 MiB (1+1 MiB)", r, "400 EntityTooSmall")
        r, uid, sha = self.mpu(self.k("m03"), [5 * MiB, 6 * MiB, 1 * MiB])
        self.rec("T32", "Multipart with unequal non-last parts (5+6+1 MiB)", r,
                 "R2: all parts except last must be the same size (error expected); AWS: allowed")
        r, uid, sha = self.mpu(self.k("m04"), [5 * MiB, 6 * MiB])
        self.rec("T33", "Multipart with last part larger than the others (5+6 MiB)", r,
                 "R2: last part must not be larger (error expected); AWS: allowed")
        # re-upload part number
        key = self.k("m05")
        st, uid, b = self.mpu_create(key)
        d1, d1b, d2 = os.urandom(5 * MiB), os.urandom(5 * MiB), os.urandom(1024)
        _, e1, _ = self.part_presigned(key, uid, 1, d1)
        _, e1b, _ = self.part_presigned(key, uid, 1, d1b)
        _, e2, _ = self.part_presigned(key, uid, 2, d2)
        c_old = self.mpu_complete(key, uid, [(1, e1), (2, e2)])
        c_new = self.mpu_complete(key, uid, [(1, e1b), (2, e2)])
        st, gsha, n = self.get_sha(key)
        self.rec("T34", "Re-upload part 1, Complete with the stale ETag then the new ETag",
                 {"stale_complete": obs(c_old[0], c_old[2]), "new_complete": obs(c_new[0], c_new[2]),
                  "content_is_new": gsha == hashlib.sha256(d1b + d2).hexdigest()},
                 "stale -> 400 InvalidPart; new -> 200 (same part number replaces the previous part)")
        # T34b: stale ETag only, then inspect what was stored
        key = self.k("m05b")
        st, uid, b = self.mpu_create(key)
        d1, d1b, d2 = os.urandom(5 * MiB), os.urandom(5 * MiB), os.urandom(1024)
        _, e1, _ = self.part_presigned(key, uid, 1, d1)
        _, e1b, _ = self.part_presigned(key, uid, 1, d1b)
        _, e2, _ = self.part_presigned(key, uid, 2, d2)
        c_old = self.mpu_complete(key, uid, [(1, e1), (2, e2)])
        st, gsha, n = self.get_sha(key)
        stored = ("old_part" if gsha == hashlib.sha256(d1 + d2).hexdigest() else
                  "new_part" if gsha == hashlib.sha256(d1b + d2).hexdigest() else ("absent" if st == 404 else "other"))
        self.rec("T34b", "Re-upload part 1, Complete citing ONLY the stale part-1 ETag; what is stored?",
                 {"complete": obs(c_old[0], c_old[2]), "stored": stored, "etags_differ": e1 != e1b},
                 "stale ETag -> 400 InvalidPart; nothing stored")
        # ListParts / ListMultipartUploads
        key = self.k("m06")
        st, uid, b = self.mpu_create(key)
        _, e1, _ = self.part_presigned(key, uid, 1, os.urandom(5 * MiB))
        lp = s3.call("GET", key, params={"uploadId": uid})
        lmu = s3.call("GET", None, params={"uploads": ""})
        self.rec("T35", "ListParts and ListMultipartUploads on an open upload",
                 {"list_parts": obs(lp[0], lp[2], has_part1=(e1 or "").strip('"').encode() in lp[2] if lp[0] == 200 else None),
                  "list_uploads": obs(lmu[0], lmu[2], has_upload=uid.encode() in lmu[2] if lmu[0] == 200 else None)},
                 "R2 implements both (200)")
        # abort then upload part
        ab = s3.call("DELETE", key, params={"uploadId": uid})
        pst, pe, pb = self.part_presigned(key, uid, 2, os.urandom(1024))
        self.rec("T36", "AbortMultipartUpload, then UploadPart to the aborted upload",
                 {"abort": obs(ab[0], ab[2]), "part_after_abort": obs(pst, pb)}, "204; then 404 NoSuchUpload")
        # complete twice / part after complete
        key = self.k("m07")
        st, uid, b = self.mpu_create(key)
        _, e1, _ = self.part_presigned(key, uid, 1, os.urandom(1024))
        c1 = self.mpu_complete(key, uid, [(1, e1)])
        c2 = self.mpu_complete(key, uid, [(1, e1)])
        pst, pe, pb = self.part_presigned(key, uid, 2, os.urandom(1024))
        self.rec("T37", "Complete twice, then UploadPart after Complete",
                 {"complete1": obs(c1[0], c1[2]), "complete2": obs(c2[0], c2[2]), "part_after_complete": obs(pst, pb)},
                 "undocumented for R2 -> SB leg")
        # conditional complete over an existing key
        key = self.k("m08")
        self.put(key, b"existing")
        r, uid, sha = self.mpu(key, [1024], complete_headers={"if-none-match": "*"})
        g = s3.call("GET", key)
        self.rec("T38", "CompleteMultipartUpload with If-None-Match:* when the key already exists",
                 {**r, "overwritten": g[2] != b"existing"},
                 "R2 docs list no conditional headers for Complete (AWS: 412)")
        # conditional create-multipart
        key = self.k("m09")
        self.put(key, b"existing")
        st, uid, b = self.mpu_create(key, headers={"if-none-match": "*"})
        self.rec("T39", "CreateMultipartUpload with If-None-Match:* on existing key", obs(st, b), "undocumented")

    def t_integrity(self):
        s3 = self.s3
        d = os.urandom(4096)
        bad_md5 = base64.b64encode(hashlib.md5(b"other").digest()).decode()
        st, h, b = self.put(self.k("i01"), d, headers={"content-md5": bad_md5})
        good = base64.b64encode(hashlib.md5(d).digest()).decode()
        st2, h2, b2 = self.put(self.k("i01"), d, headers={"content-md5": good})
        self.rec("T40", "PutObject with wrong vs correct Content-MD5", {"wrong": obs(st, b), "correct": obs(st2, b2)}, "400 BadDigest / 200")
        bad = base64.b64encode(hashlib.sha256(b"other").digest()).decode()
        st, h, b = self.put(self.k("i02"), d, headers={"x-amz-checksum-sha256": bad})
        g = s3.call("HEAD", self.k("i02"))
        self.rec("T41", "PutObject with wrong x-amz-checksum-sha256", {**obs(st, b), "stored": g[0] == 200},
                 "R2 validates flexible checksums: 400 BadDigest, nothing stored")
        goodc = base64.b64encode(hashlib.sha256(d).digest()).decode()
        st, h, b = self.put(self.k("i03"), d, headers={"x-amz-checksum-sha256": goodc})
        self.rec("T42", "PutObject with correct x-amz-checksum-sha256 (echoed?)",
                 {**obs(st, b), "echoed": h.get("x-amz-checksum-sha256")}, "200 and checksum echoed")
        st, h, b = s3.call_presigned("PUT", self.k("i04"), body=d, extra_headers={"x-amz-checksum-sha256": bad})
        self.rec("T43", "Presigned PUT with wrong unsigned x-amz-checksum-sha256", obs(st, b), "undocumented -> SB leg")
        # C1-S1 overlap: checksum and length signed INTO the presigned URL, body tampered
        good_b64 = base64.b64encode(hashlib.sha256(d).digest()).decode()
        tampered = os.urandom(len(d))
        st, h, b = s3.call_presigned("PUT", self.k("i06"), body=tampered, sign_headers={"x-amz-checksum-sha256": good_b64})
        g = s3.call("HEAD", self.k("i06"))
        st2, h2, b2 = s3.call_presigned("PUT", self.k("i06b"), body=d, sign_headers={"x-amz-checksum-sha256": good_b64})
        self.rec("T47", "Presigned PUT with x-amz-checksum-sha256 SIGNED into the URL; body tampered (same length) vs genuine",
                 {"tampered": obs(st, b), "tampered_stored": g[0] == 200, "genuine": obs(st2, b2)},
                 "R2 validates flexible checksums -> tampered 400 BadDigest (C1-S1 confirms for presigned)")
        md5 = base64.b64encode(hashlib.md5(d).digest()).decode()
        st, h, b = s3.call_presigned("PUT", self.k("i07"), body=tampered, sign_headers={"content-md5": md5})
        g = s3.call("HEAD", self.k("i07"))
        self.rec("T48", "Presigned PUT with Content-MD5 SIGNED into the URL; body tampered (same length)",
                 {**obs(st, b), "tampered_stored": g[0] == 200}, "400 BadDigest")
        st, h, b = s3.call_presigned("PUT", self.k("i08"), body=d + b"extra", sign_headers={"content-length": str(len(d))},
                                     extra_headers={"content-length": str(len(d) + 5)})
        g = s3.call("HEAD", self.k("i08"))
        self.rec("T49", "Presigned PUT with Content-Length SIGNED; client sends a longer body",
                 {**obs(st, b), "stored": g[0] == 200}, "403 SignatureDoesNotMatch (C1-S1 confirms)")
        # aws-chunked with trailing checksum (what SDKs send by default)
        payload = os.urandom(3000)
        crc = base64.b64encode(hashlib.sha256(payload).digest()).decode()
        chunked = f"{len(payload):x}\r\n".encode() + payload + b"\r\n0\r\n" + f"x-amz-checksum-sha256:{crc}\r\n\r\n".encode()
        st, h, b = self.put(self.k("i05"), chunked, payload_hash="STREAMING-UNSIGNED-PAYLOAD-TRAILER",
                            headers={"content-encoding": "aws-chunked", "x-amz-decoded-content-length": str(len(payload)),
                                     "x-amz-trailer": "x-amz-checksum-sha256"})
        gst, gsha, n = self.get_sha(self.k("i05"))
        self.rec("T44", "PutObject with aws-chunked body + trailing checksum (SDK default style)",
                 {**obs(st, b), "stored_equals_payload": gsha == hashlib.sha256(payload).hexdigest(), "stored_len": n, "payload_len": len(payload)},
                 "R2 supports (decoded payload stored)")

    def t_expect(self):
        s3 = self.s3
        body = os.urandom(1024)
        pq, hh = s3.signed_headers("PUT", self.k("e01"), body=body)
        host, _, port = s3.host.partition(":")
        port = int(port or (443 if s3.scheme == "https" else 80))
        if s3.scheme == "https":
            self.rec("T45", "Expect: 100-continue", {"skipped": "https target; run via SB kit"}, None)
            return
        sock = socket.create_connection((host, port), timeout=15)
        req = f"PUT {pq} HTTP/1.1\r\nHost: {s3.host}\r\n" + "".join(f"{k}: {v}\r\n" for k, v in hh.items()) + \
              f"Content-Length: {len(body)}\r\nExpect: 100-continue\r\nConnection: close\r\n\r\n"
        t0 = time.time()
        sock.sendall(req.encode())
        sock.settimeout(3)
        first = b""
        try:
            first = sock.recv(4096)
        except socket.timeout:
            pass
        t100 = time.time() - t0
        got100 = first.startswith(b"HTTP/1.1 100")
        final = first if (first and not got100) else b""
        if not final:
            sock.settimeout(10)
            try:
                sock.sendall(body)
                while b"\r\n\r\n" not in final:
                    c = sock.recv(4096)
                    if not c:
                        break
                    final += c
            except (socket.timeout, OSError) as e:
                final += f"<{type(e).__name__}>".encode()
        sock.close()
        m = re.match(rb"HTTP/1.1 (\d+)", final)
        self.rec("T45", "Expect: 100-continue (waits 3 s for 100, then sends body anyway)",
                 {"got_100_continue": got100, "seconds_waited_for_100": round(t100, 2),
                  "final_status": int(m.group(1)) if m else None, "sent_body_without_100": not got100},
                 "[unknown] not documented for R2")

    def t_transfer_chunked(self):
        """HTTP/1.1 Transfer-Encoding: chunked body (no Content-Length), UNSIGNED-PAYLOAD, as a streaming client sends."""
        s3 = self.s3
        if s3.scheme == "https":
            self.rec("T46", "Transfer-Encoding: chunked PUT", {"skipped": "https target; run via SB kit"}, None)
            return
        payload = os.urandom(5000)
        pq, hh = s3.signed_headers("PUT", self.k("tc01"), payload_hash=UNSIGNED)
        host, _, port = s3.host.partition(":")
        sock = socket.create_connection((host, int(port or 80)), timeout=15)
        req = f"PUT {pq} HTTP/1.1\r\nHost: {s3.host}\r\n" + "".join(f"{k}: {v}\r\n" for k, v in hh.items()) + \
              "Transfer-Encoding: chunked\r\nConnection: close\r\n\r\n"
        body = f"{len(payload):x}\r\n".encode() + payload + b"\r\n0\r\n\r\n"
        sock.sendall(req.encode() + body)
        resp = b""
        try:
            while True:
                c = sock.recv(65536)
                if not c:
                    break
                resp += c
        except (socket.timeout, OSError) as e:
            resp += f"<{type(e).__name__}>".encode()
        sock.close()
        m = re.match(rb"HTTP/1.1 (\d+)", resp)
        st = int(m.group(1)) if m else None
        gst, gsha, n = self.get_sha(self.k("tc01"))
        self.rec("T46", "PUT with Transfer-Encoding: chunked (unknown length), UNSIGNED-PAYLOAD",
                 {"status": st, "code": err_code(resp), "stored_equals_payload": gsha == hashlib.sha256(payload).hexdigest(),
                  "raw_head": resp[:60].decode(errors="replace")},
                 "R2 behaviour for unknown-length bodies -> SB leg")

    def t_list_delete(self):
        s3 = self.s3
        st, h, b = s3.call("GET", None, params={"list-type": "2", "prefix": self.k("t0")})
        keys = re.findall(rb"<Key>([^<]+)</Key>", b)
        self.rec("T50", "ListObjectsV2 with prefix", obs(st, b, keys_found=len(keys)), "200")
        st, h, b = s3.call("DELETE", self.k("t01"))
        g = s3.call("HEAD", self.k("t01"))
        self.rec("T51", "DeleteObject (header auth), then HEAD", {"delete": obs(st, b), "head_after": g[0]}, "204 / 404")
        st, h, b = s3.call_presigned("DELETE", self.k("t02"))
        self.rec("T52", "Presigned DELETE", obs(st, b), "204 (R2 allows presigned DELETE; the Worker must never mint one)")
        # Presigned POST (browser form upload) - send a bare multipart form
        st, h, b = s3.raw("POST", s3.path(), {"content-type": "multipart/form-data; boundary=x"},
                          b"--x\r\nContent-Disposition: form-data; name=\"key\"\r\n\r\nk\r\n--x--\r\n")
        self.rec("T53", "Presigned POST (form upload) to bucket", obs(st, b), "not supported by R2")
        lc = (b"<LifecycleConfiguration><Rule><ID>abort-staging</ID><Status>Enabled</Status>"
              b"<Filter><Prefix>staging/</Prefix></Filter><AbortIncompleteMultipartUpload><DaysAfterInitiation>7"
              b"</DaysAfterInitiation></AbortIncompleteMultipartUpload></Rule><Rule><ID>expire-restore</ID>"
              b"<Status>Enabled</Status><Filter><Prefix>restore/</Prefix></Filter><Expiration><Days>3</Days>"
              b"</Expiration></Rule></LifecycleConfiguration>")
        md5 = base64.b64encode(hashlib.md5(lc).digest()).decode()
        st, h, b = s3.call("PUT", None, params={"lifecycle": ""}, body=lc, headers={"content-md5": md5})
        st2, h2, b2 = s3.call("GET", None, params={"lifecycle": ""})
        self.rec("T54", "PutBucketLifecycleConfiguration (abort 7 d on staging/, expire 3 d on restore/) then Get",
                 {"put": obs(st, b), "get": obs(st2, b2, has_rules=b"abort-staging" in b2)},
                 "R2 supports lifecycle via S3 API (prefix-scoped abort and expiration)")

    def t_worker(self):
        if not self.worker:
            return
        import urllib.request
        def w(path, data=None, method=None):
            req = urllib.request.Request(self.worker + path, data=data, method=method or ("POST" if data is not None else "GET"))
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    return r.status, json.loads(r.read())
            except urllib.error.HTTPError as e:
                return e.code, json.loads(e.read() or b"{}")
        key = self.k("w01")
        _, j = w(f"/presign?key={urllib.parse.quote(key)}&method=PUT&expires=900")
        u = urllib.parse.urlsplit(j["url"])
        d = os.urandom(10000)
        st, h, b = self.s3.raw("PUT", u.path + "?" + u.query, {}, d)
        gs, gj = w(f"/b/get?key={urllib.parse.quote(key)}")
        self.rec("W01", "Worker-minted (aws4fetch) presigned PUT; object visible to the Worker's R2 binding",
                 {**obs(st, b), "binding_sees_same_bytes": gj.get("sha256") == hashlib.sha256(d).hexdigest()}, "n/a (Miniflare-only interop)")
        st2, j2 = w(f"/b/put-create-only?key={urllib.parse.quote(key)}", data=b"other")
        self.rec("W02", "Binding put(onlyIf If-None-Match:*) on key written over S3", {"status": st2, **j2}, "412 / stored=false")
        key = self.k("w03")
        st3, j3 = w(f"/b/put-create-only?key={urllib.parse.quote(key)}", data=b"binding")
        s, h, b = self.put(key, b"s3", headers={"if-none-match": "*"})
        self.rec("W03", "S3 PutObject If-None-Match:* on key written by binding", {"binding": st3, **obs(s, b)}, "binding 200; S3 412")
        key = self.k("w04")
        _, cj = w(f"/b/mpu-create?key={urllib.parse.quote(key)}", data=b"")
        uid = cj["uploadId"]
        parts, blobs = [], []
        for n, sz in ((1, 5 * MiB), (2, 5 * MiB), (3, 1234)):
            _, pj = w(f"/presign?key={urllib.parse.quote(key)}&method=PUT&partNumber={n}&uploadId={urllib.parse.quote(uid)}")
            u = urllib.parse.urlsplit(pj["url"])
            dd = os.urandom(sz)
            blobs.append(dd)
            st, h, b = self.s3.raw("PUT", u.path + "?" + u.query, {}, dd)
            parts.append({"partNumber": n, "etag": (h.get("etag") or "").strip('"')})
        cs, cjj = w(f"/b/mpu-complete?key={urllib.parse.quote(key)}", data=json.dumps({"uploadId": uid, "parts": parts}).encode())
        gs, gj = w(f"/b/get?key={urllib.parse.quote(key)}")
        self.rec("W04", "Binding createMultipartUpload -> Worker-presigned S3 UploadPart x3 -> binding complete",
                 {"complete": cs, "sha_match": gj.get("sha256") == hashlib.sha256(b"".join(blobs)).hexdigest(), "size": gj.get("size")},
                 "n/a (Miniflare-only interop); on R2 -> SB leg")
        w("/d1/init", data=b"")
        did = self.k("dedup")
        a = w(f"/d1/claim?key={did}&device=a", data=b"")[1]
        b_ = w(f"/d1/claim?key={did}&device=b", data=b"")[1]
        wins = []
        for r in range(10):
            dk = self.k(f"dedup-race-{r}")
            with cf.ThreadPoolExecutor(16) as ex:
                res = list(ex.map(lambda i: w(f"/d1/claim?key={dk}&device={i}", data=b"")[1].get("won"), range(16)))
            wins.append(sum(1 for x in res if x))
        self.rec("W05", "D1 claim (INSERT .. ON CONFLICT DO NOTHING): sequential, then 16-way race x10",
                 {"first": a, "second": b_, "winners_per_round": wins}, "exactly one winner")

    def run(self, only=None):
        groups = [("basic", self.t_basic), ("conditional", self.t_conditional), ("race", self.t_race),
                  ("multipart", self.t_multipart), ("integrity", self.t_integrity), ("expect", self.t_expect), ("te_chunked", self.t_transfer_chunked),
                  ("list_delete", self.t_list_delete), ("worker", self.t_worker)]
        for name, fn in groups:
            if only and name not in only:
                continue
            try:
                fn()
            except Exception as e:  # record, never hide
                self.rec(f"ERR-{name}", f"group {name} aborted", {"exception": f"{type(e).__name__}: {e}"})
        return self.results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--endpoint", required=True)
    ap.add_argument("--bucket", required=True)
    ap.add_argument("--ak", required=True)
    ap.add_argument("--sk", required=True)
    ap.add_argument("--region", default="auto")
    ap.add_argument("--worker")
    ap.add_argument("--only")
    ap.add_argument("--out")
    a = ap.parse_args()
    s3 = S3(a.endpoint, a.bucket, a.ak, a.sk, a.region)
    r = Runner(s3, a.name, a.worker)
    t0 = time.time()
    res = r.run(set(a.only.split(",")) if a.only else None)
    out = {"target": a.name, "endpoint": a.endpoint, "bucket": a.bucket, "region": a.region,
           "run_id": r.run_id, "finished_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "duration_s": round(time.time() - t0, 1),
           "requests_sent_by_script": S3.requests_sent, "body_bytes_sent_by_script": S3.bytes_sent, "results": res}
    if a.out:
        os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
        json.dump(out, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
