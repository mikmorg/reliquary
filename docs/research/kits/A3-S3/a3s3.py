#!/usr/bin/env python3
"""A3-S3 kit: real-R2 multipart resume after 24 h and after 7 days (THROWAWAY research code).

Stdlib only. Reuses the SigV4 signer from spikes/G2-S1/fidelity.py so that requests are
byte-identical to the G2-S1 fidelity run. Parts are uploaded through presigned UploadPart
URLs (as a device would), with a 900 s expiry (BUD-REVOKE: outstanding URLs <= 15 min).

Payload is synthetic: part i is a deterministic SHA-256 counter stream from --seed, so the
script can regenerate any part (and the expected whole-object SHA-256) without storing data.

Subcommands (all print one JSON line per observation and append it to --log):
  init        create a multipart upload, upload the first K parts, write a journal
  resume      ListParts, compare ETags with the journal, upload ONLY missing parts,
              complete, GET and verify SHA-256; reports bytes re-sent for journaled parts
  checkpoint  segment checkpoint (A3 F2 option 1): complete parts 1..k as segment s0,
              start a new upload s1 for the rest, finish it, verify the concatenated SHA-256
  probe       is the upload still there? (ListMultipartUploads + ListParts + one UploadPart)
  lifecycle-get / lifecycle-put   read or set AbortIncompleteMultipartUpload rules
  cleanup     abort every multipart upload and delete every object under --prefix

Data-handling class: SYN -> results.
"""
import argparse, datetime as dt, hashlib, json, os, re, sys, time, uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3] / "spikes" / "G2-S1"))
from fidelity import S3, err_code  # noqa: E402

MiB = 1024 * 1024


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def part_bytes(seed, n, size):
    """Deterministic synthetic bytes for part n (1-based)."""
    out = bytearray()
    ctr = 0
    while len(out) < size:
        out += hashlib.sha256(f"{seed}:{n}:{ctr}".encode()).digest()
        ctr += 1
    return bytes(out[:size])


def part_sizes(j):
    sizes = [j["part_size"]] * j["nparts"]
    sizes[-1] = j["last_part_size"]
    return sizes


def expected_sha256(j, first=1, last=None):
    h = hashlib.sha256()
    sizes = part_sizes(j)
    last = last or j["nparts"]
    for n in range(first, last + 1):
        h.update(part_bytes(j["seed"], n, sizes[n - 1]))
    return h.hexdigest()


class Kit:
    def __init__(self, a):
        self.a = a
        self.s3 = S3(a.endpoint, a.bucket, a.ak, a.sk, region=a.region, timeout=300)
        self.log = Path(a.log)

    def emit(self, **kv):
        kv = {"t": now(), **kv}
        line = json.dumps(kv, sort_keys=True)
        print(line)
        with self.log.open("a") as f:
            f.write(line + "\n")

    # ---- S3 primitives (header-signed, as the Worker would) ----
    def create(self, key):
        st, h, b = self.s3.call("POST", key, params={"uploads": ""})
        m = re.search(rb"<UploadId>([^<]+)</UploadId>", b)
        return st, (m.group(1).decode() if m else None), err_code(b)

    def upload_part_presigned(self, key, upload_id, n, data):
        st, h, b = self.s3.call_presigned("PUT", key, body=data, expires=900,
                                          params={"partNumber": str(n), "uploadId": upload_id})
        return st, h.get("etag"), err_code(b)

    def list_parts(self, key, upload_id):
        parts, marker = {}, None
        while True:
            params = {"uploadId": upload_id, "max-parts": "1000"}
            if marker:
                params["part-number-marker"] = marker
            st, h, b = self.s3.call("GET", key, params=params)
            if st != 200:
                return st, None, err_code(b)
            for m in re.finditer(rb"<Part>(.*?)</Part>", b, re.S):
                pn = int(re.search(rb"<PartNumber>(\d+)</PartNumber>", m.group(1)).group(1))
                et = re.search(rb"<ETag>([^<]+)</ETag>", m.group(1)).group(1).decode().replace("&quot;", '"')
                parts[pn] = et
            if b"<IsTruncated>true</IsTruncated>" not in b:
                return st, parts, None
            marker = re.search(rb"<NextPartNumberMarker>(\d+)</NextPartNumberMarker>", b).group(1).decode()

    def complete(self, key, upload_id, etags):
        body = "<CompleteMultipartUpload>" + "".join(
            f"<Part><PartNumber>{n}</PartNumber><ETag>{etags[n]}</ETag></Part>" for n in sorted(etags)
        ) + "</CompleteMultipartUpload>"
        st, h, b = self.s3.call("POST", key, params={"uploadId": upload_id}, body=body.encode())
        ok = st == 200 and b"<Error>" not in b  # S3 may return 200 with an <Error> body
        return st, ok, err_code(b)

    def get_sha256(self, key):
        st, h, b = self.s3.call("GET", key)
        return st, (hashlib.sha256(b).hexdigest() if st == 200 else None), len(b)

    def list_uploads(self, prefix):
        st, h, b = self.s3.call("GET", None, params={"uploads": "", "prefix": prefix})
        ups = [(re.search(rb"<Key>([^<]+)</Key>", m.group(1)).group(1).decode(),
                re.search(rb"<UploadId>([^<]+)</UploadId>", m.group(1)).group(1).decode())
               for m in re.finditer(rb"<Upload>(.*?)</Upload>", b, re.S)]
        return st, ups, err_code(b)

    # ---- subcommands ----
    def init(self):
        a = self.a
        key = f"{a.prefix.rstrip('/')}/{a.tag}/{uuid.uuid4()}"
        st, uid, ec = self.create(key)
        self.emit(step="create", tag=a.tag, key=key, status=st, upload_id=uid, error=ec)
        if not uid:
            sys.exit(2)
        j = {"tag": a.tag, "key": key, "upload_id": uid, "seed": a.seed, "part_size": a.part_mib * MiB,
             "last_part_size": a.last_part_kib * 1024, "nparts": a.parts, "created_at": now(), "etags": {}}
        sizes = part_sizes(j)
        for n in range(1, a.upload_parts + 1):
            st, et, ec = self.upload_part_presigned(key, uid, n, part_bytes(a.seed, n, sizes[n - 1]))
            self.emit(step="upload_part", tag=a.tag, part=n, status=st, etag=et, error=ec)
            if st == 200 and et:
                j["etags"][str(n)] = et
        Path(a.journal).write_text(json.dumps(j, indent=1))
        self.emit(step="journal_written", tag=a.tag, journal=a.journal, parts_done=len(j["etags"]))

    def resume(self):
        a = self.a
        j = json.loads(Path(a.journal).read_text())
        key, uid = j["key"], j["upload_id"]
        age_h = (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(j["created_at"])).total_seconds() / 3600
        st, listed, ec = self.list_parts(key, uid)
        self.emit(step="list_parts", tag=j["tag"], age_hours=round(age_h, 2), status=st, error=ec,
                  listed=sorted(listed) if listed else None)
        if listed is None:
            self.emit(step="RESULT", tag=j["tag"], outcome="upload-gone", status=st, error=ec,
                      note="protocol must reclaim: ask Worker for state, restart with a new upload id")
            return
        # adopt only parts whose listed ETag equals the journal (CE 8.5); never re-send journaled parts (C12)
        adopted = {int(n): e for n, e in j["etags"].items() if listed.get(int(n)) == e}
        mismatched = [int(n) for n, e in j["etags"].items() if int(n) in listed and listed[int(n)] != e]
        missing = [n for n in range(1, j["nparts"] + 1) if n not in adopted]
        self.emit(step="plan", tag=j["tag"], adopted=sorted(adopted), mismatched=mismatched, to_upload=missing)
        sizes = part_sizes(j)
        resent_journaled_bytes = 0
        etags = dict(adopted)
        for n in missing:
            if str(n) in j["etags"]:
                resent_journaled_bytes += sizes[n - 1]
            st, et, ec = self.upload_part_presigned(key, uid, n, part_bytes(j["seed"], n, sizes[n - 1]))
            self.emit(step="upload_part", tag=j["tag"], part=n, status=st, etag=et, error=ec)
            if st != 200:
                self.emit(step="RESULT", tag=j["tag"], outcome="upload-part-failed", status=st, error=ec)
                return
            etags[n] = et
        st, ok, ec = self.complete(key, uid, etags)
        self.emit(step="complete", tag=j["tag"], status=st, ok=ok, error=ec)
        gst, sha, ln = self.get_sha256(key)
        exp = expected_sha256(j)
        self.emit(step="RESULT", tag=j["tag"], outcome="completed" if ok and sha == exp else "mismatch",
                  sha256_ok=(sha == exp), length=ln, resent_journaled_bytes=resent_journaled_bytes,
                  age_hours=round(age_h, 2))

    def checkpoint(self):
        a = self.a
        j = json.loads(Path(a.journal).read_text())
        key, uid = j["key"], j["upload_id"]
        st, listed, ec = self.list_parts(key, uid)
        if listed is None:
            self.emit(step="RESULT", tag=j["tag"], outcome="upload-gone-before-checkpoint", status=st, error=ec)
            return
        k = 0
        while str(k + 1) in j["etags"] and listed.get(k + 1) == j["etags"][str(k + 1)]:
            k += 1
        s0 = {n: j["etags"][str(n)] for n in range(1, k + 1)}
        st, ok, ec = self.complete(key, uid, s0)  # same key becomes segment s0
        self.emit(step="complete_segment_s0", tag=j["tag"], parts=k, status=st, ok=ok, error=ec)
        if not ok:
            self.emit(step="RESULT", tag=j["tag"], outcome="checkpoint-complete-failed", status=st, error=ec)
            return
        key1 = key + ".s1"
        st, uid1, ec = self.create(key1)
        self.emit(step="create_segment_s1", tag=j["tag"], status=st, upload_id=uid1, error=ec)
        sizes = part_sizes(j)
        et1 = {}
        for i, n in enumerate(range(k + 1, j["nparts"] + 1), start=1):
            st, et, ec = self.upload_part_presigned(key1, uid1, i, part_bytes(j["seed"], n, sizes[n - 1]))
            self.emit(step="upload_part_s1", tag=j["tag"], part=i, source_part=n, status=st, error=ec)
            et1[i] = et
        st, ok1, ec = self.complete(key1, uid1, et1)
        self.emit(step="complete_segment_s1", tag=j["tag"], status=st, ok=ok1, error=ec)
        s0st, s0sha, _ = self.get_sha256(key)
        s1st, s1sha, _ = self.get_sha256(key1)
        self.emit(step="RESULT", tag=j["tag"], outcome="checkpointed" if ok and ok1 else "failed",
                  s0_sha256_ok=(s0sha == expected_sha256(j, 1, k)),
                  s1_sha256_ok=(s1sha == expected_sha256(j, k + 1, j["nparts"])),
                  note="homelab concatenates s0||s1; compare with expected whole-object SHA-256 offline")

    def probe(self):
        a = self.a
        j = json.loads(Path(a.journal).read_text())
        key, uid = j["key"], j["upload_id"]
        age_h = (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(j["created_at"])).total_seconds() / 3600
        st, ups, ec = self.list_uploads(j["key"])
        present = any(u == uid for _, u in ups)
        lst, listed, lec = self.list_parts(key, uid)
        self.emit(step="probe", tag=j["tag"], age_hours=round(age_h, 2), list_uploads_status=st,
                  upload_listed=present, list_parts_status=lst, list_parts_error=lec,
                  parts_listed=sorted(listed) if listed else None)
        if a.try_part:
            # one throwaway part at a part number beyond nparts, so journaled parts are never replaced
            n = min(j["nparts"] + 1, 10000)
            pst, pet, pec = self.upload_part_presigned(key, uid, n, part_bytes("probe", n, j["part_size"]))
            self.emit(step="probe_upload_part", tag=j["tag"], part=n, status=pst, error=pec)

    def lifecycle_get(self):
        st, h, b = self.s3.call("GET", None, params={"lifecycle": ""})
        self.emit(step="lifecycle_get", status=st, error=err_code(b), body=b.decode(errors="replace")[:4000])

    def lifecycle_put(self):
        a = self.a
        rules = []
        for spec in a.rule:  # "id:prefix:days"
            rid, pfx, days = spec.split(":")
            rules.append(f"<Rule><ID>{rid}</ID><Filter><Prefix>{pfx}</Prefix></Filter><Status>Enabled</Status>"
                         f"<AbortIncompleteMultipartUpload><DaysAfterInitiation>{int(days)}</DaysAfterInitiation>"
                         f"</AbortIncompleteMultipartUpload></Rule>")
        body = ("<LifecycleConfiguration>" + "".join(rules) + "</LifecycleConfiguration>").encode()
        import base64
        md5 = base64.b64encode(hashlib.md5(body).digest()).decode()
        st, h, b = self.s3.call("PUT", None, params={"lifecycle": ""}, body=body, headers={"content-md5": md5})
        self.emit(step="lifecycle_put", status=st, error=err_code(b), rules=a.rule,
                  body=b.decode(errors="replace")[:2000])

    def cleanup(self):
        a = self.a
        st, ups, ec = self.list_uploads(a.prefix)
        for key, uid in ups:
            s, h, b = self.s3.call("DELETE", key, params={"uploadId": uid})
            self.emit(step="abort", key=key, status=s, error=err_code(b))
        st, h, b = self.s3.call("GET", None, params={"list-type": "2", "prefix": a.prefix})
        for m in re.finditer(rb"<Key>([^<]+)</Key>", b):
            key = m.group(1).decode()
            s, h2, b2 = self.s3.call("DELETE", key)
            self.emit(step="delete", key=key, status=s, error=err_code(b2))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("cmd", choices=["init", "resume", "checkpoint", "probe", "lifecycle-get", "lifecycle-put", "cleanup"])
    p.add_argument("--endpoint", default=os.environ.get("A3S3_ENDPOINT"))
    p.add_argument("--bucket", default=os.environ.get("A3S3_BUCKET"))
    p.add_argument("--ak", default=os.environ.get("A3S3_AK"))
    p.add_argument("--sk", default=os.environ.get("A3S3_SK"))
    p.add_argument("--region", default="auto")
    p.add_argument("--prefix", default="a3s3/")
    p.add_argument("--tag", default="u24")
    p.add_argument("--journal", default="journal-u24.json")
    p.add_argument("--log", default="a3s3-log.jsonl")
    p.add_argument("--seed", default="a3s3-seed-1")
    p.add_argument("--parts", type=int, default=6)
    p.add_argument("--part-mib", type=int, default=5)
    p.add_argument("--last-part-kib", type=int, default=777)
    p.add_argument("--upload-parts", type=int, default=3)
    p.add_argument("--try-part", action="store_true")
    p.add_argument("--rule", action="append", default=[], help="id:prefix:days (repeatable)")
    a = p.parse_args()
    for k in ("endpoint", "bucket", "ak", "sk"):
        if not getattr(a, k):
            p.error(f"--{k} (or env A3S3_{k.upper()}) is required")
    getattr(Kit(a), a.cmd.replace("-", "_"))()


if __name__ == "__main__":
    main()
