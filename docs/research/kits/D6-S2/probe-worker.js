// D6-S2 kit probe Worker (THROWAWAY; sandbox account only, never production).
// Extends spikes/D6-S2/worker/src/index.js with routes for the real-Cloudflare audit.
// Each route puts one synthetic marker in one place so the audit can see which hosted log surface
// (Workers Logs, wrangler tail, traces) records it. Markers are synthetic (SYN): never send real data here.
const ok = (o) => new Response(JSON.stringify(o), { headers: { "content-type": "application/json" } });

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    const body = req.method === "POST" ? await req.text() : "";
    if (url.pathname.startsWith("/path/")) {
      // Marker only in a URL path segment; the code logs nothing.
      return ok({ ok: true });
    }
    switch (url.pathname) {
      case "/whoami":
        // Returns the client IP Cloudflare saw, to the caller only, so the audit can search the logs for it.
        // The code does not log it.
        return ok({ ip: req.headers.get("cf-connecting-ip") || "" });
      case "/clean": {
        // Recommended pattern: structured log with an opaque ID and an outcome only.
        let id = "none";
        try { id = JSON.parse(body).device_id || "none"; } catch {}
        console.log(JSON.stringify({ event: "probe_clean", device_id: id, outcome: "ok" }));
        return ok({ ok: true });
      }
      case "/leaky-console":
        // Anti-pattern (positive control): logs the whole request body as text.
        console.log("received body", body);
        return ok({ ok: true });
      case "/leaky-structured": {
        // Anti-pattern (positive control): logs a personal-data field as a structured key.
        let email = "";
        try { email = JSON.parse(body).email || ""; } catch {}
        console.log({ event: "probe_structured", email });
        return ok({ ok: true });
      }
      case "/throw":
        // Uncaught exception whose message contains request data.
        throw new Error("could not process " + body);
      case "/caught": {
        // Recommended pattern: catch, log a fixed code, return a generic error.
        try { throw new Error("could not process " + body); }
        catch { console.error(JSON.stringify({ event: "probe_caught", code: "E_PROCESS" })); }
        return new Response(JSON.stringify({ error: "E_PROCESS" }), { status: 500, headers: { "content-type": "application/json" } });
      }
      case "/query":   // marker only in the query string
      case "/header":  // marker only in a custom request header
      case "/ua":      // marker only in the User-Agent header
        return ok({ ok: true });
      case "/cf":
        // What client metadata the runtime exposes to code (not logged by the code).
        return ok({ cf_keys: req.cf ? Object.keys(req.cf).sort() : [], has_cf_connecting_ip: req.headers.has("cf-connecting-ip") });
      default:
        return new Response("nf", { status: 404 });
    }
  },
};
