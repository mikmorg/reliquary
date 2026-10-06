//! Reliquary A1-S2: dedup-secret rotation over a 1M-entry client hash cache
//! (THROWAWAY spike code, not production).
//!
//! Candidate construction B (see spikes/A1-S3): dk_e = HKDF-SHA256(ikm = K_e, salt = empty,
//! info = "reliquary/v1/dedup-key/sha256-digest"); id = HMAC-SHA256(dk_e, SHA-256(content)).
//! Rotation to epoch e+1 recomputes every id from the cached SHA-256 only. The synthetic cache
//! rows point at paths that DO NOT EXIST, so any attempt to read a source file would fail; the
//! run is also traced with strace to show no file other than the database is opened.
//!
//! Subcommands (one JSON line of results each):
//!   build   <db> <rows>                 create a synthetic cache at epoch 0
//!   rotate  <db> <new_epoch> inplace    rewrite the dedup_id column in one transaction
//!   rotate  <db> <new_epoch> map        keep old ids; write an (old_id -> new_id) map table
//!   derive  <rows>                      pure in-memory derivation cost (homelab catalog compute)
//!   mkfiles <dir> <count> <size>        make small SYN files for the content-variant re-read test
//!   reread  <path>...                   content variant A: HMAC(dk_new, content) over files (re-read cost)

use hkdf::Hkdf;
use hmac::{Hmac, KeyInit, Mac};
use rusqlite::{params, Connection};
use sha2::{Digest, Sha256};
use std::io::Read;
use std::time::Instant;

type HmacSha256 = Hmac<Sha256>;

const INFO_B: &[u8] = b"reliquary/v1/dedup-key/sha256-digest";
const INFO_A: &[u8] = b"reliquary/v1/dedup-key";

fn family_secret(epoch: u32) -> [u8; 32] {
    // Synthetic K_e for the spike. Real epochs use independent random secrets (D2 owns custody).
    let mut h = Sha256::new();
    h.update(b"reliquary-a1-s2-synthetic-family-secret-epoch-");
    h.update(epoch.to_be_bytes());
    h.finalize().into()
}

fn dk(epoch: u32, info: &[u8]) -> [u8; 32] {
    let hk = Hkdf::<Sha256>::new(None, &family_secret(epoch));
    let mut o = [0u8; 32];
    hk.expand(info, &mut o).unwrap();
    o
}

fn id_b(mac: &HmacSha256, sha: &[u8]) -> [u8; 32] {
    let mut m = mac.clone();
    m.update(sha);
    m.finalize().into_bytes().into()
}

fn proc_io() -> (u64, u64, u64, u64) {
    let s = std::fs::read_to_string("/proc/self/io").unwrap_or_default();
    let g = |k: &str| {
        s.lines()
            .find(|l| l.starts_with(k))
            .and_then(|l| l.split_whitespace().nth(1))
            .and_then(|v| v.parse().ok())
            .unwrap_or(0u64)
    };
    (g("rchar:"), g("wchar:"), g("read_bytes:"), g("write_bytes:"))
}

fn cpu_secs() -> f64 {
    unsafe {
        let mut ru: libc::rusage = std::mem::zeroed();
        libc::getrusage(libc::RUSAGE_SELF, &mut ru);
        let t = |tv: libc::timeval| tv.tv_sec as f64 + tv.tv_usec as f64 / 1e6;
        t(ru.ru_utime) + t(ru.ru_stime)
    }
}

fn open(db: &str) -> Connection {
    let c = Connection::open(db).unwrap();
    c.execute_batch("PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;").unwrap();
    c
}

fn build(db: &str, rows: u64) {
    let _ = std::fs::remove_file(db);
    let mut c = open(db);
    c.execute_batch(
        "CREATE TABLE cache(
            id INTEGER PRIMARY KEY,
            source_locator TEXT NOT NULL,
            size INTEGER NOT NULL, mtime_ns INTEGER NOT NULL, ctime_ns INTEGER NOT NULL, inode INTEGER NOT NULL,
            sha256 BLOB NOT NULL,
            dedup_epoch INTEGER NOT NULL, dedup_id BLOB NOT NULL);",
    )
    .unwrap();
    let t0 = Instant::now();
    let mac0 = <HmacSha256 as KeyInit>::new_from_slice(&dk(0, INFO_B)).unwrap();
    let tx = c.transaction().unwrap();
    {
        let mut st = tx
            .prepare("INSERT INTO cache(id, source_locator, size, mtime_ns, ctime_ns, inode, sha256, dedup_epoch, dedup_id) VALUES (?1,?2,?3,?4,?5,?6,?7,0,?8)")
            .unwrap();
        for i in 0..rows {
            // Synthetic digest (not of any real file) and a path that does not exist.
            let sha: [u8; 32] = Sha256::digest(i.to_le_bytes()).into();
            let id = id_b(&mac0, &sha);
            let path = format!("/nonexistent/a1-s2/DCIM/{:04}/IMG_{:07}.HEIC", i / 1000, i);
            let size = 1_000_000 + (i * 7919) % 6_000_000;
            st.execute(params![
                i as i64,
                path,
                size as i64,
                1_700_000_000_000_000_000i64 + i as i64,
                1_700_000_000_000_000_000i64 + i as i64,
                (100_000 + i) as i64,
                &sha[..],
                &id[..]
            ])
            .unwrap();
        }
    }
    tx.commit().unwrap();
    c.execute_batch("PRAGMA wal_checkpoint(TRUNCATE);").unwrap();
    let sz = std::fs::metadata(db).unwrap().len();
    println!(
        "{{\"cmd\":\"build\",\"rows\":{},\"secs\":{:.2},\"db_bytes\":{}}}",
        rows,
        t0.elapsed().as_secs_f64(),
        sz
    );
}

fn rotate(db: &str, new_epoch: u32, mode: &str) {
    let io0 = proc_io();
    let c0 = cpu_secs();
    let t0 = Instant::now();
    let mut c = open(db);
    let mac = <HmacSha256 as KeyInit>::new_from_slice(&dk(new_epoch, INFO_B)).unwrap();
    let tx = c.transaction().unwrap();
    let mut n = 0u64;
    {
        if mode == "map" {
            tx.execute_batch("CREATE TABLE IF NOT EXISTS id_map(old_epoch INTEGER, old_id BLOB, new_epoch INTEGER, new_id BLOB);")
                .unwrap();
        }
        let mut sel = tx.prepare("SELECT id, sha256, dedup_epoch, dedup_id, source_locator FROM cache").unwrap();
        let mut upd = tx.prepare("UPDATE cache SET dedup_epoch=?1, dedup_id=?2 WHERE id=?3").unwrap();
        let mut ins = tx
            .prepare("INSERT INTO id_map(old_epoch, old_id, new_epoch, new_id) VALUES (?1,?2,?3,?4)")
            .ok();
        let mut rows = sel.query([]).unwrap();
        while let Some(r) = rows.next().unwrap() {
            let id: i64 = r.get(0).unwrap();
            let sha: Vec<u8> = r.get(1).unwrap();
            let old_epoch: i64 = r.get(2).unwrap();
            let old_id: Vec<u8> = r.get(3).unwrap();
            let _loc: String = r.get(4).unwrap(); // read like a real client would, never opened
            let nid = id_b(&mac, &sha);
            if mode == "map" {
                ins.as_mut()
                    .unwrap()
                    .execute(params![old_epoch, &old_id[..], new_epoch as i64, &nid[..]])
                    .unwrap();
            }
            upd.execute(params![new_epoch as i64, &nid[..], id]).unwrap();
            n += 1;
        }
    }
    tx.commit().unwrap();
    c.execute_batch("PRAGMA wal_checkpoint(TRUNCATE);").unwrap();
    let secs = t0.elapsed().as_secs_f64();
    let io1 = proc_io();
    // spot-check one row against an independent recomputation
    let (sha, nid): (Vec<u8>, Vec<u8>) = c
        .query_row("SELECT sha256, dedup_id FROM cache WHERE id = ?1", [n as i64 / 2], |r| {
            Ok((r.get(0)?, r.get(1)?))
        })
        .unwrap();
    let ok = id_b(&mac, &sha)[..] == nid[..];
    println!(
        "{{\"cmd\":\"rotate\",\"mode\":\"{}\",\"new_epoch\":{},\"rows\":{},\"secs\":{:.2},\"cpu_secs\":{:.2},\"rchar\":{},\"wchar\":{},\"disk_read_bytes\":{},\"disk_write_bytes\":{},\"spot_check_ok\":{},\"db_bytes_after\":{}}}",
        mode,
        new_epoch,
        n,
        secs,
        cpu_secs() - c0,
        io1.0 - io0.0,
        io1.1 - io0.1,
        io1.2 - io0.2,
        io1.3 - io0.3,
        ok,
        std::fs::metadata(db).unwrap().len()
    );
}

fn derive(rows: u64) {
    let shas: Vec<[u8; 32]> = (0..rows).map(|i| Sha256::digest(i.to_le_bytes()).into()).collect();
    let t0 = Instant::now();
    let mac = <HmacSha256 as KeyInit>::new_from_slice(&dk(1, INFO_B)).unwrap();
    let mut acc = 0u8;
    for s in &shas {
        acc ^= id_b(&mac, s)[0];
    }
    let secs = t0.elapsed().as_secs_f64();
    println!(
        "{{\"cmd\":\"derive\",\"rows\":{},\"secs\":{:.3},\"ids_per_s\":{:.0},\"sink\":{}}}",
        rows,
        secs,
        rows as f64 / secs,
        acc
    );
}

fn mkfiles(dir: &str, count: u64, size: usize) {
    std::fs::create_dir_all(dir).unwrap();
    let mut buf = vec![0u8; size];
    let mut x: u64 = 0x1234_5678_9abc_def1;
    for i in 0..count {
        for b in buf.iter_mut() {
            x ^= x << 13;
            x ^= x >> 7;
            x ^= x << 17;
            *b = x as u8;
        }
        std::fs::write(format!("{}/f{:07}.bin", dir, i), &buf).unwrap();
    }
    println!("{{\"cmd\":\"mkfiles\",\"count\":{},\"size\":{}}}", count, size);
}

fn collect(p: &std::path::Path, out: &mut Vec<std::path::PathBuf>) {
    if p.is_dir() {
        let mut v: Vec<_> = std::fs::read_dir(p).unwrap().map(|e| e.unwrap().path()).collect();
        v.sort();
        for e in v {
            collect(&e, out);
        }
    } else {
        out.push(p.to_path_buf());
    }
}

fn reread(paths: &[String]) {
    let mut files = Vec::new();
    for p in paths {
        collect(std::path::Path::new(p), &mut files);
    }
    let _ = std::fs::write("/proc/sys/vm/drop_caches", b"3\n");
    let key = dk(1, INFO_A);
    let base = <HmacSha256 as KeyInit>::new_from_slice(&key).unwrap();
    let mut buf = vec![0u8; 1 << 20];
    let c0 = cpu_secs();
    let t0 = Instant::now();
    let mut bytes = 0u64;
    let mut acc = 0u8;
    for f in &files {
        let mut fh = std::fs::File::open(f).unwrap();
        let mut m = base.clone();
        loop {
            let n = fh.read(&mut buf).unwrap();
            if n == 0 {
                break;
            }
            m.update(&buf[..n]);
            bytes += n as u64;
        }
        acc ^= m.finalize().into_bytes()[0];
    }
    let secs = t0.elapsed().as_secs_f64();
    println!(
        "{{\"cmd\":\"reread\",\"construction\":\"A: HMAC(dk_new, content)\",\"cache\":\"cold (drop_caches attempted)\",\"files\":{},\"bytes\":{},\"secs\":{:.3},\"cpu_secs\":{:.3},\"us_per_file\":{:.1},\"mb_per_s\":{:.1},\"sink\":{}}}",
        files.len(),
        bytes,
        secs,
        cpu_secs() - c0,
        secs * 1e6 / files.len() as f64,
        bytes as f64 / secs / 1e6,
        acc
    );
}

fn main() {
    let a: Vec<String> = std::env::args().collect();
    match a.get(1).map(|s| s.as_str()) {
        Some("build") => build(&a[2], a[3].parse().unwrap()),
        Some("rotate") => rotate(&a[2], a[3].parse().unwrap(), &a[4]),
        Some("derive") => derive(a[2].parse().unwrap()),
        Some("mkfiles") => mkfiles(&a[2], a[3].parse().unwrap(), a[4].parse().unwrap()),
        Some("reread") => reread(&a[2..]),
        _ => {
            eprintln!("see the doc comment at the top of src/main.rs");
            std::process::exit(2)
        }
    }
}
