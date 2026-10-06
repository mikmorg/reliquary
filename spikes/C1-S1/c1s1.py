#!/usr/bin/env python3
"""C1-S1 R2 behaviour checks (throwaway research code, stdlib only).

Adds the C1-S1 hypotheses that G2-S1's fidelity.py does not already cover. It reuses
fidelity.py's SigV4 signer (spikes/G2-S1/fidelity.py) and, where the design's real path is
"the Worker presigns with aws4fetch", it asks the C1 Worker (spikes/C1-S1/worker) to presign.

Runs against Miniflare's local R2 S3 endpoint (EMULATED, NOT real R2) or, in the SB kit,
against real R2 with the Worker running under `wrangler dev` with a remote R2 binding.

  python3 c1s1.py --name miniflare --endpoint http://127.0.0.1:8787/cdn-cgi/local/r2/s3 \
     --bucket staging --ak AK --sk SK --worker http://127.0.0.1:8787 --out results/miniflare.json

Sub-steps for the SB kit that need Cloudflare account actions between calls:
  --only H9-before / H9-after   (bucket lock probe; the operator adds the lock rule in between)
  --only H11-mint / H11-poll    (token-roll probe; the operator rolls the parent token in between)

Data-handling class: SYN -> results (random bytes only).
"""
import argparse, base64, datetime as dt, hashlib, hmac, json, os, socket, sys, time, urllib.parse, urllib.request, uuid

HERE = os.path.dirname(os.path.abspath(__file__))
for cand in (os.path.join(HERE, "..", "G2-S1"), os.path.join(HERE, "..", "..", "..", "spikes", "G2-S1"),
             os.environ.get("G2S1_DIR", "")):
    if cand and os.path.exists(os.path.join(cand, "fidelity.py")):
        sys.path.insert(0, os.path.abspath(cand))
        break
import fidelity as F  # noqa: E402

MiB = 1024 * 1024


class Ctx:
    def __init__(self, a):
        self.a = a
        self.s3 = F.S3(a.endpoint, a.bucket, a.ak, a.sk, a.region)
        self.run = uuid.uuid4().hex[:8]
        self.results = []
        self.state_file = a.state

    def k(self, s):
        return f"c1s1/{self.run}/{s}"

    def rec(self, hid, cid, title, observed, expect=None, verdict=None):
        r = {"hyp": hid, "id": cid, "title": title, "observed": observed, "expected_or_documented": expect,
             "verdict": verdict}
        self.results.append(r)
        print(f"[{self.a.name}] {hid}/{cid} {title}: {json.dumps(observed)} -> {verdict}", flush=True)

    # Worker helpers -----------------------------------------------------------------------
    def w(self, path, params=None, body=None, method=None):
        url = self.a.worker + path + ("?" + urllib.parse.urlencode(params) if params else "")
        req = urllib.request.Request(url, data=body, method=method or ("POST" if body is not None else "GET"))
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.status, json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            raw = e.read()
            try:
                return e.code, json.loads(raw)
            except Exception:
                return e.code, {"raw": raw[:200].decode(errors="replace")}

    def wpresign(self, key, method="PUT", expires=900, headers=None, all_headers=False, **params):
        q = {"key": key, "method": method, "expires": str(expires)}
        if headers:
            q["h"] = json.dumps(headers)
        if all_headers:
            q["all"] = "1"
        q.update({k: v for k, v in params.items() if v is not None})
        st, j = self.w("/presign", q)
        if st != 200:
            raise RuntimeError(f"presign failed {st} {j}")
        u = urllib.parse.urlsplit(j["url"])
        return u.path + "?" + u.query, j["signedHeaders"]

    def send(self, method, pathq, headers=None, body=b""):
        try:
            return self.s3.raw(method, pathq, headers or {}, body)
        except (ConnectionError, OSError) as e:  # e.g. the server resets a rejected upload mid-body
            return 0, {}, f"<Code>CONN:{type(e).__name__}</Code>".encode()


def md5hex(b):
    return hashlib.md5(b).hexdigest()


def mpu_etag(parts):
    return hashlib.md5(b"".join(hashlib.md5(p).digest() for p in parts)).hexdigest() + f"-{len(parts)}"


# ---------------------------------------------------------------------------------------------
def h1(c):
    k = c.k("h1")
    pq, sh = c.wpresign(k, headers={"if-none-match": "*"})
    a = c.send("PUT", pq, {"if-none-match": "*"}, b"first")
    b = c.send("PUT", pq, {"if-none-match": "*"}, b"second")
    g = c.s3.call("GET", k)
    c.rec("H1", "C01", "aws4fetch-presigned PUT with signed If-None-Match:*, absent then existing key",
          {"signedHeaders": sh, "first": F.obs(a[0], a[2]), "second": F.obs(b[0], b[2]), "stored": g[2].decode(errors="replace")},
          "first 200, second 412 PreconditionFailed (R2 may answer 429 to a second write <1 s later, limits.mdx)",
          "pass" if a[0] == 200 and b[0] in (412, 429) and g[2] == b"first" else "fail")
    # The device drops the signed header: must not turn into an unconditional overwrite.
    k2 = c.k("h1-drop")
    c.s3.call("PUT", k2, body=b"orig")
    time.sleep(1.1)
    pq2, _ = c.wpresign(k2, headers={"if-none-match": "*"})
    d = c.send("PUT", pq2, {}, b"overwrite-attempt")
    g2 = c.s3.call("GET", k2)
    c.rec("H1", "C02", "Same URL, client omits the signed If-None-Match header, key exists",
          {**F.obs(d[0], d[2]), "stored": g2[2].decode(errors="replace")},
          "403 SignatureDoesNotMatch; original kept",
          "pass" if d[0] >= 400 and g2[2] == b"orig" else "fail")


def h2(c):
    # S3 Complete with If-None-Match is G2-S1 T38. Here: the Worker's own path, binding complete, onto an existing key.
    k = c.k("h2")
    c.s3.call("PUT", k, body=b"existing")
    st, j = c.w("/b/mpu-create", {"key": k})
    uid = j.get("uploadId")
    parts, blobs = [], []
    for n, sz in ((1, 5 * MiB), (2, 1024)):
        d = os.urandom(sz)
        blobs.append(d)
        pq, _ = c.wpresign(k, partNumber=str(n), uploadId=uid)
        r = c.send("PUT", pq, {}, d)
        parts.append({"partNumber": n, "etag": (r[1].get("etag") or "").strip('"')})
    st2, j2 = c.w("/b/mpu-complete", {"key": k}, json.dumps({"uploadId": uid, "parts": parts}).encode())
    g = c.s3.call("GET", k)
    over = g[0] == 200 and hashlib.sha256(g[2]).hexdigest() == hashlib.sha256(b"".join(blobs)).hexdigest()
    c.rec("H2", "C03", "Binding resumeMultipartUpload().complete() onto an existing key (no onlyIf exists on complete)",
          {"complete": st2, "overwritten": over}, "undocumented; the binding complete() takes no condition",
          "documented-gap: overwrites" if over else "refuses overwrite")


def h3(c):
    k = c.k("h3")
    pq, sh = c.wpresign(k, method="POST", uploads="")
    a = c.send("POST", pq, {}, b"")
    uid = None
    if a[0] == 200:
        import re
        m = re.search(rb"<UploadId>([^<]+)</UploadId>", a[2])
        uid = m.group(1).decode() if m else None
    c.rec("H3", "C04", "Presigned POST ?uploads (CreateMultipartUpload) used without credentials",
          {**F.obs(a[0], a[2]), "uploadId": bool(uid)}, "undocumented (R2 docs: presigned URLs support GET, HEAD, PUT, DELETE)",
          "accepted" if a[0] == 200 else "rejected")
    # Complete via presigned POST, on an upload the Worker created with the binding.
    st, j = c.w("/b/mpu-create", {"key": k + "-c"})
    uid2 = j.get("uploadId")
    d = os.urandom(1024)
    ppq, _ = c.wpresign(k + "-c", partNumber="1", uploadId=uid2)
    pr = c.send("PUT", ppq, {}, d)
    xml = f"<CompleteMultipartUpload><Part><PartNumber>1</PartNumber><ETag>{pr[1].get('etag')}</ETag></Part></CompleteMultipartUpload>".encode()
    cpq, _ = c.wpresign(k + "-c", method="POST", uploadId=uid2)
    b = c.send("POST", cpq, {"content-type": "application/xml"}, xml)
    g = c.s3.call("GET", k + "-c")
    c.rec("H3", "C05", "Presigned POST ?uploadId (CompleteMultipartUpload) used without credentials",
          {**F.obs(b[0], b[2]), "object_after": g[0], "match": g[0] == 200 and g[2] == d},
          "undocumented", "accepted" if b[0] == 200 else "rejected")


def h4(c):
    k = c.k("h4")
    st, j = c.w("/b/mpu-create", {"key": k})
    uid = j.get("uploadId")
    good = os.urandom(5 * MiB)
    md5b64 = base64.b64encode(hashlib.md5(good).digest()).decode()
    pq, sh = c.wpresign(k, headers={"content-md5": md5b64}, partNumber="1", uploadId=uid)
    bad = bytearray(good)
    bad[100] ^= 1
    t = c.send("PUT", pq, {"content-md5": md5b64}, bytes(bad))
    ok = c.send("PUT", pq, {"content-md5": md5b64}, good)
    c.rec("H4", "C06", "Presigned UploadPart with Content-MD5 signed in; tampered body (same length) then genuine",
          {"signedHeaders": sh, "tampered": F.obs(t[0], t[2]), "genuine": F.obs(ok[0], ok[2]),
           "part_etag": ok[1].get("etag"), "md5": md5hex(good),
           "part_etag_is_md5": (ok[1].get("etag") or "").strip('"') == md5hex(good)},
          "tampered 400 BadDigest; genuine 200 (UploadPart lists Content-MD5 as supported)",
          "pass" if t[0] == 400 and ok[0] == 200 else "fail")
    # Same URL, client omits Content-MD5 entirely
    o = c.send("PUT", pq, {}, bytes(bad))
    c.rec("H4", "C07", "Same UploadPart URL, client omits the signed Content-MD5 (5 MiB tampered body)", F.obs(o[0], o[2]) if o[0] else {"status": 0, "code": F.err_code(o[2])},
          "403 SignatureDoesNotMatch", "pass" if o[0] == 403 else ("rejected (not 403)" if o[0] != 200 else "fail"))


def h5(c):
    k = c.k("h5")
    body = os.urandom(4096)
    pq, sh = c.wpresign(k, headers={"content-length": str(len(body))}, all_headers=True)
    shorter = c.send("PUT", pq, {}, body[:-1])
    longer = c.send("PUT", pq, {}, body + b"x")
    st_after_bad = c.s3.call("GET", k)[0]
    exact = c.send("PUT", pq, {}, body)
    c.rec("H5", "C08", "aws4fetch presign with allHeaders and Content-Length signed; shorter, longer, exact body",
          {"signedHeaders": sh, "shorter": F.obs(shorter[0], shorter[2]), "longer": F.obs(longer[0], longer[2]),
           "exact": F.obs(exact[0], exact[2]), "stored_after_wrong_lengths": st_after_bad == 200},
          "shorter/longer 403 SignatureDoesNotMatch; exact 200",
          "pass" if shorter[0] == 403 and longer[0] == 403 and exact[0] == 200 else
          ("pass-with-wrong-status (nothing stored)" if exact[0] == 200 and st_after_bad != 200 and shorter[0] >= 400 and longer[0] >= 400 else "fail"))


def h6(c):
    k = c.k("h6")
    good = os.urandom(4096)
    sha = base64.b64encode(hashlib.sha256(good).digest()).decode()
    pq, sh = c.wpresign(k, headers={"x-amz-checksum-sha256": sha})
    bad = bytearray(good)
    bad[7] ^= 1
    t = c.send("PUT", pq, {"x-amz-checksum-sha256": sha}, bytes(bad))
    g = c.s3.call("GET", k)
    c.rec("H6", "C09", "aws4fetch presign with x-amz-checksum-sha256 signed; tampered body (same length)",
          {"signedHeaders": sh, **F.obs(t[0], t[2]), "tampered_stored": g[0] == 200 and g[2] == bytes(bad)},
          "R2: 400 BadDigest expected if R2 validates SHA-256 on PutObject; Miniflare is known to ignore it (G2-S1 T47)",
          "pass" if t[0] == 400 else "fail")
    # binding put() with a wrong sha256 option
    st, j = c.w("/b/put-sha256", {"key": k + "-b", "sha": hashlib.sha256(b"other").hexdigest()}, good)
    c.rec("H6", "C10", "Binding put() with a wrong sha256 option", {"http": st, **j},
          "documented: put() verifies sha256 -> error, nothing stored", "pass" if j.get("threw") and not j.get("stored") else "fail")


def h7(c):
    k = c.k("h7-single")
    d = os.urandom(10000)
    st, h, b = c.s3.call("PUT", k, body=d)
    st2, j = c.w("/b/head", {"key": k})
    c.rec("H7", "C11", "Single PUT: S3 ETag header vs MD5(body); binding etag/httpEtag",
          {"s3_etag": h.get("etag"), "md5": md5hex(d), "binding_etag": j.get("etag"), "binding_httpEtag": j.get("httpEtag"),
           "binding_md5": j.get("checksums", {}).get("md5")},
          "S3 ETag = \"<md5 hex>\" (quoted); binding etag unquoted, httpEtag quoted",
          "pass" if (h.get("etag") or "").strip('"') == md5hex(d) and j.get("etag") == md5hex(d) else "fail")
    k = c.k("h7-mpu")
    st, j = c.w("/b/mpu-create", {"key": k})
    uid = j.get("uploadId")
    blobs = [os.urandom(5 * MiB), os.urandom(5 * MiB), os.urandom(12345)]
    parts, pe = [], []
    for n, d in enumerate(blobs, 1):
        pq, _ = c.wpresign(k, partNumber=str(n), uploadId=uid)
        r = c.send("PUT", pq, {}, d)
        e = (r[1].get("etag") or "")
        pe.append({"etag": e, "md5": md5hex(d), "equal": e.strip('"') == md5hex(d)})
        parts.append({"partNumber": n, "etag": e.strip('"')})
    st2, j2 = c.w("/b/mpu-complete", {"key": k}, json.dumps({"uploadId": uid, "parts": parts}).encode())
    hs = c.s3.call("HEAD", k)
    c.rec("H7", "C12", "Multipart 5 MiB + 5 MiB + 12,345 B: part ETags = MD5(part); object ETag = MD5(concat part MD5s)-N",
          {"part_etags_are_md5": pe, "binding_complete_etag": j2.get("etag"), "s3_head_etag": hs[1].get("etag"),
           "formula": mpu_etag(blobs), "size": j2.get("size")},
          "R2 release note 2023-06-21: multipart ETags are MD5-based",
          ("pass" if all(x["equal"] for x in pe) else "object ETag formula holds; part ETags are not MD5")
          if (hs[1].get("etag") or "").strip('"') == mpu_etag(blobs) else "fail")


def h10(c):
    """Presigned URL whose expiry passes while the body is still being sent (plain-HTTP or HTTPS)."""
    import ssl
    k = c.k("h10")
    body = os.urandom(256 * 1024)
    pq, _ = c.wpresign(k, expires=3)
    host = c.s3.host
    hostname, _, port = host.partition(":")
    https = c.s3.scheme == "https"
    sock = socket.create_connection((hostname, int(port or (443 if https else 80))), timeout=60)
    if https:
        sock = ssl.create_default_context().wrap_socket(sock, server_hostname=hostname)
    req = (f"PUT {pq} HTTP/1.1\r\nHost: {host}\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n").encode()
    sock.sendall(req + body[:1024])
    time.sleep(6)  # URL expires 3 s after signing, mid-body
    t0 = time.time()
    try:
        sock.sendall(body[1024:])
        resp = b""
        while True:
            ch = sock.recv(65536)
            if not ch:
                break
            resp += ch
    except Exception as e:
        resp = f"EXC {e}".encode()
    sock.close()
    line = resp.split(b"\r\n", 1)[0].decode(errors="replace")
    g = c.s3.call("GET", k)
    c.rec("H10", "C13", "Presigned PUT, X-Amz-Expires=3, headers sent at t=0, rest of body sent at t=6 s",
          {"status_line": line, "code": F.err_code(resp), "stored": g[0] == 200 and g[2] == body},
          "undocumented for R2 (AWS checks expiry when the request arrives)",
          "completes" if g[0] == 200 else "fails")


def h12(c):
    k = c.k("h12")
    out = {}
    for form in ("headers", "cond"):
        kk = f"{k}-{form}"
        st1, j1 = c.w("/b/put-onlyif", {"key": kk, "form": form}, b"first")
        st2, j2 = c.w("/b/put-onlyif", {"key": kk, "form": form}, b"second")
        g = c.s3.call("GET", kk)
        out[form] = {"absent": j1.get("stored"), "existing": j2.get("stored"), "kept": g[2] == b"first"}
    c.rec("H12", "C14", "Binding put() onlyIf If-None-Match:* as Headers and as {etagDoesNotMatch:'*'}",
          out, "absent stored; existing refused (put returns null); original kept (workerd #2572 wildcard history)",
          "pass" if all(v["absent"] and not v["existing"] and v["kept"] for v in out.values()) else "fail")


def b64url(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def mint_temp(a, bucket, actions=None, prefixes=None, objects=None, ttl=900, scope="object-read-write"):
    """R2 temporary credential by local signing (r2/examples/authenticate-r2-temp-credentials.mdx)."""
    host = urllib.parse.urlsplit(a.endpoint).netloc
    now = int(time.time())
    claims = {"bucket": bucket, "scope": scope, "sub": a.account or "local", "iss": a.ak, "aud": host,
              "iat": now, "exp": now + ttl}
    if actions:
        claims["actions"] = actions
    if prefixes is not None or objects is not None:
        claims["paths"] = {"prefixPaths": prefixes or [], "objectPaths": objects or []}
    hdr = b64url(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    pl = b64url(json.dumps(claims, separators=(",", ":")).encode())
    sig = b64url(hmac.new(a.sk.encode(), f"{hdr}.{pl}".encode(), hashlib.sha256).digest())
    jwt = f"{hdr}.{pl}.{sig}"
    return {"ak": a.ak, "sk": hashlib.sha256(jwt.encode()).hexdigest(),
            "token": base64.b64encode(("jwt/" + jwt).encode()).decode()}


def temp_call(c, cred, method, key, body=b"", params=None):
    s3t = F.S3(c.a.endpoint, c.a.bucket, cred["ak"], cred["sk"], c.a.region)
    pq, h = s3t.signed_headers(method, key, params=params, headers={"x-amz-security-token": cred["token"]}, body=body)
    return s3t.raw(method, pq, h, body)


def h13(c):
    base = c.k("h13")
    c.s3.call("PUT", f"{base}/in/existing", body=b"x")
    c.s3.call("PUT", f"{base}/out/existing", body=b"x")
    cred = mint_temp(c.a, c.a.bucket, actions=["PutObject", "UploadPart", "CreateMultipartUpload", "CompleteMultipartUpload"],
                     prefixes=[f"{base}/in/"])
    r = {}
    x = temp_call(c, cred, "PUT", f"{base}/in/new", b"data")
    r["put_in_prefix"] = x[0]
    r["put_in_prefix_code"] = F.err_code(x[2])
    r["put_out_of_prefix"] = temp_call(c, cred, "PUT", f"{base}/out/new", b"data")[0]
    r["get_in_prefix(not granted)"] = temp_call(c, cred, "GET", f"{base}/in/existing")[0]
    r["delete_in_prefix(not granted)"] = temp_call(c, cred, "DELETE", f"{base}/in/existing")[0]
    r["list(not granted)"] = temp_call(c, cred, "GET", None, params={"list-type": "2", "prefix": f"{base}/"})[0]
    still = c.s3.call("GET", f"{base}/in/existing")[0]
    exp = {"put_in_prefix": 200, "put_out_of_prefix": 403, "get_in_prefix(not granted)": 403,
           "delete_in_prefix(not granted)": 403, "list(not granted)": 403}
    c.rec("H13", "C15", "Locally signed temp credential: actions=[Put, multipart write], prefixPaths=[in/]",
          {**r, "existing_survives_delete": still == 200}, exp,
          "pass" if all(r[k] == v for k, v in exp.items()) and still == 200 else
          ("not-emulated (in-scope request refused too)" if r["put_in_prefix"] != 200 else "fail"))
    # expired credential
    cred2 = mint_temp(c.a, c.a.bucket, actions=["PutObject"], prefixes=[f"{base}/in/"], ttl=1)
    time.sleep(2.5)
    e = temp_call(c, cred2, "PUT", f"{base}/in/late", b"data")
    c.rec("H13", "C16", "Temp credential used 1.5 s after its exp claim", F.obs(e[0], e[2]), "403",
          ("pass" if e[0] == 403 else "fail") if r["put_in_prefix"] == 200 else "not-emulated (valid credentials are refused too)")


# --- SB-only multi-step probes (operator acts between calls) -----------------------------------
def save_state(c, d):
    with open(c.state_file, "w") as f:
        json.dump(d, f)


def load_state(c):
    with open(c.state_file) as f:
        return json.load(f)


def h9_before(c):
    """Create objects under the lock prefix BEFORE the lock rule exists, plus an open multipart upload."""
    p = c.a.lock_prefix
    k_old = f"{p}{c.run}/pre-existing"
    c.s3.call("PUT", k_old, body=b"before-lock")
    st, uid, b = F.Runner(c.s3, c.a.name).mpu_create(f"{p}{c.run}/mpu-open")
    save_state(c, {"run": c.run, "k_old": k_old, "mpu_key": f"{p}{c.run}/mpu-open", "uid": uid})
    print(json.dumps({"next": f"Add an Age bucket lock rule on prefix '{p}' (wrangler r2 bucket lock add <bucket> c1s1-lock '{p}' --retention-days 1), wait 60 s, then run --only H9-after"}))


def h9_after(c):
    s = load_state(c)
    p = c.a.lock_prefix
    out = {}
    k_new = f"{p}{s['run']}/after-lock"
    out["put_new_key"] = c.s3.call("PUT", k_new, body=b"v1")[0]
    time.sleep(1.2)
    pq, _ = c.wpresign(k_new)
    out["presigned_overwrite"] = c.send("PUT", pq, {}, b"v2")[0]
    out["after_overwrite_content"] = c.s3.call("GET", k_new)[2].decode(errors="replace")
    # Complete onto an existing locked key
    st, uid, b = F.Runner(c.s3, c.a.name).mpu_create(k_new)
    d = os.urandom(1024)
    pr = c.s3.call_presigned("PUT", k_new, body=d, params={"partNumber": "1", "uploadId": uid})
    xml = f"<CompleteMultipartUpload><Part><PartNumber>1</PartNumber><ETag>{pr[1].get('etag')}</ETag></Part></CompleteMultipartUpload>".encode()
    out["complete_onto_locked_key"] = c.s3.call("POST", k_new, params={"uploadId": uid}, body=xml)[0]
    out["after_complete_content_is_v1"] = c.s3.call("GET", k_new)[2] == b"v1"
    out["delete_new"] = c.s3.call("DELETE", k_new)[0]
    out["delete_preexisting"] = c.s3.call("DELETE", s["k_old"])[0]
    out["preexisting_still_there"] = c.s3.call("HEAD", s["k_old"])[0]
    # The open upload created before the lock: can parts still be added and completed?
    d2 = os.urandom(1024)
    pr2 = c.s3.call_presigned("PUT", s["mpu_key"], body=d2, params={"partNumber": "1", "uploadId": s["uid"]})
    xml2 = f"<CompleteMultipartUpload><Part><PartNumber>1</PartNumber><ETag>{pr2[1].get('etag')}</ETag></Part></CompleteMultipartUpload>".encode()
    out["preexisting_mpu_part"] = pr2[0]
    out["preexisting_mpu_complete"] = c.s3.call("POST", s["mpu_key"], params={"uploadId": s["uid"]}, body=xml2)[0]
    out["abort_open_upload_under_lock"] = None
    st3, uid3, _ = F.Runner(c.s3, c.a.name).mpu_create(f"{p}{s['run']}/to-abort")
    out["abort_open_upload_under_lock"] = c.s3.call("DELETE", f"{p}{s['run']}/to-abort", params={"uploadId": uid3})[0]
    c.rec("H9", "C17", f"Age bucket lock on '{p}': overwrite by PUT/presigned PUT/Complete, DELETE, open uploads",
          out, "overwrite and delete refused (403 or similar); behaviour for in-progress uploads undocumented", None)


def h11_mint(c):
    """Run with --ak/--sk of a SEPARATE, disposable token (not the one the Worker uses)."""
    k = c.k("h11")
    c.s3.call("PUT", k, body=b"x")
    pq, _ = c.s3.presign("GET", k, expires=900)  # signed locally with the disposable token
    cred = mint_temp(c.a, c.a.bucket, actions=["GetObject"], objects=[k], ttl=3600)
    ok_url = c.send("GET", pq)[0]
    ok_tmp = temp_call(c, cred, "GET", k)[0]
    save_state(c, {"key": k, "url": pq, "cred": cred, "minted_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                   "pre_check": {"url": ok_url, "temp": ok_tmp}})
    print(json.dumps({"pre_check": {"url": ok_url, "temp": ok_tmp},
                      "next": "Delete (revoke) the disposable R2 token in the dashboard now, note the UTC time, "
                              "then run --only H11-poll --revoked-at <that UTC time, ISO 8601>"}))


def h11_poll(c):
    s = load_state(c)
    t0 = time.time()
    poll_start = dt.datetime.now(dt.timezone.utc)
    log = []
    first_fail = {"url": None, "temp": None}
    while time.time() - t0 < c.a.poll_s:
        st_u = c.send("GET", s["url"])[0]
        st_t = temp_call(c, s["cred"], "GET", s["key"])[0]
        el = round(time.time() - t0, 1)
        log.append((el, st_u, st_t))
        if st_u != 200 and first_fail["url"] is None:
            first_fail["url"] = el
        if st_t != 200 and first_fail["temp"] is None:
            first_fail["temp"] = el
        if first_fail["url"] is not None and first_fail["temp"] is not None:
            break
        time.sleep(5)
    lag = None
    if c.a.revoked_at:
        rv = dt.datetime.fromisoformat(c.a.revoked_at.replace("Z", "+00:00"))
        off = (poll_start - rv).total_seconds()
        lag = {k: (round(v + off, 1) if v is not None else None) for k, v in first_fail.items()}
    c.rec("H11", "C18", "After the parent token is deleted: time until a presigned URL and a temp credential it signed stop working",
          {"pre_check": s.get("pre_check"), "first_fail_s_after_poll_start": first_fail,
           "first_fail_s_after_revocation": lag, "polls": len(log), "last": log[-1] if log else None,
           "poll_window_s": c.a.poll_s},
          "temp creds: 'stop working immediately' (temporary-credentials.mdx); token permission changes: up to a minute "
          "(consistency.mdx); presigned URLs: undocumented. BUD-REVOKE: outstanding URLs dead within 15 min", None)


CHECKS = {"H1": h1, "H2": h2, "H3": h3, "H4": h4, "H5": h5, "H6": h6, "H7": h7, "H10": h10, "H12": h12, "H13": h13,
          "H9-before": h9_before, "H9-after": h9_after, "H11-mint": h11_mint, "H11-poll": h11_poll}
DEFAULT = ["H1", "H2", "H3", "H4", "H5", "H6", "H7", "H10", "H12", "H13"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--endpoint", required=True)
    ap.add_argument("--bucket", required=True)
    ap.add_argument("--region", default="auto")
    ap.add_argument("--ak", required=True)
    ap.add_argument("--sk", required=True)
    ap.add_argument("--account", default=None, help="Cloudflare account ID (JWT sub claim for temp credentials)")
    ap.add_argument("--worker", required=True)
    ap.add_argument("--only", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--state", default="c1s1-state.json")
    ap.add_argument("--lock-prefix", default="c1s1-locked/")
    ap.add_argument("--poll-s", type=int, default=900)
    ap.add_argument("--revoked-at", default=None, help="UTC ISO time the token was deleted (H11-poll)")
    a = ap.parse_args()
    c = Ctx(a)
    todo = a.only.split(",") if a.only else DEFAULT
    t0 = time.time()
    for h in todo:
        try:
            CHECKS[h](c)
        except Exception as e:  # record, do not stop
            c.rec(h, "ERR", "exception", {"error": f"{type(e).__name__}: {e}"}, None, "error")
    out = {"target": a.name, "endpoint": a.endpoint, "bucket": a.bucket, "run_id": c.run,
           "finished_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "duration_s": round(time.time() - t0, 1),
           "results": c.results}
    if a.out:
        with open(a.out, "w") as f:
            json.dump(out, f, indent=1)


if __name__ == "__main__":
    main()
