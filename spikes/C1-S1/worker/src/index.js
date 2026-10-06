// C1 spikes, EMULATED leg (NOT real R2/Cloudflare). Throwaway research code.
// One Worker exposes the binding-side and in-Worker operations that C1-S1 (R2 behaviour),
// C1-S2 (lease race, D1 vs DO), C1-S3 (1,000-ID presence check) and C1-S4 (presign 200 parts,
// Ed25519 verify cost) need. A Python driver (c1_emulated.py) calls it over HTTP.
import { AwsClient } from "aws4fetch";
import { DurableObject } from "cloudflare:workers";

const json = (o, s = 200) =>
  new Response(JSON.stringify(o), { status: s, headers: { "content-type": "application/json" } });
const hex = (buf) => [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");

function aws(env) {
  return new AwsClient({ accessKeyId: env.S3_AK, secretAccessKey: env.S3_SK, service: "s3", region: env.S3_REGION });
}

async function presign(client, env, key, method, expires, params, headers, allHeaders) {
  const target = new URL(`${env.S3_BASE}/${key}`);
  target.searchParams.set("X-Amz-Expires", String(expires));
  for (const [k, v] of Object.entries(params || {})) target.searchParams.set(k, v);
  const signed = await client.sign(new Request(target, { method, headers: headers || {} }), {
    aws: { signQuery: true, allHeaders: !!allHeaders },
  });
  return signed.url;
}

// ---- C1-S2: Durable Object lease shard ------------------------------------------------
export class LeaseShard extends DurableObject {
  constructor(ctx, env) {
    super(ctx, env);
    this.sql = ctx.storage.sql;
    this.sql.exec(`CREATE TABLE IF NOT EXISTS uploads (upload_id TEXT PRIMARY KEY, dedup_id TEXT NOT NULL,
      device_id TEXT NOT NULL, state TEXT NOT NULL, lease_expires_at INTEGER NOT NULL)`);
    this.sql.exec(`CREATE INDEX IF NOT EXISTS uploads_dedup ON uploads(dedup_id, lease_expires_at)`);
  }
  lease(dedup, device, ttlMs) {
    const now = Date.now();
    const uploadId = crypto.randomUUID();
    return this.ctx.storage.transactionSync(() => {
      const live = this.sql
        .exec(`SELECT count(*) AS c FROM uploads WHERE dedup_id = ? AND state = 'claimed' AND lease_expires_at > ?`, dedup, now)
        .one().c;
      if (live > 0) return { won: false };
      this.sql.exec(`INSERT INTO uploads VALUES (?, ?, ?, 'claimed', ?)`, uploadId, dedup, device, now + ttlMs);
      return { won: true, uploadId };
    });
  }
  expire(dedup) {
    this.sql.exec(`UPDATE uploads SET lease_expires_at = 0 WHERE dedup_id = ?`, dedup);
    return true;
  }
  dupcheck() {
    const now = Date.now();
    const rows = this.sql
      .exec(`SELECT dedup_id, count(*) AS c FROM uploads WHERE state = 'claimed' AND lease_expires_at > ?
             GROUP BY dedup_id HAVING c > 1`, now)
      .toArray();
    const total = this.sql.exec(`SELECT count(*) AS c FROM uploads`).one().c;
    const ids = this.sql.exec(`SELECT count(DISTINCT dedup_id) AS c FROM uploads`).one().c;
    return { dup_ids: rows.length, sample: rows.slice(0, 5), rows: total, distinct_ids: ids };
  }
  reset() {
    this.sql.exec(`DELETE FROM uploads`);
    return true;
  }
}

const shard = (env, dedup) => env.LEASES.get(env.LEASES.idFromName("shard-" + dedup[0]));

export default {
  async fetch(req, env) {
    const u = new URL(req.url);
    const p = u.searchParams;
    const key = p.get("key");
    try {
      switch (u.pathname) {
        case "/health":
          return json({ ok: true });
        case "/noop":
          return json({ ok: true });

        // ---- C1-S1 helpers --------------------------------------------------------------
        case "/presign": {
          const params = {};
          for (const k of ["partNumber", "uploadId"]) if (p.get(k)) params[k] = p.get(k);
          if (p.get("uploads") !== null) params["uploads"] = "";
          const headers = p.get("h") ? JSON.parse(p.get("h")) : {};
          const url = await presign(aws(env), env, key, p.get("method") || "PUT", p.get("expires") || "900", params, headers, p.get("all") === "1");
          return json({ url, signedHeaders: new URL(url).searchParams.get("X-Amz-SignedHeaders") });
        }
        case "/b/put": {
          const o = await env.BUCKET.put(key, await req.arrayBuffer());
          return json({ etag: o.etag, httpEtag: o.httpEtag, size: o.size, md5: o.checksums.md5 ? hex(o.checksums.md5) : null });
        }
        case "/b/put-onlyif": {
          // form=headers: onlyIf as a Headers object; form=cond: onlyIf as an R2Conditional object
          const onlyIf = p.get("form") === "cond" ? { etagDoesNotMatch: "*" } : new Headers({ "If-None-Match": "*" });
          const r = await env.BUCKET.put(key, await req.arrayBuffer(), { onlyIf });
          return json({ stored: r !== null, etag: r ? r.etag : null }, r ? 200 : 412);
        }
        case "/b/put-sha256": {
          let r, err = null;
          try { r = await env.BUCKET.put(key, await req.arrayBuffer(), { sha256: p.get("sha") }); }
          catch (e) { err = String((e && e.message) || e); }
          const after = await env.BUCKET.head(key);
          return json({ threw: err, stored: !!after, size: after ? after.size : null });
        }
        case "/b/head": {
          const o = await env.BUCKET.head(key);
          if (!o) return json({ found: false }, 404);
          const cs = {};
          for (const [k, v] of Object.entries(o.checksums.toJSON ? o.checksums.toJSON() : {})) cs[k] = v ? (typeof v === "string" ? v : hex(v)) : null;
          return json({ found: true, etag: o.etag, httpEtag: o.httpEtag, size: o.size, checksums: cs });
        }
        case "/b/mpu-create": {
          const m = await env.BUCKET.createMultipartUpload(key);
          return json({ uploadId: m.uploadId, key: m.key });
        }
        case "/b/mpu-complete": {
          const { uploadId, parts } = await req.json();
          const o = await env.BUCKET.resumeMultipartUpload(key, uploadId).complete(parts);
          return json({ etag: o.etag, httpEtag: o.httpEtag, size: o.size });
        }

        // ---- C1-S4: presign many UploadPart URLs in one request ---------------------------
        case "/presign-many": {
          const n = parseInt(p.get("n") || "200", 10);
          const client = aws(env);
          const t0 = performance.now(), d0 = Date.now();
          const urls = [];
          for (let i = 1; i <= n; i++) {
            urls.push(await presign(client, env, key, "PUT", p.get("expires") || "900", { partNumber: String(i), uploadId: p.get("uploadId") || "x" }));
          }
          const t1 = performance.now(), d1 = Date.now();
          return json({ n, perf_ms: t1 - t0, date_ms: d1 - d0, urls: p.get("urls") === "0" ? undefined : urls });
        }
        case "/bench/ed25519": {
          const n = parseInt(p.get("n") || "1000", 10);
          const kp = await crypto.subtle.generateKey({ name: "Ed25519" }, true, ["sign", "verify"]);
          const msg = new Uint8Array(256);
          crypto.getRandomValues(msg);
          const sig = await crypto.subtle.sign({ name: "Ed25519" }, kp.privateKey, msg);
          const t0 = performance.now(), d0 = Date.now();
          let ok = 0;
          for (let i = 0; i < n; i++) if (await crypto.subtle.verify({ name: "Ed25519" }, kp.publicKey, sig, msg)) ok++;
          const t1 = performance.now(), d1 = Date.now();
          return json({ n, ok, perf_ms: t1 - t0, date_ms: d1 - d0 });
        }

        // ---- C1-S2: D1 lease race ----------------------------------------------------------
        case "/d1/init": {
          await env.DB.batch([
            env.DB.prepare(`CREATE TABLE IF NOT EXISTS uploads (upload_id TEXT PRIMARY KEY, dedup_id TEXT NOT NULL,
              device_id TEXT NOT NULL, state TEXT NOT NULL, lease_expires_at INTEGER NOT NULL)`),
            env.DB.prepare(`CREATE INDEX IF NOT EXISTS uploads_dedup ON uploads(dedup_id, lease_expires_at)`),
            env.DB.prepare(`CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, ref TEXT NOT NULL)`),
            env.DB.prepare(`DELETE FROM uploads`),
            env.DB.prepare(`DELETE FROM events`),
          ]);
          return json({ ok: true });
        }
        case "/d1/lease": {
          const now = Date.now();
          const ttl = parseInt(p.get("ttl") || "600000", 10);
          const uploadId = crypto.randomUUID();
          const dedup = p.get("dedup");
          const res = await env.DB.batch([
            env.DB.prepare(`INSERT INTO uploads (upload_id, dedup_id, device_id, state, lease_expires_at)
              SELECT ?1, ?2, ?3, 'claimed', ?4 WHERE NOT EXISTS
              (SELECT 1 FROM uploads WHERE dedup_id = ?2 AND state = 'claimed' AND lease_expires_at > ?5)`)
              .bind(uploadId, dedup, p.get("device") || "dev", now + ttl, now),
            env.DB.prepare(`INSERT INTO events (kind, ref) SELECT 'lease', ?1 WHERE EXISTS (SELECT 1 FROM uploads WHERE upload_id = ?1)`)
              .bind(uploadId),
          ]);
          return json({ won: res[0].meta.changes === 1, ev: res[1].meta.changes, d: res[0].meta.duration });
        }
        case "/d1/expire": {
          await env.DB.prepare(`UPDATE uploads SET lease_expires_at = 0 WHERE dedup_id = ?1`).bind(p.get("dedup")).run();
          return json({ ok: true });
        }
        case "/d1/dupcheck": {
          const now = Date.now();
          const r = await env.DB.batch([
            env.DB.prepare(`SELECT dedup_id, count(*) AS c FROM uploads WHERE state = 'claimed' AND lease_expires_at > ?1
              GROUP BY dedup_id HAVING c > 1`).bind(now),
            env.DB.prepare(`SELECT count(*) AS c, count(DISTINCT dedup_id) AS ids FROM uploads`),
            env.DB.prepare(`SELECT count(*) AS c FROM events`),
          ]);
          return json({ dup_ids: r[0].results.length, sample: r[0].results.slice(0, 5), rows: r[1].results[0].c,
            distinct_ids: r[1].results[0].ids, events: r[2].results[0].c });
        }

        // ---- C1-S2: DO lease race ---------------------------------------------------------
        case "/do/lease": {
          const dedup = p.get("dedup");
          return json(await shard(env, dedup).lease(dedup, p.get("device") || "dev", parseInt(p.get("ttl") || "600000", 10)));
        }
        case "/do/expire": {
          const dedup = p.get("dedup");
          return json({ ok: await shard(env, dedup).expire(dedup) });
        }
        case "/do/dupcheck": {
          const out = { dup_ids: 0, rows: 0, distinct_ids: 0, sample: [] };
          for (const c of "0123456789abcdef") {
            const r = await env.LEASES.get(env.LEASES.idFromName("shard-" + c)).dupcheck();
            out.dup_ids += r.dup_ids; out.rows += r.rows; out.distinct_ids += r.distinct_ids; out.sample.push(...r.sample);
          }
          return json(out);
        }
        case "/do/reset": {
          for (const c of "0123456789abcdef") await env.LEASES.get(env.LEASES.idFromName("shard-" + c)).reset();
          return json({ ok: true });
        }

        // ---- C1-S3: presence check ----------------------------------------------------------
        case "/s3/init": {
          await env.DB.prepare(`CREATE TABLE IF NOT EXISTS dedup (id BLOB PRIMARY KEY, state INTEGER NOT NULL DEFAULT 1) WITHOUT ROWID`).run();
          return json({ ok: true });
        }
        case "/s3/fill": {
          const n = parseInt(p.get("n") || "100000", 10);
          const r = await env.DB.prepare(`INSERT INTO dedup (id) WITH RECURSIVE c(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM c WHERE x < ?1)
            SELECT randomblob(32) FROM c`).bind(n).run();
          return json({ meta: r.meta });
        }
        case "/s3/count": {
          const r = await env.DB.prepare(`SELECT count(*) AS c FROM dedup`).first();
          return json(r);
        }
        case "/s3/sample": {
          const n = parseInt(p.get("n") || "500", 10);
          const st = env.DB.prepare(`SELECT hex(id) AS h FROM dedup WHERE id >= randomblob(32) LIMIT 1`);
          const r = await env.DB.batch(Array.from({ length: n }, () => st));
          return json({ ids: r.map((x) => x.results[0] && x.results[0].h).filter(Boolean) });
        }
        case "/s3/plan": {
          const r = await env.DB.prepare(`EXPLAIN QUERY PLAN SELECT j.value FROM json_each(?1) j
            WHERE NOT EXISTS (SELECT 1 FROM dedup d WHERE d.id = unhex(j.value))`).bind("[]").all();
          return json(r.results);
        }
        case "/s3/missing": {
          const { ids } = await req.json();
          const variant = p.get("variant") || "json_each";
          if (variant === "json_each") {
            const r = await env.DB.prepare(`SELECT j.value AS id FROM json_each(?1) j
              WHERE NOT EXISTS (SELECT 1 FROM dedup d WHERE d.id = unhex(j.value))`).bind(JSON.stringify(ids)).all();
            return json({ missing: r.results.length, meta: r.meta });
          }
          // variant=in100: chunks of 100 bound parameters in one batch (the per-query parameter cap)
          const stmts = [];
          for (let i = 0; i < ids.length; i += 100) {
            const chunk = ids.slice(i, i + 100);
            stmts.push(env.DB.prepare(`SELECT hex(id) AS h FROM dedup WHERE id IN (${chunk.map((_, j) => `unhex(?${j + 1})`).join(",")})`).bind(...chunk));
          }
          const r = await env.DB.batch(stmts);
          const present = r.reduce((a, x) => a + x.results.length, 0);
          const meta = r.reduce((a, x) => ({ rows_read: a.rows_read + (x.meta.rows_read || 0), duration: a.duration + (x.meta.duration || 0) }), { rows_read: 0, duration: 0 });
          return json({ missing: ids.length - present, statements: stmts.length, meta });
        }
      }
      return json({ error: "not found" }, 404);
    } catch (e) {
      return json({ error: String((e && e.message) || e), stack: e && e.stack }, 500);
    }
  },
};
