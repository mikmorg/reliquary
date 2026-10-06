//! THROWAWAY SPIKE B4-S1. Not production code.
//!
//! The shape of a Rust core API that an iOS Swift shell can drive through UniFFI:
//! - forward-only plaintext sources implemented in Swift (PhotoKit `requestData` style);
//! - pre-encrypted part files written to a bounded spool, handed to a background
//!   URLSession as files (`uploadTask(with:fromFile:)`);
//! - short, cancellable work units (cancel flag checked per 64 KiB chunk);
//! - all resumable state in SQLite, so a relaunched process can apply task results;
//! - asset-identifier source locators instead of paths.
//!
//! The encryption is a STAND-IN (ChaCha20-Poly1305 per 64 KiB chunk with a counter
//! nonce, age-STREAM-like), used only so that parts are real ciphertext and a
//! regenerated part is byte-identical. The real object format is T1 spike 2 /
//! ADR-0007. The payload key sits in the DB here; the real design seals it with a
//! Keychain / Secure Enclave key.

use std::fs;
use std::io::Write;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::time::Instant;

use chacha20poly1305::{
    aead::{AeadInOut, KeyInit},
    ChaCha20Poly1305, Key, Nonce,
};
use md5::Md5;
use rand::{rngs::OsRng, RngCore};
use rusqlite::{params, Connection, OptionalExtension};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

uniffi::setup_scaffolding!();

pub const CHUNK_PT: u64 = 65_536;
pub const TAG_LEN: u64 = 16;

// ---------------------------------------------------------------- errors

#[derive(Debug, uniffi::Error)]
pub enum CoreError {
    Io { msg: String },
    Db { msg: String },
    /// The source no longer matches what was planned (size or bytes of an
    /// already-produced part). The upload must restart as a new upload.
    SourceChanged { msg: String },
    NotFound { msg: String },
    /// Error raised by a foreign (Swift) implementation.
    Source { msg: String },
}

impl std::fmt::Display for CoreError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{self:?}")
    }
}
impl std::error::Error for CoreError {}

impl From<uniffi::UnexpectedUniFFICallbackError> for CoreError {
    fn from(e: uniffi::UnexpectedUniFFICallbackError) -> Self {
        CoreError::Source { msg: e.reason }
    }
}
impl From<rusqlite::Error> for CoreError {
    fn from(e: rusqlite::Error) -> Self {
        CoreError::Db { msg: e.to_string() }
    }
}
impl From<std::io::Error> for CoreError {
    fn from(e: std::io::Error) -> Self {
        CoreError::Io { msg: e.to_string() }
    }
}

// ---------------------------------------------------------------- records

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, uniffi::Enum)]
pub enum LocatorKind {
    /// Desktop / Android file path (raw bytes kept in `raw_path`).
    FilePath,
    /// iOS PhotoKit: PHAsset.localIdentifier + PHAssetResource role.
    PhotoKitResource,
}

/// Generic source locator (ADR-0001: on iOS it is an asset identifier plus a
/// modification date, not a path).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, uniffi::Record)]
pub struct SourceLocator {
    pub kind: LocatorKind,
    /// Display path, or PHAsset.localIdentifier (valid on this device only).
    pub local_identifier: String,
    /// PHCloudIdentifier string when iCloud Photos is on (cross-device), if known.
    pub cloud_identifier: Option<String>,
    /// e.g. "photo", "pairedVideo", "fullSizePhoto", "adjustmentData"; "file" on desktop.
    pub resource_role: String,
    /// iOS: PHAsset.modificationDate; desktop: size/mtime/file-id snapshot.
    pub content_version: String,
    /// Lossless raw path bytes on desktop; None on iOS.
    pub raw_path: Option<Vec<u8>>,
}

#[derive(Debug, Clone, uniffi::Record)]
pub struct PartTicket {
    pub upload_id: String,
    /// 1-based, as in S3/R2 multipart.
    pub part_number: u32,
    /// Absolute path of the ciphertext part file to hand to uploadTask(fromFile:).
    pub file_path: String,
    pub byte_len: u64,
    /// MD5 of the ciphertext part (hex). S3 part ETags are the MD5; whether R2
    /// matches is an open T1 question, so the shell must not rely on it alone.
    pub ciphertext_md5_hex: String,
}

#[derive(Debug, Clone, uniffi::Record)]
pub struct ProduceReport {
    pub tickets: Vec<PartTicket>,
    pub source_bytes_read: u64,
    pub cancelled: bool,
    pub spool_bytes_after: u64,
    pub parts_remaining: u32,
    pub elapsed_ms: u64,
}

#[derive(Debug, Clone, PartialEq, uniffi::Enum)]
pub enum TaskOutcome {
    Recorded,
    Duplicate,
    UnknownTask,
    Failed { attempts: u32, reason: String },
}

#[derive(Debug, Clone, uniffi::Record)]
pub struct UploadStatus {
    pub upload_id: String,
    pub n_parts: u32,
    pub uploaded: u32,
    pub enqueued: u32,
    pub spooled: u32,
    pub missing: u32,
    pub not_started: u32,
    pub complete: bool,
}

// ---------------------------------------------------------------- foreign traits

/// Forward-only plaintext source implemented by the platform shell.
/// iOS: wraps PHAssetResourceManager.requestData (push) behind a bounded queue,
/// or a FileHandle on an AVURLAsset / writeData(toFile:) copy.
#[uniffi::export(with_foreign)]
pub trait PlaintextSource: Send + Sync {
    /// Returns the next bytes (at most `max_len`). An empty vector means EOF.
    fn read(&self, max_len: u32) -> Result<Vec<u8>, CoreError>;
}

/// Progress callback. BGContinuedProcessingTask needs frequent progress reports.
#[uniffi::export(with_foreign)]
pub trait ProgressSink: Send + Sync {
    fn on_progress(&self, source_bytes_read: u64, parts_ready: u32);
}

// ---------------------------------------------------------------- cancel token

/// UniFFI has no built-in cancellation; the manual recommends a library flag.
/// Swift calls `cancel()` from BGTask.expirationHandler / willTerminate().
#[derive(Debug, Default, uniffi::Object)]
pub struct CancelToken {
    flag: AtomicBool,
}

#[uniffi::export]
impl CancelToken {
    #[uniffi::constructor]
    pub fn new() -> Arc<Self> {
        Arc::new(Self::default())
    }
    pub fn cancel(&self) {
        self.flag.store(true, Ordering::SeqCst);
    }
    pub fn is_cancelled(&self) -> bool {
        self.flag.load(Ordering::SeqCst)
    }
}

// ---------------------------------------------------------------- core

#[derive(uniffi::Object)]
pub struct Core {
    db: Mutex<Connection>,
    spool: PathBuf,
    spool_budget: u64,
    chunks_per_part: u64,
}

struct UploadRow {
    size: u64,
    n_parts: u32,
    key: [u8; 32],
}

fn ct_len_for(pt_len: u64) -> u64 {
    // one tag per chunk; an empty final chunk still carries a tag
    let chunks = if pt_len == 0 { 1 } else { pt_len.div_ceil(CHUNK_PT) };
    pt_len + chunks * TAG_LEN
}

fn sync_dir(p: &Path) {
    if let Ok(d) = fs::File::open(p) {
        let _ = d.sync_all();
    }
}

impl Core {
    fn part_pt(&self) -> u64 {
        self.chunks_per_part * CHUNK_PT
    }
    fn part_path(&self, upload_id: &str, part: u32) -> PathBuf {
        self.spool.join(format!("{upload_id}.{part:05}.part"))
    }
    fn load_upload(&self, c: &Connection, upload_id: &str) -> Result<UploadRow, CoreError> {
        let r = c
            .query_row(
                "SELECT size, n_parts, key FROM uploads WHERE upload_id=?1",
                params![upload_id],
                |r| {
                    let k: Vec<u8> = r.get(2)?;
                    Ok((r.get::<_, i64>(0)?, r.get::<_, i64>(1)?, k))
                },
            )
            .optional()?
            .ok_or(CoreError::NotFound { msg: upload_id.to_string() })?;
        let mut key = [0u8; 32];
        key.copy_from_slice(&r.2);
        Ok(UploadRow { size: r.0 as u64, n_parts: r.1 as u32, key })
    }
    fn spool_used(c: &Connection) -> Result<u64, CoreError> {
        Ok(c.query_row(
            "SELECT COALESCE(SUM(ct_len),0) FROM parts WHERE state IN ('spooled','enqueued')",
            [],
            |r| r.get::<_, i64>(0),
        )? as u64)
    }
    /// Startup reconciliation between the spool directory and the DB.
    fn reconcile_spool(&self) -> Result<(), CoreError> {
        let c = self.db.lock().unwrap();
        // 1. torn writes from a killed process
        for e in fs::read_dir(&self.spool)? {
            let p = e?.path();
            let name = p.file_name().unwrap().to_string_lossy().to_string();
            if name.ends_with(".tmp") {
                fs::remove_file(&p)?;
            } else if name.ends_with(".part") {
                let known: i64 = c.query_row(
                    "SELECT COUNT(*) FROM parts WHERE spool_path=?1 AND state IN ('spooled','enqueued')",
                    params![p.to_string_lossy()],
                    |r| r.get(0),
                )?;
                if known == 0 {
                    fs::remove_file(&p)?; // renamed but never committed, or already uploaded
                }
            }
        }
        // 2. rows whose file vanished (e.g. purged spool) must be regenerated
        let mut st = c.prepare("SELECT upload_id, part_no, spool_path FROM parts WHERE state IN ('spooled','enqueued')")?;
        let rows: Vec<(String, i64, String)> =
            st.query_map([], |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?)))?.collect::<Result<_, _>>()?;
        for (u, p, path) in rows {
            if !Path::new(&path).exists() {
                c.execute("UPDATE parts SET state='missing' WHERE upload_id=?1 AND part_no=?2", params![u, p])?;
            }
        }
        Ok(())
    }
}

#[uniffi::export]
impl Core {
    #[uniffi::constructor]
    pub fn open(
        db_path: String,
        spool_dir: String,
        spool_budget_bytes: u64,
        chunks_per_part: u32,
    ) -> Result<Arc<Self>, CoreError> {
        fs::create_dir_all(&spool_dir)?;
        let c = Connection::open(&db_path)?;
        c.execute_batch(
            "PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL;
             CREATE TABLE IF NOT EXISTS uploads(
               upload_id TEXT PRIMARY KEY, locator_json TEXT NOT NULL, size INTEGER NOT NULL,
               n_parts INTEGER NOT NULL, chunks_per_part INTEGER NOT NULL, key BLOB NOT NULL,
               created_ms INTEGER NOT NULL) STRICT;
             CREATE TABLE IF NOT EXISTS parts(
               upload_id TEXT NOT NULL, part_no INTEGER NOT NULL,
               state TEXT NOT NULL CHECK(state IN ('spooled','enqueued','uploaded','missing')),
               spool_path TEXT NOT NULL, ct_len INTEGER NOT NULL, pt_sha256 TEXT NOT NULL,
               ct_md5 TEXT NOT NULL, etag TEXT, attempts INTEGER NOT NULL DEFAULT 0,
               PRIMARY KEY(upload_id, part_no)) STRICT;
             CREATE TABLE IF NOT EXISTS tasks(
               session_id TEXT NOT NULL, task_id INTEGER NOT NULL, upload_id TEXT NOT NULL,
               part_no INTEGER NOT NULL,
               state TEXT NOT NULL CHECK(state IN ('inflight','done','orphaned')),
               PRIMARY KEY(session_id, task_id)) STRICT;",
        )?;
        let core = Arc::new(Core {
            db: Mutex::new(c),
            spool: PathBuf::from(spool_dir),
            spool_budget: spool_budget_bytes,
            chunks_per_part: chunks_per_part as u64,
        });
        core.reconcile_spool()?;
        Ok(core)
    }

    pub fn find_upload(&self, locator: SourceLocator) -> Result<Option<String>, CoreError> {
        let c = self.db.lock().unwrap();
        let j = serde_json::to_string(&locator).unwrap();
        Ok(c.query_row("SELECT upload_id FROM uploads WHERE locator_json=?1", params![j], |r| r.get(0))
            .optional()?)
    }

    pub fn plan_upload(&self, locator: SourceLocator, plaintext_size: u64) -> Result<String, CoreError> {
        let mut id = [0u8; 8];
        OsRng.fill_bytes(&mut id);
        let upload_id = format!("up-{}", hex::encode(id));
        let mut key = [0u8; 32];
        OsRng.fill_bytes(&mut key);
        let n_parts = if plaintext_size == 0 { 1 } else { plaintext_size.div_ceil(self.part_pt()) };
        let c = self.db.lock().unwrap();
        c.execute(
            "INSERT INTO uploads VALUES(?1,?2,?3,?4,?5,?6,?7)",
            params![
                upload_id,
                serde_json::to_string(&locator).unwrap(),
                plaintext_size as i64,
                n_parts as i64,
                self.chunks_per_part as i64,
                key.to_vec(),
                std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_millis() as i64
            ],
        )?;
        Ok(upload_id)
    }

    /// One short work unit: stream the source forward once and write as many
    /// consecutive needed parts as the spool budget allows. Committed parts
    /// survive cancellation and process death; a part in progress does not.
    pub fn produce_parts(
        &self,
        upload_id: String,
        source: Arc<dyn PlaintextSource>,
        cancel: Arc<CancelToken>,
        progress: Arc<dyn ProgressSink>,
    ) -> Result<ProduceReport, CoreError> {
        let t0 = Instant::now();
        let (up, done_states, mut spool_used) = {
            let c = self.db.lock().unwrap();
            let up = self.load_upload(&c, &upload_id)?;
            let mut st = c.prepare("SELECT part_no, state, pt_sha256 FROM parts WHERE upload_id=?1")?;
            let v: Vec<(i64, String, String)> = st
                .query_map(params![upload_id], |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?)))?
                .collect::<Result<_, _>>()?;
            (up, v, Self::spool_used(&c)?)
        };
        let part_pt = self.part_pt();
        let pt_len_of = |p: u32| -> u64 {
            let start = (p as u64 - 1) * part_pt;
            part_pt.min(up.size.saturating_sub(start))
        };
        let prev_sha = |p: u32| done_states.iter().find(|r| r.0 as u32 == p).map(|r| (r.1.clone(), r.2.clone()));
        // choose targets: needed parts in ascending order within the spool budget
        let mut targets = Vec::new();
        for p in 1..=up.n_parts {
            let needed = match prev_sha(p) {
                None => true,
                Some((s, _)) => s == "missing",
            };
            if !needed {
                continue;
            }
            let len = ct_len_for(pt_len_of(p));
            if spool_used + len > self.spool_budget {
                break;
            }
            spool_used += len;
            targets.push(p);
        }
        let remaining_before = (1..=up.n_parts)
            .filter(|p| match prev_sha(*p) {
                None => true,
                Some((s, _)) => s == "missing",
            })
            .count() as u32;
        let mut report = ProduceReport {
            tickets: vec![],
            source_bytes_read: 0,
            cancelled: false,
            spool_bytes_after: 0,
            parts_remaining: remaining_before,
            elapsed_ms: 0,
        };
        let Some(&last) = targets.last() else {
            report.spool_bytes_after = Self::spool_used(&self.db.lock().unwrap())?;
            return Ok(report);
        };
        let aead = ChaCha20Poly1305::new(&Key::from(up.key));
        let total_chunks = if up.size == 0 { 1 } else { up.size.div_ceil(CHUNK_PT) };
        let mut pending: Vec<u8> = Vec::new(); // bytes read from source not yet consumed
        let mut read_exact = |want: usize, report: &mut ProduceReport| -> Result<Vec<u8>, CoreError> {
            while pending.len() < want {
                let b = source.read((want - pending.len()).min(CHUNK_PT as usize) as u32)?;
                if b.is_empty() {
                    return Err(CoreError::SourceChanged { msg: "source shorter than planned".into() });
                }
                report.source_bytes_read += b.len() as u64;
                pending.extend_from_slice(&b);
            }
            let rest = pending.split_off(want);
            Ok(std::mem::replace(&mut pending, rest))
        };

        'parts: for p in 1..=last {
            let plen = pt_len_of(p);
            let is_target = targets.contains(&p);
            let first_chunk = (p as u64 - 1) * self.chunks_per_part;
            let n_chunks = if plen == 0 { 1 } else { plen.div_ceil(CHUNK_PT) };
            let final_path = self.part_path(&upload_id, p);
            let tmp_path = final_path.with_extension("tmp");
            let mut out = if is_target { Some(fs::File::create(&tmp_path)?) } else { None };
            let mut pt_hash = Sha256::new();
            let mut ct_md5 = Md5::new();
            for i in 0..n_chunks {
                if cancel.is_cancelled() {
                    if out.is_some() {
                        drop(out.take());
                        let _ = fs::remove_file(&tmp_path);
                    }
                    report.cancelled = true;
                    break 'parts;
                }
                let clen = CHUNK_PT.min(plen - i * CHUNK_PT) as usize;
                let mut buf = read_exact(clen, &mut report)?;
                if let Some(f) = out.as_mut() {
                    pt_hash.update(&buf);
                    let idx = first_chunk + i;
                    let mut nonce = [0u8; 12];
                    nonce[3..11].copy_from_slice(&idx.to_be_bytes());
                    nonce[11] = (idx + 1 == total_chunks) as u8;
                    aead.encrypt_in_place(&Nonce::from(nonce), b"", &mut buf).expect("encrypt");
                    ct_md5.update(&buf);
                    f.write_all(&buf)?;
                }
                progress.on_progress(report.source_bytes_read, report.tickets.len() as u32);
            }
            if let Some(f) = out.take() {
                let sha = hex::encode(pt_hash.finalize());
                if let Some((_, prev)) = prev_sha(p) {
                    if prev != sha {
                        drop(f);
                        let _ = fs::remove_file(&tmp_path);
                        // same key + nonces over different plaintext would reuse keystream
                        return Err(CoreError::SourceChanged {
                            msg: format!("part {p} plaintext differs from the first production; refusing to re-encrypt"),
                        });
                    }
                }
                f.sync_all()?;
                drop(f);
                fs::rename(&tmp_path, &final_path)?;
                sync_dir(&self.spool);
                let md5 = hex::encode(ct_md5.finalize());
                let ct_len = ct_len_for(plen);
                let c = self.db.lock().unwrap();
                c.execute(
                    "INSERT INTO parts(upload_id,part_no,state,spool_path,ct_len,pt_sha256,ct_md5)
                     VALUES(?1,?2,'spooled',?3,?4,?5,?6)
                     ON CONFLICT(upload_id,part_no) DO UPDATE SET state='spooled', spool_path=?3, ct_md5=?6",
                    params![upload_id, p as i64, final_path.to_string_lossy(), ct_len as i64, sha, md5],
                )?;
                report.tickets.push(PartTicket {
                    upload_id: upload_id.clone(),
                    part_number: p,
                    file_path: final_path.to_string_lossy().to_string(),
                    byte_len: ct_len,
                    ciphertext_md5_hex: md5,
                });
                report.parts_remaining -= 1;
                progress.on_progress(report.source_bytes_read, report.tickets.len() as u32);
            }
        }
        if !report.cancelled && last == up.n_parts {
            // whole file consumed: it must end exactly here
            if !pending.is_empty() || !source.read(1)?.is_empty() {
                return Err(CoreError::SourceChanged { msg: "source longer than planned".into() });
            }
        }
        report.spool_bytes_after = Self::spool_used(&self.db.lock().unwrap())?;
        report.elapsed_ms = t0.elapsed().as_millis() as u64;
        Ok(report)
    }

    /// Parts that are spooled but not handed to the transfer service
    /// (never enqueued, failed, or orphaned by a force-quit).
    pub fn pending_handoffs(&self) -> Result<Vec<PartTicket>, CoreError> {
        let c = self.db.lock().unwrap();
        let mut st = c.prepare(
            "SELECT upload_id, part_no, spool_path, ct_len, ct_md5 FROM parts WHERE state='spooled' ORDER BY upload_id, part_no",
        )?;
        let v = st
            .query_map([], |r| {
                Ok(PartTicket {
                    upload_id: r.get(0)?,
                    part_number: r.get::<_, i64>(1)? as u32,
                    file_path: r.get(2)?,
                    byte_len: r.get::<_, i64>(3)? as u64,
                    ciphertext_md5_hex: r.get(4)?,
                })
            })?
            .collect::<Result<_, _>>()?;
        Ok(v)
    }

    /// Call after creating the URLSessionUploadTask and BEFORE task.resume(),
    /// so a completion event can never arrive for an unrecorded task.
    pub fn mark_enqueued(&self, session_id: String, task_id: u64, upload_id: String, part_number: u32) -> Result<(), CoreError> {
        let mut c = self.db.lock().unwrap();
        let tx = c.transaction()?;
        tx.execute(
            "INSERT OR REPLACE INTO tasks VALUES(?1,?2,?3,?4,'inflight')",
            params![session_id, task_id as i64, upload_id, part_number as i64],
        )?;
        tx.execute(
            "UPDATE parts SET state='enqueued' WHERE upload_id=?1 AND part_no=?2 AND state='spooled'",
            params![upload_id, part_number as i64],
        )?;
        tx.commit()?;
        Ok(())
    }

    /// Apply one URLSession task completion (delegate didCompleteWithError, possibly
    /// after a background relaunch). Idempotent.
    pub fn record_task_result(
        &self,
        session_id: String,
        task_id: u64,
        http_status: u16,
        etag: Option<String>,
        error: Option<String>,
    ) -> Result<TaskOutcome, CoreError> {
        let mut c = self.db.lock().unwrap();
        let tx = c.transaction()?;
        let row: Option<(String, i64, String)> = tx
            .query_row(
                "SELECT upload_id, part_no, state FROM tasks WHERE session_id=?1 AND task_id=?2",
                params![session_id, task_id as i64],
                |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?)),
            )
            .optional()?;
        let Some((upload_id, part_no, tstate)) = row else { return Ok(TaskOutcome::UnknownTask) };
        if tstate == "done" {
            return Ok(TaskOutcome::Duplicate);
        }
        let (pstate, path, md5, attempts): (String, String, String, i64) = tx.query_row(
            "SELECT state, spool_path, ct_md5, attempts FROM parts WHERE upload_id=?1 AND part_no=?2",
            params![upload_id, part_no],
            |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?, r.get(3)?)),
        )?;
        tx.execute(
            "UPDATE tasks SET state='done' WHERE session_id=?1 AND task_id=?2",
            params![session_id, task_id as i64],
        )?;
        if pstate == "uploaded" {
            tx.commit()?;
            return Ok(TaskOutcome::Duplicate);
        }
        let etag_clean = etag.as_deref().map(|e| e.trim_matches('"').to_ascii_lowercase());
        let ok = (200..300).contains(&http_status) && error.is_none() && etag_clean.is_some();
        let etag_matches = etag_clean.as_deref() == Some(md5.as_str());
        if ok && etag_matches {
            tx.execute(
                "UPDATE parts SET state='uploaded', etag=?3, attempts=attempts+1 WHERE upload_id=?1 AND part_no=?2",
                params![upload_id, part_no, etag_clean],
            )?;
            tx.commit()?;
            let _ = fs::remove_file(&path);
            sync_dir(&self.spool);
            return Ok(TaskOutcome::Recorded);
        }
        let reason = if ok {
            format!("etag mismatch: got {:?}, expected md5 {md5}", etag_clean)
        } else {
            format!("status {http_status}, error {:?}", error)
        };
        let new_state = if Path::new(&path).exists() { "spooled" } else { "missing" };
        tx.execute(
            "UPDATE parts SET state=?3, attempts=attempts+1 WHERE upload_id=?1 AND part_no=?2",
            params![upload_id, part_no, new_state],
        )?;
        tx.commit()?;
        Ok(TaskOutcome::Failed { attempts: (attempts + 1) as u32, reason })
    }

    /// After relaunch: compare DB in-flight tasks with URLSession.getAllTasks().
    /// Tasks the system no longer knows (user force-quit cancels them) are
    /// orphaned and their parts become re-enqueueable. Returns the count reset.
    pub fn reconcile_session(&self, session_id: String, live_task_ids: Vec<u64>) -> Result<u32, CoreError> {
        let mut c = self.db.lock().unwrap();
        let tx = c.transaction()?;
        let rows: Vec<(i64, String, i64)> = {
            let mut st = tx.prepare("SELECT task_id, upload_id, part_no FROM tasks WHERE session_id=?1 AND state='inflight'")?;
            let v = st.query_map(params![session_id], |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?)))?.collect::<Result<_, _>>()?;
            v
        };
        let mut n = 0;
        for (t, u, p) in rows {
            if live_task_ids.contains(&(t as u64)) {
                continue;
            }
            tx.execute("UPDATE tasks SET state='orphaned' WHERE session_id=?1 AND task_id=?2", params![session_id, t])?;
            n += tx.execute(
                "UPDATE parts SET state='spooled' WHERE upload_id=?1 AND part_no=?2 AND state='enqueued'",
                params![u, p],
            )? as u32;
        }
        tx.commit()?;
        Ok(n)
    }

    pub fn upload_status(&self, upload_id: String) -> Result<UploadStatus, CoreError> {
        let c = self.db.lock().unwrap();
        let up = self.load_upload(&c, &upload_id)?;
        let count = |s: &str| -> Result<u32, CoreError> {
            Ok(c.query_row(
                "SELECT COUNT(*) FROM parts WHERE upload_id=?1 AND state=?2",
                params![upload_id, s],
                |r| r.get::<_, i64>(0),
            )? as u32)
        };
        let (uploaded, enqueued, spooled, missing) = (count("uploaded")?, count("enqueued")?, count("spooled")?, count("missing")?);
        Ok(UploadStatus {
            upload_id: upload_id.clone(),
            n_parts: up.n_parts,
            uploaded,
            enqueued,
            spooled,
            missing,
            not_started: up.n_parts - uploaded - enqueued - spooled - missing,
            complete: uploaded == up.n_parts,
        })
    }

    pub fn spool_bytes(&self) -> Result<u64, CoreError> {
        Self::spool_used(&self.db.lock().unwrap())
    }
}

/// Trivial async export, only to check that UniFFI async bindings compile in the
/// Swift 5 and Swift 6 language modes.
#[uniffi::export]
pub async fn core_version_async() -> String {
    format!("reliquary-ios-shape {}", env!("CARGO_PKG_VERSION"))
}

// ---------------------------------------------------------------- test helper (not exported)

/// Decrypt part `p` (1-based) of an upload; used by the `verify` binary.
pub fn decrypt_part(key: &[u8; 32], chunks_per_part: u64, size: u64, p: u32, ct: &[u8]) -> Result<Vec<u8>, String> {
    let aead = ChaCha20Poly1305::new(&Key::from(*key));
    let total_chunks = if size == 0 { 1 } else { size.div_ceil(CHUNK_PT) };
    let first = (p as u64 - 1) * chunks_per_part;
    let mut out = Vec::new();
    for (i, c) in ct.chunks((CHUNK_PT + TAG_LEN) as usize).enumerate() {
        let idx = first + i as u64;
        let mut nonce = [0u8; 12];
        nonce[3..11].copy_from_slice(&idx.to_be_bytes());
        nonce[11] = (idx + 1 == total_chunks) as u8;
        let mut b = c.to_vec();
        aead.decrypt_in_place(&Nonce::from(nonce), b"", &mut b).map_err(|_| format!("auth fail part {p} chunk {i}"))?;
        out.extend_from_slice(&b);
    }
    Ok(out)
}
