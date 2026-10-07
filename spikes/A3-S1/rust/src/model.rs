//! A3-S1: explicit-state model of the Reliquary v0 ingest protocol
//! (docs/research/a3-ingest-protocol.md F1-F8, D1 SR-01..SR-12).
//!
//! Abstractions (see README for the full list):
//! - dedup_id == plaintext content id (HMAC abstracted as identity); a poisoner
//!   uploads BAD bytes under a valid dedup_id.
//! - one record per (slot, attempt); record ids are never reused (UUIDs).
//! - one staging key per upload (per-upload keys); upload id == record id.
//! - all multipart parts are one action; R2 is strongly consistent (C10).
//! - device<->Worker calls are atomic with an optional lost response
//!   (Worker effect applied, device state unchanged).
//! - time is nondeterministic: lease expiry, valve, R2 lifecycle abort.

use std::fmt;

pub const MAX_SLOTS: usize = 9;
pub const MAX_CONTENTS: usize = 4;

#[derive(Clone, Debug)]
pub struct DevCfg {
    pub items: Vec<u8>, // content id (== dedup id) of each item on this device
    pub poisoner: bool, // uploads BAD bytes under the claimed dedup id
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum Mode {
    /// Homelab ingests any record it can list in meta/ (path of record).
    Reconcile,
    /// Homelab ingests only records whose queue hint it pulled (mutant M4).
    QueueOnly,
}

#[derive(Clone, Debug, Default)]
pub struct Mutants {
    pub no_verify: bool,         // M1: homelab skips SHA-256/HMAC check
    pub early_delete: bool,      // M2: staging deleted before durable commit
    pub hit_is_safe: bool,       // M3: device treats IN_FLIGHT/COMMITTED as safe
    pub no_valve: bool,          // M5: no re-check and no safety valve
    pub publish_once: bool,      // M6: receipts never republished after D1 loss
    pub resign: bool,            // M7: homelab re-signs on redelivery
    pub trust_worker_commit: bool, // M8: homelab-free "committed" mark => safe
}

#[derive(Clone, Debug)]
pub struct Cfg {
    pub name: String,
    pub devs: Vec<DevCfg>,
    pub ncontents: usize,
    pub max_att: usize,     // attempts (records) per slot
    pub poison_att: usize,  // attempts for the poisoner's slots (<= max_att)
    pub max_faults: u8,     // counted faults: device reset, live abort, D1 wipe, worker lie
    pub f_device_reset: bool,
    pub f_abort_live: bool,
    pub f_d1_wipe: bool,
    pub f_worker_lie: bool,
    pub lost_responses: bool,
    pub orphan_gc: bool,
    /// Spec fix candidate: a record whose content object was orphan-GC'd by
    /// the homelab is rejected with typed code content-missing (re-upload).
    pub gc_typed_reject: bool,
    pub symmetry: bool,
    /// Spec fix candidate: the complete call carries the signed record; the
    /// Worker writes meta/ first, then completes the multipart upload, so a
    /// completed staging object always has a record.
    pub record_first: bool,
    /// With record_first: a record whose multipart upload is gone (aborted)
    /// and whose staging object does not exist gets typed reject
    /// content-missing (checked multipart-first, then object).
    pub dead_record_reject: bool,
    pub mode: Mode,
    pub hint_drop: bool,
    pub m: Mutants,
}

impl Cfg {
    pub fn att_cap(&self, s: usize) -> usize {
        if self.slot_honest(s) { self.max_att } else { self.poison_att.min(self.max_att) }
    }
    pub fn kslots(&self) -> usize {
        self.devs.iter().map(|d| d.items.len()).max().unwrap_or(0)
    }
    pub fn slot_dev(&self, s: usize) -> usize {
        s / self.kslots()
    }
    pub fn slot_exists(&self, s: usize) -> bool {
        let k = self.kslots();
        let dev = s / k;
        dev < self.devs.len() && (s % k) < self.devs[dev].items.len()
    }
    pub fn slot_content(&self, s: usize) -> usize {
        let k = self.kslots();
        self.devs[s / k].items[s % k] as usize
    }
    pub fn slot_honest(&self, s: usize) -> bool {
        !self.devs[s / self.kslots()].poisoner
    }
    pub fn nslots(&self) -> usize {
        self.devs.len() * self.kslots()
    }
    pub fn rec(&self, s: usize, a: usize) -> usize {
        s * self.max_att + a
    }
    pub fn rec_slot(&self, r: usize) -> usize {
        r / self.max_att
    }
    pub fn rec_att(&self, r: usize) -> usize {
        r % self.max_att
    }
    pub fn nrec(&self) -> usize {
        self.nslots() * self.max_att
    }
}

// Client states
pub const C_HASHED: u8 = 0;
pub const C_PENDING: u8 = 1; // attempt journaled, check+begin requested
pub const C_PENDING_FORCE: u8 = 2; // valve fired: upload own copy regardless of lease
pub const C_UPLOADING: u8 = 3;
pub const C_STAGED: u8 = 5;
pub const C_AWAIT_CONTENT: u8 = 6; // record with own content object sent
pub const C_AWAIT_HIT: u8 = 7; // dedup-hit record (content_object = null) sent
pub const C_SAFE: u8 = 8;
pub const C_ABSENT: u8 = 255;

pub fn cname(c: u8) -> &'static str {
    match c {
        C_HASHED => "hashed",
        C_PENDING => "pending",
        C_PENDING_FORCE => "pending(valve)",
        C_UPLOADING => "uploading",
        C_STAGED => "staged",
        C_AWAIT_CONTENT => "awaiting(own content)",
        C_AWAIT_HIT => "awaiting(dedup hit)",
        C_SAFE => "SAFE",
        _ => "-",
    }
}

// Blob values
pub const B_NONE: u8 = 0;
pub const B_GOOD: u8 = 1;
pub const B_BAD: u8 = 2;

#[derive(Clone, PartialEq, Eq, Hash, Debug, PartialOrd, Ord)]
pub struct State {
    // --- devices ---
    pub cs: [u8; MAX_SLOTS],
    pub att: [u8; MAX_SLOTS], // attempts allocated; current attempt = att-1
    // --- Worker + D1 (cache; may be wiped) ---
    pub lease: [u8; MAX_CONTENTS], // 0 = none, else rec+1
    pub w_committed: u8,           // bitmask over dedup ids
    pub relay: u32,                // receipts relayed (by record)
    pub rejnote: u32,              // typed rejections relayed (by record)
    // --- R2 ---
    pub multipart: u32, // initiated multipart uploads (by record/upload id)
    pub staging: u32,   // completed staging objects
    pub meta: u32,      // record objects in meta/
    pub has_content: u32, // ghost/static: record r carries a content_object
    // --- queue (QueueOnly mode) ---
    pub queue: u32,
    pub inbox: u32,
    // --- homelab (durable) ---
    pub blob: [u8; MAX_CONTENTS],
    pub receipts: u32,
    pub rejected: u32,
    pub published: u32,
    pub gc_log: u32,
    // --- bookkeeping / ghosts ---
    pub faults: u8,
    pub g_bad_delete: bool,
    pub g_resigned: bool,
}

#[derive(Clone, Copy, PartialEq, Eq, Hash, Debug)]
pub enum Act {
    // device
    Alloc(u8),
    CheckBegin { s: u8, lost: bool, lie: bool },
    Complete { s: u8, lost: bool, partial: bool },
    SendRecord { s: u8, lost: bool },
    Recheck(u8),
    Valve(u8),
    FetchReceipt(u8),
    SeeRejection(u8),
    DeviceReset(u8),
    // time / R2 / Worker
    LeaseExpire(u8),
    AbortAbandoned(u8),
    AbortLive(u8),
    D1Wipe,
    // queue
    Pull(u8),
    DropHint(u8),
    // homelab
    HVerify(u8),
    HReceipt(u8),
    HPublish(u8),
    HCleanup(u8),
    HOrphanGc(u8),
    HDangling(u8),
}

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Kind {
    Normal,
    /// Adversarial but not counted against the fault budget (lost responses,
    /// dropped hints). Excluded from the fault-free continuation.
    Adversarial,
    /// Counted fault. Excluded from the fault-free continuation.
    Fault,
}

impl Act {
    pub fn kind(&self) -> Kind {
        match self {
            // lost responses and a Worker crash mid-complete are counted faults
            Act::CheckBegin { lost, lie, .. } => {
                if *lie || *lost {
                    Kind::Fault
                } else {
                    Kind::Normal
                }
            }
            Act::Complete { lost, partial, .. } => {
                if *lost || *partial {
                    Kind::Fault
                } else {
                    Kind::Normal
                }
            }
            Act::SendRecord { lost, .. } => {
                if *lost {
                    Kind::Fault
                } else {
                    Kind::Normal
                }
            }
            Act::DeviceReset(_) | Act::AbortLive(_) | Act::D1Wipe => Kind::Fault,
            Act::DropHint(_) => Kind::Adversarial,
            _ => Kind::Normal,
        }
    }
}

#[inline]
fn bit(r: usize) -> u32 {
    1u32 << r
}
#[inline]
fn has(m: u32, r: usize) -> bool {
    m & bit(r) != 0
}

pub struct Proto {
    pub cfg: Cfg,
    pub sym: Vec<usize>,
    pub perms: Vec<Vec<usize>>,
}

impl Proto {
    pub fn new(cfg: Cfg) -> Self {
        assert!(cfg.nslots() <= MAX_SLOTS);
        assert!(cfg.ncontents <= MAX_CONTENTS);
        assert!(cfg.nrec() <= 32);
        // devices 0..g that are honest with identical items are symmetric
        let mut sym = vec![];
        if cfg.symmetry {
            for d in 0..cfg.devs.len() {
                if !cfg.devs[d].poisoner && cfg.devs[d].items == cfg.devs[0].items && sym.len() == d {
                    sym.push(d);
                }
            }
        }
        let mut perms = vec![];
        if sym.len() >= 2 {
            fn permgen(k: usize, cur: &mut Vec<usize>, used: &mut Vec<bool>, out: &mut Vec<Vec<usize>>) {
                if cur.len() == k {
                    out.push(cur.clone());
                    return;
                }
                for i in 0..k {
                    if !used[i] {
                        used[i] = true;
                        cur.push(i);
                        permgen(k, cur, used, out);
                        cur.pop();
                        used[i] = false;
                    }
                }
            }
            permgen(sym.len(), &mut vec![], &mut vec![false; sym.len()], &mut perms);
        } else {
            sym.clear();
        }
        Proto { cfg, sym, perms }
    }

    pub fn init(&self) -> State {
        let mut cs = [C_ABSENT; MAX_SLOTS];
        for s in 0..self.cfg.nslots() {
            if self.cfg.slot_exists(s) {
                cs[s] = C_HASHED;
            }
        }
        State {
            cs,
            att: [0; MAX_SLOTS],
            lease: [0; MAX_CONTENTS],
            w_committed: 0,
            relay: 0,
            rejnote: 0,
            multipart: 0,
            staging: 0,
            meta: 0,
            has_content: 0,
            queue: 0,
            inbox: 0,
            blob: [B_NONE; MAX_CONTENTS],
            receipts: 0,
            rejected: 0,
            published: 0,
            gc_log: 0,
            faults: 0,
            g_bad_delete: false,
            g_resigned: false,
        }
    }

    fn cur(&self, st: &State, s: usize) -> usize {
        self.cfg.rec(s, st.att[s] as usize - 1)
    }

    /// Records of slot s that the device has sent or allocated (attempt < att).
    fn slot_recs(&self, st: &State, s: usize) -> impl Iterator<Item = usize> + '_ {
        let base = self.cfg.rec(s, 0);
        (0..st.att[s] as usize).map(move |a| base + a)
    }

    /// Worker's dedup answer for content d asked by slot s.
    /// Returns: 0 = MISSING/GO, 1 = IN_FLIGHT (lease held by another slot),
    /// 2 = COMMITTED with a verifiable receipt relayed for d.
    fn answer(&self, st: &State, s: usize, d: usize) -> u8 {
        let committed_with_receipt = (st.w_committed >> d) & 1 == 1
            && (0..self.cfg.nrec()).any(|r| {
                has(st.relay, r)
                    && self.cfg.slot_exists(self.cfg.rec_slot(r))
                    && self.cfg.slot_content(self.cfg.rec_slot(r)) == d
            });
        if committed_with_receipt {
            return 2;
        }
        if self.cfg.m.trust_worker_commit && (st.w_committed >> d) & 1 == 1 {
            return 2;
        }
        let l = st.lease[d];
        if l != 0 && self.cfg.rec_slot((l - 1) as usize) != s {
            return 1;
        }
        0
    }

    fn put_meta(&self, st: &mut State, r: usize, content: bool) {
        st.meta |= bit(r);
        if content {
            st.has_content |= bit(r);
        }
        if self.cfg.mode == Mode::QueueOnly {
            st.queue |= bit(r); // R2 event notification -> queue hint
        }
    }

    fn can_fault(&self, st: &State) -> bool {
        st.faults < self.cfg.max_faults
    }

    fn ingest_visible(&self, st: &State, r: usize) -> bool {
        has(st.meta, r)
            && match self.cfg.mode {
                Mode::Reconcile => true,
                Mode::QueueOnly => has(st.inbox, r),
            }
    }

    pub fn actions(&self, st: &State, out: &mut Vec<Act>) {
        let c = &self.cfg;
        let lost_opts: &[bool] = if c.lost_responses && self.can_fault(st) { &[false, true] } else { &[false] };
        for s in 0..c.nslots() {
            let cs = st.cs[s];
            if cs == C_ABSENT {
                continue;
            }
            let s8 = s as u8;
            match cs {
                C_HASHED => {
                    if (st.att[s] as usize) < c.att_cap(s) {
                        out.push(Act::Alloc(s8));
                    }
                }
                C_PENDING | C_PENDING_FORCE => {
                    for &lost in lost_opts {
                        out.push(Act::CheckBegin { s: s8, lost, lie: false });
                    }
                    if c.f_worker_lie && cs == C_PENDING && self.can_fault(st) {
                        out.push(Act::CheckBegin { s: s8, lost: false, lie: true });
                    }
                }
                C_UPLOADING => {
                    for &lost in lost_opts {
                        out.push(Act::Complete { s: s8, lost, partial: false });
                    }
                    if c.record_first && c.lost_responses && self.can_fault(st) {
                        out.push(Act::Complete { s: s8, lost: true, partial: true });
                    }
                }
                C_STAGED => {
                    for &lost in lost_opts {
                        out.push(Act::SendRecord { s: s8, lost });
                    }
                }
                C_AWAIT_HIT => {
                    if !c.m.no_valve {
                        out.push(Act::Recheck(s8));
                    }
                }
                _ => {}
            }
            if (cs == C_AWAIT_HIT || cs == C_AWAIT_CONTENT)
                && !c.m.no_valve
                && (st.att[s] as usize) < c.att_cap(s)
            {
                out.push(Act::Valve(s8));
            }
            if cs != C_SAFE && self.slot_recs(st, s).any(|r| has(st.relay, r)) {
                out.push(Act::FetchReceipt(s8));
            }
            if (cs == C_AWAIT_HIT || cs == C_AWAIT_CONTENT) && has(st.rejnote, self.cur(st, s)) {
                out.push(Act::SeeRejection(s8));
            }
            if c.f_device_reset && cs != C_SAFE && cs != C_HASHED && self.can_fault(st) {
                out.push(Act::DeviceReset(s8));
            }
        }
        for d in 0..c.ncontents {
            if st.lease[d] != 0 {
                out.push(Act::LeaseExpire(d as u8));
            }
        }
        for r in 0..c.nrec() {
            if !c.slot_exists(c.rec_slot(r)) {
                continue;
            }
            let r8 = r as u8;
            if has(st.multipart, r) {
                let s = c.rec_slot(r);
                let live = st.cs[s] == C_UPLOADING && self.cur(st, s) == r;
                if !live {
                    out.push(Act::AbortAbandoned(r8));
                } else if c.f_abort_live && self.can_fault(st) {
                    out.push(Act::AbortLive(r8));
                }
            }
            if c.mode == Mode::QueueOnly && has(st.queue, r) {
                out.push(Act::Pull(r8));
                if c.hint_drop {
                    out.push(Act::DropHint(r8));
                }
            }
            // homelab
            let d = c.slot_content(c.rec_slot(r));
            if self.ingest_visible(st, r) && !has(st.rejected, r) {
                if has(st.has_content, r) && has(st.staging, r) && st.blob[d] == B_NONE {
                    out.push(Act::HVerify(r8));
                }
                if st.blob[d] != B_NONE && (!has(st.receipts, r) || c.m.resign) {
                    out.push(Act::HReceipt(r8));
                }
                if c.gc_typed_reject
                    && has(st.has_content, r)
                    && !has(st.staging, r)
                    && has(st.gc_log, r)
                    && st.blob[d] == B_NONE
                {
                    out.push(Act::HDangling(r8));
                }
            }
            if c.dead_record_reject
                && self.ingest_visible(st, r)
                && !has(st.rejected, r)
                && has(st.has_content, r)
                && !has(st.multipart, r)
                && !has(st.staging, r)
                && st.blob[d] == B_NONE
            {
                out.push(Act::HDangling(r8));
            }
            if has(st.receipts, r)
                && !has(st.relay, r)
                && !(c.m.publish_once && has(st.published, r))
            {
                out.push(Act::HPublish(r8));
            }
            if has(st.meta, r) {
                let done = (has(st.receipts, r) && has(st.published, r)) || has(st.rejected, r);
                let early = c.m.early_delete && has(st.staging, r);
                if done || early {
                    out.push(Act::HCleanup(r8));
                }
            }
            if c.orphan_gc && has(st.staging, r) && !has(st.meta, r) {
                out.push(Act::HOrphanGc(r8));
            }
        }
        if c.f_d1_wipe && self.can_fault(st) {
            out.push(Act::D1Wipe);
        }
    }

    pub fn next(&self, st: &State, a: Act) -> Option<State> {
        let c = &self.cfg;
        let mut n = st.clone();
        if a.kind() == Kind::Fault {
            n.faults += 1;
        }
        match a {
            Act::Alloc(s) => {
                let s = s as usize;
                n.att[s] += 1;
                n.cs[s] = C_PENDING;
            }
            Act::CheckBegin { s, lost, lie } => {
                let s = s as usize;
                let d = c.slot_content(s);
                let r = self.cur(st, s);
                let force = st.cs[s] == C_PENDING_FORCE;
                let ans = if lie {
                    1
                } else if force {
                    0
                } else {
                    self.answer(st, s, d)
                };
                if ans == 0 {
                    // Worker: begin (idempotent on (device, record)); advisory lease
                    if n.lease[d] == 0 {
                        n.lease[d] = (r + 1) as u8;
                    }
                    n.multipart |= bit(r);
                    if !lost {
                        n.cs[s] = C_UPLOADING;
                    }
                } else {
                    // IN_FLIGHT or COMMITTED: device sends its own dedup-hit record
                    self.put_meta(&mut n, r, false);
                    if !lost {
                        n.cs[s] = if c.m.hit_is_safe { C_SAFE } else { C_AWAIT_HIT };
                    }
                }
            }
            Act::Complete { s, lost, partial } => {
                let s = s as usize;
                let r = self.cur(st, s);
                let alive = has(st.staging, r) || has(st.multipart, r);
                if c.record_first && alive {
                    // Worker writes the signed record (create-only) before completing
                    self.put_meta(&mut n, r, true);
                }
                if partial {
                    // Worker crashed between the record write and Complete
                    return if n == *st { None } else { Some(n) };
                }
                let ok = if has(st.staging, r) {
                    true
                } else if has(st.multipart, r) {
                    n.staging |= bit(r);
                    n.multipart &= !bit(r);
                    true
                } else {
                    false // NoSuchUpload (aborted): restart with a new attempt
                };
                if !lost {
                    n.cs[s] = if !ok {
                        C_HASHED
                    } else if c.record_first {
                        C_AWAIT_CONTENT
                    } else {
                        C_STAGED
                    };
                }
            }
            Act::SendRecord { s, lost } => {
                let s = s as usize;
                let r = self.cur(st, s);
                self.put_meta(&mut n, r, true);
                if !lost {
                    n.cs[s] = C_AWAIT_CONTENT;
                }
            }
            Act::Recheck(s) => {
                let s = s as usize;
                let d = c.slot_content(s);
                if self.answer(st, s, d) == 0 && (st.att[s] as usize) < c.att_cap(s) {
                    n.cs[s] = C_HASHED;
                } else {
                    return None; // no change
                }
            }
            Act::Valve(s) => {
                let s = s as usize;
                n.att[s] += 1;
                n.cs[s] = C_PENDING_FORCE;
            }
            Act::FetchReceipt(s) => {
                n.cs[s as usize] = C_SAFE;
            }
            Act::SeeRejection(s) => {
                n.cs[s as usize] = C_HASHED;
            }
            Act::DeviceReset(s) => {
                n.cs[s as usize] = C_HASHED;
            }
            Act::LeaseExpire(d) => {
                n.lease[d as usize] = 0;
            }
            Act::AbortAbandoned(r) | Act::AbortLive(r) => {
                n.multipart &= !bit(r as usize);
            }
            Act::D1Wipe => {
                n.lease = [0; MAX_CONTENTS];
                n.w_committed = 0;
                n.relay = 0;
                n.rejnote = 0;
            }
            Act::Pull(r) => {
                n.queue &= !bit(r as usize);
                n.inbox |= bit(r as usize); // ack after durable inbox write
            }
            Act::DropHint(r) => {
                n.queue &= !bit(r as usize);
            }
            Act::HVerify(r) => {
                let r = r as usize;
                let s = c.rec_slot(r);
                let d = c.slot_content(s);
                let good = c.slot_honest(s);
                if good || c.m.no_verify {
                    n.blob[d] = if good { B_GOOD } else { B_BAD }; // put_blob: fsync before return
                } else {
                    // SR-11: keep nothing, reset lease, flag device, typed rejection
                    n.rejected |= bit(r);
                    n.rejnote |= bit(r);
                    if n.lease[d] as usize == r + 1 {
                        n.lease[d] = 0;
                    }
                }
            }
            Act::HReceipt(r) => {
                let r = r as usize;
                if has(st.receipts, r) {
                    n.g_resigned = true; // M7 only
                }
                n.receipts |= bit(r);
            }
            Act::HPublish(r) => {
                let r = r as usize;
                let d = c.slot_content(c.rec_slot(r));
                n.relay |= bit(r);
                n.w_committed |= 1 << d;
                n.published |= bit(r);
            }
            Act::HCleanup(r) => {
                let r = r as usize;
                let s = c.rec_slot(r);
                let d = c.slot_content(s);
                n.meta &= !bit(r);
                n.inbox &= !bit(r);
                if has(st.staging, r) {
                    if c.slot_honest(s) && st.blob[d] != B_GOOD {
                        n.g_bad_delete = true;
                    }
                    n.staging &= !bit(r);
                }
            }
            Act::HOrphanGc(r) => {
                let r = r as usize;
                n.staging &= !bit(r);
                n.gc_log |= bit(r);
            }
            Act::HDangling(r) => {
                let r = r as usize;
                n.rejected |= bit(r);
                n.rejnote |= bit(r); // typed: content-missing, please re-upload
            }
        }
        if n == *st {
            None
        } else {
            Some(n)
        }
    }

    /// Symmetry reduction: honest devices with identical item lists are
    /// interchangeable. Returns the lexicographically smallest permutation.
    pub fn canon(&self, st: State) -> State {
        let c = &self.cfg;
        let groups = &self.sym;
        if groups.is_empty() {
            return st;
        }
        let mut best = st.clone();
        for perm in self.perms.iter() {
            let t = self.permute(&st, perm);
            if t < best {
                best = t;
            }
        }
        let _ = c;
        best
    }

    fn permute(&self, st: &State, perm: &[usize]) -> State {
        // perm[old_dev] = new_dev
        let c = &self.cfg;
        let k = c.kslots();
        let ra = k * c.max_att; // record bits per device
        let mut n = st.clone();
        for (od, &nd) in perm.iter().enumerate() {
            for i in 0..k {
                n.cs[nd * k + i] = st.cs[od * k + i];
                n.att[nd * k + i] = st.att[od * k + i];
            }
        }
        let mapb = |m: u32| -> u32 {
            let mask: u64 = (1u64 << ra) - 1;
            let m = m as u64;
            let mut out = 0u64;
            for (od, &nd) in perm.iter().enumerate() {
                let blk = (m >> (od * ra)) & mask;
                out |= blk << (nd * ra);
            }
            // devices not in perm keep their bits
            let covered: u64 = (0..perm.len()).fold(0, |acc, d| acc | (mask << (d * ra)));
            let out = out | (m & !covered);
            out as u32
        };
        n.relay = mapb(st.relay);
        n.rejnote = mapb(st.rejnote);
        n.multipart = mapb(st.multipart);
        n.staging = mapb(st.staging);
        n.meta = mapb(st.meta);
        n.has_content = mapb(st.has_content);
        n.queue = mapb(st.queue);
        n.inbox = mapb(st.inbox);
        n.receipts = mapb(st.receipts);
        n.rejected = mapb(st.rejected);
        n.published = mapb(st.published);
        n.gc_log = mapb(st.gc_log);
        for d in 0..c.ncontents {
            let l = st.lease[d] as usize;
            if l != 0 {
                let r = l - 1;
                let od = r / ra;
                if od < perm.len() {
                    n.lease[d] = (perm[od] * ra + r % ra + 1) as u8;
                }
            }
        }
        n
    }

    /// Projection of a state onto one dedup id d (used for the item-
    /// independence check that justifies composing per-item results).
    pub fn project(&self, st: &State, d: usize) -> Vec<u64> {
        let c = &self.cfg;
        let mut v = vec![st.lease[d] as u64, ((st.w_committed >> d) & 1) as u64, st.blob[d] as u64];
        let mut mask: u32 = 0;
        for s in 0..c.nslots() {
            if c.slot_exists(s) && c.slot_content(s) == d {
                v.push(st.cs[s] as u64);
                v.push(st.att[s] as u64);
                for a in 0..c.max_att {
                    mask |= 1 << c.rec(s, a);
                }
            }
        }
        for m in [st.relay, st.rejnote, st.multipart, st.staging, st.meta, st.has_content, st.queue, st.inbox,
                  st.receipts, st.rejected, st.published, st.gc_log] {
            v.push((m & mask) as u64);
        }
        v
    }

    // ---------------- properties ----------------

    /// I1 (as worded by PLAN/analyst): no staged object is deleted by the
    /// ingest path before its content is durably committed.
    pub fn i1(&self, st: &State) -> bool {
        !st.g_bad_delete
    }

    /// I1-strong: no record awaiting commit points at a staging object that
    /// the homelab deleted while that content was not yet committed.
    pub fn i1_strong(&self, st: &State) -> bool {
        let c = &self.cfg;
        for r in 0..c.nrec() {
            let s = c.rec_slot(r);
            if !c.slot_exists(s) {
                continue;
            }
            if has(st.meta, r)
                && has(st.has_content, r)
                && !has(st.staging, r)
                && has(st.gc_log, r)
                && c.slot_honest(s)
                && st.blob[c.slot_content(s)] == B_NONE
            {
                return false;
            }
        }
        true
    }

    /// I2: device-visible SAFE => a homelab-signed receipt exists for one of
    /// the slot's own records, the record is archived and the blob is durable
    /// and good.
    pub fn i2(&self, st: &State) -> bool {
        let c = &self.cfg;
        for s in 0..c.nslots() {
            if st.cs[s] == C_SAFE && c.slot_honest(s) {
                let d = c.slot_content(s);
                let ok = self
                    .slot_recs(st, s)
                    .any(|r| has(st.receipts, r))
                    && st.blob[d] == B_GOOD;
                if !ok {
                    return false;
                }
            }
        }
        true
    }

    /// I3: dedup never merges different plaintexts (every committed blob's
    /// plaintext matches its dedup id).
    pub fn i3(&self, st: &State) -> bool {
        st.blob.iter().all(|&b| b != B_BAD)
    }

    /// I4: at most one receipt per record (receipt signing is idempotent).
    pub fn i4(&self, st: &State) -> bool {
        !st.g_resigned
    }

    /// I6: relay never holds a receipt the homelab did not sign (Worker
    /// cannot forge; structural sanity check of the model).
    pub fn i6(&self, st: &State) -> bool {
        st.relay & !st.receipts == 0
    }

    /// Goal: every honest slot SAFE, R2 staging, meta and multipart are
    /// empty (no orphans after reconciliation), and every receipt the homelab
    /// signed is in the Worker relay (receipts survive D1 loss).
    pub fn goal(&self, st: &State) -> bool {
        let c = &self.cfg;
        (0..c.nslots())
            .filter(|&s| c.slot_exists(s) && c.slot_honest(s))
            .all(|s| st.cs[s] == C_SAFE)
            && st.staging == 0
            && st.meta == 0
            && st.multipart == 0
            && st.receipts & !st.relay == 0 // every signed receipt is fetchable
    }

    pub fn fmt_act(&self, a: Act) -> String {
        let c = &self.cfg;
        let rs = |r: u8| {
            let r = r as usize;
            let s = c.rec_slot(r);
            format!(
                "rec(d{} item{} att{} content={})",
                c.slot_dev(s),
                s % c.kslots(),
                c.rec_att(r),
                (b'A' + c.slot_content(s) as u8) as char
            )
        };
        let ss = |s: u8| {
            let s = s as usize;
            format!(
                "dev{}/item{}({})",
                c.slot_dev(s),
                s % c.kslots(),
                (b'A' + c.slot_content(s) as u8) as char
            )
        };
        match a {
            Act::Alloc(s) => format!("{} journal new attempt", ss(s)),
            Act::CheckBegin { s, lost, lie } => format!(
                "{} check+begin{}{}",
                ss(s),
                if lost { " [response lost]" } else { "" },
                if lie { " [FAULT: Worker lies IN_FLIGHT]" } else { "" }
            ),
            Act::Complete { s, lost, partial } => format!(
                "{} upload parts + complete{}",
                ss(s),
                if partial { " [Worker crash after record write]" } else if lost { " [response lost]" } else { "" }
            ),
            Act::SendRecord { s, lost } => {
                format!("{} send record{}", ss(s), if lost { " [response lost]" } else { "" })
            }
            Act::Recheck(s) => format!("{} re-check", ss(s)),
            Act::Valve(s) => format!("{} safety valve: upload own copy", ss(s)),
            Act::FetchReceipt(s) => format!("{} fetch+verify receipt -> SAFE", ss(s)),
            Act::SeeRejection(s) => format!("{} sees typed rejection -> restart", ss(s)),
            Act::DeviceReset(s) => format!("{} [FAULT: device loses in-flight state]", ss(s)),
            Act::LeaseExpire(d) => format!("lease on {} expires", (b'A' + d) as char),
            Act::AbortAbandoned(r) => format!("R2 lifecycle aborts abandoned multipart {}", rs(r)),
            Act::AbortLive(r) => format!("[FAULT: R2 7-day abort of live multipart {}]", rs(r)),
            Act::D1Wipe => "[FAULT: D1 rolled back/wiped]".into(),
            Act::Pull(r) => format!("homelab pulls+acks hint {}", rs(r)),
            Act::DropHint(r) => format!("[queue drops hint {}]", rs(r)),
            Act::HVerify(r) => format!("homelab verify+put_blob {}", rs(r)),
            Act::HReceipt(r) => format!("homelab archive record + sign receipt {}", rs(r)),
            Act::HPublish(r) => format!("homelab publish receipt+commit mark {}", rs(r)),
            Act::HCleanup(r) => format!("homelab delete staging+meta {}", rs(r)),
            Act::HOrphanGc(r) => format!("homelab orphan-GC staging object of {}", rs(r)),
            Act::HDangling(r) => format!("homelab typed reject content-missing {}", rs(r)),
        }
    }

    pub fn fmt_state(&self, st: &State) -> String {
        let c = &self.cfg;
        let mut out = String::new();
        let devs: Vec<String> = (0..c.nslots())
            .filter(|&s| c.slot_exists(s))
            .map(|s| {
                format!(
                    "d{}i{}({}{})={}#{}",
                    c.slot_dev(s),
                    s % c.kslots(),
                    (b'A' + c.slot_content(s) as u8) as char,
                    if c.slot_honest(s) { "" } else { ",POISON" },
                    cname(st.cs[s]),
                    st.att[s]
                )
            })
            .collect();
        out += &format!("  devices: {}\n", devs.join(" "));
        let bl: Vec<String> = (0..c.ncontents)
            .map(|d| {
                format!(
                    "{}:{}",
                    (b'A' + d as u8) as char,
                    ["-", "good", "BAD"][st.blob[d] as usize]
                )
            })
            .collect();
        out += &format!(
            "  homelab: blobs[{}] receipts={:#x} rejected={:#x} gc_log={:#x}\n",
            bl.join(" "),
            st.receipts,
            st.rejected,
            st.gc_log
        );
        out += &format!(
            "  r2: meta={:#x} staging={:#x} multipart={:#x}; worker: relay={:#x} leases={:?} faults={}\n",
            st.meta, st.staging, st.multipart, st.relay, &st.lease[..c.ncontents], st.faults
        );
        out
    }
}

impl fmt::Display for Act {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{:?}", self)
    }
}
