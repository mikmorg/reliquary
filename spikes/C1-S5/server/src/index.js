// C1-S5 toy API: one /v1/check endpoint served in five "server generations" so an old client can be
// run against each. The generation is chosen per request by the X-Test-Server-Mode header (a test
// hook only; a real deployment would be one Worker version per generation).
import { Hono } from "hono";
import { z } from "zod";

const MIN_VERSION = { v1: "1.0.0", "v2-add-field": "1.0.0", "v2-add-enum": "1.0.0", "v2-rename": "1.0.0", "v2-break-gated": "2.0.0" };
const cmp = (a, b) => { const x = a.split(".").map(Number), y = b.split(".").map(Number);
  for (let i = 0; i < 3; i++) if ((x[i] || 0) !== (y[i] || 0)) return (x[i] || 0) - (y[i] || 0); return 0; };
const problem = (c, status, code, extra) => c.json({ type: `https://reliquary.invalid/problems/${code}`, title: code.replace(/_/g, " "),
  status, code, retryable: false, ...extra }, status, { "content-type": "application/problem+json" });

const app = new Hono();
app.use("*", async (c, next) => {
  await next();
  c.res.headers.set("Reliquary-Server-Time", String(Date.now()));
});
// Minimum-client-version gate on every /v1 route
app.use("/v1/*", async (c, next) => {
  const mode = c.req.header("X-Test-Server-Mode") || "v1";
  const hdr = c.req.header("Reliquary-Client") || "";
  const m = /^([a-z-]+)\/(\d+\.\d+\.\d+)$/.exec(hdr);
  if (!m) return problem(c, 400, "client_header_missing", {});
  if (cmp(m[2], MIN_VERSION[mode]) < 0) return problem(c, 426, "update_required", { min_version: MIN_VERSION[mode], your_version: m[2] });
  c.set("mode", mode);
  await next();
});

const CheckReq = z.object({ ids: z.array(z.string().regex(/^[0-9a-f]{64}$/)).max(1000) }); // default: unknown keys stripped
const CheckReqStrict = CheckReq.strict();

app.post("/v1/check", async (c) => {
  const mode = c.get("mode");
  const body = await c.req.json().catch(() => null);
  const strict = c.req.query("strict") === "1";
  const parsed = (strict ? CheckReqStrict : CheckReq).safeParse(body);
  if (!parsed.success) return problem(c, 400, "invalid_request", { issues: parsed.error.issues.map((i) => i.code) });
  const statuses = ["MISSING", "IN_FLIGHT", "COMMITTED"];
  const results = parsed.data.ids.map((id, i) => {
    let st = statuses[i % 3];
    if (mode === "v2-add-enum" && i % 4 === 3) st = "QUARANTINED";
    const item = mode === "v2-rename" ? { id, state: st } : { id, status: st };
    if (mode === "v2-add-field") item.committed_at = st === "COMMITTED" ? "2026-10-06T00:00:00Z" : null;
    return item;
  });
  const out = { results };
  if (mode === "v2-add-field") out.server_hint = { next_check_after_s: 30 };
  return c.json(out);
});

export default app;
