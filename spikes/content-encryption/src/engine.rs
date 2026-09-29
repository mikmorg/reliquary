//! THROWAWAY SPIKE CODE. Not production.
//!
//! Pass 1 (hash + stat snapshot), per-upload keystore entry, write-once sealed
//! upload state, append-only journal (chunk tags + completed parts), chunk
//! sources (random-access and forward-only) and the verified range generator.

use crate::format::*;
use aes_gcm::{aead::Aead, aead::Payload, Aes256Gcm, Nonce as GcmNonce};
use base64::{engine::general_purpose::STANDARD as B64P, Engine};
use hmac::{Hmac, KeyInit, Mac};
use rand::{rngs::OsRng, RngCore};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, HashMap};
use std::fs::{self, File, OpenOptions};
use std::io::{self, Read, Seek, SeekFrom, Write};
use std::os::unix::fs::{FileExt, MetadataExt, OpenOptionsExt};
use std::path::{Path, PathBuf};
use zeroize::Zeroize;

// ---------------------------------------------------------------- snapshot

/// Pre-pass-1 identity of the source. Re-checked before and after every part
/// and at completion. (Production: platform file ID / PhotoKit
/// modificationDate / MediaStore generation instead of dev:ino and ctime.)
#[derive(Clone, Debug, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct Snapshot {
    pub size: u64,
    pub mtime_ns: String,
    pub ctime_ns: String,
    pub file_id: String,
}

pub fn snapshot(path: &Path) -> io::Result<Snapshot> {
    let m = fs::metadata(path)?;
    Ok(Snapshot {
        size: m.len(),
        mtime_ns: (m.mtime() as i128 * 1_000_000_000 + m.mtime_nsec() as i128).to_string(),
        ctime_ns: (m.ctime() as i128 * 1_000_000_000 + m.ctime_nsec() as i128).to_string(),
        file_id: format!("{}:{}", m.dev(), m.ino()),
    })
}

// ---------------------------------------------------------------- pass 1

pub struct HashResult {
    pub sha256: [u8; 32],
    pub dedup_id: [u8; 32],
    pub snapshot: Snapshot,
}

#[derive(Debug)]
pub enum PassError {
    /// The file changed while it was being hashed; retry after it is quiescent.
    Unstable(String),
    Io(io::Error),
}

/// Pass 1: stat, one sequential read computing SHA-256 and
/// HMAC-SHA256(dedup_key), stat again. Two hash computations per byte.
pub fn hash_pass(path: &Path, dedup_key: &[u8; 32]) -> Result<HashResult, PassError> {
    let before = snapshot(path).map_err(PassError::Io)?;
    let mut f = File::open(path).map_err(PassError::Io)?;
    let mut sha = Sha256::new();
    let mut hm = <Hmac<Sha256> as KeyInit>::new_from_slice(dedup_key).unwrap();
    let mut buf = vec![0u8; 1 << 20];
    let mut total = 0u64;
    loop {
        let n = f.read(&mut buf).map_err(PassError::Io)?;
        if n == 0 {
            break;
        }
        sha.update(&buf[..n]);
        hm.update(&buf[..n]);
        total += n as u64;
    }
    buf.zeroize();
    let after = snapshot(path).map_err(PassError::Io)?;
    if before != after || total != before.size {
        return Err(PassError::Unstable(format!("source changed during pass 1 ({} bytes read, {:?} -> {:?})", total, before, after)));
    }
    Ok(HashResult { sha256: sha.finalize().into(), dedup_id: hm.finalize().into_bytes().into(), snapshot: before })
}

// ---------------------------------------------------------------- file helpers

/// Creates a secret file with mode 0600 (never world-readable), exclusive.
pub fn write_secret_new(path: &Path, data: &[u8]) -> io::Result<()> {
    let mut f = OpenOptions::new().write(true).create_new(true).mode(0o600).open(path)?;
    f.write_all(data)?;
    f.sync_all()
}

/// Atomic replace: unique temp name (never shared between processes), 0600,
/// fsync, rename, fsync directory.
pub fn write_atomic(path: &Path, data: &[u8]) -> io::Result<()> {
    let mut r = [0u8; 8];
    OsRng.fill_bytes(&mut r);
    let tmp = path.with_extension(format!("tmp-{}", hex::encode(r)));
    {
        let mut f = OpenOptions::new().write(true).create_new(true).mode(0o600).open(&tmp)?;
        f.write_all(data)?;
        f.sync_all()?;
    }
    fs::rename(&tmp, path)?;
    if let Some(dir) = path.parent() {
        File::open(dir)?.sync_all()?;
    }
    Ok(())
}

pub fn remove_if_exists(path: &Path) -> io::Result<()> {
    match fs::remove_file(path) {
        Err(e) if e.kind() != io::ErrorKind::NotFound => Err(e),
        _ => Ok(()),
    }
}

// ---------------------------------------------------------------- keystore

/// Prototype stand-in for a per-upload platform keystore entry (Android
/// Keystore AES-GCM key / iOS keychain ThisDeviceOnly item). One 32-byte key
/// per upload, mode 0600, deleted when the upload completes or is aborted, which
/// makes any leftover copy of the sealed state useless.
pub struct Keystore(pub PathBuf);

impl Keystore {
    fn path(&self, id: &str) -> PathBuf {
        self.0.join(format!("{id}.key"))
    }
    pub fn create(&self, id: &str) -> io::Result<[u8; 32]> {
        fs::create_dir_all(&self.0)?;
        let mut k = [0u8; 32];
        OsRng.fill_bytes(&mut k);
        write_secret_new(&self.path(id), &k)?;
        Ok(k)
    }
    pub fn load(&self, id: &str) -> Result<[u8; 32], String> {
        let v = fs::read(self.path(id)).map_err(|e| format!("keystore entry for {id}: {e}"))?;
        v.try_into().map_err(|_| "keystore entry corrupt".into())
    }
    pub fn delete(&self, id: &str) -> io::Result<()> {
        remove_if_exists(&self.path(id))
    }
}

// ---------------------------------------------------------------- sealed state

/// Write-once, per upload. Holds the only secret (the payload key) and
/// everything static. Progress lives in the append-only journal.
#[derive(serde::Serialize, serde::Deserialize)]
pub struct UploadState {
    pub v: u32,
    pub upload_id: String,
    /// R2 UploadId (simulated).
    pub r2_upload_id: String,
    /// staging/<dedup_id>/<upload_id>: one staged object per upload, never overwritten.
    pub object_key: String,
    pub device_id: String,
    pub source_path: String,
    pub snapshot: Snapshot,
    pub layout: Layout,
    pub sha256: String,
    pub dedup_id: String,
    /// Header + payload nonce. Not secret (bytes 0..prefix_len of the object).
    pub prefix_b64: String,
    /// SECRET: HKDF(file key, nonce, "payload"). Regenerates (and decrypts)
    /// this one object only.
    pub payload_key_b64: String,
    /// Signed + encrypted metadata record, built before any content byte is uploaded.
    pub meta_file: String,
    pub meta_sha256: String,
}

impl Drop for UploadState {
    fn drop(&mut self) {
        self.payload_key_b64.zeroize();
    }
}

impl UploadState {
    pub fn prefix(&self) -> Vec<u8> {
        B64P.decode(&self.prefix_b64).expect("prefix b64")
    }
    pub fn payload_key(&self) -> [u8; 32] {
        B64P.decode(&self.payload_key_b64).expect("pk b64").try_into().expect("pk len")
    }
}

const STATE_MAGIC: &[u8; 8] = b"RQUS\x00\x00\x00\x02";

/// Seal = AES-256-GCM(per-upload keystore key, random 96-bit nonce, json,
/// aad = magic || upload_id). AES-GCM because that is what a non-exportable
/// Android Keystore key can do in-keystore; iOS would wrap with a
/// Secure-Enclave P-256 ECIES key instead.
pub fn seal_state(st: &UploadState, key: &[u8; 32], path: &Path) -> io::Result<()> {
    let mut json = serde_json::to_vec(st).unwrap();
    let mut nonce = [0u8; 12];
    OsRng.fill_bytes(&mut nonce);
    let aad = [STATE_MAGIC.as_slice(), st.upload_id.as_bytes()].concat();
    let ct = Aes256Gcm::new(key.into())
        .encrypt(&GcmNonce::from(nonce), Payload { msg: &json, aad: &aad })
        .unwrap();
    json.zeroize();
    let idb = st.upload_id.as_bytes();
    let mut out = Vec::with_capacity(ct.len() + 64);
    out.extend_from_slice(STATE_MAGIC);
    out.extend_from_slice(&(idb.len() as u16).to_be_bytes());
    out.extend_from_slice(idb);
    out.extend_from_slice(&nonce);
    out.extend_from_slice(&ct);
    write_atomic(path, &out)
}

/// Every length is bounds-checked: a truncated or garbled state is an error
/// ("abort this upload and start over"), never a panic.
pub fn open_state(ks: &Keystore, path: &Path) -> Result<UploadState, String> {
    let raw = fs::read(path).map_err(|e| format!("state unreadable: {e}"))?;
    if raw.len() < 10 || &raw[..8] != STATE_MAGIC {
        return Err("state corrupt: bad magic or too short".into());
    }
    let idl = u16::from_be_bytes([raw[8], raw[9]]) as usize;
    if raw.len() < 10 + idl + 12 + 16 {
        return Err("state corrupt: truncated".into());
    }
    let id = std::str::from_utf8(&raw[10..10 + idl]).map_err(|_| "state corrupt: id")?;
    if !id.bytes().all(|b| b.is_ascii_hexdigit()) {
        return Err("state corrupt: id".into());
    }
    let key = ks.load(id)?;
    let nonce = &raw[10 + idl..22 + idl];
    let aad = [STATE_MAGIC.as_slice(), id.as_bytes()].concat();
    let mut json = Aes256Gcm::new((&key).into())
        .decrypt(&GcmNonce::try_from(nonce).unwrap(), Payload { msg: &raw[22 + idl..], aad: &aad })
        .map_err(|_| "state authentication failed".to_string())?;
    let st: Result<UploadState, _> = serde_json::from_slice(&json);
    json.zeroize();
    let st = st.map_err(|e| format!("state corrupt: {e}"))?;
    if st.upload_id != id {
        return Err("state id mismatch".into());
    }
    Ok(st)
}

/// Single writer per upload: an exclusive advisory lock held for the life of
/// the process (flock on Unix, LockFileEx on Windows via std).
pub fn lock_upload(dir: &Path, id: &str) -> Result<File, String> {
    let f = OpenOptions::new().create(true).truncate(false).write(true).mode(0o600).open(dir.join(format!("{id}.lock"))).map_err(|e| e.to_string())?;
    match f.try_lock() {
        Ok(()) => Ok(f),
        Err(fs::TryLockError::WouldBlock) => Err("BUSY".into()),
        Err(fs::TryLockError::Error(e)) => Err(e.to_string()),
    }
}

// ---------------------------------------------------------------- journal

const J_MAGIC: &[u8; 4] = b"RQJ\x01";
const REC_TAGS: u8 = 1;
const REC_DONE: u8 = 2;

/// Append-only progress journal. Records:
///   type u8 || len u32 BE || body || HMAC-SHA256(journal_key, "RQJ1" || seq u64 || type || len || body)[..16]
/// TAGS body: first_chunk u64 BE || n x 16-byte Poly1305 tags (consecutive chunks)
/// DONE body: part u32 BE (1-based) || ETag (UTF-8, stored verbatim)
/// journal_key = HKDF(payload_key, "reliquary/v1/journal"). A torn final record
/// (crash mid-append) is dropped; any other bad record fails the upload.
/// Each append is fsynced before anything that depends on it leaves the device.
pub struct Journal {
    f: Option<File>,
    key: [u8; 32],
    seq: u64,
    pub tags: HashMap<u64, [u8; 16]>,
    pub done: BTreeMap<u64, String>,
    pub bytes_written: u64,
}

impl Drop for Journal {
    fn drop(&mut self) {
        self.key.zeroize();
    }
}

impl Journal {
    fn key_from(payload_key: &[u8; 32]) -> [u8; 32] {
        hkdf32(&[], b"reliquary/v1/journal", payload_key)
    }
    /// In-memory journal (single-PUT uploads have no resume state).
    pub fn memory() -> Journal {
        Journal { f: None, key: [0; 32], seq: 0, tags: HashMap::new(), done: BTreeMap::new(), bytes_written: 0 }
    }
    pub fn create(path: &Path, payload_key: &[u8; 32]) -> io::Result<Journal> {
        let mut f = OpenOptions::new().read(true).append(true).create_new(true).mode(0o600).open(path)?;
        f.write_all(J_MAGIC)?;
        f.sync_all()?;
        if let Some(dir) = path.parent() {
            File::open(dir)?.sync_all()?;
        }
        Ok(Journal { f: Some(f), key: Self::key_from(payload_key), seq: 0, tags: HashMap::new(), done: BTreeMap::new(), bytes_written: 4 })
    }
    pub fn open(path: &Path, payload_key: &[u8; 32]) -> Result<Journal, String> {
        let mut f = OpenOptions::new().read(true).append(true).open(path).map_err(|e| format!("journal: {e}"))?;
        let mut raw = vec![];
        f.read_to_end(&mut raw).map_err(|e| e.to_string())?;
        if raw.len() < 4 || &raw[..4] != J_MAGIC {
            return Err("journal corrupt: magic".into());
        }
        let mut j = Journal { f: None, key: Self::key_from(payload_key), seq: 0, tags: HashMap::new(), done: BTreeMap::new(), bytes_written: 0 };
        let mut off = 4usize;
        let mut good_end = 4usize;
        while off < raw.len() {
            let torn = |why: &str| -> Result<(), String> { Err(format!("journal corrupt: {why}")) };
            if raw.len() - off < 5 {
                break; // torn header of the final record
            }
            let ty = raw[off];
            let len = u32::from_be_bytes(raw[off + 1..off + 5].try_into().unwrap()) as usize;
            let end = off + 5 + len + 16;
            if end > raw.len() {
                break; // torn final record
            }
            let body = &raw[off + 5..off + 5 + len];
            let mac = j.mac(ty, body);
            if mac[..16] != raw[end - 16..end] {
                if end == raw.len() {
                    break; // torn final record (garbage after a crash)
                }
                torn("record MAC")?;
            }
            match ty {
                REC_TAGS if len >= 8 && (len - 8) % 16 == 0 => {
                    let c0 = u64::from_be_bytes(body[..8].try_into().unwrap());
                    for (i, t) in body[8..].chunks(16).enumerate() {
                        j.tags.insert(c0 + i as u64, t.try_into().unwrap());
                    }
                }
                REC_DONE if len >= 4 => {
                    let p = u32::from_be_bytes(body[..4].try_into().unwrap()) as u64;
                    let etag = String::from_utf8(body[4..].to_vec()).map_err(|_| "journal corrupt: etag")?;
                    j.done.insert(p - 1, etag);
                }
                _ => torn("record type")?,
            }
            j.seq += 1;
            off = end;
            good_end = end;
        }
        if good_end != raw.len() {
            f.set_len(good_end as u64).map_err(|e| e.to_string())?;
            f.sync_all().map_err(|e| e.to_string())?;
        }
        f.seek(SeekFrom::End(0)).map_err(|e| e.to_string())?;
        j.f = Some(f);
        Ok(j)
    }
    fn mac(&self, ty: u8, body: &[u8]) -> [u8; 32] {
        hmac_sha256(&self.key, &[b"RQJ1", &self.seq.to_be_bytes(), &[ty], &(body.len() as u32).to_be_bytes(), body])
    }
    fn append(&mut self, ty: u8, body: &[u8]) -> io::Result<()> {
        if self.f.is_some() {
            let mac = self.mac(ty, body);
            let mut rec = Vec::with_capacity(body.len() + 21);
            rec.push(ty);
            rec.extend_from_slice(&(body.len() as u32).to_be_bytes());
            rec.extend_from_slice(body);
            rec.extend_from_slice(&mac[..16]);
            let f = self.f.as_mut().unwrap();
            f.write_all(&rec)?;
            f.sync_data()?;
            self.bytes_written += rec.len() as u64;
        }
        self.seq += 1;
        Ok(())
    }
    /// Durably records first-seen chunk tags (grouped into runs of consecutive chunks).
    pub fn record_tags(&mut self, new: &[(u64, [u8; 16])]) -> io::Result<()> {
        let mut i = 0;
        while i < new.len() {
            let mut j = i + 1;
            while j < new.len() && new[j].0 == new[j - 1].0 + 1 {
                j += 1;
            }
            let mut body = new[i].0.to_be_bytes().to_vec();
            for (_, t) in &new[i..j] {
                body.extend_from_slice(t);
            }
            self.append(REC_TAGS, &body)?;
            i = j;
        }
        for (c, t) in new {
            self.tags.insert(*c, *t);
        }
        Ok(())
    }
    pub fn record_done(&mut self, p: u64, etag: &str) -> io::Result<()> {
        let mut body = ((p + 1) as u32).to_be_bytes().to_vec();
        body.extend_from_slice(etag.as_bytes());
        self.append(REC_DONE, &body)?;
        self.done.insert(p, etag.to_string());
        Ok(())
    }
}

// ---------------------------------------------------------------- sources

pub trait ChunkSource {
    fn read_at(&mut self, off: u64, buf: &mut [u8]) -> io::Result<()>;
    /// Source bytes read (including bytes skipped to reach an offset).
    fn bytes_read(&self) -> u64;
    /// Times the source had to be restarted from the beginning.
    fn restarts(&self) -> u64;
}

/// Seekable file (desktop, Android file/most content:// URIs, iOS file URLs).
pub struct RandomSource {
    f: File,
    n: u64,
}

impl RandomSource {
    pub fn open(path: &Path) -> io::Result<Self> {
        Ok(RandomSource { f: File::open(path)?, n: 0 })
    }
}

impl ChunkSource for RandomSource {
    fn read_at(&mut self, off: u64, buf: &mut [u8]) -> io::Result<()> {
        self.f.read_exact_at(buf, off)?; // Windows: seek_read
        self.n += buf.len() as u64;
        Ok(())
    }
    fn bytes_read(&self) -> u64 {
        self.n
    }
    fn restarts(&self) -> u64 {
        0
    }
}

/// Forward-only stream (models iOS PHAssetResourceManager): reaching an
/// earlier offset means restarting the stream and skipping forward.
pub struct SequentialSource {
    path: PathBuf,
    r: Option<io::BufReader<File>>,
    pos: u64,
    n: u64,
    restarts: u64,
}

impl SequentialSource {
    pub fn open(path: &Path) -> io::Result<Self> {
        let f = File::open(path)?;
        Ok(SequentialSource { path: path.into(), r: Some(io::BufReader::with_capacity(1 << 16, f)), pos: 0, n: 0, restarts: 0 })
    }
}

impl ChunkSource for SequentialSource {
    fn read_at(&mut self, off: u64, buf: &mut [u8]) -> io::Result<()> {
        if off < self.pos || self.r.is_none() {
            self.r = Some(io::BufReader::with_capacity(1 << 16, File::open(&self.path)?));
            self.pos = 0;
            self.restarts += 1;
        }
        let r = self.r.as_mut().unwrap();
        let skip = off - self.pos;
        if skip > 0 {
            let copied = io::copy(&mut r.by_ref().take(skip), &mut io::sink())?;
            if copied != skip {
                return Err(io::ErrorKind::UnexpectedEof.into());
            }
            self.n += skip;
        }
        r.read_exact(buf)?;
        self.n += buf.len() as u64;
        self.pos = off + buf.len() as u64;
        Ok(())
    }
    fn bytes_read(&self) -> u64 {
        self.n
    }
    fn restarts(&self) -> u64 {
        self.restarts
    }
}

// ---------------------------------------------------------------- generator

#[derive(Debug)]
pub enum GenError {
    /// Chunk plaintext differs from what was encrypted earlier under the same
    /// key and nonce. Nothing was released; the upload must be aborted.
    SourceChanged(u64),
    Io(io::Error),
}

/// The ONLY encryption path for content objects. `gen_range` produces the
/// exact object bytes [s, e) into `out` and returns Ok only when every chunk it
/// touched is safe to release:
///   * a chunk whose tag is already in the journal must re-encrypt to exactly
///     that tag (same plaintext); otherwise SourceChanged and `out` is wiped;
///   * a chunk seen for the first time has its tag appended to the journal and
///     fsynced BEFORE gen_range returns.
/// Callers may release `out` (network, spool file) only after Ok. Streaming
/// uploads call gen_range per window of W chunks, so at most W chunks are
/// buffered and no unverified byte is ever emitted.
///
/// Poly1305 tags as change detectors: for a fixed one-time key, two different
/// 64 KiB messages collide with probability <= 8*ceil(L/16)/2^106 = 2^-91, and edits are
/// independent of the random key. The tag is computed anyway, so this costs no
/// extra hashing.
pub struct Generator<'a> {
    pub layout: Layout,
    prefix: &'a [u8],
    cipher: PayloadCipher,
    src: &'a mut dyn ChunkSource,
    cache_c: Option<u64>,
    cache_ct: Vec<u8>,
    buf: Vec<u8>,
    pub chunks_encrypted: u64,
}

impl<'a> Generator<'a> {
    pub fn new(layout: Layout, prefix: &'a [u8], payload_key: &[u8; 32], src: &'a mut dyn ChunkSource) -> Self {
        Generator {
            layout,
            prefix,
            cipher: PayloadCipher::new(payload_key, layout.n_chunks()),
            src,
            cache_c: None,
            cache_ct: Vec::with_capacity(CHUNK_CT as usize),
            buf: Vec::with_capacity(CHUNK_CT as usize),
            chunks_encrypted: 0,
        }
    }

    pub fn gen_range(&mut self, journal: &mut Journal, s: u64, e: u64, out: &mut Vec<u8>) -> Result<(), GenError> {
        let l = self.layout;
        out.clear();
        let pl = l.prefix_len;
        if s < pl {
            out.extend_from_slice(&self.prefix[s as usize..std::cmp::min(e, pl) as usize]);
        }
        let mut new_tags: Vec<(u64, [u8; 16])> = vec![];
        if let Some((c0, c1)) = l.chunks_in_range(s, e) {
            for c in c0..=c1 {
                if self.cache_c != Some(c) {
                    let (a, b) = l.chunk_pt_range(c);
                    self.buf.resize((b - a) as usize, 0);
                    if let Err(err) = self.src.read_at(a, &mut self.buf) {
                        out.zeroize();
                        out.clear();
                        return Err(GenError::Io(err));
                    }
                    self.cipher.encrypt_chunk(c, &mut self.buf);
                    self.chunks_encrypted += 1;
                    let tag: [u8; 16] = self.buf[self.buf.len() - 16..].try_into().unwrap();
                    if let Some(known) = journal.tags.get(&c) {
                        if *known != tag {
                            out.zeroize();
                            out.clear();
                            self.buf.zeroize();
                            self.cache_c = None;
                            return Err(GenError::SourceChanged(c));
                        }
                    }
                    std::mem::swap(&mut self.buf, &mut self.cache_ct);
                    self.cache_c = Some(c);
                }
                let ct = &self.cache_ct;
                if !journal.tags.contains_key(&c) {
                    new_tags.push((c, ct[ct.len() - 16..].try_into().unwrap()));
                }
                let (os, oe) = l.chunk_obj_range(c);
                let lo = std::cmp::max(os, s);
                let hi = std::cmp::min(oe, e);
                out.extend_from_slice(&ct[(lo - os) as usize..(hi - os) as usize]);
            }
        }
        if !new_tags.is_empty() {
            if let Err(err) = journal.record_tags(&new_tags) {
                out.zeroize();
                out.clear();
                return Err(GenError::Io(err));
            }
        }
        debug_assert_eq!(out.len() as u64, e - s);
        Ok(())
    }

    pub fn source_bytes_read(&self) -> u64 {
        self.src.bytes_read()
    }
    pub fn source_restarts(&self) -> u64 {
        self.src.restarts()
    }
}

/// Splits part p into windows aligned to chunk boundaries, each covering at
/// most `w` chunks (w = None: the whole part is one window).
pub fn part_windows(l: &Layout, p: u64, w: Option<u64>) -> Vec<(u64, u64)> {
    let (s, e) = l.part_range(p);
    let w = match w {
        None => return vec![(s, e)],
        Some(w) => w.max(1),
    };
    let Some((c0, c1)) = l.chunks_in_range(s, e) else { return vec![(s, e)] };
    let mut v = vec![];
    let mut start = s;
    let mut c = c0 + w;
    while c <= c1 {
        let b = l.chunk_obj_range(c).0;
        if b > start && b < e {
            v.push((start, b));
            start = b;
        }
        c += w;
    }
    v.push((start, e));
    v
}

#[cfg(test)]
mod tests {
    use super::*;

    struct MemSource(Vec<u8>, u64);
    impl ChunkSource for MemSource {
        fn read_at(&mut self, off: u64, buf: &mut [u8]) -> io::Result<()> {
            buf.copy_from_slice(&self.0[off as usize..off as usize + buf.len()]);
            self.1 += buf.len() as u64;
            Ok(())
        }
        fn bytes_read(&self) -> u64 {
            self.1
        }
        fn restarts(&self) -> u64 {
            0
        }
    }

    /// Windowed (streaming) generation yields the same bytes as whole-part
    /// generation, for any window size, and the second pass verifies every tag.
    #[test]
    fn windows_equal_whole_parts() {
        let data: Vec<u8> = (0..(5 * 65_536 + 777)).map(|i| (i * 31 % 251) as u8).collect();
        for k in 1..=4u64 {
            let l = Layout { pt_len: data.len() as u64, chunks_per_part: k, prefix_len: 184 };
            let prefix = vec![9u8; 184];
            let key = [3u8; 32];
            let mut whole = vec![];
            let mut j = Journal::memory();
            let mut src = MemSource(data.clone(), 0);
            let mut g = Generator::new(l, &prefix, &key, &mut src);
            let mut out = vec![];
            for p in 0..l.num_parts() {
                g.gen_range(&mut j, l.part_range(p).0, l.part_range(p).1, &mut out).unwrap();
                whole.extend_from_slice(&out);
            }
            assert_eq!(whole.len() as u64, l.ct_len());
            for w in 1..=3u64 {
                let mut src2 = MemSource(data.clone(), 0);
                let mut g2 = Generator::new(l, &prefix, &key, &mut src2);
                let mut streamed = vec![];
                for p in (0..l.num_parts()).rev() {
                    let mut part = vec![];
                    for (a, b) in part_windows(&l, p, Some(w)) {
                        g2.gen_range(&mut j, a, b, &mut out).unwrap();
                        part.extend_from_slice(&out);
                    }
                    let (s, e) = l.part_range(p);
                    assert_eq!(&part[..], &whole[s as usize..e as usize]);
                    streamed.push(part);
                }
            }
            // a changed chunk is refused, and nothing is returned
            let mut bad = data.clone();
            bad[65_536 + 5] ^= 1;
            let mut src3 = MemSource(bad, 0);
            let mut g3 = Generator::new(l, &prefix, &key, &mut src3);
            let r = g3.gen_range(&mut j, 0, l.ct_len(), &mut out);
            assert!(matches!(r, Err(GenError::SourceChanged(1))));
            assert!(out.is_empty());
        }
    }

    #[test]
    fn journal_torn_tail_and_corruption() {
        let dir = std::env::temp_dir().join(format!("rqj-test-{}", std::process::id()));
        let _ = fs::remove_dir_all(&dir);
        fs::create_dir_all(&dir).unwrap();
        let p = dir.join("j");
        let key = [5u8; 32];
        let mut j = Journal::create(&p, &key).unwrap();
        j.record_tags(&[(0, [1; 16]), (1, [2; 16]), (5, [3; 16])]).unwrap();
        j.record_done(0, "etag-1").unwrap();
        drop(j);
        let full = fs::read(&p).unwrap();
        // torn tail: every truncation point of the last record reopens cleanly
        for cut in 1..=25 {
            fs::write(&p, &full[..full.len() - cut]).unwrap();
            let j = Journal::open(&p, &key).unwrap();
            assert_eq!(j.tags.len(), 3);
            assert!(j.done.is_empty());
        }
        fs::write(&p, &full).unwrap();
        let j = Journal::open(&p, &key).unwrap();
        assert_eq!(j.done.get(&0).unwrap(), "etag-1");
        // corruption in a non-final record is an error, not silently skipped
        let mut bad = full.clone();
        bad[10] ^= 1;
        fs::write(&p, &bad).unwrap();
        assert!(Journal::open(&p, &key).is_err());
        // wrong key: every record fails; the first is not final, so error
        fs::write(&p, &full).unwrap();
        assert!(Journal::open(&p, &[6u8; 32]).is_err());
        let _ = fs::remove_dir_all(&dir);
    }
}
