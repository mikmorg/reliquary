// D6-S1 minimal-PII control plane (THROWAWAY spike; runs only under `wrangler dev --local`).
// The Worker never receives a name, email address or device name in plaintext:
// the roster entry and verification codes arrive as age ciphertext addressed to the homelab key.
// The only address the cloud side knows is the owner's, pinned in the OWNER_ALERT send_email binding.

const AGE_HEADER = "age-encryption.org/v1\n";
const HOUR = 3600;

const json = (obj, status = 200) =>
  new Response(JSON.stringify(obj), { status, headers: { "content-type": "application/json" } });

async function sha256hex(s) {
  const d = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s));
  return [...new Uint8Array(d)].map((b) => b.toString(16).padStart(2, "0")).join("");
}
function randHex(n) {
  const b = crypto.getRandomValues(new Uint8Array(n));
  return [...b].map((x) => x.toString(16).padStart(2, "0")).join("");
}
function b64decode(s) {
  const bin = atob(s);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}
function b64encode(u8) {
  let s = "";
  for (let i = 0; i < u8.length; i++) s += String.fromCharCode(u8[i]);
  return btoa(s);
}
// Guard: only age ciphertext may be stored on behalf of the homelab. Rejects accidental plaintext.
function isAgeCiphertext(u8) {
  const h = new TextDecoder().decode(u8.slice(0, AGE_HEADER.length));
  return h === AGE_HEADER;
}

// Simulated clock (emulation only). In production this would be Date.now().
async function nowSec(env) {
  if (env.SIM_CLOCK === "1") {
    const r = await env.DB.prepare("SELECT v FROM meta WHERE k='sim_now'").first();
    if (r) return parseInt(r.v, 10);
  }
  return Math.floor(Date.now() / 1000);
}
// Coarse timestamps (D6 key question): floor to TIME_GRANULARITY_S (default 1 h; the real-run kit uses 60 s).
const floorT = (env, t) => { const g = parseInt(env.TIME_GRANULARITY_S || "3600", 10); return Math.floor(t / g) * g; };

async function deviceAuth(req, env) {
  const tok = (req.headers.get("authorization") || "").replace(/^Bearer /, "");
  if (!tok) return null;
  const h = await sha256hex(tok);
  return env.DB.prepare("SELECT device_id, account_id FROM devices WHERE token_hash=?").bind(h).first();
}
function bearerIs(req, secret) {
  return (req.headers.get("authorization") || "") === `Bearer ${secret}`;
}

async function handle(req, env) {
  const url = new URL(req.url);
  const p = url.pathname;

  // ---- emulation-only helpers -------------------------------------------------------------
  if (p === "/v1/sim/now" && req.method === "POST" && env.SIM_CLOCK === "1") {
    const { now } = await req.json();
    await env.DB.prepare("INSERT INTO meta(k,v) VALUES('sim_now',?) ON CONFLICT(k) DO UPDATE SET v=excluded.v")
      .bind(String(now)).run();
    return json({ ok: true });
  }
  if (p === "/v1/sim/try-send-other" && req.method === "POST" && env.SIM_CLOCK === "1") {
    // Does the local simulator enforce destination_address pinning? (C12)
    const { to } = await req.json();
    try {
      const r = await env.OWNER_ALERT.send({ to, from: env.ALERT_FROM, subject: "pin test", text: "pin test" });
      return json({ sent: true, messageId: r && r.messageId });
    } catch (e) {
      return json({ sent: false, code: e.code || null, message: String(e.message || e) });
    }
  }

  // ---- admin: create invite (the admin's code; Worker stores only its hash) ------------------
  if (p === "/v1/admin/invites" && req.method === "POST") {
    if (!bearerIs(req, env.ADMIN_TOKEN)) return json({ error: "unauthorized" }, 401);
    const { code, ttl_days } = await req.json();
    const invite_id = randHex(16);
    const now = await nowSec(env);
    await env.DB.prepare("INSERT INTO invites(invite_id, code_hash, expires_at) VALUES(?,?,?)")
      .bind(invite_id, await sha256hex(code), now + (ttl_days || 30) * 86400).run();
    return json({ invite_id });
  }

  // ---- device: redeem invite ---------------------------------------------------------------
  if (p === "/v1/redeem" && req.method === "POST") {
    const { code, device_pubkey, roster_blob_b64 } = await req.json();
    const now = await nowSec(env);
    const inv = await env.DB.prepare("SELECT * FROM invites WHERE code_hash=?").bind(await sha256hex(code)).first();
    if (!inv || inv.state !== "unused" || inv.expires_at < now) return json({ error: "invalid_invite" }, 400);
    let blob = null;
    if (roster_blob_b64) {
      blob = b64decode(roster_blob_b64);
      if (!isAgeCiphertext(blob)) return json({ error: "roster_blob_must_be_age_ciphertext" }, 400);
    }
    const account_id = randHex(16), device_id = randHex(16), token = randHex(32);
    await env.DB.batch([
      env.DB.prepare("UPDATE invites SET state='redeemed', account_id=? WHERE invite_id=?").bind(account_id, inv.invite_id),
      env.DB.prepare("INSERT INTO accounts(account_id, created_hour) VALUES(?,?)").bind(account_id, floorT(env, now)),
      env.DB.prepare("INSERT INTO devices(device_id, account_id, token_hash, pubkey, enrolled_hour, last_seen_hour) VALUES(?,?,?,?,?,?)")
        .bind(device_id, account_id, await sha256hex(token), device_pubkey, floorT(env, now), floorT(env, now)),
    ]);
    if (blob) await env.INBOX.put(`inbox/roster/${account_id}/${device_id}.age`, blob);
    return json({ account_id, device_id, device_token: token });
  }

  // ---- device: add another device to the same account (ADR-0002 section 3, simplified) --------
  if (p === "/v1/device/add" && req.method === "POST") {
    const d = await deviceAuth(req, env);
    if (!d) return json({ error: "unauthorized" }, 401);
    const { device_pubkey, roster_blob_b64 } = await req.json();
    const now = await nowSec(env);
    let blob = null;
    if (roster_blob_b64) {
      blob = b64decode(roster_blob_b64);
      if (!isAgeCiphertext(blob)) return json({ error: "roster_blob_must_be_age_ciphertext" }, 400);
    }
    const device_id = randHex(16), token = randHex(32);
    await env.DB.prepare("INSERT INTO devices(device_id, account_id, token_hash, pubkey, enrolled_hour, last_seen_hour) VALUES(?,?,?,?,?,?)")
      .bind(device_id, d.account_id, await sha256hex(token), device_pubkey, floorT(env, now), floorT(env, now)).run();
    if (blob) await env.INBOX.put(`inbox/roster/${d.account_id}/${device_id}.age`, blob);
    return json({ account_id: d.account_id, device_id, device_token: token });
  }

  // ---- device: heartbeat, commit, encrypted inbox message ----------------------------------
  if (p === "/v1/heartbeat" && req.method === "POST") {
    const d = await deviceAuth(req, env);
    if (!d) return json({ error: "unauthorized" }, 401);
    const now = await nowSec(env);
    await env.DB.prepare("UPDATE devices SET last_seen_hour=? WHERE device_id=?").bind(floorT(env, now), d.device_id).run();
    return json({ ok: true });
  }
  if (p === "/v1/commit" && req.method === "POST") {
    const d = await deviceAuth(req, env);
    if (!d) return json({ error: "unauthorized" }, 401);
    const { object_id } = await req.json();
    const now = await nowSec(env);
    await env.DB.batch([
      env.DB.prepare("INSERT INTO commits(device_id, object_id, committed_hour) VALUES(?,?,?)").bind(d.device_id, object_id, floorT(env, now)),
      env.DB.prepare("UPDATE devices SET last_commit_hour=?, last_seen_hour=? WHERE device_id=?").bind(floorT(env, now), floorT(env, now), d.device_id),
    ]);
    return json({ ok: true });
  }
  if (p === "/v1/inbox" && req.method === "POST") {
    const d = await deviceAuth(req, env);
    if (!d) return json({ error: "unauthorized" }, 401);
    const { blob_b64 } = await req.json();
    const blob = b64decode(blob_b64);
    if (!isAgeCiphertext(blob)) return json({ error: "blob_must_be_age_ciphertext" }, 400);
    await env.INBOX.put(`inbox/msg/${d.account_id}/${d.device_id}/${randHex(8)}.age`, blob);
    return json({ ok: true });
  }

  // ---- homelab: outbound pull (the homelab is never reachable from here) -------------------
  if (p === "/v1/homelab/pull" && req.method === "POST") {
    if (!bearerIs(req, env.HOMELAB_TOKEN)) return json({ error: "unauthorized" }, 401);
    const { commit_cursor } = await req.json();
    const now = await nowSec(env);
    const commits = (await env.DB.prepare(
      "SELECT seq, device_id, object_id, committed_hour FROM commits WHERE seq>? ORDER BY seq LIMIT 1000"
    ).bind(commit_cursor || 0).all()).results;
    const devices = (await env.DB.prepare(
      "SELECT d.device_id, d.account_id, d.last_seen_hour, d.last_commit_hour, i.invite_id FROM devices d LEFT JOIN invites i ON i.account_id=d.account_id"
    ).all()).results;
    const listed = await env.INBOX.list({ prefix: "inbox/" });
    const blobs = [];
    for (const o of listed.objects) {
      const obj = await env.INBOX.get(o.key);
      blobs.push({ key: o.key, b64: b64encode(new Uint8Array(await obj.arrayBuffer())) });
    }
    await env.DB.prepare("INSERT INTO meta(k,v) VALUES('homelab_last_pull',?) ON CONFLICT(k) DO UPDATE SET v=excluded.v")
      .bind(String(now)).run();
    return json({ now, commits, devices, blobs });
  }
  if (p === "/v1/homelab/ack" && req.method === "POST") {
    if (!bearerIs(req, env.HOMELAB_TOKEN)) return json({ error: "unauthorized" }, 401);
    const { keys } = await req.json();
    for (const k of keys) await env.INBOX.delete(k);
    return json({ ok: true, deleted: keys.length });
  }

  return json({ error: "not_found" }, 404);
}

// Dead-man's switch: if the homelab has not pulled for DMS_HOURS, alert the owner only.
async function deadMansSwitch(env) {
  const now = await nowSec(env);
  const last = await env.DB.prepare("SELECT v FROM meta WHERE k='homelab_last_pull'").first();
  if (!last) return { fired: false, reason: "no_pull_yet" };
  const silentH = (now - parseInt(last.v, 10)) / HOUR;
  if (silentH < parseFloat(env.DMS_HOURS)) return { fired: false, silentH };
  const already = await env.DB.prepare("SELECT v FROM meta WHERE k='dms_alerted_for'").first();
  if (already && already.v === last.v) return { fired: false, reason: "already_alerted", silentH };
  // Production: omit `to`; the binding's destination_address (the owner) is used (send-bindings.mdx).
  // Miniflare 5.20260926.0-alpha does not implement that default (TypeError in extractEmailAddress),
  // so the emulator passes the pinned address explicitly. The pin itself is still enforced locally.
  await env.OWNER_ALERT.send({
    ...(env.EMULATOR_OWNER_TO ? { to: env.EMULATOR_OWNER_TO } : {}),
    from: env.ALERT_FROM,
    subject: "Reliquary: home server has not checked in",
    text: `The home backup server has not contacted the cloud for ${Math.floor(silentH)} hours.`,
  });
  await env.DB.prepare("INSERT INTO meta(k,v) VALUES('dms_alerted_for',?) ON CONFLICT(k) DO UPDATE SET v=excluded.v")
    .bind(last.v).run();
  await env.DB.prepare("INSERT INTO meta(k,v) VALUES('dms_last_fired_at',?) ON CONFLICT(k) DO UPDATE SET v=excluded.v")
    .bind(String(now)).run();
  return { fired: true, silentH };
}

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    if (url.pathname === "/v1/sim/run-dms" && env.SIM_CLOCK === "1") {
      return json(await deadMansSwitch(env));
    }
    return handle(req, env);
  },
  async scheduled(_evt, env, ctx) {
    ctx.waitUntil(deadMansSwitch(env));
  },
};
