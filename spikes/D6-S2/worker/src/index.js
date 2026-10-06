// D6-S2 log-audit probe Worker (THROWAWAY; local emulation and the real sandbox kit use the same code).
// Each route puts synthetic markers in one place so the audit can see which log surface records it.
// Markers are synthetic (SYN); never send real personal data to this Worker.
const ok = (o) => new Response(JSON.stringify(o), { headers: { "content-type": "application/json" } });

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    const body = req.method === "POST" ? await req.text() : "";
    switch (url.pathname) {
      case "/clean": {
        // Recommended pattern: structured log with an opaque ID and an outcome only.
        let id = "none";
        try { id = JSON.parse(body).device_id || "none"; } catch {}
        console.log(JSON.stringify({ event: "probe_clean", device_id: id, outcome: "ok" }));
        return ok({ ok: true });
      }
      case "/leaky-console":
        // Anti-pattern (positive control): logs the whole request body.
        console.log("received body", body);
        return ok({ ok: true });
      case "/throw":
        // Uncaught exception whose message contains request data.
        throw new Error("could not process " + body);
      case "/query":
        // Marker only in the query string; the code logs nothing.
        return ok({ ok: true });
      case "/header":
        // Marker only in a request header; the code logs nothing.
        return ok({ ok: true });
      case "/cf":
        // What client metadata the runtime exposes to code (not logged by the code).
        return ok({ cf_country: req.cf && req.cf.country, has_cf_connecting_ip: req.headers.has("cf-connecting-ip") });
      default:
        return new Response("nf", { status: 404 });
    }
  },
};
