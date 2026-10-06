//! Reliquary A1-S3: dedup-ID test vectors, Rust reference (THROWAWAY spike code).
//!
//! The constructions and the text encoding here are CANDIDATES for ADR-0006, written down so
//! that two independent implementations can be checked against each other. They are not a
//! decision. See README.md.
//!
//!   A  dk = HKDF-SHA256(ikm=K_e, salt=empty, info="reliquary/v1/dedup-key")              id = HMAC-SHA256(dk, content)
//!      (info string identical to the content-encryption spike, format note section 6)
//!   B  dk = HKDF-SHA256(ikm=K_e, salt=empty, info="reliquary/v1/dedup-key/sha256-digest") id = HMAC-SHA256(dk, SHA-256(content))
//!   C  dk = BLAKE3-derive_key("reliquary 2026-09-29 dedup-id keyed-blake3 content v1", K_e)        id = BLAKE3-keyed(dk, content)
//!   D  dk = BLAKE3-derive_key("reliquary 2026-09-29 dedup-id keyed-blake3 blake3-digest v1", K_e)  id = BLAKE3-keyed(dk, BLAKE3(content))
//!
//!   Text form (candidate): "rq1-" <construction a|b|c|d> "-e" <epoch, decimal, no leading zeros> "-"
//!   <RFC 4648 base32, lowercase, no padding, 52 chars; the last char's 4 unused bits must be zero>
//!
//! Usage:
//!   a1-vectors gen                       > vectors.json
//!   a1-vectors verify <vectors.json>     recompute every vector and run every parse negative
//!   a1-vectors blake3-official <test_vectors.json>   check the blake3 crate against the official vectors

use hkdf::Hkdf;
use hmac::{Hmac, KeyInit, Mac};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};

type HmacSha256 = Hmac<Sha256>;

const INFO_A: &str = "reliquary/v1/dedup-key";
const INFO_B: &str = "reliquary/v1/dedup-key/sha256-digest";
const CTX_C: &str = "reliquary 2026-09-29 dedup-id keyed-blake3 content v1";
const CTX_D: &str = "reliquary 2026-09-29 dedup-id keyed-blake3 blake3-digest v1";
const B32: &[u8; 32] = b"abcdefghijklmnopqrstuvwxyz234567";

fn k(epoch: u32) -> [u8; 32] {
    // Test secrets only: K_0 = 00 01 .. 1f, K_1 = 20 21 .. 3f.
    let mut o = [0u8; 32];
    for (i, b) in o.iter_mut().enumerate() {
        *b = (i as u32 + 32 * epoch) as u8;
    }
    o
}

fn hkdf32(ikm: &[u8], info: &str) -> [u8; 32] {
    let mut o = [0u8; 32];
    Hkdf::<Sha256>::new(None, ikm).expand(info.as_bytes(), &mut o).unwrap();
    o
}

fn hmac32(key: &[u8], msg: &[u8]) -> [u8; 32] {
    let mut m = <HmacSha256 as KeyInit>::new_from_slice(key).unwrap();
    m.update(msg);
    m.finalize().into_bytes().into()
}

fn b32(bytes: &[u8]) -> String {
    let mut out = String::new();
    let mut acc: u32 = 0;
    let mut nbits = 0;
    for &b in bytes {
        acc = (acc << 8) | b as u32;
        nbits += 8;
        while nbits >= 5 {
            nbits -= 5;
            out.push(B32[((acc >> nbits) & 31) as usize] as char);
        }
    }
    if nbits > 0 {
        out.push(B32[((acc << (5 - nbits)) & 31) as usize] as char);
    }
    out
}

fn text(c: char, epoch: u32, id: &[u8; 32]) -> String {
    format!("rq1-{}-e{}-{}", c, epoch, b32(id))
}

/// Strict parser for the candidate text form. Returns (construction, epoch, 32 raw bytes).
fn parse(s: &str) -> Result<(char, u32, [u8; 32]), &'static str> {
    let rest = s.strip_prefix("rq1-").ok_or("bad-version-prefix")?;
    let mut it = rest.splitn(3, '-');
    let c = it.next().ok_or("missing-construction")?;
    let e = it.next().ok_or("missing-epoch")?;
    let body = it.next().ok_or("missing-body")?;
    if !matches!(c, "a" | "b" | "c" | "d") {
        return Err("unknown-construction");
    }
    let e = e.strip_prefix('e').ok_or("bad-epoch")?;
    if e.is_empty() || e.len() > 9 || !e.bytes().all(|b| b.is_ascii_digit()) || (e.len() > 1 && e.starts_with('0')) {
        return Err("bad-epoch");
    }
    let epoch: u32 = e.parse().map_err(|_| "bad-epoch")?;
    if body.len() != 52 {
        return Err("bad-length");
    }
    let mut acc: u64 = 0;
    let mut nbits = 0;
    let mut out = Vec::with_capacity(32);
    for (i, ch) in body.bytes().enumerate() {
        let v = B32.iter().position(|&x| x == ch).ok_or("bad-character")? as u64;
        acc = (acc << 5) | v;
        nbits += 5;
        if nbits >= 8 {
            nbits -= 8;
            out.push((acc >> nbits) as u8);
            acc &= (1 << nbits) - 1;
        }
        if i == 51 && acc != 0 {
            return Err("non-canonical-trailing-bits");
        }
    }
    let mut id = [0u8; 32];
    id.copy_from_slice(&out[..32]);
    Ok((c.chars().next().unwrap(), epoch, id))
}

/// Streams the content of a vector: "abc" (ASCII) or the pattern byte[i] = i mod 251.
fn feed(content: &str, len: u64, mut f: impl FnMut(&[u8])) {
    if content == "ascii:abc" {
        f(b"abc");
        return;
    }
    assert_eq!(content, "pattern-mod-251");
    let block: Vec<u8> = (0..251u32 * 4096).map(|i| (i % 251) as u8).collect();
    let mut left = len;
    while left > 0 {
        let n = left.min(block.len() as u64) as usize;
        f(&block[..n]);
        left -= n as u64;
    }
}

struct Ids {
    sha256: [u8; 32],
    blake3: [u8; 32],
    a: [u8; 32],
    b: [u8; 32],
    c: [u8; 32],
    d: [u8; 32],
}

fn compute(content: &str, len: u64, epoch: u32) -> Ids {
    let ke = k(epoch);
    let dka = hkdf32(&ke, INFO_A);
    let dkb = hkdf32(&ke, INFO_B);
    let dkc = blake3::derive_key(CTX_C, &ke);
    let dkd = blake3::derive_key(CTX_D, &ke);
    let mut sha = Sha256::new();
    let mut ma = <HmacSha256 as KeyInit>::new_from_slice(&dka).unwrap();
    let mut b3 = blake3::Hasher::new();
    let mut kc = blake3::Hasher::new_keyed(&dkc);
    feed(content, len, |buf| {
        sha.update(buf);
        ma.update(buf);
        b3.update(buf);
        kc.update(buf);
    });
    let sha256: [u8; 32] = sha.finalize().into();
    let blake3v: [u8; 32] = *b3.finalize().as_bytes();
    Ids {
        sha256,
        blake3: blake3v,
        a: ma.finalize().into_bytes().into(),
        b: hmac32(&dkb, &sha256),
        c: *kc.finalize().as_bytes(),
        d: *blake3::keyed_hash(&dkd, &blake3v).as_bytes(),
    }
}

fn h(x: &[u8]) -> String {
    hex::encode(x)
}

fn gen() {
    let mut vectors: Vec<Value> = Vec::new();
    let mut n = 0;
    let mut next_id = |p: &str| {
        n += 1;
        format!("{}{:02}", p, n)
    };

    // Positive content vectors, epoch 0 (plus a few at epoch 1).
    let mut cases: Vec<(&str, u64, u32, &str)> = vec![
        ("pattern-mod-251", 0, 0, "empty file"),
        ("pattern-mod-251", 1, 0, "one byte"),
        ("ascii:abc", 3, 0, "ASCII \"abc\"; SHA-256 equals the widely published FIPS 180 example value"),
        ("pattern-mod-251", 55, 0, "SHA-256: longest single-block message"),
        ("pattern-mod-251", 56, 0, "SHA-256: padding spills into a second block"),
        ("pattern-mod-251", 63, 0, "SHA-256 block boundary - 1"),
        ("pattern-mod-251", 64, 0, "SHA-256 block boundary"),
        ("pattern-mod-251", 65, 0, "SHA-256 block boundary + 1"),
        ("pattern-mod-251", 1023, 0, "BLAKE3 chunk boundary - 1"),
        ("pattern-mod-251", 1024, 0, "BLAKE3 chunk boundary"),
        ("pattern-mod-251", 1025, 0, "BLAKE3 chunk boundary + 1"),
        ("pattern-mod-251", 2048, 0, "two BLAKE3 chunks"),
        ("pattern-mod-251", 2049, 0, "two BLAKE3 chunks + 1"),
        ("pattern-mod-251", 4095, 0, "page - 1"),
        ("pattern-mod-251", 4096, 0, "page"),
        ("pattern-mod-251", 65536, 0, "64 KiB (age STREAM chunk size)"),
        ("pattern-mod-251", 100000, 0, "streaming check: implementations should also feed this in irregular pieces"),
        ("pattern-mod-251", 1048576, 0, "1 MiB"),
        ("pattern-mod-251", 4194303, 0, "Dropbox block size - 1"),
        ("pattern-mod-251", 4194304, 0, "Dropbox block size (4 MiB)"),
        ("pattern-mod-251", 4194305, 0, "Dropbox block size + 1"),
        ("pattern-mod-251", 4294967295, 0, "2^32 - 1 bytes (32-bit length counters)"),
        ("pattern-mod-251", 4294967296, 0, "exactly 4 GiB"),
        ("pattern-mod-251", 4294967297, 0, "4 GiB + 1 (> 4 GiB)"),
    ];
    cases.extend([
        ("pattern-mod-251", 0, 1, "empty file, epoch 1"),
        ("pattern-mod-251", 1024, 1, "1024 bytes, epoch 1"),
        ("pattern-mod-251", 4194305, 1, "4 MiB + 1, epoch 1"),
    ]);
    let mut cache = std::collections::HashMap::new();
    for (content, len, epoch, note) in cases {
        eprintln!("computing {} len={} epoch={}", content, len, epoch);
        let ids = compute(content, len, epoch);
        vectors.push(json!({
            "id": next_id("P"), "kind": "positive", "note": note,
            "content": content, "length": len, "epoch": epoch,
            "sha256": h(&ids.sha256), "blake3": h(&ids.blake3),
            "id_a": h(&ids.a), "id_b": h(&ids.b), "id_c": h(&ids.c), "id_d": h(&ids.d),
            "text_a": text('a', epoch, &ids.a), "text_b": text('b', epoch, &ids.b),
            "text_c": text('c', epoch, &ids.c), "text_d": text('d', epoch, &ids.d),
        }));
        cache.insert((content, len, epoch), ids);
    }

    // Domain-separation negatives: "expected" must be produced, "forbidden" must not.
    let k0 = k(0);
    let x = &cache[&("pattern-mod-251", 1024u64, 0u32)];
    let x0 = &cache[&("pattern-mod-251", 1024u64, 1u32)];
    let dka = hkdf32(&k0, INFO_A);
    let dkb = hkdf32(&k0, INFO_B);
    let dkc = blake3::derive_key(CTX_C, &k0);
    let dkd = blake3::derive_key(CTX_D, &k0);
    let negs: Vec<(&str, &str, [u8; 32], [u8; 32])> = vec![
        ("id_b", "B must not equal A computed over a file whose bytes are SHA-256(X): construction A and B use different derived keys (shared key => collision)", x.b, hmac32(&dka, &x.sha256)),
        ("id_d", "D must not equal C computed over a file whose bytes are BLAKE3(X): C and D use different derive_key contexts", x.d, *blake3::keyed_hash(&dkc, &x.blake3).as_bytes()),
        ("id_a", "A must use the HKDF-derived key, not K_e directly as the HMAC key", x.a, {
            let mut m = <HmacSha256 as KeyInit>::new_from_slice(&k0).unwrap();
            feed("pattern-mod-251", 1024, |b| m.update(b));
            m.finalize().into_bytes().into()
        }),
        ("id_b", "B must MAC the 32-byte binary SHA-256 digest, not its 64-character hex text", x.b, hmac32(&dkb, h(&x.sha256).as_bytes())),
        ("id_b", "B must use the HKDF-derived key, not K_e directly", x.b, hmac32(&k0, &x.sha256)),
        ("id_c", "C must use the derive_key output, not K_e directly as the BLAKE3 key", x.c, {
            let mut hsh = blake3::Hasher::new_keyed(&k0);
            feed("pattern-mod-251", 1024, |b| { hsh.update(b); });
            *hsh.finalize().as_bytes()
        }),
        ("id_d", "D must MAC the 32-byte binary BLAKE3 digest, not its hex text", x.d, *blake3::keyed_hash(&dkd, h(&x.blake3).as_bytes()).as_bytes()),
        ("id_b", "An epoch-0 ID must differ from the epoch-1 ID of the same content", x.b, x0.b),
        ("id_b", "B is keyed: it must not equal the unkeyed SHA-256", x.b, x.sha256),
        ("id_a", "HKDF info is versioned: \"reliquary/v2/dedup-key\" gives a different key", x.a, {
            let dk2 = hkdf32(&k0, "reliquary/v2/dedup-key");
            let mut m = <HmacSha256 as KeyInit>::new_from_slice(&dk2).unwrap();
            feed("pattern-mod-251", 1024, |b| m.update(b));
            m.finalize().into_bytes().into()
        }),
    ];
    for (field, note, expected, forbidden) in negs {
        assert_ne!(expected, forbidden, "{}", note);
        vectors.push(json!({
            "id": next_id("N"), "kind": "domain-separation-negative", "note": note,
            "content": "pattern-mod-251", "length": 1024, "epoch": 0,
            "field": field, "expected": h(&expected), "forbidden": h(&forbidden),
        }));
    }

    // Encoding negatives: a strict parser must reject each string with the given reason.
    let good = text('b', 0, &x.b);
    let body = &good["rq1-b-e0-".len()..];
    let last = body.chars().last().unwrap();
    let noncanon = {
        let mut s = good.clone();
        s.pop();
        s.push(if last == 'a' { 'b' } else { 'r' });
        s
    };
    let encs: Vec<(String, &str, &str)> = vec![
        (good.to_uppercase(), "bad-version-prefix", "upper case (case-insensitive file systems: only lower case is canonical)"),
        ({
            let i = body.find(|ch: char| ch.is_ascii_lowercase()).unwrap();
            format!("rq1-b-e0-{}{}{}", &body[..i], body[i..i + 1].to_uppercase(), &body[i + 1..])
        }, "bad-character", "one upper-case character in the body"),
        (format!("{}====", good), "bad-length", "RFC 4648 padding is not allowed"),
        (good[..good.len() - 1].to_string(), "bad-length", "51 body characters"),
        (format!("{}a", good), "bad-length", "53 body characters"),
        (noncanon, "non-canonical-trailing-bits", "last character carries non-zero unused bits (two strings would decode to the same bytes)"),
        (format!("rq1-b-e0-1{}", &body[1..]), "bad-character", "'1' is not in the RFC 4648 base32 alphabet"),
        (good.replacen("rq1-", "rq2-", 1), "bad-version-prefix", "unknown version"),
        (good.replacen("-b-", "-x-", 1), "unknown-construction", "unknown construction letter"),
        (good.replacen("-e0-", "-e00-", 1), "bad-epoch", "epoch with a leading zero"),
        (good.replacen("-e0-", "-e-", 1), "bad-epoch", "empty epoch"),
        (format!("rq1-b-e0-{}", h(&x.b)), "bad-length", "hex body instead of base32"),
        (format!("{}\n", good), "bad-length", "trailing newline"),
        (format!("{}.", good), "bad-length", "trailing dot (Windows strips it from file names)"),
    ];
    for (s, reason, note) in encs {
        assert_eq!(parse(&s).err(), Some(reason), "{}", note);
        vectors.push(json!({
            "id": next_id("E"), "kind": "encoding-negative", "note": note,
            "text": s, "reject_reason": reason,
        }));
    }

    let doc = json!({
        "title": "Reliquary A1-S3 dedup-ID vectors (CANDIDATE constructions, not normative)",
        "generated_by": "spikes/A1-S3/rust (Rust: sha2 0.11.0, hmac 0.13.0, hkdf 0.13.0, blake3 1.8.7)",
        "generated_on": "2026-09-29",
        "content_rules": {
            "pattern-mod-251": "byte i of the input is (i mod 251), i counted from 0, as in the official BLAKE3 test vectors",
            "ascii:abc": "the 3 ASCII bytes 61 62 63"
        },
        "secrets": { "K_0": h(&k(0)), "K_1": h(&k(1)), "note": "test values only" },
        "constructions": {
            "a": format!("dk = HKDF-SHA256(ikm=K_e, salt=empty, info=\"{}\"); id = HMAC-SHA256(dk, content)", INFO_A),
            "b": format!("dk = HKDF-SHA256(ikm=K_e, salt=empty, info=\"{}\"); id = HMAC-SHA256(dk, SHA-256(content))", INFO_B),
            "c": format!("dk = BLAKE3 derive_key(context=\"{}\", key_material=K_e); id = BLAKE3 keyed_hash(dk, content)", CTX_C),
            "d": format!("dk = BLAKE3 derive_key(context=\"{}\", key_material=K_e); id = BLAKE3 keyed_hash(dk, BLAKE3(content))", CTX_D)
        },
        "text_form": "rq1-<a|b|c|d>-e<epoch: decimal, no leading zeros>-<RFC 4648 base32 alphabet a-z2-7, lower case, no padding, 52 chars; unused low 4 bits of the last char are zero>",
        "vectors": vectors,
    });
    println!("{}", serde_json::to_string_pretty(&doc).unwrap());
}

fn verify(path: &str) {
    let doc: Value = serde_json::from_str(&std::fs::read_to_string(path).unwrap()).unwrap();
    let (mut pass, mut fail) = (0, 0);
    for v in doc["vectors"].as_array().unwrap() {
        let ok = match v["kind"].as_str().unwrap() {
            "positive" => {
                let ids = compute(v["content"].as_str().unwrap(), v["length"].as_u64().unwrap(), v["epoch"].as_u64().unwrap() as u32);
                let e = v["epoch"].as_u64().unwrap() as u32;
                let mut ok = h(&ids.sha256) == v["sha256"] && h(&ids.blake3) == v["blake3"];
                for (c, idv) in [('a', ids.a), ('b', ids.b), ('c', ids.c), ('d', ids.d)] {
                    ok &= h(&idv) == v[format!("id_{}", c)];
                    let t = text(c, e, &idv);
                    ok &= t == v[format!("text_{}", c)];
                    ok &= parse(&t) == Ok((c, e, idv));
                }
                ok
            }
            "domain-separation-negative" => {
                let ids = compute("pattern-mod-251", 1024, 0);
                let f = v["field"].as_str().unwrap();
                let got = match f { "id_a" => ids.a, "id_b" => ids.b, "id_c" => ids.c, _ => ids.d };
                h(&got) == v["expected"] && h(&got) != v["forbidden"]
            }
            "encoding-negative" => parse(v["text"].as_str().unwrap()).err() == v["reject_reason"].as_str(),
            _ => false,
        };
        if ok { pass += 1 } else { fail += 1; eprintln!("FAIL {}", v["id"]) }
    }
    println!("{{\"impl\":\"rust\",\"pass\":{},\"fail\":{}}}", pass, fail);
    if fail > 0 { std::process::exit(1) }
}

fn blake3_official(path: &str) {
    let doc: Value = serde_json::from_str(&std::fs::read_to_string(path).unwrap()).unwrap();
    let key: [u8; 32] = doc["key"].as_str().unwrap().as_bytes().try_into().unwrap();
    let ctx = doc["context_string"].as_str().unwrap();
    let (mut pass, mut fail) = (0, 0);
    for c in doc["cases"].as_array().unwrap() {
        let len = c["input_len"].as_u64().unwrap() as usize;
        let input: Vec<u8> = (0..len).map(|i| (i % 251) as u8).collect();
        let mut out = [0u8; 131];
        let mut ok = true;
        let mut r = blake3::Hasher::new().update(&input).finalize_xof();
        r.fill(&mut out);
        ok &= h(&out) == c["hash"];
        let mut r = blake3::Hasher::new_keyed(&key).update(&input).finalize_xof();
        r.fill(&mut out);
        ok &= h(&out) == c["keyed_hash"];
        let mut r = blake3::Hasher::new_derive_key(ctx).update(&input).finalize_xof();
        r.fill(&mut out);
        ok &= h(&out) == c["derive_key"];
        if ok { pass += 1 } else { fail += 1 }
    }
    println!("{{\"check\":\"blake3-official-vectors\",\"impl\":\"rust blake3 1.8.7\",\"cases_pass\":{},\"cases_fail\":{}}}", pass, fail);
}

fn main() {
    let a: Vec<String> = std::env::args().collect();
    match a.get(1).map(|s| s.as_str()) {
        Some("gen") => gen(),
        Some("verify") => verify(&a[2]),
        Some("blake3-official") => blake3_official(&a[2]),
        _ => {
            eprintln!("usage: a1-vectors gen | verify <vectors.json> | blake3-official <test_vectors.json>");
            std::process::exit(2)
        }
    }
}
