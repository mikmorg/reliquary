mod model;

use model::*;
use std::collections::HashMap;
use std::time::Instant;

// ---------------- Stateright adapter (cross-check of the safety results) ----

struct SrModel {
    p: Proto,
}

impl stateright::Model for SrModel {
    type State = State;
    type Action = Act;
    fn init_states(&self) -> Vec<State> {
        vec![self.p.init()]
    }
    fn actions(&self, st: &State, out: &mut Vec<Act>) {
        self.p.actions(st, out)
    }
    fn next_state(&self, st: &State, a: Act) -> Option<State> {
        self.p.next(st, a)
    }
    fn properties(&self) -> Vec<stateright::Property<Self>> {
        use stateright::Property;
        vec![
            Property::always("I1 no staged delete before durable commit", |m: &SrModel, s| m.p.i1(s)),
            Property::always("I1-strong no dangling content reference", |m: &SrModel, s| m.p.i1_strong(s)),
            Property::always("I2 safe only with receipt", |m: &SrModel, s| m.p.i2(s)),
            Property::always("I3 no false dedup merge", |m: &SrModel, s| m.p.i3(s)),
            Property::always("I4 one receipt per record", |m: &SrModel, s| m.p.i4(s)),
            Property::always("I6 relay subset of signed", |m: &SrModel, s| m.p.i6(s)),
            Property::sometimes("goal reachable", |m: &SrModel, s| m.p.goal(s)),
        ]
    }
}

fn stateright_check(cfg: &Cfg) -> (usize, Vec<String>, f64) {
    use stateright::{Checker, Model};
    let t = Instant::now();
    let m = SrModel { p: Proto::new(cfg.clone()) };
    let checker = m.checker().threads(4).spawn_bfs().join();
    let mut found = vec![];
    for (name, _path) in checker.discoveries() {
        found.push(name.to_string());
    }
    found.sort();
    (checker.unique_state_count(), found, t.elapsed().as_secs_f64())
}

// ---------------- random simulation (not exhaustive) -----------------------

struct Rng(u64);
impl Rng {
    fn next(&mut self) -> u64 {
        // xorshift64*
        self.0 ^= self.0 >> 12;
        self.0 ^= self.0 << 25;
        self.0 ^= self.0 >> 27;
        self.0.wrapping_mul(0x2545F4914F6CDD1D)
    }
    fn below(&mut self, n: usize) -> usize {
        (self.next() % n as u64) as usize
    }
}

/// Random walks with faults, then a random fault-free continuation that must
/// reach the goal within `cont_steps`. Checks the safety properties on every
/// visited state.
fn simulate(cfg: Cfg, runs: usize, walk: usize, cont_steps: usize, seed: u64) {
    let p = Proto::new(cfg.clone());
    let props: Vec<(&str, fn(&Proto, &State) -> bool)> = vec![
        ("I1", Proto::i1),
        ("I1-strong", Proto::i1_strong),
        ("I2", Proto::i2),
        ("I3", Proto::i3),
        ("I4", Proto::i4),
        ("I6", Proto::i6),
    ];
    let t = Instant::now();
    let mut rng = Rng(seed | 1);
    let mut viol: HashMap<&str, usize> = HashMap::new();
    let (mut reached, mut not_reached, mut exhausted_nr) = (0usize, 0usize, 0usize);
    let mut faults_hist = vec![0usize; cfg.max_faults as usize + 1];
    let mut steps_total = 0usize;
    let mut acts = vec![];
    for _ in 0..runs {
        let mut st = p.init();
        let mut run_viol: Vec<&str> = vec![];
        for phase in 0..2 {
            let limit = if phase == 0 { walk } else { cont_steps };
            for _ in 0..limit {
                acts.clear();
                p.actions(&st, &mut acts);
                if phase == 1 {
                    acts.retain(|a| a.kind() == Kind::Normal);
                    if p.goal(&st) {
                        break;
                    }
                }
                if acts.is_empty() {
                    break;
                }
                // try a few times to find an action that changes state
                let mut moved = false;
                for _ in 0..8 {
                    let a = acts[rng.below(acts.len())];
                    if let Some(n) = p.next(&st, a) {
                        st = n;
                        moved = true;
                        break;
                    }
                }
                steps_total += 1;
                if !moved {
                    continue;
                }
                for (name, f) in props.iter() {
                    if !f(&p, &st) && !run_viol.contains(name) {
                        run_viol.push(name);
                        *viol.entry(name).or_default() += 1;
                    }
                }
            }
            if phase == 0 {
                faults_hist[st.faults as usize] += 1;
            }
        }
        if p.goal(&st) {
            reached += 1;
        } else {
            let ex = (0..cfg.nslots()).any(|s| {
                cfg.slot_exists(s) && cfg.slot_honest(s) && st.cs[s] != C_SAFE && st.att[s] as usize >= cfg.att_cap(s)
            });
            if ex {
                exhausted_nr += 1;
            } else {
                not_reached += 1;
                if not_reached <= 1 {
                    eprintln!("example run that did not reach the goal:");
                    eprint!("{}", p.fmt_state(&st));
                }
            }
        }
    }
    println!("=== SIMULATION (random, NOT exhaustive) {} ===", cfg.name);
    println!(
        "runs={} walk_steps<={} continuation_steps<={} seed={} total_steps={} time={:.1}s",
        runs, walk, cont_steps, seed, steps_total, t.elapsed().as_secs_f64()
    );
    println!("faults used per run (0..={}): {:?}", cfg.max_faults, faults_hist);
    if viol.is_empty() {
        println!("safety: no violation of I1, I1-strong, I2, I3, I4, I6 in any visited state");
    } else {
        println!("safety violations (runs with at least one violating state): {:?}", viol);
    }
    println!(
        "goal reached by random fault-free continuation: {} / {}; not reached: {} (+{} attempt-exhausted)",
        reached, runs, not_reached, exhausted_nr
    );
    println!();
}

// ---------------- own explicit-state checker -------------------------------

struct Graph {
    states: Vec<State>,
    parent: Vec<(u32, Option<Act>)>,
    depth: Vec<u16>,
    // forward CSR over Normal actions only (states are numbered in BFS order)
    offs: Vec<u32>,
    succ: Vec<u32>,
    edges: usize,
}

#[derive(Default)]
struct IdHasher(u64);
impl std::hash::Hasher for IdHasher {
    fn finish(&self) -> u64 {
        self.0
    }
    fn write(&mut self, _: &[u8]) {
        unreachable!()
    }
    fn write_u64(&mut self, v: u64) {
        self.0 = v;
    }
}
type FpMap = HashMap<u64, u32, std::hash::BuildHasherDefault<IdHasher>>;

fn fp(st: &State) -> u64 {
    use std::hash::{Hash, Hasher};
    let mut h = std::collections::hash_map::DefaultHasher::new();
    st.hash(&mut h);
    h.finish()
}

fn explore(p: &Proto) -> Graph {
    // States are deduplicated by a 64-bit SipHash fingerprint (as Stateright
    // does); the collision probability is reported with the result.
    let mut index: FpMap = FpMap::default();
    let mut states: Vec<State> = vec![];
    let mut parent = vec![];
    let mut depth = vec![];
    let mut offs: Vec<u32> = vec![0];
    let mut succ: Vec<u32> = vec![];
    let init = p.canon(p.init());
    index.insert(fp(&init), 0);
    states.push(init);
    parent.push((0, None));
    depth.push(0u16);
    let mut acts = vec![];
    let mut edges = 0usize;
    let cap: usize = std::env::var("CAP").ok().and_then(|v| v.parse().ok()).unwrap_or(50_000_000);
    let mut i = 0usize;
    while i < states.len() {
        if i % 5_000_000 == 0 && i > 0 && std::env::var("PROGRESS").is_ok() {
            eprintln!("progress: expanded {} of {} states, depth {}, normal edges {}", i, states.len(), depth[i], succ.len());
        }
        if states.len() > cap {
            eprintln!("CAP of {} states exceeded at depth {}; aborting this run", cap, depth[i]);
            std::process::exit(3);
        }
        let st = states[i].clone();
        acts.clear();
        p.actions(&st, &mut acts);
        for &a in acts.iter() {
            if let Some(n) = p.next(&st, a).map(|n| p.canon(n)) {
                edges += 1;
                let f = fp(&n);
                let j = match index.get(&f) {
                    Some(&j) => j,
                    None => {
                        let j = states.len() as u32;
                        index.insert(f, j);
                        states.push(n);
                        parent.push((i as u32, Some(a)));
                        depth.push(depth[i] + 1);
                        j
                    }
                };
                if a.kind() == Kind::Normal {
                    succ.push(j);
                }
            }
        }
        offs.push(succ.len() as u32);
        i += 1;
    }
    Graph { states, parent, depth, offs, succ, edges }
}

fn trace(p: &Proto, g: &Graph, mut i: u32) -> String {
    let mut steps = vec![];
    while let (pi, Some(a)) = g.parent[i as usize] {
        steps.push((a, i));
        i = pi;
    }
    steps.reverse();
    let mut out = String::new();
    out += "  init\n";
    out += &p.fmt_state(&g.states[0]);
    for (k, (a, j)) in steps.iter().enumerate() {
        out += &format!("  {:>2}. {}\n", k + 1, p.fmt_act(*a));
        if k + 1 == steps.len() {
            out += &p.fmt_state(&g.states[*j as usize]);
        }
    }
    out
}

struct Outcome {
    name: String,
    states: usize,
    edges: usize,
    secs: f64,
    max_depth: u16,
    violations: Vec<(String, String)>, // (property, trace)
    goal_reachable: bool,
    stuck: usize,
    stuck_artifact: usize,
    collision_p: f64,
    stuck_trace: Option<String>,
    sr: Option<(usize, Vec<String>, f64)>,
}

fn check(cfg: Cfg, with_sr: bool) -> Outcome {
    let p = Proto::new(cfg.clone());
    let t = Instant::now();
    let g = explore(&p);
    let n = g.states.len();
    type PropFn = fn(&Proto, &State) -> bool;
    let props: Vec<(&str, PropFn)> = vec![
        ("I1 no staged delete before durable commit", Proto::i1),
        ("I1-strong no dangling content reference", Proto::i1_strong),
        ("I2 safe only with receipt", Proto::i2),
        ("I3 no false dedup merge", Proto::i3),
        ("I4 one receipt per record", Proto::i4),
        ("I6 relay subset of signed", Proto::i6),
    ];
    let mut violations = vec![];
    for (name, f) in props.iter() {
        // BFS order => first index found has minimal depth
        if let Some(i) = (0..n).find(|&i| !f(&p, &g.states[i])) {
            violations.push((name.to_string(), trace(&p, &g, i as u32)));
        }
    }
    // AG EF goal over the fault-free continuation (Normal actions only):
    // least fixpoint can = goal \/ EX_normal can, iterated over the CSR.
    let mut can: Vec<bool> = (0..n).map(|i| p.goal(&g.states[i])).collect();
    let goal_reachable = can.iter().any(|&b| b);
    loop {
        let mut changed = false;
        for i in (0..n).rev() {
            if !can[i] {
                let (a, b) = (g.offs[i] as usize, g.offs[i + 1] as usize);
                if g.succ[a..b].iter().any(|&j| can[j as usize]) {
                    can[i] = true;
                    changed = true;
                }
            }
        }
        if !changed {
            break;
        }
    }
    let stuck_idx: Vec<usize> = (0..n).filter(|&i| !can[i]).collect();
    // A stuck state is a bound artifact if some honest, non-SAFE slot has used
    // every attempt the bounded model allows.
    let exhausted = |st: &State| {
        (0..cfg.nslots()).any(|s| {
            cfg.slot_exists(s)
                && cfg.slot_honest(s)
                && st.cs[s] != C_SAFE
                && st.att[s] as usize >= cfg.max_att
        })
    };
    let genuine: Vec<usize> = stuck_idx.iter().copied().filter(|&i| !exhausted(&g.states[i])).collect();
    let artifact = stuck_idx.len() - genuine.len();
    let stuck_trace = genuine
        .first()
        .or(stuck_idx.first())
        .map(|&i| trace(&p, &g, i as u32));
    let max_depth = *g.depth.iter().max().unwrap_or(&0);
    let secs = t.elapsed().as_secs_f64();
    let sr = if with_sr { Some(stateright_check(&cfg)) } else { None };
    Outcome {
        name: cfg.name.clone(),
        states: n,
        edges: g.edges,
        secs,
        max_depth,
        violations,
        goal_reachable,
        stuck: genuine.len(),
        stuck_artifact: artifact,
        collision_p: (n as f64) * (n as f64) / 2f64.powi(65),
        stuck_trace,
        sr,
    }
}

fn print(o: &Outcome, verbose: bool) {
    println!("=== {} ===", o.name);
    println!(
        "states={} transitions={} max_depth={} time={:.1}s (64-bit fingerprint collision bound {:.1e})",
        o.states, o.edges, o.max_depth, o.secs, o.collision_p
    );
    if let Some((n, found, secs)) = &o.sr {
        println!(
            "stateright 0.31.0 BFS cross-check: unique_states={} ({}), discoveries={:?} time={:.1}s",
            n,
            if *n == o.states { "matches" } else { "DIFFERS" },
            found,
            secs
        );
    }
    if o.violations.is_empty() {
        println!("safety: I1, I1-strong, I2, I3, I4, I6 hold in all reachable states");
    }
    for (name, tr) in o.violations.iter() {
        println!("VIOLATION {}", name);
        if verbose {
            print!("{}", tr);
        }
    }
    println!("goal (all honest SAFE, R2 clean) reachable: {}", o.goal_reachable);
    if o.stuck_artifact > 0 {
        println!(
            "  note: {} stuck states only because a slot used all its bounded attempts (bound artifact; trace shown only if no genuine one)",
            o.stuck_artifact
        );
    }
    if o.stuck == 0 {
        println!("liveness (AG EF goal over fault-free continuation): holds (excluding bound artifacts)");
    } else {
        println!(
            "liveness VIOLATION: {} reachable states (not attempt-exhausted) cannot reach the goal without further faults",
            o.stuck
        );
        if verbose {
            print!("{}", o.stuck_trace.as_ref().unwrap());
        }
    }
    if o.stuck == 0 && o.stuck_artifact > 0 && verbose && std::env::var("SHOWART").is_ok() {
        print!("{}", o.stuck_trace.as_ref().unwrap());
    }
    println!();
}

fn base(name: &str, devs: Vec<DevCfg>, ncontents: usize, max_att: usize, max_faults: u8) -> Cfg {
    Cfg {
        name: name.into(),
        devs,
        ncontents,
        max_att,
        poison_att: max_att,
        max_faults,
        f_device_reset: true,
        f_abort_live: true,
        f_d1_wipe: true,
        f_worker_lie: true,
        lost_responses: true,
        orphan_gc: true,
        gc_typed_reject: true,
        symmetry: true,
        record_first: false,
        dead_record_reject: false,
        mode: Mode::Reconcile,
        hint_drop: true,
        m: Mutants::default(),
    }
}

fn honest(items: &[u8]) -> DevCfg {
    DevCfg { items: items.to_vec(), poisoner: false }
}
fn poison(items: &[u8]) -> DevCfg {
    DevCfg { items: items.to_vec(), poisoner: true }
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let which = args.get(1).map(|s| s.as_str()).unwrap_or("all");
    let verbose = !args.iter().any(|a| a == "-q");
    if std::env::var("PROGRESS").is_ok() {
        eprintln!("size_of State = {}", std::mem::size_of::<State>());
    }
    let with_sr = args.iter().any(|a| a == "--stateright");

    let mut runs: Vec<Cfg> = vec![];
    let v1 = |c: &mut Cfg| {
        c.orphan_gc = false;
        c.gc_typed_reject = false;
        c.record_first = true;
        c.dead_record_reject = true;
    };
    // E-core: 2 honest devices share item A, a poisoner (1 attempt) targets A
    let core = |name: &str| {
        let mut c = base(name, vec![honest(&[0]), honest(&[0]), poison(&[0])], 1, 2, 1);
        c.poison_att = 1;
        c
    };
    if which == "all" || which == "variants" {
        for (tag, devs) in [
            ("1 honest + poisoner", vec![honest(&[0]), poison(&[0])]),
            ("2 honest", vec![honest(&[0]), honest(&[0])]),
        ] {
            let mut c = base(&format!("E1 v0 = analyst F1-F8 as written (record after complete; homelab orphan GC), {}, att<=2, faults<=1", tag), devs.clone(), 1, 2, 1);
            c.gc_typed_reject = false;
            runs.push(c);
            let c = base(&format!("E2 v0 + typed content-missing reject for GC'd objects, {}, att<=2, faults<=1", tag), devs.clone(), 1, 2, 1);
            runs.push(c);
            let mut c = base(&format!("E3 v1 = record-first complete, no orphan GC, dead-record typed reject, {}, att<=2, faults<=1", tag), devs.clone(), 1, 2, 1);
            v1(&mut c);
            runs.push(c);
        }
        let mut c = core("E3b v1, 2 honest + poisoner (1 attempt), att<=2, faults<=1");
        v1(&mut c);
        runs.push(c);
    }
    if which == "all" || which.starts_with("v1") {
        let mut c = base("E4 v1, 3 honest devices x 1 shared item, att<=2, faults<=1", vec![honest(&[0]), honest(&[0]), honest(&[0])], 1, 2, 1);
        v1(&mut c);
        runs.push(c);
        let mut c = base("E5 v1, 2 honest devices x 1 shared item, att<=3, faults<=2 (no lost-response faults)", vec![honest(&[0]), honest(&[0])], 1, 3, 2);
        v1(&mut c);
        c.lost_responses = false;
        runs.push(c);
        let mut c = base("E6 v1, 1 honest + poisoner (1 attempt), att<=3, faults<=2", vec![honest(&[0]), poison(&[0])], 1, 3, 2);
        v1(&mut c);
        c.poison_att = 1;
        runs.push(c);
        let mut c = base("E7 v1, 1 honest device, att<=4, faults<=3", vec![honest(&[0])], 1, 4, 3);
        v1(&mut c);
        runs.push(c);
    }
    if which == "all" || which == "mutants" {
        let mk = |name: &str| {
            let mut c = base(name, vec![honest(&[0]), poison(&[0])], 1, 2, 1);
            v1(&mut c);
            c
        };
        let muts: Vec<(&str, fn(&mut Mutants))> = vec![
            ("M1 homelab skips SHA-256/HMAC verification", |m| m.no_verify = true),
            ("M2 staging deleted before durable commit", |m| m.early_delete = true),
            ("M3 dedup hit (IN_FLIGHT/COMMITTED) shown as safe", |m| m.hit_is_safe = true),
            ("M5 no re-check and no safety valve", |m| m.no_valve = true),
            ("M6 receipts published once, never republished", |m| m.publish_once = true),
            ("M7 receipt re-signed on redelivery", |m| m.resign = true),
        ];
        let mut c = mk("M0 control: v1, 1 honest + poisoner, att<=2, faults<=1");
        runs.push(c.clone());
        for (name, f) in muts {
            c = mk(&format!("mutant {}", name));
            f(&mut c.m);
            runs.push(c);
        }
        let mut c = mk("mutant M4 queue-only ingest (no reconciliation listing), hints droppable");
        c.mode = Mode::QueueOnly;
        runs.push(c);
        let mut c = mk("M4 control: queue-only ingest, hints never dropped");
        c.mode = Mode::QueueOnly;
        c.hint_drop = false;
        runs.push(c);
    }
    if which == "xcheck" {
        // Stateright cross-check (no symmetry reduction, so counts compare 1:1)
        let mut c = base("X1 v1, 1 honest + poisoner, att<=2, faults<=1 (no symmetry)", vec![honest(&[0]), poison(&[0])], 1, 2, 1);
        v1(&mut c);
        c.symmetry = false;
        runs.push(c);
        let mut c = base("X2 v0, 1 honest + poisoner, att<=2, faults<=1 (no symmetry)", vec![honest(&[0]), poison(&[0])], 1, 2, 1);
        c.gc_typed_reject = false;
        c.symmetry = false;
        runs.push(c);
        let mut c = base("X3 v1, 2 honest, att<=2, faults<=1 (no symmetry)", vec![honest(&[0]), honest(&[0])], 1, 2, 1);
        v1(&mut c);
        c.symmetry = false;
        runs.push(c);
    }
    if let Some(k) = which.strip_prefix("v1:") {
        let k: usize = k.parse().unwrap();
        runs = vec![runs[k].clone()];
    }
    if which == "indep" {
        // Item independence: every transition except a D1 wipe changes the
        // projection of at most one dedup id. Checked over every transition of
        // a multi-item model (no symmetry reduction).
        for (name, devs, lost) in [
            ("1 honest x {A,B}, lost-response faults on", vec![honest(&[0, 1])], true),
            ("1 honest x {A,B} + poisoner x {B}, lost-response faults off", vec![honest(&[0, 1]), poison(&[1])], false),
        ] {
            let mut c = base(name, devs, 2, 2, 1);
            v1(&mut c);
            c.lost_responses = lost;
            c.poison_att = 1;
            c.symmetry = false;
            let p = Proto::new(c.clone());
            let g = explore(&p);
            let mut acts = vec![];
            let (mut checked, mut bad, mut wipes) = (0usize, 0usize, 0usize);
            for st in g.states.iter() {
                acts.clear();
                p.actions(st, &mut acts);
                for &a in acts.iter() {
                    if let Some(n) = p.next(st, a) {
                        let changed = (0..c.ncontents).filter(|&d| p.project(st, d) != p.project(&n, d)).count();
                        if a == Act::D1Wipe {
                            wipes += 1;
                        } else if changed > 1 {
                            bad += 1;
                            if bad == 1 {
                                eprintln!("multi-item transition: {}", p.fmt_act(a));
                            }
                        }
                        checked += 1;
                    }
                }
            }
            println!("=== INDEPENDENCE {} (v1, att<=2, faults<=1) ===", name);
            println!("states={} transitions checked={} D1-wipe transitions={} transitions touching >1 dedup id={}", g.states.len(), checked, wipes, bad);
            println!();
        }
        return;
    }
    if which == "custom" {
        // custom <n_honest> <n_items_each> <att> <faults> <poisoner 0|1> <lost 0|1>
        let nh: usize = args[2].parse().unwrap();
        let ni: usize = args[3].parse().unwrap();
        let att: usize = args[4].parse().unwrap();
        let f: u8 = args[5].parse().unwrap();
        let pz = args[6] == "1";
        let lost = args[7] == "1";
        let items: Vec<u8> = (0..ni as u8).collect();
        let mut devs: Vec<DevCfg> = (0..nh).map(|_| honest(&items)).collect();
        if pz {
            devs.push(poison(&items));
        }
        let mut c = base(&format!("custom honest={} items={} att={} faults={} poisoner={} lost={}", nh, ni, att, f, pz, lost), devs, ni, att, f);
        c.lost_responses = lost;
        if args.iter().any(|a| a == "--nogcfix") { c.gc_typed_reject = false; }
        if args.iter().any(|a| a == "--nogc") { c.orphan_gc = false; c.gc_typed_reject = false; }
        if args.iter().any(|a| a == "--v1") { c.orphan_gc = false; c.gc_typed_reject = false; c.record_first = true; c.dead_record_reject = true; }
        if args.iter().any(|a| a == "--nosym") { c.symmetry = false; }
        if let Some(i) = args.iter().position(|a| a == "--patt") { c.poison_att = args[i + 1].parse().unwrap(); }
        if args.iter().any(|a| a == "--queue") { c.mode = Mode::QueueOnly; }
        if args.iter().any(|a| a == "--nodrop") { c.hint_drop = false; }
        for a in args.iter() {
            match a.as_str() {
                "--M1" => c.m.no_verify = true,
                "--M2" => c.m.early_delete = true,
                "--M3" => c.m.hit_is_safe = true,
                "--M5" => c.m.no_valve = true,
                "--M6" => c.m.publish_once = true,
                "--M7" => c.m.resign = true,
                "--M8" => c.m.trust_worker_commit = true,
                _ => {}
            }
        }
        runs.push(c);
    }
    if which == "sim" {
        // sim <n_honest> <n_items_each> <att> <faults> <poisoner 0|1> <runs> <walk> <seed> [--v1 ...]
        let nh: usize = args[2].parse().unwrap();
        let ni: usize = args[3].parse().unwrap();
        let att: usize = args[4].parse().unwrap();
        let f: u8 = args[5].parse().unwrap();
        let pz = args[6] == "1";
        let nruns: usize = args[7].parse().unwrap();
        let walk: usize = args[8].parse().unwrap();
        let seed: u64 = args[9].parse().unwrap();
        let items: Vec<u8> = (0..ni as u8).collect();
        let mut devs: Vec<DevCfg> = (0..nh).map(|_| honest(&items)).collect();
        if pz {
            devs.push(poison(&items));
        }
        let mut c = base(&format!("honest={} items={} att={} faults={} poisoner={}", nh, ni, att, f, pz), devs, ni, att, f);
        if args.iter().any(|a| a == "--v1") { c.orphan_gc = false; c.gc_typed_reject = false; c.record_first = true; c.dead_record_reject = true; c.name += " v1"; }
        if args.iter().any(|a| a == "--nogcfix") { c.gc_typed_reject = false; c.name += " v0"; }
        simulate(c, nruns, walk, 4000, seed);
        return;
    }
    for c in runs {
        let o = check(c, with_sr);
        print(&o, verbose);
    }
}
