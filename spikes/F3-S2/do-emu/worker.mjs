// F3-S2 emulated presence endpoint (Miniflare/workerd, NOT real Cloudflare).
// One Durable Object per device keeps exact counters and enforces a hard cumulative
// lookup budget and an outstanding-claims cap. Presence answers are omitted: this
// harness tests only the accounting (NT-12: "DO counters exact under concurrency").
export class DeviceLedger {
  constructor(state, env) { this.state = state; this.env = env; }
  async fetch(req) {
    const { ids, budget, claimCap } = await req.json();
    const s = this.state.storage;
    // storage ops inside one fetch are covered by the DO input/output gates
    let used = (await s.get('used')) ?? 0;
    let open = (await s.get('open')) ?? 0;
    let refused = (await s.get('refused')) ?? 0;
    const want = ids;
    const room = Math.max(0, Math.min(budget - used, claimCap - open));
    const granted = Math.min(want, room);
    used += granted; open += granted; refused += want - granted;
    await s.put({ used, open, refused });
    return Response.json({ granted, used, open, refused });
  }
}
export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    const dev = url.searchParams.get('device');
    const stub = env.LEDGER.get(env.LEDGER.idFromName(dev));
    return stub.fetch('https://do/lookup', { method: 'POST', body: await req.text() });
  },
};
