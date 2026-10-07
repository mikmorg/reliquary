//! Reliquary A1-S1 hash benchmark (THROWAWAY spike code, not production).
//!
//! Measures, on the machine it runs on, the per-byte cost of the candidate dedup-ID
//! constructions from PLAN A1:
//!   C1  SHA-256(content) + HMAC-SHA256(K, content)       two keyed/unkeyed passes over each byte, one read
//!   C2  SHA-256(content), then HMAC-SHA256(K, digest)    one pass per byte (rotatable from the cache)
//!   C3  BLAKE3(content) + keyed_BLAKE3(K, content)        two passes per byte, one read
//!   C4  BLAKE3(content), then keyed_BLAKE3(K, digest)     one pass per byte (rotatable from the cache)
//!   C5  SHA-256(content) + keyed_BLAKE3(K, content)       mixed: SHA-256 kept for integrity
//! plus the single primitives. Output is one JSON object per line on stdout.
//!
//! Modes:
//!   info                          detected CPU features and compiled backends
//!   mem   [MiB] [runs]            in-memory buffer of random bytes (default 1024 MiB, 5 runs)
//!   file  <path> [runs] [cold]    streaming reads (1 MiB buffer; 16 MiB for rayon); "cold" drops caches first
//!   ladder                        per-file cost at small sizes (0 B .. 16 MiB), key setup included
//!   soak  <path> <seconds> [C1|C2]  repeats C2 (default) or C1 over a file for a fixed time, prints MB/s
//!                                 per 10 s window (thermal and battery check on phones; see the OL kit)
//!
//! Optional features `backend-ring` / `backend-awslc` add the workloads ring_sha256, ring_C1,
//! awslc_sha256 and awslc_C1 (same constructions through ring 0.17.14 / aws-lc-rs 1.18.1), so the
//! RustCrypto `sha2` backend can be compared with other SHA-256 code on the same device and ABI.

use hmac::{Hmac, KeyInit, Mac};
use sha2::{Digest, Sha256};
use std::fs::File;
use std::io::Read;
use std::time::{Duration, Instant};

type HmacSha256 = Hmac<Sha256>;

const KEY: [u8; 32] = *b"reliquary-a1-s1-benchmark-key-32";

#[derive(Clone, Copy, Debug)]
enum W {
    ReadOnly,
    Sha256,
    HmacContent,
    C1,
    C2,
    Blake3,
    Blake3Keyed,
    C3,
    C4,
    C5,
    Blake3Rayon,
    C4Rayon,
    #[cfg(feature = "backend-ring")]
    RingSha256,
    #[cfg(feature = "backend-ring")]
    RingC1,
    #[cfg(feature = "backend-awslc")]
    AwsSha256,
    #[cfg(feature = "backend-awslc")]
    AwsC1,
}

impl W {
    fn name(self) -> &'static str {
        match self {
            W::ReadOnly => "read_only",
            W::Sha256 => "sha256",
            W::HmacContent => "hmac_sha256_content",
            W::C1 => "C1_sha256+hmac_sha256_content",
            W::C2 => "C2_sha256_then_hmac_digest",
            W::Blake3 => "blake3",
            W::Blake3Keyed => "blake3_keyed",
            W::C3 => "C3_blake3+keyed_blake3_content",
            W::C4 => "C4_blake3_then_keyed_digest",
            W::C5 => "C5_sha256+keyed_blake3_content",
            W::Blake3Rayon => "blake3_rayon_all_cores",
            W::C4Rayon => "C4_rayon_all_cores",
            #[cfg(feature = "backend-ring")]
            W::RingSha256 => "ring_sha256",
            #[cfg(feature = "backend-ring")]
            W::RingC1 => "ring_C1_sha256+hmac_content",
            #[cfg(feature = "backend-awslc")]
            W::AwsSha256 => "awslc_sha256",
            #[cfg(feature = "backend-awslc")]
            W::AwsC1 => "awslc_C1_sha256+hmac_content",
        }
    }
    fn alt_backends() -> Vec<W> {
        #[allow(unused_mut)]
        let mut v: Vec<W> = Vec::new();
        #[cfg(feature = "backend-ring")]
        v.extend([W::RingSha256, W::RingC1]);
        #[cfg(feature = "backend-awslc")]
        v.extend([W::AwsSha256, W::AwsC1]);
        v
    }
    fn all_mem() -> Vec<W> {
        let mut v = vec![
            W::Sha256,
            W::HmacContent,
            W::C1,
            W::C2,
            W::Blake3,
            W::Blake3Keyed,
            W::C3,
            W::C4,
            W::C5,
            W::Blake3Rayon,
            W::C4Rayon,
        ];
        v.extend(W::alt_backends());
        v
    }
    fn rayon(self) -> bool {
        matches!(self, W::Blake3Rayon | W::C4Rayon)
    }
}

/// Streaming state for one workload over one "file".
enum St {
    None(u64),
    Sha(Sha256),
    Hm(HmacSha256),
    ShaHm(Sha256, HmacSha256),
    B3(blake3::Hasher),
    B3B3(blake3::Hasher, blake3::Hasher),
    ShaB3(Sha256, blake3::Hasher),
    B3R(blake3::Hasher),
    #[cfg(feature = "backend-ring")]
    Ring(ring::digest::Context, Option<ring::hmac::Context>),
    #[cfg(feature = "backend-awslc")]
    Aws(aws_lc_rs::digest::Context, Option<aws_lc_rs::hmac::Context>),
}

fn start(w: W) -> St {
    let hm = || <HmacSha256 as KeyInit>::new_from_slice(&KEY).unwrap();
    match w {
        W::ReadOnly => St::None(0),
        W::Sha256 | W::C2 => St::Sha(Sha256::new()),
        W::HmacContent => St::Hm(hm()),
        W::C1 => St::ShaHm(Sha256::new(), hm()),
        W::Blake3 | W::C4 => St::B3(blake3::Hasher::new()),
        W::Blake3Keyed => St::B3(blake3::Hasher::new_keyed(&KEY)),
        W::C3 => St::B3B3(blake3::Hasher::new(), blake3::Hasher::new_keyed(&KEY)),
        W::C5 => St::ShaB3(Sha256::new(), blake3::Hasher::new_keyed(&KEY)),
        W::Blake3Rayon | W::C4Rayon => St::B3R(blake3::Hasher::new()),
        #[cfg(feature = "backend-ring")]
        W::RingSha256 | W::RingC1 => St::Ring(
            ring::digest::Context::new(&ring::digest::SHA256),
            matches!(w, W::RingC1).then(|| ring::hmac::Context::with_key(&ring::hmac::Key::new(ring::hmac::HMAC_SHA256, &KEY))),
        ),
        #[cfg(feature = "backend-awslc")]
        W::AwsSha256 | W::AwsC1 => St::Aws(
            aws_lc_rs::digest::Context::new(&aws_lc_rs::digest::SHA256),
            matches!(w, W::AwsC1).then(|| aws_lc_rs::hmac::Context::with_key(&aws_lc_rs::hmac::Key::new(aws_lc_rs::hmac::HMAC_SHA256, &KEY))),
        ),
    }
}

fn update(s: &mut St, buf: &[u8]) {
    match s {
        St::None(acc) => {
            // touch one byte per 4 KiB so the read cannot be optimised away
            let mut a = *acc;
            for i in (0..buf.len()).step_by(4096) {
                a = a.wrapping_add(buf[i] as u64);
            }
            *acc = a;
        }
        St::Sha(h) => h.update(buf),
        St::Hm(m) => m.update(buf),
        St::ShaHm(h, m) => {
            h.update(buf);
            m.update(buf);
        }
        St::B3(h) => {
            h.update(buf);
        }
        St::B3B3(a, b) => {
            a.update(buf);
            b.update(buf);
        }
        St::ShaB3(h, b) => {
            h.update(buf);
            b.update(buf);
        }
        St::B3R(h) => {
            h.update_rayon(buf);
        }
        #[cfg(feature = "backend-ring")]
        St::Ring(h, m) => {
            h.update(buf);
            if let Some(m) = m {
                m.update(buf);
            }
        }
        #[cfg(feature = "backend-awslc")]
        St::Aws(h, m) => {
            h.update(buf);
            if let Some(m) = m {
                m.update(buf);
            }
        }
    }
}

/// Finish and return the 32-byte "ID" so the work is observable.
fn finish(w: W, s: St) -> [u8; 32] {
    let hm = || <HmacSha256 as KeyInit>::new_from_slice(&KEY).unwrap();
    match (w, s) {
        (_, St::None(a)) => {
            let mut o = [0u8; 32];
            o[..8].copy_from_slice(&a.to_le_bytes());
            o
        }
        (W::C2, St::Sha(h)) => {
            let d = h.finalize();
            let mut m = hm();
            m.update(&d);
            m.finalize().into_bytes().into()
        }
        (_, St::Sha(h)) => h.finalize().into(),
        (_, St::Hm(m)) => m.finalize().into_bytes().into(),
        (_, St::ShaHm(h, m)) => {
            let a: [u8; 32] = h.finalize().into();
            let b: [u8; 32] = m.finalize().into_bytes().into();
            xor(a, b)
        }
        (W::C4, St::B3(h)) | (W::C4Rayon, St::B3R(h)) => {
            let d = h.finalize();
            *blake3::keyed_hash(&KEY, d.as_bytes()).as_bytes()
        }
        (_, St::B3(h)) | (_, St::B3R(h)) => *h.finalize().as_bytes(),
        (_, St::B3B3(a, b)) => xor(*a.finalize().as_bytes(), *b.finalize().as_bytes()),
        (_, St::ShaB3(h, b)) => xor(h.finalize().into(), *b.finalize().as_bytes()),
        #[cfg(feature = "backend-ring")]
        (_, St::Ring(h, m)) => {
            let mut a = [0u8; 32];
            a.copy_from_slice(h.finish().as_ref());
            match m {
                Some(m) => {
                    let mut b = [0u8; 32];
                    b.copy_from_slice(m.sign().as_ref());
                    xor(a, b)
                }
                None => a,
            }
        }
        #[cfg(feature = "backend-awslc")]
        (_, St::Aws(h, m)) => {
            let mut a = [0u8; 32];
            a.copy_from_slice(h.finish().as_ref());
            match m {
                Some(m) => {
                    let mut b = [0u8; 32];
                    b.copy_from_slice(m.sign().as_ref());
                    xor(a, b)
                }
                None => a,
            }
        }
    }
}

fn xor(a: [u8; 32], b: [u8; 32]) -> [u8; 32] {
    let mut o = [0u8; 32];
    for i in 0..32 {
        o[i] = a[i] ^ b[i];
    }
    o
}

#[cfg(not(unix))]
fn cpu_secs() -> f64 {
    f64::NAN // not measured on this OS; wall-clock MB/s is still reported
}

#[cfg(unix)]
fn cpu_secs() -> f64 {
    unsafe {
        let mut ru: libc::rusage = std::mem::zeroed();
        libc::getrusage(libc::RUSAGE_SELF, &mut ru);
        let t = |tv: libc::timeval| tv.tv_sec as f64 + tv.tv_usec as f64 / 1e6;
        t(ru.ru_utime) + t(ru.ru_stime)
    }
}

fn num3(x: f64) -> String {
    if x.is_finite() { format!("{:.3}", x) } else { "null".to_string() }
}

fn median(v: &mut Vec<f64>) -> f64 {
    v.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let n = v.len();
    if n % 2 == 1 {
        v[n / 2]
    } else {
        (v[n / 2 - 1] + v[n / 2]) / 2.0
    }
}

/// xorshift64* filled buffer (incompressible enough for hashing; hash speed is data-independent anyway)
fn random_buf(len: usize) -> Vec<u8> {
    let mut v = vec![0u8; len];
    let mut x: u64 = 0x9E3779B97F4A7C15;
    for c in v.chunks_mut(8) {
        x ^= x >> 12;
        x ^= x << 25;
        x ^= x >> 27;
        let r = x.wrapping_mul(0x2545F4914F6CDD1D).to_le_bytes();
        c.copy_from_slice(&r[..c.len()]);
    }
    v
}

fn info() {
    let mut feats: Vec<String> = Vec::new();
    #[cfg(any(target_arch = "x86_64", target_arch = "x86"))]
    {
        for (n, b) in [
            ("sha", std::is_x86_feature_detected!("sha")),
            ("sse4.1", std::is_x86_feature_detected!("sse4.1")),
            ("avx2", std::is_x86_feature_detected!("avx2")),
            ("avx512f", std::is_x86_feature_detected!("avx512f")),
            ("avx512vl", std::is_x86_feature_detected!("avx512vl")),
        ] {
            feats.push(format!("\"{}\":{}", n, b));
        }
    }
    #[cfg(target_arch = "aarch64")]
    {
        for (n, b) in [
            ("neon", std::arch::is_aarch64_feature_detected!("neon")),
            ("sha2", std::arch::is_aarch64_feature_detected!("sha2")),
            ("aes", std::arch::is_aarch64_feature_detected!("aes")),
        ] {
            feats.push(format!("\"{}\":{}", n, b));
        }
    }
    // Raw ELF auxv words, so 32-bit (AArch32) processes can be classified too: on a 32-bit ARM
    // process, HWCAP2 bit 3 is HWCAP2_SHA2 (Linux arch/arm uapi hwcap.h). On AArch64, HWCAP bit 6
    // is HWCAP_SHA2 (Documentation/arch/arm64/elf_hwcaps.rst). Interpretation is left to the kit.
    #[cfg(any(target_os = "linux", target_os = "android"))]
    {
        let (h1, h2) = unsafe { (libc::getauxval(libc::AT_HWCAP), libc::getauxval(libc::AT_HWCAP2)) };
        feats.push(format!("\"at_hwcap\":\"{:#x}\",\"at_hwcap2\":\"{:#x}\"", h1, h2));
    }
    let backends: Vec<String> = W::alt_backends().iter().map(|w| format!("\"{}\"", w.name())).collect();
    let sha_soft = cfg!(any(sha2_backend = "soft", sha2_256_backend = "soft"));
    let b3_features = [
        ("pure", cfg!(feature = "blake3-pure")),
        ("portable_no_simd", cfg!(feature = "blake3-portable")),
        ("no_avx512", cfg!(feature = "blake3-no-avx512")),
        ("sse41_only", cfg!(feature = "blake3-sse41-only")),
    ];
    let b3: Vec<String> = b3_features
        .iter()
        .filter(|(_, b)| *b)
        .map(|(n, _)| format!("\"{}\"", n))
        .collect();
    println!(
        "{{\"mode\":\"info\",\"arch\":\"{}\",\"os\":\"{}\",\"threads\":{},\"cpu_features\":{{{}}},\"sha2_forced_soft\":{},\"blake3_features\":[{}],\"alt_backends\":[{}],\"target_pointer_width\":{}}}",
        std::env::consts::ARCH,
        std::env::consts::OS,
        std::thread::available_parallelism().map(|n| n.get()).unwrap_or(1),
        feats.join(","),
        sha_soft,
        b3.join(","),
        backends.join(","),
        std::mem::size_of::<usize>() * 8
    );
}

fn mem(mib: usize, runs: usize) {
    let buf = random_buf(mib << 20);
    let chunk = 1 << 20;
    for w in W::all_mem() {
        let ch = if w.rayon() { 16 << 20 } else { chunk };
        let mut rates = Vec::new();
        let mut cpg = Vec::new();
        let mut sink = 0u8;
        // one warm-up run
        for r in 0..=runs {
            let c0 = cpu_secs();
            let t0 = Instant::now();
            let mut s = start(w);
            for c in buf.chunks(ch) {
                update(&mut s, c);
            }
            let id = finish(w, s);
            let dt = t0.elapsed().as_secs_f64();
            let dc = cpu_secs() - c0;
            sink ^= id[0];
            if r > 0 {
                rates.push(buf.len() as f64 / dt / 1e6);
                cpg.push(dc / (buf.len() as f64 / 1e9));
            }
        }
        let mn = rates.iter().cloned().fold(f64::INFINITY, f64::min);
        let mx = rates.iter().cloned().fold(0.0, f64::max);
        println!(
            "{{\"mode\":\"mem\",\"workload\":\"{}\",\"bytes\":{},\"runs\":{},\"mb_per_s_median\":{:.0},\"mb_per_s_min\":{:.0},\"mb_per_s_max\":{:.0},\"cpu_s_per_gb_median\":{},\"sink\":{}}}",
            w.name(),
            buf.len(),
            runs,
            median(&mut rates),
            mn,
            mx,
            num3(median(&mut cpg)),
            sink
        );
    }
}

#[cfg(not(unix))]
fn drop_caches(_path: &str) -> bool {
    false // no-op on this OS: "cold" runs read from the OS file cache
}

#[cfg(unix)]
fn drop_caches(path: &str) -> bool {
    // Try the global knob (needs root); always also fadvise DONTNEED on the file.
    unsafe { libc::sync() };
    let global = std::fs::write("/proc/sys/vm/drop_caches", b"3\n").is_ok();
    if let Ok(f) = File::open(path) {
        use std::os::unix::io::AsRawFd;
        unsafe {
            libc::posix_fadvise(f.as_raw_fd(), 0, 0, libc::POSIX_FADV_DONTNEED);
        }
    }
    global
}

fn file_mode(path: &str, runs: usize, cold: bool) {
    let len = std::fs::metadata(path).unwrap().len();
    let mut ws = vec![W::ReadOnly];
    ws.extend([W::C1, W::C2, W::C3, W::C4, W::C5, W::C4Rayon]);
    ws.extend(W::alt_backends());
    for w in ws {
        let ch = if w.rayon() { 16 << 20 } else { 1 << 20 };
        let mut buf = vec![0u8; ch];
        let mut rates = Vec::new();
        let mut cpg = Vec::new();
        let mut dropped = false;
        for _ in 0..runs {
            if cold {
                dropped = drop_caches(path);
            }
            let c0 = cpu_secs();
            let t0 = Instant::now();
            let mut f = File::open(path).unwrap();
            let mut s = start(w);
            loop {
                let n = f.read(&mut buf).unwrap();
                if n == 0 {
                    break;
                }
                update(&mut s, &buf[..n]);
            }
            let _id = finish(w, s);
            let dt = t0.elapsed().as_secs_f64();
            let dc = cpu_secs() - c0;
            rates.push(len as f64 / dt / 1e6);
            cpg.push(dc / (len as f64 / 1e9));
        }
        println!(
            "{{\"mode\":\"file\",\"cache\":\"{}\",\"global_drop_caches_ok\":{},\"workload\":\"{}\",\"bytes\":{},\"runs\":{},\"read_buf\":{},\"mb_per_s_median\":{:.0},\"cpu_s_per_gb_median\":{}}}",
            if cold { "cold" } else { "warm" },
            dropped,
            w.name(),
            len,
            runs,
            ch,
            median(&mut rates),
            num3(median(&mut cpg))
        );
    }
}

fn ladder() {
    let sizes: [usize; 8] = [0, 1, 1024, 4096, 65536, 1 << 20, 4 << 20, 16 << 20];
    let big = random_buf(16 << 20);
    for &sz in &sizes {
        let data = &big[..sz];
        for w in [W::C1, W::C2, W::C3, W::C4, W::C5] {
            // pick iterations so each sample takes >= ~0.2 s
            let mut iters = 1usize;
            loop {
                let t0 = Instant::now();
                for _ in 0..iters {
                    let mut s = start(w);
                    update(&mut s, data);
                    std::hint::black_box(finish(w, s));
                }
                if t0.elapsed() >= Duration::from_millis(200) {
                    break;
                }
                iters *= 2;
            }
            let mut ns = Vec::new();
            for _ in 0..5 {
                let t0 = Instant::now();
                for _ in 0..iters {
                    let mut s = start(w);
                    update(&mut s, data);
                    std::hint::black_box(finish(w, s));
                }
                ns.push(t0.elapsed().as_nanos() as f64 / iters as f64);
            }
            let m = median(&mut ns);
            let mbps = if sz == 0 { 0.0 } else { sz as f64 / (m / 1e9) / 1e6 };
            println!(
                "{{\"mode\":\"ladder\",\"workload\":\"{}\",\"size\":{},\"ns_per_file_median\":{:.0},\"mb_per_s\":{:.0}}}",
                w.name(),
                sz,
                m,
                mbps
            );
        }
    }
}

fn soak(path: &str, secs: u64, w: W) {
    let len = std::fs::metadata(path).unwrap().len();
    let mut buf = vec![0u8; 1 << 20];
    let t_end = Instant::now() + Duration::from_secs(secs);
    let mut win_start = Instant::now();
    let mut win_bytes = 0u64;
    let t0 = Instant::now();
    while Instant::now() < t_end {
        let mut f = File::open(path).unwrap();
        let mut s = start(w);
        loop {
            let n = f.read(&mut buf).unwrap();
            if n == 0 {
                break;
            }
            update(&mut s, &buf[..n]);
            win_bytes += n as u64;
            if win_start.elapsed() >= Duration::from_secs(10) {
                println!(
                    "{{\"mode\":\"soak\",\"workload\":\"{}\",\"t_s\":{:.0},\"mb_per_s\":{:.0}}}",
                    w.name(),
                    t0.elapsed().as_secs_f64(),
                    win_bytes as f64 / win_start.elapsed().as_secs_f64() / 1e6
                );
                win_start = Instant::now();
                win_bytes = 0;
            }
        }
        std::hint::black_box(finish(w, s));
        let _ = len;
    }
}

fn main() {
    let a: Vec<String> = std::env::args().collect();
    let arg = |i: usize| a.get(i).map(|s| s.as_str());
    match arg(1) {
        Some("info") => info(),
        Some("mem") => {
            info();
            let mib = arg(2).map(|s| s.parse().unwrap()).unwrap_or(1024);
            let runs = arg(3).map(|s| s.parse().unwrap()).unwrap_or(5);
            mem(mib, runs)
        }
        Some("file") => {
            info();
            let p = arg(2).expect("path");
            let runs = arg(3).map(|s| s.parse().unwrap()).unwrap_or(3);
            let cold = arg(4) == Some("cold");
            file_mode(p, runs, cold)
        }
        Some("ladder") => {
            info();
            ladder()
        }
        Some("soak") => {
            info();
            let w = match arg(4) {
                None | Some("C2") => W::C2,
                Some("C1") => W::C1,
                Some(o) => panic!("soak workload must be C1 or C2, got {o}"),
            };
            soak(arg(2).expect("path"), arg(3).map(|s| s.parse().unwrap()).unwrap_or(600), w)
        }
        _ => {
            eprintln!("usage: a1-hashbench info | mem [MiB] [runs] | file <path> [runs] [cold] | ladder | soak <path> <secs> [C1|C2]");
            std::process::exit(2)
        }
    }
}
