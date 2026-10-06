//! THROWAWAY SPIKE CODE. Not production. See README.md.
//!
//! A2 spike (fork of CE spike 2): multi-stanza age headers with the hybrid PQ
//! recipient (mlkem768x25519), C2SP signed-note metadata records sealed at the
//! end of the upload, and a strict ingest with specific rejection codes.
//!
//! CLI that simulates the device (start/resume/complete/abort/dedup-hit,
//! check-receipt), R2 (a directory; every transmitted byte is logged per
//! attempt), and the homelab (ingest, chunk range reads).
//!
//! Exit codes: 0 ok, 2 usage/other error, 10 ingest rejected, 11 ingest
//! pending (content not yet committed), 12 receipt invalid, 65 source changed
//! (abort + restart), 66 source missing, 69 source unstable during pass 1,
//! 73 upload busy (another process holds the lock), 74 I/O error,
//! 75 simulated interruption, 76 state/journal corrupt (abort + restart).

mod engine;
mod format;
mod header;
mod meta;

use base64::{engine::general_purpose::STANDARD as B64P, Engine};
use engine::*;
use format::*;
use header::*;
use meta::*;
use rand::{rngs::OsRng, seq::SliceRandom, RngCore};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::collections::HashMap;
use std::fs::{self, File, OpenOptions};
use std::io::{self, Read, Seek, SeekFrom, Write};
use std::path::{Path, PathBuf};
use std::time::Instant;
use zeroize::Zeroize;

struct Args(HashMap<String, String>);
impl Args {
    fn parse() -> (String, Args) {
        let v: Vec<String> = std::env::args().skip(1).collect();
        let cmd = v.first().cloned().unwrap_or_default();
        let mut m = HashMap::new();
        let mut i = 1;
        while i < v.len() {
            let k = v[i].trim_start_matches("--").to_string();
            if i + 1 < v.len() && !v[i + 1].starts_with("--") {
                m.insert(k, v[i + 1].clone());
                i += 2;
            } else {
                m.insert(k, "1".into());
                i += 1;
            }
        }
        (cmd, Args(m))
    }
    fn s(&self, k: &str) -> String {
        self.0.get(k).cloned().unwrap_or_else(|| die(2, &format!("missing --{k}")))
    }
    fn o(&self, k: &str) -> Option<String> {
        self.0.get(k).cloned()
    }
    fn p(&self, k: &str) -> PathBuf {
        PathBuf::from(self.s(k))
    }
    fn n<T: std::str::FromStr>(&self, k: &str) -> Option<T> {
        self.o(k).map(|s| s.parse().unwrap_or_else(|_| die(2, &format!("bad --{k}"))))
    }
    fn flag(&self, k: &str) -> bool {
        self.0.contains_key(k)
    }
}

fn die(code: i32, msg: &str) -> ! {
    eprintln!("error: {msg}");
    std::process::exit(code)
}

fn io_code(e: &io::Error) -> i32 {
    if e.kind() == io::ErrorKind::NotFound {
        66
    } else {
        74
    }
}

fn now_secs() -> u64 {
    std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs()
}

fn rand_hex(n: usize) -> String {
    let mut b = vec![0u8; n];
    OsRng.fill_bytes(&mut b);
    hex::encode(b)
}

fn proc_stat(file: &str, key: &str) -> u64 {
    fs::read_to_string(file)
        .ok()
        .and_then(|s| s.lines().find(|l| l.starts_with(key)).map(|l| l[key.len()..].trim().trim_end_matches(" kB").trim().parse().unwrap_or(0)))
        .unwrap_or(0)
}

fn resource_json() -> Value {
    json!({"peak_rss_kb": proc_stat("/proc/self/status", "VmHWM:"), "io_write_bytes": proc_stat("/proc/self/io", "write_bytes:")})
}

// ------------------------------------------------------------ simulated R2

/// One transfer attempt of one part (or of a single-PUT object). Every byte
/// handed to `emit` is what the network (Cloudflare) would see; it is appended
/// to R2/<object_key>/attempts/<name>.<n>, which the tests use to prove that
/// no object offset is ever transmitted with two different values.
struct Emitter {
    f: File,
    path: PathBuf,
    final_path: PathBuf,
    h: Sha256,
}

impl Emitter {
    fn begin(r2: &Path, object_key: &str, name: &str) -> Emitter {
        let dir = r2.join(object_key).join("attempts");
        fs::create_dir_all(&dir).unwrap();
        let mut n = 1;
        let path = loop {
            let p = dir.join(format!("{name}.{n}"));
            if !p.exists() {
                break p;
            }
            n += 1;
        };
        let f = OpenOptions::new().write(true).create_new(true).open(&path).unwrap();
        Emitter { f, path, final_path: r2.join(object_key).join(name), h: Sha256::new() }
    }
    fn emit(&mut self, b: &[u8]) {
        // TEST-ONLY: A2_SLOW_US simulates network time (sleep per 16 KiB slice)
        // so that random SIGKILLs in A2-S2 land in the middle of parts.
        let slow: u64 = std::env::var("A2_SLOW_US").ok().and_then(|v| v.parse().ok()).unwrap_or(0);
        for piece in b.chunks(if slow > 0 { 16 * 1024 } else { b.len().max(1) }) {
            self.f.write_all(piece).unwrap();
            self.f.flush().unwrap();
            self.h.update(piece);
            if slow > 0 {
                std::thread::sleep(std::time::Duration::from_micros(slow));
            }
        }
    }
    /// Transfer finished: R2 stores the part and returns an ETag (simulated as
    /// hex SHA-256; stored verbatim, treated as opaque).
    fn finish(self) -> String {
        self.f.sync_all().unwrap();
        let _ = fs::remove_file(&self.final_path);
        fs::hard_link(&self.path, &self.final_path).unwrap();
        hex::encode(self.h.finalize())
    }
}

// ------------------------------------------------------------ device side

struct Dirs {
    state: PathBuf,
    ks: Keystore,
    r2: PathBuf,
}

impl Dirs {
    fn from(a: &Args) -> Dirs {
        let state = a.p("state-dir");
        fs::create_dir_all(state.join("pending")).unwrap();
        Dirs { state, ks: Keystore(a.p("keystore")), r2: a.p("r2") }
    }
    fn state_file(&self, id: &str) -> PathBuf {
        self.state.join(format!("{id}.state"))
    }
    fn journal_file(&self, id: &str) -> PathBuf {
        self.state.join(format!("{id}.journal"))
    }
    fn meta_file(&self, id: &str) -> PathBuf {
        self.state.join(format!("{id}.meta.age"))
    }
    fn pending_file(&self, id: &str) -> PathBuf {
        self.state.join("pending").join(format!("{id}.json"))
    }
}

struct RunOpts {
    interrupt_after: Option<usize>,
    shuffle: bool,
    stream_window: Option<u64>,
    stat_check: bool,
    sequential: bool,
    max_parts: Option<usize>,
}

impl RunOpts {
    fn from(a: &Args) -> RunOpts {
        RunOpts {
            interrupt_after: a.n("interrupt-after"),
            shuffle: a.flag("shuffle"),
            stream_window: a.n("stream-window"),
            // TEST HOOK: --no-stat-check models a platform/filesystem where an
            // edit is invisible to stat (same size, restored mtime, no ctime).
            stat_check: !a.flag("no-stat-check"),
            sequential: a.flag("sequential-source"),
            max_parts: a.n("max-parts"),
        }
    }
}

fn open_source(path: &Path, sequential: bool) -> Box<dyn ChunkSource> {
    let r: io::Result<Box<dyn ChunkSource>> = if sequential {
        SequentialSource::open(path).map(|s| Box::new(s) as Box<dyn ChunkSource>)
    } else {
        RandomSource::open(path).map(|s| Box::new(s) as Box<dyn ChunkSource>)
    };
    r.unwrap_or_else(|e| die(io_code(&e), &format!("SOURCE MISSING or unreadable: {e}")))
}

fn check_snapshot(path: &Path, snap: &Snapshot, o: &RunOpts) {
    if !o.stat_check {
        return;
    }
    match snapshot(path) {
        Err(e) => die(io_code(&e), &format!("SOURCE MISSING: {e}")),
        Ok(s) if &s != snap => die(65, "SOURCE CHANGED since the pass-1 snapshot: abort this upload, re-queue the file"),
        Ok(_) => {}
    }
}

/// Upload loop shared by start and resume: generates ONLY parts not yet
/// recorded as done, in windows, releasing each window only after
/// Generator::gen_range verified it and the source still matches the snapshot.
fn run_upload(st: &UploadState, journal: &mut Journal, r2: &Path, o: &RunOpts) -> Value {
    let src_path = PathBuf::from(&st.source_path);
    check_snapshot(&src_path, &st.snapshot, o);
    let mut src = open_source(&src_path, o.sequential);
    let prefix = st.prefix();
    let mut pk = st.payload_key();
    let l = st.layout;
    let mut gen = Generator::new(l, &prefix, &pk, src.as_mut());
    pk.zeroize();
    let mut todo: Vec<u64> = (0..l.num_parts()).filter(|p| !journal.done.contains_key(p)).collect();
    if o.shuffle {
        todo.shuffle(&mut OsRng);
    }
    if let Some(m) = o.max_parts {
        todo.truncate(m);
    }
    eprintln!("PLAN {}", json!({"already_completed": journal.done.keys().map(|p| p + 1).collect::<Vec<_>>(), "todo": todo.iter().map(|p| p + 1).collect::<Vec<_>>()}));
    let mut out = Vec::new();
    let mut generated = vec![];
    for (i, &p) in todo.iter().enumerate() {
        let windows = part_windows(&l, p, o.stream_window);
        let interrupt = o.interrupt_after == Some(i);
        let cut_window = if o.stream_window.is_some() && windows.len() > 1 { Some(windows.len() / 2) } else { None };
        let mut em = Emitter::begin(r2, &st.object_key, &format!("part-{:05}", p + 1));
        for (wi, &(a, b)) in windows.iter().enumerate() {
            if interrupt && cut_window == Some(wi) {
                eprintln!("SIMULATED INTERRUPTION during part {} after {} of {} windows", p + 1, wi, windows.len());
                std::process::exit(75);
            }
            match gen.gen_range(journal, a, b, &mut out) {
                Ok(()) => {}
                Err(GenError::SourceChanged(c)) => die(65, &format!("SOURCE CHANGED in chunk {c} (part {}): refusing to re-encrypt under the same key", p + 1)),
                Err(GenError::Io(e)) => die(io_code(&e), &format!("source read failed: {e}")),
            }
            // Re-stat after generating and before releasing: every released
            // window was produced while the source matched the snapshot.
            check_snapshot(&src_path, &st.snapshot, o);
            if interrupt && cut_window.is_none() {
                em.emit(&out[..out.len() / 2]);
                eprintln!("SIMULATED INTERRUPTION during part {}", p + 1);
                std::process::exit(75);
            }
            em.emit(&out);
        }
        let etag = em.finish();
        journal.record_done(p, &etag).unwrap_or_else(|e| die(74, &e.to_string()));
        generated.push(p + 1);
    }
    let remaining = l.num_parts() - journal.done.len() as u64;
    let mut v = json!({
        "generated_parts": generated,
        "num_parts": l.num_parts(),
        "remaining_parts": remaining,
        "source_bytes_read": gen.source_bytes_read(),
        "source_restarts": gen.source_restarts(),
        "chunks_encrypted": gen.chunks_encrypted,
        "journal_bytes_written": journal.bytes_written,
    });
    merge(&mut v, resource_json());
    v
}

fn merge(a: &mut Value, b: Value) {
    if let (Some(a), Value::Object(b)) = (a.as_object_mut(), b) {
        a.extend(b);
    }
}

fn load_trust_args(a: &Args) -> Trust {
    let bytes = fs::read(a.p("trust")).unwrap_or_else(|e| die(2, &format!("trust bundle: {e}")));
    load_trust(&bytes, &a.s("trust-pin")).unwrap_or_else(|e| die(2, &format!("TRUST REFUSED: {e}")))
}

// ------------------------------------------------------------ records (A2: signed-note, sealed at the end)

/// Allocates the next per-device sequence number (durable before use).
fn alloc_seq(d: &Dirs) -> u64 {
    let _l = lock_upload(&d.state, "device-seq").unwrap_or_else(|e| die(73, &e));
    let p = d.state.join("device_seq");
    let cur: u64 = fs::read_to_string(&p).ok().and_then(|s| s.trim().parse().ok()).unwrap_or(0);
    write_atomic(&p, (cur + 1).to_string().as_bytes()).unwrap();
    cur + 1
}

/// Unsigned record body (persisted at upload start, signed at sealing).
fn record_body(device_id: &str, hr: &HashResult, object: Value, path: &Path) -> Value {
    json!({
        "v": 1,
        "kind": META_KIND,
        "device_id": device_id,
        "dedup_id": hex::encode(hr.dedup_id),
        "sha256": hex::encode(hr.sha256),
        "size": hr.snapshot.size,
        "object": object,
        "source_locator": format!("file://{}", path.display()),
        "name": path.file_name().map(|p| p.to_string_lossy().to_string()),
        "mtime_ns": hr.snapshot.mtime_ns,
        "ctime_ns": hr.snapshot.ctime_ns,
        "file_id": hr.snapshot.file_id,
        "content_encoding": "identity",
    })
}

/// Seals a record: allocate device_seq + record_id, sign (signed-note,
/// Ed25519, key name = device_id), encrypt to the trust-bundle recipients.
/// Returns (signed plaintext, age ciphertext).
fn seal_record(d: &Dirs, trust: &Trust, sk: &ed25519_dalek::SigningKey, device_id: &str, mut body: Value) -> (Vec<u8>, Vec<u8>) {
    body["device_seq"] = json!(alloc_seq(d));
    body["record_id"] = json!(rand_hex(16));
    body["recorded_at"] = json!(now_secs());
    let pt = sign_note(&padded_text(body, device_id), device_id, sk);
    let ct = encrypt_small(&trust.recipients, &pt);
    (pt, ct)
}

/// After the content is in R2 (or was a dedup hit): persist the record and the
/// non-secret "awaiting commit" note, upload the record. Nothing here can
/// decrypt anything.
#[allow(clippy::too_many_arguments)]
fn finish_pending(d: &Dirs, id: &str, device_id: &str, dedup_id: &str, sha: &str, size: u64, object_key: Option<&str>, source: &str, snap: &Snapshot, rec_pt: &[u8], rec_ct: &[u8]) -> Value {
    let meta_local = d.meta_file(id);
    write_atomic(&meta_local, rec_ct).unwrap();
    let meta_key = format!("meta/{device_id}/{}.age", rand_hex(16)); // no dedup_id in the key
    let pending = json!({
        "v": 2, "status": "awaiting_commit", "device_id": device_id, "dedup_id": dedup_id,
        "sha256": sha, "size": size, "object_key": object_key, "meta_key": meta_key,
        "record_sha256": hex::encode(sha256(rec_pt)), "meta_file": meta_local.to_string_lossy(),
        "source_path": source, "snapshot": snap,
    });
    write_atomic(&d.pending_file(id), serde_json::to_vec_pretty(&pending).unwrap().as_slice()).unwrap();
    let mp = d.r2.join(&meta_key);
    fs::create_dir_all(mp.parent().unwrap()).unwrap();
    fs::write(&mp, rec_ct).unwrap(); // simulated single PUT of the metadata record
    json!({"pending": d.pending_file(id), "meta_key": meta_key, "meta_r2_path": mp})
}

fn cmd_start(a: &Args) {
    let d = Dirs::from(a);
    let o = RunOpts::from(a);
    let trust = load_trust_args(a);
    let dev_sk = load_signing_key(&a.p("device-key")).unwrap_or_else(|e| die(2, &e));
    let device_id = a.s("device-id");
    let file = fs::canonicalize(a.p("file")).unwrap_or_else(|e| die(io_code(&e), &format!("SOURCE MISSING: {e}")));
    let family = hex::decode(a.s("family-secret")).unwrap_or_else(|_| die(2, "family secret hex"));
    let dk = dedup_key(&family);
    let hr = match hash_pass(&file, &dk) {
        Ok(h) => h,
        Err(PassError::Unstable(m)) => die(69, &format!("SOURCE UNSTABLE: {m}")),
        Err(PassError::Io(e)) => die(io_code(&e), &e.to_string()),
    };
    let size = hr.snapshot.size;
    let nh = new_header(&trust.recipients, &hr.sha256, None).unwrap_or_else(|e| die(2, &e));
    let prefix_len = nh.prefix.len() as u64;
    let layout = match a.n::<u64>("chunks-per-part") {
        Some(k) => Layout { pt_len: size, chunks_per_part: k, prefix_len }, // TEST-ONLY override
        None => Layout::policy(size, prefix_len).unwrap_or_else(|e| die(2, &e)),
    };
    if layout.num_parts() > R2_MAX_PARTS {
        die(2, "too many parts");
    }
    let mut pk = nh.payload_key;
    let prefix = nh.prefix;
    let id = rand_hex(16);
    let dedup_hex = hex::encode(hr.dedup_id);
    let sha_hex = hex::encode(hr.sha256);
    let object_key = format!("staging/{dedup_hex}/{id}");
    let mac = header_mac_b64(&prefix).unwrap();
    let object = json!({"key": object_key, "header_mac": mac, "ct_len": layout.ct_len(), "prefix_len": prefix_len,
                        "profile": trust.profile, "stanzas": trust.recipients.len()});
    let body = record_body(&device_id, &hr, object, &file);
    let mode = if layout.num_parts() == 1 { "put" } else { "multipart" };
    eprintln!(
        "UPLOAD {}",
        json!({"upload_id": id, "object_key": object_key, "mode": mode, "pt_len": size, "ct_len": layout.ct_len(), "prefix_len": prefix_len,
               "part_size": layout.part_size(), "num_parts": layout.num_parts(), "sha256": sha_hex, "dedup_id": dedup_hex})
    );
    let src_path = file.to_string_lossy().to_string();

    if mode == "put" {
        // Single PUT, no resume state: an interrupted PUT is retried from
        // scratch with fresh randomness (a different key).
        let mut journal = Journal::memory();
        let mut src = open_source(&file, o.sequential);
        let mut gen = Generator::new(layout, &prefix, &pk, src.as_mut());
        pk.zeroize();
        let mut out = vec![];
        match gen.gen_range(&mut journal, 0, layout.ct_len(), &mut out) {
            Ok(()) => {}
            Err(GenError::SourceChanged(c)) => die(65, &format!("SOURCE CHANGED in chunk {c}")),
            Err(GenError::Io(e)) => die(io_code(&e), &format!("source read failed: {e}")),
        }
        check_snapshot(&file, &hr.snapshot, &o);
        let mut em = Emitter::begin(&d.r2, &object_key, "object");
        if o.interrupt_after.is_some() {
            em.emit(&out[..out.len() / 2]);
            eprintln!("SIMULATED INTERRUPTION during single PUT (next start uses a fresh key)");
            std::process::exit(75);
        }
        em.emit(&out);
        em.finish();
        let (rpt, rct) = seal_record(&d, &trust, &dev_sk, &device_id, body);
        let mut v = json!({"mode": "put", "upload_id": id, "object_key": object_key, "object": d.r2.join(&object_key).join("object"), "generated_parts": [1], "num_parts": 1});
        merge(&mut v, finish_pending(&d, &id, &device_id, &dedup_hex, &sha_hex, size, Some(&object_key), &src_path, &hr.snapshot, &rpt, &rct));
        merge(&mut v, resource_json());
        println!("{v}");
        return;
    }

    let _lock = lock_upload(&d.state, &id).unwrap_or_else(|e| die(73, &e));
    let unsigned = d.state.join(format!("{id}.record.json"));
    write_atomic(&unsigned, serde_json::to_vec(&body).unwrap().as_slice()).unwrap();
    let key = d.ks.create(&id).unwrap();
    let st = UploadState {
        v: 2,
        upload_id: id.clone(),
        r2_upload_id: rand_hex(12),
        object_key: object_key.clone(),
        device_id,
        source_path: src_path,
        snapshot: hr.snapshot.clone(),
        layout,
        sha256: sha_hex,
        dedup_id: dedup_hex,
        prefix_b64: B64P.encode(&prefix),
        payload_key_b64: B64P.encode(pk),
        meta_file: unsigned.to_string_lossy().into(),
        meta_sha256: String::new(),
    };
    seal_state(&st, &key, &d.state_file(&id)).unwrap();
    let mut journal = Journal::create(&d.journal_file(&id), &pk).unwrap();
    pk.zeroize();
    let mut v = run_upload(&st, &mut journal, &d.r2, &o);
    merge(&mut v, json!({"mode": "multipart", "upload_id": id, "object_key": object_key}));
    println!("{v}");
}

fn open_upload(d: &Dirs, id: &str) -> (File, UploadState, Journal) {
    let lock = lock_upload(&d.state, id).unwrap_or_else(|e| die(73, &format!("upload {id}: {e}")));
    let st = open_state(&d.ks, &d.state_file(id)).unwrap_or_else(|e| die(76, &format!("STATE CORRUPT or missing ({e}): abort this upload and start over")));
    let j = Journal::open(&d.journal_file(id), &st.payload_key()).unwrap_or_else(|e| die(76, &format!("JOURNAL CORRUPT ({e}): abort this upload and start over")));
    (lock, st, j)
}

fn cmd_resume(a: &Args) {
    let d = Dirs::from(a);
    let (_lock, st, mut j) = open_upload(&d, &a.s("upload-id"));
    let v = run_upload(&st, &mut j, &d.r2, &RunOpts::from(a));
    println!("{v}");
}

/// Simulated CompleteMultipartUpload, then sealing of the record and local
/// cleanup: the key entry, sealed state and journal are deleted.
fn cmd_complete(a: &Args) {
    let d = Dirs::from(a);
    let id = a.s("upload-id");
    let trust = load_trust_args(a);
    let dev_sk = load_signing_key(&a.p("device-key")).unwrap_or_else(|e| die(2, &e));
    let (_lock, st, j) = open_upload(&d, &id);
    let l = st.layout;
    let dir = d.r2.join(&st.object_key);
    let objp = dir.join("object");
    let mut out = File::create(&objp).unwrap();
    for p in 0..l.num_parts() {
        let etag = j.done.get(&p).unwrap_or_else(|| die(2, &format!("part {} not uploaded yet", p + 1)));
        let bytes = fs::read(dir.join(format!("part-{:05}", p + 1))).unwrap();
        if &hex::encode(Sha256::digest(&bytes)) != etag {
            die(2, &format!("ETag mismatch part {}", p + 1));
        }
        let (s, e) = l.part_range(p);
        if bytes.len() as u64 != e - s {
            die(2, &format!("part {} has wrong size", p + 1));
        }
        out.write_all(&bytes).unwrap();
    }
    out.sync_all().unwrap();
    let body: Value = serde_json::from_slice(&fs::read(&st.meta_file).unwrap()).unwrap();
    let (rpt, rct) = seal_record(&d, &trust, &dev_sk, &st.device_id, body);
    let mut v = json!({"object": objp, "object_len": l.ct_len(), "object_key": st.object_key, "upload_id": id});
    merge(&mut v, finish_pending(&d, &id, &st.device_id, &st.dedup_id, &st.sha256, l.pt_len, Some(&st.object_key), &st.source_path, &st.snapshot, &rpt, &rct));
    d.ks.delete(&id).unwrap();
    remove_if_exists(&d.state_file(&id)).unwrap();
    remove_if_exists(&d.journal_file(&id)).unwrap();
    remove_if_exists(Path::new(&st.meta_file)).unwrap();
    let _ = fs::remove_file(d.state.join(format!("{id}.lock")));
    println!("{v}");
}

fn cmd_abort(a: &Args) {
    let d = Dirs::from(a);
    let id = a.s("upload-id");
    let _lock = lock_upload(&d.state, &id).unwrap_or_else(|e| die(73, &e));
    if let Ok(st) = open_state(&d.ks, &d.state_file(&id)) {
        let dir = d.r2.join(&st.object_key);
        for e in fs::read_dir(&dir).into_iter().flatten().flatten() {
            if e.file_name().to_string_lossy().starts_with("part-") {
                let _ = fs::remove_file(e.path());
            }
        }
    }
    d.ks.delete(&id).unwrap();
    for p in [d.state_file(&id), d.journal_file(&id), d.meta_file(&id), d.state.join(format!("{id}.record.json")), d.state.join(format!("{id}.lock"))] {
        remove_if_exists(&p).unwrap();
    }
    println!("{}", json!({"aborted": id}));
}

fn cmd_dedup_hit(a: &Args) {
    let d = Dirs::from(a);
    let trust = load_trust_args(a);
    let dev_sk = load_signing_key(&a.p("device-key")).unwrap_or_else(|e| die(2, &e));
    let device_id = a.s("device-id");
    let file = fs::canonicalize(a.p("file")).unwrap_or_else(|e| die(66, &e.to_string()));
    let dk = dedup_key(&hex::decode(a.s("family-secret")).unwrap());
    let hr = hash_pass(&file, &dk).unwrap_or_else(|e| die(69, &format!("{e:?}")));
    let id = rand_hex(16);
    let (rpt, rct) = seal_record(&d, &trust, &dev_sk, &device_id, record_body(&device_id, &hr, Value::Null, &file));
    let mut v = json!({"upload_id": id, "dedup_id": hex::encode(hr.dedup_id)});
    merge(&mut v, finish_pending(&d, &id, &device_id, &hex::encode(hr.dedup_id), &hex::encode(hr.sha256), hr.snapshot.size, None, &file.to_string_lossy(), &hr.snapshot, &rpt, &rct));
    println!("{v}");
}

fn cmd_regen_all(a: &Args) {
    let d = Dirs::from(a);
    let (_lock, st, mut j) = open_upload(&d, &a.s("upload-id"));
    let mut src = open_source(Path::new(&st.source_path), false);
    let prefix = st.prefix();
    let pk = st.payload_key();
    let mut gen = Generator::new(st.layout, &prefix, &pk, src.as_mut());
    let mut f = File::create(a.p("out")).unwrap();
    let mut out = vec![];
    for p in 0..st.layout.num_parts() {
        let (s, e) = st.layout.part_range(p);
        gen.gen_range(&mut j, s, e, &mut out).unwrap_or_else(|e| die(65, &format!("{e:?}")));
        f.write_all(&out).unwrap();
    }
}

fn cmd_check_receipt(a: &Args) {
    let trust = load_trust_args(a);
    let pend: Value = serde_json::from_slice(&fs::read(a.p("pending")).unwrap_or_else(|e| die(12, &e.to_string()))).unwrap();
    let raw = fs::read(a.p("receipt")).unwrap_or_else(|e| die(12, &e.to_string()));
    let lk = |n: &str| if n == "homelab-receipt" { Some(trust.receipt_key) } else { None };
    let (text, _) = open_note(&raw, &lk).unwrap_or_else(|e| die(12, &format!("RECEIPT INVALID: {e}")));
    let body = parse_text_json(&text).unwrap_or_else(|e| die(12, &format!("RECEIPT INVALID: {e}")));
    let content_only = a.flag("content-only");
    let mut checks = vec![("kind", body["kind"] == RECEIPT_KIND), ("dedup_id", body["dedup_id"] == pend["dedup_id"]), ("size", body["size"] == pend["size"])];
    if !content_only {
        checks.push(("device_id", body["device_id"] == pend["device_id"]));
        checks.push(("record_sha256", body["record_sha256"] == pend["record_sha256"]));
    }
    if let Some((what, _)) = checks.iter().find(|(_, ok)| !ok) {
        die(12, &format!("RECEIPT INVALID: {what} does not match this file"));
    }
    if a.flag("consume") && !content_only {
        let _ = fs::remove_file(pend["meta_file"].as_str().unwrap_or(""));
        fs::remove_file(a.p("pending")).unwrap();
    }
    println!("{}", json!({"protected": true, "scope": if content_only {"content"} else {"file-record"}, "dedup_id": body["dedup_id"], "committed_at": body["committed_at"]}));
}

// ------------------------------------------------------------ homelab side

fn load_ids(a: &Args) -> Vec<Identity> {
    parse_identity_file(&fs::read_to_string(a.p("identity")).unwrap_or_else(|e| die(2, &e.to_string()))).unwrap_or_else(|e| die(2, &e))
}

/// The stanza-profile check (F3 parser rule): exactly the expected number of
/// stanzas, all of the profile's type, nothing else (no grease, scrypt, plugin).
fn profile_check(h: &Header, profile: &str, n: usize) -> Result<(), String> {
    let want = match profile {
        "pq" => PQ_TYPE,
        "x25519" => "X25519",
        _ => return Err("unknown profile".into()),
    };
    if h.stanzas.len() != n || h.stanzas.iter().any(|s| s.typ != want) {
        let got: Vec<&str> = h.stanzas.iter().map(|s| s.typ.as_str()).collect();
        return Err(format!("expected {n} x {want}, got {got:?}"));
    }
    Ok(())
}

fn read_prefix_buf(path: &Path) -> Vec<u8> {
    let mut f = File::open(path).unwrap();
    let mut b = vec![0u8; MAX_HEADER_LEN + 16];
    let mut have = 0;
    loop {
        let k = f.read(&mut b[have..]).unwrap();
        if k == 0 || have + k == b.len() {
            have += k;
            break;
        }
        have += k;
    }
    b.truncate(have);
    b
}

fn stream_code(e: &OpenErr) -> &'static str {
    match e {
        OpenErr::Header(_) => "E_OBJECT_HEADER",
        OpenErr::NoMatch => "E_OBJECT_NO_MATCH",
        OpenErr::Hmac => "E_OBJECT_HMAC",
        OpenErr::Payload(m) if m.contains("truncated") || m.contains("no chunks") || m.contains("final chunk is empty") => "E_STREAM_TRUNCATED",
        OpenErr::Payload(m) if m.contains("trailing data") => "E_STREAM_TRAILING",
        OpenErr::Payload(_) => "E_STREAM_AUTH",
    }
}

/// Homelab ingest. Nothing is committed, catalogued or acknowledged until the
/// record signature, the record/object binding, the stanza profile and the
/// whole object (final chunk authenticated; size, SHA-256, dedup HMAC) check out.
/// Every rejection prints `REJECT {"code": ...}` and exits 10.
fn cmd_ingest(a: &Args) {
    let temps: std::cell::RefCell<Vec<PathBuf>> = Default::default();
    let reject = |code: &str, m: &str| -> ! {
        for t in temps.borrow().iter() {
            let _ = fs::remove_file(t);
        }
        eprintln!("REJECT {}", json!({"code": code, "detail": m}));
        std::process::exit(10)
    };
    let ids = load_ids(a);
    let strict = !a.flag("lax-low-order");
    let profile = a.o("profile").unwrap_or_else(|| "pq".into());
    let n_stanzas: usize = a.n("stanzas").unwrap_or(1);
    let dk = dedup_key(&hex::decode(a.s("family-secret")).unwrap());
    let registry: HashMap<String, String> = serde_json::from_slice(&fs::read(a.p("registry")).unwrap()).unwrap();
    let receipt_sk = load_signing_key(&a.p("receipt-key")).unwrap_or_else(|e| die(2, &e));
    let store = a.p("store");
    for sub in ["tmp", "objects", "by-dedup", "devices"] {
        fs::create_dir_all(store.join(sub)).unwrap();
    }
    // 1. record: size limit, stanza profile, decrypt, signature
    let meta_ct = fs::read(a.p("meta")).unwrap();
    if meta_ct.len() > 1 << 20 {
        reject("E_RECORD_TOO_LARGE", "metadata record too large");
    }
    match parse_header(&meta_ct) {
        Ok(h) => profile_check(&h, &profile, n_stanzas).unwrap_or_else(|e| reject("E_PROFILE", &format!("record header: {e}"))),
        Err(e) => reject("E_RECORD_DECRYPT", &e.to_string()),
    }
    let mut rec_pt = vec![];
    decrypt_file(meta_ct.as_slice(), &ids, strict, |b| {
        rec_pt.extend_from_slice(b);
        Ok(())
    })
    .unwrap_or_else(|e| reject("E_RECORD_DECRYPT", &e.to_string()));
    let lookup = |k: &str| registry.get(k).and_then(|s| parse_pk_b64(s).ok());
    let (text, key_name) = open_note(&rec_pt, &lookup).unwrap_or_else(|e| {
        let code = e.split(':').next().unwrap_or("E_RECORD_FORMAT").to_string();
        reject(&code, &e)
    });
    let rec = parse_text_json(&text).unwrap_or_else(|e| reject("E_RECORD_FORMAT", &e));
    if rec["kind"] != META_KIND || rec["v"] != 1 {
        reject("E_RECORD_KIND", "not a v1 file-meta record");
    }
    if rec["device_id"] != key_name.as_str() {
        reject("E_DEVICE_MISMATCH", "record device_id does not match its signing key");
    }
    let size = rec["size"].as_u64().unwrap_or_else(|| reject("E_RECORD_FIELDS", "size"));
    let want_sha = rec["sha256"].as_str().unwrap_or_else(|| reject("E_RECORD_FIELDS", "sha256")).to_string();
    let want_dedup = rec["dedup_id"].as_str().unwrap_or_else(|| reject("E_RECORD_FIELDS", "dedup_id")).to_string();
    let record_id = rec["record_id"].as_str().unwrap_or_else(|| reject("E_RECORD_FIELDS", "record_id")).to_string();
    let seq = rec["device_seq"].as_u64().unwrap_or_else(|| reject("E_RECORD_FIELDS", "device_seq"));
    for (n, v) in [("dedup_id", &want_dedup), ("sha256", &want_sha)] {
        if v.len() != 64 || !v.bytes().all(|b| b.is_ascii_hexdigit()) {
            reject("E_RECORD_FIELDS", n);
        }
    }
    let record_sha = hex::encode(sha256(&rec_pt));
    // 2. replay / duplicate (per-device seen set; order-independent: R2 and USB may reorder)
    let dev_path = store.join("devices").join(format!("{key_name}.json"));
    let mut seen: Value = fs::read(&dev_path).ok().and_then(|b| serde_json::from_slice(&b).ok()).unwrap_or(json!({"by_record": {}, "by_seq": {}}));
    if let Some(prev) = seen["by_record"].get(&record_id) {
        if prev == &json!(record_sha) {
            eprintln!("DUPLICATE record {record_id}: already committed, receipt re-issued, no catalog write");
            let r = fs::read(store.join("receipts").join(format!("{record_sha}.note"))).unwrap();
            fs::write(a.p("out"), r).unwrap();
            println!("{}", json!({"committed": true, "duplicate": true}));
            return;
        }
        reject("E_REPLAY_RECORD_ID", "record_id reused with different content");
    }
    if let Some(prev) = seen["by_seq"].get(seq.to_string()) {
        if prev != &json!(record_id) {
            reject("E_REPLAY_SEQ", &format!("device_seq {seq} already used by another record"));
        }
    }
    // 3. content
    let by_dedup = store.join("by-dedup").join(&want_dedup);
    if rec["object"].is_object() {
        let o = &rec["object"];
        let obj_path = if let Some(p) = a.o("object") {
            PathBuf::from(p)
        } else {
            let t = store.join("tmp").join(format!("{}.age", rand_hex(8)));
            temps.borrow_mut().push(t.clone());
            let mut out = File::create(&t).unwrap();
            let mut names: Vec<_> = fs::read_dir(a.p("parts")).unwrap().flatten().map(|e| e.file_name().to_string_lossy().to_string()).filter(|n| n.starts_with("part-")).collect();
            names.sort();
            for n in names {
                io::copy(&mut File::open(a.p("parts").join(n)).unwrap(), &mut out).unwrap();
            }
            t
        };
        let obj_len = fs::metadata(&obj_path).unwrap().len();
        let head = read_prefix_buf(&obj_path);
        let h = parse_header(&head).unwrap_or_else(|e| reject("E_OBJECT_HEADER", &e.to_string()));
        profile_check(&h, &profile, n_stanzas).unwrap_or_else(|e| reject("E_PROFILE", &format!("object header: {e}")));
        let mac = base64::engine::general_purpose::STANDARD_NO_PAD.encode(h.mac);
        if !a.flag("skip-binding-precheck") {
            // TEST-ONLY flag above: shows the STREAM layer alone still rejects.
            if o["header_mac"].as_str() != Some(mac.as_str()) {
                reject("E_BINDING_HEADER_MAC", "object header MAC does not match the signed record");
            }
            if o["prefix_len"].as_u64() != Some(h.len as u64 + 16) {
                reject("E_BINDING_PREFIX", "object prefix length does not match the signed record");
            }
            if o["ct_len"].as_u64() != Some(obj_len) {
                reject("E_BINDING_LENGTH", &format!("object is {obj_len} bytes, signed record says {}", o["ct_len"]));
            }
            match Layout::pt_len_from_ct_len(obj_len, h.len as u64 + 16) {
                Ok(n) if n == size => {}
                Ok(n) => reject("E_BINDING_SIZE", &format!("object length implies {n} plaintext bytes, record says {size}")),
                Err(e) => reject("E_LENGTH_INVALID", &e),
            }
        }
        let tmp_plain = store.join("tmp").join(format!("{}.plain", rand_hex(8)));
        temps.borrow_mut().push(tmp_plain.clone());
        let mut out = File::create(&tmp_plain).unwrap();
        let mut sha = Sha256::new();
        let mut hm = <hmac::Hmac<Sha256> as hmac::KeyInit>::new_from_slice(&dk).unwrap();
        let n = decrypt_file(File::open(&obj_path).unwrap(), &ids, strict, |b| {
            sha.update(b);
            hmac::Mac::update(&mut hm, b);
            out.write_all(b)
        })
        .unwrap_or_else(|e| reject(stream_code(&e), &e.to_string()));
        let got_sha = hex::encode(sha.finalize());
        let got_dedup = hex::encode(hmac::Mac::finalize(hm).into_bytes());
        if n != size || got_sha != want_sha || got_dedup != want_dedup {
            reject("E_CONTENT_MISMATCH", &format!("size {n}/{size}, sha256 ok={}, dedup_id ok={}", got_sha == want_sha, got_dedup == want_dedup));
        }
        out.sync_all().unwrap();
        let dest = store.join("objects").join(&got_sha);
        if !dest.exists() {
            fs::rename(&tmp_plain, &dest).unwrap();
        }
        write_atomic(&by_dedup, format!("{got_sha} {n}").as_bytes()).unwrap();
        for t in temps.borrow().iter() {
            let _ = fs::remove_file(t);
        }
    } else if !rec["object"].is_null() {
        reject("E_RECORD_FIELDS", "object must be an object or null");
    } else {
        match fs::read_to_string(&by_dedup) {
            Ok(s) if s == format!("{want_sha} {size}") => {}
            Ok(_) => reject("E_DEDUP_MISMATCH", "dedup record does not match committed content"),
            Err(_) => die(11, "INGEST PENDING: content for this dedup_id is not committed yet"),
        }
    }
    // 4. catalog + seen-set + receipt
    let mut cat = OpenOptions::new().create(true).append(true).open(store.join("catalog.jsonl")).unwrap();
    writeln!(cat, "{}", json!({"record": rec, "record_sha256": record_sha})).unwrap();
    cat.sync_all().unwrap();
    seen["by_record"][&record_id] = json!(record_sha);
    seen["by_seq"][seq.to_string()] = json!(record_id);
    write_atomic(&dev_path, serde_json::to_vec(&seen).unwrap().as_slice()).unwrap();
    let body = json!({"v": 1, "kind": RECEIPT_KIND, "dedup_id": want_dedup, "size": size, "device_id": rec["device_id"],
                      "record_id": record_id, "device_seq": seq, "record_sha256": record_sha, "committed_at": now_secs()});
    let note = sign_note(&(serde_json::to_string(&body).unwrap() + "\n"), "homelab-receipt", &receipt_sk);
    fs::create_dir_all(store.join("receipts")).unwrap();
    fs::write(store.join("receipts").join(format!("{record_sha}.note")), &note).unwrap();
    fs::write(a.p("out"), note).unwrap();
    println!("{}", json!({"committed": true, "sha256": want_sha, "dedup_id": want_dedup}));
}

/// Homelab random access: read ONLY the prefix, the final chunk and chunk i.
/// The final chunk is authenticated first (CE §5.5).
fn cmd_chunk(a: &Args) {
    let ids = load_ids(a);
    let path = a.p("object");
    let obj_len = fs::metadata(&path).unwrap().len();
    let head = read_prefix_buf(&path);
    let (pk, prefix_len, _) = open_prefix(&head, &ids, true).unwrap_or_else(|e| die(2, &e.to_string()));
    let pt_len = Layout::pt_len_from_ct_len(obj_len, prefix_len as u64).unwrap_or_else(|e| die(2, &e));
    let layout = Layout { pt_len, chunks_per_part: 1, prefix_len: prefix_len as u64 };
    let cipher = PayloadCipher::new(&pk, layout.n_chunks());
    let mut f = File::open(&path).unwrap();
    let mut read_chunk = |c: u64| -> Vec<u8> {
        let (s, e) = layout.chunk_obj_range(c);
        let mut buf = vec![0u8; (e - s) as usize];
        f.seek(SeekFrom::Start(s)).unwrap();
        f.read_exact(&mut buf).unwrap();
        buf
    };
    let last = layout.n_chunks() - 1;
    let mut fin = read_chunk(last);
    cipher.decrypt_chunk(last, &mut fin).unwrap_or_else(|e| die(2, &format!("final chunk: {e} (truncated or tampered object)")));
    let i: u64 = a.n("index").unwrap_or_else(|| die(2, "missing --index"));
    if i > last {
        die(2, "chunk index out of range");
    }
    let mut buf = read_chunk(i);
    cipher.decrypt_chunk(i, &mut buf).unwrap_or_else(|e| die(2, &e));
    fs::write(a.p("out"), &buf).unwrap();
}

// ------------------------------------------------------------ key tooling

fn cmd_keygen_sign(a: &Args) {
    let mut seed = [0u8; 32];
    OsRng.fill_bytes(&mut seed);
    write_secret_new(&a.p("out"), &seed).unwrap_or_else(|e| die(2, &e.to_string()));
    let sk = ed25519_dalek::SigningKey::from_bytes(&seed);
    seed.zeroize();
    println!("{}", json!({"public_key": pk_b64(&sk)}));
}

/// Rust-side age keygen (A2-S3 reverse direction): pq or x25519.
fn cmd_keygen(a: &Args) {
    // --seed (TEST-ONLY): deterministic identities for project vectors.
    let seed: Option<[u8; 32]> = a.o("seed").map(|h| hex::decode(h).unwrap().try_into().unwrap());
    let id = if a.o("type").as_deref() == Some("x25519") {
        let mut k = [0u8; 32];
        OsRng.fill_bytes(&mut k);
        Identity::X25519(seed.unwrap_or(k))
    } else {
        match seed {
            Some(s) => Identity::pq_from_seed(s).unwrap(),
            None => Identity::generate_pq(),
        }
    };
    let r = id.recipient().encode();
    let _ = fs::remove_file(a.p("out"));
    write_secret_new(&a.p("out"), format!("# public key: {r}\n{}\n", id.encode()).as_bytes()).unwrap_or_else(|e| die(2, &e.to_string()));
    println!("{r}");
}

fn cmd_recipient(a: &Args) {
    for id in load_ids(a) {
        println!("{}", id.recipient().encode());
    }
}

fn cmd_make_trust(a: &Args) {
    let recipients: Vec<String> = fs::read_to_string(a.p("recipients-file")).unwrap().lines().map(str::trim).filter(|l| !l.is_empty() && !l.starts_with('#')).map(String::from).collect();
    let tb = TrustBundle { v: 2, profile: a.o("profile").unwrap_or_else(|| "pq".into()), recipients, receipt_key: a.s("receipt-pub") };
    let bytes = serde_json::to_vec(&tb).unwrap();
    load_trust(&bytes, &hex::encode(sha256(&bytes))).unwrap_or_else(|e| die(2, &e));
    fs::write(a.p("out"), &bytes).unwrap();
    println!("{}", json!({"pin": hex::encode(sha256(&bytes))}));
}

/// TEST-ONLY adversary tool: signs an arbitrary record body with any key and
/// any key name, then encrypts it to the trust-bundle recipients.
fn cmd_sign_meta(a: &Args) {
    let trust = load_trust_args(a);
    let sk = load_signing_key(&a.p("device-key")).unwrap();
    let body: Value = serde_json::from_slice(&fs::read(a.p("body")).unwrap()).unwrap();
    let name = a.s("key-name");
    let text = padded_text(body, &name);
    let pt = match a.o("keyhash-pk") {
        Some(pkb) => sign_note_forged_kh(&text, &name, &sk, key_hash(&name, &parse_pk_b64(&pkb).unwrap())),
        None => sign_note(&text, &name, &sk),
    };
    if let Some(p) = a.o("plain-out") {
        fs::write(p, &pt).unwrap();
    }
    fs::write(a.p("out"), encrypt_small(&trust.recipients, &pt)).unwrap();
}

fn read_recipients(path: &Path) -> Vec<Recipient> {
    fs::read_to_string(path)
        .unwrap()
        .lines()
        .map(str::trim)
        .filter(|l| !l.is_empty() && !l.starts_with('#'))
        .map(|l| Recipient::parse(l).unwrap_or_else(|e| die(2, &e)))
        .collect()
}

/// Whole-file encryption with our encoder (interop, vectors, forgery tests).
/// --seed (TEST-ONLY) makes the output deterministic for project vectors.
fn cmd_encrypt(a: &Args) {
    let recips = read_recipients(&a.p("recipients"));
    let data = fs::read(a.p("in")).unwrap();
    let ctx = match a.o("context") {
        Some(h) => hex::decode(h).unwrap().try_into().unwrap(),
        None => sha256(&data),
    };
    let seed = a.o("seed").map(|h| -> [u8; 32] { hex::decode(h).unwrap().try_into().unwrap() });
    let nh = new_header_opts(&recips, &ctx, seed, a.flag("allow-mixed"), a.flag("grease")).unwrap_or_else(|e| die(2, &e));
    let layout = Layout { pt_len: data.len() as u64, chunks_per_part: 1, prefix_len: nh.prefix.len() as u64 };
    let cipher = PayloadCipher::new(&nh.payload_key, layout.n_chunks());
    let mut out = nh.prefix.clone();
    for c in 0..layout.n_chunks() {
        let (s, e) = layout.chunk_pt_range(c);
        let mut b = data[s as usize..e as usize].to_vec();
        cipher.encrypt_chunk(c, &mut b);
        out.extend_from_slice(&b);
    }
    fs::write(a.p("out"), &out).unwrap();
    println!("{}", json!({"header_len": nh.header_len, "prefix_len": nh.prefix.len(), "ct_len": out.len(), "stanzas": recips.len()}));
}

/// Whole-file decryption with our decoder. Exit 0 on success, 1 on failure;
/// stdout carries {"ok", "class", "error", "bytes", "sha256"}.
fn cmd_decrypt(a: &Args) {
    let ids = load_ids(a);
    let f = File::open(a.p("in")).unwrap();
    let mut out = vec![];
    let r = decrypt_file(f, &ids, !a.flag("lax-low-order"), |b| {
        out.extend_from_slice(b);
        Ok(())
    });
    if let Some(p) = a.o("out") {
        if r.is_ok() {
            fs::write(p, &out).unwrap();
        }
    }
    match r {
        Ok(n) => println!("{}", json!({"ok": true, "class": "success", "bytes": n, "sha256": hex::encode(sha256(&out))})),
        Err(e) => {
            println!("{}", json!({"ok": false, "class": e.class(), "error": e.to_string(), "partial_bytes": out.len(), "partial_sha256": hex::encode(sha256(&out))}));
            std::process::exit(1);
        }
    }
}

/// TEST-ONLY (A2-S2 key-residue scan): the homelab recovers the file key and
/// payload key of an object, so the harness can search the device for them.
fn cmd_debug_keys(a: &Args) {
    let ids = load_ids(a);
    let head = read_prefix_buf(&a.p("object"));
    let (fk, h) = open_header(&head, &ids, true).unwrap_or_else(|e| die(2, &e.to_string()));
    let pk = format::hkdf32(&head[h.len..h.len + 16], b"payload", &fk);
    println!("{}", json!({"file_key": hex::encode(fk), "payload_key": hex::encode(pk), "payload_nonce": hex::encode(&head[h.len..h.len + 16]), "header_mac": base64::engine::general_purpose::STANDARD_NO_PAD.encode(h.mac)}));
}

fn cmd_inspect(a: &Args) {
    let path = a.p("in");
    let head = read_prefix_buf(&path);
    let h = parse_header(&head).unwrap_or_else(|e| die(2, &e.to_string()));
    let len = fs::metadata(&path).unwrap().len();
    println!("{}", json!({"header_len": h.len, "prefix_len": h.len + 16, "file_len": len, "stanzas": h.stanzas.iter().map(|s| json!({"type": s.typ, "args": s.args.len(), "arg_lens": s.args.iter().map(|x| x.len()).collect::<Vec<_>>(), "body_len": s.body.len()})).collect::<Vec<_>>(),
        "pt_len": Layout::pt_len_from_ct_len(len, h.len as u64 + 16).ok()}));
}

/// Runs a directory of CCTV age test vectors through our decoder.
/// Armored and passphrase-only vectors are reported as "n/a" (the Reliquary
/// profile has neither armor nor scrypt).
fn cmd_cctv(a: &Args) {
    let dir = a.p("dir");
    let strict = !a.flag("lax-low-order");
    let mut names: Vec<_> = fs::read_dir(&dir).unwrap().flatten().map(|e| e.file_name().to_string_lossy().to_string()).collect();
    names.sort();
    let (mut pass, mut fail, mut na) = (0, 0, 0);
    let mut fails = vec![];
    for n in &names {
        let raw = fs::read(dir.join(n)).unwrap();
        let mut rest: &[u8] = &raw;
        let mut kv: Vec<(String, String)> = vec![];
        loop {
            let i = rest.iter().position(|&b| b == b'\n').expect("vector header");
            let line = std::str::from_utf8(&rest[..i]).unwrap().to_string();
            rest = &rest[i + 1..];
            if line.is_empty() {
                break;
            }
            let (k, v) = line.split_once(": ").map(|(k, v)| (k.to_string(), v.to_string())).unwrap_or((line.clone(), String::new()));
            kv.push((k, v));
        }
        let get = |k: &str| kv.iter().find(|(kk, _)| kk == k).map(|(_, v)| v.clone());
        let expect = get("expect").unwrap();
        let mut file = rest.to_vec();
        if get("compressed").as_deref() == Some("zlib") {
            let mut d = flate2::read::ZlibDecoder::new(&file[..]);
            let mut o = vec![];
            d.read_to_end(&mut o).unwrap();
            file = o;
        }
        let idents: Vec<Identity> = kv.iter().filter(|(k, _)| k == "identity").map(|(_, v)| Identity::parse(v).unwrap()).collect();
        let armored = get("armored").is_some();
        if armored || idents.is_empty() {
            na += 1;
            println!("{}", json!({"vector": n, "expect": expect, "result": "n/a", "why": if armored {"armor not in profile"} else {"passphrase-only (scrypt not in profile)"}}));
            continue;
        }
        let mut out = vec![];
        let r = decrypt_file(&file[..], &idents, strict, |b| {
            out.extend_from_slice(b);
            Ok(())
        });
        let got = match &r {
            Ok(_) => "success".to_string(),
            Err(e) => e.class().to_string(),
        };
        let mut ok = got == expect;
        let mut note = String::new();
        if let Some(h) = get("payload") {
            let hs = hex::encode(sha256(&out));
            if (expect == "success" || expect == "payload failure") && hs != h {
                ok = false;
                note = format!("payload hash mismatch ({} bytes)", out.len());
            }
        }
        if ok {
            pass += 1;
        } else {
            fail += 1;
            fails.push(n.clone());
        }
        println!("{}", json!({"vector": n, "expect": expect, "got": got, "result": if ok {"pass"} else {"FAIL"}, "error": r.err().map(|e| e.to_string()), "note": note}));
    }
    println!("{}", json!({"summary": {"total": names.len(), "pass": pass, "fail": fail, "n/a": na, "failed": fails, "strict_low_order": strict}}));
}

// ------------------------------------------------------------ benchmarks (A2-S1, x86 container only)

fn per_sec(n: u64, secs: f64) -> f64 {
    (n as f64 / secs * 10.0).round() / 10.0
}

/// Per-object cost of the header: generation (device) and opening (homelab)
/// for 1 x X25519, 1 x PQ and 2 x PQ recipients.
fn cmd_bench_kem(a: &Args) {
    let iters: u64 = a.n("iters").unwrap_or(2000);
    let xi = Identity::X25519([0x42; 32]);
    let p1 = Identity::generate_pq();
    let p2 = Identity::generate_pq();
    let cases: Vec<(&str, Vec<Recipient>, &Identity)> = vec![
        ("x25519x1", vec![xi.recipient()], &xi),
        ("pqx1", vec![p1.recipient()], &p1),
        ("pqx2", vec![p1.recipient(), p2.recipient()], &p2),
    ];
    let mut res = serde_json::Map::new();
    for (name, recips, id) in &cases {
        let ctx = [7u8; 32];
        let warm = new_header(recips, &ctx, None).unwrap();
        let t = Instant::now();
        let mut last = 0;
        for _ in 0..iters {
            let nh = new_header(recips, &ctx, None).unwrap();
            last = nh.header_len;
            std::hint::black_box(&nh.prefix);
        }
        let gen = t.elapsed().as_secs_f64();
        let ids = [match id {
            Identity::X25519(k) => Identity::X25519(*k),
            Identity::Pq { seed, .. } => Identity::pq_from_seed(*seed).unwrap(),
        }];
        let t = Instant::now();
        for _ in 0..iters {
            std::hint::black_box(open_prefix(&warm.prefix, &ids, true).unwrap());
        }
        let open = t.elapsed().as_secs_f64();
        res.insert(
            name.to_string(),
            json!({"header_len": last, "gen_per_sec": per_sec(iters, gen), "gen_us": (gen / iters as f64 * 1e6 * 10.0).round() / 10.0,
                   "open_per_sec": per_sec(iters, open), "open_us": (open / iters as f64 * 1e6 * 10.0).round() / 10.0, "iters": iters}),
        );
    }
    println!("{}", serde_json::to_string_pretty(&res).unwrap());
}

/// Whole-object encryption throughput (header + STREAM, in memory) for a
/// given object size and recipient set, to show where the fixed per-object
/// PQ cost matters.
fn cmd_bench_obj(a: &Args) {
    let size: usize = a.n("size").unwrap_or(1 << 20);
    let count: usize = a.n("count").unwrap_or(200);
    let p1 = Identity::generate_pq();
    let p2 = Identity::generate_pq();
    let xi = Identity::X25519([0x42; 32]);
    let mut data = vec![0u8; size];
    OsRng.fill_bytes(&mut data);
    let mut res = serde_json::Map::new();
    for (name, recips) in [("x25519x1", vec![xi.recipient()]), ("pqx1", vec![p1.recipient()]), ("pqx2", vec![p1.recipient(), p2.recipient()])] {
        let best = (0..3)
            .map(|_| {
                let t = Instant::now();
                for i in 0..count {
                    let mut ctx = [0u8; 32];
                    ctx[..8].copy_from_slice(&(i as u64).to_be_bytes());
                    let nh = new_header(&recips, &ctx, None).unwrap();
                    let layout = Layout { pt_len: size as u64, chunks_per_part: 1, prefix_len: nh.prefix.len() as u64 };
                    let cipher = PayloadCipher::new(&nh.payload_key, layout.n_chunks());
                    let mut buf = Vec::with_capacity(CHUNK_CT as usize);
                    for c in 0..layout.n_chunks() {
                        let (s, e) = layout.chunk_pt_range(c);
                        buf.clear();
                        buf.extend_from_slice(&data[s as usize..e as usize]);
                        cipher.encrypt_chunk(c, &mut buf);
                        std::hint::black_box(&buf);
                    }
                }
                t.elapsed().as_secs_f64()
            })
            .fold(f64::MAX, f64::min);
        let bytes = (size * count) as f64;
        res.insert(name.into(), json!({"objects_per_sec": per_sec(count as u64, best), "MB_per_s": (bytes / best / 1e6 * 10.0).round() / 10.0}));
    }
    res.insert("object_size".into(), size.into());
    res.insert("objects".into(), count.into());
    println!("{}", serde_json::to_string_pretty(&res).unwrap());
}

/// Same as CE's `bench` (pass 1 + pass 2 over a file), with the trust
/// bundle's recipient set, so PQ vs X25519 can be compared on large files.
fn cmd_bench(a: &Args) {
    use chacha20poly1305::aead::{AeadInOut, KeyInit};
    use hmac::Mac;
    let file = a.p("file");
    let size = fs::metadata(&file).unwrap().len();
    let pq = a.o("profile").as_deref() != Some("x25519");
    let recips = if pq { vec![Identity::generate_pq().recipient()] } else { vec![Identity::X25519([0x42; 32]).recipient()] };
    let dk = [7u8; 32];
    let mut v = vec![];
    File::open(&file).unwrap().read_to_end(&mut v).unwrap();
    let reps = 3;
    let mut res = serde_json::Map::new();
    let best = |f: &mut dyn FnMut()| -> f64 {
        (0..reps)
            .map(|_| {
                let t = Instant::now();
                f();
                t.elapsed().as_secs_f64()
            })
            .fold(f64::MAX, f64::min)
    };
    let mbps = |bytes: u64, secs: f64| format!("{:.0} MB/s", bytes as f64 / secs / 1e6);
    let t = best(&mut || {
        let aead = chacha20poly1305::ChaCha20Poly1305::new(&[1u8; 32].into());
        let mut buf = Vec::with_capacity(CHUNK_CT as usize);
        for (i, c) in v.chunks(CHUNK_PT as usize).enumerate() {
            buf.clear();
            buf.extend_from_slice(c);
            aead.encrypt_in_place(&chunk_nonce(i as u64, false).into(), b"", &mut buf).unwrap();
            std::hint::black_box(&buf);
        }
    });
    res.insert("chacha20poly1305_only_mem".into(), mbps(size, t).into());
    let t = best(&mut || {
        std::hint::black_box(hash_pass(&file, &dk).unwrap());
    });
    res.insert("pass1_sha256+hmac_file".into(), mbps(size, t).into());
    let hr = hash_pass(&file, &dk).unwrap();
    let t = best(&mut || {
        let nh = new_header(&recips, &hr.sha256, None).unwrap();
        let layout = Layout::policy(size, nh.prefix.len() as u64).unwrap();
        let mut src = RandomSource::open(&file).unwrap();
        let mut g = Generator::new(layout, &nh.prefix, &nh.payload_key, &mut src);
        let mut j = Journal::memory();
        let mut out = Vec::new();
        for p in 0..layout.num_parts() {
            let (s, e) = layout.part_range(p);
            g.gen_range(&mut j, s, e, &mut out).unwrap();
            std::hint::black_box(&out);
        }
    });
    res.insert("pass2_header+encrypt+tag_journal_file".into(), mbps(size, t).into());
    let mut m = <hmac::Hmac<Sha256> as hmac::KeyInit>::new_from_slice(&dk).unwrap();
    m.update(&v[..0]);
    res.insert("bytes".into(), size.into());
    res.insert("profile".into(), (if pq { "pq" } else { "x25519" }).into());
    println!("{}", serde_json::to_string_pretty(&res).unwrap());
}

/// A2-S1 OL kit workload: encrypt objects of one size back to back for N
/// seconds (in memory, fresh header per object), printing one JSON line per
/// 10-second window, for battery and throttling measurements on phones.
fn cmd_soak(a: &Args) {
    let secs: u64 = a.n("seconds").unwrap_or(600);
    let size: usize = a.n("size").unwrap_or(102_400);
    let profile = a.o("profile").unwrap_or_else(|| "pq".into());
    let p1 = Identity::generate_pq();
    let p2 = Identity::generate_pq();
    let recips = match profile.as_str() {
        "x25519" => vec![Identity::X25519([0x42; 32]).recipient()],
        "pq2" => vec![p1.recipient(), p2.recipient()],
        _ => vec![p1.recipient()],
    };
    let mut data = vec![0u8; size];
    OsRng.fill_bytes(&mut data);
    let t0 = Instant::now();
    let (mut win_start, mut win_objs, mut total) = (Instant::now(), 0u64, 0u64);
    let mut i = 0u64;
    while t0.elapsed().as_secs() < secs {
        let mut ctx = [0u8; 32];
        ctx[..8].copy_from_slice(&i.to_be_bytes());
        let nh = new_header(&recips, &ctx, None).unwrap();
        let layout = Layout { pt_len: size as u64, chunks_per_part: 1, prefix_len: nh.prefix.len() as u64 };
        let cipher = PayloadCipher::new(&nh.payload_key, layout.n_chunks());
        let mut buf = Vec::with_capacity(CHUNK_CT as usize);
        for c in 0..layout.n_chunks() {
            let (s, e) = layout.chunk_pt_range(c);
            buf.clear();
            buf.extend_from_slice(&data[s as usize..e as usize]);
            cipher.encrypt_chunk(c, &mut buf);
            std::hint::black_box(&buf);
        }
        i += 1;
        win_objs += 1;
        total += 1;
        let w = win_start.elapsed().as_secs_f64();
        if w >= 10.0 {
            println!("{}", json!({"t_s": t0.elapsed().as_secs(), "profile": profile, "size": size, "objects_per_s": (win_objs as f64 / w * 10.0).round() / 10.0, "MB_per_s": ((win_objs as f64 * size as f64) / w / 1e6 * 10.0).round() / 10.0}));
            win_start = Instant::now();
            win_objs = 0;
        }
    }
    let el = t0.elapsed().as_secs_f64();
    println!("{}", json!({"done": true, "profile": profile, "size": size, "objects": total, "bytes": total * size as u64, "seconds": (el * 10.0).round() / 10.0, "MB_per_s": ((total as f64 * size as f64) / el / 1e6 * 10.0).round() / 10.0}));
}

/// Probe: what does hpke 0.14.1 do when asked for Auth mode with X-Wing?
fn cmd_hpke_auth_probe(_a: &Args) {
    use hpke::{kem::XWing, Kem as K};
    let (sk_s, pk_s) = XWing::gen_keypair();
    let (_sk_r, pk_r) = XWing::gen_keypair();
    std::panic::set_hook(Box::new(|_| {}));
    let r = std::panic::catch_unwind(|| {
        let mode = hpke::OpModeS::Auth((sk_s.clone(), pk_s.clone()));
        hpke::setup_sender::<hpke::aead::ChaCha20Poly1305, hpke::kdf::HkdfSha256, XWing>(&mode, &pk_r, b"probe").map(|_| ())
    });
    let _ = std::panic::take_hook();
    let outcome = match r {
        Ok(Ok(())) => json!({"outcome": "succeeded (unexpected)"}),
        Ok(Err(e)) => json!({"outcome": "error", "error": e.to_string()}),
        Err(p) => json!({"outcome": "panic", "message": p.downcast_ref::<&str>().map(|s| s.to_string()).or_else(|| p.downcast_ref::<String>().cloned())}),
    };
    println!("{outcome}");
}

fn main() {
    let (cmd, a) = Args::parse();
    match cmd.as_str() {
        "start" => cmd_start(&a),
        "resume" => cmd_resume(&a),
        "complete" => cmd_complete(&a),
        "abort" => cmd_abort(&a),
        "dedup-hit" => cmd_dedup_hit(&a),
        "regen-all" => cmd_regen_all(&a),
        "check-receipt" => cmd_check_receipt(&a),
        "ingest" => cmd_ingest(&a),
        "chunk" => cmd_chunk(&a),
        "keygen-sign" => cmd_keygen_sign(&a),
        "keygen" => cmd_keygen(&a),
        "recipient" => cmd_recipient(&a),
        "make-trust" => cmd_make_trust(&a),
        "sign-meta" => cmd_sign_meta(&a),
        "encrypt" => cmd_encrypt(&a),
        "decrypt" => cmd_decrypt(&a),
        "inspect" => cmd_inspect(&a),
        "debug-keys" => cmd_debug_keys(&a),
        "cctv" => cmd_cctv(&a),
        "bench" => cmd_bench(&a),
        "bench-kem" => cmd_bench_kem(&a),
        "bench-obj" => cmd_bench_obj(&a),
        "hpke-auth-probe" => cmd_hpke_auth_probe(&a),
        "soak" => cmd_soak(&a),
        _ => die(2, "usage: start|resume|complete|abort|dedup-hit|regen-all|check-receipt|ingest|chunk|keygen-sign|keygen|recipient|make-trust|sign-meta|encrypt|decrypt|inspect|cctv|bench|bench-kem|bench-obj|hpke-auth-probe"),
    }
}
