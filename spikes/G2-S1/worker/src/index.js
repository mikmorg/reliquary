// G2-S1 throwaway Worker. Exposes binding-side operations so the test script can check
// binding <-> S3-endpoint interop, and mints presigned URLs with aws4fetch (as A0's Worker would).
import { AwsClient } from "aws4fetch";

const json = (o, s = 200) => new Response(JSON.stringify(o), { status: s, headers: { "content-type": "application/json" } });

export default {
  async fetch(req, env) {
    const u = new URL(req.url);
    const key = u.searchParams.get("key");
    try {
      switch (u.pathname) {
        case "/health": return json({ ok: true });
        case "/presign": {
          const aws = new AwsClient({ accessKeyId: env.S3_AK, secretAccessKey: env.S3_SK, service: "s3", region: env.S3_REGION });
          const target = new URL(`${env.S3_BASE}/${key}`);
          target.searchParams.set("X-Amz-Expires", u.searchParams.get("expires") || "900");
          for (const p of ["partNumber", "uploadId"]) if (u.searchParams.get(p)) target.searchParams.set(p, u.searchParams.get(p));
          const signed = await aws.sign(new Request(target, { method: u.searchParams.get("method") || "PUT" }), { aws: { signQuery: true } });
          return json({ url: signed.url });
        }
        case "/b/get": {
          const o = await env.BUCKET.get(key);
          if (!o) return json({ found: false }, 404);
          const buf = await o.arrayBuffer();
          const h = await crypto.subtle.digest("SHA-256", buf);
          return json({ found: true, size: buf.byteLength, etag: o.etag, sha256: [...new Uint8Array(h)].map(b => b.toString(16).padStart(2, "0")).join("") });
        }
        case "/b/put-create-only": {
          const r = await env.BUCKET.put(key, await req.arrayBuffer(), { onlyIf: new Headers({ "If-None-Match": "*" }) });
          return json({ stored: r !== null, etag: r ? r.etag : null }, r ? 200 : 412);
        }
        case "/b/mpu-create": {
          const m = await env.BUCKET.createMultipartUpload(key);
          return json({ uploadId: m.uploadId, key: m.key });
        }
        case "/b/mpu-complete": {
          const { uploadId, parts } = await req.json();
          const m = env.BUCKET.resumeMultipartUpload(key, uploadId);
          const o = await m.complete(parts);
          return json({ etag: o.etag, size: o.size });
        }
        case "/d1/init": {
          await env.DB.exec("CREATE TABLE IF NOT EXISTS claims (dedup_id TEXT PRIMARY KEY, device TEXT NOT NULL, state TEXT NOT NULL)");
          return json({ ok: true });
        }
        case "/d1/claim": {
          const r = await env.DB.prepare("INSERT INTO claims (dedup_id, device, state) VALUES (?1, ?2, 'claimed') ON CONFLICT(dedup_id) DO NOTHING")
            .bind(key, u.searchParams.get("device") || "dev").run();
          return json({ won: r.meta.changes === 1 });
        }
      }
      return json({ error: "not found" }, 404);
    } catch (e) {
      return json({ error: String(e && e.message || e) }, 500);
    }
  },
};
