// D6-S1 kit, optional step (claim C11 in the D6 note): which recipients can an UNRESTRICTED send_email binding reach
// once a sending domain is onboarded? send-bindings.mdx says "any verified destination address"; limits.mdx says
// "any recipient" after onboarding. Deploy with a binding that has no restriction attribute:
//   "send_email": [{ "name": "EMAIL" }]
// then POST {"to": "<test inbox that is NOT a verified destination>", "from": "probe@<sending subdomain>"} with the
// header `x-probe-key: <random value set as the PROBE_KEY secret>`. Delete the Worker right after the test.
export default {
  async fetch(req, env) {
    if (req.method !== "POST" || req.headers.get("x-probe-key") !== env.PROBE_KEY) return new Response("no", { status: 403 });
    const { to, from } = await req.json();
    try {
      const r = await env.EMAIL.send({ to, from, subject: "D6-S1 C11 probe", text: "C11 probe: binding recipient scope." });
      return Response.json({ sent: true, messageId: r.messageId });
    } catch (e) {
      // Only the error code and message are returned; this probe logs nothing.
      return Response.json({ sent: false, code: e.code || null, message: String(e.message || e) });
    }
  },
};
