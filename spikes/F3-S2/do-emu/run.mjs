import { Miniflare } from 'miniflare';
const mf = new Miniflare({
  modules: true, scriptPath: 'worker.mjs', port: 0,
  durableObjects: { LEDGER: 'DeviceLedger' },
});
const BUDGET = 5000, CAP = 1_000_000;
async function trial(device, clients, reqs, maxBatch, budget, cap) {
  let sent = 0, granted = 0;
  const one = async () => {
    for (let i = 0; i < reqs; i++) {
      const n = 1 + Math.floor(Math.random() * maxBatch); sent += n;
      const r = await mf.dispatchFetch(`http://x/?device=${device}`, { method: 'POST',
        body: JSON.stringify({ ids: n, budget, claimCap: cap }) });
      const g = (await r.json()).granted; granted += g;  // read-then-add: avoid the JS `x += await` lost-update race
    }
  };
  await Promise.all(Array.from({ length: clients }, one));
  const r = await mf.dispatchFetch(`http://x/?device=${device}`, { method: 'POST',
    body: JSON.stringify({ ids: 0, budget, claimCap: cap }) });
  return { device, clients, reqs, sent, granted_sum_seen_by_clients: granted, ledger: await r.json() };
}
const out = []; console.error('start');
// (a) no budget binding: counters must equal the exact number of IDs sent
out.push(await trial('dev-a', 20, 100, 20, 1e12, 1e12));
// (b) hard budget 5000: granted must never exceed 5000 under 50 concurrent clients
out.push(await trial('dev-b', 20, 100, 20, BUDGET, CAP));
// (c) outstanding-claims cap 1000
out.push(await trial('dev-c', 20, 100, 20, 1e12, 1000));
for (const o of out) {
  const L = o.ledger;
  o.checks = {
    used_equals_granted: L.used === o.granted_sum_seen_by_clients,
    used_plus_refused_equals_sent: L.used + L.refused === o.sent,
  };
}
console.log(JSON.stringify(out, null, 1));
await mf.dispose();
