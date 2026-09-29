//! THROWAWAY SPIKE CODE. Not production. See README.md.
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
mod meta;

use base64::{engine::general_purpose::STANDARD as B64P, Engine};
use engine::*;
use format::*;
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
        self.f.write_all(b).unwrap();
        self.f.flush().unwrap();
        self.h.update(b);
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

/// Builds the signed, padded, encrypted metadata record. `content` is
/// (object_key, header_mac) when this device uploads the content object and
/// None for a dedup hit.
fn build_meta(trust: &Trust, sk: &ed25519_dalek::SigningKey, device_id: &str, hr: &HashResult, content: Option<(&str, &str)>, path: &Path) -> Vec<u8> {
    let body = json!({
        "v": 1,
        "type": "reliquary.file-meta",
        "device_id": device_id,
        "dedup_id": hex::encode(hr.dedup_id),
        "sha256": hex::encode(hr.sha256),
        "size": hr.snapshot.size,
        "content_object": content.map(|(k, mac)| json!({"key": k, "header_mac": mac})),
        "source_locator": format!("file://{}", path.display()),
        "path": path.parent().map(|p| p.to_string_lossy().to_string()),
        "name": path.file_name().map(|p| p.to_string_lossy().to_string()),
        "mtime_ns": hr.snapshot.mtime_ns,
        "ctime_ns": hr.snapshot.ctime_ns,
        "file_id": hr.snapshot.file_id,
        "recorded_at": now_secs(),
    });
    let pt = pad_meta(sign_lines(META_DOMAIN, device_id, &body, sk));
    encrypt_small(&trust.recipient, &pt)
}

/// After the content is in R2 (or was a dedup hit): persist the non-secret
/// "awaiting commit" record, upload the metadata record. Nothing here can
/// decrypt anything.
fn finish_pending(d: &Dirs, id: &str, device_id: &str, dedup_id: &str, sha: &str, size: u64, object_key: Option<&str>, source: &str, snap: &Snapshot) -> Value {
    let meta_local = d.meta_file(id);
    let meta_ct = fs::read(&meta_local).unwrap_or_else(|e| die(74, &format!("metadata record: {e}")));
    let meta_key = format!("meta/{device_id}/{}.age", rand_hex(16)); // no dedup_id in the key
    let pending = json!({
        "v": 1, "status": "awaiting_commit", "device_id": device_id, "dedup_id": dedup_id,
        "sha256": sha, "size": size, "object_key": object_key, "meta_key": meta_key,
        "meta_sha256": hex::encode(sha256(&meta_ct)), "meta_file": meta_local.to_string_lossy(),
        "source_path": source, "snapshot": snap,
    });
    write_atomic(&d.pending_file(id), serde_json::to_vec_pretty(&pending).unwrap().as_slice()).unwrap();
    let mp = d.r2.join(&meta_key);
    fs::create_dir_all(mp.parent().unwrap()).unwrap();
    fs::write(&mp, &meta_ct).unwrap(); // simulated single PUT of the metadata record
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
    let layout = match a.n::<u64>("chunks-per-part") {
        Some(k) => Layout { pt_len: size, chunks_per_part: k, prefix_len: PREFIX_LEN_X25519 }, // TEST-ONLY override
        None => Layout::policy(size, PREFIX_LEN_X25519).unwrap_or_else(|e| die(2, &e)),
    };
    if layout.num_parts() > R2_MAX_PARTS {
        die(2, "too many parts");
    }
    // (Production: send dedup_id to the Worker; continue only if it is missing
    //  and this device won the claim; receive R2 UploadId + presigned URLs.)
    let (prefix, mut pk) = new_header(&trust.recipient, &hr.sha256);
    let id = rand_hex(16);
    let dedup_hex = hex::encode(hr.dedup_id);
    let sha_hex = hex::encode(hr.sha256);
    let object_key = format!("staging/{dedup_hex}/{id}");
    let mac = header_mac_b64(&prefix).unwrap();
    let meta_ct = build_meta(&trust, &dev_sk, &device_id, &hr, Some((&object_key, &mac)), &file);
    write_atomic(&d.meta_file(&id), &meta_ct).unwrap();
    let mode = if layout.num_parts() == 1 { "put" } else { "multipart" };
    eprintln!(
        "UPLOAD {}",
        json!({"upload_id": id, "object_key": object_key, "mode": mode, "pt_len": size, "ct_len": layout.ct_len(),
               "part_size": layout.part_size(), "num_parts": layout.num_parts(), "sha256": sha_hex, "dedup_id": dedup_hex})
    );
    let src_path = file.to_string_lossy().to_string();

    if mode == "put" {
        // Single PUT, no resume state: an interrupted PUT is retried from
        // scratch with fresh randomness (a different key), so no keystream is
        // ever reused and nothing secret is persisted.
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
        let mut v = json!({"mode": "put", "upload_id": id, "object_key": object_key, "object": d.r2.join(&object_key).join("object"), "generated_parts": [1], "num_parts": 1});
        merge(&mut v, finish_pending(&d, &id, &device_id, &dedup_hex, &sha_hex, size, Some(&object_key), &src_path, &hr.snapshot));
        merge(&mut v, resource_json());
        println!("{v}");
        return;
    }

    let _lock = lock_upload(&d.state, &id).unwrap_or_else(|e| die(73, &e));
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
        meta_file: d.meta_file(&id).to_string_lossy().into(),
        meta_sha256: hex::encode(sha256(&meta_ct)),
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

/// Simulated CompleteMultipartUpload, then local cleanup: the key entry,
/// sealed state and journal are deleted; the non-secret pending record and the
/// metadata record stay until a valid commit receipt arrives.
fn cmd_complete(a: &Args) {
    let d = Dirs::from(a);
    let id = a.s("upload-id");
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
    let mut v = json!({"object": objp, "object_len": l.ct_len(), "object_key": st.object_key, "upload_id": id});
    merge(&mut v, finish_pending(&d, &id, &st.device_id, &st.dedup_id, &st.sha256, l.pt_len, Some(&st.object_key), &st.source_path, &st.snapshot));
    d.ks.delete(&id).unwrap();
    remove_if_exists(&d.state_file(&id)).unwrap();
    remove_if_exists(&d.journal_file(&id)).unwrap();
    let _ = fs::remove_file(d.state.join(format!("{id}.lock")));
    println!("{v}");
}

/// AbortMultipartUpload + forget everything for this upload. The next attempt
/// starts at pass 1 with a fresh key.
fn cmd_abort(a: &Args) {
    let d = Dirs::from(a);
    let id = a.s("upload-id");
    let _lock = lock_upload(&d.state, &id).unwrap_or_else(|e| die(73, &e));
    if let Ok(st) = open_state(&d.ks, &d.state_file(&id)) {
        let dir = d.r2.join(&st.object_key);
        for e in fs::read_dir(&dir).into_iter().flatten().flatten() {
            if e.file_name().to_string_lossy().starts_with("part-") {
                let _ = fs::remove_file(e.path()); // R2 discards parts; attempts/ keeps the audit log
            }
        }
    }
    d.ks.delete(&id).unwrap();
    for p in [d.state_file(&id), d.journal_file(&id), d.meta_file(&id), d.state.join(format!("{id}.lock"))] {
        remove_if_exists(&p).unwrap();
    }
    println!("{}", json!({"aborted": id}));
}

/// Dedup hit: the Worker says the content is already present (with a valid
/// receipt). The device still sends its own signed metadata record, with no
/// content_object, and waits for its own receipt.
fn cmd_dedup_hit(a: &Args) {
    let d = Dirs::from(a);
    let trust = load_trust_args(a);
    let dev_sk = load_signing_key(&a.p("device-key")).unwrap_or_else(|e| die(2, &e));
    let device_id = a.s("device-id");
    let file = fs::canonicalize(a.p("file")).unwrap_or_else(|e| die(66, &e.to_string()));
    let dk = dedup_key(&hex::decode(a.s("family-secret")).unwrap());
    let hr = hash_pass(&file, &dk).unwrap_or_else(|e| die(69, &format!("{e:?}")));
    let id = rand_hex(16);
    write_atomic(&d.meta_file(&id), &build_meta(&trust, &dev_sk, &device_id, &hr, None, &file)).unwrap();
    let mut v = json!({"upload_id": id, "dedup_id": hex::encode(hr.dedup_id)});
    merge(&mut v, finish_pending(&d, &id, &device_id, &hex::encode(hr.dedup_id), &hex::encode(hr.sha256), hr.snapshot.size, None, &file.to_string_lossy(), &hr.snapshot));
    println!("{v}");
}

/// Regenerates the entire object from persisted state; every chunk tag is
/// checked against the journal (determinism check).
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

/// Device: verify a commit receipt against the pinned homelab receipt key.
/// Only then is the file "protected"; --consume deletes the pending record.
fn cmd_check_receipt(a: &Args) {
    let trust = load_trust_args(a);
    let pend: Value = serde_json::from_slice(&fs::read(a.p("pending")).unwrap_or_else(|e| die(12, &e.to_string()))).unwrap();
    let raw = fs::read(a.p("receipt")).unwrap_or_else(|e| die(12, &e.to_string()));
    let (body, _) = verify_lines(RECEIPT_DOMAIN, &raw, &|_| Some(trust.receipt_key)).unwrap_or_else(|e| die(12, &format!("RECEIPT INVALID: {e}")));
    let content_only = a.flag("content-only");
    let mut checks = vec![("type", body["type"] == "reliquary.commit-receipt"), ("dedup_id", body["dedup_id"] == pend["dedup_id"]), ("size", body["size"] == pend["size"])];
    if !content_only {
        checks.push(("device_id", body["device_id"] == pend["device_id"]));
        checks.push(("meta_sha256", body["meta_sha256"] == pend["meta_sha256"]));
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

fn identity_arg(a: &Args) -> age::x25519::Identity {
    fs::read_to_string(a.p("identity")).unwrap().lines().find(|l| l.starts_with("AGE-SECRET")).unwrap().parse().unwrap()
}

fn age_decrypt_to(id: &age::x25519::Identity, input: impl Read, mut sink: impl FnMut(&[u8]) -> io::Result<()>) -> Result<u64, String> {
    let dec = age::Decryptor::new(io::BufReader::new(input)).map_err(|e| e.to_string())?;
    let mut r = dec.decrypt(std::iter::once(id as &dyn age::Identity)).map_err(|e| e.to_string())?;
    let mut buf = vec![0u8; 1 << 16];
    let mut n = 0u64;
    loop {
        let k = r.read(&mut buf).map_err(|e| e.to_string())?;
        if k == 0 {
            return Ok(n);
        }
        sink(&buf[..k]).map_err(|e| e.to_string())?;
        n += k as u64;
    }
}

/// Homelab ingest. Nothing is committed, catalogued or acknowledged until the
/// whole object has been decrypted (final chunk authenticated) and the size,
/// SHA-256 and dedup HMAC match the device-signed metadata record.
fn cmd_ingest(a: &Args) {
    // Temp files (concatenated bundle, decrypted plaintext) are removed on every rejection.
    let temps: std::cell::RefCell<Vec<PathBuf>> = Default::default();
    let reject = |m: &str| -> ! {
        for t in temps.borrow().iter() {
            let _ = fs::remove_file(t);
        }
        die(10, &format!("INGEST REJECTED: {m}"))
    };
    let id = identity_arg(a);
    let dk = dedup_key(&hex::decode(a.s("family-secret")).unwrap());
    let registry: HashMap<String, String> = serde_json::from_slice(&fs::read(a.p("registry")).unwrap()).unwrap();
    let receipt_sk = load_signing_key(&a.p("receipt-key")).unwrap_or_else(|e| die(2, &e));
    let store = a.p("store");
    for sub in ["tmp", "objects", "by-dedup"] {
        fs::create_dir_all(store.join(sub)).unwrap();
    }
    // 1. metadata record: decrypt (age crate), verify device signature
    let meta_ct = fs::read(a.p("meta")).unwrap();
    if meta_ct.len() > 1 << 20 {
        reject("metadata record too large");
    }
    let mut meta_pt = vec![];
    age_decrypt_to(&id, meta_ct.as_slice(), |b| {
        meta_pt.extend_from_slice(b);
        Ok(())
    })
    .unwrap_or_else(|e| reject(&format!("metadata decrypt: {e}")));
    let lookup = |k: &str| registry.get(k).and_then(|s| parse_pk_b64(s).ok());
    let (rec, key_id) = verify_lines(META_DOMAIN, &meta_pt, &lookup).unwrap_or_else(|e| reject(&format!("metadata record: {e}")));
    if rec["device_id"] != key_id.as_str() || rec["type"] != "reliquary.file-meta" {
        reject("metadata device_id does not match its signing key");
    }
    let size = rec["size"].as_u64().unwrap_or_else(|| reject("size"));
    let want_sha = rec["sha256"].as_str().unwrap_or_else(|| reject("sha256")).to_string();
    let want_dedup = rec["dedup_id"].as_str().unwrap_or_else(|| reject("dedup_id")).to_string();
    if want_dedup.len() != 64 || !want_dedup.bytes().all(|b| b.is_ascii_hexdigit()) {
        reject("dedup_id format");
    }

    // 2. content
    let by_dedup = store.join("by-dedup").join(&want_dedup);
    if rec["content_object"].is_object() {
        let obj_path = if let Some(p) = a.o("object") {
            PathBuf::from(p)
        } else {
            // USB bundle / staged parts: the object split at part boundaries
            let t = store.join("tmp").join(format!("{}.age", rand_hex(8)));
            temps.borrow_mut().push(t.clone());
            let mut o = File::create(&t).unwrap();
            let mut names: Vec<_> = fs::read_dir(a.p("parts")).unwrap().flatten().map(|e| e.file_name().to_string_lossy().to_string()).filter(|n| n.starts_with("part-")).collect();
            names.sort();
            for n in names {
                io::copy(&mut File::open(a.p("parts").join(n)).unwrap(), &mut o).unwrap();
            }
            t
        };
        let obj_len = fs::metadata(&obj_path).unwrap().len();
        match Layout::pt_len_from_ct_len(obj_len, PREFIX_LEN_X25519) {
            Ok(n) if n == size => {}
            Ok(n) => reject(&format!("object length implies {n} plaintext bytes, record says {size}")),
            Err(e) => reject(&e),
        }
        let mut prefix = vec![0u8; PREFIX_LEN_X25519 as usize];
        File::open(&obj_path).unwrap().read_exact(&mut prefix).unwrap();
        if header_mac_b64(&prefix).ok().as_deref() != rec["content_object"]["header_mac"].as_str() {
            reject("object header MAC does not match the metadata record");
        }
        let tmp_plain = store.join("tmp").join(format!("{}.plain", rand_hex(8)));
        temps.borrow_mut().push(tmp_plain.clone());
        let mut out = File::create(&tmp_plain).unwrap();
        let mut sha = Sha256::new();
        let mut hm = <hmac::Hmac<Sha256> as hmac::KeyInit>::new_from_slice(&dk).unwrap();
        let n = age_decrypt_to(&id, File::open(&obj_path).unwrap(), |b| {
            sha.update(b);
            hmac::Mac::update(&mut hm, b);
            out.write_all(b)
        })
        .unwrap_or_else(|e| reject(&format!("content decrypt: {e}")));
        let got_sha = hex::encode(sha.finalize());
        let got_dedup = hex::encode(hmac::Mac::finalize(hm).into_bytes());
        if n != size || got_sha != want_sha || got_dedup != want_dedup {
            reject(&format!("content mismatch (size {n}/{size}, sha256 ok={}, dedup_id ok={})", got_sha == want_sha, got_dedup == want_dedup));
        }
        out.sync_all().unwrap();
        let dest = store.join("objects").join(&got_sha);
        if !dest.exists() {
            fs::rename(&tmp_plain, &dest).unwrap(); // atomic commit; an existing copy wins
        }
        write_atomic(&by_dedup, format!("{got_sha} {n}").as_bytes()).unwrap();
        for t in temps.borrow().iter() {
            let _ = fs::remove_file(t);
        }
    } else {
        match fs::read_to_string(&by_dedup) {
            Ok(s) if s == format!("{want_sha} {size}") => {}
            Ok(_) => reject("dedup record does not match committed content"),
            Err(_) => die(11, "INGEST PENDING: content for this dedup_id is not committed yet"),
        }
    }
    // 3. catalog + receipt
    let meta_sha = hex::encode(sha256(&meta_ct));
    let mut cat = OpenOptions::new().create(true).append(true).open(store.join("catalog.jsonl")).unwrap();
    writeln!(cat, "{}", json!({"record": rec, "meta_sha256": meta_sha})).unwrap();
    cat.sync_all().unwrap();
    let body = json!({"v": 1, "type": "reliquary.commit-receipt", "dedup_id": want_dedup, "size": size,
                      "device_id": rec["device_id"], "meta_sha256": meta_sha, "committed_at": now_secs()});
    fs::write(a.p("out"), sign_lines(RECEIPT_DOMAIN, "homelab-receipt-1", &body, &receipt_sk)).unwrap();
    println!("{}", json!({"committed": true, "sha256": want_sha, "dedup_id": want_dedup}));
}

/// Homelab reference random access: read ONLY the prefix, the final chunk and
/// chunk i (HTTP Range reads in production). The object length is validated
/// and the final chunk authenticated first, so a truncated object is rejected
/// even when chunk i itself is intact.
fn cmd_chunk(a: &Args) {
    let id = parse_identity_file(&fs::read_to_string(a.p("identity")).unwrap()).unwrap();
    let mut f = File::open(a.p("object")).unwrap();
    let obj_len = f.metadata().unwrap().len();
    let pt_len = Layout::pt_len_from_ct_len(obj_len, PREFIX_LEN_X25519).unwrap_or_else(|e| die(2, &e));
    if let Some(want) = a.n::<u64>("expect-size") {
        if want != pt_len {
            die(2, &format!("object length implies {pt_len} bytes, catalog says {want}"));
        }
    }
    let mut prefix = vec![0u8; PREFIX_LEN_X25519 as usize];
    f.read_exact(&mut prefix).unwrap();
    let pk = open_prefix(&prefix, &id).unwrap_or_else(|e| die(2, &e));
    let layout = Layout { pt_len, chunks_per_part: 1, prefix_len: PREFIX_LEN_X25519 };
    let cipher = PayloadCipher::new(&pk, layout.n_chunks());
    let read_chunk = |f: &mut File, c: u64| -> Vec<u8> {
        let (s, e) = layout.chunk_obj_range(c);
        let mut buf = vec![0u8; (e - s) as usize];
        f.seek(SeekFrom::Start(s)).unwrap();
        f.read_exact(&mut buf).unwrap();
        buf
    };
    let last = layout.n_chunks() - 1;
    let mut fin = read_chunk(&mut f, last);
    cipher.decrypt_chunk(last, &mut fin).unwrap_or_else(|e| die(2, &format!("final chunk: {e} (truncated or tampered object)")));
    let i: u64 = a.n("index").unwrap_or_else(|| die(2, "missing --index"));
    if i > last {
        die(2, "chunk index out of range");
    }
    let mut buf = read_chunk(&mut f, i);
    cipher.decrypt_chunk(i, &mut buf).unwrap_or_else(|e| die(2, &e));
    fs::write(a.p("out"), &buf).unwrap();
}

/// Independent Rust decryptor: the `age` crate (0.11.5), with Seek.
fn cmd_age_crate(a: &Args) {
    let id = identity_arg(a);
    let f = File::open(a.p("object")).unwrap();
    let dec = age::Decryptor::new(f).unwrap_or_else(|e| die(2, &e.to_string()));
    let mut r = dec.decrypt(std::iter::once(&id as &dyn age::Identity)).unwrap_or_else(|e| die(2, &e.to_string()));
    let mut out = vec![];
    if let Some(off) = a.n::<u64>("offset") {
        r.seek(SeekFrom::Start(off)).unwrap_or_else(|e| die(2, &e.to_string()));
        out.resize(a.n("len").unwrap(), 0);
        r.read_exact(&mut out).unwrap_or_else(|e| die(2, &e.to_string()));
    } else {
        r.read_to_end(&mut out).unwrap_or_else(|e| die(2, &e.to_string()));
    }
    fs::write(a.p("out"), &out).unwrap();
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

fn cmd_make_trust(a: &Args) {
    let tb = TrustBundle { v: 1, recipient: fs::read_to_string(a.p("recipient-file")).unwrap().trim().to_string(), receipt_key: a.s("receipt-pub") };
    let bytes = serde_json::to_vec(&tb).unwrap();
    fs::write(a.p("out"), &bytes).unwrap();
    println!("{}", json!({"pin": hex::encode(sha256(&bytes))}));
}

/// TEST-ONLY adversary tool: a registered-but-malicious device signs an
/// arbitrary metadata body (e.g. claiming someone else's dedup_id).
fn cmd_sign_meta(a: &Args) {
    let trust = load_trust_args(a);
    let sk = load_signing_key(&a.p("device-key")).unwrap();
    let body: Value = serde_json::from_slice(&fs::read(a.p("body")).unwrap()).unwrap();
    let pt = pad_meta(sign_lines(META_DOMAIN, &a.s("key-id"), &body, &sk));
    fs::write(a.p("out"), encrypt_small(&trust.recipient, &pt)).unwrap();
}

// ------------------------------------------------------------ benchmark

fn mbps(bytes: u64, secs: f64) -> String {
    format!("{:.0} MB/s", bytes as f64 / secs / 1e6)
}

fn cmd_bench(a: &Args) {
    use chacha20poly1305::aead::{AeadInOut, KeyInit};
    use hmac::Mac;
    let file = a.p("file");
    let size = fs::metadata(&file).unwrap().len();
    let layout = Layout::policy(size, PREFIX_LEN_X25519).unwrap();
    let dk = [7u8; 32];
    let mut v = vec![];
    File::open(&file).unwrap().read_to_end(&mut v).unwrap(); // warm page cache
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
    let t = best(&mut || {
        std::hint::black_box(Sha256::digest(&v));
    });
    res.insert("sha256_only_mem".into(), mbps(size, t).into());
    let t = best(&mut || {
        let mut m = <hmac::Hmac<Sha256> as hmac::KeyInit>::new_from_slice(&dk).unwrap();
        m.update(&v);
        std::hint::black_box(m.finalize());
    });
    res.insert("hmac_sha256_only_mem".into(), mbps(size, t).into());
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
    let recipient = {
        let sk = x25519_dalek::StaticSecret::random_from_rng(OsRng);
        *x25519_dalek::PublicKey::from(&sk).as_bytes()
    };
    let (prefix, pk) = new_header(&recipient, &hr.sha256);
    let t = best(&mut || {
        let mut src = RandomSource::open(&file).unwrap();
        let mut g = Generator::new(layout, &prefix, &pk, &mut src);
        let mut j = Journal::memory();
        let mut out = Vec::new();
        for p in 0..layout.num_parts() {
            let (s, e) = layout.part_range(p);
            g.gen_range(&mut j, s, e, &mut out).unwrap();
            std::hint::black_box(&out);
        }
    });
    res.insert("pass2_encrypt+tag_journal_file".into(), mbps(size, t).into());
    let t = best(&mut || {
        let aead = chacha20poly1305::ChaCha20Poly1305::new(&[1u8; 32].into());
        let mut sha = Sha256::new();
        let mut m = <hmac::Hmac<Sha256> as hmac::KeyInit>::new_from_slice(&dk).unwrap();
        let mut buf = Vec::with_capacity(CHUNK_CT as usize);
        for (i, c) in v.chunks(CHUNK_PT as usize).enumerate() {
            sha.update(c);
            m.update(c);
            buf.clear();
            buf.extend_from_slice(c);
            aead.encrypt_in_place(&chunk_nonce(i as u64, false).into(), b"", &mut buf).unwrap();
            std::hint::black_box(&buf);
        }
        std::hint::black_box((sha.finalize(), m.finalize()));
    });
    res.insert("fused_sha256+hmac+chacha_mem".into(), mbps(size, t).into());
    res.insert("bytes".into(), size.into());
    res.insert("num_parts".into(), layout.num_parts().into());
    println!("{}", serde_json::to_string_pretty(&res).unwrap());
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
        "age-crate" => cmd_age_crate(&a),
        "keygen-sign" => cmd_keygen_sign(&a),
        "make-trust" => cmd_make_trust(&a),
        "sign-meta" => cmd_sign_meta(&a),
        "bench" => cmd_bench(&a),
        _ => die(2, "usage: start|resume|complete|abort|dedup-hit|regen-all|check-receipt|ingest|chunk|age-crate|keygen-sign|make-trust|sign-meta|bench"),
    }
}
